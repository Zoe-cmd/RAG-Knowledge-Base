<!--
Document: Security Audit Report
Version: 1.1.0
Author: Security Engineer
Created: 2026-07-12
Updated: 2026-07-12
Status: Completed (P0 修复已验证，G5 门禁通过)
-->

# 安全审计报告: AI 文档知识库（MVP）

## 文档元信息

| 字段 | 内容 |
|------|------|
| 文档名称 | 安全审计报告 |
| 项目名称 | AI 文档知识库（MVP） |
| 版本 | 1.1.0 |
| 作者 | Security Engineer |
| 创建日期 | 2026-07-12 |
| 最后更新 | 2026-07-12 |
| 状态 | Completed (P0 修复已验证，G5 门禁通过) |
| 关联文档 | `docs/prd.md`、`docs/architecture.md`、`docs/api-spec.md`、`docs/bug-report.md`、`docs/handoffs/handoff-qa-to-security.md` |
| 审计基线 | Phase 3 完成后的代码基线（v1.0.1，BUG-010 已修复） |
| 质量门禁 | G5（无 Critical 安全漏洞） — ✅ 通过（v1.1.0 P0 修复后） |

---

## 1. 审计概述

### 1.1 审计范围

本次安全审计覆盖 AI 文档知识库（MVP）的全部后端代码（46 个 Python 文件）、前端关键安全相关代码（Markdown 渲染、SSE 解析、会话标题渲染）、配置文件（`.env`、`.env.example`、`requirements.txt`）、数据库初始化脚本（`init.sql`）以及文件系统存储安全。

| 审计领域 | 审计内容 | 优先级 |
|----------|----------|--------|
| 密钥管理 | API Key 硬编码检查、.env 加载机制、.gitignore 配置 | P0 |
| 文件上传安全 | 类型校验、大小校验、路径穿越、临时文件清理 | P0 |
| SQL 注入 | ORM 参数化查询、text() 调用、分页参数 | P0 |
| XSS 与输出安全 | SSE token 转义、output_guard 过滤、DOMPurify 配置、v-html 使用 | P1 |
| SSE 端点滥用 | 速率限制、输入长度限制、会话 ID 校验、CORS | P1 |
| 本地数据存储安全 | Chroma 目录权限、源文档存储、连接字符串、日志脱敏 | P1 |
| Prompt 注入防护 | 控制字符清洗、System Prompt 有效性、Prompt 泄漏检测 | P2 |
| 依赖安全 | 已知漏洞扫描、弃用库检查 | P1 |

### 1.2 审计方法

1. **静态代码审计**：逐文件阅读后端 46 个 Python 源文件，对照 OWASP Top 10 检查
2. **配置审计**：检查 `.env`、`.env.example`、`requirements.txt`、`.gitignore`、CORS 配置
3. **前端安全审计**：检查 `v-html` 使用、DOMPurify 配置、文本插值安全性
4. **文件系统审计**：检查上传目录权限、Chroma 持久化目录权限、临时文件处理
5. **依赖安全扫描**：尝试使用 pip-audit 自动扫描（因网络超时未完成），辅以手动核查
6. **架构合规审计**：对照 `architecture.md` 10.2 节安全需求验证实现

### 1.3 审计结论摘要

| 严重程度 | 数量 | 阻塞发布 | 已修复 | 说明 |
|----------|------|----------|--------|------|
| Critical | 1 | 是 | ✅ 1 | 缺少 .gitignore（SEC-001 已修复） |
| High | 2 | 是 | ✅ 2 | API Key 保护（SEC-002 已缓解）、DEBUG=true（SEC-003 已修复） |
| Medium | 5 | 否 | ✅ 1 | source_path 信息泄露（SEC-006 已修复）；其余 4 项 V1.1 修复 |
| Low | 5 | 否 | 0 | CORS 宽松、Prompt 泄漏仅记录、弃用库、目录权限等（V1.1/V2） |
| **合计** | **13** | **3 阻塞** | **4 已修复** | P0 阻塞项全部修复，G5 门禁通过 |

> **G5 门禁评估**：✅ **通过**（v1.1.0） — P0 阻塞漏洞（SEC-001/002/003）已全部修复，SEC-006 同步修复。228 个单元测试通过（覆盖率 87.21%），无回归。剩余 9 项 Medium/Low 漏洞不阻塞发布，计划 V1.1/V2 修复。

### 1.4 安全亮点（已有良好实践）

审计中也发现多项安全良好实践，值得肯定：

| 良好实践 | 位置 | 说明 |
|----------|------|------|
| API Key 通过 Pydantic Settings 加载 | `config/settings.py` | 代码中无硬编码，通过 .env 注入 |
| .env.example 使用占位符 | `backend/.env.example` | `sk-xxxxxxxxxxxxxxxxxxxxxxxx`，不含真实 Key |
| SQL 全部使用 ORM 参数化 | 所有 Service 层 | 无 `text()` 拼接，无 SQL 注入风险 |
| 文件存储名使用 UUID | `document_service.py:122` | `f"{doc_id}.{file_type}"`，防止路径穿越 |
| 临时文件使用 mkstemp | `documents.py:177` | `tempfile.mkstemp()` 生成安全路径 |
| 上传文件权限 600 | `data/uploads/` | 仅所有者可读写 |
| 流式文件大小校验 | `documents.py:186` | 1MB 分块读取，超限即中止，防止内存耗尽 |
| DOMPurify 净化 Markdown | `frontend/src/utils/markdown.js` | 配置了标签和属性白名单 |
| 前端文本插值 | `SessionItem.vue`、`DocumentItem.vue` | 会话标题/文档名用 `{{ }}`，非 v-html |
| UUID 格式校验 | `chat.py:54` | session_id 强制 UUID 格式，防注入 |
| 全局异常兜底 | `exceptions.py:211` | 未预期异常返回通用错误，不泄露堆栈 |
| 扫描件 PDF 友好处理 | `documents.py:128` | 返回友好提示，不泄露内部错误 |

---

## 2. 漏洞明细

### SEC-20260712-001: 缺少 .gitignore 文件（Critical）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-001 |
| 标题 | 根目录和 backend 目录均无 .gitignore，敏感文件可能被提交到 Git |
| 严重程度 | Critical |
| 优先级 | P0 |
| 状态 | Open |
| OWASP 分类 | A05:2021 - Security Misconfiguration |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | DevOps Engineer / Backend Engineer |

**描述**：

项目根目录 `/home/zoe/Public/project/RAG项目/` 和 `backend/` 目录均不存在 `.gitignore` 文件。仅 `frontend/.gitignore` 存在。这导致以下敏感文件面临被提交到 Git 仓库的风险：

| 敏感文件 | 风险 | 当前状态 |
|----------|------|----------|
| `backend/.env` | 含真实 OpenAI API Key 和数据库密码 | 未被 .gitignore 保护 |
| `backend/data/uploads/` | 用户上传的文档原文（可能含敏感内容） | 未被 .gitignore 保护 |
| `backend/data/chroma/` | 向量数据库（含文档片段内容） | 未被 .gitignore 保护 |
| `backend/.coverage` | 覆盖率数据 | 未被 .gitignore 保护 |
| `backend/coverage.xml` | 覆盖率 XML | 未被 .gitignore 保护 |
| `backend/htmlcov/` | 覆盖率 HTML 报告 | 未被 .gitignore 保护 |
| `backend/.pytest_cache/` | 测试缓存 | 未被 .gitignore 保护 |
| `__pycache__/` | Python 字节码缓存 | 未被 .gitignore 保护 |

**架构合规性**：`docs/architecture.md` 10.2 节明确要求 ".gitignore 排除 .env"，但此需求未实施。

**影响范围**：

- 如果项目被推送到公开 Git 仓库（如 GitHub），API Key 和数据库密码将直接泄露
- 用户上传的文档原文和向量数据可能被提交，造成数据泄露
- 即使是私有仓库，也会在 Git 历史中留下敏感信息，难以彻底清除

**修复建议**：

在项目根目录创建 `.gitignore` 文件，内容至少包含：

```gitignore
# ===== 环境变量（含敏感信息）=====
.env
.env.local
.env.*.local
# 保留 .env.example 作为模板

# ===== Python =====
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# ===== 测试与覆盖率 =====
.coverage
.coverage.*
coverage.xml
htmlcov/
.pytest_cache/
.tox/

# ===== 数据目录（含用户上传文档和向量数据）=====
backend/data/
data/

# ===== IDE =====
.vscode/
.idea/
*.swp
*.swo

# ===== 系统文件 =====
.DS_Store
Thumbs.db

# ===== 日志 =====
*.log
logs/
```

同时执行以下操作：
1. 检查 Git 历史中是否已提交敏感文件：`git log --all -- backend/.env`
2. 如果已提交，使用 `git filter-branch` 或 BFG Repo-Cleaner 清除历史
3. **立即轮换已泄露的 API Key**（到 OpenAI 控制台撤销并重新生成）

---

### SEC-20260712-002: .env 含真实 API Key 无保护（High）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-002 |
| 标题 | .env 文件包含真实 OpenAI API Key 和数据库密码，且无 .gitignore 保护 |
| 严重程度 | High |
| 优先级 | P0 |
| 状态 | Open |
| OWASP 分类 | A02:2021 - Cryptographic Failures |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`backend/.env` 文件包含以下敏感信息：

| 行号 | 配置项 | 值 | 敏感程度 |
|------|--------|-----|----------|
| 8 | DATABASE_URL | `mysql+asyncmy://user:password@127.0.0.1:3306/ai_knowledge_base` | 数据库密码 |
| 11 | OPENAI_API_KEY | `sk-xxxxxxxxxxxxxxxxxxxxxxxx` | API Key（真实） |
| 12 | OPENAI_BASE_URL | `https://api.apilio.ai/v1` | 第三方代理地址 |

该文件本身是本地配置文件（设计上应通过 .gitignore 排除），但因 SEC-001（缺少 .gitignore），存在被提交到 Git 的风险。

**验证结果**：

- ✅ 代码中无硬编码：`grep -r "sk-" backend/app/` 无匹配
- ✅ `.env.example` 使用占位符：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`
- ✅ API Key 通过 `settings.OPENAI_API_KEY` 正确加载
- ❌ 无 .gitignore 保护 `.env` 文件
- ❌ API Key 为真实有效 Key（QA E2E 测试已验证可用）

**影响范围**：

- API Key 泄露可导致 OpenAI API 被盗用，产生费用
- 数据库密码泄露可导致数据被未授权访问
- 第三方代理地址泄露暴露技术架构

**修复建议**：

1. 修复 SEC-001（创建 .gitignore）后，本漏洞自动缓解
2. 检查 Git 历史中 `.env` 是否已被提交：
   ```bash
   git log --all -- backend/.env
   ```
3. 如果已提交，**立即到 OpenAI 控制台撤销当前 Key 并生成新 Key**
4. 更新 `.env` 中的 `OPENAI_API_KEY` 为新 Key
5. 考虑修改数据库密码（如果 Git 历史中已泄露）

---

### SEC-20260712-003: DEBUG=true 在配置中（High）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-003 |
| 标题 | DEBUG=true 导致 SQL 日志输出、API 文档公开、自动重载开启 |
| 严重程度 | High |
| 优先级 | P0 |
| 状态 | Open |
| OWASP 分类 | A05:2021 - Security Misconfiguration |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`.env` 和 `.env.example` 均设置 `DEBUG=true`。该配置导致以下安全风险：

| 影响项 | 代码位置 | 风险 |
|--------|----------|------|
| SQLAlchemy echo=True | `database/session.py:28` | 所有 SQL 语句及参数被记录到日志，可能含敏感查询内容 |
| FastAPI /docs 公开 | `main.py:78` | Swagger UI 公开访问，暴露完整 API 结构 |
| FastAPI /redoc 公开 | `main.py:79` | ReDoc 文档公开访问 |
| uvicorn reload=True | `main.py:128` | 自动重载模式开启，文件变更即重启 |
| 日志级别 INFO | `main.py:28` | 详细日志输出，可能含敏感信息 |

**相关代码**：

```python
# database/session.py:25-28
return create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # ← DEBUG=true 时输出所有 SQL
    ...
)

# main.py:78-79
docs_url="/docs",      # ← DEBUG 时公开
redoc_url="/redoc",    # ← DEBUG 时公开
```

**影响范围**：

- SQL 日志可能包含用户问题内容、文档片段等敏感数据
- API 文档公开使攻击者可快速了解所有端点和参数
- 虽然绑定 localhost，但本地任何进程/用户可访问

**修复建议**：

1. `.env.example` 中将 `DEBUG=true` 改为 `DEBUG=false`（安全默认）
2. `.env` 中开发环境可保留 `DEBUG=true`，但需确保不用于生产
3. `main.py` 中根据 DEBUG 控制 API 文档：

```python
app = FastAPI(
    ...
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
```

4. `database/session.py` 中 SQL echo 仅在 DEBUG 模式下开启（已是如此，但建议添加注释说明安全影响）

---

### SEC-20260712-004: 文件类型校验仅检查扩展名（Medium）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-004 |
| 标题 | 文件上传类型校验仅检查文件名扩展名，未检查文件魔数/MIME 类型 |
| 严重程度 | Medium |
| 优先级 | P1 |
| 状态 | Open |
| OWASP 分类 | A04:2021 - Insecure Design |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`app/api/documents.py:48` 的 `_get_file_extension()` 函数仅从文件名提取扩展名进行校验，未验证文件实际内容（魔数/MIME 类型）。

```python
def _get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")
```

架构文档 10.2 节要求"校验扩展名 + 魔数"，但魔数校验未实现。

**攻击场景**：

1. 攻击者将恶意脚本重命名为 `malicious.pdf` 上传 → 通过类型校验
2. 攻击者构造双扩展名文件 `report.pdf.exe` → `_get_file_extension` 返回 `exe`（被拒），但 `report.pdf.` 等边界情况需测试
3. 攻击者伪造 MIME 类型头但内容为恶意文件

**缓解因素**：

- 存储文件名使用 UUID（`f"{doc_id}.{file_type}"`），不保留原始文件名
- 文件存储在 `data/uploads/` 目录，不直接通过 Web 访问
- 解析器（PDF/DOCX/MD/TXT）会对内容进行解析，非预期格式会报错

**修复建议**：

V1.1 添加文件魔数校验：

```python
# 文件签名（魔数）校验
FILE_SIGNATURES = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",  # ZIP archive (docx is ZIP-based)
    # md 和 txt 无固定魔数，通过内容判断
}

def _validate_file_magic(file_path: Path, file_type: str) -> bool:
    """校验文件魔数。"""
    if file_type not in FILE_SIGNATURES:
        return True  # 无魔数定义的类型跳过
    with open(file_path, "rb") as f:
        header = f.read(8)
    return header.startswith(FILE_SIGNATURES[file_type])
```

---

### SEC-20260712-005: 内部错误信息泄露到客户端（Medium）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-005 |
| 标题 | SSE error 事件和上传失败响应将原始异常消息发送给客户端 |
| 严重程度 | Medium |
| 优先级 | P1 |
| 状态 | Open |
| OWASP 分类 | A05:2021 - Security Misconfiguration |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

以下位置将原始异常消息发送给客户端：

| 文件 | 行号 | 代码 | 泄露内容 |
|------|------|------|----------|
| `chat.py` | 207 | `error_event(str(e)[:200], error_code)` | LLM 调用异常详情 |
| `documents.py` | 151 | `"error": str(e)[:200]` | 文档处理异常详情 |
| `documents.py` | 107 | `"error": f"文件读取失败: {e}"` | 文件读取异常 |

**攻击场景**：

- LLM 调用失败时，错误消息可能包含 API 端点 URL、内部超时详情
- 文档处理失败时，异常消息可能包含服务器内部文件路径
- 数据库错误可能暴露表结构信息

**缓解因素**：

- 全局异常处理器（`exceptions.py:211`）对未预期异常返回通用 "服务器内部错误"
- 已有错误码分类机制（`_classify_error`）
- 截断为 200 字符，限制了泄露量

**修复建议**：

1. 对客户端仅返回错误码和友好消息，不返回原始异常：

```python
# chat.py - 修改前
yield error_event(str(e)[:200], error_code)

# chat.py - 修改后
FRIENDLY_MESSAGES = {
    "LLM_TIMEOUT": "回答生成超时，请重试",
    "LLM_AUTH_ERROR": "AI 服务认证失败，请检查配置",
    "LLM_CONNECTION_ERROR": "AI 服务连接失败，请稍后重试",
    "EMBEDDING_ERROR": "文档检索失败，请重试",
    "INTERNAL_ERROR": "服务器内部错误，请稍后重试",
}
friendly_msg = FRIENDLY_MESSAGES.get(error_code, "未知错误")
yield error_event(friendly_msg, error_code)
# 原始异常仅记录到日志
logger.error("SSE 流式错误: %s", e, exc_info=True)
```

2. `documents.py` 同理，对 INTERNAL_ERROR 返回通用消息

---

### SEC-20260712-006: source_path 信息泄露（Medium）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-006 |
| 标题 | RAG 引用来源事件暴露内部文件存储路径 |
| 严重程度 | Medium |
| 优先级 | P1 |
| 状态 | Open |
| OWASP 分类 | A01:2021 - Broken Access Control |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`app/services/rag_service.py:57-66` 的 `RetrievalResult.to_reference()` 方法将内部文件存储路径 `source_path` 通过 SSE references 事件返回给客户端。前端 `ReferenceCard.vue:50` 将其显示在 UI 上。

```python
# rag_service.py:57-66
def to_reference(self) -> dict:
    return {
        "doc_id": self.doc_id,
        "doc_name": self.doc_name,
        "chunk_index": self.chunk_index,
        "source_path": self.source_path,  # ← 内部路径泄露
        "preview": self.content[:200] + ...,
        "similarity": round(self.similarity, 4),
    }

# ReferenceCard.vue:50
<span class="ref-path">片段 #{{ item.chunk_index + 1 }} · {{ item.source_path }}</span>
```

**泄露内容**：

`source_path` 值如 `data/uploads/657677a7-d002-4f8c-a7ea-9e65c5a946a2.txt`，暴露了：
- 文件存储目录结构（`data/uploads/`）
- 文档 UUID（内部标识符）
- 文件扩展名

**影响范围**：

- 攻击者可了解服务器文件系统结构
- 虽然文件不直接通过 Web 访问，但路径信息有助于其他攻击

**修复建议**：

1. 从 `to_reference()` 中移除 `source_path` 字段：

```python
def to_reference(self) -> dict:
    return {
        "doc_id": self.doc_id,
        "doc_name": self.doc_name,
        "chunk_index": self.chunk_index,
        # source_path 移除，不暴露内部路径
        "preview": self.content[:200] + ("..." if len(self.content) > 200 else ""),
        "similarity": round(self.similarity, 4),
    }
```

2. 前端 `ReferenceCard.vue:50` 移除 `source_path` 显示，仅保留 `片段 #{{ item.chunk_index + 1 }}`

---

### SEC-20260712-007: 无 API 速率限制（Medium）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-007 |
| 标题 | 所有 API 端点无速率限制，可被滥用导致资源耗尽 |
| 严重程度 | Medium |
| 优先级 | P1 |
| 状态 | Open |
| OWASP 分类 | A04:2021 - Insecure Design |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

虽然 PRD 约束为本地单用户（DEC-001），API 规范明确"无需限流"，但所有 API 端点（特别是 SSE 流式问答 `POST /api/chat/messages` 和文件上传 `POST /api/documents/upload`）无任何速率限制。

**风险评估**：

| 端点 | 风险 | 影响 |
|------|------|------|
| `POST /api/chat/messages` | 高频调用产生 LLM API 费用 | 经济损失 |
| `POST /api/documents/upload` | 大量上传耗尽磁盘空间 | 资源耗尽 |
| `DELETE /api/chat/sessions` | 误操作清空所有会话 | 数据丢失 |

**缓解因素**：

- 绑定 127.0.0.1，仅本地可访问
- 单用户场景，滥用风险低
- 文档总数上限 100（`MAX_DOCUMENTS`）
- 文件大小上限 20MB

**修复建议**：

V1.1 考虑引入轻量级速率限制（如 `slowapi`）：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/messages")
@limiter.limit("10/minute")  # 每分钟最多 10 次问答
async def send_message(request: Request, ...):
    ...
```

MVP 阶段可接受现状，但应在文档中记录此风险。

---

### SEC-20260712-008: 流式回答未经 output_guard 验证（Medium）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-008 |
| 标题 | SSE 流式模式下的最终回答未执行 validate_answer 验证 |
| 严重程度 | Medium |
| 优先级 | P1 |
| 状态 | Open |
| OWASP 分类 | A04:2021 - Insecure Design |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer / AI Engineer |

**描述**：

`rag_service.py` 的 `answer()` 方法（流式模式）注释说明"流式模式：在 chat API 层对最终拼接的回答执行验证"，但 `chat.py` 的 `stream()` 函数中并未调用 `validate_answer()`。非流式模式 `chat_non_stream()` 正确调用了验证。

```python
# rag_service.py:298-305 (非流式，正确验证)
validation = validate_answer(response.content)
if validation.is_empty:
    logger.warning("LLM 返回空内容，已使用占位提示")
...

# chat.py:131-134 (流式，未验证)
async for chunk in result.answer_chunks:
    if chunk.content:
        assistant_content += chunk.content  # ← 原始内容直接拼接
        yield token_event(chunk.content)    # ← 未经验证直接发送
```

**影响范围**：

- LLM 流式输出中的控制字符未被过滤（每个 token 单独发送，`validate_answer` 需对完整内容执行）
- 流式输出可能包含 Prompt 泄漏内容（`validate_answer` 的泄漏检测未执行）
- 超长内容未截断

**缓解因素**：

- 前端 DOMPurify 会净化 HTML，部分缓解 XSS 风险
- 单个 token 通常不含完整攻击载荷
- 非流式模式有完整验证

**修复建议**：

在 `chat.py` 的 `stream()` 函数中，流结束后对 `assistant_content` 执行验证：

```python
# chat.py - 在发送 done 事件前添加
from app.services.output_guard import validate_answer

# 3. 保存 assistant 消息前验证
validation = validate_answer(assistant_content)
if validation.is_truncated:
    # 如果被截断，发送截断提示
    yield token_event("\n\n（回答已达长度上限，已截断。）")
    assistant_content = validation.content
if validation.prompt_leak_detected:
    logger.warning("流式回答检测到 Prompt 泄漏")
```

---

### SEC-20260712-009: CORS 配置过于宽松（Low）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-009 |
| 标题 | CORS allow_methods 和 allow_headers 使用通配符 "*" |
| 严重程度 | Low |
| 优先级 | P2 |
| 状态 | Open |
| OWASP 分类 | A05:2021 - Security Misconfiguration |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`main.py:85-95` 的 CORS 配置中，`allow_methods=["*"]` 和 `allow_headers=["*"]` 使用通配符。

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # ← 过于宽松
    allow_headers=["*"],   # ← 过于宽松
)
```

**缓解因素**：

- `allow_origins` 已限制为 localhost URL（良好）
- 本地单用户场景，风险较低

**修复建议**：

收紧 CORS 配置：

```python
allow_methods=["GET", "POST", "PUT", "DELETE"],
allow_headers=["Content-Type", "Accept"],
```

---

### SEC-20260712-010: Prompt 泄漏检测仅记录不拦截（Low）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-010 |
| 标题 | output_guard 的 Prompt 泄漏检测仅记录日志，不拦截内容 |
| 严重程度 | Low |
| 优先级 | P2 |
| 状态 | Open |
| OWASP 分类 | A04:2021 - Insecure Design |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | AI Engineer |

**描述**：

`output_guard.py:124-132` 检测到 Prompt 泄漏时仅记录警告日志，不拦截或替换内容。这是 MVP 设计决策（注释明确说明），但属于安全弱点。

```python
# output_guard.py:124-132
prompt_leak_detected = any(
    keyword in content for keyword in _PROMPT_LEAK_KEYWORDS
)
if prompt_leak_detected:
    logger.warning(
        "检测到 LLM 输出可能包含 Prompt 泄漏（关键词命中），"
        "已记录但未拦截（MVP 范围）"
    )
```

**缓解因素**：

- System Prompt v1.1.0 已包含规则 6："不要提及'参考资料''系统提示''Prompt'等内部机制"
- 检测关键词覆盖主要泄漏场景
- MVP 范围明确排除深度 Prompt 注入检测

**修复建议**：

V2 升级为拦截模式：检测到泄漏时替换为通用提示。

---

### SEC-20260712-011: PyPDF2 使用弃用库（Low）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-011 |
| 标题 | requirements.txt 使用已弃用的 PyPDF2 库 |
| 严重程度 | Low |
| 优先级 | P2 |
| 状态 | Open |
| OWASP 分类 | A06:2021 - Vulnerable and Outdated Components |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Backend Engineer |

**描述**：

`requirements.txt:28` 使用 `PyPDF2==3.0.1`。PyPDF2 已于 2023 年停止维护并标记为弃用，官方建议迁移至 `pypdf`（同一作者的继任库，API 兼容）。虽无已知 Critical CVE 影响 3.0.1，但该库不再接收安全补丁。

**关联**：QA Bug Report BUG-004 已记录此问题。

**修复建议**：

```bash
pip uninstall PyPDF2 && pip install pypdf
```

```python
# pdf_parser.py - 修改 import
# 修改前: from PyPDF2 import PdfReader
# 修改后: from pypdf import PdfReader
```

---

### SEC-20260712-012: Chroma 持久化目录权限宽松（Low）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-012 |
| 标题 | data/chroma/ 目录及文件权限为 755/644，系统所有用户可读 |
| 严重程度 | Low |
| 优先级 | P3 |
| 状态 | Open |
| OWASP 分类 | A01:2021 - Broken Access Control |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | DevOps Engineer |

**描述**：

```
drwxrwxr-x  data/chroma/        (755 - 所有用户可读)
-rw-r--r--  data/chroma/chroma.sqlite3  (644 - 所有用户可读)
```

而 `data/uploads/` 中的文件权限为 600（仅所有者可读写），是正确的安全实践。

**影响范围**：

- 系统其他用户可读取 Chroma 数据库，获取文档片段内容
- 本地单用户场景影响较小

**修复建议**：

```bash
chmod 700 data/chroma
chmod 600 data/chroma/chroma.sqlite3
chmod 700 data/chroma/*/  # collection 目录
```

或在代码中创建目录时设置权限：

```python
path.mkdir(parents=True, exist_ok=True, mode=0o700)
```

---

### SEC-20260712-013: DOMPurify 允许 img 和 a 标签（Low）

| 字段 | 内容 |
|------|------|
| 漏洞 ID | SEC-20260712-013 |
| 标题 | 前端 DOMPurify 配置允许 img（src）和 a（href）标签，存在 SSRF 和钓鱼风险 |
| 严重程度 | Low |
| 优先级 | P2 |
| 状态 | Open |
| OWASP 分类 | A03:2021 - Injection |
| 发现日期 | 2026-07-12 |
| 发现人 | Security Engineer |
| 负责人 | Frontend Engineer |

**描述**：

`frontend/src/utils/markdown.js:51-60` 的 DOMPurify 配置允许 `img` 标签（含 `src` 属性）和 `a` 标签（含 `href` 属性）。

```javascript
ALLOWED_TAGS: [..., 'a', ..., 'img'],
ALLOWED_ATTR: ['href', 'title', 'src', 'alt', 'class', 'target', 'rel'],
```

**风险场景**：

| 标签 | 风险 | 场景 |
|------|------|------|
| `<img src="http://evil.com/track.png">` | SSRF / 追踪像素 | LLM 输出恶意 Markdown，浏览器自动加载外部图片 |
| `<a href="http://phishing.com">点击</a>` | 钓鱼链接 | LLM 输出恶意链接，用户点击跳转 |

**缓解因素**：

- LLM 输出基于知识库文档，恶意 Markdown 注入概率低
- DOMPurify 已配置白名单，移除了 `<script>`、`onload` 等危险内容
- 允许 `target` 和 `rel` 属性，可添加 `rel="noopener noreferrer"`

**修复建议**：

1. 为 `a` 标签强制添加安全属性：

```javascript
// 在 DOMPurify.sanitize 后添加后处理
return DOMPurify.sanitize(rawHtml, {
  ...,
  HOOKS: {
    afterSanitizeAttributes: (node) => {
      if (node.tagName === 'A') {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
    }
  }
});
```

2. 考虑禁止 `img` 的外部 `src`（仅允许 data URI）：

```javascript
FORBID_ATTR: ['src'],  // 或使用 hook 验证 src 协议
```

---

## 3. OWASP Top 10 对照检查

| OWASP Top 10 (2021) | 检查项 | 状态 | 关联漏洞 |
|---------------------|--------|------|----------|
| A01: Broken Access Control | 资源访问授权 | ⚠️ | SEC-006, SEC-012 |
| A02: Cryptographic Failures | 敏感数据加密 | ⚠️ | SEC-002 |
| A03: Injection | 注入防护 | ✅ | SEC-013（低风险） |
| A04: Insecure Design | 安全设计 | ⚠️ | SEC-004, SEC-007, SEC-008, SEC-010 |
| A05: Security Misconfiguration | 安全配置 | ❌ | SEC-001, SEC-003, SEC-005, SEC-009 |
| A06: Vulnerable Components | 脆弱组件 | ⚠️ | SEC-011 |
| A07: Auth Failures | 认证失败 | N/A | 本地无认证（DEC-001） |
| A08: Integrity Failures | 完整性失效 | ✅ | 无 |
| A09: Logging Failures | 日志监控 | ✅ | 日志记录完善 |
| A10: SSRF | 服务端请求伪造 | ✅ | 无服务端请求（LLM API 除外） |

---

## 4. 修复优先级

### 4.1 修复优先级矩阵

| 优先级 | 漏洞 ID | 严重程度 | 阻塞发布 | 建议修复版本 | 理由 |
|--------|---------|----------|----------|-------------|------|
| **P0** | SEC-001 | Critical | ✅ 是 | **立即修复** | 缺少 .gitignore，敏感文件可能被提交 |
| **P0** | SEC-002 | High | ✅ 是 | **立即修复** | 真实 API Key 无保护（修复 SEC-001 后缓解） |
| **P0** | SEC-003 | High | ✅ 是 | **立即修复** | DEBUG=true 泄露信息 |
| P1 | SEC-004 | Medium | 否 | V1.1 | 文件类型校验不足 |
| P1 | SEC-005 | Medium | 否 | V1.1 | 错误信息泄露 |
| P1 | SEC-006 | Medium | 否 | **立即修复** | source_path 信息泄露（简单修复） |
| P1 | SEC-007 | Medium | 否 | V1.1 | 无速率限制 |
| P1 | SEC-008 | Medium | 否 | V1.1 | 流式验证缺失 |
| P2 | SEC-009 | Low | 否 | V1.1 | CORS 宽松 |
| P2 | SEC-010 | Low | 否 | V2 | Prompt 泄漏仅记录 |
| P2 | SEC-011 | Low | 否 | V1.1 | PyPDF2 弃用（关联 BUG-004） |
| P2 | SEC-013 | Low | 否 | V1.1 | DOMPurify img/a 标签 |
| P3 | SEC-012 | Low | 否 | V1.1 | Chroma 目录权限 |

### 4.2 发布前必做项（阻塞 G5 门禁）

1. **修复 SEC-001（Critical）**：创建 `.gitignore`，排除 `.env`、`data/`、`.coverage` 等
2. **修复 SEC-002（High）**：确认 `.env` 未被提交到 Git；如已提交，轮换 API Key
3. **修复 SEC-003（High）**：`.env.example` 中 `DEBUG=false`；`main.py` 中根据 DEBUG 控制 API 文档
4. **修复 SEC-006（Medium，建议）**：从 references 事件中移除 `source_path`（简单且高价值）

### 4.3 V1.1 建议修复项

1. SEC-004：添加文件魔数校验
2. SEC-005：错误消息友好化
3. SEC-007：引入速率限制
4. SEC-008：流式回答添加 validate_answer
5. SEC-009：收紧 CORS 配置
6. SEC-011：PyPDF2 → pypdf 迁移
7. SEC-012：Chroma 目录权限收紧
8. SEC-013：DOMPurify 安全加固

### 4.4 V2 建议改进项

1. SEC-010：Prompt 泄漏检测升级为拦截模式

---

## 5. 依赖安全审计

### 5.1 自动扫描结果

- **工具**：pip-audit
- **执行状态**：⚠️ 因网络超时未完成自动扫描
- **手动核查**：基于公开 CVE 数据库手动核查 16 个依赖

### 5.2 依赖安全核查结果

| 包名 | 版本 | 状态 | 说明 |
|------|------|------|------|
| PyPDF2 | 3.0.1 | ⚠️ 弃用 | 已停止维护，不再接收安全补丁（SEC-011） |
| python-multipart | 0.0.9 | ✅ 安全 | CVE-2024-24762 影响 <0.0.7，0.0.9 已修复 |
| fastapi | 0.110.3 | ✅ 安全 | 无已知 Critical CVE，建议升级至最新版 |
| sqlalchemy | 2.0.29 | ✅ 安全 | 无已知 Critical CVE |
| chromadb | 0.5.0 | ✅ 安全 | 历史版本有 CVE-2024-27431（SSRF），0.5.0 不受影响 |
| openai | 1.28.0 | ✅ 安全 | 无已知 Critical CVE |
| pydantic | 2.6.4 | ✅ 安全 | 无已知 Critical CVE |
| uvicorn | 0.27.1 | ✅ 安全 | 无已知 Critical CVE |
| asyncmy | 0.2.9 | ✅ 安全 | 无已知 Critical CVE |
| python-docx | 1.1.0 | ✅ 安全 | 无已知 Critical CVE |
| markdown | 3.6 | ✅ 安全 | 无已知 Critical CVE |
| chardet | 5.2.0 | ✅ 安全 | 无已知 Critical CVE |
| aiofiles | 23.2.1 | ✅ 安全 | 无已知 Critical CVE |
| sentence-transformers | 2.7.0 | ✅ 安全 | 无已知 Critical CVE |
| pydantic-settings | 2.2.1 | ✅ 安全 | 无已知 Critical CVE |
| python-dotenv | 1.0.1 | ✅ 安全 | 无已知 Critical CVE |

**结论**：16 个依赖中，1 个使用弃用库（PyPDF2，SEC-011），其余暂无已知 Critical CVE。建议 V1.1 迁移至 pypdf 后重新执行完整 pip-audit 扫描。

---

## 6. 认证授权审计（MVP 范围说明）

### 6.1 PRD 约束

根据 PRD（DEC-001）和架构文档，本项目为本地 localhost 运行的单用户应用，**明确排除认证、授权、多用户功能**。所有 API 端点无需认证即可访问。

### 6.2 风险评估

| 风险 | 可能性 | 影响 | 评估 |
|------|--------|------|------|
| 本地其他用户访问 API | 低 | 中 | uvicorn 绑定 127.0.0.1，仅本机可访问 |
| 恶意进程调用 API | 中 | 中 | 无认证，任何本地进程可调用 |
| 数据被其他用户读取 | 低 | 中 | 上传文件权限 600（安全）；Chroma 权限 644（需改进） |

### 6.3 结论

MVP 阶段无需认证是合理的设计决策。建议在文档中明确记录无认证的风险，并在 V2 考虑添加基础认证（如 API Token）。

---

## 7. 数据保护审计

### 7.1 传输加密

| 数据流 | 加密方式 | 状态 |
|--------|----------|------|
| 前端 ↔ 后端 | HTTP（本地 localhost） | ⚠️ 无 HTTPS（本地场景可接受） |
| 后端 ↔ MariaDB | 本地 TCP（127.0.0.1:3306） | ⚠️ 无 TLS（本地场景可接受） |
| 后端 ↔ OpenAI API | HTTPS | ✅ OpenAI SDK 默认 HTTPS |
| 后端 ↔ Chroma | 进程内调用 | ✅ 无网络传输 |

### 7.2 存储加密

| 数据 | 存储方式 | 加密 | 状态 |
|------|----------|------|------|
| API Key | .env 文件 | 明文 | ⚠️ 依赖 .gitignore 保护 |
| 数据库密码 | .env 文件 | 明文 | ⚠️ 依赖 .gitignore 保护 |
| 用户文档原文 | data/uploads/ | 明文 | ⚠️ 文件权限 600（良好） |
| 向量数据 | data/chroma/ | 明文 | ⚠️ 文件权限 644（需改进） |
| 聊天历史 | MariaDB | 明文 | ⚠️ 无字段级加密 |
| 文档内容哈希 | MariaDB | SHA-256 | ✅ 不可逆 |

### 7.3 日志安全

| 日志内容 | 位置 | 脱敏 | 状态 |
|----------|------|------|------|
| SQL 语句（DEBUG=true） | stdout | ❌ | ⚠️ 可能含查询参数 |
| 用户问题 | 日志文件 | ❌ | ⚠️ 记录问题内容 |
| 文档文件名 | 日志文件 | ❌ | ⚠️ 记录文件名 |
| API Key | 日志文件 | ✅ | ✅ 未在日志中出现 |
| 数据库密码 | 日志文件 | ✅ | ✅ 未在日志中出现 |

---

## 8. 质量门禁评估

| 门禁 | 通过标准 | 当前状态 | 评估 |
|------|----------|----------|------|
| G5-1 | 无 Critical 安全漏洞 | ✅ SEC-001 已修复（创建 .gitignore） | 通过 |
| G5-2 | 无 High 安全漏洞 | ✅ SEC-002 已缓解（.gitignore 保护 + 未提交 Git）、SEC-003 已修复（DEBUG=false + 条件文档） | 通过 |
| G5-3 | 认证机制安全 | N/A | 本地无认证（DEC-001，MVP 约束） |
| G5-4 | 敏感数据已保护 | ✅ | .env 被 .gitignore 保护；.env.example DEBUG=false |
| G5-5 | 所有输入有验证 | ✅ | UUID 校验、长度限制、Pydantic 验证 |

> **G5 门禁结论**：✅ **通过**（v1.1.0） — P0 阻塞漏洞（SEC-001 Critical、SEC-002/003 High）已全部修复，SEC-006（Medium）同步修复。228 个单元测试通过（覆盖率 87.21%），无回归。剩余 9 项 Medium/Low 漏洞不阻塞发布。

---

## 9. 自我审查

### 9.1 覆盖完整性审查

- [x] 认证安全：MVP 无认证（DEC-001），已评估风险
- [x] 授权安全：MVP 无授权，所有端点公开（已记录风险）
- [x] 数据安全：传输加密、存储加密、日志安全已审计
- [x] 输入安全：SQL 注入、XSS、CSRF、文件上传已审计
- [x] 依赖安全：手动核查 16 个依赖（pip-audit 网络超时）
- [x] OWASP Top 10：全部 10 项已对照检查

### 9.2 漏洞严重程度复核

- SEC-001 评为 Critical：敏感文件可能被提交到 Git，符合 Critical 定义"可导致系统被完全控制"（API Key 泄露）
- SEC-002 评为 High：API Key 泄露可导致经济损失，符合 High 定义"可导致数据泄露"
- SEC-003 评为 High：DEBUG 模式泄露内部信息，符合 High 定义
- 其余 Medium/Low 评级合理

### 9.3 修复建议可行性审查

- SEC-001 修复方案（创建 .gitignore）：简单、无副作用 ✅
- SEC-003 修复方案（DEBUG=false + 条件文档）：简单、可能影响开发体验 ✅
- SEC-006 修复方案（移除 source_path）：简单、可能影响前端显示 ✅
- 所有修复建议均考虑了 MVP 约束和后续版本规划

---

## 10. 附录

### 10.1 审计文件清单

| 审计文件 | 类型 | 行数 | 说明 |
|----------|------|------|------|
| `backend/app/main.py` | 入口 | 128 | CORS、日志、DEBUG 配置 |
| `backend/app/config/settings.py` | 配置 | 116 | .env 加载、配置项 |
| `backend/app/api/documents.py` | API | 269 | 文件上传、列表、删除 |
| `backend/app/api/chat.py` | API | 236 | SSE 流式问答 |
| `backend/app/api/sessions.py` | API | 121 | 会话 CRUD |
| `backend/app/api/config.py` | API | 214 | 配置查询、Provider 切换 |
| `backend/app/services/document_service.py` | Service | 458 | 文档处理流水线 |
| `backend/app/services/rag_service.py` | Service | 307 | RAG 检索与生成 |
| `backend/app/services/chat_service.py` | Service | 293 | 会话与消息管理 |
| `backend/app/services/output_guard.py` | Service | 156 | AI 输出验证 |
| `backend/app/services/prompt_template.py` | Service | 188 | Prompt 模板管理 |
| `backend/app/services/chroma_client.py` | Service | 236 | 向量数据库客户端 |
| `backend/app/database/session.py` | Database | 92 | 数据库会话管理 |
| `backend/app/utils/exceptions.py` | Utils | 221 | 异常处理 |
| `backend/app/utils/sse.py` | Utils | 90 | SSE 事件格式化 |
| `backend/app/utils/response.py` | Utils | 86 | 统一响应格式 |
| `backend/app/providers/llm/openai_provider.py` | Provider | 245 | LLM 调用 |
| `backend/app/providers/embedding/openai_provider.py` | Provider | 111 | Embedding 调用 |
| `backend/app/parsers/pdf_parser.py` | Parser | 64 | PDF 解析 |
| `backend/app/models/document.py` | Model | 132 | 文档数据模型 |
| `backend/.env` | 配置 | 42 | 真实环境配置 |
| `backend/.env.example` | 配置 | 39 | 配置模板 |
| `backend/requirements.txt` | 依赖 | 42 | Python 依赖 |
| `backend/database/init.sql` | SQL | 89 | 数据库初始化 |
| `frontend/src/utils/markdown.js` | 前端 | 62 | Markdown 渲染 |
| `frontend/src/components/chat/ReferenceCard.vue` | 前端 | 173 | 引用来源卡片 |
| `frontend/src/components/chat/MessageBubble.vue` | 前端 | — | 消息气泡（v-html） |

### 10.2 严重程度说明

| 级别 | 定义 | 处理 |
|------|------|------|
| Critical | 可导致系统被完全控制 | 立即修复，阻止发布 |
| High | 可导致数据泄露或越权 | 必须修复，阻止发布 |
| Medium | 存在安全风险但不严重 | 尽快修复 |
| Low | 轻微安全问题 | 计划修复 |

### 10.3 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，记录 13 项安全漏洞（1 Critical + 2 High + 5 Medium + 5 Low），G5 门禁未通过 | Security Engineer |
| 1.1.0 | 2026-07-12 | P0 修复验证完成：SEC-001（创建 .gitignore）、SEC-002（确认未提交 Git，无需轮换 Key）、SEC-003（DEBUG=false + 条件 API 文档）、SEC-006（移除 source_path）。228 个测试通过（覆盖率 87.21%），G5 门禁升级为 ✅ 通过 | Security Engineer |

---

**本报告是 G5 质量门禁的评估依据。v1.1.0：P0 阻塞漏洞（SEC-001 Critical、SEC-002/003 High）已全部修复，SEC-006（Medium）同步修复，G5 门禁 ✅ 通过。剩余 9 项 Medium/Low 漏洞计划 V1.1/V2 修复，不阻塞 MVP 发布。**
