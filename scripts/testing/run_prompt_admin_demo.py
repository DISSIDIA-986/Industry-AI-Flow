"""Prompt-admin demo runner.

Checks core prompt admin APIs and optionally performs an experiment ramp:
10% -> 30% -> 50%.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional

import requests


class DemoError(RuntimeError):
    pass


def _request(
    session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    *,
    timeout: int = 20,
    **kwargs: Any,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    resp = session.request(method=method, url=url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


def _pick_pair(prompts: list[Dict[str, Any]]) -> Optional[tuple[Dict[str, Any], Dict[str, Any]]]:
    groups: dict[tuple[str, str], list[Dict[str, Any]]] = defaultdict(list)
    for item in prompts:
        key = (str(item.get("name")), str(item.get("category")))
        groups[key].append(item)
    for _, candidates in groups.items():
        if len(candidates) >= 2:
            return candidates[0], candidates[1]
    return None


def run_demo(base_url: str, api_key: Optional[str], execute_experiment: bool) -> Dict[str, Any]:
    session = requests.Session()
    if api_key:
        session.headers.update({"X-API-Key": api_key})

    summary: Dict[str, Any] = {
        "base_url": base_url,
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "steps": [],
    }

    categories = _request(session, base_url, "GET", "/api/prompts/categories/list")
    summary["steps"].append({"step": "categories", "count": len(categories or [])})

    prompt_payload = _request(
        session,
        base_url,
        "GET",
        "/api/prompts/",
        params={"page": 1, "size": 200, "is_active": True},
    )
    prompts = prompt_payload.get("data", [])
    summary["steps"].append({"step": "list_prompts", "count": len(prompts)})

    metrics = _request(
        session,
        base_url,
        "GET",
        "/api/prompts/metrics/summary",
        params={"days": 14, "top_limit": 5},
    )
    summary["steps"].append(
        {
            "step": "metrics_summary",
            "usage_logs": metrics.get("totals", {}).get("usage_logs", 0),
        }
    )

    if not execute_experiment:
        summary["steps"].append({"step": "experiment_flow", "skipped": True})
        return summary

    pair = _pick_pair(prompts)
    if not pair:
        summary["steps"].append(
            {
                "step": "experiment_flow",
                "skipped": True,
                "reason": "need at least 2 prompts with same name/category",
            }
        )
        return summary

    prompt_a, prompt_b = pair
    exp_name = f"demo_{prompt_a['name']}_{int(datetime.utcnow().timestamp())}"
    created = _request(
        session,
        base_url,
        "POST",
        "/api/prompts/experiments",
        json={
            "name": exp_name,
            "description": "prompt-admin demo",
            "prompt_a_id": prompt_a["id"],
            "prompt_b_id": prompt_b["id"],
            "traffic_split": 0.1,
            "metrics": {"target": "success_rate"},
            "created_by": "demo-script",
        },
    )
    experiment = created.get("experiment", {})
    exp_id = experiment.get("id")
    if not exp_id:
        raise DemoError("experiment creation did not return experiment id")

    summary["steps"].append({"step": "create_experiment", "experiment_id": exp_id, "traffic_split": 0.1})

    for split in (0.3, 0.5):
        updated = _request(
            session,
            base_url,
            "PATCH",
            f"/api/prompts/experiments/{exp_id}/traffic",
            json={"traffic_split": split},
        )
        summary["steps"].append(
            {
                "step": "ramp_traffic",
                "split": split,
                "status": updated.get("experiment", {}).get("status"),
            }
        )

    paused = _request(
        session,
        base_url,
        "PATCH",
        f"/api/prompts/experiments/{exp_id}/status",
        json={"status": "paused"},
    )
    summary["steps"].append(
        {
            "step": "pause_experiment",
            "status": paused.get("experiment", {}).get("status"),
        }
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run prompt admin demo checks.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base url")
    parser.add_argument("--api-key", default=None, help="optional API key")
    parser.add_argument(
        "--execute-experiment",
        action="store_true",
        help="execute experiment create and traffic ramp flow",
    )
    parser.add_argument("--pretty", action="store_true", help="pretty print json output")
    args = parser.parse_args()

    try:
        result = run_demo(
            base_url=args.base_url,
            api_key=args.api_key,
            execute_experiment=args.execute_experiment,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1

    if args.pretty:
        print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
