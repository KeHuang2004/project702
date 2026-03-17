import logging
import os
import json
import re
import base64
import time
from html import unescape
from urllib.parse import urljoin, urlparse
import urllib.request

from flask import request, send_file, Response, stream_with_context
from flask_restful import Resource

from services.file_service import FileService
from services.knowledge_base_service import KnowledgeBaseService
from utils.file_manager.file_manager import get_file_type, is_allowed_file_type, resolve_upload_path, save_uploaded_file_to_path
from utils.request_manager.response import ApiResponse
from data_model.file import File
from services.file_service import _current_beijing_text
import tempfile
import shutil

logger = logging.getLogger(__name__)


class FileLatestDocsResource(Resource):
    """获取网页中的最新文档列表（简化抓取版）"""

    DEFAULT_URL = "https://ship-research.com/article/current"
    SHIP_RESEARCH_SOURCE = "ship-research"
    DEFAULT_COUNT = 3
    MIN_COUNT = 1
    MAX_COUNT = 10
    DEFAULT_HTML_TIMEOUT = 15
    ARTICLE_HTML_TIMEOUT = 25
    MAX_FETCH_RETRIES = 2

    def post(self):
        try:
            payload = request.get_json(silent=True) or {}
            source_type = self.SHIP_RESEARCH_SOURCE
            source_url = self.DEFAULT_URL
            count = self._normalize_count(payload.get("count"))

            html_text = self._fetch_html_with_retry(
                source_url,
                timeout=self.DEFAULT_HTML_TIMEOUT,
                retries=self.MAX_FETCH_RETRIES,
            )
            items = self._extract_ship_research_items(
                html_text=html_text,
                base_url=source_url,
                limit=count,
            )

            return ApiResponse.success(
                "抓取完成",
                {
                    "source_url": source_url,
                    "source_type": source_type,
                    "count": len(items),
                    "requested_count": count,
                    "items": items,
                },
            )
        except Exception as e:
            logger.error(f"抓取最新文档失败: {e}")
            return ApiResponse.internal_error("抓取最新文档失败", {"error": str(e)})

    @classmethod
    def _normalize_count(cls, value):
        try:
            parsed = int(value)
        except Exception:
            return cls.DEFAULT_COUNT
        return max(cls.MIN_COUNT, min(cls.MAX_COUNT, parsed))

    @staticmethod
    def _fetch_html(url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=FileLatestDocsResource.DEFAULT_HTML_TIMEOUT) as resp:
            raw = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()

        charset = None
        if "charset=" in ctype:
            charset = ctype.split("charset=")[-1].split(";")[0].strip()

        for enc in [charset, "utf-8", "gbk", "gb2312"]:
            if not enc:
                continue
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:
                continue

        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _fetch_html_with_retry(url: str, timeout: int, retries: int) -> str:
        attempts = max(0, int(retries)) + 1
        last_error = None

        for attempt in range(1, attempts + 1):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/125.0 Safari/537.36"
                        )
                    },
                )
                # 每次重试适度拉长超时时间，降低 ship-research 偶发慢响应带来的失败率
                dynamic_timeout = max(5, int(timeout) + (attempt - 1) * 8)
                with urllib.request.urlopen(req, timeout=dynamic_timeout) as resp:
                    raw = resp.read()
                    ctype = (resp.headers.get("Content-Type") or "").lower()

                charset = None
                if "charset=" in ctype:
                    charset = ctype.split("charset=")[-1].split(";")[0].strip()

                for enc in [charset, "utf-8", "gbk", "gb2312"]:
                    if not enc:
                        continue
                    try:
                        return raw.decode(enc, errors="ignore")
                    except Exception:
                        continue

                return raw.decode("utf-8", errors="ignore")
            except Exception as error:
                last_error = error
                if attempt < attempts:
                    time.sleep(min(1.2 * attempt, 3.0))

        raise last_error

    @staticmethod
    def _fetch_binary(url: str):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0 Safari/537.36"
                ),
                "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read(), (resp.headers.get("Content-Type") or "application/pdf")

    @staticmethod
    def _extract_doc_items(
        html_text: str,
        base_url: str,
        selected_date: str,
        limit: int,
    ):
        anchors = re.findall(
            r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        candidates = []
        seen = set()

        for href, inner_html in anchors:
            href = (href or "").strip()
            if not href or href.startswith("#") or href.lower().startswith("javascript:"):
                continue

            download_url = urljoin(base_url, href)
            if download_url in seen:
                continue

            title = re.sub(r"<[^>]+>", "", inner_html or "")
            title = unescape(title).strip()

            # 基于链接文本和URL提取日期/大小
            date_match = re.search(
                r"(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)",
                f"{title} {href}",
            )
            size_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)",
                f"{title} {href}",
                flags=re.IGNORECASE,
            )

            if selected_date and selected_date not in title and selected_date not in href:
                # 指定日期时优先过滤，不匹配则跳过
                continue

            if not title:
                path_name = os.path.basename(urlparse(download_url).path or "")
                title = path_name or "未命名文档"

            item = {
                "name": title,
                "date": (date_match.group(1) if date_match else (selected_date or "未知")),
                "size": (
                    f"{size_match.group(1)} {size_match.group(2).upper()}"
                    if size_match
                    else "未知"
                ),
                "download_url": download_url,
            }

            seen.add(download_url)
            candidates.append(item)

            if len(candidates) >= limit:
                break

        # 如果按日期过滤后为空，退化为不过滤抓取，避免无结果
        if not candidates and selected_date:
            return FileLatestDocsResource._extract_doc_items(
                html_text=html_text,
                base_url=base_url,
                selected_date="",
                limit=limit,
            )

        return candidates[:limit]

    @staticmethod
    def _extract_ship_research_items(
        html_text: str,
        base_url: str,
        limit: int,
    ):
        parsed_url = urlparse(base_url)
        path_lower = (parsed_url.path or "").lower()
        issue_publish_date = FileLatestDocsResource._extract_ship_issue_publish_date(html_text)

        if "/article/doi/" in path_lower or "/article/id/" in path_lower:
            item = FileLatestDocsResource._extract_ship_item_from_article_page(
                article_url=base_url,
                article_html=html_text,
            )
            if not item:
                return []
            if item.get("date") in (None, "", "未知") and issue_publish_date:
                item["date"] = issue_publish_date
            return [item]

        if "/article/current" in path_lower:
            article_urls = FileLatestDocsResource._extract_ship_current_issue_article_urls(html_text, base_url)
        else:
            scope_html = FileLatestDocsResource._extract_ship_online_first_scope(html_text)

            doi_links = re.findall(
                r"href=[\"']([^\"']*/article/doi/[^\"']+)[\"']",
                scope_html,
                flags=re.IGNORECASE,
            )
            if not doi_links:
                doi_links = re.findall(
                    r"href=[\"']([^\"']*/article/doi/[^\"']+)[\"']",
                    html_text,
                    flags=re.IGNORECASE,
                )

            article_urls = []
            seen_article_urls = set()
            for href in doi_links:
                article_url = urljoin(base_url, (href or "").strip())
                if not article_url or article_url in seen_article_urls:
                    continue
                seen_article_urls.add(article_url)
                article_urls.append(article_url)
                if len(article_urls) >= max(60, limit * 4):
                    break

        items = []
        for article_url in article_urls:
            if len(items) >= max(80, limit * 4):
                break

            try:
                article_html = FileLatestDocsResource._fetch_html_with_retry(
                    article_url,
                    timeout=FileLatestDocsResource.ARTICLE_HTML_TIMEOUT,
                    retries=FileLatestDocsResource.MAX_FETCH_RETRIES,
                )
                item = FileLatestDocsResource._extract_ship_item_from_article_page(
                    article_url=article_url,
                    article_html=article_html,
                )
            except Exception as e:
                logger.warning(f"解析 ship-research 文章失败: {article_url}, error={e}")
                continue

            if not item:
                continue

            if item.get("date") in (None, "", "未知") and issue_publish_date:
                item["date"] = issue_publish_date

            doi_from_url = FileLatestDocsResource._extract_doi_from_article_url(article_url)
            if doi_from_url and not item.get("doi"):
                item["doi"] = doi_from_url

            items.append(item)

        items.sort(
            key=lambda row: FileLatestDocsResource._normalize_date_text(row.get("date") or ""),
            reverse=True,
        )
        return items[:limit]

    @staticmethod
    def _extract_ship_current_issue_article_urls(html_text: str, base_url: str):
        issue_block_match = re.search(
            r"<div[^>]+id=[\"']issueList[\"'][^>]*>([\s\S]*?)<script[^>]+id=[\"']journalgTpl[\"']",
            html_text,
            flags=re.IGNORECASE,
        )
        issue_html = issue_block_match.group(1) if issue_block_match else html_text

        hrefs = re.findall(
            r"href=[\"']([^\"']*/article/(?:doi|id)/[^\"'?#]+)[^\"']*[\"']",
            issue_html,
            flags=re.IGNORECASE,
        )

        article_urls = []
        seen_article_urls = set()
        for href in hrefs:
            article_url = urljoin(base_url, (href or "").strip())
            if not article_url or article_url in seen_article_urls:
                continue
            seen_article_urls.add(article_url)
            article_urls.append(article_url)

        return article_urls

    @staticmethod
    def _extract_ship_issue_publish_date(html_text: str) -> str:
        match = re.search(
            r'"publishDate"\s*:\s*"(\d{4}-\d{2}-\d{2})',
            html_text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def _extract_doi_from_article_url(article_url: str) -> str:
        match = re.search(r"/article/doi/([^/?#]+)", article_url, flags=re.IGNORECASE)
        if not match:
            return ""
        return unescape(match.group(1)).strip()

    @staticmethod
    def _normalize_date_text(date_text: str) -> str:
        match = re.search(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})", str(date_text or ""))
        if not match:
            return "0000-00-00"
        y, m, d = match.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    @staticmethod
    def _extract_ship_online_first_scope(html_text: str) -> str:
        patterns = [
            r"<div[^>]+id=[\"']onlineFirst[\"'][^>]*>([\s\S]*?)<div[^>]+id=[\"']latestArticle[\"']",
            r"<div[^>]+id=[\"']onlineFirst[\"'][^>]*>([\s\S]*?)<div[^>]+id=[\"']indexLatestArticle[\"']",
            r"href=[\"']#onlineFirst[\"'][\s\S]*?<div[^>]+id=[\"']onlineFirst[\"'][^>]*>([\s\S]*?)</div>\s*</div>\s*</div>",
            r"id=[\"']onlineFirst[\"'][\s\S]*?(?:id=[\"']latestArticle[\"']|id=[\"']indexLatestArticle[\"'])",
        ]

        for pattern in patterns:
            match = re.search(pattern, html_text, flags=re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group(0)

        return html_text

    @staticmethod
    def _extract_ship_item_from_article_page(article_url: str, article_html: str):
        article_meta = FileLatestDocsResource._extract_ship_article_meta(article_html)
        return FileLatestDocsResource._build_ship_item(article_url, article_html, article_meta)

    @staticmethod
    def _extract_ship_article_meta(article_html: str):
        m = re.search(
            r"var\s+article_meta_data\s*=\s*'([^']+)'\s*;",
            article_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return {}

        raw_b64 = (m.group(1) or "").strip()
        if not raw_b64:
            return {}

        try:
            decoded = base64.b64decode(raw_b64)
            return json.loads(decoded.decode("utf-8", errors="ignore"))
        except Exception:
            return {}

    @staticmethod
    def _build_ship_item(article_url: str, article_html: str, meta: dict):
        meta = meta or {}
        article_business = meta.get("articleBusiness") or {}

        title = (meta.get("titleCn") or meta.get("titleEn") or "").strip()
        if not title:
            title_m = re.search(r"<title>(.*?)</title>", article_html, flags=re.IGNORECASE | re.DOTALL)
            if title_m:
                title = re.sub(r"\s+", " ", unescape(title_m.group(1))).strip()
        if not title:
            title = "未命名文档"

        doi = (meta.get("doi") or "").strip()
        article_id = str(
            article_business.get("articleId")
            or meta.get("id")
            or meta.get("articleId")
            or FileLatestDocsResource._extract_ship_article_id_from_html(article_html)
            or FileLatestDocsResource._extract_ship_article_id_from_url(article_url)
            or ""
        ).strip()

        # 优先取页面 meta 中的标准日期（citation_date / dc.date）
        date = FileLatestDocsResource._extract_ship_page_date(article_html)
        if not date:
            date = "未知"
        release_progress = meta.get("releaseProgress") or {}
        if date == "未知":
            for key in ("preprintDate", "pubDate", "ppubDate", "lastUpdateTime"):
                date_value = (meta.get(key) or "").strip()
                if date_value:
                    date = date_value
                    break
        if date == "未知":
            for key in ("maxLastReleaseTime", "lastReleaseTime"):
                date_value = (release_progress.get(key) or "").strip()
                if date_value:
                    date = date_value
                    break

        size = FileLatestDocsResource._extract_ship_pdf_size(article_html, article_business)
        preview_url = FileLatestDocsResource._build_ship_preview_url(article_id)
        download_url = preview_url or FileLatestDocsResource._extract_ship_download_url(
            article_url=article_url,
            article_html=article_html,
            meta=meta,
            doi=doi,
        )

        if not download_url:
            return None

        return {
            "name": title,
            "date": FileLatestDocsResource._normalize_date_text(date),
            "size": size,
            "article_id": article_id,
            "preview_url": download_url,
            "download_url": download_url,
            "doi": doi,
            "article_url": article_url,
        }

    @staticmethod
    def _extract_ship_article_id_from_url(article_url: str) -> str:
        match = re.search(r"/article/id/([^/?#]+)", article_url, flags=re.IGNORECASE)
        if not match:
            return ""
        return unescape(match.group(1)).strip()

    @staticmethod
    def _extract_ship_article_id_from_html(article_html: str) -> str:
        patterns = [
            r'<meta\s+name=["\']citation_id["\']\s+content=["\']([^"\']+)["\']',
            r'id=["\']articleId["\']\s+value=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, article_html, flags=re.IGNORECASE)
            if match:
                return (match.group(1) or "").strip()
        return ""

    @staticmethod
    def _build_ship_preview_url(article_id: str) -> str:
        aid = str(article_id or "").strip()
        if not aid:
            return ""
        return f"https://ship-research.com/cn/article/pdf/preview/{aid}.pdf"

    @staticmethod
    def _extract_ship_page_date(article_html: str) -> str:
        patterns = [
            r'<meta\s+name=["\']citation_date["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+name=["\']dc\.date["\']\s+content=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, article_html, flags=re.IGNORECASE)
            if not match:
                continue
            value = (match.group(1) or "").strip()
            normalized = FileLatestDocsResource._normalize_date_text(value)
            if normalized != "0000-00-00":
                return normalized
        return ""

    @staticmethod
    def _extract_ship_pdf_size(article_html: str, article_business: dict) -> str:
        size_kb = article_business.get("pdfFileSizeInt")
        try:
            size_kb_float = float(size_kb)
            if size_kb_float >= 1024:
                return f"{(size_kb_float / 1024):.2f} MB"
            return f"{size_kb_float:.0f} KB"
        except Exception:
            pass

        button_size_match = re.search(
            r"PDF下载\s*\((\d+(?:\.\d+)?)\s*(KB|MB|GB)\)",
            article_html,
            flags=re.IGNORECASE,
        )
        if button_size_match:
            return f"{button_size_match.group(1)} {button_size_match.group(2).upper()}"

        return "未知"


class FileLatestDocProxyResource(Resource):
    """代理下载固定站点的预览PDF，避免前端直接跨域抓取"""

    ALLOWED_HOSTS = {"ship-research.com", "www.ship-research.com"}
    ALLOWED_PATH_PREFIX = "/cn/article/pdf/preview/"

    def get(self):
        try:
            raw_url = (request.args.get("url") or "").strip()
            if not raw_url:
                return ApiResponse.bad_request("缺少预览链接")

            parsed = urlparse(raw_url)
            host = (parsed.netloc or "").lower()
            path = parsed.path or ""
            if parsed.scheme not in {"http", "https"}:
                return ApiResponse.bad_request("预览链接协议不受支持")
            if host not in self.ALLOWED_HOSTS:
                return ApiResponse.bad_request("仅允许代理 ship-research.com 站点")
            if not path.startswith(self.ALLOWED_PATH_PREFIX) or not path.lower().endswith(".pdf"):
                return ApiResponse.bad_request("仅允许代理预览PDF链接")

            binary, content_type = FileLatestDocsResource._fetch_binary(raw_url)
            filename = os.path.basename(path) or "preview.pdf"
            return Response(
                binary,
                mimetype=content_type.split(";")[0] or "application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{filename}"',
                    "Cache-Control": "no-store",
                },
            )
        except Exception as e:
            logger.error(f"代理下载最新文档PDF失败: {e}")
            return ApiResponse.internal_error("代理下载PDF失败", {"error": str(e)})

    @staticmethod
    def _extract_ship_download_url(article_url: str, article_html: str, meta: dict, doi: str) -> str:
        article_business = (meta or {}).get("articleBusiness") or {}

        article_id = str(
            article_business.get("articleId")
            or meta.get("id")
            or meta.get("articleId")
            or ""
        ).strip()

        # 统一使用 article_id 的预览PDF链接格式
        if article_id:
            return f"https://ship-research.com/cn/article/pdf/preview/{article_id}.pdf"

        pdf_link = (article_business.get("pdfLink") or "").strip()
        if pdf_link:
            return urljoin(article_url, pdf_link)

        button_link_patterns = [
            r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>\s*下载\s*</a>",
            r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>\s*PDF下载\s*</a>",
        ]
        for pattern in button_link_patterns:
            match = re.search(pattern, article_html, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            href = (match.group(1) or "").strip()
            if href and not href.lower().startswith("javascript:"):
                return urljoin(article_url, href)

        file_path = (meta.get("filePath") or "").strip()
        pdf_filename = (article_business.get("pdfFileName") or "").strip()
        if file_path and pdf_filename:
            return urljoin(article_url, f"{file_path.rstrip('/')}/{pdf_filename}")

        citation_pdf_url = re.search(
            r"<meta\s+name=[\"']citation_pdf_url[\"']\s+content=[\"']([^\"']+)[\"']",
            article_html,
            flags=re.IGNORECASE,
        )
        if citation_pdf_url:
            return urljoin(article_url, citation_pdf_url.group(1).strip())

        article_id = str((meta.get("id") or meta.get("articleId") or "")).strip()
        if article_id:
            return f"https://ship-research.com/cn/article/pdf/preview/{article_id}.pdf"

        return ""


class FileResource(Resource):
    """文件资源API"""

    def __init__(self):
        self.file_service = FileService()
        self.kb_service = KnowledgeBaseService()

    def get(self, kb_id=None, file_id=None):
        """
        GET /files：返回文件ID列表（无过滤）
        GET /files/<file_id>：返回完整记录，支持多个ID如1,2,3；?attribute=field返回字段（支持多字段，逗号分隔）
        """
        try:
            if file_id is not None:
                return self._get_files_by_ids(file_id)

            files, total = self.file_service.search_files(
                page=1,
                page_size=1_000_000,
            )
            return ApiResponse.success("获取文件ID列表成功", {"ids": [f.id for f in files]})
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return ApiResponse.internal_error("获取文件信息失败")

    def post(self, kb_id=None):
        """GET 不支持通过 kb_id，上传请使用 FileUploadResource"""
        return ApiResponse.method_not_allowed("GET/POST 请使用规范接口")


    def delete(self, file_id=None):
        """删除文件：支持多个ID，删除记录、相关文本块、更新知识库，强制删除物理文件"""
        try:
            if file_id is None:
                return ApiResponse.bad_request("缺少文件ID")

            id_strs = str(file_id).split(',')
            ids = []
            for id_str in id_strs:
                try:
                    ids.append(int(id_str.strip()))
                except ValueError:
                    return ApiResponse.bad_request(f"无效的文件ID: {id_str}")

            deleted = []
            failed = []
            for fid in ids:
                try:
                    self.file_service.delete_file_and_related(fid, delete_physical_file=True)
                    deleted.append(fid)
                except Exception:
                    failed.append(fid)

            return ApiResponse.success("删除文件完成", {"deleted": deleted, "failed": failed})
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return ApiResponse.internal_error("删除文件失败")

    def _get_single_file(self, kb_id: int, file_id):
        """获取单个文件详情"""
        attr_values = []
        for key in ("attribute", "attr"):
            attr_values.extend(request.args.getlist(key))
        attrs: list[str] = []
        for item in attr_values:
            if not item:
                continue
            for part in item.split(","):
                part = part.strip()
                if part and part not in attrs:
                    attrs.append(part)

        file_obj = self.file_service.get_by_id(file_id)
        if not file_obj:
            return ApiResponse.not_found("文件不存在")

        data = file_obj.to_dict()
        if attrs:
            invalid = [a for a in attrs if a not in data]
            if invalid:
                return ApiResponse.bad_request("无效字段")
            return ApiResponse.success("获取文件属性成功", {a: data.get(a) for a in attrs})

        return ApiResponse.success("获取文件详情成功", data)

    def _get_files_by_ids(self, file_id):
        """按文件ID获取，支持多个ID如1,2,3；支持 ?attribute=field"""
        # 支持多个ID，逗号分隔
        id_strs = str(file_id).split(',')
        ids = []
        for id_str in id_strs:
            try:
                ids.append(int(id_str.strip()))
            except ValueError:
                return ApiResponse.bad_request(f"无效的文件ID: {id_str}")

        # 获取attribute参数
        attr_param = request.args.get("attribute", "")
        attrs = [a.strip() for a in attr_param.split(",") if a.strip()] if attr_param else []

        results = []
        for fid in ids:
            file_obj = self.file_service.get_by_id(fid)
            if not file_obj:
                return ApiResponse.not_found(f"文件不存在: {fid}")

            data = file_obj.to_dict()

            if attrs:
                invalid = [a for a in attrs if a not in data]
                if invalid:
                    return ApiResponse.bad_request(f"无效字段: {', '.join(invalid)}")
                results.append({a: data.get(a) for a in attrs})
            else:
                results.append(data)

        if len(results) == 1:
            return ApiResponse.success("获取文件成功", results[0])
        else:
            return ApiResponse.success("获取文件成功", {"items": results})

        data = file_obj.to_dict()
        if attrs:
            invalid = [a for a in attrs if a not in data]
            if invalid:
                return ApiResponse.bad_request("无效字段")
            return ApiResponse.success("获取文件属性成功", {a: data.get(a) for a in attrs})

        return ApiResponse.success("获取文件详情成功", data)

    def put(self, file_id=None):
        """按文件ID更新单字段：PUT /files/<id>?attribute=field，Body为新值"""
        try:
            if file_id is None:
                return ApiResponse.bad_request("缺少文件ID")

            # 只支持单个ID更新
            try:
                fid = int(file_id)
            except ValueError:
                return ApiResponse.bad_request("无效的文件ID")

            attr = (request.args.get("attribute") or "").strip()
            if not attr:
                return ApiResponse.bad_request("缺少更新字段 attribute")

            value = request.get_json(silent=True)
            if value is None:
                return ApiResponse.bad_request("缺少更新内容（JSON）")

            file_obj = self.file_service.get_by_id(fid)
            if not file_obj:
                return ApiResponse.not_found("文件不存在")

            if not hasattr(file_obj, attr):
                return ApiResponse.bad_request("无效字段")

            # 特殊类型处理：时间字段允许传字符串（ISO8601或 'YYYY-MM-DD HH:MM:SS'）
            setattr(file_obj, attr, value)
            updated = self.file_service.update(fid, file_obj)
            return ApiResponse.success("更新文件成功", updated.to_dict())
        except Exception as e:
            logger.error(f"更新文件失败: {e}")
            return ApiResponse.internal_error("更新文件失败")

    def _get_file_list(self):
        return ApiResponse.method_not_allowed("请使用 GET /files?knowledge_base_id= 过滤获取ID列表")


class FileDownloadResource(Resource):
    """文件下载资源：GET /files/<file_id>/download"""

    def __init__(self):
        self.file_service = FileService()

    def get(self, file_id: int):
        try:
            if file_id is None:
                return ApiResponse.bad_request("缺少文件ID")

            file_obj = self.file_service.get_by_id(int(file_id))
            if not file_obj:
                return ApiResponse.not_found("文件不存在")

            file_path = getattr(file_obj, "file_path", None) or ""

            # 若数据库路径不存在，按知识库目录 + 文件名兜底
            if not file_path or not os.path.exists(file_path):
                try:
                    from config import Config

                    kb_id = int(getattr(file_obj, "knowledge_base_id", 0) or 0)
                    filename = getattr(file_obj, "filename", "") or ""
                    if kb_id and filename:
                        candidate = os.path.join(Config.UPLOAD_FOLDER, str(kb_id), filename)
                        if os.path.exists(candidate):
                            file_path = candidate
                except Exception:
                    file_path = ""

            if not file_path or not os.path.exists(file_path):
                return ApiResponse.not_found("文件不存在或已被删除")

            download_name = getattr(file_obj, "filename", None) or os.path.basename(file_path)
            return send_file(file_path, as_attachment=True, download_name=download_name)
        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return ApiResponse.internal_error("下载文件失败")


class FileProcessResource(Resource):
    """文件处理触发 API：在用户点击“下一步”后显式启动处理"""

    def __init__(self):
        self.file_service = FileService()
        self.kb_service = KnowledgeBaseService()

    def post(self, kb_id: int):
        try:
            if kb_id is None:
                return ApiResponse.bad_request("知识库ID不能为空")

            kb_id = int(kb_id)
            if not self.kb_service.exists(kb_id):
                return ApiResponse.not_found("知识库不存在")

            payload = request.get_json(silent=True) or {}
            chunk_length = payload.get("chunk_length")
            overlap_count = payload.get("chunk_overlap") or payload.get("overlap_count")
            segmentation_strategy = payload.get("segmentation_strategy") or payload.get("strategy")

            result = self.file_service.start_processing_for_kb(
                knowledge_base_id=kb_id,
                chunk_length=chunk_length,
                overlap_count=overlap_count,
                segmentation_strategy=segmentation_strategy,
            )

            return ApiResponse.success("处理任务已启动", result)
        except Exception as e:
            logger.error(f"启动处理任务失败: {str(e)}")
            return ApiResponse.internal_error("启动处理任务失败")


class FileUploadResource(Resource):
    """专用于上传文件：POST /files/<kb_id>"""

    def __init__(self):
        self.file_service = FileService()
        self.kb_service = KnowledgeBaseService()

    def post(self, kb_id=None):
        try:
            if "files" not in request.files:
                return ApiResponse.bad_request("没有上传文件")

            files = request.files.getlist("files")

            if not kb_id:
                return ApiResponse.bad_request("知识库ID不能为空")

            try:
                knowledge_base_id = int(kb_id)
            except ValueError:
                return ApiResponse.bad_request("无效的知识库ID")

            if not self.kb_service.exists(knowledge_base_id):
                return ApiResponse.not_found("知识库不存在")

            empty_name_files = []
            invalid_type_files = []
            duplicate_in_db = []

            prepared = []
            for f in files or []:
                fname = getattr(f, "filename", "") or ""
                if not fname.strip():
                    empty_name_files.append(fname)
                    continue

                ftype = get_file_type(fname)
                if not is_allowed_file_type(fname):
                    invalid_type_files.append(fname)

                try:
                    if self.file_service.exists_name_type_in_kb(fname, ftype, knowledge_base_id):
                        duplicate_in_db.append(fname)
                except Exception:
                    pass

                file_path, final_filename = resolve_upload_path(knowledge_base_id, fname)
                try:
                    spooled = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
                    if hasattr(f, "stream"):
                        f.stream.seek(0)
                    shutil.copyfileobj(f.stream, spooled)
                    spooled.seek(0)
                except Exception as exc:
                    return ApiResponse.bad_request(f"读取文件失败: {fname} ({exc})")

                prepared.append({
                    "filename": final_filename,
                    "file_type": ftype,
                    "file_path": file_path,
                    "spooled": spooled,
                })

            if empty_name_files:
                return ApiResponse.bad_request(
                    message=f"存在空文件名: {', '.join(sorted(set(empty_name_files)))}"
                )

            if duplicate_in_db:
                return ApiResponse.bad_request(
                    message=f"数据库中已存在同名同类型文件: {', '.join(sorted(set(duplicate_in_db)))}"
                )

            if invalid_type_files:
                return ApiResponse.bad_request(
                    message=f"存在不支持的文件类型: {', '.join(sorted(set(invalid_type_files)))}"
                )

            created_items = []
            for item in prepared:
                file_obj = File()
                file_obj.knowledge_base_id = knowledge_base_id
                file_obj.filename = item["filename"]
                file_obj.file_path = item["file_path"]
                file_obj.file_type = item["file_type"]
                file_obj.file_size = 0
                file_obj.status = File.STATUS_UPLOADING
                file_obj.segmentation_strategy = None
                file_obj.chunk_length = None
                file_obj.overlap_count = None
                file_obj.chunks_list = []

                errors = file_obj.validate()
                if errors:
                    return ApiResponse.bad_request("; ".join(errors))

                created = self.file_service.create(file_obj)
                self.file_service._append_file_reference(knowledge_base_id, created.id)
                item["file_id"] = created.id
                created_items.append(item)

            def generate():
                yield f"data: {json.dumps({'event': 'start', 'total': len(created_items)}, ensure_ascii=False)}\n\n"

                for item in created_items:
                    try:
                        with open(item["file_path"], "wb") as out:
                            shutil.copyfileobj(item["spooled"], out)
                        item["spooled"].close()
                        file_size = os.path.getsize(item["file_path"])

                        update = File()
                        update.id = item["file_id"]
                        update.file_size = file_size
                        update.status = File.STATUS_UPLOADED
                        update.upload_at = _current_beijing_text()
                        self.file_service.update(item["file_id"], update)
                        self.file_service._increment_kb_size(knowledge_base_id, file_size)

                        payload = {
                            "event": "file",
                            "file": {
                                "file_id": item["file_id"],
                                "filename": item["filename"],
                                "status": File.STATUS_UPLOADED,
                                "file_size": file_size,
                                "file_type": item["file_type"],
                            },
                        }
                    except Exception as exc:
                        fail_update = File()
                        fail_update.id = item["file_id"]
                        fail_update.status = File.STATUS_FAILED
                        self.file_service.update(item["file_id"], fail_update)
                        payload = {
                            "event": "error",
                            "file": {"filename": item["filename"]},
                            "message": str(exc),
                        }

                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'event': 'done'}, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}")
            return ApiResponse.internal_error("文件上传失败")




