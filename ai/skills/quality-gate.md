# Skill: quality-gate

The single quality workflow. Commands and agents reference this file instead of repeating commands.
All commands run through `uv`. `nox` is not usable here (empty `noxfile.py`); use the `uv run` forms below.

## Per change (run on the affected files/areas only)

- Format: `uv run ruff format <changed paths>`
- Lint: `uv run ruff check <changed paths>`
- Type-check: `uv run pyright <changed paths>` (strict mode is configured in `pyproject.toml`)
- Impacted tests, run **twice** so `pytest-randomly` orders them differently, and compare:
  `uv run pytest <impacted test paths>`
- Affected invariants only when the change touches them:
  - layer boundaries: `uv run lint-imports` and `uv run pytest -m architecture`
  - CUDA code: `uv run pytest -m cuda`

A test that passes in one order and fails in another is an order-dependence defect; fix the shared
state, never pin a seed to hide it. A skipped impacted test needs a stated reason.

## Checkpoint (task completion, or shared behavior changed)

- `uv run ruff format` and `uv run ruff check` (whole tree)
- `uv run pyright`
- `uv run lint-imports`
- `uv run pytest` (full suite, includes `-m architecture`)
- Configuration validation for any touched schema/mapping/YAML.

## CI only

Sonar and CodeScene run in CI on push (`.github/workflows/`). There is no supported local invocation;
do not claim they ran locally.

## Fail conditions

Any command above exits non-zero, an impacted test is order-dependent, or a claimed check did not run.

## Output

Report the exact commands run and their result under **Checks Run**; list untested impacted areas
under **Skipped Checks** with a reason.
