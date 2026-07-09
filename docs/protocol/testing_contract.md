# Testing Contract & Test Pyramid

> Ticket: P0-T08. Canonical authority for `MASTER_TICKET_LOG.md` §10. Every
> subsystem below names concrete test targets and the ticket that owns them.
> No subsystem is covered by a generic "add tests" placeholder.

## Coverage-of-Contract Rule

A ticket is not "Done" (`CHANGELOG.md`) unless every test row below that names
its ticket ID exists and passes. A subsystem with no named row is not yet
in scope for any ticket; adding one requires adding a row here first.

## 1. Unit Tests

| Subsystem | Owning ticket | Required cases |
|---|---|---|
| Config validation | P1-T04 | valid load; reject invalid q; unknown/stale policy; missing benign-only flag; hardcoded abs path; unknown experiment ID |
| Enums/domain | P1-T02 | policies match protocol doc; B0 non-ladder; B-b rejected; AUROC control; CV(FPR) primary; no stale names |
| Path resolution | P1-T05 | raw symlink resolved; stable artifact paths; env override; reject hardcoded/wrong root; missing-root raises |
| Manifest schema | P1-T07 | round-trip; reuse-key mismatch detected |
| Dataset contract | P2-T01, P6-T01, P6-T07 | device/schema/label validation; feature-count verification (CICIoT2023) |
| Split semantics | P2-T04 | benign-only calibration; no cal/test overlap; eligibility at n_min=100 |
| No attack in calibration | P2-T04, P3-T02, P7-T09 | attack-in-cal rejected |
| Threshold formulas | P3-T03…T07 | B0 pooled p95; B1 mean-of-local-p95 + pooled/weighted; B2 per-client p95 + fallback; B3 family-mean; B4 fingerprint + K=3 + cluster mean |
| Quantile behavior | P3-T01 | local/pooled/weighted/quantile-of-quantiles; attainment; reject q-range/empty |
| B4 clustering | P3-T07, P5-T03 | fingerprint scalars; K mismatch rejected; adjusted-Rand known value; feature ablation |
| `B-FedStatsBenign` | P4-T05/T06 | full pooled variance; between_ratio; matched exceedance; tie-break larger k; reject simple variance; reject attack labels |
| Conformal coverage | P4-T04 | marginal coverage near target; quantile formula |
| Metric formulas | P3-T09/T10 | Macro-F1 known values; BA; P10 definition |
| CV(FPR) edge cases | P3-T10 | known value; zero-mean; single-client undefined; eligibility filter; reject ineligible inclusion |
| AUROC invariance/control | P3-T09 | threshold-invariant; monotone-transform invariant; not used as verdict |
| Bootstrap CI | P7-T03 | BCa known-answer; reference-fixture match; exclude-zero detection; reject percentile when BCa required |
| Paired delta | P7-T03 | Wilcoxon known value; Δ = B1 − B2 |
| Claim gates | P7-T04 | confirmatory pass on positive CI; null on zero-crossing; opposite flagged; no supportive promotion |
| Artifact writer/reader | P1-T07 | round-trip; mismatch rejected |
| Determinism/seed locking | P1-T06, P1-T03 | reproducible seed lock; paired streams deterministic |
| Hardware fallback | P1-T06 | CPU fallback; VRAM limit; reject invalid device |
| Changelog format | P1-T10 | dashboard; status enum; ticket/phase table columns; no result claims |
| Protocol docs (Phase 0) | P0-T01…T11 | each doc has a named parser test (this contract's own §4) |

## 2. Integration Tests

Tiny clean pipeline (P2-T10); preprocessing→split manifest (P2-T02/T04);
split→training fixture (P2-T06); checkpoint freeze + reload (P2-T07); score
from frozen checkpoint (P2-T08); B1–B4 suite from stored scores (P3-T11);
threshold variants from stored scores (P4-T01…T06); statistics from per-seed
metrics (P7-T03); table/figure export from metrics (P4-T09, P5-T07, P7-T07);
outputs/results layout (P2-T10); no-overwrite behavior (P1-T07); Regime C tiny
Dirichlet (P6-T09); Regime D tiny external fixture (P6-T05); FedProx tiny
stress (P6-T10); personalization tiny stress (P6-T11); changelog update after
ticket (P1-T10).

## 3. Smoke / E2E Tests

One tiny synthetic full clean run (P2-T10); one tiny N-BaIoT-like
physical-device run (P2-T10); one threshold-only rerun proving no model
retraining (P4-T08); one anchor-like 2-seed mini-run (P7-T03); one reporting
run from existing outputs only (P7-T07); one failure run where
leakage/wrong lineage is detected (P7-T09); one agent-progress update
simulation marking a ticket complete + updating `CHANGELOG.md` (P1-T10).

## 4. Negative / Failure-Mode Tests

Missing raw dataset (P2-T01); wrong dataset root (P2-T01/P1-T05); mixed
client IDs (P2-T01/T03); cal/test overlap (P2-T04); attack in calibration
(P2-T04); ineligible-client threshold misuse (P3-T02); B3 without taxonomy
(P3-T06); B4 K mismatch (P3-T07); variants trying to retrain (P4-T08);
score/checkpoint mismatch (P2-T08/P4-T08); config stale policy names
(P1-T04/P7-T09); silent overwrite attempt (P1-T07); invalid seed plan
(P1-T03); invalid q (P3-T01/P4-T01); invalid temporal split (P7-T01); invalid
Laridi-faithful under benign contract (P4-T07); manual hardcoded path
(P1-T05); changelog status ≠ master log (P1-T10/P7-T10); changelog missing
tests-run entry (P1-T10); changelog missing blocker entry when blocked
(P1-T10).

## Phase 0 Test Files (This Freeze)

Each Phase 0 protocol doc is validated by a same-named parser test under
`tests/unit/`: `test_scope_boundaries.py`, `test_claim_hierarchy.py`,
`test_regimes_doc.py`, `test_policies_doc.py`, `test_artifact_contracts_doc.py`,
`test_naming_conventions.py`, `test_seed_plan_doc.py`,
`test_testing_contract.py`, `test_reuse_policy_doc.py`,
`test_behavioral_reference.py`, `test_changelog_format.py`. These are
documentation-parser tests, not runtime pipeline tests; no dataset, model, or
experiment code exists yet (Phase 1 entry gate).

## Consumers

- `ai/hooks/test_hook.md` gate checks impacted rows on every ticket.
- P7-T09 final audit cross-checks this contract against the actual test
  suite for coverage gaps.
