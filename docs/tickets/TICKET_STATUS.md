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

## Status values

`NOT_STARTED` · `READY` · `IN_PROGRESS` · `BLOCKED` · `IN_REVIEW` · `DONE` · `REJECTED` · `NOT_APPLICABLE`

## Transition rules

- `NOT_STARTED → READY` only when every dependency listed in the ticket's `Dependencies` field is `DONE` in this table.
- `READY → IN_PROGRESS` immediately before implementation begins.
- `IN_PROGRESS → IN_REVIEW` only after implementation and initial validation (the ticket's own Validation commands) are complete.
- `IN_REVIEW → DONE` only after every mandatory audit (repository-wide, architecture, raw-dictionary, ticket-reference, documentation, determinism, and all three scientific-drift audits) and every quality gate (Ruff, Pyright strict, Pylance parity, import-linter, pytest-archon, Sonar, full test suite) named in the ticket passes.
- Any active state (`READY`, `IN_PROGRESS`, `IN_REVIEW`) may become `BLOCKED`.
- `BLOCKED` requires a precise cause and unblock condition recorded in the "Blocker" column below and in the ticket file's own "Failure and blocker behavior" evidence.
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
