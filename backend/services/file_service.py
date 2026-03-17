from __future__ import annotations

import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from config import Config
from data_model.file import File
from data_model.knowledge_base import KnowledgeBase
from llm.Split.files_loader import FileLoader
from llm.Split.splitter_factory import SplitterFactory
from services.knowledge_base_service import KnowledgeBaseService
from utils.database__manager.base_model import BaseService
from utils.database__manager.connection import DatabaseConnection
from utils.file_manager.file_manager import (
    get_file_type,
    save_uploaded_file,
    delete_file_safely,
    resolve_upload_path,
    save_uploaded_file_to_path,
)
from utils.request_manager.exceptions import (
    DatabaseError,
    FileProcessingError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_chunk_service: "ChunkService | None" = None

_CTT = timezone(timedelta(hours=8))
_TIME_FORMAT = "%Y年%m月%d日%H时%M分%S秒"


def _current_beijing_text() -> str:
    return datetime.now(_CTT).strftime(_TIME_FORMAT)


def _get_chunk_service():
    global _chunk_service
    if _chunk_service is None:
        from services.chunk_service import ChunkService

        _chunk_service = ChunkService()
    return _chunk_service


class FileService(BaseService):
    """Service responsible for file ingestion and sequential processing."""

    def __init__(self) -> None:
        super().__init__(File)
        self.kb_service = KnowledgeBaseService()
    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_strategy(strategy: Optional[str]) -> str:
        if not strategy:
            return "recursive_character"
        return str(strategy).strip() or "recursive_character"

    @staticmethod
    def _normalise_chunk_length(length: Optional[int]) -> int:
        try:
            value = int(length) if length is not None else 512
        except (TypeError, ValueError):
            value = 512
        return max(value, 64)

    @staticmethod
    def _normalise_overlap(overlap: Optional[int], chunk_length: int) -> int:
        try:
            value = int(overlap) if overlap is not None else min(64, chunk_length // 4)
        except (TypeError, ValueError):
            value = min(64, chunk_length // 4)
        value = max(value, 0)
        return min(value, chunk_length - 1) if chunk_length > 1 else 0

    # ------------------------------------------------------------------
    # Upload entry point
    # ------------------------------------------------------------------
    def handle_upload(
        self,
        knowledge_base_id: int,
        files: Sequence[Any],
        segmentation_strategy: Optional[str] = None,
        chunk_length: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not files:
            raise ValidationError("缺少上传文件")

        kb_id = int(knowledge_base_id)
        if not self.kb_service.exists(kb_id):
            raise NotFoundError(f"知识库 {kb_id} 不存在")

        # 上传阶段不记录切分参数
        strategy = None
        effective_length = None
        effective_overlap = None

        stored: List[Dict[str, Any]] = []
        prepared: List[Dict[str, Any]] = []

        # 先创建记录（status=uploading）
        for payload in files:
            filename = getattr(payload, "filename", None) or getattr(payload, "name", "")
            if not filename:
                raise ValidationError("无法确定文件名")

            file_path, final_filename = resolve_upload_path(kb_id, filename)
            file_type = get_file_type(final_filename)

            file_obj = File()
            file_obj.knowledge_base_id = kb_id
            file_obj.filename = final_filename
            file_obj.file_path = file_path
            file_obj.file_type = file_type
            file_obj.file_size = 0
            file_obj.status = File.STATUS_UPLOADING
            file_obj.segmentation_strategy = None
            file_obj.chunk_length = None
            file_obj.overlap_count = None
            file_obj.chunks_list = []

            errors = file_obj.validate()
            if errors:
                raise ValidationError("; ".join(errors))

            created = self.create(file_obj)
            self._append_file_reference(kb_id, created.id)

            prepared.append(
                {
                    "payload": payload,
                    "file_id": created.id,
                    "file_path": file_path,
                    "filename": final_filename,
                    "file_type": file_type,
                }
            )
            stored.append(
                {
                    "file_id": created.id,
                    "filename": final_filename,
                    "status": File.STATUS_UPLOADING,
                    "file_size": 0,
                    "file_type": file_type,
                }
            )

        # 再逐个保存物理文件并更新状态
        for item in prepared:
            try:
                save_uploaded_file_to_path(item["payload"], item["file_path"])
                file_size = os.path.getsize(item["file_path"])

                update = File()
                update.id = item["file_id"]
                update.file_size = file_size
                update.status = File.STATUS_UPLOADED
                update.upload_at = _current_beijing_text()
                self.update(item["file_id"], update)

                self._increment_kb_size(kb_id, file_size)

                for rec in stored:
                    if rec.get("file_id") == item["file_id"]:
                        rec["status"] = File.STATUS_UPLOADED
                        rec["file_size"] = file_size
                        break
            except Exception:
                fail_update = File()
                fail_update.id = item["file_id"]
                fail_update.status = File.STATUS_FAILED
                self.update(item["file_id"], fail_update)
                for rec in stored:
                    if rec.get("file_id") == item["file_id"]:
                        rec["status"] = File.STATUS_FAILED
                        break

        return {
            "success": True,
            "knowledge_base_id": kb_id,
            "files": stored,
        }

    def _store_single_file(
        self,
        kb_id: int,
        payload: Any,
        segmentation_strategy: str,
        chunk_length: int,
        chunk_overlap: int,
    ) -> Dict[str, Any]:
        filename = getattr(payload, "filename", None) or getattr(payload, "name", "")
        if not filename:
            raise ValidationError("无法确定文件名")

        file_path, final_filename = resolve_upload_path(kb_id, filename)
        file_type = get_file_type(final_filename)

        file_obj = File()
        file_obj.knowledge_base_id = kb_id
        file_obj.filename = final_filename
        file_obj.file_path = file_path
        file_obj.file_type = file_type
        file_obj.file_size = 0
        file_obj.status = File.STATUS_UPLOADING
        file_obj.segmentation_strategy = segmentation_strategy
        file_obj.chunk_length = chunk_length
        file_obj.overlap_count = chunk_overlap
        file_obj.chunks_list = []

        errors = file_obj.validate()
        if errors:
            raise ValidationError("; ".join(errors))

        created = self.create(file_obj)
        self._append_file_reference(kb_id, created.id)

        try:
            save_uploaded_file_to_path(payload, file_path)
            file_size = os.path.getsize(file_path)

            update = File()
            update.id = created.id
            update.file_size = file_size
            update.status = File.STATUS_UPLOADED
            update.upload_at = _current_beijing_text()
            self.update(created.id, update)

            self._increment_kb_size(kb_id, file_size)

            return {
                "file_id": created.id,
                "filename": final_filename,
                "status": File.STATUS_UPLOADED,
                "file_size": file_size,
                "file_type": file_type,
            }
        except Exception as exc:
            fail_update = File()
            fail_update.id = created.id
            fail_update.status = File.STATUS_FAILED
            self.update(created.id, fail_update)
            raise exc

    def _append_file_reference(self, kb_id: int, file_id: Optional[int]) -> None:
        if not file_id:
            return
        try:
            kb = self.kb_service.get_by_id(kb_id)
            if not kb:
                return
            files = list(kb.files_list or [])
            if file_id in files:
                return
            files.append(file_id)
            update = KnowledgeBase()
            update.id = kb_id
            update.files_list = files
            self.kb_service.update(kb_id, update)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("append file reference failed kb=%s file=%s: %s", kb_id, file_id, exc)

    def _append_chunk_references(self, kb_id: int, chunk_ids: Iterable[int]) -> None:
        if not chunk_ids:
            return
        try:
            kb = self.kb_service.get_by_id(kb_id)
            if not kb:
                return
            existing = list(kb.chunks_list or [])
            existing_set = set(existing)
            updated = False
            for chunk_id in chunk_ids:
                if not chunk_id:
                    continue
                if chunk_id in existing_set:
                    continue
                existing.append(chunk_id)
                existing_set.add(chunk_id)
                updated = True
            if not updated:
                return
            update = KnowledgeBase()
            update.id = kb_id
            update.chunks_list = existing
            self.kb_service.update(kb_id, update)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("append chunk references failed kb=%s: %s", kb_id, exc)

    def _refresh_kb_files_list(self, kb_id: int) -> None:
        try:
            with DatabaseConnection.get_cursor() as (cursor, _):
                cursor.execute(
                    "SELECT id FROM files WHERE knowledge_base_id = ? ORDER BY id ASC",
                    (kb_id,),
                )
                ids = [int(row["id"]) for row in cursor.fetchall() if row["id"] is not None]
            update = KnowledgeBase()
            update.id = kb_id
            update.files_list = ids
            self.kb_service.update(kb_id, update)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("refresh kb files_list failed kb=%s: %s", kb_id, exc)

    def _refresh_kb_chunks_list(self, kb_id: int) -> None:
        try:
            with DatabaseConnection.get_cursor() as (cursor, _):
                cursor.execute(
                    "SELECT id FROM chunks WHERE knowledge_base_id = ? ORDER BY id ASC",
                    (kb_id,),
                )
                ids = [int(row["id"]) for row in cursor.fetchall() if row["id"] is not None]
            update = KnowledgeBase()
            update.id = kb_id
            update.chunks_list = ids
            self.kb_service.update(kb_id, update)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("refresh kb chunks_list failed kb=%s: %s", kb_id, exc)

    def _increment_kb_size(self, kb_id: int, delta: int) -> None:
        if not delta:
            return
        try:
            self.kb_service.update_knowledge_base_size(kb_id, delta)
        except Exception as exc:  # pragma: no cover
            logger.warning("update knowledge base size failed kb=%s: %s", kb_id, exc)

    # ------------------------------------------------------------------
    # Processing (splitting -> embedding pending)
    # ------------------------------------------------------------------
    def split_and_store(
        self,
        files_to_split: Sequence[Dict[str, Any]],
        knowledge_base_id: int,
        chunk_length: Optional[int] = None,
        overlap_count: Optional[int] = None,
        segmentation_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        kb_id = int(knowledge_base_id)
        if not self.kb_service.exists(kb_id):
            raise NotFoundError(f"知识库 {kb_id} 不存在")

        strategy = self._normalise_strategy(segmentation_strategy)
        effective_length = self._normalise_chunk_length(chunk_length)
        effective_overlap = self._normalise_overlap(overlap_count, effective_length)

        processed: List[Dict[str, Any]] = []
        file_ids: List[int] = []
        for entry in files_to_split or []:
            file_id = None
            if isinstance(entry, dict):
                file_id = entry.get("file_id") or entry.get("id")
            elif isinstance(entry, File):
                file_id = entry.id
            if file_id:
                file_ids.append(int(file_id))

        max_workers = int(getattr(Config, "SPLIT_MAX_WORKERS", 10) or 10)
        if max_workers < 1:
            max_workers = 1

        # SQLite 并发写入易出现 "database is locked"，此处强制单线程切分
        try:
            if str(getattr(Config, "SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite"):
                max_workers = 1
        except Exception:
            max_workers = 1

        for file_id in file_ids:
            try:
                current = self.get_by_id(file_id)
                current_status = (getattr(current, "status", "") or "").lower()
                if current_status != File.STATUS_RE_SPLITTING:
                    self._mark_status(file_id, File.STATUS_SPLITTING)
            except Exception as exc:
                logger.error("mark splitting failed id=%s: %s", file_id, exc)

        if len(file_ids) <= 1 or max_workers == 1:
            for file_id in file_ids:
                try:
                    processed.append(
                        self._process_single_file(
                            file_id=file_id,
                            segmentation_strategy=strategy,
                            chunk_length=effective_length,
                            chunk_overlap=effective_overlap,
                        )
                    )
                except Exception as exc:
                    logger.error("split file failed id=%s: %s", file_id, exc)
        else:
            worker_count = min(max_workers, len(file_ids))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_map = {
                    executor.submit(
                        self._process_single_file,
                        file_id=file_id,
                        segmentation_strategy=strategy,
                        chunk_length=effective_length,
                        chunk_overlap=effective_overlap,
                    ): file_id
                    for file_id in file_ids
                }
                for future in as_completed(future_map):
                    file_id = future_map[future]
                    try:
                        processed.append(future.result())
                    except Exception as exc:
                        logger.error("split file failed id=%s: %s", file_id, exc)

        self._refresh_kb_files_list(kb_id)
        self._refresh_kb_chunks_list(kb_id)

        return {
            "knowledge_base_id": kb_id,
            "processed": processed,
            "count": len(processed),
        }

    def _process_single_file(
        self,
        file_id: int,
        segmentation_strategy: str,
        chunk_length: int,
        chunk_overlap: int,
    ) -> Dict[str, Any]:
        file_obj = self.get_by_id(file_id)
        if not file_obj:
            raise NotFoundError(f"文件 {file_id} 不存在")

        current_status = (getattr(file_obj, "status", "") or "").lower()
        if current_status != File.STATUS_RE_SPLITTING:
            self._mark_status(file_id, File.STATUS_SPLITTING)

        try:
            self._clear_chunks_for_file(file_obj)

            self._append_file_reference(file_obj.knowledge_base_id, file_id)

            loader = FileLoader()
            try:
                text = loader.load_file(file_obj.file_path)
            except FileNotFoundError:
                self._mark_status(file_id, File.STATUS_FILE_NOT_FOUND)
                raise FileProcessingError(f"文件不存在: {file_obj.file_path}")
        except Exception:
            self._mark_status(file_id, File.STATUS_FAILED)
            raise

        embedding_model = getattr(Config, "DEFAULT_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")
        splitter = SplitterFactory(
            segmentation_strategy,
            chunk_length,
            chunk_overlap,
            embedding_model,
        )

        try:
            chunk_infos, _ = splitter.split_text(text or "")

            chunk_service = _get_chunk_service()
            chunk_ids: List[int] = []
            for index, info in enumerate(chunk_infos):
                chunk_record = chunk_service.create_chunk(
                    file_id=file_id,
                    knowledge_base_id=file_obj.knowledge_base_id,
                    chunk_text=info.get("chunk_text", ""),
                    chunk_index=index,
                    start_position=info.get("start_position"),
                    end_position=info.get("end_position"),
                )
                if chunk_record and getattr(chunk_record, "id", None):
                    chunk_ids.append(int(chunk_record.id))

            update_payload = File()
            update_payload.id = file_id
            update_payload.status = File.STATUS_SPLITTED
            update_payload.chunks_list = chunk_ids
            update_payload.chunk_length = chunk_length
            update_payload.overlap_count = chunk_overlap
            update_payload.segmentation_strategy = segmentation_strategy
            update_payload.upload_at = _current_beijing_text()
            self.update(file_id, update_payload)

            self._append_chunk_references(file_obj.knowledge_base_id, chunk_ids)

            return {
                "file_id": file_id,
                "chunks": len(chunk_ids),
                "status": File.STATUS_COMPLETED,
            }
        except Exception:
            self._mark_status(file_id, File.STATUS_FAILED)
            raise

    def _clear_chunks_for_file(self, file_obj: File) -> None:
        file_id = int(file_obj.id)
        try:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
                conn.commit()
        except Exception as exc:
            raise DatabaseError(f"清理文件文本块失败: {str(exc)}") from exc

        update_payload = File()
        update_payload.id = file_id
        update_payload.chunks_list = []
        self.update(file_id, update_payload)

    def _mark_status(self, file_id: int, status: str) -> None:
        if status not in File.VALID_STATUSES:
            raise ValidationError(f"无效状态: {status}")
        update_payload = File()
        update_payload.id = file_id
        update_payload.status = status
        if status == File.STATUS_COMPLETED:
            update_payload.upload_at = _current_beijing_text()
        self.update(file_id, update_payload)

    # ------------------------------------------------------------------
    # Public orchestration helpers
    # ------------------------------------------------------------------
    def start_processing_for_kb(
        self,
        knowledge_base_id: int,
        chunk_length: Optional[int] = None,
        overlap_count: Optional[int] = None,
        segmentation_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        pending = self.get_pending_files(knowledge_base_id=knowledge_base_id)
        if not pending:
            return {"started": False, "message": "无待处理文件"}

        files_payload = [{"file_id": f.id} for f in pending if f and f.id]
        result = self.split_and_store(
            files_to_split=files_payload,
            knowledge_base_id=knowledge_base_id,
            chunk_length=chunk_length,
            overlap_count=overlap_count,
            segmentation_strategy=segmentation_strategy,
        )
        result["started"] = True
        return result

    # ------------------------------------------------------------------
    # CRUD and query helpers (mostly retained from legacy implementation)
    # ------------------------------------------------------------------
    def create_by_id(self, kb_id: int, file_obj: File) -> File:
        if not self.kb_service.exists(kb_id):
            raise NotFoundError(f"知识库 ID {kb_id} 不存在")

        errors = file_obj.validate()
        if errors:
            raise ValidationError("; ".join(errors))

        try:
            file_obj.knowledge_base_id = kb_id
            return self.create(file_obj)
        except Exception as exc:
            raise DatabaseError(f"创建文件记录失败: {str(exc)}") from exc

    def create_file_record(
        self,
        knowledge_base_id: int,
        filename: str,
        file_path: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> File:
        if not self.kb_service.exists(knowledge_base_id):
            raise NotFoundError(f"知识库 ID {knowledge_base_id} 不存在")
        if not filename or not filename.strip():
            raise ValidationError("文件名不能为空")
        if not file_path or not file_path.strip():
            raise ValidationError("文件路径不能为空")
        if not os.path.exists(file_path):
            raise FileProcessingError(f"文件不存在: {file_path}")

        if file_size is None:
            file_size = os.path.getsize(file_path)
        if file_type is None:
            file_type = get_file_type(filename)

        file_obj = File()
        file_obj.knowledge_base_id = knowledge_base_id
        file_obj.filename = filename.strip()
        file_obj.file_path = file_path.strip()
        file_obj.file_type = file_type
        file_obj.file_size = file_size
        file_obj.status = File.STATUS_PENDING
        file_obj.chunks_list = []

        errors = file_obj.validate()
        if errors:
            raise ValidationError("; ".join(errors))

        try:
            created = self.create_by_id(knowledge_base_id, file_obj)
            self._append_file_reference(knowledge_base_id, created.id)
            self._increment_kb_size(knowledge_base_id, file_size)
            return created
        except Exception as exc:
            raise DatabaseError(f"创建文件记录失败: {str(exc)}") from exc

    def delete_file_record(
        self,
        kb_id: int,
        file_id: int,
        delete_physical_file: bool = False,
    ) -> bool:
        file_obj = self.get_by_id(file_id)
        if not file_obj:
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        try:
            if delete_physical_file and file_obj.file_path and os.path.exists(file_obj.file_path):
                try:
                    os.remove(file_obj.file_path)
                except OSError as exc:
                    logger.warning("删除物理文件失败 %s: %s", file_obj.file_path, exc)

            return self.delete(file_id)
        except Exception as exc:
            raise DatabaseError(f"删除文件记录失败: {str(exc)}") from exc

    def delete_file_and_related(self, file_id: int, delete_physical_file: bool = True) -> bool:
        file_obj = self.get_by_id(file_id)
        if not file_obj:
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        kb_id = int(file_obj.knowledge_base_id)
        file_size = int(file_obj.file_size or 0)
        file_path = file_obj.file_path

        try:
            with DatabaseConnection.get_cursor() as (cursor, conn):
                cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
                cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
                conn.commit()
        except Exception as exc:
            raise DatabaseError(f"删除文件与文本块失败: {str(exc)}") from exc

        try:
            if file_size:
                self.kb_service.update_knowledge_base_size(kb_id, -file_size)
        except Exception as exc:
            logger.warning("更新知识库大小失败 kb=%s: %s", kb_id, exc)

        self._refresh_kb_files_list(kb_id)
        self._refresh_kb_chunks_list(kb_id)

        # 删除嵌入向量文件目录（kb_id/file_id）
        try:
            kb_dir = os.path.join(Config.FAISS_INDEX_FOLDER, str(kb_id))
            file_vec_dir = os.path.join(kb_dir, str(file_id))
            if os.path.exists(file_vec_dir):
                shutil.rmtree(file_vec_dir)
        except Exception as exc:
            logger.warning("删除向量文件目录失败 kb=%s file=%s: %s", kb_id, file_id, exc)

        if delete_physical_file and file_path:
            try:
                delete_file_safely(file_path)
            except Exception as exc:
                logger.warning("删除物理文件失败 %s: %s", file_path, exc)

        return True

    def get_files_by_knowledge_base(
        self,
        knowledge_base_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[File], int]:
        if not self.kb_service.exists(knowledge_base_id):
            raise NotFoundError(f"知识库 ID {knowledge_base_id} 不存在")

        where_clause = "knowledge_base_id = ?"
        params: List[Any] = [knowledge_base_id]

        if status:
            if status not in File.VALID_STATUSES:
                raise ValidationError(f"无效的文件状态: {status}")
            where_clause += " AND status = ?"
            params.append(status)

        return self.get_all(
            page=page,
            page_size=page_size,
            order_by="id DESC",
            where_clause=where_clause,
            where_params=tuple(params),
        )

    def search_files(
        self,
        keyword: Optional[str] = None,
        knowledge_base_id: Optional[int] = None,
        status: Optional[str] = None,
        file_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[File], int]:
        conditions: List[str] = []
        params: List[Any] = []

        if keyword and keyword.strip():
            conditions.append("filename LIKE ?")
            params.append(f"%{keyword.strip()}%")

        if knowledge_base_id is not None:
            conditions.append("knowledge_base_id = ?")
            params.append(knowledge_base_id)

        if status:
            if status not in File.VALID_STATUSES:
                raise ValidationError(f"无效的文件状态: {status}")
            conditions.append("status = ?")
            params.append(status)

        if file_type:
            conditions.append("file_type = ?")
            params.append(file_type)

        where_clause = " AND ".join(conditions) if conditions else None
        where_params = tuple(params) if params else None

        return self.get_all(
            page=page,
            page_size=page_size,
            order_by="id DESC",
            where_clause=where_clause,
            where_params=where_params,
        )

    def find_by_path(self, file_path: str) -> Optional[File]:
        if not file_path:
            return None
        return self.find_one_by_field("file_path", file_path)

    def find_one_by_field(self, field: str, value: Any) -> Optional[File]:
        with DatabaseConnection.get_cursor() as (cursor, _):
            cursor.execute(
                f"SELECT * FROM files WHERE {field} = ? LIMIT 1",
                (value,),
            )
            row = cursor.fetchone()
            if row:
                return File.from_row(row)
            return None

    def update_file_status(self, file_id: int, status: str) -> Optional[File]:
        if status not in File.VALID_STATUSES:
            raise ValidationError(f"无效的文件状态: {status}")

        file_obj = self.get_by_id(file_id)
        if not file_obj:
            raise NotFoundError(f"文件 ID {file_id} 不存在")

        if status == File.STATUS_PROCESSING:
            file_obj.mark_as_processing()
        elif status == File.STATUS_COMPLETED:
            file_obj.mark_as_completed()
        elif status == File.STATUS_FAILED:
            file_obj.mark_as_failed()
        elif status == File.STATUS_FILE_NOT_FOUND:
            file_obj.mark_as_file_not_found()
        else:
            file_obj.status = status

        if status == File.STATUS_COMPLETED:
            file_obj.upload_at = _current_beijing_text()

        return self.update(file_id, file_obj)

    def batch_update_status(self, file_ids: Iterable[int], status: str) -> int:
        if status not in File.VALID_STATUSES:
            raise ValidationError(f"无效的文件状态: {status}")

        count = 0
        for file_id in file_ids or []:
            try:
                updated = self.update_file_status(int(file_id), status)
                if updated:
                    count += 1
            except Exception as exc:
                logger.warning("批量更新文件状态失败 id=%s: %s", file_id, exc)
        return count

    def exists_name_type_in_kb(
        self,
        filename: str,
        file_type: str,
        knowledge_base_id: int,
    ) -> bool:
        if not filename or not file_type or not knowledge_base_id:
            return False
        with DatabaseConnection.get_cursor() as (cursor, _):
            cursor.execute(
                """
                SELECT 1 FROM files
                WHERE knowledge_base_id = ?
                  AND LOWER(filename) = LOWER(?)
                  AND file_type = ?
                LIMIT 1
                """,
                (knowledge_base_id, filename.strip(), file_type),
            )
            return cursor.fetchone() is not None

    def cleanup_orphaned_files(self) -> int:
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute(
                """
                SELECT f.id, f.filename
                FROM files f
                LEFT JOIN knowledge_bases kb ON f.knowledge_base_id = kb.id
                WHERE kb.id IS NULL
                """
            )
            orphaned = cursor.fetchall()
            for row in orphaned:
                cursor.execute("DELETE FROM files WHERE id = ?", (row["id"],))
            conn.commit()
            return len(orphaned)

    def cleanup_missing_files(self) -> int:
        with DatabaseConnection.get_cursor() as (cursor, conn):
            cursor.execute("SELECT id, filename, file_path FROM files")
            rows = cursor.fetchall()
            updated = 0
            for row in rows:
                if not os.path.exists(row["file_path"]):
                    cursor.execute(
                        "UPDATE files SET status = ? WHERE id = ?",
                        (File.STATUS_FILE_NOT_FOUND, row["id"]),
                    )
                    updated += 1
            conn.commit()
            return updated

    def get_processing_files(self) -> List[File]:
        return self.find_by_field("status", File.STATUS_PROCESSING)

    def find_by_field(self, field: str, value: Any) -> List[File]:
        with DatabaseConnection.get_cursor() as (cursor, _):
            cursor.execute(
                f"SELECT * FROM files WHERE {field} = ?",
                (value,),
            )
            rows = cursor.fetchall()
            return [File.from_row(row) for row in rows]

    def get_pending_files(
        self,
        knowledge_base_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[File]:
        with DatabaseConnection.get_cursor() as (cursor, _):
            query = "SELECT * FROM files WHERE status = ?"
            params: List[Any] = [File.STATUS_PENDING]
            if knowledge_base_id is not None:
                query += " AND knowledge_base_id = ?"
                params.append(knowledge_base_id)
            query += " ORDER BY id ASC"
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [File.from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # Backwards compatibility wrappers
    # ------------------------------------------------------------------
    def process_embedding(
        self,
        files_to_embedding: Sequence[Dict[str, Any]],
        knowledge_base_id: int,
        chunk_length: Optional[int] = None,
        overlap_count: Optional[int] = None,
        segmentation_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Legacy alias retained for compatibility."""
        return self.split_and_store(
            files_to_split=files_to_embedding,
            knowledge_base_id=knowledge_base_id,
            chunk_length=chunk_length,
            overlap_count=overlap_count,
            segmentation_strategy=segmentation_strategy,
        )

    def process_embedding_async(
        self,
        files_to_embedding: Sequence[Dict[str, Any]],
        knowledge_base_id: int,
        chunk_length: Optional[int] = None,
        overlap_count: Optional[int] = None,
        segmentation_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Legacy alias retained for compatibility (now synchronous)."""
        return self.process_embedding(
            files_to_embedding=files_to_embedding,
            knowledge_base_id=knowledge_base_id,
            chunk_length=chunk_length,
            overlap_count=overlap_count,
            segmentation_strategy=segmentation_strategy,
        )

