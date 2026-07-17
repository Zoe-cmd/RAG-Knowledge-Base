<!--
Document: Database Migration Plan
Version: 1.0.0
Author: Database Engineer
Created: 2026-07-12
Updated: 2026-07-12
Status: Completed
-->

# 数据库迁移计划: AI 文档知识库（MVP）

## 文档元信息

| 字段 | 内容 |
|------|------|
| 文档名称 | 数据库迁移计划 |
| 项目名称 | AI 文档知识库（MVP） |
| 版本 | 1.0.0 |
| 作者 | Database Engineer |
| 创建日期 | 2026-07-12 |
| 状态 | Completed |
| 关联文档 | `docs/database-schema.md`、`docs/architecture.md` |

---

## 1. 概述

### 1.1 文档目的

本文档定义 AI 文档知识库（MVP）数据库的迁移策略、迁移文件管理、执行顺序、回滚方案与初始化流程，确保数据库结构可版本化管理、可重复执行、可安全回滚。

### 1.2 适用范围

- MariaDB 业务数据库（ai_knowledge_base）的表结构迁移
- Chroma 向量库的 collection 初始化（无迁移概念，仅初始化）
- 数据库初始化与重置流程

### 1.3 迁移原则

| 原则 | 说明 |
|------|------|
| 版本化 | 每个迁移文件有唯一版本号（时间戳命名） |
| 可回滚 | 每个迁移有对应的 DOWN 脚本 |
| 幂等 | 迁移可重复执行（使用 `IF NOT EXISTS` / `IF EXISTS`） |
| 原子性 | 每个迁移在事务中执行（BEGIN...COMMIT） |
| 向后兼容 | 迁移不破坏现有功能 |
| 手动执行 | MVP 阶段不引入 Alembic 等迁移工具，使用原生 SQL 脚本手动执行 |

### 1.4 迁移工具选择

| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| Alembic（SQLAlchemy 迁移工具） | 自动生成迁移、版本管理完善 | 增加学习成本、MVP 阶段过度设计 | ❌ V2 引入 |
| 原生 SQL 脚本 | 简单直接、可控、无额外依赖 | 需手动管理版本、无自动生成 | ✅ MVP 采用 |
| Flyway/Liquibase | 成熟的数据库迁移工具 | Java 生态、Python 项目不适用 | ❌ |

**决策**：MVP 阶段使用原生 SQL 脚本，按时间戳命名，手动执行。V2 引入 Alembic 自动化管理（DEC-013 技术债务）。

---

## 2. 迁移文件结构

### 2.1 目录结构

```
backend/
└── database/
    ├── init.sql                          # 完整初始化脚本（一键建库建表）
    ├── migrations/                       # 增量迁移脚本目录
    │   ├── 20260712000000_create_database.sql
    │   ├── 20260712000100_create_documents.sql
    │   ├── 20260712000200_create_chat_sessions.sql
    │   ├── 20260712000300_create_chat_messages.sql
    │   └── README.md                     # 迁移说明
    ├── seed/                             # 种子数据（可选）
    │   └── 20260712000400_seed_test_data.sql
    └── rollback/                         # 回滚脚本
        ├── 20260712000300_drop_chat_messages.sql
        ├── 20260712000200_drop_chat_sessions.sql
        ├── 20260712000100_drop_documents.sql
        └── 20260712000000_drop_database.sql
```

### 2.2 命名规范

```
{YYYYMMDDHHMMSS}_{description}.sql

示例：
20260712000000_create_database.sql        # 创建数据库
20260712000100_create_documents.sql       # 创建 documents 表
20260712000200_create_chat_sessions.sql   # 创建 chat_sessions 表
20260712000300_create_chat_messages.sql   # 创建 chat_messages 表
```

### 2.3 迁移文件清单

| 版本号 | 文件名 | 描述 | 类型 | 状态 |
|--------|--------|------|------|------|
| 20260712000000 | create_database.sql | 创建数据库 ai_knowledge_base | DDL | 待执行 |
| 20260712000100 | create_documents.sql | 创建 documents 表 | DDL | 待执行 |
| 20260712000200 | create_chat_sessions.sql | 创建 chat_sessions 表 | DDL | 待执行 |
| 20260712000300 | create_chat_messages.sql | 创建 chat_messages 表（含外键） | DDL | 待执行 |

### 2.4 执行顺序

**必须按版本号顺序执行**，因为 chat_messages 表依赖 chat_sessions 表（外键约束）：

```
1. 20260712000000_create_database.sql       → 创建数据库
2. 20260712000100_create_documents.sql      → 创建 documents 表（无依赖）
3. 20260712000200_create_chat_sessions.sql  → 创建 chat_sessions 表（无依赖）
4. 20260712000300_create_chat_messages.sql  → 创建 chat_messages 表（依赖 chat_sessions）
```

---

## 3. 迁移脚本

### 3.1 V20260712000000: 创建数据库

#### UP Migration

```sql
-- ============================================
-- Migration: 20260712000000_create_database
-- Description: 创建 AI 文档知识库数据库
-- Author: Database Engineer
-- Date: 2026-07-12
-- ============================================

CREATE DATABASE IF NOT EXISTS ai_knowledge_base
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ai_knowledge_base;

SELECT 'Database ai_knowledge_base created.' AS message;
```

#### DOWN Migration

```sql
-- ============================================
-- Rollback: 20260712000000_create_database
-- Description: 删除 AI 文档知识库数据库（危险操作，会丢失所有数据）
-- ============================================

-- ⚠️ 警告：此操作会删除所有数据，仅在开发环境使用
-- DROP DATABASE IF EXISTS ai_knowledge_base;

-- SELECT 'Database ai_knowledge_base dropped.' AS message;
```

> **安全策略**：DOWN 脚本默认注释，需手动取消注释执行，防止误操作。

---

### 3.2 V20260712000100: 创建 documents 表

#### UP Migration

```sql
-- ============================================
-- Migration: 20260712000100_create_documents
-- Description: 创建文档元数据表
-- Author: Database Engineer
-- Date: 2026-07-12
-- ============================================

USE ai_knowledge_base;

CREATE TABLE IF NOT EXISTS documents (
    id                  CHAR(36)        NOT NULL                                    COMMENT '文档唯一标识符（UUID）',
    filename            VARCHAR(255)    NOT NULL                                    COMMENT '原始文件名（含扩展名）',
    file_type           VARCHAR(20)     NOT NULL                                    COMMENT '文件类型：pdf/docx/md/txt',
    file_size           BIGINT          NOT NULL                                    COMMENT '文件大小（字节）',
    file_path           VARCHAR(512)    NOT NULL                                    COMMENT '存储路径（相对路径）',
    content_hash        CHAR(64)        DEFAULT NULL                                COMMENT '文件内容 SHA-256 哈希（去重检测）',
    chunk_count         INT             NOT NULL DEFAULT 0                          COMMENT '文本切片数量',
    chunk_size          INT             NOT NULL DEFAULT 500                        COMMENT '切片大小（字符数）',
    chunk_overlap       INT             NOT NULL DEFAULT 50                         COMMENT '切片重叠（字符数）',
    status              VARCHAR(20)     NOT NULL DEFAULT 'pending'                  COMMENT '处理状态：pending/processing/completed/failed',
    error_message       TEXT            DEFAULT NULL                                COMMENT '错误信息（status=failed 时）',
    embedding_provider  VARCHAR(20)     DEFAULT NULL                                COMMENT '使用的 Embedding Provider：openai/bge',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)       COMMENT '创建时间（UTC）',
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间（UTC）',
    deleted_at          DATETIME(3)     DEFAULT NULL                                COMMENT '软删除时间，NULL 表示未删除',

    PRIMARY KEY (id),
    INDEX idx_documents_status (status),
    INDEX idx_documents_created_at (created_at),
    INDEX idx_documents_content_hash (content_hash),
    INDEX idx_documents_embedding_provider (embedding_provider),

    CONSTRAINT ck_documents_file_type CHECK (file_type IN ('pdf', 'docx', 'md', 'txt')),
    CONSTRAINT ck_documents_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT ck_documents_file_size CHECK (file_size > 0 AND file_size <= 20971520)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档元数据表';

SELECT 'Table documents created.' AS message;
```

#### DOWN Migration

```sql
-- ============================================
-- Rollback: 20260712000100_create_documents
-- Description: 删除文档元数据表
-- ============================================

USE ai_knowledge_base;

DROP TABLE IF EXISTS chat_messages;  -- 先删除依赖此表的表（无直接依赖，预留）
DROP TABLE IF EXISTS documents;

SELECT 'Table documents dropped.' AS message;
```

---

### 3.3 V20260712000200: 创建 chat_sessions 表

#### UP Migration

```sql
-- ============================================
-- Migration: 20260712000200_create_chat_sessions
-- Description: 创建聊天会话表
-- Author: Database Engineer
-- Date: 2026-07-12
-- ============================================

USE ai_knowledge_base;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id                  CHAR(36)        NOT NULL                                    COMMENT '会话唯一标识符（UUID）',
    title               VARCHAR(255)    NOT NULL DEFAULT '新会话'                   COMMENT '会话标题',
    message_count       INT             NOT NULL DEFAULT 0                          COMMENT '消息数量（含 user 与 assistant）',
    last_message_at     DATETIME(3)     DEFAULT NULL                                COMMENT '最后一条消息时间',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)       COMMENT '创建时间（UTC）',
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间（UTC）',
    deleted_at          DATETIME(3)     DEFAULT NULL                                COMMENT '软删除时间，NULL 表示未删除',

    PRIMARY KEY (id),
    INDEX idx_chat_sessions_last_message_at (last_message_at),
    INDEX idx_chat_sessions_created_at (created_at),

    CONSTRAINT ck_chat_sessions_message_count CHECK (message_count >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

SELECT 'Table chat_sessions created.' AS message;
```

#### DOWN Migration

```sql
-- ============================================
-- Rollback: 20260712000200_create_chat_sessions
-- Description: 删除聊天会话表（需先删除 chat_messages）
-- ============================================

USE ai_knowledge_base;

DROP TABLE IF EXISTS chat_messages;  -- 必须先删除依赖此表的 chat_messages
DROP TABLE IF EXISTS chat_sessions;

SELECT 'Table chat_sessions dropped.' AS message;
```

---

### 3.4 V20260712000300: 创建 chat_messages 表

#### UP Migration

```sql
-- ============================================
-- Migration: 20260712000300_create_chat_messages
-- Description: 创建聊天消息表（依赖 chat_sessions）
-- Author: Database Engineer
-- Date: 2026-07-12
-- ============================================

USE ai_knowledge_base;

CREATE TABLE IF NOT EXISTS chat_messages (
    id                  CHAR(36)        NOT NULL                                    COMMENT '消息唯一标识符（UUID）',
    session_id          CHAR(36)        NOT NULL                                    COMMENT '会话 ID，关联 chat_sessions.id',
    role                VARCHAR(20)     NOT NULL                                    COMMENT '消息角色：user/assistant',
    content             MEDIUMTEXT      NOT NULL                                    COMMENT '消息内容（user 为问题，assistant 为回答）',
    `references`        JSON            DEFAULT NULL                                COMMENT '引用来源（仅 assistant，JSON 数组）',
    elapsed_ms          INT             DEFAULT NULL                                COMMENT '流式生成耗时（毫秒，仅 assistant）',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)       COMMENT '创建时间（UTC）',

    PRIMARY KEY (id),
    INDEX idx_chat_messages_session_created (session_id, created_at),
    INDEX idx_chat_messages_session_id (session_id),

    CONSTRAINT fk_chat_messages_session
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT ck_chat_messages_role CHECK (role IN ('user', 'assistant'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

SELECT 'Table chat_messages created.' AS message;
```

#### DOWN Migration

```sql
-- ============================================
-- Rollback: 20260712000300_create_chat_messages
-- Description: 删除聊天消息表
-- ============================================

USE ai_knowledge_base;

DROP TABLE IF EXISTS chat_messages;

SELECT 'Table chat_messages dropped.' AS message;
```

---

## 4. 完整初始化流程

### 4.1 首次初始化（推荐方式）

**适用场景**：全新环境搭建，数据库不存在。

**执行方式**：使用 `init.sql` 一键初始化（包含建库 + 建表）。

```bash
# 步骤 1：登录 MariaDB
mysql -u root -p

# 步骤 2：执行初始化脚本
MariaDB [(none)]> SOURCE /path/to/backend/database/init.sql;

# 步骤 3：验证
MariaDB [ai_knowledge_base]> SHOW TABLES;
+--------------------------------+
| Tables_in_ai_knowledge_base    |
+--------------------------------+
| chat_messages                  |
| chat_sessions                  |
| documents                      |
+--------------------------------+
3 rows in set (0.00 sec)
```

### 4.2 增量迁移方式

**适用场景**：数据库已存在，需按版本逐步迁移。

```bash
# 按版本号顺序执行迁移脚本
mysql -u root -p < backend/database/migrations/20260712000000_create_database.sql
mysql -u root -p < backend/database/migrations/20260712000100_create_documents.sql
mysql -u root -p < backend/database/migrations/20260712000200_create_chat_sessions.sql
mysql -u root -p < backend/database/migrations/20260712000300_create_chat_messages.sql
```

### 4.3 Chroma 向量库初始化

Chroma 无需 SQL 初始化，由后端代码在启动时自动创建：

```python
# 后端启动时自动初始化 Chroma
import chromadb

client = chromadb.PersistentClient(path="./data/chroma")

# 首次使用时创建 collection（按需创建）
# OpenAI Provider
collection_openai = client.get_or_create_collection(
    name="kb_openai_1536",
    metadata={"hnsw:space": "cosine"}
)

# BGE Provider（切换时创建）
collection_bge = client.get_or_create_collection(
    name="kb_bge_1024",
    metadata={"hnsw:space": "cosine"}
)
```

### 4.4 验证清单

初始化完成后，执行以下验证：

```sql
-- 1. 验证数据库存在
SHOW DATABASES LIKE 'ai_knowledge_base';

-- 2. 验证表结构
USE ai_knowledge_base;
SHOW TABLES;

-- 3. 验证 documents 表
DESCRIBE documents;
SHOW INDEX FROM documents;
SHOW CREATE TABLE documents\G

-- 4. 验证 chat_sessions 表
DESCRIBE chat_sessions;
SHOW INDEX FROM chat_sessions;
SHOW CREATE TABLE chat_sessions\G

-- 5. 验证 chat_messages 表
DESCRIBE chat_messages;
SHOW INDEX FROM chat_messages;
SHOW CREATE TABLE chat_messages\G

-- 6. 验证外键约束
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'ai_knowledge_base'
    AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 7. 验证字符集
SELECT TABLE_NAME, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_knowledge_base';
```

---

## 5. 回滚方案

### 5.1 回滚策略

| 场景 | 回滚方式 | 说明 |
|------|----------|------|
| 全部回滚（重置） | 执行 `rollback/` 目录下脚本，按反序执行 | 从 chat_messages → chat_sessions → documents → database |
| 单表回滚 | 执行该表的 DOWN 脚本 | 需注意依赖关系 |
| 数据损坏恢复 | 从备份恢复 `mysql < backup.sql` | 需提前有备份 |

### 5.2 完整回滚流程

```bash
# 按反序执行回滚（从最后执行的迁移开始）
mysql -u root -p < backend/database/rollback/20260712000300_drop_chat_messages.sql
mysql -u root -p < backend/database/rollback/20260712000200_drop_chat_sessions.sql
mysql -u root -p < backend/database/rollback/20260712000100_drop_documents.sql

# 可选：删除数据库（危险操作）
mysql -u root -p < backend/database/rollback/20260712000000_drop_database.sql
```

### 5.3 回滚注意事项

| 注意点 | 说明 |
|--------|------|
| 依赖顺序 | 回滚必须按反序执行（先删 chat_messages，再删 chat_sessions） |
| 数据丢失 | DROP TABLE 会丢失数据，生产环境必须先备份 |
| Chroma 数据 | 回滚 MariaDB 不影响 Chroma 数据，需手动清理 `./data/chroma` 目录 |
| 文件系统 | 回滚不影响 `./data/uploads` 目录，需手动清理 |

---

## 6. 备份与恢复

### 6.1 备份策略

| 类型 | 命令 | 频率 | 保留 |
|------|------|------|------|
| MariaDB 全量备份 | `mysqldump -u root -p ai_knowledge_base > backup_$(date +%Y%m%d).sql` | 手动（重要操作前） | 永久 |
| Chroma 数据备份 | `cp -r ./data/chroma ./data/chroma_backup_$(date +%Y%m%d)` | 手动 | 永久 |
| 文件系统备份 | `cp -r ./data/uploads ./data/uploads_backup_$(date +%Y%m%d)` | 手动 | 永久 |

> **注**：MVP 阶段无自动备份（DEC-013 技术债务），V1.5 引入自动备份脚本。

### 6.2 恢复流程

```bash
# 1. 恢复 MariaDB
mysql -u root -p
MariaDB [(none)]> DROP DATABASE IF EXISTS ai_knowledge_base;
MariaDB [(none)]> SOURCE backup_20260712.sql;

# 2. 恢复 Chroma（停服后操作）
rm -rf ./data/chroma
mv ./data/chroma_backup_20260712 ./data/chroma

# 3. 恢复文件系统
rm -rf ./data/uploads
mv ./data/uploads_backup_20260712 ./data/uploads

# 4. 重启服务
```

---

## 7. 未来迁移场景预测

### 7.1 V2 可能的迁移场景

| 场景 | 迁移内容 | 影响表 |
|------|----------|--------|
| 多用户支持 | 添加 users 表，documents/chat_sessions 添加 user_id 字段 | 所有表 |
| 多知识库 | 添加 knowledge_bases 表，documents 添加 kb_id 字段 | documents |
| 全文搜索 | 为 documents.content 添加 FULLTEXT 索引 | documents |
| 消息编辑 | chat_messages 添加 updated_at、is_edited 字段 | chat_messages |
| 标签系统 | 添加 tags 表与 document_tags 关联表 | 新表 |

### 7.2 迁移文件命名规范（V2 示例）

```
20260901000000_create_users_table.sql
20260901000100_add_user_id_to_documents.sql
20260901000200_add_user_id_to_chat_sessions.sql
20260901000300_create_knowledge_bases.sql
20260901000400_add_kb_id_to_documents.sql
```

---

## 8. 附录

### 8.1 迁移执行检查清单

执行迁移前：
- [ ] 确认 MariaDB 服务已启动（`systemctl status mariadb`）
- [ ] 确认 root 账号可登录（`mysql -u root -p`）
- [ ] 确认 MariaDB 版本 ≥ 10.5（`SELECT VERSION();`）
- [ ] 备份现有数据库（如已存在）

执行迁移后：
- [ ] 验证表已创建（`SHOW TABLES;`）
- [ ] 验证表结构正确（`DESCRIBE <table>;`）
- [ ] 验证索引存在（`SHOW INDEX FROM <table>;`）
- [ ] 验证外键约束（`SELECT * FROM information_schema.KEY_COLUMN_USAGE ...`）
- [ ] 验证字符集为 utf8mb4（`SHOW CREATE TABLE <table>;`）
- [ ] 测试基本 CRUD 操作

### 8.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ERROR 1007: Can't create database` | 数据库已存在 | 使用 `IF NOT EXISTS` 或先 `DROP DATABASE` |
| `ERROR 1215: Cannot add foreign key constraint` | 外键引用的表不存在或类型不匹配 | 确保先创建 chat_sessions 表，且 session_id 类型与 chat_sessions.id 一致（CHAR(36)） |
| `ERROR 1064: Syntax error` | SQL 语法错误 | 检查 MariaDB 版本兼容性，特别是 JSON 类型需 10.2.7+ |
| `references` 字段报错 | 保留字未转义 | 使用反引号 `` `references` `` |
| 中文显示乱码 | 字符集不是 utf8mb4 | 确认数据库与表使用 `DEFAULT CHARSET=utf8mb4` |

### 8.3 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，定义 4 个迁移脚本与回滚方案 | Database Engineer |

---

## 数据库工程师自检清单

- [x] 迁移文件命名规范（时间戳_描述.sql）
- [x] 迁移按版本号顺序执行（依赖关系正确）
- [x] 每个迁移有 UP 与 DOWN 脚本
- [x] 迁移脚本幂等（使用 IF NOT EXISTS / IF EXISTS）
- [x] 回滚脚本按反序执行（依赖关系正确）
- [x] 完整初始化脚本（init.sql）可一键执行
- [x] Chroma 初始化方式已说明（代码自动创建）
- [x] 备份与恢复流程已定义
- [x] 验证清单完整
- [x] 常见问题已列出
- [x] 无占位符/省略号
