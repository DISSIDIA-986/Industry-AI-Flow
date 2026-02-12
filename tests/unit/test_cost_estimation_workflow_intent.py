from __future__ import annotations

from backend.services.workflows.nodes.intent_node import _heuristic_intent
from backend.services.workflows.prompting.template_selector import TemplateSelector


def test_cost_estimation_keywords_route_to_cost_estimation_intent() -> None:
    assert _heuristic_intent("Please estimate construction cost overrun for this project") == "cost_estimation"
    assert _heuristic_intent("请帮我做一个建筑预算和成本估算") == "cost_estimation"


def test_template_selector_supports_cost_estimation_intent() -> None:
    selector = TemplateSelector()
    name, category = selector.select({"intent": "cost_estimation"})

    assert name == "code_exec_data_analysis_explainer"
    assert category == "analysis"
