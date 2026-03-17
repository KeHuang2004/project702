"""
文件处理工具模块

提供文件上传、类型检测、哈希计算等文件相关的工具函数
"""

import hashlib
import mimetypes
import os
import shutil
from datetime import datetime
from utils.time_manager.time_manager import utc_now
from typing import Any, Dict, List

from werkzeug.datastructures import FileStorage

from config import Config
from utils.request_manager.exceptions import FileProcessingError


def save_uploaded_file(
    file: FileStorage, knowledge_base_id: int, filename: str = None
) -> str:
    """保存上传的文件"""
    if not file or not file.filename:
        raise FileProcessingError("文件不能为空")

    if not filename:
        raise FileProcessingError("文件名无效")

    file_path, _ = resolve_upload_path(knowledge_base_id, filename)
    return save_uploaded_file_to_path(file, file_path)


def resolve_upload_path(knowledge_base_id: int, filename: str) -> tuple[str, str]:
    """生成唯一的文件保存路径，返回 (file_path, final_filename)"""
    if not filename:
        raise FileProcessingError("文件名无效")

    kb_dir = os.path.join(Config.UPLOAD_FOLDER, str(knowledge_base_id))
    os.makedirs(kb_dir, exist_ok=True)

    return os.path.join(kb_dir, filename), filename


def save_uploaded_file_to_path(file: FileStorage, file_path: str) -> str:
    """保存上传文件到指定路径"""
    if not file or not getattr(file, "filename", None):
        raise FileProcessingError("文件不能为空")
    if not file_path:
        raise FileProcessingError("文件路径无效")

    try:
        file.save(file_path)

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise FileProcessingError("文件保存失败")

        return file_path
    except Exception as e:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise FileProcessingError(f"保存文件失败: {str(e)}", filename=getattr(file, "filename", None))


def get_file_type(filename: str) -> str:
    """根据文件名获取文件类型"""
    if not filename:
        return "unknown"

    ext = get_file_extension(filename).lower()

    # 文档类型映射
    type_mapping = {
        "txt": "text",
        "md": "markdown",
        "pdf": "pdf",
        "doc": "word",
        "docx": "word",
        "xls": "excel",
        "xlsx": "excel",
        "ppt": "powerpoint",
        "pptx": "powerpoint",
        "csv": "csv",
        "json": "json",
        "xml": "xml",
        "html": "html",
        "htm": "html",
        "rtf": "rtf",
        "odt": "opendocument",
        "ods": "opendocument",
        "odp": "opendocument",
    }

    return type_mapping.get(ext, "unknown")


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1]


def is_allowed_file_type(filename: str, allowed_extensions: List[str] = None) -> bool:
    """检查是否为允许的文件类型"""
    if allowed_extensions is None:
        allowed_extensions = Config.ALLOWED_EXTENSIONS

    ext = get_file_extension(filename).lower()
    return ext in [e.lower() for e in allowed_extensions]


def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str:
    """计算文件哈希值"""
    if not os.path.exists(file_path):
        raise FileProcessingError(f"文件不存在: {file_path}")

    # 支持的哈希算法
    hash_algorithms = {
        "md5": hashlib.md5(),
        "sha1": hashlib.sha1(),
        "sha256": hashlib.sha256(),
        "sha512": hashlib.sha512(),
    }

    if algorithm not in hash_algorithms:
        raise FileProcessingError(f"不支持的哈希算法: {algorithm}")

    hasher = hash_algorithms[algorithm]

    try:
        with open(file_path, "rb") as f:
            # 分块读取大文件
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    except Exception as e:
        raise FileProcessingError(f"计算文件哈希失败: {str(e)}", file_path=file_path)


def get_file_info(file_path: str) -> Dict[str, Any]:
    """获取文件信息"""
    if not os.path.exists(file_path):
        raise FileProcessingError(f"文件不存在: {file_path}")

    try:
        stat = os.stat(file_path)
        filename = os.path.basename(file_path)

        return {
            "filename": filename,
            "file_path": file_path,
            "file_size": stat.st_size,
            "file_type": get_file_type(filename),
            "extension": get_file_extension(filename),
            "mime_type": get_mime_type(file_path),
            "created_time": datetime.fromtimestamp(stat.st_ctime),
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "accessed_time": datetime.fromtimestamp(stat.st_atime),
            "is_readable": os.access(file_path, os.R_OK),
            "is_writable": os.access(file_path, os.W_OK),
        }

    except Exception as e:
        raise FileProcessingError(f"获取文件信息失败: {str(e)}", file_path=file_path)


def get_mime_type(file_path: str) -> str:
    """获取文件MIME类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def validate_file_integrity(
    file_path: str, expected_hash: str = None, expected_size: int = None
) -> Dict[str, Any]:
    """验证文件完整性"""
    result = {
        "is_valid": True,
        "errors": [],
        "file_exists": False,
        "size_match": None,
        "hash_match": None,
        "current_size": None,
        "current_hash": None,
    }

    # 检查文件是否存在
    if not os.path.exists(file_path):
        result["is_valid"] = False
        result["errors"].append("文件不存在")
        return result

    result["file_exists"] = True

    try:
        # 检查文件大小
        current_size = os.path.getsize(file_path)
        result["current_size"] = current_size

        if expected_size is not None:
            result["size_match"] = current_size == expected_size
            if not result["size_match"]:
                result["is_valid"] = False
                result["errors"].append(
                    f"文件大小不匹配，期望: {expected_size}, 实际: {current_size}"
                )

        # 检查文件哈希
        if expected_hash is not None:
            current_hash = calculate_file_hash(file_path)
            result["current_hash"] = current_hash
            result["hash_match"] = current_hash == expected_hash

            if not result["hash_match"]:
                result["is_valid"] = False
                result["errors"].append(
                    f"文件哈希不匹配，期望: {expected_hash}, 实际: {current_hash}"
                )

    except Exception as e:
        result["is_valid"] = False
        result["errors"].append(f"验证过程出错: {str(e)}")

    return result


def delete_file_safely(file_path: str, backup: bool = False) -> bool:
    """安全删除文件"""
    if not os.path.exists(file_path):
        return True  # 文件已经不存在

    try:
        # 创建备份
        if backup:
            from utils.time_manager.time_manager import utc_now
            backup_path = f"{file_path}.backup.{utc_now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)

        # 删除文件
        os.remove(file_path)
        return True

    except Exception as e:
        raise FileProcessingError(f"删除文件失败: {str(e)}", file_path=file_path)


def move_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    """移动文件"""
    if not os.path.exists(source_path):
        raise FileProcessingError(f"源文件不存在: {source_path}")

    # 确保目标目录存在
    dest_dir = os.path.dirname(destination_path)
    os.makedirs(dest_dir, exist_ok=True)

    # 检查目标文件是否已存在
    if os.path.exists(destination_path) and not overwrite:
        # 生成新的文件名
        base_name, ext = os.path.splitext(destination_path)
        counter = 1
        while os.path.exists(destination_path):
            destination_path = f"{base_name}_{counter}{ext}"
            counter += 1

    try:
        shutil.move(source_path, destination_path)
        return destination_path

    except Exception as e:
        raise FileProcessingError(f"移动文件失败: {str(e)}", file_path=source_path)


def copy_file(source_path: str, destination_path: str, overwrite: bool = False) -> str:
    """复制文件"""
    if not os.path.exists(source_path):
        raise FileProcessingError(f"源文件不存在: {source_path}")

    # 确保目标目录存在
    dest_dir = os.path.dirname(destination_path)
    os.makedirs(dest_dir, exist_ok=True)

    # 检查目标文件是否已存在
    if os.path.exists(destination_path) and not overwrite:
        # 生成新的文件名
        base_name, ext = os.path.splitext(destination_path)
        counter = 1
        while os.path.exists(destination_path):
            destination_path = f"{base_name}_{counter}{ext}"
            counter += 1

    try:
        shutil.copy2(source_path, destination_path)
        return destination_path

    except Exception as e:
        raise FileProcessingError(f"复制文件失败: {str(e)}", file_path=source_path)


def get_directory_size(directory_path: str) -> int:
    """获取目录大小"""
    if not os.path.exists(directory_path):
        return 0

    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size

    except Exception as e:
        raise FileProcessingError(
            f"计算目录大小失败: {str(e)}", file_path=directory_path
        )


def cleanup_empty_directories(base_path: str) -> int:
    """清理空目录"""
    if not os.path.exists(base_path):
        return 0

    removed_count = 0

    try:
        # 从最深层开始清理
        for root, dirs, files in os.walk(base_path, topdown=False):
            for directory in dirs:
                dir_path = os.path.join(root, directory)
                try:
                    # 尝试删除空目录
                    os.rmdir(dir_path)
                    removed_count += 1
                except OSError:
                    # 目录不为空或其他错误，跳过
                    pass

        return removed_count

    except Exception as e:
        raise FileProcessingError(f"清理空目录失败: {str(e)}", file_path=base_path)


def create_file_backup(file_path: str, backup_dir: str = None) -> str:
    """创建文件备份"""
    if not os.path.exists(file_path):
        raise FileProcessingError(f"源文件不存在: {file_path}")

    filename = os.path.basename(file_path)
    from utils.time_manager.time_manager import utc_now
    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")

    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(file_path), "backups")

    os.makedirs(backup_dir, exist_ok=True)

    backup_filename = f"{timestamp}_{filename}"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        shutil.copy2(file_path, backup_path)
        return backup_path

    except Exception as e:
        raise FileProcessingError(f"创建文件备份失败: {str(e)}", file_path=file_path)


def get_available_filename(directory: str, filename: str) -> str:
    """获取可用的文件名（避免重复）"""
    base_name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename

    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base_name}_{counter}{ext}"
        counter += 1

    return new_filename


def is_text_file(file_path: str, sample_size: int = 1024) -> bool:
    """检查是否为文本文件"""
    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)

        # 检查是否包含空字节（二进制文件的特征）
        if b"\x00" in sample:
            return False

        # 尝试解码为UTF-8
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            # 尝试其他编码
            # 尝试其他编码
            encodings = ["gbk", "gb2312", "latin-1", "cp1252"]
            for encoding in encodings:
                try:
                    sample.decode(encoding)
                    return True
                except UnicodeDecodeError:
                    continue

            return False

    except Exception:
        return False


def detect_file_encoding(file_path: str, sample_size: int = 4096) -> str:
    """检测文件编码"""
    if not os.path.exists(file_path):
        raise FileProcessingError(f"文件不存在: {file_path}")

    try:
        encodings = ["utf-8", "gbk", "gb2312", "latin-1", "cp1252"]

        with open(file_path, "rb") as f:
            sample = f.read(sample_size)

        for encoding in encodings:
            try:
                sample.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        return "utf-8"  # 默认返回UTF-8

    except Exception as e:
        raise FileProcessingError(f"检测文件编码失败: {str(e)}", file_path=file_path)


def read_file_content(
    file_path: str, encoding: str = None, max_size: int = None
) -> str:
    """读取文件内容"""
    if not os.path.exists(file_path):
        raise FileProcessingError(f"文件不存在: {file_path}")

    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if max_size and file_size > max_size:
        raise FileProcessingError(f"文件太大，超过限制: {format_file_size(max_size)}")

    # 自动检测编码
    if encoding is None:
        encoding = detect_file_encoding(file_path)

    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            return f.read()

    except Exception as e:
        raise FileProcessingError(f"读取文件内容失败: {str(e)}", file_path=file_path)


def write_file_content(
    file_path: str, content: str, encoding: str = "utf-8", backup: bool = True
) -> bool:
    """写入文件内容"""
    try:
        # 创建备份
        if backup and os.path.exists(file_path):
            create_file_backup(file_path)

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)

        return True

    except Exception as e:
        raise FileProcessingError(f"写入文件内容失败: {str(e)}", file_path=file_path)


class FileManager:
    """文件管理器类"""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or Config.UPLOAD_FOLDER
        self.ensure_base_path()

    def ensure_base_path(self):
        """确保基础路径存在"""
        os.makedirs(self.base_path, exist_ok=True)

    def get_knowledge_base_path(self, knowledge_base_id: int, kb_name: str = None) -> str:
        """获取知识库路径，支持统一命名 {知识库名}_{id}"""
        if kb_name:
            safe_name = "".join(
                c for c in kb_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip().replace(" ", "_")
            dir_name = f"{safe_name}_{knowledge_base_id}"
        else:
            dir_name = str(knowledge_base_id)
        return os.path.join(self.base_path, dir_name)

    def create_knowledge_base_directory(self, knowledge_base_id: int, kb_name: str = None) -> str:
        """创建知识库目录，支持统一命名"""
        kb_path = self.get_knowledge_base_path(knowledge_base_id, kb_name)
        os.makedirs(kb_path, exist_ok=True)
        return kb_path

    def delete_knowledge_base_directory(
        self, knowledge_base_id: int, backup: bool = True
    ) -> bool:
        """删除知识库目录"""
        kb_path = self.get_knowledge_base_path(knowledge_base_id)

        if not os.path.exists(kb_path):
            return True

        try:
            if backup:
                backup_path = f"{kb_path}_backup_{utc_now().strftime('%Y%m%d_%H%M%S')}"
                shutil.move(kb_path, backup_path)
            else:
                shutil.rmtree(kb_path)

            return True

        except Exception as e:
            raise FileProcessingError(
                f"删除知识库目录失败: {str(e)}", file_path=kb_path
            )

    def list_files(
        self, knowledge_base_id: int, pattern: str = None
    ) -> List[Dict[str, Any]]:
        """列出知识库中的文件"""
        kb_path = self.get_knowledge_base_path(knowledge_base_id)

        if not os.path.exists(kb_path):
            return []

        files = []

        try:
            for filename in os.listdir(kb_path):
                file_path = os.path.join(kb_path, filename)

                if os.path.isfile(file_path):
                    # 应用模式过滤
                    if pattern and pattern not in filename:
                        continue

                    file_info = get_file_info(file_path)
                    files.append(file_info)

            return sorted(files, key=lambda x: x["modified_time"], reverse=True)

        except Exception as e:
            raise FileProcessingError(f"列出文件失败: {str(e)}", file_path=kb_path)

    def get_storage_stats(self, knowledge_base_id: int = None) -> Dict[str, Any]:
        """获取存储统计信息"""
        if knowledge_base_id:
            # 特定知识库的统计
            kb_path = self.get_knowledge_base_path(knowledge_base_id)
            if not os.path.exists(kb_path):
                return {
                    "total_size": 0,
                    "file_count": 0,
                    "directory_count": 0,
                    "last_modified": None,
                }

            stats = self._get_directory_stats(kb_path)
            stats["knowledge_base_id"] = knowledge_base_id
            return stats
        else:
            # 所有知识库的统计
            total_stats = {
                "total_size": 0,
                "file_count": 0,
                "directory_count": 0,
                "knowledge_bases": [],
                "last_modified": None,
            }

            if not os.path.exists(self.base_path):
                return total_stats

            for item in os.listdir(self.base_path):
                item_path = os.path.join(self.base_path, item)
                if os.path.isdir(item_path) and item.isdigit():
                    kb_id = int(item)
                    kb_stats = self._get_directory_stats(item_path)
                    kb_stats["knowledge_base_id"] = kb_id

                    total_stats["total_size"] += kb_stats["total_size"]
                    total_stats["file_count"] += kb_stats["file_count"]
                    total_stats["directory_count"] += 1
                    total_stats["knowledge_bases"].append(kb_stats)

                    if total_stats["last_modified"] is None or (
                        kb_stats["last_modified"]
                        and kb_stats["last_modified"] > total_stats["last_modified"]
                    ):
                        total_stats["last_modified"] = kb_stats["last_modified"]

            return total_stats

    def _get_directory_stats(self, directory_path: str) -> Dict[str, Any]:
        """获取目录统计信息"""
        stats = {
            "total_size": 0,
            "file_count": 0,
            "directory_count": 0,
            "last_modified": None,
        }

        try:
            for root, dirs, files in os.walk(directory_path):
                stats["directory_count"] += len(dirs)

                for filename in files:
                    file_path = os.path.join(root, filename)
                    if os.path.exists(file_path):
                        file_stat = os.stat(file_path)
                        stats["total_size"] += file_stat.st_size
                        stats["file_count"] += 1

                        modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                        if (
                            stats["last_modified"] is None
                            or modified_time > stats["last_modified"]
                        ):
                            stats["last_modified"] = modified_time

            return stats

        except Exception as e:
            raise FileProcessingError(
                f"获取目录统计失败: {str(e)}", file_path=directory_path
            )

    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """清理临时文件"""
        temp_dir = os.path.join(self.base_path, "temp")
        if not os.path.exists(temp_dir):
            return 0

        removed_count = 0
        cutoff_time = utc_now().timestamp() - (max_age_hours * 3600)

        try:
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    if file_stat.st_mtime < cutoff_time:
                        os.remove(file_path)
                        removed_count += 1

            return removed_count

        except Exception as e:
            raise FileProcessingError(f"清理临时文件失败: {str(e)}", file_path=temp_dir)


# 便捷函数
file_manager = FileManager()


def get_upload_path(knowledge_base_id: int) -> str:
    """获取上传路径"""
    return file_manager.get_knowledge_base_path(knowledge_base_id)


def ensure_upload_path(knowledge_base_id: int) -> str:
    """确保上传路径存在"""
    return file_manager.create_knowledge_base_directory(knowledge_base_id)
