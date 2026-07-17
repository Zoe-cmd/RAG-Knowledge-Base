"""
FastAPI 应用入口。

模块化单体架构（DEC-014），本地 localhost 运行（DEC-001）。
提供 AI 文档知识库后端 API，包括文档管理、RAG 问答、聊天历史。

启动: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    chat_router,
    config_router,
    documents_router,
    sessions_router,
)
from app.config.settings import get_settings
from app.database.session import close_engine
from app.utils.exceptions import register_exception_handlers

# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    启动时初始化资源，关闭时释放连接。
    """
    logger.info("AI 文档知识库后端启动中...")
    settings = get_settings()
    logger.info(
        "配置: host=%s:%s, debug=%s, embedding_provider=%s, llm_model=%s",
        settings.APP_HOST,
        settings.APP_PORT,
        settings.DEBUG,
        settings.EMBEDDING_PROVIDER,
        settings.LLM_MODEL,
    )
    logger.info("应用启动完成")

    yield

    # 关闭资源
    logger.info("应用关闭中...")
    await close_engine()
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    Returns:
        配置好的 FastAPI 实例
    """
    settings = get_settings()

    app = FastAPI(
        title="AI 文档知识库 API",
        description=(
            "基于 RAG 的本地 AI 文档知识库后端 API。\n\n"
            "功能: 文档上传与解析、向量检索、流式问答、聊天历史管理。\n\n"
            "架构: Python + FastAPI + MariaDB + Chroma + OpenAI"
        ),
        version="1.0.0",
        # 安全考虑：仅 DEBUG 模式下暴露 API 文档（SEC-003）
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS 中间件（DEC-015: 开发环境通过 Vite Proxy 规避跨域，
    # 此处仍配置 CORS 作为后备，允许本地前端访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 注册路由（统一 /api 前缀）
    app.include_router(documents_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api/chat")
    app.include_router(chat_router, prefix="/api")
    app.include_router(config_router, prefix="/api")

    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查端点。"""
        return {"status": "ok", "service": "ai-knowledge-base"}

    return app


# 全局应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
