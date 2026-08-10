# DATP-Core Engineering and Scientific Contract

## Authority

DATP-Core implements `docs/Journal_Extension_Master_Roadmap.md`. The roadmap, typed scientific contracts, implementation, tests, and documentation are authoritative in that order.

## Scientific identity

DATP-Core is a controlled study of threshold-calibration scope in federated IoT anomaly detection. Within each declared comparison, threshold policies receive the exact same terminal detector, preprocessing state, client identities, partitions, benign calibration evidence, held-out score evidence, labels, eligibility rule, and metrics. Only the declared threshold estimator may differ.

Calibration is benign-only. Attack-labelled rows never influence training, calibration, threshold construction, eligibility, cluster features, comparator tuning, shrinkage, or conformal settings. AUROC is a fixed-score quality control, not the primary threshold-policy verdict.

The normal execution is:

```text
data -> population/split -> preprocessing -> training -> terminal model -> scores -> thresholds -> evaluation -> analysis -> publication
```

Canonicalized data, population/split artifacts, fitted preprocessing state, and transformed data are persistent prepared inputs. `preprocess --overwrite` is the only explicit replacement path. Experiment execution consumes these inputs and never silently rebuilds them. Training produces one terminal model. Scores are generated once and passed in memory to all compared threshold policies. Recovery checkpoints only continue interrupted training. Diagnostic checkpoints are predetermined observational snapshots. Neither changes the evaluated model.

## Architecture

- `core` owns errors, identifiers, numeric values, and immutable cross-cutting contracts.
- `data` owns data, populations, splits, and preprocessing.
- `detector` owns autoencoders, training, recovery/diagnostic checkpointing, and score generation.
- `thresholds` owns calibration and threshold policies.
- `analysis` owns metrics, inference, mechanisms, and operational analysis.
- `experiments` owns experiment declarations and execution recipes.
- `artifacts` owns layout and small atomic writes where interruption could corrupt output.
- `presentation` owns tables, figures, and presentation validation.
- `app` owns planning, campaign orchestration, and CLI adapters.

No compatibility APIs, forwarding modules, migration adapters, downstream persisted-result loading, generic content hashing, output validation lifecycles, or completion markers exist. Prepared-data persistence is the sole shared execution input.

## Engineering

Use existing typed enums and immutable models before introducing new types. Do not use loose dictionary domain I/O, `Any`, fallback behavior, hardcoded scientific parameters, or static-analysis suppressions. Preserve CUDA training and deterministic requirements. Delete dead code and stale tests.

Existing output handling is explicit at the CLI boundary. Normal execution always computes current results; interrupted-training recovery is the only operational restoration path.

## Validation

Run the formatter, Ruff, Pyright, import-linter, focused scientific and integration tests, and the complete test suite after changes.
