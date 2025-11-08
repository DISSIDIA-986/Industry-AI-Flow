"""Rerank Tool - 使用Cross-Encoder重排序文档"""

from langchain_core.tools import tool
from typing import Annotated
from backend.services.retrieval.reranker import Reranker


@tool
def rerank_tool(
    query: Annotated[str, "用户查询文本"],
    documents: Annotated[list[dict], "待排序的文档列表"],
    top_k: Annotated[int, "返回的top文档数量"] = 5
) -> list[dict]:
    """
    文档重排序工具 - 使用Cross-Encoder模型精排文档

    这个工具使用深度学习Cross-Encoder模型对初检文档进行精排：
    1. 计算查询与每个文档的语义相关性分数
    2. 按分数降序排列
    3. 返回top-k个最相关文档

    相比向量搜索，Cross-Encoder能更准确地捕捉查询-文档之间的语义关系。

    Args:
        query: 用户查询文本
        documents: 待排序的文档列表，每个文档应包含content字段
        top_k: 返回的top文档数量（默认5）

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
    reranked_docs = reranker.rerank(
        query=query,
        documents=documents,
        top_k=top_k
    )

    return reranked_docs
