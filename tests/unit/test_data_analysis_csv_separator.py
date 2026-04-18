"""Regression tests: CSV separator sniffing.

Origin: 2026-04-18 — uploading UCI winequality-red.csv (';' delimited)
produced a metadata extract with one giant string column. The
deterministic planner had no numeric columns to plot, returned an empty
chart list, and the UI showed "Analysis Error".

Fix: pass ``sep=None, engine='python'`` to ``pd.read_csv`` so pandas
invokes ``csv.Sniffer`` on the file sample. This suite locks the
behaviour so any regression (someone reverts the sep kwarg) fails fast.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestCsvSeparatorSniff:
    """_extract_dataset_info must detect ';' and tab as delimiters."""

    def _build_agent(self):
        with (
            patch(
                "backend.services.data_analysis.data_analysis_agent.settings"
            ) as mock_settings,
            patch(
                "backend.services.data_analysis.data_analysis_agent.LLMClientFactory"
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent."
                "get_code_execution_manager",
                return_value=None,
            ),
            patch(
                "backend.services.data_analysis.data_analysis_agent."
                "code_executor",
                None,
            ),
        ):
            mock_settings.resolved_local_backend = "mock"
            from backend.services.data_analysis.data_analysis_agent import (
                DataAnalysisAgent,
            )

            agent = DataAnalysisAgent.__new__(DataAnalysisAgent)
            agent.llm_client = MagicMock()
            agent.code_execution_manager = None
            agent.code_executor = None
            return agent

    def test_semicolon_csv_parses_into_multiple_columns(self, tmp_path):
        """UCI wine-quality shape: ';' delimiter, quoted headers."""
        csv_path = tmp_path / "winequality.csv"
        csv_path.write_text(
            'fixed acidity;"volatile acidity";"citric acid";quality\n'
            "7.4;0.70;0.00;5\n"
            "7.8;0.88;0.00;5\n"
            "7.8;0.76;0.04;5\n",
            encoding="utf-8",
        )

        agent = self._build_agent()
        result = agent._extract_dataset_info(str(csv_path))

        assert "error" not in result, result.get("error")
        assert result["columns"] == 4, (
            f"Expected 4 columns from ';'-delimited CSV, got {result['columns']} — "
            "csv.Sniffer probably failed"
        )
        assert result["rows"] == 3

        numeric = [
            c for c in result["columns_info"] if c.get("role") == "numeric"
        ]
        assert len(numeric) >= 3, (
            f"Expected >=3 numeric columns, got {len(numeric)} — "
            "separator was not sniffed correctly"
        )

    def test_tab_csv_parses_into_multiple_columns(self, tmp_path):
        """Tab-delimited TSV masquerading as .csv."""
        csv_path = tmp_path / "tsv.csv"
        csv_path.write_text(
            "name\tscore\tcount\n"
            "alpha\t1.5\t10\n"
            "beta\t2.7\t20\n",
            encoding="utf-8",
        )

        agent = self._build_agent()
        result = agent._extract_dataset_info(str(csv_path))

        assert "error" not in result
        assert result["columns"] == 3
        assert result["rows"] == 2

    def test_comma_csv_still_works(self, tmp_path):
        """Regular ',' CSV must not break when the sniffer is in the loop."""
        csv_path = tmp_path / "plain.csv"
        csv_path.write_text(
            "id,score,label\n"
            "1,10.2,good\n"
            "2,7.5,bad\n",
            encoding="utf-8",
        )

        agent = self._build_agent()
        result = agent._extract_dataset_info(str(csv_path))

        assert "error" not in result
        assert result["columns"] == 3
        assert result["rows"] == 2


@pytest.mark.unit
class TestChartExecutorLoaderSniff:
    """The sandbox loader code must also use sep=None for csv files.

    Without this, even if metadata extraction sniffs correctly, the
    sandbox would read a ';'-delimited file with default ',' and every
    chart template would fail on "column not found".
    """

    def test_csv_loader_includes_sep_sniff(self):
        from backend.services.data_analysis.chart_executor import _loader_block

        code = _loader_block("csv")

        assert "sep=None" in code, (
            "csv loader must pass sep=None so csv.Sniffer runs in the sandbox"
        )
        assert "engine='python'" in code, (
            "csv loader must use engine='python' for sep=None to work"
        )

    def test_non_csv_loader_unaffected(self):
        from backend.services.data_analysis.chart_executor import _loader_block

        assert "read_excel" in _loader_block("xlsx")
        assert "read_json" in _loader_block("json")
