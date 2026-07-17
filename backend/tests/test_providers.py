"""
Provider 抽象层单元测试。

测试 Embedding Provider 与 LLM Provider 的实现与工厂。
使用 mock 避免实际 API 调用。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import (
    get_collection_name,
    get_embedding_provider,
)
from app.providers.llm.base import ChatChunk, LLMProvider, Message
from app.providers.llm.factory import get_llm_provider


class TestEmbeddingProviderBase:
    """Embedding Provider 抽象基类测试。"""

    def test_cannot_instantiate_abc(self):
        """抽象类不能实例化。"""
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_subclass_must_implement_all(self):
        """子类必须实现所有抽象方法。"""

        class IncompleteProvider(EmbeddingProvider):
            async def embed(self, texts):
                return []

            # 缺少 embed_query, dimension, name

        with pytest.raises(TypeError):
            IncompleteProvider()


class TestOpenAIEmbeddingProvider:
    """OpenAI Embedding Provider 测试。"""

    def test_properties(self):
        """Provider 属性。"""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(
            api_key="test-key", model="text-embedding-3-small"
        )
        assert provider.name == "openai"
        assert provider.dimension == 1536

    @pytest.mark.asyncio
    async def test_embed_calls_openai(self):
        """embed 应调用 OpenAI API。"""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(api_key="test-key", model="test-model")
        # Mock OpenAI 客户端
        provider._client = MagicMock()
        mock_response = MagicMock()
        item1 = MagicMock()
        item1.embedding = [0.1] * 1536
        item1.index = 0
        item2 = MagicMock()
        item2.embedding = [0.2] * 1536
        item2.index = 1
        mock_response.data = [item1, item2]
        provider._client.embeddings = MagicMock(create=AsyncMock(return_value=mock_response))

        result = await provider.embed(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_query(self):
        """embed_query 应返回单个向量。"""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()
        mock_response = MagicMock()
        item = MagicMock()
        item.embedding = [0.1] * 1536
        item.index = 0
        mock_response.data = [item]
        provider._client.embeddings = MagicMock(create=AsyncMock(return_value=mock_response))

        result = await provider.embed_query("query text")
        assert len(result) == 1536


class TestBGEEmbeddingProvider:
    """BGE Embedding Provider 测试。"""

    def test_properties(self):
        """Provider 属性。"""
        from app.providers.embedding.bge_provider import BGEEmbeddingProvider

        provider = BGEEmbeddingProvider(cache_dir="./data/models")
        assert provider.name == "bge"
        assert provider.dimension == 1024


class TestEmbeddingFactory:
    """Embedding Provider 工厂测试。"""

    def test_get_collection_name_openai(self):
        """OpenAI collection 名称。"""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(api_key="test", model="test")
        name = get_collection_name(provider)
        assert name == "kb_openai_1536"

    def test_get_collection_name_bge(self):
        """BGE collection 名称。"""
        from app.providers.embedding.bge_provider import BGEEmbeddingProvider

        provider = BGEEmbeddingProvider(cache_dir="./data/models")
        name = get_collection_name(provider)
        assert name == "kb_bge_1024"

    def test_get_embedding_provider_openai(self):
        """工厂返回 OpenAI Provider。"""
        from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider

        provider = get_embedding_provider()
        assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_get_embedding_provider_invalid(self):
        """无效 Provider 名称应抛出 ValueError。"""
        with patch("app.providers.embedding.factory.get_settings") as mock_settings:
            mock_settings.return_value.EMBEDDING_PROVIDER = "invalid"
            get_embedding_provider.cache_clear()
            with pytest.raises(ValueError, match="不支持"):
                get_embedding_provider()

    def test_factory_singleton(self):
        """工厂应返回单例。"""
        p1 = get_embedding_provider()
        p2 = get_embedding_provider()
        assert p1 is p2


class TestLLMProviderBase:
    """LLM Provider 抽象基类测试。"""

    def test_cannot_instantiate_abc(self):
        """抽象类不能实例化。"""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_message_dataclass(self):
        """Message 数据类。"""
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_chat_chunk_dataclass(self):
        """ChatChunk 数据类。"""
        chunk = ChatChunk(content="token", finish_reason=None)
        assert chunk.content == "token"
        assert chunk.finish_reason is None

    def test_chat_chunk_default_finish_reason(self):
        """ChatChunk 默认 finish_reason。"""
        chunk = ChatChunk(content="text")
        assert chunk.finish_reason is None


class TestLLMFactory:
    """LLM Provider 工厂测试。"""

    def test_get_llm_provider_returns_instance(self):
        """工厂返回 LLM Provider 实例。"""
        from app.providers.llm.openai_provider import OpenAILLMProvider

        provider = get_llm_provider()
        assert isinstance(provider, OpenAILLMProvider)

    def test_factory_singleton(self):
        """工厂应返回单例。"""
        p1 = get_llm_provider()
        p2 = get_llm_provider()
        assert p1 is p2

    def test_provider_properties(self):
        """Provider 属性。"""
        provider = get_llm_provider()
        assert provider.name == "openai"
        assert provider.model == "gpt-4o-mini"
