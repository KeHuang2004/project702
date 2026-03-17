"""
工具模块

包含异常处理、响应格式、验证器、文件处理等工具类
"""

from .time_manager.time_manager import (
    format_datetime,
    get_relative_time,
)
from .request_manager.exceptions import (
    BaseKnowledgeBaseError,
    DatabaseError,
    FileProcessingError,
    NotFoundError,
    ValidationError,
)
from .file_manager.file_manager import (
    calculate_file_hash,
    format_file_size,
    get_file_extension,
    get_file_type,
    is_allowed_file_type,
    save_uploaded_file,
)
from .request_manager.response import ApiResponse


__all__ = [
    # 异常类
    "BaseKnowledgeBaseError",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "FileProcessingError",
    # 响应工具
    "ApiResponse",
    # 文件工具
    "save_uploaded_file",
    "get_file_type",
    "calculate_file_hash",
    "get_file_extension",
    "is_allowed_file_type",
    "format_file_size",
    # 日期工具
    "format_datetime",
    "get_relative_time",

]
