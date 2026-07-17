"""
OpenAI LLM Provider。

基于 OpenAI gpt-4o-mini 模型，支持流式与非流式生成。
通过 base_url 配置支持任意 OpenAI 兼容端点。

重试机制（G2 质量门禁）:
- 仅对可重试的瞬时错误重试：APITimeoutError、APIConnectionError
- 不重试的错误：AuthenticationError（API Key 无效）、BadRequestError、NotFoundError
- 指数退避：1s → 2s → 4s
- 最大重试次数可配置（默认 3 次，通过 LLM_MAX_RETRIES 配置）
- 流式模式不重试（流一旦开始返回 token 即无法安全重试，避免重复输出）
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import List, Union

import openai

from app.providers.llm.base import ChatChunk, ChatResponse, LLMProvider, Message

logger = logging.getLogger(__name__)

# 可重试的异常类型（瞬时错误：网络抖动、服务暂时不可用）
# 不可重试的错误（如 AuthenticationError）会直接抛出
_RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.APIConnectionError,
)


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM Provider。

    使用 openai SDK 调用 gpt-4o-mini 模型。
    支持 base_url 配置，兼容第三方 OpenAI 兼容端点
    （如 Azure OpenAI、本地 vLLM 等）。

    非流式调用支持自动重试（指数退避），流式调用不重试。

    Attributes:
        name: "openai"
        model: 配置的模型名（默认 gpt-4o-mini）
    """

    _NAME = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        stream_timeout: int = 60,
        max_retries: int = 3,
    ):
        """初始化 OpenAI LLM Provider。

        Args:
            api_key: OpenAI API Key
            model: LLM 模型名，默认 gpt-4o-mini
            base_url: API 基础 URL，可配置为兼容端点
            timeout: 非流式调用超时（秒）
            stream_timeout: 流式调用超时（秒）
            max_retries: 非流式调用最大重试次数（仅对超时与连接错误），
                默认 3 次，指数退避 1s/2s/4s
        """
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._model_name = model
        self._stream_timeout = stream_timeout
        self._max_retries = max_retries if max_retries >= 0 else 0

    @property
    def name(self) -> str:
        return self._NAME

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def max_retries(self) -> int:
        """最大重试次数。"""
        return self._max_retries

    async def chat_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Union[ChatResponse, AsyncIterator[ChatChunk]]:
        """聊天补全。

        非流式模式下，对超时与连接错误自动重试（指数退避）；
        流式模式不重试（避免重复输出）。

        Args:
            messages: 消息列表
            stream: 是否流式返回
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Returns:
            ChatResponse 或 AsyncIterator[ChatChunk]

        Raises:
            openai.APITimeoutError: 重试耗尽后仍超时
            openai.APIConnectionError: 重试耗尽后仍连接失败
            openai.AuthenticationError: API Key 无效（不重试，直接抛出）
            openai.APIError: 其他 API 错误
        """
        # 将 Message 转换为 OpenAI SDK 格式
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        if stream:
            # 流式不重试：流一旦开始即返回 token，重试会导致重复输出
            return self._stream_chat(openai_messages, temperature, max_tokens)
        else:
            return await self._non_stream_chat_with_retry(
                openai_messages, temperature, max_tokens
            )

    async def _non_stream_chat_with_retry(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int | None,
    ) -> ChatResponse:
        """带重试的非流式聊天补全。

        仅对 _RETRYABLE_EXCEPTIONS 中的异常重试，其他异常直接抛出。
        指数退避：第 n 次重试等待 2^n 秒（1s、2s、4s...）。

        Args:
            messages: 消息列表
            temperature: 采样温度
            max_tokens: 最大 token 数

        Returns:
            ChatResponse

        Raises:
            最后一次重试失败时抛出原始异常
        """
        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await self._non_stream_chat(
                    messages, temperature, max_tokens
                )
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    # 指数退避：1s, 2s, 4s ...
                    wait_seconds = 2 ** attempt
                    logger.warning(
                        "LLM 非流式调用失败（第 %d/%d 次），%ds 后重试: %s",
                        attempt + 1,
                        self._max_retries + 1,
                        wait_seconds,
                        type(exc).__name__,
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.error(
                        "LLM 非流式调用重试 %d 次后仍失败: %s",
                        self._max_retries,
                        type(exc).__name__,
                    )

        # 所有重试耗尽，抛出最后一次异常
        assert last_exception is not None  # 理论上不会到达
        raise last_exception

    async def _non_stream_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int | None,
    ) -> ChatResponse:
        """非流式聊天补全（单次调用，不含重试）。"""
        kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return ChatResponse(content=content, usage=usage)

    async def _stream_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int | None,
    ) -> AsyncIterator[ChatChunk]:
        """流式聊天补全。

        使用 async for 逐个 yield ChatChunk。
        流式模式不重试：一旦开始返回 token 即无法安全回退。
        """
        kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            content = delta.content if delta and delta.content else ""
            finish_reason = choice.finish_reason

            # 只在有内容或结束时才 yield
            if content or finish_reason:
                yield ChatChunk(content=content, finish_reason=finish_reason)
