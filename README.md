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
- `pipeline` composes application workflows without redefining lower-level contracts. Deterministic planning, stage sequencing, reuse, provenance, completion validation, and publication live under `pipeline/`.
- `cli` is a thin research-facing adapter. It accepts only experiment IDs, dataset IDs, and `--overwrite`, and calls programme services in `pipeline/workflows/`.

No external orchestration framework is required. Artifact reuse, idempotency, provenance, checksums, and completion validation are repository-owned.

No backwards-compatibility shims, redirect modules, implicit CPU fallback, or alternate scientific interpretations are maintained.

## Runtime requirements

- Python 3.12 (see pyproject.toml requires-python);
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

## Execution

The public CLI exposes only research intentions. Scientific parameters (seeds, coefficients, populations, split protocols, threshold policies, paths, and training hyperparameters) are resolved from typed protocol declarations.

```text
datp-core
├── validate [EXPERIMENT_ID]
├── plan [EXPERIMENT_ID]
├── preprocess [DATASET_ID] [--overwrite]
├── smoke [EXPERIMENT_ID] [--overwrite]
├── anchor
│   ├── reproduce [--overwrite]
│   ├── verify
│   └── status
├── run
│   ├── experiment <EXPERIMENT_ID> [--overwrite]
│   └── campaign [--overwrite]
├── report [EXPERIMENT_ID] [--overwrite]
└── status [EXPERIMENT_ID]
```

Examples:

```bash
datp-core validate
datp-core plan shared_vs_local_confirmation
datp-core preprocess
datp-core preprocess nbaiot --overwrite
datp-core smoke shared_vs_local_confirmation
datp-core anchor reproduce
datp-core anchor verify
datp-core anchor status
datp-core run experiment shared_vs_local_confirmation
datp-core run campaign
datp-core report
datp-core status
```

Module invocation uses the same application:

```bash
python -m datp_core.cli.app --help
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

Artifact reuse, idempotency, provenance, checksums, and completion validation are owned by this repository (not by an external orchestrator). Published artifacts are immutable, checksummed, and coordinate-bound. A complete artifact may be reused only when its request identity and persisted evidence validate under the current contract. Incomplete outputs are not resumed; they are replaced and rebuilt. Changes to artifact layout or scientific contracts intentionally invalidate incompatible prior outputs.

Smoke artifacts live under `outputs/smoke/` and must not be treated as confirmatory evidence.

## Development rules

- preserve fixed-score and no-leakage controls;
- use descriptive enum-backed identities;
- use value objects for scientifically meaningful public quantities;
- keep primitives local to implementation details;
- remove obsolete callers when moving code;
- avoid forwarding wrappers and compatibility aliases;
- keep CUDA mandatory where the operation is GPU-appropriate;
- update impacted tests with every structural change.
