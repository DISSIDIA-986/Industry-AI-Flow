#!/usr/bin/env python3
"""Browser E2E for RAG citation page-number deep-linking.

Verifies the end-to-end UX of the citation deep-link feature in a real browser
(agent-browser CLI):

  1. Log in, open /workflow-chat, ask a question that has paged-PDF sources.
  2. Assert source citations render as clickable buttons with a page badge
     (data-testid="source-citation-N" + "source-page-badge-N").
  3. Click the first citation and assert the URL becomes
     /documents/<uuid>?page=<N>&chunk=<M>.
  4. On the document page, assert the PDF page-jump input (data-testid=
     "pdf-page-input") reflects the cited page, and the cited chunk row is
     marked data-target="true" (scrolled-to + highlighted).

Run:  python scripts/testing/run_citation_deeplink_browser_e2e.py
Env:  RAG_E2E_BASE_URL (default http://localhost:3123)
      RAG_E2E_LOGIN_EMAIL (default demo@example.com)
      DEMO_USER_PASSWORD (required)

Exit code 0 on PASS, 1 on any failed assertion. Mirrors the agent-browser
invocation style of run_rag_agent_browser_e2e.py.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

DEFAULT_QUERY = "What is the minimum concrete cover for reinforced concrete?"


def _ab(args: list[str], timeout: int = 45) -> tuple[bool, str]:
    if shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI is not installed or not in PATH")
    try:
        proc = subprocess.run(
            ["agent-browser", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s: {' '.join(args)}"
    except Exception as exc:  # noqa: BLE001
        return False, f"agent-browser error: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("RAG_E2E_BASE_URL", "http://localhost:3123"))
    ap.add_argument("--email", default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"))
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--response-wait-ms", type=int, default=35000)
    args = ap.parse_args()

    password = os.getenv("DEMO_USER_PASSWORD")
    if not password:
        print("FAIL: DEMO_USER_PASSWORD not set in environment")
        return 1

    base = args.base_url.rstrip("/")
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {msg}")
        if not cond:
            failures.append(msg)

    # 1. Login
    _ab(["open", f"{base}/login"])
    _ab(["wait", 'input[type="email"]'], timeout=20)
    _ab(["fill", 'input[type="email"]', args.email])
    _ab(["fill", 'input[type="password"]', password])
    ok, _ = _ab(["find", "text", "Log in", "click"])
    _ab(["wait", "3000"])
    _, url = _ab(["get", "url"])
    check("/login" not in url, f"login succeeded (url={url})")

    # 2. Ask a question with paged-PDF sources
    _ab(["open", f"{base}/workflow-chat"])
    _ab(["wait", "textarea"], timeout=20)
    _ab(["fill", "textarea", args.query])
    if not _ab(["find", "testid", "send-button", "click"])[0]:
        _ab(["press", "Enter"])
    _ab(["wait", str(args.response_wait_ms), "div.bg-gray-100"], timeout=int(args.response_wait_ms / 1000) + 10)
    _ab(["wait", "4000"])

    # 3. Citations render as buttons with page badges. Use eval/querySelectorAll
    # (DOM truth) rather than `find testid` which is sensitive to below-the-fold
    # visibility for the nested badge span.
    def _count(css: str) -> int:
        _, out = _ab(["eval", f'document.querySelectorAll({css}).length'])
        try:
            return int(re.search(r"\d+", out or "0").group())
        except Exception:
            return 0

    check(_count('"[data-testid^=\\"source-citation\\"]"') >= 1, "source-citation button(s) present")
    check(_count('"[data-testid^=\\"source-page-badge\\"]"') >= 1, "page badge(s) present")

    _, dp = _ab(["eval", 'document.querySelector("[data-testid=\\"source-citation-0\\"]")?.getAttribute("data-page")'])
    check(bool(re.search(r"\d+", dp or "")), f"citation-0 carries data-page ({dp!r})")

    # 4. Click → deep-link URL with page + chunk
    _ab(["find", "testid", "source-citation-0", "click"])
    _ab(["wait", "3500"])
    _, url2 = _ab(["get", "url"])
    m = re.search(r"/documents/[^?]+\?(?=.*page=(\d+))(?=.*chunk=(\d+))", url2 or "")
    check(bool(m), f"deep-link URL has page+chunk params (url={url2})")

    # 5. Document page reflects the cited page + highlights the cited chunk
    _ab(["wait", "2500"])
    _, page_val = _ab(["get", "value", "input[data-testid=pdf-page-input]"])
    expected_page = m.group(1) if m else None
    check(
        expected_page is not None and (page_val or "").strip() == expected_page,
        f"PDF jumped to cited page (input={page_val!r}, expected={expected_page})",
    )
    _, tgt_count = _ab(["get", "count", "[data-target=\"true\"]"])
    try:
        n_tgt = int(re.search(r"\d+", tgt_count or "0").group())
    except Exception:
        n_tgt = 0
    check(n_tgt >= 1, f"cited chunk highlighted (data-target count={tgt_count})")

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} assertion(s) failed)")
        return 1
    print("RESULT: PASS — citation deep-linking works end-to-end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
