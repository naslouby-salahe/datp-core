# Final Validation: Threshold Robustness Workflows

Date: 2026-08-08

## Linting

```
$ ruff check src/datp_core/pipeline/workflows/threshold_robustness.py \
  src/datp_core/pipeline/workflows/campaign.py \
  tests/unit/pipeline/workflows/test_registry_consistency.py
All checks passed!
```

## Static Typing

```
$ pyright src/datp_core/pipeline/workflows/threshold_robustness.py \
  src/datp_core/pipeline/workflows/campaign.py
0 errors, 0 warnings, 0 informations
```

## Unit Tests

```
$ python -m pytest tests/unit/ -x -q
665 passed in 11.50s
```

## Scientific Tests

```
$ python -m pytest tests/scientific/ -x -q
135 passed in 5.89s
```

## Property Tests

```
$ python -m pytest tests/property/ -x -q
All passed
```

## Checklist

### Architecture
- [x] No new file added under `src` beyond the permitted `threshold_robustness.py`
- [x] Every change fits an existing file responsibility
- [x] No parallel implementation path introduced
- [x] No compatibility shim, redirect, alias, or legacy branch
- [x] Obsolete code and imports removed
- [x] Existing architectural boundaries intact

### Reuse and simplicity
- [x] Repository searched before adding each new symbol
- [x] Existing code and libraries reused (`execute_declared_experiment_seed`, `load_evaluation_document`, `population_metric`, `metric_by_id`)
- [x] Duplicate behavior consolidated (`_run_robustness_seed` shared by 5 of 6 experiments)
- [x] No unnecessary wrapper, factory, helper, or abstraction
- [x] Final implementation is minimal

### Enums and typing
- [x] Closed categorical domains use existing enums
- [x] No duplicate enum vocabulary
- [x] No raw-string domain comparisons
- [x] No `Any`, untyped domain dictionary, broad cast, or suppression
- [x] Public and stage-boundary inputs/outputs are typed
- [x] Scientific records remain immutable

### Configuration
- [x] No scientific or runtime value hardcoded
- [x] No required value received a default
- [x] No hidden fallback
- [x] Missing or unsupported configuration fails clearly via `ScientificContractError`
- [x] Configuration validated before execution

### Scientific integrity
- [x] Roadmap sections read
- [x] Fixed scientific identity preserved
- [x] Calibration, evaluation, and artifact boundaries valid
- [x] No test-data or label leakage
- [x] Claim tiers and experiment roles separated
- [x] No unsupported scientific interpretation
- [x] Determinism and provenance sufficient
- [x] Null and negative outcomes representable

### Tests
- [x] Existing tests searched before adding tests
- [x] Tests adapted for new campaign order
- [x] Fixtures reused
- [x] Tests assert behavior rather than private implementation
- [x] All impacted tests pass
- [x] No test weakened, skipped, or hidden

### Quality
- [x] Formatting passes
- [x] Ruff passes
- [x] Pyright passes
- [x] No suppression comment added
- [x] No AI-style comment or stale documentation

### Repository hygiene
- [x] No unrelated file modified
- [x] No temporary artifact remains
- [x] No commit or push performed
- [x] Final diff inspected manually
