# Phase 4 — Complete Journal-Extension Implementation

## Phase identity

- **Canonical phase number and code.** 4 / `phase-4`.
- **Purpose.** Implement every mandatory journal experiment family, analysis, feasibility/suppression path, claim/report model, and synthetic validation route without performing a journal campaign.
- **Permitted work.** Synthetic tests, test doubles, dry-run expansion, expected-artifact planning, read-only frozen-anchor lineage inspection, and read-only dataset feasibility inspection where a ticket allows it.
- **Forbidden work.** Every real journal training, scoring, threshold sweep, q-sensitivity, stress test, external/temporal experiment, reduced/one-cell/debug run, real-data smoke test, or scientific integration test.
- **Entry criteria.** The integrity-based `P3-T011` journal-unlock gate has passed where required; an integrity-valid weak/null anchor is not rejected for direction.
- **Exit criteria.** All mandatory journal implementation paths are synthetically validated, every optional/conditional path has a valid terminal record, reporting/inventory is complete, and no journal campaign output exists.
- **Expected and actual ticket count.** 26 / 26.
- **Phase gate.** [`P4-T026`](P4-T026.md).
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Implementation-only and scientific boundary

E-C1 remains the sole confirmatory endpoint: Regime A, B1 versus B2, CV(FPR), paired ten-seed delta, 95% BCa interval, positive direction. B1–B4 use one fixed selected model state and compatible calibration/test score artifacts within each cell; threshold scope alone differs. Stress tests, comparators, external validation, and temporal work remain outside the ladder.

No ticket authorizes a journal `RunIdentity`, `ExecutionAttemptId`, scientific artifact write, or real journal result. Synthetic validation must use test-only namespaces. Frozen anchor artifacts are read-only and cannot be substituted across the five-seed anchor cohort and the distinct ten-seed E-C1 cohort merely because schemas look compatible.

## Ordered tickets and dependency sequence

| ID | Title | Type | Priority | Sci-exec | Dependencies | Blocks |
|---|---|---|---|---|---|---|
| [P4-T001](P4-T001.md) | Implement E-C1 confirmatory experiment specification and identity | experiment | P0 — Blocking | FORBIDDEN | P3-T011, P1-T029. | P4-T022. |
| [P4-T002](P4-T002.md) | Implement E-S1 construction-sensitivity and E-S2 q-sensitivity | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T003](P4-T003.md) | Implement E-S3 Dirichlet severity (Regime C) | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T004](P4-T004.md) | Implement E-M1 cluster/family granularity and stability | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T005](P4-T005.md) | Implement E-M2 B4 cluster-feature ablation and contingency | experiment | P1 — Mandatory | FORBIDDEN | P4-T004. | P4-T022. |
| [P4-T006](P4-T006.md) | Implement E-M3 per-client CDF overlays and Ennio deep dive | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T007](P4-T007.md) | Implement E-M4 JS↔gain association and E-M5 threshold-shift scatter | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T008](P4-T008.md) | Implement E-V1 calibration-size sweep and size-aware fallback | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T009](P4-T009.md) | Implement E-V2 local-global shrinkage (τ-shrink) | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T010](P4-T010.md) | Implement E-V3 split-conformal B2-conf and conformal coverage | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T011](P4-T011.md) | Implement the B-a CICIoT2023 boundary | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T012](P4-T012.md) | Implement B-b/temporal CICIoT2023 rejection and suppression records | feasibility | P1 — Mandatory | PLANNING_ONLY | P1-T007, P4-T011. | P4-T022. |
| [P4-T013](P4-T013.md) | Implement the Regime D Edge-IIoTset source/schema/feasibility audit | feasibility | P2 — Conditional | FORBIDDEN | P4-T001, P1-T040. | P4-T014. |
| [P4-T014](P4-T014.md) | Implement Regime D partitioning, preprocessing, training, and scoring | data | P2 — Conditional | FORBIDDEN | P4-T013. | P4-T015, P4-T019. |
| [P4-T015](P4-T015.md) | Implement E-X1 external validation | experiment | P2 — Conditional | FORBIDDEN | P4-T014, P4-T018. | P4-T022. |
| [P4-T016](P4-T016.md) | Implement E-T1 FedProx aggregation stress test | experiment | P1 — Mandatory | FORBIDDEN | P4-T001, P1-T044. | P4-T022. |
| [P4-T017](P4-T017.md) | Implement E-T2 model-personalization stress test and absorption bands | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T022. |
| [P4-T018](P4-T018.md) | Implement E-T3 B-FedStatsBenign matched comparator | experiment | P1 — Mandatory | FORBIDDEN | P4-T001, P1-T025. | P4-T015, P4-T022. |
| [P4-T019](P4-T019.md) | Implement E-B1 temporal recalibration MVE | experiment | P2 — Conditional | FORBIDDEN | P4-T014, P4-T024. | P4-T022. |
| [P4-T020](P4-T020.md) | Implement mandatory E-O1 alert burden evidence and suppression route | experiment | P1 — Mandatory | FORBIDDEN | P4-T001. | P4-T026. |
| [P4-T021](P4-T021.md) | Implement claim tiers, fallback wording, and report schemas/renderers | reporting | P0 — Blocking | FORBIDDEN | P4-T001, P1-T049. | P4-T022. |
| [P4-T022](P4-T022.md) | Implement journal expected-artifact/table/figure inventory and completeness audit | audit | P0 — Blocking | PLANNING_ONLY | P4-T002, P4-T003, P4-T004, P4-T005, P4-T006, P4-T007, P4-T008, P4-T009, P4-T010, P4-T011, P4-T012, P4-T013, P4-T014, P4-T015, P4-T016, P4-T017, P4-T018, P4-T019, P4-T020, P4-T021. | P4-T026. |
| [P4-T023](P4-T023.md) | Record optional E-Q1–E-Q6 selections and implement selected supplements | experiment | P3-Optional | FORBIDDEN | P4-T001. | P4-T026, P5-T002. |
| [P4-T024](P4-T024.md) | Resolve chronological temporal training/calibration allocation | feasibility | P0-Blocking | PLANNING_ONLY | P4-T001. | P4-T019,P5-T004,P6-T004,P7-T008. |
| [P4-T025](P4-T025.md) | Produce Appendix A B2 calibration-versus-held-out FPR analysis | reporting | P1-Mandatory | FORBIDDEN | P4-T001,P4-T008,P4-T009,P4-T010. | P4-T026,P7-T011. |
| [P4-T026](P4-T026.md) | Complete journal implementation audit and phase gate | audit | P0-Blocking | PLANNING_ONLY | P4-T022,P4-T023,P4-T024,P4-T025. | P5-T001. |

`P4-T001` opens the core implementation branches. Regime D follows `P4-T013 → P4-T014 → P4-T015`, with `P4-T018` also required by `P4-T015`; temporal work requires `P4-T014` and `P4-T024`; `P4-T022`, `P4-T023`, `P4-T024`, and `P4-T025` feed `P4-T026`. Numeric order is not dependency order. Mandatory tickets are the P0/P1 priority entries, conditional tickets are P2, and P4-T023 is P3 optional; every conditional/optional ticket requires a valid terminal-state record.

## Authority discrepancy and gate coverage

`P4-T022`'s master-log Section G index lists `P4-T023`–`P4-T025` as dependencies and `P5-T001` as its block, while its detailed Section H body lists a different dependency set and blocks `P4-T026`. This extraction preserves the detailed ticket body as the standalone field source and records the discrepancy rather than silently rewriting the authority. Gate coverage remains fail-closed because `P4-T026` directly depends on `P4-T022`–`P4-T025`; it alone certifies terminal-state completeness before `P5-T001`.

Section G and Section H also differ on downstream edges for `P4-T023` (`P5-T002` appears only in Section H) and `P4-T024` (`P7-T008` appears only in Section H). These cross-phase edges remain recorded in the standalone detailed fields and must be reconciled in the master authority by separately authorized work; this task does not choose a silent replacement.

Several detailed `Architecture contracts/types owned` labels are master-log ownership labels rather than literal architecture type definitions. Future implementation must map them to existing architecture contracts or obtain an explicit architecture decision; this documentation does not falsely claim they already exist.

Canonical IDs `P4-T001`–`P4-T026` are preserved. No ticket was added, split, moved, or renumbered. Unresolved blockers are authority/feasibility-specific and are carried by the relevant ticket; no implementation status is inferred from this documentation.
