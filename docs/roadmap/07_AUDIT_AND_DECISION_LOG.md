# 07 — Audit and Decision Log

**Purpose.** Own audit history and decisions: the audits already contained in the source roadmap, the existing go / no-go / conditional-go findings and feasibility gates, the record of what changed from the previous roadmap, and a dedicated verification of *this* roadmap-package split. It cleanly separates audits inherited from the source from audits performed to verify the restructuring.

**What this file owns.**
- Audits already contained in the source roadmap (Audits 1–7 and the path scan).
- Existing pass / conditional-pass / go / conditional-go findings and residual issues.
- Existing feasibility gates, immediate-start decisions, and unresolved conditions.
- The record of what changed from the previous roadmap.
- A single `Roadmap Package Split Verification` section with the audits performed for this task.

**What this file does not own.**
- The claim system and decision rules being audited → see [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md).
- Experiment definitions → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- Reviewer risks and readiness checklists → see [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md).

**Related files.** [00 — Index](./00_ROADMAP_INDEX.md) · [01 — Identity](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) · [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md)

---

## Existing audits (from the source roadmap)

These audit findings are inherited verbatim from the source roadmap. They are historical conclusions about the roadmap's scientific content and are **not** re-adjudicated by the package split.

### Audit 1 — Identity Preservation
- DATP remains threshold-scope-only: the sole causal variable is threshold-calibration scope. **Pass.**
- Fixed encoder preserved across B1–B4; score-artifact reuse without retraining. **Pass.**
- Stress tests (FedProx, model personalization, Laridi-style) are outside the causal ladder. **Pass.**
- Dynamic DATP, poisoning, privacy, deployment, backdoor, evasion, full drift are not absorbed; each is future work or out of scope. **Pass.**
- Residual note: the Federated-Quantile backbone touches B1 constructions; verified it is a *descriptive* estimation framing over the fixed ladder, not a new causal variable. **Pass with note.**

### Audit 2 — Claim Discipline
- Confirmatory (Tier 1) is isolated and singular; supportive/external/stress/mechanism/boundary/exploratory/future/forbidden tiers are separated. **Pass.**
- Every claim row carries evidence, regime, metric, pass condition, fallback, placement. **Pass.**
- Forbidden claims enumerated; "fairness" defined once. **Pass.**
- Null/mixed/opposite outcomes handled with pre-committed wording for every major claim. **Pass.**
- No supportive module is promoted to confirmatory; the 2×2 spin-off and cluster module are explicitly non-confirmatory. **Pass.**

### Audit 3 — Module Integration
- All four modules integrated with correct roles: Cluster/Family = core mechanism; Small-Cal/Shrinkage = supportive variant; Federated Quantiles = backbone; Model-vs-Threshold = stress test / spin-off. **Pass.**
- None bloats the confirmatory claim; each appears in RQs, matrix, register, checklists. **Pass.**
- Optional/spin-off status explicit (PC-11 for cluster, PC-5 for small-cal, PC-12 for model-vs-threshold; quantiles never standalone). **Pass.**

### Audit 4 — Reviewer Loopholes
- 28 objections covered including tautology, Laridi novelty, clustering-is-known, HARKing, absorption, comparator fairness, pseudo-clients, external-validation mixed results, Macro-F1 hiding, human-vs-service fairness, privacy, deployment, overlap, too-broad/too-narrow, inherited/scratch code. **Pass.**
- Each defense is testable (mapped to an experiment ID) or a locked wording; none is untestable-masquerading-as-evidence. **Pass.**
- Residual: L12 (absorption) and L02 (Laridi) remain the two highest residual risks; both have pre-specified interpretation rules that keep all outcomes reportable. **Pass with flagged residuals.**

### Audit 5 — Path and Scope Hygiene
- Automated scan confirms no repository/document/output/data paths remain except `/home/naslouby/Projects/datp`. **Pass** (see scan result).
- The allowed path is described only as a behavioral reference. **Pass.**
- No backward compatibility, shims, redirects, or migration layers are required; the implementation is described as scratch/clean. **Pass.**

### Audit 6 — Experimental Feasibility
- Mandatory confirmatory (E-C1) is a stored-score recomputation with a 10-seed extension — realistic. **Pass.**
- Optional experiments marked optional; suppressed/rejected documented with reasons. **Pass.**
- Edge-IIoTset feasibility gated on eligibility coverage; CICIoT2023 B-b/temporal feasibility rejections are not overclaimed. **Pass.**
- Statistical requirements (10 seeds, BCa CI) are feasible on the described hardware and stored artifacts. **Pass.**
- Feasibility flag surfaced: CICIoT2023 feature count (d = 39 in the conference artifact) must be re-verified against the actual processed artifact before any print claim, because mirror distributions differ in column count. **Conditional — flagged.**

### Audit 7 — Manuscript Readiness
- The roadmap directly guides Results, Methods, Discussion/Limitations, Related Work, Abstract/Conclusion, and cover letter. **Pass.**
- Fallback wording present for every major claim. **Pass.**
- Anti-HARKing controls: pre-specification before observation, locked K, locked protocols, suppression rules. **Pass.**
- Clear conference→journal extension story with reuse/new/redrawn split and ≥ 40% benchmark. **Pass.**

**Audit 5 scan result.** An automated token scan over the full source document finds zero repository, document, output, runtime-artifact, temp-root, or raw/processed-data paths. The only path token present is `/home/naslouby/Projects/datp` (5 occurrences), each describing it as a behavioral reference. All remaining slash tokens are terminology (e.g. Cluster/Family, AI/ML, B3/B4, within/across), not paths. **Audit 5 Pass confirmed.**

---

## Go / No-Go / Conditional-Go Summary

**Verdict: GO — with two conditional gates.**

The roadmap is coherent enough to guide implementation. The scientific identity is intact (fixed encoder, threshold-scope-only causal ladder, benign-only calibration, CV(FPR) primary, AUROC control). The confirmatory endpoint is singular and locked with a hard survival rule. The four modules are integrated in their correct roles without disturbing the confirmatory claim. Stress tests are outside the causal ladder. Fallback wording, suppression rules, and scope boundaries are pre-committed. Path hygiene is clean.

**Conditional gate 1 (feasibility — non-blocking for start, blocking for print).** Before any quantitative CICIoT2023 statement reaches print, re-verify the feature count of the actual processed artifact (conference value d = 39; mirror distributions differ). This does not block starting stored-score work on Regime A/C, which is where the confirmatory and most supportive claims live.

**Conditional gate 2 (external validation — blocking for the Tier 3 claim only).** The Edge-IIoTset external-validation claim proceeds only if eligibility coverage is met (n_k ≥ 100 for ≥ 90% of clients) and the device-vs-group partition is assigned by the first-principles feasibility audit. If coverage fails, reduce K or defer the temporal MVE to supplement per the locked wording — the confirmatory claim is unaffected.

**Immediate-start work (no dependency, lowest risk).** All existing-score extensions: E-C1 (10-seed confirmatory), E-S1/S2/S3, E-M1–M5, E-V1/V2/V3, E-T3 (`B-FedStatsBenign`), E-O1, plus Appendix A. These close the tautology critique and populate the mechanism story before any new dataset or training infrastructure is touched. (Execution phases: [05 — Execution phases](./05_IMPLEMENTATION_ROADMAP.md#execution-phases-and-dependency-order).)

**Two residual risks accepted with pre-specified handling.** Model-personalization absorption (E-T2, four bands, all reportable) and Laridi novelty (E-T3 matched-exceedance benign-only + `B-LaridiFaithful` out-of-scope disclosure). Neither can invalidate the confirmatory claim; both keep every outcome honest.

---

## What changed from the previous roadmap (source record)

This is the source roadmap's own record of how it changed from its predecessor. It is a historical decision log, preserved here unchanged.

- **Four modules woven in, not appended.** Cluster/Family Thresholding is now the core mechanism module (RQ2, Tier 5); Small-Calibration/Shrinkage is a supportive variant (RQ3); Federated Quantiles is a methods backbone/primitive (RQ4); Model-vs-Threshold Personalization is the external stress test (RQ5, possible spin-off). Each is placed in claim hierarchy, RQs, regime table, experiment matrix, reviewer register, checklists, and fallback wording.
- **All operational file paths removed.** Every repository, document, output, runtime-artifact, temp-root, and raw/processed-data path from the previous version is gone. The only remaining path is `/home/naslouby/Projects/datp`, used strictly as a behavioral reference. Status enums (`B_B_REJECTED_NO_METADATA`, `TEMPORAL_REJECTED_NO_TIMESTAMPS`, `REUSE_BLOCKED_*`) are retained as labels, not paths.
- **Claim hierarchy formalized into nine tiers** with per-claim evidence, regime, metric, pass condition, fallback, reviewer risk, and placement; the confirmatory endpoint is isolated at Tier 1 with a hard survival rule.
- **Federated-quantile backbone made explicit.** B1/B1-pool/B1-wt/B2/`B-FedStatsBenign` are now framed as a single quantile-estimation design space with uniform estimation-error / FPR-target-attainment metrics — replacing hand-waved percentile logic without any novelty overclaim.
- **2×2 personalization reconciliation.** The full 2×2 with cost accounting is now explicitly the spin-off; the in-paper realization is one model-personalization comparator × B1–B4 with the absorption ratio reading directly off the corners, honoring the one-stress-test limit.
- **Cluster module upgraded from two flat baselines to a granularity+stability science** (within/across dispersion, adjusted-Rand stability, feature ablation, contingency-table interpretability) with an explicit "clustering is known" defense.
- **Execution reorganized around a path-free gate/phase narrative** (existing-score extensions → dataset expansion → training-side stress tests) instead of task-group tables tied to a repository layout.
- **Fallback wording extended** to every module claim (cluster recovery, cluster stability, small windows, shrinkage, quantiles, absorption, FedProx, Edge-IIoTset, CICIoT2023 boundary), each with strong/weak/mixed/null/opposite/feasibility/suppressed variants.
- **Scope boundaries preserved and renumbered** (SB-01–SB-32), and the reviewer register expanded to 28 entries covering every objection in the integration prompt including the scratch-codebase reproducibility line.
- **Preserved unchanged:** venue decisions (Computer Networks primary, IoT backup, COSE excluded); the locked `B-FedStatsBenign` protocol (full pooled variance, matched exceedance); the Laridi faithful/benign-only disclosure; FedProx/model-personalization as external stress tests; the three-outcome temporal MVE on Edge-IIoTset only; the ≥ 40% self-imposed extension benchmark; the 10-seed honesty rule; the confirmatory endpoint.

---

## Roadmap Package Split Verification

This section documents the audits performed **specifically to verify this documentation-restructuring task** (splitting `docs/Journal_Extension_Master_Roadmap.md` into the eight-file `docs/roadmap/` package). These are new audits about the restructuring; they do **not** re-adjudicate the source roadmap's own historical findings above.

### Source integrity

- Source file: `docs/Journal_Extension_Master_Roadmap.md`, 622 lines, SHA256 `cee0a6072df967ce8e030189db7a2bf48e1f2c7ff42ce9492747964d8f7c8bce`.
- The source file is unchanged by this task (verified by checksum comparison before and after the split, and by repository diff inspection).

### Source-section → destination mapping

| Source section | Destination file(s) |
|---|---|
| Front matter (title, working title, venues, reference project) | [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#working-title-and-venue) (canonical); summarized in [00](./00_ROADMAP_INDEX.md) |
| §1 Executive Summary | [00](./00_ROADMAP_INDEX.md#executive-summary) (concise); identity/does-not-claim → [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md); risk summary → [06](./06_REVIEWER_RISKS_AND_READINESS.md#risk-summary) |
| §2 Non-Negotiable Scientific Identity + fairness | [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#non-negotiable-scientific-identity-locked) |
| §3 Locked Main Journal Claim + confirmatory endpoint + reference values | [02](./02_CLAIMS_AND_DECISION_RULES.md#locked-main-journal-claim) |
| §4 Threshold-Policy and Comparator Nomenclature + naming locks | [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#threshold-policy-and-comparator-nomenclature-locked) |
| §5 Claim Hierarchy (Tiers 1–9) | [02](./02_CLAIMS_AND_DECISION_RULES.md#claim-hierarchy) |
| §6 Research Questions | [02](./02_CLAIMS_AND_DECISION_RULES.md#research-questions) |
| §7 Experimental Regime Table + feasibility flags + Edge clarification | [03](./03_EXPERIMENT_CATALOGUE.md#experimental-regime-table) |
| §8 Module Integration Table + 2×2 reconciliation | [03](./03_EXPERIMENT_CATALOGUE.md#module-integration-table) |
| §9 Experiment Matrix (9.1–9.5) | [03](./03_EXPERIMENT_CATALOGUE.md#experiment-matrix); absorption bands (9.3) → [02](./02_CLAIMS_AND_DECISION_RULES.md#model-personalization-absorption-bands-pre-specified) |
| §10 Metrics and Statistical Plan | [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#metrics); seed-extension honesty rule → [02](./02_CLAIMS_AND_DECISION_RULES.md#seed-extension-honesty-rule-affects-claim-status) |
| §11 Temporal Recalibration (procedure) | [03](./03_EXPERIMENT_CATALOGUE.md#temporal-recalibration-experiment); metrics → [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#temporal-recalibration-metrics); §11.1 outcomes → [02](./02_CLAIMS_AND_DECISION_RULES.md#locked-temporal-outcome-interpretations) |
| §12 Fallback Wording (12.1–12.10) | [02](./02_CLAIMS_AND_DECISION_RULES.md#fallback-wording) |
| §13 Reviewer Loophole Register (L01–L28) | [06](./06_REVIEWER_RISKS_AND_READINESS.md#reviewer-loophole-register) |
| §14 Checklists (14.1–14.5) | [06](./06_REVIEWER_RISKS_AND_READINESS.md#checklists); manuscript-section mapping → [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#manuscript-section-mapping) |
| §15 Conference-to-Journal Originality Plan | [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#conference-to-journal-originality-plan) |
| §16 Scope Boundaries (SB-01–SB-32) | [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels) |
| §17 Implementation Planning — Code From Scratch | [05](./05_IMPLEMENTATION_ROADMAP.md) |
| §18 What Changed From the Previous Roadmap | [07 — What changed](#what-changed-from-the-previous-roadmap-source-record) |
| §19 Audit Reports (Audit 1–7 + scan) | [07 — Existing audits](#existing-audits-from-the-source-roadmap) |
| §20 Go / No-Go / Conditional-Go Summary | [07 — Go / No-Go](#go--no-go--conditional-go-summary); immediate-start ordering → [05](./05_IMPLEMENTATION_ROADMAP.md#execution-phases-and-dependency-order); readiness → [06](./06_REVIEWER_RISKS_AND_READINESS.md#submission-readiness-conditions-and-residual-risks) |

### Split-task audit results

| Audit | Scope | Result |
|---|---|---|
| Audit 1 — Source Coverage | Every heading, table, experiment, claim, checklist, fallback block, reviewer objection, audit, decision represented | PASS — all §1–§20 mapped above; 6 regimes, 9 claim tiers, 17 mandatory + 6 optional + 8 rejected experiments, L01–L28, SB-01–SB-32, 10 fallback blocks, 5 checklists all present |
| Audit 2 — Locked Scientific Fidelity | Main claim, endpoint, B1–B4 meanings, comparator names, datasets/regimes, formulas, metrics, seed counts, thresholds, checkpoint rounds, CIs, pass conditions, outcome rules, exclusions | PASS — locked statements reproduced verbatim; numeric values (1.017, 0.299, 0.718, [0.647, 0.769], 70.6%, 0.645, 0.964, 0.344→0.300, n_min=100, checkpoints {25,50,75,100,125,150,200}, absorption 0.75/0.25/0.05, split 55/15/10/20) preserved |
| Audit 3 — Experiment & Claim Traceability | Each experiment's classification, claim, metric, prerequisite, decision/fallback, placement; each claim's supporting experiments | PASS — evidentiary roles preserved; no weaker experiment promoted; null/mixed handling retained |
| Audit 4 — Canonical Ownership & Duplication | One canonical owner per rule; no competing copies | PASS — shared subjects (absorption bands, temporal outcomes, fallback, seed-extension rule) have a single canonical owner with links from other files |
| Audit 5 — Cross-File Consistency | Terminology, policy names, identifiers, datasets, status, evidentiary roles | PASS — with one source-inherited contradiction flagged below (not introduced by the split) |
| Audit 6 — Navigation & Markdown | Files exist, links resolve, anchors valid, no architecture links, headings/tables/fences valid | PASS — eight files present; internal links relative; no link points to `docs/Architecture/` or invented files |
| Audit 7 — Scope & Repository Hygiene | Source byte-for-byte unchanged; no code/test/config/ticket/architecture changes; only the eight files created | PASS — verified via checksum and `git status`; only `docs/roadmap/` files added |
| Audit 8 — Final Cold-Read | A fresh reader can locate identity, locks, scope, claim, experiments, statistics, implementation, risks, blockers | PASS — the index plus per-file purpose/owns/does-not-own headers make the package independently navigable |

### Source-roadmap contradictions (flagged)

The following is an internal inconsistency **present in the source roadmap**. Both statements are preserved as-is; no winner is chosen; resolution requires a future roadmap decision.

1. **Regime D threshold policies (B3 inclusion).** §7's regime table row for Regime D lists threshold policies as `B1–B4`, and E-X1 (§9.2) likewise lists `B1–B4 + B-FedStatsBenign + q`. However, the post-audit "Edge-IIoTset scope clarification" in §7 states that "B3 family thresholding is omitted (no Edge-IIoTset family taxonomy)." These two statements disagree on whether B3 runs in Regime D. Both are preserved in [03 — Experimental Regime Table](./03_EXPERIMENT_CATALOGUE.md#experimental-regime-table). **Requires a future roadmap decision.**

### Defects found and corrected during the split

- None affecting scientific content. All corrections were internal-link/anchor consistency fixes applied during the navigation audit; no source wording, numeric value, or classification was altered.

### Final verification verdict

**PASS WITH SOURCE-ROADMAP FLAGS** — the eight-file package faithfully represents the source; the source is unchanged; one pre-existing source contradiction (Regime D B3 inclusion) is preserved and flagged for a future roadmap decision rather than silently resolved.
