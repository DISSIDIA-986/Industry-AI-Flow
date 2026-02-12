"""Reranker with graceful fallback when torch/transformers are unavailable."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.utils.device_manager import device_manager

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker; degrades to pass-through mode if unavailable."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.available = False
        self.tokenizer = None
        self.model = None
        self.device = device_manager.get_torch_device()

        try:
            import torch  # type: ignore
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._torch = torch
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()
            self.model.to(self.device)
            self.available = True
            logger.info("Reranker model loaded on %s", self.device)
        except Exception as exc:
            self._torch = None
            self.available = False
            logger.warning(
                "Reranker disabled (dependency/model unavailable): %s", exc
            )

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        if not documents:
            return []

        if not self.available or self.model is None or self.tokenizer is None:
            # Preserve retrieval order and annotate fallback score.
            sliced = documents[:top_k]
            for rank, doc in enumerate(sliced):
                if isinstance(doc, dict) and "rerank_score" not in doc:
                    doc["rerank_score"] = float(max(0, len(sliced) - rank))
            return sliced

        pairs = [[query, doc.get("content", "")] for doc in documents]

        with self._torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            ).to(self.device)
            scores = self.model(**inputs, return_dict=True).logits.view(-1).float()
            scores = scores.cpu().numpy()

        for doc, score in zip(documents, scores):
            if isinstance(doc, dict):
                doc["rerank_score"] = float(score)

        reranked_docs = sorted(
            documents,
            key=lambda item: float(item.get("rerank_score", 0.0))
            if isinstance(item, dict)
            else 0.0,
            reverse=True,
        )
        return reranked_docs[:top_k]
