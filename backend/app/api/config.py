"""
配置管理 API 路由。

提供应用配置查询与 Embedding Provider 切换接口。
对应 api-spec.md 第 4.4 节。

端点:
- GET /api/config                         获取当前配置
- PUT /api/config/embedding-provider      切换 Embedding Provider
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.session import get_db
from app.models.document import Document
from app.models.message import ChatMessage
from app.models.session import ChatSession
from app.providers.embedding.factory import get_embedding_provider
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["配置管理"])


class SwitchProviderRequest(BaseModel):
    """切换 Embedding Provider 请求体。"""

    provider: str = Field(..., description="Embedding Provider: openai 或 bge")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """校验 provider 值。"""
        v = v.lower().strip()
        if v not in ("openai", "bge"):
            raise ValueError("provider 必须为 openai 或 bge")
        return v


@router.get("")
async def get_config(
    db: AsyncSession = Depends(get_db),
):
    """获取当前应用配置与统计信息。

    Returns:
        配置信息与知识库统计
    """
    settings = get_settings()
    provider = get_embedding_provider()

    # 统计文档
    total_docs = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.deleted_at.is_(None))
        )
    ).scalar_one()

    completed_docs = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.deleted_at.is_(None),
                Document.status == "completed",
            )
        )
    ).scalar_one()

    processing_docs = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.deleted_at.is_(None),
                Document.status == "processing",
            )
        )
    ).scalar_one()

    failed_docs = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.deleted_at.is_(None),
                Document.status == "failed",
            )
        )
    ).scalar_one()

    total_chunks = (
        await db.execute(
            select(func.coalesce(func.sum(Document.chunk_count), 0)).where(
                Document.deleted_at.is_(None),
                Document.status == "completed",
            )
        )
    ).scalar_one()

    total_sessions = (
        await db.execute(
            select(func.count())
            .select_from(ChatSession)
            .where(ChatSession.deleted_at.is_(None))
        )
    ).scalar_one()

    total_messages = (await db.execute(select(func.count()).select_from(ChatMessage))).scalar_one()

    return success_response(
        data={
            "embedding_provider": provider.name,
            "embedding_dimension": provider.dimension,
            "llm_model": settings.LLM_MODEL,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "top_k": settings.TOP_K,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
            "max_history_rounds": settings.MAX_HISTORY_ROUNDS,
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "max_documents": settings.MAX_DOCUMENTS,
            "statistics": {
                "total_documents": total_docs,
                "completed_documents": completed_docs,
                "processing_documents": processing_docs,
                "failed_documents": failed_docs,
                "total_chunks": total_chunks,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
            },
        }
    )


@router.put("/embedding-provider")
async def switch_embedding_provider(
    request: SwitchProviderRequest,
    db: AsyncSession = Depends(get_db),
):
    """切换 Embedding Provider。

    切换后需重建索引（维度可能不同）。
    旧 collection 保留但不使用，需对所有已上传文档重新 Embedding。

    Returns:
        切换前后的 Provider 信息与重建索引提示
    """
    settings = get_settings()
    old_provider_name = settings.EMBEDDING_PROVIDER
    old_provider = get_embedding_provider()

    # 校验是否与当前相同
    if request.provider == old_provider_name:
        return success_response(
            data={
                "previous_provider": old_provider_name,
                "current_provider": old_provider_name,
                "previous_dimension": old_provider.dimension,
                "current_dimension": old_provider.dimension,
                "needs_reindex": False,
                "documents_to_reindex": 0,
                "message": "Provider 未变更",
            }
        )

    # 更新配置（写入运行时 settings，需重启或重新加载生效）
    # 注意: MVP 阶段仅返回提示，实际切换需修改 .env 并重启
    # 这里计算切换后的维度信息
    new_dimension = 1536 if request.provider == "openai" else 1024

    # 统计需要重建索引的文档数
    docs_to_reindex = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.deleted_at.is_(None),
                Document.status == "completed",
            )
        )
    ).scalar_one()

    logger.info(
        "Embedding Provider 切换请求: %s → %s, 需重建 %d 个文档索引",
        old_provider_name,
        request.provider,
        docs_to_reindex,
    )

    return success_response(
        data={
            "previous_provider": old_provider_name,
            "current_provider": request.provider,
            "previous_dimension": old_provider.dimension,
            "current_dimension": new_dimension,
            "needs_reindex": True,
            "documents_to_reindex": docs_to_reindex,
            "message": (
                f"切换至 {request.provider} 需重建索引。"
                f"请修改 .env 中 EMBEDDING_PROVIDER={request.provider} 并重启服务，"
                f"然后重新上传或触发已上传文档的重新向量化。"
            ),
        }
    )
