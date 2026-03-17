from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .connection import DatabaseConnection


class BaseModel(ABC):
    """数据库模型基类"""

    def __init__(self):
        self.id: Optional[int] = None

    @classmethod
    @abstractmethod
    def get_table_name(cls) -> str:
        """获取表名"""
        pass

    @classmethod
    @abstractmethod
    def from_row(cls, row) -> "BaseModel":
        """从数据库行创建对象"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass

    @abstractmethod
    def get_insert_fields(self) -> Tuple[str, tuple]:
        """获取插入字段和值
        返回: (字段名字符串, 值元组)
        """
        pass

    @abstractmethod
    def get_update_fields(self) -> Tuple[str, tuple]:
        """获取更新字段和值
        返回: (SET子句字符串, 值元组)
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


class BaseService:
    """数据库服务基类"""

    def __init__(self, model_class):
        if not issubclass(model_class, BaseModel):
            raise TypeError("model_class must be a subclass of BaseModel")

        self.model_class = model_class
        self.table_name = model_class.get_table_name()

    def create(self, obj: BaseModel) -> BaseModel:
        """创建记录"""
        if not isinstance(obj, self.model_class):
            raise TypeError(
                f"Object must be an instance of {self.model_class.__name__}"
            )

        fields, values = obj.get_insert_fields()
        placeholders = ", ".join(["?" for _ in values])

        with DatabaseConnection.get_cursor() as (cursor, conn):
            query = f"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})"
            cursor.execute(query, values)

            obj.id = cursor.lastrowid
            conn.commit()

            # 返回从数据库重新读取的对象，确保包含所有默认值和触发器结果
            return self.get_by_id(obj.id)

    def get_by_id(self, obj_id: int) -> Optional[BaseModel]:
        """根据ID获取记录"""
        if not isinstance(obj_id, int) or obj_id <= 0:
            return None

        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (obj_id,))
            row = cursor.fetchone()

            if row:
                return self.model_class.from_row(row)
            return None

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "created_at DESC",
        where_clause: str = None,
        where_params: tuple = None,
    ) -> Tuple[List[BaseModel], int]:
        """获取所有记录（分页）

        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            order_by: 排序子句
            where_clause: WHERE子句（不包含WHERE关键字）
            where_params: WHERE子句参数

        Returns:
            (记录列表, 总数)
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        offset = (page - 1) * page_size

        # 构建查询语句
        base_query = f"FROM {self.table_name}"
        count_query = f"SELECT COUNT(*) {base_query}"
        select_query = f"SELECT * {base_query}"

        params = []

        if where_clause:
            base_query += f" WHERE {where_clause}"
            count_query = f"SELECT COUNT(*) {base_query}"
            select_query = f"SELECT * {base_query}"
            if where_params:
                params.extend(where_params)

        select_query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"

        with DatabaseConnection.get_cursor() as (cursor, conn):
            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 获取分页数据
            cursor.execute(select_query, params + [page_size, offset])
            rows = cursor.fetchall()

            return [self.model_class.from_row(row) for row in rows], total

    def update(self, obj_id: int, obj: BaseModel) -> Optional[BaseModel]:
        """更新记录"""
        if not isinstance(obj_id, int) or obj_id <= 0:
            return None

        if not isinstance(obj, self.model_class):
            raise TypeError(
                f"Object must be an instance of {self.model_class.__name__}"
            )

        fields, values = obj.get_update_fields()
        values_with_id = values + (obj_id,)

        with DatabaseConnection.get_cursor() as (cursor, conn):
            query = f"UPDATE {self.table_name} SET {fields} WHERE id = ?"
            cursor.execute(query, values_with_id)

            if cursor.rowcount > 0:
                conn.commit()
                return self.get_by_id(obj_id)
            return None

    def delete(self, obj_id: int) -> bool:
        """删除记录"""
        if not isinstance(obj_id, int) or obj_id <= 0:
            return False

        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (obj_id,))

            if cursor.rowcount > 0:
                conn.commit()
                return True
            return False

    def exists(self, obj_id: int) -> bool:
        """检查记录是否存在"""
        if not isinstance(obj_id, int) or obj_id <= 0:
            return False

        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1", (obj_id,)
            )
            return cursor.fetchone() is not None

    def count(self, where_clause: str = None, where_params: tuple = None) -> int:
        """统计记录数量"""
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        params = []

        if where_clause:
            query += f" WHERE {where_clause}"
            if where_params:
                params.extend(where_params)

        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def find_by_field(self, field_name: str, field_value: Any) -> List[BaseModel]:
        """根据字段值查找记录"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            query = f"SELECT * FROM {self.table_name} WHERE {field_name} = ?"
            cursor.execute(query, (field_value,))
            rows = cursor.fetchall()

            return [self.model_class.from_row(row) for row in rows]

    def find_one_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[BaseModel]:
        """根据字段值查找单条记录"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            query = f"SELECT * FROM {self.table_name} WHERE {field_name} = ? LIMIT 1"
            cursor.execute(query, (field_value,))
            row = cursor.fetchone()

            if row:
                return self.model_class.from_row(row)
            return None
