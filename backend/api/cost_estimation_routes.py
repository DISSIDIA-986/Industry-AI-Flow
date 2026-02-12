"""Cost estimation API routes."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from backend.config import settings
from backend.security.sanitizer import sanitize_identifier, sanitize_text
from backend.services.cost_estimation_service import (
    CostEstimationError,
    CostEstimationService,
    train_cost_estimation_model,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cost-estimation", tags=["cost-estimation"])

_service_lock = threading.Lock()
_service: Optional[CostEstimationService] = None


def _default_model_path() -> Path:
    raw = os.getenv("COST_ESTIMATION_MODEL_PATH")
    if raw:
        return Path(raw)
    return CostEstimationService.DEFAULT_MODEL_PATH


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_allowed_path(path_value: str, *, must_exist: bool) -> Path:
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed_roots = [
        Path.cwd().resolve(),
        Path(settings.temp_data_dir).resolve(),
        Path(os.getenv("TMPDIR", "/tmp")).resolve(),
        Path("/tmp").resolve(),
    ]

    if not any(_is_subpath(candidate, root) or candidate == root for root in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail="path must be within project workspace, TEMP_DATA_DIR, or /tmp",
        )

    if must_exist and not candidate.exists():
        raise HTTPException(status_code=404, detail=f"path does not exist: {candidate}")

    return candidate


def _get_service() -> CostEstimationService:
    global _service
    if _service is not None:
        return _service

    with _service_lock:
        if _service is None:
            _service = CostEstimationService(model_path=_default_model_path())
    return _service


class CostEstimationFeatures(BaseModel):
    project_type: str = Field(..., max_length=64)
    location: str = Field(..., max_length=64)
    sqft: float = Field(..., gt=0)
    floors: int = Field(..., ge=0)
    num_units: int = Field(..., ge=0)
    planned_duration_weeks: float = Field(..., gt=0)
    estimated_cost_cad: float = Field(..., gt=0)
    contractor_rating: float = Field(..., ge=0, le=5)
    complexity_score: int = Field(..., ge=1, le=10)
    team_experience_years: float = Field(..., ge=0)
    num_change_orders: int = Field(..., ge=0)
    weather_risk_factor: float = Field(..., ge=0)
    material_volatility: float = Field(..., ge=0)
    num_subcontractors: int = Field(..., ge=0)
    budget_pressure: float = Field(..., ge=0)
    risk_score: float = Field(..., ge=0)
    risk_score_original: float = Field(..., ge=0)

    @field_validator("project_type", "location", mode="before")
    @classmethod
    def _sanitize_identity_fields(cls, value: str, info: ValidationInfo) -> str:
        return sanitize_identifier(value, info.field_name, max_length=64)


class CostEstimationPredictRequest(BaseModel):
    project: CostEstimationFeatures
    confidence_quantile: float = Field(default=0.9, ge=0.5, le=0.99)


class CostEstimationBatchPredictRequest(BaseModel):
    projects: List[CostEstimationFeatures] = Field(..., min_length=1, max_length=200)
    confidence_quantile: float = Field(default=0.9, ge=0.5, le=0.99)


class CostEstimationTrainRequest(BaseModel):
    dataset_path: str = Field(..., min_length=1, max_length=1024)
    output_model_path: Optional[str] = Field(default=None, max_length=1024)
    ridge_alpha: float = Field(default=10.0, gt=0)
    folds: int = Field(default=5, ge=2, le=10)
    random_seed: int = Field(default=42, ge=0, le=2_147_483_647)

    @field_validator("dataset_path", mode="before")
    @classmethod
    def _sanitize_dataset_path(cls, value: str) -> str:
        return sanitize_text(value, field_name="dataset_path", max_length=1024)

    @field_validator("output_model_path", mode="before")
    @classmethod
    def _sanitize_output_model_path(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        return sanitize_text(value, field_name="output_model_path", max_length=1024)


@router.get("/health")
async def cost_estimation_health() -> Dict[str, Any]:
    service = _get_service()
    return {
        "status": "ok",
        "component": "cost_estimation",
        "model": service.metadata(),
    }


@router.post("/train")
async def train_cost_estimation(request: CostEstimationTrainRequest) -> Dict[str, Any]:
    dataset_path = _resolve_allowed_path(request.dataset_path, must_exist=True)
    if dataset_path.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="dataset_path must be a CSV file")

    output_path = (
        _resolve_allowed_path(request.output_model_path, must_exist=False)
        if request.output_model_path
        else _resolve_allowed_path(str(_default_model_path()), must_exist=False)
    )

    try:
        result = train_cost_estimation_model(
            dataset_path=dataset_path,
            output_model_path=output_path,
            ridge_alpha=request.ridge_alpha,
            folds=request.folds,
            random_seed=request.random_seed,
        )
    except CostEstimationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("cost estimation training failed")
        raise HTTPException(status_code=500, detail=f"training failed: {exc}") from exc

    service = _get_service()
    service.load(output_path)
    return result


@router.post("/predict")
async def predict_cost_estimation(request: CostEstimationPredictRequest) -> Dict[str, Any]:
    service = _get_service()
    try:
        prediction = service.predict_project(
            project=request.project.model_dump(),
            confidence_quantile=request.confidence_quantile,
        )
    except CostEstimationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "prediction": prediction,
    }


@router.post("/predict/batch")
async def batch_predict_cost_estimation(
    request: CostEstimationBatchPredictRequest,
) -> Dict[str, Any]:
    service = _get_service()
    try:
        predictions = service.predict_batch(
            projects=[item.model_dump() for item in request.projects],
            confidence_quantile=request.confidence_quantile,
        )
    except CostEstimationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "count": len(predictions),
        "predictions": predictions,
    }
