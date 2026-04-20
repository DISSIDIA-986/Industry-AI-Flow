"""Regression for validator `.transform()` narrowing.

Codex adversarial review 2026-04-19 proved the prior groupby-chain
heuristic had two bypasses:
  1. Alias: `g = df.groupby("a"); g.transform(lambda x: ...)` — allowed
  2. Direct: `df["a"].transform(lambda x: ...)` — allowed

The correct signal is the ACTUAL danger: a Lambda passed as an arg.
sklearn `.transform(X)` passes data only; pandas `.transform("mean")`
is a string aggregator lookup. Only `.transform(lambda ...)` runs
arbitrary Python.

These tests pin down the narrowed behavior:
- .transform(lambda) — BLOCKED (pandas footgun + alias + direct Series)
- .transform("mean") or .transform(np.sqrt) — ALLOWED
- scaler.transform(X), Pipeline.transform(X) — ALLOWED
"""
from __future__ import annotations

import pytest

from backend.services.code_executor.validator import validate_code


# -- Still blocked: pandas groupby().transform() ------------------------


def test_groupby_transform_still_blocked():
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df['demeaned'] = df.groupby('size')['tip'].transform(lambda x: x - x.mean())\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False
    assert "transform" in (result.error or "").lower()


def test_groupby_transform_with_string_agg_now_allowed():
    """String aggregators are safe (no arbitrary code). Narrowed rule
    allows them. Rewrite of the prior block test that used 'mean'."""
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "result = df.groupby(['a', 'b']).transform('mean')\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error


def test_groupby_alias_with_lambda_blocked():
    """Codex adversarial bypass #1: aliased groupby + lambda. Must block."""
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "g = df.groupby('size')\n"
        "df['demeaned'] = g['tip'].transform(lambda x: x - x.mean())\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False
    assert "transform" in (result.error or "").lower()


def test_series_transform_with_lambda_blocked():
    """Codex adversarial bypass #2: direct Series.transform(lambda).
    No groupby anywhere, but still runs arbitrary Python — must block."""
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df['big'] = df['tip'].transform(lambda x: 1 if x > 5 else 0)\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False


def test_transform_with_lambda_kwarg_blocked():
    """Lambda as a keyword argument is the same risk — must also block."""
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df['x'] = df['tip'].transform(func=lambda x: x * 2)\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False


# -- Newly allowed: sklearn .transform() -------------------------------


def test_standardscaler_transform_allowed():
    code = (
        "from sklearn.preprocessing import StandardScaler\n"
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "scaler = StandardScaler()\n"
        "X_scaled = scaler.fit_transform(df[['a', 'b']])\n"
        "X_test = scaler.transform(df[['a', 'b']])\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error


def test_labelencoder_transform_allowed():
    code = (
        "from sklearn.preprocessing import LabelEncoder\n"
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "le = LabelEncoder()\n"
        "df['species_num'] = le.fit_transform(df['species'])\n"
        "y = le.transform(df['species'])\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error


def test_pipeline_transform_allowed():
    code = (
        "from sklearn.pipeline import Pipeline\n"
        "from sklearn.preprocessing import StandardScaler\n"
        "from sklearn.impute import SimpleImputer\n"
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "pipe = Pipeline([('imp', SimpleImputer()), ('scale', StandardScaler())])\n"
        "X_clean = pipe.fit_transform(df[['a', 'b']])\n"
        "X_test = pipe.transform(df[['a', 'b']])\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error


def test_column_transformer_transform_allowed():
    code = (
        "from sklearn.compose import ColumnTransformer\n"
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder\n"
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "ct = ColumnTransformer([\n"
        "    ('num', StandardScaler(), ['a', 'b']),\n"
        "    ('cat', OneHotEncoder(), ['species']),\n"
        "])\n"
        "X = ct.fit_transform(df)\n"
        "X_test = ct.transform(df)\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error


# -- Other blocked methods unchanged -----------------------------------


def test_df_apply_still_blocked():
    """Narrowing transform() does NOT loosen .apply() — separate footgun."""
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df['big'] = df['tip'].apply(lambda x: 1 if x > 5 else 0)\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False


def test_df_agg_still_blocked():
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df.groupby('size').agg({'tip': 'mean'})\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False


def test_series_map_still_blocked():
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "df['sex_num'] = df['sex'].map({'male': 0, 'female': 1})\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is False


# -- Edge: DataFrame.transform() standalone (no groupby) ---------------


def test_dataframe_direct_transform_still_allowed():
    """Without .groupby() in the receiver chain, `.transform()` is now
    allowed. This is a deliberate loosening — a user calling
    `df.transform(sqrt)` outside a groupby is rare and the callable
    risk is lower without the groupby amplification. Keep the test to
    document the decision; flag here if future review wants to retighten.
    """
    code = (
        "import numpy as np\n"
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "result = df[['a', 'b']].transform(np.sqrt)\n"
    )
    result = validate_code(code, strict_mode=True)
    assert result.is_valid is True, result.error
