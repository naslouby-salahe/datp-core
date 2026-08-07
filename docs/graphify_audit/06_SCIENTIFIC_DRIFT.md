# 06 — Scientific Drift Audit

Verification of actual runtime behavior against journal contract. Scientific correctness outranks architecture.

---

## VERIFIED CORRECT

### Fixed-Detector Causal Contract
- **Status:** LIVE_AND_CORRECT
- FedAvg training produces fixed model per seed
- Same preprocessing state shared across B1-B4
- `validate_fixed_score_controls` enforces identical scores across threshold methods
- Training directory layout excludes threshold_method from key → structural score reuse
- AUROC identity check enforced
- Per-policy retraining/checkpoint selection rejected at protocol level

### Benign-Only Calibration
- **Status:** LIVE_AND_CORRECT
- `reject_non_benign_labels` (calibration/eligibility.py:84) enforced at calibration construction
- `dispatch_federated_threshold` validates MINIMUM_BENIGN_SUPPORT (dispatch.py:112-118)
- No attack label enters threshold fitting, quantile selection, eligibility, checkpoint selection, or comparator tuning

### Calibration/Evaluation Isolation
- **Status:** LIVE_AND_CORRECT
- Split construction places attack rows in evaluation partition only (splits.py:140+)
- Temporal split enforces forward-only chronology (splits.py:186+)
- `calibration ∩ evaluation = ∅` structurally enforced

### Preprocessing Identity
- **Status:** LIVE_AND_CORRECT
- Confirmatory FEDERATED_CLIENT_LOCAL_STANDARD: StandardScaler, client-local fit, train-only
- Fit scope, constant-feature rule, unclipped output all verified
- skops persistence with trusted estimators only
- Tolerance 1e-12

### Threshold Policies
- **Status:** LIVE_AND_CORRECT
- B1: arithmetic mean of local quantiles (shared.py:170) ✓
- B2: per-client local quantile (local.py:54) ✓
- B3: family mean of member local thresholds (family.py:188) ✓
- B4: cluster mean, fingerprint (mean, std ddof=0, skew bias=True, p95), K=3 (cluster.py:246-313) ✓
- All 10 FederatedThresholdMethod values have exhaustive dispatch ✓

### Eligibility
- **Status:** LIVE_AND_CORRECT
- n_k >= 100 enforced (MINIMUM_BENIGN_SUPPORT = CalibrationSize(100))
- Eligibility determined before test evaluation
- Identical across compared policies

### CV(FPR) Computation
- **Status:** LIVE_AND_CORRECT
- ddof=0 (descriptive population) ✓
- No epsilon stabilizer ✓
- Zero mean → UNDEFINED with ZERO_MEAN reason ✓
- Unweighted by client row count ✓

### Checkpoint Selection
- **Status:** LIVE_AND_CORRECT
- FIXED_TERMINAL_MAXIMUM_ROUND = 200 enforced ✓
- Candidates {25, 50, 75, 100, 125, 150, 200} all saved ✓
- Non-terminal candidates = stability evidence only ✓
- No test-data selection ✓
- Same round across regimes/policies ✓

### FedAvg Training
- **Status:** LIVE_AND_CORRECT
- Sample-count-weighted mean aggregation ✓
- 1 local epoch per round ✓
- Full client participation ✓
- Deterministic (seeded) ✓

### FedProx Stress Test
- **Status:** LIVE_AND_CORRECT
- Separate protocol with proximal term ✓
- Frozen coefficient grid {0.001, 0.01, 0.1, 1.0} ✓
- FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS selection (training loss at round 200) ✓
- Outside core causal ladder ✓

### Ditto Personalization
- **Status:** LIVE_AND_CORRECT
- Genuine Ditto semantics confirmed:
  - Distinct global model ✓
  - Persistent per-client personalized states ✓
  - Correct proximal personalized objective ✓
  - Personalized states never aggregated into global ✓
  - 2×2 core: FedAvg/Ditto × B1/B2 ✓

### Centralized Reference (B0)
- **Status:** LIVE_AND_CORRECT (implementation) / DISCONNECTED (wiring)
- Independently trained (CENTRALIZED_POOLED_MIN_MAX, separate from federated) ✓
- Pooled benign threshold ✓
- Not consuming federated checkpoints ✓
- But unreachable from CLI (see WR-001)

### Scoring Semantics
- **Status:** LIVE_AND_CORRECT
- Per-row MSE, higher = more anomalous ✓
- Structurally guaranteed non-negative ✓
- Perturbation-based empirical polarity removed (as journal requires) ✓

### BCa Bootstrap
- **Status:** LIVE_AND_CORRECT
- Resamples paired seed deltas ✓
- Arithmetic mean statistic ✓
- Jackknife acceleration ✓
- 10k bootstrap replicates ✓

### Confirmatory Decision Rule
- **Status:** LIVE_AND_CORRECT
- SUPPORTED iff 95% BCa lower bound > 0 ✓
- Δ = shared_minus_local ✓
- Wilcoxon signed-rank = secondary only ✓

### B-FedStatsBenign
- **Status:** LIVE_AND_CORRECT
- Full pooled variance = within + between ✓
- Between-client mean-shift term NOT omitted ✓
- Benign-only ✓
- Between ratio computed ✓

### Dataset Boundaries
- **Status:** LIVE_AND_CORRECT
- N-BaIoT: 9 physical devices = natural clients ✓
- CICIoT2023: file-defined pseudo-clients, device-aware wording prohibited ✓
- Edge-IIoTset: 10 sensor groups, attack-sensitive metrics typed UNAVAILABLE ✓
- B3 omitted for Edge-IIoTset ✓

---

## SCIENTIFIC DRIFT — NONE FOUND

After auditing all core algorithms, threshold policies, evaluation metrics, statistical procedures, preprocessing, checkpoint selection, and dataset boundaries:

**No scientific drift detected.** The implementation faithfully executes the journal contract.

---

## IMPLEMENTATION GAPS (NOT DRIFT)

These are wiring/execution gaps, not scientific drift:

| Gap | Detail |
|-----|--------|
| B0 unreachable | Centralized ref implemented but not wired to CLI |
| 15 experiments unregistered | Declared but no workflow modules |
| Dead eval diagnostics | Conformal, estimation, communication, operational metrics never produced |
| Smoke isolation broken | External/Ditto/Temporal write to production OUTPUTS_ROOT |
| Report re-executes training | Ditto/Temporal report re-runs full pipeline |

These are infrastructure/wiring issues. The scientific logic, when it runs, is correct.
