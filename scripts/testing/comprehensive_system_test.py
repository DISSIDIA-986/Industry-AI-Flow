#!/usr/bin/env python3
"""
Comprehensive System Test for Industry AI Flow
Tests all major components: RAG, OCR, Data Analysis, Streamlit integration
Supports both Ollama and GLM-4 API
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from dotenv import load_dotenv
load_dotenv()


class TestResult:
    """Test result container"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.status = "pending"  # pending, running, passed, failed, skipped
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.error = None
        self.details = {}

    def start(self):
        self.status = "running"
        self.start_time = time.time()

    def complete(self, success: bool, details: Dict = None, error: str = None):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else 0
        self.status = "passed" if success else "failed"
        self.details = details or {}
        self.error = error

    def skip(self, reason: str):
        self.status = "skipped"
        self.error = reason


class ComprehensiveSystemTest:
    """Comprehensive test suite for the entire system"""

    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[TestResult] = []
        self.test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "TEST": "🧪"
        }.get(level, "•")
        print(f"[{timestamp}] {prefix} {message}")

    def test_environment_setup(self) -> TestResult:
        """Test 1: Verify environment configuration"""
        result = TestResult("Environment Setup")
        result.start()

        try:
            self.log("Testing environment configuration...", "TEST")

            details = {
                "postgres_host": os.getenv("POSTGRES_HOST"),
                "postgres_db": os.getenv("POSTGRES_DB"),
                "ollama_host": os.getenv("OLLAMA_HOST"),
                "ollama_model": os.getenv("OLLAMA_MODEL"),
                "zhipu_configured": bool(os.getenv("ZHIPU_API_KEY")),
                "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
                "embedding_model": os.getenv("EMBEDDING_MODEL"),
            }

            # Check required variables
            required_vars = ["POSTGRES_HOST", "POSTGRES_DB", "OLLAMA_HOST", "EMBEDDING_MODEL"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            if missing_vars:
                result.complete(False, details, f"Missing variables: {missing_vars}")
            else:
                result.complete(True, details)
                self.log("Environment configuration OK", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Environment test failed: {e}", "ERROR")

        return result

    def test_database_connection(self) -> TestResult:
        """Test 2: Verify database connectivity"""
        result = TestResult("Database Connection")
        result.start()

        try:
            self.log("Testing database connection...", "TEST")

            from backend.services.vectorstore import VectorStore

            vectorstore = VectorStore()
            doc_count = vectorstore.get_document_count()
            chunk_count = vectorstore.get_chunk_count()

            details = {
                "document_count": doc_count,
                "chunk_count": chunk_count,
                "connection": "success"
            }

            result.complete(True, details)
            self.log(f"Database OK - {doc_count} docs, {chunk_count} chunks", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Database connection failed: {e}", "ERROR")

        return result

    def test_ollama_service(self) -> TestResult:
        """Test 3: Verify Ollama service"""
        result = TestResult("Ollama Service")
        result.start()

        try:
            self.log("Testing Ollama service...", "TEST")

            from backend.services.ollama_client import OllamaClient

            client = OllamaClient()
            test_prompt = "Say 'test successful' in 3 words."

            start = time.time()
            response = client.generate(test_prompt)
            latency = time.time() - start

            details = {
                "model": os.getenv("OLLAMA_MODEL"),
                "response_length": len(response),
                "latency_seconds": latency,
                "sample_response": response[:100]
            }

            result.complete(True, details)
            self.log(f"Ollama OK - latency: {latency:.2f}s", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Ollama test failed: {e}", "ERROR")

        return result

    def test_glm4_service(self) -> TestResult:
        """Test 4: Verify GLM-4 API service"""
        result = TestResult("GLM-4 API Service")
        result.start()

        try:
            if not os.getenv("ZHIPU_API_KEY"):
                result.skip("GLM-4 API key not configured")
                self.log("GLM-4 test skipped - no API key", "WARNING")
                return result

            self.log("Testing GLM-4 API service...", "TEST")

            # Temporarily switch to zhipu provider
            original_provider = os.getenv("LLM_PROVIDER")
            os.environ["LLM_PROVIDER"] = "zhipu"

            from backend.services.ollama_client import OllamaClient

            client = OllamaClient()
            test_prompt = "Say 'test successful' in 3 words."

            start = time.time()
            response = client.generate(test_prompt)
            latency = time.time() - start

            # Restore original provider
            os.environ["LLM_PROVIDER"] = original_provider or "ollama"

            details = {
                "model": os.getenv("ZHIPU_MODEL"),
                "response_length": len(response),
                "latency_seconds": latency,
                "sample_response": response[:100]
            }

            result.complete(True, details)
            self.log(f"GLM-4 OK - latency: {latency:.2f}s", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"GLM-4 test failed: {e}", "ERROR")

        return result

    def test_rag_engine(self) -> TestResult:
        """Test 5: Test RAG engine with sample queries"""
        result = TestResult("RAG Engine")
        result.start()

        try:
            self.log("Testing RAG engine...", "TEST")

            from backend.services.rag_engine import SimpleRAG

            rag = SimpleRAG(use_hybrid_search=True, use_reranker=True)

            test_questions = [
                "What is a RAG system?",
                "How does vector search work?",
                "What is LangChain?"
            ]

            query_results = []
            total_time = 0

            for question in test_questions:
                start = time.time()
                response = rag.query(question, top_k=3)
                latency = time.time() - start
                total_time += latency

                query_results.append({
                    "question": question,
                    "latency": latency,
                    "answer_length": len(response.get("answer", "")),
                    "sources_count": len(response.get("sources", []))
                })

            details = {
                "queries_tested": len(test_questions),
                "avg_latency": total_time / len(test_questions),
                "total_time": total_time,
                "results": query_results
            }

            result.complete(True, details)
            self.log(f"RAG OK - avg latency: {details['avg_latency']:.2f}s", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"RAG engine test failed: {e}", "ERROR")

        return result

    def test_ocr_functionality(self) -> TestResult:
        """Test 6: Test OCR document processing"""
        result = TestResult("OCR Processing")
        result.start()

        try:
            self.log("Testing OCR functionality...", "TEST")

            from backend.services.document_loader import EnhancedDocumentLoader

            loader = EnhancedDocumentLoader(use_ocr=True)

            # Test with text file (fallback)
            test_files = []
            samples_dir = Path("samples")

            if samples_dir.exists():
                # Look for test files
                for ext in ['.txt', '.pdf', '.png', '.jpg']:
                    test_files.extend(list(samples_dir.glob(f"*{ext}")))

            if not test_files:
                result.skip("No test files found in samples/ directory")
                self.log("OCR test skipped - no test files", "WARNING")
                return result

            processed_files = []
            for test_file in test_files[:3]:  # Test first 3 files
                try:
                    content = loader.load_document(str(test_file))
                    processed_files.append({
                        "filename": test_file.name,
                        "content_length": len(content),
                        "status": "success"
                    })
                except Exception as e:
                    processed_files.append({
                        "filename": test_file.name,
                        "status": "failed",
                        "error": str(e)
                    })

            details = {
                "files_tested": len(processed_files),
                "ocr_lang": os.getenv("OCR_LANG", "en"),
                "results": processed_files
            }

            success_count = sum(1 for f in processed_files if f["status"] == "success")

            if success_count > 0:
                result.complete(True, details)
                self.log(f"OCR OK - {success_count}/{len(processed_files)} files processed", "SUCCESS")
            else:
                result.complete(False, details, "No files processed successfully")
                self.log("OCR test failed - no successful processing", "ERROR")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"OCR test failed: {e}", "ERROR")

        return result

    def test_document_import(self) -> TestResult:
        """Test 7: Test document import workflow"""
        result = TestResult("Document Import")
        result.start()

        try:
            self.log("Testing document import workflow...", "TEST")

            from backend.services.document_loader import EnhancedDocumentLoader
            from backend.services.chunker import chunk_text
            from backend.services.embedder import embed_texts
            from backend.services.vectorstore import VectorStore

            # Use existing sample files
            samples_dir = Path("samples")
            if not samples_dir.exists() or not list(samples_dir.glob("*.txt")):
                result.skip("No sample documents found")
                self.log("Document import skipped - no samples", "WARNING")
                return result

            loader = EnhancedDocumentLoader()
            vectorstore = VectorStore()

            test_file = list(samples_dir.glob("*.txt"))[0]

            # Load document
            content = loader.load_document(str(test_file))

            # Chunk
            chunks = chunk_text(content, chunk_size=500, chunk_overlap=50)

            # Embed
            embeddings = embed_texts([chunk["content"] for chunk in chunks])

            details = {
                "test_file": test_file.name,
                "content_length": len(content),
                "chunk_count": len(chunks),
                "embedding_dim": len(embeddings[0]) if embeddings else 0,
                "import_successful": True
            }

            result.complete(True, details)
            self.log(f"Document import OK - {len(chunks)} chunks", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Document import failed: {e}", "ERROR")

        return result

    def test_hybrid_search(self) -> TestResult:
        """Test 8: Test hybrid search (BM25 + Vector)"""
        result = TestResult("Hybrid Search")
        result.start()

        try:
            self.log("Testing hybrid search...", "TEST")

            from backend.services.retrieval.hybrid_search import HybridRetriever
            from backend.services.vectorstore import VectorStore

            vectorstore = VectorStore()
            retriever = HybridRetriever(vectorstore)

            test_query = "RAG system architecture"

            # Test different weight combinations
            search_tests = [
                {"vector_weight": 1.0, "bm25_weight": 0.0, "name": "pure_vector"},
                {"vector_weight": 0.0, "bm25_weight": 1.0, "name": "pure_bm25"},
                {"vector_weight": 0.7, "bm25_weight": 0.3, "name": "hybrid"},
            ]

            search_results = []
            for test in search_tests:
                start = time.time()
                results = retriever.search(
                    query=test_query,
                    top_k=5,
                    vector_weight=test["vector_weight"],
                    bm25_weight=test["bm25_weight"]
                )
                latency = time.time() - start

                search_results.append({
                    "mode": test["name"],
                    "results_count": len(results),
                    "latency": latency
                })

            details = {
                "query": test_query,
                "search_results": search_results
            }

            result.complete(True, details)
            self.log("Hybrid search OK", "SUCCESS")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Hybrid search test failed: {e}", "ERROR")

        return result

    def test_data_analysis_service(self) -> TestResult:
        """Test 9: Test data analysis capabilities"""
        result = TestResult("Data Analysis Service")
        result.start()

        try:
            self.log("Testing data analysis service...", "TEST")

            # Check if data analysis service exists
            try:
                from backend.services.code_executor import CodeExecutor

                executor = CodeExecutor()

                # Test simple data analysis code
                test_code = """
import pandas as pd
import numpy as np

data = {'A': [1, 2, 3], 'B': [4, 5, 6]}
df = pd.DataFrame(data)
result = df.describe().to_dict()
print(result)
"""

                exec_result = executor.execute_code(test_code, language="python")

                details = {
                    "execution_status": exec_result.get("status"),
                    "has_output": bool(exec_result.get("output")),
                    "has_error": bool(exec_result.get("error"))
                }

                if exec_result.get("status") == "success":
                    result.complete(True, details)
                    self.log("Data analysis service OK", "SUCCESS")
                else:
                    result.complete(False, details, exec_result.get("error"))
                    self.log("Data analysis execution failed", "ERROR")

            except ImportError:
                result.skip("Code executor service not found")
                self.log("Data analysis test skipped - service not available", "WARNING")

        except Exception as e:
            result.complete(False, error=str(e))
            self.log(f"Data analysis test failed: {e}", "ERROR")

        return result

    def run_all_tests(self):
        """Run all tests and generate report"""
        self.log("=" * 60, "INFO")
        self.log("Starting Comprehensive System Test", "INFO")
        self.log("=" * 60, "INFO")
        print()

        # Run tests
        self.results.append(self.test_environment_setup())
        self.results.append(self.test_database_connection())
        self.results.append(self.test_ollama_service())
        self.results.append(self.test_glm4_service())
        self.results.append(self.test_rag_engine())
        self.results.append(self.test_ocr_functionality())
        self.results.append(self.test_document_import())
        self.results.append(self.test_hybrid_search())
        self.results.append(self.test_data_analysis_service())

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""
        print()
        self.log("=" * 60, "INFO")
        self.log("Test Summary", "INFO")
        self.log("=" * 60, "INFO")

        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        print()
        self.log(f"Total Tests: {total}", "INFO")
        self.log(f"Passed: {passed}", "SUCCESS")
        if failed > 0:
            self.log(f"Failed: {failed}", "ERROR")
        if skipped > 0:
            self.log(f"Skipped: {skipped}", "WARNING")

        # Success rate
        if total - skipped > 0:
            success_rate = (passed / (total - skipped)) * 100
            self.log(f"Success Rate: {success_rate:.1f}%", "INFO")

        print()
        self.log("Test Details:", "INFO")
        print()

        for r in self.results:
            status_icon = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(r.status, "•")

            print(f"{status_icon} {r.test_name}: {r.status.upper()}")
            if r.duration > 0:
                print(f"   Duration: {r.duration:.2f}s")
            if r.error:
                print(f"   Error: {r.error}")
            if r.details:
                for key, value in r.details.items():
                    if not isinstance(value, (list, dict)):
                        print(f"   {key}: {value}")
            print()

        # Save detailed JSON report
        report_file = self.output_dir / f"test_report_{self.test_timestamp}.json"
        report_data = {
            "timestamp": self.test_timestamp,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": f"{success_rate:.1f}%" if total - skipped > 0 else "N/A"
            },
            "tests": [
                {
                    "name": r.test_name,
                    "status": r.status,
                    "duration": r.duration,
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self.log(f"Detailed report saved to: {report_file}", "INFO")

        # Generate issues report
        if failed > 0:
            self.generate_issues_report()

    def generate_issues_report(self):
        """Generate report of issues found"""
        issues_file = self.output_dir / f"issues_{self.test_timestamp}.md"

        with open(issues_file, 'w') as f:
            f.write("# Issues Found During System Testing\n\n")
            f.write(f"**Test Run**: {self.test_timestamp}\n\n")

            for r in self.results:
                if r.status == "failed":
                    f.write(f"## {r.test_name}\n\n")
                    f.write(f"**Status**: ❌ FAILED\n\n")
                    if r.error:
                        f.write(f"**Error**:\n```\n{r.error}\n```\n\n")
                    if r.details:
                        f.write(f"**Details**:\n```json\n{json.dumps(r.details, indent=2)}\n```\n\n")
                    f.write("---\n\n")

        self.log(f"Issues report saved to: {issues_file}", "WARNING")


if __name__ == "__main__":
    # Create test instance
    tester = ComprehensiveSystemTest()

    # Run all tests
    tester.run_all_tests()
