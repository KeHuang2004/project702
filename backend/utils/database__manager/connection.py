"""
数据库连接管理模块

提供数据库连接的创建、管理和初始化功能
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """数据库连接管理类"""

    _db_path = None
    _initialized = False
    _db_lock = Lock()

    @classmethod
    def init_db_path(cls, app):
        """
        初始化数据库路径

        Args:
            app: Flask应用实例
        """
        # 从配置中获取数据库路径
        db_url = app.config.get(
            "SQLALCHEMY_DATABASE_URI", "sqlite:///./data/database/knowledge_base.db"
        )

        # 解析SQLite数据库路径
        if db_url.startswith("sqlite:///"):
            # 移除 sqlite:/// 前缀
            cls._db_path = db_url[10:]  # len('sqlite:///') = 10

            # 处理相对路径
            if cls._db_path.startswith("./"):
                cls._db_path = cls._db_path[2:]  # 移除 './'

            # 确保使用正确的路径分隔符
            cls._db_path = os.path.normpath(cls._db_path)

            # 如果不是绝对路径，转换为绝对路径
            if not os.path.isabs(cls._db_path):
                cls._db_path = os.path.abspath(cls._db_path)

        elif db_url.startswith("sqlite://"):
            # 处理 sqlite:// 格式（相对路径）
            cls._db_path = db_url[9:]  # len('sqlite://') = 9
            cls._db_path = os.path.normpath(cls._db_path)
            if not os.path.isabs(cls._db_path):
                cls._db_path = os.path.abspath(cls._db_path)
        else:
            # 默认路径
            cls._db_path = os.path.abspath("./data/database/knowledge_base.db")

        # 确保数据库目录存在
        db_dir = os.path.dirname(cls._db_path)
        os.makedirs(db_dir, exist_ok=True)

        cls._initialized = True
        logger.info(f"数据库路径初始化: {cls._db_path}")
        # 同步输出到标准控制台
        print(f"数据库路径初始化: {cls._db_path}")

    @classmethod
    def get_db_path(cls) -> str:
        """获取数据库路径"""
        if not cls._initialized or cls._db_path is None:
            raise RuntimeError("数据库未初始化，请先调用 init_db_path()")
        return cls._db_path

    @classmethod
    @contextmanager
    def get_connection(cls):
        """获取数据库连接的上下文管理器"""
        if not cls._initialized:
            raise RuntimeError("数据库未初始化，请先调用 init_db_path()")

        with cls._db_lock:
            conn = sqlite3.connect(cls._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # 使结果可以像字典一样访问
            conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
            conn.execute("PRAGMA journal_mode = WAL")  # 设置WAL模式提高并发性能

        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def get_cursor(cls):
        """
        获取数据库游标的上下文管理器

        使用方式:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.execute("SELECT * FROM table WHERE id = ?", (obj_id,))
                row = cursor.fetchone()

        Yields:
            tuple: (cursor, conn) 数据库游标和连接对象
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor, conn
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()

    @classmethod
    def test_connection(cls) -> bool:
        """测试数据库连接"""
        try:
            with cls.get_cursor() as (cursor, conn):
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    @classmethod
    def get_all_tables(cls) -> list:
        """获取所有表名"""
        try:
            with cls.get_cursor() as (cursor, conn):
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取表名失败: {e}")
            return []

    @classmethod
    def get_table_info(cls, table_name: str) -> list:
        """获取表结构信息"""
        try:
            with cls.get_cursor() as (cursor, conn):
                cursor.execute(f"PRAGMA table_info({table_name})")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            return []

    @classmethod
    def execute_script(cls, script_path: str):
        """执行SQL脚本文件"""
        script_file = Path(script_path)
        if not script_file.exists():
            logger.warning(f"SQL脚本文件不存在: {script_path}")
            return

        try:
            with cls.get_connection() as conn:
                with open(script_file, "r", encoding="utf-8") as f:
                    script_content = f.read()

                # 使用 executescript 方法，能正确处理包含触发器等复杂SQL的脚本
                conn.executescript(script_content)
                logger.info(f"成功执行SQL脚本: {script_path}")

        except Exception as e:
            logger.error(f"执行SQL脚本失败 {script_path}: {e}")
            raise

    @classmethod
    def execute_query(
        cls,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = True,
    ):
        """
        执行数据库查询

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否只返回一行结果
            fetch_all: 是否返回所有结果

        Returns:
            查询结果
        """
        with cls.get_cursor() as (cursor, conn):
            cursor.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.rowcount

    @classmethod
    def execute_insert(cls, query: str, params: tuple = ()):
        """
        执行插入操作

        Args:
            query: SQL插入语句
            params: 插入参数

        Returns:
            int: 新插入记录的ID
        """
        with cls.get_cursor() as (cursor, conn):
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def execute_update(cls, query: str, params: tuple = ()):
        """
        执行更新操作

        Args:
            query: SQL更新语句
            params: 更新参数

        Returns:
            int: 影响的行数
        """
        with cls.get_cursor() as (cursor, conn):
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    @classmethod
    def execute_delete(cls, query: str, params: tuple = ()):
        """
        执行删除操作

        Args:
            query: SQL删除语句
            params: 删除参数

        Returns:
            int: 删除的行数
        """
        with cls.get_cursor() as (cursor, conn):
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    @classmethod
    def backup_database(cls, backup_path: str):
        """备份数据库"""
        import shutil

        if not cls._initialized:
            raise RuntimeError("数据库未初始化，请先调用 init_db_path()")

        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(cls._db_path, backup_path)
        logger.info(f"数据库已备份到: {backup_path}")


# 保持向后兼容的函数
def init_db(app):
    """
    初始化数据库

    Args:
        app: Flask应用实例
    """
    DatabaseConnection.init_db_path(app)

    logger.info("开始初始化数据库...")

    # 检测数据库文件是否已存在
    db_path = DatabaseConnection.get_db_path()
    db_exists = os.path.exists(db_path)

    # 计算本模块目录下的 schema/demo 脚本路径
    module_dir = os.path.dirname(__file__)
    schema_path = os.path.join(module_dir, "schema.sql")

    if not db_exists:
        # 未检测到数据库文件，创建目录并初始化空数据库结构
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        logger.info("未检测到 data/database 下的数据库，正在创建空数据库并初始化...")
        print("未检测到 data/database 下的数据库，正在创建空数据库并初始化...")
        try:
            # 执行建表脚本（会在连接时创建数据库文件）
            DatabaseConnection.execute_script(schema_path)
            # 注意：已移除自动初始化演示数据（demo_data.sql）
            logger.info("空数据库已创建并初始化完成（不包含演示数据）：%s", db_path)
            print(f"空数据库已创建并初始化完成（不包含演示数据）：{db_path}")
        except Exception as e:
            logger.error("初始化数据库失败: %s", e)
            print(f"初始化数据库失败: {e}")
            raise
    else:
        # 已存在数据库文件：若缺表则补齐
        try:
            tables = DatabaseConnection.get_all_tables()
            table_set = set(tables)

            # 原有三张表缺失时，重跑 schema.sql（可能失败于重复建表，推荐首次安装使用）
            required_core = {"knowledge_bases", "files", "chunks"}
            if not required_core.issubset(table_set):
                logger.warning("检测到数据库缺少核心表，正在执行建表脚本补齐...")
                print("检测到数据库缺少核心表，正在执行建表脚本补齐...")
                DatabaseConnection.execute_script(schema_path)

            # 增量：确保 qapairs 表存在（幂等创建）
            if "qapairs" not in table_set:
                logger.info("检测到缺少 qapairs 表，正在创建...")
                create_qapairs_sql = (
                    "CREATE TABLE IF NOT EXISTS qapairs (\n"
                    "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    "    question TEXT NOT NULL,\n"
                    "    answer TEXT NOT NULL\n"
                    ");"
                )
                with DatabaseConnection.get_connection() as conn:
                    conn.executescript(create_qapairs_sql)
                logger.info("qapairs 表创建完成")
        except Exception as e:
            logger.error(f"检查/补齐数据库表失败: {e}")
        logger.info("已检测到 data/database 下有数据库，自动连接到该数据库：%s", db_path)
        print("已检测到 data/database下有数据库，自动连接到该数据库")


# 向后兼容的函数
def get_db_connection():
    """获取数据库连接（向后兼容）"""
    return DatabaseConnection.get_connection()


@contextmanager
def get_db_cursor():
    """获取数据库游标（向后兼容）"""
    with DatabaseConnection.get_cursor() as (cursor, conn):
        yield cursor


def execute_query(
    query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True
):
    """执行查询（向后兼容）"""
    return DatabaseConnection.execute_query(query, params, fetch_one, fetch_all)


def execute_insert(query: str, params: tuple = ()):
    """执行插入（向后兼容）"""
    return DatabaseConnection.execute_insert(query, params)


def execute_update(query: str, params: tuple = ()):
    """执行更新（向后兼容）"""
    return DatabaseConnection.execute_update(query, params)


def execute_delete(query: str, params: tuple = ()):
    """执行删除（向后兼容）"""
    return DatabaseConnection.execute_delete(query, params)


def check_connection():
    """检查连接（向后兼容）"""
    return DatabaseConnection.test_connection()
