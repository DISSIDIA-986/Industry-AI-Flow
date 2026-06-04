#!/usr/bin/env python3
"""Probe the metadata/preview layer (_extract_dataset_info) against extreme datasets.

Real production path, no LLM / no sandbox: upload -> POST /api/v1/data/preview.
Surfaces parse-stage breakage (crashes, single-column mis-sniff, encoding failures,
duplicate/blank headers) cheaply, before burning slow E2E LLM+sandbox runs.

Requires backend on :8000. Creds via DEMO_USER_PASSWORD in .env.
Usage: python scripts/testing/probe_extreme_metadata.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTREME_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "extreme"
API = "http://localhost:8000"


def _password() -> str:
    env = PROJECT_ROOT / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("DEMO_USER_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("No DEMO_USER_PASSWORD in .env")


def _login() -> str:
    body = json.dumps({"email": "demo@example.com", "password": _password()}).encode()
    req = urllib.request.Request(f"{API}/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["token"]


def _upload(token: str, path: Path) -> str:
    out = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{API}/api/v1/data/upload",
         "-H", f"Authorization: Bearer {token}", "-F", f"file=@{path}"],
        capture_output=True, text=True, timeout=60).stdout
    try:
        return json.loads(out)["file_id"]
    except Exception:
        return f"__upload_err__:{out[:200]}"


def _preview(token: str, file_id: str) -> dict:
    body = json.dumps({"data_file": file_id}).encode()
    req = urllib.request.Request(f"{API}/api/v1/data/preview", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"http": 200, "body": json.load(r)}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read().decode()[:300]}
    except Exception as e:  # noqa: BLE001
        return {"http": None, "body": f"exc: {e}"}


def main() -> int:
    token = _login()
    files = sorted(p for p in EXTREME_DIR.glob("*.csv"))
    rows = []
    for p in files:
        fid = _upload(token, p)
        if fid.startswith("__upload_err__"):
            rows.append({"file": p.name, "stage": "upload", "ncols": None, "detail": fid[:120]})
            print(f"  [UP-ERR] {p.name:30s} {fid[:80]}", flush=True)
            continue
        res = _preview(token, fid)
        if res["http"] != 200:
            rows.append({"file": p.name, "stage": "preview", "http": res["http"],
                         "ncols": None, "detail": str(res["body"])[:200]})
            print(f"  [PV-{res['http']}] {p.name:30s} {str(res['body'])[:90]}", flush=True)
            continue
        body = res["body"]
        meta = body.get("metadata", {}) or {}
        names = meta.get("column_names") or []
        info = meta.get("columns_info") or []
        ncols = meta.get("columns") if isinstance(meta.get("columns"), int) else len(names)
        nrows = meta.get("rows")
        roles = {}
        for c in info:
            roles[c.get("role", "?")] = roles.get(c.get("role", "?"), 0) + 1
        rows.append({"file": p.name, "stage": "ok", "ncols": ncols, "nrows": nrows,
                     "roles": roles, "detail": ",".join(str(n) for n in names[:6])})
        print(f"  [OK]     {p.name:30s} ncols={ncols} nrows={nrows} roles={rows[-1]['roles']}  cols=[{rows[-1]['detail'][:55]}]", flush=True)

    out = PROJECT_ROOT / "docs" / "testing" / "extreme-coverage" / "metadata_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
