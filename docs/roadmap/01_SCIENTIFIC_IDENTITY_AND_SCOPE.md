# 01 — Scientific Identity and Scope

**Purpose.** Define the stable, locked scientific boundaries of the DATP journal extension: what DATP *is*, what is invariant, what is in and out of scope, and the canonical nomenclature and naming locks. Everything here is intended to be stable across every experiment, claim, table, figure, and manuscript section.

**What this file owns.**
- DATP scientific identity and non-negotiable invariants.
- Fixed-model / threshold-calibration causal isolation.
- Benign-only calibration rule and the locked meaning of operational FPR equity ("fairness").
- Core threshold-policy and comparator nomenclature, plus the naming locks.
- Included scope, excluded scope, and forbidden interpretations / overclaims (scope level).
- Core-ladder versus external stress-test distinction.
- Conference-to-journal extension boundary and reuse / redraw / originality constraints.
- The stable scope-boundary register (SB-01 – SB-32) and venue constraints.

**What this file does not own.**
- The tiered claim system, confirmatory endpoint, and forbidden *claims* list → see [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md).
- Experiment definitions, regimes, and the module integration table → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md).
- Metrics, statistics, and reporting → see [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md).
- Rejected / suppressed experiments and named future work → see [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md#suppressed--rejected) and [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md#tier-8--future-work-claims-named-not-executed).

**Related files.** [00 — Index](./00_ROADMAP_INDEX.md) · [02 — Claims](./02_CLAIMS_AND_DECISION_RULES.md) · [03 — Experiments](./03_EXPERIMENT_CATALOGUE.md) · [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md)

---

## Working title and venue

**Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*

**Primary venue:** Computer Networks (Elsevier). **Backup:** Internet of Things (Elsevier). **Excluded:** Computers & Security (standing AI/ML + federated-learning scope moratorium).

**Scientific reference project (behavioral reference only):** `/home/naslouby/Projects/datp` — used solely to recover the original DATP threshold-policy logic, experiment semantics, score-artifact behavior, and result interpretation. The journal-extension implementation is written from scratch; nothing in this roadmap implies reuse of that project's source layout, backward compatibility, shims, redirects, or migration. See [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md).

---

## DATP scientific identity

DATP is a **fixed-encoder, fixed-federated-model, threshold-calibration-scope study**. A shared FedAvg autoencoder is trained once per seed and then frozen; only the *scope* at which the anomaly threshold is calibrated changes across the policy ladder B1 (shared), B2 (per-client), B3 (family), B4 (cluster). Calibration is benign-only. The causal question is not "which model is best?" but whether threshold-calibration scope changes deployed operating-point reliability — specifically per-client false-positive-rate (FPR) dispersion — across heterogeneous IoT clients. AUROC is a model-quality control, never the thresholding verdict.

---

## Non-Negotiable Scientific Identity (Locked)

The following identity is preserved verbatim across every section, table, figure, and claim in this roadmap and in the manuscript it guides.

- The trained autoencoder / encoder is **fixed** for the core DATP ladder. The same final AE state, seeds, and per-client score artifacts are reused across B1–B4 without retraining.
- **FedAvg** remains the main training baseline for the core causal ladder (E=1, full participation, as in the reference project).
- **Threshold-calibration scope is the sole experimental variable** in the causal ladder.
- **Calibration is benign-only.** Attack data are reserved for evaluation and never used to fit or tune thresholds.
- The primary operating-point concern is **per-client FPR disparity**, not global F1, AUROC, or accuracy.
- **AUROC is a model-quality sanity/control metric**, not the primary thresholding verdict.
- The journal extension strengthens DATP but must **not** turn it into a generic FL-IDS benchmark paper.
- **Stress-test comparators (FedProx, model personalization, Laridi-style) remain outside the causal threshold-scope ladder** and are never presented as sharing its experimental control.
- Dynamic DATP, poisoning, privacy guarantees, deployment profiling, backdoor, evasion, and full drift detection are **out of scope**; any mention is explicitly marked future work or spin-off.

### "Fairness" definition (locked)

Every use of "fairness" in this program means **operational / service-level FPR equity** — the evenness of false-alarm burden across client devices. It never refers to protected-attribute or human fairness. This is stated once in the manuscript and enforced throughout.

---

## Threshold-Policy and Comparator Nomenclature (Locked)

| Identifier | Meaning | Role |
|---|---|---|
| B0 | Centralized AE reference (pooled benign, pooled p95) | Privacy-incompatible reference; **not** in the FL causal ladder |
| B1 | Client-averaged shared τ (arithmetic mean of local p95) | Core ladder (shared-scope anchor) |
| B2 | Per-client p95 threshold | Core ladder (local-scope anchor); confirmatory comparator |
| B3 | Family-mean threshold (Regime A only; requires taxonomy) | Core ladder (mechanism baseline) |
| B4 | k-means cluster-mean threshold on a 4-scalar fingerprint [µ_e, σ_e, skew_e, p95(e)] | Core ladder (cluster mechanism); **K = 3 canonical**, K = 9 and other K exploratory only |
| τ-shrink (LGS) | Local-global shrinkage τ_k(λ) = λ·τ_k,p95 + (1−λ)·τ_global | Supportive threshold variant |
| Calibration-size-aware fallback | Size-dependent λ(n_k) replacing the hard n_min = 100 fallback | Supportive threshold variant |
| B2-conf | Split/federated-conformal variant of B2 at marginal coverage 1−α, α = 1−q | Supportive threshold variant (closes tautology critique) |
| `B-FedStatsBenign` | DATP-compatible **benign-only** federated summary-statistics threshold, matched-exceedance operating point | Comparator primitive / matched threshold comparator |
| `B-LaridiFaithful` | Relaxed Laridi reproduction using normal **and** anomalous validation summaries | **Out of scope** (violates benign-only contract); named disclosure only |
| FedProx | Heterogeneity-aware aggregation encoder | External stress test (not core ladder) |
| Ditto | Personalized local AE regularized toward the global model (proximal µ) | External stress test (not core ladder) |
| `FedRep-AE` / `FedPer-AE` fallback | Recognized shared-representation / local-head personalization family adapted to the DATP AE | External stress test; **never called "Ditto"** |

**Naming locks.** `B-FedStatsBenign` / `B-LaridiFaithful` replace any prior `B5` label. `τ-shrink` / LGS replace any prior `B3-LGS` label (B3 is family-mean and must not be reused). The model-personalization fallback is never labeled "Ditto" unless the true Ditto algorithm is implemented. B4 canonical K = 3; K = 9 is exploratory.

> The evidentiary *role* each policy plays in claims and experiments is elaborated in [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md#claim-hierarchy) and [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md#module-integration-table).

---

## Core ladder versus external stress-test distinction

The **core causal ladder** is B1–B4 on the fixed FedAvg autoencoder, where threshold-calibration scope is the sole experimental variable. Stress-test comparators — **FedProx** (aggregation), one **model-personalization** comparator, and the **Laridi-style** benign-only comparator — sit **outside** the causal ladder and are never presented as sharing its experimental control. This distinction is enforced by [SB-25](#scope-boundaries-stable-labels) and appears in the claim tiers ([02 — Tier 4](./02_CLAIMS_AND_DECISION_RULES.md#tier-4--stress-test-claims-outside-causal-ladder)).

---

## Included scope

The extension strengthens DATP along five disciplined axes without dissolving it into a generic FL-IDS benchmark:

1. One new sensor-group-partitioned external dataset (Edge-IIoTset, Regime D).
2. A matched-operating-point federated-threshold comparator (`B-FedStatsBenign`) plus explicit Laridi scope disclosure.
3. Two training-side stress tests outside the causal ladder (FedProx aggregation, one model-personalization comparator).
4. Four threshold variants that deepen the calibration story (q-sensitivity, local-global shrinkage, calibration-size-aware fallback, split-conformal B2-conf).
5. One chronological-split temporal-recalibration experiment.

Six mechanism analyses and Appendix A support these. The confirmatory endpoint is unchanged and remains the sole locked claim (see [02 — Sole confirmatory endpoint](./02_CLAIMS_AND_DECISION_RULES.md#sole-confirmatory-endpoint)). The full experiment catalogue lives in [03](./03_EXPERIMENT_CATALOGUE.md).

**The four newly integrated modules** (roles fixed here; details in [03 — Module Integration Table](./03_EXPERIMENT_CATALOGUE.md#module-integration-table)):
- **Cluster/Family Thresholding** — core journal mechanism module (granularity-and-stability analysis of threshold scope on a fixed detector).
- **Small-Calibration-Set / Few-Shot Thresholds** — supportive threshold-variant module (calibration-size ablation plus local-global shrinkage).
- **Federated Quantile Thresholding** — methods backbone / comparator primitive (a principled, auditable quantile-estimation vocabulary).
- **Model vs Threshold Personalization** — external stress-test / reviewer-objection module (and a possible future spin-off), keeping model personalization strictly outside the B1–B4 causal ladder.

---

## Excluded scope and forbidden interpretations (scope level)

**What the journal extension does NOT claim.** It does not claim to solve non-IID FL, to improve global Macro-F1, to preserve privacy, to handle concept drift beyond one-shot recalibration, to validate at fleet scale (K > 100), or to establish a universally dominant federated thresholding policy.

Dynamic DATP, poisoning, privacy guarantees, deployment profiling, backdoor, evasion, and full drift detection are **out of scope**; any mention is explicitly marked future work or spin-off.

> The formal, enumerated **forbidden-claims** list (Tier 9) is owned by [02 — Tier 9 Forbidden Claims](./02_CLAIMS_AND_DECISION_RULES.md#tier-9--forbidden-claims). Rejected and suppressed **experiments** are owned by [03 — Suppressed / Rejected](./03_EXPERIMENT_CATALOGUE.md#suppressed--rejected). Named **future-work** claims are owned by [02 — Tier 8](./02_CLAIMS_AND_DECISION_RULES.md#tier-8--future-work-claims-named-not-executed) and [03 — Future Work](./03_EXPERIMENT_CATALOGUE.md#future-work-named).

---

## Conference-to-Journal Originality Plan

**Reused (verbatim allowed).** DATP nomenclature and B1–B4 taxonomy; the Regime A confirmatory result (extended to 10 seeds); the Regime C Dirichlet sweep; the B0 centralized reference; theoretical definitions and notation.

**New (journal only).** Edge-IIoTset external-validation regime (D); the CICIoT2023 B-b formal rejection note; three stress-test comparator families crossed with B1–B4; four threshold variants; the chronological-split + one-shot recalibration regime; six mechanism analyses; Appendix A; expanded post-2022 related work; the four integrated modules' analyses.

**Redrawn.** Every figure is redrawn with additional series or replaced; every table extended; any section with > 50% reused prose is rewritten.

**Novelty threshold.** ≥ 40% substantive new material as a self-imposed conservative benchmark aligned with explicit Elsevier-family extension guidance (e.g. FGCS), **not** a Computer Networks requirement. Computer Networks' guide states only that enhanced, extended conference versions may be submitted; no fixed percentage is prescribed. The cover letter enumerates each new section, states no verbatim reuse of figures/text, waits for the conference camera-ready, and cites the conference paper.

---

## Scope Boundaries (Stable Labels)

- **SB-01.** Do not submit to Computers & Security (standing AI/ML + FL scope moratorium).
- **SB-02.** Do not add FedBN (encoder has no BatchNorm; adding it breaks the fixed-encoder identity).
- **SB-03.** Do not add more than one new IoT dataset (Edge-IIoTset).
- **SB-04.** Do not add more than three stress-test comparator families (FedProx; one model-personalization; one benign-only Laridi-style).
- **SB-05.** Do not claim DATP "solves" non-IID FL.
- **SB-06.** Do not claim improved global Macro-F1; P10 Macro-F1 degradation is a reported negative.
- **SB-07.** Do not claim privacy preservation without formal DP/SecAgg.
- **SB-08.** Do not claim concept-drift handling; the temporal probe is one-shot recalibration only.
- **SB-09.** Do not add adversarial robustness, poisoning, backdoor, or evasion experiments.
- **SB-10.** Do not add hardware or edge profiling.
- **SB-11.** Do not add streaming drift-detection frameworks.
- **SB-12.** Do not add Byzantine-robust federated conformal prediction.
- **SB-13.** Do not change the mainline AE architecture, FedAvg aggregator, or round budget within a dataset ladder; input_dim is matched per dataset; the fixed-encoder constraint applies within each dataset/regime/baseline ladder, not across datasets.
- **SB-14.** Do not reuse conference figures verbatim.
- **SB-15.** Do not silently change the CV(FPR) definition.
- **SB-16.** Do not generalize the CICIoT2023 file-level null; it stays Regime B-a.
- **SB-17.** Do not cite FedMSE (COSE 2025) as evidence COSE accepts FL today.
- **SB-18.** Do not target FGCS as a primary venue.
- **SB-19.** Do not use a Sankey diagram for B4 interpretability at K = 3/9; use a contingency table or small heatmap.
- **SB-20.** Do not present hypothetical alert/day numbers as measurements; use a real/cited rate or omit the metric.
- **SB-21.** Do not suppress the 10-seed result when less favorable; apply the CI-discrepancy rule.
- **SB-22.** Do not tune the `B-FedStatsBenign` protocol after seeing results; it is locked before computation.
- **SB-23.** Do not claim Regime B-b under any `B_B_REJECTED_*` status; do not collapse MAC-based and group-based partitions into one label.
- **SB-24.** Do not call the model-personalization fallback "Ditto"; use `FedRep-AE`/`FedPer-AE`, clearly labeled.
- **SB-25.** Do not present FedProx / model-personalization / Laridi-style results as part of the core B1–B4 causal ladder.
- **SB-26.** Do not use the simple pooled-variance formula for `B-FedStatsBenign`; use the full pooled variance including the between-client mean-shift term.
- **SB-27.** Do not use any fixed k as the primary `B-FedStatsBenign` comparator; the main comparison is the matched-exceedance operating point; fixed-k is supplementary.
- **SB-28.** Do not appeal to any unverified precedent to justify a dataset partition; partitioning is decided by first-principles feasibility audits.
- **SB-29.** Do not call a benign-only Laridi adaptation "faithful"; `B-LaridiFaithful` is reserved for the anomaly-labeled variant only.
- **SB-30.** Do not claim fleet-scale validation (K > 100).
- **SB-31.** Do not use Plassier et al. as the primary federated-conformal anchor; primary anchor is Lu et al. (ICML 2023), co-anchor Humbert et al. (ICML 2023).
- **SB-32.** Do not lock B4 K post-hoc; canonical K = 3; K = 9 and other K are exploratory/supplementary.

---

## Explicitly rejected future-work / spin-off topics

The following are named as future work or spin-offs and are **never** claimed as results of this paper: Dynamic DATP; Conformal DATP beyond the single B2-conf seed; formal privacy (DP/SecAgg); fleet-scale validation (K > 100); streaming drift mitigation; a standalone Model-vs-Threshold-Personalization 2×2 spin-off with full cost accounting; exhaustive personalized-FL and aggregation benchmarking. See [02 — Tier 8 Future-Work Claims](./02_CLAIMS_AND_DECISION_RULES.md#tier-8--future-work-claims-named-not-executed) and [03 — Suppressed / Rejected](./03_EXPERIMENT_CATALOGUE.md#suppressed--rejected).
