# DATP-Core Graphify-assisted audit: final report

## Executive verdict

**NOT READY — BOTH SCIENTIFIC AND RUNTIME ISSUES.**

Confirmed: 6 dead/test-only components (including one four-module island), 8 required/disconnected workflow paths, 7 incomplete/runtime/scientific defects (four high severity), 2 duplicate-declaration concerns, and 1 meaningful primitive/provenance leak. There are no confirmed stale compatibility shims/redirects or production-to-test dependencies. One execution-time anchor-handoff issue is suspected rather than confirmed; split recomputation is a hardening opportunity, not a demonstrated drift defect.

Most serious issues, in remediation order:

1. B0 cache reuse can silently rebrand stale preprocessing/split/model artifacts as a current centralized reference.
2. The anchor adapter asserts historical checkpoint status instead of verifying it from artifact provenance.
3. Threshold-estimation oracle diagnostics use held-out evaluation scores.
4. B-FedStatsBenign message/disclosure contract is incomplete; Edge comparator evidence is executed but unreported.
5. Required cluster grouped-dispersion evidence is implemented but disconnected.
6. B0 has no Regime-A report consumer and no CIC contextual route.

## Workflow summary

The CLI roots, registries, materializers, persisted preprocessing, FedAvg/FedProx/Ditto paths, checkpoint selection, scoring, evaluation, metrics, fixed-score checks, and paired BCa path are real and source-verified. The key divergences are downstream provenance/report wiring rather than absence of the core B1/B2 implementation. Campaign completion currently overstates publication completion, and direct reports can bypass general anchor gating.

## Journal coverage summary

- Fully implemented / live: core fixed-score ladder; eligibility; metrics/inference; N-BaIoT/CIC/Edge data boundaries; FedAvg, FedProx, Ditto; temporal mechanics; threshold variants except authorized values.
- Disconnected: grouped dispersion; B0 reporting; Edge FedStats reporting; CIC B0; anchor report/handoff gates; publication-completion semantics.
- Incomplete: FedStats disclosure; unresolved calibration/temporal/traffic protocol values (correctly fail-closed).
- Scientifically drifted/runtime defect: B0 reuse provenance; anchor checkpoint evidence; held-out diagnostic oracle.
- Intentionally unavailable: alert burden, size-aware shrinkage formula, calibration-repeat and temporal-decision execution pending authorized constants.

## Dead-code and architecture summary

Only confirmed candidates are in `03_DEAD_CODE_LEDGER.md`; the largest safe reduction is removal of the unreachable legacy preprocessing island. Do not simplify persisted artifact/protocol layers: they encode scientific provenance. Reconcile shadow `ExperimentSpec` declarations before any deletion.

## Test summary

Full suite: **819 passed**; Ruff and Pyright clean. Passing tests do not negate the defects above because current tests do not exercise stale B0 provenance or anchor adapter relabelling. Preserve a CUDA CI lane.

## Recommended execution order

Follow [`11_ACTION_PLAN.md`](11_ACTION_PLAN.md). The complete evidence base is in the numbered ledgers and `subagents/` reports.

