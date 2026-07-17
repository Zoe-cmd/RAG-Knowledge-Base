"""
Service 层单元测试。

测试 ChromaClient、EmbeddingService、ChatService、DocumentService、RAGService。
使用 mock 隔离外部依赖（数据库、Chroma、OpenAI API）。
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.llm.base import ChatChunk, Message
from app.services.chroma_client import ChromaClient
from app.services.embedding_service import EmbeddingService
from app.services.prompt_template import build_rag_messages


# ===== ChromaClient 测试 =====


class TestChromaClient:
    """Chroma 客户端测试。"""

    def test_get_collection(self, mock_embedding_provider):
        """获取 collection。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            collection = client.get_collection(mock_embedding_provider)
            assert collection is mock_collection
            mock_client.get_or_create_collection.assert_called_once()

    def test_add_vectors(self, mock_embedding_provider):
        """添加向量。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            count = client.add_vectors(
                provider=mock_embedding_provider,
                doc_id="doc-1",
                doc_name="test.pdf",
                source_path="uploads/test.pdf",
                chunks=["chunk1", "chunk2"],
                embeddings=[[0.1] * 1536, [0.2] * 1536],
            )
            assert count == 2
            mock_collection.add.assert_called_once()

    def test_add_vectors_empty(self, mock_embedding_provider):
        """空切片列表不添加。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            count = client.add_vectors(
                provider=mock_embedding_provider,
                doc_id="doc-1",
                doc_name="test.pdf",
                source_path="uploads/test.pdf",
                chunks=[],
                embeddings=[],
            )
            assert count == 0

    def test_query(self, mock_embedding_provider):
        """向量检索。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "ids": [["id1", "id2"]],
                "documents": [["doc1", "doc2"]],
                "metadatas": [[{"doc_id": "d1"}, {"doc_id": "d2"}]],
                "distances": [[0.2, 0.4]],
            }
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            results = client.query(
                mock_embedding_provider, [0.1] * 1536, top_k=2
            )
            assert len(results) == 2
            assert results[0]["similarity"] > results[1]["similarity"]
            assert "id" in results[0]
            assert "document" in results[0]
            assert "metadata" in results[0]

    def test_delete_by_doc_id(self, mock_embedding_provider):
        """按文档 ID 删除向量。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            client.delete_by_doc_id(mock_embedding_provider, "doc-1")
            mock_collection.delete.assert_called_once_with(where={"doc_id": "doc-1"})

    def test_count_by_doc_id(self, mock_embedding_provider):
        """按文档 ID 统计向量数。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_collection.get.return_value = {"ids": ["id1", "id2", "id3"]}
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            count = client.count_by_doc_id(mock_embedding_provider, "doc-1")
            assert count == 3

    def test_count_total(self, mock_embedding_provider):
        """统计向量总数。"""
        with patch("app.services.chroma_client.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 42
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client

            client = ChromaClient()
            count = client.count_total(mock_embedding_provider)
            assert count == 42


# ===== EmbeddingService 测试 =====


class TestEmbeddingService:
    """Embedding 服务测试。"""

    def test_properties(self, mock_embedding_provider):
        """服务属性。"""
        service = EmbeddingService(provider=mock_embedding_provider)
        assert service.name == "openai"
        assert service.dimension == 1536
        assert service.provider is mock_embedding_provider

    @pytest.mark.asyncio
    async def test_embed_documents(self, mock_embedding_provider):
        """文档批量向量化。"""
        mock_embedding_provider.embed = AsyncMock(
            return_value=[[0.1] * 1536, [0.2] * 1536]
        )
        service = EmbeddingService(provider=mock_embedding_provider)
        result = await service.embed_documents(["text1", "text2"])
        assert len(result) == 2
        mock_embedding_provider.embed.assert_called_once_with(["text1", "text2"])

    @pytest.mark.asyncio
    async def test_embed_documents_empty(self, mock_embedding_provider):
        """空列表返回空。"""
        service = EmbeddingService(provider=mock_embedding_provider)
        result = await service.embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_query(self, mock_embedding_provider):
        """查询向量化。"""
        mock_embedding_provider.embed_query = AsyncMock(
            return_value=[0.1] * 1536
        )
        service = EmbeddingService(provider=mock_embedding_provider)
        result = await service.embed_query("test query")
        assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_embed_query_empty_raises(self, mock_embedding_provider):
        """空查询应抛出 ValueError。"""
        service = EmbeddingService(provider=mock_embedding_provider)
        with pytest.raises(ValueError, match="不能为空"):
            await service.embed_query("")
        with pytest.raises(ValueError):
            await service.embed_query("   ")


# ===== ChatService 测试 =====


class TestChatService:
    """聊天服务测试。"""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """创建会话。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        service = ChatService(db)
        session = await service.create_session("测试会话")
        assert session.title == "测试会话"
        assert session.message_count == 0
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """获取不存在的会话返回 None。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        result = await service.get_session(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """获取会话列表。"""
        from app.models.session import ChatSession

        from app.services.chat_service import ChatService

        session1 = ChatSession(id=uuid.uuid4(), title="会话1", message_count=2)
        session2 = ChatSession(id=uuid.uuid4(), title="会话2", message_count=4)

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [session1, session2]
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        sessions = await service.list_sessions()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_save_message_updates_session(self):
        """保存消息应更新会话统计。"""
        from app.models.session import ChatSession

        from app.services.chat_service import ChatService

        session = ChatSession(id=uuid.uuid4(), title="新会话", message_count=0)
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        # get_session 返回会话
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = session
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        message = await service.save_message(
            session_id=session.id,
            role="user",
            content="什么是 RAG？",
        )
        assert message.role == "user"
        assert session.message_count == 1
        assert session.last_message_at is not None
        # 首条用户消息应更新标题
        assert session.title == "什么是 RAG？"

    @pytest.mark.asyncio
    async def test_save_message_session_not_found(self):
        """保存消息时会话不存在应抛出 ValueError。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        with pytest.raises(ValueError, match="会话不存在"):
            await service.save_message(
                session_id=uuid.uuid4(),
                role="user",
                content="test",
            )

    @pytest.mark.asyncio
    async def test_get_recent_history(self):
        """获取最近历史对话。"""
        from app.models.message import ChatMessage

        from app.services.chat_service import ChatService

        # 创建 4 条消息（2 轮）
        now = datetime.now(timezone.utc)
        messages = [
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="user", content="问题1", created_at=now),
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="assistant", content="回答1", created_at=now),
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="user", content="问题2", created_at=now),
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="assistant", content="回答2", created_at=now),
        ]

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = list(reversed(messages))
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        history = await service.get_recent_history(uuid.uuid4())
        assert len(history) == 4
        assert all(isinstance(m, Message) for m in history)
        # 应为时间正序
        assert history[0].content == "问题1"
        assert history[3].content == "回答2"

    def test_build_rag_messages(self):
        """组装 RAG 消息。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        service = ChatService(db)
        messages = service.build_rag_messages(
            question="问题",
            context_chunks=["上下文"],
            history=[Message(role="user", content="历史")],
        )
        assert len(messages) >= 3
        assert messages[-1].content == "问题"


# ===== RAGService 测试 =====


class TestRAGService:
    """RAG 服务测试。"""

    @pytest.mark.asyncio
    async def test_retrieve_with_results(
        self, mock_embedding_provider, mock_chroma_client
    ):
        """检索有结果。"""
        from app.services.rag_service import RAGService

        db = MagicMock()
        mock_embedding_provider.embed_query = AsyncMock(
            return_value=[0.1] * 1536
        )

        with patch(
            "app.services.rag_service.get_chroma_client",
            return_value=mock_chroma_client,
        ), patch(
            "app.services.rag_service.EmbeddingService",
        ) as mock_emb_service_cls:
            mock_emb_service = MagicMock()
            mock_emb_service.provider = mock_embedding_provider
            mock_emb_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb_service.name = "openai"
            mock_emb_service.dimension = 1536
            mock_emb_service_cls.return_value = mock_emb_service

            service = RAGService(db)
            results = await service.retrieve("什么是 RAG？")
            assert len(results) >= 1
            assert results[0].doc_name == "test.pdf"
            assert results[0].similarity > 0.3  # 高于阈值

    @pytest.mark.asyncio
    async def test_retrieve_filters_low_similarity(
        self, mock_embedding_provider
    ):
        """检索应过滤低相似度结果。"""
        from app.services.rag_service import RAGService

        db = MagicMock()
        mock_embedding_provider.embed_query = AsyncMock(
            return_value=[0.1] * 1536
        )

        mock_chroma = MagicMock()
        mock_chroma.query = MagicMock(
            return_value=[
                {
                    "id": "1",
                    "document": "不相关内容",
                    "metadata": {"doc_id": "d1", "doc_name": "test.pdf", "chunk_index": 0, "source_path": ""},
                    "distance": 1.8,  # 高距离 = 低相似度
                    "similarity": 0.1,  # 低于阈值 0.3
                }
            ]
        )

        with patch(
            "app.services.rag_service.get_chroma_client",
            return_value=mock_chroma,
        ), patch(
            "app.services.rag_service.EmbeddingService",
        ) as mock_emb_service_cls:
            mock_emb_service = MagicMock()
            mock_emb_service.provider = mock_embedding_provider
            mock_emb_service.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb_service.name = "openai"
            mock_emb_service.dimension = 1536
            mock_emb_service_cls.return_value = mock_emb_service

            service = RAGService(db)
            results = await service.retrieve("不相关的问题")
            assert len(results) == 0  # 被过滤

    @pytest.mark.asyncio
    async def test_retrieval_result_to_reference(self):
        """RetrievalResult 转引用字典。"""
        from app.services.rag_service import RetrievalResult

        result = RetrievalResult(
            doc_id="doc-1",
            doc_name="test.pdf",
            chunk_index=0,
            source_path="uploads/test.pdf",
            content="A" * 300,
            similarity=0.85,
        )
        ref = result.to_reference()
        assert ref["doc_id"] == "doc-1"
        assert ref["doc_name"] == "test.pdf"
        assert ref["chunk_index"] == 0
        assert "chunk" in ref
        assert ref["similarity"] == 0.85
        # 长内容应截断
        assert len(ref["chunk"]) <= 203  # 200 + "..."


# ===== DocumentService 测试 =====


class TestDocumentService:
    """文档服务测试。"""

    def test_validate_file_supported(self):
        """支持的文件类型。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        service = DocumentService(db)
        # 不应抛出异常
        service._validate_file("pdf", 1000)
        service._validate_file("docx", 1000)
        service._validate_file("md", 1000)
        service._validate_file("txt", 1000)

    def test_validate_file_unsupported(self):
        """不支持的文件类型。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        service = DocumentService(db)
        with pytest.raises(ValueError, match="不支持"):
            service._validate_file("xlsx", 1000)

    def test_validate_file_too_large(self):
        """文件过大。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        service = DocumentService(db)
        with pytest.raises(ValueError, match="超过限制"):
            service._validate_file("pdf", 100 * 1024 * 1024)  # 100MB

    def test_validate_file_zero_size(self):
        """文件大小为 0。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        service = DocumentService(db)
        with pytest.raises(ValueError, match="不能为 0"):
            service._validate_file("pdf", 0)

    def test_compute_hash(self, tmp_path):
        """计算文件哈希。"""
        from app.services.document_service import DocumentService

        file_path = tmp_path / "test.txt"
        file_path.write_text("test content", encoding="utf-8")

        hash1 = DocumentService._compute_hash(file_path)
        assert len(hash1) == 64  # SHA-256

        # 相同内容哈希相同
        file_path2 = tmp_path / "test2.txt"
        file_path2.write_text("test content", encoding="utf-8")
        hash2 = DocumentService._compute_hash(file_path2)
        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_check_document_limit_exceeded(self):
        """文档数量超限。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 100  # 已达上限
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        with pytest.raises(ValueError, match="上限"):
            await service._check_document_limit()
