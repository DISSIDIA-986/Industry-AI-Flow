# Conversation Memory System

Industry AI Flow now ships with a three-layer memory stack designed around the guidance in `temp/memory/optimize.01.md`. It keeps conversations coherent without exploding token budgets and plugs directly into the existing LangChain/FastAPI architecture.

## Layers

1. **Short-term memory**
   - Keeps the latest `MEMORY_SHORT_TERM_WINDOW` turns (default 6 roles).
   - Lives in `SessionContext.interaction_history` and is injected into prompts as `[{"role": ..., "content": ...}, ...]`.

2. **Summary memory**
   - After every `MEMORY_SUMMARY_TRIGGER_MESSAGES` turns (default 4) the `ConversationSummarizer` compresses new exchanges into a rolling summary (`session.summary_memory`).
   - Uses the local LLM backend (configurable via `MEMORY_SUMMARY_BACKEND`) so summaries stay on-prem.

3. **Long-term memory**
   - Structured facts (profile, preferences, tasks, facts) are extracted with `StructuredMemoryExtractor` and written to `conversation_memories` (pgvector).
   - Retrieval uses hybrid similarity with configurable `MEMORY_LONG_TERM_TOP_K` / `MEMORY_LONG_TERM_MIN_RELEVANCE`.

## Table Schema (`conversation_memories`)

```sql
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT,
    memory_type TEXT NOT NULL,
    content JSONB NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Indexes on `session_id` and `memory_type` are automatically created by `LongTermMemoryStore`.

## Key Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `ENABLE_CONVERSATION_MEMORY` | `true` | Master switch for the subsystem |
| `MEMORY_SHORT_TERM_WINDOW` | `6` | Dialogue turns kept in the short-term buffer |
| `MEMORY_SUMMARY_TRIGGER_MESSAGES` | `4` | Number of new interactions before re-summarising |
| `MEMORY_SUMMARY_BACKEND` | *empty* | Optional LLM backend override for summaries |
| `MEMORY_SUMMARY_MAX_TOKENS` | `512` | Cap for each summary generation |
| `MEMORY_LONG_TERM_TOP_K` | `5` | Number of long-term memories to retrieve per query |
| `MEMORY_LONG_TERM_MIN_RELEVANCE` | `0.45` | Minimum cosine similarity for retrieved memories |

## Testing

Unit coverage for the orchestration logic lives in `tests/unit/test_memory_manager.py` (pytest + pytest-asyncio). The tests exercise summary triggering, long-term storage, and payload assembly via dependency-injected fakes—run them with:

```bash
pytest tests/unit/test_memory_manager.py
```

## Prompt Injection Order

When `ContextManager.get_enhanced_context` is called, `context["memory_layers"]` now contains:

```
{
  "short_term": [...],
  "summary": "rolling summary text",
  "long_term": [
      {"memory_type": "tasks", "content": {...}, "relevance": 0.73},
      ...
  ]
}
```

Use this block when assembling prompts so the LLM sees:

1. System prompt / safety rules
2. Summary memory
3. Retrieved long-term facts
4. Short-term dialogue window
5. Current user query
