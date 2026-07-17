<!--
Document: Handoff
Phase: Phase 2（数据库设计） → Phase 2（后端开发）
From: Database Engineer
To: Backend Engineer
-->

# Handoff: Phase 2（数据库设计） → Phase 2（后端开发）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-006 |
| 交接日期 | 2026-07-12 |
| 交接方 | Database Engineer |
| 接收方 | Backend Engineer |
| 交接阶段 | Phase 2（数据库设计） → Phase 2（后端开发） |
| 交接状态 | Ready |

## 交接摘要

Phase 2 数据库设计阶段已完成。数据库工程师基于架构文档第 8 章（数据流设计）与第 9 章（API 接口设计），产出了完整的数据库 Schema 文档与迁移计划，覆盖 MariaDB 业务数据库（3 张表：documents、chat_sessions、chat_messages）与 Chroma 向量库 collection 结构设计。

关键设计成果：
- **MariaDB Schema**：3 张表，UUID 主键（CHAR(36)），utf8mb4 字符集，InnoDB 引擎，软删除策略（documents/chat_sessions），完整审计字段，CHECK 约束，外键级联（chat_messages → chat_sessions ON DELETE CASCADE）
- **核心索引**：chat_messages 表的 (session_id, created_at) 复合索引，支撑 DEC-011 多轮上下文查询（最近 4 轮 = 8 条消息）
- **Chroma collection**：命名规则 `kb_{provider}_{dimension}`（如 kb_openai_1536、kb_bge_1024），metadata 含 doc_id、doc_name、chunk_index、source_path、char_count
- **初始化脚本**：`init.sql` 一键建库建表；4 个增量迁移脚本（UP/DOWN）支持回滚
- **MariaDB 语法适配**：适配了 PostgreSQL 模板的差异（UUID 应用层生成、DATETIME(3)、JSON 类型、行内 COMMENT）

后端工程师需基于 database-schema.md 实现 SQLAlchemy 2.0 Models，基于架构文档实现 API 端点、Provider 抽象层与 SSE 流式输出。

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 数据库 Schema 文档 v1.0.0 | 文档 | docs/database-schema.md | 完成 |
| 数据库迁移计划 v1.0.0 | 文档 | docs/database-migration-plan.md | 完成 |
| 架构设计文档 v1.0.0 | 文档 | docs/architecture.md | Approved |
| PRD 文档 v1.0.0 | 文档 | docs/prd.md | Approved |
| 决策日志 | 文档 | docs/decision-log.md | 已更新（16 条决策） |
| 架构师→数据库工程师交接 | 文档 | docs/handoffs/handoff-architect-to-db.md | Confirmed |

## 关键决策（对后端开发的影响）

| 决策编号 | 决策标题 | 对后端开发的影响 |
|----------|----------|------|
| DEC-20260712-007 | 技术栈 SQLAlchemy 2.0 + asyncmy | 后端使用 SQLAlchemy 2.0 异步 ORM，asyncmy 驱动连接 MariaDB |
| DEC-20260712-008 | Embedding Provider 抽象层 | Chroma collection 命名 `kb_{provider}_{dim}`，切换 Provider 用新 collection |
| DEC-20260712-010 | SSE 流式输出 | chat_messages 表存储 elapsed_ms 与 references JSON；SSE 事件格式见架构文档 5.2 节 |
| DEC-20260712-011 | 多轮上下文截断 | 查询最近 8 条消息：`WHERE session_id=? ORDER BY created_at DESC LIMIT 8`，走复合索引 |
| DEC-20260712-016 | 递归字符切分 | chunk_size=500, overlap=50；documents 表存储 chunk_count |

## 表结构摘要（供后端工程师快速参考）

### documents 表

| 关键字段 | 类型 | 说明 |
|----------|------|------|
| id | CHAR(36) PK | UUID，应用层 `uuid.uuid4()` 生成 |
| filename | VARCHAR(255) | 原始文件名 |
| file_type | VARCHAR(20) | pdf/docx/md/txt（CHECK 约束） |
| file_size | BIGINT | 字节，≤ 20971520（20MB） |
| file_path | VARCHAR(512) | 相对路径 |
| content_hash | CHAR(64) | SHA-256，去重检测 |
| chunk_count | INT | 切片数量 |
| status | VARCHAR(20) | pending/processing/completed/failed |
| embedding_provider | VARCHAR(20) | openai/bge |
| created_at / updated_at / deleted_at | DATETIME(3) | 审计字段，软删除 |

### chat_sessions 表

| 关键字段 | 类型 | 说明 |
|----------|------|------|
| id | CHAR(36) PK | UUID |
| title | VARCHAR(255) | 默认 '新会话' |
| message_count | INT | 消息数量 |
| last_message_at | DATETIME(3) | 最后消息时间（会话列表排序） |
| created_at / updated_at / deleted_at | DATETIME(3) | 审计字段，软删除 |

### chat_messages 表

| 关键字段 | 类型 | 说明 |
|----------|------|------|
| id | CHAR(36) PK | UUID |
| session_id | CHAR(36) FK | 关联 chat_sessions.id，ON DELETE CASCADE |
| role | VARCHAR(20) | user/assistant |
| content | MEDIUMTEXT | 消息内容 |
| `references` | JSON | 引用来源数组（仅 assistant，注意保留字反引号转义） |
| elapsed_ms | INT | 流式耗时毫秒（仅 assistant） |
| created_at | DATETIME(3) | 创建时间（无 updated_at，消息不可修改） |

> **重要**：`references` 是 MariaDB 保留字，SQL 中须用反引号 `` `references` ``，SQLAlchemy 模型中建议用 `Column("references", JSON)` 显式映射列名。

### 核心索引

| 表 | 索引名 | 列 | 用途 |
|------|--------|------|------|
| chat_messages | idx_chat_messages_session_created | (session_id, created_at) | **多轮上下文查询 + 会话消息列表** |

## Chroma 向量库结构（供后端/AI 工程师参考）

### Collection 命名

```python
collection_name = f"kb_{provider_name}_{dimension}"
# 示例：kb_openai_1536、kb_bge_1024
```

### metadata 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| doc_id | string | 关联 documents.id |
| doc_name | string | 文档文件名 |
| chunk_index | int | 切片索引（从 0 开始） |
| source_path | string | 源文件路径 |
| char_count | int | 切片字符数 |
| created_at | string | ISO 8601 时间戳 |

### Chroma 操作要点

```python
import chromadb

client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_or_create_collection(
    name=f"kb_{provider}_{dimension}",
    metadata={"hnsw:space": "cosine"}
)

# 添加向量
collection.add(
    ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings,
    metadatas=[{...}]
)

# 检索（RAG 问答）
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5  # top_k=5
)

# 删除文档向量（文档删除时）
collection.delete(where={"doc_id": doc_id})
```

## 关键 SQL 查询（供后端工程师参考）

### 多轮上下文查询（DEC-011）

```sql
SELECT role, content
FROM chat_messages
WHERE session_id = :session_id
ORDER BY created_at DESC
LIMIT 8;
-- 应用层获取后反转顺序（ASC）
```

### 文档列表（分页）

```sql
SELECT id, filename, file_type, file_size, chunk_count, status, created_at
FROM documents
WHERE deleted_at IS NULL
ORDER BY created_at DESC
LIMIT :size OFFSET :offset;
```

### 会话列表

```sql
SELECT id, title, message_count, last_message_at, created_at
FROM chat_sessions
WHERE deleted_at IS NULL
ORDER BY (last_message_at IS NULL), last_message_at DESC
LIMIT 50;
```

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| `references` 是 MariaDB 保留字 | Medium | MariaDB 关键字冲突 | SQL 用反引号，SQLAlchemy 用 `Column("references", JSON)` |
| UUID 应用层生成 | Low | MariaDB 无 `gen_random_uuid()` | 后端在 Model 层用 `default=uuid.uuid4` 生成 |
| CHECK 约束依赖版本 | Low | MariaDB 10.2.1+ 才支持 CHECK 语法 | 应用层须做等效校验（file_type、status、role 枚举） |
| 无 Alembic 迁移工具 | Low | MVP 简化方案 | 手动执行 SQL 脚本；V2 引入 Alembic（DEC-013） |
| 软删除查询需显式过滤 | Low | MariaDB 不支持部分索引 | 所有查询须加 `WHERE deleted_at IS NULL` |

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 文档删除时向量未清理 | 中 | 中 | 后端 DocumentService 删除文档时先 `collection.delete(where={"doc_id": doc_id})`，再软删 MariaDB，再删文件 |
| 切换 Embedding Provider 后向量维度不匹配 | 低 | 高 | 严格用 `kb_{provider}_{dim}` collection 名；切换时创建新 collection 并重新向量化 |
| 外键级联删除误删消息 | 低 | 中 | 业务层用软删除会话（UPDATE deleted_at），不物理删除；CASCADE 仅作安全网 |
| JSON 字段查询性能 | 低 | 低 | MVP 不查询 references JSON 内容，仅整体读写；V2 如需查询可用 JSON_EXTRACT |

## 假设说明

- 假设 MariaDB 10.5+ 已本地安装，支持 JSON 类型与 utf8mb4
- 假设后端使用 SQLAlchemy 2.0 异步模式 + asyncmy 驱动
- 假设 UUID 在应用层生成（Python `uuid.uuid4()`），MariaDB 仅存储
- 假设时区 UTC，应用层处理时区转换
- 假设 Chroma 嵌入式模式，`./data/chroma` 目录可读写

## 下一步建议

对后端工程师（TASK-007）：

1. **实现 SQLAlchemy 2.0 Models**：基于 database-schema.md 第 2 章，实现 `backend/models/document.py`、`backend/models/session.py`、`backend/models/message.py`
2. **实现数据库连接层**：`backend/database/session.py`，使用 asyncmy + SQLAlchemy 异步引擎
3. **执行数据库初始化**：运行 `mysql -u root -p < backend/database/init.sql` 创建数据库与表
4. **实现 Provider 抽象层**：基于架构文档第 4 章 UML，实现 `providers/embedding/` 与 `providers/llm/`
5. **实现 Chroma 集成**：基于 database-schema.md 第 4 章，实现 Chroma client 与 collection 管理
6. **实现 API 端点**：基于架构文档第 9 章 11 个接口，实现 `api/documents.py`、`api/chat.py`、`api/sessions.py`
7. **实现 SSE 流式端点**：基于架构文档第 5 章时序图，实现 `POST /api/chat/messages` SSE 端点
8. **实现文档处理管线**：解析 → 切分（DEC-016 递归算法） → 向量化 → Chroma 存储 → MariaDB 元数据更新
9. **编写单元测试**：覆盖率 ≥ 80%，重点测试 Provider 抽象层、多轮上下文查询、文档删除同步向量

对 AI 工程师（TASK-009，可并行）：

- 基于 database-schema.md 第 4 章 Chroma 结构实现 RAG 检索管线
- 基于架构文档第 6 章实现多轮上下文组装
- 基于 DEC-016 实现递归字符切分算法

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | Backend Engineer |
| 确认状态 | Pending Confirmation |

---

**交接完成。请后端工程师阅读 `docs/database-schema.md`（重点第 2、4、8 章）与 `docs/architecture.md`（重点第 3、4、5、9 章）后开始工作。**
