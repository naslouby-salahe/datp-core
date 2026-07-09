.PHONY: install test unit integration lint format typecheck doctor validate-config validate-layout show-paths list-suites check

install:
	uv sync

test:
	uv run pytest

unit:
	uv run pytest tests/unit

integration:
	uv run pytest tests/integration

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

doctor:
	uv run datp-core doctor

validate-config:
	uv run datp-core validate-config

validate-layout:
	uv run datp-core validate-layout

show-paths:
	uv run datp-core show-paths

list-suites:
	uv run datp-core list-suites

check: lint typecheck test
