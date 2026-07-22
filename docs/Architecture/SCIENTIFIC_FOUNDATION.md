# SCIENTIFIC_FOUNDATION

## Purpose

Define scientific identity, datasets, thresholds, experiments, claim gates,
and scope boundaries.

## Authoritative for

Scientific meaning and publication disposition.

## Not authoritative for

Configuration composition, runtime execution, persistence, or rendering.

> Configuration alignment: executable dataset setup names, experiment names,
> and numeric protocol values are owned by
> `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md`. This document provides the
> scientific rationale; where an older conceptual label differs, the catalogue
> and the YAML configuration take precedence.

## 1. DATP-Core scientific identity

DATP-Core is a fixed-encoder, fixed-federated-model, threshold-calibration-scope
study. One federated-averaging autoencoder is trained once per seed and
frozen; only the *scope* at which the anomaly threshold is calibrated
varies across the core ladder (shared, local, family, cluster). Calibration
is benign-only. The causal question is whether threshold-calibration scope
changes deployed operating-point reliability — per-client
false-positive-rate (FPR) dispersion — across heterogeneous IoT clients,
not which model is best. AUROC is a detection-quality control, never the
thresholding verdict.
"Fairness" means operational, service-level FPR equity across client
devices, and carries no other meaning anywhere in this package (`SCI-08`).

DATP-Core strengthens this identity along five disciplined axes without
becoming a generic FL-IDS benchmark: one external sensor-group-partitioned
dataset; a matched-operating-point federated-threshold comparator plus
explicit disclosure of the anomaly-labeled comparator that is out of scope;
two training-side stress tests outside the causal ladder; four threshold
variants deepening the calibration story; and one chronological-split
temporal-recalibration experiment. Six mechanism analyses and a dedicated
tautology-defense appendix support these. The confirmatory endpoint is
singular and unchanged by the extension. The external sensor-group-partitioned and
chronological cells are **executable for benign operating-point equity** —
cross-client false-positive dispersion (`CV(FPR)`, the primary external
concern) — because held-out benign rows are recoverable for all ten
source-grounded sensor groups (eligible-benign coverage 1.0); only their
per-client attack-sensitive metrics are unavailable, because Edge-IIoTset
attack traffic is confined to the single attacker subnet (`§5`, `§5.1`). The
confirmatory Regime A endpoint is unaffected.

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

The anchor is a *distinct historical materialization*, not the DATP-Core
pipeline re-labeled. It uses training seeds 0–4, per-client train-split
standardization, Adam at 0.001, batch size 256, one local epoch, and full
participation. It trains at most 150 rounds and, from round 40, selects the
first round whose trailing ten FedAvg-weighted benign-validation losses meet
the locked relative-change rule `abs(loss[r-9] - loss[r]) / abs(loss[r-9]) <
0.005`; a zero start loss is treated as relative change zero. If none
qualifies, it selects the 150-round cap and saves exactly that one final
checkpoint. Its five-seed interval is the 95% percentile bootstrap with
10,000 resamples and seed 42. DATP-Core instead uses the 200-round scheduled
grid and ten-seed declared BCa procedures. The two do not share a terminal
autoencoder state, preprocessing identity, or checkpoint-selection rule.

## 3. Consolidated scientific invariants

| ID | Invariant |
|---|---|
| `SCI-01` | The model and its encoder are fixed across the core ladder; one trained state, seeds, and score artifacts feed every ladder member without retraining. |
| `SCI-02` | Federated averaging (one local epoch, full participation) is the training profile of the causal ladder. |
| `SCI-03` | Threshold-calibration scope is the sole causal variable in the ladder. |
| `SCI-04` | Calibration is benign-only; attack data are evaluation-only. |
| `SCI-05` | The primary operating-point concern is `CV(FPR)`, not global F1, AUROC, or accuracy. |
| `SCI-06` | AUROC is a detection-quality control, never a thresholding verdict. |
| `SCI-07` | Stress-test comparators (heterogeneity-aware aggregation, one model-personalization comparator, a benign-only federated summary threshold) remain outside the causal ladder and never share its experimental control. |
| `SCI-08` | "Fairness" means operational, service-level FPR equity across client devices, stated once, enforced everywhere. |
| `SCI-09` | Dynamic thresholding, poisoning, formal privacy, deployment/hardware profiling, streaming drift, backdoor attacks, evasion attacks, Byzantine-robust federated conformal prediction, and fleet-scale (K > 100) validation have no type, enum member, or port anywhere in this design. |
| `SCI-10` | The eligible-client population is derived once per paired comparison from shared calibration lineage and reused unchanged by every compared policy. |
| `SCI-11` | Checkpoint selection uses only natural-device-split evidence; no attack label, held-out AUROC, external-dataset result, stress-test result, or downstream threshold outcome may influence it. |
| `SCI-12` | No test-set-driven or result-driven scientific setting selection occurs anywhere; every scientific value is pre-specified before result freeze. |
| `SCI-13` | Null, mixed, and opposite results are reportable and pre-committed to fallback wording; a more-favorable preliminary result never suppresses a less-favorable extended result (the extended, larger-seed result is always reported even when it is the less favorable of the two). |

## 4. Research questions and evidence roles

| RQ | Role | Question |
|---|---|---|
| RQ1 | `CONFIRMATORY` | Does threshold-calibration scope change per-client FPR disparity on the natural device split, and what TPR/Macro-F1 trade-off does it impose? |
| RQ2 | `MECHANISM` | Do cluster/family thresholds recover part of the local-threshold benefit while improving the fairness-versus-sample-efficiency and stability trade-off? |
| RQ3 | `SUPPORTIVE` | How robust are local thresholds under small benign calibration windows, and can shrinkage and a size-aware fallback stabilize them? |
| RQ4 | `MECHANISM` (backbone) | Framed as distributed quantile estimation, do federated statistical comparators explain or challenge the threshold-scope effect? |
| RQ5 | `STRESS_TEST` | Does threshold-only personalization remain useful against aggregation-side and model-side personalization stress tests? |
| RQ6 | `EXTERNAL_VALIDATION` / `BOUNDARY` | Does the effect generalize to an independent sensor-group-partitioned dataset, across heterogeneity severity, and where does it fail? |

Evidence roles used throughout this package (`domain/catalogue.py:EvidenceRole`): `ANCHOR`, `CONFIRMATORY`,
`SENSITIVITY`, `EXPLORATORY`, `STRESS_TEST`, `COMPARATOR`, `MECHANISM`,
`SUPPORTIVE`, `BOUNDARY`, `EXTERNAL_VALIDATION` — ten members, every role an *executable* experiment can
carry. The prior architecture's `ExperimentRole` also listed `FUTURE_WORK`
and `FORBIDDEN`; neither names an executable experiment — a future-work or
forbidden item has no `configs/experiments.yaml` document and never resolves into
a `RunDefinition`, so it is not an evidence role at all. A named future-work
item is a `CatalogueDisposition.FUTURE_WORK` entry (`§7.6`), and a forbidden
claim is a manuscript-discipline rule (roadmap Tier 9), never an experiment.
This narrowing mirrors `RunRequirement`, which for the identical reason keeps
only `MANDATORY`/`CONDITIONAL`/`EXPLORATORY`/`OPTIONAL` and routes rejected and future
entries to `CatalogueDisposition`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §4`). Publication tier numbers
(Tier 1–9) survive only as `tier` traceability metadata on
`ExperimentIdentity`; only `CONFIRMATORY` may carry `TIER_1`, and no other
role may (`SCI-14`, defined with `SCI-15`–`SCI-19` in `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §2`).

`EvidenceRole` is not the only classification an experiment carries.
`RunRequirement` (`domain/catalogue.py:RunRequirement`: `MANDATORY`, `CONDITIONAL`, `EXPLORATORY`, `OPTIONAL`) answers the
different executable question—whether the study is required to run—and is
never collapsed into `evidence_role`. It is a field of `ExperimentIdentity`
only; it is never carried by an individual
`EvaluationDefinition` or `AnalysisDefinition` inside an experiment, so an
attached evaluation such as the `federated_summary_comparator`'s
fixed-k sensitivity axis (`§7.3`) is scientifically a distinct, supplementary
evaluation while sharing its owning experiment's single
`run_requirement = MANDATORY` — "supplementary, never primary" is a fact
about evidentiary weight, not a second run-requirement value. Rejected,
out-of-scope, and future catalogue entries use `CatalogueDisposition`. A
third vocabulary — `LOCKED`, `DESIGNED_NOT_IMPLEMENTED`, `BLOCKED`,
`DEFERRED`, `OUT_OF_SCOPE`, `REJECTED`, `SUPPRESSED`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1`) — is a third, still
distinct thing: it tags an *architectural design commitment* in this
package (a type, a rule, a field), never an experiment. `SUPPRESSED` may
appear in both run requirement and package vocabulary with their respective
meanings, but the fields are never conflated.

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
| `natural_devices` / `anchor_natural_devices` | N-BaIoT, foldered physical-device clients (K = 9) | A | Journal (`datp_core`) and distinct historical anchor (`anchor`) materializations. |
| `controlled_heterogeneity_evaluation` | N-BaIoT, `DirichletPartitionedClients` (K = 20, α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}) | C | `LOCKED`, supportive |
| `file_pseudo_client_evaluation` | CICIoT2023, `DatasetFilePseudoClients` (63 pseudo-clients, matching the `MERGED_CSV/` file count exactly; feature count d = 39 manually corroborated against the mounted corpus, `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §11.2` — the `processed_feature_verification` audit's own run remains the citable gate) | B-a | `LOCKED`, boundary only; never generalized beyond itself |
| `device_mac_repartition` | CICIoT2023, a device/MAC-scoped client construction | B-b | `REJECTED` — the available CSV artifact lacks MAC, device, IP, capture-source, and timestamp columns; no pseudo-client substitute and no PCAP-reprocessing branch exist |
| `chronological_probe_ciciot2023` | CICIoT2023, a genuine-timestamp temporal protocol | — | `REJECTED` — no timestamp column and no file/row/merge/directory pseudo-time substitute |
| `sensor_groups` | Edge-IIoTset, ten normal-traffic group folders | D | Static benign operating-point equity. Folder identity is authoritative; endpoint resolution is diagnostic/provenance only. Per-client attack-sensitive metrics are unavailable. |
| `chronological_sensor_groups` | Edge-IIoTset nine-folder temporal population and matched nine-folder static control; Modbus excluded only for unusable timestamps; chronological 55/15/10/20 split | D-temporal | Benign temporal operating-point equity, frozen versus one-shot recalibration, and typed attack-sensitive unavailability. |

A rejected setting is a non-executable `RejectionRecord`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §5`), never a planner branch, a
threshold-construction union member, or a configuration variant. Regime D and
D-temporal are neither rejected nor wholly suppressed: they are
**capability-scoped** cells, executable for benign operating-point equity
(`CV(FPR)` and its benign-derivable companions) and carrying a typed
`per_client_attack_detection_metrics: unavailable` limitation
(`attack_traffic_confined_to_subnet_zero`) for the metrics that require
per-client attack rows. The benign external and temporal evidence is produced;
the attack-sensitive per-client evidence is rendered as a typed unavailability,
never fabricated or deleted. The Regime A confirmatory claim is unaffected.

### 5.1 Feasibility audit ordering (no circular dependency)

`external_sensor_group_validation`'s `ExternalSensorGroupClients` sensor-group
granularity is never chosen dynamically inside a scientific run, and a resolved scientific
`DataDefinition` never refers to a feasibility artifact its own run has not
yet produced. The required sequence is:

```text
source inspection (edge_iiotset_source_inspection, non-scientific)
  → feasibility audit (edge_iiotset_feasibility_audit, non-scientific)
    → persisted FEASIBILITY_RESULT (benign sensor-group authorization decision, target
      K ∈ {6, 15}, n_k ≥ 100 for ≥ 90% of clients)
      → explicit human-authorized ExternalSensorGroupClients document
        (fixed to the benign sensor-group partition before resolution, never a
        runtime choice)
        → scientific external_sensor_group_validation configuration resolution
          (references the audit's FEASIBILITY_RESULT by `ArtifactRef` as
          provenance only)
          → scientific external_sensor_group_validation execution
```

The feasibility audit is its own prior, non-scientific run — `evidence_role`
does not apply to it and it carries no `tier`; it exists only to produce a
persisted `FEASIBILITY_RESULT`. `FEASIBILITY_AUDIT` never appears in the
planned stage sequence of a scientific `external_sensor_group_validation`
experiment, because that experiment's `ClientConstruction` already carries a
fixed, human-authored sensor-group partition by the time its configuration is
resolved; `CLIENT_PARTITION` for that experiment cites the audit's
`FEASIBILITY_RESULT` as upstream provenance, never as a value it resolves
live. The scientific experiment never dynamically selects between device
clients, group clients, or a fallback pseudo-client construction
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §9.1`).

In the resolved Edge-IIoTset campaign this is a **capability-scoped** external
validation. The normal-traffic group folder is the authoritative benign client
identity (K = 10 static groups). Direction-normalized endpoint resolution is
kept for source-integrity auditing, attack diagnostics, and provenance only;
it cannot exclude or reassign a source-integrity-valid benign row. Attack rows
do not support per-client attack-sensitive metrics, so external validation is
limited to benign calibration, benign-test FPR, and cross-client FPR
dispersion. The chronological setup and its matched static control both use
the same nine folder clients: Modbus is excluded only because its `frame.time`
values are unusable for chronology. The limitation is therefore specific to
attack-sensitive and timestamp-dependent capabilities, never the whole cell.

### 5.2 Immutable dataset limitations

These are verified, accepted source-data facts, not unresolved
implementation risk. Each is enforced by a typed unavailability or a
`RejectionRecord`, never worked around:

| Dataset | Limitation | Enforcement |
|---|---|---|
| Edge-IIoTset | Attack traffic resolves entirely to a single subnet (subnet 0); per-client attack-sensitive metrics (TPR, Macro-F1, balanced accuracy, AUROC, attack-sensitive threshold trade-offs) are unavailable for both `external_sensor_group_validation` and `chronological_recalibration_evaluation` | `per_client_attack_detection_metrics: unavailable`, reason `attack_traffic_confined_to_subnet_zero` (`§5.1`) |
| Edge-IIoTset | No authorized family taxonomy; `FamilyThreshold` (B3) is never evaluated | Excluded from every Edge-IIoTset `evaluation_refs` list (`§6`, `§7.3`) |
| Edge-IIoTset (temporal) | `Modbus` has unusable capture timestamps; the temporal population is nine groups, not the static regime's ten | `timestamp_semantics_verification` audit, `temporal_group_count: 9`, `excluded_groups: [Modbus]` |
| CICIoT2023 | `MERGED_CSV/` files are shuffled, near-i.i.d. slices of the full 34-class mixture, not naturally distinct captures, sources, or devices — file identities are pseudo-clients only | `DatasetFilePseudoClients`; boundary role only, `§7.5`, never generalized (roadmap `SB-16`) |
| CICIoT2023 | No MAC, device, IP, capture-source, or timestamp column exists in either raw tree | `device_mac_repartition` and `chronological_probe_ciciot2023` are `REJECTED` `RejectionRecord`s (`§5`, `§7.6`) |
| CICIoT2023 | Feature count (`d = 39`) is a conference-artifact value that mirror distributions of this dataset are known to vary on | `processed_feature_verification` audit gates every quantitative `file_pseudo_client_applicability_boundary` claim (`§7.7`) |
| N-BaIoT | Only nine physical devices exist; K > 100 fleet-scale validation is structurally unavailable, not merely undone | `SCI-09`; no fleet-scale type exists anywhere in this design |

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
| `FamilyThreshold` | B3 | device-family mean of member local quantiles; requires an authorized taxonomy | core ladder; mechanism baseline; N-BaIoT (Regime A) only — Edge-IIoTset has no authorized family taxonomy, so B3 is never evaluated there |
| `ClusterThreshold(aggregation=MEAN)` | B4 | k-means-cluster (K = 3 canonical) mean of member local quantiles over a fixed four-scalar fingerprint `[mean(error), std(error), skew(error), p95(error)]` | core ladder; cluster mechanism |
| `ClusterThreshold(aggregation=ROBUST_MEDIAN)` | — | canonical B4 assignment, median instead of mean member aggregation | optional supplementary variant; cannot replace canonical B4 |
| `LocalGlobalShrinkageThreshold` | τ-shrink / LGS | `τ_k(λ) = λ·τ_k,local + (1−λ)·τ_global`, λ ∈ {0, .25, .5, .75, 1} | supportive threshold variant |
| `CalibrationSizeAwareFallbackThreshold` | — | size-dependent `λ(n_k)` replacing the ordinary hard `n_min = 100` fallback for its own declared cells | supportive threshold variant |
| `ConformalLocalThreshold` | B2-conf | split- or federated-conformal local threshold at marginal coverage `1 − α`, α = 0.05 | supportive threshold variant; closes the tautology critique |
| `FederatedSummaryStatisticThreshold` (`mode = matched_exceedance`) | `B-FedStatsBenign` | benign-only client-disclosed `(n_k, mean_k, variance_k)`; sample-weighted global mean; full pooled variance including the between-client mean-shift term; matched-exceedance candidate grid `τ(k) = µ_global + k·σ_global`, k ∈ {0.00 … 5.00} at the pre-registered `matched_exceedance_k_grid_step = 0.01`, ties broken toward larger k | comparator primitive; matched, non-ladder |
| `FederatedSummaryStatisticThreshold` (`mode = fixed_k`) | fixed-k sensitivity | the same construction evaluated at a scalar fixed k ∈ {2.0, 2.5, 3.0} | supplementary sensitivity only; never the primary comparator result |
| `CentralizedPooledThreshold` | B0 | centralized pooled-benign quantile from a separately trained centralized model | non-ladder reference; never fused with federated-averaging scores |
| — (disclosure only, non-executable) | `B-LaridiFaithful` | anomaly-labeled Laridi-style reproduction | `OUT_OF_SCOPE` — violates the benign-only calibration contract; named disclosure record only |

Every remaining threshold construction requirement — that B1 and B3 use
unweighted arithmetic means of eligible local quantiles, that B4 requires
canonical K = 3 and never a q-mutated fingerprint, that `B-FedStatsBenign`
never uses a simplified variance formula or a caller-controlled tie rule,
that its matched-exceedance-versus-fixed-k choice is an explicit `mode`
discriminator (never a `fixed_k = null` sentinel), and that fixed-k can never
become primary — is a structural algorithm rule of the corresponding
discriminated variant, never a configurable boolean
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
| `threshold_quantile_sensitivity` | E-S2 | `SUPPORTIVE`; `TIER_2` | `natural_device_evaluation` (sole owner of this sweep; its external-dataset quantile axis is a benign-FPR-scope `regime_d` regime, `evaluation_scope: benign_operating_point_equity`, `§7.3`) | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`; q ∈ {.90, .95, .975, .99} |
| `controlled_heterogeneity_response` | E-S3 | `SUPPORTIVE`; `TIER_2` | `controlled_heterogeneity_evaluation` (Regime A; the E-M4 "+ Regime D points" seam is a benign-FPR-scope `regime_d` regime using benign score-distribution divergence, `attack_traffic_confined_to_subnet_zero` for attack-sensitive metrics only) | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold` across α; carries the heterogeneity–threshold-benefit association (formerly E-M4) as an attached `AnalysisDefinition` regressing distributional divergence against gain, reusing this experiment's own evaluated results — no separate source inspection, partitioning, training, scoring, or threshold construction |
| `cluster_and_family_threshold_mechanism` | E-M1 / E-M2 / E-Q2 | `MECHANISM`; `TIER_5` (+`TIER_7` exploratory for non-canonical K and `ROBUST_MEDIAN`) | `natural_device_evaluation` (Regime A; the "+ D where feasible" external seam is a benign-FPR-scope `regime_d` regime, B1/B2/B4 with `FamilyThreshold` excluded) | One merged experiment with four typed axes: threshold grouping (`FamilyThreshold` vs `ClusterThreshold`), fingerprint feature set (single-feature through all-four-feature subsets), cluster aggregation (`MEAN` vs `ROBUST_MEDIAN`), and authorized cluster count (canonical `K = 3`, mandatory; other K, exploratory only). Granularity comparison, adjusted-Rand stability, fingerprint ablation, and robust-median sensitivity are four `EvaluationDefinition`/`AnalysisDefinition` entries of this one experiment, never four experiment roots |
| `calibration_window_size_stability` | E-V1 | `BOUNDARY`; `TIER_6` (RQ3) | `natural_device_evaluation`, subsampled calibration n ∈ {50, 100, 250, 500, 1000, 5000} | `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`, `CalibrationSizeAwareFallbackThreshold`; each sweep point is a `CalibrationWindowSelection` (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §12`) |
| `local_global_threshold_shrinkage` | E-V2 | `SUPPORTIVE`; RQ3 | `natural_device_evaluation` | `LocalGlobalShrinkageThreshold`, λ ∈ {0, .25, .5, .75, 1} |
| `conformal_local_threshold_coverage` | E-V3 | `SUPPORTIVE`, Tier-1 tautology defense; non-confirmatory | `natural_device_evaluation` (the "+ external" seam is a benign-FPR-scope `regime_d` regime producing benign conformal coverage and FPR dispersion) | `ConformalLocalThreshold`, α = 0.05 |

### 7.3 External validation and stress tests

All `MANDATORY`. The Edge-IIoTset cells are **executable for benign
operating-point equity** (`evaluation_scope: benign_operating_point_equity`),
with per-client attack-sensitive metrics carrying a typed
`per_client_attack_detection_metrics: unavailable` limitation; the three stress
tests express their Regime A + Regime D coverage as a typed `regimes` list
(`regime_a` and `regime_d`, both run) rather than three invented per-dataset
sibling experiments.

| Semantic slug | Roadmap ref | Role; tier | Dataset setting | Threshold construction(s) |
|---|---|---|---|---|
| `external_sensor_group_validation` | E-X1 | `EXTERNAL_VALIDATION`; `TIER_3` | `external_sensor_group_validation` | **executable, `benign_operating_point_equity` scope** (`§5.1`): `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`, `FederatedSummaryStatisticThreshold` (no `FamilyThreshold` — Edge-IIoTset has no authorized family taxonomy) request FPR-family metrics only; per-client attack-sensitive metrics carry a typed `per_client_attack_detection_metrics: unavailable` limitation; q pinned at 0.95 (the external-dataset quantile-sensitivity sweep is owned by E-S2, `§15`); the operational alert-burden analysis (formerly E-O1) stays unavailable pending a validated traffic rate |
| `fedprox_aggregation_stress_test` | E-T1 | `STRESS_TEST`; `TIER_4` | `regimes`: `regime_a` (`natural_device_evaluation`, run) + `regime_d` (`external_sensor_group_validation`, `benign_operating_point_equity` scope, `FamilyThreshold` excluded) | core ladder, under `FederatedProxTraining`; µ bound per cell from `training.parameters.mu = {from_sweep: federated_proximal_mu}` over the pre-registered grid {0.001, 0.01, 0.1} |
| `model_personalization_absorption_test` | E-T2 | `STRESS_TEST`; `TIER_4` | `regimes`: `regime_a` (`natural_device_evaluation`, run) + `regime_d` (`external_sensor_group_validation`, `benign_operating_point_equity` scope) | `SharedThreshold`, `LocalThreshold`, under the resolved Ditto personalization comparator (see below); the absorption bands compare `CV_FPR` deltas |
| `federated_summary_comparator` | E-T3 / E-Q1 / E-Q5 | `STRESS_TEST` (comparator); `TIER_4` | `regimes`: `regime_a` (`natural_device_evaluation`, run) + `regime_d` (`external_sensor_group_validation`, `benign_operating_point_equity` scope) | One merged experiment: matched benign-summary (`mode = matched_exceedance`) `LocalThreshold` vs `FederatedSummaryStatisticThreshold` comparison (mandatory primary, former E-T3), a quantile-estimation-error analysis framed as distributed quantile estimation (mandatory backbone, former E-Q1), and `mode = fixed_k` `FederatedSummaryStatisticThreshold` sensitivity at scalar k ∈ {2.0, 2.5, 3.0} (optional supplementary evaluation, never primary, former E-Q5) |
| `chronological_recalibration_evaluation` | E-B1 | `BOUNDARY`; `TIER_6` | `chronological_recalibration_evaluation` | **executable, `benign_temporal_operating_point_equity` scope** (`§5.1`): `SharedThreshold`, `LocalThreshold`, `ClusterThreshold`, frozen vs one-shot recalibration on benign FPR using the defensible within-client benign ordering; per-client temporal attack metrics carry a typed unavailability |

The E-T2 personalization comparator is resolved to genuine **Ditto** (Li et
al., ICML 2021) on the `federated_averaging_personalized` training profile,
completely specified — never the `FedRep-AE`/`FedPer-AE` fallback the
roadmap keeps as the untrue-Ditto default (roadmap `SB-24`) — by every
element `SB-24` requires:

| Ditto element | Resolution |
|---|---|
| Global model state | Shared federated-averaging parameters `w_global`, sent to the server every round, identical in shape and update rule to the non-personalized `federated_averaging` profile |
| Persistent client-personalized state | Per-client parameters `v_k`, retained across rounds, never reset |
| Global update sent to the server | Each client's local gradient step on `w_global` only; `v_k` is never transmitted to or aggregated by the server |
| Personalized state never aggregated | `v_k` is excluded from every `FedAvg` aggregation step by construction (`personalization_proximal_weight` only enters the client-local objective below) |
| Proximal personalized objective | `min_{v_k} L_k(v_k) + (personalization_proximal_weight / 2) · ‖v_k − w_global‖²` |
| Parameter grid | `personalization_parameter_grid: [0.001, 0.01, 0.1, 1.0]` |
| Parameter-selection rule | Lowest Regime A benign-validation reconstruction error at the locked global checkpoint round, over the locked seed cohort; tie-break toward the smallest proximal weight; selected before external validation; never selected by `CV_FPR`, test loss, attack metrics, AUROC, or Edge-IIoTset results |
| Checkpoint rule | Reuses the round already authorized by `federated_averaging`'s Regime A primary selection (`§10` field-ownership matrix; `PIPELINE_EXECUTION_AND_ARTIFACTS.md §7`) — never independently recomputed |
| Evaluation state | The personalized parameters `v_k` per client, used for scoring and thresholding; `w_global` is never substituted for evaluation |
| Artifact separation | The shared checkpoint artifact is the same scientific checkpoint the core ladder reuses; the per-client personalized state is a distinct artifact, never fused with it or with plain `federated_averaging` artifacts |

Ditto's architecture-agnostic proximal regularization needs no
head/representation split, so it applies to the fixed autoencoder unchanged
— unlike FedRep or FedPer, which require a separable personalized head that
this program's fixed-encoder core-ladder identity (`SCI-01`) does not
provide (`SCI-01` scopes the fixed-encoder requirement to the core B1–B4
ladder only; `SCI-07` places this stress test outside that ladder, so the
constraint that actually rules out FedRep/FedPer here is architectural — no
separable head exists on the shared autoencoder — not a direct application
of `SCI-01` to a non-ladder experiment). This is a documented pre-training
design decision, not a runtime choice, recorded in
`configs/protocols.yaml` (`personalization_parameter_grid`,
`personalization_parameter_selection`, `ditto_specification`) and no longer
an open blocker.

### 7.4 Attached, non-root analyses

Six roadmap items are analyses, not standalone experiments: they consume an
existing owning experiment's committed evaluations without repeating source
inspection, partitioning, training, scoring, or threshold construction, and
never gain their own `configs/experiments.yaml` document.

| Roadmap ref | Former slug | Owning experiment | Attached as |
|---|---|---|---|
| E-M3 | `client_score_distribution_mechanism_analysis` | `confirmatory_threshold_scope_effect` | per-client benign/attack score-distribution overlay `AnalysisDefinition`, reusing its committed `SCORE_SET` artifacts |
| E-M5 | `threshold_shift_detection_tradeoff` | `confirmatory_threshold_scope_effect` | shared-to-local per-client shift `AnalysisDefinition`, reusing its two evaluations |
| E-Q3 | `operating_point_equity_suite` | `confirmatory_threshold_scope_effect` | optional `FleetEquityResult` evaluation (Jain index, Gini coefficient), never replacing `CV_FPR` |
| E-Q4 | `secondary_confidence_intervals_and_effect_sizes` | `confirmatory_threshold_scope_effect` | descriptive-only `WilcoxonSignedRank` and `CliffsDelta` entries in the owning analysis's `secondary_procedures`, never a second bootstrap definition |
| E-Q6 | `communication_storage_cost_analysis` | any experiment requesting it (chiefly `confirmatory_threshold_scope_effect`, `anchor_reproduction`) | the optional `RESOURCE_COST` stage (`PIPELINE_EXECUTION_AND_ARTIFACTS.md §2`), consuming manifests and artifact metadata only; `MEASURED`/`ESTIMATED` values, never conflated |
| E-M4 | `heterogeneity_threshold_benefit_association` | `controlled_heterogeneity_response` | see `§7.2` |

E-M1, E-M2, and E-Q2 are not attached analyses; they merge into the single
`cluster_and_family_threshold_mechanism` experiment root (`§7.2`) because their fingerprint,
grouping, and aggregation axes are typed variations of the same mechanism
question, not analyses of another experiment's fixed output. E-T3, E-Q1,
and E-Q5 similarly merge into `federated_summary_comparator` (`§7.3`) rather
than attaching to another root, because the comparator is their shared
subject.

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

### 7.7 Dataset-audit catalogue

Dataset audits are non-scientific `DatasetAuditDefinition` runs that produce a
persisted `FEASIBILITY_RESULT`/`SOURCE_INSPECTION` before any dependent
scientific run is authored. They carry no model, threshold, seed,
evidence-role, or claim-tier field, and `evidence_role`/`tier` do not apply
to them (`ARCH-01`, `§5.1`). Each is driven by the declarative contract its
owning dataset's `configs/datasets/<name>.yaml` document states, never by a
document under a separate `configs/dataset_audits/` root and never by an
`audits` list embedded in the dataset document
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §2.1`).

| Owning dataset | Check name | Roadmap basis | Produces | Gates |
|---|---|---|---|---|
| `nbaiot` | `source_inspection` | Regime A feasibility | `SOURCE_INSPECTION`, `FEATURE_SCHEMA_MANIFEST` | N-BaIoT scientific runs |
| `ciciot2023` | `source_inspection` | Regime B feasibility; records MAC/device/IP/timestamp absence | `SOURCE_INSPECTION` | B-a boundary; documents the B-b rejection basis |
| `ciciot2023` | `processed_feature_verification` | conditional gate 1 (roadmap §7, §20) | `FEATURE_SCHEMA_MANIFEST` (verified `d`) | any quantitative `file_pseudo_client_applicability_boundary` claim |
| `edge_iiotset` | `source_inspection` | Regime D feasibility | `SOURCE_INSPECTION`, timestamp evidence | Edge-IIoTset runs |
| `edge_iiotset` | `client_granularity_feasibility` | conditional gate 2 (sensor-group authorization, K ∈ {6,15}, ≥ 90% coverage at n_k ≥ 100) | `FEASIBILITY_RESULT` | `external_sensor_group_validation` granularity authorization |
| `edge_iiotset` | `timestamp_semantics_verification` | temporal MVE feasibility | timestamp-semantics `FEASIBILITY_RESULT` | `chronological_recalibration_evaluation` |

A scientific run never re-answers a question an audit closes; it cites the
audit's `FEASIBILITY_RESULT` by `ArtifactRef` as provenance only
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md §§2, 17`).

## 8. Experiment authorization

A generic YAML combination cannot produce a scientifically unauthorized
experiment. Every experiment is either (a) an `ScientificExperimentDefinition` fully
resolved from one named entry of the `configs/experiments.yaml` catalogue
with every field explicit, or (b) a concrete `ScientificExperimentCell`
expanded from a declared sweep dimension inside such an entry. There is no
separate "authorized profile" layer duplicating the resolved definition's
fields: authorization is enforced by construction validators on the closed
discriminated unions themselves (`ThresholdConstruction`, `ClientConstruction`,
`TrainingProfile`) plus cross-field validators that reject, at
configuration-resolution time, a confirmatory identity paired with a
non-`natural_device_evaluation` dataset, an unpaired or wrong-count seed
cohort, an extra threshold construction on the confirmatory pair, attack
data reachable from a calibration split, an unauthorized personalization
strategy on a core-ladder training profile, an inverted metric direction, a
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
