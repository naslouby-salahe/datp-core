# MASTER TICKET LOG — DATP Journal Extension (`datp-core`)

> Complete phase/ticket implementation plan for the scratch build of the DATP
> journal-extension study. This file is the **plan of record**. Progress is
> tracked separately in [CHANGELOG.md](CHANGELOG.md). No code is implemented by
> this document.

---

## 1. Title and Purpose

**Title.** DATP Journal Extension — scratch implementation master ticket log.

**Purpose.** Define every phase, ticket, contract, test, gate, and artifact
needed to build `datp-core` from zero into a reviewer-proof implementation of
the DATP fixed-encoder threshold-calibration-scope study described in
[docs/Journal_Extension_Master_Roadmap.md](docs/Journal_Extension_Master_Roadmap.md).

The plan optimizes for **one reusable pipeline** with a hard split between
expensive stages (preprocessing, training, checkpointing, scoring) and cheap
stages (threshold policies, variants, mechanism analyses, statistics, tables,
figures). Threshold-only work must never trigger retraining.

This is an implementation and validation plan. It is **not** a results file and
makes **no** experimental claims.

---

## 2. Scope Assumptions

- Clean scratch repository. Zero source carried over from the reference project
  `/home/naslouby/Projects/datp`; that project is a **behavioral reference only**
  (threshold-policy logic, split semantics, scoring semantics, metric/result
  interpretation).
- Raw datasets live under `data/raw`, which in this repo is already a **symlink**
  to `/home/naslouby/Projects/datp-shared-data/raw` and is gitignored.
- Governance is fixed by [AGENTS.md](AGENTS.md) and [ai/](ai/): no backward
  compatibility, no shims/redirects, no temp/audit clutter, no release/tag/
  versioning work, typed protocol state, mandatory gates, `AGENTS.md` final
  report format.
- Scientific identity, claim hierarchy, regimes, nomenclature, scope boundaries
  (SB-01…SB-32), and reviewer register (L01…L28) are **locked** by the roadmap
  and are inputs, not open questions.
- Python + PyTorch, deterministic seeds, `uv`-managed dependencies, `ruff` +
  `pyright` + `pytest`.
- Heavy compute (training/scoring) runs once per `(dataset, regime, seed, α)`;
  everything downstream reuses frozen checkpoints and stored score artifacts.

---

## 3. Non-Goals

- No implementation of code in this document (planning only).
- No experiment execution, no result claims, no manuscript prose.
- No backward compatibility, shims, redirects, fake-compatibility modules, or
  stale labels leaking from the reference project.
- No release, tag, semantic-versioning, `CITATION.cff`, or `VERSIONING.md` work
  (forbidden by governance; see §5 structure decision).
- No scope drift: no poisoning, Dynamic DATP, privacy guarantees, deployment
  profiling, backdoor, evasion, full drift detection, or generic FL-IDS
  benchmark expansion beyond the locked module set.
- No promotion of any supportive/stress/mechanism/exploratory result to the
  confirmatory claim.
- No temporary planning files, and no extra ops/audit files beyond the two
  requested deliverables.

---

## 4. Scientific Identity Lock

Preserved verbatim from roadmap §2–§4 and enforced by tests and gates:

- **Fixed encoder / fixed federated model.** One shared FedAvg autoencoder is
  trained once per seed and frozen; **B1–B4 reuse the same final AE state,
  seeds, and per-client score artifacts without retraining** (within a
  dataset/regime ladder; input_dim differs across datasets — SB-13).
- **Threshold-calibration scope is the sole causal variable** in the B1–B4
  ladder. B0 is a centralized reference and is **not** in the FL causal ladder.
- **Calibration is benign-only.** Attack data is evaluation-only and never fits
  or tunes any threshold.
- **Primary metric is CV(FPR)** over eligible clients (n_k ≥ n_min = 100).
  Secondary: worst-client FPR, IQR(FPR), max−min FPR, CV(TPR), P10 Macro-F1,
  worst-client BA, alert burden (real/cited rate only).
- **AUROC / Macro-F1 / BA are model-quality controls, never the thresholding
  verdict.**
- **Confirmatory endpoint (Tier 1, singular, immutable):** Regime A only,
  N-BaIoT natural physical-device split, B1 vs B2 only, CV(FPR) only, 10 paired
  seeds, 95% **BCa** bootstrap CI on Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s]. Claim
  survives **only** if the BCa CI excludes zero in the positive direction.
- **Stress tests (FedProx, model personalization, Laridi-style) live outside the
  causal ladder** and never share its experimental control (SB-25).
- **"Fairness"** means operational/service-level FPR equity only (roadmap §2).
- Null/mixed/opposite outcomes are **reportable**, never suppressed; pre-committed
  fallback wording governs reporting (roadmap §12).

---

## 5. Proposed Repository Structure Decision

The roadmap-suggested tree was audited against governance and the existing repo
state. Verdict: **accept the `configs/ · src/datp_core/ · tests/ · scripts/`
backbone and the outputs/results/checkpoints separation; reject all release/
versioning artifacts; adapt data/ to the existing symlink; do not pre-create
empty folders.**

### 5.1 Accepted (unchanged)

| Element | Reason | Implemented by | Enforced by |
|---|---|---|---|
| `configs/{datasets,training,thresholding,analysis,suites}/` | Clean separation of scientific/runtime params; no hardcoded experiment logic | P0-T06, P1-T04 | `test_config_validation.py`, `structure_hook` |
| `src/datp_core/` domain-driven modules (`domain, config, utils, data, partitioning, models, federation, thresholding, experiments, evaluation, statistics, analyses, reporting`) | Matches the reuse split (heavy vs cheap stages); narrow interfaces | P1–P7 | `structure_hook`, `test_artifact_layout.py` |
| `tests/{unit,integration,fixtures}/` pyramid | Reviewer-proof separation of contract vs pipeline vs smoke | P0-T08, P1-T10 | `test_hook` |
| `checkpoints/` frozen weight vault (gitignored, read-only after selection) | Enforces fixed-encoder identity + reuse | P2-T07 | `test_checkpoint_freeze.py` |
| `outputs/` complete runtime artifacts (gitignored) | Heavy/full artifacts kept out of `results/` | P1-T07 | `test_artifact_layout.py` |
| `results/` curated lightweight shareable derivations | Only citable/shareable derived artifacts | P7-T06 | `test_result_curation.py` |
| `scripts/{run_experiment,build_tables,build_figures,freeze_results}.py` | Thin entrypoints over the library; no logic | P1-T09, P4-T09, P5-T07, P7-T06 | `structure_hook` |
| `data/manifests/`, `checkpoints/README.md`, `outputs/README.md` contracts | Provenance + read-only rules | P0-T05, P1-T07 | `test_provenance.py` |

### 5.2 Changed

- **`data/raw`** is **already a symlink** to `/home/naslouby/Projects/datp-shared-data/raw`.
  Keep the symlink; do **not** create committed `data/raw/<dataset>/.gitkeep`
  trees inside a gitignored symlink target. `data/README.md` documents expected
  placement; presence/schema is verified at runtime by loaders + manifests
  (P2-T01, P6-T01, P6-T07). *(P0-T05, P0-T09)*
- **`data/preprocessed/` and `outputs/*` subfolders** are **created lazily by the
  ticket that owns them**, not pre-seeded with `.gitkeep` sprawl. Only
  gitignored directories that must exist before first run get a single
  `.gitkeep`. *(P1-T07, P1-T08)*
- **`.env.example`** reduced to documenting the one data-root override and device
  env vars; canonical paths come from the path resolver (P1-T05), not env
  strings. *(P1-T05)*
- **`personalized_ae.yaml`** naming: config keys never hardcode "Ditto"; the
  fallback is `FedRep-AE`/`FedPer-AE` and is labeled as such (SB-24). *(P6-T11)*
- **`configs/thresholding/b_fedstats_benign.yaml`** locks the full pooled-variance
  + matched-exceedance contract (SB-26/27) before any computation. *(P4-T05/06)*

### 5.3 Rejected

| Element | Reason |
|---|---|
| `VERSIONING.md` | Versioning/release work is forbidden by `AGENTS.md`/`ai/`. |
| `CITATION.cff` | Release-package/citation metadata = release work; out of scope now. |
| Pre-created empty `outputs/*/.gitkeep` for every experiment family | Premature folder sprawl; violates "no unnecessary folders". Created lazily. |
| Any `compat/`, `legacy/`, `migrations/`, shim, or redirect module | No-backward-compatibility policy. |
| `frozen.py` as a separate wrapper *without behavior* | Kept **only** because it carries real read-only-load behavior distinct from save/select; otherwise it would be a rejected wrapper. |

### 5.4 Preserved governance surfaces (must not be removed)

`AGENTS.md`, `ai/` (source of truth), `.claude/`, `.github/`, `.agents/`,
`.codex/`, `docs/`, `README.md`, `.gitignore`, existing `data/raw` symlink.
These are inputs; tickets never rewrite them except where a ticket explicitly
owns a doc (e.g. `data/README.md`).

---

## 6. Phase Overview Table

| Phase | Name | Tickets | Focus | Heavy? | Entry gate | Exit gate |
|---|---|---|---|---|---|---|
| 0 | Protocol, scope & architecture freeze | 11 | Freeze identity, claims, regimes, contracts, structure, go/no-go | No | Roadmap locked | All freeze docs + go/no-go signed |
| 1 | Scratch foundation | 18 | Skeleton, typed config, enums, paths, manifests, cache, CLI, fixtures, changelog | No | P0 done | Foundation tests green, layout enforced |
| 2 | Anchor reproduction pipeline | 20 | N-BaIoT → split → AE → FedAvg → freeze → score → B1/B2 → gate | **Yes** | P1 done | Frozen anchor checkpoints + stored scores + smoke green |
| 3 | Core threshold policies & metrics | 11 | Quantile backbone, B0–B4, predictions, metrics, disparity, aggregation | No (reuse) | P2 scores exist | B0–B4 + metrics validated on fixtures |
| 4 | Threshold variants & comparators | 9 | q, τ-shrink, cal-size, B2-conf, B-FedStatsBenign, no-retrain guard | No (reuse) | P3 done | Variants reuse scores; no-retrain proven |
| 5 | Mechanism analyses | 8 | CDFs, shift surface, cluster stability, JS, P10, alert burden | No (reuse) | P3 done | Mechanism artifacts from fixtures |
| 6 | External dataset & stress tests | 12 | Edge-IIoTset (D), CICIoT2023 (B-a/B-b), Dirichlet (C), FedProx, personalization | **Yes** | P2–P4 done | D/C heavy artifacts frozen; stress outside ladder |
| 7 | Temporal recalibration, final audit & freeze | 10 | Chronological split, stats finalization, claim gates, curation, audits, readiness | Partly | P6 done | Full audit + readiness report signed |

---

## 7. Ticket Count Summary

- **Total phases:** 8 (Phase 0 → Phase 7).
- **Total tickets:** 99.
- **Per phase:** P0 = 11, P1 = 18, P2 = 20, P3 = 11, P4 = 9, P5 = 8, P6 = 12,
  P7 = 10.
- **Heavy-stage tickets (create/trigger reusable heavy artifacts):** 11 —
  P2-T02, P2-T06, P2-T07, P2-T08, P2-T11, P6-T03, P6-T05, P6-T09, P6-T10,
  P6-T11, P7-T02.
- **Threshold-only / reuse-stage tickets (consume frozen artifacts):** 33 —
  all of P3 (B0–B4 + metrics), all of P4, all of P5, plus P6-T06 threshold
  ladder and P7 statistics/curation.
- **Testing/audit-focused tickets:** 12 — P0-T08, P1-T10, P2-T10, P3-T11,
  P4-T08, P5-T08, P7-T03, P7-T05, P7-T07, P7-T08, P7-T09, P7-T10.
- **Changelog/progress-tracking tickets:** 2 dedicated (P0-T11 format + go/no-go,
  P1-T10 enforcement test) plus a mandatory changelog update on every ticket.

**Why 82, not ~60.** The target was ~60 with explicit permission to increase for
clean testing, gates, artifact contracts, and reviewer-proof separation. DATP is
reviewer-attack-driven (L01–L28) and depends on a hard heavy/cheap reuse split.
Collapsing to 60 would have forced overloaded tickets such as "implement
thresholding" or "add stress tests" that mix contracts, implementation,
validation, and reporting — exactly what the brief forbids. 82 keeps every
ticket single-concern: each threshold policy, each comparator contract vs its
operating-point logic, each dataset loader vs its feasibility guard, and each
audit is isolated. See §21 for the full count justification.

---

## 8. Dependency Table (phase- and key-ticket-level)

**Phase edges:** P0 → P1 → P2 → {P3, P5} ; P3 → P4 ; {P2,P3,P4} → P6 ;
{P3,P4,P6} → P7. P5 depends only on P2 scores + P3 policies.

**Critical heavy-artifact chain (must be correct before any cheap stage):**
P2-T02 (preprocess) → P2-T04 (split manifest) → P2-T06 (FedAvg) → P2-T07
(freeze) → P2-T08 (scores) → *[reused by all of P3, P4, P5]*.

| Ticket | Depends on | Consumed by |
|---|---|---|
| P1-T04 config system | P1-T02, P1-T03 | all runtime tickets |
| P1-T07 manifest/writer | P1-T04, P1-T05 | every artifact-producing ticket |
| P2-T08 scores | P2-T07 | P3-T03…T10, P4-*, P5-*, P7-T03 |
| P3-T01 quantile backbone | P1-T02 | B0/B1/B2, B-FedStatsBenign (P4-T05/06) |
| P3-T02 policy interface | P3-T01 | B0–B4, all variants |
| P4-T08 no-retrain guard | P2-T07, P3-T02 | CI gate for all variant runs |
| P6-T04 D coverage gate | P6-T02, P6-T03 | P6-T05/06, P7-T02 |
| P7-T04 claim gates | P3-T10, P7-T03 | P7-T05, P7-T10 |
| P7-T06 curation | P7-T04 | P7-T07, P7-T10 |

A full per-ticket dependency list appears in each ticket's **Dependencies**
field in §9.

---

## 9. Full Ticket List by Phase

**Field legend (every ticket).** ID · Title · Phase · Status · Purpose ·
Scientific reason · Engineering reason · Inputs · Outputs · Files/modules ·
Dependencies · Implementation tasks · Unit tests · Integration tests ·
Smoke/E2E tests · Negative tests · Acceptance criteria · Definition of done ·
Reviewer risk addressed · Runtime/reuse impact · Stage class · Changelog update ·
Notes. Default **Status at creation: Not Started.** Every ticket requires a
CHANGELOG update after completion (§16).

---

### Phase 0 — Protocol, Scope & Architecture Freeze

Freeze phase. Deliverables are decision/contract docs under `docs/protocol/`
plus machine-checkable schema stubs; each ticket carries an audit/validation
check even though it is documentation.

#### P0-T01 — Scientific scope & identity freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock the DATP identity (roadmap §2) as the top constraint doc all
  later contracts import.
- **Scientific reason:** Prevents scope drift and confirmatory-endpoint dilution.
- **Engineering reason:** Gives tests a single source for identity assertions.
- **Inputs:** Roadmap §2–§3; AGENTS.md; ai/skills/`datp_journal_scope_guard.md`.
- **Outputs:** `docs/protocol/identity_lock.md` + `docs/protocol/scope_boundaries.md`
  (SB-01…SB-32 restated as an enumerated, testable list).
- **Files/modules:** `docs/protocol/*.md`.
- **Dependencies:** none.
- **Implementation tasks:** Restate fixed-encoder rule, sole-causal-variable rule,
  benign-only rule, CV(FPR)-primary rule, AUROC-control rule, stress-tests-
  outside-ladder rule, fairness definition; enumerate SB-01…SB-32 with IDs.
- **Unit tests:** `test_scope_boundaries.py::test_all_SB_ids_present_and_unique`
  (parses the doc, asserts SB-01…SB-32 exactly once each).
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_scope_boundaries.py::test_forbidden_terms_absent`
  (no "solves non-IID", "privacy-preserving", "concept-drift handling" as claims).
- **Acceptance:** All 32 SB IDs parse; identity bullets present; audit check green.
- **Definition of done:** Doc + parser test green; changelog updated.
- **Reviewer risk:** L25/L26 scope width; L01 triviality framing.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** This doc is imported by P1-T02 enum docstrings and P7 audits.

#### P0-T02 — Claim hierarchy & confirmatory-endpoint isolation freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock the 9-tier claim hierarchy and the singular Tier-1 endpoint.
- **Scientific reason:** Nothing below Tier 1 may be promoted; endpoint is immutable.
- **Engineering reason:** Drives `claim_gates` metadata (P7-T04) and claim map (P7-T05).
- **Inputs:** Roadmap §3, §5, §6.
- **Outputs:** `docs/protocol/claim_hierarchy.md` with per-claim (tier, evidence,
  regime, metric, min-pass, fallback ref, reviewer risk, placement).
- **Files/modules:** `docs/protocol/claim_hierarchy.md`.
- **Dependencies:** P0-T01.
- **Implementation tasks:** Encode Tiers 1–9; mark Tier 1 = {Regime A, B1 vs B2,
  CV(FPR), 10 seeds, BCa CI positive}; list forbidden claims (Tier 9).
- **Unit tests:** `test_claim_hierarchy.py::test_single_confirmatory_tier1`;
  `::test_tier9_forbidden_enumerated`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_supportive_marked_confirmatory` (only Tier 1 has
  role=confirmatory).
- **Acceptance:** Exactly one confirmatory claim; all tiers present.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L23 HARKing; L04 tautology (endpoint framing).
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Feeds `ClaimRole` enum (P1-T02) and `claim_gates` (P7-T04).

#### P0-T03 — Regime definitions freeze (A / B-a / B-b / C / D / D-temporal)
- **Phase / Status:** 0 / Done
- **Purpose:** Lock regime semantics, client definitions, purpose, pass/suppression rules.
- **Scientific reason:** Each regime has a fixed role (confirmatory/boundary/
  supportive/external/temporal) and must not be conflated.
- **Engineering reason:** Backs the `Regime` enum and per-regime gating.
- **Inputs:** Roadmap §7 regime table; §11 temporal.
- **Outputs:** `docs/protocol/regimes.md` (incl. `B_B_REJECTED_NO_METADATA`,
  `TEMPORAL_REJECTED_NO_TIMESTAMPS` status labels).
- **Files/modules:** `docs/protocol/regimes.md`.
- **Dependencies:** P0-T01.
- **Implementation tasks:** Encode A (K=9 physical), B-a (63 file-level), B-b
  (rejected), C (Dirichlet 20-client α-grid), D (Edge-IIoTset device/group), D-temporal.
- **Unit tests:** `test_regimes_doc.py::test_all_regimes_have_role_and_passrule`;
  `::test_bb_marked_rejected`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_quantitative_bb_claim` (B-b carries no metric row).
- **Acceptance:** Six regimes with roles + suppression labels present.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L14 pseudo-clients; L16 external mixed.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Drives P1-T02 `Regime` enum and P6 loaders/guards.

#### P0-T04 — Threshold-policy & comparator nomenclature freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock B0–B4 + comparator identifiers and naming locks.
- **Scientific reason:** Prevents stale labels (no `B5`, no `B3-LGS`, no "Ditto"
  fallback misname) and preserves ladder meaning.
- **Engineering reason:** Backs the `ThresholdPolicy` / `Comparator` enums.
- **Inputs:** Roadmap §4 nomenclature table; SB-24/26/27/29/32.
- **Outputs:** `docs/protocol/policies.md`.
- **Files/modules:** `docs/protocol/policies.md`.
- **Dependencies:** P0-T01.
- **Implementation tasks:** Encode B0 (centralized, not in ladder), B1, B2, B3
  (Regime A only), B4 (K=3 canonical, fingerprint [µ_e,σ_e,skew_e,p95(e)]),
  τ-shrink, cal-size fallback, B2-conf, `B-FedStatsBenign`, `B-LaridiFaithful`
  (out of scope), FedProx, Ditto/`FedRep-AE`/`FedPer-AE`.
- **Unit tests:** `test_policies_doc.py::test_no_stale_labels` (no `B5`, `B3-LGS`);
  `::test_b0_not_in_causal_ladder`; `::test_b4_canonical_k_is_3`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_fallback_not_named_ditto`.
- **Acceptance:** All identifiers + roles present; naming locks encoded.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L06/L07/L08 clustering/family/HARKing; L02 Laridi.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Feeds P3 policies and P4 comparators directly.

#### P0-T05 — Dataset & artifact/directory contract definitions
- **Phase / Status:** 0 / Done
- **Purpose:** Define contracts for raw, preprocessed, splits, checkpoints,
  scores, thresholds, metrics, stats, tables, figures, manifests, results.
- **Scientific reason:** Reuse is valid only when dataset/split/checkpoint/
  preprocessing/seed/scoring identity match exactly.
- **Engineering reason:** Single artifact contract prevents duplicated pipelines.
- **Inputs:** Roadmap §17; suggested tree; existing `data/raw` symlink.
- **Outputs:** `docs/protocol/artifact_contracts.md`; `data/README.md`;
  `checkpoints/README.md`; `outputs/README.md`; `results/README.md` (stubs).
- **Files/modules:** those docs.
- **Dependencies:** P0-T01.
- **Implementation tasks:** For each artifact define producer stage, consumer
  stages, required manifest fields (hashes/IDs), reuse-validity keys, read-only
  rules; document `data/raw` as a symlink and expected per-dataset placement.
- **Unit tests:** `test_artifact_contracts_doc.py::test_every_artifact_has_manifest_fields`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_results_excludes_heavy_artifacts` (results = derived only).
- **Acceptance:** All 14 artifact classes documented with reuse keys.
- **Definition of done:** Docs + test green; changelog updated.
- **Reviewer risk:** L27/L28 reproducibility.
- **Runtime/reuse impact:** Defines the reuse contract (foundational).
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Implemented concretely by P1-T07 manifest schema.

#### P0-T06 — Config, experiment-suite & experiment-ID naming conventions
- **Phase / Status:** 0 / Done
- **Purpose:** Lock config group layout, suite names, and experiment IDs (E-C1…).
- **Scientific reason:** Every table/figure must trace to a stable experiment ID.
- **Engineering reason:** Prevents hardcoded experiment logic; drives config loader.
- **Inputs:** Roadmap §9 experiment matrix; suggested `configs/` tree.
- **Outputs:** `docs/protocol/naming_conventions.md` (config groups
  datasets/training/thresholding/analysis/suites; suite names; E-ID registry).
- **Files/modules:** `docs/protocol/naming_conventions.md`.
- **Dependencies:** P0-T02, P0-T03, P0-T04.
- **Implementation tasks:** Map experiment IDs E-C1, E-S1…S3, E-M1…M5, E-V1…V3,
  E-X1, E-T1…T3, E-B1, E-O1, E-Q1…Q6 to suites; define config-key naming rules
  (no raw policy strings; enum-backed).
- **Unit tests:** `test_naming_conventions.py::test_experiment_ids_unique`;
  `::test_suite_names_map_to_known_experiments`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_stale_policy_names_in_registry`.
- **Acceptance:** All roadmap experiment IDs registered; suites named.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L23 HARKing; reproducibility.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Feeds P1-T04 config schemas and P6/P4 suite configs.

#### P0-T07 — Seed plan freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock the paired 10-seed plan and seed roles.
- **Scientific reason:** Confirmatory endpoint = 10 paired seeds; seed-extension
  honesty rule (roadmap §10) must be encoded.
- **Engineering reason:** Backs `SeedPlan` types and paired-delta wiring.
- **Inputs:** Roadmap §3, §10 seed-extension honesty rule.
- **Outputs:** `docs/protocol/seed_plan.md`.
- **Files/modules:** `docs/protocol/seed_plan.md`.
- **Dependencies:** P0-T02.
- **Implementation tasks:** Define 10 seeds, pairing rule (same seed → B1 & B2 use
  identical AE state), 5-seed preliminary vs 10-seed main, CI-discrepancy block rule.
- **Unit tests:** `test_seed_plan_doc.py::test_ten_paired_seeds`;
  `::test_seed_extension_rule_present`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_seed_dropping_allowed`.
- **Acceptance:** 10 paired seeds + honesty rule documented.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L23/L21 seed suppression.
- **Runtime/reuse impact:** Seeds key checkpoint/score reuse identity.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Feeds P1-T03 seed types and P2-T09 paired plan.

#### P0-T08 — Testing contract & test-pyramid freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock the unit/integration/smoke/negative test taxonomy and the
  required test list per subsystem.
- **Scientific reason:** Enforces no-leakage, benign-only, no-retrain, metric
  correctness before any result is trusted.
- **Engineering reason:** Gives every later ticket a named test target.
- **Inputs:** Brief testing requirements; ai/hooks/`test_hook.md`.
- **Outputs:** `docs/protocol/testing_contract.md` (§10 of this doc in canonical form).
- **Files/modules:** `docs/protocol/testing_contract.md`.
- **Dependencies:** P0-T05.
- **Implementation tasks:** Enumerate the unit/integration/smoke/negative lists
  from §10; assign each to owning phase/ticket; define coverage-of-contract rule.
- **Unit tests:** `test_testing_contract.py::test_every_subsystem_has_named_tests`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_generic_add_tests_placeholder`.
- **Acceptance:** Every subsystem maps to named tests; no generic placeholders.
- **Definition of done:** Doc + test green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** none.
- **Stage class:** Testing/audit.
- **Changelog update:** required.
- **Notes:** This is the authority for §10 Testing Strategy.

#### P0-T09 — Reuse/caching principle & raw-data placement freeze
- **Phase / Status:** 0 / Done
- **Purpose:** Lock the heavy-vs-cheap stage split and the `data/raw` placement rule.
- **Scientific reason:** Threshold-only variants must reuse frozen checkpoints and
  stored scores; heavy reruns only on model/data/split/preprocess/scoring change.
- **Engineering reason:** Prevents duplicated pipelines and hidden retraining.
- **Inputs:** Roadmap §17; brief reuse requirements; existing symlink.
- **Outputs:** `docs/protocol/reuse_policy.md` (stage table: heavy vs cheap;
  reuse-invalidation triggers; `data/raw` symlink placement + expected datasets).
- **Files/modules:** `docs/protocol/reuse_policy.md`.
- **Dependencies:** P0-T05.
- **Implementation tasks:** Define which stages are heavy (preprocess, train,
  checkpoint, score) vs cheap (threshold, variant, mechanism, stats, table,
  figure); list the 6 invalidation triggers; document `data/raw/{nbaiot,
  ciciot2023,edge_iiotset}` expected under the symlink target.
- **Unit tests:** `test_reuse_policy_doc.py::test_stage_classification_complete`;
  `::test_invalidation_triggers_listed`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_threshold_stage_not_marked_heavy`.
- **Acceptance:** Stage table + triggers + placement documented.
- **Definition of done:** Doc + tests green; changelog updated.
- **Reviewer risk:** L27/L28 reproducibility; duplicated-pipeline risk.
- **Runtime/reuse impact:** Defines the whole reuse discipline.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Enforced in code by P4-T08 no-retrain guard and P7-T09 audit.

#### P0-T10 — Old DATP behavioral-reference extraction
- **Phase / Status:** 0 / Done
- **Purpose:** Extract, from `/home/naslouby/Projects/datp`, only the behavioral
  semantics needed (threshold policy math, split semantics, scoring, metric defs).
- **Scientific reason:** Preserve exact DATP behavior without inheriting layout.
- **Engineering reason:** Prevents accidental structural/code copying.
- **Inputs:** Reference project (read-only); roadmap §17 behavior notes.
- **Outputs:** `docs/protocol/behavioral_reference.md` (behavior notes only, no
  source paste, no layout, with explicit "reference only" banner-free statement).
- **Files/modules:** `docs/protocol/behavioral_reference.md`.
- **Dependencies:** P0-T04, P0-T09.
- **Implementation tasks:** Record p95 semantics, n_min=100 eligibility + τ_global
  fallback, CV(FPR) formula, B1 arithmetic-mean-of-local-p95, B4 fingerprint,
  benign-only calibration split semantics, checkpoint protocol; cite reference as
  behavioral only.
- **Unit tests:** `test_behavioral_reference.py::test_no_source_paths_copied`
  (doc references reference project only as behavioral; no old module names as
  targets).
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `::test_no_backward_compat_language`.
- **Acceptance:** Behavior captured; no layout/source inheritance.
- **Definition of done:** Doc + test green; changelog updated.
- **Reviewer risk:** L27 inherited/messy code.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze.
- **Changelog update:** required.
- **Notes:** Consulted by P3 (policy math) and P2-T04 (split semantics).

#### P0-T11 — Repository structure decision, changelog format & go/no-go coding gate
- **Phase / Status:** 0 / Done
- **Purpose:** Ratify §5 structure decision, lock the CHANGELOG format/update
  contract, and record the go/no-go gate that authorizes Phase 1 coding.
- **Scientific reason:** Ensures the build starts only after identity/claims/
  regimes/contracts are frozen.
- **Engineering reason:** Single authorization point; changelog format is fixed
  before any progress is logged.
- **Inputs:** §5 of this doc; brief changelog requirements; ai/hooks/`final_report_hook.md`.
- **Outputs:** `docs/protocol/structure_decision.md`; `docs/protocol/go_no_go.md`;
  initial `CHANGELOG.md` (created here) with dashboard + tables + update template.
- **Files/modules:** those docs; `CHANGELOG.md`.
- **Dependencies:** P0-T01…P0-T10.
- **Implementation tasks:** Record accepted/changed/rejected structure; encode
  changelog status enum (Not Started/In Progress/Blocked/Done/Skipped/Split/
  Merged/Reopened); state go/no-go criteria (all P0 docs signed, tests green).
- **Unit tests:** `test_changelog_format.py::test_dashboard_fields_present`;
  `::test_status_enum_values`; `::test_update_template_present`.
- **Integration tests:** `test_changelog_update_after_ticket.py` (see P1-T10).
- **Smoke/E2E:** none.
- **Negative tests:** `test_changelog_format.py::test_no_experimental_claims_in_changelog`.
- **Acceptance:** Structure ratified; CHANGELOG created and schema-valid; go/no-go signed.
- **Definition of done:** Docs + CHANGELOG + tests green; changelog updated (self).
- **Reviewer risk:** L25/L27/L28.
- **Runtime/reuse impact:** none.
- **Stage class:** Documentation/freeze + testing.
- **Changelog update:** required (this ticket creates the CHANGELOG).
- **Notes:** **Phase 0 exit gate.** No Phase 1 code before this is Done.

---

### Phase 1 — Scratch Foundation

Buildable code begins here. All tickets are cheap-stage; they create the typed
substrate every later stage depends on. **Entry gate:** P0-T11 go/no-go Done.

> **Implementation note (2026-07-09, Phase 1 exit).** Phase 1 was executed
> under an alternate, more granular 18-ticket breakdown (P1-T01..P1-T18)
> supplied directly by the requesting user for the implementation session,
> which explicitly authorized splitting/renumbering this plan and required
> recording the deviation (see `CHANGELOG.md` §12). The ten ticket bodies
> below (original P1-T01..P1-T10) are preserved as the historical plan
> record and are **not** rewritten; their status lines still read
> `Not Started` because none of them was executed verbatim under its
> original ID. Disposition:
>
> - Original P1-T01 (skeleton/tooling), P1-T02 (domain enums), P1-T03
>   (seed-plan types), P1-T04 (typed config system), P1-T05 (path resolver),
>   P1-T06 (determinism/hardware/logging), and P1-T07 (manifest schema +
>   no-overwrite) are all **implemented**, split across new P1-T01..P1-T11 —
>   see `CHANGELOG.md` §3/§5 for the exact new-ticket-to-file mapping.
> - Original P1-T08 (preprocessing cache contract, `data/cache.py`) is
>   **not implemented**; deferred to Phase 2 (`CHANGELOG.md` §11).
> - Original P1-T09 (CLI entrypoint & dataset registry) is **partially
>   implemented**: the dataset registry (new P1-T06) and a read-only CLI
>   skeleton (new P1-T12) exist; the suite run-dispatcher, plan/runner/
>   readiness-gate modules, and `scripts/run_experiment.py` are **not
>   implemented** — Phase 1's CLI never runs heavy work by design. Deferred
>   to Phase 2 (`CHANGELOG.md` §11).
> - Original P1-T10 (test fixtures & CHANGELOG-enforcement test) is
>   **partially implemented**: tiny deterministic fixtures exist (new
>   P1-T13); the programmatic CHANGELOG/master-log consistency test
>   (`test_changelog_update_after_ticket.py`) is **not implemented** —
>   deferred (`CHANGELOG.md` §11).
>
> Phase 1 moved the plan-of-record total from 82 to 90 (10 → 18 tickets).
> The authorized Phase 2 breakdown below moves it from 90 to 99 (11 → 20
> tickets); see `CHANGELOG.md` §2/§12.

#### P1-T01 — Project skeleton, pyproject, tooling & Makefile
- **Phase / Status:** 1 / Not Started
- **Purpose:** Create `src/datp_core/` package, `pyproject.toml` (uv), `ruff` +
  `pyright` + `pytest` config, `Makefile`, `.gitignore` additions, `.env.example`.
- **Scientific reason:** None directly; enables reproducible tooling.
- **Engineering reason:** Deterministic, lint/type-clean foundation.
- **Inputs:** §5 structure decision; governance dependency policy.
- **Outputs:** `pyproject.toml`, `uv.lock`, `Makefile`, `src/datp_core/__init__.py`,
  `.env.example`, `.gitignore` (raw/checkpoints/outputs ignored).
- **Files/modules:** repo root; `src/datp_core/__init__.py`.
- **Dependencies:** P0-T11.
- **Implementation tasks:** Pin Python + torch/numpy/scipy/scikit-learn/pyyaml;
  `make test|lint|typecheck|smoke`; ensure `data/raw`, `checkpoints/`, `outputs/`
  gitignored; no release/version metadata.
- **Unit tests:** `test_package_import.py::test_import_datp_core`.
- **Integration tests:** `test_tooling.py::test_make_targets_exist`.
- **Smoke/E2E:** `make smoke` runs empty-suite no-op successfully.
- **Negative tests:** `test_tooling.py::test_no_citation_or_versioning_files`.
- **Acceptance:** `uv sync`, `ruff`, `pyright`, `pytest` all run clean on empty package.
- **Definition of done:** Toolchain green; changelog updated.
- **Reviewer risk:** L27/L28.
- **Runtime/reuse impact:** none.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** No `CITATION.cff`/`VERSIONING.md` (governance).

#### P1-T02 — Domain enums & metric registry
- **Phase / Status:** 1 / Not Started
- **Purpose:** Implement `Regime`, `ClientKind`, `ThresholdPolicy`, `Comparator`,
  `Dataset`, `ClaimRole`, and a metric registry (name → direction → claim role).
- **Scientific reason:** Encodes locked nomenclature/regimes/claim roles as types.
- **Engineering reason:** Prefer explicit enums over raw strings/dicts (governance).
- **Inputs:** P0-T02/T03/T04 docs.
- **Outputs:** `domain/regimes.py`, `domain/clients.py`, `domain/policies.py`,
  `domain/datasets.py`, `domain/metrics.py`.
- **Files/modules:** `src/datp_core/domain/*`.
- **Dependencies:** P1-T01.
- **Implementation tasks:** Frozen enums; metric registry with fields
  {higher_is_better, is_control, claim_role, eligibility_rule}; CV(FPR) marked
  primary, AUROC marked control.
- **Unit tests:** `test_enums.py::test_policies_match_protocol_doc`;
  `test_metrics_registry.py::test_auroc_is_control`,
  `::test_cvfpr_is_primary`, `::test_no_stale_policy_names`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_enums.py::test_b0_flagged_not_in_causal_ladder`;
  `::test_bb_regime_flagged_rejected`.
- **Acceptance:** Enums exactly match protocol docs; registry roles correct.
- **Definition of done:** Types + tests green; changelog updated.
- **Reviewer risk:** L04/L06/L17 metric-role confusion.
- **Runtime/reuse impact:** none.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Imported everywhere; single source for policy/metric identity.

#### P1-T03 — Seed-plan types
- **Phase / Status:** 1 / Not Started
- **Purpose:** Typed `SeedPlan`/`PairedSeed` with roles and paired-RNG derivation.
- **Scientific reason:** Guarantees B1 & B2 share identical AE state per seed.
- **Engineering reason:** Deterministic, testable pairing.
- **Inputs:** P0-T07 seed plan.
- **Outputs:** `domain/seeds.py`; `utils/random.py`.
- **Files/modules:** `src/datp_core/domain/seeds.py`, `src/datp_core/utils/random.py`.
- **Dependencies:** P1-T02.
- **Implementation tasks:** 10-seed plan, 5-seed preliminary subset, paired RNG
  spawns (train vs split vs bootstrap streams) derived from one seed.
- **Unit tests:** `test_seeds.py::test_ten_paired_seeds`,
  `::test_paired_streams_deterministic`, `::test_5seed_is_prefix_of_10`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_seeds.py::test_reject_duplicate_or_missing_seed`,
  `::test_reject_invalid_seed_plan`.
- **Acceptance:** Deterministic reproducible streams; invalid plans rejected.
- **Definition of done:** Types + tests green; changelog updated.
- **Reviewer risk:** L23 seed integrity.
- **Runtime/reuse impact:** Seeds key checkpoint/score reuse identity.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Used by P2-T06 training and P2-T09 paired eval.

#### P1-T04 — Typed config system (loader, schemas, validation)
- **Phase / Status:** 1 / Not Started
- **Purpose:** YAML → typed dataclass configs with consistency validation.
- **Scientific reason:** No hidden defaults that change threshold semantics.
- **Engineering reason:** Typed configs over raw dicts; fail-fast validation.
- **Inputs:** P0-T06 naming conventions; config groups.
- **Outputs:** `config/loader.py`, `config/schemas.py`, `config/validation.py`;
  seed `configs/datasets|training|thresholding|analysis|suites/` skeletons.
- **Files/modules:** `src/datp_core/config/*`, `configs/**`.
- **Dependencies:** P1-T02, P1-T03.
- **Implementation tasks:** Frozen dataclass schemas per group; validation rules:
  q ∈ (0,1); n_min ≥ 1; policy names ∈ enum; B4 K ≥ 1 with canonical=3; suite
  references known experiment IDs; benign-only flag present on calibration configs.
- **Unit tests:** `test_config_validation.py::test_valid_configs_load`,
  `::test_reject_invalid_q`, `::test_reject_unknown_policy`,
  `::test_reject_stale_policy_name`, `::test_reject_missing_benign_only_flag`.
- **Integration tests:** `test_config_roundtrip.py::test_all_shipped_configs_valid`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_config_validation.py::test_reject_hardcoded_abs_path`,
  `::test_reject_unknown_experiment_id_in_suite`.
- **Acceptance:** All shipped configs validate; invalid ones rejected with typed errors.
- **Definition of done:** Config system + tests green; changelog updated.
- **Reviewer risk:** L23 HARKing (config drift); reproducibility.
- **Runtime/reuse impact:** Config identity feeds manifests/reuse keys.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Every runtime ticket loads configs through this system only.

#### P1-T05 — Canonical path resolver
- **Phase / Status:** 1 / Not Started
- **Purpose:** Single resolver for data/preprocessed/checkpoints/outputs/results.
- **Scientific reason:** None; provenance correctness.
- **Engineering reason:** No hardcoded absolute paths anywhere else.
- **Inputs:** §5 layout; `data/raw` symlink; `.env.example`.
- **Outputs:** `utils/paths.py`.
- **Files/modules:** `src/datp_core/utils/paths.py`.
- **Dependencies:** P1-T01.
- **Implementation tasks:** Resolve roots from repo + optional `DATP_DATA_ROOT`
  override; expose typed path builders keyed by (dataset, regime, seed, artifact).
- **Unit tests:** `test_paths.py::test_resolves_raw_symlink`,
  `::test_artifact_paths_stable`, `::test_env_override_respected`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_paths.py::test_reject_hardcoded_abs_path`,
  `::test_reject_wrong_dataset_root`, `::test_missing_raw_root_raises`.
- **Acceptance:** All paths derive from resolver; symlink honored; overrides work.
- **Definition of done:** Resolver + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Path identity underlies reuse keys.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Only module allowed to know filesystem layout.

#### P1-T06 — Runtime utilities (determinism, hardware, logging)
- **Phase / Status:** 1 / Not Started
- **Purpose:** Deterministic setup, device/VRAM selection with CPU fallback, and
  structured logging helpers.
- **Scientific reason:** Deterministic seeds are required for paired reproducibility.
- **Engineering reason:** Centralized, testable runtime setup.
- **Inputs:** P0-T07 seed plan; hardware constraints.
- **Outputs:** `utils/determinism.py`, `utils/hardware.py`, `utils/logging.py`,
  `utils/typing.py`.
- **Files/modules:** `src/datp_core/utils/*`.
- **Dependencies:** P1-T03.
- **Implementation tasks:** Lock Python/NumPy/Torch RNG + cudnn deterministic;
  device select (CUDA→CPU fallback, VRAM cap); JSON-line logging.
- **Unit tests:** `test_determinism.py::test_seed_lock_reproducible`;
  `test_hardware.py::test_cpu_fallback_when_no_cuda`,
  `::test_vram_limit_respected`.
- **Integration tests:** `test_determinism.py::test_two_runs_identical_scores` (tiny AE).
- **Smoke/E2E:** none.
- **Negative tests:** `test_hardware.py::test_reject_invalid_device_request`.
- **Acceptance:** Identical outputs across two runs; graceful device fallback.
- **Definition of done:** Utils + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Determinism is a reuse-validity precondition.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Training/scoring tickets call these first.

#### P1-T07 — Manifest schema, artifact writer/reader & no-overwrite policy
- **Phase / Status:** 1 / Not Started
- **Purpose:** Typed manifests (hashes/IDs) + safe artifact I/O that refuses
  silent overwrite.
- **Scientific reason:** Reuse validity requires exact identity matching.
- **Engineering reason:** Prevents accidental mismatch and silent clobbering.
- **Inputs:** P0-T05 artifact contracts.
- **Outputs:** `data/manifests.py` writer/reader, `experiments/artifacts.py`,
  `experiments/provenance.py`; `outputs/README.md`, `checkpoints/README.md`.
- **Files/modules:** `src/datp_core/data/manifests.py`,
  `src/datp_core/experiments/{artifacts,provenance}.py`.
- **Dependencies:** P1-T04, P1-T05.
- **Implementation tasks:** Manifest fields {dataset, regime, seed, preprocess_hash,
  split_hash, checkpoint_hash, scoring_contract_id, config_hash, created_at};
  write→(compute hash, refuse if exists unless explicit new version dir); read→verify.
- **Unit tests:** `test_provenance.py::test_manifest_roundtrip`,
  `::test_reuse_key_mismatch_detected`.
- **Integration tests:** `test_no_overwrite.py::test_second_write_refused`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_no_overwrite.py::test_silent_overwrite_attempt_raises`;
  `test_provenance.py::test_score_checkpoint_mismatch_rejected`.
- **Acceptance:** Round-trip stable; mismatches + overwrites rejected.
- **Definition of done:** Manifest I/O + tests green; changelog updated.
- **Reviewer risk:** L27/L28 provenance.
- **Runtime/reuse impact:** **Core reuse-enforcement mechanism.**
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Every heavy/cheap artifact ticket writes through this.

#### P1-T08 — Preprocessing cache contract
- **Phase / Status:** 1 / Not Started
- **Purpose:** Cache preprocessed artifacts with validity keyed to raw hash +
  preprocessing config.
- **Scientific reason:** Preprocessing change is a heavy-rerun trigger.
- **Engineering reason:** Avoids recomputation; detects stale caches.
- **Inputs:** P0-T09 reuse policy; P1-T07 manifests.
- **Outputs:** `data/cache.py`; `data/manifests/preprocessing_manifest.json` schema.
- **Files/modules:** `src/datp_core/data/cache.py`.
- **Dependencies:** P1-T07.
- **Implementation tasks:** Cache key = raw_hash + preprocess_config_hash; hit
  returns artifact + manifest; miss/invalid recomputes; never silently reuse on
  key mismatch.
- **Unit tests:** `test_cache.py::test_cache_hit_on_match`,
  `::test_cache_invalidated_on_config_change`.
- **Integration tests:** `test_cache.py::test_preprocess_then_reuse`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_cache.py::test_stale_cache_rejected_on_raw_change`.
- **Acceptance:** Deterministic hit/miss/invalidation.
- **Definition of done:** Cache + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Gatekeeps heavy preprocessing reruns.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** Consumed by P2-T02 and P6-T03 preprocessing.

#### P1-T09 — CLI entrypoint & dataset registry
- **Phase / Status:** 1 / Not Started
- **Purpose:** `datp` CLI + `scripts/run_experiment.py` dispatch; dataset registry
  mapping `Dataset` → loader/metadata.
- **Scientific reason:** None; single controlled execution surface.
- **Engineering reason:** No hidden one-off scripts; suites run through one path.
- **Inputs:** P1-T04 configs; P0-T06 suite names.
- **Outputs:** `cli.py`, `experiments/plan.py`, `experiments/runner.py`,
  `experiments/readiness.py`, `scripts/run_experiment.py`.
- **Files/modules:** `src/datp_core/cli.py`, `src/datp_core/experiments/*`,
  `scripts/run_experiment.py`.
- **Dependencies:** P1-T04, P1-T07.
- **Implementation tasks:** `datp run <suite>`; plan expands suite → run cells;
  readiness gate runs before any expensive execution; registry lookups typed.
- **Unit tests:** `test_cli.py::test_run_dispatches_known_suite`;
  `test_dataset_registry.py::test_registry_covers_all_datasets`.
- **Integration tests:** `test_runner_plan.py::test_suite_expands_to_expected_cells`.
- **Smoke/E2E:** `test_clean_pipeline_smoke.py` (empty/tiny suite dispatch).
- **Negative tests:** `test_cli.py::test_reject_unknown_suite`;
  `test_dataset_registry.py::test_reject_unknown_dataset`.
- **Acceptance:** Suites dispatch; readiness gate blocks unready runs.
- **Definition of done:** CLI + tests green; changelog updated.
- **Reviewer risk:** L27 messy/one-off code.
- **Runtime/reuse impact:** Readiness gate prevents redundant heavy runs.
- **Stage class:** Foundation (cheap).
- **Changelog update:** required.
- **Notes:** All later heavy/cheap runs invoked via this entrypoint.

#### P1-T10 — Test fixtures & CHANGELOG update-enforcement test
- **Phase / Status:** 1 / Not Started
- **Purpose:** Ship deterministic tiny fixtures and the test that enforces the
  CHANGELOG update contract.
- **Scientific reason:** Fixtures let cheap-stage tests run without heavy compute.
- **Engineering reason:** Guarantees progress tracking stays synchronized.
- **Inputs:** §5 fixtures; P0-T11 changelog format.
- **Outputs:** `tests/fixtures/{tiny_scores.json, tiny_clients.yaml,
  tiny_edge_iiotset.yaml, absorption_bands.yaml, b_fedstats_benign_scores.json}`;
  `tests/unit/test_changelog_format.py`, `tests/integration/test_changelog_update_after_ticket.py`.
- **Files/modules:** `tests/fixtures/*`, changelog tests.
- **Dependencies:** P1-T07, P0-T11.
- **Implementation tasks:** Build minimal benign/attack score fixtures with known
  CV(FPR); implement changelog parser + assertions (dashboard fields, status
  enum, per-ticket update template, no experimental claims).
- **Unit tests:** `test_changelog_format.py::test_dashboard_present`,
  `::test_status_values_valid`, `::test_ticket_table_columns`,
  `::test_phase_table_columns`, `::test_no_result_claims`.
- **Integration tests:** `test_changelog_update_after_ticket.py::test_marking_done_requires_tests_run_entry`,
  `::test_blocked_ticket_requires_blocker_entry`,
  `::test_changelog_status_matches_master_ticket_log`.
- **Smoke/E2E:** `test_agent_progress_update_sim.py` marks a dummy ticket Done and
  validates the appended block.
- **Negative tests:** `test_changelog_update_after_ticket.py::test_missing_tests_run_entry_fails`,
  `::test_status_mismatch_with_master_log_fails`.
- **Acceptance:** Fixtures deterministic; changelog contract enforced by tests.
- **Definition of done:** Fixtures + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility; progress integrity.
- **Runtime/reuse impact:** none.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required. **Phase 1 exit gate.**
- **Notes:** Fixtures reused across P3/P4/P5 cheap-stage tests.

---

### Phase 2 — Anchor Reproduction Pipeline

Builds the reusable heavy backbone for Regime A and produces the frozen
checkpoints + stored score artifacts every cheap stage consumes. **Entry gate:**
P1-T10 Done. **Exit gate:** anchor smoke green + frozen checkpoints + scores +
provenance manifests exist for ≥ 2 seeds.

> **2026-07-09 authorized Phase 2 breakdown.** The requesting user supplied a
> more granular 20-ticket Phase 2 contract (P2-T01..P2-T20), explicitly
> replacing the eleven historical bodies below for implementation tracking.
> The current ticket mapping and status are maintained in `CHANGELOG.md` §3/§5:
> entry gate; discovery; loader; client mapping; splits; leakage manifests; AE;
> FedAvg; checkpoints; scoring; score reuse; B1/B2; metrics; aggregation;
> paired plan; safe commands; unit, integration, and smoke tests; quality gate.
> The historical bodies remain below for design provenance and their `Not Started`
> status lines do not describe the authorized Phase 2 implementation work.

#### P2-T01 — N-BaIoT loader & schema
- **Phase / Status:** 2 / Not Started
- **Purpose:** Typed N-BaIoT loader with schema + device identity validation.
- **Scientific reason:** Regime A depends on the 9 natural physical devices.
- **Engineering reason:** Fail-fast on missing/malformed raw data.
- **Inputs:** `data/raw/nbaiot/*`; P0-T05 dataset contract.
- **Outputs:** `data/nbaiot.py`; `data/manifests/dataset_manifest.json` entry.
- **Files/modules:** `src/datp_core/data/nbaiot.py`.
- **Dependencies:** P1-T07, P1-T09.
- **Implementation tasks:** Load per-device benign/attack; validate 9 devices,
  feature schema, benign/attack labels; write dataset manifest with hashes.
- **Unit tests:** `test_nbaiot_loader.py::test_nine_devices_present`,
  `::test_feature_schema_matches_contract`, `::test_benign_attack_labels_present`.
- **Integration tests:** `test_nbaiot_loader.py::test_manifest_written_with_hashes`.
- **Smoke/E2E:** covered by anchor smoke (P2-T10).
- **Negative tests:** `test_nbaiot_loader.py::test_missing_raw_dataset_raises`,
  `::test_wrong_dataset_root_raises`, `::test_mixed_client_ids_rejected`.
- **Acceptance:** 9 devices load; manifest hashes stable; bad inputs rejected.
- **Definition of done:** Loader + tests green; changelog updated.
- **Reviewer risk:** L14 client validity; L28 provenance.
- **Runtime/reuse impact:** Raw hash keys preprocessing cache.
- **Stage class:** Heavy-adjacent (I/O); cached downstream.
- **Changelog update:** required.
- **Notes:** Feasibility facts (device IDs) verified, never assumed (Tier 9).

#### P2-T02 — N-BaIoT preprocessing & cache
- **Phase / Status:** 2 / Not Started
- **Purpose:** Reusable preprocessing (feature scaling on benign-train stats) with cache.
- **Scientific reason:** Preprocessing must be benign-fit only; leakage-free.
- **Engineering reason:** Expensive; cached and reused across seeds/policies.
- **Inputs:** P2-T01 loaded data; P1-T08 cache.
- **Outputs:** `data/preprocessing.py`; `data/preprocessed/nbaiot/*` + manifest.
- **Files/modules:** `src/datp_core/data/preprocessing.py`.
- **Dependencies:** P2-T01, P1-T08.
- **Implementation tasks:** Fit scaler on benign-train only; transform cal/test;
  persist with preprocessing manifest; cache-key on raw+config hash.
- **Unit tests:** `test_preprocessing.py::test_scaler_fit_on_benign_train_only`,
  `::test_transform_deterministic`.
- **Integration tests:** `test_preprocessing.py::test_preprocess_cached_and_reused`.
- **Smoke/E2E:** anchor smoke (P2-T10).
- **Negative tests:** `test_preprocessing.py::test_attack_not_used_in_fit`,
  `::test_test_stats_not_leaked_into_fit`.
- **Acceptance:** Benign-only fit; cache hit on rerun; no leakage.
- **Definition of done:** Preprocessing + tests green; changelog updated.
- **Reviewer risk:** L03 overfit/leakage.
- **Runtime/reuse impact:** **Heavy; reusable artifact.** Rerun only on preprocess change.
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Reused identically by every Regime A downstream stage.

#### P2-T03 — Physical-device partition builder
- **Phase / Status:** 2 / Not Started
- **Purpose:** Build the K=9 physical-device partition (Regime A clients).
- **Scientific reason:** Natural device split is the confirmatory substrate.
- **Engineering reason:** Deterministic, typed partition object.
- **Inputs:** P2-T01 device identity.
- **Outputs:** `partitioning/physical_device.py`; partition manifest.
- **Files/modules:** `src/datp_core/partitioning/physical_device.py`.
- **Dependencies:** P2-T01.
- **Implementation tasks:** Map devices→clients; freeze client IDs; emit manifest.
- **Unit tests:** `test_partitions.py::test_physical_device_k9`,
  `::test_client_ids_stable`.
- **Integration tests:** none.
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_partitions.py::test_reject_mixed_client_ids`.
- **Acceptance:** Nine stable clients; deterministic.
- **Definition of done:** Partition + tests green; changelog updated.
- **Reviewer risk:** L14 client validity.
- **Runtime/reuse impact:** Partition identity keys splits/scores.
- **Stage class:** Cheap.
- **Changelog update:** required.
- **Notes:** Sibling builders (file-level, group, Dirichlet) added in P6.

#### P2-T04 — Benign train/calibration/test split semantics & split manifest
- **Phase / Status:** 2 / Not Started
- **Purpose:** Construct benign-only train/cal splits + benign/attack test split,
  with a split manifest.
- **Scientific reason:** Benign-only calibration; no cal/test overlap; n_min=100 eligibility.
- **Engineering reason:** Type-level separation of calibration vs test data.
- **Inputs:** P2-T02 preprocessed; P2-T03 partition; P0-T10 behavior notes.
- **Outputs:** `data/splits.py`; split manifest per (seed, client).
- **Files/modules:** `src/datp_core/data/splits.py`.
- **Dependencies:** P2-T02, P2-T03.
- **Implementation tasks:** Per client: benign→train/cal disjoint; test=held-out
  benign+attack; eligibility n_k≥100 flag; typed `CalibrationData`/`TestData`.
- **Unit tests:** `test_splits.py::test_benign_only_calibration`,
  `::test_no_cal_test_overlap`, `::test_eligibility_flag_at_100`.
- **Integration tests:** `test_splits.py::test_split_manifest_roundtrip`.
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_splits.py::test_attack_in_calibration_rejected`,
  `::test_cal_test_overlap_rejected`, `::test_ineligible_client_flagged`.
- **Acceptance:** Disjoint benign-only cal; eligibility correct; manifest stable.
- **Definition of done:** Splits + tests green; changelog updated.
- **Reviewer risk:** L03 leakage; L04 tautology (test-FPR measured, not cal).
- **Runtime/reuse impact:** Split hash keys scores/reuse.
- **Stage class:** Cheap (but identity-critical).
- **Changelog update:** required.
- **Notes:** `CalibrationData`/`TestData` types prevent leakage at compile time.

#### P2-T05 — Autoencoder architecture
- **Phase / Status:** 2 / Not Started
- **Purpose:** Fixed AE architecture (per roadmap behavior; no BatchNorm — SB-02).
- **Scientific reason:** Fixed-encoder identity; input_dim per dataset (SB-13).
- **Engineering reason:** Single typed model definition.
- **Inputs:** P0-T10 behavior; `configs/training/base_autoencoder.yaml`.
- **Outputs:** `models/autoencoder.py`.
- **Files/modules:** `src/datp_core/models/autoencoder.py`.
- **Dependencies:** P1-T04.
- **Implementation tasks:** Config-driven dims; reconstruction AE; no BatchNorm;
  deterministic init from seed.
- **Unit tests:** `test_autoencoder.py::test_forward_shape`,
  `::test_no_batchnorm_layers`, `::test_deterministic_init`.
- **Integration tests:** none.
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_autoencoder.py::test_reject_mismatched_input_dim`.
- **Acceptance:** Deterministic AE; no BatchNorm; config-driven dims.
- **Definition of done:** Model + tests green; changelog updated.
- **Reviewer risk:** L01 triviality; SB-02/SB-13 identity.
- **Runtime/reuse impact:** Architecture change = heavy-rerun trigger.
- **Stage class:** Cheap (definition) / heavy when trained.
- **Changelog update:** required.
- **Notes:** Same class reused (different input_dim) for Edge-IIoTset.

#### P2-T06 — FedAvg training loop
- **Phase / Status:** 2 / Not Started
- **Purpose:** Core FedAvg (E=1, full participation) training per seed.
- **Scientific reason:** Main training baseline for the causal ladder.
- **Engineering reason:** Deterministic, checkpointable server/client loop.
- **Inputs:** P2-T04 splits; P2-T05 AE; P1-T06 determinism; seed plan.
- **Outputs:** `federation/{client,server,fedavg}.py`; trained state per seed.
- **Files/modules:** `src/datp_core/federation/*`.
- **Dependencies:** P2-T05, P2-T04, P1-T06.
- **Implementation tasks:** Local benign-train updates; FedAvg aggregation; round
  budget to 200; deterministic; logs convergence as diagnostic metadata only.
- **Unit tests:** `test_fedavg.py::test_aggregation_is_weighted_mean`,
  `::test_e1_full_participation`, `::test_deterministic_given_seed`.
- **Integration tests:** `test_fedavg_tiny.py::test_two_client_tiny_converges` (fixture).
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_fedavg.py::test_reject_attack_data_in_training`.
- **Acceptance:** Deterministic FedAvg; benign-only; convergence logged not gated.
- **Definition of done:** Training + tests green; changelog updated.
- **Reviewer risk:** L13 comparator fairness (E/rounds locked).
- **Runtime/reuse impact:** **Heavy; trains the shared AE once per seed.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** FedProx (P6-T10) mirrors this loop with µ term, outside ladder.

#### P2-T07 — Checkpoint save/select & freeze/read-only loading
- **Phase / Status:** 2 / Not Started
- **Purpose:** Train-once/save-many checkpoints at {25,50,75,100,125,150,200};
  Regime-A global selection; read-only frozen loading for B1–B4.
- **Scientific reason:** No test-metric checkpoint selection; one global primary
  checkpoint drives every main-regime table (roadmap §10).
- **Engineering reason:** Immutable weight vault; frozen loads for reuse.
- **Inputs:** P2-T06 trained states; checkpoint protocol.
- **Outputs:** `models/checkpoints.py`, `models/frozen.py`; `checkpoints/fedavg/nbaiot/*`.
- **Files/modules:** `src/datp_core/models/{checkpoints,frozen}.py`.
- **Dependencies:** P2-T06, P1-T07.
- **Implementation tasks:** Save all rounds + hashes; selection rule uses only
  benign/diagnostic criteria (never test AUROC/attack); frozen loader is read-only.
- **Unit tests:** `test_checkpoints.py::test_all_rounds_saved`,
  `::test_selection_ignores_test_metrics`, `::test_frozen_load_is_readonly`.
- **Integration tests:** `test_checkpoint_freeze.py::test_frozen_checkpoint_reused_across_ladder`.
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_checkpoints.py::test_checkpoint_selection_by_test_auroc_rejected`,
  `::test_write_to_frozen_checkpoint_rejected`.
- **Acceptance:** Checkpoints hashed + frozen; selection science-valid; reuse proven.
- **Definition of done:** Checkpoints + tests green; changelog updated.
- **Reviewer risk:** L08 HARKing; §10 checkpoint protocol.
- **Runtime/reuse impact:** **Heavy artifact; the fixed-encoder vault.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Same frozen state reused by B1–B4 and all variants (no retrain).

#### P2-T08 — Score generation & score-artifact contract
- **Phase / Status:** 2 / Not Started
- **Purpose:** Generate per-client benign/attack reconstruction scores from the
  frozen checkpoint; persist under a versioned scoring contract.
- **Scientific reason:** Scores are the reusable substrate for all thresholds.
- **Engineering reason:** Reuse valid only when dataset/split/checkpoint/preprocess/
  seed/scoring-contract match exactly.
- **Inputs:** P2-T07 frozen checkpoint; P2-T04 splits.
- **Outputs:** `models/scoring.py`; `outputs/scores/nbaiot/*` + score manifest.
- **Files/modules:** `src/datp_core/models/scoring.py`.
- **Dependencies:** P2-T07.
- **Implementation tasks:** Reconstruction error per sample; store cal + test
  benign/attack scores per client; manifest binds all six reuse keys + scoring_contract_id.
- **Unit tests:** `test_scoring.py::test_scores_deterministic`,
  `::test_score_manifest_has_all_reuse_keys`.
- **Integration tests:** `test_scoring.py::test_scores_reload_and_match_checkpoint`.
- **Smoke/E2E:** anchor smoke.
- **Negative tests:** `test_scoring.py::test_scores_from_wrong_checkpoint_rejected`,
  `::test_score_checkpoint_hash_mismatch_rejected`.
- **Acceptance:** Deterministic scores; manifest binds reuse identity; mismatch rejected.
- **Definition of done:** Scoring + tests green; changelog updated.
- **Reviewer risk:** L27/L28 provenance.
- **Runtime/reuse impact:** **Heavy artifact; consumed by all of P3/P4/P5.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** The single most-reused artifact; the reuse contract lives or dies here.

#### P2-T09 — B1/B2 anchor evaluation & 10-seed paired plan
- **Phase / Status:** 2 / Not Started
- **Purpose:** Wire B1 and B2 over stored scores, per-seed paired, into CV(FPR)
  and Δ_s across the seed plan.
- **Scientific reason:** This is the confirmatory comparator wiring (B1 vs B2).
- **Engineering reason:** Reuses scores; no retraining across seeds/policies.
- **Inputs:** P2-T08 scores; P1-T03 seed plan.
- **Outputs:** `experiments` cell producing per-seed CV(FPR)[B1], CV(FPR)[B2], Δ_s.
- **Files/modules:** thresholding B1/B2 (interim; formalized in P3), `experiments/plan.py`.
- **Dependencies:** P2-T08, P1-T03.
- **Implementation tasks:** For each seed: B1=mean local p95, B2=per-client p95 →
  eval FPR on test benign → CV(FPR) → Δ_s; paired across identical AE state.
- **Unit tests:** `test_anchor_eval.py::test_b1_is_mean_of_local_p95`,
  `::test_b2_is_per_client_p95`, `::test_delta_is_b1_minus_b2`.
- **Integration tests:** `test_anchor_eval.py::test_paired_seeds_reuse_same_checkpoint`.
- **Smoke/E2E:** 2-seed mini-run (P2-T10/P2-T11).
- **Negative tests:** `test_anchor_eval.py::test_reject_unpaired_b1_b2_states`.
- **Acceptance:** Per-seed Δ_s produced from reused scores; pairing enforced.
- **Definition of done:** Eval + tests green; changelog updated.
- **Reviewer risk:** L04 tautology; L23 pairing integrity.
- **Runtime/reuse impact:** Cheap; reuses scores across all 10 seeds.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** B1/B2 finalized as formal policies in P3-T04/T05.

#### P2-T10 — Anchor smoke run & provenance
- **Phase / Status:** 2 / Not Started
- **Purpose:** Tiny end-to-end Regime A run (fixtures) proving load→preprocess→
  split→train→freeze→score→B1/B2 with full lineage.
- **Scientific reason:** Confirms the pipeline is leakage-free and reproducible.
- **Engineering reason:** Fast CI gate for the heavy backbone.
- **Inputs:** Fixtures (P1-T10); all P2 modules.
- **Outputs:** `tests/integration/test_clean_pipeline_smoke.py` (Regime A path).
- **Files/modules:** integration tests + fixtures.
- **Dependencies:** P2-T01…P2-T09.
- **Implementation tasks:** Wire a tiny N-BaIoT-like fixture through the full chain;
  assert manifests chain config→checkpoint→scores→metrics.
- **Unit tests:** n/a (integration ticket).
- **Integration tests:** `test_clean_pipeline_smoke.py::test_full_regimeA_smoke`;
  `test_artifact_layout.py::test_outputs_checkpoints_results_layout`.
- **Smoke/E2E:** `test_nbaiot_like_fixture_run` (physical-device path).
- **Negative tests:** `test_clean_pipeline_smoke.py::test_broken_lineage_detected`.
- **Acceptance:** Smoke green in seconds; lineage verified; layout enforced.
- **Definition of done:** Smoke + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Uses fixtures only (no real heavy compute).
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Must stay fast; guards every future refactor of the backbone.

#### P2-T11 — Anchor statistical gate (gated production run)
- **Phase / Status:** 2 / Not Started
- **Purpose:** Gated ticket to execute the real 10-seed Regime A anchor and record
  CV(FPR)[B1,B2] + Δ_s per seed (no claim; implementation/validation focus).
- **Scientific reason:** Produces the substrate for the Tier-1 BCa CI (computed in P7).
- **Engineering reason:** Confirms heavy backbone runs at full scale reproducibly.
- **Inputs:** All P2 modules; P0-T07 seed plan; readiness gate.
- **Outputs:** `outputs/confirmatory/*` per-seed metrics + manifests (no results claim).
- **Files/modules:** runner; `outputs/confirmatory/`.
- **Dependencies:** P2-T09, P1-T09 readiness.
- **Implementation tasks:** Run 10 seeds via CLI; store per-seed Δ_s; verify
  reference-order sanity (B2<B1) as a diagnostic only; no CI/claim here.
- **Unit tests:** n/a.
- **Integration tests:** `test_anchor_production_gate.py::test_readiness_blocks_until_ready`.
- **Smoke/E2E:** 2-seed mini-run under CI; full 10-seed run is operator-gated.
- **Negative tests:** `test_anchor_production_gate.py::test_run_refused_without_frozen_checkpoints`.
- **Acceptance:** 10-seed per-seed Δ_s stored with manifests; gate enforced.
- **Definition of done:** Gated run wired + tests green; changelog updated.
  **Phase 2 exit gate.**
- **Reviewer risk:** L21/L23 seed honesty.
- **Runtime/reuse impact:** **Heavy; the once-per-seed run all cheap stages reuse.**
- **Stage class:** **Heavy (gated execution).**
- **Changelog update:** required — record seeds run, not any claim.
- **Notes:** CI computed later in P7-T03; this ticket produces substrate only.

---

### Phase 3 — Core Threshold Policies & Metrics

All cheap-stage: every ticket consumes frozen checkpoints + stored scores from
Phase 2. **Entry gate:** P2-T08 scores exist. **Exit gate:** B0–B4 + full metric
suite validated on synthetic fixtures with known values.

#### P3-T01 — Federated quantile backbone utility
- **Phase / Status:** 3 / Not Started
- **Purpose:** Single quantile-estimation interface underlying B0/B1/B1-pool/
  B1-wt/B2 and `B-FedStatsBenign`.
- **Scientific reason:** Uniform, auditable quantile vocabulary (RQ4 backbone); no
  novel estimator claimed.
- **Engineering reason:** One implementation prevents hand-waved percentile logic.
- **Inputs:** P2-T08 scores; P0-T10 behavior (p95).
- **Outputs:** `thresholding/quantiles.py`.
- **Files/modules:** `src/datp_core/thresholding/quantiles.py`.
- **Dependencies:** P1-T02.
- **Implementation tasks:** Local p_q, pooled p_q, weighted p_q, quantile-of-quantiles;
  estimation-error vs oracle; FPR-target attainment helper.
- **Unit tests:** `test_quantiles.py::test_local_p95_matches_numpy`,
  `::test_pooled_vs_weighted_quantile`, `::test_quantile_of_quantiles`,
  `::test_fpr_target_attainment`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_quantiles.py::test_reject_q_out_of_range`,
  `::test_reject_empty_score_vector`.
- **Acceptance:** All quantile forms correct; invalid q/empty rejected.
- **Definition of done:** Utility + tests green; changelog updated.
- **Reviewer risk:** L11 quantile novelty overclaim.
- **Runtime/reuse impact:** Cheap; shared by all threshold constructions.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** No novelty claim; framed as reproducibility/comparability device.

#### P3-T02 — Threshold-policy interface & contract validation
- **Phase / Status:** 3 / Not Started
- **Purpose:** Typed `ThresholdPolicy` protocol (calibration-in → per-client τ-out)
  + contract validation (benign-only input, eligibility handling).
- **Scientific reason:** Enforces benign-only calibration and eligibility at the type level.
- **Engineering reason:** Narrow interface; no raw dicts; frozen-input guarantee.
- **Inputs:** P3-T01; P2-T04 `CalibrationData`; P1-T02 policy enum.
- **Outputs:** `thresholding/base` protocol + `thresholding` validation.
- **Files/modules:** `src/datp_core/thresholding/__init__.py` (protocol), validation.
- **Dependencies:** P3-T01, P2-T04.
- **Implementation tasks:** Interface accepts only `CalibrationData`; n_min=100
  eligibility + τ_global fallback for pending clients; coverage report |K_elig|/|K|.
- **Unit tests:** `test_threshold_contract.py::test_policy_accepts_only_calibration_type`,
  `::test_eligibility_fallback_applied`, `::test_coverage_reported`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_threshold_contract.py::test_attack_input_type_rejected`,
  `::test_ineligible_client_threshold_misuse_rejected`.
- **Acceptance:** Contract enforced; eligibility/coverage correct.
- **Definition of done:** Interface + tests green; changelog updated.
- **Reviewer risk:** L03 leakage; L04 tautology.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** All B0–B4 + variants implement this one protocol.

#### P3-T03 — B0 centralized reference threshold
- **Phase / Status:** 3 / Not Started
- **Purpose:** B0 = pooled-benign pooled-p95 centralized reference.
- **Scientific reason:** Privacy-incompatible reference; **not** in the causal ladder.
- **Engineering reason:** Isolated policy; flagged non-ladder.
- **Inputs:** P3-T02; scores.
- **Outputs:** `thresholding/centralized.py`.
- **Files/modules:** `src/datp_core/thresholding/centralized.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** Pool benign cal across clients; pooled p95; single τ.
- **Unit tests:** `test_threshold_policies.py::test_b0_pooled_p95`,
  `::test_b0_flagged_not_in_ladder`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke (P3-T11 / integration).
- **Negative tests:** `test_threshold_policies.py::test_b0_not_counted_in_causal_delta`.
- **Acceptance:** Correct pooled p95; non-ladder flag enforced.
- **Definition of done:** B0 + tests green; changelog updated.
- **Reviewer risk:** L01 reference framing.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Used as oracle in quantile backbone comparisons (E-Q1).

#### P3-T04 — B1 shared threshold
- **Phase / Status:** 3 / Not Started
- **Purpose:** B1 = arithmetic mean of local p95 (shared τ); plus B1-pool, B1-wt variants.
- **Scientific reason:** Shared-scope anchor; construction-sensitivity rule-out (E-S1).
- **Engineering reason:** Single shared-τ family via quantile backbone.
- **Inputs:** P3-T02; scores.
- **Outputs:** `thresholding/shared.py`.
- **Files/modules:** `src/datp_core/thresholding/shared.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** B1 = mean(local p95); B1-pool = pooled p95; B1-wt =
  sample-weighted; all emit shared τ for all clients.
- **Unit tests:** `test_threshold_policies.py::test_b1_mean_of_local_p95`,
  `::test_b1_pool_and_weighted_variants`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_threshold_policies.py::test_b1_uses_benign_only`.
- **Acceptance:** B1 + pooled/weighted correct.
- **Definition of done:** B1 + tests green; changelog updated.
- **Reviewer risk:** L05 metric fragility (E-S1 supports).
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** B1 is the confirmatory shared comparator.

#### P3-T05 — B2 per-client threshold
- **Phase / Status:** 3 / Not Started
- **Purpose:** B2 = per-client p95 (local-scope anchor; confirmatory comparator).
- **Scientific reason:** The confirmatory local comparator.
- **Engineering reason:** Per-client τ with eligibility fallback.
- **Inputs:** P3-T02; scores.
- **Outputs:** `thresholding/local.py`.
- **Files/modules:** `src/datp_core/thresholding/local.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** τ_k = local p95; τ_global fallback for ineligible clients.
- **Unit tests:** `test_threshold_policies.py::test_b2_per_client_p95`,
  `::test_b2_fallback_for_ineligible`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_threshold_policies.py::test_b2_no_attack_in_calibration`.
- **Acceptance:** Per-client p95 + fallback correct.
- **Definition of done:** B2 + tests green; changelog updated.
- **Reviewer risk:** L04 tautology (measured on test, not cal).
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Paired with B1 for the Tier-1 endpoint.

#### P3-T06 — B3 family-mean threshold
- **Phase / Status:** 3 / Not Started
- **Purpose:** B3 = family-mean τ (Regime A only; requires device taxonomy).
- **Scientific reason:** Mechanism baseline; underperforms because taxonomy ≠
  calibration structure (motivates B4).
- **Engineering reason:** Guarded to Regime A with taxonomy present.
- **Inputs:** P3-T02; scores; device taxonomy.
- **Outputs:** `thresholding/family.py`.
- **Files/modules:** `src/datp_core/thresholding/family.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** Group clients by family; τ = family mean of local p95.
- **Unit tests:** `test_threshold_policies.py::test_b3_family_mean`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_threshold_policies.py::test_b3_rejected_without_taxonomy`.
- **Acceptance:** Family-mean correct; rejected absent taxonomy.
- **Definition of done:** B3 + tests green; changelog updated.
- **Reviewer risk:** L07 arbitrary family labels.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** B3 must never be reused as a shrinkage label (SB naming lock).

#### P3-T07 — B4 cluster threshold (fingerprint + k-means)
- **Phase / Status:** 3 / Not Started
- **Purpose:** B4 = k-means cluster-mean τ on the 4-scalar fingerprint
  [µ_e, σ_e, skew_e, p95(e)]; K=3 canonical.
- **Scientific reason:** Cluster-scope mechanism; taxonomy-free middle ground.
- **Engineering reason:** Locked fingerprint + K; deterministic clustering.
- **Inputs:** P3-T02; scores.
- **Outputs:** `thresholding/cluster.py`.
- **Files/modules:** `src/datp_core/thresholding/cluster.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** Compute 4-scalar fingerprint per client; k-means K=3;
  τ = cluster mean of local p95; K parameterizable (9/other = exploratory).
- **Unit tests:** `test_threshold_policies.py::test_b4_fingerprint_four_scalars`,
  `::test_b4_canonical_k3`, `::test_b4_cluster_mean_tau`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_threshold_policies.py::test_b4_k_mismatch_rejected`,
  `::test_b4_post_hoc_k_lock_rejected`.
- **Acceptance:** Fingerprint + K=3 clustering correct; K mismatch rejected.
- **Definition of done:** B4 + tests green; changelog updated.
- **Reviewer risk:** L06/L08 clustering/HARKing.
- **Runtime/reuse impact:** Cheap; stability analyzed in P5-T03.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Fingerprint is not a privacy mechanism (Tier 9 forbidden).

#### P3-T08 — Prediction generation & operating points
- **Phase / Status:** 3 / Not Started
- **Purpose:** Threshold → per-client predictions → FPR/TPR operating points.
- **Scientific reason:** FPR is measured on held-out test, not calibration.
- **Engineering reason:** Deterministic thresholded predictions.
- **Inputs:** any policy τ; test scores.
- **Outputs:** `evaluation/predictions.py`, `evaluation/operating_points.py`.
- **Files/modules:** `src/datp_core/evaluation/{predictions,operating_points}.py`.
- **Dependencies:** P3-T02.
- **Implementation tasks:** score>τ → alert; per-client FPR (benign test), TPR (attack test).
- **Unit tests:** `test_operating_points.py::test_fpr_on_benign_test`,
  `::test_tpr_on_attack_test`, `::test_threshold_boundary_semantics`.
- **Integration tests:** none.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_operating_points.py::test_fpr_not_computed_on_calibration`.
- **Acceptance:** FPR/TPR correct; measured on test only.
- **Definition of done:** Predictions + tests green; changelog updated.
- **Reviewer risk:** L03/L04.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Shared by all policies and variants.

#### P3-T09 — Classification metrics (Macro-F1, BA, AUROC control)
- **Phase / Status:** 3 / Not Started
- **Purpose:** Macro-F1, balanced accuracy, AUROC — all flagged as controls.
- **Scientific reason:** AUROC is a model-quality control, never the verdict.
- **Engineering reason:** Metric registry ties direction + control flag.
- **Inputs:** predictions/scores.
- **Outputs:** `evaluation/classification.py`.
- **Files/modules:** `src/datp_core/evaluation/classification.py`.
- **Dependencies:** P1-T02 metric registry, P3-T08.
- **Implementation tasks:** Macro-F1, BA, AUROC (threshold-free); P10 Macro-F1
  (10th-percentile-client); mark AUROC control in outputs.
- **Unit tests:** `test_metrics.py::test_macro_f1_known_values`,
  `::test_auroc_threshold_invariant`, `::test_auroc_monotonic_transform_invariant`,
  `::test_p10_macro_f1_definition`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_metrics.py::test_auroc_not_used_as_threshold_verdict`.
- **Acceptance:** Metric values correct; AUROC invariances hold; control flagged.
- **Definition of done:** Metrics + tests green; changelog updated.
- **Reviewer risk:** L17/L18 AUROC/Macro-F1 misreads.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** P10 Macro-F1 degradation is a reported negative (SB-06).

#### P3-T10 — Disparity metrics & per-client/per-seed aggregation
- **Phase / Status:** 3 / Not Started
- **Purpose:** CV(FPR), IQR(FPR), max−min FPR, worst-client FPR/BA, CV(TPR) +
  per-client and per-seed aggregation.
- **Scientific reason:** Per-client FPR disparity is the primary concern.
- **Engineering reason:** Correct CV(FPR) with documented edge cases.
- **Inputs:** operating points across eligible clients.
- **Outputs:** `evaluation/disparity.py`, `evaluation/aggregation.py`.
- **Files/modules:** `src/datp_core/evaluation/{disparity,aggregation}.py`.
- **Dependencies:** P3-T08, P3-T09.
- **Implementation tasks:** CV(FPR)=σ/µ over eligible clients; edge cases:
  µ_FPR=0 → defined as 0/undefined-and-reported; single eligible client →
  undefined; absolute-dispersion checks alongside; per-seed Δ aggregation.
- **Unit tests:** `test_disparity.py::test_cvfpr_known_value`,
  `::test_cvfpr_zero_mean_edge_case`, `::test_cvfpr_single_client_undefined`,
  `::test_iqr_maxmin_worstclient`, `::test_eligibility_filter_applied`.
- **Integration tests:** `test_aggregation.py::test_per_seed_delta_aggregation`.
- **Smoke/E2E:** threshold-suite smoke.
- **Negative tests:** `test_disparity.py::test_reject_including_ineligible_clients`.
- **Acceptance:** CV(FPR) + edge cases + absolute-dispersion correct.
- **Definition of done:** Disparity + tests green; changelog updated.
- **Reviewer risk:** L05 metric fragility; small-denominator artifacts.
- **Runtime/reuse impact:** Cheap; feeds statistics (P7).
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** CV(FPR) definition frozen; never silently changed (SB-15).

#### P3-T11 — Threshold-policy equivalence tests on synthetic fixtures
- **Phase / Status:** 3 / Not Started
- **Purpose:** End-to-end B0–B4 behavior on synthetic score fixtures with known
  ordering, plus the B1–B4 threshold-suite smoke.
- **Scientific reason:** Guards policy semantics against silent drift.
- **Engineering reason:** Fast validation of the whole cheap ladder.
- **Inputs:** `tiny_scores.json`; P3-T03…T10.
- **Outputs:** `tests/unit/test_threshold_policies.py` (equivalence),
  `tests/integration/test_threshold_suite_smoke.py`.
- **Files/modules:** those tests.
- **Dependencies:** P3-T03…P3-T10.
- **Implementation tasks:** Construct fixtures where B2<B4<B1 CV(FPR) ordering is
  analytically known; assert ordering + per-client τ correctness.
- **Unit tests:** `test_threshold_policies.py::test_known_ordering_b2_lt_b4_lt_b1`.
- **Integration tests:** `test_threshold_suite_smoke.py::test_b1_to_b4_from_stored_scores`.
- **Smoke/E2E:** `test_threshold_suite_smoke.py::test_no_training_triggered`.
- **Negative tests:** `test_threshold_suite_smoke.py::test_missing_scores_refused`.
- **Acceptance:** Known ordering reproduced; suite runs from stored scores only.
- **Definition of done:** Tests green; changelog updated. **Phase 3 exit gate.**
- **Reviewer risk:** L05/L06.
- **Runtime/reuse impact:** Proves ladder reuses scores (no retrain).
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Ordering values are fixture-analytic, not experimental claims.

---

### Phase 4 — Threshold Variants & Comparators

All cheap-stage, all reuse frozen checkpoints + stored scores. The defining
constraint: **no variant may trigger training.** **Entry gate:** P3 done.
**Exit gate:** all variants reuse scores; P4-T08 no-retrain guard green.

#### P4-T01 — q-sensitivity sweep
- **Phase / Status:** 4 / Not Started
- **Purpose:** CV(FPR) for B1/B2/B4 across q ∈ {.90,.95,.975,.99}.
- **Scientific reason:** Headline not a q=0.95 artifact; ordering preserved, inversions reported.
- **Engineering reason:** Reuses scores via quantile backbone.
- **Inputs:** P2-T08 scores; `configs/thresholding/quantiles.yaml`.
- **Outputs:** `analyses/q_sensitivity.py`; `outputs/threshold_variants/q/*`.
- **Files/modules:** `src/datp_core/analyses/q_sensitivity.py`.
- **Dependencies:** P3-T01, P3-T10.
- **Implementation tasks:** Sweep q; recompute B1/B2/B4 τ and CV(FPR); record ordering.
- **Unit tests:** `test_q_sensitivity.py::test_sweep_covers_qgrid`,
  `::test_ordering_recorded_per_q`.
- **Integration tests:** `test_q_sensitivity.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_q_sensitivity.py::test_reject_invalid_q_value`.
- **Acceptance:** q-grid swept from stored scores; inversions surfaced.
- **Definition of done:** Sweep + tests green; changelog updated.
- **Reviewer risk:** L05 metric fragility (Tier 2 support).
- **Runtime/reuse impact:** Cheap; pure reuse.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Extended to Regime D in P6-T06.

#### P4-T02 — Local-global shrinkage (τ-shrink)
- **Phase / Status:** 4 / Not Started
- **Purpose:** τ_k(λ) = λ·τ_k,p95 + (1−λ)·τ_global, λ ∈ {0,.25,.5,.75,1}.
- **Scientific reason:** Interpolates B2↔B1; defends B2 under small windows (RQ3).
- **Engineering reason:** Reuses scores; deterministic λ-curve.
- **Inputs:** scores; `configs/thresholding/shrinkage.yaml`.
- **Outputs:** `thresholding/shrinkage.py`; `outputs/threshold_variants/shrinkage/*`.
- **Files/modules:** `src/datp_core/thresholding/shrinkage.py`.
- **Dependencies:** P3-T04, P3-T05, P3-T10.
- **Implementation tasks:** λ-blend of local and global τ; CV(FPR) + P10 F1 per λ.
- **Unit tests:** `test_shrinkage.py::test_lambda0_equals_global`,
  `::test_lambda1_equals_local`, `::test_intermediate_blend`.
- **Integration tests:** `test_shrinkage.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_shrinkage.py::test_reject_lambda_out_of_range`.
- **Acceptance:** Endpoints match B1/B2; blend correct; non-monotone reported as-is.
- **Definition of done:** Shrinkage + tests green; changelog updated.
- **Reviewer risk:** L09/L10 shrinkage novelty/realism.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Never labeled `B3-LGS` (SB naming lock).

#### P4-T03 — Calibration-size-aware fallback & size ablation
- **Phase / Status:** 4 / Not Started
- **Purpose:** Size-dependent λ(n_k) replacing the hard n_min=100 fallback; ablate
  n_k ∈ {50,100,250,500,1000,5000}.
- **Scientific reason:** Graceful degradation vs naive collapse under small windows.
- **Engineering reason:** Reuses scores via subsampling; deterministic.
- **Inputs:** scores; `configs/thresholding/{calibration_size,calibration_size_shrinkage}.yaml`.
- **Outputs:** `thresholding/calibration_size.py`; `analyses/calibration_size_shrinkage.py`.
- **Files/modules:** those modules.
- **Dependencies:** P4-T02.
- **Implementation tasks:** Subsample benign cal to n_k; λ(n_k) schedule; threshold
  variance + worst-client FPR vs n; joint size×shrinkage surface.
- **Unit tests:** `test_calibration_size.py::test_lambda_schedule_monotone_in_n`,
  `::test_subsample_deterministic`.
- **Integration tests:** `test_calibration_size.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_calibration_size.py::test_reject_n_below_one`.
- **Acceptance:** Size ablation + λ(n_k) from stored scores; collapse/plateau reported.
- **Definition of done:** Fallback + tests green; changelog updated.
- **Reviewer risk:** L09 small-window realism.
- **Runtime/reuse impact:** Cheap; subsampling only.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Fallback reverts to B1-equivalent FPR as operating floor.

#### P4-T04 — Split/federated conformal B2-conf
- **Phase / Status:** 4 / Not Started
- **Purpose:** Split-conformal variant of B2 at marginal coverage 1−α, α=1−q.
- **Scientific reason:** Closes the tautology critique (finite-sample coverage).
- **Engineering reason:** Reuses cal/test scores; deterministic conformal quantile.
- **Inputs:** scores; `configs/thresholding/conformal_b2.yaml`.
- **Outputs:** `thresholding/conformal.py`; `analyses` coverage output.
- **Files/modules:** `src/datp_core/thresholding/conformal.py`.
- **Dependencies:** P3-T05, P3-T08.
- **Implementation tasks:** Split-conformal per-client τ at level 1−α; measure
  marginal coverage vs target; report coverage miss as adaptation limit.
- **Unit tests:** `test_conformal_coverage.py::test_marginal_coverage_near_target`,
  `::test_conformal_quantile_formula`.
- **Integration tests:** `test_conformal_coverage.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_conformal_coverage.py::test_reject_alpha_out_of_range`.
- **Acceptance:** Coverage ≈ target on fixtures; misses reported honestly.
- **Definition of done:** B2-conf + tests green; changelog updated.
- **Reviewer risk:** L03/L04 tautology closure.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Primary conformal anchor Lu et al. (SB-31); named-only here.

#### P4-T05 — B-FedStatsBenign statistics contract
- **Phase / Status:** 4 / Not Started
- **Purpose:** Locked benign-only federated summary-stat comparator: client
  (n_k, µ_k, σ_k²) → weighted global mean + **full pooled variance incl.
  between-client mean-shift term** + between_ratio.
- **Scientific reason:** Matched benign-only comparator vs Laridi novelty collapse.
- **Engineering reason:** Locked before any computation (SB-22/26); no raw scores/labels exchanged.
- **Inputs:** benign cal scores; `configs/thresholding/b_fedstats_benign.yaml`.
- **Outputs:** `thresholding/b_fedstats_benign.py` (stats half).
- **Files/modules:** `src/datp_core/thresholding/b_fedstats_benign.py`.
- **Dependencies:** P3-T01.
- **Implementation tasks:** σ²_global = Σ n_k[σ_k²+(µ_k−µ_global)²]/Σ n_k; report
  within_term, between_term, between_ratio; flag between_ratio>0.5.
- **Unit tests:** `test_b_fedstats_benign.py::test_pooled_variance_full_formula`,
  `::test_between_ratio_computed`, `::test_only_benign_summaries_used`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_b_fedstats_benign.py::test_reject_simple_pooled_variance`,
  `::test_reject_attack_labels_in_message`.
- **Acceptance:** Full pooled variance + between_ratio correct; benign-only.
- **Definition of done:** Stats + tests green; changelog updated.
- **Reviewer risk:** L02 Laridi novelty; SB-26.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Uses `b_fedstats_benign_scores.json` fixture.

#### P4-T06 — B-FedStatsBenign matched-exceedance & fixed-k supplementary
- **Phase / Status:** 4 / Not Started
- **Purpose:** Matched-exceedance operating point on τ(k)=µ_global+k·σ_global,
  k*∈{0.00..5.00}, k*=argmin|Σc_k/Σn_k−(1−q)| (ties→larger k); fixed-k supplementary.
- **Scientific reason:** Main comparison is matched-exceedance (SB-27), not fixed-k.
- **Engineering reason:** Only benign exceedance counts exchanged.
- **Inputs:** P4-T05 stats; benign exceedance counts.
- **Outputs:** `thresholding/b_fedstats_benign.py` (operating-point half).
- **Files/modules:** same module.
- **Dependencies:** P4-T05.
- **Implementation tasks:** Grid search k*; matched-exceedance selection; fixed-k
  k∈{2.0,2.5,3.0} as sensitivity only.
- **Unit tests:** `test_b_fedstats_benign.py::test_matched_exceedance_selection`,
  `::test_tie_break_toward_larger_k`, `::test_fixed_k_marked_supplementary`.
- **Integration tests:** `test_b_fedstats_benign.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_b_fedstats_benign.py::test_reject_tuning_after_results`
  (protocol locked before computation).
- **Acceptance:** Matched-exceedance k* correct; fixed-k supplementary.
- **Definition of done:** Operating point + tests green; changelog updated.
- **Reviewer risk:** L02; SB-22/27.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Comparator reduces dispersion vs B1 but expected < B2; reported honestly.

#### P4-T07 — B-LaridiFaithful out-of-scope disclosure guard
- **Phase / Status:** 4 / Not Started
- **Purpose:** A guard that refuses to run any anomaly-labeled Laridi-faithful
  calibration under the benign-only contract; emits a named disclosure only.
- **Scientific reason:** `B-LaridiFaithful` violates benign-only; out of scope (E-R4, SB-29).
- **Engineering reason:** Fail-closed guard; no accidental attack-in-calibration path.
- **Inputs:** policy request; benign-only contract.
- **Outputs:** guard in `thresholding/b_fedstats_benign.py` / policy dispatch.
- **Files/modules:** thresholding dispatch + validation.
- **Dependencies:** P3-T02, P4-T05.
- **Implementation tasks:** If policy=`B-LaridiFaithful` and calibration includes
  anomaly labels → raise + record disclosure; never fit thresholds on attack data.
- **Unit tests:** `test_laridi_guard.py::test_faithful_variant_refused_under_benign_contract`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_laridi_guard.py::test_anomaly_labeled_calibration_rejected`,
  `::test_benign_only_adaptation_not_called_faithful`.
- **Acceptance:** Faithful variant refused; disclosure recorded; benign-only preserved.
- **Definition of done:** Guard + tests green; changelog updated.
- **Reviewer risk:** L02 Laridi; SB-29.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Disclosure is wording only; never an executed experiment.

#### P4-T08 — Threshold-only reuse enforcement (no-retrain guard)
- **Phase / Status:** 4 / Not Started
- **Purpose:** Enforce that threshold-only variants reuse frozen checkpoints +
  stored scores and never trigger training/preprocessing.
- **Scientific reason:** Preserves fixed-encoder identity across variants.
- **Engineering reason:** Catches accidental retraining/duplicated pipelines.
- **Inputs:** P2-T07 checkpoints; P2-T08 scores; run plan.
- **Outputs:** `experiments/readiness.py` guard + CI test.
- **Files/modules:** `src/datp_core/experiments/readiness.py`, tests.
- **Dependencies:** P2-T07, P3-T02.
- **Implementation tasks:** Variant run cells declared cheap-stage → readiness
  asserts checkpoints frozen + scores present + no training module invoked;
  instrument training entrypoints to raise if called from a cheap suite.
- **Unit tests:** `test_no_retrain_guard.py::test_variant_marked_cheap_stage`.
- **Integration tests:** `test_no_retrain_guard.py::test_variant_run_reuses_frozen_checkpoint`.
- **Smoke/E2E:** `test_threshold_only_rerun.py::test_no_model_retraining_occurs`
  (spies training entrypoint; asserts zero calls).
- **Negative tests:** `test_no_retrain_guard.py::test_variant_triggering_training_fails`,
  `::test_hidden_retraining_detected`, `::test_score_artifact_mismatch_to_checkpoint_fails`.
- **Acceptance:** Cheap suites provably reuse frozen artifacts; retrain attempts fail.
- **Definition of done:** Guard + tests green; changelog updated.
- **Reviewer risk:** L27/L28; duplicated-pipeline/hidden-retrain.
- **Runtime/reuse impact:** **Enforces the entire reuse discipline.**
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Reused as a gate by P6 comparator runs and P7 audits.

#### P4-T09 — Variant output contracts, tables & figures
- **Phase / Status:** 4 / Not Started
- **Purpose:** Output contracts + table/figure export for all P4 variants.
- **Scientific reason:** Every variant table/figure traces to a manifest.
- **Engineering reason:** No one-off plotting; reuses reporting layer.
- **Inputs:** variant outputs; `configs/analysis/reporting.yaml`.
- **Outputs:** `reporting/tables.py`, `reporting/figures.py` (variant paths);
  `outputs/threshold_variants/*` + `scripts/build_tables.py`, `build_figures.py`.
- **Files/modules:** `src/datp_core/reporting/*`, scripts.
- **Dependencies:** P4-T01…P4-T06, P1-T07.
- **Implementation tasks:** Deterministic table/figure builders from stored variant
  outputs; each artifact carries source manifest.
- **Unit tests:** `test_reporting_variants.py::test_table_traces_to_manifest`.
- **Integration tests:** `test_reporting_variants.py::test_tables_figures_from_outputs_only`.
- **Smoke/E2E:** `test_reporting_run.py::test_build_from_existing_outputs`.
- **Negative tests:** `test_reporting_variants.py::test_reject_plot_without_manifest`.
- **Acceptance:** Variant tables/figures reproducible from outputs; manifest-traced.
- **Definition of done:** Reporting + tests green; changelog updated. **Phase 4 exit gate.**
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Same reporting layer reused by P5/P6/P7.

---

### Phase 5 — Mechanism Analyses

All cheap-stage, all reuse stored scores + frozen fingerprints. Mechanism (Tier 5)
+ some exploratory (Tier 7). **Entry gate:** P3 done. **Exit gate:** all mechanism
artifacts reproduced from fixed score fixtures.

#### P5-T01 — Benign/attack per-client CDF overlays & Ennio deep dive
- **Phase / Status:** 5 / Not Started
- **Purpose:** Per-client benign+attack score CDF overlays; Ennio Doorbell deep dive.
- **Scientific reason:** FPR-concentration mechanism behind the P10 Macro-F1 tradeoff.
- **Engineering reason:** Reuses stored scores; deterministic figures.
- **Inputs:** P2-T08 scores.
- **Outputs:** `analyses/cdf_mechanism.py`; `outputs/metrics` + figure.
- **Files/modules:** `src/datp_core/analyses/cdf_mechanism.py`.
- **Dependencies:** P3-T08.
- **Implementation tasks:** Per-client empirical CDFs; overlay B1/B2/B4 τ; Ennio case.
- **Unit tests:** `test_cdf_mechanism.py::test_cdf_monotone`,
  `::test_threshold_marker_placement`.
- **Integration tests:** `test_cdf_mechanism.py::test_reuses_scores_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_cdf_mechanism.py::test_no_device_filtering`.
- **Acceptance:** CDFs correct; all clients included; Ennio case produced.
- **Definition of done:** CDF analysis + tests green; changelog updated.
- **Reviewer risk:** L18 hidden tradeoff.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** No device filtering (integrity).

#### P5-T02 — Threshold-shift vs ΔFPR/ΔTPR surface
- **Phase / Status:** 5 / Not Started
- **Purpose:** Per-client Δτ vs ΔFPR/ΔTPR under B1→B2, all 9 devices.
- **Scientific reason:** Quantifies the fairness–sensitivity tradeoff surface.
- **Engineering reason:** Reuses thresholds + scores.
- **Inputs:** B1/B2 τ; scores.
- **Outputs:** `analyses/fairness_tradeoff.py`; figure.
- **Files/modules:** `src/datp_core/analyses/fairness_tradeoff.py`.
- **Dependencies:** P3-T04, P3-T05, P3-T08.
- **Implementation tasks:** Compute Δτ, ΔFPR, ΔTPR per device; scatter; no filtering.
- **Unit tests:** `test_fairness_tradeoff.py::test_delta_definitions`,
  `::test_all_nine_devices_present`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_fairness_tradeoff.py::test_reject_device_filtering`.
- **Acceptance:** All devices; deltas correct.
- **Definition of done:** Analysis + tests green; changelog updated.
- **Reviewer risk:** L18/L19.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** "Fairness" = operational FPR equity only.

#### P5-T03 — Cluster/family granularity, stability & adjusted Rand + feature ablation
- **Phase / Status:** 5 / Not Started
- **Purpose:** B1/B3/B4/B2 granularity comparison; within/across-cluster dispersion;
  cluster stability (adjusted Rand across seeds); 4-scalar feature ablation.
- **Scientific reason:** Cluster scope as middle ground; stability decides exploratory status.
- **Engineering reason:** Reuses frozen fingerprints + scores.
- **Inputs:** B4 fingerprints (P3-T07); scores.
- **Outputs:** `analyses/cluster_stability.py`; tables/figures.
- **Files/modules:** `src/datp_core/analyses/cluster_stability.py`.
- **Dependencies:** P3-T06, P3-T07, P3-T10.
- **Implementation tasks:** within/across dispersion; adjusted Rand across seeds;
  ablate fingerprint subsets; cluster→device contingency table (not Sankey, SB-19).
- **Unit tests:** `test_cluster_stability.py::test_adjusted_rand_known_value`,
  `::test_within_across_dispersion`, `::test_feature_ablation_subsets`.
- **Integration tests:** `test_cluster_stability.py::test_reuses_fingerprints_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_cluster_stability.py::test_instability_reported_not_hidden`.
- **Acceptance:** ARI + dispersion + ablation correct; instability surfaced.
- **Definition of done:** Analysis + tests green; changelog updated.
- **Reviewer risk:** L06/L08 clustering/HARKing.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** B4 stays exploratory at N=9 if unstable.

#### P5-T04 — JS-divergence vs DATP-benefit regression
- **Phase / Status:** 5 / Not Started
- **Purpose:** Regress DATP benefit on JS-divergence of per-client benign distributions.
- **Scientific reason:** Heterogeneity severity predicts benefit (association, not causation).
- **Engineering reason:** Reuses benign distributions.
- **Inputs:** benign score distributions; per-seed Δ.
- **Outputs:** `analyses/js_benefit.py`; scatter+fit.
- **Files/modules:** `src/datp_core/analyses/js_benefit.py`.
- **Dependencies:** P3-T10.
- **Implementation tasks:** Pairwise JS; regress benefit; report R², ρ with caveats.
- **Unit tests:** `test_js_benefit.py::test_js_symmetry_bounds`,
  `::test_regression_outputs_r2_rho`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_js_benefit.py::test_weak_r2_not_suppressed`.
- **Acceptance:** JS + regression correct; weak R² reported as real.
- **Definition of done:** Analysis + tests green; changelog updated.
- **Reviewer risk:** L05; association-not-causation framing.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Extended with Regime C/D points later.

#### P5-T05 — P10 Macro-F1 & FPR-concentration mechanism
- **Phase / Status:** 5 / Not Started
- **Purpose:** Link P10 Macro-F1 degradation to FPR concentration under B2.
- **Scientific reason:** Honest negative: B2 degrades detection in low-separability clients.
- **Engineering reason:** Reuses classification + disparity metrics.
- **Inputs:** predictions; P3-T09/T10.
- **Outputs:** `analyses` mechanism output + table.
- **Files/modules:** `src/datp_core/analyses/cdf_mechanism.py` (extension) or new module.
- **Dependencies:** P3-T09, P3-T10, P5-T01.
- **Implementation tasks:** P10 Macro-F1 per policy; correlate with FPR concentration.
- **Unit tests:** `test_p10_mechanism.py::test_p10_definition`,
  `::test_concentration_metric`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_p10_mechanism.py::test_negative_result_reported`.
- **Acceptance:** P10 tradeoff quantified and reportable as negative.
- **Definition of done:** Analysis + tests green; changelog updated.
- **Reviewer risk:** L18; SB-06.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Never framed as improved global Macro-F1.

#### P5-T06 — Alert-burden analysis (gated on real/cited rate)
- **Phase / Status:** 5 / Not Started
- **Purpose:** Alerts/device/day under B1 vs B2, only with a real or cited traffic rate.
- **Scientific reason:** Operational burden; no hypothetical numbers (SB-20).
- **Engineering reason:** Gated: metric omitted if no real/cited rate.
- **Inputs:** FPR per client; declared/cited rate config.
- **Outputs:** `analyses` alert-burden output.
- **Files/modules:** `src/datp_core/analyses/` (alert burden).
- **Dependencies:** P3-T10.
- **Implementation tasks:** alerts = FPR × benign rate; require rate source; omit if absent.
- **Unit tests:** `test_alert_burden.py::test_alerts_from_rate`,
  `::test_omitted_without_rate_source`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_alert_burden.py::test_reject_hypothetical_rate`.
- **Acceptance:** Metric computed only with real/cited rate; else omitted.
- **Definition of done:** Analysis + tests green; changelog updated.
- **Reviewer risk:** L20/L21; SB-20.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Hypothetical alert numbers forbidden.

#### P5-T07 — Mechanism figure/table export
- **Phase / Status:** 5 / Not Started
- **Purpose:** Export all mechanism tables/figures via the reporting layer, manifest-traced.
- **Scientific reason:** Every mechanism artifact traces to source scores.
- **Engineering reason:** Reuses P4-T09 reporting; no one-off plots.
- **Inputs:** mechanism outputs.
- **Outputs:** `outputs/figures`, `outputs/tables` (mechanism) via reporting.
- **Files/modules:** `src/datp_core/reporting/*`.
- **Dependencies:** P5-T01…P5-T06, P4-T09.
- **Implementation tasks:** Register mechanism artifacts; deterministic export.
- **Unit tests:** `test_reporting_mechanism.py::test_artifact_traces_to_manifest`.
- **Integration tests:** `test_reporting_mechanism.py::test_export_from_outputs_only`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_reporting_mechanism.py::test_reject_untraced_figure`.
- **Acceptance:** Mechanism artifacts reproducible + manifest-traced.
- **Definition of done:** Export + tests green; changelog updated.
- **Reviewer risk:** L28.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** SB-19 contingency table/heatmap, not Sankey.

#### P5-T08 — Mechanism tests from fixed score fixtures
- **Phase / Status:** 5 / Not Started
- **Purpose:** Validate all mechanism analyses against `tiny_scores.json` with known outputs.
- **Scientific reason:** Guards mechanism math against drift.
- **Engineering reason:** Fast, deterministic mechanism regression suite.
- **Inputs:** fixtures; P5-T01…P5-T07.
- **Outputs:** `tests/unit/test_mechanisms_*` consolidated.
- **Files/modules:** mechanism tests.
- **Dependencies:** P5-T01…P5-T07.
- **Implementation tasks:** Known-value assertions for CDF, ARI, JS, P10, tradeoff.
- **Unit tests:** `test_mechanisms_fixture.py::test_all_mechanisms_known_values`.
- **Integration tests:** `test_mechanisms_fixture.py::test_all_from_fixtures_no_retrain`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_mechanisms_fixture.py::test_missing_scores_refused`.
- **Acceptance:** All mechanism outputs match fixture-known values.
- **Definition of done:** Tests green; changelog updated. **Phase 5 exit gate.**
- **Reviewer risk:** L05/L06/L18.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Fixture-known values are analytic, not experimental claims.

---

### Phase 6 — External Dataset & Stress Tests

Mixed heavy/cheap. New datasets (Edge-IIoTset D, CICIoT2023 B-a/B-b, Dirichlet C)
and training-side stress tests (FedProx, model personalization) — all **outside
the causal ladder**. **Entry gate:** P2–P4 done. **Exit gate:** D/C heavy
artifacts frozen with manifests; stress tests never presented in the ladder.

#### P6-T01 — Edge-IIoTset loader & schema
- **Phase / Status:** 6 / Not Started
- **Purpose:** Typed Edge-IIoTset loader + schema + label validation.
- **Scientific reason:** Regime D external-validation substrate.
- **Engineering reason:** Fail-fast on missing/malformed raw data.
- **Inputs:** `data/raw/edge_iiotset/*`; dataset contract.
- **Outputs:** `data/edge_iiotset.py`; dataset manifest entry.
- **Files/modules:** `src/datp_core/data/edge_iiotset.py`.
- **Dependencies:** P1-T07, P1-T09.
- **Implementation tasks:** Load benign/attack; validate schema + labels; manifest hashes.
- **Unit tests:** `test_edge_loader.py::test_schema_matches_contract`,
  `::test_benign_attack_labels_present`.
- **Integration tests:** `test_edge_loader.py::test_manifest_written`.
- **Smoke/E2E:** Regime D tiny fixture (P6-T05).
- **Negative tests:** `test_edge_loader.py::test_missing_raw_dataset_raises`,
  `::test_wrong_dataset_root_raises`.
- **Acceptance:** Loads + validates; bad inputs rejected.
- **Definition of done:** Loader + tests green; changelog updated.
- **Reviewer risk:** L15 client mapping.
- **Runtime/reuse impact:** Raw hash keys D preprocessing cache.
- **Stage class:** Heavy-adjacent (I/O).
- **Changelog update:** required.
- **Notes:** input_dim differs from N-BaIoT (SB-13).

#### P6-T02 — Edge-IIoTset client-mapping feasibility audit
- **Phase / Status:** 6 / Not Started
- **Purpose:** First-principles device-vs-group client assignment + eligibility audit.
- **Scientific reason:** Partition decided by feasibility, not external precedent (SB-28).
- **Engineering reason:** Blocks training until partition is decided + documented.
- **Inputs:** P6-T01 data.
- **Outputs:** `partitioning/group_client.py`; feasibility report + partition manifest.
- **Files/modules:** `src/datp_core/partitioning/group_client.py`.
- **Dependencies:** P6-T01.
- **Implementation tasks:** Assess device vs group clients; coverage (n_k≥100 for
  ≥90% clients); pick K∈[6,15]; document decision before training.
- **Unit tests:** `test_edge_feasibility.py::test_partition_decision_recorded`,
  `::test_coverage_computed`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_edge_feasibility.py::test_reject_partition_without_audit`,
  `::test_reject_precedent_appeal`.
- **Acceptance:** Partition + coverage documented from first principles.
- **Definition of done:** Audit + tests green; changelog updated.
- **Reviewer risk:** L15; SB-28.
- **Runtime/reuse impact:** Gates D training.
- **Stage class:** Cheap (audit).
- **Changelog update:** required.
- **Notes:** Feeds P6-T04 coverage gate.

#### P6-T03 — Edge-IIoTset preprocessing & cache
- **Phase / Status:** 6 / Not Started
- **Purpose:** Reusable benign-fit preprocessing for Regime D with cache.
- **Scientific reason:** Benign-only, leakage-free; matches N-BaIoT contract.
- **Engineering reason:** Heavy; cached and reused.
- **Inputs:** P6-T01; P6-T02 partition; P1-T08 cache.
- **Outputs:** `data/preprocessed/edge_iiotset/*` + manifest.
- **Files/modules:** `src/datp_core/data/preprocessing.py` (D path).
- **Dependencies:** P6-T02, P1-T08.
- **Implementation tasks:** Benign-train-fit scaler; transform cal/test; cache-key.
- **Unit tests:** `test_edge_preprocessing.py::test_benign_fit_only`.
- **Integration tests:** `test_edge_preprocessing.py::test_cached_and_reused`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_edge_preprocessing.py::test_attack_not_used_in_fit`.
- **Acceptance:** Benign-only fit; cache correct.
- **Definition of done:** Preprocessing + tests green; changelog updated.
- **Reviewer risk:** L03.
- **Runtime/reuse impact:** **Heavy; reusable D artifact.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Reuses the same preprocessing module as P2-T02.

#### P6-T04 — Regime D split manifests & eligibility-coverage gate
- **Phase / Status:** 6 / Not Started
- **Purpose:** Benign train/cal/test splits + coverage gate (proceed iff n_k≥100
  for ≥90% clients, else reduce K/defer).
- **Scientific reason:** External-validation feasibility rule (roadmap §7/§12.9).
- **Engineering reason:** Blocks D training on failed coverage.
- **Inputs:** P6-T03; P6-T02 coverage.
- **Outputs:** D split manifests; coverage gate result.
- **Files/modules:** `src/datp_core/data/splits.py` (D path).
- **Dependencies:** P6-T03.
- **Implementation tasks:** Reuse split semantics; compute coverage; gate proceed/defer.
- **Unit tests:** `test_edge_splits.py::test_coverage_gate_threshold`,
  `::test_benign_only_calibration`.
- **Integration tests:** `test_edge_splits.py::test_split_manifest_roundtrip`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_edge_splits.py::test_defer_when_coverage_below_90`.
- **Acceptance:** Coverage gate enforced; splits benign-only.
- **Definition of done:** Splits + tests green; changelog updated.
- **Reviewer risk:** L15/L16.
- **Runtime/reuse impact:** Gates D heavy training.
- **Stage class:** Cheap (gate).
- **Changelog update:** required.
- **Notes:** Failure → reduce K or defer temporal MVE (P7-T02).

#### P6-T05 — Regime D FedAvg training & scoring
- **Phase / Status:** 6 / Not Started
- **Purpose:** Train FedAvg AE on Edge-IIoTset per seed; freeze; generate scores.
- **Scientific reason:** External-validation fixed encoder (separate from confirmatory).
- **Engineering reason:** Reuses training/scoring modules with D input_dim.
- **Inputs:** P6-T04 splits; P2-T05/T06/T07/T08 modules.
- **Outputs:** `checkpoints/fedavg/edge_iiotset/*`; `outputs/regime_d/scores/*` + manifests.
- **Files/modules:** federation + models (D path).
- **Dependencies:** P6-T04, P2-T06, P2-T07, P2-T08.
- **Implementation tasks:** Train with D input_dim; freeze; score; manifests bind D identity.
- **Unit tests:** `test_regime_d_train.py::test_input_dim_matches_dataset`.
- **Integration tests:** `test_regime_d_smoke.py::test_tiny_edge_fixture_end_to_end`.
- **Smoke/E2E:** `test_regime_d_smoke.py::test_D_ladder_from_frozen_checkpoint`.
- **Negative tests:** `test_regime_d_train.py::test_reject_nbaiot_checkpoint_for_D_scores`.
- **Acceptance:** D checkpoints frozen + scores stored with D manifests.
- **Definition of done:** Train/score + tests green; changelog updated.
- **Reviewer risk:** L15/L16.
- **Runtime/reuse impact:** **Heavy; separate D encoder (SB-13).**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** External validation, never merged into the Tier-1 endpoint.

#### P6-T06 — Regime D threshold-ladder & comparator evaluation
- **Phase / Status:** 6 / Not Started
- **Purpose:** B1–B4 + q-sensitivity + `B-FedStatsBenign` on stored D scores; BCa CI.
- **Scientific reason:** Tier-3 external-validation claim; direction vs Regime A.
- **Engineering reason:** Reuses P3/P4 policies + D scores; no retrain.
- **Inputs:** P6-T05 scores; P3/P4 policies.
- **Outputs:** `outputs/regime_d/*` metrics + tables/figures.
- **Files/modules:** thresholding + evaluation + reporting (D path).
- **Dependencies:** P6-T05, P3-T04..T10, P4-T01, P4-T06, P4-T08.
- **Implementation tasks:** Run ladder + comparator on D scores; CV(FPR)+BCa CI;
  report divergence as boundary if present.
- **Unit tests:** `test_regime_d_eval.py::test_ladder_runs_on_D_scores`.
- **Integration tests:** `test_regime_d_eval.py::test_no_retrain_on_D_ladder`.
- **Smoke/E2E:** `test_regime_d_smoke.py::test_reporting_from_D_outputs`.
- **Negative tests:** `test_regime_d_eval.py::test_D_result_not_labeled_confirmatory`.
- **Acceptance:** D ladder from stored scores; direction reported; not confirmatory.
- **Definition of done:** Eval + tests green; changelog updated.
- **Reviewer risk:** L16; external separated from Tier 1.
- **Runtime/reuse impact:** Cheap; reuses D scores.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Mixed/null → boundary wording (§12.9).

#### P6-T07 — CICIoT2023 file-level loader & Regime B-a boundary
- **Phase / Status:** 6 / Not Started
- **Purpose:** File-level (63 pseudo-clients, d=39) loader for the B-a boundary regime.
- **Scientific reason:** Near-homogeneous applicability boundary (null reported only).
- **Engineering reason:** Feature-count re-verification gate before any print claim.
- **Inputs:** `data/raw/ciciot2023/*`.
- **Outputs:** `data/ciciot2023.py`; B-a partition; manifest.
- **Files/modules:** `src/datp_core/data/ciciot2023.py`, `partitioning/file_level.py`.
- **Dependencies:** P1-T07, P1-T09.
- **Implementation tasks:** Load file-level pseudo-clients; verify feature count of
  the actual processed artifact (d=39 expected, mirror distributions differ).
- **Unit tests:** `test_ciciot_loader.py::test_file_level_63_pseudo_clients`,
  `::test_feature_count_verified`.
- **Integration tests:** `test_ciciot_loader.py::test_manifest_written`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_ciciot_loader.py::test_reject_unverified_feature_count`,
  `::test_boundary_not_generalized`.
- **Acceptance:** File-level loads; feature count verified; boundary-only.
- **Definition of done:** Loader + tests green; changelog updated.
- **Reviewer risk:** L14; SB-16.
- **Runtime/reuse impact:** Heavy-adjacent (I/O).
- **Stage class:** Cheap/Heavy-adjacent.
- **Changelog update:** required.
- **Notes:** Null stays Regime B-a; never generalized to CICIoT2023.

#### P6-T08 — CICIoT2023 B-b rejection guard (B_B_REJECTED_NO_METADATA)
- **Phase / Status:** 6 / Not Started
- **Purpose:** Fail-closed guard rejecting any device/MAC repartition when metadata absent.
- **Scientific reason:** B-b infeasible on available CSV (no MAC/device/IP/timestamp) — E-R1.
- **Engineering reason:** Prevents accidental B-b claims/labels.
- **Inputs:** CICIoT2023 schema.
- **Outputs:** guard + `B_B_REJECTED_NO_METADATA` status emission.
- **Files/modules:** `src/datp_core/data/ciciot2023.py` (guard).
- **Dependencies:** P6-T07.
- **Implementation tasks:** If device/MAC/IP/timestamp columns absent → refuse B-b,
  emit rejection status; no pseudo-client substitute; no PCAP branch.
- **Unit tests:** `test_ciciot_bb_guard.py::test_bb_rejected_without_metadata`.
- **Integration tests:** none.
- **Smoke/E2E:** none.
- **Negative tests:** `test_ciciot_bb_guard.py::test_no_quantitative_bb_claim_possible`,
  `::test_mac_and_group_partitions_not_collapsed`.
- **Acceptance:** B-b refused with status; no B-b metric path exists.
- **Definition of done:** Guard + tests green; changelog updated.
- **Reviewer risk:** L14; SB-23.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (guard).
- **Changelog update:** required.
- **Notes:** Also `TEMPORAL_REJECTED_NO_TIMESTAMPS` for CICIoT2023 temporal (E-R2).

#### P6-T09 — Regime C Dirichlet partition builder & alpha-sweep
- **Phase / Status:** 6 / Not Started
- **Purpose:** Synthetic 20-client Dirichlet partitions over N-BaIoT; α ∈
  {0.1,0.3,0.5,1.0,10.0,IID}; train/score per α.
- **Scientific reason:** Heterogeneity-severity sweep (Tier 2 supportive).
- **Engineering reason:** Each α is a distinct split → distinct heavy training.
- **Inputs:** N-BaIoT preprocessed; `configs/suites/regime_c_dirichlet.yaml`.
- **Outputs:** `partitioning/dirichlet.py`; `checkpoints/.../regime_c`;
  `outputs/regime_c/*`.
- **Files/modules:** `src/datp_core/partitioning/dirichlet.py` + training/scoring.
- **Dependencies:** P2-T02, P2-T06, P2-T08.
- **Implementation tasks:** Deterministic Dirichlet partition per α+seed; train;
  score; B1/B2/B4 + CV(FPR) vs α; low-α reported as band, not strict monotone.
- **Unit tests:** `test_dirichlet.py::test_partition_deterministic_given_seed`,
  `::test_alpha_grid_covered`, `::test_iid_limit_behavior`.
- **Integration tests:** `test_regime_c_smoke.py::test_dirichlet_b1_b2_b4_smoke`.
- **Smoke/E2E:** `test_regime_c_smoke.py::test_tiny_alpha_sweep`.
- **Negative tests:** `test_dirichlet.py::test_reject_invalid_alpha`.
- **Acceptance:** Deterministic partitions; α-sweep trained+scored; band reporting.
- **Definition of done:** Builder + sweep + tests green; changelog updated.
- **Reviewer risk:** L05; non-monotone band honesty.
- **Runtime/reuse impact:** **Heavy; one training per α (split changes).**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** 20 synthetic clients ≠ Regime A's 9 physical clients.

#### P6-T10 — FedProx implementation & stress-test evaluation
- **Phase / Status:** 6 / Not Started
- **Purpose:** FedProx aggregation (µ-grid frozen) × B1–B4; CV(FPR) delta vs FedAvg.
- **Scientific reason:** Stress test outside the ladder; gain not absorbed by aggregation.
- **Engineering reason:** Mirrors FedAvg loop + proximal term; E/rounds locked equal.
- **Inputs:** Regime A/D splits; `configs/training/fedprox_*.yaml`.
- **Outputs:** `federation/fedprox.py`; `checkpoints/fedprox/*`; `outputs/stress_tests/fedprox/*`.
- **Files/modules:** `src/datp_core/federation/fedprox.py`.
- **Dependencies:** P2-T06, P3-T04..T07, P4-T08.
- **Implementation tasks:** FedProx µ term; frozen µ-grid; train; score; B1–B4 delta;
  convergence failure reported non-retroactively (no post-hoc µ).
- **Unit tests:** `test_fedprox.py::test_proximal_term`,
  `::test_mu_grid_frozen`, `::test_e_rounds_equal_fedavg`.
- **Integration tests:** `test_fedprox_tiny.py::test_tiny_stress_fixture`.
- **Smoke/E2E:** `test_fedprox_tiny.py::test_delta_vs_fedavg_from_frozen`.
- **Negative tests:** `test_fedprox.py::test_reject_post_hoc_mu`,
  `::test_fedprox_not_in_causal_ladder`.
- **Acceptance:** FedProx trained on frozen µ-grid; delta reported; outside ladder.
- **Definition of done:** FedProx + tests green; changelog updated.
- **Reviewer risk:** L13; SB-25.
- **Runtime/reuse impact:** **Heavy; separate stress-test encoders.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Convergence failure = reportable outcome, no µ search post-hoc.

#### P6-T11 — Model-personalization comparator & absorption ratio
- **Phase / Status:** 6 / Not Started
- **Purpose:** One model-personalization comparator (Ditto if faithful, else
  `FedRep-AE`/`FedPer-AE`) × B1–B4; absorption ratio Δ_pers/Δ_FedAvg with pre-specified bands.
- **Scientific reason:** Highest residual risk (L12); model personalization outside ladder.
- **Engineering reason:** Fallback never called "Ditto" (SB-24); bands applied as-is.
- **Inputs:** Regime A/D splits; `configs/training/personalized_ae.yaml`; `absorption_bands.yaml`.
- **Outputs:** `federation/personalization.py`; `checkpoints/personalized/*`;
  `outputs/stress_tests/personalization/*`.
- **Files/modules:** `src/datp_core/federation/personalization.py`,
  `src/datp_core/analyses/personalization_absorption.py`.
- **Dependencies:** P2-T06, P3-T04, P3-T05, P4-T08.
- **Implementation tasks:** Train personalized AE; score; Δ_pers/Δ_FedAvg; apply
  4 absorption bands (§9.3) without adjustment; honest label for fallback.
- **Unit tests:** `test_personalization.py::test_absorption_ratio_formula`,
  `::test_bands_applied_as_specified`, `::test_fallback_not_named_ditto`.
- **Integration tests:** `test_personalization_tiny.py::test_tiny_stress_fixture`.
- **Smoke/E2E:** `test_personalization_tiny.py::test_absorption_from_frozen`.
- **Negative tests:** `test_personalization.py::test_personalization_not_in_causal_ladder`,
  `::test_bands_not_tuned_post_hoc`.
- **Acceptance:** Absorption ratio + bands correct; fallback honestly labeled; outside ladder.
- **Definition of done:** Comparator + tests green; changelog updated.
- **Reviewer risk:** L12/L13; SB-24/25.
- **Runtime/reuse impact:** **Heavy; separate personalized encoders.**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Full 2×2 with cost accounting is the spin-off (future work only).

#### P6-T12 — Stress-test reporting
- **Phase / Status:** 6 / Not Started
- **Purpose:** Stress-test tables/figures (FedProx, personalization, `B-FedStatsBenign`)
  clearly separated from the causal ladder.
- **Scientific reason:** Stress/comparator results never share ladder framing.
- **Engineering reason:** Reuses reporting layer; manifest-traced.
- **Inputs:** stress-test outputs.
- **Outputs:** `outputs/stress_tests/*` tables/figures; `results/tables/stress_tests.csv` (curated later).
- **Files/modules:** `src/datp_core/reporting/*`.
- **Dependencies:** P6-T06, P6-T10, P6-T11, P4-T06.
- **Implementation tasks:** Stress-test tables labeled outside-ladder; manifest-traced.
- **Unit tests:** `test_stress_reporting.py::test_tables_labeled_outside_ladder`.
- **Integration tests:** `test_stress_reporting.py::test_from_outputs_only`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_stress_reporting.py::test_reject_ladder_framing_for_stress`.
- **Acceptance:** Stress tables reproducible + separated from ladder.
- **Definition of done:** Reporting + tests green; changelog updated. **Phase 6 exit gate.**
- **Reviewer risk:** L12/L13; SB-25.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** Comparator table separate from confirmatory/main ladder tables.

---

### Phase 7 — Temporal Recalibration, Final Audit & Freeze

Temporal MVE + statistical finalization + claim gates + curation + full audits.
**Entry gate:** P6 done. **Exit gate:** full audit + readiness report signed.

#### P7-T01 — Chronological split support & temporal score-artifact contract
- **Phase / Status:** 7 / Not Started
- **Purpose:** Chronological 70/30 split by capture time (Edge-IIoTset) + temporal
  score-artifact contract distinct from static scores.
- **Scientific reason:** Temporal MVE substrate; Edge-IIoTset is the sole temporal dataset.
- **Engineering reason:** Separate temporal manifests to avoid mixing with static.
- **Inputs:** P6-T01 timestamps; P6-T03 preprocessing.
- **Outputs:** `data/splits.py` (temporal), temporal score manifest.
- **Files/modules:** `src/datp_core/data/splits.py` (temporal path).
- **Dependencies:** P6-T05.
- **Implementation tasks:** First 70% by time → train+cal; last 30% → eval; gapped;
  temporal manifest with time boundaries.
- **Unit tests:** `test_temporal_split.py::test_chronological_ordering`,
  `::test_70_30_boundary`, `::test_no_future_leakage_into_calibration`.
- **Integration tests:** `test_temporal_split.py::test_temporal_manifest_roundtrip`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_temporal_split.py::test_reject_missing_timestamps`,
  `::test_reject_invalid_temporal_split`.
- **Acceptance:** Chronological split correct; no future leakage; manifest stable.
- **Definition of done:** Split + tests green; changelog updated.
- **Reviewer risk:** L28; SB-08.
- **Runtime/reuse impact:** Temporal training is a distinct heavy run.
- **Stage class:** Cheap (split) / feeds heavy P7-T02.
- **Changelog update:** required.
- **Notes:** CICIoT2023 temporal rejected (TEMPORAL_REJECTED_NO_TIMESTAMPS).

#### P7-T02 — Frozen vs one-shot recalibration, temporal metrics & 3 pre-specified outcomes
- **Phase / Status:** 7 / Not Started
- **Purpose:** Compare frozen thresholds vs one-shot recalibration at the temporal
  boundary; per-window CV(FPR); recovery ratio; apply one of Outcomes A/B/C.
- **Scientific reason:** One-shot recalibration only; no retroactive drift detector.
- **Engineering reason:** Requires training on first-70% window (heavy) then reuse.
- **Inputs:** P7-T01 temporal splits; training/scoring modules.
- **Outputs:** `analyses/temporal_recalibration.py`; `outputs/temporal/*`.
- **Files/modules:** `src/datp_core/analyses/temporal_recalibration.py`.
- **Dependencies:** P7-T01, P2-T06, P2-T08, P3-T04, P3-T05, P3-T07.
- **Implementation tasks:** Train on first 70%; B1/B2/B4 frozen thresholds; one-shot
  recal at boundary; recovery ratio; select Outcome A (≥50%), B (<50%), C (no drift).
- **Unit tests:** `test_temporal_recal.py::test_recovery_ratio_formula`,
  `::test_outcome_selection_thresholds`.
- **Integration tests:** `test_temporal_recal.py::test_frozen_vs_oneshot_from_window`.
- **Smoke/E2E:** `test_temporal_recal.py::test_tiny_temporal_fixture`.
- **Negative tests:** `test_temporal_recal.py::test_reject_streaming_detector`,
  `::test_reject_retroactive_drift_rescue`.
- **Acceptance:** Recovery ratio + one pre-specified outcome; no streaming rescue.
- **Definition of done:** Temporal MVE + tests green; changelog updated.
- **Reviewer risk:** L16; SB-08/SB-11.
- **Runtime/reuse impact:** **Heavy (temporal-window training).**
- **Stage class:** **Heavy.**
- **Changelog update:** required.
- **Notes:** Defer to supplement if timestamps unsuitable.

#### P7-T03 — Statistical finalization: BCa CI audit, Wilcoxon & Cliff's δ
- **Phase / Status:** 7 / Not Started
- **Purpose:** BCa bootstrap CI (audited), Wilcoxon signed-rank, Cliff's δ; the
  Tier-1 CI on Δ_s computed here.
- **Scientific reason:** 95% BCa CI is the confirmatory statistic; Wilcoxon/Cliff's
  δ are descriptive secondary.
- **Engineering reason:** Deterministic, audited bootstrap; reuses per-seed Δ_s.
- **Inputs:** per-seed Δ_s (P2-T11 outputs); `configs/analysis/statistics.yaml`.
- **Outputs:** `statistics/{bootstrap,paired_tests,effect_sizes}.py`;
  `outputs/confirmatory/stats/*`.
- **Files/modules:** `src/datp_core/statistics/*`.
- **Dependencies:** P3-T10, P2-T11.
- **Implementation tasks:** BCa (bias-correction + acceleration) with known-answer
  audit vs reference; Wilcoxon; Cliff's δ; CI-discrepancy block rule (roadmap §10).
- **Unit tests:** `test_statistics.py::test_bca_ci_known_answer`,
  `::test_bca_matches_reference_on_fixture`, `::test_wilcoxon_known_value`,
  `::test_cliffs_delta_known_value`, `::test_ci_excludes_zero_detection`.
- **Integration tests:** `test_statistics.py::test_ci_from_per_seed_deltas`.
- **Smoke/E2E:** `test_anchor_mini_run.py::test_2seed_ci_pipeline`.
- **Negative tests:** `test_statistics.py::test_reject_percentile_when_bca_required`,
  `::test_seed_extension_discrepancy_blocks`.
- **Acceptance:** BCa CI correct vs known answer; secondary stats correct; block rule works.
- **Definition of done:** Statistics + tests green; changelog updated.
- **Reviewer risk:** L23/L21 statistical integrity.
- **Runtime/reuse impact:** Cheap; reuses per-seed Δ_s.
- **Stage class:** Testing/audit + cheap.
- **Changelog update:** required — record CI computed, not any pass/fail claim.
- **Notes:** This ticket computes the number; P7-T04 gates the claim.

#### P7-T04 — Claim-gate logic (confirmatory/supportive/stress)
- **Phase / Status:** 7 / Not Started
- **Purpose:** Encode pass logic: confirmatory survives iff BCa CI excludes zero
  positive; supportive/stress/external gates per tier.
- **Scientific reason:** No supportive result promoted; endpoint rule immutable.
- **Engineering reason:** Typed gate objects tied to `ClaimRole` + fallback wording refs.
- **Inputs:** P7-T03 stats; P0-T02 claim hierarchy.
- **Outputs:** `statistics/claim_gates.py`.
- **Files/modules:** `src/datp_core/statistics/claim_gates.py`.
- **Dependencies:** P7-T03, P1-T02.
- **Implementation tasks:** Gate per tier; confirmatory gate = CI positive-excludes-zero;
  map weak/mixed/null/opposite to fallback wording IDs (§12).
- **Unit tests:** `test_claim_gates.py::test_confirmatory_pass_positive_ci`,
  `::test_null_when_ci_includes_zero`, `::test_opposite_direction_flagged`,
  `::test_supportive_not_promoted_to_confirmatory`.
- **Integration tests:** `test_claim_gates.py::test_gate_reads_stats_outputs`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_claim_gates.py::test_reject_promoting_stress_into_ladder`.
- **Acceptance:** Gates match roadmap rules; no promotion possible.
- **Definition of done:** Gates + tests green; changelog updated.
- **Reviewer risk:** L23; endpoint isolation.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (logic).
- **Changelog update:** required.
- **Notes:** Gate outputs feed the claim map (P7-T05); no prose written here.

#### P7-T05 — Claim-to-evidence map
- **Phase / Status:** 7 / Not Started
- **Purpose:** Map each claim/tier → experiment IDs → artifacts/manifests.
- **Scientific reason:** Every claim traces to reproducible evidence.
- **Engineering reason:** Reuses manifests + gate outputs; no unverified claims.
- **Inputs:** P7-T04 gates; manifests.
- **Outputs:** `reporting/claim_map.py`; `results/supplementary/claim_evidence_map.md` (structure only).
- **Files/modules:** `src/datp_core/reporting/claim_map.py`.
- **Dependencies:** P7-T04.
- **Implementation tasks:** Build claim→evidence table from gate outputs + manifests;
  no claim without a linked artifact.
- **Unit tests:** `test_claim_map.py::test_every_claim_has_evidence_link`.
- **Integration tests:** `test_claim_map.py::test_map_built_from_manifests`.
- **Smoke/E2E:** none.
- **Negative tests:** `test_claim_map.py::test_reject_claim_without_evidence`.
- **Acceptance:** Every claim linked to artifacts; unlinked claims rejected.
- **Definition of done:** Claim map + tests green; changelog updated.
- **Reviewer risk:** L23/L28.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Structure only; no result values asserted in this plan.

#### P7-T06 — Result curation (outputs→results) & freeze_results
- **Phase / Status:** 7 / Not Started
- **Purpose:** Copy only curated lightweight derived artifacts into `results/`.
- **Scientific reason:** `results/` holds citable/shareable derivations only.
- **Engineering reason:** No heavy artifacts in results; reproducible curation.
- **Inputs:** `outputs/*`; gate outputs; `results/README.md`.
- **Outputs:** `reporting/manifests.py`; `scripts/freeze_results.py`;
  `results/{tables,figures,supplementary}/*`, `result_manifest.md`.
- **Files/modules:** `src/datp_core/reporting/manifests.py`, `scripts/freeze_results.py`.
- **Dependencies:** P7-T04, P4-T09, P5-T07, P6-T12.
- **Implementation tasks:** Select curated CSVs/PDFs; write result manifest with
  provenance links; refuse to copy heavy artifacts.
- **Unit tests:** `test_result_curation.py::test_result_manifest_has_provenance`.
- **Integration tests:** `test_result_curation.py::test_curation_reproducible`.
- **Smoke/E2E:** `test_result_curation.py::test_freeze_results_from_outputs_only`.
- **Negative tests:** `test_result_curation.py::test_reject_heavy_artifact_in_results`.
- **Acceptance:** Curated results reproducible; heavy artifacts excluded.
- **Definition of done:** Curation + tests green; changelog updated.
- **Reviewer risk:** L28 reproducibility.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Cheap (reuse).
- **Changelog update:** required.
- **Notes:** No release/tag/versioning (governance).

#### P7-T07 — Table/figure reproducibility checks
- **Phase / Status:** 7 / Not Started
- **Purpose:** Re-run table/figure builders and assert byte/value-stable reproduction.
- **Scientific reason:** Every table/figure must reproduce from stored outputs.
- **Engineering reason:** Guards against non-deterministic reporting.
- **Inputs:** `outputs/*`; reporting layer.
- **Outputs:** reproducibility test suite.
- **Files/modules:** `tests/integration/test_reporting_reproducibility.py`.
- **Dependencies:** P7-T06.
- **Implementation tasks:** Build twice; compare table values + figure metadata.
- **Unit tests:** n/a.
- **Integration tests:** `test_reporting_reproducibility.py::test_tables_stable_across_runs`,
  `::test_figures_deterministic`.
- **Smoke/E2E:** `test_reporting_run.py::test_reporting_only_from_outputs`.
- **Negative tests:** `test_reporting_reproducibility.py::test_detect_nondeterministic_table`.
- **Acceptance:** Tables/figures reproduce identically from outputs.
- **Definition of done:** Tests green; changelog updated.
- **Reviewer risk:** L28.
- **Runtime/reuse impact:** Cheap.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Reporting reads outputs only; never recomputes heavy stages.

#### P7-T08 — Full-suite dry run
- **Phase / Status:** 7 / Not Started
- **Purpose:** `full_journal.yaml` dry-run expanding every suite into run cells
  without executing heavy stages; validates the plan graph end to end.
- **Scientific reason:** Confirms all experiments are wired + ordered correctly.
- **Engineering reason:** Catches missing deps/duplicated pipelines before real runs.
- **Inputs:** all suites; runner/plan.
- **Outputs:** dry-run report; `test_full_suite_dry_run.py`.
- **Files/modules:** `src/datp_core/experiments/plan.py`, tests.
- **Dependencies:** P1-T09, P6-T12, P7-T02.
- **Implementation tasks:** Expand full journal suite; assert each cell has a stage
  class + reuse keys; detect duplicated/one-off logic.
- **Unit tests:** `test_full_suite_dry_run.py::test_every_experiment_id_present`.
- **Integration tests:** `test_full_suite_dry_run.py::test_no_duplicated_pipeline`,
  `::test_cheap_cells_declare_reuse`.
- **Smoke/E2E:** `test_full_suite_dry_run.py::test_dry_run_no_heavy_execution`.
- **Negative tests:** `test_full_suite_dry_run.py::test_detect_hidden_one_off_logic`.
- **Acceptance:** Full graph expands; no duplication; heavy stages not executed.
- **Definition of done:** Dry run + tests green; changelog updated.
- **Reviewer risk:** L27; duplicated-pipeline risk.
- **Runtime/reuse impact:** Validates the whole reuse graph.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Real heavy execution stays operator-gated.

#### P7-T09 — Final audit: no-leakage, no-overwrite & provenance
- **Phase / Status:** 7 / Not Started
- **Purpose:** Consolidated audit: attack-not-in-calibration, cal/test disjoint,
  no test-metric checkpoint selection, no silent overwrite, full lineage integrity,
  no hidden retraining.
- **Scientific reason:** Enforces every identity/leakage rule before freeze.
- **Engineering reason:** Single audit surface over all subsystems.
- **Inputs:** all manifests + guards.
- **Outputs:** `tests/integration/test_final_audit.py`; a failure-run fixture.
- **Files/modules:** audit tests.
- **Dependencies:** P2-T04, P2-T07, P2-T08, P4-T08, P1-T07.
- **Implementation tasks:** Assert leakage guards, overwrite refusal, provenance,
  reuse-key integrity across a full mini-pipeline; include a failure run where
  leakage/wrong lineage is deliberately injected and detected.
- **Unit tests:** n/a.
- **Integration tests:** `test_final_audit.py::test_no_attack_in_calibration_global`,
  `::test_no_test_metric_checkpoint_selection`, `::test_no_silent_overwrite`,
  `::test_full_lineage_integrity`.
- **Smoke/E2E:** `test_final_audit.py::test_failure_run_detects_leakage`,
  `::test_failure_run_detects_wrong_lineage`.
- **Negative tests:** `test_final_audit.py::test_hidden_retraining_detected`,
  `::test_stale_policy_name_in_config_detected`.
- **Acceptance:** All leakage/overwrite/provenance/retrain guards fire correctly.
- **Definition of done:** Audit + tests green; changelog updated.
- **Reviewer risk:** L03/L04/L08/L27/L28.
- **Runtime/reuse impact:** Cheap; validates the reuse contract globally.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** The reviewer-proof gate before readiness sign-off.

#### P7-T10 — Final implementation readiness report
- **Phase / Status:** 7 / Not Started
- **Purpose:** Produce the final readiness report against the global audit checklist
  (§17) and confirm CHANGELOG matches the master ticket log.
- **Scientific reason:** Confirms identity preserved and endpoint isolated end to end.
- **Engineering reason:** Single sign-off; changelog/master-log consistency verified.
- **Inputs:** all phase exit gates; audit results; CHANGELOG.
- **Outputs:** `docs/protocol/readiness_report.md` (structure only, no result claims).
- **Files/modules:** `docs/protocol/readiness_report.md`; consistency test.
- **Dependencies:** P7-T01…P7-T09.
- **Implementation tasks:** Run §17 checklist; assert changelog statuses == master
  log; list green tests, lint/type status, remaining risks.
- **Unit tests:** `test_readiness.py::test_checklist_items_all_addressed`.
- **Integration tests:** `test_readiness.py::test_changelog_matches_master_log`.
- **Smoke/E2E:** `make test && make lint && make typecheck` all green.
- **Negative tests:** `test_readiness.py::test_fail_when_open_blocker_exists`,
  `::test_fail_on_changelog_master_mismatch`.
- **Acceptance:** §17 checklist satisfied; changelog consistent; all checks green.
- **Definition of done:** Report + tests green; changelog updated. **Phase 7 exit gate.**
- **Reviewer risk:** All (final integrity).
- **Runtime/reuse impact:** none.
- **Stage class:** Testing/audit (cheap).
- **Changelog update:** required.
- **Notes:** Contains no experimental results; readiness/implementation status only.

---

## 10. Testing Strategy (Test Pyramid)

Authority: P0-T08. Every subsystem below names concrete tests (owning ticket in
parentheses). No generic "add tests".

### 10.1 Unit tests
- **Config validation** (P1-T04): valid load, reject invalid q, unknown/stale
  policy, missing benign-only flag, hardcoded abs path, unknown experiment ID.
- **Enums/domain** (P1-T02): policies match protocol doc, B0 non-ladder, B-b
  rejected, AUROC control, CV(FPR) primary, no stale names.
- **Path resolution** (P1-T05): raw symlink resolved, stable artifact paths, env
  override, reject hardcoded/wrong root, missing-root raises.
- **Manifest schema** (P1-T07): round-trip, reuse-key mismatch detected.
- **Dataset contract** (P2-T01, P6-T01, P6-T07): device/schema/label validation,
  feature-count verification (CICIoT2023).
- **Split semantics** (P2-T04): benign-only calibration, no cal/test overlap,
  eligibility at 100.
- **No attack in calibration** (P2-T04, P3-T02, P7-T09): attack-in-cal rejected.
- **Threshold formulas** (P3-T03…T07): B0 pooled p95, B1 mean-of-local-p95 +
  pooled/weighted, B2 per-client p95 + fallback, B3 family-mean, B4 fingerprint +
  K=3 + cluster mean.
- **Quantile behavior** (P3-T01): local/pooled/weighted/quantile-of-quantiles,
  attainment, reject q-range/empty.
- **B4 clustering** (P3-T07, P5-T03): fingerprint scalars, K mismatch rejected,
  adjusted-Rand known value, feature ablation.
- **B-FedStatsBenign** (P4-T05/06): full pooled variance, between_ratio, matched
  exceedance, tie-break larger k, reject simple variance, reject attack labels.
- **Conformal coverage** (P4-T04): marginal coverage near target, quantile formula.
- **Metric formulas** (P3-T09/T10): Macro-F1 known values, BA, P10 definition.
- **CV(FPR) edge cases** (P3-T10): known value, zero-mean, single-client undefined,
  eligibility filter, reject ineligible inclusion.
- **AUROC invariance/control** (P3-T09): threshold-invariant, monotone-transform
  invariant, not used as verdict.
- **Bootstrap CI** (P7-T03): BCa known-answer, reference-fixture match, exclude-zero
  detection, reject percentile when BCa required.
- **Paired delta** (P7-T03): Wilcoxon known value, Δ = B1 − B2.
- **Claim gates** (P7-T04): confirmatory pass on positive CI, null on zero-crossing,
  opposite flagged, no supportive promotion.
- **Artifact writer/reader** (P1-T07): round-trip, mismatch rejected.
- **Determinism/seed locking** (P1-T06, P1-T03): reproducible seed lock, paired
  streams deterministic.
- **Hardware fallback** (P1-T06): CPU fallback, VRAM limit, reject invalid device.
- **Changelog format** (P1-T10): dashboard, status enum, ticket/phase table
  columns, no result claims.

### 10.2 Integration tests
- Tiny clean pipeline (P2-T10); preprocessing→split manifest (P2-T02/T04);
  split→training fixture (P2-T06); checkpoint freeze + reload (P2-T07); score from
  frozen checkpoint (P2-T08); B1–B4 suite from stored scores (P3-T11); threshold
  variants from stored scores (P4-T01…T06); statistics from per-seed metrics
  (P7-T03); table/figure export from metrics (P4-T09, P5-T07, P7-T07);
  outputs/results layout (P2-T10); no-overwrite behavior (P1-T07); Regime C tiny
  Dirichlet (P6-T09); Regime D tiny external fixture (P6-T05); FedProx tiny stress
  (P6-T10); personalization tiny stress (P6-T11); changelog update after ticket
  (P1-T10).

### 10.3 Smoke / E2E tests
- One tiny synthetic full clean run (P2-T10); one tiny N-BaIoT-like physical-device
  run (P2-T10); one threshold-only rerun proving **no** model retraining (P4-T08);
  one anchor-like 2-seed mini-run (P7-T03); one reporting run from existing outputs
  only (P7-T07); one failure run where leakage/wrong lineage is detected (P7-T09);
  one agent-progress update simulation marking a ticket complete + updating
  CHANGELOG (P1-T10).

### 10.4 Negative / failure-mode tests
- Missing raw dataset (P2-T01); wrong dataset root (P2-T01/P1-T05); mixed client
  IDs (P2-T01/T03); cal/test overlap (P2-T04); attack in calibration (P2-T04);
  ineligible-client threshold misuse (P3-T02); B3 without taxonomy (P3-T06); B4 K
  mismatch (P3-T07); variants trying to retrain (P4-T08); score/checkpoint mismatch
  (P2-T08/P4-T08); config stale policy names (P1-T04/P7-T09); silent overwrite
  attempt (P1-T07); invalid seed plan (P1-T03); invalid q (P3-T01/P4-T01); invalid
  temporal split (P7-T01); invalid Laridi-faithful under benign contract (P4-T07);
  manual hardcoded path (P1-T05); changelog status ≠ master log (P1-T10/P7-T10);
  changelog missing tests-run entry (P1-T10); changelog missing blocker entry when
  blocked (P1-T10).

---

## 11. Artifact Strategy

Contracts defined in P0-T05, implemented in P1-T07. **Outputs = complete runtime
artifacts (gitignored). Results = curated lightweight derived artifacts only.
Checkpoints = frozen weight vault, read-only after selection.**

| Artifact | Producer | Consumers | Reuse-validity keys | Location |
|---|---|---|---|---|
| Raw data | external | loaders | raw hash | `data/raw` (symlink) |
| Preprocessed | P2-T02/P6-T03 | splits, scoring | raw_hash + preprocess_config | `data/preprocessed/` |
| Split manifest | P2-T04/P6-T04/P7-T01 | training, scoring | partition + split_config + seed | `data/manifests/`, `outputs/manifests/` |
| Checkpoint | P2-T07/P6-T05/P6-T10/P6-T11 | scoring only | dataset+regime+seed+train_config+arch | `checkpoints/` |
| Scores | P2-T08/P6-T05 | all thresholds/variants/mechanisms | all six reuse keys + scoring_contract_id | `outputs/scores/` |
| Thresholds | P3/P4 | predictions/metrics | policy + q + score manifest | `outputs/metrics/` |
| Metrics | P3-T10 | statistics/reporting | threshold + metric registry | `outputs/metrics/` |
| Statistical summaries | P7-T03 | claim gates | metrics + stats config | `outputs/confirmatory/stats/` |
| Tables/figures | P4-T09/P5-T07/P7-T06 | manuscript (external) | source manifest | `outputs/{tables,figures}/`, `results/` |
| Run manifests | P1-T07 | audits | config+data+checkpoint+score lineage | `outputs/manifests/` |
| Claim map | P7-T05 | readiness | gate outputs + manifests | `results/supplementary/` |
| Curated results | P7-T06 | sharing | provenance links | `results/` |
| Progress changelog | every ticket | humans/audit | status enum | `CHANGELOG.md` |

Every reusable artifact carries a manifest with hashes/stable IDs sufficient to
prevent accidental mismatch (P1-T07 enforces on read).

---

## 12. Reuse / Caching Strategy

Authority: P0-T09, enforced by P1-T08 (cache), P1-T07 (manifests), P4-T08
(no-retrain guard), P7-T08/T09 (audits).

- **Heavy stages (rerun only on trigger):** preprocessing, FedAvg/FedProx/
  personalization training, checkpoint selection, score generation. Tickets:
  P2-T02, P2-T06, P2-T07, P2-T08, P2-T11, P6-T03, P6-T05, P6-T09, P6-T10, P6-T11,
  P7-T02.
- **Cheap stages (always reuse frozen artifacts):** threshold policies (B0–B4),
  q-sensitivity, shrinkage, calibration-size, B2-conf, `B-FedStatsBenign`,
  mechanism analyses, statistics, tables, figures. Tickets: all of P3, P4, P5,
  plus P6-T06 and P7-T03…T07.
- **Six invalidation triggers (heavy rerun):** change to model, dataset split,
  training algorithm, temporal protocol, preprocessing contract, or scoring
  contract. Any other change (threshold policy, q, shrinkage, comparator, metric,
  table, figure) must reuse.
- **Enforcement:** cheap suites are declared cheap-stage; readiness (P4-T08)
  asserts frozen checkpoints + present scores and spies training entrypoints to
  prove zero training calls; the full-suite dry-run (P7-T08) proves no duplicated
  pipeline exists.

---

## 13. Data and Split Strategy

- **Raw** under `data/raw` (symlink → shared data), gitignored; loaders verify
  presence/schema and never assume dataset facts (Tier 9).
- **Datasets:** N-BaIoT (Regime A/C), Edge-IIoTset (Regime D/D-temporal),
  CICIoT2023 (Regime B-a; B-b rejected).
- **Splits:** per client, benign→train/cal disjoint, test = held-out benign +
  attack; `CalibrationData`/`TestData` are distinct types (compile-time leakage
  guard). Eligibility n_k ≥ 100 with τ_global fallback; coverage = |K_elig|/|K|.
- **Partitions:** physical-device (A, K=9), file-level (B-a, 63), group/device
  (D, K∈[6,15] by audit), Dirichlet (C, 20 clients, α-grid).
- **Temporal:** chronological 70/30 by capture time (Edge-IIoTset only); gapped;
  no future leakage into calibration.
- **Leakage rules (tested):** no attack in calibration; no cal/test overlap; no
  test-set-driven checkpoint selection; preprocessing fit on benign-train only.

---

## 14. Checkpoint and Score-Artifact Strategy

- **Train once** per (dataset, regime, seed, α) to ≤ 200 rounds; save checkpoints
  at {25,50,75,100,125,150,200} with hashes (P2-T07).
- **Selection** uses only benign/diagnostic criteria; Regime A selects one global
  primary checkpoint used for every main-regime table. Test-AUROC / attack-label /
  per-regime / weak-curve-hiding selection is forbidden and tested against.
- **Freeze:** checkpoints are read-only after selection; frozen loader refuses
  writes (P2-T07).
- **Scores:** generated once from the frozen checkpoint; manifest binds all six
  reuse keys + `scoring_contract_id` (P2-T08). B1–B4 and every variant reuse the
  same scores; mismatched score/checkpoint pairs are rejected on load.
- **Cross-dataset:** input_dim differs per dataset (SB-13); N-BaIoT checkpoints
  may never score Edge-IIoTset (tested in P6-T05).

---

## 15. Statistical Validation Strategy

- **Confirmatory statistic:** 95% BCa bootstrap CI on per-seed
  Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s], 10 paired seeds; survives iff CI excludes
  zero positive (P7-T03/T04).
- **BCa audit:** bias-correction + acceleration validated against a known-answer
  fixture and the reference CI behavior; percentile rejected where BCa required.
- **Secondary (descriptive only):** Wilcoxon signed-rank, Cliff's δ; absolute-
  dispersion checks (IQR, max−min) alongside CV to guard small-denominator artifacts.
- **Seed-extension honesty rule:** 10-seed result is the main result even when less
  favorable; CI-discrepancy vs reference (shift toward zero or > ~20% wider) blocks
  expansion claims until resolved (P7-T03).
- **Claim gates (P7-T04):** per-tier pass logic; no supportive/stress/external
  result promoted; weak/mixed/null/opposite mapped to pre-committed fallback IDs.
- **No result values live in this plan or in CHANGELOG** — only implementation and
  test status.

---

## 16. Changelog and Progress-Tracking Strategy

- `CHANGELOG.md` is created in P0-T11 and is a first-class project-control file.
- Format enforced by tests (P1-T10): dashboard, phase table, ticket table, latest-
  update block, completed/in-progress/blocked logs, decision log, test log, files-
  changed log, risks/follow-ups, deviations, next action.
- **Status enum:** Not Started · In Progress · Blocked · Done · Skipped · Split ·
  Merged · Reopened.
- **After every ticket**, the agent appends an update block (template in CHANGELOG)
  and updates dashboard + tables. Marking Done requires a tests-run entry; marking
  Blocked requires a blocker entry (both tested).
- **Consistency:** changelog statuses must match this master log (tested in
  P1-T10 and P7-T10).
- The changelog records **implementation progress, tests, blockers, decisions
  only** — never unverified experimental claims.

---

## 17. Reviewer-Proof Audit Checklist (global, final)

Verified by P7-T09/T10:

- ☐ Scientific identity preserved (fixed encoder, threshold-scope-only ladder).
- ☐ B1–B4 share the same final AE state + scores per seed (no retraining).
- ☐ Benign-only calibration preserved; attack never in calibration.
- ☐ AUROC used only as control, never the thresholding verdict.
- ☐ Regime A confirmatory endpoint isolated (B1 vs B2, CV(FPR), 10 seeds, BCa CI).
- ☐ Supportive/stress/external/mechanism/exploratory never promoted.
- ☐ Edge-IIoTset external validation separated from the confirmatory claim.
- ☐ FedProx / model personalization kept outside the causal ladder.
- ☐ Threshold-only variants reuse scores; no hidden retraining.
- ☐ No stale labels (no `B5`, `B3-LGS`, "Ditto" fallback misname).
- ☐ No compatibility shims/redirects; no temp files; no audit clutter.
- ☐ No duplicated pipelines / one-off logic (dry-run proven).
- ☐ Tests green; lint (`ruff`) + type (`pyright`) green.
- ☐ Artifact manifests valid; result curation reproducible.
- ☐ CHANGELOG up to date; statuses match this master log.

---

## 18. Final Definition of Done

The implementation is done when:

1. All 82 tickets are Done (or explicitly Skipped/Merged/Split with recorded reason).
2. Every phase exit gate passed (P0-T11, P1-T10, P2-T11, P3-T11, P4-T09, P5-T08,
   P6-T12, P7-T10).
3. The global audit checklist (§17) is fully satisfied.
4. `make test`, `make lint`, `make typecheck` are green.
5. Heavy artifacts (checkpoints, scores) exist with valid manifests for Regime A
   (10 seeds), Regime C (α-grid), Regime D (external + temporal), and stress tests.
6. Cheap stages provably reuse frozen artifacts (P4-T08, P7-T08).
7. `results/` contains only curated, reproducible, manifest-traced artifacts.
8. CHANGELOG matches this master log; readiness report signed (P7-T10).

**No experimental result claim is part of the definition of done** — this plan
delivers a validated implementation, not scientific conclusions.

---

## 19. Risks and Mitigation Table

| # | Risk | Impact | Mitigation | Owning tickets |
|---|---|---|---|---|
| R1 | Threshold-only variant silently retrains | Breaks fixed-encoder identity | No-retrain guard + training-entrypoint spy + dry-run | P4-T08, P7-T08 |
| R2 | Score/checkpoint mismatch reused | Invalid results | Six-key manifest binding; reject on load | P1-T07, P2-T08 |
| R3 | Attack data leaks into calibration | Invalidates benign-only contract | Typed `CalibrationData`; global leakage audit | P2-T04, P7-T09 |
| R4 | Test-metric checkpoint selection | HARKing | Selection uses benign/diagnostic only; audit test | P2-T07, P7-T09 |
| R5 | Stale labels leak from reference project | Reviewer confusion | Enum locks + naming tests; behavioral-reference-only doc | P1-T02, P0-T10 |
| R6 | Duplicated per-experiment pipelines | Maintenance + reuse failure | One runner/plan; dry-run duplication detector | P1-T09, P7-T08 |
| R7 | Edge-IIoTset coverage/partition ambiguity | External-validity ceiling | First-principles feasibility audit + coverage gate | P6-T02, P6-T04 |
| R8 | CICIoT2023 feature-count drift (mirror variance) | Wrong quantitative boundary claim | Feature-count re-verification gate before any print | P6-T07 |
| R9 | Model-personalization absorption of the gain | Confirmatory narrowing | Pre-specified absorption bands applied as-is | P6-T11 |
| R10 | CI widens/near-zero under 10-seed extension | Confirmatory weakened | Seed-extension honesty + CI-discrepancy block rule | P7-T03 |
| R11 | Non-deterministic reporting | Non-reproducible tables/figures | Reproducibility checks; reporting reads outputs only | P7-T07 |
| R12 | Changelog drifts from master log | Lost progress integrity | Format + consistency tests | P1-T10, P7-T10 |
| R13 | Scope drift (privacy/drift/poisoning) | Identity violation | Scope-boundary doc + Tier-9 forbidden tests | P0-T01, P0-T02 |
| R14 | Silent output overwrite | Data loss / provenance break | No-overwrite policy; versioned dirs | P1-T07 |

---

## 20. Open Questions and Blockers

None are coding blockers for Phase 0–5 (all reuse Regime A stored artifacts).
Two conditional gates (from roadmap §20) affect only later, non-confirmatory work:

- **OQ1 (blocking for CICIoT2023 print claims only):** verify the feature count of
  the *actual* processed CICIoT2023 artifact (expected d=39; mirrors differ).
  Resolved in P6-T07 before any B-a quantitative statement. Does **not** block
  Regime A/C.
- **OQ2 (blocking for Tier-3 external claim only):** Edge-IIoTset eligibility
  coverage (n_k ≥ 100 for ≥ 90% of clients) and device-vs-group partition, decided
  by the P6-T02 feasibility audit. Failure → reduce K or defer temporal MVE; the
  confirmatory claim is unaffected.
- **OQ3 (implementation choice, non-blocking):** true Ditto vs `FedRep-AE`/
  `FedPer-AE` fallback for P6-T11 — decided and documented before training; the
  fallback is never labeled "Ditto" (SB-24).

No open question alters the locked confirmatory endpoint.

---

## 21. Final Counts and Justification

- **Total phases:** 8.
- **Total tickets:** 82.
- **Tickets per phase:** P0 = 11 · P1 = 10 · P2 = 11 · P3 = 11 · P4 = 9 · P5 = 8 ·
  P6 = 12 · P7 = 10.
- **Heavy-stage tickets:** 11 (P2-T02, P2-T06, P2-T07, P2-T08, P2-T11, P6-T03,
  P6-T05, P6-T09, P6-T10, P6-T11, P7-T02).
- **Threshold-only / reuse-stage tickets:** 33 (all P3 + all P4 + all P5 + P6-T06 +
  P7-T03…T07).
- **Testing / audit-focused tickets:** 12 (P0-T08, P1-T10, P2-T10, P3-T11, P4-T08,
  P5-T08, P7-T03, P7-T05, P7-T07, P7-T08, P7-T09, P7-T10).
- **Changelog / progress-tracking tickets:** 2 dedicated (P0-T11, P1-T10) + a
  mandatory update on all 82 tickets.

**Why 82 rather than ~60.** The brief permitted increasing the count for clean
testing, gates, artifact contracts, and reviewer-proof separation, and required
that no ticket be vague or overloaded. DATP is driven by 28 reviewer attacks
(L01–L28) and 32 scope boundaries (SB-01–SB-32), and its correctness rests on a
strict heavy/cheap reuse split. Holding to ~60 would have forced merges that mix
unrelated concerns — e.g. one "implement thresholding" ticket instead of a
separate quantile backbone, policy interface, five policies, and an equivalence
suite; or one "stress tests" ticket instead of FedProx, personalization,
comparator, and reporting. 82 keeps every ticket single-concern while covering
every locked regime, policy, comparator, mechanism, dataset guard, statistic, and
audit. The excess over 60 (≈ 22 tickets) is concentrated in Phase 0 freezes,
per-policy isolation (Phase 3), and reviewer-proof audits (Phase 7) — exactly the
areas where conflation would create reviewer risk.

---

*End of MASTER_TICKET_LOG.md. Progress is tracked in [CHANGELOG.md](CHANGELOG.md).*
