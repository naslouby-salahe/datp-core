# Roadmap Scientific Authority Extraction (Drift Audit A input)

Sources: `docs/roadmap/00_ROADMAP_INDEX.md`, `01_SCIENTIFIC_IDENTITY_AND_SCOPE.md`, `02_CLAIMS_AND_DECISION_RULES.md`, `03_EXPERIMENT_CATALOGUE.md`, `04_EVALUATION_AND_REPORTING_PROTOCOL.md`, `05_IMPLEMENTATION_ROADMAP.md`, `06_REVIEWER_RISKS_AND_READINESS.md`, `07_AUDIT_AND_DECISION_LOG.md`, `SCIENTIFIC_SOURCE_OF_TRUTH.md` (SoT = canonical tie-breaking authority per `01 §1.3`/`SoT §1`).

## Scientific identity / project scope
DATP-Core is a controlled ablation of **threshold-calibration scope** on a fixed, once-trained, frozen FedAvg autoencoder in federated IoT anomaly detection (`01 §2.2`, `SoT §2`). One autoencoder per seed/dataset regime, checkpoint-selected once, frozen; same per-client calibration/test scores reused across a threshold-scope ladder (shared / per-device-family / per-cluster / per-client). Causal question: does threshold-calibration scope change cross-client FPR dispersion, holding model/scores fixed — not which model/FL algorithm is best. AUROC is a model-quality control only, never the thresholding verdict (`01 §4.6`, `SoT §2.7`). Journal extension adds (without becoming a generic FL-IDS benchmark): Edge-IIoTset (external dataset), `B-FedStatsBenign` (federated-threshold comparator w/ Laridi disclosure), FedProx + one personalization method (training-side stress tests), threshold-estimation-depth variants, one temporal-recalibration experiment.

## Dataset definitions
- **N-BaIoT** (`01 §10.1`, `SoT §4.1`): confirmatory anchor, sole confirmatory substrate. 9 commercial IoT devices (Mirai/BASHLITE) = 9 fixed natural clients, no subsampling, never filtered. Device-family taxonomy available (supports B3). Local artifact authoritative over source paper.
- **CICIoT2023** (`01 §10.2–10.3`, `SoT §4.2`): applicability-boundary dataset (Regime B-a); physical-device repartition rejected (Regime B-b, no trustworthy device metadata). Client rule: **63 file-defined pseudo-clients** (artifact file boundaries, not physical devices). `n_k>=100` eligibility at pseudo-client level. Device-aware wording prohibited for this regime.
- **Edge-IIoTset** (`01 §10.5–10.6`, `SoT §4.3`): sole new external dataset. **10 benign sensor-group folders** = static client population (Regime D). **9 verified temporal groups** for Regime D-temporal (Modbus excluded from temporal only — its `frame.time` is address literals, not timestamps; still valid for static population). Attack traffic confined to attacker's subnet → per-client attack metrics (TPR/Macro-F1/BA/AUROC/attack equity) permanently **unavailable**, never imputed. B3 omitted (no taxonomy). Dataset roster hard-fixed at these 3; a 4th requires formal roadmap revision.

## Client definitions / partitioning rules
- Canonical eligibility: `n_k >= 100` benign calibration samples, fixed before test evaluation, identical across compared policies.
- Regime A (N-BaIoT): 9 natural device clients.
- Regime B-a (CICIoT2023): 63 file-defined pseudo-clients.
- Regime B-b (CICIoT2023 device repartition): rejected/suppressed.
- Regime C (controlled heterogeneity): **20 synthetic clients**, locked Dirichlet partition, severity grid `alpha ∈ {0.1,0.3,0.5,1.0,10.0,IID}`.
- Regime D/D-temporal (Edge-IIoTset): 10 static / 9 temporal clients.
- Aggregation client accumulation order: ascending client identifier.

## Experiment catalogue structure
Evidence-role vocabulary (exactly one per experiment): Confirmatory, Supportive, External validation, Stress test, Mechanism analysis, Threshold variant, Boundary condition, Exploratory, Suppression evidence, Future work (`02 §1`, `03 §1.1`). No post-hoc role promotion (anti-HARKing). ~29 experiment families across 7 execution stages: Stage1 anchor+confirmatory extension → Stage2 stored-score threshold analyses → Stage3 controlled heterogeneity → Stage4 external validation → Stage5 training-side stress tests → Stage6 temporal boundary → Stage7 optional supplement. Fixed per-experiment spec template (`03 §1.2`).

## Training profiles
- Core ladder algorithm: **FedAvg only**. Adam, lr=0.001, batch=256, 1 local epoch/round, full participation.
- Round budget: anchor 150-round cap; journal **200 rounds**.
- Anchor checkpoint: convergence rule from round 40, `abs(loss[r-9]-loss[r])/abs(loss[r-9]) < 0.005` over trailing 10 FedAvg-weighted benign val losses, else cap at 150.
- Journal checkpoint grid: `{25,50,75,100,125,150,200}`; primary round chosen once via lowest FedAvg-weighted benign validation reconstruction error, frozen before outcome inspection, reused across FedProx/Ditto.
- Forbidden checkpoint selectors: anything test/attack/AUROC/external/policy-outcome-driven.
- **FedProx**: proximal `mu ∈ {0.001,0.01,0.1,1.0}`; `mu=0` ≡ FedAvg, not a FedProx condition.
- **Ditto**: genuine global model + persistent per-client personalized states never reset, proximal personalized objective `min_v L_k(v_k) + (proximal_weight/2)||v_k - w_global||^2`, fresh personalized optimizer state per local fit, separate provenance. If unmet, must use real method name (e.g. FedRep-AE/FedPer-AE), never "Ditto".
- Seed cohorts: `datp_core_ten_seed = [0..9]` (journal), `anchor_five_seed = [0..4]` (historical anchor). Partition seeds independent domain.
- FedProx/Ditto permanently outside the B0–B4 causal ladder.

## Checkpoint rules
Checkpoint identity = selected round + selection-rule id. Reuse gated by checksum/schema-version/parent-fingerprint/completion/non-stale; rejected on any dataset/materialization/client-assignment/split change.

## Threshold policy families
- **B0** centralized reference (pooled data + pooled threshold) — not in federated ladder.
- **B1** shared: local `q=0.95` quantile per eligible client; server threshold = arithmetic mean of local quantiles (not exact pooled quantile).
- **B2** per-client: own benign q=0.95 quantile. Confirmatory comparator.
- **B3** family: mean of member local thresholds per validated physical-device family; N-BaIoT only; mechanism baseline not confirmatory.
- **B4** cluster: taxonomy-free groups from 4-scalar benign fingerprint `{mean, std(ddof=1), skew(uncorrected Fisher-Pearson), p95(linear interp)}`; degenerate rules for <2 scores / non-finite skew; feature scaling zero-mean/unit-var ddof=0 per population; k-means Lloyd's, k-means++ init, 10 inits, max 300 iter, tol 1e-4, **seed=42**; canonical **K=3** (K=9 etc. exploratory only); relabel by ascending cluster threshold then smallest member client ID; cluster threshold = mean of member local thresholds.
- Shared-threshold controls: exact pooled quantile, sample-weighted shared threshold — supportive, don't replace B1.
- Local-global shrinkage: `tau_k(lambda) = lambda*tau_k,local + (1-lambda)*tau_shared`, grid `lambda ∈ {0.00,0.25,0.50,0.75,1.00}`; calibration-size-aware `lambda(n_k)` must be frozen before test eval, monotone unless justified, bounded [0,1].
- **B2-conf**: split-conformal local threshold, benign errors as nonconformity scores, finite-sample-adjusted quantile at `alpha=1-q`, main `alpha=0.05`. Supportive diagnostic only.
- **`B-FedStatsBenign`**: federated benign-only summary-stats comparator; client msg = benign-only `n_k, mu_k, sigma_k^2` + exceedance counts; `mu_global = Σn_k*mu_k/Σn_k`; `within=Σn_k*sigma_k^2/Σn_k`, `between=Σn_k*(mu_k-mu_global)^2/Σn_k` (mandatory), `sigma^2_global=within+between`; candidate grid `tau(k)=mu_global+k*sigma_global`, k=0.00..5.00 step 0.01; select `k*=argmin|AchievedExceedance(k)-(1-q)|`, tie→larger k; fixed multipliers `{2.0,2.5,3.0}` supplementary only. Never called "faithful Laridi reproduction" (reserved name `B-LaridiFaithful` is out of scope).
- Retired/forbidden identifiers, must never reappear: `B5`, `B3-LGS`, "Laridi-faithful benign".

## Seed cohorts / deterministic seed derivation
- Training seeds: `datp_core_ten_seed=[0..9]`, `anchor_five_seed=[0..4]`; sole independent replication unit (never clients/rows/checkpoints/windows/subsamples).
- Historical bootstrap seed: literal hardcoded `analysis_seed=42` for `historical_five_seed_percentile_bootstrap`, distinct from cohort-level `bootstrap_analysis_seed=300`.
- Clustering seed: `random_seed=42` for B4 k-means.
- Partition seeds: independent domain, derived via `blake2b`-based algorithm, 8-byte digest over ordered UTF-8 component key, `mod 2^32`.
- Separate seed domains: training, partitioning, calibration subsampling, clustering, bootstrap analysis, dataloader shuffling.
- Dataloader seed namespaces: `dataloader_shuffle=[training_seed,round_index,client_id,local_epoch_index]`; `dataloader_worker=[training_seed,round_index,client_id,worker_index]`.
- Allowed nondeterminism (e.g. GPU reduction order) must be recorded/quantified, never claimed bitwise-reproducible.

## Split rules
- Standard (non-temporal): disjoint `training/calibration/test`.
- Temporal (Regime D-temporal only), chronological per client: `historical_training 55% / historical_calibration 15% / future_recalibration 10% / future_evaluation 20%`; stable sort by genuine capture time; no future leakage into historical splits.
- Preprocessing fitted only on permitted benign training population, persisted with fitted params/feature order/excluded columns/fit-population identity/config fingerprint.
- No feature selection beyond fixed dataset-declared schema.

## Calibration contracts
Benign-only calibration for every threshold policy/comparator. Attack-labelled data never determines: threshold values, quantile selection, client eligibility, checkpoint selection, comparator tuning, shrinkage strength, conformal alpha, cluster count/feature selection, external-dataset client construction. Calibration/evaluation records disjoint. Checkpoint selection uses only trailing FedAvg-weighted benign validation loss.

## Evaluation metrics required
Prediction rule: `y_hat = attack if e > tau else benign`. Per-client: FPR, TPR, BA=(TPR+(1-FPR))/2, Macro-F1, AUROC (must match across B1-B4 up to numerical tolerance). Cross-client: `mu_FPR` (unweighted mean over eligible), `sigma_FPR` (population SD ddof=0), **`CV(FPR)=sigma_FPR/mu_FPR`** = sole primary confirmatory metric, no epsilon stabilizer, `undefined` at mean FPR=0; `cv_instability_threshold` for near-zero-denominator warning is itself **unresolved/unconfigured** (the one unresolved item in the whole roadmap, SoT §17 item 20). Dispersion companions (never substitutes): `IQR(FPR)`, `Range(FPR)`, `WorstFPR`; lower-tail companions `CV(TPR)`, `P10(MacroF1)`, `WorstBA`. Optional: Jain index, Gini, cluster dispersion. Metric status enum (must be used, never silent 0/NaN): `available, undefined_zero_denominator, undefined_near_zero_denominator, unavailable_missing_benign_class, unavailable_missing_attack_class, unavailable_invalid_attack_assignment, unavailable_ineligible_client, unavailable_unsupported_regime, failed_invalid_artifact, failed_statistical_procedure`. Reporting precision: rates/CI/effect sizes 3 decimals, p-values 3 sig figs with `<0.001` label, counts integers; never round before computing contrasts/intervals.

## Statistical procedures named
Confirmatory paired contrast `Δ_s = CV(FPR)_{B1,s} - CV(FPR)_{B2,s}`, mean over 10 seeds. Confirmatory interval: two-sided 95% **BCa bootstrap** over paired deltas, mean statistic, bias correction, acceleration via leave-one-seed-out jackknife, fixed recorded seed, ≥10,000 resamples exploratory / **50,000 frozen publication**. Degenerate BCa → `failed_statistical_procedure`; percentile/basic intervals diagnostic-only. Sign consistency descriptive only. Secondary: Wilcoxon signed-rank (never determines confirmatory verdict); matched-pairs rank-biserial (never unpaired Cliff's delta). Multiplicity: none for sole confirmatory endpoint; **Holm correction** within pre-declared families only for secondary emphasis. Nested replicates (calibration subsamples, cluster restarts): summarize within seed before cross-seed inference. Association: Spearman + regression + R² + influence diagnostics, associative language only. Cluster stability: Adjusted Rand Index + memberships/sizes/empty/singleton counts. Historical five-seed bootstrap: 95% two-sided **percentile** (not BCa), 10,000 resamples, hardcoded seed 42 — context only. Historical reference values (never replaced by a weaker 10-seed result, only compared against): B1 CV(FPR)=1.017, B2=0.299, paired reduction 0.718, 5-seed 95% CI [0.647,0.769], relative reduction 70.6%, B4 CV(FPR)=0.645 (~52% recovery), B3 CV(FPR)=0.964, P10 Macro-F1 0.344→0.300 under B2.

## Reporting rules
Main paper requires (§18.1-3): all 10 seed-level B1/B2 values + paired diffs + BCa interval + sign consistency + IQR/range/worst-FPR + per-client FPR + P10 Macro-F1 tradeoff + AUROC-invariance control; mechanism evidence (B1/B3/B4/B2, cluster stability/memberships, score distributions, threshold-movement vs FPR/TPR, heterogeneity association); boundary/stress evidence (calibration-size/shrinkage, B2-conf coverage, CICIoT2023 boundary, Edge-IIoTset validation, B-FedStatsBenign, FedProx, Ditto, temporal recalibration). Required figures (§19): paired-seed confirmatory plot, all-client FPR comparison, quantile-sensitivity, heterogeneity-severity, cluster membership/stability, benign/attack CDFs, threshold-shift, calibration-size/shrinkage curves, B2-conf coverage, Edge-IIoTset plot, FedProx/Ditto comparison, temporal plot — all pre-specified conditions/clients shown, no unsupported smoothing/truncated axes, **no Sankey diagram for B4**. Required tables (§20) distinguish mean-client vs pooled, estimated vs measured communication, unavailable vs undefined, core-ladder vs stress-test models. **Result freeze** (§22): only when all seeds present/formally-failed, eligibility final, all conditions represented, statuses resolved, provenance complete; post-freeze no seed/client/checkpoint/quantile/size/cluster-count/comparator setting may be removed/retuned — corrections create a new version. Favorable-result selection prohibited (§23).

## Artifact provenance requirements
Chain: `configuration → dataset artifact → split manifest → preprocessing state → training run → checkpoint → score artifact → threshold artifact → per-client metrics → seed-level aggregate → statistical result → table/figure`. Every artifact carries scoped identity key from every upstream link. Required fingerprints: **configuration fingerprint** (any result-affecting value), **scientific fingerprint** (dataset identity + regime + client-definition rule + split manifest + model/training protocol version), **execution fingerprint** (OS/Python/framework/CUDA/driver/GPU/dependency-lock/deterministic-flags/execution-profile). Input/output hashes per stage. Atomic writes on every execution profile (`scientific, development, smoke, dataset_audit, test_smoke`). Reuse requires checksum + schema-version + parent-fingerprint + completion + non-stale all true; invalidated upstream invalidates all downstream (regenerate, never patch in place).

## Deterministic execution requirements
Deterministic library flags where supported; separate seed domains as above; `nondeterministic_operation_policy: raise_never_silently_downgrade`.

## Capability restrictions
GPU required under main runtime profile: `configs/runtime.yaml: device_policy_rules.cuda_required.missing_device_behavior: fail_execution_never_downgrade`. `resource_pressure_policy`: silent reduction of batch-size/round-count/seed-count/client-count forbidden; `on_budget_exceeded: block_execution_and_report`.

## Suppressed or limited experiments
CICIoT2023 device/MAC repartition (Regime B-b) — suppressed. CICIoT2023 temporal analysis — suppressed (no valid timestamps). FedBN — rejected (would require BatchNorm, changes locked architecture). Anomaly-labelled Laridi-faithful threshold — out of scope. Empirical membership-inference probe — rejected. Streaming drift detectors/continuous adaptation — rejected (belongs to "Dynamic DATP"). Byzantine-robust federated conformal prediction — rejected (belongs to DATP-CP/future work). Broad personalized-FL benchmark (APFL, Per-FedAvg, pFedMe, FedRep, FedPer alongside Ditto) — rejected, only one personalization stress test allowed. Regime D attack-sensitive per-client metrics — permanently unavailable, not deferred. Dataset roster hard limit = 3 (N-BaIoT, CICIoT2023, Edge-IIoTset). Comparator roster hard limit = FedProx + Ditto + B-FedStatsBenign.

## Claim boundaries
Permitted: controlled threshold-calibration-scope study; operating-point reliability under heterogeneous federated IoT clients; false-alarm-equity analysis on a fixed detector; journal extension w/ external/stress/mechanism evidence; evaluating when threshold personalization remains useful.
Prohibited (exhaustive, §14.2/§17): solving non-IID FL generally; improving global Macro-F1/every client; guaranteeing human/demographic/protected-attribute fairness; formal privacy claims (DP, secure agg, HE, SMPC, MI-resistance, reconstruction-resistance, formal privacy budgets); robustness to poisoning/backdoors/Byzantine/evasion; concept-drift handling beyond one-shot recalibration; deployment readiness/hardware validation; fleet-scale validation above 100 real clients; universal dominance of any policy/comparator/personalization method; Edge-IIoTset cross-client attack-detection equity; "faithful Laridi reproduction" via B-FedStatsBenign; first federated conformal method; "universally optimal threshold"; JS-divergence causal claims; B4 as privacy mechanism; real-time/online claims; energy/battery claims (only analytically estimated comms/storage, labeled estimates); raw-network attack-realizability claims beyond source dataset's own claims. Words *first, novel, state of the art, guarantees, solves, optimal, universally superior* forbidden without independent verification.

## Hardcoded-vs-configuration audit flags (critical for refactor)
- Explicitly hardcoded-by-design (locked scientific constants, NOT meant to be swept): historical bootstrap `analysis_seed=42` (distinct from cohort `bootstrap_analysis_seed=300`); B4 k-means `random_seed=42`; `q=0.95`; `K=3`; `n_k>=100`; FedProx `mu` grid; shrinkage `lambda` grid; B2-conf `alpha=0.05`; k-means init count 10/max iter 300/tol 1e-4; chronological split 55/15/10/20; Dirichlet grid.
- **But**: every one of these must still have a **named configuration-key mapping** in `configs/protocols.yaml`/`configs/experiments.yaml`/`configs/runtime.yaml` (`05 §2.1`, `SoT §16.1`) — "locked" means "not tunable/HARK-able post-result," NOT "may live as an untracked code literal." A missing scientific value must fail configuration validation, never silently default.
- **Unresolved / must NOT be invented a value**: `cv_instability_threshold` (SoT §17 item 20) — blocks only the near-zero-denominator warning annotation, not the confirmatory endpoint itself. Do not add a default for this during the refactor.
- Rule: "An item marked unresolved in this file must not be given an invented value by configuration, code, or narrative text" (SoT §1.4). "A configuration value that contradicts this file is a configuration defect, not an alternate scientific decision" (SoT §1.3).

## Notes for the refactor
- `SCIENTIFIC_SOURCE_OF_TRUTH.md` is the numeric tie-breaking authority; any constant centralized into config during the refactor must match SoT's contract exactly, not the narrative files 01-06.
- A refactor that centralizes constants into one config module matches the roadmap's own documented pattern (docs reference SoT sections rather than duplicating values) — supports the `configuration/` package design in section 6 of the task.
- Any hardcoded literal in `src/datp_core` matching the "must come from configuration" list is a candidate finding independent of whether its value is currently correct.
