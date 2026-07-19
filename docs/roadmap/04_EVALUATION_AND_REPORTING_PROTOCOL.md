# 04 — Evaluation and Reporting Protocol

**Purpose.** Own evaluation, statistics, provenance, and reporting: metric definitions, the locked statistical plan, seed structure, BCa requirements, checkpoint protocol, and the rules for tables, figures, diagnostics, and main-paper-versus-appendix placement. This file defines *how results are measured and reported*, never which experiments exist or what may be claimed.

**What this file owns.**
- Primary, secondary, optional, and control metrics, with exact definitions.
- Eligible-client aggregation rules.
- Statistical procedures, seed structure, BCa bootstrap requirements, secondary tests, and effect sizes.
- Small-denominator safeguards and checkpoint evaluation/selection restrictions.
- Temporal-recalibration metric formulas.
- Artifact/provenance reporting and traceability requirements.
- Required tables, figures, and diagnostics, and main-paper versus appendix placement.
- Manuscript-section mapping and rules preventing favorable-result selection.

**What this file does not own.**
- Experiment scope, prerequisites, and dependencies → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- Claim consequences, fallback wording, absorption bands, and temporal-outcome interpretations → see [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md).
- Implementation of manifests, provenance flow, and determinism → see [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md).
- Readiness checklists → see [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md).

**Related files.** [00 — Index](./00_ROADMAP_INDEX.md) · [02 — Claims](./02_CLAIMS_AND_DECISION_RULES.md) · [03 — Experiments](./03_EXPERIMENT_CATALOGUE.md) · [05 — Implementation](./05_IMPLEMENTATION_ROADMAP.md)

---

## Metrics

**Primary metric.** CV(FPR) = σ_FPR / µ_FPR over eligible clients (n_k ≥ n_min = 100 benign calibration samples). CV(FPR) definition is identical to the conference version and is never silently changed (enforced by [SB-15](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)).

**Secondary operating-point metrics.** worst-client FPR; IQR(FPR); max−min FPR; alert burden (only with a real or cited traffic rate); CV(TPR); P10 Macro-F1; worst-client balanced accuracy.

**Optional equity metrics.** Jain index; Gini coefficient; within/across-cluster dispersion. Reported alongside CV(FPR), never replacing it.

**Model-quality controls (not thresholding verdicts).** AUROC; Macro-F1; balanced accuracy.

**Threshold-estimation metrics (federated-quantile backbone).** quantile-estimation error vs centralized oracle; threshold variance; FPR-target attainment (|achieved exceedance − (1−q)|); calibration sample efficiency.

### Eligible-client aggregation rule

CV(FPR) is computed over **eligible clients** (n_k ≥ n_min = 100 benign calibration samples); calibration-pending clients fall back to τ_global, and coverage is reported as |K_elig|/|K|. Absolute-dispersion checks accompany CV wherever mean FPR is small.

---

## Statistical requirements (locked)

- 10 paired seeds for the confirmatory claim; per-seed Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s].
- 95% **BCa** bootstrap CI on the per-seed Δ for the primary claim (BCa preferred over percentile for small samples).
- Wilcoxon signed-rank and matched-pairs rank-biserial correlation (the paired effect size; replaces Cliff's δ, which is an unpaired/independent-samples statistic unsuited to this program's entirely paired-seed design) are descriptive secondary evidence only.
- Absolute-dispersion checks (IQR, max−min) accompany CV wherever mean FPR is small, to guard against small-denominator artifacts.
- No test-set-driven checkpoint selection. No poisoned, stress-test, or external-regime metric selects the main checkpoint. Regime A alone selects one global primary checkpoint used for every main-regime table.
- Null and mixed results remain reportable and are pre-committed to fallback wording (see [02 — Fallback Wording](./02_CLAIMS_AND_DECISION_RULES.md#fallback-wording)).

**Seed-extension honesty rule.** The rule governing when the 10-seed result replaces the 5-seed result, and when expansion claims are blocked, is owned by [02 — Seed-extension honesty rule](./02_CLAIMS_AND_DECISION_RULES.md#seed-extension-honesty-rule-affects-claim-status) because it determines claim status. The underlying seed structure (10 paired seeds; per-seed Δ_s; 95% BCa CI) is specified above.

---

## Journal checkpoint protocol (locked)

Train once to a maximum of 200 rounds; save and evaluate checkpoints at rounds {25, 50, 75, 100, 125, 150, 200}. Convergence is logged as diagnostic metadata and does not stop training. Regime A selects one global primary checkpoint; that checkpoint is used for every main-regime table. Other checkpoints are supplementary stability evidence. Per-regime selection, test-AUROC selection, attack-label selection, and hiding weak checkpoint curves are all forbidden.

---

## Temporal recalibration metrics

For the Edge-IIoTset chronological experiment (procedure owned by [03 — Temporal recalibration experiment](./03_EXPERIMENT_CATALOGUE.md#temporal-recalibration-experiment)):

- `static_reference_cv`, `frozen_future_cv`, and `recalibrated_future_cv` are all reported.
- `drift_excess = frozen_future_cv − static_reference_cv`.
- `recovered_amount = frozen_future_cv − recalibrated_future_cv`.
- `recovery_ratio = recovered_amount / drift_excess`, computed **only** when `drift_excess` is meaningfully positive (undefined and never computed otherwise).
- The seed analysis is paired over the locked seed cohort with a 95% BCa bootstrap CI.

Outcome interpretation of these quantities (Outcomes A/B/C) is owned by [02 — Locked temporal-outcome interpretations](./02_CLAIMS_AND_DECISION_RULES.md#locked-temporal-outcome-interpretations).

---

## Reporting, tables, figures, and placement

- **Placement rule.** Regime A alone selects one global primary checkpoint used for every main-regime table; other checkpoints are supplementary stability evidence. Exploratory material (e.g. B4 at other K, the federated-quantile backbone) goes to the supplement; the main paper stays readable and focused.
- **Main-paper versus appendix.** The per-experiment `Placement` column in [03 — Experiment Matrix](./03_EXPERIMENT_CATALOGUE.md#experiment-matrix) is the canonical source of each result's main/supplement placement. Optional (E-Q*) experiments are supplement/backbone.
- **Required diagnostics.** Convergence logged as diagnostic metadata; between_ratio reported in main text for `B-FedStatsBenign`; within/across-cluster dispersion and cluster stability (adjusted Rand) for the cluster module; absolute-dispersion checks alongside CV(FPR).
- **Traceability.** Every table and figure traces to a manifest (config → checkpoint → scores → metrics → table/figure); implementation of that manifest flow is owned by [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md#provenance-and-traceability).
- **Figures.** Every figure is redrawn with additional series or replaced (see [01 — Originality plan](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#conference-to-journal-originality-plan)); do not use a Sankey diagram for B4 interpretability at K = 3/9 — use a contingency table or small heatmap ([SB-19](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)).

### Manuscript-section mapping

The roadmap maps to manuscript sections as follows (derived from claim tiers and experiment placement):

- **Results** ← Tier 1–7 claims ([02 — Claim hierarchy](./02_CLAIMS_AND_DECISION_RULES.md#claim-hierarchy)) and the experiment matrix ([03](./03_EXPERIMENT_CATALOGUE.md#experiment-matrix)).
- **Methods** ← metrics and statistics (this file) and the implementation contract ([05](./05_IMPLEMENTATION_ROADMAP.md)).
- **Discussion / Limitations** ← boundary-condition claims ([02 — Tier 6](./02_CLAIMS_AND_DECISION_RULES.md#tier-6--boundary-condition-claims)), fallback wording, and residual risks ([06](./06_REVIEWER_RISKS_AND_READINESS.md)).
- **Related Work** ← reviewer objections L02/L06 and the originality plan ([06](./06_REVIEWER_RISKS_AND_READINESS.md), [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#conference-to-journal-originality-plan)).
- **Abstract / Conclusion** ← executive summary and the locked claim ([00](./00_ROADMAP_INDEX.md), [02 — Locked claim](./02_CLAIMS_AND_DECISION_RULES.md#locked-main-journal-claim)).
- **Cover letter** ← originality plan ([01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#conference-to-journal-originality-plan)).

The full manuscript-readiness checklist (prose order Results → Methods → Discussion → Limitations → Related Work → Abstract → Conclusion → Supplement → cover letter) is owned by [06 — Manuscript Readiness Checklist](./06_REVIEWER_RISKS_AND_READINESS.md#manuscript-readiness-checklist).

---

## Rules preventing favorable-result selection

- No test-set-driven checkpoint selection; no poisoned, stress-test, or external-regime metric selects the main checkpoint.
- No cherry-picked checkpoint, K, or calibration size; K = 3 is canonical and pre-committed ([SB-32](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)).
- The `B-FedStatsBenign` protocol is locked before computation ([SB-22](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)).
- Null and mixed results remain reportable; the 10-seed result is never suppressed when less favorable ([SB-21](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)).
- Anti-HARKing and non-suppression rules are owned by [02 — Anti-HARKing and non-suppression rules](./02_CLAIMS_AND_DECISION_RULES.md#anti-harking-and-non-suppression-rules).
