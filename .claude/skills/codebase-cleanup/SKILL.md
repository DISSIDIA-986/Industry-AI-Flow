---
name: codebase-cleanup
description: |
  Capstone-aware codebase cleanup for Industry-AI-Flow with multi-expert analysis,
  soft-delete archiving, module boundary enforcement, and demo-readiness verification.
  Use this skill when:
  - Root directory has accumulated status reports, audit logs, and one-off scripts
  - Backend has duplicate modules, orphaned venvs, or EN: placeholder text
  - Frontend has duplicate page variants (-new, -integrated suffixes)
  - Module boundaries are unclear (e.g. code_executor.py vs code_executor/)
  - Preparing for capstone demo or final delivery
  - After TDI rounds to clean up accumulated test artifacts
  Triggers: "cleanup", "organize", "archive", "structure", "prepare for demo", "clean up project"
---

# Codebase Cleanup — Industry AI Flow

**SAIT Capstone demo preparation cleanup** for a 2-person construction-industry AI platform. Showcase is approximately late March / early April 2026 — demo must not crash. This skill focuses on removing confusion (duplicate modules, orphaned files) and improving clarity for evaluators reviewing the codebase.

**Three demo features that MUST NOT be broken by cleanup:**
1. RAG Knowledge QA (~12 docs in pgvector, hybrid retrieval)
2. Cost Estimation (Ridge regression on partner-provided dataset)
3. Dynamic Data Analysis (cloud LLM code generation + Docker sandbox — highest risk, untested)

**Demo hardware**: Mac Studio M1 Max 32GB or Windows 32GB+RTX5060 (undecided). Orphaned venvs consume ~4.5 GB of scarce disk space.

**Zero hard deletes** (except `__pycache__/` and orphaned venvs). All files moved to `.deprecated/` with rollback capability.

## Quick Start

```
/codebase-cleanup                     # Full analysis + execution
/codebase-cleanup --dry-run           # Preview only (no changes)
/codebase-cleanup --analyze-only      # Analysis report without execution
/codebase-cleanup --execute           # Run existing cleanup script
/codebase-cleanup --rollback          # Undo last cleanup
/codebase-cleanup --verify            # Run safety verification only
```

## Core Principles

| Principle | Implementation |
|-----------|---------------|
| Zero Hard Deletes | All files soft-moved to `.deprecated/` (except `__pycache__/`, orphaned venvs) |
| Pipeline Integrity | 10-node fixed-order workflow pipeline + 11-node intent StateGraph tested before and after every change |
| Import Chain Safety | Every move validated against `grep -r` import analysis across 150+ backend modules |
| Rollback Ready | Auto-generated `scripts/rollback_cleanup.sh` with absolute paths |
| Manifest Logging | Every move logged to `cleanup_manifest.log` with timestamp |
| Human Confirmation | Each phase requires explicit approval before proceeding |
| Demo Readiness | Final verification includes smoke test gate (`make test-demo-smoke-gate`) |
| Branch Safe | Refuses to run on `main` branch |

## Project Context

This is a **Capstone concept prototype** (not production). 2-person team: one software dev, one construction background. Evaluators judge: demo stability, presentation clarity, architecture soundness, technical decision logic.

**Non-demo features to deprioritize during cleanup**: Multi-tenant isolation (X-Tenant-ID — architecture preview only), prompt A/B testing, Prometheus metrics. These should NOT be deleted but do not need cleanup attention.

### Architecture (DO NOT TOUCH)

```
Client → FastAPI (main.py)
       → Intent Classification (heuristic + optional classifier)
       → 10-Node Workflow Pipeline (core innovation):
           intent → safety → cost_estimation → retrieval → rerank →
           prompt → route → code_exec → response → groundedness
       → Route to: RAG QA / Cost Estimation / Dynamic Data Analysis
       → Memory Update (3-layer)
       → Response with citations
```

### Known Cleanup Targets (from project audit)

| Target | Size/Count | Impact |
|--------|-----------|--------|
| Orphaned venvs (6 directories) | ~4.5 GB | Disk, git noise |
| Root-level status reports | 16 files, ~166 KB | Clutter |
| EN: placeholder text | ~250+ instances across multiple modules (partially fixed in TDI rounds 12-14, many remain) | Professionalism |
| Duplicate modules (code_executor, init_database) | 3-4 files | Confusion |
| Frontend duplicate pages (-new, -integrated) | 6 files | Confusion |
| Oversized __init__.py files | 2 files (137, 51 lines) | Maintainability |
| Scattered CLAUDE.md files | 24 files | Redundancy |
| _archived/ and .deprecated/ overlap | 2 directories | Organization |

## Execution Workflow

### Phase 1: Multi-Expert Analysis (5 parallel agents)

```
Agent 1 (Senior Architect):
  - Directory structure audit, module boundary mapping
  - Identify duplicate modules (code_executor.py vs code_executor/)
  - Map __init__.py files with implementation code (>20 lines)
  - Catalog scattered CLAUDE.md files (keep only root + backend/)

Agent 2 (RAG Expert):
  - Verify retrieval pipeline file dependencies
  - Check embedding model references across config files
  - Map hybrid_search.py → reranker.py → vectorstore.py dependency chain
  - Identify orphaned retrieval-related test fixtures

Agent 3 (LLM/AI Expert):
  - Map LLM client factory import chains (llama_cpp, ollama, zhipu)
  - Verify prompt template references in prompt_manager.py
  - Check data_analysis_agent.py lazy init pattern is preserved
  - Identify unused model configuration files

Agent 4 (QA Engineer):
  - Map test file → source file dependencies for ~129 test files
  - Identify orphaned test fixtures and conftest.py files
  - Verify test markers (unit, integration, slow, ocr, llm)
  - Check tests/unit/bugs/ files (rounds 3–14, ~22 files) reference valid source locations

Agent 5 (Security Analyst):
  - Verify .env.example has no real secrets
  - Check .gitignore covers all venv directories
  - Audit file permissions on scripts/
  - Verify no credentials in status reports before archiving
```

**Output**: Categorized file list with safety classification per expert.

### Phase 2: Cross-Validation (2 QA agents)

```
QA Agent 1: Dependency verification
  - grep all `from backend.` and `import backend.` statements
  - Check docker-compose*.yml volume mounts and service refs
  - Verify Makefile targets reference existing paths
  - Check pytest.ini testpaths and conftest.py fixture chains
  - Verify frontend/src imports don't reference moved files

QA Agent 2: Completeness audit
  - Find missed cleanup targets using patterns from Phase 1
  - Verify .gitignore covers archive directories
  - Check for orphaned references in CLAUDE.md files
  - Verify no circular imports introduced by module consolidation
```

**Output**: BLOCKER list (items that cannot be moved) + supplementary targets.

### Phase 3: Script Generation

Generate `scripts/cleanup_project.sh` with:
- `--dry-run` mode (preview all moves, execute none)
- `--execute` mode (perform moves with manifest logging)
- `--rollback` mode (reverse all moves from manifest)
- Post-cleanup integrity verification
- EN: placeholder replacement report

Also generate `scripts/rollback_cleanup.sh` with absolute paths.

### Phase 4: Execution with Safety Gates

```
Step 1: ./scripts/cleanup_project.sh --dry-run      → Review output
Step 2: User approval                                 → Explicit "yes"
Step 3: ./scripts/cleanup_project.sh --execute       → Perform moves
Step 4: python3.13 -m py_compile backend/main.py     → Syntax OK
Step 5: make test-demo-smoke-gate                     → Smoke tests pass
Step 6: pytest tests/unit/ -v --tb=short -q           → No regressions
Step 7: git add <specific files>                      → Atomic commit
```

### Phase 5: Comprehensive Review (4 Team Agents)

```
Architect:   py_compile all modified files, import chain validation
RAG Expert:  Hybrid search → reranker → vectorstore chain intact
QA:          pytest --collect-only, test count unchanged, coverage >= 70%
LLM Expert:  LLM client factory imports resolve, dispatch_service routing intact
```

## File Classification Rules

### DO NOT TOUCH (Core Business Logic)

```
backend/main.py                              # FastAPI entry, thread-safe singletons
backend/config.py                            # Pydantic BaseSettings
backend/services/rag_engine.py               # RAG orchestration
backend/services/retrieval/                  # Hybrid search, reranker, vectorstore
backend/services/cost_estimation_service.py  # Ridge regression model
backend/services/llm_integration/            # LLM client factory, dispatch
backend/services/memory/                     # 3-layer memory system
backend/services/prompt_manager.py           # Versioned prompts, A/B testing
backend/services/workflows/                  # 11-node pipeline, orchestrator
backend/services/intent_classification/      # Intent workflow, State Graph
backend/services/data_analysis/              # Data analysis agent
backend/services/code_executor/              # Code executor package (NOT code_executor.py)
backend/api/                                 # All route files
backend/security/                            # Auth, sanitizer, rate limiting
backend/middleware/                           # Middleware chain
backend/observability/                       # Metrics
backend/migrations/                          # SQL migrations
frontend/src/                                # All frontend source
docker-compose*.yml                          # All compose files
Dockerfile                                   # Container definition
Makefile                                     # Build targets
requirements.txt / backend/requirements.txt  # Dependencies
CLAUDE.md (root)                             # Project context (root only)
pytest.ini                                   # Test configuration
.env.example                                 # Environment template
```

### Category 1: Root Status Reports → `.deprecated/archived-root-files/`
```
Pattern: *_REPORT*.md, *_STATUS*.md, *_FIXES*.md, *_COMPLETE*.md,
         *_AUDIT*.md, *_OPTIMIZATION*.md, SMOKE_TEST_*.md
Count:   ~16 files, ~166 KB
Safety:  Documentation only, no code references
Example: SMOKE_TEST_REPORT.md, SMOKE_TEST_REPORT_FINAL.md
```

### Category 2: Orphaned Virtual Environments → Hard Delete (with confirmation)
```
Pattern: venv/, .venv_uv/, venv_docs/, venv_python313/,
         backend/venv_llamacpp/, test_env/
Size:    ~4.5 GB total
Safety:  Regenerable from requirements.txt
Note:    Keep only the primary venv used by `make capstone-env-setup`
         Verify each is NOT the active venv before deletion
Action:  rm -rf (after confirming not active)
```

### Category 3: Duplicate Backend Modules → Consolidate or Archive
```
Target A: backend/services/code_executor.py (legacy facade, 200+ lines)
  → Archive to .deprecated/services/ IF code_executor/ package handles all callers
  → Verify: grep -r "from backend.services.code_executor import" (not code_executor/)
  → Verify: grep -r "from backend.services import code_executor" (not code_executor/)

Target B: backend/services/database/init_database.py vs backend/database/__init__.py
  → Identify which is active, archive the duplicate

Target C: Scattered CLAUDE.md files (24 total)
  → Keep: root CLAUDE.md, backend/CLAUDE.md (if MCP context references it)
  → Archive rest to .deprecated/claude-md-backup/
  → Verify: no tool or script reads them programmatically
```

### Category 4: Frontend Duplicate Pages → Archive
```
Pattern: *-new.tsx, *-integrated.tsx variants in frontend/src/
Count:   ~6 files
Safety:  Verify which variant is used in routing (app/ directory structure)
Action:  Archive unused variants to .deprecated/frontend/
```

### Category 5: EN: Placeholder Text → In-Place Fix
```
Pattern: "EN:" prefix in comments, docstrings, logging messages
Count:   50+ instances across 8 core backend files
Files:   code_executor.py, prompt_manager_middleware.py, and others
Action:  Replace with meaningful English text (NOT archive — in-place edit)
Note:    This was partially fixed in commit 07dcccc but ~50 remain
Verification: grep -rn "EN:" backend/ --include="*.py" | grep -v venv
```

### Category 6: _archived/ Directory → Merge into .deprecated/
```
Current: _archived/ contains research/, logs/, reports/ (~30 files)
Target:  Move contents to .deprecated/archived-research/
Action:  Consolidate, then remove empty _archived/
Safety:  Verify no imports or script references
```

### Category 7: Oversized __init__.py → Refactor
```
Target A: backend/services/code_executor/__init__.py (137 lines)
  → Extract implementation to dedicated module
  → __init__.py should only re-export public API

Target B: backend/services/document_processing/__init__.py (51 lines)
  → Same treatment: extract, keep __init__.py as thin re-export layer
```

### Category 8: Python Cache → Hard Delete
```
Pattern: **/__pycache__/ directories
Action:  find . -type d -name __pycache__ -not -path "*/venv/*" -exec rm -rf {} +
Safety:  Regenerable on next Python execution
```

### Category 9: Root-Level One-Off Scripts → Archive
```
Pattern: *.sh at project root (not in scripts/)
Safety:  Verify not referenced by Makefile or CI
Action:  Archive to .deprecated/archived-root-files/
```

### Category 10: Stale Logs and Manifests → Archive
```
Pattern: *.log, cleanup_manifest.log at root
Safety:  Operational artifacts, no code references
Action:  Archive to .deprecated/archived-root-files/
```

## EN: Placeholder Replacement Guide

The codebase contains "EN:" prefixed strings that were bilingual placeholders. These need meaningful English replacements, not removal.

**Strategy**:
1. Run: `grep -rn "EN:" backend/ --include="*.py" | grep -v venv | grep -v __pycache__`
2. For each match, determine context (comment, docstring, log message, error string)
3. Replace with professional English text appropriate to the context
4. Do NOT change variable names, function signatures, or logic

**Examples**:
```python
# Before:
logger.info("EN: Starting document processing")
# After:
logger.info("Starting document processing")

# Before:
"""EN: This module handles cost estimation."""
# After:
"""Construction project cost estimation using Ridge regression."""
```

## Module Boundary Clarification

### code_executor (Priority: High)

**Current state**: Both `backend/services/code_executor.py` (legacy facade) and `backend/services/code_executor/` (package with providers) exist. The package has `__init__.py` (137 lines) that duplicates facade logic.

**Target state**:
```
backend/services/code_executor/
├── __init__.py          # Thin re-exports only (<20 lines)
├── manager.py           # Orchestration (moved from __init__.py)
├── docker_executor.py   # Docker implementation
├── validator.py         # Code validation
└── providers/
    ├── base.py          # Provider interface
    ├── docker_provider.py
    └── ppio_provider.py
```
- Archive `code_executor.py` (legacy facade) to `.deprecated/services/`
- Update all callers to import from package

### retrieval (Status: Clean)

```
backend/services/retrieval/
├── __init__.py          # Minimal
├── hybrid_search.py     # BM25 + vector + RRF
├── reranker.py          # bge-reranker-base
└── (vectorstore in core/)
```
No action needed — boundaries are clear.

### safety vs security (Clarification needed)

```
backend/services/safety/          # Groundedness checking (RAG quality)
backend/security/                 # Auth, sanitizer, rate limiting (HTTP security)
backend/services/security/        # Egress guard, redaction (data security)
```
**Decision**: Document the distinction, do not merge. Safety = AI output quality. Security = application security. Services/security = data protection.

## Archive Directory Structure

```
.deprecated/                           # Gitignored archive root
├── archived-root-files/               # Status reports, one-off scripts, logs
├── archived-research/                 # Merged from _archived/
├── services/                          # Deprecated service modules
│   └── code_executor.py               # Legacy facade
├── frontend/                          # Unused page variants
├── claude-md-backup/                  # Non-root CLAUDE.md files
└── README.md                          # Archive inventory
```

## Safety Verification Checklist

After each cleanup execution, verify ALL of these:

1. **Syntax**: `python3.13 -m py_compile backend/main.py` passes
2. **Core dirs exist**: `backend/services/`, `backend/api/`, `backend/security/`, `backend/middleware/`, `frontend/src/`
3. **Core files exist**: `backend/main.py`, `backend/config.py`, `Makefile`, `docker-compose*.yml`
4. **Imports resolve**: `python3.13 -c "from backend.services.rag_engine import SimpleRAG"` succeeds
5. **Workflow pipeline**: `python3.13 -c "from backend.services.workflows.graph import run_workflow_pipeline"` succeeds
6. **LLM factory**: `python3.13 -c "from backend.services.llm_integration.llm_client import LLMClientFactory"` succeeds
7. **Cost estimation**: `python3.13 -c "from backend.services.cost_estimation_service import CostEstimationService"` succeeds
8. **Code executor**: `python3.13 -c "from backend.services.code_executor import DockerCodeExecutor"` succeeds
9. **Test collection**: `pytest --collect-only tests/unit/ -q` succeeds with expected count
10. **Smoke gate**: `make test-demo-smoke-gate` passes
11. **Unit tests**: `pytest tests/unit/ -v --tb=short -q` — no NEW failures vs baseline
12. **Coverage**: `pytest tests/unit/ --cov=backend --cov-fail-under=70` passes

## macOS APFS Warning

macOS uses case-insensitive filesystem by default:
- `_archived/` and `_Archived/` are the same directory
- Use consistent lowercase for all archive directories
- Test directory operations with `ls -la` before `mv`

## Troubleshooting

### "Import error after cleanup"
Run the Safety Verification Checklist items 4-8. The moved file should NOT have been a cleanup target. Check `cleanup_manifest.log` and restore with `scripts/rollback_cleanup.sh`.

### "Test count changed after cleanup"
Compare: `pytest --collect-only tests/ -q | tail -1` before and after. If tests disappeared, a conftest.py or test file was accidentally moved.

### "EN: replacements broke string formatting"
Some EN: strings may contain format specifiers (`{variable}`, `%s`). Always preserve the format structure when replacing.

### "Refused to run on main"
Create a feature branch: `git checkout -b chore/codebase-cleanup`

### "Venv is still active"
Check with `which python3.13` — if it points inside a venv you're about to delete, deactivate first.

## Integration with Capstone Workflow

**Priority order for the remaining month before Showcase:**
1. `/tdi` — find and fix P0/P1 bugs (demo stability is #1 priority)
2. `/codebase-cleanup` — remove confusion before evaluators review code
3. Demo script preparation — fixed inputs with known-good outputs

- **TDI**: Run `/codebase-cleanup` AFTER `/tdi` rounds to archive bug test artifacts
- **Demo prep**: Run with `--verify` before capstone demo to confirm structure
- **Disk space**: Orphaned venvs (~4.5 GB) are critical to clean on Mac Studio with 32GB RAM — that disk space may be needed for Docker images and Ollama models
- **Evaluator impression**: Clean root directory and clear module boundaries demonstrate engineering maturity
- **CI/CD**: Archive directories are gitignored — no impact on Docker builds or deploys
- **Makefile**: All `make` targets continue to work after cleanup (verified in Phase 4)

## Verification Commands

```bash
# Pre-cleanup baseline
pytest --collect-only tests/ -q | tail -1          # Record test count
pytest tests/unit/ -v --tb=short -q 2>&1 | tail -5 # Record pass/fail baseline

# Post-cleanup verification
make test-demo-smoke-gate                           # Smoke tests
pytest tests/unit/ -v --tb=short -q                 # Unit tests
python3.13 -m py_compile backend/main.py            # Syntax check

# EN: placeholder audit
grep -rn "EN:" backend/ --include="*.py" | grep -v venv | grep -v __pycache__ | wc -l

# Orphaned venv check
du -sh venv/ .venv_uv/ venv_docs/ venv_python313/ backend/venv_llamacpp/ test_env/ 2>/dev/null

# Import chain validation
python3.13 -c "
from backend.services.rag_engine import SimpleRAG
from backend.services.workflows.graph import run_workflow_pipeline
from backend.services.llm_integration.llm_client import LLMClientFactory
from backend.services.cost_estimation_service import CostEstimationService
print('All critical imports OK')
"
```
