# DATP Journal Extension — Integrated Master Roadmap

**Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*

**Scientific reference project (behavioral reference only):** `/home/naslouby/Projects/datp` — used solely to recover the original DATP threshold-policy logic, experiment semantics, score-artifact behavior, and result interpretation. The journal-extension implementation is written from scratch; nothing in this roadmap implies reuse of that project's source layout, backward compatibility, shims, redirects, or migration.

**Primary venue:** Computer Networks (Elsevier). **Backup:** Internet of Things (Elsevier). **Excluded:** Computers & Security (standing AI/ML + federated-learning scope moratorium).

---

## 1. Executive Summary

**DATP identity.** DATP is a fixed-encoder, fixed-federated-model, threshold-calibration-scope study. A shared FedAvg autoencoder is trained once per seed and then frozen; only the *scope* at which the anomaly threshold is calibrated changes across the policy ladder B1 (shared), B2 (per-client), B3 (family), B4 (cluster). Calibration is benign-only. The causal question is not "which model is best?" but whether threshold-calibration scope changes deployed operating-point reliability — specifically per-client false-positive-rate (FPR) dispersion — across heterogeneous IoT clients. AUROC is a model-quality control, never the thresholding verdict.

**Journal-extension strategy.** The extension strengthens DATP along five disciplined axes without dissolving it into a generic FL-IDS benchmark: (i) one new sensor-group-partitioned external dataset (Edge-IIoTset, Regime D); (ii) a matched-operating-point federated-threshold comparator (`B-FedStatsBenign`) plus explicit Laridi scope disclosure; (iii) two training-side stress tests outside the causal ladder (FedProx aggregation, one model-personalization comparator); (iv) four threshold variants that deepen the calibration story (q-sensitivity, local-global shrinkage, calibration-size-aware fallback, split-conformal B2-conf); and (v) one chronological-split temporal-recalibration experiment. Six mechanism analyses and Appendix A support these. The confirmatory endpoint is unchanged and remains the sole locked claim.

**The four newly integrated modules.** Cluster/Family Thresholding is folded in as a **core journal mechanism module** that turns the discrete B3/B4 baselines into a granularity-and-stability analysis of threshold scope on a fixed detector. Small-Calibration-Set / Few-Shot Thresholds enters as a **supportive threshold-variant module** (calibration-size ablation plus local-global shrinkage) that defends B2 against the "needs too much benign data" objection. Federated Quantile Thresholding enters as a **methods backbone / comparator primitive** that gives every threshold construction a principled, auditable quantile-estimation vocabulary rather than hand-waved percentile logic. Model vs Threshold Personalization enters as an **external stress-test / reviewer-objection module** (and a possible future spin-off) that answers "why not personalize the model instead?" while keeping model personalization strictly outside the B1–B4 causal ladder.

**Risk summary.** The dominant residual risk is model-personalization *absorption* — whether the threshold-scope gain survives when the model itself is personalized — handled by a pre-specified absorption rule with all outcomes reportable. The second risk is novelty collapse against Laridi et al. (2024), handled by a matched-exceedance benign-only comparator plus an explicit disclosure that the anomaly-labeled Laridi-faithful setting is out of DATP's benign-only contract. Secondary risks are modest client count (K ∈ [9, 15]), single temporal split, qualitative-only privacy framing, and possible CI widening under the 10-seed extension. All are scoped explicitly with pre-committed wording.

**What the journal extension does NOT claim.** It does not claim to solve non-IID FL, to improve global Macro-F1, to preserve privacy, to handle concept drift beyond one-shot recalibration, to validate at fleet scale (K > 100), or to establish a universally dominant federated thresholding policy.

---

## 2. Non-Negotiable Scientific Identity (Locked)

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

**"Fairness" definition (locked).** Every use of "fairness" in this program means **operational / service-level FPR equity** — the evenness of false-alarm burden across client devices. It never refers to protected-attribute or human fairness. This is stated once in the manuscript and enforced throughout.

---

## 3. Locked Main Journal Claim

> **DATP's threshold-scope effect remains observable under a stronger journal protocol that adds external validation, a matched federated-threshold comparator, model/aggregation stress tests, and mechanism analyses, while preserving the fixed-encoder threshold-calibration identity.**

The **sole confirmatory endpoint** is tightly scoped and immutable:

- Regime A only (N-BaIoT natural physical-device split).
- B1 vs B2 only.
- CV(FPR) only.
- 10-seed paired evidence.
- 95% BCa bootstrap confidence interval on the per-seed delta.
- Δ_s = CV(FPR)[B1, s] − CV(FPR)[B2, s].
- **The confirmatory claim survives only if the BCa CI excludes zero in the correct (positive) direction.**

Reference conference values to be reproduced and honestly extended: B1 CV(FPR) = 1.017, B2 = 0.299, Δ = 0.718, 5-seed bootstrap CI [0.647, 0.769], 70.6% relative reduction, all seed deltas positive; B4 CV(FPR) = 0.645 (≈52% recovery); B3 = 0.964 (negligible); P10 Macro-F1 falls 0.344 → 0.300 under B2.

**Everything other than the confirmatory endpoint** is explicitly classified as exactly one of: supportive evidence, external validation, stress test, mechanism analysis, threshold variant, boundary condition, exploratory analysis, suppression evidence, future work, or possible spin-off. No supportive module may become a confirmatory claim.

---

## 4. Threshold-Policy and Comparator Nomenclature (Locked)

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

---

## 5. Claim Hierarchy

Nine ordered tiers. Each claim carries evidence, regime, metric, minimum pass condition, weak/null fallback, reviewer risk, and manuscript placement. Confirmatory sits alone at Tier 1; nothing below it may be promoted.

### 5.1 Tier 1 — Locked Confirmatory Claim

| Field | Specification |
|---|---|
| Claim text | Under Regime A natural device split, per-client p95 calibration (B2) reduces CV(FPR) relative to the client-averaged shared threshold (B1) by a magnitude whose 95% BCa bootstrap CI on the per-seed delta excludes zero (positive direction). |
| Evidence required | 10 paired seeds; Δ_s per seed; BCa CI on Δ; sign-consistency summary |
| Dataset / regime | Regime A (N-BaIoT, K = 9), confirmatory |
| Metric | CV(FPR) (primary) |
| Minimum pass condition | BCa CI excludes zero, positive direction |
| Fallback if weak/mixed/null | See §12.1; if CI touches/crosses zero, the confirmatory claim is revised to the observed direction and reported as the main result — never suppressed |
| Reviewer risk | "B2 equalizes FPR by construction" (tautology) — mitigated by Appendix A + B2-conf + calibration-size sweep |
| Placement | Main paper (headline result) |

### 5.2 Tier 2 — Secondary Supportive Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The B1→B2 reduction is not an artifact of the arithmetic-mean construction | Pooled and sample-weighted shared variants | Regime A | CV(FPR), IQR, max−min | All shared variants exceed B2 CV(FPR) | Main |
| The reduction holds in absolute dispersion, not only CV | IQR(FPR), max−min FPR | Regime A | IQR, max−min | Same B1 > B2 ordering | Main |
| The effect is heterogeneity-graded | Dirichlet α sweep | Regime C | CV(FPR) delta | Gap largest at low α, vanishes at IID | Main |
| The headline is not a q = 0.95 artifact | q-sensitivity sweep | Regime A | CV(FPR) | B2 < B4 < B1 ordering preserved across q (inversions reported) | Main |

### 5.3 Tier 3 — External Validation Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The threshold-scope effect generalizes to an independent sensor-group-partitioned dataset | B1–B4 + q-sensitivity + `B-FedStatsBenign` on Edge-IIoTset | Regime D | CV(FPR) + BCa CI | Effect direction consistent with Regime A, or divergence reported as boundary | Main |

### 5.4 Tier 4 — Stress-Test Claims (Outside Causal Ladder)

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| The gain is not absorbed by heterogeneity-aware aggregation | FedProx × B1–B4, µ-grid frozen | Regime A + D | CV(FPR) delta | Δ under FedProx compared to Δ under FedAvg; any absorption reported | Main (stress-test table) |
| The gain is not absorbed by model-side personalization | One model-personalization comparator × B1–B4; absorption ratio | Regime A + D | Δ_personalized / Δ_FedAvg | Pre-specified absorption bands (§9.3) | Main (stress-test table) |
| DATP is not dominated by a matched benign-only federated summary-statistics threshold | `B-FedStatsBenign` matched-exceedance; between-ratio diagnostic | Regime A + D | CV(FPR); between_ratio | Comparator reduces dispersion vs B1 but less than B2, or result reported honestly | Main (comparator table) |

### 5.5 Tier 5 — Mechanism Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| Cluster/family scope is a middle ground between global and local scope | B1/B3/B4/B2 comparison + within/across-cluster dispersion + cluster-stability (adjusted Rand) | Regime A (+ D where feasible) | CV(FPR), worst-client FPR, dispersion, stability | Cluster scope recovers part of B2's gain with lower per-client calibration demand, or result reported | Main |
| FPR concentration mechanism explains the P10 Macro-F1 tradeoff | Per-client benign+attack CDF overlays; Ennio Doorbell deep dive | Regime A | Per-client CDF, P10 F1 | Mechanism figure produced | Main |
| Heterogeneity severity predicts DATP benefit (association, not causation) | JS-divergence ↔ gain regression | Regime A/C | R², ρ | Reported with caveats; weak R² is a real result | Main |
| The fairness–sensitivity tradeoff is a quantified surface | Threshold-shift vs ΔFPR/ΔTPR scatter | Regime A | Δτ, ΔFPR, ΔTPR | All 9 devices, no filtering | Main |
| B4 clusters carry meaningful taxonomy-free structure | Cluster-feature ablation + cluster-to-device contingency table | Regime A | CV(FPR) per subset | Reported; instability reported if present | Main |

### 5.6 Tier 6 — Boundary-Condition Claims

| Claim | Evidence | Regime | Metric | Min pass | Placement |
|---|---|---|---|---|---|
| Under near-homogeneous file-level pseudo-clients, no dispersion reduction is observed | CICIoT2023 file-level | Regime B-a | CV(FPR); pairwise JS | Null reported as applicability boundary only | Main |
| B2 degrades detection in low-separability clients | P10 Macro-F1; worst-client BA | Regime A | P10 F1 | Reported as honest negative | Main |
| Under small benign calibration windows, naive local thresholds degrade and shrinkage stabilizes | Calibration-size sweep + τ-shrink | Regime A | Threshold variance, worst-client FPR vs n | Graceful degradation vs naive collapse, or reported | Main |
| Device-aware thresholds under a chronological split behave per one of three pre-specified temporal outcomes | Edge-IIoTset chronological 55/15/10/20 (historical train / historical calibration / future recalibration / future evaluation); frozen vs one-shot recalibration | Regime D-temporal | Per-window CV(FPR); recovery ratio | One pre-specified outcome applied (§11.1) | Main |

### 5.7 Tier 7 — Exploratory Claims

| Claim | Evidence | Regime | Metric | Placement |
|---|---|---|---|---|
| B4 at K = 3 recovers ≈52% of B2's improvement without a taxonomy | Existing Regime A result | Regime A | B4 recovery % | Main (labeled exploratory at N = 9) |
| B4 behavior at other K is a granularity sensitivity, not a main claim | K sweep where feasible | Regime A/D | CV(FPR) | Supplement |
| Federated quantile-estimation error tracks threshold reliability across constructions | Quantile-estimation error, FPR-target attainment | Regime A | Estimation error, attainment | Supplement/backbone |

### 5.8 Tier 8 — Future-Work Claims (Named, Not Executed)

Dynamic DATP (temporally adaptive per-client thresholds); Conformal DATP beyond the single B2-conf seed; formal privacy (DP/SecAgg); fleet-scale validation (K > 100); streaming drift mitigation; a standalone Model-vs-Threshold-Personalization 2×2 spin-off with full cost accounting; exhaustive personalized-FL and aggregation benchmarking. Each is named in Future Work and none is claimed as a result.

### 5.9 Tier 9 — Forbidden Claims

DATP "solves" non-IID FL; improved global Macro-F1; privacy preservation; concept-drift handling beyond one-shot recalibration; universal dominance over Laridi-style thresholding; fleet-scale validation; any "first"/"novel" language without independent verification; any dataset property (device IDs, timestamps, family counts) stated as verified fact without an artifact check; B4 fingerprints framed as a privacy mechanism.

---

## 6. Research Questions

Each RQ is tagged by role. Only RQ1 is confirmatory; the rest are supportive, mechanism, stress-test, or external/boundary.

- **RQ1 (confirmatory).** Under a fixed FedAvg AE, does threshold-calibration scope (B1 shared vs B2 per-client) change per-client FPR disparity on the natural N-BaIoT physical-device split, and what TPR/Macro-F1 tradeoff does it impose?
- **RQ2 (mechanism).** Do cluster/family thresholds (B3, B4) recover part of the local-threshold benefit while improving the fairness-vs-sample-efficiency and stability tradeoff relative to both B1 and B2 — and why does clustering *thresholds* on a fixed model differ from clustering *models*?
- **RQ3 (supportive).** How robust are local thresholds under small benign calibration windows, and can local-global shrinkage (τ-shrink) and a calibration-size-aware fallback stabilize them without discarding personalization?
- **RQ4 (mechanism / backbone).** Framing thresholds as distributed quantile-estimation objects, do federated quantile/statistical comparators (`B-FedStatsBenign`, pooled/weighted quantiles) explain or challenge DATP's threshold-scope effect, and at what estimation error and FPR-target attainment?
- **RQ5 (stress test).** Does threshold-only personalization remain useful when compared against aggregation-side (FedProx) and model-side personalization stress tests — i.e., does model personalization absorb the threshold-scope gain?
- **RQ6 (external / boundary).** Does the threshold-scope effect generalize to an independent sensor-group-partitioned dataset (Edge-IIoTset), how does it behave across Dirichlet severity, and where does it fail (near-homogeneous file-level pseudo-clients; chronological drift)?

RQ1 maps to Tier 1. RQ2 → Tier 5 (with the exploratory B4-recovery claim in Tier 7). RQ3 → Tier 6 calibration-window claim + supportive variants. RQ4 → Tier 4 comparator claim + Tier 7 backbone. RQ5 → Tier 4. RQ6 → Tier 3 + Tier 2 (Regime C) + Tier 6 (boundaries).

---

## 7. Experimental Regime Table

| Regime | Dataset | Client definition | Purpose | Threshold policies | New modules involved | Primary metric | Status | Pass / fail / suppression rule | Placement |
|---|---|---|---|---|---|---|---|---|---|
| A | N-BaIoT | 9 physical devices (K = 9) | Confirmatory B1 vs B2 | B0–B4 + all variants | Cluster/Family, Small-Cal, Fed-Quantile, Model-vs-Threshold | CV(FPR) | **Confirmatory** | Pass iff 10-seed BCa CI on Δ excludes zero (positive); revise honestly otherwise | Main |
| B-a | CICIoT2023 (file-level, d = 39) | 63 file-defined pseudo-clients | Near-homogeneous applicability boundary | B0, B1, B2, B4 | Fed-Quantile (framing) | CV(FPR); pairwise JS | **Boundary** | Null reported as boundary only; never generalized to CICIoT2023 | Main |
| B-b | CICIoT2023 (device/MAC repartition) | — | (Intended heterogeneous repartition) | — | — | — | **Rejected** (`B_B_REJECTED_NO_METADATA`) | Suppressed: available CSV artifact lacks MAC/device/IP/capture-source/timestamp columns; no pseudo-client substitute; no PCAP branch | Suppression note |
| C | N-BaIoT (Dirichlet) | 20 synthetic clients, α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID} | Non-IID severity sweep | B1, B2, B4 | Cluster/Family; Fed-Quantile | CV(FPR) delta | **Supportive** | Report gain vs α; overlapping low-α seed ranges → high-heterogeneity band, not strict monotonicity | Main |
| D | Edge-IIoTset | Sensor-group client (K = 10 benign group folders) | External validation | B1–B4 + `B-FedStatsBenign` + q-sensitivity | Cluster/Family, Fed-Quantile, Model-vs-Threshold, Small-Cal | CV(FPR) + BCa CI | **External validation** | Coverage ≥ 90% (n_k ≥ 100 for ≥ 90% of clients) to proceed; else reduce K or defer | Main |
| D-temporal | Edge-IIoTset (chronological) | Verified nine-group temporal population (K = 9, Modbus excluded — unusable timestamps), chronological 55/15/10/20 | Temporal recalibration MVE | B1, B2, B4; frozen vs one-shot | Small-Cal (shrinkage under recalibration) | Per-window CV(FPR); recovery ratio | **Boundary / exploratory** | One of three pre-specified outcomes (§11.1); no retroactive drift detector | Main (or supplement if timestamps unsuitable) |

**Feasibility flags.** CICIoT2023 feature count is treated as d = 39 consistent with the conference artifact; before any quantitative CICIoT2023 claim reaches print, the feature count of the *actual* processed artifact is re-verified, since mirror distributions of this dataset differ in column count. Edge-IIoTset benign sensor-group client identity is decided by a first-principles feasibility audit, not by appeal to any external precedent.

**Edge-IIoTset scope clarification (post-audit).** The completed full-corpus audit resolves Regime D feasibility. The normal-traffic group folder is the authoritative benign client identity: every source-integrity-valid benign row remains in its folder-defined client, while direction-normalized endpoint resolution is retained only for source-integrity auditing, attack-assignment diagnostics, and provenance. Benign sensor-group identity is therefore source-grounded and fully recoverable (eligible-benign coverage 1.0), so Regime D and D-temporal execute as **benign operating-point equity** validations — cross-client CV(FPR) dispersion, which is the primary external concern and the metric named in the table above. Because Edge-IIoTset attack traffic is confined to the attacker's subnet 0, *per-client attack-sensitive* metrics (TPR, Macro-F1, balanced accuracy, AUROC) are unavailable and are reported as a typed unavailability, never fabricated. Regime D therefore validates external **false-positive equity**, not cross-client attack-detection equity; B3 family thresholding is omitted (no Edge-IIoTset family taxonomy). This clarification distinguishes benign-FPR external validation (executable) from attack-sensitive external evaluation (unavailable) and does not affect the locked Regime A confirmatory endpoint.

---

## 8. Module Integration Table

| Module | Roadmap status | Scientific role | Required experiments | Required baselines | Required metrics | Reviewer objection answered | Claim status | Keep / optional / spin-off |
|---|---|---|---|---|---|---|---|---|
| **Cluster / Family Thresholding** | Integrated (core journal mechanism) | Deepen B3/B4 into a threshold-granularity + stability science; middle ground between B1 and B2 | B1/B2/B3/B4 comparison; cluster-granularity sweep (feasible K); cluster-stability (adjusted Rand); within- vs across-cluster dispersion; feature ablation | B1, B2, B3, B4 | CV(FPR), worst-client FPR, within/across dispersion, cluster stability; equity suite (Jain/IQR/Gini) as optional | "Clustering is known" → contribution is threshold-scope clustering on a *fixed* federated detector; outcome is operational FPR equity, not accuracy | Mechanism (Tier 5) + exploratory (Tier 7); **not** confirmatory | Keep in journal; PC-11 conference spin-off only if granularity results are strong |
| **Small Calibration Windows / Shrinkage** | Integrated (supportive threshold variant) | Calibration robustness; interpolate B2↔B1/B4 as n shrinks | Calibration-size ablation (n_k ∈ {50,100,250,500,1k,5k}); τ-shrink λ-sweep; calibration-size-aware λ(n_k) fallback | B1, B2, B4, (conformal) | Threshold variance vs n, worst-client FPR at small n, personalization retained, P10 F1 per λ | "Just collect more benign data" / "shrinkage is textbook" → some IoT clients only yield small/contaminated windows; contribution is applying/testing calibration robustness in the FL-IoT thresholding regime, no new statistical theory claimed | Supportive (Tier 6 + variants) | Keep as module; PC-5 spin-off only if edge-regime robustness is convincing |
| **Federated Quantile Thresholding** | Integrated (methods backbone / comparator primitive) | Treat thresholds as distributed quantile-estimation objects; principled, auditable estimation core | Exact centralized (oracle) vs local vs quantile-of-quantiles / weighted; estimation error; FPR-target attainment; (optional) communication cost | Local quantile (B2), centralized exact quantile (B0/pooled) | Quantile-estimation error, threshold variance, FPR-target attainment, calibration sample efficiency, (optional) comm cost | "This is just quantiles" → no novel-estimator claim; purpose is reproducibility, auditability, comparability of threshold estimation | Backbone (Tier 7) + supports Tier 4 comparator | Keep as backbone; **not** a standalone paper |
| **Model vs Threshold Personalization** | Integrated (external stress test / reviewer objection) | Answer "why personalize thresholds not the model?"; keep model personalization outside B1–B4 ladder | 2×2 framing (global/personalized model × global/personalized threshold) realized as one model-personalization comparator × B1–B4; absorption ratio; cost/benefit framing | Global-model+global-threshold, global-model+B2, personalized-model+global-threshold, personalized-model+B2 | CV(FPR), worst-client FPR, Macro-F1/BA, communication + compute + complexity cost | "Model personalization makes threshold personalization obsolete" → show when threshold-only captures most operating-point equity at lower cost; report absorption honestly | Stress test (Tier 4) | Keep as in-paper stress test; **possible spin-off** (PC-12) as a full standalone 2×2 with cost accounting — future work only |

**2×2 reconciliation.** The full independent 2×2 with cost accounting is the *spin-off*. In this paper the 2×2 is realized economically as a single model-personalization comparator crossed with the threshold ladder, so that {FedAvg, personalized} × {B1, B2} populates the 2×2 corners and the absorption ratio reads directly off it. This satisfies the 2×2 conceptual requirement without exceeding the hard limit of one model-personalization stress test. **Ditto-vs-fallback choice resolved.** The comparator is genuine Ditto (Li et al., ICML 2021), not the `FedRep-AE`/`FedPer-AE` fallback: Ditto's architecture-agnostic proximal regularization needs no separable representation/head split, so it applies to the fixed autoencoder unchanged, unlike FedRep/FedPer. `SCIENTIFIC_FOUNDATION.md §7.3` and `configs/models/autoencoder.yaml` carry the complete specification (global model state, persistent client-personalized state never aggregated, proximal personalized objective, a pre-registered proximal-weight grid, a Regime-A-locked-checkpoint selection rule, checkpoint reuse, evaluation state, and artifact separation) required by SB-24 before the "Ditto" label may be used.

---

## 9. Experiment Matrix

Experiments are partitioned into mandatory-confirmatory, mandatory-supportive, optional-high-value, suppressed/rejected, and future-work. The partition is the primary scope-creep guard: nothing migrates upward without an explicit decision recorded here.

### 9.1 Mandatory Confirmatory

| ID | Purpose | Inputs | Baselines | Metrics | Minimum viable | Journal-grade | Blocking deps | Claim | Failure interpretation | Placement |
|---|---|---|---|---|---|---|---|---|---|---|
| E-C1 | B1 vs B2 threshold-scope effect | Regime A stored/recomputed scores, 10 seeds | B1, B2 | CV(FPR), Δ_s, BCa CI | 5-seed CI (power-limited) | 10-seed BCa CI | Score artifacts | Tier 1 | If CI crosses zero, revise claim to observed direction; report, never hide | Main |

### 9.2 Mandatory Supportive / Mechanism / External / Stress

| ID | Purpose | Inputs | Baselines | Metrics | Minimum viable | Journal-grade | Blocking deps | Claim | Failure interpretation | Placement |
|---|---|---|---|---|---|---|---|---|---|---|
| E-S1 | Construction-sensitivity (mean-artifact rule-out) | Regime A scores | B1, B1-pool, B1-wt, B2 | CV(FPR), IQR, max−min | Existing table | + 10-seed | Scores | Tier 2 | If a shared variant matches B2, narrow the "not mean-artifact" claim | Main |
| E-S2 | q-sensitivity | Regime A scores | B1, B2, B4 | CV(FPR) at q∈{.90,.95,.975,.99} | Heatmap | + Regime D | Scores | Tier 2 | Report any ordering inversion honestly | Main |
| E-S3 | Dirichlet severity | Regime C | B1, B2, B4 | CV(FPR) vs α | Existing sweep | + BCa per α | Regime C scores | Tier 2 | Non-monotone low-α band reported as band, not ordered pair | Main |
| E-M1 | Cluster/family granularity + stability | Regime A (+ D) fingerprints | B1, B2, B3, B4 | CV(FPR), within/across dispersion, adjusted Rand, worst-client FPR | K = 3 + stability | + K sweep + D | Fingerprints | Tier 5 (RQ2) | If clusters unstable, report instability; B4 stays exploratory at K = 9 | Main |
| E-M2 | B4 cluster-feature ablation | Regime A fingerprints | B4 subsets + all-four | CV(FPR) per subset; cluster→device contingency | 4 subsets | + per-seed stability | Fingerprints | Tier 5/7 | Report subset instability | Main |
| E-M3 | Per-client CDF overlays + Ennio deep dive | Regime A benign+attack scores | B1, B2, B4 overlays | Per-client CDF, P10 F1 | Figure | + all clients | Scores | Tier 5 | — | Main |
| E-M4 | JS ↔ gain regression | Regime A/C benign distributions | — | R², ρ | Scatter+fit | + Regime D points | Distributions | Tier 5 | Weak R² is a real result | Main |
| E-M5 | Threshold-shift vs ΔFPR/ΔTPR | Regime A thresholds+scores | B1→B2 shift | Δτ, ΔFPR, ΔTPR | Scatter, 9 devices | — | Scores | Tier 5 | No device filtering | Main |
| E-V1 | Calibration-size sweep | Regime A scores subsampled | B1, B2, B4 | Threshold variance, worst-client FPR vs n | n∈{50,100,250,500,1k,5k} | + shrinkage overlay | Scores | Tier 6/RQ3 | Plateau/collapse reported | Main |
| E-V2 | Local-global shrinkage τ-shrink | Regime A scores | B1, B2 | CV(FPR), P10 F1 per λ∈{0,.25,.5,.75,1} | λ-curve | + calibration-size-aware λ(n_k) | Scores | RQ3 supportive | Non-monotone λ reported | Main |
| E-V3 | Split-conformal B2-conf | Regime A cal/test scores | B2 | Marginal coverage vs 1−α, CV(FPR) | Coverage check α=.05 | + Regime D | Scores | Tier 1 support (tautology) | Coverage miss reported as conformal-adaptation limit | Main |
| E-X1 | Edge-IIoTset external validation | Regime D processed data | B1–B4 + `B-FedStatsBenign` + q | CV(FPR) + BCa CI | K∈{6,15} | + temporal | Regime D preprocessing/training | Tier 3 | Divergence reported as boundary | Main |
| E-T1 | FedProx aggregation stress test | Regime A + D | FedProx×B1–B4, µ frozen | CV(FPR) delta | µ-grid on A | + D | Trained FedProx encoders | Tier 4 | Convergence failure reported non-retroactively; no µ search post-hoc | Main (stress) |
| E-T2 | Model-personalization stress test | Regime A + D | (personalized)×B1–B4 | Δ_personalized/Δ_FedAvg | On A | + D | Personalized encoders | Tier 4 | Absorption bands (§9.3) applied as-is | Main (stress) |
| E-T3 | `B-FedStatsBenign` matched comparator | Regime A + D scores | B1, B2, `B-FedStatsBenign` | CV(FPR); between_ratio | On A | + D | Scores | Tier 4 | Reported honestly; benign-only scope stated | Main (comparator) |
| E-B1 | Temporal recalibration MVE | Regime D chronological | frozen vs one-shot | Per-window CV(FPR), recovery ratio | 55/15/10/20 split | + per-client slope | Regime D timestamps | Tier 6 | One of three outcomes (§11.1) | Main |
| E-O1 | Operational alert burden | Regime A/D scores + declared rate | B1, B2 | Alerts/device/day | Table | + per-device | Real/cited rate source | Tier 5 support | Omit metric if no real/cited rate | Main |

### 9.3 Optional but High-Value

| ID | Purpose | Metrics | Placement |
|---|---|---|---|
| E-Q1 | Federated quantile-estimation backbone: exact vs local vs quantile-of-quantiles/weighted; estimation error and FPR-target attainment across B1/B1-pool/B1-wt/`B-FedStatsBenign` | Quantile-estimation error, FPR-target attainment, threshold variance, (optional) comm cost | Supplement / backbone |
| E-Q2 | Robust cluster-median B4 variant | CV(FPR) outlier robustness | Supplement |
| E-Q3 | Equity suite (Jain / Gini / IQR) alongside CV(FPR) | Equity indices | Supplement |
| E-Q4 | Bootstrap CIs for all secondary metrics; full Wilcoxon + matched-pairs rank-biserial correlation | Effect sizes | Supplement |
| E-Q5 | Fixed-k Laridi variants (k∈{2.0,2.5,3.0}) as sensitivity | CV(FPR) | Supplement |
| E-Q6 | Bytes-per-round communication/storage table for B1/B2/B4 | Estimated message sizes | Supplement |

**Model-personalization absorption bands (pre-specified, applied without adjustment).** Let Δ_FedAvg = CV(FPR)[FedAvg+B1] − CV(FPR)[FedAvg+B2] and Δ_pers = CV(FPR)[Pers+B1] − CV(FPR)[Pers+B2].
- Δ_pers ≥ 0.75·Δ_FedAvg → threshold personalization remains strongly useful under model personalization (corroborating).
- 0.25·Δ_FedAvg ≤ Δ_pers < 0.75·Δ_FedAvg → partial absorption (boundary condition).
- Δ_pers < 0.25·Δ_FedAvg → largely absorbed; DATP claim narrowed to FedAvg-style / shared-encoder settings, reported explicitly.
- If CV(FPR)[Pers+B1] is within 0.05 of CV(FPR)[FedAvg+B2] → model personalization is an alternative path to FPR equity; reported as an informative positive finding about the method, not a DATP failure.

### 9.4 Suppressed / Rejected

| ID | Item | Status | Reason |
|---|---|---|---|
| E-R1 | CICIoT2023 B-b device/MAC repartition | `B_B_REJECTED_NO_METADATA` | Available CSV artifact lacks MAC/device/IP/capture-source/timestamp columns; no pseudo-client substitute; no PCAP branch |
| E-R2 | CICIoT2023 temporal probing | `TEMPORAL_REJECTED_NO_TIMESTAMPS` | No timestamp column; no pseudo-time from file/row/merge/folder order |
| E-R3 | FedBN | Rejected | Encoder has no BatchNorm; adding it changes the fixed-encoder identity |
| E-R4 | `B-LaridiFaithful` (anomaly-labeled) | Out of scope | Requires anomaly-labeled calibration; violates benign-only contract; named-disclosure only |
| E-R5 | MIA empirical leakage probe | Rejected | No established IoT-threshold leakage literature; qualitative bounded-disclosure only |
| E-R6 | Streaming drift / Page-Hinkley / FLARE-FLAME | Rejected | Scope drift; Dynamic DATP future work |
| E-R7 | Byzantine-robust federated conformal | Rejected | Scope drift (DATP-CP / defense line, not this paper) |
| E-R8 | Broad personalized-FL benchmark (APFL, Per-FedAvg, pFedMe, FedPer full) | Rejected | Exceeds three-family stress-test limit |

### 9.5 Future Work (Named)

Dynamic DATP; Conformal DATP beyond the B2-conf seed; DP/SecAgg privacy; fleet-scale K > 100; standalone Model-vs-Threshold 2×2 spin-off; further aggregation sensitivity; hardware/edge profiling. All named, none executed.

---

## 10. Metrics and Statistical Plan

**Primary metric.** CV(FPR) = σ_FPR / µ_FPR over eligible clients (n_k ≥ n_min = 100 benign calibration samples). CV(FPR) definition is identical to the conference version and is never silently changed.

**Secondary operating-point metrics.** worst-client FPR; IQR(FPR); max−min FPR; alert burden (only with a real or cited traffic rate); CV(TPR); P10 Macro-F1; worst-client balanced accuracy.

**Optional equity metrics.** Jain index; Gini coefficient; within/across-cluster dispersion. Reported alongside CV(FPR), never replacing it.

**Model-quality controls (not thresholding verdicts).** AUROC; Macro-F1; balanced accuracy.

**Threshold-estimation metrics (federated-quantile backbone).** quantile-estimation error vs centralized oracle; threshold variance; FPR-target attainment (|achieved exceedance − (1−q)|); calibration sample efficiency.

**Statistical requirements (locked).**
- 10 paired seeds for the confirmatory claim; per-seed Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s].
- 95% **BCa** bootstrap CI on the per-seed Δ for the primary claim (BCa preferred over percentile for small samples).
- Wilcoxon signed-rank and matched-pairs rank-biserial correlation (the paired effect size; replaces Cliff's δ, which is an unpaired/independent-samples statistic unsuited to this program's entirely paired-seed design) are descriptive secondary evidence only.
- Absolute-dispersion checks (IQR, max−min) accompany CV wherever mean FPR is small, to guard against small-denominator artifacts.
- No test-set-driven checkpoint selection. No poisoned, stress-test, or external-regime metric selects the main checkpoint. Regime A alone selects one global primary checkpoint used for every main-regime table.
- Null and mixed results remain reportable and are pre-committed to fallback wording (§12).

**Seed-extension honesty rule.** If the 10-seed extension widens the CI or brings it near zero, the 10-seed result becomes the main result and the 5-seed conference result is labeled preliminary. If the reproduced 5-seed CI differs materially from the reference [0.647, 0.769] — shifting toward zero or more than ~20% wider than the reference width (≈0.122, i.e. wider than ≈0.147) — expansion claims are blocked until resolved. The 10-seed result is never suppressed when less favorable.

**Journal checkpoint protocol (locked).** Train once to a maximum of 200 rounds; save and evaluate checkpoints at rounds {25, 50, 75, 100, 125, 150, 200}. Convergence is logged as diagnostic metadata and does not stop training. Regime A selects one global primary checkpoint; that checkpoint is used for every main-regime table. Other checkpoints are supplementary stability evidence. Per-regime selection, test-AUROC selection, attack-label selection, and hiding weak checkpoint curves are all forbidden.

**Historical anchor protocol (locked).** The five-seed conference-faithful anchor uses per-client standardization fit on each client’s benign training rows, Adam with learning rate `0.001`, batch size 256, one local epoch, and full participation. From round 40, evaluate the relative endpoint change across the trailing ten FedAvg-weighted benign validation losses; select the first round below `0.005`, otherwise the 150-round cap, and save only that selected checkpoint. Its 95% five-seed interval is the percentile bootstrap with 10,000 resamples and seed 42.

---

## 11. Temporal Recalibration — Pre-Specified Outcomes

Edge-IIoTset is the sole temporal substrate (multi-day capture window), using the verified nine-group temporal population (Modbus excluded — unusable timestamps). N-BaIoT drift magnitude is limited; CICIoT2023 temporal probing is rejected (`TEMPORAL_REJECTED_NO_TIMESTAMPS`). The MVE is a leakage-free within-client chronological 55/15/10/20 split: `historical_train` (first 55% of each client's benign data by capture time) and `historical_calibration` (next 15%) drive AE training and B1/B2/B4 calibration; `future_recalibration` (next 10%) supplies the one-shot recalibration window; `future_evaluation` (final 20%) reports frozen-threshold and recalibrated-threshold CV(FPR). A matched static reference is constructed over the same nine groups (random_fractional split, no chronology) to isolate drift from ordinary sampling variance: `static_reference_cv`, `frozen_future_cv`, and `recalibrated_future_cv` are all reported, with `drift_excess = frozen_future_cv − static_reference_cv` and `recovered_amount = frozen_future_cv − recalibrated_future_cv`; `recovery_ratio = recovered_amount / drift_excess` is computed only when `drift_excess` is meaningfully positive (undefined and never computed otherwise). Duplicate timestamps preserve original row order (stable sort); endpoint resolution never excludes a source-integrity-valid benign row from its folder-defined client; minimum row counts and a typed infeasibility outcome apply if chronology cannot be verified; the seed analysis is paired over the locked seed cohort with a 95% BCa bootstrap CI. Rejected as scope drift: streaming sliding-window recalibration, cross-dataset transfer, Page-Hinkley, FLARE/FLAME, Byzantine-robust federated conformal.

### 11.1 Locked Outcome Interpretations

- **Outcome A — drift exists, one-shot recalibration helps** (recovery ratio ≥ 50% of the original CV(FPR) gain). "Under the available temporal window, one-shot threshold recalibration recovers a meaningful portion of the CV(FPR) gain; periodic recalibration is a viable operational policy for device-aware thresholds."
- **Outcome B — drift exists, one-shot recalibration does not help** (recovery ratio < 50%). "Device-aware thresholds exhibit temporal fragility in this benchmark; one-shot recalibration is insufficient; continuous drift mitigation would be required (future work)." No streaming detector is added retroactively to rescue the result.
- **Outcome C — no meaningful drift** (FPR drift within the bootstrap CI of the static split). "Under the available chronological window, device-aware thresholds appear stable; this does not establish general temporal robustness but reduces concern that the DATP effect is a static-split artifact."

---

## 12. Fallback Wording

Every major claim carries pre-committed wording for strong-positive, weak-positive, mixed, null, opposite, feasibility-rejection, and suppressed outcomes. Wording is selected only after result freeze and never softens a null.

### 12.1 B1 vs B2 Confirmatory (Tier 1)

- **Strong positive.** "B2 reduces CV(FPR) from [B1] to [B2] (10-seed BCa CI [a, b], excluding zero); all seed deltas positive."
- **Weak positive.** "B2 reduces CV(FPR) with a 10-seed BCa CI [a, b] that excludes zero but is wide; the effect is directionally consistent though the magnitude is uncertain at this seed count."
- **Mixed.** "The reduction is present in most seeds; the BCa CI [a, b] excludes zero, but seed [x] shows attenuation attributable to [cause], reported as a stability caveat."
- **Null.** "At 10 seeds the BCa CI [a, b] includes zero; the confirmatory endpoint is not met at this power. We report the point estimate and the failure to exclude zero rather than the 5-seed result."
- **Opposite.** "B2 increases CV(FPR) relative to B1 in this regime (CI [a, b], positive lower bound in the opposite direction), which we report as an unexpected reversal and analyze in §Mechanism."
- **Feasibility rejection.** N/A for Regime A.
- **Suppressed.** N/A — the confirmatory experiment is never suppressed.

### 12.2 B4 Cluster Recovery

- **Strong.** "B4 recovers ≈[x]% of B2's improvement at K = 3 without a taxonomy."
- **Weak/mixed.** "B4 partially recovers B2's improvement ([x]%), with recovery varying across seeds ([range]); B4 is exploratory at N = 9."
- **Null.** "B4 does not recover a meaningful fraction of B2's gain under this fingerprint; cluster-scope thresholds are not supported at this device count."

### 12.3 Cluster Stability

- **Strong.** "Cluster assignments are stable across seeds (adjusted Rand [x])."
- **Weak/null.** "Cluster assignments are unstable across seeds (adjusted Rand [range]); B4 results are reported as exploratory and sensitive to initialization."

### 12.4 Small Calibration Windows

- **Strong.** "As n_k falls, naive local thresholds show rising variance while shrinkage maintains worst-client FPR; personalization is retained down to n_k = [N*]."
- **Weak/null.** "Shrinkage does not stabilize thresholds below n_k = [N*]; the calibration-size-aware fallback reverts to B1-equivalent FPR, which we report as the operating floor."

### 12.5 Shrinkage (τ-shrink)

- **Strong.** "τ-shrink interpolates B1↔B2 monotonically and mitigates the P10 Macro-F1 loss at intermediate λ."
- **Weak/null.** "τ-shrink shows non-monotone λ behavior / does not mitigate the P10 Macro-F1 loss; we report the λ-curve as-is without selecting a favorable λ."

### 12.6 Federated Quantiles (Backbone)

- **Positive.** "Framing B1/B1-pool/B1-wt/`B-FedStatsBenign` as quantile estimators clarifies their estimation error and FPR-target attainment; no novel estimator is claimed."
- **Null/limitation.** "Approximate federated quantile estimation does not improve FPR-target attainment over the local baseline here; the backbone remains a reproducibility and comparability device, not a contribution."

### 12.7 Model-Personalization Stress Test

Wording follows the four absorption bands (§9.3) verbatim; all four are valid findings and none is hidden.

### 12.8 FedProx Stress Test

- **Survives.** "The B1→B2 CV(FPR) gain persists under FedProx aggregation across the frozen µ-grid; the threshold-scope effect is not an artifact of vanilla FedAvg."
- **Convergence failure.** "All pre-specified µ values fail to converge on Regime [x]; we report the convergence failure and add no post-hoc µ. Any µ introduced after seeing results is labeled exploratory and cannot support the stress-test claim."

### 12.9 Edge-IIoTset External Validation

- **Consistent (external validation, non-confirmatory).** "On Edge-IIoTset ([partition], K = [x]), B2 reduces CV(FPR) from [Y] to [Z] (95% BCa CI [a, b]), consistent with Regime A; this is external-validation (Tier 3) evidence, not a second confirmatory endpoint — the sole confirmatory claim remains Regime A B1-vs-B2 (§3, §5.1)."
- **Mixed/null.** "On Edge-IIoTset the effect is [attenuated/absent]; we report this as an external boundary rather than as confirmation, and discuss partition/heterogeneity differences."
- **Feasibility rejection.** "Edge-IIoTset did not meet the eligibility-coverage threshold (n_k ≥ 100 for ≥ 90% of clients); we reduce K / defer the temporal MVE and document the reason."

### 12.10 CICIoT2023 Boundary

- **Boundary (expected).** "Under the file-level near-homogeneous partition, no dispersion reduction is observed; this is an applicability boundary, not a general CICIoT2023 statement."
- **B-b feasibility rejection.** "CICIoT2023 B-b was infeasible on the available CSV artifact because MAC/device/IP/capture-source/timestamp metadata are absent; reprocessing from PCAPs is out of scope."

---

## 13. Reviewer Loophole Register

Each row: the reviewer attack, why it is dangerous, the roadmap defense, the required experiment or wording, and a status checkbox. Defenses are testable; none is hand-waved.

| # | Reviewer attack | Why dangerous | Roadmap defense | Required experiment / wording | Status |
|---|---|---|---|---|---|
| L01 | "Thresholding is trivial post-processing" | Dismisses the whole contribution | Freeze the encoder; show scope changes per-client FPR at near-constant AUROC | E-C1 + AUROC control reported | ☐ |
| L02 | "Laridi already does federated thresholding" | Novelty collapse | Delta is benign-only + operating-point equity; matched-exceedance comparator; explicit faithful/benign-only split | E-T3 + `B-LaridiFaithful` out-of-scope disclosure | ☐ |
| L03 | "Local thresholds just overfit benign calibration" | Undercuts B2 | Held-out test measurement; calibration-size sweep; conformal coverage | E-C1 (test), E-V1, E-V3 | ☐ |
| L04 | "B2 works only because it controls FPR by construction" | Tautology | Appendix A: equality exact on cal data only; empirical test-FPR variance is what is measured; B2-conf finite-sample coverage | Appendix A + E-V3 + wording (§12.1) | ☐ |
| L05 | "CV(FPR) is not enough" | Metric fragility | Report IQR, max−min, worst-client FPR, alert burden, equity suite | E-S1, E-O1, E-Q3 | ☐ |
| L06 | "Cluster thresholds are just known clustering" | Novelty of module | Contribution is threshold-scope clustering on a *fixed* federated detector; outcome is operational FPR equity; contrast Sáez-de-Cámara (clusters models) | E-M1 + related work | ☐ |
| L07 | "Family labels are arbitrary" | Undermines B3 | B3 reported precisely as underperforming because taxonomy ≠ calibration structure; motivates B4 | Existing B3 result + wording | ☐ |
| L08 | "B4 K was tuned after seeing results" | HARKing | K = 3 canonical pre-committed; silhouette instability documented; other K exploratory/supplementary | SB-K lock + E-M1 | ☐ |
| L09 | "Small calibration windows make B2 unrealistic" | External validity | Calibration-size sweep + shrinkage + calibration-size-aware fallback; argue small/contaminated windows are real | E-V1, E-V2 | ☐ |
| L10 | "Shrinkage is textbook" | Novelty of module | No new statistical theory claimed; contribution is testing calibration robustness in FL-IoT thresholding | E-V2 wording | ☐ |
| L11 | "Federated quantiles are not novel" | Overclaim risk | Positioned explicitly as backbone/primitive; no novel-estimator claim | E-Q1 wording | ☐ |
| L12 | "Model personalization makes threshold personalization obsolete" | Strongest objection | Absorption ratio with pre-specified bands; all outcomes reportable | E-T2 + §9.3 | ☐ |
| L13 | "FedProx/Ditto/FedRep/FedPer are unfairly implemented" | Comparator fairness | µ-grid and E locked equal to FedAvg; Ditto choice documented before training; fallback named honestly | E-T1, E-T2 + G-notes | ☐ |
| L14 | "CICIoT2023 pseudo-clients are not real clients" | Dataset validity | Reported as Regime B-a boundary only; B-b rejected on metadata grounds | E-R1 + wording (§12.10) | ☐ |
| L15 | "Edge-IIoTset client mapping is ambiguous" | External-validity ceiling | Partition decided by first-principles feasibility audit; documented before training | E-X1 preprocessing audit | ☐ |
| L16 | "External validation failed or is mixed" | Honesty test | Pre-committed mixed/null wording; reported as boundary | §12.9 | ☐ |
| L17 | "AUROC did not improve" | Misreads the paper | AUROC is a control, not the verdict; stated explicitly | Identity statement + wording | ☐ |
| L18 | "Macro-F1 tradeoff is hidden" | Integrity | P10 Macro-F1 degradation reported as honest negative; Ennio deep dive | E-M3 + Tier 6 claim | ☐ |
| L19 | "False-positive fairness is not human fairness" | Framing | "Fairness" defined once as operational/service-level FPR equity | Locked definition (§2) | ☐ |
| L20 | "No privacy guarantee" | Scope | Qualitative bounded-disclosure only; B4 explicitly not a privacy mechanism; DP/SecAgg future work | Privacy disclosure table | ☐ |
| L21 | "No deployment measurement" | Scope | Communication/storage estimated from message sizes; no hardware claim | E-Q6 + wording | ☐ |
| L22 | "No poisoning/evasion/backdoor analysis" | Scope | Explicitly out of scope; named future work (DATP-CP is a separate paper) | SB list | ☐ |
| L23 | "Too many experiments create HARKing" | Integrity | Pre-specification before observation; fallback wording locked; suppression rules explicit | §10 + §12 | ☐ |
| L24 | "Conference-to-journal overlap is too high" | Desk reject | ≥ 40% substantive new material (self-imposed benchmark); cover-letter enumeration; figures redrawn | §15 | ☐ |
| L25 | "The journal extension is too broad" | Scope creep | Hard limits: 1 new dataset, 3 stress-test families, 4 threshold variants, 1 temporal family, 6 mechanism analyses | Scope boundaries (§16) | ☐ |
| L26 | "The journal extension is too narrow" | Editor judgment | Framed as a fairness-oriented threshold-calibration study with external + stress + mechanism evidence | Executive summary framing | ☐ |
| L27 | "The code was inherited and messy" | Reproducibility | New codebase written from scratch; reference project used only for DATP semantics | §17 | ☐ |
| L28 | "Scratch codebase means reproducibility must be specified cleanly" | Reproducibility | Deterministic seeds, reproducible manifests, testable threshold-policy contracts, traceable tables/figures | §17 checklist | ☐ |

---

## 14. Checklists

### 14.1 Core Identity Checklist
- ☐ Encoder/AE fixed for the core B1–B4 ladder (same final state, seeds, score artifacts).
- ☐ Threshold-calibration scope is the sole causal variable.
- ☐ Calibration is benign-only; attack data evaluation-only.
- ☐ CV(FPR) is the primary metric everywhere.
- ☐ AUROC is a control metric, never the thresholding verdict.
- ☐ FedProx, model personalization, and Laridi-style comparators are outside the causal ladder.
- ☐ No privacy / deployment / security / drift overclaim anywhere.
- ☐ "Fairness" means operational FPR equity, stated once.

### 14.2 Experiment Readiness Checklist
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

### 14.3 Module Integration Checklist
- ☐ Cluster/Family module integrated as core mechanism (Tier 5), not confirmatory.
- ☐ Small-window/shrinkage module integrated as supportive variant.
- ☐ Federated-quantile module integrated as backbone/primitive, no novelty overclaim.
- ☐ Model-vs-threshold module integrated as external stress test; spin-off marked future work.
- ☐ No module hijacks the confirmatory claim.
- ☐ Optional/spin-off decisions are explicit for every module.

### 14.4 Claim Discipline Checklist
- ☐ Every claim has an evidence requirement and a regime/metric.
- ☐ Every weak/mixed/null outcome has pre-committed fallback wording.
- ☐ No unsupported novelty language; no "first" without independent verification.
- ☐ No hidden main claim in the supplement.
- ☐ No cherry-picked checkpoint, K, or calibration size.
- ☐ No hidden failed experiment; suppressed items are documented in §9.4.

### 14.5 Manuscript Readiness Checklist
- ☐ Results written before the abstract; prose order Results → Methods → Discussion → Limitations → Related Work → Abstract → Conclusion → Supplement → cover letter.
- ☐ Methods match the executed experiments exactly.
- ☐ Limitations explicit (K, seeds, temporal, privacy, Laridi adaptation, CI width).
- ☐ Related work addresses Laridi (2024) and model personalization directly.
- ☐ Discussion separates success, boundary, and failure.
- ☐ Supplement holds exploratory material; main paper stays readable and focused.

---

## 15. Conference-to-Journal Originality Plan

**Reused (verbatim allowed).** DATP nomenclature and B1–B4 taxonomy; the Regime A confirmatory result (extended to 10 seeds); the Regime C Dirichlet sweep; the B0 centralized reference; theoretical definitions and notation.

**New (journal only).** Edge-IIoTset external-validation regime (D); the CICIoT2023 B-b formal rejection note; three stress-test comparator families crossed with B1–B4; four threshold variants; the chronological-split + one-shot recalibration regime; six mechanism analyses; Appendix A; expanded post-2022 related work; the four integrated modules' analyses.

**Redrawn.** Every figure is redrawn with additional series or replaced; every table extended; any section with > 50% reused prose is rewritten.

**Novelty threshold.** ≥ 40% substantive new material as a self-imposed conservative benchmark aligned with explicit Elsevier-family extension guidance (e.g. FGCS), **not** a Computer Networks requirement. Computer Networks' guide states only that enhanced, extended conference versions may be submitted; no fixed percentage is prescribed. The cover letter enumerates each new section, states no verbatim reuse of figures/text, waits for the conference camera-ready, and cites the conference paper.

---

## 16. Scope Boundaries (Stable Labels)

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

## 17. Implementation Planning — Code From Scratch (No Paths)

The journal-extension implementation is written from scratch for clarity. `/home/naslouby/Projects/datp` is consulted **only** as a behavioral reference for original DATP logic (threshold policies, calibration/test split semantics, score-artifact reuse, result interpretation). Nothing below reuses that project's source layout.

**Design principles.**
- No backward compatibility with the reference project's structure; no shims, redirects, or path aliases; no migration layers.
- No legacy naming that confuses the journal design; no stale policy labels leaking into new claims.
- No over-engineered boilerplate, no artificial abstraction layers, no autogenerated-looking or bloated comments. Comments only where they explain a non-obvious scientific or statistical decision.
- Clean enums, frozen dataclasses, and configs; explicit policy definitions; deterministic seeds; reproducible run manifests; testable threshold-policy contracts.
- Conceptual separation (not a folder listing) of: raw data, processed splits, per-client score artifacts, threshold outputs, metrics, reports, and manuscript exports — each stage traceable to a manifest.
- Clear experiment IDs (as in §9) and clean, conceptual output naming; every table and figure traces to a manifest.

**Threshold-scope semantics preserved from the reference project (behavior only).**
- Train once per (dataset, regime, seed, α); freeze the AE; score calibration and test benign/attack under the fixed AE; derive B1–B4 from shared score artifacts without retraining.
- Benign-only calibration; n_min = 100 eligibility with τ_global fallback for calibration-pending clients; coverage reported as |K_elig|/|K|.
- CV(FPR) computed over eligible clients; absolute-dispersion checks alongside.

**Federated-quantile backbone (conceptual contract).** A single quantile-estimation interface underlies B1 (client-averaged local p95), B1-pool (pooled p95), B1-wt (weighted), B2 (local p95), and `B-FedStatsBenign`, so estimation error, threshold variance, and FPR-target attainment are computed uniformly and comparably. No novel estimator is introduced.

**`B-FedStatsBenign` locked contract (before any computation).** Client message: benign-only count n_k, mean µ_k, variance σ_k² (no raw scores, no attack labels). Sample-count-weighted global mean. **Full pooled variance including the between-client mean-shift term:** σ²_global = Σ n_k·[σ_k² + (µ_k − µ_global)²] / Σ n_k. Report within_term, between_term, and between_ratio = between_term / (within_term + between_term) in the main text; if between_ratio > 0.5, state that the between-client mean shift dominates and a single global summary threshold is structurally strained. Matched-exceedance operating point on a fixed candidate grid τ(k) = µ_global + k·σ_global, k ∈ {0.00, …, 5.00} at step 0.01, selecting k* = argmin |Σ c_k(k)/Σ n_k − (1−q)| with ties broken toward larger k; only benign exceedance counts are exchanged. Fixed-k variants (k ∈ {2.0, 2.5, 3.0}) are supplementary sensitivity only.

**Implementation-clarity checklist.**
- ☐ Policy definitions are explicit (enum-backed, no stale labels).
- ☐ Threshold computation is isolated from scoring and from metrics.
- ☐ Calibration data is separated from test data at the type level.
- ☐ Metric computation is deterministic and unit-tested.
- ☐ Regime definitions are explicit and enumerated.
- ☐ Experiment manifests are reproducible (config → checkpoint → scores → metrics → table/figure).
- ☐ Every table/figure traces to a manifest.
- ☐ No test metric selects the main checkpoint.
- ☐ No hidden default changes threshold semantics.
- ☐ No old naming leaks into new claims.

---

## 18. What Changed From the Previous Roadmap

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

## 19. Audit Reports

### Audit 1 — Identity Preservation
- DATP remains threshold-scope-only: the sole causal variable is threshold-calibration scope (§2, §3, regime table). **Pass.**
- Fixed encoder preserved across B1–B4; score-artifact reuse without retraining (§2, §17). **Pass.**
- Stress tests (FedProx, model personalization, Laridi-style) are outside the causal ladder (§4, §8 table, SB-25). **Pass.**
- Dynamic DATP, poisoning, privacy, deployment, backdoor, evasion, full drift are not absorbed; each is future work or out of scope (§5.8, §5.9, §16). **Pass.**
- Residual note: the Federated-Quantile backbone touches B1 constructions; verified it is a *descriptive* estimation framing over the fixed ladder, not a new causal variable. **Pass with note.**

### Audit 2 — Claim Discipline
- Confirmatory (Tier 1) is isolated and singular; supportive/external/stress/mechanism/boundary/exploratory/future/forbidden tiers are separated (§5). **Pass.**
- Every claim row carries evidence, regime, metric, pass condition, fallback, placement (§5, §9). **Pass.**
- Forbidden claims enumerated (§5.9); "fairness" defined once (§2). **Pass.**
- Null/mixed/opposite outcomes handled with pre-committed wording for every major claim (§12). **Pass.**
- No supportive module is promoted to confirmatory; the 2×2 spin-off and cluster module are explicitly non-confirmatory. **Pass.**

### Audit 3 — Module Integration
- All four modules integrated with correct roles: Cluster/Family = core mechanism; Small-Cal/Shrinkage = supportive variant; Federated Quantiles = backbone; Model-vs-Threshold = stress test / spin-off (§8). **Pass.**
- None bloats the confirmatory claim; each appears in RQs, matrix, register, checklists (§6, §9, §13, §14). **Pass.**
- Optional/spin-off status explicit (PC-11 for cluster, PC-5 for small-cal, PC-12 for model-vs-threshold; quantiles never standalone). **Pass.**

### Audit 4 — Reviewer Loopholes
- 28 objections covered including tautology, Laridi novelty, clustering-is-known, HARKing, absorption, comparator fairness, pseudo-clients, external-validation mixed results, Macro-F1 hiding, human-vs-service fairness, privacy, deployment, overlap, too-broad/too-narrow, inherited/scratch code (§13). **Pass.**
- Each defense is testable (mapped to an experiment ID) or a locked wording; none is untestable-masquerading-as-evidence. **Pass.**
- Residual: L12 (absorption) and L02 (Laridi) remain the two highest residual risks; both have pre-specified interpretation rules that keep all outcomes reportable. **Pass with flagged residuals.**

### Audit 5 — Path and Scope Hygiene
- Automated scan below confirms no repository/document/output/data paths remain except `/home/naslouby/Projects/datp`. **Pass** (see scan result).
- The allowed path is described only as a behavioral reference (§0 front matter, §17). **Pass.**
- No backward compatibility, shims, redirects, or migration layers are required; the implementation is described as scratch/clean (§17). **Pass.**

### Audit 6 — Experimental Feasibility
- Mandatory confirmatory (E-C1) is a stored-score recomputation with a 10-seed extension — realistic (§9.1). **Pass.**
- Optional experiments marked optional (§9.3); suppressed/rejected documented with reasons (§9.4). **Pass.**
- Edge-IIoTset feasibility gated on eligibility coverage; CICIoT2023 B-b/temporal feasibility rejections are not overclaimed (§7, §9.4, §12). **Pass.**
- Statistical requirements (10 seeds, BCa CI) are feasible on the described hardware and stored artifacts. **Pass.**
- Feasibility flag surfaced: CICIoT2023 feature count (d = 39 in the conference artifact) must be re-verified against the actual processed artifact before any print claim, because mirror distributions differ in column count. **Conditional — flagged in §7.**

### Audit 7 — Manuscript Readiness
- The roadmap directly guides Results (§5, §9), Methods (§10, §17), Discussion/Limitations (§5.6, §12, §22-equivalent residuals), Related Work (§13 L02/L06, §15), Abstract/Conclusion (§1, §3), and cover letter (§15). **Pass.**
- Fallback wording present for every major claim (§12). **Pass.**
- Anti-HARKing controls: pre-specification before observation, locked K, locked protocols, suppression rules (§10, §16, L08, L23). **Pass.**
- Clear conference→journal extension story with reuse/new/redrawn split and ≥ 40% benchmark (§15). **Pass.**

**Audit 5 scan result.** An automated token scan over the full document finds zero repository, document, output, runtime-artifact, temp-root, or raw/processed-data paths. The only path token present is `/home/naslouby/Projects/datp` (5 occurrences), each describing it as a behavioral reference. All remaining slash tokens are terminology (e.g. Cluster/Family, AI/ML, B3/B4, within/across), not paths. **Audit 5 Pass confirmed.**

---

## 20. Go / No-Go / Conditional-Go Summary

**Verdict: GO — with two conditional gates.**

The roadmap is coherent enough to guide implementation. The scientific identity is intact (fixed encoder, threshold-scope-only causal ladder, benign-only calibration, CV(FPR) primary, AUROC control). The confirmatory endpoint is singular and locked with a hard survival rule. The four modules are integrated in their correct roles without disturbing the confirmatory claim. Stress tests are outside the causal ladder. Fallback wording, suppression rules, and scope boundaries are pre-committed. Path hygiene is clean.

**Conditional gate 1 (feasibility — non-blocking for start, blocking for print).** Before any quantitative CICIoT2023 statement reaches print, re-verify the feature count of the actual processed artifact (conference value d = 39; mirror distributions differ). This does not block starting stored-score work on Regime A/C, which is where the confirmatory and most supportive claims live.

**Conditional gate 2 (external validation — blocking for the Tier 3 claim only).** The Edge-IIoTset external-validation claim proceeds only if eligibility coverage is met (n_k ≥ 100 for ≥ 90% of clients) and the device-vs-group partition is assigned by the first-principles feasibility audit. If coverage fails, reduce K or defer the temporal MVE to supplement per the locked wording — the confirmatory claim is unaffected.

**Immediate-start work (no dependency, lowest risk).** All existing-score extensions: E-C1 (10-seed confirmatory), E-S1/S2/S3, E-M1–M5, E-V1/V2/V3, E-T3 (`B-FedStatsBenign`), E-O1, plus Appendix A. These close the tautology critique and populate the mechanism story before any new dataset or training infrastructure is touched.

**Two residual risks accepted with pre-specified handling.** Model-personalization absorption (E-T2, four bands, all reportable) and Laridi novelty (E-T3 matched-exceedance benign-only + `B-LaridiFaithful` out-of-scope disclosure). Neither can invalidate the confirmatory claim; both keep every outcome honest.

**No-Go conditions (none currently triggered).** The roadmap would move to No-Go only if: the confirmatory endpoint were widened beyond Regime A / B1-vs-B2 / CV(FPR); a stress test were promoted into the causal ladder; a supportive module were elevated to a confirmatory claim; or scope drift (poisoning, privacy guarantees, deployment, Dynamic DATP as a result rather than future work) were introduced. All are actively guarded by §2, §5, §16, and the reviewer register.
