# Comprehensive RAG System Testing Prompt for Coding LLMs

## Task Overview
You are a specialized testing engineer tasked with comprehensively testing the Industry AI Flow RAG (Retrieval-Augmented Generation) system using the provided test cases and resources. Your mission is to execute thorough functional and performance testing across all system components.

## System Context
The Industry AI Flow is an enterprise-level RAG system built with:
- LangChain 1.0 for agent orchestration
- PostgreSQL + pgvector for vector storage
- PaddleOCR for document processing
- llama.cpp/Ollama for LLM integration
- Intent classification for smart routing

## Test Resources Directory Structure
```
test_cases/                 # Test case specifications in Markdown format
├── paddleocr_test_cases.md     # PaddleOCR functionality tests
├── rag_test_cases.md           # RAG system tests
├── system_workflow_test_cases.md # System workflow and intent classification tests
└── normal_distribution_test_cases.md # Statistically distributed test cases

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

## Testing Objectives

### 1. Functional Testing
- **Core RAG Pipeline**: Document ingestion → Vectorization → Retrieval → Generation
- **Intent Classification**: Proper routing of queries to appropriate agents
- **Document Processing**: Handling of various document types and OCR
- **Code Execution**: Safe execution of code snippets in queries
- **Data Analysis**: Processing and visualization of datasets
- **OCR Capabilities**: Text extraction from images using PaddleOCR

### 2. Performance Testing
- **Response Time**: Measure latency for different query types
- **Throughput**: Test system capacity under various loads
- **Resource Usage**: Monitor memory and CPU consumption
- **Scalability**: Evaluate system behavior with increasing document count

## Detailed Testing Instructions

### Phase 1: Environment Setup
1. Verify all test resources exist as specified in the directory structure above
2. Set up the Industry AI Flow system according to the installation guide
3. Ensure all dependencies (PaddleOCR, PostgreSQL, etc.) are properly installed
4. Import test datasets from `test_resources/datasets/`
5. Load test documents from `test_resources/documents/`

### Phase 2: Component-Specific Testing

#### 2.1 RAG Engine Testing
Using `test_cases/rag_test_cases.md`:
1. Execute all RAG engine structure validation tests
2. Verify vector database integration
3. Test LLM integration
4. Validate document processing functionality
5. Test retrieval mechanisms
6. Confirm configuration management
7. Run complete RAG workflow simulation
8. Validate error handling mechanisms

#### 2.2 OCR Testing
Using `test_cases/paddleocr_test_cases.md`:
1. Verify PaddlePaddle version compatibility
2. Test MPS acceleration (if on Apple Silicon)
3. Validate PaddleOCR initialization
4. Execute OCR recognition tests on images from `test_resources/images/`
5. Test batch processing capabilities
6. Run complete OCR workflow tests

#### 2.3 Workflow Testing
Using `test_cases/system_workflow_test_cases.md`:
1. Test intent classification accuracy
2. Validate confidence-based clarification
3. Verify routing for all intent categories:
   - Knowledge Retrieval
   - Data Analysis
   - Document Processing
   - Code Execution
4. Test context-aware classification
5. Validate API integration
6. Confirm error handling and fallbacks

#### 2.4 Statistical Distribution Testing
Using `test_cases/normal_distribution_test_cases.md`:
1. Execute mean cases (μ) - 68.2% of tests for common scenarios
2. Execute 1σ deviation cases - 27.2% for moderately complex scenarios
3. Execute 2σ+ deviation cases - 4.6% for edge cases
4. Document performance metrics for each distribution tier

### Phase 3: Integration Testing
1. Test end-to-end workflows combining multiple components
2. Verify proper handoff between agents
3. Test system behavior with concurrent requests
4. Validate data consistency across components

### Phase 4: Performance Testing
1. Load test with increasing query volumes
2. Stress test system under maximum expected load
3. Measure response times for different query complexities
4. Monitor resource utilization (CPU, memory, disk I/O)
5. Test system recovery from high-load scenarios

## Test Execution Framework

### Using Test Queries
1. Load queries from `test_resources/datasets/test_queries.json`
2. Execute each query and verify proper classification
3. Record response times and accuracy
4. Validate that expected intents match actual routing

### Document Testing
1. Process documents from `test_resources/documents/`
2. Verify text extraction accuracy
3. Test chunking and vectorization
4. Validate retrieval quality

### Image Testing
1. Use images from `test_resources/images/` for OCR testing
2. Verify text recognition accuracy for both English and Chinese
3. Test performance metrics for different image types

## Expected Deliverables

### 1. Test Execution Report
- Summary of tests executed and passed/failed
- Performance metrics by test category
- Resource utilization data
- Bottleneck identification

### 2. Quality Metrics
- Intent classification accuracy
- RAG response accuracy
- OCR recognition accuracy
- System response times
- Error rates by component

### 3. Issue Log
- Detailed descriptions of any failures
- Stack traces or error messages
- Reproduction steps for identified issues
- Severity assessment

### 4. Recommendations
- Performance optimization suggestions
- Architecture improvements
- Additional test cases needed
- Resource allocation recommendations

## Success Criteria
- >=90% of mean case tests pass (from normal distribution)
- >=80% of 1σ deviation tests pass
- >=70% of 2σ+ deviation tests pass
- Average response time <2 seconds for simple queries
- System remains stable under 10 concurrent requests
- Intent classification accuracy >=85% for clear intent queries

## Reporting Format
For each test executed, provide:
```
Test ID: [Unique identifier]
Category: [Component being tested]
Status: [PASS/FAIL/ERROR]
Execution Time: [Duration]
Input: [Test input data]
Expected Result: [What was expected]
Actual Result: [What actually happened]
Performance Metrics: [Response time, resource usage, etc.]
Notes: [Any additional observations]
```

Execute the comprehensive testing plan and provide detailed reports to ensure the Industry AI Flow system meets enterprise-level quality, performance, and reliability standards.
