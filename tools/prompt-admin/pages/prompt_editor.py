"""Prompt create/update page."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import streamlit as st

from api_client import PromptApiClient, PromptApiError


def _collect_prompt_payload(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    default = default or {}
    name = st.text_input("name", value=default.get("name", ""))
    category = st.text_input("category", value=default.get("category", "rag"))
    subcategory = st.text_input("subcategory", value=default.get("subcategory") or "")
    version = st.text_input("version", value=default.get("version", "1.0.0"))
    priority = st.number_input("priority", min_value=0, max_value=1000, value=int(default.get("priority") or 0))
    content = st.text_area("content", value=default.get("content", ""), height=220)
    tags_str = st.text_input("tags (comma-separated)", value=",".join(default.get("tags") or []))
    created_by = st.text_input("operator", value=default.get("created_by") or "prompt-admin")

    variables_default = default.get("variables") or []
    metadata_default = default.get("metadata") or {}
    variables_text = st.text_area(
        "variables JSON",
        value=json.dumps(variables_default, ensure_ascii=False, indent=2),
        height=140,
    )
    metadata_text = st.text_area(
        "metadata JSON",
        value=json.dumps(metadata_default, ensure_ascii=False, indent=2),
        height=120,
    )

    variables = json.loads(variables_text) if variables_text.strip() else []
    metadata = json.loads(metadata_text) if metadata_text.strip() else {}

    payload: Dict[str, Any] = {
        "name": name.strip(),
        "category": category.strip(),
        "subcategory": subcategory.strip() or None,
        "version": version.strip(),
        "content": content,
        "variables": variables,
        "metadata": metadata,
        "priority": int(priority),
        "tags": [item.strip() for item in tags_str.split(",") if item.strip()],
        "created_by": created_by.strip() or None,
    }
    return payload


def render(client: PromptApiClient) -> None:
    st.subheader("Prompt Editor")
    mode = st.radio("mode", ["create", "update"], horizontal=True)

    selected_prompt: Dict[str, Any] = {}
    selected_prompt_id: Optional[str] = None

    if mode == "update":
        prompts_payload = client.list_prompts(page=1, size=100)
        prompts = prompts_payload.get("data", [])
        if not prompts:
            st.info("No prompt available.")
            return
        selected_prompt_id = st.selectbox(
            "select prompt",
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
        selected_prompt = next((item for item in prompts if item.get("id") == selected_prompt_id), {})

    with st.form("prompt-editor-form"):
        try:
            payload = _collect_prompt_payload(default=selected_prompt if mode == "update" else None)
        except json.JSONDecodeError as exc:
            st.error(f"JSON parse error: {exc}")
            return
        submitted = st.form_submit_button("submit")

    if not submitted:
        return

    try:
        if mode == "create":
            result = client.create_prompt(payload)
            st.success("prompt created")
            st.json(result)
        else:
            assert selected_prompt_id
            update_payload = {
                "content": payload["content"],
                "variables": payload["variables"],
                "metadata": payload["metadata"],
                "priority": payload["priority"],
                "tags": payload["tags"],
                "updated_by": payload["created_by"],
                "create_new_version": True,
            }
            result = client.update_prompt(selected_prompt_id, update_payload)
            st.success("prompt updated")
            st.json(result)
    except PromptApiError as exc:
        st.error(str(exc))
