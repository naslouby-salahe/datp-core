# 06 — Reviewer Risks and Readiness

**Purpose.** Own reviewer defence and readiness: the complete reviewer-objection register with testable defences, the highest residual risks, the identity/experiment/claim/module/manuscript readiness checklists, and the submission-readiness conditions. This file consolidates *what a reviewer might attack and whether the program is ready to answer*.

**What this file owns.**
- The complete reviewer-objection register (L01–L28) with testable defence or locked wording.
- Novelty/overlap, Laridi positioning, tautology, model-personalization absorption, dataset/client-partition, privacy/deployment/security/fairness-framing risks.
- Risk severity and residual risks (highest residual risks and their handling).
- Core-identity, experiment-readiness, module-integration, claim-discipline, and manuscript-readiness checklists.
- Submission-readiness conditions and blocking/non-blocking residual risks.

**What this file does not own.**
- The formal claim tiers, fallback wording, and decision rules → see [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md).
- Experiment definitions the defences point to → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- Go/No-Go decisions and feasibility gates → see [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md).
- Scientific identity, nomenclature, and scope boundaries → see [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md).

> **Status note.** The checklists below reproduce the source roadmap's unchecked (☐) state. Splitting the roadmap into a package does **not** mark any checklist item complete.

**Related files.** [00 — Index](./00_ROADMAP_INDEX.md) · [01 — Identity](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) · [02 — Claims](./02_CLAIMS_AND_DECISION_RULES.md) · [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md)

---

## Risk summary

The dominant residual risk is model-personalization *absorption* — whether the threshold-scope gain survives when the model itself is personalized — handled by a pre-specified absorption rule with all outcomes reportable. The second risk is novelty collapse against Laridi et al. (2024), handled by a matched-exceedance benign-only comparator plus an explicit disclosure that the anomaly-labeled Laridi-faithful setting is out of DATP's benign-only contract. Secondary risks are modest client count (K ∈ [9, 15]), single temporal split, qualitative-only privacy framing, and possible CI widening under the 10-seed extension. All are scoped explicitly with pre-committed wording.

---

## Reviewer Loophole Register

Each row: the reviewer attack, why it is dangerous, the roadmap defense, the required experiment or wording, and a status checkbox. Defenses are testable; none is hand-waved.

| # | Reviewer attack | Why dangerous | Roadmap defense | Required experiment / wording | Status |
|---|---|---|---|---|---|
| L01 | "Thresholding is trivial post-processing" | Dismisses the whole contribution | Freeze the encoder; show scope changes per-client FPR at near-constant AUROC | E-C1 + AUROC control reported | ☐ |
| L02 | "Laridi already does federated thresholding" | Novelty collapse | Delta is benign-only + operating-point equity; matched-exceedance comparator; explicit faithful/benign-only split | E-T3 + `B-LaridiFaithful` out-of-scope disclosure | ☐ |
| L03 | "Local thresholds just overfit benign calibration" | Undercuts B2 | Held-out test measurement; calibration-size sweep; conformal coverage | E-C1 (test), E-V1, E-V3 | ☐ |
| L04 | "B2 works only because it controls FPR by construction" | Tautology | Appendix A: equality exact on cal data only; empirical test-FPR variance is what is measured; B2-conf finite-sample coverage | Appendix A + E-V3 + wording ([02](./02_CLAIMS_AND_DECISION_RULES.md#b1-vs-b2-confirmatory-tier-1)) | ☐ |
| L05 | "CV(FPR) is not enough" | Metric fragility | Report IQR, max−min, worst-client FPR, alert burden, equity suite | E-S1, E-O1, E-Q3 | ☐ |
| L06 | "Cluster thresholds are just known clustering" | Novelty of module | Contribution is threshold-scope clustering on a *fixed* federated detector; outcome is operational FPR equity; contrast Sáez-de-Cámara (clusters models) | E-M1 + related work | ☐ |
| L07 | "Family labels are arbitrary" | Undermines B3 | B3 reported precisely as underperforming because taxonomy ≠ calibration structure; motivates B4 | Existing B3 result + wording | ☐ |
| L08 | "B4 K was tuned after seeing results" | HARKing | K = 3 canonical pre-committed; silhouette instability documented; other K exploratory/supplementary | SB-K lock + E-M1 | ☐ |
| L09 | "Small calibration windows make B2 unrealistic" | External validity | Calibration-size sweep + shrinkage + calibration-size-aware fallback; argue small/contaminated windows are real | E-V1, E-V2 | ☐ |
| L10 | "Shrinkage is textbook" | Novelty of module | No new statistical theory claimed; contribution is testing calibration robustness in FL-IoT thresholding | E-V2 wording | ☐ |
| L11 | "Federated quantiles are not novel" | Overclaim risk | Positioned explicitly as backbone/primitive; no novel-estimator claim | E-Q1 wording | ☐ |
| L12 | "Model personalization makes threshold personalization obsolete" | Strongest objection | Absorption ratio with pre-specified bands; all outcomes reportable | E-T2 + [02 — Absorption bands](./02_CLAIMS_AND_DECISION_RULES.md#model-personalization-absorption-bands-pre-specified) | ☐ |
| L13 | "FedProx/Ditto/FedRep/FedPer are unfairly implemented" | Comparator fairness | µ-grid and E locked equal to FedAvg; Ditto choice documented before training; fallback named honestly | E-T1, E-T2 + G-notes | ☐ |
| L14 | "CICIoT2023 pseudo-clients are not real clients" | Dataset validity | Reported as Regime B-a boundary only; B-b rejected on metadata grounds | E-R1 + wording ([02](./02_CLAIMS_AND_DECISION_RULES.md#ciciot2023-boundary)) | ☐ |
| L15 | "Edge-IIoTset client mapping is ambiguous" | External-validity ceiling | Partition decided by first-principles feasibility audit; documented before training | E-X1 preprocessing audit | ☐ |
| L16 | "External validation failed or is mixed" | Honesty test | Pre-committed mixed/null wording; reported as boundary | [02 — Edge-IIoTset external validation](./02_CLAIMS_AND_DECISION_RULES.md#edge-iiotset-external-validation) | ☐ |
| L17 | "AUROC did not improve" | Misreads the paper | AUROC is a control, not the verdict; stated explicitly | Identity statement + wording | ☐ |
| L18 | "Macro-F1 tradeoff is hidden" | Integrity | P10 Macro-F1 degradation reported as honest negative; Ennio deep dive | E-M3 + Tier 6 claim | ☐ |
| L19 | "False-positive fairness is not human fairness" | Framing | "Fairness" defined once as operational/service-level FPR equity | Locked definition ([01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#fairness-definition-locked)) | ☐ |
| L20 | "No privacy guarantee" | Scope | Qualitative bounded-disclosure only; B4 explicitly not a privacy mechanism; DP/SecAgg future work | Privacy disclosure table | ☐ |
| L21 | "No deployment measurement" | Scope | Communication/storage estimated from message sizes; no hardware claim | E-Q6 + wording | ☐ |
| L22 | "No poisoning/evasion/backdoor analysis" | Scope | Explicitly out of scope; named future work (DATP-CP is a separate paper) | SB list | ☐ |
| L23 | "Too many experiments create HARKing" | Integrity | Pre-specification before observation; fallback wording locked; suppression rules explicit | [04 — Statistical requirements](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#statistical-requirements-locked) + [02 — Fallback Wording](./02_CLAIMS_AND_DECISION_RULES.md#fallback-wording) | ☐ |
| L24 | "Conference-to-journal overlap is too high" | Desk reject | ≥ 40% substantive new material (self-imposed benchmark); cover-letter enumeration; figures redrawn | [01 — Originality plan](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#conference-to-journal-originality-plan) | ☐ |
| L25 | "The journal extension is too broad" | Scope creep | Hard limits: 1 new dataset, 3 stress-test families, 4 threshold variants, 1 temporal family, 6 mechanism analyses | Scope boundaries ([01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#scope-boundaries-stable-labels)) | ☐ |
| L26 | "The journal extension is too narrow" | Editor judgment | Framed as a fairness-oriented threshold-calibration study with external + stress + mechanism evidence | Executive summary framing | ☐ |
| L27 | "The code was inherited and messy" | Reproducibility | New codebase written from scratch; reference project used only for DATP semantics | [05 — Scratch boundary](./05_IMPLEMENTATION_ROADMAP.md#scratch-implementation-boundary-and-behavioral-reference) | ☐ |
| L28 | "Scratch codebase means reproducibility must be specified cleanly" | Reproducibility | Deterministic seeds, reproducible manifests, testable threshold-policy contracts, traceable tables/figures | [05 — Implementation-clarity checklist](./05_IMPLEMENTATION_ROADMAP.md#implementation-clarity-checklist) | ☐ |

**Highest residual risks.** L12 (model-personalization absorption) and L02 (Laridi novelty) remain the two highest residual risks; both have pre-specified interpretation rules that keep all outcomes reportable. Neither can invalidate the confirmatory claim.

---

## Checklists

### Core Identity Checklist
- ☐ Encoder/AE fixed for the core B1–B4 ladder (same final state, seeds, score artifacts).
- ☐ Threshold-calibration scope is the sole causal variable.
- ☐ Calibration is benign-only; attack data evaluation-only.
- ☐ CV(FPR) is the primary metric everywhere.
- ☐ AUROC is a control metric, never the thresholding verdict.
- ☐ FedProx, model personalization, and Laridi-style comparators are outside the causal ladder.
- ☐ No privacy / deployment / security / drift overclaim anywhere.
- ☐ "Fairness" means operational FPR equity, stated once.

### Experiment Readiness Checklist
- ☐ Dataset feasibility verified (N-BaIoT, Edge-IIoTset coverage; CICIoT2023 B-b rejection recorded).
- ☐ Client identity verified per regime before training.
- ☐ Calibration/test split semantics verified (benign-only calibration; gapped chronological splits where used).
- ☐ Checkpoint protocol fixed before results (train-once, save-many, Regime-A global selection).
- ☐ Seeds fixed (10 for confirmatory).
- ☐ Metrics fixed before results.
- ☐ Suppression and fallback rules fixed before results.
- ☐ Any reused score cells verified by full lineage (schema, split identity, client IDs, checkpoint hashes, metric tolerance) or rejected.
- ☐ Scratch implementation does not rely on the reference project's layout.
- ☐ `/home/naslouby/Projects/datp` used only as a behavioral reference for DATP semantics.

### Module Integration Checklist
- ☐ Cluster/Family module integrated as core mechanism (Tier 5), not confirmatory.
- ☐ Small-window/shrinkage module integrated as supportive variant.
- ☐ Federated-quantile module integrated as backbone/primitive, no novelty overclaim.
- ☐ Model-vs-threshold module integrated as external stress test; spin-off marked future work.
- ☐ No module hijacks the confirmatory claim.
- ☐ Optional/spin-off decisions are explicit for every module.

### Claim Discipline Checklist
- ☐ Every claim has an evidence requirement and a regime/metric.
- ☐ Every weak/mixed/null outcome has pre-committed fallback wording.
- ☐ No unsupported novelty language; no "first" without independent verification.
- ☐ No hidden main claim in the supplement.
- ☐ No cherry-picked checkpoint, K, or calibration size.
- ☐ No hidden failed experiment; suppressed items are documented in [03 — Suppressed / Rejected](./03_EXPERIMENT_CATALOGUE.md#suppressed--rejected).

### Manuscript Readiness Checklist
- ☐ Results written before the abstract; prose order Results → Methods → Discussion → Limitations → Related Work → Abstract → Conclusion → Supplement → cover letter.
- ☐ Methods match the executed experiments exactly.
- ☐ Limitations explicit (K, seeds, temporal, privacy, Laridi adaptation, CI width).
- ☐ Related work addresses Laridi (2024) and model personalization directly.
- ☐ Discussion separates success, boundary, and failure.
- ☐ Supplement holds exploratory material; main paper stays readable and focused.

---

## Submission-readiness conditions and residual risks

- **Blocking for print (non-blocking for start).** Re-verify the actual processed CICIoT2023 feature count before any quantitative CICIoT2023 statement (conference value d = 39; mirror distributions differ). Recorded as a feasibility gate in [07 — Go / No-Go](./07_AUDIT_AND_DECISION_LOG.md#go--no-go--conditional-go-summary).
- **Blocking for the Tier 3 claim only.** The Edge-IIoTset external-validation claim proceeds only if eligibility coverage is met (n_k ≥ 100 for ≥ 90% of clients) and the partition is assigned by the first-principles feasibility audit; otherwise reduce K or defer per the locked wording.
- **Accepted residual risks (non-blocking, pre-specified handling).** Model-personalization absorption (E-T2, four bands, all reportable) and Laridi novelty (E-T3 matched-exceedance benign-only + `B-LaridiFaithful` out-of-scope disclosure); modest client count (K ∈ [9, 15]); single temporal split; qualitative-only privacy framing; possible CI widening under the 10-seed extension. None can invalidate the confirmatory claim.
