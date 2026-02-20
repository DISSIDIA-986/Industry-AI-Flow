#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT/.venv_capstone}"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
LOCK_FILE="${LOCK_FILE:-$ROOT/requirements/lock/py313-capstone.txt}"
WITH_GATE="${WITH_GATE:-false}"
INSTALL_PADDLE_NIGHTLY="${INSTALL_PADDLE_NIGHTLY:-false}"

# On Apple Silicon, prefer arm64 Homebrew Python when available to avoid
# creating x86_64 (Rosetta) venvs that break torch/sentence-transformers wheels.
if [[ "$PYTHON_BIN" == "python3.13" ]] && [[ "$(uname -m)" == "arm64" ]]; then
  if [[ -x "/opt/homebrew/bin/python3.13" ]]; then
    PYTHON_BIN="/opt/homebrew/bin/python3.13"
  fi
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON_BIN"
  echo "Install Python 3.13 and rerun (example: brew install python@3.13)."
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$LOCK_FILE"

if [[ "$(uname -m)" == "arm64" ]]; then
  VENV_ARCH="$(python - <<'PY'
import platform
print(platform.machine())
PY
)"
  if [[ "$VENV_ARCH" != "arm64" ]]; then
    echo "ERROR: created venv architecture is '$VENV_ARCH' on Apple Silicon host."
    echo "Set PYTHON_BIN=/opt/homebrew/bin/python3.13 and retry."
    exit 1
  fi
fi

if [[ "$INSTALL_PADDLE_NIGHTLY" == "true" ]]; then
  python -m pip install --pre paddlepaddle -i https://www.paddlepaddle.org.cn/packages/nightly/cpu/
fi

python "$ROOT/scripts/setup/check_capstone_env.py" \
  --lock "$LOCK_FILE" \
  --strict-python

if [[ "$WITH_GATE" == "true" ]]; then
  (cd "$ROOT" && make test-phase1-gate)
fi

echo "Capstone environment is ready: $VENV_DIR"
