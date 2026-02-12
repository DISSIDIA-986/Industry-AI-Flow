"""Embedding utilities with optional sentence-transformers dependency."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, List

from backend.config import settings
from backend.utils.device_manager import device_manager

try:  # pragma: no cover - runtime dependency probe
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - lightweight fallback mode
    SentenceTransformer = None  # type: ignore

logger = logging.getLogger(__name__)

_model: Any = None
_FALLBACK_DIM = int(getattr(settings, "embedding_dim", 384) or 384)


def _fallback_embedding(text: str, *, dim: int) -> List[float]:
    """Build deterministic pseudo-embedding from text hash.

    This keeps the system runnable when transformer stack is unavailable.
    """
    text_bytes = text.encode("utf-8", errors="ignore")
    values: List[float] = []
    counter = 0
    while len(values) < dim:
        digest = hashlib.sha256(text_bytes + str(counter).encode("utf-8")).digest()
        for idx in range(0, len(digest), 4):
            chunk = digest[idx : idx + 4]
            if len(chunk) < 4:
                continue
            integer = int.from_bytes(chunk, byteorder="big", signed=False)
            values.append((integer / 4294967295.0) * 2.0 - 1.0)
            if len(values) >= dim:
                break
        counter += 1

    # L2 normalize for cosine similarity compatibility.
    norm = sum(v * v for v in values) ** 0.5
    if norm > 0:
        values = [v / norm for v in values]
    return values


def get_model() -> Any:
    """Load sentence-transformers model when available."""
    global _model
    if _model is not None:
        return _model

    if SentenceTransformer is None:
        logger.warning(
            "sentence-transformers is unavailable; using deterministic fallback embeddings"
        )
        return None

    device = device_manager.get_sentence_transformer_device()
    logger.info("Initializing embedding model: %s on %s", settings.embedding_model, device)
    _model = SentenceTransformer(settings.embedding_model, trust_remote_code=True, device=device)
    logger.info("Embedding model loaded, dimension: %s", _model.get_sentence_embedding_dimension())
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    if model is None:
        return [_fallback_embedding(text, dim=_FALLBACK_DIM) for text in texts]

    embeddings = model.encode(texts, show_progress_bar=True)
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(item) for item in embeddings]


def embed_single_text(text: str) -> list[float]:
    return embed_texts([text])[0]
