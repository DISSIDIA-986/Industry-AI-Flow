"""Experiment management page."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict

import pandas as pd
import streamlit as st

from api_client import PromptApiClient, PromptApiError

VALID_STATUSES = ["active", "paused", "completed", "cancelled"]
RAMP_STEPS = [0.1, 0.3, 0.5]


def _load_latest_prompts(client: PromptApiClient) -> list[Dict[str, Any]]:
    payload = client.list_prompts(page=1, size=200, is_latest=True, is_active=True)
    return payload.get("data", [])


def _group_prompt_pairs(prompts: list[Dict[str, Any]]) -> dict[str, list[Dict[str, Any]]]:
    groups: dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for item in prompts:
        key = f"{item.get('category')}::{item.get('name')}"
        groups[key].append(item)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def render(client: PromptApiClient) -> None:
    st.subheader("A/B Experiments")
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("status", ["all"] + VALID_STATUSES)
    with col2:
        category_filter = st.text_input("category filter", value="")

    try:
        experiments_payload = client.list_experiments(
            page=1,
            size=100,
            status=None if status_filter == "all" else status_filter,
            category=category_filter.strip() or None,
        )
    except PromptApiError as exc:
        st.error(str(exc))
        return

    experiments = experiments_payload.get("data", [])
    if experiments:
        st.dataframe(pd.DataFrame(experiments), use_container_width=True)
    else:
        st.info("No experiments yet.")

    st.markdown("---")
    st.markdown("### Create Experiment")
    try:
        prompts = _load_latest_prompts(client)
    except PromptApiError as exc:
        st.error(str(exc))
        return

    grouped = _group_prompt_pairs(prompts)
    if not grouped:
        st.warning("Need at least two active latest prompts with same name/category.")
        return

    group_key = st.selectbox("prompt group", sorted(grouped.keys()))
    candidates = grouped[group_key]
    prompt_options = [item.get("id") for item in candidates]
    label_map = {
        item.get("id"): f"{item.get('name')} v{item.get('version')} ({item.get('id')[:8]})"
        for item in candidates
    }

    a_id = st.selectbox("prompt A", prompt_options, format_func=lambda pid: label_map[pid])
    b_id = st.selectbox("prompt B", prompt_options, format_func=lambda pid: label_map[pid], index=1)
    exp_name = st.text_input("experiment name", value=f"{group_key.replace('::', '_')}_exp")
    exp_desc = st.text_input("description", value="prompt-admin experiment")
    split = st.slider("traffic split (A)", min_value=0.01, max_value=0.99, value=0.1, step=0.01)
    operator = st.text_input("created_by", value="prompt-admin")

    if st.button("create experiment", type="primary"):
        if a_id == b_id:
            st.error("Prompt A and B must be different.")
        else:
            payload = {
                "name": exp_name,
                "description": exp_desc,
                "prompt_a_id": a_id,
                "prompt_b_id": b_id,
                "traffic_split": split,
                "metrics": {"target": "success_rate"},
                "created_by": operator,
            }
            try:
                result = client.create_experiment(payload)
                st.success("experiment created")
                st.json(result)
            except PromptApiError as exc:
                st.error(str(exc))

    if not experiments:
        return

    st.markdown("---")
    st.markdown("### Operate Existing Experiment")
    selected_exp = st.selectbox(
        "experiment",
        options=[item.get("id") for item in experiments],
        format_func=lambda exp_id: next(
            (
                f"{item.get('name')} ({item.get('status')}, split={item.get('traffic_split')})"
                for item in experiments
                if item.get("id") == exp_id
            ),
            exp_id,
        ),
    )

    col_status, col_traffic = st.columns(2)
    with col_status:
        new_status = st.selectbox("target status", VALID_STATUSES)
        if st.button("update status"):
            try:
                result = client.update_experiment_status(selected_exp, new_status)
                st.success("status updated")
                st.json(result)
            except PromptApiError as exc:
                st.error(str(exc))

    with col_traffic:
        chosen_step = st.selectbox("ramp step", options=RAMP_STEPS, format_func=lambda x: f"{int(x * 100)}%")
        if st.button("apply traffic split"):
            try:
                result = client.update_experiment_traffic(selected_exp, float(chosen_step))
                st.success("traffic split updated")
                st.json(result)
            except PromptApiError as exc:
                st.error(str(exc))
