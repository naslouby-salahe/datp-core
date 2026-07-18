# EVALUATION_REPORTING_AND_PROVENANCE

## 1. Primitive evaluation evidence

The evaluator derives every outcome from lineage-bound primitives only:

- the committed test or temporal score artifact (benign and attack members)
- the ground-truth label implied by each member
- client identity
- the threshold assignment and the calibration `ScoreIdentity` it consumed
- the persisted `EligibleClientSet` for the paired comparison
- the declared evaluation population (`EvaluationSuiteDefinition`)

The evaluator never trusts an externally supplied confusion count as
authoritative input. `ThresholdConstructor.construct` accepts only a
calibration score set and has no field capable of carrying a test or attack
score; `PolicyEvaluator.evaluate` accepts only a committed test or temporal
score set and has no calibration-score field. Calibration/test leakage is
therefore a type error, not a runtime convention (`SCI-04`, `EVAL-02`).

## 2. Confusion-matrix derivation

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ConfusionMatrix:
    true_positive: ConfusionCount
    true_negative: ConfusionCount
    false_positive: ConfusionCount
    false_negative: ConfusionCount
```

For every eligible client, `benign_test_count == true_negative +
false_positive` and `attack_test_count == true_positive + false_negative`;
every derived rate, precision, recall, F1, and balanced-accuracy value is
recomputable from these stored counts and the declared zero-denominator
policy. `ConfusionMatrix` is a computed result; it is never accepted as a
confirmatory or publication-facing input (`EVAL-01`).

## 3. Legacy aggregate import boundary

If an aggregate confusion count must ever be imported from outside this
lineage, it is isolated behind a clearly non-authoritative adapter that
validates non-negative integer counts, population totals, label
definitions, client identity, experiment identity, and source provenance,
and reconciles any supplied derived metric against the recomputed value. An
imported count never supports a confirmatory computation unless the roadmap
explicitly authorizes it — no roadmap experiment currently does
(`EVAL-03`).

## 3.1 Complete statistical and evaluation result-type catalogue

Every statistical and evaluation result type this design produces, its
owning stage, and its persistence status:

| Type | Produced by | Persisted | Purpose |
|---|---|---|---|
| `ClientEvaluationResult` | `EVALUATE` | yes, within `METRIC_OUTPUT` | per-client counts, assigned threshold, derived rates, eligibility status/reason |
| `EligibleClientSet` | `EVALUATE` (first use per comparison) | yes | the one persisted paired-comparison population |
| `EligibilityCoverageResult` | `EVALUATE` | yes | protocol-rule coverage |
| `ConformalCoverageResult` | `EVALUATE` (conformal threshold only) | yes | B2-conf empirical coverage |
| `FleetDispersionResult` | `EVALUATE` | yes, within `METRIC_OUTPUT` | `CV_FPR`, `CV_TPR`, `IQR_FPR`, `FPR_RANGE`, `WORST_CLIENT_FPR` |
| `FleetDetectionResult` | `EVALUATE` | yes | Macro-F1, P10 Macro-F1, worst-client balanced accuracy, AUROC control |
| `FleetEquityResult` | `EVALUATE` (optional suite) | yes | Jain index, Gini coefficient |
| `ClusterDispersionResult` | `EVALUATE` (cluster mechanism only) | yes | within/across-cluster dispersion, adjusted-Rand stability |
| `AlertBurdenResult` | `EVALUATE` (alert-burden suite) | yes | evidence-backed derived burden |
| `PairedDeltaResult` | `STATISTICAL_ANALYZE` | yes, within `STATISTICAL_OUTPUT` | per-seed delta, locked orientation |
| `BootstrapIntervalOutcome` | `STATISTICAL_ANALYZE` | yes | valid or expected-degenerate BCa result |
| `WilcoxonSignedRankResult` / `CliffsDeltaResult` | `STATISTICAL_ANALYZE` (descriptive) | yes | secondary evidence only |
| `ConfirmatoryAnalysisResult` | `STATISTICAL_ANALYZE` (confirmatory/anchor only) | yes | the Tier-1 or anchor verdict |
| `AbsorptionResult` | `STATISTICAL_ANALYZE` (`model_personalization_absorption_test`) | yes | delta ratio and band |
| `TemporalRecoveryResult` | `STATISTICAL_ANALYZE` (`chronological_recalibration_evaluation`) | yes | recovery ratio and outcome |
| `AnchorEquivalenceResult` | `ANCHOR_EQUIVALENCE` | yes, within `ANCHOR_EQUIVALENCE_RESULT` | pass/fail against the reference interval |
| `ResourceCostResult` | `RESOURCE_COST` | yes, within `RESOURCE_COST_OUTPUT` | communication/storage cost, `MEASURED`/`ESTIMATED` |

## 4. Complete metric catalogue and ownership

| Family | Member | Direction | Control-only | Eligible-only | Notes |
|---|---|---|---|---|---|
| Operating point | `FPR` | lower is better | no | yes | per-client rate |
| Operating point | `TPR` | higher is better | no | yes | per-client rate |
| Operating point | `CV_FPR` | lower is better | **no — primary** | yes | `σ_FPR / µ_FPR` over eligible clients |
| Operating point | `CV_TPR` | context-dependent | no | yes | secondary dispersion |
| Operating point | `IQR_FPR` | lower is better | no | yes | absolute-dispersion companion, guards small-mean artifacts |
| Operating point | `FPR_RANGE` (max − min) | lower is better | no | yes | absolute-dispersion companion |
| Operating point | `WORST_CLIENT_FPR` | lower is better | no | yes | tail behavior |
| Operating point | `ALERT_BURDEN` | lower is better | no | yes | requires valid `TrafficRateEvidence` |
| Operating point | `FPR_TARGET_ATTAINMENT` | closer to zero is better | no | yes | `|achieved exceedance − (1 − q)|` |
| Detection quality | `AUROC` | higher is better | **yes — never the thresholding verdict** | no | threshold-independent, computed from scores/labels directly |
| Detection quality | `MACRO_F1` | higher is better | yes | no | |
| Detection quality | `P10_MACRO_F1` | higher is better | yes | no | tenth-percentile client Macro-F1 |
| Detection quality | `BALANCED_ACCURACY` | higher is better | yes | no | |
| Detection quality | `WORST_CLIENT_BA` | higher is better | yes | yes | |
| Equity (optional) | `JAIN_INDEX` | higher is better | no | yes | supplements `CV_FPR`, never replaces it |
| Equity (optional) | `GINI_COEFFICIENT` | lower is better | no | yes | |
| Equity (optional) | `WITHIN_CLUSTER_DISPERSION` | lower is better | no | yes | B4 mechanism only |
| Equity (optional) | `ACROSS_CLUSTER_DISPERSION` | context-dependent | no | yes | B4 mechanism only |
| Estimation | `QUANTILE_ESTIMATION_ERROR` | lower is better | no | n/a | federated-quantile backbone |
| Estimation | `THRESHOLD_VARIANCE` | lower is better | no | n/a | calibration-size sweep |
| Estimation | `CALIBRATION_SAMPLE_EFFICIENCY` | higher is better | no | n/a | |
| Estimation | `ELIGIBILITY_COVERAGE` | higher is better | no | n/a | protocol-rule coverage; disjoint from conformal coverage |
| Estimation | `CONFORMAL_COVERAGE` | closer to target is better | no | n/a | B2-conf empirical coverage; disjoint from eligibility coverage |
| Cluster | `ADJUSTED_RAND_INDEX` | higher is better | no | n/a | cluster-assignment stability across seeds |
| Cluster | `SILHOUETTE` | higher is better | no | n/a | supplementary diagnostic |
| Distribution | `PAIRWISE_JS_DIVERGENCE` | context-dependent | no | n/a | heterogeneity measure |
| Diagnostic ratio | `ABSORPTION_RATIO` | see §6.4 bands | no | n/a | model-personalization stress test |
| Diagnostic ratio | `BETWEEN_RATIO` | reported, not a pass rule | no | n/a | `FederatedSummaryStatisticThreshold` between/within decomposition |
| Diagnostic ratio | `RECOVERY_RATIO` | see §6.5 outcomes | no | n/a | temporal recalibration |
| Resource | `COMMUNICATION_BYTES_PER_ROUND`, `TOTAL_COMMUNICATION_BYTES`, `CLIENT_TO_SERVER_BYTES`, `SERVER_TO_CLIENT_BYTES`, `THRESHOLD_MESSAGE_BYTES`, `CHECKPOINT_STORAGE_BYTES`, `SCORE_ARTIFACT_STORAGE_BYTES`, `RESULT_STORAGE_BYTES` | lower is better | no | n/a | each `MEASURED` or `ESTIMATED`; never conflated |

Thirty-seven metric identifiers across eight disjoint families; a metric
identifier belongs to exactly one family, so `MetricId` is an unambiguous
union. Every metric family has one calculator owner and one `MetricSpec`
(`family`, `is_control`, `needs_eligible_only`, `higher_is_better`); no
metric name is duplicated across families.

## 5. Undefined metric outcomes

A metric that cannot be computed never silently returns zero, `NaN`,
infinity, or an empty value. Typed availability outcomes distinguish:

```text
CvOutcome = ValidCvResult | UndefinedCvResult
BootstrapIntervalOutcome = ValidBootstrapIntervalResult | DegenerateBootstrapIntervalResult
```

`UndefinedCvResult` carries the reason (zero-mean degeneracy), the mean
value, its absolute-dispersion companions (`IQR_FPR`, `FPR_RANGE`), and a
`ClaimOutcome`. `DegenerateBootstrapIntervalResult` carries the sample size,
degeneracy reason, attempted resample count, and an available point
estimate where one exists; BCa is never silently replaced by a percentile
interval. A `StatisticsError` is reserved for a genuinely unexpected failure
(adapter crash, corrupted input, unsupported method) and is never raised for
expected degeneracy (`EVAL-04`, `STAT-06`).

## 6. Eligibility, coverage, and alert burden

### 6.1 Eligibility

`EligibleClientSet` is derived once per paired comparison from shared
calibration lineage — a client below the eligibility minimum (`n_min =
100`) receives the ordinary hard global-threshold fallback only where its
authorized profile permits that fallback, and remains excluded from
eligible-only dispersion metrics. `CalibrationSizeAwareFallbackThreshold`
replaces, rather than follows, the ordinary hard fallback for its own
declared cells. Compared policies never use different eligible-client sets
(`SCI-10`, `EVAL-05`).

### 6.2 Coverage

`EligibilityCoverageResult` (`eligible_count / roster_count`) and
`ConformalCoverageResult` (empirical B2-conf coverage against target) are
disjoint identities and never share a metric, table column, or result field
(`EVAL-06`).

### 6.3 Alert burden

Requesting `ALERT_BURDEN` selects `AlertBurdenEvaluationSuite`, which
requires a validated `TrafficRateEvidence` (`Measured` or `Cited`) — a
numeric rate, unit, scope, and source. A negative rate, a non-finite rate,
an uncited assumed rate, or an incompatible unit is rejected before
evaluation; alert burden is omitted, never estimated, when no valid rate
exists.

### 6.4 Model-personalization absorption bands

Locked, applied without adjustment: let `Δ_core = CV_FPR[core+shared] −
CV_FPR[core+local]` and `Δ_pers = CV_FPR[personalized+shared] −
CV_FPR[personalized+local]`.

| Band | Condition | Interpretation |
|---|---|---|
| `STRONGLY_USEFUL` | `Δ_pers ≥ 0.75·Δ_core` | threshold personalization remains strongly useful |
| `PARTIAL` | `0.25·Δ_core ≤ Δ_pers < 0.75·Δ_core` | partial absorption; boundary condition |
| `LARGELY_ABSORBED` | `Δ_pers < 0.25·Δ_core` | claim narrowed to shared-encoder settings |
| `ALTERNATIVE_PATH` | `CV_FPR[personalized+shared]` within 0.05 of `CV_FPR[core+local]` | model personalization is an alternative equity path; reported as a positive finding, not a DATP-Core failure |

### 6.5 Temporal recovery outcomes

Locked, applied to the chronological recalibration evaluation:

| Outcome | Condition | Wording |
|---|---|---|
| `RECAL_HELPS` | recovery ratio ≥ 50% | one-shot recalibration recovers a meaningful portion of the gain |
| `RECAL_INSUFFICIENT` | recovery ratio < 50% | temporal fragility; no retroactive streaming detector is added |
| `NO_MEANINGFUL_DRIFT` | FPR drift within the static split's bootstrap CI | thresholds appear stable; not a general temporal-robustness claim |

## 7. Communication and storage cost

The optional `RESOURCE_COST` stage (formerly the standalone
`communication_storage_cost_analysis`/E-Q6, now attached to any requesting
experiment, `SCIENTIFIC_FOUNDATION.md §7.4`) produces `ResourceCostResult`
values across the eight `ResourceMetric` members
(`COMMUNICATION_BYTES_PER_ROUND`, `TOTAL_COMMUNICATION_BYTES`,
`CLIENT_TO_SERVER_BYTES`, `SERVER_TO_CLIENT_BYTES`,
`THRESHOLD_MESSAGE_BYTES`, `CHECKPOINT_STORAGE_BYTES`,
`SCORE_ARTIFACT_STORAGE_BYTES`, `RESULT_STORAGE_BYTES`) for
`SharedThreshold`, `LocalThreshold`, and `ClusterThreshold`. Each value is
`MEASURED` or `ESTIMATED` and never conflated; an `ESTIMATED` communication
value is always rendered with that label and never described as measured
traffic (`ART-07`). This resource-cost family is deliberately distinct from
two operationally similar but scientifically unrelated concepts: disk
preflight (`StorageRootPreflightResult`, `DiskSpacePreflightResult`), which
validates writability and capacity before execution and never enters
scientific identity or reporting; and advisory execution-cost estimation
(`ExecutionCostEstimate`), which is shown to an operator before a run,
remains explicitly non-scientific, may cite compatible historical manifests
as its basis, and never unlocks a stage or changes a resolved specification.
None of the three substitutes for either of the other two, and no
communication/storage evidence is fabricated from an approximate model when
a message-size derivation from the actual resolved configuration is
available; a derivation is either computed from the resolved
`ThresholdConstruction` and client roster (yielding `MEASURED` or a
disclosed `ESTIMATED` label) or the metric is omitted for that construction
(`EVAL-07`).

## 8. Statistical procedure architecture

`StatisticalProcedureDefinition` — owned by `AnalysisDefinition`, never by
`EvaluationDefinition` (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.3`) —
fixes method, confidence level, and resample count; every choice is
pre-specified in configuration, never selected after observing results
(`STAT-01`). Paired-seed count is owned once, by the experiment's
`SeedCohortDefinition`, and read by every `AnalysisDefinition` comparing
that experiment's evaluations — never re-declared per analysis. Required
procedures: BCa bootstrap (primary for the confirmatory and anchor
endpoints), Wilcoxon signed-rank and Cliff's delta (descriptive secondary
evidence only, requested via `StatisticalProcedureDefinition.include_wilcoxon`/
`include_cliffs_delta` on the same `PairedThresholdAnalysis` rather than a
second, standalone analysis), Spearman correlation and linear regression
(mechanism association analyses), percentile bootstrap (never substituted
for BCa without an explicit, separately named procedure).

### 8.1 Confirmatory isolation

The confirmatory (and anchor) statistical contract — enforced on
`confirmatory_threshold_scope_effect`'s (and `anchor_reproduction`'s) single
`PairedThresholdAnalysis` — rejects: a dataset setting other than
`natural_device_evaluation`; a threshold pair other than
`{SharedThreshold(MEAN), LocalThreshold}`; any extra threshold construction
on the same pair of evaluations; an unpaired or wrong-count `seed_cohort`;
a primary metric other than `CV_FPR`; a reversed delta orientation; a
confidence level other than `0.95`; an unauthorized checkpoint lineage; a
different eligible-client set between the two compared policies; or, for
the confirmatory experiment specifically, a missing passed anchor result
(enforced by its typed `ExperimentPrerequisite`,
`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`). Secondary statistics
(Wilcoxon, Cliff's delta) never silently become confirmatory decision
inputs (`STAT-02`, `SCI-14`).

### 8.2 Claim outcomes

```text
ClaimOutcome = STRONG_POSITIVE | WEAK_POSITIVE | MIXED | NULL | OPPOSITE
             | FEASIBILITY_REJECTION | SUPPRESSED
```

Outcome selection follows the roadmap's locked interpretation rules and
occurs only after result freeze; wording is never inferred favorably at
render time (`REPORT-04`).

## 9. Safe reporting architecture

### 9.1 Forbidden row contracts

`Sequence[str | int | float]`, `Mapping[str, Any]`, `dict[str, object]`,
`list[dict[str, Any]]`, and `tuple[object, ...]` never appear in a
publication-facing report row.

### 9.2 Safe report model

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ReportDefinition:
    report_identity: ReportArtifactType
    schema_version: str
    columns: tuple[SemanticColumn, ...]   # each: name, unit, metric_direction
    row_projection: RowProjectionRule
    ordering: DeterministicOrdering
    missing_value_policy: MissingValuePolicy
    source_result_types: tuple[type, ...]
    source_artifact_refs: tuple[ArtifactRef, ...]
    output_formats: tuple[SerializationFormat, ...]
```

One row dataclass per table is used only where tables have genuinely
distinct scientific schemas (for example a dispersion-ladder table and a
cluster-stability table); a shared schema is reused rather than duplicated.
Reports never recompute a metric or a statistic, infer experiment meaning
from a string, select favorable seeds, guess a missing value, rename a
metric silently, decide a claim outcome, reconstruct provenance, or read a
raw upstream file directly — they consume only a frozen `ResultFreezeManifest`
and a framework-free table/figure specification (`REPORT-01`–`REPORT-03`).

### 9.3 Table and figure families

`TableType`: `CONFIRMATORY_INTERVAL`, `DISPERSION_LADDER`,
`SENSITIVITY_GRID`, `COMPARATOR`, `STRESS_TEST`, `CLUSTER_STABILITY`,
`CONTINGENCY`, `BOUNDARY_NULL`, `ALERT_BURDEN`,
`COMMUNICATION_STORAGE_COST`. `FigureType`: `CDF_OVERLAY`, `SCATTER`,
`HEATMAP`, `LAMBDA_CURVE`, `RECOVERY_CURVE`, `SEVERITY_TREND` — no Sankey
member; B4 interpretability renders as a contingency table or a small
heatmap. Each `ReportDefinition` declares its expected source result types
explicitly.

### 9.4 Report-family to experiment mapping

| `TableType` / `FigureType` | Serves |
|---|---|
| `CONFIRMATORY_INTERVAL` | `anchor_reproduction`, `confirmatory_threshold_scope_effect` |
| `DISPERSION_LADDER` | `shared_threshold_construction_sensitivity`, `file_pseudo_client_applicability_boundary` |
| `SENSITIVITY_GRID` / `HEATMAP` | `threshold_quantile_sensitivity` |
| `SEVERITY_TREND` | `controlled_heterogeneity_response` |
| `CLUSTER_STABILITY` / `CONTINGENCY` | `cluster_mechanism` (granularity comparison, adjusted-Rand stability, fingerprint ablation, and robust-median sensitivity, all as evaluations/analyses of this one experiment) |
| `CDF_OVERLAY` | `confirmatory_threshold_scope_effect` (attached client score-distribution overlay analysis, formerly E-M3) |
| `SCATTER` | `confirmatory_threshold_scope_effect` (attached threshold-shift-detection tradeoff analysis, formerly E-M5), `controlled_heterogeneity_response` (attached heterogeneity–threshold-benefit association, formerly E-M4) |
| `SENSITIVITY_GRID` | `calibration_window_size_stability` |
| `LAMBDA_CURVE` | `local_global_threshold_shrinkage` |
| `COMPARATOR` | `federated_summary_comparator` (matched benign-summary comparison, quantile-estimation backbone analysis, and optional fixed-k sensitivity, all as evaluations of this one merged experiment) |
| `STRESS_TEST` | `fedprox_aggregation_stress_test`, `model_personalization_absorption_test` |
| `RECOVERY_CURVE` | `chronological_recalibration_evaluation` |
| `ALERT_BURDEN` | `external_device_dataset_validation` (attached alert-burden evaluation, formerly `operational_alert_burden_analysis`/E-O1, requiring validated `TrafficRateEvidence`) |
| `COMMUNICATION_STORAGE_COST` | any experiment requesting the optional `RESOURCE_COST` stage (chiefly `confirmatory_threshold_scope_effect`, `anchor_reproduction`; formerly the standalone `communication_storage_cost_analysis`/E-Q6) |
| `BOUNDARY_NULL` | `file_pseudo_client_applicability_boundary`, any experiment whose claim outcome is `NULL` or `FEASIBILITY_REJECTION` |

The optional equity suite (Jain index, Gini coefficient; formerly the
standalone `operating_point_equity_suite`/E-Q3) and the descriptive
secondary confidence-interval/effect-size analysis (formerly the standalone
`secondary_confidence_intervals_and_effect_sizes`/E-Q4) both attach to
`confirmatory_threshold_scope_effect` and reuse its `CONFIRMATORY_INTERVAL`
table family with additional optional columns, rather than introducing a
new `TableType` for either (`SCIENTIFIC_FOUNDATION.md §7.4`).

Every experiment in `SCIENTIFIC_FOUNDATION.md §7` maps to at least one
table or figure family above; a new experiment either reuses an existing
family or introduces one new `ReportDefinition`, never a bespoke row type
(extension test 7 in `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §9`).

## 10. Result freeze and provenance closure

Before rendering, `RESULT_FREEZE` validates every required source artifact,
its content hash, its schema version, the experiment identity, the
configuration fingerprint, and the claim outcome, then persists an
immutable `ResultFreezeManifest`. `TableFigureTracer.trace` requires this
manifest's expected inputs and hashes to close; otherwise it returns
`TRACE_REFUSED` and raises `ProvenanceError` rather than rendering a
possibly stale artifact. A rendered file remains traceable to its frozen
input set through `TableProvenance`/`FigureProvenance`, which record output
identity, output type, source records, and rendering status
(`PROV-01`–`PROV-02`).

### 10.1 Worked trace: the confirmatory table

Rendering the `confirmatory_interval` main table for
`confirmatory_threshold_scope_effect` traces as: `RESULT_FREEZE` consumes
the experiment's `ConfirmatoryAnalysisResult` (from `StatisticalOutput`),
which itself references the ten paired `PolicyEvaluationResult` values (one
per seed) that produced its per-seed deltas, each of which references its
`ThresholdOutput` and `ScoreSet` (`SplitRole = TEST`) `ArtifactRef` values,
which in turn reference the single selected `CheckpointSelection` and its
upstream `TrainingIdentity`. `TableFigureTracer.trace` walks this entire
chain, verifies every content hash and schema version along it, and only
then hands the framework-free `confirmatory_interval` table specification
to the Markdown/LaTeX renderer. If any one of the ten seeds' evaluation
results is missing, stale, or hash-mismatched, the trace refuses for the
whole table rather than silently rendering nine seeds as ten.

## 11. Pre-specification evidence

`PreSpecificationRecord` names the subject (the absorption bands in §6.4,
the temporal outcome bands in §6.5), the version-controlled roadmap-lock
revision, and the time it was fixed — evidencing that a decision band was
locked before any external-dataset or stress-test data existed. The bands
are applied exactly as locked, without post-hoc adjustment.

## 12. Null and suppression reporting

Every claim above `EXPLORATORY` carries pre-committed fallback wording for
every outcome in §8.2, selected only after result freeze
(`SCIENTIFIC_FOUNDATION.md §9`). The confirmatory endpoint is never a valid
`SUPPRESSED` subject: if its interval includes zero, the null result and the
failure to exclude zero are reported as the main result. A `SuppressionRecord`
names its subject, reason, and resulting `ClaimOutcome`, and is itself a
persisted, non-scientific decision record — never a mechanism for hiding an
unfavorable confirmatory result.
