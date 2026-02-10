"""Streamlit Prompt Admin entrypoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api_client import PromptApiClient
from pages import experiments, metrics, prompt_editor, prompt_list, prompt_test


def _build_client() -> PromptApiClient:
    base_url = st.sidebar.text_input(
        "API Base URL",
        value=os.getenv("PROMPT_API_BASE_URL", "http://localhost:8000"),
    ).strip()
    api_key = st.sidebar.text_input(
        "API Key (optional)",
        value=os.getenv("PROMPT_API_KEY", ""),
        type="password",
    ).strip()
    return PromptApiClient(base_url=base_url, api_key=api_key or None)


def main() -> None:
    st.set_page_config(page_title="Prompt Admin", layout="wide")
    st.title("Prompt Admin")
    st.caption("Real API management for prompts, experiments, and metrics.")

    client = _build_client()
    page = st.sidebar.radio(
        "Page",
        options=[
            "Prompt List",
            "Prompt Editor",
            "Prompt Test",
            "Experiments",
            "Metrics",
        ],
    )

    if page == "Prompt List":
        prompt_list.render(client)
    elif page == "Prompt Editor":
        prompt_editor.render(client)
    elif page == "Prompt Test":
        prompt_test.render(client)
    elif page == "Experiments":
        experiments.render(client)
    elif page == "Metrics":
        metrics.render(client)


if __name__ == "__main__":
    main()
