"""
AI 输出验证守卫单元测试。

测试 validate_answer 与 validate_question 的验证规则:
- 空内容检测
- 控制字符过滤
- 超长截断
- Prompt 泄漏检测
"""

import pytest

from app.services.output_guard import (
    EMPTY_ANSWER_PLACEHOLDER,
    MAX_ANSWER_LENGTH,
    TRUNCATION_SUFFIX,
    validate_answer,
    validate_question,
)


class TestValidateAnswerEmpty:
    """空内容检测测试。"""

    def test_none_input(self):
        """None 输入应返回占位提示。"""
        result = validate_answer(None)
        assert result.is_empty is True
        assert result.content == EMPTY_ANSWER_PLACEHOLDER
        assert result.is_truncated is False

    def test_empty_string(self):
        """空字符串应返回占位提示。"""
        result = validate_answer("")
        assert result.is_empty is True
        assert result.content == EMPTY_ANSWER_PLACEHOLDER

    def test_whitespace_only(self):
        """仅空白字符应视为空内容。"""
        result = validate_answer("   \n\t  \n  ")
        assert result.is_empty is True
        assert result.content == EMPTY_ANSWER_PLACEHOLDER

    def test_non_empty_content(self):
        """非空内容不应标记为空。"""
        result = validate_answer("RAG 是检索增强生成。")
        assert result.is_empty is False
        assert "RAG" in result.content


class TestValidateAnswerControlChars:
    """控制字符过滤测试。"""

    def test_filter_null_byte(self):
        """应过滤 NULL 字节。"""
        result = validate_answer("RAG\x00是检索")
        assert result.had_control_chars is True
        assert "\x00" not in result.content
        assert "RAG" in result.content
        assert "是检索" in result.content

    def test_filter_bell_and_backspace(self):
        """应过滤 BEL 与 BS 字符。"""
        result = validate_answer("回答\x07内容\x08")
        assert result.had_control_chars is True
        assert "\x07" not in result.content
        assert "\x08" not in result.content

    def test_preserve_newline_and_tab(self):
        """应保留换行符与制表符。"""
        content = "第一行\n第二行\n\t缩进"
        result = validate_answer(content)
        assert result.had_control_chars is False
        assert "\n" in result.content
        assert "\t" in result.content

    def test_filter_zero_width_space(self):
        """应过滤零宽空格等 Unicode 控制字符。"""
        result = validate_answer("RAG\u200b是检索")
        assert result.had_control_chars is True
        assert "\u200b" not in result.content

    def test_no_control_chars(self):
        """正常内容不应标记控制字符。"""
        result = validate_answer("这是正常回答内容。")
        assert result.had_control_chars is False


class TestValidateAnswerTruncation:
    """超长截断测试。"""

    def test_truncate_long_answer(self):
        """超过上限的回答应被截断。"""
        long_content = "A" * (MAX_ANSWER_LENGTH + 100)
        result = validate_answer(long_content)
        assert result.is_truncated is True
        assert result.content.endswith(TRUNCATION_SUFFIX)
        # 截断后总长度 = MAX_ANSWER_LENGTH + len(TRUNCATION_SUFFIX)
        assert len(result.content) == MAX_ANSWER_LENGTH + len(TRUNCATION_SUFFIX)

    def test_no_truncation_for_short_answer(self):
        """未超限的回答不应截断。"""
        content = "A" * 100
        result = validate_answer(content)
        assert result.is_truncated is False
        assert result.content == content

    def test_exact_boundary_not_truncated(self):
        """恰好等于上限的回答不应截断。"""
        content = "A" * MAX_ANSWER_LENGTH
        result = validate_answer(content)
        assert result.is_truncated is False


class TestValidateAnswerPromptLeak:
    """Prompt 泄漏检测测试。"""

    def test_detect_prompt_leak_system_prompt(self):
        """应检测到 System Prompt 关键词。"""
        result = validate_answer("根据系统提示，我认为...")
        assert result.prompt_leak_detected is True

    def test_detect_prompt_leak_english(self):
        """应检测到英文 Prompt 关键词。"""
        result = validate_answer("Based on System Prompt, I will...")
        assert result.prompt_leak_detected is True

    def test_no_prompt_leak(self):
        """正常回答不应触发泄漏检测。"""
        result = validate_answer("RAG 是检索增强生成技术。")
        assert result.prompt_leak_detected is False


class TestValidateAnswerCombined:
    """综合验证测试。"""

    def test_strips_whitespace(self):
        """应去除首尾空白。"""
        result = validate_answer("  RAG 回答  \n")
        assert result.content == "RAG 回答"

    def test_control_chars_and_truncation(self):
        """同时包含控制字符与超长。"""
        long_content = ("A\x00" * (MAX_ANSWER_LENGTH + 50))
        result = validate_answer(long_content)
        assert result.had_control_chars is True
        assert result.is_truncated is True
        assert "\x00" not in result.content


class TestValidateQuestion:
    """用户问题输入验证测试。"""

    def test_filter_control_chars(self):
        """应过滤问题中的控制字符。"""
        result = validate_question("什么是\x00RAG\x07？")
        assert "\x00" not in result
        assert "\x07" not in result
        assert "RAG" in result

    def test_preserve_normal_question(self):
        """正常问题应保持不变（去除首尾空白）。"""
        result = validate_question("  什么是 RAG？  ")
        assert result == "什么是 RAG？"

    def test_empty_question(self):
        """空问题应返回空。"""
        assert validate_question("") == ""
        assert validate_question(None) is None

    def test_preserve_newline_in_question(self):
        """应保留问题中的换行符。"""
        result = validate_question("第一行\n第二行")
        assert "\n" in result

    def test_filter_zero_width_chars(self):
        """应过滤零宽字符（防不可见注入）。"""
        result = validate_question("什么是\u200bRAG\u200b？")
        assert "\u200b" not in result
        assert "RAG" in result
