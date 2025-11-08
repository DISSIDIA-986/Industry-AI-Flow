# PaddleOCR Test Cases

## Overview
This document contains test cases for PaddleOCR functionality in the Industry AI Flow project, specifically testing PP-OCRv5 version with Apple MPS acceleration support.

## Test Case 1: PaddlePaddle Version Check
- **Objective**: Verify PaddlePaddle installation and version requirements
- **Expected Version**: >=2.6.0
- **Steps**:
  1. Import paddle module
  2. Check version string
  3. Validate version meets requirements
- **Expected Result**: PaddlePaddle version >=2.6.0 is installed and functional

## Test Case 2: MPS Device Detection
- **Objective**: Test Apple Metal Performance Shaders (MPS) acceleration
- **Prerequisites**: Apple Silicon (M1/M2/M3) chip
- **Steps**:
  1. Get all custom devices
  2. Check for 'mps' in device list
  3. Attempt to set device to MPS
- **Expected Result**: MPS device detected and functional, providing 2-5x performance boost

## Test Case 3: PaddleOCR Version Check
- **Objective**: Verify PaddleOCR installation and import functionality
- **Test Version**: PaddleOCR 3.3.1 with PP-OCRv5 support
- **Steps**:
  1. Import paddleocr module
  2. Check version information
  3. Verify PaddleOCR class import
- **Expected Result**: PaddleOCR imports successfully with PP-OCRv5 features available

## Test Case 4: OCR Processor Initialization
- **Objective**: Test OCR processor initialization with project code
- **Configuration**: 
  - Language: Chinese (ch)
  - GPU: Enabled
  - Version: PP-OCRv5
- **Steps**:
  1. Import OCRProcessor from backend.services.document_processing
  2. Initialize with local OCR enabled
  3. Verify successful initialization
- **Expected Result**: OCR processor initializes successfully with all features enabled

## Test Case 5: NumPy Version Compatibility
- **Objective**: Ensure NumPy version compatibility with PaddleOCR
- **Expected Version**: <2.0 (for PaddleOCR compatibility)
- **Steps**:
  1. Import numpy module
  2. Check version
  3. Validate compatibility
- **Expected Result**: NumPy version is less than 2.0 for PaddleOCR compatibility

## Test Case 6: OCR Recognition on Visualizations
- **Objective**: Test OCR recognition on Chinese visualization images
- **Test Data**: Images from `chinese_visualization_output` directory
- **Steps**:
  1. Load test images
  2. Initialize OCR with Chinese language setting
  3. Process each image
  4. Measure recognition time, confidence, and text quality
- **Expected Result**: Images are recognized with good confidence (>70%) and accurate text extraction

## Test Case 7: Batch Processing Capability
- **Objective**: Test ability to process multiple images in batch
- **Steps**:
  1. Collect multiple images
  2. Process in batch mode
  3. Measure performance statistics
- **Expected Result**: All images processed with reasonable performance metrics

## Test Case 8: Complete Workflow Test
- **Objective**: Test full OCR workflow from image to text extraction and storage
- **Steps**:
  1. Select test image
  2. Process document with OCR
  3. Extract text content
  4. Save results to output file
- **Expected Result**: Complete workflow executes successfully with proper text extraction and storage

## Performance Metrics
- **Time per image**: Should be under 10 seconds for standard images
- **Confidence threshold**: Recognition confidence should be >0.7 for reliable results
- **Accuracy**: Text recognition accuracy should be >80% for standard text
- **Performance boost**: MPS acceleration should provide 2-5x speedup

## Known Issues & Limitations
- PaddlePaddle requires Python 3.13.x or lower on macOS
- MPS acceleration only available on Apple Silicon
- NumPy versions >=2.0 may cause compatibility issues
- Complex visualizations may have reduced recognition accuracy