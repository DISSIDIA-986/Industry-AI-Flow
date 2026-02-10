"""Prompt list page."""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from api_client import PromptApiClient, PromptApiError


def _prompt_table_rows(prompts: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for item in prompts:
        usage_count = int(item.get("usage_count") or 0)
        success_count = int(item.get("success_count") or 0)
        rows.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "category": item.get("category"),
                "version": item.get("version"),
                "priority": item.get("priority"),
                "usage_count": usage_count,
                "success_rate": round(success_count / usage_count, 4) if usage_count > 0 else 0.0,
                "performance_score": float(item.get("performance_score") or 0.0),
                "updated_at": item.get("updated_at"),
            }
        )
    return rows


def render(client: PromptApiClient) -> None:
    st.subheader("Prompt List")
    col1, col2, col3 = st.columns(3)
    with col1:
        categories = ["all"] + client.list_categories()
        category = st.selectbox("category", categories)
    with col2:
        page = st.number_input("page", min_value=1, value=1, step=1)
    with col3:
        size = st.number_input("size", min_value=1, max_value=100, value=20, step=1)

    try:
        payload = client.list_prompts(
            page=int(page),
            size=int(size),
            category=None if category == "all" else category,
        )
    except PromptApiError as exc:
        st.error(str(exc))
        return

    data = payload.get("data", [])
    pagination = payload.get("pagination", {})
    st.caption(f"total={pagination.get('total', 0)} pages={pagination.get('pages', 0)}")

    table_rows = _prompt_table_rows(data)
    if not table_rows:
        st.info("No prompt records found.")
        return

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    selected = st.selectbox(
        "detail",
        options=[row["id"] for row in table_rows],
        format_func=lambda x: next((f"{r['name']} ({r['version']})" for r in table_rows if r["id"] == x), x),
    )
    if selected:
        detail = next((item for item in data if item.get("id") == selected), {})
        st.json(detail)
