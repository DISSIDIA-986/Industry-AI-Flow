# Test Organization for Industry AI Flow

This document describes the organization of test cases and resources for the Industry AI Flow project.

## Directory Structure

```
test_cases/                                   # Test case specifications in Markdown format
├── paddleocr_test_cases.md                   # PaddleOCR functionality tests
├── rag_test_cases.md                         # RAG system tests
├── system_workflow_test_cases.md             # System workflow and intent classification tests
├── normal_distribution_test_cases.md         # Statistically distributed test cases
├── comprehensive_testing_prompt_for_coding_llms.md # Prompt for other Coding LLMs
├── problem_classification_test_cases.md      # Problem classification system tests
├── vector_retrieval_test_cases.md            # Vector retrieval system tests
├── answer_generation_test_cases.md           # Answer generation system tests
├── ocr_integration_test_cases.md             # OCR integration tests
├── data_analysis_code_execution_test_cases.md # Data analysis and code execution tests
├── streamlit_interface_test_cases.md         # Streamlit interface tests
├── user_feedback_impact_test_cases.md        # User feedback impact tests
├── comprehensive_test_integration_plan.md    # Complete test integration framework
├── extended_problem_classification_test_cases.md    # Extended problem classification tests
├── extended_vector_retrieval_test_cases.md          # Extended vector retrieval tests
├── extended_answer_generation_test_cases.md         # Extended answer generation tests
├── extended_ocr_integration_test_cases.md           # Extended OCR integration tests
├── extended_data_analysis_code_execution_test_cases.md  # Extended data analysis and code execution tests
├── extended_streamlit_interface_test_cases.md       # Extended Streamlit interface tests
├── extended_user_feedback_impact_test_cases.md      # Extended user feedback impact tests
├── extended_test_integration_plan.md               # Extended test integration framework
├── architecture_construction_test_cases.md         # Architecture and construction industry specific tests
├── architecture_construction_rag_performance_test.md # RAG performance test in architecture domain
└── architecture_construction_testing_prompt.md     # Prompt for testing LLMs on architecture domain

test_resources/                              # Test data and assets
├── datasets/                                # Test datasets and JSON files
│   ├── test_queries.json                    # Test queries for intent classification
│   ├── employee_data.csv                    # Sample CSV for data analysis tests
│   └── ...
├── documents/                               # Test documents (PDF, DOCX, TXT, etc.)
│   ├── sample_ai_basics.md                  # AI basics documentation
│   ├── retrieval_augmented_generation.md    # RAG documentation
│   └── ...
└── images/                                  # Test images for OCR and visual processing
    ├── test_ocr_image.png                   # English text image for OCR
    └── test_chinese_ocr_image.png           # Chinese text image for OCR
```

## Test Cases Overview

### 1. Core System Test Cases
- **paddleocr_test_cases.md**: PaddlePaddle and OCR functionality validation
- **rag_test_cases.md**: RAG engine and vector database integration
- **system_workflow_test_cases.md**: Intent classification and workflow routing

### 2. Statistical Distribution Test Cases
- **normal_distribution_test_cases.md**: Test cases distributed according to normal distribution principles for systematic coverage
- **comprehensive_testing_prompt_for_coding_llms.md**: Prompt to direct other AI systems for comprehensive testing

### 3. Problem Classification Tests
- **problem_classification_test_cases.md**: Tests for intent detection across simple Q&A, complex reasoning, and multi-turn conversations

### 4. Vector Retrieval Tests
- **vector_retrieval_test_cases.md**: Evaluation of recall rate, precision, and performance with different datasets and query types

### 5. Answer Generation Tests
- **answer_generation_test_cases.md**: Validation of correctness, fluency, and relevance in response generation

### 6. OCR Integration Tests
- **ocr_integration_test_cases.md**: PaddleOCR text extraction quality and RAG system performance with OCR-processed text

### 7. Data Analysis & Code Execution Tests
- **data_analysis_code_execution_test_cases.md**: Validation of data analysis capabilities and safe code execution

### 8. Interface & User Experience Tests
- **streamlit_interface_test_cases.md**: Comprehensive testing of frontend interfaces and user experience

### 9. User Feedback Tests
- **user_feedback_impact_test_cases.md**: Evaluation of how user feedback affects RAG system performance and quality

### 10. Integration Framework
- **comprehensive_test_integration_plan.md**: Complete integration plan for all test cases and execution workflow

## Test Resources Overview

### Datasets
- `test_queries.json`: Structured queries for intent classification testing
- `employee_data.csv`: Sample dataset for data analysis feature testing

### Documents
- Sample documents in various formats to test document processing capabilities

### Images
- OCR test images with both English and Chinese text
- Images with tables and structured text for layout analysis

## Usage

1. **Running Tests**: Execute tests using the project's testing framework:
   ```bash
   make test
   ```

2. **Adding New Tests**: 
   - Add new test case descriptions to the appropriate `.md` file in `test_cases/`
   - Add new test data to the appropriate subdirectory in `test_resources/`

3. **Test Execution**: The system will use these resources during automated testing.

4. **Comprehensive Testing**: Use `comprehensive_test_integration_plan.md` to execute coordinated testing across all components.

## Contributing

When adding new functionality:
1. Create appropriate test cases in the `test_cases/` directory
2. Add required test resources to the `test_resources/` directory
3. Update this documentation as needed
4. Integrate new tests into the comprehensive test plan in `comprehensive_test_integration_plan.md`