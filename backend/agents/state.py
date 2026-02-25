"""Agent State Definitions - LangChain 1.0 TypedDict-based"""

import operator
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage


class RAGAgentState(TypedDict):
    """
    RAG AgentEN

    LangChain 1.0ENTypedDictENAgentEN(ENPydantic/dataclass).
    ENAnnotatedENoperator.addEN.

    Attributes:
        messages: EN(EN)
        question: EN
        retrieved_docs: EN
        reranked_docs: EN
        final_answer: EN
        retrieval_latency: EN(EN)
        rerank_latency: EN(EN)
        generation_latency: EN(EN)
    """

    # EN(ENoperator.addEN)
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # RAGEN
    question: str
    retrieved_docs: list[dict]
    reranked_docs: list[dict]
    final_answer: str

    # EN
    retrieval_latency: float
    rerank_latency: float
    generation_latency: float


class CodeAnalysisAgentState(TypedDict):
    """
    EN Agent EN

    EN,EN,EN.

    Attributes:
        messages: EN(EN)
        question: EN
        code_iterations: EN
        current_code: EN
        execution_status: EN ("executing", "failed", "success")
        dataset_info: EN
        data_source: EN ("file_upload", "database", "api")
        execution_result: EN
        visualizations: EN
        analysis_summary: EN
        execution_latency: EN(EN)
        iteration_count: EN
    """

    # EN(ENoperator.addEN)
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # EN
    question: str

    # EN
    code_iterations: list[dict]  # EN
    current_code: str
    execution_status: str  # "executing", "failed", "success"

    # EN
    dataset_info: dict
    data_source: str  # "file_upload", "database", "api"

    # EN
    execution_result: dict
    visualizations: list[dict]
    analysis_summary: str

    # EN
    execution_latency: float
    iteration_count: int
