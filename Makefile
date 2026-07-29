.PHONY: format format-check lint pylint typecheck test test-parallel nox materialize-canonical sonar-analyze codescene-delta code-health

UV ?= uv
SONAR ?= $(HOME)/.local/share/sonarqube-cli/bin/sonar
SONAR_PROJECT ?= naslouby-salahe_datp-core
SONAR_ORG ?= naslouby-salahe
SONAR_SERVER ?= https://sonarcloud.io
CS ?= /usr/local/bin/cs

format:
	$(UV) run ruff format src tests noxfile.py

format-check:
	$(UV) run ruff format --check src tests noxfile.py

lint:
	$(UV) run ruff check src tests noxfile.py
	$(UV) run pylint src
	$(UV) run pylint --disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison tests

pylint:
	$(UV) run pylint src
	$(UV) run pylint --disable=missing-module-docstring,too-few-public-methods,use-implicit-booleaness-not-comparison tests

typecheck:
	$(UV) run pyright

test: test-parallel

test-parallel:
	$(UV) run pytest -n auto -q

nox:
	$(UV) run nox

materialize-canonical:
	$(UV) run datp-core materialize-canonical-datasets

# Loads untracked .env into the recipe environment without printing secrets.
define load-local-env
	set -a; \
	if [ -f .env ]; then . ./.env; fi; \
	set +a; \
	test -n "$${SONARQUBE_CLI_TOKEN:-}"
endef

sonar-analyze:
	@$(load-local-env); \
	SONARQUBE_CLI_SERVER="$(SONAR_SERVER)" \
	SONARQUBE_CLI_ORG="$(SONAR_ORG)" \
	  "$(SONAR)" analyze \
	  --project "$(SONAR_PROJECT)" --base origin/main --depth DEEP --format json \
	  > /tmp/datp-sonar-analyze.json; \
	python3 -c 'import json,sys; d=json.load(open("/tmp/datp-sonar-analyze.json")); secrets=int((d.get("secrets") or {}).get("summary",{}).get("totalIssues") or 0); agentic=int((d.get("agentic") or {}).get("summary",{}).get("totalIssues") or 0); failures=int((d.get("agentic") or {}).get("summary",{}).get("totalFailures") or 0); print(json.dumps({"secretsIssues": secrets, "agenticIssues": agentic, "agenticServiceFailures": failures, "totalIssues": secrets+agentic}, indent=2)); sys.exit(1 if secrets+agentic else 0)'

codescene-delta:
	@$(load-local-env); \
	test -n "$${CS_ACCESS_TOKEN:-}"; \
	"$(CS)" delta --output-format json --pretty

code-health: sonar-analyze codescene-delta
