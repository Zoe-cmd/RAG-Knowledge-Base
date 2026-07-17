"""
聊天会话与消息服务。

管理会话 CRUD、消息持久化、多轮上下文查询（DEC-011）。

多轮上下文策略:
- 保留最近 4 轮（8 条消息），更早的丢弃
- 查询: WHERE session_id=? ORDER BY created_at DESC LIMIT 8，应用层反转
- 会话级隔离，不同会话上下文独立
"""

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.message import ChatMessage
from app.models.session import ChatSession
from app.providers.llm.base import Message
from app.services.prompt_template import build_rag_messages


class ChatService:
    """聊天会话与消息服务。

    提供:
    - 会话 CRUD（创建、列表、删除、清空）
    - 消息持久化（user 与 assistant）
    - 多轮上下文查询（最近 4 轮 = 8 条消息）
    - RAG 消息组装（system + context + history + question）
    """

    def __init__(self, db: AsyncSession) -> None:
        """初始化 ChatService。

        Args:
            db: 异步数据库会话
        """
        self._db = db
        self._settings = get_settings()

    # ===== 会话管理 =====

    async def create_session(self, title: str = "新会话") -> ChatSession:
        """创建新会话。

        Args:
            title: 会话标题，默认"新会话"

        Returns:
            创建的 ChatSession 实例
        """
        session = ChatSession(
            id=uuid.uuid4(),
            title=title,
            message_count=0,
        )
        self._db.add(session)
        await self._db.flush()
        return session

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        """获取会话（不含已软删除）。

        Args:
            session_id: 会话 ID

        Returns:
            ChatSession 实例，不存在或已删除返回 None
        """
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 50) -> List[ChatSession]:
        """获取会话列表。

        排序: 最后消息时间倒序（NULL 在后）。
        软删除的会话不返回。

        Args:
            limit: 返回数量上限，默认 50

        Returns:
            ChatSession 列表
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.deleted_at.is_(None))
            .order_by(
                ChatSession.last_message_at.is_(None),
                ChatSession.last_message_at.desc(),
            )
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        """删除会话（软删除 + 物理删除消息）。

        业务层软删除会话（UPDATE deleted_at），
        同时物理删除该会话的所有消息（CASCADE 安全网）。

        Args:
            session_id: 会话 ID

        Returns:
            是否删除成功（会话不存在返回 False）
        """
        session = await self.get_session(session_id)
        if session is None:
            return False

        # 软删除会话
        session.deleted_at = datetime.now(timezone.utc)

        # 物理删除该会话的所有消息
        await self._db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        await self._db.flush()
        return True

    async def delete_all_sessions(self) -> int:
        """清空所有会话（软删除 + 物理删除消息）。

        Returns:
            删除的会话数量
        """
        # 查询所有未删除的会话
        stmt = select(ChatSession).where(ChatSession.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        sessions = list(result.scalars().all())

        if not sessions:
            return 0

        now = datetime.now(timezone.utc)
        session_ids = [s.id for s in sessions]

        # 软删除会话
        for s in sessions:
            s.deleted_at = now

        # 物理删除这些会话的消息
        await self._db.execute(
            delete(ChatMessage).where(
                ChatMessage.session_id.in_(session_ids)
            )
        )
        await self._db.flush()
        return len(sessions)

    # ===== 消息管理 =====

    async def save_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        references: list[dict] | None = None,
        elapsed_ms: int | None = None,
    ) -> ChatMessage:
        """保存消息并更新会话统计。

        Args:
            session_id: 会话 ID
            role: 消息角色（user/assistant）
            content: 消息内容
            references: 引用来源（仅 assistant）
            elapsed_ms: 流式生成耗时毫秒（仅 assistant）

        Returns:
            创建的 ChatMessage 实例

        Raises:
            ValueError: 会话不存在
        """
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"会话不存在: {session_id}")

        message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            references=references,
            elapsed_ms=elapsed_ms,
        )
        self._db.add(message)

        # 更新会话统计
        session.message_count += 1
        session.last_message_at = datetime.now(timezone.utc)

        # 首条用户消息时，用问题内容更新会话标题
        if role == "user" and session.title == "新会话":
            session.title = content[:30] + ("..." if len(content) > 30 else "")

        await self._db.flush()
        return message

    async def list_messages(
        self, session_id: uuid.UUID
    ) -> List[ChatMessage]:
        """获取会话所有消息（按时间正序）。

        Args:
            session_id: 会话 ID

        Returns:
            ChatMessage 列表（按 created_at 升序）
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_history(
        self, session_id: uuid.UUID
    ) -> List[Message]:
        """获取最近 4 轮对话历史（DEC-011）。

        查询最近 8 条消息（4 轮 user+assistant），
        应用层反转为时间正序，转换为 LLM Message 格式。

        Args:
            session_id: 会话 ID

        Returns:
            历史消息列表（时间正序），最多 8 条
        """
        limit = self._settings.MAX_HISTORY_ROUNDS * 2  # 4 轮 = 8 条
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        messages = list(result.scalars().all())

        # 反转为时间正序
        messages.reverse()

        # 转换为 LLM Message 格式（仅 role 与 content）
        return [
            Message(role=msg.role, content=msg.content) for msg in messages
        ]

    async def get_message_count(self, session_id: uuid.UUID) -> int:
        """统计会话消息数量。

        Args:
            session_id: 会话 ID

        Returns:
            消息数量
        """
        stmt = select(func.count()).select_from(ChatMessage).where(
            ChatMessage.session_id == session_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    def build_rag_messages(
        self,
        question: str,
        context_chunks: List[str],
        history: List[Message],
    ) -> List[Message]:
        """组装 RAG 消息列表（委托给 prompt_template）。

        Args:
            question: 当前用户问题
            context_chunks: 检索到的文档片段
            history: 历史消息列表

        Returns:
            组装后的 Message 列表
        """
        return build_rag_messages(question, context_chunks, history)
