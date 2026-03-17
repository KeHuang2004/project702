import json
from typing import Any, Dict, List, Optional, Tuple

from utils.database__manager.base_model import BaseModel


class KnowledgeBase(BaseModel):
    """知识库模型类（已移除 generation_model 和 faiss_name）"""

    def __init__(self):
        super().__init__()
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.total_size: Optional[int] = None
        self.created_at: Optional[str] = None
        self.files_list: Optional[List[int]] = None
        self.chunks_list: Optional[List[int]] = None

    @staticmethod
    def _parse_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    @classmethod
    def get_table_name(cls) -> str:
        return "knowledge_bases"

    @classmethod
    def from_row(cls, row) -> "KnowledgeBase":
        kb = cls()
        kb.id = row["id"]
        kb.name = row["name"]
        kb.description = row["description"]
        kb.total_size = row["total_size"] or 0

        row_keys = set(row.keys()) if hasattr(row, "keys") else set()
        kb.files_list = (
            cls._parse_list(row["files_list"]) if "files_list" in row_keys else []
        )
        kb.chunks_list = (
            cls._parse_list(row["chunks_list"]) if "chunks_list" in row_keys else []
        )

        created_val = row["created_at"] if "created_at" in row_keys else None
        kb.created_at = str(created_val) if created_val is not None else None
        return kb

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBase":
        kb = cls()
        kb.id = data.get("id")
        kb.name = data.get("name")
        kb.description = data.get("description")
        kb.total_size = int(data.get("total_size", 0))

        kb.files_list = cls._parse_list(data.get("files_list"))
        kb.chunks_list = cls._parse_list(data.get("chunks_list"))

        created = data.get("created_at")
        kb.created_at = str(created) if created is not None else None
        return kb

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_size": self.total_size or 0,
            "created_at": self.created_at,
            "files_list": self.files_list or [],
            "chunks_list": self.chunks_list or [],
        }

    def get_insert_fields(self) -> Tuple[str, tuple]:
        """获取插入字段和值（与最新表结构保持 1:1 对齐）"""
        fields: list[str] = []
        values: list = []

        if self.name is not None:
            fields.append("name")
            values.append(self.name)
        if self.description is not None:
            fields.append("description")
            values.append(self.description)
        if self.total_size is not None:
            fields.append("total_size")
            values.append(self.total_size)

        if self.created_at is not None:
            fields.append("created_at")
            values.append(self.created_at)

        fields.append("files_list")
        values.append(json.dumps(self.files_list or []))

        fields.append("chunks_list")
        values.append(json.dumps(self.chunks_list or []))

        return ", ".join(fields), tuple(values)

    def get_update_fields(self) -> Tuple[str, tuple]:
        """获取更新字段和值"""
        fields: list[str] = []
        values: list = []

        if self.name is not None:
            fields.append("name = ?")
            values.append(self.name)
        if self.description is not None:
            fields.append("description = ?")
            values.append(self.description)
        if self.total_size is not None:
            fields.append("total_size = ?")
            values.append(self.total_size)

        if self.created_at is not None:
            fields.append("created_at = ?")
            values.append(self.created_at)

        if self.files_list is not None:
            fields.append("files_list = ?")
            values.append(json.dumps(self.files_list or []))

        if self.chunks_list is not None:
            fields.append("chunks_list = ?")
            values.append(json.dumps(self.chunks_list or []))

        return ", ".join(fields), tuple(values)

    def validate(self) -> list:
        errors = []

        if not self.name or not self.name.strip():
            errors.append("知识库名称不能为空")
        elif len(self.name.strip()) > 255:
            errors.append("知识库名称长度不能超过255个字符")

        # 嵌入模型由系统配置管理，不再在单个知识库对象层面校验

        if self.total_size is not None and self.total_size < 0:
            errors.append("知识库大小不能为负数")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def __str__(self):
        return f"KnowledgeBase(id={self.id}, name='{self.name}')"

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name='{self.name}')>"
