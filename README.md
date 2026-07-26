# DATP-Core

Device-Aware Threshold Personalization for non-IID federated IoT anomaly detection.

**Scientific identity.** DATP is a threshold-calibration-scope study on a fixed, once-trained, frozen FedAvg autoencoder. The encoder and scores are never retrained across the B1-B4 comparison; only the granularity at which the benign quantile threshold is shared (federation-wide, family-wide, cluster-wide, or per-client) varies. Calibration is benign-only. The causal question is whether threshold-calibration scope changes deployed per-client false-positive-rate dispersion.

This is not a generic FL-IDS framework.

## Setup

```bash
uv sync --dev
```

Create a symlink to external datasets:

```bash
ln -s /path/to/external/raw data/raw
```

The symlink target must exist. Runtime validation rejects broken symlinks.

## Configuration

Authoritative configuration lives in `configs/`. Every scientific value originates from validated YAML through Pydantic v2 models. No scientific defaults exist in Python code.

```bash
datp-core config validate
datp-core config fingerprint
```

## Execution

```bash
datp-core experiment plan --config anchor_reproduction
datp-core experiment run --config anchor_reproduction
datp-core campaign run
```

Campaign resumption uses the same command. Completed experiments are validated and skipped. The first incomplete experiment is restarted from preflight. Use `--override` to delete and restart a specific experiment.

## Outputs and Results

`outputs/` holds machine-oriented artifacts: checkpoints, scores, thresholds, metrics, stage manifests. These are generated and consumed by the pipeline.

`results/` holds paper-facing frozen derivatives: tables, figures, statistics, manifests. Reports trace to frozen manifests with complete provenance.

Do not place smoke results in `results/`.

## Quality Commands

```bash
make help          # Show all targets
make install       # Install dependencies
make format        # Format source code
make lint          # Lint (ruff)
make typecheck     # Static type checking (pyright)
make pylint        # Static analysis (pylint)
make test          # Run test suite
make test-full     # Run tests with coverage
make contracts     # Contract and scientific invariant tests
make imports       # Layer dependency checks
make scientific-audit  # Scientific invariant tests
make smoke         # Smoke experiments (requires GPU)
make smoke-synthetic   # Synthetic end-to-end smoke tests
make sonar         # SonarQube analysis
make quality       # All quality gates
make clean         # Remove artifacts, preserve data symlink and results
```

Quality gates are also available through Nox:

```bash
uv run nox -s quality
```

## GPU Requirements

Training requires CUDA. CUDA-specific tests check capability at runtime and skip with an explicit reason when CUDA is absent. GPU-required execution must not silently fall back to CPU.

## Adding a Threshold Policy

1. Define a `ThresholdPolicyKind` member in `thresholding/policies/enums.py`
2. Create a typed policy record
3. Implement the estimator function
4. Register in the estimator dispatch
5. Add focused tests

No changes required to training, score generation, evaluation, or unrelated pipeline stages.

## Data Symlink

`data/raw` is a symlink to external raw datasets. Never replace it, dereference it during cleanup, or copy raw data into the repository.

## Smoke Limitations

Smoke runs use a typed smoke runtime profile that:
- Remains separate from scientific configuration
- Does not change canonical scientific values
- Marks all artifacts as smoke
- Never produces paper results

A smoke run is not a completed experiment.
