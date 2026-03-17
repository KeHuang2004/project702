"""
自定义异常类模块

定义了知识库系统中使用的各种异常类
"""


class BaseKnowledgeBaseError(Exception):
    """知识库系统基础异常类"""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self):
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self):
        return f"{self.error_code}: {self.message}"


class ValidationError(BaseKnowledgeBaseError):
    """数据验证异常"""

    def __init__(self, message: str, field: str = None, value=None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


class NotFoundError(BaseKnowledgeBaseError):
    """资源不存在异常"""

    def __init__(self, message: str, resource_type: str = None, resource_id=None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = str(resource_id)

        super().__init__(message, "NOT_FOUND_ERROR", details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class DatabaseError(BaseKnowledgeBaseError):
    """数据库操作异常"""

    def __init__(self, message: str, operation: str = None, table: str = None):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table

        super().__init__(message, "DATABASE_ERROR", details)
        self.operation = operation
        self.table = table


class FileProcessingError(BaseKnowledgeBaseError):
    """文件处理异常"""

    def __init__(self, message: str, filename: str = None, file_path: str = None):
        details = {}
        if filename:
            details["filename"] = filename
        if file_path:
            details["file_path"] = file_path

        super().__init__(message, "FILE_PROCESSING_ERROR", details)
        self.filename = filename
        self.file_path = file_path


class ConfigurationError(BaseKnowledgeBaseError):
    """配置错误异常"""

    def __init__(self, message: str, config_key: str = None, config_value=None):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = str(config_value)

        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key
        self.config_value = config_value


class EmbeddingError(BaseKnowledgeBaseError):
    """向量嵌入异常"""

    def __init__(self, message: str, model_name: str = None, text_length: int = None):
        details = {}
        if model_name:
            details["model_name"] = model_name
        if text_length is not None:
            details["text_length"] = text_length

        super().__init__(message, "EMBEDDING_ERROR", details)
        self.model_name = model_name
        self.text_length = text_length


class VectorSearchError(BaseKnowledgeBaseError):
    """向量搜索异常"""

    def __init__(
        self, message: str, index_path: str = None, query_vector_dim: int = None
    ):
        details = {}
        if index_path:
            details["index_path"] = index_path
        if query_vector_dim is not None:
            details["query_vector_dim"] = query_vector_dim

        super().__init__(message, "VECTOR_SEARCH_ERROR", details)
        self.index_path = index_path
        self.query_vector_dim = query_vector_dim


class AuthenticationError(BaseKnowledgeBaseError):
    """身份验证异常"""

    def __init__(self, message: str, user_id: str = None):
        details = {}
        if user_id:
            details["user_id"] = user_id

        super().__init__(message, "AUTHENTICATION_ERROR", details)
        self.user_id = user_id


class AuthorizationError(BaseKnowledgeBaseError):
    """权限授权异常"""

    def __init__(
        self, message: str, user_id: str = None, required_permission: str = None
    ):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(message, "AUTHORIZATION_ERROR", details)
        self.user_id = user_id
        self.required_permission = required_permission


class RateLimitError(BaseKnowledgeBaseError):
    """请求频率限制异常"""

    def __init__(self, message: str, limit: int = None, window: int = None):
        details = {}
        if limit is not None:
            details["limit"] = limit
        if window is not None:
            details["window"] = window

        super().__init__(message, "RATE_LIMIT_ERROR", details)
        self.limit = limit
        self.window = window


class ExternalServiceError(BaseKnowledgeBaseError):
    """外部服务异常"""

    def __init__(self, message: str, service_name: str = None, status_code: int = None):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if status_code is not None:
            details["status_code"] = status_code

        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)
        self.service_name = service_name
        self.status_code = status_code
