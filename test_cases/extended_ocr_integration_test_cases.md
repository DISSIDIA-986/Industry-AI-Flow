# Extended OCR Integration Test Cases

## Overview
This document provides extended test cases for PaddleOCR integration testing with additional scenarios and edge cases.

## Extended Test Categories

### 1. Extended OCR Text Extraction Quality Tests

#### Test Set 1.1: Special Character Handling
**Test ID: OCR-ED-SC-001 to 003**
- **Input**: Image with mathematical symbols (∫ ∑ ∞ + - × ÷ = ≠ ≤ ≥)
- **Expected Output**: Accurate recognition of mathematical symbols
- **Evaluation Metrics**:
  - Symbol Accuracy: >90%
  - Symbol Context Preservation: >85%
- **Image**: `/test_resources/images/math_equations_image.png`

- **Input**: Image with currency symbols ($ € £ ¥ ¢)
- **Expected Output**: Accurate recognition of currency symbols
- **Evaluation Metrics**:
  - Symbol Accuracy: >92%
  - Context Preservation: >88%
- **Image**: `/test_resources/images/currency_symbols_image.png`

- **Input**: Image with special punctuation (! ? @ # % & *)
- **Expected Output**: Accurate recognition of special characters
- **Evaluation Metrics**:
  - Symbol Accuracy: >88%
  - Context Preservation: >82%
- **Image**: `/test_resources/images/special_chars_image.png`

#### Test Set 1.2: Handwritten Text Recognition
**Test ID: OCR-ED-HT-001 to 002**
- **Input**: Handwritten note image (created earlier)
- **Expected Output**: Recognition of main text content with accuracy assessment
- **Evaluation Metrics**:
  - Character Accuracy: >70%
  - Word Accuracy: >60%
  - Readability Score: >75%
- **Image**: `/test_resources/images/handwritten_note.png`

- **Input**: Mixed handwritten-printed text image
- **Expected Output**: Separation and accurate recognition of different text types
- **Evaluation Metrics**:
  - Handwritten Accuracy: >65%
  - Printed Accuracy: >85%
  - Type Differentiation: >80%

#### Test Set 1.3: Table Structure Recognition (Extended)
**Test ID: OCR-ED-TS-001 to 002**
- **Input**: Complex sales report table image (created earlier)
- **Expected Output**: Accurate extraction with proper table structure preservation
- **Evaluation Metrics**:
  - Cell Content Accuracy: >85%
  - Table Structure Preservation: >80%
  - Header Recognition: >90%
- **Image**: `/test_resources/images/complex_table_image.png`

- **Input**: Nested table image
- **Expected Output**: Recognition of nested table structures
- **Evaluation Metrics**:
  - Nested Structure Accuracy: >75%
  - Content Accuracy: >80%

### 2. Extended RAG System Performance Tests

#### Test Set 2.1: Low-Quality OCR Impact on RAG
**Test ID: OCR-ED-LQ-001 to 002**
- **Input**: Blurry, low-resolution image processed through OCR
- **Pipeline**: Low-quality OCR text → RAG ingestion → retrieval
- **Expected Output**: System handles OCR errors gracefully in RAG pipeline
- **Evaluation Metrics**:
  - Error Tolerance: Maintains 70% retrieval quality with 20% OCR error rate
  - Performance Degradation: <30% performance drop with poor OCR input

- **Input**: High OCR error rate document (e.g., old scanned documents)
- **Pipeline**: High-error OCR text → RAG processing
- **Expected Output**: System identifies low-quality input and adjusts appropriately
- **Evaluation Metrics**:
  - Quality Assessment: Correctly identifies low-quality input
  - Adaptive Processing: Adjusts retrieval strategy for noisy text

#### Test Set 2.2: Multi-Page Document Processing
**Test ID: OCR-ED-MP-001 to 001**
- **Input**: Multi-page document with consistent OCR processing
- **Pipeline**: Multi-page images → Batch OCR → RAG ingestion
- **Expected Output**: All pages processed consistently with preserved context
- **Evaluation Metrics**:
  - Multi-page Success: >95% success rate
  - Context Continuity: Maintains document context across pages
  - Processing Efficiency: Maintains reasonable throughput

### 3. Extended Language Model Tests

#### Test Set 3.1: Mixed Script Recognition
**Test ID: OCR-ED-MS-001 to 002**
- **Configuration**: Multi-language model
- **Input**: Image with English, Chinese, and numbers mixed
- **Expected Output**: Accurate recognition of all scripts
- **Evaluation Metrics**:
  - Multi-script Accuracy: >85% overall
  - Script Segregation: >90% accurate separation

- **Configuration**: Multi-language model
- **Input**: Image with Latin, Arabic, and numeric text
- **Expected Output**: Recognition of mixed scripts
- **Evaluation Metrics**:
  - Multi-script Accuracy: >80% overall
  - Direction Handling: Proper RTL/LTR text handling

### 4. Extended Performance Tests

#### Test Set 4.1: Large Document Processing
**Test ID: OCR-ED-LD-001 to 001**
- **Input**: Large document (50+ pages)
- **Expected Time**: <15 minutes total processing time
- **Metrics**:
  - Processing Throughput: >5 pages per minute
  - Memory Usage: <4GB peak usage
  - Stability: No crashes during processing

#### Test Set 4.2: Concurrent OCR Tasks with RAG Integration
**Test ID: OCR-ED-CC-001 to 001**
- **Test**: Multiple OCR tasks while RAG system is active
- **Concurrency**: 10 parallel OCR + RAG tasks
- **Metrics**:
  - Throughput: All tasks complete successfully
  - Performance Degradation: <40% slowdown under load
  - Resource Sharing: Fair resource allocation

### 5. Extended Edge Cases

#### Test Set 5.1: Unusual Document Types
**Test ID: OCR-ED-UD-001 to 003**
- **Input**: Hand-drawn diagrams with text labels
- **Expected Output**: Recognition of text elements in diagram
- **Metrics**:
  - Text Recognition: >60% of labeled text recognized
  - Non-text Handling: Proper exclusion of pure graphics

- **Input**: Form with check boxes and radio buttons
- **Expected Output**: Recognition of form text and field types
- **Metrics**:
  - Form Element Recognition: >75% of fields identified
  - Content Accuracy: >80% for form content

- **Input**: Tabular form with handwritten entries
- **Expected Output**: Table structure and content recognition
- **Metrics**:
  - Structure Recognition: >70% of table structure preserved
  - Handwritten Content: >65% accuracy for handwritten entries

#### Test Set 5.2: OCR Error Recovery
**Test ID: OCR-ED-ER-001 to 001**
- **Input**: Document with OCR processing errors
- **Expected Behavior**: System attempts recovery or provides error feedback
- **Metrics**:
  - Recovery Success: >80% of errors handled gracefully
  - Feedback Quality: Clear error messages provided

### 6. Extended RAG-Specific Workflow Tests

#### Test Set 6.1: OCR Quality Impact Gradients
**Test ID: OCR-ED-OQ-001 to 002**
- **Assessment**: Performance degradation from poor OCR quality
- **Method**: Intentionally degraded OCR output at various quality levels
- **Metrics**:
  - Quality Threshold: Point where RAG becomes ineffective
  - Degradation Curve: Performance vs. OCR quality
  - Tolerance Limits: Minimum acceptable OCR quality for effective RAG

- **Assessment**: Impact of specific OCR error types on RAG performance
- **Method**: Introduce specific error types (character substitution, word deletion, etc.)
- **Metrics**:
  - Error Type Impact: Which errors most affect RAG
  - Resilience Score: RAG system's ability to handle specific error types

#### Test Set 6.2: Semantic Preservation Through OCR
**Test ID: OCR-ED-SP-001 to 001**
- **Test**: How well meaning is preserved through OCR → RAG pipeline
- **Method**: Compare RAG responses on original text vs. OCR-extracted text
- **Metrics**:
  - Semantic Preservation: >80% of meaning preserved
  - Answer Quality Maintenance: <15% degradation in answer quality

### 7. Extended Integration Tests

#### Test Set 7.1: OCR Preprocessing Pipeline
**Test ID: OCR-ED-OP-001 to 001**
- **Workflow**: Image → Preprocessing → OCR → RAG
- **Input**: Various quality images requiring preprocessing
- **Expected**: Preprocessing improves OCR quality which improves RAG
- **Metrics**:
  - Preprocessing Impact: Measurable improvement after preprocessing
  - Efficiency: Preprocessing doesn't significantly slow pipeline

### 8. Advanced Model Testing

#### Test Set 8.1: Model Version Comparison
**Test ID: OCR-ED-MV-001 to 001**
- **Test**: Compare performance of different PaddleOCR models
- **Models**: PP-OCRv3 vs PP-OCRv4 vs PP-OCRv5
- **Metrics**:
  - Accuracy Comparison: Quantified improvement between versions
  - Speed Comparison: Processing speed differences
  - Resource Usage: Different memory/compute requirements

### 9. Quality Assurance Tests

#### Test Set 9.1: OCR Confidence Scoring Integration
**Test ID: OCR-ED-CS-001 to 001**
- **Test**: Use OCR confidence scores to weight RAG results
- **Method**: Lower confidence OCR text gets lower weight in retrieval
- **Metrics**:
  - Confidence Integration: Proper use of confidence scores
  - Quality Improvement: Better overall results with confidence weighting

### 10. New Image-Based Tests

#### Test Set 10.1: Created Test Images Evaluation
**Test ID: OCR-ED-CT-001 to 002**
- **Input**: Complex table image created for testing
- **Image Path**: `/test_resources/images/complex_table_image.png`
- **Expected**: Accurate extraction of table data
- **Metrics**:
  - Table Data Accuracy: >85% of data correctly extracted
  - Structure Preservation: Table format maintained
  - Cell Recognition: Individual cells properly identified

- **Input**: Handwritten note image created for testing
- **Image Path**: `/test_resources/images/handwritten_note.png`
- **Expected**: Reasonable recognition of handwritten text
- **Metrics**:
  - Text Recognition: >65% of content correctly identified
  - Structure Recognition: Note structure preserved
  - Accuracy Score: Reasonable accuracy for handwritten content

## Extended Evaluation Metrics Summary

1. **Special Character Recognition**: Accuracy with mathematical, linguistic, and special symbols
2. **Handwritten Text Recognition**: Performance with non-standard fonts/handwriting
3. **Table Structure Preservation**: Maintaining tabular data relationships
4. **Low-Quality Tolerance**: Performance with poor input quality
5. **Multi-Script Handling**: Accuracy with mixed language scripts
6. **Large Document Processing**: Performance with many pages
7. **Form Processing**: Recognition of structured documents
8. **Error Recovery**: Handling of OCR failures gracefully
9. **Semantic Preservation**: Meaning preservation through OCR-RAG pipeline
10. **Confidence Integration**: Using OCR confidence for RAG weighting

## Extended Success Criteria
- Special character accuracy: >88%
- Handwritten text recognition: >60%
- Table structure preservation: >80%
- Error tolerance: Maintains 70% quality with 20% OCR errors
- Multi-script accuracy: >85%
- Large document processing: >95% success rate
- Form processing: >75% accuracy
- Error recovery: 100% graceful handling
- Semantic preservation: >80% meaning maintained
- Confidence integration: Effective use of confidence scores
