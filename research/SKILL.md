---
name: codebase-cleanup
description: |
  Automated codebase structure cleanup with safety-first soft-delete workflow.
  Use this skill when:
  - Project root has accumulated test files, status reports, debug scripts
  - Root directory has 10+ non-configuration files cluttering the workspace
  - After major feature completion to archive phase artifacts
  - Code review reveals organizational issues or stale references
  - Need to identify and archive deprecated code, temp docs, env backups
  Triggers: "cleanup", "organize project", "archive files", "project structure", "remove stale", "clean root"
---

# Codebase Cleanup

Automated project structure cleanup with multi-agent analysis, soft-delete archiving, and comprehensive safety verification. **Zero hard deletes** — all files moved to gitignored archive directories with full rollback capability.

## Quick Start

```
/codebase-cleanup                     # Full analysis + execution
/codebase-cleanup --dry-run           # Preview only (no changes)
/codebase-cleanup --analyze-only      # Analysis report without script generation
/codebase-cleanup --execute           # Run existing cleanup script
/codebase-cleanup --rollback          # Undo last cleanup
/codebase-cleanup --verify            # Run validation dashboard only
```

## Core Principles

| Principle | Implementation |
|-----------|---------------|
| Zero Hard Deletes | All files soft-moved to `Deprecated/`, `Temp/`, `CN Docs/` |
| Core Files Untouchable | `app.py`, `services/`, `routes/`, `models/`, `middleware/`, `handlers/` never moved |
| Rollback Ready | Auto-generated `scripts/rollback_cleanup.sh` with absolute paths |
| Manifest Logging | Every move logged to `cleanup_manifest.log` |
| Human Confirmation | Each phase requires explicit approval before proceeding |
| macOS Safe | Handles APFS case-insensitive filesystem (temp/ == Temp/) |

## Execution Workflow

### Phase 1: Multi-Agent Analysis (3 parallel agents)

```
Agent 1 (Architect):  Directory structure analysis, architectural layer mapping
Agent 2 (Code Manager): Deprecated/temp file inventory, cleanup target identification
Agent 3 (Developer):  Core dependency mapping, import chains, DO-NOT-TOUCH list
```

**Output**: Categorized file list with safety classification.

### Phase 2: Cross-Validation (2 QA agents)

```
QA Agent 1: Verify zero dependencies on planned cleanup targets
            - grep all import/require/from statements
            - Check docker-compose volume mounts
            - Verify CI/CD references
            - Check template includes

QA Agent 2: Completeness audit
            - Find missed cleanup targets
            - Verify .gitignore coverage
            - Check for orphaned references
```

**Output**: BLOCKER list (items that cannot be moved) + supplementary targets.

### Phase 3: Script Generation

Generate `scripts/cleanup_project.sh` with:
- `--dry-run` mode (preview all moves, execute none)
- `--execute` mode (perform moves with manifest logging)
- `--rollback` mode (reverse all moves from manifest)
- Post-cleanup integrity verification (8 critical files, 9 critical directories)
- Category 6 macOS workaround (in-place reorganization for case collisions)

### Phase 4: Execution with Safety Gates

```
Step 1: ./scripts/cleanup_project.sh --dry-run     → Review output
Step 2: User approval                                → Explicit "yes"
Step 3: ./scripts/cleanup_project.sh --execute      → Perform moves
Step 4: Integrity verification                       → py_compile + docker-compose config
Step 5: python3 scripts/validation_dashboard.py     → Full health check
Step 6: git add + commit                             → Atomic commit
```

### Phase 5: Comprehensive Review (4 Team Agents)

```
Architect:    flake8/py_compile verification, docker-compose validation
Code Manager: Import chain integrity, no references to moved files
Developer:    Archive contents correct, no hard deletes, rollback functional
QA:           pytest regression, import chains, RLS intact, templates exist
```

## File Classification Rules

### DO NOT TOUCH (Core Business Logic)
```
app.py                          # Flask entry point
services/                       # Trading logic, broker pool, AI
routes/                         # API endpoints
models/                         # SQLAlchemy models
middleware/                     # Auth, rate limiting
handlers/                       # Request handlers
templates/                      # Jinja2 templates
static/                         # CSS/JS/images
migrations/v2_baseline/         # Active database migrations
docker-compose*.yml             # All compose files
Dockerfile                      # Container definition
requirements.txt                # Python dependencies
CLAUDE.md                       # Project documentation
.env.example                    # Environment template
pytest.ini                      # Test configuration
webhook-simulator/              # Docker-compose dependency
prompts/                        # Referenced by core code
```

### Category 1: Root Test Files → `Deprecated/root-tests/`
```
Pattern: test_*.py at project root
Example: test_l2_btc.py, test_l2_comprehensive.py
Safety:  Verified zero imports from core code
```

### Category 2: Status/Completion Reports → `Temp/reports/`
```
Pattern: *_COMPLETE.md, *_STATUS*.md, *_FIXES*.md, PHASE*_*.md
Example: DEPLOYMENT_STATUS_FINAL.md, PHASE1_FIXES_COMPLETE.md
Safety:  Documentation only, no code references
```

### Category 3: Reference Guides → `Temp/guides/`
```
Pattern: *_GUIDE*.md, *_REFERENCE*.md (at root)
Example: DATA_COLLECTION_GUIDE.md
Safety:  No imports or CI references
```

### Category 4: Artifact Directories → `Deprecated/artifacts/`
```
Pattern: Directories with host:port names, temp build artifacts
Example: localhost:5001/, VPS:31.97.58.77/
Safety:  Never imported, no docker-compose references
```

### Category 5: Test Results → `Temp/test-results/`
```
Pattern: test-results/ directory (can be 50MB+)
Safety:  Historical data, not referenced by pytest
```

### Category 6: Temp Session Work → `Temp/session-work/` (macOS special handling)
```
Pattern: temp/ directory contents
Safety:  On macOS APFS, temp/ == Temp/ (case-insensitive)
         Uses in-place reorganization instead of cross-directory move
```

### Category 7: Side Projects → `Deprecated/side-projects/`
```
Pattern: Standalone utility directories (l2-simulator/, etc.)
EXCLUDE: webhook-simulator/ (docker-compose.multi-user.yml dependency!)
Safety:  Each verified against docker-compose volume mounts
```

### Category 8: Chinese Documentation → `CN Docs/`
```
Pattern: cnDocs/ directory
Safety:  Only referenced by utility scripts, not core code
```

### Category 9: Environment Backups → `Deprecated/env-backups/`
```
Pattern: .env.*.bak, .gitignore.bak, coverage.json, .coverage
Safety:  Backup files, no code references
```

## Archive Directory Structure

```
Deprecated/                     # Gitignored
├── root-tests/                 # test_*.py from root
├── artifacts/                  # Build/debug artifact dirs
├── side-projects/              # Standalone utility projects
└── env-backups/                # Environment file backups

Temp/                           # Gitignored (== temp/ on macOS)
├── reports/                    # Status/completion reports
├── guides/                     # Reference guide documents
├── test-results/               # Archived test output
└── session-work/               # Previous temp/ contents

CN Docs/                        # Gitignored, Chinese documentation
```

## Safety Verification Checklist

After each cleanup execution, verify:

1. **Syntax**: `python3 -m py_compile app.py` passes
2. **Core dirs exist**: `services/`, `routes/`, `models/`, `middleware/`, `handlers/`, `templates/`, `static/`, `migrations/`
3. **Core files exist**: `app.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`
4. **Docker**: `docker-compose -f docker-compose.multi-user.yml config --services` lists webhook-simulator
5. **Imports**: All import chains resolve (models, services, routes)
6. **Tests**: `pytest --collect-only tests/` succeeds
7. **Dashboard**: `python3 scripts/validation_dashboard.py` — 0 FAIL

## macOS APFS Filesystem Warning

macOS uses a case-insensitive filesystem by default:
- `temp/` and `Temp/` are the SAME directory
- `mv temp/ Temp/session-work/` fails with "cannot move to subdirectory of itself"
- **Solution**: Create `session-work/` subdirectory, then move individual files into it

This is handled automatically by the cleanup script's Category 6 logic.

## Existing Tools

| Tool | Location | Purpose |
|------|----------|---------|
| Cleanup script | `scripts/cleanup_project.sh` | Main cleanup executor |
| Rollback script | `scripts/rollback_cleanup.sh` | Undo cleanup |
| Validation dashboard | `scripts/validation_dashboard.py` | One-click health check |
| Manifest log | `cleanup_manifest.log` | Audit trail of all moves |

## Integration with CI/CD

The cleanup skill does NOT modify CI/CD pipelines. All archive directories (`Deprecated/`, `Temp/`, `CN Docs/`) are gitignored, so:
- No impact on git history size
- No impact on Docker build context (already in `.dockerignore`)
- No impact on deployment artifacts

## Troubleshooting

### "File already exists in target"
The script handles this with `SKIP` logging. Re-run is idempotent.

### "Cannot move temp/ to Temp/"
macOS case-insensitive filesystem. The script uses in-place reorganization (Category 6 special handling).

### "Rollback failed"
Check `scripts/rollback_cleanup.sh` uses absolute paths. If paths are relative, regenerate the rollback script.

### "Import error after cleanup"
Run `python3 scripts/validation_dashboard.py` to identify which import chain broke. The moved file should NOT have been a cleanup target — check the manifest and restore it.

## Related Files

- Cleanup script: `scripts/cleanup_project.sh`
- Rollback script: `scripts/rollback_cleanup.sh`
- Validation dashboard: `scripts/validation_dashboard.py`
- Manifest: `cleanup_manifest.log`
- .gitignore: Archive directory exclusions
- This skill: `.claude/skills/codebase-cleanup/`
