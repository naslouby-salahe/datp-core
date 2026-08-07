# Audit: Thresholding, Evaluation, Analysis, Statistics

Scope: `src/datp_core/{thresholding,calibration,evaluation,analysis}` + `protocols/{calibration,statistics,seeds,metrics,populations,experiments}` + `domain/enums.py` + `datasets/*/capabilities.py` + `pipeline/decision/centralized.py` + `evaluation/federated/execution.py`.

## B1-B4 core policies — all dispatchable, construction correct

| Policy | Method enum | Dispatch case | Construction | Journal spec |
|---|---|---|---|---|
| B1 shared | `SHARED_THRESHOLD` | `dispatch.py:120` | `construct_shared_threshold` → `mean_local_threshold(local_quantiles)` (`shared.py:170`, `assignments.py:61`) | mean of local quantiles ✓ |
| B2 local | `LOCAL_THRESHOLD` | `dispatch.py:125` | `construct_local_threshold` → per-client `local_quantile` (`local.py:54`) | local quantile ✓ |
| B3 family | `FAMILY_THRESHOLD` | `dispatch.py:143` → `_family_threshold_or_unavailable` | `construct_family_threshold` → `mean_local_threshold` over family members (`family.py:188`) | family mean ✓ |
| B4 cluster | `CLUSTER_THRESHOLD` | `dispatch.py:145` → `_cluster_threshold_or_unavailable` | `construct_grouped_threshold` → per-cluster `mean_local_threshold` (`cluster.py:293,313`) | cluster mean ✓ |

- B4 fingerprint `FingerprintFeatures(mean, std, skewness, p95)` (`cluster.py:49-53`): mean, `np.std(ddof=0)`, `scipy.stats.skew(bias=True)`, p95 via `exact_empirical_quantile(scores, CANONICAL_QUANTILE=0.95)`. Correct (`cluster.py:246-266`).
- B4 canonical K=3 locked: `LOCKED_CLUSTER_GROUP_COUNT = GroupCount(3)` (`protocols/calibration.py:54`), enforced in `ClusterThresholdProtocol.validate_fingerprint_features` (`calibration.py:158-161`) and used in `construct_grouped_threshold`. StandardScaler + KMeans k-means++ n_init=10 max_iter=300 random_state=42 (`cluster.py:194-201`).
- B4 median aggregation available separately (`CLUSTER_MEDIAN_THRESHOLD_PROTOCOL`, `protocols/calibration.py:237`); only wired for `GROUP_MEDIAN_SUPPLEMENT` experiment (`pipeline/execution/workspace.py:173-188`).

## B0 centralized — implemented separately

- `pipeline/decision/centralized.py` — `POOLED_BENIGN_QUANTILE` (`construct_pooled_benign_quantile`, `exact_pooled_quantile`, lines 268-366). Federated dispatch explicitly rejects centralized methods (`dispatch.py:49-56`). Enforced benign-only via `reject_attack_rows_in_benign_calibration` (line 369). Evaluation is SUPPORTIVE role only, never CONFIRMATORY (`centralized.py:171-175`).

## Benign-only calibration and n_k >= 100

- Benign-only enforced in `calibration/eligibility.py:84` `reject_non_benign_labels` (any attack label raises `LeakageError`), plus `reject_calibration_evaluation_overlap` (line 32) prevents calibration/evaluation row leakage.
- Dispatch re-checks `MINIMUM_BENIGN_SUPPORT` = `CalibrationSize(100)` per eligible client (`dispatch.py:112-118`, `protocols/calibration.py:179`).
- Eligibility gate `decide_eligibility` uses `protocol.minimum_support.fits_within(...)` (`eligibility.py:121`); `CALIBRATION_ELIGIBILITY_PROTOCOL` sets 100 (`protocols/calibration.py:187`).
- Sampling: deterministic nested without-replacement prefixes of one seeded permutation (`calibration/sampling.py`), replicate seed from `(training_seed, population, client_id, replicate_index)`.

## CV(FPR) — ddof=0, no epsilon stabilizer

- `evaluation/population_metrics.py:121` `np.std(array, ddof=0)`; CV = std/mean (line 132). Zero mean → metric marked `UNDEFINED / ZERO_MEAN` (line 127-130), never epsilon-stabilized. TPR CV same (`_coefficient_of_variation`, line 206). Near-zero mean (< 0.01) emits `NEAR_ZERO_MEAN_FPR` warning (`protocols/metrics.py:35`).

## Attack-sensitive metrics unavailable for Edge-IIoTset

- Edge capabilities: `attack_assignment=UNAVAILABLE` (`datasets/edge_iiotset/capabilities.py:50-56`); metrics capability lists TPR/BACC/BIN_MACRO_F1/AUROC as unsupported (line 63).
- `_attack_metric_status` returns UNAVAILABLE when `requires_client_attack_assignment` is False or no client-level assignment (`partitioning/contracts.py:629-647`). SOURCE_DEFINED_SENSOR_GROUPS → `requires_client_attack_assignment=False` (`protocols/populations.py:50-54`).
- At evaluation, `attack_assignment_valid=False` → TPR, BACC, BIN_MACRO_F1, AUROC all `UNAVAILABLE / INVALID_ATTACK_ASSIGNMENT` (`evaluation/client_metrics.py:62-74,94,123`); confusion rejects attack counts when invalid (`evaluation/models.py:171-172`). Pooled macro-F1 also suppressed (`population_metrics.py:236`).

## BCa bootstrap — correct for paired seed deltas

- `analysis/inference/bootstrap/estimation.py` `paired_bca_interval`: deltas = per-seed `left-right` (`wilcoxon.paired_deltas`), estimate = mean delta, resample mean-of-deltas with replacement over seeds (line 147-153), jackknife acceleration (line 205), bias correction via `norm.ppf(proportion_less)` (line 172-174), BCa adjusted quantiles, linear-interp endpoints. 10,000 replicates (`protocols/statistics.py:81`). Degeneracy blocked (identical deltas, degenerate distribution, invalid acceleration/quantiles).
- Confirmatory contrasts validated to the canonical endpoint: SHARED(left) vs LOCAL(right) on N-BaIoT natural devices, metric `FPR_COEFFICIENT_OF_VARIATION`, exact 10-seed cohort, fixed-score provenance enforced (`analysis/inference/bootstrap/validation.py:16-43`).

## Wilcoxon — secondary only

- Decision derives solely from BCa interval (`prepare_confirmatory_analysis`, `preparation.py:192` → `decide_confirmatory`). Wilcoxon signed-rank and matched-pairs rank-biserial are recorded diagnostics only (`preparation.py:222-223`), never gate the decision. Protocol locks two-sided/Pratt/exact-preferred (`protocols/statistics.py:66-74`).

## Confirmatory decision rule — correct

- `analysis/scientific_decision.py:49-81`: lower_bound > 0 → SUPPORTED; upper_bound < 0 → OPPOSITE_DIRECTION; point estimate > 0 with interval crossing zero → DIRECTIONAL_INCONCLUSIVE; else NO_OBSERVED_ADVANTAGE. BLOCKED when interval unavailable/degenerate. Delta = shared − local; SUPPORTED means local lowers CV(FPR). Rationale text matches.

## Shrinkage, B2-conf, B-FedStatsBenign — all implemented

- Fixed shrinkage `LOCAL_GLOBAL_SHRINKAGE`: weights (0, .25, .5, .75, 1), blended = λ·local + (1−λ)·shared, validated exactly (`methods/shrinkage.py:40-48,104-143`). Multi-lambda evaluated as a curve (`evaluation/federated/execution.py:341-379`), local endpoint λ=1 drives the population result.
- Size-aware shrinkage `SIZE_AWARE_SHRINKAGE`: dispatchable, returns typed `ThresholdUnavailableResult` (reason `SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED`) — no declared λ(n_k), correctly not invented (`shrinkage.py:146-154`).
- B2-conf (local conformal) `LOCAL_CONFORMAL_THRESHOLD`: finite-sample rank rule `ceil((n+1)·coverage)`, effective quantile = rank/n, ties counted (`methods/conformal.py`, `quantiles.py:161-193`). Threshold is live/evaluated; its coverage *diagnostic* is pipeline-dead (below).
- B-FedStatsBenign `FEDERATED_BENIGN_STATISTICS`: uses FULL pooled variance = within + between (`methods/federated_statistics.py:226-240`, validated `floats_exactly_equal` at line 71-79). Matched threshold via Gaussian `mean + Φ⁻¹(q)·√var` (`quantiles.py:204-215`). Fixed-coefficient curve (2, 2.5, 3).

## Dead / dormant evaluation diagnostics and metrics

Diagnostic modules are wired into `_evaluate_diagnostics` (`evaluation/federated/execution.py:250-285`) but every pipeline workflow passes empty inputs / None evidence (`pipeline/execution/workspace.py:257-260`, `pipeline/workflows/temporal.py:407-410`, `pipeline/decision/calibration.py:139-140`). No producer exists in `src` for `ThresholdEstimationStageInput`, `ConformalCoverageStageInput`, `CommunicationMessageDiagnostic`, or `ValidatedTrafficRateEvidence`.

- Conformal coverage diagnostic `evaluation/conformal_coverage.py` — `conformal_coverage_inputs=()` everywhere. Metrics `TARGET_COVERAGE`, `ACHIEVED_COVERAGE`, `SIGNED_COVERAGE_ERROR`, `ABSOLUTE_COVERAGE_ERROR` never produced.
- Threshold estimation + sample efficiency `evaluation/threshold_estimation.py` — `threshold_estimation_inputs=()` everywhere; `sample_efficiency_curve` always `()`. Metrics `ABSOLUTE_THRESHOLD_ERROR`, `RELATIVE_THRESHOLD_ERROR`, `SIGNED_ATTAINMENT_ERROR`, `ABSOLUTE_ATTAINMENT_ERROR` never produced.
- Communication `evaluation/communication.py` — `communication_messages=()` everywhere. Metric `COMMUNICATION_BYTES` never produced.
- Alert burden `evaluation/operational.py` + `traffic_rates.py` — `traffic_rate_evidence=None` everywhere; `ALERT_BURDEN_TRANSLATION` experiment declared SUPPRESSED (`protocols/experiments.py:209-212,405-411`). Metric `ALERTS_PER_DAY` never produced.
- These metrics appear in `MetricId` enum but in NO metric-set constant (`evaluation/models.py`, `protocols/metrics.py`), so they can never surface in an evaluation document.
- Live diagnostics: `calibration_size_ablation` (gated to `CALIBRATION_SIZE_ABLATION`, `workspace.py:226-244`) and shrinkage curve (gated to `FIXED_SHRINKAGE_CURVE`).

Analysis paths: mechanism modules (`analysis/mechanisms/{movement,dispersion,divergence,association,clustering,absorption}`) are live via `analyze_confirmatory_campaign` (`pipeline/workflows/confirmatory.py:191-193`). No dead analysis module found; `analysis/adapters/scipy.py`, `multiplicity.py`, `wilcoxon.py`, `bootstrap/*` all exercised by confirmatory/supplementary/temporal preparation.

## Other audit notes

- All 10 federated methods dispatchable; `assert_never` exhaustiveness (`dispatch.py:159`). Capability-gated via `valid_threshold_methods` per population (`partitioning/contracts.py:656-669`); family threshold appended only where family taxonomy SUPPORTED and required.
- `POOLED_SHARED_QUANTILE`, `SAMPLE_WEIGHTED_SHARED_THRESHOLD`, `LOCAL_CONFORMAL_THRESHOLD`, `FEDERATED_BENIGN_STATISTICS`, `LOCAL_GLOBAL_SHRINKAGE` are controls/comparators — not part of the B1-B4 ladder (correctly kept outside the confirmatory endpoint).
- Confirmatory endpoint is only shared-vs-local (B1 vs B2); B3/B4 stay in mechanism/granularity experiments (`FAMILY_AND_GROUPED_GRANULARITY`, `CONTROLLED_HETEROGENEITY_SWEEP`, `GROUP_MEDIAN_SUPPLEMENT`).
- No dead code in thresholding; `publication.py` rebase is a documented no-op pass-through (line 103-108) but not dead — it is part of the publication codec contract.
