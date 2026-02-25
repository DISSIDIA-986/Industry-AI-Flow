"""Hybrid Retrieval Tool - Combining BM25 and vector search"""

from typing import Annotated

from langchain_core.tools import tool

from backend.services.core.vectorstore import VectorStore
from backend.services.retrieval.hybrid_search import HybridRetriever


@tool
def hybrid_retrieval_tool(
    query: Annotated[str, "User query text"], top_k: Annotated[int, "Number of documents to return"] = 10
) -> list[dict]:
    """
    混合检索工具 - 结合BM25和向量搜索检索相关文档

    这个工具使用混合检索策略：
    1. 向量搜索：使用embedding相似度查找语义相关文档
    2. BM25搜索：使用关键词匹配查找精确匹配文档
    3. 结果融合：按权重合并两种搜索结果

    Args:
        query: User query text
        top_k: Number of documents to return（默认10，用于后续重排序）

    Returns:
        检索到的文档列表，每个文档包含：
        - content: 文档内容
        - doc_id: 文档ID
        - chunk_id: 文档块ID
        - score: 相关性分数

    Example:
        >>> docs = hybrid_retrieval_tool.invoke({"query": "什么是LangChain?", "top_k": 5})
        >>> print(f"检索到 {len(docs)} 个文档")
    """
    # 初始化向量存储和混合检索器
    vectorstore = VectorStore()
    retriever = HybridRetriever(vectorstore)

    # 执行混合检索（向量权重0.7，BM25权重0.3）
    docs = retriever.search(
        query=query, top_k=top_k, vector_weight=0.7, bm25_weight=0.3
    )

    return docs
