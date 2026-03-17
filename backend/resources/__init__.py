"""
API资源层模块

包含知识库、文件和文本块的REST API接口定义
"""

from .chat_resource import ChatResource
from .chunk_resource import ChunkRetrieveResource
from .file_resource import FileResource, FileDownloadResource
from .knowledge_base_resource import (
    KnowledgeBaseResource,
)
from .qapair_resource import QApairResource

__all__ = [
    "KnowledgeBaseResource",
    "FileResource",
    "FileDownloadResource",
    "ChunkRetrieveResource",
    "ChatResource",
    "QApairResource",
]
