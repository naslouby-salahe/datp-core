# DATP-Core Scientific Contract Ledger
(Extracted from docs/Journal_Extension_Master_Roadmap.md, full read 2026-08-07. This is the sole authority for scientific judgments in this audit. Any conflict between source code/tests and this ledger is resolved in favor of this ledger, per CLAUDE.md authority order.)

## 1. Programme identity
- Causal question: does threshold_calibration_scope (shared vs per-client vs family vs cluster) change cross-client FPR dispersion, detector held fixed. NOT a model-selection study.
- Sole confirmatory endpoint: Regime A (N-BaIoT, 9 physical devices), B1 vs B2, CV(FPR), 10 paired seeds, locked BCa decision rule (§5.1, §11 evaluation doc).
- Primary metric: CV(FPR) across eligible clients. AUROC = model-quality control only, must be IDENTICAL across B1-B4 (fixed scores) up to numerical tolerance — any policy-dependent AUROC difference = bug (mismatched scores/model).

## 2. Fixed vs manipulated elements (core B1-B4 ladder)
FIXED: model family/architecture (except input dim), FedAvg, E=1 local epoch, full participation, optimizer/hyperparams, preprocessing/normalization, split semantics, round budget + checkpoint rule, seed cohort, scoring procedure, eligibility, test population, metric defs.
MANIPULATED (sole variable): threshold_calibration_scope in {shared, physical_device_family, data_driven_client_cluster, individual_client}.
FORBIDDEN: per-policy retraining, per-policy checkpoint selection, thresholds from attack-labelled data, policy choice via held-out F1/TPR/AUROC/BA/CV(FPR), changing eligible clients between policies, dropping unfavorable clients, treating FedProx/personalization as a threshold-scope condition, promoting B4/shrinkage/conformal to rescue a failed B1-vs-B2 result.

## 3. Preprocessing lock (part of fixed detector state)
- Primary confirmatory (`FEDERATED_CLIENT_LOCAL_STANDARD`): StandardScaler, with_mean=True/with_std=True, fit scope = client-local benign train partition only; calib/eval/recalibration transform-only; zero-scale -> unit scale + zero-centered column; unclipped; skops persistence, trusted-estimator-only; serialization tolerance 1e-12.
- Supportive (not confirmatory): `FEDERATED_POOLED_MIN_MAX` — MinMaxScaler, pooled benign train fit scope.
- Centralized reference: `CENTRALIZED_POOLED_MIN_MAX` — independent fitted state (never reuses federated states), MinMaxScaler, pooled benign train, zero-range->zero.
- No imputation/zero-fill/clip/cap/inf-replace/label-inference anywhere. N-BaIoT non-finite -> validation failure (not filled). CICIoT2023 eligibility = outcome-blind finite-feature + recognized-label gate, canonical rows lossless. Edge-IIoTset non-finite retained-numeric rows excluded from model input with provenance.
- No identity/no-scaling transform for confirmatory multi-feature AE input.
- Distinct preprocessing protocol identities must never be silently mixed within one confirmatory ladder.

## 4. Threshold policies (canonical identifiers — locked, must not be reused/renamed)
- B0: centralized reference. Independent centralized AE, pooled benign threshold, pooled MinMax preprocessing, own training+eval. NOT part of federated ladder. A FedAvg model with a pooled threshold is NOT B0.
- B1: shared. Each eligible client's local benign q=0.95 quantile; server threshold = arithmetic MEAN of local quantiles (NOT the pooled exact quantile — must not be described as such).
- B2: per-client/local. Each eligible client's own q=0.95 quantile. Confirmatory comparator vs B1.
- B3: family. One threshold per physical-device family = mean of eligible local thresholds in family. Requires defensible, outcome-independent, stable/auditable family taxonomy. Available: Regime A only (natively); NOT Regime C unless partition preserves family mapping; omitted for Edge-IIoTset and CICIoT2023 pseudo-clients. Mechanism baseline, not confirmatory.
- B4: cluster (taxonomy-free). Fingerprint = [mean(error), std(error), skewness(error), p95(error)] per client from BENIGN calibration errors only. Canonical K=3 (K=9 exploratory/supplementary only, cannot be promoted post hoc). Cluster threshold = mean of member eligible local thresholds. NOT model clustering, NOT clustered FL training, NOT a privacy mechanism, NOT confirmatory.
- Ladder interpretation: B1 (federation-wide) -> B3 (per family) -> B4 (per data-driven cluster) -> B2 (per client), increasing granularity; B3/B4 need not sit strictly between B1 and B2 numerically.
- Reserved/forbidden names: B3-LGS, B5 (retired, must not reappear), "Laridi-faithful benign", generic "personalized model v2"/"hybrid personalization" when a real algorithm is implemented.

## 5. Supportive threshold variants (never confirmatory, cannot be promoted post hoc)
- Quantile sensitivity: q in {0.90, 0.95, 0.975, 0.99}; canonical q=0.95 fixed regardless of observed ordering.
- Shared-threshold construction controls (supportive only, do not replace B1): exact pooled quantile; sample-weighted-by-eligible-n construction.
- Local-global shrinkage: tau_k(lambda) = lambda*tau_local + (1-lambda)*tau_shared; lambda grid {0.00,0.25,0.50,0.75,1.00}; full curve is the result, no single lambda selected post hoc from test data.
- Calibration-size-aware shrinkage: lambda(n_k) fixed pre-evaluation, monotone-by-default, bounded [0,1], identical functional form across clients, compared vs fixed-lambda curves.
- B2-conf: split-conformal local threshold on benign errors, alpha = 1-q, main setting alpha=0.05. Supportive diagnostic; does not prove universal client-conditional coverage; coverage misses reported not hidden; never confirmatory.

## 6. Federated threshold comparator
- `B-FedStatsBenign`: DATP-compatible benign-only federated summary-statistics comparator. Uses count n_k, mean mu_k, variance sigma_k^2 per client, benign-only. Full pooled-variance decomposition MUST include between-client mean-shift term (never omit `between`). Target exceedance matched to 1-q (not F1-tuned). Locked protocol before result inspection; discloses every communicated statistic.
  - mu_global = sum(n_k*mu_k)/sum(n_k); within = sum(n_k*sigma_k^2)/sum(n_k); between = sum(n_k*(mu_k-mu_global)^2)/sum(n_k); sigma^2_global = within+between; between_ratio = between/(within+between), undefined if denom 0.
  - A fixed multiplier k in {2.0,2.5,3.0} is supplementary sensitivity only.
  - MUST NOT be called `B-LaridiFaithful` (that name reserved for an anomaly-informed reproduction, out of scope). Must not claim faithful Laridi reproduction.

## 7. Training-side stress tests (OUTSIDE the B1-B4 causal ladder — must never merge)
- FedProx: aggregation-side heterogeneity stress test. mu grid {0.001,0.01,0.1,1.0} pre-registered/frozen before outcome inspection; mu=0 is FedAvg-equivalent, NOT a FedProx condition. Primary mu selection rule is LOCKED: `FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS` — among grid, pick mu with lowest population-weighted aggregate federated training loss at terminal checkpoint round 200, averaged across confirmatory seed cohort on Regime A; ties -> smallest mu; uses ONLY training-loss trajectories, NEVER test data/attack labels/CV(FPR)/threshold outcomes/Regime D results. FedProx results cannot enter core causal ladder; B1-B4 may be recomputed from FedProx scores as a separate absorption analysis only.
- Ditto: model-personalization stress test. Requires genuine Ditto semantics: distinct global model, persistent per-client personalized states, correct proximal personalized objective, personalized states never aggregated as if global, separate evaluation. If genuine Ditto is infeasible, fallback must be named for what it actually is (e.g. FedRep-AE, FedPer-AE) — NEVER called Ditto. 2x2 interpretable core: FedAvg+B1, FedAvg+B2, Ditto+B1, Ditto+B2. Absorption measure: Delta_FedAvg = CV(FPR)[FedAvg+B1]-CV(FPR)[FedAvg+B2]; Delta_Ditto = CV(FPR)[Ditto+B1]-CV(FPR)[Ditto+B2]. Bands: Delta_Ditto>=0.75*Delta_FedAvg -> still strongly useful; 0.25<=..<0.75 -> partial absorption; <0.25 -> largely absorbed; if CV(FPR)[Ditto+B1] within 0.05 of CV(FPR)[FedAvg+B2] -> personalization = alternative equity route.

## 8. Evidence architecture / claim tiers
Roles: confirmatory (only Regime A B1-vs-B2 CV(FPR)) / supportive robustness / mechanism analysis / threshold variant / external validation / aggregation stress test / model-personalization stress test / applicability boundary / temporal boundary / exploratory. A supportive/mechanism/exploratory result can NEVER rescue a failed confirmatory endpoint or be silently promoted. Null/negative/mixed results must be reported, not suppressed or replaced.

## 9. Dataset/regime boundaries
- Regime A (N-BaIoT): 9 physical devices = natural clients. ONLY confirmatory regime. Supports B0-B4, all supportive/mechanism/stress-test work. All 9 clients always shown, no filtering.
- Regime B-a (CICIoT2023): 63 file-defined pseudo-clients, NO verified physical-device mapping. Applicability-boundary role ONLY. Prohibited: device-level generalization claims, physical-client equity claims, temporal claims, "device-aware" wording. Eligibility gate: outcome-blind finite-feature + recognized-label; canonical rows lossless; no impute/fill/clip/infer. Supports B0,B1,B2,B4 (no B3). Null B1-vs-B2 result here is scientifically expected/useful (near-homogeneous clients), not a failure.
- Regime C (controlled Dirichlet N-BaIoT sweep): 20 synthetic clients from N-BaIoT analysis population, locked Dirichlet procedure. alpha in {0.1,0.3,0.5,1.0,10.0,IID}. Policies B1,B2,B4 (B3 not automatically available — only if partition preserves family taxonomy). Supportive heterogeneity sensitivity, not confirmatory; non-monotonicity acceptable; does not replace Regime A.
- Regime D (Edge-IIoTset external): 10 benign sensor-group folders = static clients (Modbus valid for static benign eval, excluded only from temporal population due to unusable frame.time). Eligible-benign coverage = 1.0 under n_k>=100. Model-input schema: 33 finite-numeric columns (exact list locked, see roadmap §4.4), architecture (33,25,17,11,8,11,17,25,33) — must preserve N-BaIoT encoder depth/symmetry/compression ratios; padding to 115-dim or reusing 115-input weights PROHIBITED. Supports B1,B2,B4,B-FedStatsBenign,quantile sensitivity,calibration-size/shrinkage,FedProx,Ditto where feasible. B3 OMITTED (no family taxonomy). Attack-sensitive per-client metrics (TPR,recall,MacroF1,P10MacroF1,BA,worst-BA,per-client AUROC) UNAVAILABLE — must be represented as unavailable, never estimated/imputed/inherited.
- Regime D-temporal: 9 temporal groups (Modbus excluded, unusable timestamps). Chronological split per client: historical-train 55% / historical-calib 15% / future-recalib 10% / future-eval 20%, stable sort by genuine capture time, duplicate timestamps keep original row order. Compared states: static reference (same 55/15/10/20 budget via deterministic client-local randomization incl. a non-fitted/non-scored/non-evaluated reserve), frozen-future threshold, one-shot recalibrated-future threshold. Policies B1,B2,B4,shrinkage-if-pre-specified. No streaming/periodic/sliding-window/Page-Hinkley/FLARE/FLAME/auto-drift-detection/cross-dataset-transfer — out of scope for this experiment.
- Dataset expansion limit: NO IoT dataset beyond N-BaIoT, CICIoT2023, Edge-IIoTset. Adding another = scope violation.

## 10. Eligibility
- Canonical minimum benign calibration support: n_k >= 100. Determined BEFORE test evaluation; identical across policies compared in same experiment; cannot change after examining outcomes.
- FPR-evaluable additionally requires non-empty benign test denominator.
- Attack-evaluable additionally requires valid per-client attack assignment + >=1 held-out attack row + both classes where required. A client can be FPR-evaluable but NOT attack-evaluable (mandatory distinction for Edge-IIoTset).
- coverage = K_eligible / K_candidate; report candidate/eligible/attack-evaluable/fallback/excluded counts + exclusion reason per client.
- Ineligible fallback clients (deployment-fallback declared explicitly by an experiment) never enter primary CV(FPR).

## 11. Checkpoint protocol
- Training: max 200 rounds; evaluated candidates at {25,50,75,100,125,150,200}.
- Regime A: ONE global primary checkpoint via locked non-test rule `FIXED_TERMINAL_MAXIMUM_ROUND` = candidate at round 200 (fixed-budget, not early-stopping/best-metric). No metric/label/score/threshold-outcome/cross-policy-contrast may enter selection. Same primary round applied consistently across regimes/policies where checkpoint exists; weights remain seed/population/model-specific. B0 applies same rule to its own candidates, never consumes federated checkpoints.
- Anchor checkpoint: conference-historical, preserved as-is, NOT retrofitted with journal selection rule.
- FORBIDDEN selectors: test AUROC, test FPR/CV(FPR), MacroF1/BA, attack labels, B1-vs-B2 effect, external/stress-test results, policy-specific best performance.
- FedProx mu selection: separate locked rule, see §7 above (training-loss based, round 200, ties->smallest mu).

## 12. Score semantics
- Higher reconstruction MSE = stronger anomaly evidence, structurally guaranteed by MSE formula (non-negative by construction). The perturbation-based empirical polarity experiment previously in `scoring/reconstruction.py` was REMOVED deliberately (redundant with structural definition; additive-perturbation heuristic could admit false negatives). Its absence is INTENTIONAL, not a gap — do not flag as missing/incomplete unless a live caller still references it.
- Prediction rule: y_hat = attack if e>tau else benign (comparison operator fixed across policies).

## 13. Metrics (evaluation/reporting protocol)
- Per-client-first: compute per client, then aggregate; pooled-row metrics are controls only, cannot replace client-level metrics.
- FPR_k = FP_k/(FP_k+TN_k), unavailable if benign denom=0. TPR_k similarly with attack denom. BA_k=(TPR_k+(1-FPR_k))/2, needs both. MacroF1_k = mean(F1_benign,F1_attack); never silently zero-fill undefined class metrics.
- AUROC: must be IDENTICAL across B1-B4 (fixed scores/model) up to numerical tolerance — a policy-dependent AUROC difference indicates a BUG (mismatched scores or unintended model variation). Model-quality control, not threshold verdict.
- Cross-client: mu_FPR = unweighted mean over K_eligible; sigma_FPR population std with ddof=0; CV(FPR)=sigma/mu, NO epsilon/stabilizer permitted; mu=0 -> CV undefined (not inf, not 0); near-zero mu -> retain numeric CV but flag near-zero-denominator warning, interpret alongside absolute dispersion. IQR(FPR)=Q75-Q25; Range=max-min; WorstFPR=max.
- Optional (never replace CV(FPR)): Jain index (undefined if all-zero), Gini (undefined if sum zero), cluster within/across dispersion (B4).
- Threshold-estimation: AbsoluteThresholdError=|tau-tau_oracle|; RelativeThresholdError undefined if oracle=0; SignedAttainmentError = achieved_exceedance - (1-q).
- Confirmatory stats: Delta_s = CV(FPR)_B1,s - CV(FPR)_B2,s per seed; point estimate = arithmetic mean over 10 seeds; B1/B2 NEVER resampled independently; two-sided 95% BCa over the 10 paired deltas (bias-correction+acceleration from paired data) is the confirmatory inferential result. If BCa degenerate/undefined (identical deltas, invalid acceleration, degenerate bootstrap, <10 valid pairs): report paired values+point estimate, percentile/basic interval as diagnostic ONLY, never silently substituted as confirmatory. SignConsistency = count(Delta_s>0)/10, descriptive only. Wilcoxon signed-rank + matched-pairs rank-biserial = secondary only, p-value never determines confirmatory verdict (matched-pairs rank-biserial specifically — NOT unpaired Cliff's delta). Secondary p-value emphasis requires pre-declared test families + Holm correction within family; confirmatory endpoint itself gets NO multiplicity correction.
- Nested replicates (calibration subsamples, cluster restarts, temporal windows): summarize within-seed first, then across-seed inference on seed-level estimates only — never treat replicate-level values as independent seeds.
- Temporal: drift_excess = frozen_future_cv - static_reference_cv; recovered_amount = frozen_future_cv - recalibrated_future_cv; recovery_ratio = recovered_amount/drift_excess, computed ONLY when drift_excess exceeds a pre-specified positive-materiality threshold, else explicitly `undefined` (never 0/NaN/blank).
- Rounding: full precision until final presentation; never round before computing contrasts/intervals.

## 14. Excluded scope (must NOT appear in implementation)
No adversarial attacks/poisoning/defenses studied as a research object; no formal privacy mechanism/guarantee (locality != privacy proof; B4 clustering != privacy mechanism; message size != privacy proof); no hardware/production/deployment validation (message-size estimates != deployment measurement); no fleet-scale claim beyond ~100 clients; no continuous/online drift adaptation; not a broad FL/personalization/clustering benchmark; FedBN excluded (would change locked AE architecture); B2-conf must not expand into general federated-conformal method development; no dataset beyond the 3 named.

## 15. Naming rules (violations = drift, not just style)
DATP = original/conference method+identity. DATP-Core = extended study. "anchor" = conference-faithful reference protocol. B0-B4 identifiers fixed meanings, never reused for shrinkage/conformal/comparator/stress-test variants. tau-shrink / calibration-size-aware shrinkage / B2-conf / B-FedStatsBenign are the only variant names. Regime names: Regime A, B-a, B-b, C, D, D-temporal (D... wait — no Regime B-b defined in text actually referenced beyond B-a; note B-b appears only in naming list §12.6 but is NOT otherwise defined in the catalogue — ROADMAP AMBIGUITY, flag if implementation references "Regime B-b" or fails to and instead invents another). Ditto name reserved for genuine Ditto only.

## 16. Roadmap ambiguity noted during ledger construction
- §12.6 (identity doc) lists canonical regime identifiers including "Regime B-b", but the Experiment Catalogue (§4) only defines Regime A, B-a, C, D, D-temporal — no Regime B-b is ever specified with population/procedure. This is a ROADMAP AMBIGUITY: either B-b is a reserved-but-unused identifier (fine) or an intended regime whose catalogue entry is missing from this document. Do not treat any codebase artifact called "Regime B-b" as required, and do not treat its absence as MISSING — flag as ROADMAP_AMBIGUITY only if code references it inconsistently.

## 17. CLI / production roots to verify wired (per audit brief)
datp-core validate [EXPERIMENT_ID]; plan [EXPERIMENT_ID]; preprocess [DATASET_ID] [--overwrite]; smoke [EXPERIMENT_ID] [--overwrite]; anchor reproduce/verify/status; run experiment <ID>/campaign [--overwrite]; report [EXPERIMENT_ID] [--overwrite]; status [EXPERIMENT_ID].
