# Phase 7 — Final Result Freeze, Reporting, and Audit

## Phase identity

- **Canonical phase number and code.** 7 / `phase-7`.
- **Purpose.** Verify immutable results and lineage, audit scientific/statistical invariants and claims, regenerate planned outputs from frozen artifacts, defend reviewer attacks, establish originality evidence, clean the repository, and close the backlog.
- **Permitted work.** Post-campaign verification, provenance and invariant audits, frozen-output regeneration, reviewer/originality audits, cleanup, and closure.
- **Forbidden work.** New scientific execution, result mutation or suppression, untraced output values, outcome-strengthening changes, or overclaims.
- **Entry criteria.** `P6-T009` recorded journal acceptance.
- **Exit criteria.** Provenance closes, audits pass, planned outputs are regenerated from frozen artifacts, originality evidence completes, and the master log closes with a recorded verdict.
- **Expected and actual ticket count.** 12 / 12.
- **Phase gate.** [`P7-T011`](P7-T011.md).
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Post-campaign boundary

All tickets are `POST_CAMPAIGN_ONLY`. They audit and report immutable evidence; none authorizes a changed configuration, new experiment, manual result injection, hidden output replacement, or a retry intended to obtain a preferable direction. Every integrity-valid weak, null, mixed, unfavorable, or opposite result is retained and presented with locked fallback wording.

The frozen provenance chain is configuration → run → attempt → artifact → checkpoint → score → threshold → evaluation → statistics → result freeze → rendered output. Anchor and journal cohorts, seed plans, namespaces, and reuse evidence remain distinct.

## Ordered tickets and dependency sequence

| ID | Title | Type | Priority | Dependencies | Blocks |
|---|---|---|---|---|---|
| [P7-T001](P7-T001.md) | Immutable-result and artifact-hash verification; manifest completeness | audit | P0 — Blocking | P6-T009 | P7-T002 |
| [P7-T002](P7-T002.md) | Lineage closure and provenance verification | audit | P0 — Blocking | P7-T001 | P7-T009 |
| [P7-T003](P7-T003.md) | Seed-plan completeness and paired-seed validation | audit | P0 — Blocking | P7-T001 | P7-T007 |
| [P7-T004](P7-T004.md) | Same-model/same-score causal-ladder audit | audit | P0 — Blocking | P7-T002 | P7-T011 |
| [P7-T005](P7-T005.md) | Benign-only-calibration, attack-exclusion, and checkpoint-selection audit | audit | P0 — Blocking | P7-T002 | P7-T011 |
| [P7-T006](P7-T006.md) | Metric-orientation, CV(FPR), absolute-dispersion, and AUROC-control audit | audit | P0 — Blocking | P7-T002 | P7-T011 |
| [P7-T007](P7-T007.md) | BCa implementation, CI-direction, secondary-statistics, and degeneracy audit | audit | P0 — Blocking | P7-T003 | P7-T011 |
| [P7-T008](P7-T008.md) | Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates | audit | P0 — Blocking | P7-T002 | P7-T011 |
| [P7-T009](P7-T009.md) | Table/figure/export provenance and frozen-output regeneration | reporting | P0 — Blocking | P7-T002 | P7-T011 |
| [P7-T010](P7-T010.md) | Repository cleanup, stale-output detection, and anchor/journal namespace protection | audit | P0 — Blocking | P7-T001 | P7-T011 |
| [P7-T012](P7-T012.md) | Audit conference-to-journal originality and manuscript handoff evidence | audit | P0 — Blocking | P7-T002, P7-T009 | P7-T011 |
| [P7-T011](P7-T011.md) | Reviewer red-team, architecture, and roadmap final audits; master-log closure | audit | P0 — Blocking | P7-T004–P7-T010, P7-T012, P4-T025 | — |

`P6-T009 → P7-T001`; `P7-T001 → P7-T002, P7-T003, P7-T010`; `P7-T002 → P7-T004, P7-T005, P7-T006, P7-T008, P7-T009`; `P7-T003 → P7-T007`; `P7-T009 → P7-T012`; all listed closure inputs plus `P4-T025 → P7-T011`. P7-T012 is a required closure dependency despite its later number.

## Gate coverage and recorded authority blocker

`P7-T011` is terminal only after every direct dependency has valid terminal evidence, all 28 reviewer loopholes are defended, Architecture §29 invariants are verified, roadmap checklists pass, and the master log has a recorded closure verdict.

The authoritative P4-T024 detailed body lists `P7-T008` as a downstream block, while P7-T008's canonical dependency field lists only `P7-T002`. Existing Phase 4 documentation records this Section G/H discrepancy as fail-closed. This extraction preserves the canonical P7 metadata and records the discrepancy rather than silently adding a dependency: temporal claims remain blocked unless the P4-T024 authority condition is resolved through authorized reconciliation.

Canonical IDs `P7-T001`–`P7-T012` are preserved. No ticket was added, split, moved, or renumbered.
