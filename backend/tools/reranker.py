"""Rerank Tool - Rerank documents using Cross-Encoder"""

from typing import Annotated

from langchain_core.tools import tool

from backend.services.retrieval.reranker import Reranker


@tool
def rerank_tool(
    query: Annotated[str, "User query text"],
    documents: Annotated[list[dict], "List of documents to rank"],
    top_k: Annotated[int, "Number of top documents to return"] = 5,
) -> list[dict]:
    """
    文档重排序工具 - 使用Cross-Encoder模型精排文档

    这个工具使用深度学习Cross-Encoder模型对初检文档进行精排：
    1. 计算查询与每个文档的语义相关性分数
    2. 按分数降序排列
    3. 返回top-k个最相关文档

    相比向量搜索，Cross-Encoder能更准确地捕捉查询-文档之间的语义关系。

    Args:
        query: User query text
        documents: List of documents to rank，每个文档应包含content字段
        top_k: Number of top documents to return（默认5）

    Returns:
        重排序后的top-k文档列表，按相关性分数降序排列

    Example:
        >>> docs = [{"content": "文档1"}, {"content": "文档2"}]
        >>> reranked = rerank_tool.invoke({
        ...     "query": "什么是AI?",
        ...     "documents": docs,
        ...     "top_k": 1
        ... })
        >>> print(f"最相关文档: {reranked[0]['content']}")
    """
    # 初始化重排序器
    reranker = Reranker()

    # 执行重排序
    reranked_docs = reranker.rerank(query=query, documents=documents, top_k=top_k)

    return reranked_docs
