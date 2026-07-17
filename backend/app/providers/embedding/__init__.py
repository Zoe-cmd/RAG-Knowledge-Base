"""Embedding Provider 抽象层。"""

from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "get_embedding_provider"]
