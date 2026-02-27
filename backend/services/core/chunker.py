import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


# EN(EN)
CONSTRUCTION_SEPARATORS = [
    "\n\n## ",  # MarkdownEN
    "\n\n### ",  # MarkdownEN
    "\n\n#### ",  # MarkdownEN
    "\n\n",  # EN
    "\n",  # EN
    ". ",  # EN+EN
    "! ",  # EN+EN
    "? ",  # EN+EN
    "; ",  # EN+EN
    ", ",  # EN+EN
    " ",  # EN
    "",  # EN
]

# EN(EN)
CONSTRUCTION_PATTERNS = [
    r"Section \d+\.\d+\.\d+",  # EN "Section 4.3.2.1"
    r"CSA [A-Z]\d+\.\d+-\d+",  # EN "CSA A23.1-19"
    r"Figure \d+-\d+",  # EN "Figure 3-2"
    r"Table \d+\.\d+",  # EN "Table 4.5"
    r"Part \d+",  # EN "Part 23"(Alberta OHS)
    r"Clause \d+\.\d+\.\d+",  # EN "Clause 7.2.4"
]


def _is_construction_reference(text: str) -> bool:
    """EN(EN)"""
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
    EN:EN + EN

    EN(2026-02-09):
    - EN300EN512EN,EN
    - EN,EN
    - EN

    Args:
        text: EN
        chunk_size: EN(EN,EN512)
        chunk_overlap: EN(EN128)

    Returns:
        EN
    """
    chunks = []

    # EN(LangChain RecursiveCharacterTextSplitterEN)
    def split_text_by_separators(text: str, separators: List[str]) -> List[str]:
        """EN"""
        if not separators:
            return [text]

        # EN
        separator = separators[0]
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)  # EN

        # EN
        final_splits = []
        for i, split in enumerate(splits):
            if i > 0 and separator:
                split = separator + split  # EN
            # EN,EN
            if len(split) > chunk_size and separators[1:]:
                sub_splits = split_text_by_separators(split, separators[1:])
                final_splits.extend(sub_splits)
            else:
                if split:
                    final_splits.append(split)

        return final_splits

    # EN
    splits = split_text_by_separators(text, CONSTRUCTION_SEPARATORS)

    # ENchunk_size
    current_chunk = ""
    chunk_id = 0
    start_pos = 0

    for split in splits:
        # ENchunk + ENsplitENchunk_size,ENchunk
        if current_chunk and len(current_chunk) + len(split) > chunk_size:
            # Avoid splitting mid-reference (e.g. "CSA A23.1-14")
            if _is_construction_reference(current_chunk[-50:]):
                # Extend chunk to include the split, then continue to
                # the next iteration WITHOUT the unconditional append below.
                current_chunk += split
                continue
            else:
                saved_chunk = current_chunk
                saved_length = len(saved_chunk)
                # ENchunk
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

                # EN(ENchunk_overlapEN)
                if saved_length > chunk_overlap:
                    overlap_start = saved_length - chunk_overlap
                    current_chunk = saved_chunk[overlap_start:]
                    # ENchunkEN
                    start_pos += overlap_start
                else:
                    current_chunk = ""
                    start_pos += saved_length

        # ENsplitENchunk
        current_chunk += split

    # ENchunk
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
    """EN"""

    def __init__(self):
        from backend.config import settings

        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def chunk_document(self, document) -> list:
        """
        ENLangChain DocumentEN

        Args:
            document: LangChain DocumentEN

        Returns:
            ENLangChain DocumentEN
        """
        try:
            from langchain_core.documents import Document

            # EN
            text_content = document.page_content
            original_metadata = document.metadata or {}

            # EN
            raw_chunks = chunk_text(
                text=text_content,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            # ENLangChain DocumentEN
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
