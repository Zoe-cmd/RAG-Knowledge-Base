"""
Embedding Provider 抽象基类。

定义统一的 Embedding 调用接口，支持不同 Provider（OpenAI、BGE）的实现。
依赖倒置：Service 层依赖此抽象，不依赖具体实现。
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Embedding 提供者抽象类。

    所有 Embedding Provider 必须实现此接口。
    通过工厂模式（factory.py）根据配置返回具体实例。

    属性:
        dimension: 向量维度（用于 Chroma collection 命名）
        name: Provider 名称（用于 Chroma collection 命名）
    """

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量。

        用于文档向量化场景，将多个文本片段批量转换为向量。

        Args:
            texts: 文本列表

        Returns:
            向量列表，每个元素是与输入文本对应的浮点数列表

        Raises:
            EmbeddingError: 向量化失败时抛出
        """
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """生成单个查询向量。

        用于 RAG 问答场景，将用户问题转换为向量用于检索。
        与 embed() 分离是因为查询向量与文档向量的生成方式可能不同
        （如某些模型有 query/passage 区分）。

        Args:
            text: 查询文本

        Returns:
            查询向量（浮点数列表）

        Raises:
            EmbeddingError: 向量化失败时抛出
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度。

        用于 Chroma collection 命名规则: kb_{name}_{dimension}
        OpenAI text-embedding-3-small: 1536
        BGE bge-m3: 1024
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称。

        用于 Chroma collection 命名规则: kb_{name}_{dimension}
        OpenAI: "openai"
        BGE: "bge"
        """
        pass
