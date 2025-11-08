# Normal Distribution Based Test Cases for Industry AI Flow

## Overview
This document presents test cases designed according to normal distribution principles to ensure comprehensive coverage of the Industry AI Flow system's functionality and use cases. The tests are distributed to ensure most common scenarios are thoroughly tested while still covering edge cases.

## Statistical Test Distribution
- **Mean (μ)**: Most common use cases (68.2% of tests)
- **1 Standard Deviation (σ)**: Common variations (27.2% of tests)
- **2+ Standard Deviations**: Edge cases and rare scenarios (4.6% of tests)

## Test Case Categories by Distribution

### 1. Intent Classification System (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of intent tests
**Test ID: IC-M-001 to IC-M-007**
- **Objective**: Test most common queries that clearly fit into one category
- **Sample Queries**:
  - "What is machine learning?" → Knowledge Retrieval
  - "Analyze this dataset" → Data Analysis
  - "Extract text from this PDF" → Document Processing
  - "Write Python code to sort an array" → Code Execution
  - "Tell me about neural networks" → Knowledge Retrieval
  - "Create a histogram of sales" → Data Analysis
  - "Summarize this document" → Document Processing

#### 1σ Deviation: 27.2% of intent tests
**Test ID: IC-S-001 to IC-S-003**
- **Objective**: Test ambiguous queries or cross-domain queries
- **Sample Queries**:
  - "Analyze sales data and write a report" (Data Analysis + Document Processing)
  - "Show me how machine learning works with examples" (Knowledge + Data Analysis)
  - "I need to process this document and then run some code" (Document + Code)

#### 2σ+ Deviation: 4.6% of intent tests
**Test ID: IC-E-001 to IC-E-001**
- **Objective**: Test rare or challenging edge cases
- **Sample Queries**:
  - "How to use Industry AI Flow for my research?" (Multi-intent, complex)

### 2. RAG System (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of RAG tests
**Test ID: RAG-M-001 to RAG-M-007**
- **Objective**: Test RAG with well-formatted, clean documents and clear queries
- **Input Characteristics**:
  - Clean, well-formatted text documents
  - Clear, specific questions
  - Good context relevance
  - Standard document types (PDF, DOCX, TXT)
  - Medium length documents (2-10 pages)

#### 1σ Deviation: 27.2% of RAG tests
**Test ID: RAG-S-001 to RAG-S-003**
- **Objective**: Test RAG with moderately challenging documents/queries
- **Input Characteristics**:
  - Documents with tables, images, formatting
  - Complex or multi-part questions
  - Noisy or imperfect documents
  - Longer documents (>10 pages)
  - Mixed document types

#### 2σ+ Deviation: 4.6% of RAG tests
**Test ID: RAG-E-001 to RAG-E-001**
- **Objective**: Test extreme edge cases
- **Input Characteristics**:
  - Heavily corrupted documents
  - Very short or very long queries
  - Completely irrelevant questions
  - Multiple file types combined

### 3. Document Processing (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of doc tests
**Test ID: DOC-M-001 to DOC-M-007**
- **Objective**: Test processing of standard document types
- **Input Types**:
  - Clean PDF documents
  - Well-formatted Word documents
  - Plain text files
  - Clear scan images (high DPI)
  - Standard document layouts
  - Common languages (English/Chinese)
  - Reasonable file sizes (<10MB)

#### 1σ Deviation: 27.2% of doc tests
**Test ID: DOC-S-001 to DOC-S-003**
- **Objective**: Test processing of slightly challenging documents
- **Input Types**:
  - Documents with complex layouts
  - Scanned documents with minor quality issues
  - Multi-language documents
  - Large documents (10-50MB)
  - Documents with embedded images/tables

#### 2σ+ Deviation: 4.6% of doc tests
**Test ID: DOC-E-001 to DOC-E-001**
- **Objective**: Test extreme document processing scenarios
- **Input Types**:
  - Severely damaged documents
  - Extremely large files (>100MB)
  - Uncommon document formats
  - Documents with severe OCR errors

### 4. OCR Functionality (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of OCR tests
**Test ID: OCR-M-001 to OCR-M-007**
- **Objective**: Test OCR on high-quality, standard images
- **Input Characteristics**:
  - High-resolution images (300+ DPI)
  - Clear, printed text
  - Good lighting, minimal noise
  - Standard fonts
  - English text
  - Simple layouts
  - Good contrast between text and background

#### 1σ Deviation: 27.2% of OCR tests
**Test ID: OCR-S-001 to OCR-S-003**
- **Objective**: Test OCR on moderately challenging images
- **Input Characteristics**:
  - Moderate image quality
  - Mixed fonts and sizes
  - Multiple languages
  - Tables and structured text
  - Slight noise or artifacts
  - Handwritten text mixed with print

#### 2σ+ Deviation: 4.6% of OCR tests
**Test ID: OCR-E-001 to OCR-E-001**
- **Objective**: Test OCR on extremely challenging images
- **Input Characteristics**:
  - Very low quality images
  - Severely damaged or cropped images
  - Complex layouts with overlapping text
  - Very small or very large fonts
  - Severe lighting conditions

### 5. Code Execution (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of code tests
**Test ID: CODE-M-001 to CODE-M-007**
- **Objective**: Test execution of simple, safe code snippets
- **Code Types**:
  - Simple mathematical calculations
  - Basic string manipulation
  - Simple data processing
  - Standard library functions
  - Error-free code
  - Deterministic output
  - Short execution time (<1 sec)

#### 1σ Deviation: 27.2% of code tests
**Test ID: CODE-S-001 to CODE-S-003**
- **Objective**: Test moderately complex or longer-running code
- **Code Types**:
  - Mathematical algorithms
  - File I/O operations
  - Data analysis with pandas/numpy
  - Plots and visualizations
  - Code with standard exceptions handled
  - Medium execution time (1-5 sec)

#### 2σ+ Deviation: 4.6% of code tests
**Test ID: CODE-E-001 to CODE-E-001**
- **Objective**: Test challenging or potentially unsafe code
- **Code Types**:
  - Long-running computations
  - Network requests
  - System commands
  - Code with intentional errors
  - Memory-intensive operations

### 6. Data Analysis (Normal Distribution Applied)

#### Mean Cases (μ): 68.2% of analysis tests
**Test ID: ANAL-M-001 to ANAL-M-007**
- **Objective**: Test analysis of clean, structured datasets
- **Dataset Characteristics**:
  - Well-formatted CSV/JSON files
  - Clean numerical data
  - No missing values
  - Standard data types
  - Appropriate for common visualizations
  - Small to medium size (<10k rows)
  - Clear column names

#### 1σ Deviation: 27.2% of analysis tests
**Test ID: ANAL-S-001 to ANAL-S-003**
- **Objective**: Test analysis of moderately complex datasets
- **Dataset Characteristics**:
  - Mixed data types
  - Some missing values
  - Complex relationships
  - Larger datasets (10k-100k rows)
  - Non-standard formats
  - Time series data

#### 2σ+ Deviation: 4.6% of analysis tests
**Test ID: ANAL-E-001 to ANAL-E-001**
- **Objective**: Test analysis of extremely challenging datasets
- **Dataset Characteristics**:
  - Heavily corrupted data
  - Extremely large datasets (>1M rows)
  - Complex nested structures
  - Multiple data sources requiring joins
  - Inconsistent schemas

## Performance Metrics by Distribution

### Mean Cases (μ) Performance Targets:
- Response time: <2 seconds
- Accuracy: >90% for clear inputs
- Success rate: >95%

### 1σ Deviation Performance Targets:
- Response time: <5 seconds
- Accuracy: >80% for clear inputs
- Success rate: >85%

### 2σ+ Deviation Performance Targets:
- Response time: <10 seconds
- Accuracy: >60% where applicable
- Success rate: >70%

## Implementation Notes

1. **Test Data Generation**: Use the test resources in `/test_resources/` directory
2. **Distribution Validation**: Ensure actual test execution reflects the intended distribution
3. **Metrics Collection**: Track performance separately for each distribution tier
4. **Reporting**: Provide separate reports for each standard deviation group

This approach ensures that the most important use cases (mean) receive the most attention while still providing coverage for edge cases (tails of the distribution).