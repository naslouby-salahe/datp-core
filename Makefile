.PHONY: install format format-check lint lint-imports pylint typecheck test test-parallel \
	test-unit test-integration test-property test-scientific test-e2e test-target nox \
	validate plan preprocess smoke report status run-experiment run-campaign \
	anchor-reproduce anchor-verify anchor-status release-validate clean \
	code-health sonar-analyze codescene-delta

UV ?= uv
SONAR ?= $(HOME)/.local/share/sonarqube-cli/bin/sonar
SONAR_PROJECT ?= naslouby-salahe_datp-core
SONAR_ORG ?= naslouby-salahe
SONAR_SERVER ?= https://sonarcloud.io
CS ?= /usr/local/bin/cs

# Optional make-variable arguments for CLI targets:
#   EXPERIMENT_ID, DATASET_ID, OVERWRITE=1, TEST_TARGET, RELEASE_ROOT

install: ## Install the project with every optional group and extra
	$(UV) sync --all-groups --all-extras

format: ## Apply Ruff formatting to source, tests, tools, and the noxfile
	$(UV) run ruff format src tests tools noxfile.py

format-check: ## Verify Ruff formatting without modifying files
	$(UV) run ruff format --check src tests tools noxfile.py

lint: ## Run Ruff, Pylint, and import-linter architecture contracts
	$(UV) run ruff check src tests tools noxfile.py
	$(UV) run pylint src
	$(UV) run pylint --disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison tests
	$(UV) run lint-imports

lint-imports: ## Enforce the import-linter architecture contracts
	$(UV) run lint-imports

pylint: ## Run Pylint on source and tests
	$(UV) run pylint src
	$(UV) run pylint --disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison tests

typecheck: ## Run Pyright static type checking
	$(UV) run pyright

test: test-parallel ## Default test target: full suite in parallel

test-parallel: ## Run the full test suite in parallel (pytest -n auto)
	$(UV) run pytest -n auto -q

test-unit: ## Run unit tests
	$(UV) run pytest -n auto -q tests/unit

test-integration: ## Run integration tests
	$(UV) run pytest -n auto -q tests/integration

test-property: ## Run property-based tests
	$(UV) run pytest -n auto -q tests/property

test-scientific: ## Run scientific-invariant tests
	$(UV) run pytest -n auto -q tests/scientific

test-e2e: ## Run end-to-end pipeline tests (CUDA-gated)
	$(UV) run pytest -n auto -q tests/e2e

test-target: ## Run a targeted test path: make test-target TEST_TARGET=tests/unit/thresholding
	$(UV) run pytest -n auto -q $(TEST_TARGET)

nox: ## Run the default nox session set
	$(UV) run nox

validate: ## CLI: validate programme declarations (optional EXPERIMENT_ID)
	$(UV) run datp-core validate $(EXPERIMENT_ID)

plan: ## CLI: print the execution plan (optional EXPERIMENT_ID)
	$(UV) run datp-core plan $(EXPERIMENT_ID)

preprocess: ## CLI: materialize canonical dataset artifacts (DATASET_ID=nbaiot|ciciot2023|edge_iiotset)
	@test -n "$(DATASET_ID)" || (echo "DATASET_ID is required: nbaiot|ciciot2023|edge_iiotset" && exit 1)
	$(UV) run datp-core preprocess $(DATASET_ID) $(if $(OVERWRITE),--overwrite,)

smoke: ## CLI: run the bounded smoke programme (optional EXPERIMENT_ID)
	$(UV) run datp-core smoke $(EXPERIMENT_ID) $(if $(OVERWRITE),--overwrite,)

report: ## CLI: generate experiment reports (optional EXPERIMENT_ID)
	$(UV) run datp-core report $(EXPERIMENT_ID)

status: ## CLI: show programme status (optional EXPERIMENT_ID)
	$(UV) run datp-core status $(EXPERIMENT_ID)

run-experiment: ## CLI: execute one experiment (EXPERIMENT_ID required)
	@test -n "$(EXPERIMENT_ID)" || (echo "EXPERIMENT_ID is required (see datp-core validate)" && exit 1)
	$(UV) run datp-core run experiment $(EXPERIMENT_ID) $(if $(OVERWRITE),--overwrite,)

run-campaign: ## CLI: execute the complete campaign
	$(UV) run datp-core run campaign $(if $(OVERWRITE),--overwrite,)

anchor-reproduce: ## CLI: rebuild the independent anchor reproduction
	$(UV) run datp-core anchor reproduce $(if $(OVERWRITE),--overwrite,)

anchor-verify: ## CLI: verify the anchor reproduction gate
	$(UV) run datp-core anchor verify

anchor-status: ## CLI: show anchor gate status
	$(UV) run datp-core anchor status

release-validate: ## Validate a reproducibility release bundle (RELEASE_ROOT required)
	@test -n "$(RELEASE_ROOT)" || (echo "RELEASE_ROOT is required" && exit 1)
	$(UV) run python -m tools.reproducibility.release $(RELEASE_ROOT)

clean: ## Remove Python caches, coverage data, and build artifacts
	rm -rf build dist .coverage .pytest_cache .ruff_cache .benchmarks .nox
	find . -type d -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './.venv/*' -delete

# Loads untracked .env into the recipe environment without printing secrets.
define load-local-env
	set -a; \
	if [ -f .env ]; then . ./.env; fi; \
	set +a; \
	test -n "$${SONARQUBE_CLI_TOKEN:-}"
endef

sonar-analyze: ## Run the SonarQube CLI analysis against origin/main
	@$(load-local-env); \
	SONARQUBE_CLI_SERVER="$(SONAR_SERVER)" \
	SONARQUBE_CLI_ORG="$(SONAR_ORG)" \
	  "$(SONAR)" analyze \
	  --project "$(SONAR_PROJECT)" --base origin/main --depth DEEP --format json \
	  > /tmp/datp-sonar-analyze.json; \
	python3 -c 'import json,sys; d=json.load(open("/tmp/datp-sonar-analyze.json")); secrets=int((d.get("secrets") or {}).get("summary",{}).get("totalIssues") or 0); agentic=int((d.get("agentic") or {}).get("summary",{}).get("totalIssues") or 0); failures=int((d.get("agentic") or {}).get("summary",{}).get("totalFailures") or 0); print(json.dumps({"secretsIssues": secrets, "agenticIssues": agentic, "agenticServiceFailures": failures, "totalIssues": secrets+agentic}, indent=2)); sys.exit(1 if secrets+agentic else 0)'

codescene-delta: ## Run the CodeScene delta analysis
	@$(load-local-env); \
	test -n "$${CS_ACCESS_TOKEN:-}"; \
	"$(CS)" delta --output-format json --pretty

code-health: sonar-analyze codescene-delta ## Run external code-health analyses (requires .env tokens)
