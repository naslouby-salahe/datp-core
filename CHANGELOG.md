# CHANGELOG — DATP Journal Extension (`datp-core`)

> Agent-progress tracker for the scratch build. Read the dashboard first, then the
> phase/ticket tables, then the latest update. Plan of record:
> [MASTER_TICKET_LOG.md](MASTER_TICKET_LOG.md).
>
> **This is not a scientific result file.** It tracks implementation progress,
> tests, blockers, and decisions only. It must never contain experimental result
> claims, CI values, or metric outcomes. Status values: `Not Started` ·
> `In Progress` · `Blocked` · `Done` · `Skipped` · `Split` · `Merged` · `Reopened`.

---

## 1. Current Status Dashboard

```text
Current phase:        Phase 0 — Protocol, Scope & Architecture Freeze (complete)
Current ticket:       None — Phase 0 closed by P0-T11 go/no-go = Go
Overall progress:     11 / 82 tickets Done (13%)
Completed tickets:    11
In-progress tickets:  0
Blocked tickets:      0
Last completed ticket: P0-T11
Next ticket:          P1-T01 (Phase 1 not started; requires explicit authorization)
Last tests run:       pytest tests/unit -q — 32 passed, 0 failed
Current blocker:      None
Last update:          2026-07-09 — Phase 0 complete, go/no-go signed Go
```

---

## 2. Phase Progress Table

| Phase | Total Tickets | Done | In Progress | Blocked | Status | Exit Gate |
|---|---|---|---|---|---|---|
| 0 — Protocol/scope/architecture freeze | 11 | 11 | 0 | 0 | Done | P0-T11 go/no-go signed (Go) |
| 1 — Scratch foundation | 10 | 0 | 0 | 0 | Not Started | P1-T10 foundation tests green |
| 2 — Anchor reproduction pipeline | 11 | 0 | 0 | 0 | Not Started | P2-T11 frozen anchor + scores |
| 3 — Core threshold policies & metrics | 11 | 0 | 0 | 0 | Not Started | P3-T11 B0–B4 + metrics validated |
| 4 — Threshold variants & comparators | 9 | 0 | 0 | 0 | Not Started | P4-T09 variants reuse scores |
| 5 — Mechanism analyses | 8 | 0 | 0 | 0 | Not Started | P5-T08 mechanisms from fixtures |
| 6 — External dataset & stress tests | 12 | 0 | 0 | 0 | Not Started | P6-T12 D/C frozen, stress separated |
| 7 — Temporal, final audit & freeze | 10 | 0 | 0 | 0 | Not Started | P7-T10 readiness report signed |
| **Total** | **82** | **11** | **0** | **0** | **In Progress** | — |

---

## 3. Ticket Progress Table

| Ticket | Phase | Status | Last Update | Tests Run | Files Changed | Notes |
|---|---|---|---|---|---|---|
| P0-T01 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_scope_boundaries.py` (2 passed) | `docs/protocol/identity_lock.md`, `docs/protocol/scope_boundaries.md`, `tests/unit/test_scope_boundaries.py` | Scientific scope & identity freeze |
| P0-T02 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_claim_hierarchy.py` (3 passed) | `docs/protocol/claim_hierarchy.md`, `tests/unit/test_claim_hierarchy.py` | Claim hierarchy & confirmatory isolation |
| P0-T03 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_regimes_doc.py` (3 passed) | `docs/protocol/regimes.md`, `tests/unit/test_regimes_doc.py` | Regime definitions freeze |
| P0-T04 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_policies_doc.py` (4 passed) | `docs/protocol/policies.md`, `tests/unit/test_policies_doc.py` | Threshold-policy & comparator nomenclature |
| P0-T05 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_artifact_contracts_doc.py` (3 passed) | `docs/protocol/artifact_contracts.md`, `data/README.md`, `checkpoints/README.md`, `outputs/README.md`, `results/README.md`, `tests/unit/test_artifact_contracts_doc.py` | Dataset & artifact/directory contracts |
| P0-T06 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_naming_conventions.py` (3 passed) | `docs/protocol/naming_conventions.md`, `tests/unit/test_naming_conventions.py` | Config/suite/experiment-ID naming |
| P0-T07 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_seed_plan_doc.py` (3 passed) | `docs/protocol/seed_plan.md`, `tests/unit/test_seed_plan_doc.py` | Seed plan freeze |
| P0-T08 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_testing_contract.py` (2 passed) | `docs/protocol/testing_contract.md`, `tests/unit/test_testing_contract.py` | Testing contract & test-pyramid |
| P0-T09 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_reuse_policy_doc.py` (3 passed) | `docs/protocol/reuse_policy.md`, `tests/unit/test_reuse_policy_doc.py` | Reuse/caching + raw-data placement |
| P0-T10 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_behavioral_reference.py` (2 passed) | `docs/protocol/behavioral_reference.md`, `tests/unit/test_behavioral_reference.py` | Old DATP behavioral-reference extraction |
| P0-T11 | 0 | Done | 2026-07-09 | `pytest tests/unit -q` (full suite) | `docs/protocol/structure_decision.md`, `docs/protocol/go_no_go.md`, `CHANGELOG.md`, `tests/unit/test_changelog_format.py` | Structure decision + changelog + go/no-go |
| P1-T01 | 1 | Not Started | — | — | — | Skeleton, pyproject, tooling, Makefile |
| P1-T02 | 1 | Not Started | — | — | — | Domain enums & metric registry |
| P1-T03 | 1 | Not Started | — | — | — | Seed-plan types |
| P1-T04 | 1 | Not Started | — | — | — | Typed config system |
| P1-T05 | 1 | Not Started | — | — | — | Canonical path resolver |
| P1-T06 | 1 | Not Started | — | — | — | Runtime utilities (determinism/hw/logging) |
| P1-T07 | 1 | Not Started | — | — | — | Manifest schema + writer/reader + no-overwrite |
| P1-T08 | 1 | Not Started | — | — | — | Preprocessing cache contract |
| P1-T09 | 1 | Not Started | — | — | — | CLI entrypoint & dataset registry |
| P1-T10 | 1 | Not Started | — | — | — | Test fixtures & CHANGELOG enforcement test |
| P2-T01 | 2 | Not Started | — | — | — | N-BaIoT loader & schema |
| P2-T02 | 2 | Not Started | — | — | — | N-BaIoT preprocessing & cache (**heavy**) |
| P2-T03 | 2 | Not Started | — | — | — | Physical-device partition builder |
| P2-T04 | 2 | Not Started | — | — | — | Benign train/cal/test split & manifest |
| P2-T05 | 2 | Not Started | — | — | — | Autoencoder architecture |
| P2-T06 | 2 | Not Started | — | — | — | FedAvg training loop (**heavy**) |
| P2-T07 | 2 | Not Started | — | — | — | Checkpoint save/select & freeze (**heavy**) |
| P2-T08 | 2 | Not Started | — | — | — | Score generation & contract (**heavy**) |
| P2-T09 | 2 | Not Started | — | — | — | B1/B2 anchor eval & 10-seed plan |
| P2-T10 | 2 | Not Started | — | — | — | Anchor smoke run & provenance |
| P2-T11 | 2 | Not Started | — | — | — | Anchor statistical gate (**heavy, gated**) |
| P3-T01 | 3 | Not Started | — | — | — | Federated quantile backbone |
| P3-T02 | 3 | Not Started | — | — | — | Threshold-policy interface & validation |
| P3-T03 | 3 | Not Started | — | — | — | B0 centralized reference |
| P3-T04 | 3 | Not Started | — | — | — | B1 shared threshold |
| P3-T05 | 3 | Not Started | — | — | — | B2 per-client threshold |
| P3-T06 | 3 | Not Started | — | — | — | B3 family-mean threshold |
| P3-T07 | 3 | Not Started | — | — | — | B4 cluster threshold (fingerprint+kmeans) |
| P3-T08 | 3 | Not Started | — | — | — | Prediction generation & operating points |
| P3-T09 | 3 | Not Started | — | — | — | Classification metrics (AUROC control) |
| P3-T10 | 3 | Not Started | — | — | — | Disparity metrics & aggregation |
| P3-T11 | 3 | Not Started | — | — | — | Threshold-policy equivalence tests |
| P4-T01 | 4 | Not Started | — | — | — | q-sensitivity sweep |
| P4-T02 | 4 | Not Started | — | — | — | Local-global shrinkage (τ-shrink) |
| P4-T03 | 4 | Not Started | — | — | — | Calibration-size fallback & ablation |
| P4-T04 | 4 | Not Started | — | — | — | Split/federated conformal B2-conf |
| P4-T05 | 4 | Not Started | — | — | — | B-FedStatsBenign statistics contract |
| P4-T06 | 4 | Not Started | — | — | — | B-FedStatsBenign matched-exceedance |
| P4-T07 | 4 | Not Started | — | — | — | B-LaridiFaithful disclosure guard |
| P4-T08 | 4 | Not Started | — | — | — | Threshold-only reuse (no-retrain) guard |
| P4-T09 | 4 | Not Started | — | — | — | Variant output contracts, tables & figures |
| P5-T01 | 5 | Not Started | — | — | — | Benign/attack CDF overlays & Ennio |
| P5-T02 | 5 | Not Started | — | — | — | Threshold-shift vs ΔFPR/ΔTPR surface |
| P5-T03 | 5 | Not Started | — | — | — | Cluster granularity, stability, ARI, ablation |
| P5-T04 | 5 | Not Started | — | — | — | JS-divergence vs benefit regression |
| P5-T05 | 5 | Not Started | — | — | — | P10 Macro-F1 & FPR-concentration |
| P5-T06 | 5 | Not Started | — | — | — | Alert-burden (gated on real/cited rate) |
| P5-T07 | 5 | Not Started | — | — | — | Mechanism figure/table export |
| P5-T08 | 5 | Not Started | — | — | — | Mechanism tests from fixtures |
| P6-T01 | 6 | Not Started | — | — | — | Edge-IIoTset loader & schema |
| P6-T02 | 6 | Not Started | — | — | — | Edge-IIoTset client-mapping feasibility |
| P6-T03 | 6 | Not Started | — | — | — | Edge-IIoTset preprocessing & cache (**heavy**) |
| P6-T04 | 6 | Not Started | — | — | — | Regime D splits & coverage gate |
| P6-T05 | 6 | Not Started | — | — | — | Regime D FedAvg train & score (**heavy**) |
| P6-T06 | 6 | Not Started | — | — | — | Regime D threshold ladder & comparator |
| P6-T07 | 6 | Not Started | — | — | — | CICIoT2023 file-level loader & B-a boundary |
| P6-T08 | 6 | Not Started | — | — | — | CICIoT2023 B-b rejection guard |
| P6-T09 | 6 | Not Started | — | — | — | Regime C Dirichlet builder & sweep (**heavy**) |
| P6-T10 | 6 | Not Started | — | — | — | FedProx impl & stress eval (**heavy**) |
| P6-T11 | 6 | Not Started | — | — | — | Model-personalization & absorption (**heavy**) |
| P6-T12 | 6 | Not Started | — | — | — | Stress-test reporting |
| P7-T01 | 7 | Not Started | — | — | — | Chronological split & temporal contract |
| P7-T02 | 7 | Not Started | — | — | — | Frozen vs one-shot recal & 3 outcomes (**heavy**) |
| P7-T03 | 7 | Not Started | — | — | — | BCa CI audit, Wilcoxon, Cliff's δ |
| P7-T04 | 7 | Not Started | — | — | — | Claim-gate logic |
| P7-T05 | 7 | Not Started | — | — | — | Claim-to-evidence map |
| P7-T06 | 7 | Not Started | — | — | — | Result curation (outputs→results) |
| P7-T07 | 7 | Not Started | — | — | — | Table/figure reproducibility checks |
| P7-T08 | 7 | Not Started | — | — | — | Full-suite dry run |
| P7-T09 | 7 | Not Started | — | — | — | Final audit: leakage/overwrite/provenance |
| P7-T10 | 7 | Not Started | — | — | — | Final implementation readiness report |

---

## 4. Latest Update Block

> Use the template in §14 for every future update. The most recent update goes
> at the top of §5 (Completed Work Log).

---

## 5. Completed Work Log

Newest first.

```text
## 2026-07-09 — P0-T11 — Repository structure decision, changelog format & go/no-go coding gate

Status:            Done
Summary:           Ratified the §5 structure decision as docs/protocol/structure_decision.md,
                    wrote docs/protocol/go_no_go.md recording the Go verdict, added the
                    changelog-format parser test, and closed out this changelog for all of
                    Phase 0.
Files changed:      docs/protocol/structure_decision.md (new), docs/protocol/go_no_go.md (new),
                    tests/unit/test_changelog_format.py (new), CHANGELOG.md (this file).
Tests added:        test_changelog_format.py::test_dashboard_fields_present,
                    ::test_status_enum_values, ::test_update_template_present,
                    ::test_no_experimental_claims_in_changelog.
Tests run:          pytest tests/unit -q — see full-suite count in §9.
Result:             Phase 0 exit gate signed Go. Phase 1 authorized but not started.
Artifacts created:  docs/protocol/structure_decision.md, docs/protocol/go_no_go.md.
Decisions made:     None new; ratifies D-002, D-003 (Decision Log §8).
Blockers:           None.
Risks:              None new.
Next ticket:        P1-T01 (not started; requires explicit Phase 1 authorization).
```

```text
## 2026-07-09 — P0-T10 — Old DATP behavioral-reference extraction

Status:            Done
Summary:           Extracted threshold-policy math, eligibility/fallback rule, CV(FPR)
                    formula, split semantics, checkpoint protocol, and AUROC role from
                    /home/naslouby/Projects/datp as behavior-only notes (no source paste, no
                    layout, no module-name inheritance).
Files changed:      docs/protocol/behavioral_reference.md (new),
                    tests/unit/test_behavioral_reference.py (new).
Tests added:        test_behavioral_reference.py::test_no_source_paths_copied,
                    ::test_no_backward_compat_language.
Tests run:          pytest tests/unit/test_behavioral_reference.py -q — 2 passed.
Result:             Behavioral reference locked; no structural/code inheritance introduced.
Artifacts created:  docs/protocol/behavioral_reference.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T11.
```

```text
## 2026-07-09 — P0-T09 — Reuse/caching principle & raw-data placement freeze

Status:            Done
Summary:           Locked the heavy-vs-cheap stage table, the six invalidation triggers, and
                    the data/raw symlink placement contract.
Files changed:      docs/protocol/reuse_policy.md (new), tests/unit/test_reuse_policy_doc.py
                    (new).
Tests added:        test_reuse_policy_doc.py::test_stage_classification_complete,
                    ::test_invalidation_triggers_listed, ::test_threshold_stage_not_marked_heavy.
Tests run:          pytest tests/unit/test_reuse_policy_doc.py -q — 3 passed.
Result:             Reuse/caching contract locked; enforced later by P4-T08 and P7-T09.
Artifacts created:  docs/protocol/reuse_policy.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T10.
```

```text
## 2026-07-09 — P0-T08 — Testing contract & test-pyramid freeze

Status:            Done
Summary:           Canonicalized the unit/integration/smoke/negative test taxonomy
                    (MASTER_TICKET_LOG.md §10) as a standalone doc with a coverage-of-contract
                    rule and named Phase-0 test files.
Files changed:      docs/protocol/testing_contract.md (new),
                    tests/unit/test_testing_contract.py (new).
Tests added:        test_testing_contract.py::test_every_subsystem_has_named_tests,
                    ::test_no_generic_add_tests_placeholder.
Tests run:          pytest tests/unit/test_testing_contract.py -q — 2 passed.
Result:             Testing contract locked as the authority for MASTER_TICKET_LOG.md §10.
Artifacts created:  docs/protocol/testing_contract.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T09.
```

```text
## 2026-07-09 — P0-T07 — Seed plan freeze

Status:            Done
Summary:           Locked the 10-seed set, the B1/B2/B0/B3/B4 pairing rule, the 5-seed
                    preliminary vs 10-seed main distinction, and the seed-extension honesty
                    rule (SB-21).
Files changed:      docs/protocol/seed_plan.md (new), tests/unit/test_seed_plan_doc.py (new).
Tests added:        test_seed_plan_doc.py::test_ten_paired_seeds,
                    ::test_seed_extension_rule_present, ::test_no_seed_dropping_allowed.
Tests run:          pytest tests/unit/test_seed_plan_doc.py -q — 3 passed.
Result:             Seed plan locked; feeds P1-T03 seed types and P2-T09 paired plan.
Artifacts created:  docs/protocol/seed_plan.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T08.
```

```text
## 2026-07-09 — P0-T06 — Config, experiment-suite & experiment-ID naming conventions

Status:            Done
Summary:           Locked the five config groups, the seven suite names, and the full
                    E-C1…E-Q6 experiment-ID-to-suite registry; stated config-key naming rules
                    (enum-backed, no raw policy strings, no "Ditto" hardcode).
Files changed:      docs/protocol/naming_conventions.md (new),
                    tests/unit/test_naming_conventions.py (new).
Tests added:        test_naming_conventions.py::test_experiment_ids_unique,
                    ::test_suite_names_map_to_known_experiments,
                    ::test_no_stale_policy_names_in_registry.
Tests run:          pytest tests/unit/test_naming_conventions.py -q — 3 passed.
Result:             Naming conventions locked; feeds P1-T04 config schemas.
Artifacts created:  docs/protocol/naming_conventions.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T07.
```

```text
## 2026-07-09 — P0-T05 — Dataset & artifact/directory contract definitions

Status:            Done
Summary:           Wrote per-dataset contracts (N-BaIoT, CICIoT2023, Edge-IIoTset; 12 fields
                    each) and the 20-class pipeline artifact contract table (producer,
                    consumers, manifest fields, reuse-validity key, read-only rule); added
                    stub READMEs for data/, checkpoints/, outputs/, results/.
Files changed:      docs/protocol/artifact_contracts.md (new), data/README.md (new),
                    checkpoints/README.md (new), outputs/README.md (new), results/README.md
                    (new), tests/unit/test_artifact_contracts_doc.py (new).
Tests added:        test_artifact_contracts_doc.py::test_every_artifact_has_manifest_fields,
                    ::test_readmes_exist, ::test_results_excludes_heavy_artifacts.
Tests run:          pytest tests/unit/test_artifact_contracts_doc.py -q — 3 passed.
Result:             Dataset/artifact contracts locked; concretely implemented by P1-T07.
Artifacts created:  docs/protocol/artifact_contracts.md, four README.md stubs.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T06.
```

```text
## 2026-07-09 — P0-T04 — Threshold-policy & comparator nomenclature freeze

Status:            Done
Summary:           Locked B0–B4, threshold variants (τ-shrink, calibration-size-aware
                    fallback, B2-conf), comparators (B-FedStatsBenign, B-LaridiFaithful), and
                    stress-test comparators (FedProx, Ditto/FedRep-AE/FedPer-AE), plus every
                    naming lock (no B5, no B3-LGS, B4 canonical K=3, no bare "Ditto").
Files changed:      docs/protocol/policies.md (new), tests/unit/test_policies_doc.py (new).
Tests added:        test_policies_doc.py::test_no_stale_labels, ::test_b0_not_in_causal_ladder,
                    ::test_b4_canonical_k_is_3, ::test_fallback_not_named_ditto.
Tests run:          pytest tests/unit/test_policies_doc.py -q — 4 passed.
Result:             Policy/comparator nomenclature locked; feeds P3/P4 implementations.
Artifacts created:  docs/protocol/policies.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T05.
```

```text
## 2026-07-09 — P0-T03 — Regime definitions freeze (A / B-a / B-b / C / D / D-temporal)

Status:            Done
Summary:           Locked all six regimes with role, client definition, purpose, threshold
                    policies, primary metric, and pass/fail/suppression rule; recorded the two
                    rejected-status labels (B_B_REJECTED_NO_METADATA,
                    TEMPORAL_REJECTED_NO_TIMESTAMPS).
Files changed:      docs/protocol/regimes.md (new), tests/unit/test_regimes_doc.py (new).
Tests added:        test_regimes_doc.py::test_all_regimes_have_role_and_passrule,
                    ::test_bb_marked_rejected, ::test_no_quantitative_bb_claim.
Tests run:          pytest tests/unit/test_regimes_doc.py -q — 3 passed.
Result:             Regime definitions locked; drives the Regime enum and P6 loaders/guards.
Artifacts created:  docs/protocol/regimes.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T04.
```

```text
## 2026-07-09 — P0-T02 — Claim hierarchy & confirmatory-endpoint isolation freeze

Status:            Done
Summary:           Locked the nine claim tiers with the singular Tier-1 confirmatory claim,
                    evidence/regime/metric/min-pass/fallback/reviewer-risk/placement fields
                    per tier, and the Tier-9 forbidden-claims list.
Files changed:      docs/protocol/claim_hierarchy.md (new),
                    tests/unit/test_claim_hierarchy.py (new).
Tests added:        test_claim_hierarchy.py::test_single_confirmatory_tier1,
                    ::test_tier9_forbidden_enumerated, ::test_no_supportive_marked_confirmatory.
Tests run:          pytest tests/unit/test_claim_hierarchy.py -q — 3 passed.
Result:             Claim hierarchy locked; feeds ClaimRole enum and P7-T04 claim gates.
Artifacts created:  docs/protocol/claim_hierarchy.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T03.
```

```text
## 2026-07-09 — P0-T01 — Scientific scope & identity freeze

Status:            Done
Summary:           Locked the fixed-encoder / sole-causal-variable / benign-only /
                    CV(FPR)-primary / AUROC-control / stress-outside-ladder identity
                    statements and the operational-FPR-equity fairness definition; enumerated
                    SB-01…SB-32 as a parseable, testable list.
Files changed:      docs/protocol/identity_lock.md (new), docs/protocol/scope_boundaries.md
                    (new), tests/unit/test_scope_boundaries.py (new).
Tests added:        test_scope_boundaries.py::test_all_SB_ids_present_and_unique,
                    ::test_forbidden_terms_absent.
Tests run:          pytest tests/unit/test_scope_boundaries.py -q — 2 passed.
Result:             Scientific identity locked; imported by all later P0 docs and by P1-T02.
Artifacts created:  docs/protocol/identity_lock.md, docs/protocol/scope_boundaries.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T02.
```

```text
## 2026-07-09 — Planning — MASTER_TICKET_LOG.md + CHANGELOG.md created

Status: Done
Summary: Authored the full 82-ticket master plan across 8 phases and this
         progress tracker. No implementation started.
Files changed: MASTER_TICKET_LOG.md (new), CHANGELOG.md (new).
Tests added: None (planning only).
Tests run: None.
Result: Plan of record established; ready to begin P0-T01.
Artifacts created: MASTER_TICKET_LOG.md, CHANGELOG.md.
Decisions made: See Decision Log §8 (D-001…D-006).
Blockers: None.
Risks: See MASTER_TICKET_LOG §19 (R1–R14).
Next ticket: P0-T01 — Scientific scope & identity freeze.
```

---

## 6. In-Progress Work Log

*None.* When a ticket moves to `In Progress`, record: ticket ID, start date,
current sub-tasks, partial artifacts, and any early findings.

---

## 7. Blocked Ticket Log

*None.* When a ticket is `Blocked`, this section MUST contain: ticket ID, blocker
description, what it depends on, who/what can unblock, and date blocked. A missing
entry here for a blocked ticket is a changelog-contract violation (tested by
P1-T10).

---

## 8. Decision Log

| ID | Date | Decision | Rationale | Affected tickets |
|---|---|---|---|---|
| D-001 | 2026-07-09 | 82 tickets across 8 phases (vs ~60 target) | Reviewer-proof single-concern separation (L01–L28, SB-01–SB-32); heavy/cheap reuse split | All |
| D-002 | 2026-07-09 | Reject `VERSIONING.md` and `CITATION.cff` | Governance forbids release/tag/versioning work | P1-T01 |
| D-003 | 2026-07-09 | Keep `data/raw` as existing symlink; no committed `.gitkeep` trees inside it | Symlink already points to shared data; folders created lazily | P0-T05, P1-T07, P2-T01 |
| D-004 | 2026-07-09 | Model-personalization fallback never labeled "Ditto" | SB-24; use `FedRep-AE`/`FedPer-AE` unless true Ditto implemented | P6-T11 |
| D-005 | 2026-07-09 | `B-FedStatsBenign` uses full pooled variance + matched-exceedance, locked before computation | SB-26/27; matched-exceedance is the main comparison | P4-T05, P4-T06 |
| D-006 | 2026-07-09 | Statistics (BCa CI) computed in P7-T03; claim gating separated into P7-T04 | Keep number computation distinct from claim pass/fail logic | P7-T03, P7-T04 |

---

## 9. Test Log

| Date | Ticket | Command | Result | Notes |
|---|---|---|---|---|
| 2026-07-09 | P0-T01 | `pytest tests/unit/test_scope_boundaries.py -q` | 2 passed | SB-ID parser + forbidden-term negation checks |
| 2026-07-09 | P0-T02 | `pytest tests/unit/test_claim_hierarchy.py -q` | 3 passed | Tier parser |
| 2026-07-09 | P0-T03 | `pytest tests/unit/test_regimes_doc.py -q` | 3 passed | Regime role/pass-rule parser |
| 2026-07-09 | P0-T04 | `pytest tests/unit/test_policies_doc.py -q` | 4 passed | Naming-lock parser |
| 2026-07-09 | P0-T05 | `pytest tests/unit/test_artifact_contracts_doc.py -q` | 3 passed | Artifact-table + README existence |
| 2026-07-09 | P0-T06 | `pytest tests/unit/test_naming_conventions.py -q` | 3 passed | Experiment-ID registry parser |
| 2026-07-09 | P0-T07 | `pytest tests/unit/test_seed_plan_doc.py -q` | 3 passed | Seed-set + honesty-rule parser |
| 2026-07-09 | P0-T08 | `pytest tests/unit/test_testing_contract.py -q` | 2 passed | Subsystem-coverage parser |
| 2026-07-09 | P0-T09 | `pytest tests/unit/test_reuse_policy_doc.py -q` | 3 passed | Stage-classification parser |
| 2026-07-09 | P0-T10 | `pytest tests/unit/test_behavioral_reference.py -q` | 2 passed | No-source-paste / no-compat-language checks |
| 2026-07-09 | P0-T11 | `pytest tests/unit -q` | 32 passed | Full Phase-0 doc-parser suite (includes test_changelog_format.py) |

Record `make test` / `make lint` / `make typecheck` and targeted `pytest` runs
here, one row per meaningful run, tied to the ticket that triggered it.

---

## 10. Files Changed Log

| Date | Ticket | File | Change |
|---|---|---|---|
| 2026-07-09 | Planning | `MASTER_TICKET_LOG.md` | Created (82-ticket plan) |
| 2026-07-09 | Planning | `CHANGELOG.md` | Created (this tracker) |
| 2026-07-09 | P0-T01 | `docs/protocol/identity_lock.md` | Created |
| 2026-07-09 | P0-T01 | `docs/protocol/scope_boundaries.md` | Created |
| 2026-07-09 | P0-T01 | `tests/unit/test_scope_boundaries.py` | Created |
| 2026-07-09 | P0-T02 | `docs/protocol/claim_hierarchy.md` | Created |
| 2026-07-09 | P0-T02 | `tests/unit/test_claim_hierarchy.py` | Created |
| 2026-07-09 | P0-T03 | `docs/protocol/regimes.md` | Created |
| 2026-07-09 | P0-T03 | `tests/unit/test_regimes_doc.py` | Created |
| 2026-07-09 | P0-T04 | `docs/protocol/policies.md` | Created |
| 2026-07-09 | P0-T04 | `tests/unit/test_policies_doc.py` | Created |
| 2026-07-09 | P0-T05 | `docs/protocol/artifact_contracts.md` | Created |
| 2026-07-09 | P0-T05 | `data/README.md` | Created |
| 2026-07-09 | P0-T05 | `checkpoints/README.md` | Created |
| 2026-07-09 | P0-T05 | `outputs/README.md` | Created |
| 2026-07-09 | P0-T05 | `results/README.md` | Created |
| 2026-07-09 | P0-T05 | `tests/unit/test_artifact_contracts_doc.py` | Created |
| 2026-07-09 | P0-T06 | `docs/protocol/naming_conventions.md` | Created |
| 2026-07-09 | P0-T06 | `tests/unit/test_naming_conventions.py` | Created |
| 2026-07-09 | P0-T07 | `docs/protocol/seed_plan.md` | Created |
| 2026-07-09 | P0-T07 | `tests/unit/test_seed_plan_doc.py` | Created |
| 2026-07-09 | P0-T08 | `docs/protocol/testing_contract.md` | Created |
| 2026-07-09 | P0-T08 | `tests/unit/test_testing_contract.py` | Created |
| 2026-07-09 | P0-T09 | `docs/protocol/reuse_policy.md` | Created |
| 2026-07-09 | P0-T09 | `tests/unit/test_reuse_policy_doc.py` | Created |
| 2026-07-09 | P0-T10 | `docs/protocol/behavioral_reference.md` | Created |
| 2026-07-09 | P0-T10 | `tests/unit/test_behavioral_reference.py` | Created |
| 2026-07-09 | P0-T11 | `docs/protocol/structure_decision.md` | Created |
| 2026-07-09 | P0-T11 | `docs/protocol/go_no_go.md` | Created |
| 2026-07-09 | P0-T11 | `tests/unit/test_changelog_format.py` | Created |
| 2026-07-09 | P0-T11 | `CHANGELOG.md` | Updated (dashboard, tables, 11 update blocks, this log) |

---

## 11. Risks and Follow-ups

- Live risk register is maintained in [MASTER_TICKET_LOG.md §19](MASTER_TICKET_LOG.md)
  (R1–R14). Add follow-ups here as they surface during implementation.
- Conditional gates (non-blocking for Regime A/C): OQ1 CICIoT2023 feature-count
  verification (P6-T07); OQ2 Edge-IIoTset coverage/partition (P6-T02/T04); OQ3
  Ditto-vs-fallback choice (P6-T11). See MASTER_TICKET_LOG §20.
- No live follow-ups yet.

---

## 12. Deviations from MASTER_TICKET_LOG.md

*None.* Every deviation (ticket Split/Merged/Skipped/Reopened, or scope change)
MUST be recorded here with: ticket ID, deviation type, reason, and the
corresponding master-log update. Changelog statuses must match the master log at
all times (tested by P1-T10 and P7-T10).

---

## 13. Next Action

- **Phase 0 is complete.** All eleven P0 tickets are `Done`; the go/no-go gate
  ([docs/protocol/go_no_go.md](docs/protocol/go_no_go.md)) is signed **Go**.
- **P1-T01 (project skeleton, pyproject, tooling & Makefile) is the next
  ticket** but is not started and requires explicit authorization to begin
  Phase 1 coding.
- No source/runtime code, dataset preprocessing, or model training exists in
  this repository as of this update.

---

## 14. Update Template (use after every ticket)

```text
## YYYY-MM-DD — P?-T?? — Ticket Title

Status:            (Done / In Progress / Blocked / Skipped / Split / Merged / Reopened)
Summary:           (what changed, one paragraph)
Files changed:     (paths)
Tests added:       (named tests)
Tests run:         (command + pass/fail counts)
Result:            (outcome — implementation status only, never a scientific claim)
Artifacts created: (manifests/outputs, or None)
Decisions made:    (link Decision Log IDs, or None)
Blockers:          (blocker + dependency, or None)
Risks:             (new/updated risks, or None)
Next ticket:       (ID + title)
```

After filling the template: update the §1 dashboard, the §2 phase table, and the
§3 ticket row for that ticket. Marking a ticket `Done` requires a Tests-run entry;
marking it `Blocked` requires a §7 blocker entry.

---

## 15. Phase 0 Consistency Audit (P0-T14/P0-T11 exit check)

Run 2026-07-09 after all eleven P0 tickets reached `Done` and
`pytest tests/unit -q` passed (32/32). Manual review against the checklist
below; each row cites the doc that carries the guarantee.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Scientific identity is preserved | Pass | `docs/protocol/identity_lock.md` |
| 2 | Core ladder has a fixed encoder | Pass | `identity_lock.md` §1, `policies.md` |
| 3 | B1–B4 share the same AE checkpoint per seed | Pass | `behavioral_reference.md` §7, `artifact_contracts.md` (frozen-checkpoint reuse key) |
| 4 | Calibration is benign-only | Pass | `identity_lock.md` §4, `behavioral_reference.md` §6 |
| 5 | Attack data is excluded from threshold fitting | Pass | `behavioral_reference.md` §6, `artifact_contracts.md` §1 (per-dataset benign-only requirement) |
| 6 | AUROC is not used as the threshold verdict | Pass | `identity_lock.md` §6, `behavioral_reference.md` §8 |
| 7 | Regime A confirmatory endpoint is isolated | Pass | `claim_hierarchy.md` Tier 1 (singular `role=confirmatory`), `regimes.md` |
| 8 | Supportive/stress/exploratory modules are not promoted | Pass | `claim_hierarchy.md` (`test_no_supportive_marked_confirmatory`) |
| 9 | FedProx and personalization are outside the causal ladder | Pass | `policies.md` (stress-test comparators table), `identity_lock.md` §8 |
| 10 | Regime D is external validation only | Pass | `regimes.md` (`role: external_validation`) |
| 11 | CICIoT2023 B-b has a metadata-based guard | Pass | `regimes.md`, `artifact_contracts.md` §1.2 rejection rule |
| 12 | Threshold variants are threshold-only unless explicitly requiring new scores | Pass | `reuse_policy.md` stage table |
| 13 | Score reuse contract is explicit | Pass | `artifact_contracts.md` §2 (reuse-validity key column) |
| 14 | Checkpoint reuse contract is explicit | Pass | `artifact_contracts.md` §2, `checkpoints/README.md` |
| 15 | No hidden retraining is allowed | Pass | `reuse_policy.md` "Enforcement" |
| 16 | No stale labels are allowed | Pass | `policies.md` "Naming Locks" (`test_no_stale_labels`) |
| 17 | No old DATP compatibility is allowed | Pass | `behavioral_reference.md` (`test_no_backward_compat_language`) |
| 18 | No shims are allowed | Pass | `structure_decision.md` "Rejected" |
| 19 | No duplicated pipelines are allowed | Pass | `reuse_policy.md` "Enforcement" (P7-T08 dry-run cross-reference) |
| 20 | Repository structure decision is documented | Pass | `docs/protocol/structure_decision.md` |
| 21 | Changelog is initialized | Pass | This file (dashboard, phase/ticket tables, 12 update blocks) |
| 22 | Phase 1 entry criteria are clear | Pass | `docs/protocol/go_no_go.md` |
| 23 | No temp files or ops/audit side folders were created | Pass | `git status --short` shows only `docs/protocol/`, `tests/`, four README stubs, and this file |
| 24 | No runtime/experiment code exists | Pass | No `src/`, `pyproject.toml`, or `scripts/` created |
| 25 | No raw dataset was moved or modified | Pass | `data/raw` symlink untouched; only `data/README.md` added |

**Audit result: 25/25 pass, 0 failures.** Phase 0 go/no-go
([docs/protocol/go_no_go.md](docs/protocol/go_no_go.md)) is signed **Go**.

---

## Initial State (bootstrap record)

- **Initial status:** Not Started (0 / 82 Done).
- **Initial phase:** Phase 0 — Protocol, Scope & Architecture Freeze.
- **Initial ticket:** P0-T01 — Scientific scope & identity freeze.
- **Initial blocker state:** None.
- **Next action:** Begin P0-T01 (see §13).
- **Reminder:** This changelog MUST be updated after every ticket using the §14
  template, and its statuses MUST stay consistent with
  [MASTER_TICKET_LOG.md](MASTER_TICKET_LOG.md). It records implementation progress
  only — never unverified experimental claims.
