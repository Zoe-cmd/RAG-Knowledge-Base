"""
TXT 文档解析器。

使用 chardet 自动检测文件编码，优先 UTF-8，回退 GBK。
"""

from pathlib import Path

from app.parsers.base import DocumentParser


class TxtParser(DocumentParser):
    """TXT 文档解析器。

    自动检测文件编码：
    1. 尝试 UTF-8 解码
    2. 失败则使用 chardet 检测编码
    3. 检测失败回退 GBK（常见中文编码）
    """

    def parse(self, file_path: Path) -> str:
        """解析 TXT 为纯文本。

        Args:
            file_path: TXT 文件路径

        Returns:
            解析后的纯文本

        Raises:
            Exception: 文件读取失败
        """
        raw_bytes = file_path.read_bytes()
        text = self._decode_text(raw_bytes)
        return self.clean_text(text)

    def _decode_text(self, raw_bytes: bytes) -> str:
        """解码文本，自动检测编码。

        Args:
            raw_bytes: 原始字节

        Returns:
            解码后的文本
        """
        # 1. 尝试 UTF-8（含 BOM 检测）
        try:
            # 去除 UTF-8 BOM
            if raw_bytes.startswith(b"\xef\xbb\xbf"):
                return raw_bytes[3:].decode("utf-8")
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # 2. 使用 chardet 检测编码
        try:
            import chardet

            detection = chardet.detect(raw_bytes)
            encoding = detection.get("encoding")
            if encoding:
                try:
                    return raw_bytes.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    pass
        except ImportError:
            pass

        # 3. 回退 GBK（常见中文编码）
        try:
            return raw_bytes.decode("gbk")
        except UnicodeDecodeError:
            pass

        # 4. 最终回退：忽略错误字符
        return raw_bytes.decode("utf-8", errors="ignore")
