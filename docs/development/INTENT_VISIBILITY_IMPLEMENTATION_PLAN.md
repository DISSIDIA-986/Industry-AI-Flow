# Intent Classification Visibility — Implementation Plan

**Date**: 2026-03-14
**Status**: PENDING REVIEW
**Scope**: L1 (Pipeline Insight) + L2 (Intent Demo Page) + L3 (Capability Registry)

---

## 1. Executive Summary

Enhance the system so that **intent classification becomes visible and demonstrable** during the Capstone Showcase:

| Layer | Deliverable | Purpose | Est. Effort |
|-------|------------|---------|-------------|
| **L3** | Capability Registry (backend) | Single source of truth for all capabilities; MCP-inspired design | 1-1.5 days |
| **L1** | Pipeline Insight panel (workflow-chat) | Real-time visualization of intent/routing/nodes in the main chat | 0.5-1 day |
| **L2** | Intent Demo page (new frontend page) | Standalone demo page for intent classification showcase | 1-1.5 days |

**Implementation order**: L3 → L1 → L2 (backend foundation first, then frontend consumers).

---

## 2. L3: Capability Registry (Backend)

### 2.1 Design Philosophy

Inspired by MCP's `tools/list` pattern: capabilities are registered as structured objects with metadata, and consumers (intent classifier, routing engine, API endpoints) derive their behavior from the registry rather than hardcoded logic.

**Current problem**: Intent definitions are scattered across 5+ files with duplicated keyword lists:
- `intent_classifier.py` lines 24-32 (IntentType enum)
- `intent_classifier.py` lines 430-437 (LLM prompt — bare names only)
- `intent_classifier.py` lines 518-632 (heuristic keyword chains)
- `simple_intent_classifier.py` lines 83+ (separate keyword rules)
- `intent_node.py` lines 22+ (yet another heuristic)
- `routing_decision.py` lines 139+, 323+ (agent mapping + config)

Adding a new capability requires touching all 6 locations. The registry consolidates this.

### 2.2 Data Model

**File**: `backend/services/intent_classification/capability_registry.py`

```python
@dataclass(frozen=True)
class Capability:
    id: str                     # "knowledge_retrieval" — matches IntentType.value
    name: str                   # "Knowledge Retrieval"
    description: str            # Rich description for LLM prompt context
    agent_type: str             # "rag_agent" — matches AgentType value
    keywords: list[str]         # Heuristic matching keywords
    patterns: list[str]         # Regex patterns for heuristic
    example_queries: list[str]  # 3-4 examples (for API + frontend, NOT in LLM prompt)
    parameters: dict            # Agent config (timeout, retry, formats)
    fallback_ids: list[str]     # Ordered fallback capability IDs
    priority: int = 0           # Keyword check order (higher = checked first)
    enabled: bool = True
```

**Design decisions**:
- `frozen=True`: Capabilities are configuration, not mutable state
- `id` matches `IntentType` enum values — no migration of downstream code needed
- `agent_type` is a string to avoid circular imports with `routing_decision.py`
- `example_queries` are for the API catalog and frontend only — NOT injected into the LLM prompt (token budget matters for Qwen3.5:4b)
- `unclear_intent` is NOT registered as a capability — it remains a built-in sentinel

### 2.3 Registry Class

```python
class CapabilityRegistry:
    def register(self, capability: Capability) -> None
    def get(self, capability_id: str) -> Capability | None
    def list_all(self, enabled_only: bool = True) -> list[Capability]

    # For IntentClassifier LLM prompt
    def build_intent_prompt_section(self) -> str

    # For heuristic classifiers
    def build_keyword_rules(self) -> dict[str, dict]

    # For routing engine
    def get_agent_mapping(self) -> dict[str, str]
    def get_fallback_mapping(self) -> dict[str, list[str]]
    def get_agent_config(self) -> dict[str, dict]

    # For API / frontend (MCP-like tools/list)
    def to_catalog(self) -> list[dict]
```

Module-level singleton: `get_capability_registry()` returns a lazily-initialized default instance.

### 2.4 Configuration Source

**YAML config file**: `backend/config/capabilities.yaml`

```yaml
capabilities:
  - id: knowledge_retrieval
    name: Knowledge Retrieval
    description: >-
      Search the construction knowledge base for regulations, standards,
      and technical specifications using hybrid RAG retrieval.
    agent_type: rag_agent
    keywords:
      - "what is"
      - "how to"
      - "explain"
      - "regulation"
      - "safety"
      - "osha"
      - "construction"
      # ... (full list from current intent_classifier.py lines 538-566)
    example_queries:
      - "What are the fall protection requirements under OSHA 1926?"
      - "Summarize the key requirements in the National Building Code."
      - "What safety equipment must workers wear on construction sites?"
    parameters:
      max_response_time: 30
      retry_count: 2
      supported_formats: ["pdf", "txt", "docx"]
    fallback_ids: ["general"]
    priority: 0

  - id: cost_estimation
    name: Cost Estimation
    description: >-
      Predict construction project cost overruns using Ridge regression ML model.
      Handles budget forecasting, pricing queries, and cost analysis.
    agent_type: cost_estimation_agent
    keywords:
      - "cost estimate"
      - "budget"
      - "overrun"
      - "construction cost"
      - "how much"
      # ... (full list from intent_classifier.py lines 520-531)
    example_queries:
      - "How much does a 10-story commercial office building cost?"
      - "Estimate cost for a residential project with 5 floors."
      - "What is the typical budget overrun for healthcare projects?"
    parameters:
      max_response_time: 30
      retry_count: 2
    fallback_ids: ["knowledge_retrieval"]
    priority: 10  # Checked BEFORE knowledge_retrieval

  # ... data_analysis, document_processing, code_execution
```

**Why YAML over pure Python**: User requested config-file based. YAML is human-readable, editable without code changes, and the file is loaded once at startup. Fallback to hardcoded defaults if YAML is missing/corrupt.

### 2.5 Integration Changes

| File | Change | Risk |
|------|--------|------|
| `intent_classifier.py` `_build_classification_request` (L430) | Replace hardcoded intent list with `registry.build_intent_prompt_section()` | Low — output format is identical, just adds descriptions |
| `intent_classifier.py` `_simulate_llm_response` (L491) | Replace hardcoded keyword chains with `registry.build_keyword_rules()` iteration | Low — same logic, centralized source |
| `simple_intent_classifier.py` `_build_keyword_rules` | Delegate to registry | Low |
| `intent_node.py` `_heuristic_intent` | Use registry keyword rules instead of local copy | Low |
| `routing_decision.py` `_map_intent_to_agent` + `agent_config` | Derive from registry at init time | Low |
| `main.py` L647 | Add `app.include_router(intent_router)` | Low — router already exists |
| `intent_classification_routes.py` | Add `GET /capabilities` endpoint | New endpoint, no existing code affected |

**Key principle**: The `IntentType` enum is preserved. The registry wraps it, not replaces it. All downstream code that references `IntentType.KNOWLEDGE_RETRIEVAL` continues to work unchanged.

### 2.6 New API Endpoint

```
GET /api/intent/capabilities
```

Response (MCP-like tools/list format):
```json
{
  "capabilities": [
    {
      "id": "knowledge_retrieval",
      "name": "Knowledge Retrieval",
      "description": "Search the construction knowledge base...",
      "example_queries": ["What are the fall protection requirements?", ...],
      "parameters": {"supported_formats": ["pdf", "txt", "docx"]},
      "enabled": true
    }
  ],
  "version": "1.0",
  "total": 5
}
```

Internal fields (`keywords`, `patterns`, `agent_type`, `fallback_ids`, `priority`) are excluded from the API response — they are implementation details.

### 2.7 Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM prompt regression (adding descriptions changes classification) | `build_intent_prompt_section()` tested against 5 representative queries; heuristic shortcut at >= 0.85 means most queries never reach LLM |
| YAML parse error at startup | Fallback to hardcoded defaults in `_register_defaults()` |
| Circular imports | Registry is a leaf module — imports nothing from consumers |
| Breaking existing tests | Registry injected via constructor; tests can pass `None` to use defaults; existing mock patterns unchanged |

---

## 3. L1: Pipeline Insight Panel (workflow-chat)

### 3.1 Approach

Replace the static "Function description" card in the workflow-chat right sidebar (lines 624-647) with a dynamic **PipelineInsight** component that visualizes the most recent query's classification and pipeline execution.

**Zero backend changes required** — all data already exists in the `WorkflowQueryResponse.metadata`:
- `metadata.intent` — classified intent type
- `metadata.confidence` — confidence score
- `metadata.completed_nodes` — list of executed pipeline nodes
- `metadata.node_latency_ms` — per-node timing
- `metadata.pipeline_status` — "completed" or "error"

### 3.2 Component Design

**File**: `frontend/src/components/PipelineInsight.tsx`

```
+----------------------------------------+
| AI Pipeline Monitor                     |
+----------------------------------------+
|                                         |
| Intent: [knowledge_retrieval]  badge    |
| Confidence: [===========---] 85%       |
| Route: RAG Agent > Direct              |
|                                         |
+----------------------------------------+
| Pipeline Nodes              Total: 1.2s |
|                                         |
| [v] intent_node              45ms      |
| [v] safety_node              12ms      |
| [v] retrieval_node          680ms      |
| [v] rerank_node             230ms      |
| [v] prompt_node              18ms      |
| [v] route_node                8ms      |
| [ ] code_exec_node         skipped     |
| [v] response_node           180ms      |
| [v] groundedness_node        25ms      |
+----------------------------------------+
| Send a query to see the pipeline       |
| in action.               (placeholder) |
+----------------------------------------+
```

**Visual elements**:
- Intent badge: color-coded by intent type (blue=knowledge, green=cost, purple=data, orange=doc, red=code)
- Confidence bar: green >= 80%, blue 60-79%, yellow 40-59%, red < 40%
- Node list: checkmark for completed, dash for skipped, with latency in ms
- Loading state: "Classifying intent..." spinner while query is in flight

### 3.3 Integration Point

In `workflow-chat/page.tsx`:
1. Track `lastPipelineData` state from the most recent AI response's `metadata`
2. Replace the static card (lines 624-647) with `<PipelineInsight data={lastPipelineData} loading={loading} />`
3. When no query sent yet: show placeholder with system capabilities list (from L3 registry if available, otherwise hardcoded)

### 3.4 Intent Color Mapping

```typescript
const INTENT_CONFIG: Record<string, { label: string; color: string }> = {
  knowledge_retrieval: { label: 'Knowledge Retrieval', color: 'blue' },
  cost_estimation:     { label: 'Cost Estimation',     color: 'green' },
  data_analysis:       { label: 'Data Analysis',       color: 'purple' },
  document_processing: { label: 'Document Processing', color: 'orange' },
  code_execution:      { label: 'Code Execution',      color: 'red' },
  unclear_intent:      { label: 'Unclear Intent',      color: 'gray' },
}
```

---

## 4. L2: Intent Demo Page (Frontend)

### 4.1 Page Location

**Route**: `/intent-demo`
**File**: `frontend/src/app/(mvp)/intent-demo/page.tsx`

Inherits `(mvp)` layout: Navbar + DashboardShell + ProtectedRoute + AppConfigProvider.

### 4.2 Navbar Update

In `Navbar.tsx`, add after "Workflow Chat":
```typescript
const navItems = [
  { name: 'Dashboard', href: '/simple-dashboard' },
  { name: 'Workflow Chat', href: '/workflow-chat' },
  { name: 'Intent Demo', href: '/intent-demo' },       // NEW
  { name: 'Documents', href: '/documents-integrated' },
  { name: 'Data Dashboard', href: '/data-dashboard' },
  { name: 'Cost Estimation', href: '/cost-estimation' },
  { name: 'API Test', href: '/api-integration-test' },
  { name: 'Component Demo', href: '/components-demo' },
]
```

8 items — fits on demo big screen. Mobile hamburger handles overflow.

### 4.3 Page Layout

```
+------------------------------------------------------------------+
| HERO: "AI Intent Classification Engine"                           |
| "See how the system understands and routes your queries"          |
| "Powered by 11-Node LangGraph StateGraph"                        |
+------------------------------------------------------------------+
|                                                                    |
| +--- LEFT PANEL (40%) ----+  +---- RIGHT PANEL (60%) ----------+ |
| |                          |  |                                  | |
| | [Category Tabs]          |  | CLASSIFICATION RESULT            | |
| | * RAG Knowledge          |  |                                  | |
| | * Cost Estimation        |  | Intent: [badge]                  | |
| | * Data Analysis          |  | Confidence: [========--] 85%     | |
| | * Document Processing    |  |                                  | |
| | * Code Execution         |  | Reasoning:                       | |
| |                          |  | "Query contains knowledge..."    | |
| | Example queries:         |  |                                  | |
| | > "What is the fire..."  |  | Routing Decision:                | |
| | > "What are the fall..." |  | Agent: RAG Agent                 | |
| | > "Explain the diff..."  |  | Path: DIRECT_ROUTING             | |
| |                          |  | Processing: 340ms                | |
| | [Custom query input]     |  |                                  | |
| | [_________________] [Go] |  | Capabilities Used:               | |
| |                          |  | - Hybrid Search (BM25+Vector)    | |
| +--PIPELINE FLOW-----------+  | - BGE Reranker                   | |
| | [Input]→[Context]→[Class |  | - Ollama Qwen3.5 Generation     | |
| | ify]→[Evaluate]→[Route]  |  +----------------------------------+ |
| | →[Dispatch]→[Response]   |  |                                  | |
| +--HISTORY-----------------+  | SYSTEM CAPABILITIES              | |
| | "What is the fire..." |85%| | (from /api/intent/capabilities)  | |
| | "Estimate cost..."    |91%| | [5 capability cards with         | |
| | "Analyze trend..."    |90%| |  descriptions + examples]        | |
| +--------------------------+  +----------------------------------+ |
+------------------------------------------------------------------+
```

### 4.4 Example Queries

Organized by intent, using construction-domain language:

| Intent | Example Queries |
|--------|----------------|
| **Knowledge Retrieval** | "What are the fall protection requirements under Ontario Regulation 213/91?" / "What safety equipment must workers wear according to OSHA 29 CFR 1926?" / "Explain the difference between Type A and Type B construction." |
| **Cost Estimation** | "How much does a 10-story commercial office building cost in Toronto?" / "Estimate the construction cost for a residential project with 5 floors and 20,000 sqft." / "What is the typical budget overrun for healthcare projects?" |
| **Data Analysis** | "Analyze the trend of construction costs over the past 5 years." / "Create a visualization comparing project budgets by location." / "Show me statistics on cost overruns for different project types." |
| **Document Processing** | "Upload and scan this PDF document for text extraction using OCR." / "Process the uploaded image and extract text from the building permit." |
| **Code Execution** | "Run a Python script to calculate the structural load capacity." / "Execute a computation to determine material requirements for a 50m bridge span." |

### 4.5 API Integration

**Primary endpoint**: `POST /api/intent/classify` (via backend proxy)

```typescript
// Add to api-client.ts
export const intentApi = {
  async classify(request: IntentClassifyRequest): Promise<IntentClassifyResponse> {
    return requestBackend<IntentClassifyResponse>('/api/intent/classify', {
      method: 'POST',
      body: request,
    })
  },
  async getCapabilities(): Promise<CapabilityCatalog> {
    return requestBackend<CapabilityCatalog>('/api/intent/capabilities', {
      method: 'GET',
    })
  },
}
```

**No frontend mock fallback** — per user decision, backend will be available during demo.

### 4.6 Pipeline Flow Visualization

Simplified horizontal flow showing the 11 intent workflow nodes:

```
[Preprocess] → [Enrich] → [Classify] → [Evaluate] → [Route] → [Dispatch] → [Response]
                                                   ↘ [Clarify] → [Process] ↗
```

After classification completes, highlight the path taken (e.g., high confidence skips clarification).

### 4.7 Capabilities Display

Fetch from `GET /api/intent/capabilities` on page load. Display each capability as a card:

```
+----------------------------------+
| Knowledge Retrieval         [ON] |
| Search the construction          |
| knowledge base for regulations   |
| and technical specifications.    |
|                                  |
| Try: "What are the fall          |
|  protection requirements?"       |
+----------------------------------+
```

---

## 5. Demo Script

**Recommended presentation flow** (30-60 seconds):

1. **Open Intent Demo page** (5s): "Our system uses an AI-powered intent classification engine to understand and route queries."
2. **Click a RAG example** (10s): "When I ask about building codes, the system recognizes this as a Knowledge Retrieval query with 85% confidence and routes it to our RAG pipeline."
3. **Click a Cost example** (10s): "A cost-related question is classified differently — Cost Estimation — and routed to our ML prediction model."
4. **Show pipeline flow** (5s): "Each query passes through an 11-node LangGraph StateGraph for classification and a 10-node execution pipeline."
5. **Switch to Workflow Chat** (remaining time): "Let me show you this in action..." — evaluators see the Pipeline Insight panel update in real time as queries are answered.

---

## 6. File Change Summary

### New Files
| File | Purpose |
|------|---------|
| `backend/services/intent_classification/capability_registry.py` | Capability dataclass + CapabilityRegistry class + singleton |
| `backend/config/capabilities.yaml` | Capability definitions (YAML config) |
| `frontend/src/components/PipelineInsight.tsx` | Pipeline visualization component |
| `frontend/src/app/(mvp)/intent-demo/page.tsx` | Intent demo page |

### Modified Files
| File | Change |
|------|--------|
| `backend/main.py` L647 | Add `app.include_router(intent_router)` + import |
| `backend/api/intent_classification_routes.py` | Add `GET /capabilities` endpoint |
| `backend/services/intent_classification/intent_classifier.py` | Use registry for prompt building + heuristic keywords |
| `backend/services/intent_classification/simple_intent_classifier.py` | Use registry for keyword rules |
| `backend/services/workflows/nodes/intent_node.py` | Use registry for heuristic intent |
| `backend/services/routing_decision.py` | Derive agent mapping from registry |
| `frontend/src/lib/api-client.ts` | Add `intentApi` namespace |
| `frontend/src/components/Navbar.tsx` | Add "Intent Demo" nav item |
| `frontend/src/app/(mvp)/workflow-chat/page.tsx` | Replace static sidebar card with PipelineInsight |

### NOT Changed
- `IntentType` enum — preserved as-is
- `IntentClassificationWorkflow` (11-node graph) — no changes
- `graph.py` (10-node pipeline) — no changes
- Database schema — no changes

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| LLM prompt change affects classification accuracy | Medium | Test with 5 representative queries; heuristic shortcut bypasses LLM for most queries |
| Intent route initialization fails (DB/LLM not ready) | Medium | Add try/except with graceful fallback; demo pre-warms Ollama |
| YAML config parse error | Low | Fallback to hardcoded defaults |
| Navbar overflow on small screens | Low | Demo is on big screen; mobile hamburger handles overflow |
| New page increases demo surface area | Low | Page is self-contained; failure doesn't affect other features |

---

## 8. Acceptance Criteria

- [ ] `GET /api/intent/capabilities` returns structured capability catalog
- [ ] `POST /api/intent/classify` correctly classifies all 5 intent types
- [ ] Pipeline Insight panel in workflow-chat shows intent + confidence + nodes for each query
- [ ] Intent Demo page loads, displays capabilities, and classifies example queries
- [ ] All existing unit tests pass (no regressions)
- [ ] Demo script can be executed in 30-60 seconds without errors
