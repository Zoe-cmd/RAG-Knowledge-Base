-- ============================================
-- AI 文档知识库（MVP）数据库初始化脚本
-- Database: ai_knowledge_base
-- Engine: MariaDB 10.5+
-- Author: Database Engineer
-- Date: 2026-07-12
-- ============================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS ai_knowledge_base
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. 使用数据库
USE ai_knowledge_base;

-- 3. 创建 documents 表
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

-- 4. 创建 chat_sessions 表
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

-- 5. 创建 chat_messages 表
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

-- 6. 验证表创建
SELECT TABLE_NAME, TABLE_COMMENT, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ai_knowledge_base';

-- 7. 完成
SELECT 'Database ai_knowledge_base initialized successfully.' AS message;
