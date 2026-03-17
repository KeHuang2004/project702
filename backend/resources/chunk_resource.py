import logging
import json
import time
import threading
from typing import Dict

from flask import request, Response
from flask_restful import Resource

from services.chunk_service import ChunkService
from services.knowledge_base_service import KnowledgeBaseService
from services.file_service import FileService
from config import Config
from utils.request_manager.exceptions import NotFoundError, ValidationError
from utils.request_manager.response import ApiResponse
from data_model.file import File

import threading

logger = logging.getLogger(__name__)


class ChunkRetrieveResource(Resource):
    def __init__(self):
        self.chunk_service = ChunkService()
        self.kb_service = KnowledgeBaseService()

    def post(self, kb_id: int):
        """
        新接口：/api/v1/chunks/retrieve/<kb_id>
        请求体：{ query: str, top_k?: int, threshold?: float }
        行为：
          1) 校验 kb 是否存在
          2) 校验 top_k 范围（1..chunk_count）
          3) 调用检索 -> 根据 chunk_index 拉取 chunk 详情
          4) 调用重排 -> 生成 reranked_score 并按其降序排列
        返回：统一响应格式，data.results 为最终列表
        """
        try:
            if kb_id is None:
                return ApiResponse.bad_request("知识库ID不能为空")

            payload = request.get_json(silent=True) or {}
            query = payload.get("query")
            top_k = payload.get("top_k", 5)
            threshold = payload.get("threshold")  # 可选，用于按检索分数过滤

            if not query or not str(query).strip():
                return ApiResponse.bad_request("查询内容(query)不能为空")

            # 知识库存在性
            kb = self.kb_service.get_by_id(int(kb_id))
            if not kb:
                raise NotFoundError("知识库不存在")

            # 校验 top_k
            try:
                top_k = int(top_k)
            except Exception:
                return ApiResponse.bad_request("top_k 必须为整数")

            # top_k 范围：[1, chunk_count]
            total_chunks = self.chunk_service.count_chunks_by_knowledge_base(int(kb_id))
            if total_chunks <= 0:
                return ApiResponse.success("检索成功", {"results": []})
            if top_k < 1:
                return ApiResponse.bad_request("top_k 不能小于 1")
            if top_k > total_chunks:
                return ApiResponse.bad_request(
                    f"top_k 不能大于知识库文本块总数 {total_chunks}"
                )

            # 1) 检索
            retrieved = self.chunk_service.process_retrieving(
                kb_id=int(kb_id), query=query, top_k=top_k
            )
            # 2) 重排
            reranked = self.chunk_service.process_reranking(
                query=query, chunks=retrieved
            )

            # 在重排之后按 reranked_score 进行阈值过滤（如果提供）
            if threshold is not None:
                try:
                    thr = float(threshold)
                except Exception:
                    return ApiResponse.bad_request("threshold 必须为数值")
                reranked = [
                    r
                    for r in reranked
                    if (
                        r.get("reranked_score") is not None
                        and r["reranked_score"] >= thr
                    )
                ]

            return ApiResponse.success("检索成功", {"results": reranked})
        except NotFoundError as e:
            return ApiResponse.not_found(str(e))
        except ValidationError as e:
            return ApiResponse.bad_request(str(e))
        except Exception as e:
            logger.error(f"检索文本块异常: {str(e)}")
            return ApiResponse.internal_error("检索文本块失败")


class ChunkListResource(Resource):
    """列出文本块ID（无过滤）。"""

    def __init__(self):
        self.chunk_service = ChunkService()

    def get(self):
        try:
            chunks, _ = self.chunk_service.search_chunks(
                page=1,
                page_size=1_000_000,
            )

            return ApiResponse.success("获取文本块ID列表成功", {"ids": [c.id for c in chunks]})
        except Exception as e:
            logger.error(f"获取文本块列表失败: {e}")
            return ApiResponse.internal_error("获取文本块列表失败")

    def post(self):
        """
        新接口：POST /api/v1/chunks
        请求体：{ file_ids: [1,2,3], segmentation_strategy, chunk_length, chunk_overlap }
        行为：对指定文件执行切分并入库
        """
        try:
            payload = request.get_json(silent=True) or {}
            file_ids = payload.get("file_ids") or payload.get("files") or payload.get("ids")
            if not file_ids:
                return ApiResponse.bad_request("缺少 file_ids")

            if isinstance(file_ids, str):
                file_ids = [fid.strip() for fid in file_ids.split(",") if fid.strip()]

            try:
                ids = [int(fid) for fid in file_ids]
            except Exception:
                return ApiResponse.bad_request("file_ids 必须为整数列表")

            segmentation_strategy = payload.get("segmentation_strategy") or payload.get("strategy") or "recursive_character"
            try:
                chunk_length = int(payload.get("chunk_length")) if payload.get("chunk_length") is not None else getattr(Config, "DEFAULT_CHUNK_SIZE", 512)
            except Exception:
                chunk_length = getattr(Config, "DEFAULT_CHUNK_SIZE", 512)
            try:
                chunk_overlap = int(payload.get("chunk_overlap")) if payload.get("chunk_overlap") is not None else getattr(Config, "DEFAULT_CHUNK_OVERLAP", 50)
            except Exception:
                chunk_overlap = getattr(Config, "DEFAULT_CHUNK_OVERLAP", 50)

            file_service = FileService()
            groups = {}
            for fid in ids:
                file_obj = file_service.get_by_id(fid)
                if not file_obj:
                    return ApiResponse.not_found(f"文件不存在: {fid}")
                kb_id = int(file_obj.knowledge_base_id)
                groups.setdefault(kb_id, []).append({"file_id": fid})
                current_status = (getattr(file_obj, "status", "") or "").lower()
                has_chunks = bool(getattr(file_obj, "chunks_list", None))

                if has_chunks:
                    try:
                        file_service._clear_chunks_for_file(file_obj)
                    except Exception as exc:
                        logger.error(f"清理文本块失败: {exc}")
                        return ApiResponse.internal_error("清理文本块失败")

                update_payload = File()
                update_payload.id = fid
                update_payload.status = File.STATUS_SPLITTING if current_status == File.STATUS_UPLOADED else File.STATUS_RE_SPLITTING
                try:
                    file_service.update(fid, update_payload)
                except Exception as exc:
                    logger.error(f"更新文件状态失败: {exc}")
                    return ApiResponse.internal_error("更新文件状态失败")

            # 刷新知识库 chunks_list
            for kb_id in groups.keys():
                try:
                    file_service._refresh_kb_chunks_list(kb_id)
                except Exception:
                    pass

            def _run_split():
                for kb_id, files_payload in groups.items():
                    try:
                        file_service.split_and_store(
                            files_to_split=files_payload,
                            knowledge_base_id=kb_id,
                            chunk_length=chunk_length,
                            overlap_count=chunk_overlap,
                            segmentation_strategy=segmentation_strategy,
                        )
                    except Exception as exc:
                        logger.error(f"切分失败 kb={kb_id}: {exc}")

            threading.Thread(target=_run_split, daemon=True).start()

            pending = set(ids)

            def generate():
                while True:
                    files_payload = []
                    done_ids = []
                    for fid in list(pending):
                        file_obj = file_service.get_by_id(fid)
                        status = getattr(file_obj, "status", None) if file_obj else "file_not_found"
                        files_payload.append({"id": fid, "status": status})
                        if str(status).lower() in ("splitted", "failed", "file_not_found"):
                            done_ids.append(fid)

                    for fid in done_ids:
                        pending.discard(fid)

                    payload = {
                        "files": files_payload,
                        "pending": list(pending),
                        "done": len(pending) == 0,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                    if not pending:
                        break
                    time.sleep(1)

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        except Exception as e:
            logger.error(f"切分失败: {e}")
            return ApiResponse.internal_error("切分失败")


class ChunkEmbeddingResource(Resource):
    """批量对文本块执行向量嵌入。"""

    def __init__(self):
        self.chunk_service = ChunkService()

    def post(self):
        try:
            payload = request.get_json(silent=True) or {}
            chunk_ids = payload.get("chunk_ids") or []
            if not isinstance(chunk_ids, list) or not all(isinstance(x, int) for x in chunk_ids):
                return ApiResponse.bad_request("chunk_ids 必须为整型ID数组")

            model = payload.get("embedding_model")
            result = self.chunk_service.embed_chunks_by_ids(chunk_ids=chunk_ids, embedding_model=model)
            return ApiResponse.success("嵌入任务完成", result)
        except ValidationError as e:
            return ApiResponse.bad_request(str(e))
        except Exception as e:
            logger.error(f"文本块嵌入异常: {e}")
            return ApiResponse.internal_error("文本块嵌入失败")


class ChunkEmbeddingToFileResource(Resource):
    """按文本块嵌入并写入文件向量。"""

    def __init__(self):
        self.chunk_service = ChunkService()

    def post(self):
        try:
            payload = request.get_json(silent=True) or {}
            items = payload.get("items")

            if items is None:
                # 兼容单条
                items = [
                    {
                        "chunk_id": payload.get("chunk_id"),
                        "chunk_index": payload.get("chunk_index"),
                        "file_id": payload.get("file_id"),
                    }
                ]

            if not isinstance(items, list) or len(items) == 0:
                return ApiResponse.bad_request("items 不能为空")

            normalized = self.chunk_service.prepare_embedding_items(items)
            requested_by_file: Dict[int, set] = {}
            for item in normalized:
                fid = int(item.get("file_id"))
                cid = int(item.get("chunk_id"))
                requested_by_file.setdefault(fid, set()).add(cid)

            def generate():
                success_by_file: Dict[int, set] = {}
                yield f"data: {json.dumps({'event': 'start', 'total': len(normalized)}, ensure_ascii=False)}\n\n"

                batch_size = 500
                for i in range(0, len(normalized), batch_size):
                    batch = normalized[i : i + batch_size]
                    try:
                        results, errors = self.chunk_service.embed_chunks_to_files_batch(batch)
                        for result in results:
                            payload = {"event": "chunk", "chunk": result}
                            fid = int(result.get("file_id"))
                            cid = int(result.get("chunk_id"))
                            success_by_file.setdefault(fid, set()).add(cid)
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                        for err in errors:
                            item = err.get("item") or {}
                            payload = {
                                "event": "error",
                                "chunk": {
                                    "chunk_id": item.get("chunk_id"),
                                    "chunk_index": item.get("chunk_index"),
                                    "file_id": item.get("file_id"),
                                },
                                "message": err.get("reason") or "嵌入失败",
                            }
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    except Exception as exc:
                        for item in batch:
                            payload = {
                                "event": "error",
                                "chunk": {
                                    "chunk_id": item.get("chunk_id"),
                                    "chunk_index": item.get("chunk_index"),
                                    "file_id": item.get("file_id"),
                                },
                                "message": str(exc),
                            }
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # 请求涉及的文件先置为 embedding（若尚未更新），结束后检查是否已全部 embedded
                file_service = FileService()
                for fid in requested_by_file.keys():
                    try:
                        file_service.update_file_status(fid, File.STATUS_EMBEDDING)
                    except Exception:
                        pass

                for fid in requested_by_file.keys():
                    try:
                        file_obj = file_service.get_by_id(fid)
                        file_chunks = list(getattr(file_obj, "chunks_list", []) or []) if file_obj else []
                        if not file_chunks:
                            continue

                        all_embedded = True
                        for cid in file_chunks:
                            try:
                                chunk = self.chunk_service.get_by_id(int(cid))
                                status = (getattr(chunk, "status", "") or "").lower() if chunk else ""
                                if status != File.STATUS_EMBEDDED:
                                    all_embedded = False
                                    break
                            except Exception:
                                all_embedded = False
                                break

                        if all_embedded:
                            file_service.update_file_status(fid, File.STATUS_EMBEDDED)
                    except Exception:
                        pass

                yield f"data: {json.dumps({'event': 'done'}, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        except ValidationError as e:
            return ApiResponse.bad_request(str(e))
        except Exception as e:
            logger.error(f"文本块文件嵌入异常: {e}")
            return ApiResponse.internal_error("文本块嵌入失败")


class ChunkDetailResource(Resource):
    """获取单个文本块或指定属性"""

    def __init__(self):
        self.chunk_service = ChunkService()

    def get(self, chunk_id: str):
        """获取单个文本块，支持多个ID如1,2,3；?attribute=field返回字段（支持多字段，逗号分隔）"""
        try:
            # 支持多个ID，逗号分隔
            id_strs = chunk_id.split(',')
            ids = []
            for id_str in id_strs:
                try:
                    ids.append(int(id_str.strip()))
                except ValueError:
                    return ApiResponse.bad_request(f"无效的文本块ID: {id_str}")

            # 获取attribute参数
            attr_param = request.args.get("attribute", "")
            attrs = [a.strip() for a in attr_param.split(",") if a.strip()] if attr_param else []

            results = []
            for cid in ids:
                chunk = self.chunk_service.get_by_id(cid)
                if not chunk:
                    return ApiResponse.not_found(f"文本块不存在: {cid}")

                data = chunk.to_dict()

                if attrs:
                    invalid = [a for a in attrs if a not in data]
                    if invalid:
                        return ApiResponse.bad_request(f"无效字段: {', '.join(invalid)}")
                    results.append({a: data.get(a) for a in attrs})
                else:
                    results.append(data)

            if len(results) == 1:
                return ApiResponse.success("获取文本块成功", results[0])
            else:
                return ApiResponse.success("获取文本块成功", {"items": results})
        except Exception as e:
            logger.error(f"获取文本块失败: {e}")
            return ApiResponse.internal_error("获取文本块失败")

    def put(self, chunk_id: str):
        """按文本块ID更新单字段：PUT /chunks/<id>?attribute=field，Body为新值"""
        try:
            attr = (request.args.get("attribute") or "").strip()
            if not attr:
                return ApiResponse.bad_request("缺少更新字段 attribute")

            value = request.get_json(silent=True)
            if value is None:
                return ApiResponse.bad_request("缺少更新内容（JSON）")

            # 只支持单个ID更新
            try:
                cid = int(chunk_id)
            except ValueError:
                return ApiResponse.bad_request("无效的文本块ID")

            chunk = self.chunk_service.get_by_id(cid)
            if not chunk:
                return ApiResponse.not_found("文本块不存在")

            if not hasattr(chunk, attr):
                return ApiResponse.bad_request("无效字段")

            setattr(chunk, attr, value)

            updated = self.chunk_service.update(cid, chunk)
            return ApiResponse.success("更新文本块成功", updated.to_dict())
        except ValidationError as e:
            return ApiResponse.bad_request(str(e))
        except Exception as e:
            logger.error(f"更新文本块失败: {e}")
            return ApiResponse.internal_error("更新文本块失败")



    def delete(self, chunk_id: str):
        """删除文本块：DELETE /chunks/<chunk_id>，支持多个ID如1,2,3"""
        try:
            id_strs = str(chunk_id).split(',')
            ids = []
            for id_str in id_strs:
                try:
                    ids.append(int(id_str.strip()))
                except ValueError:
                    return ApiResponse.bad_request(f"无效的文本块ID: {id_str}")

            deleted = []
            failed = []
            for cid in ids:
                try:
                    chunk = self.chunk_service.get_by_id(cid)
                    if not chunk:
                        failed.append(cid)
                        continue

                    # 获取相关信息
                    file_id = chunk.file_id
                    kb_id = chunk.knowledge_base_id

                    # 删除chunk记录
                    self.chunk_service.delete(cid)

                    # 更新文件的chunks_list
                    if file_id:
                        file_service = FileService()
                        file_obj = file_service.get_by_id(file_id)
                        if file_obj and file_obj.chunks_list:
                            if cid in file_obj.chunks_list:
                                file_obj.chunks_list.remove(cid)
                                file_service.update(file_id, file_obj)

                    # 更新知识库的chunks_list
                    if kb_id:
                        kb_service = KnowledgeBaseService()
                        kb = kb_service.get_by_id(kb_id)
                        if kb and kb.chunks_list:
                            if cid in kb.chunks_list:
                                kb.chunks_list.remove(cid)
                                kb_service.update(kb_id, kb)

                    deleted.append(cid)
                except Exception:
                    failed.append(cid)

            return ApiResponse.success("删除文本块完成", {"deleted": deleted, "failed": failed})
        except Exception as e:
            logger.error(f"删除文本块失败: {e}")
            return ApiResponse.internal_error("删除文本块失败")
