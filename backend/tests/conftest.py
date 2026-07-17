"""
pytest 共享夹具。

提供测试用的夹具:
- 配置重置（清除 lru_cache）
- Mock Embedding Provider
- Mock LLM Provider
- Mock ChromaClient
- 内存数据库会话
- FastAPI 测试客户端
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# 设置测试环境变量（在导入 app 模块前设置）
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("EMBEDDING_PROVIDER", "openai")


@pytest.fixture(autouse=True)
def reset_caches():
    """每个测试前清除 lru_cache，确保隔离。"""
    from app.config.settings import get_settings
    from app.providers.embedding.factory import get_embedding_provider
    from app.providers.llm.factory import get_llm_provider
    from app.services.chroma_client import get_chroma_client

    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_chroma_client.cache_clear()
    yield
    # 测试后再次清除
    get_settings.cache_clear()
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_chroma_client.cache_clear()


@pytest.fixture
def mock_embedding_provider():
    """Mock Embedding Provider。"""
    provider = MagicMock()
    provider.name = "openai"
    provider.dimension = 1536
    provider.embed = AsyncMock(return_value=[[0.1] * 1536])
    provider.embed_query = AsyncMock(return_value=[0.1] * 1536)
    return provider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM Provider。"""
    from app.providers.llm.base import ChatChunk, ChatResponse, Message

    provider = MagicMock()
    provider.name = "openai"
    provider.model = "gpt-4o-mini"

    async def mock_chat_completion(messages, stream=False, **kwargs):
        if stream:
            async def stream_gen():
                yield ChatChunk(content="这是", finish_reason=None)
                yield ChatChunk(content="回答", finish_reason=None)
                yield ChatChunk(content="。", finish_reason="stop")

            return stream_gen()
        else:
            return ChatResponse(
                content="这是回答。",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            )

    provider.chat_completion = mock_chat_completion
    return provider


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaClient。"""
    client = MagicMock()
    collection = MagicMock()
    client.get_collection.return_value = collection
    client.add_vectors = MagicMock(return_value=5)
    client.delete_by_doc_id = MagicMock(return_value=None)
    client.count_total = MagicMock(return_value=100)
    client.collection_exists = MagicMock(return_value=True)

    # query 返回模拟检索结果
    client.query = MagicMock(
        return_value=[
            {
                "id": "doc1_0",
                "document": "RAG 是检索增强生成",
                "metadata": {
                    "doc_id": "doc-uuid-1",
                    "doc_name": "test.pdf",
                    "chunk_index": 0,
                    "source_path": "uploads/test.pdf",
                    "char_count": 100,
                },
                "distance": 0.3,
                "similarity": 0.85,
            }
        ]
    )
    return client


# ===== API 测试夹具 =====


@pytest.fixture
def mock_db():
    """Mock 数据库会话。"""
    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
async def client(mock_db):
    """创建异步测试客户端，覆盖 get_db 依赖。"""
    from app.database.session import get_db
    from app.main import app

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
