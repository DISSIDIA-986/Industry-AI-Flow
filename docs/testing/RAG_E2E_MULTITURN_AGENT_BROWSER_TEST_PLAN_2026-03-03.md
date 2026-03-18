# RAG End-to-End Multi-Turn Test Plan (Agent Browser)

## 1. Summary

This plan validates the full RAG workflow end-to-end via real frontend interaction driven by `agent-browser`, not backend-only API calls.

Scope includes:
- At least 30 multi-turn conversations.
- 5 turns per conversation (minimum).
- Questions grounded in already vectorized documents in the current vector DB.
- Evaluation of retrieval accuracy, answer quality, context continuity, intent recognition, and runtime stability.

Current verified storage baseline:
- Vectorized documents: 9
- Total chunks: 3568
- Chunks with embedding: 3568
- Embedding coverage: 100%

## 2. Constraints and Assumptions

- The current `/api/v1/workflow/query` path is tested with English prompts.
- Existing vectorized corpus is used as source of truth for this run.
- Frontend path: `/workflow-chat`.
- Browser automation must run through `agent-browser` and UI interaction.
- Latency uses `TTFB` as first-token proxy metric.

## 3. Test Architecture

### 3.1 Layers

1. UI execution layer
- Launch frontend page and send user prompts via input + send button.
- Observe rendered AI responses, source cards, and suggested follow-up questions.

2. Runtime telemetry layer
- Capture network request timing for `/api/v1/workflow/query`.
- Capture `TTFB proxy`, full render time, and estimated TPS.

3. Backend evidence layer
- Correlate with `logs/audit.log` (`workflow.query`, `llm.dispatch`) for triage.

### 3.2 Coverage Organization

Conversation categories:
- Standard interpretation
- Evidence follow-up
- Comparison and reasoning
- Procedure/checklist conversion
- Context-memory stress
- Proactive suggestion validation

Distribution principle:
- Minimum 2 groups per source document.
- Heavier allocation to larger/high-impact sources (`gsa_p100`, `ufgs_03_30_00`).

## 4. Public Interfaces / Types (Test Contracts)

No production API contract changes are required.

Recommended test contracts:

`RagE2ECase`
- `case_id`
- `source_filename`
- `source_hint`
- `turns[5]`
- `expected_keywords`
- `expected_intents`
- `pass_rules`

`RagE2ETurnResult`
- `case_id`
- `turn_index`
- `session_id`
- `trace_id`
- `http_status`
- `ttfb_proxy_ms`
- `total_render_ms`
- `tps_est`
- `source_hit`
- `intent`
- `suggestion_present`
- `error`

`RagE2ESummary`
- `retrieval_accuracy`
- `answer_quality`
- `context_memory`
- `intent_accuracy`
- `stability`
- `latency_p50_p95`
- `failure_breakdown`

## 5. Execution Flow (Agent Browser)

1. Start backend and frontend services.
2. Open `/workflow-chat` with `agent-browser`.
3. Snapshot interactive refs and locate input/send controls dynamically.
4. For each case:
- Refresh page to ensure a new conversation session.
- Run 5 turns continuously in the same page session.
- Per turn: fill prompt -> click send -> wait for AI message -> capture response/source/suggestions.
- Persist screenshot + snapshot + network timing sample.
5. After all cases, aggregate metrics and produce JSON + Markdown reports.

Per-turn latency fields:
- `TTFB_proxy_ms = responseStart - startTime` (resource timing)
- `total_render_ms = click_send_to_ai_message_visible`
- `tps_est = estimated_tokens / max((total_render_ms - ttfb_proxy_ms)/1000, epsilon)`

## 6. Scoring and Acceptance Criteria

### 6.1 Retrieval Accuracy

- Metric: `source_hit_rate`
- Definition: expected source appears in rendered source card/citation.
- Target: `>= 0.75`

### 6.2 Answer Quality

Auto + manual mixed score (0-5):
- Auto checks: non-empty, keyword coverage, non-template output.
- Manual checks: factual correctness, grounding sufficiency, actionable quality.
- Target mean: `>= 3.8`

### 6.3 Context Continuity

- Metric: follow-up constraint retention on turns 2-5.
- Target: `>= 0.80`

### 6.4 Intent Recognition

- Metric: intent label matches expected category.
- Target: `>= 0.70`

### 6.5 Stability

- HTTP error rate: `<= 2%`
- Empty response rate: `<= 1%`
- Adjacent repeat-answer rate (similarity >= 0.88): `<= 10%`
- Fatal crash: `0`

### 6.6 Performance

- Report p50/p95 for `TTFB_proxy_ms`, `total_render_ms`, `tps_est`.
- Performance degradation is warned separately from correctness failures.

## 7. Root-Cause Analysis Framework

Failure mapping:
- Retrieval miss + stable UI -> retrieval/vector relevance issue.
- Source hit + wrong answer -> generation/prompting issue.
- API success + broken UI rendering -> frontend interaction/render issue.
- Frequent timeout/fallback -> model/provider runtime issue.

Evidence chain per failure:
- Browser screenshot
- Browser snapshot / network timing
- `audit.log` workflow and dispatch events

## 8. Manual Review Policy

- Review all failed turns.
- Randomly sample at least 20% of passed turns.
- For large score disagreement (>1.0), manual review overrides auto score.

## 9. Deliverables

Recommended outputs:
- `logs/rag_e2e_browser/report.json`
- `logs/rag_e2e_browser/summary.md`
- `logs/rag_e2e_browser/screenshots/*`
- `logs/rag_e2e_browser/snapshots/*`
- correlated `logs/audit.log` window

## 10. 30 Multi-Turn Conversation Sets (5 Turns Each)

### G01 (buildingsmart_ifc_4_3_schema_specifications.txt)
1. What is IFC 5 in this source and how does it relate to IFC 4.x?
2. From the same source, list maturity status and package formats mentioned.
3. What is stated about IFC 4.4 compared with IFC 4.3?
4. If my team is on IFC 4.3, what migration risk should be checked first?
5. Give 3 follow-up questions to validate schema-version compatibility.

### G02 (buildingsmart_ifc_4_3_schema_specifications.txt)
1. In the schema table, what does "Retired" vs "Official" imply?
2. Which entries mention ISO 16739 and what year appears for each?
3. Compare IFC4_ADD1.xsd and IFC2X3.xsd from the same source.
4. If a pipeline still references retired XSDs, what compliance risk should be flagged?
5. Provide a short schema-governance validation checklist.

### G03 (caltrans_2025_standard_plans_digest.pdf)
1. What marker-length revisions are described for Type C/D/G/H or related markers?
2. Which standard plan numbers are tied to those revisions?
3. Identify one added table-note change related to parameter "a".
4. How would this affect drawing review in an ongoing roadway package?
5. Give next-step QA checks a reviewer should run.

### G04 (caltrans_2025_standard_plans_digest.pdf)
1. What new MSE-related details were added in the digest?
2. Which terms indicate backfill-scope changes?
3. From the same source, what retaining-wall detail should be reverified?
4. Convert this into a 4-step field verification checklist.
5. What follow-up question should be asked before sign-off?

### G05 (caltrans_2025_standard_specifications_digest.pdf)
1. What changed around Section 30 and Cold Central Plant Recycling?
2. What nearby compliance conditions were added in this digest?
3. Summarize implications for mix submittal review.
4. How should a contractor adjust document workflow?
5. Suggest 3 targeted follow-up checks for spec conformance.

### G06 (caltrans_2025_standard_specifications_digest.pdf)
1. What revisions are noted for shop drawings and temporary support?
2. Which section adds supplementary requirement S1 for reinforcing bars?
3. Explain likely impact on rebar approval timing.
4. Turn this into a risk-control checklist for construction managers.
5. Propose one follow-up question to detect missing temp support detail.

### G07 (gsa_core_building_standards_memo_2025.pdf)
1. What does this memo state about ASCE 38-02 utility data guidance?
2. What is required for site work over 5,000 sf under EISA 438?
3. What design-phase deliverable should capture this requirement?
4. What compliance risk appears if this is skipped?
5. Suggest 3 follow-up questions for federal site-work compliance.

### G08 (gsa_core_building_standards_memo_2025.pdf)
1. Which referenced guides are listed for courts, NASA, or land ports of entry?
2. What does this imply about cross-agency standard alignment?
3. How to decide binding vs informative references from this source?
4. Create a short decision tree for standard applicability.
5. Suggest proactive follow-up questions for security scope gaps.

### G09 (gsa_core_building_training_2025-04-30.pdf)
1. Which ASTM test standards are listed in this excerpt?
2. Which are tied to roofing, anchors, or sealants?
3. What QA artifacts should include these tests?
4. Build a prioritized pre-construction test matrix.
5. What follow-up question should be asked on acceptance criteria?

### G10 (gsa_core_building_training_2025-04-30.pdf)
1. What supplemental requirement context is given for IIJA/IRA projects?
2. How does the source frame local/state code considerations?
3. What should be included in a code-applicability memo?
4. Convert this into a pass/fail review checklist.
5. Give 3 follow-up questions to reduce jurisdictional ambiguity.

### G11 (gsa_p100_2024_final.pdf)
1. What does the source say about background noise and NIC/SPP?
2. How does sound masking affect interpretation?
3. What design-phase data should be submitted?
4. Provide an acoustic compliance QA checklist.
5. Suggest the best follow-up question for unresolved assumptions.

### G12 (gsa_p100_2024_final.pdf)
1. What role does FSC play according to this excerpt?
2. How is ISC Risk Management positioned as baseline?
3. What should appear in program requirements from this source?
4. What impact occurs if tenant representation is incomplete?
5. Give 3 follow-up questions for security governance readiness.

### G13 (osha_29_cfr_1926.txt)
1. What asbestos-related appendices are listed under 1926.1101?
2. Which appendices are explicitly non-mandatory?
3. What practical distinction should a safety lead make?
4. Turn this into a compliance briefing checklist.
5. Suggest follow-up questions to confirm training coverage.

### G14 (osha_29_cfr_1926.txt)
1. What does this excerpt indicate about training guidance under 1926.65 appendices?
2. Which appendices look like references vs instructions?
3. What minimum documentation should a contractor retain?
4. Provide a field-audit checklist.
5. Suggest one follow-up to test emergency preparedness depth.

### G15 (ufgs_03_30_00_cast_in_place_concrete.pdf)
1. What does the source say about contractor responsibility when fine aggregate is out of spec?
2. Which control principle is emphasized for acceptance?
3. What immediate corrective-action path is implied?
4. Convert to a 5-step nonconformance workflow.
5. Give follow-up questions to verify corrective-action closure.

### G16 (ufgs_03_30_00_cast_in_place_concrete.pdf)
1. Which standards govern PVC/rubber/thermoplastic/hydrophilic waterstops?
2. Map each waterstop type to its cited standard.
3. What mandatory submittal evidence should be required?
4. Create installation-readiness checklist items.
5. Suggest follow-up questions for joint waterproofing risk.

### G17 (ufgs_toc.pdf)
1. What roofing section codes are listed in this TOC excerpt?
2. Which entries show revision/change markers?
3. How should a spec manager use TOC changes for scope review?
4. Generate a document-control checklist for section updates.
5. Suggest follow-up questions for missing coordination.

### G18 (ufgs_toc.pdf)
1. What fire-protection systems are listed in this TOC excerpt?
2. Which items show recent revision markers?
3. What should be prioritized in life-safety coordination?
4. Convert this into a commissioning-prep checklist.
5. Give a follow-up question to uncover interface conflicts.

### G19 (gsa_p100_2024_final.pdf)
1. What does this excerpt say about change management in workplace design?
2. Which activities are explicitly included?
3. What governance artifact should be produced before design freeze?
4. Create a stakeholder-engagement checklist.
5. Suggest follow-up questions to validate adoption risk.

### G20 (gsa_p100_2024_final.pdf)
1. What requirements are stated for panelboards and surge protection?
2. What constraints are given for poles/subfeeds?
3. What electrical QA checks should happen at design review?
4. Turn this into a construction inspection checklist.
5. Suggest follow-up questions for electrical protection gaps.

### G21 (gsa_p100_2024_final.pdf)
1. What does this source state about flagpole number/location exceptions?
2. How should "generally one flagpole" be interpreted on complex sites?
3. What approval rationale should be documented for exceptions?
4. Provide a short decision checklist for site planners.
5. Suggest follow-up questions to avoid inconsistent standards.

### G22 (gsa_p100_2024_final.pdf)
1. What baseline metering requirements are described?
2. How do tier expectations evolve in this excerpt?
3. What BAS/graphics integration requirement is implied?
4. Create a commissioning checklist for metering interfaces.
5. Suggest follow-up questions on meter data quality.

### G23 (caltrans_2025_standard_plans_digest.pdf)
1. The digest repeats marker-dimension revisions across sheets; summarize the pattern.
2. Which plan identifiers are explicitly tied to it?
3. What risk appears if field crews use outdated sheets?
4. Generate a version-control checklist for deployment.
5. Suggest follow-up questions for revision traceability.

### G24 (ufgs_03_30_00_cast_in_place_concrete.pdf)
1. What does the source state about switching curing procedures during curing period?
2. Which area type is explicitly called out for moist curing?
3. What inspection hold points should be introduced?
4. Provide a stepwise curing-compliance checklist.
5. Suggest follow-up questions for coating-curing conflicts.

### G25 (gsa_p100_2024_final.pdf)
1. What does this excerpt imply about filtration requirements under special exposure context?
2. How are superseding security/risk requirements referenced?
3. What early design decision should be locked first?
4. Convert this into a risk-register entry template.
5. Suggest follow-up questions to validate environmental assumptions.

### G26 (gsa_core_building_training_2025-04-30.pdf)
1. What remains mandatory around delegated design and inspections/certifications?
2. How should teams treat innovative methods alongside retained requirements?
3. What approval gates should be enforced?
4. Create a delegated-structural-scope compliance checklist.
5. Suggest follow-up questions for peer-review sufficiency.

### G27 (ufgs_03_30_00_cast_in_place_concrete.pdf)
1. Which field quality-control activities are listed?
2. How are aggregate testing and concrete testing separated?
3. What minimum sampling-plan content is implied?
4. Turn this into on-site QC checklist steps.
5. Suggest follow-up questions for sampling frequency adequacy.

### G28 (ufgs_03_30_00_cast_in_place_concrete.pdf)
1. What installation spacing/finish requirements are indicated?
2. What is stated about splash blocks at downspouts?
3. What field acceptance criteria should be explicit?
4. Build a short inspection checklist for this item.
5. Suggest follow-up questions to catch drainage defects early.

### G29 (gsa_p100_2024_final.pdf)
1. How does this excerpt define applicability for partial-building work areas?
2. What interpretation risk exists if teams ignore this clause?
3. What document should prove correct applicability scoping?
4. Create a renovation-phase scoping checklist.
5. Suggest follow-up questions to verify chapter-boundary decisions.

### G30 (gsa_p100_2024_final.pdf)
1. What protocol compatibility expectation is stated for BAS integration?
2. Which power-measurement fields are expected to be monitored?
3. What interoperability test should be mandatory before handover?
4. Convert this into commissioning test checklist items.
5. Suggest follow-up questions for protocol mismatch risk.

## 11. Final Goal

This document is intended to be execution-ready for systematic quality validation of the entire RAG chain through realistic browser behavior:
- 30+ multi-turn conversations
- Full E2E UI + backend interaction validation
- Quantitative metrics + manual review
- Reproducible defect localization across model, retrieval, prompting, and frontend layers
