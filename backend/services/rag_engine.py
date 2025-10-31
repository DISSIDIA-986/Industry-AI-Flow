from backend.services.embedder import embed_single_text
from backend.services.vectorstore import VectorStore
from backend.services.ollama_client import OllamaClient
from backend.config import settings


class SimpleRAG:
    def __init__(self):
        self.vectorstore = VectorStore()
        self.llm_client = OllamaClient()

    def query(self, question: str, top_k: int = None) -> dict:
        """RAG查询流程"""
        if top_k is None:
            top_k = settings.top_k

        # 1. 向量化问题
        query_embedding = embed_single_text(question)

        # 2. 检索相似文档块
        similar_chunks = self.vectorstore.similarity_search(
            query_embedding, top_k=top_k
        )

        # 3. 构建提示词
        context = "\n---\n".join([chunk['content'] for chunk in similar_chunks])
        prompt = f"""基于以下上下文回答问题。如果无法从上下文中找到答案，请说"我不知道"。

上下文：
{context}

问题：{question}

答案："""

        # 4. LLM生成答案
        answer = self.llm_client.generate(prompt)

        # 5. 返回结果
        return {
            "question": question,
            "answer": answer,
            "sources": [chunk['doc_id'] for chunk in similar_chunks],
            "retrieved_chunks": similar_chunks
        }
