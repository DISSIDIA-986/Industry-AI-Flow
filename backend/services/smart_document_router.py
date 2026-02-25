"""
EN - EN

EN:
1. CSV/ExcelEN → ENAgent + CodeExecutor
2. PDF/TXTEN → RAGEN
3. EN/EN → OCREN → RAGEN
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """EN"""

    STRUCTURED_DATA = "structured_data"  # CSV, Excel - EN
    TEXT_DOCUMENT = "text_document"  # PDF, TXT, DOCX - ENRAG
    IMAGE_DOCUMENT = "image_document"  # JPG, PNG - ENOCR
    CODE_FILE = "code_file"  # PY, JS - EN
    UNKNOWN = "unknown"  # EN


class ProcessingStrategy(Enum):
    """EN"""

    DATA_ANALYSIS = "data_analysis"  # ENAgent
    RAG_RETRIEVAL = "rag_retrieval"  # RAGEN
    OCR_PROCESSING = "ocr_processing"  # OCREN
    HYBRID = "hybrid"  # EN
    UNSUPPORTED = "unsupported"  # EN


class SmartDocumentRouter:
    """EN"""

    def __init__(self):
        """EN"""
        # EN
        self.extension_mapping = {
            # EN
            ".csv": DocumentType.STRUCTURED_DATA,
            ".xlsx": DocumentType.STRUCTURED_DATA,
            ".xls": DocumentType.STRUCTURED_DATA,
            ".tsv": DocumentType.STRUCTURED_DATA,
            ".parquet": DocumentType.STRUCTURED_DATA,
            ".json": DocumentType.STRUCTURED_DATA,
            # EN
            ".pdf": DocumentType.TEXT_DOCUMENT,
            ".txt": DocumentType.TEXT_DOCUMENT,
            ".md": DocumentType.TEXT_DOCUMENT,
            ".doc": DocumentType.TEXT_DOCUMENT,
            ".docx": DocumentType.TEXT_DOCUMENT,
            ".rtf": DocumentType.TEXT_DOCUMENT,
            # EN
            ".jpg": DocumentType.IMAGE_DOCUMENT,
            ".jpeg": DocumentType.IMAGE_DOCUMENT,
            ".png": DocumentType.IMAGE_DOCUMENT,
            ".bmp": DocumentType.IMAGE_DOCUMENT,
            ".tiff": DocumentType.IMAGE_DOCUMENT,
            ".gif": DocumentType.IMAGE_DOCUMENT,
            # EN
            ".py": DocumentType.CODE_FILE,
            ".js": DocumentType.CODE_FILE,
            ".java": DocumentType.CODE_FILE,
            ".cpp": DocumentType.CODE_FILE,
            ".c": DocumentType.CODE_FILE,
        }

        # EN
        self.strategy_mapping = {
            DocumentType.STRUCTURED_DATA: ProcessingStrategy.DATA_ANALYSIS,
            DocumentType.TEXT_DOCUMENT: ProcessingStrategy.RAG_RETRIEVAL,
            DocumentType.IMAGE_DOCUMENT: ProcessingStrategy.OCR_PROCESSING,
            DocumentType.CODE_FILE: ProcessingStrategy.RAG_RETRIEVAL,  # ENRAG
            DocumentType.UNKNOWN: ProcessingStrategy.UNSUPPORTED,
        }

        logger.info("EN")

    def route_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        EN

        Args:
            file_path: EN

        Returns:
            DictEN:
            - document_type: EN
            - processing_strategy: EN
            - recommended_agent: ENAgent
            - metadata: EN
            - rationale: EN
        """
        file_path = Path(file_path)

        # 1. EN
        doc_type = self._identify_document_type(file_path)

        # 2. EN
        strategy = self.strategy_mapping.get(doc_type, ProcessingStrategy.UNSUPPORTED)

        # 3. ENAgent
        recommended_agent = self._recommend_agent(doc_type, strategy)

        # 4. EN
        metadata = self._collect_metadata(file_path, doc_type)

        # 5. EN
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
            f"EN: {file_path.name} → {strategy.value} "
            f"(EN: {doc_type.value}, Agent: {recommended_agent})"
        )

        return routing_result

    def route_query(
        self,
        question: str,
        related_files: Optional[List[str]] = None,
        intent_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        EN

        Args:
            question: EN
            related_files: EN
            intent_result: EN

        Returns:
            DictEN
        """
        # 1. EN
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

        # 2. EN
        if intent_result:
            intent_type = getattr(intent_result, "intent", None)
            if intent_type:
                intent_value = (
                    intent_type.value
                    if hasattr(intent_type, "value")
                    else str(intent_type)
                )

                # EN
                if intent_value == "data_analysis":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (EN)"

                # EN
                elif intent_value == "cost_estimation":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (EN)"

                # EN
                elif intent_value == "knowledge_retrieval":
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"

                # EN
                elif intent_value == "document_processing":
                    strategy = ProcessingStrategy.OCR_PROCESSING
                    agent = "OCRAgent"

                # EN
                else:
                    # EN
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    elif has_text_documents:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (EN)"
            else:
                # EN,EN
                if has_structured_data:
                    strategy = ProcessingStrategy.DATA_ANALYSIS
                    agent = "DataAnalysisAgent"
                else:
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"
        else:
            # EN,EN
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
        """EN"""
        ext = file_path.suffix.lower()

        return self.extension_mapping.get(ext, DocumentType.UNKNOWN)

    def _recommend_agent(
        self, doc_type: DocumentType, strategy: ProcessingStrategy
    ) -> str:
        """ENAgent"""
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
        """EN"""
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
                logger.warning(f"EN: {e}")

        return metadata

    def _generate_rationale(
        self,
        doc_type: DocumentType,
        strategy: ProcessingStrategy,
        metadata: Dict[str, Any],
    ) -> str:
        """EN"""
        rationale_templates = {
            DocumentType.STRUCTURED_DATA: (
                f"EN({metadata.get('extension', 'unknown')}),"
                "ENAgentEN.EN,"
                "EN."
            ),
            DocumentType.TEXT_DOCUMENT: (
                f"EN({metadata.get('extension', 'unknown')}),"
                "ENRAGEN.EN,EN,"
                "EN."
            ),
            DocumentType.IMAGE_DOCUMENT: (
                f"EN({metadata.get('extension', 'unknown')}),"
                "ENOCREN,ENRAGEN."
            ),
            DocumentType.CODE_FILE: (
                f"EN({metadata.get('extension', 'unknown')}),"
                "EN,ENRAGEN."
            ),
            DocumentType.UNKNOWN: (
                f"EN({metadata.get('extension', 'unknown')})," "EN."
            ),
        }

        return rationale_templates.get(doc_type, "EN")

    def _generate_query_rationale(
        self,
        question: str,
        strategy: ProcessingStrategy,
        has_structured_data: bool,
        has_text_documents: bool,
        intent_result: Optional[Any],
    ) -> str:
        """EN"""
        parts = []

        # EN
        if intent_result and hasattr(intent_result, "intent"):
            intent_value = (
                intent_result.intent.value
                if hasattr(intent_result.intent, "value")
                else str(intent_result.intent)
            )
            confidence = getattr(intent_result, "confidence", 0)
            parts.append(f"EN: {intent_value} (EN: {confidence:.2f})")

        # EN
        if has_structured_data:
            parts.append("EN")
        if has_text_documents:
            parts.append("EN")

        # EN
        if strategy == ProcessingStrategy.DATA_ANALYSIS:
            parts.append("→ ENAgentEN")
        elif strategy == ProcessingStrategy.RAG_RETRIEVAL:
            parts.append("→ ENRAGEN")
        elif strategy == ProcessingStrategy.OCR_PROCESSING:
            parts.append("→ ENOCR AgentEN")

        return "; ".join(parts) if parts else "EN"

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """EN"""
        formats = {}

        for ext, doc_type in self.extension_mapping.items():
            type_name = doc_type.value
            if type_name not in formats:
                formats[type_name] = []
            formats[type_name].append(ext)

        return formats


# EN
smart_document_router = SmartDocumentRouter()
