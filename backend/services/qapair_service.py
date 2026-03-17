import json
from typing import List, Dict, Tuple

from utils.request_manager.exceptions import FileProcessingError
from utils.database__manager.connection import DatabaseConnection


class QApairService:
    """QApair 业务：解析上传的 JSON 文件，提取问答对并存入数据库；提供查询与删除。"""

    def import_files(self, uploaded_files) -> Dict:
        """解析上传的多个 JSON 文件，批量写入数据库。

        Args:
            uploaded_files: werkzeug FileStorage 列表

        Returns:
            {"inserted": int, "files": int}
        """
        if not uploaded_files:
            raise FileProcessingError("没有上传文件")

        total_pairs: List[Tuple[str, str]] = []
        file_count = 0

        for f in uploaded_files:
            filename = getattr(f, "filename", None) or ""
            if not filename.lower().endswith(".json"):
                raise FileProcessingError(f"不支持的文件类型: {filename}")

            try:
                content = f.read()
                if isinstance(content, bytes):
                    text = content.decode("utf-8")
                else:
                    text = str(content)

                obj = json.loads(text)
            except Exception as e:
                raise FileProcessingError(f"文件不是合法的 JSON: {filename}, 错误: {e}")

            pairs = self._normalize(obj)
            # 仅保留有 question 的项
            for item in pairs:
                q = (item.get("q") or item.get("question") or "").strip()
                a = (item.get("a") or item.get("answer") or "").strip()
                if q:
                    total_pairs.append((q, a))

            file_count += 1

        inserted = 0
        if total_pairs:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.executemany(
                    "INSERT INTO qapairs (question, answer) VALUES (?, ?)",
                    total_pairs,
                )
                inserted = cursor.rowcount if cursor.rowcount is not None else len(total_pairs)
                conn.commit()

        return {"inserted": inserted, "files": file_count}

    def get_all_pairs(self) -> List[Dict]:
        rows = DatabaseConnection.execute_query(
            "SELECT id, question, answer FROM qapairs ORDER BY id ASC",
            (),
            fetch_all=True,
        )
        return [
            {"id": r["id"], "question": r["question"], "answer": r["answer"]}
            for r in rows
        ]

    def get_pair_by_id(self, qa_id: int) -> Dict | None:
        if not isinstance(qa_id, int) or qa_id <= 0:
            return None
        row = DatabaseConnection.execute_query(
            "SELECT id, question, answer FROM qapairs WHERE id = ?",
            (qa_id,),
            fetch_one=True,
            fetch_all=False,
        )
        if not row:
            return None
        return {"id": row["id"], "question": row["question"], "answer": row["answer"]}

    def delete_pair(self, qa_id: int) -> bool:
        if not isinstance(qa_id, int) or qa_id <= 0:
            raise FileProcessingError("无效的ID")
        affected = DatabaseConnection.execute_delete(
            "DELETE FROM qapairs WHERE id = ?", (qa_id,)
        )
        return affected > 0

    def update_pair(self, qa_id: int, question: str, answer: str) -> bool:
        if not isinstance(qa_id, int) or qa_id <= 0:
            raise FileProcessingError("无效的ID")
        q = (question or "").strip()
        a = (answer or "").strip()
        if not q:
            raise FileProcessingError("question 不能为空")
        affected = DatabaseConnection.execute_update(
            "UPDATE qapairs SET question = ?, answer = ? WHERE id = ?",
            (q, a, qa_id),
        )
        return affected > 0

    def _normalize(self, data) -> List[Dict]:
        """把各种 JSON 结构转换为统一的 [{q,a}, ...] 格式"""
        results: List[Dict] = []

        def extract_qa_from_obj(obj):
            if not isinstance(obj, dict):
                return None
            q = None
            a = None
            q_keys = ["q", "Q", "question", "Question", "问", "问题"]
            a_keys = ["a", "A", "answer", "Answer", "答", "回答"]
            for k in q_keys:
                if k in obj and obj[k] is not None:
                    q = obj[k]
                    break
            for k in a_keys:
                if k in obj and obj[k] is not None:
                    a = obj[k]
                    break
            if q is None:
                for k in ("prompt", "input"):
                    if k in obj:
                        q = obj[k]
                        break
            if a is None:
                for k in ("result", "output"):
                    if k in obj:
                        a = obj[k]
                        break
            if q is None and a is None:
                return None
            return {"q": str(q), "a": str(a) if a is not None else ""}

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    qa = extract_qa_from_obj(item)
                    if qa:
                        results.append(qa)
                elif isinstance(item, list) and len(item) >= 2:
                    results.append({"q": str(item[0]), "a": str(item[1])})
        elif isinstance(data, dict):
            if "pairs" in data and isinstance(data["pairs"], list):
                for item in data["pairs"]:
                    if isinstance(item, dict):
                        qa = extract_qa_from_obj(item)
                        if qa:
                            results.append(qa)
            else:
                all_string_values = all(
                    isinstance(v, (str, int, float, bool, type(None)))
                    for v in data.values()
                )
                if all_string_values:
                    for k, v in data.items():
                        results.append({"q": str(k), "a": "" if v is None else str(v)})
                else:
                    for v in data.values():
                        if isinstance(v, dict):
                            qa = extract_qa_from_obj(v)
                            if qa:
                                results.append(qa)

        return results
