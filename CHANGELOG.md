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
Current phase:        Phase 0 — Protocol, Scope & Architecture Freeze
Current ticket:       P0-T01 — Scientific scope & identity freeze
Overall progress:     0 / 82 tickets Done (0%)
Completed tickets:    0
In-progress tickets:  0
Blocked tickets:      0
Last completed ticket: None
Next ticket:          P0-T01
Last tests run:       None (no code yet)
Current blocker:      None
Last update:          2026-07-09 — planning package created
```

---

## 2. Phase Progress Table

| Phase | Total Tickets | Done | In Progress | Blocked | Status | Exit Gate |
|---|---|---|---|---|---|---|
| 0 — Protocol/scope/architecture freeze | 11 | 0 | 0 | 0 | Not Started | P0-T11 go/no-go signed |
| 1 — Scratch foundation | 10 | 0 | 0 | 0 | Not Started | P1-T10 foundation tests green |
| 2 — Anchor reproduction pipeline | 11 | 0 | 0 | 0 | Not Started | P2-T11 frozen anchor + scores |
| 3 — Core threshold policies & metrics | 11 | 0 | 0 | 0 | Not Started | P3-T11 B0–B4 + metrics validated |
| 4 — Threshold variants & comparators | 9 | 0 | 0 | 0 | Not Started | P4-T09 variants reuse scores |
| 5 — Mechanism analyses | 8 | 0 | 0 | 0 | Not Started | P5-T08 mechanisms from fixtures |
| 6 — External dataset & stress tests | 12 | 0 | 0 | 0 | Not Started | P6-T12 D/C frozen, stress separated |
| 7 — Temporal, final audit & freeze | 10 | 0 | 0 | 0 | Not Started | P7-T10 readiness report signed |
| **Total** | **82** | **0** | **0** | **0** | **Not Started** | — |

---

## 3. Ticket Progress Table

| Ticket | Phase | Status | Last Update | Tests Run | Files Changed | Notes |
|---|---|---|---|---|---|---|
| P0-T01 | 0 | Not Started | — | — | — | Scientific scope & identity freeze |
| P0-T02 | 0 | Not Started | — | — | — | Claim hierarchy & confirmatory isolation |
| P0-T03 | 0 | Not Started | — | — | — | Regime definitions freeze |
| P0-T04 | 0 | Not Started | — | — | — | Threshold-policy & comparator nomenclature |
| P0-T05 | 0 | Not Started | — | — | — | Dataset & artifact/directory contracts |
| P0-T06 | 0 | Not Started | — | — | — | Config/suite/experiment-ID naming |
| P0-T07 | 0 | Not Started | — | — | — | Seed plan freeze |
| P0-T08 | 0 | Not Started | — | — | — | Testing contract & test-pyramid |
| P0-T09 | 0 | Not Started | — | — | — | Reuse/caching + raw-data placement |
| P0-T10 | 0 | Not Started | — | — | — | Old DATP behavioral-reference extraction |
| P0-T11 | 0 | Not Started | — | — | — | Structure decision + changelog + go/no-go |
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
> at the top of §5 (Completed Work Log) once tickets start closing.

```text
## 2026-07-09 — Planning — MASTER_TICKET_LOG.md + CHANGELOG.md created

Status: Planning package delivered (no code).
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

## 5. Completed Work Log

*None yet.* Newest completed ticket appears at the top once work begins, each as a
full update block (template §14).

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
| — | — | — | — | No tests run yet (no code). |

Record `make test` / `make lint` / `make typecheck` and targeted `pytest` runs
here, one row per meaningful run, tied to the ticket that triggered it.

---

## 10. Files Changed Log

| Date | Ticket | File | Change |
|---|---|---|---|
| 2026-07-09 | Planning | `MASTER_TICKET_LOG.md` | Created (82-ticket plan) |
| 2026-07-09 | Planning | `CHANGELOG.md` | Created (this tracker) |

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

- **Begin P0-T01 — Scientific scope & identity freeze.** Produce
  `docs/protocol/identity_lock.md` + `docs/protocol/scope_boundaries.md`, add the
  SB-ID parser test, then update this changelog using the §14 template.
- Phase 0 is documentation/freeze; no source code until P0-T11 (go/no-go) is Done.

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
