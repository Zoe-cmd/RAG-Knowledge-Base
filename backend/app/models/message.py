"""
ChatMessage 数据模型。

存储会话中的每条消息。
对应数据库表: chat_messages

注意:
- references 是 MariaDB 保留字，SQL 中须用反引号转义。
  SQLAlchemy 模型中通过 Column("references", JSON) 显式映射列名。
- 此表不使用软删除与 updated_at（消息不可修改）。
- 删除会话时由业务层物理删除该会话的所有消息。
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, GUID


class ChatMessage(Base):
    """聊天消息模型。

    user 消息包含 content；assistant 消息额外包含
    references（引用来源 JSON）与 elapsed_ms（流式生成耗时）。

    多轮上下文查询通过 (session_id, created_at) 复合索引
    快速获取最近 N 条消息（DEC-011: 最近 4 轮 = 8 条消息）。
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="消息唯一标识符（UUID）",
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话 ID，关联 chat_sessions.id",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="消息角色：user/assistant",
    )
    content: Mapped[str] = mapped_column(
        Text(length=16777215),  # MEDIUMTEXT
        nullable=False,
        comment="消息内容（user 为问题，assistant 为回答）",
    )
    # references 是 MariaDB 保留字，显式映射列名
    references: Mapped[list[dict[str, Any]] | None] = mapped_column(
        "references",
        JSON,
        nullable=True,
        default=None,
        comment="引用来源（仅 assistant，JSON 数组）",
    )
    elapsed_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="流式生成耗时（毫秒，仅 assistant）",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default="CURRENT_TIMESTAMP(3)",
        comment="创建时间（UTC）",
    )

    def __repr__(self) -> str:
        return (
            f"<ChatMessage(id={self.id}, session_id={self.session_id}, "
            f"role={self.role!r})>"
        )

    def to_dict(self) -> dict:
        """转换为字典（用于 API 响应）。"""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "references": self.references,
            "elapsed_ms": self.elapsed_ms,
            "created_at": self.created_at.isoformat() + "Z"
            if self.created_at
            else None,
        }
