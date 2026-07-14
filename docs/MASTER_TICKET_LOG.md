# DATP Journal-Extension — Master Implementation Ticket Log

**Status.** ACTIVE — sole operational implementation backlog for the repository at this stage.

**Reconstruction status (honest accounting for this revision).** This file is undergoing a staged, full reconstruction against `docs/Journal_Extension_Master_Roadmap.md` and `docs/DATP Core Architecture.md`, both read completely across the reconstruction stages performed so far. Completed to date: Sections A, B, C, D, and E; every Phase 0 ticket (P0-T001–P0-T026) in Sections F, G, and H, fully rebuilt under the mandatory ticket template; the Phase 1 mega-ticket decomposition (the former `P1-T010`, `P1-T041`, `P1-T047`, and `P1-T048` tickets have been retired and replaced by twenty new tickets `P1-T051`–`P1-T070`, the last of which is the renumbered Phase 1 socle-readiness gate, formerly `P1-T051`), with every cross-phase reference to a retired ID updated to its correct replacement; the full-template normalization of every remaining Phase 1 ticket (all 66 Phase 1 tickets now use the mandatory template); the full-template normalization of all 23 Phase 2 tickets (P2-T001–P2-T023); the full-template normalization of all 11 Phase 3 tickets (P3-T001–P3-T011); the full-template normalization of all 26 Phase 4 tickets (P4-T001–P4-T026); the full-template normalization of all 9 Phase 5 tickets (P5-T001–P5-T009); the full-template normalization of all 9 Phase 6 tickets (P6-T001–P6-T009); and the full-template normalization of all 12 Phase 7 tickets (P7-T001–P7-T012). **All 182 tickets across all 8 phases (Phase 0 through Phase 7) now use the mandatory 38-field template.** Every phase's ticket count and IDs are unchanged from the prior revision (no overloaded ticket requiring a split was found in Phases 5, 6, or 7). Sections I, J, and K (diagrams and traceability matrices) and the `Campaign scope` column in Section G's shared index table remain in their prior, not-yet-regenerated form; they are not certified by this revision. Section M states this precisely.

**Purpose.** This file is the single authoritative implementation ticket backlog for the `datp_core` journal-extension repository. It covers the complete project lifecycle from the current repository state through repository/engineering foundation, technical socle, complete DATP anchor implementation, the coordinated DATP anchor scientific campaign, complete journal-extension implementation, journal campaign planning and readiness, the coordinated journal scientific campaign, and final result freeze/reporting/traceability/audit. It is a planning artifact only: it contains no source code, tests, configuration, or scientific execution.

**Repository path.** `/home/naslouby/Projects/datp-core`

**Behavioral reference path (read-only).** `/home/naslouby/Projects/datp` — consulted only to recover original DATP autoencoder semantics, preprocessing behavior, client construction, training/calibration/test split semantics, FedAvg behavior, checkpoint behavior, calibration-score and test-score semantics, threshold-policy formulas, evaluation logic, and result interpretation. It is never a source-layout template, migration source, compatibility target, or naming template.

**Authority hierarchy (strict).**
1. `docs/Journal_Extension_Master_Roadmap.md` — sole authority for scientific meaning.
2. `docs/DATP Core Architecture.md` — sole authority for technical and architectural design.
3. `/home/naslouby/Projects/datp` — behavioral evidence only.
4. Existing repository files do not override the architecture or roadmap.
5. This backlog governs ticket structure, planning discipline, and high-level implementation sequencing.
6. When the roadmap is scientifically silent, follow the architecture.
7. When the architecture is technically silent, a ticket must raise an explicit design-decision or blocker rather than invent a rule.
8. No ambiguity is resolved silently; no scientific rule is invented for convenience; no locked rule is weakened.

**Last updated.** 2026-07-13.

**Operational statements.**
- This file is currently the sole operational backlog.
- It will later be split into per-phase and per-ticket files; every ticket below is written to remain understandable in isolation once extracted, without relying on surrounding prose.
- This planning task modifies no implementation files: no source, tests, configs, hooks, agents, skills, workflows, commands, datasets, checkpoints, outputs, or results are changed by producing this log. No repository implementation ticket has been executed; only this backlog document has been reconstructed.

**Total phase count.** 8 (Phase 0 through Phase 7).

**Total ticket count.** 182 entries across 8 phases, all fully reconstructed under the mandatory 38-field template in this and prior revisions: 26 in Phase 0, 66 in Phase 1, 23 in Phase 2, 11 in Phase 3, 26 in Phase 4, 9 in Phase 5, 9 in Phase 6, and 12 in Phase 7 (182 tickets total, 182/182 on the mandatory template).

**Progress summary.** All entries are `NOT_STARTED`. No scientific execution has occurred. No campaign identity has been created.

---

## A. Project identity and scientific locks

These locks are restated concisely from the roadmap and architecture. They are binding on every ticket in every phase, reconstructed or not. The full definitions live in the authoritative documents; this section is an index, not a replacement. Every scientific artifact carries exactly one `ProtocolTrack` (`ProtocolTrack.DATP_ANCHOR` or `ProtocolTrack.JOURNAL_EXTENSION`; Architecture §6.1) and resolves only beneath the matching `ArtifactNamespace` (`DATP_ANCHOR` or `JOURNAL_EXTENSION`; Architecture §6.4, §15.2); the two tracks and their namespaces are never merged or substituted for each other.

- **Fixed encoder for the core B1–B4 ladder.** One FedAvg autoencoder is trained per seed and then frozen; the same selected model state, seeds, calibration-score artifacts, and test-score artifacts feed B1, B2, B3, and B4 without retraining. (Roadmap §2; Architecture §1.2, §29.1.)
- **FedAvg core baseline.** FedAvg is the training baseline of the causal ladder. (Roadmap §2; Architecture §1.2.)
- **E = 1 where locked.** Local epochs E = 1 for the core ladder and matched FedProx stress cells. (Roadmap §2; Architecture §9.1 `FederationSpec`.)
- **Full participation where locked.** `ParticipationStrategy.FULL`; a round aborts on any missing/timed-out/malformed/non-finite/shape-incompatible update. (Architecture §6.3, §16.5.)
- **Threshold-calibration scope is the sole causal variable.** Only the scope at which the anomaly threshold is calibrated changes across B1 (shared), B2 (per-client), B3 (family), B4 (cluster). (Roadmap §2, §3.)
- **Benign-only calibration.** Calibration uses benign data only; attack data are reserved for evaluation and never fit or tune a threshold. (Roadmap §2; Architecture §9.2.)
- **Attack data reserved for evaluation.** Attack scores exist only on TEST-role artifacts. (Architecture §9.2.)
- **CV(FPR) is the primary operating-point endpoint.** CV(FPR) = σ_FPR / µ_FPR over eligible clients. (Roadmap §10; Architecture §29.1.)
- **AUROC is a model-quality control**, never the thresholding verdict. (Roadmap §2; Architecture §11.4, §29.1.)
- **Two distinct seed cohorts, never substituted.** The anchor track (Phase 2–3) reproduces the historical five-seed conference cohort and its own honesty diagnostic. The journal track's confirmatory endpoint (E-C1, Phase 4 onward) uses the ten paired seeds defined by the resolved authoritative seed specification. Neither cohort is inferred from seed position, a "first-N" subset, or the other cohort's identity. (Roadmap §3, §10; Architecture §8.3.)
- **Positive-direction BCa rule.** A confirmatory or honesty-gate claim survives only if its 95% BCa bootstrap CI on Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s] excludes zero in the positive direction. The anchor honesty diagnostic (Phase 3) and the journal confirmatory verdict (Phase 6) are distinct results computed over distinct cohorts and are never presented as one another. (Roadmap §3, §5.1, §10; Architecture §9.3.)
- **Stress-test separation.** FedProx, model personalization, and Laridi-style comparators remain outside the causal ladder and never share its experimental control. (Roadmap §2, SB-25; Architecture §1.2.)
- **B4 canonical K.** Canonical K = 3 with a fixed 4-scalar fingerprint `[mean(error), std(error), skew(error), p95(error)]`; K = 9 and other K are exploratory only. (Roadmap §4, SB-32; Architecture §7.1, §9.2.)
- **B0 is a separate centralized comparator, never a ladder member.** B0 trains through `CentralizedModelTrainer`, never `FederatedTrainer`; it owns its own centralized model, checkpoint, calibration-score, test-score, threshold, and evaluation identities and rejects every FedAvg identity offered to it. (Roadmap §4; Architecture §9.2, §13.1, §29.1.)
- **Fairness = operational/service-level FPR equity.** "Fairness" means the evenness of false-alarm burden across client devices; it never refers to protected-attribute or human fairness. (Roadmap §2; Architecture §1.3.)
- **Out-of-scope boundaries.** Dynamic DATP, poisoning, backdoor, evasion, formal privacy guarantees, deployment/hardware profiling, streaming drift detection, Byzantine-robust federated conformal, and fleet-scale (K > 100) validation are out of scope with no executable path. (Roadmap §5.9, §16; Architecture §1.3, §26.)

No seed identifiers, seed ordering, or execution counts appear anywhere in this log beyond what the authoritative documents state.

---

## B. Campaign semantics

The project has two top-level **protocol tracks** (`ProtocolTrack.DATP_ANCHOR`, `ProtocolTrack.JOURNAL_EXTENSION`; Architecture §6.1), realized operationally as two **campaign scopes**: the DATP anchor campaign (Phase 3) and the journal-extension campaign (Phase 6). These are groupings of coordinated execution under one scientific `RunIdentity`, not new scientific-protocol constraints, and the two tracks are never merged.

- Anchor and journal are top-level operational campaign scopes only; neither defines seed values or seed ordering.
- Campaign scope does **not** imply one operating-system process, one CLI invocation, one machine job, or one uninterrupted session.
- Campaign scope does **not** prohibit resume, and does **not** prohibit valid recomputation after an invalidated upstream identity.
- Campaign scope does **not** mean each artifact is physically generated exactly once; reuse is decided by lineage compatibility (Architecture §13.3), never described as "exactly once."
- **Lineage compatibility determines reuse.** An upstream artifact is reused only when its complete scientific and technical identity is compatible; any identity-bearing upstream change forces recomputation; reuse is rejected when lineage compatibility cannot be proven; scientifically distinct training/scoring/threshold/evaluation/statistical stages keep separate artifact identities; a compatible threshold-only policy change never triggers retraining or rescoring; similar filenames, paths, list position, or seed order never justify reuse.
- **Campaign configuration determines the resolved experiment matrix.**
- **Real development runs are prohibited outside the approved campaign phases** (Phase 3 for the anchor, Phase 6 for the journal).

**Six distinct operational concepts, never conflated with one another or used as a generic "rerun."**
1. **Resume.** An in-progress `ExecutionAttemptId` continues after a safe pause or interruption, using a compatible committed recovery state, under the same `RunIdentity` (Architecture §17–§18).
2. **Recovery.** The act of validating and loading a previously committed compatible `RecoveryState` to resume training; it is conditional on such a state existing and is never assumed to exist (Architecture §17.2–17.3).
3. **Transient infrastructure retry.** A bounded retry of a classified `RETRYABLE_TRANSIENT` failure (for example a lock-acquisition conflict) that never changes scientific output and continues the same `ExecutionAttemptId` (Architecture §20.2).
4. **Technical-invalidity correction.** Corrective work permitted only after a diagnosed technical invalidity — corrupted input, an implementation defect, an incomplete artifact, a lineage mismatch, a determinism/configuration/statistical implementation defect, a framework/infrastructure failure, or an interruption without a valid committed recovery state. It requires a recorded root cause, a corrective ticket, affected and regression tests, a new `ExecutionAttemptId`, preserved failed-attempt evidence, confirmation that scientific configuration did not change (or a new campaign identity if it did), and explicit approval before expensive re-execution.
5. **Affected-stage recomputation.** Recomputing only the stages whose identity was actually invalidated (Architecture §13.3, `ReuseImpact`), never a wholesale rerun of a campaign.
6. **New execution attempt versus new campaign.** A new `ExecutionAttemptId` continues the same `RunIdentity` when scientific configuration is unchanged; any change to scientific configuration produces a new `RunIdentity` and therefore a new campaign identity (Architecture §7, §11.5).

**A scientifically valid outcome that is weak, null, mixed, non-significant, unfavorable, or opposite-direction is never grounds for any of the six actions above.** It is frozen, reported with its pre-committed roadmap fallback wording (Roadmap §12), and never rerun to seek a preferred outcome. Only a diagnosed technical invalidity (item 4) may justify corrective execution, and even then only over the specific invalidated stages, under a new execution attempt, with preserved failed-attempt evidence.

**Execution-attempt vocabulary (Architecture §7, §16.5–16.7, §18).** `RunIdentity` derives from resolved scientific configuration and is unchanged across attempts; `ExecutionAttemptId` is operational and per-attempt; a CUDA-OOM failure is terminal for the current `ExecutionAttemptId` and never auto-transitions to paused/recovered/retried; a later explicit attempt may resume only from a previously committed compatible recovery checkpoint.

---

## C. Status legend

- `NOT_STARTED` — no work begun.
- `READY` — dependencies satisfied; may begin.
- `IN_PROGRESS` — actively being implemented.
- `BLOCKED` — a dependency, decision, or gate prevents progress.
- `IN_REVIEW` — implementation complete; under review.
- `DONE` — complete per the global completion rules (Section E).
- `REJECTED` — deliberately not implemented (with recorded reason).
- `NOT_APPLICABLE` — superseded or out of scope after a recorded decision.

---

## D. Priority, type, scientific-execution and campaign-scope legends

**Priority.**
- `P0 — Blocking` — nothing downstream proceeds without it.
- `P1 — Mandatory` — required for a correct, complete deliverable.
- `P2 — Conditional` — required only when a named condition (feasibility gate, roadmap-optional module) holds.
- `P3 — Optional` — high-value but non-blocking (e.g., roadmap §9.3 optional experiments).

**Ticket types (controlled vocabulary; exactly one per ticket; no compound or slash-joined type is valid).** `foundation` · `architecture` · `domain` · `configuration` · `application` · `infrastructure` · `composition` · `cli` · `telemetry` · `persistence` · `reporting` · `agent-governance` · `skill` · `hook` · `contract` · `workflow` · `command` · `data` · `preprocessing` · `training` · `checkpoint` · `scoring` · `threshold` · `evaluation` · `statistics` · `feasibility` · `experiment` · `campaign` · `audit` · `test-support`. `domain/application` and `composition/CLI` are explicitly invalid ticket types: `domain` and `application` are distinct layers owned by distinct tickets, and `composition` and `cli` are distinct layers owned by distinct tickets (Architecture §3.1, §12.5). A ticket found to require two of these types is overloaded and must be split before it is scheduled.

**Scientific-execution classification (per ticket).** `FORBIDDEN` · `PLANNING_ONLY` · `ANCHOR_CAMPAIGN_ALLOWED` · `JOURNAL_CAMPAIGN_ALLOWED` · `POST_CAMPAIGN_ONLY`. No other value is valid.

**Campaign scope (per ticket).** `NONE` · `ANCHOR` · `JOURNAL` · `POST_CAMPAIGN`. A ticket has exactly one campaign scope; `BOTH_TRACKS` and any combined-track value are invalid.

**Protocol track (per scientific artifact; Architecture §6.1).** `ProtocolTrack.DATP_ANCHOR` · `ProtocolTrack.JOURNAL_EXTENSION`. Every artifact produced by an `ANCHOR_CAMPAIGN_ALLOWED` or `JOURNAL_CAMPAIGN_ALLOWED` ticket carries exactly one of these; they are never mixed within one artifact or manifest.

---

## E. Global completion and terminal-state rules

A ticket is **not** complete merely because files exist. `DONE` requires all of:

- implementation complete for the stated objective;
- required tests (per the ticket's explicit test-category fields in Section H) complete and passing;
- architecture rules passing (import-linter + pytest-archon boundary tests, framework confinement, forbidden-name, no-cycles, no-import-side-effect);
- applicable governance hooks passing;
- cleanup complete (no temp files, no scratch artifacts, no audit clutter, no stray generated files);
- acceptance criteria all pass/fail-verified as pass;
- completion evidence recorded (the ticket's own Section H "Completion evidence" field);
- no unresolved relevant blocker in `ScientificReadinessResult` for the affected scope;
- no unrelated modifications outside the ticket's allowed scope;
- no stale documentation or stale names in touched scope;
- no untracked generated clutter left behind.

For Phase 3 and Phase 6 tickets that perform real execution, completion additionally requires a recorded campaign identity and execution-attempt identity, preserved failure evidence for any failed attempt, and — for any corrective action — the technical-invalidity correction record defined in Section B. A weak, null, mixed, non-significant, unfavorable, or opposite-direction scientific outcome satisfies `DONE` on its own once it is frozen and reported with its fallback wording; it is never a reason to withhold `DONE` or to trigger further execution.

**Terminal-state rule for phase gates.** Mandatory tickets must be `DONE`. A conditional ticket must be `DONE`, `REJECTED` with its failed feasibility condition recorded, or `NOT_APPLICABLE` with an authority-grounded reason. An optional ticket must be `DONE` when selected, `NOT_APPLICABLE` when not selected, or `REJECTED` with an explicit recorded reason. No unresolved, silently skipped, or merely `NOT_STARTED` conditional/optional ticket satisfies a phase gate. A phase-gate ticket must depend, directly or through one named intermediate audit ticket, on every mandatory ticket in its own phase; a gate is not `DONE` while any such dependency is unresolved.

**Campaign decision rule.** `CAMPAIGN_INTEGRITY_STATUS` records technical evidence validity; `SCIENTIFIC_OUTCOME_STATUS` records the observed scientific direction/strength; the two are independent fields. Integrity-valid null, mixed, non-significant, weak, unfavorable, or opposite-direction results are frozen and reported with the roadmap's fallback wording (Roadmap §12). Only a diagnosed technical invalidity (Section B, item 4) may justify corrective work; changed scientific configuration creates a new campaign identity (Section B, item 6); a preferred scientific direction is never grounds for rerun.

**Mandatory ticket template.** Every ticket in Section H uses the exact 38-field template defined at the start of Section H. No ticket may substitute a compact metadata line, an abbreviated field, or a merged field for any named field. `NONE`, `NOT_APPLICABLE`, or `—` are used explicitly where a field has no content; a field is never silently omitted.

---

## F. Phase overviews

### Phase 0 — Repository and Engineering Foundation

- **Purpose.** Establish the Python 3.12 project, repository structure, quality tooling, architecture enforcement, test infrastructure, the canonical provider-agnostic agent/skill/hook/contract/workflow/command governance system, and implementation-task governance.
- **Permitted work.** Project scaffolding, tool configuration, empty layered package skeleton, governance catalogue, CI-less local validation lanes, read-only inspection of the existing `ai/` system and reference repository.
- **Forbidden work.** Any scientific execution; any domain/application/infrastructure behavior implementation (that is Phase 1); reduced real-data runs of any kind.
- **Entry criteria.** Authoritative documents present; repository accessible.
- **Exit criteria.** Tooling, layered skeleton, enforcement contracts, test lanes, and governance catalogue exist and pass a baseline quality gate; no source behavior implemented yet.
- **Mandatory tickets.** P0-T001 through P0-T026 (all `P0-Blocking`/`P1-Mandatory`; Phase 0 has no conditional or optional ticket).
- **Conditional tickets.** None.
- **Optional tickets.** None.
- **Authority blockers.** None. Phase 0 is pure tooling/governance scaffolding and raises no scientific blocker.
- **Phase gate.** Baseline quality gate (P0-T026): depends directly on every one of P0-T001–P0-T025 (repository baseline, project metadata, dependency and lock policy, skeleton/layout, lint/type/test/property/golden/Nox/CUDA lanes, governance catalogue, contracts, workflows, command adapters, hooks) and blocks P1-T001. Ruff, Pyright strict on the empty/typed skeleton, import-linter contracts, Nox sessions, and thin governance adapters must all pass.
- **Downstream phase.** Phase 1, gated exclusively through P1-T001's dependency on P0-T026.
- **Expected deliverables.** `pyproject.toml`, lockfile discipline, source skeleton, `configs/` root, tool configs, `noxfile.py`, `importlinter.ini`, governance catalogue under `ai/` plus thin adapters.
- **Main risks.** Governance duplication across provider folders; premature behavior implementation; tooling drift from the architecture's pinned-library requirements.
- **Ticket count.** 26 (P0-T001–P0-T026), all fully reconstructed under the Section H mandatory template in this revision (see master index, Section G).

### Phase 1 — Complete Technical Socle

- **Purpose.** Implement the reusable technical foundation: domain vocabulary, immutable specifications and identities, configuration boundary and mapping, application ports and stages, infrastructure adapters, artifacts/lineage/reuse, deterministic execution, batching/resource controls, persistence/lifecycle/recovery, composition and CLI boundaries, validated with synthetic data and test doubles.
- **Permitted work.** All socle implementation; synthetic and property/contract/architecture tests; deterministic synthetic arrays and fake adapters; dry-run planning; lineage simulation.
- **Forbidden work.** Any scientific execution; any real N-BaIoT/Edge-IIoTset/CICIoT2023 training or scoring; reduced real-data debugging runs.
- **Entry criteria.** Phase 0 gate (P0-T026) passed.
- **Exit criteria.** Full socle implemented and validated on synthetic data; all architecture-boundary and lineage/atomicity suites green; a synthetic end-to-end run of the full stage sequence passes; a campaign-execution-prohibition guard is in place.
- **Phase gate.** Socle-readiness gate (P1-T070, renumbered from the retired `P1-T051` as part of the mega-ticket decomposition): it explicitly depends on every other Phase 1 ticket, P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, and P1-T051–P1-T069. It passes only when domain contracts, telemetry, reporting specifications, artifact schemas, persistence, recovery, composition, CLI, synthetic end-to-end validation, and the real-campaign-execution prohibition all pass; architecture, framework-confinement, reuse/invalidation, atomicity, and determinism suites are green; no real-data path is exercised.
- **Expected deliverables.** `src/datp_core/{domain,application,config,analysis,infrastructure,composition,cli}` modules; typed collections; error hierarchy; ports/adapters; planner/preflight/executor; storage/lineage.
- **Main risks.** Framework leakage across ports; unstable fingerprints; hidden defaults; object-shaped dictionaries; scattered global seeds.
- **Ticket count.** 66 (P1-T001–P1-T070, with P1-T010/P1-T041/P1-T047/P1-T048 retired). The mega-ticket decomposition mandated by governance is **complete**: `P1-T010` (observability/reporting/test vocabulary) was split into P1-T051 (application telemetry vocabulary), P1-T052 (analysis reporting vocabulary), and P1-T053 (test-support vocabulary); `P1-T041` (path/hashing/serialization/persistence/locks) was split into P1-T054–P1-T059; `P1-T047` (CUDA/hardware/pressure/checkpoint/recovery/telemetry/reporting) was split into P1-T060–P1-T067; `P1-T048` (composition/CLI) was split into P1-T068 (composition root and registries) and P1-T069 (CLI boundary). **All 66 Phase 1 tickets now use the full mandatory template**, including the 46 tickets carried over from the original Phase 1 set, which were rewritten from the prior compact `**Metadata.**` line to the full 38-field template in this revision without changing their IDs, ownership, or dependency meaning; only their `Depends`/`Blocks` fields were updated where they referenced a retired ID.

### Phase 2 — Complete DATP Anchor Implementation

- **Purpose.** Recover original DATP behavioral semantics from the reference repository; implement the complete N-BaIoT anchor pipeline (partitioning, splits, preprocessing, training, checkpoint selection, scoring, B0–B4 thresholding, evaluation, statistics, artifact generation, reporting); make the anchor campaign ready — without real scientific execution.
- **Permitted work.** Read-only reference inspection; source/schema inspection; synthetic-data validation; dry-run anchor planning; expected-artifact inventory; anchor readiness evaluation.
- **Forbidden work.** Any real anchor training or scoring; reduced-seed/reduced-round/reduced-row real-data runs; ad hoc real-data scoring for debugging; any assumption of a specific seed sequence not stated by the roadmap.
- **Entry criteria.** Phase 1 socle-readiness gate passed.
- **Exit criteria.** The full anchor pipeline is implemented and validated on synthetic data; a recovered-semantics register is complete; anchor readiness is evaluable; no real anchor data has been executed.
- **Phase gate.** Anchor-implementation-audit gate (P2-T020): every anchor stage implemented, synthetic end-to-end anchor simulation passes, recovered-semantics blockers closed or explicitly carried into `ScientificReadinessResult`.
- **Expected deliverables.** N-BaIoT adapters; anchor threshold constructions B0–B4; anchor evaluation/statistics; anchor report models; anchor expected-artifact inventory and dry-run planner.
- **Main risks.** Guessed AE/optimizer/preprocessing semantics; leakage in checkpoint selection; incorrect B4 fingerprint/K; inventing a seed sequence.
- **Ticket summary.** P2-T001 … P2-T023, all 23 tickets fully reconstructed under the mandatory 38-field template in this revision (P2-T021–P2-T023 were already in this format, relocated verbatim from Section F in an earlier stage; P2-T001–P2-T020 were rewritten in this stage from the prior compact `**Metadata.**` line without changing any ID, dependency, or scientific content).

### Phase 3 — DATP Anchor Campaign

- **Purpose.** Perform final readiness checks; freeze code/config/environment/dependency/campaign identities; execute the complete configured anchor experiment program; resume safely without changing scientific identity; audit the completed anchor; decide acceptance; freeze accepted evidence; block journal implementation where the roadmap requires anchor acceptance.
- **Permitted work.** Real anchor scientific training and scoring — **only** in tickets classified `ANCHOR_CAMPAIGN_ALLOWED`; readiness checks, freezes, monitoring, resume, audits.
- **Forbidden work.** Any journal-track scientific execution; interpreting the phase as one process/one job/one attempt/one physical write; inventing seed numbers, seed order, a "first-five" subset, or blanket "exactly once" rules; scientific tuning based on observed results.
- **Entry criteria.** Phase 2 anchor-implementation-audit gate passed; clean worktree; resolved anchor configuration frozen.
- **Exit criteria.** The coordinated anchor B0–B4 reproduction program completes; completeness and compatibility audits pass; campaign integrity and scientific outcome are recorded separately; valid anchor evidence (including null, mixed, or unfavorable evidence) is frozen; the journal-unlock gate reflects integrity and any authority-defined blocker, never preferred direction.
- **Phase gate.** Anchor-integrity and journal-unlock gate (P3-T011): every mandatory anchor ticket is `DONE`; conditional recovery is `DONE` when activated or `NOT_APPLICABLE` with uninterrupted-execution evidence; the configured anchor reproduction analysis and honesty diagnostic are complete; `CAMPAIGN_INTEGRITY_STATUS` and `SCIENTIFIC_OUTCOME_STATUS` are recorded separately; only diagnosed technical invalidity can route to corrective work. A scientific direction, strength, significance, or null/mixed result never controls this gate.
- **Expected deliverables.** Frozen anchor manifests; anchor campaign identity and attempt records; completeness/compatibility audit records; anchor acceptance decision; journal-unlock evidence.
- **Main risks.** Dirty worktree at freeze; incomplete outputs mistaken for complete; conflating infrastructure retry with scientific rerun; unresolved cell collisions.
- **Ticket summary.** P3-T001 … P3-T011, all 11 tickets fully reconstructed under the mandatory 38-field template in this revision (rewritten from the prior compact `**Metadata.**` line via three parallel drafting subagents without changing any ID, dependency, or scientific content).

### Phase 4 — Complete Journal-Extension Implementation

- **Purpose.** Implement every mandatory journal experiment and analysis, threshold-only extensions, new regimes and datasets, stress-test comparators, temporal logic where feasible, statistical analysis, feasibility/suppression outcomes, and all report models/renderers the journal campaign needs — without journal scientific execution.
- **Permitted work.** Frozen anchor-artifact inspection; lineage compatibility inspection; dataset feasibility inspection; synthetic implementation tests; dry-run matrix expansion; resource/storage estimation; expected-artifact/table/figure enumeration.
- **Forbidden work.** Any journal scientific run; running q-sensitivity/shrinkage/B2-conf/B4-ablations/FedProx/personalization/external/temporal as real experiments during development; treating real experiments as integration tests.
- **Entry criteria.** Phase 3 anchor acceptance passed (where the roadmap requires it for the affected module).
- **Exit criteria.** Every roadmap experiment family and analysis is implemented and validated on synthetic data; reporting/claim machinery is complete; feasibility/suppression paths are represented.
- **Phase gate.** Journal-implementation-completeness audit (P4-T026): every roadmap experiment ID has specification/config/identity/tests/expected-artifacts/output coverage; every optional experiment has a recorded terminal decision; unresolved temporal allocation and other authority blockers prevent relevant branches from passing; no journal real run occurred.
- **Expected deliverables.** Implementations and specs for E-C1, E-S1–S3, E-M1–M5, E-V1–V3, E-X1, E-T1–T3, E-B1, E-O1, E-Q1–Q6, B0, B-a boundary, and all rejection records; threshold variants; report schemas/renderers.
- **Main risks.** Silently upgrading a supportive module to confirmatory; inventing seeds/orderings for new families; mislabeling personalization; blanket "exactly once" reuse wording.
- **Ticket summary.** P4-T001 … P4-T026, all 26 tickets fully reconstructed under the mandatory 38-field template in this revision (P4-T001–P4-T022 rewritten via five parallel drafting subagents; P4-T023–P4-T026 already used the full template from their earlier relocation out of Section F and required no rewrite).

### Phase 5 — Journal Campaign Planning and Readiness

- **Purpose.** Expand the complete journal experiment matrix; resolve feasibility gates; verify reuse and invalidation; enumerate expensive identities; estimate resources and storage; validate execution staging; freeze code/config/environment/dependencies/campaign plan; produce a formal go/no-go result — without journal scientific execution.
- **Permitted work.** Matrix expansion; cell/identity enumeration; feasibility resolution; resource/storage estimation; execution-staging validation; configuration and code-state freezing.
- **Forbidden work.** Any real training/scoring; using observed scientific results to alter campaign design; inferring seed order; requiring identical seed specs across families unless the roadmap does.
- **Entry criteria.** Phase 4 completeness audit passed.
- **Exit criteria.** A frozen journal campaign manifest, resolved execution graph, enumerated expensive identities, feasibility resolutions, and a recorded go/no-go verdict.
- **Phase gate.** Journal go/no-go gate (P5-T009): formal decision recorded from the frozen plan, with each training/checkpoint/scoring identity classified by complete typed lineage as `REUSABLE_FROM_COMPATIBLE_ANCHOR`, `REQUIRES_NEW_JOURNAL_COMPUTATION`, or `BLOCKED_BY_UNRESOLVED_IDENTITY`.
- **Expected deliverables.** Journal experiment-cell enumeration; expected-artifact/table/figure/export inventories; feasibility resolutions and suppression cells; frozen journal campaign manifest.
- **Main risks.** Cell-ID collisions; unresolved cells not blocked; reuse/invalidation gaps; seed-order inference.
- **Ticket summary.** P5-T001 … P5-T009, all 9 tickets fully reconstructed under the mandatory 38-field template in this revision via parallel drafting subagents, with no ID, dependency, or scientific-content change.

### Phase 6 — Journal Campaign

- **Purpose.** Execute the complete resolved journal experiment program; reuse compatible anchor artifacts; compute threshold-only stages from compatible scores; execute genuinely new training and scoring identities; resume safely; persist failures explicitly; freeze complete journal results; render planned outputs; decide campaign acceptance.
- **Permitted work.** Real journal scientific training/scoring — **only** in tickets classified `JOURNAL_CAMPAIGN_ALLOWED`; reuse validation; threshold-only stage execution; audits; result freeze; rendering.
- **Forbidden work.** Treating stages as independent mini-campaigns; interpreting the phase as one process/one job/one attempt/one seed order/one physical write per artifact; blanket "exactly once" wording.
- **Entry criteria.** Phase 5 go decision recorded; frozen journal campaign manifest.
- **Exit criteria.** The coordinated journal campaign completes; complete-cell/statistics/output audits pass; journal results are frozen; planned outputs render; campaign acceptance is decided.
- **Phase gate.** Journal-integrity and result-freeze gate (P6-T009): complete-cell, complete-statistics, and complete-output audits pass; the ten-paired-seed E-C1 cohort is complete; `CAMPAIGN_INTEGRITY_STATUS` and `SCIENTIFIC_OUTCOME_STATUS` are separately recorded; an uninterrupted campaign may close recovery as `NOT_APPLICABLE`.
- **Expected deliverables.** Journal execution-attempt records; reused-and-new artifact ledger; frozen journal result manifests; rendered planned outputs; acceptance decision.
- **Main risks.** Invalidated-upstream reuse; incomplete outputs mistaken for complete; conflating retries with reruns; scientific config drift creating an unrecorded new campaign identity.
- **Ticket summary.** P6-T001 … P6-T009, all 9 tickets fully reconstructed under the mandatory 38-field template in this revision via parallel drafting subagents, with no ID, dependency, or scientific-content change.

### Phase 7 — Final Result Freeze, Reporting, and Audit

- **Purpose.** Verify frozen results, lineage, scientific invariants, and statistics; regenerate outputs from frozen artifacts; conduct harsh reviewer audits; close the backlog. No new unplanned scientific experiment is introduced.
- **Permitted work.** Immutable-result verification; provenance closure; invariant/statistical audits; frozen-output regeneration; reviewer red-team audits; repository cleanup; backlog closure.
- **Forbidden work.** Any new unplanned scientific experiment; any result suppression; any overclaiming.
- **Entry criteria.** Phase 6 journal acceptance recorded.
- **Exit criteria.** All provenance closes; invariants and statistics audited; outputs regenerated from frozen artifacts; reviewer/architecture/roadmap audits complete; master log closed.
- **Phase gate.** Backlog-closure gate (P7-T011): all Phase 7 audits, including P7-T012 originality evidence, pass and the master log is closed with a recorded verdict.
- **Expected deliverables.** Verification records; provenance-closure reports; regenerated frozen outputs; reviewer/architecture/roadmap audit records; master-log closure entry.
- **Main risks.** Provenance gaps; hidden null/mixed results; stale outputs; namespace bleed between anchor and journal.
- **Ticket summary.** P7-T001 … P7-T012, all 12 tickets fully reconstructed under the mandatory 38-field template in this revision via parallel drafting subagents (P7-T012 already used the full template from an earlier relocation and required no rewrite), with no ID, dependency, or scientific-content change.

---

## G. Master ticket index

All tickets are `NOT_STARTED`. Scientific-execution classification (Sci-Exec) is abbreviated: `FORB` = FORBIDDEN, `PLAN` = PLANNING_ONLY, `ANCH` = ANCHOR_CAMPAIGN_ALLOWED, `JOUR` = JOURNAL_CAMPAIGN_ALLOWED, `POST` = POST_CAMPAIGN_ONLY. `Campaign scope` (Scope) uses the same abbreviation set plus `NONE` (no campaign scope, Phases 0–1). Dependencies and Blocks list explicit ticket IDs only — no phase-wide prose such as "all Phase 1 tickets" is used; where a ticket is a dependency of every subsequent ticket in a phase, it is expressed as blocking that phase's single defined gate ticket. Roadmap IDs list roadmap experiment identifiers where applicable. **All 182 rows below (P0-T001–P7-T012) are fully reconstructed and mechanically cross-checked against their Section H bodies in this revision, including the `Campaign scope` column, added by extracting each ticket's own `Campaign scope` field from Section H (no new value invented).**

<div style="overflow-x:auto">

| ID | Title | Type | Pri | Sci-Exec | Scope | Depends on | Blocks | Roadmap IDs |
|---|---|---|---|---|---|---|---|---|
| P0-T001 | Audit and record repository starting state | foundation | P0 | PLAN | NONE | — | P0-T002 | — |
| P0-T002 | Establish the Python 3.12 project and build backend | foundation | P0 | PLAN | NONE | P0-T001 | P0-T003,P0-T005,P0-T007,P0-T008,P0-T009 | — |
| P0-T003 | Define dependency groups and pin scientific libraries | foundation | P0 | PLAN | NONE | P0-T002 | P0-T004,P0-T026 | — |
| P0-T004 | Establish dependency-lock discipline | foundation | P0 | PLAN | NONE | P0-T003 | P3-T002,P5-T008,P0-T026 | — |
| P0-T005 | Create the approved layered source skeleton | architecture | P0 | PLAN | NONE | P0-T002 | P0-T011,P0-T026 | — |
| P0-T006 | Establish repository root layout and tracked/generated/gitignored policy | foundation | P0 | PLAN | NONE | P0-T002 | P1-T054,P0-T026 | — |
| P0-T007 | Configure Ruff lint and format | foundation | P1 | PLAN | NONE | P0-T002 | P0-T026 | — |
| P0-T008 | Configure Pyright strict typing | foundation | P0 | PLAN | NONE | P0-T002 | P0-T026 | — |
| P0-T009 | Configure pytest, coverage, timeout, and order-randomization | foundation | P0 | PLAN | NONE | P0-T002 | P0-T010,P0-T026 | — |
| P0-T010 | Configure Hypothesis property-testing profiles | foundation | P1 | PLAN | NONE | P0-T009 | P0-T026 | — |
| P0-T011 | Configure import-linter layer contracts | architecture | P0 | PLAN | NONE | P0-T005 | P0-T026,P1-T050 | — |
| P0-T012 | Configure pytest-archon in-test boundary assertions | architecture | P0 | PLAN | NONE | P0-T005,P0-T009 | P1-T050,P0-T026 | — |
| P0-T013 | Configure syrupy golden-snapshot support | foundation | P1 | PLAN | NONE | P0-T009 | P0-T026 | — |
| P0-T014 | Establish Nox validation sessions | foundation | P0 | PLAN | NONE | P0-T007,P0-T008,P0-T009 | P0-T015,P0-T026 | — |
| P0-T015 | Establish the serialized CUDA lane and CPU xdist policy | foundation | P0 | PLAN | NONE | P0-T014 | P0-T026 | — |
| P0-T016 | Audit and consolidate the canonical provider-agnostic AI catalogue | agent-governance | P0 | PLAN | NONE | P0-T001 | P0-T017,P0-T018,P0-T019,P0-T020,P0-T021 | — |
| P0-T017 | Complete the canonical agent-role catalogue | agent-governance | P0 | PLAN | NONE | P0-T016 | P0-T024,P0-T026 | — |
| P0-T018 | Complete the canonical skill catalogue | skill | P0 | PLAN | NONE | P0-T016 | P0-T022,P0-T026 | — |
| P0-T019 | Establish the task-contract template set | agent-governance | P0 | PLAN | NONE | P0-T016 | P0-T026 | — |
| P0-T020 | Establish the workflow catalogue | workflow | P0 | PLAN | NONE | P0-T016 | P0-T026 | — |
| P0-T021 | Establish the command catalogue and provider thin adapters | command | P1 | PLAN | NONE | P0-T016 | P0-T026 | — |
| P0-T022 | Implement pre-edit and post-edit blocking hooks | hook | P0 | PLAN | NONE | P0-T018 | P0-T026 | — |
| P0-T023 | Implement structure/naming/typing/comment blocking hooks | hook | P0 | PLAN | NONE | P0-T007,P0-T008,P0-T011 | P0-T026 | — |
| P0-T024 | Implement scope/threshold/statistics/lineage/config blocking hooks | hook | P0 | PLAN | NONE | P0-T017 | P0-T026 | — |
| P0-T025 | Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks | hook | P0 | PLAN | NONE | P0-T014 | P0-T026 | — |
| P0-T026 | Establish implementation-task governance and repository baseline quality gate | foundation | P0 | PLAN | NONE | P0-T001,P0-T002,P0-T003,P0-T004,P0-T005,P0-T006,P0-T007,P0-T008,P0-T009,P0-T010,P0-T011,P0-T012,P0-T013,P0-T014,P0-T015,P0-T016,P0-T017,P0-T018,P0-T019,P0-T020,P0-T021,P0-T022,P0-T023,P0-T024,P0-T025 | P1-T001 | — |
| P1-T001 | Implement dataset/regime/partition/split domain vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T019 | — |
| P1-T002 | Implement model/training/checkpoint/score domain vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T021,P1-T023 | — |
| P1-T003 | Implement threshold-policy/variant/comparator domain vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T024 | — |
| P1-T004 | Implement metric-family enums and the MetricId union | domain | P0 | FORB | NONE | P0-T026 | P1-T026 | — |
| P1-T005 | Implement statistical-method/claim-outcome/absorption vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T027 | — |
| P1-T006 | Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant | domain | P0 | FORB | NONE | P0-T026 | P1-T029 | — |
| P1-T007 | Implement feasibility/rejection/reuse/blocking vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T029,P4-T012 | — |
| P1-T008 | Implement storage/artifact/manifest vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T054,P1-T055,P1-T056,P1-T057,P1-T058,P1-T059 | — |
| P1-T009 | Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary | domain | P0 | FORB | NONE | P0-T026 | P1-T036,P1-T039 | — |
| P1-T011 | Implement finite-numeric and Decimal probability-like value objects | domain | P0 | FORB | NONE | P1-T001 | P1-T019,P1-T024 | — |
| P1-T012 | Implement identity, seed-plan, and stage-fingerprint value objects | domain | P0 | FORB | NONE | P1-T009 | P1-T013 | — |
| P1-T013 | Implement per-stage nominal identity dataclasses | domain | P0 | FORB | NONE | P1-T012 | P1-T028 | — |
| P1-T014 | Implement resource, traffic-rate, and byte value objects | domain | P0 | FORB | NONE | P1-T011 | P1-T026 | — |
| P1-T015 | Implement immutable typed collections and the object-dict prohibition | domain | P0 | FORB | NONE | P1-T011,P1-T012 | P1-T023 | — |
| P1-T016 | Implement locked dispersion, quantile, and pooled-variance mathematics | domain | P0 | FORB | NONE | P1-T011 | P1-T026,P2-T016 | — |
| P1-T017 | Implement Cliff's delta and effect-size pure functions | domain | P1 | FORB | NONE | P1-T011 | P1-T027 | — |
| P1-T018 | Implement locked domain constants and the protocol eligibility rule | domain | P0 | FORB | NONE | P1-T011,P1-T016 | P1-T026 | — |
| P1-T019 | Implement dataset, partition, and split specifications | domain | P0 | FORB | NONE | P1-T001,P1-T011 | P1-T028,P2-T005 | — |
| P1-T020 | Implement preprocessing and processed-split specifications | domain | P0 | FORB | NONE | P1-T019 | P1-T028,P2-T007 | — |
| P1-T021 | Implement model, federation, training, and batch specifications | domain | P0 | FORB | NONE | P1-T002 | P1-T028,P2-T008 | — |
| P1-T022 | Implement checkpoint schedule, selection, and recovery specifications | domain | P0 | FORB | NONE | P1-T002 | P1-T028,P2-T010 | — |
| P1-T023 | Implement scoring and split-scoped score-artifact specifications | domain | P0 | FORB | NONE | P1-T002,P1-T015 | P1-T024,P2-T011 | — |
| P1-T024 | Implement the threshold-construction union and suite specifications | domain | P0 | FORB | NONE | P1-T003,P1-T023 | P1-T025,P2-T013 | — |
| P1-T025 | Implement B4 clustering and federated-statistics specifications | domain | P0 | FORB | NONE | P1-T024 | P2-T015,P4-T018 | — |
| P1-T026 | Implement evaluation, operating-point, and alert-burden result types | domain | P0 | FORB | NONE | P1-T004,P1-T014,P1-T016,P1-T018 | P1-T028,P2-T016 | — |
| P1-T027 | Implement statistical, confirmatory, and anchor-gate result types | domain | P0 | FORB | NONE | P1-T005,P1-T017 | P1-T028,P2-T018 | E-C1 |
| P1-T028 | Implement the scientific-protocol and policy aggregates | domain | P0 | FORB | NONE | P1-T019,P1-T020,P1-T021,P1-T022,P1-T023,P1-T024,P1-T026,P1-T027 | P1-T029 | — |
| P1-T029 | Implement experiment identity/profile/cell aggregates and closed profiles | domain | P0 | FORB | NONE | P1-T006,P1-T007,P1-T028 | P1-T031,P4-T001 | E-C1 |
| P1-T030 | Implement the DatpCoreError hierarchy and typed error families | domain | P0 | FORB | NONE | P0-T026 | P1-T034,P1-T037 | — |
| P1-T031 | Implement Pydantic boundary schemas and discriminated unions | configuration | P0 | FORB | NONE | P1-T029 | P1-T032 | — |
| P1-T032 | Implement YAML loading, override composition, and schema-to-domain mapping | configuration | P0 | FORB | NONE | P1-T031 | P1-T036,P2-T003 | — |
| P1-T033 | Implement resolved-configuration recording and the typed spec-diff | configuration | P0 | FORB | NONE | P1-T032 | P1-T036,P5-T005 | — |
| P1-T034 | Implement data/learning/scoring/thresholding application ports | application | P0 | FORB | NONE | P1-T028,P1-T030 | P1-T037,P1-T043 | — |
| P1-T035 | Implement statistics/reporting/telemetry application ports | application | P0 | FORB | NONE | P1-T027,P1-T051,P1-T030 | P1-T065,P1-T067 | — |
| P1-T036 | Implement persistence/runtime application ports | application | P0 | FORB | NONE | P1-T008,P1-T009,P1-T033 | P1-T054,P1-T055,P1-T056,P1-T057,P1-T058,P1-T059,P1-T060,P1-T061,P1-T062,P1-T063,P1-T064,P1-T068 | — |
| P1-T037 | Implement reusable pipeline stage functions and concrete services | application | P0 | FORB | NONE | P1-T034,P1-T035,P1-T036 | P1-T038,P2-T004 | — |
| P1-T038 | Implement ExperimentPlanner and the ScoreReuseGate | application | P0 | FORB | NONE | P1-T037,P1-T033 | P1-T039,P5-T002 | — |
| P1-T039 | Implement preflight, executor, lifecycle, and resource-pressure orchestration | application | P0 | FORB | NONE | P1-T038 | P1-T060,P1-T062,P1-T068,P3-T005 | — |
| P1-T040 | Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing | application | P0 | FORB | NONE | P1-T038,P1-T027 | P2-T020,P4-T013,P1-T067 | — |
| P1-T042 | Implement PyArrow streaming and bounded-pandas data adapters | infrastructure | P0 | FORB | NONE | P1-T034,P1-T054,P1-T055,P1-T056,P1-T057 | P2-T004 | — |
| P1-T043 | Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters | infrastructure | P0 | FORB | NONE | P1-T034,P1-T054,P1-T055,P1-T056 | P1-T044,P2-T008 | — |
| P1-T044 | Implement Flower FedAvg/FedProx and centralized trainers | infrastructure | P0 | FORB | NONE | P1-T043 | P2-T009,P4-T016 | — |
| P1-T045 | Implement scoring, threshold, clustering, quantile, and fed-stats adapters | infrastructure | P0 | FORB | NONE | P1-T043 | P2-T011,P2-T015 | — |
| P1-T046 | Implement the SciPy statistics adapter and per-family metric calculators | infrastructure | P0 | FORB | NONE | P1-T035,P1-T056,P1-T057 | P2-T016,P2-T018 | — |
| P1-T049 | Implement the analysis table/figure/wording/report-model specification layer | reporting | P1 | FORB | NONE | P1-T052,P1-T026,P1-T027 | P2-T019,P4-T021 | — |
| P1-T050 | Implement the architecture-boundary and framework-confinement test suite | architecture | P0 | FORB | NONE | P0-T011,P0-T012,P1-T068,P1-T069 | P1-T070 | — |
| P1-T051 | Implement application telemetry vocabulary and contracts | telemetry | P1 | FORB | NONE | P0-T026 | P1-T065 | — |
| P1-T052 | Implement analysis reporting vocabulary | reporting | P1 | FORB | NONE | P0-T026 | P1-T049 | — |
| P1-T053 | Implement test-support vocabulary and typed test profiles | test-support | P1 | FORB | NONE | P0-T026 | P1-T070 | — |
| P1-T054 | Implement semantic storage-root binding and path resolution | persistence | P0 | FORB | NONE | P1-T036,P0-T006 | P1-T055,P1-T056,P1-T057,P1-T058,P1-T059,P1-T042,P1-T043,P1-T070 | — |
| P1-T055 | Implement content hashing | persistence | P0 | FORB | NONE | P1-T054 | P1-T057,P1-T058,P1-T042,P1-T043,P1-T046,P1-T070 | — |
| P1-T056 | Implement serialization and schema-version handling | persistence | P0 | FORB | NONE | P1-T054 | P1-T057,P1-T058,P1-T042,P1-T043,P1-T046,P1-T070 | — |
| P1-T057 | Implement atomic single-artifact persistence | persistence | P0 | FORB | NONE | P1-T054,P1-T055,P1-T056 | P1-T058,P1-T059,P1-T070 | — |
| P1-T058 | Implement immutable multi-file bundle commit and manifest verification | persistence | P0 | FORB | NONE | P1-T057 | P1-T070 | — |
| P1-T059 | Implement lock providers, leases, and commit ownership | persistence | P0 | FORB | NONE | P1-T057 | P1-T070 | — |
| P1-T060 | Implement CUDA guard and deterministic device initialization | infrastructure | P0 | FORB | NONE | P1-T035,P1-T036 | P1-T039,P1-T068,P1-T070 | — |
| P1-T061 | Implement hardware inventory and GPU assignment | infrastructure | P0 | FORB | NONE | P1-T035,P1-T036 | P1-T062,P1-T066,P1-T068,P1-T070 | — |
| P1-T062 | Implement resource-pressure monitoring and cooperative throttling | infrastructure | P0 | FORB | NONE | P1-T061 | P1-T039,P1-T068,P1-T070 | — |
| P1-T063 | Implement the CheckpointStore adapter (scientific and recovery persistence) | persistence | P0 | FORB | NONE | P1-T054,P1-T055,P1-T056,P1-T057,P1-T059 | P1-T068,P1-T070,P2-T010 | — |
| P1-T064 | Implement run-state persistence and lifecycle storage | persistence | P0 | FORB | NONE | P1-T054,P1-T056 | P1-T068,P1-T070 | — |
| P1-T065 | Implement the structured telemetry adapter | telemetry | P1 | FORB | NONE | P1-T051,P1-T035 | P1-T068,P1-T070 | — |
| P1-T066 | Implement the environment and provenance inventory adapter | persistence | P0 | FORB | NONE | P1-T061 | P1-T068,P1-T070 | — |
| P1-T067 | Implement report renderers | reporting | P1 | FORB | NONE | P1-T052,P1-T040 | P1-T068,P1-T070 | — |
| P1-T068 | Implement the composition root and strategy registries | composition | P0 | FORB | NONE | P1-T039,P1-T042,P1-T043,P1-T044,P1-T045,P1-T046,P1-T054,P1-T055,P1-T056,P1-T057,P1-T058,P1-T059,P1-T060,P1-T061,P1-T062,P1-T063,P1-T064,P1-T065,P1-T066,P1-T067 | P1-T069,P1-T050,P1-T070 | — |
| P1-T069 | Implement the CLI boundary and command invocation | cli | P0 | FORB | NONE | P1-T068 | P1-T050,P1-T070 | — |
| P1-T070 | Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test | application | P0 | FORB | NONE | P1-T001,P1-T002,P1-T003,P1-T004,P1-T005,P1-T006,P1-T007,P1-T008,P1-T009,P1-T011,P1-T012,P1-T013,P1-T014,P1-T015,P1-T016,P1-T017,P1-T018,P1-T019,P1-T020,P1-T021,P1-T022,P1-T023,P1-T024,P1-T025,P1-T026,P1-T027,P1-T028,P1-T029,P1-T030,P1-T031,P1-T032,P1-T033,P1-T034,P1-T035,P1-T036,P1-T037,P1-T038,P1-T039,P1-T040,P1-T042,P1-T043,P1-T044,P1-T045,P1-T046,P1-T049,P1-T050,P1-T051,P1-T052,P1-T053,P1-T054,P1-T055,P1-T056,P1-T057,P1-T058,P1-T059,P1-T060,P1-T061,P1-T062,P1-T063,P1-T064,P1-T065,P1-T066,P1-T067,P1-T068,P1-T069 | P2-T001 | — |
| P2-T001 | Recover DATP behavioral semantics from the reference repository (read-only) | data | P0 | PLAN | ANCH | P1-T070 | P2-T002,P2-T004,P2-T008 | — |
| P2-T002 | Record the recovered-semantics register in the master log | data | P0 | PLAN | ANCH | P2-T001 | P2-T020 | — |
| P2-T003 | Inspect the N-BaIoT source and feature schema | data | P0 | PLAN | ANCH | P2-T001,P1-T032 | P2-T004 | — |
| P2-T004 | Implement the N-BaIoT source adapter and deterministic source-row identity | data | P0 | FORB | ANCH | P2-T003,P1-T042 | P2-T005 | ANCHOR-B0–B4 |
| P2-T005 | Implement physical-device (9-client) partitioning | data | P0 | FORB | ANCH | P2-T004,P1-T019 | P2-T006 | ANCHOR-B0–B4 |
| P2-T006 | Implement benign train/calibration and held-out benign/malicious test splits | data | P0 | FORB | ANCH | P2-T005 | P2-T007 | ANCHOR-B0–B4 |
| P2-T007 | Implement preprocessing fit authorization and streaming transform | preprocessing | P0 | FORB | ANCH | P2-T006,P1-T020 | P2-T008 | ANCHOR-B0–B4 |
| P2-T008 | Implement the fixed autoencoder, optimizer, and scheduler | training | P0 | FORB | ANCH | P2-T007,P1-T043,P2-T002 | P2-T009 | ANCHOR-B0–B4 |
| P2-T009 | Implement FedAvg training (E=1, full participation, deterministic CUDA) | training | P0 | FORB | ANCH | P2-T008,P1-T044 | P2-T010 | ANCHOR-B0–B4 |
| P2-T010 | Implement the evidence-recovered anchor checkpoint protocol, persistence, and global selection | checkpoint | P0 | FORB | ANCH | P2-T009,P2-T002,P1-T022 | P2-T011 | ANCHOR-B0–B4 |
| P2-T011 | Implement anchor calibration, benign-test, and malicious-test scoring with atomic score bundles | scoring | P0 | FORB | ANCH | P2-T010,P1-T045 | P2-T012,P2-T013,P2-T022 | ANCHOR-B0–B4 |
| P2-T012 | Implement B0 centralized training branch | training | P1 | FORB | ANCH | P2-T006,P1-T044 | P2-T021 | B0 |
| P2-T013 | Implement canonical anchor B1 shared construction | threshold | P0 | FORB | ANCH | P2-T011,P1-T024 | P2-T016 | ANCHOR-B1 |
| P2-T014 | Implement anchor B2 per-client and B3 family constructions | threshold | P0 | FORB | ANCH | P2-T013 | P2-T016 | ANCHOR-B2–B3 |
| P2-T015 | Implement canonical anchor B4 exact k-means++ clustering and cluster-mean thresholds (K=3) | threshold | P1 | FORB | ANCH | P2-T014,P1-T025 | P2-T016 | ANCHOR-B4 |
| P2-T016 | Implement anchor per-client confusion counts and operating-point metrics | evaluation | P0 | FORB | ANCH | P2-T013,P2-T014,P2-T015,P2-T023,P1-T026 | P2-T017 | ANCHOR-B0–B4 |
| P2-T017 | Implement anchor detection-quality metrics (AUROC control, Macro-F1, P10, worst-client BA) | evaluation | P0 | FORB | ANCH | P2-T016 | P2-T018 | ANCHOR-B0–B4 |
| P2-T018 | Implement anchor paired deltas, BCa diagnostic, Wilcoxon, Cliff's delta, and reference diagnostics | statistics | P0 | FORB | ANCH | P2-T017,P1-T046 | P2-T019 | ANCHOR-B1–B2 |
| P2-T019 | Implement anchor report models, expected-artifact inventory, and dry-run planner | reporting | P0 | PLAN | ANCH | P2-T018,P1-T049 | P2-T020 | ANCHOR-B0–B4 |
| P2-T020 | Implement the anchor readiness evaluator and anchor-implementation audit | audit | P0 | PLAN | ANCH | P2-T019,P2-T002,P1-T040 | P3-T001 | ANCHOR-B0–B4 |
| P2-T021 | Implement B0 centralized checkpoint schedule and scientific checkpoint selection | checkpoint | P1 | FORB | ANCH | P2-T012,P2-T002,P1-T022 | P2-T022 | B0 |
| P2-T022 | Implement B0 centralized calibration and held-out score generation | scoring | P1 | FORB | ANCH | P2-T021,P1-T045 | P2-T023 | B0 |
| P2-T023 | Implement B0 pooled threshold, evaluation, statistics, and reporting route | evaluation | P1 | FORB | ANCH | P2-T022,P1-T026 | P2-T016 | B0 |
| P3-T001 | Final anchor implementation audit and clean-worktree check | audit | P0 | PLAN | ANCH | P2-T020 | P3-T002 | ANCHOR-B0–B4 |
| P3-T002 | Freeze code-state, dependency-lock, and environment provenance | campaign | P0 | PLAN | ANCH | P3-T001,P0-T004 | P3-T006 | ANCHOR-B0–B4 |
| P3-T003 | Freeze the resolved anchor configuration and verify the authoritative seed plan | campaign | P0 | PLAN | ANCH | P3-T001 | P3-T004 | ANCHOR-B0–B4 |
| P3-T004 | Verify the anchor experiment matrix and enumerate stage identities and expected artifacts | campaign | P0 | PLAN | ANCH | P3-T003 | P3-T005 | ANCHOR-B0–B4 |
| P3-T005 | Resource/storage/CUDA/VRAM preflight and output-namespace compatibility | campaign | P0 | PLAN | ANCH | P3-T004,P1-T039,P1-T060,P1-T061,P1-T062 | P3-T006 | ANCHOR-B0–B4 |
| P3-T006 | Create the anchor campaign identity and execution-attempt identity | campaign | P0 | PLAN | ANCH | P3-T002,P3-T005 | P3-T007 | ANCHOR-B0–B4 |
| P3-T007 | Execute the coordinated anchor campaign | campaign | P0 | ANCH | ANCH | P3-T006 | P3-T009 | ANCHOR-B0–B4 |
| P3-T008 | Conditional anchor recovery, resume, and infrastructure-retry handling | campaign | P0 | ANCH | ANCH | P3-T006 | P3-T009 | ANCHOR-B0–B4 |
| P3-T009 | Completeness and same-model/same-score compatibility audits; typed failure persistence | audit | P0 | PLAN | ANCH | P3-T007; P3-T008 when activated | P3-T010 | ANCHOR-B0–B4 |
| P3-T010 | Historical-reference diagnostic and full configured anchor statistical analysis | statistics | P0 | ANCH | ANCH | P3-T009 | P3-T011 | ANCHOR-B0–B4 |
| P3-T011 | Anchor integrity decision, technical-invalidity correction path, artifact freeze, journal-unlock gate | audit | P0 | PLAN | ANCH | P3-T010 | P4-T001 | ANCHOR-B0–B4 |
| P4-T001 | Implement E-C1 confirmatory experiment specification and identity | experiment | P0 | FORB | JOUR | P3-T011,P1-T029 | P4-T022 | E-C1 |
| P4-T002 | Implement E-S1 construction-sensitivity and E-S2 q-sensitivity | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-S1,E-S2 |
| P4-T003 | Implement E-S3 Dirichlet severity (Regime C) | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-S3 |
| P4-T004 | Implement E-M1 cluster/family granularity and stability | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-M1 |
| P4-T005 | Implement E-M2 B4 cluster-feature ablation and contingency | experiment | P1 | FORB | JOUR | P4-T004 | P4-T022 | E-M2 |
| P4-T006 | Implement E-M3 per-client CDF overlays and Ennio deep dive | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-M3 |
| P4-T007 | Implement E-M4 JS↔gain association and E-M5 threshold-shift scatter | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-M4,E-M5 |
| P4-T008 | Implement E-V1 calibration-size sweep and size-aware fallback | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-V1 |
| P4-T009 | Implement E-V2 local-global shrinkage (τ-shrink) | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-V2 |
| P4-T010 | Implement E-V3 split-conformal B2-conf and conformal coverage | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-V3 |
| P4-T011 | Implement the B-a CICIoT2023 boundary | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | B-a |
| P4-T012 | Implement B-b/temporal CICIoT2023 rejection and suppression records | feasibility | P1 | PLAN | JOUR | P1-T007,P4-T011 | P4-T022 | E-R1,E-R2,E-R3,E-R4,E-R5,E-R6,E-R7,E-R8 |
| P4-T013 | Implement the Regime D Edge-IIoTset source/schema/feasibility audit | feasibility | P2 | FORB | JOUR | P4-T001,P1-T040 | P4-T014 | E-X1 |
| P4-T014 | Implement Regime D partitioning, preprocessing, training, and scoring | data | P2 | FORB | JOUR | P4-T013 | P4-T015,P4-T019 | E-X1 |
| P4-T015 | Implement E-X1 external validation | experiment | P2 | FORB | JOUR | P4-T014,P4-T018 | P4-T022 | E-X1 |
| P4-T016 | Implement E-T1 FedProx aggregation stress test | experiment | P1 | FORB | JOUR | P4-T001,P1-T044 | P4-T022 | E-T1 |
| P4-T017 | Implement E-T2 model-personalization stress test and absorption bands | experiment | P1 | FORB | JOUR | P4-T001 | P4-T022 | E-T2 |
| P4-T018 | Implement E-T3 B-FedStatsBenign matched comparator | experiment | P1 | FORB | JOUR | P4-T001,P1-T025 | P4-T015,P4-T022 | E-T3 |
| P4-T019 | Implement E-B1 temporal recalibration MVE | experiment | P2 | FORB | JOUR | P4-T014,P4-T024 | P4-T022 | E-B1 |
| P4-T020 | Implement mandatory E-O1 alert burden evidence and suppression route | experiment | P1 | FORB | JOUR | P4-T001 | P4-T026 | E-O1 |
| P4-T021 | Implement claim tiers, fallback wording, and report schemas/renderers | reporting | P0 | FORB | JOUR | P4-T001,P1-T049 | P4-T022 | — |
| P4-T022 | Implement journal expected-artifact/table/figure inventory and completeness audit | audit | P0 | PLAN | JOUR | P4-T002,P4-T003,P4-T004,P4-T005,P4-T006,P4-T007,P4-T008,P4-T009,P4-T010,P4-T011,P4-T012,P4-T015,P4-T016,P4-T017,P4-T018,P4-T019,P4-T020,P4-T021,P4-T023,P4-T024,P4-T025 | P5-T001 | all |
| P4-T023 | Record optional E-Q1–E-Q6 selections and implement selected supplements | experiment | P3 | FORB | JOUR | P4-T001 | P4-T026 | E-Q1,E-Q2,E-Q3,E-Q4,E-Q5,E-Q6 |
| P4-T024 | Resolve chronological temporal training/calibration allocation | feasibility | P0 | PLAN | JOUR | P4-T001 | P4-T019,P5-T004,P6-T004 | E-B1 |
| P4-T025 | Produce Appendix A B2 calibration-versus-held-out FPR analysis | reporting | P1 | FORB | JOUR | P4-T001,P4-T008,P4-T009,P4-T010 | P4-T026,P7-T011 | E-C1,E-V1,E-V2,E-V3 |
| P4-T026 | Complete journal implementation audit and phase gate | audit | P0 | PLAN | JOUR | P4-T022,P4-T023,P4-T024,P4-T025 | P5-T001 | all |
| P5-T001 | Implementation-completeness and anchor-artifact-compatibility audit | audit | P0 | PLAN | JOUR | P4-T026,P3-T011 | P5-T002 | — |
| P5-T002 | Configuration expansion and journal experiment-cell enumeration | campaign | P0 | PLAN | JOUR | P5-T001,P1-T038 | P5-T003 | all |
| P5-T003 | Cell-ID uniqueness and stage-identity enumeration | campaign | P0 | PLAN | JOUR | P5-T002 | P5-T004 | all |
| P5-T004 | Feasibility-gate resolution, suppression cells, and unresolved-cell blocking | feasibility | P0 | PLAN | JOUR | P5-T003,P4-T013,P4-T024 | P5-T005 | E-X1,E-B1,B-a |
| P5-T005 | Reuse and invalidation verification against frozen anchor artifacts | campaign | P0 | PLAN | JOUR | P5-T003,P1-T033 | P5-T006 | — |
| P5-T006 | Expected-artifact/table/figure/export inventory and experiment-to-claim/output mapping | reporting | P0 | PLAN | JOUR | P5-T003 | P5-T007 | all |
| P5-T007 | Resource/storage estimation and worker/CUDA/process/resume-boundary planning | campaign | P0 | PLAN | JOUR | P5-T005,P5-T006 | P5-T008 | — |
| P5-T008 | Clean-worktree check and freeze of code/dependency/environment/config/campaign identity | campaign | P0 | PLAN | JOUR | P5-T004,P5-T007,P0-T004 | P5-T009 | — |
| P5-T009 | Journal campaign manifest and final go/no-go decision | campaign | P0 | PLAN | JOUR | P5-T008 | P6-T001 | all |
| P6-T001 | Final readiness confirmation and journal execution-attempt creation | campaign | P0 | PLAN | JOUR | P5-T009 | P6-T002 | — |
| P6-T002 | Journal Regime-A identity completion, reuse validation, and threshold-only execution | campaign | P0 | JOUR | JOUR | P6-T001 | P6-T006 | E-C1,E-S1,E-S2,E-V1,E-V2,E-V3,E-T3,E-M1,E-M2,E-M3,E-M4,E-M5,B0,B-a,E-Q1,E-Q2,E-Q3,E-Q4,E-Q5,E-Q6 |
| P6-T003 | Regime C execution | campaign | P1 | JOUR | JOUR | P6-T001 | P6-T006 | E-S3 |
| P6-T004 | Accepted Regime D execution (external + temporal) | campaign | P2 | JOUR | JOUR | P6-T001,P5-T004 | P6-T006 | E-X1,E-B1 |
| P6-T005 | FedProx and model-personalization stress-test execution | campaign | P1 | JOUR | JOUR | P6-T001 | P6-T006 | E-T1,E-T2 |
| P6-T006 | Statistics execution, typed-failure and invalidated-artifact handling | statistics | P0 | JOUR | JOUR | P6-T002,P6-T003,P6-T004,P6-T005 | P6-T008 | all |
| P6-T007 | Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits | campaign | P0 | JOUR | JOUR | P6-T001 | P6-T008 | — |
| P6-T008 | Complete-cell/statistics/output audits and result freeze | audit | P0 | PLAN | JOUR | P6-T006,P6-T007 | P6-T009 | all |
| P6-T009 | Report rendering, journal integrity/outcome decision, technical-invalidity correction path | reporting | P0 | PLAN | JOUR | P6-T008 | P7-T001 | all |
| P7-T001 | Immutable-result and artifact-hash verification; manifest completeness | audit | P0 | POST | POST | P6-T009 | P7-T002 | — |
| P7-T002 | Lineage closure and provenance verification | audit | P0 | POST | POST | P7-T001 | P7-T009 | — |
| P7-T003 | Seed-plan completeness and paired-seed validation | audit | P0 | POST | POST | P7-T001 | P7-T007 | E-C1 |
| P7-T004 | Same-model/same-score causal-ladder audit | audit | P0 | POST | POST | P7-T002 | P7-T011 | — |
| P7-T005 | Benign-only-calibration, attack-exclusion, and checkpoint-selection audit | audit | P0 | POST | POST | P7-T002 | P7-T011 | — |
| P7-T006 | Metric-orientation, CV(FPR), absolute-dispersion, and AUROC-control audit | audit | P0 | POST | POST | P7-T002 | P7-T011 | — |
| P7-T007 | BCa implementation, CI-direction, secondary-statistics, degeneracy audit | audit | P0 | POST | POST | P7-T003 | P7-T011 | E-C1 |
| P7-T008 | Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates | audit | P0 | POST | POST | P7-T002 | P7-T011 | E-X1,E-B1,E-O1 |
| P7-T009 | Table/figure/export provenance and frozen-output regeneration | reporting | P0 | POST | POST | P7-T002 | P7-T011 | all |
| P7-T010 | Repository cleanup, stale-output detection, and anchor/journal namespace protection | audit | P0 | POST | POST | P7-T001 | P7-T011 | — |
| P7-T011 | Reviewer red-team, architecture, and roadmap final audits; master-log closure | audit | P0 | POST | POST | P7-T004,P7-T005,P7-T006,P7-T007,P7-T008,P7-T009,P7-T010,P7-T012,P4-T025 | — | all |
| P7-T012 | Audit conference-to-journal originality and manuscript handoff evidence | audit | P0 | POST | POST | P7-T002,P7-T009 | P7-T011 | — |

</div>

---

## H. Detailed ticket bodies

Every ticket below uses the exact mandatory template (37 named fields, in this order): Ticket ID; Title; Phase; Status; Priority; Ticket type; Owner; Supporting agents; Scientific-execution classification; Campaign scope; Roadmap experiment IDs; Architecture contracts/types owned; Objective; Why this ticket exists; Authority references; Dependencies; Blocks; Downstream consumers; Preconditions; Inputs; Allowed scope; Forbidden actions; Required configuration or NONE; Implementation responsibilities; Required unit tests; Required property tests; Required contract tests; Required architecture tests; Required integration tests; Required CUDA tests; Required system/end-to-end tests; Validation commands; Acceptance criteria; Completion evidence; Failure and blocker behavior; Stop conditions; Deliverables; Final review checklist. `NONE`, `NOT_APPLICABLE`, or `—` is used explicitly wherever a field has no content for that ticket; no field is omitted. Trivial tests (enum-membership, enum-spelling, dataclass-existence, constant-existence, default-Python-enum-behavior) are never required; test fields instead name the meaningful validation, invalid-combination, serialization-stability, exhaustive-dispatch, or lineage/determinism/atomicity/recovery/scientific-invariant behavior actually being checked, or state `NONE` when a category genuinely does not apply (Phase 0 tickets are tooling/governance and own no domain contract, so most Phase 0 property/contract/CUDA/system fields are `NONE`). "Authority" citations name verified sections of `docs/DATP Core Architecture.md` (abbreviated **Arch**) and `docs/Journal_Extension_Master_Roadmap.md` (abbreviated **Road**); no section number is invented, and no reference to a numbered section of this backlog is used where this backlog is organized by letter (A–M) — cross-references to this document cite the lettered section (for example "Section E") instead. Bodies below are ordered Phase 0, then Phase 1 through Phase 7, and numerically within each phase; the Phase 0 tickets below are fully reconstructed in this revision, and Phases 1–7 remain in their prior form pending their own reconstruction stage (see the front-matter reconstruction-status note and Section M).

### Phase 0 — Repository and Engineering Foundation

#### P0-T001 — Audit and record repository starting state

- **Ticket ID.** P0-T001
- **Title.** Audit and record repository starting state
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** architecture-cleaner
- **Supporting agents.** roadmap-orchestrator
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (read-only discovery; no type is implemented by this ticket).
- **Objective.** Produce a factual, read-only record of the actual current repository: empty `src/` and `tests/`, absent `configs/`, the current `pyproject.toml` (Python 3.11, three runtime deps, Pyright basic), the existing `ai/` governance catalogue and its provider adapters, and the tracked/gitignored roots.
- **Why this ticket exists.** Every later foundation ticket assumes a known starting point; an unverified assumption about what already exists (for example that a package skeleton or `configs/` exists) would cause silent duplication or overwrite. It is a discrete discovery responsibility with no code change, kept separate from any ticket that changes files.
- **Authority references.** Arch §5.2 (repository tree), §5.3 (structure rules); Road — (no scientific content in this ticket).
- **Dependencies.** —
- **Blocks.** P0-T002.
- **Downstream consumers.** P0-T002 through P0-T026 all assume the facts recorded by this ticket; none may assume an undocumented starting state.
- **Preconditions.** Repository accessible; `docs/Journal_Extension_Master_Roadmap.md` and `docs/DATP Core Architecture.md` present.
- **Inputs.** The working tree, git status, `pyproject.toml`, and the `ai/` catalogue.
- **Allowed scope.** Read-only inspection of the working tree, tracked files, and `ai/`. Recording the finding into this master log's changelog (Section L) only.
- **Forbidden actions.** No source/config/tooling creation; no edits to `ai/`; no backward-compatibility scaffolding; no scratch or audit files; no claiming this ticket `DONE` while its own status field still reads `NOT_STARTED`.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Enumerate tracked roots and their git status; confirm `src/datp_core` does not yet exist; confirm `tests/` and `configs/` state; capture the exact `pyproject.toml` deviations from Arch §4 (Python version, missing pinned libraries, typing mode); inventory `ai/` agents/skills/hooks/contracts/workflows and provider adapter folders.
- **Required unit tests.** NONE (discovery ticket; no enum-existence or file-existence test is created for a fact-finding record).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Directory listing; `git status`; dependency inspection — all read-only.
- **Acceptance criteria.** [ ] Starting-state finding recorded in the changelog (Section L). [ ] Deviations of `pyproject.toml` from Arch §4 enumerated. [ ] `ai/` catalogue inventory recorded. [ ] No file other than this master log changed.
- **Completion evidence.** Changed files (this log only); commands run (read-only listings); recorded finding text; cleanup confirmation (no artifact left besides the changelog entry); confirmation that no unrelated file changed.
- **Failure and blocker behavior.** If the working tree is dirty at audit time, record the dirty state as a finding rather than cleaning it; if `ai/` conflicts irreconcilably with Arch §3.1 (provider-agnostic catalogue), record the conflict as a blocker rather than resolving it silently.
- **Stop conditions.** Stop and raise a blocker if either authoritative document is missing.
- **Deliverables.** A changelog entry (Section L) summarizing the verified starting state.
- **Final review checklist.** [ ] No implementation file touched. [ ] Findings are factual, not aspirational. [ ] Status remains `NOT_STARTED` until the finding is recorded and reviewed.

#### P0-T002 — Establish the Python 3.12 project and build backend

- **Ticket ID.** P0-T002
- **Title.** Establish the Python 3.12 project and build backend
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (project/build metadata only; no domain contract).
- **Objective.** Reconfigure `pyproject.toml` to Python 3.12 (committed), a single build backend for `src/datp_core`, and project metadata consistent with the architecture, replacing the current 3.11 configuration outright with no compatibility with the prior configuration.
- **Why this ticket exists.** Arch §4 commits to Python 3.12 language features (PEP 695, `StrEnum`, `match`, slotted kw-only dataclasses). The current `requires-python >=3.11` and `target-version py311` would silently permit incompatible assumptions. Project/runtime setup is kept distinct from linting, typing, and dependency-group design, which are separate tickets.
- **Authority references.** Arch §4 (Python 3.12 committed), §5.2 (repository tree), §24 (naming); AGENTS.md (no-backward-compatibility policy).
- **Dependencies.** P0-T001.
- **Blocks.** P0-T003, P0-T005, P0-T007, P0-T008, P0-T009.
- **Downstream consumers.** Every Phase 0 tooling ticket (P0-T003–P0-T015) and the baseline gate P0-T026 assume the 3.12 project/build configuration established here.
- **Preconditions.** P0-T001 complete.
- **Inputs.** The current `pyproject.toml`.
- **Allowed scope.** `pyproject.toml` project table, build-system table, `python-version` pin.
- **Forbidden actions.** No dependency-group content change here (that is P0-T003); no source modules; no legacy 3.11 fallbacks, shims, or dual-version claims; no release/tag/version work.
- **Required configuration or NONE.** Project table and build-system table only; no scientific configuration.
- **Implementation responsibilities.** Set `requires-python == 3.12`; set the build backend and wheel target for `src/datp_core`; align project name/description with the architecture; remove the 3.11 target markers so later tickets can set 3.12 tool targets.
- **Required unit tests.** NONE (static configuration).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A single import-time smoke that the interpreter is 3.12 and the empty package builds (owned by P0-T014's Nox baseline, not authored here).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Build/metadata resolution of the empty package; interpreter-version check.
- **Acceptance criteria.** [ ] `requires-python` is 3.12. [ ] Build backend targets `src/datp_core`. [ ] No 3.11 marker remains. [ ] No legacy alias/shim introduced.
- **Completion evidence.** Changed files (`pyproject.toml`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If a required dependency in Arch §4 is unavailable on 3.12 in this environment, record it as a blocker rather than downgrading Python.
- **Stop conditions.** Stop if 3.12 cannot be adopted without violating a hard environment constraint; record the blocker instead of compromising.
- **Deliverables.** Updated `pyproject.toml` project/build sections.
- **Final review checklist.** [ ] Single build backend. [ ] No dual-version compatibility language.

#### P0-T003 — Define dependency groups and pin scientific libraries

- **Ticket ID.** P0-T003
- **Title.** Define dependency groups and pin scientific libraries
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** reproducibility-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (dependency configuration only).
- **Objective.** Declare the exact accepted-library set of Arch §4.1 across purpose-scoped dependency groups, pinning the numerically/order-sensitive libraries (scikit-learn, PyArrow, NumPy, SciPy, blake3, msgspec, PyTorch, Flower) and the tooling set, and explicitly excluding the rejected libraries of Arch §4.2.
- **Why this ticket exists.** The current `pyproject.toml` lacks Pydantic, PyArrow, blake3, msgspec, Flower, scikit-learn, SciPy, structlog, filelock, Hypothesis, import-linter, pytest-archon, syrupy, Nox, Typer, rich, and pynvml/psutil. Reproducibility (Arch §9.5 `EnvironmentInventory`) requires exact pins for the numerically sensitive libraries; this is kept separate from lock-file discipline (P0-T004).
- **Authority references.** Arch §4.1 (accepted libraries and layer confinement), §4.2 (rejected), §9.5 (pinned exact versions of scikit-learn/PyArrow/NumPy/SciPy/blake3/msgspec).
- **Dependencies.** P0-T002.
- **Blocks.** P0-T004, P0-T026.
- **Downstream consumers.** Every Phase 1 infrastructure ticket that constructs a framework adapter assumes the dependency groups declared here; consumption is gated transitively through the baseline gate P0-T026 → P1-T001, never listed as a direct dependency of an individual Phase 1 ticket.
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §4.1/§4.2 accepted/rejected library tables.
- **Allowed scope.** `pyproject.toml` dependency groups (runtime, dev/tooling, optional).
- **Forbidden actions.** No Hydra/OmegaConf/MLflow-hard/Ray/Dask/Celery/ORM/DAG-engine/DI-framework (Arch §4.2); no unpinned numerically sensitive library; no `torch.compile` enablement; no source code.
- **Required configuration or NONE.** Dependency-group tables only.
- **Implementation responsibilities.** Group runtime scientific libraries; group tooling (Ruff, Pyright, pytest, pytest-cov, Hypothesis, pytest-xdist, pytest-timeout, pytest-randomly, import-linter, pytest-archon, syrupy, Nox); add optional groups (Typer, rich, psutil, pynvml); pin the numerically/order-sensitive libraries to exact versions; confine each library's intended layer in a comment referencing Arch §4.1.
- **Required unit tests.** NONE (dependency-group declaration; no enum/spelling test).
- **Required property tests.** NONE.
- **Required contract tests.** An environment-inventory contract test asserting the pinned versions match `EnvironmentInventory` (owned by the Phase 1 telemetry/provenance ticket, not authored here).
- **Required architecture tests.** NONE.
- **Required integration tests.** Dependency resolution of every group succeeds; rejected libraries are verifiably absent.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Dependency resolution of all groups; verification that rejected libraries are absent.
- **Acceptance criteria.** [ ] Every Arch §4.1 accepted library present in a purpose-scoped group. [ ] Numerically sensitive libraries pinned exactly. [ ] No Arch §4.2 rejected library present. [ ] Optional libraries marked optional.
- **Completion evidence.** Changed files (`pyproject.toml`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If an exact pin required by Arch §9.5 cannot be resolved for 3.12, record a blocker rather than substituting an unpinned or approximate version.
- **Stop conditions.** Stop on any unresolvable exact-pin requirement.
- **Deliverables.** Dependency-group configuration.
- **Final review checklist.** [ ] Layer-confinement comments cite Arch §4.1. [ ] No rejected dependency.

#### P0-T004 — Establish dependency-lock discipline

- **Ticket ID.** P0-T004
- **Title.** Establish dependency-lock discipline
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** reproducibility-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `DependencyLockState` (Arch §9.5) — field mapping documented here; the type itself is implemented in Phase 1.
- **Objective.** Establish a deterministic, committed dependency lock so `DependencyLockState` is reproducible and can be frozen at campaign time, with a documented rule for regenerating it.
- **Why this ticket exists.** Campaign freezes (P3-T002, P5-T008) and Phase 7 provenance audits require an exact, committed lock. Lock generation and its update rule are a distinct governance responsibility from dependency-group design (P0-T003).
- **Authority references.** Arch §9.5 (`DependencyLockState`, `EnvironmentInventory` pinned versions), §22.5 (provenance).
- **Dependencies.** P0-T003.
- **Blocks.** P3-T002, P5-T008, P0-T026.
- **Downstream consumers.** P3-T002 (anchor provenance freeze), P5-T008 (journal provenance freeze), P7-T001 (immutable-result/hash verification).
- **Preconditions.** P0-T003 complete.
- **Inputs.** The resolved dependency groups from P0-T003.
- **Allowed scope.** Lockfile and its regeneration rule; documentation of the rule in the governance catalogue.
- **Forbidden actions.** No hand-editing of pinned versions; no unlocked scientific dependency; no legacy lock retention.
- **Required configuration or NONE.** None beyond lock metadata.
- **Implementation responsibilities.** Commit the resolved lock; document how it is regenerated deterministically; define which lock fields feed `DependencyLockState` and how a campaign freeze snapshots it.
- **Required unit tests.** NONE here (a provenance contract test lives in Phase 1/Phase 7).
- **Required property tests.** NONE.
- **Required contract tests.** A drift check comparing the committed lock to the resolved environment (owned by the Phase 1/7 provenance ticket).
- **Required architecture tests.** NONE.
- **Required integration tests.** Lock resolution is reproducible on a clean checkout.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Lock resolution reproducibility; clean/dirty lock detection.
- **Acceptance criteria.** [ ] A committed lock exists and resolves deterministically. [ ] The regeneration rule is documented. [ ] The `DependencyLockState` field mapping is stated.
- **Completion evidence.** Changed files (lockfile, governance note); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A drift between the committed lock and the resolved environment is surfaced as a provenance finding, never silently accepted.
- **Stop conditions.** Stop if the lock cannot be resolved deterministically in this environment.
- **Deliverables.** Committed lock; regeneration rule note in the governance catalogue.
- **Final review checklist.** [ ] Lock is deterministic. [ ] No manual version edits.

#### P0-T005 — Create the approved layered source skeleton

- **Ticket ID.** P0-T005
- **Title.** Create the approved layered source skeleton
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** architecture
- **Owner.** architecture-cleaner
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (empty package directories only; no type is defined by this ticket).
- **Objective.** Create the empty `src/datp_core/{domain,application,config,analysis,infrastructure,composition,cli}` package tree exactly as Arch §5.1 prescribes, with cohesive capability subpackages and no forbidden generic module names, and no behavior yet.
- **Why this ticket exists.** The seven-layer dependency model (Arch §3) can be enforced only once the layer packages exist; import-linter contracts (P0-T011) bind to these package names. This is kept separate from behavior implementation (Phase 1) and from enforcement configuration (P0-T011/P0-T012).
- **Authority references.** Arch §3.1 (layers), §5.1 (source-package tree), §5.3 (structure rules), §24 (naming), §29.2 (no root `experiments/` package).
- **Dependencies.** P0-T002.
- **Blocks.** P0-T011, P0-T026.
- **Downstream consumers.** Every Phase 1 domain/application/config/analysis/infrastructure/composition/cli ticket writes into a package created here; consumption is gated transitively through P0-T026 → P1-T001.
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §5.1 source-package tree.
- **Allowed scope.** Package directories and minimal side-effect-free `__init__` files with explicit `__all__` placeholders; capability subpackage folders named per Arch §5.1.
- **Forbidden actions.** No `utils`/`helpers`/`common`/`misc`/`base`/`manager`/`handler`/`processor`/`context`/`payload`/`shared` modules; no root `experiments/` package; no behavior; no import side effects; no speculative modules for deferred/out-of-scope work.
- **Required configuration or NONE.** NONE (source layout only).
- **Implementation responsibilities.** Create `domain/{data,learning,thresholding,evaluation,experiments,artifacts,runtime,mathematics}`, `application/{planning,stages,runtime,reporting,ports}`, `config/{schemas,mapping}`, `analysis/{tables,figures}`, `infrastructure/{data,learning,scoring,thresholding,evaluation,statistics,persistence,runtime,reporting,telemetry}`, `composition`, `cli/commands`; keep every `__init__` side-effect-free.
- **Required unit tests.** NONE (the no-forbidden-name and no-side-effect architecture tests are authored in Phase 1 and bound to this tree).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Import of every package produces no side effect (scaffolding-level smoke only; the full suite is Phase 1).
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Import of every package with no side effect; forbidden-name scan; absence of a root `experiments/` package.
- **Acceptance criteria.** [ ] Every Arch §5.1 layer and capability subpackage exists. [ ] No forbidden generic module name. [ ] No root `experiments/` package. [ ] All `__init__` files side-effect-free.
- **Completion evidence.** Changed files (empty package tree); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If a module's ownership in Arch §5.1 is ambiguous (two plausible homes), record a placement blocker per Arch §3.6 rather than guessing.
- **Stop conditions.** Stop on any unresolved placement ambiguity.
- **Deliverables.** Empty layered source tree.
- **Final review checklist.** [ ] Layout matches Arch §5.1. [ ] No behavior added.

#### P0-T006 — Establish repository root layout and tracked/generated/gitignored policy

- **Ticket ID.** P0-T006
- **Title.** Establish repository root layout and tracked/generated/gitignored policy
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** architecture-cleaner
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `StorageRootKind`, `StorageVisibility`, `ArtifactNamespace` (Arch §6.4, §15.1) — root-layout binding documented here; the enums themselves are implemented in Phase 1.
- **Objective.** Create the repository root layout of Arch §5.2 — `configs/`, `data/{raw,manifests}`, `checkpoints/`, `outputs/{anchor,journal}`, `results/{tables,figures,exports}`, `.runtime/{recovery,run_state,cache,locks,staging}`, `tests/`, `docs/decisions/` — and the tracked/generated/gitignored policy, with anchor/journal output namespaces structurally separated.
- **Why this ticket exists.** Storage roots (Arch §15) bind to these directories; the anchor/journal namespace separation prevents overwrite (Arch §15.2). This is kept separate from the source skeleton (P0-T005) and from path-resolution implementation (Phase 1).
- **Authority references.** Arch §5.2 (repository tree, tracked vs generated), §15.1 (semantic roots), §15.2 (namespace branches).
- **Dependencies.** P0-T002.
- **Blocks.** P1-T054, P0-T026.
- **Downstream consumers.** P1-T054 (semantic storage-root binding and path resolution) and every ticket that persists an anchor or journal artifact assume this root layout.
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §5.2/§15.1/§15.2.
- **Allowed scope.** Root directory scaffolding, `.gitignore` policy, `configs/` group folders (`protocols`, `experiments`, `execution`, `artifacts`, `reporting`, `tests`), `data/manifests` tracked, `docs/decisions/`.
- **Forbidden actions.** No `__init__.py` under `configs/`; no executable code under `configs/`; no committing of `data/raw`, `checkpoints`, `outputs`, `.runtime`; no merging anchor and journal output branches.
- **Required configuration or NONE.** `configs/` group folders exist as empty external-data directories only.
- **Implementation responsibilities.** Create the roots and their visibility policy; set `.gitignore` for generated/ephemeral roots; keep `results/` tracked/append-only; keep `data/manifests/` tracked; separate `outputs/anchor` and `outputs/journal`.
- **Required unit tests.** NONE (layout only).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE (storage-boundary tests are authored in Phase 1).
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Gitignore verification for generated roots; confirmation `configs/` carries no executable code.
- **Acceptance criteria.** [ ] All Arch §5.2 roots exist with correct tracked/generated status. [ ] Anchor and journal output roots are separate. [ ] `configs/` has no `__init__.py` or code. [ ] `results/` is tracked/append-only.
- **Completion evidence.** Changed files (root layout, `.gitignore`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If a root's visibility class is ambiguous under Arch §15.1, record a blocker rather than guessing.
- **Stop conditions.** Stop on any unresolved visibility-class ambiguity.
- **Deliverables.** Root layout and gitignore policy.
- **Final review checklist.** [ ] No scientific output root committed. [ ] Namespace branches separate.

#### P0-T007 — Configure Ruff lint and format

- **Ticket ID.** P0-T007
- **Title.** Configure Ruff lint and format
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** naming-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Configure Ruff for lint and format targeting Python 3.12, with import hygiene and style rules that support the architecture's naming and no-`import *` rules.
- **Why this ticket exists.** Style/import hygiene is a distinct tooling responsibility feeding the baseline gate; the current config targets py311.
- **Authority references.** Arch §4.1 (Ruff role), §24 (naming/imports), §5.3.
- **Dependencies.** P0-T002.
- **Blocks.** P0-T026.
- **Downstream consumers.** P0-T014 (Nox lint session), P0-T023 (structure/naming hook binding).
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §5.3/§24 naming and cohesion rules.
- **Allowed scope.** Ruff configuration in `pyproject.toml`.
- **Forbidden actions.** No suppression of the forbidden-name or import rules; no py311 target.
- **Required configuration or NONE.** Ruff table only.
- **Implementation responsibilities.** Set target py312; enable import sorting and relevant lint rule families; forbid `import *`; align line-length with Arch §5.3 soft-cap guidance (not a hard splitter).
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Ruff runs clean on the empty skeleton.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Lint and format check on `src/` and `tests/`.
- **Acceptance criteria.** [ ] Ruff targets 3.12. [ ] Import hygiene enforced. [ ] Runs clean on skeleton.
- **Completion evidence.** Changed files (`pyproject.toml` Ruff table); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected; a genuine tool-version incompatibility is recorded as a blocker.
- **Stop conditions.** None expected.
- **Deliverables.** Ruff configuration.
- **Final review checklist.** [ ] No rule silently disabled.

#### P0-T008 — Configure Pyright strict typing

- **Ticket ID.** P0-T008
- **Title.** Configure Pyright strict typing
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Configure Pyright in strict mode for Python 3.12 with no untyped public surface, so exhaustiveness (`assert_never`) and identity typing can be statically enforced.
- **Why this ticket exists.** The current config is `basic`; the architecture requires strict typing to make forgotten enum branches and framework leakage compile errors (Arch §6.10, §18, §29.2). This is a distinct tooling responsibility from lint/format (P0-T007).
- **Authority references.** Arch §4.1 (Pyright strict), §6.10 (exhaustiveness), §29.2 (Pyright strict enforces type consistency).
- **Dependencies.** P0-T002.
- **Blocks.** P0-T026.
- **Downstream consumers.** P0-T014 (Nox strict-type session), P0-T023 (typing hook binding), every Phase 1 ticket authoring a closed union.
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §4.1/§6.10.
- **Allowed scope.** Pyright configuration.
- **Forbidden actions.** No `basic` mode; no broad `Any`; no untyped public surface allowance.
- **Required configuration or NONE.** Pyright table only.
- **Implementation responsibilities.** Set strict mode, py312, include `src/` and `tests/`; forbid implicit `Any` on public surfaces.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Pyright strict passes on the empty typed skeleton.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type check on `src/` and `tests/`.
- **Acceptance criteria.** [ ] Strict mode enabled. [ ] py312 target. [ ] Passes on skeleton.
- **Completion evidence.** Changed files (`pyproject.toml` Pyright table); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None expected.
- **Deliverables.** Pyright configuration.
- **Final review checklist.** [ ] Strict, no `basic` remnant.

#### P0-T009 — Configure pytest, coverage, timeout, and order-randomization

- **Ticket ID.** P0-T009
- **Title.** Configure pytest, coverage, timeout, and order-randomization
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `TestSuiteKind` (Arch §6.7) — marker registration documented here; the enum itself is implemented in Phase 1 test support.
- **Objective.** Configure pytest with coverage (pytest-cov), per-test timeouts (pytest-timeout), and order randomization (pytest-randomly, disabled for the CUDA lane), plus marker registration for the test suites of Arch §21.2.
- **Why this ticket exists.** Test infrastructure discipline (timeouts, order independence, coverage gates) is a distinct responsibility from the CUDA lane (P0-T015) and property config (P0-T010).
- **Authority references.** Arch §4.1 (pytest/pytest-cov/pytest-timeout/pytest-randomly), §21 (test architecture), §21.3 (config ownership: `pyproject.toml` holds markers only).
- **Dependencies.** P0-T002.
- **Blocks.** P0-T010, P0-T026.
- **Downstream consumers.** P0-T010 (Hypothesis profiles), P0-T012 (pytest-archon scaffold), P0-T013 (syrupy scaffold), P0-T014 (Nox sessions), P0-T015 (CUDA/xdist lanes).
- **Preconditions.** P0-T002 complete.
- **Inputs.** Arch §21.2 test-suite table.
- **Allowed scope.** pytest tables and marker registration in `pyproject.toml`.
- **Forbidden actions.** No test-profile fields in `pyproject.toml` (those live in `configs/tests/`); no order-dependence exemption except the serialized CUDA lane.
- **Required configuration or NONE.** Marker registration only; profile data belongs to `configs/tests/` (Phase 1 test support).
- **Implementation responsibilities.** Register markers aligned to `TestSuiteKind`; set coverage policy and per-profile timeout hooks; enable randomization by default; document that the CUDA lane disables randomization.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A trivial passing collection on the empty tree; order-independence verified once suites exist in Phase 1.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Test collection; coverage report on skeleton.
- **Acceptance criteria.** [ ] Markers registered per `TestSuiteKind`. [ ] Timeout and randomization enabled. [ ] Coverage configured. [ ] No profile data in `pyproject.toml`.
- **Completion evidence.** Changed files (`pyproject.toml` pytest tables); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A timeout violation fails the session (`TestProfileValidationError` path, defined in Phase 1).
- **Stop conditions.** None expected.
- **Deliverables.** pytest configuration.
- **Final review checklist.** [ ] Order-independence default on.

#### P0-T010 — Configure Hypothesis property-testing profiles

- **Ticket ID.** P0-T010
- **Title.** Configure Hypothesis property-testing profiles
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Configure Hypothesis with bounded, deterministic profiles (bounded example counts, deadlines, seeds) for value-object range/finiteness and locked pure-function properties.
- **Why this ticket exists.** Property testing has distinct determinism/timeout constraints (Arch §21.2 bounded property tests) that are separate from unit-test configuration.
- **Authority references.** Arch §4.1 (Hypothesis), §21.2 (property tests bounded by timeout/memory), §7 (value objects), §7.3 (non-finite rejection).
- **Dependencies.** P0-T009.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every Phase 1 property test for a value object or locked pure function (e.g., `cv_fpr`, `pooled_variance`, `cliffs_delta`).
- **Preconditions.** P0-T009 complete.
- **Inputs.** Arch §7/§7.3/§21.2.
- **Allowed scope.** Hypothesis profile registration.
- **Forbidden actions.** No unbounded example generation; no order-dependent stateful test without deterministic seeding.
- **Required configuration or NONE.** Hypothesis settings profiles (code-side registration under `tests/support/`).
- **Implementation responsibilities.** Register CI/dev profiles with bounded examples and deadlines; ensure a deterministic derandomization option for the CUDA/serial lanes.
- **Required unit tests.** NONE.
- **Required property tests.** A trivial property runs within the profile's bounded example count and deadline (self-check of the profile itself).
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Property lane collection succeeds on the empty tree.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property lane collection and a bounded sample run.
- **Acceptance criteria.** [ ] Bounded, deterministic profiles registered. [ ] Deadlines set. [ ] Runs within budget on skeleton.
- **Completion evidence.** Changed files (Hypothesis profile registration); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A deadline exceed fails the property test rather than being silently extended.
- **Stop conditions.** None.
- **Deliverables.** Hypothesis profile registration.
- **Final review checklist.** [ ] Bounded and deterministic.

#### P0-T011 — Configure import-linter layer contracts

- **Ticket ID.** P0-T011
- **Title.** Configure import-linter layer contracts
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** architecture
- **Owner.** architecture-cleaner
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (static contract configuration only).
- **Objective.** Encode the Arch §3.2 forbidden-dependency contracts in `importlinter.ini`: `domain`→stdlib/domain only; `application`→`domain` only (no `config`/`infrastructure`/`analysis`/`cli`/frameworks); `config`→`domain` only; `analysis`→`domain` only (framework-free science); `infrastructure`→`application`/`domain` (+`analysis` for rendering); `composition`→all layers (no direct framework); `cli`→`composition` only.
- **Why this ticket exists.** Static boundary enforcement is the backbone of the layered design and must exist before behavior. Distinct from the in-test pytest-archon assertions (P0-T012).
- **Authority references.** Arch §3.1–§3.3 (layers/forbidden directions/diagram), §29.2.
- **Dependencies.** P0-T005.
- **Blocks.** P0-T026, P1-T050.
- **Downstream consumers.** P1-T050 (full architecture test suite), every Phase 1 layer implementation.
- **Preconditions.** P0-T005 complete (packages exist).
- **Inputs.** Arch §3.3 layer dependency diagram.
- **Allowed scope.** `importlinter.ini` contracts.
- **Forbidden actions.** No carve-out for a root `experiments/` package; no framework import allowed into `domain`/`application`/`config`/`analysis`-science; no relaxation to accommodate convenience.
- **Required configuration or NONE.** Contract definitions only.
- **Implementation responsibilities.** Author layer/independence/forbidden contracts matching every edge and absent edge of the Arch §3.3 diagram; forbid PyTorch/Flower/scikit-learn/SciPy/pandas/NumPy/Pydantic in the wrong layers.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** Contracts load and pass on the empty skeleton (exhaustiveness against the §3.3 diagram).
- **Required architecture tests.** NONE beyond the contract load itself (the full suite is P1-T050).
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** `import-linter` run.
- **Acceptance criteria.** [ ] Every Arch §3.2 forbidden direction encoded. [ ] Framework confinement encoded. [ ] Passes on skeleton. [ ] No root `experiments/` carve-out.
- **Completion evidence.** Changed files (`importlinter.ini`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If a layer package is missing, stop and return to P0-T005 rather than authoring a contract against a nonexistent package.
- **Stop conditions.** Stop if a layer package is missing.
- **Deliverables.** `importlinter.ini`.
- **Final review checklist.** [ ] Matches the §3.3 diagram exactly.

#### P0-T012 — Configure pytest-archon in-test boundary assertions

- **Ticket ID.** P0-T012
- **Title.** Configure pytest-archon in-test boundary assertions
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** architecture
- **Owner.** architecture-cleaner
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Establish the pytest-archon in-test boundary-assertion scaffold under `tests/architecture/` so boundary failures produce clear diffs alongside import-linter.
- **Why this ticket exists.** Arch §3.3/§4.1 require both static (import-linter) and in-test (pytest-archon) enforcement for clearer failure diffs. Distinct tool from P0-T011.
- **Authority references.** Arch §4.1 (pytest-archon), §3.3 (backed by pytest-archon in-test assertions), §21.2 (architecture tests).
- **Dependencies.** P0-T005, P0-T009.
- **Blocks.** P1-T050, P0-T026.
- **Downstream consumers.** P1-T050 (complete architecture test suite).
- **Preconditions.** P0-T005, P0-T009 complete.
- **Inputs.** Arch §3.3/§21.2.
- **Allowed scope.** `tests/architecture/` scaffold and pytest-archon wiring (full assertions authored in Phase 1).
- **Forbidden actions.** No production import of test modules; no duplication of import-linter as the sole check.
- **Required configuration or NONE.** None beyond test wiring.
- **Implementation responsibilities.** Create the architecture-test package and a minimal boundary assertion proving the harness works on the skeleton; leave complete assertions to Phase 1.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** A minimal pytest-archon assertion passes on the skeleton.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Architecture-lane run.
- **Acceptance criteria.** [ ] pytest-archon harness runs. [ ] Minimal boundary assertion passes. [ ] `tests/architecture/` scaffold present.
- **Completion evidence.** Changed files (`tests/architecture/` scaffold); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A boundary breach fails the test rather than being suppressed.
- **Stop conditions.** None.
- **Deliverables.** Architecture-test scaffold.
- **Final review checklist.** [ ] Complements, not replaces, import-linter.

#### P0-T013 — Configure syrupy golden-snapshot support

- **Ticket ID.** P0-T013
- **Title.** Configure syrupy golden-snapshot support
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Establish syrupy snapshot support under `tests/golden/` for `ExperimentManifest`/`ProvenanceRecord` shapes and the fixed B4 assignment/adjusted-Rand evidence, catching silent manifest-shape drift.
- **Why this ticket exists.** Golden shape regression is a distinct concern used only for meaningful manifest/provenance/B4 shapes (Arch §4.1, §21.2), separate from unit/property configuration.
- **Authority references.** Arch §4.1 (syrupy), §16.2 (B4 golden equivalence), §21.2 (`tests/golden/`).
- **Dependencies.** P0-T009.
- **Blocks.** P0-T026.
- **Downstream consumers.** Phase 1 provenance/manifest tickets and Phase 2 B4 clustering tickets that require golden coverage.
- **Preconditions.** P0-T009 complete.
- **Inputs.** Arch §4.1/§16.2/§21.2.
- **Allowed scope.** `tests/golden/` scaffold and syrupy configuration; snapshots authored later where shapes exist.
- **Forbidden actions.** No golden snapshot of a scientific value that belongs in an artifact; no snapshot of raw floats used as identity.
- **Required configuration or NONE.** Snapshot directory policy (recoverable evidence, not scientific output).
- **Implementation responsibilities.** Wire syrupy; document that golden snapshots cover manifest/provenance/B4 shapes only.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A trivial snapshot round-trips.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Golden-lane run.
- **Acceptance criteria.** [ ] syrupy wired under `tests/golden/`. [ ] Scope documented (manifest/provenance/B4 shapes). [ ] Trivial snapshot passes.
- **Completion evidence.** Changed files (`tests/golden/` scaffold); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A snapshot mismatch fails the golden lane.
- **Stop conditions.** None.
- **Deliverables.** Golden-snapshot scaffold.
- **Final review checklist.** [ ] No scientific value snapshotted as identity.

#### P0-T014 — Establish Nox validation sessions

- **Ticket ID.** P0-T014
- **Title.** Establish Nox validation sessions
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Author `noxfile.py` with the named validation sessions of Arch §21.2 (`cuda`, `serial`, `resource_intensive`, `xdist_safe`, `synthetic`, `scientific_smoke`) plus format/lint/type/architecture sessions, with no logic beyond session wiring.
- **Why this ticket exists.** Session orchestration composes the tool tickets into runnable lanes and is the substrate for the baseline gate; distinct from individual tool configuration.
- **Authority references.** Arch §4.1 (Nox owns sessions), §21.2 (named sessions), §21.3.
- **Dependencies.** P0-T007, P0-T008, P0-T009.
- **Blocks.** P0-T015, P0-T026.
- **Downstream consumers.** P0-T015 (CUDA/xdist lane policy binds to these sessions), P0-T025 (impacted-test/order-independence gate), every subsequent phase's validation commands.
- **Preconditions.** P0-T007, P0-T008, P0-T009 complete.
- **Inputs.** Arch §21.2 named-session table.
- **Allowed scope.** `noxfile.py`.
- **Forbidden actions.** No business logic in sessions; no session that writes to a scientific output root; no CUDA lane under xdist.
- **Required configuration or NONE.** None beyond session wiring.
- **Implementation responsibilities.** Define sessions for lint, format, strict-type, architecture, `xdist_safe`, `serial`, `cuda` (serialized), `synthetic`, `scientific_smoke`, `resource_intensive`; wire impacted-test and full-suite composition.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Every session runs on the empty skeleton.
- **Required CUDA tests.** The `cuda` session is present and serialized (no CUDA execution required yet; the session wiring itself is validated).
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Each Nox session on the skeleton.
- **Acceptance criteria.** [ ] All Arch §21.2 sessions present. [ ] CUDA lane serialized. [ ] Sessions run on skeleton. [ ] No logic beyond wiring.
- **Completion evidence.** Changed files (`noxfile.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A failing session returns non-zero; no silent pass.
- **Stop conditions.** None.
- **Deliverables.** `noxfile.py`.
- **Final review checklist.** [ ] Session-only, no logic.

#### P0-T015 — Establish the serialized CUDA lane and CPU xdist policy

- **Ticket ID.** P0-T015
- **Title.** Establish the serialized CUDA lane and CPU xdist policy
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** implementation-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `TestParallelismMode`, `TestDeviceRequirement` (Arch §6.7) — lane-policy binding documented here; the enums themselves are implemented in Phase 1 test support.
- **Objective.** Lock the policy that CUDA-tagged tests run serialized on one worker (`SERIAL_CUDA_LANE`) with randomization disabled, and CPU-safe suites run under xdist (`XDIST_SAFE`), so no two CUDA tests share a GPU.
- **Why this ticket exists.** Concurrent CUDA tests on one GPU are explicitly rejected (Arch §23, §21.3); this is a distinct policy from Nox session wiring (P0-T014).
- **Authority references.** Arch §21.3, §16.4 (parallelism), §21.2 (`tests/integration/cuda/` serialized).
- **Dependencies.** P0-T014.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every Phase 1/2 CUDA integration test.
- **Preconditions.** P0-T014 complete.
- **Inputs.** Arch §16.4/§21.2/§21.3.
- **Allowed scope.** CUDA/xdist lane policy in Nox and test support.
- **Forbidden actions.** No concurrent CUDA on one GPU; no xdist on the CUDA lane; no test writing to a scientific output root.
- **Required configuration or NONE.** Lane mapping to `TestParallelismMode`.
- **Implementation responsibilities.** Configure the serialized CUDA lane; configure xdist for CPU-safe suites; document skip/serialize policy for `TestDeviceRequirement`.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A no-op CUDA-tagged test serializes; a CPU test runs under xdist.
- **Required CUDA tests.** The serialized lane runs a no-op CUDA-tagged test without concurrency (CUDA hardware itself is not required to validate the lane's serialization policy on CPU-only CI, but the policy wiring is verified).
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** CUDA lane and xdist lane runs.
- **Acceptance criteria.** [ ] CUDA lane serialized, randomization off. [ ] CPU suites under xdist. [ ] No concurrent GPU test.
- **Completion evidence.** Changed files (lane policy configuration); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A CUDA test that cannot serialize fails rather than running concurrently.
- **Stop conditions.** None.
- **Deliverables.** CUDA/xdist lane policy.
- **Final review checklist.** [ ] One CUDA test per GPU at a time.

#### P0-T016 — Audit and consolidate the canonical provider-agnostic AI catalogue

- **Ticket ID.** P0-T016
- **Title.** Audit and consolidate the canonical provider-agnostic AI catalogue
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** agent-governance
- **Owner.** roadmap-orchestrator
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Confirm `ai/` is the single provider-agnostic source of truth and that `.github/`, `.claude/`, `.agents/`, `.codex/` are thin adapters pointing back to `AGENTS.md` and `ai/`, duplicating no full governance content; record and close any duplication found.
- **Why this ticket exists.** `AGENTS.md`'s Native Adapter Policy requires a provider-agnostic canonical catalogue with provider folders as thin adapters only; the repository already has `ai/` plus four provider folders that must not become a second source of truth. Distinct from completing the individual catalogues (P0-T017–P0-T021).
- **Authority references.** `AGENTS.md` (Native Adapter Policy); `ai/README.md`.
- **Dependencies.** P0-T001.
- **Blocks.** P0-T017, P0-T018, P0-T019, P0-T020, P0-T021.
- **Downstream consumers.** P0-T017 through P0-T021 (each catalogue), transitively P0-T026.
- **Preconditions.** P0-T001 complete.
- **Inputs.** `ai/README.md`, provider adapter folders (`.github/`, `.claude/`, `.agents/`, `.codex/`).
- **Allowed scope.** `ai/README.md`, adapter pointer files under provider folders.
- **Forbidden actions.** No duplication of full agent/skill/hook/contract/workflow/command definitions into provider folders; no second source of truth; no deletion of `ai/` content without a recorded decision.
- **Required configuration or NONE.** NONE (governance docs only).
- **Implementation responsibilities.** Verify each provider adapter references `AGENTS.md`/`ai/`; flag any adapter carrying full definitions; consolidate to thin pointers.
- **Required unit tests.** NONE (documentation governance).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A governance-lint scan verifies adapters contain pointers only.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Adapter-content scan for duplication.
- **Acceptance criteria.** [ ] `ai/` confirmed sole source of truth. [ ] All provider folders are thin adapters. [ ] No duplicated full definitions. [ ] Duplications (if any) resolved.
- **Completion evidence.** Changed files (adapter pointers, `ai/README.md`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If an adapter's provider requires content that conflicts with provider-agnosticism, record a design decision rather than silently duplicating.
- **Stop conditions.** Stop on an unresolved provider-agnosticism conflict.
- **Deliverables.** Consolidated adapter pointers; catalogue audit note.
- **Final review checklist.** [ ] One source of truth.

#### P0-T017 — Complete the canonical agent-role catalogue

- **Ticket ID.** P0-T017
- **Title.** Complete the canonical agent-role catalogue
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** agent-governance
- **Owner.** roadmap-orchestrator
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure the non-duplicated canonical agent catalogue covers every role required by this backlog (roadmap orchestrator, scientific-protocol guardian, architecture guardian, implementation engineer, configuration engineer, data-pipeline engineer, federated-learning engineer, threshold-policy engineer, experiment engineer, statistics auditor, artifact-lineage auditor, reproducibility auditor, structure auditor, naming auditor, dependency auditor, claim/evidence auditor, literature/novelty auditor, reviewer-style red-team auditor, report-output auditor), each with responsibility, allowed/forbidden scope, required inputs, expected outputs, escalation rules, and relevant hooks/commands.
- **Why this ticket exists.** Every ticket in this backlog names owner/supporting agent roles; the catalogue must exist, be complete, and be non-overlapping. Existing `ai/agents/` covers most roles; gaps (for example configuration engineer, artifact-lineage auditor, structure/dependency auditor as distinct roles) must be closed without decorative overlap.
- **Authority references.** This backlog's required-agent-role list above; `ai/agents/`; `AGENTS.md`.
- **Dependencies.** P0-T016.
- **Blocks.** P0-T024, P0-T026.
- **Downstream consumers.** Every ticket in every phase that names an owner or supporting agent role.
- **Preconditions.** P0-T016 complete.
- **Inputs.** `ai/agents/` existing files.
- **Allowed scope.** `ai/agents/` role files and provider adapter pointers.
- **Forbidden actions.** No overlapping decorative agent; no duplication into provider folders; no agent granted scientific-execution authority (execution is gated by phase, not by agent role).
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Map each required role to an existing `ai/agents/` file or add a missing one; specify responsibility/allowed/forbidden scope, inputs, outputs, escalation, hooks, and commands for each.
- **Required unit tests.** NONE (governance docs).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A catalogue-completeness cross-check against the required-role list.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Catalogue completeness cross-check.
- **Acceptance criteria.** [ ] Every required role present and non-overlapping. [ ] Each role fully specified. [ ] No provider duplication.
- **Completion evidence.** Changed files (`ai/agents/` files); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If two required roles cannot be made non-overlapping, record a design decision rather than adding a wrapper role.
- **Stop conditions.** Stop on unresolved role overlap.
- **Deliverables.** Completed agent catalogue.
- **Final review checklist.** [ ] No decorative agent.

#### P0-T018 — Complete the canonical skill catalogue

- **Ticket ID.** P0-T018
- **Title.** Complete the canonical skill catalogue
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** skill
- **Owner.** roadmap-orchestrator
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure reusable skills exist for every check this backlog relies on: task-contract creation, architecture placement, immutable domain modeling, enum/value-object/dataclass selection, raw-dictionary avoidance, hidden-default prevention, configuration mapping, dependency direction, lineage/identity design, deterministic seed handling, CUDA safety, batching/resource preflight, persistence atomicity, checkpoint/recovery separation, test selection, threshold-policy verification, metric verification, statistical verification, feasibility assessment, experiment readiness, artifact reuse, result traceability, claim discipline, and final review.
- **Why this ticket exists.** Skills are the pass/fail checks invoked by tickets and hooks; the set must be complete. Existing `ai/skills/` covers many; gaps (lineage/identity design, CUDA safety, batching/resource preflight, persistence atomicity, checkpoint/recovery separation, artifact reuse, result traceability) need adding.
- **Authority references.** This backlog's required-skill list above; `ai/skills/`.
- **Dependencies.** P0-T016.
- **Blocks.** P0-T022, P0-T026.
- **Downstream consumers.** Every hook (P0-T022–P0-T025) that invokes a skill.
- **Preconditions.** P0-T016 complete.
- **Inputs.** `ai/skills/` existing files.
- **Allowed scope.** `ai/skills/` files.
- **Forbidden actions.** No provider duplication; no skill that authorizes scientific execution.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Map each required skill to an existing file or add it; give each explicit pass/fail criteria.
- **Required unit tests.** NONE (governance docs).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A catalogue-completeness cross-check against the required-skill list.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Catalogue completeness cross-check.
- **Acceptance criteria.** [ ] Every required skill present with pass/fail criteria. [ ] No provider duplication.
- **Completion evidence.** Changed files (`ai/skills/` files); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None expected.
- **Deliverables.** Completed skill catalogue.
- **Final review checklist.** [ ] Each skill has objective criteria.

#### P0-T019 — Establish the task-contract template set

- **Ticket ID.** P0-T019
- **Title.** Establish the task-contract template set
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** agent-governance
- **Owner.** roadmap-orchestrator
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure task-contract templates (task, implementation, experiment, audit, cleanup/refactor, manuscript) exist and require a contract before any work begins, consistent with the mandatory workflow lifecycle.
- **Why this ticket exists.** `CLAUDE.md`/`AGENTS.md` require a contract from `ai/contracts/` before any task; the templates must be complete and current for the ticket workflow. Existing `ai/contracts/` covers these; this ticket verifies and completes them.
- **Authority references.** `AGENTS.md` (workflow lifecycle, contract-gate); `ai/contracts/`.
- **Dependencies.** P0-T016.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every implementation ticket in every subsequent phase, which must open a contract before work begins.
- **Preconditions.** P0-T016 complete.
- **Inputs.** `ai/contracts/` existing templates.
- **Allowed scope.** `ai/contracts/`.
- **Forbidden actions.** No provider duplication; no contract that permits scope drift or backward compatibility.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify each contract template exists and encodes intake → contract → gates → cleanup → final-report; add any missing template.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** A contract-completeness cross-check against the required template list.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Contract completeness cross-check.
- **Acceptance criteria.** [ ] All contract templates present and current. [ ] Contract-first lifecycle enforced. [ ] No provider duplication.
- **Completion evidence.** Changed files (`ai/contracts/` files); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Contract template set.
- **Final review checklist.** [ ] Contract required before work.

#### P0-T020 — Establish the workflow catalogue

- **Ticket ID.** P0-T020
- **Title.** Establish the workflow catalogue
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** workflow
- **Owner.** roadmap-orchestrator
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure workflow definitions (implementation, experiment, audit-only, cleanup/refactor, manuscript, result-audit) exist with gate order and completion rules matching the mandatory lifecycle.
- **Why this ticket exists.** Each ticket selects a workflow; the catalogue must define approved paths and gate order. Existing `ai/workflows/` covers these; this ticket verifies and completes them.
- **Authority references.** `AGENTS.md` (lifecycle); `ai/workflows/`.
- **Dependencies.** P0-T016.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every ticket in every phase selects one of these workflows.
- **Preconditions.** P0-T016 complete.
- **Inputs.** `ai/workflows/` existing files.
- **Allowed scope.** `ai/workflows/`.
- **Forbidden actions.** No provider duplication; no workflow that skips gates or permits scientific execution outside campaign phases.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify/complete each workflow's gate order and completion rules; ensure the experiment workflow forbids real runs outside Phase 3/6.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A workflow-completeness cross-check.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Workflow completeness cross-check.
- **Acceptance criteria.** [ ] All workflows present with gate order. [ ] Experiment workflow forbids non-campaign real runs. [ ] No provider duplication.
- **Completion evidence.** Changed files (`ai/workflows/` files); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Workflow catalogue.
- **Final review checklist.** [ ] Gate order explicit.

#### P0-T021 — Establish the command catalogue and provider thin adapters

- **Ticket ID.** P0-T021
- **Title.** Establish the command catalogue and provider thin adapters
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** command
- **Owner.** roadmap-orchestrator
- **Supporting agents.** —
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure the command catalogue (contract, gate, and check commands) exists canonically and that provider command adapters (for example `.claude/commands/`) are thin and point back to `ai/`.
- **Why this ticket exists.** Commands invoke gates/contracts; provider adapters must not duplicate governance. Existing `.claude/commands/` is present and must be verified thin.
- **Authority references.** `AGENTS.md` (native adapter policy); `.claude/commands/`, `.github/instructions/`.
- **Dependencies.** P0-T016.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every governance hook (P0-T022–P0-T025) invoked through a command adapter.
- **Preconditions.** P0-T016 complete.
- **Inputs.** `.claude/commands/`, `.github/instructions/`.
- **Allowed scope.** Command adapter files and canonical command references.
- **Forbidden actions.** No duplicated governance; no provider command performing scientific execution.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify each command adapter is thin and references the canonical gate/contract/check; add missing command pointers.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A command-adapter duplication scan.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Command-adapter duplication scan.
- **Acceptance criteria.** [ ] Command adapters thin and canonical. [ ] No duplication. [ ] Coverage of gates/contracts/checks.
- **Completion evidence.** Changed files (command adapter files); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Command catalogue/adapters.
- **Final review checklist.** [ ] Thin adapters only.

#### P0-T022 — Implement pre-edit and post-edit blocking hooks

- **Ticket ID.** P0-T022
- **Title.** Implement pre-edit and post-edit blocking hooks
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** hook
- **Owner.** architecture-cleaner
- **Supporting agents.** roadmap-orchestrator
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure the pre-edit and post-edit gate hooks are defined and enforce contract presence, scope limits, and post-edit checks (typing/tests/cleanup) as blocking checklist gates.
- **Why this ticket exists.** Pre/post-edit gates bracket every implementation ticket; they must exist and block. Existing `ai/hooks/pre_edit_hook.md`, `post_edit_hook.md` are present and must be verified/completed.
- **Authority references.** `AGENTS.md` (workflow lifecycle steps 3 and 5); `ai/hooks/`.
- **Dependencies.** P0-T018.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every implementation ticket in every subsequent phase.
- **Preconditions.** P0-T018 complete.
- **Inputs.** `ai/hooks/pre_edit_hook.md`, `post_edit_hook.md`.
- **Allowed scope.** `ai/hooks/pre_edit_hook.md`, `post_edit_hook.md`, provider adapter pointers.
- **Forbidden actions.** No non-blocking downgrade; no provider duplication.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify/complete the pre-edit gate (contract present, scope defined, blocker checklist) and post-edit gate (impacted tests, typing, structure, cleanup) with explicit failure behavior.
- **Required unit tests.** NONE (checklist gates).
- **Required property tests.** NONE.
- **Required contract tests.** A gate dry-run against a sample edit.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Gate dry-run against a sample edit.
- **Acceptance criteria.** [ ] Pre-edit and post-edit gates defined and blocking. [ ] Failure behavior explicit. [ ] No provider duplication.
- **Completion evidence.** Changed files (the two hook definitions); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A failed gate blocks completion rather than being bypassed.
- **Stop conditions.** None.
- **Deliverables.** Pre/post-edit hook definitions.
- **Final review checklist.** [ ] Blocking, not advisory.

#### P0-T023 — Implement structure/naming/typing/comment blocking hooks

- **Ticket ID.** P0-T023
- **Title.** Implement structure/naming/typing/comment blocking hooks
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** hook
- **Owner.** naming-auditor
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure the structure, naming, typing, and comment/docstring hooks enforce Arch §5.3/§24 (forbidden module/class names, cohesion, no `import *`), strict typing, and comment hygiene (no AI/banner/decorative/stale comments).
- **Why this ticket exists.** These are the recurring blocking gates for every code ticket. Existing hooks are present and must be bound to the architecture's specific rules.
- **Authority references.** `AGENTS.md` (universal blocker checklist); Arch §5.3, §24; `ai/hooks/structure_hook.md`, `naming_hook.md`, `typing_hook.md`, `comment_hook.md`.
- **Dependencies.** P0-T007, P0-T008, P0-T011.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every implementation ticket in every subsequent phase.
- **Preconditions.** P0-T007, P0-T008, P0-T011 complete.
- **Inputs.** Arch §5.3/§24.
- **Allowed scope.** The four hook files and adapters.
- **Forbidden actions.** No provider duplication; no rule relaxation.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Bind the structure hook to forbidden names and the cohesion cap; the naming hook to class/enum naming locks; the typing hook to Pyright strict; the comment hook to no AI/banner/stale comments.
- **Required unit tests.** NONE (checklist gates).
- **Required property tests.** NONE.
- **Required contract tests.** A hook dry-run against a sample module exercising each of the four rules.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Hook dry-run against a sample module.
- **Acceptance criteria.** [ ] Structure/naming/typing/comment hooks bound to Arch §5.3/§24 and strict typing. [ ] Blocking. [ ] No provider duplication.
- **Completion evidence.** Changed files (four hook definitions); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** Any violation blocks completion rather than being bypassed.
- **Stop conditions.** None.
- **Deliverables.** Four hook definitions.
- **Final review checklist.** [ ] Names/comments/typing enforced.

#### P0-T024 — Implement scope/threshold/statistics/lineage/config blocking hooks

- **Ticket ID.** P0-T024
- **Title.** Implement scope/threshold/statistics/lineage/config blocking hooks
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** hook
- **Owner.** datp-protocol-guardian
- **Supporting agents.** statistics-auditor, artifact-lineage-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (this ticket encodes checklist gates, not domain types).
- **Objective.** Ensure scientific-scope, threshold-semantics, statistics, lineage/provenance, and configuration hooks enforce the locked identity: benign-only calibration, CV(FPR) primary / AUROC control, threshold-scope-only causal variable, stage-scoped lineage, no hidden config defaults, no out-of-scope drift.
- **Why this ticket exists.** These hooks encode the scientific and lineage invariants as blocking gates for every domain/experiment ticket. Existing `datp_journal_scope_guard`, `threshold_policy_semantics`, `statistics_hook`, `claim_evidence_hook` are present; a lineage/provenance hook and a configuration hook must be ensured.
- **Authority references.** Roadmap §2 (locks), §10 (statistics); Arch §13 (lineage), §11 (configuration), §29.1; `ai/hooks/statistics_hook.md`, `claim_evidence_hook.md`; `ai/skills/threshold_policy_semantics.md`, `datp_journal_scope_guard.md`, `typed_protocol_state_check.md`.
- **Dependencies.** P0-T017.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every domain/experiment ticket in Phase 1 onward.
- **Preconditions.** P0-T017 complete.
- **Inputs.** Roadmap §2/§10; Arch §11/§13/§29.1.
- **Allowed scope.** Scope/threshold/statistics/lineage/config hook files and adapters.
- **Forbidden actions.** No provider duplication; no hook that permits scope drift, AUROC-as-verdict, attack-in-calibration, or hidden defaults.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Author/bind: the scientific-scope hook (out-of-scope drift block); the threshold-semantics hook (benign-only, scope-only, B4 K=3, naming locks); the statistics hook (CV(FPR) primary, BCa direction, degeneracy typed); the lineage/provenance hook (stage-scoped identity, reuse compatibility, no path identity); the configuration hook (no hidden defaults, discriminated tags, fingerprint separation).
- **Required unit tests.** NONE (checklist gates; the encoded invariants get executable tests in Phase 1/2/7).
- **Required property tests.** NONE.
- **Required contract tests.** A hook dry-run against sample threshold/statistics/config edits.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Hook dry-run against sample threshold/statistics/config edits.
- **Acceptance criteria.** [ ] Scope/threshold/statistics/lineage/config hooks present and blocking. [ ] Locked identity encoded. [ ] No provider duplication.
- **Completion evidence.** Changed files (five hook definitions); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** If a hook rule would require inventing a scientific rule not in the roadmap, raise a blocker instead of inventing it.
- **Stop conditions.** Stop on any invented-rule requirement.
- **Deliverables.** Five hook definitions.
- **Final review checklist.** [ ] Locks enforced, none invented.

#### P0-T025 — Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks

- **Ticket ID.** P0-T025
- **Title.** Implement dependency/no-BC/command-sync/cleanup/final-report/impacted-test hooks
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** hook
- **Owner.** architecture-cleaner
- **Supporting agents.** reproducibility-auditor, compatibility-blocker
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE.
- **Objective.** Ensure the dependency, no-backward-compatibility, command/documentation-synchronization, cleanup, final-report, and impacted-test hooks are defined and blocking, including a test-order-independence gate.
- **Why this ticket exists.** These cross-cutting gates enforce dependency direction, the clean-break policy, doc-sync, cleanup, the mandated final-report format, and impacted-test execution/order-independence. Existing hooks are present; this ticket ensures completeness and the impacted-test/order-independence coverage.
- **Authority references.** `AGENTS.md` (no-BC policy, final-report format, lifecycle steps 6–9); Arch §21 (order independence); `ai/hooks/dependency_hook.md`, `no_backward_compatibility_hook.md`, `readme_makefile_hook.md`, `cleanup_hook.md`, `final_report_hook.md`, `test_hook.md`.
- **Dependencies.** P0-T014.
- **Blocks.** P0-T026.
- **Downstream consumers.** Every implementation ticket in every subsequent phase.
- **Preconditions.** P0-T014 complete.
- **Inputs.** `AGENTS.md`; Arch §21.
- **Allowed scope.** The six hook files and adapters.
- **Forbidden actions.** No provider duplication; no non-blocking downgrade; no allowance of legacy aliases/shims/redirects.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Bind the dependency hook to import-linter/pytest-archon; the no-BC hook to the clean-break policy; the command/doc-sync hook to keep commands and docs aligned; the cleanup hook to no temp/audit clutter; the final-report hook to the required headings; the impacted-test hook to run affected suites and assert order independence.
- **Required unit tests.** NONE (checklist gates; order-independence executable check lives in the test lanes).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Hook dry-runs; an impacted-test lane run; an order-independence run.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Hook dry-runs; impacted-test lane; order-independence run.
- **Acceptance criteria.** [ ] All six hooks defined and blocking. [ ] Final-report headings enforced. [ ] Impacted-test + order-independence gate present. [ ] No provider duplication.
- **Completion evidence.** Changed files (six hook definitions); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** Any failure blocks completion rather than being bypassed.
- **Stop conditions.** None.
- **Deliverables.** Six hook definitions.
- **Final review checklist.** [ ] Clean-break enforced; final-report format enforced.

#### P0-T026 — Establish implementation-task governance and repository baseline quality gate

- **Ticket ID.** P0-T026
- **Title.** Establish implementation-task governance and repository baseline quality gate
- **Phase.** 0
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** foundation
- **Owner.** roadmap-orchestrator
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (this ticket is a composed gate over the tickets it depends on; it owns no domain type of its own).
- **Objective.** Define the implementation-task governance (ticket-extraction discipline, contract-first, gate order) and a single repository baseline quality gate that runs Ruff, Pyright strict, import-linter, pytest-archon, and the Nox validation sessions green on the empty typed skeleton, certifying Phase 0 complete. **This is the Phase 0 baseline quality gate.**
- **Why this ticket exists.** It is the Phase 0 exit gate: it proves the tooling, enforcement, and governance work together before any behavior is written, and it fixes the discipline that each ticket is independently extractable and contract-gated.
- **Authority references.** `AGENTS.md` (lifecycle); Arch §3, §4, §21; Section E (global completion rules).
- **Dependencies.** P0-T001, P0-T002, P0-T003, P0-T004, P0-T005, P0-T006, P0-T007, P0-T008, P0-T009, P0-T010, P0-T011, P0-T012, P0-T013, P0-T014, P0-T015, P0-T016, P0-T017, P0-T018, P0-T019, P0-T020, P0-T021, P0-T022, P0-T023, P0-T024, P0-T025.
- **Blocks.** P1-T001.
- **Downstream consumers.** P1-T001 is the sole direct downstream consumer; every other Phase 1 ticket depends transitively on this gate through the Phase 1 dependency chain rooted at P1-T001.
- **Preconditions.** All twenty-five listed Phase 0 tickets are `DONE` per Section E.
- **Inputs.** Completion evidence from every dependency listed above.
- **Allowed scope.** Governance documentation of the baseline gate and ticket discipline; running the gate.
- **Forbidden actions.** No source behavior; no scientific execution; no relaxation of any tool to make the gate pass.
- **Required configuration or NONE.** Gate composition only.
- **Implementation responsibilities.** Compose the baseline gate (lint/format/strict-type/architecture/import-linter/pytest-archon/Nox sessions) into one runnable check; document ticket-extraction and contract-first governance; record Phase 0 completion in the changelog (Section L) once genuinely reached.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** The full architecture lane (import-linter + pytest-archon scaffold from P0-T011/P0-T012) passes on the empty skeleton.
- **Required integration tests.** The composed baseline gate runs green on the empty skeleton (lint, format, strict-type, architecture, Nox sessions).
- **Required CUDA tests.** The `cuda` Nox session (P0-T014/P0-T015) is present and serialized; no CUDA hardware execution is required to pass the empty-skeleton gate.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Full baseline gate on the skeleton (Ruff, Pyright strict, import-linter, pytest-archon, Nox sessions).
- **Acceptance criteria.** [ ] Baseline gate green on skeleton. [ ] Ticket-extraction/contract-first governance documented. [ ] Phase 0 completion recorded in the changelog (Section L). [ ] Every one of P0-T001–P0-T025 is `DONE`.
- **Completion evidence.** Changed files (governance note); commands run and results for every composed check; a changelog entry (Section L) recording Phase 0 completion; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A red baseline gate blocks Phase 1; no tool is relaxed to force a green result.
- **Stop conditions.** Stop if any tool cannot pass on the empty skeleton without relaxing a rule.
- **Deliverables.** Baseline quality gate; governance note; changelog entry.
- **Final review checklist.** [ ] Green without rule relaxation. [ ] No behavior implemented. [ ] Every mandatory Phase 0 ticket is `DONE`, not merely `NOT_STARTED`, before this gate itself is marked `DONE`.

### Phase 1 — Complete Technical Socle

> **Phase-wide note (applies to every P1 ticket).** Sci-exec is `FORBIDDEN` for all P1 tickets: no real N-BaIoT/Edge-IIoTset/CICIoT2023 data is read, trained, or scored; validation uses deterministic synthetic arrays, synthetic datasets, fake adapters, and test doubles only. Campaign scope is `NONE`. "Completion evidence" for every P1 ticket is the standard final report (Changed Files, Checks Run, Cleanup Result, Remaining Risks, Skipped Checks) plus the resulting type/config/artifact identities the ticket introduced. Every closed union added must be exhausted with `assert_never`; every float-wrapping value object must reject `NaN`/infinity at construction; no object-shaped dictionary may appear in a domain or application contract.

#### P1-T001 — Implement dataset/regime/partition/split domain vocabulary

- **Ticket ID.** P1-T001
- **Title.** Implement dataset/regime/partition/split domain vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `Dataset` (N_BAIOT, CICIOT2023, EDGE_IIOTSET), `Regime` (A, B_A, C, D, D_TEMPORAL — no B-b), `ClientDefinitionStrategy`, `SplitRole`, `RecalibrationMode`, `TemporalOutcome`.
- **Objective.** Implement the finite dataset/regime/partition/split enums in `domain/data/`: `Dataset` (N_BAIOT, CICIOT2023, EDGE_IIOTSET), `Regime` (A, B_A, C, D, D_TEMPORAL — no B-b), `ClientDefinitionStrategy`, `SplitRole`, `RecalibrationMode`, `TemporalOutcome`.
- **Why this ticket exists.** These vocabularies gate every downstream spec/identity; Regime B-b must be absent (out-of-scope has no executable member). Separate because it owns one capability's finite vocabulary.
- **Authority references.** Arch §6.1 (enum table), §5.1 (`domain/data/`), §6.10 (exhaustiveness); Road §7 (regime table).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T019.
- **Downstream consumers.** P1-T019 (dataset/partition/split specifications) builds on these enums; every later dataset/regime-aware spec and identity depends on them transitively.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1, §5.1, §6.10; Road §7.
- **Allowed scope.** `domain/data/datasets.py`, `partitioning.py`, `splitting.py` (enums only, no specs).
- **Forbidden actions.** No Regime B-b member; no out-of-scope member; no frameworks; no path/string as enum; no specs here.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s with UPPER_SNAKE members / snake_case values; co-locate per capability; no centralized `vocabulary.py`.
- **Required unit tests.** Membership and serialized-value stability for each enum.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** No forbidden module name; no framework import in `domain/data`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; architecture lane; unit lane.
- **Acceptance criteria.** [ ] Enums match Arch §6.1 exactly. [ ] No B-b/out-of-scope member. [ ] No framework import. [ ] Serialized values stable.
- **Completion evidence.** Changed files (`domain/data/datasets.py`, `partitioning.py`, `splitting.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Stop if a member's meaning is ambiguous vs. the roadmap regime table; raise an explicit design-decision blocker rather than guessing.
- **Stop conditions.** Stop if a member's meaning is ambiguous vs. the roadmap regime table.
- **Deliverables.** `domain/data/` enum modules.
- **Final review checklist.** [ ] Regime B-b absent. [ ] Co-located, not centralized.

#### P1-T002 — Implement model/training/checkpoint/score domain vocabulary

- **Ticket ID.** P1-T002
- **Title.** Implement model/training/checkpoint/score domain vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** federated-learning-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ActivationFunction`, `AggregationStrategy` (FEDAVG, FEDPROX), `ModelPersonalizationStrategy` (NONE, DITTO, FEDREP_AE, FEDPER_AE), `ParticipationStrategy` (FULL), `OptimizerType`, `LrSchedulerType`, `PrecisionMode`, `DeterminismLevel`, `CheckpointKind`, `CheckpointSelectionStrategy` (REGIME_A_GLOBAL_PRIMARY), `QuantileEstimatorType`.
- **Objective.** Implement `domain/learning/` enums: `ActivationFunction`, `AggregationStrategy` (FEDAVG, FEDPROX), `ModelPersonalizationStrategy` (NONE, DITTO, FEDREP_AE, FEDPER_AE), `ParticipationStrategy` (FULL), `OptimizerType`, `LrSchedulerType`, `PrecisionMode`, `DeterminismLevel`, `CheckpointKind`, `CheckpointSelectionStrategy` (REGIME_A_GLOBAL_PRIMARY), `QuantileEstimatorType`.
- **Why this ticket exists.** Encodes training/scoring locks: FedAvg core, FedProx stress only, full participation, one global checkpoint-selection rule, exact quantile estimators, personalization naming lock (never mislabel FedRep/FedPer as Ditto).
- **Authority references.** Arch §6.1, §6.2, §6.3 (`SeedRole` excluded — that is P1-T009), §29.4.
- **Dependencies.** P0-T026.
- **Blocks.** P1-T021, P1-T023.
- **Downstream consumers.** P1-T021 (model/federation/training/batch specs) and P1-T023 (scoring specs) build directly on this vocabulary.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1, §6.2, §6.3, §29.4.
- **Allowed scope.** `domain/learning/models.py`, `training.py`, `checkpoints.py`, `scores.py` (enums only).
- **Forbidden actions.** No partial-participation member; no per-regime/test-driven checkpoint-selection member; no approximate quantile member; no BatchNorm-implying member; naming-lock violation forbidden.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s per capability; `CheckpointSelectionStrategy` has exactly one member; `ParticipationStrategy` has exactly `FULL`.
- **Required unit tests.** Membership and serialized-value stability for each enum.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/learning/`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; architecture; unit lanes.
- **Acceptance criteria.** [ ] One checkpoint-selection member. [ ] Participation is FULL only. [ ] All quantile estimators exact. [ ] Personalization naming lock present.
- **Completion evidence.** Changed files (`domain/learning/` enum modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; a genuinely ambiguous enum member is raised as a design-decision blocker rather than guessed.
- **Stop conditions.** None.
- **Deliverables.** `domain/learning/` enum modules.
- **Final review checklist.** [ ] No partial participation; no approximate quantile.

#### P1-T003 — Implement threshold-policy/variant/comparator domain vocabulary

- **Ticket ID.** P1-T003
- **Title.** Implement threshold-policy/variant/comparator domain vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** threshold-policy-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `CoreThresholdPolicy` (B1–B4), `ThresholdConstructionKind` (9 variants), `SharedThresholdConstruction` (MEAN/POOLED/WEIGHTED), `ThresholdVariant`, `ThresholdComparatorRole` (CENTRALIZED_MODEL_B0, FED_STATS_BENIGN), `ConformalMode`.
- **Objective.** Implement `domain/thresholding/` enums: `CoreThresholdPolicy` (B1–B4), `ThresholdConstructionKind` (9 variants), `SharedThresholdConstruction` (MEAN/POOLED/WEIGHTED), `ThresholdVariant`, `ThresholdComparatorRole` (CENTRALIZED_MODEL_B0, FED_STATS_BENIGN), `ConformalMode`.
- **Why this ticket exists.** Encodes the causal ladder and the explicit discriminator tag for the threshold union; B0 is a comparator not a ladder policy; `B-LaridiFaithful` has no executable member.
- **Authority references.** Arch §6.1, §6.2, §6.10; Road §4 (nomenclature, naming locks).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T024.
- **Downstream consumers.** P1-T024 (threshold-construction union and suite specifications) is the sole immediate consumer.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1, §6.2, §6.10; Road §4.
- **Allowed scope.** `domain/thresholding/policies.py`, `variants.py`, `federated_statistics.py` (enums only).
- **Forbidden actions.** No `B-LaridiFaithful` executable member; no B5 label; B0 never a ladder policy member; no q-mutated fingerprint concept as enum.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s; `ThresholdConstructionKind` is the explicit tag for the closed union (built in P1-T024).
- **Required unit tests.** Membership and serialized values for each enum.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/thresholding/`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; architecture; unit lanes.
- **Acceptance criteria.** [ ] Nine construction kinds present. [ ] B0/FedStats are comparator roles, not ladder members. [ ] No Laridi-faithful executable member. [ ] Naming locks honored.
- **Completion evidence.** Changed files (`domain/thresholding/` enum modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; exhaustiveness is enforced at union consumers built in P1-T024.
- **Stop conditions.** None.
- **Deliverables.** `domain/thresholding/` enum modules.
- **Final review checklist.** [ ] Ladder = B1–B4 only.

#### P1-T004 — Implement metric-family enums and the MetricId union

- **Ticket ID.** P1-T004
- **Title.** Implement metric-family enums and the MetricId union
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `MetricFamily`, `OperatingPointMetric` (CV_FPR), `DetectionQualityMetric` (AUROC control-only), `EquityMetric`, `EstimationMetric`, `ClusterMetric`, `DistributionMetric`, `DiagnosticRatio`, `ResourceMetric`, the disjoint `MetricId` union, `MetricSpec`.
- **Objective.** Implement `domain/evaluation/metrics.py` metric-family enums (`MetricFamily`, `OperatingPointMetric` with CV_FPR, `DetectionQualityMetric` with AUROC control-only, `EquityMetric`, `EstimationMetric`, `ClusterMetric`, `DistributionMetric`, `DiagnosticRatio`, `ResourceMetric`), the disjoint `MetricId` union, and `MetricSpec` (family, is_control, needs_eligible_only, higher_is_better).
- **Why this ticket exists.** Encodes CV(FPR)-primary / AUROC-control at the type level; disjoint families make the union unambiguous.
- **Authority references.** Arch §6.1, §6.8, §9.3 (`MetricSpec`), §11.4 (primary must be CV_FPR); Road §10.
- **Dependencies.** P0-T026.
- **Blocks.** P1-T026.
- **Downstream consumers.** P1-T026 (evaluation/operating-point/alert-burden result types) is the sole immediate consumer.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1, §6.8, §9.3, §11.4; Road §10.
- **Allowed scope.** `domain/evaluation/metrics.py`, alert-burden enums in `alert_burden.py`.
- **Forbidden actions.** No overlapping metric ids across families; no AUROC without control flag; no generic metric bag.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Family enums; `type MetricId = ...` union; `MetricSpec` frozen dataclass; `MetricMap` template co-located.
- **Required unit tests.** Family disjointness; `MetricSpec` flags for CV_FPR (primary/eligible-only) and AUROC (control).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/evaluation/metrics.py`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] Metric ids disjoint across families. [ ] AUROC is control-only. [ ] `MetricSpec` carries all four flags. [ ] Union unambiguous.
- **Completion evidence.** Changed files (`domain/evaluation/metrics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** A non-metric key is rejected by `MetricMap` (P1-T015); no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Metric vocabulary and `MetricSpec`.
- **Final review checklist.** [ ] CV_FPR primary; AUROC control.

#### P1-T005 — Implement statistical-method/claim-outcome/absorption vocabulary

- **Ticket ID.** P1-T005
- **Title.** Implement statistical-method/claim-outcome/absorption vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `StatisticalMethod` (BCA_BOOTSTRAP primary, PERCENTILE_BOOTSTRAP, WILCOXON_SIGNED_RANK, CLIFFS_DELTA, SPEARMAN, LINEAR_REGRESSION_R2), `ClaimOutcome` (seven outcomes), `AbsorptionBand` (four bands).
- **Objective.** Implement `domain/evaluation/statistical_results.py` enums: `StatisticalMethod` (BCA_BOOTSTRAP primary, PERCENTILE_BOOTSTRAP, WILCOXON_SIGNED_RANK, CLIFFS_DELTA, SPEARMAN, LINEAR_REGRESSION_R2), `ClaimOutcome` (seven outcomes), `AbsorptionBand` (four bands).
- **Why this ticket exists.** Encodes BCa-primary, the fallback-wording selector, and the pre-specified absorption bands as closed vocabularies.
- **Authority references.** Arch §6.1; Road §9.3 (absorption bands), §12 (fallback wording).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T027.
- **Downstream consumers.** P1-T027 (statistical/confirmatory/anchor-gate result types) is the sole immediate consumer.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1; Road §9.3, §12.
- **Allowed scope.** `domain/evaluation/statistical_results.py` (enums here; result dataclasses in P1-T027).
- **Forbidden actions.** No silent BCa→percentile substitution path; no extra absorption band; no free-text outcome.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s per Arch §6.1.
- **Required unit tests.** Membership and serialized values for each enum.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/evaluation/statistical_results.py`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] BCa present as primary method. [ ] Four absorption bands exactly. [ ] Seven claim outcomes exactly.
- **Completion evidence.** Changed files (`domain/evaluation/statistical_results.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; exhaustiveness is enforced at consumers.
- **Stop conditions.** None.
- **Deliverables.** Statistical vocabulary enums.
- **Final review checklist.** [ ] Bands/outcomes match roadmap.

#### P1-T006 — Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant

- **Ticket ID.** P1-T006
- **Title.** Implement experiment-role/claim-tier/status vocabulary and the role/tier invariant
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ExperimentRole` (nine roles), `ClaimTier` (`IntEnum` TIER_1..TIER_9), `ExecutionStatus`, the constructor-enforced role/tier invariant.
- **Objective.** Implement `domain/experiments/claims.py`: `ExperimentRole` (nine roles), `ClaimTier` (IntEnum TIER_1..TIER_9), `ExecutionStatus`, and the constructor-enforced invariant that `CONFIRMATORY ⇔ TIER_1` and no other role carries TIER_1.
- **Why this ticket exists.** Makes it impossible to promote a supportive/mechanism/stress experiment into the confirmatory claim.
- **Authority references.** Arch §6.1, §8.3 (role/tier invariant), §29.1; Road §5 (nine tiers), §3.
- **Dependencies.** P0-T026.
- **Blocks.** P1-T029.
- **Downstream consumers.** P1-T029 (experiment identity/profile/cell aggregates) enforces this invariant at construction.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1, §8.3, §29.1; Road §5, §3.
- **Allowed scope.** `domain/experiments/claims.py`.
- **Forbidden actions.** No confirmatory role outside Tier 1; no promotion path; no free-text role.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Enums plus a validation used by `ExperimentIdentity` construction (finalized in P1-T029).
- **Required unit tests.** Confirmatory requires Tier 1; any other role with Tier 1 rejected.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit lanes.
- **Acceptance criteria.** [ ] Nine roles, nine tiers. [ ] Role/tier invariant enforced. [ ] Only confirmatory maps to Tier 1.
- **Completion evidence.** Changed files (`domain/experiments/claims.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on a role/tier mismatch; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Experiment-role/tier vocabulary and invariant.
- **Final review checklist.** [ ] No promotion possible.

#### P1-T007 — Implement feasibility/rejection/reuse/blocking vocabulary

- **Ticket ID.** P1-T007
- **Title.** Implement feasibility/rejection/reuse/blocking vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** experiment-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `FeasibilityStatus`, `RejectionReason` (E-R1..R8), `ReuseIncompatibilityReason` (13 members), `BlockingReason`, `ClientEligibilityStatus`, `ClientEligibilityReason`.
- **Objective.** Implement `domain/experiments/feasibility.py` enums: `FeasibilityStatus`, `RejectionReason` (E-R1..R8), `ReuseIncompatibilityReason` (13 members), `BlockingReason`, plus `ClientEligibilityStatus`/`ClientEligibilityReason`.
- **Why this ticket exists.** Encodes rejected experiments as non-executable records and reuse-incompatibility/blocking causes as typed reasons (never free text).
- **Authority references.** Arch §6.1; Road §9.4 (rejected), §7 (B-b rejection), §11 (temporal rejection).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T029, P4-T012.
- **Downstream consumers.** P1-T029 (experiment identity/profile/cell aggregates) and P4-T012 consume this vocabulary directly.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.1; Road §9.4, §7, §11.
- **Allowed scope.** `domain/experiments/feasibility.py`, eligibility enums in `domain/evaluation/operating_points.py`.
- **Forbidden actions.** No executable member for a rejected experiment; no free-text reason; missing-traffic-rate is not a client-eligibility reason (fails alert-burden config instead).
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s per Arch §6.1; stable rendered labels (`B_B_REJECTED_NO_METADATA`, `TEMPORAL_REJECTED_NO_TIMESTAMPS`).
- **Required unit tests.** Membership; stable rendered labels.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Rejected-experiment members carry no executable path (asserted with the catalogue tests in P1-T050/P4).
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] E-R1..R8 reasons present. [ ] 13 reuse-incompatibility reasons. [ ] Stable rendered rejection labels. [ ] No free-text reason.
- **Completion evidence.** Changed files (`domain/experiments/feasibility.py`, `domain/evaluation/operating_points.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; typed reasons only, no free-text fallback.
- **Stop conditions.** None.
- **Deliverables.** Feasibility/rejection/reuse/blocking vocabulary.
- **Final review checklist.** [ ] Rejected ≠ executable.

#### P1-T008 — Implement storage/artifact/manifest vocabulary

- **Ticket ID.** P1-T008
- **Title.** Implement storage/artifact/manifest vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `StorageRootKind`, `StorageVisibility`, `ArtifactNamespace` (DATP_ANCHOR, JOURNAL_EXTENSION, RECOVERY, CACHE, STAGING, TEST_SANDBOX), `SerializationFormat`, `WriteDisposition`, `ManifestType`, `ArtifactType`, `LockScope`, `ValidationStatus`, `IntegrityStatus`, `SchemaCompatibility`.
- **Objective.** Implement `domain/artifacts/` enums: `StorageRootKind`, `StorageVisibility`, `ArtifactNamespace` (DATP_ANCHOR, JOURNAL_EXTENSION, RECOVERY, CACHE, STAGING, TEST_SANDBOX), `SerializationFormat`, `WriteDisposition`, `ManifestType`, `ArtifactType`, `LockScope`, `ValidationStatus`, `IntegrityStatus`, `SchemaCompatibility`.
- **Why this ticket exists.** Encodes semantic roots (never paths), anchor/journal namespace separation, and the artifact/manifest provenance vocabulary; every persisted entity maps to exactly one precise `ArtifactType`.
- **Authority references.** Arch §6.4, §15.1, §15.2, §9.5.
- **Dependencies.** P0-T026.
- **Blocks.** P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059.
- **Downstream consumers.** All six persistence tickets (P1-T054–P1-T059) depend on this vocabulary for their storage/artifact/manifest types.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.4, §15.1, §15.2, §9.5.
- **Allowed scope.** `domain/artifacts/keys.py`, `manifests.py`, `references.py`, `lineage.py` (enums only).
- **Forbidden actions.** No path as enum; no generic `ArtifactType` catch-all; no merged anchor/journal namespace.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s per Arch §6.4; separate anchor/journal/recovery/cache/staging/test namespaces.
- **Required unit tests.** Each independently persisted concept maps to exactly one `ArtifactType` (cross-check with §9.5).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/artifacts/`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] Namespaces separated. [ ] Every §9.5 persisted type maps to one `ArtifactType`. [ ] No path enum.
- **Completion evidence.** Changed files (`domain/artifacts/` enum modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Storage/artifact/manifest vocabulary.
- **Final review checklist.** [ ] One `ArtifactType` per entity.

#### P1-T009 — Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary

- **Ticket ID.** P1-T009
- **Title.** Implement runtime/lifecycle/seed-role/pipeline-stage vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ExecutionMode`, `DevicePolicy`, `PipelineStage` (authoritative ordered stages), `RunStatus`, `SeedRole`, `ReuseDecisionKind`, `StageConcurrency`, `ProcessStartMethod`, `WorkerRole`, `FailureDisposition`, `RoundDisposition`, `ResourcePressureLevel`, `PauseDecision`, `ReuseImpact`. `PipelineStage` and `SeedRole` feed stage identity.
- **Objective.** Implement `domain/runtime/` and `domain/artifacts/lineage.py` execution vocabularies: `ExecutionMode`, `DevicePolicy`, `PipelineStage` (authoritative ordered stages), `RunStatus`, `SeedRole`, `ReuseDecisionKind`, `StageConcurrency`, `ProcessStartMethod`, `WorkerRole`, `FailureDisposition`, `RoundDisposition`, `ResourcePressureLevel`, `PauseDecision`, `ReuseImpact`.
- **Why this ticket exists.** Defines the pipeline-stage identity/order, seed ownership, reuse/impact classification, and cooperative-pressure vocabulary underpinning determinism and lifecycle.
- **Authority references.** Arch §6.3, §13.1 (stage order), §16.6–16.7, §18.
- **Dependencies.** P0-T026.
- **Blocks.** P1-T036, P1-T039.
- **Downstream consumers.** P1-T036 (persistence/runtime application ports) and P1-T039 (preflight/executor/lifecycle/resource-pressure orchestration) consume this vocabulary directly.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.3, §13.1, §16.6–16.7, §18.
- **Allowed scope.** `domain/runtime/policies.py`, `seeds.py`, `domain/artifacts/lineage.py` (enums here).
- **Forbidden actions.** No scattered global-seed concept; no execution enum that mutates scientific identity; no multi-GPU/multi-node member.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `StrEnum`s; `PipelineStage` ordered per Arch §6.3; `SeedRole` covers all random-state owners.
- **Required unit tests.** Stage-order stability; seed-role completeness.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Framework confinement for `domain/runtime/` and `domain/artifacts/lineage.py`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] `PipelineStage` matches Arch §6.3 order. [ ] All `SeedRole` owners present. [ ] No multi-GPU member.
- **Completion evidence.** Changed files (`domain/runtime/policies.py`, `seeds.py`, `domain/artifacts/lineage.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Exhaustiveness is enforced at dispatch (`assert_never`); no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Runtime/lifecycle vocabulary.
- **Final review checklist.** [ ] Stage order authoritative.

#### P1-T051 — Implement application telemetry vocabulary and contracts

- **Ticket ID.** P1-T051
- **Title.** Implement application telemetry vocabulary and contracts
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** telemetry
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `LogEventKind`, `LogSink`, `LogFormat`, `StructuredEvent`, `EventContext`, the typed detail union (`RunPlannedDetail`, `StageLifecycleDetail`, `ArtifactEventDetail`, `ResourceEventDetail`, `DeterminismEventDetail`, `LineageEventDetail`, `FederatedRoundEventDetail`, `HeartbeatEventDetail`, `RecoveryEventDetail`, `TestProfileDetail`), `EventSink` (Protocol boundary only; the infrastructure adapter is P1-T065).
- **Objective.** Implement the observability vocabulary and typed event envelope in `application/ports/telemetry.py`: `LogEventKind`, `LogSink`, `LogFormat`, `StructuredEvent`, `EventContext`, and the discriminated per-kind detail types, plus the `EventSink` Protocol.
- **Why this ticket exists.** This vocabulary is an `application` concern, not a `domain` one (Arch §6.5): log-rendering and event-envelope shape are operational, not scientific meaning. It is split out of the former combined observability/reporting/test-vocabulary ticket because it owns a distinct layer (`application`) from the reporting vocabulary (`analysis`/`application`) and the test vocabulary (`tests/support`), which must never be a single ticket type per Section D.
- **Authority references.** Arch §6.5 (observability vocabulary), §19.1 (event model), §19.2 (rules), §9.2 layer-ownership rule (Section 3.5 ownership matrix: `application` owns ports).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T065.
- **Downstream consumers.** P1-T065 (structured telemetry adapter) implements `EventSink`; every stage function that publishes an event depends on this vocabulary transitively through the port.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.5, §19.1, §19.2.
- **Allowed scope.** `application/ports/telemetry.py`.
- **Forbidden actions.** No domain placement of observability enums; no event kind binding to more than one detail type; no array/per-sample score/secret/dataset-row/full-config-dump field in any detail type.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Define `LogEventKind`/`LogSink`/`LogFormat` as `StrEnum`s; define `EventContext` and `StructuredEvent` as frozen dataclasses; define the closed detail-type union with one detail bound per `LogEventKind`; define the `EventSink` Protocol (`publish(event: StructuredEvent) -> None`).
- **Required unit tests.** Each `LogEventKind` member binds to exactly one detail type; no detail type carries an array, per-sample score, secret, dataset row, or full configuration dump.
- **Required property tests.** NONE.
- **Required contract tests.** `EventSink.publish` accepts every constructed `StructuredEvent` variant without a type error.
- **Required architecture tests.** `application/ports/telemetry.py` imports no framework and no `infrastructure` module.
- **Required integration tests.** NONE (adapter-level integration belongs to P1-T065).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] `LogEventKind`/`LogSink`/`LogFormat` defined. [ ] `StructuredEvent`/`EventContext` frozen and complete. [ ] Detail union is one-to-one with `LogEventKind`. [ ] `EventSink` Protocol defined with no framework import.
- **Completion evidence.** Changed files (`application/ports/telemetry.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected; a genuinely ambiguous event-kind/detail mapping is recorded as a design-decision blocker rather than guessed.
- **Stop conditions.** None.
- **Deliverables.** Application telemetry vocabulary and `EventSink` port.
- **Final review checklist.** [ ] No framework leakage. [ ] One detail type per event kind.

#### P1-T052 — Implement analysis reporting vocabulary

- **Ticket ID.** P1-T052
- **Title.** Implement analysis reporting vocabulary
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ReportArtifactType`, `TableType`, `FigureType` (no Sankey member), `RenderingStatus`.
- **Objective.** Implement the reporting vocabulary in `analysis/report_models.py` (`ReportArtifactType`, `TableType`, `FigureType`) and `RenderingStatus` in `application/reporting/tracing.py`, with `FigureType` explicitly carrying no Sankey member.
- **Why this ticket exists.** Split out of the former combined observability/reporting/test-vocabulary ticket because this vocabulary spans the `analysis` and `application` layers, distinct from the `application`-only telemetry vocabulary (P1-T051) and the test-only vocabulary (P1-T053); each layer/concern owns exactly one ticket type per Section D.
- **Authority references.** Arch §6.6 (reporting vocabulary), §22.1 (no Sankey; B4 interpretability uses a contingency table or heatmap).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T049.
- **Downstream consumers.** P1-T049 (analysis table/figure/wording/report-model specification layer) and P1-T067 (report renderers) both consume this vocabulary.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.6, §22.1.
- **Allowed scope.** `analysis/report_models.py`, `application/reporting/tracing.py` (vocabulary only; the tracing service itself is P1-T040/gates work already scoped elsewhere).
- **Forbidden actions.** No Sankey `FigureType` member; no generic coverage field shared by eligibility and conformal coverage (Arch §22.1); no persistence or rendering-library import in `analysis`.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Define `ReportArtifactType`, `TableType`, `FigureType` as `StrEnum`s with the exact roadmap-required members and no Sankey member; define `RenderingStatus` (`PENDING`, `RENDERED`, `TRACE_REFUSED`).
- **Required unit tests.** No Sankey `FigureType` member exists; `TableType` and `FigureType` cover every roadmap table/figure family named in Road §5/§9.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** `analysis/report_models.py` imports no framework, no persistence adapter, and no `infrastructure` module.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] No Sankey figure type. [ ] `ReportArtifactType`/`TableType`/`FigureType` complete. [ ] `RenderingStatus` defined. [ ] `analysis` stays framework-free.
- **Completion evidence.** Changed files (`analysis/report_models.py`, `application/reporting/tracing.py` vocabulary additions); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Analysis reporting vocabulary.
- **Final review checklist.** [ ] No Sankey. [ ] Framework-free `analysis`.

#### P1-T053 — Implement test-support vocabulary and typed test profiles

- **Ticket ID.** P1-T053
- **Title.** Implement test-support vocabulary and typed test profiles
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** test-support
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `TestSuiteKind`, `TestDataScale`, `TestIsolationMode`, `TestDeviceRequirement`, `TestParallelismMode`, `ExternalDependencyPolicy`, `ArtifactRetentionPolicy`, `TestOutcome`, `TestResourceBudget`, `TestArtifactPolicy`, `TestLoggingSpec`, `TestProfileSpec`.
- **Objective.** Implement the test vocabulary and `TestProfileSpec` under `tests/support/` (`TestSuiteKind`, `TestDataScale`, `TestIsolationMode`, `TestDeviceRequirement`, `TestParallelismMode`, `ExternalDependencyPolicy`, `ArtifactRetentionPolicy`, `TestOutcome`), explicitly never imported by any `src/datp_core` production package.
- **Why this ticket exists.** Split out of the former combined observability/reporting/test-vocabulary ticket because test infrastructure is a `tests/support/` concern, never a production application contract (Arch §21.1, §12.3), and must never share a ticket type with the `application`/`analysis` vocabularies of P1-T051/P1-T052.
- **Authority references.** Arch §6.7 (test vocabulary), §21.1 (`TestProfileSpec`), §21.3 (configuration ownership: `configs/tests/` holds profile data, `pyproject.toml` holds markers only).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T070.
- **Downstream consumers.** Every `tests/` fixture and profile resolution in Phase 1 onward, and the Phase 1 socle-readiness gate (P1-T070), which exercises test profiles end-to-end.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §6.7, §21.1, §21.3.
- **Allowed scope.** `tests/support/profiles.py` and related test-vocabulary modules under `tests/support/`.
- **Forbidden actions.** No import of this vocabulary by any `src/datp_core` production package; no test-profile field in `pyproject.toml`; no raw mapping in place of `TestProfileSpec`.
- **Required configuration or NONE.** Profile data lives in `configs/tests/` as plain YAML with no `__init__.py` and no executable Python; this ticket implements the code-side types that map to it.
- **Implementation responsibilities.** Define the eight test-vocabulary `StrEnum`s; define `TestResourceBudget`, `TestArtifactPolicy`, `TestLoggingSpec`, and the composed `TestProfileSpec` as frozen dataclasses.
- **Required unit tests.** `tests/support/` vocabulary and `TestProfileSpec` are not importable from any `src/datp_core` module (verified by an architecture-level import check, not a trivial existence test).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** No production module under `src/datp_core` imports `tests/support/`; the dependency runs one way only (Arch §21).
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit; architecture lanes.
- **Acceptance criteria.** [ ] All eight test-vocabulary enums defined. [ ] `TestProfileSpec` composed correctly. [ ] Not importable from `src/datp_core`. [ ] No profile data in `pyproject.toml`.
- **Completion evidence.** Changed files (`tests/support/` vocabulary modules); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Test-support vocabulary and `TestProfileSpec`.
- **Final review checklist.** [ ] Test-only; never imported by production code.

#### P1-T011 — Implement finite-numeric and Decimal probability-like value objects

- **Ticket ID.** P1-T011
- **Title.** Implement finite-numeric and Decimal probability-like value objects
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ThresholdPercentile`, `FprTarget`, `ConfidenceLevel`, `CoverageRatio`, `EligibilityCoverage`, `ConformalCoverage`, `Probability`, `FalsePositiveRate`, `TruePositiveRate`, `AuRocScore`, `ThresholdValue`, `DirichletAlpha`, `ShrinkageWeight`.
- **Objective.** Implement the scalar value objects of Arch §7 with `__post_init__` validation: `ThresholdPercentile`/`FprTarget`/`ConfidenceLevel`/`CoverageRatio`/`EligibilityCoverage`/`ConformalCoverage`/`Probability` as canonical `Decimal` types (quantized once), and all float-wrapping rates/scores (`FalsePositiveRate`, `TruePositiveRate`, `AuRocScore`, `ThresholdValue`, `DirichletAlpha`, `ShrinkageWeight`, etc.) rejecting `NaN`/infinity; enforce `FprTarget == 1 − q` on canonical Decimals and keep probability-like types mutually non-interchangeable.
- **Why this ticket exists.** Non-finite values in fingerprinted fields silently break reuse (`NaN != NaN`); Decimal canonicality makes `q`/`1−q` exact and reproducible; distinct types prevent confidence/target/coverage confusion.
- **Authority references.** Arch §7 (value-object table), §7.3 (numeric validity/canonical Decimal), §13.4.
- **Dependencies.** P1-T001.
- **Blocks.** P1-T019, P1-T024.
- **Downstream consumers.** P1-T019 (dataset/partition/split specifications) and P1-T024 (threshold-construction union) build directly on these value objects; probability-like objects feed threshold/statistical identities.
- **Preconditions.** P1-T001 complete.
- **Inputs.** Arch §7, §7.3, §13.4.
- **Allowed scope.** `domain/thresholding/policies.py`/`variants.py`, `domain/evaluation/statistical_results.py`, `domain/data/` alpha.
- **Forbidden actions.** No binary-float storage for identity-bearing probabilities; no interchangeable probability types; no missing finiteness check.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen slotted kw-only dataclasses; Decimal quantization in `__post_init__`; range + finiteness checks; `FprTarget == 1 − q` exact check.
- **Required unit tests.** Quantization determinism.
- **Required property tests.** Range/finiteness for every float VO; `fpr_target == 1 − q` under canonical representation; probability types not substitutable.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property lane; strict type; unit lane.
- **Acceptance criteria.** [ ] Every float VO rejects NaN/inf. [ ] Probability-like VOs are Decimal and non-interchangeable. [ ] `FprTarget == 1 − q` holds exactly. [ ] Quantization deterministic.
- **Completion evidence.** Changed files (value-object modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` (including a non-finite subtype) on invalid/NaN/inf input; stop if the roadmap's canonical decimal-place count for a quantity is unresolved and raise a blocker.
- **Stop conditions.** Stop if the roadmap's canonical decimal-place count for a quantity is unresolved; raise a blocker.
- **Deliverables.** Scalar value-object modules.
- **Final review checklist.** [ ] No raw-float identity fields.

#### P1-T012 — Implement identity, seed-plan, and stage-fingerprint value objects

- **Ticket ID.** P1-T012
- **Title.** Implement identity, seed-plan, and stage-fingerprint value objects
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ExperimentId`, `ArchitectureCatalogueId`, `CellId`, `ArtifactId`, `RunIdentity`, `ExecutionAttemptId`, `StageRunIdentity`, `CheckpointId`, `StageFingerprint`, `Seed`, `RoundNumber`, `SeedTuple`, `SeedRoleTuple`, `SeedMap`, `ConfirmatorySeedCohort`, `derive_seed`. Introduces `StageFingerprint`, id, and seed identities.
- **Objective.** Implement `ExperimentId`/`ArchitectureCatalogueId`/`CellId`/`ArtifactId`/`RunIdentity`/`ExecutionAttemptId`/`StageRunIdentity`/`CheckpointId`/`StageFingerprint`/`Seed`/`RoundNumber` and the seed collections (`SeedTuple`, `SeedRoleTuple`, `SeedMap`, `ConfirmatorySeedCohort`) with their validation regexes/cardinalities, plus `derive_seed`.
- **Why this ticket exists.** Distinguishes scientific identity (`RunIdentity`) from operational attempt (`ExecutionAttemptId`); prevents random scientific ids; enforces the ten-paired-seed cohort shape without inventing seed values.
- **Authority references.** Arch §7 (identity VOs), §7.2, §10 (seed collections), §16.7 (`derive_seed`), §13.5.
- **Dependencies.** P1-T009.
- **Blocks.** P1-T013.
- **Downstream consumers.** P1-T013 (per-stage nominal identity dataclasses) wraps `StageFingerprint` from this ticket for every stage identity.
- **Preconditions.** P1-T009 complete.
- **Inputs.** Arch §7, §7.2, §10, §16.7, §13.5.
- **Allowed scope.** `domain/experiments/identities.py`, `domain/artifacts/references.py`, `domain/runtime/seeds.py`.
- **Forbidden actions.** No random scientific `ArtifactId`; no seed values invented; no interchange of `RunIdentity`/`ExecutionAttemptId`; no PEP 695 alias as identity guard.
- **Required configuration or NONE.** NONE (seed values come from resolved config, not here).
- **Implementation responsibilities.** Regex/format validation; `CellId = <ExperimentId>#<hash16>` from canonical resolved cell spec; `ConfirmatorySeedCohort` cardinality = ten paired; `derive_seed(experiment_seed, role, stage_fp)`.
- **Required unit tests.** Cohort requires exactly ten paired; random-id prohibition for scientific artifacts.
- **Required property tests.** Id format validation; deterministic `derive_seed`.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property; unit; strict type lanes.
- **Acceptance criteria.** [ ] `RunIdentity`≠`ExecutionAttemptId`. [ ] Scientific ids deterministic, never random. [ ] Cohort = exactly ten paired. [ ] `derive_seed` deterministic. [ ] No seed value hardcoded.
- **Completion evidence.** Changed files (`domain/experiments/identities.py`, `domain/artifacts/references.py`, `domain/runtime/seeds.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on malformed ids/cohorts; stop if the authoritative seed specification format is unresolved and raise a blocker (do not invent values).
- **Stop conditions.** Stop if the authoritative seed specification format is unresolved; raise a blocker (do not invent values).
- **Deliverables.** Identity/seed value objects and `derive_seed`.
- **Final review checklist.** [ ] No invented seeds.

#### P1-T013 — Implement per-stage nominal identity dataclasses

- **Ticket ID.** P1-T013
- **Title.** Implement per-stage nominal identity dataclasses
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `DatasetSourceIdentity`, `FeatureSchemaIdentity`, `PartitionIdentity`, `SplitIdentity`, `FittedPreprocessorIdentity`, `ProcessedSplitIdentity`, `TrainingIdentity`, `CheckpointIdentity`, `CheckpointSelectionIdentity`, `CalibrationScoringIdentity`, `TestScoringIdentity`, `TemporalScoringIdentity`, `ThresholdIdentity`, `EvaluationIdentity`, `StatisticalIdentity`, `ResultFreezeIdentity`, `ReportIdentity`, the centralized-branch identities, `TemporalWindowIdentity`, `ResolvedConfigurationIdentity`, `RecoveryCompatibilityIdentity`, `StageIdentity`. Introduces every per-stage identity type.
- **Objective.** Implement each per-stage identity as its own frozen dataclass wrapping `StageFingerprint` (not a PEP 695 alias): `DatasetSourceIdentity`, `FeatureSchemaIdentity`, `PartitionIdentity`, `SplitIdentity`, `FittedPreprocessorIdentity`, `ProcessedSplitIdentity`, `TrainingIdentity`, `CheckpointIdentity`, `CheckpointSelectionIdentity`, `CalibrationScoringIdentity`, `TestScoringIdentity`, `TemporalScoringIdentity`, `ThresholdIdentity`, `EvaluationIdentity`, `StatisticalIdentity`, `ResultFreezeIdentity`, `ReportIdentity`, the centralized-branch identities, `TemporalWindowIdentity`, `ResolvedConfigurationIdentity`, `RecoveryCompatibilityIdentity`, and the composing `StageIdentity`.
- **Why this ticket exists.** Nominal distinctness makes cross-stage and calibration/test-role substitution a type error; a structural alias cannot.
- **Authority references.** Arch §7.2, §13.1–§13.2, §29.2.
- **Dependencies.** P1-T012.
- **Blocks.** P1-T028.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) composes these identities transitively through every downstream spec.
- **Preconditions.** P1-T012 complete.
- **Inputs.** Arch §7.2, §13.1–§13.2, §29.2.
- **Allowed scope.** `domain/artifacts/lineage.py` and the identity types it declares.
- **Forbidden actions.** No `type X = StageFingerprint` alias as an identity; no shared identity between FedAvg and centralized branches; no substitutable calibration/test identity.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen dataclasses each wrapping a `StageFingerprint`; `StageIdentity` composes distinct calibration/test/temporal identities.
- **Required unit tests.** A calibration identity cannot be passed where a test identity is required (type-level; asserted via a nominal-type check).
- **Required property tests.** Fingerprint wrapping stable.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Strict type; unit lanes.
- **Acceptance criteria.** [ ] Every stage identity is a distinct nominal dataclass. [ ] No alias-as-identity. [ ] Centralized identities separate from FedAvg. [ ] `StageIdentity` composes distinct roles.
- **Completion evidence.** Changed files (`domain/artifacts/lineage.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; substitution is caught by strict typing.
- **Stop conditions.** None.
- **Deliverables.** Per-stage identity dataclasses.
- **Final review checklist.** [ ] Nominal, not structural.

#### P1-T014 — Implement resource, traffic-rate, and byte value objects

- **Ticket ID.** P1-T014
- **Title.** Implement resource, traffic-rate, and byte value objects
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `BatchSize`, `GradientAccumulationSteps`, `WorkerCount`, `ChunkRowCount`, `RamBudgetBytes`, `VramFraction`, `GpuIndex`, `NumericTolerance`, `ByteCount`, `DiskCapacity`, `BootstrapResampleCount`, `TrafficRate`, `TrafficRateUnit`, `SampleCount`, `ConfusionCount`, `CalibrationSampleCount`(+Ref), `RelativeArtifactPath`. `BatchSize`/`GradientAccumulationSteps` are fingerprinted; `WorkerCount` conditionally.
- **Objective.** Implement `BatchSize`, `GradientAccumulationSteps`, `WorkerCount`, `ChunkRowCount`, `RamBudgetBytes`, `VramFraction`, `GpuIndex`, `NumericTolerance`, `ByteCount`, `DiskCapacity`, `BootstrapResampleCount` (explicit, no default), `TrafficRate` (decimal + `TrafficRateUnit`), `SampleCount`, `ConfusionCount`, `CalibrationSampleCount`(+Ref), `RelativeArtifactPath`.
- **Why this ticket exists.** Encodes fingerprinted batch semantics, explicit (never-defaulted) bootstrap counts, strictly-positive traffic rates, and a traversal-safe relative path — all identity- or safety-bearing.
- **Authority references.** Arch §7 (VO table), §7.4 (immutable mapping fields), §16.6, §10 (bootstrap authority in §27 blockers).
- **Dependencies.** P1-T011.
- **Blocks.** P1-T026.
- **Downstream consumers.** P1-T026 (evaluation/operating-point/alert-burden result types) consumes these value objects directly.
- **Preconditions.** P1-T011 complete.
- **Inputs.** Arch §7, §7.4, §16.6, §10, §27.
- **Allowed scope.** `domain/runtime/admissibility.py`, `domain/artifacts/keys.py`/`references.py`, `domain/evaluation/alert_burden.py`.
- **Forbidden actions.** No default `BootstrapResampleCount`; no `..`/absolute/whitespace in `RelativeArtifactPath`; no zero/negative/NaN traffic rate; no live `dict` field.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen VOs with `__post_init__` checks; `RelativeArtifactPath` rejects traversal; `TrafficRate` strictly positive + supported unit.
- **Required unit tests.** `BootstrapResampleCount` requires explicit value.
- **Required property tests.** Range/finiteness; `RelativeArtifactPath` traversal rejection; `TrafficRate` positivity.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property; unit; strict type lanes.
- **Acceptance criteria.** [ ] `RelativeArtifactPath` rejects traversal. [ ] `BootstrapResampleCount` has no default. [ ] `TrafficRate` strictly positive. [ ] Batch VOs fingerprintable.
- **Completion evidence.** Changed files (`domain/runtime/admissibility.py`, `domain/artifacts/keys.py`/`references.py`, `domain/evaluation/alert_burden.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on invalid values; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Resource/traffic/byte value objects.
- **Final review checklist.** [ ] No hidden bootstrap default.

#### P1-T015 — Implement immutable typed collections and the object-dict prohibition

- **Ticket ID.** P1-T015
- **Title.** Implement immutable typed collections and the object-dict prohibition
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** naming-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ClientRoster`, `ClientCalibrationScoreMap`, `ClientTestScoreMap`, `ClientTemporalScoreMap`, `ClientEvaluationMap`, `ThresholdAssignmentSet`, `SeedTuple`/`SeedRoleTuple`/`SeedMap`/`ConfirmatorySeedCohort`, `EnumMap`, `MetricMap`, `ClientMap`, `ArtifactReferenceCollection`, `StageDependencyCollection`.
- **Objective.** Implement the immutable typed collections of Arch §10: `ClientRoster`, `ClientCalibrationScoreMap`, `ClientTestScoreMap`, `ClientTemporalScoreMap`, `ClientEvaluationMap`, `ThresholdAssignmentSet`, `SeedTuple`/`SeedRoleTuple`/`SeedMap`/`ConfirmatorySeedCohort`, `EnumMap`, `MetricMap`, `ClientMap`, `ArtifactReferenceCollection`, `StageDependencyCollection`, each validating its invariants at construction, and forbid object-shaped dictionaries in domain/application contracts.
- **Why this ticket exists.** Replaces every raw structured mapping with a named, validated type; a field-name-keyed dict is an unnamed object and is banned.
- **Authority references.** Arch §10, §7.4, §23 (object-shaped dictionaries rejected).
- **Dependencies.** P1-T011, P1-T012.
- **Blocks.** P1-T023.
- **Downstream consumers.** P1-T023 (scoring and split-scoped score-artifact specifications) consumes these collections directly; carriers (not identity-bearing).
- **Preconditions.** P1-T011, P1-T012 complete.
- **Inputs.** Arch §10, §7.4, §23.
- **Allowed scope.** Collection modules co-located with their capability per Arch §10.
- **Forbidden actions.** No `dict[str, Any]`/`Mapping[str, object]` in domain/application contracts; no junk-drawer `collections.py`; no foreign keys.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen collections storing immutable snapshots; roster-equality and lineage-role invariants validated at construction; `SeedTuple`≠`SeedRoleTuple`.
- **Required unit tests.** Object-dict absence in signatures (aided by architecture scan).
- **Required property tests.** Roster-key equality; ordering stability; duplicate rejection.
- **Required contract tests.** NONE.
- **Required architecture tests.** No `dict[str, Any]` in domain/application contracts.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property; unit; architecture lanes.
- **Acceptance criteria.** [ ] All §10 collections implemented with invariants. [ ] No object-shaped dict in contracts. [ ] `SeedTuple`/`SeedRoleTuple` distinct.
- **Completion evidence.** Changed files (collection modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on invariant breach; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Typed collection modules.
- **Final review checklist.** [ ] No junk-drawer module.

#### P1-T016 — Implement locked dispersion, quantile, and pooled-variance mathematics

- **Ticket ID.** P1-T016
- **Title.** Implement locked dispersion, quantile, and pooled-variance mathematics
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** threshold-policy-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `cv_fpr`, `pooled_variance` (with between-client mean-shift term), `fpr_target`, exact quantile helpers, `is_canonical_k`, eligibility helpers.
- **Objective.** Implement `domain/mathematics/dispersion.py` (`cv_fpr`, `pooled_variance` with the between-client mean-shift term), `quantiles.py` (`fpr_target`, exact quantile helpers), and `pooled_statistics.py` (`is_canonical_k`, eligibility helpers).
- **Why this ticket exists.** These are locked scientific formulas that must be exact and framework-free; the full pooled variance (with between-term) is a structural rule, not an option.
- **Authority references.** Arch §5.1, §7.1 (`is_canonical_k`), §9.2 (FedStats variance), §29.4; Road §10 (CV(FPR) definition), §17 (FedStats contract).
- **Dependencies.** P1-T011.
- **Blocks.** P1-T026, P2-T016.
- **Downstream consumers.** P1-T026 (evaluation/operating-point/alert-burden result types) and P2-T016 consume these pure functions directly.
- **Preconditions.** P1-T011 complete.
- **Inputs.** Arch §5.1, §7.1, §9.2, §29.4; Road §10.
- **Allowed scope.** `domain/mathematics/`.
- **Forbidden actions.** No simple pooled variance (without between-term); no configurable variance/tie toggle; no framework import.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Pure functions; CV(FPR) = σ/µ over eligible clients; full pooled variance `Σ n_k[σ_k²+(µ_k−µ_global)²]/Σ n_k`; exact quantiles.
- **Required unit tests.** Known-value checks for `cv_fpr`, `pooled_variance`, `fpr_target`, `is_canonical_k`.
- **Required property tests.** `cv_fpr` correctness; `pooled_variance` includes between-term; `fpr_target = 1 − q`; `is_canonical_k` only for K=3.
- **Required contract tests.** NONE.
- **Required architecture tests.** No framework import in `domain/mathematics/`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property; unit; strict type lanes.
- **Acceptance criteria.** [ ] Pooled variance includes the between-term. [ ] `cv_fpr` matches the locked definition. [ ] `is_canonical_k` true only for K=3. [ ] No framework import.
- **Completion evidence.** Changed files (`domain/mathematics/dispersion.py`, `quantiles.py`, `pooled_statistics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Zero-mean CV returns a typed degeneracy signal consumed by result types (P1-T026), never a divide-by-zero.
- **Stop conditions.** None (formulas are locked, not blockers).
- **Deliverables.** Locked mathematics modules.
- **Final review checklist.** [ ] Between-term present; no toggle.

#### P1-T017 — Implement Cliff's delta and effect-size pure functions

- **Ticket ID.** P1-T017
- **Title.** Implement Cliff's delta and effect-size pure functions
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `cliffs_delta`.
- **Objective.** Implement `domain/mathematics/effect_sizes.py::cliffs_delta` as a vetted, property-tested pure function (not in SciPy), with antisymmetry, `[−1, 1]` bounds, and correct tie handling.
- **Why this ticket exists.** Cliff's delta is descriptive secondary evidence and is not provided by SciPy; it must be an in-repo pure function.
- **Authority references.** Arch §4.1 (Cliff's delta in-repo), §5.1, §21.2 (dedicated properties).
- **Dependencies.** P1-T011.
- **Blocks.** P1-T027.
- **Downstream consumers.** P1-T027 (statistical/confirmatory/anchor-gate result types) is the sole immediate consumer.
- **Preconditions.** P1-T011 complete.
- **Inputs.** Arch §4.1, §5.1, §21.2.
- **Allowed scope.** `domain/mathematics/effect_sizes.py`.
- **Forbidden actions.** No framework import; no use of Cliff's delta as a confirmatory decision branch.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Pure `cliffs_delta`; deterministic; finite inputs.
- **Required unit tests.** Known-value tests.
- **Required property tests.** Antisymmetry, bounds in `[−1,1]`, correct ties.
- **Required contract tests.** NONE.
- **Required architecture tests.** No framework import in `domain/mathematics/effect_sizes.py`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Property; unit lanes.
- **Acceptance criteria.** [ ] Antisymmetric. [ ] Bounded `[−1,1]`. [ ] Correct ties. [ ] Descriptive-only (no confirmatory branch).
- **Completion evidence.** Changed files (`domain/mathematics/effect_sizes.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on non-finite input; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** `cliffs_delta` pure function.
- **Final review checklist.** [ ] Property-tested, framework-free.

#### P1-T018 — Implement locked domain constants and the protocol eligibility rule

- **Ticket ID.** P1-T018
- **Title.** Implement locked domain constants and the protocol eligibility rule
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** datp-protocol-guardian
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES`, `REGIME_D_MINIMUM_COVERAGE`, `REGIME_D_TEMPORAL_HISTORICAL_FRACTION`, `ProtocolEligibilitySpec`. Eligibility feeds evaluation identity.
- **Objective.** Implement the locked constants of Arch §7.5 (`PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES = 100`, `REGIME_D_MINIMUM_COVERAGE = 0.90`, `REGIME_D_TEMPORAL_HISTORICAL_FRACTION = 0.70`) and `ProtocolEligibilitySpec` as the sole authority for the minimum client-calibration count, with no configuration override.
- **Why this ticket exists.** The n_min=100 eligibility rule, 90% Regime-D coverage gate, and 70/30 temporal boundary are protocol definitions owned once; they must not be config-overridable.
- **Authority references.** Arch §7.5, §9.3 (eligibility), §11.4; Road §10 (n_min=100), §7 (Regime-D coverage), §11 (70/30).
- **Dependencies.** P1-T011, P1-T016.
- **Blocks.** P1-T026.
- **Downstream consumers.** P1-T026 (evaluation/operating-point/alert-burden result types) consumes these constants directly.
- **Preconditions.** P1-T011, P1-T016 complete.
- **Inputs.** Arch §7.5, §9.3, §11.4; Road §10, §7, §11.
- **Allowed scope.** `domain/mathematics/pooled_statistics.py`, `ProtocolEligibilitySpec` in the owning domain module.
- **Forbidden actions.** No config override of these constants; no per-dataset ingestion-minimum confusion; no alternate coverage/boundary value.
- **Required configuration or NONE.** NONE (these are definitions, not blockers).
- **Implementation responsibilities.** `Final` constants; `ProtocolEligibilitySpec(minimum_calibration_samples=...)`; eligibility classification helper.
- **Required unit tests.** Single ownership of the minimum; eligibility classification below/above threshold; constants not overridable.
- **Required property tests.** Eligibility monotonic in sample count.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] n_min=100 owned once, no override. [ ] Coverage 0.90 and fraction 0.70 locked. [ ] Eligibility classification correct.
- **Completion evidence.** Changed files (`domain/mathematics/pooled_statistics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; these are locked definitions, not blockers.
- **Stop conditions.** None.
- **Deliverables.** Locked constants and eligibility spec.
- **Final review checklist.** [ ] No config override.

#### P1-T019 — Implement dataset, partition, and split specifications

- **Ticket ID.** P1-T019
- **Title.** Implement dataset, partition, and split specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** data-pipeline-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `DatasetSpec`, `DatasetSourceInspectionResult`, `ClientPartitionSpec` (+closed strategy variants incl. `DirichletPartitionSpec`), `ClientPartitionResult`, the closed `SplitSpec` union (`TrainingSplitSpec`/`BenignCalibrationSplitSpec`/`TestSplitSpec`), `SplitCollectionSpec`, `SplitManifestResult`, `TemporalWindowSpec`/`TemporalBoundary`, `TemporalProtocolSpec`, `OneShotRecalibrationSpec`, `ConformalSplitSpec`. Dataset/partition/split identities.
- **Objective.** Implement `DatasetSpec`, `DatasetSourceInspectionResult`, `ClientPartitionSpec`(+closed strategy variants incl. `DirichletPartitionSpec`), `ClientPartitionResult`, the closed `SplitSpec` union (`TrainingSplitSpec`/`BenignCalibrationSplitSpec`/`TestSplitSpec`), `SplitCollectionSpec`, `SplitManifestResult`, `TemporalWindowSpec`/`TemporalBoundary`, `TemporalProtocolSpec`, `OneShotRecalibrationSpec`, `ConformalSplitSpec`.
- **Why this ticket exists.** Encodes benign-only calibration and TEST-cannot-fit-thresholds at the type level; Dirichlet fields exist only on the Dirichlet variant; temporal/conformal contracts are dedicated.
- **Authority references.** Arch §9.1 (spec table), §8.1 (`SplitCollectionSpec`), §7.5 (temporal locks).
- **Dependencies.** P1-T001, P1-T011.
- **Blocks.** P1-T028, P2-T005.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T005 consume these specs directly.
- **Preconditions.** P1-T001, P1-T011 complete.
- **Inputs.** Arch §9.1, §8.1, §7.5.
- **Allowed scope.** `domain/data/` spec modules.
- **Forbidden actions.** No attack-capable field on the calibration split; no generic boolean weakening calibration; no non-70/30 temporal boundary; TEST excluded from conformal fit.
- **Required configuration or NONE.** NONE (mapping in P1-T032).
- **Implementation responsibilities.** Frozen specs; closed unions with explicit tags; calibration variant has no label-policy field.
- **Required unit tests.** Calibration cannot carry attack rows; TEST cannot fit thresholds; conformal excludes TEST; canonical D-temporal fraction locked.
- **Required property tests.** Split-role exhaustiveness.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Calibration is benign-only by type. [ ] TEST cannot fit thresholds. [ ] Dirichlet fields isolated. [ ] Temporal fraction locked at 0.70.
- **Completion evidence.** Changed files (`domain/data/` spec modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on invalid split composition; stop if the first-70% train/calibration allocation is needed here (an inherited-semantics blocker, carried to readiness).
- **Stop conditions.** Stop if the first-70% train/calibration allocation is needed here (it is an inherited-semantics blocker; carry to readiness).
- **Deliverables.** Dataset/partition/split specs.
- **Final review checklist.** [ ] No attack-in-calibration path.

#### P1-T020 — Implement preprocessing and processed-split specifications

- **Ticket ID.** P1-T020
- **Title.** Implement preprocessing and processed-split specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** data-pipeline-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `PreprocessingSpec` (owns `PreprocessingChunkSpec` exclusively), `PreprocessingChunkSpec`, `FittedPreprocessorResult`, `ProcessedSplitResult`, `NormalizationStrategy`/`NormalizationScope`. Preprocessor/processed-split identities.
- **Objective.** Implement `PreprocessingSpec` (strategy/scope/fitted-stat policy, owns `PreprocessingChunkSpec` exclusively), `PreprocessingChunkSpec`, `FittedPreprocessorResult`, `ProcessedSplitResult`, `NormalizationStrategy`/`NormalizationScope`.
- **Why this ticket exists.** Fit rows are the authorized TRAIN rows only; preprocessing chunk sizing is owned once (never duplicated in budget/training/scoring); no TEST-derived statistic.
- **Authority references.** Arch §9.1, §6.2, §16.3 (two-pass fit), §29.4 (fitting on TEST unrepresentable).
- **Dependencies.** P1-T019.
- **Blocks.** P1-T028, P2-T007.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T007 consume these specs directly.
- **Preconditions.** P1-T019 complete.
- **Inputs.** Arch §9.1, §6.2, §16.3, §29.4.
- **Allowed scope.** `domain/data/preprocessing.py`.
- **Forbidden actions.** No fit on unauthorized rows; no TEST-derived stat; no chunk-size duplication in other specs.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen specs; `FittedPreprocessorResult` carries training-row-order checksum, no processed split, no TEST stat.
- **Required unit tests.** Fitted result contains no TEST statistic; chunk sizing owned once.
- **Required property tests.** Scope restricts fit to TRAIN.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Fit authorized to TRAIN only. [ ] No TEST-derived statistic. [ ] Chunk sizing owned once.
- **Completion evidence.** Changed files (`domain/data/preprocessing.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `PreprocessingError` on unauthorized fit rows (raised by the stage/adapter later); stop if the inherited preprocessing strategy/scope is unresolved and carry as a readiness blocker.
- **Stop conditions.** Stop if inherited preprocessing strategy/scope is unresolved; carry as a readiness blocker.
- **Deliverables.** Preprocessing specs.
- **Final review checklist.** [ ] No TEST leakage into fit.

#### P1-T021 — Implement model, federation, training, and batch specifications

- **Ticket ID.** P1-T021
- **Title.** Implement model, federation, training, and batch specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** federated-learning-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `AutoencoderSpec` (no BatchNorm), `FederationSpec`, `TrainingSpec` (owns `TrainingBatchSpec` exclusively), `TrainingBatchSpec`. Training/checkpoint identities.
- **Objective.** Implement `AutoencoderSpec` (no BatchNorm), `FederationSpec` (aggregation, local_epochs, participation, rounds_max, `fedprox_mu` absent for FEDAVG / strictly-positive frozen-grid member for FEDPROX), `TrainingSpec` (owns `TrainingBatchSpec` exclusively, personalization NONE for core ladder), `TrainingBatchSpec` (effective = micro × accumulation).
- **Why this ticket exists.** Encodes the fixed encoder, E=1 core, full participation, FedProx-only µ, and fingerprinted batch semantics; personalization is NONE on the core ladder.
- **Authority references.** Arch §9.1, §6.1/§6.2, §16.6, §29.1; Road §2, SB-02/SB-13.
- **Dependencies.** P1-T002.
- **Blocks.** P1-T028, P2-T008.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T008 consume these specs directly.
- **Preconditions.** P1-T002 complete.
- **Inputs.** Arch §9.1, §6.1, §6.2, §16.6, §29.1; Road §2, SB-02, SB-13.
- **Allowed scope.** `domain/learning/models.py`, `training.py`.
- **Forbidden actions.** No BatchNorm; no µ on FEDAVG; no partial participation; no batch-size duplication; no core-ladder personalization.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen specs; `effective_batch_size == micro × gradient_accumulation_steps` invariant; FedProx µ from frozen grid only.
- **Required unit tests.** No-BatchNorm; µ absent for FEDAVG, positive for FEDPROX; effective-batch invariant.
- **Required property tests.** Batch arithmetic.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] No BatchNorm. [ ] µ rules enforced. [ ] Full participation. [ ] Effective-batch invariant holds. [ ] Core personalization NONE.
- **Completion evidence.** Changed files (`domain/learning/models.py`, `training.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on µ misuse or batch inconsistency; stop if AE architecture/optimizer/scheduler/batch semantics are unresolved and carry as readiness blockers (Arch §27).
- **Stop conditions.** Stop if AE architecture/optimizer/scheduler/batch semantics are unresolved; carry as readiness blockers (Arch §27).
- **Deliverables.** Model/federation/training/batch specs.
- **Final review checklist.** [ ] Fixed-encoder identity representable only correctly.

#### P1-T022 — Implement checkpoint schedule, selection, and recovery specifications

- **Ticket ID.** P1-T022
- **Title.** Implement checkpoint schedule, selection, and recovery specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** federated-learning-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `CheckpointSchedule`, `CheckpointSelectionSpec` (REGIME_A_GLOBAL_PRIMARY only), `CheckpointCandidateResult`/`CheckpointSelectionResult`/`CheckpointSelectionArtifact`, `CheckpointDescriptor`, `RecoveryCheckpointPolicy`, `RecoveryState`. Checkpoint/selection/recovery identities.
- **Objective.** Implement `CheckpointSchedule` (rounds {25,50,75,100,125,150,200}), `CheckpointSelectionSpec` (REGIME_A_GLOBAL_PRIMARY only, candidate rounds, rule/tie-break versions), `CheckpointCandidateResult`/`CheckpointSelectionResult`/`CheckpointSelectionArtifact`, `CheckpointDescriptor`, `RecoveryCheckpointPolicy`, `RecoveryState`.
- **Why this ticket exists.** Encodes train-once/save-many, Regime-A-global selection with no forbidden evidence field (test AUROC/attack/Regime-D/FedProx/personalization/threshold cannot enter), and scientific vs recovery separation.
- **Authority references.** Arch §9.1, §17.1–17.3, §29.4; Road §10 (checkpoint protocol).
- **Dependencies.** P1-T002.
- **Blocks.** P1-T028, P2-T010.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T010 consume these specs directly.
- **Preconditions.** P1-T002 complete.
- **Inputs.** Arch §9.1, §17.1–17.3, §29.4; Road §10.
- **Allowed scope.** `domain/learning/checkpoints.py`.
- **Forbidden actions.** No per-regime selection member; no forbidden-evidence field on candidate/selection; recovery never selectable/citable.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen specs; candidate result has no attack/test-AUROC/Regime-D/FedProx/personalization/threshold field; recovery has compatibility identity and last-completed-round.
- **Required unit tests.** Forbidden fields absent from candidate/selection types; schedule fixed; recovery≠scientific.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Selection-artifact shape regression check against a fixed synthetic candidate set (replaces the former golden-test category for this ticket).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; integration (synthetic); strict type lanes.
- **Acceptance criteria.** [ ] Schedule = {25,…,200}. [ ] Regime-A-global selection only. [ ] No forbidden evidence field. [ ] Recovery non-citable.
- **Completion evidence.** Changed files (`domain/learning/checkpoints.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `CheckpointSelectionError` path defined for prohibited input (adapter/service level); stop if the Regime-A ranking/tie-break rule is unresolved and carry as a readiness blocker.
- **Stop conditions.** Stop if the Regime-A ranking/tie-break rule is unresolved; carry as a readiness blocker.
- **Deliverables.** Checkpoint/selection/recovery specs.
- **Final review checklist.** [ ] No leakage into selection.

#### P1-T023 — Implement scoring and split-scoped score-artifact specifications

- **Ticket ID.** P1-T023
- **Title.** Implement scoring and split-scoped score-artifact specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** data-pipeline-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ScoreGenerationSpec` (owns `ScoringBatchSpec`), `ScoringBatchSpec`, `ClientCalibrationScoreArtifact`, `ClientTestScoreArtifact`, `ClientTemporalScoreArtifact`, `CalibrationScoreArtifactSet`/`TestScoreArtifactSet`/`TemporalScoreArtifactSet`, `SplitScopedScoreBundle`. Calibration/test/temporal scoring identities.
- **Objective.** Implement `ScoreGenerationSpec` (owns `ScoringBatchSpec`), `ScoringBatchSpec`, `ClientCalibrationScoreArtifact` (no attack field), `ClientTestScoreArtifact` (benign+attack refs committed atomically as one aggregate), `ClientTemporalScoreArtifact`, the `CalibrationScoreArtifactSet`/`TestScoreArtifactSet`/`TemporalScoreArtifactSet`, and `SplitScopedScoreBundle`.
- **Why this ticket exists.** Makes calibration/test leakage a type error; attack scores exist only on TEST artifacts; the benign/attack pair is one committed aggregate, never a loose pair.
- **Authority references.** Arch §9.2 (score specs and atomic pair protocol), §13.3 (reuse lineage), §29.1.
- **Dependencies.** P1-T002, P1-T015.
- **Blocks.** P1-T024, P2-T011.
- **Downstream consumers.** P1-T024 (threshold-construction union) and P2-T011 consume these artifacts directly.
- **Preconditions.** P1-T002, P1-T015 complete.
- **Inputs.** Arch §9.2, §13.3, §29.1.
- **Allowed scope.** `domain/learning/scores.py`.
- **Forbidden actions.** No attack field on calibration; no loose benign/attack pair; no threshold-config field on scoring; scoring batch owned once.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen artifacts carrying full lineage/hashes/row-order checksums; test artifact holds two immutable `ArtifactRef` members plus aggregate manifest hash.
- **Required unit tests.** Calibration has no attack field; test pair is one aggregate.
- **Required property tests.** NONE.
- **Required contract tests.** Threshold constructor rejects a test-score set; evaluator rejects a calibration set.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; strict type lanes.
- **Acceptance criteria.** [ ] Calibration has no attack field. [ ] Test benign/attack committed as one aggregate. [ ] Scoring batch owned once. [ ] Role types disjoint.
- **Completion evidence.** Changed files (`domain/learning/scores.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ScoringError`/`PartialArtifactError` paths defined for adapter use; stop if score batch semantics are unresolved and carry as a readiness blocker.
- **Stop conditions.** Stop if score batch semantics are unresolved; carry as a readiness blocker.
- **Deliverables.** Scoring and score-artifact specs.
- **Final review checklist.** [ ] Leakage is a type error.

#### P1-T024 — Implement the threshold-construction union and suite specifications

- **Ticket ID.** P1-T024
- **Title.** Implement the threshold-construction union and suite specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** threshold-policy-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** The closed `ThresholdConstructionSpec` union (nine FedAvg-derived variants) with the `ThresholdConstructionKind` tag, `SharedThresholdSpec`/`LocalThresholdSpec`/`FamilyThresholdSpec`, `ShrinkageThresholdSpec`/`CalibrationSizeFallbackThresholdSpec`/`ConformalThresholdSpec`, `FedStatsBenignThresholdSpec`, `ThresholdSuiteSpec`, `ThresholdAssignment`. Threshold identity.
- **Objective.** Implement the closed `ThresholdConstructionSpec` union (nine FedAvg-derived variants) with the explicit `ThresholdConstructionKind` tag, `SharedThresholdSpec`/`LocalThresholdSpec`/`FamilyThresholdSpec`, `ShrinkageThresholdSpec`/`CalibrationSizeFallbackThresholdSpec`/`ConformalThresholdSpec`, `FedStatsBenignThresholdSpec`, `ThresholdSuiteSpec`, `ThresholdAssignment`; B0's `CentralizedModelComparatorSpec` is excluded from this union.
- **Why this ticket exists.** Encodes B1 = unweighted mean of eligible local-q thresholds; pooled/weighted are separate variants; the variant is never inferred from optional-field presence; B0 is not a ladder member.
- **Authority references.** Arch §9.2, §6.10 (explicit discriminator), §29.4.
- **Dependencies.** P1-T003, P1-T023.
- **Blocks.** P1-T025, P2-T013.
- **Downstream consumers.** P1-T025 (B4 clustering and federated-statistics specifications) and P2-T013 consume this union directly.
- **Preconditions.** P1-T003, P1-T023 complete.
- **Inputs.** Arch §9.2, §6.10, §29.4.
- **Allowed scope.** `domain/thresholding/policies.py`, `variants.py`, `federated_statistics.py`.
- **Forbidden actions.** No pseudo-discriminated variant; no B0 in the union; no test/attack score field on a construction; no fixed-k as primary FedStats.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen union with `kind` tag; suite holds ordered constructions over one calibration score set; assignment records the exact `CalibrationScoreArtifactId`.
- **Required unit tests.** Variant inferred only from tag; construction rejects test/attack score; B0 excluded.
- **Required property tests.** B1 = unweighted mean.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Nine-variant closed union with explicit tag. [ ] B0 excluded. [ ] B1 unweighted mean. [ ] No test/attack score field.
- **Completion evidence.** Changed files (`domain/thresholding/policies.py`, `variants.py`, `federated_statistics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError` for missing field; exhaustive `assert_never` at consumers.
- **Stop conditions.** None.
- **Deliverables.** Threshold construction union and suite specs.
- **Final review checklist.** [ ] Tag-discriminated only.

#### P1-T025 — Implement B4 clustering and federated-statistics specifications

- **Ticket ID.** P1-T025
- **Title.** Implement B4 clustering and federated-statistics specifications
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `B4ClusteringSpec` (fixed fingerprint `[mean,std,skew,p95]`), `ClusterThresholdAggregationSpec`, `ClusterAssignmentArtifact`, `RobustClusterMedianThresholdSpec` (optional), `FedStatsBenignThresholdSpec`. Threshold identity (B4/FedStats).
- **Objective.** Implement `B4ClusteringSpec` (ordered fixed fingerprint `[mean,std,skew,p95]`, locked scaler/fit-scope, k-means++, K=3, locked `n_init`/`max_iter`, derived random state), `ClusterThresholdAggregationSpec`, `ClusterAssignmentArtifact`, `RobustClusterMedianThresholdSpec` (optional), and the locked `FedStatsBenignThresholdSpec` (candidate grid, full pooled variance, matched exceedance, larger-k tie).
- **Why this ticket exists.** Encodes canonical B4 (K=3, fixed p95 fingerprint, q never a fingerprint field) and the FedStats structural algorithm rules that no boolean can disable.
- **Authority references.** Arch §9.2, §16.2 (exact KMeans), §29.4; Road §4, §17 (FedStats contract), SB-26/SB-27/SB-32.
- **Dependencies.** P1-T024.
- **Blocks.** P2-T015, P4-T018.
- **Downstream consumers.** P2-T015 and P4-T018 consume these B4/FedStats specs directly.
- **Preconditions.** P1-T024 complete.
- **Inputs.** Arch §9.2, §16.2, §29.4; Road §4, §17, SB-26, SB-27, SB-32.
- **Allowed scope.** `domain/thresholding/clustering.py`, `federated_statistics.py`.
- **Forbidden actions.** No q in the fingerprint; no caller-controlled K/algorithm for canonical B4; no simple pooled variance; no configurable tie-break; no MiniBatchKMeans path.
- **Required configuration or NONE.** NONE (exploratory K uses a separate authorized profile).
- **Implementation responsibilities.** Frozen specs; canonical K=3; q-specific thresholds average member local-q thresholds without reclustering; FedStats reports within/between terms and between_ratio.
- **Required unit tests.** q not a fingerprint field; FedStats variance includes between-term; larger-k tie.
- **Required property tests.** Canonical K derivation.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Fixed synthetic-fingerprint regression: a fixed fingerprint set produces a stable assignment and stable adjusted-Rand index (replaces the former golden-test category for this ticket).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (synthetic); unit; property; strict type lanes.
- **Acceptance criteria.** [ ] K=3 canonical, fixed fingerprint. [ ] q not a fingerprint field. [ ] FedStats full variance + larger-k tie. [ ] No MiniBatchKMeans.
- **Completion evidence.** Changed files (`domain/thresholding/clustering.py`, `federated_statistics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; unresolved scaler/constants block print-grade execution (readiness); stop if the B4 scaler/`n_init`/`max_iter` constants are unresolved and carry as readiness blockers.
- **Stop conditions.** Stop if the B4 scaler/`n_init`/`max_iter` constants are unresolved; carry as readiness blockers.
- **Deliverables.** B4 clustering and FedStats specs.
- **Final review checklist.** [ ] No caller override of canonical B4.

#### P1-T026 — Implement evaluation, operating-point, and alert-burden result types

- **Ticket ID.** P1-T026
- **Title.** Implement evaluation, operating-point, and alert-burden result types
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ClientEvaluationResult`, `ValidCvResult`/`UndefinedCvResult`/`CvOutcome`, `EligibleClientSet`, `EligibilityCoverageResult`, `ConformalCoverageResult`, `FleetDispersionResult`, `FleetDetectionResult`, `FleetEquityResult`, `ClusterDispersionResult`, `PolicyEvaluationResult`, `TemporalPolicyEvaluationResult`, `TrafficRateEvidence` union, `AlertBurdenResult`. Evaluation identity.
- **Objective.** Implement `ClientEvaluationResult`, `ValidCvResult`/`UndefinedCvResult`/`CvOutcome`, `EligibleClientSet`, `EligibilityCoverageResult`, `ConformalCoverageResult`, `FleetDispersionResult`, `FleetDetectionResult`, `FleetEquityResult`, `ClusterDispersionResult`, `PolicyEvaluationResult`, `TemporalPolicyEvaluationResult`, `TrafficRateEvidence` union, `AlertBurdenResult`, `MetricSpec` wiring.
- **Why this ticket exists.** Encodes eligible-only dispersion with a shared `EligibleClientSet`, typed zero-mean CV degeneracy (never an exception), and evidence-required alert burden; eligibility and conformal coverage have disjoint identities.
- **Authority references.** Arch §9.3, §29.1, §29.4 (invalid states 19–20); Road §10.
- **Dependencies.** P1-T004, P1-T014, P1-T016, P1-T018.
- **Blocks.** P1-T028, P2-T016.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T016 consume these result types directly.
- **Preconditions.** P1-T004, P1-T014, P1-T016, P1-T018 complete.
- **Inputs.** Arch §9.3, §29.1, §29.4; Road §10.
- **Allowed scope.** `domain/evaluation/operating_points.py`, `alert_burden.py`.
- **Forbidden actions.** No policy-specific eligible population; no eligibility/conformal metric substitution; no alert burden without evidence; no CV exception for expected zero mean.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen result types; `EligibleClientSet` built once per paired comparison; `UndefinedCvResult` carries absolute-dispersion companions and a `ClaimOutcome`.
- **Required unit tests.** Paired policies share one `EligibleClientSet`; eligibility≠conformal coverage; alert burden requires evidence.
- **Required property tests.** Confusion-count derivations recomputable.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Shared eligible set per paired comparison. [ ] Typed zero-mean CV. [ ] Eligibility/conformal disjoint. [ ] Alert burden evidence-gated.
- **Completion evidence.** Changed files (`domain/evaluation/operating_points.py`, `alert_burden.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Zero-mean CV → `UndefinedCvResult`; missing traffic evidence fails alert-burden construction (not a client-eligibility reason); stop if the zero-mean CV policy is unresolved and carry as a readiness blocker.
- **Stop conditions.** Stop if the zero-mean CV policy is unresolved; carry as a readiness blocker.
- **Deliverables.** Evaluation/operating-point/alert-burden result types.
- **Final review checklist.** [ ] No CV exception path.

#### P1-T027 — Implement statistical, confirmatory, and anchor-gate result types

- **Ticket ID.** P1-T027
- **Title.** Implement statistical, confirmatory, and anchor-gate result types
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** statistics-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `PairedDeltaResult`, `ValidBootstrapIntervalResult`/`DegenerateBootstrapIntervalResult`/`BootstrapIntervalOutcome`, `WilcoxonSignedRankResult`/`CliffsDeltaResult`, `AbsorptionResult`, `TemporalRecoveryResult`, `ConfirmatoryAnalysisResult`, `StatisticalAnalysisResult` union, `AnchorReferenceInterval`/`AnchorReproductionGateSpec`/`AnchorReproductionResult`. Statistical identity.
- **Objective.** Implement `PairedDeltaResult` (Δ = B1 − B2 locked), `ValidBootstrapIntervalResult`/`DegenerateBootstrapIntervalResult`/`BootstrapIntervalOutcome`, `WilcoxonSignedRankResult`/`CliffsDeltaResult`, `AbsorptionResult`, `TemporalRecoveryResult`, `ConfirmatoryAnalysisResult` (pass rule), the closed `StatisticalAnalysisResult` union, and `AnchorReferenceInterval`/`AnchorReproductionGateSpec`/`AnchorReproductionResult`.
- **Why this ticket exists.** Encodes the positive-direction BCa pass rule, typed BCa degeneracy (never silent percentile downgrade), and the five-seed anchor honesty gate.
- **Authority references.** Arch §9.3, §16.5 (degeneracy), §29.1; Road §3, §5.1, §10 (seed-extension honesty rule).
- **Dependencies.** P1-T005, P1-T017.
- **Blocks.** P1-T028, P2-T018.
- **Downstream consumers.** P1-T028 (scientific-protocol and policy aggregates) and P2-T018 consume these result types directly.
- **Preconditions.** P1-T005, P1-T017 complete.
- **Inputs.** Arch §9.3, §16.5, §29.1; Road §3, §5.1, §10.
- **Allowed scope.** `domain/evaluation/statistical_results.py`.
- **Forbidden actions.** No silent BCa→percentile; no confirmatory Wilcoxon/Cliff branch; no suppression of a less-favorable ten-seed result.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen result types; `ConfirmatoryAnalysisResult.passes` iff BCa CI excludes zero positive; degeneracy is a typed result, not an exception.
- **Required unit tests.** Pass rule; degeneracy typed; Δ = B1 − B2.
- **Required property tests.** Interval direction logic.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Pass rule = positive-direction BCa excludes zero. [ ] Degeneracy typed, never downgraded. [ ] Δ = B1 − B2 locked. [ ] Anchor gate encodes the ~20%-wider rule.
- **Completion evidence.** Changed files (`domain/evaluation/statistical_results.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `StatisticsError` reserved for genuinely unexpected failure only; stop if the operational meaning of "material movement toward zero" is unresolved and carry as a readiness blocker (Arch §27).
- **Stop conditions.** Stop if the operational meaning of "material movement toward zero" is unresolved; carry as a readiness blocker (Arch §27).
- **Deliverables.** Statistical/confirmatory/anchor-gate result types.
- **Final review checklist.** [ ] No hidden percentile substitution.

#### P1-T028 — Implement the scientific-protocol and policy aggregates

- **Ticket ID.** P1-T028
- **Title.** Implement the scientific-protocol and policy aggregates
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ScientificProtocolSpec` (composed nested specs, resource_costs optional), `ExecutionPolicy`, `ArtifactPolicy`, `ReportingPolicy`. Composes all stage-affecting specs.
- **Objective.** Implement `ScientificProtocolSpec` (composed nested specs, resource_costs optional) and the three policy aggregates `ExecutionPolicy`/`ArtifactPolicy`/`ReportingPolicy`, ensuring scientific and operational concerns never mix in one class and each field enters only the earliest stage identity it can affect.
- **Why this ticket exists.** The scientific meaning of an experiment lives entirely inside `ScientificProtocolSpec`; execution/artifact/reporting are separate policies; this composition drives the lineage model.
- **Authority references.** Arch §8.1, §8.2, §8.4.
- **Dependencies.** P1-T019, P1-T020, P1-T021, P1-T022, P1-T023, P1-T024, P1-T026, P1-T027.
- **Blocks.** P1-T029.
- **Downstream consumers.** P1-T029 (experiment identity/profile/cell aggregates) composes this ticket's aggregates directly.
- **Preconditions.** All listed dependency tickets complete.
- **Inputs.** Arch §8.1, §8.2, §8.4.
- **Allowed scope.** `domain/experiments/protocols.py`, `specifications.py`.
- **Forbidden actions.** No universal context object; no scientific/operational mixing; no `ThresholdSuiteSpec` owning scoring config.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen aggregates; `SplitCollectionSpec` holds exactly one train/calibration/test; `EvaluationSuiteSpec` alert-burden requires evidence; `StatisticalAnalysisSpec` locked for confirmatory cells.
- **Required unit tests.** Only fields reachable through `ScientificProtocolSpec` enter fingerprints; policy separation.
- **Required property tests.** Each field enters earliest affecting identity only.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Scientific meaning fully inside `ScientificProtocolSpec`. [ ] Policies separate. [ ] Alert-burden evidence-gated. [ ] Confirmatory statistics locked.
- **Completion evidence.** Changed files (`domain/experiments/protocols.py`, `specifications.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError` on invalid composition; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Protocol and policy aggregates.
- **Final review checklist.** [ ] No context object.

#### P1-T029 — Implement experiment identity/profile/cell aggregates and closed profiles

- **Ticket ID.** P1-T029
- **Title.** Implement experiment identity/profile/cell aggregates and closed profiles
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `ExperimentIdentity`, `ExperimentSpec`, `ExperimentProfileSpec`, `CentralizedModelComparatorProfileSpec`, `ExperimentCell`, `RegimeCompatibilitySpec`, `SweepSpec`, `ConfirmatoryExperimentProfileSpec` (E-C1 locked). Experiment/cell identity.
- **Objective.** Implement `ExperimentIdentity`, `ExperimentSpec`, `ExperimentProfileSpec`, `CentralizedModelComparatorProfileSpec`, `ExperimentCell`, `RegimeCompatibilitySpec`, `SweepSpec`, `ConfirmatoryExperimentProfileSpec` (E-C1 locked), and the profile catalogue holding the roadmap's fixed grids (E-S2 q, E-S3 α, E-V1 n, E-V2 λ, E-V3 α=0.05, E-Q5 k) and locked bands/gates.
- **Why this ticket exists.** Named experiments are executable only through closed profiles; a changed scientific fingerprint is a validation failure, not another lineage; E-C1 admits only its confirmatory shape.
- **Authority references.** Arch §8.3, §8.4, §29.1; Road §9 (matrix), §9.3 (grids/bands).
- **Dependencies.** P1-T006, P1-T007, P1-T028.
- **Blocks.** P1-T031, P4-T001.
- **Downstream consumers.** P1-T031 (Pydantic boundary schemas) and P4-T001 consume these aggregates directly.
- **Preconditions.** P1-T006, P1-T007, P1-T028 complete.
- **Inputs.** Arch §8.3, §8.4, §29.1; Road §9, §9.3.
- **Allowed scope.** `domain/experiments/identities.py`, `specifications.py`, `claims.py`, `feasibility.py`.
- **Forbidden actions.** No caller-supplied scientific protocol under a named id; no E-C1 non-confirmatory arm; no B0 through the FedAvg profile path; no seed values invented (seed plan is authoritative reference).
- **Required configuration or NONE.** Profile catalogue values from the roadmap only; absent values remain explicit readiness blockers.
- **Implementation responsibilities.** Frozen profiles; role/tier invariant enforced; `RegimeCompatibilitySpec` closed mapping; B-a as `ArchitectureCatalogueId`; `authorized_seed_plan` references the resolved authoritative seed specification.
- **Required unit tests.** E-C1 rejects non-confirmatory additions; unauthorized dataset/regime/policy/grid rejected; B0 uses the centralized profile only.
- **Required property tests.** Sweep expansion produces only authorized cells.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Named cells only from closed profiles. [ ] E-C1 confirmatory-only. [ ] Roadmap grids present; absent values are blockers. [ ] No invented seeds.
- **Completion evidence.** Changed files (`domain/experiments/identities.py`, `specifications.py`, `claims.py`, `feasibility.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DomainValidationError`/readiness blocker on unauthorized cell; stop if a required grid/band value is absent from the roadmap and carry as a readiness blocker.
- **Stop conditions.** Stop if a required grid/band value is absent from the roadmap; carry as a readiness blocker.
- **Deliverables.** Experiment identity/profile/cell aggregates.
- **Final review checklist.** [ ] No unauthorized cell representable.

#### P1-T030 — Implement the DatpCoreError hierarchy and typed error families

- **Ticket ID.** P1-T030
- **Title.** Implement the DatpCoreError hierarchy and typed error families
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** domain
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `DatpCoreError` and every error family of Arch §20.1 (config/domain/data/execution/modeling/federation/scoring/thresholds/readiness/evaluation/statistics/artifacts/storage/provenance/lineage/determinism/feasibility/planning/testing/environment/reporting).
- **Objective.** Implement `domain/errors.py` with `DatpCoreError` and every error family of Arch §20.1 (config/domain/data/execution/modeling/federation/scoring/thresholds/readiness/evaluation/statistics/artifacts/storage/provenance/lineage/determinism/feasibility/planning/testing/environment/reporting), each carrying typed context and a `FailureDisposition`.
- **Why this ticket exists.** Scientific runs fail loudly with typed context; raw framework exceptions never cross into application/domain; disposition drives retry/lifecycle.
- **Authority references.** Arch §20.1, §20.2, §20.3 (no `Result[T,E]` monad).
- **Dependencies.** P0-T026.
- **Blocks.** P1-T034, P1-T037.
- **Downstream consumers.** P1-T034 (data/learning/scoring/thresholding application ports) and P1-T037 (pipeline stage functions) raise these typed errors throughout.
- **Preconditions.** P0-T026 complete.
- **Inputs.** Arch §20.1, §20.2, §20.3.
- **Allowed scope.** `domain/errors.py`.
- **Forbidden actions.** No bare-string errors; no one-class-per-message; no exception swallowing; no monadic outcome layer.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Frozen-context error classes; one `detail: str` per family; dispositions per Arch §20.1.
- **Required unit tests.** Each family carries typed context and disposition; CUDA-OOM disposition is STAGE_BLOCKING/terminal; degeneracy is not raised via `StatisticsError`.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; strict type lanes.
- **Acceptance criteria.** [ ] All Arch §20.1 families present with typed context. [ ] Dispositions correct. [ ] No `Result` monad. [ ] No bare-string errors.
- **Completion evidence.** Changed files (`domain/errors.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** This ticket defines the vocabulary consumed everywhere; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Error hierarchy.
- **Final review checklist.** [ ] Fail-loudly, typed.

#### P1-T031 — Implement Pydantic boundary schemas and discriminated unions

- **Ticket ID.** P1-T031
- **Title.** Implement Pydantic boundary schemas and discriminated unions
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** configuration
- **Owner.** configuration-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `config/schemas/{scientific,execution,artifacts,reporting}.py` Pydantic v2 boundary schemas and discriminated unions.
- **Objective.** Implement `config/schemas/{scientific,execution,artifacts,reporting}.py` Pydantic v2 boundary schemas with discriminated unions for policy-specific fields, one schema owner per field, targeting the three fingerprint categories.
- **Why this ticket exists.** External configuration is validated only at the boundary; no Pydantic model crosses into application/domain/analysis; discriminated unions carry explicit tags.
- **Authority references.** Arch §4.1, §11, §11.1–11.4, §3.2 (config→domain only).
- **Dependencies.** P1-T029.
- **Blocks.** P1-T032.
- **Downstream consumers.** P1-T032 (YAML loading/override composition/mapping) is the sole immediate consumer.
- **Preconditions.** P1-T029 complete.
- **Inputs.** Arch §4.1, §11, §11.1–11.4, §3.2.
- **Allowed scope.** `config/schemas/`.
- **Forbidden actions.** No Pydantic model beyond the mapping boundary; no god-config; no hidden defaults; no `use_full_pooled_variance`/tie-break boolean; no variant inferred from optional-field presence.
- **Required configuration or NONE.** Schema definitions only.
- **Implementation responsibilities.** Section schemas; discriminated unions with explicit tags; `EvaluationConfig.primary` must be CV_FPR; `StatisticalConfig` confirmatory must be BCa/0.95/ten.
- **Required unit tests.** Discriminated-union tag required; CV_FPR primary enforced; confirmatory statistics locked; no hidden default.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** No Pydantic beyond config.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; architecture; strict type lanes.
- **Acceptance criteria.** [ ] One schema owner per field. [ ] Discriminated tags explicit. [ ] CV_FPR primary + confirmatory lock. [ ] No hidden default/boolean toggle.
- **Completion evidence.** Changed files (`config/schemas/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ConfigurationError` (RUN_BLOCKING) at load on invalid schema; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Config boundary schemas.
- **Final review checklist.** [ ] Pydantic confined to config.

#### P1-T032 — Implement YAML loading, override composition, and schema-to-domain mapping

- **Ticket ID.** P1-T032
- **Title.** Implement YAML loading, override composition, and schema-to-domain mapping
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** configuration
- **Owner.** configuration-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `config/loader.py`, `config/compose.py`, `config/mapping/{scientific,execution,artifacts,reporting}.py` pure `map_*(schema) -> DomainSpec` functions, `resolve_experiment_profile`. Produces domain specs (no config type survives mapping).
- **Objective.** Implement `config/loader.py` (YAML→schema), `config/compose.py` (explicit base+override, single precedence), and `config/mapping/{scientific,execution,artifacts,reporting}.py` pure `map_*(schema) -> DomainSpec` functions plus `resolve_experiment_profile`.
- **Why this ticket exists.** After mapping, no configuration type exists in the running system; profiles resolve before their closed cells map; B0/FedProx/temporal mapping rules are enforced here.
- **Authority references.** Arch §3.4, §11.4, §12.1.
- **Dependencies.** P1-T031.
- **Blocks.** P1-T036, P2-T003.
- **Downstream consumers.** P1-T036 (persistence/runtime application ports) and P2-T003 consume mapped domain specs directly.
- **Preconditions.** P1-T031 complete.
- **Inputs.** Arch §3.4, §11.4, §12.1.
- **Allowed scope.** `config/loader.py`, `compose.py`, `mapping/`.
- **Forbidden actions.** No YAML parsing outside config; no ambiguous override precedence; no B0 through a FedAvg arm; no FedProx µ=0/copied/post-hoc; no non-70/30 temporal; no seed value invented.
- **Required configuration or NONE.** Mapping functions consume `configs/` external data.
- **Implementation responsibilities.** Pure mapping to frozen specs; profile-first resolution; canonical D-temporal mapping rejects pseudo-time; unresolved fields accepted for DEVELOPMENT/SMOKE only.
- **Required unit tests.** Profile-first resolution; B0 mapper distinct; FedProx µ rules; temporal pseudo-time rejected; override precedence deterministic.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Resolved-configuration shape regression on a fixed synthetic override composition (replaces the former golden-test category for this ticket).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; integration (synthetic); strict type lanes.
- **Acceptance criteria.** [ ] No config type survives mapping. [ ] Single override precedence. [ ] B0/FedProx/temporal mapping rules enforced. [ ] No YAML parsing outside config.
- **Completion evidence.** Changed files (`config/loader.py`, `compose.py`, `mapping/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ConfigurationError` on invalid mapping; unresolved fields rejected for SCIENTIFIC/PRINT_GRADE.
- **Stop conditions.** None.
- **Deliverables.** Loader/compose/mapping modules.
- **Final review checklist.** [ ] Pure mapping, deterministic.

#### P1-T033 — Implement resolved-configuration recording and the typed spec-diff

- **Ticket ID.** P1-T033
- **Title.** Implement resolved-configuration recording and the typed spec-diff
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** configuration
- **Owner.** configuration-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ResolvedConfigurationArtifact`, `ResolvedSpecDiffer.compare`, `ScientificSpecificationChange`/`ExecutionPolicyChange`/`EnvironmentChange`. Resolved-configuration identity; spec-diff yields `ReuseImpact`.
- **Objective.** Implement `ResolvedConfigurationArtifact` recording and `ResolvedSpecDiffer.compare` producing typed `ScientificSpecificationChange`/`ExecutionPolicyChange`/`EnvironmentChange` variants, each with affected stage identities and one `ReuseImpact`.
- **Why this ticket exists.** Reuse/invalidation decisions depend on a field-by-field typed diff (not a recursive dict diff); a change classifies as training/scoring/threshold/eval-only/no-output-impact.
- **Authority references.** Arch §11.5, §6.3 (`ReuseImpact`), §13.
- **Dependencies.** P1-T032.
- **Blocks.** P1-T036, P5-T005.
- **Downstream consumers.** P1-T036 (persistence/runtime application ports) and P5-T005 consume this typed diff directly.
- **Preconditions.** P1-T032 complete.
- **Inputs.** Arch §11.5, §6.3, §13.
- **Allowed scope.** `config/` diff/recording and the domain change/impact types.
- **Forbidden actions.** No recursive dictionary diff; the diff never mutates a spec or unlocks reuse.
- **Required configuration or NONE.** NONE beyond recording.
- **Implementation responsibilities.** Pure `compare`; typed change variants; resolved-config artifact recorded with identity/schema version.
- **Required unit tests.** A threshold-only change yields THRESHOLD_INVALIDATED; a machine path yields NO_OUTPUT_IMPACT; diff never mutates.
- **Required property tests.** Change classification stable.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Typed spec-diff with `ReuseImpact`. [ ] No recursive dict diff. [ ] Diff is pure. [ ] Resolved config recorded with identity.
- **Completion evidence.** Changed files (`config/` diff/recording modules); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; the diff is a pure function.
- **Stop conditions.** None.
- **Deliverables.** Resolved-config recording and spec-diff.
- **Final review checklist.** [ ] Impact classification correct.

#### P1-T034 — Implement data/learning/scoring/thresholding application ports

- **Ticket ID.** P1-T034
- **Title.** Implement data/learning/scoring/thresholding application ports
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** implementation-engineer
- **Supporting agents.** data-pipeline-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `DatasetSourceInspector`, `ClientPartitioner`, `SplitManifestBuilder`, `PreprocessorFitter`, `ProcessedSplitMaterializer`, `FederatedTrainer`, `CentralizedModelTrainer`, `ScoreGenerator`, `ThresholdConstructor`, `ThresholdStrategy`, `ClusteringStrategy`, `QuantileEstimator` (Protocols; no framework carrier).
- **Objective.** Implement `application/ports/{data,learning,scoring,thresholding}.py` Protocols with dedicated typed requests/results: `DatasetSourceInspector`, `ClientPartitioner`, `SplitManifestBuilder`, `PreprocessorFitter`, `ProcessedSplitMaterializer`, `FederatedTrainer`, `CentralizedModelTrainer`, `ScoreGenerator`, `ThresholdConstructor`, `ThresholdStrategy`, `ClusteringStrategy`, `QuantileEstimator`.
- **Why this ticket exists.** Ports exist only at genuine variation points; contracts exchange framework-neutral descriptors; calibration/test leakage is a type error (score generator returns typed sets; constructor takes only calibration set).
- **Authority references.** Arch §12.2, §9.6 (framework confinement), §9.7.
- **Dependencies.** P1-T028, P1-T030.
- **Blocks.** P1-T037, P1-T043.
- **Downstream consumers.** P1-T037 (pipeline stage functions) and P1-T043 (PyTorch AE model/device adapters) implement/consume these ports directly.
- **Preconditions.** P1-T028, P1-T030 complete.
- **Inputs.** Arch §12.2, §9.6, §9.7.
- **Allowed scope.** `application/ports/data.py`, `learning.py`, `scoring.py`, `thresholding.py`.
- **Forbidden actions.** No framework carrier in a port signature; no generic `put/get/compute`; no test/attack score field on the threshold-construction request.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Protocols with one named request/result each; distinct calibration/test/temporal score methods.
- **Required unit tests.** Threshold constructor request has no test/attack field.
- **Required property tests.** NONE.
- **Required contract tests.** Contract scaffolding for later adapter conformance (full suites in P1-T037/adapters).
- **Required architecture tests.** No framework object in a port signature.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Architecture; unit; strict type lanes.
- **Acceptance criteria.** [ ] One named request/result per method. [ ] No framework carrier. [ ] Constructor cannot receive test/attack scores. [ ] Distinct centralized trainer port.
- **Completion evidence.** Changed files (`application/ports/data.py`, `learning.py`, `scoring.py`, `thresholding.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Ports raise the typed errors of P1-T030; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Data/learning/scoring/thresholding ports.
- **Final review checklist.** [ ] Framework-neutral.

#### P1-T035 — Implement statistics/reporting/telemetry application ports

- **Ticket ID.** P1-T035
- **Title.** Implement statistics/reporting/telemetry application ports
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** implementation-engineer
- **Supporting agents.** statistics-auditor, report-output-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `StatisticalProcedureRunner`, `ReportRenderer`, `EventSink`, `StructuredEvent`/`EventContext`/typed detail envelope (application-facing use).
- **Objective.** Implement `application/ports/{statistics,reporting,telemetry}.py`: `StatisticalProcedureRunner`, `ReportRenderer`, `EventSink`, plus the `StructuredEvent`/`EventContext`/typed detail envelope.
- **Why this ticket exists.** Statistics is SciPy-backed behind a port; rendering is an infrastructure sink; events are typed and never the scientific source of truth.
- **Authority references.** Arch §12.2, §19.1, §22.
- **Dependencies.** P1-T027, P1-T051, P1-T030.
- **Blocks.** P1-T065, P1-T067.
- **Downstream consumers.** P1-T065 (structured telemetry adapter) and P1-T067 (report renderers) implement/consume these ports directly. P1-T049 (analysis specification layer) does not consume these ports — Arch §3.5 confines `analysis` to a `domain`-only import, with no application-port dependency of any kind.
- **Preconditions.** P1-T027, P1-T051, P1-T030 complete.
- **Inputs.** Arch §12.2, §19.1, §22.
- **Allowed scope.** `application/ports/statistics.py`, `reporting.py`, `telemetry.py`.
- **Forbidden actions.** No framework in port signatures; no event carrying arrays/rows/secrets; no scientific value only in a log.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Protocols with typed requests/results; `StructuredEvent` with discriminated detail; each event kind binds one detail.
- **Required unit tests.** Each event kind binds exactly one detail; no array/secret in event.
- **Required property tests.** NONE.
- **Required contract tests.** Contract scaffolding for later adapter conformance.
- **Required architecture tests.** Framework confinement for `application/ports/statistics.py`, `reporting.py`, `telemetry.py`.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; architecture; strict type lanes.
- **Acceptance criteria.** [ ] Typed statistics/reporting/telemetry ports. [ ] Event kind↔detail one-to-one. [ ] No sensitive event payload. [ ] Sink failures isolated.
- **Completion evidence.** Changed files (`application/ports/statistics.py`, `reporting.py`, `telemetry.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `EventSink` failures never propagate into scientific computation; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Statistics/reporting/telemetry ports.
- **Final review checklist.** [ ] Events diagnostic only.

#### P1-T036 — Implement persistence/runtime application ports

- **Ticket ID.** P1-T036
- **Title.** Implement persistence/runtime application ports
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ArtifactStore`, `CheckpointStore` (scientific vs recovery methods), `ManifestStore`, `RunStateStore`, `ArtifactLockProvider`, `HardwareInspector`, `CudaGuard`, `ResourcePressureMonitor`.
- **Objective.** Implement `application/ports/{persistence,runtime}.py`: `ArtifactStore`, `CheckpointStore` (scientific vs recovery methods), `ManifestStore`, `RunStateStore`, `ArtifactLockProvider`, `HardwareInspector`, `CudaGuard`, `ResourcePressureMonitor` — narrow by storage semantics, no god repository, no `ArtifactPathResolver` port.
- **Why this ticket exists.** Persistence is narrowed into non-overlapping ports; path resolution is internal to infrastructure; scientific/recovery checkpoints stay distinct.
- **Authority references.** Arch §12.2, §12.7, §15, §17.
- **Dependencies.** P1-T008, P1-T009, P1-T033.
- **Blocks.** P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T060, P1-T061, P1-T062, P1-T063, P1-T064, P1-T068.
- **Downstream consumers.** Every Phase 1 persistence/runtime infrastructure adapter (P1-T054–P1-T064) and the composition root (P1-T068) implement/consume these ports directly.
- **Preconditions.** P1-T008, P1-T009, P1-T033 complete.
- **Inputs.** Arch §12.2, §12.7, §15, §17.
- **Allowed scope.** `application/ports/persistence.py`, `runtime.py`.
- **Forbidden actions.** No `ArtifactRepository` god interface; no `ArtifactPathResolver` port; no `Path` crossing the application boundary; no generic save/load conflating scientific/recovery.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Protocols with typed requests/results; separate scientific/recovery checkpoint methods; lock provider yields a context-manager lease.
- **Required unit tests.** No `Path` in signatures; scientific≠recovery methods.
- **Required property tests.** NONE.
- **Required contract tests.** Contract scaffolding for later adapter conformance.
- **Required architecture tests.** No god persistence interface.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; architecture; strict type lanes.
- **Acceptance criteria.** [ ] Four+lock persistence ports, non-overlapping. [ ] No path port. [ ] Scientific/recovery distinct. [ ] No `Path` at boundary.
- **Completion evidence.** Changed files (`application/ports/persistence.py`, `runtime.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Typed persistence/lock errors from P1-T030; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Persistence/runtime ports.
- **Final review checklist.** [ ] No god repository.

#### P1-T037 — Implement reusable pipeline stage functions and concrete services

- **Ticket ID.** P1-T037
- **Title.** Implement reusable pipeline stage functions and concrete services
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** implementation-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `application/stages/*` functions (inspect_dataset → … → analyze_statistics), `CheckpointSelector`, `PolicyEvaluator` concrete services.
- **Objective.** Implement the `application/stages/*` functions (inspect_dataset → … → analyze_statistics) and the concrete services `CheckpointSelector`, `PolicyEvaluator`, that orchestrate ports using domain types only; `train_model` dispatches to federated or centralized ports; B0 runs the same stage shape.
- **Why this ticket exists.** Stages are the reusable pipeline; B0 uses the same code path with centralized identities; `PolicyEvaluator` is pure confusion-count arithmetic (no framework).
- **Authority references.** Arch §5.1 (stages), §9.2 (B0 via same stages), §12.3.
- **Dependencies.** P1-T034, P1-T035, P1-T036.
- **Blocks.** P1-T038, P2-T004.
- **Downstream consumers.** P1-T038 (ExperimentPlanner and ScoreReuseGate) and P2-T004 consume these stage functions and services directly.
- **Preconditions.** P1-T034, P1-T035, P1-T036 complete.
- **Inputs.** Arch §5.1, §9.2, §12.3.
- **Allowed scope.** `application/stages/`, concrete services in `application/stages/select_checkpoint.py`, `evaluate_policy.py`.
- **Forbidden actions.** No framework import in stages/services; no combined partition-and-preprocess; `PolicyEvaluator` never accepts two loose benign/attack refs.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Stage functions calling ports; dispatch by resolved spec; `CheckpointSelector` reads candidate descriptors and decides; `PolicyEvaluator` consumes committed aggregates and the fixed `EligibleClientSet`.
- **Required unit tests.** Stage dispatch (with test doubles); selector decides not store; evaluator rejects calibration set.
- **Required property tests.** NONE.
- **Required contract tests.** Stages use ports only.
- **Required architecture tests.** No framework import in stages/services.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; strict type lanes.
- **Acceptance criteria.** [ ] All stages implemented over ports. [ ] B0 uses the same stage shape. [ ] Selector decides, store persists. [ ] Evaluator consumes committed aggregate only.
- **Completion evidence.** Changed files (`application/stages/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Stage errors surface typed (P1-T030); no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Stage functions and concrete services.
- **Final review checklist.** [ ] No framework in stages.

#### P1-T038 — Implement ExperimentPlanner and the ScoreReuseGate

- **Ticket ID.** P1-T038
- **Title.** Implement ExperimentPlanner and the ScoreReuseGate
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** experiment-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `application/planning/planner.py::ExperimentPlanner`, `DraftExecutionPlan`, `DraftPlannedStage`, `application/planning/reuse.py::ScoreReuseGate`, `ReuseDecision`. Derives cell/stage identities; never mutates.
- **Objective.** Implement `application/planning/planner.py::ExperimentPlanner` (deterministic sweep expansion, identity/dependency derivation, dedup by shared expensive identities, `DraftExecutionPlan` of `DraftPlannedStage`) and `application/planning/reuse.py::ScoreReuseGate` (pure lineage comparison → `ReuseDecision`).
- **Why this ticket exists.** The planner never queries a store; reuse is stage-scoped and excludes threshold/report identities so B1–B4 share one calibration/test set; cell-ID collisions are refused.
- **Authority references.** Arch §14.1–14.3, §13.3, §29.2 (planner never queries store), §29.4 (63).
- **Dependencies.** P1-T037, P1-T033.
- **Blocks.** P1-T039, P5-T002.
- **Downstream consumers.** P1-T039 (preflight/executor/lifecycle/resource-pressure orchestration) and P5-T002 consume the planner and reuse gate directly.
- **Preconditions.** P1-T037, P1-T033 complete.
- **Inputs.** Arch §14.1–14.3, §13.3, §29.2, §29.4.
- **Allowed scope.** `application/planning/planner.py`, `reuse.py`.
- **Forbidden actions.** No artifact-catalogue access in the planner; no reuse decision on a draft stage; no DAG framework; no cell-ID collision accepted.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Deterministic expansion; `ScoreReuseGate.decide_*` compares full score lineage only; `AmbiguousPlanError`/`CyclicPlanError` on conflicts.
- **Required unit tests.** Identical inputs → identical draft; threshold change preserves scoring lineage; cell-ID collision raises; planner never calls store.
- **Required property tests.** Reuse gate excludes threshold/report identities.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Deterministic draft. [ ] Threshold change reuses scores. [ ] Planner never queries store. [ ] Cell-ID collision refused.
- **Completion evidence.** Changed files (`application/planning/planner.py`, `reuse.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `AmbiguousPlanError`, `CyclicPlanError` on conflicts; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Planner and score-reuse gate.
- **Final review checklist.** [ ] Draft carries no reuse decision.

#### P1-T039 — Implement preflight, executor, lifecycle, and resource-pressure orchestration

- **Ticket ID.** P1-T039
- **Title.** Implement preflight, executor, lifecycle, and resource-pressure orchestration
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** implementation-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `application/runtime/{preflight,executor,lifecycle,resource_pressure}.py`: `ExecutionPreflight`, `FinalExecutionPlan`, `PlanExecutor`, run/stage state machine, cooperative pressure orchestration. Freezes `ResolvedBatchExecutionProfile`; never changes scientific identity.
- **Objective.** Implement `application/runtime/{preflight,executor,lifecycle,resource_pressure}.py`: `ExecutionPreflight` (validates the exact resolved batch profile, classifies stages REUSE/RECOMPUTE/BLOCKED, freezes `FinalExecutionPlan`), `PlanExecutor` (idempotent per stage), the run/stage state machine, and cooperative pressure orchestration.
- **Why this ticket exists.** Preflight is the only consumer of the artifact-catalogue snapshot; it validates the exact profile and never substitutes; the executor decides reuse before compute; pressure never mutates a frozen scientific profile.
- **Authority references.** Arch §12.3, §14, §16.5–16.7, §18.
- **Dependencies.** P1-T038.
- **Blocks.** P1-T068, P3-T005.
- **Downstream consumers.** P1-T068 (composition root) and P3-T005 consume this orchestration directly.
- **Preconditions.** P1-T038 complete.
- **Inputs.** Arch §12.3, §14, §16.5–16.7, §18.
- **Allowed scope.** `application/runtime/`.
- **Forbidden actions.** No profile substitution; no `RUNNING→REUSED`; no auto `FAILED_OOM→PAUSED/RECOVERED`; pressure never resizes a scientific batch.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Preflight classification and freeze; executor lifecycle with reuse-before-compute; OOM terminal for the attempt; pressure recommends only equivalence-preserving actions.
- **Required unit tests.** Reuse-before-compute; OOM terminal; pressure pause/resume equivalence; profile never substituted.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Executor dispatch exhaustive.
- **Required integration tests.** Reuse-before-compute, OOM-terminal, and pressure pause/resume equivalence verified on synthetic data.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; synthetic integration; strict type lanes.
- **Acceptance criteria.** [ ] Exact profile validated, never substituted. [ ] Reuse decided before compute. [ ] OOM terminal for the attempt. [ ] Pressure preserves the frozen profile.
- **Completion evidence.** Changed files (`application/runtime/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `RamPreflightError`/`DiskSpaceError`/`UnsafeParallelismError` at plan time; `CudaOutOfMemoryError` terminal.
- **Stop conditions.** None.
- **Deliverables.** Preflight/executor/lifecycle/pressure.
- **Final review checklist.** [ ] No silent batch change.

#### P1-T040 — Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing

- **Ticket ID.** P1-T040
- **Title.** Implement anchor/feasibility gates, readiness evaluator, freeze, and tracing
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** experiment-engineer
- **Supporting agents.** statistics-auditor, artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `AnchorReproductionGate`, `FeasibilityGateEvaluator`, `ScientificReadinessResult` evaluator, `TableFigureTracer` (provenance-closure), result-freeze eligibility.
- **Objective.** Implement `application/planning/gates.py` (`AnchorReproductionGate`, `FeasibilityGateEvaluator`), the `ScientificReadinessResult` evaluator, and `application/reporting/{freeze,tracing}.py` (`TableFigureTracer` provenance-closure, result-freeze eligibility).
- **Why this ticket exists.** Journal expansion requires a passed anchor gate; Regime-D science requires exact-lineage feasibility; reporting refuses untraced output.
- **Authority references.** Arch §12.3, §22.2 (tracing), §27 (blockers into readiness); Road §20 (gates).
- **Dependencies.** P1-T038, P1-T027.
- **Blocks.** P2-T020, P4-T013.
- **Downstream consumers.** P2-T020 and P4-T013 consume these gates and evaluator directly.
- **Preconditions.** P1-T038, P1-T027 complete.
- **Inputs.** Arch §12.3, §22.2, §27; Road §20.
- **Allowed scope.** `application/planning/gates.py`, `application/reporting/freeze.py`, `tracing.py`.
- **Forbidden actions.** No table-render shortcut around the anchor gate; no render before freeze/provenance closure; no relabeled failed feasibility.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Pure decision services over typed evidence; `FeasibilityGateEvaluator` blocks Regime-D materialization without matching source/partition lineage; `TableFigureTracer.trace` refuses with `ProvenanceError` when lineage does not close.
- **Required unit tests.** Anchor gate blocks journal expansion on failure; feasibility below 90% blocks; tracer refuses untraced output.
- **Required property tests.** Readiness aggregates blockers.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; strict type lanes.
- **Acceptance criteria.** [ ] Anchor gate blocks journal on failure. [ ] Feasibility gate enforces exact lineage + 90%. [ ] Tracer refuses untraced output. [ ] Readiness carries blockers.
- **Completion evidence.** Changed files (`application/planning/gates.py`, `application/reporting/freeze.py`, `tracing.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `AnchorReproductionFailure` (journal-track blocking), `ProvenanceError`, blocking reasons in readiness; no other failure expected.
- **Stop conditions.** None.
- **Deliverables.** Gates, readiness evaluator, freeze/tracing.
- **Final review checklist.** [ ] No untraced render.

#### P1-T054 — Implement semantic storage-root binding and path resolution

- **Ticket ID.** P1-T054
- **Title.** Implement semantic storage-root binding and path resolution
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `BoundStorageRoot`, internal `ArtifactPathResolver`, `ResolvedArtifactLocation`, the closed `ArtifactKey` union (`DatasetArtifactKey`, `RegimeArtifactKey`, `SeedScopedArtifactKey`, `CrossSeedArtifactKey`, `RunArtifactKey`, `ReportArtifactKey`).
- **Objective.** Implement `infrastructure/persistence/roots.py` and `paths.py`: bind each `StorageRootSpec` to a concrete `BoundStorageRoot`, and implement the internal `ArtifactPathResolver.resolve(ResolveArtifactLocationRequest)` that exhaustively matches the closed `ArtifactKey` union with `assert_never`, derives a `RelativeArtifactPath`, and joins it beneath the bound root, raising `PathResolutionError` on any escape.
- **Why this ticket exists.** Split out of the former combined path/hashing/serialization/persistence/lock mega-ticket because path resolution is a distinct, narrowly-scoped internal collaborator (Arch §15) that must never be exposed as an application-facing port and must never be conflated with hashing, serialization, atomic commit, bundle commit, or locking, each of which has its own failure modes and its own ticket (P1-T055–P1-T059).
- **Authority references.** Arch §15.1 (semantic roots), §15.2 (logical keys and resolved locations), §15.3 (path rules), §15.4 (storage resolution diagram).
- **Dependencies.** P1-T036, P0-T006.
- **Blocks.** P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T042, P1-T043, P1-T070.
- **Downstream consumers.** P1-T055 (hashing), P1-T057 (atomic single-artifact persistence), P1-T058 (bundle commit), P1-T042/P1-T043 (data/learning adapters resolving processed-split and model artifact locations), and every later infrastructure adapter that persists an artifact.
- **Preconditions.** P1-T036, P0-T006 complete.
- **Inputs.** `StorageRootSpec` values from `domain/artifacts/keys.py` (P1-T008); the repository root layout from P0-T006.
- **Allowed scope.** `infrastructure/persistence/roots.py`, `infrastructure/persistence/paths.py`.
- **Forbidden actions.** No `Path`, `BoundStorageRoot`, or `ResolvedArtifactLocation` crossing into a domain identity, scientific specification, stage fingerprint, artifact key, or scientific manifest; no application-facing `ArtifactPathResolver` port; no path-derived artifact identity.
- **Required configuration or NONE.** Storage-root binding from execution configuration/composition (concrete absolute paths supplied only at the composition root).
- **Implementation responsibilities.** Bind `StorageRootSpec` to `BoundStorageRoot`; implement content-addressed sharded relative-location derivation (`<hash[:2]>/<hash>`); implement `ArtifactPathResolver.resolve` with exhaustive `assert_never` matching over the six `ArtifactKey` variants; reject any resolution that would escape the bound root.
- **Required unit tests.** A resolution that would escape its `BoundStorageRoot` raises `PathResolutionError`; each of the six `ArtifactKey` variants resolves to a distinct, stable relative location; adding a new `ArtifactKey` variant without a resolver branch is a static (`assert_never`) failure, not a runtime one.
- **Required property tests.** Identical logical inputs always resolve to the identical relative location; content-addressed sharding is stable under repeated resolution.
- **Required contract tests.** `ArtifactPathResolver` is never invoked directly by `application`; only `infrastructure/persistence` adapters call it.
- **Required architecture tests.** No `Path` construction exists outside `infrastructure/persistence`; `domain` and `application` contracts reference only `StorageRootKind`/`StorageRootSpec`.
- **Required integration tests.** A synthetic multi-root resolution round-trip (dataset/regime/seed-scoped/cross-seed/run/report keys) produces the expected relative locations beneath each bound root.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; contract; architecture; integration (persistence) lanes.
- **Acceptance criteria.** [ ] Root-escape raises `PathResolutionError`. [ ] Exhaustive `assert_never` over `ArtifactKey`. [ ] No path-derived identity. [ ] No application-facing path port.
- **Completion evidence.** Changed files (`roots.py`, `paths.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A malformed or escaping path is a `PathResolutionError`, never silently corrected.
- **Stop conditions.** Stop if a `StorageRootKind` lacks a corresponding bound root at composition time; record a blocker rather than defaulting.
- **Deliverables.** Storage-root binding and path-resolution adapter.
- **Final review checklist.** [ ] Identity never path-derived. [ ] No application-facing path type.

#### P1-T055 — Implement content hashing

- **Ticket ID.** P1-T055
- **Title.** Implement content hashing
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (pure hashing utility consumed by `ArtifactRef.content_hash` and stage-fingerprint computation, both owned elsewhere).
- **Objective.** Implement `infrastructure/persistence/hashing.py`: blake3 content hashing as the default for content addressing (score arrays, Parquet files, state dicts), and SHA-256 via `hashlib` where a cryptographic guarantee is specifically required.
- **Why this ticket exists.** Split out of the former combined persistence mega-ticket because hashing is a narrow, independently testable utility with its own performance and correctness properties, distinct from path resolution, serialization, atomic commit, bundle commit, and locking.
- **Authority references.** Arch §4.1 (blake3/hashlib roles), §9.5 (blake3 for content hashes; SHA-256 where required), §13.4 (fingerprint computation uses blake3 over canonical typed tuples, not raw content — this ticket provides the blake3 primitive both fingerprinting and artifact hashing share).
- **Dependencies.** P1-T054.
- **Blocks.** P1-T057, P1-T058, P1-T042, P1-T043, P1-T046, P1-T070.
- **Downstream consumers.** P1-T057 (atomic single-artifact persistence verifies content hash before commit), P1-T058 (bundle member-hash verification), every adapter that persists a content-addressed artifact.
- **Preconditions.** P1-T054 complete.
- **Inputs.** Arch §4.1, §9.5, §13.4.
- **Allowed scope.** `infrastructure/persistence/hashing.py`.
- **Forbidden actions.** No use of blake3/SHA-256 to derive a logical `ArtifactId` (identity is deterministic from type/key/stage/namespace, never from content bytes); no hashing of raw floats without the canonical quantization step defined in the domain fingerprint model.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Implement a streaming blake3 hash function for large arrays/files; implement a SHA-256 path for the cryptographic-guarantee case; expose both behind narrow, named functions (never a generic `hash(data, algo)`).
- **Required unit tests.** Identical bytes hash identically across repeated calls and across chunked-vs-whole-file streaming; different bytes hash differently (no trivial collision in the test corpus); SHA-256 path is used only where explicitly requested.
- **Required property tests.** Hash output length and encoding are stable across arbitrary byte-string inputs within the declared size bounds.
- **Required contract tests.** NONE.
- **Required architecture tests.** `hashing.py` exposes no generic `compute(algo, data)` method.
- **Required integration tests.** A large synthetic array/Parquet file hashes identically whether read whole or in chunks.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; integration (persistence) lanes.
- **Acceptance criteria.** [ ] blake3 is the content-addressing default. [ ] SHA-256 available where required. [ ] No generic hash method. [ ] Chunked and whole-file hashing agree.
- **Completion evidence.** Changed files (`hashing.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected.
- **Stop conditions.** None.
- **Deliverables.** Content-hashing utility.
- **Final review checklist.** [ ] No identity derived from content hash alone.

#### P1-T056 — Implement serialization and schema-version handling

- **Ticket ID.** P1-T056
- **Title.** Implement serialization and schema-version handling
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ArtifactSchemaVersion` (serialization enforcement; the value object itself is domain-owned elsewhere).
- **Objective.** Implement `infrastructure/persistence/serialization.py`: msgspec-based (de)serialization for manifests and provenance records, with `ArtifactSchemaVersion` recorded and checked on every read.
- **Why this ticket exists.** Split out of the former combined persistence mega-ticket because serialization/schema-version enforcement is a distinct, independently testable responsibility (Arch §9.5) from hashing, path resolution, atomic commit, bundle commit, and locking.
- **Authority references.** Arch §4.1 (msgspec role, stricter/faster than `json` + `dataclasses.asdict`), §9.5 (`ArtifactSchemaVersion` on every persisted artifact).
- **Dependencies.** P1-T054.
- **Blocks.** P1-T057, P1-T058, P1-T042, P1-T043, P1-T046, P1-T070.
- **Downstream consumers.** P1-T057, P1-T058, and every adapter that serializes a manifest, provenance record, or other structured artifact.
- **Preconditions.** P1-T054 complete.
- **Inputs.** Arch §4.1, §9.5.
- **Allowed scope.** `infrastructure/persistence/serialization.py`.
- **Forbidden actions.** No Pydantic model at this boundary (Pydantic is confined to `config`); no `json.dumps` of raw floats for identity purposes; no silent schema-version mismatch acceptance.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Implement msgspec encode/decode for every manifest/provenance record type; attach and verify `ArtifactSchemaVersion` on every read; raise a typed incompatibility on mismatch.
- **Required unit tests.** A schema-version mismatch on read is rejected, not silently coerced; round-trip encode/decode preserves every field exactly.
- **Required property tests.** Round-trip encode/decode is idempotent for arbitrary valid manifest instances within the declared schema.
- **Required contract tests.** NONE.
- **Required architecture tests.** No Pydantic import in `infrastructure/persistence/serialization.py`.
- **Required integration tests.** A synthetic manifest serializes, persists, and deserializes with an unchanged value and schema version.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; integration (persistence) lanes.
- **Acceptance criteria.** [ ] msgspec used for manifest/provenance (de)serialization. [ ] Schema-version mismatch rejected. [ ] Round-trip is exact. [ ] No Pydantic at this boundary.
- **Completion evidence.** Changed files (`serialization.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A schema-version mismatch is a typed `SchemaCompatibility.INCOMPATIBLE` result surfaced to the caller, never silently upgraded.
- **Stop conditions.** None.
- **Deliverables.** Serialization/schema-version adapter.
- **Final review checklist.** [ ] No Pydantic leakage. [ ] Schema version always checked.

#### P1-T057 — Implement atomic single-artifact persistence

- **Ticket ID.** P1-T057
- **Title.** Implement atomic single-artifact persistence
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ArtifactStore` (single-file methods: `lookup`, `write_atomically`, `validate_integrity`), `ArtifactLookupRequest`/`Result`, `WriteArtifactRequest`, `ArtifactWriteResult`, `ValidateArtifactRequest`, `ArtifactValidationResult`.
- **Objective.** Implement `infrastructure/persistence/artifacts.py`: content-addressed lookup, and atomic single-file commit (temporary file in the destination directory or same validated filesystem, complete write, flush/fsync per policy, content-hash/schema verification, atomic replace, manifest update only after commit).
- **Why this ticket exists.** Split out of the former combined persistence mega-ticket because single-file atomic commit has its own correctness protocol (Arch §15.3) distinct from multi-file bundle commit (P1-T058), which requires a different (marker-based) visibility protocol.
- **Authority references.** Arch §12.2 (`ArtifactStore` port, single-file methods), §12.4 (`ArtifactStore` implementation), §15.3 (single-file writer protocol), §15.4 (storage resolution diagram), §29.4 (invalid states 33–34: partial file never marked complete; immutable overwrite forbidden).
- **Dependencies.** P1-T054, P1-T055, P1-T056.
- **Blocks.** P1-T058, P1-T059, P1-T070.
- **Downstream consumers.** Every stage that persists a single-file scientific artifact (source manifests, split manifests, threshold outputs, metric outputs, statistical outputs, resolved-configuration artifacts) depends on this ticket transitively through `ArtifactStore`.
- **Preconditions.** P1-T054, P1-T055, P1-T056 complete.
- **Inputs.** Arch §12.2, §12.4, §15.3, §15.4, §29.4.
- **Allowed scope.** `infrastructure/persistence/artifacts.py`.
- **Forbidden actions.** No directory-level atomicity claim from a single `os.replace`; no manifest update before the file is verified and replaced; no overwrite of a hash-verified immutable artifact with different content (an identical logical id with mismatched bytes is a typed integrity conflict, never resolved by minting a new random id).
- **Required configuration or NONE.** Write-disposition policy (`CREATE_IF_ABSENT`, `VERIFY_OR_FAIL`, `ATOMIC_STAGE_COMMIT`) from `ArtifactPolicy`.
- **Implementation responsibilities.** Implement content-addressed `lookup`; implement `write_atomically` per the exact same-filesystem temp-write/verify/replace/manifest-update sequence; implement `validate_integrity` re-verifying hash/schema against the persisted manifest.
- **Required unit tests.** A write that fails mid-way leaves no partial artifact marked complete; an identical logical id with mismatched persisted bytes raises a typed integrity error rather than being silently overwritten or re-keyed.
- **Required property tests.** Repeated `write_atomically` calls with identical content are idempotent (deduplicated, not re-written).
- **Required contract tests.** `ArtifactStore`'s single-file methods satisfy the Section 12.2 port contract exactly (no extra/missing method, no weak generic signature).
- **Required architecture tests.** No framework carrier (NumPy/pandas/PyArrow/Torch object) crosses the `ArtifactStore` port signature.
- **Required integration tests.** Same-filesystem atomic commit on synthetic content; a killed-mid-write simulation leaves no partial artifact and no corrupted manifest.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; contract; architecture; integration (persistence) lanes.
- **Acceptance criteria.** [ ] Atomic same-filesystem commit. [ ] No partial artifact ever marked complete. [ ] Mismatched-bytes-same-id is a typed integrity conflict. [ ] Manifest updates only after commit.
- **Completion evidence.** Changed files (`artifacts.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `ArtifactError`/`PartialArtifactError` on any incomplete or corrupt write; the stage recomputes rather than reusing a partial artifact.
- **Stop conditions.** None.
- **Deliverables.** Atomic single-artifact persistence adapter.
- **Final review checklist.** [ ] No directory-atomicity overclaim. [ ] No silent overwrite.

#### P1-T058 — Implement immutable multi-file bundle commit and manifest verification

- **Ticket ID.** P1-T058
- **Title.** Implement immutable multi-file bundle commit and manifest verification
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ArtifactStore.commit_bundle`, `CommitArtifactBundleRequest`, `ArtifactBundleManifest`, `ArtifactBundleCommitResult`, `ArtifactBundleId`.
- **Objective.** Implement `infrastructure/persistence/bundles.py`: immutable multi-file bundle commit — write and verify every declared member (schema, row count/order, lineage, content hash), then write the final commit marker last, so a reader rejects an absent/invalid marker or any member-hash mismatch and never sees a partially-written bundle.
- **Why this ticket exists.** Split out of the former combined persistence mega-ticket because the multi-file bundle protocol (marker-based visibility) is structurally different from single-file atomic replace (P1-T057) and is the mechanism the atomic per-client test-score aggregate (benign + attack scores) relies on.
- **Authority references.** Arch §9.2 (atomic test-score-pair persistence protocol, steps 1–9), §12.2 (`ArtifactStore.commit_bundle`), §15.3 (multi-file writer protocol), §29.4 (invalid state 33: partial bundle never marked complete).
- **Dependencies.** P1-T057.
- **Blocks.** P1-T070.
- **Downstream consumers.** Every scoring/evaluation stage that commits a `ClientTestScoreArtifact` aggregate (benign + attack scores) or any other fully-typed multi-file bundle.
- **Preconditions.** P1-T057 complete.
- **Inputs.** Arch §9.2, §12.2, §15.3.
- **Allowed scope.** `infrastructure/persistence/bundles.py`.
- **Forbidden actions.** No claim of directory-level atomicity from individual `os.replace` calls; no reader-visible bundle before its commit marker is written and verified; no loosely-typed or partially-committed pair accepted as a substitute for a fully declared bundle.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Implement `commit_bundle`: create a new immutable bundle directory, write/verify every declared member, compute and record member hashes in `ArtifactBundleManifest`, write the final commit marker last, and return `ArtifactBundleCommitResult` only after the marker is verified.
- **Required unit tests.** A missing benign or attack child artifact is rejected; a mismatched client/split/checkpoint/scoring-identity between declared members is rejected; an absent or invalid final commit marker makes the bundle unreadable; a child content-hash mismatch is rejected.
- **Required property tests.** NONE.
- **Required contract tests.** `ArtifactStore.commit_bundle` satisfies its Section 12.2 signature exactly; a successfully committed bundle is readable and consumed only as one aggregate (never as two independent references).
- **Required architecture tests.** No framework carrier crosses the `commit_bundle` signature.
- **Required integration tests.** A synthetic two-member bundle (benign + attack score children) commits atomically and is rejected if interrupted before the marker is written.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; integration (persistence) lanes.
- **Acceptance criteria.** [ ] Marker written last; no reader-visible partial bundle. [ ] Missing/mismatched member rejected. [ ] Committed pair consumed only as one aggregate. [ ] No directory-atomicity overclaim.
- **Completion evidence.** Changed files (`bundles.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `IncompleteArtifactBundleError`/`PartialArtifactError` on any missing/mismatched/uncommitted member; the bundle is recomputed, never partially exposed.
- **Stop conditions.** None.
- **Deliverables.** Immutable multi-file bundle commit adapter.
- **Final review checklist.** [ ] Marker-gated visibility. [ ] No loose pair accepted.

#### P1-T059 — Implement lock providers, leases, and commit ownership

- **Ticket ID.** P1-T059
- **Title.** Implement lock providers, leases, and commit ownership
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ArtifactLockProvider`, `AcquireArtifactLockRequest`, `ArtifactLockLease`, `LockScope` (`COMPUTATION_OWNERSHIP`, `COMMIT`).
- **Objective.** Implement `infrastructure/persistence/locks.py` using `filelock`: `ArtifactLockProvider.acquire` returning a context-manager `ArtifactLockLease` with owner identity, scope, acquisition/expiry, optional renewable heartbeat, stale-owner detection, and process-death recovery.
- **Why this ticket exists.** Split out of the former combined persistence mega-ticket because locking has a distinct failure mode (contention, staleness, process death) and a distinct scope model (`COMPUTATION_OWNERSHIP` may be long-lived; `COMMIT` is always short-lived), which must not be conflated with the artifact/bundle commit protocols themselves (P1-T057/P1-T058).
- **Authority references.** Arch §4.1 (filelock role), §12.2 (`ArtifactLockProvider`), §13.5 (a filesystem commit lock is not held across a long training run), §15.3 (lock lifecycle).
- **Dependencies.** P1-T057.
- **Blocks.** P1-T070.
- **Downstream consumers.** P1-T039 (executor) acquires a computation-ownership lease before compute and a short commit lease before persistence; every stage that writes an artifact depends on this ticket transitively.
- **Preconditions.** P1-T057 complete.
- **Inputs.** Arch §4.1, §12.2, §13.5, §15.3.
- **Allowed scope.** `infrastructure/persistence/locks.py`.
- **Forbidden actions.** No long-held commit lock across a long computation; no concurrent write to one artifact without a held lease; no lease that silently expires without a typed conflict/stale-owner signal.
- **Required configuration or NONE.** Timeout/heartbeat policy from `ExecutionPolicy`.
- **Implementation responsibilities.** Implement `acquire` returning a context-manager `ArtifactLockLease`; implement stale-owner detection and process-death recovery for `COMPUTATION_OWNERSHIP` leases; implement short-lived `COMMIT` leases used only around final persistence.
- **Required unit tests.** A held `COMPUTATION_OWNERSHIP` lease does not block a properly staled/expired-owner reclaim; a `COMMIT` lease is released promptly after persistence; two concurrent acquisition attempts on the same artifact/bundle id do not both succeed.
- **Required property tests.** NONE.
- **Required contract tests.** `ArtifactLockProvider.acquire` satisfies its Section 12.2 signature; `ArtifactLockLease` is a proper context manager (enter/exit, explicit release).
- **Required architecture tests.** NONE.
- **Required integration tests.** Lease release, heartbeat renewal, stale-owner detection, and process-death recovery are exercised against a synthetic concurrent-writer scenario.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; integration (persistence) lanes.
- **Acceptance criteria.** [ ] Computation-ownership vs commit scopes distinct. [ ] Stale-owner/process-death recovery works. [ ] No concurrent write without a held lease. [ ] Commit leases are short-lived.
- **Completion evidence.** Changed files (`locks.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `ArtifactLockConflict` is `RETRYABLE_TRANSIENT` with a bounded wait; exhausting retries raises the underlying error rather than silently proceeding without a lease.
- **Stop conditions.** None.
- **Deliverables.** Lock provider and lease adapter.
- **Final review checklist.** [ ] No long-held commit lock. [ ] Stale-owner recovery verified.

#### P1-T042 — Implement PyArrow streaming and bounded-pandas data adapters

- **Ticket ID.** P1-T042
- **Title.** Implement PyArrow streaming and bounded-pandas data adapters
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** infrastructure
- **Owner.** data-pipeline-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `infrastructure/data/{inspection,partitioning,splitting,preprocessing,materialization}.py` adapters implementing the P1-T034 data ports. Source/partition/split/preprocessor/processed identities via lineage.
- **Objective.** Implement `infrastructure/data/{inspection,partitioning,splitting,preprocessing,materialization}.py` using PyArrow `dataset.Scanner`/`RecordBatchReader`, bounded pandas conversion, chunked reads, two-pass fit where required, partitioned Parquet processed artifacts, source-row lineage and row-order checksums.
- **Why this ticket exists.** No large dataset loads whole; PyArrow is the sole tabular path; chunk/reference equivalence and stable row-group traversal are required.
- **Authority references.** Arch §16.3, §4.1 (PyArrow authoritative), §9.6.
- **Dependencies.** P1-T034, P1-T054, P1-T055, P1-T056, P1-T057.
- **Blocks.** P2-T004.
- **Downstream consumers.** P2-T004 consumes these adapters directly.
- **Preconditions.** P1-T034, P1-T054, P1-T055, P1-T056, P1-T057 complete.
- **Inputs.** Arch §16.3, §4.1, §9.6.
- **Allowed scope.** `infrastructure/data/`.
- **Forbidden actions.** No whole-dataset load; no PyArrow/pandas carrier crossing upward; no runtime chunk resize once a stage starts.
- **Required configuration or NONE.** Chunk sizing from `PreprocessingChunkSpec` (frozen).
- **Implementation responsibilities.** Streaming adapters; two-pass fit under `NormalizationScope`; partitioned processed Parquet per client/split; private carriers only.
- **Required unit tests.** NONE beyond adapter construction (behavioral checks are integration-level on synthetic data).
- **Required property tests.** NONE.
- **Required contract tests.** Adapters satisfy the data ports.
- **Required architecture tests.** No PyArrow/pandas carrier crosses upward out of `infrastructure/data/`.
- **Required integration tests.** Chunked-vs-reference equivalence; bounded peak memory; stable row-group traversal; source-row lineage (all on synthetic data).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); contract; strict type lanes.
- **Acceptance criteria.** [ ] No whole-dataset load. [ ] Chunk-vs-reference equivalence holds. [ ] Row-group traversal stable. [ ] Carriers stay private.
- **Completion evidence.** Changed files (`infrastructure/data/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DatasetError`/`PartitionError`/`SplitError`/`PreprocessingError`; no execution against real data occurs in Phase 1.
- **Stop conditions.** None (synthetic data only in Phase 1).
- **Deliverables.** Data infrastructure adapters.
- **Final review checklist.** [ ] Bounded memory verified on synthetic data.

#### P1-T043 — Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters

- **Ticket ID.** P1-T043
- **Title.** Implement the PyTorch AE model and deterministic device/seed/DataLoader adapters
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** infrastructure
- **Owner.** federated-learning-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `infrastructure/learning/models/autoencoder.py` (fixed AE, no BatchNorm), deterministic device/seed/DataLoader adapters. Training identity inputs (via adapters).
- **Objective.** Implement `infrastructure/learning/models/autoencoder.py` (fixed AE, no BatchNorm) and deterministic device/seed/DataLoader adapters: explicit CUDA ownership, `DeterminismLevel.STRICT` settings, explicit `torch.Generator`/`worker_init_fn`, per-worker seeded RNG, spawn context for CUDA stages.
- **Why this ticket exists.** Determinism and seed ownership are structural; there are no scattered global seed calls; CUDA stages spawn.
- **Authority references.** Arch §16.1–16.2, §16.4, §16.7, §9.6.
- **Dependencies.** P1-T034, P1-T054, P1-T055, P1-T056.
- **Blocks.** P1-T044, P2-T008.
- **Downstream consumers.** P1-T044 (FedAvg/FedProx/centralized trainers) and P2-T008 consume this model and these adapters directly.
- **Preconditions.** P1-T034, P1-T054, P1-T055, P1-T056 complete.
- **Inputs.** Arch §16.1–16.2, §16.4, §16.7, §9.6.
- **Allowed scope.** `infrastructure/learning/models/`, device/seed/DataLoader adapters in `infrastructure/runtime/{determinism,processes}.py`.
- **Forbidden actions.** No global `set_start_method`; no CUDA fork; no scattered global seeds; no BatchNorm; no `nn.Module` crossing upward.
- **Required configuration or NONE.** From training/execution specs (frozen).
- **Implementation responsibilities.** Deterministic CUDA settings; DataLoader generators from `DataLoaderSeedPlan`; per-stage spawn context; `torch.compile` off.
- **Required unit tests.** No global seed calls.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** No `nn.Module` crosses upward out of `infrastructure/learning/models/`.
- **Required integration tests.** Zero-vs-multi-worker, sequential-vs-parallel, repeated, resumed equivalence via row-order checksums (synthetic tiny model, cuda lane).
- **Required CUDA tests.** Determinism equivalence checks on a synthetic tiny model under `DeterminismLevel.STRICT`.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** CUDA lane (serialized); unit; strict type lanes.
- **Acceptance criteria.** [ ] No BatchNorm. [ ] Deterministic seed ownership. [ ] CUDA stages spawn, none fork. [ ] Worker equivalence holds on synthetic model.
- **Completion evidence.** Changed files (`infrastructure/learning/models/`, `infrastructure/runtime/determinism.py`, `processes.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `DeterminismViolationError`; stop if AE architecture is unresolved (readiness blocker) — implement only an explicit non-citable smoke AE here.
- **Stop conditions.** Stop if AE architecture is unresolved (readiness blocker) — implement only an explicit non-citable smoke AE here.
- **Deliverables.** AE model + determinism adapters.
- **Final review checklist.** [ ] Determinism structural.

#### P1-T044 — Implement Flower FedAvg/FedProx and centralized trainers

- **Ticket ID.** P1-T044
- **Title.** Implement Flower FedAvg/FedProx and centralized trainers
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** infrastructure
- **Owner.** federated-learning-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `infrastructure/learning/federation/{trainer,strategies/fedavg,strategies/fedprox}.py`, `infrastructure/learning/centralized/trainer.py`. Training/checkpoint identities.
- **Objective.** Implement `infrastructure/learning/federation/{trainer,strategies/fedavg,strategies/fedprox}.py` and `infrastructure/learning/centralized/trainer.py`, converting framework handles to checkpoint descriptors before returning; full-participation round aborts on any invalid update; FedProx inherits all non-strategy settings and adds only frozen-grid µ.
- **Why this ticket exists.** Flower stays behind the training port; full participation is enforced; FedProx is a matched stress variant; B0 is a distinct centralized backend.
- **Authority references.** Arch §12.4, §16.5 (full participation), §9.6, §25 (add training strategy).
- **Dependencies.** P1-T043.
- **Blocks.** P2-T009, P4-T016.
- **Downstream consumers.** P2-T009 and P4-T016 consume these trainers directly.
- **Preconditions.** P1-T043 complete.
- **Inputs.** Arch §12.4, §16.5, §9.6, §25.
- **Allowed scope.** `infrastructure/learning/federation/`, `centralized/`.
- **Forbidden actions.** No Flower object crossing the port; no partial participation; FedProx µ never from FedAvg/confirmatory outcomes; no shared identity between FedAvg and centralized.
- **Required configuration or NONE.** From `FederationSpec`/`TrainingSpec` (frozen); FedProx µ from frozen grid.
- **Implementation responsibilities.** Trainer lifecycle; strategies; round-abort on missing/timeout/malformed/non-finite/shape-incompatible; centralized trainer with no federation field.
- **Required unit tests.** NONE beyond construction (behavioral checks are integration/contract-level).
- **Required property tests.** NONE.
- **Required contract tests.** Adapters satisfy trainer ports.
- **Required architecture tests.** No Flower object crosses the port boundary.
- **Required integration tests.** Full-participation abort on invalid update; FedProx matches non-strategy settings; centralized rejects FedAvg identities (cuda lane, synthetic).
- **Required CUDA tests.** Full-participation abort and FedProx-vs-FedAvg equivalence on a synthetic tiny model.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** CUDA lane; contract; strict type lanes.
- **Acceptance criteria.** [ ] Full participation aborts on invalid update. [ ] FedProx µ from frozen grid only. [ ] Centralized backend distinct. [ ] No Flower object upward.
- **Completion evidence.** Changed files (`infrastructure/learning/federation/`, `centralized/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `FullParticipationViolationError`/`RoundAbortedError`, client-failure family, `TrainingError`, `CudaOutOfMemoryError`; stop if the FedProx µ-grid is not pre-registered (readiness blocker) — smoke only.
- **Stop conditions.** Stop if the FedProx µ-grid is not pre-registered (readiness blocker) — smoke only.
- **Deliverables.** FedAvg/FedProx/centralized trainers.
- **Final review checklist.** [ ] Stress trainers outside the ladder.

#### P1-T045 — Implement scoring, threshold, clustering, quantile, and fed-stats adapters

- **Ticket ID.** P1-T045
- **Title.** Implement scoring, threshold, clustering, quantile, and fed-stats adapters
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** infrastructure
- **Owner.** threshold-policy-engineer
- **Supporting agents.** data-pipeline-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `infrastructure/scoring/{calibration,test,temporal}.py`, `infrastructure/thresholding/{quantiles,policies,variants,clustering,federated_statistics}.py`. Scoring/threshold identities.
- **Objective.** Implement `infrastructure/scoring/{calibration,test,temporal}.py`, `infrastructure/thresholding/{quantiles,policies,variants,clustering,federated_statistics}.py`: batched CUDA scoring streaming to device with incremental writes; exact quantile estimators; the `ThresholdStrategy` implementations; exact k-means++ B4 (never MiniBatch); FedStats full-variance/matched-exceedance/larger-k-tie.
- **Why this ticket exists.** Scoring streams batches; thresholds derive from calibration scores only; canonical B4 is exact; FedStats structural rules cannot be disabled.
- **Authority references.** Arch §12.4, §16.2–16.3, §9.2.
- **Dependencies.** P1-T043.
- **Blocks.** P2-T011, P2-T015.
- **Downstream consumers.** P2-T011 and P2-T015 consume these adapters directly.
- **Preconditions.** P1-T043 complete.
- **Inputs.** Arch §12.4, §16.2–16.3, §9.2.
- **Allowed scope.** `infrastructure/scoring/`, `infrastructure/thresholding/`.
- **Forbidden actions.** No score/estimator carrier crossing upward; no approximate quantile in confirmatory path; no MiniBatchKMeans; no simple pooled variance/configurable tie.
- **Required configuration or NONE.** From scoring/threshold specs (frozen).
- **Implementation responsibilities.** Batched scoring; exact estimators; B4 exact k-means++ with locked constants; FedStats algorithm.
- **Required unit tests.** FedStats between-term + larger-k tie.
- **Required property tests.** NONE.
- **Required contract tests.** Adapters satisfy scoring/threshold ports.
- **Required architecture tests.** No score/estimator carrier crosses upward.
- **Required integration tests.** Batched-vs-reference scoring equivalence on synthetic data; fixed B4 assignment/adjusted-Rand regression (replaces the former golden-test category for this ticket).
- **Required CUDA tests.** Batched-vs-reference scoring equivalence on synthetic tiny model/data.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration; contract; strict type lanes.
- **Acceptance criteria.** [ ] Batched-vs-reference scoring equivalence. [ ] Exact B4 golden-stable. [ ] FedStats structural rules enforced. [ ] Carriers private.
- **Completion evidence.** Changed files (`infrastructure/scoring/`, `infrastructure/thresholding/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `ScoringError`/`ThresholdError`/`CudaOutOfMemoryError`; stop if the B4 scaler/constants are unresolved (readiness blocker) — smoke only.
- **Stop conditions.** Stop if the B4 scaler/constants are unresolved (readiness blocker) — smoke only.
- **Deliverables.** Scoring/threshold/clustering/quantile/fed-stats adapters.
- **Final review checklist.** [ ] Exact, non-approximate.

#### P1-T046 — Implement the SciPy statistics adapter and per-family metric calculators

- **Ticket ID.** P1-T046
- **Title.** Implement the SciPy statistics adapter and per-family metric calculators
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** infrastructure
- **Owner.** statistics-auditor
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `infrastructure/statistics/scipy_adapter.py`, `infrastructure/evaluation/metrics.py::MetricCalculator`. Statistical/evaluation identities.
- **Objective.** Implement `infrastructure/statistics/scipy_adapter.py` (BCa/Wilcoxon/Spearman/JS; in-repo `cliffs_delta` caller) and `infrastructure/evaluation/metrics.py` (`MetricCalculator` with one typed method per family, never a generic `compute(family, inputs)`).
- **Why this ticket exists.** BCa is primary; degeneracy is a typed result, never a silent percentile; metrics are typed per family.
- **Authority references.** Arch §12.4, §4.1 (SciPy roles), §9.3, §16.5.
- **Dependencies.** P1-T035, P1-T056, P1-T057.
- **Blocks.** P2-T016, P2-T018.
- **Downstream consumers.** P2-T016 and P2-T018 consume this adapter and calculator directly.
- **Preconditions.** P1-T035, P1-T056, P1-T057 complete.
- **Inputs.** Arch §12.4, §4.1, §9.3, §16.5.
- **Allowed scope.** `infrastructure/statistics/`, `infrastructure/evaluation/`.
- **Forbidden actions.** No generic metric method; no silent BCa→percentile; no SciPy object crossing upward.
- **Required configuration or NONE.** From statistical/evaluation specs; explicit `BootstrapResampleCount`.
- **Implementation responsibilities.** BCa with explicit resamples; typed degeneracy result; per-family calculators.
- **Required unit tests.** BCa on synthetic paired deltas; degeneracy at tiny n typed; per-family calculators.
- **Required property tests.** BCa sanity.
- **Required contract tests.** Satisfies statistics port.
- **Required architecture tests.** No SciPy object crosses upward.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; contract; strict type lanes.
- **Acceptance criteria.** [ ] BCa primary with explicit resamples. [ ] Degeneracy typed. [ ] Per-family calculators (no generic method). [ ] No SciPy object upward.
- **Completion evidence.** Changed files (`infrastructure/statistics/scipy_adapter.py`, `infrastructure/evaluation/metrics.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** `StatisticsError` for unexpected only; degeneracy as `DegenerateBootstrapIntervalResult`.
- **Stop conditions.** None.
- **Deliverables.** Statistics adapter + metric calculators.
- **Final review checklist.** [ ] No percentile substitution.

#### P1-T060 — Implement CUDA guard and deterministic device initialization

- **Ticket ID.** P1-T060
- **Title.** Implement CUDA guard and deterministic device initialization
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** infrastructure
- **Owner.** implementation-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `CudaGuard` (implementation), `GpuAssignment`, `DevicePolicy` enforcement.
- **Objective.** Implement `infrastructure/runtime/cuda.py`: `CudaGuard.require_cuda(device: DeviceSpec) -> GpuAssignment`, validating CUDA availability before any training/scoring stage and raising `CudaUnavailableError`/`CudaDeviceMismatchError`/`InvalidCpuFallbackError` with no silent CPU fallback.
- **Why this ticket exists.** Split out of the former combined CUDA/hardware/pressure/recovery/telemetry/reporting mega-ticket because CUDA device ownership and its fail-loud contract (Arch §16.1) is a distinct, independently testable responsibility from hardware inventory (P1-T061), resource pressure (P1-T062), and every persistence/telemetry/reporting concern (P1-T063–P1-T067).
- **Authority references.** Arch §12.2 (`CudaGuard` port), §12.4 (implementation), §16.1 (CUDA execution: one host, one selected GPU, at most one active scientific job), §20.1 (`CudaUnavailableError`/`CudaDeviceMismatchError`/`InvalidCpuFallbackError`).
- **Dependencies.** P1-T035, P1-T036.
- **Blocks.** P1-T039, P1-T068, P1-T070.
- **Downstream consumers.** P1-T039 (preflight/executor), P1-T043/P1-T044/P1-T045 (CUDA-required adapters), P1-T068 (composition wires this adapter to the port).
- **Preconditions.** P1-T035, P1-T036 complete (ports declared).
- **Inputs.** Arch §12.2, §12.4, §16.1, §20.1.
- **Allowed scope.** `infrastructure/runtime/cuda.py`.
- **Forbidden actions.** No silent CPU fallback for a CUDA-required stage; no multi-GPU/multi-node scheduling (Phase 0 scope is one host, one selected GPU); no unsafe concurrent model ownership on one GPU.
- **Required configuration or NONE.** `DeviceSpec` (policy, `GpuIndex`) from `ExecutionPolicy`.
- **Implementation responsibilities.** Validate CUDA availability and the requested `GpuIndex`; raise the correct typed error on absence/mismatch/invalid-fallback-request; return `GpuAssignment` on success; enforce deterministic CUDA algorithm settings for `DeterminismLevel.STRICT`.
- **Required unit tests.** A CUDA-required stage with no CUDA available raises `CudaUnavailableError`, never falls back to CPU silently; a device-index mismatch raises `CudaDeviceMismatchError`.
- **Required property tests.** NONE.
- **Required contract tests.** `CudaGuard.require_cuda` satisfies its Section 12.2 signature exactly.
- **Required architecture tests.** No stage bypasses `CudaGuard` to touch CUDA directly.
- **Required integration tests.** NONE beyond the CUDA-lane tests below.
- **Required CUDA tests.** On a CUDA-available host, `require_cuda` returns a valid `GpuAssignment`; on a CUDA-unavailable host (or forced-absent test double), it raises without ever falling back to CPU.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; CUDA lane (serialized).
- **Acceptance criteria.** [ ] No silent CPU fallback. [ ] Correct typed error per failure mode. [ ] One host/one selected GPU scope enforced. [ ] Deterministic CUDA settings applied under `STRICT`.
- **Completion evidence.** Changed files (`cuda.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `CudaUnavailableError` is `RUN_BLOCKING`; never retried, never silently downgraded to CPU.
- **Stop conditions.** None.
- **Deliverables.** `CudaGuard` adapter.
- **Final review checklist.** [ ] Fail-loud, no fallback.

#### P1-T061 — Implement hardware inventory and GPU assignment

- **Ticket ID.** P1-T061
- **Title.** Implement hardware inventory and GPU assignment
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** infrastructure
- **Owner.** implementation-engineer
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `HardwareInspector` (implementation), `HardwareInventory`, `DeviceSpec` (inventory-facing use).
- **Objective.** Implement `infrastructure/runtime/hardware.py`: `HardwareInspector.inspect() -> HardwareInventory`, read-only, reporting `cuda_available = False` rather than raising, with graceful degrade when `psutil`/`pynvml` are absent.
- **Why this ticket exists.** Split out of the former combined mega-ticket because hardware inventory is a read-only, independently testable responsibility distinct from the fail-loud `CudaGuard` (P1-T060) and from resource-pressure monitoring (P1-T062), which consumes this inventory but has its own cooperative-response logic.
- **Authority references.** Arch §12.2 (`HardwareInspector` port), §12.4 (implementation, read-only), §4.1 (psutil/pynvml optional, graceful degrade to stdlib/`torch.cuda` queries), §9.4 (`HardwareInventory` fields).
- **Dependencies.** P1-T035, P1-T036.
- **Blocks.** P1-T062, P1-T066, P1-T068, P1-T070.
- **Downstream consumers.** P1-T062 (resource-pressure monitoring), P1-T066 (environment/provenance inventory adapter), P1-T039 (preflight).
- **Preconditions.** P1-T035, P1-T036 complete.
- **Inputs.** Arch §12.2, §12.4, §4.1, §9.4.
- **Allowed scope.** `infrastructure/runtime/hardware.py`.
- **Forbidden actions.** No raising on missing optional dependency (`psutil`/`pynvml` absence degrades gracefully); no write or mutation of hardware state; no CUDA ownership decision made here (that is `CudaGuard`'s responsibility).
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Query CUDA availability, GPU name/count, VRAM, PyTorch/CUDA-runtime/driver versions, CPU count, RAM via `torch.cuda`/stdlib with optional `psutil`/`pynvml` enrichment; return a complete `HardwareInventory` even when CUDA is absent.
- **Required unit tests.** `inspect()` returns `cuda_available = False` rather than raising when no GPU is present; missing `psutil`/`pynvml` degrades to the stdlib/`torch.cuda` path without error.
- **Required property tests.** NONE.
- **Required contract tests.** `HardwareInspector.inspect` satisfies its Section 12.2 signature exactly.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE beyond the CUDA-lane test below.
- **Required CUDA tests.** On a CUDA-available host, `inspect()` reports a consistent GPU name/count/VRAM matching the actual device.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; CUDA lane.
- **Acceptance criteria.** [ ] Read-only, never raises on absence. [ ] Graceful degrade without optional libraries. [ ] Complete `HardwareInventory` in every case.
- **Completion evidence.** Changed files (`hardware.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected; inspection never raises.
- **Stop conditions.** None.
- **Deliverables.** `HardwareInspector` adapter.
- **Final review checklist.** [ ] Read-only. [ ] Graceful optional-dependency degrade.

#### P1-T062 — Implement resource-pressure monitoring and cooperative throttling

- **Ticket ID.** P1-T062
- **Title.** Implement resource-pressure monitoring and cooperative throttling
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** infrastructure
- **Owner.** implementation-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ResourcePressureMonitor` (implementation), `ResourcePressureSnapshot`, `CooperativeThrottleDecision`, `ResolvedRuntimePlan` (composition), `ResourceUsageSummary`.
- **Objective.** Implement `infrastructure/runtime/resources.py`: `ResourcePressureMonitor.inspect(ResourcePressureRequest) -> ResourcePressureSnapshot`, and the cooperative throttle/pause decision logic that may only recommend actions preserving the complete resolved batch/scoring/chunk profile.
- **Why this ticket exists.** Split out of the former combined mega-ticket because resource-pressure response has a strict, narrow contract (Arch §16.6: never resize a frozen scientific batch) that must not be conflated with hardware inventory (P1-T061, read-only facts) or CUDA ownership (P1-T060, fail-loud device guard).
- **Authority references.** Arch §12.2 (`ResourcePressureMonitor` port), §12.3 (orchestrated by `application/runtime/resource_pressure.py`), §16.4 (parallelism), §16.6 (resource pressure and frozen batch semantics — the exhaustive list of permitted vs. forbidden recommendations).
- **Dependencies.** P1-T061.
- **Blocks.** P1-T039, P1-T068, P1-T070.
- **Downstream consumers.** P1-T039 (executor's cooperative-pressure orchestration consumes this adapter's snapshots and decisions).
- **Preconditions.** P1-T061 complete.
- **Inputs.** Arch §12.2, §12.3, §16.4, §16.6.
- **Allowed scope.** `infrastructure/runtime/resources.py`.
- **Forbidden actions.** No recommendation that reduces/increases a frozen training, scoring, or temporal-scoring batch size; no recommendation that changes preprocessing chunk size, gradient-accumulation value, precision, or DataLoader batch; no dynamic autotuning or OOM-backoff recommendation.
- **Required configuration or NONE.** `ResourcePressurePolicy` thresholds from `ExecutionPolicy`.
- **Implementation responsibilities.** Observe RAM/VRAM/load against policy thresholds; produce `ResourcePressureSnapshot`; produce a `CooperativeThrottleDecision` limited to: continue, deterministic non-scientific CPU-concurrency reduction (only where worker count is not itself frozen/output-affecting), pause at a safe boundary, commit-and-exit, or resume with the identical frozen profile; compose `ResolvedRuntimePlan` from device/budget/parallelism/seed-plan/resolved-batch-profile inputs; roll up `ResourceUsageSummary` (peak RAM, peak VRAM allocated/reserved, elapsed seconds).
- **Required unit tests.** A pressure recommendation never reduces a frozen training/scoring/temporal-scoring batch size, preprocessing chunk size, gradient-accumulation value, precision, or DataLoader batch; a recommendation that would violate this is rejected before it reaches the executor.
- **Required property tests.** NONE.
- **Required contract tests.** `ResourcePressureMonitor.inspect` satisfies its Section 12.2 signature exactly.
- **Required architecture tests.** NONE.
- **Required integration tests.** A synthetic elevated-pressure scenario produces only an allowed decision (pause/throttle/resume), never a batch-altering one.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; integration lanes.
- **Acceptance criteria.** [ ] No frozen-batch-altering recommendation possible. [ ] `ResolvedRuntimePlan` composed correctly. [ ] `ResourceUsageSummary` rolled up. [ ] Cooperative pause/resume preserves the frozen profile.
- **Completion evidence.** Changed files (`resources.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected; pressure responses are advisory/cooperative, never a hard failure by themselves.
- **Stop conditions.** None.
- **Deliverables.** Resource-pressure monitor and throttle-decision adapter.
- **Final review checklist.** [ ] No scientific batch mutation possible.

#### P1-T063 — Implement the CheckpointStore adapter (scientific and recovery persistence)

- **Ticket ID.** P1-T063
- **Title.** Implement the CheckpointStore adapter (scientific and recovery persistence)
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor, reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `CheckpointStore` (implementation: `find_compatible`, `save`, `save_recovery`, `load_recovery`), `CheckpointLookupResult`, `CheckpointWriteResult`, `RecoveryWriteResult`, `RecoveryLookupResult`, `RecoveryCheckpointPolicy` (enforcement), `RecoveryState` (persistence).
- **Objective.** Implement `infrastructure/persistence/checkpoints.py` and `recovery.py`: one `CheckpointStore` adapter with methodically distinct methods, roots (`SCIENTIFIC_CHECKPOINTS` vs `RECOVERY_STATE`), and namespaces for scientific checkpoints versus recovery state, so recovery state can never be resolved as a scientific checkpoint.
- **Why this ticket exists.** Split out of the former combined mega-ticket, but kept as a single ticket (rather than splitting scientific-vs-recovery further) because the architecture requires `CheckpointStore` to be **one** port with deliberately distinct methods and roots — never two separate ports and never a generic save/load pair (Arch §12.2). Splitting the implementation across two tickets would risk an inconsistent single interface.
- **Authority references.** Arch §12.2 (`CheckpointStore` port), §12.4 (implementation), §17.1 (scientific checkpoint), §17.2 (recovery state), §17.3 (persistence/resume semantics), §29.4 (invalid state 35: recovery never selected/cited as scientific).
- **Dependencies.** P1-T054, P1-T055, P1-T056, P1-T057, P1-T059.
- **Blocks.** P1-T068, P1-T070, P2-T010.
- **Downstream consumers.** P1-T037 (`CheckpointSelector` reads candidate descriptors via `find_compatible`), P2-T010 (anchor checkpoint persistence).
- **Preconditions.** P1-T054, P1-T055, P1-T056, P1-T057, P1-T059 complete.
- **Inputs.** Arch §12.2, §12.4, §17.1–17.3, §29.4.
- **Allowed scope.** `infrastructure/persistence/checkpoints.py`, `infrastructure/persistence/recovery.py`.
- **Forbidden actions.** No generic `save`/`load` pair conflating scientific and recovery state; no resolution of `RECOVERY_STATE`-rooted content as a `SCIENTIFIC_CHECKPOINTS`-rooted checkpoint even when round numbers coincide; no raw Torch state dict crossing into the application request (only opaque staged artifact references and typed descriptors).
- **Required configuration or NONE.** `RecoveryCheckpointPolicy` (cadence, retention, atomic commit, compatibility identity) from `ExecutionPolicy`.
- **Implementation responsibilities.** Implement `find_compatible`/`save` for scientific checkpoints (`kind = SCIENTIFIC`, saved only after completed roadmap-scheduled rounds); implement `save_recovery`/`load_recovery` for `RecoveryState` (safe completed-round boundaries only, never mid-round/mid-optimizer-step); validate schema/hash/training-identity/`ResolvedBatchExecutionProfile`/seeds/last-completed-round on recovery load, raising `RecoveryStateMismatchError`/`ResumeIncompatibilityError` on mismatch.
- **Required unit tests.** Recovery state can never be loaded through the scientific-checkpoint method or vice versa; a recovery load with a mismatched training identity/batch profile/seed raises the correct typed error rather than resuming.
- **Required property tests.** NONE.
- **Required contract tests.** `CheckpointStore` satisfies its full Section 12.2 signature (all four methods) with no generic fallback.
- **Required architecture tests.** No raw Torch state dict appears in `SaveScientificCheckpointRequest`/`SaveRecoveryStateRequest`.
- **Required integration tests.** A synthetic scientific checkpoint and a synthetic recovery checkpoint persist to distinct roots/namespaces and cannot be cross-loaded; a recovery load with a changed batch profile is rejected and starts fresh.
- **Required CUDA tests.** A synthetic tiny-model checkpoint save/load round-trips correctly under the CUDA lane.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; integration (persistence); CUDA lane.
- **Acceptance criteria.** [ ] Scientific and recovery methods/roots/namespaces are distinct. [ ] Recovery never resolvable as scientific. [ ] Mismatch on resume raises the correct typed error. [ ] No raw Torch state at the application boundary.
- **Completion evidence.** Changed files (`checkpoints.py`, `recovery.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `CheckpointError`/`RecoveryStateMismatchError`/`ResumeIncompatibilityError` block reuse/resume rather than silently coercing compatibility.
- **Stop conditions.** None.
- **Deliverables.** `CheckpointStore` adapter (scientific + recovery).
- **Final review checklist.** [ ] Recovery ≠ scientific, structurally.

#### P1-T064 — Implement run-state persistence and lifecycle storage

- **Ticket ID.** P1-T064
- **Title.** Implement run-state persistence and lifecycle storage
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** implementation-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `RunStateStore` (implementation: `append`, `status_of`), `StageStartRecord`, `StageCompletionRecord`, `StageReuseRecord`, `StageBlockRecord`, `StageFailureRecord`, `StageRecoveryRecord`.
- **Objective.** Implement `infrastructure/persistence/run_state.py`: `RunStateStore.append(record) -> None` and `status_of(stage_fingerprint) -> RunStatus`, persisting the six lifecycle-record kinds beneath the `RUN_STATE` root.
- **Why this ticket exists.** Split out of the former combined mega-ticket because a lifecycle record is not an artifact and does not share `ArtifactStore`'s content-addressed commit protocol (Arch §12.2); it is deliberately a narrower, distinct port.
- **Authority references.** Arch §12.2 (`RunStateStore` port, deliberately narrower than `ArtifactStore`), §12.4 (implementation), §18.3 (lifecycle records).
- **Dependencies.** P1-T054, P1-T056.
- **Blocks.** P1-T068, P1-T070.
- **Downstream consumers.** P1-T039 (executor records every stage transition here); the Phase 1 socle-readiness gate (P1-T070) verifies lifecycle records during its synthetic end-to-end run.
- **Preconditions.** P1-T054, P1-T056 complete.
- **Inputs.** Arch §12.2, §12.4, §18.3.
- **Allowed scope.** `infrastructure/persistence/run_state.py`.
- **Forbidden actions.** No use of this store as a generic `ArtifactStore` substitute; no lifecycle record missing its stage/cell/stage-fingerprint/timestamp fields.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Implement `append` for each of the six record kinds; implement `status_of` returning the current `RunStatus` for a given stage fingerprint from the persisted record history.
- **Required unit tests.** Each of the six record kinds persists with its required fields (stage, cell id, stage fingerprint, timestamps, and — for failure — the error family); `status_of` reflects the most recent recorded transition.
- **Required property tests.** NONE.
- **Required contract tests.** `RunStateStore` satisfies its Section 12.2 signature exactly (narrower than `ArtifactStore`, no content-addressed commit protocol).
- **Required architecture tests.** NONE.
- **Required integration tests.** A synthetic sequence of stage transitions (planned → running → completed/reused/blocked/failed/recovered) is recorded and queryable via `status_of`.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; integration (persistence) lanes.
- **Acceptance criteria.** [ ] All six record kinds implemented. [ ] `status_of` reflects the latest transition. [ ] Not conflated with `ArtifactStore`.
- **Completion evidence.** Changed files (`run_state.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** NONE expected; a write failure here is `STAGE_BLOCKING` for the stage attempting to record its own transition.
- **Stop conditions.** None.
- **Deliverables.** Run-state/lifecycle persistence adapter.
- **Final review checklist.** [ ] Narrower than `ArtifactStore`, as required.

#### P1-T065 — Implement the structured telemetry adapter

- **Ticket ID.** P1-T065
- **Title.** Implement the structured telemetry adapter
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** telemetry
- **Owner.** implementation-engineer
- **Supporting agents.** report-output-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `EventSink` (implementation).
- **Objective.** Implement `infrastructure/telemetry/structured_events.py`: an `EventSink` implementation backed by `structlog`'s context binding, rendering to console (`LogSink.CONSOLE`) and JSONL (`LogSink.JSONL_FILE`) per the selected `LogFormat`, non-blocking and best-effort.
- **Why this ticket exists.** Split out of the former combined mega-ticket because the telemetry adapter is a distinct rendering responsibility from CUDA/hardware/pressure (P1-T060–P1-T062), checkpoint/run-state persistence (P1-T063–P1-T064), the environment/provenance adapter (P1-T066), and report renderers (P1-T067); it implements the port declared in P1-T051.
- **Authority references.** Arch §4.1 (structlog role), §12.2 (`EventSink` port), §12.4 (implementation), §19.1–19.3 (event model, rendering rules, relationship to provenance).
- **Dependencies.** P1-T051, P1-T035.
- **Blocks.** P1-T068, P1-T070.
- **Downstream consumers.** Every stage/service that publishes a `StructuredEvent` depends on this adapter being wired at composition (P1-T068).
- **Preconditions.** P1-T051, P1-T035 complete.
- **Inputs.** Arch §4.1, §12.2, §12.4, §19.1–19.3.
- **Allowed scope.** `infrastructure/telemetry/structured_events.py`.
- **Forbidden actions.** No blocking of scientific computation on rendering failure; no scientific value logged as its source of truth; no array/per-sample score/secret/dataset-row/full-config-dump rendered.
- **Required configuration or NONE.** `LogSink`/`LogFormat` selection from `ExecutionPolicy`/composition.
- **Implementation responsibilities.** Bind `structlog` context per event; render human-readable console output and JSONL per the selected sink/format; ensure a rendering failure never propagates into scientific computation; log an exception once at its translation boundary, never re-logged as it propagates.
- **Required unit tests.** A rendering failure (e.g., a broken sink) does not raise into the caller; an exception is logged exactly once at its translation boundary.
- **Required property tests.** NONE.
- **Required contract tests.** `EventSink.publish` satisfies its Section 12.2 signature exactly.
- **Required architecture tests.** No scientific value is sourced only from this adapter (every scientific value must also exist in a persisted artifact).
- **Required integration tests.** A synthetic sequence of `StructuredEvent`s renders correctly to both console and JSONL sinks; parallel workers' events preserve `worker_role`/`process_id`/`gpu_index` for attribution.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; integration (reporting) lanes.
- **Acceptance criteria.** [ ] Non-blocking, best-effort rendering. [ ] No scientific value only in a log. [ ] Exception logged once at the boundary. [ ] Worker attribution preserved.
- **Completion evidence.** Changed files (`structured_events.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A sink failure never propagates into scientific computation; it is itself logged once, best-effort.
- **Stop conditions.** None.
- **Deliverables.** `EventSink` adapter.
- **Final review checklist.** [ ] Diagnostic only, never scientific source of truth.

#### P1-T066 — Implement the environment and provenance inventory adapter

- **Ticket ID.** P1-T066
- **Title.** Implement the environment and provenance inventory adapter
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** persistence
- **Owner.** reproducibility-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `CodeStateProvider` (implementation), `DependencyLockStateProvider` (implementation), `Clock` (implementation; frozen in tests).
- **Objective.** Implement the infrastructure providers that produce `EnvironmentInventory`, `CodeState`, and `DependencyLockState` domain records (Arch §9.5): `CodeStateProvider` (commit identity, clean/dirty state, dirty-diff hash where permitted), `DependencyLockStateProvider` (exact dependency-lock identity and pinned versions), and `Clock.now() -> datetime`.
- **Why this ticket exists.** Split out of the former combined mega-ticket because environment/provenance inventory is a read-only, independently testable adapter responsibility distinct from hardware inventory (P1-T061, which feeds `HardwareInventory` specifically) and from the telemetry adapter (P1-T065, which renders events, not provenance).
- **Authority references.** Arch §9.5 (`EnvironmentInventory`, `CodeState`, `DependencyLockState`, provenance types), §12.4 (`CodeStateProvider`/`DependencyLockStateProvider`/`Clock`), §22.4 (pre-specification provenance).
- **Dependencies.** P1-T061.
- **Blocks.** P1-T068, P1-T070.
- **Downstream consumers.** Every `ProvenanceRecord` construction (Phase 2 onward) and every campaign-freeze ticket (P3-T002, P5-T008) depend on this adapter's output.
- **Preconditions.** P1-T061 complete.
- **Inputs.** Arch §9.5, §12.4, §22.4.
- **Allowed scope.** `infrastructure/runtime/` (provider modules) and the domain-record construction boundary they feed.
- **Forbidden actions.** No environment fact entering scientific identity or a stage fingerprint; no `Clock` call outside this provider (tests freeze it explicitly); no dependency-lock or code-state fact fabricated when unavailable — record `UNVERIFIED`/absent explicitly instead.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Implement `CodeStateProvider` reading VCS commit/clean-dirty state; implement `DependencyLockStateProvider` reading the committed lock (P0-T004); implement `Clock.now()`; assemble pinned exact versions of scikit-learn/PyArrow/NumPy/SciPy/blake3/msgspec into `EnvironmentInventory` alongside `HardwareInventory` (P1-T061).
- **Required unit tests.** A dirty working tree is reported as dirty with a diff hash where permitted, never silently reported clean; `Clock` is injectable/frozen in test contexts.
- **Required property tests.** NONE.
- **Required contract tests.** `CodeStateProvider`/`DependencyLockStateProvider` produce exactly the fields required by `CodeState`/`DependencyLockState` (Arch §9.5).
- **Required architecture tests.** No environment/provenance fact enters a stage fingerprint or scientific specification.
- **Required integration tests.** A synthetic clean checkout and a synthetic dirty checkout produce correctly distinguished `CodeState` records; the dependency-lock provider matches the P0-T004 committed lock.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; integration lanes.
- **Acceptance criteria.** [ ] Dirty state never reported clean. [ ] Pinned versions recorded exactly. [ ] No environment fact in scientific identity. [ ] `Clock` frozen in tests.
- **Completion evidence.** Changed files (provider modules); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `EnvironmentIncompatibilityError` when a required pinned version is absent; recorded as a blocker, never fabricated.
- **Stop conditions.** None.
- **Deliverables.** Environment/provenance inventory providers.
- **Final review checklist.** [ ] No fabricated provenance fact.

#### P1-T067 — Implement report renderers

- **Ticket ID.** P1-T067
- **Title.** Implement report renderers
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ReportRenderer` (implementations).
- **Objective.** Implement `infrastructure/reporting/markdown.py`, `latex.py`, and `matplotlib.py`: `ReportRenderer` implementations consuming traced, framework-free table/figure specifications from `analysis/` and producing Markdown/LaTeX/CSV/Parquet/JSON (markdown/latex) or SVG/PNG/PDF (matplotlib), never altering a scientific value.
- **Why this ticket exists.** Split out of the former combined mega-ticket because rendering is a distinct, format-specific responsibility that consumes the analysis reporting vocabulary (P1-T052) and the result-freeze/tracing gate (already scoped to P1-T040), independent of CUDA/hardware/pressure/persistence/telemetry concerns.
- **Authority references.** Arch §12.2 (`ReportRenderer` port), §12.4 (implementation), §22.1 (typed outputs; no Sankey; renderers never alter a scientific value), §22.3 (analysis/trace/render diagram).
- **Dependencies.** P1-T052, P1-T040.
- **Blocks.** P1-T068, P1-T070.
- **Downstream consumers.** Every Phase 2 onward reporting stage that renders a traced table/figure/wording block.
- **Preconditions.** P1-T052, P1-T040 complete.
- **Inputs.** Arch §12.2, §12.4, §22.1, §22.3.
- **Allowed scope.** `infrastructure/reporting/markdown.py`, `latex.py`, `matplotlib.py`.
- **Forbidden actions.** No rendering before `TableFigureTracer.trace` succeeds (a `TRACE_REFUSED` specification is never rendered); no renderer alters a scientific value; no plotting-framework import outside `matplotlib.py`; no Sankey rendering path.
- **Required configuration or NONE.** Required-format list from `ReportingPolicy`.
- **Implementation responsibilities.** Implement Markdown/LaTeX/CSV/Parquet/JSON renderers consuming `analysis/tables/`+`analysis/figures/` specifications; implement SVG/PNG/PDF rendering via matplotlib; ensure every renderer is a pure format transform with no value mutation.
- **Required unit tests.** A renderer never changes a numeric value present in its input specification (round-trip value equality); an untraced (`TRACE_REFUSED`) specification is never accepted by any renderer.
- **Required property tests.** NONE.
- **Required contract tests.** Every `ReportRenderer` implementation satisfies the Section 12.2 signature.
- **Required architecture tests.** `analysis/` is never imported by anything except through the traced specification handed to these renderers; no plotting framework leaks outside `matplotlib.py`.
- **Required integration tests.** A synthetic traced table/figure renders correctly and identically (content) across every required format for its `ReportArtifactType`.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; integration (reporting) lanes.
- **Acceptance criteria.** [ ] Renders every required format. [ ] Never alters a value. [ ] Never renders an untraced specification. [ ] No Sankey.
- **Completion evidence.** Changed files (three renderer modules); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** `ReportingError` on a render failure; never a silently degraded or partial output.
- **Stop conditions.** None.
- **Deliverables.** Format-specific report renderers.
- **Final review checklist.** [ ] Faithful, trace-gated rendering.

#### P1-T068 — Implement the composition root and strategy registries

- **Ticket ID.** P1-T068
- **Title.** Implement the composition root and strategy registries
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** composition
- **Owner.** implementation-engineer
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `composition/root.py` use-case entrypoints (e.g., `run_experiment`), `composition/registries.py` (`EnumMap` strategy registries, `StageRunnerRegistry`).
- **Objective.** Implement `composition/root.py` (construct concrete adapters, bind them to `application/ports/*` Protocols, assemble the concrete application services, select explicit strategy implementations, map resolved configuration into the object graph, expose complete use-case entrypoints) and `composition/registries.py` (`EnumMap` strategy registries populated once, plus `StageRunnerRegistry`).
- **Why this ticket exists.** Split out of the former combined composition/CLI mega-ticket because `composition` and `cli` are distinct architectural layers with distinct responsibilities and distinct forbidden actions (Arch §3.1, §12.5); `composition` is the sole wiring place and the only layer with edges to every other layer, while `cli` has exactly one outbound edge (to `composition`) and must never construct anything itself. A single ticket type cannot honestly describe both.
- **Authority references.** Arch §3.1 (composition depends on every layer), §3.2 (forbidden: framework import directly in composition), §12.5 (composition root and CLI separation), §12.6 (stage dispatch and rendering), §29.2 (composition is not the CLI's responsibility).
- **Dependencies.** P1-T039, P1-T042, P1-T043, P1-T044, P1-T045, P1-T046, P1-T054, P1-T055, P1-T056, P1-T057, P1-T058, P1-T059, P1-T060, P1-T061, P1-T062, P1-T063, P1-T064, P1-T065, P1-T066, P1-T067.
- **Blocks.** P1-T069, P1-T050, P1-T070.
- **Downstream consumers.** P1-T069 (CLI boundary invokes composition use cases), P1-T050 (architecture-boundary test suite verifies composition's exclusive wiring role), P1-T070 (socle-readiness gate exercises a use case end-to-end).
- **Preconditions.** All twenty listed infrastructure/application tickets complete.
- **Inputs.** Every application port (P1-T034–P1-T036) and every infrastructure adapter listed in Dependencies.
- **Allowed scope.** `composition/root.py`, `composition/registries.py`.
- **Forbidden actions.** No framework import directly in `composition` (frameworks are reached only through the `infrastructure` adapters composition constructs); no service-locator pattern; no scientific computation performed by composition itself.
- **Required configuration or NONE.** Resolved configuration (scientific/execution/artifact/reporting specs) mapped into the object graph.
- **Implementation responsibilities.** Construct every concrete adapter; bind each to its `application/ports/*` Protocol; assemble the concrete application services (`ExperimentPlanner`, `ExecutionPreflight`, `ScoreReuseGate`, `CheckpointSelector`, `PolicyEvaluator`, `AnchorReproductionGate`, `FeasibilityGateEvaluator`, `PlanExecutor`, `TableFigureTracer`); populate `composition/registries.py`'s `EnumMap` strategy registries (e.g., `ThresholdConstructionKind` → `ThresholdStrategy` implementation) and the exhaustive `StageRunnerRegistry`; expose `run_experiment(cell: ExperimentCell) -> ExecutionSummary` and any other complete use-case entrypoints.
- **Required unit tests.** Every use-case entrypoint resolves its full object graph without a missing binding; `StageRunnerRegistry` is exhaustive over `PipelineStage` (a missing stage handler is a construction-time failure, not a silent gap).
- **Required property tests.** NONE.
- **Required contract tests.** Every registered strategy implementation satisfies its declared port's contract.
- **Required architecture tests.** No framework import appears directly in `composition/root.py` or `registries.py` outside of constructing a named `infrastructure` adapter; `composition` is the only node with edges to every other layer.
- **Required integration tests.** A synthetic use case (with fake/test-double infrastructure where needed) runs end-to-end through the composed object graph.
- **Required CUDA tests.** NONE (CUDA-specific behavior is exercised by the adapters themselves; composition only wires them).
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract; architecture; integration (synthetic) lanes.
- **Acceptance criteria.** [ ] Composition is the sole wiring place. [ ] Registries exhaustive over `PipelineStage`. [ ] No direct framework import. [ ] Use cases exposed and resolve fully.
- **Completion evidence.** Changed files (`composition/root.py`, `registries.py`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A missing binding or unregistered stage is a construction-time failure, never a runtime silent gap.
- **Stop conditions.** Stop if a required infrastructure adapter dependency is incomplete; do not wire a partial adapter.
- **Deliverables.** Composition root and strategy registries.
- **Final review checklist.** [ ] No service locator. [ ] No framework leakage into composition itself.

#### P1-T069 — Implement the CLI boundary and command invocation

- **Ticket ID.** P1-T069
- **Title.** Implement the CLI boundary and command invocation
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** cli
- **Owner.** implementation-engineer
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (CLI owns no domain/application type; it renders and exits).
- **Objective.** Implement `cli/main.py` and `cli/commands/`: parse command-line input into a typed request, invoke exactly one `composition` use-case entrypoint, render the returned boundary result (or a typed failure, via `rich`) with rendering confined to `infrastructure` reporting reached only through composition, and convert the outcome into a process exit code.
- **Why this ticket exists.** Split out of the former combined composition/CLI mega-ticket because the CLI has a single outbound edge (to `composition`) and a narrow, purely boundary-facing responsibility (Arch §3.2, §12.5) that must never be conflated with wiring, adapter construction, or path resolution, all of which belong exclusively to P1-T068.
- **Authority references.** Arch §3.2 (`cli →` only `composition` and shared boundary result/error types), §12.5 (CLI never instantiates an adapter, never wires a dependency, never resolves a path itself), §12.6 (CLI renders typed errors and preflight findings with `rich`, translated through composition), §29.2 (the CLI is not the composition root).
- **Dependencies.** P1-T068.
- **Blocks.** P1-T050, P1-T070.
- **Downstream consumers.** P1-T050 (architecture-boundary test suite verifies the CLI's single outbound edge), P1-T070 (socle-readiness gate exercises the CLI use-case path).
- **Preconditions.** P1-T068 complete.
- **Inputs.** The use-case entrypoints exposed by `composition/root.py`.
- **Allowed scope.** `cli/main.py`, `cli/commands/`.
- **Forbidden actions.** No adapter instantiation; no dependency wiring; no filesystem path resolution; no scientific or stage-orchestration logic; no `infrastructure`/`config`/framework import directly in `cli`.
- **Required configuration or NONE.** NONE (the CLI parses arguments only; configuration loading happens through the use case it invokes).
- **Implementation responsibilities.** Parse CLI arguments into a typed request; call the appropriate `composition` use-case entrypoint; render the boundary result or typed failure via `rich`; map a `DatpCoreError` to the correct process exit code.
- **Required unit tests.** The CLI never imports `infrastructure`, `config`, or a framework directly; a typed failure returned by the use case maps to a distinct, correct exit code per error family.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** `cli` has exactly one outbound edge (to `composition`); no adapter construction or path resolution occurs inside `cli/`.
- **Required integration tests.** A synthetic CLI invocation of a use case (with test-double infrastructure) renders the expected boundary result and exit code.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; architecture; integration (synthetic) lanes.
- **Acceptance criteria.** [ ] CLI wires nothing. [ ] CLI resolves no path. [ ] Exactly one outbound edge to `composition`. [ ] Correct exit code per typed failure.
- **Completion evidence.** Changed files (`cli/main.py`, `cli/commands/`); commands run and results; cleanup confirmation; confirmation of no unrelated modification.
- **Failure and blocker behavior.** A `DatpCoreError` translates to a legible boundary message and a distinct exit code; the CLI never swallows or reinterprets it.
- **Stop conditions.** None.
- **Deliverables.** CLI boundary and command invocation.
- **Final review checklist.** [ ] CLI is thin. [ ] No wiring, no path resolution, no adapter construction.

#### P1-T049 — Implement the analysis table/figure/wording/report-model specification layer

- **Ticket ID.** P1-T049
- **Title.** Implement the analysis table/figure/wording/report-model specification layer
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `analysis/{tables,figures,wording,report_models}.py` specification modules. Report identity (spec side).
- **Objective.** Implement `analysis/{tables,figures,wording,report_models}.py`: framework-free table/figure specifications (one module per `TableType`/`FigureType` family needing one), `ClaimOutcome`-driven wording selection, and shared report-model construction derived only from domain result types.
- **Why this ticket exists.** `analysis` imports domain only and no framework/persistence; it produces specifications, not rendered output; eligibility/conformal coverage occupy disjoint columns; no Sankey.
- **Authority references.** Arch §5.1, §22.1, §3.5 (analysis ownership), §6.6.
- **Dependencies.** P1-T052, P1-T026, P1-T027.
- **Blocks.** P2-T019, P4-T021.
- **Downstream consumers.** P2-T019 and P4-T021 consume this specification layer directly.
- **Preconditions.** P1-T052, P1-T026, P1-T027 complete.
- **Inputs.** Arch §5.1, §22.1, §3.5, §6.6.
- **Allowed scope.** `analysis/`.
- **Forbidden actions.** No framework/persistence/path/rendering in analysis; no Sankey; no generic coverage field; no repository read.
- **Required configuration or NONE.** Reporting policy consumed via mapped specs.
- **Implementation responsibilities.** Framework-free spec dataclasses; wording selection keyed on `ClaimOutcome`; report models from domain results only.
- **Required unit tests.** Framework-free construction; disjoint eligibility/conformal columns; wording selection per outcome.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** `analysis` imports no framework/persistence.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; architecture; strict type lanes.
- **Acceptance criteria.** [ ] Analysis framework-free. [ ] No Sankey. [ ] Eligibility/conformal columns disjoint. [ ] Wording keyed on `ClaimOutcome`.
- **Completion evidence.** Changed files (`analysis/tables.py`, `figures.py`, `wording.py`, `report_models.py`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** NONE expected; rendering errors belong to infrastructure, not this specification layer.
- **Stop conditions.** None.
- **Deliverables.** Analysis specification layer.
- **Final review checklist.** [ ] Domain-only imports.

#### P1-T050 — Implement the architecture-boundary and framework-confinement test suite

- **Ticket ID.** P1-T050
- **Title.** Implement the architecture-boundary and framework-confinement test suite
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** architecture
- **Owner.** architecture-cleaner
- **Supporting agents.** —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `tests/architecture/test_dependency_rules.py`, `test_framework_confinement.py`, `test_no_forbidden_module_names.py`, `test_no_module_side_effects.py`, `test_no_cycles.py`.
- **Objective.** Implement `tests/architecture/` completely: `test_dependency_rules.py`, `test_framework_confinement.py`, `test_no_forbidden_module_names.py`, `test_no_module_side_effects.py`, `test_no_cycles.py`, plus assertions that every closed union is `assert_never`-exhausted and no root `experiments/` package exists.
- **Why this ticket exists.** These enforce the Arch §3 dependency graph, framework confinement, naming, side-effect-free imports, and acyclicity at test time with clear diffs.
- **Authority references.** Arch §3.3, §21.2 (architecture tests), §29.2.
- **Dependencies.** P0-T011, P0-T012, P1-T068, P1-T069.
- **Blocks.** P1-T070.
- **Downstream consumers.** P1-T070 (the Phase 1 socle-readiness gate) depends on this suite passing.
- **Preconditions.** P0-T011, P0-T012, P1-T068, P1-T069 complete.
- **Inputs.** Arch §3.3, §21.2, §29.2.
- **Allowed scope.** `tests/architecture/`.
- **Forbidden actions.** No production import of tests; no relaxation to pass.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** pytest-archon assertions matching the §3.3 diagram; forbidden-name scan; side-effect-free import assertion; cycle detection; exhaustiveness verification.
- **Required unit tests.** NONE (this ticket is itself the test suite).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** All five architecture tests present and passing on the full socle.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Architecture lane; import-linter.
- **Acceptance criteria.** [ ] All five architecture tests present and passing. [ ] No framework object crosses a port. [ ] No forbidden name/cycle/side effect. [ ] No root `experiments/`.
- **Completion evidence.** Changed files (`tests/architecture/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** A boundary breach fails the lane; no relaxation is permitted to pass.
- **Stop conditions.** None.
- **Deliverables.** Architecture test suite.
- **Final review checklist.** [ ] Matches §3.3 exactly.

#### P1-T070 — Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test

- **Ticket ID.** P1-T070
- **Title.** Implement the lineage/reuse/atomicity/determinism validation and synthetic end-to-end socle test
- **Phase.** 1
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** application
- **Owner.** reproducibility-auditor
- **Supporting agents.** artifact-lineage-auditor, experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** NONE
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `tests/system/synthetic/` end-to-end suite; reuse/invalidation, atomicity, checkpoint/recovery-separation, deterministic-seed, and batching-equivalence test suites; campaign-execution-prohibition guard. **This is the Phase 1 socle-readiness gate**, renumbered from the prior revision's `P1-T051` as part of the Phase 1 mega-ticket decomposition; the ticket ID `P1-T051` is retired and now denotes the unrelated "application telemetry vocabulary and contracts" ticket, and every downstream reference to the old gate ID has been updated to `P1-T070`.
- **Objective.** Implement `tests/system/synthetic/` (a reduced synthetic end-to-end run of the full stage sequence), the reuse/invalidation, atomicity, checkpoint/recovery-separation, deterministic-seed, and batching-equivalence suites, and a campaign-execution-prohibition guard asserting no Phase 1 path can perform real scientific execution.
- **Why this ticket exists.** This is the socle-readiness gate: it proves the whole socle works on synthetic data, that B1–B4 share one calibration/test set, that atomicity/determinism hold, and that no real-data run is reachable.
- **Authority references.** Arch §21.2 (system/synthetic, reuse tests), §13.3, §16.7, §29; Section F (Phase 1 gate).
- **Dependencies.** P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, P1-T051–P1-T069 (every other Phase 1 ticket).
- **Blocks.** P2-T001.
- **Downstream consumers.** P2-T001 (and all of Phase 2) depends on this gate passing before any anchor-implementation work begins.
- **Preconditions.** Every Phase 1 implementation ticket P1-T001 through P1-T069 (excluding this gate itself) is complete and evidence-recorded.
- **Inputs.** Arch §21.2, §13.3, §16.7, §29; Section F.
- **Allowed scope.** `tests/system/synthetic/`, `tests/integration/{learning,persistence}/`, `tests/property/`.
- **Forbidden actions.** No real-data path; no scientific output root written; no campaign execution.
- **Required configuration or NONE.** Synthetic test profiles from `configs/tests/` (P1-T053).
- **Implementation responsibilities.** Synthetic end-to-end run; reuse assertions (one calibration/test id for B1–B4, role/lineage substitution fails); atomicity/recovery/determinism/batching-equivalence tests; a guard test that real-data execution is unreachable in Phase 1.
- **Required unit tests.** NONE.
- **Required property tests.** Reuse/invalidation and batching-equivalence properties.
- **Required contract tests.** NONE.
- **Required architecture tests.** Campaign-execution-prohibition guard: no real-data path is reachable from any Phase 1 module.
- **Required integration tests.** Atomicity; determinism; checkpoint/recovery-separation (learning, persistence lanes).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic end-to-end run of the full stage sequence.
- **Validation commands.** Full Nox validation (all lanes) on synthetic data.
- **Acceptance criteria.** [ ] All P1-T001–P1-T069 are complete; no socle capability remains unowned. [ ] Synthetic end-to-end passes. [ ] B1–B4 share one calibration/test id; substitution fails. [ ] Atomicity/determinism/batching-equivalence pass. [ ] Telemetry, reporting specifications, artifact schema/version handling, persistence, recovery, composition, and CLI contracts are exercised. [ ] No real-data path reachable. [ ] Socle-readiness gate green.
- **Completion evidence.** Changed files (`tests/system/synthetic/`, `tests/integration/`, `tests/property/`); commands run and results; cleanup confirmation.
- **Failure and blocker behavior.** Any suite failure fails the gate; the gate blocks Phase 2 entry until green.
- **Stop conditions.** Stop and block Phase 2 if any socle suite fails.
- **Deliverables.** Synthetic system test + socle validation suites + prohibition guard.
- **Final review checklist.** [ ] Gate green on synthetic data only.

### Phase 2 — Complete DATP Anchor Implementation

> **Phase-wide note (applies to every P2 ticket).** No real anchor scientific execution occurs in Phase 2: implementation is validated on deterministic synthetic arrays/datasets and, where source facts are needed, read-only source/schema/metadata inspection only. No reduced-seed, reduced-round, reduced-row, or ad hoc real-data run is permitted. No ticket assumes a specific seed sequence beyond the resolved authoritative seed specification. Campaign scope is `ANCHOR` (implementation for the anchor campaign) but Sci-exec remains `FORBIDDEN` (implementation/inspection) or `PLANNING_ONLY` (readiness). "Completion evidence" is the standard five-heading report plus resulting identities and any recovered-semantics blockers carried into `ScientificReadinessResult`.

#### P2-T001 — Recover DATP behavioral semantics from the reference repository (read-only)

- **Ticket ID.** P2-T001
- **Title.** Recover DATP behavioral semantics from the reference repository (read-only)
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** datp-protocol-guardian
- **Supporting agents.** data-pipeline-engineer, federated-learning-engineer, threshold-policy-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE (evidence gathering only)
- **Objective.** Read `/home/naslouby/Projects/datp` (read-only) to recover the original DATP autoencoder architecture, optimizer/scheduler, preprocessing behavior, client construction, train/calibration/test split semantics, FedAvg behavior, **historical anchor checkpoint schedule and selection evidence**, calibration/test-score semantics, threshold-policy formulas, and evaluation/interpretation — as behavioral evidence only.
- **Why this ticket exists.** These semantics are genuine readiness blockers (Arch §27); they must be recovered from behavioral evidence, never guessed, and never used as a source-layout/migration template.
- **Authority references.** Arch §1 (reference project), §27 (blockers); Road §5 (reference-only), §17.
- **Dependencies.** P1-T070.
- **Blocks.** P2-T002, P2-T004, P2-T008.
- **Downstream consumers.** P2-T002 (recovered-semantics register), P2-T004 (N-BaIoT source adapter), P2-T008 (training semantics).
- **Preconditions.** P1-T070 complete.
- **Inputs.** Arch §1, §27; Road §5, §17.
- **Allowed scope.** Read-only inspection of the reference repository; recording findings into the recovered-semantics register (P2-T002).
- **Forbidden actions.** No copying of the reference layout; no shim/alias/migration; no import from the reference project; no execution of the reference project.
- **Required configuration or NONE.** NONE (evidence only).
- **Implementation responsibilities.** Extract AE architecture/activation/bottleneck, optimizer/lr/scheduler, preprocessing strategy/scope, client/device mapping, split semantics, FedAvg weighting/E/participation, checkpoint schedule/selection, score derivation, threshold formulas, evaluation logic; explicitly distinguish the historical anchor protocol from the journal {25,50,75,100,125,150,200} protocol. If historical schedule or selection evidence is absent, record `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` and prohibit guessed rounds or calling a journal-protocol run a historical reproduction.
- **Required unit tests.** NONE (read-only discovery).
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Read-only inspection.
- **Acceptance criteria.** [ ] Each Arch §27 anchor blocker has recovered evidence or is recorded as unresolved. [ ] No reference layout copied. [ ] No import from the reference project.
- **Completion evidence.** Standard report + list of resolved/unresolved semantics.
- **Failure and blocker behavior.** Where evidence is ambiguous or absent, record a typed readiness blocker rather than guessing.
- **Stop conditions.** Stop and record a blocker for any semantic that cannot be recovered from behavioral evidence.
- **Deliverables.** Recovered-semantics evidence feeding P2-T002.
- **Final review checklist.** [ ] Behavior only, no layout reuse.

#### P2-T002 — Record the recovered-semantics register in the master log

- **Ticket ID.** P2-T002
- **Title.** Record the recovered-semantics register in the master log
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** datp-protocol-guardian
- **Supporting agents.** NONE
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** Recovered-semantics register structure (informal documentation)
- **Objective.** Record a recovered-semantics register (a section appended to this master log) mapping each anchor semantic to its recovered value or an explicit unresolved blocker, including a separate `AnchorHistoricalCheckpointProtocol` decision distinct from `JournalCheckpointProtocol`, so downstream anchor tickets cite a single register.
- **Why this ticket exists.** Anchor implementation tickets must cite recovered semantics; a single register prevents divergent assumptions and makes blockers explicit before implementation.
- **Authority references.** Arch §27; Road §17; this backlog (single-file discipline).
- **Dependencies.** P2-T001.
- **Blocks.** P2-T020.
- **Downstream consumers.** P2-T020 and all downstream anchor tickets that cite recovered semantics from the single register.
- **Preconditions.** P2-T001 complete.
- **Inputs.** Arch §27; Road §17; recovered evidence from P2-T001.
- **Allowed scope.** Appending the register to this master log only.
- **Forbidden actions.** No separate register file; no guessed values presented as recovered; no scientific execution.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Tabulate each semantic → recovered value / blocker + evidence pointer; for the checkpoint protocol, record the recovered anchor schedule and selection rule or `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED`, the authoritative evidence needed to resolve it, affected identities, and blocked tickets P2-T008 through P3-T011. Mark print-grade blockers.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Register completeness cross-check against Arch §27.
- **Acceptance criteria.** [ ] Every anchor semantic present with value or blocker. [ ] Anchor and journal checkpoint protocols explicitly distinguished. [ ] Unresolved anchor schedule blocks affected training/selection/readiness/execution tickets. [ ] Evidence pointers recorded. [ ] Single register in this log.
- **Completion evidence.** Standard report.
- **Failure and blocker behavior.** Unresolved semantics are marked as blockers carried into readiness.
- **Stop conditions.** NONE.
- **Deliverables.** Recovered-semantics register (in this log).
- **Final review checklist.** [ ] No guessed value marked recovered.

#### P2-T003 — Inspect the N-BaIoT source and feature schema

- **Ticket ID.** P2-T003
- **Title.** Inspect the N-BaIoT source and feature schema
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** data-pipeline-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `DatasetSourceInspectionResult`, `DatasetSourceManifest`, `FeatureSchemaManifest`
- **Objective.** Inspect the N-BaIoT source (read-only) to produce `DatasetSourceInspectionResult`, `DatasetSourceManifest`, and `FeatureSchemaManifest` (ordered features, input dimension), recording source-row identity scheme and timestamp evidence (or its absence).
- **Why this ticket exists.** Source/schema facts are recorded, never partitioned/preprocessed here; input dimension and feature order feed every downstream identity.
- **Authority references.** Arch §9.1, §9.5, §12.3 (`DatasetSourceInspector`).
- **Dependencies.** P2-T001, P1-T032.
- **Blocks.** P2-T004.
- **Downstream consumers.** P2-T004 (N-BaIoT source adapter) consumes source/schema manifests and identity scheme.
- **Preconditions.** P2-T001, P1-T032 complete.
- **Inputs.** Arch §9.1, §9.5, §12.3.
- **Allowed scope.** Read-only inspection; manifest recording under `data/manifests/`.
- **Forbidden actions.** No partition/split/fit/transform; no training; no scientific execution.
- **Required configuration or NONE.** N-BaIoT dataset config section (input_dim to be verified from the manifest).
- **Implementation responsibilities.** Run source inspection; record manifests and source-row identity scheme.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): inspection produces a schema manifest with a stable feature order (on a synthetic-schema fixture if the real source is unavailable). Fixed-input regression check: schema-manifest shape.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); manifest inspection.
- **Acceptance criteria.** [ ] Source and feature-schema manifests produced. [ ] Feature order/input dimension recorded. [ ] Timestamp evidence recorded (present/absent). [ ] No partitioning/preprocessing performed.
- **Completion evidence.** Standard report + recorded identities.
- **Failure and blocker behavior.** `DatasetError` on unreadable/inconsistent source.
- **Stop conditions.** Stop if the feature schema is inconsistent with recovered semantics; record a blocker.
- **Deliverables.** N-BaIoT source/schema manifests.
- **Final review checklist.** [ ] Inspection only.

#### P2-T004 — Implement the N-BaIoT source adapter and deterministic source-row identity

- **Ticket ID.** P2-T004
- **Title.** Implement the N-BaIoT source adapter and deterministic source-row identity
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** data-pipeline-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `DatasetSourceInspector` (N-BaIoT implementation), source-row identity scheme
- **Objective.** Implement the N-BaIoT chunked source adapter behind `DatasetSourceInspector`/data ports, with a deterministic, stable source-row identity scheme preserved through downstream stages.
- **Why this ticket exists.** Deterministic source-row identity underpins lineage, partition membership, and reuse; it must be stable and chunk-order-independent.
- **Authority references.** Arch §16.3, §9.1, §25 (add a dataset), §13.5.
- **Dependencies.** P2-T003, P1-T042.
- **Blocks.** P2-T005.
- **Downstream consumers.** P2-T005 (physical-device partitioning) consumes deterministic source-row identity and chunked reader.
- **Preconditions.** P2-T003, P1-T042 complete.
- **Inputs.** Arch §16.3, §9.1, §25, §13.5; N-BaIoT source/schema manifests from P2-T003.
- **Allowed scope.** `infrastructure/data/inspection.py` N-BaIoT path; source-row identity.
- **Forbidden actions.** No whole-dataset load; no training/scoring; no real scientific run; no carrier crossing upward.
- **Required configuration or NONE.** N-BaIoT source config (paths bound in composition, not domain).
- **Implementation responsibilities.** Chunked reader; deterministic row identity; manifest hashes.
- **Required unit tests.** NONE.
- **Required property tests.** Row-identity determinism.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): stable source-row identity under chunked and single-pass reads; bounded memory.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); property lanes.
- **Acceptance criteria.** [ ] Deterministic source-row identity. [ ] Chunked read equals reference. [ ] Bounded memory. [ ] No scientific run.
- **Completion evidence.** Standard report + source identity.
- **Failure and blocker behavior.** `DatasetError` on integrity failure.
- **Stop conditions.** NONE.
- **Deliverables.** N-BaIoT source adapter.
- **Final review checklist.** [ ] Row identity stable.

#### P2-T005 — Implement physical-device (9-client) partitioning

- **Ticket ID.** P2-T005
- **Title.** Implement physical-device (9-client) partitioning
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** data-pipeline-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `ClientDefinitionStrategy.NATURAL_DEVICE`, `ClientPartitionManifest`, `ClientRoster`
- **Objective.** Implement the natural physical-device partitioner (`ClientDefinitionStrategy.NATURAL_DEVICE`, K=9) producing a source-row-preserving `ClientPartitionManifest` and `ClientRoster` for Regime A.
- **Why this ticket exists.** Regime A is the confirmatory nine-device natural split; partition identity feeds all downstream identities.
- **Authority references.** Arch §8.3 (`RegimeCompatibilitySpec` A→9 NATURAL_DEVICE), §9.1, §12.3.
- **Dependencies.** P2-T004, P1-T019.
- **Blocks.** P2-T006.
- **Downstream consumers.** P2-T006 (train/calibration/test splits) consumes nine-client roster and partition manifest.
- **Preconditions.** P2-T004, P1-T019 complete.
- **Inputs.** Arch §8.3, §9.1, §12.3; N-BaIoT source adapter from P2-T004.
- **Allowed scope.** `infrastructure/data/partitioning.py` natural-device path.
- **Forbidden actions.** No synthetic/Dirichlet partition here; no file-pseudo-client; no scientific run.
- **Required configuration or NONE.** Regime A partition config.
- **Implementation responsibilities.** Nine-device mapping; every source row preserved exactly once; partition manifest/identity.
- **Required unit tests.** NONE.
- **Required property tests.** Row conservation and no overlap.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): nine clients; source-row conservation; deterministic roster.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); property lanes.
- **Acceptance criteria.** [ ] Exactly nine clients. [ ] Every source row mapped once. [ ] Deterministic roster/identity. [ ] No synthetic partition.
- **Completion evidence.** Standard report + partition identity.
- **Failure and blocker behavior.** `PartitionError` on unmapped/duplicated rows.
- **Stop conditions.** Stop if device identity cannot be recovered unambiguously; record a blocker.
- **Deliverables.** Nine-device partitioner.
- **Final review checklist.** [ ] Natural device only.

#### P2-T006 — Implement benign train/calibration and held-out benign/malicious test splits

- **Ticket ID.** P2-T006
- **Title.** Implement benign train/calibration and held-out benign/malicious test splits
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** data
- **Owner.** data-pipeline-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** Split builder, `SplitType.TRAIN`, `SplitType.CALIBRATION`, `SplitType.TEST`, eligibility/coverage reporting
- **Objective.** Implement the split builder producing exactly one benign TRAIN, one benign CALIBRATION, and one TEST split (held-out benign + held-out malicious) per client with no overlap/leakage, attack excluded from calibration, and eligibility/fallback coverage reporting.
- **Why this ticket exists.** Benign-only calibration and attack-reserved-for-evaluation are locked; the calibration split has no attack-capable field by type; coverage is `|K_elig|/|K|`.
- **Authority references.** Arch §9.1, §29.1; Road §2, §17 (n_min=100, coverage).
- **Dependencies.** P2-T005.
- **Blocks.** P2-T007.
- **Downstream consumers.** P2-T007 (preprocessing fit/transform) consumes TRAIN/CALIBRATION/TEST splits with benign-only calibration guarantee.
- **Preconditions.** P2-T005 complete.
- **Inputs.** Arch §9.1, §29.1; Road §2, §17; nine-client partition from P2-T005.
- **Allowed scope.** `infrastructure/data/splitting.py` static-split path.
- **Forbidden actions.** No attack rows in calibration; no overlap between splits; no TEST used to fit thresholds; no scientific run.
- **Required configuration or NONE.** Regime A split config (benign-only calibration).
- **Implementation responsibilities.** Deterministic membership; row-order checksums; eligibility (n_min=100) and τ_global fallback marking; coverage reporting.
- **Required unit tests.** NONE.
- **Required property tests.** Benign-only calibration invariant; membership determinism.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): no overlap; attack absent from calibration; coverage computed.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); property lanes.
- **Acceptance criteria.** [ ] Exactly one TRAIN/CALIBRATION/TEST per client. [ ] No attack in calibration. [ ] No overlap/leakage. [ ] Coverage reported.
- **Completion evidence.** Standard report + split identity.
- **Failure and blocker behavior.** `SplitError` on overlap/leakage.
- **Stop conditions.** NONE.
- **Deliverables.** Anchor split builder.
- **Final review checklist.** [ ] Benign-only calibration by type.

#### P2-T007 — Implement preprocessing fit authorization and streaming transform

- **Ticket ID.** P2-T007
- **Title.** Implement preprocessing fit authorization and streaming transform
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** preprocessing
- **Owner.** data-pipeline-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** Preprocessing fitter, streaming transform, `FittedPreprocessor`, processed-split identities
- **Objective.** Implement the preprocessing fitter (authorized TRAIN rows only) and streaming transform producing partitioned processed splits with preserved feature order and source-row lineage; chunk/reference equivalence holds.
- **Why this ticket exists.** Fit uses authorized TRAIN rows only; no TEST-derived statistic; the transform streams and is chunk-equivalent to a reference.
- **Authority references.** Arch §9.1, §16.3, §29.4 (fitting on TEST unrepresentable).
- **Dependencies.** P2-T006, P1-T020.
- **Blocks.** P2-T008.
- **Downstream consumers.** P2-T008 (training) consumes fitted preprocessor and streaming-transformed processed splits.
- **Preconditions.** P2-T006, P1-T020 complete.
- **Inputs.** Arch §9.1, §16.3, §29.4; TRAIN/CALIBRATION/TEST splits from P2-T006.
- **Allowed scope.** `infrastructure/data/preprocessing.py`, `materialization.py`.
- **Forbidden actions.** No fit on non-TRAIN rows; no TEST stat; no runtime chunk resize; no scientific run.
- **Required configuration or NONE.** Preprocessing config (strategy/scope from recovered semantics).
- **Implementation responsibilities.** Two-pass/incremental fit under scope; feature-ordered streaming transform; row-order checksums.
- **Required unit tests.** NONE.
- **Required property tests.** Scope authorization.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): chunk-vs-reference transform equivalence; fit uses TRAIN only; feature order preserved.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); property lanes.
- **Acceptance criteria.** [ ] Fit authorized to TRAIN only. [ ] Chunk-vs-reference equivalence. [ ] Feature order preserved. [ ] No TEST statistic.
- **Completion evidence.** Standard report + preprocessor identity.
- **Failure and blocker behavior.** `PreprocessingError` on unauthorized fit rows.
- **Stop conditions.** Stop if preprocessing strategy/scope is unresolved; carry as a readiness blocker.
- **Deliverables.** Anchor preprocessing/transform.
- **Final review checklist.** [ ] No TEST leakage.

#### P2-T008 — Implement the fixed autoencoder, optimizer, and scheduler

- **Ticket ID.** P2-T008
- **Title.** Implement the fixed autoencoder, optimizer, and scheduler
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** training
- **Owner.** federated-learning-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `AutoencoderSpec`, `TrainingSpec`
- **Objective.** Implement the fixed autoencoder (recovered architecture, no BatchNorm), optimizer, and scheduler as the anchor `AutoencoderSpec`/`TrainingSpec`, validated on a synthetic tiny model without real training.
- **Why this ticket exists.** The fixed encoder is the locked ladder substrate; its architecture/optimizer/scheduler must match recovered semantics, not be guessed.
- **Authority references.** Arch §9.1, §16.2, §27 (AE/optimizer blockers); Road §2.
- **Dependencies.** P2-T007, P1-T043, P2-T001.
- **Blocks.** P2-T009.
- **Downstream consumers.** P2-T009 consumes the anchor training spec and fixed autoencoder for FedAvg training.
- **Preconditions.** P2-T007, P1-T043, P2-T001 complete.
- **Inputs.** Arch §9.1, §16.2, §27; Road §2.
- **Allowed scope.** `infrastructure/learning/models/autoencoder.py` anchor path; anchor training spec.
- **Forbidden actions.** No BatchNorm; no guessed architecture presented as recovered; no real training run.
- **Required configuration or NONE.** Anchor training config (AE dims/activation/optimizer/lr/scheduler).
- **Implementation responsibilities.** AE per recovered spec; optimizer/scheduler; synthetic forward/backward smoke.
- **Required unit tests.** No BatchNorm.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Forward/backward runs deterministically (synthetic tiny model).
- **Required CUDA tests.** Synthetic forward/backward deterministic (cuda lane).
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** CUDA lane (synthetic); unit lanes.
- **Acceptance criteria.** [ ] AE matches recovered spec. [ ] No BatchNorm. [ ] Synthetic forward/backward deterministic. [ ] No real training.
- **Completion evidence.** Changed files (autoencoder.py, anchor training spec); commands and tests run with results; training identity inputs; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** `TrainingError` on invalid config; readiness blocker if unresolved.
- **Stop conditions.** Stop if AE/optimizer/scheduler is unresolved; carry as a readiness blocker (smoke only).
- **Deliverables.** Fixed AE + optimizer/scheduler.
- **Final review checklist.** [ ] Recovered, not guessed.

#### P2-T009 — Implement FedAvg training (E=1, full participation, deterministic CUDA)

- **Ticket ID.** P2-T009
- **Title.** Implement FedAvg training (E=1, full participation, deterministic CUDA)
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** training
- **Owner.** federated-learning-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `FederationSpec`, `TrainingIdentity`
- **Objective.** Implement anchor FedAvg training (E=1, full participation, recovered weighting, deterministic CUDA, fixed batch semantics) producing scheduled scientific checkpoints, validated on synthetic clients without a real run.
- **Why this ticket exists.** FedAvg is the core baseline; E=1 and full participation are locked; training identity feeds every downstream artifact.
- **Authority references.** Arch §16.1–16.5, §9.1; Road §2.
- **Dependencies.** P2-T008, P1-T044.
- **Blocks.** P2-T010.
- **Downstream consumers.** P2-T010 consumes the anchor FedAvg training identity and checkpoints for persistence and selection.
- **Preconditions.** P2-T008, P1-T044 complete.
- **Inputs.** Arch §16.1–16.5, §9.1; Road §2.
- **Allowed scope.** FedAvg training path (anchor).
- **Forbidden actions.** No partial participation; no non-E=1; no real training run; no silent batch/precision change.
- **Required configuration or NONE.** Anchor federation config (FEDAVG, E=1, FULL, rounds_max, batch).
- **Implementation responsibilities.** FedAvg round lifecycle; recovered weighting; deterministic CUDA; round abort on invalid update.
- **Required unit tests.** NONE.
- **Required property tests.** Round determinism.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Full-participation abort; deterministic aggregation; uninterrupted-vs-resumed equivalence (cuda lane, synthetic).
- **Required CUDA tests.** Deterministic aggregation (cuda lane, synthetic).
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** CUDA lane (synthetic); property lanes.
- **Acceptance criteria.** [ ] E=1, full participation. [ ] Deterministic aggregation. [ ] Round aborts on invalid update. [ ] No real training.
- **Completion evidence.** Changed files (FedAvg training path); commands and tests run with results; training identity; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** Full-participation and CUDA error families. Stop if recovered FedAvg weighting is ambiguous; record a blocker.
- **Stop conditions.** Stop if recovered FedAvg weighting is ambiguous; record a blocker.
- **Deliverables.** Anchor FedAvg training.
- **Final review checklist.** [ ] Locked FedAvg behavior.

#### P2-T010 — Implement the checkpoint schedule, persistence, and Regime-A global selection

- **Ticket ID.** P2-T010
- **Title.** Implement the checkpoint schedule, persistence, and Regime-A global selection
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** checkpoint
- **Owner.** federated-learning-engineer
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4
- **Architecture contracts/types owned.** `CheckpointSchedule`, `CheckpointSelectionSpec`, `CheckpointSelectionResult`
- **Objective.** Implement the evidence-recovered historical anchor checkpoint persistence and selection protocol, validated on synthetic candidates. The journal {25,50,75,100,125,150,200} schedule is implemented only in the journal track and must not be imposed on anchor reproduction unless P2-T002 records authority evidence that they are identical.
- **Why this ticket exists.** A historical reproduction cannot silently redefine its training/selection protocol as the journal protocol. One anchor-global selected round may be used only after the recovered schedule, ranking rule, and tie-break are evidenced.
- **Authority references.** Arch §17.1, §9.1, §29.1/§29.4; Road §10 (checkpoint protocol).
- **Dependencies.** P2-T009, P2-T002, P1-T022.
- **Blocks.** P2-T011.
- **Downstream consumers.** P2-T011 consumes the selected checkpoint for anchor scoring.
- **Preconditions.** P2-T009, P2-T002 (anchor checkpoint protocol resolved), P1-T022 complete.
- **Inputs.** Arch §17.1, §9.1, §29.1/§29.4; Road §10.
- **Allowed scope.** `application/stages/select_checkpoint.py` (anchor), checkpoint persistence.
- **Forbidden actions.** No guessed anchor rounds; no silent journal-schedule substitution; no test AUROC/attack/Regime-D/FedProx/personalization/threshold in selection; no per-regime selection; no real run.
- **Required configuration or NONE.** `CheckpointSchedule`, `CheckpointSelectionSpec` (rule/tie-break versions).
- **Implementation responsibilities.** Persist only evidence-recovered anchor checkpoints; selection over eligible anchor candidates with prohibited-input attestation; deterministic evidence-recovered tie-break.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Selection uses Regime-A evidence only; prohibited input rejected; deterministic selected round; selection-artifact shape fixed-input regression (learning, synthetic).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (learning) lanes.
- **Acceptance criteria.** [ ] Historical anchor schedule/selection evidence is recorded. [ ] No journal schedule is assumed. [ ] Anchor-global selection only. [ ] Prohibited-input attestation present. [ ] Deterministic evidence-recovered selected round.
- **Completion evidence.** Changed files (select_checkpoint.py, checkpoint persistence); commands and tests run with results; selection identity; blocker state; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** `CheckpointSelectionError`. Stop if anchor schedule, ranking, or tie-break is unresolved; preserve `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` as a readiness blocker that prevents anchor training, checkpoint selection, campaign readiness, and execution.
- **Stop conditions.** Stop if anchor schedule, ranking, or tie-break is unresolved; preserve `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` as a readiness blocker that prevents anchor training, checkpoint selection, campaign readiness, and execution.
- **Deliverables.** Checkpoint persistence + selector.
- **Final review checklist.** [ ] No leakage into selection.

#### P2-T011 — Implement calibration, benign-test, and malicious-test scoring with atomic score bundles

- **Ticket ID.** P2-T011
- **Title.** Implement calibration, benign-test, and malicious-test scoring with atomic score bundles
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** scoring
- **Owner.** data-pipeline-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `ScoreGenerationSpec`, `SplitScopedScoreBundle`
- **Objective.** Implement anchor scoring under the selected checkpoint: per-client calibration benign scores, and the atomically committed benign+attack test-score aggregate, with full lineage/hashes/row-order checksums, validated on synthetic scores.
- **Why this ticket exists.** One calibration set and one test set per compatible seed feed B1–B4; the benign/attack pair commits as one aggregate; attack scores exist only on TEST.
- **Authority references.** Arch §9.2 (atomic pair protocol), §13.3, §29.1.
- **Dependencies.** P2-T010, P1-T045.
- **Blocks.** P2-T012, P2-T013.
- **Downstream consumers.** P2-T012 and P2-T013 consume the calibration and test score bundles for centralized and threshold policy evaluation.
- **Preconditions.** P2-T010, P1-T045 complete.
- **Inputs.** Arch §9.2, §13.3, §29.1.
- **Allowed scope.** `infrastructure/scoring/` (anchor); score-bundle commit.
- **Forbidden actions.** No attack score in calibration; no loose benign/attack pair; no real scoring run.
- **Required configuration or NONE.** Anchor scoring config (batch semantics frozen).
- **Implementation responsibilities.** Batched scoring streaming to device; atomic aggregate commit (write/verify benign, write/verify attack, build aggregate, verify shared lineage, hash, commit marker last).
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Missing benign/attack child rejected; mismatched lineage rejected; committed pair readable and consumed only by the evaluator (persistence, synthetic). Batched-vs-reference scoring equivalence (learning).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (persistence, learning) lanes.
- **Acceptance criteria.** [ ] Calibration/benign-test/malicious-test scores produced. [ ] Test pair committed atomically. [ ] Partial/mismatched pair rejected. [ ] No real run.
- **Completion evidence.** Changed files (infrastructure/scoring/); commands and tests run with results; scoring identities; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** `ScoringError`/`PartialArtifactError`; reject missing/mismatched/partial pair. Stop if score batch semantics unresolved; carry as readiness blocker.
- **Stop conditions.** Stop if score batch semantics unresolved; carry as readiness blocker.
- **Deliverables.** Anchor scoring + atomic bundles.
- **Final review checklist.** [ ] Attack only on TEST.

#### P2-T012 — Implement B0 centralized training branch

- **Ticket ID.** P2-T012
- **Title.** Implement B0 centralized training branch
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** threshold
- **Owner.** threshold-policy-engineer
- **Supporting agents.** federated-learning-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** B0
- **Architecture contracts/types owned.** `CentralizedModelComparatorProfileSpec`
- **Objective.** Implement only B0's separate centralized pooled-benign AE training identity and training path, never accepting a FedAvg identity. P2-T021 through P2-T023 own its checkpointing, scoring, and pooled threshold/evaluation/reporting route.
- **Why this ticket exists.** B0 is a privacy-incompatible centralized reference, not a ladder policy; code-path reuse is required but scientific-artifact identity reuse with the FedAvg branch is a type error.
- **Authority references.** Arch §9.2 (B0), §29.4 (80); Road §4 (B0 role).
- **Dependencies.** P2-T006, P1-T044.
- **Blocks.** P2-T021.
- **Downstream consumers.** P2-T021 consumes the B0 centralized training identity for checkpoint scheduling and selection.
- **Preconditions.** P2-T006, P1-T044 complete.
- **Inputs.** Arch §9.2, §29.4; Road §4.
- **Allowed scope.** B0 centralized path via the reusable stages.
- **Forbidden actions.** No B0 as a ladder policy; no FedAvg checkpoint/score into B0; no B0 mega-interface; no real run.
- **Required configuration or NONE.** B0 config through the dedicated centralized mapper.
- **Implementation responsibilities.** Centralized pooled-benign training/scoring/threshold via `CentralizedModelComparatorProfileSpec`; centralized nominal identities.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** Centralized-lineage.
- **Required architecture tests.** NONE.
- **Required integration tests.** B0 rejects FedAvg checkpoint/score; centralized identities distinct (learning, synthetic).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (learning); contract lanes.
- **Acceptance criteria.** [ ] B0 via same stages, centralized identities. [ ] Rejects FedAvg checkpoint/score. [ ] Not a ladder policy. [ ] No mega-interface.
- **Completion evidence.** Changed files (B0 centralized path); commands and tests run with results; centralized identities; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** Type error if a FedAvg identity is supplied to B0.
- **Stop conditions.** None.
- **Deliverables.** B0 centralized reference.
- **Final review checklist.** [ ] B0 ≠ ladder.

#### P2-T013 — Implement canonical anchor B1 shared construction

- **Ticket ID.** P2-T013
- **Title.** Implement canonical anchor B1 shared construction
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** threshold
- **Owner.** threshold-policy-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B1
- **Architecture contracts/types owned.** `ThresholdConstructionSpec`, `SharedThresholdSpec`, `EligibleClientSet`
- **Objective.** Implement only canonical anchor B1 shared τ: the unweighted arithmetic mean of eligible clients' local-q thresholds, consuming only anchor calibration scores and the shared `EligibleClientSet`.
- **Why this ticket exists.** B1 is the anchor shared-scope comparator. B1-pool, B1-wt, construction sensitivity, and formal q-sensitivity are journal-only variants owned by Phase 4; construction uses calibration scores only.
- **Authority references.** Arch §9.2 (B1 definition), §29.1; Road §4, §5.2 (E-S1).
- **Dependencies.** P2-T011, P1-T024.
- **Blocks.** P2-T016.
- **Downstream consumers.** P2-T016 consumes B1 shared threshold for evaluation.
- **Preconditions.** P2-T011, P1-T024 complete.
- **Inputs.** Arch §9.2, §29.1; Road §4, §5.2.
- **Allowed scope.** `infrastructure/thresholding/policies.py` shared constructions.
- **Forbidden actions.** No pooled or weighted construction; no E-S1 ownership; no journal q-sensitivity; no test/attack score input; no real run.
- **Required configuration or NONE.** Canonical anchor B1 threshold configuration only.
- **Implementation responsibilities.** `τ_B1 = mean_k τ_k(q)` unweighted, with the canonical anchor threshold identity.
- **Required unit tests.** B1 unweighted mean.
- **Required property tests.** Eligible-only mean.
- **Required contract tests.** Constructor rejects test scores.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; contract lanes.
- **Acceptance criteria.** [ ] B1 = unweighted mean. [ ] No pooled/weighted construction is implemented in Phase 2. [ ] Calibration scores only. [ ] Eligible-only.
- **Completion evidence.** Changed files (infrastructure/thresholding/policies.py); commands and tests run with results; threshold identities; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** `ThresholdError`.
- **Stop conditions.** None.
- **Deliverables.** Canonical anchor B1 construction.
- **Final review checklist.** [ ] Only mean is B1.

#### P2-T014 — Implement B2 per-client and B3 family constructions

- **Ticket ID.** P2-T014
- **Title.** Implement B2 per-client and B3 family constructions
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** threshold
- **Owner.** threshold-policy-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `LocalThresholdSpec`, `FamilyThresholdSpec` (`family_manifest_identity`)
- **Objective.** Implement B2 per-client local-p95 thresholds and B3 family-mean thresholds (unweighted mean of eligible family members' local-q thresholds; requires an authorized taxonomy).
- **Why this ticket exists.** B2 is the confirmatory comparator (local scope); B3 is the family mechanism baseline and must not run without an authorized taxonomy.
- **Authority references.** Arch §9.2, §8.3 (B3 requires taxonomy), §29.1; Road §4.
- **Dependencies.** P2-T013.
- **Blocks.** P2-T016.
- **Downstream consumers.** P2-T016 consumes B2 and B3 thresholds for evaluation.
- **Preconditions.** P2-T013 complete.
- **Inputs.** Arch §9.2, §8.3, §29.1; Road §4.
- **Allowed scope.** `infrastructure/thresholding/policies.py` local/family constructions.
- **Forbidden actions.** No B3 without authorized taxonomy; no test/attack input; no real run.
- **Required configuration or NONE.** Threshold config for B2/B3; taxonomy authorization for B3.
- **Implementation responsibilities.** B2 local p95 per client; B3 family unweighted mean with a `family_manifest_identity`.
- **Required unit tests.** B2 per-client; B3 requires taxonomy; family mean unweighted.
- **Required property tests.** NONE.
- **Required contract tests.** Constructor rejects test scores.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; contract lanes.
- **Acceptance criteria.** [ ] B2 local p95. [ ] B3 unweighted family mean. [ ] B3 blocked without taxonomy. [ ] Calibration scores only.
- **Completion evidence.** Changed files (infrastructure/thresholding/policies.py); commands and tests run with results; threshold identities; blocker state; cleanup confirmation; skipped checks/reasons.
- **Failure and blocker behavior.** `ThresholdError`; block B3 without taxonomy. Stop if the family taxonomy is unavailable/unauthorized; record a blocker (B3 stays blocked).
- **Stop conditions.** Stop if the family taxonomy is unavailable/unauthorized; record a blocker (B3 stays blocked).
- **Deliverables.** B2/B3 constructions.
- **Final review checklist.** [ ] B3 taxonomy-gated.

#### P2-T015 — Implement canonical anchor B4 exact k-means++ clustering and cluster-mean thresholds (K=3)

- **Ticket ID.** P2-T015
- **Title.** Implement canonical anchor B4 exact k-means++ clustering and cluster-mean thresholds (K=3)
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** threshold
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B4
- **Architecture contracts/types owned.** `ClusterAssignmentArtifact`, cluster-mean threshold specifications, `infrastructure/thresholding/clustering.py`
- **Objective.** Implement canonical B4: exact k-means++ over the fixed 4-scalar fingerprint `[mean,std,skew,p95]` at K=3 with locked scaler/`n_init`/`max_iter`/derived random state, producing a `ClusterAssignmentArtifact`, and cluster-mean thresholds that reuse the assignment across q without reclustering.
- **Why this ticket exists.** Canonical B4 is exact and stable; q is never a fingerprint field; the assignment is reused across q cells; adjusted-Rand stability compares immutable assignments.
- **Authority references.** Arch §9.2, §16.2, §7.1; Road §4, SB-32.
- **Dependencies.** P2-T014, P1-T025.
- **Blocks.** P2-T016.
- **Downstream consumers.** P2-T016 consumes the canonical B4 clustering assignment and cluster-mean thresholds for evaluation.
- **Preconditions.** P2-T014, P1-T025 complete.
- **Inputs.** Arch §9.2, §16.2, §7.1; Road §4, SB-32.
- **Allowed scope.** `infrastructure/thresholding/clustering.py` (canonical B4).
- **Forbidden actions.** No MiniBatchKMeans; no q in the fingerprint; no caller K/algorithm override; no real run.
- **Required configuration or NONE.** B4 config (canonical K=3, locked constants; exploratory K via a separate profile).
- **Implementation responsibilities.** Exact KMeans with locked constants; assignment artifact; q-specific cluster-mean thresholds averaging member local-q thresholds.
- **Required unit tests.** q not a fingerprint field; assignment reused across q; K=3 canonical.
- **Required property tests.** Canonical-K derivation.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Fixed fingerprint set → stable assignment + adjusted-Rand (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration; unit; property lanes.
- **Acceptance criteria.** [ ] Exact k-means++, K=3, locked constants. [ ] q not a fingerprint field. [ ] Assignment reused across q. [ ] Golden-stable.
- **Completion evidence.** Standard report + threshold identity.
- **Failure and blocker behavior.** `ThresholdError`; unresolved constants block print-grade (readiness).
- **Stop conditions.** Stop if scaler/`n_init`/`max_iter` are unresolved; carry as readiness blockers.
- **Deliverables.** Canonical B4 construction.
- **Final review checklist.** [ ] Exact, K=3, stable.

#### P2-T016 — Implement per-client confusion counts and operating-point metrics

- **Ticket ID.** P2-T016
- **Title.** Implement per-client confusion counts and operating-point metrics
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** evaluation
- **Owner.** statistics-auditor
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `EligibleClientSet`, `UndefinedCvResult`, confusion count types, operating-point metric specifications
- **Objective.** Implement anchor policy evaluation producing per-client confusion counts and operating-point metrics (FPR, TPR, CV(FPR) primary, CV(TPR), IQR(FPR), max−min FPR, worst-client FPR) over the shared `EligibleClientSet`, with typed zero-mean CV handling.
- **Why this ticket exists.** CV(FPR) is the primary endpoint over eligible clients; absolute-dispersion companions guard small-denominator artifacts; a shared eligible set is used by every compared policy.
- **Authority references.** Arch §9.3, §29.1; Road §10.
- **Dependencies.** P2-T013, P2-T014, P2-T015, P2-T023, P1-T026.
- **Blocks.** P2-T017.
- **Downstream consumers.** P2-T017 consumes the operating-point metrics and confusion counts for detection-quality evaluation.
- **Preconditions.** P2-T013, P2-T014, P2-T015, P2-T023, P1-T026 complete.
- **Inputs.** Arch §9.3, §29.1; Road §10.
- **Allowed scope.** `application/stages/evaluate_policy.py` (anchor), metric calculators.
- **Forbidden actions.** No per-policy eligible population; no CV exception for expected zero mean; no test-set-driven checkpoint selection; no real run.
- **Required configuration or NONE.** Evaluation config (primary CV_FPR).
- **Implementation responsibilities.** Confusion counts from committed test aggregate; eligible-only dispersion; typed `UndefinedCvResult` with companions.
- **Required unit tests.** Paired policies share one eligible set; CV(FPR) computed; zero-mean typed.
- **Required property tests.** Confusion-count recomputability.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** B1–B4 reuse one test set (learning integration).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; integration lanes.
- **Acceptance criteria.** [ ] CV(FPR) primary over eligible clients. [ ] Absolute-dispersion companions present. [ ] Shared eligible set. [ ] Zero-mean CV typed.
- **Completion evidence.** Standard report + evaluation identity.
- **Failure and blocker behavior.** Zero-mean CV → typed result; `EvaluationError` for genuine failure.
- **Stop conditions.** Stop if the zero-mean CV policy is unresolved; carry as a readiness blocker.
- **Deliverables.** Anchor operating-point evaluation.
- **Final review checklist.** [ ] CV(FPR) primary; no exception path.

#### P2-T017 — Implement detection-quality metrics (AUROC control, Macro-F1, P10, worst-client BA)

- **Ticket ID.** P2-T017
- **Title.** Implement detection-quality metrics (AUROC control, Macro-F1, P10, worst-client BA)
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** evaluation
- **Owner.** statistics-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `MetricSpec`, AUROC/Macro-F1/P10/worst-client BA calculator specifications
- **Objective.** Implement the detection-quality controls: AUROC (control-only), Macro-F1, P10 Macro-F1, worst-client balanced accuracy, wired so AUROC never becomes a thresholding verdict.
- **Why this ticket exists.** AUROC is a model-quality control; P10 Macro-F1 degradation under B2 is a reported honest negative; these never select the checkpoint or drive the confirmatory claim.
- **Authority references.** Arch §29.1 (`MetricSpec.is_control`), §11.4; Road §2, §10.
- **Dependencies.** P2-T016.
- **Blocks.** P2-T018.
- **Downstream consumers.** P2-T018 consumes the detection-quality metrics for statistical analysis.
- **Preconditions.** P2-T016 complete.
- **Inputs.** Arch §29.1, §11.4; Road §2, §10.
- **Allowed scope.** Detection-quality calculators (anchor).
- **Forbidden actions.** No AUROC-as-verdict; no AUROC-driven checkpoint selection; no real run.
- **Required configuration or NONE.** Evaluation config controls (AUROC is_control true).
- **Implementation responsibilities.** AUROC/Macro-F1/P10/worst-client BA calculators with control flags.
- **Required unit tests.** AUROC is control-only; P10 Macro-F1 computed; worst-client BA computed.
- **Required property tests.** Metric bounds.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property lanes.
- **Acceptance criteria.** [ ] AUROC control-only. [ ] P10 Macro-F1 and worst-client BA computed. [ ] No AUROC verdict path. [ ] No real run.
- **Completion evidence.** Standard report + evaluation identity.
- **Failure and blocker behavior.** `EvaluationError`.
- **Stop conditions.** None.
- **Deliverables.** Detection-quality metrics.
- **Final review checklist.** [ ] AUROC control only.

#### P2-T018 — Implement paired deltas, BCa bootstrap, Wilcoxon, Cliff's delta, reference diagnostics

- **Ticket ID.** P2-T018
- **Title.** Implement paired deltas, BCa bootstrap, Wilcoxon, Cliff's delta, reference diagnostics
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** statistics
- **Owner.** statistics-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** Paired delta specifications, BCa bootstrap types, anchor honesty diagnostic specifications
- **Objective.** Implement the anchor statistical analysis: per-seed Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s], 95% BCa bootstrap CI with explicit resamples and positive-direction pass rule, descriptive Wilcoxon and Cliff's delta, and the five-seed anchor-reference honesty diagnostic (interval vs `[0.647, 0.769]`, ~20%-wider rule).
- **Why this ticket exists.** The confirmatory verdict and the anchor honesty gate are the crux of the campaign; BCa degeneracy is typed; the less-favorable ten-seed result is never suppressed.
- **Authority references.** Arch §9.3, §16.5; Road §3, §5.1, §10.
- **Dependencies.** P2-T017, P1-T046.
- **Blocks.** P2-T019.
- **Downstream consumers.** P2-T019 consumes the statistical analysis results and confirmatory verdict for reporting and planning.
- **Preconditions.** P2-T017, P1-T046 complete.
- **Inputs.** Arch §9.3, §16.5; Road §3, §5.1, §10.
- **Allowed scope.** `application/stages/analyze_statistics.py` (anchor) + statistics adapter use.
- **Forbidden actions.** No confirmatory Wilcoxon/Cliff branch; no silent BCa→percentile; no suppression of a less-favorable result; no real run.
- **Required configuration or NONE.** Confirmatory statistical config (BCa, 0.95, ten paired; explicit `BootstrapResampleCount`).
- **Implementation responsibilities.** Paired delta; BCa CI (explicit resamples); descriptive tests; anchor honesty diagnostic; typed degeneracy.
- **Required unit tests.** Pass rule; degeneracy typed; Δ = B1 − B2.
- **Required property tests.** BCa sanity on synthetic deltas.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Anchor-reference diagnostic shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; integration lanes.
- **Acceptance criteria.** [ ] Δ = B1 − B2. [ ] BCa positive-direction pass rule. [ ] Anchor honesty diagnostic present. [ ] Degeneracy typed; no percentile substitution.
- **Completion evidence.** Standard report + statistical identity.
- **Failure and blocker behavior.** `StatisticsError` for unexpected only; degeneracy typed.
- **Stop conditions.** Stop if the anchor honesty operational tolerance is unresolved; carry as a readiness blocker.
- **Deliverables.** Anchor statistical analysis.
- **Final review checklist.** [ ] Confirmatory verdict correct.

#### P2-T019 — Implement anchor report models, expected-artifact inventory, and dry-run planner

- **Ticket ID.** P2-T019
- **Title.** Implement anchor report models, expected-artifact inventory, and dry-run planner
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `DraftExecutionPlan`, `FinalExecutionPlan`, report model specifications, artifact inventory types
- **Objective.** Implement anchor report models (confirmatory-interval, dispersion-ladder tables; relevant figures), the anchor expected-artifact inventory (every stage identity → expected artifact), and a dry-run anchor planner producing a `DraftExecutionPlan`/`FinalExecutionPlan` for the anchor matrix without executing it.
- **Why this ticket exists.** The anchor campaign must be designed and inventoried before expensive execution; a dry-run plan validates the execution DAG and expected artifacts.
- **Authority references.** Arch §22.1, §14, §26 (design now); Road §9.1.
- **Dependencies.** P2-T018, P1-T049.
- **Blocks.** P2-T020.
- **Downstream consumers.** P2-T020 consumes the report models, artifact inventory, and dry-run plan for anchor readiness evaluation.
- **Preconditions.** P2-T018, P1-T049 complete.
- **Inputs.** Arch §22.1, §14, §26; Road §9.1.
- **Allowed scope.** Anchor report specs; expected-artifact inventory; dry-run planning.
- **Forbidden actions.** No real execution; no rendering before freeze/provenance closure; no invented seed sequence.
- **Required configuration or NONE.** Anchor reporting config; anchor experiment configs.
- **Implementation responsibilities.** Report specs; inventory enumeration; dry-run plan expansion and validation.
- **Required unit tests.** Report specs framework-free; inventory covers every stage identity.
- **Required property tests.** Dry-run determinism.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Plan/inventory shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; integration; property; dry-run planning lanes.
- **Acceptance criteria.** [ ] Anchor report models present. [ ] Expected-artifact inventory complete. [ ] Dry-run plan validates without executing. [ ] No invented seeds.
- **Completion evidence.** Standard report + report identity.
- **Failure and blocker behavior.** `ProvenanceError` on untraced spec; `AmbiguousPlanError`/`CyclicPlanError` on plan conflicts.
- **Stop conditions.** None.
- **Deliverables.** Anchor report models, inventory, dry-run planner.
- **Final review checklist.** [ ] Planning only.

#### P2-T020 — Implement the anchor readiness evaluator and anchor-implementation audit

- **Ticket ID.** P2-T020
- **Title.** Implement the anchor readiness evaluator and anchor-implementation audit
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** datp-protocol-guardian, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `ScientificReadinessResult`, anchor readiness evaluator, audit record types
- **Objective.** Evaluate anchor readiness (`ScientificReadinessResult`) — every recovered-semantics blocker closed or explicitly carried — run the synthetic end-to-end anchor simulation, and produce the anchor-implementation audit certifying the anchor is implemented and ready for the campaign without any real execution. **This is the Phase 2 anchor-implementation-audit gate.**
- **Why this ticket exists.** This gate prevents entering the anchor campaign with unresolved semantics or an unvalidated pipeline; smoke behavior is explicitly non-citable.
- **Authority references.** Arch §27 (readiness), §21.2 (scientific_smoke), §26; this backlog §F (Phase 2 gate).
- **Dependencies.** P2-T019, P2-T002, P1-T040.
- **Blocks.** P3-T001.
- **Downstream consumers.** P3-T001 and all Phase 3 anchor campaign tickets depend on the completed readiness evaluation and implementation audit.
- **Preconditions.** P2-T019, P2-T002, P1-T040 complete.
- **Inputs.** Arch §27, §21.2, §26; this backlog §F.
- **Allowed scope.** Readiness evaluation; synthetic end-to-end anchor simulation; audit record.
- **Forbidden actions.** No real anchor training/scoring; no citable claim from smoke; no unresolved-blocker bypass.
- **Required configuration or NONE.** Anchor smoke profile (non-citable).
- **Implementation responsibilities.** Aggregate anchor blockers; run the synthetic anchor pipeline end-to-end; record the audit and readiness verdict.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** System (scientific_smoke, synthetic subsample): the confirmatory BCa rule and its failure behavior on a small synthetic sample; full synthetic anchor pipeline passes.
- **Validation commands.** scientific_smoke (synthetic); synthetic system; full Nox validation.
- **Acceptance criteria.** [ ] Every anchor blocker closed or explicitly carried. [ ] Synthetic anchor pipeline passes end-to-end. [ ] Audit recorded. [ ] No real execution.
- **Completion evidence.** Standard report + readiness result.
- **Failure and blocker behavior.** Unresolved print-grade blockers keep readiness failed.
- **Stop conditions.** Stop and keep readiness failed if any print-grade anchor blocker remains open.
- **Deliverables.** Anchor readiness verdict + implementation audit.
- **Final review checklist.** [ ] Ready without real runs.

> **[LEGACY — relocated, not yet reconstructed under the mandatory Section H template.]** The three tickets below (P2-T021–P2-T023) existed only in Section F prior to this revision and are moved here verbatim so that Section G's index rows have a corresponding body. Their content, field names, and dependencies are pending the Phase 2 reconstruction stage and must not be treated as validated against the current mandatory template or against the anchor/journal separation and B0-naming rules applied to Phase 0.

#### P2-T021 — Implement B0 centralized checkpoint schedule and scientific checkpoint selection

- **Ticket ID.** P2-T021
- **Title.** Implement B0 centralized checkpoint schedule and scientific checkpoint selection
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** checkpoint
- **Owner.** federated-learning-engineer
- **Supporting agents.** threshold-policy-engineer, reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** — (ANCHOR-B0; not a formal journal experiment ID)
- **Architecture contracts/types owned.** `CheckpointSchedule`, `CheckpointSelectionSpec`, `CheckpointSelectionResult`, `CheckpointSelectionArtifact`, `CheckpointDescriptor`, `CentralizedModelComparatorProfileSpec`
- **Objective.** Produce B0's separate centralized checkpoint schedule and selection identity from centralized training only.
- **Why this ticket exists.** B0 is a separately trained centralized AE reference, not a threshold operation over FedAvg outputs.
- **Authority references.** Road §4, §9; Arch §9.1, §13, §17.
- **Dependencies.** P2-T012, P2-T002, P1-T022.
- **Blocks.** P2-T022.
- **Downstream consumers.** P2-T022, P2-T023, P3-T007, P5-T005, P6-T002, P7-T002.
- **Preconditions.** Historical anchor checkpoint evidence is recovered or the affected anchor branch remains blocked; no journal checkpoint schedule is substituted.
- **Inputs.** B0 centralized training identity, recovered anchor evidence, frozen checkpoint specification.
- **Allowed scope.** Synthetic implementation and typed identity construction only.
- **Forbidden actions.** No FedAvg checkpoint reuse, no guessed historical rounds, no real campaign execution.
- **Required configuration.** Dedicated B0 centralized checkpoint configuration; or `NONE` until authoritative evidence is recovered.
- **Implementation responsibilities.** Implement a centralized schedule, persistence, and selection path that rejects federated identities and records its own scientific checkpoint.
- **Required unit tests.** Centralized checkpoint rejects a federated training identity.
- **Required property tests.** Identity changes when any centralized schedule input changes.
- **Required contract tests.** Persisted checkpoint lineage is typed and complete.
- **Required architecture tests.** No central/federated carrier crosses the wrong port.
- **Required integration tests.** Synthetic centralized checkpoint selection.
- **Required CUDA tests.** Synthetic tiny-model checkpoint persistence.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Focused unit/property/contract/integration/CUDA lanes.
- **Acceptance criteria.** [ ] Centralized schedule and checkpoint are independently identified. [ ] FedAvg identity is rejected. [ ] Unresolved historical evidence blocks the anchor branch.
- **Completion evidence.** Changed files; implemented types/contracts; commands and tests run with results; B0 checkpoint identity; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Preserve failed evidence and emit `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` rather than guessing.
- **Stop conditions.** Missing authoritative anchor checkpoint evidence.
- **Deliverables.** B0 centralized checkpoint specification and identity.
- **Final review checklist.** [ ] Centralized lineage only. [ ] No journal-protocol substitution.

#### P2-T022 — Implement B0 centralized calibration and held-out score generation

- **Ticket ID.** P2-T022
- **Title.** Implement B0 centralized calibration and held-out score generation
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** scoring
- **Owner.** federated-learning-engineer
- **Supporting agents.** data-pipeline-engineer, threshold-policy-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** — (ANCHOR-B0; not a formal journal experiment ID)
- **Architecture contracts/types owned.** `ScoreGenerationSpec`, `CalibrationScoreArtifactId`, `TestScoreArtifactId`, `CalibrationScoreArtifactSet`, `TestScoreArtifactSet`, `ArtifactBundleManifest`
- **Objective.** Generate split-scoped centralized B0 calibration, benign-test, and malicious-test score identities.
- **Why this ticket exists.** B0 cannot consume FedAvg score artifacts.
- **Authority references.** Road §4, §9; Arch §9.2, §13, §22.
- **Dependencies.** P2-T021, P1-T045.
- **Blocks.** P2-T023.
- **Downstream consumers.** P2-T023, P3-T007, P5-T005, P6-T002, P7-T002.
- **Preconditions.** B0 centralized scientific checkpoint exists.
- **Inputs.** Centralized checkpoint identity and split identities.
- **Allowed scope.** Synthetic score-bundle implementation only.
- **Forbidden actions.** No FedAvg score reuse; no test-driven threshold fit; no real campaign execution.
- **Required configuration.** B0 split-scoped score configuration.
- **Implementation responsibilities.** Enforce separate centralized score lineage and atomic bundles.
- **Required unit tests.** FedAvg score identity rejection.
- **Required property tests.** Split-scoped identities cannot collide.
- **Required contract tests.** Manifest has checkpoint and split lineage.
- **Required architecture tests.** Scoring port receives typed centralized identity.
- **Required integration tests.** Synthetic centralized scoring.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Focused unit/property/contract/integration lanes.
- **Acceptance criteria.** [ ] Separate B0 calibration and test score identities exist. [ ] No federated lineage accepted.
- **Completion evidence.** Changed files; types/contracts; commands/tests/results; score identities; cleanup; remaining blockers; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Missing or malformed score bundle is a technical invalidity, never a scientific rerun trigger.
- **Stop conditions.** Open checkpoint lineage.
- **Deliverables.** Centralized B0 score bundles.
- **Final review checklist.** [ ] Calibration and held-out scoring separated.

#### P2-T023 — Implement B0 pooled threshold, evaluation, statistics, and reporting route

- **Ticket ID.** P2-T023
- **Title.** Implement B0 pooled threshold, evaluation, statistics, and reporting route
- **Phase.** 2
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** evaluation
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor, report-output-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** — (ANCHOR-B0; not a formal journal experiment ID)
- **Architecture contracts/types owned.** `ThresholdConstructionSpec`, `PolicyEvaluationResult`, `StatisticalAnalysisResult`, `ReportIdentity`
- **Objective.** Apply B0 pooled calibration threshold and route centralized results through evaluation, statistics, and reporting.
- **Why this ticket exists.** B0 is a non-ladder centralized reference with its own complete evidence path.
- **Authority references.** Road §4, §9; Arch §9.2–§9.4, §22.
- **Dependencies.** P2-T022, P1-T026, P1-T049.
- **Blocks.** P2-T016, P2-T019.
- **Downstream consumers.** P3-T007, P5-T006, P6-T002, P7-T004, P7-T009.
- **Preconditions.** B0 centralized calibration and held-out score bundles are lineage-complete.
- **Inputs.** Centralized B0 score identities and pooled threshold configuration.
- **Allowed scope.** Synthetic threshold/evaluation/reporting tests.
- **Forbidden actions.** No B0 placement in B1–B4; no FedAvg identity reuse; no real campaign execution.
- **Required configuration.** B0 pooled p95 threshold configuration.
- **Implementation responsibilities.** Construct B0 from centralized calibration, evaluate on central held-out scores, and label B0 outside the causal ladder.
- **Required unit tests.** B0 is not accepted as a B1–B4 policy.
- **Required property tests.** Threshold identity changes with calibration lineage.
- **Required contract tests.** Evaluation/report models retain centralized lineage.
- **Required architecture tests.** Reporting stays framework-free.
- **Required integration tests.** Synthetic complete B0 route.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic anchor smoke path.
- **Validation commands.** Focused unit/property/contract/integration/system lanes.
- **Acceptance criteria.** [ ] B0 has threshold, evaluation, statistics, and report coverage. [ ] B0 is outside B1–B4.
- **Completion evidence.** Changed files; types/contracts; commands/tests/results; generated identity schema; cleanup; blockers; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Preserve any invalid artifact evidence; correct only diagnosed technical invalidity.
- **Stop conditions.** Centralized lineage gap.
- **Deliverables.** Complete B0 anchor route.
- **Final review checklist.** [ ] B0 branch is distinct end-to-end.

### Phase 3 — DATP Anchor Campaign

> **Phase-wide note (applies to every P3 ticket).** This phase contains the anchor scientific campaign. Only tickets explicitly classified `ANCHOR_CAMPAIGN_ALLOWED` perform real anchor training or scoring; all others are `PLANNING_ONLY`. The campaign is one coordinated evidence program, not one process, one job, one attempt, one seed order, a "first-five" subset, one physical write per artifact, or a blanket "exactly once" rule. Campaign scope is `ANCHOR`. Reuse follows lineage compatibility; recomputation follows any identity-bearing change; resume skips completed compatible stages. Corrected reruns require the root-cause/attempt-tracking record of §B; infrastructure retries preserving identical scientific identity continue the same campaign. "Completion evidence" is the standard five-heading report plus campaign identity and execution-attempt identity.

#### P3-T001 — Final anchor implementation audit and clean-worktree check

- **Ticket ID.** P3-T001
- **Title.** Final anchor implementation audit and clean-worktree check
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** architecture-cleaner
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `CodeState` (clean/dirty worktree status)
- **Objective.** Re-run the anchor-implementation audit and confirm a clean worktree and green baseline/architecture/socle suites immediately before any freeze, so nothing uncommitted or failing enters the campaign.
- **Why this ticket exists.** A dirty worktree or failing suite at freeze poisons provenance; the campaign identity must derive from a clean, verified state.
- **Authority references.** Arch §9.5 (`CodeState` clean/dirty), §29; this backlog §E, §B.
- **Dependencies.** P2-T020.
- **Blocks.** P3-T002.
- **Downstream consumers.** P3-T002 consumes the clean-worktree verification and green-suite confirmation before freezing provenance.
- **Preconditions.** P2-T020 (readiness passed) complete.
- **Inputs.** Arch §9.5, §29; backlog §E, §B.
- **Allowed scope.** Read-only audit; clean-worktree verification.
- **Forbidden actions.** No real execution; no code change to "make it clean" without a recorded reason; no freeze on a dirty tree.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Run baseline/architecture/socle/anchor audits; verify clean worktree; record the pre-freeze state.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Architecture lane green.
- **Required integration tests.** Full Nox validation (synthetic) green.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Full Nox validation; git status; architecture lane.
- **Acceptance criteria.** [ ] Clean worktree confirmed. [ ] Baseline/architecture/socle/anchor suites green. [ ] Pre-freeze state recorded. [ ] No real execution.
- **Completion evidence.** Pre-freeze audit record; commands run and results; clean worktree confirmation; cleanup confirmation.
- **Failure and blocker behavior.** A dirty worktree or failing suite blocks the freeze; stop if the worktree is dirty or any suite fails.
- **Stop conditions.** Stop if the worktree is dirty or any suite fails.
- **Deliverables.** Pre-freeze audit record.
- **Final review checklist.** [ ] Clean and green before freeze.

#### P3-T002 — Freeze code-state, dependency-lock, and environment provenance

- **Ticket ID.** P3-T002
- **Title.** Freeze code-state, dependency-lock, and environment provenance
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `CodeState`, `DependencyLockState`, `EnvironmentInventory`
- **Objective.** Capture and freeze `CodeState` (commit identity, clean state), `DependencyLockState`, and `EnvironmentInventory` (CUDA/GPU/VRAM/library exact versions) as the anchor campaign's provenance baseline.
- **Why this ticket exists.** Reproducibility and Phase 7 audits require an immutable provenance baseline captured before execution; pinned numerically sensitive libraries must be recorded.
- **Authority references.** Arch §9.5, §11.3, §22.
- **Dependencies.** P3-T001, P0-T004.
- **Blocks.** P3-T006.
- **Downstream consumers.** P3-T006 consumes the frozen provenance baseline for campaign identity construction.
- **Preconditions.** P3-T001, P0-T004 complete.
- **Inputs.** Arch §9.5, §11.3, §22.
- **Allowed scope.** Provenance capture and recording.
- **Forbidden actions.** No release/tag/version work; no execution; no post-hoc provenance edit.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Capture code/dependency/environment provenance records; bind them to the campaign identity (created in P3-T006).
- **Required unit tests.** Pinned libraries recorded.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Provenance-record shapes (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Provenance capture; integration lane.
- **Acceptance criteria.** [ ] Code/dependency/environment provenance captured. [ ] Pinned libraries recorded. [ ] Immutable baseline. [ ] No versioning work.
- **Completion evidence.** Changed files (provenance records); commands run and results; recorded provenance identities; cleanup confirmation.
- **Failure and blocker behavior.** `EnvironmentIncompatibilityError` if required versions are absent; stop if the environment lacks a required pinned library version.
- **Stop conditions.** Stop if the environment lacks a required pinned library version.
- **Deliverables.** Frozen provenance baseline.
- **Final review checklist.** [ ] Immutable, no tag work.

#### P3-T003 — Freeze the resolved anchor configuration and verify the authoritative seed plan

- **Ticket ID.** P3-T003
- **Title.** Freeze the resolved anchor configuration and verify the authoritative seed plan
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `ResolvedConfigurationArtifact`
- **Objective.** Resolve and freeze the anchor scientific configuration into an immutable `ResolvedConfigurationArtifact`, and verify the authoritative seed plan (the paired seeds defined by the resolved authoritative seed specification) without inventing values or ordering.
- **Why this ticket exists.** The resolved-configuration identity anchors reuse and the campaign identity; the seed plan must be verified against the authoritative specification, never fabricated.
- **Authority references.** Arch §8.1, §11, §7.5; Road §3, §10 (paired seeds).
- **Dependencies.** P3-T001.
- **Blocks.** P3-T004.
- **Downstream consumers.** P3-T004 consumes the frozen resolved configuration and verified seed plan for matrix expansion and identity enumeration.
- **Preconditions.** P3-T001 complete.
- **Inputs.** Arch §8.1, §11, §7.5; Road §3, §10.
- **Allowed scope.** Configuration resolution/freeze; seed-plan verification.
- **Forbidden actions.** No invented seed values/ordering; no "first-five" subset; no unresolved print-grade field; no execution.
- **Required configuration or NONE.** Anchor scientific configuration (`configs/protocols/`, `configs/experiments/E-C1.yaml`).
- **Implementation responsibilities.** Resolve anchor config; verify the seed plan cardinality/pairing against the authoritative spec; freeze the resolved-configuration artifact.
- **Required unit tests.** Resolved config frozen and identity-stable; seed plan matches the authoritative spec.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Resolved-config shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Configuration validation; unit; integration lanes.
- **Acceptance criteria.** [ ] Resolved anchor config frozen. [ ] Seed plan verified against the authoritative spec. [ ] No invented seeds/ordering. [ ] No unresolved print-grade field.
- **Completion evidence.** Changed files (resolved-configuration artifact); commands run and results; recorded configuration identity; cleanup confirmation.
- **Failure and blocker behavior.** `ConfigurationError` on unresolved print-grade field; blocker if the seed specification is unverifiable; stop if the authoritative seed specification cannot be verified and record a blocker.
- **Stop conditions.** Stop if the authoritative seed specification cannot be verified; record a blocker.
- **Deliverables.** Frozen resolved anchor configuration.
- **Final review checklist.** [ ] No fabricated seeds.

#### P3-T004 — Verify the anchor experiment matrix and enumerate stage identities and expected artifacts

- **Ticket ID.** P3-T004
- **Title.** Verify the anchor experiment matrix and enumerate stage identities and expected artifacts
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** experiment-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `CellId`, expected-artifact inventory
- **Objective.** Expand the frozen anchor configuration into the complete resolved experiment matrix, enumerate every stage identity, and produce the expected-artifact inventory (no cell-ID collisions), confirming B1–B4 share compatible checkpoint/score identities.
- **Why this ticket exists.** The campaign executes a resolved matrix; enumeration proves the DAG is complete, collision-free, and that the ladder shares expensive identities.
- **Authority references.** Arch §14, §13; this backlog §B.
- **Dependencies.** P3-T003.
- **Blocks.** P3-T005.
- **Downstream consumers.** P3-T005 consumes the anchor matrix and identity/artifact inventory for execution planning.
- **Preconditions.** P3-T003 complete.
- **Inputs.** Arch §14, §13; backlog §B.
- **Allowed scope.** Matrix expansion; identity/artifact enumeration.
- **Forbidden actions.** No execution; no cell-ID collision; no blanket "exactly once" wording.
- **Required configuration or NONE.** NONE beyond the frozen config.
- **Implementation responsibilities.** Expand cells; enumerate stage identities and expected artifacts; verify shared ladder identities and collision-free `CellId`s.
- **Required unit tests.** Collision-free cell enumeration; B1–B4 share checkpoint/score identities.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Expected-artifact inventory shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Dry-run planning; unit; integration lanes.
- **Acceptance criteria.** [ ] Complete resolved matrix enumerated. [ ] No cell-ID collision. [ ] Ladder shares expensive identities. [ ] Expected-artifact inventory produced.
- **Completion evidence.** Changed files (matrix expansion and identity/artifact inventory); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `AmbiguousPlanError`/`CyclicPlanError` on conflicts; stop on any cell-ID collision or cyclic dependency.
- **Stop conditions.** Stop on any cell-ID collision or cyclic dependency.
- **Deliverables.** Anchor matrix + identity/artifact inventory.
- **Final review checklist.** [ ] Collision-free DAG.

#### P3-T005 — Resource/storage/CUDA/VRAM preflight and output-namespace compatibility

- **Ticket ID.** P3-T005
- **Title.** Resource/storage/CUDA/VRAM preflight and output-namespace compatibility
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `ResolvedBatchExecutionProfile`
- **Objective.** Run preflight: validate the exact resolved batch/scoring/preprocessing profile, CUDA/VRAM availability, RAM, disk projections/reserve, same-filesystem commit capability, and confirm the anchor output namespace is separate from the journal namespace.
- **Why this ticket exists.** Preflight freezes the exact profile and proves resources before expensive execution; anchor outputs must not resolve into the journal namespace.
- **Authority references.** Arch §16, §15.2, §12.3 (preflight); this backlog §B.
- **Dependencies.** P3-T004, P1-T039, P1-T060, P1-T061, P1-T062.
- **Blocks.** P3-T006.
- **Downstream consumers.** P3-T006 consumes the frozen profile and validated resource confirmation.
- **Preconditions.** P3-T004, P1-T039, P1-T060, P1-T061, P1-T062 complete.
- **Inputs.** Arch §16, §15.2, §12.3; backlog §B.
- **Allowed scope.** Preflight validation; namespace compatibility check.
- **Forbidden actions.** No profile substitution; no execution; no anchor/journal namespace bleed.
- **Required configuration or NONE.** Anchor execution profile (frozen).
- **Implementation responsibilities.** Validate the exact profile and resources; freeze `ResolvedBatchExecutionProfile`; verify namespace separation.
- **Required unit tests.** Profile frozen, not substituted.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** CUDA/VRAM preflight; disk/same-filesystem preflight; namespace separation (cuda lane, synthetic).
- **Required CUDA tests.** CUDA/VRAM availability validation.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Preflight; CUDA lane; integration lanes.
- **Acceptance criteria.** [ ] Exact profile validated and frozen. [ ] CUDA/VRAM/RAM/disk validated. [ ] Anchor namespace separate from journal. [ ] No substitution.
- **Completion evidence.** Changed files/records (preflight validation, profile freeze); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `RamPreflightError`/`DiskSpaceError`/`CudaUnavailableError`/`UnsafeParallelismError` block the campaign.
- **Stop conditions.** Stop if any resource/preflight check fails.
- **Deliverables.** Frozen runtime plan + preflight record.
- **Final review checklist.** [ ] Profile frozen; namespaces separate.

#### P3-T006 — Create the anchor campaign identity and execution-attempt identity

- **Ticket ID.** P3-T006
- **Title.** Create the anchor campaign identity and execution-attempt identity
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** roadmap-orchestrator
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `RunIdentity`, `ExecutionAttemptId`
- **Objective.** Create the anchor campaign identity (`RunIdentity` from the frozen scientific configuration) and the initial `ExecutionAttemptId`, binding the frozen provenance, configuration, matrix, and runtime plan into one coherent campaign manifest.
- **Why this ticket exists.** The campaign is launched under a coherent identity; `RunIdentity` is unchanged across attempts while `ExecutionAttemptId` is per-attempt.
- **Authority references.** Arch §7, §16.7, §18; this backlog §B.
- **Dependencies.** P3-T002, P3-T005.
- **Blocks.** P3-T007.
- **Downstream consumers.** P3-T007 consumes the campaign identity to execute under frozen provenance.
- **Preconditions.** P3-T002, P3-T005 complete.
- **Inputs.** Arch §7, §16.7, §18; backlog §B.
- **Allowed scope.** Campaign/attempt identity creation and manifest binding.
- **Forbidden actions.** No scientific config change (would create a new campaign identity); no execution yet.
- **Required configuration or NONE.** None (uses frozen artifacts).
- **Implementation responsibilities.** Derive `RunIdentity`; mint the first `ExecutionAttemptId`; bind provenance/config/matrix/runtime into the campaign manifest.
- **Required unit tests.** `RunIdentity` derives from resolved config; attempt id operational/distinct.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Campaign manifest shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; integration lanes.
- **Acceptance criteria.** [ ] Campaign `RunIdentity` derived from frozen config. [ ] Initial `ExecutionAttemptId` minted. [ ] Manifest binds all frozen artifacts. [ ] No config drift.
- **Completion evidence.** Changed files/records (campaign identity, manifest); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** Reject any post-freeze scientific config drift.
- **Stop conditions.** Stop if any bound artifact is not frozen.
- **Deliverables.** Anchor campaign identity/manifest.
- **Final review checklist.** [ ] One coherent campaign identity.

#### P3-T007 — Execute the coordinated anchor campaign

- **Ticket ID.** P3-T007
- **Title.** Execute the coordinated anchor campaign
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** roadmap-orchestrator
- **Supporting agents.** federated-learning-engineer, reproducibility-auditor
- **Scientific-execution classification.** ANCHOR_CAMPAIGN_ALLOWED
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (never E-C1/E-S1/E-S3/E-M1)
- **Architecture contracts/types owned.** Training identities, checkpoint identities, score identities, threshold identities, evaluation identities
- **Objective.** Execute the resolved anchor experiment program under the frozen plan and campaign identity: train per seed, select the Regime-A global checkpoint, generate calibration/test scores, and fan compatible calibration scores into the anchor threshold constructions and evaluations.
- **Why this ticket exists.** This is the coordinated historical/reproduction anchor run. It produces anchor evidence only; scientifically analogous anchor cells must never be labeled as formal journal experiments or confirmatory journal evidence.
- **Authority references.** Arch §14, §13, §18; Road §9.1, §20 (immediate-start anchor work); this backlog §B.
- **Dependencies.** P3-T006.
- **Blocks.** P3-T009.
- **Downstream consumers.** P3-T009 consumes the anchor scientific artifacts for archival and readiness verification.
- **Preconditions.** P3-T006 (campaign identity created; plan frozen) complete.
- **Inputs.** Arch §14, §13, §18; Road §9.1, §20; backlog §B.
- **Allowed scope.** Real anchor training/scoring/thresholding/evaluation under the frozen plan.
- **Forbidden actions.** No one-process/one-attempt assumption; no scientific tuning from observed results; no invented seed order; no blanket "exactly once"; no journal-track execution; no scientific config change.
- **Required configuration or NONE.** Frozen anchor configuration only.
- **Implementation responsibilities.** Run the executor over the final plan; reuse compatible artifacts; compute required training/scoring/threshold/evaluation identities; persist artifacts atomically.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks (not tests-as-experiments): plan-vs-executed stage-identity match; artifact integrity/lineage verified as stages complete; no scientific value only in logs.
- **Validation commands.** Execution under the frozen plan; artifact inspection; lineage tracing.
- **Acceptance criteria.** [ ] Executed stages match the frozen plan identities. [ ] Compatible artifacts reused; new identities computed as required. [ ] Artifacts committed atomically with closed lineage. [ ] No config change during execution.
- **Completion evidence.** Standard report + campaign/attempt identities + produced stage identities.
- **Failure and blocker behavior.** Typed stage failures persist failure evidence; CUDA-OOM terminal for the attempt; full-participation aborts recorded.
- **Stop conditions.** Stop and persist failure evidence on any typed stage failure; do not tune from observed results.
- **Deliverables.** Anchor scientific artifacts (checkpoints, scores, thresholds, evaluations).
- **Final review checklist.** [ ] Coordinated, not one-shot.

#### P3-T008 — Conditional anchor recovery, resume, and infrastructure-retry handling

- **Ticket ID.** P3-T008
- **Title.** Conditional anchor recovery, resume, and infrastructure-retry handling
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** roadmap-orchestrator
- **Scientific-execution classification.** ANCHOR_CAMPAIGN_ALLOWED
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** `ExecutionAttemptId` (new attempt IDs on resume)
- **Objective.** Resume the anchor campaign safely after interruption/pressure/transient failure, skipping completed compatible stages, using only compatible recovery checkpoints, and recording new execution-attempt identities while preserving the scientific `RunIdentity`.
- **Why this ticket exists.** Campaign scope permits resume; recovery must be compatible; infrastructure retries preserving identical scientific identity continue the same campaign; CUDA-OOM requires an explicit new attempt.
- **Authority references.** Arch §16.6–16.7, §17.3, §18; this backlog §B.
- **Dependencies.** P3-T006.
- **Blocks.** P3-T009.
- **Downstream consumers.** P3-T009 consumes resumed anchor artifacts with updated attempt identities.
- **Preconditions.** Available after P3-T006 creates the campaign identity and execution begins; activate only for an interruption, transient infrastructure failure, or compatible committed recovery state.
- **Inputs.** Arch §16.6–16.7, §17.3, §18; backlog §B.
- **Allowed scope.** Resume orchestration; recovery-compatibility validation; retry of classified transient failures.
- **Forbidden actions.** No auto `FAILED_OOM→PAUSED/RECOVERED`; no resume under a changed profile; no scientific-identity change; no retry of scientific/determinism failure.
- **Required configuration or NONE.** Frozen configuration only.
- **Implementation responsibilities.** Skip completed compatible stages; validate recovery compatibility; continue the same `ExecutionAttemptId` for a graceful-pressure-boundary resume (safe unit finishes and commits, then resumes within the same attempt, per Arch §17.3); mint a new `ExecutionAttemptId` only for resume after an interruption or transient-failure recovery (not a graceful-pressure boundary); record failure and retry.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: uninterrupted-vs-resumed equivalence; incompatible recovery rejected; attempt ids recorded.
- **Validation commands.** Resume execution; lineage tracing; artifact inspection.
- **Acceptance criteria.** [ ] Completed compatible stages skipped. [ ] Only compatible recovery used. [ ] New attempt ids recorded; `RunIdentity` unchanged. [ ] No profile change on resume. [ ] Mark `NOT_APPLICABLE` with uninterrupted-completion evidence when no recovery condition occurs.
- **Completion evidence.** Standard report + attempt identities.
- **Failure and blocker behavior.** `RecoveryStateMismatchError`/`ResumeIncompatibilityError`; bounded transient retry only.
- **Stop conditions.** Mark `NOT_APPLICABLE` when execution completes uninterrupted. Stop if recovery is incompatible or the profile changed (start a new run under new identities).
- **Deliverables.** Resume/retry records.
- **Final review checklist.** [ ] Resume ≠ new campaign.

#### P3-T009 — Completeness and same-model/same-score compatibility audits; typed failure persistence

- **Ticket ID.** P3-T009
- **Title.** Completeness and same-model/same-score compatibility audits; typed failure persistence
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** Model/checkpoint completeness verification, score completeness verification, typed failure persistence, incomplete-output detection
- **Objective.** Audit the completed anchor: model/checkpoint completeness, score completeness, and same-model/same-score compatibility across B1–B4 (one selected checkpoint, one calibration set, one test set per compatible seed), and confirm every typed failure and incomplete output is persisted, not silently dropped.
- **Why this ticket exists.** The confirmatory ladder requires the same model and scores across B1–B4; incomplete outputs must be detected and persisted, never mistaken for complete.
- **Authority references.** Arch §13, §29.1, §18.2 (idempotent per-stage); this backlog §B, §E.
- **Dependencies.** P3-T007; P3-T008 when activated.
- **Blocks.** P3-T010.
- **Downstream consumers.** P3-T010 (requires completeness/compatibility verification before statistical analysis).
- **Preconditions.** Valid uninterrupted P3-T007 completion evidence, or valid P3-T007 evidence plus P3-T008 evidence when recovery activated.
- **Inputs.** Arch §13, §29.1, §18.2; backlog §B, §E.
- **Allowed scope.** Completeness/compatibility auditing; failure-evidence verification.
- **Forbidden actions.** No execution; no acceptance of incomplete output as complete; no reuse without proven lineage compatibility.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify model/checkpoint/score completeness; verify B1–B4 share compatible identities; confirm failure/incomplete-output persistence.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Same-checkpoint/same-score across B1–B4; incomplete output detected; failure evidence present.
- **Validation commands.** Artifact inspection; lineage tracing.
- **Acceptance criteria.** [ ] Model/checkpoint/score completeness verified. [ ] B1–B4 share compatible identities. [ ] Failures/incompletes persisted. [ ] No incomplete accepted as complete.
- **Completion evidence.** Changed files/records (audit reports, lineage verification records); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** Incomplete/invalid-lineage artifacts flagged for recompute (not accepted). Stop if completeness/compatibility fails; preserve evidence and permit only a diagnosed technical-invalidity action: compatible recovery, recomputation of the invalidated stage, or a new execution attempt.
- **Stop conditions.** Stop if completeness/compatibility fails; preserve evidence and permit only a diagnosed technical-invalidity action: compatible recovery, recomputation of the invalidated stage, or a new execution attempt. A scientific configuration change requires a new campaign identity.
- **Deliverables.** Anchor completeness/compatibility audit.
- **Final review checklist.** [ ] Same model/scores across ladder.

#### P3-T010 — Historical-reference diagnostic and full configured anchor statistical analysis

- **Ticket ID.** P3-T010
- **Title.** Historical-reference diagnostic and full configured anchor statistical analysis
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** statistics
- **Owner.** statistics-auditor
- **Supporting agents.** reviewer2-red-team
- **Scientific-execution classification.** ANCHOR_CAMPAIGN_ALLOWED
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4 (not a journal experiment ID)
- **Architecture contracts/types owned.** Statistical analysis specifications, BCa CI computation, honesty diagnostic, typed degeneracy persistence
- **Objective.** Run the full configured anchor statistical analysis over the completed evaluations — paired Δ, 95% BCa CI with positive-direction interpretation, descriptive Wilcoxon/Cliff's — and the five-seed historical-reference honesty diagnostic against `[0.647, 0.769]` with the authority-defined approximately-20%-wider rule.
- **Why this ticket exists.** This produces an anchor reproduction and honesty record, not the formal journal confirmatory verdict. Any less-favorable, null, mixed, or opposite-direction anchor evidence is retained and reported without suppression.
- **Authority references.** Arch §9.3; Road §3, §5.1, §10 (seed-extension honesty rule).
- **Dependencies.** P3-T009.
- **Blocks.** P3-T011.
- **Downstream consumers.** P3-T011 (requires statistical verdict and honesty diagnostic for integrity decision).
- **Preconditions.** P3-T009 complete.
- **Inputs.** Arch §9.3; Road §3, §5.1, §10.
- **Allowed scope.** Statistical analysis over completed anchor evaluations.
- **Forbidden actions.** No suppression of a less-favorable result; no silent BCa→percentile; no confirmatory Wilcoxon/Cliff branch; no result-driven tuning.
- **Required configuration or NONE.** Frozen confirmatory statistical config.
- **Implementation responsibilities.** Compute the confirmatory verdict and honesty diagnostic; persist typed degeneracy if any.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Verdict computed from frozen evaluations; honesty diagnostic applied; degeneracy typed if present.
- **Validation commands.** Statistical analysis; artifact inspection.
- **Acceptance criteria.** [ ] Confirmatory BCa verdict computed. [ ] Honesty diagnostic applied with the ~20%-wider rule. [ ] No suppression. [ ] Degeneracy typed if present.
- **Completion evidence.** Standard report + statistical identity.
- **Failure and blocker behavior.** `StatisticsError` for unexpected only; degeneracy typed. Stop if the honesty diagnostic blocks expansion; record the block and route to acceptance/rerun.
- **Stop conditions.** Stop if the honesty diagnostic blocks expansion; record the block and route to acceptance/rerun.
- **Deliverables.** Anchor statistical verdict + honesty diagnostic.
- **Final review checklist.** [ ] Verdict honest and typed.

#### P3-T011 — Anchor integrity decision, technical-invalidity correction path, artifact freeze, journal-unlock gate

- **Ticket ID.** P3-T011
- **Title.** Anchor integrity decision, technical-invalidity correction path, artifact freeze, journal-unlock gate
- **Phase.** 3
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** statistics-auditor, reviewer2-red-team, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** ANCHOR
- **Roadmap experiment IDs.** ANCHOR-B0–B4
- **Architecture contracts/types owned.** `CAMPAIGN_INTEGRITY_STATUS`, `SCIENTIFIC_OUTCOME_STATUS`
- **Objective.** Record `CAMPAIGN_INTEGRITY_STATUS` separately from `SCIENTIFIC_OUTCOME_STATUS`; freeze every integrity-valid anchor evidence package, apply the roadmap's precommitted fallback wording to null, mixed, unfavorable, and opposite-direction outcomes, and set the journal-unlock gate from integrity plus authority blockers. **This is the anchor-integrity and journal-unlock gate.**
- **Why this ticket exists.** A valid scientific result is evidence regardless of direction. Journal implementation is blocked by invalid or unresolved anchor provenance, not by a result that is null, mixed, weaker than expected, non-significant, or unfavorable.
- **Authority references.** Arch §22.4 (pre-spec provenance), §29.1 (journal expansion requires passed anchor); Road §20; this backlog §B (rerun discipline).
- **Dependencies.** P3-T010.
- **Blocks.** P4-T001.
- **Downstream consumers.** P4-T001 (requires the journal-unlock gate before journal implementation begins).
- **Preconditions.** P3-T010 complete.
- **Inputs.** Arch §22.4, §29.1; Road §20; backlog §B.
- **Allowed scope.** Integrity/outcome decision records; technical-invalidity correction path; evidence freeze; journal-unlock gate.
- **Forbidden actions.** No suppression; no result-seeking rerun; no journal unlock with unresolved technical invalidity or authority blocker; no scientific rerun without a diagnosed invalidity and the §B record.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Record both statuses with evidence; freeze all integrity-valid evidence; route only diagnosed corrupted input, implementation defect, incomplete artifact, lineage mismatch, determinism/configuration/statistical implementation defect, framework/infrastructure failure, or interrupted execution without a valid committed recovery state to corrective work. A changed scientific configuration creates a new campaign identity.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Integrity and outcome statuses are independent; valid null/mixed/unfavorable evidence freezes; only technical invalidity permits corrective work; journal-unlock reflects integrity and blockers.
- **Validation commands.** Evidence freeze; lineage tracing; changelog record.
- **Acceptance criteria.** [ ] Both statuses recorded with evidence. [ ] Valid null/mixed/unfavorable evidence frozen/immutable. [ ] Technical-invalidity correction path defined per §B. [ ] Journal-unlock reflects integrity and authority blockers, never preferred direction.
- **Completion evidence.** Changed files/records (integrity/outcome decision records, frozen evidence packages, journal-unlock gate status); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** A scientifically unfavorable outcome is frozen and reported. Only diagnosed technical invalidity routes to corrective work with a new attempt identity, preserved failed evidence, explicit approval, and unchanged-science confirmation (or a new campaign identity). Stop journal implementation on technical invalidity or an unresolved authority blocker; never stop or rerun solely because the scientific outcome is unfavorable.
- **Stop conditions.** Stop journal implementation on technical invalidity or an unresolved authority blocker; never stop or rerun solely because the scientific outcome is unfavorable.
- **Deliverables.** Anchor integrity/outcome decision + frozen evidence + journal-unlock gate.
- **Final review checklist.** [ ] Journal unlock is integrity-based, not direction-based.

### Phase 4 — Complete Journal-Extension Implementation

> **Phase-wide note (applies to every P4 ticket).** No journal scientific execution occurs in Phase 4: implementation is validated on synthetic data; frozen anchor artifacts are inspected read-only; dataset feasibility is inspected, not executed. Sci-exec is `FORBIDDEN` (implementation) or `PLANNING_ONLY` (feasibility/inventory). Campaign scope is `JOURNAL`. Every threshold-only extension must reuse compatible anchor score artifacts through lineage validation, expressed as lineage-aware reuse (never "each score generated once"); every stress test carries distinct training/scoring identities and stays outside the causal ladder; no supportive module may become confirmatory; no seed values/orderings are invented. "Completion evidence" is the standard five-heading report plus resulting identities and roadmap experiment IDs.

#### P4-T001 — Implement E-C1 confirmatory experiment specification and identity

- **Ticket ID.** P4-T001
- **Title.** Implement E-C1 confirmatory experiment specification and identity
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** experiment
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** `ConfirmatoryExperimentProfileSpec`
- **Objective.** Implement the E-C1 journal experiment as a `ConfirmatoryExperimentProfileSpec` cell (Regime A, B1 vs B2, CV(FPR), ten paired seeds, Δ = B1 − B2, 95% BCa positive-direction) referencing the frozen anchor artifacts, with no non-confirmatory arm.
- **Why this ticket exists.** E-C1 is the sole confirmatory endpoint carried into the journal; it must be the locked shape and reuse compatible anchor evidence, extended to ten seeds.
- **Authority references.** Arch §8.3 (`ConfirmatoryExperimentProfileSpec`), §29.1; Road §3, §5.1, §9.1.
- **Dependencies.** P3-T011, P1-T029.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-C1 confirmatory endpoint and experiment identity.
- **Preconditions.** P3-T011 (anchor accepted), P1-T029 complete.
- **Inputs.** Arch §8.3, §29.1; Road §3, §5.1, §9.1; frozen anchor score identities.
- **Allowed scope.** E-C1 config (`configs/experiments/E-C1.yaml`) and its domain profile.
- **Forbidden actions.** No B0/B3/B4/variant arm on E-C1; no alternate primary metric; no unpaired cohort; no journal execution; no invented seeds.
- **Required configuration or NONE.** E-C1 scientific config locked to BCa/0.95/ten.
- **Implementation responsibilities.** Compose the confirmatory profile; bind to the ten-paired-seed authoritative plan; reference frozen anchor score identities for reuse validation.
- **Required unit tests.** E-C1 rejects non-confirmatory arms; reuse of anchor scores validated by lineage.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-C1 runs end-to-end on synthetic data.
- **Validation commands.** Unit; synthetic system; configuration validation.
- **Acceptance criteria.** [ ] E-C1 is confirmatory-only. [ ] Ten-paired-seed plan referenced (not invented). [ ] Anchor reuse validated by lineage. [ ] No journal execution.
- **Completion evidence.** Changed files (E-C1 config and domain profile); commands run and results; E-C1 identity; cleanup confirmation.
- **Failure and blocker behavior.** Validation failure on any non-confirmatory addition.
- **Stop conditions.** None (anchor accepted precondition).
- **Deliverables.** E-C1 specification/config.
- **Final review checklist.** [ ] Confirmatory shape locked.

#### P4-T002 — Implement E-S1 construction-sensitivity and E-S2 q-sensitivity

- **Ticket ID.** P4-T002
- **Title.** Implement E-S1 construction-sensitivity and E-S2 q-sensitivity
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-S1, E-S2
- **Architecture contracts/types owned.** Construction sensitivity specs, q-sensitivity threshold expansion specs
- **Objective.** Implement E-S1 (B1/B1-pool/B1-wt/B2 construction sensitivity; CV(FPR), IQR, max−min) and E-S2 (q ∈ {0.90, 0.95, 0.975, 0.99} over B1/B2/B4), both reusing compatible calibration score artifacts through lineage validation; B4 membership stays fixed while member local-q thresholds are averaged.
- **Why this ticket exists.** These are threshold-only supportive analyses (Tier 2) that must reuse compatible scores and never retrain/rescore; q-sensitivity reuses the fixed B4 assignment across q.
- **Authority references.** Arch §13.3 (reuse), §9.2 (B4 across q); Road §5.2, §9.2 (E-S1/E-S2).
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-S1/E-S2 sensitivity analyses.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §13.3, §9.2; Road §5.2, §9.2; compatible calibration score artifacts.
- **Allowed scope.** E-S1/E-S2 configs and threshold-only expansion.
- **Forbidden actions.** No retraining/rescoring; no "each score generated once" wording; no B4 recluster per q; no journal execution.
- **Required configuration or NONE.** E-S2 q-grid from the roadmap; E-S1 construction set.
- **Implementation responsibilities.** Construction-sensitivity and q-grid expansion over compatible scores; B4 q-specific thresholds from fixed assignment.
- **Required unit tests.** Threshold-only reuse preserves scoring lineage; q-grid expansion; B4 not reclustered per q.
- **Required property tests.** Ordering-sensitivity computed.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-S1/E-S2 on synthetic scores.
- **Validation commands.** Unit; property; synthetic system.
- **Acceptance criteria.** [ ] E-S1/E-S2 reuse compatible scores by lineage. [ ] No retrain/rescore. [ ] B4 assignment fixed across q. [ ] No journal execution.
- **Completion evidence.** Changed files (E-S1/E-S2 configs and threshold expansion); commands run and results; threshold identities; cleanup confirmation.
- **Failure and blocker behavior.** `ReuseIncompatibilityError` → RECOMPUTE when lineage mismatches.
- **Stop conditions.** None.
- **Deliverables.** E-S1/E-S2 specs/configs.
- **Final review checklist.** [ ] Lineage-aware reuse.

#### P4-T003 — Implement E-S3 Dirichlet severity (Regime C)

- **Ticket ID.** P4-T003
- **Title.** Implement E-S3 Dirichlet severity (Regime C)
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** data-pipeline-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-S3
- **Architecture contracts/types owned.** `RegimeCompatibilitySpec` (Regime C), Dirichlet partition spec
- **Objective.** Implement E-S3: the Regime C Dirichlet partition (20 synthetic clients, α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}) with its own training/scoring identities, B1/B2/B4 evaluation, and per-α CV(FPR) trend with BCa where required.
- **Why this ticket exists.** Regime C is a supportive severity sweep (Tier 2) with genuinely new partitions/training identities; low-α seed ranges form a high-heterogeneity band, not strict monotonicity.
- **Authority references.** Arch §8.3 (RegimeCompatibilitySpec C), §14; Road §7, §9.2 (E-S3), §5.2.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-S3 Regime C severity analysis.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §8.3, §14; Road §7, §9.2, §5.2; Regime C seed policy.
- **Allowed scope.** Regime C partition/training/scoring/evaluation specs and configs.
- **Forbidden actions.** No assumption Regime C shares anchor seed identifiers unless the roadmap defines it; no journal execution; no strict-monotonicity claim where a band is warranted.
- **Required configuration or NONE.** Regime C α-grid and client count from the roadmap.
- **Implementation responsibilities.** Dirichlet partitioner (20 clients, α-grid); new training/scoring identities; per-α analysis with band reporting.
- **Required unit tests.** Distinct Regime-C identities.
- **Required property tests.** Dirichlet sample conservation, no overlap, valid α, deterministic output, timeout compliance (SYNTHETIC_TINY).
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-S3 sweep on synthetic data.
- **Validation commands.** Property; unit; synthetic system.
- **Acceptance criteria.** [ ] Dirichlet 20-client α-grid implemented. [ ] Distinct Regime-C identities. [ ] Band reporting for low-α. [ ] No invented seed sharing.
- **Completion evidence.** Changed files (Regime C partition/training/scoring/evaluation specs and configs); commands run and results; Regime C identities; cleanup confirmation.
- **Failure and blocker behavior.** `PartitionError` on invalid α; low-α band reporting; stop if Regime C seed policy is unspecified.
- **Stop conditions.** Stop if Regime C seed policy is unspecified; use the resolved authoritative spec, else blocker.
- **Deliverables.** E-S3 Regime C implementation.
- **Final review checklist.** [ ] New identities, band-aware.

#### P4-T004 — Implement E-M1 cluster/family granularity and stability

- **Ticket ID.** P4-T004
- **Title.** Implement E-M1 cluster/family granularity and stability
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-M1
- **Architecture contracts/types owned.** `ClusterDispersionResult`, cluster granularity specs, cluster stability specs
- **Objective.** Implement E-M1: B1/B2/B3/B4 comparison plus cluster-granularity sweep (feasible K), within/across-cluster dispersion, and cluster-stability (adjusted Rand) over compatible scores/fingerprints; B4 stays exploratory at N=9.
- **Why this ticket exists.** E-M1 is the core mechanism module (Tier 5) turning B3/B4 into a granularity+stability analysis; canonical K=3, other K exploratory.
- **Authority references.** Arch §9.2, §9.3 (`ClusterDispersionResult`); Road §5.5, §8 (module table), §9.2 (E-M1).
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-M1 mechanism analysis.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.2, §9.3; Road §5.5, §8, §9.2; compatible scores/fingerprints.
- **Allowed scope.** E-M1 specs/configs (cluster granularity + stability).
- **Forbidden actions.** No canonical claim for K≠3; no retrain/rescore; no journal execution.
- **Required configuration or NONE.** E-M1 K-grid (canonical K=3; exploratory K via separate profile).
- **Implementation responsibilities.** Granularity sweep over feasible K; within/across dispersion; adjusted-Rand stability on immutable assignments.
- **Required unit tests.** Canonical K=3 vs exploratory; dispersion computed.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Fixed-fingerprint assignment/adjusted-Rand (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-M1 on synthetic scores.
- **Validation commands.** Integration; unit; synthetic system.
- **Acceptance criteria.** [ ] B1–B4 + granularity + stability implemented. [ ] Canonical K=3, others exploratory. [ ] Instability reported. [ ] Reuse compatible scores.
- **Completion evidence.** Changed files (E-M1 specs/configs for cluster granularity and stability); commands run and results; threshold identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; report instability explicitly.
- **Stop conditions.** None.
- **Deliverables.** E-M1 implementation.
- **Final review checklist.** [ ] Mechanism, not confirmatory.

#### P4-T005 — Implement E-M2 B4 cluster-feature ablation and contingency

- **Ticket ID.** P4-T005
- **Title.** Implement E-M2 B4 cluster-feature ablation and contingency
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-M2
- **Architecture contracts/types owned.** B4 feature ablation specs, contingency table specs
- **Objective.** Implement E-M2: B4 cluster-feature ablation (fingerprint subsets vs all-four) and a cluster-to-device contingency table over compatible fingerprints/scores, reporting subset instability.
- **Why this ticket exists.** E-M2 (Tier 5/7) tests whether B4 clusters carry taxonomy-free structure; interpretability uses a contingency table/heatmap (never a Sankey).
- **Authority references.** Arch §22.1 (no Sankey), §9.2; Road §5.5, §9.2 (E-M2), SB-19.
- **Dependencies.** P4-T004.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-M2 ablation and interpretability analysis.
- **Preconditions.** P4-T004 complete.
- **Inputs.** Arch §22.1, §9.2; Road §5.5, §9.2; SB-19; compatible fingerprints/scores.
- **Allowed scope.** E-M2 specs/configs (feature subsets + contingency).
- **Forbidden actions.** No Sankey; no retrain/rescore; no journal execution.
- **Required configuration or NONE.** E-M2 fingerprint-subset set.
- **Implementation responsibilities.** Subset assignments; contingency table; per-seed stability.
- **Required unit tests.** Subset assignments; contingency computed; no Sankey figure.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Contingency shape (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-M2 on synthetic fingerprints.
- **Validation commands.** Unit; integration; synthetic system.
- **Acceptance criteria.** [ ] Feature-subset ablation + contingency. [ ] No Sankey. [ ] Instability reported. [ ] Reuse compatible fingerprints.
- **Completion evidence.** Changed files (E-M2 specs/configs for feature subsets and contingency); commands run and results; threshold identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; report subset instability.
- **Stop conditions.** None.
- **Deliverables.** E-M2 implementation.
- **Final review checklist.** [ ] Contingency, not Sankey.

#### P4-T006 — Implement E-M3 per-client CDF overlays and Ennio deep dive

- **Ticket ID.** P4-T006
- **Title.** Implement E-M3 per-client CDF overlays and Ennio deep dive
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** statistics-auditor
- **Supporting agents.** report-output-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-M3
- **Architecture contracts/types owned.** CDF overlay specs, Ennio Doorbell deep dive report specs, P10 Macro-F1 tradeoff figure specs
- **Objective.** Implement E-M3: per-client benign+attack score CDF overlays (B1/B2/B4) and the Ennio Doorbell deep dive, plus the P10 Macro-F1 tradeoff figure, with no device filtering.
- **Why this ticket exists.** E-M3 (Tier 5) explains the FPR-concentration mechanism and the honest P10 Macro-F1 tradeoff; all clients are shown.
- **Authority references.** Arch §22.1 (CDF_OVERLAY); Road §5.5, §9.2 (E-M3), §5.6 (P10 tradeoff).
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-M3 implementation and report specifications.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §22.1, Road §5.5, §9.2, §5.6.
- **Allowed scope.** E-M3 report specs/configs (CDF overlays + deep dive).
- **Forbidden actions.** No device filtering; no hidden P10 degradation; no journal execution.
- **Required configuration or NONE.** E-M3 figure config.
- **Implementation responsibilities.** CDF-input specs from test scores; Ennio deep-dive spec; P10 tradeoff figure spec.
- **Required unit tests.** CDF inputs from committed test scores; all clients present.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-M3 figure inputs on synthetic scores.
- **Validation commands.** Unit; synthetic system.
- **Acceptance criteria.** [ ] Per-client CDF overlays + Ennio deep dive. [ ] P10 tradeoff shown honestly. [ ] No device filtering. [ ] No journal execution.
- **Completion evidence.** Changed files/records (E-M3 report specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `ProvenanceError` on untraced figure.
- **Stop conditions.** None.
- **Deliverables.** E-M3 implementation.
- **Final review checklist.** [ ] No filtering/hiding.

#### P4-T007 — Implement E-M4 JS↔gain association and E-M5 threshold-shift scatter

- **Ticket ID.** P4-T007
- **Title.** Implement E-M4 JS↔gain association and E-M5 threshold-shift scatter
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** statistics-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-M4, E-M5
- **Architecture contracts/types owned.** JS-divergence ↔ gain regression specs, threshold-shift scatter specs
- **Objective.** Implement E-M4 (JS-divergence ↔ gain regression; R², ρ, weak R² retained as a real result) and E-M5 (threshold-shift Δτ vs ΔFPR/ΔTPR scatter over all 9 devices, no filtering).
- **Why this ticket exists.** E-M4/E-M5 (Tier 5) provide association (not causation) evidence and the quantified fairness–sensitivity surface; weak associations are honest results.
- **Authority references.** Arch §9.3; Road §5.5, §9.2 (E-M4/E-M5).
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-M4/E-M5 implementation and statistical results.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.3; Road §5.5, §9.2.
- **Allowed scope.** E-M4/E-M5 specs/configs.
- **Forbidden actions.** No causation claim; no device filtering; no journal execution.
- **Required configuration or NONE.** E-M4/E-M5 configs.
- **Implementation responsibilities.** Regression/association over distributions/evaluations; threshold-shift scatter from thresholds/scores.
- **Required unit tests.** Association computed with caveats; scatter over all 9 devices.
- **Required property tests.** Regression bounds.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Unit; property; synthetic system.
- **Acceptance criteria.** [ ] E-M4 association (not causation), weak R² retained. [ ] E-M5 scatter, all 9 devices. [ ] No filtering. [ ] No journal execution.
- **Completion evidence.** Changed files/records (E-M4/E-M5 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `StatisticsError` for unexpected only.
- **Stop conditions.** None.
- **Deliverables.** E-M4/E-M5 implementation.
- **Final review checklist.** [ ] Association only.

#### P4-T008 — Implement E-V1 calibration-size sweep and size-aware fallback

- **Ticket ID.** P4-T008
- **Title.** Implement E-V1 calibration-size sweep and size-aware fallback
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-V1
- **Architecture contracts/types owned.** Calibration-size sweep specs, calibration-size-aware fallback policy
- **Objective.** Implement E-V1: calibration-size sweep (n ∈ {50,100,250,500,1000,5000}) with threshold-variance and worst-client-FPR vs n for B1/B2/B4, plus the calibration-size-aware fallback that replaces (not follows) the ordinary hard fallback in its declared cells.
- **Why this ticket exists.** E-V1 (Tier 6) defends B2 against the small-benign-window objection; the size-aware fallback is a distinct authorized variant, fingerprinted and persisted.
- **Authority references.** Arch §9.3 (calibration-size-aware fallback), §29.4 (19); Road §5.6, §9.2 (E-V1), §8.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-V1 implementation, subsample identities, and size-aware fallback results.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.3, §29.4; Road §5.6, §9.2, §8.
- **Allowed scope.** E-V1 specs/configs (subsample grid + size-aware fallback).
- **Forbidden actions.** No fallback pre-emption of the size-aware variant; no retrain; no journal execution.
- **Required configuration or NONE.** E-V1 n-grid from the roadmap.
- **Implementation responsibilities.** Subsample identities/results; size-dependent λ(n_k) fallback replacing the hard fallback in its cells.
- **Required unit tests.** Size-aware fallback replaces hard fallback in its cells; fingerprinted.
- **Required property tests.** Subsample determinism.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** E-V1 sweep.
- **Validation commands.** Property; unit; synthetic system.
- **Acceptance criteria.** [ ] n-grid sweep implemented. [ ] Size-aware fallback replaces hard fallback in its cells. [ ] Fingerprinted/persisted. [ ] Reuse compatible scores.
- **Completion evidence.** Changed files/records (E-V1 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; report plateau/collapse.
- **Stop conditions.** None.
- **Deliverables.** E-V1 implementation.
- **Final review checklist.** [ ] Fallback replacement correct.

#### P4-T009 — Implement E-V2 local-global shrinkage (τ-shrink)

- **Ticket ID.** P4-T009
- **Title.** Implement E-V2 local-global shrinkage (τ-shrink)
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-V2
- **Architecture contracts/types owned.** τ-shrink local-global shrinkage policy specs
- **Objective.** Implement E-V2: τ-shrink local-global shrinkage τ_k(λ) = λ·τ_k,p95 + (1−λ)·τ_global over λ ∈ {0, 0.25, 0.5, 0.75, 1.0}, with CV(FPR) and P10 Macro-F1 per λ, reusing compatible scores; non-monotone λ behavior reported as-is.
- **Why this ticket exists.** E-V2 (Tier 6 supportive) tests calibration robustness without discarding personalization; no favorable λ is cherry-picked; the label is τ-shrink/LGS (never B3-LGS).
- **Authority references.** Arch §9.2; Road §4 (τ-shrink/LGS lock), §9.2 (E-V2), §12.5.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-V2 implementation and shrinkage results.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.2; Road §4, §9.2, §12.5.
- **Allowed scope.** E-V2 specs/configs (λ-grid).
- **Forbidden actions.** No B3-LGS label; no λ cherry-picking; no retrain; no journal execution.
- **Required configuration or NONE.** E-V2 λ-grid from the roadmap.
- **Implementation responsibilities.** λ-grid shrinkage over compatible scores; per-λ CV(FPR)/P10.
- **Required unit tests.** Label is τ-shrink; λ-grid; reuse scores.
- **Required property tests.** Shrinkage interpolates B2↔global within [0,1].
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Property; unit; synthetic system.
- **Acceptance criteria.** [ ] λ-grid shrinkage implemented. [ ] Labeled τ-shrink/LGS. [ ] Non-monotonicity reported. [ ] Reuse compatible scores.
- **Completion evidence.** Changed files/records (E-V2 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; report non-monotonicity.
- **Stop conditions.** None.
- **Deliverables.** E-V2 implementation.
- **Final review checklist.** [ ] Never B3-LGS.

#### P4-T010 — Implement E-V3 split-conformal B2-conf and conformal coverage

- **Ticket ID.** P4-T010
- **Title.** Implement E-V3 split-conformal B2-conf and conformal coverage
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-V3
- **Architecture contracts/types owned.** `ConformalSplitSpec`, `ConformalCoverageResult`
- **Objective.** Implement E-V3: split/federated-conformal B2-conf at marginal coverage 1−α (α = 0.05, = 1−q) with an explicit finite-sample quantile-index rule, TEST excluded from the conformal fit, and a `ConformalCoverageResult` distinct from eligibility coverage.
- **Why this ticket exists.** E-V3 closes the tautology critique (finite-sample coverage) supporting Tier 1; conformal and eligibility coverage have disjoint identities.
- **Authority references.** Arch §9.1 (`ConformalSplitSpec`), §9.3 (`ConformalCoverageResult`), §29.4 (19); Road §5.2/§5.6, §9.2 (E-V3), §13 (L04).
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes E-V3 implementation, conformal threshold identity, and coverage results.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.1, §9.3, §29.4; Road §5.2, §5.6, §9.2, §13.
- **Allowed scope.** E-V3 specs/configs (conformal split + coverage).
- **Forbidden actions.** No TEST in the conformal fit; no coverage-field substitution; no journal execution.
- **Required configuration or NONE.** E-V3 α=0.05 config.
- **Implementation responsibilities.** Proper-fit/calibration split; finite-sample index rule; conformal coverage result.
- **Required unit tests.** α == 1−q; TEST excluded; conformal≠eligibility coverage.
- **Required property tests.** Finite-sample index.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Unit; property; synthetic system.
- **Acceptance criteria.** [ ] B2-conf at α=0.05 with explicit index rule. [ ] TEST excluded. [ ] Conformal≠eligibility coverage. [ ] Reuse compatible scores.
- **Completion evidence.** Changed files/records (E-V3 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; report coverage miss as a conformal-adaptation limit.
- **Stop conditions.** None.
- **Deliverables.** E-V3 implementation.
- **Final review checklist.** [ ] Coverage identities disjoint.

#### P4-T011 — Implement the B-a CICIoT2023 boundary

- **Ticket ID.** P4-T011
- **Title.** Implement the B-a CICIoT2023 boundary
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** data-pipeline-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** B-a
- **Architecture contracts/types owned.** `ArchitectureCatalogueId("B_A_APPLICABILITY_BOUNDARY")`, file-level pseudo-client partition specification, feature-count verification gate
- **Objective.** Implement Regime B-a (CICIoT2023 file-level pseudo-clients, d=39 with feature-count verification before any print claim) as `ArchitectureCatalogueId("B_A_APPLICABILITY_BOUNDARY")` with authorized B0/B1/B2/B4, CV(FPR), applicable absolute dispersion, and pairwise-JS — boundary-only, no natural-device generalization.
- **Why this ticket exists.** B-a is a near-homogeneous applicability boundary (Tier 6); its null is never generalized to CICIoT2023; the feature count must be re-verified against the actual processed artifact.
- **Authority references.** Arch §8.3 (B-a profile), §22.5; Road §7, SB-16, §12.10.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the B-a boundary implementation and feature-count verification results.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §8.3 (B-a profile), §22.5; Road §7, SB-16, §12.10.
- **Allowed scope.** B-a specs/configs; feature-count verification.
- **Forbidden actions.** No physical-device/natural-device claim; no generalization of the null; no journal execution.
- **Required configuration or NONE.** CICIoT2023 B-a config (verified d).
- **Implementation responsibilities.** File pseudo-client partition; feature-count verification gate; authorized comparisons; boundary-only reporting.
- **Required unit tests.** Boundary-only reporting; no generalization path.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): file pseudo-client partition; feature-count verification.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Integration (data); unit; synthetic system.
- **Acceptance criteria.** [ ] B-a file pseudo-clients + feature-count verification. [ ] Boundary-only reporting. [ ] No natural-device generalization. [ ] No journal execution.
- **Completion evidence.** Changed files (B-a specs/configs, feature-count verification); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `DatasetError` on feature-count mismatch (blocks print claim). Stop print claims if the actual processed feature count differs from d=39; record the verification.
- **Stop conditions.** Stop print claims if the actual processed feature count differs from d=39; record the verification.
- **Deliverables.** B-a implementation.
- **Final review checklist.** [ ] Boundary-only.

#### P4-T012 — Implement B-b/temporal CICIoT2023 rejection and suppression records

- **Ticket ID.** P4-T012
- **Title.** Implement B-b/temporal CICIoT2023 rejection and suppression records
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** feasibility
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-R1, E-R2
- **Architecture contracts/types owned.** `RejectionRecord`, `SuppressionRecord`, `B_B_REJECTED_NO_METADATA`, `TEMPORAL_REJECTED_NO_TIMESTAMPS`
- **Objective.** Implement the non-executable rejection/suppression records for CICIoT2023 B-b (`B_B_REJECTED_NO_METADATA`) and temporal probing (`TEMPORAL_REJECTED_NO_TIMESTAMPS`), plus the other rejected experiments (E-R3..R8), as `RejectionRecord`/`SuppressionRecord` values with no executable path.
- **Why this ticket exists.** Rejected experiments must exist only as non-executable records; no strategy registry/planner/config union may create an executable path for them.
- **Authority references.** Arch §6.1 (rejection reasons), §29.4 (68); Road §9.4 (rejected), §7 (B-b), §11 (temporal).
- **Dependencies.** P1-T007, P4-T011.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the rejection/suppression records to ensure no rejected experiments are executable.
- **Preconditions.** P1-T007, P4-T011 complete.
- **Inputs.** Arch §6.1 (rejection reasons), §29.4 (68); Road §9.4 (rejected), §7 (B-b), §11 (temporal).
- **Allowed scope.** Rejection/suppression records under `domain/experiments/feasibility.py` and `docs/decisions/`.
- **Forbidden actions.** No executable path for a rejected experiment; no relabeling; no journal execution.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** `RejectionRecord`/`SuppressionRecord` for E-R1..R8; stable rendered labels; suppression-note wording.
- **Required unit tests.** Stable rendered labels.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Every `ExecutionStatus.REJECTED` catalogue entry is non-executable; no registry accepts a rejected method.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Architecture; unit lanes.
- **Acceptance criteria.** [ ] E-R1..R8 non-executable records present. [ ] Stable rendered labels. [ ] No executable path. [ ] Suppression wording recorded.
- **Completion evidence.** Changed files (domain/experiments/feasibility.py, docs/decisions/); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `FeasibilityRejection` if a rejected experiment is requested.
- **Stop conditions.** None.
- **Deliverables.** Rejection/suppression records.
- **Final review checklist.** [ ] Rejected ≠ executable.

#### P4-T013 — Implement the Regime D Edge-IIoTset source/schema/feasibility audit

- **Ticket ID.** P4-T013
- **Title.** Implement the Regime D Edge-IIoTset source/schema/feasibility audit
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P2 — Conditional
- **Ticket type.** feasibility
- **Owner.** data-pipeline-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-X1
- **Architecture contracts/types owned.** `RegimeDFeasibilityResult`, `FeasibilityGateEvaluator`, Edge-IIoTset source/schema inspection specification
- **Objective.** Implement the Edge-IIoTset source/schema inspection and the first-principles feasibility audit deciding device-vs-group client assignment, producing a `RegimeDFeasibilityResult` gated on ≥90% eligibility coverage (n_k ≥ 100), plus genuine-timestamp evidence for temporal eligibility.
- **Why this ticket exists.** Regime D partition is decided by a first-principles audit (never by external precedent); scientific stages are blocked without a passing feasibility artifact matching source/partition lineage.
- **Authority references.** Arch §12.3 (`FeasibilityGateEvaluator`), §7.5 (90% coverage), §27; Road §7 (feasibility flags), SB-28, §12.9.
- **Dependencies.** P4-T001, P1-T040.
- **Blocks.** P4-T014.
- **Downstream consumers.** P4-T014 consumes the Regime D feasibility artifact and partition decision to unlock scientific pipeline stages.
- **Preconditions.** P4-T001, P1-T040 complete.
- **Inputs.** Arch §12.3 (`FeasibilityGateEvaluator`), §7.5 (90% coverage), §27; Road §7 (feasibility flags), SB-28, §12.9.
- **Allowed scope.** Read-only Edge-IIoTset inspection; feasibility audit; partition-decision record.
- **Forbidden actions.** No scientific training/scoring; no appeal to external precedent; no reuse of a failed/relabeled partition; no pseudo-time.
- **Required configuration or NONE.** Regime D feasibility config.
- **Implementation responsibilities.** Source/schema inspection; eligibility-coverage audit; device-vs-group decision; timestamp-provenance record; feasibility artifact.
- **Required unit tests.** Partition decided by audit, not precedent.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data, synthetic-schema fixture): coverage below 90% blocks; passing evidence unlocks only matching lineage.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Integration (data); unit; feasibility evaluation.
- **Acceptance criteria.** [ ] Source/schema inspected. [ ] Feasibility gated on ≥90% coverage. [ ] Partition decided by first-principles audit. [ ] Timestamp evidence recorded. [ ] No scientific run.
- **Completion evidence.** Changed files (feasibility audit, partition-decision record); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `DatasetError`/`FeasibilityRejection`; GATED/REJECTED status recorded. Stop and reduce K or defer if coverage fails; record the reason.
- **Stop conditions.** Stop and reduce K or defer if coverage fails; record the reason. A reduced/alternate K is a new `ClientPartitionSpec` with a new `PartitionIdentity` and a new feasibility artifact; it never overwrites, retries, or relabels the failed partition's identity or feasibility artifact.
- **Deliverables.** Regime D feasibility artifact + partition decision.
- **Final review checklist.** [ ] Audit-driven, no precedent.

#### P4-T014 — Implement Regime D partitioning, preprocessing, training, and scoring

- **Ticket ID.** P4-T014
- **Title.** Implement Regime D partitioning, preprocessing, training, and scoring
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P2 — Conditional
- **Ticket type.** data
- **Owner.** data-pipeline-engineer
- **Supporting agents.** federated-learning-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-X1
- **Architecture contracts/types owned.** Regime D partition specification, Regime D preprocessing specification, Regime D training specification, Regime D scoring specification
- **Objective.** Implement the Regime D pipeline (approved device/group partition, preprocessing matched per dataset, FedAvg training at the selected global round, calibration/test scoring) with its own identities, validated on synthetic Edge-IIoTset-shaped data.
- **Why this ticket exists.** External validation requires genuinely new Regime-D training/scoring identities behind the passed feasibility gate; input_dim is matched per dataset (fixed-encoder constraint applies within a dataset ladder).
- **Authority references.** Arch §12.3, §16, SB-13; Road §7 (Regime D), §9.2 (E-X1).
- **Dependencies.** P4-T013.
- **Blocks.** P4-T015, P4-T019.
- **Downstream consumers.** P4-T015 and P4-T019 consume the Regime D pipeline and distinct training/scoring identities.
- **Preconditions.** P4-T013 (feasibility passed for implementation validation) complete.
- **Inputs.** Arch §12.3, §16, SB-13; Road §7 (Regime D), §9.2 (E-X1).
- **Allowed scope.** Regime D partition/preprocess/train/score specs and configs.
- **Forbidden actions.** No scientific run on real Edge-IIoTset; no reuse of anchor N-BaIoT identities across datasets; no feasibility-ungated stage; no construction of an alternate K's `ClientPartitionSpec` by overwriting, retrying, or relabeling a prior failed partition's identity (each roadmap-authorized alternate K is its own new `ClientPartitionSpec`, `PartitionIdentity`, and feasibility artifact).
- **Required configuration or NONE.** Regime D scientific config (matched input_dim).
- **Implementation responsibilities.** Approved partition; per-dataset preprocessing; FedAvg training; scoring; distinct Regime-D identities.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (learning/data, synthetic): Regime-D pipeline runs on synthetic data; distinct identities; feasibility-gate enforced.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Integration; synthetic system.
- **Acceptance criteria.** [ ] Regime-D pipeline implemented with distinct identities. [ ] Feasibility-gated. [ ] Matched input_dim. [ ] No real run.
- **Completion evidence.** Changed files (Regime D partition/preprocess/train/score specs and configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `DatasetError`/`TrainingError`/`ScoringError`; feasibility-gate blocking. Stop if feasibility is GATED/REJECTED.
- **Stop conditions.** Stop if feasibility is GATED/REJECTED.
- **Deliverables.** Regime D pipeline.
- **Final review checklist.** [ ] Distinct dataset identities.

#### P4-T015 — Implement E-X1 external validation

- **Ticket ID.** P4-T015
- **Title.** Implement E-X1 external validation
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P2 — Conditional
- **Ticket type.** experiment
- **Owner.** experiment-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-X1
- **Architecture contracts/types owned.** E-X1 experiment specification, Regime-D threshold specification, Regime-D evaluation specification, BCa CI specification
- **Objective.** Implement E-X1: B1–B4 + `B-FedStatsBenign` + q-sensitivity on Edge-IIoTset (Regime D) with CV(FPR) + BCa CI, reporting divergence from Regime A as a boundary; gated on the passed anchor and Regime-D feasibility.
- **Why this ticket exists.** E-X1 is the Tier-3 external-validation claim; it requires both A-gate and D-gate; divergence is reported as a boundary, not confirmation.
- **Authority references.** Arch §22.5 (E-X1 gates); Road §5.3, §9.2 (E-X1), §12.9.
- **Dependencies.** P4-T014, P4-T018.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the E-X1 external validation results and divergence-boundary analysis.
- **Preconditions.** P4-T014, P4-T018 complete.
- **Inputs.** Arch §22.5 (E-X1 gates); Road §5.3, §9.2 (E-X1), §12.9.
- **Allowed scope.** E-X1 specs/configs (Regime D ladder + comparator + q).
- **Forbidden actions.** No confirmatory promotion; no journal execution; no external run before readiness.
- **Required configuration or NONE.** E-X1 config (A-gate + D-gate).
- **Implementation responsibilities.** Regime-D ladder + FedStats + q; BCa CI; divergence-boundary wording.
- **Required unit tests.** Divergence reported as boundary.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system: E-X1 on synthetic Regime-D data; gates enforced.
- **Validation commands.** Synthetic system; unit.
- **Acceptance criteria.** [ ] Regime-D ladder + FedStats + q + BCa. [ ] A-gate and D-gate enforced. [ ] Divergence as boundary. [ ] No journal execution.
- **Completion evidence.** Changed files (E-X1 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** Feasibility/anchor gate blocking; report mixed/null as boundary. Stop if D-gate fails (defer/reduce K).
- **Stop conditions.** Stop if D-gate fails (defer/reduce K).
- **Deliverables.** E-X1 implementation.
- **Final review checklist.** [ ] Tier-3, gated.

#### P4-T016 — Implement E-T1 FedProx aggregation stress test

- **Ticket ID.** P4-T016
- **Title.** Implement E-T1 FedProx aggregation stress test
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** federated-learning-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-T1
- **Architecture contracts/types owned.** `FedProxTrainingSpec`, `FedProxCheckpointIdentity`, `FedProxScoreIdentity`, `FedProxMuGridConfig`
- **Objective.** Implement E-T1: FedProx × B1–B4 with a strictly-positive frozen pre-registered µ-grid, matched to the FedAvg profile on all non-strategy settings, with separate training/checkpoint/score identities; CV(FPR) delta vs FedAvg; convergence failure reported non-retroactively.
- **Why this ticket exists.** E-T1 is a Tier-4 stress test outside the causal ladder; µ is never from FedAvg or confirmatory outcomes; no post-hoc µ search.
- **Authority references.** Arch §9.1 (FedProx µ rules), §25 (add training strategy), §29.4 (74); Road §5.4, §9.2 (E-T1), §12.8, SB-25.
- **Dependencies.** P4-T001, P1-T044.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the FedProx training/checkpoint/score identities and CV(FPR) delta results from this ticket.
- **Preconditions.** P4-T001, P1-T044 complete.
- **Inputs.** Arch §9.1, §25, §29.4; Road §5.4, §9.2, §12.8; SB-25.
- **Allowed scope.** E-T1 specs/configs (frozen µ-grid).
- **Forbidden actions.** No core-ladder presentation; no µ from FedAvg/confirmatory; no post-hoc µ; no journal execution.
- **Required configuration or NONE.** E-T1 pre-registered µ-grid.
- **Implementation responsibilities.** FedProx cells with frozen µ-grid; distinct identities; delta-vs-FedAvg diagnostic; convergence reporting.
- **Required unit tests.** µ strictly positive/frozen; not from confirmatory outcomes.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** CUDA lane synthetic: FedProx matches non-strategy settings; distinct identities.
- **Required CUDA tests.** CUDA lane synthetic FedProx training.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** CUDA lane; unit; synthetic system.
- **Acceptance criteria.** [ ] FedProx × B1–B4 with frozen µ-grid. [ ] Distinct identities, matched non-strategy settings. [ ] No post-hoc µ. [ ] Outside the ladder.
- **Completion evidence.** Changed files (E-T1 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `TrainingError`; convergence failure reported, no post-hoc µ. Stop if the µ-grid is not pre-registered; carry as a readiness blocker.
- **Stop conditions.** Stop if the µ-grid is not pre-registered; carry as a readiness blocker.
- **Deliverables.** E-T1 implementation.
- **Final review checklist.** [ ] Stress, not ladder.

#### P4-T017 — Implement E-T2 model-personalization stress test and absorption bands

- **Ticket ID.** P4-T017
- **Title.** Implement E-T2 model-personalization stress test and absorption bands
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** federated-learning-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-T2
- **Architecture contracts/types owned.** `PersonalizationModelSpec`, `PersonalizationCheckpointIdentity`, `PersonalizationScoreIdentity`, `AbsorptionRatioSpec`, `AbsorptionBandConfig`
- **Objective.** Implement E-T2: one model-personalization comparator (faithful Ditto, or a `FedRep-AE`/`FedPer-AE` fallback correctly labeled) × B1–B4, the absorption ratio Δ_pers/Δ_FedAvg, and the four pre-specified absorption bands applied without adjustment, with distinct model/checkpoint/score identities.
- **Why this ticket exists.** E-T2 is the strongest reviewer objection (Tier 4); the fallback is never labeled "Ditto" unless true Ditto is implemented; absorption bands are pre-specified.
- **Authority references.** Arch §6.1 (personalization naming lock), §9.3 (absorption bands); Road §5.4, §8 (2×2 reconciliation), §9.3 (bands), SB-24.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the personalization model/checkpoint/score identities and absorption band results from this ticket.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §6.1, §9.3; Road §5.4, §8, §9.3; SB-24.
- **Allowed scope.** E-T2 specs/configs (personalization comparator + absorption).
- **Forbidden actions.** No mislabeling a fallback as Ditto; no band adjustment; no core-ladder presentation; no journal execution.
- **Required configuration or NONE.** E-T2 comparator/hyperparameter config (documented pre-training decision).
- **Implementation responsibilities.** Personalization comparator with distinct identities; absorption ratio; four bands applied as-is.
- **Required unit tests.** Absorption bands applied without adjustment; fallback not labeled Ditto.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** CUDA lane synthetic: distinct personalization identities; correct labeling.
- **Required CUDA tests.** CUDA lane synthetic personalization training.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** CUDA lane; unit; synthetic system.
- **Acceptance criteria.** [ ] One personalization comparator × B1–B4, distinct identities. [ ] Correct labeling (no false Ditto). [ ] Four bands applied as-is. [ ] Outside the ladder.
- **Completion evidence.** Changed files (E-T2 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `TrainingError`; report all four bands honestly. Stop if the comparator/hyperparameters are undecided; carry as a readiness blocker.
- **Stop conditions.** Stop if the comparator/hyperparameters are undecided; carry as a readiness blocker.
- **Deliverables.** E-T2 implementation.
- **Final review checklist.** [ ] Naming lock honored.

#### P4-T018 — Implement E-T3 B-FedStatsBenign matched comparator

- **Ticket ID.** P4-T018
- **Title.** Implement E-T3 B-FedStatsBenign matched comparator
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** threshold-policy-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-T3
- **Architecture contracts/types owned.** `B-FedStatsBenign`, `FedStatsVarianceSpec`, `MatchedExceedanceConfig`, `BetweenRatioResult`
- **Objective.** Implement E-T3: `B-FedStatsBenign` (benign-only client messages n_k/µ_k/σ_k², full pooled variance with between-term, weighted global mean, matched-exceedance operating point on the candidate grid, larger-k tie), reporting within/between terms and between_ratio, reusing compatible calibration scores; fixed-k variants are supplementary only.
- **Why this ticket exists.** E-T3 (Tier 4 comparator) answers the Laridi novelty objection with a benign-only matched-exceedance comparator; the locked contract cannot be disabled by any boolean; between_ratio > 0.5 is disclosed.
- **Authority references.** Arch §9.2 (FedStats locked contract), §29.4 (9); Road §4, §17 (locked contract), SB-22/SB-26/SB-27.
- **Dependencies.** P4-T001, P1-T025.
- **Blocks.** P4-T015, P4-T022.
- **Downstream consumers.** P4-T015 and P4-T022 consume the FedStats comparator threshold identity and matched-exceedance results from this ticket.
- **Preconditions.** P4-T001, P1-T025 complete.
- **Inputs.** Arch §9.2, §29.4; Road §4, §17; SB-22/SB-26/SB-27.
- **Allowed scope.** E-T3 specs/configs (matched-exceedance comparator).
- **Forbidden actions.** No simple pooled variance; no configurable tie; no fixed-k as primary; no post-hoc protocol tuning; no journal execution.
- **Required configuration or NONE.** E-T3 candidate grid; fixed-k variants supplementary.
- **Implementation responsibilities.** FedStats algorithm over compatible calibration scores; within/between/between_ratio reporting; matched-exceedance selection; larger-k tie.
- **Required unit tests.** Full variance + larger-k tie; fixed-k supplementary only; between_ratio reported.
- **Required property tests.** Matched-exceedance selection.
- **Required contract tests.** Pooled-variance/tie.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; property; contract lanes.
- **Acceptance criteria.** [ ] Full pooled variance + between-term. [ ] Matched-exceedance, larger-k tie. [ ] Fixed-k supplementary only. [ ] Reuse compatible calibration scores.
- **Completion evidence.** Changed files (E-T3 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** `ThresholdError`; disclose between_ratio > 0.5. Stop if the matched-exceedance k-grid step is unresolved; carry as a readiness blocker.
- **Stop conditions.** Stop if the matched-exceedance k-grid step is unresolved; carry as a readiness blocker.
- **Deliverables.** E-T3 implementation.
- **Final review checklist.** [ ] Locked contract, no toggle.

#### P4-T019 — Implement E-B1 temporal recalibration MVE

- **Ticket ID.** P4-T019
- **Title.** Implement E-B1 temporal recalibration MVE
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P2 — Conditional
- **Ticket type.** experiment
- **Owner.** experiment-engineer
- **Supporting agents.** data-pipeline-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-B1
- **Architecture contracts/types owned.** `TemporalWindowSpec`, `TemporalBoundary`, `OneShotRecalibrationSpec`, `TemporalOutcome`
- **Objective.** Implement E-B1: Edge-IIoTset chronological 70/30 split (genuine timestamps), early-window training/benign-only calibration, late-window evaluation, frozen vs one-shot recalibration, per-window CV(FPR) and recovery ratio, mapped to one of the three pre-specified temporal outcomes.
- **Why this ticket exists.** E-B1 (Tier 6) is the temporal recalibration MVE; it requires real timestamps and rejects file/row/merge/folder/synthetic pseudo-time; one locked outcome is applied.
- **Authority references.** Arch §7.5 (temporal locks), §9.1 (temporal specs); Road §11 (three outcomes), §11.1, SB-08.
- **Dependencies.** P4-T014, P4-T024.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the temporal window/score/eval identities and recovery ratio results from this ticket.
- **Preconditions.** P4-T014 (Regime D feasible + genuine timestamps) complete; P4-T024 (chronological temporal training/calibration allocation) resolved.
- **Inputs.** Arch §7.5, §9.1; Road §11, §11.1; SB-08.
- **Allowed scope.** E-B1 temporal specs/configs.
- **Forbidden actions.** No pseudo-time; no sliding/periodic recalibration; no retroactive drift detector; no journal execution.
- **Required configuration or NONE.** E-B1 temporal config (70/30 locked; genuine timestamp field).
- **Implementation responsibilities.** Chronological 70/30; frozen vs one-shot; recovery ratio; outcome mapping.
- **Required unit tests.** 70/30 canonical; pseudo-time rejected; one outcome applied.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Integration (data): chronological split on synthetic timestamps.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Unit; integration (data); synthetic system.
- **Acceptance criteria.** [ ] Chronological 70/30 with genuine timestamps. [ ] Frozen vs one-shot. [ ] One pre-specified outcome applied. [ ] No pseudo-time.
- **Completion evidence.** Changed files (E-B1 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** Suppression when timestamp semantics fail (`TEMPORAL_REJECTED_NO_TIMESTAMPS`). Stop if genuine timestamps are unavailable; suppress with the temporal rejection record.
- **Stop conditions.** Stop if genuine timestamps are unavailable; suppress with the temporal rejection record.
- **Deliverables.** E-B1 implementation.
- **Final review checklist.** [ ] Genuine time only.

#### P4-T020 — Implement mandatory E-O1 alert burden evidence and suppression route

- **Ticket ID.** P4-T020
- **Title.** Implement mandatory E-O1 alert burden evidence and suppression route
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** experiment
- **Owner.** experiment-engineer
- **Supporting agents.** statistics-auditor, threshold-policy-engineer
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-O1
- **Architecture contracts/types owned.** `TrafficRateEvidenceKind`, `CostDerivationKind`, `AlertBurdenSpec`, `ResourceCostSpec`
- **Objective.** Implement mandatory E-O1 alert burden with `TrafficRateEvidenceKind`, `CostDerivationKind`, unit normalization, provenance, and alert/device/day calculation. If no valid measured or cited rate exists, produce a documented feasibility rejection or suppression result; never present estimated traffic as measured. P4-T023 separately owns E-Q1–E-Q6.
- **Why this ticket exists.** E-O1 (Tier 5, mandatory) is a supportive analysis that must not present hypothetical alert rates as measurements; resource-cost estimates are labeled, never presented as measured traffic.
- **Authority references.** Arch §9.3 (alert burden/resource cost), §6.1 (traffic evidence); Road §9.2 (mandatory supportive), §10, §13 (L20/L21), SB-20.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T026.
- **Downstream consumers.** P4-T026 consumes the alert burden evidence and suppression results from this ticket.
- **Preconditions.** P4-T001 complete.
- **Inputs.** Arch §9.3, §6.1; Road §9.2, §10, §13; SB-20.
- **Allowed scope.** E-O1 spec/config.
- **Forbidden actions.** No hypothetical alert rate as measurement; no cost estimate rendered as measured; no journal execution; no E-Q1–E-Q6 content (owned separately by P4-T023).
- **Required configuration or NONE.** E-O1 traffic evidence configuration.
- **Implementation responsibilities.** Alert-burden with evidence gate; communication/storage resource cost with `MEASURED`/`ESTIMATED` labels.
- **Required unit tests.** Alert burden requires evidence; cost estimates labeled.
- **Required property tests.** NONE.
- **Required contract tests.** Resource-cost provenance closes.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Synthetic system.
- **Validation commands.** Unit; contract; synthetic system.
- **Acceptance criteria.** [ ] Alert burden evidence-gated (omit if absent). [ ] Cost estimates labeled, never measured. [ ] No E-Q1–E-Q6 content in this ticket.
- **Completion evidence.** Changed files (E-O1 specs/configs); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** Alert-burden config fails without evidence; `MEASURED`/`ESTIMATED` labels enforced. Omit alert burden if no real/cited rate exists.
- **Stop conditions.** Omit alert burden if no real/cited rate exists.
- **Deliverables.** E-O1 implementation.
- **Final review checklist.** [ ] Mandatory supportive analysis, not primary; E-Q1–E-Q6 owned separately by P4-T023.

#### P4-T021 — Implement claim tiers, fallback wording, and report schemas/renderers

- **Ticket ID.** P4-T021
- **Title.** Implement claim tiers, fallback wording, and report schemas/renderers
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** claim-evidence-auditor, reviewer2-red-team
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ClaimTier`, `ClaimOutcome`, `ReportRenderer`, `ReportIdentity`, table/figure/export specifications
- **Objective.** Implement the claim-tier machinery (nine tiers; only confirmatory at Tier 1), the `ClaimOutcome`-driven fallback wording for every major claim (strong/weak/mixed/null/opposite/feasibility/suppressed), and the report schemas/renderers (tables/figures/exports: Markdown/LaTeX/CSV/Parquet/SVG/PNG/PDF) needed by the journal campaign — no HARKing, no overclaiming, no result suppression.
- **Why this ticket exists.** The claim/report layer enforces claim discipline and honest wording; null/mixed results are reportable; suppression evidence is documented.
- **Authority references.** Arch §22, §6.6; Road §5, §12 (fallback wording), §13 (reviewer register), §14.4.
- **Dependencies.** P4-T001, P1-T049.
- **Blocks.** P4-T022.
- **Downstream consumers.** P4-T022 consumes the claim/wording/report specifications and renderer outputs for inventory completeness audit.
- **Preconditions.** P4-T001, P1-T049 complete.
- **Inputs.** Arch §22, §6.6; Road §5, §12, §13, §14.4.
- **Allowed scope.** Claim-tier/wording/report specs and renderer wiring.
- **Forbidden actions.** No confirmatory promotion of a supportive module; no HARKing/overclaiming; no result suppression; no journal execution.
- **Required configuration or NONE.** Reporting config (tables/figures/formats/wording outcomes).
- **Implementation responsibilities.** Claim-tier mapping; per-outcome wording selection; table/figure/export schemas; renderers consuming traced specs.
- **Required unit tests.** Wording per `ClaimOutcome`; only confirmatory at Tier 1; export formats.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Renderer output per format; no value altered; manifest/table shapes (fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; integration (reporting); golden lanes.
- **Acceptance criteria.** [ ] Nine tiers; only confirmatory at Tier 1. [ ] Fallback wording for every major claim. [ ] All export formats render faithfully. [ ] No suppression/overclaiming.
- **Completion evidence.** Changed files (claim/wording/report specs, renderers, configs); commands run and results; report identity recorded; cleanup confirmation.
- **Failure and blocker behavior.** `ProvenanceError` on untraced output; `ReportingError` on render failure.
- **Stop conditions.** None.
- **Deliverables.** Claim/wording/report layer.
- **Final review checklist.** [ ] Honest wording enforced.

#### P4-T022 — Implement journal expected-artifact/table/figure inventory and completeness audit

- **Ticket ID.** P4-T022
- **Title.** Implement journal expected-artifact/table/figure inventory and completeness audit
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** report-output-auditor, experiment-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `JournalInventory`, `CompletenessAudit`, `ExpectedArtifactSpec`, `TraceabilityMatrix`
- **Objective.** Produce the journal expected-artifact/table/figure/export inventory and the implementation-completeness audit certifying every roadmap experiment ID has specification/config/identity/tests/expected-artifacts/output coverage, with no journal real run performed. This is an inventory input to the Phase 4 gate.
- **Why this ticket exists.** Phase 5 planning depends on a complete, audited implementation; this gate proves every mandatory/optional/rejected experiment is represented.
- **Authority references.** Arch §22.5 (traceability matrix), §26; Road §9; this backlog §F (Phase 4 gate).
- **Dependencies.** P4-T002, P4-T003, P4-T004, P4-T005, P4-T006, P4-T007, P4-T008, P4-T009, P4-T010, P4-T011, P4-T012, P4-T013, P4-T014, P4-T015, P4-T016, P4-T017, P4-T018, P4-T019, P4-T020, P4-T021.
- **Blocks.** P4-T026.
- **Downstream consumers.** P4-T026 (the Phase 4 gate) consumes the journal inventory and completeness audit to verify readiness for Phase 5 planning.
- **Preconditions.** all P4 implementation tickets complete.
- **Inputs.** Arch §22.5, §26; Road §9; backlog §F.
- **Allowed scope.** Inventory enumeration; completeness auditing.
- **Forbidden actions.** No journal execution; no missing experiment ID; no supportive-to-confirmatory promotion.
- **Required configuration or NONE.** None beyond the implemented configs.
- **Implementation responsibilities.** Enumerate expected artifacts/tables/figures/exports; map each roadmap ID to its implementation and outputs; record the audit.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Every roadmap ID present with coverage; rejected IDs non-executable.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** All implemented experiments run on synthetic data; inventory shape (fixed-input regression check).
- **Validation commands.** Architecture; synthetic system; golden lanes.
- **Acceptance criteria.** [ ] Every roadmap ID has full coverage. [ ] Expected artifact/table/figure/export inventory complete. [ ] No journal real run. [ ] Audit recorded.
- **Completion evidence.** Changed files/records (inventory, audit); commands run and results; recorded identities; cleanup confirmation.
- **Failure and blocker behavior.** A missing experiment/output blocks the gate. Stop if any mandatory experiment ID lacks coverage.
- **Stop conditions.** Stop if any mandatory experiment ID lacks coverage.
- **Deliverables.** Journal inventory + completeness audit.
- **Final review checklist.** [ ] Complete on synthetic data only.

> **Relocated in an earlier revision; full-template-normalized and cross-checked in this revision.** The four tickets below (P4-T023–P4-T026) originally existed only in Section F and were moved here so that Section G's index rows have a corresponding body. All four use the mandatory 38-field template. The E-O1/E-Q separation is now resolved: `P4-T020` (E-O1, mandatory) no longer carries E-Q-scoped content, and Section K.1's `E-Q1`–`E-Q6` rows now correctly cite `P4-T023` (not `P4-T020`) as their implementing ticket. The Phase 7 originality-before-closure ordering was independently audited and confirmed already correct (`P7-T012` is a precondition of `P7-T011` in both Section G and Section H).

#### P4-T023 — Record optional E-Q1–E-Q6 selections and implement selected supplements

- **Ticket ID.** P4-T023
- **Title.** Record optional E-Q1–E-Q6 selections and implement selected supplements
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P3-Optional
- **Ticket type.** experiment
- **Owner.** roadmap-orchestrator
- **Supporting agents.** statistics-auditor or —
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-Q1,E-Q2,E-Q3,E-Q4,E-Q5,E-Q6
- **Architecture contracts/types owned.** `ExperimentProfileSpec`, `PreSpecificationRecord`, `ScientificStageGateDecision`
- **Objective.** Record an authority-grounded terminal selection decision for every E-Q experiment and implement only selected work.
- **Why this ticket exists.** Optional supplements are not mandatory E-O1 work.
- **Authority references.** Road §9.3; Arch §8.3, §9.5.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T026, P5-T002.
- **Downstream consumers.** P5-T002, P6-T002, P7-T008.
- **Preconditions.** Frozen optional-selection rationale.
- **Inputs.** Authority and pre-specification record.
- **Allowed scope.** Synthetic implementation and decision recording.
- **Forbidden actions.** No unselected execution; no silent omission.
- **Required configuration or NONE.** Selected E-Q configuration or `NONE`.
- **Implementation responsibilities.** Support `DONE`, `NOT_APPLICABLE` with selection decision, or `REJECTED` with authority-grounded reason for each E-Q ID.
- **Required unit tests.** Decision-state validation.
- **Required property tests.** NONE.
- **Required contract tests.** Invalid optional terminal state rejection.
- **Required architecture tests.** NONE.
- **Required integration tests.** Selected-profile dry run.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Decision validation and selected-profile dry run.
- **Acceptance criteria.** [ ] Every E-Q has a valid terminal decision. [ ] Only selected experiments proceed.
- **Completion evidence.** Decision records, changed files, commands/tests/results, selected identity list, cleanup, blockers, skipped checks, no unrelated changes.
- **Failure and blocker behavior.** Missing decision blocks P4-T026.
- **Stop conditions.** Authority-grounded selection absent.
- **Deliverables.** Optional-experiment decision register.
- **Final review checklist.** [ ] Optional is not silently dropped.

#### P4-T024 — Resolve chronological temporal training/calibration allocation

- **Ticket ID.** P4-T024
- **Title.** Resolve chronological temporal training/calibration allocation
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** feasibility
- **Owner.** datp-protocol-guardian
- **Supporting agents.** data-pipeline-engineer, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-B1
- **Architecture contracts/types owned.** `TemporalProtocolSpec`, `TemporalWindowSpec`, `OneShotRecalibrationSpec`, `FeasibilityGateDecision`, `BlockedStage`
- **Objective.** Recover or decide the chronological allocation within the first 70% between AE training and benign threshold calibration.
- **Why this ticket exists.** The authorities lock a 70/30 split but do not authorize an invented allocation.
- **Authority references.** Road §11; Arch §27.
- **Dependencies.** P4-T001.
- **Blocks.** P4-T019,P5-T004,P6-T004,P7-T008.
- **Downstream consumers.** Temporal implementation, feasibility, execution, and final audit.
- **Preconditions.** Timestamp and row-order evidence available.
- **Inputs.** Authority evidence, timestamp semantics, client records.
- **Allowed scope.** Evidence recovery or explicit design decision only.
- **Forbidden actions.** No default allocation, pseudo-time, leakage, or temporal execution while unresolved.
- **Required configuration or NONE.** `TemporalProtocolSpec` only after authority resolution.
- **Implementation responsibilities.** Specify allocation, row ordering, equal-timestamp handling, leakage prevention, insufficient-client behavior, preprocessing fit scope, and one-shot recalibration interaction.
- **Required unit tests.** NONE until decision exists.
- **Required property tests.** NONE until decision exists.
- **Required contract tests.** Decision completeness.
- **Required architecture tests.** Typed blocked-stage propagation.
- **Required integration tests.** NONE until decision exists.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Evidence and decision completeness inspection.
- **Acceptance criteria.** [ ] Every allocation semantic is evidenced or explicitly blocked. [ ] All temporal consumers depend on this ticket.
- **Completion evidence.** Evidence/decision record, dependency proof, commands, cleanup, blockers, skipped checks, no unrelated changes.
- **Failure and blocker behavior.** Remain `BLOCKED_BY_UNRESOLVED_IDENTITY`; temporal branch cannot pass.
- **Stop conditions.** Missing authority evidence.
- **Deliverables.** Temporal allocation decision or blocker.
- **Final review checklist.** [ ] No invented temporal allocation.

#### P4-T025 — Produce Appendix A B2 calibration-versus-held-out FPR analysis

- **Ticket ID.** P4-T025
- **Title.** Produce Appendix A B2 calibration-versus-held-out FPR analysis
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P1-Mandatory
- **Ticket type.** reporting
- **Owner.** statistics-auditor
- **Supporting agents.** claim-evidence-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-C1,E-V1,E-V2,E-V3
- **Architecture contracts/types owned.** `DispersionLadderTableSpec`, `TableProvenance`, `FigureProvenance`, `ResultFreezeManifest`, `EffectSizeEvidence`
- **Objective.** Produce mandatory Appendix A explaining why local empirical quantile calibration does not guarantee equal held-out FPR.
- **Why this ticket exists.** It closes the B2-by-construction reviewer loophole without claiming new theory.
- **Authority references.** Road §13, §14; Arch §22.
- **Dependencies.** P4-T001,P4-T008,P4-T009,P4-T010.
- **Blocks.** P4-T026,P7-T011.
- **Downstream consumers.** P5-T006,P6-T009,P7-T011.
- **Preconditions.** Locked report terminology.
- **Inputs.** Calibration/test identities and B2-conf/E-V1/shrinkage specifications.
- **Allowed scope.** Analytical/report specification only.
- **Forbidden actions.** No claim of new statistical theory.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Cover finite-sample quantile error, calibration size, shift, benign heterogeneity, attack separability, assumptions, limitations, failure cases, B2-conf, E-V1, shrinkage, and absolute dispersion.
- **Required unit tests.** Report schema completeness.
- **Required property tests.** NONE.
- **Required contract tests.** Traceability to cited experiments.
- **Required architecture tests.** NONE.
- **Required integration tests.** Frozen-report dry run.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Report traceability inspection.
- **Acceptance criteria.** [ ] Required analytical distinctions and limitations appear. [ ] Reviewer loophole closure is traceable.
- **Completion evidence.** Report spec, traceability records, commands/tests/results, cleanup, blockers, skipped checks, no unrelated changes.
- **Failure and blocker behavior.** Missing required topic blocks P4-T026.
- **Stop conditions.** Unsupported theoretical claim.
- **Deliverables.** Appendix A specification and output inventory entry.
- **Final review checklist.** [ ] No tautological B2 claim.

#### P4-T026 — Complete journal implementation audit and phase gate

- **Ticket ID.** P4-T026
- **Title.** Complete journal implementation audit and phase gate
- **Phase.** 4
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** datp-protocol-guardian, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `ScientificStageGateDecision`, `FeasibilityCatalogSnapshot`
- **Objective.** Verify mandatory implementation and each conditional/optional terminal state before Phase 5.
- **Why this ticket exists.** A phase gate cannot treat unresolved, skipped, or `NOT_STARTED` tickets as complete.
- **Authority references.** Road §14; Arch §14, §27.
- **Dependencies.** P4-T022,P4-T023,P4-T024,P4-T025.
- **Blocks.** P5-T001.
- **Downstream consumers.** P5-T001.
- **Preconditions.** All P4 tickets terminal under their required status semantics.
- **Inputs.** Completion evidence, decision records, matrices, inventories.
- **Allowed scope.** Audit only.
- **Forbidden actions.** No journal execution or blocker bypass.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Enforce mandatory `DONE`, conditional valid feasibility terminal states, optional valid selection states, and blocker propagation.
- **Required unit tests.** Gate-state validation.
- **Required property tests.** NONE.
- **Required contract tests.** Ticket dependency completeness.
- **Required architecture tests.** NONE.
- **Required integration tests.** Synthetic phase-gate test.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Matrix and gate validation.
- **Acceptance criteria.** [ ] No unresolved required P4 ticket. [ ] Temporal blocker prevents selected temporal work.
- **Completion evidence.** Gate decision, validation outputs, cleanup, blockers, skipped checks, no unrelated changes.
- **Failure and blocker behavior.** Fail closed.
- **Stop conditions.** Any invalid terminal state.
- **Deliverables.** P4 phase-gate decision.
- **Final review checklist.** [ ] Safe Phase 5 unlock.

### Phase 5 — Journal Campaign Planning and Readiness

> **Phase-wide note (applies to every P5 ticket).** No journal scientific execution occurs. Work is matrix expansion, feasibility resolution, reuse/invalidation verification, resource/storage estimation, execution-staging validation, and freezing. Sci-exec is `PLANNING_ONLY`; campaign scope is `JOURNAL`. Observed scientific results never alter campaign design; seed orderings are never inferred; families are not forced to share seed specs unless the roadmap requires it. "Completion evidence" is the standard five-heading report plus resulting frozen identities.

#### P5-T001 — Implementation-completeness and anchor-artifact-compatibility audit

- **Ticket ID.** P5-T001
- **Title.** Implementation-completeness and anchor-artifact-compatibility audit
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** reproducibility-auditor
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ReuseIncompatibilityError` (compatibility classification only).
- **Objective.** Confirm journal implementation is complete and that frozen anchor artifacts are lineage-compatible with the journal cells that intend to reuse them (checkpoint/calibration/test score identities), rejecting any incompatible reuse.
- **Why this ticket exists.** Journal reuse is only valid when the complete scientific/technical identity is compatible; incompatible reuse must recompute, not be silently accepted. This audit carries no new identity impact of its own.
- **Authority references.** Arch §13.3, §29.1; Road §14.2 (reuse checklist).
- **Dependencies.** P4-T026, P3-T011.
- **Blocks.** P5-T002.
- **Downstream consumers.** P5-T002 consumes this ticket's compatibility audit output.
- **Preconditions.** P4-T026, P3-T011.
- **Inputs.** Frozen anchor artifacts (checkpoint/calibration/test score identities); journal implementation-completeness evidence.
- **Allowed scope.** Read-only compatibility audit.
- **Forbidden actions.** No execution; no reuse without proven lineage compatibility; no config change.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify implementation completeness; verify anchor-artifact compatibility per intended reuse; flag incompatibilities as RECOMPUTE.
- **Required unit tests.** Compatible reuse accepted; incompatible reuse recomputed.
- **Required property tests.** NONE.
- **Required contract tests.** Compatible reuse accepted; incompatible reuse recomputed.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Lineage tracing; compatibility audit.
- **Acceptance criteria.** [ ] Implementation complete. [ ] Anchor compatibility verified per reuse. [ ] Incompatibilities classified RECOMPUTE. [ ] No execution.
- **Completion evidence.** Compatibility audit record; commands and tests run with results; RECOMPUTE classifications listed with reasons; no execution performed; no unrelated modifications.
- **Failure and blocker behavior.** Emit `ReuseIncompatibilityError` and classify as RECOMPUTE rather than accepting incompatible reuse.
- **Stop conditions.** Stop if implementation is incomplete (return to Phase 4).
- **Deliverables.** Compatibility audit record.
- **Final review checklist.** [ ] Lineage-proven reuse only.

#### P5-T002 — Configuration expansion and journal experiment-cell enumeration

- **Ticket ID.** P5-T002
- **Title.** Configuration expansion and journal experiment-cell enumeration
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** experiment-engineer
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `ExperimentCell` (journal cell identity enumeration); `AmbiguousPlanError`; `CyclicPlanError`.
- **Objective.** Expand the journal configuration into the complete resolved experiment matrix and enumerate every journal `ExperimentCell` deterministically.
- **Why this ticket exists.** The journal campaign executes a resolved matrix; deterministic enumeration is the basis for identity/reuse/resource planning, and this enumeration establishes the journal cell identities.
- **Authority references.** Arch §14; Road §9.
- **Dependencies.** P5-T001, P1-T038.
- **Blocks.** P5-T003.
- **Downstream consumers.** P5-T003 consumes the journal cell enumeration.
- **Preconditions.** P5-T001, P1-T038.
- **Inputs.** Journal configuration; resolved-experiment-matrix planner; P1-T038 outputs.
- **Allowed scope.** Matrix expansion; cell enumeration.
- **Forbidden actions.** No execution; no inferred seed ordering; no observed-result-driven design.
- **Required configuration or NONE.** NONE (expands the existing frozen journal configuration; no new configuration introduced).
- **Implementation responsibilities.** Expand all journal cells via the planner; record the enumeration.
- **Required unit tests.** Deterministic enumeration.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Golden: matrix shape (named fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Dry-run planning; unit; golden.
- **Acceptance criteria.** [ ] Complete resolved journal matrix. [ ] Deterministic enumeration. [ ] No seed-order inference. [ ] No execution.
- **Completion evidence.** Journal cell enumeration output; commands and tests run with results; deterministic matrix confirmed; no execution performed; no unrelated modifications.
- **Failure and blocker behavior.** Emit `AmbiguousPlanError` or `CyclicPlanError` rather than resolving ambiguity by inference.
- **Stop conditions.** None.
- **Deliverables.** Journal cell enumeration.
- **Final review checklist.** [ ] Deterministic matrix.

#### P5-T003 — Cell-ID uniqueness and stage-identity enumeration

- **Ticket ID.** P5-T003
- **Title.** Cell-ID uniqueness and stage-identity enumeration
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `CellId`; `AmbiguousPlanError`; unique training, checkpoint-selection, calibration-score, test-score, threshold, evaluation, and statistical stage-identity inventory.
- **Objective.** Verify cell-ID uniqueness (no collision between distinct resolved cells) and enumerate the unique training, checkpoint-selection, calibration-score, test-score, threshold, evaluation, and statistical identities, with threshold fan-out from shared score identities.
- **Why this ticket exists.** Expensive identities must be enumerated to plan reuse and resources; a `CellId` collision is an `AmbiguousPlanError`. This ticket enumerates all journal stage identities.
- **Authority references.** Arch §13.1–13.3, §14.3, §29.4 (66).
- **Dependencies.** P5-T002.
- **Blocks.** P5-T004.
- **Downstream consumers.** P5-T004 consumes the cell-ID uniqueness and stage-identity inventory.
- **Preconditions.** P5-T002.
- **Inputs.** Journal cell enumeration (P5-T002); shared score identities.
- **Allowed scope.** Identity enumeration; collision check.
- **Forbidden actions.** No execution; no blanket "exactly once" wording.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Enumerate unique identities per stage; verify collision-free cell IDs; record threshold fan-out from shared scores.
- **Required unit tests.** Collision-free; threshold fan-out from shared scores.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Golden: identity inventory (named fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Dry-run planning; unit; golden.
- **Acceptance criteria.** [ ] Cell IDs unique. [ ] Unique stage identities enumerated. [ ] Threshold fan-out from shared scores. [ ] No execution.
- **Completion evidence.** Stage-identity inventory and cell-ID collision-check results; commands and tests run with results; no execution performed; no unrelated modifications.
- **Failure and blocker behavior.** Emit `AmbiguousPlanError` on any cell-ID collision rather than allowing duplicate identities.
- **Stop conditions.** Stop on any cell-ID collision.
- **Deliverables.** Journal stage-identity inventory.
- **Final review checklist.** [ ] Collision-free.

#### P5-T004 — Feasibility-gate resolution, suppression cells, and unresolved-cell blocking

- **Ticket ID.** P5-T004
- **Title.** Feasibility-gate resolution, suppression cells, and unresolved-cell blocking
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** feasibility
- **Owner.** experiment-engineer
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-X1, E-B1, B-a
- **Architecture contracts/types owned.** `FeasibilityRejection`; `BlockingReason`; suppression-cell records.
- **Objective.** Resolve every feasibility gate (Regime D coverage, timestamp availability, CICIoT2023 feature count), create suppression cells for infeasible experiments, and block any unresolved cell from the plan. Each Regime-D partition candidate (including any roadmap-authorized alternate K) receives its own distinct suppression cell and feasibility-artifact identity; no candidate's record is shared, mutated, or overwritten by a later candidate's evaluation.
- **Why this ticket exists.** Scientific stages cannot enter the plan without resolved feasibility; infeasible experiments become documented suppression outcomes, not silent omissions.
- **Authority references.** Arch §12.3 (feasibility gate), §27; Road §7, §9.4, §12.9/§12.10.
- **Dependencies.** P5-T003, P4-T013, P4-T024.
- **Blocks.** P5-T005.
- **Downstream consumers.** P5-T005 consumes the feasibility resolutions and suppression cells.
- **Preconditions.** P5-T003, P4-T013, P4-T024.
- **Inputs.** Cell-ID/stage-identity inventory (P5-T003); Regime D coverage data; timestamp availability data; CICIoT2023 feature-count data (P4-T013, P4-T024 outputs).
- **Allowed scope.** Feasibility resolution; suppression-cell creation; unresolved-cell blocking.
- **Forbidden actions.** No execution; no unresolved cell in the plan; no relabeled failed feasibility.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Resolve gates; create suppression records; block unresolved cells with typed reasons.
- **Required unit tests.** Infeasible → suppression cell; unresolved → blocked; passing → unlocks matching lineage only; each alternate K candidate for the same experiment produces its own distinct suppression cell / feasibility-artifact identity, never a shared or mutated per-experiment record.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Feasibility evaluation; unit.
- **Acceptance criteria.** [ ] All feasibility gates resolved. [ ] Suppression cells created. [ ] Unresolved cells blocked. [ ] No relabeled feasibility.
- **Completion evidence.** Feasibility resolutions and suppression-cell records; commands and tests run with results; unresolved-cell blocking confirmed; no execution performed; no unrelated modifications.
- **Failure and blocker behavior.** Emit typed `FeasibilityRejection`/`BlockingReason` and block the unresolved cell rather than relabeling failed feasibility.
- **Stop conditions.** Stop if a mandatory cell is unresolved.
- **Deliverables.** Feasibility resolutions + suppression cells.
- **Final review checklist.** [ ] No unresolved cell planned.

#### P5-T005 — Reuse and invalidation verification against frozen anchor artifacts

- **Ticket ID.** P5-T005
- **Title.** Reuse and invalidation verification against frozen anchor artifacts
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** FORBIDDEN
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** Reuse ledger with `REUSABLE_FROM_COMPATIBLE_ANCHOR`, `REQUIRES_NEW_JOURNAL_COMPUTATION`, `BLOCKED_BY_UNRESOLVED_IDENTITY` classifications (a planning-level, journal-reuse-ledger-specific elaboration of the architecture's `ReuseDecisionKind` enum — `REUSE`/`RECOMPUTE`/`BLOCKED` respectively; this ledger vocabulary is not itself a class defined in `docs/DATP Core Architecture.md` and is used consistently across P5-T001, this ticket, and P6-T002); `ReuseIncompatibilityError`.
- **Objective.** Compare the frozen anchor lineage with the complete journal matrix and classify **every** journal training, checkpoint, calibration-score, and test-score identity as exactly `REUSABLE_FROM_COMPATIBLE_ANCHOR`, `REQUIRES_NEW_JOURNAL_COMPUTATION`, or `BLOCKED_BY_UNRESOLVED_IDENTITY`; enumerate the additional journal Regime-A identities required to complete the ten-seed E-C1 cohort. Reuse is lineage-proven, never filename-based.
- **Why this ticket exists.** Correct reuse/invalidation is essential to avoid retraining/rescoring for threshold-only changes and to recompute when identity-bearing inputs change; this ticket produces the reuse ledger.
- **Authority references.** Arch §11.5, §13.3, §29.1; this backlog §B (reuse language).
- **Dependencies.** P5-T003, P1-T033.
- **Blocks.** P5-T006.
- **Downstream consumers.** P5-T006 consumes the reuse/invalidation ledger.
- **Preconditions.** P5-T003, P1-T033.
- **Inputs.** Frozen anchor lineage; complete journal matrix (P5-T003); P1-T033 outputs.
- **Allowed scope.** Reuse/invalidation verification; reuse-ledger production.
- **Forbidden actions.** No execution; no filename-based reuse; no "exactly once" wording.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Compute the three-way classification per identity via the typed spec-diff and reuse gate; record full lineage comparison inputs and the reuse ledger; enumerate all missing Regime-A model, checkpoint-selection, calibration-score, and test-score identities for E-C1 before Phase 6.
- **Required unit tests.** Threshold-only change reuses scores; identity-bearing change requires new journal computation; incomplete lineage blocks; reuse ledger is exhaustive and correct.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Reuse classification; unit.
- **Acceptance criteria.** [ ] Every journal identity receives exactly one required classification. [ ] Complete lineage evidence is recorded. [ ] Missing ten-seed Regime-A identities are enumerated. [ ] Threshold-only reuses scores. [ ] Identity-bearing changes require new journal computation. [ ] Lineage-proven, not filename/path/seed-position based.
- **Completion evidence.** Reuse/invalidation ledger; commands and tests run with results; missing ten-seed Regime-A identities enumerated; no execution performed; no unrelated modifications.
- **Failure and blocker behavior.** Emit `ReuseIncompatibilityError` → `REQUIRES_NEW_JOURNAL_COMPUTATION`; classify missing/ambiguous evidence as `BLOCKED_BY_UNRESOLVED_IDENTITY` rather than inferring compatibility.
- **Stop conditions.** Block any journal cell with unresolved identity evidence; do not infer compatibility.
- **Deliverables.** Reuse/invalidation ledger.
- **Final review checklist.** [ ] Lineage-aware reuse.

#### P5-T006 — Expected-artifact/table/figure/export inventory and experiment-to-claim/output mapping

- **Ticket ID.** P5-T006
- **Title.** Expected-artifact/table/figure/export inventory and experiment-to-claim/output mapping
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** claim-evidence-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** Expected-output inventory records (artifact/table/figure/export) and the experiment-to-claim/output mapping; `ProvenanceError`.
- **Objective.** Produce the complete expected-artifact, expected-table, expected-figure, and expected-export inventories and map each experiment to its claim tier and its planned outputs.
- **Why this ticket exists.** Phase 7 provenance closure requires a pre-declared output inventory; each experiment's claim tier and outputs must be traceable.
- **Authority references.** Arch §22; Road §5, §14.4.
- **Dependencies.** P5-T003.
- **Blocks.** P5-T007.
- **Downstream consumers.** P5-T007 consumes the output inventory and experiment-to-claim/output mapping.
- **Preconditions.** P5-T003.
- **Inputs.** P5-T003 stage-identity enumeration; the resolved journal experiment matrix; each experiment's claim tier and planned outputs.
- **Allowed scope.** Output inventory; experiment-to-claim/output mapping.
- **Forbidden actions.** No execution; no unmapped experiment; no confirmatory promotion.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Enumerate expected outputs; map experiments to tiers/outputs.
- **Required unit tests.** Every experiment is mapped to a tier and outputs.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A named fixed-input regression check (golden) verifying the inventory shape.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Unit; golden.
- **Acceptance criteria.** [ ] Expected artifact/table/figure/export inventories complete. [ ] Experiment→claim/output mapping complete. [ ] No unmapped experiment. [ ] No execution.
- **Completion evidence.** Changed files; produced expected-artifact/table/figure/export inventories and experiment-to-claim/output mapping; commands and tests run with results; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Emit `ProvenanceError` rather than accepting an untraceable planned output; do not promote an unmapped experiment.
- **Stop conditions.** None.
- **Deliverables.** Output inventory + mapping.
- **Final review checklist.** [ ] Every output pre-declared.

#### P5-T007 — Resource/storage estimation and worker/CUDA/process/resume-boundary planning

- **Ticket ID.** P5-T007
- **Title.** Resource/storage estimation and worker/CUDA/process/resume-boundary planning
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** implementation-engineer
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ExecutionCostEstimate` (advisory); `ResourceBudgetExceededError`; `UnsafeParallelismError`; worker/CUDA/process/resume-boundary plan.
- **Objective.** Produce advisory resource/storage estimates for the resolved journal matrix and plan worker allocation, CUDA scheduling (one GPU job at a time), process isolation (spawn for CUDA stages), and resume boundaries — all non-scientific and never altering identities.
- **Why this ticket exists.** Expensive execution must be resourced and staged; estimates are advisory and never unlock a stage or change a resolved spec.
- **Authority references.** Arch §9.4 (advisory estimate), §16.4, §16.6; this backlog §B.
- **Dependencies.** P5-T005, P5-T006.
- **Blocks.** P5-T008.
- **Downstream consumers.** P5-T008 consumes the resource/storage estimates and worker/CUDA/process/resume-boundary staging plan.
- **Preconditions.** P5-T005, P5-T006.
- **Inputs.** P5-T005 reuse/invalidation ledger; P5-T006 output inventory; the resolved journal experiment matrix.
- **Allowed scope.** Estimation and staging planning.
- **Forbidden actions.** No execution; no estimate altering identity/reuse; no concurrent GPU jobs.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Produce an advisory `ExecutionCostEstimate`; produce a worker/CUDA/process/resume-boundary plan.
- **Required unit tests.** Estimates are advisory and never unlock a stage; no concurrent GPU scheduling is planned.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Estimation; plan-time validation.
- **Acceptance criteria.** [ ] Resource/storage estimates produced (advisory). [ ] Worker/CUDA/process/resume plan produced. [ ] No concurrent GPU job. [ ] Estimates never alter identity.
- **Completion evidence.** Changed files; produced advisory `ExecutionCostEstimate` and worker/CUDA/process/resume-boundary plan; commands and tests run with results; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Emit `ResourceBudgetExceededError` or `UnsafeParallelismError` at plan time rather than proceeding with an unsafe or over-budget plan; never let an advisory estimate unlock a stage or alter identity.
- **Stop conditions.** Stop if the resolved matrix exceeds hard resource limits; record a blocker.
- **Deliverables.** Estimates + staging plan.
- **Final review checklist.** [ ] Advisory only.

#### P5-T008 — Clean-worktree check and freeze of code/dependency/environment/config/campaign identity

- **Ticket ID.** P5-T008
- **Title.** Clean-worktree check and freeze of code/dependency/environment/config/campaign identity
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** roadmap-orchestrator
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** Frozen pre-execution baseline record (code-state, dependency-lock, environment inventory, resolved journal configuration) and the frozen journal campaign `RunIdentity`.
- **Objective.** Verify a clean worktree and freeze code-state, dependency-lock, environment inventory, resolved journal configuration, and the journal campaign identity into an immutable pre-execution baseline.
- **Why this ticket exists.** The journal campaign must launch from a clean, frozen, reproducible state under an immutable scientific configuration.
- **Authority references.** Arch §9.5, §22.4; this backlog §B, §E.
- **Dependencies.** P5-T004, P5-T007, P0-T004.
- **Blocks.** P5-T009.
- **Downstream consumers.** P5-T009 consumes the frozen pre-execution baseline.
- **Preconditions.** P5-T004, P5-T007, P0-T004.
- **Inputs.** P5-T004 feasibility resolutions; P5-T007 resource/staging plan; P0-T004 dependency-lock; current worktree state.
- **Allowed scope.** Clean-worktree check; provenance/config freeze; campaign-identity freeze.
- **Forbidden actions.** No execution; no freeze on a dirty tree; no scientific config change after freeze; no versioning work.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify clean worktree; capture/freeze provenance and resolved config; freeze campaign `RunIdentity`.
- **Required unit tests.** Frozen config is identity-stable; pinned libraries are recorded.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A named fixed-input regression check (golden) verifying the campaign-manifest shape.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Full Nox validation; provenance capture; git status.
- **Acceptance criteria.** [ ] Clean worktree. [ ] Code/dependency/environment/config frozen. [ ] Campaign identity frozen. [ ] No versioning work.
- **Completion evidence.** Changed files; clean-worktree verification result; frozen code-state, dependency-lock, environment inventory, resolved journal configuration, and frozen journal campaign `RunIdentity`; commands and tests run with results; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Block the freeze on a dirty worktree or missing provenance rather than freezing an unverified state.
- **Stop conditions.** Stop if the worktree is dirty or any suite fails.
- **Deliverables.** Frozen journal pre-execution baseline.
- **Final review checklist.** [ ] Immutable baseline.

#### P5-T009 — Journal campaign manifest and final go/no-go decision

- **Ticket ID.** P5-T009
- **Title.** Journal campaign manifest and final go/no-go decision
- **Phase.** 5
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** roadmap-orchestrator
- **Supporting agents.** reviewer2-red-team, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** The frozen journal campaign manifest (binding frozen `RunIdentity`, resolved config, matrix, reuse ledger, feasibility resolutions, output inventory, staging plan) and the recorded go/no-go decision record.
- **Objective.** Assemble the journal campaign manifest (frozen config, matrix, identities, reuse ledger, feasibility resolutions, output inventory, staging plan) and record a formal go/no-go decision. **This is the Phase 5 go/no-go gate.**
- **Why this ticket exists.** Expensive journal execution begins only after a formal, recorded go decision from the frozen plan.
- **Authority references.** Arch §14, §26; Road §20 (go/no-go); this backlog §F (Phase 5 gate).
- **Dependencies.** P5-T008.
- **Blocks.** P6-T001.
- **Downstream consumers.** P6-T001 consumes the journal campaign manifest and go/no-go decision.
- **Preconditions.** P5-T008.
- **Inputs.** P5-T008 frozen pre-execution baseline (code, dependency, environment, config, campaign identity).
- **Allowed scope.** Manifest assembly; go/no-go decision.
- **Forbidden actions.** No execution; no go without a complete frozen plan; no observed-result-driven change.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Bind all frozen artifacts into the campaign manifest; record the go/no-go verdict with rationale.
- **Required unit tests.** The manifest binds all frozen artifacts.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** A named fixed-input regression check (golden) verifying the manifest shape.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Manifest assembly; unit; golden.
- **Acceptance criteria.** [ ] Campaign manifest complete. [ ] Go/no-go decision recorded with rationale. [ ] No execution. [ ] No design change from observed results.
- **Completion evidence.** Changed files; assembled journal campaign manifest; recorded go/no-go decision and rationale; commands and tests run with results; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Record a no-go verdict and block Phase 6 rather than proceeding without a complete frozen plan.
- **Stop conditions.** Record no-go and block Phase 6 if any input is unfrozen or unresolved.
- **Deliverables.** Journal campaign manifest + go/no-go verdict.
- **Final review checklist.** [ ] Go decision recorded.

### Phase 6 — Journal Campaign

> **Phase-wide note (applies to every P6 ticket).** This phase contains the journal scientific campaign. Only tickets classified `JOURNAL_CAMPAIGN_ALLOWED` perform real training/scoring; others are `PLANNING_ONLY`. The stages below are internal campaign stages / resumable work units / dependency partitions of one frozen journal plan — not independent mini-campaigns. Nothing is described as "executed exactly once": execute when the resolved graph requires, reuse only when lineage compatibility passes, skip completed compatible stages on resume, recompute invalidated stages, and preserve execution-attempt/provenance records. A scientific configuration change creates a new campaign identity. Campaign scope is `JOURNAL`. "Completion evidence" is the standard five-heading report plus campaign/attempt identities.

#### P6-T001 — Final readiness confirmation and journal execution-attempt creation

- **Ticket ID.** P6-T001
- **Title.** Final readiness confirmation and journal execution-attempt creation
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** roadmap-orchestrator
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `ExecutionAttemptId`
- **Objective.** Confirm the go decision, clean worktree, and frozen manifest, and create the initial journal `ExecutionAttemptId` under the frozen journal `RunIdentity`.
- **Why this ticket exists.** Execution begins under a coherent, recorded attempt identity bound to the frozen campaign identity.
- **Authority references.** Arch §7, §18; this backlog §B.
- **Dependencies.** P5-T009.
- **Blocks.** P6-T002.
- **Downstream consumers.** P6-T002 consumes the initial journal `ExecutionAttemptId`.
- **Preconditions.** P5-T009 (go).
- **Inputs.** Go decision, clean worktree state, frozen manifest, frozen journal `RunIdentity`.
- **Allowed scope.** Readiness confirmation; attempt-identity creation.
- **Forbidden actions.** No scientific config change; no execution before attempt creation.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify go/clean/frozen; mint the initial attempt id.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: attempt id bound to frozen `RunIdentity`.
- **Validation commands.** Readiness confirmation; manifest inspection.
- **Acceptance criteria.** [ ] Go/clean/frozen confirmed. [ ] Initial attempt id minted. [ ] `RunIdentity` unchanged. [ ] No config drift.
- **Completion evidence.** Confirmed go/clean/frozen state; minted attempt id; validation command results; no config drift confirmation.
- **Failure and blocker behavior.** Reject any post-freeze config drift.
- **Stop conditions.** Stop if not go or worktree dirty.
- **Deliverables.** Journal execution-attempt identity.
- **Final review checklist.** [ ] Bound to frozen identity.

#### P6-T002 — Journal Regime-A identity completion, reuse validation, and threshold-only execution

- **Ticket ID.** P6-T002
- **Title.** Journal Regime-A identity completion, reuse validation, and threshold-only execution
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** threshold-policy-engineer
- **Supporting agents.** artifact-lineage-auditor, federated-learning-engineer
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-C1, E-S1, E-S2, E-V1, E-V2, E-V3, E-T3, E-M1, E-M2, E-M3, E-M4, E-M5, B0, B-a, E-Q1, E-Q2, E-Q3, E-Q4, E-Q5, E-Q6
- **Architecture contracts/types owned.** Journal Regime-A training/checkpoint/calibration-score/test-score/threshold/evaluation identities.
- **Objective.** Classify every journal Regime-A training, checkpoint-selection, calibration-score, and test-score identity as `REUSABLE_FROM_COMPATIBLE_ANCHOR`, `REQUIRES_NEW_JOURNAL_COMPUTATION`, or `BLOCKED_BY_UNRESOLVED_IDENTITY`; execute every required new journal identity before threshold-only work; then execute E-C1's complete ten-paired-seed B1-vs-B2 threshold/evaluation/statistics input path and the selected threshold-only Regime-A/B-a/optional cells.
- **Why this ticket exists.** The journal ten-seed confirmatory cohort cannot depend on a five-seed or scientifically distinct anchor campaign. Reuse is full typed-lineage compatibility only; missing journal identities must be computed under `JOURNAL_EXTENSION` even when an anchor artifact is read-only reusable.
- **Authority references.** Arch §13.3, §29.1; Road §20 (immediate-start extensions); this backlog §B.
- **Dependencies.** P6-T001.
- **Blocks.** P6-T006.
- **Downstream consumers.** P6-T006 consumes the journal Regime-A reuse ledger and executed artifacts.
- **Preconditions.** P6-T001.
- **Inputs.** Anchor campaign identities/artifacts, frozen journal plan, per-identity lineage evidence.
- **Allowed scope.** Journal Regime-A identity classification/computation and threshold-only execution over compatible scores; B0's separate centralized branch; B-a boundary execution when selected; selected E-Q cells.
- **Forbidden actions.** No filename/path/seed-position/"first five" reuse; no reuse without proven lineage; no retraining or rescoring for a genuinely threshold-only change; no anchor namespace writes; no config change.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Produce a per-identity reuse ledger; execute all `REQUIRES_NEW_JOURNAL_COMPUTATION` Regime-A training, checkpoint selection, calibration scoring, and test scoring identities; execute E-C1 B1/B2 across the complete ten paired seeds with per-seed deltas as statistics inputs; execute threshold constructions/evaluations for E-S1/E-S2/E-V1/E-V2/E-V3/E-T3/E-M1–E-M5, B0, B-a, and selected E-Q cells; persist each artifact atomically in the journal namespace.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: complete ten-seed E-C1 cohort; every reuse decision has complete lineage evidence; non-reusable journal identities train/select/score in the journal namespace; threshold-only stages reuse compatible scores without retrain/rescore; B0 never uses a FedAvg identity; lineage closes.
- **Validation commands.** Execution under the frozen plan; lineage tracing.
- **Acceptance criteria.** [ ] Every journal Regime-A identity has exactly one of the three required classifications. [ ] All required new journal training/checkpoint/calibration-score/test-score identities executed. [ ] Complete ten-seed E-C1 B1/B2 evaluation/statistics input path present. [ ] Threshold-only stages reuse only compatible scores. [ ] Atomic commits with closed lineage and namespace separation. [ ] No config change.
- **Completion evidence.** Per-identity reuse ledger; executed new/reused artifacts; validation command results; lineage closure confirmation.
- **Failure and blocker behavior.** `ReuseIncompatibilityError` → `REQUIRES_NEW_JOURNAL_COMPUTATION`; absent identity evidence → `BLOCKED_BY_UNRESOLVED_IDENTITY`; typed stage failures are persisted and may use only the technical-invalidity correction path.
- **Stop conditions.** Persist failure evidence on any typed failure; recompute only on invalidation; block unresolved identity rather than assume overlap.
- **Deliverables.** Journal Regime-A reuse ledger plus new and reused artifacts.
- **Final review checklist.** [ ] No anchor shortcut; no retrain for threshold-only changes.

#### P6-T003 — Regime C execution

- **Ticket ID.** P6-T003
- **Title.** Regime C execution
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** campaign
- **Owner.** data-pipeline-engineer
- **Supporting agents.** federated-learning-engineer
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-S3
- **Architecture contracts/types owned.** Regime-C training/score/eval identities.
- **Objective.** Execute the Regime C Dirichlet severity program (E-S3) with its own partition/training/scoring/evaluation identities under the frozen plan.
- **Why this ticket exists.** Regime C requires genuinely new training/scoring identities (not anchor reuse); it is executed as an internal campaign stage.
- **Authority references.** Arch §14; Road §7, §9.2 (E-S3); this backlog §B.
- **Dependencies.** P6-T001.
- **Blocks.** P6-T006.
- **Downstream consumers.** P6-T006 consumes the Regime C artifacts.
- **Preconditions.** P6-T001.
- **Inputs.** Frozen plan, Regime C partition specification.
- **Allowed scope.** Regime C execution.
- **Forbidden actions.** No anchor-identity reuse across regimes; no config change; no "exactly once" wording.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Execute Regime C cells; persist artifacts atomically.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: distinct Regime-C identities; artifacts complete.
- **Validation commands.** Execution; artifact inspection.
- **Acceptance criteria.** [ ] Regime C executed with distinct identities. [ ] Artifacts complete/atomic. [ ] No anchor-identity reuse. [ ] No config change.
- **Completion evidence.** Regime C artifacts; validation command results; identity distinctness confirmation.
- **Failure and blocker behavior.** Typed failures persisted; recompute on invalidation.
- **Stop conditions.** Persist failure evidence on any typed failure.
- **Deliverables.** Regime C artifacts.
- **Final review checklist.** [ ] Distinct identities.

#### P6-T004 — Accepted Regime D execution (external + temporal)

- **Ticket ID.** P6-T004
- **Title.** Accepted Regime D execution (external + temporal)
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P2 — Conditional
- **Ticket type.** campaign
- **Owner.** data-pipeline-engineer
- **Supporting agents.** experiment-engineer
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-X1, E-B1
- **Architecture contracts/types owned.** Regime-D external/temporal identities.
- **Objective.** Execute the accepted Regime D external-validation (E-X1) and, if feasible, temporal (E-B1) programs behind the passed anchor and Regime-D feasibility gates.
- **Why this ticket exists.** Regime D science requires exact-lineage feasibility; temporal execution requires genuine timestamps; both proceed only when accepted.
- **Authority references.** Arch §12.3, §22.5 (gates); Road §7, §11, §12.9; this backlog §B.
- **Dependencies.** P6-T001, P5-T004.
- **Blocks.** P6-T006.
- **Downstream consumers.** P6-T006 consumes the Regime D external/temporal artifacts.
- **Preconditions.** P6-T001, P5-T004 (feasibility resolved/accepted).
- **Inputs.** Passed anchor gate, Regime-D feasibility gate result, `ClientPartitionSpec`.
- **Allowed scope.** Regime D external/temporal execution behind gates.
- **Forbidden actions.** No execution if feasibility is GATED/REJECTED; no pseudo-time; no config change.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Execute E-X1 (and E-B1 if feasible); persist artifacts atomically.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: gate enforcement; artifacts complete.
- **Validation commands.** Execution; feasibility verification.
- **Acceptance criteria.** [ ] E-X1 executed behind A-gate + D-gate. [ ] E-B1 executed only if timestamp-feasible, else suppressed. [ ] Artifacts complete/atomic. [ ] No pseudo-time.
- **Completion evidence.** Regime D external/temporal artifacts; validation command results; gate enforcement confirmation.
- **Failure and blocker behavior.** Feasibility-gate blocking; suppression on failed temporal semantics.
- **Stop conditions.** Preserve the failed partition and feasibility artifact immutably. A different, roadmap-authorized K is a new `ClientPartitionSpec`, new partition identity, and new feasibility artifact; it never overwrites, retries, or relabels the failed partition. Suppress the unresolved branch when no authorized candidate passes.
- **Deliverables.** Regime D external/temporal artifacts.
- **Final review checklist.** [ ] Gated execution.

#### P6-T005 — FedProx and model-personalization stress-test execution

- **Ticket ID.** P6-T005
- **Title.** FedProx and model-personalization stress-test execution
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P1 — Mandatory
- **Ticket type.** campaign
- **Owner.** federated-learning-engineer
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** E-T1, E-T2
- **Architecture contracts/types owned.** Distinct stress-test training/checkpoint/score identities.
- **Objective.** Execute the FedProx (E-T1, frozen µ-grid) and model-personalization (E-T2) stress tests with distinct training/checkpoint/score identities, outside the causal ladder; report convergence failures and absorption bands without post-hoc adjustment.
- **Why this ticket exists.** Stress tests carry separate identities and never share the ladder's control; µ and comparator choices are frozen/pre-decided; all outcomes are reportable.
- **Authority references.** Arch §9.1, §29.4 (74); Road §5.4, §9.2 (E-T1/E-T2), §12.7/§12.8; this backlog §B.
- **Dependencies.** P6-T001.
- **Blocks.** P6-T006.
- **Downstream consumers.** P6-T006 consumes the stress-test artifacts.
- **Preconditions.** P6-T001.
- **Inputs.** Frozen µ-grid, frozen comparator choices.
- **Allowed scope.** Stress-test execution with distinct identities.
- **Forbidden actions.** No core-ladder presentation; no post-hoc µ; no band adjustment; no config change.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Execute E-T1/E-T2 cells; compute absorption bands as-is; persist artifacts atomically.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: distinct identities; bands applied as-is; convergence reported.
- **Validation commands.** Execution; artifact inspection.
- **Acceptance criteria.** [ ] E-T1/E-T2 executed with distinct identities. [ ] Bands applied without adjustment. [ ] Convergence reported non-retroactively. [ ] Outside the ladder.
- **Completion evidence.** Stress-test artifacts; validation command results; separation confirmation.
- **Failure and blocker behavior.** Persist failure evidence on any typed failure; no post-hoc µ.
- **Stop conditions.** Persist failure evidence on any typed failure; no post-hoc µ.
- **Deliverables.** Stress-test artifacts.
- **Final review checklist.** [ ] Separation preserved.

#### P6-T006 — Statistics execution, typed-failure and invalidated-artifact handling

- **Ticket ID.** P6-T006
- **Title.** Statistics execution, typed-failure and invalidated-artifact handling
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** statistics
- **Owner.** statistics-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `StatisticsError`; typed degeneracy records over journal statistics.
- **Objective.** Execute the journal statistical analyses over completed evaluations (BCa CIs, descriptive tests, absorption/temporal-recovery diagnostics), persist typed degeneracy, and recompute any invalidated-upstream statistic.
- **Why this ticket exists.** Statistics run over completed, lineage-valid evaluations; degeneracy is typed; invalidated upstreams recompute rather than reuse.
- **Authority references.** Arch §9.3, §16.5; Road §10; this backlog §B.
- **Dependencies.** P6-T002, P6-T003, P6-T004, P6-T005.
- **Blocks.** P6-T008.
- **Downstream consumers.** P6-T008 consumes P6-T006's journal statistical results and typed degeneracy records.
- **Preconditions.** P6-T002, P6-T003, P6-T004, P6-T005.
- **Inputs.** Completed, lineage-valid journal evaluations from P6-T002, P6-T003, P6-T004, P6-T005.
- **Allowed scope.** Statistical execution over completed evaluations.
- **Forbidden actions.** No silent BCa→percentile; no reuse of invalidated statistics; no confirmatory promotion.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Compute statistics per experiment; persist typed degeneracy; recompute invalidated.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: statistics computed from completed evaluations; degeneracy typed; invalidated recomputed.
- **Validation commands.** Statistical analysis; lineage tracing.
- **Acceptance criteria.** [ ] Journal statistics computed. [ ] Degeneracy typed. [ ] Invalidated statistics recomputed. [ ] No confirmatory promotion.
- **Completion evidence.** Changed files; commands run and results; journal statistical results and typed degeneracy records; cleanup confirmation.
- **Failure and blocker behavior.** `StatisticsError` for unexpected failures only; degeneracy is typed rather than silently dropped.
- **Stop conditions.** Persist failure evidence on any unexpected statistical failure.
- **Deliverables.** Journal statistical results.
- **Final review checklist.** [ ] Typed, lineage-valid.

#### P6-T007 — Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits

- **Ticket ID.** P6-T007
- **Title.** Conditional journal recovery, resume, infrastructure retry, and immutable artifact commits
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** campaign
- **Owner.** reproducibility-auditor
- **Supporting agents.** roadmap-orchestrator
- **Scientific-execution classification.** **JOURNAL_CAMPAIGN_ALLOWED**
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `RecoveryStateMismatchError`, `ResumeIncompatibilityError`.
- **Objective.** Handle journal campaign resume (skip completed compatible stages, compatible recovery only), classified infrastructure retries, and immutable artifact commits, recording new execution-attempt identities while preserving the scientific `RunIdentity`.
- **Why this ticket exists.** Resume/retry preserve scientific identity; artifacts commit immutably; failed-attempt evidence is preserved.
- **Authority references.** Arch §16.6–16.7, §17.3, §18; this backlog §B.
- **Dependencies.** P6-T001.
- **Blocks.** P6-T008.
- **Downstream consumers.** P6-T008 consumes P6-T007's resume/retry/commit records and attempt-identity evidence.
- **Preconditions.** P6-T001 creates the execution attempt and execution has begun; recovery activates only after interruption, transient infrastructure failure, or a compatible committed recovery state.
- **Inputs.** Execution attempt created by P6-T001; committed recovery state (when present); infrastructure-failure classification.
- **Allowed scope.** Resume/retry/commit orchestration.
- **Forbidden actions.** No auto OOM recovery; no resume under a changed profile; no scientific-identity change; no retry of scientific/determinism failure.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Skip completed compatible stages; validate recovery; continue the same execution-attempt identity for a graceful-pressure-boundary resume (safe unit finishes and commits, then resumes within the same attempt, per Arch §17.3); mint a new attempt id only for resume after an interruption or transient-failure recovery (not a graceful-pressure boundary); commit artifacts immutably.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: uninterrupted-vs-resumed equivalence; immutable commits; attempt ids recorded.
- **Validation commands.** Resume execution; lineage tracing.
- **Acceptance criteria.** [ ] Completed compatible stages skipped. [ ] Only compatible recovery used. [ ] Immutable commits. [ ] New attempt ids recorded; `RunIdentity` unchanged. [ ] Mark `NOT_APPLICABLE` with uninterrupted-completion evidence when no recovery condition occurs.
- **Completion evidence.** Changed files; commands run and results; new attempt-identity records; `RunIdentity` continuity evidence; cleanup confirmation.
- **Failure and blocker behavior.** `RecoveryStateMismatchError`/`ResumeIncompatibilityError` raised on incompatible recovery/resume; only bounded transient retry is permitted for infrastructure failure.
- **Stop conditions.** Mark `NOT_APPLICABLE` when execution completes uninterrupted. Start a new run under new identities if the profile changed.
- **Deliverables.** Resume/retry/commit records.
- **Final review checklist.** [ ] Resume ≠ new campaign.

#### P6-T008 — Complete-cell/statistics/output audits and result freeze

- **Ticket ID.** P6-T008
- **Title.** Complete-cell/statistics/output audits and result freeze
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** statistics-auditor, reproducibility-auditor
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** Immutable journal result manifests (frozen result-manifest artifacts).
- **Objective.** Audit that every resolved cell, statistic, and planned output is complete and lineage-valid, then freeze the complete journal results into immutable result manifests.
- **Why this ticket exists.** Journal acceptance requires complete, lineage-valid results; freezing produces the immutable evidence package for Phase 7.
- **Authority references.** Arch §13, §22 (result freeze); this backlog §B, §E.
- **Dependencies.** P6-T006; P6-T007 when activated.
- **Blocks.** P6-T009.
- **Downstream consumers.** P6-T009 consumes P6-T008's frozen journal result manifests.
- **Preconditions.** Valid uninterrupted execution evidence, or valid execution evidence plus activated P6-T007 recovery/retry evidence.
- **Inputs.** Journal statistics from P6-T006; resume/retry/commit evidence from P6-T007 when activated.
- **Allowed scope.** Completeness auditing; result freeze.
- **Forbidden actions.** No execution; no incomplete result accepted; no unfrozen result to Phase 7.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify complete cells/statistics/outputs; freeze result manifests.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: all cells/statistics/outputs complete; frozen manifests immutable.
- **Validation commands.** Completeness audit; result freeze; lineage tracing.
- **Acceptance criteria.** [ ] All cells/statistics/outputs complete. [ ] Results frozen/immutable. [ ] No incomplete accepted. [ ] No execution.
- **Completion evidence.** Changed files; commands run and results; frozen result-manifest identities; cleanup confirmation.
- **Failure and blocker behavior.** Incomplete or invalid-lineage results are flagged for recompute/rerun rather than frozen.
- **Stop conditions.** Stop and route incomplete results to recompute/rerun.
- **Deliverables.** Frozen journal result manifests.
- **Final review checklist.** [ ] Complete and frozen.

#### P6-T009 — Report rendering, journal integrity/outcome decision, technical-invalidity correction path

- **Ticket ID.** P6-T009
- **Title.** Report rendering, journal integrity/outcome decision, technical-invalidity correction path
- **Phase.** 6
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** reporting
- **Owner.** roadmap-orchestrator
- **Supporting agents.** report-output-auditor, reviewer2-red-team
- **Scientific-execution classification.** PLANNING_ONLY
- **Campaign scope.** JOURNAL
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** `CAMPAIGN_INTEGRITY_STATUS`, `SCIENTIFIC_OUTCOME_STATUS`, `ProvenanceError`.
- **Objective.** Render the planned outputs from frozen results (provenance-closed), record separate `CAMPAIGN_INTEGRITY_STATUS` and `SCIENTIFIC_OUTCOME_STATUS`, and define the technical-invalidity correction path (root cause → corrective ticket → tests/regression → new attempt identity → preserved evidence → approval). **This is the Phase 6 acceptance gate.**
- **Why this ticket exists.** Outputs render only from frozen, traced results. A null, mixed, non-significant, opposite-direction, or otherwise unfavorable scientific outcome remains valid evidence and is not a rerun trigger.
- **Authority references.** Arch §22.2 (tracing), §22.4; Road §12 (fallback wording); this backlog §B, §F (Phase 6 gate).
- **Dependencies.** P6-T008.
- **Blocks.** P7-T001.
- **Downstream consumers.** P7-T001 consumes P6-T009's rendered outputs and integrity/outcome decision.
- **Preconditions.** P6-T008.
- **Inputs.** Frozen journal result manifests from P6-T008.
- **Allowed scope.** Rendering; integrity/outcome decision; technical-invalidity correction path.
- **Forbidden actions.** No render before freeze/provenance closure; no suppression; no result-seeking rerun; no correction without the §B record and diagnosed technical invalidity.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Render planned outputs; record both statuses with evidence; freeze and map every integrity-valid result to roadmap fallback wording; route only diagnosed technical invalidity to corrective work.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: outputs render only from frozen/traced results; acceptance recorded with evidence.
- **Validation commands.** Rendering; provenance closure; changelog record.
- **Acceptance criteria.** [ ] Outputs rendered from frozen/traced results. [ ] Integrity and outcome recorded separately. [ ] Valid unfavorable evidence retained with fallback wording. [ ] Technical-invalidity correction path defined per §B. [ ] No suppression or result-seeking rerun.
- **Completion evidence.** Changed files; commands run and results; rendered outputs; integrity/outcome decision records; cleanup confirmation.
- **Failure and blocker behavior.** `ProvenanceError` on an untraced output. A valid weak, null, mixed, unfavorable, or opposite-direction result is frozen, reported with its pre-specified fallback wording, and never causes rerun. Only diagnosed technical invalidity may trigger a compatible recovery, affected-stage recomputation, or a new execution attempt.
- **Stop conditions.** Route only diagnosed technical invalidity to corrective work; valid unfavorable evidence proceeds to Phase 7.
- **Deliverables.** Rendered outputs + integrity/outcome decision + technical-invalidity correction path.
- **Final review checklist.** [ ] Traced rendering only.

### Phase 7 — Final Result Freeze, Reporting, and Audit

> **Phase-wide note (applies to every P7 ticket).** No new unplanned scientific experiment is introduced. Work verifies frozen results, lineage, invariants, and statistics, regenerates outputs from frozen artifacts, and conducts harsh reviewer audits. Sci-exec is `POST_CAMPAIGN_ONLY` (regeneration/verification over frozen artifacts). Campaign scope is `POST_CAMPAIGN`. No result is suppressed; no claim is strengthened beyond its evidence. "Completion evidence" is the standard five-heading report plus audit verdicts.

#### P7-T001 — Immutable-result and artifact-hash verification; manifest completeness

- **Ticket ID.** P7-T001
- **Title.** Immutable-result and artifact-hash verification; manifest completeness
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** reproducibility-auditor
- **Supporting agents.** artifact-lineage-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Verify every frozen result is immutable and hash-consistent (content hashes match, no logical id with mismatched bytes) and that all result/experiment manifests are complete.
- **Why this ticket exists.** Provenance and reproducibility depend on immutable, hash-verified frozen artifacts and complete manifests.
- **Authority references.** Arch §13.5, §22, §29.4 (65); this backlog §E.
- **Dependencies.** P6-T009.
- **Blocks.** P7-T002.
- **Downstream consumers.** P7-T002 consumes the integrity/manifest verification record.
- **Preconditions.** P6-T009.
- **Inputs.** Frozen result artifacts, content hashes, and result/experiment manifests produced under P6-T009.
- **Allowed scope.** Hash/manifest verification over frozen artifacts.
- **Forbidden actions.** No new experiment; no artifact mutation; no re-minting of a mismatched id.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Recompute and compare content hashes; verify manifest completeness.
- **Required unit tests.** Hash consistency check; manifest completeness check.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Golden fixed-input regression check on manifest shapes.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: hash consistency; manifest completeness.
- **Validation commands.** Artifact verification; manifest inspection.
- **Acceptance criteria.** [ ] All frozen results hash-consistent. [ ] No mismatched logical id. [ ] Manifests complete. [ ] No mutation.
- **Completion evidence.** Commands and tests run with results; integrity/manifest verification record; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Surface `ArtifactError`/integrity conflict explicitly; never silently resolve a mismatch.
- **Stop conditions.** Stop on any integrity conflict.
- **Deliverables.** Integrity/manifest verification record.
- **Final review checklist.** [ ] Immutable and hash-verified.

#### P7-T002 — Lineage closure and provenance verification

- **Ticket ID.** P7-T002
- **Title.** Lineage closure and provenance verification
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Independently verify lineage closure for the anchor cohort and the journal cohort; verify every cross-track reuse decision, code-state, configuration, dependency-lock, environment provenance, campaign identity, execution identity, seed identity, and output root. Prove that no anchor/journal result mixing occurred.
- **Why this ticket exists.** Every reported output must trace to resolved configuration; provenance must be complete and namespace-correct.
- **Authority references.** Arch §13, §22.2, §22.5, §9.5.
- **Dependencies.** P7-T001.
- **Blocks.** P7-T009.
- **Downstream consumers.** P7-T009 consumes the provenance-closure record.
- **Preconditions.** P7-T001.
- **Inputs.** Anchor and journal cohort results; cross-track reuse ledger entries; code-state, configuration, dependency-lock, and environment provenance records; campaign/execution/seed identities; output roots.
- **Allowed scope.** Provenance-closure verification.
- **Forbidden actions.** No new experiment; no untraced output tolerated.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Trace each track's results to its own resolved configuration and root; compare each reuse ledger entry against complete typed lineage; verify anchor and journal campaign/seed/output identities are separate; record any accidental mixed lineage as invalid.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: full lineage closure; provenance completeness; namespace separation.
- **Validation commands.** Lineage tracing; provenance inspection.
- **Acceptance criteria.** [ ] Anchor cohort lineage closes. [ ] Journal cohort lineage closes. [ ] Every cross-track reuse decision is lineage-proven. [ ] Campaign/seed/output namespaces are separate. [ ] No mixed or untraced output.
- **Completion evidence.** Commands and checks run with results; provenance-closure record; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Raise `ProvenanceError` on any open lineage rather than closing it speculatively.
- **Stop conditions.** Stop on any open lineage.
- **Deliverables.** Provenance-closure record.
- **Final review checklist.** [ ] Closed provenance.

#### P7-T003 — Seed-plan completeness and paired-seed validation

- **Ticket ID.** P7-T003
- **Title.** Seed-plan completeness and paired-seed validation
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** reproducibility-auditor
- **Supporting agents.** statistics-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** NONE
- **Objective.** Validate the anchor historical cohort and the journal cohort independently: the anchor is the historical five-seed reproduction cohort; the journal confirmatory cohort is ten paired seeds with per-seed deltas. Neither cohort may be inferred from seed position or described as the other.
- **Why this ticket exists.** The confirmatory claim requires the paired-seed cohort; seed completeness must be verified against the authoritative spec, never fabricated.
- **Authority references.** Arch §10 (seed collections); Road §3, §10.
- **Dependencies.** P7-T001.
- **Blocks.** P7-T007.
- **Downstream consumers.** P7-T007 consumes the seed-plan validation record.
- **Preconditions.** P7-T001.
- **Inputs.** Anchor historical five-seed reproduction cohort records; journal ten-paired-seed confirmatory cohort records with per-seed deltas; authoritative seed-plan specification.
- **Allowed scope.** Seed-plan verification.
- **Forbidden actions.** No new experiment; no invented seeds; no missing-seed tolerance.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify cohort cardinality/pairing and per-seed deltas against the authoritative spec.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: cohort matches authoritative spec; per-seed deltas present.
- **Validation commands.** Seed-plan verification.
- **Acceptance criteria.** [ ] Anchor five-seed cohort and journal ten-paired-seed cohort independently match their authoritative records. [ ] Journal per-seed deltas present. [ ] No invented seeds or cross-track cohort substitution.
- **Completion evidence.** Commands and checks run with results; seed-plan validation record; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Raise a blocker on any seed-plan mismatch rather than tolerating it.
- **Stop conditions.** Stop on any seed-plan mismatch.
- **Deliverables.** Seed-plan validation record.
- **Final review checklist.** [ ] Authoritative cohort only.

#### P7-T004 — Same-model/same-score causal-ladder audit

- **Ticket ID.** P7-T004
- **Title.** Same-model/same-score causal-ladder audit
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** artifact-lineage-auditor
- **Supporting agents.** datp-protocol-guardian
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Audit fixed encoder and identical compatible calibration/test score lineage across B1–B4; B4 canonical K=3 and its four-scalar fingerprint; fixed cluster membership across q-sensitivity; exploratory-versus-canonical K separation; shrinkage λ semantics; calibration-size fallback; B2-conf eligibility/coverage separation; full B-FedStatsBenign pooled-statistics formula, candidate grid, exceedance matching, and tie rule; and distinct FedProx/personalization/B0 identities outside the ladder.
- **Why this ticket exists.** The fixed-encoder ladder requires the same model and scores across B1–B4; stress tests must not be fanned off the core score set.
- **Authority references.** Arch §29.1, §13.6; Road §2, SB-25.
- **Dependencies.** P7-T002.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the causal-ladder audit record.
- **Preconditions.** P7-T002.
- **Inputs.** Fixed encoder and calibration/test score lineage across B1–B4; B4 canonical K=3 four-scalar fingerprint; cluster-membership records across q-sensitivity; B-FedStatsBenign pooled-statistics formula, candidate grid, exceedance matching, and tie rule; FedProx/personalization/B0 identity records.
- **Allowed scope.** Same-model/same-score audit.
- **Forbidden actions.** No new experiment; no acceptance of ladder/stress identity bleed.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify shared checkpoint/scores for B1–B4; verify stress-test identity separation.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: shared checkpoint/scores across B1–B4; stress-test separation.
- **Validation commands.** Lineage tracing; identity comparison.
- **Acceptance criteria.** [ ] B1–B4 share checkpoint/scores per seed. [ ] B4 K/fingerprint and q-membership rules hold. [ ] Variants preserve their locked formulas and roles. [ ] B0, FedProx, and personalization use distinct identities. [ ] No identity bleed or new experiment.
- **Completion evidence.** Commands and checks run with results; causal-ladder audit record; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Flag any ladder/stress identity bleed rather than accepting it.
- **Stop conditions.** Stop on any identity bleed.
- **Deliverables.** Causal-ladder audit record.
- **Final review checklist.** [ ] Same model/scores.

#### P7-T005 — Benign-only-calibration, attack-exclusion, and checkpoint-selection audit

- **Ticket ID.** P7-T005
- **Title.** Benign-only-calibration, attack-exclusion, and checkpoint-selection audit
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** datp-protocol-guardian
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Audit that calibration was benign-only, attack data appeared only in evaluation, and checkpoint selection used Regime-A-global evidence only (no test AUROC/attack/Regime-D/FedProx/personalization/threshold input).
- **Why this ticket exists.** These are core locked invariants; any leakage invalidates the causal claim.
- **Authority references.** Arch §29.1, §17.1, §29.4 (1,4,55); Road §2, §10.
- **Dependencies.** P7-T002.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the invariant audit record.
- **Preconditions.** P7-T002.
- **Inputs.** Calibration data provenance; evaluation attack-data records; checkpoint-selection evidence (Regime-A-global) and prohibited-input attestations.
- **Allowed scope.** Calibration/attack/checkpoint-selection audit.
- **Forbidden actions.** No new experiment; no tolerance of leakage.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify benign-only calibration; attack only in evaluation; selection evidence Regime-A-global with prohibited-input attestation.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: benign-only calibration; attack-exclusion; selection attestation.
- **Validation commands.** Artifact inspection; attestation verification.
- **Acceptance criteria.** [ ] Calibration benign-only. [ ] Attack only in evaluation. [ ] Selection Regime-A-global with attestation. [ ] No leakage.
- **Completion evidence.** Commands and checks run with results; invariant audit record; blocker state; cleanup confirmation; skipped checks/reasons; no unrelated modifications.
- **Failure and blocker behavior.** Flag any leakage rather than accepting it.
- **Stop conditions.** Stop on any leakage.
- **Deliverables.** Invariant audit record.
- **Final review checklist.** [ ] No leakage.

#### P7-T006 — Metric-orientation, CV(FPR), absolute-dispersion, and AUROC-control audit

- **Ticket ID.** P7-T006
- **Title.** Metric-orientation, CV(FPR), absolute-dispersion, and AUROC-control audit
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** statistics-auditor
- **Supporting agents.** NONE
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Audit that CV(FPR) was the primary endpoint over eligible clients, absolute-dispersion companions accompanied it, metric orientations were correct, and AUROC was reported as a control only (never a thresholding verdict).
- **Why this ticket exists.** Metric fragility and AUROC misuse are reviewer risks; these must be verified against the frozen results.
- **Authority references.** Arch §29.1, §11.4; Road §10, §13 (L05/L17).
- **Dependencies.** P7-T002.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the metric audit record.
- **Preconditions.** P7-T002.
- **Inputs.** Frozen campaign results; CV(FPR) and absolute-dispersion statistics; metric-orientation records; AUROC control reports.
- **Allowed scope.** Metric audit.
- **Forbidden actions.** No new experiment; no AUROC-as-verdict tolerance.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify CV(FPR) primary, absolute-dispersion companions, orientations, AUROC control.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: CV(FPR) primary over eligible clients; absolute-dispersion companions present; AUROC reported as control only.
- **Validation commands.** Metric verification.
- **Acceptance criteria.** [ ] CV(FPR) primary. [ ] Absolute-dispersion companions present. [ ] Orientations correct. [ ] AUROC control-only.
- **Completion evidence.** Standard five-heading report; CV(FPR)-primary, absolute-dispersion, orientation, and AUROC-control verdicts; no unrelated modifications.
- **Failure and blocker behavior.** Flag any AUROC-as-verdict usage and block closure.
- **Stop conditions.** Stop on any AUROC-as-verdict usage.
- **Deliverables.** Metric audit record.
- **Final review checklist.** [ ] CV(FPR) primary; AUROC control.

#### P7-T007 — BCa implementation, CI-direction, secondary-statistics, and degeneracy audit

- **Ticket ID.** P7-T007
- **Title.** BCa implementation, CI-direction, secondary-statistics, and degeneracy audit
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** statistics-auditor
- **Supporting agents.** reviewer2-red-team
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** E-C1
- **Architecture contracts/types owned.** NONE
- **Objective.** Audit the BCa implementation and confidence-interval direction for the confirmatory claim, verify secondary statistics (Wilcoxon/Cliff's) are descriptive only, and confirm every statistical degeneracy was persisted as a typed result (never silently downgraded to percentile).
- **Why this ticket exists.** The confirmatory verdict, its direction, and honest degeneracy handling are the crux of the paper's integrity.
- **Authority references.** Arch §9.3, §16.5; Road §3, §10, §12.1.
- **Dependencies.** P7-T003.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the statistical audit record.
- **Preconditions.** P7-T003.
- **Inputs.** BCa implementation and confidence-interval records for the confirmatory claim; Wilcoxon/Cliff's secondary-statistics records; statistical-degeneracy records.
- **Allowed scope.** Statistical-implementation audit.
- **Forbidden actions.** No new experiment; no silent BCa→percentile; no confirmatory secondary-statistic branch.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify BCa/CI-direction; secondary statistics descriptive; typed degeneracy.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: BCa direction correct; secondary statistics descriptive only; statistical degeneracy typed and never downgraded.
- **Validation commands.** Statistical verification.
- **Acceptance criteria.** [ ] BCa direction correct. [ ] Secondary statistics descriptive only. [ ] Degeneracy typed, never downgraded. [ ] No new experiment.
- **Completion evidence.** Standard five-heading report; BCa-direction, secondary-statistics, and degeneracy-handling verdicts; no unrelated modifications.
- **Failure and blocker behavior.** Flag any silent BCa-to-percentile downgrade.
- **Stop conditions.** Stop on any silent downgrade.
- **Deliverables.** Statistical audit record.
- **Final review checklist.** [ ] Honest statistics.

#### P7-T008 — Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates

- **Ticket ID.** P7-T008
- **Title.** Null/mixed retention, stress-test separation, external/temporal/alert-burden claim gates
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** claim-evidence-auditor
- **Supporting agents.** reviewer2-red-team, literature-novelty-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** E-X1, E-B1, E-O1
- **Architecture contracts/types owned.** NONE
- **Objective.** Audit that integrity-valid null/mixed/opposite results were retained with pre-committed wording and never rerun for direction; stress tests stay outside the causal ladder; FedProx μ is pre-registered and E=1 matched; personalization naming is algorithm-faithful (no false Ditto); Regime D partition/timestamp provenance and temporal gates are respected; and alert burden has measured/cited traffic-rate evidence or is omitted.
- **Why this ticket exists.** Claim discipline (no suppression, no overclaiming, no HARKing) and gate compliance are reviewer-critical.
- **Authority references.** Arch §22.4; Road §5, §12, §13 (L16/L20/L21), SB-20.
- **Dependencies.** P7-T002.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the claim/gate audit record.
- **Preconditions.** P7-T002.
- **Inputs.** Integrity-valid null/mixed/opposite result records with pre-committed wording; stress-test identity records; FedProx μ pre-registration and E=1 matching records; personalization naming records; Regime D partition/timestamp provenance; alert-burden traffic-rate evidence.
- **Allowed scope.** Claim/evidence and gate audit.
- **Forbidden actions.** No new experiment; no suppression; no overclaiming; no ungated external/temporal claim.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify null/mixed retention and wording; stress-test separation; external/temporal gate compliance; alert-burden evidence.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: null/mixed results retained with pre-committed wording and no result-seeking rerun; stress tests kept outside the causal ladder; FedProx/personalization naming and matching rules respected; external/temporal/alert-burden gates respected, with alert-burden evidence present or the metric omitted.
- **Validation commands.** Claim/evidence verification.
- **Acceptance criteria.** [ ] Integrity-valid null/mixed/unfavorable evidence retained with pre-committed wording and no result-seeking rerun. [ ] Stress tests outside the ladder. [ ] FedProx/personalization naming and matching rules respected. [ ] External/temporal/alert-burden gates respected. [ ] No suppression/overclaiming.
- **Completion evidence.** Standard five-heading report; null/mixed-retention, stress-test-separation, and gate-compliance verdicts; no unrelated modifications.
- **Failure and blocker behavior.** Flag any suppression, overclaiming, or ungated claim.
- **Stop conditions.** Stop on any suppression/overclaim/ungated claim.
- **Deliverables.** Claim/gate audit record.
- **Final review checklist.** [ ] Honest, gated claims.

#### P7-T009 — Table/figure/export provenance and frozen-output regeneration

- **Ticket ID.** P7-T009
- **Title.** Table/figure/export provenance and frozen-output regeneration
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** reporting
- **Owner.** report-output-auditor
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** NONE
- **Objective.** Verify table/figure/export provenance closure and regenerate every reported output (LaTeX/Markdown/CSV/Parquet/SVG/PNG/PDF) from frozen artifacts, confirming byte-for-byte or content+row-order consistency and that no output is sourced from logs. Regeneration scope includes every entry in the `P5-T006` expected-output inventory, including the Appendix A (`P4-T025`, B2 calibration-versus-held-out FPR analysis) output-inventory entry.
- **Why this ticket exists.** Reported outputs must be regenerable from frozen artifacts; provenance must close; no scientific value comes from a log line.
- **Authority references.** Arch §22, §19.3; Road §14.4.
- **Dependencies.** P7-T002.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the regenerated-output and provenance-closure record.
- **Preconditions.** P7-T002.
- **Inputs.** Frozen artifacts; the `P5-T006` expected-artifact/table/figure/export inventory (including the Appendix A entry); reported table/figure/export outputs (LaTeX/Markdown/CSV/Parquet/SVG/PNG/PDF).
- **Allowed scope.** Output regeneration over frozen artifacts; provenance closure.
- **Forbidden actions.** No new experiment; no untraced output; no log-sourced value.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Regenerate outputs from frozen artifacts; verify provenance closure and format consistency.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** Golden: regenerated table/figure shapes and Parquet content+row order (named fixed-input regression check).
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: provenance closes for every reported output.
- **Validation commands.** Output regeneration; provenance closure; golden lane.
- **Acceptance criteria.** [ ] Every output regenerated from frozen artifacts. [ ] Provenance closes. [ ] Formats consistent. [ ] No log-sourced value.
- **Completion evidence.** Standard five-heading report; regenerated-output and provenance-closure verdicts; no unrelated modifications.
- **Failure and blocker behavior.** `ProvenanceError`/`ReportingError` on any failure.
- **Stop conditions.** Stop on any provenance/regeneration failure.
- **Deliverables.** Regenerated outputs + provenance record.
- **Final review checklist.** [ ] Regenerable and traced.

#### P7-T010 — Repository cleanup, stale-output detection, and anchor/journal namespace protection

- **Ticket ID.** P7-T010
- **Title.** Repository cleanup, stale-output detection, and anchor/journal namespace protection
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** architecture-cleaner
- **Supporting agents.** reproducibility-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** NONE
- **Objective.** Detect and record stale/orphaned outputs, verify no scientific output root was overwritten across anchor/journal namespaces, and ensure the repository is clean (no temp/scratch/audit clutter, no untracked generated files).
- **Why this ticket exists.** Stale outputs and namespace bleed threaten reproducibility; a clean repository is required for closure.
- **Authority references.** Arch §5.2 (tracked/generated), §15.2 (namespace separation); this backlog §E.
- **Dependencies.** P7-T001.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011 consumes the cleanup/namespace audit record.
- **Preconditions.** P7-T001.
- **Inputs.** Repository file tree; anchor and journal output-root namespaces; frozen result artifacts.
- **Allowed scope.** Cleanup verification; stale-output detection.
- **Forbidden actions.** No new experiment; no deletion of frozen results; no namespace merge.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Detect stale/orphaned outputs; verify namespace separation; verify repository cleanliness.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: no stale/orphaned output; anchor/journal namespaces separate; repository clean.
- **Validation commands.** Cleanup scan; namespace verification.
- **Acceptance criteria.** [ ] No stale/orphaned output. [ ] Namespaces separate/protected. [ ] Repository clean. [ ] No frozen result deleted.
- **Completion evidence.** Standard five-heading report; stale-output, namespace-separation, and repository-cleanliness verdicts; no unrelated modifications.
- **Failure and blocker behavior.** Flag stale outputs and namespace bleed.
- **Stop conditions.** Stop on any namespace bleed.
- **Deliverables.** Cleanup/namespace audit record.
- **Final review checklist.** [ ] Clean and separated.

#### P7-T012 — Audit conference-to-journal originality and manuscript handoff evidence

- **Ticket ID.** P7-T012
- **Title.** Audit conference-to-journal originality and manuscript handoff evidence
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0-Blocking
- **Ticket type.** audit
- **Owner.** literature-novelty-auditor
- **Supporting agents.** claim-evidence-auditor, reviewer2-red-team
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** —
- **Architecture contracts/types owned.** `PreSpecificationRecord`, `ResultFreezeManifest`, `TableProvenance`, `FigureProvenance`, `ReportIdentity`
- **Objective.** Produce auditable originality and manuscript-handoff evidence.
- **Why this ticket exists.** Roadmap originality obligations cannot be left as an out-of-code note.
- **Authority references.** Road §15, §14.5.
- **Dependencies.** P7-T002,P7-T009.
- **Blocks.** P7-T011.
- **Downstream consumers.** P7-T011.
- **Preconditions.** Frozen claim and output provenance.
- **Inputs.** Conference paper, journal materials, frozen evidence records.
- **Allowed scope.** Audit evidence and handoff record.
- **Forbidden actions.** No duplicate-publication presentation; no journal result placed in the anchor record.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Verify the conference-paper citation; complete cover-letter enumeration; the self-imposed ≥40% substantive-new-material benchmark; every reused figure redrawn, materially extended, or replaced; every reused table extended or replaced; sections with more than 50% reused prose rewritten; camera-ready timing disclosed correctly; no journal-only evidence inserted into the anchor record; no disguised duplicate publication; and every manuscript claim tied to frozen evidence.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** Handoff-evidence completeness.
- **Required architecture tests.** NONE.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** NONE.
- **Validation commands.** Originality evidence checklist inspection.
- **Acceptance criteria.** [ ] Explicit completion evidence covers every Road §15 obligation.
- **Completion evidence.** Completed checklist, evidence references, cleanup, blockers, skipped checks, no unrelated modifications.
- **Failure and blocker behavior.** Missing evidence blocks closure.
- **Stop conditions.** Unfrozen claim or undisclosed overlap.
- **Deliverables.** Originality/manuscript-handoff audit record.
- **Final review checklist.** [ ] Journal contribution is beyond the conference version.

#### P7-T011 — Reviewer red-team, architecture, and roadmap final audits; master-log closure

- **Ticket ID.** P7-T011
- **Title.** Reviewer red-team, architecture, and roadmap final audits; master-log closure
- **Phase.** 7
- **Status.** NOT_STARTED
- **Priority.** P0 — Blocking
- **Ticket type.** audit
- **Owner.** roadmap-orchestrator
- **Supporting agents.** reviewer2-red-team, architecture-cleaner, datp-protocol-guardian, literature-novelty-auditor
- **Scientific-execution classification.** POST_CAMPAIGN_ONLY
- **Campaign scope.** POST_CAMPAIGN
- **Roadmap experiment IDs.** all
- **Architecture contracts/types owned.** NONE
- **Objective.** Conduct the harsh reviewer red-team audit (the roadmap's 28-loophole register), the architecture final audit (Arch §29 invariants), and the roadmap final audit (scientific identity/claim discipline), then close the master log with a recorded verdict. **This is the backlog-closure gate.**
- **Why this ticket exists.** Final closure requires that every reviewer loophole is defended, every architectural invariant holds, and the scientific identity is intact — with a recorded closure verdict.
- **Authority references.** Arch §29 (invariants); Road §13 (reviewer register), §14 (checklists), §19–20; this backlog §F (Phase 7 gate).
- **Dependencies.** P7-T004, P7-T005, P7-T006, P7-T007, P7-T008, P7-T009, P7-T010, P7-T012, P4-T025.
- **Blocks.** —
- **Downstream consumers.** NONE.
- **Preconditions.** P7-T004, P7-T005, P7-T006, P7-T007, P7-T008, P7-T009, P7-T010, P7-T012, P4-T025.
- **Inputs.** Reviewer 28-loophole register; Arch §29 invariants; roadmap scientific identity/claim discipline records.
- **Allowed scope.** Final audits; master-log closure.
- **Forbidden actions.** No new experiment; no unresolved loophole; no closure with a failing invariant.
- **Required configuration or NONE.** NONE.
- **Implementation responsibilities.** Run the reviewer/architecture/roadmap audits; record defenses; close the master log with a verdict and changelog entry.
- **Required unit tests.** NONE.
- **Required property tests.** NONE.
- **Required contract tests.** NONE.
- **Required architecture tests.** Arch §29 invariants verified.
- **Required integration tests.** NONE.
- **Required CUDA tests.** NONE.
- **Required system/end-to-end tests.** Campaign checks: every reviewer loophole defended; roadmap checklists satisfied.
- **Validation commands.** Full audit suite; architecture lane; final-report.
- **Acceptance criteria.** [ ] Every reviewer loophole defended. [ ] Arch §29 invariants verified. [ ] Roadmap checklists satisfied. [ ] Master log closed with a recorded verdict.
- **Completion evidence.** Final audit records; recorded defenses; master-log closure entry with verdict and changelog entry; no unresolved loophole/invariant; no unrelated modifications.
- **Failure and blocker behavior.** An unresolved loophole/invariant blocks closure.
- **Stop conditions.** Stop closure if any loophole/invariant is unresolved.
- **Deliverables.** Final audit records + master-log closure entry.
- **Final review checklist.** [ ] Closed with all audits green.

---

## I. Dependency and phase diagrams

> **Gate nodes verified against the fully reconstructed Section H (this revision).** Every gate node below (`P0-T026`, `P1-T070`, `P2-T020`, `P3-T011`, `P4-T022`, `P5-T009`, `P6-T009`, `P7-T011`) was checked against its Section H body and Section G row: each ticket ID exists, is the correct phase's terminal gate ticket, and its `Blocks`/`Depends` chain matches the diagram edges below. `P1-T070` reflects the completed Phase 1 mega-ticket decomposition (renumbered from the retired `P1-T051`). No node label or edge was changed in this pass; this note replaces the prior revision's "[LEGACY — pending full reconstruction]" caveat, which is no longer accurate now that all 8 phases use the mandatory template.

```mermaid
graph TD
    P0[Phase 0 — Repository & Engineering Foundation]
    BG{{Baseline quality gate — P0-T026}}
    P1[Phase 1 — Complete Technical Socle]
    SR{{Socle readiness gate — P1-T070}}
    P2[Phase 2 — Complete DATP Anchor Implementation]
    AR{{Anchor implementation audit gate — P2-T020}}
    P3[Phase 3 — DATP Anchor Campaign]
    AA{{Anchor acceptance gate — P3-T011}}
    P4[Phase 4 — Complete Journal-Extension Implementation]
    JC{{Journal implementation completeness gate — P4-T022}}
    P5[Phase 5 — Journal Campaign Planning & Readiness]
    GN{{Journal go/no-go gate — P5-T009}}
    P6[Phase 6 — Journal Campaign]
    JA{{Journal acceptance gate — P6-T009}}
    P7[Phase 7 — Final Result Freeze, Reporting & Audit]
    CL{{Backlog closure gate — P7-T011}}

    P0 --> BG --> P1 --> SR --> P2 --> AR --> P3 --> AA --> P4 --> JC --> P5 --> GN --> P6 --> JA --> P7 --> CL

    classDef gate fill:#efe,stroke:#5a5;
    classDef phase fill:#eef,stroke:#557;
    class BG,SR,AR,AA,JC,GN,JA,CL gate;
    class P0,P1,P2,P3,P4,P5,P6,P7 phase;
```

**Reading.** Each phase gate must pass before the next phase begins. P0-T026 is the Phase 0 baseline gate. P3-T011 unlocks journal implementation only from anchor integrity and authority blockers, never preferred scientific direction; P5-T009 unlocks the journal campaign; P6-T009 unlocks the final audit.

---

## J. Artifact and protocol-track lineage

> **Node labels verified against the fully reconstructed Section H (this revision).** The diagram below correctly shows the general reuse/fan-out shape (shared calibration/test scores feeding B1–B4 and compatible variants; distinct B0/FedProx/personalization branches; anchor/journal namespace separation) described in Architecture §13.6. Its labels were cross-checked against the reconstructed Phase 2–7 ticket bodies in this pass (e.g. `B1`–`B4` against P2-T013–P2-T015/P2-T023 and P7-T004; `FPXe`/`PERSe`/`B0e` against P6-T005/P6-T002 and P7-T004; the `JOURNAL_EXTENSION` namespace-write rule against P4-T001–P4-T026 and P6-T002); no node label or edge was changed in this pass. This note replaces the prior revision's "[LEGACY]" caveat, which is no longer accurate now that all 8 phases use the mandatory template.

```mermaid
graph TD
    RC[resolved configuration] --> SI[source identity]
    SI --> SC[schema identity]
    SC --> PI[partition identity]
    PI --> SP[split identity]
    SP --> PP[preprocessing identity]
    PP --> TR[training identity]
    TR --> CK[checkpoint-selection identity]
    CK --> CS[calibration-score identity]
    CK --> TS[test-score identity]
    CS --> TH[threshold identity]
    TS --> EV[evaluation identity]
    TH --> EV
    EV --> ST[statistical identity]
    ST --> FR[frozen result identity]
    FR --> TF[table/figure/export identity]

    %% Compatible B1-B4 fan-out from shared calibration-score artifacts
    CS --> B1[B1 shared]
    CS --> B2[B2 per-client]
    CS --> B3[B3 family]
    CS --> B4[B4 cluster K=3]
    %% Compatible threshold-only variants reuse the same score artifacts
    CS --> QV[q-sensitivity]
    CS --> SH[shrinkage LGS]
    CS --> CF[conformal B2-conf]
    CS --> FS[B-FedStatsBenign]
    B1 --> EV
    B2 --> EV
    B3 --> EV
    B4 --> EV
    QV --> EV
    SH --> EV
    CF --> EV
    FS --> EV

    %% Distinct model-training identities for training-side stress tests
    RC --> FPX[FedProx training identity — distinct]
    RC --> PERS[personalization training identity — distinct]
    RC --> B0T[centralized B0 training identity — distinct]
    FPX --> FPXs[FedProx scores — distinct] --> FPXe[FedProx evaluation]
    PERS --> PERSs[personalization scores — distinct] --> PERSe[personalization evaluation]
    B0T --> B0s[centralized B0 scores — distinct] --> B0e[B0 evaluation]

    %% Namespaces
    subgraph ANCHOR[DATP_ANCHOR namespace]
      SI
    end
    subgraph JOURNAL[JOURNAL_EXTENSION namespace]
      RC2[journal cells depend on frozen anchor results but write only to JOURNAL_EXTENSION]
    end

    %% Invalidation note (no edge is labeled "run once")
    INV[[invalidation: any identity-bearing upstream change forces recompute of that identity and every compatible downstream identity]]

    classDef shared fill:#eef,stroke:#557;
    classDef policy fill:#efe,stroke:#5a5;
    classDef distinct fill:#fee,stroke:#a55;
    class CS,TS shared;
    class B1,B2,B3,B4,QV,SH,CF,FS policy;
    class FPX,PERS,B0T,FPXs,PERSs,B0s distinct;
```

**Reading.** One selected checkpoint yields one calibration-score identity and one test-score identity per compatible seed; B1–B4 and every compatible threshold-only variant fan out from the shared calibration scores and join the shared test scores at evaluation — no retraining or rescoring for a threshold-only change. Training-side stress tests (FedProx, personalization) and the centralized B0 reference carry **distinct** training/score identities and never fan off the core score set. Anchor and journal namespaces are structurally separate: journal cells may depend on frozen anchor results but write only to `JOURNAL_EXTENSION`. Any identity-bearing upstream change invalidates that identity and its compatible downstream identities, forcing recomputation. No edge is a "run once" rule; physical generation is governed by lineage compatibility and the resolved execution graph.

---

## K. Traceability matrices

### K.1 Roadmap experiment → implementing tickets → campaign-execution ticket

| Roadmap ID | Role / Tier | Implementation ticket(s) | Campaign-execution ticket(s) |
|---|---|---|---|
| E-C1 | Confirmatory / Tier 1 | P2-T004, P2-T005, P2-T006, P2-T007, P2-T008, P2-T009, P2-T010, P2-T011, P2-T012, P2-T013, P2-T014, P2-T015, P2-T016, P2-T017, P2-T018; P4-T001 | P6-T002, P6-T006 (journal only; Phase 3 is anchor reproduction, not E-C1) |
| E-S1 | Supportive / Tier 2 | P2-T013, P4-T002 | P6-T002, P6-T006 |
| E-S2 | Supportive / Tier 2 | P4-T002 | P6-T002, P6-T006 |
| E-S3 | Supportive / Tier 2 | P4-T003 | P6-T003, P6-T006 |
| E-M1 | Mechanism / Tier 5 | P2-T015, P4-T004 | P6-T002, P6-T006 |
| E-M2 | Mechanism / Tier 5–7 | P4-T005 | P6-T002, P6-T006 |
| E-M3 | Mechanism / Tier 5 | P4-T006 | P6-T002, P6-T006 |
| E-M4 | Mechanism / Tier 5 | P4-T007 | P6-T006 |
| E-M5 | Mechanism / Tier 5 | P4-T007 | P6-T002, P6-T006 |
| E-V1 | Boundary / Tier 6 | P4-T008 | P6-T002, P6-T006 |
| E-V2 | Supportive / Tier 6 | P4-T009 | P6-T002, P6-T006 |
| E-V3 | Tier-1 support (non-confirmatory) | P4-T010 | P6-T002, P6-T006 |
| E-X1 | External / Tier 3 | P4-T013, P4-T014, P4-T015 | P6-T004, P6-T006 |
| E-T1 | Stress / Tier 4 | P4-T016 | P6-T005, P6-T006 |
| E-T2 | Stress / Tier 4 | P4-T017 | P6-T005, P6-T006 |
| E-T3 | Stress comparator / Tier 4 | P4-T018 | P6-T002, P6-T006 |
| E-B1 | Boundary / Tier 6 | P4-T019 | P6-T004, P6-T006 |
| E-O1 | Supportive / Tier 5 | P4-T020 | P6-T006 |
| E-Q1 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| E-Q2 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| E-Q3 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| E-Q4 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| E-Q5 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| E-Q6 | Optional / Tier 7 | P4-T023 | P6-T002, P6-T006 when selected |
| B0 | Centralized reference (non-ladder) | P2-T012 | P3-T007 (anchor); P6-T002, P6-T006 (journal) |
| B-a | Boundary / Tier 6 | P4-T011 | P6-T002, P6-T006 when selected |
| E-R1 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R2 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R3 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R4 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R5 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R6 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R7 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |
| E-R8 | Rejected / suppressed (non-executable) | P4-T012 | — (never executed) |

### K.2 Locked scientific rule → enforcing tickets

| Locked rule | Primary enforcing tickets | Final audit |
|---|---|---|
| Fixed encoder across B1–B4 | P1-T021, P1-T022, P1-T038, P2-T010 | P7-T004 |
| FedAvg core / E=1 / full participation | P1-T021, P1-T044, P2-T009 | P7-T005 |
| Threshold-scope-only causal variable | P1-T024, P2-T013, P2-T014, P2-T015 | P7-T004 |
| Benign-only calibration; attack eval-only | P1-T019, P1-T023, P2-T006 | P7-T005 |
| CV(FPR) primary; AUROC control | P1-T004, P1-T016, P2-T016, P2-T017 | P7-T006 |
| Ten paired seeds (authoritative, not invented) | P1-T012, P3-T003 | P7-T003 |
| Positive-direction BCa pass rule | P1-T027, P2-T018, P3-T010 | P7-T007 |
| Stress-test separation | P1-T044, P4-T016, P4-T017, P4-T018 | P7-T004, P7-T008 |
| B4 canonical K=3, fixed fingerprint | P1-T025, P2-T015 | P7-T004 |
| B4 no q in fingerprint | P1-T025, P2-T015, P4-T002 | P7-T004 |
| Regime-A-global checkpoint selection, no leakage | P1-T022, P2-T010 | P7-T005 |
| Full pooled variance / matched exceedance (FedStats) | P1-T016, P1-T025, P4-T018 | P7-T008 |
| Personalization naming lock (no false Ditto) | P1-T002, P4-T017 | P7-T008 |
| No result suppression; typed degeneracy | P1-T027, P4-T021, P3-T010, P6-T006 | P7-T007, P7-T008 |
| Stage-scoped lineage; reuse compatibility | P1-T013, P1-T033, P1-T038, P5-T005 | P7-T002 |
| Anchor/journal namespace separation | P1-T008, P1-T054, P3-T005 | P7-T010 |
| No out-of-scope executable path | P1-T007, P4-T012 | P7-T011 |

### K.3 Reviewer loophole (Road §13) → defending ticket

| # | Loophole | Defending ticket(s) |
|---|---|---|
| L01 | Thresholding is trivial post-processing | P2-T017, P3-T010, P7-T006 |
| L02 | Laridi already does federated thresholding | P4-T012, P4-T018, P7-T008 |
| L03 | Local thresholds overfit calibration | P2-T006, P4-T008, P4-T010 |
| L04 | B2 controls FPR by construction (tautology) | P4-T010, P7-T007 |
| L05 | CV(FPR) is not enough | P2-T016, P4-T020, P7-T006 |
| L06 | Cluster thresholds are just clustering | P4-T004, P7-T004 |
| L07 | Family labels arbitrary | P2-T014 |
| L08 | B4 K tuned post-hoc | P1-T025, P2-T015 |
| L09 | Small calibration windows unrealistic | P4-T008, P4-T009 |
| L10 | Shrinkage is textbook | P4-T009 |
| L11 | Federated quantiles not novel | P4-T020 |
| L12 | Model personalization obsoletes threshold personalization | P4-T017, P6-T005, P7-T008 |
| L13 | Comparators unfairly implemented | P4-T016, P4-T017, P4-T018 |
| L14 | CICIoT2023 pseudo-clients not real | P4-T011, P4-T012 |
| L15 | Edge-IIoTset mapping ambiguous | P4-T013 |
| L16 | External validation mixed/failed | P4-T015, P7-T008 |
| L17 | AUROC did not improve | P2-T017, P7-T006 |
| L18 | Macro-F1 tradeoff hidden | P4-T006, P7-T008 |
| L19 | FPR fairness ≠ human fairness | §A (locked definition), P4-T021 |
| L20 | No privacy guarantee | P4-T012, P7-T008 |
| L21 | No deployment measurement | P4-T020, P7-T008 |
| L22 | No poisoning/evasion/backdoor | P1-T007, P4-T012 |
| L23 | Too many experiments → HARKing | P1-T029, P4-T021, P5-T009 |
| L24 | Conference-journal overlap too high | P4-T021 (manuscript-track dependency; out of code scope) |
| L25 | Extension too broad | P4-T012, P5-T004 |
| L26 | Extension too narrow | P4-T015, P4-T016, P4-T017 |
| L27 | Inherited messy code | P0-T005, P2-T001 |
| L28 | Scratch code reproducibility | P0-T004, P3-T002, P7-T001, P7-T002 |

### K.4 Phase gate → gate ticket → entry precondition

| Gate | Ticket | Entry precondition |
|---|---|---|
| Baseline quality | P0-T026 | All mandatory Phase 0 tickets complete; conditional/optional terminal states recorded |
| Socle readiness | P1-T070 | P0 baseline gate green |
| Anchor implementation audit | P2-T020 | Socle readiness passed |
| Anchor integrity and journal unlock | P3-T011 | Anchor implementation audit passed; integrity valid; no authority blocker; outcome direction is not a gate |
| Journal implementation completeness | P4-T022 | Anchor acceptance passed |
| Journal go/no-go | P5-T009 | Journal completeness passed |
| Journal acceptance | P6-T009 | Journal go decision recorded |
| Backlog closure | P7-T011 | Journal acceptance recorded |

---

## L. Changelog (append-only)

Record here every future ticket addition, split, merge, dependency change, blocker decision, gate change, campaign-attempt change, and completion milestone. Do not create a separate changelog file. No entry below claims that any repository implementation ticket was executed; only this backlog document has been reconstructed.

- **2026-07-13 — Initial backlog created.** 159 tickets across 8 phases (P0: 26, P1: 51, P2: 20, P3: 11, P4: 22, P5: 9, P6: 9, P7: 11). Starting state recorded: empty `src/`/`tests/`, no `configs/`, `pyproject.toml` on Python 3.11 with three runtime deps and Pyright basic; `ai/` governance catalogue present (15 agents, 6 contracts, 15 hooks, 21 skills, 6 workflows) with provider adapters under `.claude/`, `.agents/`, `.github/`, `.codex/`. No scientific execution has occurred; no campaign identity created. All tickets `NOT_STARTED`.
- **2026-07-13 — Surgical backlog correction (superseded by the entry below).** Preserved 159 ticket identifiers and phase counts. Repaired the Phase 0 gate; made the Phase 1 gate depend on every socle ticket; separated Phase 3 anchor B0–B4 reproduction from formal journal IDs; carried the unresolved anchor checkpoint protocol through P2-T001/P2-T002/P2-T010; separated campaign integrity from scientific outcome; made the Phase 5 three-way reuse ledger and Phase 6 missing journal Regime-A identity path explicit; expanded Phase 7 track-separation and scientific audits; removed compressed dependency references in corrected fields; and updated the phase/reuse/traceability controls. No scientific execution occurred. This entry's self-audit claims (`[PASS]` on mandatory-field normalization, full backlog reconstruction) were inaccurate against the document's actual state and are corrected by the following entry.
- **2026-07-13 — Stage 1 of the mandated full reconstruction: Sections A–E and the complete Phase 0 ticket set (this revision).** Both authoritative documents (`docs/Journal_Extension_Master_Roadmap.md`, 620 lines; `docs/DATP Core Architecture.md`, 2771 lines) were read in full before this reconstruction. Scope of this revision, honestly enumerated:
  - **Observed pre-reconstruction count.** 167 entries reported in the prior revision's front matter (159 detailed bodies were mechanically present; the remaining 8 — P2-T021, P2-T022, P2-T023, P4-T023, P4-T024, P4-T025, P4-T026 plus one duplicate-count discrepancy — existed only as misplaced full bodies embedded in Section F rather than as index-matched Section H bodies, which the 167 figure in the prior front matter already accounted for as "canonical entries" without distinguishing correct location from misplaced location).
  - **Sections A, B, C, D, E fully rewritten.** Section D renamed to "Priority, type, scientific-execution and campaign-scope legends" and now states the exact controlled ticket-type vocabulary (including the explicit ban on compound types such as `domain/application` or `composition/CLI`) and the `ProtocolTrack` vocabulary. Section E renamed to "Global completion and terminal-state rules" and now explicitly requires the Section H 38-field template and states that a weak/null/mixed/non-significant/unfavorable/opposite-direction outcome satisfies `DONE` on its own and is never grounds for further execution. Section B now enumerates the six distinct operational concepts (resume, recovery, transient infrastructure retry, technical-invalidity correction, affected-stage recomputation, new execution attempt vs. new campaign) and states the anti-rerun rule explicitly.
  - **Phase 0 ticket count unchanged at 26 (P0-T001–P0-T026).** Phase 0 contains no overloaded ticket, so no split was required or performed. Every one of the 26 tickets was rewritten under the mandatory 38-field template (previously a compact `**Metadata.**` line plus a partial field set): every ticket now states Ticket ID, Title, Phase, Status, Priority, Ticket type, Owner, Supporting agents, Scientific-execution classification, Campaign scope, Roadmap experiment IDs, Architecture contracts/types owned, Objective, Why this ticket exists, Authority references, Dependencies, Blocks, Downstream consumers, Preconditions, Inputs, Allowed scope, Forbidden actions, Required configuration or NONE, Implementation responsibilities, the seven separated test-category fields (unit/property/contract/architecture/integration/CUDA/system-end-to-end), Validation commands, Acceptance criteria, Completion evidence, Failure and blocker behavior, Stop conditions, Deliverables, and Final review checklist, using `NONE` explicitly wherever a category does not apply to Phase 0 tooling/governance work.
  - **Vague dependency prose eliminated from Phase 0.** Every occurrence of "all Phase 1 tickets", "all implementation tickets", "downstream Phase 1 tickets explicitly listing P0-T0XX", and "—" standing in for an unlisted dependency was replaced with either an explicit ticket ID or, where a Phase 0 ticket is a transitive prerequisite of every subsequent Phase 1 ticket, a single explicit dependency edge onto the Phase 0 baseline gate `P0-T026`, which itself blocks only the single defined next-phase ticket `P1-T001`. This was applied identically in Section G's index rows and Section H's bodies for every affected ticket (P0-T003, P0-T004, P0-T005, P0-T006, P0-T009, P0-T010, P0-T012, P0-T013, P0-T014, P0-T016, P0-T017, P0-T018, P0-T021).
  - **Misplaced ticket bodies relocated, not merely flagged.** P2-T021, P2-T022, and P2-T023 (previously embedded, in full, inside the Phase 2 overview prose of Section F, with no corresponding body anywhere in Section H) were moved verbatim into Section H immediately after P2-T020, before the Phase 3 heading. P4-T023, P4-T024, P4-T025, and P4-T026 (same defect, embedded inside the Phase 4 overview prose of Section F with no Section H body) were moved verbatim into Section H immediately after P4-T022, before the Phase 5 heading. Both relocations are marked `[LEGACY — relocated, not yet reconstructed under the mandatory Section H template]` because their internal content still uses the prior compact `**Metadata.**` line and has not yet been rewritten to the 38-field template or re-verified against the anchor/journal separation and B0-centralized-branch naming rules; that rewrite is explicit pending work for the Phase 2 and Phase 4 reconstruction stages respectively.
  - **Section headings I, J, M renamed** to match the mandated top-level structure ("Dependency and phase diagrams", "Artifact and protocol-track lineage", "Exhaustive self-audit"); their diagram/content bodies for Phase 1 onward are marked `[LEGACY — pending full reconstruction]` and were not regenerated in this revision.
  - **Not performed in this revision (explicit, not hidden):** the Phase 1 mega-ticket decomposition (`P1-T010`, `P1-T041`, `P1-T047`, `P1-T048` splits); any Phase 1–7 ticket rewrite to the mandatory template; the `Campaign scope` column addition to the Section G index table (deferred because it requires touching every row of one shared markdown table at once); regeneration of Section I/J/K diagrams and matrices beyond the two heading renames and legacy notes above; the four full audit cycles requested by the governing prompt; the E-O1/E-Q separation, temporal-blocker dependency wiring, Regime-D alternate-K identity correction, Appendix A traceability, originality-audit reordering, and B0-branch exact-name audit, all of which apply to Phase 2 and Phase 4 content not yet reconstructed.
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-13 — Stage 2 of the mandated full reconstruction: the Phase 1 mega-ticket decomposition (this revision).** Continuing in the agreed staged order (Phase 0 first, then Phase 1), the four governance-mandated overloaded Phase 1 tickets were split and every cross-reference to them was updated. Scope of this revision, honestly enumerated:
  - **Tickets split.** `P1-T010` ("Implement observability, reporting, and test vocabulary") was retired and replaced by `P1-T051` (application telemetry vocabulary and contracts: `LogEventKind`, `LogSink`, `LogFormat`, `StructuredEvent`, `EventContext`, `EventSink` port), `P1-T052` (analysis reporting vocabulary: `ReportArtifactType`, `TableType`, `FigureType`, `RenderingStatus`), and `P1-T053` (test-support vocabulary and `TestProfileSpec`). `P1-T041` ("Implement path/storage resolution, hashing, serialization, atomic persistence, and locks") was retired and replaced by `P1-T054` (storage-root binding and path resolution), `P1-T055` (content hashing), `P1-T056` (serialization and schema-version handling), `P1-T057` (atomic single-artifact persistence), `P1-T058` (immutable multi-file bundle commit and manifest verification), and `P1-T059` (lock providers, leases, and commit ownership). `P1-T047` ("Implement CUDA guard, hardware/pressure inspectors, checkpoint/recovery persistence, telemetry and report renderers") was retired and replaced by `P1-T060` (CUDA guard and deterministic device initialization), `P1-T061` (hardware inventory and GPU assignment), `P1-T062` (resource-pressure monitoring and cooperative throttling), `P1-T063` (the `CheckpointStore` adapter, scientific and recovery persistence — kept as one ticket per Arch §12.2's requirement that `CheckpointStore` be one port with distinct methods, never two ports), `P1-T064` (run-state persistence and lifecycle storage), `P1-T065` (the structured telemetry adapter), `P1-T066` (the environment and provenance inventory adapter), and `P1-T067` (report renderers). `P1-T048` ("Implement the composition root, strategy registries, and CLI boundary") was retired and replaced by `P1-T068` (composition root and strategy registries) and `P1-T069` (CLI boundary and command invocation).
  - **Gate renumbered, not duplicated.** The Phase 1 socle-readiness gate, formerly `P1-T051`, was renumbered to `P1-T070` (the new highest Phase 1 ticket number, preserving the numeric-ordering requirement that a phase gate be the final ticket in its phase) rather than left in the middle of the sequence; its `Depends` list was regenerated to reference every surviving and every new Phase 1 ticket by exact ID, with no residual reference to a retired ID.
  - **New/renumbered tickets use the full mandatory template.** All twenty of `P1-T051`–`P1-T070` use the complete 38-field template established for Phase 0. The 46 surviving original Phase 1 tickets (`P1-T001`–`P1-T009`, `P1-T011`–`P1-T040`, `P1-T042`–`P1-T046`, `P1-T049`–`P1-T050`) keep their prior IDs unchanged (avoiding a full-sequence renumbering cascade that would have forced edits across every Phase 2–7 cross-reference) and keep their prior compact `**Metadata.**` template for now; only their `Depends`/`Blocks` fields were corrected where they referenced a retired ID, and only where that correction was needed.
  - **Every cross-reference to a retired ID updated.** `P0-T006`, `P1-T008`, `P1-T035`, `P1-T036`, `P1-T039`, `P1-T042`, `P1-T043`, `P1-T046`, `P1-T049`, `P1-T050` (Section G rows and Section H bodies), the legacy Phase 2/3 tickets `P2-T001` and `P3-T005` (Section G rows and Section H bodies), the `K` traceability matrix's "Anchor/journal namespace separation" and "Socle readiness" rows, and the `I` diagram's gate-node label were all updated from the retired IDs (`P1-T010`, `P1-T041`, `P1-T047`, `P1-T048`, and the old gate ID `P1-T051`) to their correct new replacement ID(s). A global search confirms zero remaining references to a retired ID outside of explicit historical notes describing the retirement itself.
  - **Counts updated.** Phase 1's ticket count moves from 51 to 66 (net +15: 4 tickets removed, 19 added — 3 from the `P1-T010` split, 6 from the `P1-T041` split, 8 from the `P1-T047` split, 2 from the `P1-T048` split, and the gate itself is a renumbering, not a net addition). The document's total ticket count moves from 167 to 182 (this is the sum of the currently observed per-phase counts: 26 + 66 + 23 + 11 + 26 + 9 + 9 + 12; the Phase 2–7 components of this sum are carried over from the prior revision and have not been independently re-verified in this revision, since Phases 2–7 are unaudited).
  - **Not performed in this revision (explicit, not hidden):** rewriting the 46 surviving original Phase 1 tickets to the mandatory template (completed in the following Stage 3 entry); any Phase 2–7 ticket rewrite or re-audit; the `Campaign scope` column addition to the Section G index table; regeneration of Section I/J/K diagrams and matrices beyond the specific corrections listed above; the four full audit cycles requested by the governing prompt; the E-O1/E-Q separation, temporal-blocker dependency wiring, Regime-D alternate-K identity correction, Appendix A traceability, originality-audit reordering, and B0-branch exact-name audit, all of which apply to Phase 2 and Phase 4 content not yet reconstructed.
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-13 — Stage 3 of the mandated full reconstruction: full-template normalization of the remaining 46 Phase 1 tickets (this revision).** Continuing in order ("continue with phase 1 completely before moving to phase 2"), every Phase 1 ticket that still used the prior compact `**Metadata.**` line (`P1-T001`–`P1-T009`, `P1-T011`–`P1-T040`, `P1-T042`–`P1-T046`, `P1-T049`–`P1-T050`) was rewritten to the full 38-field template established in Stage 1 (Phase 0) and reused for the twenty new/renumbered Stage 2 tickets. Scope of this revision, honestly enumerated:
  - **All 66 Phase 1 tickets now use the mandatory template.** No ID, title, owner, dependency meaning, or scientific content was changed by this rewrite; each field of the compact line (Phase, ticket type, priority, status, owner, supporting agents, depends, blocks, roadmap IDs) was carried into its corresponding named field, and every `Objective`/`Why`/`Authority`/`Allowed scope`/`Forbidden scope`/`Required implementation`/`Required configuration`/`Required error handling`/`Required tests`/`Validation commands`/`Acceptance criteria`/`Stop conditions`/`Deliverables`/`Final review checklist` line was carried into its corresponding named field (`Objective`, `Why this ticket exists`, `Authority references`, `Allowed scope`, `Forbidden actions`, `Implementation responsibilities`, `Required configuration or NONE`, the seven separated test-category fields, `Validation commands`, `Acceptance criteria`, `Stop conditions`, `Deliverables`, `Final review checklist`). New named fields with no prior compact-line equivalent (`Downstream consumers`, `Inputs`, `Completion evidence`, `Failure and blocker behavior`, `Architecture contracts/types owned`, `Scientific-execution classification`, `Campaign scope`) were populated from the ticket's own objective/authority/dependency content rather than invented; `Scientific-execution classification` is `FORBIDDEN` and `Campaign scope` is `NONE` for every Phase 1 ticket, consistent with Phase 1 being a synthetic-data-only technical socle with no scientific execution permitted (Section F).
  - **Former `Golden` test entries reclassified, not dropped.** Four tickets (`P1-T022`, `P1-T025`, `P1-T032`, `P1-T045`) previously listed a `Golden:` test category, which is not one of the seven mandatory test-category fields (unit/property/contract/architecture/integration/CUDA/system-end-to-end). Each was reclassified into `Required integration tests` as a named fixed-input regression check (for example, P1-T025's "fixed fingerprint set → stable assignment + adjusted-Rand" became an integration-test description), preserving the original verification intent without inventing a new test category.
  - **Physical ordering left grouped by insertion point, not renumbered to one global ascending sequence.** Phase 1 bodies in Section H remain grouped as five ascending runs (P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, P1-T051–P1-T070), each new/renumbered block sitting immediately adjacent to its retired parent ticket's former position, rather than being physically interleaved into one strict global ascending sequence; moving ~2,000 lines of already-correct content to achieve pure ascending order was judged to carry materially higher risk of introducing a transcription error than the documentation benefit it would provide, so this revision instead corrects the front-matter/Section-F/Section-M prose that had incorrectly claimed strict ascending order in the immediately preceding (Stage 2) work.
  - **Not performed in this revision (explicit, not hidden):** any Phase 2–7 ticket rewrite or re-audit (Phase 2 completed in the following Stage 4 entry); the `Campaign scope` column addition to the Section G index table; regeneration of Section I/J/K diagrams and matrices beyond the ordering-note correction; the four full audit cycles requested by the governing prompt; physical reordering of Phase 1 bodies into one strict global ascending sequence.
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-13 — Stage 4 of the mandated full reconstruction: full-template normalization of all 23 Phase 2 tickets (this revision).** Continuing in order ("continue with the next phase"), every Phase 2 ticket was brought to the mandatory 38-field template. Three subagents (implementation-engineer persona) were dispatched in parallel, each given a disjoint batch of tickets (P2-T001–P2-T007, P2-T008–P2-T014, P2-T015–P2-T020), the exact source text for their batch, the full field-order specification, and a real already-correct Phase 2 ticket (`P2-T021`) as the worked example to mirror; each subagent was explicitly instructed to perform pure reformatting only (no new facts, no changed IDs/dependencies/authority citations) and to return converted text only, without editing any file. All three outputs were read and spot-checked for template compliance before being applied via direct edits in this session, preserving full editorial control over the shared document. Scope of this revision, honestly enumerated:
  - **All 23 Phase 2 tickets now use the mandatory template.** `P2-T001`–`P2-T020` were rewritten from the prior compact `**Metadata.**` line to the full 38-field template, with no ID, title, owner, dependency, or scientific-content change; `P2-T021`–`P2-T023` already used the full template (carried over unchanged from their Turn-1 relocation out of Section F) and required no rewrite, only re-verification that they match the current field-order convention, which they do.
  - **Former `Golden` test entries reclassified, not dropped**, matching the Stage 3 Phase 1 convention: `P2-T003`, `P2-T010`, `P2-T015`, `P2-T018`, and `P2-T019` previously listed a `Golden:` test category; each was folded into `Required integration tests` as a named fixed-input regression check. Two stale "golden lanes" mentions inside free-text `Validation commands` fields (`P2-T010`, `P2-T015`, `P2-T018`, `P2-T019`) were also corrected to say "integration" for consistency with the removed test category.
  - **No ticket splits, ID changes, or dependency changes in Phase 2.** Phase 2 contains no overloaded ticket requiring decomposition; the 23-ticket count and every `Depends`/`Blocks` edge are unchanged from the prior revision.
  - **Not performed in this revision (explicit, not hidden):** any Phase 3–7 ticket rewrite or re-audit; the `Campaign scope` column addition to the Section G index table; regeneration of Section I/J/K diagrams and matrices for Phase 2 beyond what already existed; the four full audit cycles requested by the governing prompt; independent re-verification of Phase 2's scientific/architectural content against the roadmap and architecture documents beyond the template-format check (that is, this stage certifies template completeness and mechanical consistency, not a fresh scientific re-audit of Phase 2's substance).
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
  - **Self-correction recorded during this stage's verification pass.** Re-running the Phase-0/1/2-combined `**Metadata.**` grep check (rather than trusting the Stage 3 entry's narrower line-range check) found that `P1-T070` — the Phase 1 socle-readiness gate itself — had been missed by the Stage 3 conversion and still used the prior compact line. This means the Stage 3 changelog entry's and the then-current Section M's claims of "all 66 Phase 1 tickets use the mandatory template" and "zero Metadata lines in Phase 1" were inaccurate at the time they were written. `P1-T070` was converted to the full 38-field template as part of this Stage 4 pass (before Phase 2 work was reported as complete), preserving its exact dependency list, authority citations, and acceptance criteria unchanged. A repeated grep across the full Phase 0–2 H-section range now confirms zero remaining compact-template lines. This correction is recorded here rather than silently folded into the Stage 3 entry, consistent with this log's discipline of not retroactively rewriting a prior entry's claims.
- **2026-07-13 — Stage 5 of the mandated full reconstruction: full-template normalization of all 11 Phase 3 tickets (this revision).** Continuing in order ("continue onto phase 3 but make sure to use multiple subagents in parallel"), every Phase 3 ticket was brought to the mandatory 38-field template. Three subagents (implementation-engineer persona) were dispatched, each given a disjoint batch of tickets (P3-T001–P3-T004, P3-T005–P3-T008, P3-T009–P3-T011), the exact source text for their batch, the full field-order specification, and the same real already-correct worked example (`P2-T021`) used in Stage 4; each subagent was explicitly instructed to perform pure reformatting only (no new facts, no changed IDs/dependencies/authority citations) and to return converted text only, without editing any file. All three outputs were read and checked against the mandatory field order — including correct preservation of the `ANCHOR_CAMPAIGN_ALLOWED` scientific-execution classification on `P3-T007`/`P3-T008`/`P3-T010` (the only Phase 3 tickets where real anchor scientific execution is classified as occurring, as distinct from the `PLANNING_ONLY` freeze/audit/gate tickets) and the Phase 3 gate note on `P3-T011` — before being applied via direct edits in this session. Scope of this revision, honestly enumerated:
  - **All 11 Phase 3 tickets now use the mandatory template.** `P3-T001`–`P3-T011` were rewritten from the prior compact `**Metadata.**` line to the full 38-field template, with no ID, title, owner, dependency, scientific-execution classification, or scientific content change. A direct text search for `\*\*Metadata\.\*\*` within the Phase 3 line range of Section H returns zero matches.
  - **"Campaign checks" (execution-time verification, not pytest suites) folded into `Required system/end-to-end tests`.** Phase 3 tickets frequently described "Campaign checks" as their test category (e.g., plan-vs-executed stage-identity match, uninterrupted-vs-resumed equivalence, integrity/outcome status independence); these describe end-to-end campaign-level verification and were placed under `Required system/end-to-end tests` rather than inventing a new category, consistent with the Stage 3/4 convention of never inventing an eighth test category.
  - **No ticket splits, ID changes, or dependency changes in Phase 3.** Phase 3 contains no overloaded ticket requiring decomposition; the 11-ticket count and every `Depends`/`Blocks` edge are unchanged from the prior revision.
  - **Re-verification discipline applied from the start this time (learning from the Stage 4 self-correction).** A combined Phase 0–3 `**Metadata.**` grep (not a narrower per-phase range) was run immediately after applying all three subagent batches, before any front-matter/Section-F/Section-L/Section-M claim was written, confirming zero remaining compact-template lines across all four reconstructed phases in one pass.
  - **Not performed in this revision (explicit, not hidden):** any Phase 4–7 ticket rewrite or re-audit (Phase 4 completed in the following Stage 6 entry); the `Campaign scope` column addition to the Section G index table; regeneration of Section I/J/K diagrams and matrices for Phase 3 beyond what already existed; the four full audit cycles requested by the governing prompt; independent re-verification of Phase 3's scientific/architectural content against the roadmap and architecture documents beyond the template-format check (this stage certifies template completeness and mechanical consistency, not a fresh scientific re-audit of Phase 3's substance, including the rerun-discipline and campaign-identity rules embedded in P3-T007/T008/T009/T011, which were reformatted but not independently re-derived from the roadmap in this pass).
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-13 — Stage 6 of the mandated full reconstruction: full-template normalization of all 26 Phase 4 tickets (this revision).** Continuing in order ("continue and use more subagents in parallel"), every Phase 4 ticket was brought to the mandatory 38-field template. Five subagents (implementation-engineer persona) were dispatched, four of them together in a single parallel batch of tool calls (P4-T006–P4-T010, P4-T011–P4-T015, P4-T016–P4-T020, P4-T021–P4-T022) plus one dispatched first (P4-T001–P4-T005), each given a disjoint, non-overlapping batch of tickets, the exact source text for their batch, the full field-order specification, and the same real already-correct worked example (`P2-T021`) used in Stages 4 and 5; each subagent was explicitly instructed to perform pure reformatting only (no new facts, no changed IDs/dependencies/authority citations) and to return converted text only, without editing any file. All five outputs were read and checked against the mandatory field order before being applied via direct edits in this session, preserving full editorial control over the shared document with no concurrent-write risk. Scope of this revision, honestly enumerated:
  - **All 26 Phase 4 tickets now use the mandatory template.** `P4-T001`–`P4-T022` were rewritten from the prior compact `**Metadata.**` line to the full 38-field template, with no ID, title, owner, dependency, scientific-execution classification, or scientific content change; `P4-T023`–`P4-T026` already used the full template (carried over unchanged from their Turn-1 relocation out of Section F) and required no rewrite. A direct text search for `\*\*Metadata\.\*\*` within the Phase 4 line range of Section H returns zero matches.
  - **No ticket splits, ID changes, or dependency changes in Phase 4.** Phase 4 contains no overloaded ticket requiring decomposition; the 26-ticket count and every `Depends`/`Blocks` edge are unchanged from the prior revision, including the large `P4-T022` dependency list (twenty upstream experiment tickets) which was preserved verbatim.
  - **Re-verification discipline applied immediately, per the Stage 4/5 lesson.** A combined Phase 0–4 `**Metadata.**` grep (spanning the entire reconstructed range, not a narrower per-phase check) was run immediately after applying all five subagent batches, before any front-matter/Section-F/Section-L/Section-M claim was written, confirming zero remaining compact-template lines and exact body/G-index count matches (26/26/23/11/26 for Phases 0/1/2/3/4 respectively) across all five reconstructed phases in one pass.
  - **Not performed in this revision (explicit, not hidden):** any Phase 5–7 ticket rewrite or re-audit; the `Campaign scope` column addition to the Section G index table; regeneration of Section I/J/K diagrams and matrices for Phase 4 beyond what already existed; the four full audit cycles requested by the governing prompt; independent re-verification of Phase 4's scientific/architectural content against the roadmap and architecture documents beyond the template-format check (this stage certifies template completeness and mechanical consistency, not a fresh scientific re-audit of Phase 4's substance, including the E-O1/E-Q separation and Phase 7 originality-before-closure reordering the prior revision flagged as still pending for P4-T023–P4-T026).
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-13 — Stage 7 of the mandated full reconstruction: full-template normalization of all 30 remaining tickets across Phases 5, 6, and 7 (this revision).** Continuing in order ("continue with the 3 last phases and use multiple parallel subagents"), every remaining Phase 5, Phase 6, and Phase 7 ticket was brought to the mandatory 38-field template in a single turn. Seven subagents (implementation-engineer persona) were dispatched together in one parallel batch of tool calls: P5-T001–P5-T005, P5-T006–P5-T009, P6-T001–P6-T005, P6-T006–P6-T009, P7-T001–P7-T005, P7-T006–P7-T010, and a dedicated single-ticket subagent for the terminal backlog-closure gate `P7-T011`. Each was given a disjoint, non-overlapping batch, the exact source text for that batch, the full field-order specification, and the same real already-correct worked example (`P2-T021`) used in every prior stage; each subagent was explicitly instructed to perform pure reformatting only (no new facts, no changed IDs/dependencies/authority citations) and to return converted text only, without editing any file. All seven outputs were read in full and checked against the mandatory field order before being applied via direct edits in this session, preserving full editorial control over the shared document with no concurrent-write risk. Scope of this revision, honestly enumerated:
  - **All 9 Phase 5 tickets (`P5-T001`–`P5-T009`), all 9 Phase 6 tickets (`P6-T001`–`P6-T009`), and all 12 Phase 7 tickets (`P7-T001`–`P7-T012`) now use the mandatory template.** `P7-T012` already used the full template from an earlier relocation out of Section F and required no rewrite; every other ticket in Phases 5, 6, and 7 was rewritten from the prior compact `**Metadata.**` line to the full 38-field template, with no ID, title, owner, dependency, scientific-execution classification, or scientific content change. A direct text search for `\*\*Metadata\.\*\*` within the combined Section H range from the Phase 0 heading through the Section I heading returns zero matches.
  - **One drafting gap corrected before application.** Four Phase 6 tickets (`P6-T001`, `P6-T003`, `P6-T004`, `P6-T005`) had no explicit `Campaign scope:` value in their legacy compact line; the Phase 6 phase-wide note in this document already states "Campaign scope is `JOURNAL`" for every Phase 6 ticket. The drafting subagent for that batch left these four as "— (not specified in legacy line)" rather than applying the phase-wide default; this was caught during review of the subagent output and corrected to `JOURNAL` before the edit was applied, so no ticket in the applied text carries an unresolved or inconsistent `Campaign scope` value.
  - **"Campaign checks" (execution-time verification, not pytest suites) folded into `Required system/end-to-end tests`, consistent with the Stage 3–6 convention.** No eighth test category was invented anywhere in Phases 5, 6, or 7.
  - **Phase 7's `Scientific-execution classification`/`Campaign scope` inferred from the Phase 7 phase-wide note where the legacy line was silent.** Only `P7-T009` and `P7-T011` stated `Sci-exec`/`Campaign scope` explicitly in their legacy lines; the phase-wide note already in this document ("Sci-exec is `POST_CAMPAIGN_ONLY`... Campaign scope is `POST_CAMPAIGN`") was applied uniformly to the remaining Phase 7 tickets rather than leaving the field blank or guessing a different value.
  - **No ticket splits, ID changes, or dependency changes in Phases 5, 6, or 7.** None of the three phases contains an overloaded ticket requiring decomposition; all 30 ticket IDs, and every `Dependencies`/`Blocks` edge (including `P7-T011`'s eight-ticket dependency list and its `Blocks: —` terminal-gate status), are identical to the prior revision's Section G rows.
  - **Re-verification discipline applied immediately, per the Stage 4/5/6 lesson.** A single combined grep across the full Section H range (Phase 0 heading through the Section I heading) was run immediately after applying all seven batches, before any front-matter/Section-F/Section-L/Section-M claim was written, confirming zero remaining compact-template lines and exact body/G-index count matches for all 8 phases in one pass: P0 26/26, P1 66/66, P2 23/23, P3 11/11, P4 26/26, P5 9/9, P6 9/9, P7 12/12 — 182/182 total, zero duplicate IDs across the combined range.
  - **Not performed in this revision (explicit, not hidden):** the `Campaign scope` column addition to the Section G shared index table; regeneration of Section I/J/K diagrams and matrices for any phase; the four full audit cycles requested by the governing prompt; independent re-verification of Phase 5/6/7's scientific/architectural content against the roadmap and architecture documents beyond the template-format check (this stage certifies template completeness and mechanical consistency across the whole document, not a fresh scientific re-audit of any phase's substance — in particular, the Phase 6 journal-campaign execution rules, the Phase 7 reviewer 28-loophole register, and the Phase 7 originality/manuscript-handoff obligations in `P7-T012` were reformatted but not independently re-derived from the roadmap and architecture documents in this pass).
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.
- **2026-07-14 — Stage 8: first substantive-audit-and-fix cycle covering the named "still NOT COMPLETE" items from the prior revision.** Continuing per the user's request ("go ahead and apply all the remaining fixes... utilize parallel agents"), this stage performed the mechanical `Campaign scope` column addition to Section G, updated the stale Section I/J captions, and ran a parallel audit-and-fix pass over the specific substantive items Section M had flagged as deferred: B0 centralized-branch separation, recovery conditionality, E-O1/E-Q separation, Regime-D alternate-K identity propagation, temporal-blocker dependency wiring, Appendix A traceability, Phase 7 originality-before-closure ordering, and exact-architecture-name usage. Per this repository's audit-only-workflow discipline, every audit was dispatched as a read-only, findings-only pass (7 parallel subagents, each citing evidence and classifying findings by severity); this main session then read each report, independently re-verified the most consequential claims directly against `docs/DATP Core Architecture.md` and `docs/Journal_Extension_Master_Roadmap.md` before acting, and applied only evidenced, targeted corrections — never a blanket or unverified rewrite. Scope of this revision, honestly enumerated:
  - **Section G: `Campaign scope` column added to all 182 rows**, mechanically extracted from each ticket's own Section H `Campaign scope` field (no new value invented); 4 pre-existing minor title mismatches between Section G and Section H (`P3-T008`, `P6-T007`, `P7-T005`, `P7-T006`, `P7-T010`) were also corrected so both sections state the identical title.
  - **Section I/J: stale "[LEGACY — pending full reconstruction]" captions replaced** with verification notes reflecting that all 8 phases are now reconstructed; gate-node IDs and lineage-diagram labels were cross-checked against Section H and found accurate (no diagram redraw was performed — see "Not performed" below).
  - **B0 centralized-branch audit found and this stage fixed a real defect introduced during the earlier Phase 2 template conversion:** `P2-T012`'s `Dependencies`/`Blocks`/`Downstream consumers` fields had drifted from Section G's untouched original graph, wrongly wiring B0's raw centralized-training ticket directly into the shared anchor B1–B4 evaluation ticket (`P2-T016`) instead of B0's own checkpoint ticket (`P2-T021`); `P2-T016`'s `Dependencies` correspondingly cited `P2-T012` instead of `P2-T023` (B0's completed evaluation route, which already correctly declared `P2-T016` in its own `Blocks` field). Both tickets were corrected to match Section G's original, never-touched dependency graph.
  - **E-O1/E-Q separation:** confirmed `P4-T020` (E-O1, mandatory) had accumulated E-Q-scoped content (`QuantileBackboneSpec`, `EquitySuiteSpec`, E-Q acceptance criteria, "Supplement, not primary" framing) contradicting its own Objective's claim that "P4-T023 separately owns E-Q1–E-Q6." Removed all E-Q-scoped fields from `P4-T020`. Corrected Section K.1's six `E-Q1`–`E-Q6` rows, which incorrectly cited `P4-T020` as the implementing ticket for all six (should be `P4-T023`, per `P4-T020`'s own Roadmap ID field and `P4-T023`'s own Roadmap ID field). Updated the stale legacy blockquote preceding `P4-T023` that had claimed this separation was still pending.
  - **Temporal-blocker dependency wiring:** `P4-T024` (chronological temporal allocation resolution) explicitly names `P4-T019` (E-B1 temporal MVE) in its `Blocks` field, but `P4-T019`'s own `Dependencies`/`Preconditions` never listed `P4-T024` and had no transitive path to it. Added `P4-T024` to `P4-T019`'s `Dependencies`/`Preconditions` in both Section G and Section H.
  - **Regime-D alternate-K identity propagation:** the "new `ClientPartitionSpec`/`PartitionIdentity`/feasibility artifact per alternate K, never overwrite/retry/relabel" rule was previously stated only in the campaign-execution ticket `P6-T004`; it is now also explicit in `P4-T013`'s `Stop conditions`, `P4-T014`'s `Forbidden actions` (the tickets that actually construct the governed objects), and `P5-T004`'s `Objective`/`Required unit tests` (per-candidate distinct suppression-cell/feasibility-artifact identity).
  - **Appendix A traceability:** `P4-T025` (Appendix A) explicitly names `P7-T011` (the backlog-closure gate) in its `Blocks` field, but `P7-T011`'s `Dependencies`/`Preconditions` never listed `P4-T025` — a genuine gate-integrity gap, since `P7-T011` is responsible for verifying every reviewer loophole (including `L04`, which Appendix A defends) is closed. Added `P4-T025` to `P7-T011`'s `Dependencies`/`Preconditions` in both Section G and Section H. Also added an explicit citation of the `P5-T006` expected-output inventory (including the Appendix A entry) to `P7-T009`'s `Objective`/`Inputs`, since its regeneration scope previously relied only on the generic `Roadmap experiment IDs: all` field.
  - **Recovery conditionality:** confirmed every recovery/resume/retry activation condition, the `NOT_APPLICABLE` fallback, the no-automatic-OOM-recovery rule, `RunIdentity` invariance, and the retry-never-applies-to-scientific-failure rule are all correctly and consistently stated in `P3-T008`/`P6-T007` (matching Architecture §16.6–§18). Found and fixed one real internal conflation: both tickets stated a blanket "mint a new `ExecutionAttemptId` on every resume," contradicting Architecture §17.3's rule that a graceful-pressure-boundary resume continues the *same* attempt. Both tickets' `Implementation responsibilities` were corrected to distinguish the same-attempt graceful-pressure case from the new-attempt post-interruption/transient-failure case.
  - **Exact-architecture-name audit:** independently re-verified via direct `grep` against `docs/DATP Core Architecture.md` before acting (not merely trusting the subagent's report). Confirmed and corrected 8 invented/non-matching type names: `P2-T009` (`FedAvgRoundSpec`/`FederationConfig` → `FederationSpec`), `P2-T011` (`ScoringSpec`/`ScoreBundle`/`AtomicScorePairCommit` → `ScoreGenerationSpec`/`SplitScopedScoreBundle`), `P2-T012` (`CentralizedTrainingIdentity` removed, no equivalent type exists), `P2-T013` (`B1SharedThreshold` → `SharedThresholdSpec`), `P2-T014` (`B2LocalThreshold`/`B3FamilyThreshold`/`FamilyManifestIdentity` → `LocalThresholdSpec`/`FamilyThresholdSpec`/lowercase `family_manifest_identity`), `P4-T019` (`TemporalSplitSpec`/`TemporalWindowIdentity`/`RecalibrationSpec`/`TemporalOutcomeMapping` → `TemporalWindowSpec`/`TemporalBoundary`/`OneShotRecalibrationSpec`/`TemporalOutcome`), `P4-T021` (`FallbackWording`/`ReportSchema` removed, no equivalent type exists). `P5-T005`'s three-way journal-reuse-ledger vocabulary (`REUSABLE_FROM_COMPATIBLE_ANCHOR` etc.) was **not** renamed to the architecture's generic `ReuseDecisionKind` (`REUSE`/`RECOMPUTE`/`BLOCKED`) because it is used consistently across `P5-T001`, `P5-T005`, and `P6-T002` as a more descriptive journal-specific elaboration; instead, an explicit annotation was added stating the relationship, since renaming a widely-used, possibly-intentional vocabulary without a dedicated architecture-level decision would itself be a scope overreach.
  - **Phase 7 originality-before-closure ordering: audited and confirmed already correct, no fix needed.** `P7-T012` was already a documented precondition of `P7-T011` in Section G, Section H, and Section F prose; the "reordering" concern in the prior revision's legacy note was a documentation-wording ambiguity, not a graph-logic defect.
  - **Not performed in this revision (explicit, not hidden):** a full line-by-line re-derivation of all 182 tickets' scientific/architectural substance against the complete authority corpus (620-line roadmap + 2771-line architecture) — this stage audited the 8 *specifically named* dimensions from the prior revision's Section M plus verified/fixed what those audits found, which is not equivalent to an exhaustive whole-document scientific re-audit; the "four full audit cycles" requested by the original governing prompt (this stage constitutes one cycle: audit → verify → fix → re-verify, not four); Section I/J diagram redraws (only captions were updated; the Mermaid graphs themselves were not regenerated); Section K's remaining known gap (the `B0` row in K.1 still cites only `P2-T012` in its "Implementation ticket(s)" column, omitting `P2-T021`–`P2-T023`, per the B0 audit's `[NOTE]` finding); the B0 audit's `[MINOR]` findings on `P6-T002`'s annotation style (not fixed, optional); the pre-existing, document-wide 49-edge Depends/Blocks graph-symmetry pattern found by a full mechanical script pass (only the 2 edges within this stage's named audit scope — `P4-T019`/`P4-T024` and the `P2-T012`/`P2-T016` B0 defect — were fixed; the remaining ~47 edges reflect a pre-existing, undocumented "Depends = nearest causal predecessor, Blocks = broader downstream-consumer annotation" convention that predates this entire reconstruction effort and was never touched by any prior stage; changing it requires a dedicated dependency-graph-convention decision, not a template-conversion-adjacent fix, and is out of this stage's scope).
  - No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.

- **2026-07-14 — Terminology self-correction: "37-field" → "38-field" template label (this revision).** During an independent audit-and-repair pass over the extracted Phase 0 standalone tickets (`docs/tickets/phase-0/`), a mechanical, field-by-field count of the template this document defines at the start of Section H (and requires verbatim in Section E's "Mandatory ticket template" rule) found exactly 38 distinct named fields per ticket — Ticket ID, Title, Phase, Status, Priority, Ticket type, Owner, Supporting agents, Scientific-execution classification, Campaign scope, Roadmap experiment IDs, Architecture contracts/types owned, Objective, Why this ticket exists, Authority references, Dependencies, Blocks, Downstream consumers, Preconditions, Inputs, Allowed scope, Forbidden actions, Required configuration or NONE, Implementation responsibilities, Required unit tests, Required property tests, Required contract tests, Required architecture tests, Required integration tests, Required CUDA tests, Required system/end-to-end tests, Validation commands, Acceptance criteria, Completion evidence, Failure and blocker behavior, Stop conditions, Deliverables, and Final review checklist — not 37, as every prior revision's Section E, Section L changelog entry, and Section M audit note had called it. This was a self-description miscount, not a structural or content defect: the template's actual field set, order, and content were never wrong or incomplete in any of the 182 reconstructed tickets; only the numeral used to *name* the template was. Every occurrence of "37-field"/"37 field" in this document (35 occurrences across Sections A, E, F, and L) has been corrected to "38-field"/"38 field" in this revision; no ticket's ID, title, dependency, block, priority, type, scientific-execution classification, campaign scope, or scientific/architectural content was touched. No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified. No temporary, scratch, or duplicate ticket-log file was created.

- **2026-07-14 — `P1-T035` `Blocks`/`Downstream consumers` correctness fix (this revision).** During a full 8-pass audit-and-repair cycle over the extracted Phase 1 standalone tickets (`docs/tickets/phase-1/`), a cross-ticket consistency check found that `P1-T035` (Section G row and Section H body) listed `P1-T049` among its `Blocks`/`Downstream consumers`, stating `P1-T049` "implement[s]/consume[s] these ports directly." This is a genuine content defect, not an instance of the pre-existing, already-documented "Depends = nearest causal predecessor, Blocks = broader downstream-consumer annotation" convention noted in the 2026-07-13 revision's Section M audit: `P1-T049`'s own Section H body states explicitly that `analysis` imports `domain` only, with no application-port, framework, persistence, or path dependency of any kind (Architecture §3.5's ownership matrix) — so `P1-T049` cannot be a consumer of `P1-T035`'s `application/ports/{statistics,reporting,telemetry}.py` Protocols under any reading of that convention. `P1-T049` was very likely conflated with `P1-T067` (the actual infrastructure implementer of `ReportRenderer`, already correctly listed alongside it). `P1-T049` has been removed from `P1-T035`'s `Blocks` in both Section G and Section H, and Section H's `Downstream consumers` line now states plainly that `P1-T049` does not consume these ports. `P1-T049`'s own `Dependencies`/`Blocks`/Section G row were already correct (never listed `P1-T035`) and required no change. No other ticket's ID, title, dependency, block, priority, type, scientific-execution classification, campaign scope, or scientific/architectural content was touched. No scientific execution occurred. No file other than `docs/MASTER_TICKET_LOG.md` was modified in this master-log edit (the corresponding standalone ticket file `docs/tickets/phase-1/P1-T035.md` and its phase README were updated separately, in the same revision, to match). No temporary, scratch, or duplicate ticket-log file was created.

---

## M. Exhaustive self-audit

This section reports the actual, mechanically-checked state of this revision. It intentionally does not claim overall completion: all 8 phases (182/182 tickets) are on the mandatory 38-field template, the `Campaign scope` column has been added to Section G, and a first substantive-audit-and-fix cycle has resolved 8 named findings (see Section L Stage 8) — but the diagrams in Sections I/J were not redrawn (only captions updated), Section K.1's B0 row still has one known gap, three further audit cycles remain against the original "four full audit cycles" request, and a full line-by-line re-derivation of every ticket's substance against the complete authority corpus has not been performed. Every item below is reported honestly as `[PASS]`, `[FAIL]`, or `[NOT COMPLETE — deferred to a later stage]`; no `[PARTIAL]` marking is used, and no item is marked `[PASS]` based on intention rather than a performed check.

### M.1 Overall verdict

**NOT COMPLETE.** Of the 26 completion conditions in the governing prompt, the conditions bearing on Sections A–E, the Phase 0 ticket set, the Phase 1 mega-ticket decomposition, the full-template normalization of every ticket across all 8 phases, the `Campaign scope` column in Section G, and a first cycle of named substantive audits-and-fixes (B0 separation, recovery conditionality, E-O1/E-Q separation, Regime-D alternate-K propagation, temporal-blocker wiring, Appendix A traceability, originality-before-closure ordering, and exact-architecture-name usage) are satisfied in this revision. **All 8 phases are fully reconstructed at the template-format level (182/182 tickets), Section G now carries the `Campaign scope` column, and 8 real, evidenced defects found by this stage's audits have been fixed** (2 real dependency-graph defects, 1 content-conflation defect, 2 traceability gaps, 3 propagation gaps, 1 internal-consistency conflation, and 8 invented architecture-type names). Diagram/matrix regeneration beyond caption updates, the remaining 3 audit cycles, and a full scientific/architectural re-derivation of every ticket's substance against the complete authority corpus remain explicitly out of scope for this staged revision. No claim is made that the whole-document reconstruction — in the sense of the full 26-condition bar — is finished.

### M.2 Checks performed and their results

- **[PASS] Only `docs/MASTER_TICKET_LOG.md` modified.** No edit was made to `docs/Journal_Extension_Master_Roadmap.md`, `docs/DATP Core Architecture.md`, source code, tests, configuration, hooks, agents, skills, workflows, commands, datasets, checkpoints, outputs, or results. No temporary, scratch, audit, or duplicate ticket-log file was created.
- **[PASS] Both authority documents read in full for this revision.** `Journal_Extension_Master_Roadmap.md` (620 lines) and `DATP Core Architecture.md` (2771 lines) were read completely, not from excerpts or summaries, before any edit in this revision.
- **[PASS] Section A–E rewrite.** All five sections rewritten; Section D and E headings renamed to match the mandated structure; controlled vocabularies (ticket types, scientific-execution classification, campaign scope, protocol track) stated explicitly with an explicit ban on compound ticket types; the six distinct operational concepts (resume/recovery/retry/correction/recomputation/new-attempt-vs-new-campaign) enumerated in Section B; the anti-rerun rule stated in both Section B and Section E.
- **[PASS] Phase 0 index/body one-to-one correspondence.** All 26 Phase 0 rows in Section G correspond to exactly one Section H body each, verified by direct text search (`grep`) for `^#### P0-T0[0-9]{2}` returning exactly 26 matches in strictly ascending numeric order between the Phase 0 and Phase 1 headings, with no duplicate ID and no ID appearing outside that range.
- **[PASS] Phase 0 physical body ordering.** P0-T001 through P0-T026 appear in strict ascending numeric order in Section H, immediately after the "### Phase 0" heading and immediately before the "### Phase 1" heading; no Phase 0 body appears elsewhere in the document.
- **[PASS] Phase 0 complete ticket template.** Every one of the 26 Phase 0 tickets uses the full 38-field template (verified by direct construction in this revision); no ticket in Phase 0 retains the prior compact `**Metadata.**` line. A direct text search for `\*\*Metadata\.\*\*` returns 101 matches, but every match falls strictly after the Phase 1 heading (first match at the P1-T001 body); zero matches fall within the Phase 0 range (between the "### Phase 0" and "### Phase 1" headings in Section H). This confirms Phase 0 is fully converted and confirms, as expected and out of scope for this revision, that every Phase 1–7 ticket still uses its prior compact metadata line.
- **[PASS] Phase 0 explicit dependency existence and acyclicity.** Every `Dependencies`/`Blocks` reference among P0-T001–P0-T026 resolves to an existing ticket ID within the same set or to the single named downstream gate `P1-T001`; the graph P0-T001 → P0-T002 → {P0-T003, P0-T005, P0-T007, P0-T008, P0-T009} → … → P0-T026 → P1-T001, together with the parallel P0-T016 → {P0-T017…P0-T021} → {P0-T022…P0-T025} branch, contains no cycle (verified by manual topological trace during construction).
- **[PASS] Phase 0 controlled-vocabulary compliance.** Every Phase 0 ticket's `Ticket type` is a single atomic value from the Section D list (`foundation`, `architecture`, `agent-governance`, `skill`, `hook`, `command`); every `Scientific-execution classification` is `PLANNING_ONLY`; every `Campaign scope` is `NONE`; no compound type, no invalid classification value, and no combined campaign scope appears in Phase 0.
- **[PASS] Removal of vague dependency prose from Phase 0.** A direct text search for `all Phase 1 tickets`, `all implementation tickets`, and `downstream Phase 1 tickets` across the whole document returns zero matches; the Phase 0 rows in Section G and bodies in Section H that previously carried this prose now carry explicit ticket IDs or a single named gate ticket.
- **[PASS] Removal of stale numbered cross-references from Phase 0.** A direct text search for `this backlog §1` through `this backlog §29` and `this backlog §7` returns zero matches anywhere in the document; Phase 0 authority references now cite only verified `Arch §`/`Road §` sections or the lettered sections (A–M) of this document.
- **[PASS] Misplaced-body relocation.** P2-T021/P2-T022/P2-T023 and P4-T023/P4-T024/P4-T025/P4-T026 no longer appear inside Section F; each now appears exactly once in Section H at its correct phase location, verified by a direct text search for `^#### P2-T02[123]` and `^#### P4-T02[3456]` returning exactly one match each, both inside Section H.
- **[PASS] Phase 1 mega-ticket decomposition.** `P1-T010`, `P1-T041`, `P1-T047`, and `P1-T048` no longer exist anywhere in the document (verified by a direct text search for `P1-T010|P1-T041|P1-T047|P1-T048` returning zero matches outside of explicit historical retirement notes in the front matter, Section F, Section L, and this section). Twenty replacement/renumbered tickets `P1-T051`–`P1-T070` exist, each appearing exactly once in Section G and exactly once in Section H, verified by a direct text search for `^#### P1-T0[0-9]{2}` returning exactly 66 matches for the whole of Phase 1 (46 surviving originals + 20 new/renumbered). Bodies are physically grouped as ascending runs (P1-T001–P1-T009, P1-T011–P1-T040, P1-T042–P1-T046, P1-T049–P1-T050, P1-T051–P1-T070) rather than one single ascending sequence — each new/renumbered block sits immediately adjacent to its retired parent ticket's former position — with the renumbered gate `P1-T070` as the final Phase 1 body before the Phase 2 heading.
- **[PASS] Phase 1 full-template normalization.** All 66 Phase 1 tickets now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 1 line range of Section H (between the "### Phase 1" and "### Phase 2" H-section headings) returns zero matches, confirming no Phase 1 ticket retains the prior compact line. The 46 tickets carried over from the original Phase 1 set were rewritten to the full template without changing their IDs, titles, ownership, or scientific meaning; only `Depends`/`Blocks` fields referencing a retired ID were updated. **Correction:** the initial Stage 3 pass missed `P1-T070` (the gate ticket itself); this was caught during Stage 4 verification and fixed before this PASS mark was finalized — see the Section L Stage 4 self-correction note.
- **[PASS] Phase 1 decomposition cross-reference correctness.** Every surviving ticket that depended on a retired ID (`P0-T006`, `P1-T008`, `P1-T035`, `P1-T036`, `P1-T039`, `P1-T042`, `P1-T043`, `P1-T046`, `P1-T049`, `P1-T050`, and the legacy `P2-T001`/`P3-T005`) now references an explicit, existing replacement ID in both its Section G row and its Section H body; the `K` traceability matrix and `I` diagram gate-label were updated to the renumbered gate `P1-T070`.
- **[PASS] All Phase 1 tickets use the mandatory template; no new compound ticket type introduced.** All 66 of `P1-T001`–`P1-T070` use the full 38-field template and a single atomic `Ticket type` value (`domain`, `configuration`, `application`, `infrastructure`, `architecture`, `reporting`, `telemetry`, `persistence`, `composition`, `cli`, or `test-support`); none uses a compound type such as the retired `domain/application` or `composition/CLI`.
- **[PASS] Phase 2 full-template normalization.** All 23 Phase 2 tickets (`P2-T001`–`P2-T023`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 2 line range of Section H (between the second "### Phase 2" and the "### Phase 3" H-section headings) returns zero matches. `P2-T001`–`P2-T020` were rewritten from the prior compact line without changing IDs, dependencies, or scientific content; `P2-T021`–`P2-T023` already used the full template from their earlier relocation and needed no rewrite. Three parallel drafting subagents were used for `P2-T001`–`P2-T020`, each given a disjoint, non-overlapping batch and instructed to return converted text only (no file edits); every returned batch was read and checked against the mandatory field order before being applied via direct edits in this session, so no concurrent-write risk was introduced.
- **[PASS] Phase 2 ticket count and dependency graph unchanged.** Phase 2 contains no overloaded ticket requiring a split; all 23 ticket IDs, and every `Dependencies`/`Blocks` edge, are identical to the prior revision's Section G rows, verified by direct comparison during the conversion.
- **[PASS] Phase 3 full-template normalization.** All 11 Phase 3 tickets (`P3-T001`–`P3-T011`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 3 line range of Section H returns zero matches. Three parallel drafting subagents were used, each given a disjoint, non-overlapping batch and instructed to return converted text only (no file edits); the `ANCHOR_CAMPAIGN_ALLOWED` scientific-execution classification on `P3-T007`/`P3-T008`/`P3-T010` and the Phase 3 gate note on `P3-T011` were verified preserved exactly before the batches were applied via direct edits in this session.
- **[PASS] Phase 3 ticket count and dependency graph unchanged.** Phase 3 contains no overloaded ticket requiring a split; all 11 ticket IDs, and every `Dependencies`/`Blocks` edge, are identical to the prior revision's Section G rows, verified by direct comparison during the conversion.
- **[PASS] Combined Phase 0–3 zero-Metadata re-verification.** Immediately after applying the Phase 3 conversion, a single grep across the full Phase 0–3 H-section line range (not a narrower per-phase range, learning from the Stage 4 self-correction) confirmed zero remaining `**Metadata.**` lines, and separately confirmed 66/66, 23/23, and 11/11 body/G-index count matches for Phases 1, 2, and 3 respectively with zero duplicate IDs.
- **[PASS] Phase 4 full-template normalization.** All 26 Phase 4 tickets (`P4-T001`–`P4-T026`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 4 line range of Section H returns zero matches. `P4-T001`–`P4-T022` were rewritten from the prior compact line without changing IDs, dependencies, scientific-execution classification, or scientific content; `P4-T023`–`P4-T026` already used the full template from their earlier relocation and needed no rewrite. Five drafting subagents were used (one dispatched first, four dispatched together in a single parallel batch), each given a disjoint, non-overlapping batch and instructed to return converted text only (no file edits); every returned batch was read and checked against the mandatory field order before being applied via direct edits in this session, so no concurrent-write risk was introduced.
- **[PASS] Phase 4 ticket count and dependency graph unchanged.** Phase 4 contains no overloaded ticket requiring a split; all 26 ticket IDs, and every `Dependencies`/`Blocks` edge (including `P4-T022`'s twenty-ticket dependency list), are identical to the prior revision's Section G rows, verified by direct comparison during the conversion.
- **[PASS] Combined Phase 0–4 zero-Metadata re-verification.** Immediately after applying the Phase 4 conversion (before writing any front-matter/Section-F/Section-L/Section-M completion claim, per the Stage 4/5 discipline), a single grep across the full Phase 0–4 H-section line range confirmed zero remaining `**Metadata.**` lines, and separately confirmed 26/26, 66/66, 23/23, 11/11, and 26/26 body/G-index count matches for Phases 0 through 4 respectively with zero duplicate IDs across the combined P0–P4 range.
- **[PASS] Phase 5 full-template normalization.** All 9 Phase 5 tickets (`P5-T001`–`P5-T009`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 5 line range of Section H returns zero matches. The Phase 5 go/no-go gate note on `P5-T009` was verified preserved exactly.
- **[PASS] Phase 6 full-template normalization.** All 9 Phase 6 tickets (`P6-T001`–`P6-T009`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 6 line range of Section H returns zero matches. The `JOURNAL_CAMPAIGN_ALLOWED` bolded scientific-execution classification on `P6-T002`–`P6-T007` and the Phase 6 acceptance-gate note on `P6-T009` were verified preserved exactly. A `Campaign scope` drafting gap on four tickets (`P6-T001`, `P6-T003`, `P6-T004`, `P6-T005`, left as "not specified in legacy line" by the drafting subagent) was caught during review and corrected to `JOURNAL` — consistent with the Phase 6 phase-wide note — before the edit was applied.
- **[PASS] Phase 7 full-template normalization.** All 12 Phase 7 tickets (`P7-T001`–`P7-T012`) now use the complete 38-field template; a direct text search for `\*\*Metadata\.\*\*` within the Phase 7 line range of Section H returns zero matches. `P7-T012` already used the full template from an earlier relocation and required no rewrite. The backlog-closure gate note on `P7-T011`, its eight-ticket dependency list, and its `Blocks: —`/terminal-node status were verified preserved exactly.
- **[PASS] Phase 5/6/7 ticket counts and dependency graphs unchanged.** None of the three phases contains an overloaded ticket requiring a split; all 30 ticket IDs, and every `Dependencies`/`Blocks` edge, are identical to the prior revision's Section G rows, verified by direct comparison during the conversion.
- **[PASS] Combined Phase 0–7 (whole-document) zero-Metadata re-verification.** Immediately after applying all seven Stage 7 subagent batches (before writing any front-matter/Section-F/Section-L/Section-M completion claim, per the Stage 4/5/6 discipline), a single grep across the full Section H range (Phase 0 heading through the Section I heading) confirmed zero remaining `**Metadata.**` lines and exact body/G-index count matches for all 8 phases in one pass: P0 26/26, P1 66/66, P2 23/23, P3 11/11, P4 26/26, P5 9/9, P6 9/9, P7 12/12 — 182/182 total, zero duplicate ticket IDs anywhere in the document.
- **[PASS] `Campaign scope` column added to Section G.** All 182 rows now carry a `Scope` column, mechanically extracted from each ticket's own Section H `Campaign scope` field via a scripted awk extraction (not manually transcribed, to avoid transcription error); the extracted distribution (P0/P1: `NONE` × 92; P2/P3: `ANCH` × 34; P4/P5/P6: `JOUR` × 44; P7: `POST` × 12) exactly matches the expected per-phase pattern with no anomalies. 4 pre-existing Section G/H title mismatches (`P3-T008`, `P6-T007`, `P7-T005`, `P7-T006`, `P7-T010`) were corrected in the same pass.
- **[PASS] B0 centralized-branch audit performed; 1 real defect found and fixed.** A dedicated read-only audit subagent (datp-protocol-guardian persona) inspected every B0-related ticket against `docs/DATP Core Architecture.md` and `docs/Journal_Extension_Master_Roadmap.md`. Verdict: PARTIAL — B0's scientific identity separation from FedAvg/B1–B4 is otherwise correctly and repeatedly enforced, but `P2-T012`'s `Dependencies`/`Blocks`/`Downstream consumers` had drifted from Section G's untouched original graph during the earlier Phase 2 conversion, wrongly wiring B0's raw training ticket into the shared anchor evaluation ticket `P2-T016` instead of B0's own checkpoint ticket `P2-T021`; `P2-T016`'s `Dependencies` correspondingly cited `P2-T012` instead of `P2-T023`. Both corrected to match Section G, independently confirmed by direct inspection of both ticket bodies before editing (not merely trusting the subagent's claim).
- **[PASS] Recovery-conditionality audit performed; 1 real internal conflation found and fixed.** A dedicated read-only audit subagent (reproducibility-auditor persona) confirmed every activation condition, the `NOT_APPLICABLE` fallback, the no-automatic-OOM rule, `RunIdentity` invariance, and the retry/recompute distinction are correctly stated in `P3-T008`/`P6-T007`. Verdict: PARTIAL — both tickets stated a blanket "mint new `ExecutionAttemptId` on every resume," contradicting Architecture §17.3 (graceful-pressure-boundary resume continues the *same* attempt); corrected both tickets' `Implementation responsibilities` to distinguish the two cases.
- **[PASS] E-O1/E-Q separation audit performed; verdict FAIL, both findings fixed.** A dedicated read-only audit subagent (threshold-policy-engineer persona) found Section K.1 misattributed all six `E-Q1`–`E-Q6` rows to `P4-T020` instead of `P4-T023`, and that `P4-T020`'s own body substantively conflated mandatory E-O1 content with optional E-Q1–E-Q6 content across six fields, contradicting its own Objective. Both corrected: K.1's six rows now cite `P4-T023`; `P4-T020` now carries only E-O1-scoped content.
- **[PASS] Regime-D alternate-K identity audit performed; verdict PARTIAL, propagation gaps fixed.** A dedicated read-only audit subagent (experiment-engineer persona) confirmed the alternate-K rule (new `ClientPartitionSpec`/`PartitionIdentity`/feasibility artifact per candidate, never overwrite/retry/relabel) is correctly stated in the campaign-execution ticket `P6-T004`, but was absent from `P4-T014` (the implementation ticket that constructs the governed objects) and only partially present in `P4-T013`; `P5-T004` stated immutability but not per-candidate artifact distinctness. All three gaps closed with targeted additions to the specific fields the audit identified.
- **[PASS] Temporal-blocker dependency-wiring audit (manual, script-assisted) performed; 1 real gap found and fixed.** A full mechanical Depends/Blocks graph-symmetry script (Python) was run across all 182 Section G rows, filtered to exclude the documented same-phase gate-aggregation convention; found `P4-T024` (temporal-blocker resolution) explicitly names `P4-T019` (E-B1 temporal MVE) in its `Blocks` field with no transitive path back, while `P4-T019`'s own `Dependencies`/`Preconditions` never listed `P4-T024`. Fixed in both Section G and Section H.
- **[PASS] Appendix A traceability audit performed; verdict FAIL, both findings fixed.** A dedicated read-only audit subagent (claim-evidence-auditor persona) found `P4-T025` (Appendix A) explicitly blocks `P7-T011` (backlog-closure gate) but `P7-T011`'s `Dependencies`/`Preconditions` never listed it — a genuine gate-integrity gap, since `P7-T011` must verify reviewer loophole `L04` (which Appendix A defends) is closed. Fixed by adding `P4-T025` to `P7-T011`'s dependency fields in both Section G and Section H, and by citing the `P5-T006` output inventory (including Appendix A) explicitly in `P7-T009`'s `Objective`/`Inputs`.
- **[PASS] Phase 7 originality-before-closure ordering audit performed; verdict PASS, no fix needed.** A dedicated read-only audit subagent (literature-novelty-auditor persona) confirmed `P7-T012` was already a documented precondition of `P7-T011` in Section G, Section H, and Section F prose; the "reordering" concern in the prior revision's legacy note was a documentation-wording ambiguity, not a graph-logic defect. The stale legacy-note wording was corrected.
- **[PASS] Exact-architecture-name audit performed; verdict PARTIAL, 8 confirmed defects fixed after independent re-verification.** A dedicated read-only audit subagent (architecture-cleaner persona) sampled 30 tickets across all 8 phases against `docs/DATP Core Architecture.md`'s full type inventory and reported 8 invented/non-matching type names. Before applying any correction, this session independently re-ran direct `grep` verification of every claimed name against the architecture document (not merely trusting the subagent's report) — all 8 were confirmed absent from the architecture document under the claimed spelling, and the subagent's proposed correct names were confirmed present verbatim. Corrected `P2-T009`, `P2-T011`, `P2-T012`, `P2-T013`, `P2-T014`, `P4-T019`, `P4-T021`. `P5-T005`'s three-way reuse-ledger vocabulary was deliberately **not** renamed (used consistently across three tickets as a plausible journal-specific elaboration of the architecture's `ReuseDecisionKind`); an explicit relationship annotation was added instead, since a blanket rename of a possibly-intentional, widely-used vocabulary without a dedicated architecture-level decision would itself be a scope overreach.
- **[NOT COMPLETE — deferred] Diagram/matrix regeneration in Sections I/J/K beyond caption updates and the K.1 E-Q correction.** Section I/J's stale "[LEGACY]" captions were replaced with verification notes (gate-node IDs and lineage-diagram labels were cross-checked against Section H and confirmed accurate), but the Mermaid diagrams themselves were not redrawn. Section K.1's `B0` row still cites only `P2-T012` in its "Implementation ticket(s)" column, omitting `P2-T021`–`P2-T023` (a known, disclosed gap per the B0 audit's `[NOTE]` finding, not yet corrected).
- **[NOT COMPLETE — deferred] Full scientific/architectural re-derivation of every ticket's substance against the complete authority corpus.** This stage audited 8 *specifically named* dimensions (matching the prior revision's own Section M "NOT COMPLETE" list) plus fixed what those audits found; this is not equivalent to an exhaustive, whole-document, line-by-line re-derivation of all 182 tickets against the full 620-line roadmap and 2771-line architecture document. The pre-existing, document-wide Depends/Blocks graph-symmetry pattern (49 non-gate-aggregation edges found by the full mechanical script pass, of which only 2 fell within this stage's specifically named audit scope and were fixed) remains otherwise unaddressed; it reflects an undocumented "Depends = nearest causal predecessor, Blocks = broader downstream-consumer annotation" convention that predates this entire reconstruction effort.
- **[NOT COMPLETE — deferred] The remaining 3 of the "four full audit cycles" requested by the governing prompt.** This stage constitutes one audit-fix-verify cycle (parallel audit → independent re-verification → targeted fix → mechanical re-check); three further cycles remain, per the original governing prompt's request, before that specific completion condition is satisfied.
- **[NOT COMPLETE — deferred] B0-row Implementation-ticket completeness in Section K.1, the B0 audit's `[MINOR]` findings on `P6-T002`'s annotation style, and the `P4-T023` Section G/H `Blocks` field desync (`P5-T002` present in H, absent in G).** All three were identified as optional/minor by their respective audits and were not fixed in this stage; they do not block any acceptance criterion currently in force.
- **[PASS] No result-seeking rerun language introduced or left uncorrected anywhere in this revision.** Sections A, B, C, D, E, and all 182 tickets across Phases 0–7 contain no instance of "corrective rerun," "rejected outcome," or similar phrasing describing a preferred-direction rerun; Section B explicitly bans it, and the reformatted Phase 6 gate ticket `P6-T009` and Phase 7 audit ticket `P7-T008` explicitly restate the anti-suppression/anti-rerun and null/mixed-retention rules in their reformatted bodies.

### M.3 Mechanical counts (this revision's scope: Sections A–E, the full-template normalization of all 182 tickets, the Section G `Campaign scope` column, and the Stage 8 audit-and-fix cycle)

- Duplicate Phase 0 ticket IDs: 0.
- Phase 0 index-only entries (no Section H body): 0.
- Phase 0 body-only entries (no Section G row): 0.
- Misordered Phase 0 bodies: 0.
- Phase 0 tickets missing a mandatory template field: 0.
- Phase 0 index/body title mismatches: 0.
- Phase 0 vague dependency/blocks entries ("all Phase 1 tickets" or equivalent): 0.
- Phase 0 self-dependencies: 0.
- Phase 0 dependency cycles: 0.
- Phase 0 invalid controlled-vocabulary values: 0.
- Stale "this backlog §<number>" references anywhere in the document: 0.
- Misplaced ticket bodies remaining in Section F: 0 (both relocations completed).
- Remaining references to a retired Phase 1 ticket ID (`P1-T010`, `P1-T041`, `P1-T047`, `P1-T048`, or the old gate ID `P1-T051` used as the gate) outside of explicit historical retirement notes: 0.
- Phase 1 tickets (all 66, `P1-T001`–`P1-T070`) missing a mandatory template field: 0.
- Phase 1 duplicate ticket IDs across the full 66-ticket set: 0 (verified by exactly 66 matches for `^#### P1-T0[0-9]{2}` with no repeated number).
- Phase 1 index-only or body-only entries among `P1-T001`–`P1-T070`: 0.
- Phase 1 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 2 tickets (all 23, `P2-T001`–`P2-T023`) missing a mandatory template field: 0.
- Phase 2 duplicate ticket IDs: 0 (verified by exactly 23 matches for `^#### P2-T0[0-9]{2}` with no repeated number).
- Phase 2 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 2 ID/dependency changes introduced by the template conversion: 0 (all `Dependencies`/`Blocks` edges identical to the prior revision).
- Phase 3 tickets (all 11, `P3-T001`–`P3-T011`) missing a mandatory template field: 0.
- Phase 3 duplicate ticket IDs: 0 (verified by exactly 11 matches for `^#### P3-T0[0-9]{2}` with no repeated number).
- Phase 3 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 3 ID/dependency changes introduced by the template conversion: 0 (all `Dependencies`/`Blocks` edges identical to the prior revision).
- Combined Phase 0–3 `**Metadata.**` lines remaining in Section H: 0 (verified in one combined grep pass across all four reconstructed phases).
- Phase 4 tickets (all 26, `P4-T001`–`P4-T026`) missing a mandatory template field: 0.
- Phase 4 duplicate ticket IDs: 0 (verified by exactly 26 matches for `^#### P4-T0[0-9]{2}` with no repeated number).
- Phase 4 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 4 ID/dependency changes introduced by the template conversion: 0 (all `Dependencies`/`Blocks` edges identical to the prior revision, including `P4-T022`'s twenty-ticket dependency list).
- Combined Phase 0–4 `**Metadata.**` lines remaining in Section H: 0 (verified in one combined grep pass across all five reconstructed phases).
- Phase 5 tickets (all 9, `P5-T001`–`P5-T009`) missing a mandatory template field: 0.
- Phase 5 duplicate ticket IDs: 0 (verified by exactly 9 matches for `^#### P5-T0[0-9]{2}` with no repeated number).
- Phase 5 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 5 ID/dependency changes introduced by the template conversion: 0.
- Phase 6 tickets (all 9, `P6-T001`–`P6-T009`) missing a mandatory template field: 0.
- Phase 6 duplicate ticket IDs: 0 (verified by exactly 9 matches for `^#### P6-T0[0-9]{2}` with no repeated number).
- Phase 6 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 6 tickets with an unresolved/inconsistent `Campaign scope` field after correction: 0 (four tickets initially drafted without an explicit value were corrected to `JOURNAL` before the edit was applied, per the Section L Stage 7 note).
- Phase 6 ID/dependency changes introduced by the template conversion: 0.
- Phase 7 tickets (all 12, `P7-T001`–`P7-T012`) missing a mandatory template field: 0.
- Phase 7 duplicate ticket IDs: 0 (verified by exactly 12 matches for `^#### P7-T0[0-9]{2}` with no repeated number).
- Phase 7 tickets retaining the prior compact `**Metadata.**` line: 0.
- Phase 7 ID/dependency changes introduced by the template conversion: 0 (including `P7-T011`'s eight-ticket dependency list and terminal `Blocks: —` status).
- Combined Phase 0–7 (whole-document) `**Metadata.**` lines remaining in Section H: 0 (verified in one combined grep pass across all 8 phases).
- Whole-document duplicate ticket IDs across all 8 phases: 0 (verified by `sort | uniq -d` returning no output across the full `^#### P[0-9]-T0[0-9]{2}` set).
- Whole-document body/G-index count total: 182/182 (26+66+23+11+26+9+9+12 on both sides).
- **Not counted in this revision (deferred to future audit stages):** priority/type/scientific-execution/campaign-scope mismatches against the roadmap and architecture documents (as opposed to internal phase-wide-note consistency, which was checked), roadmap-ID mismatches, dependency/block-reference validity beyond ID-existence (except the 3 specific edges fixed in Stage 8), invalid architecture names beyond the 30-ticket sample checked in Stage 8, unmapped roadmap experiments, unmapped architecture contracts, unmapped artifact families, and stale diagram references. Reporting a zero here would be a false claim; these counts require a dedicated scientific/architectural re-audit stage, not merely template-format conversion.
- Stage 8 fixes applied: 2 dependency-graph defects (`P2-T012`/`P2-T016`, `P4-T019`/`P4-T024`); 1 content-conflation defect (`P4-T020`); 1 index misattribution (Section K.1, 6 rows); 2 traceability gaps (`P7-T011`/`P4-T025`, `P7-T009`/`P5-T006`); 3 propagation gaps (`P4-T013`, `P4-T014`, `P5-T004`); 1 internal-consistency conflation across 2 tickets (`P3-T008`, `P6-T007`); 8 invented architecture-type names across 7 tickets (`P2-T009`, `P2-T011`, `P2-T012`, `P2-T013`, `P2-T014`, `P4-T019`, `P4-T021`); 1 explanatory annotation added without renaming (`P5-T005`). Total: 18 distinct corrections across 15 tickets plus Section G/I/J/K/L/M meta-sections.

### M.4 Remaining blockers

- No genuine authority blocker was encountered while reconstructing Sections A–E and Phase 0; Phase 0 is pure tooling/governance scaffolding with no scientific content.
- Genuine authority blockers already recorded in the reformatted tickets — for example the chronological temporal training/calibration allocation (P4-T024, whose `TemporalProtocolSpec`/`FeasibilityGateDecision` remain unresolved pending authority evidence, consumed downstream by P5-T004 and P6-T004) — remain open and are not resolved or hidden by this revision; they will be re-verified when each phase's substance (as opposed to its template format) is re-audited. The Phase 2 `ANCHOR_CHECKPOINT_PROTOCOL_UNRESOLVED` blocker (historical anchor checkpoint schedule/selection evidence) is now explicitly carried in the reformatted P2-T001/P2-T002/P2-T010 bodies, and in the reformatted P3-T002/P3-T010, P5-T001, and P7-T004 bodies via their dependency chain on the anchor checkpoint protocol resolution, and remains open pending recovery.

### M.5 Honesty confirmation

- No authority file (`docs/Journal_Extension_Master_Roadmap.md`, `docs/DATP Core Architecture.md`) was changed.
- No implementation file (source, tests, configuration, hooks, agents, skills, workflows, commands, datasets, checkpoints, outputs, results) was changed.
- No scientific execution occurred.
- No temporary, scratch, audit, or duplicate file was created; only `docs/MASTER_TICKET_LOG.md` was edited, in place.
- Weak/null/mixed/unfavorable outcomes cannot trigger result-seeking execution under the rules stated in this revision's Sections B and E.
- Phase 0 is structurally ready (tooling/governance scaffolding fully specified per ticket) but no repository implementation ticket has actually been executed; every ticket's `Status` field across all 8 phases remains `NOT_STARTED`, consistent with Section C.
- **This revision is explicitly `NOT COMPLETE`** against the full 26-condition bar of the governing prompt. It completes the full-template normalization of all 182 tickets (Phases 0–7), adds the `Campaign scope` column to Section G, and completes a first audit-and-fix cycle over 8 specifically named substantive dimensions, with 18 distinct, independently-re-verified corrections applied across 15 tickets. It leaves diagram/matrix regeneration beyond caption updates, 3 further audit cycles, and a full scientific/architectural re-derivation of every ticket's substance against the complete authority corpus explicitly marked as pending future work.

---

*End of master ticket log.*
