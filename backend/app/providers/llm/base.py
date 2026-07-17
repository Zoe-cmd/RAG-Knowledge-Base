"""
LLM Provider 抽象基类。

定义统一的 LLM 调用接口，支持流式与非流式生成。
依赖倒置：Service 层依赖此抽象，不依赖具体实现。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import List, Union


@dataclass
class Message:
    """聊天消息。

    用于组装 LLM 上下文（system/user/assistant）。

    Attributes:
        role: 消息角色：system / user / assistant
        content: 消息内容
    """

    role: str
    content: str


@dataclass
class ChatChunk:
    """流式生成的单个 chunk。

    LLM 流式生成时逐个返回的片段。

    Attributes:
        content: 本次 chunk 的内容（token）
        finish_reason: 结束原因（最后一个 chunk 才有值）:
            - "stop": 正常结束
            - "length": 达到最大长度
            - None: 未结束
    """

    content: str
    finish_reason: str | None = None


@dataclass
class ChatResponse:
    """非流式生成的完整响应。

    Attributes:
        content: 完整的回答内容
        usage: token 使用统计（prompt_tokens, completion_tokens, total_tokens）
    """

    content: str
    usage: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """LLM 提供者抽象类。

    所有 LLM Provider 必须实现此接口。
    通过工厂模式（factory.py）根据配置返回具体实例。

    支持两种调用模式:
    - 非流式: 返回完整的 ChatResponse
    - 流式: 返回 AsyncIterator[ChatChunk]，逐个 yield
    """

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> Union[ChatResponse, AsyncIterator[ChatChunk]]:
        """聊天补全。

        Args:
            messages: 消息列表（system/user/assistant）
            stream: 是否流式返回
            temperature: 采样温度（0.0~2.0），值越大回答越随机
            max_tokens: 最大生成 token 数

        Returns:
            stream=False: 返回 ChatResponse（完整响应）
            stream=True: 返回 AsyncIterator[ChatChunk]（逐个 chunk）

        Raises:
            LLMTimeoutError: 调用超时
            LLMAuthError: API Key 无效
            LLMConnectionError: 网络错误
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称。"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """模型名称。"""
        pass
