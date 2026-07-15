# Phase 1 — Complete Technical Socle

## Phase identity

- **Phase number.** 1
- **Canonical phase name.** Complete Technical Socle.
- **Canonical phase code.** `phase-1`.
- **Source of truth for phase membership.** `docs/MASTER_TICKET_LOG.md`, Section F ("Phase overviews" → "Phase 1") and Section G (Master ticket index, `P1-T001`–`P1-T070` rows, excluding the retired `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048`), Section H (Detailed ticket bodies, `P1-T001`–`P1-T070`).

## Purpose

Implement the reusable technical foundation: domain vocabulary, immutable specifications and identities, the configuration boundary and mapping, application ports and stages, infrastructure adapters, artifacts/lineage/reuse, deterministic execution, batching/resource controls, persistence/lifecycle/recovery, and the composition and CLI boundaries — validated entirely with synthetic data and test doubles.

(Verbatim in substance from `docs/MASTER_TICKET_LOG.md` Section F, Phase 1 "Purpose".)

## Permitted work

All socle implementation; synthetic and property/contract/architecture tests; deterministic synthetic arrays and fake adapters; dry-run planning; lineage simulation. Every Phase 1 ticket's scientific-execution classification is `FORBIDDEN` and its campaign scope is `NONE`; validation uses deterministic synthetic arrays, synthetic datasets, fake adapters, and test doubles only — never real N-BaIoT, Edge-IIoTset, or CICIoT2023 data.

## Forbidden work

Any scientific execution; any real N-BaIoT/Edge-IIoTset/CICIoT2023 training or scoring; reduced real-data debugging runs. No Phase 1 module provides an executable path to any of this — the Phase 1 socle-readiness gate (`P1-T070`) includes a dedicated campaign-execution-prohibition guard proving exactly this.

## Entry criteria

The Phase 0 baseline quality gate (`P0-T026`) has passed: the layered skeleton, Ruff, Pyright strict, import-linter, pytest-archon, Nox, the Sonar gate (`P0-T027`), and the full governance catalogue all exist and pass.

## Exit criteria

The full socle is implemented and validated on synthetic data; all architecture-boundary, framework-confinement, lineage/reuse, atomicity, and determinism suites are green; a synthetic end-to-end run of the complete stage sequence passes; a campaign-execution-prohibition guard is in place and verified.

## Canonical ticket count

- **Per `docs/MASTER_TICKET_LOG.md`.** 66 tickets (`P1-T001`–`P1-T070`, with `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` retired as part of the master log's own prior mega-ticket decomposition — this decomposition happened before this extraction task and is not something this extraction introduced). The master log's own accounting: the former `P1-T010` (observability/reporting/test-vocabulary) was split into `P1-T051`–`P1-T053`; the former `P1-T041` (path/hashing/serialization/persistence/locks) was split into `P1-T054`–`P1-T059`; the former `P1-T047` (CUDA/hardware/pressure/checkpoint/recovery/telemetry/reporting) was split into `P1-T060`–`P1-T067`; the former `P1-T048` (composition/CLI) was split into `P1-T068`–`P1-T069`; the former Phase 1 gate `P1-T051` was renumbered to `P1-T070`.
- **Extracted in this directory.** 66 tickets (`P1-T001`–`P1-T070`, exactly matching the master log's own post-decomposition set, preserved verbatim by canonical ID). No ticket was added, split, or renumbered during this extraction; the decomposition above was already final in `docs/MASTER_TICKET_LOG.md` before this extraction began.
- **No addition made during this extraction.** Unlike Phase 0 (which added `P0-T027` for Sonar), every cross-cutting responsibility this conversion task requires (Sonar, Pyright/Pylance parity, raw-dictionary prohibition, ticket/document-reference prohibition, stale-documentation enforcement, ticket-status governance, repository-wide post-implementation audits, the scientific-drift audit mechanism) is already owned by an existing Phase 0 ticket (`P0-T008`, `P0-T022`–`P0-T027`) per Phase 0's own README, and every Phase 1 ticket in this extraction explicitly defers to those Phase 0 owners in its own Part B, Section B13. No new Phase 1 ticket was required.

## Phase-gate ticket

`P1-T070` — Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test. Depends directly on every other Phase 1 ticket (`P1-T001`–`P1-T009`, `P1-T011`–`P1-T040`, `P1-T042`–`P1-T046`, `P1-T049`–`P1-T050`, `P1-T051`–`P1-T069`); blocks `P2-T001` (outside this extracted phase). Domain contracts, telemetry, reporting specifications, artifact schemas, persistence, recovery, composition, the CLI, synthetic end-to-end validation, and the real-campaign-execution prohibition must all pass before this gate — and therefore Phase 2 — may open.

## Ordered ticket table

Ordered by the same presentation order as `docs/MASTER_TICKET_LOG.md` Section H (domain vocabulary → value objects/collections/mathematics → specifications → aggregates → config → application ports → stages/planning/runtime → persistence primitives → data/learning/scoring adapters → CUDA/hardware/persistence adapters → telemetry/reporting → composition/CLI → analysis/architecture-test → the gate), which is also its dependency-topological order.

| ID | Title | Type | Priority | Depends on | Blocks |
|---|---|---|---|---|---|
| [P1-T001](P1-T001.md) | Implement dataset/regime/partition/split domain vocabulary | domain | P0 | P0-T026 | P1-T019 |
| [P1-T002](P1-T002.md) | Implement model/training/checkpoint/score domain vocabulary | domain | P0 | P0-T026 | P1-T021, P1-T023 |
| [P1-T003](P1-T003.md) | Implement threshold-policy/variant/comparator domain vocabulary | domain | P0 | P0-T026 | P1-T024 |
| [P1-T004](P1-T004.md) | Implement metric-family enums and the MetricId union | domain | P0 | P0-T026 | P1-T026 |
| [P1-T005](P1-T005.md) | Implement statistical-method/claim-outcome/absorption vocabulary | domain | P0 | P0-T026 | P1-T027 |
| [P1-T006](P1-T006.md) | Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant | domain | P0 | P0-T026 | P1-T029 |
| [P1-T007](P1-T007.md) | Implement feasibility/rejection/reuse/blocking vocabulary | domain | P0 | P0-T026 | P1-T029, P4-T012 |
| [P1-T008](P1-T008.md) | Implement storage/artifact/manifest vocabulary | domain | P0 | P0-T026 | P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059 |
| [P1-T009](P1-T009.md) | Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary | domain | P0 | P0-T026 | P1-T036, P1-T039 |
| [P1-T051](P1-T051.md) | Implement application telemetry vocabulary and contracts | telemetry | P1 | P0-T026 | P1-T065 |
| [P1-T052](P1-T052.md) | Implement reporting-policy vocabulary | reporting | P1 | P0-T026 | P1-T049 |
| [P1-T053](P1-T053.md) | Implement test-support vocabulary and typed test profiles | test-support | P1 | P0-T026 | P1-T070 |
| [P1-T011](P1-T011.md) | Implement finite-numeric and Decimal probability-like value objects | domain | P0 | P1-T001 | P1-T019, P1-T024 |
| [P1-T012](P1-T012.md) | Implement identity, seed-plan, and stage-fingerprint value objects | domain | P0 | P1-T009 | P1-T013 |
| [P1-T013](P1-T013.md) | Implement per-stage nominal identity dataclasses | domain | P0 | P1-T012 | P1-T028 |
| [P1-T014](P1-T014.md) | Implement resource, traffic-rate, and byte value objects | domain | P0 | P1-T011 | P1-T026 |
| [P1-T015](P1-T015.md) | Implement immutable typed collections and the object-dict prohibition | domain | P0 | P1-T011, P1-T012 | P1-T023 |
| [P1-T016](P1-T016.md) | Implement locked dispersion, quantile, and pooled-variance mathematics | domain | P0 | P1-T011 | P1-T026, P2-T016 |
| [P1-T017](P1-T017.md) | Implement Cliff's delta and effect-size pure functions | domain | P1 | P1-T011 | P1-T027 |
| [P1-T018](P1-T018.md) | Implement locked domain constants and the protocol eligibility rule | domain | P0 | P1-T011, P1-T016 | P1-T026 |
| [P1-T019](P1-T019.md) | Implement dataset, partition, and split specifications | domain | P0 | P1-T001, P1-T011 | P1-T028, P2-T005 |
| [P1-T020](P1-T020.md) | Implement preprocessing and processed-split specifications | domain | P0 | P1-T019 | P1-T028, P2-T007 |
| [P1-T021](P1-T021.md) | Implement model, federation, training, and batch specifications | domain | P0 | P1-T002 | P1-T028, P2-T008 |
| [P1-T022](P1-T022.md) | Implement checkpoint schedule, selection, and recovery specifications | domain | P0 | P1-T002 | P1-T028, P2-T010 |
| [P1-T023](P1-T023.md) | Implement scoring and split-scoped score-artifact specifications | domain | P0 | P1-T002, P1-T015 | P1-T024, P2-T011 |
| [P1-T024](P1-T024.md) | Implement the threshold-construction union and suite specifications | domain | P0 | P1-T003, P1-T023 | P1-T025, P2-T013 |
| [P1-T025](P1-T025.md) | Implement B4 clustering and federated-statistics specifications | domain | P0 | P1-T024 | P2-T015, P4-T018 |
| [P1-T026](P1-T026.md) | Implement evaluation, operating-point, and alert-burden result types | domain | P0 | P1-T004, P1-T014, P1-T016, P1-T018 | P1-T028, P2-T016 |
| [P1-T027](P1-T027.md) | Implement statistical, confirmatory, and anchor-gate result types | domain | P0 | P1-T005, P1-T017 | P1-T028, P2-T018 |
| [P1-T028](P1-T028.md) | Implement the scientific-protocol and policy aggregates | domain | P0 | P1-T019, P1-T020, P1-T021, P1-T022, P1-T023, P1-T024, P1-T026, P1-T027 | P1-T029 |
| [P1-T029](P1-T029.md) | Implement experiment identity/profile/cell aggregates and closed profiles | domain | P0 | P1-T006, P1-T007, P1-T028 | P1-T031, P4-T001 |
| [P1-T030](P1-T030.md) | Implement the DatpCoreError hierarchy and typed error families | domain | P0 | P0-T026 | P1-T034, P1-T037 |
| [P1-T031](P1-T031.md) | Implement Pydantic boundary schemas and discriminated unions | configuration | P0 | P1-T029 | P1-T032 |
| [P1-T032](P1-T032.md) | Implement YAML loading, override composition, and schema-to-domain mapping | configuration | P0 | P1-T031 | P1-T036, P2-T003 |
| [P1-T033](P1-T033.md) | Implement resolved-configuration recording and the typed spec-diff | configuration | P0 | P1-T032 | P1-T036, P5-T005 |
| [P1-T034](P1-T034.md) | Implement data/learning/scoring/thresholding application ports | application | P0 | P1-T028, P1-T030 | P1-T037, P1-T043 |
| [P1-T035](P1-T035.md) | Implement statistics/reporting/telemetry application ports | application | P0 | P1-T027, P1-T051, P1-T030 | P1-T065, P1-T067 |
| [P1-T036](P1-T036.md) | Implement persistence/runtime application ports | application | P0 | P1-T008, P1-T009, P1-T033 | P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T060, P1-T061, P1-T062, P1-T063, P1-T064, P1-T068 |
| [P1-T037](P1-T037.md) | Implement reusable pipeline stage functions and concrete services | application | P0 | P1-T034, P1-T035, P1-T036 | P1-T038, P2-T004 |
| [P1-T038](P1-T038.md) | Implement ExperimentPlanner and the ScoreReuseGate | application | P0 | P1-T037, P1-T033 | P1-T039, P5-T002 |
| [P1-T039](P1-T039.md) | Implement preflight, executor, lifecycle, and resource-pressure orchestration | application | P0 | P1-T038 | P1-T060, P1-T062, P1-T068, P3-T005 |
| [P1-T040](P1-T040.md) | Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing | application | P0 | P1-T038, P1-T027 | P2-T020, P4-T013, P1-T067 |
| [P1-T054](P1-T054.md) | Implement semantic storage-root binding and path resolution | persistence | P0 | P1-T036, P0-T006 | P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T042, P1-T043, P1-T070 |
| [P1-T055](P1-T055.md) | Implement content hashing | persistence | P0 | P1-T054 | P1-T057, P1-T058, P1-T042, P1-T043, P1-T046, P1-T070 |
| [P1-T056](P1-T056.md) | Implement serialization and schema-version handling | persistence | P0 | P1-T054 | P1-T057, P1-T058, P1-T042, P1-T043, P1-T046, P1-T070 |
| [P1-T057](P1-T057.md) | Implement atomic single-artifact persistence | persistence | P0 | P1-T054, P1-T055, P1-T056 | P1-T058, P1-T059, P1-T070 |
| [P1-T058](P1-T058.md) | Implement immutable multi-file bundle commit and manifest verification | persistence | P0 | P1-T057 | P1-T070 |
| [P1-T059](P1-T059.md) | Implement lock providers, leases, and commit ownership | persistence | P0 | P1-T057 | P1-T070 |
| [P1-T042](P1-T042.md) | Implement PyArrow streaming and bounded-pandas data adapters | infrastructure | P0 | P1-T034, P1-T054, P1-T055, P1-T056, P1-T057 | P2-T004 |
| [P1-T043](P1-T043.md) | Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters | infrastructure | P0 | P1-T034, P1-T054, P1-T055, P1-T056 | P1-T044, P2-T008 |
| [P1-T044](P1-T044.md) | Implement Flower FedAvg/FedProx and centralized trainers | infrastructure | P0 | P1-T043 | P2-T009, P4-T016 |
| [P1-T045](P1-T045.md) | Implement scoring, threshold, clustering, quantile, and fed-stats adapters | infrastructure | P0 | P1-T043 | P2-T011, P2-T015 |
| [P1-T046](P1-T046.md) | Implement the SciPy statistics adapter and per-family metric calculators | infrastructure | P0 | P1-T035, P1-T056, P1-T057 | P2-T016, P2-T018 |
| [P1-T060](P1-T060.md) | Implement CUDA guard and deterministic device initialization | infrastructure | P0 | P1-T035, P1-T036 | P1-T039, P1-T068, P1-T070 |
| [P1-T061](P1-T061.md) | Implement hardware inventory and GPU assignment | infrastructure | P0 | P1-T035, P1-T036 | P1-T062, P1-T066, P1-T068, P1-T070 |
| [P1-T062](P1-T062.md) | Implement resource-pressure monitoring and cooperative throttling | infrastructure | P0 | P1-T061 | P1-T039, P1-T068, P1-T070 |
| [P1-T063](P1-T063.md) | Implement the CheckpointStore adapter (scientific and recovery persistence) | persistence | P0 | P1-T054, P1-T055, P1-T056, P1-T057, P1-T059 | P1-T068, P1-T070, P2-T010 |
| [P1-T064](P1-T064.md) | Implement run-state persistence and lifecycle storage | persistence | P0 | P1-T054, P1-T056 | P1-T068, P1-T070 |
| [P1-T065](P1-T065.md) | Implement the structured telemetry adapter | telemetry | P1 | P1-T051, P1-T035 | P1-T068, P1-T070 |
| [P1-T066](P1-T066.md) | Implement the environment and provenance inventory adapter | persistence | P0 | P1-T061 | P1-T068, P1-T070 |
| [P1-T067](P1-T067.md) | Implement report renderers | reporting | P1 | P1-T052, P1-T040 | P1-T068, P1-T070 |
| [P1-T068](P1-T068.md) | Implement the composition root and strategy registries | composition | P0 | P1-T039, P1-T042, P1-T043, P1-T044, P1-T045, P1-T046, P1-T054–P1-T067 (all 14) | P1-T069, P1-T050, P1-T070 |
| [P1-T069](P1-T069.md) | Implement the CLI boundary and command invocation | cli | P0 | P1-T068 | P1-T050, P1-T070 |
| [P1-T049](P1-T049.md) | Implement the analysis table/figure/wording/report-model specification layer | reporting | P1 | P1-T052, P1-T026, P1-T027 | P2-T019, P4-T021 |
| [P1-T050](P1-T050.md) | Implement the architecture-boundary and framework-confinement test suite | architecture | P0 | P0-T011, P0-T012, P1-T068, P1-T069 | P1-T070 |
| [P1-T070](P1-T070.md) | Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test | application | P0 | Every other Phase 1 ticket (65 tickets) | P2-T001 |

## Dependencies to `docs/tickets/TICKET_STATUS.md`

The authoritative, single operational status register for every ticket above is [`docs/tickets/TICKET_STATUS.md`](../TICKET_STATUS.md). Every ticket file's own `Status` field must match its row in that register at all times.

## Added or split tickets and justification

None added or split during this extraction. The mega-ticket decomposition recorded in `docs/MASTER_TICKET_LOG.md`'s own reconstruction-status note (retiring `P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` into `P1-T051`–`P1-T053`, `P1-T054`–`P1-T059`, `P1-T060`–`P1-T067`, and `P1-T068`–`P1-T069`, and renumbering the gate from `P1-T051` to `P1-T070`) was already final in the master log before this extraction began; this extraction preserves that decomposition verbatim by canonical ID.

## Unresolved blockers

NONE at the ticket-extraction level. Individual tickets carry their own conditional "Stop conditions" (for example, P1-T019/P1-T020/P1-T021/P1-T022/P1-T043/P1-T044/P1-T045 each name a specific inherited-semantics value — such as the exact train/calibration allocation inside Edge-IIoTset's first 70%, the AE architecture, the FedProx µ-grid, or the B4 scaler/`n_init`/`max_iter` constants — that must be resolved from the reference project or the roadmap/architecture before that ticket's own implementation may proceed to `DONE`; these are recorded per-ticket, not as phase-level blockers, since none of them prevents any other Phase 1 ticket from being scheduled or from reaching `IN_PROGRESS`).

## Confirmation that existing canonical IDs were preserved

`P1-T001`–`P1-T009`, `P1-T011`–`P1-T040`, `P1-T042`–`P1-T046`, `P1-T049`–`P1-T053`, and `P1-T054`–`P1-T070` are preserved exactly as they appear in `docs/MASTER_TICKET_LOG.md` Section G (title, type, priority, scientific-execution classification, campaign scope, dependencies, blocks, roadmap IDs) and Section H (all 38 template fields). No ticket was renumbered during this extraction, no retired ID (`P1-T010`, `P1-T041`, `P1-T047`, `P1-T048`) was reused, and no ticket was moved into or out of Phase 1.

## Responsibility ownership decisions (cross-cutting requirements)

Every standalone ticket file in this phase requires the same universal governance content (lifecycle checklist, repository-wide post-implementation audit, architecture boundary audit, raw-dictionary audit, ticket/document-reference-in-code prohibition, documentation/comment audit, full validation list, Pyright/Pylance requirements, Sonar requirements, determinism/reproducibility audit, the Phase 1 boundary confirmation, and the three scientific-drift audits). Beyond that universal content, the following tickets are the canonical *mechanism* owners for the corresponding cross-cutting responsibility within Phase 1 itself:

| Responsibility | Owning ticket | Why this ticket and not another |
|---|---|---|
| Repository-wide architecture-boundary and framework-confinement enforcement (for the finished Phase 1 socle specifically) | `P1-T050` | Owns the concrete `tests/architecture/` suite that every other Phase 1 ticket's own B3 audit ultimately executes against, once real Phase 1 modules exist to check. |
| Object-graph composition and strategy-registry population | `P1-T068` | The sole layer with edges to every other layer (Architecture §3.1); every later strategy implementation registers here. |
| Phase 1 socle-readiness gate and synthetic end-to-end proof | `P1-T070` | Depends on all 65 other Phase 1 tickets; the one place lineage/reuse/atomicity/determinism are verified together against the concrete (not merely typed) adapters. |
| Repository-wide raw-dictionary / object-shaped-dictionary prohibition (Phase 1's own contribution to the `P0-T023`-owned mechanism) | `P1-T015` | Owns the typed-collection vocabulary every other Phase 1 domain/application contract must use instead of a raw mapping. |

All cross-phase responsibilities (Pyright/Pylance parity, Sonar quality gate, the raw-dictionary/ticket-reference prohibitions' enforcing hook, stale-documentation enforcement, ticket-status lifecycle governance, the repository-wide post-implementation audit mechanism, and the scientific-drift audit mechanism) remain owned by their Phase 0 tickets exactly as recorded in `docs/tickets/phase-0/README.md` (`P0-T008`, `P0-T022`, `P0-T023`, `P0-T024`, `P0-T025`, `P0-T026`, `P0-T027`); every Phase 1 ticket's own Part B, Section B13 defers to those owners explicitly.

## Note on the ticket-conversion task's Section 19 ("Phase 0 boundary")

The ticket-conversion task that produced this directory structure includes a Section 19, "Phase 0 boundary," which is explicitly written for `PHASE_NUMBER = 0` and lists Phase-0-specific permitted/forbidden work. Because this extraction processes `PHASE_NUMBER = 1`, every standalone Phase 1 ticket substitutes the master log's own explicit Phase 1 "Permitted work"/"Forbidden work" statement (`docs/MASTER_TICKET_LOG.md` Section F, "Phase 1 — Complete Technical Socle") in place of Section 19, since the master log is the authority for phase-membership and phase-boundary content per the conversion task's own authority order (Section 2: "the master ticket log is the authority for ticket identities, phase membership, dependencies, sequencing, priorities, and ownership"). This substitution is recorded once here, and every Phase 1 ticket's own Part B, Section B11 ("Phase 1 boundary confirmation") references this note rather than restating the full justification 66 times.
