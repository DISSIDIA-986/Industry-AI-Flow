# Extended Problem Classification Test Cases

## Overview
This document provides extended test cases for the problem classification system, designed to validate the accuracy of intent detection across various domains and complexity levels.

## Extended Test Categories

### 1. Domain-Specific Classification Tests

#### Test Set 1.1: Healthcare Domain
**Test ID: PC-ED-HD-001 to 003**
- "What are the symptoms of diabetes?"
- "Explain the treatment options for hypertension"
- "How does machine learning improve medical diagnosis?"

**Expected Intent**: Knowledge Retrieval
**Domain**: Healthcare
**Confidence Threshold**: >0.80

#### Test Set 1.2: Finance Domain
**Test ID: PC-ED-FD-001 to 003**
- "Calculate the ROI for this investment portfolio"
- "Analyze the risk factors in our current financial model"
- "Explain compound interest and its calculation"

**Expected Intent**: Data Analysis / Knowledge Retrieval
**Domain**: Finance
**Confidence Threshold**: >0.85

#### Test Set 1.3: Technology Domain
**Test ID: PC-ED-TD-001 to 003**
- "Compare the performance of React vs Vue.js for web development"
- "Write a Python script to optimize database queries"
- "How does blockchain technology work?"

**Expected Intent**: Knowledge Retrieval / Code Execution
**Domain**: Technology
**Confidence Threshold**: >0.82

### 2. Multi-turn Conversation Tests (Extended)

#### Test Set 2.1: Context Inheritance
**Test ID: PC-ED-CI-001**
**Turn 1**: "I have sales data from last quarter. Can you analyze it?"
**Expected Intent**: Data Analysis
**Turn 2**: "Show me a comparison with the previous quarter"
**Expected Intent**: Data Analysis (with context from Turn 1)
**Turn 3**: "Visualize the trends you found"
**Expected Intent**: Data Analysis with Visualization (with context from Turns 1-2)

#### Test Set 2.2: Topic Divergence Handling
**Test ID: PC-ED-TD-001**
**Turn 1**: "Explain how neural networks work" (Knowledge Retrieval)
**Expected Intent**: Knowledge Retrieval
**Turn 2**: "Now show me the Python code for a simple neural network" (Code Execution)
**Expected Intent**: Code Execution
**Turn 3**: "Run this code with sample data" (Code Execution)
**Expected Intent**: Code Execution

### 3. Ambiguity Resolution Tests

#### Test Set 3.1: Context-Dependent Classification
**Test ID: PC-ED-CD-001 to 002**
- "Calculate this" (when preceded by financial data) → Expected: Data Analysis
- "Calculate this" (when preceded by code snippet) → Expected: Code Execution

#### Test Set 3.2: Polymorphic Queries
**Test ID: PC-ED-PQ-001 to 002**
- "What's the best approach?" (context-dependent, based on previous conversation)
- "How would you handle this?" (requires understanding of referenced problem)

### 4. Edge Case Tests

#### Test Set 4.1: Very Short Queries
**Test ID: PC-ED-VS-001 to 003**
- "Why?" (requires context from conversation)
- "How?" (requires context from conversation)
- "When?" (requires context from conversation)

#### Test Set 4.2: Very Long Queries
**Test ID: PC-ED-VL-001**
- "I have been working on a complex multi-year project involving machine learning algorithms to predict customer churn, analyze user behavior, generate personalized recommendations, and optimize marketing campaigns for a SaaS business with millions of users, and I need to understand how to best implement a RAG system to store and retrieve all the relevant information for answering questions about this project including the technical details, business metrics, user feedback, and performance benchmarks, while also ensuring that the system can handle real-time queries and provide accurate, contextual responses based on the specific aspect of the project that the user is asking about, and I also need to consider scalability, security, and integration with our existing infrastructure - can you guide me through the process?"

**Expected Intent**: Complex multi-step guidance (likely Knowledge Retrieval + Data Analysis)
**Confidence Threshold**: >0.70
**Processing Time**: <5 seconds

### 5. Domain Transfer Tests

#### Test Set 5.1: Cross-Domain Query Handling
**Test ID: PC-ED-CD-001 to 002**
- "Explain quantum computing and show me a Python simulation" (Science + Code)
- "Describe how the stock market works and analyze this financial data" (Finance + Data Analysis)

## Performance Metrics (Extended)

1. **Domain Classification Accuracy**: Percentage of correctly identified domains
2. **Multi-turn Context Consistency**: Accuracy of maintaining context across turns
3. **Ambiguity Resolution Success**: Success rate in resolving ambiguous queries
4. **Processing Speed**: Average response time for classification
5. **Confidence Calibration**: How well confidence scores reflect actual correctness

## Success Criteria (Extended)
- Domain-specific accuracy: >85% for each major domain
- Multi-turn context accuracy: >90% maintenance
- Edge case handling: >75% accuracy
- Average response time: <300ms
- Confidence reliability: Spearman correlation >0.7 between confidence and accuracy
