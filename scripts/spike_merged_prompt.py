#!/usr/bin/env python3
"""
Spike Test: Merged Analysis+Visualization Prompt × 5 Datasets × CodeValidator

Goal: ≥70% pass rate on CodeValidator (strict mode).
Usage: python scripts/spike_merged_prompt.py
"""

import json
import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.code_executor.validator import CodeValidator, validate_code
from backend.services.data_analysis.data_analysis_agent import DataAnalysisAgent

# ---------------------------------------------------------------------------
# 1. Build the MERGED prompt (analysis + visualization in one LLM call)
# ---------------------------------------------------------------------------

BLOCKED_METHODS = ", ".join(f".{m}()" for m in sorted(CodeValidator.BLOCKED_METHOD_NAMES))


def build_merged_prompt(
    filename: str, rows: int, columns: int, columns_desc: str, question: str
) -> str:
    return f"""You are a data analysis assistant. Write Python code that:
1. Analyzes the dataset to answer the user's question
2. Generates an appropriate visualization chart

**Dataset Metadata** (no raw data — privacy by design):
- Filename: {filename}
- Rows: {rows}, Columns: {columns}
- Column details:
{columns_desc}

**User Question**: {question}

**Hard Requirements**:
1. Use pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns
2. Read data from "/workspace/{filename}"
3. Print analysis results clearly with print() statements
4. Print a final JSON marker line: ANALYSIS_SUMMARY_JSON={{"analysis_type": "...", "key_findings": ["..."], "chart_type": "..."}}
5. Auto-detect the best chart type based on the data and question:
   - Numeric trend over time → line chart
   - Category comparison → bar chart
   - Two numeric variables correlation → scatter plot
   - Single variable distribution → histogram
   - Proportion / composition → pie chart
6. Save exactly one chart to "/workspace/analysis_chart.png"
   with plt.savefig("/workspace/analysis_chart.png", dpi=150, bbox_inches="tight")
7. Use plt.style.use("ggplot") for consistent styling
8. Set figure size to (10, 6) minimum
9. Include proper title, axis labels, and legend where appropriate

**BLOCKED methods** (code validator will reject these — DO NOT USE):
{BLOCKED_METHODS}
Use instead: df.groupby(col)[y].mean(), df[col].value_counts(), df.pivot_table(), for-loops, list comprehensions

**BLOCKED modules**: os, subprocess, sys, pathlib, socket, requests, urllib
**BLOCKED functions**: open(), eval(), exec(), __import__(), compile(), input(), getattr(), setattr()

10. Handle missing values gracefully (dropna() or fillna() before plotting)
11. All text in English only
12. Code must complete within 30 seconds

Return ONLY executable Python code, no markdown fences, no explanations."""


# ---------------------------------------------------------------------------
# 2. Test datasets + questions
# ---------------------------------------------------------------------------

DATASETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "test_resources",
    "datasets",
    "e2e_public",
)

TEST_CASES = [
    ("tips.csv", "What is the relationship between total bill and tip amount?"),
    ("tips.csv", "Compare average tips by day of the week"),
    ("penguins.csv", "Show the distribution of body mass across species"),
    ("penguins.csv", "What is the correlation between bill length and flipper length?"),
    ("titanic.csv", "What is the survival rate by passenger class?"),
    ("titanic.csv", "Show the age distribution of passengers"),
    ("mpg.csv", "How has fuel efficiency changed over model years?"),
    ("mpg.csv", "Compare horsepower across different cylinder counts"),
    ("airline-passengers.csv", "Show the passenger trend over time"),
    ("airline-passengers.csv", "What is the monthly passenger distribution?"),
]

# ---------------------------------------------------------------------------
# 3. Run spike
# ---------------------------------------------------------------------------


def main():
    agent = DataAnalysisAgent()
    if agent.llm_client is None:
        print("ERROR: No LLM client available. Check cloud LLM config.")
        sys.exit(1)

    print(f"LLM backend: {getattr(agent.llm_client, 'backend', 'unknown')}")
    print(f"Blocked methods: {BLOCKED_METHODS}")
    print(f"Test cases: {len(TEST_CASES)}")
    print("=" * 70)

    results = []

    for i, (csv_name, question) in enumerate(TEST_CASES, 1):
        csv_path = os.path.join(DATASETS_DIR, csv_name)
        if not os.path.exists(csv_path):
            print(f"[{i}/{len(TEST_CASES)}] SKIP — {csv_name} not found")
            continue

        # Extract metadata
        metadata = agent._extract_dataset_info(csv_path)
        if metadata.get("error"):
            print(f"[{i}/{len(TEST_CASES)}] SKIP — metadata error: {metadata['error']}")
            continue

        columns_desc = "\n".join(
            f"  - {col['name']} ({col['type']})"
            for col in metadata.get("columns_info", [])
        )

        # Build merged prompt
        prompt = build_merged_prompt(
            filename=csv_name,
            rows=metadata["rows"],
            columns=metadata["columns"],
            columns_desc=columns_desc,
            question=question,
        )

        # Call LLM
        print(f"\n[{i}/{len(TEST_CASES)}] {csv_name} — {question}")
        t0 = time.time()
        try:
            llm_response = agent.llm_client.generate(
                prompt, temperature=0.1, max_tokens=1500
            )
            elapsed = time.time() - t0
        except Exception as e:
            print(f"  LLM ERROR: {e}")
            results.append({"dataset": csv_name, "question": question, "pass": False, "error": str(e)})
            continue

        # Extract code
        code = agent._extract_code_from_response(llm_response)
        if not code:
            # Try raw response as code
            code = llm_response.strip()

        # Validate with CodeValidator (strict mode)
        validation = validate_code(code, strict_mode=True)

        status = "PASS" if validation.is_valid else "FAIL"
        print(f"  {status} ({elapsed:.1f}s)")
        if not validation.is_valid:
            print(f"  Error: {validation.error}")
            # Show first few lines of generated code for debugging
            lines = code.split("\n")[:5]
            for line in lines:
                print(f"    | {line}")

        results.append({
            "dataset": csv_name,
            "question": question,
            "pass": validation.is_valid,
            "error": validation.error if not validation.is_valid else None,
            "elapsed": round(elapsed, 1),
            "code_lines": len(code.split("\n")),
        })

    # ---------------------------------------------------------------------------
    # 4. Summary
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 70)
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    rate = (passed / total * 100) if total > 0 else 0

    print(f"Results: {passed}/{total} passed ({rate:.0f}%)")
    print(f"Go/No-go threshold: 70%")

    if rate >= 70:
        print(">>> GO — Proceed with implementation")
    elif rate >= 60:
        print(">>> ITERATE — Prompt needs refinement (60-70%)")
    else:
        print(">>> NO-GO — Fall back to Approach B (<60%)")

    # Show failures
    failures = [r for r in results if not r["pass"]]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures:
            print(f"  - {f['dataset']}: {f['question']}")
            print(f"    Error: {f['error']}")

    return rate >= 70


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
