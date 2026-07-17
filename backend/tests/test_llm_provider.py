"""
OpenAI LLM Provider 单元测试。

测试 chat_completion 的流式与非流式模式，使用 mock 隔离 OpenAI API。
测试重试机制（G2 质量门禁）：超时/连接错误重试、认证错误不重试、指数退避。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.providers.llm.base import ChatChunk, Message
from app.providers.llm.openai_provider import OpenAILLMProvider


class TestOpenAILLMProvider:
    """OpenAI LLM Provider 测试。"""

    def test_properties(self):
        """Provider 属性。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="gpt-4o-mini"
        )
        assert provider.name == "openai"
        assert provider.model == "gpt-4o-mini"

    def test_custom_model(self):
        """自定义模型名。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="gpt-4"
        )
        assert provider.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_non_stream_chat(self):
        """非流式聊天补全。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        # Mock 响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这是回答"
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [Message(role="user", content="问题")]
        result = await provider.chat_completion(messages, stream=False)

        assert result.content == "这是回答"
        assert result.usage["prompt_tokens"] == 10
        assert result.usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_non_stream_chat_with_max_tokens(self):
        """非流式聊天补全（带 max_tokens）。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.usage = None
        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [Message(role="user", content="问题")]
        result = await provider.chat_completion(
            messages, stream=False, max_tokens=100
        )

        assert result.content == "回答"
        assert result.usage == {}

    @pytest.mark.asyncio
    async def test_stream_chat(self):
        """流式聊天补全。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        # Mock 流式响应 chunks
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "你好"
        chunk1.choices[0].finish_reason = None

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "世界"
        chunk2.choices[0].finish_reason = None

        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None
        chunk3.choices[0].finish_reason = "stop"

        # 空 choices 的 chunk（应被跳过）
        chunk_empty = MagicMock()
        chunk_empty.choices = []

        async def mock_stream():
            for chunk in [chunk_empty, chunk1, chunk2, chunk3]:
                yield chunk

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        messages = [Message(role="user", content="问题")]
        result = await provider.chat_completion(messages, stream=True)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        assert len(chunks) == 3  # 空 choices 的 chunk 被跳过
        assert chunks[0].content == "你好"
        assert chunks[1].content == "世界"
        assert chunks[2].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_chat_with_max_tokens(self):
        """流式聊天补全（带 max_tokens）。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "回答"
        chunk.choices[0].finish_reason = "stop"

        async def mock_stream():
            yield chunk

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        messages = [Message(role="user", content="问题")]
        result = await provider.chat_completion(
            messages, stream=True, max_tokens=50
        )

        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_message_conversion(self):
        """消息格式转换。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "回答"
        mock_response.usage = None
        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        messages = [
            Message(role="system", content="系统提示"),
            Message(role="user", content="用户问题"),
            Message(role="assistant", content="历史回答"),
        ]
        await provider.chat_completion(messages, stream=False)

        # 验证调用参数中的消息格式
        call_args = provider._client.chat.completions.create.call_args
        sent_messages = call_args.kwargs["messages"]
        assert sent_messages[0] == {"role": "system", "content": "系统提示"}
        assert sent_messages[1] == {"role": "user", "content": "用户问题"}
        assert sent_messages[2] == {"role": "assistant", "content": "历史回答"}


class TestOpenAILLMProviderEdgeCases:
    """OpenAI LLM Provider 边界情况测试。"""

    @pytest.mark.asyncio
    async def test_empty_response_content(self):
        """空响应内容。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = None
        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await provider.chat_completion(
            [Message(role="user", content="问题")], stream=False
        )
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_stream_empty_choices_all(self):
        """流式响应全部为空 choices。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        provider._client = MagicMock()

        async def mock_stream():
            for _ in range(3):
                chunk = MagicMock()
                chunk.choices = []
                yield chunk

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        result = await provider.chat_completion(
            [Message(role="user", content="问题")], stream=True
        )
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        assert len(chunks) == 0


class TestOpenAILLMProviderRetry:
    """OpenAI LLM Provider 重试机制测试（G2 质量门禁）。"""

    def test_default_max_retries(self):
        """默认最大重试次数为 3。"""
        provider = OpenAILLMProvider(api_key="test-key", model="test-model")
        assert provider.max_retries == 3

    def test_custom_max_retries(self):
        """可自定义最大重试次数。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=5
        )
        assert provider.max_retries == 5

    def test_zero_max_retries(self):
        """max_retries=0 表示不重试。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=0
        )
        assert provider.max_retries == 0

    def test_negative_max_retries_clamped_to_zero(self):
        """负数 max_retries 应被钳制为 0。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=-1
        )
        assert provider.max_retries == 0

    @pytest.mark.asyncio
    async def test_retry_on_timeout_then_success(self):
        """超时后重试应最终成功（mock sleep 避免等待）。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=3
        )
        provider._client = MagicMock()

        # 成功响应
        success_response = MagicMock()
        success_response.choices = [MagicMock()]
        success_response.choices[0].message.content = "成功回答"
        success_response.usage = None

        # 第一次抛超时，第二次成功
        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=[
                openai.APITimeoutError("timeout"),
                success_response,
            ]
        )

        # mock asyncio.sleep 避免真实等待
        with patch("app.providers.llm.openai_provider.asyncio.sleep", new=AsyncMock()):
            result = await provider.chat_completion(
                [Message(role="user", content="问题")], stream=False
            )

        assert result.content == "成功回答"
        assert provider._client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_then_success(self):
        """连接错误后重试应最终成功。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=3
        )
        provider._client = MagicMock()

        success_response = MagicMock()
        success_response.choices = [MagicMock()]
        success_response.choices[0].message.content = "成功"
        success_response.usage = None

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=[
                openai.APIConnectionError(request=MagicMock()),
                success_response,
            ]
        )

        with patch("app.providers.llm.openai_provider.asyncio.sleep", new=AsyncMock()):
            result = await provider.chat_completion(
                [Message(role="user", content="问题")], stream=False
            )

        assert result.content == "成功"
        assert provider._client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """认证错误不应重试，直接抛出。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=3
        )
        provider._client = MagicMock()

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=openai.AuthenticationError(
                message="invalid api key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )

        with pytest.raises(openai.AuthenticationError):
            await provider.chat_completion(
                [Message(role="user", content="问题")], stream=False
            )

        # 认证错误不重试，只调用一次
        assert provider._client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_last_error(self):
        """重试耗尽后应抛出最后一次异常。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=2
        )
        provider._client = MagicMock()

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        # 所有 3 次调用（1 次初始 + 2 次重试）都超时
        provider._client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout")
        )

        with patch("app.providers.llm.openai_provider.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(openai.APITimeoutError):
                await provider.chat_completion(
                    [Message(role="user", content="问题")], stream=False
                )

        # 初始 1 次 + 重试 2 次 = 3 次
        assert provider._client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_zero_max_retries(self):
        """max_retries=0 时失败不重试。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=0
        )
        provider._client = MagicMock()

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout")
        )

        with pytest.raises(openai.APITimeoutError):
            await provider.chat_completion(
                [Message(role="user", content="问题")], stream=False
            )

        # 不重试，只调用 1 次
        assert provider._client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self):
        """应使用指数退避（1s, 2s, 4s）。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=3
        )
        provider._client = MagicMock()

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout")
        )

        sleep_mock = AsyncMock()
        with patch("app.providers.llm.openai_provider.asyncio.sleep", new=sleep_mock):
            with pytest.raises(openai.APITimeoutError):
                await provider.chat_completion(
                    [Message(role="user", content="问题")], stream=False
                )

        # 应调用 sleep 3 次（初始失败后 + 3 次重试前的等待）
        # 等待时间序列：2^0=1, 2^1=2, 2^2=4
        assert sleep_mock.call_count == 3
        actual_waits = [call.args[0] for call in sleep_mock.call_args_list]
        assert actual_waits == [1, 2, 4]

    @pytest.mark.asyncio
    async def test_stream_mode_no_retry(self):
        """流式模式不应重试（即使抛出可重试异常）。"""
        provider = OpenAILLMProvider(
            api_key="test-key", model="test-model", max_retries=3
        )
        provider._client = MagicMock()

        provider._client.chat = MagicMock()
        provider._client.chat.completions = MagicMock()
        provider._client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError("timeout")
        )

        with pytest.raises(openai.APITimeoutError):
            result = await provider.chat_completion(
                [Message(role="user", content="问题")], stream=True
            )
            # 流式返回的是 async generator，需要迭代才会触发实际调用
            async for _ in result:
                pass

        # 流式不重试，只调用 1 次
        assert provider._client.chat.completions.create.call_count == 1
