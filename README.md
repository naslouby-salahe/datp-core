# DATP-Core

DATP-Core is the research implementation of the *Device-Aware Threshold Personalization* journal extension: a controlled study of **threshold-calibration scope** in federated IoT anomaly detection. On a frozen federated autoencoder, only the scope at which benign anomaly thresholds are calibrated varies — one shared threshold, one per physical-device family, one per data-driven cluster, or one per client — and the resulting distribution of false-positive burden across heterogeneous clients is measured.

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
datp-core results                       gather passed experiment evidence into results/
datp-core anchor reproduce|verify|status
```

`--overwrite` is available on `preprocess`, `smoke`, `run`, `results`, and `anchor reproduce`; existing artifacts are kept by default. A passed experiment is not rerun unless `--overwrite` is given. `datp-core results --overwrite` rebuilds only the delivery `results/` bundle.

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
```
