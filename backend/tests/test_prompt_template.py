"""
Prompt 模板单元测试。

测试 System Prompt 与 RAG 上下文组装逻辑（DEC-011）。
测试 Prompt 版本化管理（G1 质量门禁）。
"""

import pytest

from app.providers.llm.base import Message
from app.services.prompt_template import (
    CURRENT_PROMPT_VERSION,
    PROMPT_REGISTRY,
    SYSTEM_PROMPT,
    _format_context,
    build_rag_messages,
    get_current_prompt,
    get_prompt,
    list_prompt_versions,
)


class TestSystemPrompt:
    """System Prompt 测试。"""

    def test_system_prompt_not_empty(self):
        """System Prompt 不为空。"""
        assert SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 50

    def test_system_prompt_contains_rules(self):
        """System Prompt 应包含回答规则。"""
        assert "参考资料" in SYSTEM_PROMPT
        assert "不要编造" in SYSTEM_PROMPT


class TestFormatContext:
    """上下文格式化测试。"""

    def test_single_chunk(self):
        """单个片段格式化。"""
        result = _format_context(["RAG 是检索增强生成"])
        assert "【资料1】" in result
        assert "RAG 是检索增强生成" in result

    def test_multiple_chunks(self):
        """多个片段格式化。"""
        chunks = ["片段一", "片段二", "片段三"]
        result = _format_context(chunks)
        assert "【资料1】" in result
        assert "【资料2】" in result
        assert "【资料3】" in result
        # 片段间应有空行分隔
        assert "\n\n" in result

    def test_empty_chunks(self):
        """空片段列表。"""
        result = _format_context([])
        assert result == ""

    def test_long_chunk_truncated(self):
        """超长片段应被截断到 500 字符。"""
        long_text = "A" * 600
        result = _format_context([long_text])
        # 截断后应包含 "..." 标记
        assert "..." in result
        # 不应包含完整的 600 个字符
        assert result.count("A") < 600


class TestBuildRAGMessages:
    """RAG 消息组装测试。"""

    def test_basic_assembly(self):
        """基本消息组装。"""
        messages = build_rag_messages(
            question="什么是 RAG？",
            context_chunks=["RAG 是检索增强生成"],
            history=[],
        )
        # 应包含 system prompt、context、user question
        assert len(messages) == 3  # system + context system + user
        assert messages[0].role == "system"
        assert messages[1].role == "system"
        assert messages[2].role == "user"
        assert messages[2].content == "什么是 RAG？"

    def test_with_history(self):
        """带历史对话的组装。"""
        history = [
            Message(role="user", content="问题1"),
            Message(role="assistant", content="回答1"),
        ]
        messages = build_rag_messages(
            question="问题2",
            context_chunks=["上下文"],
            history=history,
        )
        # system + context system + 2 history + user = 5
        assert len(messages) == 5
        # 历史应在 user 问题之前
        assert messages[2].role == "user"
        assert messages[2].content == "问题1"
        assert messages[3].role == "assistant"
        assert messages[3].content == "回答1"
        assert messages[4].content == "问题2"

    def test_no_context(self):
        """无检索上下文（检索结果为空）。"""
        messages = build_rag_messages(
            question="问题",
            context_chunks=[],
            history=[],
        )
        # 无上下文时，只有 system + user = 2
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_order_is_correct(self):
        """消息顺序应为 system → context → history → question。"""
        history = [Message(role="user", content="历史问题")]
        messages = build_rag_messages(
            question="当前问题",
            context_chunks=["上下文"],
            history=history,
        )
        roles = [m.role for m in messages]
        # 第一个和第二个是 system，最后一个是 user
        assert roles[0] == "system"
        assert roles[-1] == "user"

    def test_system_prompt_is_first(self):
        """System Prompt 应为第一条消息。"""
        messages = build_rag_messages("q", [], [])
        assert messages[0].content == SYSTEM_PROMPT


class TestPromptVersioning:
    """Prompt 版本化管理测试（G1 质量门禁）。"""

    def test_registry_not_empty(self):
        """注册表应至少包含一个版本。"""
        assert len(PROMPT_REGISTRY) >= 1

    def test_current_prompt_version_in_registry(self):
        """当前活跃版本号应存在于注册表中。"""
        assert CURRENT_PROMPT_VERSION in PROMPT_REGISTRY

    def test_get_current_prompt(self):
        """get_current_prompt 应返回当前版本。"""
        prompt = get_current_prompt()
        assert prompt.version == CURRENT_PROMPT_VERSION
        assert prompt.system_prompt
        assert len(prompt.system_prompt) > 50
        assert prompt.description
        assert prompt.created_at

    def test_get_prompt_by_version(self):
        """get_prompt 应返回指定版本。"""
        for version in PROMPT_REGISTRY:
            prompt = get_prompt(version)
            assert prompt.version == version
            assert prompt.system_prompt

    def test_get_prompt_unknown_version_raises(self):
        """获取不存在的版本应抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知的 Prompt 版本"):
            get_prompt("v999.999.999")

    def test_list_prompt_versions_sorted(self):
        """list_prompt_versions 应返回升序版本列表。"""
        versions = list_prompt_versions()
        assert len(versions) >= 1
        assert versions == sorted(versions)
        assert CURRENT_PROMPT_VERSION in versions

    def test_system_prompt_matches_current_version(self):
        """SYSTEM_PROMPT 常量应等于当前版本的 system_prompt。"""
        assert SYSTEM_PROMPT == get_current_prompt().system_prompt

    def test_each_version_has_required_fields(self):
        """每个版本应包含必填字段。"""
        for version, prompt in PROMPT_REGISTRY.items():
            assert prompt.version == version
            assert isinstance(prompt.system_prompt, str)
            assert len(prompt.system_prompt) > 50
            assert isinstance(prompt.description, str)
            assert prompt.description
            assert isinstance(prompt.created_at, str)

    def test_build_rag_messages_with_specific_version(self):
        """build_rag_messages 应支持指定 Prompt 版本。"""
        first_version = list_prompt_versions()[0]
        messages = build_rag_messages(
            question="问题",
            context_chunks=[],
            history=[],
            prompt_version=first_version,
        )
        assert messages[0].content == get_prompt(first_version).system_prompt

    def test_build_rag_messages_default_version(self):
        """build_rag_messages 默认使用当前活跃版本。"""
        messages = build_rag_messages("问题", [], [])
        assert messages[0].content == get_current_prompt().system_prompt

    def test_prompt_versions_are_immutable(self):
        """PromptVersion 应为不可变对象（frozen dataclass）。"""
        prompt = get_current_prompt()
        try:
            prompt.system_prompt = "modified"
            assert False, "应抛出 FrozenInstanceError"
        except AttributeError:
            pass  # frozen=True 在 Python 3.11+ 抛出 AttributeError
