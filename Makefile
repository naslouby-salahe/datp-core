.PHONY: help install format lint typecheck pylint test test-full contracts scientific-audit smoke smoke-synthetic sonar quality clean clean-all

help: ## Show this help
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

install: ## Install the project and development dependencies
	uv sync --dev

format: ## Format source code with Ruff
	uv run nox -s lint -- || (uv run ruff format src tests && uv run ruff check --fix src tests)

lint: ## Lint source code without modifying
	uv run nox -s lint

typecheck: ## Run Pyright static type checking
	uv run nox -s typecheck

pylint: ## Run Pylint static analysis
	uv run pylint src/datp_core

test: ## Run the test suite in parallel
	uv run nox -s tests

test-full: ## Run full test suite with coverage
	uv run nox -s tests_full

contracts: ## Run contract and scientific invariant tests
	uv run nox -s contracts

imports: ## Enforce layer dependency contracts
	uv run nox -s imports

scientific-audit: ## Run scientific invariant tests
	uv run pytest tests/scientific/ -q

smoke: ## Run smoke experiments (requires GPU)
	uv run datp-core smoke --profile smoke

smoke-synthetic: ## Run synthetic end-to-end smoke tests
	uv run nox -s smoke_synthetic

sonar: ## Run SonarQube analysis
	uv run nox -s sonar

quality: lint typecheck pylint test contracts scientific-audit imports ## Run all quality gates

clean: ## Remove build artifacts, caches, and temporary files (preserves data symlink and results/)
	rm -rf build/ .pytest_cache/ .ruff_cache/ .mypy_cache/ .nox/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@echo "data/ symlink preserved"
	@echo "results/ preserved"

clean-all: clean ## ALSO delete outputs/ (destructive — confirms before deleting)
	@echo "WARNING: This will delete all experiment outputs in outputs/"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	rm -rf outputs/
	@echo "outputs/ deleted"
