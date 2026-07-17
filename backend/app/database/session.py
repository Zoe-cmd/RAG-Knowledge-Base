"""
数据库连接与会话管理模块。

使用 SQLAlchemy 2.0 异步引擎 + asyncmy 驱动连接 MariaDB。
提供异步会话工厂与依赖注入。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings


def _create_engine():
    """创建异步引擎。

    使用 settings 中的 DATABASE_URL 创建 SQLAlchemy 异步引擎。
    """
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
    )


# 全局异步引擎（懒加载）
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    """获取全局异步引擎（懒加载单例）。"""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取异步会话工厂（懒加载单例）。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取数据库会话。

    用法::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: 异步数据库会话
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """关闭引擎，释放连接池。

    在应用关闭时调用。
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
