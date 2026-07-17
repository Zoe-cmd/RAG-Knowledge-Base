# Handoff: UI/UX 设计师 → 系统架构师（Phase 1 内部）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-004 |
| 交接日期 | 2026-07-12 |
| 交接方 | UI/UX Designer（UI/UX 设计师） |
| 接收方 | Solution Architect（系统架构师） |
| 交接阶段 | Phase 1 内部：UI/UX 设计 → 系统架构 |
| 交接状态 | Ready |

---

## 交接摘要

UI/UX 设计师已完成 TASK-004 全部设计工作，产出 4 份设计文档：设计系统（色彩/字体/间距/组件/图标/动效/无障碍）、用户流程（5 个核心流程含主流程与异常流程）、线框图（10 个页面/状态线框）、高保真原型说明（视觉规格/动效细节/前端实现建议）。

设计采用左右分栏布局（左侧会话+文档列表，右侧对话区），基于 Element Plus 组件库，主色科技蓝 #409EFF，简洁现代风格。核心亮点为流式回答逐字显示 + 引用来源卡片先于回答展示。所有设计在 DEC-001~013 技术决策约束内，与 PRD 20 个用户故事完全覆盖。

系统架构师可基于 PRD + 设计系统启动 TASK-005 架构设计，重点细化 Provider 抽象层 UML、SSE 时序图、模块划分与文本切分算法。

---

## 交付物

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 设计系统 | 文档 | `docs/design-system.md` | 完成 |
| 用户流程 | 文档 | `docs/user-flows.md` | 完成 |
| 线框图 | 文档 | `docs/wireframes.md` | 完成 |
| 高保真原型说明 | 文档 | `docs/mockups.md` | 完成 |
| PRD 文档 | 文档 | `docs/prd.md` | 已审批 |
| 决策日志 | 文档 | `docs/decision-log.md` | 13 项决策 |

---

## 关键设计决策

| 设计决策 | 说明 | 对架构的影响 |
|----------|------|--------------|
| 左右分栏布局 | 左侧 280px 会话+文档，右侧对话区 | 前端路由为单页面，无多页跳转 |
| Element Plus 组件库 | 使用 el-upload/el-table/el-dialog 等 | 前端依赖 Element Plus 2.6+ |
| 流式光标自定义 | 非 Element Plus 原生 | 前端需实现 StreamingCursor 组件 |
| 引用来源自定义 | 非 Element Plus 原生 | 前端需实现 ReferenceCard 组件 |
| 消息气泡自定义 | 非 Element Plus 原生 | 前端需实现 MessageBubble 组件 |
| 桌面端优先 | 最小 1024px，不做移动端 | 无需移动端适配架构 |
| 骨架屏加载 | el-skeleton | API 需支持快速首屏响应 |

---

## 对架构师的重点建议

### 1. Provider 抽象层 UML（DEC-008/009）

架构师需在架构文档中绘制完整的 UML 类图，明确：
- EmbeddingProvider 抽象类与 OpenAIEmbeddingProvider、BGEEmbeddingProvider 的继承关系
- LLMProvider 抽象类与 OpenAILLMProvider 的继承关系
- 工厂函数 get_embedding_provider() / get_llm_provider() 的调用方式
- 配置如何注入（.env → Settings → Provider）

### 2. SSE 时序图（DEC-010）

架构师需绘制详细的 SSE 时序图，覆盖：
- 前端 fetch → 后端 StreamingResponse → LLM stream 的完整链路
- event: references / token / done / error 的发送时机
- 停止生成时前端 abort → 后端检测断开 → 停止 LLM stream 的流程
- 异常场景（超时、网络断开、LLM 错误）的处理

### 3. 模块划分

基于设计文档，建议后端模块划分：

```
backend/
├── api/                    # API 路由层
│   ├── documents.py        # 文档管理 API
│   ├── chat.py             # 聊天 API（含 SSE）
│   └── sessions.py         # 会话管理 API
├── services/               # 业务逻辑层
│   ├── document_service.py # 文档解析+切分
│   ├── embedding_service.py# Embedding 调用
│   ├── rag_service.py      # RAG 检索+上下文组装
│   └── chat_service.py     # 聊天管理
├── providers/              # Provider 抽象层
│   ├── embedding/
│   │   ├── base.py         # EmbeddingProvider 抽象
│   │   ├── openai_provider.py
│   │   ├── bge_provider.py
│   │   └── factory.py      # 工厂函数
│   └── llm/
│       ├── base.py         # LLMProvider 抽象
│       ├── openai_provider.py
│       └── factory.py
├── models/                 # 数据模型
│   ├── document.py
│   ├── session.py
│   └── message.py
├── parsers/                # 文档解析器
│   ├── pdf_parser.py
│   ├── docx_parser.py
│   ├── markdown_parser.py
│   └── txt_parser.py
├── chunkers/               # 文本切分
│   └── recursive_chunker.py
├── config/                 # 配置
│   └── settings.py
└── main.py                 # FastAPI 入口
```

### 4. 前端组件结构

基于高保真原型说明，前端组件结构建议见 `docs/mockups.md` 第 10.1 节。架构师需确认前端状态管理方案（Pinia stores：chat/document/session）。

### 5. 文本切分算法

架构师需设计递归字符切分算法（DEC-007 不引入 langchain）：
- 输入：纯文本
- 参数：chunk_size=500, overlap=50
- 逻辑：优先按段落分隔符切分 → 按句子切分 → 按字符切分
- Markdown：优先按标题边界切分
- 输出：List[str] chunks

### 6. SSE 事件格式

架构师需定义 SSE 事件格式规范：

```
event: references
data: [{"doc_name":"...", "chunk":"...", "source_path":"..."}]

event: token
data: {"content": "RAG"}

event: token
data: {"content": "是"}

event: done
data: {"elapsed_ms": 3200}

event: error
data: {"message": "回答生成超时", "code": "LLM_TIMEOUT"}
```

---

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| 无 Figma 文件 | Low | AI Agent 不产出 Figma | 前端基于线框图+高保真说明实现 |
| 移动端不适配 | Low | 本地 localhost 桌面端场景 | 架构无需考虑移动端 |
| 自定义组件较多 | Low | Element Plus 无消息气泡等 | 前端需自建 3 个组件 |

---

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 流式渲染前端实现复杂 | 中 | 中 | 参考 mockups.md 动效细节与组件建议 |
| 自定义组件开发量大 | 低 | 低 | 3 个组件（消息气泡/引用卡片/光标）代码量可控 |
| 响应式仅 2 断点 | 低 | 低 | 桌面端场景足够 |

---

## 假设说明

- **假设 1**：架构师基于 PRD + 设计系统设计架构，不修改功能需求与视觉设计。
- **假设 2**：前端组件结构建议（mockups.md 10.1）供架构师参考，架构师可调整。
- **假设 3**：Element Plus 组件能满足设计需求，无需额外 UI 库。
- **假设 4**：设计文档中的色值、尺寸、间距为最终值，开发时直接使用。

---

## 下一步建议

### 对系统架构师（TASK-005）

1. **阅读所有设计文档**：design-system.md、user-flows.md、wireframes.md、mockups.md
2. **阅读 PRD**：理解 4 大模块、20 个用户故事、验收标准
3. **阅读技术决策**：DEC-007~013，特别是 Provider 抽象层与 SSE 方案
4. **架构文档必含**：
   - 系统架构图（前后端+数据库+向量库+外部 API）
   - 模块划分（后端目录结构+前端组件结构）
   - Provider 抽象层 UML 类图
   - SSE 时序图（含正常+异常+停止）
   - 多轮上下文组装流程图
   - 文本切分算法设计
   - 数据流图（上传流+问答流）
   - 非功能需求实现方案
5. **追加架构决策**：如有新的架构决策，追加到 decision-log.md
6. **交付物**：`docs/architecture.md`

### 对后续角色（预告）

| 角色 | 任务 | 启动时机 | 关键输入 |
|------|------|----------|----------|
| 数据库工程师 | TASK-006 | 架构完成后 | PRD 数据需求 + 架构文档 |
| 后端工程师 | TASK-007 | 数据库设计完成后 | 架构文档 + API 规范 + 数据库 Schema |

---

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | Solution Architect |
| 确认状态 | Pending |

### 接收方验证清单

- [ ] 已阅读 4 份设计文档
- [ ] 已理解左右分栏布局与组件结构
- [ ] 已理解流式回答与引用来源的设计要求
- [ ] 已理解 Provider 抽象层设计方向（DEC-008/009）
- [ ] 已理解 SSE 方案（DEC-010）
- [ ] 已确认模块划分建议的可行性
- [ ] 已确认前端组件结构的合理性

---

## 交接方验证清单

- [x] 4 份设计文档已生成
- [x] 设计覆盖所有 PRD 功能（20 个用户故事）
- [x] 设计系统完整（色彩/字体/间距/组件/图标/动效/无障碍）
- [x] 用户流程完整（5 个流程含异常）
- [x] 线框图覆盖所有页面与状态
- [x] 高保真原型含视觉规格与实现建议
- [x] 交互状态矩阵完整
- [x] 无占位符/省略号
- [x] Todo 已更新（TASK-004 COMPLETED）
- [x] 交接文档无遗漏

---

**交接完成。请系统架构师阅读所有交付物后开始架构设计。**

**特别注意**：Provider 抽象层 UML、SSE 时序图、文本切分算法是架构文档的核心内容，直接影响后端开发（TASK-007）与 AI 功能开发（TASK-009）。
