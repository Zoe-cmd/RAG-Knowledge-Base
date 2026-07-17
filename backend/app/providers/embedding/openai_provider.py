"""
OpenAI Embedding Provider。

基于 OpenAI text-embedding-3-small 模型，维度 1536。
支持通过 base_url 配置兼容端点。
"""

import asyncio
from typing import List

import openai

from app.providers.embedding.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding Provider。

    使用 openai SDK 调用 text-embedding-3-small 模型。
    支持 base_url 配置，兼容第三方 OpenAI 兼容端点。

    Attributes:
        dimension: 1536
        name: "openai"
    """

    # OpenAI text-embedding-3-small 维度
    _DIMENSION = 1536
    _NAME = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
    ):
        """初始化 OpenAI Embedding Provider。

        Args:
            api_key: OpenAI API Key
            model: Embedding 模型名，默认 text-embedding-3-small
            base_url: API 基础 URL，可配置为兼容端点
            timeout: 请求超时（秒）
        """
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._model = model

    @property
    def dimension(self) -> int:
        return self._DIMENSION

    @property
    def name(self) -> str:
        return self._NAME

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量。

        OpenAI API 单次请求最多支持 2048 个输入，此处按需分批。
        实际场景中文档切分后的 chunk 数通常远小于此限制。

        Args:
            texts: 文本列表

        Returns:
            向量列表

        Raises:
            openai.APIError: API 调用失败
            openai.AuthenticationError: API Key 无效
        """
        if not texts:
            return []

        # 分批处理，每批最多 100 个（保守值，避免 token 限制）
        batch_size = 100
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
            )
            # 按 index 排序确保顺序正确
            batch_embeddings = [
                item.embedding for item in sorted(response.data, key=lambda x: x.index)
            ]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_query(self, text: str) -> List[float]:
        """生成单个查询向量。

        Args:
            text: 查询文本

        Returns:
            查询向量
        """
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding
