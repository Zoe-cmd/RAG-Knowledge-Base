"""
SSE 事件格式化单元测试。

测试 SSE 事件构造函数是否符合 DEC-010 规范。
"""

import json

from app.utils.sse import (
    done_event,
    error_event,
    format_sse_event,
    references_event,
    token_event,
)


class TestSSEFormatting:
    """SSE 事件格式化测试。"""

    def test_format_sse_event_with_dict(self):
        """字典数据应被 JSON 序列化。"""
        result = format_sse_event("token", {"content": "hello"})
        assert result == 'event: token\ndata: {"content": "hello"}\n\n'

    def test_format_sse_event_with_string(self):
        """字符串数据应直接使用。"""
        result = format_sse_event("test", "raw string")
        assert result == "event: test\ndata: raw string\n\n"

    def test_format_sse_event_with_list(self):
        """列表数据应被 JSON 序列化。"""
        data = [{"id": 1}, {"id": 2}]
        result = format_sse_event("references", data)
        parsed = json.loads(result.split("data: ")[1].strip())
        assert parsed == data

    def test_references_event(self):
        """references 事件应包含引用来源列表。"""
        refs = [
            {"doc_id": "doc1", "doc_name": "test.pdf", "similarity": 0.85}
        ]
        result = references_event(refs)
        assert result.startswith("event: references\n")
        assert "doc1" in result
        assert result.endswith("\n\n")

    def test_references_event_empty(self):
        """空 references 事件。"""
        result = references_event([])
        assert "event: references\n" in result
        assert "data: []\n\n" in result

    def test_token_event(self):
        """token 事件应包含 content 字段。"""
        result = token_event("RAG")
        assert 'event: token\n' in result
        assert '"content": "RAG"' in result

    def test_done_event(self):
        """done 事件应包含 message_id 与 elapsed_ms。"""
        result = done_event("msg-uuid-123", 3200)
        assert "event: done\n" in result
        assert '"message_id": "msg-uuid-123"' in result
        assert '"elapsed_ms": 3200' in result

    def test_error_event(self):
        """error 事件应包含 message 与 code。"""
        result = error_event("回答生成超时", "LLM_TIMEOUT")
        assert "event: error\n" in result
        assert '"message": "回答生成超时"' in result
        assert '"code": "LLM_TIMEOUT"' in result

    def test_error_event_default_code(self):
        """error 事件默认错误码为 INTERNAL_ERROR。"""
        result = error_event("未知错误")
        assert '"code": "INTERNAL_ERROR"' in result

    def test_chinese_content_serialized(self):
        """中文内容应正确序列化（ensure_ascii=False）。"""
        result = token_event("这是中文回答")
        assert "这是中文回答" in result

    def test_event_ends_with_double_newline(self):
        """每个事件应以双换行结尾（SSE 规范）。"""
        for event in [
            references_event([]),
            token_event("test"),
            done_event("id", 100),
            error_event("err"),
        ]:
            assert event.endswith("\n\n")
