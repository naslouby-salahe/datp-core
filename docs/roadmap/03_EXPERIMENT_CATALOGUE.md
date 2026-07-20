# 03 — Experiment Catalogue

## Document purpose

This catalogue defines the complete DATP journal-extension experiment programme in a navigable, section-driven form. It explains what is executed, what remains fixed, why each experiment exists, which evidence role it may support, what must be reported, and how weak, null, contradictory, or infeasible outcomes are handled.

The document deliberately avoids compact experiment matrices and opaque coded identifiers. Each experiment is identified by a descriptive scientific title that can be understood without consulting a code catalogue.

## Canonical responsibility

This file owns:

- dataset and experimental-regime definitions;
- experimental populations and client definitions;
- threshold-policy and comparator participation by experiment;
- experimental factors, controls, and fixed elements;
- experiment-specific procedures;
- minimum required outputs;
- dependencies and feasibility gates;
- evidentiary classification;
- experiment-specific failure and boundary interpretations;
- execution ordering;
- suppressed, rejected, optional, and future experiments.

This file does not own:

- the final wording or survival of manuscript claims;
- canonical metric formulas and statistical implementation details;
- software architecture, classes, modules, configuration schemas, or paths;
- manuscript prose;
- historical audit reports.

Those responsibilities belong respectively to:

- [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md);
- [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md);
- [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md);
- [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md);
- [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md).

---

# 1. How to read this catalogue

## 1.1 Evidence-role vocabulary

Every experiment has exactly one primary evidentiary role.

**Confirmatory**  
Tests the sole locked journal endpoint. Only the Regime A B1-versus-B2 comparison on `CV(FPR)` is confirmatory.

**Supportive**  
Tests robustness of the confirmatory interpretation without becoming a second confirmatory claim.

**Mechanism analysis**  
Explains why, when, or for which clients the threshold-scope effect appears. Mechanism analyses may support interpretation but cannot rescue a failed confirmatory endpoint.

**Threshold variant**  
Tests a modified threshold-estimation rule while preserving the fixed detector. Variants are evaluated as alternatives or boundary probes, not silently merged into B1–B4.

**External validation**  
Tests whether the operating-point effect appears on an independent dataset under a separately audited client definition.

**Stress test**  
Changes the training algorithm or model-personalization mechanism and therefore sits outside the controlled B1–B4 causal ladder.

**Boundary condition**  
Identifies settings where DATP is weak, unnecessary, infeasible, or not interpretable.

**Exploratory**  
Generates descriptive or hypothesis-forming evidence that cannot be promoted after results are seen.

**Suppression evidence**  
Records why an intended experiment cannot be executed validly.

**Future work**  
Names a scientifically related extension that is not executed or claimed in this journal programme.

## 1.2 Experiment specification format

Each mandatory experiment is documented using the same subsections:

- **Scientific role**
- **Question**
- **Why the experiment is necessary**
- **Population and inputs**
- **Fixed elements**
- **Experimental factors**
- **Comparison set**
- **Procedure**
- **Required outcomes**
- **Statistical unit and analysis**
- **Interpretation rules**
- **Dependencies and feasibility**
- **Required artifacts**
- **Prohibited uses**

This structure replaces the previous matrix rows and prevents important requirements from being hidden in dense cells.

---

# 2. Scientific execution invariants

The following rules apply to every experiment unless a stress-test section explicitly states otherwise.

## 2.1 Fixed-detector causal isolation

For the B1–B4 threshold-scope ladder:

- one FedAvg autoencoder is trained per seed;
- the selected encoder state is frozen;
- the same calibration and test score artifacts are reused across B1, B2, B3, and B4;
- threshold scope is the only manipulated causal variable;
- no policy-specific retraining is permitted;
- no threshold policy may alter preprocessing, training data, model parameters, score generation, test labels, or client eligibility.

A difference between B1 and B2 is therefore interpreted as an operating-point effect of threshold-calibration scope, not as a model-quality difference.

## 2.2 Benign-only threshold calibration

All threshold policies and DATP-compatible threshold comparators use benign calibration data only.

Attack-labelled data may be used only for held-out evaluation when the regime supports valid per-client attack assignment. Attack data must never:

- determine a threshold;
- select a quantile;
- select a checkpoint;
- select a FedProx coefficient;
- select a personalization coefficient;
- decide which clients are included;
- repair an infeasible experiment.

This boundary is scientifically important because Laridi et al. aggregate information from both normal and anomalous validation data when constructing their federated threshold. `B-FedStatsBenign` is therefore a DATP-compatible comparator inspired by the summary-statistics design space, not a faithful reproduction of the Laridi method.[^laridi]

## 2.3 Paired experimental design

Within each seed, policies compared in the same experiment must receive:

- the same trained model when the experiment belongs to the fixed-detector ladder;
- the same client population;
- the same split manifests;
- the same calibration records before any declared subsampling;
- the same held-out evaluation records;
- the same score artifacts;
- the same eligibility rule;
- the same metric implementation.

The training seed is the independent replication unit. Clients, records, checkpoints, windows, or sweep cells are not treated as independent scientific replications.

## 2.4 Eligibility

The canonical eligibility threshold is:

```text
n_k >= 100 benign calibration samples
```

Only eligible clients enter the primary cross-client `CV(FPR)` calculation.

Every result must report:

- total clients in the regime;
- eligible clients;
- excluded clients;
- exclusion reasons;
- eligibility coverage;
- whether the compared policies used the same eligible population.

Eligibility cannot be changed after examining test outcomes.

## 2.5 Checkpoint discipline

The journal protocol trains to a maximum of 200 rounds and evaluates checkpoints at:

```text
25, 50, 75, 100, 125, 150, 200
```

Regime A selects one global primary checkpoint using the locked non-test selection rule. That checkpoint is used for every main Regime A result.

Forbidden practices include:

- selecting checkpoints independently for B1 and B2;
- selecting by test AUROC;
- selecting by attack labels;
- choosing a checkpoint that maximizes the DATP effect;
- selecting a different main checkpoint for a supportive experiment;
- suppressing weak checkpoint trajectories.

Other checkpoints are stability evidence only.

## 2.6 Negative-result discipline

Every mandatory experiment is reportable when it produces:

- a strong expected effect;
- a weak effect;
- a null effect;
- a reversed effect;
- unstable estimates;
- an infeasibility result.

No experiment may be removed because its result is unfavorable. A supportive or mechanism experiment cannot replace the confirmatory endpoint.

---

# 3. Threshold policies and comparison methods

## 3.1 Centralized reference: B0

B0 is a pooled-data centralized autoencoder reference with a pooled benign threshold.

It is included to show the performance of a privacy-incompatible centralized reference. It is not part of the federated threshold-scope causal ladder and must never be presented as another B1–B4 policy.

B0 must use its own centralized model and provenance. FedAvg-generated scores cannot be relabelled as B0.

## 3.2 Shared threshold: B1

Each eligible client computes its local benign `q`-quantile. The server forms one shared threshold by taking the arithmetic mean of the local quantiles.

At the canonical setting:

```text
q = 0.95
```

Every eligible client is evaluated using the same B1 threshold.

B1 is the shared-scope anchor for the confirmatory comparison.

## 3.3 Per-client threshold: B2

Each eligible client uses its own benign `q`-quantile as its deployed threshold.

At the canonical setting:

```text
q = 0.95
```

B2 is the local-scope anchor and the confirmatory comparator.

B2 is not described as universally superior. It may reduce cross-client false-positive dispersion while worsening detection quality for clients with weak benign–attack score separation.

## 3.4 Family threshold: B3

B3 groups N-BaIoT clients by the locked physical-device family taxonomy and assigns one family-level mean threshold to clients in the same family.

B3 is available only where a defensible family taxonomy exists. It is therefore:

- available in Regime A;
- unavailable in Regime C unless the synthetic partition preserves a meaningful family mapping;
- omitted from Edge-IIoTset because no equivalent family taxonomy is established;
- unavailable for CICIoT2023 file-defined pseudo-clients.

B3 is a mechanism baseline, not a confirmatory comparator.

## 3.5 Cluster threshold: B4

B4 creates taxonomy-free groups from a four-scalar benign reconstruction-error fingerprint:

```text
mean(error)
standard deviation(error)
skewness(error)
p95(error)
```

The canonical main-paper cluster count is:

```text
K = 3
```

The threshold assigned to a cluster is the mean of the local thresholds of its member clients.

Other cluster counts are granularity sensitivity analyses and remain exploratory. `K = 9` is not promoted as a main configuration.

B4 clustering is a threshold-sharing mechanism on a fixed detector. It is not a model-clustering method, a privacy mechanism, or a new clustering algorithm.

## 3.6 Shared-threshold construction controls

Two shared-threshold controls test whether the B1 result is merely an artifact of averaging local quantiles:

**Pooled shared quantile**  
The exact `q`-quantile of the pooled benign calibration scores.

**Sample-weighted shared threshold**  
A shared threshold formed by weighting local threshold contributions by eligible benign calibration size.

These constructions are supportive controls. They do not replace B1 as the locked confirmatory anchor.

## 3.7 Local–global shrinkage threshold

For client \(k\):

\[
\tau_k(\lambda)
=
\lambda \tau_{k,\mathrm{local}}
+
(1-\lambda)\tau_{\mathrm{shared}}
\]

The locked sensitivity grid is:

```text
lambda in {0.00, 0.25, 0.50, 0.75, 1.00}
```

Interpretation:

- `lambda = 0` is the shared-threshold endpoint;
- `lambda = 1` is the local-threshold endpoint;
- intermediate values trade personalization against estimation stability.

A calibration-size-aware variant may replace a fixed `lambda` with a pre-specified function `lambda(n_k)`. That function must be fixed before test evaluation.

## 3.8 Split-conformal local threshold: B2-conf

B2-conf treats benign reconstruction errors as nonconformity scores and forms a finite-sample-adjusted local quantile at significance level:

```text
alpha = 1 - q
```

The main diagnostic setting is:

```text
alpha = 0.05
```

Classical split conformal inference motivates the finite-sample rank correction under exchangeability.[^split-conformal] Federated and heterogeneous settings require additional caution because cross-client heterogeneity can violate global exchangeability; recent federated conformal work explicitly treats label shift and agent heterogeneity as nontrivial validity problems.[^fed-conformal-label-shift][^fed-conformal-heterogeneity]

Accordingly:

- B2-conf is a supportive threshold variant;
- coverage is evaluated empirically on held-out benign data;
- no universal conditional-coverage claim is made;
- a coverage miss is reported as a limitation of the adaptation, not hidden;
- B2-conf does not become a new confirmatory endpoint.

## 3.9 Benign federated summary-statistics comparator

`B-FedStatsBenign` is the matched, benign-only federated threshold comparator.

It communicates pre-specified benign summary statistics and constructs a shared threshold without using anomalous validation data. Its operating point must be matched to the DATP quantile target rather than selected to maximize F1.

The comparison must clearly distinguish:

- exact pooled benign quantile;
- arithmetic mean of local quantiles;
- sample-weighted shared construction;
- benign summary-statistics threshold;
- local per-client quantiles.

A Laridi-faithful implementation is not executed because Laridi et al. use normal and anomalous validation summaries, violating DATP’s benign-only threshold contract.[^laridi]

## 3.10 FedProx stress-test model

FedProx modifies the local training objective by adding a proximal penalty that constrains local deviation from the current global model. It was proposed to address statistical and systems heterogeneity and is appropriately used here as an aggregation-side stress test rather than as part of the threshold ladder.[^fedprox]

The proximal coefficient grid is pre-registered and frozen before attack-sensitive or confirmatory test outcomes are inspected:

```text
mu in {0.001, 0.01, 0.1, 1.0}
```

`mu = 0` is FedAvg-equivalent and is not treated as a FedProx condition.

## 3.11 Ditto personalized model

Ditto maintains a global federated model and a persistent personalized model for each client, regularized toward the global model. The method was introduced as a general personalized-FL framework and evaluated in statistically heterogeneous settings.[^ditto]

For this catalogue:

- the implementation must follow genuine Ditto semantics before using the name;
- personalized client states are never aggregated as if they were one global state;
- the comparison is a stress test outside the B1–B4 causal ladder;
- the four interpretable corners are:
  - FedAvg model with B1;
  - FedAvg model with B2;
  - Ditto personalized model with B1;
  - Ditto personalized model with B2;
- the full broad personalized-FL benchmark remains out of scope.

---

# 4. Experimental regimes

## 4.1 Regime A — N-BaIoT physical-device anchor

### Scientific role

Regime A is the sole confirmatory regime and the principal mechanism-analysis substrate.

### Dataset and population

N-BaIoT contains traffic from nine commercial IoT devices exposed to Mirai and BASHLITE botnet activity in the original dataset study.[^nbaiot] The nine physical devices are the nine federated clients.

The local artifact, not secondary literature, remains authoritative for:

- exact files;
- row counts;
- feature schema;
- split manifests;
- family taxonomy;
- eligible calibration counts.

### Permitted analyses

Regime A supports:

- B0, B1, B2, B3, and B4;
- the confirmatory B1-versus-B2 experiment;
- shared-threshold construction controls;
- quantile sensitivity;
- family/cluster granularity and stability;
- cluster-fingerprint ablation;
- score-distribution mechanism analyses;
- calibration-size ablation;
- local–global shrinkage;
- B2-conf;
- `B-FedStatsBenign`;
- FedProx;
- Ditto;
- operational alert-burden translation when a real or cited traffic rate exists.

### Primary limitation

The regime contains only nine physical clients. Client-level results are therefore displayed completely; no client may be filtered because it weakens the desired pattern.

## 4.2 Regime B-a — CICIoT2023 file-defined applicability boundary

### Scientific role

Regime B-a tests whether threshold personalization remains useful when the available processed artifacts form near-homogeneous file-defined pseudo-clients rather than natural physical-device clients.

### Dataset context

The original CICIoT2023 study describes a large IoT topology with 105 devices and 33 attacks grouped into seven categories.[^ciciot2023] Those source-level properties do not automatically survive into every processed CSV distribution.

The available experiment artifact contains 63 file-defined pseudo-clients and lacks the metadata required to reconstruct physical-device clients.

### Permitted interpretation

Regime B-a may support only an applicability-boundary statement about the file-defined artifact.

It must not be used to claim:

- device-level generalization on CICIoT2023;
- physical-client equity;
- temporal behavior;
- device-aware threshold performance on the original 105-device topology.

### Permitted analyses

- B0;
- B1;
- B2;
- B4 only when the pseudo-client fingerprints are valid;
- pairwise benign-distribution Jensen–Shannon divergence;
- `CV(FPR)`, IQR, and range;
- descriptive quantile-estimation comparisons.

### Required conclusion discipline

A null B1-versus-B2 difference is expected to be scientifically useful: it indicates that personalization may be unnecessary when clients are nearly homogeneous.

## 4.3 Regime B-b — rejected CICIoT2023 physical-device repartition

The intended physical-device or MAC-based repartition is suppressed.

### Reason

The available processed artifact does not contain a trustworthy:

- MAC address;
- device identifier;
- source or destination IP suitable for client identity;
- capture-source field;
- timestamp;
- equivalent provenance field.

### Prohibited workaround

The following are not acceptable substitutes:

- assigning clients from row order;
- assigning clients from merge order;
- treating filenames as devices without evidence;
- inferring clients from class labels;
- creating random pseudo-devices;
- claiming that the original dataset paper’s 105-device topology is retained in the processed CSV.

The rejection is evidence of an artifact boundary, not a failed implementation.

## 4.4 Regime C — controlled N-BaIoT heterogeneity sweep

### Scientific role

Regime C tests whether the threshold-scope effect changes systematically with controlled non-IID severity.

### Population

Twenty synthetic clients are constructed from the N-BaIoT analysis population using the locked Dirichlet partition procedure.

### Severity grid

```text
alpha in {0.1, 0.3, 0.5, 1.0, 10.0, IID}
```

Lower `alpha` values represent stronger concentration and more severe distributional skew. Dirichlet partitioning is used only as a controlled sensitivity mechanism; it does not replace the natural physical-device evidence of Regime A.

### Policies

- B1;
- B2;
- B4.

B3 is not automatically available because the synthetic partition need not preserve the physical family taxonomy.

### Interpretation

The primary expectation is a graded relationship between heterogeneity and the B1–B2 `CV(FPR)` difference.

However:

- strict monotonicity is not required;
- overlapping low-alpha seed distributions are described as a high-heterogeneity band;
- a non-monotone result is reported;
- the sweep does not become confirmatory.

## 4.5 Regime D — Edge-IIoTset external benign-equity validation

### Scientific role

Regime D is the independent external validation of benign operating-point equity.

### Dataset context

The Edge-IIoTset paper presents a purpose-built IoT/IIoT testbed with devices, sensors, protocols, and edge/cloud configurations, designed for centralized and federated-learning security research.[^edge-iiotset]

The experiment’s actual client definition comes from the completed local full-corpus endpoint audit, not from a generic interpretation of the paper.

### Client definition

Ten benign sensor-group folders form the static external client population. The Modbus folder is valid for static benign-equity evaluation because its rows retain the declared 63-column layout; its `frame.time` values are address literals and therefore exclude it only from the temporal population.

Eligible-benign coverage is 1.0 under the locked `n_k >= 100` rule.

### Available outcomes

Regime D supports:

- per-client benign FPR;
- cross-client `CV(FPR)`;
- IQR and range of FPR;
- worst-client FPR;
- threshold dispersion;
- benign score-distribution analysis;
- B1, B2, and B4;
- `B-FedStatsBenign`;
- quantile sensitivity;
- calibration-size and shrinkage analyses where sample support permits;
- FedProx and Ditto stress tests where training is feasible.

### Unavailable outcomes

Attack traffic is confined to the attacker’s subnet in the audited artifact. Consequently, valid per-client attack assignment is unavailable.

The following per-client outcomes must be represented as unavailable, not estimated or imputed:

- TPR;
- recall;
- Macro-F1;
- P10 Macro-F1;
- balanced accuracy;
- worst-client balanced accuracy;
- per-client AUROC;
- attack-sensitive threshold trade-offs.

Regime D therefore validates external false-positive equity, not external cross-client attack-detection equity.

### B3 status

B3 is omitted because no defensible Edge-IIoTset family taxonomy has been established for the ten sensor-group clients.

## 4.6 Regime D-temporal — Edge-IIoTset one-shot recalibration boundary

### Scientific role

This regime tests threshold aging and one-shot recalibration under genuine chronology. It is a temporal boundary experiment, not a drift-detection system.

### Population

Nine verified temporal groups are used. Modbus is excluded because its timestamps are unusable under the local audit.

### Chronological split

Each client’s benign records are stably sorted by genuine capture time and partitioned as:

```text
historical training       55%
historical calibration    15%
future recalibration      10%
future evaluation         20%
```

Duplicate timestamps preserve original stable row order.

### Compared deployment states

- threshold frozen from historical calibration;
- one-shot threshold recomputed from the future recalibration window;
- matched random-fractional static reference over the same nine clients.

### Scope boundary

This experiment does not implement:

- streaming recalibration;
- periodic recalibration;
- sliding windows;
- Page–Hinkley;
- FLARE;
- FLAME;
- automatic drift detection;
- cross-dataset transfer.

Those belong to Dynamic DATP or later work.

---

# 5. Confirmatory experiment

## 5.1 Regime A shared-versus-local threshold-scope confirmation

### Scientific role

**Confirmatory.** This is the only experiment that can establish the locked main journal endpoint.

### Question

Under one fixed FedAvg autoencoder per seed, does changing the calibration scope from one shared threshold (B1) to one threshold per physical device (B2) reduce cross-client false-positive-rate dispersion on N-BaIoT?

### Why the experiment is necessary

The conference result used five seeds. The journal extension must reproduce that evidence and expand it to ten paired seeds without suppressing a less favorable estimate.

### Population and inputs

- Regime A;
- nine physical-device clients;
- ten paired training seeds;
- one locked primary checkpoint per seed;
- benign calibration scores;
- held-out benign and attack test scores;
- unchanged eligibility.

### Fixed elements

- autoencoder architecture;
- FedAvg training;
- local epochs `E = 1`;
- full participation;
- preprocessing;
- split manifests;
- checkpoint-selection rule;
- quantile `q = 0.95`;
- test records;
- metric implementation.

### Experimental factor

Threshold-calibration scope:

- B1 shared threshold;
- B2 per-client threshold.

### Procedure

1. Reproduce the locked five-seed subset using the journal implementation.
2. Verify that the reproduced five-seed result is not materially inconsistent with the conference reference.
3. Extend execution to ten paired seeds.
4. For every seed, compute per-client FPR under B1 and B2.
5. Compute `CV(FPR)` over the same eligible clients.
6. Compute the paired seed-level contrast:

\[
\Delta_s
=
CV(FPR)_{B1,s}
-
CV(FPR)_{B2,s}
\]

7. Report all ten seed-level contrasts.
8. Compute the locked 95% BCa confidence interval over the ten paired contrasts.
9. Report sign consistency.
10. Report IQR and max–min FPR alongside CV to guard against small-denominator distortion.
11. Report detection-quality controls for Regime A without treating them as the primary verdict.

### Required outcomes

- B1 and B2 per-client FPR for every seed;
- seed-level B1 and B2 `CV(FPR)`;
- ten paired deltas;
- mean or median paired delta, as defined in the evaluation protocol;
- 95% BCa interval;
- sign-consistency count;
- IQR and range;
- Macro-F1, balanced accuracy, TPR, and P10 Macro-F1 controls;
- complete nine-client result display.

### Statistical unit and analysis

The training seed is the independent unit.

The BCa interval is the confirmatory inferential result. Wilcoxon signed-rank and matched-pairs rank-biserial correlation are descriptive secondary evidence.

### Interpretation rules

**Confirmatory support**  
The 95% BCa interval excludes zero in the positive direction.

**Directional but inconclusive**  
The point estimate is positive, but the interval touches or crosses zero.

**No observed advantage**  
The estimate is approximately null and the interval includes zero.

**Opposite direction**  
B2 increases `CV(FPR)` relative to B1.

Every outcome becomes the main ten-seed result. The five-seed result is labelled preliminary when the ten-seed evidence is weaker or materially different.

### Dependencies and feasibility

Requires valid Regime A score artifacts for all ten seeds and a passed five-seed reproduction audit.

### Required artifacts

- seed-level metric records;
- per-client metric records;
- paired-delta record;
- confidence-interval record;
- eligibility manifest;
- checkpoint provenance;
- confirmatory figure;
- manuscript-ready result summary.

### Prohibited uses

- no checkpoint selection from this result;
- no replacement by B4, shrinkage, or B2-conf if the endpoint fails;
- no removal of unfavorable seeds;
- no claim that B2 improves overall detection performance.

---

# 6. Supportive robustness experiments

## 6.1 Shared-threshold construction sensitivity

### Scientific role

**Supportive.**

### Question

Is the observed B1-versus-B2 difference caused specifically by B1’s arithmetic mean of local quantiles, or does it persist across alternative shared-threshold constructions?

### Comparison set

- B1 arithmetic mean of local quantiles;
- exact pooled benign quantile;
- sample-weighted shared construction;
- B2 local quantiles.

### Procedure

Use the same Regime A model, scores, clients, and seeds as the confirmatory experiment. Recompute thresholds only.

For each shared construction:

- compute the shared threshold;
- evaluate all eligible clients;
- compute `CV(FPR)`, IQR, range, and worst-client FPR;
- calculate the paired difference relative to B2;
- report achieved pooled and per-client exceedance.

### Interpretation

**Robust construction effect**  
All reasonable shared constructions retain higher FPR dispersion than B2.

**Construction-specific effect**  
One shared construction approaches or outperforms B2. The claim is narrowed to the locked B1 construction.

**No shared-versus-local distinction**  
Shared constructions and B2 are practically similar.

This experiment cannot alter the definition of the confirmatory B1 endpoint.

## 6.2 Quantile-level sensitivity

### Scientific role

**Supportive threshold sensitivity.**

### Question

Does the B1/B2/B4 ordering depend on choosing `q = 0.95`?

### Quantile grid

```text
q in {0.90, 0.95, 0.975, 0.99}
```

### Procedure

For every Regime A seed and quantile:

- compute B1, B2, and canonical B4;
- evaluate on unchanged held-out test scores;
- report mean FPR, `CV(FPR)`, IQR, range, worst-client FPR, TPR, and P10 Macro-F1;
- report achieved benign exceedance against the target `1 - q`;
- visualize the policy-by-quantile surface.

Where Regime D supports the same calculation, repeat only the benign-FPR outcomes.

### Interpretation

An ordering inversion is reported directly. The canonical `q = 0.95` is not changed after inspection.

## 6.3 Controlled non-IID severity

### Scientific role

**Supportive heterogeneity analysis.**

### Question

Does stronger client heterogeneity increase the operating-point advantage of local threshold calibration?

### Population and factors

- Regime C;
- 20 synthetic clients;
- Dirichlet severity grid:
  - `0.1`;
  - `0.3`;
  - `0.5`;
  - `1.0`;
  - `10.0`;
  - IID;
- B1, B2, and B4;
- ten paired seeds where feasible.

### Procedure

For every seed and severity:

1. construct the partition using the locked seed and partition rule;
2. freeze the partition manifest;
3. train or reuse the correct regime-specific model without cross-severity test selection;
4. compute B1, B2, and B4;
5. report heterogeneity diagnostics;
6. compute the B1–B2 `CV(FPR)` difference;
7. report uncertainty per alpha;
8. display seed distributions rather than only point estimates.

### Required heterogeneity diagnostics

At minimum:

- client sample-count distribution;
- client benign-distribution divergence;
- class or attack composition when valid;
- eligible-client coverage;
- pairwise or aggregate Jensen–Shannon divergence.

### Interpretation

A smooth monotone curve is not required. Low-alpha conditions may form one broad high-heterogeneity band. The result is associative and does not establish that the selected heterogeneity statistic causally determines DATP benefit.

---

# 7. Cluster and family mechanism programme

## 7.1 Threshold-sharing granularity and cluster stability

### Scientific role

**Mechanism analysis.**

### Questions

- Does family or cluster threshold sharing recover part of B2’s FPR-equity benefit?
- How much calibration granularity is required?
- Are B4 client assignments stable across seeds and calibration samples?
- Does cluster sharing provide a defensible middle ground between one global threshold and one threshold per client?

### Population

- Regime A is mandatory;
- Regime D may include B4 where its ten sensor-group fingerprints are valid;
- B3 remains Regime A only.

### Comparison set

- B1 shared;
- B3 family;
- B4 canonical `K = 3`;
- B2 local;
- exploratory B4 cluster counts where mathematically feasible.

### Procedure

1. Build each client fingerprint from benign calibration errors only.
2. Standardize fingerprint dimensions using the locked rule.
3. Fit canonical k-means with locked initialization and seed handling.
4. Assign the cluster-level threshold.
5. Evaluate FPR equity and detection controls.
6. Repeat clustering across seeds and declared resamples.
7. compare assignments using adjusted Rand index.
8. compute within-cluster and across-cluster threshold and FPR dispersion.
9. display the client-to-cluster membership for every seed.
10. compare B4 groupings against the device-family taxonomy descriptively without treating taxonomy agreement as the optimization target.

Adjusted Rand index is appropriate as a chance-adjusted comparison of two partitions, but the very small Regime A client count requires displaying the underlying assignments and contingency tables rather than relying on ARI alone.[^ari]

### Required outcomes

- B1/B3/B4/B2 `CV(FPR)`;
- worst-client FPR;
- IQR and range;
- B4 recovery fraction relative to the B1–B2 gap;
- within-cluster and across-cluster dispersion;
- ARI across seed pairs or declared resamples;
- complete membership assignments;
- cluster sizes;
- empty or singleton cluster diagnostics;
- detection-quality controls for Regime A.

### Interpretation

**Useful middle ground**  
B4 or B3 recovers a meaningful portion of B2’s equity improvement with stable groupings.

**Performance without stability**  
B4 reduces dispersion, but assignments are unstable. The result is reported as fragile.

**Stable but unhelpful**  
Clusters repeat, but do not improve the operating point.

**No cluster mechanism**  
B4 is unstable and provides little recovery. B4 remains an explored negative mechanism result.

## 7.2 B4 fingerprint ablation

### Scientific role

**Mechanism and exploratory ablation.**

### Question

Which components of the four-scalar fingerprint contribute to B4 behavior?

### Ablation design

Evaluate:

- each single feature;
- declared feature pairs or leave-one-feature-out subsets;
- the complete four-feature fingerprint.

The exact subset family must be fixed before results are examined and kept small enough to avoid an unprincipled combinatorial search.

### Required outcomes

- cluster assignments per subset and seed;
- `CV(FPR)` and worst-client FPR;
- ARI relative to the full fingerprint;
- cluster-size distribution;
- device-to-cluster contingency;
- threshold recovery fraction.

### Interpretation

The ablation identifies sensitivity, not causal importance. A feature subset cannot replace the canonical fingerprint after seeing favorable test outcomes.

## 7.3 Per-client score-distribution explanation

### Scientific role

**Mechanism analysis.**

### Question

Why does B2 reduce FPR dispersion yet sometimes lower P10 Macro-F1?

### Procedure

For all nine Regime A clients:

- plot held-out benign reconstruction-error CDFs;
- plot held-out attack reconstruction-error CDFs;
- overlay B1, B2, and B4 thresholds;
- show each threshold’s benign exceedance and attack acceptance region;
- identify clients with weak score separation;
- include the pre-specified Ennio Doorbell deep dive;
- retain all clients in supplementary panels.

### Required outcomes

- one complete multi-client CDF figure;
- one detailed Ennio Doorbell panel;
- per-client threshold positions;
- per-client FPR, TPR, balanced accuracy, and Macro-F1;
- explanation of threshold movement without claiming causality beyond the plotted score geometry.

## 7.4 Heterogeneity–benefit association

### Scientific role

**Mechanism association.**

### Question

Does benign score-distribution heterogeneity predict the magnitude of the local-threshold benefit?

### Procedure

For each valid regime/seed unit:

- calculate the locked Jensen–Shannon heterogeneity summary from benign score distributions;
- calculate the B1–B2 FPR-equity gain;
- plot both;
- report Spearman correlation;
- fit the pre-specified descriptive regression;
- report `R²`, uncertainty, leverage, and sensitivity to individual clients or regimes.

### Interpretation

A strong relationship supports a heterogeneity-conditioned interpretation. A weak relationship is a real result and prevents using JS divergence as a sufficient predictor.

The analysis is associative, not causal.

## 7.5 Threshold movement versus operating-point harm

### Scientific role

**Mechanism analysis.**

### Question

How does the client-specific threshold shift from B1 to B2 relate to changes in false positives and attack detection?

### Procedure

For every Regime A device and seed, compute:

\[
\Delta \tau_k = \tau_{B2,k} - \tau_{B1}
\]

\[
\Delta FPR_k = FPR_{B2,k} - FPR_{B1,k}
\]

\[
\Delta TPR_k = TPR_{B2,k} - TPR_{B1,k}
\]

Display:

- threshold shift versus FPR change;
- threshold shift versus TPR change;
- device labels;
- seed uncertainty;
- all nine clients without filtering.

### Interpretation

This experiment quantifies the equity–sensitivity trade-off surface. It does not claim that threshold movement alone explains every detection change.

---

# 8. Calibration robustness programme

## 8.1 Calibration-size ablation

### Scientific role

**Boundary condition and threshold-variant support.**

### Question

How much benign calibration data is required before local thresholds become stable?

### Calibration-size grid

```text
n_k in {50, 100, 250, 500, 1000, 5000}
```

A size is evaluated only when the client has sufficient source calibration records.

### Repetition

Each subsample size must use multiple deterministic subsampling replicates nested within each training seed. Subsampling replicates quantify calibration sampling variability; they are not counted as independent training seeds.

### Comparison set

- B1;
- B2;
- B4;
- shrinkage overlay where defined;
- B2-conf where its finite-sample rule is valid.

### Procedure

For every seed, client, size, and subsample replicate:

1. draw benign calibration records without replacement;
2. compute the declared thresholds;
3. evaluate on the unchanged held-out test set;
4. record threshold variance across subsamples;
5. record FPR target error;
6. record `CV(FPR)`, worst-client FPR, IQR, range, P10 Macro-F1, and balanced accuracy;
7. report clients unavailable at each size.

### Interpretation

**Graceful degradation**  
B2 remains stable as calibration shrinks.

**Shrinkage benefit**  
Naive B2 destabilizes while shrinkage reduces variance without erasing most personalization.

**Sample-starved boundary**  
Local thresholds become unreliable below a clear range.

**No sample-size effect**  
Threshold stability changes little over the tested grid.

The result cannot be summarized using only the best-performing calibration size.

## 8.2 Fixed local–global shrinkage

### Scientific role

**Supportive threshold variant.**

### Question

Can partial pooling retain FPR equity while reducing local-threshold variance or detection loss?

### Factor

```text
lambda in {0.00, 0.25, 0.50, 0.75, 1.00}
```

### Procedure

Using the same Regime A scores:

- compute the shrinkage threshold for every eligible client;
- evaluate the full lambda curve;
- report `CV(FPR)`, worst-client FPR, IQR, range, TPR, P10 Macro-F1, and threshold variance;
- repeat within the calibration-size grid where planned;
- do not choose one lambda from the test set and present it as the method.

### Interpretation

The full curve is the result.

A non-monotone response is reported. An intermediate lambda may be described as a useful empirical compromise only if its selection rule is explicitly exploratory or determined without test leakage.

## 8.3 Calibration-size-aware shrinkage

### Scientific role

**Supportive extension of shrinkage.**

### Question

Can personalization weight depend on available benign calibration size without using test outcomes?

### Requirements

The function `lambda(n_k)` must be:

- specified before evaluation;
- monotone unless a scientific reason justifies otherwise;
- bounded in `[0, 1]`;
- identical across clients apart from `n_k`;
- compared with fixed-lambda curves;
- evaluated over the same calibration-size subsamples.

### Interpretation

This is an engineering threshold variant, not a new statistical estimator claim.

## 8.4 Split-conformal B2-conf diagnostic

### Scientific role

**Supportive response to the “equalized by construction” critique.**

### Question

Does a finite-sample-adjusted local conformal quantile achieve the intended benign coverage on held-out data, and does cross-client FPR dispersion remain lower than under a shared threshold?

### Procedure

For every eligible Regime A client and seed:

1. use only the declared benign calibration scores;
2. compute the finite-sample conformal quantile at `alpha = 0.05`;
3. evaluate benign coverage on held-out benign scores;
4. report coverage error per client and seed;
5. evaluate attack-sensitive metrics only on held-out attack scores;
6. compare B2-conf with B2 and B1;
7. report results at small calibration sizes where rank granularity is material.

### Required outcomes

- target coverage;
- achieved marginal benign coverage;
- coverage error;
- per-client coverage distribution;
- `CV(FPR)`;
- threshold difference from B2;
- detection-quality controls;
- finite-sample discreteness diagnostics.

### Interpretation

B2-conf can show that the threshold rule is evaluated through held-out coverage rather than assumed to equalize test FPR by construction.

It does not prove client-conditional validity under arbitrary non-IID shift. Exchangeability limitations must remain explicit.[^split-conformal][^fed-conformal-heterogeneity]

---

# 9. Federated threshold-estimation programme

## 9.1 Benign summary-statistics comparator

### Scientific role

**Mandatory comparator stress test.**

### Question

Does a matched benign-only federated summary-statistics threshold dominate, match, or underperform DATP’s shared and local threshold scopes?

### Population

- Regime A is mandatory;
- Regime D is mandatory for benign-FPR outcomes when artifacts are available.

### Comparison set

- B1;
- exact pooled benign quantile;
- sample-weighted shared construction;
- B2;
- `B-FedStatsBenign`.

### Matching rule

The comparator’s target exceedance must be matched to:

```text
1 - q
```

It may not be tuned on attack labels or F1.

### Procedure

1. compute the exact centralized benign reference;
2. compute every distributed construction from the same calibration records;
3. evaluate threshold-estimation error against the centralized reference;
4. evaluate achieved benign exceedance;
5. evaluate cross-client FPR dispersion;
6. report communication payload estimates separately from measured network cost;
7. calculate the locked between-ratio diagnostic where defined;
8. describe precisely which statistics leave each client.

### Required outcomes

- threshold value;
- absolute and relative threshold error;
- target-attainment error;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- communication fields and estimated bytes;
- client coverage;
- comparison with B1 and B2.

### Interpretation

`B-FedStatsBenign` may:

- improve over B1 but remain weaker than B2;
- match B2;
- dominate B2;
- fail to improve over B1.

Every outcome is reported. The result does not support a faithful Laridi claim because anomalous validation summaries are excluded.[^laridi]

## 9.2 Federated quantile-estimation backbone

### Scientific role

**Optional high-value methods backbone.**

### Purpose

Reframe threshold policies as estimators of a target quantile and make their approximation error auditable.

### Required constructions

- exact pooled quantile;
- local quantiles;
- arithmetic mean of local quantiles;
- sample-weighted construction;
- quantile-of-quantiles where pre-specified;
- `B-FedStatsBenign`.

### Outcomes

- quantile-estimation error;
- achieved benign exceedance;
- threshold variance;
- calibration sample efficiency;
- estimated communication;
- relation between estimation error and FPR equity.

No novel federated quantile estimator is claimed unless a genuinely new estimator and proof are developed outside the current roadmap.

## 9.3 Fixed-coefficient Laridi sensitivity

### Scientific role

**Optional supplementary sensitivity only.**

Fixed coefficient values may be evaluated under the benign-only adaptation:

```text
k in {2.0, 2.5, 3.0}
```

This remains a sensitivity of `B-FedStatsBenign`; it must not be labelled `B-LaridiFaithful`.

---

# 10. External validation and applicability boundaries

## 10.1 Edge-IIoTset external benign-equity validation

### Scientific role

**External validation.**

### Question

Does the shared-versus-local threshold-scope effect appear on an independent sensor-group-partitioned IoT/IIoT dataset?

### Population

- Regime D;
- ten benign sensor-group clients;
- eligible-benign coverage 1.0;
- ten paired seeds where training is feasible.

### Comparison set

- B1;
- B2;
- B4 canonical;
- `B-FedStatsBenign`;
- quantile sensitivity;
- calibration-size and shrinkage analyses where supported.

B3 is omitted.

### Procedure

1. execute the locked Edge-IIoTset preprocessing and endpoint assignment;
2. verify the expected ten-client manifest;
3. fit preprocessing on benign training data only;
4. train the FedAvg autoencoder per seed;
5. freeze checkpoints and scores;
6. construct the allowed thresholds;
7. evaluate per-client benign FPR;
8. compute cross-client equity metrics;
9. represent attack-sensitive per-client metrics as unavailable;
10. compare the direction and magnitude of B1–B2 with Regime A without treating the datasets as exchangeable replications.

### Required outcomes

- client manifest;
- eligible-benign coverage;
- per-client benign sample counts;
- B1/B2/B4/`B-FedStatsBenign` thresholds;
- per-client FPR;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- seed-level B1–B2 differences;
- BCa interval as external evidence;
- typed unavailability for attack-sensitive metrics;
- dataset-specific limitations.

### Interpretation

**Consistent direction**  
Supports external benign-equity validation.

**Weaker or null effect**  
Defines a cross-dataset boundary.

**Opposite effect**  
Narrows the generalization claim.

**Client assignment or eligibility failure**  
Produces an infeasibility result; it cannot be repaired by inventing another partition after inspection.

## 10.2 CICIoT2023 file-level boundary

### Scientific role

**Applicability boundary.**

### Question

When the processed client partitions are near-homogeneous and file-defined, is threshold personalization unnecessary or unidentifiable?

### Procedure

- verify the 63 file-defined pseudo-client artifacts;
- quantify pairwise benign-distribution divergence;
- run B1 and B2 on the same scores;
- include B4 only if the fingerprints and cluster sizes are meaningful;
- report `CV(FPR)`, IQR, range, and worst pseudo-client FPR;
- keep all wording artifact-specific.

### Interpretation

A null result is not evidence that DATP fails on CICIoT2023’s original physical devices. It is evidence that the available file-defined artifact does not expose a strong threshold-scope need.

---

# 11. Training-side stress tests

## 11.1 FedProx aggregation stress test

### Scientific role

**External aggregation-side stress test.**

### Question

Does heterogeneity-aware training absorb the B1–B2 threshold-scope effect?

### Literature rationale

FedProx was designed to address systems and statistical heterogeneity by adding a proximal term to local optimization and generalizing FedAvg.[^fedprox] Its inclusion tests whether better training alignment removes the need for post-training threshold personalization.

### Population

- Regime A is mandatory;
- Regime D benign-equity outcomes are included after Regime D readiness.

### Factors

- FedAvg reference;
- FedProx with frozen `mu` grid:
  - `0.001`;
  - `0.01`;
  - `0.1`;
  - `1.0`;
- B1, B2, B3 where valid, and B4.

### Coefficient-selection rule

The primary FedProx coefficient must be selected using the pre-registered, non-test rule on Regime A. The test set, attack labels, `CV(FPR)` advantage, and Regime D outcomes cannot choose `mu`.

The complete grid remains reportable.

### Procedure

1. train FedProx models independently from FedAvg;
2. apply the same checkpoint protocol;
3. generate separate score artifacts;
4. evaluate the complete threshold ladder on each trained model;
5. calculate the B1–B2 threshold-scope difference under FedAvg and FedProx;
6. compare convergence and model-quality controls;
7. report training failure or instability without changing the grid retroactively.

### Interpretation

- retained threshold-scope effect;
- partial absorption;
- full absorption;
- opposite effect;
- FedProx non-convergence or instability.

FedProx results do not enter the core causal ladder.

## 11.2 Ditto model-personalization stress test

### Scientific role

**External model-side personalization stress test.**

### Question

Does maintaining a personalized model for each client make threshold personalization redundant?

### Literature rationale

Ditto jointly maintains global and personalized models and was proposed as a general personalized federated-learning framework for statistically heterogeneous clients.[^ditto] It is used here because it can be applied without requiring a hand-defined shared representation/local head split.

### Population

- Regime A is mandatory;
- Regime D is included for benign-equity outcomes after readiness.

### Primary comparison

The interpretable 2-by-2 core is:

- FedAvg model with B1;
- FedAvg model with B2;
- Ditto personalized model with B1;
- Ditto personalized model with B2.

B3 and B4 may be applied as supplementary threshold scopes to the personalized score artifacts.

### Procedure

1. train genuine Ditto global and personalized states;
2. keep personalized states separate by client;
3. select personalization hyperparameters without attack-test or confirmatory leakage;
4. generate scores separately from the FedAvg artifacts;
5. compute B1 and B2 on the Ditto score distributions;
6. calculate the threshold-scope gain under FedAvg and under Ditto;
7. report model-quality, FPR-equity, compute, storage, and communication differences;
8. preserve all four core corners.

### Absorption measure

\[
\Delta_{\mathrm{FedAvg}}
=
CV(FPR)_{\mathrm{FedAvg+B1}}
-
CV(FPR)_{\mathrm{FedAvg+B2}}
\]

\[
\Delta_{\mathrm{Ditto}}
=
CV(FPR)_{\mathrm{Ditto+B1}}
-
CV(FPR)_{\mathrm{Ditto+B2}}
\]

Interpretation bands:

- `Delta_Ditto >= 0.75 * Delta_FedAvg`: threshold personalization remains strongly useful;
- `0.25 * Delta_FedAvg <= Delta_Ditto < 0.75 * Delta_FedAvg`: partial absorption;
- `Delta_Ditto < 0.25 * Delta_FedAvg`: largely absorbed;
- if `CV(FPR)[Ditto+B1]` is within `0.05` of `CV(FPR)[FedAvg+B2]`, model personalization is reported as an alternative route to operating-point equity.

### Scope boundary

This is one stress test, not an exhaustive personalized-FL benchmark. APFL, Per-FedAvg, pFedMe, FedRep, FedPer, and broad architecture comparisons are not added to this paper.

---

# 12. Temporal recalibration experiment

## 12.1 One-shot recalibration under genuine chronology

### Scientific role

**Temporal boundary condition.**

### Question

When thresholds are calibrated on historical benign behavior, does future benign behavior increase cross-client FPR dispersion, and can one future benign recalibration window recover it?

### Population

- Regime D-temporal;
- nine verified temporal groups;
- Modbus excluded;
- ten paired seeds where feasible.

### Compared states

**Static reference**  
Random-fractional split over the same nine groups, used to estimate ordinary sampling variation without chronology.

**Frozen future**  
Thresholds fitted from historical calibration and applied unchanged to future evaluation.

**One-shot recalibrated future**  
Thresholds recomputed once from the future recalibration window and applied to future evaluation.

### Policies

- B1;
- B2;
- B4;
- shrinkage where pre-specified.

### Procedure

1. verify timestamps for every included client;
2. apply stable chronological ordering;
3. construct the 55/15/10/20 split;
4. fit preprocessing and the autoencoder without future leakage;
5. construct historical thresholds;
6. evaluate frozen thresholds on future evaluation;
7. recompute thresholds from future recalibration only;
8. evaluate recalibrated thresholds on the same future evaluation;
9. construct the matched static reference;
10. calculate:

\[
drift\_excess
=
CV_{\mathrm{frozen\ future}}
-
CV_{\mathrm{static\ reference}}
\]

\[
recovered\_amount
=
CV_{\mathrm{frozen\ future}}
-
CV_{\mathrm{recalibrated\ future}}
\]

\[
recovery\_ratio
=
\frac{recovered\_amount}{drift\_excess}
\]

`recovery_ratio` is undefined when `drift_excess` is not meaningfully positive.

### Required outcomes

- chronology-validation record;
- included and excluded clients;
- static-reference CV;
- frozen-future CV;
- recalibrated-future CV;
- drift excess;
- recovered amount;
- recovery ratio when defined;
- per-client FPR trajectories;
- threshold movements;
- paired seed uncertainty.

### Pre-specified interpretations

**Temporal degradation with recovery**  
Frozen future dispersion exceeds the static reference and one-shot recalibration recovers a meaningful portion.

**Temporal degradation without recovery**  
Drift excess is positive, but one-shot recalibration provides little or negative recovery.

**No detectable temporal degradation**  
Frozen future dispersion does not meaningfully exceed the static reference; recovery ratio remains undefined.

No outcome justifies claiming a complete concept-drift solution.

---

# 13. Operational translation

## 13.1 Alert-burden experiment

### Scientific role

**Supportive operational interpretation.**

### Question

What does a difference in FPR mean in approximate alerts per device per day?

### Required external input

A real measured or appropriately cited benign traffic rate:

```text
benign decisions or flows per device per unit time
```

### Calculation

For client \(k\):

\[
alerts_{k,\mathrm{day}}
=
FPR_k
\times
benign\_traffic\_rate_{k,\mathrm{day}}
\]

### Requirements

- report the rate source;
- report whether the rate is measured, dataset-derived, or externally cited;
- propagate rate assumptions separately from model uncertainty;
- show per-device burden, not only a pooled total;
- use B1 and B2 at minimum;
- label estimates as estimated when no deployment measurement exists.

### Suppression rule

When no real or cited rate is available, omit the metric. Do not invent a nominal rate merely to populate a table or figure.

---

# 14. Optional high-value analyses

These analyses are useful but cannot delay the mandatory programme unless a reviewer-critical gap remains.

## 14.1 Robust cluster-median threshold

Replace the mean of cluster-member local thresholds with a median and compare outlier sensitivity.

Report:

- cluster assignments unchanged;
- cluster threshold difference;
- `CV(FPR)`;
- worst-client FPR;
- outlier-client influence.

This remains supplementary.

## 14.2 Additional equity indices

Report, alongside rather than instead of `CV(FPR)`:

- Jain index;
- Gini coefficient;
- IQR;
- max–min range;
- within-cluster dispersion;
- across-cluster dispersion.

The primary endpoint remains unchanged.

## 14.3 Extended secondary uncertainty

Provide:

- bootstrap intervals for secondary paired metrics;
- Wilcoxon signed-rank;
- matched-pairs rank-biserial correlation;
- exact sign summaries where useful.

Multiplicity treatment must follow [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md).

## 14.4 Communication and storage estimates

Estimate bytes required for:

- B1 threshold exchange;
- B2 per-client thresholds;
- B4 fingerprints, cluster assignments, and thresholds;
- `B-FedStatsBenign` summary fields;
- FedAvg, FedProx, and Ditto model exchange where comparable.

Clearly separate:

- analytically estimated payload;
- serialized payload measured in the implementation;
- actual network traffic, which is not measured unless a network experiment exists.

---

# 15. Suppressed and rejected experiments

## 15.1 CICIoT2023 device or MAC repartition

**Status:** suppressed.

**Reason:** required client-identifying metadata is absent from the available processed artifact.

**Reactivation condition:** a verified artifact with genuine physical-device or capture-source identity becomes available and is audited before analysis.

## 15.2 CICIoT2023 temporal analysis

**Status:** suppressed.

**Reason:** no valid timestamps in the available artifact.

**Forbidden substitutes:** file order, row order, merge order, folder order, generated timestamps, or class progression.

## 15.3 FedBN

**Status:** rejected.

**Reason:** the locked autoencoder has no BatchNorm. Adding BatchNorm would change the model architecture and violate the fixed-detector identity.

## 15.4 Anomaly-labelled Laridi-faithful threshold

**Status:** out of scope.

**Reason:** it uses anomalous validation information and violates benign-only calibration.

The paper is discussed as the closest thresholding overlap and motivates a matched benign-only comparator, but its method is not relabelled as DATP-compatible.[^laridi]

## 15.5 Empirical membership-inference probe on threshold summaries

**Status:** rejected from this journal programme.

**Reason:** the roadmap provides only a bounded qualitative disclosure analysis and does not claim formal privacy. A standalone privacy study requires its own threat model.

## 15.6 Streaming drift detectors and continuous adaptation

**Status:** rejected from DATP Core.

Includes:

- Page–Hinkley;
- FLARE;
- FLAME;
- rolling recalibration;
- event-triggered recalibration;
- continuous threshold updates.

These belong to Dynamic DATP.

## 15.7 Byzantine-robust federated conformal prediction

**Status:** rejected from this paper.

It crosses into poisoning and defense research and belongs to DATP-CP or a future conformal-security study.

## 15.8 Broad personalized-FL benchmark

**Status:** rejected.

This paper allows one model-personalization stress test. It does not benchmark APFL, Per-FedAvg, pFedMe, FedRep, FedPer, Ditto, and other personalized methods together.

---

# 16. Named future work

The following are named but not executed:

- Dynamic DATP with drift-triggered or periodic recalibration;
- Conformal DATP beyond the bounded B2-conf diagnostic;
- formal differential privacy;
- secure aggregation;
- fleet-scale validation above 100 clients;
- standalone model-versus-threshold personalization with full cost accounting;
- exhaustive aggregation sensitivity;
- hardware and edge-device profiling;
- poisoning, backdoor, Byzantine, and evasion studies;
- full attack-sensitive external validation when a defensible per-client attack mapping becomes available.

No future item may appear in a result table or be described as completed.

---

# 17. Execution order and blocking gates

## 17.1 Stage 1 — Anchor reproduction and confirmatory extension

Execute first:

1. validate Regime A manifests and score provenance;
2. reproduce the locked five-seed anchor;
3. resolve any material reproduction discrepancy;
4. execute the ten-seed confirmatory comparison;
5. freeze the ten-seed result as the journal anchor.

**Blocking gate:** no expansion claim proceeds when the five-seed reproduction materially disagrees with the locked reference and the discrepancy remains unresolved.

## 17.2 Stage 2 — Stored-score threshold analyses

After valid Regime A scores exist, execute without retraining:

- shared-threshold construction sensitivity;
- quantile sensitivity;
- family/cluster threshold analysis;
- cluster stability;
- fingerprint ablation;
- CDF mechanism figures;
- JS–gain association;
- threshold-shift trade-off;
- calibration-size ablation;
- fixed shrinkage;
- size-aware shrinkage;
- B2-conf;
- `B-FedStatsBenign`;
- alert burden when a rate exists;
- optional equity and communication analyses.

These analyses must reuse frozen score artifacts.

## 17.3 Stage 3 — Controlled heterogeneity

Execute the complete Regime C severity grid after the partition and training protocol passes leakage and reproducibility checks.

**Blocking gate:** every alpha cell must have a valid manifest and comparable eligible-client reporting.

## 17.4 Stage 4 — External dataset validation

Execute Regime D after:

- source artifact integrity passes;
- the ten-client benign sensor-group assignment is reproduced;
- eligibility coverage is verified;
- attack-sensitive metric unavailability is enforced;
- preprocessing and score generation pass.

## 17.5 Stage 5 — Training-side stress tests

Execute:

1. FedProx;
2. Ditto.

Both require new training and separate score artifacts. They must not overwrite or replace FedAvg anchor artifacts.

## 17.6 Stage 6 — Temporal boundary

Execute Regime D-temporal only after:

- timestamp validity passes;
- the nine-group population is reproduced;
- Modbus exclusion is documented;
- no future leakage is confirmed;
- the matched static reference is available.

## 17.7 Stage 7 — Optional supplement

Only after all mandatory evidence is complete:

- cluster median;
- expanded equity suite;
- secondary intervals;
- fixed-coefficient benign summary-statistics sensitivity;
- extended communication/storage estimates.

---

# 18. Required experiment outputs

Every mandatory experiment must produce enough information to reconstruct its result.

## 18.1 Identity and provenance

- experiment descriptive name;
- evidentiary role;
- dataset and regime;
- client-definition version;
- seed;
- checkpoint identity;
- score-artifact identity;
- policy or comparator;
- resolved parameter values;
- eligibility manifest;
- source configuration fingerprint;
- software revision.

## 18.2 Metric records

- per-client metrics;
- seed-level aggregate metrics;
- paired contrasts where applicable;
- undefined and unavailable outcomes represented explicitly;
- denominator and eligible-client counts;
- uncertainty records;
- effect-size records where planned.

## 18.3 Threshold records

- threshold value per applicable client or group;
- quantile target;
- calibration count;
- construction method;
- group membership;
- threshold variance for subsampling analyses;
- target-attainment error.

## 18.4 Visual outputs

At minimum, the programme must support:

- confirmatory paired-seed plot;
- per-client FPR comparison;
- quantile-sensitivity surface;
- heterogeneity-severity curve;
- cluster membership and stability display;
- cluster-feature ablation;
- benign and attack CDF overlays;
- JS–gain scatter;
- threshold-shift trade-off scatter;
- calibration-size curves;
- shrinkage curve;
- conformal coverage plot;
- external-validation client plot;
- FedProx comparison;
- Ditto 2-by-2 comparison;
- temporal frozen-versus-recalibrated plot.

## 18.5 Failure and infeasibility records

Expected scientific failures are data, not exceptions to be hidden.

Record explicitly:

- insufficient eligible clients;
- missing attack assignment;
- unusable timestamp;
- empty cluster;
- singleton cluster;
- undefined CV due to zero or near-zero mean;
- undefined recovery ratio;
- conformal coverage miss;
- checkpoint-selection failure;
- training non-convergence;
- missing traffic-rate source;
- suppressed experiment reason.

---

# 19. Catalogue-level completion audit

The experiment catalogue is complete only when all checks below pass.

## 19.1 Coverage

- every mandatory roadmap experiment has a descriptive section;
- every optional experiment is explicitly labelled optional;
- every rejected experiment has a reason;
- every future item is separated from executable work;
- no previous opaque experiment code is required to understand the programme.

## 19.2 Causal discipline

- B1–B4 use the same fixed detector within a seed;
- stress tests are outside the causal ladder;
- B0 is not produced from FedAvg scores;
- benign-only calibration is preserved;
- test data never select thresholds or training hyperparameters.

## 19.3 Regime consistency

- Regime A uses nine physical devices;
- Regime B-a remains file-defined and artifact-specific;
- Regime B-b remains suppressed;
- Regime C uses the locked Dirichlet grid and 20 clients;
- Regime D uses ten benign sensor groups and omits B3;
- Regime D attack-sensitive client metrics remain unavailable;
- Regime D-temporal uses nine groups and the 55/15/10/20 split.

## 19.4 Statistical discipline

- ten paired seeds are used for the confirmatory endpoint;
- the BCa interval is the confirmatory interval;
- matched-pairs rank-biserial correlation is used for paired effect size;
- nested subsampling replicates are not counted as seeds;
- clients and windows are not treated as independent replications;
- absolute dispersion accompanies CV when denominators are small.

## 19.5 Reporting discipline

- all clients are shown where feasible;
- unfavorable seeds are retained;
- ordering inversions are reported;
- null mechanism results remain visible;
- external validation is not promoted to confirmatory evidence;
- operational estimates are not presented as deployment measurements;
- source-paper dataset properties are not substituted for local artifact verification.

---

# 20. Research foundations

The experiment programme is governed by the locked DATP roadmap. The papers below support specific design choices and literature positioning; they do not override local artifact audits or alter the locked causal claim.

[^nbaiot]: Y. Meidan et al., “N-BaIoT—Network-Based Detection of IoT Botnet Attacks Using Deep Autoencoders,” *IEEE Pervasive Computing*, 2018. DOI: [10.1109/MPRV.2018.03367731](https://doi.org/10.1109/MPRV.2018.03367731). Supports the use of nine physical N-BaIoT devices and the autoencoder anomaly-detection context.

[^edge-iiotset]: M. A. Ferrag et al., “Edge-IIoTset: A New Comprehensive Realistic Cyber Security Dataset of IoT and IIoT Applications for Centralized and Federated Learning,” *IEEE Access*, 2022. DOI: [10.1109/ACCESS.2022.3165809](https://doi.org/10.1109/ACCESS.2022.3165809). Supports Edge-IIoTset as an independent IoT/IIoT external dataset; the actual DATP client mapping remains artifact-audited.

[^ciciot2023]: E. C. P. Neto et al., “CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment,” *Sensors*, 2023. DOI: [10.3390/s23135941](https://doi.org/10.3390/s23135941). Supports the original dataset context of 105 devices and 33 attacks; the available processed DATP artifact does not retain a verified physical-device mapping.

[^fedprox]: T. Li et al., “Federated Optimization in Heterogeneous Networks,” *Proceedings of MLSys*, 2020. [Primary paper](https://arxiv.org/abs/1812.06127). Supports FedProx as a heterogeneity-oriented training stress test and not as a threshold policy.

[^ditto]: T. Li, S. Hu, A. Beirami, and V. Smith, “Ditto: Fair and Robust Federated Learning Through Personalization,” *Proceedings of ICML*, PMLR 139, 2021. [Primary paper](https://proceedings.mlr.press/v139/li21h.html). Supports the model-personalization stress-test design.

[^laridi]: S. Laridi, G. Palmer, and K.-M. M. Tam, “Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding,” *Scientific Reports*, 2024. DOI: [10.1038/s41598-024-76961-2](https://doi.org/10.1038/s41598-024-76961-2). The method aggregates summary statistics from normal and anomalous validation data; this motivates but is not equivalent to the benign-only `B-FedStatsBenign` comparator.

[^split-conformal]: J. Lei, M. G’Sell, A. Rinaldo, R. J. Tibshirani, and L. Wasserman, “Distribution-Free Predictive Inference for Regression,” *Journal of the American Statistical Association*, 2018. DOI: [10.1080/01621459.2017.1307116](https://doi.org/10.1080/01621459.2017.1307116). Supports finite-sample split-conformal rank correction under exchangeability.

[^fed-conformal-label-shift]: V. Plassier et al., “Conformal Prediction for Federated Uncertainty Quantification Under Label Shift,” *Proceedings of ICML*, PMLR 202, 2023. [Primary paper](https://proceedings.mlr.press/v202/plassier23a.html). Supports caution that federated distribution shift requires explicit treatment for conformal validity.

[^fed-conformal-heterogeneity]: V. Plassier et al., “Efficient Conformal Prediction under Data Heterogeneity,” *Proceedings of AISTATS*, PMLR 238, 2024. [Primary paper](https://proceedings.mlr.press/v238/plassier24a.html). Supports treating agent heterogeneity and non-exchangeability as substantive conformal-prediction issues.

[^ari]: L. Hubert and P. Arabie, “Comparing Partitions,” *Journal of Classification*, 1985. DOI: [10.1007/BF01908075](https://doi.org/10.1007/BF01908075). Supports adjusted Rand index for chance-adjusted comparison of cluster assignments.
