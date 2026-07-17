<!--
Document: Tech Review Report
Version: 1.0.0
Author: Tech Lead
Created: 2026-07-12
Updated: 2026-07-12
-->

# 技术评审报告：AI 文档知识库（MVP）

## 评审元信息

| 字段 | 内容 |
|------|------|
| 评审编号 | TR-20260712-001 |
| 评审日期 | 2026-07-12 |
| 评审人 | Tech Lead |
| 评审类型 | 技术选型评审（Phase 0） |
| 评审范围 | 项目技术栈、Provider 抽象层、SSE 方案、上下文策略、技术债务基线 |
| 评审输入 | `docs/project-plan.md`、`docs/decision-log.md`（DEC-001~006）、`docs/todo.md` |
| 评审输出 | 本报告 + DEC-007~013 共 7 项技术决策 |
| 评审结论 | 通过（待 Human Developer 审批） |

---

## 1. 评审摘要

本次评审为 Phase 0 技术选型评审，由技术负责人对项目经理在 G1 通过后移交的技术需求进行深入分析，最终确认技术栈并制定 7 项关键技术决策（DEC-007~013）。

**评审结论：通过**

- 技术栈与项目定位（MVP、初级开发者、本地运行、禁用 Docker）高度匹配
- 所有关键选型均为成熟主流技术，社区活跃、文档丰富
- Provider 抽象层设计合理，满足双 Embedding 方案与 LLM 兼容端点切换需求
- SSE 流式输出方案明确，前后端实现路径清晰
- 多轮上下文截断策略合理，Token 预算安全裕度充足
- 技术债务已识别 7 项基线，均有偿还计划，无 Critical 级别债务

**待 Human Developer 关注事项**：见第 7 节"后续行动"。

---

## 2. 评审范围

### 2.1 评审对象

| 评审项 | 内容 | 对应决策 |
|--------|------|----------|
| 最终技术栈 | 前后端、数据库、向量库、AI 模型、依赖库版本 | DEC-007 |
| Embedding Provider 抽象层 | 接口设计、实现策略、collection 命名 | DEC-008 |
| LLM Provider 抽象层 | 接口设计、OpenAI 兼容端点支持 | DEC-009 |
| SSE 流式输出方案 | 后端 StreamingResponse + 前端 fetch streaming | DEC-010 |
| 多轮上下文截断策略 | 组装顺序、截断规则、Token 预算 | DEC-011 |
| 本地 Embedding 模型 | bge-m3 vs m3e 选型 | DEC-012 |
| 技术债务基线 | 7 项已知债务与偿还计划 | DEC-013 |

### 2.2 评审维度

1. **合理性**：技术选型是否匹配项目定位与约束
2. **成熟度**：技术是否主流、社区是否活跃、文档是否完善
3. **一致性**：与 DEC-001~006 是否一致，是否与约束 C1~C6 兼容
4. **可实施性**：初级开发者能否独立实现
5. **可维护性**：代码结构是否清晰、技术债务是否可控
6. **扩展性**：是否为后续版本预留扩展空间

---

## 3. 技术栈评审（DEC-007）

### 3.1 后端技术栈

| 组件 | 选型 | 版本 | 评审意见 |
|------|------|------|----------|
| Python | 3.11+ | 3.11 | ✅ 异步支持完善，类型提示成熟 |
| Web 框架 | FastAPI | 0.110+ | ✅ 原生异步、自动 OpenAPI 文档、与 SSE 兼容 |
| ASGI 服务器 | uvicorn | 0.27+ | ✅ FastAPI 标准搭配，本地开发足够 |
| ORM | SQLAlchemy 2.0 | 2.0+ | ✅ 异步支持、成熟稳定、社区资源丰富 |
| 数据库驱动 | asyncmy | 最新 | ✅ MariaDB 异步驱动，与 SQLAlchemy 2.0 异步配合 |
| 文档解析 | PyPDF2 / python-docx / markdown / chardet | - | ✅ 按类型选择，依赖轻量 |
| 文本切分 | 自实现递归切分 | - | ⚠️ 需自实现约 100 行，但避免引入 langchain |

**评审结论**：后端技术栈合理。FastAPI + SQLAlchemy 2.0 异步 + asyncmy 是 MariaDB 异步访问的成熟组合。不引入 langchain 控制了依赖复杂度，文本切分自实现工作量可控。

### 3.2 前端技术栈

| 组件 | 选型 | 版本 | 评审意见 |
|------|------|------|----------|
| 框架 | Vue3 + Vite | Vue 3.4 / Vite 5 | ✅ 主流、上手快、文档中文友好 |
| UI 组件 | Element Plus | 2.6+ | ✅ 上传/表格/对话框组件齐全，适配中文场景 |
| 状态管理 | Pinia | 2.1+ | ✅ Vue3 官方推荐，API 简洁 |
| 路由 | Vue Router | 4.3+ | ✅ 官方路由方案 |
| HTTP 客户端 | axios | 1.6+ | ✅ 成熟、拦截器机制完善 |
| 流式接收 | fetch + ReadableStream | 原生 | ✅ 灵活支持 POST body，优于 EventSource |

**评审结论**：前端技术栈合理。Vue3 + Element Plus 组合对初级开发者友好，社区资源丰富。fetch streaming 虽需手动解析 SSE（约 50 行），但比 EventSource 灵活，支持 POST 请求体。

### 3.3 数据与 AI 层

| 组件 | 选型 | 版本 | 评审意见 |
|------|------|------|----------|
| 业务数据库 | MariaDB | 10.11+ | ✅ 本地安装，符合约束 C2 |
| 向量数据库 | Chroma | 0.5+ | ✅ 嵌入式持久化，无 Docker，符合约束 C1 |
| Embedding（默认） | OpenAI text-embedding-3-small | - | ✅ 1536 维，配置简单 |
| Embedding（可选） | BAAI/bge-m3 | - | ✅ 1024 维，中文优秀（DEC-012） |
| LLM | OpenAI gpt-4o-mini | - | ✅ 性价比高，支持 base_url 兼容端点 |

**评审结论**：数据与 AI 层选型合理。MariaDB 本地安装满足约束，Chroma 嵌入式模式无需独立服务。双 Embedding 方案通过 Provider 抽象层实现（DEC-008），LLM 通过 base_url 支持兼容端点（DEC-009）。

### 3.4 约束兼容性检查

| 约束 | 内容 | 兼容性 |
|------|------|--------|
| C1 | 全项目禁用 Docker | ✅ MariaDB 本地安装、Chroma 嵌入式、Python/Node 本地运行 |
| C2 | MariaDB 本地安装 | ✅ DEC-005 明确，asyncmy 驱动支持 |
| C3 | 仅本地 localhost 运行 | ✅ uvicorn 绑定 127.0.0.1 |
| C5 | 中文文档英文代码命名 | ✅ 技术栈支持中文注释 |
| C6 | 文档统一存放 docs 目录 | ✅ 所有技术文档已规划存放 docs |

---

## 4. 关键设计决策评审

### 4.1 Embedding Provider 抽象层（DEC-008）

**设计评估**：

```python
class EmbeddingProvider(ABC):
    async def embed(self, texts: List[str]) -> List[List[float]]: ...
    @property
    def dimension(self) -> int: ...
    @property
    def name(self) -> str: ...
```

**优点**：
- 抽象层接口简洁，仅 3 个成员（embed、dimension、name）
- `dimension` 属性让系统感知向量维度，避免 Chroma 维度冲突
- `name` 属性用于 collection 命名（如 `kb_openai_1536`），隔离不同 provider 数据
- 工厂函数 `get_embedding_provider()` 配置切换简单

**风险点**：
- 切换 provider 需重建向量索引（已在决策中说明）
- 增加约 150 行抽象代码（可接受）

**评审结论**：设计合理，通过。

### 4.2 LLM Provider 抽象层（DEC-009）

**设计评估**：

```python
class LLMProvider(ABC):
    async def chat_completion(
        self, messages: List[Message], stream: bool = False, **kwargs
    ) -> Union[ChatResponse, AsyncIterator[ChatChunk]]: ...
```

**优点**：
- 利用 openai SDK 原生 `base_url` 参数支持兼容端点，无需额外开发
- 抽象层为后续支持非 OpenAI 协议模型（如 Anthropic）留接口
- `stream` 参数统一支持流式与非流式

**风险点**：
- 抽象层复用 openai SDK，若未来需支持非 OpenAI 协议需扩展（V2 再考虑）
- 增加约 100 行抽象代码（可接受）

**评审结论**：设计合理，通过。复用 openai SDK 是务实选择。

### 4.3 SSE 流式输出方案（DEC-010）

**设计评估**：

| 方面 | 方案 | 评审意见 |
|------|------|----------|
| 后端 | FastAPI StreamingResponse + media_type=text/event-stream | ✅ 原生支持 |
| 事件格式 | 自定义 token/references/done/error 四类事件 | ✅ 区分清晰 |
| 前端 | fetch + ReadableStream 手动解析 SSE | ✅ 支持 POST body |
| 引用传递 | references 事件先于 token 发送 | ✅ 前端可先渲染引用框架 |

**优点**：
- FastAPI 原生支持 StreamingResponse，无需额外依赖
- 自定义事件格式让前端渲染逻辑清晰
- 引用先于 token 发送，用户体验好

**风险点**：
- 前端手动解析 SSE 增加约 50 行代码（可接受）
- 需联调验证流式稳定性（Phase 4 测试覆盖）

**评审结论**：方案合理，通过。EventSource 不支持 POST body 是正确放弃理由。

### 4.4 多轮上下文截断策略（DEC-011）

**设计评估**：

```
[系统提示 ~200 token]
[检索上下文 top_k=5 × 500字符 ~2000 token]
[历史对话 最近4轮8条消息 ~1500 token]
[当前问题 + 输出预留 ~1500 token]
总计 ~6000 token（gpt-4o-mini 上下文 128K）
```

**优点**：
- 按轮数截断（而非字符），保证对话完整性
- 每轮重新检索，答案基于最新问题相关内容
- Token 预算远低于模型上限，安全裕度大
- 会话级隔离，不同会话独立

**风险点**：
- 超过 4 轮的早期对话不进入上下文（可接受，MVP 范围）
- 长回答可能超出输出预留（通过 max_tokens 控制）

**评审结论**：策略合理，通过。4 轮覆盖大多数追问场景。

### 4.5 本地 Embedding 模型选型（DEC-012）

**评估**：

| 模型 | 维度 | 体积 | 中文表现 | 多语言 | 维护 | 评审 |
|------|------|------|----------|--------|------|------|
| bge-m3 | 1024 | 2.3GB | 优秀 | 优秀 | 活跃 | ✅ 选择 |
| m3e-large | 1024 | 较小 | 优秀 | 弱 | 一般 | 放弃 |
| bge-large-zh | 1024 | 较小 | 优秀 | 仅中文 | 活跃 | 放弃 |

**评审结论**：bge-m3 多语言能力强、MTEB 中文榜表现优秀、智源持续维护，选型合理。体积 2.3GB 需文档说明下载步骤（风险 R3）。

---

## 5. 技术债务评估（DEC-013）

### 5.1 债务清单

| # | 债务类型 | 严重程度 | 影响范围 | 计划偿还 | 评审意见 |
|---|----------|----------|----------|----------|----------|
| 1 | 前端组件测试较薄 | Medium | 前端 | V2 | ✅ 后端覆盖率 ≥ 80% 已保证 |
| 2 | 不做 Rerank | Low | RAG 检索质量 | V2 | ✅ 检索质量可接受 |
| 3 | 不做全文搜索 | Low | 检索能力 | V2 | ✅ 向量检索满足核心需求 |
| 4 | 配置项部分硬编码默认值 | Low | 全局 | V2 | ✅ 关键配置已走 .env |
| 5 | 不做日志集中收集 | Low | 运维 | V2 | ✅ 本地日志文件足够 |
| 6 | 错误码体系简化 | Low | API | V2 | ✅ HTTP 状态码 + 消息可用 |
| 7 | Chroma 无自动备份 | Medium | 数据安全 | V1.5 | ✅ 文档说明手动备份 |

### 5.2 债务评审结论

- **无 Critical 级别债务**：安全、数据丢失等关键问题 V1 必须解决
- **Medium 级别债务 2 项**：前端测试（V2 偿还）、Chroma 备份（V1.5 偿还）
- **Low 级别债务 5 项**：均为 MVP 合理妥协，V2 偿还
- 每项债务有明确偿还计划，债务可控

**评审结论**：技术债务基线合理，通过。

---

## 6. 风险评估

### 6.1 技术选型相关风险

| 风险编号 | 风险描述 | 可能性 | 影响 | 缓解措施 | 评审意见 |
|----------|----------|--------|------|----------|----------|
| R1 | 多轮上下文复杂度超预期 | 中 | 中 | DEC-011 截断策略明确，4 轮限制 | ✅ 已缓解 |
| R2 | Embedding 抽象层复杂度 | 中 | 中 | DEC-008 接口简洁，仅 3 成员 | ✅ 已缓解 |
| R3 | bge-m3 模型下载慢（2.3GB） | 中 | 低 | 文档说明下载步骤与缓存 | ✅ 已缓解 |
| R5 | OpenAI API 费用或网络问题 | 中 | 高 | DEC-009 base_url 支持兼容端点 | ✅ 已缓解 |
| R7 | SSE 流式输出联调复杂 | 中 | 中 | DEC-010 方案明确，Phase 4 联调 | ✅ 已缓解 |

### 6.2 新增风险识别

| 风险编号 | 风险描述 | 可能性 | 影响 | 缓解措施 |
|----------|----------|--------|------|----------|
| R11 | 文本切分自实现质量不稳定 | 低 | 中 | 参考 langchain RecursiveCharacterTextSplitter 逻辑实现，Phase 4 测试验证 |
| R12 | Chroma 嵌入式模式并发性能 | 低 | 低 | MVP 并发 1-2，嵌入式足够 |
| R13 | 切换 Embedding provider 后索引重建 | 中 | 低 | collection 命名隔离，文档说明重建步骤 |

**评审结论**：风险整体可控，所有 High 影响风险（R5）已有缓解措施。

---

## 7. 改进建议

| 优先级 | 建议 | 预期收益 | 实施成本 | 实施阶段 |
|--------|------|----------|----------|----------|
| P1 | 架构师在架构文档中明确 Provider 抽象层 UML 类图 | 提升开发可执行性 | 0.5h | Phase 1 |
| P1 | 架构师在架构文档中绘制 SSE 时序图 | 提升联调效率 | 0.5h | Phase 1 |
| P2 | 后端工程师搭建脚手架时预置 .env.example | 配置管理规范化 | 0.5h | Phase 2 |
| P2 | AI 工程师编写 RAG 原理说明文档 | 初级开发者可理解 | 1h | Phase 3 |
| P3 | 运维工程师在部署文档中说明 bge-m3 下载步骤 | 降低环境搭建门槛 | 0.5h | Phase 5 |

---

## 8. 后续行动

### 8.1 立即行动

1. **请求 Human Developer 审批**：提交 DEC-007~013 共 7 项技术决策供 Human Developer 审批（HITL 门禁）
2. **编写 Tech Lead → 产品经理交接文档**：将技术选型结论传递给产品经理，激活 Phase 1

### 8.2 审批通过后

1. **激活产品经理**（TASK-003）：编写 PRD，技术选型决策作为输入
2. **激活 UI/UX 设计师**（TASK-004）：PRD 完成后启动
3. **激活系统架构师**（TASK-005）：PRD + 设计系统完成后启动，架构师需在架构文档中细化 Provider 抽象层 UML、SSE 时序图、模块划分

### 8.3 需要 Human Developer 关注的决策

| 决策编号 | 关注点 |
|----------|--------|
| DEC-007 | 技术栈最终确认，是否同意不引入 langchain |
| DEC-012 | bge-m3 模型体积 2.3GB，是否接受首次下载成本 |
| DEC-013 | 7 项技术债务基线，是否认可偿还计划 |

### 8.4 下一次评审

| 评审项 | 评审时机 | 评审人 |
|--------|----------|--------|
| 架构评审（G2） | TASK-005 架构文档完成后 | Tech Lead |
| 代码评审（G3） | TASK-007/008/009 开发完成后 | Code Reviewer + Tech Lead |
| 安全评审（G5） | TASK-011 安全审计完成后 | Security Engineer + Tech Lead |

---

## 9. 评审检查清单

- [x] 技术栈已最终确认（DEC-007）
- [x] Embedding Provider 抽象方案已明确（DEC-008）
- [x] LLM Provider 抽象方案已明确（DEC-009）
- [x] SSE 流式输出方案已明确（DEC-010）
- [x] 多轮上下文截断策略已明确（DEC-011）
- [x] 本地 Embedding 模型已选定（DEC-012）
- [x] 技术债务基线已评估（DEC-013）
- [x] 约束兼容性已检查（C1~C6）
- [x] 风险已评估并更新（R1~R13）
- [x] 改进建议已列出
- [x] 评审报告完整，无占位符
- [x] 决策已记录在 Decision Log
- [x] Todo 状态已更新（TASK-002 标记 COMPLETED）
- [x] Handoff 文档已编写（HO-20260712-002）
- [ ] Human Developer 审批（待执行）

---

## 附录

### A. 评审输入文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目规划 | `docs/project-plan.md` | 项目范围、风险、约束 |
| 决策日志 | `docs/decision-log.md` | DEC-001~006（评审前） |
| 任务清单 | `docs/todo.md` | Phase 0~5 任务定义 |
| PM 交接 | `docs/handoffs/handoff-pm-to-techlead.md` | PM→Tech Lead 交接 |

### B. 评审输出文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 技术评审报告 | `docs/tech-review-report.md` | 本文件 |
| 决策日志（更新） | `docs/decision-log.md` | 追加 DEC-007~013 |
| Tech Lead 交接 | `docs/handoffs/handoff-techlead-to-pm.md` | Tech Lead→产品经理交接 |

### C. 变更历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-07-12 | 初始版本，Phase 0 技术选型评审 | Tech Lead |

---

**本报告是 Phase 0 技术选型评审的唯一真实来源。评审结论需经 Human Developer 审批后生效。**
