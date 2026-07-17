<!--
Document: Architecture Design Document
Version: 1.0.0
Author: Solution Architect
Created: 2026-07-12
Updated: 2026-07-12
Status: Approved（G2 架构评审通过，Human Developer 已审批 2026-07-12）
-->

# 架构设计文档：AI 文档知识库（MVP）

## 文档元信息

| 字段 | 内容 |
|------|------|
| 文档名称 | 架构设计文档 |
| 项目名称 | AI 文档知识库（MVP） |
| 版本 | 1.0.0 |
| 作者 | Solution Architect |
| 创建日期 | 2026-07-12 |
| 状态 | Approved（G2 架构评审通过，Human Developer 已审批 2026-07-12） |
| 关联文档 | `docs/prd.md`、`docs/design-system.md`、`docs/decision-log.md` |

---

## 1. 概述

### 1.1 文档目的

本文档定义 AI 文档知识库（MVP）的系统架构，为数据库工程师、后端工程师、前端工程师、AI 工程师提供可实现的技术蓝图。涵盖架构风格、模块划分、接口设计、数据流、Provider 抽象层、SSE 方案、文本切分算法与非功能需求实现方案。

### 1.2 系统概述

AI 文档知识库是一个本地运行的前后端分离 Web 应用，通过 RAG 技术让用户上传文档后以自然语言提问获得带引用来源的 AI 回答。系统采用单体架构，后端 FastAPI + 前端 Vue3，业务数据存 MariaDB，向量数据存 Chroma，AI 能力通过 OpenAI API（可配置兼容端点）调用。

### 1.3 关键需求

| 需求 | 类型 | 优先级 | 依据 |
|------|------|--------|------|
| 文档上传与解析（4 种格式） | 功能 | P0 | PRD FR-DOC-001/002 |
| 文本切分与向量化 | 功能 | P0 | PRD FR-VEC-001/002 |
| RAG 问答（检索+LLM 生成） | 功能 | P0 | PRD FR-RAG-001~004 |
| SSE 流式输出 | 功能 | P0 | DEC-010 |
| 引用来源展示 | 功能 | P0 | DEC-004 |
| 多轮对话（4 轮上下文） | 功能 | P0 | DEC-011 |
| 聊天历史持久化 | 功能 | P0 | PRD FR-HIS-006 |
| 双 Embedding 可配置 | 功能 | P1 | DEC-002/008 |
| 单次问答 P95 < 15s | 非功能 | P0 | PRD 4.1 |
| 首 token < 3s | 非功能 | P0 | DEC-010 |
| 本地 localhost 运行 | 约束 | P0 | DEC-001 |
| 禁用 Docker | 约束 | P0 | DEC-005 |
| 后端单元测试 ≥ 80% | 非功能 | P0 | PRD 9.2 |

### 1.4 架构约束

| 编号 | 约束 | 来源 |
|------|------|------|
| C1 | 全项目禁用 Docker | DEC-005 |
| C2 | MariaDB 本地安装 | DEC-005 |
| C3 | 仅本地 localhost 运行 | DEC-001 |
| C4 | 初级开发者独立完成 | 项目定位 |
| C5 | 不引入 langchain | DEC-007 |
| C6 | Python 3.11 + FastAPI + Vue3 | DEC-007 |

---

## 2. 架构设计

### 2.1 系统上下文图

```mermaid
graph TB
    User[用户<br/>浏览器]
    App[AI 文档知识库<br/>本地应用]
    OpenAI[OpenAI API<br/>Embedding + LLM]
    HF[HuggingFace<br/>bge-m3 模型下载]

    User -->|HTTP/SSE| App
    App -->|HTTPS REST| OpenAI
    App -.->|HTTPS 下载| HF

    style User fill:#ECF5FF,stroke:#409EFF
    style App fill:#F0F9EB,stroke:#67C23A
    style OpenAI fill:#FDF6EC,stroke:#E6A23C
    style HF fill:#FDF6EC,stroke:#E6A23C
```

**说明**：
- 用户通过浏览器访问 localhost:5173（前端）与 localhost:8000（后端 API）
- 后端调用 OpenAI API 进行 Embedding 与 LLM 生成
- 本地 Embedding 模式下首次从 HuggingFace 下载 bge-m3 模型
- 除 OpenAI API 外，所有组件本地运行

### 2.2 容器架构图

```mermaid
graph LR
    subgraph 浏览器
        FE[Vue3 前端<br/>Vite Dev Server<br/>:5173]
    end

    subgraph 本地应用
        API[FastAPI 后端<br/>uvicorn<br/>:8000]
        DB[(MariaDB<br/>业务数据)]
        Chroma[(Chroma<br/>向量数据<br/>嵌入式)]
        FS[文件系统<br/>./data/uploads]
    end

    subgraph 外部服务
        OpenAI[OpenAI API]
    end

    FE -->|HTTP REST + SSE| API
    API -->|SQL| DB
    API -->|嵌入式调用| Chroma
    API -->|文件读写| FS
    API -->|HTTPS| OpenAI

    style FE fill:#ECF5FF,stroke:#409EFF
    style API fill:#F0F9EB,stroke:#67C23A
    style DB fill:#F4F4F5,stroke:#909399
    style Chroma fill:#F4F4F5,stroke:#909399
    style FS fill:#F4F4F5,stroke:#909399
    style OpenAI fill:#FDF6EC,stroke:#E6A23C
```

**说明**：
- 前端 Vue3 通过 Vite Dev Server 运行在 :5173
- 后端 FastAPI 通过 uvicorn 运行在 :8000
- MariaDB 作为独立数据库进程运行
- Chroma 以嵌入式模式运行（进程内），数据持久化到 ./data/chroma
- 上传的文件存储在 ./data/uploads
- 开发环境下前端通过 Vite proxy 转发 API 请求到后端

### 2.3 架构风格

| 属性 | 选择 | 理由 |
|------|------|------|
| 架构风格 | 单体架构（模块化） | MVP 阶段复杂度低；单用户本地运行无需微服务；初级开发者可维护 |
| 通信协议 | REST + SSE | REST 用于 CRUD；SSE 用于流式输出（DEC-010） |
| 数据存储 | 混合（MariaDB + Chroma） | MariaDB 存业务数据；Chroma 存向量数据 |
| 部署方式 | 本地脚本启动 | 禁用 Docker（DEC-005）；提供 start.sh/start.bat |
| 前后端分离 | 是 | Vue3 前端 + FastAPI 后端，独立开发 |

### 2.4 架构原则

| 原则 | 说明 | 应用 |
|------|------|------|
| 单一职责 | 每个模块/类只做一件事 | API 层只管路由；Service 层管业务；Provider 层管外部调用 |
| 依赖倒置 | 高层模块不依赖低层模块，都依赖抽象 | Service 依赖 Provider 抽象类，不依赖具体实现 |
| 开闭原则 | 对扩展开放，对修改关闭 | 新增 Embedding/LLM Provider 只需新增类，不改 Service |
| 配置外置 | 配置通过 .env 管理 | API Key、模型名、chunk_size 等可配置 |
| 渐进式复杂度 | MVP 保持简单 | 不引入消息队列、缓存、微服务 |

---

## 3. 模块设计

### 3.1 后端模块划分

```mermaid
graph TB
    subgraph API层
        DocAPI[documents.py<br/>文档管理 API]
        ChatAPI[chat.py<br/>聊天 API + SSE]
        SessionAPI[sessions.py<br/>会话管理 API]
    end

    subgraph Service层
        DocService[DocumentService<br/>文档解析+切分]
        EmbedService[EmbeddingService<br/>向量化调用]
        RAGService[RAGService<br/>检索+上下文组装]
        ChatService[ChatService<br/>聊天管理]
    end

    subgraph Provider层
        EmbedProvider[EmbeddingProvider<br/>抽象]
        LLMProvider[LLMProvider<br/>抽象]
        OpenAIEmbed[OpenAIEmbeddingProvider]
        BGEEmbed[BGEEmbeddingProvider]
        OpenAILLM[OpenAILLMProvider]
    end

    subgraph 数据层
        Models[SQLAlchemy Models]
        ChromaClient[Chroma Client]
    end

    subgraph 工具层
        Parsers[文档解析器]
        Chunker[文本切分器]
        Config[配置 Settings]
    end

    DocAPI --> DocService
    ChatAPI --> ChatService
    ChatAPI --> RAGService
    SessionAPI --> ChatService

    DocService --> Parsers
    DocService --> Chunker
    DocService --> EmbedService
    DocService --> Models
    DocService --> ChromaClient

    EmbedService --> EmbedProvider
    RAGService --> EmbedProvider
    RAGService --> ChromaClient
    RAGService --> LLMProvider
    RAGService --> Models

    ChatService --> Models

    EmbedProvider --> OpenAIEmbed
    EmbedProvider --> BGEEmbed
    LLMProvider --> OpenAILLM

    style API层 fill:#ECF5FF,stroke:#409EFF
    style Service层 fill:#F0F9EB,stroke:#67C23A
    style Provider层 fill:#FDF6EC,stroke:#E6A23C
    style 数据层 fill:#F4F4F5,stroke:#909399
    style 工具层 fill:#F4F4F5,stroke:#909399
```

### 3.2 后端目录结构

```
backend/
├── api/                         # API 路由层（FastAPI Router）
│   ├── __init__.py
│   ├── documents.py             # 文档管理 API（上传/列表/删除）
│   ├── chat.py                  # 聊天 API（SSE 流式）
│   └── sessions.py              # 会话管理 API（CRUD）
│
├── services/                    # 业务逻辑层
│   ├── __init__.py
│   ├── document_service.py      # 文档解析+切分+向量化编排
│   ├── embedding_service.py     # Embedding 调用封装
│   ├── rag_service.py           # RAG 检索+上下文组装+LLM 调用
│   └── chat_service.py          # 会话与消息管理
│
├── providers/                   # Provider 抽象层
│   ├── __init__.py
│   ├── embedding/
│   │   ├── __init__.py
│   │   ├── base.py              # EmbeddingProvider 抽象类
│   │   ├── openai_provider.py   # OpenAI text-embedding-3-small
│   │   ├── bge_provider.py      # BAAI/bge-m3 本地模型
│   │   └── factory.py           # get_embedding_provider() 工厂
│   └── llm/
│       ├── __init__.py
│       ├── base.py              # LLMProvider 抽象类
│       ├── openai_provider.py   # OpenAI gpt-4o-mini
│       └── factory.py           # get_llm_provider() 工厂
│
├── models/                      # 数据模型（SQLAlchemy 2.0）
│   ├── __init__.py
│   ├── base.py                  # declarative base
│   ├── document.py              # Document 模型
│   ├── session.py               # ChatSession 模型
│   └── message.py               # ChatMessage 模型
│
├── parsers/                     # 文档解析器
│   ├── __init__.py
│   ├── base.py                  # DocumentParser 抽象
│   ├── pdf_parser.py            # PyPDF2
│   ├── docx_parser.py           # python-docx
│   ├── markdown_parser.py       # markdown 库
│   └── txt_parser.py            # chardet 编码检测
│
├── chunkers/                    # 文本切分器
│   ├── __init__.py
│   └── recursive_chunker.py     # 递归字符切分（自实现）
│
├── config/                      # 配置
│   ├── __init__.py
│   └── settings.py              # Pydantic Settings（.env 读取）
│
├── database/                    # 数据库连接
│   ├── __init__.py
│   └── session.py               # async sessionmaker
│
├── utils/                       # 工具函数
│   ├── __init__.py
│   └── sse.py                   # SSE 事件格式化工具
│
├── tests/                       # 测试
│   ├── __init__.py
│   ├── test_document_service.py
│   ├── test_rag_service.py
│   ├── test_chunker.py
│   └── test_providers.py
│
├── .env.example                 # 环境变量模板
├── requirements.txt             # Python 依赖
└── main.py                      # FastAPI 应用入口
```

### 3.3 前端目录结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── layouts/
│   │   └── MainLayout.vue       # 主布局（顶栏+侧栏+主区）
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatArea.vue     # 对话区（消息列表）
│   │   │   ├── MessageBubble.vue# 消息气泡（用户/AI）
│   │   │   ├── ReferenceCard.vue# 引用来源卡片
│   │   │   ├── ChatInput.vue    # 输入区
│   │   │   └── StreamingCursor.vue # 流式光标
│   │   ├── document/
│   │   │   ├── DocumentList.vue # 文档列表
│   │   │   ├── DocumentItem.vue # 文档项
│   │   │   └── UploadArea.vue   # 上传区域（拖拽）
│   │   └── session/
│   │       ├── SessionList.vue  # 会话列表
│   │       └── SessionItem.vue  # 会话项
│   ├── views/
│   │   └── HomeView.vue         # 主页
│   ├── stores/
│   │   ├── chat.ts              # 聊天状态（Pinia）
│   │   ├── document.ts          # 文档状态
│   │   └── session.ts           # 会话状态
│   ├── api/
│   │   ├── request.ts           # axios 实例
│   │   ├── document.ts          # 文档 API
│   │   ├── chat.ts              # 聊天 API（含 fetch streaming）
│   │   └── session.ts           # 会话 API
│   ├── utils/
│   │   └── sse-parser.ts        # SSE 流解析工具
│   ├── router/
│   │   └── index.ts             # Vue Router
│   ├── App.vue
│   └── main.ts
├── index.html
├── vite.config.ts               # Vite 配置（含 proxy）
├── tsconfig.json
└── package.json
```

### 3.4 模块职责

| 模块 | 职责 | 主要类/文件 |
|------|------|-------------|
| API 层 | 接收 HTTP 请求，参数校验，调用 Service，返回响应 | documents.py, chat.py, sessions.py |
| Service 层 | 业务逻辑编排，协调 Provider/Model/Chroma | DocumentService, RAGService, ChatService |
| Provider 层 | 封装外部 AI 服务调用，抽象接口 | EmbeddingProvider, LLMProvider |
| 数据层 | 数据持久化 | SQLAlchemy Models, ChromaClient |
| 解析器 | 文档格式转换 | PDFParser, DocxParser, MarkdownParser, TxtParser |
| 切分器 | 文本递归切分 | RecursiveChunker |
| 配置 | 环境变量管理 | Settings |

---

## 4. Provider 抽象层设计

### 4.1 Embedding Provider UML 类图

```mermaid
classDiagram
    class EmbeddingProvider {
        <<abstract>>
        +embed(texts: List~str~) List~List~float~~
        +embed_query(text: str) List~float~
        +dimension: int*
        +name: str*
    }

    class OpenAIEmbeddingProvider {
        -client: AsyncOpenAI
        -model: str
        +embed(texts) List~List~float~~
        +embed_query(text) List~float~
        +dimension: int = 1536
        +name: str = "openai"
    }

    class BGEEmbeddingProvider {
        -model: SentenceTransformer
        +embed(texts) List~List~float~~
        +embed_query(text) List~float~
        +dimension: int = 1024
        +name: str = "bge-m3"
    }

    class EmbeddingFactory {
        +get_embedding_provider(config) EmbeddingProvider
    }

    EmbeddingProvider <|-- OpenAIEmbeddingProvider
    EmbeddingProvider <|-- BGEEmbeddingProvider
    EmbeddingFactory ..> EmbeddingProvider : creates
```

### 4.2 LLM Provider UML 类图

```mermaid
classDiagram
    class LLMProvider {
        <<abstract>>
        +chat_completion(messages, stream) Union~ChatResponse, AsyncIterator~ChatChunk~~
        +name: str*
    }

    class OpenAILLMProvider {
        -client: AsyncOpenAI
        -model: str
        +chat_completion(messages, stream) ChatResponse|AsyncIterator
        +name: str = "openai"
    }

    class LLMFactory {
        +get_llm_provider(config) LLMProvider
    }

    class Message {
        +role: str
        +content: str
    }

    class ChatResponse {
        +content: str
        +usage: dict
    }

    class ChatChunk {
        +content: str
        +finish_reason: str
    }

    LLMProvider <|-- OpenAILLMProvider
    LLMFactory ..> LLMProvider : creates
    LLMProvider ..> Message : uses
    LLMProvider ..> ChatResponse : returns
    LLMProvider ..> ChatChunk : yields
```

### 4.3 抽象类接口定义

```python
# providers/embedding/base.py
from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """Embedding 提供者抽象类"""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量"""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """生成单个查询向量"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称（用于 collection 命名）"""
        pass
```

```python
# providers/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Union
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # system / user / assistant
    content: str

@dataclass
class ChatChunk:
    content: str
    finish_reason: str | None = None

class LLMProvider(ABC):
    """LLM 提供者抽象类"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[ChatChunk]]:
        """聊天补全"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass
```

### 4.4 工厂函数

```python
# providers/embedding/factory.py
from config.settings import settings

def get_embedding_provider() -> EmbeddingProvider:
    """根据配置返回 Embedding Provider 实例"""
    provider = settings.EMBEDDING_PROVIDER  # "openai" 或 "bge"
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small"
        )
    elif provider == "bge":
        return BGEEmbeddingProvider(
            model_name="BAAI/bge-m3",
            cache_dir=settings.MODEL_CACHE_DIR
        )
    else:
        raise ValueError(f"不支持的 Embedding Provider: {provider}")
```

### 4.5 Chroma Collection 命名规则

```python
# 根据 provider name 与 dimension 命名 collection
def get_collection_name(provider: EmbeddingProvider) -> str:
    return f"kb_{provider.name}_{provider.dimension}"
    # 示例: kb_openai_1536 或 kb_bge-m3_1024
```

---

## 5. SSE 流式输出设计

### 5.1 SSE 事件格式

```
event: references
data: [{"doc_name":"RAG原理.pdf","chunk":"检索增强生成...","source_path":"/data/uploads/RAG原理.pdf","chunk_index":12}]

event: token
data: {"content":"RAG"}

event: token
data: {"content":"是"}

event: done
data: {"elapsed_ms":3200}

event: error
data: {"message":"回答生成超时","code":"LLM_TIMEOUT"}
```

### 5.2 SSE 时序图（正常流程）

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as ChatAPI
    participant RAG as RAGService
    participant V as Chroma
    participant LLM as LLMProvider

    FE->>API: POST /api/chat/messages (session_id, question)
    API->>RAG: ask(session_id, question)

    RAG->>RAG: embed_query(question)
    RAG->>V: query(embedding, top_k=5)
    V-->>RAG: chunks + metadata

    RAG->>RAG: filter(similarity >= 0.3)
    RAG->>RAG: assemble_context(system, rag, history_4rounds, question)

    RAG-->>API: references
    API-->>FE: event: references

    RAG->>LLM: chat_completion(messages, stream=True)

    loop 流式生成
        LLM-->>RAG: ChatChunk(content="R")
        RAG-->>API: chunk
        API-->>FE: event: token
    end

    LLM-->>RAG: finish
    RAG->>RAG: save_message(question, answer, references)
    RAG-->>API: done(elapsed_ms)
    API-->>FE: event: done
```

### 5.3 SSE 时序图（停止生成）

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as ChatAPI
    participant RAG as RAGService
    participant LLM as LLMProvider

    FE->>API: POST /api/chat/messages
    API->>RAG: ask(session_id, question)
    RAG-->>FE: event: references
    RAG->>LLM: stream=True

    loop 流式生成中
        LLM-->>RAG: chunk
        RAG-->>FE: event: token
    end

    FE->>FE: 用户点击"停止生成"
    FE->>API: abort fetch (关闭连接)
    API->>API: 检测连接断开 (GeneratorExit)
    API->>RAG: 取消生成
    RAG->>LLM: close stream
    RAG->>RAG: save_partial_message(已生成部分)
```

### 5.4 SSE 时序图（异常流程）

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as ChatAPI
    participant RAG as RAGService
    participant LLM as LLMProvider

    FE->>API: POST /api/chat/messages
    API->>RAG: ask(session_id, question)
    RAG-->>FE: event: references
    RAG->>LLM: stream=True

    alt LLM 超时 (>30s)
        LLM--xRAG: TimeoutError
        RAG-->>API: error("回答生成超时")
        API-->>FE: event: error
    else LLM API Key 无效
        LLM--xRAG: AuthenticationError
        RAG-->>API: error("API Key 无效")
        API-->>FE: event: error
    else 网络中断
        LLM--xRAG: ConnectionError
        RAG-->>API: error("网络中断")
        API-->>FE: event: error
    end
```

### 5.5 无相关内容处理

```mermaid
flowchart TD
    A[检索 top_k=5] --> B[过滤相似度 < 0.3]
    B --> C{有结果?}
    C -- 否 --> D[返回空引用 + 友好提示]
    D --> E[event: references 空数组]
    E --> F[event: done 无 token]
    C -- 是 --> G[正常流程]
```

### 5.6 后端 SSE 实现要点

```python
# api/chat.py 核心逻辑
from fastapi.responses import StreamingResponse

@router.post("/chat/messages")
async def send_message(request: ChatRequest):
    async def event_stream():
        try:
            # 1. 检索 + 组装上下文
            references = await rag_service.retrieve(request.question, request.session_id)
            # 2. 发送引用来源
            yield format_sse("references", references)
            # 3. 流式生成
            async for chunk in rag_service.generate(request.question, request.session_id):
                yield format_sse("token", {"content": chunk.content})
            # 4. 完成
            yield format_sse("done", {"elapsed_ms": elapsed})
        except Exception as e:
            yield format_sse("error", {"message": str(e), "code": "INTERNAL"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 5.7 前端 SSE 解析要点

```typescript
// api/chat.ts 核心逻辑
async function sendMessage(question: string, sessionId: string) {
  const response = await fetch('/api/chat/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId })
  })

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventType = line.slice(7)
        // 解析下一行 data: {...}
        // 根据 eventType 触发回调
      }
    }
  }
}
```

---

## 6. 多轮上下文管理

### 6.1 上下文组装流程

```mermaid
flowchart TD
    A[用户提问] --> B[加载会话历史]
    B --> C[截取最近 4 轮 8 条消息]
    C --> D[问题向量化]
    D --> E[Chroma 检索 top_k=5]
    E --> F[过滤相似度 < 0.3]
    F --> G[组装消息列表]

    G --> G1[1. System Prompt]
    G --> G2[2. RAG Context<br/>检索到的文档片段]
    G --> G3[3. History<br/>最近 4 轮对话]
    G --> G4[4. User Question<br/>当前问题]

    G1 --> H[发送给 LLM]
    G2 --> H
    G3 --> H
    G4 --> H
```

### 6.2 System Prompt 设计

```python
SYSTEM_PROMPT = """你是一个基于文档知识库的 AI 助手。请根据提供的参考文档片段回答用户问题。

要求：
1. 回答必须基于参考文档内容，不要编造信息
2. 如果参考文档中没有相关信息，请明确说明"未在文档库中找到相关内容"
3. 回答时使用清晰的中文
4. 如适用，使用 Markdown 格式组织回答（列表、代码块等）
5. 不要提及"参考文档"或"系统提示"等内部机制"""
```

### 6.3 上下文 Token 预算

| 组成部分 | 预估 Token | 说明 |
|----------|------------|------|
| System Prompt | ~200 | 角色定义与规则 |
| RAG 上下文 | ~2000 | top_k=5 × 500 字符 |
| 历史对话 | ~1500 | 最近 4 轮 × ~375 token |
| 当前问题 | ~100 | 用户输入 |
| 输出预留 | ~2000 | LLM 回答空间 |
| **总计** | **~6000** | 远低于 gpt-4o-mini 128K 上下文 |

### 6.4 截断策略

```python
def assemble_messages(
    question: str,
    rag_context: List[str],
    history: List[ChatMessage]
) -> List[Message]:
    messages = []

    # 1. 系统提示
    messages.append(Message(role="system", content=SYSTEM_PROMPT))

    # 2. RAG 上下文（注入到 system 消息或单独 user 消息）
    context_text = "\n\n".join([f"参考文档 {i+1}:\n{chunk}" for i, chunk in enumerate(rag_context)])
    messages.append(Message(role="system", content=f"以下是检索到的相关文档片段：\n\n{context_text}"))

    # 3. 历史对话（最近 4 轮 = 8 条消息）
    recent_history = history[-8:]  # 取最近 8 条
    for msg in recent_history:
        messages.append(Message(role=msg.role, content=msg.content))

    # 4. 当前问题
    messages.append(Message(role="user", content=question))

    return messages
```

---

## 7. 文本切分算法

### 7.1 算法设计

```mermaid
flowchart TD
    A[输入纯文本] --> B[清洗文本<br/>去除多余空白]
    B --> C{是 Markdown?}
    C -- 是 --> D[按标题优先切分]
    C -- 否 --> E[递归字符切分]
    D --> E
    E --> F[按段落分隔符切分]
    F --> G{chunk > 500?}
    G -- 是 --> H[按句子分隔符切分]
    G -- 否 --> I{chunk < 350?}
    H --> I
    I -- 是 --> J[与下一段合并]
    I -- 否 --> K[保留当前 chunk]
    J --> F
    K --> L[添加 overlap 50 字符]
    L --> M[输出 chunks 列表]
```

### 7.2 切分参数

| 参数 | 值 | 说明 |
|------|------|------|
| chunk_size | 500 字符 | 目标 chunk 长度 |
| overlap | 50 字符 | 相邻 chunk 重叠 |
| 最小 chunk | 350 字符 | 低于此值与下一段合并 |
| 段落分隔符 | `\n\n` | 优先切分点 |
| 句子分隔符 | `。！？.!?\n` | 次优切分点 |

### 7.3 实现伪代码

```python
class RecursiveChunker:
    def __init__(self, chunk_size=500, overlap=50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, is_markdown: bool = False) -> List[str]:
        # 1. 清洗
        text = self._clean(text)

        # 2. Markdown 按标题预切分
        if is_markdown:
            sections = self._split_by_headers(text)
        else:
            sections = [text]

        # 3. 递归切分每个 section
        chunks = []
        for section in sections:
            chunks.extend(self._recursive_split(section))

        # 4. 添加 overlap
        chunks = self._add_overlap(chunks)

        return chunks

    def _recursive_split(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        # 按段落切分
        paragraphs = text.split('\n\n')
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) <= self.chunk_size:
                current += "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                # 段落本身过长，按句子切分
                if len(para) > self.chunk_size:
                    chunks.extend(self._split_by_sentences(para))
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        import re
        sentences = re.split(r'[。！？.!?\n]', text)
        # ... 合并短句至 chunk_size
```

---

## 8. 数据流设计

### 8.1 文档上传数据流

```mermaid
flowchart LR
    A[用户上传文件] --> B[API 层接收]
    B --> C[DocumentService]
    C --> D[Parser 解析为文本]
    D --> E[Chunker 切分]
    E --> F[EmbeddingProvider 向量化]
    F --> G[Chroma 存储向量]
    C --> H[MariaDB 存储元数据]
    C --> I[文件系统存储原文件]
```

### 8.2 RAG 问答数据流

```mermaid
flowchart LR
    A[用户提问] --> B[API 层接收]
    B --> C[RAGService]
    C --> D[EmbeddingProvider 问题向量化]
    D --> E[Chroma 检索 top_k=5]
    E --> F[组装上下文]
    F --> G[LLMProvider 流式生成]
    G --> H[SSE 返回前端]
    C --> I[MariaDB 保存消息]
```

### 8.3 数据存储分配

| 数据类型 | 存储位置 | 说明 |
|----------|----------|------|
| 文档元数据 | MariaDB `documents` 表 | 文件名、类型、大小、切片数、状态 |
| 会话数据 | MariaDB `chat_sessions` 表 | 会话标题、消息数、时间 |
| 消息数据 | MariaDB `chat_messages` 表 | 问答内容、引用 JSON、耗时 |
| 向量数据 | Chroma `kb_{provider}_{dim}` | chunk 文本、embedding、metadata |
| 原文件 | 文件系统 `./data/uploads/` | 上传的原始文件 |

---

## 9. API 接口设计

### 9.1 API 总览

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 文档 | POST | `/api/documents/upload` | 上传文档 |
| 文档 | GET | `/api/documents` | 文档列表（分页） |
| 文档 | DELETE | `/api/documents/{id}` | 删除文档 |
| 会话 | POST | `/api/chat/sessions` | 新建会话 |
| 会话 | GET | `/api/chat/sessions` | 会话列表 |
| 会话 | DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| 会话 | DELETE | `/api/chat/sessions` | 清空所有会话 |
| 消息 | GET | `/api/chat/sessions/{id}/messages` | 会话消息列表 |
| 消息 | POST | `/api/chat/messages` | 发送消息（SSE 流式） |
| 配置 | GET | `/api/config` | 获取当前配置 |
| 配置 | PUT | `/api/config/embedding-provider` | 切换 Embedding Provider |

### 9.2 核心 API：发送消息（SSE）

```yaml
POST /api/chat/messages
Content-Type: application/json
Accept: text/event-stream

Request:
{
  "session_id": "uuid",
  "question": "什么是 RAG？"
}

Response (SSE):
event: references
data: [{"doc_name":"RAG原理.pdf","chunk":"...","source_path":"..."}]

event: token
data: {"content":"RAG"}

event: token
data: {"content":"是"}

event: done
data: {"elapsed_ms":3200}

Error Response:
event: error
data: {"message":"回答生成超时","code":"LLM_TIMEOUT"}
```

### 9.3 其他 API 规范

```yaml
# 上传文档
POST /api/documents/upload
Content-Type: multipart/form-data
Request: file (File), file (File), ...
Response: 201
{
  "documents": [
    {"id": "uuid", "filename": "doc.pdf", "status": "processing"}
  ]
}

# 文档列表
GET /api/documents?page=1&size=20
Response: 200
{
  "items": [{"id":"...","filename":"...","file_type":"pdf","file_size":2300000,"chunk_count":96,"status":"completed","created_at":"..."}],
  "total": 12,
  "page": 1,
  "size": 20
}

# 删除文档
DELETE /api/documents/{id}
Response: 204

# 新建会话
POST /api/chat/sessions
Response: 201
{"id": "uuid", "title": "新会话", "created_at": "..."}

# 会话消息列表
GET /api/chat/sessions/{id}/messages
Response: 200
{
  "messages": [
    {"id":"...","role":"user","content":"什么是 RAG？","created_at":"..."},
    {"id":"...","role":"assistant","content":"RAG 是...","references":[...],"elapsed_ms":3200,"created_at":"..."}
  ]
}
```

---

## 10. 非功能需求实现方案

### 10.1 性能

| 需求 | 方案 | 实现位置 |
|------|------|----------|
| P95 < 15s | LLM 流式输出；检索优化（top_k=5） | RAGService |
| 首 token < 3s | 检索先行，快速返回 references；LLM stream=True | ChatAPI |
| API < 500ms | MariaDB 索引优化；Chroma 嵌入式无网络开销 | 各 API |
| 页面 < 3s | Vite 构建；路由懒加载；骨架屏 | 前端 |

### 10.2 安全

| 需求 | 方案 |
|------|------|
| API Key 管理 | .env + Pydantic Settings；.gitignore 排除 .env |
| 文件上传安全 | 校验扩展名 + 魔数；大小限制 20MB；路径不穿越 |
| SQL 注入防护 | SQLAlchemy 参数化查询 |
| XSS 防护 | 前端 v-text 而非 v-html；Markdown 渲染用 DOMPurify |
| 本地运行 | uvicorn 绑定 127.0.0.1 |

### 10.3 可扩展性

| 扩展点 | 方案 |
|--------|------|
| 新增 Embedding Provider | 继承 EmbeddingProvider，在 factory 注册 |
| 新增 LLM Provider | 继承 LLMProvider，在 factory 注册 |
| 新增文档格式 | 继承 DocumentParser，在 parser factory 注册 |
| 多知识库 | Chroma collection 隔隔（V2） |

### 10.4 可维护性

| 需求 | 方案 |
|------|------|
| 代码规范 | PEP 8 + Black + Ruff |
| 类型检查 | Python type hints + mypy |
| 单元测试 | pytest，覆盖率 ≥ 80% |
| API 文档 | FastAPI 自动生成 OpenAPI /docs |
| 配置管理 | .env + Settings 类 |

---

## 11. 配置设计

### 11.1 环境变量（.env）

```env
# 应用
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=true

# MariaDB
DATABASE_URL=mysql+asyncmy://root:password@127.0.0.1:3306/ai_knowledge_base

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Embedding Provider (openai / bge)
EMBEDDING_PROVIDER=openai

# 本地模型（bge-m3）
MODEL_CACHE_DIR=./data/models

# Chroma
CHROMA_PERSIST_DIR=./data/chroma

# RAG 参数
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
SIMILARITY_THRESHOLD=0.3
MAX_HISTORY_ROUNDS=4

# 文件上传
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE_MB=20
MAX_DOCUMENTS=100
```

### 11.2 配置类

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DATABASE_URL: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_PROVIDER: str = "openai"
    MODEL_CACHE_DIR: str = "./data/models"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    MAX_HISTORY_ROUNDS: int = 4
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE_MB: int = 20
    MAX_DOCUMENTS: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 12. 部署架构

### 12.1 本地启动方案

```mermaid
graph TB
    subgraph 启动流程
        A[start.sh / start.bat] --> B[检查 Python 3.11+]
        B --> C[检查 Node.js 18+]
        C --> D[检查 MariaDB 运行]
        D --> E[后端: pip install]
        E --> F[后端: alembic migrate]
        F --> G[后端: uvicorn main:app]
        G --> H[前端: npm install]
        H --> I[前端: npm run dev]
    end
```

### 12.2 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 Vite | 5173 | 开发服务器 |
| 后端 FastAPI | 8000 | API 服务 |
| MariaDB | 3306 | 数据库 |

### 12.3 Vite Proxy 配置

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
```

---

## 13. 架构决策记录

### 13.1 本文档新增决策

| 决策编号 | 标题 | 状态 |
|----------|------|------|
| DEC-20260712-014 | 采用模块化单体架构 | Accepted |
| DEC-20260712-015 | 前后端通过 Vite Proxy 通信 | Accepted |
| DEC-20260712-016 | 文本切分采用递归字符切分算法 | Accepted |

### 13.2 DEC-014: 模块化单体架构

| 字段 | 内容 |
|------|------|
| 决策编号 | DEC-20260712-014 |
| 决策者 | Solution Architect |
| 决策类型 | 架构决策 |
| 影响范围 | 整个系统 |

**背景**：MVP 阶段需在复杂度与可维护性间平衡。微服务对本地单用户场景过度设计。

**决策**：采用模块化单体架构，后端按 API/Service/Provider/Data 分层，模块间通过接口调用。

**理由**：1) 本地单用户无需独立扩展；2) 初级开发者可维护；3) 无分布式事务复杂度；4) 未来可拆分为微服务。

### 13.3 DEC-015: Vite Proxy 通信

**决策**：开发环境前端通过 Vite Proxy 转发 /api 请求到后端，避免 CORS 问题。

**理由**：前后端分离开发时，Vite Proxy 是最简单的跨域解决方案，无需配置 CORS 中间件。

### 13.4 DEC-016: 递归字符切分算法

**决策**：自实现递归字符切分，按段落→句子→字符三级切分，chunk_size=500，overlap=50。

**理由**：不引入 langchain（DEC-007）；算法简单可控（~100 行）；参考 langchain RecursiveCharacterTextSplitter 逻辑。

---

## 14. 架构检查清单

- [x] 系统架构图（上下文图 + 容器图）
- [x] 架构风格与原则明确
- [x] 后端模块划分（5 层 + 目录结构）
- [x] 前端组件结构（3 大组件组 + stores）
- [x] Provider 抽象层 UML 类图（Embedding + LLM）
- [x] SSE 时序图（正常 + 停止 + 异常 + 无内容）
- [x] 多轮上下文组装流程图
- [x] 文本切分算法设计
- [x] 数据流设计（上传流 + 问答流）
- [x] API 接口设计（11 个接口）
- [x] 非功能需求实现方案（性能/安全/扩展/维护）
- [x] 配置设计（.env + Settings 类）
- [x] 部署架构（本地启动 + 端口 + Proxy）
- [x] 架构决策记录（DEC-014/015/016）
- [x] 无占位符/省略号

---

## 附录

### A. 参考文档

| 文档 | 路径 |
|------|------|
| PRD | `docs/prd.md` |
| 设计系统 | `docs/design-system.md` |
| 用户流程 | `docs/user-flows.md` |
| 决策日志 | `docs/decision-log.md`（DEC-001~016） |

### B. 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，完整架构设计 | Solution Architect |
