# 01 — Repository and CLI Inventory

## CLI surface (verified by running `datp-core --help` and reading `app/cli/*.py`)

Entry point: `datp_core.app.cli.app:main` (pyproject `[project.scripts]`).

| Command | Subcommand | Args | Domain construction | Execution/service | Planner | File:line |
|---|---|---|---|---|---|---|
| `validate` | — | `EXPERIMENT_ID?` | `validate_programme()` | graph + registry-vs-recipe reconciliation | — | `app/cli/app.py`, `app/validation.py` |
| `plan` | — | `EXPERIMENT_ID?` | `build_programme_plan()` | `expand_experiment_plan()` | deterministic coordinate ordering + digest | `app/cli/app.py`, `app/planning.py` |
| `preprocess` | — | `DATASET_ID`, `--overwrite` | `preprocess_datasets()` | `materialize_datasets()` | — | `app/cli/app.py` |
| `smoke` | — | `EXPERIMENT_ID?`, `--overwrite` | `run_smoke()` | one canonical seed per experiment; anchor gate enforced | `seed_cohort_for()` | `app/cli/app.py` |
| `report` | — | `EXPERIMENT_ID?`, `--overwrite` | `generate_report()` | `recipe_for(id).report()` | — | `app/cli/app.py` |
| `status` | — | `EXPERIMENT_ID?` | `programme_status()` | filesystem-only, read-only | — | `app/cli/app.py` |
| `run` | `experiment` | `EXPERIMENT_ID`, `--overwrite` | `run_experiment()` | `recipe_for(id).dispatch()` | `seed_cohort_for()` | `app/cli/execution.py` |
| `run` | `campaign` | `--overwrite` | `run_campaign()` | mandatory recipes, dependency order | plan-based | `app/cli/execution.py` |
| `anchor` | `reproduce` | `--overwrite` | `reproduce_anchor()` | locked 5-seed historical cohort | — | `app/cli/anchor.py` |
| `anchor` | `verify` | — | `verify_anchor_programme()` | 14-condition gate validator | — | `app/cli/anchor.py` |
| `anchor` | `status` | — | `anchor_status()` | read-only | — | `app/cli/anchor.py` |

Matches CLAUDE.md §9 public-CLI contract exactly (8 top-level commands, no extra/hidden entry points found).

## Experiment registry reconciliation

- Matrix declares **24** experiment identities; registry (`experiments/registry.py`) declares **24**; `app/recipes.py` wires **22** (`ExperimentRecipe(` occurrences verified by direct grep count) via `EXPERIMENT_RECIPES`, covering every non-suppressed, non-anchor experiment. `HISTORICAL_DATP_REPRODUCTION` is anchor-only (wired through `anchor` CLI, not `run experiment`). `ALERT_BURDEN_TRANSLATION` is the sole `SUPPRESSED` experiment, correctly has no recipe. 22 + 1 anchor-only + 1 suppressed = 24, reconciling exactly with the matrix/registry count.
- Consistency between registry and recipes is enforced at runtime by `validate_programme()` (`app/validation.py`, raises `ProtocolValidationError` on missing/duplicate/stale wiring) and is covered by `tests/unit/app/test_programme.py::test_every_non_suppressed_experiment_has_exactly_one_recipe` (independently confirmed present — an initial subagent finding that this test was missing was a false positive, corrected after direct inspection).
- Full mapping table: see `05_EXPERIMENT_AUDITS.md`.

## Source component inventory (by canonical package)

Enumerated directly via `list_dir`/`find`; matches the canonical tree in `CLAUDE.md` at the package level (`core/`, `data/`, `detector/`, `thresholds/`, `analysis/`, `experiments/`, `artifacts/`, `presentation/`, `app/`, `runtime/` all present, no obsolete top-level roots `datp_core.{anchor,calibration,datasets,domain,evaluation,learning,pipeline,preprocessing,protocols,thresholding,reporting,cli}` exist — confirmed via `test_architecture.py` and direct search).

Known file-level deviations from the CLAUDE.md tree diagram (not package-level, see `08_FINDINGS.md` ARCH-001/ARCH-002):
- `artifacts/repositories/` contains `datasets.py, evaluations.py, models.py, publication.py, thresholds.py` — no `populations.py, preprocessing.py, checkpoints.py, scores.py` (persistence for those lives in `data/populations/`, `data/preprocessing/`, `detector/checkpoints/`, `detector/scoring/` instead, colocated with the domain logic that validates it).
- `artifacts/serializers/` contains `json.py, parquet.py` — no `safetensors.py, skops.py` (used inline via `safetensors.torch`/`skops.io` in `detector/checkpoints/`, `detector/training/`, `data/preprocessing/`).
- Stale `__pycache__` entries (`repositories/checkpoints.cpython-312.pyc`, `repositories/preprocessing.cpython-312.pyc`, `serializers/safetensors.cpython-312.pyc`, `serializers/skops.cpython-312.pyc`) prove these files existed previously and were removed without the diagram being updated.
- `experiments/anchor/` has `spec.py, run.py` + domain modules (`comparison.py, contracts.py, gate.py, reproduction.py`) but no `analyze.py`/`report.py`; `experiments/confirmatory/` has `spec.py, run.py` only; `experiments/temporal/` has `run.py` only (no `spec.py`/`analyze.py`/`report.py`).

Graphify: pre-existing index at `graphify-out/graph.json` used by subagents for initial navigation where available; direct source inspection (`read_file`/`grep_search`) was the primary verification method throughout, consistent with "Graphify is a navigation accelerator, not scientific proof."
