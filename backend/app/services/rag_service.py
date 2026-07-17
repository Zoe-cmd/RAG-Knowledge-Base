"""
RAG 检索增强生成服务。

实现 RAG 管线: 查询向量化 → 向量检索 → 相似度过滤 → 上下文组装 → LLM 流式生成 → 引用来源回传。

关键参数（DEC-006/DEC-011）:
- top_k=5: 检索返回 5 个最相似片段
- similarity_threshold=0.3: 低于此相似度的片段被过滤
- max_history_rounds=4: 保留最近 4 轮对话历史

输出验证（G3 质量门禁）:
- 非流式模式：对完整回答执行 validate_answer 验证
- 流式模式：在 chat API 层对最终拼接的回答执行验证
- 输入问题：执行 validate_question 清洗控制字符
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.providers.llm.base import ChatChunk, LLMProvider, Message
from app.providers.llm.factory import get_llm_provider
from app.services.chat_service import ChatService
from app.services.chroma_client import get_chroma_client
from app.services.embedding_service import EmbeddingService
from app.services.output_guard import validate_answer, validate_question

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """单个检索结果。

    Attributes:
        doc_id: 文档 ID
        doc_name: 文档文件名
        chunk_index: 切片索引
        source_path: 源文件路径
        content: 切片文本内容
        similarity: 相似度分数（0~1）
    """

    doc_id: str
    doc_name: str
    chunk_index: int
    source_path: str
    content: str
    similarity: float

    def to_reference(self) -> dict:
        """转换为引用来源字典（用于 SSE references 事件与持久化）。

        安全考虑：不暴露 source_path 内部文件存储路径（SEC-006）。
        字段命名对齐 api-spec.md 第 4.9 节 references 事件规范（chunk 而非 preview），
        内容为前 200 字符预览，避免 SSE 传输过大。
        """
        return {
            "doc_id": self.doc_id,
            "doc_name": self.doc_name,
            "chunk_index": self.chunk_index,
            "chunk": self.content[:200] + ("..." if len(self.content) > 200 else ""),
            "similarity": round(self.similarity, 4),
        }


@dataclass
class RAGStreamResult:
    """RAG 流式问答结果。

    Attributes:
        references: 引用来源列表（检索阶段确定，流式开始前发送）
        answer_chunks: 回答内容的 chunk 迭代器
        total_elapsed_ms: 总耗时（由调用方在流结束后填充）
    """

    references: List[dict]
    answer_chunks: AsyncIterator[ChatChunk]


class RAGService:
    """RAG 检索增强生成服务。

    提供:
    - 检索（查询向量化 → Chroma 检索 → 相似度过滤）
    - 流式生成（上下文组装 → LLM 流式调用）
    - 引用来源回传

    Service 层通过此服务执行 RAG 问答，
    不直接依赖 Provider、Chroma 实现。
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        """初始化 RAGService。

        Args:
            db: 异步数据库会话
            embedding_service: Embedding 服务实例，None 时自动创建
            llm_provider: LLM Provider 实例，None 时从工厂获取
        """
        self._db = db
        self._settings = get_settings()
        self._embedding_service = embedding_service or EmbeddingService()
        self._llm = llm_provider or get_llm_provider()
        self._chroma = get_chroma_client()
        self._chat_service = ChatService(db)

    async def retrieve(self, question: str) -> List[RetrievalResult]:
        """检索相关文档片段。

        流程:
        1. 将问题向量化
        2. Chroma 检索 top_k 个最相似片段
        3. 按相似度阈值过滤
        4. 转换为 RetrievalResult 列表

        Args:
            question: 用户问题

        Returns:
            检索结果列表（按相似度降序），可能为空
        """
        # 1. 查询向量化
        query_embedding = await self._embedding_service.embed_query(question)

        # 2. Chroma 检索
        top_k = self._settings.TOP_K
        raw_results = await asyncio.to_thread(
            self._chroma.query,
            self._embedding_service.provider,
            query_embedding,
            top_k,
        )

        # 3. 相似度过滤
        threshold = self._settings.SIMILARITY_THRESHOLD
        filtered: List[RetrievalResult] = []
        for item in raw_results:
            similarity = item.get("similarity", 0.0)
            if similarity < threshold:
                logger.debug(
                    "过滤低相似度片段: similarity=%.4f < %.2f",
                    similarity,
                    threshold,
                )
                continue

            metadata = item.get("metadata", {})
            filtered.append(
                RetrievalResult(
                    doc_id=metadata.get("doc_id", ""),
                    doc_name=metadata.get("doc_name", ""),
                    chunk_index=metadata.get("chunk_index", 0),
                    source_path=metadata.get("source_path", ""),
                    content=item.get("document", ""),
                    similarity=similarity,
                )
            )

        logger.info(
            "RAG 检索完成: 问题=%s...，top_k=%d，过滤后=%d",
            question[:30],
            top_k,
            len(filtered),
        )
        return filtered

    async def answer(
        self,
        session_id,
        question: str,
    ) -> RAGStreamResult:
        """RAG 流式问答。

        流程:
        1. 检索相关文档片段
        2. 获取多轮对话历史（最近 4 轮）
        3. 组装 RAG 消息列表
        4. 调用 LLM 流式生成
        5. 返回引用来源与回答 chunk 迭代器

        若检索结果为空，返回"未找到相关内容"提示，
        不调用 LLM 生成（避免无依据编造）。

        Args:
            session_id: 会话 ID
            question: 用户问题

        Returns:
            RAGStreamResult，包含引用来源与回答 chunk 迭代器
        """
        import uuid as uuid_module
        sid = (
            uuid_module.UUID(session_id)
            if isinstance(session_id, str)
            else session_id
        )

        # 输入验证：清洗问题中的不可见控制字符
        question = validate_question(question)

        # 1. 检索
        retrieval_results = await self.retrieve(question)
        references = [r.to_reference() for r in retrieval_results]

        # 2. 若无相关内容，返回提示（不调用 LLM）
        if not retrieval_results:
            logger.info("未检索到相关内容，返回提示")

            async def empty_stream() -> AsyncIterator[ChatChunk]:
                yield ChatChunk(
                    content="未在知识库中找到相关内容，无法回答该问题。",
                    finish_reason="stop",
                )

            return RAGStreamResult(
                references=[],
                answer_chunks=empty_stream(),
            )

        # 3. 获取历史对话
        history = await self._chat_service.get_recent_history(sid)

        # 4. 组装 RAG 消息
        context_chunks = [r.content for r in retrieval_results]
        messages = self._chat_service.build_rag_messages(
            question=question,
            context_chunks=context_chunks,
            history=history,
        )

        # 5. LLM 流式生成
        stream = await self._llm.chat_completion(
            messages=messages,
            stream=True,
            temperature=0.7,
        )

        logger.info(
            "RAG 问答开始: session=%s，引用数=%d，历史轮数=%d",
            sid,
            len(references),
            len(history) // 2,
        )

        return RAGStreamResult(
            references=references,
            answer_chunks=stream,
        )

    async def chat_non_stream(
        self,
        question: str,
        history: List[Message] | None = None,
    ) -> tuple[str, List[dict]]:
        """非流式问答（用于测试或简单场景）。

        Args:
            question: 用户问题
            history: 历史消息列表，None 表示无历史

        Returns:
            (回答内容, 引用来源列表)
        """
        # 输入验证：清洗问题中的不可见控制字符
        question = validate_question(question)

        # 1. 检索
        retrieval_results = await self.retrieve(question)
        references = [r.to_reference() for r in retrieval_results]

        # 2. 无相关内容
        if not retrieval_results:
            return "未在知识库中找到相关内容，无法回答该问题。", []

        # 3. 组装消息
        context_chunks = [r.content for r in retrieval_results]
        messages = self._chat_service.build_rag_messages(
            question=question,
            context_chunks=context_chunks,
            history=history or [],
        )

        # 4. 非流式生成
        response = await self._llm.chat_completion(
            messages=messages,
            stream=False,
            temperature=0.7,
        )

        # 5. 输出验证：空内容检测、控制字符过滤、超长截断
        validation = validate_answer(response.content)
        if validation.is_empty:
            logger.warning("LLM 返回空内容，已使用占位提示")
        if validation.is_truncated:
            logger.info("LLM 输出超长，已截断")
        if validation.had_control_chars:
            logger.info("已过滤 LLM 输出中的控制字符")

        return validation.content, references
