"""聊天业务逻辑服务模块。

提供聊天会话及消息的增删改查与流式回复支持。
标题生成功能已从项目中移除。
"""

import json
import logging
import threading
from typing import Any, Dict, Generator, List

from utils.time_manager.time_manager import utc_now
from utils.tinydb_manager.tinydb_manager import TinyDBManager
from data_model.chat_session import ChatMessage, ChatSession
from utils.request_manager.exceptions import DatabaseError, NotFoundError
from config import Config

try:  # pragma: no cover - 容错导入
    from llm.API.generating import generating
    from llm.API.summary_generating import summary_generating
except Exception:  # pragma: no cover - 容错导入
    generating = None  # type: ignore
    summary_generating = None  # type: ignore


logger = logging.getLogger(__name__)


class ChatService:
    """聊天业务逻辑服务。"""

    def __init__(self, db_manager: TinyDBManager):
        self.db_manager = db_manager

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------
    def create_session(self, title: str = "") -> int:
        """创建新的会话。

        如果未提供标题，则使用固定文案“新会话”。
        """
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
                self.db_manager.update_session(session_id, {"updated_at": utc_now().isoformat()})
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
    # 流式发送
    # ------------------------------------------------------------------
    def send_message_stream(self, session_id: int, content: str, mode: str = "normal", file_id: int = None) -> Generator[str, None, None]:
        """发送消息并返回逐段响应数据。"""
        try:
            session = self.db_manager.get_session(session_id)
            if not session:
                raise NotFoundError("会话不存在", "session", session_id)

            logger.debug(
                "send_message_stream start: session=%s mode=%s file_id=%s content_len=%s",
                session_id,
                mode,
                file_id,
                len(content) if content is not None else 0,
            )

            self.add_message(session_id, "user", content)
            logger.debug("用户消息已保存: session=%s", session_id)

            assistant_content = ""
            if mode in ["summary", "literature"] and summary_generating is not None:
                # 使用新API
                # file_id 可能来自前端 localStorage（字符串），强制转换为 int
                original_file_id = file_id
                if file_id is not None and not isinstance(file_id, int):
                    try:
                        file_id = int(file_id)
                    except Exception:
                        logger.warning(
                            "file_id 无效，无法转换为 int: %s (原始值: %s)",
                            file_id,
                            original_file_id,
                        )
                        file_id = None
                prompt = self._build_prompt(mode, content, file_id)
                logger.info(
                    "开始流式生成 (新API): session=%s, mode=%s, file_id=%s",
                    session_id,
                    mode,
                    file_id,
                )
                logger.debug("生成Prompt长度: %s", len(prompt))
                for chunk in summary_generating(prompt):
                    assistant_content += chunk
                    yield json.dumps({"content": chunk})
            elif generating is not None:
                # 使用原API
                logger.info("开始流式生成: session=%s", session_id)
                for chunk in generating(content):
                    assistant_content += chunk
                    yield json.dumps({"content": chunk})
            else:
                assistant_content = f"Echo: {content}"
                yield json.dumps({"content": assistant_content})

            if assistant_content:
                self.add_message(session_id, "assistant", assistant_content)
                logger.debug("助手回复已保存: session=%s, reply_len=%s", session_id, len(assistant_content))

            logger.info("发送消息成功: %s", session_id)
        except NotFoundError:
            raise
        except Exception as exc:  # pragma: no cover - 数据层异常
            logger.exception("发送消息失败: %s", exc)
            raise DatabaseError("发送消息失败", "stream", "messages")

    def _build_prompt(self, mode: str, user_content: str, file_id: int = None) -> str:
        """构建prompt。"""
        if mode == "summary":
            if file_id is None:
                logger.debug("summary 模式但未提供 file_id，使用用户问题构建 prompt")
                return f"请对用户的问题进行回答：{user_content}"
            # 获取文件内容
            from services.file_service import FileService
            file_service = FileService()
            file_obj = file_service.get_by_id(file_id)
            if not file_obj:
                logger.warning("summary 模式：未找到文件，file_id=%s", file_id)
                return f"文件不存在。请对用户的问题进行回答：{user_content}"
            # 读取文件内容
            file_path = file_obj.file_path
            logger.debug("summary 模式：读取文件内容 file_id=%s file_path=%s", file_id, file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                logger.exception("读取文件失败：file_id=%s file_path=%s", file_id, file_path)
                file_content = "无法读取文件内容。"

            # 直接对文献进行要点提炼，不包含用户问题（因为用户问题就是要点提炼请求）
            prompt = f"请对以下文献进行要点提炼，提取关键信息、主要观点和核心内容：\n\n文献内容：\n{file_content}"
            logger.debug("summary prompt 构建完成，长度=%s", len(prompt))
            return prompt
        elif mode == "literature":
            # 暂时不实现
            return f"文献综述模式暂未实现。请对用户的问题进行回答：{user_content}"
        else:
            return user_content

