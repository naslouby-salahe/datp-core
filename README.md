# DATP-Core

DATP-Core is the reproducible research implementation for the journal extension of Device-Aware Threshold Personalization in federated IoT malware detection.

## Scientific scope

The repository separates model training from threshold calibration and evaluation. Its core comparisons use fixed model, preprocessing, checkpoint, score, label, client, cohort, and row-order evidence so threshold policy is the controlled difference.

The current research surface includes:

- N-BaIoT natural physical-device clients and controlled Dirichlet/IID clients;
- CICIoT2023 file-defined pseudo-client applicability evidence;
- Edge-IIoTset static and chronology-verified temporal groups;
- centralized and federated autoencoder training;
- FedAvg, FedProx, and Ditto stress-test paths;
- shared, local, family, cluster, shrinkage, conformal, and federated-statistics thresholds;
- confirmatory, mechanism, external-validation, temporal, and operational evidence roles.

The scientific source of truth is [`docs/Journal_Extension_Master_Roadmap.md`](docs/Journal_Extension_Master_Roadmap.md).

## Architecture

The intended dependency direction is:

```text
domain
  -> protocols
  -> datasets / calibration / preprocessing / learning / thresholding / evaluation
  -> analysis / reporting
  -> pipeline
  -> cli
```

Key boundaries:

- `domain` contains stable identities, values, contracts, and errors. It must not own repository or filesystem behavior.
- `protocols` contains frozen scientific declarations and validation.
- `datasets` owns audited ingestion, canonical publication, populations, partitioning, and split evidence.
- `preprocessing`, `learning`, `thresholding`, and `evaluation` own their scientific computations and contracts.
- `analysis` consumes validated evaluation evidence.
- `pipeline` composes application workflows without redefining lower-level contracts.
- `cli` is an adapter over application services.

No backwards-compatibility shims, redirect modules, implicit CPU fallback, or alternate scientific interpretations are maintained.

## Runtime requirements

- Python 3.13 or newer;
- CUDA-capable PyTorch runtime;
- GPU execution for training and other GPU-appropriate operations;
- raw datasets available beneath `data/raw` using the audited directory names documented in `RAW_DATA_STRUCTURE.md`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Main commands

```bash
python -m datp_core.cli.app --help
python -m datp_core.cli.app plan validate-protocols
python -m datp_core.cli.app plan build
python -m datp_core.cli.app run materialize-datasets
python -m datp_core.cli.app run confirmatory-campaign
```

Inspect command-specific options before execution:

```bash
python -m datp_core.cli.app run --help
```

## Validation

Use the repository-owned checks rather than ad hoc substitutes:

```bash
pytest
ruff check .
pyright
python -m importlinter
```

Training and end-to-end execution additionally require the audited raw datasets and CUDA runtime.

## Artifact lifecycle

Published artifacts are immutable, checksummed, and coordinate-bound. A complete artifact may be reused only when its request identity and persisted evidence validate under the current contract. Incomplete outputs are not resumed; they are replaced and rebuilt. Changes to artifact layout or scientific contracts intentionally invalidate incompatible prior outputs.

## Development rules

- preserve fixed-score and no-leakage controls;
- use descriptive enum-backed identities;
- use value objects for scientifically meaningful public quantities;
- keep primitives local to implementation details;
- remove obsolete callers when moving code;
- avoid forwarding wrappers and compatibility aliases;
- keep CUDA mandatory where the operation is GPU-appropriate;
- update impacted tests with every structural change.
