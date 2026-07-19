# 01 — Scientific Identity and Scope

## Document status

This document is the canonical scientific contract for DATP-Core.

It defines the stable identity of the journal extension, the boundaries that cannot change after results are observed, the meaning of every threshold-policy family, and the distinction between the controlled DATP experiment and the external stress tests that surround it.

It is intentionally written as a readable scientific specification rather than as a numbered rule register. The absence of opaque scope codes does not weaken the constraints: every boundary in this document is mandatory unless the master roadmap is formally revised before the affected results are examined.

---

# 1. Responsibility and precedence

## 1.1 What this document owns

This file owns:

- the scientific identity of DATP-Core;
- the causal object of study;
- the fixed-model and benign-calibration invariants;
- the meaning of operational false-positive-rate equity;
- the canonical names and roles of threshold policies, threshold variants, comparators, and training-side stress tests;
- the boundary between the controlled threshold ladder and all external comparisons;
- included and excluded scientific scope;
- dataset- and regime-level identity restrictions;
- originality and conference-to-journal extension boundaries;
- venue-level submission constraints;
- language that is permitted or prohibited at the scope level;
- the change-control process for modifying the scientific programme.

## 1.2 What this document does not own

This file does not define:

- whether a claim survives a statistical test;
- weak, mixed, null, or opposite-result manuscript wording;
- complete experiment procedures;
- metric formulas or statistical implementation;
- software classes, modules, APIs, schemas, or repository structure;
- execution status;
- audit history.

Those responsibilities belong to:

- [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md);
- [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md);
- [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md);
- [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md);
- [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md);
- [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md).

## 1.3 Precedence

When roadmap files appear to conflict, use this order:

1. explicit locked scientific identity in this file;
2. explicit claim-decision rules in `02_CLAIMS_AND_DECISION_RULES.md`;
3. experiment definitions in `03_EXPERIMENT_CATALOGUE.md`;
4. metric and reporting rules in `04_EVALUATION_AND_REPORTING_PROTOCOL.md`;
5. implementation requirements in `05_IMPLEMENTATION_ROADMAP.md`;
6. reviewer-readiness material and historical audits.

An implementation detail cannot override a scientific invariant.

A reporting convenience cannot alter an experiment.

A favorable result cannot retroactively change the scope, metric, policy definition, client population, checkpoint, or comparator.

---

# 2. Programme identity

## 2.1 Working title

*Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.*

The parenthetical phrase *journal extension* may be used in planning documents and submission disclosures, but it is not part of the scientific method name.

## 2.2 DATP-Core in one paragraph

DATP-Core is a controlled study of **threshold-calibration scope** in federated IoT anomaly detection.

For each seed and dataset regime, a federated autoencoder is trained and selected under one locked training protocol. The selected detector is then frozen. The same per-client calibration and test scores are reused across the core threshold ladder. The ladder changes only the scope at which a benign anomaly threshold is estimated: one shared threshold, one threshold per physical-device family, one threshold per data-driven client cluster, or one threshold per client.

The scientific question is therefore not:

> Which model or federated-learning algorithm is best?

It is:

> When heterogeneous IoT clients share one frozen federated anomaly detector, how does the scope of benign threshold calibration affect the distribution of false-alarm burden across clients?

The primary object of interest is cross-client false-positive-rate dispersion. Model discrimination, including AUROC, remains a control rather than the thresholding verdict.

---

# 3. Core causal contract

## 3.1 Unit of causal comparison

The controlled comparison is performed within a seed, regime, and frozen detector.

The core threshold policies must receive:

- the same selected autoencoder state;
- the same preprocessing state;
- the same client identities;
- the same split manifests;
- the same benign calibration records;
- the same held-out test scores;
- the same held-out test labels;
- the same eligibility rule;
- the same quantile target unless a declared quantile-sensitivity experiment changes it;
- the same metric implementation.

Only threshold-calibration scope may differ.

## 3.2 Fixed elements

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
- score-generation implementation;
- client eligibility;
- test population;
- metric definitions.

The fixed-detector rule applies **within each regime and training baseline**. It does not mean that the same numerical model parameters are reused across different datasets with incompatible feature spaces.

## 3.3 Sole manipulated variable

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

## 3.4 Prohibited causal contamination

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

# 4. Calibration and evaluation contract

## 4.1 Benign-only calibration

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

## 4.2 Separation of calibration and evaluation

Calibration records and evaluation records must be disjoint.

For temporal experiments:

- historical calibration must precede future recalibration;
- future recalibration must precede future evaluation;
- future evaluation cannot influence any earlier stage;
- file order, merge order, or generated pseudo-time cannot replace real chronology.

## 4.3 Client eligibility

The canonical minimum benign calibration support is:

```text
n_k >= 100
```

Only eligible clients enter the primary cross-client false-positive dispersion calculation.

Eligibility is determined before test evaluation and is identical across policies compared within the same experiment.

An ineligible client may receive a separately declared deployment fallback only when the experiment explicitly studies fallback behavior. It cannot be silently included in the confirmatory population.

## 4.4 Meaning of “fairness”

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

## 4.5 Primary operating-point concern

The primary concern is:

```text
CV(FPR) across eligible clients
```

Absolute dispersion measures accompany it when mean FPR is small.

The confirmatory endpoint and its decision rule belong to `02_CLAIMS_AND_DECISION_RULES.md`.

## 4.6 Model-quality controls

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

# 5. Threshold-policy system

## 5.1 Centralized reference: B0

B0 is the privacy-incompatible centralized reference.

It uses:

- a centralized autoencoder trained on pooled benign training data;
- a pooled benign calibration threshold;
- separate centralized provenance.

B0 is not part of the federated threshold-scope ladder.

A FedAvg model evaluated with a pooled threshold is not B0.

B0 exists to provide context for the cost of federation, not to participate in the confirmatory claim.

## 5.2 Shared threshold: B1

B1 is the shared-scope anchor.

Each eligible client computes its local benign quantile. The server calculates one shared threshold as the arithmetic mean of the eligible local quantiles.

At the canonical operating point:

```text
q = 0.95
```

Every eligible client uses the same resulting threshold.

B1 is not the exact pooled quantile and must not be described as such.

## 5.3 Local threshold: B2

B2 is the client-local scope anchor.

Each eligible client deploys its own benign calibration quantile at the same canonical target:

```text
q = 0.95
```

B2 is the comparator in the sole confirmatory B1-versus-B2 endpoint.

B2 is not assumed to dominate every policy on every metric. It may reduce FPR dispersion while increasing missed detections or weakening lower-tail classification performance for specific clients.

## 5.4 Family threshold: B3

B3 assigns one threshold to each validated physical-device family.

The threshold is formed from the eligible local thresholds belonging to that family.

B3 is permitted only when:

- a defensible family taxonomy exists;
- the taxonomy is defined independently of test outcomes;
- family membership is stable and auditable;
- the taxonomy represents device identity rather than attack labels.

B3 is a mechanism baseline.

It is available for the N-BaIoT physical-device regime and unavailable in regimes without a defensible family taxonomy.

## 5.5 Cluster threshold: B4

B4 is the taxonomy-free grouped-threshold mechanism.

Each eligible client is represented by the locked benign reconstruction-error fingerprint:

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

## 5.6 Ladder interpretation

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

# 6. Supportive threshold variants

Threshold variants preserve the fixed detector but alter the threshold estimator.

They remain outside the B1–B4 identity and cannot become confirmatory after results are observed.

## 6.1 Quantile sensitivity

The canonical quantile remains:

```text
q = 0.95
```

A pre-specified sensitivity grid tests whether conclusions depend on that choice.

An alternative quantile cannot replace the canonical endpoint post hoc.

## 6.2 Local–global shrinkage

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

## 6.3 Calibration-size-aware shrinkage

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

## 6.4 Split-conformal local threshold: B2-conf

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

# 7. Federated threshold comparator

## 7.1 `B-FedStatsBenign`

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

## 7.2 Relationship to Laridi et al.

Laridi et al. proposed a federated autoencoder threshold based on aggregated summary statistics from both normal and anomalous validation data.[^laridi]

DATP’s comparator deliberately excludes anomalous calibration information.

Therefore:

- `B-FedStatsBenign` is not a faithful Laridi reproduction;
- it must not be called `B-LaridiFaithful`;
- its results cannot be used to claim reproduction of Laridi et al.;
- the difference in calibration contracts must be disclosed in related work and limitations.

The reserved name `B-LaridiFaithful` refers only to a genuinely anomaly-informed implementation, which is out of scope for DATP-Core.

---

# 8. Training-side stress tests

Training-side stress tests change the detector and therefore cannot share the causal interpretation of the B1–B4 ladder.

They require separate models, scores, provenance, and reporting.

## 8.1 FedProx

FedProx is the aggregation-side heterogeneity stress test.

FedProx modifies local optimization with a proximal term intended to limit divergence from the current global model under heterogeneous federated data.[^fedprox]

Its purpose in DATP-Core is to ask:

> Does a heterogeneity-aware training algorithm absorb the operating-point benefit of threshold personalization?

FedProx results must be described as a training-side sensitivity.

They cannot be merged with the FedAvg confirmatory endpoint.

## 8.2 Ditto

Ditto is the planned model-personalization stress test.

Ditto maintains global and persistent client-personalized models regularized toward the global state.[^ditto]

The name *Ditto* may be used only when the implementation preserves genuine Ditto semantics, including:

- a distinct global model;
- persistent client-personalized states;
- the correct proximal personalized objective;
- no aggregation of personalized states as if they were global;
- separate evaluation provenance.

The purpose is to ask:

> Does model personalization make threshold personalization redundant, complementary, or partially absorbed?

The in-paper comparison remains one personalized-model family, not a broad personalized-FL benchmark.

## 8.3 Fallback naming

When genuine Ditto cannot be implemented without violating the locked model contract, the alternative must be named according to the algorithm actually implemented, such as:

```text
FedRep-AE
FedPer-AE
```

A fallback must never be called Ditto.

A fallback changes the scientific comparator and must be recorded before its results are used.

## 8.4 Separation from the core ladder

For every stress-test model:

- B1, B2, B3, and B4 may be recomputed on that model’s score artifacts;
- the model’s threshold-scope difference may be compared with the FedAvg difference;
- the result may support retention, partial absorption, or full absorption;
- the result cannot alter the identity of the FedAvg core ladder.

---

# 9. Evidence architecture

## 9.1 Sole confirmatory evidence

Only one endpoint is confirmatory:

- N-BaIoT physical-device regime;
- B1 versus B2;
- `CV(FPR)`;
- ten paired seeds;
- locked BCa decision rule.

Its exact survival rule belongs to `02_CLAIMS_AND_DECISION_RULES.md`.

## 9.2 Supporting evidence families

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
- suppression evidence;
- future work.

A supportive analysis cannot be promoted to rescue a failed confirmatory endpoint.

An external dataset cannot silently become a second confirmatory regime.

An exploratory result cannot be rewritten as pre-specified evidence after it is observed.

## 9.3 Honest negative evidence

The following are scientifically meaningful outcomes:

- B2 reduces FPR dispersion but harms P10 Macro-F1;
- B3 provides negligible recovery;
- B4 is unstable;
- shared constructions match B2;
- small calibration windows destabilize local thresholds;
- conformal coverage misses its target;
- FedProx absorbs the threshold effect;
- Ditto absorbs the threshold effect;
- Edge-IIoTset produces a null or opposite direction;
- CICIoT2023 file-defined clients are too homogeneous;
- one-shot recalibration fails;
- a planned regime is infeasible because the required metadata do not exist.

None may be hidden or replaced by a more favorable analysis.

---

# 10. Dataset and regime boundaries

Detailed regime procedures belong to [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md#4-experimental-regimes). This section fixes only the identity-level boundaries.

## 10.1 N-BaIoT physical-device anchor

N-BaIoT is the confirmatory dataset anchor.

The original dataset study evaluated nine commercial IoT devices infected with Mirai and BASHLITE using deep autoencoder anomaly detection.[^nbaiot]

For DATP-Core:

- the nine physical devices are the natural clients;
- this is the only confirmatory client population;
- the device-family taxonomy may support B3;
- all nine clients remain visible in mechanism reporting;
- the small client count is an explicit limitation.

## 10.2 CICIoT2023 file-defined boundary

The original CICIoT2023 publication describes a large IoT environment with 105 devices and 33 attacks.[^ciciot2023]

The available processed DATP artifact does not retain a verified physical-device mapping.

Therefore:

- file-defined pseudo-clients may be used only as an artifact-specific applicability boundary;
- a null result cannot be generalized to the original 105-device topology;
- source-paper device counts cannot be substituted for missing artifact metadata;
- device-aware wording is prohibited for this regime.

## 10.3 Rejected CICIoT2023 physical-device repartition

The intended device- or MAC-based repartition is suppressed because the required identifying metadata are absent.

Forbidden substitutes include:

- row order;
- file merge order;
- folder order;
- class labels;
- random pseudo-device assignment;
- inferred timestamps;
- undocumented filename assumptions.

The experiment may be reopened only if a verified artifact containing genuine client identity becomes available and passes a new feasibility audit before result inspection.

## 10.4 Controlled heterogeneity regime

The Dirichlet N-BaIoT regime is a controlled sensitivity experiment.

It does not replace natural device partitioning.

It may support a graded heterogeneity interpretation but cannot establish that one scalar non-IID parameter reproduces real device heterogeneity.

## 10.5 Edge-IIoTset external validation

Edge-IIoTset is the sole new external dataset.[^edge-iiotset]

Its client definition is established through first-principles artifact audit, not by copying a partition from another paper.

The audited external scope is benign operating-point equity.

Where attack traffic cannot be validly assigned to each client:

- per-client TPR is unavailable;
- per-client Macro-F1 is unavailable;
- per-client balanced accuracy is unavailable;
- per-client AUROC is unavailable;
- attack-sensitive cross-client equity is unavailable.

These outcomes must be represented as unavailable rather than estimated, inherited from another partition, or fabricated.

B3 is omitted when no defensible external family taxonomy exists.

## 10.6 Temporal external regime

The temporal experiment is limited to one-shot threshold recalibration on a verified chronological Edge-IIoTset population.

It does not establish:

- continuous adaptation;
- online learning;
- streaming drift detection;
- drift-triggered recalibration;
- concept-drift resolution;
- production stability over repeated cycles.

CICIoT2023 temporal probing remains suppressed when valid timestamps are absent.

## 10.7 Dataset expansion limit

DATP-Core adds no external IoT dataset beyond Edge-IIoTset.

Adding another dataset requires a formal roadmap revision before implementation or result inspection.

This limit prevents the paper from becoming a generic multi-dataset FL-IDS benchmark.

---

# 11. Included scientific scope

DATP-Core strengthens the original DATP study along five bounded directions.

## 11.1 External validation

One external IoT/IIoT dataset tests whether benign false-alarm equity effects transfer beyond N-BaIoT.

## 11.2 Federated threshold comparison

One benign-only summary-statistics comparator tests whether threshold personalization is dominated by a distributed shared-threshold alternative.

## 11.3 Training-side robustness

Two external stress tests examine:

- heterogeneity-aware federated optimization;
- client model personalization.

They remain outside the causal ladder.

## 11.4 Threshold-estimation depth

The threshold story is extended through:

- quantile-level sensitivity;
- local–global shrinkage;
- calibration-size-aware shrinkage;
- a bounded split-conformal local-threshold diagnostic.

## 11.5 Temporal boundary

One chronological, one-shot recalibration experiment tests whether frozen thresholds age and whether a single future benign calibration window recovers operating-point equity.

## 11.6 Mechanism analysis

The journal extension includes bounded mechanism work covering:

- family and cluster granularity;
- cluster stability;
- cluster-fingerprint sensitivity;
- per-client benign and attack score geometry;
- heterogeneity–benefit association;
- threshold movement versus FPR/TPR trade-off.

These analyses explain the result but do not create additional confirmatory claims.

## 11.7 Hard scope limits

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

Expansion beyond these limits requires formal pre-result change control.

---

# 12. Excluded scientific scope

## 12.1 Security attacks and defenses

DATP-Core does not study:

- calibration poisoning;
- training-data poisoning;
- model poisoning;
- aggregation attacks;
- Byzantine clients;
- backdoors;
- inference-time evasion;
- adversarial examples;
- robust aggregation defenses.

Calibration-channel poisoning belongs to DATP-CP.

## 12.2 Formal privacy

DATP-Core does not implement or claim:

- differential privacy;
- secure aggregation;
- homomorphic encryption;
- secure multiparty computation;
- membership-inference resistance;
- reconstruction resistance;
- formal privacy budgets.

Keeping raw data local is a structural property of FL, not a formal privacy guarantee.

B4 clustering is not a privacy mechanism.

Threshold-message size is not a privacy proof.

## 12.3 Deployment validation

DATP-Core does not provide:

- Raspberry Pi or embedded-device benchmarks;
- inference latency measurements;
- training energy measurements;
- battery impact;
- real-network bandwidth measurements;
- production alert-operations validation;
- hardware suitability claims.

Communication and storage may be estimated from serialized message sizes. Such estimates must not be called deployment measurements.

## 12.4 Fleet scale

The paper does not claim fleet-scale validation above 100 clients.

Synthetic client counts or file-defined pseudo-clients do not establish real fleet-scale deployment.

## 12.5 Full drift handling

The temporal experiment does not include:

- Page–Hinkley;
- FLARE;
- FLAME;
- adaptive conformal inference;
- repeated online recalibration;
- streaming windows;
- autonomous drift detection.

These belong to Dynamic DATP or later work.

## 12.6 Broad FL benchmarking

The study is not an exhaustive comparison of:

- federated optimizers;
- personalized-FL methods;
- clustering algorithms;
- anomaly-detector architectures;
- privacy mechanisms;
- intrusion-detection models.

FedBN is excluded because introducing BatchNorm would change the locked autoencoder architecture and therefore the scientific object.

## 12.7 Federated conformal breadth

The bounded B2-conf diagnostic does not expand into:

- global federated conformal benchmarking;
- weighted conformal method development;
- adversarial conformal prediction;
- online conformal adaptation;
- a claim of being the first federated conformal method.

Lu et al. and Humbert et al. are primary prior-art anchors for federated conformal prediction.[^lu-fcp][^humbert-fcp]

---

# 13. Terminology and naming rules

## 13.1 Project naming

Use:

```text
DATP
```

for the original method and conference identity.

Use:

```text
DATP-Core
```

for the journal-extension project and implementation.

Use:

```text
anchor
```

for the conference-faithful reference protocol inside DATP-Core.

Avoid using *journal* as a runtime object, model name, experiment identifier, or scientific method name.

## 13.2 Threshold-policy names

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

## 13.3 Threshold-variant names

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

## 13.4 Laridi naming

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

## 13.5 Personalized-model naming

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

## 13.6 Regime names

Regime identifiers remain:

```text
Regime A
Regime B-a
Regime B-b
Regime C
Regime D
Regime D-temporal
```

They refer to scientific dataset/population contracts, not arbitrary configuration shortcuts.

Every mention must include a descriptive phrase at first use, such as:

```text
Regime A — N-BaIoT physical-device anchor
```

## 13.7 Statistical and equity language

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

## 13.8 Novelty language

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

# 14. Claim-level framing boundaries

The complete claim hierarchy belongs to `02_CLAIMS_AND_DECISION_RULES.md`. The following scope-level framing remains mandatory.

## 14.1 Permitted central framing

DATP-Core may be framed as:

- a controlled threshold-calibration-scope study;
- a study of operating-point reliability under heterogeneous federated IoT clients;
- a false-alarm-equity analysis on a fixed anomaly detector;
- a journal extension with external, stress-test, and mechanism evidence;
- an evaluation of when threshold personalization remains useful.

## 14.2 Prohibited central framing

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

## 14.3 AUROC language

Permitted:

> AUROC is reported as a detector-quality control and is expected to remain unchanged when only threshold scope changes.

Prohibited:

> B2 improves AUROC.

A threshold change cannot change score ranking when the model and scores are fixed.

## 14.4 Macro-F1 language

Permitted:

> Threshold personalization may reduce false-positive dispersion while producing a lower-tail detection trade-off.

Prohibited:

> DATP improves detection performance overall.

That statement is unsupported when global or lower-tail classification metrics weaken.

## 14.5 External validation language

Permitted:

> Edge-IIoTset provides independent validation of benign operating-point equity under the audited sensor-group client definition.

Prohibited:

> DATP generalizes attack detection across Edge-IIoTset clients.

Per-client attack-sensitive metrics are unavailable under the audited artifact.

## 14.6 Temporal language

Permitted:

> One-shot recalibration is evaluated as a bounded response to threshold aging under a verified chronological split.

Prohibited:

> DATP handles concept drift.

## 14.7 Privacy language

Permitted:

> Raw traffic remains local during federated training, but no formal privacy mechanism or guarantee is provided.

Prohibited:

> DATP is privacy preserving.

## 14.8 Deployment language

Permitted:

> Communication and storage requirements are estimated from message content.

Prohibited:

> DATP is lightweight, edge ready, or deployable on constrained devices.

No hardware validation supports those claims.

---

# 15. Conference-to-journal originality boundary

## 15.1 Anchor relationship

The original DATP conference work is the scientific anchor.

DATP-Core must reproduce the anchor behavior before relying on the journal extension.

The anchor is used to recover:

- threshold-policy semantics;
- experiment meaning;
- score-artifact expectations;
- result interpretation;
- conference-faithful settings.

The scientific reference project is:

```text
/home/naslouby/Projects/datp
```

It is a behavioral reference only.

Its source layout, technical debt, module structure, names, defaults, and compatibility behavior are not inherited.

## 15.2 Material carried forward

The journal extension may retain:

- DATP nomenclature;
- the B1–B4 policy taxonomy;
- mathematical definitions and notation;
- the N-BaIoT physical-device anchor;
- the B1-versus-B2 scientific question;
- the centralized reference concept;
- the controlled heterogeneity concept;
- conference result values as historical reference.

Historical values must be identified as conference or preliminary values until reproduced in DATP-Core.

## 15.3 Substantive journal additions

The journal contribution includes:

- expansion from five to ten paired seeds;
- independent Edge-IIoTset benign-equity validation;
- formal rejection of invalid CICIoT2023 repartitions;
- shared-threshold construction sensitivity;
- benign summary-statistics comparison;
- FedProx stress testing;
- one model-personalization stress test;
- quantile sensitivity;
- calibration-size analysis;
- shrinkage thresholds;
- bounded split-conformal diagnostics;
- cluster granularity and stability;
- score-distribution mechanisms;
- one-shot temporal recalibration;
- expanded statistics, provenance, and null-result handling.

The complete executable programme is defined in `03_EXPERIMENT_CATALOGUE.md`.

## 15.4 Text and figure reuse

The journal manuscript must:

- cite the conference paper;
- disclose that it is an extended version;
- enumerate substantive new contributions in the cover letter;
- redraw or materially extend figures;
- extend or replace tables;
- avoid verbatim reuse of conference prose beyond necessary technical definitions;
- ensure that the journal paper is understandable without the conference paper.

No conference figure is reused verbatim.

A section dominated by conference prose must be rewritten.

## 15.5 Self-imposed extension threshold

DATP-Core targets at least 40% substantive new material as a conservative internal safeguard.

This is not presented as a Computer Networks rule.

Computer Networks states that enhanced, extended conference or workshop papers may be submitted, while same-content or simultaneous duplicate submissions are rejected; its current guide does not prescribe a fixed numerical extension percentage.[^computer-networks-guide]

The journal’s actual guide for authors must be rechecked immediately before submission.

## 15.6 Camera-ready and disclosure discipline

Before journal submission:

- the conference paper must have a stable citable version;
- the journal manuscript must cite it;
- the cover letter must explain the overlap and additions;
- reused data and experiments must be distinguished from new data and experiments;
- simultaneous submission is forbidden;
- any reused wording must comply with publisher and copyright rules.

---

# 16. Venue strategy

## 16.1 Primary venue

The primary target is:

```text
Computer Networks
```

The manuscript should emphasize:

- federated networked IoT detection;
- client heterogeneity;
- distributed calibration;
- operating-point reliability;
- reproducible comparative evaluation;
- practical implications for network monitoring.

Computer Networks explicitly permits enhanced, extended versions of quality conference or workshop papers, subject to originality and non-duplication requirements.[^computer-networks-guide]

## 16.2 Backup venue

The backup target is:

```text
Internet of Things
```

The final venue decision must be re-evaluated against the manuscript’s completed contribution and the current guide for authors.

## 16.3 Other non-target venue

Future Generation Computer Systems is not a primary or backup target for this paper.

Its policies or practices may be consulted only as general planning context. They must not be presented as Computer Networks requirements.

## 16.4 Excluded venue

Computers & Security is excluded under its current scope statement.

Its guide states that, since early 2024, submissions featuring AI or ML as significant components are subject to a moratorium, and it explicitly identifies federated learning as outside its current scope.[^computers-security-guide]

Because journal policies can change, this status must be rechecked at submission. The roadmap does not treat the moratorium as permanent.

## 16.5 Venue claims that must not appear

Do not state:

- that Computer Networks requires 40% new content;
- that Computers & Security will never accept FL;
- that acceptance by one Elsevier journal implies acceptance by another;
- that another paper’s publication proves current venue scope;
- that publication of FedMSE or any other prior FL paper proves that Computers & Security currently accepts federated-learning submissions;
- that Future Generation Computer Systems guidance is a Computer Networks requirement;
- that a venue is suitable without checking its current author guide.

---

# 17. Consolidated scientific guardrails

This section replaces the previous flat list of labelled boundaries.

## 17.1 Causal guardrails

- Keep the detector frozen across B1–B4 within a seed and regime.
- Keep threshold scope as the sole manipulated variable in the core ladder.
- Keep FedAvg as the core training baseline.
- Keep benign-only threshold calibration.
- Keep attack data evaluation-only.
- Keep client eligibility identical across compared policies.
- Keep the selected checkpoint common across the core ladder.
- Do not use test outcomes to choose policy parameters.

## 17.2 Metric and statistical guardrails

- Keep `CV(FPR)` as the confirmatory primary metric.
- Do not silently change its formula or denominator.
- Accompany it with absolute dispersion when mean FPR is small.
- Keep AUROC as a control.
- Keep paired seeds as the independent replication unit.
- Do not treat clients, checkpoints, windows, or subsamples as independent seeds.
- Retain the ten-seed result when it is less favorable than the five-seed result.
- Do not cherry-pick checkpoints, cluster counts, calibration sizes, or quantiles.

## 17.3 Policy and comparator guardrails

- Keep B0 outside the federated causal ladder.
- Keep B1, B2, B3, and B4 meanings fixed.
- Keep B4 canonical `K = 3`.
- Keep alternative B4 cluster counts exploratory.
- Keep `B-FedStatsBenign` benign-only and matched by exceedance.
- Use full pooled variance, including between-client mean shift.
- Keep fixed multipliers supplementary.
- Keep FedProx, Ditto, and `B-FedStatsBenign` outside the core causal ladder.
- Do not call a benign-only comparator Laridi-faithful.
- Do not call a fallback implementation Ditto.
- Do not add FedBN.

## 17.4 Dataset and regime guardrails

- Keep N-BaIoT physical devices as the sole confirmatory population.
- Add no external IoT dataset beyond Edge-IIoTset.
- Derive every client partition from audited artifact evidence.
- Do not infer CICIoT2023 physical devices from missing metadata.
- Do not infer chronology from ordering artifacts.
- Do not generalize file-level CICIoT2023 results to physical devices.
- Keep Edge-IIoTset external claims limited to supported benign-equity outcomes.
- Represent unavailable attack-sensitive metrics explicitly.
- Keep B3 out of regimes without a defensible family taxonomy.
- Do not claim fleet-scale validation.

## 17.5 Scope guardrails

- Do not add poisoning, backdoor, Byzantine, or evasion experiments.
- Do not add formal privacy mechanisms.
- Do not add hardware profiling.
- Do not add streaming drift detectors.
- Do not add Byzantine-robust federated conformal prediction.
- Do not add a broad personalized-FL benchmark.
- Do not add an exhaustive aggregation benchmark.
- Do not convert the paper into a generic FL-IDS comparison.

## 17.6 Framing guardrails

- Do not claim DATP solves non-IID FL.
- Do not claim improved global Macro-F1.
- Do not claim privacy preservation.
- Do not claim concept-drift handling.
- Do not claim deployment readiness.
- Do not claim universal threshold dominance.
- Do not use false-positive equity as a synonym for human fairness.
- Do not hide the P10 Macro-F1 trade-off.
- Do not hide null, opposite, or infeasible results.
- Do not use unsupported “first” or “state-of-the-art” language.

## 17.7 Reporting and operational guardrails

- Use a contingency table or small heatmap for B4 client-to-cluster interpretability.
- Do not use a Sankey diagram for the small `K = 3` or `K = 9` client populations.
- Translate FPR into alerts per day only when a measured or appropriately cited traffic rate exists.
- Omit alert-burden estimates when no defensible rate is available.
- Do not present hypothetical alert rates as measurements.
- Distinguish analytically estimated payload, serialized payload, and measured network traffic.

## 17.8 Originality guardrails

- Cite the conference paper.
- Disclose the extension.
- Redraw or materially extend every conference figure.
- Extend or replace every conference table.
- Do not copy the reference project’s source structure.
- Do not create backward-compatibility shims for the reference codebase.
- Keep the 40% target explicitly self-imposed.
- Recheck current venue policies at submission.
- Do not submit materially identical content simultaneously.

---

# 18. Accepted scientific limitations

The following limitations are accepted by design and must be disclosed rather than “fixed” through scope expansion.

## 18.1 Small natural client population

N-BaIoT provides nine physical-device clients.

The study does not infer fleet-scale behavior from this population.

## 18.2 One external dataset

Edge-IIoTset improves external validity but does not establish universal cross-dataset generalization.

## 18.3 Incomplete external attack assignment

The audited Edge-IIoTset artifact supports benign operating-point equity but not valid per-client attack-sensitive evaluation.

## 18.4 Single temporal family

One-shot recalibration on one verified chronological population is a boundary probe, not a general drift solution.

## 18.5 No formal privacy guarantee

Federated data locality is retained, but model updates and threshold summaries may disclose information. No formal protection is claimed.

## 18.6 No hardware evidence

Estimated message sizes do not establish latency, energy, memory, or deployment feasibility.

## 18.7 Threshold trade-offs

Reducing FPR dispersion may worsen attack sensitivity for some clients. The journal contribution includes this trade-off rather than assuming it away.

## 18.8 Comparator incompleteness

One aggregation stress test and one model-personalization stress test cannot establish superiority over the full FL literature.

## 18.9 Conformal limitation

B2-conf is an empirical diagnostic under bounded assumptions. It does not establish arbitrary per-client conditional coverage under heterogeneous, non-exchangeable, or adversarial data.

---

# 19. Change-control protocol

## 19.1 Changes allowed without scientific revision

The following may be improved without changing the scientific contract:

- wording;
- heading organization;
- internal links;
- formatting;
- clarification that does not alter meaning;
- implementation detail that satisfies existing requirements;
- correction of an obvious typographical error;
- addition of a citation supporting an existing decision.

## 19.2 Changes requiring formal roadmap revision

A formal revision is required before changing:

- the confirmatory dataset;
- the confirmatory client population;
- B1 or B2 definitions;
- the primary metric;
- seed count;
- confidence-interval decision rule;
- eligibility threshold;
- canonical quantile;
- canonical B4 cluster count;
- model family;
- FedAvg core baseline;
- checkpoint-selection rule;
- external dataset count;
- comparator-family count;
- threshold-variant count;
- temporal scope;
- benign-only calibration;
- any excluded research family.

## 19.3 Timing restriction

A scope-changing revision must occur:

- before the affected result is inspected;
- before a parameter sweep is evaluated on held-out test data;
- before a failed experiment motivates a replacement;
- before manuscript claim wording is selected.

Post-result changes are allowed only to correct errors and must preserve the original result and audit trail.

## 19.4 Required revision record

Every formal scientific revision must record:

- previous rule;
- new rule;
- reason;
- evidence available at decision time;
- whether any affected results had already been observed;
- experiments invalidated or requiring rerun;
- claim changes;
- approval date;
- affected roadmap files.

The record belongs in `07_AUDIT_AND_DECISION_LOG.md`.

---

# 20. Scientific conformance checklist

Before any core result is accepted, verify:

## 20.1 Identity

- [ ] The paper is framed as a threshold-calibration-scope study.
- [ ] The core detector is frozen across B1–B4.
- [ ] Threshold scope is the sole core manipulated variable.
- [ ] Calibration is benign-only.
- [ ] Operational FPR equity is defined and distinguished from human fairness.
- [ ] AUROC is treated as a control.

## 20.2 Policies

- [ ] B0 has separate centralized provenance.
- [ ] B1 is the arithmetic mean of eligible local quantiles.
- [ ] B2 uses one local quantile per eligible client.
- [ ] B3 is used only with a defensible family taxonomy.
- [ ] B4 uses the locked four-scalar fingerprint.
- [ ] Canonical B4 uses `K = 3`.
- [ ] No retired B5 or B3-LGS terminology appears.

## 20.3 Comparators

- [ ] `B-FedStatsBenign` is benign-only.
- [ ] Full pooled variance includes between-client mean shift.
- [ ] The primary comparator is matched by exceedance.
- [ ] Fixed multipliers remain supplementary.
- [ ] FedProx is reported outside the causal ladder.
- [ ] Ditto is genuine or renamed to the actual fallback.
- [ ] Personalized states have separate provenance.

## 20.4 Regimes

- [ ] Regime A uses nine N-BaIoT physical devices.
- [ ] CICIoT2023 file-level results remain artifact-specific.
- [ ] CICIoT2023 physical-device repartition remains suppressed without metadata.
- [ ] Edge-IIoTset client identity is audit-grounded.
- [ ] Unsupported Edge-IIoTset attack-sensitive metrics are unavailable.
- [ ] Temporal splits use real chronology.
- [ ] No new dataset was added without revision.

## 20.5 Scope

- [ ] No poisoning, evasion, backdoor, or Byzantine study was added.
- [ ] No formal privacy claim appears.
- [ ] No hardware or deployment claim appears.
- [ ] No full drift-handling claim appears.
- [ ] No fleet-scale claim appears.
- [ ] No generic FL-IDS benchmark framing appears.

## 20.6 Originality

- [ ] The conference paper is cited.
- [ ] New contributions are enumerated.
- [ ] Conference figures are redrawn or materially extended.
- [ ] Conference tables are extended or replaced.
- [ ] The 40% target is described as self-imposed.
- [ ] Current venue policies were rechecked before submission.
- [ ] The reference codebase was used only for behavioral semantics.

---

# 21. Research and policy foundations

The roadmap remains the authority for DATP-Core decisions. The sources below support scientific positioning and current venue-policy statements; they do not override local artifact audits.

[^nbaiot]: Y. Meidan et al., “N-BaIoT—Network-Based Detection of IoT Botnet Attacks Using Deep Autoencoders,” *IEEE Pervasive Computing*, 2018. DOI: [10.1109/MPRV.2018.03367731](https://doi.org/10.1109/MPRV.2018.03367731).

[^edge-iiotset]: M. A. Ferrag et al., “Edge-IIoTset: A New Comprehensive Realistic Cyber Security Dataset of IoT and IIoT Applications for Centralized and Federated Learning,” *IEEE Access*, 2022. DOI: [10.1109/ACCESS.2022.3165809](https://doi.org/10.1109/ACCESS.2022.3165809).

[^ciciot2023]: E. C. P. Neto et al., “CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment,” *Sensors*, 2023. DOI: [10.3390/s23135941](https://doi.org/10.3390/s23135941).

[^laridi]: S. Laridi, G. Palmer, and K.-M. M. Tam, “Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding,” *Scientific Reports*, 2024. DOI: [10.1038/s41598-024-76961-2](https://doi.org/10.1038/s41598-024-76961-2).

[^fedprox]: T. Li et al., “Federated Optimization in Heterogeneous Networks,” *Proceedings of MLSys*, 2020. Primary manuscript: [arXiv:1812.06127](https://arxiv.org/abs/1812.06127).

[^ditto]: T. Li, S. Hu, A. Beirami, and V. Smith, “Ditto: Fair and Robust Federated Learning Through Personalization,” *Proceedings of ICML*, PMLR 139, 2021. [Primary publication](https://proceedings.mlr.press/v139/li21h.html).

[^lu-fcp]: C. Lu et al., “Federated Conformal Predictors for Distributed Uncertainty Quantification,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/lu23i.html).

[^humbert-fcp]: P. Humbert, B. Le Bars, A. Bellet, and S. Arlot, “One-Shot Federated Conformal Prediction,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/humbert23a.html).

[^computer-networks-guide]: Elsevier, *Computer Networks — Guide for Authors*. The guide states that enhanced, extended versions of quality conference or workshop papers may be submitted and rejects same-content or simultaneous duplicate submissions. [Current guide](https://www.sciencedirect.com/journal/computer-networks/publish/guide-for-authors).

[^computers-security-guide]: Elsevier, *Computers & Security — Guide for Authors*. The current guide states that submissions featuring AI or ML as significant components are subject to a moratorium and explicitly lists federated learning as outside the journal’s present scope. [Current guide](https://www.sciencedirect.com/journal/computers-and-security/publish/guide-for-authors).