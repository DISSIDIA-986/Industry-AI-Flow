#!/usr/bin/env python3
"""Run ONE analysis case and dump the full result envelope for root-cause.

Usage: python scripts/testing/probe_one_case.py <dataset_path> "<instruction>"
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API = "http://localhost:8000"


def _pw() -> str:
    for line in (PROJECT_ROOT / ".env").read_text().splitlines():
        if line.startswith("DEMO_USER_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no pw")


def main() -> int:
    ds, instr = sys.argv[1], sys.argv[2]
    b = json.dumps({"email": "demo@example.com", "password": _pw()}).encode()
    r = urllib.request.Request(f"{API}/api/v1/auth/login", data=b, headers={"Content-Type": "application/json"})
    token = json.load(urllib.request.urlopen(r, timeout=30))["token"]
    fid = json.loads(subprocess.run(
        ["curl", "-s", "-X", "POST", f"{API}/api/v1/data/upload",
         "-H", f"Authorization: Bearer {token}", "-F", f"file=@{ds}"],
        capture_output=True, text=True, timeout=60).stdout)["file_id"]
    body = json.dumps({"data_file": fid, "instruction": instr, "generate_visualization": True}).encode()
    req = urllib.request.Request(f"{API}/api/v1/data/analyze/start", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    job = json.load(urllib.request.urlopen(req, timeout=30))["job_id"]
    print(f"[job] {job}", flush=True)
    deadline = time.time() + 180
    res = {}
    while time.time() < deadline:
        time.sleep(3)
        try:
            with urllib.request.urlopen(f"{API}/api/v1/data/analyze/result/{job}", timeout=10) as r:
                body = json.load(r)
        except Exception:
            continue
        if body.get("status") == "done":
            res = body.get("result") or {}
            break
    cg = res.get("code_generation") or {}
    print("=" * 70)
    print(f"success={res.get('success')} charts={len(res.get('charts') or [])} "
          f"rounds={cg.get('rounds')} repair={cg.get('repair_trigger_type')} "
          f"fallback={cg.get('fallback_reason')}")
    print("--- ANSWER ---"); print(str(res.get("answer"))[:800])
    print("--- STDERR ---"); print(str(res.get("stderr"))[:2500])
    print("--- STDOUT ---"); print(str(res.get("stdout"))[:1500])
    print("--- CODE (final) ---"); print(str(res.get("code") or cg.get("code"))[:3000])
    print("--- CHARTS ---")
    for c in (res.get("charts") or []):
        print(f"  {c.get('id')} {c.get('type')} status={c.get('status')} err={str(c.get('error'))[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
