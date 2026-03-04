#!/usr/bin/env python3
"""Capstone demo smoke runner with preflight checks and API sanity probes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_DATASET_COLUMNS: Tuple[str, ...] = (
    "project_type",
    "location",
    "sqft",
    "floors",
    "num_units",
    "planned_duration_weeks",
    "estimated_cost_cad",
    "actual_cost_cad",
    "cost_overrun_pct",
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
)

PREDICTION_FEATURE_COLUMNS: Tuple[str, ...] = (
    "project_type",
    "location",
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
)

INT_FIELDS = {
    "floors",
    "num_units",
    "complexity_score",
    "num_change_orders",
    "num_subcontractors",
}

FLOAT_FIELDS = set(PREDICTION_FEATURE_COLUMNS) - INT_FIELDS - {"project_type", "location"}


@dataclass
class CheckResult:
    name: str
    passed: bool
    required: bool
    detail: str


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip() or default


def _check_python(allow_non_313: bool) -> CheckResult:
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    is_313 = (sys.version_info.major, sys.version_info.minor) == (3, 13)
    if is_313:
        return CheckResult("python", True, True, f"Python {version}")
    if allow_non_313:
        return CheckResult("python", True, True, f"Python {version} (non-3.13 allowed)")
    return CheckResult(
        "python",
        False,
        True,
        f"Python {version} detected; expected 3.13.x for capstone baseline",
    )


def _check_dataset(dataset_path: Path) -> CheckResult:
    if not dataset_path.exists():
        return CheckResult("dataset", False, True, f"missing: {dataset_path}")

    try:
        with dataset_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or [])
            first_row = next(reader, None)
    except Exception as exc:
        return CheckResult("dataset", False, True, f"read failed: {exc}")

    missing_columns = sorted(set(REQUIRED_DATASET_COLUMNS) - set(fieldnames))
    if missing_columns:
        return CheckResult(
            "dataset",
            False,
            True,
            f"missing required columns: {missing_columns}",
        )

    if first_row is None:
        return CheckResult("dataset", False, True, "dataset has no rows")

    return CheckResult(
        "dataset",
        True,
        True,
        f"ok: {dataset_path} ({len(fieldnames)} columns)",
    )


def _check_postgres(host: str, port: int, skip: bool) -> CheckResult:
    if skip:
        return CheckResult("postgres", True, False, "skipped")

    try:
        with socket.create_connection((host, port), timeout=2):
            return CheckResult("postgres", True, True, f"reachable at {host}:{port}")
    except OSError as exc:
        return CheckResult(
            "postgres",
            False,
            True,
            f"not reachable at {host}:{port} ({exc})",
        )


def _fetch_ollama_models(ollama_host: str) -> Tuple[bool, List[str], str]:
    base = ollama_host.rstrip("/")
    url = urllib.parse.urljoin(base + "/", "api/tags")
    req = urllib.request.Request(url=url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return False, [], str(exc)
    except Exception as exc:
        return False, [], str(exc)

    models = payload.get("models", []) if isinstance(payload, dict) else []
    names: List[str] = []
    for item in models:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return True, names, "ok"


def _check_ollama(ollama_host: str, model: str, skip: bool) -> CheckResult:
    if skip:
        return CheckResult("ollama", True, False, "skipped")

    ok, models, detail = _fetch_ollama_models(ollama_host)
    if not ok:
        return CheckResult(
            "ollama",
            False,
            True,
            f"service unavailable at {ollama_host} ({detail})",
        )

    if model in models:
        return CheckResult("ollama", True, True, f"model '{model}' available")

    return CheckResult(
        "ollama",
        False,
        True,
        f"configured model '{model}' missing; installed models: {models or ['<none>']}",
    )


def _train_cost_model(dataset_path: Path, model_path: Path) -> Tuple[bool, str]:
    try:
        from backend.services.cost_estimation_service import train_cost_estimation_model

        result = train_cost_estimation_model(
            dataset_path=dataset_path,
            output_model_path=model_path,
            ridge_alpha=10.0,
            folds=5,
            random_seed=42,
        )
        return True, f"trained model rows={result.get('training_rows')}"
    except Exception as exc:
        return False, str(exc)


def _check_or_prepare_model(
    model_path: Path,
    dataset_path: Path,
    train_if_missing: bool,
) -> CheckResult:
    if model_path.exists():
        return CheckResult("cost_model", True, True, f"exists: {model_path}")

    if not train_if_missing:
        return CheckResult(
            "cost_model",
            False,
            True,
            f"missing: {model_path} (use --train-model-if-missing)",
        )

    ok, detail = _train_cost_model(dataset_path=dataset_path, model_path=model_path)
    if not ok:
        return CheckResult("cost_model", False, True, f"train failed: {detail}")
    return CheckResult("cost_model", True, True, f"trained: {model_path}; {detail}")


def _load_prediction_sample(dataset_path: Path) -> Dict[str, Any]:
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        first_row = next(reader)

    if first_row is None:
        raise ValueError("dataset has no rows")

    sample: Dict[str, Any] = {}
    for key in PREDICTION_FEATURE_COLUMNS:
        raw = first_row.get(key)
        if raw is None or raw == "":
            raise ValueError(f"dataset sample missing value for '{key}'")
        if key in INT_FIELDS:
            sample[key] = int(float(raw))
        elif key in FLOAT_FIELDS:
            sample[key] = float(raw)
        else:
            sample[key] = str(raw)
    return sample


class _FakeWorkflowRunner:
    async def run_workflow(
        self,
        query: str,
        session_id: str,
        user_id: str | None = None,
        thread_id: str | None = None,
        route_mode: str | None = None,
    ) -> Dict[str, Any]:
        del user_id, thread_id
        return {
            "success": True,
            "agent_response": f"demo-smoke handled: {query}",
            "intent_result": {"intent": "cost_estimation"},
            "metadata": {
                "provider_used": "local",
                "route_mode": route_mode or "local_only",
            },
            "error": None,
        }


def _run_api_smoke(model_path: Path, sample_project: Dict[str, Any], skip: bool) -> CheckResult:
    if skip:
        return CheckResult("api_smoke", True, False, "skipped")

    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api import cost_estimation_routes, workflow_query_routes
        from backend.api.workflow_query_routes import get_workflow_runner
    except Exception as exc:
        return CheckResult("api_smoke", False, True, f"import failed: {exc}")

    os.environ["COST_ESTIMATION_MODEL_PATH"] = str(model_path)
    cost_estimation_routes._service = None

    async def _mock_workflow_runner() -> _FakeWorkflowRunner:
        return _FakeWorkflowRunner()

    app = FastAPI()
    app.include_router(cost_estimation_routes.router)
    app.include_router(workflow_query_routes.router)

    @app.get("/api/v1/health")
    async def _health() -> Dict[str, str]:
        return {"status": "ok"}

    app.dependency_overrides[get_workflow_runner] = _mock_workflow_runner

    checks: List[str] = []
    try:
        with TestClient(app) as client:
            health_resp = client.get("/api/v1/health")
            if health_resp.status_code != 200:
                return CheckResult("api_smoke", False, True, "health endpoint failed")
            checks.append("health")

            wf_health_resp = client.get("/api/v1/workflow/health")
            if wf_health_resp.status_code != 200:
                return CheckResult("api_smoke", False, True, "workflow health endpoint failed")
            checks.append("workflow_health")

            cost_health_resp = client.get("/api/v1/cost-estimation/health")
            if cost_health_resp.status_code != 200:
                return CheckResult("api_smoke", False, True, "cost health endpoint failed")
            checks.append("cost_health")

            predict_resp = client.post(
                "/api/v1/cost-estimation/predict",
                json={"project": sample_project, "confidence_quantile": 0.9},
            )
            if predict_resp.status_code != 200:
                return CheckResult(
                    "api_smoke",
                    False,
                    True,
                    f"cost predict failed: {predict_resp.status_code}",
                )
            checks.append("cost_predict")

            workflow_resp = client.post(
                "/api/v1/workflow/query",
                json={
                    "query": "estimate construction cost risk for Toronto office",
                    "session_id": "demo-smoke-session",
                    "route_mode": "local_only",
                },
            )
            if workflow_resp.status_code != 200:
                return CheckResult(
                    "api_smoke",
                    False,
                    True,
                    f"workflow query failed: {workflow_resp.status_code}",
                )
            checks.append("workflow_query")
    finally:
        app.dependency_overrides.pop(get_workflow_runner, None)
        workflow_query_routes._workflow_service = None

    return CheckResult("api_smoke", True, True, f"passed checks: {checks}")


def _render(results: List[CheckResult], pretty: bool) -> str:
    required_failed = [r for r in results if r.required and not r.passed]
    payload = {
        "passed": len(required_failed) == 0,
        "required_failed": len(required_failed),
        "checks": [asdict(r) for r in results],
    }
    return json.dumps(payload, indent=2 if pretty else None, ensure_ascii=False)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-path",
        default="datasets/unified_construction_projects_enhanced.csv",
        help="Path to cost-estimation training dataset.",
    )
    parser.add_argument(
        "--model-path",
        default="workspace/models/cost_estimation/latest.json",
        help="Path to cost-estimation model artifact.",
    )
    parser.add_argument(
        "--ollama-host",
        default=_env("OLLAMA_HOST", "http://localhost:11434"),
        help="Ollama host URL.",
    )
    parser.add_argument(
        "--ollama-model",
        default=_env("OLLAMA_MODEL", "qwen3.5:4b"),
        help="Configured Ollama model name.",
    )
    parser.add_argument(
        "--postgres-host",
        default=_env("POSTGRES_HOST", "localhost"),
        help="PostgreSQL host.",
    )
    parser.add_argument(
        "--postgres-port",
        type=int,
        default=int(_env("POSTGRES_PORT", "5432")),
        help="PostgreSQL port.",
    )
    parser.add_argument(
        "--train-model-if-missing",
        action="store_true",
        help="Train cost model artifact when model file is missing.",
    )
    parser.add_argument(
        "--allow-non313-python",
        action="store_true",
        help="Allow running smoke checks on non-3.13 Python interpreter.",
    )
    parser.add_argument(
        "--skip-postgres-check",
        action="store_true",
        help="Skip PostgreSQL availability check.",
    )
    parser.add_argument(
        "--skip-ollama-check",
        action="store_true",
        help="Skip Ollama availability/model check.",
    )
    parser.add_argument(
        "--skip-api-smoke",
        action="store_true",
        help="Skip FastAPI TestClient smoke checks.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output.")
    return parser


def main(argv: List[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    dataset_path = Path(args.dataset_path)
    model_path = Path(args.model_path)

    results: List[CheckResult] = []
    results.append(_check_python(allow_non_313=args.allow_non313_python))
    results.append(_check_dataset(dataset_path=dataset_path))

    if results[-1].passed:
        results.append(
            _check_or_prepare_model(
                model_path=model_path,
                dataset_path=dataset_path,
                train_if_missing=args.train_model_if_missing,
            )
        )
    else:
        results.append(
            CheckResult(
                "cost_model",
                False,
                True,
                "skipped because dataset check failed",
            )
        )

    results.append(
        _check_postgres(
            host=args.postgres_host,
            port=args.postgres_port,
            skip=args.skip_postgres_check,
        )
    )
    results.append(
        _check_ollama(
            ollama_host=args.ollama_host,
            model=args.ollama_model,
            skip=args.skip_ollama_check,
        )
    )

    sample_project: Dict[str, Any] = {}
    can_run_api = (
        not args.skip_api_smoke
        and all(
            r.passed
            for r in results
            if r.name in {"python", "dataset", "cost_model"}
        )
    )

    if can_run_api:
        try:
            sample_project = _load_prediction_sample(dataset_path=dataset_path)
        except Exception as exc:
            results.append(
                CheckResult(
                    "api_smoke",
                    False,
                    True,
                    f"cannot build prediction sample: {exc}",
                )
            )
        else:
            results.append(
                _run_api_smoke(
                    model_path=model_path,
                    sample_project=sample_project,
                    skip=False,
                )
            )
    else:
        results.append(CheckResult("api_smoke", True, False, "skipped"))

    print(_render(results=results, pretty=args.pretty))
    required_failed = [r for r in results if r.required and not r.passed]
    return 0 if not required_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
