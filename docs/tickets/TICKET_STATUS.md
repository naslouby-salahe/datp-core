# Ticket Status Register

**Status.** ACTIVE — single operational status register for every ticket extracted from `docs/MASTER_TICKET_LOG.md` into `docs/tickets/`.

This file and each standalone ticket file's own `Status` field must always agree. A mismatch between this file and a ticket file is a blocking defect and must be resolved before either is treated as authoritative.

## Register metadata — Phase 0

- **Selected phase.** Phase 0 — Repository and Engineering Foundation.
- **Canonical phase code.** `phase-0` (directory `docs/tickets/phase-0/`; ticket ID prefix `P0-`).
- **Expected ticket count (per `docs/MASTER_TICKET_LOG.md`).** 26 (`P0-T001`–`P0-T026`).
- **Extracted ticket count (this register).** 28 (`P0-T001`–`P0-T026` preserved verbatim by ID, plus two added tickets `P0-T027` and `P0-T028`; see "Added ticket" below).
- **Added ticket.** `P0-T027` — Configure SonarQube/SonarCloud analysis and quality gate. Added because the ticket-conversion task instructions (Section 16 of the conversion task) mandate a Sonar quality gate in every ticket's validation requirements, no existing Phase 0 ticket can absorb project-wide Sonar configuration without overloading a single-tool-configuration responsibility (the existing pattern is one ticket per tool: `P0-T007` Ruff, `P0-T008` Pyright, `P0-T009` pytest, `P0-T010` Hypothesis, `P0-T011` import-linter, `P0-T012` pytest-archon, `P0-T013` syrupy), and `P0-T014` (Nox session wiring) explicitly forbids "business logic in sessions," which Sonar project configuration would violate if folded in. `P0-T027` is a genuinely new tool-configuration ticket, not a renumbering of an existing one; no existing ID was reused or altered. `docs/MASTER_TICKET_LOG.md` itself is unchanged by this addition — the addition exists only in `docs/tickets/`.
- **Added ticket.** `P0-T028` — Configure CodeScene analysis and quality gate. Added under the identical one-tool-per-ticket precedent established by `P0-T027`: CodeScene is a second, independent code-health/hotspot analysis tool with its own project configuration (`.codescene/code-health-rules.json`) and its own Nox session, and folding it into an existing ticket would overload that ticket's single-tool-configuration responsibility in the same way folding Sonar into `P0-T014` would have. `P0-T028` is a genuinely new tool-configuration ticket, independent of and a peer to `P0-T027` (same dependency base: `P0-T007`, `P0-T008`, `P0-T009`; no dependency on `P0-T027` itself). `docs/MASTER_TICKET_LOG.md` itself is unchanged by this addition — the addition exists only in `docs/tickets/`.
- **Phase-gate ticket.** `P0-T026` — Establish implementation-task governance and repository baseline quality gate. Its dependency list has been extended in the standalone ticket file to include `P0-T027` and `P0-T028` in addition to the 25 dependencies already present in the master log (`P0-T001`–`P0-T025`), so the gate cannot pass without either the Sonar ticket or the CodeScene ticket.
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
- **Current active ticket.** NONE — all 66 Phase 1 tickets are `DONE`; Phase 1 is complete.
- **Next eligible ticket.** NONE within Phase 1 — `P1-T070` finished at 2026-07-15T17:15:45Z with PASS/PASS/PASS audits, unblocking `P2-T001`.
- **Unresolved blockers.** NONE — Architecture §§7.3, 16.7, 17.1, and 27.1 resolve the former precision, identity/seed, training, and checkpoint decisions.
- **Last updated.** 2026-07-15T17:15:45Z (P1-T070 completion; this metadata block was stale from the 2026-07-14 conversion pass and is corrected here to match the Phase 1 ticket table, which already recorded P1-T070 as DONE).
- **Roadmap last-read timestamp.** 2026-07-14 (`docs/Journal_Extension_Master_Roadmap.md`, read in full during extraction).
- **Architecture last-read timestamp.** 2026-07-14 (`docs/DATP Core Architecture.md`, Sections 1–8 read in full during extraction; Sections 9, 12, 15–22, 25, 27, 29 read section-by-section as cited by individual Phase 1 tickets during their reconstruction).
- **Master-log last-read timestamp.** 2026-07-14 (`docs/MASTER_TICKET_LOG.md`, Sections A–H, Phase 1 in full — all 66 ticket bodies read completely).



## Register metadata — Phase 2

- **Selected phase.** Phase 2 — Complete DATP Anchor Implementation.
- **Canonical phase code.** `phase-2` (directory `docs/tickets/phase-2/`; ticket prefix `P2-`).
- **Expected ticket count.** 23 (`P2-T001`–`P2-T023`) per `docs/MASTER_TICKET_LOG.md`.
- **Extracted ticket count.** 23; all IDs preserved with no addition, split, renumbering, or retirement.
- **Phase gate.** `P2-T020`; direct dependencies: `P2-T019`, `P2-T002`, and `P1-T040`; all Phase 2 routes are transitively covered.
- **Current active ticket.** NONE — `P2-T009` is complete.
- **Next eligible ticket.** `P2-T010` — `P2-T009` and its other direct dependencies are `DONE`.
- **Unresolved blockers.** Recovered anchor semantics, including the historical checkpoint protocol, must be resolved or carried to readiness; never guessed or resolved by real execution.
- **Authority finding.** The master log conflicts about the reconstruction status of `P2-T021`–`P2-T023`. Its Phase 2 index and detailed bodies also differ for `P2-T003` (scientific-execution classification and roadmap ID), `P2-T008` (dependency), `P2-T011` (block), `P2-T012` (type), and `P2-T023` (dependency/block), with further roadmap-ID drift. The standalone files preserve the detailed ticket bodies; the authority is unchanged.
- **Last updated.** 2026-07-15T22:59:10Z (`P2-T009` implementation, validation, audits, and cleanup complete; no scientific execution performed).
- **Roadmap last-read timestamp.** 2026-07-14 (complete authority read).
- **Architecture last-read timestamp.** 2026-07-14 (complete authority read).
- **Master-log last-read timestamp.** 2026-07-14 (complete authority read; Phase 2 bodies re-read).

## Ticket table — Phase 2

Rows record independently verified implementation status; no row authorizes scientific execution.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2-T001 | Recover DATP behavioral semantics from the reference repository (read-only) | DONE | P1-T070. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete (corrected) | PASS | PASS | PASS | ANCHOR_LOCAL_EPOCH_PROTOCOL_UNRESOLVED (print-grade, carried to P2-T020; does not block ticket completion — recorded per acceptance criteria) | Completion record in `P2-T001.md`; 12/13 semantics resolved, 1/13 (E) an explicit evidenced blocker; `AnchorHistoricalCheckpointProtocol` accepted provisionally; register in `docs/MASTER_TICKET_LOG.md` §N (corrected) |
| P2-T002 | Record the recovered-semantics register in the master log | DONE | P2-T001. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete (corrected) | PASS | PASS | PASS | ANCHOR_LOCAL_EPOCH_PROTOCOL_UNRESOLVED (print-grade, carried to P2-T020; does not block ticket completion — recorded per acceptance criteria) | Completion record in `P2-T002.md`; register in `docs/MASTER_TICKET_LOG.md` §N (N.1 corrected table, N.2 AnchorHistoricalCheckpointProtocol, N.2b new AnchorLocalEpochProtocol blocker, N.3 authority-conflict findings, N.4 one print-grade blocker) |
| P2-T003 | Inspect the N-BaIoT source and feature schema | DONE | P2-T001, P1-T032. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | NONE | Completion record in `P2-T003.md`; real inspection of `data/raw/N-BaIoT` (9 devices, 89 files, 7,062,606 rows, 115 features, no timestamp); manifests persisted under `data/manifests/`; 7 integration tests pass; full suite 557/557 both orders |
| P2-T004 | Implement the N-BaIoT source adapter and deterministic source-row identity | DONE | P2-T003, P1-T042. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | NONE | Completion record in `P2-T004.md`; fixed a real batch-size-dependence defect in shared `update_row_order_checksum`; real-data checksum identity proven on Ennio_Doorbell across 64KiB vs 16MiB blocks; full suite 562/562 both orders |
| P2-T005 | Implement physical-device (9-client) partitioning | DONE | P2-T004, P1-T019. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | NONE | Completion record in `P2-T005.md`; real 9-device run on N-BaIoT confirms 7,062,606 rows conserved (matches P2-T003 independently); checkpoint-1 full gate (13 Nox sessions incl. Sonar/CodeScene) all green; fixed a real CodeScene complexity finding |
| P2-T006 | Implement benign train/calibration and held-out benign/malicious test splits | DONE | P2-T005. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | NONE | Completion record in `P2-T006.md`; real-data split arithmetic verified exact against P2-T003's numbers; fixed real Sonar/CodeScene dashboard findings across P2-T003-T006 |
| P2-T007 | Implement preprocessing fit authorization and streaming transform | DONE | P2-T006, P1-T020. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | NONE | Completion record in `P2-T007.md`; TRAIN-only two-pass fit + streaming transform, chunk/reference equivalence proven via deterministic re-fit; `cs check` 10.00 |
| P2-T008 | Implement the fixed autoencoder, optimizer, and scheduler | DONE | P2-T007, P1-T043, P2-T001. | 2026-07-15 | 2026-07-15 | 2026-07-15 | Complete | PASS | PASS | PASS | ANCHOR_LOCAL_EPOCH_PROTOCOL_UNRESOLVED (print-grade, carried to P2-T020; does not block ticket completion) | Completion record in `P2-T008.md`; recovered AE/optimizer/scheduler already matched P1-T043's fixed architecture and TrainingSpec exactly; added locked `anchor_training_spec`/`build_anchor_optimizer`; `cs check` 10.00; real CUDA smoke test passed |
| P2-T009 | Implement FedAvg training (E=1, full participation, deterministic CUDA) | DONE | P2-T008, P1-T044. | 2026-07-15T22:52:12Z | 2026-07-15T22:59:10Z | 2026-07-15T22:59:10Z | Complete | PASS | PASS | PASS | ANCHOR_LOCAL_EPOCH_PROTOCOL_UNRESOLVED (print-grade, carried to P2-T020; does not change locked E=1 implementation) | Completion record in `P2-T009.md`; deterministic typed anchor executor, CPU/CUDA resume equivalence, full-participation lifecycle checks, Nox/Sonar/CodeScene and three audits passed; synthetic-only |
| P2-T010 | Implement the checkpoint schedule, persistence, and Regime-A global selection | IN_REVIEW | P2-T009, P2-T002, P1-T022. | 2026-07-16T15:35:00Z | 2026-07-16T16:10:00Z | — | — | PASS | PASS | BLOCKED | NONE | Checkpoint-2 (P2-T006..T010) full local gates + Sonar API both PASS for pushed 39098d3; CodeScene remote analysis for 39098d3 BLOCKED on external daily rate-limit (24/day), not a code finding — checkpoint held at IN_REVIEW until CodeScene confirms |
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
| P0-T001 | Audit and record repository starting state | DONE | — | 2026-07-14T14:57:06Z | 2026-07-14T14:57:06Z | 2026-07-14T14:57:06Z | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T001.md` |
| P0-T002 | Establish the Python 3.12 project and build backend | DONE | P0-T001 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T002.md` |
| P0-T003 | Define dependency groups and pin scientific libraries | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T003.md`; sqlalchemy/alembic transitive-via-flwr disposition recorded |
| P0-T004 | Establish dependency-lock discipline | DONE | P0-T003 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T004.md`; from-scratch resolve drift finding recorded |
| P0-T005 | Create the approved layered source skeleton | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T005.md`; 163 files, 162 submodules import clean |
| P0-T006 | Establish repository root layout and tracked/generated/gitignored policy | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T006.md`; untracked pre-committed `data/raw` symlink, fixed gitignore/comment defects |
| P0-T007 | Configure Ruff lint and format | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T007.md`; ruff check/format clean repo-wide |
| P0-T008 | Configure Pyright strict typing | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T008.md`; strict mode live-verified against 5 real violations |
| P0-T009 | Configure pytest, coverage, timeout, and order-randomization | DONE | P0-T002 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T009.md`; 9 markers registered, randomization live-verified |
| P0-T010 | Configure Hypothesis property-testing profiles | DONE | P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T010.md`; profiles live-verified deterministic; fixed cross-ticket Pyright venv gap |
| P0-T011 | Configure import-linter layer contracts | DONE | P0-T005 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T011.md`; 7 contracts, 2 live adversarial violations caught |
| P0-T012 | Configure pytest-archon in-test boundary assertions | DONE | P0-T005, P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T012.md`; assertion live-proven to fail then pass |
| P0-T013 | Configure syrupy golden-snapshot support | DONE | P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T013.md`; round-trip and mismatch both live-verified |
| P0-T014 | Establish Nox validation sessions | DONE | P0-T007, P0-T008, P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T014.md`; fixed critical PATH tool-resolution defect, all 12 sessions verified |
| P0-T015 | Establish the serialized CUDA lane and CPU xdist policy | DONE | P0-T014 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T015.md`; real-GPU-verified, 3 real defects found and fixed |
| P0-T016 | Audit and consolidate the canonical provider-agnostic AI catalogue | DONE | P0-T001 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T016.md`; no duplication found across all 4 adapters |
| P0-T017 | Complete the canonical agent-role catalogue | DONE | P0-T016 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T017.md`; 7 roles added, 19/19 required roles covered |
| P0-T018 | Complete the canonical skill catalogue | DONE | P0-T016 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T018.md`; 15 skills added, 24/24 required checks covered |
| P0-T019 | Establish the task-contract template set | DONE | P0-T016 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T019.md`; closed generic-template bypass loophole |
| P0-T020 | Establish the workflow catalogue | DONE | P0-T016 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T020.md`; fixed 3 missing gate-order gaps (post-edit/no-BC) |
| P0-T021 | Establish the command catalogue and provider thin adapters | DONE | P0-T016 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T021.md`; added 4 missing hook commands |
| P0-T022 | Implement pre-edit and post-edit blocking hooks | DONE | P0-T018 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T022.md`; fixed critical diff-only wording defect in post_edit_hook |
| P0-T023 | Implement structure/naming/typing/comment blocking hooks | DONE | P0-T007, P0-T008, P0-T011 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T023.md`; all 4 hooks bound to concrete architecture rules |
| P0-T024 | Implement scope/threshold/statistics/lineage/config blocking hooks | DONE | P0-T017 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T024.md`; 4 new hooks created, statistics_hook strengthened |
| P0-T025 | Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks | DONE | P0-T014 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE | Completion record in `P0-T025.md`; order-independence live-verified, 3 real gaps fixed |
| P0-T026 | Establish implementation-task governance and repository baseline quality gate | DONE | P0-T001–P0-T025, P0-T027, P0-T028 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE (reopened to compose the CodeScene gate, reverified green, returned to DONE) | Completion record in `P0-T026.md`; CodeScene addendum recorded; CHANGELOG.md added |
| P0-T027 | Configure SonarQube/SonarCloud analysis and quality gate (added; see "Added ticket" above) | DONE | P0-T007, P0-T008, P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE (auth resolved; live analysis passed, 304 files, 0 issues) | Completion record in `P0-T027.md` |
| P0-T028 | Configure CodeScene analysis and quality gate (added; see "Added ticket" above) | DONE | P0-T007, P0-T008, P0-T009 | 2026-07-14 | 2026-07-14 | 2026-07-14 | Complete | PASS | PASS | PASS | NONE (auth resolved; live delta analysis passed after a genuine duplication finding was fixed) | Completion record in `P0-T028.md` |

## Notes on the Phase 0 register

- Every dependency ID above is cross-checked against `docs/MASTER_TICKET_LOG.md` Section G (Master ticket index) for `P0-T001`–`P0-T026`; `P0-T027`'s and `P0-T028`'s dependencies were assigned during extraction per the justification above.
- `P0-T026`'s dependency list is extended beyond the master log (`P0-T001`–`P0-T025`) to also require `P0-T027` and `P0-T028`, so that the baseline quality gate cannot reach `DONE` without both the Sonar gate and the CodeScene gate. This is the intentional dependency change made during extraction (later widened to include `P0-T028`), and it is documented here and in `docs/tickets/phase-0/P0-T026.md` and `docs/tickets/phase-0/README.md`.
- No other ticket's dependencies, blocks, priority, type, scientific-execution classification, or campaign scope were altered from `docs/MASTER_TICKET_LOG.md`.

## Ticket table — Phase 1

All rows are initialized `NOT_STARTED`. Creating a standalone ticket Markdown file does not change this status: the document-conversion task performed to produce `docs/tickets/phase-1/` implements nothing. Retired IDs `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` are intentionally absent — they are not part of the master log's current Phase 1 ticket set and must never be reintroduced.

| Ticket ID | Title | Status | Dependencies | Started | Last Updated | Finished | Current Step | Audit 1 | Audit 2 | Audit 3 | Blocker | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1-T001 | Implement dataset/regime/partition/split domain vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Six vocabulary enums and exhaustive tests; focused checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T002 | Implement model/training/checkpoint/score domain vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Learning enums and focused tests; direct checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T003 | Implement threshold-policy/variant/comparator domain vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Threshold enums and focused tests; direct checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T004 | Implement metric-family enums and the MetricId union | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Eight metric-family enums, MetricId union, and exhaustive immutable metadata; focused checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T005 | Implement statistical-method/claim-outcome/absorption vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Closed statistical, claim, and absorption vocabularies; focused checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T006 | Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T19:34:59Z | 2026-07-14T19:34:59Z | Complete | PASS | PASS | PASS | NONE | Closed vocabularies and typed invariant; randomized full pytest and all Nox sessions, Sonar, and CodeScene passed |
| P1-T007 | Implement feasibility/rejection/reuse/blocking vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Added adversarial alert-burden suite-construction failure-path test; full Nox, Sonar, and CodeScene passed |
| P1-T008 | Implement storage/artifact/manifest vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-15T05:35:00Z | 2026-07-15T05:35:00Z | Complete | PASS | PASS | PASS | NONE | Vocabulary and exhaustive tests passed; P1-T054's physical anchor/journal separation proof closed the final adversarial audit; whole-project Nox, Sonar, and CodeScene passed |
| P1-T009 | Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | 2026-07-14T18:44:43Z | Complete | PASS | PASS | PASS | NONE | Closed runtime/lifecycle/seed/stage vocabularies; focused checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T051 | Implement application telemetry vocabulary and contracts | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T23:31:00Z | 2026-07-14T23:31:00Z | Complete | PASS | PASS | PASS | NONE | Canonical typed event envelope, exhaustive detail binding, focused checks, configured import-linter, architecture lane, and two randomized whole-project pytest runs passed; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T052 | Implement reporting-policy vocabulary | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-15T00:20:00Z | 2026-07-14T18:44:43Z | Complete; architecture repair applied | PASS | PASS | PASS | NONE | Reporting-policy vocabulary moved to the domain-owned `ReportingPolicy` module to remove the detected domain-to-analysis import; focused checks, randomized full pytest, all Nox sessions, Sonar, and CodeScene passed |
| P1-T053 | Implement test-support vocabulary and typed test profiles | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T23:35:00Z | 2026-07-14T23:35:00Z | Complete | PASS | PASS | PASS | NONE | Typed test profiles, exhaustive production-isolation AST check, configured import-linter, and two randomized whole-project pytest runs passed; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T011 | Implement finite-numeric and Decimal probability-like value objects | DONE | P1-T001 | 2026-07-14T18:44:43Z | 2026-07-14T19:51:07Z | 2026-07-14T20:04:39Z | Complete | PASS | PASS | PASS | NONE | Decimal/finiteness contracts, focused unit/property tests, randomized full pytest, post-review complete Nox, Sonar, and CodeScene passed |
| P1-T012 | Implement identity, seed-plan, and stage-fingerprint value objects | DONE | P1-T009 | 2026-07-14T20:04:39Z | 2026-07-15T12:41:48Z | 2026-07-14T20:10:25Z | Complete | PASS | PASS | PASS | NONE | Canonical identity/seed contracts, focused tests, randomized full pytest, post-review full Nox, Sonar, and CodeScene passed; 2026-07-15 audit remediation added the architecture-required typed DataLoaderSeedPlan/SeedPlan |
| P1-T013 | Implement per-stage nominal identity dataclasses | DONE | P1-T012 | 2026-07-14T20:10:25Z | 2026-07-14T20:10:25Z | 2026-07-14T20:14:24Z | Complete | PASS | PASS | PASS | NONE | Nominal stage identities, focused tests, post-review full Nox, Sonar, and CodeScene passed |
| P1-T014 | Implement resource, traffic-rate, and byte value objects | DONE | P1-T011 | 2026-07-14T20:14:24Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused gates, and audits passed |
| P1-T015 | Implement immutable typed collections and the object-dict prohibition | DONE | P1-T011, P1-T012 | 2026-07-14T20:23:50Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused gates, and audits passed |
| P1-T016 | Implement locked dispersion, quantile, and pooled-variance mathematics | DONE | P1-T011 | 2026-07-14T20:31:44Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused gates, and audits passed |
| P1-T017 | Implement Cliff's delta and effect-size pure functions | DONE | P1-T011 | 2026-07-14T20:38:00Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused gates, and audits passed |
| P1-T018 | Implement locked domain constants and the protocol eligibility rule | DONE | P1-T011, P1-T016 | 2026-07-14T20:41:33Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused gates, and audits passed |
| P1-T019 | Implement dataset, partition, and split specifications | DONE | P1-T001, P1-T011 | 2026-07-14T20:44:19Z | 2026-07-14T20:55:00Z | 2026-07-14T20:55:00Z | Complete | PASS | PASS | PASS | NONE | Full Nox, Sonar, CodeScene, focused unit/property/type/architecture gates, and scientific-drift audits passed |
| P1-T020 | Implement preprocessing and processed-split specifications | DONE | P1-T019 | 2026-07-14T21:00:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | TRAIN-only fit authorization and whole-project P1-T020–P1-T029 quality gate passed |
| P1-T021 | Implement model, federation, training, and batch specifications | DONE | P1-T002 | 2026-07-14T21:10:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Frozen FedProx/batch/personalization contracts and whole-project quality gate passed |
| P1-T022 | Implement checkpoint schedule, selection, and recovery specifications | DONE | P1-T002 | 2026-07-14T21:34:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Locked schedule, closed Regime-A evidence, and whole-project quality gate passed |
| P1-T023 | Implement scoring and split-scoped score-artifact specifications | DONE | P1-T002, P1-T015 | 2026-07-14T21:50:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Typed role lineage, atomic test pair, and whole-project quality gate passed; port conformance remains P1-T034-owned work |
| P1-T024 | Implement the threshold-construction union and suite specifications | DONE | P1-T003, P1-T023 | 2026-07-14T22:10:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Nine tagged variants, B0 exclusion, B1 mean, and whole-project quality gate passed |
| P1-T025 | Implement B4 clustering and federated-statistics specifications | DONE | P1-T024 | 2026-07-14T22:34:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Locked B4 fields, FedStats tie rule, and whole-project quality gate passed |
| P1-T026 | Implement evaluation, operating-point, and alert-burden result types | DONE | P1-T004, P1-T014, P1-T016, P1-T018 | 2026-07-14T23:00:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Paired eligibility, evidence-gated alert burden, and whole-project quality gate passed |
| P1-T027 | Implement statistical, confirmatory, and anchor-gate result types | DONE | P1-T005, P1-T017 | 2026-07-14T23:25:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Locked B1−B2, typed BCa degeneracy, anchor gate, and whole-project quality gate passed |
| P1-T028 | Implement the scientific-protocol and policy aggregates | DONE | P1-T019, P1-T020, P1-T021, P1-T022, P1-T023, P1-T024, P1-T026, P1-T027 | 2026-07-14T23:45:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Exact scientific/policy separation and whole-project quality gate passed |
| P1-T029 | Implement experiment identity/profile/cell aggregates and closed profiles | DONE | P1-T006, P1-T007, P1-T028 | 2026-07-15T00:05:00Z | 2026-07-15T00:45:00Z | 2026-07-15T00:45:00Z | Complete | PASS | PASS | PASS | NONE | Closed catalogue and authorized-only expansion passed the whole-project quality gate |
| P1-T030 | Implement the DatpCoreError hierarchy and typed error families | DONE | P0-T026 | 2026-07-14T18:44:43Z | 2026-07-14T19:36:06Z | 2026-07-14T19:36:06Z | Complete | PASS | PASS | PASS | NONE | Complete typed error hierarchy; randomized full pytest and all Nox sessions, Sonar, and CodeScene passed |
| P1-T031 | Implement Pydantic boundary schemas and discriminated unions | DONE | P1-T029 | 2026-07-15T01:00:00Z | 2026-07-15T02:10:00Z | 2026-07-15T02:10:00Z | Complete | PASS | PASS | PASS | NONE | Expanded explicit policy schemas, restored Pydantic confinement, and re-passed the whole-project quality gate |
| P1-T032 | Implement YAML loading, override composition, and schema-to-domain mapping | DONE | P1-T031 | 2026-07-15T02:10:00Z | 2026-07-15T02:20:00Z | 2026-07-15T02:20:00Z | Complete | PASS | PASS | PASS | NONE | Pure profile-first mapping, B0/FedProx/D-temporal guards, YAML boundary, and project quality checks passed |
| P1-T033 | Implement resolved-configuration recording and the typed spec-diff | DONE | P1-T032 | 2026-07-15T02:20:00Z | 2026-07-15T02:50:00Z | 2026-07-15T02:50:00Z | Complete | PASS | PASS | PASS | NONE | Typed pure diff, exhaustive classification guard, and two whole-project random-order pytest runs passed; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T034 | Implement data/learning/scoring/thresholding application ports | DONE | P1-T028, P1-T030 | 2026-07-15T03:00:00Z | 2026-07-15T03:20:00Z | 2026-07-15T03:20:00Z | Complete | PASS | PASS | PASS | NONE | Twelve framework-neutral typed ports, threshold leakage guard, and two whole-project random-order pytest runs passed; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T035 | Implement statistics/reporting/telemetry application ports | DONE | P1-T027, P1-T051, P1-T030 | 2026-07-14T23:35:00Z | 2026-07-14T23:45:00Z | 2026-07-14T23:45:00Z | Complete | PASS | PASS | PASS | NONE | Typed statistic/report/telemetry ports, diagnostic sink isolation, focused checks, configured import-linter, architecture lane, and two randomized whole-project pytest runs passed; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T036 | Implement persistence/runtime application ports | DONE | P1-T008, P1-T009, P1-T033 | 2026-07-14T23:50:00Z | 2026-07-15T04:15:00Z | 2026-07-15T04:15:00Z | Complete | PASS | PASS | PASS | NONE | Eight exact typed ports; domain provenance/runtime record placement repaired; two randomized whole-project runs passed (270 each), plus Ruff/format/Pyright/import-linter/architecture; shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint remains scheduled |
| P1-T037 | Implement reusable pipeline stage functions and concrete services | DONE | P1-T034, P1-T035, P1-T036 | 2026-07-15T05:45:00Z | 2026-07-15T06:00:00Z | 2026-07-15T06:00:00Z | Complete | PASS | PASS | PASS | NONE | Eleven framework-free stages, pure selector/evaluator, typed port doubles, randomized full suite, Nox, Sonar, and CodeScene passed |
| P1-T038 | Implement ExperimentPlanner and the ScoreReuseGate | DONE | P1-T037, P1-T033 | 2026-07-15T06:10:00Z | 2026-07-15T06:10:00Z | 2026-07-15T06:40:00Z | Deterministic closed-profile expansion derives canonical BLAKE3 cell/stage identities and immutable stages; full typed score lineage compares atomically, excluding threshold/report state; no storage access. | Focused unit/property/strict typing passed; whole-project Ruff/format/Pyright/import-linter, architecture lane, and randomized suites passed (306 each). | Shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint after P1-T040 per user batching direction. | No real data, training, scoring, or scientific execution. | NONE | P1-T037 and P1-T033 verified DONE |
| P1-T039 | Implement preflight, executor, lifecycle, and resource-pressure orchestration | DONE | P1-T038 | 2026-07-15T06:45:00Z | 2026-07-15T10:37:25Z | 2026-07-15T10:37:25Z | Frozen typed preflight; exhaustive executor dispatch; terminal OOM lifecycle; equivalence-preserving pressure orchestration. | Focused unit/integration, architecture, Ruff/format/Pyright/import-linter, and two randomized full suites passed (316 each). | Shared P1-T031–P1-T040 Nox/Sonar/CodeScene checkpoint after P1-T040 per user batching direction. | No real data, training, scoring, or scientific execution. | NONE | P1-T038 verified DONE |
| P1-T040 | Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing | DONE | P1-T038, P1-T027 | 2026-07-15T10:37:25Z | 2026-07-15T11:00:11Z | 2026-07-15T11:00:11Z | Typed anchor/feasibility/readiness/freeze/tracing gates, including runtime readiness blocking and canonical 90% Regime D coverage. | Focused unit/property, strict typing, architecture, full Nox, Sonar, CodeScene, and two randomized full suites passed (323 each). | Shared P1-T031–P1-T040 quality checkpoint passed. | No real data, training, scoring, or scientific execution. | NONE | P1-T038 and P1-T027 verified DONE |
| P1-T054 | Implement semantic storage-root binding and path resolution | DONE | P1-T036, P0-T006 | 2026-07-15T04:25:00Z | 2026-07-15T05:35:00Z | 2026-07-15T05:35:00Z | Complete | PASS | PASS | PASS | NONE | Bound all semantic roots; exhaustive typed resolver, deterministic sharding, root-escape, six-root integration, architecture confinement, whole-project Nox, Sonar, and CodeScene passed |
| P1-T055 | Implement content hashing | DONE | P1-T054 | 2026-07-15T11:02:24Z | 2026-07-15T11:07:45Z | 2026-07-15T11:07:45Z | Explicit BLAKE3 byte/chunk/file hashing; explicit SHA-256 path; no generic dispatcher or logical identity derivation. | PASS | PASS | PASS | NONE | Focused tests (8), architecture (12), two randomized full suites (331 each), selected Nox lanes, Sonar, CodeScene, and project audits passed; P1-T054 fixture repaired |
| P1-T056 | Implement serialization and schema-version handling | DONE | P1-T054 | 2026-07-15T11:08:42Z | 2026-07-15T11:18:00Z | 2026-07-15T11:18:00Z | Explicit msgspec manifest/provenance records; schema mismatch returns INCOMPATIBLE; runtime annotation cycle repaired. | PASS | PASS | PASS | NONE | Focused checks, two randomized full suites (338 each), full Nox, Sonar, CodeScene, and project audits passed |
| P1-T057 | Implement atomic single-artifact persistence | DONE | P1-T054, P1-T055, P1-T056 | 2026-07-15T11:16:20Z | 2026-07-15T11:31:27Z | 2026-07-15T11:31:27Z | Complete | PASS | PASS | PASS | NONE | Atomic verified-write/replace/manifest adapter; focused, randomized full, final Nox, Sonar, and CodeScene gates passed; Pylance executable unavailable, strict Pyright passed |
| P1-T058 | Implement immutable multi-file bundle commit and manifest verification | DONE | P1-T057 | 2026-07-15T11:32:39Z | 2026-07-15T11:51:39Z | 2026-07-15T11:51:39Z | Complete | PASS | PASS | PASS | NONE | Marker-gated immutable bundle adapter; focused 21-test suite, randomized whole-project pytest (369), architecture, full Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed |
| P1-T059 | Implement lock providers, leases, and commit ownership | DONE | P1-T057 | 2026-07-15T11:52:51Z | 2026-07-15T12:06:20Z | 2026-07-15T12:06:20Z | Typed filelock leases with distinct computation/commit scopes, dead-owner recovery, typed expiry, and process-safe contention. | PASS | PASS | PASS | NONE | Focused 41-test persistence/port/architecture set, randomized 380-test project suite, full Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed |
| P1-T042 | Implement PyArrow streaming and bounded-pandas data adapters | DONE | P1-T034, P1-T054, P1-T055, P1-T056, P1-T057 | 2026-07-15T12:07:16Z | 2026-07-15T15:50:16Z | 2026-07-15T15:50:16Z | Complete | PASS | PASS | PASS | NONE | Generic bounded scanner/readers, exact two-pass numeric profiling, private client/split streams, partitioned Parquet materialization, and row-order lineage checks; P2-T004–P2-T007 correctly retain concrete data-port semantics; focused 7-test integration, full Nox, Sonar, and CodeScene passed |
| P1-T043 | Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters | DONE | P1-T034, P1-T054, P1-T055, P1-T056 | 2026-07-15T12:23:54Z | 2026-07-15T12:41:48Z | 2026-07-15T12:41:48Z | Complete | PASS | PASS | PASS | NONE | Fixed ReLU 80/40/20 AE, strict CUDA settings, typed DataLoader seed plan, per-worker seeding, spawn context, and framework confinement; focused 20-test unit/architecture/integration/CUDA set, full Nox, Sonar, and CodeScene passed; Pylance unavailable, strict Pyright passed |
| P1-T044 | Implement Flower FedAvg/FedProx and centralized trainers | DONE | P1-T043 | 2026-07-15T12:43:15Z | 2026-07-15T13:03:43Z | 2026-07-15T13:03:43Z | Complete | PASS | PASS | PASS | NONE | Full-participation trainer lifecycle, frozen FedProx grid, distinct centralized identity, Flower confinement; 17 focused tests, 3 CUDA tests, final 13-session Nox, Sonar, and CodeScene passed; Pylance unavailable, strict Pyright passed |
| P1-T045 | Implement scoring, threshold, clustering, quantile, and fed-stats adapters | DONE | P1-T043 | 2026-07-15T13:04:50Z | 2026-07-15T13:30:19Z | 2026-07-15T14:45:28Z | Batched CUDA scoring; all exact quantile/threshold strategies; locked B4 KMeans; full-variance matched-exceedance FedStats; typed comparator identity separation. | PASS | PASS | PASS | NONE | Focused and randomized full-suite validation, shared full Nox, Sonar, and CodeScene passed; synthetic-only scope preserved. |
| P1-T046 | Implement the SciPy statistics adapter and per-family metric calculators | DONE | P1-T035, P1-T056, P1-T057 | 2026-07-15T13:33:29Z | 2026-07-15T13:41:38Z | 2026-07-15T14:45:28Z | Seeded SciPy BCa/Wilcoxon/Spearman/Jensen–Shannon adapter, in-repo Cliff's delta delegation, exact BCA port runner, eight named metric-family calculators, and an explicit SciPy-confinement architecture test. | PASS | PASS | PASS | NONE | Focused and randomized full-suite validation, shared full Nox, Sonar, and CodeScene passed; synthetic-only scope preserved. |
| P1-T060 | Implement CUDA guard and deterministic device initialization | DONE | P1-T035, P1-T036 | 2026-07-15T13:46:52Z | 2026-07-15T13:50:12Z | 2026-07-15T14:45:28Z | Exact fail-loud CUDA guard with one typed assignment, selected-device verification, and strict deterministic initialization. | PASS | PASS | PASS | NONE | Focused and randomized full-suite validation, shared full Nox, Sonar, and CodeScene passed; no silent CPU fallback. |
| P1-T061 | Implement hardware inventory and GPU assignment | DONE | P1-T035, P1-T036 | 2026-07-15T13:51:03Z | 2026-07-15T13:55:14Z | 2026-07-15T14:45:28Z | Read-only complete hardware inventory with CUDA/NVML enrichment and resilient stdlib fallback. | PASS | PASS | PASS | NONE | Focused and randomized full-suite validation, shared full Nox, Sonar, and CodeScene passed; no dataset access. |
| P1-T062 | Implement resource-pressure monitoring and cooperative throttling | DONE | P1-T061 | 2026-07-15T13:56:19Z | 2026-07-15T13:58:49Z | 2026-07-15T14:45:28Z | Observed RAM/VRAM/load monitor, closed cooperative action selection, and immutable observed-peak rollup. | PASS | PASS | PASS | NONE | Focused and randomized full-suite validation, shared full Nox, Sonar, and CodeScene passed; frozen profile preserved. |
| P1-T063 | Implement the CheckpointStore adapter (scientific and recovery persistence) | DONE | P1-T054, P1-T055, P1-T056, P1-T057, P1-T059 | 2026-07-15T14:00:02Z | 2026-07-15T14:13:13Z | 2026-07-15T14:45:28Z | Distinct atomic scientific/recovery metadata repositories, typed compatibility enforcement, and focused unit/contract/architecture/integration/CUDA evidence complete. | PASS | PASS | PASS | NONE | Two randomized full suites, full Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed. |
| P1-T064 | Implement run-state persistence and lifecycle storage | DONE | P1-T054, P1-T056 | 2026-07-15T14:14:38Z | 2026-07-15T14:31:34Z | 2026-07-15T14:45:28Z | Six typed lifecycle records, a durable ordered run-state journal, and focused plus repository-wide audit evidence complete. | PASS | PASS | PASS | NONE | Two randomized full suites, full Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed. |
| P1-T065 | Implement the structured telemetry adapter | DONE | P1-T051, P1-T035 | 2026-07-15T14:22:00Z | 2026-07-15T14:31:34Z | 2026-07-15T14:45:28Z | Bounded asynchronous structlog adapter, typed payload guard, synthetic worker-attribution evidence, and repository-wide audit complete. | PASS | PASS | PASS | NONE | Two randomized full suites, full Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed. |
| P1-T066 | Implement the environment and provenance inventory adapter | DONE | P1-T061 | 2026-07-15T14:45:28Z | 2026-07-15T14:59:23Z | 2026-07-15T15:00:07Z | Typed Git code-state, committed-uv-lock, environment-inventory, and injected-clock adapters implemented; direct lock-adapter wall-clock reads were replaced with the same injected `Clock`. | PASS | PASS | PASS | NONE | Focused provenance/lock tests, two randomized full suites, complete Nox, Sonar, and CodeScene passed; Pylance executable unavailable and strict Pyright passed. |
| P1-T067 | Implement report renderers | DONE | P1-T052, P1-T040, P1-T049 | 2026-07-15T15:25:16Z | 2026-07-15T15:50:16Z | 2026-07-15T15:50:16Z | Complete | PASS | PASS | PASS | NONE | Trace-gated typed render contract; exact Markdown/CSV/Parquet/JSON/LaTeX/SVG/PNG/PDF rendering; 21 focused tests, two randomized 490-test project suites, project Nox, Sonar, and CodeScene passed; Pylance unavailable and strict Pyright passed |
| P1-T068 | Implement the composition root and strategy registries | DONE | P1-T039, P1-T042, P1-T043, P1-T044, P1-T045, P1-T046, P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T060, P1-T061, P1-T062, P1-T063, P1-T064, P1-T065, P1-T066, P1-T067 | 2026-07-15T15:50:16Z | 2026-07-15T16:17:11Z | 2026-07-15T16:17:11Z | Explicit typed root, exhaustive registries, resolved configuration agreement, synthetic full-cell entrypoint, and full-project audit/quality gates passed. | — | — | — | NONE | Pylance executable unavailable; strict Pyright passed. |
| P1-T069 | Implement the CLI boundary and command invocation | DONE | P1-T068 | 2026-07-15T16:19:04Z | 2026-07-15T16:35:02Z | 2026-07-15T16:37:09Z | Typed parser/result boundary, composition-only CLI edge, exhaustive typed exit mapping, and synthetic command evidence complete. | PASS | PASS | PASS | NONE | Full project quality gates: 530-test randomized suites, Nox, Sonar, and CodeScene passed; Pylance executable unavailable and strict Pyright passed. |
| P1-T049 | Implement the analysis table/figure/wording/report-model specification layer | DONE | P1-T052, P1-T026, P1-T027 | 2026-07-15T15:03:25Z | 2026-07-15T15:25:16Z | 2026-07-15T15:25:16Z | Framework-free typed specifications cover every table and permitted figure family, retain dedicated coverage types, and select all pre-committed claim-outcome wording deterministically. | PASS | PASS | PASS | NONE | Focused seven-test analysis suite, two randomized full suites, complete Nox, Sonar, and CodeScene passed; Pylance executable unavailable and strict Pyright passed. |
| P1-T050 | Implement the architecture-boundary and framework-confinement test suite | DONE | P0-T011, P0-T012, P1-T068, P1-T069 | 2026-07-15T16:38:36Z | 2026-07-15T17:00:05Z | 2026-07-15T17:05:26Z | Five architecture modules enforce direct layer edges, framework confinement, generic-name/root-package absence, import side effects, cycles, and checked closed matches; all use adversarial fixtures. BLAKE3 stage fingerprinting was reconciled to P1-T055/Architecture §13.4. Whole-project architecture/static/full/random/Nox/Sonar/CodeScene gates passed. | PASS | PASS | PASS | NONE | Pylance executable unavailable; Pyright strict parity passed. |
| P1-T070 | Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test | DONE | P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, P1-T051–P1-T069 (all 65 other Phase 1 tickets) | 2026-07-15T17:06:34Z | 2026-07-15T17:09:32Z | 2026-07-15T17:15:45Z | Synthetic complete-stage/CLI proof, explicit campaign-boundary refusal, concrete persistence/recovery/determinism/reporting/telemetry checks, full project audit, full Nox, Sonar, and CodeScene complete the socle gate. | PASS | PASS | PASS | NONE | Pylance executable unavailable; strict Pyright parity passed. |

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
- **Unresolved blockers.** The documented Phase 4 Section G/H discrepancy remains fail-closed through P4-T026. P4-T024 is a direct P5-T004 input; unresolved temporal allocation produces a typed blocked/suppression outcome and cannot be inferred. Master Section G/phase overview classify P5-T001–T005 as planning while detailed bodies classify them FORBIDDEN; both prohibit execution and the conflict must be resolved before an active status advance. The Section-H-only P4-T023 → P5-T002 edge likewise requires authorized reconciliation before P5-T002 advances.
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
- **Unresolved blockers.** Regime D remains conditional on P5-T004 feasibility. P6-T007 is NOT_APPLICABLE only with uninterrupted-execution evidence; otherwise its recovery evidence is required before P6-T008. Master Section G makes P6-T007 unconditional for P6-T008 while detailed bodies make it conditional; preserve the detailed terminal-state rule and fail closed on an unresolved interpretation.
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
| P6-T006 | Statistics execution, typed-failure and invalidated-artifact handling | NOT_STARTED | P6-T002, P6-T003, P6-T005; P6-T004 = DONE with artifacts or REJECTED/NOT_APPLICABLE with feasibility/suppression evidence; activated P6-T007 recovery evidence | — | — | — | — | — | — | — | NONE | — |
| P6-T007 | Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits | NOT_STARTED | P6-T001 | — | — | — | — | — | — | — | NONE | — |
| P6-T008 | Complete-cell/statistics/output audits and result freeze | NOT_STARTED | P6-T006; conditional P6-T007 = DONE with recovery/retry evidence or NOT_APPLICABLE with uninterrupted-completion evidence | — | — | — | — | — | — | — | NONE | — |
| P6-T009 | Report rendering, journal integrity/outcome decision, technical-invalidity correction path | NOT_STARTED | P6-T008 | — | — | — | — | — | — | — | NONE | — |

## Register metadata — Phase 7

- **Selected phase.** Phase 7 — Final Result Freeze, Reporting, and Audit (phase-7; P7-).
- **Expected / extracted ticket count.** 12 / 12 (P7-T001–P7-T012); no added, split, moved, retired, or renumbered ticket.
- **Phase gate.** P7-T011 — terminal backlog-closure gate, requiring P7-T012 despite its later number and P4-T025 Appendix A evidence.
- **Current active ticket.** NONE — documentation conversion does not audit, mutate, regenerate, or close scientific evidence.
- **Next eligible ticket.** NONE — P6-T009 is NOT_STARTED.
- **Unresolved blockers.** Phase 4 records a Section G/H conflict in which P4-T024 blocks P7-T008 only in one authority location. Canonical P7-T008 metadata remains unchanged, but the temporal claim audit is fail-closed pending authorized reconciliation or an evidence-defined P4-T024 terminal outcome. Master index/detail also differ on P7-T007 title punctuation and P7-T012 priority formatting; detailed-body values are retained without aliases.
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
| P7-T008 | Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | Precondition authority conflict; status remains NOT_STARTED until eligible | — |
| P7-T009 | Table/figure/export provenance and frozen-output regeneration | NOT_STARTED | P7-T002 | — | — | — | — | — | — | — | NONE | — |
| P7-T010 | Repository cleanup, stale-output detection, and anchor/journal namespace protection | NOT_STARTED | P7-T001 | — | — | — | — | — | — | — | NONE | — |
| P7-T012 | Audit conference-to-journal originality and manuscript handoff evidence | NOT_STARTED | P7-T002, P7-T009 | — | — | — | — | — | — | — | NONE | — |
| P7-T011 | Reviewer red-team, architecture, and roadmap final audits; master-log closure | NOT_STARTED | P7-T004, P7-T005, P7-T006, P7-T007, P7-T008, P7-T009, P7-T010, P7-T012, P4-T025 | — | — | — | — | — | — | — | NONE | — |

## Notes on the Phase 5 through Phase 7 registers

- Ticket-file and register statuses must always agree; mismatch is blocking.
- No row may advance because documentation exists. Every ticket requires its Part A evidence, Part B audits, valid dependencies, cleanup, and the global terminal-state rule.
- The P4-T022 discrepancy and the Section-H-only P4-T023 → P5-T002 / P4-T024 → P7-T008 edges remain authority findings. This register records the resulting fail-closed conditions but does not alter canonical detailed-ticket dependencies.
- Documentation repair never fills Started, Finished, Audit 1–3, or Evidence fields. Only future ticket work may enter evidence, and it must synchronize ticket and register records.
- Before a Phase 6 row enters IN_REVIEW or DONE, its Evidence must name the frozen RunIdentity, relevant ExecutionAttemptId values, attempt/failure/recovery records, reuse/new/invalidated ledger, ResultFreeze identity, and separate integrity/outcome statuses. Before a Phase 7 row enters IN_REVIEW or DONE, its Evidence must name the accepted ResultFreeze identity/manifest hash and the provenance/ReportIdentity for every audited or regenerated output.
