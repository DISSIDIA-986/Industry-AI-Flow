# OCR Integration Test Cases for RAG System

## Overview
This document provides comprehensive test cases for PaddleOCR integration within the RAG system, evaluating text extraction quality and how extracted text impacts overall RAG performance.

## Test Categories

### 1. OCR Text Extraction Quality Tests

#### Test Set 1.1: Basic Text Recognition
**Test ID: OCR-QT-BT-001 to 005**
- **Input**: Clear, high-resolution image with printed English text
- **Image**: `/test_resources/images/test_ocr_image.png`
- **Expected Output**: Accurate extraction of all text content
- **Evaluation Metrics**:
  - Character Accuracy: >95%
  - Word Accuracy: >90%
  - Character Error Rate (CER): <5%
  - Word Error Rate (WER): <10%
- **Additional Image**: Clean document scan with single font
- **Expected Output**: Complete text extraction with proper formatting
- **Evaluation Metrics**:
  - Character Accuracy: >96%
  - Word Accuracy: >92%
  - Formatting Preservation: >85%
- **Additional Image**: Multi-column layout document
- **Expected Output**: Text extraction preserving column structure
- **Evaluation Metrics**:
  - Character Accuracy: >93%
  - Column Separation: >90%
  - Reading Order: >85%
- **Additional Image**: Document with headers and footers
- **Expected Output**: Extraction of main content with metadata
- **Evaluation Metrics**:
  - Content Accuracy: >94%
  - Header/Footer Recognition: >80%
- **Additional Image**: Simple table image
- **Expected Output**: Extraction of text in tabular format
- **Evaluation Metrics**:
  - Cell Content Accuracy: >90%
  - Table Structure Preservation: >80%

#### Test Set 1.2: Multilingual Text Recognition
**Test ID: OCR-QT-MT-001 to 002**
- **Input**: Chinese text image with mixed English
- **Image**: `/test_resources/images/test_chinese_ocr_image.png`
- **Expected Output**: Accurate recognition of both Chinese and English text
- **Evaluation Metrics**:
  - Chinese Character Accuracy: >92%
  - English Word Accuracy: >90%
  - Mixed Script Handling: >85%
- **Additional Input**: Mixed language document (Chinese/English)
- **Expected Output**: Proper identification and extraction of both languages
- **Evaluation Metrics**:
  - Language Detection Accuracy: >95%
  - Bilingual Content Accuracy: >88%

#### Test Set 1.3: Quality Degradation Tests
**Test ID: OCR-QT-QD-001 to 004**
- **Input**: Low-resolution image (72 DPI)
- **Expected Output**: Reasonable extraction with expected degradation
- **Evaluation Metrics**:
  - Character Accuracy: >80%
  - Word Accuracy: >70%
  - Performance vs. quality: Documented degradation curve
- **Input**: Image with poor contrast
- **Expected Output**: Extraction with reduced accuracy
- **Evaluation Metrics**:
  - Character Accuracy: >75%
  - Noise Handling: >70%
- **Input**: Skewed/rotated image
- **Expected Output**: Automatic correction and accurate extraction
- **Evaluation Metrics**:
  - Alignment Correction: >85%
  - Extraction Accuracy: >80%
- **Input**: Image with noise and artifacts
- **Expected Output**: Extraction with noise filtering
- **Evaluation Metrics**:
  - Noise Filtering: >75%
  - Content Preservation: >80%

### 2. RAG System Performance with OCR Text

#### Test Set 2.1: Document Ingestion Pipeline
**Test ID: OCR-RP-DIP-001 to 003**
- **Input**: Image document processed through OCR
- **Pipeline**: Image → OCR → Text Extraction → RAG Ingestion
- **Expected Output**: Successfully ingested into vector database
- **Evaluation Metrics**:
  - Ingestion Success Rate: >95%
  - Processing Time: <10 seconds per page
  - Text Quality for Embedding: >85% retention of meaningful content
- **Input**: Multiple image files batch ingestion
- **Pipeline**: Multi-image → Batch OCR → Batch Ingestion
- **Expected Output**: All documents ingested successfully
- **Evaluation Metrics**:
  - Batch Success Rate: >98%
  - Throughput: >5 pages/minute
- **Input**: Mixed content: text, table, graphs in image
- **Pipeline**: Complex image → OCR → Content separation → Ingestion
- **Expected Output**: Structured ingestion preserving content types
- **Evaluation Metrics**:
  - Content Type Recognition: >90%
  - Structure Preservation: >80%

#### Test Set 2.2: Retrieval Quality with OCR Text
**Test ID: OCR-RP-RQ-001 to 003**
- **Query**: Text-based question about content in OCR-processed document
- **Expected Results**: Relevant passages retrieved from OCR-extracted text
- **Evaluation Metrics**:
  - Retrieval Recall: >80% of relevant passages found
  - Retrieval Precision: >75% of retrieved passages relevant
  - OCR Quality Impact: Documented effect on retrieval performance
- **Query**: Complex multi-term query
- **Expected Results**: Accurate retrieval despite OCR errors
- **Evaluation Metrics**:
  - Complex Query Handling: >75%
  - Error Tolerance: How well system handles OCR errors
- **Query**: Fuzzy query matching OCR artifacts
- **Expected Results**: Robust retrieval despite OCR imperfections
- **Evaluation Metrics**:
  - Fuzzy Matching Success: >80%
  - Error Robustness: >70%

#### Test Set 2.3: Answer Generation from OCR Text
**Test ID: OCR-RP-AG-001 to 002**
- **Query**: Question requiring answer from OCR-processed document
- **Expected Output**: Accurate answer generated from OCR-extracted content
- **Evaluation Metrics**:
  - Answer Accuracy: >85% (compared to human baseline)
  - OCR Error Impact: How errors affect answer quality
  - Context Quality: How well OCR text supports QA
- **Query**: Multi-hop question using OCR content
- **Expected Output**: Answer requiring multiple pieces of OCR-extracted information
- **Evaluation Metrics**:
  - Multi-hop Accuracy: >80%
  - Information Integration: >85%

### 3. PaddleOCR Version and Configuration Tests

#### Test Set 3.1: PP-OCRv5 Performance
**Test ID: OCR-PC-PV-001 to 002**
- **Configuration**: PP-OCRv5 Chinese model
- **Input**: Chinese text images from test resources
- **Expected Output**: Superior recognition for Chinese text
- **Evaluation Metrics**:
  - Chinese Character Accuracy: >95%
  - Speed: <5 seconds per image
  - Model Size Efficiency: Documented
- **Configuration**: PP-OCRv5 English model
- **Input**: English text images
- **Expected Output**: Superior recognition for English text
- **Evaluation Metrics**:
  - English Word Accuracy: >96%
  - Speed: <5 seconds per image

#### Test Set 3.2: Language Model Testing
**Test ID: OCR-PC-LM-001 to 003**
- **Model**: English-only model
- **Input**: English and Chinese mixed text
- **Expected Output**: English recognition, Chinese as noise
- **Evaluation Metrics**:
  - English Accuracy: >95%
  - Error Handling: Proper handling of unsupported script
- **Model**: Chinese-only model
- **Input**: English and Chinese mixed text
- **Expected Output**: Chinese recognition, English as noise
- **Evaluation Metrics**:
  - Chinese Accuracy: >94%
  - Error Handling: Proper handling of unsupported script
- **Model**: Multi-language model
- **Input**: Mixed script text
- **Expected Output**: Recognition of both languages
- **Evaluation Metrics**:
  - Multi-language Accuracy: >90% overall
  - Language Segregation: >85%

### 4. Performance and Scalability Tests

#### Test Set 4.1: Processing Speed Tests
**Test ID: OCR-PS-PS-001 to 003**
- **Input**: Single high-resolution image (300 DPI)
- **Expected Time**: <8 seconds with GPU acceleration
- **Metrics**:
  - Processing Time: Documented
  - Resource Usage: CPU, GPU, Memory
  - Throughput: Images per minute
- **Input**: Batch of 10 images
- **Expected Time**: <60 seconds total
- **Metrics**:
  - Batch Processing Time: Documented
  - Throughput: Images per minute
  - Efficiency: Per-image time compared to single processing
- **Input**: Large document (20+ pages)
- **Expected Time**: <300 seconds total
- **Metrics**:
  - Document Processing Time: Documented
  - Memory Usage: Peak and average
  - Stability: No crashes during processing

#### Test Set 4.2: Resource Utilization
**Test ID: OCR-PS-RU-001 to 002**
- **Test**: Continuous OCR processing
- **Duration**: 1 hour continuous operation
- **Metrics**:
  - Memory Usage: Peak and stability
  - CPU/GPU Utilization: Average and peak
  - Temperature: System thermal performance
- **Test**: Concurrent OCR tasks
- **Concurrency**: 5 parallel tasks
- **Metrics**:
  - Throughput: Total images per minute
  - Individual Performance: Per-task speed degradation
  - Resource Sharing: Efficiency of resource utilization

### 5. Integration Edge Cases

#### Test Set 5.1: Error Handling
**Test ID: OCR-IC-EE-001 to 003**
- **Input**: Corrupted image file
- **Expected Behavior**: Graceful error handling
- **Metrics**:
  - Error Detection: Proper identification of corrupted input
  - Error Reporting: Clear error messages
  - System Stability: No system crashes
- **Input**: Unsupported image format
- **Expected Behavior**: Format detection and handling
- **Metrics**:
  - Format Detection: Proper identification
  - Error Handling: Appropriate response
  - Fallback Options: Available alternatives
- **Input**: Extremely large image file (>100MB)
- **Expected Behavior**: Proper handling or rejection
- **Metrics**:
  - Size Detection: Proper identification
  - Memory Management: No memory overflow
  - Time Management: Appropriate timeout

#### Test Set 5.2: Special Content Handling
**Test ID: OCR-IC-SC-001 to 003**
- **Input**: Image with handwritten text
- **Expected Output**: Attempted recognition with quality indicator
- **Metrics**:
  - Recognition Success: Whether attempted
  - Quality Score: Accuracy assessment
  - Suitability: How well PaddleOCR handles handwriting
- **Input**: Image with mathematical equations
- **Expected Output**: Text extraction of equation content
- **Metrics**:
  - Mathematical Content Recognition: Accuracy of math symbols
  - Structure Preservation: Maintaining equation structure
  - Symbol Recognition: Accuracy of special symbols
- **Input**: Image with diagrams/charts
- **Expected Output**: Text extraction from labels, titles, etc.
- **Metrics**:
  - Label Recognition: Accuracy of text elements
  - Non-text Handling: Proper exclusion of pure graphics

### 6. RAG-Specific Workflow Tests

#### Test Set 6.1: End-to-End Document Processing
**Test ID: OCR-RW-ED-001 to 003**
- **Workflow**: Image document → OCR → Text processing → Vector embedding → RAG retrieval
- **Input**: Real-world document (manual/whitepaper)
- **Expected**: Complete pipeline success
- **Metrics**:
  - End-to-end Success Rate: >95%
  - Quality Preservation: Text quality through pipeline
  - Retrieval Effectiveness: How well OCR text supports retrieval
- **Workflow**: Multi-page document → Batch OCR → Chunking → Embedding → Storage
- **Input**: Multi-page technical document
- **Expected**: All pages processed and stored
- **Metrics**:
  - Multi-page Success: >98%
  - Page Continuity: Context preservation across pages
  - Performance: Processing time per page
- **Workflow**: Image + PDF combination → Processing → Unified index
- **Input**: Mixed document types
- **Expected**: Unified searchable index
- **Metrics**:
  - Multi-format Integration: >95%
  - Cross-format Retrieval: >90%

#### Test Set 6.2: Quality Impact Assessment
**Test ID: OCR-RW-QI-001 to 002**
- **Assessment**: Compare performance: native text vs. OCR text
- **Method**: Same document in text and image form
- **Metrics**:
  - Performance Difference: Quantified impact of OCR
  - Quality Threshold: Minimum OCR quality for effective RAG
  - Cost-Benefit: Trade-off between OCR and manual transcription
- **Assessment**: Progressive degradation test
- **Method**: Intentionally degraded images at various quality levels
- **Metrics**:
  - Quality Threshold: Point where RAG becomes ineffective
  - Degradation Curve: Performance vs. image quality
  - Tolerance Limits: Minimum acceptable OCR quality

### 7. MPS Acceleration Tests (Apple Silicon)
**Test ID: OCR-MA-MS-001 to 002**
- **Platform**: Apple Silicon with MPS acceleration
- **Test**: Performance comparison with CPU-only
- **Metrics**:
  - Speed Improvement: Quantified MPS acceleration benefit
  - Energy Efficiency: Power consumption comparison
  - Accuracy: Verify no accuracy loss with acceleration
- **Platform**: Apple Silicon with MPS
- **Test**: Memory usage optimization
- **Metrics**:
  - Memory Efficiency: Reduced memory usage with MPS
  - Stability: System stability during processing

### 8. Comparison Against Baseline
**Test ID: OCR-CB-BL-001 to 001**
- **Baseline**: Previous OCR implementation or manual transcription
- **Comparison**: Accuracy, speed, cost metrics
- **Metrics**:
  - Relative Performance: Improvement over baseline
  - ROI Analysis: Cost-benefit of OCR integration
  - Quality Assurance: Meeting minimum quality standards

### Evaluation Metrics Summary

1. **Text Recognition Metrics**:
   - Character Accuracy Rate (CAR)
   - Word Accuracy Rate (WAR)
   - Character Error Rate (CER)
   - Word Error Rate (WER)
   - Language Detection Accuracy

2. **RAG Performance Metrics**:
   - Retrieval Recall@K
   - Retrieval Precision@K
   - Mean Reciprocal Rank (MRR)
   - Answer Generation Accuracy
   - OCR Quality Impact on RAG

3. **Performance Metrics**:
   - Processing Time per Image
   - Throughput (Images per Minute)
   - Resource Utilization (CPU, GPU, Memory)
   - Energy Efficiency

4. **Robustness Metrics**:
   - Error Handling Success Rate
   - System Stability under Load
   - Recovery from Error Conditions

### Success Criteria
- OCR Character Accuracy: >90% for good quality images
- RAG retrieval with OCR text: >75% of baseline performance
- Processing time: <10 seconds per standard page
- System stability: 99.9% uptime during testing
- Error handling: 100% graceful handling of invalid inputs
