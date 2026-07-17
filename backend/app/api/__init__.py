"""
API 路由层包。

提供 FastAPI 路由模块:
- documents: 文档管理（上传/列表/删除/统计）
- sessions: 聊天会话 CRUD
- chat: 聊天消息（SSE 流式问答）
- config: 配置管理
"""

from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.documents import router as documents_router
from app.api.sessions import router as sessions_router

__all__ = [
    "documents_router",
    "sessions_router",
    "chat_router",
    "config_router",
]
