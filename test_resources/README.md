# Test Resources for Industry AI Flow

This directory contains test data and resources used for testing the Industry AI Flow system.

## Overview

The test resources are organized into three main categories:
1. **Datasets**: Structured data for testing various system capabilities
2. **Documents**: Text-based files for document processing tests
3. **Images**: Image files for OCR and visual processing tests

## Directory Structure

```
test_resources/
├── datasets/      # Test datasets (JSON, CSV, etc.)
├── documents/     # Document files for processing tests
└── images/        # Image files for OCR tests
```

## Datasets

- `test_queries.json`: Contains sample queries for intent classification testing
- `employee_data.csv`: Sample CSV dataset for data analysis feature testing
- `Housing.csv`: Housing dataset for data analysis testing
- `Thyroid_Diff.csv`: Thyroid disease dataset for data analysis testing
- `Unemployment_Canada_1976_present.csv`: Unemployment dataset for data analysis testing
- `architecture_building_projects.csv`: Architecture and construction project dataset for industry-specific testing
- `construction_materials_properties.csv`: Construction materials properties dataset for structural analysis testing
- `architecture_construction_test_dataset.json`: Architecture and construction test specifications

## Documents

- `sample_ai_basics.md`: Sample document with AI basics for RAG system testing
- `retrieval_augmented_generation.md`: Documentation on RAG systems for knowledge retrieval testing

## Images

- `test_ocr_image.png`: Test image with English text for OCR functionality
- `test_chinese_ocr_image.png`: Test image with Chinese text for multilingual OCR testing
- Various visualization images for Chinese analysis testing
- `architectural_floor_plan.png`: Architectural floor plan image for construction OCR testing
- `construction_detail_drawing.png`: Construction detail drawing for structural analysis testing

## Adding New Resources

When adding new test resources:
1. Place datasets in the `datasets/` directory
2. Place document files in the `documents/` directory
3. Place image files in the `images/` directory
4. Update this documentation as needed