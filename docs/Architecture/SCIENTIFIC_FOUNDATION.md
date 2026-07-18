# SCIENTIFIC_FOUNDATION

## 1. DATP-Core scientific identity

DATP-Core is a fixed-detector, threshold-calibration-scope study. One
federated-averaging autoencoder is trained once per seed and frozen; only
the *scope* at which the anomaly threshold is calibrated varies across the
core ladder (shared, local, family, cluster). Calibration is benign-only.
The causal question is whether threshold-calibration scope changes deployed
operating-point reliability — per-client false-positive-rate (FPR)
dispersion — across heterogeneous IoT clients, not which detector is best.
AUROC is a detection-quality control, never the thresholding verdict.
"Fairness" means operational, service-level FPR equity across client
devices, and carries no other meaning anywhere in this package (`SCI-08`).

DATP-Core strengthens this identity along five disciplined axes without
becoming a generic FL-IDS benchmark: one external device-partitioned
dataset; a matched-operating-point federated-threshold comparator plus
explicit disclosure of the anomaly-labeled comparator that is out of scope;
two training-side stress tests outside the causal ladder; four threshold
variants deepening the calibration story; and one chronological-split
temporal-recalibration experiment. Six mechanism analyses and a dedicated
tautology-defense appendix support these. The confirmatory endpoint is
singular and unchanged by the extension.

## 2. Anchor relationship

The anchor reproduces the original conference-stage result — client-averaged
shared-threshold versus per-client local-threshold `CV(FPR)` dispersion on
the natural device split — at five paired seeds, against a locked reference
interval of `[0.647, 0.769]` at 95% confidence (width `0.122`). An
`AnchorEquivalenceGate` decision (`PIPELINE_EXECUTION_AND_ARTIFACTS.md §7`)
compares the freshly computed five-seed interval against this reference and
blocks every DATP-Core experiment other than source inspection and
feasibility auditing until it passes. Two conditions block passage and are
recorded, never silently resolved: the reproduced interval shifting
materially toward zero, or the reproduced interval being roughly 20% wider
than the reference width (wider than approximately `0.147`). The ten-seed
confirmatory extension is a separate, later experiment sharing the anchor's
scientific shape; a less-favorable ten-seed result is never suppressed in
favor of the five-seed anchor result (`ANCHOR-03`, `SCI-13`).

## 3. Consolidated scientific invariants

| ID | Invariant |
|---|---|
| `SCI-01` | The detector and its encoder are fixed across the core ladder; one trained state, seeds, and score artifacts feed every ladder member without retraining. |
| `SCI-02` | Federated averaging (one local epoch, full participation) is the training protocol of the causal ladder. |
| `SCI-03` | Threshold-calibration scope is the sole causal variable in the ladder. |
| `SCI-04` | Calibration is benign-only; attack data are evaluation-only. |
| `SCI-05` | The primary operating-point concern is `CV(FPR)`, not global F1, AUROC, or accuracy. |
| `SCI-06` | AUROC is a detection-quality control, never a thresholding verdict. |
| `SCI-07` | Stress-test comparators (heterogeneity-aware aggregation, one model-personalization comparator, a benign-only federated summary threshold) remain outside the causal ladder and never share its experimental control. |
| `SCI-08` | "Fairness" means operational, service-level FPR equity across client devices, stated once, enforced everywhere. |
| `SCI-09` | Dynamic thresholding, poisoning, formal privacy, deployment/hardware profiling, streaming drift, Byzantine-robust federated conformal prediction, and fleet-scale (K > 100) validation have no type, enum member, or port anywhere in this design. |
| `SCI-10` | The eligible-client population is derived once per paired comparison from shared calibration lineage and reused unchanged by every compared policy. |
| `SCI-11` | Checkpoint selection uses only natural-device-split evidence; no attack label, held-out AUROC, external-dataset result, stress-test result, or downstream threshold outcome may influence it. |
| `SCI-12` | No test-set-driven or result-driven scientific setting selection occurs anywhere; every scientific value is pre-specified before result freeze. |
| `SCI-13` | Null, mixed, and opposite results are reportable and pre-committed to fallback wording; a less-favorable extended result never suppresses a more-favorable preliminary one. |

## 4. Research questions and evidence roles

| RQ | Role | Question |
|---|---|---|
| RQ1 | `CONFIRMATORY` | Does threshold-calibration scope change per-client FPR disparity on the natural device split, and what TPR/Macro-F1 trade-off does it impose? |
| RQ2 | `MECHANISM` | Do cluster/family thresholds recover part of the local-threshold benefit while improving the fairness-versus-sample-efficiency and stability trade-off? |
| RQ3 | `SUPPORTIVE` | How robust are local thresholds under small benign calibration windows, and can shrinkage and a size-aware fallback stabilize them? |
| RQ4 | `MECHANISM` (backbone) | Framed as distributed quantile estimation, do federated statistical comparators explain or challenge the threshold-scope effect? |
| RQ5 | `STRESS_TEST` | Does threshold-only personalization remain useful against aggregation-side and model-side personalization stress tests? |
| RQ6 | `EXTERNAL_VALIDATION` / `BOUNDARY` | Does the effect generalize to an independent device-partitioned dataset, across heterogeneity severity, and where does it fail? |

Evidence roles used throughout this package: `ANCHOR`, `CONFIRMATORY`,
`SUPPORTIVE`, `EXTERNAL_VALIDATION`, `STRESS_TEST`, `MECHANISM`, `BOUNDARY`,
`EXPLORATORY`, `FUTURE_WORK`, `FORBIDDEN` — ten members, matching the prior
architecture's `ExperimentRole` exactly plus `ANCHOR`. Publication tier
numbers (Tier 1–9) survive only as `tier` traceability metadata on
`ExperimentIdentity`; only `CONFIRMATORY` may carry `TIER_1`, and no other
role may (`SCI-14`).

`EvidenceRole` is not the only classification an experiment carries. A
separate field, `execution_status` (`MANDATORY`, `OPTIONAL`, `SUPPRESSED`,
`REJECTED`, `FUTURE`; `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §2`), answers
a different question — is the study required to run this at all — and is
never collapsed into `evidence_role`. For example,
`federated_quantile_estimation_backbone` is `evidence_role = MECHANISM,
execution_status = OPTIONAL`: it is scientifically a mechanism analysis,
and it is optional to execute; neither fact substitutes for the other. A
third vocabulary — `LOCKED`, `DESIGNED_NOT_IMPLEMENTED`, `BLOCKED`,
`DEFERRED`, `OUT_OF_SCOPE`, `REJECTED`, `SUPPRESSED`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1`) — is a third, still
distinct thing: it tags an *architectural design commitment* in this
package (a type, a rule, a field), never an experiment. `REJECTED` and
`SUPPRESSED` appear in both `ExecutionStatus` and the package-wide status
vocabulary because both objects can genuinely be rejected or suppressed,
but an experiment's `execution_status` and a design commitment's package
status are never read from the same field.

## 5. Complete dataset and evaluation-setting model

No `Regime` type drives control flow anywhere in `domain` or `application`
— no stage, port, planner branch, or artifact key is ever keyed on it. A
dataset evaluation setting is fully expressed by composing a dataset, a
client construction, a split definition, and — where applicable — a
heterogeneity or temporal protocol
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.1`). A closed `Regime` enum
does still exist, but only as a **derived, publication-facing label**
computed from an already-resolved composition, for citing the roadmap's own
five letters — never as a constructor input, and never checked in any
`if`/`match` that decides scientific or execution behavior
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.1`, `NAME-01`). Every setting
the roadmap names is represented below, executable or not:

| Semantic setting | Composition | Roadmap letter | Status |
|---|---|---|---|
| `natural_device_evaluation` | N-BaIoT, `PhysicalDeviceClients` (K = 9) | A | `LOCKED`, confirmatory + anchor |
| `controlled_heterogeneity_evaluation` | N-BaIoT, `DirichletPartitionedClients` (K = 20, α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}) | C | `LOCKED`, supportive |
| `file_pseudo_client_evaluation` | CICIoT2023, `DatasetFilePseudoClients` (63 pseudo-clients, feature count d = 39 pending re-verification against the actual processed artifact) | B-a | `LOCKED`, boundary only; never generalized beyond itself |
| `device_mac_repartition` | CICIoT2023, a device/MAC-scoped client construction | B-b | `REJECTED` — the available CSV artifact lacks MAC, device, IP, capture-source, and timestamp columns; no pseudo-client substitute and no PCAP-reprocessing branch exist |
| `chronological_probe_ciciot2023` | CICIoT2023, a genuine-timestamp temporal protocol | — | `REJECTED` — no timestamp column and no file/row/merge/directory pseudo-time substitute |
| `external_device_validation` | Edge-IIoTset, `ExternalDeviceOrGroupClients`, device-versus-group resolved by a first-principles feasibility audit (target K ∈ {6, 15}; requires n_k ≥ 100 for ≥ 90% of clients) | D | `LOCKED`, external validation; feasibility-gated |
| `chronological_recalibration_evaluation` | `external_device_validation` composition, chronological 70/30 split, frozen-versus-one-shot recalibration | D-temporal | `LOCKED`, boundary/exploratory; feasibility- and timestamp-gated |

A rejected setting is a non-executable `RejectionRecord`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §5`), never a planner branch, a
threshold-construction union member, or a configuration variant.

## 6. Threshold and comparator nomenclature

Publication codes (`B0`–`B4`, `B-FedStatsBenign`, `B-LaridiFaithful`) appear
only as `roadmap_reference` metadata; none is an enum identity, YAML
discriminator, method name, class name, file name, branch condition, or
artifact identity (`NAME-03`).

| Semantic identity | Roadmap code | Construction | Ladder membership |
|---|---|---|---|
| `SharedThreshold(construction=MEAN)` | B1 | client-averaged mean of local benign quantiles | core ladder |
| `SharedThreshold(construction=POOLED)` | B1-pool | pooled shared quantile | supportive variant |
| `SharedThreshold(construction=WEIGHTED)` | B1-wt | sample-weighted shared quantile | supportive variant |
| `LocalThreshold` | B2 | per-client benign quantile | core ladder; confirmatory comparator |
| `FamilyThreshold` | B3 | device-family mean of member local quantiles; requires an authorized taxonomy | core ladder; mechanism baseline |
| `ClusterThreshold(aggregation=MEAN)` | B4 | k-means-cluster (K = 3 canonical) mean of member local quantiles over a fixed four-scalar fingerprint `[mean(error), std(error), skew(error), p95(error)]` | core ladder; cluster mechanism |
| `ClusterThreshold(aggregation=ROBUST_MEDIAN)` | — | canonical B4 assignment, median instead of mean member aggregation | optional supplementary variant; cannot replace canonical B4 |
| `LocalGlobalShrinkageThreshold` | τ-shrink / LGS | `τ_k(λ) = λ·τ_k,local + (1−λ)·τ_global`, λ ∈ {0, .25, .5, .75, 1} | supportive threshold variant |
| `CalibrationSizeAwareFallbackThreshold` | — | size-dependent `λ(n_k)` replacing the ordinary hard `n_min = 100` fallback for its own declared cells | supportive threshold variant |
| `ConformalLocalThreshold` | B2-conf | split- or federated-conformal local threshold at marginal coverage `1 − α`, α = 0.05 | supportive threshold variant; closes the tautology critique |
| `FederatedSummaryStatisticThreshold` | `B-FedStatsBenign` | benign-only client-disclosed `(n_k, mean_k, variance_k)`; sample-weighted global mean; full pooled variance including the between-client mean-shift term; matched-exceedance candidate grid `τ(k) = µ_global + k·σ_global`, k ∈ {0.00 … 5.00}, ties broken toward larger k | comparator primitive; matched, non-ladder |
| `FederatedSummaryStatisticThreshold` (fixed-k) | fixed-k sensitivity | the same construction evaluated at fixed k ∈ {2.0, 2.5, 3.0} | supplementary sensitivity only; never the primary comparator result |
| `CentralizedPooledThreshold` | B0 | centralized pooled-benign quantile from a separately trained centralized detector | non-ladder reference; never fused with federated-averaging scores |
| — (disclosure only, non-executable) | `B-LaridiFaithful` | anomaly-labeled Laridi-style reproduction | `OUT_OF_SCOPE` — violates the benign-only calibration contract; named disclosure record only |

Every remaining threshold construction requirement — that B1 and B3 use
unweighted arithmetic means of eligible local quantiles, that B4 requires
canonical K = 3 and never a q-mutated fingerprint, that `B-FedStatsBenign`
never uses a simplified variance formula or a caller-controlled tie rule,
and that fixed-k can never become primary — is a structural algorithm rule
of the corresponding discriminated variant, never a configurable boolean
(`SCI-15`–`SCI-18`, `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §2`).

## 7. Complete experiment catalogue

Every experiment below carries a semantic slug and, where the roadmap names
it, a `roadmap_reference`. The roadmap identifier is source-traceability
metadata only and never an internal control-flow value (`NAME-04`).

### 7.1 Anchor and confirmatory

| Semantic slug | Roadmap ref | Role; tier | Status | Dataset setting | Threshold pair |
|---|---|---|---|---|---|
| `anchor_reproduction` | — | `ANCHOR` | `MANDATORY` | `natural_device_evaluation` | `SharedThreshold(MEAN)` vs `LocalThreshold`, 5 paired seeds |
| `confirmatory_threshold_scope_effect` | E-C1 | `CONFIRMATORY`; `TIER_1` | `MANDATORY` | `natural_device_evaluation` | `SharedThreshold(MEAN)` vs `LocalThreshold`, 10 paired seeds |

### 7.2 Supportive and mechanism

All `MANDATORY` unless noted.

| Semantic slug | Roadmap ref | Role; tier | Dataset setting | Threshold construction(s) |
|---|---|---|---|---|
| `shared_threshold_construction_sensitivity` | E-S1 | `SUPPORTIVE`; `TIER_2` | `natural_device_evaluation` | `SharedThreshold(MEAN\|POOLED\|WEIGHTED)`, `LocalThreshold` |
| `threshold_quantile_sensitivity` | E-S2 | `SUPPORTIVE`; `TIER_2` | `natural_device_evaluation` (+ external) | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`; q ∈ {.90, .95, .975, .99} |
| `controlled_heterogeneity_response` | E-S3 | `SUPPORTIVE`; `TIER_2` | `controlled_heterogeneity_evaluation` | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold` across α |
| `cluster_family_threshold_granularity_and_stability` | E-M1 | `MECHANISM`; `TIER_5` (+`TIER_7` exploratory at K ≠ 3) | `natural_device_evaluation` (+ external where feasible) | `SharedThreshold`, `LocalThreshold`, `FamilyThreshold`, `ClusterThreshold`; granularity comparison and adjusted-Rand stability as two evaluation definitions of one experiment |
| `cluster_fingerprint_feature_ablation` | E-M2 | `MECHANISM`; `TIER_5`/`TIER_7` | `natural_device_evaluation` | `ClusterThreshold` over fingerprint feature subsets, plus the all-four fingerprint |
| `client_score_distribution_mechanism_analysis` | E-M3 | `MECHANISM`; `TIER_5` | `natural_device_evaluation` | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`; per-client benign/attack score-distribution overlays, every client |
| `heterogeneity_threshold_benefit_association` | E-M4 | `MECHANISM`; `TIER_5` | `natural_device_evaluation` / `controlled_heterogeneity_evaluation` (+ external) | none (distributional divergence regressed against gain) |
| `threshold_shift_detection_tradeoff` | E-M5 | `MECHANISM`; `TIER_5` | `natural_device_evaluation` | `SharedThreshold` → `LocalThreshold` shift, every client |
| `calibration_window_size_stability` | E-V1 | `BOUNDARY`; `TIER_6` (RQ3) | `natural_device_evaluation`, subsampled calibration n ∈ {50, 100, 250, 500, 1000, 5000} | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`, `CalibrationSizeAwareFallbackThreshold` |
| `local_global_threshold_shrinkage` | E-V2 | `SUPPORTIVE`; RQ3 | `natural_device_evaluation` | `LocalGlobalShrinkageThreshold`, λ ∈ {0, .25, .5, .75, 1} |
| `conformal_local_threshold_coverage` | E-V3 | `SUPPORTIVE`, Tier-1 tautology defense; non-confirmatory | `natural_device_evaluation` (+ external) | `ConformalLocalThreshold`, α = 0.05 |

### 7.3 External validation and stress tests

All `MANDATORY`.

| Semantic slug | Roadmap ref | Role; tier | Dataset setting | Threshold construction(s) |
|---|---|---|---|---|
| `external_device_dataset_validation` | E-X1 | `EXTERNAL_VALIDATION`; `TIER_3` | `external_device_validation` | `SharedThreshold`, `LocalThreshold`, `FamilyThreshold`, `ClusterThreshold`, `FederatedSummaryStatisticThreshold`, quantile sensitivity |
| `fedprox_aggregation_stress_test` | E-T1 | `STRESS_TEST`; `TIER_4` | `natural_device_evaluation` + `external_device_validation` | core ladder, under `FederatedProxTraining`, µ ∈ {0.001, 0.01, 0.1} |
| `model_personalization_absorption_test` | E-T2 | `STRESS_TEST`; `TIER_4` | `natural_device_evaluation` + `external_device_validation` | `SharedThreshold`, `LocalThreshold`, under the authorized personalization comparator |
| `federated_summary_threshold_comparison` | E-T3 | `STRESS_TEST` (comparator); `TIER_4` | `natural_device_evaluation` + `external_device_validation` | `LocalThreshold` vs `FederatedSummaryStatisticThreshold`, between-ratio diagnostic |
| `chronological_recalibration_evaluation` | E-B1 | `BOUNDARY`; `TIER_6` | `chronological_recalibration_evaluation` | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`, frozen vs one-shot recalibration |
| `operational_alert_burden_analysis` | E-O1 | `SUPPORTIVE`; `TIER_5` (RQ1 support) | `natural_device_evaluation` / `external_device_validation` | `SharedThreshold`, `LocalThreshold`; requires validated traffic-rate evidence |

### 7.4 Optional (`execution_status = OPTIONAL` for every row below)

| Semantic slug | Roadmap ref | Role; tier | Purpose |
|---|---|---|---|
| `federated_quantile_estimation_backbone` | E-Q1 | `MECHANISM`; `TIER_7` | Exact centralized oracle vs local vs pooled/weighted quantile estimation error and FPR-target attainment |
| `robust_cluster_median_sensitivity` | E-Q2 | `EXPLORATORY`; `TIER_7` | `ClusterThreshold(ROBUST_MEDIAN)` outlier robustness |
| `operating_point_equity_suite` | E-Q3 | `EXPLORATORY` | Jain index, Gini coefficient alongside `CV(FPR)`, never replacing it |
| `secondary_confidence_intervals_and_effect_sizes` | E-Q4 | `EXPLORATORY` | Bootstrap CIs, full Wilcoxon signed-rank, Cliff's delta, descriptive only |
| `fixed_parameter_comparator_sensitivity` | E-Q5 | `EXPLORATORY` | Fixed-k `FederatedSummaryStatisticThreshold` sensitivity, never primary |
| `communication_storage_cost_analysis` | E-Q6 | `SUPPORTIVE` | Byte-level communication/storage estimates for `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`; estimated values always labeled `ESTIMATED`, never rendered as measured |

Every row above carries a genuine `EvidenceRole` (`MECHANISM`,
`EXPLORATORY`, or `SUPPORTIVE`, matching the roadmap's own classification
of each item) and, separately, `execution_status = OPTIONAL` — the two
fields are never merged into one invented role.

### 7.5 Non-ladder reference and boundary

| Semantic slug | Roadmap ref | Role; status | Notes |
|---|---|---|---|
| `centralized_pooled_reference` | B0 | `SUPPORTIVE`; `MANDATORY` wherever another experiment cites it | Own centralized training, checkpoint, calibration, test, and threshold identity chain; never fused with federated-averaging artifacts (`ANCHOR-04`, `ART-06`); supports the "not a mean-construction artifact" reasoning rather than bearing its own tier |
| `file_pseudo_client_applicability_boundary` | `B_A_APPLICABILITY_BOUNDARY` | `BOUNDARY`; `TIER_6`; `MANDATORY` | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold` on `file_pseudo_client_evaluation`; boundary report only, never generalized to a natural-device claim |

### 7.6 Rejected, suppressed, and future work

| Semantic slug | Roadmap ref | Status | Reason |
|---|---|---|---|
| `device_mac_repartition` (see §5) | E-R1 | `REJECTED` | No MAC/device/IP/capture-source/timestamp metadata; no pseudo-client substitute |
| `chronological_probe_ciciot2023` (see §5) | E-R2 | `REJECTED` | No timestamp column; no pseudo-time substitute |
| `fedbn_encoder_variant` | E-R3 | `REJECTED` | The encoder has no batch normalization; adding it breaks the fixed-encoder identity |
| `laridi_faithful_anomaly_labeled_disclosure` | E-R4 | `OUT_OF_SCOPE` | Requires anomaly-labeled calibration; violates the benign-only contract; disclosure only |
| `membership_inference_leakage_probe` | E-R5 | `REJECTED` | No established IoT-threshold leakage literature; qualitative bounded disclosure only |
| `streaming_drift_detection` | E-R6 | `REJECTED` (scope) | Dynamic DATP future work |
| `byzantine_robust_federated_conformal` | E-R7 | `REJECTED` (scope) | Separate defense-line research, not this program |
| `broad_personalized_fl_benchmark` | E-R8 | `REJECTED` | Exceeds the three-stress-test-family limit |

Future work, named but never executed: dynamic per-client thresholds
(Dynamic DATP); conformal DATP beyond the single conformal seed; formal
privacy (DP or secure aggregation); fleet-scale (K > 100) validation; a
standalone model-versus-threshold-personalization spin-off with full cost
accounting; further aggregation-strategy sensitivity; hardware or edge
profiling. Each carries status `DEFERRED` or `OUT_OF_SCOPE`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1`) and has no executable type
anywhere in this design.

## 8. Experiment authorization

A generic YAML combination cannot produce a scientifically unauthorized
experiment. Every experiment is either (a) an `ExperimentDefinition` fully
resolved from a named `configs/experiments/` document with every field
explicit, or (b) a concrete `ExperimentCell` expanded from a declared sweep
dimension inside such a document. There is no separate "authorized profile"
layer duplicating the resolved definition's fields: authorization is
enforced by construction validators on the closed discriminated unions
themselves (`ThresholdConstruction`, `ClientConstruction`,
`TrainingProtocol`) plus cross-field validators that reject, at
configuration-resolution time, a confirmatory identity paired with a
non-`natural_device_evaluation` dataset, an unpaired or wrong-count seed
cohort, an extra threshold construction on the confirmatory pair, attack
data reachable from a calibration split, an unauthorized personalization
strategy on a core-ladder detector, an inverted metric direction, a
non-`TIER_1` confirmatory tier, or a checkpoint-selection rule other than
the one locked rule (`CFG-08`, `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §5`).

## 9. Null-result and opposite-result discipline

Every claim above `EXPLORATORY` carries pre-committed fallback wording for
strong-positive, weak-positive, mixed, null, opposite, feasibility-rejected,
and suppressed outcomes, selected only after result freeze
(`EVALUATION_REPORTING_AND_PROVENANCE.md §6`). The confirmatory endpoint is
never suppressed under any outcome: if its ten-seed BCa interval includes
zero, the null result and the failure to exclude zero are reported as the
main result, and the earlier five-seed figure is relabeled preliminary
(`SCI-13`, `ANCHOR-03`).

## 10. Roadmap-to-architecture traceability

Every roadmap section maps onto this package as follows: identity and
invariants (roadmap §§1–3) → this file §§1–3; nomenclature (§4) → §6; claim
hierarchy and research questions (§§5–6) → §4; regime table (§7) → §5;
module integration (§8) → the mechanism and stress-test rows of §7; the
experiment matrix (§9) → §7 in full; statistics (§10) →
`EVALUATION_REPORTING_AND_PROVENANCE.md §5`; temporal outcomes (§11) →
`EVALUATION_REPORTING_AND_PROVENANCE.md §6.5`; fallback wording (§12) →
`EVALUATION_REPORTING_AND_PROVENANCE.md §6`; the reviewer register (§13) is
answered structurally throughout this package rather than reproduced, since
every listed objection maps to a named experiment or a locked rule already
covered above; checklists (§14) → the conformance checklist in
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §9`; scope boundaries (§16) →
`SCI-09` and the rejected-experiment table in §7.6; implementation planning
(§17) → `DOMAIN_AND_APPLICATION_ARCHITECTURE.md` and
`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md` in full.
