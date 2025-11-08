"""
pytest configuration for Industry AI Flow tests.

This file provides common fixtures and configuration for all test suites.
"""

import os
import sys
from pathlib import Path

import pytest

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


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
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Custom markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
