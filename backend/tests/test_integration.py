"""
集成测试 - API 端点集成测试。

补充单元测试（test_api.py）未覆盖的 API 层场景，提升 app/api/ 模块覆盖率：
- 文档上传成功流程与各种失败场景（补充 documents.py 覆盖）
- SSE 流式问答正常流程与异常（补充 chat.py 覆盖）
- 文档统计端点
- 会话消息列表成功流程

测试策略：
- 使用 httpx AsyncClient + ASGITransport 测试 FastAPI 端点
- 通过 dependency_overrides 覆盖 get_db（由 conftest 的 client fixture 完成）
- 通过 unittest.mock.patch 隔离 DocumentService / ChatService / RAGService
- SSE 流式测试通过 response.text 读取完整事件流并解析

对应测试计划: docs/test-plan.md
- TC-DOC-001~006: 文档上传各场景
- TC-RAG-001~003: SSE 流式问答
- TC-DOC-008: 文档统计
- TC-HIS-003: 会话消息列表
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.llm.base import ChatChunk
from app.services.rag_service import RAGStreamResult


# ===== 文档上传集成测试（补充 app/api/documents.py 覆盖）=====


class TestDocumentUploadIntegration:
    """文档上传端点集成测试，对应 TC-DOC-001~006。"""

    @pytest.mark.asyncio
    async def test_upload_txt_success(self, client, mock_db):
        """TC-DOC-001: 上传 TXT 文档成功流程。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            # 构造 mock document 对象
            doc_id = str(uuid.uuid4())
            doc = MagicMock()
            doc.to_dict.return_value = {
                "id": doc_id,
                "filename": "test.txt",
                "file_type": "txt",
                "file_size": 47,
                "status": "completed",
                "chunk_count": 1,
                "created_at": "2026-07-12T12:00:00",
            }
            mock_service = MagicMock()
            mock_service.upload_and_process = AsyncMock(return_value=doc)
            mock_service_cls.return_value = mock_service

            content = b"RAG is Retrieval Augmented Generation."
            response = await client.post(
                "/api/documents/upload",
                files=[("files", ("test.txt", content, "text/plain"))],
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["documents"]) == 1
        assert data["data"]["documents"][0]["filename"] == "test.txt"
        assert data["data"]["documents"][0]["file_type"] == "txt"
        assert data["data"]["failed"] == []

    @pytest.mark.asyncio
    async def test_upload_markdown_success(self, client, mock_db):
        """TC-DOC-003: 上传 Markdown 文档成功。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            doc = MagicMock()
            doc.to_dict.return_value = {
                "id": str(uuid.uuid4()),
                "filename": "guide.md",
                "file_type": "md",
                "file_size": 100,
                "status": "completed",
                "chunk_count": 1,
                "created_at": "2026-07-12T12:00:00",
            }
            mock_service = MagicMock()
            mock_service.upload_and_process = AsyncMock(return_value=doc)
            mock_service_cls.return_value = mock_service

            content = b"# RAG Guide\n\nRAG combines retrieval and generation."
            response = await client.post(
                "/api/documents/upload",
                files=[("files", ("guide.md", content, "text/markdown"))],
            )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["documents"][0]["file_type"] == "md"

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, client, mock_db):
        """TC-DOC-006/BC-003: 上传不支持的文件类型返回失败列表。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_and_process = AsyncMock()
            mock_service_cls.return_value = mock_service

            content = b"executable content"
            response = await client.post(
                "/api/documents/upload",
                files=[("files", ("malware.exe", content, "application/octet-stream"))],
            )

        assert response.status_code == 201  # 批量上传整体 201，单项失败在 failed 列表
        data = response.json()
        assert len(data["data"]["failed"]) == 1
        assert data["data"]["failed"][0]["code"] == "UNSUPPORTED_FILE_TYPE"
        assert data["data"]["failed"][0]["filename"] == "malware.exe"
        # DocumentService 不应被调用
        mock_service.upload_and_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_scanned_pdf(self, client, mock_db):
        """TC-DOC-006: 扫描件 PDF 返回 SCANNED_PDF 错误。"""
        from app.parsers.pdf_parser import ScannedPDFError

        with patch("app.api.documents.DocumentService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_and_process = AsyncMock(
                side_effect=ScannedPDFError("test.pdf")
            )
            mock_service_cls.return_value = mock_service

            # 构造一个最小 PDF 文件头
            content = b"%PDF-1.4\n%test\n"
            response = await client.post(
                "/api/documents/upload",
                files=[("files", ("scanned.pdf", content, "application/pdf"))],
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["failed"]) == 1
        assert data["data"]["failed"][0]["code"] == "SCANNED_PDF"
        assert "扫描件" in data["data"]["failed"][0]["error"]
        assert "OCR" in data["data"]["failed"][0]["error"]

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client, mock_db):
        """TC-DOC-006/BC-002: 超大文件返回 FILE_TOO_LARGE。"""
        # 通过 patch get_settings 降低大小限制，避免构造 21MB 内容
        with patch("app.api.documents.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.supported_file_types = ["pdf", "docx", "md", "txt"]
            mock_settings.max_file_size_bytes = 100  # 100 字节限制
            mock_get_settings.return_value = mock_settings

            with patch("app.api.documents.DocumentService") as mock_service_cls:
                mock_service = MagicMock()
                mock_service.upload_and_process = AsyncMock()
                mock_service_cls.return_value = mock_service

                content = b"x" * 200  # 200 字节，超过 100 字节限制
                response = await client.post(
                    "/api/documents/upload",
                    files=[("files", ("big.txt", content, "text/plain"))],
                )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["failed"]) == 1
        assert data["data"]["failed"][0]["code"] == "FILE_TOO_LARGE"
        mock_service.upload_and_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_batch_mixed_results(self, client, mock_db):
        """TC-DOC-005: 批量上传，部分成功部分失败。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            doc = MagicMock()
            doc.to_dict.return_value = {
                "id": str(uuid.uuid4()),
                "filename": "ok.txt",
                "file_type": "txt",
                "file_size": 10,
                "status": "completed",
                "chunk_count": 1,
                "created_at": "2026-07-12T12:00:00",
            }
            mock_service = MagicMock()
            # 第一个文件成功，第二个（.exe）在类型校验阶段就失败，不会调用 service
            mock_service.upload_and_process = AsyncMock(return_value=doc)
            mock_service_cls.return_value = mock_service

            response = await client.post(
                "/api/documents/upload",
                files=[
                    ("files", ("ok.txt", b"hello world", "text/plain")),
                    ("files", ("bad.exe", b"binary", "application/octet-stream")),
                ],
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["documents"]) == 1
        assert data["data"]["documents"][0]["filename"] == "ok.txt"
        assert len(data["data"]["failed"]) == 1
        assert data["data"]["failed"][0]["filename"] == "bad.exe"

    @pytest.mark.asyncio
    async def test_upload_processing_exception(self, client, mock_db):
        """文档处理过程中抛出一般异常，返回 INTERNAL_ERROR。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.upload_and_process = AsyncMock(
                side_effect=RuntimeError("解析内部错误")
            )
            mock_service_cls.return_value = mock_service

            response = await client.post(
                "/api/documents/upload",
                files=[("files", ("test.txt", b"content", "text/plain"))],
            )

        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["failed"]) == 1
        assert data["data"]["failed"][0]["code"] == "INTERNAL_ERROR"


# ===== 文档统计端点测试 =====


class TestDocumentStatsIntegration:
    """文档统计端点集成测试，对应 TC-VEC-005。"""

    @pytest.mark.asyncio
    async def test_get_document_stats(self, client, mock_db):
        """TC-VEC-005: 获取知识库统计信息。"""
        with patch("app.api.documents.DocumentService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_stats = AsyncMock(
                return_value={
                    "total_documents": 10,
                    "total_chunks": 150,
                    "embedding_provider": "openai",
                    "vector_dimension": 1536,
                }
            )
            mock_service_cls.return_value = mock_service

            response = await client.get("/api/documents/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_documents"] == 10
        assert data["data"]["total_chunks"] == 150
        assert data["data"]["embedding_provider"] == "openai"
        assert data["data"]["vector_dimension"] == 1536


# ===== 会话消息列表集成测试（补充成功流程）=====


class TestSessionMessagesIntegration:
    """会话消息列表集成测试，对应 TC-HIS-003。"""

    @pytest.mark.asyncio
    async def test_get_session_messages_success(self, client, mock_db):
        """TC-HIS-003: 获取会话历史消息成功。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            # mock session 存在
            session = MagicMock()
            session.id = uuid.uuid4()
            # mock 消息列表
            msg1 = MagicMock()
            msg1.to_dict.return_value = {
                "id": str(uuid.uuid4()),
                "session_id": str(session.id),
                "role": "user",
                "content": "什么是 RAG？",
                "references": None,
                "elapsed_ms": None,
                "created_at": "2026-07-12T12:00:00",
            }
            msg2 = MagicMock()
            msg2.to_dict.return_value = {
                "id": str(uuid.uuid4()),
                "session_id": str(session.id),
                "role": "assistant",
                "content": "RAG 是检索增强生成。",
                "references": [{"doc_name": "test.pdf", "chunk": "..."}],
                "elapsed_ms": 1200,
                "created_at": "2026-07-12T12:00:01",
            }
            mock_service = MagicMock()
            mock_service.get_session = AsyncMock(return_value=session)
            mock_service.list_messages = AsyncMock(return_value=[msg1, msg2])
            mock_service_cls.return_value = mock_service

            response = await client.get(
                f"/api/chat/sessions/{session.id}/messages"
            )

        assert response.status_code == 200
        data = response.json()
        messages = data["data"]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["elapsed_ms"] == 1200


# ===== SSE 流式问答集成测试（补充 app/api/chat.py 覆盖）=====


def _make_stream_db():
    """构造流式会话使用的 mock 数据库。"""
    stream_db = MagicMock()
    stream_db.commit = AsyncMock()
    stream_db.rollback = AsyncMock()
    return stream_db


def _make_message_mock(msg_id=None):
    """构造含 id 属性的 message mock。"""
    message = MagicMock()
    message.id = msg_id or uuid.uuid4()
    return message


async def _mock_answer_chunks(contents):
    """构造 mock 的 answer_chunks 异步迭代器。"""
    for i, content in enumerate(contents):
        is_last = i == len(contents) - 1
        yield ChatChunk(content=content, finish_reason="stop" if is_last else None)


class TestSSEChatIntegration:
    """SSE 流式问答端点集成测试，对应 TC-RAG-001~003。"""

    @pytest.mark.asyncio
    async def test_sse_chat_success(self, client, mock_db):
        """TC-RAG-001: 正常流式问答，验证 references → token × N → done 事件序列。"""
        session = MagicMock()
        session.id = uuid.uuid4()
        references = [
            {
                "doc_id": "doc-1",
                "doc_name": "test.pdf",
                "chunk_index": 0,
                "source_path": "uploads/test.pdf",
                "chunk": "RAG 是检索增强生成...",
                "similarity": 0.85,
            }
        ]
        rag_result = RAGStreamResult(
            references=references,
            answer_chunks=_mock_answer_chunks(["这是", "回答", "。"]),
        )
        stream_db = _make_stream_db()
        message = _make_message_mock()

        @asynccontextmanager
        async def mock_factory():
            yield stream_db

        with (
            patch("app.api.chat.ChatService") as mock_chat_cls,
            patch("app.api.chat.get_session_factory", return_value=mock_factory),
            patch("app.api.chat.RAGService") as mock_rag_cls,
        ):
            mock_chat = MagicMock()
            mock_chat.get_session = AsyncMock(return_value=session)
            mock_chat.save_message = AsyncMock(return_value=message)
            mock_chat_cls.return_value = mock_chat

            mock_rag = MagicMock()
            mock_rag.answer = AsyncMock(return_value=rag_result)
            mock_rag_cls.return_value = mock_rag

            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(session.id),
                    "question": "什么是 RAG？",
                },
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # 解析 SSE 事件流
        text = response.text
        events = self._parse_sse_events(text)
        event_types = [e["event"] for e in events]

        # 验证事件顺序: references 在 token 之前，done 在最后
        assert "references" in event_types
        assert "done" in event_types
        assert event_types.index("references") < event_types.index("done")
        token_count = event_types.count("token")
        assert token_count == 3  # "这是" + "回答" + "。"

        # 验证 references 事件在所有 token 之前
        first_token_idx = event_types.index("token")
        assert event_types.index("references") < first_token_idx

        # 验证 done 事件在所有 token 之后
        last_token_idx = len(event_types) - 1 - event_types[::-1].index("token")
        assert event_types.index("done") > last_token_idx

        # 验证 references 内容
        ref_event = next(e for e in events if e["event"] == "references")
        assert len(ref_event["data"]) == 1
        assert ref_event["data"][0]["doc_name"] == "test.pdf"

        # 验证 done 事件含 message_id 与 elapsed_ms
        done_event = next(e for e in events if e["event"] == "done")
        assert "message_id" in done_event["data"]
        assert "elapsed_ms" in done_event["data"]

    @pytest.mark.asyncio
    async def test_sse_chat_no_references(self, client, mock_db):
        """TC-RAG-003: 无相关内容时 references 为空，但仍发送 done。"""
        session = MagicMock()
        session.id = uuid.uuid4()
        rag_result = RAGStreamResult(
            references=[],
            answer_chunks=_mock_answer_chunks(["未在文档库中找到相关内容。"]),
        )
        stream_db = _make_stream_db()
        message = _make_message_mock()

        @asynccontextmanager
        async def mock_factory():
            yield stream_db

        with (
            patch("app.api.chat.ChatService") as mock_chat_cls,
            patch("app.api.chat.get_session_factory", return_value=mock_factory),
            patch("app.api.chat.RAGService") as mock_rag_cls,
        ):
            mock_chat = MagicMock()
            mock_chat.get_session = AsyncMock(return_value=session)
            mock_chat.save_message = AsyncMock(return_value=message)
            mock_chat_cls.return_value = mock_chat

            mock_rag = MagicMock()
            mock_rag.answer = AsyncMock(return_value=rag_result)
            mock_rag_cls.return_value = mock_rag

            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(session.id),
                    "question": "一个无关的问题",
                },
            )

        assert response.status_code == 200
        events = self._parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        # references 事件存在但数据为空列表
        assert "references" in event_types
        ref_event = next(e for e in events if e["event"] == "references")
        assert ref_event["data"] == []
        # 仍有 token 与 done 事件
        assert event_types.count("token") >= 1
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_sse_chat_llm_error(self, client, mock_db):
        """TC-RAG-006: LLM 流式过程中出错，发送 error 事件。"""
        session = MagicMock()
        session.id = uuid.uuid4()
        # answer 方法直接抛出异常（模拟 LLM 超时）
        stream_db = _make_stream_db()
        message = _make_message_mock()

        @asynccontextmanager
        async def mock_factory():
            yield stream_db

        with (
            patch("app.api.chat.ChatService") as mock_chat_cls,
            patch("app.api.chat.get_session_factory", return_value=mock_factory),
            patch("app.api.chat.RAGService") as mock_rag_cls,
        ):
            mock_chat = MagicMock()
            mock_chat.get_session = AsyncMock(return_value=session)
            mock_chat.save_message = AsyncMock(return_value=message)
            mock_chat_cls.return_value = mock_chat

            mock_rag = MagicMock()
            mock_rag.answer = AsyncMock(
                side_effect=TimeoutError("LLM 调用超时（30s）")
            )
            mock_rag_cls.return_value = mock_rag

            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(session.id),
                    "question": "测试超时",
                },
            )

        assert response.status_code == 200
        events = self._parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        # 应该有 error 事件
        assert "error" in event_types
        error_event = next(e for e in events if e["event"] == "error")
        assert "message" in error_event["data"]
        assert "code" in error_event["data"]
        # 超时错误应分类为 LLM_TIMEOUT
        assert error_event["data"]["code"] == "LLM_TIMEOUT"

    @pytest.mark.asyncio
    async def test_sse_chat_connection_error_classification(self, client, mock_db):
        """EX-005: 连接错误分类为 LLM_CONNECTION_ERROR。"""
        session = MagicMock()
        session.id = uuid.uuid4()
        stream_db = _make_stream_db()
        message = _make_message_mock()

        @asynccontextmanager
        async def mock_factory():
            yield stream_db

        with (
            patch("app.api.chat.ChatService") as mock_chat_cls,
            patch("app.api.chat.get_session_factory", return_value=mock_factory),
            patch("app.api.chat.RAGService") as mock_rag_cls,
        ):
            mock_chat = MagicMock()
            mock_chat.get_session = AsyncMock(return_value=session)
            mock_chat.save_message = AsyncMock(return_value=message)
            mock_chat_cls.return_value = mock_chat

            mock_rag = MagicMock()
            mock_rag.answer = AsyncMock(
                side_effect=ConnectionError("network connection failed")
            )
            mock_rag_cls.return_value = mock_rag

            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(session.id),
                    "question": "测试连接错误",
                },
            )

        assert response.status_code == 200
        events = self._parse_sse_events(response.text)
        error_event = next(e for e in events if e["event"] == "error")
        assert error_event["data"]["code"] == "LLM_CONNECTION_ERROR"

    @staticmethod
    def _parse_sse_events(text: str) -> list[dict]:
        """解析 SSE 事件流文本为事件列表。

        Args:
            text: SSE 原始文本

        Returns:
            事件字典列表，每个含 event 与 data 字段
        """
        import json

        events = []
        # SSE 事件以空行分隔
        blocks = text.split("\n\n")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            event_type = None
            data_str = ""
            for line in block.split("\n"):
                if line.startswith("event: "):
                    event_type = line[len("event: "):]
                elif line.startswith("data: "):
                    data_str = line[len("data: "):]
            if event_type:
                try:
                    data = json.loads(data_str)
                except (json.JSONDecodeError, ValueError):
                    data = data_str
                events.append({"event": event_type, "data": data})
        return events


# ===== 边界测试补充 =====


class TestBoundaryIntegration:
    """边界场景集成测试，对应 BC 系列。"""

    @pytest.mark.asyncio
    async def test_question_max_length(self, client, mock_db):
        """BC-009: 问题长度达到上限 2000 字符仍可接受。"""
        session = MagicMock()
        session.id = uuid.uuid4()
        stream_db = _make_stream_db()
        message = _make_message_mock()

        @asynccontextmanager
        async def mock_factory():
            yield stream_db

        rag_result = RAGStreamResult(
            references=[],
            answer_chunks=_mock_answer_chunks(["ok"]),
        )

        with (
            patch("app.api.chat.ChatService") as mock_chat_cls,
            patch("app.api.chat.get_session_factory", return_value=mock_factory),
            patch("app.api.chat.RAGService") as mock_rag_cls,
        ):
            mock_chat = MagicMock()
            mock_chat.get_session = AsyncMock(return_value=session)
            mock_chat.save_message = AsyncMock(return_value=message)
            mock_chat_cls.return_value = mock_chat

            mock_rag = MagicMock()
            mock_rag.answer = AsyncMock(return_value=rag_result)
            mock_rag_cls.return_value = mock_rag

            # 恰好 2000 字符（上限）
            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(session.id),
                    "question": "问" * 2000,
                },
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_question_exceeds_max_length(self, client):
        """BC-009: 问题长度超过 2000 字符返回 422。"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "session_id": str(uuid.uuid4()),
                "question": "问" * 2001,
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_question_whitespace_only(self, client):
        """BC-008: 仅含空白的问题返回 422（field_validator 拦截）。"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "session_id": str(uuid.uuid4()),
                "question": "   ",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_documents_invalid_size(self, client):
        """BC-010: size 参数超过 100 返回 422（le=100 约束）。"""
        response = await client.get("/api/documents?size=1000")
        assert response.status_code == 422
