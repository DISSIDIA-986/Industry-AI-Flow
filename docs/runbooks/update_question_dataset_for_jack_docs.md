# Runbook: Update Question Dataset & Quick Tips for Jack's Construction Documents

> **Created**: 2026-03-13 (updated with demo focus, OCR verification, and hand-picked Quick Tips)
> **Author**: Claude Opus 4.6 (plan only — not executed)
> **Purpose**: Iterate the RAG question bank and Quick Tips to reflect Jack's 21 newly-ingested construction documents, ensuring demo-quality questions with real practical value.
> **Constraint**: Voice-related code must NOT be touched. Only question data and its generation/display logic are in scope.

---

## Demo Focus: Recommended Documents (Top 2)

After reviewing all 21 documents' content, chunk quality, authority level, and OCR fidelity, the following **2 documents** are recommended as demo focus. The demo goal is **single-document retrieval** (relevance, accuracy, confidence), not cross-document reasoning.

### Pick 1: `ontario_reg_213_91_construction_projects.txt`
- **What it is**: Ontario Regulation 213/91 — Construction Projects (under the Occupational Health and Safety Act)
- **Why it's the best pick**:
  - **TEXT file** — zero OCR risk, perfectly clean text, 100% reliable retrieval
  - **1,387 chunks** — sweet spot: large enough for rich retrieval, small enough to avoid noise
  - **Extremely practical content**: fall protection rankings (Section 26.1), guardrail requirements (Section 26.3), excavation safety, scaffold rules, PPE requirements, crane operations — exactly what a construction site engineer needs
  - **Structured legal text** with section numbers (e.g., "O. Reg. 145/00, s. 12") — easy to verify cited sources in the answer
  - **Bilingual definitions** (English + French) show document authenticity
- **Demo impression**: "Ask our system about Ontario construction safety law, and it cites the exact regulation section."

### Pick 2: `nbc_2020_national_building_code_canada.pdf`
- **What it is**: National Building Code of Canada 2020 — the authoritative national standard
- **Why**:
  - **Most impressive scope**: 12,863 chunks, 1,530 pages — "our system searched through all 1,500+ pages of Canada's national building code"
  - **OCR quality verified**: avg 67.8% alphabetic content (good), low-quality chunks are cross-reference tables (not garbled text)
  - **Rich technical content**: fire resistance ratings, structural design requirements, building classifications, occupancy definitions
  - **National authority** — every Canadian construction professional knows this document
- **Demo impression**: "The system can find specific fire safety requirements across the entire National Building Code."

### Why not 3?

With limited demo time, 2 documents are optimal:
- One **clean text file** (guaranteed perfect retrieval) for the primary demo
- One **large OCR'd PDF** (shows the system can handle real-world scanned documents at scale)
- Adding a third would dilute focus without adding new capability showcase

### Documents NOT selected (and why)

| Document | Reason skipped |
|----------|---------------|
| `bcbc_2024_web_version_revision2.pdf` | Overlaps with NBC 2020 (both building codes); NBC is more authoritative |
| `bc_ohs_regulation_part20_construction.txt` | Clean text but only 347 chunks — too small for impressive retrieval demo |
| `quebec_safety_code_construction_s2_1_r4.txt` | Good content but French sections could confuse demo audience |
| Various energy/fire/plumbing codes | Niche topics, less relatable to general audience |

---

## OCR Quality Verification Results (automated, 2026-03-13)

Automated verification was performed by analyzing the alphabetic character ratio across all chunks per document. Results:

| Document | Type | Chunks | Avg Alpha% | Low-Quality Chunks | Assessment |
|----------|------|--------|------------|-------------------|------------|
| `ontario_reg_213_91_construction_projects.txt` | TEXT | 1,387 | 70.5% | 1 | Excellent |
| `bc_ohs_regulation_part20_construction.txt` | TEXT | 347 | 76.1% | 1 | Excellent |
| `nbc_2020_national_building_code_canada.pdf` | OCR | 12,863 | 67.8% | 380 (3.0%) | Good |
| `bcbc_2024_web_version_revision2.pdf` | OCR | 12,301 | 67.2% | 390 (3.2%) | Good |

**Key finding**: The ~3% "low-quality" chunks in OCR'd PDFs are **not garbled text** — they are cross-reference index tables (e.g., `A-4.1.8.16.(4)`, `A-4.1.8.18.(7)(e)`). Actual OCR text quality is clean and well-structured. No LLM-based verification is needed.

**GLM (Zhipu BigModel) verification was evaluated but deemed unnecessary**: The project has `ZHIPU_API_KEY` configured (`backend/config.py:48`, model: `glm-4-plus`, base URL: `https://open.bigmodel.cn/api/anthropic`). However, since OCR artifacts are structural (index tables) rather than garbled text, automated alpha-ratio analysis is sufficient and costs zero tokens.

---

## Hand-Picked Quick Tips Questions (10 Entry Questions for `defaultQuickPrompts`)

These questions are crafted from **actual document content verified in the database**. Each question:
- Has a real, practical answer that exists in the indexed chunks
- Would produce an impressive, authoritative response during demo
- Is specific enough to demonstrate retrieval precision, not vague enough to produce generic answers
- Is designed to seed a **5-turn conversation chain** (entry question + 4 follow-up rounds via suggested questions)

> **Chunk ID note**: Source references below use two ID types — **chunk_id** (within-document index, e.g., "chunks 113-114") and **primary key id** (database auto-increment, e.g., "chunks 179423-179424"). To query by chunk_id: `SELECT * FROM document_chunks WHERE doc_id = '<doc_id>' AND chunk_id = <N>`. To query by primary key: `SELECT * FROM document_chunks WHERE id = <N>`. The chunk_id references (113-114, 119-120, 123-124, 142, 188-189) belong to Ontario Reg. or NBC 2020 respectively. The primary key references (179xxx, 156xxx) are database IDs.

### For Ontario Reg. 213/91 (Text file — 5 questions):

1. **"What is the ranked hierarchy of fall protection methods required under Ontario Regulation 213/91?"**
   - Why: Section 26.1(2) lists a precise ranked order (travel restraint → fall restricting → fall arrest → safety net). The answer will show the system can retrieve and present a clear regulatory hierarchy.
   - Source: chunks 113-114, verified content includes the exact 4-method ranking.

2. **"When is a guardrail system required on a construction project under Ontario Regulation 213/91?"**
   - Why: Section 26.3(1) gives specific trigger conditions (fall of 2.4m or more, floor/bridge/roof/scaffold). The answer is concrete and verifiable.
   - Source: chunks 123-124, verified content lists the 4 work surface types.

3. **"What training requirements does Ontario Regulation 213/91 mandate for workers using fall protection systems?"**
   - Why: Section 26.2 requires "adequate oral and written instructions by a competent person" plus Ontario Regulation 297/13 working-at-heights training. Specific, actionable.
   - Source: chunks 119-120, verified.

4. **"What personal protective equipment must a worker wear on an Ontario construction project under Regulation 213/91?"**
   - Why: Section 21(1)-(3) establishes the employer-worker PPE obligation chain: worker must wear protective clothing, employer must enforce it, and adequate instruction must be given before use. Shows the system can retrieve duty-of-care provisions.
   - Source: chunks 179423-179424, verified content includes the 3-part PPE obligation.

5. **"What notification must a constructor file before beginning a construction project under Ontario Regulation 213/91?"**
   - Why: Section 6(2)-(6) details the pre-construction notification workflow: complete an approved form, file at nearest Ministry office or submit electronically, keep posted conspicuously. Practical for project managers.
   - Source: chunks 179400-179403, verified content includes the filing process and emergency exception.

### For NBC 2020 (PDF/OCR — 5 questions):

6. **"How does the National Building Code of Canada define 'fire compartment' and what fire-resistance rating is required?"**
   - Why: The definition is precise ("enclosed space... separated from all other parts of the building by enclosing construction providing a fire separation having a required fire-resistance rating"). Shows the system can retrieve exact definitions from a 1,500-page document.
   - Source: chunks 188-189, verified clean OCR.

7. **"Under the National Building Code of Canada, when can separate portions of a building be treated as separate buildings?"**
   - Why: Section 1.3.3.4 requires "a vertical fire separation that has a fire-resistance rating of not less than 1 h and extends through all storeys." Very practical for architects and structural engineers.
   - Source: chunk 142, verified clean OCR.

8. **"How does the National Building Code of Canada classify buildings by major occupancy groups?"**
   - Why: Groups A (assembly) through G (agricultural) with divisions. Chunks 156498-156509 contain detailed occupancy group definitions (Group A assembly, Group B care/treatment, Group C residential, Group D business, Group E mercantile, Group F industrial, Group G agricultural). This is foundational knowledge every building professional needs.
   - Source: chunks 156498-156509, verified clean OCR.

9. **"What does the National Building Code of Canada define as 'means of egress' and what are its components?"**
   - Why: NBC defines it as "a continuous path of travel provided for the escape of persons from any point in a building... to a separate building, an open public thoroughfare, or an exterior open space." The definition includes access to exit, exit, and exit level. Fundamental life-safety concept.
   - Source: chunks 156584-156585, verified clean OCR.

10. **"What are the five stated objectives of the National Building Code of Canada?"**
    - Why: NBC explicitly states five objectives: safety, health, accessibility, fire and structural protection of buildings, and environment. The answer is concise, authoritative, and demonstrates the system can find high-level policy statements in a massive document.
    - Source: chunk 156380, verified clean OCR.

### Recommended `defaultQuickPrompts` (all 10):

```typescript
const defaultQuickPrompts = [
  // Ontario Reg. 213/91 (text, reliable single-doc retrieval)
  'What is the ranked hierarchy of fall protection methods required under Ontario Regulation 213/91?',
  'When is a guardrail system required on a construction project under Ontario Regulation 213/91?',
  'What training requirements does Ontario Regulation 213/91 mandate for workers using fall protection systems?',
  'What personal protective equipment must a worker wear on an Ontario construction project under Regulation 213/91?',
  'What notification must a constructor file before beginning a construction project under Ontario Regulation 213/91?',
  // NBC 2020 (OCR'd PDF, impressive scale)
  'How does the National Building Code of Canada define "fire compartment" and what fire-resistance rating is required?',
  'Under the National Building Code of Canada, when can separate portions of a building be treated as separate buildings?',
  'How does the National Building Code of Canada classify buildings by major occupancy groups?',
  'What does the National Building Code of Canada define as "means of egress" and what are its components?',
  'What are the five stated objectives of the National Building Code of Canada?',
]
```

> **Note**: The UI currently shows 5 Quick Tips at a time (see Phase 4 for frontend changes needed to display 10). The 10 questions are split 5:5 between the two demo documents for balanced coverage.

---

## 5-Turn Conversation Chain Design

Each Quick Tip entry question initiates a **5-turn conversation chain**. After the system answers, it generates up to 5 follow-up question suggestions (via `_build_suggested_questions()` in `intent_workflow.py:1091-1211`). The user clicks one to continue. This repeats for 5 turns total.

### How `_build_suggested_questions()` Works

The method generates follow-ups from 4 sources (in priority order):

1. **Source-aware** — uses retrieved document names:
   - `"Which specific sections in {primary_source} provide the strongest evidence for this answer?"`
   - `"How do the requirements in {primary} compare with those in {secondary}?"` (if 2+ sources)
   - `"Are there any conflicting requirements across {src1}, {src2}, and {src3}?"` (if 3+ sources)

2. **Profile-aware** — uses document outlines and keywords from `document_profiles` table (truncated to `outline[:6]` and `keywords[:12]` by `get_ranked_profiles()`):
   - Ontario Reg. outline headings (index 2-5): `"CONSTRUCTION PROJECTS"`, `"CONTENTS"`, `"Sections"`, `"SS TO AND EGRESS FROM WORK AREAS"` — note: single-word headings like `"Sections"` and `"CONTENTS"` are **filtered out** by the 2-word minimum filter (`len(str(h).split()) >= 2`), so only `"CONSTRUCTION PROJECTS"` and `"SS TO AND EGRESS FROM WORK AREAS"` are effective candidates
   - Ontario Reg. keywords: `"hyperlink"`, `"project"`, `"system"`, `"work"`, `"worker"`, `"means"`, `"fall"`, `"subsection"`, `"regulation"`, `"workers"`, `"used"`, `"constructor"` (first 12 of 14)
   - NBC 2020 outline headings (index 2-5): `"Volume 1"`, `"CANADIAN COMMISSION ON"`, `"BUILDING AND FIRE CODES"`, `"National Building Code"` — `"Volume 1"` is filtered out (single word after digit removal); other 3 pass
   - NBC 2020 keywords: `"canada"`, `"code"`, `"national"`, `"division"`, `"means"`, `"fire"`, `"part"`, `"codes"`, `"buildings"`, `"occupancy"`, `"objectives"`, `"volume"` (first 12 of 14)
   - Keyword matching uses **substring check** (`k in query_norm`), not word-boundary match
   - Generates: `"What does {filename} specify about '{heading}'?"` and `"Summarize the {kw1} and {kw2} requirements in {filename}."`

3. **Query-contextual** — extracts 4+ char keywords from the user's query (skipping stopwords), takes the **first 4 in order of appearance** as `{topic}`:
   - `"What are the common exceptions or special cases for {topic}?"`
   - `"Can you create a compliance checklist for {topic}?"`
   - **Important**: `{topic}` is the first 4 extracted keywords joined by space — for questions starting with document names (e.g., "National Building Code of Canada"), the topic will be dominated by the document name (e.g., `"national building code canada"`), not by the semantic subject of the question

4. **Generic fallbacks**:
   - `"What details should I provide for a more precise answer?"`
   - `"What are the highest-risk items I should prioritize?"`

The method deduplicates, then shuffles beyond the first item to add variety. Returns up to 5 suggestions.

### Conversation Chain Format

Each chain below shows the **recommended path** — the suggested follow-up that would produce the most impressive demo result at each turn. The actual follow-ups are generated dynamically, so these are **illustrative predictions, not guaranteed outputs**:

- **Random elements**: `_random.choice()` for headings and `_random.shuffle()` for ordering mean exact output varies per run
- **Topic extraction**: `{topic}` in query-contextual templates uses the **first 4 keywords** in order of appearance from the query, which for questions starting with document names will be dominated by the document name rather than the semantic subject
- **Keyword pairing**: Profile-aware keyword pairs are selected via substring matching (`k in query_norm`) and random sampling — the specific pairs shown below are one possible outcome

Despite these caveats, the **types** of follow-ups (source-aware, checklist, exceptions, evidence requests) are deterministic — only the specific wording varies. The chains below represent realistic demo scenarios.

---

### Chain 1: Fall Protection Hierarchy (Ontario Reg.)

**Turn 1** — Entry question:
> "What is the ranked hierarchy of fall protection methods required under Ontario Regulation 213/91?"

Expected answer: Retrieves Section 26.1(2) — ranked order: (1) travel restraint, (2) fall restricting, (3) fall arrest, (4) safety net. Cites `ontario_reg_213_91_construction_projects.txt`.

Expected follow-ups from `_build_suggested_questions()`:
1. "Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence for this answer?"
2. **"What are the common exceptions or special cases for ranked hierarchy fall protection?"** ← recommended click (note: topic = first 4 keywords)
3. "Can you create a compliance checklist for ranked hierarchy fall protection?"
4. "Summarize the fall and regulation requirements in ontario_reg_213_91_construction_projects.txt." (keyword pair from substring match: "fall" + "regulation" both appear in query)
5. "What are the highest-risk items I should prioritize?"

**Turn 2** — Follow-up click:
> "What are the common exceptions or special cases for ranked hierarchy fall protection methods?"

Expected answer: Section 26.1(3)-(4) — exceptions for certain work types (e.g., scaffold work, safety net arrangements, temporary conditions). Retrieves from same document.

Expected follow-ups:
1. "Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence for this answer?"
2. **"Can you create a compliance checklist for fall protection exceptions?"** ← recommended click
3. "Summarize the worker and regulation requirements in ontario_reg_213_91_construction_projects.txt."
4. "What details should I provide for a more precise answer?"
5. "What are the highest-risk items I should prioritize?"

**Turn 3** — Follow-up click:
> "Can you create a compliance checklist for fall protection exceptions?"

Expected answer: A structured checklist derived from Section 26 provisions — verifying guardrails, checking fall arrest anchors, confirming training records, etc.

Expected follow-ups:
1. **"Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence for this answer?"** ← recommended click
2. "What are the common exceptions or special cases for compliance checklist fall protection?"
3. "Summarize the constructor and project requirements in ontario_reg_213_91_construction_projects.txt."
4. "What details should I provide for a more precise answer?"
5. "What are the highest-risk items I should prioritize?"

**Turn 4** — Follow-up click:
> "Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence for this answer?"

Expected answer: Direct section citations — Section 26.1, 26.2, 26.3, 26.4, etc. with exact regulation references (O. Reg. 145/00, s. 14; O. Reg. 345/15, s. 6).

Expected follow-ups:
1. "What are the common exceptions or special cases for specific sections strongest evidence?"
2. **"What are the highest-risk items I should prioritize?"** ← recommended click
3. "Summarize the fall and worker requirements in ontario_reg_213_91_construction_projects.txt."
4. "Can you create a compliance checklist for specific sections strongest evidence?"
5. "What details should I provide for a more precise answer?"

**Turn 5** — Follow-up click:
> "What are the highest-risk items I should prioritize?"

Expected answer: Prioritized risk items: unprotected edges >2.4m, missing training records, absent guardrails on scaffolds, improper fall arrest anchor points. Practical summary for site supervisors.

---

### Chain 2: Guardrail Requirements (Ontario Reg.)

**Turn 1** — Entry:
> "When is a guardrail system required on a construction project under Ontario Regulation 213/91?"

Expected answer: Section 26.3(1) — required at edges of floors, bridges, roofs (during formwork), scaffold platforms where fall of 2.4m or more. Four work surface types listed.

**Turn 2** — Recommended click:
> "What are the common exceptions or special cases for guardrail system construction?"

Expected answer: Section 26.3 exceptions — cases where guardrails are impractical (small openings, temporary removal during material hoisting, etc.).

**Turn 3** — Recommended click:
> "Can you create a compliance checklist for guardrail system requirements?"

Expected answer: Structured checklist: verify height (min 0.9m to 1.07m), mid-rail presence, toe board, load capacity, material condition.

**Turn 4** — Recommended click:
> "Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence for this answer?"

Expected answer: Direct citations — Section 26.3, 26.4, 26.5 with amendment references.

**Turn 5** — Recommended click:
> "Summarize the fall and safety requirements in ontario_reg_213_91_construction_projects.txt."

Expected answer: Broad summary of Part II fall protection regime — connects guardrails to the overall hierarchy.

---

### Chain 3: Fall Protection Training (Ontario Reg.)

**Turn 1** — Entry:
> "What training requirements does Ontario Regulation 213/91 mandate for workers using fall protection systems?"

**Turn 2** — `"What are the common exceptions or special cases for training requirements fall protection?"` → Exemptions from O. Reg. 297/13 working-at-heights training.

**Turn 3** — `"Can you create a compliance checklist for training requirements fall protection?"` → Checklist: training provider approval, record keeping, refresher intervals.

**Turn 4** — `"Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence?"` → Section 26.2, O. Reg. 297/13 cross-reference.

**Turn 5** — `"What are the highest-risk items I should prioritize?"` → Missing training records, expired certifications, untrained workers on scaffolds.

---

### Chain 4: PPE Requirements (Ontario Reg.)

**Turn 1** — Entry:
> "What personal protective equipment must a worker wear on an Ontario construction project under Regulation 213/91?"

Expected answer: Section 21(1)-(3) — worker must wear protective clothing/devices as necessary, employer must enforce compliance, adequate instruction must precede use.

**Turn 2** — `"What are the common exceptions or special cases for personal protective equipment?"` → Section 21 exemptions, dust control provisions (Section 59).

**Turn 3** — `"Can you create a compliance checklist for personal protective equipment requirements?"` → PPE checklist: hard hat, safety boots, eye protection, high-visibility vest, hearing protection in noise zones.

**Turn 4** — `"Summarize the worker and safety requirements in ontario_reg_213_91_construction_projects.txt."` → Broad worker safety obligations under Part II General Construction.

**Turn 5** — `"What are the highest-risk items I should prioritize?"` → Workers without hard hats, missing eye protection in cutting/welding zones, inadequate instruction records.

---

### Chain 5: Project Notification (Ontario Reg.)

**Turn 1** — Entry:
> "What notification must a constructor file before beginning a construction project under Ontario Regulation 213/91?"

Expected answer: Section 6(2)-(6) — complete approved notification form, file at nearest Ministry office or submit electronically, keep posted conspicuously. Emergency exception: phone/fax notice if immediate work needed to prevent injury.

**Turn 2** — `"What are the common exceptions or special cases for notification constructor construction?"` → Section 6(5) emergency exception, Section 7 suspended work platform notification (48 hours advance).

**Turn 3** — `"Can you create a compliance checklist for notification constructor filing?"` → Pre-project checklist: form completion, Ministry office identification, posting requirement, emergency protocol.

**Turn 4** — `"Which specific sections in ontario_reg_213_91_construction_projects.txt provide the strongest evidence?"` → Section 6, Section 7, amendments O. Reg. 145/00 s. 4, O. Reg. 242/16 s. 4.

**Turn 5** — `"What details should I provide for a more precise answer?"` → Project type, size, location, timeline — for more specific notification requirements.

---

### Chain 6: Fire Compartment Definition (NBC 2020)

**Turn 1** — Entry:
> "How does the National Building Code of Canada define 'fire compartment' and what fire-resistance rating is required?"

Expected answer: Definition from Section 1.4.1.2 — "enclosed space in a building that is separated from all other parts of the building by enclosing construction providing a fire separation having a required fire-resistance rating." Retrieves from `nbc_2020_national_building_code_canada.pdf`.

**Turn 2** — `"What are the common exceptions or special cases for fire compartment fire-resistance rating?"` → Sprinklered buildings may have reduced ratings; interconnected floor spaces; mezzanines.

**Turn 3** — `"Which specific sections in nbc_2020_national_building_code_canada.pdf provide the strongest evidence?"` → Section 1.4.1.2 definitions, Part 3 fire separation tables.

**Turn 4** — `"Summarize the fire and building requirements in nbc_2020_national_building_code_canada.pdf."` → Overview of NBC fire protection framework: fire separations, fire-resistance ratings, combustible vs noncombustible construction.

**Turn 5** — `"Can you create a compliance checklist for fire compartment fire-resistance rating?"` → Fire compartment inspection checklist: continuity of fire separation, penetration sealing, door rating verification.

---

### Chain 7: Separate Building Provisions (NBC 2020)

**Turn 1** — Entry:
> "Under the National Building Code of Canada, when can separate portions of a building be treated as separate buildings?"

Expected answer: Section 1.3.3.4 — vertical fire separation ≥1h through all storeys, each portion ≤4 storeys, assembly/residential/business occupancies only, unobstructed firefighter path.

**Turn 2** — `"What are the common exceptions or special cases for separate portions building?"` → Agricultural buildings (Section 1.3.3.2), high-hazard industrial buildings, post-disaster buildings.

**Turn 3** — `"Can you create a compliance checklist for separate portions building treated separate?"` → Checklist: fire separation rating verification, storey count per portion, occupancy type confirmation, firefighter access path.

**Turn 4** — `"Summarize the fire and code requirements in nbc_2020_national_building_code_canada.pdf."` → NBC fire and structural protection framework overview.

**Turn 5** — `"What are the highest-risk items I should prioritize?"` → Insufficient fire separation rating, mixed occupancy conflicts, blocked firefighter access routes.

---

### Chain 8: Occupancy Classification (NBC 2020)

**Turn 1** — Entry:
> "How does the National Building Code of Canada classify buildings by major occupancy groups?"

Expected answer: Groups A (assembly), B (care/treatment/detention), C (residential), D (business/personal services), E (mercantile), F (industrial — Div 1 high-hazard, Div 2 medium, Div 3 low), G (agricultural — Div 1-4). From chunks 156498-156509.

**Turn 2** — `"What are the common exceptions or special cases for classify buildings major occupancy groups?"` → Multiple occupancy buildings classified according to all major occupancies; agricultural occupancy density thresholds (1 person per 40m²).

**Turn 3** — `"Which specific sections in nbc_2020_national_building_code_canada.pdf provide the strongest evidence?"` → Section 1.3.3.2 (agricultural), Table 3.1.2.1 (occupancy classification table), Part 9 threshold (600m², 3 storeys).

**Turn 4** — `"Summarize the occupancy and division requirements in nbc_2020_national_building_code_canada.pdf."` → Detailed breakdown of occupancy-to-building-code mapping.

**Turn 5** — `"Can you create a compliance checklist for building occupancy classification?"` → Classification checklist: identify all occupancies, determine divisions, check area/height thresholds, verify Part 3 vs Part 9 applicability.

---

### Chain 9: Means of Egress (NBC 2020)

**Turn 1** — Entry:
> "What does the National Building Code of Canada define as 'means of egress' and what are its components?"

Expected answer: "A continuous path of travel provided for the escape of persons from any point in a building or contained open space to a separate building, an open public thoroughfare, or an exterior open space." Components: access to exit + exit (+ exit level). From chunks 156584-156585.

**Turn 2** — `"What are the common exceptions or special cases for means egress components?"` → Protected floor spaces for interconnected floor spaces; exit alternatives for small buildings.

**Turn 3** — `"Can you create a compliance checklist for means egress requirements?"` → Egress checklist: travel distance limits, exit width calculations, illumination requirements, signage.

**Turn 4** — `"Which specific sections in nbc_2020_national_building_code_canada.pdf provide the strongest evidence?"` → Section 1.4.1.2 definitions, Subsection 3.4 (exits), Section 3.3 (safety within floor areas).

**Turn 5** — `"What are the highest-risk items I should prioritize?"` → Dead-end corridors exceeding limits, insufficient exit width, missing emergency lighting.

---

### Chain 10: NBC Objectives (NBC 2020)

**Turn 1** — Entry:
> "What are the five stated objectives of the National Building Code of Canada?"

Expected answer: (1) Safety, (2) Health, (3) Accessibility, (4) Fire and structural protection of buildings, (5) Environment. From chunk 156380.

**Turn 2** — `"What are the common exceptions or special cases for five stated objectives national building?"` → Existing buildings — NBC doesn't enforce retrospective application unless required by local regulations.

**Turn 3** — `"Which specific sections in nbc_2020_national_building_code_canada.pdf provide the strongest evidence?"` → Preface/Introduction section, Division A Part 2 (objectives statements).

**Turn 4** — `"Summarize the code and standards requirements in nbc_2020_national_building_code_canada.pdf."` → Overview: acceptable solutions (Division B) vs alternative solutions, mandatory vs advisory provisions.

**Turn 5** — `"Can you create a compliance checklist for national building code objectives?"` → High-level compliance framework mapped to each of the 5 objectives.

---

### Conversation Chain Assessment: `_build_suggested_questions()` Adequacy

**Verdict: The current implementation is adequate for demo purposes. No code changes needed.**

Strengths:
- Source-aware questions reference the correct document by name → good for demo credibility
- Query-contextual "compliance checklist" and "exceptions" templates are highly relevant to regulatory documents
- Generic fallbacks ("highest-risk items") produce sensible construction-domain answers
- 5-suggestion limit provides enough variety without overwhelming the user

Minor observations (NOT blockers, NOT worth fixing for demo):
- Document filenames in suggestions are verbose (e.g., `ontario_reg_213_91_construction_projects.txt`) — but this is actually a positive for demo: it shows the system knows which document it retrieved from
- Profile outline headings like `"SS TO AND EGRESS FROM WORK AREAS"` are truncated OCR artifacts — but these only appear occasionally due to random selection, and the suggestions are still understandable
- The keywords list for Ontario Reg includes `"hyperlink"` (an artifact from the .doc→.txt conversion) — this could surface in keyword-based suggestions. Low probability due to random sampling, and even if it appears, it's one of 5 options the user can ignore

**Recommendation**: Leave `_build_suggested_questions()` unchanged. The 10 entry questions above are designed to work well with the existing follow-up generation algorithm. If OCR artifact keywords become a visible demo issue during testing (Phase 6), the fix would be to clean the `document_profiles.keywords` column for these 2 documents via SQL, NOT to change the code.

---

## Current State Summary

### Database (verified 2026-03-13)

| Metric | Value |
|--------|-------|
| Total documents | 28 |
| Jack's new documents | 21 (from `construction_seed_20260313/`) |
| Pre-existing documents | 7 (caltrans, gsa, ufgs — from earlier ingestion) |
| Total chunks | 57,596 |
| All embeddings present | Yes (57,596 / 57,596) |

**Top documents by chunk count:**

| Rank | Filename | Chunks | Source |
|------|----------|--------|--------|
| 1 | `nbc_2020_national_building_code_canada.pdf` | 12,863 | Jack |
| 2 | `bcbc_2024_web_version_revision2.pdf` | 12,301 | Jack |
| 3 | `canada_labour_code_part2.pdf` | 4,140 | Jack |
| 4 | `new_brunswick_ohs_general_regulation_91_191.pdf` | 3,084 | Jack |
| 5 | `217.06.pdf` | 2,848 | Jack |
| 6 | `Alberta OHSCode_March_31,_2025_(rep_s850)_only.pdf` | 2,698 | Jack |
| 7 | `nfc2020_p1.pdf` | 2,674 | Jack |
| 8 | `gsa_p100_2024_final.pdf` | 2,593 | Pre-existing |
| 9 | `canada_ohs_regulations_sor_86_304.pdf` | 2,560 | Jack |
| 10 | `NECB2025p1.pdf` | 2,212 | Jack |

### Existing Question Dataset

**File**: `docs/testing/rag_question_bank_180.csv`
- 180 questions covering **only 9 pre-existing documents**
- Zero coverage of Jack's 21 new documents
- Generated by `scripts/testing/generate_rag_question_bank_csv.py`
- Used by `scripts/testing/run_rag_agent_browser_e2e.py` (default `--csv` path)

**Question quality issues in current 180:**
- Topics extracted from OCR'd chunks sometimes contain garbled text (e.g., `"retired ifc4"`, `"tatus full"`, `"cancellations s1"`)
- Template-based questions are generic and don't reflect domain expertise
- No coverage of Canadian building codes, OHS regulations, energy/fire/plumbing codes

### Quick Tips Architecture (3-layer, priority high→low)

| Layer | Source | File | Current Behavior |
|-------|--------|------|------------------|
| 1 | Env var override | `NEXT_PUBLIC_DEMO_PINNED_QUICK_TIPS` | Not set — falls through |
| 2 | Document-aware dynamic | `frontend/src/lib/workflow-quick-tips.ts:71-174` | Loads doc list from API, matches keywords, generates tips |
| 3 | Hardcoded fallback | `frontend/src/app/(mvp)/workflow-chat/page.tsx:37-43` | 5 generic construction questions |

**Layer 2 keyword matching problem** (`workflow-quick-tips.ts:96-105`):
```typescript
// Current keywords — biased toward old US-centric documents
safetyDoc:    ['osha', 'cfr', 'safety']           // matches osha_29_cfr_1926.txt, quebec_safety_code
concreteDoc:  ['concrete', 'cast_in_place', 'ufgs_03_30_00']  // only matches old ufgs doc
standardsDoc: ['gsa', 'p100', 'standard', 'specification', 'caltrans']  // old US docs
ifcDoc:       ['ifc', 'buildingsmart', 'schema']   // matches ifc doc (still valid)
```

With Jack's docs, `top` (by chunk count) will be `nbc_2020_national_building_code_canada.pdf`, `second` will be `bcbc_2024_web_version_revision2.pdf`, `third` will be `canada_labour_code_part2.pdf`. The generic top/second/third templates will fire, but the domain-specific categories (`concreteDoc`, `standardsDoc`) will mostly miss Jack's docs.

### Suggested Follow-up Questions (backend) — Powers the 5-Turn Conversation Chain

**File**: `backend/services/intent_classification/intent_workflow.py:1091-1211`
- Method: `_build_suggested_questions()` — generates up to 5 follow-up suggestions after each RAG response
- **4 generation sources**: source-aware (document names), profile-aware (outlines + keywords from `document_profiles` table), query-contextual (exceptions/checklist templates), generic fallbacks
- Driven by query content + retrieved source items — **no hardcoded document names**
- This is already dynamic and does NOT need updating
- **Detailed analysis and 5-turn conversation chain predictions**: see "5-Turn Conversation Chain Design" section above
- **Document profiles verified**: Both demo docs have 10 outline headings + 14 keywords each in `document_profiles` table — profile-aware follow-ups will fire correctly

### RAG E2E Validation Script

**File**: `scripts/testing/run_construction_rag_e2e_validation.py`
- `QUERY_CASES` (line 37-58): 4 hardcoded queries referencing only old docs (gsa_p100, ufgs 03_30_00, osha_29_cfr_1926, ifc_4_3)
- `EXPECTED_INGESTED_DOCS` (line 61-71): Lists only the 9 pre-existing documents
- `WORKFLOW_PROBE_CASES` (line 82-98): 2 additional queries referencing old docs
- All need updating to include Jack's documents

---

## Execution Plan

### Phase 1: Regenerate Question Bank CSV

**Goal**: Replace the 180-question bank (covering 9 old docs) with a comprehensive bank covering all 28 documents.

**Prerequisite**: PostgreSQL running on port 5432, database `ai_workflow` accessible.

**Step 1.1** — Backup existing question bank:
```bash
cp docs/testing/rag_question_bank_180.csv \
   docs/testing/rag_question_bank_180_backup_20260313.csv
```

**Step 1.2** — Run the generator script:
```bash
.venv/bin/python scripts/testing/generate_rag_question_bank_csv.py \
  --output docs/testing/rag_question_bank_560.csv \
  --questions-per-doc 20 \
  --seed 20260313 \
  --min-content-chars 180
```

Expected output: **28 docs × 20 questions = 560 questions**.

**Step 1.3** — Verify the output:
```bash
# Check total line count (should be 561 = 1 header + 560 data rows)
wc -l docs/testing/rag_question_bank_560.csv

# Check document coverage
cut -d',' -f4 docs/testing/rag_question_bank_560.csv | sort -u | wc -l
# Expected: 29 (28 docs + 1 header)

# Spot-check for Jack's docs
grep -c "nbc_2020" docs/testing/rag_question_bank_560.csv
grep -c "bcbc_2024" docs/testing/rag_question_bank_560.csv
grep -c "ontario_building_code" docs/testing/rag_question_bank_560.csv
# Each should return 20
```

**Step 1.4** — Quality spot-check: Read 10-15 questions from Jack's documents and evaluate whether the auto-extracted topics make sense. Look for:
- OCR noise in topic words (garbled text, random character sequences)
- Overly generic topics like `"compliance requirement"` (the fallback value)
- Topics that are actually meaningful (section numbers, legal terms, technical terms)

If quality is acceptable, proceed to Phase 2. If not, proceed to Phase 2A first.

**Step 1.5** — Update the default CSV path reference:

In `scripts/testing/run_rag_agent_browser_e2e.py` line 24:
```python
# Change from:
DEFAULT_CSV = PROJECT_ROOT / "docs" / "testing" / "rag_question_bank_180.csv"
# To:
DEFAULT_CSV = PROJECT_ROOT / "docs" / "testing" / "rag_question_bank_560.csv"
```

Also update `--max-questions` default on line 461:
```python
# Change from:
parser.add_argument("--max-questions", type=int, default=180)
# To:
parser.add_argument("--max-questions", type=int, default=560)
```

---

### Phase 2: Improve Question Generation Quality (if Phase 1 quality is poor)

**Goal**: Make the auto-generated questions sound like real construction professional queries.

**File to modify**: `scripts/testing/generate_rag_question_bank_csv.py`

**Step 2.1** — Strengthen OCR noise filtering in `_is_term_candidate()` (around line 146):

Add these filters:
```python
def _is_term_candidate(token: str) -> bool:
    token = str(token or "").strip().lower()
    if not token or token in STOPWORDS:
        return False
    if token.isdigit():
        return False
    compact = token.replace("-", "")
    if not compact:
        return False
    if len(compact) < 4 and not any(ch.isdigit() for ch in compact):
        return False
    if compact.isalpha() and sum(1 for ch in compact if ch in "aeiou") == 0:
        return False
    # NEW: reject tokens that are mostly digits with scattered letters (OCR noise)
    digit_ratio = sum(1 for ch in compact if ch.isdigit()) / len(compact)
    if digit_ratio > 0.6 and len(compact) > 4:
        return False
    # NEW: reject tokens with too many consecutive consonants (garbled OCR)
    import re
    if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', compact):
        return False
    return True
```

**Step 2.2** — Add chunk quality filtering in `_load_chunks()` (around line 212):

After loading chunks, filter out likely headers/footers/TOC entries:
```python
def _is_quality_chunk(content: str) -> bool:
    """Reject chunks that are likely page headers, footers, or TOC entries."""
    text = content.strip()
    # Too short to generate meaningful questions
    if len(text) < 200:
        return False
    # Mostly numbers (page of table/index content)
    alpha_count = sum(1 for ch in text if ch.isalpha())
    if alpha_count < len(text) * 0.4:
        return False
    return True
```

Apply this filter when selecting chunks for question generation (in `build_question_bank`, around line 261):
```python
quality_chunks = [c for c in chunks if _is_quality_chunk(c.content)]
if len(quality_chunks) >= 2:
    chunks = quality_chunks
# else fall back to unfiltered chunks
```

**Step 2.3** — Add Canadian regulatory document templates to `TURN_TEMPLATES`:

Add a new template variant set for legal/regulatory documents (detectable by filename keywords like `act`, `regulation`, `code`, `ohs`):

```python
REGULATORY_TURN_TEMPLATES: dict[int, tuple[str, ...]] = {
    1: (
        'What does Section "{topic1}" require for construction projects?',
        'What are the mandatory obligations regarding "{topic1}" under this regulation?',
        'How does this code define compliance for "{topic1}"?',
    ),
    2: (
        'Summarize the enforcement and penalty provisions related to "{topic1}".',
        'What exemptions or exceptions exist for "{topic1}" in this regulation?',
        'List the key definitions this act provides for "{topic1}".',
    ),
    3: (
        'Cite the exact section number and wording for the "{topic1}" requirement.',
        'What specific documentation must be maintained for "{topic1}" compliance?',
        'Provide the verbatim regulatory text that governs "{topic1}".',
    ),
    4: (
        'How do "{topic1}" requirements interact with "{topic2}" provisions?',
        'If "{topic1}" and "{topic2}" conflict, which takes precedence under this act?',
        'What are the practical implications of complying with both "{topic1}" and "{topic2}"?',
    ),
    5: (
        'Create a compliance checklist for "{topic1}" that a site supervisor could use.',
        'What inspection steps verify "{topic1}" compliance on a construction site?',
        'Draft a pre-audit preparation guide based on the "{topic1}" requirements.',
    ),
}
```

Select the template set based on filename:
```python
def _is_regulatory_doc(filename: str) -> bool:
    lower = filename.lower()
    keywords = ['act', 'regulation', 'code', 'ohs', 'cfr', 'reg_']
    return any(kw in lower for kw in keywords)
```

**Step 2.4** — After modifying, re-run the generator:
```bash
.venv/bin/python scripts/testing/generate_rag_question_bank_csv.py \
  --output docs/testing/rag_question_bank_560.csv \
  --questions-per-doc 20 \
  --seed 20260313 \
  --min-content-chars 180
```

Re-do the quality spot-check from Phase 1 Step 1.4.

---

### Phase 3: Update Frontend Quick Tips Dynamic Generation

**Goal**: Make `buildQuickTipsFromDocuments()` recognize Jack's Canadian regulatory documents and generate relevant tips.

**File to modify**: `frontend/src/lib/workflow-quick-tips.ts`

**Step 3.1** — Add new document category matchers after line 105:

```typescript
const buildingCodeDoc =
  readyDocs.find((item) =>
    hasKeyword(item.name, ['nbc', 'national_building_code', 'bcbc', 'building_code'])
  ) || undefined
const ohsDoc =
  readyDocs.find((item) =>
    hasKeyword(item.name, ['ohs', 'occupational', 'labour_code', 'labour'])
  ) || undefined
const energyCodeDoc =
  readyDocs.find((item) =>
    hasKeyword(item.name, ['necb', 'energy_code', 'energy'])
  ) || undefined
const fireCodeDoc =
  readyDocs.find((item) =>
    hasKeyword(item.name, ['nfc', 'fire_code', 'fire'])
  ) || undefined
const provincialDoc =
  readyDocs.find((item) =>
    hasKeyword(item.name, ['ontario', 'quebec', 'alberta', 'brunswick'])
  ) || undefined
```

**Step 3.2** — Add question generation blocks for new categories (after the existing `ifcDoc` block, before line 158):

```typescript
if (buildingCodeDoc) {
  appendUnique(
    generated,
    `What are the fire resistance and structural safety requirements in "${buildingCodeDoc.name}"?`,
  )
}

if (ohsDoc && ohsDoc.name !== safetyDoc?.name) {
  appendUnique(
    generated,
    `What are the employer obligations for workplace hazard prevention under "${ohsDoc.name}"?`,
  )
}

if (energyCodeDoc) {
  appendUnique(
    generated,
    `What energy efficiency standards does "${energyCodeDoc.name}" mandate for commercial buildings?`,
  )
}

if (fireCodeDoc) {
  appendUnique(
    generated,
    `From "${fireCodeDoc.name}", what fire protection systems are required for high-rise construction?`,
  )
}

if (provincialDoc && safetyDoc && provincialDoc.name !== safetyDoc.name) {
  appendUnique(
    generated,
    `Compare the fall protection requirements between "${provincialDoc.name}" and "${safetyDoc.name}".`,
  )
}
```

**Step 3.3** — Increase `maxCount` default to accommodate more tips.

In the function signature (line 74):
```typescript
// Change from:
maxCount = 8,
// To:
maxCount = 10,
```

**Step 3.4** — Update the test file:

**File**: `frontend/tests/unit/workflow-quick-tips.spec.ts`

Read this file first to understand the existing test structure, then add test cases for the new document categories. Ensure existing tests still pass. The new tests should verify that:
- A document named `nbc_2020_national_building_code_canada.pdf` triggers the `buildingCodeDoc` branch
- A document named `Alberta OHSCode...` triggers the `ohsDoc` branch
- The generated tips contain the expected question text fragments

---

### Phase 4: Update Hardcoded Fallback Quick Prompts (10 Questions + UI)

**Goal**: Replace the 5 generic fallback questions with 10 hand-picked, demo-verified questions. Update UI to display all 10.

#### Step 4.1 — Update `defaultQuickPrompts`

**File to modify**: `frontend/src/app/(mvp)/workflow-chat/page.tsx` lines 37-43

**Replace with the 10 hand-picked questions from the "Hand-Picked Quick Tips Questions" section above:**
```typescript
const defaultQuickPrompts = [
  // Ontario Reg. 213/91 (text, reliable single-doc retrieval)
  'What is the ranked hierarchy of fall protection methods required under Ontario Regulation 213/91?',
  'When is a guardrail system required on a construction project under Ontario Regulation 213/91?',
  'What training requirements does Ontario Regulation 213/91 mandate for workers using fall protection systems?',
  'What personal protective equipment must a worker wear on an Ontario construction project under Regulation 213/91?',
  'What notification must a constructor file before beginning a construction project under Ontario Regulation 213/91?',
  // NBC 2020 (OCR'd PDF, impressive scale)
  'How does the National Building Code of Canada define "fire compartment" and what fire-resistance rating is required?',
  'Under the National Building Code of Canada, when can separate portions of a building be treated as separate buildings?',
  'How does the National Building Code of Canada classify buildings by major occupancy groups?',
  'What does the National Building Code of Canada define as "means of egress" and what are its components?',
  'What are the five stated objectives of the National Building Code of Canada?',
]
```

#### Step 4.2 — Update `pinnedQuickPrompts` length fallback

In the same file, line 47:
```typescript
// Change from:
pinnedQuickPrompts = parsePinnedQuickTips(
  process.env.NEXT_PUBLIC_DEMO_PINNED_QUICK_TIPS,
  defaultQuickPrompts.length,  // This already adapts to array length — no change needed
)
```
This line already uses `defaultQuickPrompts.length`, so it auto-adapts. No change needed.

#### Step 4.3 — Adjust Quick Tips sidebar layout for 10 items

The Quick Tips sidebar panel is at **lines 511-525** of `page.tsx` (NOT lines 420-448, which are the inline suggested questions inside AI message bubbles — a different UI element). The sidebar layout is:

```tsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
  <h3 className="font-medium text-gray-900 mb-3">Quick Tips</h3>
  <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
    {quickPrompts.map(...)}
  </div>
</div>
```

The current layout is a **vertical list** (`space-y-2`) inside a scrollable container — this is correct for long question strings. Do NOT change to a grid layout (the sidebar is only ~384px wide, grid columns would make text unreadable).

**Required change**: Increase `max-h-64` (256px) to `max-h-96` (384px) or `max-h-[28rem]` (448px). With 10 long questions at ~60px each, `max-h-64` only shows 3-4 items — the user must scroll to see 60-70% of the questions. On macOS the scrollbar is hidden by default, so evaluators may not notice more items exist.

```tsx
// Change from:
<div className="max-h-64 overflow-y-auto space-y-2 pr-1">
// To:
<div className="max-h-96 overflow-y-auto space-y-2 pr-1">
```

**Note**: There are **two separate UI elements** for suggested questions:
1. **Sidebar Quick Tips** (lines 511-525): vertical list in right panel, shows `quickPrompts` state
2. **Inline suggested questions** (lines 430-448): `flex flex-wrap gap-2` pill buttons inside AI message bubbles, shows per-message `suggestedQuestions`

After the first response, both locations show the same follow-up suggestions (set via `setQuickPrompts(suggestedQuestions)` at line 273). The sidebar replaces the initial 10 Quick Tips with the backend's follow-up suggestions.

#### Step 4.4 — Design consideration: 5-turn conversation chain in UI

The 5-turn chain works automatically via the existing suggested questions mechanism:
1. User clicks a Quick Tip → sends as query
2. Backend returns answer + `suggested_questions` in metadata
3. Frontend extracts them → updates `quickPrompts` state
4. User sees new set of follow-up buttons → clicks one → cycle repeats

**No code changes needed for the conversation chain mechanism itself.** The existing pipeline handles it:
- `_build_suggested_questions()` generates up to 5 follow-ups (backend) ✓
- `normalizeSuggestedQuestions()` in `frontend/src/lib/api-client.ts` (line 535) caps at **5 items** for the HTTP path ✓
- `extractSuggestedQuestions()` in `page.tsx` (line 66) caps at 8 items for the WebSocket path (WebSocket is disabled by default, so HTTP path's 5-item limit is what applies in demo) ✓
- `buildFallbackSuggestedQuestions()` provides 3 generic fallbacks if backend doesn't include suggestions ✓
- `setQuickPrompts(suggestedQuestions)` replaces Quick Tips with follow-ups after first answer ✓

**Two code paths (HTTP vs WebSocket)**:
- **HTTP path** (default, lines 240-274): reads `response.suggested_questions` from the normalized API response. Limited to 5 by `normalizeSuggestedQuestions()` in `api-client.ts`.
- **WebSocket path** (disabled by default, lines 174-189): uses `extractSuggestedQuestions(data.metadata)`. Limited to 8.
- Since WebSocket is disabled (`useState(false)` at line 101), **the demo will use the HTTP path and show 5 follow-up suggestions per turn** — consistent with the backend's `max_questions = 5`.

**What to verify during Phase 6 testing**: After clicking a Quick Tip, the follow-up suggestions should:
- Reference the correct source document by name
- Include at least one "exceptions" or "checklist" question (from query-contextual templates)
- Not contain garbled OCR text in the question wording
- Clicking a follow-up should produce a relevant answer (not loop back to the same content)

**Why these specific questions**: Each question was verified against actual database chunks. The answers exist in the knowledge base and are specific, authoritative, and demonstrable. See the "Hand-Picked Quick Tips Questions" section for the source chunk IDs and content verification.

**IMPORTANT**: These questions target **single-document retrieval** (the demo focus). They do NOT require cross-document reasoning. Questions 1-5 target Ontario Reg. 213/91 (text file, reliable). Questions 6-10 target NBC 2020 (large PDF, impressive scope). Each question is designed to seed a 5-turn conversation chain where follow-ups are generated dynamically by `_build_suggested_questions()` — see the "5-Turn Conversation Chain Design" section above for the predicted conversation paths.

---

### Phase 5: Update RAG E2E Validation Script

**Goal**: Ensure the E2E validation script tests retrieval from Jack's documents, not just the 9 old ones.

**File to modify**: `scripts/testing/run_construction_rag_e2e_validation.py`

**Step 5.1** — Update `EXPECTED_INGESTED_DOCS` (line 61-71) to include all 28 documents:

```python
EXPECTED_INGESTED_DOCS = [
    "217.06.pdf",
    "Alberta OHSCode_March_31,_2025_(rep_s850)_only.pdf",
    "bc_ohs_regulation_part20_construction.txt",
    "bcbc_2024_web_version_revision2.pdf",
    "buildingsmart_ifc_4_3_schema_specifications.txt",
    "canada_labour_code_part2.pdf",
    "canada_nrc_act.pdf",
    "canada_ohs_regulations_sor_86_304.pdf",
    "caltrans_2025_standard_plans_digest.pdf",
    "caltrans_2025_standard_specifications_digest.pdf",
    "gsa_core_building_standards_memo_2025.pdf",
    "gsa_core_building_training_2025-04-30.pdf",
    "gsa_p100_2024_final.pdf",
    "nbc_2020_national_building_code_canada.pdf",
    "necb2020_p1.pdf",
    "NECB2025p1.pdf",
    "new_brunswick_ohs_general_regulation_91_191.pdf",
    "nfc2020_p1.pdf",
    "npc2020_p1.pdf",
    "ontario_building_code_act_1992.txt",
    "ontario_reg_213_91_construction_projects.txt",
    "osha_29_cfr_1926.txt",
    "quebec_building_act_b1_1.txt",
    "quebec_safety_code_construction_s2_1_r4.txt",
    "T94-39-2021-eng.pdf",
    "T94-51-2023-eng.pdf",
    "ufgs_03_30_00_cast_in_place_concrete.pdf",
    "ufgs_toc.pdf",
]
```

**Step 5.2** — Add Jack's document queries to `QUERY_CASES` (line 37-58):

Keep existing 4 queries and add new ones:
```python
QUERY_CASES: list[QueryCase] = [
    # Existing queries (keep for backward compatibility)
    QueryCase(
        query="What does P100 say about federal facility design standards?",
        expected_source_hint="gsa_p100",
        expected_keywords=["standards", "facility", "design"],
    ),
    QueryCase(
        query="What are cast-in-place concrete requirements in UFGS?",
        expected_source_hint="03_30_00",
        expected_keywords=["concrete", "requirements", "quality"],
    ),
    QueryCase(
        query="What topics are covered in OSHA 29 CFR 1926?",
        expected_source_hint="osha_29_cfr_1926",
        expected_keywords=["safety", "construction", "1926"],
    ),
    QueryCase(
        query="What is IFC 4.3 schema specification used for?",
        expected_source_hint="ifc_4_3",
        expected_keywords=["ifc", "schema", "specification"],
    ),
    # New queries for Jack's documents
    QueryCase(
        query="What are the fire resistance requirements in the National Building Code of Canada?",
        expected_source_hint="nbc_2020",
        expected_keywords=["fire", "resistance", "building"],
    ),
    QueryCase(
        query="What fall protection requirements does Ontario Regulation 213/91 specify for construction projects?",
        expected_source_hint="ontario_reg_213",
        expected_keywords=["fall", "protection", "construction"],
    ),
    QueryCase(
        query="What are the energy efficiency requirements in the National Energy Code of Canada for Buildings 2025?",
        expected_source_hint="NECB2025",
        expected_keywords=["energy", "efficiency", "building"],
    ),
    QueryCase(
        query="What workplace safety obligations does the Alberta OHS Code impose on employers?",
        expected_source_hint="Alberta",
        expected_keywords=["safety", "employer", "workplace"],
    ),
    QueryCase(
        query="What does the BC Building Code 2024 require for structural design of buildings?",
        expected_source_hint="bcbc_2024",
        expected_keywords=["structural", "design", "building"],
    ),
    QueryCase(
        query="What fire protection systems are required under the National Fire Code of Canada?",
        expected_source_hint="nfc2020",
        expected_keywords=["fire", "protection", "system"],
    ),
]
```

**Step 5.3** — Similarly update `WORKFLOW_PROBE_CASES` (line 82-98) to add 2-3 probes for Jack's docs.

---

### Phase 6: Verification

**Step 6.0** — Run code formatters and full test suites (mandatory before any verification):
```bash
# Python formatting (from project root)
make format

# TypeScript formatting
cd frontend && npx prettier --write src/ tests/ && cd ..

# Backend unit tests
make test-unit

# Frontend tests (may need assertion updates — see Step 6.2)
cd frontend && npx jest --verbose && cd ..
```

**Step 6.1** — Run the question bank generator and verify output (Phase 1).

**Step 6.2** — Run frontend tests, with attention to existing assertions:
```bash
cd frontend && npx jest tests/unit/workflow-quick-tips.spec.ts --verbose
```

**Warning**: The existing test at `workflow-quick-tips.spec.ts` line 40 asserts `expect(result).toHaveLength(5)`. If this assertion was written when `maxCount` defaulted to 5, it may already be incorrect with the current `maxCount=8`, and will definitely need updating after Phase 3 changes `maxCount` to 10. **Read the test file and update the assertion** to match the expected output count based on the test's mock document set and the new `maxCount` value.

**Step 6.3** — Run the RAG E2E validation (requires Ollama + PostgreSQL running):
```bash
.venv/bin/python scripts/testing/run_construction_rag_e2e_validation.py
```
Verify all new query cases pass (retrieve chunks from Jack's documents).

**Step 6.4** — Manual UI check (Quick Tips display):
1. Start backend: `make run`
2. Start frontend: `make frontend-dev`
3. Open `http://localhost:3123/workflow-chat`
4. Verify Quick Tips panel shows all 10 questions (5 Ontario + 5 NBC)
5. Verify the layout is readable (no text overflow, buttons are clickable)

**Step 6.5** — Manual UI check (5-turn conversation chain):

For **at least 2 chains** (one Ontario, one NBC), execute the full 5-turn flow:
1. Click a Quick Tip entry question
2. Verify RAG retrieves from the correct document (check source citations in the answer)
3. After the answer, verify 3-5 follow-up suggestion buttons appear below the response
4. Verify follow-up suggestions are relevant (not garbled, reference correct doc)
5. Click a follow-up suggestion → verify the next answer is relevant and different from Turn 1
6. Repeat for 5 turns total — verify the conversation deepens rather than loops

**Recommended test chains** (from the "5-Turn Conversation Chain Design" section):
- **Chain 1** (Ontario): "What is the ranked hierarchy of fall protection methods..." → follow the recommended clicks through 5 turns
- **Chain 6** (NBC): "How does the National Building Code define 'fire compartment'..." → follow the recommended clicks through 5 turns

**What to watch for during conversation chain testing:**
- Follow-ups should not repeat the same question the user already asked
- Source document name in follow-ups should match the document that was actually retrieved
- After Turn 3-4, the follow-ups may become more generic (this is expected — the system runs out of specific follow-up templates)
- If `"hyperlink"` keyword appears in a follow-up suggestion (OCR artifact from Ontario Reg. keywords), note it as a cosmetic issue — fix via SQL: `UPDATE document_profiles SET keywords = keywords - '"hyperlink"' WHERE filename = 'ontario_reg_213_91_construction_projects.txt';`

**Step 6.6** — Run the full browser E2E test (optional, time-consuming):
```bash
.venv/bin/python scripts/testing/run_rag_agent_browser_e2e.py \
  --csv docs/testing/rag_question_bank_560.csv \
  --max-questions 30 \
  --output logs/rag_e2e_jack_docs_smoke.json
```

---

## Phase Dependency Graph

```
Phase 1 (Regenerate CSV)
    ↓ quality ok?
    ├─ yes → Phase 3 + Phase 4 + Phase 5 (can run in parallel)
    └─ no  → Phase 2 (Improve generator) → re-run Phase 1 → Phase 3/4/5
                                                ↓
                                          Phase 6 (Verification)
```

## Files Modified (Summary)

| File | Phase | Change Type |
|------|-------|-------------|
| `docs/testing/rag_question_bank_560.csv` | 1 | New file (generated) |
| `docs/testing/rag_question_bank_180_backup_20260313.csv` | 1 | Backup (copy) |
| `scripts/testing/run_rag_agent_browser_e2e.py` | 1 | Update default CSV path + max-questions |
| `scripts/testing/generate_rag_question_bank_csv.py` | 2 | OCR filter, chunk quality, regulatory templates |
| `frontend/src/lib/workflow-quick-tips.ts` | 3 | Add Canadian doc categories + tips |
| `frontend/tests/unit/workflow-quick-tips.spec.ts` | 3 | Add tests for new categories |
| `frontend/src/app/(mvp)/workflow-chat/page.tsx` | 4 | Update to 10 fallback quick prompts, verify layout for 10 items |
| `scripts/testing/run_construction_rag_e2e_validation.py` | 5 | Update EXPECTED_INGESTED_DOCS, QUERY_CASES |

## Important Constraints

1. **Do NOT modify** any voice/speech-related code
2. **Do NOT modify** `backend/services/intent_classification/intent_workflow.py` — the `_build_suggested_questions()` method is already dynamic and needs no changes
3. **Do NOT modify** the ingestion pipeline or vector database — all 28 documents are already ingested and verified
4. **Do NOT delete** the original `rag_question_bank_180.csv` — keep the backup
5. **Run `make format`** after any Python file changes (black + isort)
6. **Run `cd frontend && npx prettier --write`** after any TypeScript file changes
7. **Ensure all existing tests pass** before adding new ones — run `make test-unit` for backend, `cd frontend && npx jest` for frontend
