import json
import logging
from typing import Generator

import requests

from config import Config
from ..Generate.generator import Generator as _Generator


logger = logging.getLogger(__name__)


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
    llm_mode = (getattr(Config, "llm_mode", "local") or "local").strip().lower()

    if llm_mode == "remote":
        yield from _generate_remote(prompt, endpoint=endpoint, model=model)
        return

    # 若未显式传入 endpoint，则根据模型名解析对应端口的端点
    resolved_endpoint = endpoint or resolve_chat_endpoint(model)
    g = _Generator(endpoint=resolved_endpoint, model=model)
    yield from g.generate_stream(prompt)


def _generate_remote(
    prompt: str,
    *,
    endpoint: str | None = None,
    model: str | None = None,
) -> Generator[str, None, None]:
    api_url = endpoint or getattr(Config, "llm_api_url", None)
    api_key = getattr(Config, "llm_api_key", None)
    remote_model = model or getattr(Config, "llm_model", None)

    if not api_url:
        raise Exception("远程 LLM API URL 未配置")
    if not api_key:
        raise Exception("远程 LLM API KEY 未配置")
    if not remote_model:
        raise Exception("远程 LLM 模型名未配置")

    payload = {
        "model": remote_model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info("使用远程 LLM 生成: url=%s model=%s", api_url, remote_model)

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60,
        )
    except requests.exceptions.SSLError as ssl_err:
        logger.warning("远程 LLM SSL 错误，尝试 verify=False 重试: %s", ssl_err)
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=60,
            verify=False,
        )

    if response.status_code != 200:
        raise Exception(f"remote llm error: HTTP {response.status_code} - {response.text[:200]}")

    for raw_line in response.iter_lines():
        if not raw_line:
            continue

        line = raw_line.decode("utf-8", errors="ignore").strip()
        if line.startswith("data:"):
            data_str = line[len("data:") :].strip()
        else:
            data_str = line

        if not data_str:
            continue
        if data_str == "[DONE]":
            break

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        choices = chunk.get("choices") or []
        if not choices:
            continue

        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            yield content
