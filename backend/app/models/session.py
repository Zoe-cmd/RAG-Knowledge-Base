"""
ChatSession 数据模型。

存储聊天会话信息。
对应数据库表: chat_sessions
"""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, GUID, SoftDeleteMixin, TimestampMixin


class ChatSession(Base, TimestampMixin, SoftDeleteMixin):
    """聊天会话模型。

    每个会话包含标题、消息数量、最后消息时间等。
    用户新建会话后可在其中进行多轮问答。
    删除会话时软删除此表记录，业务层同步物理删除关联消息。
    """

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="会话唯一标识符（UUID）",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="新会话",
        comment="会话标题",
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="消息数量（含 user 与 assistant）",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        default=None,
        comment="最后一条消息时间",
    )

    def __repr__(self) -> str:
        return (
            f"<ChatSession(id={self.id}, title={self.title!r}, "
            f"message_count={self.message_count})>"
        )

    def to_dict(self) -> dict:
        """转换为字典（用于 API 响应）。"""
        return {
            "id": str(self.id),
            "title": self.title,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() + "Z"
            if self.last_message_at
            else None,
            "created_at": self.created_at.isoformat() + "Z"
            if self.created_at
            else None,
        }
