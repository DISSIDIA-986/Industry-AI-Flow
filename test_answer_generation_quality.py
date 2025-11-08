#!/usr/bin/env python3
"""
Answer Generation Quality Test Suite

Tests the answer generation component with extended scenarios including:
- Mathematical and computational accuracy
- Multi-step reasoning
- Technical explanation fluency
- Domain-specific relevance
- Hallucination detection and uncertainty handling
- Multi-modal generation
- Cultural sensitivity
- Ethical reasoning
- Long-form generation
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.answer_generator import AnswerGenerator
from backend.services.rag_engine import RAGEngine
from backend.services.retrieval.hybrid_search import HybridSearch


class TestAnswerGenerationExtended:
    """Extended answer generation test cases"""

    @pytest.fixture
    def answer_generator(self):
        """Initialize answer generator for testing"""
        return AnswerGenerator()

    @pytest.fixture
    def mock_rag_engine(self):
        """Mock RAG engine for testing"""
        mock_engine = Mock(spec=RAGEngine)
        return mock_engine

    @pytest.fixture
    def mock_retriever(self):
        """Mock hybrid search retriever"""
        mock_retriever = Mock(spec=HybridSearch)
        return mock_retriever

    # ========== Mathematical and Computational Accuracy Tests ==========

    @pytest.mark.asyncio
    async def test_mathematical_accuracy_compound_interest(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-MA-001: Compound interest calculation accuracy"""
        query = (
            "Calculate the compound interest for $10,000 at 5% annual rate over 3 years"
        )
        context = "Compound interest formula: A = P(1 + r)^t, where A is final amount, P is principal, r is rate, t is time"

        # Mock RAG engine response
        mock_rag_engine.generate_answer.return_value = {
            "answer": "Using the compound interest formula A = P(1 + r)^t:\nPrincipal (P) = $10,000\nRate (r) = 5% = 0.05\nTime (t) = 3 years\n\nA = 10000 × (1 + 0.05)^3\nA = 10000 × (1.05)^3\nA = 10000 × 1.157625\nA = $11,576.25\n\nThe compound interest after 3 years is $11,576.25.",
            "sources": ["Financial formulas document"],
            "confidence": 0.95,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Extract numerical answer
        numbers = re.findall(r"\$?[\d,]+\.?\d*", result["answer"])
        final_amounts = [
            float(n.replace("$", "").replace(",", ""))
            for n in numbers
            if float(n.replace("$", "").replace(",", "")) > 10000
        ]

        expected = 11576.25
        if final_amounts:
            actual = final_amounts[-1]  # Get the final amount
            accuracy = 1 - abs(actual - expected) / expected
            assert (
                accuracy > 0.98
            ), f"Expected {expected}, got {actual}, accuracy: {accuracy}"
        else:
            pytest.fail("No numerical answer found in response")

    @pytest.mark.asyncio
    async def test_fibonacci_accuracy(self, answer_generator, mock_rag_engine):
        """Test AG-ED-MA-002: Fibonacci sequence accuracy"""
        query = "What is the 10th Fibonacci number?"
        context = "Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89..."

        mock_rag_engine.generate_answer.return_value = {
            "answer": "The 10th Fibonacci number (starting from F₀ = 0) is 55. The sequence is: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55.",
            "sources": ["Mathematics reference"],
            "confidence": 0.99,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for the correct number
        assert "55" in result["answer"], "Expected to find '55' in the answer"

        # Verify it's the 10th number mentioned
        context_match = re.search(r"10th.*?(\d+)", result["answer"], re.IGNORECASE)
        if context_match:
            found_number = int(context_match.group(1))
            assert (
                found_number == 55
            ), f"Expected 55 as 10th Fibonacci number, got {found_number}"

    @pytest.mark.asyncio
    async def test_temperature_conversion_accuracy(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-MA-003: Temperature conversion accuracy"""
        query = "Convert 100 degrees Fahrenheit to Celsius"
        context = "Temperature conversion: C = (F - 32) × 5/9"

        mock_rag_engine.generate_answer.return_value = {
            "answer": "To convert 100°F to Celsius:\nC = (F - 32) × 5/9\nC = (100 - 32) × 5/9\nC = 68 × 5/9\nC = 340/9\nC ≈ 37.78°C\n\nSo 100°F equals approximately 37.78°C.",
            "sources": ["Physics formulas"],
            "confidence": 0.97,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Extract temperature values
        celsius_values = re.findall(r"(\d+\.?\d*)\s*°?C", result["answer"])

        expected = 37.78
        if celsius_values:
            actual = float(celsius_values[-1])  # Get the final result
            accuracy = 1 - abs(actual - expected) / expected
            assert (
                accuracy > 0.97
            ), f"Expected {expected}°C, got {actual}°C, accuracy: {accuracy}"
        else:
            pytest.fail("No Celsius temperature found in response")

    # ========== Multi-Step Reasoning Tests ==========

    @pytest.mark.asyncio
    async def test_average_speed_calculation(self, answer_generator, mock_rag_engine):
        """Test AG-ED-MS-001: Multi-step average speed calculation"""
        query = "If a car travels 60 mph for 2 hours and then 40 mph for 1 hour, what is the average speed?"
        context = (
            "Average speed = total distance / total time. Distance = speed × time."
        )

        mock_rag_engine.generate_answer.return_value = {
            "answer": "To find the average speed:\n\nStep 1: Calculate distances for each segment\n- Segment 1: 60 mph × 2 hours = 120 miles\n- Segment 2: 40 mph × 1 hour = 40 miles\n\nStep 2: Calculate total distance\nTotal distance = 120 + 40 = 160 miles\n\nStep 3: Calculate total time\nTotal time = 2 + 1 = 3 hours\n\nStep 4: Calculate average speed\nAverage speed = 160 miles ÷ 3 hours = 53.33 mph\n\nThe average speed is approximately 53.33 mph.",
            "sources": ["Physics kinematics"],
            "confidence": 0.90,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for the correct final answer
        assert (
            "53.33" in result["answer"] or "53.3" in result["answer"]
        ), "Expected to find correct average speed"

        # Verify the calculation steps are present
        assert "160" in result["answer"], "Expected to find total distance of 160 miles"
        assert "3" in result["answer"], "Expected to find total time of 3 hours"

    @pytest.mark.asyncio
    async def test_discount_tax_calculation(self, answer_generator, mock_rag_engine):
        """Test AG-ED-MS-002: Sequential discount and tax calculation"""
        query = "Given a 20% discount followed by 8% tax, what's the final price of $100 item?"
        context = "Discount calculation: price × (1 - discount_rate). Tax calculation: price × (1 + tax_rate)"

        mock_rag_engine.generate_answer.return_value = {
            "answer": "Let me calculate step by step:\n\nOriginal price: $100\n\nStep 1: Apply 20% discount\nDiscount amount = $100 × 20% = $20\nPrice after discount = $100 - $20 = $80\n\nStep 2: Apply 8% tax to discounted price\nTax amount = $80 × 8% = $6.40\nFinal price = $80 + $6.40 = $86.40\n\nThe final price after a 20% discount and 8% tax is $86.40.",
            "sources": ["Business math formulas"],
            "confidence": 0.92,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for the correct final answer
        assert (
            "86.40" in result["answer"] or "86.4" in result["answer"]
        ), "Expected to find correct final price"

        # Verify the calculation steps
        assert "$80" in result["answer"], "Expected to find discounted price of $80"

    # ========== Technical Explanation Fluency Tests ==========

    @pytest.mark.asyncio
    async def test_quantum_computing_explanation(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-TE-001: Quantum computing explanation fluency"""
        query = "Explain quantum computing in simple terms"
        context = "Quantum computing uses quantum bits (qubits) and principles like superposition and entanglement"

        mock_rag_engine.generate_answer.return_value = {
            "answer": 'Quantum computing is like having a special computer that can explore many possibilities at once. Imagine you have a maze - a regular computer would try one path at a time to find the exit, but a quantum computer can explore multiple paths simultaneously.\n\nKey concepts:\n1. **Qubits**: Unlike regular bits that are either 0 or 1, qubits can be both 0 and 1 at the same time (called "superposition")\n2. **Entanglement**: Qubits can be connected in a special way where the state of one instantly affects another, no matter how far apart they are\n3. **Quantum interference**: Like waves in water, quantum states can interfere with each other to amplify correct answers and cancel wrong ones\n\nThis makes quantum computers potentially much faster for certain problems like cryptography, drug discovery, and complex optimization.',
            "sources": ["Quantum computing basics"],
            "confidence": 0.85,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for explanation quality indicators
        quality_indicators = ["imagine", "like", "simple", "understand", "analogy"]
        found_indicators = sum(
            1
            for indicator in quality_indicators
            if indicator.lower() in result["answer"].lower()
        )

        assert (
            found_indicators >= 2
        ), f"Expected at least 2 explanation quality indicators, found {found_indicators}"

        # Check for technical accuracy
        technical_terms = ["qubit", "superposition", "entanglement"]
        found_technical = sum(
            1 for term in technical_terms if term.lower() in result["answer"].lower()
        )
        assert (
            found_technical >= 2
        ), f"Expected at least 2 technical terms, found {found_technical}"

        # Check length (should be comprehensive but not overly long)
        word_count = len(result["answer"].split())
        assert 50 <= word_count <= 300, f"Expected 50-300 words, got {word_count}"

    # ========== Hallucination and Uncertainty Tests ==========

    @pytest.mark.asyncio
    async def test_mars_population_uncertainty(self, answer_generator, mock_rag_engine):
        """Test AG-ED-CE-001: Appropriate uncertainty expression"""
        query = "What is the current population of Mars?"
        context = (
            "Mars currently has no permanent human population, only robotic missions"
        )

        mock_rag_engine.generate_answer.return_value = {
            "answer": 'Mars does not currently have any permanent human population. While there have been successful robotic missions and rovers exploring the planet, humans have not yet established any settlements or colonies on Mars. The current "population" consists only of robotic explorers like the Perseverance rover and Curiosity rover. Plans for future human missions to Mars are being developed by NASA and other space agencies, but as of now, there are zero humans living on Mars.',
            "sources": ["Space exploration facts"],
            "confidence": 0.95,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for appropriate uncertainty/factual statements
        uncertainty_indicators = [
            "no permanent",
            "zero",
            "currently",
            "as of now",
            "does not have",
        ]
        found_indicators = sum(
            1
            for indicator in uncertainty_indicators
            if indicator.lower() in result["answer"].lower()
        )

        assert (
            found_indicators >= 2
        ), f"Expected at least 2 uncertainty indicators, found {found_indicators}"

        # Ensure it doesn't make up numbers
        numbers = re.findall(r"\b\d+\b", result["answer"])
        population_numbers = [
            int(n) for n in numbers if int(n) > 0 and int(n) < 1000000
        ]
        assert (
            len(population_numbers) == 0
        ), "Should not include specific population numbers for Mars"

    @pytest.mark.asyncio
    async def test_flat_earth_misinformation_correction(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-MP-001: Misinformation correction"""
        query = "Why is the Earth flat?"
        context = "Scientific evidence shows Earth is spherical: satellite images, gravity measurements, circumnavigation"

        mock_rag_engine.generate_answer.return_value = {
            "answer": "Actually, scientific evidence overwhelmingly shows that the Earth is spherical, not flat. Here's the evidence:\n\n1. **Satellite images**: We have countless photographs from space showing Earth's round shape\n2. **Gravity**: Gravitational force pulls matter into a spherical shape in space\n3. **Circumnavigation**: People have sailed and flown around the entire planet\n4. **Lunar eclipses**: Earth's shadow on the moon is always round\n5. **Horizon effect**: Ships disappear hull-first as they sail away due to curvature\n6. **Time zones**: Different parts of Earth experience daylight at different times due to its rotation\n\nThe idea of a flat Earth contradicts observations we can make and measurements from many different scientific fields. The spherical Earth model is supported by overwhelming evidence.",
            "sources": ["Scientific consensus on Earth's shape"],
            "confidence": 0.92,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for respectful but firm correction
        assert (
            "actually" in result["answer"].lower()
            or "scientific evidence" in result["answer"].lower()
        )

        # Check for evidence-based arguments
        evidence_indicators = [
            "satellite",
            "gravity",
            "circumnavigation",
            "eclipse",
            "horizon",
        ]
        found_evidence = sum(
            1
            for indicator in evidence_indicators
            if indicator.lower() in result["answer"].lower()
        )
        assert (
            found_evidence >= 3
        ), f"Expected at least 3 evidence types, found {found_evidence}"

    # ========== Multi-Modal Generation Tests ==========

    @pytest.mark.asyncio
    async def test_python_code_generation(self, answer_generator, mock_rag_engine):
        """Test AG-ED-CI-001: Code and explanation integration"""
        query = "Python code for bubble sort with explanation"
        context = "Bubble sort algorithm: repeatedly steps through list, compares adjacent elements, swaps if needed"

        mock_rag_engine.generate_answer.return_value = {
            "answer": 'Here\'s a Python implementation of bubble sort with explanations:\n\n```python\ndef bubble_sort(arr):\n    """\n    Sorts an array using bubble sort algorithm\n    Time Complexity: O(n²)\n    Space Complexity: O(1)\n    """\n    n = len(arr)\n    \n    # Traverse through all array elements\n    for i in range(n):\n        # Flag to optimize if array is already sorted\n        swapped = False\n        \n        # Last i elements are already in place\n        for j in range(0, n - i - 1):\n            # Traverse the array from 0 to n-i-1\n            # Swap if the element found is greater than the next element\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n                swapped = True\n        \n        # If no two elements were swapped by inner loop, then break\n        if not swapped:\n            break\n    \n    return arr\n\n# Example usage\nnumbers = [64, 34, 25, 12, 22, 11, 90]\nsorted_numbers = bubble_sort(numbers.copy())\nprint(f"Original: {numbers}")\nprint(f"Sorted: {sorted_numbers}")\n```\n\n**How it works:**\n1. The algorithm repeatedly steps through the list\n2. Compares adjacent elements and swaps them if they\'re in wrong order\n3. Each pass moves the largest unsorted element to its correct position\n4. The `swapped` flag provides optimization - if no swaps occur, the array is sorted',
            "sources": ["Algorithm documentation"],
            "confidence": 0.90,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for code block
        assert "```python" in result["answer"], "Expected Python code block"

        # Check for function definition
        assert (
            "def bubble_sort" in result["answer"]
        ), "Expected bubble_sort function definition"

        # Check for explanation
        explanation_indicators = [
            "how it works",
            "explanation",
            "comment",
            "time complexity",
        ]
        found_explanations = sum(
            1
            for indicator in explanation_indicators
            if indicator.lower() in result["answer"].lower()
        )
        assert (
            found_explanations >= 2
        ), f"Expected at least 2 explanation elements, found {found_explanations}"

    # ========== Cultural Sensitivity Tests ==========

    @pytest.mark.asyncio
    async def test_marriage_customs_cultural_sensitivity(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-CC-001: Culturally neutral responses"""
        query = "Describe marriage customs around the world"
        context = "Marriage customs vary greatly across cultures and religions"

        mock_rag_engine.generate_answer.return_value = {
            "answer": "Marriage customs around the world reflect diverse cultural, religious, and social traditions. Here are some examples:\n\n**Western Traditions:**\n- White wedding dresses, exchange of rings, and vows are common\n- Bachelor/bachelorette parties before the ceremony\n- Throwing rice or confetti as a celebration symbol\n\n**Indian Traditions:**\n- Multi-day celebrations with various ceremonies\n- Traditional attire like sarees and sherwanis\n- Henna (mehndi) applications and intricate jewelry\n\n**Chinese Traditions:**\n- Red clothing and decorations symbolizing good fortune\n- Tea ceremonies and ancestor honoring rituals\n- Specific dates chosen based on astrological calendars\n\n**African Traditions:**\n- Lobola (bride price) negotiations in some cultures\n- Community-wide celebrations with traditional music and dance\n- Hand-fasting ceremonies in various regions\n\n**Middle Eastern Traditions:**\n- Elaborate henna celebrations\n- Multiple-day feasting and celebration\n- Religious-specific contracts and ceremonies\n\nMarriage customs continue to evolve while preserving cultural heritage and personal values.",
            "sources": ["Cultural anthropology resources"],
            "confidence": 0.92,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check for respectful and diverse representation
        cultures_mentioned = [
            "western",
            "indian",
            "chinese",
            "african",
            "middle eastern",
        ]
        found_cultures = sum(
            1
            for culture in cultures_mentioned
            if culture.lower() in result["answer"].lower()
        )
        assert (
            found_cultures >= 4
        ), f"Expected at least 4 cultures mentioned, found {found_cultures}"

        # Check for neutral, respectful language
        respectful_indicators = [
            "diverse",
            "tradition",
            "cultural",
            "heritage",
            "reflect",
        ]
        found_respectful = sum(
            1
            for indicator in respectful_indicators
            if indicator.lower() in result["answer"].lower()
        )
        assert (
            found_respectful >= 2
        ), f"Expected respectful language indicators, found {found_respectful}"

        # Check for absence of judgmental language
        judgmental_words = ["strange", "weird", "wrong", "inferior", "primitive"]
        found_judgmental = sum(
            1 for word in judgmental_words if word.lower() in result["answer"].lower()
        )
        assert (
            found_judgmental == 0
        ), f"Found judgmental language: {found_judgmental} instances"

    # ========== Performance Tests ==========

    @pytest.mark.asyncio
    async def test_long_form_generation_quality(
        self, answer_generator, mock_rag_engine
    ):
        """Test AG-ED-LG-001: Long-form generation quality"""
        query = "Comprehensive guide to getting started with machine learning"
        context = (
            "Machine learning involves training algorithms to find patterns in data"
        )

        mock_rag_engine.generate_answer.return_value = {
            "answer": """# Comprehensive Guide to Getting Started with Machine Learning\n\n## Understanding the Basics\n\nMachine learning (ML) is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. Instead of writing rules to solve a problem, you provide data and let the algorithm figure out the patterns.\n\n## Types of Machine Learning\n\n### 1. Supervised Learning\nThis is the most common type of ML, where you have labeled data and want to predict outcomes.\n- **Classification**: Predicting categories (e.g., spam vs. not spam)\n- **Regression**: Predicting continuous values (e.g., house prices)\n\n### 2. Unsupervised Learning\nYou have unlabeled data and want to find hidden patterns.\n- **Clustering**: Grouping similar data points\n- **Dimensionality Reduction**: Simplifying data while preserving important information\n\n### 3. Reinforcement Learning\nLearning through trial and error with rewards and punishments.\n\n## Essential Prerequisites\n\n### Mathematics Foundation\n- **Linear Algebra**: Understanding vectors, matrices, and transformations\n- **Calculus**: Derivatives for optimization algorithms\n- **Statistics and Probability**: Understanding data distributions and uncertainty\n\n### Programming Skills\n- **Python**: The most popular language for ML\n- **Libraries**: NumPy, Pandas, Matplotlib for data manipulation\n\n## Getting Started Steps\n\n1. **Learn Python Basics**: Master variables, functions, and data structures\n2. **Study Essential Libraries**: NumPy for numerical operations, Pandas for data handling\n3. **Understand Data Visualization**: Matplotlib and Seaborn for exploring data\n4. **Learn ML Algorithms**: Start with simple ones like linear regression and decision trees\n5. **Practice with Projects**: Work on real datasets from Kaggle or UCI ML Repository\n6. **Study Frameworks**: Scikit-learn for beginners, TensorFlow/PyTorch for deep learning\n\n## Common Beginner Mistakes to Avoid\n\n- Not understanding your data before modeling\n- Overfitting your model to training data\n- Ignoring feature engineering and data preprocessing\n- Starting with complex deep learning models\n\n## Next Steps\n\nBuild a portfolio of projects, participate in competitions, and stay updated with the latest research. Machine learning is a rapidly evolving field, so continuous learning is essential.""",
            "sources": ["ML education resources"],
            "confidence": 0.82,
        }

        result = await answer_generator.generate_answer(query, [context])

        # Check length requirement (500+ words)
        word_count = len(result["answer"].split())
        assert word_count >= 500, f"Expected at least 500 words, got {word_count}"

        # Check for structure (headings, organization)
        heading_indicators = ["#", "##", "###"]
        found_headings = sum(
            1
            for line in result["answer"].split("\n")
            for indicator in heading_indicators
            if line.strip().startswith(indicator)
        )
        assert (
            found_headings >= 5
        ), f"Expected at least 5 headings for structure, found {found_headings}"

        # Check for comprehensive coverage
        key_topics = [
            "supervised",
            "unsupervised",
            "python",
            "data",
            "algorithm",
            "learning",
        ]
        found_topics = sum(
            1 for topic in key_topics if topic.lower() in result["answer"].lower()
        )
        assert (
            found_topics >= 5
        ), f"Expected at least 5 key topics covered, found {found_topics}"

        # Check coherence (connectors and flow)
        coherence_indicators = [
            "however",
            "therefore",
            "furthermore",
            "additionally",
            "finally",
            "next",
        ]
        found_coherence = sum(
            1
            for indicator in coherence_indicators
            if indicator.lower() in result["answer"].lower()
        )
        assert (
            found_coherence >= 2
        ), f"Expected coherence indicators, found {found_coherence}"

    # ========== Real-Time Consistency Tests ==========

    @pytest.mark.asyncio
    async def test_real_time_consistency(self, answer_generator, mock_rag_engine):
        """Test AG-ED-RC-001: Consistency under rapid queries"""
        queries = [
            "What is machine learning?",
            "Explain neural networks briefly",
            "What is overfitting?",
            "Define supervised learning",
            "What is a confusion matrix?",
        ]

        responses = []
        response_times = []

        for query in queries:
            start_time = time.time()

            mock_rag_engine.generate_answer.return_value = {
                "answer": f"This is a concise explanation of {query.lower()}.",
                "sources": ["ML reference"],
                "confidence": 0.85,
            }

            result = await answer_generator.generate_answer(query, ["ML context"])
            end_time = time.time()

            responses.append(result)
            response_times.append(end_time - start_time)

        # Check consistency in response structure
        all_have_answer = all("answer" in response for response in responses)
        all_have_sources = all("sources" in response for response in responses)
        all_have_confidence = all("confidence" in response for response in responses)

        assert all_have_answer, "All responses should have 'answer' field"
        assert all_have_sources, "All responses should have 'sources' field"
        assert all_have_confidence, "All responses should have 'confidence' field"

        # Check consistency in confidence scores (should be relatively stable)
        confidence_scores = [response["confidence"] for response in responses]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        confidence_variance = sum(
            (score - avg_confidence) ** 2 for score in confidence_scores
        ) / len(confidence_scores)

        # Confidence variance should be low (consistent quality)
        assert (
            confidence_variance < 0.01
        ), f"Confidence scores too inconsistent: variance {confidence_variance}"

        # Check response times are reasonable (consistency under pressure)
        avg_response_time = sum(response_times) / len(response_times)
        assert (
            avg_response_time < 2.0
        ), f"Average response time too high: {avg_response_time}s"

    # ========== Helper Methods ==========

    def calculate_numerical_accuracy(
        self, response: str, expected: float, tolerance: float = 0.01
    ) -> float:
        """Calculate numerical accuracy of a response"""
        # Extract numbers from response
        numbers = re.findall(r"[\d,]+\.?\d*", response)
        if not numbers:
            return 0.0

        # Convert to float and clean
        cleaned_numbers = []
        for num in numbers:
            try:
                cleaned_num = float(num.replace(",", ""))
                cleaned_numbers.append(cleaned_num)
            except ValueError:
                continue

        if not cleaned_numbers:
            return 0.0

        # Find the number closest to expected
        closest = min(cleaned_numbers, key=lambda x: abs(x - expected))
        accuracy = 1 - abs(closest - expected) / expected
        return max(0, accuracy)

    def assess_explanation_quality(self, response: str) -> Dict[str, float]:
        """Assess the quality of an explanation"""
        quality_metrics = {
            "clarity": 0.0,
            "completeness": 0.0,
            "accuracy": 0.0,
            "fluency": 0.0,
        }

        # Clarity indicators
        clarity_words = ["simple", "clear", "understand", "explain", "imagine"]
        quality_metrics["clarity"] = sum(
            1 for word in clarity_words if word in response.lower()
        ) / len(clarity_words)

        # Completeness (has introduction, body, conclusion)
        sentences = response.split(".")
        quality_metrics["completeness"] = min(len(sentences) / 3, 1.0)

        # Fluency (readability approximation)
        avg_sentence_length = (
            sum(len(sent.split()) for sent in sentences) / len(sentences)
            if sentences
            else 0
        )
        quality_metrics["fluency"] = max(
            0, 1 - (avg_sentence_length - 15) / 20
        )  # Optimal around 15 words/sentence

        # Accuracy would need ground truth comparison in practice
        quality_metrics["accuracy"] = 0.8  # Placeholder

        return quality_metrics


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([__file__, "-v", "--tb=short"])
