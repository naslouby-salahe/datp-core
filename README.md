# datp-core

Device-aware threshold calibration for federated IoT malware detection.

DATP is a fixed-encoder, fixed-federated-model, threshold-calibration-scope
study: a shared FedAvg autoencoder is trained once per seed and frozen; only
the threshold-calibration scope varies across the core ladder (B0-B4).
Governance, scope boundaries, and the full protocol freeze live under
[`ai/`](ai/) and [`docs/protocol/`](docs/protocol/) — read
[`AGENTS.md`](AGENTS.md) first.

## Status: Phase 1 — Scratch Foundation

Phase 1 delivers a clean, tested, runnable project foundation. It does
**not** implement scientific algorithms, run experiments, train models, or
process real datasets. Concretely, Phase 1 provides:

- project skeleton, package metadata, and a Phase 1 CLI skeleton
- canonical path resolution and a repository layout contract
- domain enums / typed identifiers for regimes, policies, datasets, seeds, metrics
- a typed config loader and schema validation for `configs/`
- config skeletons for every dataset/training/thresholding/analysis/suite group
- dataset contracts (no loaders — raw data presence is checked, never assumed)
- artifact manifest schemas with JSON round-trip and reuse-identity guards
- a no-overwrite policy for produced artifacts and curated results
- determinism and seed-locking utilities (Python/NumPy; PyTorch if present)
- a hardware/device selection utility (CPU fallback; CUDA only if available)
- a project logging convention
- reusable, tiny, deterministic test fixtures

**Not in Phase 1:** dataset loaders/preprocessing, FedAvg/FedProx training,
threshold policy computation (B0-B4 and variants), scoring, statistics,
table/figure generation, or any experiment execution. Those begin in Phase 2+
per [`MASTER_TICKET_LOG.md`](MASTER_TICKET_LOG.md); track day-to-day progress
in [`CHANGELOG.md`](CHANGELOG.md).

## Setup

```bash
uv sync
```

## Raw data

Raw datasets are never bundled in this repository. `data/raw` is a symlink to
an external raw-data root (see [`data/README.md`](data/README.md)); presence
is checked at runtime — nothing is created automatically, and nothing under
`data/raw` is ever moved or modified. Override the resolved root with
`DATP_DATA_ROOT` (see [`.env.example`](.env.example)) if your raw data lives
elsewhere.

## Outputs, checkpoints, and results

- `checkpoints/` — frozen model weights, one per (dataset, regime, seed, α);
  read-only once frozen. See [`checkpoints/README.md`](checkpoints/README.md).
- `outputs/` — the complete, heavy, reproducible-but-not-curated runtime
  artifact store (logs, scores, thresholds, metrics, raw tables/figures).
  See [`outputs/README.md`](outputs/README.md).
- `results/` — curated, lightweight, shareable derivations only, promoted
  from `outputs/` by result curation. See [`results/README.md`](results/README.md).

## Developer commands

```bash
make install         # uv sync
make test             # full pytest suite
make unit             # tests/unit only
make integration       # tests/integration only
make lint              # ruff check
make format             # ruff format
make typecheck           # pyright
make validate-config     # validate every configs/*.yaml skeleton
make validate-layout     # check the repo against the layout contract
make doctor              # environment/device/raw-data/layout summary
make check                # lint + typecheck + test
```

Or invoke the CLI directly: `uv run datp-core --help`. Phase 1 exposes only
read-only commands (`doctor`, `validate-config`, `show-paths`, `list-suites`,
`validate-layout`) — there is no training or experiment-execution command
yet, and none will run heavy work until Phase 2+.
