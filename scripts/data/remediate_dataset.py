"""
Dataset remediation pipeline for construction cost estimation.

Fixes known synthetic data artifacts:
1. Duration outliers (cap at 520 weeks = 10 years)
2. Risk score floor smoothing (replace clipped 20.0 with original values)
3. Location cost adjustment (Statistics Canada BCPI multipliers)
4. Budget pressure redistribution (correlate with risk factors, NOT target)

Input:  datasets/unified_construction_projects_enhanced.csv
Output: datasets/unified_construction_projects_remediated.csv
Log:    datasets/remediation_log.json

Idempotent: running twice produces identical output.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# BCPI-based location multipliers (Statistics Canada, relative to national average)
LOCATION_MULTIPLIERS = {
    "Vancouver": 1.35,
    "Toronto": 1.30,
    "Surrey": 1.32,
    "Brampton": 1.28,
    "Markham": 1.28,
    "Mississauga": 1.28,
    "Victoria": 1.25,
    "Calgary": 1.10,
    "Edmonton": 1.08,
    "Ottawa": 1.08,
    "Montreal": 1.05,
    "Quebec City": 0.98,
    "Winnipeg": 0.95,
    "Halifax": 0.92,
    "Saskatoon": 0.90,
}

MAX_DURATION_WEEKS = 520  # 10 years


def remediate(input_path: Path, output_path: Path, log_path: Path) -> dict:
    """Run all remediation steps and return summary log."""
    df = pd.read_csv(input_path)
    original_rows = len(df)
    log = {"input": str(input_path), "output": str(output_path), "original_rows": original_rows, "steps": []}

    # Step 1: Duration outlier cap
    duration_mask = df["planned_duration_weeks"] > MAX_DURATION_WEEKS
    affected_duration = int(duration_mask.sum())
    if affected_duration > 0:
        ratio = df.loc[duration_mask, "actual_duration_weeks"] / df.loc[duration_mask, "planned_duration_weeks"]
        df.loc[duration_mask, "planned_duration_weeks"] = MAX_DURATION_WEEKS
        df.loc[duration_mask, "actual_duration_weeks"] = MAX_DURATION_WEEKS * ratio
    log["steps"].append({"name": "duration_cap", "affected_rows": affected_duration, "max_weeks": MAX_DURATION_WEEKS})

    # Step 2: Risk score smoothing — use risk_score_original where risk_score was clipped
    risk_clipped_mask = (df["risk_score"] == 20.0) & (df["risk_score_original"] < 20.0)
    affected_risk = int(risk_clipped_mask.sum())
    df.loc[risk_clipped_mask, "risk_score"] = df.loc[risk_clipped_mask, "risk_score_original"]
    log["steps"].append({"name": "risk_score_smooth", "affected_rows": affected_risk})

    # Step 3: Location cost adjustment (BCPI multipliers)
    # Synthetic data has negligible location impact (<2% variance).
    # We treat all costs as national-baseline and apply multipliers directly.
    affected_location = 0
    for loc, mult in LOCATION_MULTIPLIERS.items():
        loc_mask = df["location"] == loc
        count = int(loc_mask.sum())
        if count > 0 and mult != 1.0:
            df.loc[loc_mask, "estimated_cost_cad"] *= mult
            df.loc[loc_mask, "actual_cost_cad"] *= mult
            affected_location += count
    log["steps"].append({"name": "location_bcpi_adjust", "affected_rows": affected_location, "multipliers": LOCATION_MULTIPLIERS})

    # Step 4: Budget pressure redistribution
    # Shift budget_pressure upward for rows with high change_orders AND high complexity.
    # DO NOT modify cost_overrun_pct (target variable) — that would be label tampering.
    bp_mask = (df["num_change_orders"] > 5) & (df["complexity_score"] > 6)
    affected_bp = int(bp_mask.sum())
    if affected_bp > 0:
        shift = np.random.RandomState(42).uniform(0.1, 0.2, size=affected_bp)
        df.loc[bp_mask, "budget_pressure"] = (df.loc[bp_mask, "budget_pressure"] + shift).clip(upper=0.85)
    log["steps"].append({"name": "budget_pressure_redistribute", "affected_rows": affected_bp})

    # Step 5: Recompute actual_cost_cad from overrun % to maintain consistency
    # actual_cost = estimated_cost * (1 + overrun_pct / 100)
    df["actual_cost_cad"] = df["estimated_cost_cad"] * (1 + df["cost_overrun_pct"] / 100)

    # Step 6: Drop risk_score_original (redundant after smoothing)
    df = df.drop(columns=["risk_score_original"])
    log["steps"].append({"name": "drop_risk_score_original", "columns_dropped": ["risk_score_original"]})

    # Validate
    assert len(df) == original_rows, f"Row count changed: {original_rows} -> {len(df)}"
    assert df.isnull().sum().sum() == 0, "Null values introduced"

    # Save
    df.to_csv(output_path, index=False)
    log["output_rows"] = len(df)
    log["output_columns"] = list(df.columns)

    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    # Save location multipliers as standalone JSON for frontend transparency panel
    multipliers_path = output_path.parent / "location_multipliers.json"
    with open(multipliers_path, "w") as f:
        json.dump(LOCATION_MULTIPLIERS, f, indent=2)

    return log


def main():
    root = Path(__file__).resolve().parent.parent.parent
    input_path = root / "datasets" / "unified_construction_projects_enhanced.csv"
    output_path = root / "datasets" / "unified_construction_projects_remediated.csv"
    log_path = root / "datasets" / "remediation_log.json"

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    log = remediate(input_path, output_path, log_path)
    print(f"Remediation complete: {log['original_rows']} rows")
    for step in log["steps"]:
        print(f"  {step['name']}: {step.get('affected_rows', 'N/A')} rows affected")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
