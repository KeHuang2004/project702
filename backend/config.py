"""
配置文件

定义不同环境下的配置参数
"""

import os
from datetime import timedelta


class Config:
    """基础配置类"""

    # Flask基础配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or r"sqlite:///data/database/knowledge_base.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # TinyDB配置（聊天系统）
    TINYDB_PATH = os.environ.get("TINYDB_PATH") or "./data/tinydb/chat_db.json"

    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "./data/uploads"
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500MB
    ALLOWED_EXTENSIONS = {
        "txt",
        "pdf",
        "doc",
        "docx",
        "rtf",
        "md",
        "xls",
        "xlsx",
        "csv",
        "ppt",
        "pptx",
        "html",
        "htm",
        "json",
        "xml",
    }

    # 向量化配置
    # 统一使用 faiss_index 目录
    FAISS_INDEX_FOLDER = os.environ.get("FAISS_INDEX_PATH") or "./data/faiss_index"
    DEFAULT_EMBEDDING_MODEL = (
        os.environ.get("EMBEDDING_MODEL") or "Qwen3-Embedding-0.6B"
    )
    DEFAULT_CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 1000))
    DEFAULT_CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", 1000000))
    SPLIT_MAX_WORKERS = int(os.environ.get("SPLIT_MAX_WORKERS", 10))

    # API配置
    API_RATE_LIMIT = os.environ.get("API_RATE_LIMIT") or "1000/hour"
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", 30))
    RERANK_TIMEOUT = int(os.environ.get("RERANK_TIMEOUT", 120))
    PAGINATION_SIZE = int(os.environ.get("PAGINATION_SIZE", 20))
    PAGINATION_MAX_SIZE = int(os.environ.get("PAGINATION_MAX_SIZE", 100))

    # 日志配置
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "INFO"
    LOG_FILE = os.environ.get("LOG_FILE") or "knowledge_base.log"
    # 日志目录（默认放在 data 下）
    LOG_DIR = os.environ.get("LOG_DIR") or "./data/logs"
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))

    # 外部服务配置
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL") or "gpt-3.5-turbo"

    # 安全配置
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_EXPIRES_HOURS", 24))
    )

    # CORS配置
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # 缓存配置
    CACHE_TYPE = os.environ.get("CACHE_TYPE") or "simple"
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_TIMEOUT", 300))

    # 启动时间
    STARTUP_TIME = None
    # 统一的日期时间展示格式（中文，使用北京时间，但不追加文字）
    # 约定：YYYY年MM月DD日 HH时mm分ss秒
    DATE_TIME_FORMAT = "%Y年%m月%d日 %H时%M分%S秒"

    # —— vLLM/服务端口与端点配置 ——
    VLLM_HOST = os.environ.get("VLLM_HOST", "127.0.0.1")

 
    # —— 嵌入/重排 模型的基本配置 ——
    EMBEDDING_SERVE = {
        "model_path": "/data/home/huangke/project702/models/Qwen3-Embedding-0.6B",
        "port": 11500,
        "gpu_memory_utilization": 0.2,
    }

    RERANK_SERVE = {
        "model_path": "/data/home/huangke/project702/models/bge-reranker-v2-m3",
        "port": 11510,
        "gpu_memory_utilization": 0.2,
    }

    # —— 问答模型的基本配置 ——
    # llm_mode 用于指定问答模型的调用方式：local 或 remote
    llm_mode = "remote"

    # local 模式下使用本地问答模型服务
    CHAT_SERVE = {
        "model_path": "/data/home/huangke/project702/models/DeepSeek-R1-Distill-Qwen-7B",
        "port": 11520,
        "gpu_memory_utilization": 0.5,
    }

    # remote 模式下使用外部问答模型服务
    llm_api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    llm_api_key = "sk-f5d4e6d321bc49cfb6e9656c012078ca"
    llm_model = "qwen3.5-flash"
    # 远程问答调用稳健性配置
    llm_request_timeout = 90
    llm_request_retries = 2



    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        from utils.time_manager.time_manager import format_utc_now

        # 统一使用 UTC 与全局中文格式
        Config.STARTUP_TIME = format_utc_now()

        # 创建必要的目录
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.config["FAISS_INDEX_FOLDER"], exist_ok=True)

        # 创建日志目录（统一放到 data/logs）
        os.makedirs(app.config.get("LOG_DIR", "./data/logs"), exist_ok=True)

        # 创建TinyDB目录
        tinydb_dir = os.path.dirname(app.config["TINYDB_PATH"])
        os.makedirs(tinydb_dir, exist_ok=True)


def get_config():
    """获取当前配置"""
    return Config
