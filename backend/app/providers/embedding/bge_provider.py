"""
BGE Embedding Provider。

基于 BAAI/bge-m3 本地模型，维度 1024。
通过 sentence-transformers 库加载，首次使用需下载约 2.3GB 模型。
"""

import asyncio
from functools import lru_cache
from typing import List

from app.providers.embedding.base import EmbeddingProvider


@lru_cache(maxsize=1)
def _load_bge_model(cache_dir: str):
    """懒加载 bge-m3 模型（单例）。

    模型约 2.3GB，首次加载耗时较长。
    使用 lru_cache 确保全局只加载一次。

    Args:
        cache_dir: 模型缓存目录

    Returns:
        SentenceTransformer 实例
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        "BAAI/bge-m3",
        cache_folder=cache_dir,
    )


class BGEEmbeddingProvider(EmbeddingProvider):
    """BGE Embedding Provider。

    使用 BAAI/bge-m3 本地模型生成向量。
    首次使用需下载约 2.3GB 模型文件。

    Attributes:
        dimension: 1024
        name: "bge"
    """

    # bge-m3 维度
    _DIMENSION = 1024
    _NAME = "bge"

    def __init__(self, cache_dir: str = "./data/models"):
        """初始化 BGE Embedding Provider。

        Args:
            cache_dir: 模型缓存目录
        """
        self._cache_dir = cache_dir
        # 模型懒加载，首次调用 embed 时才加载
        self._model = None

    def _ensure_model(self):
        """确保模型已加载。"""
        if self._model is None:
            self._model = _load_bge_model(self._cache_dir)

    @property
    def dimension(self) -> int:
        return self._DIMENSION

    @property
    def name(self) -> str:
        return self._NAME

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量。

        sentence-transformers 是同步库，使用 asyncio.to_thread
        在线程池中执行，避免阻塞事件循环。

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        if not texts:
            return []

        self._ensure_model()

        # 在线程池中执行同步推理
        embeddings = await asyncio.to_thread(
            self._model.encode,
            texts,
            normalize_embeddings=True,
        )
        # 转换为 list[list[float]]
        return embeddings.tolist()

    async def embed_query(self, text: str) -> List[float]:
        """生成单个查询向量。

        Args:
            text: 查询文本

        Returns:
            查询向量
        """
        self._ensure_model()

        embedding = await asyncio.to_thread(
            self._model.encode,
            text,
            normalize_embeddings=True,
        )
        return embedding.tolist()
