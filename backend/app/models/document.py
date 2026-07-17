"""
Document 数据模型。

存储上传文档的元数据信息。
对应数据库表: documents
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, GUID, SoftDeleteMixin, TimestampMixin


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """文档元数据模型。

    存储上传文档的文件名、类型、大小、处理状态等信息。
    文档上传后由 DocumentService 解析、切分、向量化，
    状态从 pending 流转为 processing → completed（或 failed）。
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="文档唯一标识符（UUID）",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="原始文件名（含扩展名）",
    )
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="文件类型：pdf/docx/md/txt",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="文件大小（字节）",
    )
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="存储路径（相对路径）",
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment="文件内容 SHA-256 哈希（去重检测）",
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="文本切片数量",
    )
    chunk_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=500,
        comment="切片大小（字符数）",
    )
    chunk_overlap: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        comment="切片重叠（字符数）",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="处理状态：pending/processing/completed/failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="错误信息（status=failed 时记录）",
    )
    embedding_provider: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
        comment="使用的 Embedding Provider：openai/bge",
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, filename={self.filename!r}, "
            f"status={self.status!r})>"
        )

    def to_dict(self, include_deleted: bool = False) -> dict:
        """转换为字典（用于 API 响应）。

        Args:
            include_deleted: 是否包含 deleted_at 字段

        Returns:
            文档信息的字典表示
        """
        data = {
            "id": str(self.id),
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "embedding_provider": self.embedding_provider,
            "created_at": self.created_at.isoformat() + "Z"
            if self.created_at
            else None,
            "updated_at": self.updated_at.isoformat() + "Z"
            if self.updated_at
            else None,
        }
        if include_deleted:
            data["deleted_at"] = (
                self.deleted_at.isoformat() + "Z"
                if self.deleted_at
                else None
            )
        return data
