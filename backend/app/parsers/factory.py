"""
文档解析器工厂。

根据文件扩展名返回对应的解析器实例。
遵循开闭原则：新增格式只需新增解析器类并在此注册。
"""

from functools import lru_cache
from pathlib import Path

from app.parsers.base import DocumentParser
from app.parsers.docx_parser import DocxParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.pdf_parser import PDFParser, ScannedPDFError
from app.parsers.txt_parser import TxtParser


@lru_cache
def get_parser(file_type: str) -> DocumentParser:
    """根据文件类型获取解析器（单例）。

    Args:
        file_type: 文件扩展名（不含点），如 pdf/docx/md/txt

    Returns:
        对应的 DocumentParser 实例

    Raises:
        ValueError: 不支持的文件类型
    """
    parsers = {
        "pdf": PDFParser,
        "docx": DocxParser,
        "md": MarkdownParser,
        "txt": TxtParser,
    }

    parser_class = parsers.get(file_type.lower())
    if parser_class is None:
        raise ValueError(
            f"不支持的文件类型: {file_type}，"
            f"支持的类型: {', '.join(parsers.keys())}"
        )

    return parser_class()


def parse_document(file_path: Path, file_type: str) -> str:
    """解析文档为纯文本。

    便捷函数：获取解析器并解析。

    Args:
        file_path: 文件路径
        file_type: 文件类型（扩展名）

    Returns:
        解析后的纯文本

    Raises:
        ScannedPDFError: PDF 为扫描件
        ValueError: 不支持的文件类型
        Exception: 解析失败
    """
    parser = get_parser(file_type)
    return parser.parse(file_path)


__all__ = [
    "DocumentParser",
    "PDFParser",
    "DocxParser",
    "MarkdownParser",
    "TxtParser",
    "ScannedPDFError",
    "get_parser",
    "parse_document",
]
