# Phase 0 — Repository and Engineering Foundation

## Phase identity

- **Phase number.** 0
- **Canonical phase name.** Repository and Engineering Foundation.
- **Canonical phase code.** `phase-0`.
- **Source of truth for phase membership.** `docs/MASTER_TICKET_LOG.md`, Section F ("Phase overviews" → "Phase 0") and Section G (Master ticket index, rows `P0-T001`–`P0-T026`), Section H (Detailed ticket bodies, `P0-T001`–`P0-T026`).

## Purpose

Establish the Python 3.12 project, repository structure, quality tooling, architecture enforcement, test infrastructure, the canonical provider-agnostic agent/skill/hook/contract/workflow/command governance system, and implementation-task governance — with no scientific behavior of any kind.

(Verbatim from `docs/MASTER_TICKET_LOG.md` Section F, Phase 0 "Purpose".)

## Permitted work

Repository inspection; project metadata; Python 3.12 setup; dependency definitions; lock discipline; empty layered package skeleton; repository layout; lint configuration; formatting configuration; typing configuration; testing infrastructure; architecture enforcement; Nox; CUDA test-lane governance; AI-agent governance; skills; hooks; contracts; workflows; commands; provider-thin adapters; implementation-task governance; quality-gate setup (per the ticket-conversion task's Section 19, "Phase 0 boundary," which is consistent with and extends `docs/MASTER_TICKET_LOG.md`'s own "Permitted work" statement for Phase 0: project scaffolding, tool configuration, empty layered package skeleton, governance catalogue, CI-less local validation lanes, read-only inspection of the existing `ai/` system and reference repository).

## Forbidden work

Scientific execution; real dataset access; preprocessing implementation; model implementation; model training; scoring; threshold construction; evaluation; statistics; experiment execution; experiment configuration values; synthetic implementations that become production algorithms; Phase 1 domain behavior; Phase 1 application behavior; Phase 1 infrastructure behavior; placeholder scientific code; reduced real-data testing; guessed seeds; guessed protocol values; backward compatibility; shims; redirects; temporary future-phase behavior; any domain/application/infrastructure behavior implementation (that is Phase 1); reduced real-data runs of any kind.

The Phase 0 source tree (`src/datp_core/`, created by `P0-T005`) must remain an empty structural skeleton without scientific behavior throughout Phase 0.

## Entry criteria

Authoritative documents present (`docs/Journal_Extension_Master_Roadmap.md`, `docs/DATP Core Architecture.md`); repository accessible.

## Exit criteria

Tooling, layered skeleton, enforcement contracts, test lanes, and governance catalogue exist and pass a baseline quality gate (`P0-T026`, extended in this extraction to also require the Sonar gate `P0-T027`); no source behavior implemented yet.

## Canonical ticket count

- **Per `docs/MASTER_TICKET_LOG.md`.** 26 tickets (`P0-T001`–`P0-T026`), all `P0-Blocking`/`P1-Mandatory`; Phase 0 has no conditional or optional ticket.
- **Extracted in this directory.** 27 tickets (`P0-T001`–`P0-T026` preserved verbatim by canonical ID, plus one added ticket, `P0-T027`).
- **Added ticket and justification.** `P0-T027` — Configure SonarQube/SonarCloud analysis and quality gate. The ticket-conversion task instructions (its Section 16) mandate that every ticket's quality gate include Sonar, and require an explicit ownership decision during extraction: strengthen an existing ticket if one can cleanly own it, otherwise add a new ticket at the next unused canonical ID. No existing Phase 0 ticket can absorb Sonar configuration without becoming overloaded: `P0-T014` ("Establish Nox validation sessions") explicitly forbids "business logic in sessions" and Sonar project configuration is substantive tool configuration, not session wiring; every other Phase 0 tooling ticket (`P0-T007` Ruff, `P0-T008` Pyright, `P0-T009` pytest, `P0-T010` Hypothesis, `P0-T011` import-linter, `P0-T012` pytest-archon, `P0-T013` syrupy) already owns exactly one tool, establishing a one-ticket-per-tool pattern that `P0-T027` follows for Sonar. `P0-T027` is genuinely new: no existing ID was renumbered, reused, or altered, and `docs/MASTER_TICKET_LOG.md` itself was not modified — the addition exists only under `docs/tickets/`.

## Phase-gate ticket

`P0-T026` — Establish implementation-task governance and repository baseline quality gate. Depends directly on every one of `P0-T001`–`P0-T025` (per `docs/MASTER_TICKET_LOG.md`) plus `P0-T027` (added during extraction so the Sonar gate cannot be bypassed); blocks `P1-T001` (outside this phase's extraction scope). Ruff, Pyright strict, Pylance-configuration parity, import-linter contracts, pytest-archon, Nox sessions, the Sonar quality gate, and thin governance adapters must all pass green before `P0-T026` may become `DONE`.

## Ordered ticket table

Ordered by canonical ID; the `Order note` column records the actual dependency-topological position where it differs from ID order (relevant only for `P0-T027`).

| ID | Title | Type | Priority | Depends on | Blocks | Order note |
|---|---|---|---|---|---|---|
| [P0-T001](P0-T001.md) | Audit and record repository starting state | foundation | P0-Blocking | — | P0-T002 | — |
| [P0-T002](P0-T002.md) | Establish the Python 3.12 project and build backend | foundation | P0-Blocking | P0-T001 | P0-T003, P0-T005, P0-T007, P0-T008, P0-T009 | — |
| [P0-T003](P0-T003.md) | Define dependency groups and pin scientific libraries | foundation | P0-Blocking | P0-T002 | P0-T004, P0-T026 | — |
| [P0-T004](P0-T004.md) | Establish dependency-lock discipline | foundation | P0-Blocking | P0-T003 | P3-T002, P5-T008, P0-T026 | Blocks two Phase 3/5 tickets outside this extracted phase; recorded verbatim from the master log. |
| [P0-T005](P0-T005.md) | Create the approved layered source skeleton | architecture | P0-Blocking | P0-T002 | P0-T011, P0-T026 | — |
| [P0-T006](P0-T006.md) | Establish repository root layout and tracked/generated/gitignored policy | foundation | P0-Blocking | P0-T002 | P1-T054, P0-T026 | Blocks a Phase 1 ticket outside this extracted phase; recorded verbatim. |
| [P0-T007](P0-T007.md) | Configure Ruff lint and format | foundation | P1-Mandatory | P0-T002 | P0-T026, P0-T027 | — |
| [P0-T008](P0-T008.md) | Configure Pyright strict typing | foundation | P0-Blocking | P0-T002 | P0-T026, P0-T027 | Also owns Pylance-configuration parity (Section 15 of the conversion task). |
| [P0-T009](P0-T009.md) | Configure pytest, coverage, timeout, and order-randomization | foundation | P0-Blocking | P0-T002 | P0-T010, P0-T026, P0-T027 | — |
| [P0-T010](P0-T010.md) | Configure Hypothesis property-testing profiles | foundation | P1-Mandatory | P0-T009 | P0-T026 | — |
| [P0-T011](P0-T011.md) | Configure import-linter layer contracts | architecture | P0-Blocking | P0-T005 | P0-T026, P1-T050 | — |
| [P0-T012](P0-T012.md) | Configure pytest-archon in-test boundary assertions | architecture | P0-Blocking | P0-T005, P0-T009 | P1-T050, P0-T026 | — |
| [P0-T013](P0-T013.md) | Configure syrupy golden-snapshot support | foundation | P1-Mandatory | P0-T009 | P0-T026 | — |
| [P0-T014](P0-T014.md) | Establish Nox validation sessions | foundation | P0-Blocking | P0-T007, P0-T008, P0-T009 | P0-T015, P0-T026 | — |
| [P0-T015](P0-T015.md) | Establish the serialized CUDA lane and CPU xdist policy | foundation | P0-Blocking | P0-T014 | P0-T026 | — |
| [P0-T016](P0-T016.md) | Audit and consolidate the canonical provider-agnostic AI catalogue | agent-governance | P0-Blocking | P0-T001 | P0-T017, P0-T018, P0-T019, P0-T020, P0-T021 | — |
| [P0-T017](P0-T017.md) | Complete the canonical agent-role catalogue | agent-governance | P0-Blocking | P0-T016 | P0-T024, P0-T026 | — |
| [P0-T018](P0-T018.md) | Complete the canonical skill catalogue | skill | P0-Blocking | P0-T016 | P0-T022, P0-T026 | — |
| [P0-T019](P0-T019.md) | Establish the task-contract template set | agent-governance | P0-Blocking | P0-T016 | P0-T026 | — |
| [P0-T020](P0-T020.md) | Establish the workflow catalogue | workflow | P0-Blocking | P0-T016 | P0-T026 | — |
| [P0-T021](P0-T021.md) | Establish the command catalogue and provider thin adapters | command | P1-Mandatory | P0-T016 | P0-T026 | — |
| [P0-T022](P0-T022.md) | Implement pre-edit and post-edit blocking hooks | hook | P0-Blocking | P0-T018 | P0-T026 | Owns the repository-wide post-implementation-audit mechanism. |
| [P0-T023](P0-T023.md) | Implement structure/naming/typing/comment blocking hooks | hook | P0-Blocking | P0-T007, P0-T008, P0-T011 | P0-T026 | Owns the raw-dictionary prohibition and the ticket/document-reference-in-code prohibition. |
| [P0-T024](P0-T024.md) | Implement scope/threshold/statistics/lineage/config blocking hooks | hook | P0-Blocking | P0-T017 | P0-T026 | Owns the scientific-drift audit *mechanism* that Phase 1+ tickets bind to. |
| [P0-T025](P0-T025.md) | Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks | hook | P0-Blocking | P0-T014 | P0-T026 | Owns the stale-documentation enforcement mechanism. |
| [P0-T026](P0-T026.md) | Establish implementation-task governance and repository baseline quality gate | foundation | P0-Blocking | P0-T001–P0-T025, **P0-T027** | P1-T001 | Phase gate. Dependency on `P0-T027` added during extraction. Owns ticket-status lifecycle governance. |
| [P0-T027](P0-T027.md) | Configure SonarQube/SonarCloud analysis and quality gate | foundation | P0-Blocking | P0-T007, P0-T008, P0-T009 | P0-T026 | **Added ticket** (not in `docs/MASTER_TICKET_LOG.md`); see "Added ticket and justification" above. Owns the Sonar quality gate. |

## Dependencies to `docs/tickets/TICKET_STATUS.md`

The authoritative, single operational status register for every ticket above is [`docs/tickets/TICKET_STATUS.md`](../TICKET_STATUS.md). Every ticket file's own `Status` field must match its row in that register at all times.

## Added or split tickets and justification

- **Added: `P0-T027`.** See "Added ticket and justification" above. No ticket was split; every original `P0-T001`–`P0-T026` responsibility maps to exactly one ticket, unchanged.

## Unresolved blockers

NONE. `docs/MASTER_TICKET_LOG.md` Section F records Phase 0's "Authority blockers" as "None. Phase 0 is pure tooling/governance scaffolding and raises no scientific blocker," and this extraction introduced no new blocker.

## Confirmation that existing canonical IDs were preserved

`P0-T001` through `P0-T026` are preserved exactly as they appear in `docs/MASTER_TICKET_LOG.md` Section G (title, type, priority, scientific-execution classification, campaign scope, dependencies, blocks, roadmap IDs) and Section H (all 37 template fields), with the single documented exception that `P0-T026`'s `Dependencies` field is extended to include the added `P0-T027`. No ticket was renumbered, no retired ID was reused (Phase 0 has no retired ID), and no ticket was moved into or out of Phase 0.

## Responsibility ownership decisions (cross-cutting requirements)

Every standalone ticket file requires the same universal governance content (lifecycle checklist, repository-wide post-implementation audit, architecture boundary audit, raw-dictionary audit, ticket/document-reference-in-code prohibition, documentation/comment audit, full validation list, Pyright/Pylance requirements, Sonar requirements, determinism/reproducibility audit, and the three scientific-drift audits). Beyond that universal content, the following Phase 0 tickets are the canonical *mechanism* owners for the corresponding cross-cutting responsibility, i.e. the ticket whose deliverable is the tool, hook, or gate that makes the requirement enforceable for every ticket in every later phase:

| Responsibility | Owning ticket | Why this ticket and not another |
|---|---|---|
| Sonar quality gate | `P0-T027` | New ticket; see justification above. |
| Pyright/Pylance configuration parity | `P0-T008` | Already owns Pyright strict configuration; Pylance parity is the same configuration surface (`pyproject.toml` Pyright table plus workspace settings), not a distinct tool. |
| Raw-dictionary / `Any` / untyped-`dict` prohibition | `P0-T023` | Already owns the typing hook bound to Pyright strict; the raw-dictionary prohibition is enforced through the same strict-typing surface, not a separate tool. |
| Prohibition on ticket/document references in code | `P0-T023` | Already owns the comment hook (no AI/banner/decorative/stale comments); a source-code reference to a ticket ID or planning document is the same class of defect (a planning artifact leaking into runtime text) as a stale or AI-generated comment. |
| Stale-documentation enforcement | `P0-T025` | Already owns the command/documentation-synchronization hook (`readme_makefile_hook.md`), whose explicit purpose is keeping documentation and commands aligned with actual behavior. |
| Ticket-status lifecycle governance (`docs/tickets/TICKET_STATUS.md` synchronization rules) | `P0-T026` | Already owns "implementation-task governance (ticket-extraction discipline, contract-first, gate order)"; ticket-status synchronization is the same governance responsibility extended to the extracted-ticket regime this conversion task establishes. |
| Repository-wide post-implementation audit (full-project scan, not diff-only) | `P0-T022` | Already owns the post-edit gate, whose explicit purpose is post-implementation checks (typing/tests/cleanup); this extraction requires that gate's scope to be repository-wide rather than diff-only. |
| Scientific-drift audit *mechanism* for Phase 1 onward | `P0-T024` | Already owns the scope/threshold/statistics/lineage/config blocking hooks that encode the locked scientific identity (benign-only calibration, CV(FPR) primary/AUROC control, threshold-scope-only causal variable) as executable gates; Phase 0's *own* three scientific-drift audits (required in every Phase 0 ticket) are necessarily boundary-confirmation audits under Section 19 of the conversion task, since no scientific or domain code exists yet in Phase 0. |

No responsibility above required a second new ticket: each was absorbed by an existing ticket whose stated objective already covers the same enforcement surface, per the conversion task's instruction to prefer strengthening an existing ticket over creating a new one whenever an existing ticket can own the requirement cleanly.
