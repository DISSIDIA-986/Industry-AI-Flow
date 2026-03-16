"""Embedding utilities with optional sentence-transformers dependency."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Iterable, List

from backend.config import settings
from backend.utils.device_manager import device_manager

try:  # pragma: no cover - runtime dependency probe
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - lightweight fallback mode
    SentenceTransformer = None  # type: ignore

try:  # pragma: no cover - runtime dependency probe
    from fastembed import TextEmbedding
except Exception:  # pragma: no cover - lightweight fallback mode
    TextEmbedding = None  # type: ignore

logger = logging.getLogger(__name__)

_model: Any = None
_active_backend: str | None = None
_FALLBACK_DIM = int(getattr(settings, "embedding_dim", 768) or 768)


class _FastEmbedAdapter:
    """Adapter that aligns fastembed API with sentence-transformers usage."""

    def __init__(self, model_name: str):
        if TextEmbedding is None:
            raise RuntimeError("fastembed unavailable")
        self._model_name = model_name
        self._model = TextEmbedding(model_name=model_name)
        self._dim: int | None = None

    def encode(
        self, texts: list[str], show_progress_bar: bool = False
    ) -> list[list[float]]:
        del show_progress_bar
        vectors = list(self._model.embed(texts))
        return [
            vector.tolist() if hasattr(vector, "tolist") else list(vector)
            for vector in vectors
        ]

    def get_sentence_embedding_dimension(self) -> int:
        if self._dim is None:
            probe = self.encode(["embedding dimension probe"], show_progress_bar=False)
            self._dim = len(probe[0]) if probe else _FALLBACK_DIM
        return self._dim


def _supports_nomic_retrieval_prefix() -> bool:
    model_name = str(getattr(settings, "embedding_model", "") or "").lower()
    return "nomic-embed-text" in model_name


def _prepare_text(text: str, *, input_type: str) -> str:
    """Apply model-specific input formatting for better retrieval quality."""
    normalized = text or ""
    if not _supports_nomic_retrieval_prefix():
        return normalized

    if input_type == "query":
        prefix = "search_query: "
    else:
        prefix = "search_document: "

    if normalized.startswith(prefix):
        return normalized
    return f"{prefix}{normalized}"


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
    global _model, _active_backend
    if _model is not None:
        return _model

    if SentenceTransformer is not None:
        try:
            device = device_manager.get_sentence_transformer_device()
            logger.info(
                "Initializing embedding model: %s on %s",
                settings.embedding_model,
                device,
            )
            _model = SentenceTransformer(
                settings.embedding_model,
                trust_remote_code=True,
                device=device,
            )
            _active_backend = "sentence_transformers"
            logger.info(
                "Embedding model loaded, dimension: %s",
                _model.get_sentence_embedding_dimension(),
            )
            return _model
        except Exception as exc:
            logger.warning(
                "Failed to initialize sentence-transformers backend: %s", exc
            )

    if TextEmbedding is not None:
        try:
            logger.info("Initializing fastembed model: %s", settings.embedding_model)
            _model = _FastEmbedAdapter(settings.embedding_model)
            _active_backend = "fastembed"
            logger.info(
                "Fastembed model loaded, dimension: %s",
                _model.get_sentence_embedding_dimension(),
            )
            return _model
        except Exception as exc:
            logger.warning("Failed to initialize fastembed backend: %s", exc)

    _active_backend = "fallback_hash"
    logger.warning(
        "semantic embedding backends unavailable; using deterministic fallback embeddings"
    )
    return None


def _fastembed_supported_models() -> dict[str, int]:
    if TextEmbedding is None:
        return {}
    try:
        metadata: Iterable[dict[str, Any]] = TextEmbedding.list_supported_models()
    except Exception:
        return {}

    results: dict[str, int] = {}
    for row in metadata:
        name = str(row.get("model") or row.get("model_name") or "").strip()
        if not name:
            continue
        try:
            dim = int(row.get("dim", 0) or 0)
        except Exception:
            dim = 0
        results[name] = dim
    return results


def embedding_backend_status() -> dict:
    """
    Return embedding backend readiness without forcing heavy model initialization.

    ready=True means semantic embedding backend is available.
    ready=False means the system is running deterministic fallback embeddings.
    """
    if _active_backend == "fallback_hash":
        return {
            "ready": False,
            "backend": "fallback_hash",
            "fallback_active": True,
            "reason": "semantic_backends_unavailable",
            "model": str(getattr(settings, "embedding_model", "")),
            "dimension": _FALLBACK_DIM,
            "loaded": False,
        }

    if _model is not None:
        dim = None
        try:
            dim = int(_model.get_sentence_embedding_dimension())
        except Exception:
            dim = _FALLBACK_DIM
        backend = _active_backend or "unknown"
        return {
            "ready": backend != "fallback_hash",
            "backend": backend,
            "fallback_active": backend == "fallback_hash",
            "reason": "ok" if backend != "fallback_hash" else "unavailable",
            "model": str(getattr(settings, "embedding_model", "")),
            "dimension": dim,
            "loaded": True,
        }

    if SentenceTransformer is None:
        supported = _fastembed_supported_models()
        model_name = str(getattr(settings, "embedding_model", ""))
        if TextEmbedding is not None and model_name in supported:
            dim = int(supported.get(model_name) or _FALLBACK_DIM)
            return {
                "ready": True,
                "backend": "fastembed",
                "fallback_active": False,
                "reason": "not_initialized",
                "model": model_name,
                "dimension": dim,
                "loaded": False,
            }

        return {
            "ready": False,
            "backend": "fallback_hash",
            "fallback_active": True,
            "reason": "sentence_transformers_unavailable",
            "model": model_name,
            "dimension": _FALLBACK_DIM,
            "loaded": False,
        }

    return {
        "ready": True,
        "backend": "sentence_transformers",
        "fallback_active": False,
        "reason": "not_initialized",
        "model": str(getattr(settings, "embedding_model", "")),
        "dimension": int(
            getattr(settings, "embedding_dim", _FALLBACK_DIM) or _FALLBACK_DIM
        ),
        "loaded": False,
    }


def embed_texts(texts: list[str], *, input_type: str = "document") -> list[list[float]]:
    prepared_texts = [_prepare_text(text, input_type=input_type) for text in texts]
    model = get_model()
    if model is None:
        return [_fallback_embedding(text, dim=_FALLBACK_DIM) for text in prepared_texts]

    embeddings = model.encode(prepared_texts, show_progress_bar=True)
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(item) for item in embeddings]


def embed_single_text(text: str, *, input_type: str = "document") -> list[float]:
    return embed_texts([text], input_type=input_type)[0]


def embed_query_text(text: str) -> list[float]:
    return embed_single_text(text, input_type="query")
