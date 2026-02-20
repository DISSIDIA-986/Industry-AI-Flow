from __future__ import annotations

import backend.services.core.embedder as embedder


class _FakeFastEmbed:
    def __init__(self, model_name: str):
        self.model_name = model_name

    @staticmethod
    def list_supported_models():
        return [{"model": "test-embed-model", "dim": 256}]

    def embed(self, texts):
        for text in texts:
            yield [float(len(text)), 1.0]


def _reset_embedder_state(monkeypatch):
    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(embedder, "_active_backend", None)


def test_embedding_backend_status_prefers_fastembed_when_st_unavailable(monkeypatch):
    _reset_embedder_state(monkeypatch)
    monkeypatch.setattr(embedder, "SentenceTransformer", None)
    monkeypatch.setattr(embedder, "TextEmbedding", _FakeFastEmbed)
    monkeypatch.setattr(embedder.settings, "embedding_model", "test-embed-model")

    status = embedder.embedding_backend_status()

    assert status["ready"] is True
    assert status["backend"] == "fastembed"
    assert status["fallback_active"] is False
    assert status["dimension"] == 256
    assert status["loaded"] is False


def test_embed_texts_uses_fastembed_backend(monkeypatch):
    _reset_embedder_state(monkeypatch)
    monkeypatch.setattr(embedder, "SentenceTransformer", None)
    monkeypatch.setattr(embedder, "TextEmbedding", _FakeFastEmbed)
    monkeypatch.setattr(embedder.settings, "embedding_model", "test-embed-model")

    vectors = embedder.embed_texts(["abc", "hello"])

    assert embedder._active_backend == "fastembed"
    assert len(vectors) == 2
    assert vectors[0] == [3.0, 1.0]
    assert vectors[1] == [5.0, 1.0]


def test_embedding_backend_status_reports_fallback_when_no_semantic_backend(monkeypatch):
    _reset_embedder_state(monkeypatch)
    monkeypatch.setattr(embedder, "SentenceTransformer", None)
    monkeypatch.setattr(embedder, "TextEmbedding", None)
    monkeypatch.setattr(embedder.settings, "embedding_model", "test-embed-model")

    status = embedder.embedding_backend_status()

    assert status["ready"] is False
    assert status["backend"] == "fallback_hash"
    assert status["fallback_active"] is True
    assert status["loaded"] is False


def test_embedding_backend_status_reflects_active_fallback_backend(monkeypatch):
    _reset_embedder_state(monkeypatch)
    monkeypatch.setattr(embedder, "_active_backend", "fallback_hash")

    status = embedder.embedding_backend_status()

    assert status["ready"] is False
    assert status["backend"] == "fallback_hash"
    assert status["reason"] == "semantic_backends_unavailable"
