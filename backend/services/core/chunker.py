import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


# Hierarchical text separators (ordered by priority)
CONSTRUCTION_SEPARATORS = [
    "\n\n## ",  # Markdown H2 heading
    "\n\n### ",  # Markdown H3 heading
    "\n\n#### ",  # Markdown H4 heading
    "\n\n",  # Double newline (paragraph break)
    "\n",  # Single newline
    ". ",  # Sentence boundary (period)
    "! ",  # Sentence boundary (exclamation)
    "? ",  # Sentence boundary (question)
    "; ",  # Clause boundary (semicolon)
    ", ",  # Clause boundary (comma)
    " ",  # Word boundary
    "",  # Character-level (last resort)
]

# Construction document reference patterns (avoid splitting mid-reference)
CONSTRUCTION_PATTERNS = [
    r"Section \d+\.\d+\.\d+",  # e.g. "Section 4.3.2.1"
    r"CSA [A-Z]\d+\.\d+-\d+",  # e.g. "CSA A23.1-19"
    r"Figure \d+-\d+",  # e.g. "Figure 3-2"
    r"Table \d+\.\d+",  # e.g. "Table 4.5"
    r"Part \d+",  # e.g. "Part 23" (Alberta OHS)
    r"Clause \d+\.\d+\.\d+",  # e.g. "Clause 7.2.4"
]


def _is_construction_reference(text: str) -> bool:
    """Check if text contains a construction standard reference."""
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
    Split text into chunks using semantic separators and overlap.

    Update (2026-02-09):
    - Increased default chunk size from 300 to 512 characters for better context
    - Added construction reference awareness to avoid mid-reference splits
    - Added overlap for context continuity

    Args:
        text: Input text to chunk
        chunk_size: Maximum chunk size in characters (default 512)
        chunk_overlap: Overlap between consecutive chunks (default 128)

    Returns:
        List of chunk dicts with content and metadata
    """
    chunks = []

    # Recursive splitting (inspired by LangChain RecursiveCharacterTextSplitter)
    def split_text_by_separators(text: str, separators: List[str]) -> List[str]:
        """Recursively split text using hierarchical separators."""
        if not separators:
            return [text]

        # Use the first separator
        separator = separators[0]
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)  # Character-level split

        # Process splits
        final_splits = []
        for i, split in enumerate(splits):
            if i > 0 and separator:
                split = separator + split  # Re-attach separator
            # If split is still too large, recurse with next separator
            if len(split) > chunk_size and separators[1:]:
                sub_splits = split_text_by_separators(split, separators[1:])
                final_splits.extend(sub_splits)
            else:
                if split:
                    final_splits.append(split)

        return final_splits

    # Split text using hierarchical separators
    splits = split_text_by_separators(text, CONSTRUCTION_SEPARATORS)

    # Merge splits into chunks respecting chunk_size
    current_chunk = ""
    chunk_id = 0
    start_pos = 0

    for split in splits:
        # If current chunk + new split exceeds chunk_size, save current chunk
        if current_chunk and len(current_chunk) + len(split) > chunk_size:
            # Avoid splitting mid-reference (e.g. "CSA A23.1-14")
            # but cap at 3x chunk_size to prevent unbounded growth
            if (
                _is_construction_reference(current_chunk[-50:])
                and len(current_chunk) + len(split) <= chunk_size * 3
            ):
                # Extend chunk to include the split, then continue to
                # the next iteration WITHOUT the unconditional append below.
                current_chunk += split
                continue
            else:
                saved_chunk = current_chunk
                saved_length = len(saved_chunk)
                # Save the current chunk
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

                # Create overlap (keep last chunk_overlap characters)
                if saved_length > chunk_overlap:
                    overlap_start = saved_length - chunk_overlap
                    current_chunk = saved_chunk[overlap_start:]
                    # Update start position for the overlap region
                    start_pos += overlap_start
                else:
                    current_chunk = ""
                    start_pos += saved_length

        # Append split to current chunk
        current_chunk += split

    # Save the final chunk
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
    """Document chunker with configurable size and overlap."""

    def __init__(self):
        from backend.config import settings

        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def chunk_document(self, document) -> list:
        """
        Chunk a LangChain Document into smaller pieces.

        Args:
            document: LangChain Document object

        Returns:
            List of chunked LangChain Document objects
        """
        try:
            from langchain_core.documents import Document

            # Extract text content
            text_content = document.page_content
            original_metadata = document.metadata or {}

            # Chunk the text
            raw_chunks = chunk_text(
                text=text_content,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            # Convert to LangChain Document objects
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
