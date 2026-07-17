"""
Markdown 文档解析器。

提取 Markdown 文档的纯文本内容，保留段落结构。
不渲染 HTML，仅去除 Markdown 语法标记。
"""

import re
from pathlib import Path

from app.parsers.base import DocumentParser


class MarkdownParser(DocumentParser):
    """Markdown 文档解析器。

    将 Markdown 转换为纯文本：
    - 去除标题标记（#）但保留标题文本
    - 去除链接语法，保留链接文本
    - 去除图片语法
    - 去除强调标记（*、_、`）
    - 保留段落分隔
    """

    def parse(self, file_path: Path) -> str:
        """解析 Markdown 为纯文本。

        Args:
            file_path: Markdown 文件路径

        Returns:
            解析后的纯文本

        Raises:
            Exception: 文件读取失败
        """
        # Markdown 默认 UTF-8 编码
        raw_text = file_path.read_text(encoding="utf-8")
        text = self._strip_markdown_syntax(raw_text)
        return self.clean_text(text)

    def _strip_markdown_syntax(self, text: str) -> str:
        """去除 Markdown 语法标记。

        Args:
            text: 原始 Markdown 文本

        Returns:
            去除语法标记后的纯文本
        """
        # 去除图片: ![alt](url) → alt
        text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
        # 去除链接: [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # 去除标题标记: # Title → Title
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # 去除粗体/斜体: **text** / *text* / __text__ / _text_ → text
        text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^\*]+)\*", r"\1", text)
        text = re.sub(r"__([^__]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)
        # 去除行内代码: `code` → code
        text = re.sub(r"`([^`]+)`", r"\1", text)
        # 去除代码块标记
        text = re.sub(r"```[^\n]*\n", "", text)
        text = re.sub(r"```", "", text)
        # 去除引用标记: > text → text
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
        # 去除列表标记: - item / * item / 1. item → item
        text = re.sub(r"^[\-\*\+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
        # 去除水平分隔线: --- / *** → 空
        text = re.sub(r"^[\-\*\_]{3,}$", "", text, flags=re.MULTILINE)

        return text
