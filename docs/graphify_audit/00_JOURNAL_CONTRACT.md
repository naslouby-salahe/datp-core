# DATP-Core journal implementation contract

Authority: `docs/Journal_Extension_Master_Roadmap.md`, read in full before this audit.  This contract is a compact implementation-facing extraction; the roadmap remains authoritative where wording differs.

## Scientific identity and non-negotiable invariants

DATP-Core is a controlled study of **threshold-calibration scope** for a frozen federated anomaly detector.  The sole confirmatory result is Regime A (the nine natural N-BaIoT devices), B1 versus B2, `CV(FPR)`, ten paired training seeds, and a two-sided 95% BCa interval over paired seed deltas.  The training seed—not row, client, checkpoint, window, or nested resample—is the independent replication unit.

For a B1–B4 comparison within a seed and regime, the selected detector state, model/preprocessing protocol, client identities, split records, calibration records/scores, test records/scores/labels, eligibility, quantile, and metric implementation are fixed.  Only calibration scope changes.  Threshold fitting, eligibility, checkpoint selection, comparator/model selection, cluster setup, shrinkage setup, and external client construction are benign-only and outcome-blind.  Calibration and evaluation must be disjoint.

Eligibility is `benign_calibration_count >= 100`, determined before evaluation and shared by all compared policies.  Predictions use `attack iff error > threshold`; no denominator epsilon is permitted for CV.  Undefined metrics must stay typed/unavailable, never become zero or an unqualified NaN.

## Protocol identities and fixed variables

| Responsibility | Required semantics / fixed invariants | Inputs → outputs |
| --- | --- | --- |
| Confirmatory preprocessing | `FEDERATED_CLIENT_LOCAL_STANDARD`: per-client `StandardScaler`, fit on benign train only; persisted with skops; transform-only calibration/test; constant scale semantics, unclipped output, 1e-12 serialization equivalence. | benign train records → per-client fitted transformers and transformed partitions |
| Supportive federated preprocessing | `FEDERATED_POOLED_MIN_MAX`: pooled benign federated train fit, not a replacement for confirmatory preprocessing. | pooled train → fitted transformer |
| B0 preprocessing/reference | `CENTRALIZED_POOLED_MIN_MAX`; independent centralized model/state, pooled benign calibration threshold; never federated weights/scores relabelled as B0. | pooled data → independently trained centralized reference |
| Missing/non-finite data | no imputation, zero-fill, clipping/capping, infinity replacement, or label inference. N-BaIoT fails declared non-finite inputs; CIC has outcome-blind finite/recognized-label gate with lossless provenance; Edge excludes bad numeric model-input rows with provenance. | canonical rows → validated eligibility/provenance |
| Training/checkpoint | FedAvg: one local epoch, full participation, locked model/hyperparameters. Journal primary round is declared terminal `200` (`FIXED_TERMINAL_MAXIMUM_ROUND`), candidates 25/50/75/100/125/150/200; no score/test/policy selection. | transformed benign train → checkpointed model |
| Scoring | frozen selected model and frozen preprocessing; higher MSE reconstruction error means greater anomaly evidence; all threshold policies reuse score sets. | model + transformed calibration/test → named score artifacts |
| Statistics | client-first metrics; `ddof=0`; paired B1–B2 deltas; BCa over ten pairs; no pseudoreplication; secondary Wilcoxon/rank-biserial stay secondary. | per-client held-out metrics → seed estimates/inference |

## Policies, evidence roles, and exact semantics

| Policy / programme | Evidence role | Required construction and outputs | Prohibitions |
| --- | --- | --- | --- |
| B0 centralized reference | contextual reference | independently train pooled centralized AE; pooled benign quantile. | Not a FedAvg model with a pooled threshold; not in B1–B4 causal ladder. |
| B1 shared | confirmatory anchor | each eligible client computes local benign q-quantile; threshold is arithmetic mean of those local quantiles; q=.95 canonical. | Not the exact pooled quantile. |
| B2 local | confirmatory comparator | eligible client deploys its own benign q-quantile. | Must not be selected/retrained or assumed universally superior. |
| B3 family | mechanism | mean of eligible local thresholds per validated physical-device family. | Only Regime A/defensible independent taxonomy; no attack-derived families. |
| B4 cluster | mechanism | benign score fingerprint `[mean, std, skewness, p95]`, standardized fingerprint, locked k-means, K=3 canonical; mean local threshold by cluster. | Not model clustering/privacy/confirmatory; alternative K exploratory. |
| Pooled / weighted shared | supportive controls | exact pooled q and calibration-size-weighted local threshold constructions on frozen scores. | Cannot replace locked B1. |
| Quantile sensitivity | supportive | q in `.90,.95,.975,.99`, full curve. | Cannot replace canonical q post hoc. |
| Shrinkage | supportive variant | `lambda*local + (1-lambda)*shared`, lambda grid 0,.25,.5,.75,1; size-aware function predeclared, bounded and size-only. | No test-informed lambda selection. |
| B2-conf | supportive diagnostic | finite-sample adjusted local benign conformal quantile alpha=.05 and held-out benign coverage. | No universal conditional-coverage claim or confirmatory replacement. |
| B-FedStatsBenign | mandatory comparator stress test | benign-only client n/mean/variance/exceedance summaries, full within+between pooled variance, matched target exceedance, communication record. | Never called Laridi-faithful; no anomaly information or F1 tuning. |
| FedProx | training-side stress test | separate models/scores; mu `.001,.01,.1,1`; primary mu by predeclared minimum terminal benign federated training loss. | Does not enter / alter FedAvg ladder. |
| Ditto | model-personalization stress test | distinct global state and persistent per-client states, proximal personalized objective, separate scoring/evaluation. | Never aggregate personalized states; never call a fallback Ditto. |

## Experiment/responsibility matrix

| Regime / required programme | Role | Dataset/population and required paths | Evaluation/artifacts and boundaries |
| --- | --- | --- | --- |
| Regime A: N-BaIoT physical-device anchor | **Confirmatory** for B1 vs B2; also support/mechanism/stress | nine actual devices/natural clients; FedAvg, q=.95, ten paired seeds; B0–B4 where valid. | all nine visible; per-client FPR/TPR/BA/Macro-F1/AUROC control, CV/IQR/range/worst FPR, BCa; family taxonomy B3 valid. |
| Regime B-a: CICIoT2023 file-defined pseudo-clients | applicability boundary | 63 file-defined pseudo-clients; lossless canonical artifact then recognized-label+finite-feature gate; no verified physical identities/timestamps. | B0/B1/B2/B4 and benign distribution diagnostics only; no device claims, B3, fabricated chronology, or physical repartitioning. |
| Regime C: controlled N-BaIoT heterogeneity | supportive sensitivity | twenty synthetic clients; locked Dirichlet alpha `.1,.3,.5,1,10,IID`; B1/B2/B4. | retain pre-specified partitions, coverage and JS diagnostics; associative/non-confirmatory; B3 only if meaningful taxonomy retained. |
| Regime D: Edge-IIoTset static | external validation | ten benign sensor-group clients; immutable 33-column numeric schema and 33-25-17-11-8-11-17-25-33 AE; B1/B2/B4/FedStats etc. | benign FPR equity only; B3 omitted; per-client attack metrics/AUROC explicitly unavailable (not estimated). |
| Regime D-temporal | temporal boundary | nine chronological Edge groups (exclude Modbus); stable 55/15/10/20 history train/calibration/future recalibration/future eval, plus matched static reference. | frozen vs one-shot recalibrated thresholds; strict past→future isolation; no streaming/drift claims. |
| Family/cluster mechanisms | mechanism | Regime A mandatory, D B4 optional; fingerprints only benign calibration scores. | membership, K, ARI, cluster sizes/singletons and within/across dispersion artifacts. |
| Calibration robustness | boundary / variants | deterministic nested subsamples 50/100/250/500/1000/5000 where supported. | replicate summaries nested within seed; no extra N; full curves and unavailable clients. |
| Operational alert burden | supportive | only real/cited benign decision rate. | omit if rate unavailable; not deployment validation. |

## Reporting and claim boundaries

Primary metric is unweighted cross-client `CV(FPR)` with IQR/range/worst FPR beside it. AUROC is unchanged for a fixed-score ladder and is only a detector control. Supportive, external, mechanism, stress, and exploratory evidence cannot rescue a failed confirmatory result. Edge attack-sensitive outcomes, unsupported client identity, and undefined metrics must be recorded as unavailable with reasons. No formal privacy, deployment readiness, broad FL benchmark, fleet-scale, adversarial-defense, continuous drift, or universal-superiority claim is within scope.

## Audit decision rules derived from the contract

An unreachable symbol is not dead until its source, callers/callees, real roots, and required programme responsibility are reconciled. A journal-required but unreachable implementation is `WIRE_REQUIRED` or `FIX_INCOMPLETE`; an implementation is not wired merely because it exists. Deletion additionally requires a positive finding that the journal does not require the responsibility, or that an authoritative live implementation supersedes it.
