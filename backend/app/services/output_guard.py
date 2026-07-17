"""
AI 输出验证守卫。

对 LLM 生成的输出进行基本验证与过滤（G3 质量门禁）。
MVP 范围内仅做轻量级验证，不做复杂的内容安全过滤。

验证规则:
- 空内容检测：LLM 返回空内容时给出友好提示
- 超长截断：回答超过上限时截断并附加提示
- 控制字符过滤：移除不可见的控制字符（保留换行与制表符）
- Prompt 泄漏检测：检测输出是否包含 System Prompt 片段（基本防护）

不做的事（MVP 范围外，V2 考虑）:
- 有害内容分类（需专用模型）
- Prompt 注入深度检测
- 事实一致性校验
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ===== 验证参数 =====
# 回答最大字符数（超过则截断）
MAX_ANSWER_LENGTH = 8000
# 回答最小有效字符数（低于此值视为空回答）
MIN_ANSWER_LENGTH = 1
# 空回答的友好提示
EMPTY_ANSWER_PLACEHOLDER = "（模型未返回有效回答，请重试或重新提问。）"
# 超长截断后附加的提示
TRUNCATION_SUFFIX = "\n\n（回答已达长度上限，已截断。如需更详细内容，请缩小问题范围后重试。）"

# 不可见控制字符正则（保留 \n \r \t）
# 匹配 ASCII 0-8, 11, 12, 14-31, 127 以及部分 Unicode 控制字符
_CONTROL_CHAR_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u2028\u2029]"
)

# Prompt 泄漏关键词（检测输出中是否暴露 System Prompt 内容）
# 命中时记录警告日志，但不拦截（MVP 仅记录，V2 可升级为拦截）
_PROMPT_LEAK_KEYWORDS = (
    "系统提示",
    "System Prompt",
    "参考资料是",
    "根据你提供的 Prompt",
)


@dataclass
class ValidationResult:
    """输出验证结果。

    Attributes:
        content: 验证后的内容（可能被清洗或截断）
        is_empty: 是否为空内容
        is_truncated: 是否被截断
        had_control_chars: 是否包含控制字符
        prompt_leak_detected: 是否检测到 Prompt 泄漏
    """

    content: str
    is_empty: bool
    is_truncated: bool
    had_control_chars: bool
    prompt_leak_detected: bool


def validate_answer(raw_content: str | None) -> ValidationResult:
    """验证并清洗 LLM 生成的回答。

    流程:
    1. 空内容检测 → 返回占位提示
    2. 控制字符过滤
    3. 超长截断
    4. Prompt 泄漏检测（仅记录日志）

    Args:
        raw_content: LLM 原始输出（可能为 None 或空字符串）

    Returns:
        ValidationResult 包含清洗后的内容与验证标志
    """
    # 1. 空内容检测
    if raw_content is None:
        logger.warning("LLM 返回 None，使用占位提示")
        return ValidationResult(
            content=EMPTY_ANSWER_PLACEHOLDER,
            is_empty=True,
            is_truncated=False,
            had_control_chars=False,
            prompt_leak_detected=False,
        )

    content = str(raw_content).strip()

    if len(content) < MIN_ANSWER_LENGTH:
        logger.warning("LLM 返回空内容（strip 后为空），使用占位提示")
        return ValidationResult(
            content=EMPTY_ANSWER_PLACEHOLDER,
            is_empty=True,
            is_truncated=False,
            had_control_chars=False,
            prompt_leak_detected=False,
        )

    # 2. 控制字符过滤
    had_control_chars = bool(_CONTROL_CHAR_PATTERN.search(content))
    if had_control_chars:
        content = _CONTROL_CHAR_PATTERN.sub("", content)
        logger.info("已过滤 LLM 输出中的不可见控制字符")

    # 3. 超长截断
    is_truncated = len(content) > MAX_ANSWER_LENGTH
    if is_truncated:
        content = content[:MAX_ANSWER_LENGTH] + TRUNCATION_SUFFIX
        logger.info(
            "LLM 输出超长（%d 字符），已截断到 %d 字符",
            len(raw_content),
            MAX_ANSWER_LENGTH,
        )

    # 4. Prompt 泄漏检测（仅记录，不拦截）
    prompt_leak_detected = any(
        keyword in content for keyword in _PROMPT_LEAK_KEYWORDS
    )
    if prompt_leak_detected:
        logger.warning(
            "检测到 LLM 输出可能包含 Prompt 泄漏（关键词命中），"
            "已记录但未拦截（MVP 范围）"
        )

    return ValidationResult(
        content=content,
        is_empty=False,
        is_truncated=is_truncated,
        had_control_chars=had_control_chars,
        prompt_leak_detected=prompt_leak_detected,
    )


def validate_question(question: str) -> str:
    """验证并清洗用户问题（输入验证）。

    移除问题中的不可见控制字符，防止通过问题注入控制字符。
    不做 Prompt 注入深度检测（MVP 范围外）。

    Args:
        question: 用户原始问题

    Returns:
        清洗后的问题字符串
    """
    if not question:
        return question
    return _CONTROL_CHAR_PATTERN.sub("", question.strip())
