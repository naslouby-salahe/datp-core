# DATP-Core

DATP-Core is the research implementation of the *Device-Aware Threshold Personalization* journal extension: a controlled study of **threshold-calibration scope** in federated IoT anomaly detection. On a frozen federated autoencoder, only the scope at which benign anomaly thresholds are calibrated varies — one shared threshold, one per physical-device family, one per data-driven cluster, or one per client — and the resulting distribution of false-positive burden across heterogeneous clients is measured.

## Repository purpose

- implements the full scientific pipeline: data materialization, population/split construction, preprocessing, federated training, fixed-score generation, threshold calibration, evaluation, statistical analysis, and reporting;
- reproduces the historical N-BaIoT five-seed anchor and extends it to the ten-seed confirmatory campaign;
- provides the CLI, artifact repositories, provenance validation, and the reproducibility-release builder required by the roadmap;
- the authoritative scientific contract is `docs/Journal_Extension_Master_Roadmap.md`.

## Setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups --all-extras
```

Audited raw datasets live under `data/raw`. End-to-end training additionally requires a CUDA-capable PyTorch runtime.

## Principal CLI usage

```text
datp-core validate [EXPERIMENT_ID]      validate programme declarations
datp-core plan [EXPERIMENT_ID]          show the execution plan
datp-core preprocess DATASET_ID         materialize canonical dataset artifacts
datp-core smoke [EXPERIMENT_ID]         bounded smoke validation
datp-core run experiment EXPERIMENT_ID  run one experiment
datp-core run campaign                  run the complete campaign
datp-core report [EXPERIMENT_ID]        generate experiment reports
datp-core status [EXPERIMENT_ID]        show programme status
datp-core anchor reproduce|verify|status
```

`--overwrite` is available on `preprocess`, `smoke`, `run`, `report`, and `anchor reproduce`; existing artifacts are kept by default.

The reproducibility-release validator runs outside the runtime CLI:

```bash
uv run python -m tools.reproducibility.release <release-root>
```

## Development and validation

```bash
make format            # apply Ruff formatting
make lint              # Ruff + Pylint + import-linter contracts
make typecheck         # Pyright
make test              # full suite in parallel (pytest -n auto)
make test-target TEST_TARGET=tests/unit/thresholding
make validate          # CLI programme validation
make clean             # remove caches and build artifacts
```

The equivalent nox sessions are `tests`, `unit`, `integration`, `property`, `scientific`, `e2e`, `format`, `lint`, `types`, and `imports`; `nox` runs the default set (`tests`, `format`, `lint`, `types`, `imports`).

## Repository structure

```text
src/datp_core/          package source
├── data/               dataset materialization, populations, splits, preprocessing
├── detector/           autoencoder, federated training, scoring
├── thresholds/         calibration, threshold policies and variants
├── analysis/           metrics, statistics, mechanism analyses
├── experiments/        experiment registry, planning, execution
├── presentation/       figures, tables, claim validation
├── artifacts/          artifact repositories and serializers
├── app/                CLI and programme orchestration
└── core/               domain identities, contracts, errors
tests/                  unit, integration, property, scientific, e2e tests
tools/reproducibility/  release-bundle builder and validator
docs/                   roadmap, audit matrix, progress archive
```

## Engineering rules

- no backwards compatibility: obsolete APIs are replaced at their callers and deleted;
- typed, immutable domain identities and contracts; no `Any` or dictionary-shaped application plumbing;
- one semantic owner per scientific contract, verified by runtime-reachability audit;
- benign-only calibration, disjoint calibration/evaluation evidence, and no test-outcome feedback;
- the roadmap is the scientific authority; the audit matrix tracks implementation state.
