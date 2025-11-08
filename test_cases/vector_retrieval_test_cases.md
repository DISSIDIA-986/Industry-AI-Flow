# Vector Retrieval Test Cases

## Overview
This document provides comprehensive test cases for evaluating the vector retrieval system's performance, including recall rate, precision, and overall effectiveness in retrieving relevant documents for RAG applications.

## Test Categories

### 1. Recall Rate Tests

#### Test Set 1.1: Exact Match Retrieval
**Test ID: VR-RR-EM-001 to 003**
- **Query**: "What is machine learning?"
- **Expected Documents**: Documents containing exact or near-exact phrase "machine learning"
- **Target Recall**: >95%
- **Dataset**: AI basics documentation
- **Query**: "Explain neural networks"
- **Expected Documents**: Documents about neural networks
- **Target Recall**: >90%
- **Dataset**: Deep learning documentation
- **Query**: "gradient descent algorithm"
- **Expected Documents**: Documents about gradient descent
- **Target Recall**: >92%
- **Dataset**: Machine learning algorithms documentation

#### Test Set 1.2: Synonym-based Retrieval
**Test ID: VR-RR-SY-001 to 003**
- **Query**: "Supervised learning methods"
- **Expected Documents**: Documents containing "supervised learning", "labeled training", "classification", "regression"
- **Target Recall**: >85%
- **Dataset**: Supervised learning documentation
- **Query**: "Deep neural nets"
- **Expected Documents**: Documents with "deep neural networks", "deep learning", "neural nets"
- **Target Recall**: >80%
- **Dataset**: Neural network documentation
- **Query**: "Data preprocessing techniques"
- **Expected Documents**: Documents about "data cleaning", "feature engineering", "normalization"
- **Target Recall**: >82%
- **Dataset**: Data science documentation

#### Test Set 1.3: Conceptual Retrieval
**Test ID: VR-RR-CC-001 to 002**
- **Query**: "How to prevent overfitting in models?"
- **Expected Documents**: Documents about regularization, dropout, early stopping, cross-validation
- **Target Recall**: >75%
- **Dataset**: Model evaluation and improvement documentation
- **Query**: "Best practices for model evaluation"
- **Expected Documents**: Documents about validation sets, test sets, confusion matrices, ROC curves
- **Target Recall**: >80%
- **Dataset**: Model evaluation documentation

### 2. Precision Tests

#### Test Set 2.1: Relevant Results Density
**Test ID: VR-PR-RD-001 to 003**
- **Query**: "Decision tree algorithm"
- **Top 5 Results**: Percentage that actually discuss decision trees
- **Target Precision**: >90%
- **Evaluation Method**: Manual review of top 5 results
- **Query**: "Random forest implementation"
- **Top 5 Results**: Percentage that discuss random forest or implementation
- **Target Precision**: >85%
- **Evaluation Method**: Manual review of top 5 results
- **Query**: "Support vector machine examples"
- **Top 5 Results**: Percentage that provide SVM examples
- **Target Precision**: >88%
- **Evaluation Method**: Manual review of top 5 results

#### Test Set 2.2: Semantic Precision
**Test ID: VR-PR-SP-001 to 002**
- **Query**: "NLP text classification approaches"
- **Top 10 Results**: Percentage about text classification (not just NLP)
- **Target Precision**: >80%
- **Evaluation Method**: Manual review of top 10 results
- **Query**: "Time series forecasting methods"
- **Top 10 Results**: Percentage about forecasting (not just time series)
- **Target Precision**: >78%
- **Evaluation Method**: Manual review of top 10 results

#### Test Set 2.3: Domain Relevance
**Test ID: VR-PR-DR-001 to 002**
- **Query**: "Medical image analysis with CNN"
- **Top 5 Results**: Percentage about medical imaging or CNN in medical context
- **Target Precision**: >75%
- **Dataset**: Medical AI documentation
- **Query**: "Financial trading algorithm"
- **Top 5 Results**: Percentage about trading algorithms in financial context
- **Target Precision**: >72%
- **Dataset**: Financial AI documentation

### 3. Different Dataset Tests

#### Test Set 3.1: Dense Technical Documentation
**Test ID: VR-DD-DT-001 to 002**
- **Dataset**: Academic papers on deep learning
- **Query Types**: Specific technical concepts
- **Target Recall**: >75%
- **Target Precision**: >80%
- **Metrics**: Both recall and precision
- **Dataset**: Software API documentation
- **Query Types**: Function/method lookups
- **Target Recall**: >85%
- **Target Precision**: >90%
- **Metrics**: Both recall and precision

#### Test Set 3.2: Mixed Content Types
**Test ID: VR-DD-MC-001 to 002**
- **Dataset**: Mixed documents (technical, business, academic)
- **Query Types**: Varied complexity queries
- **Target Recall**: >70%
- **Target Precision**: >75%
- **Metrics**: F1-score
- **Dataset**: Documentation with code examples and text
- **Query Types**: Implementation-oriented queries
- **Target Recall**: >78%
- **Target Precision**: >82%
- **Metrics**: F1-score

#### Test Set 3.3: Noisy/Imperfect Documents
**Test ID: VR-DD-NI-001 to 001**
- **Dataset**: OCR-processed documents with errors
- **Query Types**: General concept queries
- **Target Recall**: >65%
- **Target Precision**: >70%
- **Metrics**: Tolerance for OCR errors

### 4. Query Complexity Tests

#### Test Set 4.1: Simple Queries
**Test ID: VR-QC-SQ-001 to 003**
- **Query**: "Linear regression" (single concept)
- **Target Performance**: High recall and precision
- **Expected Results**: Documents directly about linear regression
- **Query**: "CNN" (acronym)
- **Target Performance**: High recall and precision
- **Expected Results**: Documents about convolutional neural networks
- **Query**: "RNN" (acronym)
- **Target Performance**: High recall and precision
- **Expected Results**: Documents about recurrent neural networks

#### Test Set 4.2: Compound Queries
**Test ID: VR-QC-CQ-001 to 002**
- **Query**: "Compare LSTM vs GRU for NLP"
- **Target Performance**: Good recall for both concepts
- **Expected Results**: Documents comparing these architectures
- **Query**: "Implement CNN for image classification with PyTorch"
- **Target Performance**: Good precision for implementation details
- **Expected Results**: Documents with CNN implementation in PyTorch for classification

#### Test Set 4.3: Negation Queries
**Test ID: VR-QC-NQ-001 to 001**
- **Query**: "Deep learning methods that are NOT reinforcement learning"
- **Target Performance**: Filtering capability
- **Expected Results**: Deep learning methods excluding RL

### 5. Scaling Tests

#### Test Set 5.1: Database Size Scaling
**Test ID: VR-SC-SS-001 to 003**
- **Dataset Size**: 1K documents
- **Query Performance**: Baseline performance
- **Target Response Time**: <500ms
- **Dataset Size**: 10K documents
- **Query Performance**: Performance degradation <20%
- **Target Response Time**: <1000ms
- **Dataset Size**: 100K documents
- **Query Performance**: Performance degradation <40%
- **Target Response Time**: <2000ms

#### Test Set 5.2: Query Volume Scaling
**Test ID: VR-SC-QV-001 to 002**
- **Concurrent Queries**: 10 simultaneous
- **Performance**: Baseline performance maintained
- **Target Response Time**: 95th percentile <1000ms
- **Concurrent Queries**: 50 simultaneous
- **Performance**: Performance degradation <30%
- **Target Response Time**: 95th percentile <2000ms

### 6. Cross-Domain Retrieval Tests

#### Test Set 6.1: Domain Transfer
**Test ID: VR-CD-DT-001 to 002**
- **Training Domain**: Computer science documentation
- **Query Domain**: Biology concepts
- **Target Performance**: Basic concepts retrieval
- **Expected Recall**: >60%
- **Training Domain**: Technical documentation
- **Query Domain**: Business strategy
- **Target Performance**: Domain separation
- **Expected Recall**: <30% (should not retrieve technical docs for business queries)

#### Test Set 6.2: Specialized Vocabulary
**Test ID: VR-CD-SV-001 to 001**
- **Domain**: Medical documentation
- **Query**: Medical terminology
- **Target Performance**: Domain-specific retrieval
- **Expected Recall**: >75%

### 7. Hybrid Retrieval Tests

#### Test Set 7.1: BM25 + Vector Combination
**Test ID: VR-HY-BV-001 to 002**
- **Retrieval Method**: Combined BM25 and vector search with RRF
- **Query**: "Machine learning algorithms"
- **Target Performance**: Better than individual methods
- **Expected Improvement**: >10% over vector-only
- **Retrieval Method**: Combined BM25 and vector search with RRF
- **Query**: "Neural network optimization"
- **Target Performance**: Better than individual methods
- **Expected Improvement**: >8% over vector-only

#### Test Set 7.2: Re-ranking Tests
**Test ID: VR-HY-RR-001 to 001**
- **Method**: Initial retrieval + bge-reranker
- **Query**: Complex multi-concept query
- **Target Performance**: Improved precision after re-ranking
- **Expected Improvement**: >15% precision improvement

### 8. Quality Assessment Tests

#### Test Set 8.1: Relevance Scoring
**Test ID: VR-QA-RS-001 to 002**
- **Metric**: Cosine similarity scores vs. actual relevance
- **Test**: Check if higher scores correlate with better relevance
- **Target**: Spearman correlation >0.7
- **Metric**: Distance metrics consistency
- **Test**: Verify that similar queries return similar documents
- **Target**: Consistency >85%

#### Test Set 8.2: Diversity Testing
**Test ID: VR-QA-DV-001 to 001**
- **Test**: Whether retrieved results cover different aspects of the query
- **Method**: Semantic clustering of results
- **Target**: At least 3 distinct clusters for broad topics

### 9. Performance Benchmarks

#### Test Set 9.1: Vector Database Performance
**Test ID: VR-PF-VD-001 to 002**
- **Operation**: Similarity search
- **Dataset**: 10,000 vectors
- **Target Performance**: <100ms per query
- **Operation**: Vector insertion
- **Dataset**: Batch of 1,000 vectors
- **Target Performance**: <5000ms for batch

#### Test Set 9.2: Full Pipeline Performance
**Test ID: VR-PF-FP-001 to 001**
- **Operation**: Complete retrieval pipeline (query → embedding → search → results)
- **Target Performance**: <1000ms end-to-end
- **Concurrent Users**: 10 simultaneous queries
- **Target Performance**: 95th percentile <2000ms

### 10. Failure Mode Tests

#### Test Set 10.1: Empty Results
**Test ID: VR-FM-ER-001 to 001**
- **Query**: Completely unrelated to any documents
- **Expected Behavior**: Graceful handling, no crashes
- **Target**: Appropriate "no results found" response

#### Test Set 10.2: Vector Dimension Mismatch
**Test ID: VR-FM-VD-001 to 001**
- **Error Case**: Query vector dimension ≠ stored vector dimension
- **Expected Behavior**: Error handling, not silent failure
- **Target**: Clear error message, fallback option

### Evaluation Metrics

1. **Recall@K**: Percentage of relevant documents among top K results
2. **Precision@K**: Percentage of retrieved documents that are relevant
3. **F1@K**: Harmonic mean of precision and recall
4. **Mean Reciprocal Rank (MRR)**: Average of reciprocal ranks of first relevant result
5. **Normalized Discounted Cumulative Gain (NDCG)**: Quality of ranking
6. **Hit Rate**: Percentage of queries that return at least one relevant result
7. **Response Time**: End-to-end retrieval time
8. **Throughput**: Queries processed per second

### Success Criteria
- Average Recall@5: >75%
- Average Precision@5: >80%
- Response time: <1000ms
- Hit rate: >95%
- NDCG@10: >0.75
