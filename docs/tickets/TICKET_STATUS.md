# Ticket Status Register

**Status.** ACTIVE — single operational status register for every ticket extracted from `docs/MASTER_TICKET_LOG.md` into `docs/tickets/`.

This file and each standalone ticket file's own `Status` field must always agree. A mismatch between this file and a ticket file is a blocking defect and must be resolved before either is treated as authoritative.

## Register metadata — Phase 0

- **Selected phase.** Phase 0 — Repository and Engineering Foundation.
- **Canonical phase code.** `phase-0` (directory `docs/tickets/phase-0/`; ticket ID prefix `P0-`).
- **Expected ticket count (per `docs/MASTER_TICKET_LOG.md`).** 26 (`P0-T001`–`P0-T026`).
- **Extracted ticket count (this register).** 27 (`P0-T001`–`P0-T026` preserved verbatim by ID, plus one added ticket `P0-T027`; see "Added ticket" below).
- **Added ticket.** `P0-T027` — Configure SonarQube/SonarCloud analysis and quality gate. Added because the ticket-conversion task instructions (Section 16 of the conversion task) mandate a Sonar quality gate in every ticket's validation requirements, no existing Phase 0 ticket can absorb project-wide Sonar configuration without overloading a single-tool-configuration responsibility (the existing pattern is one ticket per tool: `P0-T007` Ruff, `P0-T008` Pyright, `P0-T009` pytest, `P0-T010` Hypothesis, `P0-T011` import-linter, `P0-T012` pytest-archon, `P0-T013` syrupy), and `P0-T014` (Nox session wiring) explicitly forbids "business logic in sessions," which Sonar project configuration would violate if folded in. `P0-T027` is a genuinely new tool-configuration ticket, not a renumbering of an existing one; no existing ID was reused or altered. `docs/MASTER_TICKET_LOG.md` itself is unchanged by this addition — the addition exists only in `docs/tickets/`.
- **Phase-gate ticket.** `P0-T026` — Establish implementation-task governance and repository baseline quality gate. Its dependency list has been extended in the standalone ticket file to include `P0-T027` in addition to the 25 dependencies already present in the master log (`P0-T001`–`P0-T025`), so the gate cannot pass without the Sonar ticket.
- **Current active ticket.** NONE — no ticket has been started; this is a document-conversion task only.
- **Next eligible ticket.** `P0-T001` (the only Phase 0 ticket with no dependencies).
- **Unresolved blockers.** NONE — Phase 0 raises no scientific or architectural blocker per `docs/MASTER_TICKET_LOG.md` Section F ("Authority blockers. None. Phase 0 is pure tooling/governance scaffolding and raises no scientific blocker.").
- **Resolved authority-document inconsistency (historical note).** `docs/MASTER_TICKET_LOG.md` Section G previously listed priority `P0` in its compact table for `P0-T007`, `P0-T010`, `P0-T013`, and `P0-T021`, contradicting Section H's `P1-Mandatory` for those same four tickets and Section F's own phrasing ("all `P0-Blocking`/`P1-Mandatory`", implying a mix). This was corrected directly in `docs/MASTER_TICKET_LOG.md` Section G to read `P1` for these four rows, matching Section H and Section F, at the user's explicit request. The four standalone ticket files (`P0-T007.md`, `P0-T010.md`, `P0-T013.md`, `P0-T021.md`) already used `P1 — Mandatory` and required no change. All three sections of the master log now agree.
- **Last updated.** 2026-07-14T00:00:00Z (ticket-extraction task; no implementation performed).
- **Roadmap last-read timestamp.** 2026-07-14 (`docs/Journal_Extension_Master_Roadmap.md`, Section A cross-check read during extraction).
- **Architecture last-read timestamp.** 2026-07-14 (`docs/DATP Core Architecture.md`, Sections 1–5, 21, 24, 29 read directly during extraction; full table of contents verified against every cited section number).
- **Master-log last-read timestamp.** 2026-07-14 (`docs/MASTER_TICKET_LOG.md`, Sections A–H, Phase 0 in full).

## Register metadata — Phase 1

- **Selected phase.** Phase 1 — Complete Technical Socle.
- **Canonical phase code.** `phase-1` (directory `docs/tickets/phase-1/`; ticket ID prefix `P1-`).
- **Expected ticket count (per `docs/MASTER_TICKET_LOG.md`).** 66 (`P1-T001`–`P1-T070`, with `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` already retired by the master log's own prior mega-ticket decomposition, recorded in the master log's reconstruction-status note, before this extraction began).
- **Extracted ticket count (this register).** 66 (`P1-T001`–`P1-T070`, exactly matching the master log's post-decomposition set, preserved verbatim by canonical ID). No ticket was added or split during this extraction.
- **Added ticket.** NONE. Every cross-cutting responsibility this conversion task requires (Sonar, Pyright/Pylance parity, raw-dictionary prohibition, ticket/document-reference prohibition, stale-documentation enforcement, ticket-status governance, repository-wide post-implementation audits, the scientific-drift audit mechanism) is already owned by an existing Phase 0 ticket per `docs/tickets/phase-0/README.md`; every Phase 1 ticket defers to those owners in its own Part B, Section B13. See `docs/tickets/phase-1/README.md` for full detail.
- **Phase-gate ticket.** `P1-T070` — Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test. Depends on all 65 other Phase 1 tickets; blocks `P2-T001` (outside this extracted phase).
- **Current active ticket.** NONE — no ticket has been started; this is a document-conversion task only.
- **Next eligible ticket.** `P1-T001`, `P1-T002`, `P1-T003`, `P1-T004`, `P1-T005`, `P1-T006`, `P1-T007`, `P1-T008`, `P1-T009`, `P1-T030`, `P1-T051`, `P1-T052`, `P1-T053` — every Phase 1 ticket whose sole dependency is the already-`NOT_STARTED`-but-Phase-0-scoped `P0-T026`/`P0-T006`; none is yet `READY` because `P0-T026` itself has not been marked `DONE` in this register (Phase 0 tickets are all still `NOT_STARTED`, per the Phase 0 table above). No Phase 1 ticket is `READY` until Phase 0's gate is `DONE`.
- **Unresolved blockers.** NONE at the phase-extraction level. Individual tickets carry their own conditional per-ticket "Stop conditions" (inherited-semantics values such as the exact Edge-IIoTset first-70% train/calibration split, the final AE architecture, the FedProx µ-grid, and the B4 scaler/`n_init`/`max_iter` constants) that must be resolved before that specific ticket reaches `DONE`; these are recorded in the affected tickets' own files and are not phase-blocking for scheduling purposes.
- **Last updated.** 2026-07-14T00:00:00Z (ticket-extraction task; no implementation performed).
- **Roadmap last-read timestamp.** 2026-07-14 (`docs/Journal_Extension_Master_Roadmap.md`, read in full during extraction).
- **Architecture last-read timestamp.** 2026-07-14 (`docs/DATP Core Architecture.md`, Sections 1–8 read in full during extraction; Sections 9, 12, 15–22, 25, 27, 29 read section-by-section as cited by individual Phase 1 tickets during their reconstruction).
- **Master-log last-read timestamp.** 2026-07-14 (`docs/MASTER_TICKET_LOG.md`, Sections A–H, Phase 1 in full — all 66 ticket bodies read completely).



## Register metadata — Phase 2

- **Selected phase.** Phase 2 — Complete DATP Anchor Implementation.
- **Canonical phase code.** `phase-2` (directory `docs/tickets/phase-2/`; ticket prefix `P2-`).
- **Expected ticket count.** 23 (`P2-T001`–`P2-T023`) per `docs/MASTER_TICKET_LOG.md`.
- **Extracted ticket count.** 23; all IDs preserved with no addition, split, renumbering, or retirement.
- **Phase gate.** `P2-T020`; direct dependencies: `P2-T019`, `P2-T002`, and `P1-T040`; all Phase 2 routes are transitively covered.
- **Current active ticket.** NONE — conversion is not implementation.
- **Next eligible ticket.** NONE — `P1-T070` is `NOT_STARTED`.
- **Unresolved blockers.** Recovered anchor semantics, including the historical checkpoint protocol, must be resolved or carried to readiness; never guessed or resolved by real execution.
- **Authority finding.** The master log conflicts about the reconstruction status of `P2-T021`–`P2-T023`. Its Phase 2 index and detailed bodies also differ for `P2-T003` (scientific-execution classification and roadmap ID), `P2-T008` (dependency), `P2-T011` (block), `P2-T012` (type), and `P2-T023` (dependency/block), with further roadmap-ID drift. The standalone files preserve the detailed ticket bodies; the authority is unchanged.
- **Last updated.** 2026-07-14 (Phase 2 documentation conversion; no implementation/scientific execution).
- **Roadmap last-read timestamp.** 2026-07-14 (complete authority read).
- **Architecture last-read timestamp.** 2026-07-14 (complete authority read).
- **Master-log last-read timestamp.** 2026-07-14 (complete authority read; Phase 2 bodies re-read).

## Ticket table — Phase 2

All rows remain `NOT_STARTED`; documentation creation does not implement tickets.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2-T001 | Recover DATP behavioral semantics from the reference repository (read-only) | NOT_STARTED | P1-T070. | — | — | — | — | — | — | — | NONE | — |
| P2-T002 | Record the recovered-semantics register in the master log | NOT_STARTED | P2-T001. | — | — | — | — | — | — | — | NONE | — |
| P2-T003 | Inspect the N-BaIoT source and feature schema | NOT_STARTED | P2-T001, P1-T032. | — | — | — | — | — | — | — | NONE | — |
| P2-T004 | Implement the N-BaIoT source adapter and deterministic source-row identity | NOT_STARTED | P2-T003, P1-T042. | — | — | — | — | — | — | — | NONE | — |
| P2-T005 | Implement physical-device (9-client) partitioning | NOT_STARTED | P2-T004, P1-T019. | — | — | — | — | — | — | — | NONE | — |
| P2-T006 | Implement benign train/calibration and held-out benign/malicious test splits | NOT_STARTED | P2-T005. | — | — | — | — | — | — | — | NONE | — |
| P2-T007 | Implement preprocessing fit authorization and streaming transform | NOT_STARTED | P2-T006, P1-T020. | — | — | — | — | — | — | — | NONE | — |
| P2-T008 | Implement the fixed autoencoder, optimizer, and scheduler | NOT_STARTED | P2-T007, P1-T043, P2-T001. | — | — | — | — | — | — | — | NONE | — |
| P2-T009 | Implement FedAvg training (E=1, full participation, deterministic CUDA) | NOT_STARTED | P2-T008, P1-T044. | — | — | — | — | — | — | — | NONE | — |
| P2-T010 | Implement the checkpoint schedule, persistence, and Regime-A global selection | NOT_STARTED | P2-T009, P2-T002, P1-T022. | — | — | — | — | — | — | — | NONE | — |
| P2-T011 | Implement calibration, benign-test, and malicious-test scoring with atomic score bundles | NOT_STARTED | P2-T010, P1-T045. | — | — | — | — | — | — | — | NONE | — |
| P2-T012 | Implement B0 centralized training branch | NOT_STARTED | P2-T006, P1-T044. | — | — | — | — | — | — | — | NONE | — |
| P2-T013 | Implement canonical anchor B1 shared construction | NOT_STARTED | P2-T011, P1-T024. | — | — | — | — | — | — | — | NONE | — |
| P2-T014 | Implement B2 per-client and B3 family constructions | NOT_STARTED | P2-T013. | — | — | — | — | — | — | — | NONE | — |
| P2-T015 | Implement canonical anchor B4 exact k-means++ clustering and cluster-mean thresholds (K=3) | NOT_STARTED | P2-T014, P1-T025. | — | — | — | — | — | — | — | NONE | — |
| P2-T016 | Implement per-client confusion counts and operating-point metrics | NOT_STARTED | P2-T013, P2-T014, P2-T015, P2-T023, P1-T026. | — | — | — | — | — | — | — | NONE | — |
| P2-T017 | Implement detection-quality metrics (AUROC control, Macro-F1, P10, worst-client BA) | NOT_STARTED | P2-T016. | — | — | — | — | — | — | — | NONE | — |
| P2-T018 | Implement paired deltas, BCa bootstrap, Wilcoxon, Cliff's delta, reference diagnostics | NOT_STARTED | P2-T017, P1-T046. | — | — | — | — | — | — | — | NONE | — |
| P2-T019 | Implement anchor report models, expected-artifact inventory, and dry-run planner | NOT_STARTED | P2-T018, P1-T049. | — | — | — | — | — | — | — | NONE | — |
| P2-T020 | Implement the anchor readiness evaluator and anchor-implementation audit | NOT_STARTED | P2-T019, P2-T002, P1-T040. | — | — | — | — | — | — | — | NONE | — |
| P2-T021 | Implement B0 centralized checkpoint schedule and scientific checkpoint selection | NOT_STARTED | P2-T012, P2-T002, P1-T022. | — | — | — | — | — | — | — | NONE | — |
| P2-T022 | Implement B0 centralized calibration and held-out score generation | NOT_STARTED | P2-T021, P1-T045. | — | — | — | — | — | — | — | NONE | — |
| P2-T023 | Implement B0 pooled threshold, evaluation, statistics, and reporting route | NOT_STARTED | P2-T022, P1-T026, P1-T049. | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 2 register

- Ticket-file and register statuses must always agree; mismatch is blocking.
- `P2-T020` cannot be `DONE` until all mandatory responsibilities reach valid terminal states through the authoritative graph and the synthetic anchor simulation passes.
- No implementation status, audit result, timestamp, evidence, or scientific result was fabricated by this conversion.



## Status values

`NOT_STARTED` · `READY` · `IN_PROGRESS` · `BLOCKED` · `IN_REVIEW` · `DONE` · `REJECTED` · `NOT_APPLICABLE`

## Transition rules

- `NOT_STARTED → READY` only when every dependency has the terminal state required by the consuming ticket; unconditional dependencies normally require `DONE`, while conditional/optional branches must honor their ticket-specific accepted-terminal-state rule.
- `READY → IN_PROGRESS` immediately before implementation begins.
- `IN_PROGRESS → IN_REVIEW` only after implementation and initial validation (the ticket's own Validation commands) are complete.
- `IN_REVIEW → DONE` only after every mandatory audit (repository-wide, architecture, raw-dictionary, ticket-reference, documentation, determinism, and all three scientific-drift audits) and every quality gate (Ruff, Pyright strict, Pylance parity, import-linter, pytest-archon, Sonar, full test suite) named in the ticket passes.
- Any active state (`READY`, `IN_PROGRESS`, `IN_REVIEW`) may become `BLOCKED`.
- `BLOCKED` requires a precise cause and unblock condition recorded in the "Blocker" column below and in the ticket file's own "Failure and blocker behavior" evidence.
- An eligible conditional or optional ticket may transition from `READY`, `IN_PROGRESS`, `IN_REVIEW`, or `BLOCKED` to `REJECTED` only with the ticket-defined feasibility/authority rejection evidence, the three completed audits, a terminal decision record, and synchronized ticket/register status.
- An eligible conditional or optional ticket may transition from `NOT_STARTED`, `READY`, `IN_PROGRESS`, `IN_REVIEW`, or `BLOCKED` to `NOT_APPLICABLE` only with the ticket-defined authority-grounded withdrawal or non-selection evidence, the three completed audits, a terminal decision record, and synchronized ticket/register status.
- `REJECTED` and `NOT_APPLICABLE` are valid terminal states only where the ticket explicitly permits them; they never substitute for incomplete implementation, missing evidence, or an unresolved blocker.
- The standalone ticket file's `Status` field and this table's `Status` column must always show the same status; a mismatch is a blocking defect that must be corrected before further work continues.
- Status must be updated at the time work starts, while it remains ongoing (current step), when it enters review, when it becomes blocked, and when it finishes — never reconstructed retroactively after the fact.

## Ticket table — Phase 0

All rows are initialized `NOT_STARTED`. Creating a standalone ticket Markdown file does not change this status: the document-conversion task performed to produce `docs/tickets/phase-0/` implements nothing.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0-T001 | Audit and record repository starting state | NOT_STARTED | — | — | — | — | — | — | — | — | NONE | — |
| P0-T002 | Establish the Python 3.12 project and build backend | NOT_STARTED | P0-T001 | — | — | — | — | — | — | — | NONE | — |
| P0-T003 | Define dependency groups and pin scientific libraries | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T004 | Establish dependency-lock discipline | NOT_STARTED | P0-T003 | — | — | — | — | — | — | — | NONE | — |
| P0-T005 | Create the approved layered source skeleton | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T006 | Establish repository root layout and tracked/generated/gitignored policy | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T007 | Configure Ruff lint and format | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T008 | Configure Pyright strict typing | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T009 | Configure pytest, coverage, timeout, and order-randomization | NOT_STARTED | P0-T002 | — | — | — | — | — | — | — | NONE | — |
| P0-T010 | Configure Hypothesis property-testing profiles | NOT_STARTED | P0-T009 | — | — | — | — | — | — | — | NONE | — |
| P0-T011 | Configure import-linter layer contracts | NOT_STARTED | P0-T005 | — | — | — | — | — | — | — | NONE | — |
| P0-T012 | Configure pytest-archon in-test boundary assertions | NOT_STARTED | P0-T005, P0-T009 | — | — | — | — | — | — | — | NONE | — |
| P0-T013 | Configure syrupy golden-snapshot support | NOT_STARTED | P0-T009 | — | — | — | — | — | — | — | NONE | — |
| P0-T014 | Establish Nox validation sessions | NOT_STARTED | P0-T007, P0-T008, P0-T009 | — | — | — | — | — | — | — | NONE | — |
| P0-T015 | Establish the serialized CUDA lane and CPU xdist policy | NOT_STARTED | P0-T014 | — | — | — | — | — | — | — | NONE | — |
| P0-T016 | Audit and consolidate the canonical provider-agnostic AI catalogue | NOT_STARTED | P0-T001 | — | — | — | — | — | — | — | NONE | — |
| P0-T017 | Complete the canonical agent-role catalogue | NOT_STARTED | P0-T016 | — | — | — | — | — | — | — | NONE | — |
| P0-T018 | Complete the canonical skill catalogue | NOT_STARTED | P0-T016 | — | — | — | — | — | — | — | NONE | — |
| P0-T019 | Establish the task-contract template set | NOT_STARTED | P0-T016 | — | — | — | — | — | — | — | NONE | — |
| P0-T020 | Establish the workflow catalogue | NOT_STARTED | P0-T016 | — | — | — | — | — | — | — | NONE | — |
| P0-T021 | Establish the command catalogue and provider thin adapters | NOT_STARTED | P0-T016 | — | — | — | — | — | — | — | NONE | — |
| P0-T022 | Implement pre-edit and post-edit blocking hooks | NOT_STARTED | P0-T018 | — | — | — | — | — | — | — | NONE | — |
| P0-T023 | Implement structure/naming/typing/comment blocking hooks | NOT_STARTED | P0-T007, P0-T008, P0-T011 | — | — | — | — | — | — | — | NONE | — |
| P0-T024 | Implement scope/threshold/statistics/lineage/config blocking hooks | NOT_STARTED | P0-T017 | — | — | — | — | — | — | — | NONE | — |
| P0-T025 | Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks | NOT_STARTED | P0-T014 | — | — | — | — | — | — | — | NONE | — |
| P0-T026 | Establish implementation-task governance and repository baseline quality gate | NOT_STARTED | P0-T001–P0-T025, P0-T027 | — | — | — | — | — | — | — | NONE | — |
| P0-T027 | Configure SonarQube/SonarCloud analysis and quality gate (added; see "Added ticket" above) | NOT_STARTED | P0-T007, P0-T008, P0-T009 | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 0 register

- Every dependency ID above is cross-checked against `docs/MASTER_TICKET_LOG.md` Section G (Master ticket index) for `P0-T001`–`P0-T026`; `P0-T027`'s dependencies were assigned during extraction per the justification above.
- `P0-T026`'s dependency list is extended beyond the master log (`P0-T001`–`P0-T025`) to also require `P0-T027`, so that the baseline quality gate cannot reach `DONE` without the Sonar gate. This is the one intentional dependency change made during extraction, and it is documented here and in `docs/tickets/phase-0/P0-T026.md` and `docs/tickets/phase-0/README.md`.
- No other ticket's dependencies, blocks, priority, type, scientific-execution classification, or campaign scope were altered from `docs/MASTER_TICKET_LOG.md`.

## Ticket table — Phase 1

All rows are initialized `NOT_STARTED`. Creating a standalone ticket Markdown file does not change this status: the document-conversion task performed to produce `docs/tickets/phase-1/` implements nothing. Retired IDs `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` are intentionally absent — they are not part of the master log's current Phase 1 ticket set and must never be reintroduced.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1-T001 | Implement dataset/regime/partition/split domain vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T002 | Implement model/training/checkpoint/score domain vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T003 | Implement threshold-policy/variant/comparator domain vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T004 | Implement metric-family enums and the MetricId union | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T005 | Implement statistical-method/claim-outcome/absorption vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T006 | Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T007 | Implement feasibility/rejection/reuse/blocking vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T008 | Implement storage/artifact/manifest vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T009 | Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T051 | Implement application telemetry vocabulary and contracts | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T052 | Implement analysis reporting vocabulary | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T053 | Implement test-support vocabulary and typed test profiles | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T011 | Implement finite-numeric and Decimal probability-like value objects | NOT_STARTED | P1-T001 | — | — | — | — | — | — | — | NONE | — |
| P1-T012 | Implement identity, seed-plan, and stage-fingerprint value objects | NOT_STARTED | P1-T009 | — | — | — | — | — | — | — | NONE | — |
| P1-T013 | Implement per-stage nominal identity dataclasses | NOT_STARTED | P1-T012 | — | — | — | — | — | — | — | NONE | — |
| P1-T014 | Implement resource, traffic-rate, and byte value objects | NOT_STARTED | P1-T011 | — | — | — | — | — | — | — | NONE | — |
| P1-T015 | Implement immutable typed collections and the object-dict prohibition | NOT_STARTED | P1-T011, P1-T012 | — | — | — | — | — | — | — | NONE | — |
| P1-T016 | Implement locked dispersion, quantile, and pooled-variance mathematics | NOT_STARTED | P1-T011 | — | — | — | — | — | — | — | NONE | — |
| P1-T017 | Implement Cliff's delta and effect-size pure functions | NOT_STARTED | P1-T011 | — | — | — | — | — | — | — | NONE | — |
| P1-T018 | Implement locked domain constants and the protocol eligibility rule | NOT_STARTED | P1-T011, P1-T016 | — | — | — | — | — | — | — | NONE | — |
| P1-T019 | Implement dataset, partition, and split specifications | NOT_STARTED | P1-T001, P1-T011 | — | — | — | — | — | — | — | NONE | — |
| P1-T020 | Implement preprocessing and processed-split specifications | NOT_STARTED | P1-T019 | — | — | — | — | — | — | — | NONE | — |
| P1-T021 | Implement model, federation, training, and batch specifications | NOT_STARTED | P1-T002 | — | — | — | — | — | — | — | NONE | — |
| P1-T022 | Implement checkpoint schedule, selection, and recovery specifications | NOT_STARTED | P1-T002 | — | — | — | — | — | — | — | NONE | — |
| P1-T023 | Implement scoring and split-scoped score-artifact specifications | NOT_STARTED | P1-T002, P1-T015 | — | — | — | — | — | — | — | NONE | — |
| P1-T024 | Implement the threshold-construction union and suite specifications | NOT_STARTED | P1-T003, P1-T023 | — | — | — | — | — | — | — | NONE | — |
| P1-T025 | Implement B4 clustering and federated-statistics specifications | NOT_STARTED | P1-T024 | — | — | — | — | — | — | — | NONE | — |
| P1-T026 | Implement evaluation, operating-point, and alert-burden result types | NOT_STARTED | P1-T004, P1-T014, P1-T016, P1-T018 | — | — | — | — | — | — | — | NONE | — |
| P1-T027 | Implement statistical, confirmatory, and anchor-gate result types | NOT_STARTED | P1-T005, P1-T017 | — | — | — | — | — | — | — | NONE | — |
| P1-T028 | Implement the scientific-protocol and policy aggregates | NOT_STARTED | P1-T019, P1-T020, P1-T021, P1-T022, P1-T023, P1-T024, P1-T026, P1-T027 | — | — | — | — | — | — | — | NONE | — |
| P1-T029 | Implement experiment identity/profile/cell aggregates and closed profiles | NOT_STARTED | P1-T006, P1-T007, P1-T028 | — | — | — | — | — | — | — | NONE | — |
| P1-T030 | Implement the DatpCoreError hierarchy and typed error families | NOT_STARTED | P0-T026 | — | — | — | — | — | — | — | NONE | — |
| P1-T031 | Implement Pydantic boundary schemas and discriminated unions | NOT_STARTED | P1-T029 | — | — | — | — | — | — | — | NONE | — |
| P1-T032 | Implement YAML loading, override composition, and schema-to-domain mapping | NOT_STARTED | P1-T031 | — | — | — | — | — | — | — | NONE | — |
| P1-T033 | Implement resolved-configuration recording and the typed spec-diff | NOT_STARTED | P1-T032 | — | — | — | — | — | — | — | NONE | — |
| P1-T034 | Implement data/learning/scoring/thresholding application ports | NOT_STARTED | P1-T028, P1-T030 | — | — | — | — | — | — | — | NONE | — |
| P1-T035 | Implement statistics/reporting/telemetry application ports | NOT_STARTED | P1-T027, P1-T051, P1-T030 | — | — | — | — | — | — | — | NONE | — |
| P1-T036 | Implement persistence/runtime application ports | NOT_STARTED | P1-T008, P1-T009, P1-T033 | — | — | — | — | — | — | — | NONE | — |
| P1-T037 | Implement reusable pipeline stage functions and concrete services | NOT_STARTED | P1-T034, P1-T035, P1-T036 | — | — | — | — | — | — | — | NONE | — |
| P1-T038 | Implement ExperimentPlanner and the ScoreReuseGate | NOT_STARTED | P1-T037, P1-T033 | — | — | — | — | — | — | — | NONE | — |
| P1-T039 | Implement preflight, executor, lifecycle, and resource-pressure orchestration | NOT_STARTED | P1-T038 | — | — | — | — | — | — | — | NONE | — |
| P1-T040 | Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing | NOT_STARTED | P1-T038, P1-T027 | — | — | — | — | — | — | — | NONE | — |
| P1-T054 | Implement semantic storage-root binding and path resolution | NOT_STARTED | P1-T036, P0-T006 | — | — | — | — | — | — | — | NONE | — |
| P1-T055 | Implement content hashing | NOT_STARTED | P1-T054 | — | — | — | — | — | — | — | NONE | — |
| P1-T056 | Implement serialization and schema-version handling | NOT_STARTED | P1-T054 | — | — | — | — | — | — | — | NONE | — |
| P1-T057 | Implement atomic single-artifact persistence | NOT_STARTED | P1-T054, P1-T055, P1-T056 | — | — | — | — | — | — | — | NONE | — |
| P1-T058 | Implement immutable multi-file bundle commit and manifest verification | NOT_STARTED | P1-T057 | — | — | — | — | — | — | — | NONE | — |
| P1-T059 | Implement lock providers, leases, and commit ownership | NOT_STARTED | P1-T057 | — | — | — | — | — | — | — | NONE | — |
| P1-T042 | Implement PyArrow streaming and bounded-pandas data adapters | NOT_STARTED | P1-T034, P1-T054, P1-T055, P1-T056, P1-T057 | — | — | — | — | — | — | — | NONE | — |
| P1-T043 | Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters | NOT_STARTED | P1-T034, P1-T054, P1-T055, P1-T056 | — | — | — | — | — | — | — | NONE | — |
| P1-T044 | Implement Flower FedAvg/FedProx and centralized trainers | NOT_STARTED | P1-T043 | — | — | — | — | — | — | — | NONE | — |
| P1-T045 | Implement scoring, threshold, clustering, quantile, and fed-stats adapters | NOT_STARTED | P1-T043 | — | — | — | — | — | — | — | NONE | — |
| P1-T046 | Implement the SciPy statistics adapter and per-family metric calculators | NOT_STARTED | P1-T035, P1-T056, P1-T057 | — | — | — | — | — | — | — | NONE | — |
| P1-T060 | Implement CUDA guard and deterministic device initialization | NOT_STARTED | P1-T035, P1-T036 | — | — | — | — | — | — | — | NONE | — |
| P1-T061 | Implement hardware inventory and GPU assignment | NOT_STARTED | P1-T035, P1-T036 | — | — | — | — | — | — | — | NONE | — |
| P1-T062 | Implement resource-pressure monitoring and cooperative throttling | NOT_STARTED | P1-T061 | — | — | — | — | — | — | — | NONE | — |
| P1-T063 | Implement the CheckpointStore adapter (scientific and recovery persistence) | NOT_STARTED | P1-T054, P1-T055, P1-T056, P1-T057, P1-T059 | — | — | — | — | — | — | — | NONE | — |
| P1-T064 | Implement run-state persistence and lifecycle storage | NOT_STARTED | P1-T054, P1-T056 | — | — | — | — | — | — | — | NONE | — |
| P1-T065 | Implement the structured telemetry adapter | NOT_STARTED | P1-T051, P1-T035 | — | — | — | — | — | — | — | NONE | — |
| P1-T066 | Implement the environment and provenance inventory adapter | NOT_STARTED | P1-T061 | — | — | — | — | — | — | — | NONE | — |
| P1-T067 | Implement report renderers | NOT_STARTED | P1-T052, P1-T040 | — | — | — | — | — | — | — | NONE | — |
| P1-T068 | Implement the composition root and strategy registries | NOT_STARTED | P1-T039, P1-T042, P1-T043, P1-T044, P1-T045, P1-T046, P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T060, P1-T061, P1-T062, P1-T063, P1-T064, P1-T065, P1-T066, P1-T067 | — | — | — | — | — | — | — | NONE | — |
| P1-T069 | Implement the CLI boundary and command invocation | NOT_STARTED | P1-T068 | — | — | — | — | — | — | — | NONE | — |
| P1-T049 | Implement the analysis table/figure/wording/report-model specification layer | NOT_STARTED | P1-T052, P1-T026, P1-T027 | — | — | — | — | — | — | — | NONE | — |
| P1-T050 | Implement the architecture-boundary and framework-confinement test suite | NOT_STARTED | P0-T011, P0-T012, P1-T068, P1-T069 | — | — | — | — | — | — | — | NONE | — |
| P1-T070 | Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test | NOT_STARTED | P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, P1-T051–P1-T069 (all 65 other Phase 1 tickets) | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 1 register

- Every dependency ID above is cross-checked against `docs/MASTER_TICKET_LOG.md` Section G (Master ticket index) for `P1-T001`–`P1-T070`. No dependency, blocks, priority, type, scientific-execution classification, or campaign scope was altered from `docs/MASTER_TICKET_LOG.md` during this extraction.
- No ticket was added or split during this extraction; the mega-ticket decomposition (retiring `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048`) was already final in the master log before this extraction began, per that document's own reconstruction-status note.
- `P1-T070` cannot become `READY` until every other Phase 1 row above is `DONE`; it is the Phase 1 phase-gate ticket, analogous to `P0-T026` for Phase 0.
- No Phase 1 ticket can become `READY` until `P0-T026` (Phase 0's own phase-gate ticket) is `DONE`, since every Phase 1 ticket with no other listed dependency still depends transitively on the Phase 0 baseline quality gate.

## Register metadata — Phase 3

- **Selected phase.** Phase 3 — DATP Anchor Campaign (`phase-3`; `P3-`).
- **Expected / extracted ticket count.** 11 / 11 (`P3-T001`–`P3-T011`); no added, split, moved, or retired ticket.
- **Phase gate.** `P3-T011` — anchor integrity and journal-unlock gate.
- **Current active ticket.** NONE — documentation conversion does not start implementation.
- **Next eligible ticket.** NONE — `P2-T020` is not `DONE`.
- **Unresolved blockers.** Implementation prerequisites remain `NOT_STARTED`; `P3-T008` is conditional and requires uninterrupted-completion evidence when `NOT_APPLICABLE`.
- **Dates and evidence.** No implementation timestamp, audit result, or scientific evidence is recorded by this documentation task.

## Ticket table — Phase 3

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P3-T001 | Final anchor implementation audit and clean-worktree check | NOT_STARTED | P2-T020. | — | — | — | — | — | — | — | NONE | — |
| P3-T002 | Freeze code-state, dependency-lock, and environment provenance | NOT_STARTED | P3-T001, P0-T004. | — | — | — | — | — | — | — | NONE | — |
| P3-T003 | Freeze the resolved anchor configuration and verify the authoritative seed plan | NOT_STARTED | P3-T001. | — | — | — | — | — | — | — | NONE | — |
| P3-T004 | Verify the anchor experiment matrix and enumerate stage identities and expected artifacts | NOT_STARTED | P3-T003. | — | — | — | — | — | — | — | NONE | — |
| P3-T005 | Resource/storage/CUDA/VRAM preflight and output-namespace compatibility | NOT_STARTED | P3-T004, P1-T039, P1-T060, P1-T061, P1-T062. | — | — | — | — | — | — | — | NONE | — |
| P3-T006 | Create the anchor campaign identity and execution-attempt identity | NOT_STARTED | P3-T002, P3-T005. | — | — | — | — | — | — | — | NONE | — |
| P3-T007 | Execute the coordinated anchor campaign | NOT_STARTED | P3-T006. | — | — | — | — | — | — | — | NONE | — |
| P3-T008 | Conditional anchor recovery, resume, and infrastructure-retry handling | NOT_STARTED | P3-T006. | — | — | — | — | — | — | — | NONE | — |
| P3-T009 | Completeness and same-model/same-score compatibility audits; typed failure persistence | NOT_STARTED | P3-T007; P3-T008 when activated. | — | — | — | — | — | — | — | NONE | — |
| P3-T010 | Historical-reference diagnostic and full configured anchor statistical analysis | NOT_STARTED | P3-T009. | — | — | — | — | — | — | — | NONE | — |
| P3-T011 | Anchor integrity decision, technical-invalidity correction path, artifact freeze, journal-unlock gate | NOT_STARTED | P3-T010. | — | — | — | — | — | — | — | NONE | — |

## Register metadata — Phase 4

- **Selected phase.** Phase 4 — Complete Journal-Extension Implementation (`phase-4`; `P4-`).
- **Expected / extracted ticket count.** 26 / 26 (`P4-T001`–`P4-T026`); no added, split, moved, or retired ticket.
- **Phase gate.** `P4-T026` — journal implementation-completeness audit.
- **Current active ticket.** NONE — documentation conversion does not start implementation.
- **Next eligible ticket.** NONE — `P3-T011` and prior prerequisites are not `DONE`.
- **Unresolved blockers.** `P4-T022` has a documented Section G/Section H dependency discrepancy; it must remain `BLOCKED` when reached until an authorized reconciliation chooses its dependency/block fields. Section G/Section H also differ on the `P4-T023 → P5-T002` and `P4-T024 → P7-T008` downstream edges. Phase 4 remains fail-closed through `P4-T026`.
- **Dates and evidence.** No implementation timestamp, audit result, journal output, or scientific evidence is recorded by this documentation task.

## Ticket table — Phase 4

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P4-T001 | Implement E-C1 confirmatory experiment specification and identity | NOT_STARTED | P3-T011, P1-T029. | — | — | — | — | — | — | — | NONE | — |
| P4-T002 | Implement E-S1 construction-sensitivity and E-S2 q-sensitivity | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T003 | Implement E-S3 Dirichlet severity (Regime C) | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T004 | Implement E-M1 cluster/family granularity and stability | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T005 | Implement E-M2 B4 cluster-feature ablation and contingency | NOT_STARTED | P4-T004. | — | — | — | — | — | — | — | NONE | — |
| P4-T006 | Implement E-M3 per-client CDF overlays and Ennio deep dive | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T007 | Implement E-M4 JS↔gain association and E-M5 threshold-shift scatter | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T008 | Implement E-V1 calibration-size sweep and size-aware fallback | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T009 | Implement E-V2 local-global shrinkage (τ-shrink) | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T010 | Implement E-V3 split-conformal B2-conf and conformal coverage | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T011 | Implement the B-a CICIoT2023 boundary | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T012 | Implement B-b/temporal CICIoT2023 rejection and suppression records | NOT_STARTED | P1-T007, P4-T011. | — | — | — | — | — | — | — | NONE | — |
| P4-T013 | Implement the Regime D Edge-IIoTset source/schema/feasibility audit | NOT_STARTED | P4-T001, P1-T040. | — | — | — | — | — | — | — | NONE | — |
| P4-T014 | Implement Regime D partitioning, preprocessing, training, and scoring | NOT_STARTED | P4-T013. | — | — | — | — | — | — | — | NONE | — |
| P4-T015 | Implement E-X1 external validation | NOT_STARTED | P4-T014, P4-T018. | — | — | — | — | — | — | — | NONE | — |
| P4-T016 | Implement E-T1 FedProx aggregation stress test | NOT_STARTED | P4-T001, P1-T044. | — | — | — | — | — | — | — | NONE | — |
| P4-T017 | Implement E-T2 model-personalization stress test and absorption bands | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T018 | Implement E-T3 B-FedStatsBenign matched comparator | NOT_STARTED | P4-T001, P1-T025. | — | — | — | — | — | — | — | NONE | — |
| P4-T019 | Implement E-B1 temporal recalibration MVE | NOT_STARTED | P4-T014, P4-T024. | — | — | — | — | — | — | — | NONE | — |
| P4-T020 | Implement mandatory E-O1 alert burden evidence and suppression route | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T021 | Implement claim tiers, fallback wording, and report schemas/renderers | NOT_STARTED | P4-T001, P1-T049. | — | — | — | — | — | — | — | NONE | — |
| P4-T022 | Implement journal expected-artifact/table/figure inventory and completeness audit | NOT_STARTED | P4-T002, P4-T003, P4-T004, P4-T005, P4-T006, P4-T007, P4-T008, P4-T009, P4-T010, P4-T011, P4-T012, P4-T013, P4-T014, P4-T015, P4-T016, P4-T017, P4-T018, P4-T019, P4-T020, P4-T021. | — | — | — | — | — | — | — | NONE | — |
| P4-T023 | Record optional E-Q1–E-Q6 selections and implement selected supplements | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T024 | Resolve chronological temporal training/calibration allocation | NOT_STARTED | P4-T001. | — | — | — | — | — | — | — | NONE | — |
| P4-T025 | Produce Appendix A B2 calibration-versus-held-out FPR analysis | NOT_STARTED | P4-T001,P4-T008,P4-T009,P4-T010. | — | — | — | — | — | — | — | NONE | — |
| P4-T026 | Complete journal implementation audit and phase gate | NOT_STARTED | P4-T022,P4-T023,P4-T024,P4-T025. | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 3 and Phase 4 registers

- Every ticket-file `Status` field and row above must match; a mismatch is blocking.
- `P3-T011` records integrity separately from scientific outcome. An integrity-valid weak, null, mixed, unfavorable, or opposite-direction anchor result is frozen evidence, not a retry condition; journal unlock also requires the authority-defined passed anchor reproduction result.
- Phase 4 validation is synthetic, dry-run, or read-only artifact inspection only. No row may receive journal campaign evidence until a future authorized phase.
- The `P4-T022` discrepancy is retained as an authority finding: Section G and Section H disagree on some dependencies/blocks. The standalone fields preserve Section H for traceability but do not resolve the conflict; P4-T022 must be `BLOCKED` when reached until authorized reconciliation. `P4-T026` directly requires `P4-T022`–`P4-T025`, preserving fail-closed phase-gate coverage.
## Register metadata — Phase 5

- **Selected phase.** Phase 5 — Journal Campaign Planning and Readiness (phase-5; P5-).
- **Expected / extracted ticket count.** 9 / 9 (P5-T001–P5-T009); no added, split, moved, retired, or renumbered ticket.
- **Phase gate.** P5-T009 — frozen journal manifest and formal go/no-go decision.
- **Current active ticket.** NONE — documentation conversion does not start planning or campaign work.
- **Next eligible ticket.** NONE — P4-T026 and its prerequisites are NOT_STARTED.
- **Unresolved blockers.** The documented Phase 4 Section G/H discrepancy remains fail-closed through P4-T026. P4-T024 is a direct P5-T004 input; unresolved temporal allocation produces a typed blocked/suppression outcome and cannot be inferred.
- **Dates and evidence.** No implementation timestamp, audit result, frozen campaign identity, manifest, or scientific evidence is recorded by this documentation task.

## Ticket table — Phase 5

All rows are initialized NOT_STARTED; creating the standalone specifications performs no planning or scientific execution.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P5-T001 | Implementation-completeness and anchor-artifact-compatibility audit | NOT_STARTED | P4-T026, P3-T011 | — | — | — | — | — | — | — | NONE | — |
| P5-T002 | Configuration expansion and journal experiment-cell enumeration | NOT_STARTED | P5-T001, P1-T038 | — | — | — | — | — | — | — | NONE | — |
| P5-T003 | Cell-ID uniqueness and stage-identity enumeration | NOT_STARTED | P5-T002 | — | — | — | — | — | — | — | NONE | — |
| P5-T004 | Feasibility-gate resolution, suppression cells, and unresolved-cell blocking | NOT_STARTED | P5-T003, P4-T013, P4-T024 | — | — | — | — | — | — | — | NONE | — |
| P5-T005 | Reuse and invalidation verification against frozen anchor artifacts | NOT_STARTED | P5-T003, P1-T033 | — | — | — | — | — | — | — | NONE | — |
| P5-T006 | Expected-artifact/table/figure/export inventory and experiment-to-claim/output mapping | NOT_STARTED | P5-T003 | — | — | — | — | — | — | — | NONE | — |
| P5-T007 | Resource/storage estimation and worker/CUDA/process/resume-boundary planning | NOT_STARTED | P5-T005, P5-T006 | — | — | — | — | — | — | — | NONE | — |
| P5-T008 | Clean-worktree check and freeze of code/dependency/environment/config/campaign identity | NOT_STARTED | P5-T004, P5-T007, P0-T004 | — | — | — | — | — | — | — | NONE | — |
| P5-T009 | Journal campaign manifest and final go/no-go decision | NOT_STARTED | P5-T008 | — | — | — | — | — | — | — | NONE | — |

## Register metadata — Phase 6

- **Selected phase.** Phase 6 — Journal Campaign (phase-6; P6-).
- **Expected / extracted ticket count.** 9 / 9 (P6-T001–P6-T009); no added, split, moved, retired, or renumbered ticket.
- **Phase gate.** P6-T009 — complete-cell/statistics/output audit, immutable result freeze, rendered outputs, and separate integrity/outcome decision.
- **Current active ticket.** NONE — documentation conversion does not create an attempt or execute a campaign.
- **Next eligible ticket.** NONE — P5-T009 is NOT_STARTED.
- **Unresolved blockers.** Regime D remains conditional on P5-T004 feasibility. P6-T007 is NOT_APPLICABLE only with uninterrupted-execution evidence; otherwise its recovery evidence is required before P6-T008.
- **Dates and evidence.** No execution-attempt ID, journal artifact, output, result freeze, audit result, or scientific evidence is recorded by this documentation task.

## Ticket table — Phase 6

All rows are initialized NOT_STARTED; documentation creation does not create a journal campaign or authorize scientific execution.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P6-T001 | Final readiness confirmation and journal execution-attempt creation | NOT_STARTED | P5-T009 | — | — | — | — | — | — | — | NONE | — |
| P6-T002 | Journal Regime-A identity completion, reuse validation, and threshold-only execution | NOT_STARTED | P6-T001 | — | — | — | — | — | — | — | NONE | — |
| P6-T003 | Regime C execution | NOT_STARTED | P6-T001 | — | — | — | — | — | — | — | NONE | — |
| P6-T004 | Accepted Regime D execution (external + temporal) | NOT_STARTED | P6-T001, P5-T004 | — | — | — | — | — | — | — | NONE | — |
| P6-T005 | FedProx and model-personalization stress-test execution | NOT_STARTED | P6-T001 | — | — | — | — | — | — | — | NONE | — |
| P6-T006 | Statistics execution, typed-failure and invalidated-artifact handling | NOT_STARTED | P6-T002, P6-T003, P6-T004, P6-T005 | — | — | — | — | — | — | — | NONE | — |
| P6-T007 | Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits | NOT_STARTED | P6-T001 | — | — | — | — | — | — | — | NONE | — |
| P6-T008 | Complete-cell/statistics/output audits and result freeze | NOT_STARTED | P6-T006; P6-T007 when activated | — | — | — | — | — | — | — | NONE | — |
| P6-T009 | Report rendering, journal integrity/outcome decision, technical-invalidity correction path | NOT_STARTED | P6-T008 | — | — | — | — | — | — | — | NONE | — |

## Register metadata — Phase 7

- **Selected phase.** Phase 7 — Final Result Freeze, Reporting, and Audit (phase-7; P7-).
- **Expected / extracted ticket count.** 12 / 12 (P7-T001–P7-T012); no added, split, moved, retired, or renumbered ticket.
- **Phase gate.** P7-T011 — terminal backlog-closure gate, requiring P7-T012 despite its later number and P4-T025 Appendix A evidence.
- **Current active ticket.** NONE — documentation conversion does not audit, mutate, regenerate, or close scientific evidence.
- **Next eligible ticket.** NONE — P6-T009 is NOT_STARTED.
- **Unresolved blockers.** Phase 4 records a Section G/H conflict in which P4-T024 blocks P7-T008 only in one authority location. Canonical P7-T008 metadata remains unchanged, but the temporal claim audit is fail-closed pending authorized reconciliation or an evidence-defined P4-T024 terminal outcome.
- **Dates and evidence.** No post-campaign audit result, regeneration evidence, originality verdict, or closure verdict is recorded by this documentation task.

## Ticket table — Phase 7

All rows are initialized NOT_STARTED; documentation creation performs no post-campaign work and cannot close the backlog.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P7-T001 | Immutable-result and artifact-hash verification; manifest completeness | NOT_STARTED | P6-T009 | — | — | — | — | — | — | — | NONE | — |
| P7-T002 | Lineage closure and provenance verification | NOT_STARTED | P7-T001 | — | — | — | — | — | — | — | NONE | — |
| P7-T003 | Seed-plan completeness and paired-seed validation | NOT_STARTED | P7-T001 | — | — | — | — | — | — | — | NONE | — |
| P7-T004 | Same-model/same-score causal-ladder audit | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | NONE | — |
| P7-T005 | Benign-only-calibration, attack-exclusion, and checkpoint-selection audit | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | NONE | — |
| P7-T006 | Metric-orientation, CV(FPR), absolute-dispersion, and AUROC-control audit | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | NONE | — |
| P7-T007 | BCa implementation, CI-direction, secondary-statistics, and degeneracy audit | NOT_STARTED | P7-T003 | — | — | — | — | — | — | — | NONE | — |
| P7-T008 | Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | P4-T024 authority conflict | — |
| P7-T009 | Table/figure/export provenance and frozen-output regeneration | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | NONE | — |
| P7-T010 | Repository cleanup, stale-output detection, and anchor/journal namespace protection | NOT_STARTED | P7-T001 | — | — | — | — | — | — | — | NONE | — |
| P7-T012 | Audit conference-to-journal originality and manuscript handoff evidence | NOT_STARTED | P7-T002, P7-T009 | — | — | — | — | — | — | — | NONE | — |
| P7-T011 | Reviewer red-team, architecture, and roadmap final audits; master-log closure | NOT_STARTED | P7-T004, P7-T005, P7-T006, P7-T007, P7-T008, P7-T009, P7-T010, P7-T012, P4-T025 | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 5 through Phase 7 registers

- Ticket-file and register statuses must always agree; mismatch is blocking.
- No row may advance because documentation exists. Every ticket requires its Part A evidence, Part B audits, valid dependencies, cleanup, and the global terminal-state rule.
- The P4-T022 discrepancy and the Section-H-only P4-T023 → P5-T002 / P4-T024 → P7-T008 edges remain authority findings. This register records the resulting fail-closed conditions but does not alter canonical detailed-ticket dependencies.
