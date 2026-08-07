# 00 — Journal Contract

Derived from `docs/Journal_Extension_Master_Roadmap.md` (read complete, 2026-08-07).

## Scientific Identity

DATP-Core is a controlled study of **threshold-calibration scope** in federated IoT anomaly detection.

**Core question:** When heterogeneous IoT clients share one frozen federated anomaly detector, how does the scope of benign threshold calibration affect the distribution of false-alarm burden across clients?

**Not:** which model or FL algorithm is best.

**Primary object of interest:** cross-client false-positive-rate dispersion (`CV(FPR)`).

## Causal Contract (Section 2)

### Fixed elements per regime/seed:
- Model family (autoencoder)
- Architecture (except input dim matching dataset features)
- FedAvg training algorithm
- 1 local epoch per round
- Full client participation
- Optimizer and hyperparameters
- Preprocessing/normalization semantics
- Split semantics
- Round budget and checkpoint candidates
- Checkpoint-selection rule
- Seed cohort
- Scoring procedure
- Client eligibility
- Test population
- Metric definitions

### Sole manipulated variable:
`threshold_calibration_scope` ∈ {shared, physical_device_family, data_driven_client_cluster, individual_client}

### Prohibited in core ladder:
- Retraining AE per policy
- Independent checkpoint per policy
- Attack-labelled threshold selection
- Policy parameter from test outcomes
- Changing eligible clients between policies
- Removing unfavorable clients
- Treating FedProx/personalization as threshold-scope condition
- Replacing failed B1-vs-B2 with B4/shrinkage/conformal

## Threshold Policies (Sections 4, 5)

### B0 — Centralized reference (NOT in federated ladder)
- Centralized AE on pooled benign data
- Pooled benign calibration threshold
- Separate centralized training and evaluation

### B1 — Shared threshold (confirmatory anchor)
- Each eligible client computes local benign q-quantile
- Server: arithmetic mean of local quantiles
- Canonical q = 0.95
- Every eligible client uses same threshold

### B2 — Local/per-client threshold (confirmatory comparator)
- Each eligible client deploys own benign q-quantile
- q = 0.95
- Primary comparator for confirmatory B1-vs-B2

### B3 — Family threshold (mechanism baseline)
- One threshold per physical-device family
- Mean of eligible local thresholds in family
- Available ONLY with defensible family taxonomy (N-BaIoT)
- Unavailable: CICIoT2023, Edge-IIoTset

### B4 — Cluster threshold (mechanism)
- Taxonomy-free, data-driven client clusters
- Fingerprint: mean(error), std(error), skewness(error), p95(error)
- Canonical K = 3
- Cluster threshold = mean of member local thresholds
- NOT model clustering, privacy mechanism, or new algorithm

### Supportive variants (outside B1-B4 identity):
- Quantile sensitivity: q ∈ {0.90, 0.95, 0.975, 0.99}
- Local-global shrinkage: τ_k(λ) = λ·τ_local + (1-λ)·τ_shared, λ ∈ {0.00, 0.25, 0.50, 0.75, 1.00}
- Calibration-size-aware shrinkage: λ = λ(n_k)
- B2-conf: split-conformal local threshold, α = 0.05

### B-FedStatsBenign — Federated summary-statistics comparator
- Benign-only: count, mean, variance per client
- Full pooled variance decomposition (within + between)
- Matched target exceedance 1-q
- NOT Laridi-faithful (excludes anomalous validation data)

## Training-Side Stress Tests (Section 7)

### FedProx
- Proximal coefficient grid: μ ∈ {0.001, 0.01, 0.1, 1.0}
- Primary μ selected via `FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS`
- Separate from FedAvg core ladder
- Results = training-side sensitivity, not confirmatory

### Ditto (model personalization)
- Must preserve genuine Ditto semantics
- Global + persistent client-personalized models
- Personalized states never aggregated as global
- 2×2 core: FedAvg/Ditto × B1/B2
- Absorption bands defined for Δ comparison
- Fallback naming if Ditto can't be implemented: FedRep-AE, FedPer-AE

## Calibration and Evaluation (Section 3)

### Benign-only calibration
- Attack-labelled records NEVER influence: thresholds, quantiles, eligibility, checkpoint selection, comparator tuning, shrinkage, conformal significance, cluster count, cluster features, external client construction

### Calibration/evaluation separation
- calibration ∩ evaluation = ∅
- Temporal: historical → future recalibration → future evaluation (no backwards leakage)

### Client eligibility
- n_k >= 100 benign calibration samples
- Determined before test evaluation
- Identical across compared policies
- Must report: total, eligible, excluded, reasons, coverage

### Primary operating-point concern
- `CV(FPR)` across eligible clients
- `ddof = 0` (descriptive population)
- No epsilon stabilizer
- `CV(FPR) = undefined` when mean(FPR) = 0
- Absolute dispersion: IQR, Range, WorstFPR

### Model-quality controls (NOT verdict)
- AUROC (must be identical across B1-B4 up to tolerance)
- Macro-F1, Balanced Accuracy, TPR, P10 Macro-F1
- Worst-client BA

## Preprocessing Lock (Section 2.2.1)

### Confirmatory: FEDERATED_CLIENT_LOCAL_STANDARD
- StandardScaler (with_mean=True, with_std=True)
- Fit scope: client-local, benign train only
- Transform-only: calibration, evaluation, future recalibration
- Constant-feature: zero scale → unit scale, zero-centered
- Unclipped output
- skops persistence, trusted estimators only
- Tolerance: 1e-12

### Supportive: FEDERATED_POOLED_MIN_MAX
- MinMaxScaler
- Fit: pooled benign training rows
- NOT confirmatory

### Centralized: CENTRALIZED_POOLED_MIN_MAX
- MinMaxScaler
- Fit: pooled centralized benign train
- Independent of federated states

### Missing-value policy (all datasets):
- No imputation, zero-fill, clipping, capping, infinity replacement
- N-BaIoT non-finite features: fail validation
- CICIoT2023: outcome-blind finite-feature + recognized-label gate
- Edge-IIoTset: exclude non-finite rows with provenance
- Attack labels never influence preprocessing fit
- No zero-fill fabrication for empty train

## Datasets and Regimes (Sections 9, 4 of catalogue)

### Regime A — N-BaIoT physical-device anchor (CONFIRMATORY)
- 9 physical devices = 9 federated clients
- Natural device-family taxonomy supports B3
- Supports: B0-B4, all threshold variants, FedProx, Ditto, all mechanism analyses
- Limitation: small client count (9)

### Regime B-a — CICIoT2023 file-defined boundary
- 63 file-defined pseudo-clients
- NO verified physical-device mapping
- Supports: B0, B1, B2, B4, JS divergence, descriptive
- B3 unavailable
- Device-aware wording PROHIBITED
- Raw-fidelity canonical artifact with lossless gate

### Regime C — Controlled N-BaIoT heterogeneity sweep
- 20 synthetic Dirichlet clients
- α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}
- Supports: B1, B2, B4
- B3: only if synthetic partition preserves family taxonomy

### Regime D — Edge-IIoTset external benign-equity validation
- 10 sensor-group clients (static)
- 33-dim numeric model input (canonical ordered columns)
- AE architecture: (33, 25, 17, 11, 8, 11, 17, 25, 33)
- Supports: B1, B2, B4, B-FedStatsBenign, quantile sensitivity
- B3 omitted (no family taxonomy)
- Attack-sensitive metrics UNAVAILABLE (attack traffic in attacker subnet)
- Modbus: valid for static, excluded from temporal (timestamp = address literals)

### Regime D-temporal — One-shot recalibration
- 9 temporal groups (Modbus excluded)
- Chronological split: 55/15/10/20 (train/calib/recalib/eval)
- States: static reference, frozen future, recalibrated future
- drift_excess, recovered_amount, recovery_ratio

## Checkpoint Protocol (Section 13)

- Train to max 200 rounds
- Candidates: {25, 50, 75, 100, 125, 150, 200}
- Primary: round 200 (`FIXED_TERMINAL_MAXIMUM_ROUND`)
- Same round number across regimes/policies
- B0 applies same rule independently
- Forbidden: test-AUROC selection, attack-label selection, policy-specific selection

## Confirmatory Experiment (Section 5 of catalogue)

### Sole confirmatory: Regime A B1-vs-B2 on CV(FPR)
- 10 paired seeds
- Δ_s = CV(FPR)_{B1,s} - CV(FPR)_{B2,s}
- Point estimate: mean of 10 Δ_s
- 95% BCa bootstrap CI over paired seed deltas
- Sign consistency (descriptive)
- Decision: CI excludes zero in positive direction → confirmatory support
- Wilcoxon signed-rank + matched-pairs rank-biserial = secondary

### Prohibited:
- Checkpoint selection from this result
- Replacement by B4, shrinkage, B2-conf
- Removal of unfavorable seeds
- Claim that B2 improves overall detection

## Evidence Architecture (Section 8)

| Role | Scope |
|------|-------|
| Confirmatory | Regime A, B1-vs-B2, CV(FPR), 10 seeds, BCa |
| Supportive | Shared-threshold construction sensitivity, quantile sensitivity, heterogeneity sweep |
| Mechanism | Cluster/family granularity, score distributions, heterogeneity-benefit association, threshold movement vs harm |
| Threshold variant | Shrinkage, size-aware shrinkage, B2-conf |
| External validation | Regime D benign-equity |
| Stress test | FedProx, Ditto |
| Boundary condition | CICIoT2023 file-level, calibration-size ablation, temporal |
| Exploratory | Robust cluster-median, additional equity indices, extended uncertainty |

Supportive analysis CANNOT rescue failed confirmatory endpoint.
Exploratory CANNOT be rewritten as pre-specified.

## Statistical Rules (Section 11)

- Training seed = independent replication unit
- Clients/rows/checkpoints/windows NOT independent
- Nested replicates summarized within seed before across-seed inference
- No multiplicity correction on single confirmatory endpoint
- Secondary p-values: Holm correction within pre-defined families
- Association analyses: Spearman correlation, declared regression, associative NOT causal language

## Score Semantics

- Higher reconstruction error ≡ stronger anomaly evidence
- Structurally guaranteed by MSE formula (non-negative)
- Perturbation-based polarity experiment removed as redundant

## Naming Rules (Section 12)

- B0-B4 reserved for threshold policies only
- B5 retired, must not reappear
- B-FedStatsBenign (NOT B-LaridiFaithful)
- Ditto name ONLY for genuine Ditto implementation
- tau-shrink, calibration-size-aware shrinkage, B2-conf
- Regime A, B-a, C, D, D-temporal

## Excluded Scope (Section 11)

- Security attacks/defenses
- Formal privacy
- Deployment validation (hardware/resources)
- Fleet scale (>100 clients)
- Full drift handling
- Broad FL benchmarking
- FedBN (BatchNorm would change locked AE architecture)
- Federated conformal breadth beyond B2-conf

## Limitations (Section 14)

- Small natural client population (9 devices)
- One external dataset (Edge-IIoTset)
- Incomplete external attack assignment
- Single temporal family
- No formal privacy guarantee
- No hardware evidence
- Threshold trade-offs (FPR equity may worsen attack sensitivity)
- Comparator incompleteness (one aggregation + one personalization stress test)
- Conformal limitation (empirical diagnostic, not conditional coverage)
