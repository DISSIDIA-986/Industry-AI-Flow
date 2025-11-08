def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[dict]:
    """
    简单分块：按字符数切分，带重叠

    Args:
        text: 待分块的文本
        chunk_size: 每块大小（字符数）
        chunk_overlap: 块之间重叠的字符数

    Returns:
        包含分块内容和元数据的字典列表
    """
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end]
        chunks.append(
            {
                "content": chunk_content,
                "metadata": {
                    "chunk_id": idx,
                    "start_pos": start,
                    "end_pos": min(end, len(text)),
                    "length": len(chunk_content),
                },
            }
        )
        start += chunk_size - chunk_overlap
        idx += 1
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
            print(f"Error chunking document: {e}")
            return []
