# Phase 2 — Complete DATP Anchor Implementation

The phase implements and validates the anchor pipeline without conducting an anchor campaign. The roadmap is scientific authority, the architecture is technical authority, and the master log governs ticket identity and dependencies.

## Phase boundary

- **Scientific execution.** Each ticket is `FORBIDDEN` or `PLANNING_ONLY`; none is campaign-execution authorized.
- **Campaign scope.** `ANCHOR`.
- **Purpose.** Recover reference behavior and implement N-BaIoT source/partition/split/preprocessing/training/checkpoint/scoring, B0–B4, evaluation, statistics, artifacts, reports, inventory, dry-run planning, and readiness using synthetic validation.
- **Allowed.** Read-only reference/source/schema inspection; synthetic tests; dry-run planning; expected-artifact inventory; readiness evaluation.
- **Forbidden.** Real N-BaIoT training/scoring/thresholds/metrics; real-data smoke/debug work; partial campaigns; guessed seed order; scientific outputs; result-driven tuning.
- **Entry.** `P1-T070` is `DONE`.
- **Exit.** Synthetic pipeline validation passes; recovered semantics are resolved or explicitly blocked; readiness is evaluated without real execution.
- **Gate.** `P2-T020` — anchor readiness evaluator and anchor-implementation audit.
- **Ticket count.** 23 expected / 23 extracted; `P2-T001`–`P2-T023` are preserved with no additions, splits, renumbering, or retirement.
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Ordered tickets

| ID | Title | Type | Priority | Sci-exec | Dependencies |
|---|---|---|---|---|---|
| [P2-T001](P2-T001.md) | Recover DATP behavioral semantics from the reference repository (read-only) | data | P0 — Blocking | PLANNING_ONLY | P1-T070. |
| [P2-T002](P2-T002.md) | Record the recovered-semantics register in the master log | data | P0 — Blocking | PLANNING_ONLY | P2-T001. |
| [P2-T003](P2-T003.md) | Inspect the N-BaIoT source and feature schema | data | P0 — Blocking | FORBIDDEN | P2-T001, P1-T032. |
| [P2-T004](P2-T004.md) | Implement the N-BaIoT source adapter and deterministic source-row identity | data | P0 — Blocking | FORBIDDEN | P2-T003, P1-T042. |
| [P2-T005](P2-T005.md) | Implement physical-device (9-client) partitioning | data | P0 — Blocking | FORBIDDEN | P2-T004, P1-T019. |
| [P2-T006](P2-T006.md) | Implement benign train/calibration and held-out benign/malicious test splits | data | P0 — Blocking | FORBIDDEN | P2-T005. |
| [P2-T007](P2-T007.md) | Implement preprocessing fit authorization and streaming transform | preprocessing | P0 — Blocking | FORBIDDEN | P2-T006, P1-T020. |
| [P2-T008](P2-T008.md) | Implement the fixed autoencoder, optimizer, and scheduler | training | P0 — Blocking | FORBIDDEN | P2-T007, P1-T043, P2-T001. |
| [P2-T009](P2-T009.md) | Implement FedAvg training (E=1, full participation, deterministic CUDA) | training | P0 — Blocking | FORBIDDEN | P2-T008, P1-T044. |
| [P2-T010](P2-T010.md) | Implement the checkpoint schedule, persistence, and Regime-A global selection | checkpoint | P0 — Blocking | FORBIDDEN | P2-T009, P2-T002, P1-T022. |
| [P2-T011](P2-T011.md) | Implement calibration, benign-test, and malicious-test scoring with atomic score bundles | scoring | P0 — Blocking | FORBIDDEN | P2-T010, P1-T045. |
| [P2-T012](P2-T012.md) | Implement B0 centralized training branch | threshold | P1 — Mandatory | FORBIDDEN | P2-T006, P1-T044. |
| [P2-T013](P2-T013.md) | Implement canonical anchor B1 shared construction | threshold | P0 — Blocking | FORBIDDEN | P2-T011, P1-T024. |
| [P2-T014](P2-T014.md) | Implement B2 per-client and B3 family constructions | threshold | P0 — Blocking | FORBIDDEN | P2-T013. |
| [P2-T015](P2-T015.md) | Implement canonical anchor B4 exact k-means++ clustering and cluster-mean thresholds (K=3) | threshold | P1 — Mandatory | FORBIDDEN | P2-T014, P1-T025. |
| [P2-T016](P2-T016.md) | Implement per-client confusion counts and operating-point metrics | evaluation | P0 — Blocking | FORBIDDEN | P2-T013, P2-T014, P2-T015, P2-T023, P1-T026. |
| [P2-T017](P2-T017.md) | Implement detection-quality metrics (AUROC control, Macro-F1, P10, worst-client BA) | evaluation | P0 — Blocking | FORBIDDEN | P2-T016. |
| [P2-T018](P2-T018.md) | Implement paired deltas, BCa bootstrap, Wilcoxon, Cliff's delta, reference diagnostics | statistics | P0 — Blocking | FORBIDDEN | P2-T017, P1-T046. |
| [P2-T019](P2-T019.md) | Implement anchor report models, expected-artifact inventory, and dry-run planner | reporting | P0 — Blocking | PLANNING_ONLY | P2-T018, P1-T049. |
| [P2-T020](P2-T020.md) | Implement the anchor readiness evaluator and anchor-implementation audit | audit | P0 — Blocking | PLANNING_ONLY | P2-T019, P2-T002, P1-T040. |
| [P2-T021](P2-T021.md) | Implement B0 centralized checkpoint schedule and scientific checkpoint selection | checkpoint | P1-Mandatory | FORBIDDEN | P2-T012, P2-T002, P1-T022. |
| [P2-T022](P2-T022.md) | Implement B0 centralized calibration and held-out score generation | scoring | P1-Mandatory | FORBIDDEN | P2-T021, P1-T045. |
| [P2-T023](P2-T023.md) | Implement B0 pooled threshold, evaluation, statistics, and reporting route | evaluation | P1-Mandatory | FORBIDDEN | P2-T022, P1-T026, P1-T049. |

## Dependency sequence and gate coverage

Anchor path: `P2-T001 → P2-T002`; `P2-T003 → P2-T004 → P2-T005 → P2-T006 → P2-T007 → P2-T008 → P2-T009 → P2-T010 → P2-T011 → P2-T013 → P2-T014 → P2-T015 → P2-T016 → P2-T017 → P2-T018 → P2-T019 → P2-T020`. B0 route: `P2-T012 → P2-T021 → P2-T022 → P2-T023 → P2-T016`; therefore it reaches the phase gate. `P2-T002` and `P1-T040` directly feed `P2-T020`. All 23 tickets are mandatory (18 P0-blocking, 5 P1-mandatory); authority-conditional facts block the affected route instead of being guessed.

## Recovered semantics, readiness, and authority finding

`P2-T001` owns read-only behavioral recovery; `P2-T002` owns the structured register. Relevant tickets require evidence, authority reconciliation, architecture representation, differences, tests, uncertainty, and blocker status. `P2-T020` aggregates print-grade blockers into `ScientificReadinessResult` and runs the synthetic anchor simulation.

The master log says both that `P2-T021`–`P2-T023` are fully reconstructed and, in a retained legacy note, that they are unvalidated. Its compact Phase 2 index and detailed ticket bodies also differ for `P2-T003` (scientific-execution classification and roadmap ID), `P2-T008` (dependency), `P2-T011` (block), `P2-T012` (type), and `P2-T023` (dependency/block), with further roadmap-ID drift. These standalone files preserve the detailed Section H ticket bodies and flag every conflict for a separately authorized master-log correction; this task does not alter authority metadata.

## Responsibility ownership

| Responsibility | Owner |
|---|---|
| Reference evidence | `P2-T001` |
| Recovered-semantics register | `P2-T002` |
| N-BaIoT schema/source, clients, splits, preprocessing | `P2-T003`–`P2-T007` |
| Fixed FedAvg AE, training, selection, scoring | `P2-T008`–`P2-T011` |
| Centralized B0 branch | `P2-T012`, `P2-T021`–`P2-T023` |
| B1, B2/B3, B4 | `P2-T013`, `P2-T014`, `P2-T015` |
| Evaluation/statistics | `P2-T016`–`P2-T018` |
| Reports, inventory, dry-run | `P2-T019` |
| Synthetic E2E, execution prohibition, readiness, gate | `P2-T020` |

## Unresolved blockers

- `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` persists until historical schedule, ranking, and tie-break evidence are recovered; the journal schedule is never a substitute.
- AE/optimizer/scheduler, preprocessing/split and batch semantics, B4 scaler/`n_init`/`max_iter`, bootstrap resample count, and anchor-honesty tolerance must be recovered or recorded as blockers before print-grade completion.
- The retained master-log legacy-note and index/body conflicts are findings only; no authority file is changed by this task.
