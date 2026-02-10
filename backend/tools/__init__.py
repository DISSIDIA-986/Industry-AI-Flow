"""LangChain tools package with optional heavy dependencies."""

hybrid_retrieval_tool = None
rerank_tool = None

try:
    from backend.tools.retrieval import hybrid_retrieval_tool  # type: ignore[assignment]
except Exception:  # pragma: no cover
    hybrid_retrieval_tool = None

try:
    from backend.tools.reranker import rerank_tool  # type: ignore[assignment]
except Exception:  # pragma: no cover
    rerank_tool = None

__all__ = ["hybrid_retrieval_tool", "rerank_tool"]
