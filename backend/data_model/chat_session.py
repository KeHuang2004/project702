from utils.time_manager.time_manager import utc_now
from typing import Optional


class ChatSession:
    def __init__(self, title: str = "", created_at: Optional[str] = None):
        self.title = title
        self.created_at = created_at or utc_now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self):
        return {
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict):
        session = cls()
        session.title = data.get("title", "")
        session.created_at = data.get("created_at")
        session.updated_at = data.get("updated_at")
        return session


class ChatMessage:
    def __init__(
        self,
        session_id: int,
        role: str,
        content: str,
        message_id: Optional[int] = None,
        created_at: Optional[str] = None,
    ):
        self.message_id = message_id
        self.session_id = session_id
        self.role = role  # "user" or "assistant"
        self.content = content
        self.created_at = created_at or utc_now().isoformat()

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict):
        message = cls(
            session_id=data.get("session_id"),
            role=data.get("role"),
            content=data.get("content"),
        )
        message.message_id = data.get("message_id")
        message.created_at = data.get("created_at")
        return message
