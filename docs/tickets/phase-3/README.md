# Phase 3 — DATP Anchor Campaign

## Phase identity

- **Canonical phase number and code.** 3 / `phase-3`.
- **Purpose.** Freeze the ready anchor implementation, execute only the approved anchor campaign, preserve complete provenance, audit the resulting evidence, and make a journal-unlock decision requiring integrity plus a passed anchor reproduction gate.
- **Permitted work.** Readiness/freeze/audit work plus real anchor operations only for `ANCHOR_CAMPAIGN_ALLOWED` tickets under the frozen plan.
- **Forbidden work.** Journal-track scientific execution, journal datasets or cells, result-driven tuning, invented seed values/order/subsets, generic rerun wording, and any scientific-configuration change hidden as an attempt.
- **Entry criteria.** `P2-T020` is `DONE`, a clean worktree is verified, and resolved anchor configuration is frozen.
- **Exit criteria.** Complete compatible B0–B4 anchor evidence, separate integrity and outcome records, immutable accepted evidence, and a journal-unlock decision requiring a `PassedAnchorReproductionResult`; direction never authorizes repetition or suppression.
- **Expected and actual ticket count.** 11 / 11.
- **Phase gate.** [`P3-T011`](P3-T011.md).
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Campaign boundary

One frozen scientific configuration yields one `RunIdentity`; operational attempts have distinct `ExecutionAttemptId` values. A changed scientific configuration is a new campaign. Resume, compatible recovery, bounded infrastructure retry, technical-invalidity correction, affected-stage recomputation, and a new attempt are distinct operations. A valid weak, null, mixed, unfavorable, or opposite-direction result is frozen evidence and never authorizes a retry.

The fixed FedAvg model and compatible calibration/test score artifacts feed B1–B4; B0 is separate, calibration is benign-only, CV(FPR) is primary, and AUROC is control. The five-seed anchor reproduction/honesty diagnostic is not the ten-seed journal E-C1 confirmatory verdict. No journal execution is permitted in this phase.

## Ordered tickets and dependency sequence

| ID | Title | Type | Priority | Sci-exec | Dependencies | Blocks |
|---|---|---|---|---|---|---|
| [P3-T001](P3-T001.md) | Final anchor implementation audit and clean-worktree check | audit | P0 — Blocking | PLANNING_ONLY | P2-T020. | P3-T002. |
| [P3-T002](P3-T002.md) | Freeze code-state, dependency-lock, and environment provenance | campaign | P0 — Blocking | PLANNING_ONLY | P3-T001, P0-T004. | P3-T006. |
| [P3-T003](P3-T003.md) | Freeze the resolved anchor configuration and verify the authoritative seed plan | campaign | P0 — Blocking | PLANNING_ONLY | P3-T001. | P3-T004. |
| [P3-T004](P3-T004.md) | Verify the anchor experiment matrix and enumerate stage identities and expected artifacts | campaign | P0 — Blocking | PLANNING_ONLY | P3-T003. | P3-T005. |
| [P3-T005](P3-T005.md) | Resource/storage/CUDA/VRAM preflight and output-namespace compatibility | campaign | P0 — Blocking | PLANNING_ONLY | P3-T004, P1-T039, P1-T060, P1-T061, P1-T062. | P3-T006. |
| [P3-T006](P3-T006.md) | Create the anchor campaign identity and execution-attempt identity | campaign | P0 — Blocking | PLANNING_ONLY | P3-T002, P3-T005. | P3-T007. |
| [P3-T007](P3-T007.md) | Execute the coordinated anchor campaign | campaign | P0 — Blocking | ANCHOR_CAMPAIGN_ALLOWED | P3-T006. | P3-T009. |
| [P3-T008](P3-T008.md) | Conditional anchor recovery, resume, and infrastructure-retry handling | campaign | P0 — Blocking | ANCHOR_CAMPAIGN_ALLOWED | P3-T006. | P3-T009. |
| [P3-T009](P3-T009.md) | Completeness and same-model/same-score compatibility audits; typed failure persistence | audit | P0 — Blocking | PLANNING_ONLY | P3-T007; P3-T008 when activated. | P3-T010. |
| [P3-T010](P3-T010.md) | Historical-reference diagnostic and full configured anchor statistical analysis | statistics | P0 — Blocking | ANCHOR_CAMPAIGN_ALLOWED | P3-T009. | P3-T011. |
| [P3-T011](P3-T011.md) | Anchor integrity decision, technical-invalidity correction path, artifact freeze, journal-unlock gate | audit | P0 — Blocking | PLANNING_ONLY | P3-T010. | P4-T001. |

`P3-T001 → P3-T002` and `P3-T001 → P3-T003 → P3-T004 → P3-T005`; `P3-T002` and `P3-T005` join at `P3-T006 → P3-T007`; conditional `P3-T008` joins `P3-T009 → P3-T010 → P3-T011`. Numeric order does not replace these dependencies. `P3-T008` is mandatory when activated and otherwise must finish `NOT_APPLICABLE` with uninterrupted-execution evidence; every other ticket is mandatory.

## Responsibility ownership and unresolved blockers

- `P3-T001`–`P3-T006` own readiness, freeze, campaign/attempt identity, and preflight; `P3-T007` owns frozen-plan execution; `P3-T008` owns conditional recovery; `P3-T009` owns completeness/compatibility; `P3-T010` owns historical reproduction and honesty analysis; `P3-T011` owns integrity, outcome, freeze, and journal unlock.
- Architecture §18 permits a classified transient retry to remain in the same `ExecutionAttemptId`; this differs from master-log Section H for P3-T008. The standalone rule follows the architecture and records the discrepancy rather than silently changing lifecycle semantics.
- The master-log canonical supporting-agent value `artifact-lineage-auditor` for `P3-T004` is not in the present agent catalogue; future implementation must record that role-catalogue discrepancy rather than silently rename it.
- Canonical IDs `P3-T001`–`P3-T011` are preserved. No ticket was added, split, moved, or renumbered.
