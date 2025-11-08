# Intent Classification and System Workflow Test Cases

## Overview
This document contains test cases for the intent classification system and overall workflow in the Industry AI Flow project. These tests cover the four main intent categories and their routing mechanisms.

## Test Case 1: Intent Classification Accuracy
- **Objective**: Verify the system correctly identifies user intents
- **Target Intents**:
  - Knowledge Retrieval (RAG)
  - Data Analysis
  - Document Processing
  - Code Execution
- **Steps**:
  1. Submit test queries for each intent category
  2. Check classification results
  3. Verify confidence scores
- **Expected Result**: System correctly identifies intent with confidence >0.8 for clear queries

## Test Case 2: Confidence-Based Clarification
- **Objective**: Test clarification mechanism for low-confidence queries
- **Threshold**: <0.8 confidence triggers clarification
- **Steps**:
  1. Submit ambiguous query
  2. Check confidence score
  3. Verify clarification dialog triggered
  4. Confirm user can specify intent
- **Expected Result**: System prompts for clarification when confidence is low

## Test Case 3: Knowledge Retrieval Routing
- **Objective**: Test routing to RAG system for knowledge questions
- **Sample Queries**:
  - "What is machine learning?"
  - "Explain neural networks"
- **Steps**:
  1. Submit knowledge-based query
  2. Verify intent classification as "Knowledge Retrieval"
  3. Route to RAG engine
  4. Check for relevant document retrieval
- **Expected Result**: Query is properly routed to RAG system with relevant results

## Test Case 4: Data Analysis Routing
- **Objective**: Test routing to data analysis tools
- **Sample Queries**:
  - "Analyze this dataset"
  - "Show me a chart of sales data"
- **Steps**:
  1. Submit data analysis query
  2. Verify intent classification as "Data Analysis"
  3. Route to data analysis agent
  4. Check for appropriate data tools activation
- **Expected Result**: Query is routed to data analysis system with proper tool usage

## Test Case 5: Document Processing Routing
- **Objective**: Test routing to document processing system
- **Sample Queries**:
  - "Extract text from this PDF"
  - "Summarize this document"
- **Steps**:
  1. Submit document processing query
  2. Verify intent classification as "Document Processing"
  3. Route to document processing agent
  4. Check for OCR or parsing tools activation
- **Expected Result**: Query is routed to document processing system with appropriate tools

## Test Case 6: Code Execution Routing
- **Objective**: Test routing to code execution environment
- **Sample Queries**:
  - "Write a Python function to calculate Fibonacci"
  - "Run this code snippet"
- **Steps**:
  1. Submit code execution query
  2. Verify intent classification as "Code Execution"
  3. Route to code execution agent
  4. Check for code generation and execution tools
- **Expected Result**: Query is routed to code execution system with secure execution

## Test Case 7: Context-Aware Classification
- **Objective**: Test classification with conversation history
- **Features**:
  - Session context awareness
  - User preference learning
  - Follow-up query understanding
- **Steps**:
  1. Establish conversation context
  2. Submit follow-up query
  3. Check context-aware classification
- **Expected Result**: System correctly interprets follow-up queries in context

## Test Case 8: API Integration Testing
- **Objective**: Test API endpoints for intent classification
- **Endpoints**:
  - `/health` - System health check
  - `/rag/query` - RAG query endpoint
  - `/intent/classify` - Intent classification endpoint
- **Steps**:
  1. Test each endpoint with valid requests
  2. Verify response formats
  3. Check for proper error handling
- **Expected Result**: All API endpoints respond correctly with proper data formats

## Test Case 9: Error Handling and Fallbacks
- **Objective**: Test system behavior when individual components fail
- **Failure Scenarios**:
  - LLM unavailable
  - Vector database down
  - OCR processing failure
  - Code execution sandbox issues
- **Steps**:
  1. Simulate component failures
  2. Verify fallback mechanisms
  3. Check graceful degradation
- **Expected Result**: System continues operating with fallback options

## Test Case 10: Performance Under Load
- **Objective**: Test system performance with concurrent requests
- **Metrics**:
  - Response time <5 seconds
  - Throughput of 10+ queries per minute
  - Memory usage under 2GB
- **Steps**:
  1. Send concurrent requests
  2. Monitor response times
  3. Check system resource usage
- **Expected Result**: System maintains performance under expected load

## Test Case 11: Multi-Agent Coordination
- **Objective**: Test coordination between different agents
- **Scenario**: Complex query requiring multiple agents
- **Steps**:
  1. Submit complex query
  2. Observe agent handoff behavior
  3. Verify result synthesis
- **Expected Result**: Multiple agents coordinate effectively to answer complex queries

## Test Case 12: Document Processing with OCR
- **Objective**: Test document processing that involves OCR
- **Document Types**:
  - PDF files
  - Image files (PNG, JPG)
  - Scanned documents
- **Steps**:
  1. Submit document requiring OCR
  2. Verify OCR processing
  3. Check text extraction quality
  4. Route to appropriate downstream agent
- **Expected Result**: Documents are processed with OCR when needed, then routed correctly

## Quality Metrics
- **Intent Classification Accuracy**: >=90% for clear intent queries
- **Response Time**: <5 seconds for 95% of queries
- **System Availability**: >99% uptime
- **Memory Usage**: <2GB under normal load

## Known Limitations
- Performance metrics may vary based on hardware
- Intent classification accuracy depends on training data quality
- Complex multi-intent queries may require additional handling