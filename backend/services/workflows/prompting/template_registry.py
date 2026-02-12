"""Template registry for workflow prompt selection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    category: str


DEFAULT_TEMPLATE = TemplateSpec(
    name="construction_rag_grounded_qa",
    category="rag",
)


INTENT_TO_TEMPLATE: dict[str, TemplateSpec] = {
    "knowledge_retrieval": TemplateSpec("construction_rag_grounded_qa", "rag"),
    "document_processing": TemplateSpec("drawing_ocr_structured_parse", "ocr"),
    "data_analysis": TemplateSpec("code_exec_data_analysis_explainer", "analysis"),
    "cost_estimation": TemplateSpec("code_exec_data_analysis_explainer", "analysis"),
    "code_execution": TemplateSpec("code_exec_data_analysis_explainer", "analysis"),
}
