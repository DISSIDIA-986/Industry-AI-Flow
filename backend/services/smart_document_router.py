"""
Smart Document Router - Automatically routes documents to the appropriate processing pipeline.

Routing rules:
1. CSV/Excel (structured data) -> Data Analysis Agent + CodeExecutor
2. PDF/TXT (text documents) -> RAG retrieval pipeline
3. Images (scanned documents) -> OCR processing -> RAG pipeline
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document type classification."""

    STRUCTURED_DATA = "structured_data"  # CSV, Excel - for data analysis
    TEXT_DOCUMENT = "text_document"  # PDF, TXT, DOCX - for RAG retrieval
    IMAGE_DOCUMENT = "image_document"  # JPG, PNG - requires OCR
    CODE_FILE = "code_file"  # PY, JS - code files
    UNKNOWN = "unknown"  # Unsupported format


class ProcessingStrategy(Enum):
    """Document processing strategy."""

    DATA_ANALYSIS = "data_analysis"  # Route to Data Analysis Agent
    RAG_RETRIEVAL = "rag_retrieval"  # Route to RAG pipeline
    OCR_PROCESSING = "ocr_processing"  # Route to OCR processing
    HYBRID = "hybrid"  # Combined processing
    UNSUPPORTED = "unsupported"  # Format not supported


class SmartDocumentRouter:
    """Routes documents to appropriate processing pipelines based on file type."""

    def __init__(self):
        """Initialize the smart document router with extension and strategy mappings."""
        # File extension to document type mapping
        self.extension_mapping = {
            # Structured data formats
            ".csv": DocumentType.STRUCTURED_DATA,
            ".xlsx": DocumentType.STRUCTURED_DATA,
            ".xls": DocumentType.STRUCTURED_DATA,
            ".tsv": DocumentType.STRUCTURED_DATA,
            ".parquet": DocumentType.STRUCTURED_DATA,
            ".json": DocumentType.STRUCTURED_DATA,
            # Text document formats
            ".pdf": DocumentType.TEXT_DOCUMENT,
            ".txt": DocumentType.TEXT_DOCUMENT,
            ".md": DocumentType.TEXT_DOCUMENT,
            ".doc": DocumentType.TEXT_DOCUMENT,
            ".docx": DocumentType.TEXT_DOCUMENT,
            ".rtf": DocumentType.TEXT_DOCUMENT,
            # Image formats
            ".jpg": DocumentType.IMAGE_DOCUMENT,
            ".jpeg": DocumentType.IMAGE_DOCUMENT,
            ".png": DocumentType.IMAGE_DOCUMENT,
            ".bmp": DocumentType.IMAGE_DOCUMENT,
            ".tiff": DocumentType.IMAGE_DOCUMENT,
            ".gif": DocumentType.IMAGE_DOCUMENT,
            # Code file formats
            ".py": DocumentType.CODE_FILE,
            ".js": DocumentType.CODE_FILE,
            ".java": DocumentType.CODE_FILE,
            ".cpp": DocumentType.CODE_FILE,
            ".c": DocumentType.CODE_FILE,
        }

        # Document type to processing strategy mapping
        self.strategy_mapping = {
            DocumentType.STRUCTURED_DATA: ProcessingStrategy.DATA_ANALYSIS,
            DocumentType.TEXT_DOCUMENT: ProcessingStrategy.RAG_RETRIEVAL,
            DocumentType.IMAGE_DOCUMENT: ProcessingStrategy.OCR_PROCESSING,
            DocumentType.CODE_FILE: ProcessingStrategy.RAG_RETRIEVAL,  # Code files use RAG
            DocumentType.UNKNOWN: ProcessingStrategy.UNSUPPORTED,
        }

        logger.info("Smart document router initialized")

    def route_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Route a document to the appropriate processing pipeline.

        Args:
            file_path: Path to the document file.

        Returns:
            Routing result dictionary containing:
            - document_type: Identified document type.
            - processing_strategy: Recommended processing strategy.
            - recommended_agent: Recommended agent for processing.
            - metadata: File metadata.
            - rationale: Explanation of the routing decision.
        """
        file_path = Path(file_path)

        # 1. Identify document type
        doc_type = self._identify_document_type(file_path)

        # 2. Determine processing strategy
        strategy = self.strategy_mapping.get(doc_type, ProcessingStrategy.UNSUPPORTED)

        # 3. Recommend agent
        recommended_agent = self._recommend_agent(doc_type, strategy)

        # 4. Collect metadata
        metadata = self._collect_metadata(file_path, doc_type)

        # 5. Generate rationale
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
            f"Document routed: {file_path.name} -> {strategy.value} "
            f"(type: {doc_type.value}, Agent: {recommended_agent})"
        )

        return routing_result

    def route_query(
        self,
        question: str,
        related_files: Optional[List[str]] = None,
        intent_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Route a query to the appropriate processing pipeline.

        Args:
            question: User's question text.
            related_files: Optional list of related file paths.
            intent_result: Optional intent classification result.

        Returns:
            Routing result dictionary with strategy and agent recommendation.
        """
        # 1. Analyze related files
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

        # 2. Apply intent-based routing rules
        if intent_result:
            intent_type = getattr(intent_result, "intent", None)
            if intent_type:
                intent_value = (
                    intent_type.value
                    if hasattr(intent_type, "value")
                    else str(intent_type)
                )

                # Data analysis intent
                if intent_value == "data_analysis":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (fallback)"

                # Cost estimation intent
                elif intent_value == "cost_estimation":
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (fallback)"

                # Knowledge retrieval intent
                elif intent_value == "knowledge_retrieval":
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"

                # Document processing intent
                elif intent_value == "document_processing":
                    strategy = ProcessingStrategy.OCR_PROCESSING
                    agent = "OCRAgent"

                # Other intents
                else:
                    # Route based on available file types
                    if has_structured_data:
                        strategy = ProcessingStrategy.DATA_ANALYSIS
                        agent = "DataAnalysisAgent"
                    elif has_text_documents:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent"
                    else:
                        strategy = ProcessingStrategy.RAG_RETRIEVAL
                        agent = "RAGAgent (fallback)"
            else:
                # No specific intent, route based on file types
                if has_structured_data:
                    strategy = ProcessingStrategy.DATA_ANALYSIS
                    agent = "DataAnalysisAgent"
                else:
                    strategy = ProcessingStrategy.RAG_RETRIEVAL
                    agent = "RAGAgent"
        else:
            # No intent result, route based on file types
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
        """Identify the document type based on file extension."""
        ext = file_path.suffix.lower()

        return self.extension_mapping.get(ext, DocumentType.UNKNOWN)

    def _recommend_agent(
        self, doc_type: DocumentType, strategy: ProcessingStrategy
    ) -> str:
        """Recommend the appropriate agent based on processing strategy."""
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
        """Collect file metadata for routing decisions."""
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
                logger.warning(f"Failed to collect file metadata: {e}")

        return metadata

    def _generate_rationale(
        self,
        doc_type: DocumentType,
        strategy: ProcessingStrategy,
        metadata: Dict[str, Any],
    ) -> str:
        """Generate a human-readable rationale for the routing decision."""
        rationale_templates = {
            DocumentType.STRUCTURED_DATA: (
                f"Structured data file ({metadata.get('extension', 'unknown')}), "
                "routed to Data Analysis Agent for statistical analysis and visualization."
            ),
            DocumentType.TEXT_DOCUMENT: (
                f"Text document ({metadata.get('extension', 'unknown')}), "
                "routed to RAG pipeline for chunking, embedding, and retrieval-based Q&A."
            ),
            DocumentType.IMAGE_DOCUMENT: (
                f"Image file ({metadata.get('extension', 'unknown')}), "
                "will be processed with OCR first, then fed into RAG pipeline."
            ),
            DocumentType.CODE_FILE: (
                f"Code file ({metadata.get('extension', 'unknown')}), "
                "routed to RAG pipeline for code-aware retrieval."
            ),
            DocumentType.UNKNOWN: (
                f"Unknown file type ({metadata.get('extension', 'unknown')}), "
                "format not supported."
            ),
        }

        return rationale_templates.get(doc_type, "No rationale available.")

    def _generate_query_rationale(
        self,
        question: str,
        strategy: ProcessingStrategy,
        has_structured_data: bool,
        has_text_documents: bool,
        intent_result: Optional[Any],
    ) -> str:
        """Generate a rationale for the query routing decision."""
        parts = []

        # Intent information
        if intent_result and hasattr(intent_result, "intent"):
            intent_value = (
                intent_result.intent.value
                if hasattr(intent_result.intent, "value")
                else str(intent_result.intent)
            )
            confidence = getattr(intent_result, "confidence", 0)
            parts.append(f"Intent: {intent_value} (confidence: {confidence:.2f})")

        # File type context
        if has_structured_data:
            parts.append("Structured data files detected")
        if has_text_documents:
            parts.append("Text documents detected")

        # Routing decision
        if strategy == ProcessingStrategy.DATA_ANALYSIS:
            parts.append("-> Routed to Data Analysis Agent")
        elif strategy == ProcessingStrategy.RAG_RETRIEVAL:
            parts.append("-> Routed to RAG pipeline")
        elif strategy == ProcessingStrategy.OCR_PROCESSING:
            parts.append("-> Routed to OCR Agent")

        return "; ".join(parts) if parts else "Default routing applied"

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get a dictionary of supported formats grouped by document type."""
        formats = {}

        for ext, doc_type in self.extension_mapping.items():
            type_name = doc_type.value
            if type_name not in formats:
                formats[type_name] = []
            formats[type_name].append(ext)

        return formats


# Global singleton instance
smart_document_router = SmartDocumentRouter()
