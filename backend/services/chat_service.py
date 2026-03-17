"""聊天业务逻辑服务模块。

提供聊天会话及消息的增删改查，并在服务层内直接完成模型调用。
当前先实现普通模式的远程模型调用，后端统一返回非流式结果。
"""

import logging
import time
from typing import Any, Dict, List

import requests

from config import Config
from data_model.chat_session import ChatMessage, ChatSession
from data_model.chunk import Chunk
from data_model.file import File
from services.knowledge_base_service import KnowledgeBaseService
from utils.request_manager.exceptions import (
    ConfigurationError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from utils.time_manager.time_manager import utc_now
from utils.database__manager.base_model import BaseService
from utils.tinydb_manager.tinydb_manager import TinyDBManager


logger = logging.getLogger(__name__)


class ChatService:
    """聊天业务逻辑服务。"""

    MODE_NORMAL = "normal"
    MODE_RAG = "rag"
    MODE_LITERATURE_REVIEW = "literature-review"
    MODE_SUMMARY = "summary"
    MODE_LIST_CONTENTS = "list-contents"
    SUPPORTED_MODES = {
        MODE_NORMAL,
        MODE_RAG,
        MODE_LITERATURE_REVIEW,
        MODE_SUMMARY,
        MODE_LIST_CONTENTS,
    }

    def __init__(self, db_manager: TinyDBManager):
        self.db_manager = db_manager
        self.request_timeout = int(getattr(Config, "llm_request_timeout", Config.API_TIMEOUT))
        self.request_retries = int(getattr(Config, "llm_request_retries", 1))
        self.file_store = BaseService(File)
        self.chunk_store = BaseService(Chunk)
        self.kb_service = KnowledgeBaseService()

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------
    def create_session(self, title: str = "") -> int:
        """创建新的会话。"""
        try:
            session_title = title.strip() or "新会话"
            session = ChatSession(title=session_title)
            session_id = self.db_manager.create_session(session.to_dict())
            logger.info("创建会话成功: %s", session_id)
            return session_id
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("创建会话失败: %s", exc)
            raise DatabaseError("创建会话失败", "create", "sessions")

    def get_session(self, session_id: int) -> Dict[str, Any]:
        """获取单个会话。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            session["id"] = session_id
            return session
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("获取会话失败: %s", exc)
            raise DatabaseError("获取会话失败", "read", "sessions")

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取全部会话列表。"""
        try:
            sessions = self.db_manager.get_all_sessions()
            if not sessions:
                logger.info("没有找到任何会话")
                return []
            return sessions
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("获取会话列表失败: %s", exc)
            return []

    def update_session_title(self, session_id: int, title: str) -> Dict[str, Any]:
        """更新会话标题。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            update_data = {"title": title, "updated_at": utc_now().isoformat()}
            updated_session = self.db_manager.update_session(session_id, update_data)
            if updated_session:
                updated_session["id"] = session_id

            logger.info("更新会话标题成功: %s", session_id)
            return updated_session
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("更新会话标题失败: %s", exc)
            raise DatabaseError("更新会话标题失败", "update", "sessions")

    def delete_session(self, session_id: int) -> bool:
        """删除会话。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            self.db_manager.delete_session(session_id)
            logger.info("删除会话成功: %s", session_id)
            return True
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("删除会话失败: %s", exc)
            raise DatabaseError("删除会话失败", "delete", "sessions")

    # ------------------------------------------------------------------
    # 消息管理
    # ------------------------------------------------------------------
    def get_session_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """获取会话中所有消息。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            messages = self.db_manager.get_session_messages(session_id)
            messages.sort(key=lambda item: item.get("id", 0))
            return messages
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("获取会话消息失败: %s", exc)
            raise DatabaseError("获取会话消息失败", "read", "messages")

    def add_message(self, session_id: int, role: str, content: str) -> int:
        """新增一条聊天消息。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            message = ChatMessage(session_id=session_id, role=role, content=content)
            message_id = self.db_manager.add_message(message.to_dict())

            try:
                self.db_manager.update_session(
                    session_id,
                    {"updated_at": utc_now().isoformat()},
                )
            except Exception as exc:  # pragma: no cover - 非关键路径
                logger.warning("更新会话更新时间失败: %s (%s)", session_id, exc)

            logger.info("添加消息成功: %s - %s", session_id, role)
            return message_id
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.error("添加消息失败: %s", exc)
            raise DatabaseError("添加消息失败", "create", "messages")

    # ------------------------------------------------------------------
    # 发送消息（非流式）
    # ------------------------------------------------------------------
    def send_message(
        self,
        session_id: int,
        query: str,
        mode: str = MODE_NORMAL,
        file_id: int = None,
        kb_id: int = None,
    ) -> Dict[str, Any]:
        """发送消息并返回简单 JSON 结果。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            normalized_query = str(query or "").strip()
            if not normalized_query:
                raise ValidationError("消息内容不能为空", field="query")

            normalized_mode = (mode or self.MODE_NORMAL).strip().lower()
            if normalized_mode not in self.SUPPORTED_MODES:
                raise ValidationError(
                    f"不支持的聊天模式: {normalized_mode}",
                    field="mode",
                    value=normalized_mode,
                )

            user_message_id = self.add_message(session_id, "user", normalized_query)
            assistant_content = self._dispatch_mode(
                normalized_mode,
                normalized_query,
                session_id,
                file_id=file_id,
                kb_id=kb_id,
            )
            assistant_message_id = self.add_message(session_id, "assistant", assistant_content)

            messages = self.get_session_messages(session_id)
            assistant_message = messages[-1] if messages else None

            logger.info("发送消息成功: session=%s mode=%s", session_id, normalized_mode)
            return {
                "session_id": session_id,
                "mode": normalized_mode,
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
                "reply": assistant_message,
            }
        except NotFoundError:
            raise
        except ValidationError:
            raise
        except ConfigurationError:
            raise
        except ExternalServiceError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.exception("发送消息失败: %s", exc)
            raise DatabaseError("发送消息失败", "create", "messages")

    def _dispatch_mode(
        self,
        mode: str,
        query: str,
        session_id: int,
        file_id: int = None,
        kb_id: int = None,
    ) -> str:
        if mode == self.MODE_NORMAL:
            return self._handle_normal_mode(query, session_id)
        if mode == self.MODE_RAG:
            return self._handle_rag_mode(query, session_id, kb_id=kb_id)
        if mode == self.MODE_LITERATURE_REVIEW:
            return self._handle_literature_review_mode(query, session_id, kb_id=kb_id)
        if mode == self.MODE_SUMMARY:
            return self._handle_summary_mode(query, session_id, file_id=file_id)
        if mode == self.MODE_LIST_CONTENTS:
            return self._handle_list_contents_mode(query, session_id)
        raise ValidationError(f"不支持的聊天模式: {mode}", field="mode", value=mode)

    def _handle_normal_mode(self, query: str, session_id: int) -> str:
        """普通模式：直接请求远程模型并返回完整文本。"""
        logger.info("普通模式调用开始: session=%s", session_id)
        if Config.llm_mode != "remote":
            raise ConfigurationError(
                "当前仅支持 remote 模式的普通对话",
                config_key="llm_mode",
                config_value=Config.llm_mode,
            )

        messages = self._build_remote_messages(session_id)
        return self._request_remote_completion(messages)

    def _handle_rag_mode(self, query: str, session_id: int, kb_id: int = None) -> str:
        """RAG 模式：关键词提炼 -> 检索 -> 基于知识重答。"""
        logger.info("RAG 模式调用开始: session=%s kb_id=%s", session_id, kb_id)
        if Config.llm_mode != "remote":
            raise ConfigurationError(
                "当前仅支持 remote 模式的 RAG 对话",
                config_key="llm_mode",
                config_value=Config.llm_mode,
            )

        normalized_kb_id = self._normalize_kb_id(kb_id)
        keywords = self._extract_rag_keywords(query)
        retrieval_query = " ".join(keywords).strip() if keywords else query
        contexts = self._retrieve_kb_context(
            normalized_kb_id,
            retrieval_query,
            top_k=3,
            threshold=0.001,
        )
        prompt = self._build_rag_answer_prompt(query, contexts)
        messages = [{"role": "user", "content": prompt}]
        return self._request_remote_completion(messages)

    def _handle_literature_review_mode(self, query: str, session_id: int, kb_id: int = None) -> str:
        """文献综述模式：关键词提炼 -> 检索文献 -> 基于文献生成综述。"""
        logger.info("Literature-review 模式调用开始: session=%s kb_id=%s", session_id, kb_id)
        if Config.llm_mode != "remote":
            raise ConfigurationError(
                "当前仅支持 remote 模式的文献综述",
                config_key="llm_mode",
                config_value=Config.llm_mode,
            )

        normalized_kb_id = self._normalize_kb_id(kb_id)
        keywords = self._extract_rag_keywords(query)
        retrieval_query = " ".join(keywords).strip() if keywords else query
        contexts = self._retrieve_kb_context(
            normalized_kb_id,
            retrieval_query,
            top_k=10,
            threshold=0.001,
        )
        if not contexts:
            return "未在所选知识库中检索到相关文献，无法基于给定文献生成综述。请尝试调整问题描述或更换知识库。"

        prompt = self._build_literature_review_prompt(query, contexts)
        messages = [{"role": "user", "content": prompt}]
        return self._request_remote_completion(messages)

    def _handle_summary_mode(self, query: str, session_id: int, file_id: int = None) -> str:
        """要点提炼模式：按文件 chunks 拼接文章内容并请求模型。"""
        logger.info("Summary 模式调用开始: session=%s file_id=%s", session_id, file_id)
        if Config.llm_mode != "remote":
            raise ConfigurationError(
                "当前仅支持 remote 模式的要点提炼",
                config_key="llm_mode",
                config_value=Config.llm_mode,
            )

        normalized_file_id = self._normalize_file_id(file_id)
        file_obj = self._get_summary_file(normalized_file_id)
        article_content = self._build_summary_content(file_obj)
        prompt = self._build_summary_prompt(
            query,
            file_obj.filename or "未命名文章",
            article_content,
        )
        messages = [{"role": "user", "content": prompt}]
        return self._request_remote_completion(messages)

    def _handle_list_contents_mode(self, query: str, session_id: int) -> str:
        """目录提纲模式实现占位。"""
        logger.info("List-contents 模式占位逻辑: session=%s", session_id)
        return ""

    def _build_remote_messages(self, session_id: int) -> List[Dict[str, str]]:
        """构造发送给远程模型的历史消息。"""
        history = self.get_session_messages(session_id)
        messages: List[Dict[str, str]] = []
        for item in history:
            role = (item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant", "system"}:
                continue
            if not content:
                continue
            messages.append({"role": role, "content": content})
        return messages

    def _normalize_file_id(self, file_id: int) -> int:
        try:
            normalized_file_id = int(file_id)
        except (TypeError, ValueError):
            raise ValidationError("要点提炼模式缺少有效的 file_id", field="file_id", value=file_id)

        if normalized_file_id <= 0:
            raise ValidationError("file_id 必须是正整数", field="file_id", value=file_id)
        return normalized_file_id

    def _normalize_kb_id(self, kb_id: int) -> int:
        try:
            normalized_kb_id = int(kb_id)
        except (TypeError, ValueError):
            raise ValidationError("RAG 模式缺少有效的 kb_id", field="kb_id", value=kb_id)

        if normalized_kb_id <= 0:
            raise ValidationError("kb_id 必须是正整数", field="kb_id", value=kb_id)
        return normalized_kb_id

    def _extract_rag_keywords(self, query: str) -> List[str]:
        keyword_prompt = (
            "你现在是一个关键词提炼专家，我需要你根据用户询问的问题"
            f"{query}"
            "提炼出用户核心想要询问的关键词，然后给我直接回复出来所有你提炼出来的关键词，"
            "最多5个关键词，每个最长5个字。"
            "示例: 请给我介绍xxxx，回复:xxxxx"
        )
        try:
            reply = self._request_remote_completion([{"role": "user", "content": keyword_prompt}])
            return self._parse_keywords(reply)
        except ExternalServiceError as exc:
            # 关键词提炼失败时降级：直接使用原 query 继续检索，避免整次 RAG 失败
            logger.warning("关键词提炼失败，降级使用原问题检索: %s", exc)
            return []

    def _parse_keywords(self, text: str) -> List[str]:
        raw = str(text or "").strip()
        if not raw:
            return []

        normalized = (
            raw.replace("，", " ")
            .replace("、", " ")
            .replace("；", " ")
            .replace(";", " ")
            .replace("\n", " ")
            .replace("\t", " ")
        )
        tokens = [t.strip() for t in normalized.split(" ") if t.strip()]

        seen = set()
        keywords: List[str] = []
        for token in tokens:
            # 处理可能带编号的情况：1.关键词
            if "." in token and token.split(".", 1)[0].isdigit():
                token = token.split(".", 1)[1].strip()
            token = token.strip("'\"[](){}:：")
            if not token:
                continue
            if len(token) > 5:
                token = token[:5]
            if token in seen:
                continue
            seen.add(token)
            keywords.append(token)
            if len(keywords) >= 5:
                break
        return keywords

    def _retrieve_kb_context(
        self,
        kb_id: int,
        retrieval_query: str,
        top_k: int = 3,
        threshold: float = 0.001,
    ) -> List[Dict[str, str]]:
        retrieved = self.kb_service.retrieve_by_cosine(
            kb_id=kb_id,
            query=retrieval_query,
            top_k=top_k,
            threshold=threshold,
        )
        rows = retrieved.get("results", []) if isinstance(retrieved, dict) else []
        contexts: List[Dict[str, str]] = []
        file_name_cache: Dict[int, str] = {}

        for row in rows:
            chunk_id = row.get("chunk_id")
            if chunk_id is None:
                continue
            chunk_obj = self.chunk_store.get_by_id(int(chunk_id))
            if not chunk_obj:
                continue

            file_id = int(chunk_obj.file_id or 0)
            if file_id not in file_name_cache:
                file_obj = self.file_store.get_by_id(file_id) if file_id > 0 else None
                file_name_cache[file_id] = (file_obj.filename if file_obj else "未知文件") or "未知文件"

            chunk_text = str(chunk_obj.chunk_text or "").strip()
            if not chunk_text:
                continue

            contexts.append({
                "chunk_text": chunk_text,
                "file_name": file_name_cache[file_id],
            })
        return contexts

    def _build_rag_answer_prompt(self, original_query: str, contexts: List[Dict[str, str]]) -> str:
        if contexts:
            knowledge_lines = []
            for item in contexts:
                knowledge_lines.append(
                    f"{{{{文本块: {item['chunk_text']}, 所属文件名: {item['file_name']}}}}}"
                )
            knowledge_text = "\n".join(knowledge_lines)
        else:
            knowledge_text = "未检索到相关知识。"

        return (
            "你现在是一个总结专家，"
            f"用户之前希望询问：{original_query}。"
            "通过已有的知识库，有关联的知识如下：\n"
            f"{knowledge_text}\n"
            "现在需要你结合已有的知识，重新回答用户的问题，并且在相关引用的知识，需要加上引用，"
            "在最后面给出知识列表，列出所有引用文件的文件name即可。"
        )

    def _build_literature_review_prompt(self, original_query: str, contexts: List[Dict[str, str]]) -> str:
        literature_lines = []
        for index, item in enumerate(contexts, start=1):
            title = str(item.get("file_name") or f"文献{index}").strip() or f"文献{index}"
            chunk_text = str(item.get("chunk_text") or "").strip()
            if not chunk_text:
                continue
            literature_lines.append(
                f"[{index}] 文献标题：《{title}》\n文献内容：{chunk_text}"
            )

        literature_text = "\n\n".join(literature_lines) if literature_lines else "未检索到相关文献内容。"

        return (
            "请基于以下文献内容及其对应的文献名字，基于用户的要求，写一篇综述。\n"
            "1. 依照学术论文的格式写作。\n"
            "2. 需要将这些提供的论文在正文中以 [序号] 形式引用，并列在文章末尾。\n"
            "3. 文章内容必须严格基于所给文献事实，不得编造。\n"
            "4. 条理清晰，语言朴实。\n"
            "5. 如果文献未提供作者、年份、期刊等元数据，不得补写这些信息，可仅使用《文献标题》或 [序号] 引用。\n"
            f"用户要求：{original_query}\n\n"
            "相关文献内容：\n"
            f"{literature_text}\n\n"
            "输出要求：\n"
            "1. 请输出题目、摘要、正文、结论、参考文献等结构。\n"
            "2. 参考文献按 [序号]《文献标题》 的格式列出。\n"
            "3. 若某一部分无法由给定文献支撑，请明确说明“给定文献未涉及”，不要自行补充。"
        )

    def _get_summary_file(self, file_id: int) -> File:
        file_obj = self.file_store.get_by_id(file_id)
        if not file_obj:
            raise NotFoundError("文件不存在", "file", file_id)
        return file_obj

    def _build_summary_content(self, file_obj: File) -> str:
        chunk_ids = list(file_obj.chunks_list or [])
        if not chunk_ids:
            raise ValidationError("该文件还没有可用的文本块", field="file_id", value=file_obj.id)

        chunk_texts: List[str] = []
        for chunk_id in chunk_ids:
            chunk_obj = self.chunk_store.get_by_id(int(chunk_id))
            if not chunk_obj:
                continue
            if int(chunk_obj.file_id or 0) != int(file_obj.id or 0):
                continue
            text = str(chunk_obj.chunk_text or "").strip()
            if not text:
                continue
            chunk_texts.append(
                f"[文本块 {chunk_obj.chunk_index if chunk_obj.chunk_index is not None else chunk_obj.id}]\n{text}"
            )

        if not chunk_texts:
            raise ValidationError("未能读取到该文件的有效文本块内容", field="file_id", value=file_obj.id)

        return "\n\n".join(chunk_texts)

    def _build_summary_prompt(self, query: str, filename: str, content: str) -> str:
        return (
            f"用户当前请求是：{query}\n\n"
            f"这是我现有的一篇文章，文章名字是《{filename}》。"
            "下面会有很多我已经拆分好了的文本块，有部分重叠并且可能存在乱码，需要你简单注意这个问题。"
            "我需要你根据我给你的这些文章内容，做一个文章的重要内容要点的提炼。"
            "请直接输出结构清晰的提炼结果，不要解释你的处理过程。\n\n"
            f"{content}"
        )

    def _request_remote_completion(self, messages: List[Dict[str, str]]) -> str:
        """向远程模型发起一次非流式请求。"""
        api_url = str(Config.llm_api_url or "").strip()
        api_key = str(Config.llm_api_key or "").strip()
        model = str(Config.llm_model or "").strip()

        if not api_url:
            raise ConfigurationError("未配置远程模型地址", config_key="llm_api_url")
        if not api_key:
            raise ConfigurationError("未配置远程模型 API Key", config_key="llm_api_key")
        if not model:
            raise ConfigurationError("未配置远程模型名称", config_key="llm_model")
        if not messages:
            raise ValidationError("远程模型消息不能为空", field="messages")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        max_attempts = max(1, self.request_retries + 1)
        response = None
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.request_timeout,
                )
                break
            except requests.Timeout as exc:
                last_exception = exc
                logger.warning(
                    "远程模型请求超时（第 %s/%s 次）: %s",
                    attempt,
                    max_attempts,
                    exc,
                )
            except requests.RequestException as exc:
                last_exception = exc
                logger.warning(
                    "远程模型请求异常（第 %s/%s 次）: %s",
                    attempt,
                    max_attempts,
                    exc,
                )

            if attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 3))

        if response is None:
            logger.error("远程模型请求失败（重试后仍失败）: %s", last_exception)
            raise ExternalServiceError("远程模型请求失败", "remote-llm")

        if response.status_code >= 400:
            logger.error(
                "远程模型返回错误: status=%s body=%s",
                response.status_code,
                response.text[:1000],
            )
            raise ExternalServiceError(
                "远程模型返回错误",
                "remote-llm",
                response.status_code,
            )

        try:
            result = response.json()
        except ValueError as exc:
            logger.error("远程模型响应不是合法 JSON: %s", exc)
            raise ExternalServiceError("远程模型响应解析失败", "remote-llm")

        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(reply, str) or not reply.strip():
            logger.error("远程模型响应缺少内容: %s", result)
            raise ExternalServiceError("远程模型未返回有效内容", "remote-llm")

        return reply.strip()
