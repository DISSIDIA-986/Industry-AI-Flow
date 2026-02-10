# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

Local miniconda is available. Either create a new virtual environment or use the base environment (which has common data analysis and ML libraries pre-installed).

```bash
# Option 1: New environment
conda create -n ai_workflow python=3.10
conda activate ai_workflow
pip install -r backend/requirements.txt

# Option 2: Use base environment
conda activate base
pip install -r backend/requirements.txt
```

## Common Commands

```bash
# Setup (first time only)
make setup                              # Initialize environment, DB, models
bash scripts/verify_env.sh              # Verify environment setup

# Development
make start                              # Start FastAPI at localhost:8000
make test                               # Run RAG accuracy tests
make clean                              # Truncate database tables

# Document operations
python scripts/import_docs.py ./samples/    # Bulk import documents
python scripts/test_rag.py                  # Evaluate RAG accuracy

# Single test query
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "your question here", "top_k": 3}'

# Rebuild BM25 index after bulk imports
# The BM25 index is built automatically on first query, but can be pre-built
```

## Project Overview

A local Mac-based RAG (Retrieval-Augmented Generation) system for intelligent Q&A over private documents. Supports PDF, TXT, and images via OCR.

**Tech Stack**: Ollama (qwen2.5:7b) + PostgreSQL/pgvector + FastAPI + nomic-embed-text + BM25/RRF hybrid retrieval + bge-reranker

**Acceptance Criteria (all achieved)**:
- 1000 docs vectorized in <10 min
- P95 query latency <10s
- >70% accuracy on test questions
- 30-min stability without crashes

## Architecture

```
User → FastAPI → RAG Engine → [HybridRetriever + Reranker] → VectorStore → Ollama LLM
                     ↓
              DocumentLoader → Chunker → Embedder → pgvector
```

### Key Services (`backend/services/`)

| File | Purpose |
|------|---------|
| `rag_engine.py` | Main RAG orchestrator - coordinates retrieval, reranking, and generation |
| `retrieval/hybrid_search.py` | BM25 + vector search with RRF fusion (70% vector, 30% BM25) |
| `retrieval/reranker.py` | bge-reranker-base for result re-ranking |
| `vectorstore.py` | pgvector operations (store, search, document/chunk management) |
| `embedder.py` | nomic-embed-text-v1.5 (768-dim) embeddings |
| `document_loader.py` | PDF/TXT extraction + PaddleOCR for images |
| `chunker.py` | Text chunking (default: 300 chars, 50 overlap) |
| `ollama_client.py` | Ollama API client |

### Configuration (`backend/config.py`)

All settings via environment variables or `.env` file:
- `OLLAMA_MODEL`: LLM model (default: qwen2.5:7b)
- `EMBEDDING_MODEL`: Embedding model (default: nomic-ai/nomic-embed-text-v1.5)
- `CHUNK_SIZE`/`CHUNK_OVERLAP`: Document chunking params
- `OCR_LANG`: OCR language (en, ch, en+ch)
- `TOP_K`: Default retrieval count

## RAG Query Flow

1. **Hybrid Retrieval**: Query → embed + BM25 tokenize (jieba for Chinese) → retrieve top_k*2 from both → RRF (Reciprocal Rank Fusion) with weights (70% vector, 30% BM25)
2. **Reranking**: bge-reranker scores fused results → return top_k
3. **Generation**: Build context from chunks → Ollama generates answer with citations

**Key Implementation Details**:
- BM25 index built lazily on first query or after bulk imports
- RRF fusion formula: `score = vector_weight/rank + bm25_weight/rank`
- Reranker triggered when `use_reranker=True` (default)
- Chinese text supported via jieba tokenization

## Documentation Structure

The `docs/` directory contains all project documentation:

- **`docs/research/`** - Core research and planning documents
  - `best-ai-workflow.plan.md` - Synthesized architecture from 6 AI analyses
  - `local-development-feasibility.md` - Mac local development guide
  - `best-document-archiving.plan.md` - Document classification/storage design
  - Individual AI platform analyses (`claude.plan.md`, `gemini.plan.md`, etc.)

- **`docs/reports/`** - Phase completion reports
  - `PHASE1_REPORT.md`, `PHASE2_REPORT.md`, `PHASE2_COMPLETE.md`
  - `OCR_OPTIMIZATION.md`

- **`docs/proposals/`** - Feature proposals for future phases
  - `METADATA_RETRIEVAL_PROPOSAL.md`

- **`docs/prompts/`** - Development prompts used during Vibe Coding
- **`docs/archive/`** - Historical working notes and drafts

## Prerequisites

- macOS M1/M2/M3 with 16GB+ RAM
- PostgreSQL 14+ (via homebrew) with pgvector extension
- Redis (via homebrew)
- Ollama with qwen2.5:7b and nomic-embed-text models

## Important Implementation Notes

**Database Schema**:
- `documents` table: Stores document metadata (id, filename, created_at)
- `document_chunks` table: Stores chunked text with embeddings (id, doc_id, chunk_id, content, embedding vector[768])
- pgvector index: Used for fast similarity search on embedding column

**Retrieval Strategies**:
- Pure vector search: `use_hybrid_search=False` in SimpleRAG
- Hybrid search (default): BM25 + vector with RRF fusion
- Optional reranking: `use_reranker=True` (default, improves accuracy significantly)

**Performance Considerations**:
- BM25 index rebuilds on each initialization (stores in-memory)
- For large document sets (>1000), consider pre-building index
- Chinese text requires jieba tokenization (auto-handled)
- OCR processing is CPU-intensive; batch imports recommended
