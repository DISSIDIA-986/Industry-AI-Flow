"""Agent State Definitions - LangChain 1.0 TypedDict-based"""

import operator
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage


class RAGAgentState(TypedDict):
    """
    RAG Agent状态定义

    LangChain 1.0要求使用TypedDict定义Agent状态（不再支持Pydantic/dataclass）。
    使用Annotated和operator.add实现消息列表的累加语义。

    Attributes:
        messages: 对话消息列表（自动累加）
        question: 用户问题
        retrieved_docs: 检索到的原始文档列表
        reranked_docs: 重排序后的文档列表
        final_answer: 最终答案
        retrieval_latency: 检索延迟（秒）
        rerank_latency: 重排序延迟（秒）
        generation_latency: 生成延迟（秒）
    """

    # 核心消息流（使用operator.add实现累加）
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # RAG工作流状态
    question: str
    retrieved_docs: list[dict]
    reranked_docs: list[dict]
    final_answer: str

    # 性能指标
    retrieval_latency: float
    rerank_latency: float
    generation_latency: float


class CodeAnalysisAgentState(TypedDict):
    """
    代码分析 Agent 状态定义

    支持代码执行、数据分析、可视化和机器学习任务的状态管理。

    Attributes:
        messages: 对话消息列表（自动累加）
        question: 用户问题
        code_iterations: 代码执行历史记录
        current_code: 当前执行的代码
        execution_status: 执行状态 ("executing", "failed", "success")
        dataset_info: 数据集信息
        data_source: 数据来源 ("file_upload", "database", "api")
        execution_result: 执行结果
        visualizations: 生成的可视化图表列表
        analysis_summary: 分析总结
        execution_latency: 执行延迟（秒）
        iteration_count: 迭代次数
    """

    # 核心消息流（使用operator.add实现累加）
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 基础状态
    question: str

    # 代码执行状态
    code_iterations: list[dict]  # 历史执行记录
    current_code: str
    execution_status: str  # "executing", "failed", "success"

    # 数据状态
    dataset_info: dict
    data_source: str  # "file_upload", "database", "api"

    # 分析结果
    execution_result: dict
    visualizations: list[dict]
    analysis_summary: str

    # 性能指标
    execution_latency: float
    iteration_count: int
