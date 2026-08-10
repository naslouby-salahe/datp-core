# DATP-Core

DATP-Core is the research implementation of the Device-Aware Threshold Personalization journal extension for federated IoT anomaly detection.

## Scientific execution

Each scientific execution computes a fresh coherent result from declared prepared data:

```text
data -> population and split -> preprocessing -> training -> terminal model -> scores -> thresholds -> evaluation -> analysis -> publication
```

Canonicalized data, population/split artifacts, fitted preprocessing state, and transformed data are persistent prepared inputs. `preprocess --overwrite` explicitly replaces them. Experiment execution consumes existing prepared data and never silently rebuilds it.

Training produces one terminal model. Every compared threshold policy receives that same terminal model and the same in-memory score evidence, rows, labels, client identities, partitions, calibration eligibility rule, and metric definitions. Only threshold construction differs. Calibration is benign-only and held-out evaluation labels never influence training, calibration, or threshold construction.

Recovery checkpoints exist only to continue interrupted training. Predetermined diagnostic snapshots are observational training outputs. Neither is a model-choice mechanism or an input to scoring.

The scientific source of truth is [the master roadmap](docs/Journal_Extension_Master_Roadmap.md).

## Runtime requirements

- Python 3.12
- CUDA-capable PyTorch runtime
- Audited raw datasets under `data/raw`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## CLI

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

An execution writes its current results. Existing destinations are replaced only through the CLI's explicit overwrite contract. Interrupted-training recovery is isolated from normal execution.

## Validation

```bash
pytest
ruff check .
pyright
python -m importlinter
```

End-to-end training requires CUDA and the audited raw datasets.

## Engineering rules

- no backward compatibility, aliases, redirects, shims, or parallel APIs;
- typed immutable scientific and application contracts;
- no downstream persisted-result reuse;
- no attack-label leakage into calibration or threshold construction;
- delete obsolete code and tests instead of retaining stale callers.
