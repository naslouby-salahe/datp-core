# Action plan

## 1. Scientific integrity and runtime provenance

1. **AP-01 (II-03 / TS-001):** Bind B0 training and score reuse to persisted coordinate, architecture/schema, preprocessing, split, selected candidate, feature-value/input checksums. Reject stale reuse; add changed-provenance reuse tests. This protects independent centralized reference semantics.
2. **AP-02 (II-04 / AS-001):** Persist checkpoint-selection identity/status in score/evaluation provenance and validate it in anchor observation creation. Add wrong-checkpoint artifact integration test.
3. **AP-03 (II-02):** Build threshold-estimation oracle from eligible calibration scores, separate calibration-oracle vs held-out-attainment checksums, and regress test-leakage.
4. **AP-04 (II-01):** Complete B-FedStatsBenign message/provenance contract (per-client benign exceedance statistic, n/mean/variance disclosure, byte estimate); verify no attack input.

## 2. Missing workflow/report wiring

5. **AP-05 (WL-07):** In the live confirmation cluster collector, produce `GroupedDispersionResult` from B4 membership/local thresholds/B4 FPR and append to mechanism evidence; add integration publication test. Then delete dead bundle DC-03.
6. **AP-06 (WL-01, WL-06):** Add independent B0 report consumption for Regime A and CIC contextual B0 route/report. B0 must retain its own pooled preprocessing/model/scores; do not reuse federated state.
7. **AP-07 (WL-05):** Add Edge FedStats report consumer publishing benign-only FPR/equity/estimator/communication evidence and typed unavailable attack outcomes.
8. **AP-08 (WL-02, WL-03, WL-04, WL-08):** Gate anchor-required reports; validate handoff before full dependent execution; split execution vs publication completion markers; move optional analyses off mandatory campaign path.

## 3. Authorized protocol decisions before enabling blocked work

9. **AP-09 (II-05–07):** Obtain—not infer—calibration replicate count, temporal materiality/recovery criteria, and traffic-rate evidence provenance. Persist values and only then enable the relevant routes.

## 4. Reduction and hardening after correctness

10. **AP-10 (DC-01–06):** Delete legacy preprocessing island, dead wrappers, exact unused registry, and test-only helpers after migrating tests to canonical guards. No aliases/shims.
11. **AP-11 (AD-02–04, PL-01):** Canonicalize duplicated execution identity; add split handoff equality assertion; reconcile shadow specs before removal; type traffic evidence only when operational programme is enabled.

Validation for every action: relevant focused tests plus full `pytest -q`, Ruff, Pyright, `datp-core validate`, plan/status checks; add provenance/artifact-reload regression cases where applicable. The order intentionally fixes science and runtime correctness before reducing LOC.

