"""
聊天会话 API 路由。

提供会话 CRUD 与会话消息列表接口。
对应 api-spec.md 第 4.2 节。

端点:
- POST   /api/chat/sessions            新建会话
- GET    /api/chat/sessions            会话列表
- DELETE /api/chat/sessions/{id}       删除单个会话
- DELETE /api/chat/sessions            清空所有会话
- GET    /api/chat/sessions/{id}/messages  会话消息列表
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.chat_service import ChatService
from app.utils.exceptions import SessionNotFoundError
from app.utils.response import success_response

router = APIRouter(prefix="/sessions", tags=["聊天会话"])


class CreateSessionRequest(BaseModel):
    """新建会话请求体。"""

    title: str = Field(default="新会话", max_length=255, description="会话标题")


@router.post("", status_code=201)
async def create_session(
    request: CreateSessionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """新建会话。

    Returns:
        创建的会话信息
    """
    title = request.title if request else "新会话"
    service = ChatService(db)
    session = await service.create_session(title=title)
    return success_response(data=session.to_dict())


@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
):
    """获取会话列表。

    按最后消息时间倒序（NULL 在后），最多返回 50 条。

    Returns:
        会话列表
    """
    service = ChatService(db)
    sessions = await service.list_sessions(limit=50)
    return success_response(data=[s.to_dict() for s in sessions])


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除单个会话及其所有消息。

    物理删除消息，软删除会话。

    Returns:
        204 No Content
    """
    service = ChatService(db)
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise SessionNotFoundError()


@router.delete("")
async def delete_all_sessions(
    db: AsyncSession = Depends(get_db),
):
    """清空所有会话及其消息。

    物理删除所有消息，软删除所有会话。

    Returns:
        删除的会话数量
    """
    service = ChatService(db)
    count = await service.delete_all_sessions()
    return success_response(data={"deleted_count": count})


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """获取会话所有消息（按时间正序）。

    Returns:
        会话消息列表
    """
    service = ChatService(db)

    # 校验会话存在
    session = await service.get_session(session_id)
    if session is None:
        raise SessionNotFoundError()

    messages = await service.list_messages(session_id)
    return success_response(
        data={"messages": [m.to_dict() for m in messages]}
    )
