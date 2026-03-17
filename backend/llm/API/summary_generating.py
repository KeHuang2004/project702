import logging
from typing import Generator

from config import Config

from .generating import generating

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """用于要点提炼和文献综述的统一生成器。"""

    def __init__(self, model: str | None = None):
        self.model = model or getattr(Config, "llm_model", "qwen3.5-flash")

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        """根据 Config.llm_mode 使用远程或本地模型。"""
        try:
            llm_mode = (getattr(Config, "llm_mode", "local") or "local").strip().lower()
            logger.info('SummaryGenerator 使用模式: %s', llm_mode)

            if llm_mode == "remote":
                for chunk in generating(
                    prompt,
                    endpoint=getattr(Config, "llm_api_url", None),
                    model=self.model,
                ):
                    yield chunk
            else:
                for chunk in generating(prompt):
                    yield chunk
        except Exception as err:
            logger.error('要点提炼生成失败，回退到简单文本摘要: %s', err)
            yield self._generate_simple_summary(prompt)

    def _generate_simple_summary(self, prompt: str) -> str:
        """简单的文本摘要回退方案"""
        logger.info('使用简单文本处理生成摘要')
        # 从prompt中提取文献内容
        content_start = prompt.find("文献内容：\n")
        if content_start == -1:
            content_start = prompt.find("用户输入：\n")
        if content_start == -1:
            return "无法提取输入内容进行摘要。"

        content = prompt[content_start + 6 :]

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