# Phase 5 — Journal Campaign Planning and Readiness

## Phase identity

- **Canonical phase number and code.** 5 / `phase-5`.
- **Purpose.** Expand the journal matrix, resolve feasibility, verify lineage reuse, enumerate identities and expected outputs, plan resources, freeze the campaign baseline, and record a go/no-go decision without journal scientific execution.
- **Permitted work.** Matrix and identity enumeration, feasibility and suppression decisions, read-only lineage checks, resource/staging planning, and configuration/provenance freezing.
- **Forbidden work.** Real journal training, scoring, threshold evaluation, reduced/debug runs, result-driven design changes, seed-order inference, or execution under an unfrozen plan.
- **Entry criteria.** `P4-T026` passed; anchor evidence remains frozen and compatible reuse is proven rather than assumed.
- **Exit criteria.** A frozen journal manifest binds the resolved matrix, stage identities, feasibility decisions, reuse ledger, expected-output inventory, resource/staging plan, and a recorded go/no-go verdict.
- **Expected and actual ticket count.** 9 / 9.
- **Phase gate.** [`P5-T009`](P5-T009.md).
- **Status register.** [TICKET_STATUS.md](../TICKET_STATUS.md).

## Campaign boundary

Phase 5 is planning only. The individual Part A classifications are authoritative: `P5-T001`–`P5-T005` are `FORBIDDEN`; `P5-T006`–`P5-T009` are `PLANNING_ONLY`. This preserves the master log's classification distinction without treating either as authority to execute.

Every planned cell must have a collision-free identity, resolved feasibility, and a complete typed reuse classification. Similar paths, artifact names, seed positions, or the anchor's first five seeds do not establish compatibility. A scientific-configuration change creates a new campaign identity; a threshold-only change must not create retraining or rescoring work. A no-go decision is valid and blocks Phase 6.

## Configuration-catalogue boundary

Planning resolves the named scientific documents `configs/scientific/protocol.yaml`, `configs/scientific/datasets.yaml`, `configs/scientific/regimes.yaml`, `configs/scientific/models.yaml`, `configs/scientific/thresholds.yaml`, `configs/scientific/evaluation.yaml`, and `configs/scientific/experiments.yaml` together with `configs/execution/profiles.yaml`. Artifact and reporting policy are read from `configs/artifacts/policy.yaml` and `configs/reporting/policy.yaml`. `configs/locks/protocol-lock.json` must verify the scientific and execution source documents before a campaign baseline or manifest is frozen. No scalar protocol document, overlay, or layered-configuration path is a valid planning input.

## Ordered tickets and dependency sequence

| ID | Title | Type | Priority | Sci-exec | Dependencies | Blocks |
|---|---|---|---|---|---|---|
| [P5-T001](P5-T001.md) | Implementation-completeness and anchor-artifact-compatibility audit | audit | P0 — Blocking | FORBIDDEN | P4-T026, P3-T011 | P5-T002 |
| [P5-T002](P5-T002.md) | Configuration expansion and journal experiment-cell enumeration | campaign | P0 — Blocking | FORBIDDEN | P5-T001, P1-T038 | P5-T003 |
| [P5-T003](P5-T003.md) | Cell-ID uniqueness and stage-identity enumeration | campaign | P0 — Blocking | FORBIDDEN | P5-T002 | P5-T004 |
| [P5-T004](P5-T004.md) | Feasibility-gate resolution, suppression cells, and unresolved-cell blocking | feasibility | P0 — Blocking | FORBIDDEN | P5-T003, P4-T013, P4-T024 | P5-T005 |
| [P5-T005](P5-T005.md) | Reuse and invalidation verification against frozen anchor artifacts | campaign | P0 — Blocking | FORBIDDEN | P5-T003, P1-T033 | P5-T006 |
| [P5-T006](P5-T006.md) | Expected-artifact/table/figure/export inventory and experiment-to-claim/output mapping | reporting | P0 — Blocking | PLANNING_ONLY | P5-T003 | P5-T007 |
| [P5-T007](P5-T007.md) | Resource/storage estimation and worker/CUDA/process/resume-boundary planning | campaign | P0 — Blocking | PLANNING_ONLY | P5-T005, P5-T006 | P5-T008 |
| [P5-T008](P5-T008.md) | Clean-worktree check and freeze of code/dependency/environment/config/campaign identity | campaign | P0 — Blocking | PLANNING_ONLY | P5-T004, P5-T007, P0-T004 | P5-T009 |
| [P5-T009](P5-T009.md) | Journal campaign manifest and final go/no-go decision | campaign | P0 — Blocking | PLANNING_ONLY | P5-T008 | P6-T001 |

`P5-T001 → P5-T002 → P5-T003`; `P5-T003 → P5-T004 → P5-T005` and `P5-T003 → P5-T006`; `P5-T005 + P5-T006 → P5-T007`; `P5-T004 + P5-T007 + P0-T004 → P5-T008 → P5-T009`. Numeric order never replaces dependencies.

## Gate coverage and blockers

`P5-T009` cannot pass without the frozen baseline from `P5-T008`. `P5-T004` must carry the unresolved `P4-T024` temporal-allocation authority condition forward: an unresolved or rejected temporal candidate becomes a typed blocked/suppression outcome, never an inferred allocation or silently executable cell. The master log's Phase 5 phase-wide `PLANNING_ONLY` label and P5-T001–T005 `FORBIDDEN` fields differ; each ticket preserves its detailed-body field, and neither permits execution.

Canonical IDs `P5-T001`–`P5-T009` are preserved. No ticket was added, split, moved, or renumbered.

P5-T009 also requires every P5 terminal evidence record and the explicit no-go conditions for identity collision or ambiguity, unresolved feasibility, failed preflight/storage/CUDA readiness, incomplete expected artifacts or lineage, and premature execution. The Section-H-only P4-T023 → P5-T002 edge is a recorded authority conflict: P5-T002 remains fail-closed until authorized reconciliation determines whether the optional-decision record is a direct dependency.
