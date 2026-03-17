import json
import logging
from typing import Generator

import requests

from .generating import generating

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """使用外部API的生成器，用于要点提炼和文献综述。"""

    def __init__(self, model: str = "qwen3.5-flash"):
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_key = "sk-f5d4e6d321bc49cfb6e9656c012078ca"
        self.model = model
        self.use_local_fallback = True  # 启用本地模型回退

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        """首选远程API，失败时回退到本地模型"""
        try:
            # 尝试使用远程API
            logger.info('尝试使用远程API (DashScope) 进行要点提炼')
            for chunk in self._generate_remote(prompt):
                yield chunk
        except Exception as remote_err:
            logger.warning('远程API失败，回退到本地模型: %s', remote_err)
            if self.use_local_fallback:
                try:
                    # 使用本地模型
                    logger.info('尝试使用本地vLLM模型进行要点提炼')
                    for chunk in self._generate_local(prompt):
                        yield chunk
                except Exception as local_err:
                    logger.error('本地模型也失败，使用简单文本摘要: %s', local_err)
                    yield self._generate_simple_summary(prompt)
            else:
                yield f"生成失败：{remote_err}"

    def _generate_remote(self, prompt: str) -> Generator[str, None, None]:
        """使用远程API生成"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info('Summary API 请求 URL=%s model=%s', self.api_url, self.model)
        logger.debug('Summary API 请求 payload=%s', payload)
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, stream=True, timeout=60)
        except requests.exceptions.SSLError as ssl_err:
            logger.error('Summary API SSL错误: %s', ssl_err)
            logger.error('尝试使用 verify=False 重试...')
            try:
                response = requests.post(self.api_url, json=payload, headers=headers, stream=True, timeout=60, verify=False)
                logger.warning('使用 verify=False 成功连接，但这不安全')
            except Exception as retry_err:
                logger.error('重试也失败: %s', retry_err)
                raise Exception(f"SSL连接失败: {ssl_err}")
        except Exception as e:
            logger.error('Summary API 请求失败: %s', e)
            raise Exception(f"API请求失败: {e}")

        logger.info('Summary API 响应 status=%s', response.status_code)
        if response.status_code != 200:
            logger.error('Summary API 响应异常：%s', response.text[:400])
            raise Exception(f"API error: HTTP {response.status_code} - {response.text[:200]}")

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

    def _generate_local(self, prompt: str) -> Generator[str, None, None]:
        """使用本地模型生成"""
        logger.info('使用本地模型进行要点提炼')
        try:
            for chunk in generating(prompt):
                yield chunk
        except Exception as e:
            logger.error('本地模型生成失败，回退到简单文本处理: %s', e)
            # 提供简单的文本摘要作为最后回退
            yield self._generate_simple_summary(prompt)

    def _generate_simple_summary(self, prompt: str) -> str:
        """简单的文本摘要回退方案"""
        logger.info('使用简单文本处理生成摘要')
        # 从prompt中提取文献内容
        content_start = prompt.find("文献内容：\n")
        if content_start == -1:
            return "无法提取文献内容进行摘要。"

        content = prompt[content_start + 6:]  # 跳过"文献内容：\n"

        # 简单的摘要逻辑：取前500个字符
        if len(content) > 500:
            summary = content[:500] + "..."
        else:
            summary = content

        return f"文献要点摘要：\n{summary}\n\n注意：这是系统生成的简化摘要，建议配置正确的AI服务以获得更好的摘要质量。"


def summary_generating(prompt: str) -> Generator[str, None, None]:
    """
    统一对外的生成接口：返回一个逐块产出字符串的生成器，用于要点提炼和文献综述。
    """
    g = SummaryGenerator()
    return g.generate_stream(prompt)