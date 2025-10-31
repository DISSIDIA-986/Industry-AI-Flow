from backend.services.embedder import embed_single_text
from backend.services.vectorstore import VectorStore
from backend.services.ollama_client import OllamaClient
from backend.services.retrieval.hybrid_search import HybridRetriever
from backend.services.retrieval.reranker import Reranker
from backend.config import settings


class SimpleRAG:
    def __init__(self, use_hybrid_search: bool = True, use_reranker: bool = True):
        """
        初始化 RAG 系统

        Args:
            use_hybrid_search: 是否使用混合检索（BM25 + 向量）
            use_reranker: 是否使用重排序模块
        """
        self.vectorstore = VectorStore()
        self.llm_client = OllamaClient()
        self.use_hybrid_search = use_hybrid_search
        self.use_reranker = use_reranker

        # Phase 2 Step 2: 初始化混合检索器
        if use_hybrid_search:
            self.hybrid_retriever = HybridRetriever(self.vectorstore)
        else:
            self.hybrid_retriever = None

        # Phase 2 Step 3: 初始化重排序器
        if use_reranker:
            self.reranker = Reranker()
        else:
            self.reranker = None

    def query(self, question: str, top_k: int = None) -> dict:
        """RAG查询流程"""
        if top_k is None:
            top_k = settings.top_k

        # Phase 2 Step 2: 使用混合检索或纯向量检索
        if self.use_hybrid_search and self.hybrid_retriever:
            # 混合检索（BM25 + 向量），先获取更多候选（top_k * 2）
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            similar_chunks = self.hybrid_retriever.search(
                query=question, top_k=retrieve_k, vector_weight=0.7, bm25_weight=0.3
            )
        else:
            # 纯向量检索（Phase 1 方法）
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            query_embedding = embed_single_text(question)
            similar_chunks = self.vectorstore.similarity_search(query_embedding, top_k=retrieve_k)

        # Phase 2 Step 3: 使用重排序器精排
        if self.use_reranker and self.reranker and similar_chunks:
            similar_chunks = self.reranker.rerank(
                query=question, documents=similar_chunks, top_k=top_k
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
