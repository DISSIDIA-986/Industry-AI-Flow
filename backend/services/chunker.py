def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """简单分块：按字符数切分，带重叠"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks
