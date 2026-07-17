"""
聊天消息 API 路由（含 SSE 流式问答）。

提供 RAG 流式问答端点。
对应 api-spec.md 第 4.3 节。

端点:
- POST /api/chat/messages  发送消息（SSE 流式响应）

SSE 事件格式（DEC-010）:
- event: references  引用来源（流式开始前）
- event: token       流式 token
- event: done        完成
- event: error       错误
"""

import logging
import time
import uuid as uuid_module
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db, get_session_factory
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService
from app.utils.exceptions import SessionNotFoundError
from app.utils.sse import done_event, error_event, references_event, token_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天消息"])

# SSE 响应头
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲（如使用反向代理）
}


class ChatRequest(BaseModel):
    """发送消息请求体。"""

    session_id: str = Field(..., description="会话 ID（UUID）")
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """校验 session_id 为有效 UUID。"""
        try:
            uuid_module.UUID(v)
        except ValueError:
            raise ValueError("session_id 不是有效的 UUID")
        return v

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """校验问题非空。"""
        if not v.strip():
            raise ValueError("问题不能为空")
        return v.strip()


@router.post("/messages")
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """发送消息（SSE 流式响应）。

    RAG 管线: 查询向量化 → Chroma 检索 → 相似度过滤 →
    上下文组装 → LLM 流式生成 → 引用来源回传。

    返回 SSE 事件流:
    1. references 事件（引用来源）
    2. token 事件（逐个，流式回答）
    3. done 事件（完成，含 message_id 与 elapsed_ms）

    若检索无结果，发送空 references 与 done 事件。
    若发生错误，发送 error 事件。
    """
    session_id = uuid_module.UUID(request.session_id)
    question = request.question

    # 预校验会话存在（在流式开始前返回 404）
    chat_service = ChatService(db)
    session = await chat_service.get_session(session_id)
    if session is None:
        raise SessionNotFoundError()

    # 保存用户消息（在主会话中提交）
    await chat_service.save_message(
        session_id=session_id,
        role="user",
        content=question,
    )
    await db.commit()

    # 流式响应（使用独立会话，避免与主会话生命周期冲突）
    factory = get_session_factory()

    async def stream() -> AsyncGenerator[str, None]:
        """SSE 流式生成器。"""
        start_time = time.time()
        assistant_content = ""
        references: list[dict] = []
        error_occurred = False

        async with factory() as stream_db:
            try:
                # 创建 RAG 服务（使用流式独立会话）
                rag_service = RAGService(stream_db)

                # 执行 RAG 问答（检索 + 组装 + LLM 流式）
                result = await rag_service.answer(
                    session_id=session_id,
                    question=question,
                )
                references = result.references

                # 1. 发送 references 事件
                yield references_event(references)

                # 2. 流式发送 token 事件
                async for chunk in result.answer_chunks:
                    if chunk.content:
                        assistant_content += chunk.content
                        yield token_event(chunk.content)

                elapsed_ms = int((time.time() - start_time) * 1000)

                # 3. 保存 assistant 消息
                stream_chat_service = ChatService(stream_db)
                message = await stream_chat_service.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_content,
                    references=references if references else None,
                    elapsed_ms=elapsed_ms,
                )
                await stream_db.commit()

                # 4. 发送 done 事件
                yield done_event(str(message.id), elapsed_ms)

            except GeneratorExit:
                # 客户端断开连接（停止生成）
                # 保存已生成的部分内容
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    "客户端断开连接，保存部分内容: session=%s, 已生成 %d 字符",
                    session_id,
                    len(assistant_content),
                )
                if assistant_content:
                    try:
                        stream_chat_service = ChatService(stream_db)
                        await stream_chat_service.save_message(
                            session_id=session_id,
                            role="assistant",
                            content=assistant_content,
                            references=references if references else None,
                            elapsed_ms=elapsed_ms,
                        )
                        await stream_db.commit()
                    except Exception as save_err:
                        logger.error(
                            "保存部分内容失败: %s", save_err, exc_info=True
                        )
                        await stream_db.rollback()
                raise

            except Exception as e:
                # 流式过程中发生错误
                error_occurred = True
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    "流式问答失败: session=%s, 错误: %s",
                    session_id,
                    e,
                    exc_info=True,
                )

                # 尝试保存已生成的部分内容
                if assistant_content:
                    try:
                        stream_chat_service = ChatService(stream_db)
                        await stream_chat_service.save_message(
                            session_id=session_id,
                            role="assistant",
                            content=assistant_content,
                            references=references if references else None,
                            elapsed_ms=elapsed_ms,
                        )
                        await stream_db.commit()
                    except Exception:
                        await stream_db.rollback()

                # 发送 error 事件
                error_code = _classify_error(e)
                yield error_event(str(e)[:200], error_code)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


def _classify_error(exc: Exception) -> str:
    """将异常分类为 SSE 错误码。

    Args:
        exc: 异常实例

    Returns:
        错误码字符串
    """
    exc_name = type(exc).__name__
    exc_msg = str(exc).lower()

    if "timeout" in exc_name.lower() or "timeout" in exc_msg:
        return "LLM_TIMEOUT"
    if "auth" in exc_msg or "api key" in exc_msg or "401" in exc_msg:
        return "LLM_AUTH_ERROR"
    if "connection" in exc_msg or "network" in exc_msg:
        return "LLM_CONNECTION_ERROR"
    if "embed" in exc_msg.lower():
        return "EMBEDDING_ERROR"
    return "INTERNAL_ERROR"
