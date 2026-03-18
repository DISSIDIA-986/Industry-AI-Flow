# Progress Report -- Phase 3

**Project:** Industry AI Flow -- AI-Powered Construction Industry Platform

**Program:** Integrated Artificial Intelligence, SAIT Capstone Project

**Team Members:**
- Angel Daniel Bustamante Perez
- Jason Niu
- Jack Si

**Instructor:** Reeta

**Date:** March 2026

---

## Project Status Summary

Our system is feature-complete with all three core capabilities working: RAG Knowledge QA, Construction Cost Estimation, and Dynamic Data Analysis. We are now focused on ensuring demo stability, completing final testing, and preparing for the Capstone Showcase.

---

## Task Distribution

### Jason Niu -- Software Development Lead

| Task | Status | Description |
|------|--------|-------------|
| System architecture design | Complete | Designed 6-layer architecture with 3 AI runtime paths |
| Backend API development | Complete | FastAPI with 10+ route modules, authentication, tenant isolation |
| RAG pipeline implementation | Complete | Hybrid search (BM25 + vector + RRF), BGE reranker, groundedness check |
| Intent classification system | Complete | 11-node LangGraph StateGraph with multi-turn clarification |
| Cost estimation ML model | Complete | Ridge regression, 5-fold CV, R^2 = 0.989 |
| Code execution sandbox | Complete | Docker-based isolated Python execution with security hardening |
| LLM integration (Ollama) | Complete | Qwen3.5:4b/9b with Metal GPU, hybrid local/cloud dispatch |
| Frontend development | Complete | Next.js App Router with chat, dashboard, cost estimation pages |
| Testing & quality gates | Complete | 516+ unit tests, 70% coverage, 11-gate release validation |
| Performance optimization | Complete | Query caching, BM25 throttling, connection pooling |
| Documentation | Complete | Architecture docs, API reference, deployment guide |

### Jack Si -- Construction Domain Expert

| Task | Status | Description |
|------|--------|-------------|
| Construction document collection | Complete | Curated ~12 industry documents (safety, codes, guides) |
| Cost estimation dataset | Complete | Provided 10,000-row construction project dataset |
| Domain knowledge validation | Complete | Verified RAG answers against industry knowledge |
| Feature selection for cost model | Complete | Identified key cost drivers: change orders, risk score, contractor rating |
| User acceptance testing | Complete | Tested system from construction professional perspective |
| Demo scenario preparation | In Progress | Preparing realistic demo queries and workflows |

### Angel Daniel Bustamante Perez -- Project Support

| Task | Status | Description |
|------|--------|-------------|
| Project coordination | Complete | Team communication and milestone tracking |
| Document preparation | In Progress | Assignment submissions and presentation materials |
| Testing support | Complete | Assisted with system testing and bug reporting |

---

## Milestones

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Phase 1: Project proposal | Completed | Done |
| Phase 2: Data collection & preprocessing | Completed | Done |
| Phase 3: System architecture design | March 2026 | Done |
| Core RAG pipeline functional | Completed | Done |
| Cost estimation model trained & integrated | Completed | Done |
| Dynamic data analysis with code sandbox | Completed | Done |
| Frontend UI complete | Completed | Done |
| 36 rounds of test-driven improvement | Completed | Done |
| Demo preparation & rehearsal | Late March 2026 | In Progress |
| Capstone Showcase | Late March / Early April 2026 | Upcoming |

---

## Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| Ollama LLM performance slower than expected | We switched to the smaller Qwen3.5:4b model and made sure Metal GPU acceleration was enabled |
| PaddleOCR incompatible with Python 3.14 | We locked our environment to Python 3.13.x and used PaddleOCR's nightly build |
| Intent classification getting stuck in loops | We added a MAX_CLARIFICATION_ROUNDS = 2 limit to prevent infinite recursion |
| Code sandbox had security vulnerabilities | We ran 9 rounds of iterative security hardening to patch bypass issues |
| RAG queries were too slow for demo | We added response caching, throttled BM25 index rebuilds, and reused TCP connections |

---

## Next Steps

1. Final demo rehearsal with realistic construction scenarios
2. Prepare presentation slides for Capstone Showcase
3. Ensure system stability under sustained demo usage
4. Complete remaining assignment submissions
