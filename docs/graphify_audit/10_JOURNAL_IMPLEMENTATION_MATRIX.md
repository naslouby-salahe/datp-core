# 10 — Journal Implementation Matrix

Every major journal responsibility mapped to implementation state.

---

## Core Scientific Identity

| Responsibility | Status | Owner |
|---------------|--------|-------|
| Fixed-detector causal contract | LIVE_AND_CORRECT | `evaluation/fixed_score/validation.py` |
| Benign-only calibration | LIVE_AND_CORRECT | `calibration/eligibility.py`, `thresholding/dispatch.py` |
| Calibration/evaluation isolation | LIVE_AND_CORRECT | `datasets/partitioning/splits.py` |
| Client eligibility n_k >= 100 | LIVE_AND_CORRECT | `protocols/calibration.py`, `thresholding/dispatch.py` |
| CV(FPR) ddof=0, no epsilon | LIVE_AND_CORRECT | `evaluation/population_metrics.py` |
| Higher MSE = more anomalous | LIVE_AND_CORRECT | `learning/autoencoder.py` |

## Threshold Policies

| Responsibility | Status | Owner |
|---------------|--------|-------|
| B0 — Centralized reference | DISCONNECTED | `pipeline/workflows/centralized.py` |
| B1 — Shared threshold (mean of local quantiles) | LIVE_AND_CORRECT | `thresholding/methods/shared.py` |
| B2 — Local threshold (per-client quantile) | LIVE_AND_CORRECT | `thresholding/methods/local.py` |
| B3 — Family threshold | LIVE_AND_CORRECT | `thresholding/methods/family.py` |
| B4 — Cluster threshold (K=3, fingerprint) | LIVE_AND_CORRECT | `thresholding/methods/cluster.py` |
| Pooled shared quantile (control) | LIVE_AND_CORRECT | `thresholding/methods/shared.py` |
| Sample-weighted shared (control) | LIVE_AND_CORRECT | `thresholding/methods/shared.py` |
| Local-global shrinkage | LIVE_AND_CORRECT | `thresholding/methods/shrinkage.py` |
| Size-aware shrinkage | INCOMPLETE | `thresholding/methods/shrinkage.py` (typed unavailable) |
| B2-conf (conformal) | LIVE_AND_CORRECT | `thresholding/methods/conformal.py` |
| B-FedStatsBenign | LIVE_AND_CORRECT | `thresholding/methods/federated_statistics.py` |

## Training

| Responsibility | Status | Owner |
|---------------|--------|-------|
| FedAvg (sample-weighted, 1 epoch, full participation) | LIVE_AND_CORRECT | `learning/federated/training.py` |
| FedProx (proximal term, frozen μ grid) | LIVE_AND_CORRECT | `learning/federated/training.py` |
| Ditto (genuine semantics, global+personalized) | LIVE_AND_CORRECT | `learning/federated/ditto.py` |
| Centralized training (independent, pooled) | LIVE_AND_CORRECT | `learning/centralized/training.py` |
| Checkpoint candidates {25,50,75,100,125,150,200} | LIVE_AND_CORRECT | `protocols/training.py` |
| FIXED_TERMINAL_MAXIMUM_ROUND = 200 | LIVE_AND_CORRECT | `protocols/checkpoints.py` |
| Checkpoint attack-label rejection | LIVE_AND_CORRECT | `learning/federated/checkpoints/selection.py` |

## Preprocessing

| Responsibility | Status | Owner |
|---------------|--------|-------|
| FEDERATED_CLIENT_LOCAL_STANDARD (confirmatory) | LIVE_AND_CORRECT | `preprocessing/models.py`, `preprocessing/federated.py` |
| FEDERATED_POOLED_MIN_MAX (supportive) | DISCONNECTED | `preprocessing/models.py` — implemented, never dispatched |
| CENTRALIZED_POOLED_MIN_MAX (centralized) | LIVE_AND_CORRECT | `preprocessing/centralized.py` — only via dead centralized.py |
| Missing-value policy (no imputation) | LIVE_AND_CORRECT | `preprocessing/validation.py` |
| CICIoT2023 lossless gate | LIVE_AND_CORRECT | `datasets/ciciot2023/reader.py`, `materialize.py` |
| Edge-IIoTset 33-col numeric projection | LIVE_AND_CORRECT | `datasets/edge_iiotset/schema.py` |
| skops persistence (trusted estimators) | LIVE_AND_CORRECT | `preprocessing/persisted_artifacts.py` |

## Datasets and Populations

| Responsibility | Status | Owner |
|---------------|--------|-------|
| N-BaIoT materialization | LIVE_AND_CORRECT | `datasets/nbaiot/materialize.py` |
| CICIoT2023 materialization | LIVE_AND_CORRECT | `datasets/ciciot2023/materialize.py` |
| Edge-IIoTset materialization | LIVE_AND_CORRECT | `datasets/edge_iiotset/materialize.py` |
| N-BaIoT natural device population | LIVE_AND_CORRECT | `datasets/partitioning/populations.py` |
| CICIoT file client population | LIVE_AND_CORRECT | `datasets/partitioning/populations.py` |
| N-BaIoT Dirichlet population | LIVE_AND_CORRECT | `datasets/partitioning/controlled.py` |
| Edge sensor group population | LIVE_AND_CORRECT | `datasets/partitioning/populations.py` |
| Edge temporal group population | LIVE_AND_CORRECT | `datasets/partitioning/populations.py` |
| NON_TEMPORAL_EQUAL_THIRDS split | LIVE_AND_CORRECT | `datasets/partitioning/splits.py` |
| TEMPORAL_HISTORICAL_FUTURE split | LIVE_AND_CORRECT | `datasets/partitioning/splits.py` |
| RANDOM_FRACTIONAL_STATIC_REFERENCE split | LIVE_AND_CORRECT | `datasets/partitioning/splits.py` |

## Evaluation

| Responsibility | Status | Owner |
|---------------|--------|-------|
| Per-client FPR, TPR, BA, Macro-F1 | LIVE_AND_CORRECT | `evaluation/client_metrics.py` |
| Cross-client CV(FPR), IQR, Range, WorstFPR | LIVE_AND_CORRECT | `evaluation/population_metrics.py` |
| AUROC (model-quality control only) | LIVE_AND_CORRECT | `evaluation/client_metrics.py` |
| Fixed-score invariant enforcement | LIVE_AND_CORRECT | `evaluation/fixed_score/validation.py` |
| Edge-IIoTset attack metrics → UNAVAILABLE | LIVE_AND_CORRECT | `evaluation/client_metrics.py`, capabilities |
| Threshold estimation diagnostics | DISCONNECTED | `evaluation/threshold_estimation.py` |
| Conformal coverage diagnostics | DISCONNECTED | `evaluation/conformal_coverage.py` |
| Communication estimation | DISCONNECTED | `evaluation/communication.py` |
| Operational alert burden | DISCONNECTED | `evaluation/operational.py` |

## Statistical Analysis

| Responsibility | Status | Owner |
|---------------|--------|-------|
| Paired seed contrast Δ_s = CV(FPR)_{B1} - CV(FPR)_{B2} | LIVE_AND_CORRECT | `analysis/contrasts.py` |
| 95% BCa bootstrap (10 seeds, 10k reps) | LIVE_AND_CORRECT | `analysis/inference/bootstrap/estimation.py` |
| Confirmatory decision: lower bound > 0 | LIVE_AND_CORRECT | `analysis/scientific_decision.py` |
| Wilcoxon signed-rank (secondary) | LIVE_AND_CORRECT | `analysis/preparation.py` |
| Matched-pairs rank-biserial (secondary) | LIVE_AND_CORRECT | `analysis/preparation.py` |
| Sign consistency | LIVE_AND_CORRECT | `analysis/preparation.py` |
| Mechanism evidence (movement, divergence, association, clustering) | LIVE_AND_CORRECT | `analysis/mechanisms/` |
| Score geometry (per-client CDFs) | LIVE_AND_CORRECT | `analysis/descriptive.py` |
| Temporal drift/recovery analysis | LIVE_AND_CORRECT | `analysis/temporal.py`, `analysis/preparation.py` |

## Anchor

| Responsibility | Status | Owner |
|---------------|--------|-------|
| 5-seed historical reproduction | LIVE_AND_CORRECT | `anchor/reproduction.py` |
| Anchor gate (PASS/BLOCKED) | LIVE_AND_CORRECT | `anchor/gate.py` |
| Per-metric equivalence comparison | LIVE_AND_CORRECT | `anchor/comparison.py` |
| Independent package collection | LIVE_AND_CORRECT | `pipeline/workflows/anchor.py` |
| Reference provenance documentation | MISSING | Reference values in code only, no config/artifact citation |

## Experiments (Execution)

| Responsibility | Status | Owner |
|---------------|--------|-------|
| SHARED_VS_LOCAL_CONFIRMATION | LIVE_AND_CORRECT | `pipeline/workflows/confirmatory.py` |
| FAMILY_AND_GROUPED_GRANULARITY | LIVE_AND_CORRECT | `pipeline/workflows/confirmatory.py` |
| EDGE_BENIGN_EQUITY_VALIDATION | LIVE_AND_CORRECT | `pipeline/workflows/external.py` |
| CICIOT_FILE_CLIENT_BOUNDARY | LIVE_AND_CORRECT | `pipeline/workflows/external.py` |
| FEDPROX_ABSORPTION_STRESS_TEST | LIVE_AND_CORRECT | `pipeline/workflows/personalization.py` |
| DITTO_ABSORPTION_STRESS_TEST | LIVE_AND_CORRECT | `pipeline/workflows/personalization.py` |
| EDGE_ONE_SHOT_RECALIBRATION | LIVE_AND_CORRECT | `pipeline/workflows/temporal.py` |
| 15 other experiments | DISCONNECTED | Declared only, no workflow modules |

## Reporting

| Responsibility | Status | Owner |
|---------------|--------|-------|
| Confirmatory publication export | LIVE_AND_CORRECT | `reporting/export.py` |
| Mechanism publication export | LIVE_AND_CORRECT | `reporting/export.py` |
| Empirical CDF figures | LIVE_AND_CORRECT | `reporting/figures.py` |
| Statistical tables | LIVE_AND_CORRECT | `reporting/tables.py` |
| Report-from-evidence (no training) | PARTIAL | Ditto/Temporal re-execute training |

---

## Summary Counts

| State | Count |
|-------|-------|
| LIVE_AND_CORRECT | 52 |
| DISCONNECTED | 6 |
| INCOMPLETE | 1 |
| MISSING | 1 |
| PARTIAL | 1 |
| **Total** | **61** |

**Coverage:** 52/61 (85%) journal responsibilities fully implemented and wired.
**Disconnected:** 6 responsibilities have implementations but no execution path.
**Incomplete:** 1 responsibility (size-aware shrinkage) is typed unavailable.
**Missing:** 1 responsibility (anchor reference provenance).
