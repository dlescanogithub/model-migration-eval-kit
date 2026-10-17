# Plain `python -m ...` equivalents are in README.md (How to reproduce).
# make is optional.

PY ?= python3

.PHONY: setup lint test eval eval-regression demo secretscan

setup:
	$(PY) -m pip install -e ".[dev]"
	-$(PY) -m pre_commit install

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) -m mypy

test:
	$(PY) -m pytest

eval:
	$(PY) -m migration_eval eval --provider fake-old --runs 5 --today 2026-10-17

# This target is supposed to fail. A zero exit means the regression gate is broken.
eval-regression:
	$(PY) -m migration_eval eval-regression --runs 5 --today 2026-10-17

demo:
	$(PY) -m migration_eval compare --old fake-old --new fake-new --runs 10 --today 2026-10-17 --out out/demo

secretscan:
	$(PY) -m migration_eval secretscan .
