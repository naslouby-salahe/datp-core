# Threshold calibration, evaluation, inference, and scientific-drift audit

## Scope and method

Read `docs/graphify_audit/00_JOURNAL_CONTRACT.md` and the complete roadmap before this review. Production code was read only. Graphify was already installed in WSL and the refreshed AST graph was used to corroborate live chains; source is cited for every finding because Graphify's multigraph diagnostic reports edge-collapse risk.

The live core chain is:

`ExperimentWorkspace.threshold` → `dispatch_federated_threshold` → policy/variant constructor → `ExperimentWorkspace.evaluation` → `evaluate_federated_detector` → `prepare_federated_evaluation` → fixed-score validation, client metrics, population metrics, evaluation publication. Confirmatory analysis then loads B1/B2 documents and builds a paired contrast before the paired BCa routine.

Graphify corroboration from the refreshed graph: `_dispatch_confirmatory → run_confirmatory_seed → execute_declared_experiment_seed`; the execution workspace is therefore a real production downstream consumer, not an isolated threshold utility.

## Confirmed contract-aligned paths

- B1 is the unweighted arithmetic mean of eligible local quantiles; B2 assigns each eligible local quantile (`src/datp_core/thresholds/policies/shared.py:139-157`, `local.py:40-55`). Pooled and sample-weighted shared constructions are separate methods.
- Dispatch is exhaustive and rejects centralized threshold methods in federated execution (`thresholds/dispatch.py:62-222`). It checks population capabilities and enforces the canonical support floor unless executing the declared size-ablation route.
- Calibration reads benign calibration references, checks calibration/evaluation stable-row disjointness before eligibility, and derives eligibility before threshold construction (`thresholds/calibration/service.py:35-95`).
- B4 uses the required benign calibration fingerprint (mean, population SD, skewness, p95), `StandardScaler`, locked KMeans, K=3, fixed random state and mean local thresholds; a median aggregation is only explicitly selected for the group-median supplement (`thresholds/policies/cluster.py:106-195`; `protocols/calibration.py:24-161`; `execution/workspace.py:202-208`).
- Predictions use strict `score > threshold`; confusion is restricted to held-out evaluation rows and rejects invalid client attack assignments (`analysis/metrics/confusion.py:11-65`). Population CV uses `ddof=0`, no epsilon, and produces typed undefined CV/equity indices at zero mean (`analysis/metrics/population.py:88-140`).
- Confirmatory contrast construction validates same score coordinate, split, selected checkpoint, preprocessing and fixed-score evidence. The BCa validator requires exactly the declared ten seed identities and B1-minus-B2 `CV(FPR)` on the confirmatory population (`analysis/contrasts.py:119-174`; `analysis/inference/bootstrap/validation.py:16-69`). The bootstrap uses paired seed deltas and returns a typed blocked/degenerate interval rather than silently substituting another method (`bootstrap/estimation.py:34-125`).

## Findings

### SCIENTIFIC_DRIFT-THRESH-01 — threshold-estimation “pooled calibration oracle” is derived from held-out evaluation scores

**Journal requirement.** Threshold estimators and their centralized exact-pool reference are constructed from the same benign calibration data. Calibration and evaluation must remain disjoint; evaluation may be used for held-out attainment/coverage diagnostics, not as the threshold-estimation oracle.

**Live caller chain.** `ExperimentWorkspace.evaluation` passes `_threshold_estimation_inputs()` into `EvaluateFederatedDetectorRequest` (`src/datp_core/experiments/execution/workspace.py:420-434`). `prepare_federated_evaluation` sends each input to `evaluate_threshold_estimate` (`analysis/metrics/federated_execution.py:188-227`). The diagnostic is published in the federated evaluation document and is consumed by `report_federated_benign_statistics_comparison` / quantile-estimation reports (`experiments/federated_threshold/run.py:179-303`).

**Evidence.** `_threshold_estimation_inputs` first reads `self.scores.evaluation_records` and filters their held-out benign scores (`workspace.py:328-346`). It concatenates those evaluation scores into `pooled_values` and computes `pooled_quantile` (`:347-350`), then passes it as `exact_pooled_benign_quantile_reference` (`:351-370`). The same function separately calls `verify_held_out_benign_scores`, confirming that this input is evaluation data rather than calibration data.

**Impact.** Reported absolute/relative threshold error is against a test-benign pooled quantile, not the declared exact pooled calibration quantile. This does not alter the already-constructed threshold, but it contaminates the estimator-comparison diagnostic and can make a calibration method look closer/farther from an oracle selected from held-out data.

**Required direction.** Build the exact pooled reference from the eligible benign calibration-score artifacts (the same client score sets that built B1/B2/FedStats) and retain held-out benign scores only for achieved-exceedance/coverage diagnostics. Record distinct calibration-oracle and held-out-attainment provenance/checksums.

### FIX_INCOMPLETE-THRESH-02 — B-FedStatsBenign does not emit the required benign exceedance summary or its communication record

**Journal requirement.** The mandatory benign-only federated comparator communicates client benign `n`, mean, variance, and permitted benign exceedance summaries; it must use full within+between variance, match target exceedance, and disclose every communicated statistic/communication record. It must not be named Laridi-faithful.

**Live caller chain.** Threshold dispatch routes `FEDERATED_BENIGN_STATISTICS` to `construct_federated_benign_statistics` (`src/datp_core/thresholds/dispatch.py:165-170`), then workspace evaluation publishes its result. The N-BaIoT estimation recipe runs it through `run_federated_benign_statistics_comparison_seed` and summarizes evaluation diagnostics in `report_federated_benign_statistics_comparison` (`experiments/federated_threshold/run.py:320-367`).

**Evidence.** The result model has an optional `benign_exceedance_count` (`thresholds/variants/federated_statistics.py:31-47`), but `_client_summary` always sets it to `None` (`:207-215`). `_communication_bytes` consequently counts only three scalars per client (count, mean, variance) and conditionally adds one only if the always-`None` field were present (`:246-248`). The comparator does correctly compute full pooled variance with the between-client term (`:217-243`) and uses benign inputs, but neither the result nor the report emits a client communication-field record; the report only aggregates generic evaluation communication and scalar summary metrics (`experiments/federated_threshold/run.py:179-303`).

**Impact.** The required comparator is algorithmically reachable but scientifically incomplete: its disclosed message contract is missing the permitted exceedance summary, and readers cannot audit exactly what leaves each client. The aggregate byte count therefore understates/changes the declared comparator protocol.

**Required direction.** Define the predeclared benign exceedance summary (including the target/reference it counts), populate it for every eligible client, include it in byte estimation, and serialize a per-client communication record alongside `n`, mean, variance, within/between/full variance and target-attainment diagnostics. Keep the name `B-FedStatsBenign`.

### WIRE_REQUIRED-THRESH-03 — the mandatory Edge B-FedStatsBenign comparator executes but has no external-result analysis/report path

**Journal requirement.** Regime D requires B1/B2/B4/**FedStats** benign-FPR outcomes. The comparator is mandatory for Regime A and Regime D when artifacts are available; external attack-sensitive outcomes remain typed unavailable.

**Live caller chain.** The Edge declaration includes `FEDERATED_BENIGN_STATISTICS` in `_EDGE_BENIGN_EQUITY_METHODS` (`src/datp_core/protocols/experiments.py:91-99,370-379`). The public external dispatcher invokes `run_external_validation_seed` → `_run_seed` → `execute_declared_experiment_seed` (`src/datp_core/experiments/external/run.py:55-100`), so Edge FedStats coordinate/evaluation artifacts are produced.

**Evidence.** The only Edge campaign analysis builds a supplementary paired plan for B1 versus B2 and loads exactly those two methods (`external/run.py:102-158` and `:162-179`). `AnalyzeExternalEvidenceRequest` therefore receives no B4 or FedStats evidence. The only dedicated FedStats report (`report_federated_benign_statistics_comparison`) hardcodes `PopulationId.NBAIOT_NATURAL_DEVICES` for its directory and reads the N-BaIoT ten-seed cohort (`experiments/federated_threshold/run.py:256-303`); it cannot consume Edge artifacts.

**Impact.** Edge FedStats is reachable execution code but unreported evidence. The external report can claim only B1/B2 evidence while the journal-required external comparator's FPR, threshold error/attainment, between-ratio, and communication outcomes have no publication consumer.

**Required direction.** Add an Edge-aware FedStats analysis/report that consumes the existing Edge evaluation/threshold artifacts and publishes benign-only FPR equity, estimator diagnostics, variance decomposition, and communication disclosure with typed unavailable attack outcomes. Do not promote it to confirmatory inference.

### WIRE_REQUIRED-THRESH-04 — Regime B-a's required B0 contextual reference is absent from the live declaration and runner graph

**Journal requirement.** The CICIoT2023 file-defined applicability boundary allows B0/B1/B2/B4 and benign distribution diagnostics while prohibiting physical-device claims and B3. B0 must be an independently trained centralized reference, never federated scores relabelled as B0.

**Evidence.** The live CICIOT declaration has only `_SHARED_LOCAL_AND_GROUPED_METHODS` (B1/B4/B2) (`src/datp_core/protocols/experiments.py:385-394`); B0 has no federated-threshold identifier and no separate contextual-reference declaration. `run_ciciot_boundary_seed` delegates only to that declaration (`experiments/external/run.py:67-100`). The sole centralized runner hardcodes `PopulationId.NBAIOT_NATURAL_DEVICES` (`src/datp_core/experiments/centralized_reference.py:54-84`), and its only public orchestrator is the campaign B0 helper described in `app/research.py:198-215`.

**Impact.** There is no possible CIC B0 artifact or comparison product. This is an absent required programme branch, not an intentional typed unavailable outcome.

**Required direction.** Add a CIC-specific independent centralized-reference route with its own pooled preprocessing/model/scores/pooled benign calibration threshold, and expose it only as the contextual boundary reference. If CIC B0 is deliberately removed by an authoritative roadmap revision, update the contract/matrix first; the current code silently omits it.

## Additional drift watch

The canonical protocol labels the controlled Dirichlet sweep `EvidenceRole.MECHANISM` (`protocols/experiments.py:279-290`) and its publication writer uses the same role (`experiments/heterogeneity/run.py:98-255`), whereas the contract frames Regime C as a supportive sensitivity. This is a claim-tier metadata mismatch. It does not alter threshold construction, but the evidence role should be reconciled before manuscript/export language treats it as a mechanism rather than supportive non-confirmatory sensitivity.

## Conclusion

The B1/B2 fixed-score ladder, typed metric semantics, and paired ten-seed BCa implementation are strongly wired. The main scientific risks are downstream: a held-out-test oracle is used for estimator diagnostics, B-FedStats' declared message contract is incomplete and missing from Edge reporting, and the CIC applicability branch lacks its required independent B0 reference.
