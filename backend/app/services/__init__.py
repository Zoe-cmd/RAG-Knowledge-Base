"""
Service 层包。

提供业务逻辑服务，封装 Provider、Parser、Chunker、Chroma 等基础组件，
为 API 层提供统一的高层接口。

服务模块:
- chroma_client: Chroma 向量库客户端封装
- embedding_service: Embedding 调用服务
- document_service: 文档管理服务（上传→解析→切分→向量化→存储）
- chat_service: 聊天会话与消息服务（多轮上下文管理）
- rag_service: RAG 检索增强生成服务
- prompt_template: Prompt 模板与上下文组装
"""

from app.services.chat_service import ChatService
from app.services.chroma_client import ChromaClient, get_chroma_client
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.prompt_template import SYSTEM_PROMPT, build_rag_messages
from app.services.rag_service import RAGService, RetrievalResult

__all__ = [
    "ChromaClient",
    "get_chroma_client",
    "EmbeddingService",
    "get_embedding_service",
    "DocumentService",
    "ChatService",
    "RAGService",
    "RetrievalResult",
    "SYSTEM_PROMPT",
    "build_rag_messages",
]
