import glob
import os
from typing import Dict, List, Optional

from tinydb import Query, TinyDB
from tinydb.storages import JSONStorage


class TinyDBManager:
    """
    TinyDB 按会话分文件管理器。

    - 基础目录来自传入的 db_path 的目录名（例如 ./data/tinydb）。
    - 每个会话一个 JSON 文件：<session_id>.json，内部包含两个表：session（单条）、messages（多条）。
    - 会话列表通过扫描目录的 *.json 文件并读取各自的 session 表得到。
    """

    def __init__(self, db_path: str):
        self.base_dir = os.path.dirname(db_path)
        os.makedirs(self.base_dir, exist_ok=True)
        self.query = Query()

    # -------------------- 辅助工具 --------------------
    def _session_file(self, session_id: int) -> str:
        return os.path.join(self.base_dir, f"{session_id}.json")

    def _open_session_db(self, session_id: int) -> TinyDB:
        return TinyDB(self._session_file(session_id), storage=JSONStorage)

    def _list_session_files(self) -> List[str]:
        return sorted(glob.glob(os.path.join(self.base_dir, "*.json")))

    def _get_next_session_id(self) -> int:
        try:
            files = self._list_session_files()
            ids = []
            for f in files:
                name = os.path.splitext(os.path.basename(f))[0]
                if name.isdigit():
                    ids.append(int(name))
            return (max(ids) + 1) if ids else 1
        except Exception as e:
            print(f"计算下一个会话ID失败: {e}")
            return 1

    def _get_next_message_id(self, session_id: int) -> int:
        try:
            with self._open_session_db(session_id) as db:
                table = db.table("messages")
                all_msgs = table.all()
                if not all_msgs:
                    return 1
                return max(m.get("id", 0) for m in all_msgs) + 1
        except Exception as e:
            print(f"计算下一个消息ID失败: {e}")
            return 1

    # -------------------- 会话操作 --------------------
    def create_session(self, session_data: Dict) -> Optional[int]:
        try:
            next_id = self._get_next_session_id()
            session_data["id"] = next_id

            with self._open_session_db(next_id) as db:
                s_table = db.table("session")
                s_table.insert(session_data)
                # 消息表初始化为空，TinyDB 无需提前建表
            print(f"创建会话成功: ID={next_id}, file={self._session_file(next_id)}")
            return next_id
        except Exception as e:
            print(f"创建会话时出错: {str(e)}")
            return None

    def get_session(self, session_id: int) -> Optional[Dict]:
        try:
            path = self._session_file(session_id)
            if not os.path.exists(path):
                return None
            with self._open_session_db(session_id) as db:
                s_table = db.table("session")
                result = s_table.search(self.query.id == session_id)
                return result[0] if result else None
        except Exception as e:
            print(f"获取会话时出错: {str(e)}")
            return None

    def get_all_sessions(self) -> List[Dict]:
        try:
            sessions: List[Dict] = []
            for f in self._list_session_files():
                try:
                    sid_str = os.path.splitext(os.path.basename(f))[0]
                    if not sid_str.isdigit():
                        continue
                    sid = int(sid_str)
                    with TinyDB(f, storage=JSONStorage) as db:
                        s_table = db.table("session")
                        result = s_table.search(self.query.id == sid)
                        if result:
                            sessions.append(result[0])
                except Exception as inner:
                    print(f"读取会话文件失败 {f}: {inner}")
            # 按ID从大到小排序
            sessions.sort(key=lambda x: x.get("id", 0), reverse=True)
            return sessions
        except Exception as e:
            print(f"获取所有会话时出错: {str(e)}")
            return []

    def update_session(self, session_id: int, session_data: Dict) -> Optional[Dict]:
        try:
            path = self._session_file(session_id)
            if not os.path.exists(path):
                return None
            with self._open_session_db(session_id) as db:
                s_table = db.table("session")
                if "id" in session_data:
                    session_data.pop("id")
                s_table.update(session_data, self.query.id == session_id)
                result = s_table.search(self.query.id == session_id)
                return result[0] if result else None
        except Exception as e:
            print(f"更新会话时出错: {str(e)}")
            return None

    def delete_session(self, session_id: int) -> None:
        try:
            path = self._session_file(session_id)
            if os.path.exists(path):
                os.remove(path)
                print(f"删除会话 {session_id} 成功，文件已移除")
        except Exception as e:
            print(f"删除会话时出错: {str(e)}")

    # -------------------- 消息操作 --------------------
    def add_message(self, message_data: Dict) -> Optional[int]:
        try:
            session_id = int(message_data.get("session_id"))
            if not self.get_session(session_id):
                return None
            next_id = self._get_next_message_id(session_id)
            message_data["id"] = next_id
            with self._open_session_db(session_id) as db:
                m_table = db.table("messages")
                m_table.insert(message_data)
            print(f"添加消息成功: session={session_id}, ID={next_id}")
            return next_id
        except Exception as e:
            print(f"添加消息时出错: {str(e)}")
            return None

    def get_session_messages(self, session_id: int) -> List[Dict]:
        try:
            if not self.get_session(session_id):
                return []
            with self._open_session_db(session_id) as db:
                m_table = db.table("messages")
                messages = m_table.all()
                messages.sort(key=lambda x: x.get("id", 0))
                return messages
        except Exception as e:
            print(f"获取会话消息时出错: {str(e)}")
            return []

    def get_message(self, message_id: int):
        """跨所有会话尝试查找指定消息ID（可能较慢）。"""
        try:
            for f in self._list_session_files():
                try:
                    with TinyDB(f, storage=JSONStorage) as db:
                        m_table = db.table("messages")
                        result = m_table.search(self.query.id == message_id)
                        if result:
                            return result[0]
                except Exception:
                    continue
            return None
        except Exception as e:
            print(f"获取消息时出错: {str(e)}")
            return None

    def close(self):
        """兼容旧接口：分文件模式无需持久连接，留空。"""
        return None
