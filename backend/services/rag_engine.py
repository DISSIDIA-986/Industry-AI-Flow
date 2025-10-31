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
        # 为每个文档块添加编号，提高可读性
        context_parts = []
        for i, chunk in enumerate(similar_chunks, 1):
            context_parts.append(f"[文档{i}]\n{chunk['content']}")
        context = "\n\n".join(context_parts)

        prompt = f"""你是一个专业的技术问答助手。请基于以下参考文档回答用户问题。

**重要指示**：
1. 仔细阅读所有参考文档
2. 只使用文档中的信息回答
3. 如果文档中没有相关信息，明确说"我不知道"
4. 回答要准确、简洁、专业

**参考文档**：
{context}

**用户问题**：{question}

**你的回答**："""

        # 4. LLM生成答案
        answer = self.llm_client.generate(prompt)

        # 5. 返回结果
        return {
            "question": question,
            "answer": answer,
            "sources": [chunk['doc_id'] for chunk in similar_chunks],
            "retrieved_chunks": similar_chunks
        }
