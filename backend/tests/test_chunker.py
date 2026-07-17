"""
递归字符切分器单元测试。

测试 DEC-016 递归字符切分算法:
- 基本切分
- 段落/句子/字符三级递归
- Markdown 标题预切分
- 短 chunk 合并
- overlap 叠加
- 边界情况
"""

import pytest

from app.chunkers.recursive_chunker import RecursiveChunker


class TestRecursiveChunker:
    """递归字符切分器测试。"""

    def test_short_text_returns_single_chunk(self):
        """短文本应返回单个 chunk。"""
        chunker = RecursiveChunker(chunk_size=500, overlap=50)
        result = chunker.chunk("这是一段短文本。")
        assert len(result) == 1
        assert "这是一段短文本" in result[0]

    def test_empty_text_returns_empty_list(self):
        """空文本应返回空列表。"""
        chunker = RecursiveChunker(chunk_size=500, overlap=50)
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []
        assert chunker.chunk("\n\n\n") == []

    def test_long_text_split_by_paragraph(self):
        """长文本应按段落切分。"""
        chunker = RecursiveChunker(chunk_size=100, overlap=10)
        # 构造超过 chunk_size 的文本，包含段落分隔
        text = "这是第一段。" * 20 + "\n\n" + "这是第二段。" * 20
        result = chunker.chunk(text)
        assert len(result) > 1
        # 每个 chunk 不应超过 chunk_size 太多（允许 overlap）
        for chunk in result:
            assert len(chunk) <= 200  # 允许一定余量

    def test_split_by_sentence(self):
        """超长段落应按句子切分。"""
        chunker = RecursiveChunker(chunk_size=30, overlap=5)
        # 无段落分隔的长文本（超过 chunk_size=30）
        text = "这是第一个句子。这是第二个句子。这是第三个句子。这是第四个句子。"
        result = chunker.chunk(text)
        assert len(result) > 1

    def test_markdown_header_split(self):
        """Markdown 应按标题预切分。"""
        chunker = RecursiveChunker(chunk_size=200, overlap=10)
        text = """# 标题一

这是标题一的内容。

## 子标题

这是子标题的内容。

# 标题二

这是标题二的内容，包含更多详细信息。"""
        result = chunker.chunk(text, is_markdown=True)
        assert len(result) >= 1
        # 至少有一个 chunk 包含标题一
        assert any("标题一" in c for c in result)

    def test_overlap_added_between_chunks(self):
        """相邻 chunk 之间应添加 overlap。"""
        chunker = RecursiveChunker(chunk_size=50, overlap=10)
        # 构造足够长的文本以产生多个 chunk
        text = "这是一个测试文本。" * 10
        result = chunker.chunk(text)
        if len(result) > 1:
            # 第二个 chunk 的开头应与第一个 chunk 的结尾有重叠
            prev_tail = result[0][-10:]
            assert result[1].startswith(prev_tail)

    def test_min_chunk_size_merge(self):
        """过短 chunk 应被合并。"""
        chunker = RecursiveChunker(chunk_size=100, overlap=0, min_chunk_size=70)
        # 构造短段落 + 长段落
        text = "短。\n\n" + "长文本内容。" * 10
        result = chunker.chunk(text)
        # 短 chunk 应被合并，不应有太短的 chunk
        for chunk in result:
            assert len(chunk) >= 10  # 合并后应更长

    def test_clean_text_merges_spaces(self):
        """清洗文本应合并连续空格。"""
        chunker = RecursiveChunker(chunk_size=500, overlap=50)
        text = "这是  有多个  空格的  文本"
        result = chunker._clean_text(text)
        assert "  " not in result

    def test_clean_text_merges_newlines(self):
        """清洗文本应合并 3+ 换行为 2 个。"""
        chunker = RecursiveChunker(chunk_size=500, overlap=50)
        text = "段落一\n\n\n\n\n段落二"
        result = chunker._clean_text(text)
        assert "\n\n\n" not in result

    def test_split_by_headers_no_headers(self):
        """无标题的 Markdown 应返回原文。"""
        chunker = RecursiveChunker(chunk_size=500, overlap=50)
        text = "这是普通文本，没有标题。"
        result = chunker._split_by_headers(text)
        assert result == [text]

    def test_split_by_chars_forced(self):
        """无分隔符的超长文本应按字符强制切分。"""
        chunker = RecursiveChunker(chunk_size=10, overlap=0)
        # 无任何分隔符的长文本
        text = "abcdefghij" * 5  # 50 字符
        result = chunker._split_by_chars(text, 10)
        assert len(result) == 5
        assert all(len(c) == 10 for c in result)

    def test_custom_parameters(self):
        """应支持自定义参数。"""
        chunker = RecursiveChunker(
            chunk_size=200, overlap=20, min_chunk_size=140
        )
        assert chunker.chunk_size == 200
        assert chunker.overlap == 20
        assert chunker.min_chunk_size == 140

    def test_mixed_content(self):
        """混合内容（中英文、代码块）应正确切分。"""
        chunker = RecursiveChunker(chunk_size=100, overlap=10)
        text = """# Python 教程

Python is a programming language.

```python
def hello():
    print("Hello, World!")
```

## 变量

变量用于存储数据。"""
        result = chunker.chunk(text, is_markdown=True)
        assert len(result) >= 1
        assert all(c.strip() for c in result)  # 无空 chunk
