"""
SQLAlchemy 模型基类。

定义 declarative base 与公共 mixin（审计字段、软删除）。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """UUID 类型适配器。

    MariaDB 无原生 UUID 类型，使用 CHAR(36) 存储。
    Python 端使用 uuid.UUID 对象，数据库端为 CHAR(36) 字符串。
    """

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Python → DB：UUID 对象转字符串。"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        """DB → Python：字符串转 UUID 对象。"""
        if value is None:
            return None
        return uuid.UUID(value)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base。"""


class TimestampMixin:
    """审计字段 mixin：created_at 与 updated_at。

    所有需要审计的表（documents、chat_sessions）使用此 mixin。
    chat_messages 不使用（消息不可修改，无需 updated_at）。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.current_timestamp(),
        nullable=False,
        comment="创建时间（UTC）",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
        comment="更新时间（UTC）",
    )


class SoftDeleteMixin:
    """软删除 mixin：deleted_at 字段。

    NULL 表示未删除，非 NULL 表示已软删除（值为删除时间）。
    所有查询须显式过滤 `deleted_at IS NULL`。
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        default=None,
        comment="软删除时间，NULL 表示未删除",
    )
