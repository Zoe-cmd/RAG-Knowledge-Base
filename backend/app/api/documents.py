"""
文档管理 API 路由。

提供文档上传、列表、删除、知识库统计接口。
对应 api-spec.md 第 4.1 节。

端点:
- POST   /api/documents/upload  上传文档（multipart/form-data）
- GET    /api/documents         文档列表（分页）
- DELETE /api/documents/{id}    删除文档
- GET    /api/documents/stats   知识库统计
"""

import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_db
from app.parsers.pdf_parser import ScannedPDFError as ParserScannedPDFError
from app.services.document_service import DocumentService
from app.utils.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    ValidationError,
)
from app.utils.response import paginated_response, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])


def _get_file_extension(filename: str) -> str:
    """从文件名提取扩展名（小写，不含点）。

    Args:
        filename: 文件名

    Returns:
        扩展名（如 pdf/docx/md/txt）
    """
    return Path(filename).suffix.lower().lstrip(".")


@router.post("/upload", status_code=201)
async def upload_documents(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传文档（支持批量）。

    自动触发解析→切分→向量化流水线。
    支持格式: PDF、Word(docx)、Markdown、TXT。
    单文件上限 20MB，文档总数上限 100。

    Returns:
        包含成功上传文档列表与失败列表的响应
    """
    if not files:
        raise ValidationError("未提供文件")

    settings = get_settings()
    service = DocumentService(db)

    uploaded: list[dict] = []
    failed: list[dict] = []

    for file in files:
        if not file.filename:
            failed.append(
                {"filename": "未知", "error": "文件名为空", "code": "VALIDATION_ERROR"}
            )
            continue

        file_type = _get_file_extension(file.filename)

        # 类型校验
        if file_type not in settings.supported_file_types:
            failed.append(
                {
                    "filename": file.filename,
                    "error": f"不支持的文件类型: {file_type}",
                    "code": "UNSUPPORTED_FILE_TYPE",
                }
            )
            continue

        # 保存到临时文件并校验大小
        try:
            tmp_path = await _save_upload_to_temp(file, settings.max_file_size_bytes)
        except FileTooLargeError as e:
            failed.append(
                {
                    "filename": file.filename,
                    "error": e.message,
                    "code": "FILE_TOO_LARGE",
                }
            )
            continue
        except Exception as e:
            logger.error("保存临时文件失败: %s, 错误: %s", file.filename, e)
            failed.append(
                {
                    "filename": file.filename,
                    "error": f"文件读取失败: {e}",
                    "code": "INTERNAL_ERROR",
                }
            )
            continue

        file_size = tmp_path.stat().st_size

        # 处理文档
        try:
            document = await service.upload_and_process(
                file_path=tmp_path,
                filename=file.filename,
                file_type=file_type,
                file_size=file_size,
            )
            uploaded.append(document.to_dict())
        except ParserScannedPDFError:
            failed.append(
                {
                    "filename": file.filename,
                    "error": "该 PDF 为扫描件，MVP 暂不支持，需 OCR",
                    "code": "SCANNED_PDF",
                }
            )
        except ValueError as e:
            failed.append(
                {
                    "filename": file.filename,
                    "error": str(e),
                    "code": "VALIDATION_ERROR",
                }
            )
        except Exception as e:
            logger.error(
                "文档处理失败: %s, 错误: %s", file.filename, e, exc_info=True
            )
            failed.append(
                {
                    "filename": file.filename,
                    "error": str(e)[:200],
                    "code": "INTERNAL_ERROR",
                }
            )

    return success_response(
        data={"documents": uploaded, "failed": failed}
    )


async def _save_upload_to_temp(
    file: UploadFile, max_size: int
) -> Path:
    """将 UploadFile 保存到临时文件，并校验大小。

    Args:
        file: FastAPI UploadFile 对象
        max_size: 最大文件大小（字节）

    Returns:
        临时文件路径

    Raises:
        FileTooLargeError: 文件大小超过限制
    """
    # 创建临时文件
    fd, tmp_path = tempfile.mkstemp(prefix="upload_", suffix=".tmp")
    os.close(fd)

    path = Path(tmp_path)
    total_size = 0

    try:
        with open(path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size:
                    raise FileTooLargeError(
                        filename=file.filename or "未知",
                        size_mb=total_size / (1024 * 1024),
                        limit_mb=max_size // (1024 * 1024),
                    )
                f.write(chunk)
    except Exception:
        # 出错时清理临时文件
        path.unlink(missing_ok=True)
        raise

    return path


@router.get("")
async def list_documents(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(
        default=None,
        description="按状态过滤: pending/processing/completed/failed",
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表（分页）。

    按创建时间倒序排列。

    Returns:
        分页文档列表
    """
    service = DocumentService(db)
    result = await service.list_documents(page=page, page_size=size)

    # 按状态过滤（应用层过滤，MVP 简化）
    items = result["items"]
    if status:
        items = [item for item in items if item.get("status") == status]
        result["total"] = len(items)

    return paginated_response(
        items=items,
        total=result["total"],
        page=page,
        size=size,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """删除文档。

    同步删除 Chroma 中该文档的所有向量，
    软删除 MariaDB 记录，删除文件系统原文件。

    Returns:
        204 No Content
    """
    service = DocumentService(db)
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise DocumentNotFoundError()


@router.get("/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取知识库统计信息。

    Returns:
        包含文档数、切片数、Provider 信息的统计
    """
    service = DocumentService(db)
    stats = await service.get_stats()
    return success_response(data=stats)
