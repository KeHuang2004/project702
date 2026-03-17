"""
Flask应用入口文件

创建并配置Flask应用，注册资源和中间件
"""

import logging
import os
import subprocess
import atexit
from logging.handlers import RotatingFileHandler

from flask import Flask, request
from flask_cors import CORS
from flask_restful import Api, Resource

from config import get_config, Config
from utils.database__manager.connection import init_db
from resources.chat_resource import ChatResource

# 导入资源类
from resources.chunk_resource import ChunkRetrieveResource, ChunkListResource, ChunkEmbeddingResource, ChunkEmbeddingToFileResource, ChunkDetailResource
from resources.file_resource import (
    FileResource,
    FileProcessResource,
    FileUploadResource,
    FileDownloadResource,
    FileLatestDocsResource,
    FileLatestDocProxyResource,
)
from resources.knowledge_base_resource import (
    KnowledgeBaseResource,
    KnowledgeBaseRetrieveResource,
)
from utils.request_manager.exceptions import BaseKnowledgeBaseError
from utils.request_manager.response import ApiResponse

def build_health_data(app):
    """构建健康检查数据（供 API 与启动时复用）。返回 (status, data)。"""
    try:
        from utils.database__manager.connection import DatabaseConnection
        db_status = "healthy" if DatabaseConnection.test_connection() else "unhealthy"
    except Exception as e:
        app.logger.error(f"数据库连接检查失败: {e}")
        db_status = "unhealthy"

    upload_dir = app.config.get("UPLOAD_FOLDER", "./data/uploads")
    faiss_dir = app.config.get("FAISS_INDEX_FOLDER", "./data/faiss_index")
    tinydb_dir = os.path.dirname(app.config.get("TINYDB_PATH", "./data/tinydb/chat_db.json"))

    # 数据库目录
    try:
        from utils.database__manager.connection import DatabaseConnection
        db_path = DatabaseConnection.get_db_path()
    except Exception:
        db_path = None
    db_dir = os.path.dirname(db_path) if db_path else "./data/database"

    upload_dir_exists = os.path.exists(upload_dir)
    faiss_dir_exists = os.path.exists(faiss_dir)
    db_dir_exists = os.path.exists(db_dir)
    tinydb_dir_exists = os.path.exists(tinydb_dir)

    status = (
        "healthy"
        if all([
            db_status == "healthy",
            upload_dir_exists,
            faiss_dir_exists,
            db_dir_exists,
            tinydb_dir_exists,
        ]) else "unhealthy"
    )

    health_data = {
        "status": status,
        "timestamp": app.config.get("STARTUP_TIME"),
        "checks": {
            "database": db_status,
            "upload_directory": "healthy" if upload_dir_exists else "unhealthy",
            "faiss_directory": "healthy" if faiss_dir_exists else "unhealthy",
            "database_directory": "healthy" if db_dir_exists else "unhealthy",
            "tinydb_directory": "healthy" if tinydb_dir_exists else "unhealthy",
        },
        "directories": {
            "upload": upload_dir,
            "faiss": faiss_dir,
            "database": db_dir,
            "tinydb": tinydb_dir,
        "logs": app.config.get("LOG_DIR", "./data/logs"),
        },
    }
    return status, health_data


def run_startup_connectivity_checks(app: Flask) -> None:
    """检查预定义的 vLLM 端口（11500,11510,11520）的连通性并打印结果。"""
    try:
        host = getattr(Config, "VLLM_HOST", "127.0.0.1")
        ports = [11500, 11510, 11520]
        print("[INFO] 检查 vLLM 预定义端口连通性: " + ",".join(map(str, ports)))
        unhealthy = []
        import urllib.request
        for p in ports:
            url = f"http://{host}:{p}/v1/models"
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    print(f"[INFO] 端口 {p} -> OK ({resp.status})")
            except Exception as e:
                print(f"[INFO] 端口 {p} -> FAILED ({e})")
                unhealthy.append(p)
        if not unhealthy:
            print("[INFO] 预定义 vLLM 端口全部正常")
        else:
            print("[WARN] 以下预定义端口不可达: " + ",".join(map(str, unhealthy)))
    except Exception as e:
        print(f"[WARN] 启动连通性检查失败（已忽略）：{e}")
  
  
def start_vllm_services(app: Flask) -> None:
    """
    启动本地 vLLM 服务：从 `app.config` 中读取 `EMBEDDING_SERVE` 和 `RERANK_SERVE`，
    在运行时组装 `vllm serve` 命令并启动对应子进程（不在 config 中保存完整命令）。
    """
    # 从 app.config 读取 EMBEDDING_SERVE / RERANK_SERVE
    app.vllm_processes = []

    def _maybe_start(name: str, cfg: dict):
        model_path = cfg.get("model_path")
        # 使用统一固定的 served name（不在 config 中配置）
        if name == "embedding":
            served_name = "embedding__model"
        elif name == "rerank":
            served_name = "rerank__model"
        else:
            served_name = "chat__model"
        port = int(cfg.get("port", 0) or 0)
        gpu_frac = float(cfg.get("gpu_memory_utilization", cfg.get("gpu_fraction", 0.0)) or 0.0)

        if not model_path:
            print(f"[WARN] {name} 未配置 model_path，跳过启动")
            return
        if not os.path.exists(model_path):
            print(f"[WARN] 未找到 {name} 模型目录：{model_path}，跳过启动")
            return

        # 构建 vllm serve 命令（与示例一致，不使用 --task 标志）
        cmd_parts = ["vllm", "serve", f'"{model_path}"']
        cmd_parts += ["--served-model-name", f"{served_name}"]
        if port:
            cmd_parts += ["--port", str(port)]
        cmd = " ".join(cmd_parts)

        env = os.environ.copy()
        # 将 gpu_memory_utilization 暴露为环境变量，供外部 wrapper 或自定义 vllm 启动脚本使用
        if gpu_frac and gpu_frac > 0:
            env["VLLM_GPU_MEMORY_UTILIZATION"] = str(gpu_frac)

        try:
            print(f"[INFO] 启动 vLLM {name} 服务: {cmd}")
            proc = subprocess.Popen(cmd, shell=True, env=env)
            app.vllm_processes.append(proc)
        except Exception as e:
            print(f"[ERROR] 启动 vLLM {name} 失败: {e}")

    # embedding
    embed_cfg = app.config.get("EMBEDDING_SERVE", {})
    _maybe_start("embedding", embed_cfg)

    # rerank
    rerank_cfg = app.config.get("RERANK_SERVE", {})
    _maybe_start("rerank", rerank_cfg)


def stop_vllm_services(app: Flask) -> None:
    """优雅停止已启动的 vLLM 子进程（在应用退出时调用）。"""
    procs = getattr(app, "vllm_processes", []) or []
    for p in procs:
        try:
            if p.poll() is None:
                print(f"[INFO] 停止 vLLM 进程 pid={p.pid} ...")
                p.terminate()
                p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)

    # 加载配置
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = get_config()
    app.config.from_object(config_class)

    # 在初始化扩展前，优先检查并创建数据目录，输出清晰的人类可读日志
    check_and_prepare_data_folders(app)

    # 不再自动启动本地 vLLM 服务；仅在启动前检查预定义端口的连通性
    run_startup_connectivity_checks(app)
    # 初始化扩展
    init_extensions(app)

    # 注册资源
    register_resources(app)

    # 注册错误处理器
    register_error_handlers(app)

    # 注册中间件
    register_middleware(app)

    # 配置日志
    configure_logging(app)

    # 初始化配置
    config_class.init_app(app)

    return app


def check_and_prepare_data_folders(app: Flask) -> None:
    """启动前检查 data 目录及其基础子目录，若不存在则创建，并打印详细信息。

    目录期望：backend/data 下包含 database、uploads、tinydb、faiss_index
    """
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        rel_base_for_log = "backend/data"  # 统一日志中的展示路径

        print("[INFO]自动检查backend/data是否存在")

        created_any = False
        if not os.path.exists(base_dir):
            print("检测到该文件夹不存在！自动创建该文件夹")
            os.makedirs(base_dir, exist_ok=True)
            print(f"文件夹创建成功！{rel_base_for_log}")
            print("并同步创建 faiss_index database tinydb uploads 文件夹")
            for name in ("faiss_index", "database", "tinydb", "uploads"):
                os.makedirs(os.path.join(base_dir, name), exist_ok=True)
            created_any = True
        else:
            # 单独检查每个子目录
            for name in ("database", "uploads", "tinydb", "faiss_index"):
                subdir = os.path.join(base_dir, name)
                if os.path.exists(subdir):
                    print(f"[INFO]检测到文件夹存在：{rel_base_for_log}/{name}")
                else:
                    print(f"[INFO]检测到文件夹不存在：{rel_base_for_log}/{name}，自动创建...")
                    os.makedirs(subdir, exist_ok=True)
                    print(f"[INFO]创建成功：{rel_base_for_log}/{name}")
                    created_any = True

        # 确保与配置项一致的目录也存在（尤其是 TINYDB 的文件路径所在目录）
        try:
            upload_dir = app.config.get("UPLOAD_FOLDER", "./data/uploads")
            faiss_dir = app.config.get("FAISS_INDEX_FOLDER", "./data/faiss_index")
            tinydb_dir = os.path.dirname(app.config.get("TINYDB_PATH", "./data/tinydb/chat_db.json"))
            for p in (upload_dir, faiss_dir, tinydb_dir):
                if not os.path.exists(p):
                    os.makedirs(p, exist_ok=True)
        except Exception:
            # 配置兜底失败不影响主流程
            pass

        # 仅输出目录检查结果（不进行数据库连通性探测，避免未初始化阶段的冗余日志）
        if created_any:
            print("所有基础文件夹创建成功！")
        else:
            print("[INFO]所有基础文件夹检查完毕！")
    except Exception as e:
        print(f"[WARN]数据目录自检失败（已忽略）：{e}")


def init_extensions(app):
    """初始化Flask扩展"""
    # 初始化数据库
    init_db(app)

    # 初始化CORS
    CORS(app, origins=app.config["CORS_ORIGINS"])


def register_resources(app):
    """注册Flask-RESTful资源"""
    api = Api(app, prefix="/api/v1")

    # 知识库资源：一个资源类同时处理集合与单项（PUT/DELETE 仅允许路径参数）
    api.add_resource(
        KnowledgeBaseResource,
        "/knowledge-bases",
        "/knowledge-bases/<kb_id>",
    )

    # 知识库检索（余弦相似度）
    api.add_resource(
        KnowledgeBaseRetrieveResource,
        "/knowledge-bases/<int:kb_id>/retrieve",
    )

    # 知识库统计信息资源已移除，前端自行汇总

    # 文件资源
    api.add_resource(
        FileLatestDocsResource,
        "/files/latest-docs",
        methods=["POST"],
    )

    api.add_resource(
        FileLatestDocProxyResource,
        "/files/latest-docs/proxy",
        methods=["GET"],
    )

    api.add_resource(
        FileResource,
        "/files",
        "/files/<file_id>",
        methods=["GET", "PUT", "DELETE"],
    )

    # 文件上传（仅 POST，用于路径中的 kb_id）
    api.add_resource(
        FileUploadResource,
        "/files/<int:kb_id>",
        methods=["POST"],
    )

    # 文件下载
    api.add_resource(
        FileDownloadResource,
        "/files/<int:file_id>/download",
        methods=["GET"],
    )

    # 显式启动文件处理
    api.add_resource(FileProcessResource, "/files/<int:kb_id>/process")

    # 文本块检索资源（新接口：携带知识库ID路径参数）
    api.add_resource(ChunkRetrieveResource, "/chunks/retrieve/<int:kb_id>")
    # 文本块列表与批量嵌入
    api.add_resource(ChunkListResource, "/chunks")
    api.add_resource(ChunkEmbeddingResource, "/chunks/embed")
    api.add_resource(ChunkEmbeddingToFileResource, "/chunks/embedding")
    api.add_resource(ChunkDetailResource, "/chunks/<chunk_id>")

    # 聊天资源初始化
    from utils.tinydb_manager.tinydb_manager import TinyDBManager
    from services.chat_service import ChatService

    tinydb_manager = TinyDBManager(app.config["TINYDB_PATH"])
    chat_service = ChatService(tinydb_manager)

    # 聊天资源
    api.add_resource(
        ChatResource,
        "/chat",
        "/chat/<int:session_id>",
        resource_class_kwargs={"chat_service": chat_service},
    )

    # QApair 资源：以问答对为最小实体，支持导入/查询/删除
    from resources.qapair_resource import QApairResource
    api.add_resource(
        QApairResource,
        "/qapairs",
        "/qapairs/<qa_id>",
    )
    # 原先的图片服务（主要用于词云展示）已移除

    # 文本生成资源（非流式，用于 RAG 管线中的抽取/重写）
    from resources.generate_resource import GenerateResource
    api.add_resource(GenerateResource, "/generate")


def register_error_handlers(app):
    """注册错误处理器"""

    @app.errorhandler(BaseKnowledgeBaseError)
    def handle_custom_error(error):
        """处理自定义异常"""
        # 对于错误处理器，我们需要使用 Flask 的 jsonify
        from flask import jsonify

        response_data, status_code = ApiResponse.from_exception(error)
        return jsonify(response_data), status_code

    @app.errorhandler(400)
    def handle_bad_request(error):
        """处理400错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.bad_request("请求参数错误")
        return jsonify(response_data), status_code

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """处理401错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.unauthorized("未授权访问")
        return jsonify(response_data), status_code

    @app.errorhandler(403)
    def handle_forbidden(error):
        """处理403错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.forbidden("禁止访问")
        return jsonify(response_data), status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.not_found("资源不存在")
        return jsonify(response_data), status_code

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理405错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.method_not_allowed("请求方法不允许")
        return jsonify(response_data), status_code

    @app.errorhandler(413)
    def handle_payload_too_large(error):
        """处理413错误（文件太大）"""
        from flask import jsonify

        response_data, status_code = ApiResponse.bad_request("上传文件过大")
        return jsonify(response_data), status_code

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        """处理429错误"""
        from flask import jsonify

        response_data, status_code = ApiResponse.rate_limit_exceeded("请求频率超限")
        return jsonify(response_data), status_code

    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理500错误"""
        app.logger.error(f"服务器内部错误: {error}")
        from flask import jsonify

        response_data, status_code = ApiResponse.internal_error("服务器内部错误")
        return jsonify(response_data), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """处理未预期的错误"""
        app.logger.error(f"未预期的错误: {error}", exc_info=True)
        from flask import jsonify

        if app.debug:
            response_data, status_code = ApiResponse.internal_error(
                f"未预期的错误: {str(error)}"
            )
        else:
            response_data, status_code = ApiResponse.internal_error("服务器内部错误")
        return jsonify(response_data), status_code


def register_middleware(app):
    """注册中间件"""

    @app.before_request
    def log_request_info():
        """记录请求信息"""
        if app.config.get("LOG_LEVEL") == "DEBUG":
            app.logger.debug(f"请求: {request.method} {request.url}")
            if request.json:
                app.logger.debug(f"请求体: {request.json}")

    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 添加安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 记录响应信息
        if app.config.get("LOG_LEVEL") == "DEBUG":
            app.logger.debug(f"响应状态: {response.status_code}")

        return response


def configure_logging(app):
    """配置日志"""
    if not app.debug and not app.testing:
        # 确保日志目录存在（默认放在 data/logs）
        log_dir = app.config.get("LOG_DIR", "./data/logs")
        os.makedirs(log_dir, exist_ok=True)

        # 文件日志处理器
        if app.config.get("LOG_FILE"):
            log_file_path = os.path.join(log_dir, app.config["LOG_FILE"])
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=app.config.get("LOG_MAX_BYTES", 10240000),
                backupCount=app.config.get("LOG_BACKUP_COUNT", 10),
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO")))
            app.logger.addHandler(file_handler)

        # 控制台日志处理器
        if not app.logger.handlers:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(
                getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
            )
            stream_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            )
            app.logger.addHandler(stream_handler)

        app.logger.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO")))
        app.logger.info("知识库应用启动")


# 端口探测逻辑已移除：不再在应用内检查外部 embedding/rerank 服务端口


# 创建应用实例
app = create_app()


# 创建根路径资源
class RootResource(Resource):
    """根路径资源"""

    def get(self):
        """获取API信息"""
        return ApiResponse.success(
            "知识库系统API",
            {
                "version": "1.0.0",
                "status": "running",
                "environment": os.environ.get("FLASK_ENV", "development"),
                "endpoints": {
                    "knowledge_bases": "/api/v1/knowledge-bases",
                    "files": "/api/v1/files",
                    "chunks": "/api/v1/chunks",
                    "chat": "/api/v1/chat",
                    "search": "/api/v1/search",
                    "health": "/api/v1/health",
                },
            },
        )


class HealthResource(Resource):
    """健康检查资源"""

    def get(self):
        """健康检查"""
        status, health_data = build_health_data(app)
        if status == "healthy":
            return ApiResponse.success("系统健康", health_data)
        else:
            return ApiResponse.internal_error("系统不健康", health_data)


# 注册根路径和健康检查资源
root_api = Api(app)
root_api.add_resource(RootResource, "/")
root_api.add_resource(HealthResource, "/health")

if __name__ == "__main__":
    # 开发/本地启动，支持命令行参数优先，其次读取环境变量
    import argparse

    parser = argparse.ArgumentParser(description="Run Knowledge Base Backend Server")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host to bind (default from HOST env or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 11550)),
        help="Port to listen on (default from PORT env or 11550)",
    )
    parser.add_argument(
        "--debug",
        action="store_true" if os.environ.get("FLASK_DEBUG") is None else "store_false",
        help="Enable Flask debug mode (or set FLASK_DEBUG=1)",
    )

    args, unknown = parser.parse_known_args()

    # 若设置了环境变量 FLASK_DEBUG，则以其为准；否则采用命令行开关
    if os.environ.get("FLASK_DEBUG") is not None:
        env_flag = os.environ.get("FLASK_DEBUG", "0").lower()
        debug = env_flag in ("1", "true", "yes", "on")
    else:
        # 当提供 --debug 时为 True；未提供时为 False
        debug = args.debug if isinstance(args.debug, bool) else False

    host = args.host
    port = args.port

    # 确保必要的目录存在
    os.makedirs("./data/database", exist_ok=True)
    os.makedirs("./data/uploads", exist_ok=True)
    os.makedirs("./data/faiss_index", exist_ok=True)
    os.makedirs("./data/tinydb", exist_ok=True)
    # 日志目录
    os.makedirs(app.config.get("LOG_DIR", "./data/logs"), exist_ok=True)

    # 异步 HTTP 方式 ping 自身 /health 并输出（待服务启动后，打印完整返回）
    import threading
    import time
    def _delayed_ping_health():
        time.sleep(1.0)
        try:
            import urllib.request
            import json
            url = f"http://{host}:{port}/health"
            with urllib.request.urlopen(url, timeout=2) as resp:
                ok = resp.status == 200
                body = resp.read()
                try:
                    parsed = json.loads(body.decode("utf-8", errors="ignore"))
                    pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
                except Exception:
                    pretty = body.decode("utf-8", errors="ignore")
                print(f"[INFO]启动后HTTP健康检查 {url} -> {'OK' if ok else 'FAILED'} ({resp.status})\n{pretty}")
        except Exception as e:
            print(f"[INFO]启动后HTTP健康检查失败: {e}")

    threading.Thread(target=_delayed_ping_health, daemon=True).start()

    app.run(host=host, port=port, debug=debug)

