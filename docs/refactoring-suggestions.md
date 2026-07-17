<!--
Document: Refactoring Suggestions
Version: 1.0.0
Author: Code Reviewer
Created: 2026-07-12
Updated: 2026-07-12
Status: Completed
-->

# 重构建议：AI 文档知识库（MVP）

> 本文档基于 [code-review-report.md](file:///home/zoe/Public/project/RAG项目/docs/code-review-report.md) 的审查结果，提供分阶段、可操作的重构建议。每项建议包含：问题背景、重构方案、代码示例、预期收益、验证步骤。

## 重构优先级总览

| 优先级 | 编号 | 标题 | 严重程度 | 建议时机 | 预估工时 |
|--------|------|------|----------|----------|----------|
| P1 | RS-001 | 文档列表状态过滤下推到数据库 | Medium | V1.1 | 1h |
| P1 | RS-002 | 流式回答补充 output_guard 验证 | Medium | V1.1 | 1h |
| P2 | RS-003 | 统一 typing 风格为 Python 3.11+ 内置泛型 | Medium | V1.1 | 0.5h |
| P2 | RS-004 | temperature 配置外置 | Medium | V1.1 | 0.5h |
| P2 | RS-005 | RAGService.answer() 类型注解与导入规范化 | Medium | V1.1 | 0.5h |
| P2 | RS-006 | ChatService 异常类型统一为 SessionNotFoundError | Medium | V1.1 | 0.5h |
| P3 | RS-007 | Embedding 维度映射常量化 | Medium | V1.1 | 0.5h |
| P3 | RS-008 | Provider 切换端点 API 契约修正 | Medium | V1.1 | 1h |
| P4 | RS-009 | 清理未使用导入与日志风格统一 | Low | V1.1 | 0.5h |
| P4 | RS-010 | source_path 残留清理 | Low | V1.1 | 1h |
| P4 | RS-011 | 文件路径存储基准统一 | Low | V1.1 | 1h |
| V2 | RS-012 | 前端迁移至 TypeScript | Low | V2 | 8h+ |

---

## P1 重构（建议 V1.1 首批执行）

### RS-001: 文档列表状态过滤下推到数据库

**对应问题**: M-001 / TD-002

**问题背景**: 当前 `list_documents` 端点在应用层过滤状态，导致分页元数据（`total`、`totalPages`）错误。当用户按状态筛选文档时，看到的分页信息与实际数据不匹配。

**重构方案**: 将 `status` 参数传入 `DocumentService.list_documents`，在数据库查询层过滤。

**代码示例**:

```python
# backend/app/services/document_service.py

async def list_documents(
    self,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,  # 新增参数
) -> dict:
    """获取文档列表（分页，支持状态过滤）。

    Args:
        page: 页码，从 1 开始
        page_size: 每页数量
        status: 可选状态过滤（pending/processing/completed/failed）

    Returns:
        包含 items、total、page、page_size 的字典
    """
    offset = (page - 1) * page_size

    # 构建查询条件
    conditions = [Document.deleted_at.is_(None)]
    if status:
        conditions.append(Document.status == status)

    # 查询总数（带状态过滤）
    count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(*conditions)
    )
    total = (await self._db.execute(count_stmt)).scalar_one()

    # 查询当前页（带状态过滤）
    stmt = (
        select(Document)
        .where(*conditions)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await self._db.execute(stmt)
    documents = list(result.scalars().all())

    return {
        "items": [doc.to_dict() for doc in documents],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
```

```python
# backend/app/api/documents.py

@router.get("")
async def list_documents(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: str | None = Query(
        default=None,
        description="按状态过滤: pending/processing/completed/failed",
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表（分页）。"""
    service = DocumentService(db)
    result = await service.list_documents(page=page, page_size=size, status=status)

    return paginated_response(
        items=result["items"],
        total=result["total"],
        page=page,
        size=size,
    )
```

**预期收益**: 分页元数据正确，数据库查询效率提升（只返回匹配的记录）。

**验证步骤**:
1. 上传多个不同状态的文档
2. 调用 `GET /api/documents?status=completed`，验证 `total` 为已完成文档总数
3. 验证分页 `totalPages` 计算正确
4. 运行现有测试确保无回归

---

### RS-002: 流式回答补充 output_guard 验证

**对应问题**: M-008 / SEC-008 / TD-004

**问题背景**: 流式生成路径中，`assistant_content` 拼接后直接保存与返回，未经 `validate_answer()` 验证。非流式路径已正确调用。这导致流式回答可能包含控制字符、超长内容未截断、空内容未处理。

**重构方案**: 在 `done` 事件发送前，对完整 `assistant_content` 执行验证，使用验证后的内容保存。

**代码示例**:

```python
# backend/app/api/chat.py — stream() 函数内，done 事件发送前

from app.services.output_guard import validate_answer

# ... 在 stream() 函数内 ...

# 3. 保存 assistant 消息（先验证）
validation = validate_answer(assistant_content)
final_content = validation.content

if validation.is_empty:
    logger.warning("流式回答为空，使用占位提示")
if validation.had_control_chars:
    logger.info("流式回答包含控制字符，已过滤")
if validation.is_truncated:
    logger.info("流式回答超长，已截断")

stream_chat_service = ChatService(stream_db)
message = await stream_chat_service.save_message(
    session_id=session_id,
    role="assistant",
    content=final_content,  # 使用验证后的内容
    references=references if references else None,
    elapsed_ms=elapsed_ms,
)
await stream_db.commit()

# 4. 发送 done 事件
yield done_event(str(message.id), elapsed_ms)
```

**注意事项**:
- 验证后的内容可能与前端已渲染的 token 不完全一致（如截断后少了尾部内容）。前端 `onDone` 时可考虑用最终内容替换占位消息内容，但 MVP 阶段可接受微小差异。
- 若验证修改了内容（如控制字符过滤），前端已显示的 token 与最终保存内容可能不一致。建议前端 `onDone` 回调中以服务端最终内容为准。

**预期收益**: 流式与非流式路径行为一致，输出均经验证，防止控制字符注入与超长内容。

**验证步骤**:
1. 测试空内容场景（LLM 返回空）
2. 测试超长内容场景（LLM 返回 > 8000 字符）
3. 测试包含控制字符的内容
4. 验证保存到数据库的内容为验证后的版本

---

## P2 重构（建议 V1.1 第二批执行）

### RS-003: 统一 typing 风格为 Python 3.11+ 内置泛型

**对应问题**: M-006 / TD-001

**问题背景**: 12 个文件使用 `from typing import List, Dict, Union`，与项目其他文件使用的 `list[str]`、`dict[str, Any]`、`str | None` 风格混杂。项目目标 Python 3.11，应统一使用内置泛型。

**重构方案**: 使用 `pyupgrade` 自动迁移，或手动替换。

**操作步骤**:

```bash
# 方法 1: 使用 pyupgrade 自动迁移（推荐）
pip install pyupgrade
pyupgrade --py311-plus backend/app/**/*.py

# 方法 2: 手动替换（受影响文件见 code-review-report.md M-006 表格）
# List[str] → list[str]
# Dict[str, Any] → dict[str, Any]
# Union[A, B] → A | B
# Tuple[A, B] → tuple[A, B]
# 然后删除 from typing import List, Dict, Union, Tuple
```

**手动替换示例**:

```python
# ❌ 修改前 (providers/llm/base.py)
from typing import List, Union

async def chat_completion(
    self,
    messages: List[Message],
    stream: bool = False,
) -> Union[ChatResponse, AsyncIterator[ChatChunk]]:

# ✅ 修改后
async def chat_completion(
    self,
    messages: list[Message],
    stream: bool = False,
) -> ChatResponse | AsyncIterator[ChatChunk]:
```

**预期收益**: 代码风格统一，符合 Python 3.11+ 最佳实践，减少不必要的 typing 导入。

**验证步骤**:
1. 运行 `pyupgrade --py311-plus` 后检查 diff
2. 运行 `python -m pytest` 确保无回归
3. 运行 `mypy app/` 或 `ruff check app/` 确保类型检查通过

---

### RS-004: temperature 配置外置

**对应问题**: M-003 / TD-003

**问题背景**: `temperature=0.7` 在 `rag_service.py` 两处硬编码，违反架构原则"配置外置"。

**重构方案**: 在 `Settings` 中增加 `LLM_TEMPERATURE` 配置项。

**代码示例**:

```python
# backend/app/config/settings.py — Settings 类中新增
class Settings(BaseSettings):
    # ... 已有配置 ...

    # ===== LLM 生成参数 =====
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        description="LLM 采样温度（0.0~2.0），值越大回答越随机",
    )
```

```python
# backend/.env.example — 新增
# ===== LLM 生成参数 =====
LLM_TEMPERATURE=0.7
```

```python
# backend/app/services/rag_service.py — 引用配置
# 修改前: temperature=0.7
# 修改后:
stream = await self._llm.chat_completion(
    messages=messages,
    stream=True,
    temperature=self._settings.LLM_TEMPERATURE,
)
```

**预期收益**: temperature 可通过 .env 调整，无需改代码。符合配置外置原则。

**验证步骤**:
1. 修改 `.env` 中 `LLM_TEMPERATURE=0.3`，验证生成结果更确定
2. 恢复默认值，运行测试确保无回归

---

### RS-005: RAGService.answer() 类型注解与导入规范化

**对应问题**: M-004

**问题背景**: `answer()` 方法的 `session_id` 缺少类型注解，方法体内有内联 `import uuid`，且 UUID 转换逻辑冗余。

**重构方案**: 移至模块级导入，添加类型注解，移除冗余转换。

**代码示例**:

```python
# backend/app/services/rag_service.py — 文件顶部（已有 import uuid 在其他地方吗？）
# 确保文件顶部有:
import uuid

# 修改 answer 方法签名
async def answer(
    self,
    session_id: uuid.UUID,  # 添加类型注解
    question: str,
) -> RAGStreamResult:
    """RAG 流式问答。

    Args:
        session_id: 会话 ID（UUID）
        question: 用户问题

    Returns:
        RAGStreamResult，包含引用来源与回答 chunk 迭代器
    """
    # 移除内联 import 与冗余转换
    # 修改前:
    #   import uuid as uuid_module
    #   sid = uuid_module.UUID(session_id) if isinstance(...) else session_id
    # 修改后:
    sid = session_id  # 调用方已传入 uuid.UUID 类型

    # 输入验证
    question = validate_question(question)

    # ... 后续逻辑中所有 sid 替换为 session_id ...
```

**预期收益**: 符合编码规范，消除内联导入，类型安全。

**验证步骤**:
1. 运行测试确保 `answer()` 方法正常工作
2. `mypy` 类型检查通过

---

### RS-006: ChatService 异常类型统一为 SessionNotFoundError

**对应问题**: M-005

**问题背景**: `ChatService.save_message` 在会话不存在时抛出 `ValueError`，与项目定义的 `SessionNotFoundError` 不一致。

**重构方案**: 改用 `SessionNotFoundError`。

**代码示例**:

```python
# backend/app/services/chat_service.py

# 新增导入
from app.utils.exceptions import SessionNotFoundError

class ChatService:
    # ...

    async def save_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        references: list[dict] | None = None,
        elapsed_ms: int | None = None,
    ) -> ChatMessage:
        session = await self.get_session(session_id)
        if session is None:
            # 修改前: raise ValueError(f"会话不存在: {session_id}")
            # 修改后:
            raise SessionNotFoundError()

        # ... 后续逻辑不变 ...
```

**预期收益**: 异常处理一致，`SessionNotFoundError` 会被全局异常处理器捕获并返回 404 标准错误响应，而非 `ValueError` 被捕获为 500。

**验证步骤**:
1. 测试会话不存在时保存消息，验证返回 404 而非 500
2. 运行测试确保无回归

---

## P3 重构（建议 V1.1 第三批执行）

### RS-007: Embedding 维度映射常量化

**对应问题**: M-007

**问题背景**: `config.py` 中 `1536` 与 `1024` 硬编码，与 Provider 实现中的 `_DIMENSION` 重复定义。

**重构方案**: 维护一个维度映射常量。

**代码示例**:

```python
# backend/app/providers/embedding/factory.py — 新增常量

# Embedding Provider 维度映射（用于配置端点预览，无需实例化 Provider）
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "openai": 1536,
    "bge": 1024,
}


def get_embedding_dimension(provider_name: str) -> int:
    """获取指定 Provider 的向量维度（无需实例化）。"""
    if provider_name not in EMBEDDING_DIMENSIONS:
        raise ValueError(f"不支持的 Embedding Provider: {provider_name}")
    return EMBEDDING_DIMENSIONS[provider_name]
```

```python
# backend/app/api/config.py — 引用常量
from app.providers.embedding.factory import EMBEDDING_DIMENSIONS

# 修改前: new_dimension = 1536 if request.provider == "openai" else 1024
# 修改后:
new_dimension = EMBEDDING_DIMENSIONS.get(request.provider, 0)
```

**预期收益**: 消除魔法数字，维度信息单一来源。

**验证步骤**:
1. 测试 Provider 切换预览端点返回正确维度
2. 运行测试确保无回归

---

### RS-008: Provider 切换端点 API 契约修正

**对应问题**: M-002

**问题背景**: `PUT /api/config/embedding-provider` 不执行实际切换，仅返回提示，与 PUT 语义不符。

**重构方案（短期 MVP 可接受）**: 明确文档说明，或调整 HTTP 方法。

**方案 A（推荐 MVP）**: 保留端点，在 API 文档与响应中明确标注为"预检查"。

```python
# backend/app/api/config.py

@router.put("/embedding-provider")
async def switch_embedding_provider(
    request: SwitchProviderRequest,
    db: AsyncSession = Depends(get_db),
):
    """预检查 Embedding Provider 切换影响。

    注意: MVP 阶段此端点不执行实际切换，仅返回切换影响评估。
    实际切换需修改 .env 中 EMBEDDING_PROVIDER 并重启服务。

    Returns:
        切换前后的 Provider 信息与重建索引提示
    """
    # ... 逻辑不变 ...
    return success_response(
        data={
            # ...
            "message": (
                f"切换至 {request.provider} 需重建索引。"
                f"请修改 .env 中 EMBEDDING_PROVIDER={request.provider} 并重启服务，"
                f"然后重新上传或触发已上传文档的重新向量化。"
            ),
            "note": "MVP 阶段此端点为预检查，不执行实际切换",
        },
    )
```

**方案 B（V1.1 实现）**: 实现运行时热切换。

```python
# 方案 B: 清除工厂单例缓存，下次调用自动重建
from app.providers.embedding.factory import get_embedding_provider

@router.put("/embedding-provider")
async def switch_embedding_provider(request: SwitchProviderRequest, db=Depends(get_db)):
    # ... 校验与统计 ...

    # 更新运行时配置
    settings = get_settings()
    old_provider_name = settings.EMBEDDING_PROVIDER
    settings.EMBEDDING_PROVIDER = request.provider  # 运行时修改

    # 清除工厂单例缓存（lru_cache）
    get_embedding_provider.cache_clear()

    # 获取新 Provider 实例
    new_provider = get_embedding_provider()

    return success_response(data={
        "previous_provider": old_provider_name,
        "current_provider": request.provider,
        "current_dimension": new_provider.dimension,
        "needs_reindex": new_provider.dimension != old_provider.dimension,
        # ...
    })
```

**预期收益**: API 契约与实现一致，用户预期明确。

**验证步骤**:
1. 方案 A: 验证响应包含 `note` 字段
2. 方案 B: 验证切换后新上传文档使用新 Provider

---

## P4 重构（建议 V1.1 随带修复）

### RS-009: 清理未使用导入与日志风格统一

**对应问题**: L-001 / L-005 / L-006 / L-007

**重构方案**: 批量清理。

```python
# L-001: backend/app/services/document_service.py
# 删除 line 17: from typing import List  (未使用)

# L-005: backend/app/services/document_service.py:343
# 修改前: logger.error("删除 Chroma 向量失败: %s，错误: %s", doc_id, e)
# 修改后: logger.error("删除 Chroma 向量失败: %s", doc_id, exc_info=True)

# L-006: backend/app/services/output_guard.py:19-20
# 修改前:
#   import re
#   import logging
# 修改后:
#   import logging
#   import re

# L-007: backend/app/providers/embedding/openai_provider.py:81
# 修改前: batch_size = 100
# 修改后: 在类中添加 _BATCH_SIZE = 100，方法内引用 self._BATCH_SIZE
```

**预期收益**: 代码整洁，日志可排查性一致。

---

### RS-010: source_path 残留清理

**对应问题**: L-002 / TD-006

**问题背景**: SEC-006 修复移除了 `to_reference()` 中的 `source_path`，但 `RetrievalResult` dataclass 与 Chroma metadata 仍保留。

**重构方案**: 评估是否可完全移除。

**决策点**:
- 若 Chroma metadata 中的 `source_path` 无消费方（已确认 `to_reference()` 不再用），可移除
- 若需要保留用于调试，添加注释说明

**代码示例（完全移除方案）**:

```python
# backend/app/services/rag_service.py — RetrievalResult
@dataclass
class RetrievalResult:
    doc_id: str
    doc_name: str
    chunk_index: int
    # 移除: source_path: str
    content: str
    similarity: float

# backend/app/services/rag_service.py — retrieve() 方法
# 移除: source_path=metadata.get("source_path", "")

# backend/app/services/chroma_client.py — add_vectors()
# metadata 中移除 "source_path": source_path
# 参数中移除 source_path: str

# backend/app/services/document_service.py — _process_document()
# 调用 chroma.add_vectors 时移除 source_path 参数
```

**预期收益**: 彻底消除内部文件路径泄露风险。

**验证步骤**:
1. 运行测试确保文档上传与检索正常
2. 验证 Chroma metadata 不再包含 source_path

---

### RS-011: 文件路径存储基准统一

**对应问题**: L-004

**问题背景**: `document_service.py` 根据 `Path.cwd()` 决定存储相对或绝对路径，启动目录变化时可能失效。

**重构方案**: 使用项目根目录作为基准。

**代码示例**:

```python
# backend/app/config/settings.py — 新增项目根目录常量
from pathlib import Path

# 项目根目录（backend 目录的父目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # app/config/ → backend/

class Settings(BaseSettings):
    # ...

    @property
    def upload_dir_path(self) -> Path:
        """上传目录 Path 对象（基于 BASE_DIR），自动创建。"""
        path = BASE_DIR / self.UPLOAD_DIR if not Path(self.UPLOAD_DIR).is_absolute() else Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
```

```python
# backend/app/services/document_service.py — 使用相对路径存储
from app.config.settings import BASE_DIR

# 修改前:
# file_path=str(stored_path.relative_to(Path.cwd()))
# if str(stored_path).startswith(str(Path.cwd()))
# else str(stored_path),

# 修改后:
file_path=str(stored_path.relative_to(BASE_DIR)),
```

**预期收益**: 路径基准固定，不受启动目录影响。

**验证步骤**:
1. 在不同目录启动应用，验证文件上传与删除正常
2. 验证数据库中存储的路径为相对路径

---

## V2 重构（长期规划）

### RS-012: 前端迁移至 TypeScript

**对应问题**: L-009 / TD-005

**问题背景**: 前端使用纯 JavaScript，对于作品集项目，TypeScript 能更好展示类型安全能力。

**重构方案**: 渐进式迁移。

**迁移步骤**:
1. 安装 TypeScript 依赖：`npm install -D typescript @types/node`
2. 创建 `tsconfig.json`
3. 将 `.js` 文件重命名为 `.ts`，逐步添加类型
4. 将 `.vue` 文件的 `<script setup>` 改为 `<script setup lang="ts">`
5. 启用严格模式：`"strict": true`

**优先迁移顺序**:
1. `utils/constants.js` → `constants.ts`（常量最易类型化）
2. `api/*.js` → `api/*.ts`（定义 API 响应类型）
3. `stores/*.js` → `stores/*.ts`（定义 State 接口）
4. `components/*.vue`（添加 Props 类型）
5. `views/*.vue`

**预期收益**: 静态类型检查，IDE 智能提示增强，作品集技术含量提升。

**预估工时**: 8-12 小时（全量迁移）

---

## 重构执行建议

### V1.1 迭代建议（预估 6-8 小时）

| 批次 | 包含项 | 预估工时 | 执行者 |
|------|--------|----------|--------|
| 第一批 | RS-001 + RS-002 | 2h | Backend Engineer |
| 第二批 | RS-003（pyupgrade 自动）+ RS-004 + RS-005 + RS-006 | 2h | Backend Engineer |
| 第三批 | RS-007 + RS-008 | 1.5h | Backend Engineer |
| 随带修复 | RS-009 + RS-010 + RS-011 | 2.5h | Backend Engineer |
| 回归测试 | 全量测试 + QA 回归 | 1h | QA Engineer |

### 验收标准

- [ ] 所有 Medium 问题已修复或已有 V1.1 Issue
- [ ] `python -m pytest` 全量通过（覆盖率不低于 87%）
- [ ] 前端构建无错误
- [ ] 编码规范合规率 >= 95%
- [ ] G3 门禁复审通过

---

## 附录：重构与安全审计的协作

以下问题在安全审计与代码审查中均有发现，由 Code Reviewer 登记并跟踪：

| 问题 | 安全审计编号 | 代码审查编号 | 负责修复 | 状态 |
|------|-------------|-------------|----------|------|
| 流式输出未验证 | SEC-008 | M-008 / RS-002 | Backend Engineer | V1.1 计划 |
| 异常消息泄露 | SEC-005 | L-003 | Backend Engineer | V1.1 计划 |
| source_path 残留 | SEC-006（已修复暴露面） | L-002 / RS-010 | Backend Engineer | V1.1 评估 |
| PyPDF2 弃用库 | SEC-011 | TD-007 | Backend Engineer | V1.1 计划 |
