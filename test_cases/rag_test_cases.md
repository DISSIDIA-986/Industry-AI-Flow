# RAG Engine Test Cases

## Overview
This document contains test cases for the Retrieval-Augmented Generation (RAG) system in the Industry AI Flow project. These tests cover structure, integration, and workflow validation without requiring a live vector database.

## Test Case 1: RAG Engine Structure Validation
- **Objective**: Verify RAG engine class and method implementations
- **Target File**: `backend/services/rag_engine.py`
- **Required Classes**:
  - `RAGEngine`
  - `EnhancedRAGEngine`
- **Required Methods**:
  - `add_documents`
  - `query`
  - `search`
  - `delete_documents`
  - `get_stats`
- **Steps**:
  1. Check for required class definitions
  2. Verify required methods exist
  3. Validate method signatures
- **Expected Result**: All required classes and methods exist in the RAG engine

## Test Case 2: Vector Database Integration
- **Objective**: Check integration with vector database technologies
- **Integration Points**:
  - Sentence Transformers
  - FAISS
  - ChromaDB
  - Embedding generation
- **Steps**:
  1. Scan code for vector-related patterns
  2. Verify integration points exist
  3. Check for proper error handling
- **Expected Result**: Vector database integration code is present and properly structured

## Test Case 3: LLM Integration
- **Objective**: Validate integration with LLM backends
- **Supported Backends**:
  - llama.cpp
  - Ollama
  - LLM Client interface
- **Steps**:
  1. Check for LLM integration code
  2. Verify LLM client implementation
  3. Test generation method availability
- **Expected Result**: LLM integration is properly implemented and available

## Test Case 4: Document Processing
- **Objective**: Test document loading and processing functionality
- **Components**:
  - DocumentLoader
  - Text chunking
  - Configuration settings
- **Steps**:
  1. Verify document loader implementation
  2. Check chunk size and overlap settings
  3. Test text splitter functionality
- **Expected Result**: Document processing components are properly implemented

## Test Case 5: Retrieval Mechanism
- **Objective**: Validate document retrieval functionality
- **Features**:
  - Similarity search
  - Cosine similarity
  - Top-K retrieval
  - Threshold filtering
- **Steps**:
  1. Check for retrieval methods
  2. Verify similarity calculation
  3. Test top-K selection
- **Expected Result**: Retrieval mechanisms are properly implemented

## Test Case 6: Configuration Management
- **Objective**: Verify RAG system configuration
- **Configuration File**: `backend/config.py`
- **Settings**:
  - Embedding model
  - Vector DB path
  - Chunk size
  - Chunk overlap
  - Max context length
- **Steps**:
  1. Check configuration file existence
  2. Verify required settings are defined
  3. Validate default values
- **Expected Result**: All required configuration settings exist and are properly defined

## Test Case 7: Complete RAG Workflow Simulation
- **Objective**: Test the complete RAG workflow end-to-end
- **Workflow Steps**:
  1. Document loading
  2. Text chunking
  3. Vectorization
  4. Query processing
  5. Similarity search
  6. Context building
  7. Answer generation
- **Steps**:
  1. Simulate document loading
  2. Process documents into chunks
  3. Generate vectors
  4. Process user query
  5. Retrieve relevant documents
  6. Build context
  7. Generate final answer
- **Expected Result**: Complete workflow executes successfully with proper output

## Test Case 8: Error Handling
- **Objective**: Validate error handling throughout the RAG system
- **Scenarios**:
  - Document loading errors
  - Vector database errors
  - LLM connection errors
  - Invalid queries
- **Steps**:
  1. Look for try/catch blocks
  2. Check for proper logging
  3. Verify graceful error responses
- **Expected Result**: Proper error handling and logging exist throughout the system

## Test Case 9: Performance under Load
- **Objective**: Test system performance with multiple documents and queries
- **Parameters**:
  - 100+ documents
  - Multiple concurrent queries
  - Large text chunks
- **Steps**:
  1. Generate mock documents
  2. Process documents in batches
  3. Execute multiple queries
  4. Measure response times
- **Expected Result**: System performs adequately under load (response times < 5 seconds)

## Test Case 10: Intent Classification Integration
- **Objective**: Test integration with intent classification system
- **Components**:
  - Query classifier
  - Intent routing
  - Confidence scoring
- **Steps**:
  1. Verify classifier integration
  2. Test intent routing to RAG
  3. Check confidence threshold handling
- **Expected Result**: Queries are properly routed to RAG system based on intent

## Quality Metrics
- **Success Rate**: >=75% of tests should pass for acceptable implementation
- **Response Time**: Queries should respond in under 5 seconds
- **Accuracy**: Retrieved documents should be >80% relevant to query
- **Robustness**: System should handle edge cases gracefully

## Known Limitations
- These tests do not require live vector database or LLM
- Results may vary when run with actual data
- Performance metrics may differ with real-world data