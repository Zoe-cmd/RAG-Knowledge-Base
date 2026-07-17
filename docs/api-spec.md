<!--
Document: API Specification
Version: 1.0.0
Author: Backend Engineer
Created: 2026-07-12
Updated: 2026-07-12
Status: Completed
-->

# API Specification: AI 文档知识库（MVP）

## 文档元信息

| 字段 | 内容 |
|------|------|
| 文档名称 | API 规范文档 |
| 项目名称 | AI 文档知识库（MVP） |
| 版本 | 1.0.0 |
| 作者 | Backend Engineer |
| 创建日期 | 2026-07-12 |
| 最后更新 | 2026-07-12 |
| 状态 | Completed |
| 关联文档 | `docs/prd.md`、`docs/architecture.md`、`docs/database-schema.md` |

---

## 1. 概述

### 1.1 基本信息

| 属性 | 值 |
|------|------|
| 服务名称 | AI 文档知识库后端 API |
| 版本 | v1 |
| 基础 URL | `http://127.0.0.1:8000/api` |
| 协议 | HTTP（本地运行，DEC-001 无需 HTTPS） |
| 数据格式 | JSON（除文件上传与 SSE 流式端点） |
| 运行环境 | 本地 localhost（DEC-001） |
| 认证方式 | 无（本地单用户，DEC-001） |

### 1.2 通用规范

本 API 遵循 `shared/api-standard.md` 中定义的所有规范。因项目为本地运行的单用户应用（DEC-001），以下规范做如下适配：

| 规范项 | 标准要求 | 本项目适配 | 依据 |
|--------|----------|------------|------|
| 认证 | 所有 API 必须认证 | 无需认证 | DEC-001 本地运行 |
| HTTPS | 必须使用 HTTPS | 使用 HTTP | DEC-001 本地运行 |
| 限流 | 必须有限流 | 无需限流 | DEC-001 单用户 |
| CORS | 严格配置 | 通过 Vite Proxy 规避 | DEC-015 |
| 版本号 | URL 路径 `/v1/` | 路径为 `/api/`，版本在文档中管理 | MVP 简化 |

### 1.3 响应格式说明

本项目响应格式在遵循 api-standard.md 的基础上做适度简化（DEC-013 错误码体系简化技术债务），采用以下统一格式：

**成功响应**（单资源）：
```json
{
  "data": { ... },
  "meta": {
    "requestId": "uuid"
  }
}
```

**成功响应**（集合）：
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

**错误响应**：
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

> 注：SSE 流式端点（POST /api/chat/messages）不使用上述 JSON 响应格式，使用 SSE 事件流（详见 4.9）。

---

## 2. 认证与授权

### 2.1 认证方式

本项目为本地 localhost 运行（DEC-001），**无需认证**。所有 API 端点均可直接访问，无需 Authorization 头。

### 2.2 权限模型

无权限模型。本地单用户场景下，所有资源均可自由访问。

---

## 3. 通用响应

### 3.1 成功响应格式

见 1.3 节。

### 3.2 错误响应格式

见 1.3 节。

### 3.3 HTTP 状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 OK | 请求成功 | GET、PUT、PATCH 成功 |
| 201 Created | 资源创建成功 | POST 创建成功 |
| 204 No Content | 无内容 | DELETE 成功 |
| 400 Bad Request | 请求格式错误 | 参数验证失败 |
| 404 Not Found | 资源不存在 | 资源未找到 |
| 409 Conflict | 资源冲突 | 文档数超限、重复上传 |
| 413 Payload Too Large | 请求体过大 | 文件超过 20MB |
| 415 Unsupported Media Type | 不支持的媒体类型 | 文件类型不支持 |
| 422 Unprocessable Entity | 语义错误 | 扫描件 PDF、业务逻辑验证失败 |
| 500 Internal Server Error | 服务器内部错误 | 未预期的错误 |
| 503 Service Unavailable | 服务不可用 | 数据库连接失败、OpenAI API 不可用 |

---

## 4. API 端点

### 4.1 资源: 文档（Documents）

#### 4.1.1 上传文档

```
POST /api/documents/upload
```

**描述**: 上传一个或多个文档，自动触发解析→切分→向量化流水线。支持 PDF、Word(docx)、Markdown、TXT 四种格式。

**认证**: 不需要

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | File[] | 是 | 一个或多个文件（支持批量上传） |

**业务规则**:

| 规则 | 说明 |
|------|------|
| 文件类型校验 | 扩展名必须在 [pdf, docx, md, txt] 内（BR-DOC-001） |
| 文件大小校验 | 单文件 ≤ 20MB（BR-DOC-002） |
| 文档总数校验 | 已有文档数 < 100（BR-DOC-003） |
| 扫描件检测 | PDF 解析后字数为 0 时判定为扫描件，返回 422（BR-DOC-005） |
| 重名处理 | 允许上传同名文档，不覆盖（BR-DOC-004） |

**响应**:

```json
{
  "data": {
    "documents": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "RAG原理.pdf",
        "file_type": "pdf",
        "file_size": 2300000,
        "status": "processing",
        "chunk_count": 0,
        "created_at": "2026-07-12T12:00:00.000Z"
      }
    ],
    "failed": [
      {
        "filename": "扫描件.pdf",
        "error": "该 PDF 为扫描件，MVP 暂不支持，需 OCR",
        "code": "SCANNED_PDF"
      }
    ]
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

HTTP 状态码: `201 Created`

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| documents | array | 成功上传的文档列表 |
| documents[].id | string (UUID) | 文档 ID |
| documents[].filename | string | 原始文件名 |
| documents[].file_type | string | 文件类型：pdf/docx/md/txt |
| documents[].file_size | int | 文件大小（字节） |
| documents[].status | string | 处理状态：processing（异步处理中） |
| documents[].chunk_count | int | 切片数量（上传时为 0，处理完成后更新） |
| documents[].created_at | string (ISO 8601) | 创建时间 |
| failed | array | 上传失败的文件列表 |
| failed[].filename | string | 失败的文件名 |
| failed[].error | string | 失败原因 |
| failed[].code | string | 错误码 |

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | VALIDATION_ERROR | 未提供文件 |
| 409 | DOCUMENT_LIMIT_EXCEEDED | 文档数已达上限 100 |
| 413 | FILE_TOO_LARGE | 文件超过 20MB 限制 |
| 415 | UNSUPPORTED_FILE_TYPE | 不支持的文件类型 |
| 422 | SCANNED_PDF | 该 PDF 为扫描件 |
| 503 | SERVICE_UNAVAILABLE | OpenAI API 不可用或数据库连接失败 |

**处理流程**:

1. 校验文件类型与大小
2. 检查文档总数限制
3. 保存文件到 `./data/uploads/{YYYY}/{MM}/{uuid}.{ext}`
4. 计算 SHA-256 内容哈希（用于去重检测）
5. INSERT documents 记录（status=processing）
6. 异步执行：解析 → 切分 → Embedding → Chroma 存储
7. 完成后 UPDATE documents SET chunk_count, embedding_provider, status=completed
8. 失败时 UPDATE documents SET status=failed, error_message

---

#### 4.1.2 获取文档列表

```
GET /api/documents
```

**描述**: 获取已上传的文档列表（分页），按创建时间倒序。

**认证**: 不需要

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码（从 1 开始） |
| size | integer | 否 | 20 | 每页数量（最大 100） |
| status | string | 否 | - | 按状态过滤：pending/processing/completed/failed |

**响应**:

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "RAG原理.pdf",
      "file_type": "pdf",
      "file_size": 2300000,
      "chunk_count": 96,
      "status": "completed",
      "embedding_provider": "openai",
      "created_at": "2026-07-12T12:00:00.000Z",
      "updated_at": "2026-07-12T12:00:15.000Z"
    }
  ],
  "meta": {
    "requestId": "req-abc-123",
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 12,
      "totalPages": 1
    }
  }
}
```

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | VALIDATION_ERROR | 分页参数无效 |

---

#### 4.1.3 删除文档

```
DELETE /api/documents/{id}
```

**描述**: 删除指定文档。同步删除 Chroma 中该文档的所有向量，软删除 MariaDB 记录，删除文件系统原文件。

**认证**: 不需要

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 文档 ID |

**响应**: HTTP 状态码 `204 No Content`（无响应体）

**删除流程**:

1. 查询文档是否存在（`WHERE deleted_at IS NULL`）
2. 删除 Chroma 中 `where={"doc_id": id}` 的所有向量
3. 软删除 MariaDB 记录（`UPDATE documents SET deleted_at = NOW() WHERE id = ?`）
4. 删除文件系统原文件（`./data/uploads/...`）

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | DOCUMENT_NOT_FOUND | 文档不存在 |
| 500 | INTERNAL_ERROR | 删除失败（Chroma 或文件系统错误） |

---

### 4.2 资源: 会话（Sessions）

#### 4.2.1 新建会话

```
POST /api/chat/sessions
```

**描述**: 创建新的聊天会话。

**认证**: 不需要

**请求体**: 无（可空对象 `{}`）

**响应**:

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "新会话",
    "message_count": 0,
    "last_message_at": null,
    "created_at": "2026-07-12T12:00:00.000Z"
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

HTTP 状态码: `201 Created`

---

#### 4.2.2 获取会话列表

```
GET /api/chat/sessions
```

**描述**: 获取所有会话列表，按最后消息时间倒序（NULL 排在最后）。

**认证**: 不需要

**查询参数**: 无（MVP 返回全部会话，最多 50 条）

**响应**:

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "什么是 RAG？",
      "message_count": 8,
      "last_message_at": "2026-07-12T12:30:00.000Z",
      "created_at": "2026-07-12T12:00:00.000Z"
    }
  ],
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

**排序规则**: `ORDER BY (last_message_at IS NULL), last_message_at DESC`（NULL 排最后）

---

#### 4.2.3 删除单个会话

```
DELETE /api/chat/sessions/{id}
```

**描述**: 删除指定会话及其所有消息。物理删除消息，软删除会话。

**认证**: 不需要

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 会话 ID |

**响应**: HTTP 状态码 `204 No Content`

**删除流程**:

1. 查询会话是否存在
2. 物理删除该会话的所有消息（`DELETE FROM chat_messages WHERE session_id = ?`）
3. 软删除会话（`UPDATE chat_sessions SET deleted_at = NOW() WHERE id = ?`）

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | SESSION_NOT_FOUND | 会话不存在 |

---

#### 4.2.4 清空所有会话

```
DELETE /api/chat/sessions
```

**描述**: 清空所有会话及其消息。物理删除所有消息，软删除所有会话。

**认证**: 不需要

**响应**:

```json
{
  "data": {
    "deleted_count": 5
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

**删除流程**:

1. 物理删除所有未软删会话的消息（`DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE deleted_at IS NULL)`）
2. 软删除所有未软删会话（`UPDATE chat_sessions SET deleted_at = NOW() WHERE deleted_at IS NULL`）

---

#### 4.2.5 获取会话消息列表

```
GET /api/chat/sessions/{id}/messages
```

**描述**: 获取指定会话的所有消息，按时间正序排列。

**认证**: 不需要

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | UUID | 是 | 会话 ID |

**响应**:

```json
{
  "data": {
    "messages": [
      {
        "id": "msg-uuid-1",
        "role": "user",
        "content": "什么是 RAG？",
        "references": null,
        "elapsed_ms": null,
        "created_at": "2026-07-12T12:00:00.000Z"
      },
      {
        "id": "msg-uuid-2",
        "role": "assistant",
        "content": "RAG 是检索增强生成...",
        "references": [
          {
            "doc_id": "doc-uuid-1",
            "doc_name": "RAG原理.pdf",
            "chunk": "RAG（Retrieval-Augmented Generation）是一种结合检索与生成的方法...",
            "source_path": "uploads/2026/07/doc-uuid-1.pdf",
            "chunk_index": 3,
            "similarity": 0.87
          }
        ],
        "elapsed_ms": 3200,
        "created_at": "2026-07-12T12:00:03.200Z"
      }
    ]
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | SESSION_NOT_FOUND | 会话不存在 |

---

### 4.3 资源: 聊天消息（Chat Messages）

#### 4.3.1 发送消息（SSE 流式）

```
POST /api/chat/messages
```

**描述**: 发送用户问题，通过 RAG 管线检索相关文档片段，调用 LLM 流式生成回答。响应为 SSE 事件流。

**认证**: 不需要

**Content-Type**: `application/json`

**Accept**: `text/event-stream`

**请求体**:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "什么是 RAG？"
}
```

**请求体验证**:

| 字段 | 类型 | 必填 | 规则 |
|------|------|------|------|
| session_id | string (UUID) | 是 | 必须为有效 UUID，且会话存在 |
| question | string | 是 | 1-2000 字符，不能为空 |

**响应**: SSE 事件流（`Content-Type: text/event-stream`）

**SSE 事件格式**:

```
event: {event_type}
data: {json_data}

```

> 每个 SSE 事件由 `event:` 行、`data:` 行和一个空行组成。

**事件类型**:

##### 事件 1: references（引用来源）

在流式回答开始前发送，包含检索到的文档片段引用。

```
event: references
data: [{"doc_id":"doc-uuid-1","doc_name":"RAG原理.pdf","chunk":"RAG（Retrieval-Augmented Generation）是一种结合检索与生成的方法...","source_path":"uploads/2026/07/doc-uuid-1.pdf","chunk_index":3,"similarity":0.87}]

```

**data 字段**: JSON 数组，每个元素结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 文档 ID |
| doc_name | string | 文档文件名 |
| chunk | string | 引用的文本片段内容 |
| source_path | string | 源文件路径 |
| chunk_index | int | 切片索引 |
| similarity | float | 相似度得分（0.0~1.0） |

##### 事件 2: token（流式 token）

LLM 生成的回答逐 token 返回。

```
event: token
data: {"content":"RAG"}

```

##### 事件 3: done（完成）

回答生成完成，包含耗时与消息 ID。

```
event: done
data: {"message_id":"msg-uuid-2","elapsed_ms":3200}

```

##### 事件 4: error（错误）

发生错误时发送。

```
event: error
data: {"message":"回答生成超时","code":"LLM_TIMEOUT"}

```

**完整流程**:

1. 验证请求参数
2. 查询会话是否存在
3. 保存用户消息（role=user）到 MariaDB
4. 问题向量化（EmbeddingProvider.embed_query）
5. Chroma 检索 top_k=5 相关片段
6. 过滤相似度 < 0.3 的片段（DEC-006 阈值）
7. 若无相关片段，发送空 references + done 事件（FR-RAG-008）
8. 发送 references 事件（引用来源）
9. 查询最近 4 轮（8 条）历史消息（DEC-011）
10. 组装上下文：System Prompt + RAG Context + History + Question
11. 调用 LLMProvider.chat_completion(stream=True)
12. 逐 token 发送 token 事件
13. LLM 完成后，保存 assistant 消息（role=assistant, references, elapsed_ms）
14. 更新会话统计（message_count, last_message_at）
15. 发送 done 事件

**错误码**:

| 错误码 | 说明 |
|--------|------|
| SESSION_NOT_FOUND | 会话不存在 |
| LLM_TIMEOUT | LLM 调用超时（>30s） |
| LLM_AUTH_ERROR | OpenAI API Key 无效 |
| LLM_CONNECTION_ERROR | 网络中断 |
| EMBEDDING_ERROR | 问题向量化失败 |
| INTERNAL_ERROR | 其他内部错误 |

**停止生成**:

前端通过关闭 fetch 连接（abort）中断流式。后端检测到 `GeneratorExit` 后：
1. 关闭 LLM stream
2. 保存已生成的部分内容为 assistant 消息（FR-RAG-007）

**无相关内容处理**（FR-RAG-008）:

当检索结果全部低于相似度阈值时：
```
event: references
data: []

event: done
data: {"message_id":"msg-uuid-2","elapsed_ms":0}

```

> 前端根据空 references 数组提示"未在文档库中找到相关内容"。

---

### 4.4 资源: 配置（Config）

#### 4.4.1 获取当前配置

```
GET /api/config
```

**描述**: 获取当前应用配置信息，包括 Embedding Provider、向量维度、文档统计等。

**认证**: 不需要

**响应**:

```json
{
  "data": {
    "embedding_provider": "openai",
    "embedding_dimension": 1536,
    "llm_model": "gpt-4o-mini",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 5,
    "similarity_threshold": 0.3,
    "max_history_rounds": 4,
    "max_file_size_mb": 20,
    "max_documents": 100,
    "statistics": {
      "total_documents": 12,
      "completed_documents": 10,
      "processing_documents": 1,
      "failed_documents": 1,
      "total_chunks": 1150,
      "total_sessions": 5,
      "total_messages": 48
    }
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

---

#### 4.4.2 切换 Embedding Provider

```
PUT /api/config/embedding-provider
```

**描述**: 切换 Embedding Provider。切换后需重建索引（维度可能不同）。

**认证**: 不需要

**请求体**:

```json
{
  "provider": "bge"
}
```

**请求体验证**:

| 字段 | 类型 | 必填 | 规则 |
|------|------|------|------|
| provider | string | 是 | 枚举值：openai / bge |

**响应**:

```json
{
  "data": {
    "previous_provider": "openai",
    "current_provider": "bge",
    "previous_dimension": 1536,
    "current_dimension": 1024,
    "needs_reindex": true,
    "documents_to_reindex": 12
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

**说明**:
- 切换 Provider 后，使用新 collection（如 `kb_bge_1024`）
- 旧 collection 保留但不使用
- 需对所有已上传文档重新 Embedding（前端提示用户并触发重建）
- 重建索引通过文档列表接口的状态轮询监控

**错误**:

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | VALIDATION_ERROR | provider 参数无效 |
| 422 | REINDEX_REQUIRED | 切换需重建索引（响应同上，提示前端） |

---

## 5. 数据模型

### 5.1 Document

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "RAG原理.pdf",
  "file_type": "pdf",
  "file_size": 2300000,
  "file_path": "uploads/2026/07/550e8400-e29b-41d4-a716-446655440000.pdf",
  "content_hash": "a1b2c3d4e5f6...",
  "chunk_count": 96,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "status": "completed",
  "error_message": null,
  "embedding_provider": "openai",
  "created_at": "2026-07-12T12:00:00.000Z",
  "updated_at": "2026-07-12T12:00:15.000Z"
}
```

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 文档唯一标识符 | 应用层生成 |
| filename | string | 原始文件名 | 1-255 字符 |
| file_type | string | 文件类型 | pdf/docx/md/txt |
| file_size | int | 文件大小（字节） | >0, ≤20971520 |
| file_path | string | 存储路径（相对） | - |
| content_hash | string | SHA-256 哈希 | 64 字符 |
| chunk_count | int | 切片数量 | ≥0 |
| chunk_size | int | 切片大小 | 默认 500 |
| chunk_overlap | int | 切片重叠 | 默认 50 |
| status | string | 处理状态 | pending/processing/completed/failed |
| error_message | string | 错误信息 | status=failed 时 |
| embedding_provider | string | Embedding Provider | openai/bge |
| created_at | datetime | 创建时间 | 自动生成 |
| updated_at | datetime | 更新时间 | 自动更新 |

### 5.2 ChatSession

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "什么是 RAG？",
  "message_count": 8,
  "last_message_at": "2026-07-12T12:30:00.000Z",
  "created_at": "2026-07-12T12:00:00.000Z"
}
```

### 5.3 ChatMessage

```json
{
  "id": "msg-uuid-2",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "RAG 是检索增强生成...",
  "references": [
    {
      "doc_id": "doc-uuid-1",
      "doc_name": "RAG原理.pdf",
      "chunk": "RAG（Retrieval-Augmented Generation）是一种结合检索与生成的方法...",
      "source_path": "uploads/2026/07/doc-uuid-1.pdf",
      "chunk_index": 3,
      "similarity": 0.87
    }
  ],
  "elapsed_ms": 3200,
  "created_at": "2026-07-12T12:00:03.200Z"
}
```

---

## 6. 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| DOCUMENT_NOT_FOUND | 404 | 文档不存在 |
| SESSION_NOT_FOUND | 404 | 会话不存在 |
| DOCUMENT_LIMIT_EXCEEDED | 409 | 文档数已达上限 100 |
| FILE_TOO_LARGE | 413 | 文件超过 20MB 限制 |
| UNSUPPORTED_FILE_TYPE | 415 | 不支持的文件类型 |
| SCANNED_PDF | 422 | 该 PDF 为扫描件 |
| REINDEX_REQUIRED | 422 | 切换需重建索引 |
| LLM_TIMEOUT | 500 | LLM 调用超时（SSE error 事件） |
| LLM_AUTH_ERROR | 500 | OpenAI API Key 无效（SSE error 事件） |
| LLM_CONNECTION_ERROR | 500 | 网络中断（SSE error 事件） |
| EMBEDDING_ERROR | 500 | 问题向量化失败（SSE error 事件） |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 |

---

## 7. API 端点总览

| # | 方法 | 路径 | 说明 | 响应类型 |
|---|------|------|------|----------|
| 1 | POST | `/api/documents/upload` | 上传文档 | JSON |
| 2 | GET | `/api/documents` | 文档列表 | JSON |
| 3 | DELETE | `/api/documents/{id}` | 删除文档 | 204 |
| 4 | POST | `/api/chat/sessions` | 新建会话 | JSON |
| 5 | GET | `/api/chat/sessions` | 会话列表 | JSON |
| 6 | DELETE | `/api/chat/sessions/{id}` | 删除会话 | 204 |
| 7 | DELETE | `/api/chat/sessions` | 清空会话 | JSON |
| 8 | GET | `/api/chat/sessions/{id}/messages` | 会话消息 | JSON |
| 9 | POST | `/api/chat/messages` | 发送消息（SSE） | SSE |
| 10 | GET | `/api/config` | 获取配置 | JSON |
| 11 | PUT | `/api/config/embedding-provider` | 切换 Provider | JSON |

---

## 8. 附录

### 8.1 SSE 完整示例

**请求**:
```
POST /api/chat/messages HTTP/1.1
Content-Type: application/json
Accept: text/event-stream

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "什么是 RAG？"
}
```

**响应**:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: references
data: [{"doc_id":"doc-1","doc_name":"RAG原理.pdf","chunk":"RAG 是...","source_path":"uploads/2026/07/doc-1.pdf","chunk_index":3,"similarity":0.87}]

event: token
data: {"content":"RAG"}

event: token
data: {"content":"是"}

event: token
data: {"content":"检索增强生成"}

event: done
data: {"message_id":"msg-2","elapsed_ms":3200}

```

### 8.2 错误响应示例

```json
// POST /api/documents/upload - 文件过大
// 413 Payload Too Large
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "文件 RAG原理.pdf 超过 20MB 限制",
    "details": [
      {
        "field": "files",
        "message": "文件大小 25MB 超过限制 20MB",
        "code": "FILE_SIZE_EXCEEDED"
      }
    ]
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

```json
// DELETE /api/documents/00000000-0000-0000-0000-000000000000
// 404 Not Found
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "文档不存在",
    "details": []
  },
  "meta": {
    "requestId": "req-abc-123"
  }
}
```

### 8.3 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，定义 11 个 API 端点 | Backend Engineer |

---

**本 API 规范是前后端协作的唯一真实来源。前端工程师基于本文档实现 API 调用层，后端工程师基于本文档实现 API 端点。任何接口变更须先更新本文档。**
