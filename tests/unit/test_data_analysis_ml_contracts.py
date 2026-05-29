"""Contract tests for advanced-ML governance in the Dynamic Data Analysis path.

Derived from the 2026-05-29 adversarial review
(docs/data_analysis_ml_adversarial_review.md). These encode the *desired*
security/governance contracts. Gaps that the current implementation does not yet
satisfy are marked ``xfail`` (non-strict) with the review's priority tag, so the
suite stays green while the gap is tracked. Drop the marker when a fix lands and
the test flips to xpass.

Offline only — no backend, no sandbox. The live behavioural contracts
(GridSearch guard, RL refusal status, xgboost disclosure, seed determinism, SSE
recovery) live in ``scripts/testing/run_data_analysis_ml_e2e.py`` because they
need the running pipeline.
"""

import pytest

from backend.services.code_executor.validator import validate_code

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# P1 — validator is name-based and trivially bypassed.
# The validator docstring claims filesystem/network prevention; these snippets
# show allowed-library gadgets that defeat that claim. Desired = BLOCK.
# ---------------------------------------------------------------------------
class TestValidatorMlGadgets:
    # (id, code, why)
    GADGETS = [
        (
            "url_read_csv",
            "import pandas as pd\ndf = pd.read_csv('https://evil.example/x.csv')\n",
            "SSRF / data exfiltration via pandas URL reader",
        ),
        (
            "abs_path_read_csv",
            "import pandas as pd\ndf = pd.read_csv('/etc/hosts', sep='\\t')\n",
            "arbitrary local file read",
        ),
        (
            "np_fromfile",
            "import numpy as np\na = np.fromfile('/etc/passwd')\n",
            "arbitrary local file read (np.fromfile not blocked)",
        ),
        (
            "aliased_np_load",
            "from numpy import load as L\nx = L('/tmp/x.npy')\n",
            "aliasing defeats the name-based np.load block",
        ),
        (
            "sklearn_fetch",
            "from sklearn.datasets import fetch_openml\nd = fetch_openml('mnist_784')\n",
            "outbound network via sklearn dataset fetcher",
        ),
        (
            "scipy_loadmat",
            "from scipy.io import loadmat\nm = loadmat('/tmp/x.mat')\n",
            "deserialization gadget",
        ),
        (
            "savefig_abs_path",
            "import matplotlib.pyplot as plt\nplt.plot([1, 2])\nplt.savefig('/tmp/evil.png')\n",
            "arbitrary filesystem write outside /workspace",
        ),
    ]

    @pytest.mark.parametrize("snippet_id,code,why", GADGETS, ids=[g[0] for g in GADGETS])
    def test_gadget_is_blocked(self, snippet_id, code, why):
        # Closed 2026-05-29 by CodeValidator._validate_io_safety (alias-resistant
        # I/O safety pass): workspace-local paths only, no URLs, no network
        # fetchers / deserialization gadgets.
        result = validate_code(code, strict_mode=True)
        assert result.is_valid is False, f"{snippet_id}: {why} — should be blocked"

    def test_direct_np_load_is_blocked(self):
        # Regression guard: the name-based block DOES catch the direct form.
        result = validate_code("import numpy as np\nx = np.load('/tmp/x.npy')\n", strict_mode=True)
        assert result.is_valid is False

    def test_pickle_import_is_blocked(self):
        result = validate_code("import pickle\n", strict_mode=True)
        assert result.is_valid is False

    def test_workspace_read_is_allowed(self):
        # Baseline: the intended happy path must stay valid.
        code = "import pandas as pd\ndf = pd.read_csv('/workspace/x.csv')\nprint(df.mean())\n"
        assert validate_code(code, strict_mode=True).is_valid is True


class TestValidatorAllowsLegitMl:
    """Regression guard: I/O hardening must NOT block real generated-code shapes."""

    LEGIT = [
        ("workspace_read", "import pandas as pd\ndf = pd.read_csv('/workspace/x.csv', sep=',')\n"),
        # Generated code passes the path as a variable (header-sniff loop) — must pass.
        ("var_path_read", "import pandas as pd\n_p = '/workspace/tips.csv'\ndf = pd.read_csv(_p, sep=None)\n"),
        ("savefig_workspace", "import matplotlib.pyplot as plt\nplt.savefig('/workspace/analysis_chart.png')\n"),
        ("savefig_relative", "import matplotlib.pyplot as plt\nplt.savefig('analysis_chart.png')\n"),
        ("matplotlib_use_agg", "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"),
        ("sklearn_local_loader", "from sklearn.datasets import load_iris\nd = load_iris()\n"),
        ("sklearn_estimator", "from sklearn.ensemble import RandomForestClassifier\nm = RandomForestClassifier(random_state=42)\n"),
        ("to_csv_workspace", "import pandas as pd\ndf = pd.DataFrame({'a': [1]})\ndf.to_csv('/workspace/out.csv')\n"),
    ]

    @pytest.mark.parametrize("snippet_id,code", LEGIT, ids=[s[0] for s in LEGIT])
    def test_legit_ml_code_allowed(self, snippet_id, code):
        result = validate_code(code, strict_mode=True)
        assert result.is_valid is True, f"{snippet_id} wrongly blocked: {result.error}"


# ---------------------------------------------------------------------------
# P1 — whitelist / runtime drift: xgboost & lightgbm are whitelisted (so they
# pass validation) but are NOT bootstrapped into the E2B sandbox, so they fail
# at runtime and get silently repaired to sklearn. Either remove them from the
# whitelist (fail fast) or bootstrap them. This test documents the drift.
# ---------------------------------------------------------------------------
class TestLibraryAvailabilityContract:
    def test_xgboost_lightgbm_fail_fast(self):
        # Closed 2026-05-29: xgboost/lightgbm removed from the whitelist (not
        # installed in E2B). They now fail fast at validation instead of being
        # silently rewritten to sklearn at runtime.
        for lib in ("xgboost", "lightgbm"):
            assert validate_code(f"import {lib}\n", strict_mode=True).is_valid is False, (
                f"{lib} should be rejected (not installed in sandbox)"
            )

    def test_gradient_boosting_capability_still_available(self):
        # The gradient-boosting capability is preserved via sklearn.
        code = (
            "from sklearn.ensemble import GradientBoostingClassifier\n"
            "m = GradientBoostingClassifier(random_state=42)\n"
        )
        assert validate_code(code, strict_mode=True).is_valid is True

    def test_whitelist_matches_sandbox_runtime(self):
        from backend.services.code_executor.validator import CodeValidator
        from backend.services.data_analysis.agentic_loop import BOOTSTRAP_PACKAGES

        whitelisted = set(CodeValidator.WHITELISTED_IMPORTS)
        # Packages assumed present in the E2B base image (sklearn/scipy/etc.) plus
        # whatever we bootstrap. Anything ML-heavy that is whitelisted but neither
        # in the base nor bootstrapped is a latent runtime trap.
        e2b_base = {
            "pandas", "numpy", "scipy", "sklearn", "matplotlib", "seaborn",
            "plotly", "math", "statistics", "datetime", "json", "csv", "re",
            "collections", "itertools", "warnings", "random",
        }
        runtime_available = e2b_base | set(BOOTSTRAP_PACKAGES)
        trap = {
            lib for lib in ("xgboost", "lightgbm", "catboost")
            if lib in whitelisted and lib not in runtime_available
        }
        assert not trap, f"whitelisted but unavailable at runtime: {sorted(trap)}"
