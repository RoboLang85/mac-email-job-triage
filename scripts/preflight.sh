#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run ./scripts/bootstrap_macos.sh first."
  exit 1
fi

python3 -m compileall -q src tests
.venv/bin/ruff check .
.venv/bin/pytest -q

if [[ -d .git ]]; then
  for risky in .env resume_profile.md job_boards.json; do
    if git ls-files --error-unmatch "$risky" >/dev/null 2>&1; then
      echo "FAIL: private runtime file is tracked: $risky"
      exit 1
    fi
  done
fi

if grep -RInE \
  --exclude='.env.example' \
  --exclude-dir='.git' \
  --exclude-dir='.venv' \
  '(GMAIL_APP_PASSWORD=.{4,}|FRONTIER_API_KEY=.{4,}|MS_CLIENT_SECRET=.{4,})' \
  .; then
  echo "FAIL: possible credential material found. Review matches before publishing."
  exit 1
fi

echo "Preflight passed."
