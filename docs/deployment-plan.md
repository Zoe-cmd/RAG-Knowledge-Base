<!--
Document: Deployment Plan
Version: 1.0.0
Author: DevOps Engineer
Created: 2026-07-13
Updated: 2026-07-13
Status: Ready（待 Human Developer 在干净环境验证，G6 前置）
-->

# 部署方案：AI 文档知识库（MVP）

## 0. 文档导读

| 项 | 内容 |
|---|---|
| 部署版本 | v1.1.0（MVP） |
| 部署环境 | 本地原生部署（localhost，DEC-001 无认证） |
| 部署目标 | 开发者本地机器，作品集演示与个人学习 |
| 操作系统 | Linux / macOS / Windows（推荐 Linux/macOS） |
| 🔴 硬约束 C1 | **全项目禁用 Docker**，采用本地原生部署 |
| 🔴 硬约束 C2 | **MariaDB 本地安装**，不得容器化 |
| 🔴 硬约束 C3 | 所有敏感配置通过 `.env` 管理，不得硬编码 |
| 预计部署耗时 | 全新环境 30~60 分钟（含依赖下载） |
| 预计停机时间 | 不适用（首次部署） |
| 回滚时间 | < 5 分钟（停止服务 + 还原备份） |

> 本方案严格遵循 `shared/deployment-standard.md`，但因项目硬约束 C1 禁用 Docker，**不提供 Dockerfile / docker-compose.yml**，所有组件本地原生运行。

---

## 1. 部署架构

### 1.1 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                    开发者本地机器（localhost）                  │
│                                                             │
│   ┌─────────────────┐         ┌─────────────────────────┐   │
│   │  前端 Vite 服务  │  /api   │  后端 FastAPI 服务       │   │
│   │  (Vue3 + EPlus) │ ──────▶ │  (uvicorn ASGI)          │   │
│   │  127.0.0.1:5173 │  Proxy  │  127.0.0.1:8000          │   │
│   └─────────────────┘         └────────┬────────────────┘   │
│                                       │                     │
│                  ┌────────────────────┼──────────────┐      │
│                  │                    │              │      │
│                  ▼                    ▼              ▼      │
│         ┌────────────────┐  ┌──────────────────┐  ┌────────┐│
│         │  MariaDB       │  │  Chroma 向量库    │  │ OpenAI ││
│         │  127.0.0.1:3306│  │  ./data/chroma   │  │  API   ││
│         │  (本地安装)     │  │  (嵌入式持久化)   │  │ (外部) ││
│         └────────────────┘  └──────────────────┘  └────────┘│
│                                                             │
│   数据目录: ./backend/data/{uploads,chroma,models,logs}     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 端口分配

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| 前端 Vite | 5173 | HTTP | 开发服务器（`npm run dev`） |
| 前端 Preview | 4173 | HTTP | 生产预览（`npm run preview`，可选） |
| 后端 FastAPI | 8000 | HTTP | API 服务（uvicorn） |
| MariaDB | 3306 | TCP | 数据库（本地安装，默认端口） |

### 1.3 通信方式

| 通信路径 | 方式 | 说明 |
|----------|------|------|
| 浏览器 ↔ 前端 Vite | HTTP | 浏览器访问 `http://127.0.0.1:5173` |
| 前端 ↔ 后端 | Vite Proxy | `/api` 前缀由 Vite 转发到 `127.0.0.1:8000`（DEC-015） |
| 后端 ↔ MariaDB | TCP | `mysql+asyncmy://` 异步驱动 |
| 后端 ↔ Chroma | 进程内嵌入式 | Chroma 作为 Python 库嵌入，无独立进程 |
| 后端 ↔ OpenAI | HTTPS | 调用 OpenAI API（gpt-4o-mini / text-embedding-3-small） |

### 1.4 数据目录结构

```
backend/
├── data/                          # 运行时数据（已加入 .gitignore）
│   ├── uploads/                   # 用户上传的原始文档
│   ├── chroma/                    # Chroma 向量库持久化目录
│   ├── models/                    # 本地 Embedding 模型缓存（bge-m3，可选）
│   └── logs/                      # 应用日志（部署时由脚本创建）
├── database/
│   └── init.sql                   # 数据库初始化脚本
└── .env                           # 环境变量（部署者从 .env.example 复制并填写）
```

---

## 2. 环境准备

### 2.1 系统要求

| 组件 | 最低版本 | 推荐版本 | 验证命令 |
|------|----------|----------|----------|
| Python | 3.11 | 3.11.x | `python --version` |
| Node.js | 18.0 | 20.x LTS | `node --version` |
| npm | 9.0 | 10.x | `npm --version` |
| MariaDB | 10.5 | 10.11 LTS | `mariadb --version` |
| Git | 2.30 | 2.40+ | `git --version` |

### 2.2 Python 安装

> ⚠️ **重要**：项目在 **Python 3.11** 下开发与测试。**不要使用 Python 3.13+**（依赖如 asyncmy、chromadb、sentence-transformers 尚未提供 3.13+ 的预编译 wheel，会导致编译失败或运行时错误）。推荐使用 **conda** 创建独立的 3.11 环境。

#### 方式 A：conda 环境（推荐，最稳定）

```bash
# 使用 conda 创建独立的 Python 3.11 环境（名为 rag-kb）
conda create -n rag-kb python=3.11 -y

# 验证
conda run -n rag-kb python --version
# 应输出: Python 3.11.x

# 后续启动脚本会自动检测并激活 rag-kb 环境，无需手动激活
```

如未安装 conda，可从 https://docs.conda.io/en/latest/miniconda.html 安装 Miniconda。

#### 方式 B：系统 Python 3.11

##### Linux（Ubuntu/Debian）

```bash
# 安装 Python 3.11 + 开发工具（asyncmy 编译需要）
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev build-essential default-libmysqlclient-dev pkg-config

# 验证
python3.11 --version
```

##### macOS（Homebrew）

```bash
brew install python@3.11 mysql-client pkg-config
python3.11 --version
```

##### Windows

1. 访问 https://www.python.org/downloads/ 下载 Python 3.11.x 安装包
2. 安装时勾选 "Add Python to PATH"
3. 验证：`python --version`（应显示 3.11.x）

> **注意**：Windows 安装 `asyncmy` 需要 Visual C++ Build Tools。从 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 下载安装，勾选 "Desktop development with C++"。

#### 版本兼容性说明

| Python 版本 | 兼容性 | 说明 |
|-------------|--------|------|
| 3.11.x | ✅ 推荐 | 开发与测试版本，所有依赖有预编译 wheel |
| 3.12.x | ⚠️ 兼容 | 大多数依赖可用，未经完整测试 |
| 3.13+ | ❌ 不支持 | 依赖（asyncmy/chromadb/sentence-transformers）无预编译 wheel，会编译失败 |
| < 3.11 | ❌ 不支持 | 版本过低 |

### 2.3 Node.js 安装

#### Linux（Ubuntu/Debian，使用 NodeSource）

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version && npm --version
```

#### macOS

```bash
brew install node@20
node --version && npm --version
```

#### Windows

1. 访问 https://nodejs.org/ 下载 20.x LTS 安装包
2. 安装后验证：`node --version`

### 2.4 MariaDB 安装

#### Linux（Ubuntu/Debian）

```bash
sudo apt install -y mariadb-server mariadb-client

# 启动服务
sudo systemctl start mariadb
sudo systemctl enable mariadb

# 安全初始化（设置 root 密码、移除匿名用户等）
sudo mysql_secure_installation

# 验证
mariadb --version
sudo systemctl status mariadb
```

#### macOS

```bash
brew install mariadb
brew services start mariadb
mariadb --version
```

#### Windows

1. 访问 https://mariadb.org/download/ 下载 MariaDB 10.11 LTS MSI 安装包
2. 安装时记住 root 密码（部署时需要）
3. 安装完成后确认服务已启动（服务管理器中查看 "MariaDB"）
4. 验证：`mariadb --version`

> **约束提醒**：🔴 C2 — MariaDB 必须本地安装，**不得使用 Docker 容器化的 MariaDB**。

### 2.5 Git 安装（可选，用于克隆代码）

```bash
# Linux
sudo apt install -y git

# macOS
brew install git

# Windows: 从 https://git-scm.com/ 下载
```

---

## 3. 部署步骤

### 3.1 部署前检查清单

| # | 检查项 | 验证方法 | 状态 |
|---|--------|----------|------|
| 1 | Python 3.11+ 已安装 | `python --version` | ☐ |
| 2 | Node.js 18+ 已安装 | `node --version` | ☐ |
| 3 | MariaDB 10.5+ 已安装并运行 | `sudo systemctl status mariadb` | ☐ |
| 4 | MariaDB root 密码已知 | `mariadb -u root -p` 可登录 | ☐ |
| 5 | OpenAI API Key 已获取 | 可在 https://platform.openai.com/ 查看 | ☐ |
| 6 | 项目代码已下载到本地 | `ls /path/to/RAG项目` | ☐ |
| 7 | 端口 5173、8000、3306 未被占用 | `lsof -i :8000` 等 | ☐ |

### 3.2 获取代码

```bash
# 方式 A：Git 克隆（如已推送到仓库）
git clone <repository-url> ~/RAG项目
cd ~/RAG项目

# 方式 B：直接解压项目压缩包
unzip RAG项目.zip -d ~/
cd ~/RAG项目
```

### 3.3 数据库初始化

#### 步骤 1：执行 Schema 初始化脚本

项目已提供 `backend/database/init.sql` 一键初始化脚本，会创建数据库、3 张表（documents、chat_sessions、chat_messages）、索引与约束。

```bash
# 进入项目目录
cd /path/to/RAG项目

# 使用 root 登录 MariaDB 并执行初始化脚本
mariadb -u root -p < backend/database/init.sql
# 输入 root 密码后回车

# 验证数据库与表已创建
mariadb -u root -p -e "USE ai_knowledge_base; SHOW TABLES; SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'ai_knowledge_base';"
```

**预期输出**：

```
+-------------------------+
| Tables_in_ai_knowledge_base |
+-------------------------+
| chat_messages           |
| chat_sessions           |
| documents               |
+-------------------------+

+--------------+----------------------+
| TABLE_NAME   | TABLE_COMMENT        |
+--------------+----------------------+
| chat_messages | 聊天消息表           |
| chat_sessions | 聊天会话表           |
| documents     | 文档元数据表         |
+--------------+----------------------+
```

#### 步骤 2：（可选）创建独立数据库用户

为安全起见，建议创建独立数据库用户而非使用 root：

```sql
-- 登录 MariaDB
-- mariadb -u root -p

CREATE USER 'ai_kb'@'localhost' IDENTIFIED BY 'your-strong-password';
GRANT ALL PRIVILEGES ON ai_knowledge_base.* TO 'ai_kb'@'localhost';
FLUSH PRIVILEGES;
```

然后将 `.env` 中的 `DATABASE_URL` 改为：
```
DATABASE_URL=mysql+asyncmy://ai_kb:your-strong-password@127.0.0.1:3306/ai_knowledge_base
```

### 3.4 后端部署

#### 步骤 1：创建虚拟环境

```bash
cd /path/to/RAG项目/backend

# 创建虚拟环境
python3.11 -m venv .venv

# 激活虚拟环境
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .\.venv\Scripts\Activate.ps1
# Windows (CMD):
# .venv\Scripts\activate.bat

# 验证（应指向 .venv 内的 python）
which python && python --version
```

#### 步骤 2：安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 验证关键依赖
python -c "import fastapi, sqlalchemy, chromadb, openai; print('依赖安装成功')"
```

> **首次安装提示**：`asyncmy` 与 `sentence-transformers` 编译安装可能耗时 3~10 分钟，请耐心等待。如遇编译错误，请确认已安装 Python 开发头文件（`python3.11-dev`）与 MySQL 客户端库（`default-libmysqlclient-dev`）。

#### 步骤 3：配置 .env

```bash
# 从模板复制
cp .env.example .env

# 编辑 .env，填写真实配置
# 必填项：
#   - DATABASE_URL（数据库连接串，含密码）
#   - OPENAI_API_KEY（OpenAI API Key）
# 选填项（保留默认即可）：
#   - APP_HOST / APP_PORT / DEBUG
#   - 其他 RAG 参数
nano .env  # 或使用 vim / code / 任意编辑器
```

**`.env` 必须包含的关键配置**：

```env
# 应用配置
APP_HOST=127.0.0.1
APP_PORT=8000
DEBUG=false                # 生产/演示环境必须 false（SEC-003）

# MariaDB（修改为真实密码）
DATABASE_URL=mysql+asyncmy://root:你的真实密码@127.0.0.1:3306/ai_knowledge_base

# OpenAI（修改为真实 API Key）
OPENAI_API_KEY=sk-你的真实API Key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# 其他配置项保留默认即可
```

> 🔴 **C3 约束**：`.env` 已被 `.gitignore` 排除，**绝不会提交到 Git**。如不慎提交，需立即轮换 API Key。

#### 步骤 4：创建数据目录

```bash
# 在 backend 目录下创建数据目录（.gitignore 已排除）
mkdir -p data/uploads data/chroma data/models data/logs

# （可选）收紧 data 目录权限（SEC-012 建议）
chmod 700 data/chroma data/uploads
```

#### 步骤 5：验证后端可启动

```bash
# 在 backend 目录、虚拟环境已激活的状态下
# 启动后端（前台运行，用于验证）
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 看到以下输出表示启动成功：
# INFO:     应用启动完成
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

# 另开一个终端验证健康检查
curl http://127.0.0.1:8000/health
# 预期返回：{"status":"ok","service":"ai-knowledge-base"}

# 验证 API 文档（DEBUG=false 时不暴露，临时调试可改 DEBUG=true）
# curl http://127.0.0.1:8000/docs

# 验证完成后按 Ctrl+C 停止后端
```

### 3.5 前端部署

#### 步骤 1：安装依赖

```bash
cd /path/to/RAG项目/frontend

# 安装依赖
npm install

# 验证
npm run lint:check  # 应零错误
```

#### 步骤 2：配置前端环境变量

```bash
# 开发环境（默认即可，已配置 .env.development）
cat .env.development
# VITE_API_BASE_URL=/api
# VITE_BACKEND_HEALTH_URL=http://127.0.0.1:8000/health

# 生产预览环境（如需 npm run preview，配置 .env.production）
# 已默认配置为：VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

> **说明**：本项目面向作品集演示，**默认使用开发模式（`npm run dev`）启动**，通过 Vite Proxy 转发 `/api` 到后端，规避 CORS。如需静态构建产物部署，可执行 `npm run build` 后用 `npm run preview` 启动，或交由 Nginx 托管 `dist/`。

#### 步骤 3：验证前端可启动

```bash
# 确保后端已启动（步骤 3.4 步骤 5）
npm run dev

# 看到以下输出表示启动成功：
#   VITE v5.4.x  ready in xxx ms
#   ➜  Local:   http://127.0.0.1:5173/

# 浏览器访问 http://127.0.0.1:5173
# 应看到 AI 文档知识库界面，左侧栏可上传文档，右侧为对话区

# 验证完成后按 Ctrl+C 停止前端
```

### 3.6 一键启动

完成上述一次性配置后，日常启停使用项目根目录提供的一键脚本：

```bash
cd /path/to/RAG项目

# 一键启动（自动启动前后端，后台运行）
./scripts/start.sh

# 查看状态
./scripts/status.sh

# 一键停止
./scripts/stop.sh

# 重启
./scripts/restart.sh
```

脚本功能详见 [附录 B：启动脚本说明](#附录-b启动脚本说明)。

### 3.7 部署后验证

| # | 验证项 | 方法 | 预期结果 | 状态 |
|---|--------|------|----------|------|
| 1 | 后端健康检查 | `curl http://127.0.0.1:8000/health` | `{"status":"ok",...}` | ☐ |
| 2 | 前端可访问 | 浏览器打开 `http://127.0.0.1:5173` | 显示应用主页 | ☐ |
| 3 | 前后端联通 | 前端页面 → 上传一个 PDF | 上传成功，文档列表显示 | ☐ |
| 4 | RAG 闭环 | 上传文档后提问 | 流式返回答案 + 引用来源 | ☐ |
| 5 | 数据库写入 | `mariadb -u root -p -e "SELECT COUNT(*) FROM ai_knowledge_base.documents"` | 文档数与前端一致 | ☐ |
| 6 | Chroma 写入 | `ls backend/data/chroma/` | 存在 chroma.sqlite3 文件 | ☐ |
| 7 | 日志输出 | `ls backend/data/logs/` | 存在 app.log 文件且内容非空 | ☐ |
| 8 | 文件上传 | `ls backend/data/uploads/` | 存在上传的文档副本 | ☐ |

---

## 4. 配置管理

### 4.1 环境变量清单（后端）

完整配置项见 [backend/.env.example](file:///home/zoe/Public/project/RAG项目/backend/.env.example)，所有配置通过 Pydantic Settings 加载，详见 [backend/app/config/settings.py](file:///home/zoe/Public/project/RAG项目/backend/app/config/settings.py)。

| 配置项 | 默认值 | 是否必填 | 说明 |
|--------|--------|----------|------|
| `APP_HOST` | 127.0.0.1 | 否 | 后端监听地址 |
| `APP_PORT` | 8000 | 否 | 后端监听端口 |
| `DEBUG` | false | 否 | 调试模式（true 时暴露 /docs，SEC-003） |
| `DATABASE_URL` | — | **是** | MariaDB 连接串 |
| `OPENAI_API_KEY` | — | **是** | OpenAI API Key |
| `OPENAI_BASE_URL` | https://api.openai.com/v1 | 否 | OpenAI API 基址（兼容第三方代理） |
| `LLM_MODEL` | gpt-4o-mini | 否 | LLM 模型名 |
| `EMBEDDING_MODEL` | text-embedding-3-small | 否 | Embedding 模型名 |
| `EMBEDDING_PROVIDER` | openai | 否 | Embedding Provider：`openai` 或 `bge` |
| `MODEL_CACHE_DIR` | ./data/models | 否 | 本地模型缓存目录（bge-m3） |
| `CHROMA_PERSIST_DIR` | ./data/chroma | 否 | Chroma 向量库持久化目录 |
| `CHUNK_SIZE` | 500 | 否 | 文本切片大小（字符） |
| `CHUNK_OVERLAP` | 50 | 否 | 切片重叠（字符） |
| `TOP_K` | 5 | 否 | 检索返回数量 |
| `SIMILARITY_THRESHOLD` | 0.3 | 否 | 相似度阈值 |
| `MAX_HISTORY_ROUNDS` | 4 | 否 | 多轮对话保留轮数 |
| `UPLOAD_DIR` | ./data/uploads | 否 | 上传文件存储目录 |
| `MAX_FILE_SIZE_MB` | 20 | 否 | 单文件大小上限（MB） |
| `MAX_DOCUMENTS` | 100 | 否 | 文档数量上限 |
| `LLM_TIMEOUT` | 30 | 否 | LLM 调用超时（秒） |
| `LLM_STREAM_TIMEOUT` | 60 | 否 | LLM 流式调用超时（秒） |
| `LLM_MAX_RETRIES` | 3 | 否 | LLM 最大重试次数 |

### 4.2 环境变量清单（前端）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `VITE_API_BASE_URL` | `/api`（dev） / `http://127.0.0.1:8000/api`（prod） | API 基础路径 |
| `VITE_BACKEND_HEALTH_URL` | `http://127.0.0.1:8000/health` | 后端健康检查地址 |

### 4.3 敏感信息管理

- 🔴 `.env` 文件已被 `.gitignore` 排除，**绝不会提交到 Git**
- `.env.example` 仅作模板，不含真实密钥
- API Key 通过 Pydantic Settings 加载，不写入代码
- 日志中不打印敏感信息（API Key、数据库密码等）
- **切换 Embedding Provider 后必须重启后端服务**（M-002 已知问题，V1.1 修复热切换）

---

## 5. 日志管理

### 5.1 日志配置

后端通过 Python `logging` 模块输出日志，配置见 [backend/app/main.py](file:///home/zoe/Public/project/RAG项目/backend/app/main.py#L26-L32)。

**当前配置（控制台输出）**：

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

### 5.2 日志文件（部署时配置）

启动脚本 `scripts/start.sh` 已通过输出重定向将日志写入文件：

| 日志文件 | 路径 | 说明 |
|----------|------|------|
| 后端日志 | `backend/data/logs/backend.out.log` | stdout + stderr |
| 前端日志 | `frontend/data/logs/frontend.out.log` | stdout + stderr |

### 5.3 日志级别

| 环境 | LOG_LEVEL | 说明 |
|------|-----------|------|
| 开发调试 | DEBUG | 输出详细调试信息 |
| 演示运行 | INFO（默认） | 输出关键运行信息 |
| 生产运行 | WARNING | 仅输出警告与错误 |

> 当前 `LOG_LEVEL` 由 `main.py` 中 `logging.basicConfig(level=logging.INFO)` 固定为 INFO。如需调整，编辑 [backend/app/main.py](file:///home/zoe/Public/project/RAG项目/backend/app/main.py#L28) 中的 `level` 字段。V1.1 计划将日志级别提取到 `.env`（RS-007）。

### 5.4 日志查看

```bash
# 实时查看后端日志
tail -f backend/data/logs/backend.out.log

# 查看最近 100 行后端日志
tail -n 100 backend/data/logs/backend.out.log

# 过滤错误日志
grep -i "error\|exception\|traceback" backend/data/logs/backend.out.log

# 查看前端日志
tail -f frontend/data/logs/frontend.out.log
```

### 5.5 日志轮转（建议）

MVP 阶段不强制配置日志轮转。长期运行建议使用 `logrotate`（Linux）：

```bash
# /etc/logrotate.d/ai-kb
/path/to/RAG项目/backend/data/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

---

## 6. 监控与告警

### 6.1 健康检查

项目已内置健康检查端点 [backend/app/main.py:108](file:///home/zoe/Public/project/RAG项目/backend/app/main.py#L108)：

```bash
# 健康检查端点
GET /health

# 响应
{"status": "ok", "service": "ai-knowledge-base"}
```

### 6.2 健康检查脚本

项目提供 `scripts/healthcheck.sh` 一键检查前后端状态：

```bash
./scripts/healthcheck.sh
```

输出示例：

```
[2026-07-13 10:00:00] 健康检查开始
[OK]   后端 http://127.0.0.1:8000/health → {"status":"ok","service":"ai-knowledge-base"}
[OK]   前端 http://127.0.0.1:5173        → HTTP 200
[OK]   MariaDB 127.0.0.1:3306             → 在线
[OK]   Chroma 数据                         → backend/data/chroma/chroma.sqlite3 (2.3 MB)
[OK]   日志目录                            → backend/data/logs/ 可写
[2026-07-13 10:00:01] 健康检查完成：6/6 通过
```

### 6.3 关键监控指标

MVP 阶段为本地单用户，监控以"可用性"为主，不引入 Prometheus/Grafana：

| 指标 | 检查方法 | 预期 | 频率 |
|------|----------|------|------|
| 后端存活 | `curl http://127.0.0.1:8000/health` | 200 OK | 每次使用前 |
| 前端存活 | `curl -I http://127.0.0.1:5173` | 200 OK | 每次使用前 |
| MariaDB 存活 | `mariadb -e "SELECT 1"` | 1 | 每次使用前 |
| Chroma 数据 | `ls backend/data/chroma/` | 存在 sqlite3 文件 | 异常时 |
| 磁盘空间 | `df -h .` | 使用率 < 85% | 每周 |
| 日志异常 | `grep ERROR backend/data/logs/*.log` | 无新增 | 异常时 |

### 6.4 告警（建议）

本地部署阶段不强制配置告警。如需邮件/消息通知，可结合 `scripts/healthcheck.sh` 与 cron：

```bash
# crontab -e
# 每 5 分钟健康检查，失败时写入日志
*/5 * * * * /path/to/RAG项目/scripts/healthcheck.sh >> /path/to/RAG项目/backend/data/logs/healthcheck.log 2>&1
```

### 6.5 性能基线

依据 QA Engineer 性能测试报告（[test-report.md](file:///home/zoe/Public/project/RAG项目/docs/test-report.md)）：

| 指标 | PRD 目标 | 实测值 | 状态 | 说明 |
|------|----------|--------|------|------|
| 端到端响应 P95 | < 15s | 6.8s | ✅ 达标 | PT-001 |
| 首 Token 延迟 | < 3s | 5.0s | ⚠️ 超标 | PT-002，由 OpenAI API 代理延迟导致 |
| API 响应时间 | < 100ms | 1~5ms | ✅ 达标 | PT-005 |

> **首 Token 延迟说明**：实测 5.0s 超过 PRD 目标 3s，主要受 OpenAI API 网络代理影响。部署时如需优化，可：(1) 配置更快的 API 代理端点（修改 `OPENAI_BASE_URL`）；(2) 切换到本地 LLM（V2 规划）；(3) 使用更接近的 API 区域。

---

## 7. 备份与恢复

### 7.1 备份策略

| 资源 | 频率 | 保留 | 备份方式 |
|------|------|------|----------|
| MariaDB 数据 | 每次重要变更前 | 永久（手动） | `mariadb-dump` 全量导出 |
| Chroma 向量库 | 每次重要变更前 | 永久（手动） | 目录复制 |
| 上传文档 | 每次重要变更前 | 永久（手动） | 目录复制 |
| `.env` 配置 | 每次变更后 | 永久（手动） | 文件复制（注意保密） |

> MVP 阶段为本地单用户，未配置自动备份。**建议在重要操作（如切换 Provider、重构索引）前手动备份**。

### 7.2 备份脚本

```bash
#!/bin/bash
# 手动备份脚本（保存为 backup.sh）
# 用法: ./backup.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "开始备份到 $BACKUP_DIR ..."

# 1. 备份 MariaDB（需要 root 密码，会提示输入）
mariadb-dump -u root -p ai_knowledge_base > "$BACKUP_DIR/mariadb.sql"

# 2. 备份 Chroma 向量库
cp -r backend/data/chroma "$BACKUP_DIR/chroma"

# 3. 备份上传文档
cp -r backend/data/uploads "$BACKUP_DIR/uploads"

# 4. 备份 .env 配置（注意保密）
cp backend/.env "$BACKUP_DIR/.env.backup"

echo "备份完成: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
```

### 7.3 恢复流程

#### 步骤 1：停止服务

```bash
./scripts/stop.sh
```

#### 步骤 2：恢复 MariaDB

```bash
# 登录 MariaDB 创建空数据库
mariadb -u root -p -e "DROP DATABASE IF EXISTS ai_knowledge_base; CREATE DATABASE ai_knowledge_base DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 导入备份
mariadb -u root -p ai_knowledge_base < backups/YYYYMMDD_HHMMSS/mariadb.sql
```

#### 步骤 3：恢复 Chroma 与上传目录

```bash
# 删除现有数据
rm -rf backend/data/chroma backend/data/uploads

# 从备份恢复
cp -r backups/YYYYMMDD_HHMMSS/chroma backend/data/
cp -r backups/YYYYMMDD_HHMMSS/uploads backend/data/

# 修正权限
chmod 700 backend/data/chroma backend/data/uploads
```

#### 步骤 4：恢复 .env（如需要）

```bash
cp backups/YYYYMMDD_HHMMSS/.env.backup backend/.env
```

#### 步骤 5：重启服务并验证

```bash
./scripts/start.sh
./scripts/healthcheck.sh
```

### 7.4 备份验证

> **重要**：配置备份后必须至少执行一次恢复演练，验证备份可用。建议每月演练一次。

```bash
# 验证 SQL 备份可读
mariadb -u root -p --execute="SELECT COUNT(*) FROM ai_knowledge_base.documents;" < backups/YYYYMMDD_HHMMSS/mariadb.sql 2>&1 | head

# 验证 Chroma 备份完整
ls -la backups/YYYYMMDD_HHMMSS/chroma/
# 应包含 chroma.sqlite3 文件
```

---

## 8. 回滚方案

### 8.1 回滚触发条件

| 条件 | 阈值 | 检查方式 |
|------|------|----------|
| 后端无法启动 | `curl /health` 失败连续 3 次 | 健康检查 |
| 数据库迁移失败 | 启动报错 | 后端日志 |
| 核心功能不可用 | 上传或问答失败 | 手动验证 |
| 配置错误 | `.env` 配置错误 | 启动日志 |

### 8.2 回滚步骤

```
检测到回滚条件
    ↓
1. 停止服务
   ./scripts/stop.sh
    ↓
2. 评估问题
   ├── 配置问题 → 修正 .env → 重启
   ├── 数据问题 → 恢复备份（见 7.3）
   └── 代码问题 → 切换到上一可用版本（Git checkout）
    ↓
3. 执行恢复
    ↓
4. 重启验证
   ./scripts/start.sh && ./scripts/healthcheck.sh
    ↓
5. 记录事后分析
```

### 8.3 代码版本回滚（如使用 Git）

```bash
# 查看历史版本
git log --oneline

# 回滚到上一版本
git checkout <previous-commit-hash>

# 重装依赖（如 requirements.txt 有变更）
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 重启
./scripts/restart.sh
```

---

## 9. 已知问题与部署注意事项

> 完整问题清单见 [code-review-report.md](file:///home/zoe/Public/project/RAG项目/docs/code-review-report.md) 与 [security-audit-report.md](file:///home/zoe/Public/project/RAG项目/docs/security-audit-report.md)。

### 9.1 部署相关注意事项

| # | 事项 | 影响 | 处理建议 |
|---|------|------|----------|
| 1 | **切换 Embedding Provider 后必须重启后端**（M-002） | 切换不生效 | 修改 `.env` 中 `EMBEDDING_PROVIDER` 后执行 `./scripts/restart.sh` |
| 2 | **向量维度必须匹配 Provider**（M-007） | 维度不匹配导致检索失败 | OpenAI=1536 维，BGE=1024 维；切换后需重建索引（删除 `data/chroma/` 后重新上传文档） |
| 3 | **DEBUG=false 时不暴露 API 文档**（SEC-003） | 无法访问 `/docs` | 调试时临时改 `DEBUG=true` 并重启，调试后改回 `false` |
| 4 | **CORS 配置较宽松**（SEC-009） | 本地部署可接受 | V1.1 收紧为精确匹配来源；本地部署无需处理 |
| 5 | **`data/chroma/` 目录权限**（SEC-012） | 安全加固建议 | 执行 `chmod 700 backend/data/chroma` |
| 6 | **首 Token 延迟 5.0s**（PT-002） | 用户体验略差 | 由 OpenAI API 代理延迟导致；可配置更快的 `OPENAI_BASE_URL` |
| 7 | **首次加载 BGE 本地模型需下载几百 MB~1GB** | 首次启动慢 | 默认使用 OpenAI Embedding（在线）；切换到 `bge` 时首次需等待下载 |
| 8 | **`PyPDF2` 已弃用**（TD-007/SEC-011） | 不影响功能 | V1.1 迁移到 `pypdf` |
| 9 | **流式输出未调用输出校验**（M-008/SEC-008） | 安全相关 | V1.1 在 `done` 事件前调用 `validate_answer()` |
| 10 | **扫描型 PDF 不支持** | 用户上传报错 | PRD 已明确不支持；前端会显示友好错误提示 |

### 9.2 部署检查重点

部署时请重点关注以下文件是否配置正确：

| 文件 | 检查内容 |
|------|----------|
| `backend/.env` | DATABASE_URL 含正确密码、OPENAI_API_KEY 已填写、DEBUG=false |
| `backend/database/init.sql` | 已执行，3 张表已创建 |
| `backend/data/` 目录 | uploads/chroma/models/logs 四个子目录已创建 |
| `frontend/.env.development` | VITE_API_BASE_URL=/api（默认） |
| 端口 | 5173、8000、3306 未被占用 |

---

## 10. 部署后运维操作

### 10.1 日常启停

```bash
./scripts/start.sh        # 启动
./scripts/stop.sh         # 停止
./scripts/restart.sh      # 重启
./scripts/status.sh       # 查看状态
./scripts/healthcheck.sh  # 健康检查
```

### 10.2 日志查看

```bash
# 实时查看后端日志
tail -f backend/data/logs/backend.out.log

# 实时查看前端日志
tail -f frontend/data/logs/frontend.out.log

# 查看历史错误
grep -i "error\|traceback" backend/data/logs/backend.out.log | tail -50
```

### 10.3 数据库维护

```bash
# 查看文档数量
mariadb -u root -p -e "SELECT COUNT(*), status FROM ai_knowledge_base.documents GROUP BY status;"

# 查看会话数量
mariadb -u root -p -e "SELECT COUNT(*) FROM ai_knowledge_base.chat_sessions WHERE deleted_at IS NULL;"

# 清理已删除的文档（软删除 → 物理删除）
mariadb -u root -p -e "DELETE FROM ai_knowledge_base.documents WHERE deleted_at IS NOT NULL;"
```

### 10.4 Chroma 维护

```bash
# 查看 Chroma 数据大小
du -sh backend/data/chroma/

# 重建向量索引（切换 Provider 后必须执行）
./scripts/stop.sh
rm -rf backend/data/chroma/*
./scripts/start.sh
# 然后重新上传所有文档
```

### 10.5 更新依赖

```bash
# 后端
cd backend
source .venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate

# 前端
cd frontend
npm update
```

---

## 附录 A：部署检查清单

### A.1 部署前检查

- [ ] Python 3.11+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] MariaDB 10.5+ 已安装并运行
- [ ] MariaDB root 密码已知
- [ ] OpenAI API Key 已获取
- [ ] 项目代码已下载
- [ ] 端口 5173、8000、3306 未被占用

### A.2 数据库检查

- [ ] `init.sql` 已执行
- [ ] 数据库 `ai_knowledge_base` 已创建
- [ ] 3 张表已创建（documents、chat_sessions、chat_messages）
- [ ] （可选）独立数据库用户已创建并授权

### A.3 后端检查

- [ ] 虚拟环境已创建并激活
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] `.env` 已配置（DATABASE_URL、OPENAI_API_KEY 已填写）
- [ ] 数据目录已创建（data/uploads、data/chroma、data/models、data/logs）
- [ ] `DEBUG=false`
- [ ] `uvicorn app.main:app` 可启动
- [ ] `curl /health` 返回 200

### A.4 前端检查

- [ ] 依赖已安装（`npm install`）
- [ ] `npm run lint:check` 零错误
- [ ] `npm run dev` 可启动
- [ ] 浏览器可访问 `http://127.0.0.1:5173`

### A.5 联通性检查

- [ ] 前端可调用后端 API（上传文档成功）
- [ ] RAG 问答可返回答案
- [ ] 数据库已写入文档记录
- [ ] Chroma 已写入向量数据
- [ ] 日志文件已生成

### A.6 部署后验证

- [ ] `./scripts/healthcheck.sh` 全部通过
- [ ] 上传一个测试 PDF 文档，状态变为 completed
- [ ] 提问后流式返回答案 + 引用来源
- [ ] 多轮对话上下文生效
- [ ] 文档删除后向量同步删除
- [ ] 重启服务后历史会话可恢复

---

## 附录 B：启动脚本说明

项目 `scripts/` 目录提供以下脚本：

| 脚本 | 功能 | 用法 |
|------|------|------|
| `start.sh` | 启动前后端（后台运行） | `./scripts/start.sh` |
| `stop.sh` | 停止前后端 | `./scripts/stop.sh` |
| `restart.sh` | 重启前后端 | `./scripts/restart.sh` |
| `status.sh` | 查看运行状态 | `./scripts/status.sh` |
| `healthcheck.sh` | 健康检查 | `./scripts/healthcheck.sh` |
| `start.bat` | Windows 启动脚本 | `scripts\start.bat` 或双击 |

### 脚本行为说明

**`scripts/start.sh`** 会执行以下操作：

1. 检查 Python 3.11+ / Node.js 18+ / MariaDB 是否可用
2. 检查 `backend/.env` 是否存在，不存在则从 `.env.example` 复制并提示编辑
3. 激活后端虚拟环境（不存在则创建）
4. 创建数据目录 `data/{uploads,chroma,models,logs}`
5. 后台启动后端 uvicorn，PID 写入 `backend/backend.pid`，日志写入 `backend/data/logs/backend.out.log`
6. 后台启动前端 Vite，PID 写入 `frontend/frontend.pid`，日志写入 `frontend/data/logs/frontend.out.log`
7. 等待 5 秒后执行健康检查，输出启动结果

**`scripts/stop.sh`** 会通过 PID 文件优雅停止服务，超时后强制 kill。

---

## 附录 C：变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-13 | 初始版本，本地原生部署方案（禁用 Docker），覆盖环境准备、数据库初始化、前后端部署、一键启动、日志、监控、备份恢复、回滚、已知问题 | DevOps Engineer |

---

**本部署方案严格遵循项目硬约束 C1（禁用 Docker）/ C2（MariaDB 本地安装）/ C3（.env 管理敏感配置）。请 Human Developer 在干净环境按本文档验证可成功启动，作为 G6 门禁前置。**
