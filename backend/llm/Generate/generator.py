import json
from typing import Generator as TypingGenerator

import requests
from config import Config


class Generator:
    """极简流式生成器：直连 vLLM OpenAI 接口并按块返回 content。"""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
    ) -> None:
        # 统一使用固定 chat 模型名 'chat__model'；endpoint 从配置的 CHAT_SERVE.port 拼接或由环境变量覆盖
        default_endpoint = getattr(Config, "CHAT_COMPLETIONS_ENDPOINT", None)
        if not default_endpoint:
            host = getattr(Config, "VLLM_HOST", "127.0.0.1")
            port = getattr(Config, "CHAT_SERVE", {}).get("port", 11520)
            default_endpoint = f"http://{host}:{port}/v1/chat/completions"
        self.endpoint = endpoint or default_endpoint
        self.model = model or "chat__model"

    def generate_stream(self, prompt: str) -> TypingGenerator[str, None, None]:
        payload = {
            "model": self.model,
            "stream": True,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }

        response = requests.post(self.endpoint, json=payload, stream=True, timeout=30)
        if response.status_code != 200:
            raise Exception(
                f"vLLM error: HTTP {response.status_code} - {response.text[:200]}"
            )

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


# 兼容原有导入名
StreamGenerator = Generator
