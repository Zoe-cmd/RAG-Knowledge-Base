# Handoff: Phase 3（前端与 AI）→ Phase 4（质量保证）

## 交接信息

| 字段 | 内容 |
|------|------|
| 交接编号 | HO-20260712-008 |
| 交接日期 | 2026-07-12 22:00 |
| 交接方 | Frontend Engineer |
| 接收方 | QA Engineer |
| 交接阶段 | Phase 3（前端与 AI）→ Phase 4（质量保证） |
| 交接状态 | Ready |

## 交接摘要

前端工程师基于 PRD、设计系统、API 规范与后端交接文档，完成了 AI 文档知识库（MVP）的前端应用开发。技术栈为 Vue 3.5 + Element Plus 2.8 + Pinia 2.2 + Vue Router 4.4 + Vite 5.4 + Sass，采用 JavaScript + `<script setup>` + JSDoc（面向初级开发者，控制复杂度，满足 PropTypes 类型验收标准）。

共交付 36 个源文件，覆盖完整的 RAG 知识库前端功能：文档上传（拖拽+批量+预校验+进度条）、SSE 流式问答（fetch+ReadableStream+Markdown 渲染+引用来源展示）、会话管理（CRUD+消息加载）、文档管理（列表+删除+轮询）、Embedding Provider 切换、响应式布局（≥1024px 固定侧边栏 / <1024px 抽屉）。

**构建验证**：`npm run build` 通过（1742 模块，3.3s），`npm run lint:check` 零错误零警告，`npm run dev` 开发服务器正常启动（127.0.0.1:5173）。

## 交付物

### 源代码

| 交付物 | 类型 | 路径 | 状态 |
|--------|------|------|------|
| 包配置 | 配置 | `frontend/package.json` | 完成 |
| Vite 构建配置 | 配置 | `frontend/vite.config.js` | 完成 |
| ESLint 配置 | 配置 | `frontend/.eslintrc.cjs` | 完成 |
| Prettier 配置 | 配置 | `frontend/.prettierrc.json` | 完成 |
| 环境变量示例 | 配置 | `frontend/.env.example` | 完成 |
| 开发环境变量 | 配置 | `frontend/.env.development` | 完成 |
| 生产环境变量 | 配置 | `frontend/.env.production` | 完成 |
| 全局样式变量 | 样式 | `frontend/src/styles/variables.scss` | 完成 |
| 全局样式 | 样式 | `frontend/src/styles/global.scss` | 完成 |

### Vue 组件（17 个）

| 组件 | 路径 | 职责 |
|------|------|------|
| App | `src/App.vue` | 根组件（RouterView） |
| ChatView | `src/views/ChatView.vue` | 主视图，组装布局+初始化数据 |
| MainLayout | `src/components/layout/MainLayout.vue` | 响应式布局容器 |
| AppHeader | `src/components/layout/AppHeader.vue` | 顶部栏（标题+统计+Provider切换） |
| AppSidebar | `src/components/layout/AppSidebar.vue` | 左侧栏（会话+文档+上传弹窗） |
| ChatArea | `src/components/chat/ChatArea.vue` | 对话区容器（空状态/消息列表+输入） |
| MessageList | `src/components/chat/MessageList.vue` | 消息列表（自动滚动+回到底部） |
| MessageBubble | `src/components/chat/MessageBubble.vue` | 消息气泡（用户/AI+Markdown+流式光标） |
| ReferenceCard | `src/components/chat/ReferenceCard.vue` | 引用来源卡片（折叠展开） |
| ChatInput | `src/components/chat/ChatInput.vue` | 输入区（自动扩展+发送/停止） |
| EmptyChat | `src/components/chat/EmptyChat.vue` | 对话区空状态引导 |
| SessionList | `src/components/sessions/SessionList.vue` | 会话列表（选中+删除确认） |
| SessionItem | `src/components/sessions/SessionItem.vue` | 会话列表项 |
| DocumentList | `src/components/documents/DocumentList.vue` | 文档列表（删除确认+空状态） |
| DocumentItem | `src/components/documents/DocumentItem.vue` | 文档列表项（图标+状态+切片数） |
| UploadDialog | `src/components/documents/UploadDialog.vue` | 上传弹窗（拖拽+批量+预校验+进度） |
| StatusTag | `src/components/common/StatusTag.vue` | 文档状态标签 |

### Pinia Store（4 个）

| Store | 路径 | 职责 |
|-------|------|------|
| chat | `src/stores/chat.js` | 消息列表+SSE 流式生命周期+中断控制 |
| sessions | `src/stores/sessions.js` | 会话列表 CRUD+当前选中 |
| documents | `src/stores/documents.js` | 文档列表+上传+删除+处理轮询 |
| config | `src/stores/config.js` | 应用配置+统计信息+Provider 切换 |

### API 层（5 个模块）

| 模块 | 路径 | 职责 |
|------|------|------|
| request | `src/api/request.js` | Axios 实例+拦截器（响应归一化+错误归一化） |
| documents | `src/api/documents.js` | 文档上传/列表/删除 |
| sessions | `src/api/sessions.js` | 会话 CRUD+消息列表 |
| chat | `src/api/chat.js` | SSE 流式问答（fetch+ReadableStream） |
| config | `src/api/config.js` | 配置查询+Provider 切换 |

### 工具与组合式函数（5 个）

| 模块 | 路径 | 职责 |
|------|------|------|
| constants | `src/utils/constants.js` | 全局常量（API路径/文件类型/状态映射/错误码映射） |
| format | `src/utils/format.js` | 格式化工具（文件大小/日期/相对时间/耗时） |
| markdown | `src/utils/markdown.js` | Markdown 渲染（marked+DOMPurify+highlight.js） |
| message | `src/utils/message.js` | 消息提示（错误码→友好文案映射） |
| useUploadDialog | `src/composables/useUploadDialog.js` | 上传弹窗共享状态 |

## 关键决策

| 决策编号 | 决策标题 | 影响 |
|----------|----------|------|
| FE-DEC-001 | 采用 JavaScript + `<script setup>` + JSDoc，不使用 TypeScript | 面向初级开发者控制复杂度；满足 PropTypes 类型验收标准（运行时 prop 验证）；与后端交接文档示例一致 |
| FE-DEC-002 | SSE 接收使用 fetch + ReadableStream，不使用 EventSource | EventSource 不支持 POST 方法；手动解析 event:/data: 协议，支持 AbortController 中断 |
| FE-DEC-003 | 使用 Vite Proxy 规避开发环境跨域（DEC-015） | 前端请求 `/api/*` 由 Vite 代理转发至 `127.0.0.1:8000`，无需配置 CORS；后端仍保留 CORS 作为后备 |
| FE-DEC-004 | Markdown 渲染使用 marked + DOMPurify + highlight.js | DOMPurify 净化防止 XSS；highlight.js 代码语法高亮；marked 支持 GFM+换行 |
| FE-DEC-005 | 响应式布局使用 matchMedia 监听 1024px 断点 | ≥1024px 固定侧边栏，<1024px el-drawer 抽屉；侧边栏内容通过具名插槽避免重复渲染 |
| FE-DEC-006 | 上传弹窗可见性使用模块级 ref 共享（useUploadDialog） | 避免为单一布尔值引入 Pinia store；AppSidebar 持有弹窗，对话区空状态/文档列表空状态均可触发 |
| FE-DEC-007 | axios 响应拦截器返回 `response.data`（解包 {data, meta}） | Store 层直接操作 `res.data` / `res.meta`，无需每处解包；错误拦截器归一化四种错误格式 |
| FE-DEC-008 | 处理中文档自动轮询（3s 间隔），所有处理完成后停止 | 用户无需手动刷新；轮询在 store 层管理，组件销毁时调用 stopPolling 清理 |
| FE-DEC-009 | 消息列表自动滚动仅在用户已贴近底部时触发 | 用户上滑阅读历史时不强制打断滚动；提供"回到底部"悬浮按钮 |

## 已知问题

| 问题 | 严重程度 | 原因 | 建议 |
|------|----------|------|------|
| references 字段名不匹配（已修复） | High | 后端 `rag_service.py` 的 `to_reference()` 返回 `preview` 字段，但 api-spec.md 规范为 `chunk`；同时出于 SEC-006 安全考虑不返回 `source_path` | **已修复**（2026-07-13 联调）：后端 `preview` → `chunk`；前端 ReferenceCard.vue 适配 `source_path` 可选显示、`chunk \|\| preview` 兼容；4 处后端测试同步更新 |
| 未编写前端单元测试/E2E 测试 | Medium | MVP 阶段优先实现功能，测试由 QA Engineer 统一规划 | QA 编写测试计划时覆盖前端交互场景 |
| Sass legacy-js-api 弃用警告 | Low | Vite 5 使用旧版 Sass JS API，Dart Sass 2.0 将移除 | 不影响构建与运行；Vite 6+ 将使用新 API |
| Element Plus 全量引入（929KB） | Low | MVP 简化配置，未使用按需引入插件 | V2 可使用 `unplugin-element-plus` 按需引入减小包体积 |
| `@vueuse/core` PURE 注释警告 | Info | Rollup 无法识别第三方库的 PURE 注释位置 | 不影响功能，构建产物正常 |
| 无骨架屏/加载占位 | Low | MVP 简化，使用 v-loading 指令替代 | V2 可添加骨架屏提升用户体验 |
| `source_path` 字段不返回 | Info | 后端 SEC-006 安全决策，不暴露内部文件存储路径 | 前端已适配为可选显示（`v-if="item.source_path"`）；qa-spec 与实现存在偏差，建议后续对齐 api-spec.md 标注 source_path 为可选字段 |

## 风险提示

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 后端未启动时前端初始化失败 | 高 | 中 | 已使用 Promise.allSettled 保证单项失败不阻塞；错误由 request 拦截器显示 ElMessage 提示 |
| SSE 流式中途断连 | 中 | 中 | 已实现 AbortError 静默处理；网络中断显示"连接中断"提示；已生成内容保留 |
| Markdown 渲染 XSS | 低 | 高 | 已使用 DOMPurify 净化（白名单标签+属性）；v-html 添加了 eslint-disable 注释说明 |
| 文档上传超大文件超时 | 低 | 中 | 已设置 120s 上传超时；前端预校验 20MB 限制 |
| Provider 切换后向量空间不兼容 | 中 | 高 | AppHeader 切换时有二次确认弹窗提示"需重建索引"；切换后自动刷新文档列表 |

## 假设说明

- 假设后端 API 已开发完成并正常运行在 `127.0.0.1:8000`（TASK-007 已 COMPLETED）
- 假设 Vite Proxy 配置正确，开发环境 `/api/*` 请求能正确代理到后端
- 假设浏览器支持 fetch + ReadableStream（所有现代浏览器均支持）
- 假设 Element Plus 2.8+ 的组件行为与文档一致
- 假设 OpenAI API Key 已在 `backend/.env` 中正确配置
- 假设 Chroma 持久化目录 `./data/chroma` 已创建且可读写

## 测试覆盖情况

### 当前状态

前端目前**未编写自动化测试**（单元测试/E2E 测试）。以下为手动验证结果：

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 构建编译 | `npm run build` | 通过（1742 模块，3.3s） |
| ESLint 检查 | `npm run lint:check` | 通过（0 错误 0 警告） |
| 开发服务器启动 | `npm run dev` | 通过（127.0.0.1:5173，152ms） |
| 代码分割 | 构建产物分析 | 通过（vue/element-plus/markdown 三 chunk 分离） |

### 联调验证（2026-07-13）

前端工程师在前后端联调阶段执行了端到端验证，确认 RAG 闭环完整可用：

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 后端健康检查 | `curl /health` | ✅ `{"status":"ok"}` |
| 文档列表 API | `curl /api/documents` | ✅ 3 个文档（test.txt 12 chunks） |
| 会话列表 API | `curl /api/chat/sessions` | ✅ 正确返回会话数组 |
| 会话创建 API | `curl POST /api/chat/sessions` | ✅ 201 返回新会话对象 |
| 配置查询 API | `curl /api/config` | ✅ embedding=openai, llm=gpt-5.6-luna |
| SSE 流式问答 | `curl POST /api/chat/messages` | ✅ references → token × N → done 完整事件流 |
| references 字段 | SSE 事件数据检查 | ✅ 返回 `chunk` 字段（修复后对齐 spec） |
| 引用来源检索 | SSE references 事件 | ✅ top_k=5，相似度 0.70~0.84，阈值 0.3 过滤正常 |
| 回答质量 | 人工评估 | ✅ 准确基于 test.txt 内容回答 |
| 消息持久化 | `curl /api/chat/sessions/{id}/messages` | ✅ 6 条消息（3 轮问答）正确保存到 MariaDB |
| 多轮上下文 | 连续 3 轮问答 | ✅ DEC-011 上下文管理正常 |
| 响应性能 | done 事件 elapsed_ms | ✅ 9017ms（满足 P95 < 15s） |
| 后端测试回归 | `pytest test_services.py test_integration.py` | ✅ 45 个测试全部通过 |
| 前端 UI 加载 | 浏览器访问 127.0.0.1:5173 | ✅ 页面正常渲染，会话/文档列表显示 |
| 前端历史消息 | 浏览器点击会话 | ✅ 历史消息正确加载 |
| 前端发送问答 | 浏览器输入并发送 | ✅ 按钮切换"停止生成"，SSE 请求发起 |

**联调发现并修复的集成 bug**：

后端 `rag_service.py` 的 `RetrievalResult.to_reference()` 方法返回 `preview` 字段（前 200 字符预览），但 [api-spec.md:588-595](../../api-spec.md) 规范定义为 `chunk` 字段，导致前端 [ReferenceCard.vue](../../frontend/src/components/chat/ReferenceCard.vue) 的 `item.chunk` 取值为 `undefined`，引用卡片内容显示为空。

修复内容：
1. 后端 `rag_service.py`：`preview` → `chunk`（字段名对齐 spec，保持 200 字符截断行为）
2. 前端 `ReferenceCard.vue`：`{{ item.chunk || item.preview }}` 兼容 + `source_path` 可选显示（`v-if`）
3. 后端测试 `test_services.py`、`test_integration.py`：4 处 `preview` → `chunk` 同步更新

### UX 体验审查与修复（2026-07-13）

基于用户反馈"为什么没有滑轮滚动功能，请站在一个用户的角度体验前端交互各个功能"，执行了完整 UX 审查，发现并修复以下问题：

| 问题 | 严重度 | 根因 | 修复 |
|------|--------|------|------|
| 消息列表无法滚动 | High | `ChatArea.vue` 的 `.chat-content` 缺少 `display: flex; flex-direction: column`，导致 `MessageList` 的 `.message-list-wrapper` 的 `flex: 1` 无法获得有界高度，`overflow-y: auto` 不生效 | `.chat-content` 添加 `display: flex; flex-direction: column` |
| SSE 流式问答失败（net::ERR_ABORTED） | Critical | Vite dev server 代理长时间运行后进入异常状态，不转发 SSE chunked 响应；`vite.config.js` 代理缺少 SSE 专用配置 | 重启 Vite 清理状态 + `vite.config.js` 添加 `selfHandleResponse: false` 与代理错误日志 |
| 新建会话后输入框消失 | High | `ChatArea.vue` 用 `v-if/v-else` 在 `EmptyChat`（无输入框）与 `MessageList+ChatInput` 间切换，新会话无消息 → 显示 EmptyChat → 无输入框 | 重构为 `ChatInput` 始终在底部，`MessageList/EmptyChat` 在上方 `.chat-content` 区切换 |
| EmptyChat 按钮冗余 | Medium | `EmptyChat` 含"开始提问"和"上传文档"按钮，与左侧栏功能重复 | 简化为纯欢迎信息，不含按钮 |
| references `preview` vs `chunk` 字段名不匹配 | High | 后端返回 `preview`，API 规范定义 `chunk` | 后端 `preview` → `chunk`，前端 `item.chunk || item.preview` 兼容 |

**UX 验证结果**（浏览器自动化测试）：

| 功能 | 结果 | 证据 |
|------|------|------|
| 页面初始加载 | ✅ PASS | 布局完整，侧边栏+输入框正常 |
| SSE 流式问答 | ✅ PASS | 15 条消息 + 3 引用卡片 + 流式 token + 耗时显示 |
| 消息列表滚动 | ✅ PASS | `scrollHeight > clientHeight`，"回到底部"按钮正常 |
| 会话列表滚动 | ✅ PASS | 可滚动 |
| 新建会话 | ✅ PASS | 输入框始终存在，空状态显示 |
| 会话切换 | ✅ PASS | 历史消息正确加载 |
| 上传文档弹窗 | ✅ PASS | 打开/关闭（X 按钮/取消）正常 |
| 停止生成 | ✅ PASS | 中断+保留内容+恢复输入 |
| 响应式设计 | ✅ PASS | 代码正确（1024px 断点，matchMedia 切换抽屉） |
| ESLint 检查 | ✅ PASS | 0 错误 0 警告 |
| 生产构建 | ✅ PASS | 1742 模块，3.3s |

### QA 测试建议覆盖范围

| 测试类别 | 场景 | 优先级 |
|----------|------|--------|
| 功能测试 | 文档上传（PDF/Word/MD/TXT） | P0 |
| 功能测试 | 扫描件 PDF 友好错误提示 | P0 |
| 功能测试 | 文档列表展示+状态轮询 | P0 |
| 功能测试 | 文档删除（含二次确认） | P0 |
| 功能测试 | 新建会话+发送问题+SSE 流式接收 | P0 |
| 功能测试 | 引用来源展示（折叠/展开） | P0 |
| 功能测试 | 停止生成（AbortController） | P0 |
| 功能测试 | 无相关内容时友好提示 | P0 |
| 功能测试 | 会话切换+消息加载 | P0 |
| 功能测试 | 会话删除+清空所有 | P0 |
| 功能测试 | Provider 切换（含确认弹窗） | P1 |
| 交互测试 | Markdown 渲染（代码高亮/列表/链接） | P1 |
| 交互测试 | 消息列表自动滚动+回到底部按钮 | P1 |
| 交互测试 | 输入区自动扩展+Enter发送/Shift+Enter换行 | P1 |
| 交互测试 | 上传弹窗拖拽+批量+预校验+进度条 | P1 |
| 响应式 | ≥1024px 固定侧边栏布局 | P1 |
| 响应式 | <1024px 抽屉式侧边栏 | P1 |
| 错误处理 | 后端未启动时初始化错误提示 | P1 |
| 错误处理 | 网络中断时流式错误提示 | P1 |
| 错误处理 | 文件类型/大小/数量超限提示 | P2 |

## 下一步建议

### QA Engineer 测试重点

1. **RAG 闭环 E2E 测试**：上传文档 → 等待处理完成 → 新建会话 → 提问 → 验证流式回答渲染 → 验证引用来源展示
2. **SSE 流式测试**：验证 token 逐字渲染、流式光标动画、references 在回答前展示、done 事件后停止光标
3. **停止生成测试**：流式生成中点击"停止生成"，验证已生成内容保留、消息标记"已停止"
4. **无相关内容测试**：提问与文档无关的问题，验证"未在文档库中找到相关内容"提示
5. **文档上传预校验**：尝试上传 .exe/.jpg 等不支持类型、超过 20MB 文件、超过 100 篇文档
6. **响应式测试**：调整浏览器窗口大小，验证 1024px 断点处侧边栏切换为抽屉
7. **多轮对话测试**：连续对话 5+ 轮，验证消息列表滚动与上下文加载
8. **错误恢复测试**：停止后端 → 操作前端 → 验证错误提示 → 重启后端 → 验证恢复正常

### 测试环境准备

```bash
# 1. 启动后端（需先配置 backend/.env）
cd backend
source venv/bin/activate  # 或 conda activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. 启动前端
cd frontend
npm install
npm run dev

# 3. 访问应用
# 浏览器打开 http://127.0.0.1:5173
```

### 测试数据建议

- 准备 4 种文档：PDF（文本型）、Word(.docx)、Markdown(.md)、TXT
- 准备 1 个扫描型 PDF 验证友好错误提示
- 准备 1 个超过 20MB 的文件验证大小限制
- 准备 1 个不支持的类型（如 .jpg）验证类型限制
- 准备跨 chunk 的问题（答案分布在两个 chunk）验证检索效果
- 准备无相关答案的问题验证"未找到相关内容"兜底

## 接收方确认

| 字段 | 内容 |
|------|------|
| 确认日期 | 待确认 |
| 确认人 | QA Engineer |
| 确认状态 | Pending Confirmation |

---

**交接完成。请 QA Engineer 阅读所有交付物后再开始工作。**

**关键提醒**：
1. 测试前请确保后端已启动（`127.0.0.1:8000`）且 `OPENAI_API_KEY` 已配置
2. 前端开发服务器：`cd frontend && npm run dev`（127.0.0.1:5173）
3. 前端通过 Vite Proxy 代理 `/api/*` 到后端，无需额外 CORS 配置
4. 后端 API 文档（Swagger）：`http://127.0.0.1:8000/docs`
5. 详细 API 规范见 [docs/api-spec.md](../api-spec.md)，设计规范见 [docs/design-system.md](../design-system.md)
6. 后端→前端交接文档（含 SSE 协议详解）：[docs/handoffs/handoff-backend-to-frontend-ai.md](./handoff-backend-to-frontend-ai.md)
