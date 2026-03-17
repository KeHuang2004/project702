"""
API响应工具模块

提供统一的API响应格式和便捷的响应构建方法
"""

from typing import Any, Dict
from utils.time_manager.time_manager import format_utc_now


class ApiResponse:
    """API响应工具类"""

    # HTTP状态码常量
    HTTP_OK = 200
    HTTP_CREATED = 201
    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_METHOD_NOT_ALLOWED = 405
    HTTP_CONFLICT = 409
    HTTP_UNPROCESSABLE_ENTITY = 422
    HTTP_TOO_MANY_REQUESTS = 429
    HTTP_INTERNAL_SERVER_ERROR = 500
    HTTP_BAD_GATEWAY = 502
    HTTP_SERVICE_UNAVAILABLE = 503

    @staticmethod
    def _create_response(
        success: bool,
        message: str,
        data: Any = None,
        error_code: str = None,
        status_code: int = HTTP_OK,
        meta: Dict = None,
    ) -> tuple:
        """创建响应 - Flask-RESTful 版本"""
        # 统一使用 UTC 中文格式
        utc_now_iso = format_utc_now()

        response_data = {
            "success": success,
            "message": message,
            "timestamp": utc_now_iso,
            "data": data,
        }

        if error_code:
            response_data["error_code"] = error_code

        if meta:
            response_data["meta"] = meta

        # 统一规范 data 中的时间字段，转为中文 UTC 格式
        try:
            formatted = ResponseFormatter.format_datetime_fields(response_data)
        except Exception:
            formatted = response_data

        # Flask-RESTful 直接返回字典和状态码，不使用 jsonify
        return formatted, status_code

    @classmethod
    def success(
        cls, message: str = "操作成功", data: Any = None, meta: Dict = None
    ) -> tuple:
        """成功响应"""
        return cls._create_response(
            success=True, message=message, data=data, status_code=cls.HTTP_OK, meta=meta
        )

    @classmethod
    def created(
        cls, message: str = "创建成功", data: Any = None, meta: Dict = None
    ) -> tuple:
        """创建成功响应"""
        return cls._create_response(
            success=True,
            message=message,
            data=data,
            status_code=cls.HTTP_CREATED,
            meta=meta,
        )

    @classmethod
    def bad_request(
        cls,
        message: str = "请求参数错误",
        error_code: str = "BAD_REQUEST",
        data: Any = None,
    ) -> tuple:
        """400 错误请求响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_BAD_REQUEST,
        )

    @classmethod
    def unauthorized(
        cls,
        message: str = "未授权访问",
        error_code: str = "UNAUTHORIZED",
        data: Any = None,
    ) -> tuple:
        """401 未授权响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_UNAUTHORIZED,
        )

    @classmethod
    def forbidden(
        cls, message: str = "禁止访问", error_code: str = "FORBIDDEN", data: Any = None
    ) -> tuple:
        """403 禁止访问响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_FORBIDDEN,
        )

    @classmethod
    def not_found(
        cls,
        message: str = "资源不存在",
        error_code: str = "NOT_FOUND",
        data: Any = None,
    ) -> tuple:
        """404 资源不存在响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_NOT_FOUND,
        )

    @classmethod
    def method_not_allowed(
        cls,
        message: str = "请求方法不允许",
        error_code: str = "METHOD_NOT_ALLOWED",
        data: Any = None,
    ) -> tuple:
        """405 方法不允许响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_METHOD_NOT_ALLOWED,
        )

    @classmethod
    def conflict(
        cls, message: str = "资源冲突", error_code: str = "CONFLICT", data: Any = None
    ) -> tuple:
        """409 冲突响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_CONFLICT,
        )

    @classmethod
    def validation_error(
        cls,
        message: str = "数据验证失败",
        error_code: str = "VALIDATION_ERROR",
        data: Any = None,
    ) -> tuple:
        """422 数据验证错误响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_UNPROCESSABLE_ENTITY,
        )

    @classmethod
    def rate_limit_exceeded(
        cls,
        message: str = "请求频率超限",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        data: Any = None,
    ) -> tuple:
        """429 请求频率超限响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_TOO_MANY_REQUESTS,
        )

    @classmethod
    def internal_error(
        cls,
        message: str = "服务器内部错误",
        error_code: str = "INTERNAL_ERROR",
        data: Any = None,
    ) -> tuple:
        """500 服务器内部错误响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_INTERNAL_SERVER_ERROR,
        )

    @classmethod
    def service_unavailable(
        cls,
        message: str = "服务不可用",
        error_code: str = "SERVICE_UNAVAILABLE",
        data: Any = None,
    ) -> tuple:
        """503 服务不可用响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=cls.HTTP_SERVICE_UNAVAILABLE,
        )

    @classmethod
    def custom_error(
        cls, message: str, error_code: str, status_code: int, data: Any = None
    ) -> tuple:
        """自定义错误响应"""
        return cls._create_response(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            status_code=status_code,
        )

    @classmethod
    def paginated_success(
        cls,
        message: str,
        items: list,
        page: int,
        page_size: int,
        total: int,
        data: Dict = None,
    ) -> tuple:
        """分页成功响应"""
        pages = (total + page_size - 1) // page_size

        response_data = {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1,
            },
        }

        if data:
            response_data.update(data)

        return cls.success(message, response_data)

    @classmethod
    def from_exception(
        cls, exception: Exception, default_message: str = "操作失败"
    ) -> tuple:
        """从异常创建响应"""
        from .exceptions import BaseKnowledgeBaseError

        if isinstance(exception, BaseKnowledgeBaseError):
            # 根据异常类型选择状态码
            status_code_map = {
                "ValidationError": cls.HTTP_BAD_REQUEST,
                "NotFoundError": cls.HTTP_NOT_FOUND,
                "DatabaseError": cls.HTTP_INTERNAL_SERVER_ERROR,
                "FileProcessingError": cls.HTTP_BAD_REQUEST,
                "ConfigurationError": cls.HTTP_INTERNAL_SERVER_ERROR,
                "EmbeddingError": cls.HTTP_INTERNAL_SERVER_ERROR,
                "VectorSearchError": cls.HTTP_INTERNAL_SERVER_ERROR,
                "AuthenticationError": cls.HTTP_UNAUTHORIZED,
                "AuthorizationError": cls.HTTP_FORBIDDEN,
                "RateLimitError": cls.HTTP_TOO_MANY_REQUESTS,
                "ExternalServiceError": cls.HTTP_BAD_GATEWAY,
            }

            status_code = status_code_map.get(
                exception.__class__.__name__, cls.HTTP_INTERNAL_SERVER_ERROR
            )

            return cls._create_response(
                success=False,
                message=exception.message,
                data=exception.details,
                error_code=exception.error_code,
                status_code=status_code,
            )
        else:
            # 普通异常
            return cls.internal_error(
                message=default_message, data={"original_error": str(exception)}
            )


class ResponseFormatter:
    """响应格式化工具"""

    @staticmethod
    def format_datetime_fields(data: Any, fields: list = None) -> Any:
        """保留输入数据的原始时间字段"""
        return data

    @staticmethod
    def remove_sensitive_fields(data: Any, sensitive_fields: list = None) -> Any:
        """移除敏感字段"""
        if sensitive_fields is None:
            sensitive_fields = ["password", "secret", "token", "key", "private"]

        if isinstance(data, dict):
            # 移除敏感字段
            for field in list(data.keys()):
                if any(sensitive in field.lower() for sensitive in sensitive_fields):
                    data.pop(field, None)

            # 递归处理嵌套字典
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = ResponseFormatter.remove_sensitive_fields(
                        value, sensitive_fields
                    )

        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i] = ResponseFormatter.remove_sensitive_fields(
                    item, sensitive_fields
                )

        return data

    @staticmethod
    def add_computed_fields(data: Any, computed_fields: Dict = None) -> Any:
        """添加计算字段"""
        if computed_fields is None:
            computed_fields = {}

        if isinstance(data, dict):
            # 添加计算字段
            for field_name, field_func in computed_fields.items():
                if callable(field_func):
                    try:
                        data[field_name] = field_func(data)
                    except Exception:
                        pass  # 忽略计算错误

            # 递归处理嵌套字典
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = ResponseFormatter.add_computed_fields(
                        value, computed_fields
                    )

        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i] = ResponseFormatter.add_computed_fields(item, computed_fields)

        return data
