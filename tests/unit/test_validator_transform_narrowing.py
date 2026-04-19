"""Regression for validator `.transform()` narrowing.

Live demo 2026-04-19 found: blocking all `.transform()` calls produced
false positives on sklearn's core API (`StandardScaler().transform`,
`LabelEncoder().transform`, `Pipeline.transform`). The pandas
footgun we actually want to block is `df.groupby(...).transform(...)`,
which accepts arbitrary callables — same risk profile as `.apply()`.

These tests pin down the narrowed behavior:
- groupby().transform() — BLOCKED (pandas footgun preserved)
- scaler.transform() — ALLOWED (sklearn preprocessing)
- LabelEncoder().transform() — ALLOWED
- Pipeline.transform() — ALLOWED
- ColumnTransformer.transform() — ALLOWED
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


def test_groupby_transform_chained_via_column_still_blocked():
    code = (
        "import pandas as pd\n"
        "df = pd.read_csv('/workspace/x.csv')\n"
        "result = df.groupby(['a', 'b']).transform('mean')\n"
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
