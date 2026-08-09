# 05 — Experiment Audits

All 24 matrix-declared experiment identities reconcile 1:1 with `experiments/registry.py` declarations
(23 executable via `app/recipes.EXPERIMENT_RECIPES`, 1 anchor-only, 1 suppressed). Full mapping:

| # | Matrix ID | Registry ID | Evidence role | Campaign role | Reachability |
|---|---|---|---|---|---|
| 1 | EXPERIMENT-CONFIRM-NBAIOT-SHARED-VS-LOCAL (anchor) | HISTORICAL_DATP_REPRODUCTION | ANCHOR_REPRODUCTION | anchor-gated | `anchor reproduce/verify/status` |
| 2 | EXPERIMENT-CONFIRM-NBAIOT-SHARED-VS-LOCAL (confirmatory) | SHARED_VS_LOCAL_CONFIRMATION | CONFIRMATORY | MANDATORY | `run experiment` |
| 3 | EXPERIMENT-SUPPORT-SHARED-CONSTRUCTION | SHARED_CONSTRUCTION_SENSITIVITY | SUPPORTIVE | MANDATORY | wired |
| 4 | EXPERIMENT-SUPPORT-QUANTILE-SENSITIVITY | QUANTILE_SENSITIVITY | SUPPORTIVE | MANDATORY | wired |
| 5 | EXPERIMENT-SUPPORT-CONTROLLED-NONIID | CONTROLLED_HETEROGENEITY_SWEEP | MECHANISM | MANDATORY | wired |
| 6 | EXPERIMENT-MECHANISM-GRANULARITY-STABILITY | FAMILY_AND_GROUPED_GRANULARITY | MECHANISM | MANDATORY | wired |
| 7 | EXPERIMENT-MECHANISM-SCORE-GEOMETRY | PER_CLIENT_SCORE_GEOMETRY | MECHANISM | MANDATORY | wired |
| 8 | EXPERIMENT-MECHANISM-HETEROGENEITY-ASSOCIATION | HETEROGENEITY_BENEFIT_ASSOCIATION | MECHANISM | MANDATORY | wired |
| 9 | EXPERIMENT-MECHANISM-THRESHOLD-MOVEMENT | THRESHOLD_MOVEMENT_TRADEOFF | MECHANISM | MANDATORY | wired |
| 10 | EXPERIMENT-BOUNDARY-CALIBRATION-SIZE | CALIBRATION_SIZE_ABLATION | SUPPORTIVE | MANDATORY | wired |
| 11 | EXPERIMENT-VARIANT-FIXED-SHRINKAGE | FIXED_SHRINKAGE_CURVE | SUPPORTIVE | MANDATORY | wired |
| 12 | EXPERIMENT-VARIANT-SIZE-AWARE-SHRINKAGE | SIZE_AWARE_SHRINKAGE | SUPPORTIVE | MANDATORY | wired, UNAVAILABLE outcome (correct — no locked λ(n_k)) |
| 13 | EXPERIMENT-VARIANT-SPLIT-CONFORMAL | LOCAL_CONFORMAL_COVERAGE | SUPPORTIVE | MANDATORY | wired |
| 14 | EXPERIMENT-COMPARATOR-BENIGN-FEDSTATS | FEDERATED_BENIGN_STATISTICS_COMPARISON | THRESHOLD_VARIANT | MANDATORY | wired |
| 15 | EXPERIMENT-METHODS-QUANTILE-BACKBONE | FEDERATED_QUANTILE_ESTIMATION | THRESHOLD_VARIANT | MANDATORY | wired |
| 16 | EXPERIMENT-SENSITIVITY-FEDSTATS-FIXED-K | FIXED_COEFFICIENT_STATISTICS_SENSITIVITY | THRESHOLD_VARIANT | MANDATORY | wired |
| 17 | EXPERIMENT-EXTERNAL-EDGE-BENIGN-EQUITY | EDGE_BENIGN_EQUITY_VALIDATION | EXTERNAL_VALIDATION | MANDATORY | wired |
| 18 | EXPERIMENT-BOUNDARY-CICIOT-FILE-CLIENTS | CICIOT_FILE_CLIENT_BOUNDARY | APPLICABILITY_BOUNDARY | MANDATORY | wired |
| 19 | EXPERIMENT-STRESS-FEDPROX | FEDPROX_ABSORPTION_STRESS_TEST | TRAINING_STRESS_TEST | MANDATORY | wired, separate detector/scores confirmed |
| 20 | EXPERIMENT-STRESS-DITTO | DITTO_ABSORPTION_STRESS_TEST | TRAINING_STRESS_TEST | MANDATORY | wired, separate personalized states confirmed |
| 21 | EXPERIMENT-TEMPORAL-ONE-SHOT | EDGE_ONE_SHOT_RECALIBRATION | TEMPORAL_BOUNDARY | MANDATORY | wired |
| 22 | EXPERIMENT-OPERATIONAL-ALERT-BURDEN | ALERT_BURDEN_TRANSLATION | OPERATIONAL_TRANSLATION | **SUPPRESSED** | correctly no recipe, no traffic-rate evidence exists |
| 23 | EXPERIMENT-OPTIONAL-CLUSTER-MEDIAN | GROUP_MEDIAN_SUPPLEMENT | EXPLORATORY | OPTIONAL | wired |
| 24 | EXPERIMENT-OPTIONAL-EQUITY-INDICES | OPTIONAL_EQUITY_INDICES | EXPLORATORY | OPTIONAL | wired |

## Deep-dive verdicts (adversarial checks, Matrix §76)

- **Detector/preprocessing contamination across threshold policies**: blocked — `ExperimentWorkspace` caches checkpoint/scores/preprocessing once per coordinate; policies only ever receive `ClientBenignCalibrationScores`, never checkpoint/model access.
- **FedAvg↔FedProx↔Ditto artifact collision**: blocked — `TrainingModelId` + `model_coefficient` participate in `ExperimentCoordinate`/`stable_key`; FedAvg requires `coefficient=None`, FedProx/Ditto require non-`None`.
- **Cross-severity (Dirichlet) contamination**: blocked — `controlled_partition_kind`/`dirichlet_concentration` are coordinate fields with `__post_init__` consistency checks (Dirichlet requires concentration, IID forbids it).
- **Centralized↔federated contamination**: blocked — `centralized.py` explicitly calls `reject_federated_preprocessing_for_training()`.
- **Cluster fingerprint altering model-input preprocessing**: blocked — fingerprint `StandardScaler` operates on `[mean,std,skew,p95]` of benign reconstruction-error scores (`thresholds/policies/cluster.py`), a distinct object from the model-input `StandardScaler`/`MinMaxScaler` in `data/preprocessing/`.
- **Anchor gate bypass**: not found — `_enforce_anchor_gate()` gates both `run_campaign()` and `generate_report()`.
- **Pseudo chronology**: not found — temporal split raises rather than synthesizing timestamps; CICIoT2023/N-BaIoT chronology correctly stays `UNAVAILABLE`.
- **Coordinate collision** (raised as HIGH by one discovery subagent): **independently re-verified and downgraded to REJECTED_FALSE_POSITIVE** — `ExperimentCoordinate.stable_key` (`experiments/common/coordinates.py:168-209`) concatenates *every* scientifically relevant dimension (experiment, evidence_role, dataset, population, training_model, seed, split_protocol, preprocessing_protocol, coefficient, threshold_method, metric, temporal_state, quantile, partition/concentration) into the artifact path; coordinates are only ever constructed by the deterministic plan-expansion code from declared registry grids, never from open user input, so two scientifically-different conditions structurally cannot produce the same path. See `08_FINDINGS.md` for disposition.
