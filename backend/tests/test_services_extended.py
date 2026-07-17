"""
Service 层补充测试。

补充 DocumentService、ChatService、RAGService 的测试用例，
提升测试覆盖率至 80% 以上。
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.llm.base import ChatChunk, Message


# ===== DocumentService 补充测试 =====


class TestDocumentServiceList:
    """DocumentService 列表与查询测试。"""

    @pytest.mark.asyncio
    async def test_list_documents(self):
        """文档列表分页。"""
        from app.models.document import Document
        from app.services.document_service import DocumentService

        doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            file_type="pdf",
            file_size=1000,
            file_path="uploads/test.pdf",
            status="completed",
        )

        db = MagicMock()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 1
        list_mock = MagicMock()
        list_mock.scalars.return_value.all.return_value = [doc]
        db.execute = AsyncMock(side_effect=[count_mock, list_mock])

        service = DocumentService(db)
        result = await service.list_documents(page=1, page_size=20)
        assert result["total"] == 1
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_documents_empty(self):
        """空文档列表。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        list_mock = MagicMock()
        list_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[count_mock, list_mock])

        service = DocumentService(db)
        result = await service.list_documents(page=1, page_size=20)
        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_get_document_found(self):
        """获取存在的文档。"""
        from app.models.document import Document
        from app.services.document_service import DocumentService

        doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            file_type="pdf",
            file_size=1000,
            file_path="uploads/test.pdf",
            status="completed",
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service.get_document(doc.id)
        assert result is doc

    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """获取不存在的文档。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service.get_document(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_count_documents(self):
        """统计文档数量。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 5
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        count = await service.count_documents()
        assert count == 5

    @pytest.mark.asyncio
    async def test_find_by_hash_found(self):
        """通过哈希找到文档（去重）。"""
        from app.models.document import Document
        from app.services.document_service import DocumentService

        doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            file_type="pdf",
            file_size=1000,
            file_path="uploads/test.pdf",
            content_hash="abc123",
            status="completed",
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service._find_by_hash("abc123")
        assert result is doc

    @pytest.mark.asyncio
    async def test_find_by_hash_not_found(self):
        """通过哈希未找到文档。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service._find_by_hash("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """知识库统计。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 5
        chunks_mock = MagicMock()
        chunks_mock.scalar_one.return_value = 100
        db.execute = AsyncMock(side_effect=[count_mock, chunks_mock])

        service = DocumentService(db)
        stats = await service.get_stats()
        assert stats["document_count"] == 5
        assert stats["total_chunks"] == 100
        assert "embedding_provider" in stats
        assert "embedding_dimension" in stats


class TestDocumentServiceDelete:
    """DocumentService 删除测试。"""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, mock_embedding_provider):
        """删除文档成功。"""
        from app.models.document import Document
        from app.services.document_service import DocumentService

        doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            file_type="pdf",
            file_size=1000,
            file_path="/tmp/nonexistent_test_file.pdf",
            status="completed",
            embedding_provider="openai",
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()

        service = DocumentService(db, embedding_service=MagicMock(provider=mock_embedding_provider, name="openai", dimension=1536))

        with patch("app.services.document_service.get_chroma_client") as mock_chroma_factory, \
             patch("app.services.document_service.asyncio.to_thread", new_callable=AsyncMock):
            mock_chroma = MagicMock()
            mock_chroma.delete_by_doc_id = MagicMock()
            mock_chroma_factory.return_value = mock_chroma

            result = await service.delete_document(doc.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self):
        """删除不存在的文档返回 False。"""
        from app.services.document_service import DocumentService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service.delete_document(uuid.uuid4())
        assert result is False


class TestDocumentServiceUpload:
    """DocumentService 上传测试。"""

    @pytest.mark.asyncio
    async def test_upload_rejects_duplicate(self, tmp_path):
        """重复上传（哈希去重）返回已存在文档。"""
        from app.models.document import Document
        from app.services.document_service import DocumentService

        existing_doc = Document(
            id=uuid.uuid4(),
            filename="existing.pdf",
            file_type="pdf",
            file_size=1000,
            file_path="uploads/existing.pdf",
            content_hash="abc123",
            status="completed",
        )

        db = MagicMock()
        db.flush = AsyncMock()
        db.add = MagicMock()

        service = DocumentService(db)

        # Mock internal methods
        service._compute_hash = MagicMock(return_value="abc123")
        service._find_by_hash = AsyncMock(return_value=existing_doc)
        service._validate_file = MagicMock()
        service._check_document_limit = AsyncMock()

        file_path = tmp_path / "test.pdf"
        file_path.write_text("test", encoding="utf-8")

        result = await service.upload_and_process(
            file_path=file_path,
            filename="test.pdf",
            file_type="pdf",
            file_size=4,
        )
        assert result is existing_doc


# ===== ChatService 补充测试 =====


class TestChatServiceDelete:
    """ChatService 删除测试。"""

    @pytest.mark.asyncio
    async def test_delete_session_success(self):
        """删除会话成功。"""
        from app.models.session import ChatSession
        from app.services.chat_service import ChatService

        session = ChatSession(id=uuid.uuid4(), title="测试", message_count=2)
        db = MagicMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = session
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        result = await service.delete_session(session.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self):
        """删除不存在的会话返回 False。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        result = await service.delete_session(uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_all_sessions(self):
        """清空所有会话。"""
        from app.models.session import ChatSession
        from app.services.chat_service import ChatService

        sessions = [
            ChatSession(id=uuid.uuid4(), title="会话1", message_count=0),
            ChatSession(id=uuid.uuid4(), title="会话2", message_count=0),
        ]

        db = MagicMock()
        db.flush = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = sessions
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        count = await service.delete_all_sessions()
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_all_sessions_empty(self):
        """清空空会话列表。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        count = await service.delete_all_sessions()
        assert count == 0

    @pytest.mark.asyncio
    async def test_list_messages(self):
        """获取会话消息列表。"""
        from app.models.message import ChatMessage
        from app.services.chat_service import ChatService

        messages = [
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="user", content="问题", created_at=datetime.now(timezone.utc)),
            ChatMessage(id=uuid.uuid4(), session_id=uuid.uuid4(), role="assistant", content="回答", created_at=datetime.now(timezone.utc)),
        ]

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = messages
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        result = await service.list_messages(uuid.uuid4())
        assert len(result) == 2
        assert result[0].role == "user"
        assert result[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_get_message_count(self):
        """统计会话消息数。"""
        from app.services.chat_service import ChatService

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 10
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        count = await service.get_message_count(uuid.uuid4())
        assert count == 10

    @pytest.mark.asyncio
    async def test_save_assistant_message(self):
        """保存 assistant 消息（含 references 和 elapsed_ms）。"""
        from app.models.session import ChatSession
        from app.services.chat_service import ChatService

        session = ChatSession(id=uuid.uuid4(), title="测试", message_count=1)
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = session
        db.execute = AsyncMock(return_value=result_mock)

        service = ChatService(db)
        refs = [{"doc_id": "d1", "doc_name": "test.pdf"}]
        message = await service.save_message(
            session_id=session.id,
            role="assistant",
            content="这是回答",
            references=refs,
            elapsed_ms=1500,
        )
        assert message.role == "assistant"
        assert message.references == refs
        assert message.elapsed_ms == 1500
        assert session.message_count == 2


# ===== RAGService 补充测试 =====


class TestRAGServiceAnswer:
    """RAGService answer() 方法测试。"""

    @pytest.mark.asyncio
    async def test_answer_no_results(self, mock_embedding_provider, mock_llm_provider):
        """无检索结果时返回提示消息。"""
        from app.services.rag_service import RAGService

        db = MagicMock()

        with patch(
            "app.services.rag_service.EmbeddingService"
        ) as mock_emb_cls, patch(
            "app.services.rag_service.get_chroma_client"
        ) as mock_chroma_factory, patch(
            "app.services.rag_service.get_llm_provider",
            return_value=mock_llm_provider,
        ), patch(
            "app.services.rag_service.ChatService"
        ) as mock_chat_cls:
            mock_emb = MagicMock()
            mock_emb.provider = mock_embedding_provider
            mock_emb.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb.name = "openai"
            mock_emb.dimension = 1536
            mock_emb_cls.return_value = mock_emb

            mock_chroma = MagicMock()
            mock_chroma.query = MagicMock(return_value=[])  # 无检索结果
            mock_chroma_factory.return_value = mock_chroma

            mock_chat = MagicMock()
            mock_chat.get_recent_history = AsyncMock(return_value=[])
            mock_chat.build_rag_messages = MagicMock(
                return_value=[Message(role="system", content="test")]
            )
            mock_chat_cls.return_value = mock_chat

            service = RAGService(db)
            result = await service.answer(
                session_id=uuid.uuid4(), question="测试问题"
            )

            assert result.references == []
            # 应该有一个 chunk（提示消息）
            chunks = []
            async for chunk in result.answer_chunks:
                chunks.append(chunk)
            assert len(chunks) == 1
            assert "未在知识库中找到" in chunks[0].content

    @pytest.mark.asyncio
    async def test_answer_with_results(
        self, mock_embedding_provider, mock_llm_provider
    ):
        """有检索结果时调用 LLM 流式生成。"""
        from app.services.rag_service import RAGService

        db = MagicMock()

        with patch(
            "app.services.rag_service.EmbeddingService"
        ) as mock_emb_cls, patch(
            "app.services.rag_service.get_chroma_client"
        ) as mock_chroma_factory, patch(
            "app.services.rag_service.get_llm_provider",
            return_value=mock_llm_provider,
        ), patch(
            "app.services.rag_service.ChatService"
        ) as mock_chat_cls:
            mock_emb = MagicMock()
            mock_emb.provider = mock_embedding_provider
            mock_emb.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb.name = "openai"
            mock_emb.dimension = 1536
            mock_emb_cls.return_value = mock_emb

            mock_chroma = MagicMock()
            mock_chroma.query = MagicMock(
                return_value=[
                    {
                        "id": "1",
                        "document": "RAG 是检索增强生成",
                        "metadata": {
                            "doc_id": "d1",
                            "doc_name": "test.pdf",
                            "chunk_index": 0,
                            "source_path": "uploads/test.pdf",
                        },
                        "distance": 0.3,
                        "similarity": 0.85,
                    }
                ]
            )
            mock_chroma_factory.return_value = mock_chroma

            mock_chat = MagicMock()
            mock_chat.get_recent_history = AsyncMock(return_value=[])
            mock_chat.build_rag_messages = MagicMock(
                return_value=[Message(role="system", content="test")]
            )
            mock_chat_cls.return_value = mock_chat

            service = RAGService(db)
            result = await service.answer(
                session_id=uuid.uuid4(), question="什么是 RAG？"
            )

            assert len(result.references) == 1
            assert result.references[0]["doc_name"] == "test.pdf"

            # 收集流式 chunks
            chunks = []
            async for chunk in result.answer_chunks:
                chunks.append(chunk)
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_non_stream(self, mock_embedding_provider, mock_llm_provider):
        """非流式问答。"""
        from app.services.rag_service import RAGService

        db = MagicMock()

        with patch(
            "app.services.rag_service.EmbeddingService"
        ) as mock_emb_cls, patch(
            "app.services.rag_service.get_chroma_client"
        ) as mock_chroma_factory, patch(
            "app.services.rag_service.get_llm_provider",
            return_value=mock_llm_provider,
        ), patch(
            "app.services.rag_service.ChatService"
        ) as mock_chat_cls:
            mock_emb = MagicMock()
            mock_emb.provider = mock_embedding_provider
            mock_emb.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb.name = "openai"
            mock_emb.dimension = 1536
            mock_emb_cls.return_value = mock_emb

            mock_chroma = MagicMock()
            mock_chroma.query = MagicMock(
                return_value=[
                    {
                        "id": "1",
                        "document": "RAG 内容",
                        "metadata": {
                            "doc_id": "d1",
                            "doc_name": "test.pdf",
                            "chunk_index": 0,
                            "source_path": "uploads/test.pdf",
                        },
                        "distance": 0.3,
                        "similarity": 0.85,
                    }
                ]
            )
            mock_chroma_factory.return_value = mock_chroma

            mock_chat = MagicMock()
            mock_chat.build_rag_messages = MagicMock(
                return_value=[Message(role="system", content="test")]
            )
            mock_chat_cls.return_value = mock_chat

            service = RAGService(db)
            answer, refs = await service.chat_non_stream(
                question="什么是 RAG？", history=[]
            )
            assert "这是回答" in answer
            assert len(refs) == 1

    @pytest.mark.asyncio
    async def test_chat_non_stream_no_results(
        self, mock_embedding_provider, mock_llm_provider
    ):
        """非流式问答无检索结果。"""
        from app.services.rag_service import RAGService

        db = MagicMock()

        with patch(
            "app.services.rag_service.EmbeddingService"
        ) as mock_emb_cls, patch(
            "app.services.rag_service.get_chroma_client"
        ) as mock_chroma_factory, patch(
            "app.services.rag_service.get_llm_provider",
            return_value=mock_llm_provider,
        ), patch(
            "app.services.rag_service.ChatService"
        ):
            mock_emb = MagicMock()
            mock_emb.provider = mock_embedding_provider
            mock_emb.embed_query = AsyncMock(return_value=[0.1] * 1536)
            mock_emb.name = "openai"
            mock_emb.dimension = 1536
            mock_emb_cls.return_value = mock_emb

            mock_chroma = MagicMock()
            mock_chroma.query = MagicMock(return_value=[])
            mock_chroma_factory.return_value = mock_chroma

            service = RAGService(db)
            answer, refs = await service.chat_non_stream("问题")
            assert "未在知识库中找到" in answer
            assert refs == []


# ===== 额外 API 测试 =====


class TestDocumentStatsAPI:
    """文档统计 API 测试。"""

    @pytest.mark.asyncio
    async def test_get_stats(self, client, mock_db):
        """获取知识库统计。"""
        with patch(
            "app.api.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_stats = AsyncMock(
                return_value={
                    "document_count": 5,
                    "total_chunks": 100,
                    "embedding_provider": "openai",
                    "embedding_dimension": 1536,
                }
            )
            mock_service_cls.return_value = mock_service

            response = await client.get("/api/documents/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["document_count"] == 5
            assert data["data"]["total_chunks"] == 100


class TestSessionMessagesAPI:
    """会话消息 API 测试。"""

    @pytest.mark.asyncio
    async def test_get_session_messages_success(self, client, mock_db):
        """获取会话消息列表。"""
        from app.models.message import ChatMessage
        from app.models.session import ChatSession

        session = ChatSession(id=uuid.uuid4(), title="测试", message_count=2)
        messages = [
            ChatMessage(
                id=uuid.uuid4(),
                session_id=session.id,
                role="user",
                content="问题",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        with patch("app.api.sessions.ChatService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_session = AsyncMock(return_value=session)
            mock_service.list_messages = AsyncMock(return_value=messages)
            mock_service_cls.return_value = mock_service

            response = await client.get(
                f"/api/chat/sessions/{session.id}/messages"
            )
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data["data"]
            assert len(data["data"]["messages"]) == 1


class TestExceptionHandlers:
    """异常处理器测试。"""

    @pytest.mark.asyncio
    async def test_validation_error_format(self, client):
        """验证错误响应格式。"""
        response = await client.post(
            "/api/chat/sessions",
            json={"title": "a" * 300},  # 超长标题
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
        assert "meta" in data
        assert "requestId" in data["meta"]
