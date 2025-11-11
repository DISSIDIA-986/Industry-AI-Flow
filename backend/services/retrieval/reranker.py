import logging

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.utils.device_manager import device_manager

logger = logging.getLogger(__name__)


class Reranker:
    """重排序模块：使用交叉编码器对检索结果进行精排（支持 MPS/GPU/CPU）"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        初始化重排序模型

        Args:
            model_name: HuggingFace模型名称，默认使用 bge-reranker-base
        """
        logger.info(f"🚀 初始化 Reranker 模型: {model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

        # 使用设备管理器获取设备
        self.device = device_manager.get_torch_device()
        self.model.to(self.device)

        logger.info("✅ Reranker 模型加载完成，使用设备: %s", self.device)

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        重排序检索结果

        Args:
            query: 查询文本
            documents: 检索结果列表 [{content, doc_id, filename, ...}]
            top_k: 返回前K个结果

        Returns:
            重排序后的文档列表 [{content, doc_id, filename, rerank_score, ...}]
        """
        if not documents:
            return []

        # 准备输入对 [(query, doc_content), ...]
        pairs = [[query, doc["content"]] for doc in documents]

        # Tokenize
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            ).to(self.device)

            # 计算相关性分数
            scores = self.model(**inputs, return_dict=True).logits.view(-1).float()
            scores = scores.cpu().numpy()

        # 将分数添加到文档中
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        # 按分数降序排序
        reranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # 返回 top_k
        return reranked_docs[:top_k]
