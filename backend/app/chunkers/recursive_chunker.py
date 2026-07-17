"""
递归字符文本切分器。

按段落 → 右子 → 字符三级递归切分，支持 Markdown 按标题优先切分。
DEC-016: 自实现递归字符切分，不引入 langchain。

切分参数:
- chunk_size: 目标 chunk 长度（字符数），默认 500
- overlap: 相邻 chunk 重叠（字符数），默认 50
- min_chunk_size: 最小 chunk 长度，低于此值与下一段合并，默认 350
"""

import re
from typing import List

from app.config.settings import get_settings


class RecursiveChunker:
    """递归字符文本切分器。

    切分策略:
    1. 清洗文本（去除多余空白）
    2. 若是 Markdown，按标题预切分为 sections
    3. 对每个 section 递归切分:
       a. 按段落分隔符（\\n\\n）切分
       b. 段落过长则按句子分隔符（。！？.!?\\n）切分
       c. 句子过长则按字符强制切分
    4. 合并过短 chunk（< min_chunk_size）
    5. 添加 overlap（重叠字符）

    参考实现: langchain RecursiveCharacterTextSplitter
    """

    # 段落分隔符
    PARAGRAPH_SEPARATORS = ["\n\n", "\n"]
    # 句子分隔符（中英文标点）
    SENTENCE_SEPARATORS = ["。", "！", "？", ".", "!", "?", "\n"]
    # Markdown 标题正则
    MARKDOWN_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
        min_chunk_size: int | None = None,
    ):
        """初始化切分器。

        Args:
            chunk_size: 目标 chunk 长度，None 时从配置读取
            overlap: 重叠长度，None 时从配置读取
            min_chunk_size: 最小 chunk 长度，None 时默认为 chunk_size * 0.7
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP
        self.min_chunk_size = min_chunk_size or int(self.chunk_size * 0.7)

    def chunk(self, text: str, is_markdown: bool = False) -> List[str]:
        """切分文本为 chunks。

        Args:
            text: 待切分的文本
            is_markdown: 是否为 Markdown（按标题优先切分）

        Returns:
            chunk 列表
        """
        if not text or not text.strip():
            return []

        # 1. 清洗文本
        text = self._clean_text(text)

        # 2. Markdown 按标题预切分
        if is_markdown:
            sections = self._split_by_headers(text)
        else:
            sections = [text]

        # 3. 对每个 section 递归切分
        chunks: List[str] = []
        for section in sections:
            if section.strip():
                chunks.extend(self._recursive_split(section))

        # 4. 合并过短 chunk
        chunks = self._merge_short_chunks(chunks)

        # 5. 添加 overlap
        chunks = self._add_overlap(chunks)

        # 6. 过滤空 chunk
        return [c.strip() for c in chunks if c.strip()]

    def _clean_text(self, text: str) -> str:
        """清洗文本。

        合并连续空格，合并 3+ 换行为 2 个。

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 合并连续空格（非换行）为单个空格
        text = re.sub(r"[^\S\n]+", " ", text)
        # 合并 3+ 换行为 2 个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_by_headers(self, text: str) -> List[str]:
        """按 Markdown 标题切分为 sections。

        Args:
            text: Markdown 文本

        Returns:
            section 列表（每个 section 可能包含标题行）
        """
        # 找到所有标题位置
        matches = list(self.MARKDOWN_HEADER_PATTERN.finditer(text))

        if not matches:
            return [text]

        sections: List[str] = []

        # 第一个标题之前的内容
        if matches[0].start() > 0:
            pre_content = text[: matches[0].start()].strip()
            if pre_content:
                sections.append(pre_content)

        # 每个标题到下一个标题之间的内容
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)

        return sections

    def _recursive_split(self, text: str) -> List[str]:
        """递归切分文本。

        按段落 → 句子 → 字符三级切分。

        Args:
            text: 待切分文本

        Returns:
            chunk 列表
        """
        text = text.strip()
        if not text:
            return []

        # 若文本长度 <= chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [text]

        # 1. 按段落切分
        chunks = self._split_by_separator(
            text, self.PARAGRAPH_SEPARATORS, self.chunk_size
        )

        # 2. 若仍有超长 chunk，按句子切分
        refined_chunks: List[str] = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                refined_chunks.extend(
                    self._split_by_separator(
                        chunk, self.SENTENCE_SEPARATORS, self.chunk_size
                    )
                )
            else:
                refined_chunks.append(chunk)

        return refined_chunks

    def _split_by_separator(
        self, text: str, separators: List[str], max_length: int
    ) -> List[str]:
        """按分隔符切分文本，尽量不超过 max_length。

        Args:
            text: 待切分文本
            separators: 分隔符列表（按优先级）
            max_length: 单个 chunk 最大长度

        Returns:
            chunk 列表
        """
        if len(text) <= max_length:
            return [text]

        # 尝试按每个分隔符切分
        for sep in separators:
            if sep in text:
                return self._split_and_merge(text, sep, max_length)

        # 所有分隔符都不存在，按字符强制切分
        return self._split_by_chars(text, max_length)

    def _split_and_merge(
        self, text: str, separator: str, max_length: int
    ) -> List[str]:
        """按分隔符切分，并合并短片段。

        Args:
            text: 待切分文本
            separator: 分隔符
            max_length: 单个 chunk 最大长度

        Returns:
            chunk 列表
        """
        # 按分隔符切分
        parts = text.split(separator)

        chunks: List[str] = []
        current = ""

        for part in parts:
            # 尝试将 part 加入 current
            candidate = (
                current + separator + part if current else part
            )

            if len(candidate) <= max_length:
                current = candidate
            else:
                # current 已满，保存
                if current:
                    chunks.append(current)
                # 若 part 本身超长，递归切分
                if len(part) > max_length:
                    chunks.extend(self._recursive_split(part))
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        return chunks

    def _split_by_chars(self, text: str, max_length: int) -> List[str]:
        """按字符强制切分。

        Args:
            text: 待切分文本
            max_length: 单个 chunk 最大长度

        Returns:
            chunk 列表
        """
        return [
            text[i : i + max_length]
            for i in range(0, len(text), max_length)
        ]

    def _merge_short_chunks(self, chunks: List[str]) -> List[str]:
        """合并过短 chunk。

        将长度 < min_chunk_size 的 chunk 与下一个 chunk 合并
        （除非合并后超过 chunk_size）。

        Args:
            chunks: 原 chunk 列表

        Returns:
            合并后的 chunk 列表
        """
        if not chunks:
            return []

        merged: List[str] = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            # 若 current 过短，尝试与 next_chunk 合并
            if len(current) < self.min_chunk_size:
                candidate = current + "\n\n" + next_chunk
                if len(candidate) <= self.chunk_size:
                    current = candidate
                    continue

            # 无法合并，保存 current
            merged.append(current)
            current = next_chunk

        merged.append(current)
        return merged

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """为相邻 chunk 添加重叠。

        每个 chunk 的开头添加前一个 chunk 的末尾 overlap 个字符。

        Args:
            chunks: 原 chunk 列表

        Returns:
            添加重叠后的 chunk 列表
        """
        if self.overlap <= 0 or len(chunks) <= 1:
            return chunks

        result: List[str] = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            # 取前一个 chunk 的末尾 overlap 个字符
            overlap_text = prev_chunk[-self.overlap :] if len(prev_chunk) > self.overlap else prev_chunk
            # 拼接到当前 chunk 开头
            result.append(overlap_text + chunks[i])

        return result
