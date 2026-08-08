# Reviewer 4 — Independent Audit of Prompt 4/8 (Federated Threshold Estimation and Comparator Workflows)

Date: 2026-08-08
Scope: current working tree (uncommitted) at `/home/naslouby/Projects/datp-core`
Method: read `docs/Journal_Extension_Master_Roadmap.md` in full; treated `docs/graphify_implementation/04_FEDERATED_THRESHOLD_ESTIMATION.md` as untrusted; inspected actual source, tests, experiment declarations, evaluation/communication/thresholding contracts, workflow registration and CLI call chains.

---

## Summary

The three experiments are wired end-to-end: declaration -> plan -> execute_declared_experiment_seed -> evaluation document -> workflow report -> CLI smoke/report/status -> completion marker. Registration is complete and consistent. B-FedStatsBenign construction is benign-only and mathematically correct. However, the scope is **scientifically incomplete** where it claims to be complete: the fixed-coefficient sensitivity experiment does not actually evaluate the k-grid, and the federated quantile-estimation experiment is a duplicate of the comparison experiment rather than the roadmap's quantile-estimation backbone. One report fabricates a hardcoded `coefficient=0.0` value that has no basis in any artifact.

---

## Findings

### F1 — HIGH — FIXED_COEFFICIENT_STATISTICS_SENSITIVITY does not evaluate the coefficient grid; report fabricates `coefficient=0.0`

**Where:** `src/datp_core/pipeline/workflows/federated_threshold_estimation.py`, `report_fixed_coefficient_statistics_sensitivity` (L310-343), `_FixedCoefficientSummaryRow.coefficient` (L63-68).

**Evidence:**
- The experiment declaration (`src/datp_core/protocols/experiments.py`) resolves to methods `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FEDERATED_BENIGN_STATISTICS` — the same three methods as a per-method comparison. Nothing in the plan, execution, or evaluation distinguishes any coefficient value.
- The report loop iterates `declaration.federated_thresholds` x seeds and reads only `MetricId.FPR_COEFFICIENT_OF_VARIATION` and `WORST_CLIENT_FPR` from the evaluation document (L322-333). No coefficient is read from any artifact.
- Line 328 writes `coefficient=0.0` unconditionally for every row. This value is fabricated: no artifact anywhere contains a coefficient value of 0.0 for these rows, and k=0 is not on the locked grid.
- The production threshold construction (`src/datp_core/thresholding/methods/federated_statistics.py`, `construct_federated_benign_statistics`, `fixed_coefficient_curve` L187-197) computes the k in {2.0, 2.5, 3.0} curve, but that curve is **never consumed for evaluation** (`src/datp_core/evaluation/federated/execution.py`, `_assignments` L382-401 and `_deployment_fallback_threshold` L404-424 read only `matched_threshold`/`assignments`). The only consumer of `fixed_coefficient_curve` is a test asserting it differs from `matched_threshold` (`tests/scientific/test_benign_only_threshold_construction.py` L284-293).
- Therefore the "sensitivity" experiment evaluates a single operating point per method (the k-independent matched threshold) across seeds, producing a spread that reflects seed variance, not coefficient sensitivity. The report then labels every row coefficient=0.0. A reader of `summary.json` would infer a k=0 sensitivity point that was never computed.

**Why it is wrong:** Roadmap §9.3 locks coefficient sensitivity k in {2.0, 2.5, 3.0}. This experiment produces no per-coefficient evidence; the reported coefficient field is false data that will be consumed as if it were a scientific result. This violates §2.2 (never invent scientific values), §10.1 (no hardcoded values), and §3 (do not promote evidence beyond the claim tier).

**Fix (two parts, both required):**
1. Make the k-grid real: route `fixed_coefficient_curve` (or a per-k deployment) into the evaluation path so each k in {2.0, 2.5, 3.0} produces a distinct threshold per method/seed, and declare/evaluate per-coefficient coordinates (e.g., by threshold variant or an explicit coefficient dimension) rather than only per method. The experiment must actually vary k to be a sensitivity study.
2. In the report, remove the fabricated `coefficient=0.0` write. Either surface the real coefficient from the evaluated artifact, or remove the field. Never write a value that was not computed.

---

### F2 — MEDIUM — FEDERATED_QUANTILE_ESTIMATION duplicates FEDERATED_BENIGN_STATISTICS_COMPARISON; roadmap §9.2 outcomes are not surfaced

**Where:** `src/datp_core/protocols/experiments.py` L357-383 (declarations), `src/datp_core/pipeline/workflows/federated_threshold_estimation.py` L190-286 (reports).

**Evidence:**
- The two experiment declarations are identical: same role, population, training model, and the same `_FEDERATED_STATISTICS_COMPARISON_METHODS` tuple (SHARED, POOLED_SHARED_QUANTILE, SAMPLE_WEIGHTED_SHARED_THRESHOLD, LOCAL, FEDERATED_BENIGN_STATISTICS).
- The two report functions `report_federated_benign_statistics_comparison` (L190-226) and `report_federated_quantile_estimation` (L250-286) are textually near-identical; the dataclasses `_FederatedComparisonSummaryRow` (L44) and `_QuantileEstimationSummaryRow` (L53) are identical field-for-field.
- Roadmap §9.2 defines federated quantile-estimation as a distinct scientific object: a threshold constructed from federated quantile estimation, with its own required outcomes (threshold error, target-attainment error, communication fields/bytes, client coverage). The shared and pooled-quantile threshold methods do exist in the thresholding layer, but this experiment surfaces none of the quantile-estimation-specific diagnostics — it reports the same FPR-CV / worst-client-FPR per method as the comparison experiment.
- No artifact distinguishes the two runs at execution time, so the two experiments will produce substantively the same evaluation documents and the same summary.json shape.

**Why it is wrong:** A second experiment with a distinct identifier and roadmap section that reproduces the first experiment's content is a duplicate responsibility (CLAUDE.md §5, §6). The roadmap's §9.2 outcomes (threshold error, target-attainment error, communication, coverage) are not reported anywhere in this workflow.

**Fix:** Either (a) make FEDERATED_QUANTILE_ESTIMATION evaluate and report the roadmap §9.2 outcomes (quantile-estimation threshold error vs exact reference, target-attainment error, communication fields/bytes, client coverage), or (b) if the roadmap intends these as one experiment, remove the duplicate declaration, report, and registration and consolidate. Do not keep two identifiers pointing at identical behavior.

---

### F3 — MEDIUM — B-FedStatsBenign communication estimate computed but never surfaced to any report

**Where:** `src/datp_core/thresholding/methods/federated_statistics.py` L209 (`estimated_communication_bytes`), `src/datp_core/pipeline/execution/workspace.py` L389 (`_communication_messages`, records only `ThresholdPayloadKind.MODEL_TRANSMISSION`).

**Evidence:**
- `construct_federated_benign_statistics` computes `estimated_communication_bytes` but it is not stored on the result contract and has no consumer.
- `src/datp_core/evaluation/communication.py` L25 defines `ThresholdPayloadKind.BENIGN_SUMMARY_STATISTICS`, but no message is ever constructed with this kind; `_communication_messages` only records training-payload messages.
- Roadmap §9.1 required outcomes for the benign summary-statistics comparator include "communication fields/bytes". The implementation claims this as a completed required outcome but no artifact records or reports the federated-statistics communication cost. The workflow reports (F2/F5) do not include a communication field.

**Why it is wrong:** The roadmap requires communication cost as a comparator outcome. It is computed in one place and dropped everywhere else, so the required outcome is unreportable.

**Fix:** Construct a `BENIGN_SUMMARY_STATISTICS` message (or otherwise record `estimated_communication_bytes` into the communication evidence), and surface it in the comparison report (and quantile report if retained). This makes an existing computation reach the required outcome rather than adding new math.

---

### F4 — MEDIUM — Duplicated report/helper scaffolding across workflow modules

**Where:** `src/datp_core/pipeline/workflows/federated_threshold_estimation.py` L94-170 (`_finalize_report`, `_declaration_for`, `_evaluation_document_path`, `_evaluation_document_for_seed`, `_mean`, `_complete_marker`-style pattern) vs `src/datp_core/pipeline/workflows/threshold_robustness.py` (same-named helpers).

**Evidence:** `_finalize_report` (L94-104), `_declaration_for` (L107-110), `_evaluation_document_path` (L113-121), `_evaluation_document_for_seed` (L124-145), and `_mean` (L169-170) are functionally identical to the helpers in `threshold_robustness.py` (e.g., `_finalize_report` at L119 there). The two report bodies in the new module are also near-copies of each other (F2).

**Why it is wrong:** Direct duplication of an existing responsibility violates the reuse-first rule (CLAUDE.md §5) and deletion bias (§6). This is not a wrapper-with-one-caller case; it is five identical helpers plus two identical report bodies.

**Fix:** Consolidate the shared report-scaffolding (marker write, missing-count handling, evaluation-document resolution per seed/method, mean aggregation) into one canonical helper used by both `threshold_robustness.py` and `federated_threshold_estimation.py`. Delete the local duplicates. If F2's consolidation removes the quantile report, the comparison report becomes the single canonical consumer.

---

### F5 — LOW — Redundant and misleading report fields

**Where:** `src/datp_core/pipeline/workflows/federated_threshold_estimation.py` L44-50, L209-215, L326-332.

**Evidence:**
- `_FederatedComparisonSummaryRow.mean_cv_fpr` and `fpr_coefficient_of_variation` are both assigned `_mean(cv_values)` (L212, L214) — the same value stored under two names; `fpr_coefficient_of_variation` is a misnomer for the mean of per-seed CV values.
- `worst_client_fpr` in the comparison row is a mean across seeds (L213), so the field name overstates what it is.
- `_FixedCoefficientSummaryRow.coefficient=0.0` (F1) is a fabricated value.

**Why it is wrong:** Redundant fields and misnamed metrics mislead downstream consumers and violate §20 (naming must express meaning) and §16 (attributable outputs).

**Fix:** Remove the duplicate `fpr_coefficient_of_variation` field or give it a distinct, correct meaning; rename mean-aggregated fields to state their aggregation (e.g., `mean_worst_client_fpr`); remove the fabricated coefficient.

---

### F6 — INFO — Graphify graph is stale relative to the completed scope

**Where:** `graphify-out/2026-08-07/graph.json` (built_at_commit e015142b).

**Evidence:** The graph has no nodes for `src/datp_core/pipeline/workflows/federated_threshold_estimation.py` or the three new experiment ids; the working tree adds/modifies files after that commit.

**Why it matters:** Any graph-based review of this scope is incomplete until the graph is rebuilt. Not a code defect.

**Fix:** Rebuild the Graphify graph at the current HEAD once the scope is committed.

---

## NO ISSUE — categories checked and found correct

- **Wiring/registration completeness:** all 3 experiments registered in `_REGISTERED_WORKFLOWS`, `_CAMPAIGN_ORDER`, `_EXPERIMENT_DISPATCH_HANDLERS`, `_EXPERIMENT_REPORT_HANDLERS`, and `_ANALYSIS_MARKER_CHECKS`; the consistency tests lock order and anchor-gating; `test_federated_estimation_registration.py` locks declaration contents (5 methods for comparison/quantile, 3 for fixed-coefficient, family/cluster excluded from fixed-coefficient).
- **CLI call chain:** real production entrypoint traced — CLI smoke/report/status -> `run_experiment` -> `_dispatch_*` -> `run_*_seed` -> `_run_estimation_seed` -> `execute_declared_experiment_seed` -> plan/build/execute_campaign -> evaluation document; report path -> `_generate_experiment_report` -> `report_*` -> `_finalize_report` writes COMPLETE marker only after all seeds resolved.
- **Anchor-gating:** 3 new entries are anchor-gated; `_EXPECTED_ANCHOR_GATED_EXPERIMENTS` in the consistency test matches.
- **Benign-only construction:** `construct_federated_benign_statistics` consumes benign-only calibration; no attack labels enter threshold construction.
- **Eligibility:** per-method eligibility and `n_k >= 100` handling remain in the declaration/planning path; no weakening introduced.
- **Threshold math:** B-FedStatsBenign pooled-variance decomposition (within/between/full), between-ratio, Gaussian-matched exceedance, and the k in {2.0,2.5,3.0} curve are correct; the k-grid matches roadmap §9.3 and `SUMMARY_COEFFICIENTS`.
- **Deterministic seeded execution:** CONFIRMATORY_SEED_COHORT (seeds 0-9), explicit `Seed`/`SeedCohort`, output coordinates deterministic; no new randomness.
- **Typed boundaries:** no `Any`, no untyped domain dicts at stage boundaries; report rows are frozen dataclasses, serialized via `asdict` at the output boundary; `StrictModel`/enum contracts preserved.
- **Artifact lifecycle:** reports write under `federated_threshold_estimation/<experiment>/<population>/analysis/`, reuse `OUTPUTS_ROOT`; COMPLETE marker only after all required seeds resolve; no temp files in output dirs.

---

## Validation performed

- Read the full roadmap (incl. §6, §9.1, §9.2, §9.3, §4.5, evaluation contract §8.2-8.4).
- Read the implementation report; treated as untrusted.
- Read the new workflow module, campaign registration/dispatch/handlers, experiment declarations, thresholding method, evaluation execution, workspace communication accounting, communication enum, calibration protocol, and both workflow test files.
- Grepped all production consumers of `fixed_coefficient_curve` and `estimated_communication_bytes` (found only a test for the former, nothing for the latter).
- Traced the CLI -> dispatch -> seed -> execute_declared_experiment_seed -> evaluation chain and the report chain.
- Ran registration tests (19 passed), thresholding tests (58 passed); programme/declaration validation passes.

## Remaining issues

All actionable findings above (F1-F6) are open. F1 and F2 are blockers for claiming this scope "Complete": F1 fabricates a scientific value, F2 duplicates an experiment rather than delivering the roadmap §9.2 outcomes.
