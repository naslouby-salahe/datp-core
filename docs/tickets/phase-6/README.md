# Phase 6 — Journal Campaign

## Phase identity

- **Canonical phase number and code.** 6 / `phase-6`.
- **Purpose.** Execute the resolved journal campaign, reuse only compatible anchor artifacts, persist complete new artifacts and failures, freeze results, render planned outputs, and record journal acceptance.
- **Permitted work.** Real journal scientific work only in `JOURNAL_CAMPAIGN_ALLOWED` tickets under the frozen Phase 5 manifest; compatible reuse, audits, result freeze, and frozen-output rendering.
- **Forbidden work.** Mini-campaign interpretation, outcome-driven protocol changes, generic rerun wording, inferred reuse, hidden scientific configuration changes, or executing a blocked/suppressed cell.
- **Entry criteria.** `P5-T009` recorded a go decision and the campaign manifest is frozen.
- **Exit criteria.** Complete required cells, statistics, and planned outputs; immutable result manifests; separate integrity and scientific-outcome records; rendered planned outputs; campaign decision.
- **Expected and actual ticket count.** 9 / 9.
- **Phase gate.** [`P6-T009`](P6-T009.md).
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Campaign boundary

One resolved scientific configuration defines a `RunIdentity`; operational attempts are recorded separately. The phase is a coordinated, resumable campaign, not one command, one job, one attempt, or exactly-one physical artifact generation. Reuse requires complete typed lineage. A compatible threshold-only variation reuses scores; an identity-bearing change needs new computation.

A valid weak, null, mixed, unfavorable, or opposite-direction outcome is immutable evidence and must use the roadmap fallback wording. It never authorizes another run. Only a diagnosed technical invalidity may use the recorded corrective path, preserving failed evidence and limiting recomputation to invalidated stages.

## Frozen configuration-catalogue boundary

Phase 6 executes only the Phase 5-frozen named scientific catalogue (`configs/scientific/protocol.yaml`, `configs/scientific/datasets.yaml`, `configs/scientific/regimes.yaml`, `configs/scientific/models.yaml`, `configs/scientific/thresholds.yaml`, `configs/scientific/evaluation.yaml`, and `configs/scientific/experiments.yaml`), selected profile from `configs/execution/profiles.yaml`, artifact/reporting policies, and verified `configs/locks/protocol-lock.json`. The campaign manifest records their digests. No overlay, layered-configuration rule, scalar protocol document, or replacement execution profile is permitted during an attempt.

## Ordered tickets and dependency sequence

| ID | Title | Type | Priority | Sci-exec | Dependencies | Blocks |
|---|---|---|---|---|---|---|
| [P6-T001](P6-T001.md) | Final readiness confirmation and journal execution-attempt creation | campaign | P0 — Blocking | PLANNING_ONLY | P5-T009 | P6-T002 |
| [P6-T002](P6-T002.md) | Journal Regime-A identity completion, reuse validation, and threshold-only execution | campaign | P0 — Blocking | JOURNAL_CAMPAIGN_ALLOWED | P6-T001 | P6-T006 |
| [P6-T003](P6-T003.md) | Regime C execution | campaign | P1 — Mandatory | JOURNAL_CAMPAIGN_ALLOWED | P6-T001 | P6-T006 |
| [P6-T004](P6-T004.md) | Accepted Regime D execution (external + temporal) | campaign | P2 — Conditional | JOURNAL_CAMPAIGN_ALLOWED | P6-T001, P5-T004 | P6-T006 |
| [P6-T005](P6-T005.md) | FedProx and model-personalization stress-test execution | campaign | P1 — Mandatory | JOURNAL_CAMPAIGN_ALLOWED | P6-T001 | P6-T006 |
| [P6-T006](P6-T006.md) | Statistics execution, typed-failure and invalidated-artifact handling | statistics | P0 — Blocking | JOURNAL_CAMPAIGN_ALLOWED | P6-T002, P6-T003, P6-T004, P6-T005 | P6-T008 |
| [P6-T007](P6-T007.md) | Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits | campaign | P0 — Blocking | JOURNAL_CAMPAIGN_ALLOWED | P6-T001 | P6-T008 |
| [P6-T008](P6-T008.md) | Complete-cell/statistics/output audits and result freeze | audit | P0 — Blocking | PLANNING_ONLY | P6-T006; P6-T007 when activated | P6-T009 |
| [P6-T009](P6-T009.md) | Report rendering, journal integrity/outcome decision, technical-invalidity correction path | reporting | P0 — Blocking | PLANNING_ONLY | P6-T008 | P7-T001 |

`P5-T009 → P6-T001`; `P6-T001` opens `P6-T002`–`P6-T005` and conditional `P6-T007`; `P6-T002`–`P6-T005 → P6-T006`; `P6-T006` plus activated `P6-T007 → P6-T008 → P6-T009`. `P6-T007` may be `NOT_APPLICABLE` only with uninterrupted-execution evidence; numeric order never replaces dependencies.

## Gate coverage and blockers

`P6-T004` is conditional and cannot execute until the matching `P5-T004` feasibility record passes; an unresolved Regime D cell remains blocked or suppressed. The frozen cell graph must also cover any feasibility-gated Regime D work assigned to other tickets; it cannot be inferred or forced into execution. Graceful pressure-boundary resume and interruption/transient recovery follow their ticket-specific architecture semantics; CUDA OOM is terminal for the attempt and never auto-retried.

`P6-T009` is the Phase 6 gate. It requires the complete ten-paired-seed E-C1 cohort, complete-cell/statistics/output audits, frozen traced outputs, and separate `CAMPAIGN_INTEGRITY_STATUS` and `SCIENTIFIC_OUTCOME_STATUS` records. Canonical IDs `P6-T001`–`P6-T009` are preserved without additions, splits, moves, or renumbering.

The result-freeze audit also requires failed-attempt, lineage, and namespace records. Master Section G lists P6-T007 as unconditional for P6-T008 while detailed Section H makes it conditional; this extraction preserves the detailed terminal rule: an activated P6-T007 must be DONE with recovery evidence, otherwise it must be NOT_APPLICABLE with uninterrupted-completion evidence.
