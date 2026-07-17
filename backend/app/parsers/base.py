"""
文档解析器抽象基类。

定义统一的文档解析接口，不同格式（PDF/DOCX/MD/TXT）实现各自的解析逻辑。
"""

from abc import ABC, abstractmethod
from pathlib import Path


class DocumentParser(ABC):
    """文档解析器抽象类。

    所有格式解析器必须实现此接口。
    通过 ParserFactory 根据文件扩展名返回对应实例。
    """

    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """解析文档为纯文本。

        Args:
            file_path: 文件路径

        Returns:
            解析后的纯文本

        Raises:
            ParseError: 解析失败
            ScannedPDFError: PDF 为扫描件（字数为 0）
        """
        pass

    @staticmethod
    def clean_text(text: str) -> str:
        """清洗文本，去除多余空白与特殊字符。

        - 合并连续空格为单个空格
        - 合并连续换行为双换行（保留段落分隔）
        - 去除首尾空白

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        import re

        # 合并连续空格（非换行）为单个空格
        text = re.sub(r"[^\S\n]+", " ", text)
        # 合并 3 个以上换行为 2 个
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除每行首尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # 去除首尾空白
        return text.strip()
