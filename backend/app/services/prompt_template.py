"""
Prompt 模板管理。

定义 RAG 问答的 System Prompt 与上下文组装逻辑。
DEC-011: 系统提示 + 检索上下文 + 最近 4 轮历史 + 当前问题。

Prompt 版本化管理（G1 质量门禁）:
- 所有 Prompt 通过 PROMPT_REGISTRY 注册版本
- 每个版本含 version / system_prompt / description / created_at
- 通过 get_prompt(version) 获取指定版本，get_current_prompt() 获取当前版本
- SYSTEM_PROMPT 常量保持向后兼容，指向当前版本的 system_prompt
- 版本变更需更新 CHANGELOG 并保留旧版本以便回滚
"""

from dataclasses import dataclass
from typing import Dict, List

from app.providers.llm.base import Message


@dataclass(frozen=True)
class PromptVersion:
    """Prompt 版本信息。

    Attributes:
        version: 版本号（语义化版本，如 v1.0.0）
        system_prompt: System Prompt 内容
        description: 版本描述与变更说明
        created_at: 版本创建日期（YYYY-MM-DD）
    """

    version: str
    system_prompt: str
    description: str
    created_at: str


# ===== Prompt 版本注册表 =====
# 新增版本时：
# 1. 在 PROMPT_REGISTRY 中追加新版本
# 2. 更新 CURRENT_PROMPT_VERSION 指向新版本
# 3. 在 docs/prompts.md 中记录变更说明
PROMPT_REGISTRY: Dict[str, PromptVersion] = {
    "v1.0.0": PromptVersion(
        version="v1.0.0",
        system_prompt="""你是一个专业的文档知识库助手。请根据提供的参考资料回答用户问题。

回答规则：
1. 必须基于参考资料内容回答，不要编造未在资料中出现的信息。
2. 如果参考资料不足以回答问题，请明确说明"根据知识库中的资料，暂无法回答该问题"。
3. 回答时请保持准确、简洁、有条理。
4. 如有必要，可适当引用资料中的原文。
5. 使用与用户问题相同的语言回答。""",
        description="初始版本：基于参考资料回答、不编造、不足时明确说明、保持原文语言",
        created_at="2026-07-12",
    ),
    "v1.1.0": PromptVersion(
        version="v1.1.0",
        system_prompt="""你是基于本地文档知识库的 AI 助手。请严格根据下方提供的"参考资料"回答用户问题。

回答规则：
1. 回答必须基于参考资料内容，不要编造资料中未出现的信息。
2. 如果参考资料不足以回答问题，请明确回复："根据知识库中的资料，暂无法回答该问题。"，不要拼凑或臆测。
3. 回答应准确、简洁、有条理；如适用可用 Markdown 列表或代码块组织。
4. 引用资料原文时使用引号标明。
5. 使用与用户问题相同的语言回答（中文问题用中文，英文问题用英文）。
6. 不要提及"参考资料""系统提示""Prompt"等内部机制。

输出格式：
- 直接给出回答正文，不要输出"回答："之类的引导语。
- 如需分点说明，使用 Markdown 有序列表。""",
        description="优化版本：增强防编造约束、明确输出格式、禁止暴露内部机制、支持 Markdown 排版",
        created_at="2026-07-12",
    ),
}

# 当前活跃版本（变更此常量即可切换默认使用的 Prompt 版本）
CURRENT_PROMPT_VERSION = "v1.1.0"


# 向后兼容：SYSTEM_PROMPT 指向当前活跃版本的 system_prompt
# 已有代码与测试可直接引用此常量，无需改动
SYSTEM_PROMPT: str = PROMPT_REGISTRY[CURRENT_PROMPT_VERSION].system_prompt


def get_prompt(version: str = CURRENT_PROMPT_VERSION) -> PromptVersion:
    """获取指定版本的 Prompt。

    Args:
        version: Prompt 版本号，默认为当前活跃版本

    Returns:
        PromptVersion 实例

    Raises:
        ValueError: 版本号不存在于注册表
    """
    if version not in PROMPT_REGISTRY:
        available = ", ".join(sorted(PROMPT_REGISTRY.keys()))
        raise ValueError(
            f"未知的 Prompt 版本: {version}，可用版本: {available}"
        )
    return PROMPT_REGISTRY[version]


def get_current_prompt() -> PromptVersion:
    """获取当前活跃版本的 Prompt。

    Returns:
        当前活跃的 PromptVersion
    """
    return get_prompt(CURRENT_PROMPT_VERSION)


def list_prompt_versions() -> List[str]:
    """列出所有可用的 Prompt 版本号（按版本排序）。

    Returns:
        版本号列表（升序）
    """
    return sorted(PROMPT_REGISTRY.keys())


def build_rag_messages(
    question: str,
    context_chunks: List[str],
    history: List[Message],
    prompt_version: str = CURRENT_PROMPT_VERSION,
) -> List[Message]:
    """组装 RAG 上下文消息列表。

    组装顺序（DEC-011）:
    1. System Prompt（角色设定 + 回答规则）
    2. 检索上下文（RAG Context，作为 system 消息的补充或独立 user 消息）
    3. 历史对话（最近 4 轮 = 8 条消息，按时间正序）
    4. 当前用户问题

    Args:
        question: 当前用户问题
        context_chunks: 检索到的文档片段列表
        history: 历史消息列表（已截断为最近 4 轮，按时间正序）
        prompt_version: 指定使用的 Prompt 版本，默认为当前活跃版本

    Returns:
        组装后的 Message 列表，可直接传给 LLM Provider
    """
    messages: List[Message] = []

    # 1. System Prompt（按版本获取）
    system_prompt = get_prompt(prompt_version).system_prompt
    messages.append(Message(role="system", content=system_prompt))

    # 2. 检索上下文（若有）
    if context_chunks:
        context_text = _format_context(context_chunks)
        messages.append(
            Message(
                role="system",
                content=f"以下是从知识库中检索到的参考资料，请基于这些资料回答用户问题：\n\n{context_text}",
            )
        )

    # 3. 历史对话
    messages.extend(history)

    # 4. 当前用户问题
    messages.append(Message(role="user", content=question))

    return messages


def _format_context(chunks: List[str]) -> str:
    """格式化检索到的文档片段为上下文文本。

    Args:
        chunks: 文档片段列表

    Returns:
        格式化后的上下文文本，每段带编号
    """
    formatted: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        # 限制每段长度，避免上下文过长
        if len(chunk) > 500:
            truncated = chunk[:500] + "..."
        else:
            truncated = chunk
        formatted.append(f"【资料{i}】\n{truncated}")
    return "\n\n".join(formatted)
