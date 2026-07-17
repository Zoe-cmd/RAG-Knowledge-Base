# AI 文档知识库（MVP）

> 基于 RAG（Retrieval-Augmented Generation）的本地 AI 文档知识库，支持文档上传、向量化检索、流式问答与引用来源标注。面向个人学习与作品集展示。

![Status](https://img.shields.io/badge/status-v1.1.0%20MVP-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Node](https://img.shields.io/badge/Node.js-18+-green)
![MariaDB](https://img.shields.io/badge/MariaDB-10.5+-orange)

---

## ✨ 核心特性

- 📄 **多格式文档上传**：PDF / Word / Markdown / TXT，拖拽批量上传，自动解析与切分
- 🔍 **RAG 检索增强生成**：基于向量相似度检索，注入上下文生成回答，避免幻觉
- 🌊 **流式输出**：SSE 实时流式返回答案，支持中断与已生成内容保留
- 📌 **引用来源标注**：每条回答附带引用片段与原文出处
- 💬 **多轮对话上下文**：保留最近 4 轮对话历史，支持上下文截断
- 🔄 **Provider 抽象层**：OpenAI（在线，1536 维）+ BGE 本地模型（1024 维）可配置切换
- 🛡️ **安全加固**：XSS 防护（DOMPurify）、文件类型/大小校验、UUID 文件名、`.env` 管理 API Key
- 🏠 **本地原生部署**：禁用 Docker，MariaDB 本地安装，所有数据本地存储

---

## 🛠️ 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 前端 | Vue 3 + Element Plus + Pinia + Vue Router + Vite | Vue 3.5 / EPlus 2.8 |
| 后端 | Python + FastAPI + uvicorn (ASGI) | Python 3.11 / FastAPI 0.110 |
| 数据库 | MariaDB（本地安装） | 10.5+ |
| 向量库 | Chroma（嵌入式持久化） | 0.5.0 |
| LLM | OpenAI API（gpt-4o-mini，默认） | — |
| Embedding | OpenAI text-embedding-3-small / BGE-m3（可选） | — |
| 文档解析 | PyPDF2 / python-docx / markdown / chardet | — |

> 📌 详细技术选型见 [docs/tech-review-report.md](file:///home/zoe/Public/project/RAG项目/docs/tech-review-report.md) 与 [docs/decision-log.md](file:///home/zoe/Public/project/RAG项目/docs/decision-log.md)。

---

## 📁 项目结构

```
RAG项目/
├── backend/                          # 后端（Python + FastAPI）
│   ├── app/
│   │   ├── api/                       # API 路由层（documents / chat / sessions / config）
│   │   ├── services/                  # 业务逻辑层（rag / chat / document / embedding）
│   │   ├── providers/                 # Provider 抽象层（embedding / llm，工厂模式）
│   │   ├── models/                    # 数据模型（SQLAlchemy ORM）
│   │   ├── chunkers/                  # 文本切分器（递归字符切分）
│   │   ├── parsers/                   # 文档解析器（PDF / DOCX / MD / TXT）
│   │   ├── config/                    # 配置管理（Pydantic Settings）
│   │   ├── database/                  # 数据库会话管理
│   │   ├── utils/                     # 工具函数（异常 / 响应 / SSE）
│   │   └── main.py                    # FastAPI 应用入口
│   ├── database/
│   │   └── init.sql                   # MariaDB Schema 初始化脚本
│   ├── data/                          # 运行时数据（.gitignore 排除）
│   │   ├── uploads/                   # 上传的原始文档
│   │   ├── chroma/                    # Chroma 向量库持久化
│   │   ├── models/                    # 本地模型缓存（bge-m3）
│   │   └── logs/                      # 应用日志
│   ├── tests/                         # 单元测试 + 集成测试
│   ├── .env.example                   # 环境变量模板
│   ├── requirements.txt               # Python 依赖
│   └── pytest.ini                     # 测试配置
│
├── frontend/                          # 前端（Vue3 + Element Plus）
│   ├── src/
│   │   ├── api/                       # API 调用层（axios 封装 + SSE 解析）
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── components/                # Vue 组件（对话 / 文档 / 布局）
│   │   ├── views/                     # 页面视图
│   │   ├── router/                    # Vue Router 路由
│   │   ├── utils/                     # 工具函数（常量 / Markdown / 格式化）
│   │   └── App.vue                    # 根组件
│   ├── .env.development               # 开发环境变量
│   ├── .env.production                # 生产环境变量
│   ├── vite.config.js                 # Vite 配置（含 Proxy）
│   └── package.json
│
├── docs/                              # 项目文档
│   ├── prd.md                         # 产品需求文档
│   ├── architecture.md                # 系统架构设计
│   ├── api-spec.md                    # API 规范
│   ├── database-schema.md             # 数据库 Schema
│   ├── design-system.md               # 设计系统
│   ├── deployment-plan.md             # 🚀 部署方案（开始这里）
│   ├── test-report.md                 # 测试报告
│   ├── security-audit-report.md       # 安全审计报告
│   ├── code-review-report.md          # 代码审查报告
│   ├── decision-log.md                # 决策日志
│   ├── todo.md                        # 任务清单
│   └── handoffs/                      # 阶段交接文档
│
├── start.sh / stop.sh / restart.sh    # 一键启动/停止/重启脚本（Linux/macOS）
├── status.sh / healthcheck.sh         # 状态查看 / 健康检查脚本
├── start.bat                          # Windows 启动脚本
├── .gitignore
└── README.md                          # 本文件
```

---

## 🚀 快速开始

### 前置条件

| 组件 | 版本 | 必需 |
|---|---|---|
| Python | 3.11+ | ✅ |
| Node.js | 18+ | ✅ |
| MariaDB | 10.5+ | ✅ |
| OpenAI API Key | — | ✅ |

> 🔴 **硬约束**：本项目**禁用 Docker**（DEC-005），MariaDB 必须**本地安装**（C2），敏感配置通过 `.env` 管理（C3）。

### 三步启动

#### 1️⃣ 初始化数据库

```bash
# 安装 MariaDB（如未安装，详见部署文档 2.4 节）
# 执行 Schema 初始化脚本
mariadb -u root -p < backend/database/init.sql
```

#### 2️⃣ 配置 .env

```bash
cd backend
cp .env.example .env
nano .env
# 必填项：
#   DATABASE_URL=mysql+asyncmy://root:你的密码@127.0.0.1:3306/ai_knowledge_base
#   OPENAI_API_KEY=sk-你的真实Key
cd ..
```

#### 3️⃣ 一键启动

```bash
./start.sh
```

启动成功后访问：

| 服务 | 地址 |
|---|---|
| 🖥️ 前端 | http://127.0.0.1:5173 |
| ⚙️ 后端 API | http://127.0.0.1:8000 |
| ❤️ 健康检查 | http://127.0.0.1:8000/health |
| 📚 API 文档 | http://127.0.0.1:8000/docs（仅 `DEBUG=true`） |

### 日常操作

```bash
./start.sh        # 启动
./stop.sh         # 停止
./restart.sh      # 重启
./status.sh       # 查看运行状态
./healthcheck.sh  # 健康检查
```

> 📖 完整部署指南见 [docs/deployment-plan.md](file:///home/zoe/Public/project/RAG项目/docs/deployment-plan.md)

---

## 📸 截图

> 截图位（部署后可由 Human Developer 补充）

| 截图 | 说明 |
|---|---|
| ![main](docs/screenshots/main.png) | 主界面（左右分栏：会话列表 + 对话区） |
| ![upload](docs/screenshots/upload.png) | 文档上传（拖拽 + 进度） |
| ![chat](docs/screenshots/chat.png) | 流式问答（光标 + 引用来源） |
| ![documents](docs/screenshots/documents.png) | 文档管理列表 |

---

## 📖 文档导航

| 文档 | 说明 |
|---|---|
| [🚀 部署方案](file:///home/zoe/Public/project/RAG项目/docs/deployment-plan.md) | 本地部署完整指南 |
| [📋 PRD](file:///home/zoe/Public/project/RAG项目/docs/prd.md) | 产品需求文档 |
| [🏗️ 架构设计](file:///home/zoe/Public/project/RAG项目/docs/architecture.md) | 系统架构与设计决策 |
| [🔌 API 规范](file:///home/zoe/Public/project/RAG项目/docs/api-spec.md) | 11 个 API 端点详细说明 |
| [🗄️ 数据库 Schema](file:///home/zoe/Public/project/RAG项目/docs/database-schema.md) | MariaDB 表结构 + Chroma collection |
| [🤖 Prompt 设计](file:///home/zoe/Public/project/RAG项目/docs/prompts.md) | Prompt 模板与版本管理 |
| [📚 RAG 原理](file:///home/zoe/Public/project/RAG项目/docs/rag-explanation.md) | 面向初学者的 RAG 原理说明 |
| [🧪 测试报告](file:///home/zoe/Public/project/RAG项目/docs/test-report.md) | 单元/集成/E2E/性能测试 |
| [🔒 安全审计](file:///home/zoe/Public/project/RAG项目/docs/security-audit-report.md) | OWASP Top 10 安全审计 |
| [👀 代码审查](file:///home/zoe/Public/project/RAG项目/docs/code-review-report.md) | 86 文件代码审查报告 |
| [📝 决策日志](file:///home/zoe/Public/project/RAG项目/docs/decision-log.md) | 16 项架构决策记录 |

---

## 🧪 测试

```bash
cd backend
source .venv/bin/activate    # 激活虚拟环境
pytest                        # 运行所有测试
pytest --cov=app              # 生成覆盖率报告
```

**测试结果**（v1.1.0）：

| 指标 | 数值 | 目标 | 状态 |
|---|---|---|---|
| 单元测试 | 228 通过 | — | ✅ |
| 集成测试 | 17 通过 | — | ✅ |
| 总测试数 | 229 通过 | — | ✅ |
| 覆盖率 | 87.21% | ≥ 80% | ✅ |
| E2E 测试 | 6/8 通过 | — | ⚠️ |
| 性能 P95 | 6.8s | < 15s | ✅ |

---

## 🔒 安全

- ✅ **G5 门禁通过**：13 项漏洞中 P0 已全部修复
- ✅ `.env` 被 `.gitignore` 排除，不会提交
- ✅ API Key 通过 Pydantic Settings 加载，不硬编码
- ✅ DEBUG=false 时不暴露 `/docs` API 文档（SEC-003）
- ✅ 文件上传：扩展名校验 + 20MB 大小限制 + UUID 文件名
- ✅ 前端 XSS 防护：DOMPurify 净化 Markdown 渲染
- ✅ SQL 注入防护：SQLAlchemy ORM 参数化查询
- ⚠️ 9 项 Medium/Low 漏洞计划 V1.1/V2 修复（不阻塞 MVP）

> 📖 完整审计见 [docs/security-audit-report.md](file:///home/zoe/Public/project/RAG项目/docs/security-audit-report.md)

---

## 📊 质量门禁状态

| 门禁 | 名称 | 状态 | 说明 |
|---|---|---|---|
| G1 | PRD 评审 | ✅ 通过 | v1.0.0 已审批 |
| G2 | 架构评审 | ✅ 通过 | DEC-014/015/016 已记录 |
| G3 | 代码审查 | ✅ 通过 | 0 Critical / 0 High |
| G4 | 测试 | ✅ 通过 | 229 测试通过，覆盖率 87% |
| G5 | 安全审计 | ✅ 通过 | P0 漏洞已修复 |
| G6 | 上线确认 | ⏳ 待验证 | 待 Human Developer 干净环境验证 |

---

## 🗺️ 路线图

### V1.1（计划中）

- 🔧 typing 风格统一（`List/Dict` → `list/dict`）
- 🔧 Embedding Provider 热切换（无需重启）
- 🔧 流式输出验证守卫（M-008 / SEC-008）
- 🔧 配置项外置（temperature、日志级别等）
- 🔧 PyPDF2 → pypdf 迁移

### V2（规划）

- 🔐 用户认证与多用户支持
- 📝 TypeScript 前端迁移
- 🌐 本地 LLM 支持（Ollama）
- 📊 RAG 评测体系（RAGAS）
- 🔄 文档更新与增量索引

---

## 📜 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

本项目由 13 个 AI Agent 角色协同完成，遵循企业级软件开发流程（需求分析 → 架构设计 → 数据库设计 → 后端开发 → 前端开发 → AI 功能 → 测试 → 安全审计 → 代码评审 → 部署上线）。

| 角色 | 职责 |
|---|---|
| Project Manager | 项目规划与进度跟踪 |
| Tech Lead | 技术选型与决策评审 |
| Product Manager | PRD 撰写 |
| UI/UX Designer | 设计系统与原型 |
| Solution Architect | 架构设计 |
| Database Engineer | 数据库 Schema 设计 |
| Backend Engineer | 后端 API 开发 |
| Frontend Engineer | 前端页面开发 |
| AI Engineer | RAG 管线与 Prompt 工程 |
| QA Engineer | 测试与缺陷管理 |
| Security Engineer | 安全审计与修复 |
| Code Reviewer | 代码审查与重构建议 |
| **DevOps Engineer** | **部署与运维（本角色）** |

---

## 📞 联系

如有问题或建议，欢迎提交 Issue。
