"""
TDI Round 12 — Reproduction tests for 7 P1 bugs.

All bugs are EN-placeholder remnants in user-facing strings.
Tests use AST/source inspection since many modules crash on import.
"""

import ast
import os
import re

import pytest

# ─── Paths ───────────────────────────────────────────────────────────────────

_ROUTING_DECISION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "backend",
    "services",
    "routing_decision.py",
)

_INTENT_WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "backend",
    "services",
    "intent_classification",
    "intent_workflow.py",
)

_DATA_ANALYSIS_AGENT_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "backend",
    "services",
    "data_analysis",
    "data_analysis_agent.py",
)


def _read_source(path: str) -> str:
    with open(os.path.normpath(path)) as f:
        return f.read()


def _extract_string_literals(source: str) -> list[str]:
    """Extract all string literals from Python source code."""
    tree = ast.parse(source)
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
    return strings


# ─── R12-01: keyword_intent_mapping uses real English keywords ───────────────


class TestR12_01_KeywordIntentMapping:
    """BUG R12-01: keyword_intent_mapping had 'EN' literal keys that would
    never match any real user query."""

    def test_mapping_keys_are_real_english_words(self):
        source = _read_source(_ROUTING_DECISION_PATH)
        tree = ast.parse(source)

        # Find the keyword_intent_mapping dict
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "keyword_intent_mapping"
                    ):
                        assert isinstance(
                            node.value, ast.Dict
                        ), "keyword_intent_mapping should be a dict literal"
                        keys = []
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                keys.append(key.value)
                        assert (
                            len(keys) >= 5
                        ), f"Expected at least 5 mapping keys, got {len(keys)}"
                        en_keys = [k for k in keys if k.strip().upper() == "EN"]
                        assert (
                            len(en_keys) == 0
                        ), f"Found 'EN' placeholder keys: {en_keys}"
                        # Verify at least some expected keywords exist
                        key_set = set(k.lower() for k in keys)
                        expected = {"analyze", "cost", "document", "code"}
                        found = expected & key_set
                        assert (
                            len(found) >= 3
                        ), f"Expected real keywords like {expected}, got {key_set}"
                        return
        pytest.fail("Could not find keyword_intent_mapping assignment")


# ─── R12-02: clarification_templates use real English questions ──────────────


class TestR12_02_ClarificationTemplates:
    """BUG R12-02: clarification_templates had 'EN?' gibberish instead of
    real English clarification questions."""

    def test_templates_contain_real_questions(self):
        source = _read_source(_ROUTING_DECISION_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "clarification_templates"
                    ):
                        assert isinstance(node.value, ast.Dict)
                        # Collect all string values from the template lists
                        all_questions = []
                        for val in node.value.values:
                            if isinstance(val, ast.List):
                                for elt in val.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(
                                        elt.value, str
                                    ):
                                        all_questions.append(elt.value)
                        assert (
                            len(all_questions) >= 5
                        ), f"Expected at least 5 clarification questions, got {len(all_questions)}"
                        # No question should be just EN gibberish
                        for q in all_questions:
                            words = [
                                w
                                for w in q.split()
                                if len(w) >= 3 and w.upper() != "EN"
                            ]
                            assert (
                                len(words) >= 3
                            ), f"Clarification question looks like EN placeholder: '{q}'"
                        return
        pytest.fail("Could not find clarification_templates assignment")


# ─── R12-03: intent_workflow clarification messages are real English ─────────


class TestR12_03_IntentWorkflowClarification:
    """BUG R12-03: _generate_clarification_with_prompt and
    _generate_default_clarification produced 'EN.EN:' gibberish."""

    def test_clarification_with_prompt_produces_english(self):
        source = _read_source(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_clarification_with_prompt":
                    # Extract all string literals in this function
                    fn_strings = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            fn_strings.append(child.value)
                    # Check user-visible strings (>10 chars) for whole-word EN placeholders
                    visible = [s for s in fn_strings if len(s.strip()) > 10]
                    for s in visible:
                        # Count standalone "EN" words (not substrings like "intents")
                        en_words = len(re.findall(r"\bEN\b", s))
                        total_words = max(len(s.split()), 1)
                        assert (
                            en_words / total_words < 0.3
                        ), f"String looks like EN placeholder in _generate_clarification_with_prompt: '{s}'"
                    # Must contain real English phrases
                    all_text = " ".join(fn_strings)
                    real_words = [
                        w for w in all_text.split() if len(w) >= 4 and w.upper() != "EN"
                    ]
                    assert (
                        len(real_words) >= 5
                    ), f"Expected real English in clarification prompt, got: {all_text[:200]}"
                    return
        pytest.fail("Could not find _generate_clarification_with_prompt method")

    def test_default_clarification_produces_english(self):
        source = _read_source(_INTENT_WORKFLOW_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_default_clarification":
                    fn_strings = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            fn_strings.append(child.value)
                    visible = [s for s in fn_strings if len(s.strip()) > 10]
                    for s in visible:
                        en_words = len(re.findall(r"\bEN\b", s))
                        total_words = max(len(s.split()), 1)
                        assert (
                            en_words / total_words < 0.3
                        ), f"String looks like EN placeholder in _generate_default_clarification: '{s}'"
                    all_text = " ".join(fn_strings)
                    real_words = [
                        w for w in all_text.split() if len(w) >= 4 and w.upper() != "EN"
                    ]
                    assert (
                        len(real_words) >= 5
                    ), f"Expected real English in default clarification, got: {all_text[:200]}"
                    return
        pytest.fail("Could not find _generate_default_clarification method")


# ─── R12-04: code generation prompt is real English ──────────────────────────


class TestR12_04_CodeGenerationPrompt:
    """BUG R12-04: _build_code_generation_prompt returned EN gibberish
    instead of a real English LLM prompt."""

    def test_prompt_contains_real_instructions(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_build_code_generation_prompt":
                    fn_strings = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            fn_strings.append(child.value)
                    # The prompt should contain key instruction words
                    all_text = " ".join(fn_strings).lower()
                    expected_terms = ["python", "data", "pandas", "print"]
                    found = [t for t in expected_terms if t in all_text]
                    assert (
                        len(found) >= 3
                    ), f"Prompt missing expected terms {expected_terms}; found {found}"
                    # No dominant EN gibberish
                    for s in fn_strings:
                        if len(s.strip()) > 10:
                            en_count = s.upper().count("EN")
                            word_count = max(len(s.split()), 1)
                            assert (
                                en_count / word_count < 0.3
                            ), f"Prompt string looks like EN placeholder: '{s[:100]}'"
                    return
        pytest.fail("Could not find _build_code_generation_prompt method")


# ─── R12-05: Template output labels are real English ─────────────────────────


class TestR12_05_TemplateOutputLabels:
    """BUG R12-05: Template methods (_template_count, _template_percentage)
    had 'EN:' in their print() output labels."""

    def test_template_count_has_english_labels(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_template_count":
                    fn_source = ast.get_source_segment(source, node)
                    if fn_source is None:
                        # Fallback: extract by line numbers
                        lines = source.splitlines()
                        fn_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    # Should not contain 'EN:' or 'EN"' output labels
                    assert (
                        "'EN:" not in fn_source and '"EN:' not in fn_source
                    ), f"_template_count still has EN labels"
                    # Should contain real English labels
                    assert (
                        "count" in fn_source.lower() or "total" in fn_source.lower()
                    ), "_template_count should have descriptive English labels"
                    return
        pytest.fail("Could not find _template_count method")

    def test_template_percentage_has_english_labels(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_template_percentage":
                    fn_source = ast.get_source_segment(source, node)
                    if fn_source is None:
                        lines = source.splitlines()
                        fn_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    assert (
                        "'EN:" not in fn_source and '"EN:' not in fn_source
                    ), f"_template_percentage still has EN labels"
                    assert (
                        "percentage" in fn_source.lower()
                        or "distribution" in fn_source.lower()
                    ), "_template_percentage should have descriptive English labels"
                    return
        pytest.fail("Could not find _template_percentage method")


# ─── R12-06: Template keyword matching uses real English words ───────────────


class TestR12_06_TemplateKeywordMatching:
    """BUG R12-06: _generate_template_code used 'EN' as keyword match strings,
    meaning queries like 'total count' would never match the count template."""

    def test_keyword_lists_have_no_en_placeholders(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_template_code":
                    # Find all list literals used in keyword matching
                    for child in ast.walk(node):
                        if isinstance(child, ast.List):
                            for elt in child.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    assert (
                                        elt.value.strip().upper() != "EN"
                                    ), f"Found 'EN' placeholder in keyword list: {[e.value for e in child.elts if isinstance(e, ast.Constant)]}"
                    return
        pytest.fail("Could not find _generate_template_code method")

    def test_template_routing_covers_key_words(self):
        """Verify real keywords like 'total', 'maximum', 'minimum' are mapped."""
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_template_code":
                    # Collect all string constants in keyword lists
                    all_keywords = set()
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            all_keywords.add(child.value.lower())
                    # Check that real English synonyms are present
                    assert (
                        "avg" in all_keywords or "average" in all_keywords
                    ), "Missing average-related keywords"
                    assert (
                        "maximum" in all_keywords or "largest" in all_keywords
                    ), "Missing max-related keywords"
                    assert (
                        "minimum" in all_keywords or "smallest" in all_keywords
                    ), "Missing min-related keywords"
                    assert (
                        "total" in all_keywords or "number of" in all_keywords
                    ), "Missing count-related keywords"
                    assert (
                        "proportion" in all_keywords or "ratio" in all_keywords
                    ), "Missing percentage-related keywords"
                    return
        pytest.fail("Could not find _generate_template_code method")


# ─── R12-07: Fallback answer and parse output use real English ───────────────


class TestR12_07_FallbackAndParseOutput:
    """Additional EN-placeholder fixes in _parse_execution_output and
    _generate_fallback_answer."""

    def test_parse_output_has_english_messages(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_parse_execution_output":
                    fn_strings = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            fn_strings.append(child.value)
                    # Filter to user-visible strings (>5 chars)
                    visible = [s for s in fn_strings if len(s.strip()) > 5]
                    for s in visible:
                        en_tokens = sum(
                            1 for w in s.split() if w.strip().upper() == "EN"
                        )
                        total_words = max(len(s.split()), 1)
                        assert (
                            en_tokens / total_words < 0.3
                        ), f"_parse_execution_output has EN placeholder: '{s}'"
                    return
        pytest.fail("Could not find _parse_execution_output method")

    def test_fallback_answer_has_english_messages(self):
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_fallback_answer":
                    fn_strings = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(
                            child.value, str
                        ):
                            fn_strings.append(child.value)
                    # Check user-visible strings (>10 chars, excludes keyword matches)
                    visible = [s for s in fn_strings if len(s.strip()) > 10]
                    for s in visible:
                        en_tokens = sum(
                            1 for w in s.split() if w.strip().upper() == "EN"
                        )
                        total_words = max(len(s.split()), 1)
                        assert (
                            en_tokens / total_words < 0.3
                        ), f"_generate_fallback_answer has EN placeholder: '{s}'"
                    # Should contain real English response text
                    all_text = " ".join(visible).lower()
                    assert (
                        "dataset" in all_text
                        or "column" in all_text
                        or "analysis" in all_text
                    ), "Fallback answer should contain data-analysis related English"
                    return
        pytest.fail("Could not find _generate_fallback_answer method")

    def test_fallback_keyword_matching_no_en_literals(self):
        """Keyword matching in _generate_fallback_answer should not use 'EN' as keywords."""
        source = _read_source(_DATA_ANALYSIS_AGENT_PATH)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "_generate_fallback_answer":
                    # Find all `in question_lower` comparisons
                    for child in ast.walk(node):
                        if isinstance(child, ast.Compare):
                            for comparator in child.comparators:
                                if (
                                    isinstance(comparator, ast.Name)
                                    and comparator.id == "question_lower"
                                ):
                                    # The left side should be a real keyword, not "EN"
                                    if isinstance(
                                        child.left, ast.Constant
                                    ) and isinstance(child.left.value, str):
                                        assert (
                                            child.left.value.strip().upper() != "EN"
                                        ), f"Found 'EN' placeholder in fallback keyword matching"
                    return
        pytest.fail("Could not find _generate_fallback_answer method")
