"""
LLM Provider 工厂。

根据配置返回对应的 LLM Provider 实例。
当前仅支持 OpenAI（通过 base_url 可兼容其他端点），
未来可扩展其他 Provider（如 Anthropic）。
"""

from functools import lru_cache

from app.config.settings import get_settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.openai_provider import OpenAILLMProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """获取 LLM Provider 实例（单例）。

    当前仅支持 OpenAI（通过 base_url 可兼容其他端点）。

    Returns:
        LLMProvider 实例

    Raises:
        ValueError: 不支持的 Provider 名称
    """
    settings = get_settings()

    # 当前仅支持 OpenAI 兼容端点
    # 未来可在此扩展其他 Provider
    return OpenAILLMProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        timeout=settings.LLM_TIMEOUT,
        stream_timeout=settings.LLM_STREAM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )
