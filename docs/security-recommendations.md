<!--
Document: Security Recommendations
Version: 1.0.0
Author: Security Engineer
Created: 2026-07-12
Updated: 2026-07-12
Status: Completed
-->

# 安全加固建议: AI 文档知识库（MVP）

## 文档元信息

| 字段   | 内容                                                                            |
| ---- | ----------------------------------------------------------------------------- |
| 文档名称 | 安全加固建议                                                                        |
| 项目名称 | AI 文档知识库（MVP）                                                                 |
| 版本   | 1.0.0                                                                         |
| 作者   | Security Engineer                                                             |
| 创建日期 | 2026-07-12                                                                    |
| 最后更新 | 2026-07-12                                                                    |
| 状态   | Completed                                                                     |
| 关联文档 | `docs/security-audit-report.md`、`docs/architecture.md`、`docs/decision-log.md` |

***

## 1. 概述

### 1.1 文档目的

本文档为 AI 文档知识库（MVP）提供分阶段、可执行的安全加固建议，作为 [`docs/security-audit-report.md`](file:///home/zoe/Public/project/RAG项目/docs/security-audit-report.md) 的配套实施指南。每项建议包含修复方案、代码示例、验证方法和影响评估，供 Backend Engineer、Frontend Engineer、DevOps Engineer 直接落地实施。

### 1.2 加固原则

| 原则           | 说明                                          |
| ------------ | ------------------------------------------- |
| **安全默认**     | 所有配置采用最小权限与安全默认值（如 `DEBUG=false`）           |
| **纵深防御**     | 多层防护，不依赖单一安全控制                              |
| **最小知识**     | 客户端仅获取必要信息，不暴露内部路径与错误细节                     |
| **MVP 约束优先** | 加固方案不破坏 DEC-001（本地单用户）和 DEC-005（无 Docker）约束 |
| **渐进式加固**    | P0 阻塞项立即修复，P1/V1.1 计划修复，P2/V2 长期改进          |

### 1.3 修复路线图

```
P0（立即修复，阻塞 G5 门禁）
  ├─ SEC-001: 创建 .gitignore
  ├─ SEC-002: 确认 .env 未提交 Git + 轮换 API Key
  ├─ SEC-003: DEBUG=false 安全默认
  └─ SEC-006: 移除 source_path 信息泄露（建议同步修复）
        ↓
V1.1（计划修复，不阻塞 MVP 发布）
  ├─ SEC-004: 文件魔数校验
  ├─ SEC-005: 错误信息友好化
  ├─ SEC-007: 速率限制
  ├─ SEC-008: 流式回答 output_guard 验证
  ├─ SEC-009: CORS 收紧
  ├─ SEC-011: PyPDF2 → pypdf 迁移
  ├─ SEC-012: Chroma 目录权限
  └─ SEC-013: DOMPurify 安全加固
        ↓
V2（长期改进）
  └─ SEC-010: Prompt 泄漏拦截模式
```

***

## 2. P0 立即修复项（阻塞 G5 门禁）

### 2.1 SEC-001: 创建 .gitignore 文件

**漏洞严重程度**：Critical
**负责角色**：DevOps Engineer / Backend Engineer
**预估工时**：15 分钟
**风险等级**：低（纯新增文件，无副作用）

#### 修复方案

在项目根目录 `/home/zoe/Public/project/RAG项目/` 创建 `.gitignore` 文件：

```gitignore
# ===== 环境变量（含敏感信息）=====
.env
.env.local
.env.*.local
# 保留 .env.example 作为模板
!/.env.example

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
.mypy_cache/
.ruff_cache/

# ===== 数据目录（含用户上传文档和向量数据）=====
backend/data/
data/

# ===== 虚拟环境 =====
.venv/
venv/
env/

# ===== IDE =====
.vscode/
.idea/
*.swp
*.swo
*~

# ===== 系统文件 =====
.DS_Store
Thumbs.db

# ===== 日志 =====
*.log
logs/

# ===== 前端构建产物（如需独立部署）=====
frontend/dist/
frontend/node_modules/
```

#### 验证步骤

```bash
# 1. 确认 .gitignore 已创建
ls -la /home/zoe/Public/project/RAG项目/.gitignore

# 2. 验证 .env 不再被 Git 跟踪
cd /home/zoe/Public/project/RAG项目
git status backend/.env
# 预期输出: nothing to commit, working tree clean（或 untracked）

# 3. 验证 .env.example 仍可提交
git status backend/.env.example
# 预期: 不在 .gitignore 排除范围

# 4. 检查 Git 历史是否已提交敏感文件
git log --all -- backend/.env
# 如果有输出，需执行 2.2 节的轮换流程
```

#### 影响评估

* **功能影响**：无（不影响任何运行时功能）

* **开发体验**：无（开发者仍可本地使用 .env）

* **CI/CD 影响**：无（部署时通过其他方式注入环境变量）

***

### 2.2 SEC-002: 确认 .env 未提交 Git + 轮换 API Key

**漏洞严重程度**：High
**负责角色**：Backend Engineer + Human Developer
**预估工时**：30 分钟（轮换 Key 需人工操作）
**风险等级**：中（涉及 API Key 轮换，需协调）

#### 修复方案

**步骤 1：检查 Git 历史**

```bash
cd /home/zoe/Public/project/RAG项目

# 检查 .env 是否曾被提交
git log --all -- backend/.env

# 检查 API Key 是否出现在任何已提交文件中
git log -p --all -S "sk-xxxxxxxxxxxxxxxxxxxxxxxx" --source
```

**步骤 2：根据检查结果分支处理**

| 检查结果          | 处理方式                                     |
| ------------- | ---------------------------------------- |
| .env 从未提交     | ✅ 仅需确保 SEC-001 的 .gitignore 生效即可         |
| .env 已提交但仅本地  | 执行 `git rm --cached backend/.env`，从跟踪中移除 |
| .env 已推送到远程仓库 | ⚠️ **必须轮换 API Key**（见步骤 3）               |

**步骤 3：轮换 API Key（如需）**

1. 登录 OpenAI 控制台（或第三方代理 apilio.ai 控制台）
2. 撤销当前 API Key：`sk-xxx...xxx`
3. 生成新 API Key
4. 更新 `backend/.env` 中的 `OPENAI_API_KEY`
5. 清除 Git 历史中的敏感信息（使用 BFG Repo-Cleaner）：

```bash
# 下载 BFG Repo-Cleaner
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 镜像仓库（裸克隆）
git clone --mirror /home/zoe/Public/project/RAG项目 /tmp/RAG项目.git

# 使用 BFG 删除 .env 文件
java -jar bfg-1.14.0.jar --delete-folders .env /tmp/RAG项目.git

# 清理 Git 垃圾
cd /tmp/RAG项目.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 推回原仓库
git push
```

**步骤 4：修改数据库密码（如已泄露）**

```bash
# 登录 MariaDB
mysql -u root -p

# 修改 RAG 用户密码
ALTER USER 'RAG'@'localhost' IDENTIFIED BY '新强密码';
FLUSH PRIVILEGES;
```

更新 `backend/.env` 中的 `DATABASE_URL`。

#### 验证步骤

```bash
# 1. 确认旧 Key 已失效（预期返回 401）
curl -H "Authorization: Bearer sk-xxxxxxxxxxxxxxxxxxxxxxxx" \
     https://api.apilio.ai/v1/models

# 2. 确认新 Key 可用
curl -H "Authorization: Bearer 新Key" https://api.apilio.ai/v1/models

# 3. 确认 Git 历史中无 API Key
git log -p --all | grep "sk-" || echo "✅ API Key 已从历史中清除"
```

#### 影响评估

* **功能影响**：API Key 轮换后需重启后端服务

* **开发体验**：开发者需更新本地 .env

* **风险**：轮换过程中短暂的 API 不可用窗口

***

### 2.3 SEC-003: DEBUG=false 安全默认

**漏洞严重程度**：High
**负责角色**：Backend Engineer
**预估工时**：30 分钟
**风险等级**：低（配置调整 + 少量代码修改）

#### 修复方案

**步骤 1：修改** **`.env.example`**

```bash
# backend/.env.example
# 修改前: DEBUG=true
# 修改后:
DEBUG=false  # 生产环境必须为 false；本地开发可改为 true
```

**步骤 2：修改** **`backend/app/main.py`（条件暴露 API 文档）**

```python
# backend/app/main.py
# 找到 FastAPI 应用初始化代码（约第 75-85 行）

# 修改前:
app = FastAPI(
    title="AI 文档知识库 API",
    description="基于 RAG 的文档知识库问答系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 修改后:
app = FastAPI(
    title="AI 文档知识库 API",
    description="基于 RAG 的文档知识库问答系统",
    version="1.0.0",
    # 安全考虑：仅 DEBUG 模式下暴露 API 文档
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)
```

**步骤 3：修改** **`backend/app/main.py`（uvicorn 启动参数）**

```python
# backend/app/main.py（约第 125-130 行）

# 修改前:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,  # ← 无条件开启 reload
    )

# 修改后:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # ← 仅 DEBUG 模式下开启 reload
    )
```

**步骤 4：在** **`backend/app/database/session.py`** **添加安全注释**

```python
# backend/app/database/session.py（约第 25-30 行）

return create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # ⚠️ 安全注意：DEBUG=true 时输出所有 SQL（含查询参数），生产环境必须为 false
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)
```

#### 验证步骤

```bash
# 1. 启动后端（DEBUG=false）
cd /home/zoe/Public/project/RAG项目/backend
# 修改 .env: DEBUG=false
python -m app.main

# 2. 验证 /docs 不可访问（预期 404）
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs
# 预期: 404

# 3. 验证 /redoc 不可访问
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/redoc
# 预期: 404

# 4. 验证 API 功能正常
curl http://127.0.0.1:8000/api/config
# 预期: 正常返回配置信息

# 5. 切换 DEBUG=true，验证 /docs 可访问
# 修改 .env: DEBUG=true，重启后端
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs
# 预期: 200
```

#### 影响评估

* **功能影响**：DEBUG=false 时无法访问 Swagger UI（开发者需切换配置）

* **开发体验**：开发者本地开发时需手动设置 `DEBUG=true`

* **安全收益**：消除 SQL 日志泄露、API 结构暴露、reload 模式风险

***

### 2.4 SEC-006: 移除 source\_path 信息泄露（建议同步修复）

**漏洞严重程度**：Medium（建议与 P0 同步修复，简单且高价值）
**负责角色**：Backend Engineer + Frontend Engineer
**预估工时**：20 分钟
**风险等级**：低（移除非必要字段）

#### 修复方案

**步骤 1：修改** **`backend/app/services/rag_service.py`**

```python
# backend/app/services/rag_service.py（约第 57-66 行）

# 修改前:
def to_reference(self) -> dict:
    return {
        "doc_id": self.doc_id,
        "doc_name": self.doc_name,
        "chunk_index": self.chunk_index,
        "source_path": self.source_path,  # ← 内部路径泄露
        "preview": self.content[:200] + ("..." if len(self.content) > 200 else ""),
        "similarity": round(self.similarity, 4),
    }

# 修改后:
def to_reference(self) -> dict:
    return {
        "doc_id": self.doc_id,
        "doc_name": self.doc_name,
        "chunk_index": self.chunk_index,
        # 移除 source_path：不暴露内部文件存储路径
        "preview": self.content[:200] + ("..." if len(self.content) > 200 else ""),
        "similarity": round(self.similarity, 4),
    }
```

**步骤 2：修改** **`frontend/src/components/chat/ReferenceCard.vue`**

```vue
<!-- frontend/src/components/chat/ReferenceCard.vue（约第 50 行） -->

<!-- 修改前: -->
<span class="ref-path text-ellipsis">片段 #{{ item.chunk_index + 1 }} · {{ item.source_path }}</span>

<!-- 修改后: -->
<span class="ref-path text-ellipsis">片段 #{{ item.chunk_index + 1 }}</span>
```

#### 验证步骤

```bash
# 1. 重启后端，执行一次 RAG 问答
# 2. 检查 SSE references 事件中是否包含 source_path
# 预期: references 事件中无 source_path 字段

# 3. 检查前端引用来源卡片
# 预期: 仅显示 "片段 #N"，不显示文件路径
```

#### 影响评估

* **功能影响**：前端不再显示文件路径（用户体验轻微变化）

* **安全收益**：消除内部文件系统结构泄露

***

## 3. V1.1 计划修复项

### 3.1 SEC-004: 文件魔数校验

**负责角色**：Backend Engineer
**预估工时**：1 小时

#### 修复方案

在 `backend/app/api/documents.py` 中添加文件魔数校验：

```python
# backend/app/api/documents.py

# 文件签名（魔数）定义
FILE_SIGNATURES = {
    "pdf": b"%PDF-",                         # PDF 文件头
    "docx": b"PK\x03\x04",                   # DOCX（ZIP-based）
    # md 和 txt 无固定魔数，通过内容可读性判断
}


def _validate_file_magic(file_path: Path, file_type: str) -> bool:
    """校验文件魔数，防止伪造扩展名攻击。

    Args:
        file_path: 临时文件路径
        file_type: 文件类型（pdf/docx/md/txt）

    Returns:
        True 表示通过校验（或类型无魔数定义）
    """
    if file_type not in FILE_SIGNATURES:
        return True  # md/txt 无魔数定义，跳过

    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        return header.startswith(FILE_SIGNATURES[file_type])
    except (IOError, OSError):
        return False
```

在 `upload_and_process` 函数中调用：

```python
# 在保存临时文件后，调用 _validate_file_magic
if not _validate_file_magic(tmp_path, file_type):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"文件内容与扩展名不匹配（{file_type}）",
    )
```

#### 验证

* 构造 `malicious.pdf`（实际为 .exe 重命名），上传应返回 400

* 正常 PDF/DOCX 上传应成功

***

### 3.2 SEC-005: 错误信息友好化

**负责角色**：Backend Engineer
**预估工时**：1 小时

#### 修复方案

在 `backend/app/api/chat.py` 和 `backend/app/api/documents.py` 中引入错误码→友好消息映射：

```python
# backend/app/utils/error_messages.py（新增文件）

"""错误码与用户友好消息的映射。"""

FRIENDLY_ERROR_MESSAGES = {
    # LLM 相关
    "LLM_TIMEOUT": "回答生成超时，请重试",
    "LLM_AUTH_ERROR": "AI 服务认证失败，请检查配置",
    "LLM_CONNECTION_ERROR": "AI 服务连接失败，请稍后重试",
    "LLM_RATE_LIMIT": "AI 服务请求频率过高，请稍后重试",
    # Embedding 相关
    "EMBEDDING_ERROR": "文档向量化失败，请重试",
    "EMBEDDING_TIMEOUT": "文档向量化超时，请重试",
    # 检索相关
    "RETRIEVAL_ERROR": "文档检索失败，请重试",
    "NO_DOCUMENTS": "知识库为空，请先上传文档",
    # 通用
    "INTERNAL_ERROR": "服务器内部错误，请稍后重试",
    "DOCUMENT_NOT_FOUND": "文档不存在",
    "SESSION_NOT_FOUND": "会话不存在",
    "FILE_TOO_LARGE": "文件大小超过限制（20MB）",
    "UNSUPPORTED_FILE_TYPE": "不支持的文件类型",
    "PARSE_ERROR": "文档解析失败，请检查文件格式",
}


def get_friendly_message(error_code: str, default: str = "未知错误") -> str:
    """根据错误码获取用户友好消息。"""
    return FRIENDLY_ERROR_MESSAGES.get(error_code, default)
```

修改 `chat.py` 的错误处理：

```python
# backend/app/api/chat.py（约第 205-210 行）

# 修改前:
yield error_event(str(e)[:200], error_code)

# 修改后:
from app.utils.error_messages import get_friendly_message

friendly_msg = get_friendly_message(error_code)
yield error_event(friendly_msg, error_code)
# 原始异常仅记录到日志（不发送给客户端）
logger.error("SSE 流式错误 [%s]: %s", error_code, e, exc_info=True)
```

修改 `documents.py` 的错误处理（同理）。

***

### 3.3 SEC-007: API 速率限制

**负责角色**：Backend Engineer
**预估工时**：2 小时

#### 修复方案

引入 `slowapi` 轻量级速率限制库：

```bash
# 添加依赖
echo "slowapi==0.1.9" >> backend/requirements.txt
pip install slowapi==0.1.9
```

在 `backend/app/main.py` 中配置：

```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(...)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

在关键端点应用限制：

```python
# backend/app/api/chat.py
from app.main import limiter

@router.post("/messages")
@limiter.limit("10/minute")  # 每分钟最多 10 次问答
async def send_message(request: Request, ...):
    ...

# backend/app/api/documents.py
@router.post("/upload")
@limiter.limit("5/minute")  # 每分钟最多 5 次上传
async def upload_document(request: Request, ...):
    ...
```

#### 注意事项

* `slowapi` 需要请求中包含 `request: Request` 参数

* 本地单用户场景下，速率限制主要防止误操作或脚本滥用

* 限制值可根据实际使用调整

***

### 3.4 SEC-008: 流式回答 output\_guard 验证

**负责角色**：Backend Engineer / AI Engineer
**预估工时**：1 小时

#### 修复方案

在 `backend/app/api/chat.py` 的 `stream()` 函数中，流结束后对完整内容执行验证：

```python
# backend/app/api/chat.py（stream 函数末尾，发送 done 事件前）

from app.services.output_guard import validate_answer

# ... 流式拼接 assistant_content ...

# 流结束后验证完整内容
validation = validate_answer(assistant_content)

# 处理截断
if validation.is_truncated:
    yield token_event("\n\n（回答已达长度上限，已截断。）")
    assistant_content = validation.content

# 处理 Prompt 泄漏（记录日志）
if validation.prompt_leak_detected:
    logger.warning("流式回答检测到 Prompt 泄漏（已记录，未拦截）")

# 处理空内容
if validation.is_empty:
    assistant_content = "抱歉，我无法生成有效回答，请尝试重新提问。"
    yield token_event(assistant_content)

# 发送 done 事件
yield done_event(...)
```

#### 验证

* 单元测试：Mock LLM 返回含控制字符的内容，验证流式输出已清洗

* 单元测试：Mock LLM 返回超长内容，验证截断提示

***

### 3.5 SEC-009: CORS 收紧

**负责角色**：Backend Engineer
**预估工时**：15 分钟

#### 修复方案

```python
# backend/app/main.py（约第 85-95 行）

# 修改前:
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

# 修改后:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 仅允许必要的 HTTP 方法
    allow_headers=["Content-Type", "Accept"],         # 仅允许必要的头
)
```

#### 验证

```bash
# 验证 OPTIONS 预检请求返回正确的允许方法
curl -X OPTIONS -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     http://127.0.0.1:8000/api/chat/messages -I
# 预期: access-control-allow-methods: GET, POST, PUT, DELETE
```

***

### 3.6 SEC-011: PyPDF2 → pypdf 迁移

**负责角色**：Backend Engineer
**预估工时**：30 分钟
**关联**：BUG-004

#### 修复方案

```bash
# 1. 卸载旧库
pip uninstall PyPDF2

# 2. 安装新库
pip install pypdf

# 3. 更新 requirements.txt
# 修改: PyPDF2==3.0.1 → pypdf>=4.0.0
```

修改 `backend/app/parsers/pdf_parser.py`：

```python
# 修改前:
from PyPDF2 import PdfReader

# 修改后:
from pypdf import PdfReader
```

#### 验证

```bash
# 运行 PDF 解析相关测试
cd backend
python -m pytest tests/test_parsers.py -v

# 上传一个 PDF 文档验证解析正常
```

#### 注意事项

* `pypdf` API 与 `PyPDF2 3.0.x` 基本兼容，迁移成本极低

* 迁移后重新执行 `pip-audit` 完整扫描

***

### 3.7 SEC-012: Chroma 目录权限收紧

**负责角色**：DevOps Engineer
**预估工时**：15 分钟

#### 修复方案

```bash
# 收紧 Chroma 持久化目录权限
cd /home/zoe/Public/project/RAG项目/backend/data

chmod 700 chroma
chmod 600 chroma/chroma.sqlite3
find chroma -type d -exec chmod 700 {} \;
find chroma -type f -exec chmod 600 {} \;
```

或在代码中创建目录时设置权限（`backend/app/services/chroma_client.py`）：

```python
# backend/app/services/chroma_client.py
from pathlib import Path

# 创建 Chroma 持久化目录时设置权限
chroma_path = Path(settings.CHROMA_PERSIST_DIR)
chroma_path.mkdir(parents=True, exist_ok=True, mode=0o700)
```

#### 验证

```bash
ls -la /home/zoe/Public/project/RAG项目/backend/data/chroma/
# 预期: drwx------ (700)

ls -la /home/zoe/Public/project/RAG项目/backend/data/chroma/chroma.sqlite3
# 预期: -rw------- (600)
```

***

### 3.8 SEC-013: DOMPurify 安全加固

**负责角色**：Frontend Engineer
**预估工时**：1 小时

#### 修复方案

修改 `frontend/src/utils/markdown.js`，添加 DOMPurify 钩子：

```javascript
// frontend/src/utils/markdown.js

import DOMPurify from 'dompurify';

// 配置 DOMPurify 钩子：为 <a> 标签强制添加安全属性
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  // 为所有 <a> 标签强制添加 target="_blank" 和 rel="noopener noreferrer"
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }

  // 为所有 <img> 标签的 src 验证协议（仅允许 https/data）
  if (node.tagName === 'IMG') {
    const src = node.getAttribute('src') || '';
    if (!src.startsWith('https://') && !src.startsWith('data:')) {
      node.removeAttribute('src');  // 移除不安全的图片源
    }
  }
});

export function renderMarkdown(rawMarkdown) {
  const rawHtml = marked.parse(rawMarkdown);
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'code', 'pre', 'blockquote',
      'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr', 'del', 'span',
    ],
    ALLOWED_ATTR: ['href', 'title', 'src', 'alt', 'class', 'target', 'rel'],
  });
}
```

#### 验证

```javascript
// 测试用例
renderMarkdown('[点击](http://phishing.com)')
// 预期: <a href="http://phishing.com" target="_blank" rel="noopener noreferrer">点击</a>

renderMarkdown('![img](http://evil.com/track.png)')
// 预期: <img> 标签的 src 被移除（http 不允许）

renderMarkdown('![img](https://safe.com/img.png)')
// 预期: <img src="https://safe.com/img.png"> 保留
```

***

## 4. V2 长期改进项

### 4.1 SEC-010: Prompt 泄漏拦截模式

**负责角色**：AI Engineer
**预估工时**：2 小时

#### 当前状态

`output_guard.py:124-132` 检测到 Prompt 泄漏时仅记录日志，不拦截。

#### V2 改进方案

```python
# backend/app/services/output_guard.py

# 修改 prompt_leak_detected 处理逻辑
if prompt_leak_detected:
    logger.warning("检测到 LLM 输出包含 Prompt 泄漏，已拦截并替换")

    # V2: 拦截模式 - 替换为通用提示
    content = "抱歉，我无法回答这个问题。请基于知识库内容重新提问。"
    prompt_leak_intercepted = True  # 新增标志位

return ValidationResult(
    content=content,
    is_empty=is_empty,
    is_truncated=is_truncated,
    prompt_leak_detected=prompt_leak_detected,
    prompt_leak_intercepted=prompt_leak_intercepted,  # 新字段
)
```

#### 注意事项

* 拦截模式可能导致误伤（如用户合法询问"什么是 System Prompt"）

* 建议配合更精确的检测规则（上下文感知）

* 需要充分测试，确保不影响正常问答

***

## 5. 安全加固验证清单

### 5.1 P0 修复验证（G5 门禁复评）

| 验证项                           | 验证方法                                                             | 预期结果              | 状态 |
| ----------------------------- | ---------------------------------------------------------------- | ----------------- | -- |
| .gitignore 存在                 | `ls -la .gitignore`                                              | 文件存在              | ⬜  |
| .env 不被 Git 跟踪                | `git status backend/.env`                                        | untracked 或 clean | ⬜  |
| Git 历史无 API Key               | `git log -p --all \| grep "sk-"`                                | 无匹配               | ⬜  |
| API Key 已轮换（如泄露）              | 旧 Key 调用 OpenAI API                                              | 401 Unauthorized  | ⬜  |
| DEBUG=false 默认                | `grep DEBUG .env.example`                                        | `DEBUG=false`     | ⬜  |
| /docs 在 DEBUG=false 时不可访问     | `curl -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs` | 404               | ⬜  |
| source\_path 不在 references 事件 | 执行 RAG 问答，检查 SSE 事件                                              | 无 source\_path 字段 | ⬜  |

### 5.2 V1.1 修复验证

| 验证项          | 验证方法                 | 预期结果                    | 状态 |
| ------------ | -------------------- | ----------------------- | -- |
| 文件魔数校验       | 上传伪造扩展名文件            | 返回 400                  | ⬜  |
| 错误信息友好化      | 触发 LLM 超时            | 返回友好消息，无堆栈              | ⬜  |
| 速率限制生效       | 1 分钟内调用 11 次问答       | 第 11 次返回 429            | ⬜  |
| 流式验证         | Mock 超长内容            | 返回截断提示                  | ⬜  |
| CORS 收紧      | OPTIONS 预检           | 仅允许 GET/POST/PUT/DELETE | ⬜  |
| pypdf 迁移     | 上传 PDF 解析            | 正常解析                    | ⬜  |
| Chroma 权限    | `ls -la data/chroma` | 700/600                 | ⬜  |
| DOMPurify 加固 | 渲染含链接的 Markdown      | a 标签含 rel="noopener"    | ⬜  |

***

## 6. 安全编码规范建议

### 6.1 后端安全编码规范

| 规范             | 说明                 | 示例                                         |
| -------------- | ------------------ | ------------------------------------------ |
| 禁止硬编码密钥        | 所有密钥通过 .env 注入     | `settings.OPENAI_API_KEY`                  |
| 使用 ORM 参数化查询   | 禁止 `text()` 拼接 SQL | `db.execute(select(Document).where(...))`  |
| 文件名使用 UUID     | 防止路径穿越             | `f"{doc_id}.{file_type}"`                  |
| 临时文件使用 mkstemp | 防止符号链接攻击           | `tempfile.mkstemp()`                       |
| 错误消息脱敏         | 对客户端返回友好消息         | `get_friendly_message(error_code)`         |
| 输入长度限制         | 防止缓冲区溢出            | `max_length=2000`                          |
| UUID 格式校验      | 防止 ID 注入           | `re.match(r"^[a-f0-9-]{36}$", session_id)` |
| 日志不记录敏感数据      | API Key、密码不写入日志    | `logger.info("API Key: ***")`              |

### 6.2 前端安全编码规范

| 规范                    | 说明             | 示例                              |
| --------------------- | -------------- | ------------------------------- |
| 禁止 v-html 渲染用户输入      | 仅渲染受信任的 LLM 输出 | `<div v-html="sanitizedHtml">`  |
| DOMPurify 净化所有 HTML   | 防止 XSS         | `DOMPurify.sanitize(rawHtml)`   |
| 文本插值用 `{{ }}`         | 自动转义 HTML      | `{{ userTitle }}`               |
| a 标签添加 rel="noopener" | 防止 tabnabbing  | `<a rel="noopener noreferrer">` |
| 不存储敏感信息到 localStorage | 防止 XSS 窃取      | API Key 仅在后端                    |

### 6.3 配置安全规范

| 规范                 | 说明                            |
| ------------------ | ----------------------------- |
| .env 不提交 Git       | 通过 .gitignore 排除              |
| .env.example 使用占位符 | `sk-xxxxxxxxxxxxxxxxxxxxxxxx` |
| 安全默认值              | `DEBUG=false`                 |
| 最小权限原则             | 数据库用户仅授权必要权限                  |
| 文件权限最小化            | 数据目录 700，文件 600               |

***

## 7. 安全监控建议

### 7.1 日志监控

| 监控项       | 日志特征                                | 告警阈值       |
| --------- | ----------------------------------- | ---------- |
| API 滥用    | 同一 IP 高频请求                          | > 100 次/分钟 |
| 文件上传异常    | 上传失败率突增                             | > 20%      |
| LLM 调用失败  | LLM\_TIMEOUT/LLM\_CONNECTION\_ERROR | > 10 次/小时  |
| Prompt 泄漏 | "检测到 Prompt 泄漏"                     | > 0 次      |
| 认证失败（V2）  | 401 Unauthorized                    | > 5 次/分钟   |

### 7.2 定期安全审查

| 频率      | 审查内容              | 负责人               |
| ------- | ----------------- | ----------------- |
| 每月      | 依赖漏洞扫描（pip-audit） | Backend Engineer  |
| 每季度     | 完整安全审计            | Security Engineer |
| 重大版本发布前 | 安全审计报告复评          | Security Engineer |
| 依赖升级时   | 针对性 CVE 核查        | Backend Engineer  |

***

## 8. 变更历史

| 版本    | 日期         | 变更说明                                  | 作者                |
| ----- | ---------- | ------------------------------------- | ----------------- |
| 1.0.0 | 2026-07-12 | 初始版本，包含 13 项漏洞的加固建议、修复路线图、安全编码规范、监控建议 | Security Engineer |

***

**本建议文档是安全审计报告的配套实施指南。P0 项必须修复后方可通过 G5 门禁；V1.1 项建议在 MVP 发布后两周内完成；V2 项作为长期改进计划。**
