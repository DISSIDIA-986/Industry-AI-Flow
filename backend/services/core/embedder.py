import logging

from sentence_transformers import SentenceTransformer

from backend.config import settings
from backend.utils.device_manager import device_manager

logger = logging.getLogger(__name__)

# 全局模型实例（避免重复加载）
_model = None


def get_model():
    """获取或初始化嵌入模型（带设备优化）"""
    global _model
    if _model is None:
        # 获取设备配置
        device = device_manager.get_sentence_transformer_device()

        logger.info(f"🚀 初始化嵌入模型: {settings.embedding_model}")
        logger.info(f"   使用设备: {device_manager.device_name}")

        # 加载模型并指定设备
        _model = SentenceTransformer(
            settings.embedding_model, trust_remote_code=True, device=device
        )

        logger.info(f"✅ 模型加载完成，维度: {_model.get_sentence_embedding_dimension()}")

    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """向量化文本列表"""
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


def embed_single_text(text: str) -> list[float]:
    """向量化单个文本"""
    return embed_texts([text])[0]
