<!--
Document: Test Plan
Version: 1.0.0
Author: QA Engineer
Created: 2026-07-12
Updated: 2026-07-12
Status: In Progress
-->

# Test Plan: AI 文档知识库（MVP）

## 文档元信息

| 字段 | 内容 |
|------|------|
| 文档名称 | 测试计划 |
| 项目名称 | AI 文档知识库（MVP） |
| 版本 | 1.0.0 |
| 作者 | QA Engineer |
| 创建日期 | 2026-07-12 |
| 最后更新 | 2026-07-12 |
| 状态 | In Progress |
| 关联文档 | `docs/prd.md`、`docs/api-spec.md`、`docs/architecture.md`、上游交接 HO-008/HO-009 |

---

## 1. 概述

### 1.1 测试目标

验证 AI 文档知识库（MVP）是否符合 PRD v1.0.0 的功能需求、非功能需求与验收标准，重点验证：

1. **RAG 核心闭环**：文档上传 → 解析 → 切分 → 向量化 → 检索 → 流式问答 → 引用回传 全链路可用
2. **流式输出正确性**：SSE 事件序列（references → token × N → done）符合规范
3. **多轮上下文管理**：最近 4 轮（8 条消息）截断策略正确
4. **文档删除一致性**：删除文档时同步删除 Chroma 向量与 MariaDB 元数据
5. **边界与异常处理**：扫描件 PDF、超大文件、不支持类型、无相关内容等场景的友好提示
6. **性能达标**：单次问答 P95 < 15s，首 token < 3s
7. **覆盖率达标**：后端单元测试覆盖率 >= 80%

### 1.2 测试范围

| 在范围内 | 不在范围内 |
|----------|------------|
| 文档上传（PDF/Word/Markdown/TXT，批量+拖拽） | OCR 扫描件识别（仅检测并提示） |
| 文档解析与切分（chunk_size=500, overlap=50） | 多用户与权限控制（DEC-001 本地单用户） |
| Embedding 生成（OpenAI + BGE 双 Provider） | 全文搜索引擎（MVP 不做） |
| 向量存储与检索（Chroma，top_k=5，阈值 0.3） | 插件系统、MCP、多 Agent |
| RAG 流式问答（SSE，引用来源回传） | 工作流编排、消息队列、微服务 |
| 多轮上下文（最近 4 轮截断） | 暗色模式（DEC-013 债务） |
| 聊天会话 CRUD 与历史持久化 | 移动端原生 App |
| 文档删除（同步删除向量） | 社交登录/OAuth |
| Embedding Provider 切换（含重建索引提示） | 邮件通知、推送 |
| 响应式布局（1024px 断点） | Safari 兼容性（不保证） |
| 错误处理与友好提示 | 高可用集群部署 |
| 安全相关：API Key 管理、文件上传校验、XSS | 渗透测试（由 Security Engineer 负责） |

### 1.3 测试环境

| 环境 | 说明 |
|------|------|
| 单元/集成测试环境 | 本地 Python 3.13.12 + pytest 9.0.3，使用 SQLite 内存库 + Mock 外部依赖（OpenAI/Chroma） |
| E2E 测试环境 | 后端 `127.0.0.1:8000` + 前端 `127.0.0.1:5173`，需配置 `backend/.env`（含有效 OPENAI_API_KEY） |
| 数据库 | 单元/集成测试用 SQLite（aiosqlite）；E2E 用 MariaDB 10.11+（本地安装） |
| 向量库 | 单元/集成测试用 Mock；E2E 用 Chroma 嵌入式持久化（`./data/chroma`） |
| LLM | 单元/集成测试用 Mock；E2E 用 OpenAI gpt-4o-mini（需有效 API Key） |
| 浏览器 | Chrome 最新版、Edge 最新版、Firefox 最新版 |

### 1.4 测试工具

| 工具 | 用途 | 版本 |
|------|------|------|
| pytest | 后端单元/集成测试框架 | 9.0.3 |
| pytest-asyncio | 异步测试支持 | 1.4.0 |
| pytest-cov | 覆盖率统计 | 7.1.0 |
| pytest-mock | Mock 工具 | 3.15.1 |
| httpx (AsyncClient) | API 集成测试客户端 | 0.27.0 |
| Faker | 测试数据生成 | 39.0.0 |
| 手动测试 | E2E 闭环验证与前端交互验证 | 浏览器 |
| 后端计时 | 性能测试（time.perf_counter） | Python 内置 |

---

## 2. 测试策略

### 2.1 测试类型

| 类型 | 范围 | 工具 | 目标 | 负责人 |
|------|------|------|------|--------|
| 单元测试 | 所有 Service/Provider/Parser/Chunker 模块 | pytest | 覆盖率 >= 80% | 已由各 Engineer 编写 |
| 集成测试 | API 端点 + 模块间交互（mock 外部依赖） | pytest + httpx AsyncClient | 关键路径 100%，补充 API 层覆盖 | QA Engineer |
| E2E 测试 | RAG 闭环用户流程（真实环境） | 手动 + 脚本 | 核心用户流程 100% | QA Engineer（需真实环境） |
| 性能测试 | 问答延迟、首 token 延迟、上传延迟 | Python 计时脚本 | P95 < 15s，首 token < 3s | QA Engineer（需真实环境） |
| 安全测试 | API Key、文件上传、输入验证 | 代码审查 + 手动验证 | 无 Critical 漏洞 | Security Engineer（Phase 4 后续） |

### 2.2 测试优先级

| 优先级 | 测试范围 | 说明 | 通过要求 |
|--------|----------|------|----------|
| P0 | RAG 闭环、流式输出、多轮上下文、文档删除同步、扫描件检测 | 核心功能，必须全部通过 | 100% 通过 |
| P1 | 文档批量上传、Provider 切换、停止生成、历史持久化、响应式布局 | 重要功能，必须全部通过 | 100% 通过 |
| P2 | 知识库统计、会话标题、空状态引导 | 辅助功能 | 允许少量失败 |
| P3 | 边缘浏览器兼容、极端并发 | 边缘场景 | 允许失败 |

### 2.3 测试金字塔

```
        ┌──────────┐
        │   E2E    │  ← 8 个核心用户流程（手动 + 脚本）
        │   ~8     │
       ┌┴──────────┴┐
       │ Integration │  ← 25 个集成测试用例（TestClient + Mock）
       │   ~25       │
      ┌┴─────────────┴┐
      │     Unit       │  ← 212 个已有单元测试 + 新增集成测试
      │    212+25      │
      └────────────────┘
```

---

## 3. 测试用例

### 3.1 模块 1: 文档管理（FR-DOC）

#### TC-DOC-001: 上传 PDF 文档（正常流程）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-001 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | 文档数 < 100；文件为文本型 PDF |
| 关联需求 | FR-DOC-001, US-001 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST /api/documents/upload，上传 1 个文本型 PDF（< 20MB） | HTTP 201，返回 data.documents 数组含 1 项 |
| 2 | 检查响应字段 | id(UUID)、filename、file_type="pdf"、file_size、status="processing"、chunk_count、created_at |
| 3 | 检查文档列表 GET /api/documents | 列表含该文档，状态流转为 completed |

#### TC-DOC-002: 上传 Word(docx) 文档（含表格）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-002 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | docx 文件含文本与表格 |
| 关联需求 | FR-DOC-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 上传含表格的 docx 文件 | HTTP 201，解析成功 |
| 2 | 检查解析结果 | 表格内容转为文本，存入向量库 |

#### TC-DOC-003: 上传 Markdown 文档（按标题切分）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-003 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | Markdown 文件含多级标题 |
| 关联需求 | FR-VEC-001 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 上传含 # ## ### 标题的 .md 文件 | HTTP 201，切分成功 |
| 2 | 检查切分结果 | 标题边界保留；chunk_size <= 500 字符 |

#### TC-DOC-004: 上传 TXT 文档（编码检测）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-004 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | TXT 文件分别为 UTF-8 与 GBK 编码 |
| 关联需求 | FR-DOC-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 上传 UTF-8 编码 TXT | HTTP 201，正确解析 |
| 2 | 上传 GBK 编码 TXT | HTTP 201，chardet 检测后正确解析 |

#### TC-DOC-005: 批量上传多个文档

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-005 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | 准备 3 个不同类型文档 |
| 关联需求 | US-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST /api/documents/upload，同时上传 3 个文件 | HTTP 201，data.documents 含 3 项 |
| 2 | 检查每个文件独立处理 | 每个文档有独立 id 与状态 |

#### TC-DOC-006: 扫描件 PDF 友好提示

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-006 |
| 模块 | 文档管理 - 上传 |
| 优先级 | P0 |
| 前置条件 | 扫描型 PDF（解析后字数=0） |
| 关联需求 | FR-DOC-003, BR-DOC-005 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 上传扫描型 PDF | HTTP 422 |
| 2 | 检查响应 | error.code="SCANNED_PDF"，message 含"扫描件"与"OCR" |
| 3 | 检查文档列表 | 该文档不出现在列表，不占用文档计数 |

#### TC-DOC-007: 文档列表展示与分页

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-007 |
| 模块 | 文档管理 - 列表 |
| 优先级 | P0 |
| 前置条件 | 数据库有 25 条文档记录 |
| 关联需求 | FR-DOC-004 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET /api/documents?page=1&size=20 | HTTP 200，data 含 20 项 |
| 2 | 检查 meta.pagination | total=25, totalPages=2, page=1, size=20 |
| 3 | GET /api/documents?page=2&size=20 | data 含 5 项 |
| 4 | 检查字段完整性 | id, filename, file_type, file_size, chunk_count, status, created_at |

#### TC-DOC-008: 删除文档（同步删除向量）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-008 |
| 模块 | 文档管理 - 删除 |
| 优先级 | P0 |
| 前置条件 | 文档已上传且向量化完成 |
| 关联需求 | FR-DOC-005, BR-DOC-006 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | DELETE /api/documents/{id} | HTTP 204 |
| 2 | GET /api/documents/{id} | HTTP 404 |
| 3 | 验证 Chroma 调用 | chroma_client.delete_by_doc_id 被调用 1 次 |
| 4 | 验证 MariaDB | documents 表记录已删除（或软删除标记） |

#### TC-DOC-009: 删除不存在的文档

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-DOC-009 |
| 模块 | 文档管理 - 删除 |
| 优先级 | P1 |
| 前置条件 | 使用不存在的 UUID |
| 关联需求 | 错误处理 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | DELETE /api/documents/{不存在的UUID} | HTTP 404 |
| 2 | 检查响应 | error.code="DOCUMENT_NOT_FOUND" |

### 3.2 模块 2: 向量化与知识库（FR-VEC）

#### TC-VEC-001: 文本切分（递归字符切分）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-VEC-001 |
| 模块 | 向量化 - 切分 |
| 优先级 | P0 |
| 关联需求 | FR-VEC-001, BR-VEC-003 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 切分 1200 字符文本（chunk_size=500, overlap=50） | 生成 3 个 chunk |
| 2 | 检查 chunk 长度 | 每个 chunk <= 500 字符 |
| 3 | 检查 overlap | 相邻 chunk 有 50 字符重叠 |

#### TC-VEC-002: Embedding 生成（OpenAI Provider）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-VEC-002 |
| 模块 | 向量化 - Embedding |
| 优先级 | P0 |
| 关联需求 | FR-VEC-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 调用 OpenAI Embedding Provider | 返回 1536 维向量 |
| 2 | 检查向量维度 | dimension == 1536 |

#### TC-VEC-003: 向量存储与元数据

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-VEC-003 |
| 模块 | 向量化 - 存储 |
| 优先级 | P0 |
| 关联需求 | FR-VEC-003, FR-VEC-004 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 存储向量到 Chroma | add_vectors 成功 |
| 2 | 检查元数据字段 | doc_id, doc_name, chunk_index, source_path, char_count 完整 |

#### TC-VEC-004: Provider 切换（含重建索引提示）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-VEC-004 |
| 模块 | 向量化 - Provider 切换 |
| 优先级 | P1 |
| 关联需求 | FR-VEC-005, US-008 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | PUT /api/config，切换 EMBEDDING_PROVIDER 为 bge | HTTP 200，返回新配置 |
| 2 | 检查响应 | 含"需重建索引"提示信息 |
| 3 | GET /api/config | provider 已切换为 bge |

#### TC-VEC-005: 知识库统计

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-VEC-005 |
| 模块 | 向量化 - 统计 |
| 优先级 | P2 |
| 关联需求 | FR-VEC-006, US-009 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET /api/config 或统计端点 | 返回总文档数、总切片数、provider、维度 |

### 3.3 模块 3: RAG 问答（FR-RAG）

#### TC-RAG-001: RAG 问答正常流程（流式）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-001 |
| 模块 | RAG 问答 - 流式 |
| 优先级 | P0 |
| 前置条件 | 知识库有相关文档；已创建会话 |
| 关联需求 | FR-RAG-001~006, US-010/011/012 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST /api/chat/messages（session_id + question），Accept: text/event-stream | HTTP 200，Content-Type: text/event-stream |
| 2 | 接收首个事件 | event: references，含 doc_name、chunk 预览、source_path |
| 3 | 接收后续事件 | event: token，逐 token 返回 |
| 4 | 接收结束事件 | event: done |
| 5 | 检查事件顺序 | references 在所有 token 之前 |

#### TC-RAG-002: 引用来源先于回答展示

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-002 |
| 模块 | RAG 问答 - 引用 |
| 优先级 | P0 |
| 关联需求 | FR-RAG-005, BR-RAG-005 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送问答请求，捕获完整 SSE 事件流 | 事件序列为 references → token × N → done |
| 2 | 验证 references 事件索引 | 在首个 token 事件之前 |

#### TC-RAG-003: 无相关内容提示

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-003 |
| 模块 | RAG 问答 - 无相关内容 |
| 优先级 | P0 |
| 前置条件 | 提问与文档库无关的问题 |
| 关联需求 | FR-RAG-008, US-014 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 检索结果全部低于阈值 0.3 | 不调用 LLM 编造 |
| 2 | 检查响应 | 返回友好提示"未在文档库中找到相关内容" |
| 3 | 验证 LLM 未被调用 | mock_llm_provider.chat_completion 调用次数为 0 |

#### TC-RAG-004: 多轮上下文（4 轮截断）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-004 |
| 模块 | RAG 问答 - 多轮 |
| 优先级 | P0 |
| 前置条件 | 会话已有 5 轮历史 |
| 关联需求 | FR-RAG-009, BR-RAG-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 第 6 轮提问时检查上下文组装 | 仅保留最近 4 轮（8 条消息） |
| 2 | 验证第 1 轮消息 | 不进入 LLM 上下文 |
| 3 | 验证会话隔离 | 不同 session_id 的上下文独立 |

#### TC-RAG-005: 停止生成（AbortController）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-005 |
| 模块 | RAG 问答 - 停止 |
| 优先级 | P1 |
| 关联需求 | FR-RAG-007, US-015 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 流式生成过程中客户端断开连接 | 后端检测到断开，停止生成 |
| 2 | 检查已生成内容 | 已生成部分保留并保存到历史 |

#### TC-RAG-006: LLM 超时处理

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-006 |
| 模块 | RAG 问答 - 异常 |
| 优先级 | P0 |
| 关联需求 | FR-RAG-010, BR-RAG-007 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | Mock LLM 抛出超时异常 | 返回 event: error |
| 2 | 检查错误消息 | 含"超时"或"重试"提示 |

#### TC-RAG-007: LLM 重试机制（指数退避）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-007 |
| 模块 | RAG 问答 - 重试 |
| 优先级 | P0 |
| 关联需求 | AI-DEC-005 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | Mock LLM 前 2 次超时，第 3 次成功 | 重试后返回正常结果 |
| 2 | 验证重试次数 | 共调用 3 次 |
| 3 | Mock LLM 认证错误 | 不重试，立即失败 |

#### TC-RAG-008: 输出验证守卫

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-RAG-008 |
| 模块 | RAG 问答 - 输出验证 |
| 优先级 | P0 |
| 关联需求 | AI-DEC-006 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | Mock LLM 返回空内容 | 返回友好占位提示 |
| 2 | Mock LLM 返回含控制字符内容 | 控制字符被过滤（保留 \n\r\t） |
| 3 | Mock LLM 返回 8001 字符内容 | 截断为 8000 字符 |

### 3.4 模块 4: 聊天历史（FR-HIS）

#### TC-HIS-001: 新建会话

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-HIS-001 |
| 模块 | 聊天历史 - 会话 |
| 优先级 | P0 |
| 关联需求 | FR-HIS-001, US-016 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST /api/chat/sessions | HTTP 201，返回 id、title="新会话" |
| 2 | GET /api/chat/sessions | 列表含新会话 |

#### TC-HIS-002: 会话列表（按时间倒序）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-HIS-002 |
| 模块 | 聊天历史 - 列表 |
| 优先级 | P0 |
| 关联需求 | FR-HIS-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 3 个会话（不同时间） | GET /api/chat/sessions 返回按 last_active_at 倒序 |
| 2 | 检查字段 | id, title, message_count, last_active_at, created_at |

#### TC-HIS-003: 切换会话与历史加载

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-HIS-003 |
| 模块 | 聊天历史 - 切换 |
| 优先级 | P0 |
| 关联需求 | FR-HIS-003, US-017/020 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 会话 A 有 3 条消息，GET /api/chat/sessions/{A}/messages | 返回 3 条历史消息 |
| 2 | 检查消息字段 | question, answer, references, elapsed_ms, created_at |

#### TC-HIS-004: 删除会话（级联删除消息）

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-HIS-004 |
| 模块 | 聊天历史 - 删除 |
| 优先级 | P0 |
| 关联需求 | FR-HIS-004, BR-HIS-002 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | DELETE /api/chat/sessions/{id} | HTTP 204 |
| 2 | GET /api/chat/sessions/{id}/messages | HTTP 404 |
| 3 | 验证消息级联删除 | chat_messages 表该会话记录已删除 |

#### TC-HIS-005: 会话标题生成

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-HIS-005 |
| 模块 | 聊天历史 - 标题 |
| 优先级 | P2 |
| 关联需求 | FR-HIS-008 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 首条问题为"什么是 RAG 技术？" | 会话标题更新为"什么是 RAG 技术？"（前 20 字符） |
| 2 | 无消息的会话 | 标题显示"新会话" |

### 3.5 模块 5: 配置与健康检查

#### TC-CFG-001: 获取配置

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-CFG-001 |
| 模块 | 配置 |
| 优先级 | P1 |
| 关联需求 | FR-VEC-006 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET /api/config | HTTP 200，返回 embedding_provider、dimension、chunk_size、top_k、similarity_threshold |

#### TC-CFG-002: 健康检查

| 字段 | 内容 |
|------|------|
| 测试 ID | TC-CFG-002 |
| 模块 | 健康检查 |
| 优先级 | P1 |

**测试步骤**:

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET /api/health | HTTP 200，返回 status="healthy" |

### 3.6 边界测试

| TC ID | 场景 | 输入 | 预期结果 |
|-------|------|------|----------|
| BC-001 | 空文件 | 0 字节 TXT | HTTP 422 或 400，提示文件为空 |
| BC-002 | 超大文件 | 21MB 文件 | HTTP 413，提示超过 20MB 限制 |
| BC-003 | 不支持类型 | .exe / .jpg / .xlsx | HTTP 415，提示不支持类型 |
| BC-004 | 文档数达上限 | 已有 100 篇，再上传 | HTTP 409，提示达上限 100 |
| BC-005 | 重名文档 | 上传同名文件 | 允许上传，不覆盖，列表显示两项 |
| BC-006 | 超长文件名 | 255+ 字符文件名 | 正常处理或友好提示 |
| BC-007 | 特殊字符文件名 | 含 `<script>` 的文件名 | 转义存储，不触发 XSS |
| BC-008 | 空问题 | question="" | HTTP 422，验证错误 |
| BC-009 | 超长问题 | 10000 字符问题 | 正常处理或友好截断提示 |
| BC-010 | 分页参数越界 | page=0 或 size=1000 | HTTP 400 或返回默认分页 |
| BC-011 | 无效 UUID | documents/123（非 UUID） | HTTP 422，验证错误 |
| BC-012 | chunk 边界 | 恰好 500 字符文本 | 生成 1 个 chunk |
| BC-013 | overlap 边界 | 文本长度 < overlap（50） | 生成 1 个 chunk，不报错 |
| BC-014 | Unicode 内容 | 含中文、emoji 的文档 | 正确解析与切分 |

### 3.7 异常测试

| TC ID | 场景 | 触发条件 | 预期结果 |
|-------|------|----------|----------|
| EX-001 | 数据库不可用 | Mock DB 抛出连接异常 | HTTP 503，INTERNAL_ERROR |
| EX-002 | Chroma 不可用 | Mock chroma_client.query 抛异常 | HTTP 500 或 503，友好错误 |
| EX-003 | OpenAI API 超时 | Mock LLM 超时 | event: error，含超时提示 |
| EX-004 | OpenAI 认证失败 | Mock LLM 抛 AuthenticationError | 不重试，立即返回 error |
| EX-005 | OpenAI 连接错误 | Mock LLM 抛 APIConnectionError | 重试 3 次后返回 error |
| EX-006 | 会话不存在 | chat/messages 使用不存在的 session_id | HTTP 404，SESSION_NOT_FOUND |
| EX-007 | Embedding 生成失败 | Mock embedding 抛异常 | HTTP 503，友好错误 |
| EX-008 | 文档解析失败 | 损坏的 PDF/DOCX | HTTP 422，PARSE_ERROR |
| EX-009 | 流式中途断连 | 客户端断开 SSE 连接 | 后端停止生成，已生成内容保存 |
| EX-010 | 重试耗尽 | LLM 连续 3 次超时 | 返回 error，不无限重试 |

### 3.8 性能测试

| TC ID | 场景 | 目标 | 测量方法 |
|-------|------|------|----------|
| PT-001 | 单次问答 P95 延迟 | < 15 秒（含 LLM） | 后端 time.perf_counter 计时 |
| PT-002 | 流式首 token 延迟 | < 3 秒 | 从发送到首个 token 事件 |
| PT-003 | 文档上传解析（1MB） | < 10 秒 | 后端计时 |
| PT-004 | Embedding 生成（单 chunk） | < 2 秒（OpenAI） | 后端计时 |
| PT-005 | API 响应时间（非 LLM） | < 500ms P95 | 后端监控 |
| PT-006 | 页面首次加载 | < 3 秒 | Lighthouse |

> **注**：性能测试 PT-001~PT-004 需真实 OpenAI API Key 与运行中的后端，由 Human Developer 在真实环境执行。PT-006 需浏览器 Lighthouse 工具。

### 3.9 前端交互测试（手动）

| TC ID | 场景 | 优先级 | 验证点 |
|-------|------|--------|--------|
| FE-001 | 拖拽上传 | P1 | 拖拽高亮、释放上传 |
| FE-002 | 上传进度条 | P1 | 进度正确显示 |
| FE-003 | 流式逐字渲染 | P0 | token 逐字显示、流式光标 |
| FE-004 | Markdown 渲染 | P1 | 代码高亮、列表、链接 |
| FE-005 | 引用来源卡片 | P0 | 折叠/展开、字段完整 |
| FE-006 | 停止生成按钮 | P1 | 点击后停止、内容保留 |
| FE-007 | 消息列表自动滚动 | P1 | 贴底自动滚动、上滑不打断 |
| FE-008 | 输入区自动扩展 | P1 | Enter 发送、Shift+Enter 换行 |
| FE-009 | 响应式 ≥1024px | P1 | 固定侧边栏布局 |
| FE-010 | 响应式 <1024px | P1 | 抽屉式侧边栏 |
| FE-011 | 后端未启动错误提示 | P1 | 友好错误提示 |
| FE-012 | 删除二次确认 | P0 | 弹窗确认 |
| FE-013 | Provider 切换确认 | P1 | 二次确认弹窗 |
| FE-014 | 空状态引导 | P2 | 文档空/会话空有引导 |
| FE-015 | XSS 防护 | P0 | DOMPurify 净化回答内容 |

---

## 4. 测试执行

### 4.1 执行计划

| 阶段 | 测试类型 | 环境 | 负责人 | 状态 |
|------|----------|------|--------|------|
| 1 | 单元测试（212 个） | 本地 Python + Mock | 各 Engineer 已编写 | ✅ 已通过 |
| 2 | 集成测试（25 个） | 本地 TestClient + Mock | QA Engineer | 🔄 本次执行 |
| 3 | E2E 测试（8 个核心流程） | 真实后端+前端+API Key | QA Engineer / Human Developer | ⏳ 需真实环境 |
| 4 | 性能测试（6 项） | 真实环境 | QA Engineer / Human Developer | ⏳ 需真实环境 |
| 5 | 前端交互测试（15 项） | 浏览器 | QA Engineer / Human Developer | ⏳ 需真实环境 |
| 6 | 安全测试 | 代码审查 | Security Engineer | ⏳ Phase 4 后续 |

### 4.2 测试数据准备

| 数据 | 说明 | 准备方式 |
|------|------|----------|
| 文本型 PDF | 含可提取文本的 PDF（< 20MB） | 准备 1 份技术文档 PDF |
| 扫描型 PDF | 解析后字数为 0 的 PDF | 准备 1 份扫描件 |
| Word(docx) | 含文本与表格 | 准备 1 份 .docx |
| Markdown | 含多级标题 | 准备 1 份 .md |
| TXT(UTF-8) | UTF-8 编码 | 准备 1 份 .txt |
| TXT(GBK) | GBK 编码 | 准备 1 份 .txt |
| 超大文件 | > 20MB | 构造 21MB 文件 |
| 不支持类型 | .exe / .jpg | 准备 1 份 |
| 跨 chunk 问题 | 答案分布在两个 chunk | 设计针对性问题 |
| 无关问题 | 与文档库无关 | 设计无关问题 |

### 4.3 测试命令

```bash
# 单元测试（不含覆盖率门禁）
cd backend && python -m pytest --no-cov -q

# 单元测试 + 覆盖率（含门禁 80%）
cd backend && python -m pytest

# 集成测试（本次新增）
cd backend && python -m pytest tests/test_integration.py -v

# E2E 测试（需启动后端+配置 .env）
# 1. 配置 backend/.env（参考 .env.example，填入有效 OPENAI_API_KEY）
# 2. 启动后端：cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
# 3. 启动前端：cd frontend && npm run dev
# 4. 浏览器访问 http://127.0.0.1:5173 执行手动测试用例
```

---

## 5. 当前测试状态分析

### 5.1 已有单元测试（212 个，全部通过）

| 测试文件 | 用例数 | 覆盖模块 | 状态 |
|----------|--------|----------|------|
| test_api.py | 21 | API 端点（sessions/config/health） | ✅ 通过 |
| test_chunker.py | 13 | 递归字符切分 | ✅ 通过 |
| test_llm_provider.py | 20 | LLM Provider + 重试机制 | ✅ 通过 |
| test_output_guard.py | 22 | AI 输出验证守卫 | ✅ 通过 |
| test_parsers.py | 20 | PDF/DOCX/MD/TXT 解析器 | ✅ 通过 |
| test_prompt_template.py | 22 | Prompt 版本管理 | ✅ 通过 |
| test_providers.py | 18 | Embedding Provider | ✅ 通过 |
| test_response.py | 12 | 统一响应格式 | ✅ 通过 |
| test_services.py | 28 | 业务服务层 | ✅ 通过 |
| test_services_extended.py | 25 | 业务服务层扩展 | ✅ 通过 |
| test_sse.py | 11 | SSE 事件格式 | ✅ 通过 |
| **合计** | **212** | | **✅ 1.32s** |

### 5.2 覆盖率分析（总覆盖率 81%）

| 模块 | 语句数 | 未覆盖 | 覆盖率 | 评估 |
|------|--------|--------|--------|------|
| app/api/chat.py | 102 | 61 | 40% | ⚠️ 不足，SSE 端点未充分测试 |
| app/api/documents.py | 93 | 56 | 40% | ⚠️ 不足，上传端点未充分测试 |
| app/api/sessions.py | 41 | 0 | 100% | ✅ |
| app/api/config.py | 46 | 0 | 100% | ✅ |
| app/services/chat_service.py | 77 | 0 | 100% | ✅ |
| app/services/rag_service.py | 86 | 3 | 97% | ✅ |
| app/services/document_service.py | 142 | 50 | 65% | ⚠️ 部分分支未覆盖 |
| app/database/session.py | 30 | 20 | 33% | ⚠️ 不足，DB 连接逻辑 |
| app/providers/llm/openai_provider.py | 67 | 0 | 100% | ✅ |
| app/providers/embedding/bge_provider.py | 33 | 12 | 64% | ⚠️ 本地模型逻辑 |
| app/parsers/txt_parser.py | 30 | 10 | 67% | ⚠️ 编码检测分支 |
| **TOTAL** | **1508** | **279** | **81%** | ✅ 达标（>=80%） |

### 5.3 覆盖缺口与补充策略

| 缺口模块 | 原因 | 补充策略 |
|----------|------|----------|
| app/api/chat.py (40%) | SSE 流式端点难以纯单元测试 | 本次编写集成测试（TestClient） |
| app/api/documents.py (40%) | 文件上传 multipart 难以纯单元测试 | 本次编写集成测试（TestClient） |
| app/database/session.py (33%) | 真实 DB 连接逻辑 | E2E 测试覆盖（需真实 MariaDB） |
| app/services/document_service.py (65%) | 上传处理流水线分支 | 集成测试补充 |
| app/providers/embedding/bge_provider.py (64%) | 本地模型加载逻辑 | 需真实模型环境，标注为已知限制 |
| app/parsers/txt_parser.py (67%) | 编码检测回退分支 | 补充编码边界测试用例 |

### 5.4 已知问题（来自上游交接）

| 问题 | 严重程度 | 来源 | QA 处理 |
|------|----------|------|---------|
| PyPDF2 弃用警告 | Low | HO-009 | 记录，建议迁移 pypdf，不阻塞 |
| 整体覆盖率曾显示 35% | Medium | HO-009 | 已验证全量运行达 81%，问题已消除 |
| 前端无自动化测试 | Medium | HO-008 | 本次提供手动测试用例，自动化测试列为 V2 改进 |
| Element Plus 全量引入 929KB | Low | HO-008 | 记录，V2 按需引入 |
| 无骨架屏 | Low | HO-008 | 记录，V2 改进 |

---

## 6. 缺陷管理

### 6.1 缺陷严重程度定义

| 级别 | 定义 | 处理 |
|------|------|------|
| Critical | 系统崩溃、数据丢失、安全漏洞 | 立即修复，阻止发布 |
| High | 核心功能不可用 | 必须修复，阻止发布 |
| Medium | 功能部分可用 | 建议修复 |
| Low | 轻微问题 | 可延后修复 |

### 6.2 缺陷处理流程

```
发现缺陷 → 记录到 bug-report.md → 分配负责人 → 修复 → 回归验证 → 关闭
```

### 6.3 通过标准（G4 质量门禁）

| 门禁 | 标准 | 当前状态 |
|------|------|----------|
| G4-1 | 所有 P0 测试通过 | 待集成测试执行后确认 |
| G4-2 | 覆盖率 >= 80% | ✅ 81% |
| G4-3 | 性能指标达标 | ⏳ 需真实环境验证 |
| G4-4 | 无 Critical/High Bug | 待测试完成后确认 |
| G4-5 | RAG 闭环 E2E 通过 | ⏳ 需真实环境验证 |

---

## 7. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 无有效 OpenAI API Key 导致 E2E 无法执行 | 高 | 高 | 单元/集成测试已用 Mock 验证逻辑；E2E 用例已设计，待 Human Developer 配置环境 |
| MariaDB 未安装/未启动导致 DB 集成测试失败 | 中 | 中 | 集成测试用 SQLite 内存库；E2E 需真实 MariaDB |
| 流式输出在测试环境中不稳定 | 中 | 中 | 单元测试已 mock SSE；E2E 手动验证 |
| 性能指标因网络波动不达标 | 中 | 中 | 多次测量取 P95；区分 LLM 延迟与系统延迟 |
| 本地 BGE 模型未下载导致 Provider 切换失败 | 低 | 中 | E2E 标注需先下载模型；默认用 OpenAI |

---

## 8. 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，覆盖 4 大模块、9 类测试用例、212 个已有单元测试分析 | QA Engineer |

---

**本测试计划是 QA Engineer 的核心交付物。所有测试执行结果记录于 `docs/test-report.md`，缺陷记录于 `docs/bug-report.md`。**
