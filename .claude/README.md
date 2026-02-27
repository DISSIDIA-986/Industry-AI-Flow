# Claude Code Skills for Industry AI Flow

Auto-generated Claude Code skills tailored for Industry AI Flow project.

## 🎯 Generated Skills

### 1. Python 3.13 Expert Agent
**Location**: `.claude/agents/python313-expert.json`
**Purpose**: Specialized assistant for Python 3.13 development with deep knowledge of:
- PaddleOCR 3.0.0b0+ (Nightly build)
- LangChain 1.0 State Graph patterns
- advanced_version_manager.py compatibility checks
- Industry AI Flow project structure

**Usage**:
```bash
# Activate agent in Claude Code
/agent python313-expert

# Example queries:
"Help me create a new LangChain agent"
"Check if this code is Python 3.13 compatible"
"Review PaddleOCR integration"
```

### 2. RAG Architect Agent
**Location**: `.claude/agents/rag-architect.json`
**Purpose**: Expert in RAG system design and optimization:
- pgvector hybrid retrieval (BM25 + vector)
- Multi-tenant query optimization
- Conversation memory integration
- Performance tuning (< 500ms p95)

**Usage**:
```bash
/agent rag-architect

# Example queries:
"Optimize pgvector indexing strategy"
"Design a new retriever with reranking"
"Review hybrid search implementation"
```

### 3. Create Agent Command
**Location**: `.claude/commands/create-agent.ts`
**Purpose**: Generate LangChain 1.0 agent scaffolding with:
- State Graph architecture
- Tool executor integration
- Multi-tenant support
- Async/await patterns

**Usage**:
```bash
# Generate new agent
/create-agent document_analyzer react

# Creates: backend/agents/document_analyzer.py
```

### 4. Create RAG Module Command
**Location**: `.claude/commands/create-rag-module.ts`
**Purpose**: Scaffold RAG components:
- Retrievers (hybrid search, pgvector)
- Embedders (nomic-embed-text-v1.5)
- Chunkers (recursive text splitter)
- Rerankers (bge-reranker-base)

**Usage**:
```bash
# Generate retriever
/create-rag-module retriever custom_retriever

# Generate embedder
/create-rag-module embedder custom_embedder

# Creates: backend/services/retrieval/{module}.py
```

### 5. Pre-Run Version Check Hook
**Location**: `.claude/hooks/pre-run-version-check.ts`
**Purpose**: Auto-validate Python 3.13 environment before command execution:
- Checks Python version (must be 3.13.x)
- Runs advanced_version_manager.py
- Validates PaddleOCR and dependencies
- Blocks execution on version mismatch

**Status**: Auto-enabled for all Claude Code commands

## 📋 Installation

Skills are auto-discovered by Claude Code from `.claude/` directory. No manual installation needed.

To verify:
```bash
# List available agents
ls -la .claude/agents/

# List available commands
ls -la .claude/commands/

# Check hooks
ls -la .claude/hooks/
```

## 🔧 Project Settings

**Location**: `.claude/settings.json`
- Python 3.13 configuration
- Project structure mapping
- Code style preferences (Black, Flake8, mypy)
- Framework versions (LangChain 1.0, FastAPI, pgvector)

## 📚 Best Practices

1. **Always use Python 3.13 Expert** when working with agent/RAG code
2. **Use RAG Architect** for retrieval optimization and pgvector tuning
3. **Generate scaffolds** with `/create-agent` and `/create-rag-module`
4. **Trust the version check hook** - it prevents incompatible code execution
5. **Follow settings.json guidelines** for code style and patterns

## 🚀 Quick Start

```bash
# Activate Python 3.13 Expert
/agent python313-expert

# Generate a new LangChain agent
/create-agent sentiment_analyzer react

# Create a custom retriever
/create-rag-module retriever sentiment_retriever

# Hook will auto-validate Python version before execution
```

## 🛠️ Customization

Edit skill files in `.claude/` to customize:
- Agent system prompts (`.claude/agents/*.json`)
- Command templates (`.claude/commands/*.ts`)
- Hook behavior (`.claude/hooks/*.ts`)
- Project settings (`.claude/settings.json`)

## 📖 Related Documentation

- `advanced_version_manager.py` - Version compatibility checker
- `README.md` - Project overview and setup
- `docs/MEMORY_SYSTEM.md` - Conversation memory architecture
- `docs/SECURITY_AND_TENANT_GUIDE.md` - Multi-tenant security

---

Generated with claude-code-templates for Industry AI Flow
