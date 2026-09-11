#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "Warning: this bootstrap is optimized for Apple Silicon macOS."
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found. Install Python 3.12+ first."
  exit 1
fi

PY_MINOR="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("Python 3.12+ is required")
PY

echo "Using Python ${PY_MINOR}"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env from .env.example"
fi

if [[ ! -f job_boards.json ]]; then
  cp job_boards.example.json job_boards.json
fi

if [[ ! -f resume_profile.md ]]; then
  cp resume_profile.example.md resume_profile.md
fi

mkdir -p logs
.venv/bin/triage init-db
.venv/bin/python -m pytest -q

echo
echo "Bootstrap complete."
echo "Next: install/start Ollama, run '.venv/bin/triage model', then '.venv/bin/triage pull-model'."
echo "After configuring .env, run '.venv/bin/triage doctor' and '.venv/bin/triage run'."
