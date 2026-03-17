import os
import json
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

from utils.database__manager.base_model import BaseService
from utils.database__manager.connection import DatabaseConnection
from data_model.knowledge_base import KnowledgeBase


logger = logging.getLogger(__name__)

_CTT = timezone(timedelta(hours=8))
_TIME_FORMAT = "%Y年%m月%d日%H时%M分%S秒"


def _current_beijing_text() -> str:
    return datetime.now(_CTT).strftime(_TIME_FORMAT)


class KnowledgeBaseService(BaseService):
    """知识库服务"""

    def __init__(self):
        super().__init__(KnowledgeBase)
    def create_knowledge_base(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> KnowledgeBase:
        """创建知识库"""

        # 创建知识库对象
        kb = KnowledgeBase()
        kb.name = name.strip()
        kb.description = description.strip() if description else None
        kb.total_size = 0
        kb.files_list = []
        kb.chunks_list = []
        kb.created_at = _current_beijing_text()

        try:
            # 保存到数据库并获取自增 ID
            created_kb = cast(KnowledgeBase, self.create(kb))

            from config import Config

            kb_dir = os.path.join(Config.FAISS_INDEX_FOLDER, str(created_kb.id))
            try:
                os.makedirs(kb_dir, exist_ok=True)
            except Exception as e:
                # 目录创建失败时回滚数据库记录
                try:
                    self.delete(created_kb.id)
                except Exception:
                    pass
                raise Exception("创建知识库索引目录失败: " + str(e))

            # 同时创建以知识库 ID 为名的上传目录 data/uploads/{kb_id}
            try:
                uploads_dir = os.path.join(Config.UPLOAD_FOLDER, str(created_kb.id))
                os.makedirs(uploads_dir, exist_ok=True)
            except Exception as e:
                # 如果创建 uploads 目录失败，也回滚数据库与已创建的 faiss 目录
                try:
                    import shutil

                    if os.path.exists(kb_dir):
                        shutil.rmtree(kb_dir)
                    self.delete(created_kb.id)
                except Exception:
                    pass
                raise Exception("创建知识库上传目录失败: " + str(e))

            return created_kb

        except Exception as e:
            raise Exception("创建知识库失败: " + str(e))

    def update_knowledge_base(
        self,
        kb_id: int,
        name: str,
        description: Optional[str] = None,
    ) -> Optional[KnowledgeBase]:
        """更新知识库，主要更新名称和描述"""
        from config import Config

        existing_kb = cast(Optional[KnowledgeBase], self.get_by_id(kb_id))
        if not existing_kb:
            return None

        # 验证名称
        name = name.strip()
        if not name:
            return None

        def safe_name_func(n: str) -> str:
            return (
                ("".join(c for c in n if c.isalnum() or c in (" ", "-", "_")))
                .rstrip()
                .replace(" ", "_")
            )

        old_safe_name = safe_name_func(existing_kb.name or "")
        new_safe_name = safe_name_func(name)
        kb_dir_old = f"{old_safe_name}_{kb_id}"
        kb_dir_new = f"{new_safe_name}_{kb_id}"

        uploads_base = Config.UPLOAD_FOLDER
        old_upload_dir = os.path.join(uploads_base, kb_dir_old)
        new_upload_dir = os.path.join(uploads_base, kb_dir_new)
        if os.path.exists(old_upload_dir) and old_upload_dir != new_upload_dir:
            try:
                os.rename(old_upload_dir, new_upload_dir)
            except Exception as e:
                raise Exception(f"重命名 uploads 目录失败: {str(e)}")

        # 更新字段
        update_kb = KnowledgeBase()
        update_kb.id = kb_id
        update_kb.name = name
        update_kb.description = description.strip() if description else None

        try:
            return cast(Optional[KnowledgeBase], self.update(kb_id, update_kb))
        except Exception as e:
            raise Exception(f"更新知识库失败: {str(e)}")

    def update_knowledge_base_size(
        self, kb_id: int, size: int
    ) -> Optional[KnowledgeBase]:
        """
        更新知识库的总大小
        """

        kb = cast(Optional[KnowledgeBase], self.get_by_id(kb_id))
        if not kb:
            return False

        new_size = (kb.total_size or 0) + (size or 0)
        if new_size < 0:
            new_size = 0

        try:
            update_kb = KnowledgeBase()
            update_kb.id = kb_id
            update_kb.total_size = new_size
            return cast(Optional[KnowledgeBase], self.update(kb_id, update_kb))
        except Exception as e:
            raise Exception(f"更新知识库大小失败: {str(e)}")

    def delete_knowledge_base(self, kb_id: int) -> bool:
        """
        删除知识库，清理 FAISS 索引、uploads 目录、相关文件和文本块
        """
        # 检查知识库是否存在
        kb = cast(Optional[KnowledgeBase], self.get_by_id(kb_id))
        if not kb:
            return False

        try:
            import shutil
            from services.file_service import FileService

            # 先删除所有相关文件（这会级联删除chunks并更新知识库）
            file_service = FileService()
            files = file_service.get_files_by_knowledge_base(kb_id)
            for file_obj in files[0]:  # files[0] 是文件列表
                file_service.delete_file_and_related(file_obj.id, delete_physical_file=False)  # 不删除物理文件，因为下面会删除整个目录

            # 删除 FAISS 索引目录（按知识库 ID 命名）
            from config import Config

            kb_faiss_dir = os.path.join(Config.FAISS_INDEX_FOLDER, str(kb_id))
            if os.path.exists(kb_faiss_dir):
                shutil.rmtree(kb_faiss_dir)

            # 删除 uploads 目录下对应知识库的文件
            safe_name_src = kb.name or ""
            safe_name = (
                "".join(c for c in safe_name_src if c.isalnum() or c in (" ", "-", "_"))
                .rstrip()
                .replace(" ", "_")
            )
            kb_dir_name = f"{safe_name}_{kb_id}"

            uploads_base = Config.UPLOAD_FOLDER
            # 考虑两种目录命名：safe_name_{id} 与 {id}
            kb_upload_dir_named = os.path.join(uploads_base, kb_dir_name)
            kb_upload_dir_idonly = os.path.join(uploads_base, str(kb_id))
            for path in {kb_upload_dir_named, kb_upload_dir_idonly}:
                if os.path.exists(path):
                    shutil.rmtree(path)

            # 删除数据库记录
            return self.delete(kb_id)

        except Exception as e:
            raise Exception(f"删除知识库失败: {str(e)}")
        
    def retrieve_by_cosine(self, kb_id: int, query: str, top_k: int = 5, threshold: float = None) -> Dict[str, Any]:
        """基于余弦相似度检索知识库文本块。"""
        from utils.request_manager.exceptions import NotFoundError, ValidationError
        from services.chunk_service import ChunkService
        from llm.Embed import Embedder
        from config import Config
        from llm.API.reranking import reranking
        if kb_id is None:
            raise ValidationError("知识库ID不能为空")

        if not query or not str(query).strip():
            raise ValidationError("查询内容不能为空")

        if top_k is None:
            top_k = 5

        try:
            top_k = int(top_k)
        except Exception:
            raise ValidationError("top_k 必须为整数")

        if top_k <= 0:
            raise ValidationError("top_k 必须大于 0")

        if threshold is not None:
            try:
                threshold = float(threshold)
            except Exception:
                raise ValidationError("threshold 必须为数值")
            if threshold < 0 or threshold > 1:
                raise ValidationError("threshold 必须在 0-1 之间")

        kb = self.get_by_id(int(kb_id))
        if not kb:
            raise NotFoundError("知识库不存在")

        chunk_ids = kb.chunks_list or []
        if not chunk_ids:
            return {"results": []}

        embedder = Embedder(getattr(Config, "DEFAULT_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B"))
        query_vecs = embedder.embed([query])
        if not query_vecs:
            return {"results": []}
        q = np.asarray(query_vecs[0], dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return {"results": []}

        chunk_service = ChunkService()
        chunks = chunk_service.get_chunks_by_ids(chunk_ids)
        results = []

        for ck in chunks:
            try:
                vec_path = os.path.join(
                    Config.FAISS_INDEX_FOLDER,
                    str(int(ck.knowledge_base_id)),
                    str(int(ck.file_id)),
                    f"{int(ck.chunk_index)}.json",
                )
                if not os.path.exists(vec_path):
                    continue

                with open(vec_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                vec = payload.get("vector")
                if vec is None:
                    continue

                v = np.asarray(vec, dtype=np.float32)
                v_norm = np.linalg.norm(v)
                if v_norm == 0:
                    continue

                score = float(np.dot(q, v) / (q_norm * v_norm))
                if threshold is not None and score < threshold:
                    continue
                results.append({
                    "chunk_id": ck.id,
                    "retrieved_score": score,
                    "chunk_text": ck.chunk_text,
                })
            except Exception:
                continue

        if not results:
            return {"results": []}

        # 重排：调用 reranker 并回填 reranked_score
        texts = [r.get("chunk_text", "") for r in results]
        try:
            reranked = reranking(query=query, retrieved_chunks=texts)
        except Exception as e:
            logger.warning(f"rerank 失败，降级为检索排序: {e}")
            reranked = []

        text_to_indices: Dict[str, List[int]] = {}
        for idx, r in enumerate(results):
            t = r.get("chunk_text", "")
            text_to_indices.setdefault(t, []).append(idx)

        for score, text in reranked:
            indices = text_to_indices.get(text) or []
            if not indices:
                continue
            use_idx = indices.pop(0)
            results[use_idx]["reranked_score"] = float(score)

        for r in results:
            if r.get("reranked_score") is None:
                r["reranked_score"] = r.get("retrieved_score", 0.0)

        results.sort(key=lambda x: x.get("reranked_score", 0.0), reverse=True)
        # 最终只返回分数与 chunk_id
        trimmed = []
        for r in results[:top_k]:
            trimmed.append({
                "chunk_id": r.get("chunk_id"),
                "retrieved_score": r.get("retrieved_score", 0.0),
                "reranked_score": r.get("reranked_score", 0.0),
            })
        return {"results": trimmed}

    def get_knowledge_base_statistics(self) -> Dict[str, Any]:
        """
        获取整体知识库的统计信息
        """
        with DatabaseConnection.get_cursor() as (cursor, conn):
            # 获取总体统计信息
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM knowledge_bases) as knowledge_base_count,
                    (SELECT COUNT(*) FROM files) as document_count,
                    (SELECT COALESCE(SUM(total_size), 0) FROM knowledge_bases) as knowledge_size
            """)

            stats = cursor.fetchone()

            if stats:
                return {
                    "knowledge_base_count": stats["knowledge_base_count"] or 0,
                    "document_count": stats["document_count"] or 0,
                    "knowledge_size": stats["knowledge_size"] or 0,
                    "statistics_chart_url": "http://127.0.0.1:5000/image/wordcloud.png",
                }
            else:
                return {
                    "knowledge_base_count": 0,
                    "document_count": 0,
                    "knowledge_size": 0,
                    "statistics_chart_url": "http://127.0.0.1:5000/image/wordcloud.png",
                }

    def exists_by_name(self, name: str) -> bool:
        """
        检查知识库名称是否存在
        """
        if not name:
            return False

        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT 1 FROM knowledge_bases WHERE name = ? LIMIT 1", (name.strip(),)
            )
            return cursor.fetchone() is not None

    def search_knowledge_bases(self) -> Tuple[List[KnowledgeBase], int]:
        """
        获取所有知识库条目
        """
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute("SELECT * FROM knowledge_bases ORDER BY created_at DESC")
            rows = cursor.fetchall()
            items = [KnowledgeBase.from_row(row) for row in rows]
            return items, len(items)

    def export_knowledge_base_config(self, kb_id: int) -> Dict[str, Any]:
        """
        导出知识库配置
        """
        kb = self.get_by_id(kb_id)
        if not kb:
            raise Exception(f"知识库ID {kb_id} 不存在")

        config = kb.to_dict()

        # 删除导出时不需要的字段
        config.pop("id", None)
        config.pop("created_at", None)
        config.pop("updated_at", None)
        config.pop("faiss_index_path", None)  # 璺緞涓嶅簲璇ュ鍑?

        return config

    def import_knowledge_base_config(self, config: Dict[str, Any]) -> KnowledgeBase:
        """
        导入知识库配置
        """
        required_fields = ["name"]
        for field in required_fields:
            if field not in config:
                raise Exception(f"配置中缺少必填字段: {field}")

        return self.create_knowledge_base(
            name=config["name"],
            description=config.get("description"),
        )


