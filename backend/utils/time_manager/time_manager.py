"""
时间管理工具模块（UTC统一）

目标：
- 全项目统一以 UTC 表示时间
- 默认展示格式：YYYY年MM月DD日 HH时mm分ss秒 UTC（可由 Config.DATE_TIME_FORMAT 配置）
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    # 避免循环依赖：仅在运行时导入配置
    from backend.config import Config  # when running as module
except Exception:  # pragma: no cover
    try:
        from config import Config  # when running from backend/
    except Exception:  # pragma: no cover
        class _Fallback:
            DATE_TIME_FORMAT = "%Y年%m月%d日 %H时%M分%S秒"

        Config = _Fallback()  # type: ignore


def utc_now() -> datetime:
    """获取当前UTC时间（aware datetime）"""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """将 datetime 统一转为 UTC aware；None 直接返回。"""
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        raise ValueError("输入必须是 datetime")
    if dt.tzinfo is None:
        # 视为 UTC（避免本地时区偏差）
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


_CTT = timezone(timedelta(hours=8))  # China Standard Time (UTC+8)


def format_utc(dt: Optional[datetime] = None, fmt: Optional[str] = None) -> str:
    """将时间格式化为中文时间字符串（北京时间），不附加“北京时间”字样。

    Args:
        dt: datetime；缺省则使用当前UTC时间
        fmt: 格式字符串；缺省使用 Config.DATE_TIME_FORMAT
    """
    the_dt = ensure_utc(dt) or utc_now()
    # 转为北京时区再格式化
    the_dt = the_dt.astimezone(_CTT)
    pattern = fmt or getattr(Config, "DATE_TIME_FORMAT", "%Y年%m月%d日 %H时%M分%S秒")
    return the_dt.strftime(pattern)


def format_utc_now(fmt: Optional[str] = None) -> str:
    """格式化当前UTC时间为指定格式（默认全局格式）。"""
    return format_utc(utc_now(), fmt)


def parse_to_utc(s: Optional[str]) -> Optional[datetime]:
    """尽量解析字符串为 UTC aware datetime。

    支持：
    - ISO8601（含 Z 或 +00:00）
    - 常见 "YYYY-MM-DD HH:MM:SS"（视为UTC）
    - 已经是 None 则返回 None
    """
    if not s:
        return None
    try:
        # ISO with Z
        if "Z" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        # ISO general
        dt = datetime.fromisoformat(s)
        return ensure_utc(dt)
    except Exception:
        pass
    # 兜底常见格式
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, pattern).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


# 兼容原先接口：格式化与相对时间（保留但走UTC）
def format_datetime(dt: datetime, format_str: Optional[str] = None, timezone_aware: bool = True) -> str:
    the_dt = ensure_utc(dt) if timezone_aware else dt
    pattern = format_str or getattr(Config, "DATE_TIME_FORMAT", "%Y年%m月%d日 %H时%M分%S秒")
    # format_datetime 保持输入时区，不强制转 CTT，供兼容旧调用
    return (the_dt or utc_now()).strftime(pattern)


def get_relative_time(dt: datetime, base_time: Optional[datetime] = None, language: str = "zh") -> str:
    if dt is None:
        return ""
    base = ensure_utc(base_time) or utc_now()
    dt_utc = ensure_utc(dt)
    diff = base - dt_utc
    total_seconds = diff.total_seconds()

    if language == "zh":
        if total_seconds < 0:
            total_seconds = -total_seconds
            if total_seconds < 60:
                return "即将"
            elif total_seconds < 3600:
                minutes = int(total_seconds // 60)
                return f"{minutes}分钟后"
            elif total_seconds < 86400:
                hours = int(total_seconds // 3600)
                return f"{hours}小时后"
            elif total_seconds < 2592000:
                days = int(total_seconds // 86400)
                return f"{days}天后"
            else:
                return format_datetime(dt_utc, "%Y年%m月%d日")
        else:
            if total_seconds < 60:
                return "刚刚"
            elif total_seconds < 3600:
                minutes = int(total_seconds // 60)
                return f"{minutes}分钟前"
            elif total_seconds < 86400:
                hours = int(total_seconds // 3600)
                return f"{hours}小时前"
            elif total_seconds < 2592000:
                days = int(total_seconds // 86400)
                return f"{days}天前"
            else:
                return format_datetime(dt_utc, "%Y年%m月%d日")
    else:
        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            minutes = int(total_seconds // 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:
            hours = int(total_seconds // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif total_seconds < 2592000:
            days = int(total_seconds // 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return format_datetime(dt_utc, "%Y-%m-%d")
