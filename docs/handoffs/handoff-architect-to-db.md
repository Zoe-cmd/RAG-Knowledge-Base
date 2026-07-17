<!--
Document: Handoff
Phase: Phase 1（需求与设计） → Phase 2（数据与后端）
From: Solution Architect
To: Database Engineer
-->

# Handoff: Phase 1（架构设计） → Phase 2（数据库设计）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-005 |
| 交接日期 | 2026-07-12 |
| 交接方 | Solution Architect |
| 接收方 | Database Engineer |
| 交接阶段 | Phase 1（架构设计） → Phase 2（数据库设计） |
| 交接状态 | Confirmed |

## 交接摘要

Phase 1 架构设计阶段已完成。系统架构师基于 PRD（4 大功能模块、20 个用户故事）与 UI/UX 设计文档，产出了完整的架构设计文档 `docs/architecture.md`，覆盖系统上下文图、容器架构图、模块化单体架构（后端 API/Service/Provider/Data 五层 + 前端组件结构）、Provider 抽象层 UML 类图（EmbeddingProvider + LLMProvider）、SSE 流式输出时序图（正常/停止/异常/无内容）、多轮上下文组装流程图、递归字符切分算法、数据流设计（上传流 + 问答流 + 数据存储分配）、API 接口设计（11 个接口）、非功能需求实现方案、配置设计（.env + Pydantic Settings）、部署架构（本地启动方案）。

架构设计已通过 G2 架构评审（Tech Lead + Human Developer 审批通过 2026-07-12），追加 3 项架构决策（DEC-014 模块化单体架构、DEC-015 Vite Proxy 通信、DEC-016 递归字符切分算法）到决策日志。

数据库工程师需基于架构文档第 8 章"数据流设计"的 8.3 节"数据存储分配"与第 9 章"API 接口设计"，设计 MariaDB 业务数据库 Schema（documents、chat_sessions、chat_messages 三张表）与 Chroma 向量库 collection 结构，并编写可执行的初始化 SQL 脚本与迁移计划。

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 架构设计文档 v1.0.0 | 文档 | docs/architecture.md | Approved |
| PRD 文档 v1.0.0 | 文档 | docs/prd.md | Approved |
| 设计系统文档 | 文档 | docs/design-system.md | Approved |
| 用户流程文档 | 文档 | docs/user-flows.md | Approved |
| 线框图文档 | 文档 | docs/wireframes.md | Approved |
| 高保真原型文档 | 文档 | docs/mockups.md | Approved |
| 技术评审报告 | 文档 | docs/tech-review-report.md | Approved |
| 决策日志 | 文档 | docs/decision-log.md | 已更新（16 条决策 DEC-001~016） |
| UI/UX → 架构师交接 | 文档 | docs/handoffs/handoff-uiux-to-architect.md | Confirmed |

## 关键决策

| 决策编号 | 决策标题 | 对数据库设计的影响 |
|----------|----------|------|
| DEC-20260712-001 | 本地 localhost 运行 | MariaDB 本地安装，绑定 127.0.0.1 |
| DEC-20260712-005 | 禁用 Docker，MariaDB 本地安装 | 数据库必须本地原生安装，不可容器化；初始化脚本需支持手动执行 |
| DEC-20260712-007 | 技术栈确认（MariaDB + Chroma） | 业务数据用 MariaDB；向量数据用 Chroma 嵌入式持久化 |
| DEC-20260712-008 | Embedding Provider 抽象层 | Chroma collection 命名需含 provider 与维度信息（如 `kb_openai_1536`） |
| DEC-20260712-010 | SSE 流式输出 | chat_messages 表需存储 elapsed_ms（流式耗时）与 references（引用 JSON） |
| DEC-20260712-011 | 多轮上下文截断策略 | chat_messages 表需支持按 session_id 查询最近 4 轮（8 条消息）的快速检索，需索引 |
| DEC-20260712-012 | 本地 Embedding 选 bge-m3 | Chroma 可能存在 `kb_bge_1024` collection（bge-m3 维度 1024） |
| DEC-20260712-013 | 技术债务基线 | Chroma 单机嵌入式无备份自动化（V1.5 偿还），文档需说明手动备份 |
| DEC-20260712-014 | 模块化单体架构 | 数据层通过 SQLAlchemy 2.0 ORM 访问，数据库工程师定义 Schema，后端工程师实现 Model |
| DEC-20260712-016 | 递归字符切分算法 | documents 表需存储 chunk_count（切片数量）；Chroma metadata 需含 chunk_index |

## 数据存储分配（架构文档 8.3 节摘录）

| 数据类型 | 存储位置 | 说明 |
|----------|----------|------|
| 文档元数据 | MariaDB `documents` 表 | 文件名、类型、大小、切片数、状态 |
| 会话数据 | MariaDB `chat_sessions` 表 | 会话标题、消息数、时间 |
| 消息数据 | MariaDB `chat_messages` 表 | 问答内容、引用 JSON、耗时 |
| 向量数据 | Chroma `kb_{provider}_{dim}` | chunk 文本、embedding、metadata |
| 原文件 | 文件系统 `./data/uploads/` | 上传的原始文件 |

## API 接口对数据字段的要求（架构文档第 9 章摘录）

数据库工程师需确保 Schema 字段能支撑以下 API 响应：

### 文档列表 API 响应字段
- `id`、`filename`、`file_type`、`file_size`、`chunk_count`、`status`、`created_at`

### 会话 API 响应字段
- 会话：`id`、`title`、`created_at`
- 消息：`id`、`role`（user/assistant）、`content`、`references`（JSON 数组，仅 assistant）、`elapsed_ms`（仅 assistant）、`created_at`

## Chroma 向量库设计约束

| 约束 | 说明 |
|------|------|
| collection 命名规则 | `kb_{provider}_{dimension}`，如 `kb_openai_1536`、`kb_bge_1024` |
| 持久化目录 | `./data/chroma`（DEC-007，嵌入式模式） |
| 文档 metadata 字段 | `doc_id`（关联 MariaDB documents.id）、`doc_name`、`chunk_index`、`source_path`、`char_count` |
| 切换 Provider | 使用新 collection，旧 collection 保留但不再使用；需对文档重新 Embedding |
| 删除文档 | 需同步删除 Chroma 中该 doc_id 的所有向量（架构文档 10.2 节） |

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| 数据库模板基于 PostgreSQL，项目实际用 MariaDB | Medium | 模板使用 `gen_random_uuid()`、`TIMESTAMPTZ`、`JSONB`、部分索引 `WHERE` 等 PostgreSQL 特有语法 | 数据库工程师需适配 MariaDB 语法：UUID 用 `UUID()` 函数或应用层生成、时间用 `DATETIME(3)`、JSON 用 `JSON` 类型、部分索引改用普通索引或生成列 |
| Chroma 无 Schema 定义文件 | Low | Chroma 是嵌入式向量库，Schema 由代码创建 | 数据库工程师在 database-schema.md 中描述 Chroma collection 结构与 metadata 字段定义即可，无需 DDL |
| 软删除策略需明确 | Low | database-standard 要求软删除，但文档/会话删除时需同步清理 Chroma 向量与文件系统 | documents 与 chat_sessions 表使用 `deleted_at` 软删除；删除文档时业务层同步清理 Chroma 向量与文件（后端工程师实现） |

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| MariaDB 与 PostgreSQL 语法差异导致 DDL 不可执行 | 中 | 高 | 数据库工程师严格使用 MariaDB 10.5+ 兼容语法；避免 PostgreSQL 特有功能；DDL 在本地 MariaDB 验证 |
| Chroma collection 命名不一致导致向量数据错乱 | 低 | 高 | 严格遵循 `kb_{provider}_{dimension}` 命名规则；切换 Provider 时创建新 collection |
| 多轮上下文查询性能差 | 低 | 中 | chat_messages 表对 (session_id, created_at) 建复合索引，支持快速查询最近 N 条消息 |
| 文档删除后向量未清理导致脏数据 | 中 | 中 | 后端工程师在删除文档时同步删除 Chroma 向量（架构文档已明确）；数据库 Schema 文档需说明此约束 |

## 假设说明

- 假设 MariaDB 10.5+ 已本地安装，支持 JSON 类型与 `utf8mb4` 字符集
- 假设数据量较小（MVP 阶段文档 ≤ 100 个，消息 ≤ 10000 条），无需分库分表
- 假设 Chroma 嵌入式模式数据目录 `./data/chroma` 可读写
- 假设主键使用 UUID（应用层用 Python `uuid4()` 生成，MariaDB 存储为 `CHAR(36)` 或 `BINARY(16)`）
- 假设时区使用 UTC，应用层处理时区转换

## 下一步建议

对数据库工程师（TASK-006）：

1. **优先设计 MariaDB Schema**：基于架构文档 8.3 节数据存储分配，设计 `documents`、`chat_sessions`、`chat_messages` 三张表，字段需支撑 API 接口响应（架构文档第 9 章）
2. **适配 MariaDB 语法**：注意 PostgreSQL 模板与 MariaDB 的差异（UUID、时间类型、JSON 类型、部分索引）
3. **设计 Chroma collection 结构**：在 database-schema.md 中描述 collection 命名规则、metadata 字段、与 MariaDB 的关联关系
4. **编写初始化 SQL**：提供 `init.sql` 脚本，可一键创建数据库与表结构
5. **编写迁移计划**：提供 UP/DOWN 迁移脚本，支持回滚
6. **重点关注索引**：chat_messages 表的 (session_id, created_at) 复合索引是 RAG 多轮上下文查询的关键
7. **交付物**：`docs/database-schema.md`、`docs/database-migration-plan.md`，并编写交接文档给后端工程师

对后端工程师（TASK-007，后续）：

- 基于 database-schema.md 实现 SQLAlchemy 2.0 Models
- 基于 Provider 抽象层 UML（架构文档第 4 章）实现 Embedding/LLM Provider
- 基于 API 接口设计（架构文档第 9 章）实现 11 个 API 端点
- 基于 SSE 时序图（架构文档第 5 章）实现流式问答端点

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 2026-07-12 |
| 确认人 | Database Engineer |
| 确认状态 | Confirmed |

---

**交接完成。请数据库工程师阅读 `docs/architecture.md`（重点第 8、9 章）与 `docs/prd.md` 后开始工作。**
