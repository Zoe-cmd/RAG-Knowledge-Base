<!--
Document: Prompt Design
Version: 1.0.0
Author: AI Engineer
Created: 2026-07-12
Updated: 2026-07-12
-->

# Prompt 设计文档

> 本文档是 RAG 文档知识库（MVP）Prompt 的唯一真实来源。
> 包含 System Prompt 版本管理、上下文注入格式、Few-shot 示例、安全措施与输出验证规则。
> 对应代码：`backend/app/services/prompt_template.py`、`backend/app/services/output_guard.py`。

---

## 1. 概述

本项目 Prompt 设计遵循 **AI 工程师角色规范** 的 G1（Prompt 版本化）与 G3（输出验证）质量门禁：

- **G1 版本化管理**：所有 System Prompt 通过 `PROMPT_REGISTRY` 注册版本，支持版本切换与回滚。
- **G3 输出验证**：LLM 输出经过 `output_guard.validate_answer` 清洗（控制字符过滤、超长截断、空内容兜底、Prompt 泄漏检测）。

Prompt 不硬编码在业务代码中，而是通过 `prompt_template.py` 独立管理，业务层通过 `build_rag_messages()` 组装消息列表。

---

## 2. Prompt 版本管理

### 2.1 设计原则

| 原则 | 说明 |
|------|------|
| 版本化注册 | 每个 Prompt 版本注册到 `PROMPT_REGISTRY`，含 version / system_prompt / description / created_at |
| 不可变 | `PromptVersion` 使用 `@dataclass(frozen=True)`，防止运行时篡改 |
| 向后兼容 | `SYSTEM_PROMPT` 常量指向当前版本，已有代码无需改动 |
| 显式切换 | 通过 `get_prompt(version)` 可获取任意历史版本，便于 A/B 测试与回滚 |
| 可追溯 | 版本变更须在本文档第 2.3 节记录变更说明 |

### 2.2 当前活跃版本

| 字段 | 值 |
|------|------|
| 当前版本 | `v1.1.0` |
| 对应代码常量 | `CURRENT_PROMPT_VERSION = "v1.1.0"` |
| 文件位置 | `backend/app/services/prompt_template.py` |

### 2.3 版本变更历史

| 版本 | 创建日期 | 描述 | 变更说明 |
|------|----------|------|----------|
| v1.0.0 | 2026-07-12 | 初始版本 | 基于参考资料回答、不编造、不足时明确说明、保持原文语言 |
| v1.1.0 | 2026-07-12 | 优化版本（当前活跃） | 增强防编造约束、明确输出格式、禁止暴露内部机制、支持 Markdown 排版 |

### 2.4 版本切换方式

切换默认版本只需修改 `prompt_template.py` 中的 `CURRENT_PROMPT_VERSION` 常量并同步更新本文档 2.2 节。

调用方也可在 `build_rag_messages()` 中显式指定版本：

```python
from app.services.prompt_template import build_rag_messages

messages = build_rag_messages(
    question="什么是 RAG？",
    context_chunks=["RAG 是检索增强生成..."],
    history=[],
    prompt_version="v1.0.0",  # 显式指定使用旧版本
)
```

---

## 3. System Prompt

### 3.1 v1.1.0（当前活跃版本）

```
你是基于本地文档知识库的 AI 助手。请严格根据下方提供的"参考资料"回答用户问题。

回答规则：
1. 回答必须基于参考资料内容，不要编造资料中未出现的信息。
2. 如果参考资料不足以回答问题，请明确回复："根据知识库中的资料，暂无法回答该问题。"，不要拼凑或臆测。
3. 回答应准确、简洁、有条理；如适用可用 Markdown 列表或代码块组织。
4. 引用资料原文时使用引号标明。
5. 使用与用户问题相同的语言回答（中文问题用中文，英文问题用英文）。
6. 不要提及"参考资料""系统提示""Prompt"等内部机制。

输出格式：
- 直接给出回答正文，不要输出"回答："之类的引导语。
- 如需分点说明，使用 Markdown 有序列表。
```

### 3.2 v1.0.0（初始版本）

```
你是一个专业的文档知识库助手。请根据提供的参考资料回答用户问题。

回答规则：
1. 必须基于参考资料内容回答，不要编造未在资料中出现的信息。
2. 如果参考资料不足以回答问题，请明确说明"根据知识库中的资料，暂无法回答该问题"。
3. 回答时请保持准确、简洁、有条理。
4. 如有必要，可适当引用资料中的原文。
5. 使用与用户问题相同的语言回答。
```

### 3.3 设计要点

| 规则 | 设计意图 |
|------|----------|
| 规则 1：基于资料不编造 | 防止 LLM 幻觉（Hallucination），这是 RAG 系统的核心约束 |
| 规则 2：不足时明确说明 | 让用户得到诚实反馈，而不是误导性的拼凑答案 |
| 规则 3：Markdown 排版 | 提升回答可读性，便于前端渲染 |
| 规则 4：引用原文加引号 | 区分模型复述与模型推理，便于用户核对 |
| 规则 5：语言跟随 | 中文问题用中文回答，英文问题用英文回答 |
| 规则 6：不暴露内部机制 | 防止 LLM 在回答中提及"参考资料""System Prompt"等术语，提升用户体验 |
| 输出格式约束 | 避免"回答："等引导语，使回答可直接展示 |

---

## 4. User Prompt 模板

本项目不使用固定的 User Prompt 模板，而是通过 `build_rag_messages()` 动态组装消息列表。组装顺序遵循 **DEC-011 多轮上下文策略**：

```
1. System Prompt（角色设定 + 回答规则）           ← role: system
2. 检索上下文（RAG Context，作为补充 system 消息）  ← role: system
3. 历史对话（最近 4 轮 = 8 条消息，时间正序）       ← role: user / assistant
4. 当前用户问题                                     ← role: user
```

### 4.1 上下文注入格式

检索到的文档片段通过 `_format_context()` 格式化为编号文本：

```
以下是从知识库中检索到的参考资料，请基于这些资料回答用户问题：

【资料1】
{chunk_content_1}

【资料2】
{chunk_content_2}

...

【资料N】
{chunk_content_N}
```

**参数约束**：
- 每段资料最长 500 字符，超出部分截断并附加 `...`
- 资料数量由检索参数 `top_k=5` 控制（可配置）

### 4.2 组装示例

用户问题："什么是 RAG？"，检索到 2 段资料，有 1 轮历史对话：

```python
messages = [
    Message(role="system", content="<v1.1.0 System Prompt>"),
    Message(role="system", content="以下是从知识库中检索到的参考资料...\n\n【资料1】\nRAG 是检索增强生成...\n\n【资料2】\n它结合了检索与生成..."),
    Message(role="user", content="什么是 LLM？"),       # 历史第1轮 user
    Message(role="assistant", content="LLM 是大语言模型..."),  # 历史第1轮 assistant
    Message(role="user", content="什么是 RAG？"),       # 当前问题
]
```

---

## 5. Few-shot 示例

> 注：MVP 阶段未在 Prompt 中硬编码 Few-shot 示例（避免 token 消耗与上下文膨胀）。
> 以下示例用于说明期望的输入-输出行为，供 Prompt 优化参考。

| # | 用户问题 | 检索到的资料 | 期望回答 |
|---|----------|--------------|----------|
| 1 | RAG 的全称是什么？ | RAG（Retrieval-Augmented Generation，检索增强生成）是一种结合检索与生成的技术。 | RAG 的全称是 Retrieval-Augmented Generation（检索增强生成）。它是一种结合检索与生成的技术。 |
| 2 | 如何配置 Embedding 模型？ | （未检索到相关资料，similarity < 0.3） | 根据知识库中的资料，暂无法回答该问题。 |
| 3 | 文档分块策略是什么？ | 1. 采用递归字符切分；2. chunk_size=500 字符；3. overlap=50 字符。 | 文档分块策略如下：1. 采用递归字符切分；2. 每个 chunk 默认 500 字符；3. 相邻 chunk 重叠 50 字符以保证上下文连续性。 |

### 5.1 示例设计要点

- **示例 1**：正常回答场景，展示"基于资料回答 + 引用关键信息"。
- **示例 2**：无相关资料场景，展示"规则 2：不足时明确说明"，而非编造。
- **示例 3**：多信息点场景，展示"规则 3：Markdown 列表组织"。

---

## 6. 输出 Schema

本项目为 **开放式文本生成**，不强制结构化输出（无 JSON Schema 约束）。

**输出约束**（由 `output_guard.py` 执行）：

| 约束 | 参数 | 处理方式 |
|------|------|----------|
| 最小长度 | `MIN_ANSWER_LENGTH = 1` | 空内容返回占位提示 `（模型未返回有效回答，请重试或重新提问。）` |
| 最大长度 | `MAX_ANSWER_LENGTH = 8000` | 超长截断并附加 `（回答已达长度上限，已截断。如需更详细内容，请缩小问题范围后重试。）` |
| 控制字符 | 正则匹配 ASCII 0-8, 11, 12, 14-31, 127, U+200B-200F, U+2028-2029 | 过滤移除（保留 `\n` `\r` `\t`） |
| Prompt 泄漏 | 关键词检测 | 记录警告日志，不拦截（MVP 范围） |

---

## 7. 安全措施

### 7.1 Prompt 注入防护

| 措施 | 实现位置 | 说明 |
|------|----------|------|
| 输入清洗 | `output_guard.validate_question()` | 移除用户问题中的控制字符，防止通过控制字符注入 |
| 角色分离 | `build_rag_messages()` | System Prompt 与用户问题分属不同 message，用户内容无法覆盖 System Prompt |
| 内部机制隐藏 | v1.1.0 规则 6 | 指示 LLM 不提及"参考资料""System Prompt"等术语 |

**MVP 范围外（V2 考虑）**：
- 深度 Prompt 注入检测（如"忽略上述指令"模式检测）
- 用户输入与系统指令的标记隔离（`[USER INPUT START]...[USER INPUT END]`）
- 有害内容分类（需专用模型）

### 7.2 输入净化规则

`validate_question(question)` 执行以下清洗：

1. `strip()` 去除首尾空白
2. 移除不可见控制字符（正则同 7.3）
3. 不做 Prompt 注入语义检测（MVP 范围外）

### 7.3 输出验证规则

`validate_answer(raw_content)` 按顺序执行：

```
1. 空内容检测
   ├── raw_content is None → 返回占位提示，is_empty=True
   └── strip() 后长度 < 1 → 返回占位提示，is_empty=True

2. 控制字符过滤
   ├── 匹配正则: [\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u2028\u2029]
   ├── 命中 → 移除控制字符，had_control_chars=True
   └── 保留: \n \r \t（正常排版字符）

3. 超长截断
   ├── len(content) > 8000 → 截断到 8000 + 追加截断提示
   └── is_truncated=True

4. Prompt 泄漏检测（仅记录日志，不拦截）
   ├── 关键词: "系统提示" "System Prompt" "参考资料是" "根据你提供的 Prompt"
   └── 命中 → prompt_leak_detected=True，记录 WARNING 日志
```

### 7.4 日志脱敏

| 日志内容 | 是否脱敏 | 说明 |
|----------|----------|------|
| LLM 调用失败原因 | 仅记录异常类型 | 不记录完整异常堆栈中的请求体 |
| 控制字符过滤 | 仅记录事件 | 不记录原始内容 |
| Prompt 泄漏检测 | 仅记录命中关键词 | 不记录完整输出 |
| API Key | 永不记录 | 通过 `.env` 管理，代码中不引用 |

---

## 8. 超时与重试

对应 **G2 质量门禁**，详见代码 `backend/app/providers/llm/openai_provider.py`。

### 8.1 超时配置

| 参数 | 默认值 | 配置项 | 说明 |
|------|--------|--------|------|
| 非流式超时 | 30s | `OpenAILLMProvider(timeout=30)` | 非流式 chat completion 超时 |
| 流式超时 | 60s | `OpenAILLMProvider(stream_timeout=60)` | 流式 chat completion 超时（更宽容） |

### 8.2 重试策略

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_MAX_RETRIES` | 3 | 非流式调用最大重试次数 |

**重试规则**：
- **可重试的异常**（瞬时错误）：
  - `openai.APITimeoutError`（请求超时）
  - `openai.APIConnectionError`（连接失败）
- **不重试的异常**（永久错误）：
  - `openai.AuthenticationError`（API Key 无效）
  - `openai.BadRequestError`、`openai.NotFoundError`（请求参数错误）
- **退避策略**：指数退避，第 n 次重试等待 `2^n` 秒（1s → 2s → 4s）
- **流式模式不重试**：流一旦开始返回 token 即无法安全重试，避免重复输出

### 8.3 重试流程图

```
非流式调用
    │
    ├─ attempt 0 (初次调用)
    │   ├─ 成功 → 返回 ChatResponse
    │   └─ 失败（瞬时错误）→ 等待 1s
    │
    ├─ attempt 1 (第1次重试)
    │   ├─ 成功 → 返回 ChatResponse
    │   └─ 失败（瞬时错误）→ 等待 2s
    │
    ├─ attempt 2 (第2次重试)
    │   ├─ 成功 → 返回 ChatResponse
    │   └─ 失败（瞬时错误）→ 等待 4s
    │
    └─ attempt 3 (第3次重试)
        ├─ 成功 → 返回 ChatResponse
        └─ 失败 → 抛出最后一次异常
```

---

## 9. 验证清单

- [x] 所有 Prompt 有版本管理（`PROMPT_REGISTRY`）
- [x] `PromptVersion` 使用 frozen dataclass 保证不可变
- [x] 所有 AI 调用有超时（30s/60s）与重试（3 次，指数退避）
- [x] 所有 AI 输出有验证与过滤（`validate_answer`）
- [x] 输入验证完整（`validate_question` 清洗控制字符）
- [x] 内容安全过滤到位（空内容兜底、超长截断、Prompt 泄漏检测）
- [x] 日志脱敏完整（仅记录异常类型，不记录原始内容）
- [x] 代码符合编码规范（中文注释、类型注解、docstring）
- [x] AI 功能测试完整（`test_prompt_template.py`、`test_output_guard.py`、`test_llm_provider.py` 共 64 个测试用例，覆盖率 100%）

---

## 10. 相关文档

| 文档 | 说明 |
|------|------|
| [architecture.md](./architecture.md) | 系统架构（含 Provider 抽象层 UML、SSE 协议、上下文组装） |
| [api-spec.md](./api-spec.md) | API 规范（含 SSE 事件协议、错误码） |
| [rag-explanation.md](./rag-explanation.md) | RAG 原理说明（面向初级开发者） |
| [decision-log.md](./decision-log.md) | 决策日志（含 DEC-011 多轮上下文策略） |

---

**本文档由 AI 工程师维护。Prompt 变更须更新版本历史并通知 QA Engineer。**
