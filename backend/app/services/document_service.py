"""
文档管理服务。

实现文档处理全流水线: 上传 → 解析 → 切分 → 向量化 → Chroma 存储 → MariaDB 元数据。
同时提供文档列表、删除（同步清理 Chroma 向量与文件）、去重检测。

状态流转: pending → processing → completed（或 failed）
"""

import asyncio
import hashlib
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.chunkers.recursive_chunker import RecursiveChunker
from app.models.document import Document
from app.parsers.factory import parse_document
from app.parsers.pdf_parser import ScannedPDFError
from app.services.chroma_client import get_chroma_client
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class DocumentService:
    """文档管理服务。

    提供:
    - 文档上传与处理（解析→切分→向量化→存储）
    - 文档列表（分页）
    - 文档删除（同步清理 Chroma 向量与文件）
    - 去重检测（SHA-256 内容哈希）
    - 文档数量统计

    所有 Chroma 同步操作通过 asyncio.to_thread 包装为异步，
    避免阻塞事件循环。
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """初始化 DocumentService。

        Args:
            db: 异步数据库会话
            embedding_service: Embedding 服务实例，None 时自动创建
        """
        self._db = db
        self._settings = get_settings()
        self._embedding_service = embedding_service or EmbeddingService()
        self._chunker = RecursiveChunker()
        self._chroma = get_chroma_client()

    # ===== 文档上传与处理 =====

    async def upload_and_process(
        self,
        file_path: Path,
        filename: str,
        file_type: str,
        file_size: int,
    ) -> Document:
        """上传并处理文档（同步处理，MVP 简化方案）。

        流水线:
        1. 校验文件类型与大小
        2. 计算内容哈希（去重检测）
        3. 创建 Document 记录（status=pending）
        4. 保存文件到上传目录
        5. 解析文档为纯文本
        6. 递归切分文本
        7. 批量向量化
        8. 存入 Chroma
        9. 更新 Document 状态为 completed

        任一步骤失败则更新 status=failed 并记录 error_message。

        Args:
            file_path: 临时文件路径（上传的临时文件）
            filename: 原始文件名
            file_type: 文件类型（扩展名，不含点）
            file_size: 文件大小（字节）

        Returns:
            处理后的 Document 实例（状态为 completed 或 failed）

        Raises:
            ValueError: 文件类型不支持或大小超限
            ScannedPDFError: PDF 为扫描件
        """
        # 1. 校验
        self._validate_file(file_type, file_size)

        # 2. 校验文档总数上限
        await self._check_document_limit()

        # 3. 计算内容哈希
        content_hash = await asyncio.to_thread(
            self._compute_hash, file_path
        )

        # 4. 去重检测
        existing = await self._find_by_hash(content_hash)
        if existing is not None:
            logger.info("文档已存在（哈希去重）: %s", filename)
            # 删除临时文件
            await asyncio.to_thread(file_path.unlink, missing_ok=True)
            return existing

        # 5. 创建 Document 记录
        doc_id = uuid.uuid4()
        stored_filename = f"{doc_id}.{file_type}"
        stored_path = self._settings.upload_dir_path / stored_filename

        document = Document(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_path=str(stored_path.relative_to(Path.cwd()))
            if str(stored_path).startswith(str(Path.cwd()))
            else str(stored_path),
            content_hash=content_hash,
            chunk_count=0,
            chunk_size=self._settings.CHUNK_SIZE,
            chunk_overlap=self._settings.CHUNK_OVERLAP,
            status="pending",
            embedding_provider=self._embedding_service.name,
        )
        self._db.add(document)
        await self._db.flush()

        # 6. 保存文件到上传目录
        await asyncio.to_thread(
            shutil.copy2, str(file_path), str(stored_path)
        )
        # 删除临时文件
        await asyncio.to_thread(file_path.unlink, missing_ok=True)

        # 7. 处理文档（解析→切分→向量化→存储）
        await self._process_document(document, stored_path)

        # 刷新文档对象，确保数据库自动更新的字段（如 updated_at）
        # 已加载到内存，避免 to_dict() 序列化时在异步上下文中触发
        # 同步懒加载导致 MissingGreenlet 异常（修复 BUG-010）
        await self._db.refresh(document)

        return document

    async def _process_document(
        self, document: Document, file_path: Path
    ) -> None:
        """处理文档核心流水线。

        Args:
            document: Document 实例
            file_path: 文件存储路径
        """
        try:
            # 更新状态为 processing
            document.status = "processing"
            await self._db.flush()

            # 1. 解析文档
            logger.info("解析文档: %s", document.filename)
            text = await asyncio.to_thread(
                parse_document, file_path, document.file_type
            )

            if not text or not text.strip():
                raise ValueError("文档解析结果为空")

            # 2. 切分文本
            is_markdown = document.file_type == "md"
            chunks = self._chunker.chunk(text, is_markdown=is_markdown)
            if not chunks:
                raise ValueError("文本切分结果为空")

            logger.info(
                "文档切分完成: %s，共 %d 个切片",
                document.filename,
                len(chunks),
            )

            # 3. 向量化
            embeddings = await self._embedding_service.embed_documents(
                chunks
            )
            if len(embeddings) != len(chunks):
                raise ValueError(
                    f"向量化数量不匹配: 期望 {len(chunks)}，"
                    f"实际 {len(embeddings)}"
                )

            # 4. 存入 Chroma
            await asyncio.to_thread(
                self._chroma.add_vectors,
                self._embedding_service.provider,
                str(document.id),
                document.filename,
                document.file_path,
                chunks,
                embeddings,
            )

            # 5. 更新 Document 状态
            document.chunk_count = len(chunks)
            document.status = "completed"
            document.error_message = None
            await self._db.flush()

            logger.info(
                "文档处理完成: %s，切片数=%d",
                document.filename,
                len(chunks),
            )

        except ScannedPDFError:
            # 扫描件特殊处理
            document.status = "failed"
            document.error_message = "该 PDF 为扫描件，MVP 暂不支持，需 OCR"
            await self._db.flush()
            logger.warning("扫描件 PDF 不支持: %s", document.filename)
            raise

        except Exception as e:
            # 其他错误
            document.status = "failed"
            document.error_message = str(e)[:500]
            await self._db.flush()
            logger.error(
                "文档处理失败: %s，错误: %s", document.filename, e
            )
            raise

    # ===== 文档列表 =====

    async def list_documents(
        self, page: int = 1, page_size: int = 20
    ) -> dict:
        """获取文档列表（分页）。

        Args:
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            包含 items、total、page、page_size 的字典
        """
        offset = (page - 1) * page_size

        # 查询总数
        count_stmt = select(func.count()).select_from(Document).where(
            Document.deleted_at.is_(None)
        )
        total = (await self._db.execute(count_stmt)).scalar_one()

        # 查询当前页
        stmt = (
            select(Document)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self._db.execute(stmt)
        documents = list(result.scalars().all())

        return {
            "items": [doc.to_dict() for doc in documents],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_document(self, doc_id: uuid.UUID) -> Document | None:
        """获取文档（不含已软删除）。

        Args:
            doc_id: 文档 ID

        Returns:
            Document 实例，不存在或已删除返回 None
        """
        stmt = select(Document).where(
            Document.id == doc_id, Document.deleted_at.is_(None)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_documents(self) -> int:
        """统计未删除文档数量。

        Returns:
            文档数量
        """
        stmt = select(func.count()).select_from(Document).where(
            Document.deleted_at.is_(None)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    # ===== 文档删除 =====

    async def delete_document(self, doc_id: uuid.UUID) -> bool:
        """删除文档（软删除 + 清理 Chroma 向量 + 删除文件）。

        删除顺序（DEC HO-006 风险缓解）:
        1. 删除 Chroma 中对应向量
        2. 软删除 MariaDB 元数据
        3. 删除上传的文件

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功（文档不存在返回 False）
        """
        document = await self.get_document(doc_id)
        if document is None:
            return False

        # 1. 删除 Chroma 向量（仅当文档已向量化）
        if document.status == "completed" and document.embedding_provider:
            provider = self._embedding_service.provider
            try:
                await asyncio.to_thread(
                    self._chroma.delete_by_doc_id, provider, str(doc_id)
                )
                logger.info("已删除 Chroma 向量: %s", doc_id)
            except Exception as e:
                logger.error(
                    "删除 Chroma 向量失败: %s，错误: %s", doc_id, e
                )
                # 即使向量删除失败也继续删除元数据与文件，
                # 避免残留无向量的文档记录

        # 2. 软删除 MariaDB 元数据
        document.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()

        # 3. 删除上传的文件
        file_path = Path(document.file_path)
        if file_path.exists():
            try:
                await asyncio.to_thread(file_path.unlink)
                logger.info("已删除文件: %s", file_path)
            except Exception as e:
                logger.warning("删除文件失败: %s，错误: %s", file_path, e)

        return True

    # ===== 知识库统计 =====

    async def get_stats(self) -> dict:
        """获取知识库统计信息。

        Returns:
            包含 document_count、total_chunks、embedding_provider、
            embedding_dimension 的字典
        """
        doc_count = await self.count_documents()

        # 统计总切片数（仅已完成的文档）
        stmt = select(func.coalesce(func.sum(Document.chunk_count), 0)).where(
            Document.deleted_at.is_(None),
            Document.status == "completed",
        )
        total_chunks = (await self._db.execute(stmt)).scalar_one()

        return {
            "document_count": doc_count,
            "total_chunks": total_chunks,
            "embedding_provider": self._embedding_service.name,
            "embedding_dimension": self._embedding_service.dimension,
        }

    # ===== 私有方法 =====

    def _validate_file(self, file_type: str, file_size: int) -> None:
        """校验文件类型与大小。

        Args:
            file_type: 文件类型
            file_size: 文件大小（字节）

        Raises:
            ValueError: 类型不支持或大小超限
        """
        if file_type.lower() not in self._settings.supported_file_types:
            raise ValueError(
                f"不支持的文件类型: {file_type}，"
                f"支持的类型: {', '.join(self._settings.supported_file_types)}"
            )

        if file_size > self._settings.max_file_size_bytes:
            raise ValueError(
                f"文件大小超过限制: {file_size} 字节，"
                f"最大 {self._settings.max_file_size_bytes} 字节"
            )

        if file_size <= 0:
            raise ValueError("文件大小不能为 0")

    async def _check_document_limit(self) -> None:
        """检查文档数量是否达到上限。

        Raises:
            ValueError: 文档数量已达上限
        """
        count = await self.count_documents()
        if count >= self._settings.MAX_DOCUMENTS:
            raise ValueError(
                f"文档数量已达上限: {self._settings.MAX_DOCUMENTS}"
            )

    async def _find_by_hash(self, content_hash: str) -> Document | None:
        """通过内容哈希查找文档（去重检测）。

        Args:
            content_hash: SHA-256 哈希

        Returns:
            已存在的 Document 实例，不存在返回 None
        """
        stmt = select(Document).where(
            Document.content_hash == content_hash,
            Document.deleted_at.is_(None),
            Document.status == "completed",
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """计算文件 SHA-256 哈希。

        Args:
            file_path: 文件路径

        Returns:
            64 位十六进制哈希字符串
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                hasher.update(block)
        return hasher.hexdigest()
