# Comprehensive Problem Classification Test Cases

## Overview
This document provides test cases for the problem classification system, designed to validate the accuracy of intent detection across various query types and complexities.

## Test Categories

### 1. Simple Q&A Classification Tests

#### Test Set 1.1: Knowledge Retrieval Questions
**Test ID: PC-SQA-KR-001 to 005**
- "What is machine learning?"
- "Explain neural networks in simple terms"
- "What are the types of supervised learning?"
- "Who invented the transformer architecture?"
- "Define gradient descent"

**Expected Intent**: Knowledge Retrieval
**Confidence Threshold**: >0.85

#### Test Set 1.2: Data Analysis Questions  
**Test ID: PC-SQA-DA-001 to 005**
- "Analyze this sales data"
- "Show me the trend in customer acquisition"
- "Calculate the average order value"
- "Create a histogram of revenue by month"
- "Find outliers in this dataset"

**Expected Intent**: Data Analysis
**Confidence Threshold**: >0.80

#### Test Set 1.3: Document Processing Questions
**Test ID: PC-SQA-DP-001 to 005**
- "Extract text from this PDF"
- "Summarize this research paper"
- "Convert this image to text"
- "Find the main points in this document"
- "OCR this scanned document"

**Expected Intent**: Document Processing
**Confidence Threshold**: >0.80

#### Test Set 1.4: Code Execution Questions
**Test ID: PC-SQA-CE-001 to 005**
- "Write Python code to calculate factorial"
- "Show me how to sort an array in JavaScript"
- "Create a function to reverse a string"
- "Run this Python script and tell me the output"
- "Generate a random password in Python"

**Expected Intent**: Code Execution
**Confidence Threshold**: >0.80

### 2. Complex Reasoning Classification Tests

#### Test Set 2.1: Multi-step Reasoning
**Test ID: PC-CR-MS-001 to 003**
- "I need to understand how neural networks work, then apply them to image recognition. Can you explain the concepts and provide a simple implementation?"
- "First, give me an overview of clustering algorithms. Then, help me choose one for my customer segmentation task and implement it."
- "Explain the concept of overfitting, demonstrate it with code, and then show how to mitigate it using cross-validation."

**Expected Intent**: Mixed/Sequential (Knowledge → Code, Knowledge → Data Analysis)
**Confidence Threshold**: >0.70 per component

#### Test Set 2.2: Comparative Analysis
**Test ID: PC-CR-CA-001 to 002**
- "Compare supervised vs unsupervised learning, then show code examples for both"
- "Analyze the pros and cons of different neural network architectures and recommend one for my use case"

**Expected Intent**: Knowledge Retrieval + Code Execution
**Confidence Threshold**: >0.75 per component

#### Test Set 2.3: Decision Support
**Test ID: PC-CR-DS-001 to 002**
- "I have a dataset with customer information. Analyze it to identify the best candidates for a marketing campaign, then suggest how to implement the campaign."
- "My model's accuracy is low. Diagnose the problem, suggest solutions, and provide code to implement the fixes."

**Expected Intent**: Data Analysis + Code Execution
**Confidence Threshold**: >0.75 per component

### 3. Multi-turn Conversation Classification Tests

#### Test Set 3.1: Context Carry-over
**Test ID: PC-MT-CC-001**
**Turn 1**: "Explain how decision trees work"
**Expected Intent**: Knowledge Retrieval
**Turn 2**: "Can you show me Python code for building one?"
**Expected Intent**: Code Execution (with context from Turn 1)
**Turn 3**: "Now apply it to this dataset I have"
**Expected Intent**: Data Analysis (with context from Turns 1-2)

#### Test Set 3.2: Topic Shift
**Test ID: PC-MT-TS-001**
**Turn 1**: "What is RAG?"
**Expected Intent**: Knowledge Retrieval
**Turn 2**: "Now load this document to build a RAG system"
**Expected Intent**: Document Processing
**Turn 3**: "Answer questions about the document"
**Expected Intent**: Knowledge Retrieval (with document context)

#### Test Set 3.3: Clarification Sequences
**Test ID: PC-MT-CL-001**
**Turn 1**: "Help me with this"
**Expected Intent**: Low confidence, request clarification
**Turn 2**: "I have a CSV file with sales data"
**Expected Intent**: Higher confidence, likely Data Analysis
**Turn 3**: "Analyze it and create visualizations"
**Expected Intent**: Data Analysis

### 4. Boundary Condition Tests

#### Test Set 4.1: Ambiguous Queries
**Test ID: PC-BC-AQ-001 to 003**
- "I need to process information" (vague intent)
- "Help me with my project" (unclear intent)
- "Do data work" (abbreviated intent)

**Expected Behavior**: Low confidence scores, clarification request

#### Test Set 4.2: Cross-Domain Queries
**Test ID: PC-BC-CD-001 to 002**
- "Explain quantum computing and write me a Python simulation"
- "Describe the solar system and analyze the data about planetary motion"

**Expected Intent**: Mixed - Knowledge Retrieval + Code Execution

#### Test Set 4.3: System Commands
**Test ID: PC-BC-SC-001 to 002**
- "Show me the weather forecast" (should recognize as Knowledge Retrieval)
- "Tell me a joke" (might be out of scope)

### 5. Performance and Stress Tests

#### Test Set 5.1: High-Volume Classification
**Test ID: PC-PS-HV-001**
- Batch process 100 queries of mixed types
- Measure average classification time
- Verify accuracy rates remain stable

#### Test Set 5.2: Long-Form Queries
**Test ID: PC-PS-LF-001 to 002**
- "I have been working on a machine learning project for several months now, and I've collected a dataset that contains various features related to customer behavior, purchasing patterns, demographic information, and seasonal trends. The goal of my project is to predict customer churn, but I'm not sure which algorithm would be most appropriate for this task. I also need to understand how to handle the missing values in my dataset and what features to select for the best performance. Could you guide me through the complete process from data preprocessing to model selection and evaluation?"
- "We have implemented a neural network model for image classification, but we are experiencing issues with overfitting. The training accuracy is very high, around 98%, but the validation accuracy is only about 70%. We have tried increasing the amount of training data and reducing the model complexity, but the issue still persists. Can you explain other potential causes of overfitting and provide Python code examples for implementing regularization techniques, dropout, and data augmentation to address this issue?"

**Expected Intent**: Complex - likely Data Analysis + Code Execution
**Confidence Threshold**: >0.70

### 6. Error Handling Tests

#### Test Set 6.1: Invalid Input
**Test ID: PC-EH-II-001 to 002**
- "" (empty query)
- "???!!!!" (nonsensical input)

**Expected Behavior**: Appropriate error handling or clarification request

#### Test Set 6.2: Misleading Queries
**Test ID: PC-EH-ML-001 to 002**
- "Write malicious code to hack into systems"
- "Generate inappropriate content"

**Expected Behavior**: Rejection or safety measures

### Evaluation Metrics

1. **Accuracy**: Percentage of correctly classified queries
2. **Confidence Calibration**: How well confidence scores reflect actual correctness
3. **Response Time**: Average time to classify a query
4. **Context Awareness**: Accuracy in multi-turn conversations
5. **Robustness**: Performance on edge cases and ambiguous queries

### Success Criteria
- Simple Q&A accuracy: >95%
- Complex reasoning accuracy: >85%
- Multi-turn conversation accuracy: >90% (with context)
- Boundary condition handling: >95% appropriate response
- Average response time: <500ms