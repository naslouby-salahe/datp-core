# DATP-Core Journal Extension — Lean Audit & Implementation Matrix

> **Purpose:** active implementation/audit tracker for the authoritative DATP-Core roadmap. This matrix is intentionally lean. It does **not** duplicate formulas, prose sentinels, literal blocks, source tables, or atomic roadmap bullets. The roadmap remains the only scientific authority.

## 0. Authority, migration, and operating rules

- **Authoritative roadmap:** `Journal_Extension_Master_Roadmap.md`
- **Roadmap SHA-256:** `f77ad1c1ebc181c184f29f0c22e5e872a105c4f6ace59207a0c35982bcabf7dc`
- **Roadmap size:** `335741` bytes on disk (CRLF; `329257` LF-normalized); `6484` lines
- **Migrated legacy matrix SHA-256:** `1d26ba846312f467af2b1446dc64a9e29162c0b8d642b1b91a0aa4d9e55766bb`
- **Migration date:** `2026-08-13`
- **Repository policy:** no backwards compatibility. Replace obsolete APIs/identities at callers and remove stale paths.
- **Scientific authority rule:** when this matrix and the roadmap differ, the roadmap wins.
- **No-rescue rule:** supportive, mechanism, external, stress, optional, or boundary evidence cannot replace the sole confirmatory endpoint.

### 0.1 Workflow statuses

| Status | Meaning |
|---|---|
| `PASS` | the active row was already closed by retained implementation/evidence |
| `PARTIAL` | useful audited work exists and is preserved; only unresolved section-level/integration work remains |
| `NOT_AUDITED` | no retained closure exists at this active-row level |
| `OPTIONAL_DEFERRED` | explicitly optional roadmap work; do not execute while any mandatory row remains unresolved |
| `FAIL` | a real unmet requirement/evidence condition remains |
| `EVIDENCE_REQUIRED` | implementation exists, but campaign/submission evidence cannot yet be produced |

### 0.2 Lean-matrix execution rules

1. **Read the roadmap section referenced by the active row before changing code.** The matrix is a tracker, not a substitute specification.
2. **Audit coherent capabilities/experiments, not individual roadmap sentences.** Do not recreate atomic, formula, literal, prose-sentinel, or table-sentinel queues.
3. **Preserve completed work.** A `PASS` row is frozen unless a code change or roadmap change directly affects its semantic owner.
4. **Impact-driven re-audit only.** After a large implementation chunk, reopen only rows/gates whose owning code, protocol identity, artifact schema, or evidence path changed.
5. **No repeated global audits after small changes.** Run broad Ruff/Pyright/Pylance/pytest and gate review only after substantial coherent chunks or at final closure.
6. **Tests do not replace reachability.** Production requirements require a reachable runtime owner plus retained evidence.
7. **One scientific contract, one semantic owner.** Competing runtime implementations with different semantics are a failure until consolidated.
8. **No silent defaults.** Roadmap-locked values come from typed protocol identities/constants, not library defaults or historical fixtures.
9. **Optional work is non-blocking.** `OPTIONAL_DEFERRED` rows remain deferred until all mandatory implementation rows are closed.
10. **Campaign-only evidence is not an implementation defect.** Submission-time literature evidence and final release-bundle evidence remain `EVIDENCE_REQUIRED` until the campaign/submission stage; do not fabricate or repeatedly re-audit them.
11. **The progress archive is read-only.** Do not scan it during ordinary implementation. Open it only when a migrated `PASS`/`PARTIAL` row needs historical evidence or is explicitly impacted by a change.
12. **Full scientific experiment execution is not required to close code implementation rows.** Implementation, tests, static validation, reachability, artifact contracts, and bounded smoke validation are sufficient until the actual campaign stage; campaign-dependent gates remain pending evidence.

### 0.3 Migration validation

The previous exhaustive matrix was migrated without discarding completed work:

| Legacy layer | Previous size | Completed/adjudicated progress retained | Validation against current roadmap |
|---|---:|---:|---|
| Curated Part-I scientific contracts | `95` rows | all existing PASS evidence retained and rolled into Section 2 | source line ranges unchanged |
| Formula ledger | `198` rows | `77 PASS` mappings retained | all 77 formula blocks still match the current roadmap source ranges |
| Literal ledger | `93` rows | `6 PASS` mappings retained | all 6 literal blocks still match the current roadmap source ranges |
| Atomic requirement register | `1195` rows | `377 PASS`, `1 NOT_APPLICABLE`, `2 FAIL` retained | all 380 adjudicated atomic requirements still match the current roadmap source lines exactly |
| Gates A–R summaries | `18` | `18 NOT_AUDITED` (fresh Cycle-3 reset) |

The removed `NOT_AUDITED` microscopic rows are **not lost requirements**: their authoritative content remains in the roadmap and is now inherited by the coherent active row that owns the relevant section.

### 0.4 Active queue size after trimming

| Active layer | Rows | Current migrated state |
|---|---:|---|
| Scientific programme groups | `14` | `14 NOT_AUDITED` (fresh Cycle-3 reset) |
| Experiments / analyses | `36` | `32 NOT_AUDITED`, `4 OPTIONAL_DEFERRED` (fresh Cycle-3 reset) |
| Evaluation / statistics groups | `14` | `14 NOT_AUDITED` (fresh Cycle-3 reset) |
| Manuscript deliverables | `6` | `6 NOT_AUDITED` (fresh Cycle-3 reset) |
| Gates A–R summaries | `18` | `18 NOT_AUDITED` (fresh Cycle-3 reset) |

That is **88 active tracking rows** instead of thousands of atomic/formula/literal/sentinel/card rows. The 14 drift sentinels and 30 numerical locks are guardrails/lookup indexes, not independent work queues.

### 0.5 Deterministic semantic ownership

| Contract family | Semantic owner |
|---|---|
| identities, enums, immutable coordinates, provenance objects | domain/protocol contracts |
| dataset parsing, populations, split-capability facts | datasets |
| fitted transforms and preprocessing identity | preprocessing |
| centralized/federated/personalized detector training | learning/training |
| immutable reconstruction-score generation | scoring/pipeline score stage |
| benign calibration, support, eligibility | calibration |
| threshold estimators/policies/sketches/shrinkage/conformal rules | thresholding |
| per-client and aggregate metrics | evaluation |
| bootstrap/tests/associations/mechanisms/temporal inference | analysis |
| experiment coordinate expansion and execution order | planner/pipeline |
| figures, tables, claims, release exports | reporting/publication |
| determinism, environment, artifact integrity | runtime/provenance validation |

## 1. Scientific drift sentinels

These rows are intentionally duplicated as **audit sentinels** because a paragraph-level omission here would be scientifically dangerous even if downstream experiment rows were otherwise complete. They do not override the authoritative roadmap owner.

| Sentinel ID | Locked invariant | Roadmap owner | Audit consequence |
|---|---|---|---|
| `DRIFT-SENTINEL-001` | Only one endpoint is confirmatory: `NBAIOT_NATURAL_DEVICES`, `SHARED_THRESHOLD` vs `LOCAL_THRESHOLD`, `CV(FPR)`, exactly ten paired training seeds, locked BCa decision rule. | Part I §8.1; Part II §5.1; Part III §11 | Any competing confirmatory endpoint or tier promotion is `FAIL`. |
| `DRIFT-SENTINEL-002` | The core threshold-scope intervention changes threshold-calibration scope only; detector, preprocessing, population, calibration/test score identity, labels, eligibility, q target, and metric semantics are fixed within the comparison coordinate. | Part I §§2.1–2.4 | Policy-specific retraining/rescoring/refitting or test-population changes are causal-isolation `FAIL`. |
| `DRIFT-SENTINEL-003` | Every DATP-compatible threshold uses benign calibration evidence only; calibration and evaluation are disjoint. | Part I §§3.1–3.2 | Attack-label calibration or row overlap is a claim-blocking `FAIL`. |
| `DRIFT-SENTINEL-004` | The complete threshold programme assumes protocol-compliant calibration participants and an honest protocol-executing server; contributor-availability is non-adversarial and does not establish Byzantine/poisoning/message-integrity robustness. | Part I §3.2A / §10.E.10 | Adversarial robustness wording is `FAIL`. |
| `DRIFT-SENTINEL-005` | `n_k_source >= 100` is the primary eligibility rule and is computed before experimental calibration subsampling. | Part I §3.3 | Recomputing eligibility from experimental `m` is `FAIL`. |
| `DRIFT-SENTINEL-006` | Confirmatory deployment regime is `PERSISTENT_IDENTIFIABLE_CLIENTS` with full training participation and persistent client identity/state where required. | Part I §3.3A | Intermittent/unseen-client generalization is `FAIL`. |
| `DRIFT-SENTINEL-007` | Canonical empirical threshold is `q=0.95`, Hyndman–Fan type-7 / NumPy `method="linear"`, float64; conformal and KLL are explicit exceptions with their own semantics. | Part I §2.2.3 | Alternate interpolation under the same method identity is `FAIL`. |
| `DRIFT-SENTINEL-008` | Every federated training execution has one scientific terminal detector at round `200`; diagnostic/recovery checkpoints never become scientific score sources. | Part III §13 / Gate F | Non-terminal scientific scoring is `FAIL`. |
| `DRIFT-SENTINEL-009` | AUROC/AP are detector-quality controls computed from canonical continuous scores; threshold policy cannot improve AUROC within a fixed-score ladder. | Part I §2.2.2 / Part III §§4.5–4.6 | Policy-specific AUROC differences are provenance `FAIL`. |
| `DRIFT-SENTINEL-010` | `CICIOT_FILE_CLIENTS` is file-defined applicability-boundary evidence only; no physical-device reconstruction or device-aware claim is authorized. | Part I §9.2 / Part II §4.2 | Inferred-device semantics are `FAIL`. |
| `DRIFT-SENTINEL-011` | Edge static/temporal populations support the exact client/metric semantics declared by the roadmap; unsupported per-client attack-sensitive metrics remain unavailable. | Part I §§9.4–9.5 / Part II §§4.4–4.5 | Reconstructed unsupported attack metrics are `FAIL`. |
| `DRIFT-SENTINEL-012` | DATP-Core adds no external IoT dataset beyond Edge-IIoTset; no extra dataset is added without an explicit roadmap amendment. | Part I §9.6 / Gate O | Silent dataset expansion is `FAIL`. |
| `DRIFT-SENTINEL-013` | FedProx, `FEDAVG_LOCAL_FINE_TUNING`, Ditto, preprocessing sensitivity, external validation, temporal evidence, threshold variants, and mechanism analyses remain outside the sole confirmatory causal endpoint. | Part I §§7–8 / Part II evidence roles | Stress/supportive evidence cannot rescue or replace confirmation. |
| `DRIFT-SENTINEL-014` | No formal privacy, Byzantine/poisoning robustness, hardware deployment, fleet-scale, continuous-drift, or universal non-IID solution claim is authorized. | Part I §10.B / §10.D / §10.E | Overclaim is Gate R `FAIL`. |

## 2. Scientific programme implementation groups

These 14 rows replace the old 95-row active Part-I queue. Detailed completed evidence is preserved in the progress archive. `Unresolved child contracts` identifies only the old curated rows that did not already have PASS closure; it is a navigation aid, not a request to reconstruct the old microscopic matrix.

| ID | Coherent roadmap scope | Roadmap owner | Status | Migrated progress credit | Unresolved child contracts |
|---|---|---|---|---|---|
| `SCIENTIFIC-01` | Programme identity | Part I §§1.1–1.2 | `NOT_AUDITED` | fresh Cycle-2 audit: programme identity, working title, one-paragraph scope verified against Part I §§1.1-1.2 | GLOBAL-CONTRACT-001, GLOBAL-CONTRACT-002 |
| `SCIENTIFIC-02` | Core causal / fixed-detector contract | Part I §§2.1–2.4 | `NOT_AUDITED` | fresh Cycle-2 audit: causal contract, fixed-detector rule, sole manipulated variable, fixed elements verified | GLOBAL-CONTRACT-005, BOUNDARY-CONTRACT-001 |
| `SCIENTIFIC-03` | Calibration, evaluation, eligibility, federation regime, metric intent | Part I §§3.1–3.6 | `NOT_AUDITED` | fresh Cycle-2 audit: calibration/evaluation/eligibility/federation regime verified | GLOBAL-CONTRACT-006, GLOBAL-CONTRACT-007, GLOBAL-CONTRACT-008, GLOBAL-CONTRACT-009 |
| `SCIENTIFIC-04` | Core threshold-policy system | Part I §§4.1–4.6 | `NOT_AUDITED` | fresh Cycle-2 audit: core threshold-policy system verified (shared/local/family/cluster) | GLOBAL-CONTRACT-010, GLOBAL-CONTRACT-011 |
| `SCIENTIFIC-05` | Supportive threshold variants | Part I §§5.1–5.4 | `NOT_AUDITED` | fresh Cycle-2 audit: threshold variants and comparators verified (shrinkage, conformal, KLL, benign-summary) | — |
| `SCIENTIFIC-06` | Federated shared-threshold comparators | Part I §§6.1–6.2 | `NOT_AUDITED` | fresh Cycle-2 audit: training-side stress tests verified (FedProx grid, Ditto lambda-D grid, 10-epoch fine-tuning) | GLOBAL-CONTRACT-013 |
| `SCIENTIFIC-07` | Training-side stress tests and absorption semantics | Part I §§7.1–7.4 | `NOT_AUDITED` | fresh Cycle-2 audit: evidence architecture verified (sole confirmatory endpoint, roles, honest negative evidence) | — |
| `SCIENTIFIC-08` | Evidence architecture and negative evidence | Part I §§8.1–8.3 | `NOT_AUDITED` | fresh Cycle-2 audit: dataset/population boundaries verified (9 physical devices, CICIoT gate, Edge, Dirichlet) | GLOBAL-CONTRACT-016, CALIBRATION-CONTRACT-007, GLOBAL-CONTRACT-017 |
| `SCIENTIFIC-09` | Dataset/population and heterogeneity boundaries | Part I §§9.1–9.7 | `NOT_AUDITED` | fresh Cycle-2 audit: scope/terminology/claim boundaries verified (naming rules, claim-survival, prior-art table) | — |
| `SCIENTIFIC-10` | Included scientific scope | Part I §10.A | `NOT_AUDITED` | fresh Cycle-2 audit: numerical locks verified (q=0.95, grids, materiality, terminal round 200, R=10) | GLOBAL-CONTRACT-018, THRESHOLD-CONTRACT-011, THRESHOLD-CONTRACT-012, TEMPORAL-CONTRACT-001, GLOBAL-CONTRACT-019, GLOBAL-CONTRACT-020 |
| `SCIENTIFIC-11` | Excluded scope and non-expansion guardrails | Part I §10.B | `NOT_AUDITED` | fresh Cycle-2 audit: statistical and evaluation contracts verified (BCa, sign test, Wilcoxon, precision, LODO) | GLOBAL-CONTRACT-021, GLOBAL-CONTRACT-022, GLOBAL-CONTRACT-023, GLOBAL-CONTRACT-024, TEMPORAL-CONTRACT-002, GLOBAL-CONTRACT-025, CALIBRATION-CONTRACT-008, GLOBAL-CONTRACT-026 |
| `SCIENTIFIC-12` | Terminology, identities, statistical/calibration vocabulary | Part I §10.C | `NOT_AUDITED` | fresh Cycle-2 audit: temporal boundary verified (drift-excess materiality 0.05, recovery ratio 0.5, uncertainty-for-supported) | GLOBAL-CONTRACT-027, THRESHOLD-CONTRACT-013, THRESHOLD-CONTRACT-014, GLOBAL-CONTRACT-028, STAT-CONTRACT-001, CALIBRATION-CONTRACT-009 |
| `SCIENTIFIC-13` | Claim framing, novelty, claim survival, negative evidence | Part I §10.D | `NOT_AUDITED` | fresh Cycle-2 audit: reproducibility/provenance/release contracts verified | REPORT-CONTRACT-006, REPORT-CONTRACT-007, GLOBAL-CONTRACT-033 |
| `SCIENTIFIC-14` | Accepted scientific limitations | Part I §10.E | `NOT_AUDITED` | fresh Cycle-2 audit: manuscript deliverables and evidence narrative verified | DATASET-CONTRACT-008, DATASET-CONTRACT-009, GLOBAL-CONTRACT-034, TEMPORAL-CONTRACT-004, GLOBAL-CONTRACT-035, GLOBAL-CONTRACT-036, THRESHOLD-CONTRACT-015, GLOBAL-CONTRACT-037, CALIBRATION-CONTRACT-010, CALIBRATION-CONTRACT-011, BOUNDARY-CONTRACT-002 |

## 3. High-risk numerical lock lookup

This is **lookup-only**, copied from the current roadmap. These rows are not a second audit queue. Verify each value while closing its owning scientific/experiment/evaluation row; do not create a separate numeric-remediation pass unless an owning row fails.

| Contract | Locked value / rule | Authoritative section |
|---|---|---|
| calibration object | DATP-Core studies anomaly operating-point calibration of a fixed continuous anomaly score; probability calibration and general federated conformal calibration are separate objects and do not authorize ECE/NLL/Brier or broad coverage claims | §10.C.7A |
| `H_TAUTOLOGY` held-out falsification | `CalibrationExceedance=(1/n_k_used) sum_j 1[e_cal>tau]`; `CalibrationTargetError=CalibrationExceedance-0.05`; `TestTargetError=FPR_test-0.05`; `CalibrationGeneralizationGap=TestTargetError-CalibrationTargetError` on disjoint calibration/evaluation rows | Part III §4.8A |
| honest calibration participants | protocol-compliant clients/server; no fabrication, semantic alteration, suppression, replay, identity substitution, or adversarial message manipulation of calibration rows, scores, thresholds, support counts, summaries, fingerprints, sketches, or conformal statistics; no Byzantine-robustness claim | §3.2A / §10.E.10 |
| canonical empirical quantile | `q=0.95`, Hyndman–Fan type-7 / NumPy `method="linear"` | §2.2.3 |
| quantile sensitivity | `{0.90,0.95,0.975,0.99}` | Part II §6.2 |
| historical moment estimator | `mean + sample SD`, `ddof=1`, float64; 2-by-2 `{TYPE7_Q95, moment} x {SHARED,LOCAL}` | §5.1A / Part II §6.2A |
| primary eligibility | `n_k_source >= 100` | §3.3 |
| calibration-size grid | `m={50,100,250,500,1000,5000}` | Part II §8.1 |
| calibration nested replicates | `R=10` per `(training_seed, client, m)` with prefix-nested SHA-256→PCG64 sampling | Part II §2.3A and §8.1 |
| calibration-subsample threshold variance | sample variance `s_tau^2=(R-1)^{-1} sum_r (tau_r-bar_tau)^2`, `R=10`, `ddof=1`; `ThresholdSD=sqrt(s_tau^2)` | Part III §8.4 |
| support-versus-burden diagnostic | per-seed Spearman correlations `rho(S,FPR_shared)` and `rho(S,FPR_shared-FPR_local)`; average ranks for ties; require at least `5` valid clients and at least `2` distinct values in both inputs; no client-level inferential p-value | Part II §7.5A |
| per-device effect direction counts | exact sign counts of `DeltaFPR_k=FPR_local,k-FPR_shared,k` and, where valid, `DeltaTPR_k=TPR_local,k-TPR_shared,k`; equality uses the exact common FP/TP counts, not a floating tolerance | Part II §7.5 |
| fixed shrinkage | `lambda={0,0.25,0.50,0.75,1.00}` | §5.2 / Part II §8.2 |
| size-aware shrinkage | `lambda_k=n_k_used/(n_k_used+100)` | §5.3 |
| CLUSTER_THRESHOLD fingerprint | `[mean,std,skew,p95]` of benign reconstruction error | §4.5 |
| CLUSTER_THRESHOLD clustering | separate score-side fingerprint standardization; canonical `K=3`; locked initialization/seed handling | §4.5 and Part II §7.1 |
| KLL comparator | float64; primary `k=400`; sensitivity `{200,800}`; inclusive rank | §6.1A / Part II §9.2 |
| FedProx | `mu={0.001,0.01,0.1,1.0}`; `mu=0` is FedAvg-equivalent, not a FedProx cell | §7.1 |
| FedProx activation diagnostics | `L2Drift`, `RMSDrift=L2/sqrt(P)`, terminal rounds `151..200`, un-clipped `DriftSuppression=1-D_FedProx/D_FedAvg` when denominator `>1e-12` | §7.1A / Part II §11.1 |
| calibration-contributor availability | omit `m={0,1,2,3,4}` shared-threshold contributors; exhaust every subset with `K_s-m>=5`; apply resulting shared threshold to unchanged full eligible evaluation population | Part II §8.6 |
| federation regime | persistent identifiable clients; full training participation `1.0`; retained client-local threshold/personalized state where applicable; no intermittent-cross-device or unseen-client claim | §3.3A |
| post-FedAvg local fine-tuning | initialize from exact FedAvg round-200 terminal detector; benign TRAIN only; exactly `10` local epochs; fresh optimizer state; no validation/calibration/test access; epoch-10 terminal personalized state | §7.2A / Part II §11.2A |
| common upstream absorption diagnostics | condition-native `H` for within-condition mapping; cross-model `ModelAlignmentH` on a seed-specific fixed FedAvg 64-bin grid; location/scale/local-q95 dispersion; normalized shared-local threshold distance; raw `DeltaScope`; un-clipped `ScopeAbsorption`; un-clipped `AlignmentReduction` when FedAvg denominator `>1e-12` | §7.2B |
| natural-device helped/harmed profile | exact sign-based FPR/TPR/Macro-F1/BA help-harm fractions; Pareto direction categories; per-device help frequency over the same ten seeds; fixed support strata of 3+3+3 eligible N-BaIoT devices | Part II §7.5B / Part III §5.6 |
| Ditto | `lambda_D={0.1,1.0,2.0}`, canonical `1.0` | §7.2 |
| terminal detector | one detector at fixed round `200` | Part III §13 |
| confirmatory replication | exactly `10` paired training seeds | §8.1 / Part II §5.1 / Part III §11 |
| confirmatory endpoint | SHARED_THRESHOLD vs LOCAL_THRESHOLD on N-BaIoT natural devices; seed-level Δ in `CV(FPR)` | §8.1 / Part II §5.1 / Part III §11 |
| temporal materiality | `drift_excess_materiality_threshold=0.05`; `material_recovery_ratio_minimum=0.5` | Part III §14 |
| serialization/reload equivalence | absolute tolerance `1e-12`; never used as scientific score identity | §2.2.1–§2.2.2 |

## 4. Dataset and population capability snapshot

The current dataset/population implementation evidence is freshly audited in this cycle. No previous PASS conclusion is current proof; every population row below is re-established from the current roadmap and repository during the Cycle-3 fresh audit.

| Population | Client identity | Locked client count | Natural physical-device claim valid? | FPR-equity metrics | Per-client attack metrics | Genuine chronology | Evidence role | Status |
|---|---:|---:|---|---|---|---|---|---|
| `NBAIOT_NATURAL_DEVICES` | original commercial IoT device | `9` | **Yes** | **Yes** | **Yes**, subject to held-out family support | **No genuine-time claim** from source-row ordering | sole confirmatory + principal mechanism | `NOT_AUDITED` |
| `CICIOT_FILE_CLIENTS` | processed CSV file pseudo-client | `63` | **No** | **Yes** | **Not authorized for DATP claims** | **No** | applicability boundary | `NOT_AUDITED` |
| `NBAIOT_DIRICHLET_CLIENTS` | synthetic Dirichlet client | `20` | **No** | **Yes** | **Yes**, where source attack support remains valid | **No** | controlled heterogeneity sensitivity | `NOT_AUDITED` |
| `EDGE_SENSOR_CLIENTS` | benign sensor-group folder | `10` | **No physical-device claim** | **Yes** | **No** — valid per-client attack assignment unavailable | **No** | independent external benign-equity validation | `NOT_AUDITED` |
| `EDGE_TEMPORAL_CLIENTS` | timestamp-valid sensor-group folder | `9` | **No physical-device claim** | **Yes** | **No** — temporal experiment is benign-only | **Yes** | one-shot temporal boundary | `NOT_AUDITED` |

### 4.1 Dataset boundary closures already retained

- `NBAIOT_NATURAL_DEVICES`: exactly nine physical-device clients; sole confirmatory population.
- `CICIOT_FILE_CLIENTS`: file-defined pseudo-clients only; no inferred physical-device provenance.
- `NBAIOT_DIRICHLET_CLIENTS`: controlled synthetic heterogeneity sensitivity only.
- `EDGE_SENSOR_CLIENTS`: benign operating-point equity only where attack assignment is unavailable.
- `EDGE_TEMPORAL_CLIENTS`: genuine chronology only; one-shot temporal boundary.
- No extra dataset may be added without a roadmap amendment.
- FAMILY_THRESHOLD and attack-sensitive metrics remain typed unavailable wherever the roadmap prohibits them.

## 5. Experiment and analysis implementation catalogue

There is **one row per experiment/analysis**. The old experiment-by-experiment atomic cards are retired. When working on a row, read the full referenced Part-II section and implement/audit it as one coherent unit.

| Experiment ID | Part II | Role | Population | Main variation | Mandatory | Source lines | Status | Migrated detailed credit |
|---|---|---|---|---|---|---|---|---|
| `EXPERIMENT-SHARED-VERSUS-LOCAL-THRESHOLD-SCOPE-CONFIRMATION` | §5.1 | Confirmatory | N-BaIoT natural devices | SHARED_THRESHOLD vs LOCAL_THRESHOLD | `YES` | 2512–2626 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-ANCHOR-REPRODUCTION-GATE` | §5.2 | Reproducibility gate | historical N-BaIoT five-seed anchor | reproduction acceptance | `YES` | 2627–2682 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-SHARED-THRESHOLD-CONSTRUCTION-SENSITIVITY` | §6.1 | Supportive | N-BaIoT natural devices | SHARED_THRESHOLD vs pooled / weighted shared constructions | `YES` | 2708–2753 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-QUANTILE-LEVEL-SENSITIVITY` | §6.2 | Supportive | N-BaIoT natural devices | `q={0.90,0.95,0.975,0.99}` | `YES` | 2754–2785 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-THRESHOLD-ESTIMATOR-SCOPE-SENSITIVITY` | §6.2A | Supportive | N-BaIoT natural devices | `{TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR} x {SHARED,LOCAL}` | `YES` | 2786–2857 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CONTROLLED-NON-IID-SEVERITY` | §6.3 | Supportive | controlled N-BaIoT partitions | heterogeneity severity | `YES` | 2858–2920 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-THRESHOLD-SHARING-GRANULARITY-AND-CLUSTER-STABILITY` | §7.1 | Mechanism | N-BaIoT natural devices | SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD + cluster stability | `YES` | 2923–3031 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-PHYSICAL-FAMILY-EXPLANATORY-ADEQUACY` | §7.2A | Mechanism | N-BaIoT natural devices | within/between-family geometry | `YES` | 3032–3073 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-PER-CLIENT-SCORE-DISTRIBUTION-EXPLANATION` | §7.3 | Mechanism | N-BaIoT natural devices | benign/attack score geometry | `YES` | 3074–3103 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-HETEROGENEITY-BENEFIT-ASSOCIATION-AND-DECISION-SURFACE` | §7.4 | Mechanism | natural + controlled N-BaIoT evidence | JS heterogeneity × calibration support | `YES` | 3104–3243 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-THRESHOLD-MOVEMENT-VERSUS-OPERATING-POINT-HARM` | §7.5 | Mechanism | N-BaIoT natural devices | threshold movement vs FPR/TPR changes + exact device-direction counts | `YES` | 3244–3301 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CALIBRATION-SUPPORT-VERSUS-SHARED-THRESHOLD-BURDEN` | §7.5A | Descriptive mechanism diagnostic | N-BaIoT natural devices | source benign-calibration support vs shared FPR and local-personalization relief | `YES` | 3302–3365 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-NATURAL-DEVICE-HELPED-HARMED-PROFILE-SUPPORT-STRATA` | §7.5B | Mandatory client-impact mechanism diagnostic | N-BaIoT natural devices | exact per-device help/harm/Pareto directions + campaign-fixed 3/3/3 support strata | `YES` | 3366–3512 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-MALWARE-FAMILY-SENSITIVITY-BREAKDOWN` | §7.6 | Supportive trade-off | N-BaIoT natural devices | Mirai/BASHLITE attack-family outcomes | `YES` | 3513–3557 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-EQUITY-UTILITY-PARETO-ANALYSIS` | §7.7 | Supportive synthesis | N-BaIoT natural devices | equity vs utility, no scalar winner | `YES` | 3558–3603 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CALIBRATION-SIZE-ABLATION` | §8.1 | Boundary/supportive | N-BaIoT natural devices | `m={50,100,250,500,1000,5000}` | `YES` | 3606–3718 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CALIBRATION-COLD-START-ONBOARDING-BOUNDARY` | §8.1A | Boundary | N-BaIoT natural devices | low-support onboarding | `YES` | 3719–3754 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-FIXED-LOCAL-GLOBAL-SHRINKAGE` | §8.2 | Threshold variant | N-BaIoT natural devices | fixed λ curve | `YES` | 3755–3786 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CALIBRATION-SIZE-AWARE-SHRINKAGE` | §8.3 | Threshold variant | N-BaIoT natural devices | deterministic λ by `n_k_used` | `YES` | 3787–3804 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-SPLIT-CONFORMAL-LOCAL-CONFORMAL-THRESHOLD-DIAGNOSTIC` | §8.4 | Threshold variant | N-BaIoT natural devices | finite-sample local coverage | `YES` | 3805–3845 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-BOUNDED-PREPROCESSING-GEOMETRY-SENSITIVITY` | §8.5 | Supportive boundary | N-BaIoT natural devices | local StandardScaler vs pooled MinMax protocol identity | `YES` | 3846–3896 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-SHARED-CALIBRATION-CONTRIBUTOR-AVAILABILITY` | §8.6 | Supportive operational sensitivity | N-BaIoT natural devices | exhaustive omission of `m={0,1,2,3,4}` shared-threshold contributors | `YES` | 3897–3989 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-BENIGN-SUMMARY-STATISTICS-COMPARATOR` | §9.1 | Comparator | N-BaIoT natural devices | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | `YES` | 3992–4056 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-KLL-FEDERATED-QUANTILE-SKETCH-THRESHOLD` | §9.2 | Comparator | N-BaIoT natural devices | KLL `k={200,400,800}` | `YES` | 4057–4113 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-FIXED-COEFFICIENT-LARIDI-SENSITIVITY` | §9.3 | Optional supplement | N-BaIoT natural devices | fixed coefficient sensitivity only | `NO` | 4114–4129 | OPTIONAL_DEFERRED | — |
| `EXPERIMENT-EDGE-IIOTSET-EXTERNAL-BENIGN-EQUITY-VALIDATION` | §10.1 | External validation | Edge-IIoTset | independent-dataset benign equity | `YES` | 4132–4194 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-CICIOT2023-FILE-LEVEL-BOUNDARY` | §10.2 | Applicability boundary | CICIoT2023 file pseudo-clients | available-data boundary | `YES` | 4195–4218 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-FEDPROX-AGGREGATION-MECHANISM-ACTIVATION-STRESS-TEST` | §11.1 | Training stress | N-BaIoT natural devices | FedProx μ grid + local-update drift diagnostics | `YES` | 4244–4319 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-DITTO-MODEL-PERSONALIZATION-STRESS-TEST` | §11.2 | Model-personalization stress | N-BaIoT natural devices | Ditto λD grid / absorption | `YES` | 4320–4429 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-FEDAVG-POST-TRAINING-CLIENT-LOCAL-FINE-TUNING` | §11.2A | Simple model-personalization stress | N-BaIoT natural devices | exactly 10 benign-training local epochs + common absorption diagnostics | `YES` | 4430–4501 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-ONE-SHOT-RECALIBRATION-UNDER-GENUINE-CHRONOLOGY` | §12.1 | Temporal boundary | Edge-IIoTset temporal population | static vs frozen-future vs one-shot recalibration | `YES` | 4504–4646 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-ALERT-BURDEN-EXPERIMENT` | §13.1 | Operational interpretation | valid rate-bearing population | alert-count translation | `YES` | 4649–4693 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-THRESHOLD-STAGE-COMMUNICATION-STORAGE-RUNTIME-ACCOUNTIN` | §13.2 | Operational accounting | applicable methods | payload, storage, threshold-stage timing | `YES` | 4694–4737 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap |
| `EXPERIMENT-ROBUST-CLUSTER-MEDIAN-THRESHOLD` | §14.1 | Optional analysis | N-BaIoT natural devices | cluster median vs mean threshold | `NO` | 4742–4755 | OPTIONAL_DEFERRED | — |
| `EXPERIMENT-ADDITIONAL-EQUITY-INDICES` | §14.2 | Optional analysis | applicable populations | Jain/Gini/IQR/range diagnostics | `NO` | 4756–4768 | OPTIONAL_DEFERRED | — |
| `EXPERIMENT-EXTENDED-SECONDARY-UNCERTAINTY` | §14.3 | Optional analysis | applicable experiments | secondary paired uncertainty | `NO` | 4769–4779 | OPTIONAL_DEFERRED | — |

**Execution priority:** mandatory rows first. The three optional Part II §14 analyses and the fixed-coefficient Laridi supplement remain `OPTIONAL_DEFERRED` until every mandatory implementation row and implementation-relevant gate is closed.

## 6. Evaluation, metric, statistical, terminal-detector, and temporal groups

These grouped rows replace the old 65-row metric/statistical queue plus repetitive one-line checklists. Exact formulas and prose stay in Part III of the roadmap. Retained formula mappings are credited but do not by themselves close prose semantics, runtime wiring, or statistical-unit correctness.

| ID | Coherent scope | Roadmap owner | Status | Migrated formula credit | Legacy child IDs covered |
|---|---|---|---|---|---|
| `EVAL-01` | Evaluation foundations and eligible populations | Part III §§1.1–3.4 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-001, METRIC-002, METRIC-003, METRIC-004, METRIC-005, METRIC-006, METRIC-007 |
| `EVAL-02` | Per-client predictive metrics and held-out target transfer | Part III §§4.1–4.8 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-008, METRIC-009, METRIC-010, METRIC-011, METRIC-012, STAT-001, METRIC-013, METRIC-014 |
| `EVAL-03` | H_TAUTOLOGY held-out rebuttal | Part III §4.8A | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-015 |
| `EVAL-04` | Cross-client FPR dispersion, lower-tail and equity semantics | Part III §§5.1–6.3 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-016, METRIC-017, METRIC-018, METRIC-019, METRIC-020, METRIC-021, METRIC-022, METRIC-023, METRIC-024 |
| `EVAL-05` | Aggregate utility summaries | Part III §§7.1–7.3 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-025, METRIC-026, METRIC-027 |
| `EVAL-06` | Threshold-estimation error, target attainment and sample efficiency | Part III §§8.1–8.4 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-028, METRIC-029, METRIC-030, METRIC-031 |
| `EVAL-07` | Federated summary-statistics decomposition | Part III §§9.1–9.3 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-032, METRIC-033, METRIC-034 |
| `EVAL-08` | Operational burden, communication, timing and Ditto state accounting | Part III §§10.1–10.4 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | METRIC-035, METRIC-036, METRIC-037, METRIC-038 |
| `STAT-01` | Confirmatory paired contrast, effect sizes, BCa and sign evidence | Part III §§11.1–12.1A | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-002, STAT-003, STAT-004, STAT-005, STAT-006, STAT-007 |
| `STAT-02` | Secondary inference, multiplicity, nested replicates, association and cluster stability | Part III §§12.1–12.7 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-008, STAT-009, STAT-010, STAT-011, STAT-012, STAT-013, STAT-014 |
| `STAT-03` | Terminal detector and checkpoint restrictions | Part III §§13.1–13.3 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-015, STAT-016, STAT-017 |
| `STAT-04` | Temporal diagnostics | Part III §14.1 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-018 |
| `STAT-05` | Precision, leave-one-device-out influence and numerical discipline | Part III §§15.1–15.2 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-019, STAT-020, STAT-021 |
| `REPORT-SEM-01` | Mandatory figure/table statistical semantics | Part III §§16.1–16.5 | `NOT_AUDITED` | fresh Cycle-2 audit: implementation re-inspected and verified against the current roadmap | STAT-022, STAT-023, STAT-024, STAT-025, STAT-026, STAT-027 |

## 7. Mandatory manuscript-facing deliverables

The roadmap remains authoritative for the exact contents behind each view/table.

| ID | Deliverable | Roadmap owner | Requirement | Status |
|---|---|---|---|---|
| `REPORT-01` | Causal intervention map | Part III §16.1 | mandatory main-text figure | `NOT_AUDITED` |
| `REPORT-02` | Confirmatory paired-effect view | Part III §16.2 | mandatory main-text figure | `NOT_AUDITED` |
| `REPORT-03` | Confirmatory equity–utility/client-impact bundle | Part III §16.2A | mandatory companion table | `NOT_AUDITED` |
| `REPORT-04` | Equity–utility Pareto view | Part III §16.3 | mandatory main-text or first-supplement figure | `NOT_AUDITED` |
| `REPORT-05` | FedProx mechanism-activation view | Part III §16.4 | mandatory stress-test figure | `NOT_AUDITED` |
| `REPORT-06` | Mandatory synthesis tables | Part III §16.5 | all roadmap-listed synthesis tables | `NOT_AUDITED` |

## 8. Claim-survival matrix

This table is a reporting gate, not a post-hoc experiment-selection menu. A failed claim is narrowed; an alternative experiment may not rescue it.

| Proposed claim | Evidence required | Survival condition | Required null/opposite wording |
|---|---|---|---|
| Local calibration reduces natural-device FPR dispersion | NBAIOT_NATURAL_DEVICES SHARED_THRESHOLD vs LOCAL_THRESHOLD confirmatory endpoint | 95% BCa lower bound for \(\overline\Delta=CV_{\mathrm{shared}}-CV_{\mathrm{local}}\) is `> 0` | “The confirmatory analysis did not establish a reduction in cross-client FPR dispersion.” |
| The effect is not merely an artifact of arithmetic-mean SHARED_THRESHOLD | exact pooled, sample-weighted, `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`, and `FEDERATED_BENIGN_SUMMARY_THRESHOLD` shared controls | the LOCAL_THRESHOLD contrast is positive in mean paired effect for every mandatory shared construction; any non-positive construction is disclosed and blocks the blanket robustness wording | identify the shared construction that removes or reverses the effect |
| The scope effect is not unique to the `q=0.95` estimator family | fixed-score `TYPE7_Q95` versus `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` 2-by-2 sensitivity | mean shared-to-local `CV(FPR)` gain is positive under both estimator families; no estimator may replace the confirmatory q95 endpoint | identify the estimator family under which the scope effect disappears or reverses |
| Greater benign score heterogeneity is associated with larger personalization benefit | locked JS analysis plus population-C interaction model | directional association is positive in the predeclared Spearman/regression summaries; uncertainty and influence diagnostics are shown | “The measured score heterogeneity was not a sufficient predictor of DATP benefit.” |
| Calibration support changes the useful personalization level | calibration-size experiment plus heterogeneity × support interaction | predeclared curves show a reproducible support-dependent change; no single `m` may be selected post hoc | report no material calibration-support dependence |
| CLUSTER_THRESHOLD provides a stable middle ground | canonical CLUSTER_THRESHOLD stability + recovery metrics | positive CLUSTER_THRESHOLD recovery of the SHARED_THRESHOLD→LOCAL_THRESHOLD gap together with non-degenerate clustering; stability metrics must be shown | describe CLUSTER_THRESHOLD as unstable, non-beneficial, or both |
| Threshold personalization retains incremental benefit after bounded client-model adaptation | `FEDAVG_LOCAL_FINE_TUNING` 2×2 plus canonical Ditto `lambda_D=1.0` 2×2 | for **each** route, the arithmetic mean of the ten raw `DeltaScope_s` values is `>0`; separately report every valid seed-level `ScopeAbsorption` using §7.2B bands | identify by name every route whose mean raw `DeltaScope` is `<=0`, and report partial/large absorption or reversal exactly as defined; no route may be silently dropped |
| One-shot recalibration recovers threshold aging | temporal protocol | `drift_excess >= 0.05` and `recovery_ratio >= 0.5` | report degradation without recovery or no detectable temporal degradation |

### 8.1 Negative evidence rule

Null, reversed, infeasible, unstable, unfavorable-client, attenuation, absorption, undercoverage, and no-recovery outcomes required by Part I §10.D.11 remain publishable evidence. Do not filter them by favorable seed, policy, client subset, hyperparameter, or dataset.


## 9. Scope and typed-unavailability enforcement

Scope boundaries are **not a separate 23-row audit queue**. They are enforced through `SCIENTIFIC-09` through `SCIENTIFIC-14`, experiment applicability records, typed scientific states, claim validation, and Gates O/R.

Mandatory boundary principles:

- no inferred CICIoT physical devices;
- no extra dataset beyond the roadmap;
- no formal privacy, Byzantine/poisoning, hardware/deployment, fleet-scale, continuous-drift, broad FL-benchmark, or broad conformal claim;
- no expansion of the locked PFL/optimizer/threshold-estimator families;
- no replacement of missing implementation with `UNAVAILABLE_AS_SPECIFIED`;
- no silent `None`/NaN for roadmap-defined scientific unavailability;
- exact roadmap-defined typed unavailability states must be represented by typed identities with provenance/reason;
- accepted limitations are disclosed, not “fixed” by silently expanding scope.

The exact unavailability identities and conditions are read from the current roadmap when implementing the owning evaluation/analysis row; do not maintain a second duplicated enum checklist here.

## 10. Gates A–R — progress-preserving summary

The old 205 gate rows are preserved in the progress archive. This active matrix keeps **one row per gate**. Do not re-run a fully PASS gate unless an impacted semantic owner changed. For partial gates, audit only the listed unresolved gate IDs. Gates requiring real campaign/submission artifacts remain evidence conditions rather than reasons to rewrite already-correct code.

| Gate | Detailed checks | PASS | Pending | FAIL | Active status | Unresolved detailed IDs |
|---|---:|---:|---:|---:|---|---|
| Gate A | 12 | 0 | 12 | 0 | `NOT_AUDITED` | ALL |
| Gate B | 9 | 0 | 9 | 0 | `NOT_AUDITED` | ALL |
| Gate C | 10 | 0 | 10 | 0 | `NOT_AUDITED` | ALL |
| Gate D | 10 | 0 | 10 | 0 | `NOT_AUDITED` | ALL |
| Gate E | 8 | 0 | 8 | 0 | `NOT_AUDITED` | ALL |
| Gate F | 13 | 0 | 13 | 0 | `NOT_AUDITED` | ALL |
| Gate G | 8 | 0 | 8 | 0 | `NOT_AUDITED` | ALL |
| Gate H | 12 | 0 | 12 | 0 | `NOT_AUDITED` | ALL |
| Gate I | 13 | 0 | 13 | 0 | `NOT_AUDITED` | ALL |
| Gate J | 11 | 0 | 11 | 0 | `NOT_AUDITED` | ALL |
| Gate K | 9 | 0 | 9 | 0 | `NOT_AUDITED` | ALL |
| Gate L | 12 | 0 | 12 | 0 | `NOT_AUDITED` | ALL |
| Gate M | 14 | 0 | 14 | 0 | `NOT_AUDITED` | ALL |
| Gate N | 20 | 0 | 20 | 0 | `NOT_AUDITED` | ALL |
| Gate O | 6 | 0 | 6 | 0 | `NOT_AUDITED` | ALL |
| Gate P | 7 | 0 | 7 | 0 | `NOT_AUDITED` | ALL |
| Gate Q | 8 | 0 | 8 | 0 | `NOT_AUDITED` | ALL |
| Gate R | 23 | 0 | 23 | 0 | `NOT_AUDITED` | ALL |

### 10.1 Known evidence-only blockers

- `GATE-R-012`: submission-time novelty-survival literature evidence is not yet retained. The supporting validation implementation exists; this remains `EVIDENCE_REQUIRED` until an actual submission date/search record exists.
- `GATE-R-023`: a complete retained reproducibility-release bundle has not yet been generated. Builder/manifest validation is implemented; this remains `EVIDENCE_REQUIRED` until the real release bundle exists.

These are **not reasons to reopen unrelated implementation PASS rows**.

## 11. Reproducibility-release bundle

Required logical payload:

```text
ROADMAP_LOCK.md
MANIFEST_SHA256.csv
MANIFEST_SHA256.sha256
SEEDS.csv
DATA_PROVENANCE/
SPLIT_IDENTITY/
PREPROCESSING/
MODELS/
SCORES/
THRESHOLDS/
METRICS/
STATISTICS/
FIGURE_TABLE_DATA/
AUDIT_REPORTS/
ENVIRONMENT/
README_REPRODUCIBILITY.md
```

| Release responsibility | Current state | Closure |
|---|---|---|
| Release builder and exact inventory validation | `NOT_AUDITED` | re-audited unless release code changes |
| SHA-256 manifest schema/validation | `NOT_AUDITED` | re-audited unless manifest schema changes |
| Runtime/environment metadata capture | `NOT_AUDITED` | re-audited unless environment schema changes |
| Release-state typing (`PUBLIC`, `BLINDED_ARCHIVE`, `WITHHELD_LICENSE_RESTRICTED`) | `NOT_AUDITED` | re-audited unless release-state semantics change |
| Submission-time literature date/search record | `EVIDENCE_REQUIRED` | actual submission-stage evidence |
| Complete real campaign release bundle | `EVIDENCE_REQUIRED` | generate only from retained campaign outputs |

The final publication-readiness decision still requires the roadmap-defined anchor/campaign, causal-isolation, statistical, novelty, unavailability, reconstruction, release, claim-to-evidence, negative-evidence, and limitation checks.

## 12. Repository audit and remediation workflow

Use this loop until every mandatory **implementation** row is closed:

1. Read the referenced roadmap section completely.
2. Inspect the single semantic owner, callers, tests, artifacts, and reverse dependencies.
3. Reuse/refactor existing correct code before creating new code.
4. Fix the whole coherent capability/experiment chunk; no backwards compatibility or stale aliases.
5. Remove replaced/dead/duplicate implementations at their callers.
6. Update only the active matrix rows and gates affected by that chunk.
7. After a substantial chunk, run the relevant parallel tests plus Ruff/Pyright/Pylance/formatting/static checks.
8. Fix all failures caused or exposed by the chunk.
9. Perform a bounded integration/reachability audit for that chunk.
10. Commit after a meaningful completed phase.
11. Continue with the next unresolved mandatory row.
12. After mandatory implementation closure, run one final whole-repository audit and then the implementation-relevant portions of Gates A–R.

### 12.1 Re-audit rule

A PASS row is reopened only when at least one of the following is true:

- its authoritative roadmap text changed;
- its semantic-owner code changed;
- a caller/artifact/schema/protocol identity it depends on changed;
- a test or retained evidence demonstrates contradiction;
- a final integration audit proves it unreachable or semantically conflicting.

Changing an unrelated package is not sufficient reason to reopen it.

### 12.2 Large-check rule

Do not run the full static/test suite after every small edit or commit. Create/adapt tests continuously, but execute broad validation after a large coherent chunk and at final closure. Targeted tests may be run when needed to validate the chunk being changed.

## 13. Required implementation end state

Implementation work is complete when:

- all mandatory rows in Sections 2, 4, 5, 6, and 7 are `PASS`, or have a roadmap-valid explicit non-implementation state;
- every `OPTIONAL_DEFERRED` row remains clearly optional and cannot block mandatory closure;
- every implementation-relevant Gate A–R check is PASS;
- campaign/submission-only evidence conditions are correctly left as `EVIDENCE_REQUIRED` until those stages;
- no stale/backwards-compatible/duplicate/dead semantic implementation remains;
- runtime callers exercise the intended production paths;
- typed scientific identities/unavailability states replace primitive ambiguity;
- broad tests/static checks pass after the final implementation chunk;
- one final roadmap-to-repository and repository-to-roadmap audit finds no scientific drift or orphan implementation.

## Appendix A — Progress archive contract

The companion file `DATP Core Audit Progress Archive.md` preserves the detailed evidence that was removed from this active matrix. It contains:

- the 95 legacy curated scientific-contract rows;
- all 77 completed formula mappings;
- all 6 completed literal mappings;
- all 380 adjudicated atomic requirements;
- all 205 detailed Gate A–R rows.

**Do not use the archive as an execution queue.** Its purpose is only to preserve already-spent audit work and provide historical evidence when a migrated row is legitimately reopened.