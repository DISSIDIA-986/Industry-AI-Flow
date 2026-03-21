"""Cost estimation training and inference service."""

from __future__ import annotations

import json
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
    "risk_score_original",
]

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
    for col in NUMERIC_FEATURES + [TARGET_OVERRUN, TARGET_ACTUAL_COST]:
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


class CostEstimationService:
    """Loads model artifact and serves project-level predictions."""

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
        if self.model_path.exists():
            self.load(self.model_path)

    def is_loaded(self) -> bool:
        return self._artifact is not None and self._model is not None

    def load(self, model_path: Optional[Path] = None) -> None:
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

        return {
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
