"""
API 端点单元测试。

使用 httpx AsyncClient 测试 FastAPI 端点。
通过 dependency_overrides 与 patch 隔离外部依赖。
client 与 mock_db 夹具定义在 conftest.py 中。
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database.session import get_db
from app.main import app


# ===== 健康检查测试 =====


class TestHealthCheck:
    """健康检查端点测试。"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """健康检查返回 200。"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ===== 文档 API 测试 =====


class TestDocumentsAPI:
    """文档 API 端点测试。"""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client, mock_db):
        """空文档列表。"""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        response = await client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"] == []
        assert "meta" in data
        assert "pagination" in data["meta"]

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client, mock_db):
        """文档列表分页参数。"""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        result_mock.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=result_mock)

        response = await client.get("/api/documents?page=2&size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["pagination"]["page"] == 2
        assert data["meta"]["pagination"]["size"] == 10

    @pytest.mark.asyncio
    async def test_list_documents_invalid_page(self, client):
        """无效页码返回 422。"""
        response = await client.get("/api/documents?page=0")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_no_files(self, client):
        """上传无文件返回 422（FastAPI 必填字段验证）。"""
        response = await client.post("/api/documents/upload")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client, mock_db):
        """删除不存在的文档返回 404。"""
        with patch(
            "app.api.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_document = AsyncMock(return_value=False)
            mock_service_cls.return_value = mock_service

            response = await client.delete(
                f"/api/documents/{uuid.uuid4()}"
            )
            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_document_success(self, client, mock_db):
        """删除文档成功返回 204。"""
        with patch(
            "app.api.documents.DocumentService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_document = AsyncMock(return_value=True)
            mock_service_cls.return_value = mock_service

            response = await client.delete(
                f"/api/documents/{uuid.uuid4()}"
            )
            assert response.status_code == 204


# ===== 会话 API 测试 =====


class TestSessionsAPI:
    """会话 API 端点测试。"""

    @pytest.mark.asyncio
    async def test_create_session(self, client, mock_db):
        """创建会话。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            from app.models.session import ChatSession

            session = ChatSession(id=uuid.uuid4(), title="新会话")
            mock_service = MagicMock()
            mock_service.create_session = AsyncMock(return_value=session)
            mock_service_cls.return_value = mock_service

            response = await client.post(
                "/api/chat/sessions", json={"title": "新会话"}
            )
            assert response.status_code == 201
            data = response.json()
            assert "data" in data
            assert data["data"]["title"] == "新会话"

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, mock_db):
        """获取会话列表。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            from app.models.session import ChatSession

            sessions = [ChatSession(id=uuid.uuid4(), title="会话1")]
            mock_service = MagicMock()
            mock_service.list_sessions = AsyncMock(return_value=sessions)
            mock_service_cls.return_value = mock_service

            response = await client.get("/api/chat/sessions")
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client, mock_db):
        """删除不存在的会话返回 404。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_session = AsyncMock(return_value=False)
            mock_service_cls.return_value = mock_service

            response = await client.delete(
                f"/api/chat/sessions/{uuid.uuid4()}"
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_all_sessions(self, client, mock_db):
        """清空所有会话。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.delete_all_sessions = AsyncMock(return_value=3)
            mock_service_cls.return_value = mock_service

            response = await client.delete("/api/chat/sessions")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["deleted_count"] == 3

    @pytest.mark.asyncio
    async def test_get_session_messages_not_found(self, client, mock_db):
        """获取不存在的会话消息返回 404。"""
        with patch("app.api.sessions.ChatService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_session = AsyncMock(return_value=None)
            mock_service_cls.return_value = mock_service

            response = await client.get(
                f"/api/chat/sessions/{uuid.uuid4()}/messages"
            )
            assert response.status_code == 404


# ===== 聊天 API 测试 =====


class TestChatAPI:
    """聊天消息 API 端点测试。"""

    @pytest.mark.asyncio
    async def test_send_message_invalid_uuid(self, client):
        """无效 session_id 返回 422。"""
        response = await client.post(
            "/api/chat/messages",
            json={"session_id": "not-uuid", "question": "问题"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_message_empty_question(self, client):
        """空问题返回 422。"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "session_id": str(uuid.uuid4()),
                "question": "",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, client, mock_db):
        """会话不存在返回 404。"""
        with patch("app.api.chat.ChatService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_session = AsyncMock(return_value=None)
            mock_service_cls.return_value = mock_service

            response = await client.post(
                "/api/chat/messages",
                json={
                    "session_id": str(uuid.uuid4()),
                    "question": "什么是 RAG？",
                },
            )
            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "SESSION_NOT_FOUND"


# ===== 配置 API 测试 =====


class TestConfigAPI:
    """配置 API 端点测试。"""

    @pytest.mark.asyncio
    async def test_get_config(self, client, mock_db):
        """获取配置。"""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)

        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "embedding_provider" in data["data"]
        assert "llm_model" in data["data"]
        assert "statistics" in data["data"]

    @pytest.mark.asyncio
    async def test_switch_provider_invalid(self, client):
        """无效 provider 返回 422。"""
        response = await client.put(
            "/api/config/embedding-provider",
            json={"provider": "invalid"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_switch_provider_same(self, client, mock_db):
        """切换为相同 provider。"""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 0
        mock_db.execute = AsyncMock(return_value=result_mock)

        response = await client.put(
            "/api/config/embedding-provider",
            json={"provider": "openai"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["needs_reindex"] is False

    @pytest.mark.asyncio
    async def test_switch_provider_different(self, client, mock_db):
        """切换为不同 provider。"""
        result_mock = MagicMock()
        result_mock.scalar_one.return_value = 5
        mock_db.execute = AsyncMock(return_value=result_mock)

        response = await client.put(
            "/api/config/embedding-provider",
            json={"provider": "bge"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["needs_reindex"] is True
        assert data["data"]["current_provider"] == "bge"
        assert data["data"]["documents_to_reindex"] == 5


# ===== 错误处理测试 =====


class TestErrorHandling:
    """错误处理测试。"""

    @pytest.mark.asyncio
    async def test_404_unknown_route(self, client):
        """未知路由返回标准错误格式。"""
        response = await client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "meta" in data
        assert "requestId" in data["meta"]

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self, client):
        """OpenAPI 文档可用。"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "AI 文档知识库 API"
