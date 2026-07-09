# datp-core

Device-aware threshold calibration for federated IoT malware detection.

DATP is a fixed-encoder, fixed-federated-model, threshold-calibration-scope
study: a shared FedAvg autoencoder is trained once per seed and frozen; only
the threshold-calibration scope varies across the core ladder (B0-B4).
Governance, scope boundaries, and the full protocol freeze live under
[`ai/`](ai/) and [`docs/protocol/`](docs/protocol/) — read
[`AGENTS.md`](AGENTS.md) first.

## Status: Phase 2 — Anchor Reproduction Pipeline

Phase 2 implements a fixture-validated Regime A N-BaIoT anchor: typed raw-data
discovery/loading, physical-device mapping, leakage-checked splits, fixed
autoencoder FedAvg, frozen checkpoints, reconstruction scores, and B1/B2
evaluation. The safe CLI exposes a fixture smoke run, a dry 10-seed plan, and a
two-seed real-data mini-run and full-run readiness gate that require configured CUDA.

**Not in Phase 2:** B3/B4 or threshold variants, FedProx, personalization,
Regime C, Edge-IIoTset, temporal recalibration, full 10-seed execution,
statistics, or result/manuscript production. Track implementation progress in
[`CHANGELOG.md`](CHANGELOG.md).

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

Or invoke the CLI directly: `uv run datp-core --help`. Phase 2 adds
`run-smoke anchor-fixture`, `run-mini confirmatory-regime-a --seeds 2`,
`plan confirmatory-regime-a`, and `validate-anchor-readiness`. The full
10-seed execution requires `run-full confirmatory-regime-a --confirm-full-run`
and is never run automatically.

## Static analysis

`sonar-project.properties` defines the SonarQube project scope. The local
analysis was run against SonarQube Community Build with zero open findings.
