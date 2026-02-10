import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


# 建筑文档专用分隔符（优化语义分块）
CONSTRUCTION_SEPARATORS = [
    "\n\n## ",  # Markdown二级标题
    "\n\n### ",  # Markdown三级标题
    "\n\n#### ",  # Markdown四级标题
    "\n\n",  # 段落分隔
    "\n",  # 行分隔
    ". ",  # 句号+空格
    "! ",  # 感叹号+空格
    "? ",  # 问号+空格
    "; ",  # 分号+空格
    ", ",  # 逗号+空格
    " ",  # 空格
    "",  # 紧急情况下按字符切分
]

# 建筑术语和法规引用模式（不拆分这些模式）
CONSTRUCTION_PATTERNS = [
    r"Section \d+\.\d+\.\d+",  # 如 "Section 4.3.2.1"
    r"CSA [A-Z]\d+\.\d+-\d+",  # 如 "CSA A23.1-19"
    r"Figure \d+-\d+",  # 如 "Figure 3-2"
    r"Table \d+\.\d+",  # 如 "Table 4.5"
    r"Part \d+",  # 如 "Part 23"（Alberta OHS）
    r"Clause \d+\.\d+\.\d+",  # 如 "Clause 7.2.4"
]


def _is_construction_reference(text: str) -> bool:
    """检查是否为建筑规范引用（不应在中间拆分）"""
    for pattern in CONSTRUCTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 128,
) -> list[dict]:
    """
    优化分块：语义感知 + 建筑文档专用分隔符

    优化说明（2026-02-09）：
    - 从300字符增加到512字符，提升上下文完整性
    - 使用建筑文档专用分隔符，避免在条款引用中间拆分
    - 保护建筑术语和规范引用不被切断

    Args:
        text: 待分块的文本
        chunk_size: 每块大小（字符数，默认512）
        chunk_overlap: 块之间重叠的字符数（默认128）

    Returns:
        包含分块内容和元数据的字典列表
    """
    chunks = []

    # 按分隔符切分（LangChain RecursiveCharacterTextSplitter逻辑）
    def split_text_by_separators(text: str, separators: List[str]) -> List[str]:
        """递归按分隔符切分文本"""
        if not separators:
            return [text]

        # 使用当前分隔符切分
        separator = separators[0]
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)  # 紧急情况按字符切分

        # 递归处理每个片段
        final_splits = []
        for i, split in enumerate(splits):
            if i > 0 and separator:
                split = separator + split  # 保留分隔符
            # 仅在片段仍然过大时继续递归，避免无意义拆到字符级
            if len(split) > chunk_size and separators[1:]:
                sub_splits = split_text_by_separators(split, separators[1:])
                final_splits.extend(sub_splits)
            else:
                if split:
                    final_splits.append(split)

        return final_splits

    # 切分文本
    splits = split_text_by_separators(text, CONSTRUCTION_SEPARATORS)

    # 合并小片段直到达到chunk_size
    current_chunk = ""
    chunk_id = 0
    start_pos = 0

    for split in splits:
        # 如果当前chunk + 新split超过chunk_size，保存当前chunk
        if current_chunk and len(current_chunk) + len(split) > chunk_size:
            # 检查是否在建筑规范引用中间（避免切断）
            if _is_construction_reference(current_chunk[-50:]):
                # 延长当前chunk以包含完整引用
                current_chunk += split
            else:
                saved_chunk = current_chunk
                saved_length = len(saved_chunk)
                # 保存当前chunk
                chunks.append(
                    {
                        "content": saved_chunk.strip(),
                        "metadata": {
                            "chunk_id": chunk_id,
                            "start_pos": start_pos,
                            "end_pos": start_pos + saved_length,
                            "length": len(saved_chunk.strip()),
                            "chunking_method": "semantic_construction",
                        },
                    }
                )
                chunk_id += 1

                # 计算重叠（保留chunk_overlap字符）
                if saved_length > chunk_overlap:
                    overlap_start = saved_length - chunk_overlap
                    current_chunk = saved_chunk[overlap_start:]
                    # 下一个chunk的起点应该回退到重叠开始处
                    start_pos += overlap_start
                else:
                    current_chunk = ""
                    start_pos += saved_length

        # 添加新split到当前chunk
        current_chunk += split

    # 保存最后一个chunk
    if current_chunk.strip():
        chunks.append(
            {
                "content": current_chunk.strip(),
                "metadata": {
                    "chunk_id": chunk_id,
                    "start_pos": start_pos,
                    "end_pos": start_pos + len(current_chunk),
                    "length": len(current_chunk.strip()),
                    "chunking_method": "semantic_construction",
                },
            }
        )

    return chunks


class DocumentChunker:
    """兼容新文档管理系统的文档分块器"""

    def __init__(self):
        from backend.config import settings

        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def chunk_document(self, document) -> list:
        """
        对LangChain Document对象进行分块

        Args:
            document: LangChain Document对象

        Returns:
            分块后的LangChain Document对象列表
        """
        try:
            from langchain_core.documents import Document

            # 获取文档内容
            text_content = document.page_content
            original_metadata = document.metadata or {}

            # 使用现有分块函数
            raw_chunks = chunk_text(
                text=text_content,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            # 转换为LangChain Document对象
            chunks = []
            for chunk_data in raw_chunks:
                chunk_metadata = original_metadata.copy()
                chunk_metadata.update(chunk_data["metadata"])

                chunk = Document(
                    page_content=chunk_data["content"], metadata=chunk_metadata
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error("Error chunking document: %s", e)
            return []
