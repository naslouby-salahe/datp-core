# datp-core

DATP journal-extension scratch implementation: fixed-encoder, fixed-federated-model,
threshold-calibration-scope study.

## Status

Phase 0 (repository and engineering foundation) is complete. `src/datp_core/` is an
empty, layered architectural skeleton with no scientific behavior yet — no dataset
access, preprocessing, training, scoring, or thresholding logic has been implemented.
See `CHANGELOG.md` for what Phase 0 delivered.

## Requirements

- Python 3.12 (exact `3.12.*`, enforced by `pyproject.toml`).
- [`uv`](https://docs.astral.sh/uv/) for dependency resolution and the committed lock.
- An NVIDIA GPU with CUDA is optional; CUDA-marked tests are skipped/serialized
  automatically when no GPU is present.

## Setup

```bash
uv sync --all-groups --all-extras --frozen
```

`--frozen` installs strictly from the committed `uv.lock`, with no re-resolution — this
is the reproducible install path and the one used to validate every quality gate below.

## Project layout

`src/datp_core/` is organized as seven layers, enforced by `import-linter` and
`pytest-archon` (no import runs the wrong direction):

- `domain/` — pure business rules and value objects (data, evaluation, experiments,
  learning, mathematics, runtime, thresholding).
- `application/` — use-case orchestration (planning, ports, reporting, runtime, stages).
- `infrastructure/` — concrete adapters for the application ports.
- `config/` — external configuration schemas and mapping.
- `composition/` — dependency wiring/registries.
- `cli/` — the `datp-core` command-line entrypoint.
- `analysis/` — report tables and figures.

`ai/` holds the provider-agnostic AI governance catalogue (agents, skills, hooks,
contracts, workflows, commands) described in `ai/README.md`; `.claude/`, `.agents/`,
`.codex/`, and `.github/` are thin adapters over it. `docs/` holds the roadmap,
architecture, and ticket tracking that governs implementation work — see `AGENTS.md`
for how a task should use them.

## Running checks

All validation is orchestrated through [Nox](https://nox.thea.codes/) sessions
(`nox -l` lists them); the ones with no `.venv`-pinned Python equivalent (`sonar`,
`codescene`) call a standalone system CLI directly.

| Session | What it checks |
|---|---|
| `lint` | `ruff check` |
| `format` | `ruff format --check` |
| `typecheck` | `pyright` (strict) |
| `architecture` | `import-linter` layer contracts, `pytest-archon` boundary tests |
| `xdist_safe` | the parallel-safe test suite (`pytest -n auto`) |
| `serial` | non-CUDA tests that must not run under parallel workers |
| `resource_intensive` | tests with an elevated resource budget, run in isolation |
| `cuda` | CUDA-dependent tests, serialized, order-randomization disabled |
| `synthetic` | reduced synthetic end-to-end system tests |
| `scientific_smoke` | confirmatory-statistic smoke tests on a small real-data subsample |
| `impacted` | ad hoc pytest invocation, args forwarded via `session.posargs` |
| `sonar` | SonarQube/SonarCloud analysis and quality gate |
| `codescene` | CodeScene Code Health delta analysis and quality gate |
| `full_suite` | every session above |

```bash
nox -s full_suite
```

`sonar` and `codescene` need their own credentials, supplied only as environment
variables (never committed to the repository):

- `sonar`: authenticate once interactively (`sonar auth login`), or export
  `SONARQUBE_CLI_TOKEN`/`SONARQUBE_CLI_ORG` in your shell.
- `codescene`: export `CS_ACCESS_TOKEN` (a codescene.io Personal Access Token).

If a token is missing, the corresponding session fails with an explicit message
rather than silently reporting a pass.

## Application configuration

Copy `.env.example` to `.env` and adjust if needed; both variables there are optional
and fall back to safe defaults (`DATP_DATA_ROOT` for the raw-dataset location,
`DATP_DEVICE` for device selection).
