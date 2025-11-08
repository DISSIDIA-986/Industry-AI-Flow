# Test Organization for Industry AI Flow

This document describes the organization of test cases and resources for the Industry AI Flow project.

## Directory Structure

```
test_cases/                 # Test case specifications in Markdown format
├── paddleocr_test_cases.md     # PaddleOCR functionality tests
├── rag_test_cases.md           # RAG system tests
└── system_workflow_test_cases.md # System workflow and intent classification tests

test_resources/            # Test data and assets
├── datasets/              # Test datasets and JSON files
│   ├── test_queries.json     # Test queries for intent classification
│   ├── employee_data.csv     # Sample CSV for data analysis tests
│   └── ...
├── documents/             # Test documents (PDF, DOCX, TXT, etc.)
│   ├── sample_ai_basics.md   # AI basics documentation
│   ├── retrieval_augmented_generation.md # RAG documentation
│   └── ...
└── images/                # Test images for OCR and visual processing
    ├── test_ocr_image.png         # English text image for OCR
    └── test_chinese_ocr_image.png # Chinese text image for OCR
```

## Test Cases Overview

### 1. PaddleOCR Test Cases (`paddleocr_test_cases.md`)
- PaddlePaddle version check
- MPS device detection (Apple Silicon)
- PaddleOCR initialization
- OCR recognition on visualizations
- Batch processing capability
- Complete workflow tests

### 2. RAG Test Cases (`rag_test_cases.md`)
- RAG engine structure validation
- Vector database integration
- LLM integration
- Document processing
- Retrieval mechanisms
- Configuration management
- Complete workflow simulation
- Error handling

### 3. System Workflow Test Cases (`system_workflow_test_cases.md`)
- Intent classification accuracy
- Confidence-based clarification
- Routing to different agents
- Context-aware classification
- API integration
- Error handling and fallbacks
- Performance under load

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

## Contributing

When adding new functionality:
1. Create appropriate test cases in the `test_cases/` directory
2. Add required test resources to the `test_resources/` directory
3. Update this documentation as needed