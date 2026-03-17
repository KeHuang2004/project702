from typing import Generator

from config import Config
from ..Generate.generator import Generator as _Generator


def resolve_chat_endpoint(model: str | None = None) -> str:
    """返回聊天 completions 端点：优先使用 `Config.CHAT_COMPLETIONS_ENDPOINT`，
    否则根据 `Config.CHAT_SERVE['port']` 和 `Config.VLLM_HOST` 拼接默认端点。
    """
    endpoint = getattr(Config, "CHAT_COMPLETIONS_ENDPOINT", None)
    if endpoint:
        return endpoint
    host = getattr(Config, "VLLM_HOST", "127.0.0.1")
    port = getattr(Config, "CHAT_SERVE", {}).get("port", 11520)
    return f"http://{host}:{port}/v1/chat/completions"


def generating(
    prompt: str,
    *,
    endpoint: str | None = None,
    model: str | None = None,
) -> Generator[str, None, None]:
    """
    统一对外的生成接口：返回一个逐块产出字符串的生成器。

    - prompt: 用户输入
    - endpoint: vLLM OpenAI 兼容接口地址（含 /v1/chat/completions）
    - model: 模型名称

    使用方式：
        for chunk in generating("你好"):
            ...
    """
    # 若未显式传入 endpoint，则根据模型名解析对应端口的端点
    resolved_endpoint = endpoint or resolve_chat_endpoint(model)
    g = _Generator(endpoint=resolved_endpoint, model=model)
    return g.generate_stream(prompt)
