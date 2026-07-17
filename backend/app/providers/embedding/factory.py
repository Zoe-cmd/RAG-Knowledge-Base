"""
Embedding Provider 工厂。

根据配置（EMBEDDING_PROVIDER 环境变量）返回对应的 Provider 实例。
遵循开闭原则：新增 Provider 只需新增类，在工厂注册。
"""

from functools import lru_cache

from app.config.settings import get_settings
from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.bge_provider import BGEEmbeddingProvider
from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """获取 Embedding Provider 实例（单例）。

    根据配置中的 EMBEDDING_PROVIDER 返回:
    - "openai": OpenAIEmbeddingProvider（默认）
    - "bge": BGEEmbeddingProvider（本地模型）

    Returns:
        EmbeddingProvider 实例

    Raises:
        ValueError: 不支持的 Provider 名称
    """
    settings = get_settings()
    provider_name = settings.EMBEDDING_PROVIDER.lower()

    if provider_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OPENAI_BASE_URL,
        )
    elif provider_name == "bge":
        return BGEEmbeddingProvider(
            cache_dir=settings.MODEL_CACHE_DIR,
        )
    else:
        raise ValueError(
            f"不支持的 Embedding Provider: {provider_name}，"
            f"可选值: openai, bge"
        )


def get_collection_name(provider: EmbeddingProvider) -> str:
    """生成 Chroma collection 名称。

    命名规则: kb_{provider_name}_{dimension}
    示例:
    - kb_openai_1536
    - kb_bge_1024

    Args:
        provider: Embedding Provider 实例

    Returns:
        Chroma collection 名称
    """
    return f"kb_{provider.name}_{provider.dimension}"
