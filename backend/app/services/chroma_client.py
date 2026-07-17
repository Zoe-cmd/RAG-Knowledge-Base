"""
Chroma 向量数据库客户端封装。

提供 collection 管理、向量增删查的统一接口。
采用嵌入式持久化模式，数据存储在 ./data/chroma 目录。

Collection 命名规则: kb_{provider}_{dimension}（DEC-008）
距离度量: cosine（余弦相似度）
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, List

import chromadb
from chromadb.api.models.Collection import Collection

from app.config.settings import get_settings
from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import get_collection_name


@lru_cache(maxsize=1)
def get_chroma_client() -> "ChromaClient":
    """获取 Chroma 客户端单例。

    Returns:
        ChromaClient 实例
    """
    return ChromaClient()


class ChromaClient:
    """Chroma 向量数据库客户端。

    封装 chromadb.PersistentClient，提供:
    - collection 管理（按 Provider 获取/创建）
    - 向量批量添加
    - 相似度检索
    - 按文档 ID 删除向量
    - 统计向量数量

    所有操作均为同步（Chroma 嵌入式模式本身是同步的），
    Service 层在异步上下文中通过 asyncio.to_thread 调用。
    """

    def __init__(self) -> None:
        """初始化 Chroma 持久化客户端。"""
        settings = get_settings()
        # 显式禁用 chromadb 遥测上报
        # 原因：chromadb 0.5.0 与新版 posthog 不兼容，
        #       会报 "capture() takes 1 positional argument but 3 were given"
        #       ANONYMIZED_TELEMETRY 环境变量在 0.5.0 中不生效，需通过 Settings 禁用
        self._client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_path),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )

    def get_collection(self, provider: EmbeddingProvider) -> Collection:
        """获取或创建对应 Provider 的 collection。

        Collection 命名: kb_{provider_name}_{dimension}
        距离度量: cosine（余弦相似度）

        Args:
            provider: Embedding Provider 实例

        Returns:
            Chroma Collection 对象
        """
        collection_name = get_collection_name(provider)
        return self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_vectors(
        self,
        provider: EmbeddingProvider,
        doc_id: str,
        doc_name: str,
        source_path: str,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> int:
        """批量添加文档向量。

        每个 chunk 生成一个向量，id 格式为 {doc_id}_{chunk_index}。
        metadata 包含 doc_id、doc_name、chunk_index、source_path、char_count、created_at。

        Args:
            provider: Embedding Provider 实例
            doc_id: 文档 ID（UUID 字符串）
            doc_name: 文档文件名
            source_path: 源文件路径
            chunks: 文本切片列表
            embeddings: 与 chunks 对应的向量列表

        Returns:
            添加的向量数量
        """
        if not chunks:
            return 0

        collection = self.get_collection(provider)
        now = datetime.now(timezone.utc).isoformat()

        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "chunk_index": i,
                "source_path": source_path,
                "char_count": len(chunk),
                "created_at": now,
            }
            for i, chunk in enumerate(chunks)
        ]

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def query(
        self,
        provider: EmbeddingProvider,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[dict[str, Any]]:
        """向量相似度检索。

        Args:
            provider: Embedding Provider 实例
            query_embedding: 查询向量
            top_k: 返回的最相似结果数量

        Returns:
            检索结果列表，每项含:
            - id: 向量 ID
            - document: 文本内容
            - metadata: 元数据
            - distance: 余弦距离（越小越相似）
            - similarity: 余弦相似度（1 - distance/2，越大越相似）
        """
        collection = self.get_collection(provider)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 解析 Chroma 返回的嵌套结构
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        parsed: List[dict[str, Any]] = []
        for i in range(len(ids)):
            distance = distances[i] if i < len(distances) else 1.0
            # Chroma cosine distance 范围 [0, 2]，相似度 = 1 - distance/2
            similarity = 1.0 - (distance / 2.0)
            parsed.append(
                {
                    "id": ids[i],
                    "document": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distance,
                    "similarity": similarity,
                }
            )
        return parsed

    def delete_by_doc_id(
        self, provider: EmbeddingProvider, doc_id: str
    ) -> None:
        """删除指定文档的所有向量。

        文档删除时调用，确保 Chroma 与 MariaDB 数据一致。

        Args:
            provider: Embedding Provider 实例
            doc_id: 文档 ID（UUID 字符串）
        """
        collection = self.get_collection(provider)
        collection.delete(where={"doc_id": doc_id})

    def count_by_doc_id(
        self, provider: EmbeddingProvider, doc_id: str
    ) -> int:
        """统计指定文档的向量数量。

        Args:
            provider: Embedding Provider 实例
            doc_id: 文档 ID（UUID 字符串）

        Returns:
            向量数量
        """
        collection = self.get_collection(provider)
        # chromadb 的 count() 不支持 where 参数，
        # 使用 get(where=..., include=[]) 获取 id 数量
        result = collection.get(where={"doc_id": doc_id}, include=[])
        ids = result.get("ids", [])
        return len(ids)

    def count_total(self, provider: EmbeddingProvider) -> int:
        """统计 collection 中向量总数。

        Args:
            provider: Embedding Provider 实例

        Returns:
            向量总数
        """
        collection = self.get_collection(provider)
        return collection.count()

    def collection_exists(self, provider: EmbeddingProvider) -> bool:
        """检查 Provider 对应的 collection 是否存在。

        Args:
            provider: Embedding Provider 实例

        Returns:
            collection 是否存在
        """
        collection_name = get_collection_name(provider)
        collections = self._client.list_collections()
        # 兼容不同 chromadb 版本返回类型
        names = [
            c.name if hasattr(c, "name") else c
            for c in collections
        ]
        return collection_name in names
