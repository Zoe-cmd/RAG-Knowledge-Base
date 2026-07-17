<!--
Document: Handoff
Phase: Phase 2（后端开发） → Phase 3（前端与 AI）
From: Backend Engineer
To: Frontend Engineer, AI Engineer
-->

# Handoff: Phase 2（后端开发） → Phase 3（前端与 AI）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-007 |
| 交接日期 | 2026-07-12 |
| 交接方 | Backend Engineer |
| 接收方 | Frontend Engineer, AI Engineer |
| 交接阶段 | Phase 2（后端开发） → Phase 3（前端与 AI） |
| 交接状态 | Ready |

## 交接摘要

Phase 2 后端开发阶段已完成。后端工程师基于架构文档、数据库 Schema 与 API 规范，实现了完整的后端 API 服务，包含 11 个 API 端点、SSE 流式问答、文档处理流水线、RAG 检索管线、多轮上下文管理与统一错误处理。

关键交付成果：
- **11 个 API 端点**：文档上传/列表/删除/统计、会话 CRUD/消息列表、SSE 流式问答、配置查询/Provider 切换
- **架构分层**：API → Service → Provider → Data，模块化单体设计
- **SSE 流式输出**：references / token / done / error 四类事件，支持客户端中断保存部分内容
- **Provider 抽象层**：Embedding（OpenAI 1536 维 + BGE bge-m3 1024 维）与 LLM（OpenAI gpt-4o-mini），工厂模式 + 可配置
- **RAG 检索管线**：top_k=5，相似度阈值 0.3，无 rerank（MVP 简化）
- **DEC-011 多轮上下文**：保留最近 4 轮（8 条消息），超出截断
- **DEC-016 递归字符切分**：chunk_size=500，overlap=50，Markdown 按标题优先切分
- **文档处理流水线**：解析 → 切分 → 向量化 → Chroma 存储 → MariaDB 元数据更新
- **文档删除同步**：Chroma 向量删除 → MariaDB 软删除 → 文件系统删除
- **168 个单元测试**，覆盖率 80.51%

前端工程师与 AI 工程师可基于本文档与 `docs/api-spec.md` 并行启动开发。

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| API 规范文档 v1.0.0 | 文档 | docs/api-spec.md | 完成 |
| 后端应用代码 | 代码 | backend/app/ | 完成 |
| 单元测试代码 | 代码 | backend/tests/ | 完成（168 个用例，覆盖率 80.51%） |
| 依赖清单 | 配置 | backend/requirements.txt | 完成 |
| 测试配置 | 配置 | backend/pytest.ini | 完成 |
| 环境变量模板 | 配置 | backend/.env.example | 完成 |
| 数据库初始化脚本 | 脚本 | backend/database/init.sql | 完成 |
| 架构设计文档 v1.0.0 | 文档 | docs/architecture.md | Approved |
| 数据库 Schema 文档 v1.0.0 | 文档 | docs/database-schema.md | 完成 |
| 决策日志 | 文档 | docs/decision-log.md | 已更新（16 条决策） |
| DB→Backend 交接 | 文档 | docs/handoffs/handoff-db-to-backend.md | Confirmed |

## 后端目录结构

```
backend/
├── app/
│   ├── api/                    # API 路由层
│   │   ├── documents.py        # 文档上传/列表/删除/统计
│   │   ├── sessions.py         # 会话 CRUD/消息列表
│   │   ├── chat.py             # SSE 流式问答
│   │   ├── config.py           # 配置查询/Provider 切换
│   │   └── __init__.py
│   ├── chunkers/               # 文本切分
│   │   └── recursive_chunker.py  # DEC-016 递归字符切分
│   ├── config/
│   │   └── settings.py         # Pydantic Settings 配置
│   ├── database/
│   │   └── session.py          # 异步 DB Session 管理
│   ├── models/                 # SQLAlchemy 2.0 模型
│   │   ├── document.py
│   │   ├── session.py
│   │   ├── message.py
│   │   └── base.py
│   ├── parsers/                # 文档解析器
│   │   ├── pdf_parser.py       # PDF（扫描件检测）
│   │   ├── docx_parser.py      # Word
│   │   ├── markdown_parser.py  # Markdown
│   │   ├── txt_parser.py       # TXT（自动编码检测）
│   │   └── factory.py          # 解析器工厂
│   ├── providers/              # AI Provider 抽象层
│   │   ├── embedding/          # Embedding Provider
│   │   │   ├── base.py         # ABC
│   │   │   ├── openai_provider.py  # OpenAI 1536 维
│   │   │   ├── bge_provider.py     # BGE bge-m3 1024 维
│   │   │   └── factory.py
│   │   └── llm/                # LLM Provider
│   │       ├── base.py         # ABC（Message/ChatChunk/ChatResponse）
│   │       ├── openai_provider.py  # gpt-4o-mini
│   │       └── factory.py
│   ├── services/               # 业务服务层
│   │   ├── chroma_client.py    # Chroma 向量库封装
│   │   ├── embedding_service.py    # Embedding 服务
│   │   ├── document_service.py     # 文档处理流水线
│   │   ├── rag_service.py      # RAG 检索 + 流式回答
│   │   ├── chat_service.py     # 会话/消息管理
│   │   └── prompt_template.py  # System Prompt + 上下文组装
│   ├── utils/                  # 工具层
│   │   ├── response.py         # 统一响应格式
│   │   ├── exceptions.py       # 统一异常处理
│   │   └── sse.py              # SSE 事件格式化
│   └── main.py                 # FastAPI 应用入口
├── database/
│   └── init.sql                # 数据库初始化脚本
├── tests/                      # 单元测试（168 个）
├── requirements.txt
├── pytest.ini
└── .env.example
```

## 关键决策（对前端与 AI 开发的影响）

| 决策编号 | 决策标题 | 对前端开发的影响 | 对 AI 开发的影响 |
|----------|----------|------------------|------------------|
| DEC-001 | 本地 localhost 运行，无认证 | 无需实现登录/鉴权 UI；API Base URL 为 `http://127.0.0.1:8000/api` | 无需处理认证逻辑 |
| DEC-007 | 禁用 LangChain | - | RAG 管线全自研，已实现于 `rag_service.py` |
| DEC-010 | SSE 流式输出 | 须用 fetch + ReadableStream 接收 SSE（详见第 6 节） | LLM Provider 已封装流式接口 |
| DEC-011 | 多轮上下文截断（4 轮） | 前端无需截断，后端自动处理 | 已在 `chat_service.get_recent_history()` 实现 |
| DEC-013 | 错误码体系简化 | 错误响应格式统一（详见第 5 节） | - |
| DEC-015 | CORS 通过 Vite Proxy 规避 | **前端开发用 Vite Proxy 代理 `/api` 到后端**，生产环境无 CORS 问题 | - |
| DEC-016 | 递归字符切分 | - | 已实现于 `recursive_chunker.py`，参数可配置 |

## API 端点清单

### 完整端点总览

| # | 方法 | 路径 | 说明 | 响应类型 | 状态码 |
|---|------|------|------|----------|--------|
| 1 | POST | `/api/documents/upload` | 上传文档（批量） | JSON | 201 |
| 2 | GET | `/api/documents` | 文档列表（分页） | JSON | 200 |
| 3 | DELETE | `/api/documents/{id}` | 删除文档 | 204 | 204 |
| 4 | GET | `/api/documents/stats` | 知识库统计 | JSON | 200 |
| 5 | POST | `/api/chat/sessions` | 新建会话 | JSON | 201 |
| 6 | GET | `/api/chat/sessions` | 会话列表 | JSON | 200 |
| 7 | DELETE | `/api/chat/sessions/{id}` | 删除单个会话 | 204 | 204 |
| 8 | DELETE | `/api/chat/sessions` | 清空所有会话 | JSON | 200 |
| 9 | GET | `/api/chat/sessions/{id}/messages` | 会话消息列表 | JSON | 200 |
| 10 | POST | `/api/chat/messages` | 发送消息（SSE 流式） | SSE | 200 |
| 11 | GET | `/api/config` | 获取配置与统计 | JSON | 200 |

> **注意**：端点 4 `/api/documents/stats` 与端点 11 `/api/config` 均返回统计数据，前者侧重文档维度，后者侧重全局配置。完整请求/响应格式详见 `docs/api-spec.md`。

### 关键端点说明

#### 1. 文档上传（POST /api/documents/upload）

- **Content-Type**: `multipart/form-data`
- **请求参数**: `files`（File[]，支持批量）
- **业务规则**:
  - 文件类型：pdf / docx / md / txt
  - 单文件 ≤ 20MB
  - 文档总数 < 100
  - 扫描件 PDF 返回 422
  - 允许同名上传，不覆盖
- **响应**：`data.documents`（成功列表）+ `data.failed`（失败列表）

#### 2. SSE 流式问答（POST /api/chat/messages）

- **Content-Type**: `application/json`
- **Accept**: `text/event-stream`
- **请求体**:
  ```json
  {
    "session_id": "UUID",
    "question": "1-2000 字符"
  }
  ```
- **响应**：SSE 事件流（详见第 6 节）

#### 3. 文档删除（DELETE /api/documents/{id}）

- **删除流程**：Chroma 向量删除 → MariaDB 软删除 → 文件系统删除
- **响应**：204 No Content（无响应体）

## 统一响应格式

### 成功响应（单资源）

```json
{
  "data": { ... },
  "meta": {
    "requestId": "uuid"
  }
}
```

### 成功响应（集合 + 分页）

```json
{
  "data": [ ... ],
  "meta": {
    "requestId": "uuid",
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 100,
      "totalPages": 5
    }
  }
}
```

### 错误响应

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "人类可读的错误消息",
    "details": []
  },
  "meta": {
    "requestId": "uuid"
  }
}
```

> **注意**：SSE 流式端点（POST /api/chat/messages）不使用上述 JSON 格式，使用 SSE 事件流（详见第 6 节）。SSE 错误通过 `error` 事件传递，不返回 HTTP 错误响应体。

## 错误码体系

| 错误码 | HTTP 状态码 | 说明 | 前端处理建议 |
|--------|-------------|------|--------------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 | 表单校验提示 |
| DOCUMENT_NOT_FOUND | 404 | 文档不存在 | 刷新文档列表 |
| SESSION_NOT_FOUND | 404 | 会话不存在 | 刷新会话列表 |
| DOCUMENT_LIMIT_EXCEEDED | 409 | 文档数已达上限 100 | 提示用户删除旧文档 |
| FILE_TOO_LARGE | 413 | 文件超过 20MB | 上传前前端预校验 |
| UNSUPPORTED_FILE_TYPE | 415 | 不支持的文件类型 | 上传前前端预校验 |
| SCANNED_PDF | 422 | 该 PDF 为扫描件 | 友好提示需 OCR |
| REINDEX_REQUIRED | 422 | 切换需重建索引 | 提示用户并触发重建 |
| LLM_TIMEOUT | SSE error | LLM 调用超时 | 提示重试 |
| LLM_AUTH_ERROR | SSE error | API Key 无效 | 提示检查 .env 配置 |
| LLM_CONNECTION_ERROR | SSE error | 网络中断 | 提示检查网络 |
| EMBEDDING_ERROR | SSE error | 问题向量化失败 | 提示重试 |
| INTERNAL_ERROR | 500 | 服务器内部错误 | 通用错误提示 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 | 提示检查后端服务 |

> **注意**：FastAPI 的 Pydantic 请求体校验失败返回 **422**（非 400），响应体为 FastAPI 标准格式（非本项目统一格式），前端需兼容两种 422 响应结构。

## SSE 事件协议规范

### 事件格式

```
event: {event_type}
data: {json_data}

```

> 每个 SSE 事件由 `event:` 行、`data:` 行和一个空行（`\n\n`）组成。JSON 序列化使用 `ensure_ascii=False`，中文内容原样输出。

### 事件类型

#### 事件 1: references（引用来源）

在流式回答开始前发送，包含检索到的文档片段引用。

```
event: references
data: [{"doc_id":"doc-1","doc_name":"RAG原理.pdf","chunk":"RAG 是...","source_path":"uploads/2026/07/doc-1.pdf","chunk_index":3,"similarity":0.87}]

```

**data 字段**：JSON 数组，每个元素结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档 ID |
| doc_name | string | 文档文件名 |
| chunk | string | 引用的文本片段内容 |
| source_path | string | 源文件路径 |
| chunk_index | int | 切片索引 |
| similarity | float | 相似度得分（0.0~1.0） |

**空结果处理**（FR-RAG-008）：当检索结果全部低于相似度阈值时，发送空数组 `data: []`，前端应提示"未在文档库中找到相关内容"。

#### 事件 2: token（流式 token）

LLM 生成的回答逐 token 返回。

```
event: token
data: {"content":"RAG"}

```

#### 事件 3: done（完成）

回答生成完成，包含耗时与消息 ID。

```
event: done
data: {"message_id":"msg-2","elapsed_ms":3200}

```

#### 事件 4: error（错误）

发生错误时发送，流式连接随后关闭。

```
event: error
data: {"message":"回答生成超时","code":"LLM_TIMEOUT"}

```

### SSE 响应头

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### 客户端中断处理

前端通过 `AbortController` 中断 fetch 连接后，后端检测到 `GeneratorExit` 会：
1. 关闭 LLM stream
2. 保存已生成的部分内容为 assistant 消息（FR-RAG-007）
3. 更新会话统计

## 前端集成指引

### 1. 开发环境配置

#### Vite Proxy 配置（DEC-015）

前端开发时通过 Vite Proxy 代理 API 请求到后端，规避 CORS：

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

#### API Base URL

- 开发环境：`/api`（通过 Vite Proxy 代理）
- 生产环境：`http://127.0.0.1:8000/api`（本地部署，无 CORS 问题）

### 2. API 调用层建议

#### axios 封装

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => response.data,  // 直接返回 data
  (error) => {
    const errData = error.response?.data
    if (errData?.error) {
      // 本项目统一错误格式
      return Promise.reject(errData.error)
    }
    // FastAPI 422 校验错误格式
    if (errData?.detail) {
      return Promise.reject({
        code: 'VALIDATION_ERROR',
        message: errData.detail.map(d => d.msg).join('; '),
        details: errData.detail,
      })
    }
    return Promise.reject({
      code: 'NETWORK_ERROR',
      message: '网络错误，请检查后端服务',
    })
  }
)
```

### 3. SSE 流式接收

#### fetch + ReadableStream 实现

```javascript
async function streamChat(sessionId, question, callbacks) {
  const response = await fetch('/api/chat/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({ session_id: sessionId, question }),
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()  // 保留不完整的行

    let currentEvent = null
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7)
      } else if (line.startsWith('data: ') && currentEvent) {
        const data = JSON.parse(line.slice(6))
        switch (currentEvent) {
          case 'references':
            callbacks.onReferences(data)
            break
          case 'token':
            callbacks.onToken(data.content)
            break
          case 'done':
            callbacks.onDone(data)
            break
          case 'error':
            callbacks.onError(data)
            break
        }
        currentEvent = null
      }
    }
  }
}

// 中断生成
const controller = new AbortController()
// 在 fetch 配置中添加: signal: controller.signal
// 调用 controller.abort() 中断
```

#### EventSource 不可用说明

由于 SSE 问答端点使用 **POST** 方法，浏览器原生 `EventSource` 仅支持 GET，因此**必须使用 fetch + ReadableStream** 方案接收 SSE 流。

### 4. 关键交互状态

| 状态 | 触发 | 前端表现 |
|------|------|----------|
| 上传中 | POST /api/documents/upload | 进度条 / Loading |
| 解析中 | 文档 status=processing | 轮询文档列表或状态 |
| 解析失败 | 文档 status=failed | 显示 error_message |
| 流式回答中 | SSE token 事件 | 逐字渲染 + 打字机效果 |
| 无引用内容 | SSE references=[] | 提示"未在文档库中找到相关内容" |
| 客户端中断 | AbortController.abort() | 停止渲染，保留已生成内容 |

## AI 工程师指引

### 1. 已实现的 AI 功能

后端已完整实现 AI 核心功能，AI 工程师的主要工作是**验证、调优与补充文档**，而非从零开发。

#### 1.1 Embedding Provider 抽象层

- **位置**：`backend/app/providers/embedding/`
- **已实现**：
  - `base.py`：`EmbeddingProvider` ABC，定义 `embed_documents()` / `embed_query()` / `name` / `dimension`
  - `openai_provider.py`：OpenAI text-embedding-3-small，1536 维
  - `bge_provider.py`：BGE bge-m3，1024 维（本地模型，首次加载需下载）
  - `factory.py`：工厂模式，根据配置返回 Provider 实例（`@lru_cache` 单例）
- **配置**：`.env` 中 `EMBEDDING_PROVIDER=openai|bge`

#### 1.2 LLM Provider 抽象层

- **位置**：`backend/app/providers/llm/`
- **已实现**：
  - `base.py`：`LLMProvider` ABC，定义 `chat_completion(stream)` / `name` / `model`；`Message` / `ChatChunk` / `ChatResponse` 数据类
  - `openai_provider.py`：gpt-4o-mini，支持流式与非流式，`base_url` 可配置兼容端点
  - `factory.py`：工厂模式（`@lru_cache` 单例）
- **配置**：`.env` 中 `LLM_MODEL=gpt-4o-mini`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`

#### 1.3 RAG 检索管线

- **位置**：`backend/app/services/rag_service.py`
- **参数**（可在 `.env` 配置）：
  - `TOP_K=5`：检索 top 5 相关片段
  - `SIMILARITY_THRESHOLD=0.3`：相似度阈值，低于此值的片段过滤
  - 无 rerank（MVP 简化）
- **流程**：
  1. 问题向量化（`EmbeddingProvider.embed_query`）
  2. Chroma 检索 top_k=5
  3. 相似度阈值过滤（`1.0 - distance/2.0 > threshold`）
  4. 无结果时返回空引用
  5. 有结果时组装上下文 → LLM 流式生成

#### 1.4 Prompt 模板

- **位置**：`backend/app/services/prompt_template.py`
- **System Prompt**：已定义 RAG 回答规则（基于文档内容回答、无法回答时明确说明、引用来源编号）
- **上下文组装顺序**：System Prompt → RAG Context（system role）→ History（多轮）→ Question
- **上下文格式**：`【资料N】\n{text}`，单片段超过 500 字符截断并加 `...`

#### 1.5 文本切分

- **位置**：`backend/app/chunkers/recursive_chunker.py`
- **算法**：DEC-016 递归字符切分（无 langchain 依赖）
- **参数**：`chunk_size=500`，`overlap=50`
- **切分优先级**：段落 → 换行 → 句号 → 逗号 → 空格 → 字符

### 2. AI 工程师待办事项

| 事项 | 说明 | 优先级 |
|------|------|--------|
| 验证 RAG 闭环 | 上传文档 → 提问 → 验证引用来源与回答质量 | P0 |
| Prompt 调优 | 根据实际效果调整 System Prompt 与上下文格式 | P1 |
| 超时与重试机制 | 检查 LLM/Embedding 调用的超时配置（当前 timeout=30s, stream_timeout=60s） | P1 |
| 输出验证与过滤 | 检查 LLM 输出是否需要额外过滤（当前未做内容过滤） | P2 |
| RAG 原理说明文档 | 编写 `docs/rag-explanation.md`，便于初级开发者理解 RAG 原理 | P1 |
| Provider 兼容性验证 | 验证 OpenAI 兼容端点（如 Azure OpenAI、本地 vLLM）的可用性 | P2 |

### 3. Chroma 向量库操作要点

#### Collection 命名规则

```python
collection_name = f"kb_{provider_name}_{dimension}"
# 示例：kb_openai_1536、kb_bge_1024
```

#### 相似度计算

Chroma 使用 cosine distance（0~2），后端转换为相似度：

```python
similarity = 1.0 - (distance / 2.0)
# distance=0 → similarity=1.0（完全相似）
# distance=2 → similarity=0.0（完全不同）
```

#### 切换 Provider 的索引重建

切换 Embedding Provider 后：
1. 使用新 collection（如 `kb_bge_1024`）
2. 旧 collection 保留但不使用
3. 需对所有已上传文档重新 Embedding
4. MVP 阶段 `PUT /api/config/embedding-provider` 仅返回提示信息，实际重建需手动触发

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| FastAPI 422 响应格式不统一 | Medium | FastAPI 内置校验返回标准格式，非本项目统一格式 | 前端需兼容两种 422 响应结构 |
| Embedding Provider 切换需手动重建 | Medium | MVP 未实现自动重建索引 | 前端提示用户，V2 实现自动重建 |
| 本地 BGE 模型首次加载慢 | Low | 需下载几百 MB~1GB 模型 | 默认使用 OpenAI，BGE 作为可选 |
| 无内容过滤 | Low | MVP 未实现 LLM 输出过滤 | V2 可增加输出验证 |
| 文档上传为同步处理 | Low | MVP 未实现真正的异步任务队列 | 大文件上传时可能阻塞，V2 可引入 BackgroundTasks |
| 无 rerank | Low | DEC 简化 MVP | V2 可引入 rerank 模型提升检索质量 |

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| OpenAI API Key 泄露 | 低 | 高 | 严格通过 `.env` 管理，安全审计阶段重点检查 |
| SSE 连接长时间占用 | 中 | 中 | 前端中断后后端检测 GeneratorExit 释放资源；V2 可加超时强制关闭 |
| 文档删除时向量残留 | 低 | 中 | 后端已实现 Chroma → MariaDB → 文件三步删除，顺序保证一致性 |
| 切换 Provider 后维度不匹配 | 低 | 高 | 严格用 `kb_{provider}_{dim}` collection 名隔离 |
| LLM 超时无响应 | 中 | 中 | 前端设置超时提示，后端 stream_timeout=60s |
| 大文件上传阻塞 | 低 | 低 | 流式读取 + 大小校验，超 20MB 拒绝 |

## 假设说明

- 假设后端服务运行在 `http://127.0.0.1:8000`（DEC-001 本地运行）
- 假设前端开发环境使用 Vite Proxy 代理 `/api`（DEC-015）
- 假设 MariaDB 已本地安装并执行 `init.sql` 初始化
- 假设 `.env` 已配置 `OPENAI_API_KEY`（默认 Embedding 与 LLM 均使用 OpenAI）
- 假设 Chroma 数据目录 `./data/chroma` 可读写
- 假设上传文件目录 `./data/uploads` 可读写

## 启动后端服务

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 3. 初始化数据库
mysql -u root -p < database/init.sql

# 4. 启动服务
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 5. 验证
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs  # OpenAPI 文档
```

## 下一步建议

### 对前端工程师（TASK-008）：

1. **阅读 `docs/api-spec.md`**：完整的 11 个 API 端点请求/响应格式
2. **阅读 `docs/design-system.md`、`docs/wireframes.md`、`docs/mockups.md`**：UI 设计规范
3. **配置 Vite Proxy**：代理 `/api` 到 `http://127.0.0.1:8000`（DEC-015）
4. **实现 API 调用层**：基于 axios，统一错误处理（兼容两种 422 格式）
5. **实现 SSE 流式接收**：fetch + ReadableStream（EventSource 不支持 POST）
6. **实现核心页面**：
   - 文档上传页（拖拽 + 批量 + 进度）
   - 对话页（左右分栏 + 流式渲染 + 引用来源）
   - 会话列表（排序 + 删除 + 清空）
   - 文档管理列表（分页 + 状态 + 删除）
7. **实现状态管理**：Pinia stores（documents, sessions, chat, config）
8. **处理关键交互状态**：上传中、解析中、流式回答中、空状态、错误状态

### 对 AI 工程师（TASK-009，可与前端并行）：

1. **验证 RAG 闭环**：上传测试文档 → 提问 → 验证引用来源与回答质量
2. **检查 Provider 抽象层**：`backend/app/providers/`，验证 OpenAI 与 BGE 双 Provider 切换
3. **检查 Prompt 模板**：`backend/app/services/prompt_template.py`，根据实际效果调优
4. **检查 RAG 检索参数**：`backend/app/services/rag_service.py`，top_k=5、阈值 0.3
5. **检查超时与重试**：`backend/app/providers/llm/openai_provider.py`，timeout=30s、stream_timeout=60s
6. **编写 RAG 原理说明文档**：`docs/rag-explanation.md`，面向初级开发者
7. **验证引用来源元数据回传**：检查 SSE references 事件的完整性与准确性

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | Frontend Engineer, AI Engineer |
| 确认状态 | Pending Confirmation |

---

**交接完成。请前端工程师阅读 `docs/api-spec.md`（重点第 4、6、8 节）与 `docs/design-system.md`、`docs/wireframes.md`、`docs/mockups.md` 后开始工作。请 AI 工程师阅读 `docs/architecture.md`（重点第 4、6 章）与后端 `backend/app/providers/`、`backend/app/services/rag_service.py`、`backend/app/services/prompt_template.py` 后开始工作。**
