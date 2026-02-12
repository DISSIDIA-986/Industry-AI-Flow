"""
智能文档路由器 - 根据文件类型自动选择处理策略

核心原则:
1. CSV/Excel等结构化数据 → 数据分析Agent + CodeExecutor
2. PDF/TXT等文本文档 → RAG向量检索
3. 图片/扫描文档 → OCR处理 → RAG向量检索
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """文档类型枚举"""

    STRUCTURED_DATA = "structured_data"  # CSV, Excel - 使用数据分析
    TEXT_DOCUMENT = "text_document"  # PDF, TXT, DOCX - 使用RAG
    IMAGE_DOCUMENT = "image_document"  # JPG, PNG - 使用OCR
    CODE_FILE = "code_file"  # PY, JS - 特殊处理
    UNKNOWN = "unknown"  # 未知类型


class ProcessingStrategy(Enum):
    """处理策略枚举"""

    DATA_ANALYSIS = "data_analysis"  # 数据分析Agent
    RAG_RETRIEVAL = "rag_retrieval"  # RAG向量检索
    OCR_PROCESSING = "ocr_processing"  # OCR文字识别
    HYBRID = "hybrid"  # 混合处理
    UNSUPPORTED = "unsupported"  # 不支持


class SmartDocumentRouter:
    """智能文档路由器"""

    def __init__(self):
        """初始化路由器"""
        # 文件扩展名到文档类型的映射
        self.extension_mapping = {
            # 结构化数据
            ".csv": DocumentType.STRUCTURED_DATA,
            ".xlsx": DocumentType.STRUCTURED_DATA,
            ".xls": DocumentType.STRUCTURED_DATA,
            ".tsv": DocumentType.STRUCTURED_DATA,
            ".parquet": DocumentType.STRUCTURED_DATA,
            ".json": DocumentType.STRUCTURED_DATA,
            # 文本文档
            ".pdf": DocumentType.TEXT_DOCUMENT,
            ".txt": DocumentType.TEXT_DOCUMENT,
            ".md": DocumentType.TEXT_DOCUMENT,
            ".doc": DocumentType.TEXT_DOCUMENT,
            ".docx": DocumentType.TEXT_DOCUMENT,
            ".rtf": DocumentType.TEXT_DOCUMENT,
            # 图片文档
            ".jpg": DocumentType.IMAGE_DOCUMENT,
            ".jpeg": DocumentType.IMAGE_DOCUMENT,
            ".png": DocumentType.IMAGE_DOCUMENT,
            ".bmp": DocumentType.IMAGE_DOCUMENT,
            ".tiff": DocumentType.IMAGE_DOCUMENT,
            ".gif": DocumentType.IMAGE_DOCUMENT,
            # 代码文件
            ".py": DocumentType.CODE_FILE,
            ".js": DocumentType.CODE_FILE,
            ".java": DocumentType.CODE_FILE,
            ".cpp": DocumentType.CODE_FILE,
            ".c": DocumentType.CODE_FILE,
        }

        # 文档类型到处理策略的映射
        self.strategy_mapping = {
            DocumentType.STRUCTURED_DATA: ProcessingStrategy.DATA_ANALYSIS,
            DocumentType.TEXT_DOCUMENT: ProcessingStrategy.RAG_RETRIEVAL,
            DocumentType.IMAGE_DOCUMENT: ProcessingStrategy.OCR_PROCESSING,
            DocumentType.CODE_FILE: ProcessingStrategy.RAG_RETRIEVAL,  # 代码也使用RAG
            DocumentType.UNKNOWN: ProcessingStrategy.UNSUPPORTED,
        }

        logger.info("智能文档路由器初始化完成")

    def route_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        路由文档到合适的处理策略

        Args:
            file_path: 文档路径

        Returns:
            Dict包含:
            - document_type: 文档类型
            - processing_strategy: 处理策略
            - recommended_agent: 推荐的Agent
            - metadata: 文档元数据
            - rationale: 路由原因
        """
        file_path = Path(file_path)

        # 1. 识别文档类型
        doc_type = self._identify_document_type(file_path)

        # 2. 确定处理策略
        strategy = self.strategy_mapping.get(doc_type, ProcessingStrategy.UNSUPPORTED)

        # 3. 推荐Agent
        recommended_agent = self._recommend_agent(doc_type, strategy)

        # 4. 收集元数据
        metadata = self._collect_metadata(file_path, doc_type)

        # 5. 生成路由原因
        rationale = self._generate_rationale(doc_type, strategy, metadata)

        routing_result = {
            "file_path": str(file_path),
            "filename": file_path.name,
            "document_type": doc_type.value,
            "processing_strategy": strategy.value,
            "recommended_agent": recommended_agent,
            "metadata": metadata,
            "rationale": rationale,
            "should_use_rag": strategy == ProcessingStrategy.RAG_RETRIEVAL,
            "should_use_data_analysis": strategy == ProcessingStrategy.DATA_ANALYSIS,
            "should_use_ocr": strategy == ProcessingStrategy.OCR_PROCESSING,
        }

        logger.info(
            f"文档路由: {file_path.name} → {strategy.value} "
            f"(类型: {doc_type.value}, Agent: {recommended_agent})"
        )

        return routing_result

    def route_query(
        self,
        question: str,
        related_files: Optional[List[str]] = None,
        intent_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        路由用户查询到合适的处理流程

        Args:
            question: 用户问题
            related_files: 相关文件列表
            intent_result: 意图分类结果

        Returns:
            Dict包含路由决策和处理建议
        """
        # 1. 分析相关文件
        file_analysis = []
        has_structured_data = False
        has_text_documents = False

        if related_files:
            for file_path in related_files:
                if os.path.exists(file_path):
                    routing = self.route_document(file_path)
                    file_analysis.append(routing)

                    if routing["should_use_data_analysis"]:
                        has_structured_data = True
                    if routing["should_use_rag"]:
                        has_text_documents = True

        # 2. 基于意图和文件类型决定策略
        if intent_result:
            intent_type = getattr(intent_result, "intent", None)
            if intent_type:
                intent_value = (
                    intent_type.value
                    if hasattr(intent_type, "value")
                    else str(intent_type)
                )

                # 数据分析意图
                if intent_value == "data_analysis":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (未找到结构化数据文件)"

                # 成本估算意图
                elif intent_value == "cost_estimation":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (成本估算缺少结构化数据)"

                # 知识检索意图
                elif intent_value == "knowledge_retrieval":
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"

                # 文档处理意图
                elif intent_value == "document_processing":
                    strategy = ProcessingStrategy.OCR_PROCESSING
                    agent = "OCRAgent"

                # 其他意图
                else:
                    # 根据文件类型自动决定
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    elif has_text_documents:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (默认)"
            else:
                # 没有有效意图，根据文件决定
                if has_structured_data:
                    strategy = ProcessingStrategy.DATA_ANALYSIS
                    agent = "DataAnalysisAgent"
                else:
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"
        else:
            # 没有意图分类结果，纯基于文件
            if has_structured_data:
                strategy = ProcessingStrategy.DATA_ANALYSIS
                agent = "DataAnalysisAgent"
            else:
                strategy = ProcessingStrategy.RAG_RETRIEVAL
                agent = "RAGAgent"

        return {
            "question": question,
            "processing_strategy": strategy.value,
            "recommended_agent": agent,
            "file_analysis": file_analysis,
            "has_structured_data": has_structured_data,
            "has_text_documents": has_text_documents,
            "rationale": self._generate_query_rationale(
                question,
                strategy,
                has_structured_data,
                has_text_documents,
                intent_result,
            ),
        }

    def _identify_document_type(self, file_path: Path) -> DocumentType:
        """识别文档类型"""
        ext = file_path.suffix.lower()

        return self.extension_mapping.get(ext, DocumentType.UNKNOWN)

    def _recommend_agent(
        self, doc_type: DocumentType, strategy: ProcessingStrategy
    ) -> str:
        """推荐处理Agent"""
        agent_mapping = {
            ProcessingStrategy.DATA_ANALYSIS: "DataAnalysisAgent",
            ProcessingStrategy.RAG_RETRIEVAL: "RAGAgent",
            ProcessingStrategy.OCR_PROCESSING: "OCRAgent",
            ProcessingStrategy.UNSUPPORTED: "None",
        }

        return agent_mapping.get(strategy, "None")

    def _collect_metadata(
        self, file_path: Path, doc_type: DocumentType
    ) -> Dict[str, Any]:
        """收集文档元数据"""
        metadata = {
            "extension": file_path.suffix.lower(),
            "size_bytes": 0,
            "exists": file_path.exists(),
        }

        if file_path.exists():
            try:
                metadata["size_bytes"] = file_path.stat().st_size
                metadata["size_mb"] = round(metadata["size_bytes"] / 1024 / 1024, 2)
                metadata["modified_time"] = file_path.stat().st_mtime
            except Exception as e:
                logger.warning(f"无法获取文件元数据: {e}")

        return metadata

    def _generate_rationale(
        self,
        doc_type: DocumentType,
        strategy: ProcessingStrategy,
        metadata: Dict[str, Any],
    ) -> str:
        """生成路由决策原因"""
        rationale_templates = {
            DocumentType.STRUCTURED_DATA: (
                f"检测到结构化数据文件({metadata.get('extension', 'unknown')})，"
                "应使用数据分析Agent处理。这类文件包含可计算的数值和统计信息，"
                "不适合转换为文本后存入向量数据库。"
            ),
            DocumentType.TEXT_DOCUMENT: (
                f"检测到文本文档({metadata.get('extension', 'unknown')})，"
                "适合使用RAG向量检索系统。文档内容将被分块、向量化并存储，"
                "支持语义检索和问答。"
            ),
            DocumentType.IMAGE_DOCUMENT: (
                f"检测到图片文件({metadata.get('extension', 'unknown')})，"
                "需要先使用OCR提取文字，然后可以使用RAG进行检索。"
            ),
            DocumentType.CODE_FILE: (
                f"检测到代码文件({metadata.get('extension', 'unknown')})，"
                "将作为文本文档处理，使用RAG进行代码片段检索。"
            ),
            DocumentType.UNKNOWN: (
                f"未识别的文件类型({metadata.get('extension', 'unknown')})，" "无法自动选择处理策略。"
            ),
        }

        return rationale_templates.get(doc_type, "无法确定处理策略")

    def _generate_query_rationale(
        self,
        question: str,
        strategy: ProcessingStrategy,
        has_structured_data: bool,
        has_text_documents: bool,
        intent_result: Optional[Any],
    ) -> str:
        """生成查询路由原因"""
        parts = []

        # 意图部分
        if intent_result and hasattr(intent_result, "intent"):
            intent_value = (
                intent_result.intent.value
                if hasattr(intent_result.intent, "value")
                else str(intent_result.intent)
            )
            confidence = getattr(intent_result, "confidence", 0)
            parts.append(f"意图分类: {intent_value} (置信度: {confidence:.2f})")

        # 文件类型部分
        if has_structured_data:
            parts.append("检测到结构化数据文件")
        if has_text_documents:
            parts.append("检测到文本文档")

        # 策略选择部分
        if strategy == ProcessingStrategy.DATA_ANALYSIS:
            parts.append("→ 使用数据分析Agent处理统计和计算查询")
        elif strategy == ProcessingStrategy.RAG_RETRIEVAL:
            parts.append("→ 使用RAG检索系统进行知识问答")
        elif strategy == ProcessingStrategy.OCR_PROCESSING:
            parts.append("→ 使用OCR Agent提取图片文字")

        return "; ".join(parts) if parts else "自动路由"

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的文件格式列表"""
        formats = {}

        for ext, doc_type in self.extension_mapping.items():
            type_name = doc_type.value
            if type_name not in formats:
                formats[type_name] = []
            formats[type_name].append(ext)

        return formats


# 全局实例
smart_document_router = SmartDocumentRouter()
