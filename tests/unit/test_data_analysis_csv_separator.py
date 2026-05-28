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

        # As of fix/csv-sniff-single-column, sep is detected by trying
        # candidates with nrows=0 and picking the first that yields >1
        # column (sep=None+engine='python' over-sniffed single-column
        # CSVs and corrupted column names). The previous header-read
        # approach was reverted because the validator BLOCKS open().
        # Must include the multi-sep try loop with nrows=0:
        assert "nrows=0" in code, (
            "csv loader must use nrows=0 to peek the header without "
            "reading the full file"
        )
        # Must consider all four standard delimiters
        for delim_repr in ("','", "';'", "'\\t'", "'|'"):
            assert delim_repr in code, (
                f"csv loader must include delimiter candidate {delim_repr}"
            )
        # Must fall back to default comma when no delimiter found
        assert "_df is None" in code, (
            "csv loader must fall back to default read_csv when no "
            "multi-column sep is found"
        )
        # MUST NOT use open() — validator blocks it in strict mode
        assert "open(" not in code, (
            "csv loader must not use open() — validator blocks it; "
            "use pandas-only sniff instead"
        )

    def test_non_csv_loader_unaffected(self):
        from backend.services.data_analysis.chart_executor import _loader_block

        assert "read_excel" in _loader_block("xlsx")
        assert "read_json" in _loader_block("json")


class TestSingleColumnCsvRegression:
    """Adversarial-review 2026-05-28 regression: pd.read_csv(sep=None,
    engine='python') over-sniffs single-column CSVs and corrupts the
    column name. E.g. 'value\\n0.24\\n1.35' was being read as
    ['Unnamed: 0', 'alue'] with the second column 100% null, which
    fooled the LLM into reporting 'no data to plot' on perfectly good
    single-column data."""

    def test_detect_sep_returns_none_for_single_column(self):
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("value") is None
        assert _detect_csv_sep_from_header("price\n") is None
        assert _detect_csv_sep_from_header("") is None

    def test_detect_sep_picks_comma(self):
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("a,b,c") == ","

    def test_detect_sep_picks_semicolon(self):
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("a;b;c") == ";"

    def test_detect_sep_picks_tab(self):
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("a\tb\tc") == "\t"

    def test_detect_sep_picks_pipe(self):
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("a|b|c") == "|"

    def test_detect_sep_picks_most_frequent(self):
        # 3 commas vs 1 semicolon — commas win even though header has both
        from backend.services.data_analysis.spike_harness import (
            _detect_csv_sep_from_header,
        )
        assert _detect_csv_sep_from_header("a,b,c,d;extra") == ","

    def test_load_single_column_csv_preserves_header(self, tmp_path):
        from backend.services.data_analysis.spike_harness import load_dataframe
        csv = tmp_path / "single.csv"
        csv.write_text("value\n0.24\n1.35\n0.99\n")
        df = load_dataframe(str(csv))
        assert list(df.columns) == ["value"]
        assert len(df) == 3
        assert df["value"].notna().all()

    def test_load_semicolon_csv_still_works(self, tmp_path):
        from backend.services.data_analysis.spike_harness import load_dataframe
        csv = tmp_path / "semi.csv"
        csv.write_text("a;b;c\n1;2;3\n4;5;6\n")
        df = load_dataframe(str(csv))
        assert list(df.columns) == ["a", "b", "c"]
        assert len(df) == 2

    def test_load_standard_comma_csv(self, tmp_path):
        from backend.services.data_analysis.spike_harness import load_dataframe
        csv = tmp_path / "std.csv"
        csv.write_text("name,age,score\nAlice,30,90\nBob,25,85\n")
        df = load_dataframe(str(csv))
        assert list(df.columns) == ["name", "age", "score"]
        assert len(df) == 2
