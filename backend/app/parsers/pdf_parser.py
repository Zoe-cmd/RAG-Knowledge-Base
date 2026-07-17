"""
PDF 文档解析器。

使用 PyPDF2 库解析 PDF 文档为纯文本。
扫描型 PDF（字数为 0）会抛出 ScannedPDFError。
"""

from pathlib import Path

from app.parsers.base import DocumentParser


class ScannedPDFError(Exception):
    """扫描型 PDF 异常。

    PDF 解析后文本字数为 0 时抛出，
    提示用户该 PDF 为扫描件，MVP 暂不支持（需 OCR）。
    """

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(
            f"该 PDF {filename} 为扫描件，MVP 暂不支持，需 OCR"
        )


class PDFParser(DocumentParser):
    """PDF 文档解析器。

    使用 PyPDF2 提取 PDF 中的文本。
    若提取后文本字数为 0，判定为扫描件并抛出异常。
    """

    def parse(self, file_path: Path) -> str:
        """解析 PDF 为纯文本。

        Args:
            file_path: PDF 文件路径

        Returns:
            解析后的纯文本

        Raises:
            ScannedPDFError: PDF 为扫描件（字数为 0）
            Exception: PDF 解析失败
        """
        from PyPDF2 import PdfReader

        reader = PdfReader(str(file_path))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        raw_text = "\n\n".join(text_parts)
        cleaned_text = self.clean_text(raw_text)

        # 扫描件检测：解析后字数为 0
        if len(cleaned_text) == 0:
            raise ScannedPDFError(file_path.name)

        return cleaned_text
