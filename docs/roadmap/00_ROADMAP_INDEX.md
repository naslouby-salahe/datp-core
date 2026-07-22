# 00 — Roadmap Index

**Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*

**Purpose of this package.** This directory is the active DATP-Core roadmap. [`SCIENTIFIC_SOURCE_OF_TRUTH.md`](./SCIENTIFIC_SOURCE_OF_TRUTH.md) is the canonical authority for every locked scientific fact, formula, value, boundary, and decision rule; this file and files 01–06 own explanation, planning, experiment organization, reporting, and implementation sequencing, and defer to the source of truth for canonical values rather than restating them. Where a detail is owned by one file, other files link to it rather than duplicating it.

---

## Executive summary

**DATP identity.** DATP is a fixed-encoder, fixed-federated-model, threshold-calibration-scope study. A shared FedAvg autoencoder is trained once per seed and then frozen; only the *scope* at which the anomaly threshold is calibrated changes across the policy ladder B1 (shared), B2 (per-client), B3 (family), B4 (cluster). Calibration is benign-only. The causal question is whether threshold-calibration scope changes deployed operating-point reliability — specifically per-client false-positive-rate (FPR) dispersion — across heterogeneous IoT clients. AUROC is a model-quality control, never the thresholding verdict.

**Extension strategy.** The journal extension strengthens DATP along five disciplined axes — one external dataset (Edge-IIoTset, Regime D), a matched federated-threshold comparator (`B-FedStatsBenign`) plus Laridi disclosure, two training-side stress tests (FedProx, one model-personalization comparator), four threshold variants (q-sensitivity, τ-shrink, calibration-size-aware fallback, split-conformal B2-conf), and one temporal-recalibration experiment — without turning DATP into a generic FL-IDS benchmark. The confirmatory endpoint is unchanged and remains the sole locked claim. Full scope: [01 — Included scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#included-scope).

**Main claim (locked).** DATP's threshold-scope effect remains observable under a stronger journal protocol while preserving the fixed-encoder threshold-calibration identity. The sole confirmatory endpoint is Regime A, B1 vs B2, CV(FPR), 10 paired seeds, 95% BCa CI excluding zero (positive). See [02 — Locked main journal claim](./02_CLAIMS_AND_DECISION_RULES.md#locked-main-journal-claim).

---

## Current status

- **Scientific status.** Identity intact (fixed encoder, threshold-scope-only causal ladder, benign-only calibration, CV(FPR) primary, AUROC control). Confirmatory endpoint singular and locked with a hard survival rule.
- **Execution status.** **GO — with two conditional gates.** Stored-score work on Regime A/C can start immediately; two feasibility gates apply (CICIoT2023 feature-count re-verification before print; Edge-IIoTset eligibility coverage before the Tier 3 claim). Full decision: [07 — Go / No-Go](./07_AUDIT_AND_DECISION_LOG.md#go--no-go--conditional-go-summary).

---

## Navigation table

| File | Canonical responsibility | Main contents | When to consult it |
|---|---|---|---|
| [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) | Stable scientific boundaries | Identity & invariants, fairness definition, nomenclature & naming locks, scope in/out, originality plan, SB-01–SB-32 | To confirm what is locked, what is in/out of scope, or a policy/comparator name |
| [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md) | The claim system | Locked claim & endpoint, nine claim tiers, RQs, absorption bands, temporal outcomes, seed-honesty rule, fallback wording | To find a claim, its pass condition, or how a result outcome is interpreted |
| [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md) | Every experiment & relationship | Regime table, module integration, experiment matrix (E-*), suppressed/rejected, execution ordering, temporal procedure | To find an experiment, its inputs/deps, or its evidentiary role |
| [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md) | Metrics, statistics, reporting | Metric definitions, statistical plan, BCa/seed structure, checkpoint protocol, tables/figures/placement, manuscript mapping | To find a metric definition, a statistical requirement, or a reporting rule |
| [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md) | Implementation requirements | Scratch boundary, execution phases, stored-score vs retraining, preserved semantics, `B-FedStatsBenign` contract, determinism | To find what must be implemented and in what order |
| [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md) | Reviewer defence & readiness | Reviewer register L01–L28, residual risks, five checklists, submission-readiness conditions | To find a reviewer objection's defence or a readiness gate |
| [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md) | Audits & decisions | Source audits 1–7, go/no-go, what-changed record, split-verification | To find an audit conclusion, a go/no-go decision, or the split verification |

---

## Canonical ownership and precedence rules

- Every substantive requirement has exactly **one canonical owner file**. Other files provide a concise statement and a relative link; they never duplicate the full table, checklist, protocol, or rule.
- Subjects that span files are split as: experiment definition → [03](./03_EXPERIMENT_CATALOGUE.md); statistics & reporting → [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md); claim consequence & fallback → [02](./02_CLAIMS_AND_DECISION_RULES.md); implementation dependency → [05](./05_IMPLEMENTATION_ROADMAP.md); reviewer objection & defence → [06](./06_REVIEWER_RISKS_AND_READINESS.md).
- **Precedence.** If any package file appears to disagree with [`../Journal_Extension_Master_Roadmap.md`](../Journal_Extension_Master_Roadmap.md), the master roadmap governs. Known source-internal contradictions are flagged, not resolved, in [07 — Source-roadmap contradictions](./07_AUDIT_AND_DECISION_LOG.md#source-roadmap-contradictions-flagged).

---

## Immediate-start work, dependencies, and go status

- **Immediate-start (no dependency).** Stored-score extensions: E-C1 (10-seed confirmatory), E-S1/S2/S3, E-M1–M5, E-V1/V2/V3, E-T3, E-O1, plus Appendix A. See [05 — Execution phases](./05_IMPLEMENTATION_ROADMAP.md#execution-phases-and-dependency-order).
- **Major dependencies.** Edge-IIoTset external validation (E-X1) and temporal MVE (E-B1) need Regime D preprocessing/training and eligibility coverage; FedProx (E-T1) and model-personalization (E-T2) need trained encoders. See the `Blocking deps` column in [03 — Experiment Matrix](./03_EXPERIMENT_CATALOGUE.md#experiment-matrix).
- **Go / conditional-go status.** GO with two conditional gates — [07 — Go / No-Go](./07_AUDIT_AND_DECISION_LOG.md#go--no-go--conditional-go-summary).

---

## How to find things

- **A claim, its pass condition, or its fallback wording** → [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md).
- **An experiment (E-*), its inputs, prerequisites, or evidentiary role** → [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- **A metric definition, statistical requirement, or reporting/placement rule** → [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md).
- **An implementation requirement, execution phase, or the `B-FedStatsBenign` contract** → [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md).
- **A reviewer risk and its defence, or a readiness checklist** → [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md).
- **An audit conclusion, go/no-go decision, or the split verification** → [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md).
- **What is locked, in/out of scope, or a comparator name** → [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md).
