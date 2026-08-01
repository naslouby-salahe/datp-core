# DATP Journal Extension — Master Roadmap

**Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*

## Purpose and structure

This roadmap defines the DATP-Core scientific programme: its causal question, threshold policies, datasets, experiments, metrics, statistical analysis, and interpretation boundaries. It is a single research document rather than an implementation specification or project-administration record.

The study asks whether the scope of benign threshold calibration changes the distribution of false-positive burden across heterogeneous federated IoT clients while the detector is held fixed. The confirmatory comparison is shared versus per-client threshold calibration on the natural-device regime; all other studies supply supporting, mechanism, stress-test, external, or boundary evidence.

## Scientific identity, scope, and claims

### 1. Programme identity

**1.1 Working title**

*Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.*

**1.2 DATP-Core in one paragraph**

DATP-Core is a controlled study of **threshold-calibration scope** in federated IoT anomaly detection.

For each seed and dataset regime, a federated autoencoder is trained and selected under one locked training protocol. The selected detector is then frozen. The same per-client calibration and test scores are reused across the core threshold ladder. The ladder changes only the scope at which a benign anomaly threshold is estimated: one shared threshold, one threshold per physical-device family, one threshold per data-driven client cluster, or one threshold per client.

The scientific question is therefore not:

> Which model or federated-learning algorithm is best?

It is:

> When heterogeneous IoT clients share one frozen federated anomaly detector, how does the scope of benign threshold calibration affect the distribution of false-alarm burden across clients?

The primary object of interest is cross-client false-positive-rate dispersion. Model discrimination, including AUROC, remains a control rather than the thresholding verdict.

---

### 2. Core causal contract

**2.1 Unit of causal comparison**

The controlled comparison is performed within a seed, regime, and frozen detector.

The core threshold policies must receive:

- the same selected autoencoder state;
- the same preprocessing state;
- the same client identities;
- the same predefined data partitions;
- the same benign calibration records;
- the same held-out test scores;
- the same held-out test labels;
- the same eligibility rule;
- the same quantile target unless a declared quantile-sensitivity experiment changes it;
- the same metric implementation.

Only threshold-calibration scope may differ.

**2.2 Fixed elements**

Within a core dataset ladder, the following remain fixed:

- model family;
- autoencoder architecture, apart from the input dimension required by the dataset feature schema;
- FedAvg as the training algorithm;
- one local epoch per round;
- full client participation;
- optimizer and training hyperparameters;
- preprocessing and normalization semantics;
- split semantics;
- round budget and checkpoint candidates;
- checkpoint-selection rule;
- seed cohort;
- scoring procedure;
- client eligibility;
- test population;
- metric definitions.

The fixed-detector rule applies **within each regime and training baseline**. It does not mean that the same numerical model parameters are reused across different datasets with incompatible feature spaces.

### 2.2.1 Preprocessing and normalization lock

Preprocessing is part of the fixed detector state. Within a seed, population, training baseline, and **named preprocessing protocol identity**, every compared threshold policy reuses one fitted preprocessing state. Threshold methods never select, refit, or alter preprocessing. Distinct protocol identities must never be mixed silently within one confirmatory ladder.

**Primary confirmatory federated method** (`FEDERATED_CLIENT_LOCAL_STANDARD`):

- transformer family: zero-mean unit-variance standardization (`StandardScaler`, `with_mean=True`, `with_std=True`);
- fit scope: **client-local**, fit only on each client’s benign training partition;
- fit partition: train only; calibration, evaluation, and future recalibration rows are transformed only;
- constant-feature rule: zero training scale uses unit scale and yields a zero-centered column (sklearn standard-scaler behaviour);
- out-of-range transformed values after fit: retained unclipped;
- fitted-state persistence: skops with trusted estimator classes only;
- transform serialization equivalence absolute tolerance: `1e-12` (engineering research amendment reusing the fixed-score absolute-tolerance magnitude; skops defines no scientific tolerance).

**Rationale.** The conference DATP reproducibility specification locks **per-client StandardScaler** for model-input normalization. The recovered anchor implementation stores one scaler per device fitted on benign train only. Meidan et al. leave scaling unspecified; the paper’s reproducibility table and the historical DATP artifact path supply the confirmatory lock for the N-BaIoT natural-device ladder. Cluster-threshold **fingerprint** standardization remains a separate score-side `StandardScaler` contract and is not model-input preprocessing.

**Supportive federated method** (`FEDERATED_POOLED_MIN_MAX`) — **not confirmatory:**

- transformer family: feature-wise min–max (`MinMaxScaler`);
- fit scope: pooled benign training rows of the federated population;
- same train-only, skops, unclipped, and tolerance rules.

Successor N-BaIoT federated-AE work often uses global/collaborative min–max for a shared detector. That geometry may be used only under its own protocol identity and claim tier (supportive / mechanism). It must not replace the confirmatory client-local StandardScaler ladder without an explicit claim-tier change.

**Centralized-reference scientific method** (`CENTRALIZED_POOLED_MIN_MAX`):

- independent of federated fitted states (never reuse federated client-local or pooled federated states);
- transformer family: min–max (`MinMaxScaler`);
- fit scope: pooled benign training rows of the centralized reference population;
- fit partition: train only;
- constant-feature rule: zero training range maps to zero;
- unclipped, skops, and tolerance rules as above.

**Missing-value and non-finite policy (all datasets):**

- no imputation, zero-fill, clipping, capping, infinity replacement, or label inference in the fitted pipeline;
- N-BaIoT non-finite declared features fail validation rather than being filled;
- CICIoT2023 model-input eligibility remains the outcome-blind finite-feature and recognized-label gate (canonical rows stay lossless; ineligible rows never enter client construction, split, fit, calibration, or evaluation);
- Edge-IIoTset model-input rows with non-finite retained numeric fields are excluded from model input with explicit provenance, never filled;
- attack labels never influence preprocessing fit;
- empty-train or missing-support recovery by fabricating zero-filled rows is forbidden.

**Excluded for multi-feature confirmatory AE input:** identity (no scaling) transforms.

These locks are prospective research amendments that complete the fixed-detector contract. Confirmatory client-local StandardScaler is paper-and-anchor backed; pooled MinMax is a declared supportive alternative from successor FL literature, not the confirmatory default.



**2.3 Sole manipulated variable**

For the B1–B4 ladder, the manipulated variable is:

```text
threshold_calibration_scope
```

Its permitted core values are:

```text
shared
physical_device_family
data_driven_client_cluster
individual_client
```

A policy-specific model, policy-specific checkpoint, policy-specific feature transformation, or policy-specific test population invalidates the controlled comparison.

**2.4 Prohibited causal contamination**

The following are forbidden inside the core ladder:

- retraining the autoencoder separately for B1, B2, B3, or B4;
- selecting a checkpoint independently for each threshold policy;
- selecting thresholds from attack-labelled data;
- choosing a policy parameter using held-out test F1, TPR, AUROC, balanced accuracy, or `CV(FPR)`;
- changing eligible clients between compared policies;
- removing clients that weaken the expected ordering;
- treating FedProx or model personalization as another threshold-scope condition;
- replacing a failed B1-versus-B2 result with a more favorable B4, shrinkage, or conformal result.

---

### 3. Calibration and evaluation contract

**3.1 Benign-only calibration**

Every core threshold and every DATP-compatible threshold variant is fitted using benign calibration data only.

Attack-labelled records are reserved for held-out evaluation and may not influence:

- threshold values;
- quantile selection;
- client eligibility;
- checkpoint selection;
- comparator tuning;
- shrinkage strength;
- conformal significance level;
- cluster count;
- cluster-feature selection;
- external-dataset client construction.

This boundary is central to DATP’s identity. It distinguishes the study from methods that optimize a threshold using both normal and anomalous validation summaries.

**3.2 Separation of calibration and evaluation**

Calibration records and evaluation records must be disjoint.

For temporal experiments:

- historical calibration must precede future recalibration;
- future recalibration must precede future evaluation;
- future evaluation cannot influence any earlier stage;
- data ordering or generated pseudo-time cannot replace real chronology.

**3.3 Client eligibility**

The canonical minimum benign calibration support is:

```text
n_k >= 100
```

Only eligible clients enter the primary cross-client false-positive dispersion calculation.

Eligibility is determined before test evaluation and is identical across policies compared within the same experiment.

An ineligible client may receive a separately declared deployment fallback only when the experiment explicitly studies fallback behavior. It cannot be silently included in the confirmatory population.

**3.4 Meaning of “fairness”**

Within DATP-Core, **fairness means operational or service-level false-positive-rate equity**.

It refers to how evenly false alarms are distributed across IoT clients.

It does not refer to:

- demographic fairness;
- protected-attribute fairness;
- individual human fairness;
- equalized odds over human groups;
- social or legal nondiscrimination.

Preferred manuscript language is:

- operational FPR equity;
- false-alarm equity;
- cross-client FPR dispersion;
- service-level operating-point equity;
- distribution of false-alarm burden.

The unqualified word *fairness* should be used sparingly and defined at first use.

**3.5 Primary operating-point concern**

The primary concern is:

```text
CV(FPR) across eligible clients
```

Absolute dispersion measures accompany it when mean FPR is small.

The confirmatory endpoint and its decision rule are specified in 04 — Evaluation and Reporting Protocol.

**3.6 Model-quality controls**

The following may be reported as controls:

- AUROC;
- Macro-F1;
- balanced accuracy;
- TPR or recall;
- P10 Macro-F1;
- worst-client balanced accuracy.

They do not replace `CV(FPR)` as the primary operating-point verdict.

In particular:

- unchanged AUROC does not invalidate a threshold-scope effect;
- improved AUROC does not establish a threshold-scope effect;
- lower P10 Macro-F1 under B2 is an important negative trade-off and must remain visible;
- global average performance cannot hide severe client-level false-alarm disparity.

---

### 4. Threshold-policy system

**4.1 Centralized reference: B0**

B0 is the privacy-incompatible centralized reference.

It uses:

- a centralized autoencoder trained on pooled benign training data;
- a pooled benign calibration threshold;
- separate centralized training and evaluation.

B0 is not part of the federated threshold-scope ladder.

A FedAvg model evaluated with a pooled threshold is not B0.

B0 exists to provide context for the cost of federation, not to participate in the confirmatory claim.

**4.2 Shared threshold: B1**

B1 is the shared-scope anchor.

Each eligible client computes its local benign quantile. The server calculates one shared threshold as the arithmetic mean of the eligible local quantiles.

At the canonical operating point:

```text
q = 0.95
```

Every eligible client uses the same resulting threshold.

B1 is not the exact pooled quantile and must not be described as such.

**4.3 Local threshold: B2**

B2 is the client-local scope anchor.

Each eligible client deploys its own benign calibration quantile at the same canonical target:

```text
q = 0.95
```

B2 is the comparator in the sole confirmatory B1-versus-B2 endpoint.

B2 is not assumed to dominate every policy on every metric. It may reduce FPR dispersion while increasing missed detections or weakening lower-tail classification performance for specific clients.

**4.4 Family threshold: B3**

B3 assigns one threshold to each validated physical-device family.

The threshold is formed from the eligible local thresholds belonging to that family.

B3 is permitted only when:

- a defensible family taxonomy exists;
- the taxonomy is defined independently of test outcomes;
- family membership is stable and auditable;
- the taxonomy represents device identity rather than attack labels.

B3 is a mechanism baseline.

It is available for the N-BaIoT physical-device regime and unavailable in regimes without a defensible family taxonomy.

**4.5 Cluster threshold: B4**

B4 is the taxonomy-free grouped-threshold mechanism.

Each eligible client is represented by its benign reconstruction-error fingerprint:

```text
mean(error)
standard_deviation(error)
skewness(error)
p95(error)
```

The canonical cluster count is:

```text
K = 3
```

The threshold for a cluster is the mean of the eligible local thresholds of its members.

B4 studies grouped threshold sharing on a fixed detector.

It is not:

- model clustering;
- clustered federated training;
- a privacy mechanism;
- a new clustering algorithm;
- a confirmatory endpoint.

Alternative cluster counts, including `K = 9`, are exploratory or supplementary. The canonical count cannot be changed after observing the most favorable test outcome.

**4.6 Ladder interpretation**

The core ladder represents increasing calibration granularity:

```text
B1: one threshold for the federation
B3: one threshold per physical-device family
B4: one threshold per data-driven client cluster
B2: one threshold per individual client
```

B3 and B4 do not have to form a strict numerical ordering between B1 and B2.

Their scientific role is to test whether intermediate sharing scopes recover part of B2’s operating-point equity while reducing per-client calibration dependence.

---

### 5. Supportive threshold variants

Threshold variants preserve the fixed detector but alter the threshold estimator.

They remain outside the B1–B4 identity and cannot become confirmatory after results are observed.

**5.1 Quantile sensitivity**

The canonical quantile remains:

```text
q = 0.95
```

A pre-specified sensitivity grid tests whether conclusions depend on that choice.

An alternative quantile cannot replace the canonical endpoint post hoc.

**5.2 Local–global shrinkage**

The local–global shrinkage threshold is:

\[
\tau_k(\lambda)
=
\lambda \tau_{k,\mathrm{local}}
+
(1-\lambda)\tau_{\mathrm{shared}}
\]

Interpretation:

- `lambda = 0` gives the shared endpoint;
- `lambda = 1` gives the local endpoint;
- intermediate values partially pool client information.

The complete pre-specified lambda curve is the result.

A favorable intermediate lambda cannot be presented as the primary policy unless its selection rule was fixed without test leakage.

**5.3 Calibration-size-aware shrinkage**

A size-aware fallback may set:

```text
lambda = lambda(n_k)
```

The function must be:

- fixed before evaluation;
- identical across clients apart from `n_k`;
- bounded in `[0, 1]`;
- explicitly reported;
- compared against fixed-lambda endpoints.

It is a calibration-robustness mechanism, not a novel statistical-theory claim.

**5.4 Split-conformal local threshold: B2-conf**

B2-conf applies a finite-sample-adjusted local conformal quantile to benign reconstruction errors.

Its role is to test held-out benign coverage and address the criticism that per-client thresholds merely equalize FPR by construction.

The principal federated-conformal positioning anchors are Lu et al.’s Federated Conformal Prediction framework and Humbert et al.’s one-shot federated conformal method.[^lu-fcp][^humbert-fcp]

B2-conf does not establish:

- arbitrary client-conditional coverage;
- validity under unrestricted non-exchangeability;
- robustness to Byzantine calibration;
- a full conformal DATP contribution;
- a replacement confirmatory endpoint.

Coverage failures, finite-sample granularity, and heterogeneous-client limitations remain reportable.

---

### 6. Federated threshold comparator

**6.1 `B-FedStatsBenign`**

`B-FedStatsBenign` is the DATP-compatible benign-only federated summary-statistics comparator.

It exists to compare threshold-scope personalization against a federated shared-threshold method that communicates summary statistics rather than local score arrays.

Its main construction must:

- use benign calibration information only;
- use the full pooled variance decomposition, including between-client mean-shift;
- target the same benign exceedance as the DATP quantile;
- lock its protocol before result inspection;
- disclose every statistic communicated by a client;
- remain a shared-threshold comparator.

The primary comparator is matched by target exceedance.

A fixed multiplier such as `k = 2`, `2.5`, or `3` is supplementary sensitivity only.

**6.2 Relationship to Laridi et al.**

Laridi et al. proposed a federated autoencoder threshold based on aggregated summary statistics from both normal and anomalous validation data.[^laridi]

DATP’s comparator deliberately excludes anomalous calibration information.

Therefore:

- `B-FedStatsBenign` is not a faithful Laridi reproduction;
- it must not be called `B-LaridiFaithful`;
- its results cannot be used to claim reproduction of Laridi et al.;
- the difference in calibration contracts must be disclosed in related work and limitations.

The reserved name `B-LaridiFaithful` refers only to a genuinely anomaly-informed implementation, which is out of scope for DATP-Core.

---

### 7. Training-side stress tests

Training-side stress tests change the detector and therefore cannot share the causal interpretation of the B1–B4 ladder.

They require separate models, score sets, and evaluation.

**7.1 FedProx**

FedProx is the aggregation-side heterogeneity stress test.

FedProx modifies local optimization with a proximal term intended to limit divergence from the current global model under heterogeneous federated data.[^fedprox]

Its purpose in DATP-Core is to ask:

> Does a heterogeneity-aware training algorithm absorb the operating-point benefit of threshold personalization?

FedProx results must be described as a training-side sensitivity.

They cannot be merged with the FedAvg confirmatory endpoint.

**7.2 Ditto**

Ditto is the planned model-personalization stress test.

Ditto maintains global and persistent client-personalized models regularized toward the global state.[^ditto]

The name *Ditto* may be used only when the implementation preserves genuine Ditto semantics, including:

- a distinct global model;
- persistent client-personalized states;
- the correct proximal personalized objective;
- no aggregation of personalized states as if they were global;
- separate evaluation.

The purpose is to ask:

> Does model personalization make threshold personalization redundant, complementary, or partially absorbed?

The in-paper comparison remains one personalized-model family, not a broad personalized-FL benchmark.

**7.3 Fallback naming**

When genuine Ditto cannot be implemented without violating the locked model contract, the alternative must be named according to the algorithm actually implemented, such as:

```text
FedRep-AE
FedPer-AE
```

A fallback must never be called Ditto.

A fallback changes the scientific comparator and must be recorded before its results are used.

**7.4 Separation from the core ladder**

For every stress-test model:

- B1, B2, B3, and B4 may be recomputed from that model’s scores;
- the model’s threshold-scope difference may be compared with the FedAvg difference;
- the result may support retention, partial absorption, or full absorption;
- the result cannot alter the identity of the FedAvg core ladder.

---

### 8. Evidence architecture

**8.1 Sole confirmatory evidence**

Only one endpoint is confirmatory:

- N-BaIoT physical-device regime;
- B1 versus B2;
- `CV(FPR)`;
- ten paired seeds;
- locked BCa decision rule.

The statistical decision rule is specified in 04 — Evaluation and Reporting Protocol.

**8.2 Supporting evidence families**

All remaining work belongs to one of the following roles:

- supportive robustness;
- mechanism analysis;
- threshold variant;
- external validation;
- aggregation-side stress test;
- model-personalization stress test;
- applicability boundary;
- temporal boundary;
- exploratory supplement;

A supportive analysis cannot be promoted to rescue a failed confirmatory endpoint.

An external dataset cannot silently become a second confirmatory regime.

An exploratory result cannot be rewritten as pre-specified evidence after it is observed.

**8.3 Honest negative evidence**

Null, opposite, and infeasible outcomes remain scientifically meaningful. They must be reported rather than hidden or replaced by a more favorable analysis.

---

### 9. Dataset and regime boundaries

Detailed regime procedures belong to 03 — Experiment Catalogue. This section fixes only the identity-level boundaries.

**9.1 N-BaIoT physical-device anchor**

N-BaIoT is the confirmatory dataset anchor.

The original dataset study evaluated nine commercial IoT devices infected with Mirai and BASHLITE using deep autoencoder anomaly detection.[^nbaiot]

For DATP-Core:

- the nine physical devices are the natural clients;
- this is the only confirmatory client population;
- the device-family taxonomy may support B3;
- all nine clients remain visible in mechanism reporting;
- the small client count is an explicit limitation.

**9.2 CICIoT2023 available-data boundary**

The original CICIoT2023 publication describes a large IoT environment with 105 devices and 33 attacks.[^ciciot2023]

The available processed DATP artifact does not retain a verified physical-device mapping.

Therefore:

- available-data pseudo-clients may be used only as a dataset-specific applicability boundary;
- a null result cannot be generalized to the original 105-device topology;
- source-paper device counts cannot be substituted for missing artifact metadata;
- device-aware wording is prohibited for this regime.

Without verified physical-device identities, CICIoT2023 cannot be repartitioned as physical devices. Artificial groupings and inferred chronology are not valid substitutes.

The lossless canonical artifact remains the raw-fidelity record. Before any file-defined client construction, split, fitting, calibration, or evaluation, a CICIoT2023 row is eligible for model input if and only if its normalized label is recognized and every declared model-input feature is finite. The gate records the missing-or-unrecognized-label and non-finite-feature signals independently, preserves stable row identity and source provenance, and applies identically to every compared method. It never imputes, zero-fills, caps, clips, replaces infinities, or infers labels.

**9.3 Controlled heterogeneity regime**

The Dirichlet N-BaIoT regime is a controlled sensitivity experiment.

It does not replace natural device partitioning.

It may support a graded heterogeneity interpretation but cannot establish that one scalar non-IID parameter reproduces real device heterogeneity.

**9.4 Edge-IIoTset external validation**

Edge-IIoTset is the sole new external dataset.[^edge-iiotset]

Its client definition is established from first-principles dataset evidence, not by copying a partition from another paper.

The external scope is benign operating-point equity.

Where attack traffic cannot be validly assigned to each client:

- per-client TPR is unavailable;
- per-client Macro-F1 is unavailable;
- per-client balanced accuracy is unavailable;
- per-client AUROC is unavailable;
- attack-sensitive cross-client equity is unavailable.

These outcomes must be represented as unavailable rather than estimated, inherited from another partition, or fabricated.

B3 is omitted when no defensible external family taxonomy exists.

**9.5 Temporal external regime**

The temporal experiment is limited to one-shot threshold recalibration on a verified chronological Edge-IIoTset population.

It does not establish:

- continuous adaptation;
- online learning;
- streaming drift detection;
- drift-triggered recalibration;
- concept-drift resolution;
- production stability over repeated cycles.

CICIoT2023 temporal probing remains suppressed when valid timestamps are absent.

**9.6 Dataset expansion limit**

DATP-Core adds no external IoT dataset beyond Edge-IIoTset.

Adding another dataset would change the study’s scientific scope.

This limit prevents the paper from becoming a generic multi-dataset FL-IDS benchmark.

---

### 10. Included scientific scope

DATP-Core strengthens the original DATP study along five bounded directions.

**10.1 External validation**

One external IoT/IIoT dataset tests whether benign false-alarm equity effects transfer beyond N-BaIoT.

**10.2 Federated threshold comparison**

One benign-only summary-statistics comparator tests whether threshold personalization is dominated by a distributed shared-threshold alternative.

**10.3 Training-side robustness**

Two external stress tests examine:

- heterogeneity-aware federated optimization;
- client model personalization.

They remain outside the causal ladder.

**10.4 Threshold-estimation depth**

The threshold story is extended through:

- quantile-level sensitivity;
- local–global shrinkage;
- calibration-size-aware shrinkage;
- a bounded split-conformal local-threshold diagnostic.

**10.5 Temporal boundary**

One chronological, one-shot recalibration experiment tests whether frozen thresholds age and whether a single future benign calibration window recovers operating-point equity.

**10.6 Mechanism analysis**

The journal extension includes bounded mechanism work covering:

- family and cluster granularity;
- cluster stability;

- per-client benign and attack score geometry;
- heterogeneity–benefit association;
- threshold movement versus FPR/TPR trade-off.

These analyses explain the result but do not create additional confirmatory claims.

**10.7 Hard scope limits**

The complete programme is limited to:

- one new IoT dataset;
- three external comparator families:
  - FedProx;
  - one model-personalization method;
  - one benign-only federated threshold comparator;
- four threshold-extension families;
- one temporal-recalibration family;
- the pre-specified mechanism programme;
- ten paired seeds for the confirmatory endpoint.

Expansion beyond these limits would change the study’s scientific scope.

---

### 11. Excluded scientific scope

**11.1 Security attacks and defenses**

DATP-Core does not study adversarial attacks, poisoning, or defensive mechanisms.

**11.2 Formal privacy**

DATP-Core does not implement or claim formal privacy protections or guarantees.

Keeping raw data local is a structural property of FL, not a formal privacy guarantee.

B4 clustering is not a privacy mechanism.

Threshold-message size is not a privacy proof.

**11.3 Deployment validation**

DATP-Core does not provide hardware, resource, network-traffic, or production deployment validation.

Communication and storage may be estimated from serialized message sizes. Such estimates must not be called deployment measurements.

**11.4 Fleet scale**

The paper does not claim fleet-scale validation above 100 clients.

Synthetic client counts or available-data pseudo-clients do not establish real fleet-scale deployment.

**11.5 Full drift handling**

The temporal experiment does not provide continuous adaptation, online recalibration, or autonomous drift detection.

**11.6 Broad FL benchmarking**

The study is not an exhaustive benchmark of federated learning, personalization, clustering, anomaly detection, privacy, or intrusion-detection methods.

FedBN is excluded because introducing BatchNorm would change the locked autoencoder architecture and therefore the scientific object.

**11.7 Federated conformal breadth**

The bounded B2-conf diagnostic does not expand into federated conformal benchmarking, method development, adversarial conformal prediction, or online adaptation.

Lu et al. and Humbert et al. are primary prior-art anchors for federated conformal prediction.[^lu-fcp][^humbert-fcp]

---

### 12. Terminology and naming rules

**12.1 Project naming**

Use:

```text
DATP
```

for the original method and conference identity.

Use:

```text
DATP-Core
```

for the extended study.

Use:

```text
anchor
```

for the conference-faithful reference protocol inside DATP-Core.

Avoid using *journal* as a model, experiment, or scientific method name.

**12.2 Threshold-policy names**

Canonical policy identifiers are:

```text
B0
B1
B2
B3
B4
```

Their meanings are fixed by this document.

Do not reuse these identifiers for:

- shrinkage;
- conformal variants;
- summary-statistics comparators;
- stress-test models;
- future methods.

**12.3 Threshold-variant names**

Use:

```text
tau-shrink
calibration-size-aware shrinkage
B2-conf
B-FedStatsBenign
```

Do not use:

```text
B3-LGS
B5
Laridi-faithful benign
```

B3 is reserved for physical-device-family thresholding.

B5 is retired and must not reappear.

**12.4 Laridi naming**

Use:

```text
B-FedStatsBenign
```

for the benign-only DATP-compatible summary-statistics comparator.

Reserve:

```text
B-LaridiFaithful
```

for a genuinely anomaly-informed reproduction, which is out of scope.

Never call the benign adaptation *faithful*.

**12.5 Personalized-model naming**

Use *Ditto* only for a genuine Ditto implementation.

Otherwise use the actual method name, such as:

```text
FedRep-AE
FedPer-AE
```

Do not use generic names such as:

```text
personalized model v2
local personalized baseline
hybrid personalization
```

when a recognized algorithm is implemented.

**12.6 Regime names**

Regime identifiers remain:

```text
Regime A
Regime B-a
Regime B-b
Regime C
Regime D
Regime D-temporal
```

They refer to scientific dataset/population contracts, not arbitrary implementation labels.

Every mention must include a descriptive phrase at first use, such as:

```text
Regime A — N-BaIoT physical-device anchor
```

**12.7 Statistical and equity language**

Use:

```text
CV(FPR)
IQR(FPR)
worst-client FPR
false-alarm equity
operating-point equity
cross-client FPR dispersion
```

Avoid:

```text
fair model
fair detector
equal treatment
privacy-preserving threshold
robust threshold
optimal threshold
```

unless the corresponding property is formally established.

**12.8 Novelty language**

Do not use:

- first;
- novel federated conformal prediction;
- first personalized threshold;
- state of the art;
- universally superior;
- solves non-IID;
- guarantees fairness;
- privacy preserving;
- deployment ready.

Such language requires independent evidence beyond this roadmap.

---

### 13. Claim-level framing boundaries

The following scope-level framing remains mandatory.

**13.1 Permitted central framing**

DATP-Core may be framed as:

- a controlled threshold-calibration-scope study;
- a study of operating-point reliability under heterogeneous federated IoT clients;
- a false-alarm-equity analysis on a fixed anomaly detector;
- a journal extension with external, stress-test, and mechanism evidence;
- an evaluation of when threshold personalization remains useful.

**13.2 Prohibited central framing**

DATP-Core must not be framed as:

- a new federated-learning optimizer;
- a complete FL-IDS framework benchmark;
- a privacy-preserving security system;
- a robust federated-learning defense;
- a drift-adaptive production IDS;
- a fleet-scale deployment;
- a universal thresholding method;
- a method that improves every client;
- a method that improves global Macro-F1;
- a solution to non-IID federated learning.

**13.3 AUROC language**

Permitted:

> AUROC is reported as a detector-quality control and is expected to remain unchanged when only threshold scope changes.

Prohibited:

> B2 improves AUROC.

A threshold change cannot change score ranking when the model and scores are fixed.

**13.4 Macro-F1 language**

Permitted:

> Threshold personalization may reduce false-positive dispersion while producing a lower-tail detection trade-off.

Prohibited:

> DATP improves detection performance overall.

That statement is unsupported when global or lower-tail classification metrics weaken.

**13.5 External validation language**

Permitted:

> Edge-IIoTset provides independent validation of benign operating-point equity under the audited sensor-group client definition.

Prohibited:

> DATP generalizes attack detection across Edge-IIoTset clients.

Per-client attack-sensitive metrics are unavailable under the audited artifact.

**13.6 Temporal language**

Permitted:

> One-shot recalibration is evaluated as a bounded response to threshold aging under a verified chronological split.

Prohibited:

> DATP handles concept drift.

**13.7 Privacy language**

Permitted:

> Raw traffic remains local during federated training, but no formal privacy mechanism or guarantee is provided.

Prohibited:

> DATP is privacy preserving.

**13.8 Deployment language**

Permitted:

> Communication and storage requirements are estimated from message content.

Prohibited:

> DATP is lightweight, edge ready, or deployable on constrained devices.

No hardware validation supports those claims.

---

### 14. Accepted scientific limitations

The following limitations are accepted by design and must be disclosed rather than “fixed” through scope expansion.

**14.1 Small natural client population**

N-BaIoT provides nine physical-device clients.

The study does not infer fleet-scale behavior from this population.

**14.2 One external dataset**

Edge-IIoTset improves external validity but does not establish universal cross-dataset generalization.

**14.3 Incomplete external attack assignment**

The available Edge-IIoTset data support benign operating-point equity but not valid per-client attack-sensitive evaluation.

**14.4 Single temporal family**

One-shot recalibration on one verified chronological population is a boundary probe, not a general drift solution.

**14.5 No formal privacy guarantee**

Federated data locality is retained, but model updates and threshold summaries may disclose information. No formal protection is claimed.

**14.6 No hardware evidence**

Estimated message sizes do not establish latency, energy, memory, or deployment feasibility.

**14.7 Threshold trade-offs**

Reducing FPR dispersion may worsen attack sensitivity for some clients. The journal contribution includes this trade-off rather than assuming it away.

**14.8 Comparator incompleteness**

One aggregation stress test and one model-personalization stress test cannot establish superiority over the full FL literature.

**14.9 Conformal limitation**

B2-conf is an empirical diagnostic under bounded assumptions. It does not establish arbitrary per-client conditional coverage under heterogeneous, non-exchangeable, or adversarial data.

---

### 15. Research foundations

[^nbaiot]: Y. Meidan et al., “N-BaIoT—Network-Based Detection of IoT Botnet Attacks Using Deep Autoencoders,” *IEEE Pervasive Computing*, 2018. DOI: [10.1109/MPRV.2018.03367731](https://doi.org/10.1109/MPRV.2018.03367731).

[^edge-iiotset]: M. A. Ferrag et al., “Edge-IIoTset: A New Comprehensive Realistic Cyber Security Dataset of IoT and IIoT Applications for Centralized and Federated Learning,” *IEEE Access*, 2022. DOI: [10.1109/ACCESS.2022.3165809](https://doi.org/10.1109/ACCESS.2022.3165809).

[^ciciot2023]: E. C. P. Neto et al., “CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment,” *Sensors*, 2023. DOI: [10.3390/s23135941](https://doi.org/10.3390/s23135941).

[^laridi]: S. Laridi, G. Palmer, and K.-M. M. Tam, “Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding,” *Scientific Reports*, 2024. DOI: [10.1038/s41598-024-76961-2](https://doi.org/10.1038/s41598-024-76961-2).

[^fedprox]: T. Li et al., “Federated Optimization in Heterogeneous Networks,” *Proceedings of MLSys*, 2020. Primary manuscript: [arXiv:1812.06127](https://arxiv.org/abs/1812.06127).

[^ditto]: T. Li, S. Hu, A. Beirami, and V. Smith, “Ditto: Fair and Robust Federated Learning Through Personalization,” *Proceedings of ICML*, PMLR 139, 2021. [Primary publication](https://proceedings.mlr.press/v139/li21h.html).

[^lu-fcp]: C. Lu et al., “Federated Conformal Predictors for Distributed Uncertainty Quantification,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/lu23i.html).

[^humbert-fcp]: P. Humbert, B. Le Bars, A. Bellet, and S. Arlot, “One-Shot Federated Conformal Prediction,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/humbert23a.html).

## Experiment programme and decision rules

**Document purpose**

This catalogue defines the complete DATP journal-extension experiment programme in a navigable, section-driven form. It explains what is executed, what remains fixed, why each experiment exists, which evidence role it may support, and how weak, null, contradictory, or infeasible outcomes are handled.

The document deliberately avoids compact experiment matrices and opaque coded identifiers. Each experiment is identified by a descriptive scientific title that can be understood without consulting a code catalogue.

### 1. How to read this catalogue

**1.1 Evidence-role vocabulary**

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

**1.2 Experiment specification format**

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
- **Prohibited uses**

This structure replaces the previous matrix rows and prevents important requirements from being hidden in dense cells.

---

### 2. Scientific execution invariants

The following rules apply to every experiment unless a stress-test section explicitly states otherwise.

**2.1 Fixed-detector causal isolation**

For the B1–B4 threshold-scope ladder:

- one FedAvg autoencoder is trained per seed;
- the same trained encoder state is used across B1, B2, B3, and B4;
- the same calibration and test scores are used across B1, B2, B3, and B4;
- threshold scope is the only manipulated causal variable;
- no policy-specific retraining is permitted;
- no threshold policy may alter preprocessing, training data, model parameters, score generation, test labels, or client eligibility.

A difference between B1 and B2 is therefore interpreted as an operating-point effect of threshold-calibration scope, not as a model-quality difference.

**2.2 Benign-only threshold calibration**

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

**2.3 Paired experimental design**

Within each seed, policies compared in the same experiment must receive:

- the same trained model when the experiment belongs to the fixed-detector ladder;
- the same client population;
- the same calibration records before any declared subsampling;
- the same held-out evaluation records;
- the same eligibility rule;
- the same metric implementation.

The training seed is the independent replication unit. Clients, records, checkpoints, windows, or sweep cells are not treated as independent scientific replications.

**2.4 Eligibility**

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

**2.5 Checkpoint discipline**

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

**2.6 Negative-result discipline**

Every mandatory experiment is reportable when it produces:

- a strong expected effect;
- a weak effect;
- a null effect;
- a reversed effect;
- unstable estimates;
- an infeasibility result.

No experiment may be removed because its result is unfavorable. A supportive or mechanism experiment cannot replace the confirmatory endpoint.

---

### 3. Threshold policies and comparison methods

**3.1 Centralized reference: B0**

B0 is a pooled-data centralized autoencoder reference with a pooled benign threshold.

It is included to show the performance of a privacy-incompatible centralized reference. It is not part of the federated threshold-scope causal ladder and must never be presented as another B1–B4 policy.

B0 must use its own centralized model. FedAvg-generated scores cannot be relabelled as B0.

**3.2 Shared threshold: B1**

Each eligible client computes its local benign `q`-quantile. The server forms one shared threshold by taking the arithmetic mean of the local quantiles.

At the canonical setting:

```text
q = 0.95
```

Every eligible client is evaluated using the same B1 threshold.

B1 is the shared-scope anchor for the confirmatory comparison.

**3.3 Per-client threshold: B2**

Each eligible client uses its own benign `q`-quantile as its deployed threshold.

At the canonical setting:

```text
q = 0.95
```

B2 is the local-scope anchor and the confirmatory comparator.

B2 is not described as universally superior. It may reduce cross-client false-positive dispersion while worsening detection quality for clients with weak benign–attack score separation.

**3.4 Family threshold: B3**

B3 groups N-BaIoT clients by the locked physical-device family taxonomy and assigns one family-level mean threshold to clients in the same family.

B3 is available only where a defensible family taxonomy exists. It is therefore:

- available in Regime A;
- unavailable in Regime C unless the synthetic partition preserves a meaningful family mapping;
- omitted from Edge-IIoTset because no equivalent family taxonomy is established;
- unavailable for CICIoT2023 file-defined pseudo-clients.

B3 is a mechanism baseline, not a confirmatory comparator.

**3.5 Cluster threshold: B4**

B4 creates taxonomy-free groups from each client's benign reconstruction-error fingerprint:

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

Other cluster counts are granularity sensitivity analyses and remain exploratory. `K = 9` is not promoted as the main setting.

B4 clustering is a threshold-sharing mechanism on a fixed detector. It is not a model-clustering method, a privacy mechanism, or a new clustering algorithm.

**3.6 Shared-threshold construction controls**

Two shared-threshold controls test whether the B1 result is merely a consequence of averaging local quantiles:

**Pooled shared quantile**
The exact `q`-quantile of the pooled benign calibration scores.

**Sample-weighted shared threshold**
A shared threshold formed by weighting local threshold contributions by eligible benign calibration size.

These constructions are supportive controls. They do not replace B1 as the locked confirmatory anchor.

**3.7 Local–global shrinkage threshold**

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

**3.8 Split-conformal local threshold: B2-conf**

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

**3.9 Benign federated summary-statistics comparator**

`B-FedStatsBenign` is the matched, benign-only federated threshold comparator.

It communicates pre-specified benign summary statistics and constructs a shared threshold without using anomalous validation data. Its operating point must be matched to the DATP quantile target rather than selected to maximize F1.

The comparison must clearly distinguish:

- exact pooled benign quantile;
- arithmetic mean of local quantiles;
- sample-weighted shared construction;
- benign summary-statistics threshold;
- local per-client quantiles.

A Laridi-faithful implementation is not executed because Laridi et al. use normal and anomalous validation summaries, violating DATP’s benign-only threshold contract.[^laridi]

**3.10 FedProx stress-test model**

FedProx modifies the local training objective by adding a proximal penalty that constrains local deviation from the current global model. It was proposed to address statistical and systems heterogeneity and is appropriately used here as an aggregation-side stress test rather than as part of the threshold ladder.[^fedprox]

The proximal coefficient grid is pre-registered and frozen before attack-sensitive or confirmatory test outcomes are inspected:

```text
mu in {0.001, 0.01, 0.1, 1.0}
```

`mu = 0` is FedAvg-equivalent and is not treated as a FedProx condition.

**3.11 Ditto personalized model**

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

### 4. Experimental regimes

**4.1 Regime A — N-BaIoT physical-device anchor**

**Scientific role**

Regime A is the sole confirmatory regime and the principal mechanism-analysis substrate.

**Dataset and population**

N-BaIoT contains traffic from nine commercial IoT devices exposed to Mirai and BASHLITE botnet activity in the original dataset study.[^nbaiot] The nine physical devices are the nine federated clients.

**Permitted analyses**

Regime A supports:

- B0, B1, B2, B3, and B4;
- the confirmatory B1-versus-B2 experiment;
- shared-threshold construction controls;
- quantile sensitivity;
- family/cluster granularity and stability;
- score-distribution mechanism analyses;
- calibration-size ablation;
- local–global shrinkage;
- B2-conf;
- `B-FedStatsBenign`;
- FedProx;
- Ditto;
- operational alert-burden translation when a real or cited traffic rate exists.

**Primary limitation**

The regime contains only nine physical clients. Client-level results are therefore displayed completely; no client may be filtered because it weakens the desired pattern.

**4.2 Regime B-a — CICIoT2023 file-defined applicability boundary**

**Scientific role**

Regime B-a tests whether threshold personalization remains useful when the available processed artifacts form near-homogeneous file-defined pseudo-clients rather than natural physical-device clients.

**Dataset context**

The original CICIoT2023 study describes a large IoT topology with 105 devices and 33 attacks grouped into seven categories.[^ciciot2023] Those source-level properties do not automatically survive into every processed CSV distribution.

The available data contain 63 file-defined pseudo-clients and lack the metadata required to reconstruct physical-device clients.

**Permitted interpretation**

Regime B-a may support only an applicability-boundary statement about the file-defined pseudo-clients.

It must not be used to claim:

- device-level generalization on CICIoT2023;
- physical-client equity;
- temporal behavior;
- device-aware threshold performance on the original 105-device topology.

**Permitted analyses**

- B0;
- B1;
- B2;
- B4;
- pairwise benign-distribution Jensen–Shannon divergence;
- `CV(FPR)`, IQR, and range;
- descriptive quantile-estimation comparisons.

**Required conclusion discipline**

A null B1-versus-B2 difference is expected to be scientifically useful: it indicates that personalization may be unnecessary when clients are nearly homogeneous.

**4.3 Regime C — controlled N-BaIoT heterogeneity sweep**

**Scientific role**

Regime C tests whether the threshold-scope effect changes systematically with controlled non-IID severity.

**Population**

Twenty synthetic clients are constructed from the N-BaIoT analysis population using the locked Dirichlet partition procedure.

**Severity grid**

```text
alpha in {0.1, 0.3, 0.5, 1.0, 10.0, IID}
```

Lower `alpha` values represent stronger concentration and more severe distributional skew. Dirichlet partitioning is used only as a controlled sensitivity mechanism; it does not replace the natural physical-device evidence of Regime A.

**Policies**

- B1;
- B2;
- B4.

B3 is not automatically available because the synthetic partition need not preserve the physical family taxonomy.

**Interpretation**

The primary expectation is a graded relationship between heterogeneity and the B1–B2 `CV(FPR)` difference.

However:

- strict monotonicity is not required;
- overlapping low-alpha seed distributions are described as a high-heterogeneity band;
- a non-monotone result is reported;
- the sweep does not become confirmatory.

**4.4 Regime D — Edge-IIoTset external benign-equity validation**

**Scientific role**

Regime D is the independent external validation of benign operating-point equity.

**Dataset context**

The Edge-IIoTset paper presents a purpose-built IoT/IIoT testbed with devices, sensors, protocols, and edge/cloud configurations, designed for centralized and federated-learning security research.[^edge-iiotset]

**Client definition**

Ten benign sensor-group folders form the static external client population. The Modbus folder is valid for static benign-equity evaluation because its rows retain the declared 63-column layout; its `frame.time` values are address literals and therefore exclude it only from the temporal population.

Eligible-benign coverage is 1.0 under the locked `n_k >= 100` rule.

**Model-input representation and architecture**

The canonical Edge rows retain their original lexical values for provenance, but the external detector has a separate, immutable numeric model-input schema. A complete canonical-data audit identified 33 columns for which every non-null value in all 11,209,913 static benign rows parses strictly as a finite numeric value. Those columns, in canonical order, are:

```text
icmp.seq_le, icmp.unused, http.file_data, http.content_length,
http.request.uri.query, http.request.method, http.referer,
http.request.full_uri, http.request.version, http.response, http.tls_port,
tcp.ack, tcp.connection.fin, tcp.connection.rst, tcp.connection.syn,
tcp.connection.synack, tcp.flags.ack, tcp.seq, tcp.srcport, udp.port,
udp.stream, udp.time_delta, dns.qry.type, dns.retransmission,
dns.retransmit_request, dns.retransmit_request_in,
mqtt.conflag.cleansess, mqtt.msg_decoded_as, mqtt.msgtype, mqtt.topic_len,
mqtt.ver, mbtcp.trans_id, mbtcp.unit_id
```

This is a prospective, versioned numeric-projection amendment. It uses strict numeric parsing only; it does not fill, coerce, hash, ordinal-encode, one-hot encode, or fit a vocabulary for mixed lexical fields. `raw_timestamp`, labels, source folders, and client identity remain provenance or outcome fields and never enter the model. A row whose retained numeric value is null or non-finite is excluded with provenance; no missing value is manufactured. The input feature order is part of the preprocessing protocol checksum and is identical for every client.

The external autoencoder is therefore a 33-dimensional symmetric model with widths `(33, 25, 17, 11, 8, 11, 17, 25, 33)`. It preserves the locked N-BaIoT model's encoder depth, symmetry, and rounded relative compression ratios while matching the declared schema exactly. Padding the vector to 115 dimensions, truncating an existing model, or silently reusing 115-input weights is prohibited. The Edge-IIoTset source establishes the 61 extracted features and the independent testbed; it does not prescribe a categorical encoder, so no unvalidated categorical transformation is represented as source-locked.[^edge-iiotset]

**Available outcomes**

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

**Unavailable outcomes**

Attack traffic is confined to the attacker’s subnet. Consequently, valid per-client attack assignment is unavailable.

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

**B3 status**

B3 is omitted because no defensible Edge-IIoTset family taxonomy has been established for the ten sensor-group clients.

**4.5 Regime D-temporal — Edge-IIoTset one-shot recalibration boundary**

**Scientific role**

This regime tests threshold aging and one-shot recalibration under genuine chronology. It is a temporal boundary experiment, not a drift-detection system.

**Population**

Nine temporal groups are used. Modbus is excluded because its timestamps are unusable.

**Chronological split**

Each client’s benign records are stably sorted by genuine capture time and partitioned as:

```text
historical training       55%
historical calibration    15%
future recalibration      10%
future evaluation         20%
```

Duplicate timestamps preserve original stable row order.

**Compared deployment states**

- threshold frozen from historical calibration;
- one-shot threshold recomputed from the future recalibration window;
- matched random-fractional static reference over the same nine clients. The static reference uses the same 55/15/10/20 row budget after deterministic client-local randomization: train, calibration, an explicitly retained but non-fitted/non-scored/non-evaluated reserve, and evaluation. The reserve preserves row-budget comparability without assigning a false temporal meaning to static rows.

**Scope boundary**

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

### 5. Confirmatory experiment

**5.1 Regime A shared-versus-local threshold-scope confirmation**

**Scientific role**

**Confirmatory.** This is the only experiment that can establish the locked main journal endpoint.

**Question**

Under one fixed FedAvg autoencoder per seed, does changing the calibration scope from one shared threshold (B1) to one threshold per physical device (B2) reduce cross-client false-positive-rate dispersion on N-BaIoT?

**Why the experiment is necessary**

The conference result used five seeds. The journal extension must reproduce that evidence and expand it to ten paired seeds without suppressing a less favorable estimate.

**Population and inputs**

- Regime A;
- nine physical-device clients;
- ten paired training seeds;
- one locked primary checkpoint per seed;
- benign calibration scores;
- held-out benign and attack test scores;
- unchanged eligibility.

**Fixed elements**

- autoencoder architecture;
- FedAvg training;
- local epochs `E = 1`;
- full participation;
- preprocessing;
- checkpoint-selection rule;
- quantile `q = 0.95`;
- test records;
- metric implementation.

**Experimental factor**

Threshold-calibration scope:

- B1 shared threshold;
- B2 per-client threshold.

**Procedure**

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

**Required outcomes**

- B1 and B2 per-client FPR for every seed;
- seed-level B1 and B2 `CV(FPR)`;
- ten paired deltas;
- mean or median paired delta, as defined in the evaluation protocol;
- 95% BCa interval;
- sign-consistency count;
- IQR and range;
- Macro-F1, balanced accuracy, TPR, and P10 Macro-F1 controls;
- complete nine-client result display.

**Statistical unit and analysis**

The training seed is the independent unit.

The BCa interval is the confirmatory inferential result. Wilcoxon signed-rank and matched-pairs rank-biserial correlation are descriptive secondary evidence.

**Interpretation rules**

**Confirmatory support**
The 95% BCa interval excludes zero in the positive direction.

**Directional but inconclusive**
The point estimate is positive, but the interval touches or crosses zero.

**No observed advantage**
The estimate is approximately null and the interval includes zero.

**Opposite direction**
B2 increases `CV(FPR)` relative to B1.

Every outcome becomes the main ten-seed result. The five-seed result is labelled preliminary when the ten-seed evidence is weaker or materially different.

**Prohibited uses**

- no checkpoint selection from this result;
- no replacement by B4, shrinkage, or B2-conf if the endpoint fails;
- no removal of unfavorable seeds;
- no claim that B2 improves overall detection performance.

---

### 6. Supportive robustness experiments

**6.1 Shared-threshold construction sensitivity**

**Scientific role**

**Supportive.**

**Question**

Is the observed B1-versus-B2 difference caused specifically by B1’s arithmetic mean of local quantiles, or does it persist across alternative shared-threshold constructions?

**Comparison set**

- B1 arithmetic mean of local quantiles;
- exact pooled benign quantile;
- sample-weighted shared construction;
- B2 local quantiles.

**Procedure**

Use the same Regime A model, scores, clients, and seeds as the confirmatory experiment. Recompute thresholds only.

For each shared construction:

- compute the shared threshold;
- evaluate all eligible clients;
- compute `CV(FPR)`, IQR, range, and worst-client FPR;
- calculate the paired difference relative to B2;
- report achieved pooled and per-client exceedance.

**Interpretation**

**Robust construction effect**
All reasonable shared constructions retain higher FPR dispersion than B2.

**Construction-specific effect**
One shared construction approaches or outperforms B2. The claim is narrowed to the locked B1 construction.

**No shared-versus-local distinction**
Shared constructions and B2 are practically similar.

This experiment cannot alter the definition of the confirmatory B1 endpoint.

**6.2 Quantile-level sensitivity**

**Scientific role**

**Supportive threshold sensitivity.**

**Question**

Does the B1/B2/B4 ordering depend on choosing `q = 0.95`?

**Quantile grid**

```text
q in {0.90, 0.95, 0.975, 0.99}
```

**Procedure**

For every Regime A seed and quantile:

- compute B1, B2, and canonical B4;
- evaluate on unchanged held-out test scores;
- report mean FPR, `CV(FPR)`, IQR, range, worst-client FPR, TPR, and P10 Macro-F1;
- report achieved benign exceedance against the target `1 - q`;
- visualize the policy-by-quantile surface.

Where Regime D supports the same calculation, repeat only the benign-FPR outcomes.

**Interpretation**

An ordering inversion is reported directly. The canonical `q = 0.95` is not changed after inspection.

**6.3 Controlled non-IID severity**

**Scientific role**

**Supportive heterogeneity analysis.**

**Question**

Does stronger client heterogeneity increase the operating-point advantage of local threshold calibration?

**Population and factors**

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

**Procedure**

For every seed and severity:

1. construct the partition using the locked seed and partition rule;
2. retain the pre-specified partition;
3. train or reuse the correct regime-specific model without cross-severity test selection;
4. compute B1, B2, and B4;
5. report heterogeneity diagnostics;
6. compute the B1–B2 `CV(FPR)` difference;
7. report uncertainty per alpha;
8. display seed distributions rather than only point estimates.

**Required heterogeneity diagnostics**

At minimum:

- client sample-count distribution;
- client benign-distribution divergence;
- class or attack composition when valid;
- eligible-client coverage;
- pairwise or aggregate Jensen–Shannon divergence.

**Interpretation**

A smooth monotone curve is not required. Low-alpha conditions may form one broad high-heterogeneity band. The result is associative and does not establish that the selected heterogeneity statistic causally determines DATP benefit.

---

### 7. Cluster and family mechanism programme

**7.1 Threshold-sharing granularity and cluster stability**

**Scientific role**

**Mechanism analysis.**

**Questions**

- Does family or cluster threshold sharing recover part of B2’s FPR-equity benefit?
- How much calibration granularity is required?
- Are B4 client assignments stable across seeds and calibration samples?
- Does cluster sharing provide a defensible middle ground between one global threshold and one threshold per client?

**Population**

- Regime A is mandatory;
- Regime D may include B4;
- B3 remains Regime A only.

**Comparison set**

- B1 shared;
- B3 family;
- B4 canonical `K = 3`;
- B2 local;
- exploratory B4 cluster counts where mathematically feasible.

**Procedure**

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

**Required outcomes**

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

**Interpretation**

**Useful middle ground**
B4 or B3 recovers a meaningful portion of B2’s equity improvement with stable groupings.

**Performance without stability**
B4 reduces dispersion, but assignments are unstable. The result is reported as fragile.

**Stable but unhelpful**
Clusters repeat, but do not improve the operating point.

**No cluster mechanism**
B4 is unstable and provides little recovery. B4 remains an explored negative mechanism result.

**7.3 Per-client score-distribution explanation**

**Scientific role**

**Mechanism analysis.**

**Question**

Why does B2 reduce FPR dispersion yet sometimes lower P10 Macro-F1?

**Procedure**

For all nine Regime A clients:

- plot held-out benign reconstruction-error CDFs;
- plot held-out attack reconstruction-error CDFs;
- overlay B1, B2, and B4 thresholds;
- show each threshold’s benign exceedance and attack acceptance region;
- identify clients with weak score separation;
- include the pre-specified Ennio Doorbell deep dive;
- retain all clients in supplementary panels.

**Required outcomes**

- one complete multi-client CDF figure;
- one detailed Ennio Doorbell panel;
- per-client threshold positions;
- per-client FPR, TPR, balanced accuracy, and Macro-F1;
- explanation of threshold movement without claiming causality beyond the plotted score geometry.

**7.4 Heterogeneity–benefit association**

**Scientific role**

**Mechanism association.**

**Question**

Does benign score-distribution heterogeneity predict the magnitude of the local-threshold benefit?

**Procedure**

For each valid regime/seed unit:

- calculate the locked Jensen–Shannon heterogeneity summary from benign score distributions;
- calculate the B1–B2 FPR-equity gain;
- plot both;
- report Spearman correlation;
- fit the pre-specified descriptive regression;
- report `R²`, uncertainty, leverage, and sensitivity to individual clients or regimes.

**Interpretation**

A strong relationship supports a heterogeneity-conditioned interpretation. A weak relationship is a real result and prevents using JS divergence as a sufficient predictor.

The analysis is associative, not causal.

**7.5 Threshold movement versus operating-point harm**

**Scientific role**

**Mechanism analysis.**

**Question**

How does the client-specific threshold shift from B1 to B2 relate to changes in false positives and attack detection?

**Procedure**

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

**Interpretation**

This experiment quantifies the equity–sensitivity trade-off surface. It does not claim that threshold movement alone explains every detection change.

---

### 8. Calibration robustness programme

**8.1 Calibration-size ablation**

**Scientific role**

**Boundary condition and threshold-variant support.**

**Question**

How much benign calibration data is required before local thresholds become stable?

**Calibration-size grid**

```text
n_k in {50, 100, 250, 500, 1000, 5000}
```

A size is evaluated only when the client has sufficient source calibration records.

**Repetition**

Each subsample size must use multiple deterministic subsampling replicates nested within each training seed. Subsampling replicates quantify calibration sampling variability; they are not counted as independent training seeds.

**Comparison set**

- B1;
- B2;
- B4;
- shrinkage overlay where defined;
- B2-conf where its finite-sample rule is valid.

**Procedure**

For every seed, client, size, and subsample replicate:

1. draw benign calibration records without replacement;
2. compute the declared thresholds;
3. evaluate on the unchanged held-out test set;
4. record threshold variance across subsamples;
5. record FPR target error;
6. record `CV(FPR)`, worst-client FPR, IQR, range, P10 Macro-F1, and balanced accuracy;
7. report clients unavailable at each size.

**Interpretation**

**Graceful degradation**
B2 remains stable as calibration shrinks.

**Shrinkage benefit**
Naive B2 destabilizes while shrinkage reduces variance without erasing most personalization.

**Sample-starved boundary**
Local thresholds become unreliable below a clear range.

**No sample-size effect**
Threshold stability changes little over the tested grid.

The result cannot be summarized using only the best-performing calibration size.

**8.2 Fixed local–global shrinkage**

**Scientific role**

**Supportive threshold variant.**

**Question**

Can partial pooling retain FPR equity while reducing local-threshold variance or detection loss?

**Factor**

```text
lambda in {0.00, 0.25, 0.50, 0.75, 1.00}
```

**Procedure**

Using the same Regime A scores:

- compute the shrinkage threshold for every eligible client;
- evaluate the full lambda curve;
- report `CV(FPR)`, worst-client FPR, IQR, range, TPR, P10 Macro-F1, and threshold variance;
- repeat within the calibration-size grid where planned;
- do not choose one lambda from the test set and present it as the method.

**Interpretation**

The full curve is the result.

A non-monotone response is reported. An intermediate lambda may be described as a useful empirical compromise only if its selection rule is explicitly exploratory or determined without test leakage.

**8.3 Calibration-size-aware shrinkage**

**Scientific role**

**Supportive extension of shrinkage.**

**Question**

Can personalization weight depend on available benign calibration size without using test outcomes?

**Requirements**

The function `lambda(n_k)` must be:

- specified before evaluation;
- monotone unless a scientific reason justifies otherwise;
- bounded in `[0, 1]`;
- identical across clients apart from `n_k`;
- compared with fixed-lambda curves;
- evaluated over the same calibration-size subsamples.

**Interpretation**

This is an engineering threshold variant, not a new statistical estimator claim.

**8.4 Split-conformal B2-conf diagnostic**

**Scientific role**

**Supportive response to the “equalized by construction” critique.**

**Question**

Does a finite-sample-adjusted local conformal quantile achieve the intended benign coverage on held-out data, and does cross-client FPR dispersion remain lower than under a shared threshold?

**Procedure**

For every eligible Regime A client and seed:

1. use only the declared benign calibration scores;
2. compute the finite-sample conformal quantile at `alpha = 0.05`;
3. evaluate benign coverage on held-out benign scores;
4. report coverage error per client and seed;
5. evaluate attack-sensitive metrics only on held-out attack scores;
6. compare B2-conf with B2 and B1;
7. report results at small calibration sizes where rank granularity is material.

**Required outcomes**

- target coverage;
- achieved marginal benign coverage;
- coverage error;
- per-client coverage distribution;
- `CV(FPR)`;
- threshold difference from B2;
- detection-quality controls;
- finite-sample discreteness diagnostics.

**Interpretation**

B2-conf can show that the threshold rule is evaluated through held-out coverage rather than assumed to equalize test FPR by construction.

It does not prove client-conditional validity under arbitrary non-IID shift. Exchangeability limitations must remain explicit.[^split-conformal][^fed-conformal-heterogeneity]

---

### 9. Federated threshold-estimation programme

**9.1 Benign summary-statistics comparator**

**Scientific role**

**Mandatory comparator stress test.**

**Question**

Does a matched benign-only federated summary-statistics threshold dominate, match, or underperform DATP’s shared and local threshold scopes?

**Population**

- Regime A is mandatory;
- Regime D is mandatory for benign-FPR outcomes when artifacts are available.

**Comparison set**

- B1;
- exact pooled benign quantile;
- sample-weighted shared construction;
- B2;
- `B-FedStatsBenign`.

**Matching rule**

The comparator’s target exceedance must be matched to:

```text
1 - q
```

It may not be tuned on attack labels or F1.

**Procedure**

1. compute the exact centralized benign reference;
2. compute every distributed construction from the same calibration records;
3. evaluate threshold-estimation error against the centralized reference;
4. evaluate achieved benign exceedance;
5. evaluate cross-client FPR dispersion;
6. report communication payload estimates separately from measured network cost;
7. calculate the locked between-ratio diagnostic where defined;
8. describe precisely which statistics leave each client.

**Required outcomes**

- threshold value;
- absolute and relative threshold error;
- target-attainment error;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- communication fields and estimated bytes;
- client coverage;
- comparison with B1 and B2.

**Interpretation**

`B-FedStatsBenign` may:

- improve over B1 but remain weaker than B2;
- match B2;
- dominate B2;
- fail to improve over B1.

Every outcome is reported. The result does not support a faithful Laridi claim because anomalous validation summaries are excluded.[^laridi]

**9.2 Federated quantile-estimation backbone**

**Scientific role**

**Optional high-value methods backbone.**

**Purpose**

Reframe threshold policies as estimators of a target quantile and make their approximation error auditable.

**Required constructions**

- exact pooled quantile;
- local quantiles;
- arithmetic mean of local quantiles;
- sample-weighted construction;
- quantile-of-quantiles where pre-specified;
- `B-FedStatsBenign`.

**Outcomes**

- quantile-estimation error;
- achieved benign exceedance;
- threshold variance;
- calibration sample efficiency;
- estimated communication;
- relation between estimation error and FPR equity.

No novel federated quantile estimator is claimed unless a genuinely new estimator and proof are developed outside the current roadmap.

**9.3 Fixed-coefficient Laridi sensitivity**

**Scientific role**

**Optional supplementary sensitivity only.**

Fixed coefficient values may be evaluated under the benign-only adaptation:

```text
k in {2.0, 2.5, 3.0}
```

This remains a sensitivity of `B-FedStatsBenign`; it must not be labelled `B-LaridiFaithful`.

---

### 10. External validation and applicability boundaries

**10.1 Edge-IIoTset external benign-equity validation**

**Scientific role**

**External validation.**

**Question**

Does the shared-versus-local threshold-scope effect appear on an independent sensor-group-partitioned IoT/IIoT dataset?

**Population**

- Regime D;
- ten benign sensor-group clients;
- eligible-benign coverage 1.0;
- ten paired seeds where training is feasible.

**Comparison set**

- B1;
- B2;
- B4 canonical;
- `B-FedStatsBenign`;
- quantile sensitivity;
- calibration-size and shrinkage analyses where supported.

B3 is omitted.

**Procedure**

1. train the FedAvg autoencoder per seed using benign training data;
2. construct the allowed thresholds;
3. evaluate per-client benign FPR;
4. compute cross-client equity metrics;
5. represent attack-sensitive per-client metrics as unavailable;
6. compare the direction and magnitude of B1–B2 with Regime A without treating the datasets as exchangeable replications.

**Required outcomes**

- eligible-benign coverage;
- per-client benign sample counts;
- B1/B2/B4/`B-FedStatsBenign` thresholds;
- per-client FPR;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- seed-level B1–B2 differences;
- BCa interval as external evidence;
- typed unavailability for attack-sensitive metrics;
- dataset-specific limitations.

**Interpretation**

**Consistent direction**
Supports external benign-equity validation.

**Weaker or null effect**
Defines a cross-dataset boundary.

**Opposite effect**
Narrows the generalization claim.

**Client assignment or eligibility failure**
Produces an infeasibility result; it cannot be repaired by inventing another partition after inspection.

**10.2 CICIoT2023 file-level boundary**

**Scientific role**

**Applicability boundary.**

**Question**

When the processed client partitions are near-homogeneous and file-defined, is threshold personalization unnecessary or unidentifiable?

**Procedure**

- quantify pairwise benign-distribution divergence;
- run B1 and B2 on the same scores;
- include B4 only if cluster sizes are meaningful;
- report `CV(FPR)`, IQR, range, and worst pseudo-client FPR;
- keep all wording specific to the available pseudo-clients.

**Interpretation**

A null result is not evidence that DATP fails on CICIoT2023’s original physical devices. It is evidence that the available file-defined pseudo-clients do not expose a strong threshold-scope need.

---

### 11. Training-side stress tests

**11.1 FedProx aggregation stress test**

**Scientific role**

**External aggregation-side stress test.**

**Question**

Does heterogeneity-aware training absorb the B1–B2 threshold-scope effect?

**Literature rationale**

FedProx was designed to address systems and statistical heterogeneity by adding a proximal term to local optimization and generalizing FedAvg.[^fedprox] Its inclusion tests whether better training alignment removes the need for post-training threshold personalization.

**Population**

- Regime A is mandatory;
- Regime D benign-equity outcomes are included after Regime D readiness.

**Factors**

- FedAvg reference;
- FedProx with frozen `mu` grid:
  - `0.001`;
  - `0.01`;
  - `0.1`;
  - `1.0`;
- B1, B2, B3 where valid, and B4.

**Coefficient-selection rule**

The primary FedProx coefficient must be selected using the pre-registered, non-test rule on Regime A. The test set, attack labels, `CV(FPR)` advantage, and Regime D outcomes cannot choose `mu`.

The complete grid remains reportable.

**Procedure**

1. train FedProx models independently from FedAvg;
2. apply the same checkpoint protocol;
3. produce separate score sets;
4. evaluate the complete threshold ladder on each trained model;
5. calculate the B1–B2 threshold-scope difference under FedAvg and FedProx;
6. compare convergence and model-quality controls;
7. report training failure or instability without changing the grid retroactively.

**Interpretation**

- retained threshold-scope effect;
- partial absorption;
- full absorption;
- opposite effect;
- FedProx non-convergence or instability.

FedProx results do not enter the core causal ladder.

**11.2 Ditto model-personalization stress test**

**Scientific role**

**External model-side personalization stress test.**

**Question**

Does maintaining a personalized model for each client make threshold personalization redundant?

**Literature rationale**

Ditto jointly maintains global and personalized models and was proposed as a general personalized federated-learning framework for statistically heterogeneous clients.[^ditto] It is used here because it can be applied without requiring a hand-defined shared representation/local head split.

**Population**

- Regime A is mandatory;
- Regime D is included for benign-equity outcomes after readiness.

**Primary comparison**

The interpretable 2-by-2 core is:

- FedAvg model with B1;
- FedAvg model with B2;
- Ditto personalized model with B1;
- Ditto personalized model with B2.

B3 and B4 may be applied as supplementary threshold scopes to the personalized scores.

**Procedure**

1. train genuine Ditto global and personalized states;
2. keep personalized states separate by client;
3. select personalization hyperparameters without attack-test or confirmatory leakage;
4. generate scores separately from the FedAvg artifacts;
5. compute B1 and B2 on the Ditto score distributions;
6. calculate the threshold-scope gain under FedAvg and under Ditto;
7. report model-quality, FPR-equity, compute, storage, and communication differences;
8. preserve all four core corners.

**Absorption measure**

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

**Scope boundary**

This is one stress test, not an exhaustive personalized-FL benchmark. APFL, Per-FedAvg, pFedMe, FedRep, FedPer, and broad architecture comparisons are not added to this paper.

---

### 12. Temporal recalibration experiment

**12.1 One-shot recalibration under genuine chronology**

**Scientific role**

**Temporal boundary condition.**

**Question**

When thresholds are calibrated on historical benign behavior, does future benign behavior increase cross-client FPR dispersion, and can one future benign recalibration window recover it?

**Population**

- Regime D-temporal;
- nine verified temporal groups;
- Modbus excluded;
- ten paired seeds where feasible.

**Compared states**

**Static reference**
Random-fractional split over the same nine groups, used to estimate ordinary sampling variation without chronology.

**Frozen future**
Thresholds fitted from historical calibration and applied unchanged to future evaluation.

**One-shot recalibrated future**
Thresholds recomputed once from the future recalibration window and applied to future evaluation.

**Policies**

- B1;
- B2;
- B4;
- shrinkage where pre-specified.

**Procedure**

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

**Required outcomes**

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

**Pre-specified interpretations**

**Temporal degradation with recovery**
Frozen future dispersion exceeds the static reference and one-shot recalibration recovers a meaningful portion.

**Temporal degradation without recovery**
Drift excess is positive, but one-shot recalibration provides little or negative recovery.

**No detectable temporal degradation**
Frozen future dispersion does not meaningfully exceed the static reference; recovery ratio remains undefined.

No outcome justifies claiming a complete concept-drift solution.

---

### 13. Operational translation

**13.1 Alert-burden experiment**

**Scientific role**

**Supportive operational interpretation.**

**Question**

What does a difference in FPR mean in approximate alerts per device per day?

**Required external input**

A real measured or appropriately cited benign traffic rate:

```text
benign decisions or flows per device per unit time
```

**Calculation**

For client \(k\):

\[
alerts_{k,\mathrm{day}}
=
FPR_k
\times
benign\_traffic\_rate_{k,\mathrm{day}}
\]

**Requirements**

- report the rate source;
- report whether the rate is measured, dataset-derived, or externally cited;
- propagate rate assumptions separately from model uncertainty;
- show per-device burden, not only a pooled total;
- use B1 and B2 at minimum;
- label estimates as estimated when no deployment measurement exists.

**Suppression rule**

When no real or cited rate is available, omit the metric. Do not invent a nominal rate merely to populate a table or figure.

---

### 14. Optional high-value analyses

These analyses are useful but cannot delay the mandatory programme unless a reviewer-critical gap remains.

**14.1 Robust cluster-median threshold**

Replace the mean of cluster-member local thresholds with a median and compare outlier sensitivity.

Report:

- cluster assignments unchanged;
- cluster threshold difference;
- `CV(FPR)`;
- worst-client FPR;
- outlier-client influence.

This remains supplementary.

**14.2 Additional equity indices**

Report, alongside rather than instead of `CV(FPR)`:

- Jain index;
- Gini coefficient;
- IQR;
- max–min range;
- within-cluster dispersion;
- across-cluster dispersion.

The primary endpoint remains unchanged.

**14.3 Extended secondary uncertainty**

Provide:

- bootstrap intervals for secondary paired metrics;
- Wilcoxon signed-rank;
- matched-pairs rank-biserial correlation;
- exact sign summaries where useful.

Multiplicity treatment must follow 04 — Evaluation and Reporting Protocol.

### 15. Research foundations

The papers below support specific design choices and literature positioning; they do not alter the locked causal claim.

[^nbaiot]: Y. Meidan et al., “N-BaIoT—Network-Based Detection of IoT Botnet Attacks Using Deep Autoencoders,” *IEEE Pervasive Computing*, 2018. DOI: [10.1109/MPRV.2018.03367731](https://doi.org/10.1109/MPRV.2018.03367731). Supports the use of nine physical N-BaIoT devices and the autoencoder anomaly-detection context.

[^edge-iiotset]: M. A. Ferrag et al., “Edge-IIoTset: A New Comprehensive Realistic Cyber Security Dataset of IoT and IIoT Applications for Centralized and Federated Learning,” *IEEE Access*, 2022. DOI: [10.1109/ACCESS.2022.3165809](https://doi.org/10.1109/ACCESS.2022.3165809). Supports Edge-IIoTset as an independent IoT/IIoT external dataset.

[^ciciot2023]: E. C. P. Neto et al., “CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment,” *Sensors*, 2023. DOI: [10.3390/s23135941](https://doi.org/10.3390/s23135941). Supports the original dataset context of 105 devices and 33 attacks; the available data do not retain a verified physical-device mapping.

[^fedprox]: T. Li et al., “Federated Optimization in Heterogeneous Networks,” *Proceedings of MLSys*, 2020. [Primary paper](https://arxiv.org/abs/1812.06127). Supports FedProx as a heterogeneity-oriented training stress test and not as a threshold policy.

[^ditto]: T. Li, S. Hu, A. Beirami, and V. Smith, “Ditto: Fair and Robust Federated Learning Through Personalization,” *Proceedings of ICML*, PMLR 139, 2021. [Primary paper](https://proceedings.mlr.press/v139/li21h.html). Supports the model-personalization stress-test design.

[^laridi]: S. Laridi, G. Palmer, and K.-M. M. Tam, “Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding,” *Scientific Reports*, 2024. DOI: [10.1038/s41598-024-76961-2](https://doi.org/10.1038/s41598-024-76961-2). The method aggregates summary statistics from normal and anomalous validation data; this motivates but is not equivalent to the benign-only `B-FedStatsBenign` comparator.

[^split-conformal]: J. Lei, M. G’Sell, A. Rinaldo, R. J. Tibshirani, and L. Wasserman, “Distribution-Free Predictive Inference for Regression,” *Journal of the American Statistical Association*, 2018. DOI: [10.1080/01621459.2017.1307116](https://doi.org/10.1080/01621459.2017.1307116). Supports finite-sample split-conformal rank correction under exchangeability.

[^fed-conformal-label-shift]: V. Plassier et al., “Conformal Prediction for Federated Uncertainty Quantification Under Label Shift,” *Proceedings of ICML*, PMLR 202, 2023. [Primary paper](https://proceedings.mlr.press/v202/plassier23a.html). Supports caution that federated distribution shift requires explicit treatment for conformal validity.

[^fed-conformal-heterogeneity]: V. Plassier et al., “Efficient Conformal Prediction under Data Heterogeneity,” *Proceedings of AISTATS*, PMLR 238, 2024. [Primary paper](https://proceedings.mlr.press/v238/plassier24a.html). Supports treating agent heterogeneity and non-exchangeability as substantive conformal-prediction issues.

[^ari]: L. Hubert and P. Arabie, “Comparing Partitions,” *Journal of Classification*, 1985. DOI: [10.1007/BF01908075](https://doi.org/10.1007/BF01908075). Supports adjusted Rand index for chance-adjusted comparison of cluster assignments.

## Evaluation, statistical analysis, and reporting

**Purpose**

This file defines how DATP-Core results are calculated, aggregated, compared, and reported.

---

### 1. Evaluation contract

**1.1 Fixed-score comparison**

Within B1–B4, every policy uses the same:

- selected model state;
- preprocessing and normalization procedure;
- client identities;
- calibration and test splits;
- eligibility decisions;
- metric implementation.

Only thresholds may change.

**1.2 Independent unit**

The training seed is the independent replication unit.

Clients, rows, checkpoints, attack categories, calibration subsamples, cluster initializations, and temporal windows are not independent replications.

Nested replicates are summarized within seed before across-seed inference.

**1.3 Per-client-first reporting**

Metrics are calculated per client before cross-client aggregation whenever valid client identity exists.

Pooled-row metrics may be reported as controls but cannot replace client-level operating-point metrics.

---

### 2. Prediction and confusion counts

For score \(e\) and threshold \(\tau\):

\[
\widehat{y}
=
\begin{cases}
\text{attack}, & e > \tau \\
\text{benign}, & e \leq \tau
\end{cases}
\]

The comparison operator is fixed across policies.

For client \(k\):

- \(TN_k\): benign predicted benign;
- \(FP_k\): benign predicted attack;
- \(TP_k\): attack predicted attack;
- \(FN_k\): attack predicted benign.

All counts come from held-out test rows. Calibration rows never enter reported test metrics.

A higher reconstruction error must always indicate greater anomaly evidence.

---

### 3. Metric populations

**3.1 Calibration eligibility**

A client is primary-analysis eligible when:

```text
benign_calibration_count >= 100
```

Eligibility is determined before test evaluation and remains identical across policies in the same comparison.

**3.2 FPR-evaluable population**

A client additionally requires a non-empty benign test denominator.

**3.3 Attack-evaluable population**

Attack-sensitive metrics additionally require:

- valid per-client attack assignment;
- at least one held-out attack row;
- both semantic classes where required.

A client may be FPR-evaluable but unavailable for TPR, balanced accuracy, Macro-F1, or AUROC.

This distinction is mandatory for Edge-IIoTset.

**3.4 Coverage**

\[
coverage
=
\frac{K_{\mathrm{eligible}}}{K_{\mathrm{candidate}}}
\]

Report candidate, eligible, attack-evaluable, fallback, and excluded client counts, with an exclusion reason per client.

Ineligible fallback clients do not enter the primary `CV(FPR)` calculation.

---

### 4. Per-client metrics

**4.1 False-positive rate**

\[
FPR_k
=
\frac{FP_k}{FP_k + TN_k}
\]

Unavailable when the benign denominator is zero.

**4.2 True-positive rate**

\[
TPR_k
=
\frac{TP_k}{TP_k + FN_k}
\]

Unavailable when the attack denominator is zero or client-level attack assignment is invalid.

**4.3 Balanced accuracy**

\[
BA_k
=
\frac{TPR_k + (1-FPR_k)}{2}
\]

Unavailable unless both FPR and TPR are available.

**4.4 Per-client Macro-F1**

Calculate benign-class and attack-class F1 separately, then:

\[
MacroF1_k
=
\frac{
F1_{k,\mathrm{benign}}
+
F1_{k,\mathrm{attack}}
}{2}
\]

Macro-F1 is unavailable when a required class or denominator is absent.

Do not silently convert undefined class metrics to zero.

**4.5 AUROC**

AUROC uses continuous anomaly scores and requires both classes.

Within a fixed-score B1–B4 comparison, AUROC must be identical up to numerical tolerance. Any policy-dependent difference indicates mismatched scores or unintended model variation.

AUROC is a model-quality control, not a threshold-policy verdict.

---

### 5. Cross-client operating-point metrics

Let \(K_e\) be the eligible FPR-evaluable client count.

**5.1 Mean FPR**

\[
\mu_{FPR}
=
\frac{1}{K_e}
\sum_{k=1}^{K_e} FPR_k
\]

The primary equity calculation is unweighted by client row count.

**5.2 Population standard deviation**

\[
\sigma_{FPR}
=
\sqrt{
\frac{1}{K_e}
\sum_{k=1}^{K_e}
(FPR_k-\mu_{FPR})^2
}
\]

Use:

```text
ddof = 0
```

The executed clients are the complete descriptive population for that cell.

**5.3 Coefficient of variation**

\[
CV(FPR)
=
\frac{\sigma_{FPR}}{\mu_{FPR}}
\]

No epsilon or denominator stabilizer is permitted.

When `mean(FPR) = 0`:

```text
CV(FPR) = undefined
```

When the mean is positive but very close to zero, retain the numerical CV only with a near-zero-denominator warning.

Such cells are interpreted only alongside absolute dispersion.

**5.4 Absolute dispersion**

\[
IQR(FPR)
=
Q_{0.75}(FPR)-Q_{0.25}(FPR)
\]

\[
Range(FPR)
=
\max(FPR_k)-\min(FPR_k)
\]

\[
WorstFPR
=
\max(FPR_k)
\]

**5.5 TPR and lower-tail metrics**

Where attack evaluation is valid:

\[
CV(TPR)
=
\frac{\operatorname{std}(TPR_k,ddof=0)}
{\operatorname{mean}(TPR_k)}
\]

The same zero-denominator rules apply.

\[
P10(MacroF1)
=
Q_{0.10}(MacroF1_k)
\]

\[
WorstBA
=
\min(BA_k)
\]

Report the number of attack-evaluable clients with each aggregate.

---

### 6. Optional equity metrics

Optional metrics accompany `CV(FPR)` and never replace it.

**6.1 Jain index**

\[
Jain(FPR)
=
\frac{
(\sum_k FPR_k)^2
}{
K_e\sum_k FPR_k^2
}
\]

Undefined when all FPR values are zero.

**6.2 Gini coefficient**

\[
Gini(FPR)
=
\frac{
\sum_i\sum_j|FPR_i-FPR_j|
}{
2K_e\sum_iFPR_i
}
\]

Undefined when the FPR sum is zero.

**6.3 Cluster dispersion**

For B4, report:

- cluster size;
- within-cluster threshold spread;
- within-cluster FPR spread;
- across-cluster threshold spread;
- across-cluster mean-FPR spread;
- singleton and empty-cluster status.

Do not conflate these quantities.

---

### 7. Aggregate model-quality controls

**7.1 Mean client Macro-F1**

\[
MeanClientMacroF1
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} MacroF1_k
\]

where \(K_a\) is the attack-evaluable client count.

**7.2 Pooled Macro-F1**

Pooled Macro-F1 may be reported from pooled confusion counts but must be labeled separately.

It cannot replace:

- mean client Macro-F1;
- P10 Macro-F1;
- worst-client balanced accuracy.

**7.3 Mean client balanced accuracy**

\[
MeanClientBA
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} BA_k
\]

Always report the worst-client value alongside it.

---

### 8. Threshold-estimation metrics

**8.1 Centralized oracle**

When defined by the experiment, the exact pooled benign quantile is the centralized threshold reference.

The quantile probability and interpolation method must match the distributed estimators.

**8.2 Threshold error**

\[
AbsoluteThresholdError
=
|\tau-\tau_{\mathrm{oracle}}|
\]

\[
RelativeThresholdError
=
\frac{
|\tau-\tau_{\mathrm{oracle}}|
}{
|\tau_{\mathrm{oracle}}|
}
\]

Relative error is undefined when the oracle threshold is zero.

**8.3 Target attainment**

For target quantile \(q\):

\[
TargetExceedance = 1-q
\]

\[
SignedAttainmentError
=
AchievedBenignExceedance-(1-q)
\]

\[
AbsoluteAttainmentError
=
|SignedAttainmentError|
\]

Report both signed and absolute error.

**8.4 Threshold variance and sample efficiency**

For calibration-size studies, calculate threshold variation across declared subsampling replicates within client and seed.

The complete calibration-size curve is reported using:

- threshold variance;
- attainment error;
- `CV(FPR)`;
- worst-client FPR;
- P10 Macro-F1 where available.

Subsampling replicates do not increase the seed count.

---

### 9. `B-FedStatsBenign` diagnostics

For eligible client \(k\), the comparator uses benign-only:

- count \(n_k\);
- mean \(\mu_k\);
- variance \(\sigma_k^2\);
- permitted benign exceedance counts.

**9.1 Global mean**

\[
\mu_{global}
=
\frac{
\sum_k n_k\mu_k
}{
\sum_k n_k
}
\]

**9.2 Full pooled variance**

\[
within
=
\frac{
\sum_k n_k\sigma_k^2
}{
\sum_k n_k
}
\]

\[
between
=
\frac{
\sum_k n_k(\mu_k-\mu_{global})^2
}{
\sum_k n_k
}
\]

\[
\sigma^2_{global}=within+between
\]

The between-client mean-shift term must not be omitted.

**9.3 Between ratio**

\[
between\_ratio
=
\frac{between}{within+between}
\]

Undefined when the denominator is zero.

Report `within`, `between`, pooled variance, and `between_ratio`.

---

### 10. Operational metrics

**10.1 Alert burden**

When a measured or appropriately cited benign decision rate exists:

\[
Alerts_{k,day}
=
FPR_k
\times
BenignDecisions_{k,day}
\]

Report the rate source and whether it is measured, dataset-derived, or externally cited.

When no defensible rate exists, omit alert burden.

### 11. Confirmatory statistical analysis

**11.1 Paired contrast**

For seed \(s\):

\[
\Delta_s
=
CV(FPR)_{B1,s}
-
CV(FPR)_{B2,s}
\]

The confirmatory point estimate is the arithmetic mean:

\[
\overline{\Delta}
=
\frac{1}{10}
\sum_{s=1}^{10}\Delta_s
\]

B1 and B2 are never resampled independently.

**11.2 BCa confidence interval**

The confirmatory interval is a two-sided 95% BCa bootstrap interval over the ten paired seed-level deltas.

The interval resamples paired seed deltas with replacement, uses the arithmetic mean as its statistic, and calculates bias correction and acceleration from the paired seed data.

**11.3 Degenerate BCa**

If BCa is undefined or unstable because of identical deltas, invalid acceleration, a degenerate bootstrap distribution, or fewer than ten valid pairs:

- report the paired values and point estimate;
- allow percentile or basic intervals only as diagnostics;
- do not silently substitute another interval for the confirmatory rule.

**11.4 Sign consistency**

\[
SignConsistency
=
\frac{
|\{s:\Delta_s>0\}|
}{
10
}
\]

Also report zero and negative counts.

This is descriptive only.

---

### 12. Secondary statistical evidence

**12.1 Wilcoxon signed-rank**

Use paired seed-level values with:

- two-sided alternative;
- explicit zero-difference handling;
- exact computation when data and implementation permit;
- recorded approximation or permutation method otherwise.

The p-value does not determine the confirmatory verdict.

**12.2 Matched-pairs rank-biserial correlation**

Use matched-pairs rank-biserial correlation as the paired nonparametric effect size.

Do not use unpaired Cliff’s delta for the seed-paired comparison.

Report method, sign, magnitude, and non-zero pair count.

**12.3 Secondary confidence intervals**

Secondary BCa intervals may be reported for pre-specified seed-level contrasts, but remain secondary.

**12.4 Multiplicity**

The single confirmatory endpoint receives no multiplicity correction.

When secondary p-values are emphasized:

- define test families before analysis;
- report family size;
- apply Holm correction within each family;
- retain raw values only as clearly labeled diagnostics.

Exploratory analyses may remain descriptive.

**12.5 Nested replicates**

For calibration subsamples, cluster restarts, or similar nested repetitions:

1. calculate replicate-level values;
2. summarize them within seed;
3. produce one seed-level estimate per condition;
4. perform across-seed inference on those seed-level estimates.

**12.6 Association analyses**

For heterogeneity–benefit analyses, report:

- Spearman correlation;
- declared regression;
- coefficient and uncertainty;
- `R²`;
- influence diagnostics;
- all observations.

Use associative, not causal, language.

**12.7 Cluster stability**

Adjusted Rand index is descriptive and must be accompanied by memberships, cluster sizes, empty clusters, and singleton clusters.

---

### 13. Checkpoint protocol

**13.1 Anchor checkpoint**

The conference anchor preserves its historical endpoint and checkpoint semantics; it is not retrofitted with journal checkpoint selection merely to improve reproduction.

**13.2 Primary journal round**

Regime A selects one primary **round number** using a non-test rule specified before journal outcomes are inspected.

**Locked non-test rule (`FIXED_TERMINAL_MAXIMUM_ROUND`, prospective research amendment).** Among the declared candidates, the primary checkpoint is the candidate at the declared maximum round (`200`). No metric, label, score artifact, threshold outcome, or cross-policy contrast may enter selection. Non-terminal retained candidates are stability evidence only. The same primary **round number** is applied consistently across main regimes and policies where the checkpoint exists; model weights remain seed-, population-, and model-specific. The independent centralized reference (B0) applies the same rule to its own candidate set and never consumes federated checkpoints. Historical early-stopping practice is superseded by this fixed-budget protocol.

**13.3 Forbidden selectors**

The round cannot be chosen using:

- test AUROC;
- test FPR or `CV(FPR)`;
- Macro-F1 or balanced accuracy;
- attack labels;
- the B1-versus-B2 effect;
- external or stress-test results;
- policy-specific best performance.

### 14. Temporal recalibration quantities

For each seed and policy, report:

- `static_reference_cv`;
- `frozen_future_cv`;
- `recalibrated_future_cv`.

\[
drift\_excess
=
frozen\_future\_cv-static\_reference\_cv
\]

\[
recovered\_amount
=
frozen\_future\_cv-recalibrated\_future\_cv
\]

\[
recovery\_ratio
=
\frac{
recovered\_amount
}{
drift\_excess
}
\]

`recovery_ratio` is computed only when `drift_excess` satisfies a positive-materiality threshold specified before analysis.

Otherwise:

```text
recovery_ratio = undefined
```

Temporal BCa analysis resamples paired seed records, not rows or windows.

Undefined or unavailable metrics must be reported with their reason; do not substitute zero, an empty value, or an unqualified `NaN`.

---

### 15. Precision and selection discipline

Calculations use full available precision. Rounding occurs only for presentation.

Recommended presentation:

- rates and aggregate metrics: three decimals;
- confidence intervals and effect sizes: three decimals;
- p-values: three significant digits, with `< 0.001` when appropriate;
- counts: integers;
- thresholds: enough digits to reproduce decisions.

Never round before computing contrasts or intervals.

Do not choose checkpoints, policies, or parameter values from test outcomes, remove unfavorable seeds or clients, convert undefined metrics to zero, or hide material null or contrary results.
