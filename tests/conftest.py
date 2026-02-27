"""
pytest configuration for Industry AI Flow tests.

This file provides common fixtures and configuration for all test suites.
"""

import importlib
import importlib.util
import os
from pathlib import Path

import pytest

# Keep API-key auth enabled by default in runtime, but off in tests unless explicitly set.
os.environ.setdefault("REQUIRE_API_KEY", "false")


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_documents_dir(test_data_dir):
    """Fixture providing path to sample documents directory."""
    return test_data_dir / "documents"


@pytest.fixture(scope="session")
def test_queries_dir(test_data_dir):
    """Fixture providing path to test queries directory."""
    return test_data_dir / "queries"


@pytest.fixture(scope="session")
def expected_results_dir(test_data_dir):
    """Fixture providing path to expected results directory."""
    return test_data_dir / "expected_results"


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "This is a mock response for testing purposes.",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "model": "mock-model",
        "finish_reason": "stop",
    }


@pytest.fixture
def sample_document():
    """Sample document content for testing."""
    return {
        "title": "Test Document",
        "content": "This is a test document for testing the document processing pipeline.",
        "source": "test",
        "metadata": {"type": "text", "size": 1000},
    }


@pytest.fixture
def sample_query():
    """Sample query for testing RAG functionality."""
    return {
        "text": "What is machine learning?",
        "intent": "knowledge_retrieval",
        "context": "test context",
    }


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "cache: mark cache behavior/integration tests")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "legacy_chinese: historical Chinese-language or Chinese-font suites"
    )


def pytest_collection_modifyitems(config, items):
    """Tag Chinese-specific historical tests for optional exclusion."""
    for item in items:
        node = item.nodeid.lower()
        if "chinese" in node or "matplotlib_chinese" in node:
            item.add_marker(pytest.mark.legacy_chinese)


# Custom markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow


def _missing_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is None
    except Exception:
        return True


def _missing_attrs(module_name: str, attrs: list[str]) -> bool:
    if _missing_module(module_name):
        return True
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return True
    return any(not hasattr(module, attr) for attr in attrs)


collect_ignore: list[str] = []

# Optional-heavy tests: skip when external dependencies are unavailable in this env.
if _missing_module("matplotlib"):
    collect_ignore.extend(
        [
            "integration/test_complete_analysis.py",
            "integration/test_simple.py",
            "performance/test_temp_analysis.py",
        ]
    )

if _missing_module("sklearn"):
    collect_ignore.append("performance/test_advanced_analysis.py")

if _missing_module("aiohttp"):
    collect_ignore.append("unit/test_frontend_chat_interface.py")

if _missing_module("langchain_anthropic"):
    collect_ignore.append("integration/llm/test_zhipu_integration.py")

if _missing_module("langchain_ollama"):
    collect_ignore.append("unit/test_langchain.py")

# Legacy/removed module compatibility: skip tests that target removed modules.
if _missing_module("backend.services.answer_generator"):
    collect_ignore.append("unit/test_answer_generation_quality.py")

if _missing_module("backend.services.intent_classifier"):
    collect_ignore.append("unit/test_intent_classification_system.py")

# Legacy test suites that target removed llm_integration contracts.
if _missing_attrs(
    "backend.services.llm_integration.types",
    ["LLMUsage", "DispatchResult", "LLMProvider"],
):
    collect_ignore.extend(
        [
            "integration/llm/test_llm_dispatch_integration.py",
            "unit/llm_integration/test_dispatch_service.py",
        ]
    )

if _missing_attrs("backend.services.llm_integration.cost_tracker", ["LLMCost"]):
    collect_ignore.append("unit/llm_integration/test_cost_tracker.py")

# Legacy prompt-manager suite targets pre-refactor contracts (template/version ints, async internals).
if not _missing_module("backend.services.prompt_manager"):
    try:
        prompt_manager_mod = importlib.import_module("backend.services.prompt_manager")
        prompt_info_fields = getattr(prompt_manager_mod.PromptInfo, "__dataclass_fields__", {})
        if "content" in prompt_info_fields and "template" not in prompt_info_fields:
            collect_ignore.append("unit/test_prompt_manager.py")
    except Exception:
        collect_ignore.append("unit/test_prompt_manager.py")

# Legacy security suite conflicts with current conservative redaction contract.
# Canonical coverage lives in unit/test_redaction_service.py.
collect_ignore.append("unit/security/test_redaction_service.py")

# Experimental stochastic simulation (long-running/flaky) is opt-in.
if os.getenv("RUN_EXPERIMENTAL_FEEDBACK_TESTS") != "1":
    collect_ignore.append("unit/test_user_feedback_rag_impact.py")
