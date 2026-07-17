"""
Embedding 服务层。

封装 Embedding Provider 调用，提供文档批量向量化和查询向量化的统一接口。
处理 Provider 获取、批量分片、异常包装等通用逻辑。
"""

import logging
from typing import List

from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import get_embedding_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding 服务。

    封装 Embedding Provider，提供:
    - 文档批量向量化（自动分批）
    - 查询向量化
    - Provider 信息查询（名称、维度）

    Service 层通过此服务访问 Embedding 能力，不直接依赖 Provider 实现。
    """

    def __init__(self, provider: EmbeddingProvider | None = None) -> None:
        """初始化 Embedding 服务。

        Args:
            provider: Embedding Provider 实例，None 时从工厂获取
        """
        self._provider = provider or get_embedding_provider()

    @property
    def provider(self) -> EmbeddingProvider:
        """当前 Embedding Provider 实例。"""
        return self._provider

    @property
    def name(self) -> str:
        """Provider 名称（openai/bge）。"""
        return self._provider.name

    @property
    def dimension(self) -> int:
        """向量维度。"""
        return self._provider.dimension

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """文档批量向量化。

        将文本切片批量转换为向量，用于文档入库。
        Provider 内部已处理分批（OpenAI 每批 100 条）。

        Args:
            texts: 文本切片列表

        Returns:
            向量列表，与输入文本一一对应

        Raises:
            Exception: 向量化失败
        """
        if not texts:
            return []
        logger.info(
            "开始文档向量化，共 %d 个切片，Provider=%s，维度=%d",
            len(texts),
            self.name,
            self.dimension,
        )
        embeddings = await self._provider.embed(texts)
        logger.info("文档向量化完成，生成 %d 个向量", len(embeddings))
        return embeddings

    async def embed_query(self, text: str) -> List[float]:
        """查询向量化。

        将用户问题转换为向量，用于 RAG 检索。

        Args:
            text: 用户查询文本

        Returns:
            查询向量

        Raises:
            Exception: 向量化失败
        """
        if not text or not text.strip():
            raise ValueError("查询文本不能为空")
        return await self._provider.embed_query(text)


def get_embedding_service() -> EmbeddingService:
    """获取 EmbeddingService 实例。

    每次返回新实例（轻量，Provider 为单例）。

    Returns:
        EmbeddingService 实例
    """
    return EmbeddingService()
