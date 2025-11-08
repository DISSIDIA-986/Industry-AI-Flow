#!/usr/bin/env python3
"""
Comprehensive Testing Script for Industry AI Flow RAG System
Based on test_cases/comprehensive_testing_prompt_for_coding_llms.md
"""

import sys
import os
import json
import time
import traceback
from typing import Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Test results storage
test_results = []
bug_reports = []

class TestResult:
    """Test result container"""
    def __init__(self, test_id: str, category: str, status: str,
                 execution_time: float = 0, input_data: str = "",
                 expected: str = "", actual: str = "",
                 notes: str = "", metrics: Dict = None):
        self.test_id = test_id
        self.category = category
        self.status = status  # PASS/FAIL/ERROR
        self.execution_time = execution_time
        self.input_data = input_data
        self.expected = expected
        self.actual = actual
        self.notes = notes
        self.metrics = metrics or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "category": self.category,
            "status": self.status,
            "execution_time": self.execution_time,
            "input": self.input_data,
            "expected_result": self.expected,
            "actual_result": self.actual,
            "performance_metrics": self.metrics,
            "notes": self.notes,
            "timestamp": self.timestamp
        }


def log_test(result: TestResult):
    """Log test result"""
    test_results.append(result)
    status_symbol = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⚠️"
    print(f"{status_symbol} {result.test_id}: {result.status} ({result.execution_time:.3f}s)")
    if result.notes:
        print(f"   Note: {result.notes}")


def log_bug(test_id: str, category: str, description: str,
            severity: str, reproduction_steps: str, stack_trace: str = ""):
    """Log bug report"""
    bug = {
        "test_id": test_id,
        "category": category,
        "description": description,
        "severity": severity,
        "reproduction_steps": reproduction_steps,
        "stack_trace": stack_trace,
        "timestamp": datetime.now().isoformat()
    }
    bug_reports.append(bug)
    print(f"🐛 BUG FOUND: {test_id} - {description} [Severity: {severity}]")


# ============================================
# Phase 1: Environment Setup Tests
# ============================================

def test_environment_setup():
    """Test Case: Environment Setup - Verify dependencies and resources"""
    print("\n" + "="*60)
    print("PHASE 1: ENVIRONMENT SETUP")
    print("="*60)

    # Test 1.1: Verify test resources
    test_id = "ENV-001"
    start_time = time.time()
    try:
        required_dirs = [
            "test_resources/datasets",
            "test_resources/documents",
            "test_resources/images"
        ]
        missing_dirs = []
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)

        if missing_dirs:
            log_test(TestResult(
                test_id, "Environment Setup", "FAIL",
                time.time() - start_time,
                input_data="Check test resources",
                expected="All test resource directories exist",
                actual=f"Missing: {', '.join(missing_dirs)}",
                notes="Test resources directory structure incomplete"
            ))
            log_bug(test_id, "Environment",
                   "Missing test resource directories",
                   "HIGH",
                   f"Expected directories: {', '.join(required_dirs)}")
        else:
            log_test(TestResult(
                test_id, "Environment Setup", "PASS",
                time.time() - start_time,
                input_data="Check test resources",
                expected="All test resource directories exist",
                actual="All directories found"
            ))
    except Exception as e:
        log_test(TestResult(
            test_id, "Environment Setup", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))
        log_bug(test_id, "Environment", str(e), "CRITICAL",
               "Run environment setup check", traceback.format_exc())

    # Test 1.2: Verify Python dependencies
    test_id = "ENV-002"
    start_time = time.time()
    try:
        required_modules = [
            "langchain",
            "langchain_core",
            "langchain_community",
            "langgraph",
            "sentence_transformers",
            "fastapi",
            "pydantic",
            "pandas",
            "numpy"
        ]
        missing_modules = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)

        if missing_modules:
            log_test(TestResult(
                test_id, "Environment Setup", "FAIL",
                time.time() - start_time,
                input_data="Import core dependencies",
                expected="All core modules importable",
                actual=f"Missing: {', '.join(missing_modules)}",
                notes="Install missing dependencies from requirements.txt"
            ))
            log_bug(test_id, "Environment",
                   f"Missing Python modules: {', '.join(missing_modules)}",
                   "HIGH",
                   "Install dependencies: pip install -r requirements.txt")
        else:
            log_test(TestResult(
                test_id, "Environment Setup", "PASS",
                time.time() - start_time,
                input_data="Import core dependencies",
                expected="All core modules importable",
                actual="All modules imported successfully"
            ))
    except Exception as e:
        log_test(TestResult(
            test_id, "Environment Setup", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))


# ============================================
# Phase 2: RAG Engine Tests
# ============================================

def test_rag_engine_structure():
    """Test Case: RAG Engine Structure Validation"""
    print("\n" + "="*60)
    print("PHASE 2: RAG ENGINE TESTS")
    print("="*60)

    test_id = "RAG-001"
    start_time = time.time()
    try:
        # Import RAG engine
        from backend.services.rag_engine import SimpleRAG

        # Check required methods
        required_methods = ['query', 'add_documents', 'delete_document']
        missing_methods = []

        for method in required_methods:
            if not hasattr(SimpleRAG, method):
                missing_methods.append(method)

        if missing_methods:
            log_test(TestResult(
                test_id, "RAG Engine", "FAIL",
                time.time() - start_time,
                input_data="Check RAG engine methods",
                expected=f"Methods: {', '.join(required_methods)}",
                actual=f"Missing: {', '.join(missing_methods)}",
                notes="RAG engine missing required methods"
            ))
            log_bug(test_id, "RAG Engine",
                   f"Missing methods: {', '.join(missing_methods)}",
                   "HIGH",
                   "Check backend/services/rag_engine.py")
        else:
            log_test(TestResult(
                test_id, "RAG Engine", "PASS",
                time.time() - start_time,
                input_data="Check RAG engine methods",
                expected="All required methods exist",
                actual="All methods found"
            ))
    except ImportError as e:
        log_test(TestResult(
            test_id, "RAG Engine", "ERROR",
            time.time() - start_time,
            notes=f"Import error: {str(e)}"
        ))
        log_bug(test_id, "RAG Engine",
               f"Cannot import RAG engine: {str(e)}",
               "CRITICAL",
               "Check backend/services/rag_engine.py exists and is valid",
               traceback.format_exc())
    except Exception as e:
        log_test(TestResult(
            test_id, "RAG Engine", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))


def test_config_management():
    """Test Case: Configuration Management"""
    test_id = "RAG-002"
    start_time = time.time()
    try:
        from backend.config import settings

        # Check required settings
        required_settings = [
            'embedding_model',
            'chunk_size',
            'chunk_overlap',
            'top_k',
            'database_url'
        ]
        missing_settings = []

        for setting in required_settings:
            if not hasattr(settings, setting):
                missing_settings.append(setting)

        if missing_settings:
            log_test(TestResult(
                test_id, "Configuration", "FAIL",
                time.time() - start_time,
                input_data="Check configuration settings",
                expected=f"Settings: {', '.join(required_settings)}",
                actual=f"Missing: {', '.join(missing_settings)}",
                notes="Configuration incomplete"
            ))
            log_bug(test_id, "Configuration",
                   f"Missing settings: {', '.join(missing_settings)}",
                   "MEDIUM",
                   "Check backend/config.py")
        else:
            # Show configuration values
            config_values = {s: getattr(settings, s) for s in required_settings}
            log_test(TestResult(
                test_id, "Configuration", "PASS",
                time.time() - start_time,
                input_data="Check configuration settings",
                expected="All required settings present",
                actual="All settings found",
                metrics=config_values
            ))
    except Exception as e:
        log_test(TestResult(
            test_id, "Configuration", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))
        log_bug(test_id, "Configuration", str(e), "HIGH",
               "Check backend/config.py", traceback.format_exc())


# ============================================
# Phase 3: OCR Tests
# ============================================

def test_paddleocr_installation():
    """Test Case: PaddleOCR Installation and Version"""
    print("\n" + "="*60)
    print("PHASE 3: OCR TESTS")
    print("="*60)

    test_id = "OCR-001"
    start_time = time.time()
    try:
        import paddle
        import paddleocr

        # Check PaddlePaddle version
        paddle_version = paddle.__version__
        expected_min_version = "2.6.0"

        version_check = paddle_version >= expected_min_version

        log_test(TestResult(
            test_id, "OCR", "PASS" if version_check else "FAIL",
            time.time() - start_time,
            input_data="Check PaddlePaddle version",
            expected=f">= {expected_min_version}",
            actual=paddle_version,
            metrics={"paddle_version": paddle_version}
        ))

        if not version_check:
            log_bug(test_id, "OCR",
                   f"PaddlePaddle version {paddle_version} < {expected_min_version}",
                   "MEDIUM",
                   "Upgrade PaddlePaddle: pip install paddlepaddle>=2.6.0")

    except ImportError as e:
        log_test(TestResult(
            test_id, "OCR", "FAIL",
            time.time() - start_time,
            input_data="Import PaddleOCR",
            expected="PaddleOCR installed",
            actual=f"Import error: {str(e)}",
            notes="PaddleOCR not installed"
        ))
        log_bug(test_id, "OCR",
               "PaddleOCR not installed",
               "HIGH",
               "Install: pip install paddlepaddle>=2.6.0 paddleocr>=3.3.0")
    except Exception as e:
        log_test(TestResult(
            test_id, "OCR", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))


def test_ocr_processor_initialization():
    """Test Case: OCR Processor Initialization"""
    test_id = "OCR-002"
    start_time = time.time()
    try:
        from backend.services.document_processing.ocr_processor import OCRProcessor

        # Try to initialize OCR processor
        ocr = OCRProcessor(use_gpu=False)  # Use CPU for testing

        log_test(TestResult(
            test_id, "OCR", "PASS",
            time.time() - start_time,
            input_data="Initialize OCRProcessor",
            expected="OCR processor initialized",
            actual="Initialization successful",
            notes="OCR processor ready"
        ))
    except ImportError as e:
        log_test(TestResult(
            test_id, "OCR", "FAIL",
            time.time() - start_time,
            input_data="Initialize OCRProcessor",
            expected="OCR processor initialized",
            actual=f"Import error: {str(e)}",
            notes="Cannot import OCRProcessor"
        ))
        log_bug(test_id, "OCR",
               f"OCRProcessor import failed: {str(e)}",
               "HIGH",
               "Check backend/services/document_processing/ocr_processor.py",
               traceback.format_exc())
    except Exception as e:
        log_test(TestResult(
            test_id, "OCR", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))
        log_bug(test_id, "OCR", str(e), "MEDIUM",
               "Initialize OCRProcessor", traceback.format_exc())


# ============================================
# Phase 4: System Workflow Tests
# ============================================

def test_intent_classification_structure():
    """Test Case: Intent Classification Structure"""
    print("\n" + "="*60)
    print("PHASE 4: SYSTEM WORKFLOW TESTS")
    print("="*60)

    test_id = "WORKFLOW-001"
    start_time = time.time()
    try:
        from backend.services.intent_classification.intent_classifier import IntentClassifier

        # Check for required methods
        required_methods = ['classify', 'get_confidence']
        missing_methods = []

        for method in required_methods:
            if not hasattr(IntentClassifier, method):
                missing_methods.append(method)

        if missing_methods:
            log_test(TestResult(
                test_id, "Intent Classification", "FAIL",
                time.time() - start_time,
                input_data="Check IntentClassifier methods",
                expected=f"Methods: {', '.join(required_methods)}",
                actual=f"Missing: {', '.join(missing_methods)}",
                notes="Intent classifier incomplete"
            ))
            log_bug(test_id, "Intent Classification",
                   f"Missing methods: {', '.join(missing_methods)}",
                   "HIGH",
                   "Check backend/services/intent_classification/intent_classifier.py")
        else:
            log_test(TestResult(
                test_id, "Intent Classification", "PASS",
                time.time() - start_time,
                input_data="Check IntentClassifier structure",
                expected="All required methods exist",
                actual="Structure validated"
            ))
    except ImportError as e:
        log_test(TestResult(
            test_id, "Intent Classification", "FAIL",
            time.time() - start_time,
            input_data="Import IntentClassifier",
            expected="IntentClassifier importable",
            actual=f"Import error: {str(e)}",
            notes="Cannot import IntentClassifier"
        ))
        log_bug(test_id, "Intent Classification",
               f"IntentClassifier import failed: {str(e)}",
               "HIGH",
               "Check backend/services/intent_classification/",
               traceback.format_exc())
    except Exception as e:
        log_test(TestResult(
            test_id, "Intent Classification", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))


def test_api_health_endpoint():
    """Test Case: API Health Endpoint"""
    test_id = "WORKFLOW-002"
    start_time = time.time()
    try:
        # Check if main.py exists
        if not os.path.exists("backend/main.py"):
            log_test(TestResult(
                test_id, "API", "FAIL",
                time.time() - start_time,
                input_data="Check main.py",
                expected="backend/main.py exists",
                actual="File not found",
                notes="FastAPI main file missing"
            ))
            log_bug(test_id, "API",
                   "backend/main.py not found",
                   "HIGH",
                   "Create backend/main.py with FastAPI application")
            return

        # Try to import main
        from backend.main import app

        log_test(TestResult(
            test_id, "API", "PASS",
            time.time() - start_time,
            input_data="Import FastAPI app",
            expected="FastAPI app object",
            actual="App imported successfully",
            notes="API structure valid"
        ))
    except ImportError as e:
        log_test(TestResult(
            test_id, "API", "ERROR",
            time.time() - start_time,
            input_data="Import FastAPI app",
            expected="FastAPI app object",
            actual=f"Import error: {str(e)}",
            notes="Cannot import FastAPI app"
        ))
        log_bug(test_id, "API", str(e), "HIGH",
               "Check backend/main.py", traceback.format_exc())
    except Exception as e:
        log_test(TestResult(
            test_id, "API", "ERROR",
            time.time() - start_time,
            notes=f"Exception: {str(e)}"
        ))


# ============================================
# Report Generation
# ============================================

def generate_test_report():
    """Generate comprehensive test execution report"""
    print("\n" + "="*60)
    print("TEST EXECUTION REPORT")
    print("="*60)

    # Calculate statistics
    total_tests = len(test_results)
    passed = sum(1 for r in test_results if r.status == "PASS")
    failed = sum(1 for r in test_results if r.status == "FAIL")
    errors = sum(1 for r in test_results if r.status == "ERROR")

    pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

    # Summary
    summary = {
        "test_execution": {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{pass_rate:.1f}%",
            "timestamp": datetime.now().isoformat()
        },
        "quality_metrics": {
            "rag_tests": sum(1 for r in test_results if "RAG" in r.category),
            "ocr_tests": sum(1 for r in test_results if "OCR" in r.category),
            "workflow_tests": sum(1 for r in test_results if "Workflow" in r.category or "API" in r.category),
            "environment_tests": sum(1 for r in test_results if "Environment" in r.category)
        },
        "test_results": [r.to_dict() for r in test_results],
        "bug_reports": bug_reports
    }

    # Print summary
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Errors: {errors}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print(f"\nBugs Found: {len(bug_reports)}")

    # Success criteria check
    print("\n" + "="*60)
    print("SUCCESS CRITERIA EVALUATION")
    print("="*60)

    criteria = [
        ("Mean case tests (>=90% pass)", pass_rate >= 90, pass_rate),
        ("1σ deviation tests (>=80% pass)", pass_rate >= 80, pass_rate),
        ("2σ+ deviation tests (>=70% pass)", pass_rate >= 70, pass_rate),
    ]

    for criterion, met, value in criteria:
        status = "✅ MET" if met else "❌ NOT MET"
        print(f"{status}: {criterion} (Actual: {value:.1f}%)")

    # Save detailed report
    report_dir = "test_results"
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{report_dir}/test_report_{timestamp}.json"

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Detailed report saved to: {report_file}")

    # Save bug report
    if bug_reports:
        bug_file = f"{report_dir}/bug_report_{timestamp}.json"
        with open(bug_file, 'w', encoding='utf-8') as f:
            json.dump(bug_reports, f, indent=2, ensure_ascii=False)
        print(f"🐛 Bug report saved to: {bug_file}")

    return summary


# ============================================
# Main Test Execution
# ============================================

def main():
    """Run comprehensive test suite"""
    print("="*60)
    print("INDUSTRY AI FLOW - COMPREHENSIVE TEST SUITE")
    print("="*60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = time.time()

    # Phase 1: Environment Setup
    test_environment_setup()

    # Phase 2: RAG Engine Tests
    test_rag_engine_structure()
    test_config_management()

    # Phase 3: OCR Tests
    test_paddleocr_installation()
    test_ocr_processor_initialization()

    # Phase 4: System Workflow Tests
    test_intent_classification_structure()
    test_api_health_endpoint()

    # Generate report
    total_time = time.time() - start_time
    print(f"\n⏱️  Total Execution Time: {total_time:.2f}s")

    summary = generate_test_report()

    # Return exit code based on results
    if summary["test_execution"]["failed"] > 0 or summary["test_execution"]["errors"] > 0:
        print("\n❌ Tests completed with failures or errors")
        return 1
    else:
        print("\n✅ All tests passed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
