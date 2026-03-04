#!/usr/bin/env python3
"""Run browser-based RAG E2E conversations from a CSV question bank."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = PROJECT_ROOT / "docs" / "testing" / "rag_question_bank_180.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "logs" / "rag_agent_browser_e2e_report.json"

TEXTAREA_SELECTOR = 'textarea[placeholder="Enter your question or query..."]'
SEND_BUTTON_SELECTOR = 'button:has-text("send")'
USER_BUBBLE_SELECTOR = "div.bg-blue-600 .whitespace-pre-wrap"
AI_BUBBLE_SELECTOR = "div.bg-gray-100 .whitespace-pre-wrap"
SOURCE_SECTION_SELECTOR = 'text="Reference sources:"'
SUGGESTION_SECTION_SELECTOR = 'text="Suggested follow-up questions:"'
LOGIN_EMAIL_SELECTOR = 'input[type="email"]'
LOGIN_PASSWORD_SELECTOR = 'input[type="password"]'
LOGIN_BUTTON_SELECTOR = 'button:has-text("Log in")'


@dataclass(frozen=True)
class QuestionRow:
    question_id: str
    document_filename: str
    conversation_group: str
    turn_index: int
    question_type: str
    question_text: str


def _check_http(url: str, timeout: int = 8) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.getcode() < 400
    except Exception:
        return False


def _extract_last_int(text: str) -> int:
    values = re.findall(r"-?\d+", text or "")
    if not values:
        return 0
    return int(values[-1])


def _run_agent_browser(args: list[str], timeout: int = 45) -> tuple[bool, str]:
    timeout_cmd = shutil.which("timeout")
    command = ["agent-browser", *args]
    if timeout_cmd:
        command = [timeout_cmd, str(max(1, int(timeout))), *command]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(5, int(timeout) + 10),
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 124 and timeout_cmd:
            return False, f"agent-browser timeout after {timeout}s: {' '.join(args)}"
        return proc.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"agent-browser timeout after {timeout}s: {' '.join(args)}"
    except Exception as exc:
        return False, f"agent-browser execution error: {exc}"


def _run_agent_browser_eval(js: str, timeout: int = 30) -> tuple[bool, str]:
    encoded = base64.b64encode(js.encode("utf-8")).decode("ascii")
    return _run_agent_browser(["eval", "-b", encoded], timeout=timeout)


def _get_count(selector: str) -> int:
    ok, output = _run_agent_browser(["get", "count", selector], timeout=20)
    if not ok:
        return -1
    return _extract_last_int(output)


def _is_visible(selector: str) -> bool:
    ok, output = _run_agent_browser(["is", "visible", selector], timeout=20)
    if not ok:
        return False
    lowered = output.lower()
    return "true" in lowered or lowered.strip().endswith("1")


def _wait_for_new_ai_message(before_ai_count: int, max_wait_ms: int) -> tuple[bool, int]:
    """Wait until a new AI bubble appears (best effort)."""
    wait_ms = max(1000, int(max_wait_ms))
    deadline = time.time() + (wait_ms / 1000.0)
    last_count = before_ai_count

    while time.time() < deadline:
        current = _get_count(AI_BUBBLE_SELECTOR)
        if current >= 0:
            last_count = current
        if before_ai_count >= 0 and current > before_ai_count:
            return True, current
        _run_agent_browser(["wait", "1200"], timeout=8)

    # If baseline is unknown, treat any known count as best-effort completion.
    if before_ai_count < 0 and last_count >= 0:
        return True, last_count
    return False, last_count


def _prepare_capture_layout() -> tuple[bool, str]:
    """Adjust page layout before screenshot so each turn shows complete Q/A."""
    js = """
(() => {
  try {
    const allDivs = Array.from(document.querySelectorAll('div'));
    const chatContainer = allDivs.find((el) => {
      const cls = typeof el.className === 'string' ? el.className : '';
      return cls.includes('overflow-y-auto') && cls.includes('h-[500px]');
    });
    if (!chatContainer) return 'chat_container_not_found';

    // Expand chat panel so long answers are not clipped by internal scrolling.
    chatContainer.style.height = 'auto';
    chatContainer.style.maxHeight = 'none';
    chatContainer.style.overflowY = 'visible';
    chatContainer.style.overflow = 'visible';

    // Hide right sidebar so the chat column has more width and less line wrapping.
    const sidebar = allDivs.find((el) => {
      const cls = typeof el.className === 'string' ? el.className : '';
      return cls.includes('space-y-6');
    });
    if (sidebar) sidebar.style.display = 'none';

    // Keep only latest Q/A pair visible for clearer per-turn capture.
    const userBubbles = Array.from(document.querySelectorAll('div.bg-blue-600'));
    const aiBubbles = Array.from(document.querySelectorAll('div.bg-gray-100'));
    const lastUser = userBubbles.length ? userBubbles[userBubbles.length - 1] : null;
    const lastAi = aiBubbles.length ? aiBubbles[aiBubbles.length - 1] : null;
    const lastUserWrap = lastUser ? lastUser.closest('div.mb-6') : null;
    const lastAiWrap = lastAi ? lastAi.closest('div.mb-6') : null;

    const messageBlocks = Array.from(chatContainer.children).filter((el) => {
      return el && el.matches && el.matches('div.mb-6');
    });
    for (const block of messageBlocks) {
      if (block !== lastUserWrap && block !== lastAiWrap) {
        block.style.display = 'none';
      } else {
        block.style.display = 'block';
      }
    }

    const rects = [lastUserWrap, lastAiWrap]
      .filter(Boolean)
      .map((el) => el.getBoundingClientRect());
    if (rects.length > 0) {
      const top = Math.min(...rects.map((r) => r.top));
      const bottom = Math.max(...rects.map((r) => r.bottom));
      const pairHeight = Math.max(1, bottom - top);
      const availableHeight = Math.max(300, window.innerHeight - 180);
      let zoom = Math.min(1, availableHeight / pairHeight);
      zoom = Math.max(0.55, zoom);
      document.body.style.zoom = zoom.toFixed(2);
      window.scrollTo({
        top: Math.max(0, window.scrollY + top - 80),
        left: 0,
        behavior: 'instant',
      });
      return `ok:zoom=${zoom.toFixed(2)}:pairHeight=${Math.round(pairHeight)}`;
    }

    document.body.style.zoom = '0.80';
    return 'ok:no_pair_rect';
  } catch (err) {
    return `error:${String(err)}`;
  }
})()
"""
    return _run_agent_browser_eval(js, timeout=20)


def _open_chat(chat_url: str) -> tuple[bool, str, str]:
    open_ok, open_output = _run_agent_browser(["open", chat_url], timeout=45)
    wait_ok, wait_output = _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
    if not wait_ok:
        # Some pages keep background polling active, making networkidle unreliable.
        fallback_ok, fallback_output = _run_agent_browser(["wait", "1200"], timeout=10)
        combined = f"{wait_output} | fallback_wait={fallback_output}"
        return open_ok and fallback_ok, open_output, combined
    return open_ok and wait_ok, open_output, wait_output


def _ensure_chat_ready(
    *,
    chat_url: str,
    login_email: str,
    login_password: str,
) -> None:
    ready, open_output, wait_output = _open_chat(chat_url)
    if not ready:
        raise RuntimeError(
            f"failed_to_open_chat: open={open_output!r}, wait={wait_output!r}"
        )

    if _get_count(TEXTAREA_SELECTOR) > 0 and _get_count(SEND_BUTTON_SELECTOR) > 0:
        return

    if login_email and login_password and _get_count(LOGIN_EMAIL_SELECTOR) > 0:
        _run_agent_browser(["fill", LOGIN_EMAIL_SELECTOR, login_email], timeout=20)
        _run_agent_browser(["fill", LOGIN_PASSWORD_SELECTOR, login_password], timeout=20)
        _run_agent_browser(["click", LOGIN_BUTTON_SELECTOR], timeout=20)
        _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
        _run_agent_browser(["wait", "1200"], timeout=10)
        ready_after_login, _, _ = _open_chat(chat_url)
        if (
            ready_after_login
            and _get_count(TEXTAREA_SELECTOR) > 0
            and _get_count(SEND_BUTTON_SELECTOR) > 0
        ):
            return

    raise RuntimeError(
        "chat_input_unavailable: workflow-chat not ready; login may be required."
    )


def _load_questions(csv_path: Path, max_questions: int) -> list[QuestionRow]:
    rows: list[QuestionRow] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                turn_index = int(row.get("turn_index") or "0")
            except Exception:
                continue
            rows.append(
                QuestionRow(
                    question_id=str(row.get("question_id") or "").strip(),
                    document_filename=str(row.get("document_filename") or "").strip(),
                    conversation_group=str(row.get("conversation_group") or "").strip(),
                    turn_index=turn_index,
                    question_type=str(row.get("question_type") or "").strip(),
                    question_text=str(row.get("question_text") or "").strip(),
                )
            )
    rows.sort(
        key=lambda item: (
            item.document_filename,
            item.conversation_group,
            item.turn_index,
            item.question_id,
        )
    )
    return rows[:max_questions]


def _group_questions(rows: list[QuestionRow]) -> dict[str, list[QuestionRow]]:
    grouped: dict[str, list[QuestionRow]] = defaultdict(list)
    for row in rows:
        grouped[row.conversation_group].append(row)
    for key in grouped:
        grouped[key].sort(key=lambda item: item.turn_index)
    return dict(grouped)


def run_e2e(
    *,
    frontend_url: str,
    csv_path: Path,
    output_path: Path,
    max_questions: int,
    wait_after_send_ms: int,
    login_email: str,
    login_password: str,
) -> dict[str, Any]:
    if shutil.which("agent-browser") is None:
        raise RuntimeError("agent-browser CLI is not installed or not in PATH")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV question bank not found: {csv_path}")

    chat_url = frontend_url.rstrip("/") + "/workflow-chat"
    if not _check_http(frontend_url):
        raise RuntimeError(f"Frontend not reachable: {frontend_url}")
    _ensure_chat_ready(
        chat_url=chat_url,
        login_email=login_email,
        login_password=login_password,
    )

    rows = _load_questions(csv_path, max_questions=max_questions)
    grouped = _group_questions(rows)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    screenshot_dir = output_path.parent / f"rag_agent_browser_screenshots_{timestamp}"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    all_turns: list[dict[str, Any]] = []
    started = time.perf_counter()

    for group_index, (group_name, turns) in enumerate(grouped.items(), start=1):
        try:
            _ensure_chat_ready(
                chat_url=chat_url,
                login_email=login_email,
                login_password=login_password,
            )
        except Exception as exc:
            all_turns.append(
                {
                    "conversation_group": group_name,
                    "group_index": group_index,
                    "turn_index": 0,
                    "question_id": "",
                    "question_type": "group_init",
                    "question_text": "",
                    "success": False,
                    "error": "failed_to_open_chat",
                    "open_output": "",
                    "wait_output": str(exc),
                }
            )
            continue

        for turn in turns:
            before_user_count = _get_count(USER_BUBBLE_SELECTOR)
            before_ai_count = _get_count(AI_BUBBLE_SELECTOR)
            turn_started = time.perf_counter()
            response_observed = False

            ok_fill = False
            ok_click = False
            out_fill = ""
            out_click = ""
            # Retry when the composer is transiently disabled while the previous turn is still rendering.
            for _ in range(4):
                ok_fill, out_fill = _run_agent_browser(
                    ["fill", TEXTAREA_SELECTOR, turn.question_text],
                    timeout=35,
                )
                ok_click, out_click = _run_agent_browser(
                    ["click", SEND_BUTTON_SELECTOR], timeout=25
                )
                if ok_fill and ok_click:
                    break
                _run_agent_browser(["wait", "3000"], timeout=10)

            # Wait until this turn receives a new AI message so screenshot contains full Q/A.
            if ok_fill and ok_click:
                response_observed, _ = _wait_for_new_ai_message(
                    before_ai_count=before_ai_count,
                    max_wait_ms=max(3000, int(wait_after_send_ms)),
                )
                # Small settle delay to ensure the bubble is fully rendered before screenshot.
                _run_agent_browser(["wait", "1500"], timeout=10)
                _run_agent_browser(["wait", "--load", "networkidle"], timeout=45)
            else:
                _run_agent_browser(["wait", "2000"], timeout=10)

            after_user_count = _get_count(USER_BUBBLE_SELECTOR)
            after_ai_count = _get_count(AI_BUBBLE_SELECTOR)
            has_source_section = _is_visible(SOURCE_SECTION_SELECTOR)
            has_suggestion_section = _is_visible(SUGGESTION_SECTION_SELECTOR)

            elapsed_ms = (time.perf_counter() - turn_started) * 1000
            screenshot_path = screenshot_dir / f"{group_name}_t{turn.turn_index}_{turn.question_id}.png"
            capture_layout_ok, capture_layout_output = _prepare_capture_layout()
            _run_agent_browser(["wait", "1000"], timeout=8)
            ok_shot, out_shot = _run_agent_browser(
                ["screenshot", str(screenshot_path)],
                timeout=45,
            )

            success = bool(
                ok_fill
                and ok_click
                and (
                    response_observed
                    if before_ai_count >= 0
                    else after_ai_count >= 0
                )
            )
            all_turns.append(
                {
                    "conversation_group": group_name,
                    "group_index": group_index,
                    "question_id": turn.question_id,
                    "document_filename": turn.document_filename,
                    "turn_index": turn.turn_index,
                    "question_type": turn.question_type,
                    "question_text": turn.question_text,
                    "success": success,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "before_user_count": before_user_count,
                    "after_user_count": after_user_count,
                    "before_ai_count": before_ai_count,
                    "after_ai_count": after_ai_count,
                    "has_source_section": has_source_section,
                    "has_suggestion_section": has_suggestion_section,
                    "response_observed": response_observed,
                    "capture_layout_ok": capture_layout_ok,
                    "capture_layout_output": capture_layout_output[:240],
                    "screenshot_path": str(screenshot_path) if ok_shot else "",
                    "error": "" if success else "send_or_render_failed",
                    "fill_output": out_fill[:300],
                    "click_output": out_click[:300],
                    "screenshot_output": out_shot[:240],
                }
            )

    duration_ms = (time.perf_counter() - started) * 1000
    success_count = sum(1 for item in all_turns if item.get("turn_index", 0) > 0 and item.get("success"))
    turn_rows = [item for item in all_turns if item.get("turn_index", 0) > 0]

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frontend_url": frontend_url,
        "chat_url": chat_url,
        "csv_path": str(csv_path),
        "output_path": str(output_path),
        "screenshot_dir": str(screenshot_dir),
        "max_questions": max_questions,
        "total_groups": len(grouped),
        "total_turns": len(turn_rows),
        "success_turns": success_count,
        "success_rate": round(success_count / len(turn_rows), 4) if turn_rows else 0.0,
        "avg_elapsed_ms": round(
            sum(float(item.get("elapsed_ms") or 0.0) for item in turn_rows) / len(turn_rows), 2
        )
        if turn_rows
        else 0.0,
        "elapsed_ms": round(duration_ms, 2),
        "turns": all_turns,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG browser E2E from CSV questions.")
    parser.add_argument("--frontend-url", default="http://localhost:3000")
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-questions", type=int, default=180)
    parser.add_argument("--wait-after-send-ms", type=int, default=1200)
    parser.add_argument(
        "--login-email",
        default=os.getenv("RAG_E2E_LOGIN_EMAIL", "demo@example.com"),
    )
    parser.add_argument(
        "--login-password",
        default=os.getenv("RAG_E2E_LOGIN_PASSWORD", "demo123"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_e2e(
        frontend_url=str(args.frontend_url),
        csv_path=Path(args.csv),
        output_path=Path(args.output),
        max_questions=max(1, int(args.max_questions)),
        wait_after_send_ms=max(0, int(args.wait_after_send_ms)),
        login_email=str(args.login_email),
        login_password=str(args.login_password),
    )
    print("RAG agent-browser E2E run complete.")
    print(f"report={args.output}")
    print(f"total_turns={report['total_turns']}")
    print(f"success_rate={report['success_rate']}")
    return 0 if report["success_rate"] >= 0.7 else 2


if __name__ == "__main__":
    raise SystemExit(main())
