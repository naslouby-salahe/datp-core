# 02 — Claims and Decision Rules

**Purpose.** Own the complete claim system: the locked main claim and sole confirmatory endpoint, the full nine-tier claim hierarchy, the research questions, and every decision rule that determines whether a claim survives, is narrowed, or is reported as a negative. This file governs *what may be claimed and under what conditions* — never the experimental procedure or the statistics themselves.

**What this file owns.**
- Locked main journal claim and the sole confirmatory endpoint.
- Reference conference values to be reproduced and honestly extended.
- The full nine-tier claim hierarchy (evidence, regime, metric, minimum pass, fallback, placement).
- Research questions (RQ1–RQ6) and their tier mapping.
- Evidence classification, minimum pass conditions, and claim-survival rules.
- Statistical decision boundaries that determine claims (CI-excludes-zero, absorption bands, temporal outcomes).
- Weak / mixed / null / contradictory / infeasible / failed-result interpretations (fallback wording).
- Seed-extension honesty rule affecting claim status.
- External-validation interpretation rules and temporal-recalibration outcome interpretations.
- Anti-HARKing and non-suppression rules.

**What this file does not own.**
- Experiment definitions, inputs, prerequisites, and dependencies → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- Metric definitions, seed structure, BCa mechanics, and reporting placement → see [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md).
- Scientific identity, nomenclature, and scope boundaries → see [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md).
- Reviewer-objection defence and readiness checklists → see [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md).

**Related files.** [00 — Index](./00_ROADMAP_INDEX.md) · [01 — Identity](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) · [03 — Experiments](./03_EXPERIMENT_CATALOGUE.md) · [04 — Evaluation](./04_EVALUATION_AND_REPORTING_PROTOCOL.md)

---

## Locked Main Journal Claim

> **DATP's threshold-scope effect remains observable under a stronger journal protocol that adds external validation, a matched federated-threshold comparator, model/aggregation stress tests, and mechanism analyses, while preserving the fixed-encoder threshold-calibration identity.**

### Sole confirmatory endpoint

The **sole confirmatory endpoint** is tightly scoped and immutable:

- Regime A only (N-BaIoT natural physical-device split).
- B1 vs B2 only.
- CV(FPR) only.
- 10-seed paired evidence.
- 95% BCa bootstrap confidence interval on the per-seed delta.
- Δ_s = CV(FPR)[B1, s] − CV(FPR)[B2, s].
- **The confirmatory claim survives only if the BCa CI excludes zero in the correct (positive) direction.**

**Reference conference values to be reproduced and honestly extended:** B1 CV(FPR) = 1.017, B2 = 0.299, Δ = 0.718, 5-seed bootstrap CI [0.647, 0.769], 70.6% relative reduction, all seed deltas positive; B4 CV(FPR) = 0.645 (≈52% recovery); B3 = 0.964 (negligible); P10 Macro-F1 falls 0.344 → 0.300 under B2.

**Everything other than the confirmatory endpoint** is explicitly classified as exactly one of: supportive evidence, external validation, stress test, mechanism analysis, threshold variant, boundary condition, exploratory analysis, suppression evidence, future work, or possible spin-off. No supportive module may become a confirmatory claim.

---

## Claim Hierarchy

Nine ordered tiers. Each claim carries evidence, regime, metric, minimum pass condition, weak/null fallback, reviewer risk, and manuscript placement. Confirmatory sits alone at Tier 1; nothing below it may be promoted.

### Tier 1 — Locked Confirmatory Claim

| Field | Specification |
|---|---|
| Claim text | Under Regime A natural device split, per-client p95 calibration (B2) reduces CV(FPR) relative to the client-averaged shared threshold (B1) by a magnitude whose 95% BCa bootstrap CI on the per-seed delta excludes zero (positive direction). |
| Evidence required | 10 paired seeds; Δ_s per seed; BCa CI on Δ; sign-consistency summary |
| Dataset / regime | Regime A (N-BaIoT, K = 9), confirmatory |
| Metric | CV(FPR) (primary) |
| Minimum pass condition | BCa CI excludes zero, positive direction |
| Fallback if weak/mixed/null | See [§ B1 vs B2 Confirmatory fallback](#b1-vs-b2-confirmatory-tier-1); if CI touches/crosses zero, the confirmatory claim is revised to the observed direction and reported as the main result — never suppressed |
| Reviewer risk | "B2 equalizes FPR by construction" (tautology) — mitigated by Appendix A + B2-conf + calibration-size sweep (see [06 — L04](./06_REVIEWER_RISKS_AND_READINESS.md#reviewer-loophole-register)) |
| Placement | Main paper (headline result) |

Experiment: [E-C1 in 03](./03_EXPERIMENT_CATALOGUE.md#mandatory-confirmatory). Statistics: [04 — Statistical requirements](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#statistical-requirements-locked).

### Tier 2 — Secondary Supportive Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The B1→B2 reduction is not an artifact of the arithmetic-mean construction | Pooled and sample-weighted shared variants | Regime A | CV(FPR), IQR, max−min | All shared variants exceed B2 CV(FPR) | Main |
| The reduction holds in absolute dispersion, not only CV | IQR(FPR), max−min FPR | Regime A | IQR, max−min | Same B1 > B2 ordering | Main |
| The effect is heterogeneity-graded | Dirichlet α sweep | Regime C | CV(FPR) delta | Gap largest at low α, vanishes at IID | Main |
| The headline is not a q = 0.95 artifact | q-sensitivity sweep | Regime A | CV(FPR) | B2 < B4 < B1 ordering preserved across q (inversions reported) | Main |

### Tier 3 — External Validation Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The threshold-scope effect generalizes to an independent sensor-group-partitioned dataset | B1–B4 + q-sensitivity + `B-FedStatsBenign` on Edge-IIoTset | Regime D | CV(FPR) + BCa CI | Effect direction consistent with Regime A, or divergence reported as boundary | Main |

> External-validation is Tier 3 evidence only, never a second confirmatory endpoint. Interpretation rules: [§ Edge-IIoTset External Validation](#edge-iiotset-external-validation).

### Tier 4 — Stress-Test Claims (Outside Causal Ladder)

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The gain is not absorbed by heterogeneity-aware aggregation | FedProx × B1–B4, µ-grid frozen | Regime A + D | CV(FPR) delta | Δ under FedProx compared to Δ under FedAvg; any absorption reported | Main (stress-test table) |
| The gain is not absorbed by model-side personalization | One model-personalization comparator × B1–B4; absorption ratio | Regime A + D | Δ_personalized / Δ_FedAvg | Pre-specified absorption bands ([§ Absorption bands](#model-personalization-absorption-bands-pre-specified)) | Main (stress-test table) |
| DATP is not dominated by a matched benign-only federated summary-statistics threshold | `B-FedStatsBenign` matched-exceedance; between-ratio diagnostic | Regime A + D | CV(FPR); between_ratio | Comparator reduces dispersion vs B1 but less than B2, or result reported honestly | Main (comparator table) |

### Tier 5 — Mechanism Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| Cluster/family scope is a middle ground between global and local scope | B1/B3/B4/B2 comparison + within/across-cluster dispersion + cluster-stability (adjusted Rand) | Regime A (+ D where feasible) | CV(FPR), worst-client FPR, dispersion, stability | Cluster scope recovers part of B2's gain with lower per-client calibration demand, or result reported | Main |
| FPR concentration mechanism explains the P10 Macro-F1 tradeoff | Per-client benign+attack CDF overlays; Ennio Doorbell deep dive | Regime A | Per-client CDF, P10 F1 | Mechanism figure produced | Main |
| Heterogeneity severity predicts DATP benefit (association, not causation) | JS-divergence ↔ gain regression | Regime A/C | R², ρ | Reported with caveats; weak R² is a real result | Main |
| The fairness–sensitivity tradeoff is a quantified surface | Threshold-shift vs ΔFPR/ΔTPR scatter | Regime A | Δτ, ΔFPR, ΔTPR | All 9 devices, no filtering | Main |
| B4 clusters carry meaningful taxonomy-free structure | Cluster-feature ablation + cluster-to-device contingency table | Regime A | CV(FPR) per subset | Reported; instability reported if present | Main |

### Tier 6 — Boundary-Condition Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| Under near-homogeneous file-level pseudo-clients, no dispersion reduction is observed | CICIoT2023 file-level | Regime B-a | CV(FPR); pairwise JS | Null reported as applicability boundary only | Main |
| B2 degrades detection in low-separability clients | P10 Macro-F1; worst-client BA | Regime A | P10 F1 | Reported as honest negative | Main |
| Under small benign calibration windows, naive local thresholds degrade and shrinkage stabilizes | Calibration-size sweep + τ-shrink | Regime A | Threshold variance, worst-client FPR vs n | Graceful degradation vs naive collapse, or reported | Main |
| Device-aware thresholds under a chronological split behave per one of three pre-specified temporal outcomes | Edge-IIoTset chronological 55/15/10/20 (historical train / historical calibration / future recalibration / future evaluation); frozen vs one-shot recalibration | Regime D-temporal | Per-window CV(FPR); recovery ratio | One pre-specified outcome applied ([§ Temporal outcomes](#locked-temporal-outcome-interpretations)) | Main |

### Tier 7 — Exploratory Claims

| Claim | Evidence | Regime | Metric | Placement |
|---|---|---|---|---|
| B4 at K = 3 recovers ≈52% of B2's improvement without a taxonomy | Existing Regime A result | Regime A | B4 recovery % | Main (labeled exploratory at N = 9) |
| B4 behavior at other K is a granularity sensitivity, not a main claim | K sweep where feasible | Regime A/D | CV(FPR) | Supplement |
| Federated quantile-estimation error tracks threshold reliability across constructions | Quantile-estimation error, FPR-target attainment | Regime A | Estimation error, attainment | Supplement/backbone |

### Tier 8 — Future-Work Claims (Named, Not Executed)

Dynamic DATP (temporally adaptive per-client thresholds); Conformal DATP beyond the single B2-conf seed; formal privacy (DP/SecAgg); fleet-scale validation (K > 100); streaming drift mitigation; a standalone Model-vs-Threshold-Personalization 2×2 spin-off with full cost accounting; exhaustive personalized-FL and aggregation benchmarking. Each is named in Future Work and none is claimed as a result. See also [03 — Future Work](./03_EXPERIMENT_CATALOGUE.md#future-work-named).

### Tier 9 — Forbidden Claims

DATP "solves" non-IID FL; improved global Macro-F1; privacy preservation; concept-drift handling beyond one-shot recalibration; universal dominance over Laridi-style thresholding; fleet-scale validation; any "first"/"novel" language without independent verification; any dataset property (device IDs, timestamps, family counts) stated as verified fact without an artifact check; B4 fingerprints framed as a privacy mechanism.

---

## Research Questions

Each RQ is tagged by role. Only RQ1 is confirmatory; the rest are supportive, mechanism, stress-test, or external/boundary.

- **RQ1 (confirmatory).** Under a fixed FedAvg AE, does threshold-calibration scope (B1 shared vs B2 per-client) change per-client FPR disparity on the natural N-BaIoT physical-device split, and what TPR/Macro-F1 tradeoff does it impose?
- **RQ2 (mechanism).** Do cluster/family thresholds (B3, B4) recover part of the local-threshold benefit while improving the fairness-vs-sample-efficiency and stability tradeoff relative to both B1 and B2 — and why does clustering *thresholds* on a fixed model differ from clustering *models*?
- **RQ3 (supportive).** How robust are local thresholds under small benign calibration windows, and can local-global shrinkage (τ-shrink) and a calibration-size-aware fallback stabilize them without discarding personalization?
- **RQ4 (mechanism / backbone).** Framing thresholds as distributed quantile-estimation objects, do federated quantile/statistical comparators (`B-FedStatsBenign`, pooled/weighted quantiles) explain or challenge DATP's threshold-scope effect, and at what estimation error and FPR-target attainment?
- **RQ5 (stress test).** Does threshold-only personalization remain useful when compared against aggregation-side (FedProx) and model-side personalization stress tests — i.e., does model personalization absorb the threshold-scope gain?
- **RQ6 (external / boundary).** Does the threshold-scope effect generalize to an independent sensor-group-partitioned dataset (Edge-IIoTset), how does it behave across Dirichlet severity, and where does it fail (near-homogeneous file-level pseudo-clients; chronological drift)?

RQ1 maps to Tier 1. RQ2 → Tier 5 (with the exploratory B4-recovery claim in Tier 7). RQ3 → Tier 6 calibration-window claim + supportive variants. RQ4 → Tier 4 comparator claim + Tier 7 backbone. RQ5 → Tier 4. RQ6 → Tier 3 + Tier 2 (Regime C) + Tier 6 (boundaries).

---

## Statistical decision boundaries that determine claims

### Model-personalization absorption bands (pre-specified)

Pre-specified and applied without adjustment. Let Δ_FedAvg = CV(FPR)[FedAvg+B1] − CV(FPR)[FedAvg+B2] and Δ_pers = CV(FPR)[Pers+B1] − CV(FPR)[Pers+B2].

- Δ_pers ≥ 0.75·Δ_FedAvg → threshold personalization remains strongly useful under model personalization (corroborating).
- 0.25·Δ_FedAvg ≤ Δ_pers < 0.75·Δ_FedAvg → partial absorption (boundary condition).
- Δ_pers < 0.25·Δ_FedAvg → largely absorbed; DATP claim narrowed to FedAvg-style / shared-encoder settings, reported explicitly.
- If CV(FPR)[Pers+B1] is within 0.05 of CV(FPR)[FedAvg+B2] → model personalization is an alternative path to FPR equity; reported as an informative positive finding about the method, not a DATP failure.

Experiment: [E-T2 in 03](./03_EXPERIMENT_CATALOGUE.md#mandatory-supportive--mechanism--external--stress).

### Locked temporal-outcome interpretations

Outcome interpretations for the Edge-IIoTset chronological recalibration experiment. The experiment procedure and split are owned by [03 — Temporal recalibration experiment](./03_EXPERIMENT_CATALOGUE.md#temporal-recalibration-experiment); metric formulas by [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#temporal-recalibration-metrics).

- **Outcome A — drift exists, one-shot recalibration helps** (recovery ratio ≥ 50% of the original CV(FPR) gain). "Under the available temporal window, one-shot threshold recalibration recovers a meaningful portion of the CV(FPR) gain; periodic recalibration is a viable operational policy for device-aware thresholds."
- **Outcome B — drift exists, one-shot recalibration does not help** (recovery ratio < 50%). "Device-aware thresholds exhibit temporal fragility in this benchmark; one-shot recalibration is insufficient; continuous drift mitigation would be required (future work)." No streaming detector is added retroactively to rescue the result.
- **Outcome C — no meaningful drift** (FPR drift within the bootstrap CI of the static split). "Under the available chronological window, device-aware thresholds appear stable; this does not establish general temporal robustness but reduces concern that the DATP effect is a static-split artifact."

### Seed-extension honesty rule (affects claim status)

If the 10-seed extension widens the CI or brings it near zero, the 10-seed result becomes the main result and the 5-seed conference result is labeled preliminary. If the reproduced 5-seed CI differs materially from the reference [0.647, 0.769] — shifting toward zero or more than ~20% wider than the reference width (≈0.122, i.e. wider than ≈0.147) — expansion claims are blocked until resolved. The 10-seed result is never suppressed when less favorable. Enforced by [SB-21](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels); statistical structure in [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#statistical-requirements-locked).

---

## Anti-HARKing and non-suppression rules

- Null and mixed results remain reportable and are pre-committed to fallback wording (below).
- Pre-specification before observation; fallback wording locked; suppression rules explicit (see [04 — Statistical requirements](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#statistical-requirements-locked)).
- No supportive module may become a confirmatory claim; no hidden main claim in the supplement.
- The confirmatory experiment is never suppressed. Suppressed / rejected experiments are documented in [03 — Suppressed / Rejected](./03_EXPERIMENT_CATALOGUE.md#suppressed--rejected).
- No cherry-picked checkpoint, K, or calibration size (see [04 — Checkpoint protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#journal-checkpoint-protocol-locked)).

---

## Fallback Wording

Every major claim carries pre-committed wording for strong-positive, weak-positive, mixed, null, opposite, feasibility-rejection, and suppressed outcomes. Wording is selected only after result freeze and never softens a null.

### B1 vs B2 Confirmatory (Tier 1)

- **Strong positive.** "B2 reduces CV(FPR) from [B1] to [B2] (10-seed BCa CI [a, b], excluding zero); all seed deltas positive."
- **Weak positive.** "B2 reduces CV(FPR) with a 10-seed BCa CI [a, b] that excludes zero but is wide; the effect is directionally consistent though the magnitude is uncertain at this seed count."
- **Mixed.** "The reduction is present in most seeds; the BCa CI [a, b] excludes zero, but seed [x] shows attenuation attributable to [cause], reported as a stability caveat."
- **Null.** "At 10 seeds the BCa CI [a, b] includes zero; the confirmatory endpoint is not met at this power. We report the point estimate and the failure to exclude zero rather than the 5-seed result."
- **Opposite.** "B2 increases CV(FPR) relative to B1 in this regime (CI [a, b], positive lower bound in the opposite direction), which we report as an unexpected reversal and analyze in §Mechanism."
- **Feasibility rejection.** N/A for Regime A.
- **Suppressed.** N/A — the confirmatory experiment is never suppressed.

### B4 Cluster Recovery

- **Strong.** "B4 recovers ≈[x]% of B2's improvement at K = 3 without a taxonomy."
- **Weak/mixed.** "B4 partially recovers B2's improvement ([x]%), with recovery varying across seeds ([range]); B4 is exploratory at N = 9."
- **Null.** "B4 does not recover a meaningful fraction of B2's gain under this fingerprint; cluster-scope thresholds are not supported at this device count."

### Cluster Stability

- **Strong.** "Cluster assignments are stable across seeds (adjusted Rand [x])."
- **Weak/null.** "Cluster assignments are unstable across seeds (adjusted Rand [range]); B4 results are reported as exploratory and sensitive to initialization."

### Small Calibration Windows

- **Strong.** "As n_k falls, naive local thresholds show rising variance while shrinkage maintains worst-client FPR; personalization is retained down to n_k = [N*]."
- **Weak/null.** "Shrinkage does not stabilize thresholds below n_k = [N*]; the calibration-size-aware fallback reverts to B1-equivalent FPR, which we report as the operating floor."

### Shrinkage (τ-shrink)

- **Strong.** "τ-shrink interpolates B1↔B2 monotonically and mitigates the P10 Macro-F1 loss at intermediate λ."
- **Weak/null.** "τ-shrink shows non-monotone λ behavior / does not mitigate the P10 Macro-F1 loss; we report the λ-curve as-is without selecting a favorable λ."

### Federated Quantiles (Backbone)

- **Positive.** "Framing B1/B1-pool/B1-wt/`B-FedStatsBenign` as quantile estimators clarifies their estimation error and FPR-target attainment; no novel estimator is claimed."
- **Null/limitation.** "Approximate federated quantile estimation does not improve FPR-target attainment over the local baseline here; the backbone remains a reproducibility and comparability device, not a contribution."

### Model-Personalization Stress Test

Wording follows the four absorption bands ([§ Absorption bands](#model-personalization-absorption-bands-pre-specified)) verbatim; all four are valid findings and none is hidden.

### FedProx Stress Test

- **Survives.** "The B1→B2 CV(FPR) gain persists under FedProx aggregation across the frozen µ-grid; the threshold-scope effect is not an artifact of vanilla FedAvg."
- **Convergence failure.** "All pre-specified µ values fail to converge on Regime [x]; we report the convergence failure and add no post-hoc µ. Any µ introduced after seeing results is labeled exploratory and cannot support the stress-test claim."

### Edge-IIoTset External Validation

- **Consistent (external validation, non-confirmatory).** "On Edge-IIoTset ([partition], K = [x]), B2 reduces CV(FPR) from [Y] to [Z] (95% BCa CI [a, b]), consistent with Regime A; this is external-validation (Tier 3) evidence, not a second confirmatory endpoint — the sole confirmatory claim remains Regime A B1-vs-B2 ([Locked claim](#locked-main-journal-claim), [Tier 1](#tier-1--locked-confirmatory-claim))."
- **Mixed/null.** "On Edge-IIoTset the effect is [attenuated/absent]; we report this as an external boundary rather than as confirmation, and discuss partition/heterogeneity differences."
- **Feasibility rejection.** "Edge-IIoTset did not meet the eligibility-coverage threshold (n_k ≥ 100 for ≥ 90% of clients); we reduce K / defer the temporal MVE and document the reason."

### CICIoT2023 Boundary

- **Boundary (expected).** "Under the file-level near-homogeneous partition, no dispersion reduction is observed; this is an applicability boundary, not a general CICIoT2023 statement."
- **B-b feasibility rejection.** "CICIoT2023 B-b was infeasible on the available CSV artifact because MAC/device/IP/capture-source/timestamp metadata are absent; reprocessing from PCAPs is out of scope."
