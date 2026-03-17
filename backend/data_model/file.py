import json
from typing import Any, Dict, Optional, Tuple, List

from utils.database__manager.base_model import BaseModel


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


class File(BaseModel):
    """文件模型类（精简版，仅保留基础字段 + chunks_list）"""

    STATUS_PENDING = "pending"
    STATUS_UPLOADING = "uploading"
    STATUS_UPLOADED = "uploaded"
    STATUS_SPLITTING = "splitting"
    STATUS_RE_SPLITTING = "re-splitting"
    STATUS_SPLITTED = "splitted"
    STATUS_PROCESSING = "processing"
    STATUS_UPLOADING_PENDING = "uploading_pending"
    STATUS_COMPLETED = "completed"
    STATUS_EMBEDDING = "embedding"
    STATUS_EMBEDDED = "embedded"
    STATUS_FAILED = "failed"
    STATUS_FILE_NOT_FOUND = "file_not_found"

    VALID_STATUSES = [
        STATUS_PENDING,
        STATUS_UPLOADING,
        STATUS_UPLOADED,
        STATUS_SPLITTING,
        STATUS_RE_SPLITTING,
        STATUS_SPLITTED,
        STATUS_PROCESSING,
        STATUS_UPLOADING_PENDING,
        STATUS_COMPLETED,
        STATUS_EMBEDDING,
        STATUS_EMBEDDED,
        STATUS_FAILED,
        STATUS_FILE_NOT_FOUND,
    ]

    def __init__(self):
        super().__init__()
        self.knowledge_base_id: Optional[int] = None
        self.filename: Optional[str] = None
        self.file_path: Optional[str] = None
        self.file_type: Optional[str] = None
        self.file_size: Optional[int] = None
        self.chunks_list: List[int] = []
        self.status: str = self.STATUS_PENDING
        self.chunk_length: Optional[int] = None
        self.overlap_count: Optional[int] = None
        self.segmentation_strategy: Optional[str] = None
        self.upload_at: Optional[str] = None

    @classmethod
    def get_table_name(cls) -> str:
        """获取表名"""
        return "files"

    @classmethod
    def from_row(cls, row) -> "File":
        """从数据库行创建对象"""
        file_obj = cls()
        file_obj.id = row["id"]
        file_obj.knowledge_base_id = row["knowledge_base_id"]
        file_obj.filename = row["filename"]
        file_obj.file_path = row["file_path"]
        file_obj.file_type = row["file_type"]
        file_obj.file_size = row["file_size"]
        row_keys = set(row.keys()) if hasattr(row, "keys") else set()
        file_obj.chunks_list = _parse_list(row["chunks_list"]) if "chunks_list" in row_keys else []
        file_obj.status = row["status"] or cls.STATUS_PENDING
        file_obj.chunk_length = row["chunk_length"] if "chunk_length" in row_keys else None
        file_obj.overlap_count = row["overlap_count"] if "overlap_count" in row_keys else None
        file_obj.segmentation_strategy = row["segmentation_strategy"] if "segmentation_strategy" in row_keys else None
        file_obj.upload_at = str(row["upload_at"]) if "upload_at" in row_keys and row["upload_at"] is not None else None

        return file_obj

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "File":
        """从字典创建对象"""
        file_obj = cls()
        file_obj.id = data.get("id")
        file_obj.knowledge_base_id = data.get("knowledge_base_id")
        file_obj.filename = data.get("filename")
        file_obj.file_path = data.get("file_path")
        file_obj.file_type = data.get("file_type")
        file_obj.file_size = data.get("file_size")
        file_obj.chunks_list = _parse_list(data.get("chunks_list"))
        file_obj.status = data.get("status", cls.STATUS_PENDING)
        file_obj.chunk_length = data.get("chunk_length")
        file_obj.overlap_count = data.get("overlap_count")
        file_obj.segmentation_strategy = data.get("segmentation_strategy")
        upload_val = data.get("upload_at")
        file_obj.upload_at = str(upload_val) if upload_val is not None else None

        return file_obj

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_length": self.chunk_length,
            "overlap_count": self.overlap_count,
            "segmentation_strategy": self.segmentation_strategy,
            "status": self.status,
            "upload_at": self.upload_at,
            "chunks_list": self.chunks_list or [],
        }

    def get_insert_fields(self) -> Tuple[str, tuple]:
        """获取插入字段和值"""
        fields = []
        values = []

        if self.knowledge_base_id is not None:
            fields.append("knowledge_base_id")
            values.append(self.knowledge_base_id)

        if self.filename is not None:
            fields.append("filename")
            values.append(self.filename)

        if self.file_path is not None:
            fields.append("file_path")
            values.append(self.file_path)

        if self.file_type is not None:
            fields.append("file_type")
            values.append(self.file_type)

        if self.file_size is not None:
            fields.append("file_size")
            values.append(self.file_size)

        if self.chunk_length is not None:
            fields.append("chunk_length")
            values.append(self.chunk_length)

        if self.overlap_count is not None:
            fields.append("overlap_count")
            values.append(self.overlap_count)

        if self.segmentation_strategy is not None:
            fields.append("segmentation_strategy")
            values.append(self.segmentation_strategy)

        if self.upload_at is not None:
            fields.append("upload_at")
            values.append(self.upload_at)

        fields.append("chunks_list")
        values.append(json.dumps(self.chunks_list or []))
        if self.status is not None:
            fields.append("status")
            values.append(self.status)

        return ", ".join(fields), tuple(values)

    def get_update_fields(self) -> Tuple[str, tuple]:
        """获取更新字段和值"""
        fields = []
        values = []

        if self.knowledge_base_id is not None:
            fields.append("knowledge_base_id = ?")
            values.append(self.knowledge_base_id)

        if self.filename is not None:
            fields.append("filename = ?")
            values.append(self.filename)

        if self.file_path is not None:
            fields.append("file_path = ?")
            values.append(self.file_path)

        if self.file_type is not None:
            fields.append("file_type = ?")
            values.append(self.file_type)

        if self.file_size is not None:
            fields.append("file_size = ?")
            values.append(self.file_size)

        if self.chunks_list is not None:
            fields.append("chunks_list = ?")
            values.append(json.dumps(self.chunks_list or []))

        if self.status is not None:
            fields.append("status = ?")
            values.append(self.status)

        if self.chunk_length is not None:
            fields.append("chunk_length = ?")
            values.append(self.chunk_length)

        if self.overlap_count is not None:
            fields.append("overlap_count = ?")
            values.append(self.overlap_count)

        if self.segmentation_strategy is not None:
            fields.append("segmentation_strategy = ?")
            values.append(self.segmentation_strategy)

        if self.upload_at is not None:
            fields.append("upload_at = ?")
            values.append(self.upload_at)

        return ", ".join(fields), tuple(values)

    def validate(self) -> list:
        """验证数据有效性"""
        errors = []

        if self.knowledge_base_id is None:
            errors.append("知识库ID不能为空")
        elif not isinstance(self.knowledge_base_id, int) or self.knowledge_base_id <= 0:
            errors.append("知识库ID必须是正整数")

        if not self.filename or not self.filename.strip():
            errors.append("文件名不能为空")

        if not self.file_path or not self.file_path.strip():
            errors.append("文件路径不能为空")

        if self.file_size is not None and self.file_size < 0:
            errors.append("文件大小不能为负数")

        if self.status not in self.VALID_STATUSES:
            errors.append(f"无效的文件状态: {self.status}")

        return errors

    def is_valid(self) -> bool:
        """检查数据是否有效"""
        return len(self.validate()) == 0

    def is_processing_completed(self) -> bool:
        """检查文件是否处理完成"""
        return self.status == self.STATUS_COMPLETED

    def is_processing_failed(self) -> bool:
        """检查文件处理是否失败"""
        return self.status in [self.STATUS_FAILED, self.STATUS_FILE_NOT_FOUND]

    def can_be_processed(self) -> bool:
        """检查文件是否可以被处理"""
        return self.status in [self.STATUS_PENDING, self.STATUS_UPLOADED, self.STATUS_FAILED]

    def mark_as_processing(self):
        """标记文件为处理中"""
        self.status = self.STATUS_PROCESSING

    def mark_as_completed(self):
        """标记文件处理完成"""
        self.status = self.STATUS_COMPLETED

    def mark_as_failed(self, error_message: str = None):
        """标记文件处理失败"""
        self.status = self.STATUS_FAILED

    def mark_as_file_not_found(self):
        """标记文件未找到"""
        self.status = self.STATUS_FILE_NOT_FOUND

    def get_status_display(self) -> str:
        """获取状态的中文显示"""
        status_map = {
            self.STATUS_PENDING: "待处理",
            self.STATUS_PROCESSING: "处理中",
            self.STATUS_UPLOADING_PENDING: "上传排队",
            self.STATUS_COMPLETED: "已完成",
            self.STATUS_EMBEDDING: "嵌入中",
            self.STATUS_EMBEDDED: "已嵌入",
            self.STATUS_FAILED: "处理失败",
            self.STATUS_FILE_NOT_FOUND: "文件不存在",
        }
        return status_map.get(self.status, "未知状态")

    def __str__(self):
        return f"File(id={self.id}, filename='{self.filename}', status='{self.status}')"

    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', knowledge_base_id={self.knowledge_base_id}, status='{self.status}')>"
