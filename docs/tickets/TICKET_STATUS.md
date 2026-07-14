# Ticket Status Register

**Status.** ACTIVE — single operational status register for every ticket extracted from `docs/MASTER_TICKET_LOG.md` into `docs/tickets/`.

This file and each standalone ticket file's own `Status` field must always agree. A mismatch between this file and a ticket file is a blocking defect and must be resolved before either is treated as authoritative.

## Register metadata

- **Selected phase.** Phase 0 — Repository and Engineering Foundation.
- **Canonical phase code.** `phase-0` (directory `docs/tickets/phase-0/`; ticket ID prefix `P0-`).
- **Expected ticket count (per `docs/MASTER_TICKET_LOG.md`).** 26 (`P0-T001`–`P0-T026`).
- **Extracted ticket count (this register).** 27 (`P0-T001`–`P0-T026` preserved verbatim by ID, plus one added ticket `P0-T027`; see "Added ticket" below).
- **Added ticket.** `P0-T027` — Configure SonarQube/SonarCloud analysis and quality gate. Added because the ticket-conversion task instructions (Section 16 of the conversion task) mandate a Sonar quality gate in every ticket's validation requirements, no existing Phase 0 ticket can absorb project-wide Sonar configuration without overloading a single-tool-configuration responsibility (the existing pattern is one ticket per tool: `P0-T007` Ruff, `P0-T008` Pyright, `P0-T009` pytest, `P0-T010` Hypothesis, `P0-T011` import-linter, `P0-T012` pytest-archon, `P0-T013` syrupy), and `P0-T014` (Nox session wiring) explicitly forbids "business logic in sessions," which Sonar project configuration would violate if folded in. `P0-T027` is a genuinely new tool-configuration ticket, not a renumbering of an existing one; no existing ID was reused or altered. `docs/MASTER_TICKET_LOG.md` itself is unchanged by this addition — the addition exists only in `docs/tickets/`.
- **Phase-gate ticket.** `P0-T026` — Establish implementation-task governance and repository baseline quality gate. Its dependency list has been extended in the standalone ticket file to include `P0-T027` in addition to the 25 dependencies already present in the master log (`P0-T001`–`P0-T025`), so the gate cannot pass without the Sonar ticket.
- **Current active ticket.** NONE — no ticket has been started; this is a document-conversion task only.
- **Next eligible ticket.** `P0-T001` (the only Phase 0 ticket with no dependencies).
- **Unresolved blockers.** NONE — Phase 0 raises no scientific or architectural blocker per `docs/MASTER_TICKET_LOG.md` Section F ("Authority blockers. None. Phase 0 is pure tooling/governance scaffolding and raises no scientific blocker.").
- **Last updated.** 2026-07-14T00:00:00Z (ticket-extraction task; no implementation performed).
- **Roadmap last-read timestamp.** 2026-07-14 (`docs/Journal_Extension_Master_Roadmap.md`, Section A cross-check read during extraction).
- **Architecture last-read timestamp.** 2026-07-14 (`docs/DATP Core Architecture.md`, Sections 1–5, 21, 24, 29 read directly during extraction; full table of contents verified against every cited section number).
- **Master-log last-read timestamp.** 2026-07-14 (`docs/MASTER_TICKET_LOG.md`, Sections A–H, Phase 0 in full).

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

## Notes on this register

- Every dependency ID above is cross-checked against `docs/MASTER_TICKET_LOG.md` Section G (Master ticket index) for `P0-T001`–`P0-T026`; `P0-T027`'s dependencies were assigned during extraction per the justification above.
- `P0-T026`'s dependency list is extended beyond the master log (`P0-T001`–`P0-T025`) to also require `P0-T027`, so that the baseline quality gate cannot reach `DONE` without the Sonar gate. This is the one intentional dependency change made during extraction, and it is documented here and in `docs/tickets/phase-0/P0-T026.md` and `docs/tickets/phase-0/README.md`.
- No other ticket's dependencies, blocks, priority, type, scientific-execution classification, or campaign scope were altered from `docs/MASTER_TICKET_LOG.md`.
