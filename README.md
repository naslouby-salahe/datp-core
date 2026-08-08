# DATP-Core

DATP-Core is the reproducible research implementation of the Device-Aware Threshold Personalization journal extension for federated IoT anomaly detection.

## Scientific scope

The study isolates threshold-calibration scope while preserving the fixed-detector contract. Within a seed and regime, compared threshold methods reuse the same selected detector, preprocessing state, client identities, predefined partitions, benign calibration evidence, held-out scores and labels, eligibility rule, and metric implementation. Calibration is benign-only and attack-labelled data remain evaluation-only.

The scientific source of truth is [`docs/Journal_Extension_Master_Roadmap.md`](docs/Journal_Extension_Master_Roadmap.md).

The implementation covers:

- N-BaIoT natural physical-device clients and controlled Dirichlet/IID clients;
- CICIoT2023 file-defined pseudo-client boundary evidence;
- Edge-IIoTset static and chronology-verified temporal groups;
- centralized and federated autoencoder training;
- FedAvg, FedProx, and genuine Ditto training-side stress tests;
- descriptive shared, local, family, cluster, shrinkage, conformal, and federated-statistics threshold identities;
- confirmatory, supportive, mechanism, external-validation, stress-test, temporal, applicability-boundary, and exploratory evidence.

## Architecture

The repository has one application architecture:

```text
domain
  -> protocols
  -> datasets / preprocessing / learning / calibration / thresholding / evaluation
  -> analysis
  -> pipeline foundations
  -> experiments
  -> presentation
  -> app programme / research services
  -> app CLI
```

Responsibilities are intentionally non-overlapping:

- `domain` owns stable identities, errors, provenance, and value objects.
- `protocols` owns frozen scientific declarations and protocol validation.
- scientific capability packages own their numerical and data-processing kernels.
- `pipeline` owns execution coordinates, stage services, scoring, checkpoint, decision, and publication foundations.
- `experiments` owns complete scientific experiment recipes and evidence analyses.
- `presentation` owns tables, figures, publication exports, and presentation validation.
- `app` owns programme planning, exact experiment registration, anchor gating, campaign lifecycle, reporting orchestration, status, and the thin CLI adapter.

There is no legacy `datp_core.cli`, `pipeline.workflows`, `reporting`, alternate planner, compatibility import, redirect module, or dual execution registry.

## Runtime requirements

- Python 3.12;
- CUDA-capable PyTorch runtime;
- GPU execution for training and GPU-appropriate operations;
- audited raw datasets beneath `data/raw` using the repository's declared raw-data structure.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## CLI

The public CLI exposes research intentions only. Seeds, populations, split protocols, threshold identities, model coefficients, paths, and scientific hyperparameters are resolved from typed declarations.

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
datp-core preprocess nbaiot --overwrite
datp-core smoke shared_vs_local_confirmation
datp-core anchor reproduce
datp-core anchor verify
datp-core run experiment shared_vs_local_confirmation
datp-core run campaign
datp-core report
datp-core status
```

Module invocation uses the same adapter:

```bash
python -m datp_core.app.cli.app --help
```

## Artifact lifecycle

Artifacts are deterministic, checksummed, coordinate-bound, and attributable to one scientific execution unit. Existing evidence is reused only when its request identity and completion contract validate. `--overwrite` is converted at the CLI boundary into an explicit application lifecycle mode and rebuilds only the owning scope. Smoke evidence lives under `outputs/smoke/` and is never confirmatory evidence.

## Validation

Repository checks are:

```bash
pytest
ruff check .
pyright
python -m importlinter
```

End-to-end training additionally requires CUDA and the audited raw datasets.

## Engineering rules

- no backward compatibility, aliases, redirects, shims, or parallel legacy APIs;
- descriptive enum-backed closed vocabularies; no runtime B0/B1/B2/B3/B4 identifiers;
- typed immutable scientific and application contracts;
- no `Any`, `object`-based domain contracts, untyped dictionary I/O, hidden defaults, or silent fallbacks;
- no hardcoded scientific values outside their validated protocol declarations;
- no attack-label leakage into calibration, threshold selection, eligibility, or checkpoint selection;
- capability-gated metrics and explicit unavailable/infeasible outcomes;
- delete dead code and obsolete tests rather than preserving stale callers.
