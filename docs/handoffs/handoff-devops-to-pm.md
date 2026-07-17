# Handoff: Phase 5（部署上线）→ Phase 5（项目验收）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260713-013 |
| 交接日期 | 2026-07-13 |
| 交接方 | DevOps Engineer |
| 接收方 | Project Manager |
| 交接阶段 | Phase 5（部署上线 TASK-013）→ Phase 5（项目验收 TASK-014） |
| 交接状态 | Ready（⏳ 触发 HITL，等待 Human Developer 干净环境验证 G6 前置） |

## 交接摘要

DevOps Engineer 完成了 AI 文档知识库（MVP）的本地原生部署方案（TASK-013），严格遵循项目硬约束 **C1（全项目禁用 Docker）/ C2（MariaDB 本地安装）/ C3（.env 管理敏感配置）**。

**部署成果**：

- **部署文档**：`docs/deployment-plan.md` v1.0.0，共 10 章 + 3 附录，覆盖部署架构、环境准备（Python/Node/MariaDB 安装）、数据库初始化、后端部署、前端部署、一键启动、配置管理、日志、监控、备份恢复、回滚方案、已知问题
- **启动脚本**：5 个 Linux/macOS 脚本（`start.sh` / `stop.sh` / `restart.sh` / `status.sh` / `healthcheck.sh`）+ 1 个 Windows 脚本（`start.bat`），含环境检查、虚拟环境创建、依赖自动安装、PID 管理、健康检查、端口兜底清理
- **配置模板**：完善 `backend/.env.example`，标注 [必填]/[可选] 与说明，便于部署者配置
- **健康检查**：`healthcheck.sh` 6 项检查（后端 /health、前端可达、MariaDB 端口、Chroma 数据、日志目录、磁盘空间）
- **项目 README**：项目根 `README.md`，含项目介绍、技术栈、目录结构、快速启动、文档导航、测试结果、安全说明、质量门禁状态、路线图
- **.gitignore 补充**：排除 PID 文件与备份目录

**质量门禁**：

- G1（CI/CD）：N/A（本地部署，无 CI/CD 流水线；已通过 `start.sh` 验证启动流程可重复）
- G2（健康检查）：✅ 通过（`/health` 端点 + `healthcheck.sh` 脚本）
- G3（监控配置）：✅ 通过（健康检查 + 监控指标说明 + cron 建议）
- G4（备份配置）：✅ 通过（备份脚本 + 恢复流程 + 备份验证）

**当前状态**：所有部署交付物已完成，**触发 HITL**，等待 Human Developer 在干净环境按 `docs/deployment-plan.md` 验证可成功启动，作为 G6 门禁前置。验证通过后即可进入 TASK-014（项目验收）。

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 部署方案文档 | 文档 | [docs/deployment-plan.md](file:///home/zoe/Public/project/RAG项目/docs/deployment-plan.md) | 完成（v1.0.0，10 章 + 3 附录） |
| 一键启动脚本 | 脚本 | [start.sh](file:///home/zoe/Public/project/RAG项目/start.sh) | 完成（Linux/macOS，含环境检查、虚拟环境、PID 管理、健康检查） |
| 一键停止脚本 | 脚本 | [stop.sh](file:///home/zoe/Public/project/RAG项目/stop.sh) | 完成（优雅停止 + 强制 kill + 端口兜底） |
| 重启脚本 | 脚本 | [restart.sh](file:///home/zoe/Public/project/RAG项目/restart.sh) | 完成 |
| 状态查看脚本 | 脚本 | [status.sh](file:///home/zoe/Public/project/RAG项目/status.sh) | 完成（进程 + 端口 + HTTP 健康检查） |
| 健康检查脚本 | 脚本 | [healthcheck.sh](file:///home/zoe/Public/project/RAG项目/healthcheck.sh) | 完成（6 项检查） |
| Windows 启动脚本 | 脚本 | [start.bat](file:///home/zoe/Public/project/RAG项目/start.bat) | 完成 |
| 后端环境变量模板 | 配置 | [backend/.env.example](file:///home/zoe/Public/project/RAG项目/backend/.env.example) | 完成（[必填]/[可选] 标注） |
| 项目 README | 文档 | [README.md](file:///home/zoe/Public/project/RAG项目/README.md) | 完成（截图位待补） |
| .gitignore 补充 | 配置 | [.gitignore](file:///home/zoe/Public/project/RAG项目/.gitignore) | 完成（排除 PID/备份） |
| Todo 更新 | 文档 | [docs/todo.md](file:///home/zoe/Public/project/RAG项目/docs/todo.md) | 完成（TASK-013 COMPLETED，完成率 93.3%） |

## 关键决策

| 决策编号 | 决策标题 | 影响 |
|----------|----------|------|
| DEVOPS-DEC-001 | 采用本地原生部署，禁用 Docker | 严格遵守 C1；不编写 Dockerfile/docker-compose，所有组件本地运行 |
| DEVOPS-DEC-002 | 使用 `start.sh` 等脚本作为本地部署的"自动化流水线" | 等同于本地 CI/CD：环境检查、虚拟环境创建、依赖安装、启动、健康检查一体化 |
| DEVOPS-DEC-003 | 默认使用开发模式（`npm run dev`）启动前端 | 通过 Vite Proxy 规避 CORS（DEC-015），适合作品集演示场景；可选 `npm run build` + `preview` 静态部署 |
| DEVOPS-DEC-004 | MVP 阶段不引入 Prometheus/Grafana | 本地单用户场景，监控以"可用性"为主，使用 `healthcheck.sh` + cron 即可 |
| DEVOPS-DEC-005 | 备份采用手动脚本而非自动化 | MVP 单用户，建议重要操作前手动备份；文档含完整备份脚本与恢复流程 |
| DEVOPS-DEC-006 | 健康检查端点 `/health` 不需要鉴权 | DEC-001 本地部署无认证；端点仅返回 `{"status":"ok"}`，不泄露敏感信息 |

## 已知问题

### 部署相关已知问题（来自代码审查与安全审计，详见 deployment-plan.md 第 9 章）

| # | 问题 | 严重程度 | 对部署的影响 | 处理建议 |
|---|------|----------|-------------|----------|
| 1 | M-002: 切换 Embedding Provider 后必须重启后端 | Medium | 切换不生效 | 部署文档已注明：修改 `.env` 后执行 `./restart.sh` |
| 2 | M-007: 向量维度必须匹配 Provider | Medium | 维度不匹配导致检索失败 | OpenAI=1536 / BGE=1024；切换后需重建索引（删除 `data/chroma/` 重新上传） |
| 3 | SEC-003: DEBUG=false 时不暴露 API 文档 | Low | 无法访问 `/docs` | 调试时临时改 `DEBUG=true`；部署文档已说明 |
| 4 | SEC-009: CORS 配置较宽松 | Low | 本地部署可接受 | V1.1 收紧；本地部署无需处理 |
| 5 | SEC-012: `data/chroma/` 目录权限 | Low | 安全加固建议 | `start.sh` 已自动 `chmod 700` |
| 6 | PT-002: 首 Token 延迟 5.0s（PRD 目标 3s） | Medium | 用户体验略差 | OpenAI API 代理延迟；可配置更快的 `OPENAI_BASE_URL` |
| 7 | 首次加载 BGE 本地模型需下载几百 MB~1GB | Low | 首次启动慢 | 默认使用 OpenAI Embedding；切换到 BGE 时首次需等待下载 |
| 8 | TD-007/SEC-011: PyPDF2 已弃用 | Low | 不影响功能 | V1.1 迁移到 `pypdf` |
| 9 | M-008/SEC-008: 流式输出未调用输出校验 | Medium | 安全相关 | V1.1 在 `done` 事件前调用 `validate_answer()` |
| 10 | 扫描型 PDF 不支持 | Low | 用户上传报错 | PRD 已明确不支持；前端会显示友好错误 |

### 部署未覆盖项（明确说明）

| 项 | 说明 | 原因 |
|---|------|------|
| Docker 配置 | 不提供 Dockerfile / docker-compose.yml | 🔴 硬约束 C1 禁用 Docker |
| Kubernetes 编排 | 不提供 k8s manifests | 本地单用户部署，无需要 |
| Prometheus / Grafana | 不引入 | 本地单用户场景，监控以可用性为主 |
| ELK / Splunk 日志收集 | 不引入 | 日志输出到本地文件即可 |
| 自动化 CI/CD（GitHub Actions） | 不提供 | 项目未初始化 Git 仓库；本地脚本即"自动化流水线" |
| 截图 | README 预留截图位 | 部署后由 Human Developer 补充 |

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| Human Developer 干净环境验证失败 | 中 | 高 | 部署文档已含完整检查清单与故障排查指引；如失败可对照 `healthcheck.sh` 输出定位 |
| `asyncmy` 编译安装失败（Windows / 缺少编译工具） | 中 | 高 | 部署文档已说明需 Visual C++ Build Tools（Windows）/ `python3.11-dev` + `default-libmysqlclient-dev`（Linux） |
| MariaDB root 密码遗忘 | 低 | 高 | 部署文档建议在 `mysql_secure_installation` 时记录密码；或创建独立用户 |
| OpenAI API Key 配额耗尽 | 中 | 中 | 部署文档已注明 Key 从 https://platform.openai.com/ 获取；MVP 流量低，配额风险低 |
| 首次启动慢（下载 BGE 模型） | 中 | 低 | 默认使用 OpenAI Embedding；BGE 为可选项 |
| 端口被占用（5173 / 8000 / 3306） | 中 | 中 | `start.sh` 含端口占用检查；`stop.sh` 含端口兜底清理 |
| 切换 Provider 后未重启导致检索失败 | 中 | 中 | 部署文档已强调；V1.1 实现热切换后消除 |
| 数据丢失（未备份） | 低 | 高 | 部署文档含完整备份脚本；建议重要操作前手动备份 |

## 假设说明

- 假设代码基线（v1.1.0）与 DevOps Engineer 部署时一致，部署前不再有功能代码变更
- 假设 Security Engineer 的 P0 修复（SEC-001/002/003/006）已全部合入代码基线，G5 门禁已通过
- 假设 QA 的 BUG-010 已修复并回归验证通过，G4 门禁已通过
- 假设部署目标环境为开发者本地机器（localhost，DEC-001），无认证
- 假设 Human Developer 已具备基础的命令行操作能力（执行 `mariadb`、`pip`、`npm` 等命令）
- 假设 Human Developer 已获取 OpenAI API Key
- 假设项目代码已下载到本地（Git 克隆或压缩包解压）
- 假设 `start.sh` 在 Linux/macOS 上执行；Windows 用户使用 `start.bat`
- 假设 `backend/.env` 由部署者填写真实配置（脚本检测占位符会报错退出）

## 下一步建议

### 对 Human Developer 的建议（HITL — 干净环境验证 G6 前置）

1. **干净环境验证**（最重要）：
   - 在未配置开发环境的机器上（或新建用户、新虚拟机），按 [docs/deployment-plan.md](file:///home/zoe/Public/project/RAG项目/docs/deployment-plan.md) 完整执行部署
   - 重点验证：(a) MariaDB 安装与 `init.sql` 执行；(b) `backend/.env` 配置；(c) `./start.sh` 一键启动成功；(d) `./healthcheck.sh` 全部通过；(e) 上传 PDF 文档 → 提问 → 获得流式答案 + 引用来源
   - 验证通过后，G6 门禁可标记为 ✅

2. **截图补充**：在干净环境验证过程中，截取主界面、上传、问答、文档管理 4 张截图，替换 `README.md` 中的截图位

3. **首 Token 延迟评估**：参考 QA 性能测试 PT-002（5.0s 超标），如有更快的 OpenAI API 代理端点，可修改 `OPENAI_BASE_URL`

4. **V1.1 重构排期**：审阅 [docs/refactoring-suggestions.md](file:///home/zoe/Public/project/RAG项目/docs/refactoring-suggestions.md)，确认 RS-001~RS-012 的优先级与排期

### 对 Project Manager 的建议（TASK-014 项目验收）

1. **启动 TASK-014 项目验收**：
   - 等待 Human Developer 干净环境验证通过（G6 前置）
   - 对照 PRD 成功标准 S1~S5 验收
   - 检查所有 Todo 完成状态（TASK-001~015）
   - 汇总所有质量门禁状态：G1 ✅、G2 ✅、G3 ✅、G4 ✅、G5 ✅、G6 待验证

2. **编写交付物**：
   - `docs/project-summary.md`：项目总结（覆盖范围、成果、指标、里程碑）
   - `docs/lessons-learned.md`：经验教训（成功经验、问题与改进、流程优化建议）

3. **质量门禁汇总**：

   | 门禁 | 名称 | 状态 | 说明 |
   |------|------|------|------|
   | G1 | PRD 评审 | ✅ 通过 | v1.0.0 已审批（2026-07-12） |
   | G2 | 架构评审 | ✅ 通过 | DEC-014/015/016 已记录 |
   | G3 | 代码审查 | ✅ 通过 | 0 Critical / 0 High，合规率 ~92% |
   | G4 | 测试 | ✅ 通过 | 229 测试通过，覆盖率 87% |
   | G5 | 安全审计 | ✅ 通过 | P0 漏洞已修复（SEC-001/002/003/006） |
   | G6 | 上线确认 | ⏳ 待验证 | 等 Human Developer 干净环境验证 |

4. **项目最终交付清单**（建议在 project-summary.md 中汇总）：
   - 后端代码：46 个 Python 文件，11 个 API 端点，覆盖率 87%
   - 前端代码：40 个 JS/Vue 文件，36 个源文件
   - 测试：229 单元/集成测试 + 8 E2E + 5 性能测试
   - 文档：23 份（PRD、架构、API 规范、数据库、设计系统、部署方案、测试报告、安全审计、代码审查、决策日志等）
   - 部署：6 个启动脚本 + 健康检查 + 完整部署文档
   - 决策：16 项架构决策（DEC-001~016）

### 整体项目进度

| Phase | 任务 | 状态 |
|-------|------|------|
| Phase 0 | TASK-001 项目规划 | ✅ COMPLETED |
| Phase 0 | TASK-002 技术选型 | ✅ COMPLETED |
| Phase 1 | TASK-003 编写 PRD | ✅ COMPLETED |
| Phase 1 | TASK-004 设计 UI/UX | ✅ COMPLETED |
| Phase 1 | TASK-005 设计系统架构 | ✅ COMPLETED |
| Phase 2 | TASK-006 设计数据库 | ✅ COMPLETED |
| Phase 2 | TASK-007 开发后端 API | ✅ COMPLETED |
| Phase 3 | TASK-008 开发前端 | ✅ COMPLETED |
| Phase 3 | TASK-009 开发 AI 功能 | ✅ COMPLETED |
| Phase 4 | TASK-010 执行测试 | ✅ COMPLETED |
| Phase 4 | TASK-011 执行安全审计 | ✅ COMPLETED |
| Phase 5 | TASK-012 执行代码审查 | ✅ COMPLETED |
| Phase 5 | TASK-013 部署上线 | ✅ COMPLETED（本次） |
| Phase 5 | TASK-014 项目验收 | ⏳ NOT_STARTED（等待 G6 验证） |
| Phase 0 | TASK-015 编写交接文档 | ✅ COMPLETED |

**完成率**：14/15 = 93.3%

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | Project Manager |
| 确认状态 | Pending Confirmation |

---

## 附录：DevOps Engineer 自检 Review Checklist

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 部署文档完整 | ✅ | `deployment-plan.md` v1.0.0，10 章 + 3 附录 |
| 启动脚本可执行 | ✅ | 5 个 Linux/macOS + 1 个 Windows，已 `chmod +x` |
| .env.example 完善 | ✅ | 后端含 [必填]/[可选] 标注，21 个配置项全部说明 |
| 健康检查配置 | ✅ | `/health` 端点 + `healthcheck.sh` 6 项检查 |
| 监控告警配置 | ✅ | 健康检查脚本 + 监控指标 + cron 建议 |
| 日志管理配置 | ✅ | 日志文件路径 + 查看命令 + 轮转建议 |
| 备份恢复配置 | ✅ | 备份脚本 + 恢复流程 + 验证方法 |
| 环境变量管理 | ✅ | Pydantic Settings 加载，无硬编码，.gitignore 排除 .env |
| README 完整 | ✅ | 项目介绍、技术栈、目录结构、快速启动、文档导航、测试结果、安全说明、质量门禁、路线图（截图位待补） |
| 部署检查清单 | ✅ | 附录 A：6 类共 30 项检查清单 |
| 已知问题记录 | ✅ | 10 项部署注意事项 + 6 项未覆盖项明确说明 |
| Todo 已更新 | ✅ | TASK-013 COMPLETED，完成率 93.3%（14/15），变更历史 v2.3.0 |
| Handoff 已编写 | ✅ | 本文档（HO-013） |
| 严格遵循约束 C1 | ✅ | 全项目无任何 Dockerfile / docker-compose.yml |
| 严格遵循约束 C2 | ✅ | 部署文档含 MariaDB 本地安装指引（Linux/macOS/Windows） |
| 严格遵循约束 C3 | ✅ | 所有敏感配置通过 .env 管理，无硬编码 |

---

**交接完成。✅ TASK-013 部署上线已完成。触发 HITL：等待 Human Developer 在干净环境按 `docs/deployment-plan.md` 验证可成功启动，作为 G6 门禁前置。验证通过后 Project Manager 可启动 TASK-014 项目验收。**

**重要约束遵循确认**：
- 🔴 **C1 禁用 Docker**：✅ 全项目未编写任何 Dockerfile / docker-compose.yml，所有组件本地原生运行
- 🔴 **C2 MariaDB 本地安装**：✅ 部署文档含 Linux/macOS/Windows 三平台的 MariaDB 本地安装指引
- 🔴 **C3 .env 管理敏感配置**：✅ 所有敏感配置（DATABASE_URL、OPENAI_API_KEY）通过 `.env` 管理，`.env` 被 `.gitignore` 排除
