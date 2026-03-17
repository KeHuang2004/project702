import json
from typing import Any, Dict, Optional, Tuple

from utils.database__manager.base_model import BaseModel


class Chunk(BaseModel):
    """文本块模型类（与 schema 同步：不再包含 faiss_vector_id）"""

    def __init__(self):
        super().__init__()
        self.file_id: Optional[int] = None
        self.knowledge_base_id: Optional[int] = None
        self.chunk_text: Optional[str] = None
        self.chunk_index: Optional[int] = None
        self.start_position: Optional[int] = None
        self.end_position: Optional[int] = None
        self.status: Optional[str] = None
        self.created_at: Optional[str] = None
        self.embed_at: Optional[str] = None

    @classmethod
    def get_table_name(cls) -> str:
        return "chunks"

    @classmethod
    def from_row(cls, row) -> "Chunk":
        chunk = cls()
        chunk.id = row["id"]
        chunk.file_id = row["file_id"]
        chunk.knowledge_base_id = row["knowledge_base_id"]
        chunk.chunk_text = row["chunk_text"]
        chunk.chunk_index = row["chunk_index"]
        chunk.start_position = row["start_position"]
        chunk.end_position = row["end_position"]
        # chunk.faiss_vector_id = row["faiss_vector_id"]  # 已移除
        # chunk.metadata = row["metadata"]  # 已移除
        # sqlite3.Row 无 get 方法，使用 keys 检查
        row_keys = set(row.keys()) if hasattr(row, "keys") else set()
        chunk.status = row["status"] if "status" in row_keys else None
        created_val = row["created_at"] if "created_at" in row_keys else None
        chunk.created_at = str(created_val) if created_val is not None else None
        embed_val = row["embed_at"] if "embed_at" in row_keys else None
        chunk.embed_at = str(embed_val) if embed_val is not None else None
        return chunk

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        chunk = cls()
        chunk.id = data.get("id")
        chunk.file_id = data.get("file_id")
        chunk.knowledge_base_id = data.get("knowledge_base_id")
        chunk.chunk_text = data.get("chunk_text")
        chunk.chunk_index = data.get("chunk_index")
        chunk.start_position = data.get("start_position")
        chunk.end_position = data.get("end_position")
        # chunk.faiss_vector_id = data.get("faiss_vector_id")  # 已移除

        created = data.get("created_at")
        chunk.created_at = str(created) if created is not None else None

        status = data.get("status")
        chunk.status = str(status) if status is not None else None

        embed = data.get("embed_at")
        chunk.embed_at = str(embed) if embed is not None else None

        return chunk

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "file_id": self.file_id,
            "knowledge_base_id": self.knowledge_base_id,
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index,
            "start_position": self.start_position,
            "end_position": self.end_position,
            # "faiss_vector_id": self.faiss_vector_id,  # 已移除
            "status": self.status,
            "created_at": self.created_at,
            "embed_at": self.embed_at,
        }

        return result

    def get_insert_fields(self) -> Tuple[str, tuple]:
        fields, values = [], []

        if self.file_id is not None:
            fields.append("file_id")
            values.append(self.file_id)

        if self.knowledge_base_id is not None:
            fields.append("knowledge_base_id")
            values.append(self.knowledge_base_id)

        if self.chunk_text is not None:
            fields.append("chunk_text")
            values.append(self.chunk_text)

        if self.chunk_index is not None:
            fields.append("chunk_index")
            values.append(self.chunk_index)

        if self.start_position is not None:
            fields.append("start_position")
            values.append(self.start_position)

        if self.end_position is not None:
            fields.append("end_position")
            values.append(self.end_position)

        if self.status is not None:
            fields.append("status")
            values.append(self.status)

        if self.created_at is not None:
            fields.append("created_at")
            values.append(self.created_at)

        if self.embed_at is not None:
            fields.append("embed_at")
            values.append(self.embed_at)

        return ", ".join(fields), tuple(values)

    def get_update_fields(self) -> Tuple[str, tuple]:
        fields, values = [], []

        if self.file_id is not None:
            fields.append("file_id = ?")
            values.append(self.file_id)

        if self.knowledge_base_id is not None:
            fields.append("knowledge_base_id = ?")
            values.append(self.knowledge_base_id)

        if self.chunk_text is not None:
            fields.append("chunk_text = ?")
            values.append(self.chunk_text)

        if self.chunk_index is not None:
            fields.append("chunk_index = ?")
            values.append(self.chunk_index)

        if self.start_position is not None:
            fields.append("start_position = ?")
            values.append(self.start_position)

        if self.end_position is not None:
            fields.append("end_position = ?")
            values.append(self.end_position)

        if self.status is not None:
            fields.append("status = ?")
            values.append(self.status)

        if self.created_at is not None:
            fields.append("created_at = ?")
            values.append(self.created_at)

        if self.embed_at is not None:
            fields.append("embed_at = ?")
            values.append(self.embed_at)

        return ", ".join(fields), tuple(values)

    def validate(self) -> list:
        errors = []

        if self.file_id is None:
            errors.append("文件ID不能为空")
        elif not isinstance(self.file_id, int) or self.file_id <= 0:
            errors.append("文件ID必须是正整数")

        if self.knowledge_base_id is None:
            errors.append("知识库ID不能为空")
        elif not isinstance(self.knowledge_base_id, int) or self.knowledge_base_id <= 0:
            errors.append("知识库ID必须是正整数")

        if not self.chunk_text or not str(self.chunk_text).strip():
            errors.append("文本块内容不能为空")

        if self.chunk_index is None:
            errors.append("文本块索引不能为空")
        elif not isinstance(self.chunk_index, int) or self.chunk_index < 0:
            errors.append("文本块索引必须是非负整数")

        if self.start_position is not None and self.start_position < 0:
            errors.append("起始位置不能为负数")

        if self.end_position is not None and self.end_position < 0:
            errors.append("结束位置不能为负数")

        if (
            self.start_position is not None
            and self.end_position is not None
            and self.start_position > self.end_position
        ):
            errors.append("起始位置不能大于结束位置")

        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def get_text_length(self) -> int:
        return len(self.chunk_text) if self.chunk_text else 0

    def get_text_preview(self, max_length: int = 100) -> str:
        if not self.chunk_text:
            return ""
        return self.chunk_text if len(self.chunk_text) <= max_length else self.chunk_text[:max_length] + "..."

    def __str__(self):
        preview = self.get_text_preview(50)
        return f"Chunk(id={self.id}, index={self.chunk_index}, text='{preview}')"

    def __repr__(self):
        return f"<Chunk(id={self.id}, file_id={self.file_id}, knowledge_base_id={self.knowledge_base_id}, chunk_index={self.chunk_index})>"
