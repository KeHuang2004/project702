import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple


from utils.database__manager.base_model import BaseService
from utils.database__manager.connection import DatabaseConnection
from data_model.chunk import Chunk
from data_model.file import File
from services.file_service import FileService
from services.knowledge_base_service import KnowledgeBaseService
from utils.request_manager.exceptions import DatabaseError, NotFoundError, ValidationError
from typing import Iterable
import os
import requests
from config import Config
from llm.API.retrieving import retrieving as llm_retrieving
from llm.API.reranking import reranking as llm_reranking


logger = logging.getLogger(__name__)

_CTT = timezone(timedelta(hours=8))
_TIME_FORMAT = "%Y年%m月%d日%H时%M分%S秒"


def _current_beijing_text() -> str:
    return datetime.now(_CTT).strftime(_TIME_FORMAT)


class ChunkService(BaseService):
    """文本块服务类"""

    def __init__(self):
        super().__init__(Chunk)
        self.kb_service = KnowledgeBaseService()
        self.file_service = FileService()

    def create_chunk(
        self,
        file_id: int,
        knowledge_base_id: int,
        chunk_text: str,
        chunk_index: int,
        start_position: int = None,
        end_position: int = None,
        faiss_vector_id: int = None,
    ) -> Chunk:
        """创建文本块"""
        # 验证文件是否存在
        if not self.file_service.exists(file_id):
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        # 验证知识库是否存在
        if not self.kb_service.exists(knowledge_base_id):
            raise NotFoundError(f"知识库 ID {knowledge_base_id} 不存在")

        # 验证文件是否属于指定的知识库
        file_obj = self.file_service.get_by_id(file_id)
        if file_obj and file_obj.knowledge_base_id != knowledge_base_id:
            raise ValidationError(
                f"文件 ID {file_id} 不属于知识库 ID {knowledge_base_id}"
            )

        # 验证必需参数
        if not chunk_text or not chunk_text.strip():
            raise ValidationError("文本块内容不能为空")

        if chunk_index is None or chunk_index < 0:
            raise ValidationError("文本块索引必须是非负整数")

        # 检查相同文件中是否已存在相同索引的chunk
        existing_chunk = self.find_by_file_and_index(file_id, chunk_index)
        if existing_chunk:
            raise ValidationError(
                f"文件 ID {file_id} 中已存在索引为 {chunk_index} 的文本块"
            )

        # 创建文本块对象
        chunk = Chunk()
        chunk.file_id = file_id
        chunk.knowledge_base_id = knowledge_base_id
        chunk.chunk_text = chunk_text.strip()
        chunk.chunk_index = chunk_index
        chunk.start_position = start_position
        chunk.end_position = end_position
        chunk.faiss_vector_id = faiss_vector_id
        chunk.created_at = _current_beijing_text()
        chunk.status = File.STATUS_SPLITTED

        # 验证数据
        errors = chunk.validate()
        if errors:
            raise ValidationError("; ".join(errors))

        try:
            return self.create(chunk)
        except Exception as e:
            raise DatabaseError(f"创建文本块失败: {str(e)}")

    def update_chunk(
        self,
        chunk_id: int,
        chunk_text: str = None,
        start_position: int = None,
        end_position: int = None,
        faiss_vector_id: int = None,
    ) -> Optional[Chunk]:
        """更新文本块"""
        # 检查文本块是否存在
        existing_chunk = self.get_by_id(chunk_id)
        if not existing_chunk:
            raise NotFoundError(f"文本块 ID {chunk_id} 不存在")

        # 准备更新数据
        update_chunk = Chunk()
        update_chunk.id = chunk_id

        if chunk_text is not None:
            chunk_text = chunk_text.strip()
            if not chunk_text:
                raise ValidationError("文本块内容不能为空")
            update_chunk.chunk_text = chunk_text

        if start_position is not None:
            if start_position < 0:
                raise ValidationError("起始位置不能为负数")
            update_chunk.start_position = start_position

        if end_position is not None:
            if end_position < 0:
                raise ValidationError("结束位置不能为负数")
            update_chunk.end_position = end_position

        if faiss_vector_id is not None:
            if faiss_vector_id < 0:
                raise ValidationError("FAISS向量ID不能为负数")
            update_chunk.faiss_vector_id = faiss_vector_id

        try:
            return self.update(chunk_id, update_chunk)
        except Exception as e:
            raise DatabaseError(f"更新文本块失败: {str(e)}")

    def delete_chunk(self, chunk_id: int) -> bool:
        """删除文本块"""
        # 检查文本块是否存在
        if not self.exists(chunk_id):
            raise NotFoundError(f"文本块 ID {chunk_id} 不存在")

        try:
            return self.delete(chunk_id)
        except Exception as e:
            raise DatabaseError(f"删除文本块失败: {str(e)}")

    def get_chunks_by_file(
        self, file_id: int, page: int = 1, page_size: int = 50
    ) -> Tuple[List[Chunk], int]:
        """根据文件ID获取文本块列表"""
        # 验证文件是否存在
        if not self.file_service.exists(file_id):
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        return self.get_all(
            page=page,
            page_size=page_size,
            where_clause="file_id = ?",
            where_params=(file_id,),
            order_by="chunk_index ASC",
        )

    def get_chunks_by_knowledge_base(
        self, knowledge_base_id: int, page: int = 1, page_size: int = 50
    ) -> Tuple[List[Chunk], int]:
        """根据知识库ID获取文本块列表"""
        # 验证知识库是否存在
        if not self.kb_service.exists(knowledge_base_id):
            raise NotFoundError(f"知识库 ID {knowledge_base_id} 不存在")

        return self.get_all(
            page=page,
            page_size=page_size,
            where_clause="knowledge_base_id = ?",
            where_params=(knowledge_base_id,),
            order_by="created_at DESC",
        )

    def search_chunks(
        self,
        keyword: str = None,
        knowledge_base_id: int = None,
        file_id: int = None,
        has_vector: bool = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Chunk], int]:
        """搜索文本块"""
        where_conditions = []
        where_params = []

        if keyword and keyword.strip():
            keyword = keyword.strip()
            where_conditions.append("chunk_text LIKE ?")
            where_params.append(f"%{keyword}%")

        if knowledge_base_id is not None:
            where_conditions.append("knowledge_base_id = ?")
            where_params.append(knowledge_base_id)

        if file_id is not None:
            where_conditions.append("file_id = ?")
            where_params.append(file_id)

        if has_vector is not None:
            if has_vector:
                where_conditions.append("faiss_vector_id IS NOT NULL")
            else:
                where_conditions.append("faiss_vector_id IS NULL")

        where_clause = " AND ".join(where_conditions) if where_conditions else None
        where_params_tuple = tuple(where_params) if where_params else None

        return self.get_all(
            page=page,
            page_size=page_size,
            where_clause=where_clause,
            where_params=where_params_tuple,
            order_by="created_at DESC",
        )

    def get_chunks_by_ids(self, chunk_ids: List[int]) -> List[Chunk]:
        if not chunk_ids:
            return []
        placeholders = ",".join(["?" for _ in chunk_ids])
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                f"SELECT * FROM chunks WHERE id IN ({placeholders})",
                tuple(chunk_ids),
            )
            rows = cursor.fetchall()
            return [Chunk.from_row(r) for r in rows]

    def embed_chunks_by_ids(
        self,
        chunk_ids: List[int],
        embedding_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对给定 chunk_id 集合执行向量嵌入：
        - 按 knowledge_base_id 分组，分别向其对应的 FAISS 索引追加向量
        - 为每个 chunk 分配新的向量ID，并将 chunk_index 更新为该向量ID
        返回：{"processed": N}
        """
        if not chunk_ids:
            return {"processed": 0}

        from config import Config as AppConfig
        model_name = embedding_model or getattr(AppConfig, "DEFAULT_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")

        # 获取 chunk 详情并分组
        chunks = self.get_chunks_by_ids(chunk_ids)
        if not chunks:
            return {"processed": 0}

        groups: Dict[int, List[Chunk]] = {}
        file_groups: Dict[int, List[Chunk]] = {}
        for c in chunks:
            groups.setdefault(int(c.knowledge_base_id), []).append(c)
            if c.file_id:
                file_groups.setdefault(int(c.file_id), []).append(c)

        from llm.Embed import Embedder
        import numpy as np
        import faiss
        import os

        total = 0
        for kb_id, items in groups.items():
            # 准备索引
            kb_index_dir = os.path.join(AppConfig.FAISS_INDEX_FOLDER, str(kb_id))
            os.makedirs(kb_index_dir, exist_ok=True)
            index_path = os.path.join(kb_index_dir, "index.faiss")
            index = None
            dim_existing = None
            start_id = 0
            if os.path.exists(index_path):
                try:
                    index = faiss.read_index(index_path)
                    dim_existing = int(index.d)
                    start_id = int(index.ntotal)
                except Exception as e:
                    raise DatabaseError(f"读取已有索引失败: {e}")

            # 文本集合
            texts = [c.chunk_text or "" for c in items]
            embedder = Embedder(model_name)

            assigned_ids: List[int] = []
            vecs_all = []
            BATCH = 10
            dim = None

            for i in range(0, len(texts), BATCH):
                batch = texts[i:i+BATCH]
                vecs = np.asarray(embedder.embed(batch), dtype=np.float32)
                if vecs.ndim != 2 or vecs.shape[0] != len(batch):
                    raise DatabaseError("嵌入返回形状异常")

                faiss.normalize_L2(vecs)

                if dim is None:
                    dim = int(vecs.shape[1])
                    if dim_existing is not None and dim_existing != dim:
                        raise DatabaseError(
                            f"索引维度不一致：已有 {dim_existing}，新增 {dim}"
                        )
                    if index is None:
                        index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))

                ids = np.arange(start_id, start_id + len(batch), dtype="int64")
                index.add_with_ids(vecs, ids)
                assigned_ids.extend(ids.tolist())
                start_id += len(batch)

            if index is not None and assigned_ids:
                faiss.write_index(index, index_path)

            # 更新每个 chunk 的索引
            for chunk, vid in zip(items, assigned_ids):
                upd = Chunk()
                upd.id = chunk.id
                upd.chunk_index = int(vid)
                self.update(chunk.id, upd)

            total += len(items)

        # 嵌入完成后，按文件检查是否全部文本块完成，更新文件状态
        for file_id in file_groups.keys():
            try:
                self._mark_file_if_completed(file_id)
            except Exception as e:
                print(f"Warning: 文件 {file_id} 完成检查失败: {e}")

        return {"processed": total}

    def embed_chunks_to_files(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按文本块逐个嵌入，并将向量写入：
        data/faiss_index/<kb_id>/<file_id>/<chunk_index>.json

        items: [{chunk_id, chunk_index, file_id}, ...]
        """
        if not items:
            return {"processed": 0, "failed": []}

        processed = 0
        failed = []

        for item in items:
            try:
                self.embed_chunk_to_file(
                    chunk_id=item.get("chunk_id"),
                    chunk_index=item.get("chunk_index"),
                    file_id=item.get("file_id"),
                )
                processed += 1
            except Exception as e:
                failed.append({"item": item, "reason": str(e)})

        return {"processed": processed, "failed": failed}

    def embed_chunks_to_files_batch(
        self, items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """批量嵌入文本块并写入文件向量，返回成功与失败列表。"""
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        if not items:
            return results, errors

        valid_items: List[Tuple[Dict[str, Any], Chunk]] = []
        texts: List[str] = []

        for item in items:
            try:
                chunk_id = int(item.get("chunk_id"))
                chunk_index = int(item.get("chunk_index"))
                file_id = int(item.get("file_id"))
            except Exception:
                errors.append({"item": item, "reason": "无效的 chunk_id/chunk_index/file_id"})
                continue

            chunk = self.get_by_id(chunk_id)
            if not chunk:
                errors.append({"item": item, "reason": f"文本块不存在: {chunk_id}"})
                continue

            if chunk.file_id != file_id:
                errors.append({"item": item, "reason": "file_id 与文本块不匹配"})
                continue

            if chunk.chunk_index != chunk_index:
                errors.append({"item": item, "reason": "chunk_index 与文本块不匹配"})
                continue

            current_status = (chunk.status or "").lower()
            if current_status not in (File.STATUS_EMBEDDING, "re-embedding"):
                errors.append({"item": item, "reason": "文本块状态不是 embedding/re-embedding"})
                continue

            if not chunk.chunk_text or not str(chunk.chunk_text).strip():
                errors.append({"item": item, "reason": "文本块内容为空"})
                continue

            valid_items.append((item, chunk))
            texts.append(chunk.chunk_text)

        if not valid_items:
            return results, errors

        vectors = self._embed_texts(texts)
        if len(vectors) != len(valid_items):
            raise DatabaseError("嵌入结果数量不一致")

        for (item, chunk), vec in zip(valid_items, vectors):
            file_id = int(item.get("file_id"))
            chunk_index = int(item.get("chunk_index"))
            kb_id = int(chunk.knowledge_base_id)

            kb_dir = os.path.join(Config.FAISS_INDEX_FOLDER, str(kb_id))
            file_dir = os.path.join(kb_dir, str(file_id))
            os.makedirs(file_dir, exist_ok=True)

            vec_path = os.path.join(file_dir, f"{chunk_index}.json")
            with open(vec_path, "w", encoding="utf-8") as f:
                json.dump({"vector": vec}, f, ensure_ascii=False)

            upd = Chunk()
            upd.id = chunk.id
            upd.embed_at = _current_beijing_text()
            upd.status = File.STATUS_EMBEDDED
            self.update(chunk.id, upd)

            results.append(
                {
                    "chunk_id": chunk.id,
                    "file_id": file_id,
                    "chunk_index": chunk_index,
                    "status": File.STATUS_EMBEDDED,
                }
            )

        return results, errors

    def embed_chunk_to_file(self, chunk_id: Any, chunk_index: Any, file_id: Any) -> Dict[str, Any]:
        """嵌入单个文本块并写入文件向量。"""
        try:
            chunk_id = int(chunk_id)
            chunk_index = int(chunk_index)
            file_id = int(file_id)
        except Exception:
            raise ValidationError("无效的 chunk_id/chunk_index/file_id")

        chunk = self.get_by_id(chunk_id)
        if not chunk:
            raise NotFoundError(f"文本块不存在: {chunk_id}")

        if chunk.file_id != file_id:
            raise ValidationError("file_id 与文本块不匹配")

        if chunk.chunk_index != chunk_index:
            raise ValidationError("chunk_index 与文本块不匹配")

        current_status = (chunk.status or "").lower()
        if current_status not in (File.STATUS_EMBEDDING, "re-embedding"):
            raise ValidationError("文本块状态不是 embedding/re-embedding")

        if not chunk.chunk_text or not str(chunk.chunk_text).strip():
            raise ValidationError("文本块内容为空")

        vectors = self._embed_texts([chunk.chunk_text])
        if not vectors:
            raise DatabaseError("嵌入结果为空")

        vec = vectors[0]
        kb_id = int(chunk.knowledge_base_id)

        kb_dir = os.path.join(Config.FAISS_INDEX_FOLDER, str(kb_id))
        file_dir = os.path.join(kb_dir, str(file_id))
        os.makedirs(file_dir, exist_ok=True)

        vec_path = os.path.join(file_dir, f"{chunk_index}.json")
        with open(vec_path, "w", encoding="utf-8") as f:
            json.dump({"vector": vec}, f, ensure_ascii=False)

        upd = Chunk()
        upd.id = chunk.id
        upd.embed_at = _current_beijing_text()
        upd.status = File.STATUS_EMBEDDED
        self.update(chunk.id, upd)

        return {
            "chunk_id": chunk.id,
            "file_id": file_id,
            "chunk_index": chunk_index,
            "status": File.STATUS_EMBEDDED,
        }

    def prepare_embedding_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """校验文本块状态并将其置为 embedding，同时更新文件状态为 embedding。"""
        if not items:
            return []

        normalized: List[Dict[str, Any]] = []
        file_ids: set[int] = set()

        for item in items:
            try:
                chunk_id = int(item.get("chunk_id"))
                chunk_index = int(item.get("chunk_index"))
                file_id = int(item.get("file_id"))
            except Exception:
                raise ValidationError("无效的 chunk_id/chunk_index/file_id")

            chunk = self.get_by_id(chunk_id)
            if not chunk:
                raise NotFoundError(f"文本块不存在: {chunk_id}")

            if chunk.file_id != file_id:
                raise ValidationError("file_id 与文本块不匹配")

            if chunk.chunk_index != chunk_index:
                raise ValidationError("chunk_index 与文本块不匹配")

            current_status = (chunk.status or "").lower()
            if current_status not in (File.STATUS_SPLITTED, File.STATUS_EMBEDDED, File.STATUS_EMBEDDING, "re-embedding"):
                raise ValidationError("文本块状态不支持嵌入")

            kb_id = int(chunk.knowledge_base_id)
            vec_path = os.path.join(
                Config.FAISS_INDEX_FOLDER,
                str(kb_id),
                str(file_id),
                f"{chunk_index}.json",
            )
            if os.path.exists(vec_path):
                try:
                    os.remove(vec_path)
                except Exception as exc:
                    raise DatabaseError(f"删除旧向量文件失败: {exc}")

            normalized.append({
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "file_id": file_id,
            })
            file_ids.add(file_id)

        # 将文本块状态置为 embedding/re-embedding
        for item in normalized:
            upd = Chunk()
            upd.id = item["chunk_id"]
            chunk = self.get_by_id(item["chunk_id"])
            current_status = (chunk.status or "").lower() if chunk else ""
            upd.status = "re-embedding" if current_status == File.STATUS_EMBEDDED else File.STATUS_EMBEDDING
            self.update(upd.id, upd)

        # 将文件状态置为 embedding
        for fid in file_ids:
            try:
                self.file_service.update_file_status(fid, File.STATUS_EMBEDDING)
            except Exception:
                pass

        return normalized

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """直接调用嵌入服务，返回向量列表"""
        if not texts:
            return []

        cfg = getattr(Config, "EMBEDDING_SERVE", {})
        host = getattr(Config, "VLLM_HOST", "127.0.0.1")
        port = int(cfg.get("port", 0) or 0)
        endpoint = f"http://{host}:{port}/v1/embeddings"
        payload = {"model": "embedding__model", "input": texts}
        try:
            resp = requests.post(endpoint, json=payload, timeout=Config.API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]
        except Exception as e:
            raise DatabaseError(f"调用嵌入服务失败: {str(e)}")

    def _mark_file_if_completed(self, file_id: int):
        """若文件所有文本块都已嵌入，则将文件状态置为 completed。"""
        # 拉取该文件所有文本块，检查 embedded 标志
        page = 1
        page_size = 200
        all_embedded = True
        while True:
            chunks, total = self.get_chunks_by_file(file_id=file_id, page=page, page_size=page_size)
            if not chunks:
                break
            for ck in chunks:
                # 由于移除了 metadata，暂时假设所有 chunk 都已嵌入
                # 如果需要，可以通过其他方式检查嵌入状态
                pass
            if not all_embedded:
                break
            if len(chunks) < page_size:
                break
            page += 1

        if all_embedded:
            try:
                from services.file_service import FileService
                fs = FileService()
                fs.update_file_status(file_id, File.STATUS_COMPLETED)
            except Exception as e:
                print(f"Warning: 更新文件 {file_id} 状态为 completed 失败: {e}")


    def find_by_file_and_index(self, file_id: int, chunk_index: int) -> Optional[Chunk]:
        """根据文件ID和块索引查找文本块"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                """
                SELECT * FROM chunks 
                WHERE file_id = ? AND chunk_index = ? 
                LIMIT 1
            """,
                (file_id, chunk_index),
            )

            row = cursor.fetchone()
            if row:
                return Chunk.from_row(row)
            return None

    def find_by_vector_id(self, faiss_vector_id: str) -> Optional[Chunk]:
        """根据FAISS向量ID查找文本块"""
        if faiss_vector_id is None:
            return None

        return self.find_one_by_field("faiss_vector_id", faiss_vector_id)

    def find_by_kb_and_chunk_index(
        self, knowledge_base_id: int, chunk_index: int
    ) -> Optional[Chunk]:
        """根据 知识库ID + chunk_index 查找文本块（无 faiss_vector_id 情况下的替代方案）"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                """
                SELECT * FROM chunks
                WHERE knowledge_base_id = ? AND chunk_index = ?
                LIMIT 1
                """,
                (knowledge_base_id, chunk_index),
            )
            row = cursor.fetchone()
            if row:
                return Chunk.from_row(row)
            return None

    def get_chunks_without_vectors(
        self, knowledge_base_id: int = None, limit: int = 100
    ) -> List[Chunk]:
        """获取没有向量的文本块"""
        where_clause = "faiss_vector_id IS NULL"
        where_params = None

        if knowledge_base_id is not None:
            where_clause += " AND knowledge_base_id = ?"
            where_params = (knowledge_base_id,)

        chunks, _ = self.get_all(
            page=1,
            page_size=limit,
            where_clause=where_clause,
            where_params=where_params,
            order_by="created_at ASC",
        )
        return chunks

    def update_vector_ids(self, chunk_vector_pairs: List[Tuple[int, int]]) -> int:
        """批量更新文本块的向量ID"""
        if not chunk_vector_pairs:
            return 0

        try:
            with DatabaseConnection.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                cursor = conn.cursor()

                updated_count = 0
                for chunk_id, vector_id in chunk_vector_pairs:
                    cursor.execute(
                        "UPDATE chunks SET faiss_vector_id = ? WHERE id = ?",
                        (vector_id, chunk_id),
                    )
                    if cursor.rowcount > 0:
                        updated_count += 1

                conn.commit()
                return updated_count

        except Exception as e:
            raise DatabaseError(f"批量更新向量ID失败: {str(e)}")

    def delete_chunks_by_file(self, file_id: int) -> int:
        """删除指定文件的所有文本块"""
        # 验证文件是否存在
        if not self.file_service.exists(file_id):
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        try:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
        except Exception as e:
            raise DatabaseError(f"删除文件的文本块失败: {str(e)}")

    def delete_chunks_by_knowledge_base(self, knowledge_base_id: int) -> int:
        """删除指定知识库的所有文本块"""
        # 验证知识库是否存在
        if not self.kb_service.exists(knowledge_base_id):
            raise NotFoundError(f"知识库 ID {knowledge_base_id} 不存在")

        try:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.execute(
                    "DELETE FROM chunks WHERE knowledge_base_id = ?",
                    (knowledge_base_id,),
                )
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
        except Exception as e:
            raise DatabaseError(f"删除知识库的文本块失败: {str(e)}")

    def get_chunk_with_context(
        self, chunk_id: int, context_size: int = 2
    ) -> Dict[str, Any]:
        """获取文本块及其上下文"""
        chunk = self.get_by_id(chunk_id)
        if not chunk:
            raise NotFoundError(f"文本块 ID {chunk_id} 不存在")

        with DatabaseConnection.get_cursor() as (cursor, conn):
            # 获取同一文件中的相邻文本块
            cursor.execute(
                """
                SELECT * FROM chunks 
                WHERE file_id = ? 
                  AND chunk_index BETWEEN ? AND ?
                ORDER BY chunk_index ASC
            """,
                (
                    chunk.file_id,
                    max(0, chunk.chunk_index - context_size),
                    chunk.chunk_index + context_size,
                ),
            )

            context_chunks = [Chunk.from_row(row) for row in cursor.fetchall()]

            # 获取文件信息
            file_obj = self.file_service.get_by_id(chunk.file_id)

            return {
                "chunk": chunk.to_dict(),
                "context_chunks": [c.to_dict() for c in context_chunks],
                "file": file_obj.to_dict() if file_obj else None,
                "context_size": context_size,
            }

    def cleanup_orphaned_chunks(self) -> int:
        """清理孤立的文本块（对应的文件不存在）"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            # 查找孤立的文本块
            cursor.execute("""
                SELECT c.id
                FROM chunks c
                LEFT JOIN files f ON c.file_id = f.id
                WHERE f.id IS NULL
            """)

            orphaned_chunk_ids = [row[0] for row in cursor.fetchall()]

            if not orphaned_chunk_ids:
                return 0

            # 删除孤立的文本块
            placeholders = ",".join(["?" for _ in orphaned_chunk_ids])
            cursor.execute(
                f"DELETE FROM chunks WHERE id IN ({placeholders})", orphaned_chunk_ids
            )

            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

    # ==================== 检索与重排 - 新增 ====================
    def count_chunks_by_knowledge_base(self, knowledge_base_id: int) -> int:
        """统计某知识库下的 chunk 总数"""
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT COUNT(*) FROM chunks WHERE knowledge_base_id = ?",
                (knowledge_base_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    def process_retrieving(self, kb_id: int, query: str, top_k: int) -> list:
        """
        调用 LLM 检索，返回基础检索结果：包含 chunk 基本信息与 retrieved_score。

        返回：[{chunk_id, file_id, file_name, file_type, knowledge_base_id, chunk_text,
               chunk_index, start_position, end_position, created_at,
               retrieved_score}]
        """
        if not query or not str(query).strip():
            raise ValidationError("查询内容不能为空")

        # 获取知识库与模型
        kb = self.kb_service.get_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")
        # 嵌入模型使用系统配置的默认值，不再依赖知识库记录
        embedding_model = getattr(Config, "DEFAULT_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")

        # 以 kb_id 作为索引目录
        faiss_index_path = os.path.join(Config.FAISS_INDEX_FOLDER, str(kb_id))

        # 调用检索服务，获得 [(chunk_index, retrieved_score), ...]
        try:
            pairs = llm_retrieving(
                faiss_index_path=faiss_index_path,
                embedding_model=embedding_model,
                query=query,
                top_k=int(top_k),
            )
        except FileNotFoundError as e:
            raise NotFoundError(f"FAISS 索引不存在: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"调用检索服务失败: {str(e)}")

        results = []
        for vector_index, retrieved_score in pairs or []:
            chunk = self.find_by_kb_and_chunk_index(knowledge_base_id=kb_id, chunk_index=int(vector_index))
            if not chunk:
                continue
            # 获取文件信息
            file_info = self.file_service.get_by_id(chunk.file_id) if self.file_service else None
            item = {
                "chunk_id": chunk.id,
                "file_id": chunk.file_id,
                "file_name": getattr(file_info, "filename", None) if file_info else None,
                "file_type": getattr(file_info, "file_type", None) if file_info else None,
                "knowledge_base_id": chunk.knowledge_base_id,
                "chunk_text": chunk.chunk_text,
                "chunk_index": chunk.chunk_index,
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "created_at": chunk.created_at,
                "retrieved_score": float(retrieved_score) if retrieved_score is not None else None,
            }
            results.append(item)

        return results

    def process_reranking(self, query: str, chunks: Iterable[dict]) -> list:
        """
        调用 LLM 重排，根据 query 与 chunks 的文本进行 rerank，返回包含 reranked_score 的列表，顺序按 reranked_score 降序。

        输入 chunks 为包含 'chunk_text' 的字典集合。
        """
        texts = [c.get("chunk_text", "") for c in chunks]
        if not any(t.strip() for t in texts):
            return []

        try:
            reranked = llm_reranking(query=query, retrieved_chunks=texts)
            # reranked: List[Tuple[score, text]] 已按分数降序
        except Exception as e:
            raise DatabaseError(f"调用重排服务失败: {str(e)}")

        # 将分数回填到对应 chunk。处理重复文本：采用 FIFO 匹配
        text_to_indices = {}
        for idx, c in enumerate(chunks):
            t = c.get("chunk_text", "")
            text_to_indices.setdefault(t, []).append(idx)

        chunks_list = list(chunks)
        for score, text in reranked:
            indices = text_to_indices.get(text) or []
            if not indices:
                continue
            use_idx = indices.pop(0)
            chunks_list[use_idx]["reranked_score"] = float(score)

        # 默认无分数的置 0，便于排序
        for c in chunks_list:
            if c.get("reranked_score") is None:
                c["reranked_score"] = 0.0

        chunks_list.sort(key=lambda x: x.get("reranked_score", 0.0), reverse=True)
        return chunks_list

    def rebuild_chunk_indexes(self, file_id: int) -> int:
        """重建文件的文本块索引"""
        # 验证文件是否存在
        if not self.file_service.exists(file_id):
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        try:
            with DatabaseConnection.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                cursor = conn.cursor()

                # 获取文件的所有文本块，按创建时间排序
                cursor.execute(
                    """
                    SELECT id FROM chunks 
                    WHERE file_id = ? 
                    ORDER BY created_at ASC
                """,
                    (file_id,),
                )

                chunk_ids = [row[0] for row in cursor.fetchall()]

                # 重新分配索引
                updated_count = 0
                for new_index, chunk_id in enumerate(chunk_ids):
                    cursor.execute(
                        "UPDATE chunks SET chunk_index = ? WHERE id = ?",
                        (new_index, chunk_id),
                    )
                    if cursor.rowcount > 0:
                        updated_count += 1

                conn.commit()
                return updated_count

        except Exception as e:
            raise DatabaseError(f"重建文本块索引失败: {str(e)}")
