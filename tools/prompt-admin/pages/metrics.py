"""Metrics summary page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import PromptApiClient, PromptApiError


def render(client: PromptApiClient) -> None:
    st.subheader("Prompt Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.number_input("window days", min_value=1, max_value=365, value=14, step=1)
    with col2:
        categories = ["all"] + client.list_categories()
        category = st.selectbox("category", categories)
    with col3:
        top_limit = st.number_input("top prompts", min_value=1, max_value=50, value=10, step=1)

    try:
        summary = client.get_metrics_summary(
            days=int(days),
            category=None if category == "all" else category,
            top_limit=int(top_limit),
        )
    except PromptApiError as exc:
        st.error(str(exc))
        return

    totals = summary.get("totals", {})
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("usage logs", totals.get("usage_logs", 0))
    with k2:
        st.metric("success logs", totals.get("success_logs", 0))
    with k3:
        st.metric("success rate", f"{(totals.get('success_rate', 0.0) * 100):.2f}%")
    with k4:
        st.metric("avg exec ms", f"{totals.get('avg_execution_time_ms', 0.0):.2f}")

    st.markdown("### Top Prompts")
    top_rows = summary.get("top_prompts", [])
    if top_rows:
        st.dataframe(pd.DataFrame(top_rows), use_container_width=True)
    else:
        st.info("No top prompt records.")

    st.markdown("### Daily Trend")
    daily_rows = summary.get("daily", [])
    if not daily_rows:
        st.info("No daily trend records.")
        return

    daily_df = pd.DataFrame(daily_rows)
    if "date" in daily_df.columns:
        daily_df["date"] = pd.to_datetime(daily_df["date"])
        daily_df = daily_df.sort_values(by="date")
        daily_df = daily_df.set_index("date")
    st.line_chart(daily_df[["usage_count", "success_count"]], use_container_width=True)
