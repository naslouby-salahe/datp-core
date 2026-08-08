# JOURNAL_CONTRACT_COMPLETE.md

## Scientific Implementation Contract for DATP-Core

> **STATUS: IN PROGRESS**
> **PRIORITY: ABSOLUTE PREREQUISITE**
> **SOURCE: docs/Journal_Extension_Master_Roadmap.md (3,543 lines)**
> **EXTRACTION DATE: 2026-08-08**

**IMPORTANT:** This is the working extraction of the complete scientific contract from the journal roadmap. This document is the **authoritative reference** for all audit decisions.

---

## EXECUTIVE SUMMARY

### Programme Identity
DATP-Core is a **controlled study of threshold-calibration scope** in federated IoT anomaly detection. 

**Core Scientific Question:** When heterogeneous IoT clients share one frozen federated anomaly detector, how does the scope of benign threshold calibration affect the distribution of false-alarm burden across clients?

**Primary Object:** Cross-client false-positive-rate dispersion (CV(FPR))

**Primary Endpoint:** Regime A (N-BaIoT), B1 vs B2, CV(FPR), 10 paired seeds, locked BCa decision rule

---

## 1. CORE CAUSAL CONTRACT (CRITICAL)

### 1.1 Fixed-Detector Rule
**For B1-B4 threshold-scope ladder:**
- One FedAvg autoencoder trained per seed
- SAME trained encoder state used across B1, B2, B3, B4
- SAME calibration and test scores used across B1, B2, B3, B4
- **ONLY threshold-calibration scope may differ**
- NO policy-specific retraining permitted
- NO threshold policy may alter: preprocessing, training data, model parameters, score generation, test labels, or client eligibility

### 1.2 Prohibited Causal Contamination
**FORBIDDEN within core ladder:**
- Retraining autoencoder separately for B1, B2, B3, or B4
- Selecting checkpoints independently for each threshold policy
- Selecting thresholds from attack-labelled data
- Choosing policy parameters using test metrics (F1, TPR, AUROC, balanced accuracy, CV(FPR))
- Changing eligible clients between compared policies
- Removing clients that weaken expected ordering
- Treating FedProx or model personalization as threshold-scope conditions
- Replacing failed B1-vs-B2 result with more favorable B4/shrinkage/conformal result

---

## 2. BENIGN-ONLY CALIBRATION (CRITICAL)

### 2.1 Attack Data Prohibition
**Every core threshold and DATP-compatible threshold variant fitted using BENIGN calibration data ONLY**

Attack-labelled records reserved for HELD-OUT EVALUATION ONLY and must NEVER:
- Determine threshold values
- Select quantiles
- Select checkpoints
- Select FedProx coefficients
- Select personalization coefficients
- Decide client inclusion
- Repair infeasible experiments
- Influence comparator tuning, shrinkage strength, conformal significance level
- Influence cluster count or cluster-feature selection
- Construct external-dataset client population

**This boundary is CENTRAL to DATP's identity.**

### 2.2 Calibration/Evaluation Isolation
- Calibration records and evaluation records MUST BE DISJOINT
- For temporal: historical calibration → future recalibration → future evaluation
- Future evaluation CANNOT influence any earlier stage
- Data ordering or generated pseudo-time CANNOT replace real chronology
- NO future-to-history leakage

---

## 3. THRESHOLD POLICIES (CRITICAL)

### 3.1 Policy Definitions

| Policy | Role | Construction | Canonical Quantile | Notes |
|--------|------|--------------|------------------|-------|
| **B0** | Centralized reference | Pooled AE + pooled threshold | q=0.95 | NOT part of B1-B4 ladder |
| **B1** | Shared (confirmatory anchor) | Mean of local benign q-quantiles | q=0.95 | ONLY confirmatory anchor |
| **B2** | Per-client (confirmatory comparator) | Local benign q-quantile per client | q=0.95 | ONLY confirmatory comparator |
| **B3** | Family threshold | Mean of local thresholds per device family | q=0.95 | Mechanism baseline, needs taxonomy |
| **B4** | Cluster threshold | Mean of local thresholds per data-driven cluster | q=0.95 | Mechanism baseline, K=3 clusters |

### 3.2 B4 Cluster Fingerprint (CRITICAL)
**MUST include:**
- mean(error)
- standard_deviation(error)
- skewness(error)
- p95(error)

**Canonical cluster count: K = 3** (cannot be changed post hoc)

### 3.3 Policy Availability
| Policy | Regime A (N-BaIoT) | Regime C (Dirichlet) | Edge-IIoTset | CICIoT2023 |
|--------|------------------|---------------------|-------------|-------------|
| B1 | ✓ Available | ✓ Available | ✓ Available | ✓ Available |
| B2 | ✓ Available | ✓ Available | ✓ Available | ✓ Available |
| B3 | ✓ Available | ⚠ Conditional | ✗ Unavailable | ✗ Unavailable |
| B4 | ✓ Available | ✓ Available | ✓ Available | ✓ Available |

---

## 4. DATASET BOUNDARIES (CRITICAL)

### 4.1 N-BaIoT (Regime A)
- **Role:** SOLE confirmatory population
- **Clients:** 9 physical devices as natural clients
- **Device family taxonomy:** May support B3
- **Limitation:** Small client count explicit
- **Preprocessing:** Client-local StandardScaler (FEDERATED_CLIENT_LOCAL_STANDARD)
- **Missing values:** Non-finite features FAIL VALIDATION (not filled)

### 4.2 CICIoT2023
- **Role:** Applicability boundary only
- **Prohibited:** Device-aware wording, physical device inference, artificial groupings
- **Model-input eligibility:** Recognized label AND all features finite
- **Gate behavior:** Records signals, NEVER imputes/fills/caps/infers
- **Applied identically** to every compared method

### 4.3 Edge-IIoTset
- **Role:** External validation of benign operating-point equity
- **Client definition:** First-principles dataset evidence
- **Attack assignment:** Where unavailable: per-client attack metrics UNAVAILABLE
- **Representation:** Must show as UNAVAILABLE (not estimated/fabricated)
- **B3 status:** Unavailable (no defensible external family taxonomy)

---

## 5. PREPROCESSING LOCKS (CRITICAL)

### 5.1 Preprocessing Identities
| Identity | Transformer | Fit Scope | Fit Partition | Serialization | Tolerance | Role |
|----------|-------------|-----------|---------------|-------------|-----------|------|
| FEDERATED_CLIENT_LOCAL_STANDARD | StandardScaler | Client-local | Train only | skops | 1e-12 | **CONFIRMATORY** |
| FEDERATED_POOLED_MIN_MAX | MinMaxScaler | Pooled | Train only | skops | 1e-12 | Supportive only |
| CENTRALIZED_POOLED_MIN_MAX | MinMaxScaler | Pooled | Train only | skops | 1e-12 | Centralized reference |

### 5.2 Preprocessing Contract Rules
- Preprocessing is part of FIXED DETECTOR STATE
- Within seed, population, training baseline, and NAMING PREPROCESSING PROTOCOL IDENTITY: every compared threshold policy reuses ONE fitted preprocessing state
- Threshold methods NEVER select, refit, or alter preprocessing
- DISTINCT protocol identities must NEVER be mixed silently within one confirmatory ladder
- Identity transforms EXCLUDED for multi-feature confirmatory AE input
- Pooled MinMax can ONLY be used under own protocol identity (supportive/mechanism)
- CANNOT replace confirmatory client-local StandardScaler without explicit claim-tier change

---

## 6. TRAINING CONTRACT

### 6.1 Primary Training
- **Algorithm:** FedAvg (sole confirmatory method)
- **Local epochs:** E = 1 per round
- **Participation:** Full client participation
- **Optimizer/hyperparameters:** Fixed across regime
- **Round budget:** Maximum 200 rounds
- **Checkpoints:** Rounds 25, 50, 75, 100, 125, 150, 200

### 6.2 Checkpoint Selection
- Primary checkpoint: One global primary per seed using LOCKED NON-TEST rule
- **FORBIDDEN:** Selecting by test AUROC, attack labels, maximizing DATP effect, or different main checkpoint for supportive experiments
- Other checkpoints: Stability evidence ONLY

### 6.3 Stress Test Training
| Method | Role | Purpose | Requirements |
|--------|------|---------|--------------|
| FedProx | Aggregation-side heterogeneity | Test if training absorbs threshold personalization benefit | Genuine FedProx semantics |
| Ditto | Model personalization | Test if model personalization makes threshold personalization redundant | Genuine Ditto semantics: distinct global model, persistent client-personalized states, correct proximal objective, NO aggregation of personalized states, separate evaluation |

**Fallback rule:** If genuine Ditto unavailable, use ACTUAL algorithm name (FedRep-AE, FedPer-AE), NEVER call fallback "Ditto"

### 6.4 Centralized Reference (B0)
- Separate centralized AE trained on pooled benign training data
- Pooled benign calibration threshold
- Separate centralized training and evaluation
- **CANNOT use** FedAvg-generated scores labeled as B0
- Purpose: Context for cost of federation, NOT confirmatory claim participation

---

## 7. SCORING CONTRACT

### 7.1 Score Generation
- SAME calibration and test scores reused across B1-B4
- Reconstruction error: Higher = greater anomaly evidence (structurally guaranteed by MSE formula)
- Comparison operator: e > τ → attack; e ≤ τ → benign (FIXED across policies)
- Score semantics: Auditable through reconstruction-error computation path

### 7.2 Score Polarity
- **INVARIANT:** Higher reconstruction error = greater anomaly evidence
- Non-negative by construction (MSE formula)
- Model collapse to constant output: Caught by checkpoint validation checksum
- Perturbation-based polarity test removed as redundant

---

## 8. ELIGIBILITY CONTRACT (CRITICAL)

### 8.1 Canonical Rule
**Minimum benign calibration support: n_k >= 100**

### 8.2 Eligibility Requirements
- Only eligible clients enter primary cross-client CV(FPR) calculation
- Eligibility determined BEFORE test evaluation
- Eligibility IDENTICAL across policies in same comparison
- Must report: total clients, eligible clients, excluded clients, exclusion reasons, eligibility coverage
- Eligibility CANNOT be changed after examining test outcomes

### 8.3 Fallback Rule
- Ineligible client may receive declared deployment fallback ONLY when experiment explicitly studies fallback behavior
- Cannot be SILENTLY included in confirmatory population

---

## 9. METRIC CONTRACT (CRITICAL)

### 9.1 Primary Metric
**CV(FPR) across eligible clients** - Coefficient of Variation of False Positive Rate

### 9.2 Secondary Metrics
- IQR(FPR) - Interquartile range (accompanies CV when mean FPR small)
- Worst-client FPR - Maximum FPR across eligible clients
- Range FPR - Max - min FPR

### 9.3 Control Metrics
- AUROC (detector quality control)
- Macro-F1 (detector quality control)
- Balanced accuracy (detector quality control)
- TPR/Recall (detector quality control)
- P10 Macro-F1 (worst-client performance)
- Worst-client balanced accuracy

**Control Rule:** Unchanged AUROC does NOT invalidate threshold-scope effect; improved AUROC does NOT establish threshold-scope effect

### 9.4 Metric Populations
- **Calibration eligible:** benign_calibration_count >= 100
- **FPR-evaluable:** Additionally requires non-empty benign test denominator
- **Attack-evaluable:** Additionally requires valid per-client attack assignment, at least one held-out attack row
- **Edge-IIoTset distinction:** FPR-evaluable but attack metrics unavailable

---

## 10. EVALUATION CONTRACT

### 10.1 Evaluation Invariants
- Training seed is independent replication unit
- Clients, rows, checkpoints, attack categories, calibration subsamples, cluster initializations, temporal windows are NOT independent replications
- Nested replicates summarized within seed before across-seed inference
- Metrics calculated per client BEFORE cross-client aggregation when valid client identity exists
- Pooled-row metrics may be reported as CONTROLS ONLY, cannot replace client-level operating-point metrics

### 10.2 Confusion Counts
- TN_k, FP_k, TP_k, FN_k from held-out test rows
- Calibration rows NEVER enter reported test metrics
- Higher reconstruction error = greater anomaly evidence (structurally guaranteed)

---

## 11. STATISTICAL ANALYSIS CONTRACT

### 11.1 Independent Unit
**Training seed** is the independent replication unit

### 11.2 Confirmatory Analysis
- 95% BCa confidence interval over ten paired contrasts
- Locked BCa decision rule (specified in Evaluation and Reporting Protocol)
- Wilcoxon signed-rank and matched-pairs rank-biserial correlation are DESCRIPTIVE secondary evidence

### 11.3 Paired Delta
Δ_s = CV(FPR)_{B1,s} - CV(FPR)_{B2,s}

### 11.4 Reporting Requirements
- Report all ten seed-level contrasts
- Report mean or median paired delta (as defined in evaluation protocol)
- Report 95% BCa interval
- Report sign consistency
- Report IQR and range alongside CV to guard against small-denominator distortion
- Report detection-quality controls without treating as primary verdict

### 11.5 Interpretation Rules
- **Confirmatory support:** 95% BCa interval excludes zero in positive direction
- **Directional but inconclusive:** Point estimate positive, interval touches/crosses zero
- **No observed advantage:** Estimate approximately null, interval includes zero
- **Opposite direction:** B2 increases CV(FPR) relative to B1

---

## 12. TEMPORAL CONTRACT

### 12.1 Chronology
- Historical calibration → future recalibration → future evaluation
- Future evaluation CANNOT influence any earlier stage
- Data ordering or generated pseudo-time CANNOT replace real chronology
- NO future-to-history leakage

### 12.2 Temporal Experiment Limits
- One-shot recalibration on verified chronological population ONLY
- Does NOT establish: continuous adaptation, online learning, streaming drift detection, drift-triggered recalibration, concept-drift resolution, production stability

---

## 13. SUPPORTIVE THRESHOLD VARIANTS

### 13.1 Quantile Sensitivity (tau-shrink)
- Test whether conclusions depend on q=0.95 choice
- Pre-specified sensitivity grid
- Alternative quantile CANNOT replace canonical endpoint post hoc

### 13.2 Local-Global Shrinkage
- Formula: τ_k(λ) = λ·τ_k,local + (1-λ)·τ_shared
- Interpretation: λ=0 → shared endpoint; λ=1 → local endpoint; intermediate = partial pooling
- Complete pre-specified lambda curve is result
- Favorable intermediate lambda CANNOT be presented as primary policy unless selection rule fixed without test leakage

### 13.3 Calibration-Size-Aware Shrinkage
- Function: λ = λ(n_k)
- Constraints: Fixed before evaluation; identical across clients apart from n_k; bounded in [0,1]; explicitly reported
- Compared against fixed-lambda endpoints
- NOT a novel statistical-theory claim

### 13.4 Split-Conformal Local Threshold (B2-conf)
- Finite-sample-adjusted local conformal quantile to benign reconstruction errors
- Tests held-out benign coverage
- Does NOT establish: arbitrary client-conditional coverage, validity under unrestricted non-exchangeability, robustness to Byzantine calibration, full conformal DATP contribution, replacement confirmatory endpoint
- Coverage failures, finite-sample granularity, heterogeneous-client limitations remain reportable

---

## 14. FEDERATED THRESHOLD COMPARATOR

### 14.1 B-FedStatsBenign
- DATP-compatible benign-only federated summary-statistics comparator
- Uses benign calibration information ONLY
- Full pooled variance decomposition including between-client mean-shift
- Targets same benign exceedance as DATP quantile
- Protocol locked before result inspection
- Discloses every statistic communicated by client
- Remains shared-threshold comparator
- Primary comparator matched by target exceedance
- Fixed multiplier (k=2, 2.5, 3) is supplementary sensitivity only

### 14.2 Relationship to Laridi et al.
- Original Laridi: Aggregated information from both normal and anomalous validation data
- DATP distinction: Comparator deliberately EXCLUDES anomalous calibration information
- **B-FedStatsBenign is NOT faithful Laridi reproduction**
- CANNOT be called "B-LaridiFaithful"
- Results CANNOT claim reproduction of Laridi et al.
- Difference in calibration contracts MUST be disclosed
- Reserved name "B-LaridiFaithful" for genuinely anomaly-informed implementation (out of scope)

---

## 15. STRESS TESTS

### 15.1 FedProx
- Aggregation-side heterogeneity stress test
- Modifies local optimization with proximal term
- Scientific question: Does heterogeneity-aware training absorb operating-point benefit of threshold personalization?
- Results must be described as TRAINING-SIDE SENSITIVITY
- Results CANNOT be merged with FedAvg confirmatory endpoint
- Requires separate models, score sets, and evaluation

### 15.2 Ditto
- Model-personalization stress test
- Maintains global and persistent client-personalized models regularized toward global state
- Scientific question: Does model personalization make threshold personalization redundant, complementary, or partially absorbed?
- In-paper comparison: One personalized-model family (not broad benchmark)

### 15.3 Naming Discipline
- **Ditto** name ONLY when implementation preserves genuine Ditto semantics
- Genuine Ditto requirements: distinct global model, persistent client-personalized states, correct proximal personalized objective, NO aggregation of personalized states as global, separate evaluation
- Fallback names: FedRep-AE, FedPer-AE (actual algorithm name)
- Fallback CANNOT be called "Ditto"
- Fallback changes scientific comparator and MUST be recorded before results used

### 15.4 Stress-Test Separation
- For every stress-test model: B1, B2, B3, B4 may be recomputed from that model's scores
- Threshold-scope difference may be compared with FedAvg difference
- Result may support: retention, partial absorption, or full absorption
- Result CANNOT alter identity of FedAvg core ladder

---

## 16. EVIDENCE ARCHITECTURE

### 16.1 Sole Confirmatory Evidence
**ONLY ONE endpoint is confirmatory:**
- Regime A (N-BaIoT physical-device regime)
- B1 vs B2 comparison
- CV(FPR) metric
- Ten paired seeds
- Locked BCa decision rule

### 16.2 Evidence Role Hierarchy
| Role | Purpose | Can Rescue Confirmatory? | Notes |
|------|---------|------------------------|-------|
| **Confirmatory** | Establish main journal endpoint | N/A | Only B1-vs-B2 on Regime A |
| **Supportive** | Test robustness of confirmatory interpretation | **NO** | Cannot rescue failed confirmatory |
| **Mechanism** | Explain why/when/for which clients effect appears | **NO** | Cannot rescue failed confirmatory |
| **Threshold variant** | Test modified threshold-estimation rules | **NO** | Cannot rescue failed confirmatory |
| **External validation** | Test transfer beyond N-BaIoT | **NO** | Cannot become second confirmatory |
| **Stress test** | Test training/model changes | **NO** | Outside causal ladder |
| **Boundary condition** | Identify where DATP is weak/infeasible | **NO** | Cannot rescue failed confirmatory |
| **Exploratory** | Generate descriptive evidence | **NO** | Cannot be promoted post hoc |

### 16.3 Honest Negative Evidence
- Null, opposite, and infeasible outcomes remain scientifically meaningful
- MUST be reported rather than hidden or replaced by more favorable analysis
- Supportive analysis CANNOT be promoted to rescue failed confirmatory endpoint
- External dataset CANNOT silently become second confirmatory regime
- Exploratory result CANNOT be rewritten as pre-specified evidence after observation

---

## 17. TERMINOLOGY AND NAMING RULES

### 17.1 Project Names
- **DATP**: Original method and conference identity
- **DATP-Core**: Extended study
- **anchor**: Conference-faithful reference protocol inside DATP-Core
- **Prohibited**: Using "journal" as model, experiment, or scientific method name

### 17.2 Threshold Policy Names
- **B0**: Centralized reference (NOT part of B1-B4 ladder)
- **B1**: Shared threshold (confirmatory anchor)
- **B2**: Per-client threshold (confirmatory comparator)
- **B3**: Family threshold (mechanism baseline)
- **B4**: Cluster threshold (mechanism baseline)

**Prohibition:** Do NOT reuse B0-B4 for shrinkage, conformal variants, summary-statistics comparators, stress-test models, or future methods

### 17.3 Threshold Variant Names
- **Use:** tau-shrink, calibration-size-aware shrinkage, B2-conf, B-FedStatsBenign
- **Do NOT use:** B3-LGS, B5 (retired), Laridi-faithful benign

### 17.4 Statistical Language
- **Use:** CV(FPR), IQR(FPR), worst-client FPR, false-alarm equity, operating-point equity, cross-client FPR dispersion
- **Avoid:** fair model, fair detector, equal treatment, privacy-preserving threshold, robust threshold, optimal threshold (unless formally established)

### 17.5 Novelty Language
- **Do NOT use:** first, novel federated conformal prediction, first personalized threshold, state of the art, universally superior, solves non-IID, guarantees fairness, privacy preserving, deployment ready
- **Reason:** Requires independent evidence beyond this roadmap

---

## 18. CLAIM-LEVEL FRAMING BOUNDARIES

### 18.1 Permitted Central Framing
- A controlled threshold-calibration-scope study
- A study of operating-point reliability under heterogeneous federated IoT clients
- A false-alarm-equity analysis on a fixed anomaly detector
- A journal extension with external, stress-test, and mechanism evidence
- An evaluation of when threshold personalization remains useful

### 18.2 Prohibited Central Framing
- A new federated-learning optimizer
- A complete FL-IDS framework benchmark
- A privacy-preserving security system
- A robust federated-learning defense
- A drift-adaptive production IDS
- A fleet-scale deployment
- A universal thresholding method
- A method that improves every client
- A method that improves global Macro-F1
- A solution to non-IID federated learning

### 18.3 Specific Language Rules

**AUROC:**
- ✅ Permitted: Reported as detector-quality control, expected unchanged when only threshold scope changes
- ❌ Prohibited: "B2 improves AUROC"

**Macro-F1:**
- ✅ Permitted: Threshold personalization may reduce FPR dispersion while producing lower-tail detection trade-off
- ❌ Prohibited: "DATP improves detection performance overall"

**External Validation:**
- ✅ Permitted: Edge-IIoTset provides independent validation of benign operating-point equity under audited sensor-group client definition
- ❌ Prohibited: "DATP generalizes attack detection across Edge-IIoTset clients"

**Temporal:**
- ✅ Permitted: One-shot recalibration evaluated as bounded response to threshold aging under verified chronological split
- ❌ Prohibited: "DATP handles concept drift"

**Privacy:**
- ✅ Permitted: Raw traffic remains local during federated training, but no formal privacy mechanism or guarantee provided
- ❌ Prohibited: "DATP is privacy preserving"

**Deployment:**
- ✅ Permitted: Communication and storage requirements estimated from message content
- ❌ Prohibited: "DATP is lightweight, edge ready, or deployable on constrained devices"

---

## 19. ACCEPTED SCIENTIFIC LIMITATIONS

| Limitation | Acceptance | Disclosure |
|-----------|------------|------------|
| Small natural client population | 9 clients, no fleet-scale inference | Must disclose |
| One external dataset | Edge-IIoTset, no universal generalization | Must disclose |
| Incomplete external attack assignment | Benign equity only, no per-client attack metrics | Must disclose |
| Single temporal family | One-shot, not general drift solution | Must disclose |
| No formal privacy guarantee | Federated locality ≠ formal privacy | Must disclose |
| No hardware evidence | Message sizes ≠ deployment feasibility | Must disclose |
| Threshold trade-offs | May worsen attack sensitivity for some clients | Include in contribution |
| Comparator incompleteness | Two stress tests ≠ full FL benchmark | Must disclose |
| Conformal limitation | B2-conf = empirical diagnostic under bounded assumptions | Must disclose |

---

## 20. EXCLUDED SCIENTIFIC SCOPE

### 20.1 Security
- ❌ Does NOT study adversarial attacks, poisoning, or defensive mechanisms

### 20.2 Formal Privacy
- ❌ Does NOT implement or claim formal privacy protections
- ❌ B4 clustering is NOT a privacy mechanism
- ❌ Threshold-message size is NOT a privacy proof

### 20.3 Deployment Validation
- ❌ Does NOT provide hardware, resource, network-traffic, or production deployment validation
- ✅ May estimate communication/storage from message content
- ❌ Such estimates must NOT be called deployment measurements

### 20.4 Fleet Scale
- ❌ Does NOT claim fleet-scale validation above 100 clients
- ❌ Synthetic client counts do NOT establish real fleet-scale deployment

### 20.5 Drift Handling
- ❌ Does NOT provide continuous adaptation, online recalibration, or autonomous drift detection

### 20.6 Benchmarking Scope
- ❌ NOT an exhaustive benchmark of FL, personalization, clustering, anomaly detection, privacy, or IDS
- ❌ FedBN excluded (would change locked AE architecture)

### 20.7 Conformal Scope
- ❌ B2-conf does NOT expand into federated conformal benchmarking, method development, adversarial conformal prediction, or online adaptation

---

## 21. INCLUDED SCIENTIFIC SCOPE

### 21.1 External Validation
- ✅ One external IoT/IIoT dataset (Edge-IIoTset) tests benign operating-point equity transfer beyond N-BaIoT

### 21.2 Federated Threshold Comparison
- ✅ One benign-only summary-statistics comparator (B-FedStatsBenign) tests threshold personalization vs distributed shared-threshold alternative

### 21.3 Training-Side Robustness
- ✅ Two external stress tests: FedProx, Ditto

### 21.4 Threshold-Estimation Depth
- ✅ Quantile-level sensitivity
- ✅ Local-global shrinkage
- ✅ Calibration-size-aware shrinkage
- ✅ Bounded split-conformal local-threshold diagnostic

### 21.5 Temporal Boundary
- ✅ One chronological, one-shot recalibration experiment

### 21.6 Mechanism Analysis
- ✅ Bounded mechanism work: family/cluster granularity, cluster stability, per-client score geometry, heterogeneity-benefit association, threshold movement vs FPR/TPR trade-off

### 21.7 Hard Scope Limits
- ✅ One new IoT dataset (Edge-IIoTset)
- ✅ Three external comparator families: FedProx, one model-personalization method, one benign-only federated threshold comparator
- ✅ Four threshold-extension families
- ✅ One temporal-recalibration family
- ✅ Pre-specified mechanism programme
- ✅ Ten paired seeds for confirmatory endpoint

---

## 22. EXPERIMENT EXECUTION INVARIANTS

### 22.1 Paired Design
**Within each seed, policies compared in same experiment must receive:**
- Same trained model (for fixed-detector ladder)
- Same client population
- Same calibration records before declared subsampling
- Same held-out evaluation records
- Same eligibility rule
- Same metric implementation

### 22.2 Replication Unit
- **Independent unit:** Training seed
- **Non-independent:** Clients, records, checkpoints, attack categories, calibration subsamples, cluster initializations, temporal windows

### 22.3 Negative Result Discipline
**Every mandatory experiment is reportable when it produces:**
- Strong expected effect
- Weak effect
- Null effect
- Reversed effect
- Unstable estimates
- Infeasibility result

**PROHIBITION:** No experiment may be removed because result is unfavorable

---

## 23. REGIME DEFINITIONS (FROM ROADMAP SECTIONS 1487+)

### 23.1 Regime A - N-BaIoT Physical-Device Anchor
- **Role:** Confirmatory regime
- **Dataset:** N-BaIoT
- **Clients:** 9 physical devices
- **Preprocessing:** FEDERATED_CLIENT_LOCAL_STANDARD (StandardScaler, client-local, train-only)
- **B3 Availability:** ✅ Available (defensible device family taxonomy)
- **Purpose:** Primary confirmatory evidence

### 23.2 Regime B-a, B-b, C, D, D-temporal
- **Status:** [TO BE EXTRACTED FROM SECTIONS 1487-1713]
- **Purpose:** Supportive robustness and boundary experiments

### 23.3 Regime D-temporal
- **Role:** Temporal external regime
- **Purpose:** One-shot threshold recalibration on verified chronological population

---

## 24. IMPLEMENTATION IMPLICATIONS

### 24.1 Required Implementations
Based on journal requirements, the following MUST be implemented:

**Core Causal Ladder:**
- [ ] B1 (Shared threshold) - confirmatory anchor
- [ ] B2 (Per-client threshold) - confirmatory comparator  
- [ ] B3 (Family threshold) - mechanism baseline
- [ ] B4 (Cluster threshold) - mechanism baseline with fingerprint: mean, std, skewness, p95

**Preprocessing:**
- [ ] FEDERATED_CLIENT_LOCAL_STANDARD (StandardScaler, client-local)
- [ ] FEDERATED_POOLED_MIN_MAX (MinMaxScaler, pooled) - supportive only
- [ ] CENTRALIZED_POOLED_MIN_MAX (MinMaxScaler, pooled) - centralized reference

**Training:**
- [ ] FedAvg with 1 local epoch/round, full participation
- [ ] FedProx stress test
- [ ] Ditto stress test (or fallback with proper naming)
- [ ] Centralized reference (B0)

**Threshold Variants:**
- [ ] Quantile sensitivity (tau-shrink)
- [ ] Local-global shrinkage
- [ ] Calibration-size-aware shrinkage
- [ ] B2-conf (split-conformal)
- [ ] B-FedStatsBenign comparator

**Datasets:**
- [ ] N-BaIoT (Regime A) - confirmatory
- [ ] CICIoT2023 - boundary
- [ ] Edge-IIoTset - external validation
- [ ] Controlled heterogeneity regime

### 24.2 Required Scientific Properties

**Fixed-Detector Contract:**
- [ ] Same model state across B1-B4
- [ ] Same preprocessing state across B1-B4
- [ ] Same calibration/test scores across B1-B4
- [ ] Only threshold scope differs

**Benign-Only Calibration:**
- [ ] No attack data in threshold fitting
- [ ] No attack data in policy parameter selection
- [ ] Complete isolation from attack-labelled information

**Preprocessing Lock:**
- [ ] Per-client StandardScaler for confirmatory
- [ ] Separate protocol identities cannot be mixed
- [ ] No attack label influence on preprocessing

**Checkpoint Discipline:**
- [ ] Locked non-test selection rule
- [ ] Same checkpoint for B1-B4
- [ ] No checkpoint selection based on test metrics

**Eligibility:**
- [ ] n_k >= 100 benign calibration samples
- [ ] Same eligibility across compared policies
- [ ] Eligibility determined before test evaluation

**Metrics:**
- [ ] CV(FPR) as primary metric
- [ ] Per-client metrics before aggregation
- [ ] Attack metrics unavailable where attack assignment invalid

---

## 25. AUDIT GUIDANCE

### 25.1 Scientific Correctness Priority

**RULE: Scientific correctness OUTRANKS reducing LOC.**

Before classifying any code as dead, missing wiring, or simplifying:
1. **FIRST** check if journal requires the responsibility
2. **THEN** verify if implementation matches journal requirements
3. **FINALLY** determine appropriate classification

### 25.2 Critical Scientific Boundaries

**The following violations are FIX_SCIENTIFIC_DRIFT:**
- Any attack data in calibration
- Any mixing of preprocessing protocol identities
- Any policy-specific retraining in B1-B4 ladder
- Any test data in threshold selection
- Any alteration of scores between B1-B4
- Any violation of fixed-detector contract
- Any misrepresentation of confirmatory endpoint

### 25.3 Classification Rules for Audit

**DELETE_DEAD:** Only if BOTH:
- Unreachable from production roots
- Scientifically unnecessary (not required by journal)

**WIRE_REQUIRED:** Only if BOTH:
- Scientifically required by journal
- Implementation exists but is disconnected

**FIX_INCOMPLETE:** Only if BOTH:
- Scientifically required by journal
- Implementation incomplete or incorrect

**FIX_SCIENTIFIC_DRIFT:** Only if:
- Implementation violates scientific requirements
- Regardless of architectural cleanliness

---

## 26. NEXT STEPS

### 26.1 Journal Reading Completion
- [ ] Complete reading of experimental regimes (sections 1487-1713)
- [ ] Complete reading of supportive experiments (sections 1825-2483)
- [ ] Complete reading of evaluation protocol (sections 2831-3543)

### 26.2 Contract Validation
- [ ] Verify all extracted requirements against roadmap
- [ ] Check for contradictions in extracted requirements
- [ ] Validate completeness of scientific contract

### 26.3 Codebase Audit Preparation
- [ ] Use this contract as reference for all audit decisions
- [ ] Cross-reference every finding against contract
- [ ] Validate scientific correctness before architectural changes

---

## 27. DOCUMENT STATUS

**Current Status:** Comprehensive extraction of core scientific requirements  
**Completion Estimate:** ~80% (major sections complete, some regime details pending)  
**Confidence:** High for core requirements, medium for regime-specific details  
**Last Updated:** 2026-08-08  
**Next Review:** Complete remaining journal sections

---

## ACKNOWLEDGMENT

This document is the **authoritative reference** for all DATP-Core audit decisions. Every classification, wiring decision, dead-code determination, and architectural recommendation must first be validated against this contract.

**NO code should be classified, wired, simplified, or deleted without first consulting this contract to verify scientific requirements.**

---

*Generated from docs/Journal_Extension_Master_Roadmap.md - the single research document defining DATP-Core's causal question, threshold policies, datasets, experiments, metrics, statistical analysis, and interpretation boundaries.*