"""
应用配置模块。

通过 Pydantic Settings 从 .env 文件读取配置，提供类型安全的配置访问。
所有配置项均有默认值，敏感配置（如 API Key）必须通过 .env 提供。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类。

    从 .env 文件加载配置，所有字段有默认值。
    敏感字段（OPENAI_API_KEY、DATABASE_URL）必须在 .env 中提供。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ===== 应用配置 =====
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # ===== MariaDB =====
    DATABASE_URL: str = Field(
        default="mysql+asyncmy://root:password@127.0.0.1:3306/ai_knowledge_base",
        description="MariaDB 异步连接字符串",
    )

    # ===== OpenAI =====
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ===== Embedding Provider =====
    EMBEDDING_PROVIDER: str = Field(
        default="openai",
        description="Embedding Provider: openai 或 bge",
    )

    # ===== 本地模型 =====
    MODEL_CACHE_DIR: str = "./data/models"

    # ===== Chroma 向量库 =====
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # ===== RAG 参数 =====
    CHUNK_SIZE: int = Field(default=500, description="切片大小（字符数）")
    CHUNK_OVERLAP: int = Field(default=50, description="切片重叠（字符数）")
    TOP_K: int = Field(default=5, description="检索返回的最相似结果数量")
    SIMILARITY_THRESHOLD: float = Field(
        default=0.3, description="相似度阈值，低于此值的片段被过滤"
    )
    MAX_HISTORY_ROUNDS: int = Field(
        default=4, description="多轮对话保留的历史轮数"
    )

    # ===== 文件上传 =====
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 20
    MAX_DOCUMENTS: int = 100

    # ===== LLM 超时与重试 =====
    LLM_TIMEOUT: int = Field(default=30, description="LLM 调用超时（秒）")
    LLM_STREAM_TIMEOUT: int = Field(
        default=60, description="LLM 流式调用超时（秒）"
    )
    LLM_MAX_RETRIES: int = Field(
        default=3,
        description="LLM 调用最大重试次数（仅对超时与连接错误重试，指数退避）",
    )

    @property
    def max_file_size_bytes(self) -> int:
        """最大文件大小（字节）。"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def supported_file_types(self) -> tuple[str, ...]:
        """支持的文件类型扩展名。"""
        return ("pdf", "docx", "md", "txt")

    @property
    def upload_dir_path(self) -> Path:
        """上传目录 Path 对象，自动创建。"""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_persist_path(self) -> Path:
        """Chroma 持久化目录 Path 对象，自动创建。"""
        path = Path(self.CHROMA_PERSIST_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """获取 Settings 单例。

    使用 lru_cache 确保全局只有一个 Settings 实例，
    避免重复读取 .env 文件。
    """
    return Settings()
