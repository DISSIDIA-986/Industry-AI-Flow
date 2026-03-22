"""Cost estimation training and inference service."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

NUMERIC_FEATURES: List[str] = [
    "sqft",
    "floors",
    "num_units",
    "planned_duration_weeks",
    "estimated_cost_cad",
    "contractor_rating",
    "complexity_score",
    "team_experience_years",
    "num_change_orders",
    "weather_risk_factor",
    "material_volatility",
    "num_subcontractors",
    "budget_pressure",
    "risk_score",
]

# Legacy feature kept for backward compatibility with v1.0 artifacts
_LEGACY_NUMERIC_FEATURES = NUMERIC_FEATURES + ["risk_score_original"]

# Features used for similar project distance calculation
SIMILAR_DISTANCE_FEATURES: List[str] = [
    "sqft",
    "floors",
    "estimated_cost_cad",
    "planned_duration_weeks",
    "contractor_rating",
    "complexity_score",
]

# What-if adjustable features with their valid ranges
WHATIF_FEATURES: Dict[str, Tuple[float, float]] = {
    "contractor_rating": (2.0, 5.0),
    "num_change_orders": (0, 30),
    "weather_risk_factor": (0.0, 1.0),
    "material_volatility": (0.0, 1.0),
    "budget_pressure": (0.0, 1.0),
}

# Human-readable feature labels for SHAP display
FEATURE_LABELS: Dict[str, str] = {
    "sqft": "Square Footage",
    "floors": "Number of Floors",
    "num_units": "Number of Units",
    "planned_duration_weeks": "Planned Duration",
    "estimated_cost_cad": "Estimated Cost",
    "contractor_rating": "Contractor Rating",
    "complexity_score": "Complexity Score",
    "team_experience_years": "Team Experience",
    "num_change_orders": "Change Orders",
    "weather_risk_factor": "Weather Risk",
    "material_volatility": "Material Volatility",
    "num_subcontractors": "Subcontractors",
    "budget_pressure": "Budget Pressure",
    "risk_score": "Risk Score",
}

CATEGORICAL_FEATURES: List[str] = [
    "project_type",
    "location",
]

TARGET_OVERRUN = "cost_overrun_pct"
TARGET_ACTUAL_COST = "actual_cost_cad"
ESTIMATED_COST = "estimated_cost_cad"

REQUIRED_TRAINING_COLUMNS: List[str] = (
    NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET_OVERRUN, TARGET_ACTUAL_COST]
)
# Legacy datasets may still have risk_score_original; training accepts both
_LEGACY_REQUIRED_COLUMNS: List[str] = (
    _LEGACY_NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET_OVERRUN, TARGET_ACTUAL_COST]
)

_PROJECT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "residential_single_family": [
        "residential single family",
        "single family",
        "single-family",
        "detached house",
    ],
    "residential_multi_family": [
        "residential multi family",
        "multi family",
        "multi-family",
        "apartment",
    ],
    "commercial_office": [
        "commercial office",
        "office building",
        "office tower",
        "business office",
    ],
    "commercial_retail": [
        "commercial retail",
        "retail",
        "shopping",
        "shopping center",
    ],
    "industrial_warehouse": [
        "industrial warehouse",
        "warehouse",
        "distribution center",
        "logistics hub",
    ],
    "education_school": ["education school", "school", "campus", "education facility"],
    "healthcare_hospital": [
        "healthcare hospital",
        "hospital",
        "medical center",
        "healthcare facility",
    ],
    "infrastructure_bridge": [
        "infrastructure bridge",
        "bridge",
        "infrastructure project",
        "transport bridge",
    ],
    "renovation_commercial": [
        "renovation commercial",
        "commercial renovation",
        "tenant improvement",
        "retrofit",
    ],
    "mixed_use": [
        "mixed use",
        "mixed-use",
        "mixed development",
    ],
    "renewable_energy": [
        "renewable energy",
        "solar farm",
        "wind farm",
        "energy project",
    ],
    "transit_station": [
        "transit station",
        "train station",
        "subway station",
        "transit hub",
    ],
}

_LOCATION_KEYWORDS: List[str] = [
    "Toronto",
    "Calgary",
    "Ottawa",
    "Vancouver",
    "Montreal",
    "Halifax",
    "Edmonton",
    "Winnipeg",
    "Victoria",
    "Saskatoon",
    "Brampton",
    "Markham",
    "Mississauga",
    "Quebec City",
    "Surrey",
]

_NUMERIC_PATTERNS: Dict[str, List[str]] = {
    "sqft": [
        r"(?:sqft|square\s*feet|square\s*ft|area)\s*[:=]?\s*([0-9][0-9,.\s]*[0-9]|[0-9])\b",
        r"([0-9][0-9,.\s]*[0-9]|[0-9])\s*(?:sqft|square\s*feet|square\s*ft)\b",
    ],
    "floors": [
        r"(?:floors?|storeys?|stories|levels?)\s*[:=]?\s*([0-9]+)",
    ],
    "num_units": [
        r"(?:num\s*units|number\s+of\s+(?:units|apartments?|homes?))\s*[:=]?\s*([0-9]+)",
        r"([0-9]+)\s+(?:units|apartments|homes)\b",
    ],
    "planned_duration_weeks": [
        r"(?:planned\s*duration|duration)\s*[:=]?\s*([0-9][0-9,.]*[0-9]|[0-9])\s*(?:weeks?)?",
    ],
    "estimated_cost_cad": [
        r"(?:estimated\s*cost|budget(?:\s*estimate)?|project\s*cost|target\s*cost|total\s*cost)\s*[:=]?\s*\$?\s*([0-9][0-9,.]*[kmb]?)\b",
        r"\$\s*([0-9][0-9,.]*[kmb]?)\b",
    ],
    "contractor_rating": [
        r"(?:contractor\s*rating|builder\s*rating|rating)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "complexity_score": [
        r"(?:complexity|complexity\s*score)\s*[:=]?\s*([0-9]+)",
    ],
    "team_experience_years": [
        r"(?:team\s*experience|experience\s*years|years\s*experience)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "num_change_orders": [
        r"(?:change\s*orders?|variation\s*orders?)\s*[:=]?\s*([0-9]+)",
    ],
    "weather_risk_factor": [
        r"(?:weather\s*risk|climate\s*risk)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "material_volatility": [
        r"(?:material\s*volatility|material\s*risk)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "num_subcontractors": [
        r"(?:subcontractors?|subs?)\s*[:=]?\s*([0-9]+)",
    ],
    "budget_pressure": [
        r"(?:budget\s*pressure|budget\s*stress)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "risk_score": [
        r"(?:risk\s*score(?!\s*original)|overall\s*risk)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
    "risk_score_original": [
        r"(?:risk\s*score\s*original|baseline\s*risk\s*score)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)",
    ],
}


class CostEstimationError(RuntimeError):
    """Raised when training or inference preconditions are not satisfied."""


@dataclass
class _RidgeModel:
    bias: float
    weights: np.ndarray
    means: np.ndarray
    stds: np.ndarray


def _parse_human_number(value: str) -> Optional[float]:
    cleaned = value.strip().lower().replace(",", "").replace(" ", "")
    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("b"):
        multiplier = 1_000_000_000.0
        cleaned = cleaned[:-1]

    cleaned = cleaned.strip()
    if not cleaned:
        return None

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def extract_cost_features_from_query(query: str) -> Dict[str, Any]:
    """
    Extract cost-estimation features from a free-form natural-language query.

    The extractor is intentionally conservative. It only fills fields when
    explicit values are present and leaves the rest for model medians/defaults.
    """
    text = (query or "").strip()
    if not text:
        return {}

    lowered = text.lower()
    extracted: Dict[str, Any] = {}

    # Project type keyword mapping
    for canonical, keywords in _PROJECT_TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            extracted["project_type"] = canonical
            break

    # Location keyword mapping
    for location in _LOCATION_KEYWORDS:
        if location.lower() in lowered:
            extracted["location"] = location
            break

    # Generic location capture fallback: "location Toronto"
    if "location" not in extracted:
        loc_match = re.search(
            r"(?:location|city|region)\s*[:=]?\s*([A-Za-z][A-Za-z\s-]{1,30})",
            text,
            re.IGNORECASE,
        )
        if loc_match:
            extracted["location"] = loc_match.group(1).strip().title()

    # Numeric captures
    for field, patterns in _NUMERIC_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = _parse_human_number(match.group(1))
            if value is None:
                continue
            if field in {
                "floors",
                "num_units",
                "complexity_score",
                "num_change_orders",
                "num_subcontractors",
            }:
                extracted[field] = int(round(value))
            else:
                extracted[field] = float(value)
            break

    return extracted


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.maximum(np.abs(y_true), 1.0)
    return float(np.mean(np.abs(y_true - y_pred) / denom))


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y_true - y_pred))))


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum(np.square(y_true - y_pred)))
    ss_tot = float(np.sum(np.square(y_true - np.mean(y_true))))
    if ss_tot <= 0:
        return 0.0
    return float(1.0 - (ss_res / ss_tot))


def _kfold_indices(
    n_samples: int, folds: int, seed: int
) -> Iterable[Tuple[np.ndarray, np.ndarray]]:
    if folds < 2:
        raise CostEstimationError("folds must be >= 2")
    if n_samples < folds:
        raise CostEstimationError("folds cannot exceed number of rows")

    rng = np.random.default_rng(seed)
    indices = np.arange(n_samples)
    rng.shuffle(indices)
    split_indices = np.array_split(indices, folds)

    for i in range(folds):
        valid_idx = split_indices[i]
        train_idx = np.concatenate([split_indices[j] for j in range(folds) if j != i])
        yield train_idx, valid_idx


def _ensure_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise CostEstimationError(f"dataset is missing required columns: {missing}")


def _clean_training_rows(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    # Use whichever numeric features are present in the dataset
    numeric_cols = [c for c in NUMERIC_FEATURES + ["risk_score_original"] if c in cleaned.columns]
    for col in numeric_cols + [TARGET_OVERRUN, TARGET_ACTUAL_COST]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    cleaned = cleaned.dropna(
        subset=[TARGET_OVERRUN, TARGET_ACTUAL_COST, ESTIMATED_COST]
    )
    cleaned = cleaned[cleaned[ESTIMATED_COST] > 0]
    cleaned = cleaned[cleaned[TARGET_ACTUAL_COST] > 0]
    cleaned = cleaned.reset_index(drop=True)
    if cleaned.empty:
        raise CostEstimationError("dataset has no usable rows after cleaning")
    return cleaned


def _category_levels(df: pd.DataFrame) -> Dict[str, List[str]]:
    levels: Dict[str, List[str]] = {}
    for col in CATEGORICAL_FEATURES:
        levels[col] = sorted(df[col].astype(str).fillna("").unique().tolist())
    return levels


def _numeric_medians(df: pd.DataFrame) -> Dict[str, float]:
    medians: Dict[str, float] = {}
    for col in NUMERIC_FEATURES:
        series = pd.to_numeric(df[col], errors="coerce")
        median = float(series.median()) if not series.dropna().empty else 0.0
        medians[col] = median
    return medians


def _build_feature_matrix(
    df: pd.DataFrame,
    category_levels: Mapping[str, List[str]],
    medians: Mapping[str, float],
) -> np.ndarray:
    features: List[np.ndarray] = []

    for col in NUMERIC_FEATURES:
        series = pd.to_numeric(df[col], errors="coerce").fillna(float(medians[col]))
        features.append(series.to_numpy(dtype=float).reshape(-1, 1))

    for col in CATEGORICAL_FEATURES:
        values = df[col].astype(str).fillna("")
        for level in category_levels[col]:
            encoded = (values == level).astype(float).to_numpy().reshape(-1, 1)
            features.append(encoded)

    if not features:
        return np.empty((len(df), 0), dtype=float)
    return np.hstack(features)


def _feature_names(category_levels: Mapping[str, List[str]]) -> List[str]:
    names = list(NUMERIC_FEATURES)
    for col in CATEGORICAL_FEATURES:
        for level in category_levels[col]:
            names.append(f"{col}__{level}")
    return names


def _fit_ridge(X: np.ndarray, y: np.ndarray, ridge_alpha: float) -> _RidgeModel:
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0.0] = 1.0
    X_norm = (X - means) / stds

    X_bias = np.c_[np.ones(len(X_norm)), X_norm]
    reg = np.eye(X_bias.shape[1], dtype=float)
    reg[0, 0] = 0.0  # do not regularize intercept

    xtx = X_bias.T @ X_bias
    xty = X_bias.T @ y
    weights = np.linalg.pinv(xtx + (ridge_alpha * reg)) @ xty

    return _RidgeModel(
        bias=float(weights[0]),
        weights=weights[1:].astype(float),
        means=means.astype(float),
        stds=stds.astype(float),
    )


def _predict_overrun(X: np.ndarray, model: _RidgeModel) -> np.ndarray:
    X_norm = (X - model.means) / model.stds
    return model.bias + (X_norm @ model.weights)


def _evaluate_actual_cost(
    y_true_actual: np.ndarray,
    estimated_cost: np.ndarray,
    pred_overrun_pct: np.ndarray,
) -> Dict[str, float]:
    pred_actual = estimated_cost * (1.0 + (pred_overrun_pct / 100.0))
    pred_actual = np.maximum(pred_actual, 0.0)
    return {
        "mae_cad": _mae(y_true_actual, pred_actual),
        "rmse_cad": _rmse(y_true_actual, pred_actual),
        "mape": _mape(y_true_actual, pred_actual),
        "r2": _r2(y_true_actual, pred_actual),
    }


def _evaluate_overrun(
    y_true_overrun: np.ndarray, pred_overrun_pct: np.ndarray
) -> Dict[str, float]:
    return {
        "mae_pct": _mae(y_true_overrun, pred_overrun_pct),
        "rmse_pct": _rmse(y_true_overrun, pred_overrun_pct),
        "mape": _mape(y_true_overrun, pred_overrun_pct),
        "r2": _r2(y_true_overrun, pred_overrun_pct),
    }


def _artifact_dict(
    *,
    model: _RidgeModel,
    category_levels: Dict[str, List[str]],
    medians: Dict[str, float],
    metrics: Dict[str, Any],
    ridge_alpha: float,
    dataset_path: str,
    training_rows: int,
) -> Dict[str, Any]:
    return {
        "artifact_version": "1.0",
        "trained_at_utc": _utc_now_iso(),
        "dataset_path": dataset_path,
        "training_rows": int(training_rows),
        "ridge_alpha": float(ridge_alpha),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "category_levels": category_levels,
        "numeric_medians": medians,
        "feature_names": _feature_names(category_levels),
        "model": {
            "bias": float(model.bias),
            "weights": [float(v) for v in model.weights.tolist()],
            "means": [float(v) for v in model.means.tolist()],
            "stds": [float(v) for v in model.stds.tolist()],
        },
        "targets": {
            "primary": TARGET_OVERRUN,
            "derived": TARGET_ACTUAL_COST,
        },
        "metrics": metrics,
    }


def train_cost_estimation_model(
    dataset_path: Path,
    output_model_path: Path,
    *,
    ridge_alpha: float = 10.0,
    folds: int = 5,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Train and persist a two-stage cost estimation model artifact."""
    if ridge_alpha <= 0:
        raise CostEstimationError("ridge_alpha must be > 0")
    if folds < 2:
        raise CostEstimationError("folds must be >= 2")

    if not dataset_path.exists() or not dataset_path.is_file():
        raise CostEstimationError(f"dataset does not exist: {dataset_path}")

    df = pd.read_csv(dataset_path)
    _ensure_columns(df, REQUIRED_TRAINING_COLUMNS)
    df = _clean_training_rows(df)

    y_overrun = df[TARGET_OVERRUN].to_numpy(dtype=float)
    y_actual = df[TARGET_ACTUAL_COST].to_numpy(dtype=float)
    estimated_cost = df[ESTIMATED_COST].to_numpy(dtype=float)

    # Out-of-fold evaluation
    oof_pred_overrun = np.zeros(len(df), dtype=float)
    for train_idx, valid_idx in _kfold_indices(len(df), folds=folds, seed=random_seed):
        train_df = df.iloc[train_idx].reset_index(drop=True)
        valid_df = df.iloc[valid_idx].reset_index(drop=True)

        levels = _category_levels(train_df)
        medians = _numeric_medians(train_df)
        X_train = _build_feature_matrix(train_df, levels, medians)
        X_valid = _build_feature_matrix(valid_df, levels, medians)
        y_train = train_df[TARGET_OVERRUN].to_numpy(dtype=float)

        fold_model = _fit_ridge(X_train, y_train, ridge_alpha=ridge_alpha)
        oof_pred_overrun[valid_idx] = _predict_overrun(X_valid, fold_model)

    oof_actual_metrics = _evaluate_actual_cost(
        y_actual, estimated_cost, oof_pred_overrun
    )
    oof_overrun_metrics = _evaluate_overrun(y_overrun, oof_pred_overrun)

    baseline_actual = estimated_cost
    baseline_metrics = {
        "mae_cad": _mae(y_actual, baseline_actual),
        "rmse_cad": _rmse(y_actual, baseline_actual),
        "mape": _mape(y_actual, baseline_actual),
        "r2": _r2(y_actual, baseline_actual),
    }

    oof_pred_actual = np.maximum(
        estimated_cost * (1.0 + (oof_pred_overrun / 100.0)), 0.0
    )
    oof_ape = np.abs(y_actual - oof_pred_actual) / np.maximum(y_actual, 1.0)
    residual_quantiles = {
        "0.50": float(np.quantile(oof_ape, 0.50)),
        "0.80": float(np.quantile(oof_ape, 0.80)),
        "0.90": float(np.quantile(oof_ape, 0.90)),
        "0.95": float(np.quantile(oof_ape, 0.95)),
    }

    # Fit final model on all rows
    levels = _category_levels(df)
    medians = _numeric_medians(df)
    X_full = _build_feature_matrix(df, levels, medians)
    final_model = _fit_ridge(X_full, y_overrun, ridge_alpha=ridge_alpha)
    full_pred_overrun = _predict_overrun(X_full, final_model)

    final_actual_metrics = _evaluate_actual_cost(
        y_actual, estimated_cost, full_pred_overrun
    )
    final_overrun_metrics = _evaluate_overrun(y_overrun, full_pred_overrun)

    metrics = {
        "cross_validation": {
            "folds": folds,
            "random_seed": random_seed,
            "actual_cost": oof_actual_metrics,
            "overrun_pct": oof_overrun_metrics,
        },
        "baseline_estimated_cost": {
            "actual_cost": baseline_metrics,
        },
        "train_fit": {
            "actual_cost": final_actual_metrics,
            "overrun_pct": final_overrun_metrics,
        },
        "prediction_interval_ape_quantiles": residual_quantiles,
    }

    # Store training data range for prediction reasonableness validation.
    dataset_stats = {
        "estimated_cost_min": float(estimated_cost.min()),
        "estimated_cost_max": float(estimated_cost.max()),
        "overrun_pct_min": float(y_overrun.min()),
        "overrun_pct_max": float(y_overrun.max()),
        "actual_cost_min": float(y_actual.min()),
        "actual_cost_max": float(y_actual.max()),
    }

    artifact = _artifact_dict(
        model=final_model,
        category_levels=levels,
        medians=medians,
        metrics=metrics,
        ridge_alpha=ridge_alpha,
        dataset_path=str(dataset_path),
        training_rows=len(df),
    )
    artifact["dataset_stats"] = dataset_stats

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    output_model_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "success": True,
        "model_path": str(output_model_path),
        "training_rows": len(df),
        "metrics": metrics,
    }


def _load_and_validate_dataset(
    dataset_path: Path, folds: int
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Shared dataset loading for both Ridge and CatBoost training."""
    if not dataset_path.exists() or not dataset_path.is_file():
        raise CostEstimationError(f"dataset does not exist: {dataset_path}")

    df = pd.read_csv(dataset_path)

    # Accept both remediated (no risk_score_original) and legacy datasets
    has_legacy = "risk_score_original" in df.columns
    if has_legacy:
        _ensure_columns(df, _LEGACY_REQUIRED_COLUMNS)
    else:
        _ensure_columns(df, REQUIRED_TRAINING_COLUMNS)

    df = _clean_training_rows(df)
    y_overrun = df[TARGET_OVERRUN].to_numpy(dtype=float)
    y_actual = df[TARGET_ACTUAL_COST].to_numpy(dtype=float)
    estimated_cost = df[ESTIMATED_COST].to_numpy(dtype=float)
    return df, y_overrun, y_actual, estimated_cost


def _compute_all_metrics(
    y_overrun: np.ndarray,
    y_actual: np.ndarray,
    estimated_cost: np.ndarray,
    oof_pred_overrun: np.ndarray,
    full_pred_overrun: np.ndarray,
    folds: int,
    random_seed: int,
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Shared metrics computation for both Ridge and CatBoost training."""
    oof_actual_metrics = _evaluate_actual_cost(y_actual, estimated_cost, oof_pred_overrun)
    oof_overrun_metrics = _evaluate_overrun(y_overrun, oof_pred_overrun)

    baseline_metrics = {
        "mae_cad": _mae(y_actual, estimated_cost),
        "rmse_cad": _rmse(y_actual, estimated_cost),
        "mape": _mape(y_actual, estimated_cost),
        "r2": _r2(y_actual, estimated_cost),
    }

    oof_pred_actual = np.maximum(estimated_cost * (1.0 + (oof_pred_overrun / 100.0)), 0.0)
    oof_ape = np.abs(y_actual - oof_pred_actual) / np.maximum(y_actual, 1.0)
    residual_quantiles = {
        "0.50": float(np.quantile(oof_ape, 0.50)),
        "0.80": float(np.quantile(oof_ape, 0.80)),
        "0.90": float(np.quantile(oof_ape, 0.90)),
        "0.95": float(np.quantile(oof_ape, 0.95)),
    }

    final_actual_metrics = _evaluate_actual_cost(y_actual, estimated_cost, full_pred_overrun)
    final_overrun_metrics = _evaluate_overrun(y_overrun, full_pred_overrun)

    metrics = {
        "cross_validation": {
            "folds": folds,
            "random_seed": random_seed,
            "actual_cost": oof_actual_metrics,
            "overrun_pct": oof_overrun_metrics,
        },
        "baseline_estimated_cost": {"actual_cost": baseline_metrics},
        "train_fit": {
            "actual_cost": final_actual_metrics,
            "overrun_pct": final_overrun_metrics,
        },
        "prediction_interval_ape_quantiles": residual_quantiles,
    }

    dataset_stats = {
        "estimated_cost_min": float(estimated_cost.min()),
        "estimated_cost_max": float(estimated_cost.max()),
        "overrun_pct_min": float(y_overrun.min()),
        "overrun_pct_max": float(y_overrun.max()),
        "actual_cost_min": float(y_actual.min()),
        "actual_cost_max": float(y_actual.max()),
    }

    return metrics, dataset_stats


def train_catboost_model(
    dataset_path: Path,
    output_model_path: Path,
    *,
    iterations: int = 500,
    learning_rate: float = 0.05,
    depth: int = 6,
    folds: int = 5,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """Train CatBoost model for overrun prediction + Ridge for actual cost."""
    try:
        from catboost import CatBoostRegressor, Pool
        import shap
    except ImportError as e:
        raise CostEstimationError(
            f"CatBoost/SHAP not installed: {e}. Install: pip install catboost shap"
        ) from e

    logger = logging.getLogger(__name__)

    df, y_overrun, y_actual, estimated_cost = _load_and_validate_dataset(dataset_path, folds)

    # Prepare CatBoost features (native categoricals, no one-hot)
    cat_indices = [NUMERIC_FEATURES.index(f) if f in NUMERIC_FEATURES else None for f in CATEGORICAL_FEATURES]
    # CatBoost feature order: numeric features + categorical features
    cb_feature_names = list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES)

    def _make_cb_matrix(frame: pd.DataFrame) -> np.ndarray:
        parts = []
        for col in NUMERIC_FEATURES:
            parts.append(pd.to_numeric(frame[col], errors="coerce").fillna(0).to_numpy().reshape(-1, 1))
        for col in CATEGORICAL_FEATURES:
            parts.append(frame[col].astype(str).fillna("").to_numpy().reshape(-1, 1))
        return np.hstack(parts)

    cat_feature_indices = list(range(len(NUMERIC_FEATURES), len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)))

    # Out-of-fold CatBoost evaluation
    oof_pred_overrun = np.zeros(len(df), dtype=float)
    for train_idx, valid_idx in _kfold_indices(len(df), folds=folds, seed=random_seed):
        train_df = df.iloc[train_idx].reset_index(drop=True)
        valid_df = df.iloc[valid_idx].reset_index(drop=True)

        X_train = _make_cb_matrix(train_df)
        X_valid = _make_cb_matrix(valid_df)
        y_train = train_df[TARGET_OVERRUN].to_numpy(dtype=float)

        train_pool = Pool(X_train, y_train, cat_features=cat_feature_indices, feature_names=cb_feature_names)
        valid_pool = Pool(X_valid, cat_features=cat_feature_indices, feature_names=cb_feature_names)

        fold_model = CatBoostRegressor(
            iterations=iterations,
            learning_rate=learning_rate,
            depth=depth,
            l2_leaf_reg=3,
            random_seed=random_seed,
            verbose=0,
        )
        fold_model.fit(train_pool, eval_set=Pool(X_valid, valid_df[TARGET_OVERRUN].to_numpy(dtype=float), cat_features=cat_feature_indices, feature_names=cb_feature_names), verbose=0)
        oof_pred_overrun[valid_idx] = fold_model.predict(valid_pool)

    # Train final CatBoost on all data
    X_full = _make_cb_matrix(df)
    full_pool = Pool(X_full, y_overrun, cat_features=cat_feature_indices, feature_names=cb_feature_names)
    final_cb = CatBoostRegressor(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        l2_leaf_reg=3,
        random_seed=random_seed,
        verbose=0,
    )
    final_cb.fit(full_pool)
    full_pred_overrun = final_cb.predict(X_full)

    # SHAP expected value
    explainer = shap.TreeExplainer(final_cb)
    ev = explainer.expected_value
    shap_expected = float(ev.item()) if hasattr(ev, 'item') else float(ev)
    logger.info("CatBoost SHAP expected value (base overrun rate): %.2f%%", shap_expected)

    # Also train Ridge for actual cost (existing behavior)
    levels = _category_levels(df)
    medians = _numeric_medians(df)
    X_ridge = _build_feature_matrix(df, levels, medians)
    ridge_model = _fit_ridge(X_ridge, y_overrun, ridge_alpha=10.0)

    # Compute metrics
    metrics, dataset_stats = _compute_all_metrics(
        y_overrun, y_actual, estimated_cost, oof_pred_overrun, full_pred_overrun, folds, random_seed
    )

    # Compute feature min/max for similar project normalization
    feature_ranges: Dict[str, Dict[str, float]] = {}
    for col in SIMILAR_DISTANCE_FEATURES:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        feature_ranges[col] = {"min": float(series.min()), "max": float(series.max())}

    # Save CatBoost model binary
    cbm_path = output_model_path.parent / "catboost_overrun.cbm"
    final_cb.save_model(str(cbm_path))

    # Build v2.0 artifact JSON (unified metadata)
    artifact = {
        "artifact_version": "2.0",
        "trained_at_utc": _utc_now_iso(),
        "dataset_path": str(dataset_path),
        "training_rows": len(df),
        "model_type": "catboost+ridge",
        "catboost_config": {
            "iterations": iterations,
            "learning_rate": learning_rate,
            "depth": depth,
            "l2_leaf_reg": 3,
        },
        "ridge_alpha": 10.0,
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "catboost_feature_names": cb_feature_names,
        "catboost_cat_indices": cat_feature_indices,
        "category_levels": levels,
        "numeric_medians": medians,
        "feature_names": _feature_names(levels),  # For Ridge compatibility
        "model": {  # Ridge weights for actual cost prediction
            "bias": float(ridge_model.bias),
            "weights": [float(v) for v in ridge_model.weights.tolist()],
            "means": [float(v) for v in ridge_model.means.tolist()],
            "stds": [float(v) for v in ridge_model.stds.tolist()],
        },
        "catboost_model_path": str(cbm_path),
        "shap_expected_value": shap_expected,
        "feature_ranges": feature_ranges,
        "targets": {"primary": TARGET_OVERRUN, "derived": TARGET_ACTUAL_COST},
        "metrics": metrics,
        "dataset_stats": dataset_stats,
    }

    output_model_path.parent.mkdir(parents=True, exist_ok=True)
    output_model_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "CatBoost model trained: overrun CV R²=%.3f, actual cost CV R²=%.3f",
        metrics["cross_validation"]["overrun_pct"]["r2"],
        metrics["cross_validation"]["actual_cost"]["r2"],
    )

    return {
        "success": True,
        "model_path": str(output_model_path),
        "catboost_model_path": str(cbm_path),
        "training_rows": len(df),
        "metrics": metrics,
    }


class CostEstimationService:
    """Loads model artifact and serves project-level predictions with SHAP explainability."""

    DEFAULT_MODEL_PATH = (
        Path(__file__).resolve().parent.parent.parent
        / "workspace"
        / "models"
        / "cost_estimation"
        / "latest.json"
    )

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self._artifact: Optional[Dict[str, Any]] = None
        self._model: Optional[_RidgeModel] = None
        self._catboost_model: Any = None  # CatBoostRegressor or None
        self._shap_explainer: Any = None  # shap.TreeExplainer or None
        self._dataset_df: Optional[pd.DataFrame] = None  # For similar project lookup
        if self.model_path.exists():
            self.load(self.model_path)

    def is_loaded(self) -> bool:
        return self._artifact is not None and self._model is not None

    @property
    def has_catboost(self) -> bool:
        return self._catboost_model is not None

    def load(self, model_path: Optional[Path] = None) -> None:
        logger = logging.getLogger(__name__)
        path = model_path or self.model_path
        if not path.exists():
            raise CostEstimationError(f"model artifact not found: {path}")

        artifact = json.loads(path.read_text(encoding="utf-8"))
        for required in (
            "numeric_features",
            "categorical_features",
            "category_levels",
            "model",
        ):
            if required not in artifact:
                raise CostEstimationError(f"invalid artifact; missing '{required}'")

        model_payload = artifact["model"]
        self._model = _RidgeModel(
            bias=float(model_payload["bias"]),
            weights=np.array(model_payload["weights"], dtype=float),
            means=np.array(model_payload["means"], dtype=float),
            stds=np.array(model_payload["stds"], dtype=float),
        )
        self._artifact = artifact
        self.model_path = path

        # Load CatBoost model if v2.0 artifact
        version = artifact.get("artifact_version", "1.0")
        if version >= "2.0":
            cbm_path_str = artifact.get("catboost_model_path", "")
            cbm_path = Path(cbm_path_str) if cbm_path_str else None
            if cbm_path and cbm_path.exists():
                try:
                    from catboost import CatBoostRegressor
                    import shap
                    self._catboost_model = CatBoostRegressor()
                    self._catboost_model.load_model(str(cbm_path))
                    self._shap_explainer = shap.TreeExplainer(self._catboost_model)
                    logger.info("CatBoost model loaded from %s", cbm_path)
                except ImportError:
                    logger.warning("CatBoost/SHAP not installed; falling back to Ridge only")
                except Exception as e:
                    logger.warning("Failed to load CatBoost model: %s; using Ridge fallback", e)

            # Load dataset for similar project lookup
            dataset_path_str = artifact.get("dataset_path", "")
            if dataset_path_str:
                ds_path = Path(dataset_path_str)
                if ds_path.exists():
                    try:
                        self._dataset_df = pd.read_csv(ds_path)
                        logger.info("Dataset loaded for similar projects: %d rows", len(self._dataset_df))
                    except Exception as e:
                        logger.warning("Failed to load dataset for similar projects: %s", e)

    def metadata(self) -> Dict[str, Any]:
        if self._artifact is None:
            return {
                "loaded": False,
                "model_path": str(self.model_path),
            }
        return {
            "loaded": True,
            "model_path": str(self.model_path),
            "trained_at_utc": self._artifact.get("trained_at_utc"),
            "training_rows": self._artifact.get("training_rows"),
            "ridge_alpha": self._artifact.get("ridge_alpha"),
            "model_type": self._artifact.get("model_type", "ridge"),
            "has_catboost": self.has_catboost,
            "shap_expected_value": self._artifact.get("shap_expected_value"),
            "metrics": self._artifact.get("metrics", {}),
        }

    def predict_project(
        self,
        project: Mapping[str, Any],
        *,
        confidence_quantile: float = 0.90,
    ) -> Dict[str, Any]:
        if not self.is_loaded() or self._artifact is None or self._model is None:
            raise CostEstimationError("cost estimation model is not loaded")

        medians = self._artifact["numeric_medians"]
        levels = self._artifact["category_levels"]

        row: Dict[str, Any] = {}
        for col in NUMERIC_FEATURES:
            raw = project.get(col, medians[col])
            try:
                row[col] = float(raw)
            except (TypeError, ValueError):
                row[col] = float(medians[col])

        for col in CATEGORICAL_FEATURES:
            raw = project.get(col, "")
            row[col] = str(raw).strip()

        input_df = pd.DataFrame([row])

        # Use CatBoost for overrun prediction if available, else Ridge
        shap_contributions: Optional[List[Dict[str, Any]]] = None
        shap_base_rate: Optional[float] = None

        if self._catboost_model is not None and self._shap_explainer is not None:
            cb_features = list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES)
            cb_row = []
            for col in NUMERIC_FEATURES:
                cb_row.append(row[col])
            for col in CATEGORICAL_FEATURES:
                cb_row.append(row[col])
            cb_matrix = np.array([cb_row], dtype=object)

            pred_overrun = float(self._catboost_model.predict(cb_matrix)[0])

            # SHAP values
            sv = self._shap_explainer.shap_values(cb_matrix)
            shap_vals = sv[0] if isinstance(sv, np.ndarray) else np.array(sv)[0]
            shap_base_rate = float(self._artifact.get("shap_expected_value", 0.0))

            # Build top-5 contributions sorted by absolute magnitude
            contributions = []
            for i, feat in enumerate(cb_features):
                val = float(shap_vals[i])
                if abs(val) < 0.001:
                    continue
                label = FEATURE_LABELS.get(feat, feat)
                contributions.append({
                    "feature": feat,
                    "label": label,
                    "value": row.get(feat, None),
                    "contribution_pct": round(val, 2),
                    "direction": "increase" if val > 0 else "decrease",
                })
            contributions.sort(key=lambda c: abs(c["contribution_pct"]), reverse=True)
            shap_contributions = contributions[:5]
        else:
            X = _build_feature_matrix(input_df, levels, medians)
            pred_overrun = float(_predict_overrun(X, self._model)[0])

        estimated_cost = float(row[ESTIMATED_COST])
        pred_actual_cost = max(0.0, estimated_cost * (1.0 + (pred_overrun / 100.0)))

        interval_quantile, ape_quantile = self._resolve_interval_quantile(
            confidence_quantile
        )
        lower_bound = max(0.0, pred_actual_cost * (1.0 - ape_quantile))
        upper_bound = pred_actual_cost * (1.0 + ape_quantile)

        unknown_categories: Dict[str, str] = {}
        for col in CATEGORICAL_FEATURES:
            if row[col] not in levels[col]:
                unknown_categories[col] = row[col]

        confidence_degraded = bool(unknown_categories)

        warning = None
        if unknown_categories:
            cats = ", ".join(f"{k}={v}" for k, v in unknown_categories.items())
            warning = (
                f"Prediction reliability reduced. "
                f"Categories not in training data: {cats}."
            )

        # Reasonableness validation against training data range.
        reasonableness = {"within_training_range": True, "flags": []}
        stats = (self._artifact or {}).get("dataset_stats")
        if isinstance(stats, dict):
            if estimated_cost < stats.get("estimated_cost_min", 0) * 0.5:
                reasonableness["flags"].append("estimated_cost_below_training_range")
                reasonableness["within_training_range"] = False
            if estimated_cost > stats.get("estimated_cost_max", float("inf")) * 2.0:
                reasonableness["flags"].append("estimated_cost_above_training_range")
                reasonableness["within_training_range"] = False
            if pred_overrun < stats.get("overrun_pct_min", -100) - 20:
                reasonableness["flags"].append("predicted_overrun_unusually_low")
                reasonableness["within_training_range"] = False
            if pred_overrun > stats.get("overrun_pct_max", 100) + 20:
                reasonableness["flags"].append("predicted_overrun_unusually_high")
                reasonableness["within_training_range"] = False

        if reasonableness["flags"] and not warning:
            warning = (
                "Prediction may be less reliable: input values are outside the "
                "training data range."
            )

        result: Dict[str, Any] = {
            "predicted_cost_overrun_pct": pred_overrun,
            "predicted_actual_cost_cad": pred_actual_cost,
            "estimated_cost_cad": estimated_cost,
            "prediction_interval_cad": {
                "confidence_quantile": interval_quantile,
                "lower": lower_bound,
                "upper": upper_bound,
            },
            "uncertainty": {
                "ape_quantile": ape_quantile,
            },
            "reasonableness": reasonableness,
            "unknown_categories": unknown_categories,
            "confidence_degraded": confidence_degraded,
            "warning": warning,
        }

        if shap_contributions is not None:
            result["shap_contributions"] = shap_contributions
        if shap_base_rate is not None:
            result["shap_base_rate_pct"] = shap_base_rate

        result["model_info"] = {
            "type": "catboost" if self._catboost_model is not None else "ridge",
            "metrics": self._artifact.get("metrics", {}).get("cross_validation", {}),
            "training_rows": self._artifact.get("training_rows"),
            "data_source": "synthetic_remediated" if "2.0" <= self._artifact.get("artifact_version", "1.0") else "synthetic",
        }

        return result

    MAX_BATCH_SIZE = 200

    def predict_batch(
        self,
        projects: List[Mapping[str, Any]],
        *,
        confidence_quantile: float = 0.90,
        max_batch_size: int = MAX_BATCH_SIZE,
    ) -> List[Dict[str, Any]]:
        if len(projects) > max_batch_size:
            raise CostEstimationError(
                f"batch size {len(projects)} exceeds maximum of {max_batch_size}"
            )
        return [
            self.predict_project(project, confidence_quantile=confidence_quantile)
            for project in projects
        ]

    def find_similar_projects(
        self,
        project: Mapping[str, Any],
        *,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find the most similar projects in the training dataset."""
        if self._dataset_df is None or self._artifact is None:
            return []

        df = self._dataset_df
        project_type = str(project.get("project_type", ""))

        # Filter by project_type (mandatory); relax if < top_k matches
        type_mask = df["project_type"] == project_type
        candidates = df[type_mask]
        if len(candidates) < top_k:
            # Relax: match category prefix (e.g., "commercial_*")
            prefix = project_type.split("_")[0] if "_" in project_type else project_type
            candidates = df[df["project_type"].str.startswith(prefix)]
        if len(candidates) < top_k:
            candidates = df  # Use entire dataset as fallback

        # Compute min-max normalized Euclidean distance
        feature_ranges = self._artifact.get("feature_ranges", {})
        if not feature_ranges:
            return []

        dist_features = [f for f in SIMILAR_DISTANCE_FEATURES if f in feature_ranges]
        if not dist_features:
            return []

        input_vec = np.zeros(len(dist_features))
        for i, feat in enumerate(dist_features):
            val = float(project.get(feat, 0))
            fr = feature_ranges[feat]
            rng = fr["max"] - fr["min"]
            input_vec[i] = (val - fr["min"]) / rng if rng > 0 else 0.0

        cand_matrix = np.zeros((len(candidates), len(dist_features)))
        for i, feat in enumerate(dist_features):
            vals = pd.to_numeric(candidates[feat], errors="coerce").fillna(0).to_numpy()
            fr = feature_ranges[feat]
            rng = fr["max"] - fr["min"]
            cand_matrix[:, i] = (vals - fr["min"]) / rng if rng > 0 else 0.0

        distances = np.sqrt(np.sum((cand_matrix - input_vec) ** 2, axis=1))
        top_indices = np.argsort(distances)[:top_k]

        results = []
        for idx in top_indices:
            row = candidates.iloc[idx]
            # Find key difference: largest absolute feature delta
            key_diff = ""
            max_delta = 0.0
            for feat in dist_features:
                input_val = float(project.get(feat, 0))
                match_val = float(row.get(feat, 0))
                delta = abs(input_val - match_val)
                # Normalize by range for comparison
                fr = feature_ranges.get(feat, {})
                rng = fr.get("max", 1) - fr.get("min", 0)
                norm_delta = delta / rng if rng > 0 else 0
                if norm_delta > max_delta:
                    max_delta = norm_delta
                    label = FEATURE_LABELS.get(feat, feat)
                    direction = "higher" if match_val > input_val else "lower"
                    key_diff = f"{direction} {label} ({match_val:,.0f} vs {input_val:,.0f})"

            results.append({
                "project_type": str(row.get("project_type", "")),
                "location": str(row.get("location", "")),
                "sqft": float(row.get("sqft", 0)),
                "estimated_cost_cad": float(row.get("estimated_cost_cad", 0)),
                "actual_overrun_pct": float(row.get("cost_overrun_pct", 0)),
                "key_diff": key_diff,
                "similarity_score": round(1.0 / (1.0 + float(distances[idx])), 3),
            })

        return results

    def predict_what_if(
        self,
        project: Mapping[str, Any],
        overrides: List[Dict[str, Any]],
        *,
        confidence_quantile: float = 0.90,
    ) -> Dict[str, Any]:
        """Predict with feature overrides for what-if analysis."""
        if not overrides:
            raise CostEstimationError("overrides list cannot be empty")

        # Validate overrides
        warnings: List[str] = []
        modified_project = dict(project)
        for override in overrides:
            feat = override.get("feature", "")
            if feat not in WHATIF_FEATURES:
                raise CostEstimationError(
                    f"Feature '{feat}' is not adjustable. "
                    f"Allowed: {list(WHATIF_FEATURES.keys())}"
                )
            val = float(override.get("value", 0))
            lo, hi = WHATIF_FEATURES[feat]
            if val < lo or val > hi:
                clamped = max(lo, min(hi, val))
                warnings.append(f"{feat} clamped from {val} to {clamped} (range: {lo}-{hi})")
                val = clamped
            modified_project[feat] = val

        modified_prediction = self.predict_project(modified_project, confidence_quantile=confidence_quantile)

        # Compute delta — actual_cost derived from CatBoost overrun for consistency
        modified_overrun = modified_prediction["predicted_cost_overrun_pct"]
        estimated = float(project.get("estimated_cost_cad", 0))
        modified_actual = max(0.0, estimated * (1.0 + modified_overrun / 100.0))
        modified_prediction["predicted_actual_cost_cad"] = modified_actual

        return {
            "modified_prediction": modified_prediction,
            "overrides_applied": overrides,
            "warnings": warnings,
        }

    def get_data_transparency(self) -> Dict[str, Any]:
        """Return dataset statistics and limitations for the transparency panel."""
        if self._artifact is None:
            return {"available": False}

        stats = self._artifact.get("dataset_stats", {})
        metrics = self._artifact.get("metrics", {})
        cv = metrics.get("cross_validation", {})

        return {
            "available": True,
            "dataset": {
                "rows": self._artifact.get("training_rows", 0),
                "source": "synthetic_remediated" if self._artifact.get("artifact_version", "1.0") >= "2.0" else "synthetic",
                "features_numeric": len(NUMERIC_FEATURES),
                "features_categorical": len(CATEGORICAL_FEATURES),
            },
            "stats": stats,
            "model_performance": {
                "overrun_r2": cv.get("overrun_pct", {}).get("r2"),
                "overrun_mape": cv.get("overrun_pct", {}).get("mape"),
                "actual_cost_r2": cv.get("actual_cost", {}).get("r2"),
                "actual_cost_mape": cv.get("actual_cost", {}).get("mape"),
            },
            "limitations": [
                "Training data is synthetic (generated, not collected from real projects)",
                "Location cost adjustments based on Statistics Canada BCPI estimates",
                "Duration values were capped at 520 weeks during data remediation",
                "Risk score distribution was smoothed to remove artificial floor at 20.0",
                "Model has not been validated against real construction project outcomes",
            ],
        }

    def _resolve_interval_quantile(self, requested: float) -> Tuple[float, float]:
        if self._artifact is None:
            return 0.90, 0.10

        quantiles = self._artifact.get("metrics", {}).get(
            "prediction_interval_ape_quantiles", {}
        )
        if not quantiles:
            return 0.90, 0.10

        # Quantile keys are stored as strings like "0.90".
        numeric_quantiles: List[Tuple[float, float]] = []
        for q_key, ape in quantiles.items():
            try:
                numeric_quantiles.append((float(q_key), float(ape)))
            except (TypeError, ValueError):
                continue

        if not numeric_quantiles:
            return 0.90, 0.10

        # Select the smallest quantile >= requested.
        candidates = [(q, ape) for q, ape in numeric_quantiles if q >= requested]
        if candidates:
            selected = min(candidates, key=lambda item: item[0])
        else:
            # No quantile >= requested; use the maximum available.
            selected = max(numeric_quantiles, key=lambda item: item[0])
        return selected
