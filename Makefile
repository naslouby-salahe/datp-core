.PHONY: format format-check lint pylint typecheck test test-parallel nox \
	materialize-canonical preprocess-dataset preprocess-all-datasets

UV ?= uv
DATASET ?= nbaiot
OVERWRITE ?= 0

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

preprocess-dataset:
	@if [ "$(OVERWRITE)" = "1" ]; then \
		$(UV) run datp-core preprocess-dataset $(DATASET) --overwrite; \
	else \
		$(UV) run datp-core preprocess-dataset $(DATASET); \
	fi

preprocess-all-datasets:
	@if [ "$(OVERWRITE)" = "1" ]; then \
		$(UV) run datp-core preprocess-all-datasets --overwrite; \
	else \
		$(UV) run datp-core preprocess-all-datasets; \
	fi
