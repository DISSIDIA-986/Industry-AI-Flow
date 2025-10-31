from sentence_transformers import SentenceTransformer
from backend.config import settings

# 全局模型实例（避免重复加载）
_model = None


def get_model():
    """获取或初始化嵌入模型"""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """向量化文本列表"""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


def embed_single_text(text: str) -> list[float]:
    """向量化单个文本"""
    return embed_texts([text])[0]
