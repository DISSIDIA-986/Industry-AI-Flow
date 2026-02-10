"""Prompt render testing page."""

from __future__ import annotations

import json
from typing import Any, Dict

import streamlit as st

from api_client import PromptApiClient, PromptApiError


def _safe_json(text: str) -> Dict[str, Any]:
    if not text.strip():
        return {}
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object")
    return value


def render(client: PromptApiClient) -> None:
    st.subheader("Prompt Test")
    payload = client.list_prompts(page=1, size=100)
    prompts = payload.get("data", [])
    if not prompts:
        st.info("No prompt available.")
        return

    prompt_id = st.selectbox(
        "prompt",
        options=[item.get("id") for item in prompts],
        format_func=lambda pid: next(
            (
                f"{item.get('name')} ({item.get('category')}/{item.get('version')})"
                for item in prompts
                if item.get("id") == pid
            ),
            pid,
        ),
    )
    default_variables = {"query": "What is Alberta OHS requirement for scaffolding over 3m?"}
    variables_text = st.text_area(
        "variables JSON",
        value=json.dumps(default_variables, ensure_ascii=False, indent=2),
        height=140,
    )
    context_text = st.text_area(
        "context JSON (optional)",
        value=json.dumps({"tenant_id": "demo"}, ensure_ascii=False, indent=2),
        height=100,
    )

    if not st.button("run test", use_container_width=True):
        return

    try:
        variables = _safe_json(variables_text)
        context = _safe_json(context_text) if context_text.strip() else None
        result = client.test_prompt(prompt_id, variables=variables, context=context)
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"Invalid JSON: {exc}")
        return
    except PromptApiError as exc:
        st.error(str(exc))
        return

    st.success("render succeeded")
    st.text_area(
        "rendered content",
        value=result.get("rendered_content", ""),
        height=260,
    )
    st.json(result)
