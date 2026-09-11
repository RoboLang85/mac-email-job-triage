.PHONY: setup test lint doctor run digest jobs

setup:
	./scripts/bootstrap_macos.sh

test:
	.venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .

doctor:
	.venv/bin/triage doctor

run:
	.venv/bin/triage run

digest:
	.venv/bin/triage digest

jobs:
	.venv/bin/triage jobs-refresh
