# Handoff: Tech Lead → 产品经理（Phase 0 → Phase 1）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-002 |
| 交接日期 | 2026-07-12 |
| 交接方 | Tech Lead（技术负责人） |
| 接收方 | Product Manager（产品经理） |
| 交接阶段 | Phase 0（技术选型） → Phase 1（需求与设计） |
| 交接状态 | Ready（待 Human Developer 审批技术选型后激活） |

---

## 交接摘要

Phase 0 技术选型阶段已由技术负责人完成核心工作。本次技术选型共制定 7 项技术决策（DEC-007~013），覆盖最终技术栈确认、Embedding Provider 抽象层设计、LLM Provider 抽象层设计、SSE 流式输出方案、多轮对话上下文截断策略、本地 Embedding 模型选型、技术债务基线评估。所有决策已写入决策日志，并通过技术评审报告（TR-20260712-001）评审，结论为"通过"。

技术栈最终确认为：后端 Python 3.11 + FastAPI + SQLAlchemy 2.0 + asyncmy + MariaDB + Chroma；前端 Vue3 + Vite + Element Plus + Pinia + Vue Router + axios；AI 层 OpenAI gpt-4o-mini + text-embedding-3-small（默认）/ bge-m3（可选）。全项目禁用 Docker，所有组件本地运行。

技术选型决策已提交 Human Developer 审批（HITL 门禁）。审批通过后，产品经理可启动 TASK-003 编写 PRD，技术选型决策作为 PRD 的重要输入，约束功能需求的实现边界。

---

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 技术评审报告 | 文档 | `docs/tech-review-report.md` | 完成（待审批） |
| 决策日志（更新） | 文档 | `docs/decision-log.md` | 已追加 DEC-007~013（共 13 项） |
| PM → Tech Lead 交接 | 文档 | `docs/handoffs/handoff-pm-to-techlead.md` | 已确认（HO-001） |
| 项目规划 | 文档 | `docs/project-plan.md` | G1 已通过 |
| 任务清单 | 文档 | `docs/todo.md` | TASK-002 待标记 COMPLETED |

---

## 关键决策

以下 7 项技术决策由技术负责人在 Phase 0 制定，直接影响 Phase 1 及后续阶段的工作：

| 决策编号 | 决策标题 | 对产品经理的影响 |
|----------|----------|------------------|
| DEC-20260712-007 | 最终技术栈确认 | PRD 功能需求需在以下技术栈边界内设计：FastAPI/Vue3/MariaDB/Chroma/OpenAI。不引入 langchain，文本切分自实现 |
| DEC-20260712-008 | Embedding Provider 抽象层 | PRD 需说明双 Embedding 方案（OpenAI 默认 + 本地可选）的用户体验：切换 provider 需重建索引 |
| DEC-20260712-009 | LLM Provider 抽象层 | PRD 需说明 LLM 可配置 base_url，支持兼容端点（如第三方代理） |
| DEC-20260712-010 | SSE 流式输出方案 | PRD 需描述流式回答用户体验：逐字显示 + 引用来源先于回答展示 |
| DEC-20260712-011 | 多轮上下文截断策略 | PRD 需说明多轮对话保留最近 4 轮，超出自动截断（用户需知晓） |
| DEC-20260712-012 | 本地 Embedding 模型 bge-m3 | PRD 需说明本地模型首次下载 2.3GB，需网络环境支持 |
| DEC-20260712-013 | 技术债务基线 | PRD 需在"非功能需求"或"已知限制"章节说明 7 项技术债务 |

### 决策详情速查

**技术栈（DEC-007）**：

| 层级 | 选型 |
|------|------|
| 后端 | Python 3.11 + FastAPI 0.110+ + uvicorn + SQLAlchemy 2.0 + asyncmy |
| 业务数据库 | MariaDB 10.11+（本地安装） |
| 向量数据库 | Chroma 0.5+（嵌入式持久化） |
| 文档解析 | PyPDF2 / python-docx / markdown / chardet |
| 文本切分 | 自实现递归切分（不引入 langchain） |
| 前端 | Vue 3.4 + Vite 5 + Element Plus 2.6+ + Pinia 2.1+ + Vue Router 4.3+ + axios 1.6+ |
| 流式接收 | fetch + ReadableStream |
| Embedding | OpenAI text-embedding-3-small（1536 维，默认）/ bge-m3（1024 维，可选） |
| LLM | OpenAI gpt-4o-mini（可配置 base_url） |

**Provider 抽象层（DEC-008/009）**：
- EmbeddingProvider 抽象类：`embed()`、`dimension`、`name`
- LLMProvider 抽象类：`chat_completion(messages, stream)` 
- 工厂函数配置切换：`get_embedding_provider()`、`get_llm_provider()`
- Chroma collection 命名含 provider 与维度：`kb_openai_1536` / `kb_bge-m3_1024`

**SSE 方案（DEC-010）**：
- 后端：FastAPI StreamingResponse，media_type=text/event-stream
- 事件类型：token / references / done / error
- 引用先于 token 发送
- 前端：fetch + ReadableStream 手动解析（不用 EventSource）

**上下文策略（DEC-011）**：
- 组装：系统提示 + RAG 上下文（top_k=5） + 最近 4 轮（8 条消息） + 当前问题
- Token 预算约 6000（gpt-4o-mini 上下文 128K）
- 按轮数截断，保证对话完整性
- 会话级隔离

---

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| 技术选型待 Human Developer 审批 | Medium | HITL 门禁要求 | PRD 编写可在审批通过后启动，或并行起草待审批后定稿 |
| 文本切分需自实现 | Low | 不引入 langchain | 架构师在 Phase 1 设计切分算法，参考 RecursiveCharacterTextSplitter |
| bge-m3 首次下载 2.3GB | Low | 模型体积大 | 运维工程师在部署文档说明下载步骤与缓存目录 |
| 切换 Embedding provider 需重建索引 | Low | 维度不同 | PRD 需说明此限制，UI 需提示用户 |

---

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| R1 多轮上下文复杂度超预期 | 中 | 中 | DEC-011 已明确截断策略（4 轮），PRD 需描述截断行为 |
| R2 Embedding 抽象层复杂度 | 中 | 中 | DEC-008 接口简洁（3 成员），架构师 Phase 1 细化 UML |
| R3 bge-m3 模型下载慢 | 中 | 低 | 运维文档说明下载步骤，建议首次使用 OpenAI 方案 |
| R5 OpenAI API 费用或网络问题 | 中 | 高 | DEC-009 支持 base_url 兼容端点，可切换第三方代理 |
| R7 SSE 流式输出联调复杂 | 中 | 中 | DEC-010 方案明确，架构师绘制时序图，Phase 4 联调 |
| R11 文本切分自实现质量不稳定 | 低 | 中 | 参考 langchain 逻辑，Phase 4 测试验证 |
| R13 切换 provider 索引重建 | 中 | 低 | collection 命名隔离，UI 提示 |

---

## 假设说明

- **假设 1**：Human Developer 会审批通过 DEC-007~013 技术选型决策。若审批未通过，产品经理需等待技术负责人调整后再启动 PRD。
- **假设 2**：PRD 编写以 DEC-001~013 共 13 项决策为约束边界，不在 PRD 中提出与技术决策冲突的需求。
- **假设 3**：产品经理在 PRD 中描述功能需求时，需同步考虑技术约束（如流式输出、多轮截断、双 Embedding），确保需求可实现。
- **假设 4**：技术债务基线（DEC-013）中的 7 项债务在 V1 可接受，PRD 不应将这些债务列为必须解决的需求。
- **假设 5**：PRD 中的非功能需求（P95 < 15s、并发 1-2、Chrome/Edge/Firefox）已在 DEC-006 确认，PRD 直接引用即可。

---

## 下一步建议

### 对产品经理（TASK-003 编写 PRD）

1. **阅读所有技术决策**：仔细阅读 `docs/decision-log.md` 中 DEC-001~013 共 13 项决策，理解技术约束边界
2. **阅读技术评审报告**：阅读 `docs/tech-review-report.md`，理解技术选型理由与风险
3. **PRD 必须覆盖的功能模块**：
   - 文档管理：上传（批量/拖拽）、解析、列表、删除
   - 向量化：双 Embedding 方案说明、切换提示
   - RAG 问答：多轮对话、流式输出、引用来源
   - 聊天历史：会话管理（新建/切换/删除/清空）
4. **PRD 必须包含的非功能需求**：
   - 性能：单次问答 P95 < 15s
   - 并发：1-2
   - 兼容性：Chrome/Edge/Firefox 最新版
   - 界面语言：简体中文
5. **PRD 必须说明的已知限制**（基于 DEC-013 技术债务）：
   - 不支持 OCR（扫描件 PDF 友好提示）
   - 不支持暗色模式
   - 不支持聊天记录导出
   - 多轮对话仅保留最近 4 轮上下文
   - 切换 Embedding provider 需重建索引
   - 本地模型首次下载 2.3GB
6. **PRD 用户故事建议**：以"个人开发者/学习者"为目标用户，围绕"上传文档→提问→获得引用回答"核心闭环设计
7. **提交 G1 审批**：PRD 完成后提交 Human Developer 审批

### 对后续角色（预告）

| 角色 | 任务 | 启动时机 | 关键输入 |
|------|------|----------|----------|
| UI/UX 设计师 | TASK-004 | PRD 完成后 | PRD + 技术栈（SSE 流式、引用展示） |
| 系统架构师 | TASK-005 | PRD + 设计系统完成后 | PRD + DEC-007~013 + 设计系统 |

### 对架构师的特别提示（Phase 1 预告）

架构师在 TASK-005 中需重点细化以下技术决策的实现细节：
1. Provider 抽象层 UML 类图（DEC-008/009）
2. SSE 流式输出时序图（DEC-010）
3. 多轮上下文组装流程图（DEC-011）
4. 模块划分（文档处理、向量服务、RAG 服务、聊天服务、API 层）
5. 文本切分算法设计（自实现递归切分）

---

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | Product Manager（产品经理） |
| 确认状态 | Pending（等待 Human Developer 审批技术选型后确认） |

### 接收方验证清单

产品经理在确认交接前，需完成以下验证：

- [ ] 已阅读 `docs/tech-review-report.md` 技术评审报告
- [ ] 已阅读 `docs/decision-log.md` 中 DEC-007~013 共 7 项技术决策
- [ ] 已理解技术栈边界（FastAPI/Vue3/MariaDB/Chroma/OpenAI）
- [ ] 已理解双 Embedding 方案对用户体验的影响
- [ ] 已理解 SSE 流式输出与引用来源的呈现方式
- [ ] 已理解多轮对话截断策略（4 轮）
- [ ] 已理解 7 项技术债务作为 PRD"已知限制"的来源
- [ ] 已评估风险 R1~R13 对 PRD 编写的影响
- [ ] 已确认下一步建议的可行性

---

## 交接方验证清单

技术负责人在发出交接前，已完成以下验证：

- [x] 所有交付物已生成并位于指定路径
- [x] 交付物已通过技术评审（TR-20260712-001）
- [x] 交付物之间的引用关系正确，无死链
- [x] 关键决策已记录到 Decision Log（DEC-007~013）
- [x] 已知问题和风险已明确记录
- [x] 假设已明确列出，含验证状态
- [x] 下一步建议具体且可执行
- [x] 交接文档本身已自检（无占位符、无遗漏）
- [x] 评审报告检查清单已完成
- [ ] Todo 状态已更新（待执行：TASK-002 标记 COMPLETED）
- [x] 交接通知已准备发送给产品经理

---

**交接完成。请产品经理在 Human Developer 审批技术选型后，阅读所有交付物再开始 PRD 编写。**

**特别注意**：PRD 的功能需求必须在 DEC-001~013 共 13 项技术决策的约束边界内设计。如有冲突，需通过新决策记录（DEC-YYYYMMDD-NNN）调整，而非在 PRD 中直接覆盖技术决策。
