# DATP Journal Extension — Master Roadmap

**Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*

## Purpose and structure

This roadmap is the authoritative DATP-Core research contract. It deliberately serves four linked purposes without mixing their ownership:

1. **Scientific programme** — the causal question, evidence hierarchy, methods, populations, scope, and claim boundaries.
2. **Exact protocol** — the numerical, mathematical, preprocessing, training, thresholding, and dataset rules that determine scientific behavior.
3. **Experiment programme and evaluation** — what is executed, what changes, what is measured, and how inference is performed.
4. **Development and audit contract** — the provenance, identity, completeness, and publication gates used to verify that the implementation actually realizes the scientific programme.

The study asks whether the scope of benign threshold calibration changes the distribution of false-positive burden across heterogeneous federated IoT clients while the detector is held fixed. The confirmatory comparison is shared versus per-client threshold calibration on the N-BaIoT natural-device population; all other studies provide supportive, mechanism, stress-test, external, operational, or boundary evidence.

### Roadmap architecture and inheritance rule

**Define once, inherit everywhere.** Each scientific or engineering rule has one authoritative owner. Experiments inherit all applicable global contracts unless they explicitly declare a deviation. Experiment sections therefore describe their scientific delta rather than restating the whole pipeline.

This inheritance rule is a deduplication rule, **not a relaxation rule**. A referenced contract remains fully mandatory. If an implementation or experiment must differ, the deviation must receive an explicit protocol identity and be recorded before outcome inspection.

### Restructure amendment

This version restructures the previous master roadmap without narrowing the scientific programme. Detailed experiment procedures, locked grids, formulas, metric semantics, negative-result rules, and audit-critical implementation constraints are retained. True duplicate method definitions and repeated global invariants are consolidated into authoritative contracts and cross-references. Research citations are defined once in Appendix A.

### Surgical strengthening amendment — 12 August 2026

This amendment preserves every existing scientific contract and adds only bounded reviewer-critical strengthening: a fixed-score historical estimator-by-scope sensitivity, natural-device influence diagnostics, calibration-to-held-out generalization metrics, exact seed-sign robustness reporting, normalized model-personalization absorption, promotion of all mandatory shared-threshold constructions into the main robustness panel, a current-literature novelty-survival gate, FedProx mechanism-activation diagnostics, an exhaustive calibration-contributor-availability sensitivity, an explicit four-axis threshold/personalization taxonomy, a population-capability summary, and mandatory causal/equity-utility reporting views. It additionally locks a protocol-compliant/honest calibration-participant assumption for the whole threshold programme, distinguishes anomaly operating-point calibration from probability and conformal calibration, makes the calibration pooling bias–variance hypothesis explicit, adds a calibration-support-versus-client-burden mechanism diagnostic and exact per-device direction counts, strengthens the prior-art distinction schema, and incorporates current 2026 calibrated-IoT/Byzantine-calibration collision literature.

A second bounded strengthening pass on the same date makes the **deployment/federation regime explicit**, adds one simple post-FedAvg client-local fine-tuning stress condition, standardizes model-side absorption diagnostics across FedProx/fine-tuning/Ditto, adds a complete natural-device helped/harmed profile with prospectively fixed support strata, makes the held-out rebuttal to the “local q95 is equalized by construction” objection explicit, converts the existing heterogeneity/support surface into a typed descriptive policy surface rather than a learned selector, and adds a submission-grade reproducibility-release bundle. These additions do **not** change the sole confirmatory endpoint, do not add another dataset, do not create a PFL benchmark zoo, and do not authorize post-hoc model or threshold selection.

It does **not** add a new dataset, a broad FL-algorithm zoo, a threshold-estimator zoo, formal privacy experiments, attack experiments, hardware deployment, sequential majority-vote alerting, or a broader conformal-prediction programme.

### Descriptive naming amendment

This version also removes opaque letter/number aliases from the active scientific vocabulary. Threshold policies, comparators, and dataset populations are named by what they **do** or **contain**, so the roadmap, implementation, audit outputs, tables, and manuscript can be read without decoding shorthand.

The active identifiers are descriptive and stable:

```text
CENTRALIZED_REFERENCE
SHARED_THRESHOLD
LOCAL_THRESHOLD
FAMILY_THRESHOLD
CLUSTER_THRESHOLD
LOCAL_CONFORMAL_THRESHOLD
FEDERATED_BENIGN_SUMMARY_THRESHOLD
FEDERATED_KLL_SHARED_THRESHOLD

NBAIOT_NATURAL_DEVICES
CICIOT_FILE_CLIENTS
NBAIOT_DIRICHLET_CLIENTS
EDGE_SENSOR_CLIENTS
EDGE_TEMPORAL_CLIENTS
```

Opaque B-number aliases and lettered population aliases are retired from active use. They must not appear in new code-facing enums, manifests, experiment identifiers, tables, figures, audit outputs, or manuscript prose. Historical artifacts may retain old labels only as immutable provenance; they must be translated to the descriptive identity at the ingestion boundary rather than propagated.

## Part I — Scientific Programme and Global Protocol Contracts

### 1. Programme identity

**1.1 Working title**

*Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.*

**1.2 DATP-Core in one paragraph**

DATP-Core is a controlled study of **threshold-calibration scope** in federated IoT anomaly detection.

For each seed and dataset population, a federated autoencoder is trained to one fixed terminal scientific model under one locked training protocol. The terminal detector is fixed before score generation. Compared policies consume the same execution-scoped per-client calibration and test-score evidence. The ladder changes only the scope at which a benign anomaly threshold is estimated: one shared threshold, one threshold per physical-device family, one threshold per data-driven client cluster, or one threshold per client.

The scientific question is therefore not:

> Which model or federated-learning algorithm is best?

It is:

> When heterogeneous IoT clients share one frozen federated anomaly detector, how does the scope of benign threshold calibration affect the distribution of false-alarm burden across clients?

The primary object of interest is cross-client false-positive-rate dispersion. Model discrimination, including AUROC, remains a control rather than the thresholding verdict.

**Current empirical motivation.** Recent federated IoT/IoMT anomaly-detection evidence independently reinforces the distinction between discrimination and deployment operating point. Robalino-Díaz et al. report a FedAvg model with `AUC-ROC = 0.995` but overall `Recall = 0.530`, with IoMT recall falling to `0.290` under a fixed `0.5` decision threshold; post-hoc calibration materially changes that operating behavior.[^robalino2026] DATP-Core does not reproduce that probabilistic-calibration experiment. It uses the result only as external motivation for treating AUROC as insufficient to characterize a deployed thresholded detector.

---

### 2. Core causal contract

**2.1 Unit of causal comparison**

The controlled comparison is performed within a seed, population, and frozen detector.

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
- round budget and terminal scientific-model rule;
- seed cohort;
- scoring procedure;
- client eligibility;
- test population;
- metric definitions.

The fixed-detector rule applies **within each population and training baseline**. It does not mean that the same numerical model parameters are reused across different datasets with incompatible feature spaces.

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

### 2.2.2 Fixed-score identity and serialization tolerance

Two distinct notions of score equality apply within DATP-Core and must never be conflated.

**Scientific fixed-score identity.** Within any fixed-detector threshold comparison, calibration scores and evaluation scores are immutable scientific inputs. Every compared threshold policy must reference the same score-artifact identity, ordered row identities, client identities, split identities, terminal-detector identity, preprocessing identity, and evaluation labels. Policy-level score equality is proven by scientific artifact identity and provenance, never by two independently generated floating-point arrays being numerically close. A threshold policy must never independently regenerate scores when the scientific contract requires one fixed score artifact.

**Serialization/reload equivalence.** The `1e-12` absolute tolerance defined in §2.2.1 applies only to serialization/reload numerical equivalence (for example, confirming a persisted and reloaded preprocessing state reproduces the same transform). It must not be silently redefined as the threshold-policy score-identity criterion.

**AUROC.** AUROC is a detector-quality control computed from the fixed continuous evaluation-score and evaluation-label artifact; the threshold policy itself is not an AUROC input. Within one fixed-detector threshold ladder, AUROC is computed once from the canonical score/label artifact, or is proven to derive from that exact artifact by scientific artifact identity. A threshold-policy-specific AUROC difference indicates a score/provenance identity failure, not a threshold-scope effect.

**2.2.3 Empirical-quantile definition lock**

Every non-conformal exact empirical quantile used by SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, CLUSTER_THRESHOLD, the exact pooled benign oracle, the sample-weighted shared construction, shrinkage endpoints, calibration-size studies, and quantile-sensitivity studies uses the same Hyndman–Fan type-7 / NumPy `method="linear"` convention.

For sorted scores \(x_{(1)} \le \cdots \le x_{(n)}\), target \(q\in[0,1]\), and

\[
h=(n-1)q,\qquad j=\lfloor h\rfloor,\qquad \gamma=h-j,
\]

the locked quantile is

\[
Q_7(q)
=(1-\gamma)x_{(j+1)}+\gamma x_{(j+2)},
\]

with the boundary cases \(Q_7(0)=x_{(1)}\) and \(Q_7(1)=x_{(n)}\). Internal calculations use `float64` and are not rounded before threshold application.

Two exceptions are intentional and must stay explicit:

- `LOCAL_CONFORMAL_THRESHOLD` uses its finite-sample conformal order-statistic rule rather than type-7 interpolation;
- `FEDERATED_KLL_SHARED_THRESHOLD` is an approximate rank sketch and therefore returns an approximate retained-value quantile under the sketch's inclusive-rank semantics. Its error is measured against the exact type-7 pooled oracle rather than silently treated as exact.

A change in quantile interpolation is a protocol change, not an implementation detail.

**2.3 Sole manipulated variable**

For the core threshold-scope comparison, the manipulated variable is:

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

A policy-specific terminal detector, feature transformation, or test population invalidates the controlled comparison.

**2.4 Prohibited causal contamination**

The following are forbidden inside the core ladder:

- retraining the autoencoder separately for SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, or CLUSTER_THRESHOLD;
- using a non-terminal detector state for a scientific result;
- selecting thresholds from attack-labelled data;
- choosing a policy parameter using held-out test F1, TPR, AUROC, balanced accuracy, or `CV(FPR)`;
- changing eligible clients between compared policies;
- removing clients that weaken the expected ordering;
- treating FedProx or model personalization as another threshold-scope condition;
- replacing a failed shared-versus-local result with a more favorable CLUSTER_THRESHOLD, shrinkage, or conformal result.

---

### 3. Calibration and evaluation contract

**3.1 Benign-only calibration**

Every core threshold and every DATP-compatible threshold variant is fitted using benign calibration data only.

Attack-labelled records are reserved for held-out evaluation and may not influence:

- threshold values;
- quantile selection;
- client eligibility;
- terminal-detector identity;
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

**3.2A Honest-calibration participant and message-integrity assumption**

The complete DATP-Core threshold programme assumes **protocol-compliant calibration participants and an honest protocol-executing server**. This is a scientific threat-model boundary, not a security guarantee.

For every client and every threshold method, the following are assumed to be generated exactly from the declared immutable artifacts and procedure:

- benign calibration row identities and labels;
- reconstruction scores computed by the locked detector/preprocessing state;
- local empirical thresholds and calibration support counts;
- family/cluster threshold inputs;
- CLUSTER_THRESHOLD fingerprints `[mean, sample std, skewness, p95]`;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD` summary statistics;
- `FEDERATED_KLL_SHARED_THRESHOLD` sketches and declared sketch parameters;
- conformal score/order-statistic inputs;
- any serialized threshold-stage message used for communication accounting.

DATP-Core does **not** allow a participant or server to fabricate, edit, suppress, replay, reorder for semantic effect, or substitute these scientific values adversarially. In particular, no client may falsify a local threshold, support count, score summary, fingerprint, KLL sketch, conformal statistic, or client identity. No network adversary is modeled between client and server.

The shared-calibration contributor-availability sensitivity in Part II §8.6 is explicitly **non-adversarial availability sensitivity**: omission subsets are prospectively enumerated and the remaining contributors still report truthful values. It is not a Byzantine-client experiment and cannot support malicious-dropout, poisoning, integrity, or robust-aggregation claims.

A checksum/provenance mismatch, impossible support count, or message/artifact identity mismatch is treated as an **invalid scientific artifact / failed integrity gate**, not as empirical evidence that the method resisted an attack.

This boundary is required because Byzantine federated-calibration work demonstrates that malicious clients can corrupt federated conformal calibration by reporting arbitrary calibration statistics, and newer work jointly protects training and calibration against Byzantine behavior.[^robfcp2024][^prismfcp2026] DATP-Core therefore makes no claim of Byzantine-robust calibration, secure threshold aggregation, authenticated messaging, or adversarial calibration integrity.

**3.3 Client eligibility**

Two explicit calibration-size quantities apply throughout DATP-Core. `n_k_source` is the number of benign calibration records available to client `k` **before** any experimental calibration-size subsampling. `m` is the calibration sample size actually used by the calibration-size ablation (Part II — Experiment Programme, §8.1); its locked grid is `m in {50, 100, 250, 500, 1000, 5000}`.

The canonical minimum benign calibration support for primary-analysis eligibility is:

```text
n_k_source >= 100
```

Eligibility is determined from the source calibration pool, before calibration-size experimental subsampling (Part II — Experiment Programme, §8.1). It is never recomputed simply because a declared ablation cell deliberately uses fewer than 100 observations.

Only eligible clients enter the primary cross-client false-positive dispersion calculation.

Eligibility is determined before test evaluation and is identical across policies compared within the same experiment.

An ineligible client may receive a separately declared deployment fallback only when the experiment explicitly studies fallback behavior. It cannot be silently included in the confirmatory population.

**3.3A Federation regime, client persistence, and deployment identity**

DATP-Core's confirmatory population is a **persistent, identifiable-client federation**. This is an explicit operating assumption, not an implicit generalization to massive intermittent cross-device FL. Motley distinguishes cross-device settings—where clients may be numerous, sampled sparsely, unavailable, and effectively stateless—from cross-silo settings with persistent identities and stateful personalization.[^motley] DATP-Core uses the persistence semantics relevant to the latter while retaining **physical IoT devices**, not organizations, as the N-BaIoT clients.

The locked confirmatory regime is:

```text
federation_regime = PERSISTENT_IDENTIFIABLE_CLIENTS
training_participation_fraction = 1.0
training_participation = FULL_EVERY_ROUND
client_identity_persistence = REQUIRED
client_local_threshold_state_persistence = REQUIRED
client_local_personalized_model_state_persistence = REQUIRED_WHEN_APPLICABLE
intermittent_cross_device_training_claim = FORBIDDEN
unseen_client_personalized_threshold_claim = FORBIDDEN
unseen_client_personalized_model_claim = FORBIDDEN
```

For an execution coordinate `(dataset_id, population_id, training_seed)`, the same immutable `client_id` must bind, where applicable:

- the benign training partition;
- the benign calibration source pool;
- the held-out evaluation partition;
- fitted client-local preprocessing state;
- client-local threshold state;
- Ditto personalized state;
- post-FedAvg locally fine-tuned state;
- all client-disaggregated metrics.

A mismatch in this identity chain invalidates the affected artifact. Client identities may not be reassigned between training, calibration, and evaluation to make a personalization method feasible.

The cold-start calibration experiment in Part II §8.1A studies **insufficient calibration support for an already-defined client**. It is not a new/unseen-client personalization experiment. `m=0` therefore means “the known client has no usable local calibration sample in this experimental cell,” not “a never-before-seen device has arrived.”

Training-time partial participation, random client dropout, stragglers, churn, stateless client sampling, and unseen-client adaptation are outside the present scientific programme. The threshold-stage calibration-contributor-availability sensitivity in Part II §8.6 is not a substitute for those experiments because it changes only truthful contributor availability at threshold construction after the detector has already been trained.

The manuscript must therefore qualify any deployment statement as applying to **persistent identifiable IoT clients capable of retaining client-specific calibration/personalization state**. No conclusion may be generalized to population-scale intermittent cross-device FL without a separately scoped study.

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

The confirmatory endpoint and its decision rule are specified in Part III — Evaluation, Statistical Analysis, and Reporting.

**3.6 Model-quality controls**

The following may be reported as controls:

- AUROC;
- average precision (`AP`, reported as the PR-curve summary / AUPRC control);
- Macro-F1;
- balanced accuracy;
- TPR or recall;
- P10 Macro-F1;
- worst-client balanced accuracy.

They do not replace `CV(FPR)` as the primary operating-point verdict.

In particular:

- unchanged AUROC does not invalidate a threshold-scope effect;
- improved AUROC does not establish a threshold-scope effect;
- lower P10 Macro-F1 under LOCAL_THRESHOLD is an important negative trade-off and must remain visible;
- global average performance cannot hide severe client-level false-alarm disparity.

---

### 4. Threshold-policy system

**4.1 Centralized reference: CENTRALIZED_REFERENCE**

CENTRALIZED_REFERENCE is the privacy-incompatible centralized reference.

It uses:

- a centralized autoencoder trained on pooled benign training data;
- a pooled benign calibration threshold;
- separate centralized training and evaluation.

CENTRALIZED_REFERENCE is not part of the federated threshold-scope comparison.

A FedAvg model evaluated with a pooled threshold is not CENTRALIZED_REFERENCE.

CENTRALIZED_REFERENCE exists to provide context for the cost of federation, not to participate in the confirmatory claim.

**4.2 Shared threshold: SHARED_THRESHOLD**

SHARED_THRESHOLD is the shared-scope anchor.

Each eligible client computes its local benign quantile. The server calculates one shared threshold as the arithmetic mean of the eligible local quantiles.

At the canonical operating point:

```text
q = 0.95
```

Every eligible client uses the same resulting threshold.

SHARED_THRESHOLD is not the exact pooled quantile and must not be described as such.

**4.3 Local threshold: LOCAL_THRESHOLD**

LOCAL_THRESHOLD is the client-local scope anchor.

Each eligible client deploys its own benign calibration quantile at the same canonical target:

```text
q = 0.95
```

LOCAL_THRESHOLD is the comparator in the sole confirmatory shared-versus-local endpoint.

LOCAL_THRESHOLD is not assumed to dominate every policy on every metric. It may reduce FPR dispersion while increasing missed detections or weakening lower-tail classification performance for specific clients.

**4.4 Family threshold: FAMILY_THRESHOLD**

FAMILY_THRESHOLD assigns one threshold to each validated physical-device family.

The threshold is formed from the eligible local thresholds belonging to that family.

FAMILY_THRESHOLD is permitted only when:

- a defensible family taxonomy exists;
- the taxonomy is defined independently of test outcomes;
- family membership is stable and auditable;
- the taxonomy represents device identity rather than attack labels.

FAMILY_THRESHOLD is a mechanism baseline.

It is available for the N-BaIoT physical-device population and unavailable in populations without a defensible family taxonomy.

**4.5 Cluster threshold: CLUSTER_THRESHOLD**

CLUSTER_THRESHOLD is the taxonomy-free grouped-threshold mechanism.

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

CLUSTER_THRESHOLD studies grouped threshold sharing on a fixed detector.

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
SHARED_THRESHOLD: one threshold for the federation
FAMILY_THRESHOLD: one threshold per physical-device family
CLUSTER_THRESHOLD: one threshold per data-driven client cluster
LOCAL_THRESHOLD: one threshold per individual client
```

FAMILY_THRESHOLD and CLUSTER_THRESHOLD do not have to form a strict numerical ordering between SHARED_THRESHOLD and LOCAL_THRESHOLD.

Their scientific role is to test whether intermediate sharing scopes recover part of LOCAL_THRESHOLD’s operating-point equity while reducing per-client calibration dependence.

---

### 5. Supportive threshold variants

Threshold variants preserve the fixed detector but alter the threshold estimator.

They remain outside the core threshold-scope identity and cannot become confirmatory after results are observed.

**5.1 Quantile sensitivity**

The canonical quantile remains:

```text
q = 0.95
```

A pre-specified sensitivity grid tests whether conclusions depend on that choice.

An alternative quantile cannot replace the canonical endpoint post hoc.

**5.1A Historical mean-plus-standard-deviation estimator sensitivity**

A fixed-score estimator-by-scope sensitivity tests whether the shared-versus-local operating-point effect is specific to the empirical `q=0.95` estimator. It uses the historical N-BaIoT-style moment rule as a deliberately simple alternative estimator while preserving the DATP causal score identity.[^nbaiot]

The code-facing estimator identity is:

```text
MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR
```

For eligible client `k` with benign calibration reconstruction errors `S_k={e_{k,1},...,e_{k,n_k}}`, define

\[
\bar e_k=\frac{1}{n_k}\sum_{i=1}^{n_k}e_{k,i},
\]

\[
s_k=
\sqrt{
\frac{1}{n_k-1}
\sum_{i=1}^{n_k}(e_{k,i}-\bar e_k)^2
},
\]

using `float64` and sample standard deviation with `ddof=1`. The local moment-rule threshold is

\[
\tau_{k,\mathrm{moment}}=\bar e_k+s_k.
\]

The sensitivity is a locked `2 x 2` estimator-by-scope design:

```text
estimator in {TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR}
scope     in {SHARED, LOCAL}
```

For `TYPE7_Q95`, the existing SHARED_THRESHOLD and LOCAL_THRESHOLD definitions are reused unchanged. For the moment estimator:

\[
\tau_{\mathrm{local},k}^{\mathrm{moment}}=\tau_{k,\mathrm{moment}},
\]

\[
\tau_{\mathrm{shared}}^{\mathrm{moment}}
=\frac{1}{K_e}\sum_{k=1}^{K_e}\tau_{k,\mathrm{moment}}.
\]

Every eligible client uses `tau_shared^moment` in the shared condition. The arithmetic mean is intentionally the same equal-client scope operator used by SHARED_THRESHOLD, so the sensitivity changes the estimator family without changing the meaning of shared versus local calibration scope.

This is **not** presented as a faithful reproduction of Meidan et al.'s complete detector, because their system also used separately trained per-device autoencoders, separately optimized hyperparameters, and a sequential majority-vote alarm rule. DATP uses only the moment threshold formula as a historical estimator-family sensitivity on one frozen score artifact. No sequential windowing is imported.

This sensitivity is supportive only. `q=0.95` remains the confirmatory estimator and cannot be replaced by the moment rule after outcome inspection.

**5.2 Local–global shrinkage**

**Calibration pooling bias–variance hypothesis.** Let the unknown client-specific population benign q-quantile be

\[
\tau_k^*=\inf\{t:F_k(t)\ge q\},
\]

where `F_k` is client `k`'s benign reconstruction-error CDF under the fixed detector. A single shared threshold can reduce estimation noise by pooling information but can incur **distribution-mismatch error** when `tau_shared` differs from `tau_k^*`. A client-local empirical threshold better targets the client's own score distribution but has greater finite-sample estimation variance when local calibration support is small. DATP-Core does not estimate `tau_k^*` from held-out test outcomes and does not claim an unbiased estimator of this unknown population quantity.

The empirical programme therefore uses only predeclared proxies:

- full-calibration scope-mismatch proxy:

\[
D^{scope}_{s,k}
=\tau^{full}_{shared,s}-\tau^{full}_{local,s,k};
\]

- finite-calibration local estimation variance across the `R=10` nested subsamples, defined in Part III §8.4;
- `Bias_tau` and `RMSE_tau` versus each client's full-calibration local threshold, defined in Part II §8.1;
- held-out target-attainment error and calibration-to-held-out generalization gap, defined in Part III §§4.7–4.8.

The scientific hypothesis is therefore not “local is always better.” It is that **shared calibration trades lower sampling variance for potential cross-client distribution mismatch, while local calibration trades lower scope mismatch for potentially higher finite-sample variance**. FAMILY_THRESHOLD, CLUSTER_THRESHOLD, fixed shrinkage, and size-aware shrinkage are interpreted as partial-pooling points on this trade-off, not as automatically superior methods. This framing is consistent with modern federated calibration work in which local calibration can become statistically poor at small sites and shrinkage borrows information across sites.[^shahid-fcrc2026]

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

The size-aware rule is fixed prospectively before experiment execution. `n_k_source` is client `k`'s complete benign calibration support before experimental subsampling and is used only for eligibility and feasibility. `n_k_used` is the benign calibration support actually supplied to estimate client `k`'s local threshold in the current experimental cell.

\[
\lambda_k = \lambda(n_{k,\mathrm{used}}) = \frac{n_{k,\mathrm{used}}}{n_{k,\mathrm{used}} + n_{\min}}
\]

where `n_min = 100`, the existing canonical minimum benign support. The deployed threshold is:

\[
\tau_k^{SA} = \lambda_k\tau_{k,\mathrm{local}} + (1-\lambda_k)\tau_{\mathrm{shared}}
\]

This deterministic rule never depends on evaluation or test labels, metrics, F1, FPR, `CV(FPR)`, AUROC, balanced accuracy, or downstream results. It is bounded in `[0, 1]` and strictly increases with positive `n_k_used`. `lambda = 0` is the conceptual shared endpoint and `lambda -> 1` approaches the local endpoint as calibration support grows. `n_min = 100` is neither fitted nor selected from experiment results; it is inherited from the canonical calibration-support contract.

In ordinary full-calibration execution, `n_k_used` is the exact benign calibration count supplied to threshold construction. In calibration-size ablations, `n_k_used = m`; a cell exists only when `n_k_source >= m`, and `n_k_source` must never replace `m` in the weight. The locked grid therefore has weights `m=50 -> 50/150`, `m=100 -> 100/200`, `m=250 -> 250/350`, `m=500 -> 500/600`, `m=1000 -> 1000/1100`, and `m=5000 -> 5000/5100`. Values are never rounded internally.

Size-aware shrinkage is compared with the shared threshold, the local threshold, and the complete locked fixed-lambda curve `{0, 0.25, 0.50, 0.75, 1.00}` without post-hoc fixed-lambda selection. It is a calibration-robustness mechanism, not a novel statistical-theory claim or confirmatory endpoint.

**Current-literature positioning.** Shahid's 2026 site-conditional federated conformal-risk-control study independently uses the same shrinkage-weight family `w_k=n_k/(n_k+n_0)` to interpolate between site-local and pooled calibration, with `n_0` selected through leave-one-site-out sensitivity analysis.[^shahid-fcrc2026] DATP therefore makes **no novelty claim for the functional form** `n/(n+n_0)`. DATP's distinct protocol choice is that the denominator constant is prospectively fixed to the pre-existing `n_min=100` calibration-support contract and is never selected from downstream performance.

**5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**

LOCAL_CONFORMAL_THRESHOLD applies a finite-sample-adjusted local conformal quantile to benign reconstruction errors. Its significance level is tied to the threshold target by:

```text
alpha = 1 - q
```

At the canonical `q = 0.95`, the main diagnostic setting is `alpha = 0.05`.

Its role is to test held-out benign coverage and address the criticism that per-client thresholds merely equalize FPR by construction.

The principal federated-conformal positioning anchors are Lu et al.’s Federated Conformal Prediction framework and Humbert et al.’s one-shot federated conformal method.[^lu-fcp][^humbert-fcp] The submission-time related-work boundary must also acknowledge personalized/localized federated conformal prediction, FedWQ-CP weighted aggregation of client quantile thresholds, group-conditional federated conformal prediction, and personalized federated weighted conformal prediction.[^pfcp2025][^fedwqcp2026][^gcfcp2026][^pfwcp2026]

These methods strengthen the scope boundary rather than expanding the experiment programme: DATP does not implement group-conditional conformal calibration, density-ratio-weighted conformal calibration, or a broad federated-conformal benchmark.

LOCAL_CONFORMAL_THRESHOLD does not establish:

- arbitrary client-conditional coverage;
- validity under unrestricted non-exchangeability;
- robustness to Byzantine calibration (explicitly outside scope in light of Rob-FCP/PRISM-FCP[^robfcp2024][^prismfcp2026]);
- a full conformal DATP contribution;
- a replacement confirmatory endpoint.

Coverage failures, finite-sample granularity, and heterogeneous-client limitations remain reportable.

---

### 6. Federated threshold comparator

**6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**

`FEDERATED_BENIGN_SUMMARY_THRESHOLD` is the DATP-compatible benign-only federated summary-statistics comparator.

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

**6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**

`FEDERATED_KLL_SHARED_THRESHOLD` is the mandatory quantile-native shared-threshold comparator. It answers whether a communication-efficient, mergeable approximation of the **pooled benign quantile** can remove an apparent SHARED_THRESHOLD weakness without introducing attack labels or a local threshold at deployment.

The comparator uses the Karnin–Lang–Liberty (KLL) mergeable quantile sketch.[^kll] The locked implementation contract is:

```text
sketch_family = KLL
numeric_type = float64
primary_k = 400
sensitivity_k = {200, 400, 800}
search_semantics = inclusive rank
q = 0.95 in the canonical experiment
client_input = all eligible benign calibration scores for that client
server_operation = merge client sketches, then query q
output_scope = one shared threshold for every eligible client
```

Apache DataSketches reports single-sided normalized-rank errors of approximately `1.33%`, `0.68%`, and `0.35%` for `k = 200`, `400`, and `800`, respectively; its `k=400` bound is approximately `0.006776` in normalized-rank units at the library's documented 99% error-bound convention.[^datasketches-kll] These values justify the locked grid; they are not DATP empirical results.

For pooled benign calibration scores \(S=\{e_i\}_{i=1}^{N}\), define the empirical CDF

\[
\widehat F_{pool}(t)
=
\frac{1}{N}\sum_{i=1}^{N}\mathbf 1[e_i\le t].
\]

For the sketch threshold \(\tau_{KLL}\), report the directly observed rank error

\[
EmpiricalRankError
=
\left|\widehat F_{pool}(\tau_{KLL})-q\right|.
\]

Also report absolute and relative threshold error against the exact type-7 pooled quantile, held-out benign target-attainment error, `CV(FPR)`, IQR, range, worst-client FPR, actual serialized sketch bytes per client, total uploaded sketch bytes, merge/query time, and client coverage.

The primary comparator uses `k=400`. The `k={200,800}` conditions are sensitivity points only and cannot replace `k=400` after outcome inspection. KLL itself is established prior art; DATP makes no sketch-algorithm novelty claim.

**6.2 Relationship to Laridi et al.**

Laridi et al. proposed a federated autoencoder threshold based on aggregated summary statistics from both normal and anomalous validation data.[^laridi]

DATP’s comparator deliberately excludes anomalous calibration information.

Therefore:

- `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is not a faithful Laridi reproduction;
- it must not be called `LARIDI_ANOMALY_INFORMED_REFERENCE`;
- its results cannot be used to claim reproduction of Laridi et al.;
- the difference in calibration contracts must be disclosed in related work and limitations.

The reserved name `LARIDI_ANOMALY_INFORMED_REFERENCE` refers only to a genuinely anomaly-informed implementation, which is out of scope for DATP-Core.

---

### 7. Training-side stress tests

Training-side stress tests change the detector and therefore cannot share the causal interpretation of the core threshold-scope comparison.

They require separate models, score sets, and evaluation.

**7.1 FedProx**

FedProx is the aggregation-side heterogeneity stress test.

At round \(t\), client \(k\) optimizes the genuine FedProx local objective

\[
\min_w\; F_k(w)+\frac{\mu}{2}\lVert w-w^{(t)}\rVert_2^2,
\]

where \(w^{(t)}\) is the server model broadcast at the start of the round. FedProx was introduced to address statistical and systems heterogeneity in federated optimization.[^fedprox]

The locked DATP stress-test coefficient grid is:

```text
mu in {0.001, 0.01, 0.1, 1.0}
```

`mu = 0` is FedAvg-equivalent and is not treated as a FedProx condition. The complete grid is reported; no single coefficient may be promoted post hoc as the "best FedProx" condition.

Its purpose in DATP-Core is to ask:

> Does a heterogeneity-aware training algorithm absorb the operating-point benefit of threshold personalization?

FedProx results must be described as a training-side sensitivity.

They cannot be merged with the FedAvg confirmatory endpoint.

**7.1A FedProx mechanism-activation diagnostics**

Because DATP-Core deliberately fixes `local_epochs = 1`, the FedProx stress test must measure whether the proximal intervention actually changes local-update drift rather than assuming that the mechanism was strongly activated.

Let `P` be the total number of trainable scalar parameters. For client `k` in round `t`, let `w^(t)` be the exact server-broadcast state and `w_out(k,t)` the exact client state returned after its one local epoch. Persist the broadcast-state identity and compute in float64:

\[
L2Drift_{k,t}
=\left\|w^{out}_{k,t}-w^{(t)}\right\|_2,
\]

\[
RMSDrift_{k,t}
=\frac{L2Drift_{k,t}}{\sqrt{P}},
\]

and, for FedProx only,

\[
TerminalProxPenalty_{k,t}(\mu)
=\frac{\mu}{2}L2Drift_{k,t}^2.
\]

For each training seed `s` and training condition `a in {FedAvg, FedProx(mu)}`, summarize:

\[
D^{all}_{s,a}
=\operatorname{median}_{k,t\in\{1,\ldots,200\}} RMSDrift_{k,t},
\]

\[
D^{terminal50}_{s,a}
=\operatorname{median}_{k,t\in\{151,\ldots,200\}} RMSDrift_{k,t}.
\]

The terminal-50-round window is fixed prospectively to the final 25% of the locked 200-round training run and is never changed after outcomes are seen. Also report each client's terminal-50 median so that a federation-wide median cannot hide one highly drifting client.

When `D_terminal50[s,FedAvg] > 1e-12`, define the un-clipped descriptive drift-suppression fraction

\[
DriftSuppression_{s,\mu}
=1-
\frac{D^{terminal50}_{s,FedProx(\mu)}}
{D^{terminal50}_{s,FedAvg}}.
\]

Interpretation is literal: `0` means no median drift suppression, `0.5` means a 50% reduction, values `<0` mean larger median drift than FedAvg, and values `>1` are impossible for non-negative drift unless a provenance/numerical error has occurred. If the FedAvg denominator is `<=1e-12`, record `UNAVAILABLE_NEAR_ZERO_FEDAVG_DRIFT`; do not add an epsilon.

For each `mu`, report the ten seed-level drift-suppression values together with the corresponding change in full-score benign heterogeneity

\[
\Delta H_{s,\mu}=H_{s,FedProx(\mu)}-H_{s,FedAvg}
\]

and the SHARED_THRESHOLD-to-LOCAL_THRESHOLD scope gain. These quantities are mechanism diagnostics only. Client-round cells are repeated measurements nested inside a training seed and must never be treated as independent inferential observations.

**7.2 Ditto**

Ditto is the planned model-personalization stress test.

Ditto maintains the ordinary global federated solution \(w\) and, for each client \(k\), a persistent personalized state \(v_k\) obtained from

\[
\min_{v_k}\;F_k(v_k)+\frac{\lambda_D}{2}\lVert v_k-w\rVert_2^2.
\]

The locked DATP stress-test grid is

```text
lambda_D in {0.1, 1.0, 2.0}
canonical_lambda_D = 1.0
```

The grid is taken from the scale of the original Ditto evaluation, which explicitly tuned among values including `{0.1, 1, 2}`; `1.0` is prospectively designated as the canonical DATP condition before DATP outcomes are inspected.[^ditto] All three values are executed and reported. The `0.1` and `2.0` conditions are sensitivity analyses and cannot rescue or replace the canonical `1.0` result.

The name *Ditto* may be used only when the implementation preserves genuine Ditto semantics, including:

- a distinct global model;
- persistent client-personalized states;
- the correct proximal personalized objective;
- no aggregation of personalized states as if they were global;
- separate evaluation.

The purpose is to ask:

> Does model personalization make threshold personalization redundant, complementary, or partially absorbed?

The in-paper comparison remains one personalized-model family, not a broad personalized-FL benchmark.

**7.2A Post-FedAvg client-local fine-tuning stress test**

`FEDAVG_LOCAL_FINE_TUNING` is the simple model-personalization stress condition. It is included because empirical PFL benchmarking shows that standard FL followed by local fine-tuning is a strong baseline and can rival more specialized personalization methods.[^matsuda-pfl] Cheng, Chadha, and Duchi additionally evaluate fine-tuned FedAvg with **10 local epochs before evaluation**; DATP-Core adopts `10` as a prospective, literature-backed stress depth rather than tuning the number of epochs against DATP outcomes.[^cheng-ftfa]

The stress condition is intentionally simple:

```text
training_method = FEDAVG_LOCAL_FINE_TUNING
initial_model = exact FedAvg terminal scientific detector at round 200
fine_tuning_epochs = 10
fine_tuning_partition = client-local benign TRAIN only
fine_tuning_calibration_access = FORBIDDEN
fine_tuning_evaluation_access = FORBIDDEN
fine_tuning_attack_label_access = FORBIDDEN
fine_tuning_aggregation_after_local_update = FORBIDDEN
fine_tuning_early_stopping = FORBIDDEN
fine_tuning_checkpoint = end of local epoch 10
optimizer_state_inheritance = FORBIDDEN
```

For client `k`, initialize

\[
v^{FT}_{k,0}=w^{FedAvg}_{200}
\]

and perform exactly ten complete local epochs minimizing the ordinary client benign-training reconstruction objective

\[
v^{FT}_{k,e+1}
=\operatorname{LocalEpoch}
\left(v^{FT}_{k,e};\,D^{train,benign}_k,\,\theta_{FedAvg}\right),
\qquad e=0,\ldots,9,
\]

where `theta_FedAvg` denotes the **same optimizer class and local-training hyperparameters** used by the FedAvg reference. The objective receives no proximal or personalization penalty; the only change is continued local optimization from the FedAvg terminal weights.

The optimizer contract is exact:

- instantiate a **fresh optimizer** for each `(training_seed, client_id)` fine-tuning run;
- copy model weights only; never copy Adam/SGD momentum, moments, scheduler counters, gradient scaler state, or any other optimizer state from federated training;
- use the FedAvg reference learning rate, batch size, optimizer betas/momentum, epsilon, weight decay, loss, gradient handling, and benign-train data-loader semantics unchanged;
- if the FedAvg reference uses a constant learning rate, retain that constant rate for all ten local epochs;
- if the FedAvg reference uses a round-indexed learning-rate schedule, use the **round-200 reference learning rate** and hold it constant throughout the ten fine-tuning epochs; do not restart or extrapolate the federated schedule;
- no new fine-tuning learning-rate grid, epoch grid, regularization grid, validation sweep, or outcome-selected checkpoint is permitted.

Fine-tuning randomness is derived deterministically from the existing seed-derivation contract with purpose label `FEDAVG_LOCAL_FINE_TUNING` and identity tuple

```text
(dataset_id, population_id, training_seed, client_id)
```

so that repeated execution of the same coordinate yields the same local batch order and terminal personalized state.

After epoch 10, each client model is frozen. That client model generates one immutable calibration-score artifact and one immutable evaluation-score artifact for that client. SHARED_THRESHOLD and LOCAL_THRESHOLD are then computed from those **fine-tuned-model scores**, without further model updates. Policy-specific re-fine-tuning is forbidden.

This condition is a model-side stress test, not part of the FedAvg fixed-detector confirmatory ladder. Ditto remains a distinct persistent regularized-personalization stress test; fine-tuning does not replace it and cannot be renamed Ditto.

**7.2B Common model-side score-alignment and threshold-absorption diagnostics**

FedProx, `FEDAVG_LOCAL_FINE_TUNING`, and Ditto must all be analyzed through the same upstream-mechanism vocabulary so that “absorption” is not inferred only from the final `CV(FPR)` contrast.

For every training seed `s`, model condition `a`, and eligible client `k`, use that condition's **full benign calibration score artifact** to compute in float64:

\[
M_{s,a,k}=\operatorname{median}(E^{cal}_{s,a,k}),
\]

\[
I_{s,a,k}=Q_7(0.75;E^{cal}_{s,a,k})-Q_7(0.25;E^{cal}_{s,a,k}),
\]

\[
T_{s,a,k}=Q_7(0.95;E^{cal}_{s,a,k}).
\]

Across the common eligible clients, define three coefficient-of-variation-style descriptive dispersions:

\[
LocationDispersion_{s,a}
=\frac{SD_k(M_{s,a,k})}{Mean_k(M_{s,a,k})},
\]

\[
ScaleDispersion_{s,a}
=\frac{SD_k(I_{s,a,k})}{Mean_k(I_{s,a,k})},
\]

\[
LocalThresholdDispersion_{s,a}
=\frac{SD_k(T_{s,a,k})}{Mean_k(T_{s,a,k})},
\]

where every `SD` is the sample standard deviation with `ddof=1`. If a denominator is non-finite or `<=1e-12`, the corresponding quantity is `UNAVAILABLE_NONPOSITIVE_SCALE`; no epsilon is added.

Let `tau_shared[s,a]` be that condition's canonical SHARED_THRESHOLD and `tau_local[s,a,k]=T[s,a,k]`. Define

\[
MeanSharedLocalThresholdDistance_{s,a}
=\frac{1}{K_e}\sum_k
\left|\tau^{shared}_{s,a}-\tau^{local}_{s,a,k}\right|,
\]

\[
NormalizedSharedLocalThresholdDistance_{s,a}
=\frac{MeanSharedLocalThresholdDistance_{s,a}}
{Mean_k(\tau^{local}_{s,a,k})}.
\]

The normalized quantity is unavailable when its denominator is non-finite or `<=1e-12`.

The ordinary within-condition benign-distribution heterogeneity term `H[s,a]` remains the exact 64-bin mean pairwise JSD defined in Part II §7.4 and is used for the within-condition empirical policy-selection surface. It is **not** used for a cross-model reduction ratio because condition-specific quantile bin edges would move with the model.

For cross-model alignment only, define a FedAvg-anchored histogram grid separately for each training seed `s`. Pool the **FedAvg full benign calibration scores** of the common eligible clients and compute the 63 type-7 cut points

\[
b_{s,j}=Q_7\!\left(\frac{j}{64};\;\bigcup_{k\in K_e}E^{cal}_{s,FedAvg,k}\right),
\qquad j=1,\ldots,63.
\]

Remove non-finite cut points and collapse exact duplicate cut points while preserving strict ascending order. The resulting fixed bins are

\[
(-\infty,b_{s,1}],\;(b_{s,1},b_{s,2}],\;\ldots,\;(b_{s,J_s},+\infty),
\]

where `J_s` is the number of retained unique interior cut points. If `J_s=0`, emit `UNAVAILABLE_DEGENERATE_FEDAVG_JSD_GRID` for cross-model JSD alignment. Otherwise apply **these same FedAvg-derived bins without refitting** to every client under FedAvg, every FedProx `mu`, `FEDAVG_LOCAL_FINE_TUNING`, and every Ditto `lambda_D`. Convert counts to relative frequencies; add no pseudocount. Use the same base-2 JSD and `0*log2(0/x)=0` convention as Part II §7.4. Define

\[
ModelAlignmentH_{s,a}
:=\frac{2}{K_e(K_e-1)}
\sum_{i<j}JSD_{B_s}(P_{s,a,i},P_{s,a,j}),
\]

where `B_s` denotes the fixed seed-specific FedAvg bin grid. `ModelAlignmentH` is therefore directly comparable across model-side conditions within a seed; the ordinary `H` remains the condition-native heterogeneity descriptor.

The raw threshold-scope gain is

\[
\Delta Scope_{s,a}
:=CV(FPR)_{s,a,shared}-CV(FPR)_{s,a,local}.
\]

For any scalar mechanism quantity

```text
X in {
  ModelAlignmentH,
  LocationDispersion,
  ScaleDispersion,
  LocalThresholdDispersion,
  NormalizedSharedLocalThresholdDistance
}
```

with valid `X[s,FedAvg] > 1e-12`, define the un-clipped alignment-reduction fraction

\[
AlignmentReduction^X_{s,a}
=1-\frac{X_{s,a}}{X_{s,FedAvg}}.
\]

If the FedAvg denominator is `<=1e-12`, emit `UNAVAILABLE_NO_POSITIVE_FEDAVG_REFERENCE`. Negative values are retained and mean the upstream model condition increased the measured dispersion/heterogeneity.

When `DeltaScope[s,FedAvg] > 1e-12`, define the general un-clipped scope-absorption fraction

\[
ScopeAbsorption_{s,a}
=1-\frac{\Delta Scope_{s,a}}{\Delta Scope_{s,FedAvg}}.
\]

The existing canonical Ditto `AbsorptionFraction` is exactly `ScopeAbsorption[s,Ditto(lambda_D=1.0)]`; it is not a separate formula. The same calculation is reported for every FedProx coefficient and for `FEDAVG_LOCAL_FINE_TUNING` when the denominator is valid.

For every model-side condition, interpretation uses the same locked seed-level bands when `DeltaScope[s,FedAvg] > 1e-12`:

```text
ScopeAbsorption <= 0.25          RETAINED_STRONGLY
0.25 < ScopeAbsorption <= 0.75   PARTIALLY_ABSORBED
0.75 < ScopeAbsorption <= 1.00   LARGELY_ABSORBED
ScopeAbsorption > 1.00           REVERSED_SHARED_LOCAL_ORDERING
```

Values `<0` remain inside `RETAINED_STRONGLY` and explicitly mean amplification rather than absorption. When the FedAvg gap is `<=1e-12`, emit `UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP` and interpret raw deltas only. Campaign summaries report the ten seed-level raw deltas and the distribution of valid seed-level absorption values; a ratio of campaign-level means is forbidden.

Every model-side stress condition must report, per seed, the tuple

```text
(
  ModelAlignmentH,
  LocationDispersion,
  ScaleDispersion,
  LocalThresholdDispersion,
  NormalizedSharedLocalThresholdDistance,
  DeltaScope,
  ScopeAbsorption
)
```

plus every available `AlignmentReduction`. The mechanistic hypothesis is the ordered chain

```text
upstream client adaptation
    -> lower benign-score heterogeneity / dispersion
    -> smaller shared-to-local threshold mismatch
    -> smaller SHARED_THRESHOLD-to-LOCAL_THRESHOLD FPR-equity gain
```

This chain is **tested descriptively, not assumed**. If a stress method changes the detector but does not reduce `ModelAlignmentH`/score/threshold dispersion, a null absorption result must not be interpreted as evidence that threshold personalization survives a strongly activated alignment mechanism. Conversely, association among these quantities is not sufficient for a causal mediation claim.

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

- SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, and CLUSTER_THRESHOLD may be recomputed from that model’s scores;
- the model’s threshold-scope difference may be compared with the FedAvg difference;
- the common score-alignment/threshold-absorption diagnostics in §7.2B are mandatory whenever their inputs are available;
- the result may support retention, partial absorption, or full absorption;
- the result cannot alter the identity of the FedAvg core ladder.

---

### 8. Evidence architecture

**8.1 Sole confirmatory evidence**

Only one endpoint is confirmatory:

- N-BaIoT physical-device population;
- shared versus local;
- `CV(FPR)`;
- ten paired seeds;
- locked BCa decision rule.

The statistical decision rule is specified in Part III — Evaluation, Statistical Analysis, and Reporting.

**8.2 Supporting evidence families**

All remaining work belongs to one of the following roles:

- supportive robustness;
- mechanism analysis;
- threshold variant;
- shared-estimator control;
- calibration-support/heterogeneity interaction;
- calibration cold-start boundary;
- preprocessing sensitivity;
- external validation;
- aggregation-side stress test;
- simple post-FedAvg fine-tuning stress test;
- model-personalization stress test;
- applicability boundary;
- temporal boundary;
- exploratory supplement;

A supportive analysis cannot be promoted to rescue a failed confirmatory endpoint.

An external dataset cannot silently become a second confirmatory population.

An exploratory result cannot be rewritten as pre-specified evidence after it is observed.

**8.3 Honest negative evidence**

Null, opposite, and infeasible outcomes remain scientifically meaningful. They must be reported rather than hidden or replaced by a more favorable analysis.

---

### 9. Dataset and population boundaries

Detailed population procedures belong to Part II — Experiment Programme. This section fixes only the identity-level boundaries.

**9.1 N-BaIoT physical-device anchor**

N-BaIoT is the confirmatory dataset anchor.

The original dataset study evaluated nine commercial IoT devices infected with Mirai and BASHLITE using deep autoencoder anomaly detection.[^nbaiot]

For DATP-Core:

- the nine physical devices are the natural clients;
- this is the only confirmatory client population;
- the device-family taxonomy may support FAMILY_THRESHOLD;
- all nine clients remain visible in mechanism reporting;
- the small client count is an explicit limitation.

**9.2 CICIoT2023 available-data boundary**

The original CICIoT2023 publication describes a large IoT environment with 105 devices and 33 attacks.[^ciciot2023]

The available processed DATP artifact does not retain a verified physical-device mapping.

Therefore:

- available-data pseudo-clients may be used only as a dataset-specific applicability boundary;
- a null result cannot be generalized to the original 105-device topology;
- source-paper device counts cannot be substituted for missing artifact metadata;
- device-aware wording is prohibited for this population.

Without verified physical-device identities, CICIoT2023 cannot be repartitioned as physical devices. Artificial groupings and inferred chronology are not valid substitutes.

The lossless canonical artifact remains the raw-fidelity record. Before any file-defined client construction, split, fitting, calibration, or evaluation, a CICIoT2023 row is eligible for model input if and only if its normalized label is recognized and every declared model-input feature is finite. The gate records the missing-or-unrecognized-label and non-finite-feature signals independently, preserves stable row identity and source provenance, and applies identically to every compared method. It never imputes, zero-fills, caps, clips, replaces infinities, or infers labels.

**No additional CICIoT2023 physical-device population is defined.** The currently available CICIoT2023 artifact supports `CICIOT_FILE_CLIENTS` only. The original study's device count must not be substituted for missing device-level provenance in the available DATP artifact. Do not construct inferred devices, MAC-derived clients without verified MAC provenance, artificial physical-device mappings, or synthetic replacements masquerading as natural devices.

A future CICIoT2023 physical-device population would constitute a new scientific population and may be added only if independently verified device-level provenance becomes available and the roadmap is explicitly revised before execution.

**9.3 Controlled heterogeneity population**

The Dirichlet N-BaIoT population is a controlled sensitivity experiment.

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

FAMILY_THRESHOLD is omitted when no defensible external family taxonomy exists.

**9.5 Temporal external population**

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

**9.7 Heterogeneity taxonomy and claim boundary**

The phrase **heterogeneous federated IoT clients** is not permitted to collapse fundamentally different sources of heterogeneity. Hardware-sensitive FL work explicitly treats model/hardware-capability heterogeneity as a separate problem from statistical data heterogeneity,[^fairhetero] while DATP-Core's intervention is primarily about the distribution of anomaly scores and calibration support after model training.

Every heterogeneity dimension in DATP-Core has one or more of the following status labels:

```text
OBSERVED
MANIPULATED
STRESS_TESTED
BOUNDARY_ONLY
EXCLUDED
```

| Heterogeneity dimension | Operational definition in DATP-Core | Locked status | Evidence / experiment | Claim boundary |
|---|---|---|---|---|
| natural statistical/device heterogeneity | physical devices have different benign/attack data and resulting score distributions | `OBSERVED` | `NBAIOT_NATURAL_DEVICES` | supports natural-device heterogeneity claims only for the nine N-BaIoT devices |
| controlled distribution heterogeneity | source observations are redistributed into synthetic clients with a prospectively fixed Dirichlet severity | `MANIPULATED` | `NBAIOT_DIRICHLET_CLIENTS` | sensitivity evidence; never called natural-device evidence |
| benign score-distribution heterogeneity | between-client differences in the frozen detector's benign reconstruction-score distributions, quantified by `H` and score-dispersion diagnostics | `OBSERVED`, `MANIPULATED_INDIRECTLY` | natural devices, Dirichlet sweep, preprocessing/training stress conditions | supports score-geometry mechanism language, not universal “non-IID severity” equivalence |
| calibration-support / quantity heterogeneity | clients differ in `n_k_source`; controlled analyses also restrict used calibration size `m` | `OBSERVED`, `MANIPULATED` | Part II §§7.5A, 7.5B, 8.1, 8.1A | supports finite-calibration and support-conditioned conclusions only |
| model/predictor heterogeneity | clients deploy distinct learned detector parameters | `STRESS_TESTED`, `EXCLUDED_FROM_CORE` | Ditto and `FEDAVG_LOCAL_FINE_TUNING`; FedProx remains one global-model training condition | cannot be mixed into the fixed-detector confirmatory contrast |
| hardware/resource heterogeneity | clients differ in compute, memory, energy, accelerator, or feasible model capacity | `EXCLUDED` | none | no hardware-sensitive or resource-fairness claim |
| participation/client-lifecycle heterogeneity | clients are intermittently available, sampled sparsely, churn, or arrive unseen | `EXCLUDED`; truthful threshold-contributor availability is `BOUNDARY_ONLY` | §3.3A and Part II §8.6 | no cross-device intermittency, unseen-client, straggler, or dropout claim |
| temporal heterogeneity | score distributions change over real chronology | `BOUNDARY_ONLY`, `OBSERVED` where timestamp-valid | `EDGE_TEMPORAL_CLIENTS` one-shot recalibration | no continuous adaptation or drift-detector claim |

`MANIPULATED_INDIRECTLY` means the programme changes a declared upstream condition (for example Dirichlet allocation, preprocessing, or model training) and then **measures** resulting score heterogeneity; it does not directly synthesize a target JSD value.

The manuscript's unqualified central heterogeneity language refers to **natural/statistical device heterogeneity, benign-score heterogeneity, and calibration-support heterogeneity**, with the controlled Dirichlet and temporal programmes providing bounded sensitivity/boundary evidence. Hardware/model-capacity heterogeneity and intermittent-client systems heterogeneity remain separate research problems.

### 10. Scope, terminology, claim boundaries, and accepted limitations

This section consolidates scope control, vocabulary, claim discipline, and accepted limitations. The underlying constraints are preserved; consolidation prevents the same boundary from being rediscovered in several distant sections.

#### 10.A Included scientific scope

DATP-Core strengthens the original DATP study along six bounded directions.

**10.A.1 External validation**

One external IoT/IIoT dataset tests whether benign false-alarm equity effects transfer beyond N-BaIoT.

**10.A.2 Federated threshold comparison**

One benign-only summary-statistics comparator tests whether threshold personalization is dominated by a distributed shared-threshold alternative.

**10.A.3 Training-side robustness**

Three bounded training-side stress routes examine:

- heterogeneity-aware federated optimization through FedProx;
- simple post-FedAvg client-local fine-tuning through `FEDAVG_LOCAL_FINE_TUNING`;
- persistent proximal client model personalization through Ditto.

They remain outside the causal ladder. Fine-tuning and Ditto are two deliberately different implementations of the same reviewer counterfactual—client-specific model adaptation—not authorization for a broader PFL benchmark.

**10.A.4 Threshold-estimation depth**

The threshold story is extended through:

- quantile-level sensitivity;
- one fixed-score historical `mean + sample-standard-deviation` estimator-by-scope sensitivity;
- local–global shrinkage;
- calibration-size-aware shrinkage;
- a bounded split-conformal local-threshold diagnostic.

**10.A.5 Temporal boundary**

One chronological, one-shot recalibration experiment tests whether frozen thresholds age and whether a single future benign calibration window recovers operating-point equity.

**10.A.6 Mechanism analysis**

The journal extension includes bounded mechanism work covering:

- family and cluster granularity;
- cluster stability;

- per-client benign and attack score geometry;
- heterogeneity–benefit association;
- threshold movement versus FPR/TPR trade-off.

These analyses explain the result but do not create additional confirmatory claims.

**10.A.7 Hard scope limits**

The complete programme is limited to:

- one new IoT dataset;
- four bounded external comparator/stress identities:
  - FedProx;
  - `FEDAVG_LOCAL_FINE_TUNING`;
  - Ditto;
  - one benign-only federated threshold comparator;
- five threshold-extension families;
- one temporal-recalibration family;
- the pre-specified mechanism programme;
- ten paired seeds for the confirmatory endpoint.

Expansion beyond these limits would change the study’s scientific scope.

---

#### 10.B Excluded scientific scope

**10.B.1 Security attacks and defenses**

DATP-Core does not study adversarial attacks, poisoning, or defensive mechanisms. The exclusion covers training poisoning, model/update poisoning, backdoors, inference-time evasion, malicious calibration-row manipulation, falsified threshold/summary/fingerprint/sketch messages, Byzantine calibration contributors, malicious contributor omission, and network tampering with threshold-stage messages. The protocol-compliant calibration assumption is defined in §3.2A.

Rob-FCP shows that arbitrary malicious calibration statistics can invalidate ordinary federated conformal calibration, while PRISM-FCP extends Byzantine treatment across both training and calibration phases.[^robfcp2024][^prismfcp2026] These works define an explicit future/security boundary; they do not create a DATP-Core experiment.

**10.B.2 Formal privacy**

DATP-Core does not implement or claim formal privacy protections or guarantees.

Keeping raw data local is a structural property of FL, not a formal privacy guarantee.

CLUSTER_THRESHOLD clustering is not a privacy mechanism.

Threshold-message size is not a privacy proof.

**10.B.3 Deployment validation**

DATP-Core does not provide hardware, resource, network-traffic, or production deployment validation.

Communication and storage may be estimated from serialized message sizes. Such estimates must not be called deployment measurements.

**10.B.4 Fleet scale**

The paper does not claim fleet-scale validation above 100 clients.

Synthetic client counts or available-data pseudo-clients do not establish real fleet-scale deployment.

**10.B.5 Full drift handling**

The temporal experiment does not provide continuous adaptation, online recalibration, or autonomous drift detection.

**10.B.6 Broad FL benchmarking**

The study is not an exhaustive benchmark of federated learning, personalization, clustering, anomaly detection, privacy, or intrusion-detection methods.

FedBN is excluded because introducing BatchNorm would change the locked autoencoder architecture and therefore the scientific object.

**10.B.7 Federated conformal breadth**

The bounded LOCAL_CONFORMAL_THRESHOLD diagnostic does not expand into federated conformal benchmarking, method development, adversarial conformal prediction, or online adaptation.

Lu et al. and Humbert et al. are primary prior-art anchors for federated conformal prediction.[^lu-fcp][^humbert-fcp]

---

**10.B.10 Explicit non-expansion guardrails for this amendment**

The additions above do not authorize the following scope expansion:

- no faithful anomaly-informed Laridi comparator inside the core threshold-scope comparison;
- no ECE or Brier score without a probabilistic-calibration semantics that this roadmap does not define;
- no APFL/pFedMe/Per-FedAvg/FedRep/FedPer/FedBN personalization zoo beyond the two locked client-model stress routes `FEDAVG_LOCAL_FINE_TUNING` and Ditto; G-PFL-ID and FBID are citation/positioning evidence, not additional implementations;
- no FedNova/FedAdam/FedYogi/SCAFFOLD/robust-aggregation benchmark zoo beyond the locked FedProx stress test;
- no POT/SPOT/ECDF/PyThresh/KDE/MAD or other broad threshold-estimator benchmark zoo; the locked `TYPE7_Q95` versus historical `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` sensitivity is the bounded estimator-family robustness test;
- no poisoning, backdoor, Byzantine, evasion, or calibration-channel attack experiment in DATP-Core; Rob-FCP and PRISM-FCP remain threat-boundary citations, not baselines;
- no CF-HFC reproduction, Fuzzy-FedProx branch, hardware-aware fuzzy scheduling experiment, or Adaptive Conformal Calibration branch; CF-HFC is citation/positioning evidence only;
- no DP, secure aggregation, or homomorphic-encryption claim unless introduced later as a separately scoped mechanism with its own threat model;
- no extra external dataset added merely to increase dataset count;
- no continuous drift detector, adaptive online controller, or streaming-threshold paper hidden inside the one-shot temporal boundary experiment;
- no client-count sweep presented as natural-device scalability evidence.

These remain future or separate-study directions.

#### 10.C Terminology and naming rules

**10.C.1 Project naming**

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

**10.C.2 Threshold-policy identifiers**

Active descriptive policy identifiers are:

```text
CENTRALIZED_REFERENCE
SHARED_THRESHOLD
LOCAL_THRESHOLD
FAMILY_THRESHOLD
CLUSTER_THRESHOLD
```

Their meanings are fixed by this document. The identifiers describe the scientific behavior directly and are shared across the roadmap, implementation contracts, manifests, audit outputs, tables, and figures.

Do not reuse these identifiers for:

- shrinkage;
- conformal variants;
- summary-statistics comparators;
- stress-test models;
- future methods.

**10.C.3 Threshold-variant identifiers**

Use descriptive identities:

```text
LOCAL_GLOBAL_SHRINKAGE
CALIBRATION_SIZE_AWARE_SHRINKAGE
LOCAL_CONFORMAL_THRESHOLD
FEDERATED_BENIGN_SUMMARY_THRESHOLD
FEDERATED_KLL_SHARED_THRESHOLD
```

Opaque numbered aliases, recycled family-policy labels, and vague names such as `Laridi-faithful benign` are prohibited. `FAMILY_THRESHOLD` is reserved exclusively for physical-device-family thresholding.

**10.C.4 Laridi naming**

Use:

```text
FEDERATED_BENIGN_SUMMARY_THRESHOLD
```

for the benign-only DATP-compatible summary-statistics comparator.

Reserve:

```text
LARIDI_ANOMALY_INFORMED_REFERENCE
```

for a genuinely anomaly-informed reproduction, which is out of scope.

Never call the benign adaptation *faithful*.

**10.C.5 Personalized-model naming**

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

**10.C.5A Simple local-fine-tuning naming**

Use the exact identity `FEDAVG_LOCAL_FINE_TUNING` for the locked ten-epoch post-FedAvg stress condition. Do not call it Ditto, FedPer, Per-FedAvg, local-only training, or a new DATP threshold method. Its personalization occurs in the detector parameters before scoring; the downstream SHARED_THRESHOLD/LOCAL_THRESHOLD comparison remains a separate threshold-calibration intervention.

**10.C.6 Population identifiers**

Active population identifiers are:

```text
NBAIOT_NATURAL_DEVICES
CICIOT_FILE_CLIENTS
NBAIOT_DIRICHLET_CLIENTS
EDGE_SENSOR_CLIENTS
EDGE_TEMPORAL_CLIENTS
```

They refer to scientific dataset/population contracts, not arbitrary implementation labels.

Every mention must include a descriptive phrase at first use, such as:

```text
NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor
```

**10.C.7 Statistical and equity language**

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

**10.C.7A Calibration-object taxonomy — mandatory at first manuscript use**

The word *calibration* is overloaded. DATP-Core must distinguish the following three scientific objects explicitly:

1. **Probability/confidence calibration** — transforms or evaluates predictive probabilities/logits so that confidence corresponds to outcome frequency. Typical quantities include ECE, NLL, and Brier score; FedCal is representative adjacent federated work.[^fedcal2024] DATP-Core does **not** claim this object and reconstruction errors are not probabilities.
2. **Anomaly operating-point calibration** — maps a fixed anomaly-score distribution plus declared benign calibration evidence to one or more decision thresholds. This is DATP-Core's primary object. Its direct held-out diagnostics are FPR, target-FPR error, calibration-to-held-out generalization gap, threshold-estimation error, and cross-client FPR dispersion.
3. **Conformal calibration** — uses nonconformity/conformity scores and a finite-sample calibration rule to construct prediction sets or acceptance regions with coverage/risk guarantees under stated assumptions. `LOCAL_CONFORMAL_THRESHOLD` touches this object only as a bounded diagnostic and inherits the explicit validity limitations in §5.4.

Consequences:

- ECE, NLL, and Brier score are not added merely because DATP uses the word *calibration*;
- held-out benign FPR/coverage and operating-point transfer are the correct primary diagnostics for DATP's threshold object;
- FedCal cannot be presented as a direct anomaly-threshold baseline;
- conformal coverage terminology may be used only for `LOCAL_CONFORMAL_THRESHOLD` and only with its declared assumptions;
- the manuscript must use **anomaly operating-point calibration** or **threshold calibration** when ambiguity with probability/conformal calibration is possible.

**10.C.8 Novelty language**

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

#### 10.D Claim-level framing boundaries

The following scope-level framing remains mandatory.

**10.D.1 Permitted central framing**

DATP-Core may be framed as:

- a controlled threshold-calibration-scope study;
- a study of operating-point reliability under heterogeneous federated IoT clients;
- a false-alarm-equity analysis on a fixed anomaly detector;
- a journal extension with external, stress-test, and mechanism evidence;
- an evaluation of when threshold personalization remains useful.

**10.D.2 Prohibited central framing**

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

**10.D.3 AUROC language**

Permitted:

> AUROC is reported as a detector-quality control and is expected to remain unchanged when only threshold scope changes.

Prohibited:

> LOCAL_THRESHOLD improves AUROC.

A threshold change cannot change score ranking when the model and scores are fixed.

**10.D.4 Macro-F1 language**

Permitted:

> Threshold personalization may reduce false-positive dispersion while producing a lower-tail detection trade-off.

Prohibited:

> DATP improves detection performance overall.

That statement is unsupported when global or lower-tail classification metrics weaken.

**10.D.5 External validation language**

Permitted:

> Edge-IIoTset provides independent validation of benign operating-point equity under the audited sensor-group client definition.

Prohibited:

> DATP generalizes attack detection across Edge-IIoTset clients.

Per-client attack-sensitive metrics are unavailable under the audited artifact.

**10.D.6 Temporal language**

Permitted:

> One-shot recalibration is evaluated as a bounded response to threshold aging under a verified chronological split.

Prohibited:

> DATP handles concept drift.

**10.D.7 Privacy language**

Permitted:

> Raw traffic remains local during federated training, but no formal privacy mechanism or guarantee is provided.

Prohibited:

> DATP is privacy preserving.

**10.D.8 Deployment language**

Permitted:

> Communication and storage requirements are estimated from message content.

Prohibited:

> DATP is lightweight, edge ready, or deployable on constrained devices.

No hardware validation supports those claims.

---

**10.D.9 Novelty boundary and mandatory prior-art audit**

DATP-Core does **not** claim invention of any of the following primitives:

```text
local anomaly thresholds
client-specific anomaly thresholds
benign p95 thresholds
mean/aggregation of local thresholds
federated threshold computation
percentile thresholding
personalized federated calibration in general
federated conformal prediction
clustered federated learning
```

The defensible contribution is the controlled intervention:

> DATP-Core is a controlled empirical study of threshold-calibration scope in federated IoT anomaly detection: detector state, preprocessing, client population, calibration evidence, score identity, evaluation labels, and quantile target are held fixed while only threshold-sharing scope is varied, and the resulting operating-point effects are assessed primarily through cross-client false-positive-rate dispersion under benign-only calibration.

The manuscript must distinguish four separate design axes:

```text
A. threshold estimator:
    empirical quantile / moment rule / sketch / conformal order statistic / supervised F1 search / ...

B. threshold-calibration scope:
    federation / physical-device family / data-driven cluster / individual client

C. detector/model personalization:
    one shared detector / partially personalized detector / one personalized detector per client

D. temporal adaptation:
    frozen threshold / one-shot recalibration / streaming-or-continuous adaptation
```

Komadina et al. provide direct evidence that the estimator axis is itself broad: their IEEE Access study identifies and implements five supervised and twenty unsupervised threshold-selection methods.[^komadina2024] DATP-Core deliberately does not reproduce that estimator catalogue. Its confirmatory causal comparison manipulates **axis B only**, while the detector/score artifact, type-7 empirical-quantile estimator, and `q=0.95` target are fixed. The q95-versus-moment sensitivity deliberately changes axis A; FedProx/Ditto and preprocessing sensitivity alter upstream detector geometry (axis C or its inputs); the one-shot temporal experiment changes axis D. None can replace the confirmatory axis-B endpoint.

The threshold-related-work subsection must be organized by the object being calibrated or personalized:

1. local anomaly-threshold estimators;
2. federated/shared threshold aggregation;
3. anomaly-informed supervised global threshold optimization;
4. group/cluster threshold scope;
5. personalized-model plus personalized-threshold systems;
6. formal federated and personalized calibration/conformal methods.

At minimum, the following collision table must be represented in the manuscript or supplement and kept current at submission time:

| Prior work | Relevant overlap | What DATP must not claim | DATP distinction |
|---|---|---|---|
| Meidan et al. 2018[^nbaiot] | one benign-trained autoencoder and one anomaly threshold per physical N-BaIoT device; historical `mean + std` threshold rule | first device-specific anomaly threshold / first device-aware thresholding on N-BaIoT | Meidan personalizes detector, hyperparameters, threshold, and sequential alarm rule together; DATP isolates threshold scope on one frozen federated detector and score artifact |
| Zhang et al. / FedIoT 2021[^fediot2021] | N-BaIoT federated autoencoder with post-training benign-score threshold construction and global/personalized threshold support | first post-training threshold construction for federated IoT anomaly detection | DATP makes threshold scope the controlled intervention and cross-client FPR dispersion the primary outcome |
| Rey et al. 2022[^rey2022] | federated IoT malware detection with an autoencoder and server averaging of client-local anomaly thresholds | first federated IoT AE thresholding / first aggregation of local thresholds | fixed-score threshold-scope intervention with per-client FPR dispersion as primary outcome |
| Ochiai et al. 2023[^ochiai2023] | distributed IoT-edge anomaly detection with coordinated thresholding | first distributed IoT threshold coordination | centralized causal comparison of threshold-sharing scope on immutable scores |
| Laridi et al. 2024[^laridi] | explicit federated global threshold selection | first federated threshold-selection study | benign-only calibration; no anomaly-informed F1 optimization; scope rather than estimator competition |
| Komadina et al. 2024[^komadina2024] | systematic network-anomaly threshold-estimator study covering five supervised and twenty unsupervised methods | exhaustive/first broad threshold-estimator benchmark; q95 is globally optimal | DATP fixes the estimator in the confirmatory ladder and studies who contributes calibration evidence; the historical estimator 2×2 is only a bounded robustness check |
| FedCal 2024[^fedcal2024] | explicit local and global calibration in federated learning using client-specific parameterized scalers aggregated into a global scaler | first local/global federated calibration study / first federated calibration method | DATP calibrates anomaly-score operating thresholds rather than predictive probabilities and studies fixed-score FPR-equity effects in federated IoT anomaly detection |
| Asiri et al. 2025[^asiri2025] | benign local `p95` reconstruction-error threshold in federated IoT malware detection | first benign p95/client threshold for FL IoT | operating-point-equity study with fixed detector and controlled scope |
| Personalized federated conformal prediction, 2025[^pfcp2025] | agent-personalized federated calibration with formal coverage goals | first personalized federated calibration / novel federated conformal calibration | LOCAL_CONFORMAL_THRESHOLD is only a bounded supportive diagnostic for AE benign-score thresholding |
| G-PFL-ID 2026[^gpfli2026] | unsupervised personalized federated IoT IDS using graph encoders/DeepSVDD, evaluated on IoT-23 and natural-device N-BaIoT | first personalized unsupervised federated IoT IDS / first personalized N-BaIoT anomaly detector | DATP does not compete on model architecture; the locked Ditto experiment asks whether model personalization absorbs the fixed-score threshold-scope effect |
| Fed-DTCN 2026[^feddtcn2026] | personalized federated IoT anomaly detector with client-specific threshold \(\rho_k\) | first client-specific federated IoT anomaly threshold | shared frozen-detector score evidence is separated from threshold personalization |
| FBID 2026[^fbid2026] | adaptive personalized FL for CICIoT2023 OOD intrusion detection using server-side bandit control and global/local blending | first personalized FL-IDS / first OOD-aware personalized IoT IDS | DATP neither reproduces FBID nor claims PFL novelty; FBID strengthens the reviewer counterfactual tested by the single locked Ditto absorption experiment |
| Robalino-Díaz et al. 2026[^robalino2026] | FedAvg preserves `AUC-ROC=0.995` while recall falls to `0.530` overall and `0.290` on IoMT under a fixed threshold | first observation that discrimination and operating behavior can diverge in federated IoT/IoMT | DATP turns operating-point calibration scope into the controlled intervention and uses AUROC only as a frozen-score detector control |
| FedWQ-CP 2026[^fedwqcp2026] | clients transmit local conformal quantile thresholds and calibration sizes; server forms a weighted global threshold | first weighted aggregation of federated local calibration thresholds | DATP's shared-construction controls are comparators; DATP does not claim federated quantile-aggregation novelty |
| GC-FCP 2026[^gcfcp2026] | group-conditional federated calibration with mergeable group-stratified summaries and formal coverage objectives | first group-conditional federated calibration | FAMILY_THRESHOLD/CLUSTER_THRESHOLD are empirical AE operating-point scopes, not group-conditional conformal guarantees |
| PFWCP 2026[^pfwcp2026] | personalized weighted federated conformal calibration under heterogeneity and limited local calibration | first personalized weighted federated calibration | DATP's local calibration and shrinkage are empirical anomaly-threshold mechanisms without conformal-theory novelty |
| Rob-FCP 2024[^robfcp2024] | Byzantine-robust federated conformal calibration; malicious clients may submit arbitrary calibration statistics and are filtered before global conformal quantile estimation | Byzantine robustness of DATP thresholds / secure or attack-resistant threshold aggregation | DATP assumes protocol-compliant calibration participants and studies statistical scope, not adversarial trustworthiness |
| CF-HFC 2026[^cfhfc2026] | heterogeneous-IoT IDS combining hardware-aware fuzzy client clustering, Fuzzy-FedProx, and Adaptive Conformal Calibration that dynamically adjusts decision thresholds | first calibrated FL-IDS for heterogeneous IoT / first adaptive conformal thresholding in federated IoT | CF-HFC changes clustering, optimization, system scheduling, and calibration jointly; DATP isolates threshold-calibration scope on fixed score artifacts and does not reproduce this multi-component system |
| PRISM-FCP 2026[^prismfcp2026] | Byzantine-robust FCP across both model training and calibration using partial model sharing plus histogram-based filtering of calibration submissions | end-to-end Byzantine robustness / communication-efficient secure calibration | DATP's honest-calibration contract intentionally excludes both adversarial training and adversarial calibration; PRISM-FCP is a threat-boundary citation, not a baseline |
| Shahid 2026[^shahid-fcrc2026] | fixed pretrained model; pooled versus local/site-uniform calibration; site-level failures hidden by average calibration; `n_k/(n_k+n_0)` shrinkage | first demonstration that average federated calibration can hide local/site failures / first local-global sample-size shrinkage | DATP's narrow contribution is federated IoT AE operating-point equity under frozen detector/score evidence; its `n_min=100` shrinkage constant is prospectively inherited rather than tuned |

No absolute `first`, `only`, or `state-of-the-art` novelty sentence is permitted unless it is separately re-verified against literature available immediately before submission.

**10.D.9A Submission-time novelty-survival literature gate**

Within **14 calendar days before manuscript submission**, repeat a targeted literature search against at least Google Scholar, Semantic Scholar, arXiv, IEEE Xplore, ACM Digital Library, Scopus or Web of Science when institutionally available, and the target journal publisher search. The search date, database/source, exact query string, and top relevant collisions must be retained with the submission evidence.

The mandatory query set is:

```text
"federated anomaly threshold"
"personalized threshold" federated anomaly detection
"site conditional" federated calibration
"group conditional" federated conformal
"federated quantile" calibration
IoT personalized anomaly threshold federated
"local threshold" federated autoencoder anomaly
"shared threshold" federated IoT anomaly
"threshold selection" network anomaly detection
"personalized federated" intrusion detection IoT
"OOD" personalized federated intrusion detection IoT
"Byzantine" federated calibration
"adversarial calibration" federated conformal
"adaptive conformal calibration" federated IoT intrusion
"calibrated federated" heterogeneous IoT intrusion threshold
```

For each query, inspect at minimum the first **50 relevance-ranked results** when the source exposes that many results, plus every 2025–submission-date item whose title/abstract directly concerns distributed/federated calibration, anomaly thresholding, client/site-conditional calibration, or personalized conformal calibration. Duplicate versions of one work are consolidated to the latest authoritative version.

A newly discovered collision triggers claim rewording and citation updates, not post-hoc experiment substitution. The gate passes only when:

- every material collision has an explicit overlap/distinction record;
- the collision table above is updated through the search date;
- no central contribution sentence relies on an unverified absolute-priority claim;
- the abstract, introduction, related work, discussion, and conclusion use the same narrowed novelty boundary.

This literature/claim-survival gate is not an authorization to add new experiments after results are known.

**10.D.9B Mandatory source-grounded prior-art distinction table**

In addition to the narrative collision table above, the manuscript or supplement must include one compact **method-object distinction table**. This is a related-work evidence table, not an implementation audit.

Minimum rows:

```text
FedIoT/FedDetect 2021
Rey et al. 2022
Ochiai et al. 2023
Laridi et al. 2024
FedCal 2024
Rob-FCP 2024
Asiri et al. 2025
PFCP 2025
Fed-DTCN 2026
CF-HFC 2026
PRISM-FCP 2026
Shahid federated CRC 2026
DATP-Core
```

Required columns, in this order:

```text
Work
Primary calibration object
Detector fixed across the work's threshold/calibration comparison?
Score/probability mapping modified by the calibration method?
Benign-only threshold fitting?
Outcome/class/attack labels used to fit the calibration object?
Shared/federation-wide operating point present?
Client-local operating point present?
Group/cluster operating point present?
Same evaluation population used across compared scopes?
Cross-client FPR dispersion reported as an endpoint?
Formal coverage/risk guarantee?
Adversarial/Byzantine calibration guarantee?
DATP-Core distinction
```

Every categorical cell must use exactly one of:

```text
YES
NO
PARTIAL
NOT_APPLICABLE
NOT_REPORTED
```

`NOT_REPORTED` is mandatory when the primary source does not establish the fact; inference must not be silently promoted into a factual table cell. Each row must be traceable to the primary paper/official publication. The table must be updated by the 14-day novelty-survival gate together with the narrative collision table.

**10.D.10 Claim-survival rules**

Each central manuscript claim must have a predeclared survival condition and a predeclared fallback wording. A failed claim is narrowed; it is never rescued by replacing the experiment.

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

**10.D.11 Negative evidence that must remain publishable**

The following are explicitly retained when observed:

- every device/seed cell for which LOCAL_THRESHOLD increases FPR or lowers an available TPR/Macro-F1 under the exact paired metric values, together with the §7.5B repeated-seed frequency; no post-hoc magnitude cutoff defines whether the cell is retained;
- any seed with \(\Delta_s\le 0\);
- any quantile level at which the SHARED_THRESHOLD–LOCAL_THRESHOLD ordering weakens or reverses;
- shrinkage values that are dominated or non-monotone;
- FAMILY_THRESHOLD/CLUSTER_THRESHOLD groupings that are unstable or provide no recovery;
- KLL sketch settings whose approximation materially changes the operating point;
- external-dataset null or opposite results;
- preprocessing conditions that attenuate the effect;
- shared-calibration contributor omissions that materially destabilize the shared threshold or its FPR distribution;
- FedProx conditions that absorb the threshold-scope effect;
- FedProx conditions whose downstream result is null while the measured local-update drift is barely changed or moves in the opposite direction;
- every `FEDAVG_LOCAL_FINE_TUNING` or Ditto condition that largely absorbs or reverses the shared-to-local scope effect under the locked §7.2B bands;
- any model-side stress condition that changes detector parameters but fails to reduce `ModelAlignmentH`, score-location/scale dispersion, local-q95 dispersion, or normalized shared-local threshold distance;
- temporal windows with no drift or no recovery;
- LOCAL_CONFORMAL_THRESHOLD undercoverage, overcoverage, or coarse finite-sample behavior.

None may be hidden by reporting only a favorable policy, seed, hyperparameter, client subset, or dataset.

#### 10.E Accepted scientific limitations

The following limitations are accepted by design and must be disclosed rather than “fixed” through scope expansion.

**10.E.1 Small natural client population**

N-BaIoT provides nine physical-device clients.

The study does not infer fleet-scale behavior from this population.

**10.E.2 One external dataset**

Edge-IIoTset improves external validity but does not establish universal cross-dataset generalization.

**10.E.3 Incomplete external attack assignment**

The available Edge-IIoTset data support benign operating-point equity but not valid per-client attack-sensitive evaluation.

**10.E.4 Single temporal family**

One-shot recalibration on one verified chronological population is a boundary probe, not a general drift solution.

**10.E.5 No formal privacy guarantee**

Federated data locality is retained, but model updates and threshold summaries may disclose information. No formal protection is claimed.

**10.E.6 No hardware evidence**

Estimated message sizes do not establish latency, energy, memory, or deployment feasibility.

**10.E.7 Threshold trade-offs**

Reducing FPR dispersion may worsen attack sensitivity for some clients. The journal contribution includes this trade-off rather than assuming it away.

**10.E.8 Comparator incompleteness**

One aggregation stress family and two bounded client-model adaptation routes (simple post-FedAvg fine-tuning and Ditto) cannot establish superiority over the full FL or personalized-FL literature.

**10.E.9 Conformal limitation**

LOCAL_CONFORMAL_THRESHOLD is an empirical diagnostic under bounded assumptions. It does not establish arbitrary per-client conditional coverage under heterogeneous, non-exchangeable, or adversarial data.

**10.E.10 Honest-calibration / no Byzantine-integrity guarantee**

All threshold-stage results assume the protocol-compliant calibration contract in §3.2A. A compromised client could in principle falsify calibration scores, local thresholds, support counts, summary statistics, cluster fingerprints, or quantile sketches; DATP-Core neither detects nor tolerates such behavior. Rob-FCP and PRISM-FCP show that adversarial calibration is a distinct federated research problem.[^robfcp2024][^prismfcp2026] This limitation is disclosed rather than repaired by adding an attack/defense branch to DATP-Core.

**10.E.11 Persistent identifiable-client limitation**

The confirmatory and client-personalized stress results require the Part I §3.3A regime: the same client identity persists across training, calibration, deployment evaluation, and any retained local threshold/personalized-model state, with full training participation. DATP-Core therefore makes **no empirical claim** for massive intermittent cross-device FL, stateless clients, unseen clients that lack a pre-existing local calibration state, or client populations whose identities cannot be linked across stages. The calibration cold-start experiment tests **support scarcity for an identified client**, not unseen-client personalization.

---

### 11. Numerical and formula navigation ledger

This ledger is a **lookup index**, not a competing definition. When a conflict exists, the cited authoritative section wins. The purpose is to let implementation and audit work locate every high-risk numerical lock quickly.

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

### 12. Protocol ownership and inheritance map

Every rule has one owner. Downstream sections inherit the owner and state only deviations or experiment-specific additions.

| Contract family | Authoritative owner | Typical inheritors |
|---|---|---|
| causal isolation / fixed detector | Part I §2 | all core threshold-scope experiments |
| preprocessing identity | Part I §2.2.1 | scoring, thresholding, preprocessing sensitivity |
| fixed-score scientific identity | Part I §2.2.2 | all threshold comparisons and evaluation |
| quantile convention | Part I §2.2.3 | core threshold-scope, pooled oracle, shrinkage, calibration-size studies |
| benign-only calibration / honest-participant contract / eligibility / persistent-client regime | Part I §3 | all DATP-compatible threshold methods, client-bound artifacts, and threshold-stage messages |
| threshold-method semantics | Part I §§4–6 | Part II experiments |
| training-stress semantics | Part I §7 | FedProx / `FEDAVG_LOCAL_FINE_TUNING` / Ditto experiments |
| evidence roles and claim tiers | Part I §8 and §10 | all experiments and manuscript claims |
| dataset/population boundaries | Part I §9 | Part II population-specific procedures |
| nested randomness | Part II §2.3A | calibration-size, cold-start, KLL when applicable |
| experiment-specific procedure | Part II | execution and reporting |
| metric and statistical semantics | Part III | all result generation |
| implementation/provenance/audit checks | Part IV | development, campaign audit, publication gate |

A duplicated statement in a downstream section is explanatory only; it cannot override the authoritative owner. Any intentional deviation must be named as a separate protocol identity before execution.


## Part II — Experiment Programme and Decision Rules

This part defines the complete executable scientific programme. It is deliberately detailed, but it no longer redefines global method or causal contracts already owned by Part I. Each experiment states what changes, what is compared, what evidence must be produced, and how the result may be interpreted.

### 0. Master experiment index

This index is navigational. Detailed procedures and decision rules remain authoritative in the referenced sections.

| Section | Experiment / analysis | Primary role | Population / setting | Main variation |
|---|---|---|---|---|
| §5.1 | Shared-versus-local threshold-scope confirmation | Confirmatory | N-BaIoT natural devices | SHARED_THRESHOLD vs LOCAL_THRESHOLD |
| §5.2 | Anchor reproduction gate | Reproducibility gate | historical N-BaIoT five-seed anchor | reproduction acceptance |
| §6.1 | Shared-threshold construction sensitivity | Supportive | N-BaIoT natural devices | SHARED_THRESHOLD vs pooled / weighted shared constructions |
| §6.2 | Quantile-level sensitivity | Supportive | N-BaIoT natural devices | `q={0.90,0.95,0.975,0.99}` |
| §6.2A | Threshold-estimator × scope sensitivity | Supportive | N-BaIoT natural devices | `{TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR} x {SHARED,LOCAL}` |
| §6.3 | Controlled non-IID severity | Supportive | controlled N-BaIoT partitions | heterogeneity severity |
| §7.1 | Threshold-sharing granularity and cluster stability | Mechanism | N-BaIoT natural devices | SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD + cluster stability |
| §7.2A | Physical-family explanatory adequacy | Mechanism | N-BaIoT natural devices | within/between-family geometry |
| §7.3 | Per-client score-distribution explanation | Mechanism | N-BaIoT natural devices | benign/attack score geometry |
| §7.4 | Heterogeneity–benefit association and decision surface | Mechanism | natural + controlled N-BaIoT evidence | JS heterogeneity × calibration support |
| §7.5 | Threshold movement versus operating-point harm | Mechanism | N-BaIoT natural devices | threshold movement vs FPR/TPR changes + exact device-direction counts |
| §7.5A | Calibration support versus shared-threshold burden | Descriptive mechanism diagnostic | N-BaIoT natural devices | source benign-calibration support vs shared FPR and local-personalization relief |
| §7.5B | Natural-device helped/harmed profile + support strata | Mandatory client-impact mechanism diagnostic | N-BaIoT natural devices | exact per-device help/harm/Pareto directions + campaign-fixed 3/3/3 support strata |
| §7.6 | Malware-family sensitivity breakdown | Supportive trade-off | N-BaIoT natural devices | Mirai/BASHLITE attack-family outcomes |
| §7.7 | Equity–utility Pareto analysis | Supportive synthesis | N-BaIoT natural devices | equity vs utility, no scalar winner |
| §8.1 | Calibration-size ablation | Boundary/supportive | N-BaIoT natural devices | `m={50,100,250,500,1000,5000}` |
| §8.1A | Calibration cold-start/onboarding boundary | Boundary | N-BaIoT natural devices | low-support onboarding |
| §8.2 | Fixed local–global shrinkage | Threshold variant | N-BaIoT natural devices | fixed λ curve |
| §8.3 | Calibration-size-aware shrinkage | Threshold variant | N-BaIoT natural devices | deterministic λ by `n_k_used` |
| §8.4 | Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | Threshold variant | N-BaIoT natural devices | finite-sample local coverage |
| §8.5 | Bounded preprocessing-geometry sensitivity | Supportive boundary | N-BaIoT natural devices | local StandardScaler vs pooled MinMax protocol identity |
| §8.6 | Shared-calibration contributor availability | Supportive operational sensitivity | N-BaIoT natural devices | exhaustive omission of `m={0,1,2,3,4}` shared-threshold contributors |
| §9.1 | Benign summary-statistics comparator | Comparator | N-BaIoT natural devices | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` |
| §9.2 | KLL federated quantile-sketch threshold | Comparator | N-BaIoT natural devices | KLL `k={200,400,800}` |
| §9.3 | Fixed-coefficient Laridi sensitivity | Optional supplement | N-BaIoT natural devices | fixed coefficient sensitivity only |
| §10.1 | Edge-IIoTset external benign-equity validation | External validation | Edge-IIoTset | independent-dataset benign equity |
| §10.2 | CICIoT2023 file-level boundary | Applicability boundary | CICIoT2023 file pseudo-clients | available-data boundary |
| §11.1 | FedProx aggregation + mechanism-activation stress test | Training stress | N-BaIoT natural devices | FedProx μ grid + local-update drift diagnostics |
| §11.2 | Ditto model-personalization stress test | Model-personalization stress | N-BaIoT natural devices | Ditto λD grid / absorption |
| §11.2A | FedAvg post-training client-local fine-tuning | Simple model-personalization stress | N-BaIoT natural devices | exactly 10 benign-training local epochs + common absorption diagnostics |
| §12.1 | One-shot recalibration under genuine chronology | Temporal boundary | Edge-IIoTset temporal population | static vs frozen-future vs one-shot recalibration |
| §13.1 | Alert-burden experiment | Operational interpretation | valid rate-bearing population | alert-count translation |
| §13.2 | Threshold-stage communication/storage/runtime accounting | Operational accounting | applicable methods | payload, storage, threshold-stage timing |
| §14.1 | Robust cluster-median threshold | Optional analysis | N-BaIoT natural devices | cluster median vs mean threshold |
| §14.2 | Additional equity indices | Optional analysis | applicable populations | Jain/Gini/IQR/range diagnostics |
| §14.3 | Extended secondary uncertainty | Optional analysis | applicable experiments | secondary paired uncertainty |


### 1. How to read this catalogue

**1.1 Evidence-role vocabulary**

Every experiment has exactly one primary evidentiary role.

**Confirmatory**
Tests the sole locked journal endpoint. Only the NBAIOT_NATURAL_DEVICES shared-versus-local comparison on `CV(FPR)` is confirmatory.

**Supportive**
Tests robustness of the confirmatory interpretation without becoming a second confirmatory claim.

**Mechanism analysis**
Explains why, when, or for which clients the threshold-scope effect appears. Mechanism analyses may support interpretation but cannot rescue a failed confirmatory endpoint.

**Threshold variant**
Tests a modified threshold-estimation rule while preserving the fixed detector. Variants are evaluated as alternatives or boundary probes, not silently merged into core threshold-scope.

**External validation**
Tests whether the operating-point effect appears on an independent dataset under a separately audited client definition.

**Stress test**
Changes the training algorithm or model-personalization mechanism and therefore sits outside the controlled core threshold-scope causal comparison.

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

### 2. Protocol inheritance and experiment-wide execution additions

The experiment catalogue is **delta-based**. Unless an experiment explicitly declares a deviation, it inherits the authoritative contracts in Part I and the evaluation/statistical rules in Part III. An experiment-specific section may narrow a contract but may not silently redefine it.

**2.1 Fixed-detector causal isolation — inherited**

Authoritative definition: Part I §§2.1–2.4. core threshold-scope share the same detector, preprocessing state, score artifacts, labels, eligibility state, and metric implementation within a fixed comparison coordinate. Threshold scope is the only manipulated variable.

**2.2 Benign-only threshold calibration — inherited**

Authoritative definition: Part I §§3.1–3.3. All DATP-compatible threshold methods use benign calibration evidence only. The Laridi distinction is defined once in Part I §6.2.

**2.3 Paired experimental design — inherited**

Authoritative scientific pairing: Part I §2.1 and Part III §§1.1–1.3. The independent replication unit is the training seed. Clients, rows, checkpoints, windows, sketch reconstructions, cluster restarts, and calibration subsamples are nested evidence and never inflate the seed count.

**2.3A Deterministic nested-randomness contract**

Every newly introduced calibration subsample, cold-start subsample, or other nested experimental draw uses the same deterministic seed derivation. Let `purpose` be an ASCII identifier and let all identity parts be canonical UTF-8 strings. Define

```text
seed_material = "DATP-Core|" + purpose + "|" + "|".join(identity_parts)
digest = SHA256(UTF8(seed_material))
seed32 = int.from_bytes(digest[0:8], byteorder="big", signed=False) mod 2^32
rng = numpy.random.Generator(numpy.random.PCG64(seed32))
```

For calibration-size and cold-start sampling:

```text
purpose = "CALIBRATION_SUBSAMPLE"
identity_parts = [dataset_id, population_id, str(training_seed), client_id, str(replicate_index)]
```

The source calibration pool is first sorted by immutable row identity. One permutation of that ordered pool is generated per `(dataset, population, training_seed, client, replicate_index)`. A sample of size `m` is the first `m` positions of that permutation. Therefore, within one replicate, smaller feasible calibration sets are exact prefixes of larger feasible sets (`m=50` is contained in `m=100`, etc.). Sampling is without replacement. Policies never receive different permutations.

`replicate_index` is zero-based in `{0,...,9}`. This deterministic subsampling seed is a nested experimental seed only; it is not a new training seed and is summarized within training seed before inference.

**2.4 Eligibility — inherited**

Authoritative definition: Part I §3.3. Every result still reports total clients, eligible clients, excluded clients, exclusion reasons, eligibility coverage, and whether compared methods used the identical eligible population.

**2.5 Terminal scientific-model discipline — inherited**

Authoritative definition: Part III §13. The locked terminal scientific round is **200**. Recovery and diagnostic checkpoints cannot become scientific detectors or policy-specific score sources.

**2.6 Negative-result discipline**

Every mandatory experiment remains reportable when it produces a strong expected effect, weak effect, null effect, reversed effect, unstable estimate, or infeasibility result. No supportive or mechanism result may replace the confirmatory endpoint.

**2.7 Manuscript evidence narrative**

The programme is interpreted through four questions; experiments are not presented as an undifferentiated benchmark zoo.

1. **Does threshold scope matter?** — NBAIOT_NATURAL_DEVICES confirmatory shared versus local.
2. **Why does it matter?** — CDF/JS geometry, FAMILY_THRESHOLD/CLUSTER_THRESHOLD mechanism, threshold movement, held-out target attainment.
3. **When does it matter?** — heterogeneity severity, calibration support, their interaction, quantile sensitivity, shrinkage, preprocessing sensitivity.
4. **When does it stop mattering?** — near-homogeneous CICIoT2023 boundary, FedProx absorption, simple post-FedAvg local fine-tuning absorption, Ditto absorption, external validation, and temporal boundary evidence.

**2.7A Three competing explanations that the programme must eliminate or bound**

The manuscript must organize the robustness evidence around three mutually distinguishable reviewer explanations rather than presenting supportive experiments as an algorithm catalogue:

1. **Scope effect** — heterogeneous clients genuinely require different operating points even when the detector and score artifacts are fixed. Primary evidence: the confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD paired `CV(FPR)` effect, held-out target attainment, per-device threshold/FPR movement, and grouped-scope mechanism analyses.
2. **Estimator artifact** — the apparent effect exists only because the canonical shared threshold is poorly constructed or because `q=0.95` is a special estimator. Required attacks on this explanation: exact pooled shared, sample-weighted shared, KLL shared, `FEDERATED_BENIGN_SUMMARY_THRESHOLD`, quantile sensitivity, and the fixed-score `TYPE7_Q95` versus `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` 2×2.
3. **Upstream absorption** — better representation, preprocessing, heterogeneity-aware optimization, or personalized models remove the score heterogeneity that creates the threshold-scope effect. Required attacks on this explanation: pooled-MinMax preprocessing sensitivity, FedProx mechanism-activation/absorption, the literature-backed 10-epoch `FEDAVG_LOCAL_FINE_TUNING` 2×2, the canonical Ditto 2×2, and the common score-alignment/threshold-absorption diagnostics from Part I §7.2B. The required mechanistic chain is `upstream adaptation -> lower score heterogeneity/dispersion -> lower shared-local threshold mismatch -> lower DeltaScope`; every arrow is measured rather than presumed.

Calibration-size/shrinkage analyses bound a fourth practical issue—**finite local calibration uncertainty**—without redefining the three causal explanations above. External and temporal experiments bound transport/stationarity rather than replacing the primary explanation test.

A result may survive one explanation and fail another; the manuscript must report that pattern rather than collapse all evidence into a single robustness adjective.

**2.8 Reviewer-objection → experiment coverage**

| Reviewer objection | Mandatory response | Decisive output |
|---|---|---|
| “SHARED_THRESHOLD is simply a poor global-threshold estimator.” | exact pooled + sample-weighted + KLL + `FEDERATED_BENIGN_SUMMARY_THRESHOLD` controls | LOCAL_THRESHOLD contrast under every mandatory shared construction |
| “Local p95 is trivial/prior art.” | fixed-detector scope intervention, not estimator novelty | paired `CV(FPR)` effect with immutable score identity |
| “Local q95 equalizes FPR by construction.” | strict calibration/evaluation row disjointness + explicit `H_TAUTOLOGY` rebuttal | calibration exceedance, held-out `SignedTestFPRTargetError`, and `CalibrationGeneralizationGap` on different rows |
| “Local thresholds only work with abundant calibration data.” | calibration-size curve + cold-start boundary | threshold RMSE/bias, target error, SHARED_THRESHOLD/LOCAL_THRESHOLD/shrinkage curves |
| “The effect is just stronger heterogeneity.” | controlled Dirichlet sweep + JS mechanism | heterogeneity–benefit association with all severities retained |
| “Calibration size and heterogeneity are confounded.” | predeclared 3×4 interaction experiment | interaction coefficient and complete cell grid |
| “q=0.95 was chosen because it worked.” | locked q sensitivity `{0.90,0.95,0.975,0.99}` | complete q surface; canonical q never replaced |
| “The scope effect exists only for quantile thresholding.” | fixed-score historical moment-estimator 2-by-2 sensitivity | shared-to-local `CV(FPR)` gain under both `TYPE7_Q95` and `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` |
| “One pathological N-BaIoT device drives the headline result.” | leave-one-device-out influence diagnostic with no retraining/rescoring | all nine `Delta_(s,-j)` surfaces, mean-effect range, `MaxLODOShift`, and sign retention |
| “FedAvg is the problem.” | complete FedProx `mu` grid | SHARED_THRESHOLD–LOCAL_THRESHOLD gain under each independently trained detector |
| “Personalized models make DATP redundant.” | literature-backed `FEDAVG_LOCAL_FINE_TUNING` 10-epoch 2×2 + canonical Ditto 2×2 plus Ditto λ sensitivity | raw `DeltaScope`, `ScopeAbsorption`, and common score/threshold-alignment diagnostics |
| “An upstream method changed the model but did not actually align client score geometry.” | common Part I §7.2B mechanism diagnostics for FedProx/fine-tuning/Ditto | fixed-grid cross-model `ModelAlignmentH`, location/scale/q95 dispersion, normalized shared-local threshold distance, alignment reductions |
| “DATP silently assumes persistent clients and does not apply to intermittent cross-device FL.” | Part I §3.3A persistent-identifiable-client contract + cold-start distinction | explicit full-participation/persistence regime; unseen/intermittent claims forbidden |
| “Average personalization gains may hide harmed devices.” | exact N-BaIoT helped/harmed profile + fixed support-stratum summary | per-seed help/harm/Pareto fractions, per-device help frequency, support-stratum summaries |
| “CLUSTER_THRESHOLD is arbitrary clustering.” | stability, silhouette, within/between JS, feature leave-one-out | ARI, membership tables, silhouette, CLUSTER_THRESHOLD recovery and ablations |
| “Per-client normalization created the effect.” | bounded pooled-MinMax preprocessing sensitivity | SHARED_THRESHOLD–LOCAL_THRESHOLD gain and score heterogeneity under each preprocessing protocol |
| “Lower CV merely hides utility loss.” | equity–utility Pareto analysis + family TPR | Pareto set, P10 Macro-F1, worst BA, Mirai/BASHLITE TPR |
| “The method has no operational-cost story.” | threshold-stage payload/runtime/storage accounting | actual serialized bytes and threshold-stage timing; no hardware claim |
| “Calibration clients can lie or poison the summaries.” | Part I §3.2A honest-calibration threat boundary + Rob-FCP/PRISM-FCP prior art | explicit non-Byzantine scope statement; no attack-resilience claim |
| “Calibration means ECE/Brier; why are those missing?” | Part I §10.C.7A calibration-object taxonomy | anomaly operating-point calibration is separated from probability and conformal calibration |
| “Small or low-support clients may pay a different shared-threshold burden.” | Part II §7.5A calibration-support-versus-burden diagnostic | per-seed Spearman support associations plus all-client support/burden table |
| “A 2026 heterogeneous-IoT paper already combines FL calibration and adaptive thresholds.” | CF-HFC collision row + fixed-score causal distinction | citation/positioning only; no multi-component CF-HFC reproduction |

This table is a manuscript-defence map, not an implementation audit.


### 3. Method crosswalk — definitions are owned by Part I

Part II does not redefine methods. It references the authoritative scientific definitions below and adds only experiment-specific factors, procedures, and outputs.

| Method / family | Authoritative definition | Role in Part II |
|---|---|---|
| CENTRALIZED_REFERENCE centralized reference | Part I §4.1 | contextual centralized reference only |
| SHARED_THRESHOLD shared threshold | Part I §4.2 | locked confirmatory shared-scope anchor |
| LOCAL_THRESHOLD local threshold | Part I §4.3 | locked confirmatory local-scope comparator |
| FAMILY_THRESHOLD physical-family threshold | Part I §4.4 | mechanism baseline where taxonomy is defensible |
| CLUSTER_THRESHOLD data-driven cluster threshold | Part I §4.5 | taxonomy-free grouped-threshold mechanism |
| exact pooled / sample-weighted shared constructions | Part II §6.1 | supportive shared-estimator controls |
| `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` | Part I §5.1A; Part II §6.2A | fixed-score historical estimator-family sensitivity; sample SD `ddof=1` |
| fixed local–global shrinkage | Part I §5.2; Part II §8.2 | locked `lambda in {0.00,0.25,0.50,0.75,1.00}` curve |
| size-aware shrinkage | Part I §5.3; Part II §8.3 | deterministic `n_k_used/(n_k_used+100)` mechanism |
| LOCAL_CONFORMAL_THRESHOLD | Part I §5.4; Part II §8.4 | finite-sample local coverage diagnostic |
| `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | Part I §6.1; Part II §9.1 | benign-only shared federated threshold comparator |
| `FEDERATED_KLL_SHARED_THRESHOLD` | Part I §6.1A; Part II §9.2 | KLL shared approximate pooled-quantile comparator; sensitivity `k in {200, 800}` around canonical `k=400` |
| FedProx | Part I §7.1; Part II §11.1 | separate-detector training stress test; `mu in {0.001,0.01,0.1,1.0}` |
| `FEDAVG_LOCAL_FINE_TUNING` | Part I §7.2A; Part II §11.2A | separate client-personalized detector stress test; exactly 10 benign-training epochs from round-200 FedAvg |
| Ditto | Part I §7.2; Part II §11.2 | separate personalized-model stress test; `lambda_D in {0.1,1.0,2.0}`, canonical `1.0` |

Any implementation that changes one of these definitions creates a new protocol identity; it may not inherit the old name silently.


### 4. Dataset populations and evaluation settings

**4.0 Population capability and claim-boundary table**

This table is mandatory manuscript/supplement metadata. It prevents an available metric from being mistaken for an authorized scientific claim.

| Population | Client identity | Locked client count | Natural physical-device claim valid? | FPR-equity metrics | Per-client attack metrics | Genuine chronology | Primary evidence role |
|---|---|---:|---|---|---|---|---|
| `NBAIOT_NATURAL_DEVICES` | original commercial IoT device | `9` | **Yes** | **Yes** | **Yes**, subject to held-out family support | **No genuine-time claim** from source-row ordering | sole confirmatory + principal mechanism |
| `CICIOT_FILE_CLIENTS` | processed CSV file pseudo-client | `63` | **No** | **Yes** | **Not authorized for DATP claims** | **No** | applicability boundary |
| `NBAIOT_DIRICHLET_CLIENTS` | synthetic Dirichlet client | `20` | **No** | **Yes** | **Yes**, where source attack support remains valid | **No** | controlled heterogeneity sensitivity |
| `EDGE_SENSOR_CLIENTS` | benign sensor-group folder | `10` | **No physical-device claim** | **Yes** | **No** — valid per-client attack assignment unavailable | **No** | independent external benign-equity validation |
| `EDGE_TEMPORAL_CLIENTS` | timestamp-valid sensor-group folder | `9` | **No physical-device claim** | **Yes** | **No** — temporal experiment is benign-only | **Yes** | one-shot temporal boundary |

`FPR-equity metrics = Yes` means the roadmap authorizes per-client benign FPR and cross-client dispersion for that population under its own protocol. It does not imply that all threshold methods or all manuscript claims are available there. `Per-client attack metrics = No` is an explicit scientific unavailability state, not missing implementation.

**4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor**

**Scientific role**

NBAIOT_NATURAL_DEVICES is the sole confirmatory population and the principal mechanism-analysis substrate.

**Dataset and population**

N-BaIoT contains traffic from nine commercial IoT devices exposed to Mirai and BASHLITE botnet activity in the original dataset study.[^nbaiot] The nine physical devices are the nine federated clients.

**Permitted analyses**

NBAIOT_NATURAL_DEVICES supports:

- CENTRALIZED_REFERENCE, SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, and CLUSTER_THRESHOLD;
- the confirmatory shared-versus-local experiment;
- shared-threshold construction controls;
- quantile sensitivity;
- family/cluster granularity and stability;
- score-distribution mechanism analyses;
- calibration-size ablation;
- local–global shrinkage;
- LOCAL_CONFORMAL_THRESHOLD;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
- `FEDERATED_KLL_SHARED_THRESHOLD`;
- attack-family TPR breakdown for Mirai and BASHLITE where client-level family support is valid;
- equity–utility Pareto analysis;
- bounded preprocessing sensitivity;
- calibration cold-start boundary;
- FedProx;
- `FEDAVG_LOCAL_FINE_TUNING`;
- Ditto;
- operational alert-burden translation when a real or cited traffic rate exists.

**Primary limitation**

The population contains only nine physical clients. Client-level results are therefore displayed completely; no client may be filtered because it weakens the desired pattern.

**4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary**

**Scientific role**

CICIOT_FILE_CLIENTS tests whether threshold personalization remains useful when the available processed artifacts form near-homogeneous file-defined pseudo-clients rather than natural physical-device clients.

**Dataset context**

The original CICIoT2023 study describes a large IoT topology with 105 devices and 33 attacks grouped into seven categories.[^ciciot2023] Those source-level properties do not automatically survive into every processed CSV distribution.

The available data contain 63 file-defined pseudo-clients and lack the metadata required to reconstruct physical-device clients.

**Permitted interpretation**

CICIOT_FILE_CLIENTS may support only an applicability-boundary statement about the file-defined pseudo-clients.

It must not be used to claim:

- device-level generalization on CICIoT2023;
- physical-client equity;
- temporal behavior;
- device-aware threshold performance on the original 105-device topology.

**Permitted analyses**

- CENTRALIZED_REFERENCE;
- SHARED_THRESHOLD;
- LOCAL_THRESHOLD;
- CLUSTER_THRESHOLD;
- pairwise benign-distribution Jensen–Shannon divergence;
- `CV(FPR)`, IQR, and range;
- descriptive quantile-estimation comparisons.

**Required conclusion discipline**

A null shared-versus-local difference is expected to be scientifically useful: it indicates that personalization may be unnecessary when clients are nearly homogeneous.

**4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep**

**Scientific role**

NBAIOT_DIRICHLET_CLIENTS tests whether the threshold-scope effect changes systematically with controlled non-IID severity.

**Population**

Twenty synthetic clients are constructed from the N-BaIoT analysis population using the locked Dirichlet partition procedure.

**Severity grid**

```text
alpha in {0.1, 0.3, 0.5, 1.0, 10.0, IID}
```

Lower `alpha` values represent stronger concentration and more severe distributional skew. Dirichlet partitioning is used only as a controlled sensitivity mechanism; it does not replace the natural physical-device evidence of NBAIOT_NATURAL_DEVICES.

**Policies**

- SHARED_THRESHOLD;
- LOCAL_THRESHOLD;
- CLUSTER_THRESHOLD.

FAMILY_THRESHOLD is not automatically available because the synthetic partition need not preserve the physical family taxonomy.

**Interpretation**

The primary expectation is a graded relationship between heterogeneity and the SHARED_THRESHOLD–LOCAL_THRESHOLD `CV(FPR)` difference.

However:

- strict monotonicity is not required;
- overlapping low-alpha seed distributions are described as a high-heterogeneity band;
- a non-monotone result is reported;
- the sweep does not become confirmatory.

**4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation**

**Scientific role**

EDGE_SENSOR_CLIENTS is the independent external validation of benign operating-point equity.

**Dataset context**

The Edge-IIoTset paper presents a purpose-built IoT/IIoT testbed with devices, sensors, protocols, and edge/cloud configurations, designed for centralized and federated-learning security research.[^edge-iiotset]

**Client definition**

Ten benign sensor-group folders form the static external client population. The Modbus folder is valid for static benign-equity evaluation because its rows retain the declared 63-column layout; its `frame.time` values are address literals and therefore exclude it only from the temporal population.

Eligible-benign coverage is 1.0 under the locked `n_k_source >= 100` rule.

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

EDGE_SENSOR_CLIENTS supports:

- per-client benign FPR;
- cross-client `CV(FPR)`;
- IQR and range of FPR;
- worst-client FPR;
- threshold dispersion;
- benign score-distribution analysis;
- SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
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

EDGE_SENSOR_CLIENTS therefore validates external false-positive equity, not external cross-client attack-detection equity.

**FAMILY_THRESHOLD status**

FAMILY_THRESHOLD is omitted because no defensible Edge-IIoTset family taxonomy has been established for the ten sensor-group clients.

**4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary**

**Scientific role**

This population tests threshold aging and one-shot recalibration under genuine chronology. It is a temporal boundary experiment, not a drift-detection system.

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

**5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation**

**Scientific role**

**Confirmatory.** This is the only experiment that can establish the locked main journal endpoint.

**Question**

Under one fixed FedAvg autoencoder per seed, does changing the calibration scope from one shared threshold (SHARED_THRESHOLD) to one threshold per physical device (LOCAL_THRESHOLD) reduce cross-client false-positive-rate dispersion on N-BaIoT?

**Why the experiment is necessary**

The conference result used five seeds. The journal extension must reproduce that evidence and expand it to ten paired seeds without suppressing a less favorable estimate.

**Population and inputs**

- NBAIOT_NATURAL_DEVICES;
- nine physical-device clients;
- ten paired training seeds;
- one terminal scientific detector per seed;
- benign calibration scores;
- held-out benign and attack test scores;
- unchanged eligibility.

**Fixed elements**

- autoencoder architecture;
- FedAvg training;
- local epochs `E = 1`;
- full participation;
- preprocessing;
- terminal scientific-model rule;
- quantile `q = 0.95`;
- test records;
- metric implementation;
- historical temporal-gap data partition (per-device chronological source-row order, `60 / 1 / 20 / 1 / 18`, guard gaps discarded, scaler fit on training rows only).

**Experimental factor**

Threshold-calibration scope:

- SHARED_THRESHOLD shared threshold;
- LOCAL_THRESHOLD per-client threshold.

**Procedure**

1. Reproduce the locked five-seed subset using the journal implementation.
2. Apply the anchor reproduction gate (§5.2) to the reproduced five-seed result. Do not proceed to step 3 unless the gate emits an anchor-success verdict.
3. Extend execution to ten paired seeds.
4. For every seed, compute per-client FPR under SHARED_THRESHOLD and LOCAL_THRESHOLD.
5. Compute `CV(FPR)` over the same eligible clients.
6. Compute the paired seed-level contrast:

\[
\Delta_s
=
CV(FPR)_{\mathrm{shared},s}
-
CV(FPR)_{\mathrm{local},s}
\]

7. Report all ten seed-level contrasts.
8. Compute the locked 95% BCa confidence interval over the ten paired contrasts.
9. Report sign consistency and the exact paired sign-test diagnostic defined in Part III §12.1A.
10. Report IQR and max–min FPR alongside CV to guard against small-denominator distortion.
11. Report absolute paired changes in worst-client FPR and FPR IQR, plus the descriptive relative `CV(FPR)` reduction defined in Part III §11.1A.
12. Execute the leave-one-device-out influence diagnostic in Part III §15.1A using the already generated score artifacts; do not retrain or rescore.
13. Report detection-quality controls for NBAIOT_NATURAL_DEVICES without treating them as the primary verdict.

**Required outcomes**

- SHARED_THRESHOLD and LOCAL_THRESHOLD per-client FPR for every seed;
- seed-level SHARED_THRESHOLD and LOCAL_THRESHOLD `CV(FPR)`;
- ten paired deltas;
- arithmetic-mean paired delta as the confirmatory point estimate, plus the descriptive median paired delta;
- 95% BCa interval;
- sign-consistency positive/zero/negative counts and exact paired sign-test p-value as secondary evidence;
- IQR and range;
- `DeltaWorstFPR`, `DeltaIQR`, and descriptive `RelativeCVReduction`;
- complete leave-one-device-out `Delta_(s,-j)` values, per-device ten-seed mean, `MinLODOMean`, `MaxLODOMean`, `MaxLODOShift`, and positive-direction retention count;
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
LOCAL_THRESHOLD increases `CV(FPR)` relative to SHARED_THRESHOLD.

**Confirmatory inference unavailable**
The locked 95% BCa interval cannot validly be produced (see §5.3). The confirmatory claim is not established; no other interval or test substitutes for it.

Every outcome becomes the main ten-seed result. The five-seed result is labelled preliminary when the ten-seed evidence is weaker or materially different.

**Prohibited uses**

- no alteration of the terminal detector from this result;
- no replacement by CLUSTER_THRESHOLD, shrinkage, or LOCAL_CONFORMAL_THRESHOLD if the endpoint fails;
- no removal of unfavorable seeds;
- no claim that LOCAL_THRESHOLD improves overall detection performance.

**5.2 Anchor reproduction gate**

This is an anchor reproduction/compatibility gate. It is not a formal statistical equivalence test. No additional equivalence margin is invented.

**Locked historical reference**

```text
reference 95% BCa interval = [0.647, 0.769]
reference interval width   = 0.122
maximum width multiplier   = 1.20
maximum exact reproduced interval width = 1.20 x 0.122 = 0.1464
display-only three-decimal value = 0.147
```

`0.1464` is the operative exact bound used for the pass/fail decision. `0.147` is a display-only rounded representation of the same bound; it never introduces a second, looser threshold.

**Acceptance conditions**

The reproduced five-seed anchor passes only when all of the following hold:

1. the exact historical five-seed cohort is used;
2. the historical anchor dataset identity is preserved;
3. the historical client population is preserved;
4. the historical preprocessing identity is preserved;
5. the historical training protocol is preserved;
6. the historical terminal-model semantics are preserved;
7. the historical scoring semantics are preserved;
8. the historical threshold semantics are preserved;
9. the historical eligibility semantics are preserved;
10. the historical metric definition is preserved;
11. the reproduced 95% BCa interval remains entirely positive;
12. the reproduced interval overlaps `[0.647, 0.769]`;
13. the reproduced interval width is `<= 0.1464`;
14. required artifact lineage, provenance, identity, serialization, and reload-validation gates pass.

If every condition passes, the existing appropriate anchor-success state is emitted and execution may proceed to the ten-seed extension.

**`ANCHOR_REPRODUCTION_FAILED`**

If any condition fails, the anchor status is exactly `ANCHOR_REPRODUCTION_FAILED`. This status:

- blocks the ten-seed journal extension;
- blocks downstream journal claim-generating execution;
- requires investigation;
- requires a successful anchor reproduction before proceeding;
- is not overridden by supportive evidence;
- is not overridden by external validation;
- is not overridden by favorable alternative threshold methods;
- is never relaxed after observing the result; the fourteen acceptance conditions above cannot be loosened post hoc.

**Deterministic anchor path**

```text
anchor reproduction -> anchor verification -> anchor acceptance verdict -> permission or prohibition to continue
```

**5.3 Confirmatory inference unavailable**

The sole confirmatory endpoint locks a 95% BCa confidence interval (Part III §11.2). `CONFIRMATORY_INFERENCE_UNAVAILABLE` is the explicit outcome when that locked interval cannot validly be produced, including at minimum:

- fewer than ten valid paired seed deltas;
- undefined BCa acceleration;
- invalid BCa acceleration;
- degenerate bootstrap distribution;
- another explicitly detected BCa degeneracy that prevents valid computation of the locked interval.

When this occurs, the report must include:

- every available paired seed-level delta;
- the arithmetic mean paired delta;
- sign counts;
- the exact reason BCa inference was unavailable;
- valid descriptive secondary statistics;
- percentile/basic bootstrap intervals only when explicitly labelled as diagnostics.

**Scientific interpretation.** The confirmatory claim is **not established**. This must not be silently converted to `CONFIRMATORY_SUPPORT` or to `NO_OBSERVED_ADVANTAGE`. No secondary result -- percentile bootstrap, basic bootstrap, normal bootstrap, Wilcoxon, another statistical test, a supportive threshold result, mechanism analysis, an external dataset, a FedProx result, a Ditto result, or an exploratory result -- may rescue an unavailable confirmatory inference. The manuscript must explicitly report that the confirmatory endpoint was inferentially unavailable under the locked protocol while separately reporting descriptive observations.

---

### 6. Supportive robustness experiments

**6.1 Shared-threshold construction sensitivity**

**Scientific role**

**Supportive.**

**Question**

Is the observed shared-versus-local difference caused specifically by SHARED_THRESHOLD’s arithmetic mean of local quantiles, or does it persist across alternative shared-threshold constructions?

**Comparison set**

- SHARED_THRESHOLD arithmetic mean of local quantiles;
- exact pooled benign type-7 quantile;
- sample-weighted mean of eligible local type-7 quantiles;
- `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD` with the locked matched-target construction;
- LOCAL_THRESHOLD local quantiles.

The KLL and benign-summary methods retain their authoritative method definitions in Part I §6 and their dedicated diagnostics in Part II §9; §6.1 only promotes their **shared-versus-local operating-point contrast** into the mandatory shared-construction robustness panel.

**Procedure**

Use the same NBAIOT_NATURAL_DEVICES model, scores, clients, and seeds as the confirmatory experiment. Recompute thresholds only.

For each shared construction:

- compute the shared threshold;
- evaluate all eligible clients;
- compute `CV(FPR)`, IQR, range, and worst-client FPR;
- calculate the paired difference relative to LOCAL_THRESHOLD;
- report achieved pooled and per-client exceedance.

**Interpretation**

**Robust construction effect**
All reasonable shared constructions retain higher FPR dispersion than LOCAL_THRESHOLD.

**Construction-specific effect**
One shared construction approaches or outperforms LOCAL_THRESHOLD. The claim is narrowed to the locked SHARED_THRESHOLD construction.

**No shared-versus-local distinction**
Shared constructions and LOCAL_THRESHOLD are practically similar.

This experiment cannot alter the definition of the confirmatory SHARED_THRESHOLD endpoint.

**6.2 Quantile-level sensitivity**

**Scientific role**

**Supportive threshold sensitivity.**

**Question**

Does the SHARED_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD ordering depend on choosing `q = 0.95`?

**Quantile grid**

```text
q in {0.90, 0.95, 0.975, 0.99}
```

**Procedure**

For every NBAIOT_NATURAL_DEVICES seed and quantile:

- compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and canonical CLUSTER_THRESHOLD;
- evaluate on unchanged held-out test scores;
- report mean FPR, `CV(FPR)`, IQR, range, worst-client FPR, TPR, and P10 Macro-F1;
- report achieved benign exceedance against the target `1 - q`;
- visualize the policy-by-quantile surface.

Where EDGE_SENSOR_CLIENTS supports the same calculation, repeat only the benign-FPR outcomes.

**Interpretation**

An ordering inversion is reported directly. The canonical `q = 0.95` is not changed after inspection.

**6.2A Threshold-estimator × scope sensitivity**

**Scientific role**

**Supportive estimator-family robustness test.**

**Question**

Does the shared-versus-local operating-point effect persist when the threshold estimator changes from the canonical type-7 `q=0.95` quantile to the historical `mean + sample-standard-deviation` rule?

**Population and fixed evidence**

- NBAIOT_NATURAL_DEVICES only;
- the exact same ten frozen FedAvg detector/score artifacts as §5.1;
- the same eligible clients, calibration records, evaluation rows, labels, and metric implementation;
- no retraining, rescoring, calibration resampling, or windowed majority-vote stage.

**Locked 2-by-2 factors**

```text
estimator = {TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR}
scope     = {SHARED, LOCAL}
```

`TYPE7_Q95` reuses canonical SHARED_THRESHOLD and LOCAL_THRESHOLD at `q=0.95`. `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` uses Part I §5.1A exactly (`float64`, sample SD, `ddof=1`).

For each seed `s` and estimator `E`, define the scope gain

\[
\Delta^{scope}_{s,E}
=CV(FPR)_{s,E,shared}-CV(FPR)_{s,E,local}.
\]

Define the estimator-sensitivity contrast

\[
\Delta^{estimator}_s
=\Delta^{scope}_{s,MEAN+SD}-\Delta^{scope}_{s,Q95}.
\]

This contrast describes how much the shared-to-local gain changes when the estimator family changes. It is secondary and does not test a new confirmatory hypothesis.

**Procedure**

1. load the canonical fixed calibration/test score artifact for each seed;
2. compute the four locked estimator/scope thresholds;
3. evaluate per-client FPR and attack-sensitive controls on the unchanged held-out evaluation scores;
4. compute `CV(FPR)`, IQR, range, worst-client FPR, held-out target/attainment diagnostics where a nominal target exists, and the calibration-generalization gap from Part III §4.8;
5. compute `Delta_scope[s,E]` for both estimator families and `Delta_estimator[s]`;
6. report all ten seeds; no estimator or seed may be omitted because it weakens the desired pattern.

**Required outcomes**

- all four threshold conditions per seed/client;
- per-client FPR, TPR, balanced accuracy, and Macro-F1;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- ten `Delta_scope[Q95]` values;
- ten `Delta_scope[MEAN+SD]` values;
- ten `Delta_estimator` values;
- sign counts for each estimator's scope gain;
- paired descriptive BCa interval for mean `Delta_scope[MEAN+SD]` when defined, explicitly secondary;
- complete negative-result reporting when the moment estimator weakens or reverses the scope effect.

**Interpretation**

- positive mean scope gain under both estimators: evidence that the calibration-scope phenomenon is not unique to q95;
- positive q95 gain but null/opposite moment-rule gain: estimator-dependent scope effect;
- stronger moment-rule gain: supportive robustness only, not permission to replace q95;
- moment-rule failure or poor utility: report as a historical estimator limitation.

The moment estimator never becomes confirmatory and is not described as a new DATP thresholding algorithm.

**6.3 Controlled non-IID severity**

**Scientific role**

**Supportive heterogeneity analysis.**

**Question**

Does stronger client heterogeneity increase the operating-point advantage of local threshold calibration?

**Population and factors**

- NBAIOT_DIRICHLET_CLIENTS;
- 20 synthetic clients;
- Dirichlet severity grid:
  - `0.1`;
  - `0.3`;
  - `0.5`;
  - `1.0`;
  - `10.0`;
  - IID;
- SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD;
- ten paired seeds where feasible.

**Procedure**

For every seed and severity:

1. construct the partition using the locked seed and partition rule;
2. retain the pre-specified partition;
3. train a separate terminal `FEDAVG` detector for this `(training seed, heterogeneity severity)` cell under the fixed training protocol below — this includes IID as one severity condition in this grid; never share another severity's fitted preprocessing state, detector state, calibration scores, or evaluation scores;
4. compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD;
5. report heterogeneity diagnostics;
6. compute the SHARED_THRESHOLD–LOCAL_THRESHOLD `CV(FPR)` difference;
7. report uncertainty per alpha;
8. display seed distributions rather than only point estimates.

**Detector training discipline**

For every `(training seed, heterogeneity severity)` cell, including IID, a separate terminal `FEDAVG` detector is trained. The training **protocol** remains fixed across severities: model family; architecture apart from feature-schema-driven input dimension; optimizer; loss; training hyperparameters; local epoch count; participation; aggregation semantics; round budget; terminal scientific-model rule; training-seed semantics; and named preprocessing protocol identity.

The following scientific states must never be shared between different severity/population cells: population-dependent fitted preprocessing state; terminal detector state; calibration scores; evaluation scores.

Within one fixed `(seed, heterogeneity severity)` cell, SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD use the same terminal detector, fitted preprocessing state, calibration scores, evaluation scores, evaluation labels, and eligibility state.

**Required heterogeneity diagnostics**

At minimum:

- client sample-count distribution;
- client benign-distribution divergence;
- class or attack composition when valid;
- eligible-client coverage;
- pairwise or aggregate Jensen–Shannon divergence.

**Interpretation**

A smooth monotone curve is not required. Low-alpha conditions may form one broad high-heterogeneity band. The result is associative and does not establish that the selected heterogeneity statistic causally determines DATP benefit.

Comparisons across heterogeneity severities are **supportive / associative**, not threshold-only causal comparisons. Changing heterogeneity changes the federated training problem and may change the resulting detector; cross-severity results must not be interpreted as isolating a causal effect of heterogeneity on threshold scope independently of detector learning.

---

### 7. Cluster and family mechanism programme

**7.1 Threshold-sharing granularity and cluster stability**

**Scientific role**

**Mechanism analysis.**

**Questions**

- Does family or cluster threshold sharing recover part of LOCAL_THRESHOLD’s FPR-equity benefit?
- How much calibration granularity is required?
- Are CLUSTER_THRESHOLD client assignments stable across seeds and calibration samples?
- Does cluster sharing provide a defensible middle ground between one global threshold and one threshold per client?

**Population**

- NBAIOT_NATURAL_DEVICES is mandatory;
- EDGE_SENSOR_CLIENTS may include CLUSTER_THRESHOLD;
- FAMILY_THRESHOLD remains NBAIOT_NATURAL_DEVICES only.

**Comparison set**

- SHARED_THRESHOLD shared;
- FAMILY_THRESHOLD family;
- CLUSTER_THRESHOLD canonical `K = 3`;
- LOCAL_THRESHOLD local;
- exploratory CLUSTER_THRESHOLD cluster counts where mathematically feasible.

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
10. compare CLUSTER_THRESHOLD groupings against the device-family taxonomy descriptively without treating taxonomy agreement as the optimization target;
11. calculate Euclidean silhouette values in the standardized four-feature fingerprint space;
12. calculate within-cluster versus between-cluster benign-score JS divergence;
13. calculate per-client assignment-switch frequency after label alignment to the smallest training-seed value used in the campaign;
14. execute the four locked leave-one-fingerprint-feature-out ablations, each with `K=3` and otherwise identical clustering:
    - omit `mean(error)`;
    - omit `standard_deviation(error)`;
    - omit `skewness(error)`;
    - omit `p95(error)`.

For silhouette, for client \(i\), let \(a_i\) be its mean Euclidean distance to other members of its assigned cluster and \(b_i\) the minimum mean distance to any other non-empty cluster. Then

\[
s_i=\frac{b_i-a_i}{\max(a_i,b_i)}.
\]

A singleton client receives `s_i = 0`, matching the standard silhouette-sample convention. Mean silhouette is unavailable when fewer than two non-empty clusters exist.

For label-stable per-client switch reporting, use the smallest training-seed value as the fixed reference partition. For each other seed, align cluster labels to the reference by the permutation that maximizes client-membership overlap. Client \(k\)'s switch frequency is

\[
SwitchFrequency_k
=\frac{1}{S-1}\sum_{s\ne s_0}\mathbf 1[\widetilde c_{k,s}\ne c_{k,s_0}].
\]

Adjusted Rand index remains the primary label-invariant partition-comparison diagnostic; the switch-frequency quantity is an interpretable per-client companion. Because NBAIOT_NATURAL_DEVICES has only nine clients, underlying assignments and contingency tables remain mandatory.[^ari]

**Recovery-of-local-gap definitions**

For grouped method `G in {FAMILY_THRESHOLD,CLUSTER_THRESHOLD}`, define, seed by seed,

\[
RecoveryFraction_G
=
\frac{CV(FPR)_{\mathrm{shared}}-CV(FPR)_G}
{CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}}.
\]

This quantity is available only when the shared-to-local denominator is strictly greater than `1e-12`. It is **not clipped** to `[0,1]`: values below zero mean the grouped policy is worse than SHARED_THRESHOLD on the primary dispersion metric, and values above one mean it exceeds the LOCAL_THRESHOLD reduction for that seed. If the denominator is `<= 1e-12`, the recovery fraction is `UNAVAILABLE_NO_POSITIVE_LOCAL_GAP`, while the raw CV values remain reportable.

**Required outcomes**

- SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD `CV(FPR)`;
- worst-client FPR;
- IQR and range;
- FAMILY_THRESHOLD and CLUSTER_THRESHOLD recovery fractions relative to the SHARED_THRESHOLD–LOCAL_THRESHOLD gap;
- within-cluster and across-cluster threshold/FPR dispersion;
- within-cluster and between-cluster benign-score JS divergence;
- mean silhouette and per-client silhouette values;
- ARI across seed pairs or declared resamples;
- complete membership assignments;
- per-client switch frequency;
- cluster sizes;
- empty or singleton cluster diagnostics;
- canonical-versus-leave-one-feature-out ARI, silhouette, `CV(FPR)`, and worst-client FPR for all four ablations;
- detection-quality controls for NBAIOT_NATURAL_DEVICES.

**Interpretation**

**Useful middle ground**
CLUSTER_THRESHOLD or FAMILY_THRESHOLD recovers a meaningful portion of LOCAL_THRESHOLD’s equity improvement with stable groupings.

**Performance without stability**
CLUSTER_THRESHOLD reduces dispersion, but assignments are unstable. The result is reported as fragile.

**Stable but unhelpful**
Clusters repeat, but do not improve the operating point.

**No cluster mechanism**
CLUSTER_THRESHOLD is unstable and provides little recovery. CLUSTER_THRESHOLD remains an explored negative mechanism result.

**7.2A Physical-family explanatory adequacy**

**Scientific role**

**Mechanism analysis for FAMILY_THRESHOLD.**

The locked device-family taxonomy is not assumed to correspond to score-distribution similarity. Its explanatory adequacy is measured.

For every seed, using eligible NBAIOT_NATURAL_DEVICES clients, calculate pairwise benign-score JS divergence. Let \(\mathcal P_W\) be pairs from the same physical family and \(\mathcal P_B\) pairs from different families:

\[
WithinFamilyJS
=\frac{1}{|\mathcal P_W|}\sum_{(i,j)\in\mathcal P_W}JSD(P_i,P_j),
\]

\[
BetweenFamilyJS
=\frac{1}{|\mathcal P_B|}\sum_{(i,j)\in\mathcal P_B}JSD(P_i,P_j),
\]

\[
FamilySeparationJS=BetweenFamilyJS-WithinFamilyJS.
\]

For local thresholds \(\tau_k\), report the mean within-family threshold SD over families with at least two eligible members,

\[
WithinFamilyThresholdSD
=\frac{1}{|\mathcal F_{\ge2}|}
\sum_{f\in\mathcal F_{\ge2}}
SD(\{\tau_k:k\in f\},ddof=1),
\]

and the SD of family-mean thresholds,

\[
BetweenFamilyThresholdSD
=SD(\{\overline\tau_f:f\in\mathcal F\},ddof=1).
\]

Singleton families remain listed but do not enter `WithinFamilyThresholdSD`. A non-positive `FamilySeparationJS` is a valid finding and blocks any claim that physical family is a natural score-sharing unit.

**7.3 Per-client score-distribution explanation**

**Scientific role**

**Mechanism analysis.**

**Question**

Why does LOCAL_THRESHOLD reduce FPR dispersion yet sometimes lower P10 Macro-F1?

**Procedure**

For all nine NBAIOT_NATURAL_DEVICES clients:

- plot held-out benign reconstruction-error CDFs;
- plot held-out attack reconstruction-error CDFs;
- overlay SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD thresholds;
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

**7.4 Heterogeneity–benefit association and decision surface**

**Scientific role**

**Mechanism association.**

**Question**

Does benign score-distribution heterogeneity predict the magnitude of the local-threshold benefit, and how does that relationship interact with calibration support?

**Locked Jensen–Shannon construction**

For every fixed score artifact, create one common 64-bin histogram grid from the pooled eligible benign **calibration** scores using type-7 pooled quantiles at probabilities

\[
\left\{0,\frac{1}{64},\frac{2}{64},\ldots,1\right\}.
\]

Collapse duplicate adjacent edges. If fewer than two non-zero-width bins remain, JSD is unavailable for that cell. Every client's histogram uses the exact same edges and is normalized to probability vector \(P_k\).

For probability vectors \(P\) and \(Q\), with \(M=(P+Q)/2\), use base-2 logarithms:

\[
JSD(P,Q)
=\frac{1}{2}KL_2(P\|M)+\frac{1}{2}KL_2(Q\|M),
\]

where

\[
KL_2(P\|M)=\sum_{b:P_b>0}P_b\log_2\frac{P_b}{M_b}.
\]

Thus `JSD in [0,1]`. No pseudocount is added. The federation-level heterogeneity summary is the unweighted mean pairwise JSD:

\[
H
=\frac{2}{K_e(K_e-1)}\sum_{i<j}JSD(P_i,P_j).
\]

**Primary association procedure**

For each valid population/seed unit:

- calculate `H` from benign calibration scores only;
- calculate the SHARED_THRESHOLD–LOCAL_THRESHOLD FPR-equity gain \(\Delta CV=CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}\);
- plot both;
- report Spearman correlation;
- report all points, not only population means;
- include leverage/influence diagnostics.

**Natural-device leave-one-device-out mechanism influence**

Because NBAIOT_NATURAL_DEVICES contains only nine physical clients, the heterogeneity mechanism must show whether one device dominates the measured `H` or the association. This is a nested influence diagnostic, not additional independent evidence.

For each seed `s` and physical device `j`:

1. remove device `j` from the eligible calibration/evaluation population only;
2. do **not** retrain the detector, refit preprocessing, or regenerate scores;
3. rebuild the common 64-bin JSD grid from the pooled benign calibration scores of the remaining clients using the same quantile-edge rule above;
4. recompute `H_(s,-j)` on the remaining clients;
5. recompute the shared threshold from the remaining eligible clients and recompute `CV(FPR)_shared,(s,-j)` over those clients;
6. retain each remaining client's original local threshold and recompute `CV(FPR)_local,(s,-j)` over the same reduced client set;
7. compute

\[
\Delta CV_{s,-j}=CV(FPR)_{shared,s,-j}-CV(FPR)_{local,s,-j}.
\]

Let `D` be the full collection of valid `(population,seed)` points used for the primary Spearman association and let `rho_full` be that association. For device `j`, construct `D_(-j)` by replacing only NBAIOT_NATURAL_DEVICES points with their recomputed `(H_(s,-j), DeltaCV_(s,-j))` values; every other population/seed point remains unchanged. Compute `rho_(-j)` on `D_(-j)` and report

\[
MaxLODORhoShift=\max_j|\rho_{-j}-\rho_{full}|.
\]

Also report `min_j rho_(-j)`, `max_j rho_(-j)`, and the count of the nine `rho_(-j)` values with the same sign as `rho_full`. The 90 nested `(seed,device)` values are never treated as 90 independent observations and never enter a p-value as independent samples.

**Locked heterogeneity × calibration-support interaction**

Use only the predeclared population-C subset:

```text
alpha in {0.1, 1.0, IID}
m in {50, 100, 500, full}
policies = {SHARED_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD, fixed-lambda curve, size-aware shrinkage}
finite-m nested replicates = 10 per training seed
training seeds = the same ten-seed campaign cohort
```

For each `(seed, alpha)`, compute \(H_{s,\alpha}\) once from the **full source calibration pools** so that the heterogeneity covariate itself is not changed by the experimental `m` subsampling. For `m in {50,100,500}`, use the same fixed-cohort and deterministic nested-subsampling rules as §8.1. `full` is reported as a fourth descriptive column but is excluded from the following numerical interaction regression because it has no common finite `m` value.

Within each training seed, fit the pre-specified descriptive model across the nine finite `(alpha,m)` cells:

\[
\Delta CV_{s,\alpha,m}
=\beta_{0,s}
+\beta_{1,s}H_{s,\alpha}
+\beta_{2,s}\log_{10}(m/100)
+\beta_{3,s}H_{s,\alpha}\log_{10}(m/100)
+\varepsilon_{s,\alpha,m}.
\]

The interaction coefficient \(\beta_{3,s}\) describes whether the heterogeneity–benefit association changes with calibration support. The ten seed-level coefficients are then summarized across seeds; any confidence interval on their mean is secondary BCa evidence. No individual `(alpha,m)` cell is promoted because it is favorable.

**Empirical policy-selection surface — descriptive, not learned**

For each predeclared `(alpha,m)` cell, show the measured `H`, `CV(FPR)`, P10 Macro-F1, worst-client balanced accuracy, and the set of Pareto-nondominated policies under the two primary directions

```text
minimize CV(FPR)
maximize P10 Macro-F1
```

using the policies already authorized for the interaction grid. Policy `p` dominates policy `r` in a cell when

\[
CV_p\le CV_r,
\qquad
P10F1_p\ge P10F1_r,
\]

with at least one strict inequality. No scalar weighting is introduced.

Every cell receives exactly one typed surface state:

```text
UNIQUE_<POLICY_ID>          # exactly one nondominated policy
MULTIPLE_NONDOMINATED      # two or more nondominated policies
UNAVAILABLE_NO_VALID_CV    # CV(FPR) is unavailable on the common population
UNAVAILABLE_NO_COMMON_ATTACK_UTILITY  # P10 Macro-F1 unavailable on the common population
```

For finite `m`, the manuscript-facing surface uses x=`H` and y=`log10(m/100)`; the `full` cell is shown as a separate aligned column because it has no common finite `m`. Every point is annotated with its `(alpha,m)` identity and typed state. A supplementary table contains the raw policy metrics so the state can be reconstructed exactly.

Do **not** fit a classifier, decision tree, regression boundary, policy-learning algorithm, or optimized cutoff from these cells. Do **not** invent universal numerical rules such as “if `H>x`, choose local.” The surface is a descriptive map over the tested populations/support levels, intended to show where shared, local, cluster, or shrinkage policies are empirically nondominated—not a production policy or causal treatment rule.

**Interpretation**

A strong relationship supports a heterogeneity-conditioned interpretation. A weak relationship is a real result and prevents using JS divergence as a sufficient predictor. A material interaction supports calibration-support-conditioned wording. All language remains associative, not causal.

**7.5 Threshold movement versus operating-point harm**

**Scientific role**

**Mechanism analysis.**

**Question**

How does the client-specific threshold shift from SHARED_THRESHOLD to LOCAL_THRESHOLD relate to changes in false positives and attack detection?

**Procedure**

For every NBAIOT_NATURAL_DEVICES device and seed, compute:

\[
\Delta \tau_k = \tau_{\mathrm{local},k} - \tau_{\mathrm{shared}}
\]

\[
\Delta FPR_k = FPR_{\mathrm{local},k} - FPR_{\mathrm{shared},k}
\]

\[
\Delta TPR_k = TPR_{\mathrm{local},k} - TPR_{\mathrm{shared},k}
\]

Display:

- threshold shift versus FPR change;
- threshold shift versus TPR change;
- device labels;
- seed uncertainty;
- all nine clients without filtering.

For each seed, also report exact direction counts over the common evaluable device set:

\[
N^{FPR}_{down,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}<0],\quad
N^{FPR}_{same,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}=0],\quad
N^{FPR}_{up,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}>0],
\]

and, where attack-sensitive TPR is valid,

\[
N^{TPR}_{down,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}<0],\quad
N^{TPR}_{same,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}=0],\quad
N^{TPR}_{up,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}>0].
\]

Because SHARED_THRESHOLD and LOCAL_THRESHOLD use the identical held-out rows, FPR equality can be checked from identical false-positive counts and TPR equality from identical true-positive counts; no floating-point tolerance or post-hoc “material change” cutoff is introduced. Report all ten seed-level count triples and their median across seeds; do not pool the `9 × 10` device-seed cells as 90 independent observations.

**Interpretation**

This experiment quantifies the equity–sensitivity trade-off surface. It does not claim that threshold movement alone explains every detection change.

---

**7.5A Calibration support versus shared-threshold burden**

**Scientific role**

**Descriptive mechanism diagnostic; not a causal or confirmatory endpoint.**

**Question**

Are clients with different amounts of source benign calibration support systematically associated with different SHARED_THRESHOLD false-positive burden or different FPR relief from LOCAL_THRESHOLD?

For every NBAIOT_NATURAL_DEVICES training seed `s` and eligible FPR-evaluable client `k`, define

\[
S_{s,k}=n_{s,k,source},
\]

\[
SharedTargetBurden_{s,k}=FPR_{shared,s,k}-(1-q),
\]

and

\[
PersonalizationRelief_{s,k}=FPR_{shared,s,k}-FPR_{local,s,k}=-\Delta FPR_{s,k}.
\]

Positive `SharedTargetBurden` means the shared threshold produces held-out benign FPR above the nominal target. Positive `PersonalizationRelief` means LOCAL_THRESHOLD lowers that client's FPR relative to SHARED_THRESHOLD.

Within each training seed compute exactly two nonredundant Spearman rank correlations across the common valid client set:

\[
\rho^{support,FPR}_s
=Spearman(S_{s,k},FPR_{shared,s,k}),
\]

\[
\rho^{support,relief}_s
=Spearman(S_{s,k},PersonalizationRelief_{s,k}).
\]

`SharedTargetBurden` differs from `FPR_shared` only by the seed-invariant constant `(1-q)`, so its Spearman correlation with support is exactly the same as `\rho^{support,FPR}_s` and is not counted as a third statistic.

For any valid pair of variables `x_k,y_k`, ties use average ranks `R(x_k),R(y_k)` and Spearman correlation is computed as the ordinary Pearson correlation of those ranks:

\[
Spearman(x,y)=
\frac{\sum_k(R(x_k)-\overline{R_x})(R(y_k)-\overline{R_y})}
{\sqrt{\sum_k(R(x_k)-\overline{R_x})^2}\sqrt{\sum_k(R(y_k)-\overline{R_y})^2}}.
\]

A coefficient is available only when at least `5` common clients are valid and both ranked variables have at least two distinct values; otherwise emit `INSUFFICIENT_EVIDENCE` or `UNDEFINED_CONSTANT_INPUT` as appropriate. Do **not** compute a client-level inferential p-value from `K=9`.

Reporting is locked to:

- all client `n_k_source` values;
- a scatter plot with x=`log10(n_k_source)` and y=`FPR_shared` plus a second y=`PersonalizationRelief`; the log transform is visual only and does not change Spearman ranks;
- the ten seed-level `rho` values for `support -> FPR_shared` and `support -> PersonalizationRelief`;
- median, minimum, maximum, and counts of negative/zero/positive `rho` values across valid seeds;
- a per-device table containing `n_k_source`, mean/median SHARED_THRESHOLD FPR across seeds, mean/median `SharedTargetBurden`, and mean/median `PersonalizationRelief`.

A negative `\rho^{support,FPR}` (equivalently, negative support–`SharedTargetBurden` association) is consistent with lower-support clients carrying higher shared-threshold FPR burden. A negative `\rho^{support,relief}` is consistent with lower-support clients receiving greater FPR relief from localization. Positive associations indicate the opposite ordering. Either direction is descriptive only: calibration support is not randomized and may correlate with device distribution. The calibration-size experiment in §8.1 remains the controlled test of finite-support threshold stability.

---

**7.5B Natural-device helped/harmed profile and calibration-support stratification**

**Scientific role**

**Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**

The existing direction counts in §7.5 show whether FPR/TPR moves up or down. This section converts those exact paired client outcomes into a complete **help/harm distribution** so a favorable cross-client average cannot hide a subgroup of devices that becomes worse.

Use the same common eligible/evaluable clients and the same held-out rows as the confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD comparison. Define, for seed `s` and device `k`:

\[
FPRRelief_{s,k}=FPR_{shared,s,k}-FPR_{local,s,k},
\]

\[
TPRChange_{s,k}=TPR_{local,s,k}-TPR_{shared,s,k},
\]

\[
MacroF1Change_{s,k}=MacroF1_{local,s,k}-MacroF1_{shared,s,k},
\]

\[
BAChange_{s,k}=BA_{local,s,k}-BA_{shared,s,k}.
\]

Positive `FPRRelief` is an FPR improvement. Positive values for the other three differences are utility improvements. Equality is exact from the common integer confusion-count inputs where the metric is rationally determined; no arbitrary floating tolerance or “materiality” threshold is introduced.

For every seed, report:

\[
FPRHelpedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}>0],
\]

\[
FPRHarmedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}<0],
\]

\[
FPRUnchangedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}=0].
\]

On the common attack-evaluable client set `K_attack,s`, also report

\[
TPRLossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[TPRChange_{s,k}<0],
\]

\[
MacroF1LossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[MacroF1Change_{s,k}<0],
\]

\[
BALossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[BAChange_{s,k}<0].
\]

The FPR-versus-TPR paired categories are:

```text
PARETO_IMPROVED:              FPRRelief > 0 and TPRChange >= 0
PARETO_HARMED:                FPRRelief < 0 and TPRChange <= 0
TRADEOFF_FPR_BETTER_TPR_WORSE: FPRRelief > 0 and TPRChange < 0
TRADEOFF_FPR_WORSE_TPR_BETTER: FPRRelief < 0 and TPRChange > 0
NO_FPR_CHANGE:                FPRRelief = 0   # TPR direction remains separately reported
```

Let `K_attack,s` be the clients for which both FPR and TPR are valid in seed `s`. Compute each category fraction as its client count divided by `|K_attack,s|`. When `|K_attack,s|>0`, the five displayed category fractions must sum to exactly `1` up to floating serialization round-off; persist the integer numerator and denominator for every fraction. When `|K_attack,s|=0`, emit `UNAVAILABLE_NO_COMMON_FPR_TPR_CLIENTS`. Do not discard `NO_FPR_CHANGE` clients or force them into a Pareto category.

For FPR-harmed clients, define the positive harm magnitude

\[
FPRHarmMagnitude_{s,k}=FPR_{local,s,k}-FPR_{shared,s,k}=-FPRRelief_{s,k}>0.
\]

For TPR-lost clients, define

\[
TPRLossMagnitude_{s,k}=TPR_{shared,s,k}-TPR_{local,s,k}=-TPRChange_{s,k}>0.
\]

Within each seed report the median and maximum positive magnitude among harmed/lost clients. If the relevant set is empty, emit `UNAVAILABLE_NO_FPR_HARMED_CLIENTS` or `UNAVAILABLE_NO_TPR_LOSS_CLIENTS`; do not report a fabricated zero magnitude.

Across the ten training seeds, preserve seed as the inferential unit. Report the ten seed-level fractions, their arithmetic mean, median, minimum, and maximum. Additionally, for every physical device `k`, report the descriptive frequencies

\[
FPRHelpFrequency_k=\frac{1}{10}\sum_s\mathbf 1[FPRRelief_{s,k}>0],
\]

\[
FPRHarmFrequency_k=\frac{1}{10}\sum_s\mathbf 1[FPRRelief_{s,k}<0],
\]

For TPR, let `S_k^TPR` be the subset of the ten predeclared seeds in which client `k` has a valid TPR. Define

\[
TPRLossFrequency_k=\frac{1}{|S_k^{TPR}|}\sum_{s\in S_k^{TPR}}\mathbf 1[TPRChange_{s,k}<0].
\]

Persist `|S_k^TPR|` beside the frequency. If `|S_k^TPR|=0`, emit `UNAVAILABLE_NO_VALID_TPR_SEEDS`. These frequencies are descriptive repeated-seed stability summaries; the `9×10` cells are not treated as 90 independent observations.

**Prospectively fixed calibration-support strata**

For `NBAIOT_NATURAL_DEVICES`, the support-stratified help/harm analysis is available only when the confirmatory eligible population contains exactly the expected nine devices. Because source-pool size can vary with the locked split seed, define one **campaign-fixed, outcome-blind support score** for device `k` from the ten predeclared training/split seeds:

\[
SupportScore_k
=\operatorname{median}_{s\in\mathcal S_{train}} n_{s,k,source},
\qquad |\mathcal S_{train}|=10.
\]

This score uses source calibration counts only and must be computed before any threshold-policy metric is inspected. Rank the nine devices by ascending `SupportScore_k`; break exact ties by ascending canonical `client_id`. Freeze the resulting strata for the complete campaign:

```text
LOW_SUPPORT  = SupportScore ranks 1..3
MID_SUPPORT  = SupportScore ranks 4..6
HIGH_SUPPORT = SupportScore ranks 7..9
```

If `K_e != 9`, emit `UNAVAILABLE_EXPECTED_9_ELIGIBLE_NBAIOT_CLIENTS` for this stratum analysis rather than changing bin sizes post hoc.

For each seed `s` and stratum `g`, compute from its three devices:

\[
StratumMeanFPRRelief_{s,g}=\frac{1}{3}\sum_{k\in g}FPRRelief_{s,k},
\]

\[
StratumFPRHelpedFraction_{s,g}=\frac{1}{3}\sum_{k\in g}\mathbf 1[FPRRelief_{s,k}>0],
\]

\[
StratumFPRHarmedFraction_{s,g}=\frac{1}{3}\sum_{k\in g}\mathbf 1[FPRRelief_{s,k}<0],
\]

and the stratum mean absolute held-out target error for SHARED_THRESHOLD and LOCAL_THRESHOLD:

\[
StratumMATE^{p}_{s,g}
=\frac{1}{3}\sum_{k\in g}\left|FPR_{p,s,k}-(1-q)\right|,
\qquad p\in\{shared,local\}.
\]

Summarize each stratum quantity across the same ten seeds by arithmetic mean, median, minimum, and maximum. No client-level p-value and no three-stratum significance test is performed: `n_k_source` is an observed device property, not randomized treatment. The controlled calibration-size experiment in §8.1 remains the causal sensitivity to deliberately reduced local support.

**7.6 N-BaIoT malware-family sensitivity breakdown**

**Scientific role**

**Supportive trade-off analysis.**

On NBAIOT_NATURAL_DEVICES only, compute held-out attack-family recall separately for the two original N-BaIoT malware families, `Mirai` and `BASHLITE`, whenever the client has at least one held-out sample from that family.

For client \(k\) and family \(f\):

\[
TPR_{k,f}
=\frac{TP_{k,f}}{N_{k,f}},\qquad
FNR_{k,f}=1-TPR_{k,f},\qquad
f\in\{Mirai,BASHLITE\}.
\]

For each seed and policy, additionally define the worst supported family-client recall

\[
WorstFamilyClientTPR
=\min_{(k,f):N_{k,f}>0} TPR_{k,f},
\]

and the family macro recall

\[
MacroFamilyTPR_f
=\frac{1}{|K_f|}\sum_{k\in K_f}TPR_{k,f},
\qquad
K_f=\{k:N_{k,f}>0\}.
\]

Report:

- every available `TPR_{k,f}` and `FNR_{k,f}`;
- `MacroFamilyTPR_f` for Mirai and BASHLITE separately;
- `WorstFamilyClientTPR` and the exact `(client,family)` that attains it;
- SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD differences;
- the support count \(N_{k,f}\) for every reported value.

A reduction in `CV(FPR)` must never be described as an unqualified operating improvement when it is accompanied by a material deterioration in the displayed family-specific recall outcomes. No post-hoc numeric deterioration cutoff is invented; the exact paired seed/client/family changes are shown and discussed alongside the equity result.

Named sub-attack categories may be shown only as supplementary outcomes when their source labels are preserved and the held-out support is non-zero. Family/sub-attack results never select `q`, `lambda`, cluster count, or policy.

**7.7 Equity–utility Pareto analysis**

**Scientific role**

**Supportive synthesis; no scalarized winner.**

The primary Pareto panel uses NBAIOT_NATURAL_DEVICES, canonical `q=0.95`, and the same ten-seed evidence. For each method, x is lower-is-better `CV(FPR)` and y is higher-is-better `P10(MacroF1)`:

```text
SHARED_THRESHOLD
exact pooled benign quantile
sample-weighted shared threshold
FEDERATED_KLL_SHARED_THRESHOLD(k=400)
FEDERATED_BENIGN_SUMMARY_THRESHOLD
FAMILY_THRESHOLD
CLUSTER_THRESHOLD(K=3)
LOCAL_THRESHOLD
lambda in {0, 0.25, 0.50, 0.75, 1.00}
size-aware shrinkage
```

Method \(A\) Pareto-dominates \(B\) iff

\[
CV_A\le CV_B,\qquad P10_A\ge P10_B,
\]

with at least one strict inequality. The nondominated set is the complete result; no weighted sum of equity and utility is introduced.

For the main panel, each method's plotted x and y coordinates are the arithmetic means of its ten valid seed-level values. Show a 95% BCa interval for each coordinate as **secondary descriptive uncertainty** when defined; Pareto membership itself is determined from the two arithmetic-mean coordinates, not from overlap/non-overlap of confidence intervals. Seed-level points remain available behind the mean/interval display.

A second mandatory robustness panel uses the same x-coordinate but replaces the utility axis with `WorstBA`:

```text
x = mean seed-level CV(FPR)          # lower is better
y = mean seed-level WorstBA         # higher is better
```

The same Pareto-dominance definition applies. The P10-Macro-F1 panel remains the primary equity–utility view; the WorstBA panel exists to prevent an acceptable lower-tail macro-F1 value from hiding one client with poor balanced accuracy.

Every method in the primary panel must also have an accompanying target-attainment row containing, at minimum, `MeanAbsoluteTargetError`, `WorstAbsoluteTargetError`, and `MeanAbsoluteCalibrationGeneralizationGap`. These diagnostics do not enter Pareto dominance; they explain whether the displayed equity point corresponds to a well-transferred held-out operating target.

Where attack-sensitive metrics are unavailable, such as the Edge benign-only client assignment, the Pareto panel is unavailable rather than substituting another y-axis post hoc.

Quantile-sensitivity Pareto panels may appear only as supplementary facets; they do not replace the canonical q=0.95 panel.

### 8. Calibration robustness programme

**8.1 Calibration-size ablation**

**Scientific role**

**Boundary condition and threshold-variant support.**

**Question**

How much benign calibration data is required before local thresholds become stable, and at what support levels does finite-sample local-threshold variance become large relative to the distribution-mismatch cost of a shared threshold?

This experiment operationalizes the pooling bias–variance hypothesis in Part I §5.2. It does not estimate the unknown population quantile `tau_k^*`; instead it jointly reports the locked full-calibration shared/local distance, subsampling variance, `Bias_tau`, `RMSE_tau`, held-out target error, and calibration-to-held-out generalization gap.

**Two distinct calibration-size quantities**

`n_k_source` is client `k`'s benign calibration support before any experimental subsampling (Part I §3.3, locks canonical eligibility at `n_k_source >= 100`). `m` is the calibration sample size drawn for this ablation. Canonical eligibility is fixed from `n_k_source` before this experiment subsamples anything and is never recomputed from `m`.

**Calibration-size grid**

```text
m in {50, 100, 250, 500, 1000, 5000}
```

**Feasibility rule**

A `(client, m)` experimental cell is feasible only when:

```text
n_k_source >= m
```

The `m = 50` condition is an explicit **sample-starved supportive/diagnostic condition**, deliberately below the canonical deployment-support requirement of `n_k_source >= 100`. It does not redefine canonical eligibility to 50, and it does not enter the sole confirmatory shared-versus-local endpoint.

**Fixed-cohort comparator discipline**

Within one `m` condition:

- every compared threshold policy receives the same client cohort;
- every compared threshold policy starts from the same source calibration records for that client;
- deterministic subsampling is policy-independent;
- eligibility/feasibility cannot vary by threshold policy.

For cross-size population-level comparisons intended to estimate calibration-size effects, use the intersection of clients feasible across every size directly compared. Size-specific cohorts (all clients feasible at one size, without cross-size intersection) may additionally be reported descriptively only when their coverage and client count are explicit and they are not presented as fixed-cohort calibration-size comparisons.

**Repetition**

Each subsample size must use multiple deterministic subsampling replicates nested within each training seed. Subsampling replicates quantify calibration sampling variability; they are not counted as independent training seeds.

**Locked replicate count (`CALIBRATION_SUBSAMPLE_REPLICATE_COUNT`, prospective research amendment).** Each subsample size uses exactly `10` deterministic nested replicates per `(training_seed, client)`. The exact SHA-256 → PCG64 seed derivation, immutable-row ordering, one-permutation-per-replicate construction, and prefix nesting across `m` are defined in §2.3A. Replicates are always summarized within seed before any across-seed inference (Part III §12.5); they are never treated as an independent inferential unit and never increase the seed count.

**Comparison set**

- SHARED_THRESHOLD;
- LOCAL_THRESHOLD;
- CLUSTER_THRESHOLD;
- complete fixed-lambda shrinkage curve `{0, 0.25, 0.50, 0.75, 1.00}`;
- prospectively locked size-aware shrinkage;
- LOCAL_CONFORMAL_THRESHOLD where its finite-sample rule is valid.

**Procedure**

For every seed, client, size `m`, and subsample replicate:

1. verify `(client, m)` feasibility (`n_k_source >= m`);
2. draw `m` benign calibration records without replacement from that client's source pool;
3. compute the declared thresholds;
4. evaluate on the unchanged held-out test set;
5. record threshold variance across subsamples;
6. record held-out FPR target error and the calibration-to-held-out benign generalization gap from Part III §4.8, using the exact subsampled calibration scores that constructed the threshold and the unchanged held-out benign evaluation rows;
7. define each client's full-calibration local threshold \(\tau^{full}_{s,k}\) as the fixed reference and calculate, over the `R=10` nested subsamples,

\[
Bias_\tau(s,k,m)
=\frac{1}{R}\sum_{r=1}^{R}\left(\tau_{s,k,m,r}-\tau^{full}_{s,k}\right),
\]

\[
RMSE_\tau(s,k,m)
=\sqrt{\frac{1}{R}\sum_{r=1}^{R}\left(\tau_{s,k,m,r}-\tau^{full}_{s,k}\right)^2};
\]

8. calculate threshold-order inversion against the full-calibration local thresholds. For every comparable client pair `(i,j)` whose full-calibration thresholds are unequal, a replicate is inverted when

\[
(\tau_{i,m,r}-\tau_{j,m,r})(\tau^{full}_{i}-\tau^{full}_{j})<0.
\]

Pairs tied in either comparison are reported as ties and excluded from the inversion-rate denominator;
9. record the mean absolute LOCAL_THRESHOLD-to-SHARED_THRESHOLD threshold distance

\[
MeanLocalSharedDistance
=\frac{1}{K_e}\sum_k|\tau_{\mathrm{local},k}-\tau_{\mathrm{shared}}|;
\]

10. record `CV(FPR)`, worst-client FPR, IQR, range, P10 Macro-F1, and balanced accuracy over the fixed-cohort intersection defined above for cross-size comparisons;
11. report clients infeasible at each size, with the reason.

**Interpretation**

**Graceful degradation**
LOCAL_THRESHOLD remains stable as calibration shrinks.

**Shrinkage benefit**
Naive LOCAL_THRESHOLD destabilizes while shrinkage reduces variance without erasing most personalization.

**Sample-starved boundary**
Local thresholds become unreliable below a clear range. The `m = 50` cell is always this sample-starved supportive/diagnostic condition, never a canonical eligibility redefinition.

**No sample-size effect**
Threshold stability changes little over the tested grid.

The result cannot be summarized using only the best-performing calibration size.

**8.1A Calibration cold-start / onboarding boundary**

**Scientific role**

**Deployment boundary, never confirmatory.**

This experiment asks how existing threshold scopes behave while one already-modelled client accumulates benign calibration evidence. It is **not** unseen-device generalization because the detector was trained under the ordinary NBAIOT_NATURAL_DEVICES population.

For each of the nine NBAIOT_NATURAL_DEVICES clients in turn, designate that client as the onboarding target and retain all other clients' full source calibration pools. Use:

```text
target calibration m in {0, 10, 25, 50, 100}
10 deterministic nested replicates for m in {10, 25, 50, 100}
m = 0 has no subsampling replicate
```

Rules at `m = 0`:

- target LOCAL_THRESHOLD is `UNAVAILABLE_NO_LOCAL_CALIBRATION`;
- target CLUSTER_THRESHOLD is `UNAVAILABLE_NO_FINGERPRINT`;
- leave-target-out SHARED_THRESHOLD is formed from all other eligible clients and applied to the target;
- leave-target-out FAMILY_THRESHOLD is formed from other eligible members of the target's locked physical family when at least one exists;
- when no other eligible same-family client exists, FAMILY_THRESHOLD explicitly falls back to leave-target-out SHARED_THRESHOLD and records `family_fallback = true`.

Rules at `m > 0`:

- the target's `m` benign records are the only target calibration records supplied to SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD;
- other clients retain their full calibration support;
- CLUSTER_THRESHOLD recomputes the target fingerprint from exactly the `m` target scores and uses the canonical `K=3` construction; if any of `mean`, sample standard deviation, skewness, or p95 is non-finite for that target sample, the CLUSTER_THRESHOLD target result is `UNAVAILABLE_NONFINITE_FINGERPRINT` and no imputation/zero replacement is permitted;
- all policies use the same target subsample within a replicate;
- the held-out test set remains unchanged.

Primary target-level outputs are target FPR, signed/absolute target-FPR error, threshold value, threshold RMSE versus the target's full-calibration LOCAL_THRESHOLD threshold, and attack-sensitive controls where available. The mixed-population `CV(FPR)` may be shown secondarily but cannot be interpreted as a pure calibration-size effect because only one target client's support is manipulated at a time.

The experiment may identify an onboarding boundary or fallback behavior; it does not change the canonical `n_k_source >= 100` primary-analysis eligibility rule.

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

Using the same NBAIOT_NATURAL_DEVICES scores:

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

The fixed rule is `lambda(n_k_used) = n_k_used / (n_k_used + 100)`, with 100 inherited from canonical minimum benign support. `n_k_source` remains the complete pre-subsampling support used for eligibility and feasibility, while `n_k_used` is the exact score count used in the local threshold construction. The rule is deterministic, bounded in `[0,1]`, strictly increasing in positive `n_k_used`, independent of all evaluation evidence and downstream metrics, evaluated over the same calibration-size subsamples, and compared with the full fixed-lambda curve and its shared/local endpoints without selection by test outcome.

**Interpretation**

This is an engineering threshold variant, not a new statistical estimator claim.

**8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic**

**Scientific role**

**Supportive response to the “equalized by construction” critique.**

**Question**

Does a finite-sample-adjusted local conformal quantile achieve the intended benign coverage on held-out data, and does cross-client FPR dispersion remain lower than under a shared threshold?

**Procedure**

For every eligible NBAIOT_NATURAL_DEVICES client and seed:

1. use only the declared benign calibration scores;
2. compute the finite-sample conformal quantile at `alpha = 0.05`;
3. evaluate benign coverage on held-out benign scores;
4. report coverage error per client and seed;
5. evaluate attack-sensitive metrics only on held-out attack scores;
6. compare LOCAL_CONFORMAL_THRESHOLD with LOCAL_THRESHOLD and SHARED_THRESHOLD;
7. report results at small calibration sizes where rank granularity is material.

**Required outcomes**

- target coverage;
- achieved marginal benign coverage;
- coverage error;
- per-client coverage distribution;
- `CV(FPR)`;
- threshold difference from LOCAL_THRESHOLD;
- detection-quality controls;
- finite-sample discreteness diagnostics.

**Interpretation**

LOCAL_CONFORMAL_THRESHOLD can show that the threshold rule is evaluated through held-out coverage rather than assumed to equalize test FPR by construction.

It does not prove client-conditional validity under arbitrary non-IID shift. Exchangeability limitations must remain explicit.[^split-conformal][^fed-conformal-heterogeneity]

---

**8.5 Bounded preprocessing-geometry sensitivity**

**Scientific role**

**Supportive causal-boundary test.**

NBAIOT_NATURAL_DEVICES is rerun under exactly two named preprocessing protocols already defined by this roadmap:

```text
FEDERATED_CLIENT_LOCAL_STANDARD   # confirmatory protocol
FEDERATED_POOLED_MIN_MAX         # supportive alternative
```

Each preprocessing protocol receives its own independently fitted preprocessing state and independently trained FedAvg detector for every training seed. No detector or score artifact is reused across preprocessing protocols.

Within each fixed `(seed, preprocessing_protocol)` detector, evaluate only SHARED_THRESHOLD and LOCAL_THRESHOLD plus the mechanism controls needed to interpret the result:

- `CV(FPR)`, IQR, range, worst-client FPR;
- held-out target-FPR error;
- AUROC and average precision from that detector's canonical score artifact;
- mean pairwise benign-score JSD `H`;
- SHARED_THRESHOLD–LOCAL_THRESHOLD scope gain

\[
\Delta_{scope,preproc}
=CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}.
\]

Differences **within** a preprocessing protocol remain threshold-scope comparisons. Differences **between** preprocessing protocols are supportive sensitivity evidence because preprocessing changes the learned detector geometry. FedBN is relevant prior art for the broader principle that local normalization/state can mitigate feature-shift heterogeneity, but it is **not** implemented here because introducing BatchNorm would alter DATP's locked autoencoder architecture.[^fedbn] A reduction of the DATP effect under pooled MinMax must be reported and cannot trigger replacement of the confirmatory client-local StandardScaler protocol.

For each seed `s`, define

\[
\Delta^{localStd}_s
=CV(FPR)_{shared,s,localStd}-CV(FPR)_{local,s,localStd},
\]

\[
\Delta^{pooledMinMax}_s
=CV(FPR)_{shared,s,pooledMinMax}-CV(FPR)_{local,s,pooledMinMax}.
\]

When `Delta_localStd[s] > 1e-12`, report the un-clipped preprocessing-absorption diagnostic

\[
PreprocessingAbsorption_s
=1-\frac{\Delta^{pooledMinMax}_s}{\Delta^{localStd}_s}.
\]

`0` means no attenuation of the threshold-scope gain, `1` means the pooled-MinMax detector has zero shared/local gap, `<0` means the alternative preprocessing increases the gap, and `>1` means the shared/local ordering reverses under pooled MinMax. If the confirmatory-protocol denominator is `<=1e-12`, record `UNAVAILABLE_NO_POSITIVE_LOCAL_STANDARD_GAP`. This diagnostic is descriptive and does not authorize selecting preprocessing from the result.

**8.6 Shared-calibration contributor availability sensitivity**

**Scientific role**

**Supportive operational sensitivity on fixed detector and scores.**

**Question**

How sensitive is a federation-wide shared threshold to missing client calibration summaries when all clients still retain their own local calibration evidence and remain in the evaluation population?

**Population and causal lock**

Use `NBAIOT_NATURAL_DEVICES` only. For seed `s`, let `E_s` be the fixed eligible client set and `K_s=|E_s|`. This experiment does **not** simulate FL training dropout, client unavailability during optimization, or loss of local calibration data. Every client keeps its original calibration scores, LOCAL_THRESHOLD, test scores, and test labels. The only intervention is that a declared subset does not contribute its local q95 summary to construction of the shared threshold.

**Locked omission grid**

```text
omitted_shared_contributors m in {0,1,2,3,4}
minimum_remaining_shared_contributors = 5
subset rule = exhaustive over every subset U subset E_s with |U|=m
q = 0.95, type-7, unchanged
local thresholds = unchanged for all eligible clients
shared-threshold evaluation population = all E_s, including omitted contributors
```

A value of `m` is executed only when `K_s-m >= 5`; otherwise the cell is `UNAVAILABLE_TOO_FEW_REMAINING_CONTRIBUTORS`. For the expected nine-client confirmatory population, the exact number of omission subsets per seed is

\[
\sum_{m=0}^{4}\binom{9}{m}
=1+9+36+84+126
=256.
\]

No stochastic subset sampling is used when exhaustive enumeration is feasible.

For omitted set `U`, construct

\[
\tau^{shared}_{s,U}
=\frac{1}{K_s-|U|}
\sum_{k\in E_s\setminus U}
Q_7(E^{cal}_{s,k},0.95).
\]

Apply `tau_shared[s,U]` to the held-out evaluation scores of **every** client in `E_s`, including clients in `U`. The local comparator is invariant to `U`:

\[
\tau^{local}_{s,k}=Q_7(E^{cal}_{s,k},0.95).
\]

For every subset calculate:

\[
SharedThresholdShift_{s,U}
=\tau^{shared}_{s,U}-\tau^{shared}_{s,\emptyset},
\]

\[
\Delta CV_{s,U}
=CV(FPR)^{shared}_{s,U}-CV(FPR)^{local}_{s},
\]

plus `MeanFPR`, `IQR(FPR)`, `Range(FPR)`, `WorstFPR`, `MeanAbsoluteTargetError`, `WorstAbsoluteTargetError`, P10 Macro-F1, and WorstBA where attack metrics are valid.

For each `(seed,m)`, summarize the exhaustive subset distribution with:

\[
MedianDeltaCV_{s,m}=\operatorname{median}_{|U|=m}\Delta CV_{s,U},
\]

\[
WorstSharedCV_{s,m}=\max_{|U|=m}CV(FPR)^{shared}_{s,U},
\]

\[
MaxAbsoluteThresholdShift_{s,m}
=\max_{|U|=m}|SharedThresholdShift_{s,U}|,
\]

and

\[
PositiveScopeGainRetention_{s,m}
=\frac{1}{\binom{K_s}{m}}
\sum_{|U|=m}\mathbf 1[\Delta CV_{s,U}>0].
\]

Also record the exact omission set producing `WorstSharedCV` and the exact set producing `MaxAbsoluteThresholdShift`. Across the ten training seeds, report arithmetic mean, median, minimum, and maximum of each **seed-level summary**. Any BCa interval is secondary and may use only the ten seed-level summaries. The 256 within-seed omission subsets are dependent sensitivity cells and are never treated as 256 independent observations.

**Interpretation**

This experiment answers only shared-calibration-summary availability. If shared-threshold behavior degrades as contributors are omitted while LOCAL_THRESHOLD is invariant by construction, the result demonstrates an operational dependency of the shared calibration policy on contributor participation. It does not establish robustness to training-time dropout, stragglers, asynchronous FL, or device failure. A null sensitivity is equally reportable.

### 9. Federated threshold-estimation programme

**9.1 Benign summary-statistics comparator**

**Scientific role**

**Mandatory comparator stress test.**

**Question**

Does a matched benign-only federated summary-statistics threshold dominate, match, or underperform DATP’s shared and local threshold scopes?

**Population**

- NBAIOT_NATURAL_DEVICES is mandatory;
- EDGE_SENSOR_CLIENTS is mandatory for benign-FPR outcomes when artifacts are available.

**Comparison set**

- SHARED_THRESHOLD;
- exact pooled benign quantile;
- sample-weighted shared construction;
- LOCAL_THRESHOLD;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD`.

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
- comparison with SHARED_THRESHOLD and LOCAL_THRESHOLD.

**Interpretation**

`FEDERATED_BENIGN_SUMMARY_THRESHOLD` may:

- improve over SHARED_THRESHOLD but remain weaker than LOCAL_THRESHOLD;
- match LOCAL_THRESHOLD;
- dominate LOCAL_THRESHOLD;
- fail to improve over SHARED_THRESHOLD.

Every outcome is reported. The result does not support a faithful Laridi claim because anomalous validation summaries are excluded.[^laridi]

**9.2 KLL federated quantile-sketch shared threshold**

**Scientific role**

**Mandatory shared-estimator control.**

**Question**

Can a mergeable, quantile-native approximation to the pooled benign `q`-quantile achieve the intended shared operating point without transferring raw calibration-score arrays?

**Population**

- NBAIOT_NATURAL_DEVICES mandatory;
- EDGE_SENSOR_CLIENTS benign-equity population mandatory when ready.

**Locked factors**

```text
q = 0.95 canonical
k = 400 canonical
k sensitivity = {200, 800}
KLL input = float64 benign calibration scores
one sketch per eligible client
server merge = all eligible client sketches for the condition
one shared threshold = merged_sketch.quantile(q)
```

KLL is stochastic. Client sketches are always merged in ascending canonical `client_id` order. If the selected implementation exposes a sketch RNG seed, derive it with the §2.3A SHA-256/PCG64 seed contract using `purpose = "KLL"` and identity parts `{dataset_id, population_id, training_seed, client_id, k}`. If the implementation does **not** expose a controllable sketch RNG, lock `KLL_RECONSTRUCTION_REPLICATE_COUNT = 10`: rebuild every client sketch ten times for each `(training_seed,k)`, merge each replicate in the same ascending-client order, and summarize the resulting KLL threshold/rank-error variability within training seed. The exact library version and every serialized sketch artifact are mandatory provenance. KLL reconstruction replicates are nested implementation variability and never count as independent training seeds.

**Comparison set**

- exact pooled type-7 quantile oracle;
- SHARED_THRESHOLD arithmetic mean of local quantiles;
- sample-weighted shared construction;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
- `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`;
- LOCAL_THRESHOLD local.

**Required calculations**

For every seed and comparator:

1. use identical eligible calibration-score evidence;
2. serialize each client sketch and record actual byte length;
3. merge client sketches at the server;
4. obtain \(\tau_{KLL}\) at q=0.95;
5. calculate `EmpiricalRankError = |F_pool(tau_KLL)-0.95|`;
6. calculate absolute and relative threshold error versus the exact pooled type-7 oracle;
7. calculate held-out benign signed/absolute target error;
8. calculate `CV(FPR)`, IQR, range, worst-client FPR, and attack-sensitive controls where valid;
9. record client build time, server merge/query time, upload bytes/client, total upload bytes, and download threshold bytes;
10. repeat for `k={200,800}` as sensitivity without selecting a winner.

The DataSketches reference errors (`1.33%`, `0.68%`, `0.35%` single-sided normalized rank error for `k=200,400,800`) are cited as implementation expectations only; DATP reports its **observed** rank and threshold errors on its score distributions.[^datasketches-kll]

No novel sketch or quantile-estimation theorem is claimed.

**9.3 Fixed-coefficient Laridi sensitivity**

**Scientific role**

**Optional supplementary sensitivity only.**

Fixed coefficient values may be evaluated under the benign-only adaptation:

```text
k in {2.0, 2.5, 3.0}
```

This remains a sensitivity of `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; it must not be labelled `LARIDI_ANOMALY_INFORMED_REFERENCE`.

---

### 10. External validation and applicability boundaries

**10.1 Edge-IIoTset external benign-equity validation**

**Scientific role**

**External validation.**

**Question**

Does the shared-versus-local threshold-scope effect appear on an independent sensor-group-partitioned IoT/IIoT dataset?

**Population**

- EDGE_SENSOR_CLIENTS;
- ten benign sensor-group clients;
- eligible-benign coverage 1.0;
- ten paired seeds where training is feasible.

**Comparison set**

- SHARED_THRESHOLD;
- LOCAL_THRESHOLD;
- CLUSTER_THRESHOLD canonical;
- `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
- quantile sensitivity;
- calibration-size and shrinkage analyses where supported.

FAMILY_THRESHOLD is omitted.

**Procedure**

1. train the FedAvg autoencoder per seed using benign training data;
2. construct the allowed thresholds;
3. evaluate per-client benign FPR;
4. compute cross-client equity metrics;
5. represent attack-sensitive per-client metrics as unavailable;
6. compare the direction and magnitude of SHARED_THRESHOLD–LOCAL_THRESHOLD with NBAIOT_NATURAL_DEVICES without treating the datasets as exchangeable replications.

**Required outcomes**

- eligible-benign coverage;
- per-client benign sample counts;
- SHARED_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD/`FEDERATED_BENIGN_SUMMARY_THRESHOLD` thresholds;
- per-client FPR;
- `CV(FPR)`, IQR, range, and worst-client FPR;
- seed-level SHARED_THRESHOLD–LOCAL_THRESHOLD differences;
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
- run SHARED_THRESHOLD and LOCAL_THRESHOLD on the same scores;
- include CLUSTER_THRESHOLD only if cluster sizes are meaningful;
- report `CV(FPR)`, IQR, range, and worst pseudo-client FPR;
- keep all wording specific to the available pseudo-clients.

**Interpretation**

A null result is not evidence that DATP fails on CICIoT2023’s original physical devices. It is evidence that the available file-defined pseudo-clients do not expose a strong threshold-scope need.

---

### 11. Training-side stress tests

**11.0 Upstream alternative-hypothesis ladder**

Training-side stress tests are not ranked as a new algorithm benchmark. They form an ordered falsification ladder for the alternative explanation that DATP merely compensates for an inadequately adapted detector:

```text
FedAvg reference
  -> FedProx: heterogeneity-aware global optimization
  -> FEDAVG_LOCAL_FINE_TUNING: simple client-local post-training adaptation
  -> Ditto: persistent regularized personalized models during FL
```

The prospectively tested mechanism is

\[
\text{stronger client adaptation}
\Rightarrow
\text{lower benign-score/threshold heterogeneity}
\Rightarrow
\text{smaller }\Delta Scope.
\]

This is a **falsifiable mechanism narrative**, not an assumed monotonic ordering. Each method is evaluated independently with the exact common diagnostics from Part I §7.2B. A null/reversed relationship remains a publishable boundary result; it does not authorize adding another PFL method after inspection.

**11.1 FedProx aggregation stress test**

**Scientific role**

**External aggregation-side stress test.**

**Question**

Does heterogeneity-aware training absorb the SHARED_THRESHOLD–LOCAL_THRESHOLD threshold-scope effect?

**Literature rationale**

FedProx was designed to address systems and statistical heterogeneity by adding a proximal term to local optimization and generalizing FedAvg.[^fedprox] Its inclusion tests whether better training alignment removes the need for post-training threshold personalization.

**Population**

- NBAIOT_NATURAL_DEVICES is mandatory;
- EDGE_SENSOR_CLIENTS benign-equity outcomes are included after EDGE_SENSOR_CLIENTS readiness.

**Factors**

- FedAvg reference;
- FedProx with frozen `mu` grid:
  - `0.001`;
  - `0.01`;
  - `0.1`;
  - `1.0`;
- SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD where valid, and CLUSTER_THRESHOLD.

**Coefficient grid**

Each declared FedProx coefficient is an independent stress-test condition. Every condition trains its own terminal detector and reports its own outcomes. No coefficient is designated as primary or selected from training, calibration, evaluation, external, or stress-test results.

The local objective is locked to

\[
F_k^{prox}(w;w^{(t)},\mu)
=F_k(w)+\frac{\mu}{2}\lVert w-w^{(t)}\rVert_2^2.
\]

All non-proximal training hyperparameters remain identical to the FedAvg reference unless the original algorithm mathematically requires otherwise.

**Procedure**

1. train FedProx models independently from FedAvg for every `mu`;
2. train to the same fixed terminal round;
3. persist the complete round-level training-loss trajectory and any convergence/failure state;
4. persist the broadcast-state identity and compute `L2Drift`, `RMSDrift`, and FedProx `TerminalProxPenalty` for every client-round cell exactly as Part I §7.1A specifies;
5. compute `D_all` and `D_terminal50` for FedAvg and every `mu`, plus every client's terminal-50 median drift;
6. compute seed-level `DriftSuppression[s,mu]` where defined; retain negative values rather than clipping them;
7. produce separate score sets;
8. report terminal benign reconstruction-error mean, median, and IQR per client;
9. compute AUROC and average precision from each model's canonical score artifact where valid;
10. calculate full-score benign heterogeneity `H` using the locked JSD definition and compute `DeltaH[s,mu]` relative to FedAvg;
11. compute every common Part I §7.2B score/threshold-alignment diagnostic and every defined `AlignmentReduction`;
12. evaluate the complete threshold ladder on each trained model;
13. calculate `DeltaScope[s,mu]` and `ScopeAbsorption[s,mu]` relative to FedAvg when the FedAvg denominator is valid;
14. report, for each seed and `mu`, the tuple `(DriftSuppression, DeltaH, H, LocationDispersion, ScaleDispersion, LocalThresholdDispersion, NormalizedSharedLocalThresholdDistance, DeltaScope, ScopeAbsorption)` so a null absorption result can be distinguished from a FedProx condition that barely changed update/score geometry;
15. report SHARED_THRESHOLD and LOCAL_THRESHOLD threshold distributions across clients;
16. report training failure or instability without changing the grid retroactively.

No single `mu` is reported as “best FedProx.” The entire grid is the stress-test result.

**Interpretation**

- retained threshold-scope effect with observed drift suppression;
- retained threshold-scope effect with little/no observed drift suppression;
- partial absorption;
- full absorption;
- opposite effect;
- FedProx non-convergence or instability.

`DriftSuppression <= 0` is reported as `NO_OBSERVED_MEDIAN_DRIFT_SUPPRESSION`; `DriftSuppression > 0` is `OBSERVED_MEDIAN_DRIFT_SUPPRESSION`. These labels are descriptive, not statistical significance or materiality thresholds. No universal claim about FedProx is permitted from the `E=1` DATP stress-test coordinate.

FedProx results do not enter the core causal ladder.

**11.2 Ditto model-personalization stress test**

**Scientific role**

**External model-side personalization stress test.**

**Question**

Does maintaining a personalized model for each client make threshold personalization redundant?

**Literature rationale**

Ditto jointly maintains global and personalized models and was proposed as a general personalized federated-learning framework for statistically heterogeneous clients.[^ditto] It is used here because it can be applied without requiring a hand-defined shared representation/local head split. Current IoT-IDS literature makes this counterfactual reviewer-critical rather than hypothetical: G-PFL-ID evaluates unsupervised personalized federated intrusion detection on IoT-23 and natural-device N-BaIoT,[^gpfli2026] FBID studies adaptive personalized FL under heterogeneous CICIoT2023 and explicit OOD attack conditions,[^fbid2026] and Fed-DTCN couples client-private representation learning with client-specific anomaly thresholds.[^feddtcn2026]

**Comparator-selection rationale.** Ditto is retained for a **causal absorption test**, not because it is claimed to be the newest or strongest IoT IDS. A modern IoT-specific personalized system such as Fed-DTCN changes representation/scoring geometry and threshold deployment jointly, so reproducing it would not isolate whether model personalization alone absorbs the SHARED_THRESHOLD→LOCAL_THRESHOLD effect. Ditto supplies one controlled global-versus-personalized model route while the downstream shared/local threshold comparison remains explicit. G-PFL-ID, FBID, Fed-DTCN, and other PFL-IDS systems are therefore literature counterfactuals, not additional baselines.

**Population**

- NBAIOT_NATURAL_DEVICES is mandatory;
- EDGE_SENSOR_CLIENTS is included for benign-equity outcomes after readiness.

**Primary comparison**

The interpretable 2-by-2 core is:

- FedAvg model with SHARED_THRESHOLD;
- FedAvg model with LOCAL_THRESHOLD;
- canonical Ditto personalized model (`lambda_D = 1.0`) with SHARED_THRESHOLD;
- canonical Ditto personalized model (`lambda_D = 1.0`) with LOCAL_THRESHOLD.

FAMILY_THRESHOLD and CLUSTER_THRESHOLD may be applied as supplementary threshold scopes to the personalized scores.

**Locked personalization grid**

```text
lambda_D in {0.1, 1.0, 2.0}
canonical_lambda_D = 1.0
personalized_local_epochs_per_round = 1
persistent personalized state = required
personalized states aggregated = forbidden
global Ditto path = same FedAvg global-training protocol as the reference
```

For client \(k\), the personalized objective is

\[
F_k^{Ditto}(v_k;w,\lambda_D)
=F_k(v_k)+\frac{\lambda_D}{2}\lVert v_k-w\rVert_2^2.
\]

All three λ conditions train independent persistent personalized states and are reported. Only λ=1.0 determines the locked canonical absorption wording; sensitivity values cannot replace it after inspection.

**Procedure**

1. train genuine Ditto global and persistent personalized states for each locked λ;
2. keep personalized states separate by client and never aggregate them;
3. use the same optimizer, learning-rate, batch, round, and local-epoch semantics as the reference unless Ditto's proximal update explicitly changes the objective term;
4. generate personalized scores separately from all FedAvg artifacts;
5. compute SHARED_THRESHOLD and LOCAL_THRESHOLD from the corresponding personalized score distributions;
6. calculate the threshold-scope gain under FedAvg and canonical Ditto;
7. compute every common Part I §7.2B score/threshold-alignment diagnostic and available `AlignmentReduction` for canonical Ditto and each sensitivity λ;
8. compute AUROC/AP, `CV(FPR)`, worst-client FPR, P10 Macro-F1, and held-out target error;
9. measure persistent personalized-model serialized bytes per client, extra local training wall time relative to FedAvg, and total threshold-stage payload; model-update communication remains separately accounted from local personalized-state storage;
10. preserve all four canonical corners and all sensitivity λ outcomes.

**Absorption measure**

\[
\Delta_{\mathrm{FedAvg}}
=
CV(FPR)_{\mathrm{FedAvg+shared}}
-
CV(FPR)_{\mathrm{FedAvg+local}}
\]

\[
\Delta_{\mathrm{Ditto}}
=
CV(FPR)_{\mathrm{Ditto+shared}}
-
CV(FPR)_{\mathrm{Ditto+local}}
\]

When `Delta_FedAvg > 1e-12`, additionally report the normalized absorption fraction

\[
AbsorptionFraction
=1-\frac{\Delta_{\mathrm{Ditto}}}{\Delta_{\mathrm{FedAvg}}}.
\]

This is exactly the generic `ScopeAbsorption` definition from Part I §7.2B for canonical Ditto (`lambda_D=1.0`); implementations must compute one authoritative quantity and may expose `AbsorptionFraction` only as a manuscript-facing alias.

It is not clipped. `AbsorptionFraction=0` means no absorption; `0.5` means Ditto removes half of the FedAvg shared-to-local gain; `1` means the canonical Ditto shared/local difference is zero; values `<0` mean model personalization amplifies the threshold-scope gain; values `>1` occur when the Ditto shared/local ordering reverses and must be labelled **reversal**, not “more than complete absorption.” If `Delta_FedAvg <= 1e-12`, the normalized fraction is `UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP` and only the raw deltas are interpreted.

Interpretation bands, applied only when `Delta_FedAvg > 1e-12`:

- `AbsorptionFraction <= 0.25` (equivalently `Delta_Ditto >= 0.75 * Delta_FedAvg`): threshold personalization remains strongly useful;
- `0.25 < AbsorptionFraction <= 0.75`: partial absorption;
- `0.75 < AbsorptionFraction <= 1.0`: largely absorbed;
- `AbsorptionFraction > 1.0`: reversed shared/local ordering under Ditto;
- if `CV(FPR)[Ditto+SHARED_THRESHOLD]` is within absolute `0.05` of `CV(FPR)[FedAvg+LOCAL_THRESHOLD]`, model personalization is reported as an alternative route to operating-point equity.

The absorption calculation is performed seed by seed and summarized across the ten paired training seeds; a ratio of campaign-level means is not substituted for the mean/median of valid seed-level absorption fractions.

**Scope boundary**

This is one stress test, not an exhaustive personalized-FL benchmark. APFL, Per-FedAvg, pFedMe, FedRep, FedPer, and broad architecture comparisons are not added to this paper.

---

**11.2A FedAvg post-training client-local fine-tuning stress test**

**Scientific role**

**External simple model-personalization stress test.**

**Question**

Does a simple, literature-backed local adaptation of the terminal FedAvg detector absorb the SHARED_THRESHOLD–LOCAL_THRESHOLD effect without introducing a specialized PFL algorithm?

**Literature rationale**

The peer-reviewed personalized-FL benchmark by Matsuda et al. reports that standard FL with client-local fine-tuning can be highly competitive with dedicated PFL methods.[^matsuda-pfl] Cheng et al. provide a separate primary empirical precedent for fine-tuned FedAvg and use 10 local personalization epochs before evaluation; DATP locks that value prospectively and does not tune it on its anomaly-detection outcomes.[^cheng-ftfa]

**Population**

- `NBAIOT_NATURAL_DEVICES` is mandatory;
- `EDGE_SENSOR_CLIENTS` benign-equity outcomes are included after readiness if the same benign-train/calibration/evaluation separation can be preserved.

**Primary 2-by-2 comparison**

- FedAvg + SHARED_THRESHOLD;
- FedAvg + LOCAL_THRESHOLD;
- `FEDAVG_LOCAL_FINE_TUNING` + SHARED_THRESHOLD;
- `FEDAVG_LOCAL_FINE_TUNING` + LOCAL_THRESHOLD.

The exact fine-tuning optimizer/data/checkpoint contract is inherited from Part I §7.2A. No calibration/test row or attack label may enter fine-tuning.

**Procedure**

1. load the exact seed-matched FedAvg terminal scientific detector at round `200`;
2. for every client, initialize a local copy from those exact weights;
3. instantiate a fresh optimizer and fine-tune for exactly `10` complete epochs on that client's benign **training** partition only;
4. freeze the end-of-epoch-10 client model; no early stopping, validation selection, calibration selection, or aggregation occurs;
5. generate one immutable client-specific calibration score artifact and one immutable client-specific evaluation score artifact;
6. compute SHARED_THRESHOLD and LOCAL_THRESHOLD from those frozen fine-tuned score artifacts;
7. compute AUROC/AP, FPR, `CV(FPR)`, absolute FPR dispersion, TPR, Macro-F1, balanced accuracy, P10 Macro-F1, worst-client BA, held-out target error, and calibration-generalization-gap metrics wherever valid;
8. compute the complete common Part I §7.2B mechanism tuple and every available `AlignmentReduction`;
9. define

\[
\Delta_{FT,s}
=CV(FPR)_{FT+shared,s}-CV(FPR)_{FT+local,s},
\]

and when `Delta_FedAvg,s > 1e-12`,

\[
ScopeAbsorption_{FT,s}
=1-\frac{\Delta_{FT,s}}{\Delta_{FedAvg,s}};
\]

10. retain the value un-clipped and use the same literal interpretation as the generic Part I §7.2B definition: `<0` amplification, `0` no absorption, `(0,1)` partial absorption, `1` zero residual shared/local gain, and `>1` reversal;
11. report per-client serialized fine-tuned-model bytes and **fine-tuning wall time** measured on the same execution machine as the FedAvg reference; post-training local fine-tuning adds no model-update communication round, so communication is reported as `0 additional federated rounds` rather than converted into a speculative network latency;
12. report all ten training seeds. No “best fine-tuning seed” or alternate epoch count may be substituted.

**Interpretation**

Use the exact generic `ScopeAbsorption` bands from Part I §7.2B; do not invent fine-tuning-specific “small”, “material”, or “near zero” cutoffs. In addition, define one campaign-level mechanism-activation label from the five alignment quantities. Let `MeanAlignmentReduction_X` be the arithmetic mean of the valid ten seed-level `AlignmentReduction^X` values for each `X`. Emit

```text
OBSERVED_ALIGNMENT_ACTIVATION
```

if **at least one** available `MeanAlignmentReduction_X > 0`; otherwise emit

```text
NO_OBSERVED_ALIGNMENT_ACTIVATION
```

when every available mean is `<=0`. If all five alignment-reduction quantities are unavailable, emit `ALIGNMENT_ACTIVATION_UNAVAILABLE`. This is a sign-based descriptive label, not a significance or materiality test. The raw quantities remain primary. This stress test cannot replace or rescue the FedAvg confirmatory result.

### 12. Temporal recalibration experiment

**12.1 One-shot recalibration under genuine chronology**

**Scientific role**

**Temporal boundary condition.**

**Question**

When thresholds are calibrated on historical benign behavior, does future benign behavior increase cross-client FPR dispersion, and can one future benign recalibration window recover it?

**Population**

- EDGE_TEMPORAL_CLIENTS;
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

- SHARED_THRESHOLD;
- LOCAL_THRESHOLD;
- CLUSTER_THRESHOLD;
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

**Additional locked client-level temporal diagnostics**

For every client \(k\), also calculate threshold drift

\[
\Delta\tau_k=\tau_{k,\mathrm{recalibrated}}-\tau_{k,\mathrm{historical}},
\]

and FPR deterioration/recovery

\[
FrozenFPRDeterioration_k
=FPR_{k,\mathrm{frozen\\ future}}-FPR_{k,\mathrm{static\\ reference}},
\]

\[
RecoveryFPR_k
=FPR_{k,\mathrm{frozen\\ future}}-FPR_{k,\mathrm{recalibrated\\ future}}.
\]

Calculate client-level benign drift JSD between the historical calibration and future recalibration windows using one 64-bin common quantile grid built from the union of those two benign windows for that client, with the same base-2 JSD formula as §7.4. Report Spearman association between `DriftJS_k` and `FrozenFPRDeterioration_k` within each seed when at least five valid client pairs exist.

Report helped/harmed/unchanged client fractions, with exact zero defining unchanged:

\[
HelpedFraction=\frac{|\{k:RecoveryFPR_k>0\}|}{K_e},\\quad
HarmedFraction=\frac{|\{k:RecoveryFPR_k<0\}|}{K_e}.
\]

Report worst-client recovery:

\[
WorstClientFPRRecovery
=\\max_k FPR_{k,\mathrm{frozen\\ future}}
-\\max_k FPR_{k,\mathrm{recalibrated\\ future}}.
\]

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
- per-client threshold movements `Delta tau_k`;
- per-client `DriftJS_k`;
- per-client frozen deterioration and recovery;
- helped/harmed/unchanged fractions;
- worst-client FPR recovery;
- drift-JS versus FPR-deterioration Spearman summary where available;
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
- use SHARED_THRESHOLD and LOCAL_THRESHOLD at minimum;
- label estimates as estimated when no deployment measurement exists.

**Suppression rule**

When no real or cited rate is available, omit the metric. Do not invent a nominal rate merely to populate a table or figure.

---

**13.2 Threshold-stage communication, storage, and runtime accounting**

**Scientific role**

**Supportive systems characterization only.** It does not establish edge deployment, energy efficiency, network latency, or hardware suitability.

**Payload inventory**

For each policy/comparator, report both the logical fields disclosed and the actual serialized byte count. The actual serializer output is authoritative; the minimum raw-field counts below are explanatory lower bounds before framing/metadata overhead:

| Method | Client → server threshold-stage content | Minimum raw payload before serialization overhead | Server → client content |
|---|---|---:|---|
| SHARED_THRESHOLD | one `float64` local threshold | `8` bytes/client | one `float64` shared threshold (`8` bytes/client or one broadcast payload) |
| LOCAL_THRESHOLD | no threshold summary required centrally for local deployment | `0` bytes/client | `0` |
| FAMILY_THRESHOLD | one `float64` local threshold; family identity only if not already server-known | `8` bytes/client plus family-ID encoding when sent | one family threshold (`8` bytes/client) |
| CLUSTER_THRESHOLD | four `float64` fingerprint fields + one `float64` local threshold | `40` bytes/client | cluster ID + cluster threshold; minimum `4 + 8 = 12` bytes/client when ID is `int32` |
| fixed/size-aware shrinkage | same local-threshold upload needed for the shared component as SHARED_THRESHOLD | `8` bytes/client | shared threshold (`8` bytes/client); local shrinkage computed client-side |
| `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | `uint64 n`, `float64 mean`, `float64 variance`, plus each predeclared `uint64` exceedance count | `24 + 8J` bytes/client for `J` exceedance counters | one shared threshold (`8` bytes/client) |
| `FEDERATED_KLL_SHARED_THRESHOLD` | serialized KLL sketch | measured serialized size; no fixed raw lower bound substituted | one shared threshold (`8` bytes/client) |

If family/cluster metadata are already part of an authenticated population manifest, do not double-count them as per-execution communication; state that they are pre-existing metadata.

**Disclosure inventory**

For every method, explicitly state whether the server observes an individual client's threshold, moments, fingerprint, sketch, family membership, or cluster assignment. “Raw calibration records are not transmitted” is permitted when true. “Private” or “privacy preserving” is forbidden without a formal mechanism.

**Runtime benchmark protocol**

Threshold construction is timed after score arrays are already materialized in memory, so detector scoring and disk I/O are excluded.

```text
warm-up iterations = 5
measured iterations = 20
timer = monotonic high-resolution timer (`perf_counter_ns` equivalent)
reported runtime = median, IQR, and p95 over measured iterations
unit = milliseconds
```

For KLL, client build/serialization and server deserialize/merge/query are reported separately. For SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/FedStats/shrinkage, report client-side construction and server aggregation separately where both exist.

Peak server memory is `peak RSS - pre-operation RSS`, sampled at no slower than 10 ms during the measured operation. If the runtime environment cannot produce reliable RSS sampling, peak memory is `UNAVAILABLE_MEASUREMENT_NOT_SUPPORTED`; Python-only allocator measurements must not be mislabeled as process memory.

Hardware/OS/runtime/library versions are recorded with every timing table. Cross-machine timing comparisons are forbidden.

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

Multiplicity treatment must follow Part III — Evaluation, Statistical Analysis, and Reporting.

## Part III — Evaluation, Statistical Analysis, and Reporting

This part owns metric semantics, inferential units, statistical decision rules, temporal quantities, and reporting discipline. It inherits the scientific identities and eligibility rules from Part I and the experiment-specific designs from Part II.

### 1. Evaluation contract

**1.1 Fixed-score comparison — inherited contract**

The authoritative fixed-detector and fixed-score rules are Part I §§2.1–2.4, especially §2.2.2. Part III does not redefine them. Evaluation must consume the canonical score/label artifact identities established there; serialization tolerance is never a substitute for scientific score identity.

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

This invariant is structurally guaranteed by the mean-squared-error formula used in reconstruction error computation (non-negative by construction; a model collapse to constant output would be caught by the checkpoint validation checksum and CUDA-device requirements). The perturbation-based empirical polarity experiment previously in ``scoring/reconstruction.py`` was removed as redundant with the structural definition and because the additive-perturbation heuristic could admit false-negatives on well-trained detectors. The score semantics remain auditable through the reconstruction-error computation path itself rather than through a manifest field.

---

### 3. Metric populations

**3.1 Calibration eligibility — inherited contract**

The authoritative eligibility definition is Part I §3.3: `n_k_source >= 100`, where `n_k_source` is equivalently the `benign_calibration_count`, determined from the source benign calibration pool before experimental subsampling and held fixed across compared policies. Part II §8.1 separately defines the experimental sample size `m`.

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

AUROC uses continuous anomaly scores and requires both classes. AUROC is computed from the fixed continuous evaluation-score and evaluation-label artifact; threshold-calibration scope is not an AUROC input (Part I §2.2.2).

Within a fixed-score core threshold-scope comparison, AUROC is computed once from the canonical score/label artifact, or is proven to derive from that exact artifact by scientific artifact identity (matching score-artifact identity, ordered row identities, client identities, split identities, detector identity, checkpoint identity, and preprocessing identity) rather than by numerical closeness. A policy-dependent AUROC difference indicates a score/provenance identity failure, not a threshold-scope effect.

AUROC is a model-quality control, not a threshold-policy verdict.

**4.6 Average precision / PR-curve summary**

Average precision (`AP`) is the locked precision–recall summary and is reported as the AUPRC-style detector-quality control. It uses the continuous anomaly score and requires at least one attack-positive evaluation row.

With precision \(P_n\) and recall \(R_n\) at the distinct descending score thresholds, compute the standard step-integral average precision:

\[
AP=\sum_n (R_n-R_{n-1})P_n.
\]

A trapezoidal PR-AUC must not be silently substituted under the same metric name. Within a fixed-score threshold ladder, AP is computed once from the canonical score/label artifact exactly like AUROC. Any SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD-specific AP difference is a provenance failure.

**4.7 Held-out benign target-attainment error**

For any policy targeting quantile \(q\), the nominal held-out benign FPR target is

\[
TargetFPR=1-q.
\]

For FPR-evaluable client \(k\):

\[
SignedTestFPRTargetError_k=FPR_k-(1-q),
\]

\[
AbsoluteTestFPRTargetError_k=|FPR_k-(1-q)|.
\]

Across eligible FPR-evaluable clients report:

\[
MeanAbsoluteTargetError
=\frac{1}{K_e}\sum_k AbsoluteTestFPRTargetError_k,
\]

plus median absolute target error and

\[
WorstAbsoluteTargetError=\max_k AbsoluteTestFPRTargetError_k.
\]

These are held-out operating-point diagnostics. Calibration-set exceedance is not substituted for held-out target attainment.

**4.8 Calibration-to-held-out benign generalization gap**

For every client/policy with a scalar deployed threshold `tau_k` and `n_k_used > 0` benign calibration scores, define the realized calibration exceedance

\[
CalibrationExceedance_k
=\frac{1}{n_{k,used}}
\sum_{i=1}^{n_{k,used}}
\mathbf 1[e^{cal}_{k,i}>\tau_k].
\]

Use strict `>` because the prediction rule declares an anomaly only when the reconstruction error exceeds the threshold. Ties at the threshold are therefore non-anomalous in both calibration and evaluation calculations.

The held-out benign generalization gap is

\[
CalibrationGeneralizationGap_k
=FPR^{test}_k-CalibrationExceedance_k,
\]

with absolute form

\[
AbsoluteCalibrationGeneralizationGap_k
=|CalibrationGeneralizationGap_k|.
\]

Across the common eligible FPR-evaluable client set report:

\[
MeanAbsoluteCalibrationGeneralizationGap
=\frac{1}{K_e}\sum_k AbsoluteCalibrationGeneralizationGap_k,
\]

plus median absolute gap, maximum absolute gap, and the signed client-level gaps.

This diagnostic is mandatory for SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, CLUSTER_THRESHOLD, exact pooled/shared construction controls, the q95-versus-moment estimator sensitivity, and shrinkage policies whenever their threshold can be applied to the same calibration scores. It is descriptive for calibration transfer; it never feeds threshold fitting, model selection, client eligibility, or policy selection.

For `LOCAL_CONFORMAL_THRESHOLD`, the roadmap's conformal coverage diagnostics remain authoritative; this empirical gap may be shown only as an additional descriptive quantity and must not be called a conformal validity guarantee.

**4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**

A predictable reviewer objection is formalized as

```text
H_TAUTOLOGY:
The apparent LOCAL_THRESHOLD FPR benefit is produced trivially because the
same benign observations used to estimate q95 are also used to measure FPR.
```

DATP-Core rejects this explanation by design: calibration and evaluation row identities are disjoint under Part I §3.2, and the integrity gate verifies that no evaluation row enters threshold estimation.

For client `k`, policy `p`, and `q=0.95`, define the already-authorized calibration exceedance

\[
CalibrationExceedance_{k,p}
=\frac{1}{n_{k,used}}\sum_{j=1}^{n_{k,used}}
\mathbf 1[e^{cal}_{k,j}>\tau_{k,p}],
\]

and its nominal calibration-target error

\[
CalibrationTargetError_{k,p}
=CalibrationExceedance_{k,p}-(1-q).
\]

The held-out error is

\[
TestTargetError_{k,p}
=FPR^{test}_{k,p}-(1-q),
\]

which is the same quantity as `SignedTestFPRTargetError` in §4.7. Their transfer difference is

\[
TestTargetError_{k,p}-CalibrationTargetError_{k,p}
=FPR^{test}_{k,p}-CalibrationExceedance_{k,p}
=CalibrationGeneralizationGap_{k,p}.
\]

Therefore even if an empirical local q95 yields calibration exceedance close to `0.05`, it **does not algebraically force** held-out FPR to equal `0.05`. Sampling variation, calibration/evaluation distribution shift, and finite support remain visible in `SignedTestFPRTargetError`, `AbsoluteTestFPRTargetError`, and `CalibrationGeneralizationGap`.

Mandatory confirmatory reporting for SHARED_THRESHOLD and LOCAL_THRESHOLD includes, by client and seed:

- `CalibrationExceedance`;
- `CalibrationTargetError`;
- `SignedTestFPRTargetError`;
- `AbsoluteTestFPRTargetError`;
- `CalibrationGeneralizationGap`.

No p-value is attached to `H_TAUTOLOGY`; it is a **design-level falsification condition**. Any overlap between the calibration and evaluation row-identity sets makes the affected result invalid rather than “supporting” or “rejecting” the hypothesis empirically.

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

**5.2 Sample standard deviation**

\[
\sigma_{FPR}
=
\sqrt{
\frac{1}{K_e-1}
\sum_{k=1}^{K_e}
(FPR_k-\mu_{FPR})^2
}
\]

Use:

```text
ddof = 1
```

Bessel's correction is locked so that the estimator convention matches the
historical DATP metric definition and the locked anchor reference
`[0.647, 0.769]`, which was derived with `ddof = 1`. Reproduction compares the
re-implemented pipeline to that historical reference, so both sides must share
the same estimator; the `sqrt(K_e / (K_e - 1)) = 1.061` convention mismatch
would otherwise bias every reproduction comparison.

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
\frac{\operatorname{std}(TPR_k,ddof=1)}
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

For CLUSTER_THRESHOLD, report:

- cluster size;
- within-cluster threshold spread;
- within-cluster FPR spread;
- across-cluster threshold spread;
- across-cluster mean-FPR spread;
- singleton and empty-cluster status.

Do not conflate these quantities.

---

**5.6 Natural-device help/harm summary semantics**

The Part II §7.5B client-impact profile is a mandatory companion to the confirmatory shared-versus-local result. It uses **paired within-client changes**, never pooled device-seed observations.

A headline statement that LOCAL_THRESHOLD improves operating-point equity is incomplete unless the same result block also reports:

```text
mean FPR
CV(FPR)
IQR(FPR)
range(FPR)
worst-client FPR
TPR
Macro-F1
P10 Macro-F1
worst-client balanced accuracy
FPRHelpedFraction / FPRHarmedFraction
TPRLossFraction
Pareto client-impact fractions
MeanAbsoluteTestFPRTargetError
MeanAbsoluteCalibrationGeneralizationGap
```

where attack-sensitive quantities are reported only on their common valid population. A method is not given a single scalar “winner” label from this bundle.

For the complete N-BaIoT physical-device population, the manuscript/supplement must also show every device's ten-seed `FPRHelpFrequency` and `FPRHarmFrequency`, together with its pre-outcome `n_k_source` and support-stratum identity from Part II §7.5B. This is descriptive client stability evidence; it is not a new independent sample.

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

For calibration-size studies, calculate threshold variation across declared subsampling replicates within client and seed. For `R=10` replicate thresholds `tau_{s,k,m,r}`, define

\[
\bar\tau_{s,k,m}=\frac{1}{R}\sum_{r=1}^{R}\tau_{s,k,m,r},
\]

\[
ThresholdVariance_{s,k,m}
=\frac{1}{R-1}\sum_{r=1}^{R}(\tau_{s,k,m,r}-\bar\tau_{s,k,m})^2,
\]

\[
ThresholdSD_{s,k,m}=\sqrt{ThresholdVariance_{s,k,m}}.
\]

Use the sample-variance denominator `R-1`; do not use population variance (`ddof=0`) under the same metric name. Variance/SD are first computed within `(training_seed, client, m)` and only then summarized across clients/seeds according to the experiment contract.

The complete calibration-size curve is reported using:

- threshold variance across the 10 nested replicates;
- threshold bias versus the full-calibration threshold;
- threshold RMSE versus the full-calibration threshold;
- threshold-order inversion rate and tie rate;
- mean local-to-shared threshold distance;
- held-out signed/absolute target-FPR error;
- `CV(FPR)`;
- worst-client FPR;
- P10 Macro-F1 where available.

All bias/RMSE/inversion calculations are first summarized within training seed. Nested calibration replicates never enter across-seed inference as independent observations.

Subsampling replicates do not increase the seed count.

---

### 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

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

**10.2 Threshold-stage communication**

For every threshold method report:

- logical fields sent per client;
- actual serialized upload bytes/client;
- total uploaded bytes across participating clients;
- actual serialized server response bytes/client and total;
- whether a broadcast payload is counted once on the wire or once per logical recipient;
- number of post-training threshold-communication rounds.

Estimated raw-field bytes and actual serialized bytes must be separate columns.

**10.3 Threshold-stage latency and memory**

Use the locked 5-warm-up / 20-measured-iteration protocol from the experiment catalogue. Report median/IQR/p95 construction time and peak RSS delta, with the exact hardware/runtime identity. Do not combine detector scoring time with threshold construction.

**10.4 Ditto incremental state and compute**

For the model-personalization stress test report:

- serialized global-model bytes;
- serialized persistent personalized-model bytes per client;
- extra persistent state per client relative to FedAvg;
- measured local personalized-training wall time per round and total;
- global-update communication bytes;
- threshold-stage communication bytes.

The result is a relative cost characterization on the experiment host, not an IoT-device deployment benchmark.

### 11. Confirmatory statistical analysis

**11.1 Paired contrast**

For seed \(s\):

\[
\Delta_s
=
CV(FPR)_{\mathrm{shared},s}
-
CV(FPR)_{\mathrm{local},s}
\]

The confirmatory point estimate is the arithmetic mean:

\[
\overline{\Delta}
=
\frac{1}{10}
\sum_{s=1}^{10}\Delta_s
\]

SHARED_THRESHOLD and LOCAL_THRESHOLD are never resampled independently.

**11.1A Relative and robustness-oriented descriptive effect sizes**

The confirmatory estimand remains the **absolute** paired difference \(\Delta_s\). In addition, when `CV(FPR)_{\mathrm{shared},s} > 1e-12`, report the descriptive relative reduction

\[
RelativeCVReduction_s
=\frac{CV(FPR)_{\mathrm{shared},s}-CV(FPR)_{\mathrm{local},s}}{CV(FPR)_{\mathrm{shared},s}},
\]

and `100 * RelativeCVReduction_s` as a percentage. It is unavailable, not zero, when the denominator is `<= 1e-12`.

Also report the absolute paired worst-client and dispersion-support deltas

\[
DeltaWorstFPR_s
=\max_k FPR_{shared,s,k}-\max_k FPR_{local,s,k},
\]

\[
DeltaIQR_s
=IQR(FPR)_{shared,s}-IQR(FPR)_{local,s}.
\]

Positive values favor LOCAL_THRESHOLD. Report their ten seed-level values and arithmetic means as descriptive secondary effects.

Also report the median paired \(\Delta_s\), minimum, maximum, and the full ordered ten-seed vector. None replaces the arithmetic-mean BCa confirmatory rule.

**11.2 BCa confidence interval**

The confirmatory interval is a two-sided 95% BCa bootstrap interval over the ten paired seed-level deltas.

The interval resamples paired seed deltas with replacement, uses the arithmetic mean as its statistic, and calculates bias correction and acceleration from the paired seed data.

**11.3 Degenerate BCa**

If BCa is undefined or unstable because of identical deltas, invalid acceleration, a degenerate bootstrap distribution, or fewer than ten valid pairs, the result is `CONFIRMATORY_INFERENCE_UNAVAILABLE` (Part II — Experiment Programme, §5.3):

- report the paired values and point estimate;
- allow percentile or basic intervals only as diagnostics;
- do not silently substitute another interval for the confirmatory rule;
- report the confirmatory claim as **not established**; never silently convert this outcome to `CONFIRMATORY_SUPPORT` or `NO_OBSERVED_ADVANTAGE`, and never rescue it with a secondary result, another statistical test, or supportive/mechanism/external/stress-test evidence.

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

**12.1A Exact paired sign test**

For the confirmatory shared-versus-local seed-level deltas, let

```text
n_positive = count(Delta_s > 0)
n_negative = count(Delta_s < 0)
n_nonzero  = n_positive + n_negative
```

Zero deltas are discarded for the sign test but remain visible in the sign-consistency counts. Under the null that positive and negative signs are equally likely, `X ~ Binomial(n_nonzero, 0.5)`. The locked two-sided exact p-value is

\[
p_{sign}
=\min\left(1,
2\sum_{x=0}^{\min(n_{positive},n_{negative})}
{n_{nonzero}\choose x}2^{-n_{nonzero}}
\right).
\]

If `n_nonzero = 0`, the test is `UNAVAILABLE_ALL_ZERO_DIFFERENCES`. No normal approximation is used. With the full ten non-zero pairs, the smallest possible two-sided p-value is `2/2^10 = 0.001953125`.

The exact sign test is secondary robustness evidence only. It does not replace or modify the BCa confirmatory decision rule and is not used to add/remove seeds.

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

### 13. Terminal scientific-model protocol

**13.1 Terminal detector**

Every training execution has one terminal scientific detector at the locked terminal round of **200**. Detector weights remain seed-, population-, dataset-, and training-method-specific. The centralized reference remains independent from federated detectors.

**13.2 Recovery and diagnostic checkpoints**

Recovery checkpoints may resume interrupted training only. Diagnostic checkpoints record training observations only. Neither provides a scientific detector, score source, threshold input, evaluation input, or analysis input.

**13.3 Fixed-detector restrictions**

No test metric, attack label, threshold outcome, shared-versus-local effect, external result, stress-test result, or policy-specific performance may alter the terminal detector or cause policy-specific retraining.

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

**Locked temporal decision values (`TEMPORAL_DECISION_PROTOCOL`, prospective research amendment).** `drift_excess_materiality_threshold = 0.05` (`CV(FPR)` units), matching the identical practical-indistinguishability convention already locked for the Ditto absorption comparison (§11: "within `0.05`"), so materiality is judged against the same magnitude this roadmap already treats as scientifically distinguishable rather than an unrelated imported constant. `material_recovery_ratio_minimum = 0.5`: one-shot recalibration must recover at least half of the drift excess to be reported as meaningful recovery, the conventional majority bar in recovery/restoration literature absent a study-specific reason to require more. Both values apply across the locked temporal seed cohort (EDGE_TEMPORAL_CLIENTS, bounded-evidence seeds).

Otherwise:

```text
recovery_ratio = undefined
```

Temporal BCa analysis resamples paired seed records, not rows or windows.

Undefined or unavailable metrics must be reported with their reason; do not substitute zero, an empty value, or an unqualified `NaN`.

---

**14.1 Client-level temporal diagnostics**

In addition to campaign-level `drift_excess` and `recovery_ratio`, persist and report for every valid client:

\[
DeltaTau_k=\tau_{k,recalibrated}-\tau_{k,historical},
\]

\[
FrozenFPRDeterioration_k=FPR_{k,frozen}-FPR_{k,static},
\]

\[
RecoveryFPR_k=FPR_{k,frozen}-FPR_{k,recalibrated}.
\]

`DriftJS_k` uses the locked base-2 JSD formula and 64-bin common quantile grid over that client's historical-calibration plus future-recalibration benign scores. Report within-seed Spearman(`DriftJS_k`, `FrozenFPRDeterioration_k`) only when at least five valid client pairs are present; otherwise record `INSUFFICIENT_EVIDENCE_N_LT_5`.

Helped/harmed fractions and worst-client FPR recovery use the definitions in the temporal experiment catalogue. Exact zero is retained as unchanged rather than forced into either sign.

### 15. Precision and selection discipline

**15.1 Locked ten-seed precision diagnostics**

The confirmatory sample size remains exactly ten independent training seeds and is never expanded or reduced after viewing the confirmatory effect. Precision is reported rather than retroactively “powered” from the observed result.

Let \(s_\Delta\) be the sample SD of the ten paired deltas. Report the descriptive normal-reference standard error

\[
SE_{proxy}=\frac{s_\Delta}{\sqrt{10}},
\]

and reference half-width

\[
H_{normal}=1.96\,SE_{proxy}.
\]

These are precision diagnostics only; the confirmatory interval remains BCa.

For the confirmatory BCa interval \([L_{BCa},U_{BCa}]\), report

\[
BCaWidth=U_{BCa}-L_{BCa}.
\]

Perform leave-one-seed-out influence analysis without changing the inferential sample:

\[
\overline\Delta_{(-j)}
=\frac{1}{9}\sum_{s\ne j}\Delta_s,
\]

\[
MaxLOSOShift
=\max_j|\overline\Delta_{(-j)}-\overline\Delta|.
\]

Report `min_j mean_delta_(-j)`, `max_j mean_delta_(-j)`, and `MaxLOSOShift`. A result dominated by one seed must be described as such even when the confirmatory BCa rule passes.

**15.1A Leave-one-device-out influence for the natural-device confirmatory effect**

This diagnostic tests whether one of the nine N-BaIoT physical devices drives the shared-versus-local result. It operates entirely on the already generated fixed score artifacts. It does **not** retrain the detector, refit preprocessing, regenerate scores, alter the seed cohort, or create eight-device “replications.”

For each seed `s` and physical device `j`:

- remove device `j` from both the threshold-construction and equity-evaluation client populations;
- recompute the SHARED_THRESHOLD from the remaining eligible local q95 thresholds;
- retain every remaining client's previously computed LOCAL_THRESHOLD;
- compute both `CV(FPR)` values on exactly the same remaining client set;
- define

\[
Delta_{s,-j}
=CV(FPR)_{shared,s,-j}-CV(FPR)_{local,s,-j}.
\]

For each omitted device `j`, summarize across the same ten seeds:

\[
\overline{Delta}_{-j}=\frac{1}{10}\sum_{s=1}^{10}Delta_{s,-j}.
\]

Let the full nine-device confirmatory mean be `mean_delta`. Report

\[
MinLODOMean=\min_j \overline{Delta}_{-j},
\qquad
MaxLODOMean=\max_j \overline{Delta}_{-j},
\]

\[
MaxLODOShift=\max_j|\overline{Delta}_{-j}-\overline{Delta}|.
\]

Also report:

```text
positive_direction_retention = count_j(mean_Delta_-j > 0) / 9
nonpositive_omissions = all device IDs with mean_Delta_-j <= 0
```

When `abs(mean_delta) > 1e-12`, define the relative maximum influence shift

\[
RelativeMaxLODOShift
=\frac{MaxLODOShift}{|\overline{Delta}|}.
\]

When `abs(mean_delta) <= 1e-12`, `RelativeMaxLODOShift` is `UNAVAILABLE_NEAR_ZERO_FULL_EFFECT`; it must not be stabilized by adding an arbitrary denominator constant.

The pre-specified influence flag is:

```text
LODO_HIGH_INFLUENCE =
    any(mean_Delta_-j <= 0)
    OR (RelativeMaxLODOShift >= 0.25, when defined)
```

The `0.25` boundary is a prospective sensitivity flag meaning that omission of one device changes the full-sample mean effect by at least 25%; it is not a significance threshold and does not alter the confirmatory BCa decision rule.

No p-value or BCa interval is computed over the nine omitted-device means because they are highly dependent sensitivity analyses. The original ten-seed, nine-device BCa result remains the only confirmatory inference. If `LODO_HIGH_INFLUENCE` is true, the manuscript must identify every triggering device, report the triggering condition, and describe the headline effect as influence-sensitive.

**15.2 Numerical and selection discipline**

Calculations use full available precision. Rounding occurs only for presentation.

Recommended presentation:

- rates and aggregate metrics: three decimals;
- confidence intervals and effect sizes: three decimals;
- p-values: three significant digits, with `< 0.001` when appropriate;
- counts: integers;
- thresholds: enough digits to reproduce decisions.

Never round before computing contrasts or intervals.

Do not choose checkpoints, policies, or parameter values from test outcomes, remove unfavorable seeds or clients, convert undefined metrics to zero, or hide material null or contrary results.

### 16. Mandatory manuscript-facing figures and synthesis tables

These are reporting requirements over already declared experiments; they do not create new inferential endpoints.

**16.1 Causal intervention map — mandatory main-text figure**

Render the scientific pipeline in this exact left-to-right order:

```text
raw records
  -> population / split identity
  -> fitted preprocessing state
  -> federated training
  -> terminal detector
  -> canonical calibration + evaluation score artifacts
  -> [FIXED-SCORE BOUNDARY]
  -> threshold estimator
  -> threshold-calibration scope
  -> deployed threshold(s)
  -> held-out predictions
  -> per-client metrics
  -> cross-client operating-point metrics
```

The figure must visually place interventions at their correct stage:

```text
preprocessing sensitivity -> fitted preprocessing / detector geometry
FedProx + local fine-tuning + Ditto -> training / detector geometry
Komadina-style estimator axis + q95-vs-moment sensitivity -> threshold estimator
DATP core ladder           -> threshold-calibration scope ONLY
one-shot recalibration     -> calibration evidence at a later genuine-time window
```

There must be **no arrow from held-out evaluation labels or metrics back into threshold estimation, q selection, preprocessing, training, cluster count, shrinkage, or eligibility**. The fixed-score boundary must visually separate the confirmatory threshold-scope intervention from training/model changes.

**16.2 Confirmatory paired-effect view — mandatory main-text figure**

Show all ten seed-level

\[
\Delta_s=CV(FPR)_{shared,s}-CV(FPR)_{local,s}
\]

with a horizontal zero reference, the arithmetic mean, and the locked 95% BCa interval. Every seed remains individually identifiable by seed ID. Do not replace this with a bar chart containing only a mean and error bar.

**16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table**

The confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD result must have one aligned table containing, for both policies and their paired difference where meaningful:

```text
mean FPR
CV(FPR)
IQR(FPR)
range(FPR)
worst-client FPR
TPR
Macro-F1
P10 Macro-F1
worst-client balanced accuracy
MeanAbsoluteTestFPRTargetError
MeanAbsoluteCalibrationGeneralizationGap
```

The same table or an immediately adjacent panel must show the ten seed-level `FPRHelpedFraction`, `FPRHarmedFraction`, `TPRLossFraction`, and Pareto client-impact fractions from Part II §7.5B. The purpose is to make an equity improvement visually inseparable from its detection-utility consequences. No table may headline `CV(FPR)` alone while relegating a material TPR/Macro-F1/worst-client degradation to unreferenced supplementary text.

**16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure**

Use Part II §7.7 exactly: primary `CV(FPR)` versus P10 Macro-F1, secondary `CV(FPR)` versus WorstBA, canonical `q=0.95`, same ten-seed method means, and no scalarized winner. The accompanying target-attainment table is mandatory.

**16.4 FedProx mechanism-activation view — mandatory stress-test figure**

For every `mu in {0.001,0.01,0.1,1.0}` and FedAvg, show the ten seed-level `D_terminal50` values. A companion panel or aligned table must show `(DriftSuppression, DeltaH, H, ModelAlignmentH, LocalThresholdDispersion, NormalizedSharedLocalThresholdDistance, DeltaScope, ScopeAbsorption)` by `mu`. Do not infer from threshold outcomes alone that the proximal mechanism was active.

**16.5 Mandatory synthesis tables**

The manuscript or supplement must include:

1. the Part II §4.0 population-capability/claim-boundary table;
2. the Part I §10.D.9 prior-art collision table updated through the submission-time novelty gate;
3. the shared-threshold robustness panel covering canonical arithmetic-mean shared, exact pooled, sample-weighted shared, `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`, and `FEDERATED_BENIGN_SUMMARY_THRESHOLD` against LOCAL_THRESHOLD;
4. the calibration-generalization/target-attainment diagnostics corresponding to the main threshold-policy results;
5. the Part I §10.D.9B source-grounded prior-art distinction table, using the locked categorical vocabulary;
6. the Part II §7.5A calibration-support-versus-burden table and seed-level association summary;
7. the Part II §7.5B natural-device helped/harmed table with the campaign-fixed support strata;
8. the Part II §7.4 typed empirical policy-selection surface and its reconstructable raw metric table.

## Part IV — Development, Reproducibility, and Audit Contract

### 1. Purpose and audit semantics

This part answers a different question from Parts I–III:

> Does the implementation and produced evidence actually satisfy the roadmap that defines the study?

It does not create new scientific experiments. It operationalizes the existing contracts into development and campaign-level checks.

An audit item has one of four statuses:

```text
PASS
FAIL
NOT_APPLICABLE
UNAVAILABLE_AS_SPECIFIED
```

`UNAVAILABLE_AS_SPECIFIED` is valid only when Parts I–III explicitly declare that evidence unavailable for the relevant population. It must never be used to hide a missing implementation or failed computation.

A **FAIL** in a causal-isolation, score-identity, split-leakage, calibration-leakage, eligibility, terminal-detector, confirmatory-pairing, or statistical-validity gate blocks the affected scientific claim. A publication bundle must retain the failed audit result and the reason.

### 2. Audit object identity

Every materialized scientific result must be traceable to a complete execution coordinate containing, at minimum:

```text
dataset identity
population/population identity
training method identity
training seed
preprocessing protocol identity
terminal detector identity
score artifact identity
calibration artifact identity
threshold method identity
evaluation population identity
analysis/report identity
```

Scientific identity is established by semantic provenance and ordered record identity. File hashes or checksums may be used for transport/integrity verification, but they do not replace the scientific identity contract in Part I §2.2.2.

### 3. Gate A — Roadmap and configuration integrity

- [ ] Every executable experiment maps to exactly one Part II experiment or explicitly declared diagnostic extension.
- [ ] No stale method name, retired alias, or opaque experiment code changes the active descriptive scientific identity defined in Part I §10.C.
- [ ] No opaque B-number threshold alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports.
- [ ] No lettered population alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports.
- [ ] Threshold policies use exactly `CENTRALIZED_REFERENCE`, `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FAMILY_THRESHOLD`, or `CLUSTER_THRESHOLD` where applicable.
- [ ] Dataset populations use exactly `NBAIOT_NATURAL_DEVICES`, `CICIOT_FILE_CLIENTS`, `NBAIOT_DIRICHLET_CLIENTS`, `EDGE_SENSOR_CLIENTS`, or `EDGE_TEMPORAL_CLIENTS` where applicable.
- [ ] Every locked numerical value used by code is traceable to Part I §11 or its authoritative detailed section.
- [ ] No mandatory grid has silently lost a cell.
- [ ] No unregistered value has been inserted into a locked grid.
- [ ] Canonical and sensitivity conditions are distinguishable in configuration and artifacts.
- [ ] A sensitivity cell cannot be relabelled as canonical after outcomes are observed.
- [ ] Optional analyses remain explicitly optional and cannot replace mandatory evidence.

### 4. Gate B — Dataset integrity

For every dataset used by DATP-Core:

- [ ] The physical source and canonical dataset identity are recorded.
- [ ] Declared model-input features match the dataset-specific protocol.
- [ ] Label normalization is deterministic and auditable.
- [ ] Missing, non-finite, and ineligible rows follow Part I §2.2.1 exactly; no silent imputation, zero-fill, clipping, capping, infinity replacement, or label inference occurs.
- [ ] Stable row identity and source provenance survive preprocessing and splitting.
- [ ] Dataset-specific exclusions are counted and reported.
- [ ] N-BaIoT preserves the nine natural physical devices for the confirmatory population.
- [ ] CICIoT2023 does not invent physical-device identities from unavailable provenance.
- [ ] Edge-IIoTset uses only the client definition and temporal information justified by Part I §9 and Part II §4.

### 5. Gate C — Population and client integrity

- [ ] Each result references an immutable population identity.
- [ ] Client membership is deterministic for a fixed population coordinate.
- [ ] Natural-device, file-defined, synthetic/Dirichlet, external, and temporal populations cannot be silently mixed.
- [ ] Population construction never uses held-out test outcomes.
- [ ] FAMILY_THRESHOLD is enabled only where the locked physical-family taxonomy is scientifically valid.
- [ ] CLUSTER_THRESHOLD receives exactly the eligible client population declared for the experiment.
- [ ] Empty, singleton, and excluded groups remain visible rather than being silently dropped.
- [ ] Client counts in tables equal the audited population manifest.

- [ ] For every persistent-client result, the same immutable `client_id` binds training, calibration, evaluation, local threshold state, and any personalized model state exactly as Part I §3.3A requires.
- [ ] No unseen-client or intermittent-client interpretation is inferred from the calibration cold-start experiment.

### 6. Gate D — Split, chronology, and eligibility integrity

- [ ] Train, calibration, and evaluation partitions are disjoint by immutable row identity.
- [ ] Benign training fit uses training rows only.
- [ ] Calibration rows never enter reported held-out test metrics.
- [ ] Test outcomes never influence split construction, eligibility, threshold tuning, model selection, or comparator tuning.
- [ ] `n_k_source` is computed before experimental subsampling.
- [ ] Primary eligibility is exactly `n_k_source >= 100`.
- [ ] Eligibility is fixed before test evaluation and identical across compared threshold policies.
- [ ] Calibration-size ablations use `m` independently of the source-pool eligibility decision.
- [ ] Temporal experiments use genuine chronology: historical calibration < future recalibration < future evaluation.
- [ ] Generated pseudo-time or file ordering is never substituted for real timestamps where chronology is required.

### 7. Gate E — Preprocessing integrity

- [ ] Every threshold comparison references one named preprocessing protocol identity.
- [ ] `FEDERATED_CLIENT_LOCAL_STANDARD` is fit client-locally on benign training only in the confirmatory protocol.
- [ ] `FEDERATED_POOLED_MIN_MAX` is never silently mixed into the confirmatory ladder.
- [ ] `CENTRALIZED_POOLED_MIN_MAX` is independently fitted and never reuses federated fitted states.
- [ ] Threshold methods cannot fit, select, or alter model-input preprocessing.
- [ ] Cluster-fingerprint standardization is kept distinct from model-input preprocessing.
- [ ] Serialization/reload equivalence uses the `1e-12` engineering tolerance only for reload validation.
- [ ] A reload tolerance comparison is never used to establish scientific fixed-score identity.

### 8. Gate F — Training and terminal-detector integrity

- [ ] Every **federated training** execution has exactly one scientific terminal detector at round `200`; `FEDAVG_LOCAL_FINE_TUNING` starts from that detector and produces separately identified post-training client-personalized states after exactly ten local epochs.
- [ ] Recovery checkpoints are used only to resume interrupted execution.
- [ ] Diagnostic checkpoints are observational and never become score sources.
- [ ] SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD do not trigger policy-specific retraining.
- [ ] FedAvg confirmatory models are distinct from FedProx, Ditto, centralized, preprocessing-sensitivity, and post-FedAvg fine-tuned client states where the protocol requires separate detector identities.
- [ ] No test AUROC, test label, threshold result, DATP effect, or external result changes the terminal detector.
- [ ] FedProx executes the complete locked `mu` grid.
- [ ] FedProx persists broadcast/returned state identity and produces `L2Drift`, `RMSDrift`, terminal-50 drift summaries, and `DriftSuppression` exactly as Part I §7.1A requires.
- [ ] Client-round FedProx drift cells remain nested diagnostics and are never treated as independent inferential observations.
- [ ] Ditto executes the complete locked `lambda_D` grid and preserves genuine persistent-personalized-state semantics before using the name Ditto.

- [ ] `FEDAVG_LOCAL_FINE_TUNING` initializes every client from the exact seed-matched FedAvg round-200 model, uses a fresh optimizer state, exactly 10 benign-training epochs, no early stopping, and no calibration/evaluation/attack-label access.
- [ ] Fine-tuned client models are frozen before scoring and are never re-fine-tuned per threshold policy.
- [ ] The deterministic fine-tuning seed identity includes `(dataset_id,population_id,training_seed,client_id)` with purpose `FEDAVG_LOCAL_FINE_TUNING`.

### 9. Gate G — Fixed-score and scoring integrity

- [ ] Exactly one canonical evaluation-score artifact exists per fixed detector / preprocessing / population / seed coordinate.
- [ ] SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD reference that same score artifact identity within a ladder.
- [ ] Threshold methods do not independently regenerate detector scores.
- [ ] Ordered row identities are preserved across score, label, and evaluation artifacts.
- [ ] Calibration-score identity is likewise shared where the experiment requires fixed calibration evidence.
- [ ] A higher reconstruction error always denotes greater anomaly evidence.
- [ ] AUROC is computed from the canonical continuous score/label artifact, not from thresholded predictions.
- [ ] Any policy-specific AUROC difference within a fixed-score ladder is treated as an identity/provenance failure.

### 10. Gate H — Calibration integrity

- [ ] Every DATP-compatible threshold method uses benign calibration data only.
- [ ] Attack-labelled rows never affect threshold values, q selection, eligibility, cluster count, comparator tuning, shrinkage, or conformal significance level.
- [ ] Calibration and evaluation rows are disjoint.
- [ ] Type-7 empirical quantiles use float64 and are not rounded before threshold application.
- [ ] LOCAL_CONFORMAL_THRESHOLD is the explicit conformal-order-statistic exception and is not routed through type-7 interpolation.
- [ ] Calibration-size subsampling follows Part II §2.3A exactly: immutable-row ordering, SHA-256 seed derivation, PCG64, without replacement, prefix nesting.
- [ ] The 10 nested calibration replicates are summarized within training seed and never treated as independent seeds.
- [ ] Shared-calibration contributor-availability sensitivity enumerates every permitted omission subset exhaustively, changes only shared-summary contribution, and evaluates every resulting shared threshold on the unchanged full eligible client population.
- [ ] Omission subsets are never interpreted as independent replications or used to inflate the seed count.
- [ ] Every threshold-stage artifact is generated under the Part I §3.2A protocol-compliant participant assumption; no experiment silently injects fabricated thresholds, support counts, summaries, fingerprints, sketches, scores, or client identities.
- [ ] Contributor-availability sensitivity is labeled non-adversarial; it is never called Byzantine robustness, poisoning resistance, malicious-dropout robustness, or message-integrity validation.
- [ ] Any threshold-stage provenance/checksum/identity mismatch invalidates the artifact/coordinate and is not counted as an attack-defense success.

### 11. Gate I — Threshold-policy integrity

**SHARED_THRESHOLD**
- [ ] Computes each eligible client's local q-quantile and takes the arithmetic mean of eligible local quantiles.
- [ ] Is never mislabeled as the exact pooled quantile.
- [ ] Applies one threshold to every eligible client.

**LOCAL_THRESHOLD**
- [ ] Uses each eligible client's own benign q-quantile.
- [ ] Uses the same q and score evidence as SHARED_THRESHOLD in the confirmatory comparison.

**FAMILY_THRESHOLD**
- [ ] Uses only the locked physical-family taxonomy.
- [ ] Forms family thresholds exactly from eligible family-member local thresholds.
- [ ] Is unavailable where no defensible taxonomy exists.

**CLUSTER_THRESHOLD**
- [ ] Fingerprint is exactly `[mean(error), std(error), skewness(error), p95(error)]`.
- [ ] Canonical clustering uses the separate score-side fingerprint-standardization contract, canonical `K=3`, and the locked initialization/seed handling required by Part II §7.1.
- [ ] Cluster threshold is the mean of member local thresholds.
- [ ] CLUSTER_THRESHOLD never changes the detector, performs model clustering, or acquires a privacy claim.
- [ ] Cluster identities are aligned before across-seed switch-frequency reporting.

### 12. Gate J — Comparator and threshold-variant integrity

- [ ] Exact pooled benign quantile uses the type-7 pooled oracle.
- [ ] Sample-weighted shared construction uses the declared eligible calibration weights.
- [ ] Fixed shrinkage executes the full λ curve and never selects a winner post hoc.
- [ ] Size-aware shrinkage uses `n_k_used/(n_k_used+100)` and never substitutes `n_k_source` for `m` in a subsampled cell.
- [ ] `FEDERATED_BENIGN_SUMMARY_THRESHOLD` communicates only the predeclared benign summaries and includes the full pooled variance decomposition.
- [ ] `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is never called Laridi-faithful.
- [ ] KLL uses float64, canonical `k=400`, sensitivity `{200,800}`, ascending client merge order, and the locked inclusive-rank semantics.
- [ ] KLL observed empirical rank/threshold errors are measured against the exact pooled type-7 oracle.
- [ ] KLL implementation randomness follows Part II §9.2 and remains nested within training seed.
- [ ] `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` uses float64, arithmetic mean, sample standard deviation with `ddof=1`, and the locked `{shared, local}` 2×2 scope comparison; it is never presented as a faithful reproduction of Meidan's complete detector.
- [ ] LOCAL_CONFORMAL_THRESHOLD reports held-out benign coverage and its limitations; it does not claim arbitrary client-conditional validity.

### 13. Gate K — Experiment completeness

For every mandatory Part II experiment:

- [ ] Every declared factor level was executed or has a recorded pre-specified infeasibility reason.
- [ ] Every required comparison method is present.
- [ ] Every required seed is present; confirmatory inference requires exactly ten valid paired seed deltas.
- [ ] All declared nested replicates are present where required.
- [ ] Required outcomes, diagnostics, tables, and figures were produced or explicitly marked unavailable under a roadmap rule.
- [ ] Null, reversed, unstable, and unfavorable outcomes remain in the result set.
- [ ] No experiment was dropped because it weakened the narrative.
- [ ] Optional experiments are visually and semantically separated from mandatory evidence.
- [ ] Part II §8.6 produces every feasible `m in {0,1,2,3,4}` omission subset, exact seed-level subset summaries, and the identities of worst-case omission sets.

### 14. Gate L — Evaluation and metric integrity

- [ ] Prediction semantics are exactly `attack iff score > threshold`.
- [ ] Confusion counts are computed from held-out evaluation rows only.
- [ ] Per-client metrics are computed before cross-client aggregation where valid client identity exists.
- [ ] `CV(FPR)` uses only the eligible FPR-evaluable client population defined in Part III.
- [ ] Absolute dispersion metrics accompany CV where low mean FPR could make CV unstable or misleading.
- [ ] Attack-sensitive metrics are marked unavailable when valid per-client attack assignment is absent.
- [ ] Undefined denominators remain undefined; they are never converted to zero.
- [ ] AUROC/AP are detector-quality controls and do not become threshold-scope verdicts.
- [ ] Held-out target-attainment error is computed from held-out benign rows and is never replaced by calibration-set exceedance.
- [ ] Calibration-to-held-out benign generalization gap uses the exact calibration scores that constructed each scalar threshold, the strict `score > threshold` exceedance rule, and the unchanged held-out benign evaluation rows.
- [ ] Calibration-generalization-gap diagnostics never feed threshold fitting, policy selection, model selection, or claim-tier promotion.
- [ ] P10 Macro-F1 and worst-client balanced accuracy remain visible when available, including unfavorable trade-offs.

### 15. Gate M — Statistical integrity

- [ ] Training seed is the independent inferential unit.
- [ ] Nested replicates are summarized within seed before across-seed inference.
- [ ] Confirmatory delta direction matches the Part III definition.
- [ ] The confirmatory statistic is the arithmetic mean of the ten paired seed-level deltas.
- [ ] The confirmatory uncertainty is the locked two-sided 95% BCa interval over paired seed deltas.
- [ ] Degenerate/invalid BCa states produce `CONFIRMATORY_INFERENCE_UNAVAILABLE` rather than a substituted method.
- [ ] Wilcoxon is paired, uses exact computation where feasible, and records fallback/approximation behavior.
- [ ] Rank-biserial effect size is the matched-pairs version, not unpaired Cliff's delta.
- [ ] Secondary emphasized p-values use predeclared families and Holm correction.
- [ ] Exact paired sign-test uses only non-zero paired deltas, an exact `Binomial(n_nonzero, 0.5)` null, and no normal approximation; zero deltas remain visible in sign counts.
- [ ] Leave-one-seed-out precision diagnostics are reported without changing the inferential sample.
- [ ] Leave-one-device-out confirmatory influence uses the same ten training seeds and already generated scores; the nine omitted-device means are dependent diagnostics and are never treated as nine independent replicates.
- [ ] `LODO_HIGH_INFLUENCE` is evaluated exactly as Part III §15.1A specifies; the 25% influence boundary is descriptive and never modifies the BCa decision rule.
- [ ] No seed or client is removed because of effect direction.

### 16. Gate N — Mechanism-analysis integrity

- [ ] Mechanism analyses use only pre-specified variables and populations.
- [ ] Jensen–Shannon constructions use the exact locked binning/log convention from Part II.
- [ ] Association analyses use associative, not causal, language.
- [ ] `n < 5` association cases use the declared insufficient-evidence state rather than fabricated coefficients.
- [ ] Cluster stability reports memberships, sizes, empty clusters, singleton clusters, ARI, and switch behavior where specified.
- [ ] Recovery-of-local-gap quantities are not clipped to `[0,1]`.
- [ ] Non-positive SHARED_THRESHOLD→LOCAL_THRESHOLD denominators use the declared unavailable state.
- [ ] Natural-device mechanism leave-one-device-out analysis never retrains, refits preprocessing, or rescores; it recomputes only the population-dependent heterogeneity/shared-threshold quantities defined in Part II §7.4.
- [ ] The `9 × 10` leave-one-device seed cells are never treated as 90 independent observations; the association influence analysis remains a sensitivity analysis over the original population/seed structure.
- [ ] Part II §7.5 reports exact per-seed FPR/TPR direction counts without inventing a floating tolerance or post-hoc materiality cutoff.
- [ ] Part II §7.5A support-versus-burden Spearman coefficients use only the common valid client set, require at least five clients plus nonconstant inputs, use average ranks for ties, and do not report client-level inferential p-values from the nine-device population.
- [ ] The support-versus-burden diagnostic is interpreted associatively and never used to claim that calibration support causes client harm.
- [ ] Equity–utility Pareto analysis never invents a scalarized winner.

- [ ] Every FedProx, `FEDAVG_LOCAL_FINE_TUNING`, and Ditto stress condition reports the common Part I §7.2B score/threshold-alignment tuple whenever inputs are valid.
- [ ] `ScopeAbsorption` and every `AlignmentReduction` are un-clipped; non-positive FedAvg denominators produce the declared unavailable states rather than an epsilon adjustment.
- [ ] `FEDAVG_LOCAL_FINE_TUNING` uses exactly ten benign-training local epochs from the exact round-200 FedAvg weights, a fresh optimizer state, no early stopping, and no calibration/evaluation/attack-label access.
- [ ] The N-BaIoT helped/harmed profile reports all ten seed-level fractions and every physical-device help/harm frequency; the 9×10 cells are never treated as independent observations.
- [ ] Calibration-support strata are frozen from ascending `SupportScore_k=median_s(n_{s,k,source})` with canonical-client-ID tie-break into ranks `1..3`, `4..6`, `7..9`; if exactly nine eligible N-BaIoT clients are not available, the stratum analysis emits the declared unavailable state.
- [ ] The empirical policy-selection surface emits only the declared typed states and raw nondominated sets; no learned classifier, cutoff, scalar utility weight, or post-hoc production rule is fitted.
- [ ] `H_TAUTOLOGY` reporting uses disjoint calibration/evaluation row identities and shows calibration exceedance, held-out target error, and calibration-generalization gap rather than calling local q95 held-out FPR “guaranteed.”

### 17. Gate O — External and boundary evidence integrity

- [ ] CICIoT2023 findings are described only for file-defined pseudo-clients and never generalized to the original physical-device topology.
- [ ] Edge-IIoTset conclusions are limited to the metrics and client semantics actually available.
- [ ] Unavailable Edge attack metrics remain unavailable and are not reconstructed from unsupported labels.
- [ ] External validation is never promoted into a second confirmatory endpoint.
- [ ] Controlled Dirichlet partitions remain sensitivity evidence and are not called natural-device evidence.
- [ ] No extra dataset is added without an explicit roadmap amendment.

### 18. Gate P — Temporal integrity

- [ ] Temporal evidence uses valid timestamps and genuine chronology only.
- [ ] Static, frozen-future, and one-shot-recalibrated states are computed exactly as Part II §12.1 specifies.
- [ ] Future evaluation never influences historical thresholding or future recalibration.
- [ ] `drift_excess`, `recovered_amount`, and `recovery_ratio` use Part III §14 definitions.
- [ ] `recovery_ratio` is undefined below the locked positive-materiality threshold.
- [ ] Temporal association diagnostics use the declared 64-bin common quantile grid and n≥5 requirement.
- [ ] Results are framed as one-shot threshold aging/recalibration evidence, not continuous drift handling.

### 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity

- [ ] Every table/figure/result row can be traced back to its exact execution coordinate.
- [ ] Artifact provenance records code version, dataset identity, population identity, seed, protocol identities, and dependency/library versions required by the method.
- [ ] Ordered record identities are recoverable for score and label artifacts.
- [ ] Re-running a deterministic coordinate reproduces the same identities and deterministic nested draws.
- [ ] KLL serialized artifacts and library version are retained because implementation randomness can affect reconstruction.
- [ ] Runtime tables record hardware, OS, runtime, and library versions.
- [ ] Cross-machine timing comparisons are not made.
- [ ] Missing artifacts cannot be silently regenerated under a different protocol identity and treated as original evidence.

### 20. Gate R — Reporting and claim-to-evidence integrity

- [ ] The manuscript's confirmatory claim is supported only by Part II §5.1 and Part III §11.
- [ ] Supportive, mechanism, external, stress-test, boundary, operational, and exploratory evidence keeps its declared tier.
- [ ] A failed/null confirmatory endpoint is not rescued by CLUSTER_THRESHOLD, shrinkage, conformal, FedProx, Ditto, or an external dataset.
- [ ] Operational FPR equity is not presented as demographic or protected-attribute fairness.
- [ ] Structural raw-data locality is not called a formal privacy guarantee.
- [ ] Threshold-stage byte/runtime accounting is not called deployment validation.
- [ ] No fleet-scale claim is made from synthetic or file-defined pseudo-clients.
- [ ] LOCAL_THRESHOLD/local thresholds are not claimed as universally novel; prior-art boundaries in Part I §10.D remain visible.
- [ ] The manuscript defines probability calibration, anomaly operating-point calibration, and conformal calibration according to Part I §10.C.7A and does not demand ECE/Brier/NLL for DATP's non-probabilistic threshold object.
- [ ] The manuscript explicitly states the Part I §3.2A honest/protocol-compliant calibration assumption and does not imply Byzantine, poisoning, secure-aggregation, authenticated-message, or adversarial-calibration robustness.
- [ ] The Part I §10.D.9B source-grounded prior-art distinction table is present, uses only the locked categorical vocabulary, and marks unsupported source facts as `NOT_REPORTED` rather than guessed values.
- [ ] The submission-time novelty-survival literature gate in Part I §10.D.9A was executed within 14 calendar days of submission and both prior-art tables/citations were updated through that search date.
- [ ] The historical moment-estimator sensitivity is reported as estimator-family robustness only and is not used to replace the q95 confirmatory endpoint.
- [ ] Null, reversed, infeasible, and unfavorable seed-level evidence is retained in supplementary evidence where required.
- [ ] Every headline table or figure has a traceable experiment and metric definition.
- [ ] The mandatory causal intervention map preserves the fixed-score boundary and contains no outcome-to-calibration/training feedback arrow.
- [ ] The ten confirmatory paired seed deltas are shown individually with the arithmetic mean and locked BCa interval.
- [ ] Both required equity–utility Pareto views and their target-attainment table are present when attack-sensitive N-BaIoT metrics are available.
- [ ] The FedProx mechanism figure reports terminal-50 drift rather than inferring mechanism activation from downstream performance alone.
- [ ] The manuscript explicitly qualifies the confirmatory regime as persistent identifiable IoT clients with full training participation and does not generalize to intermittent/unseen cross-device clients.
- [ ] The headline confirmatory result includes the mandatory equity–utility/client-impact bundle rather than reporting `CV(FPR)` in isolation.
- [ ] `FEDAVG_LOCAL_FINE_TUNING` is identified as a bounded simple personalization stress test, not a new PFL contribution and not a replacement for Ditto.
- [ ] The complete reproducibility-release bundle in §20A is generated in the appropriate `PUBLIC`, `BLINDED_ARCHIVE`, or `WITHHELD_LICENSE_RESTRICTED` state and its SHA-256 manifest validates.

### 20A. Reproducibility-release bundle

Publication readiness includes a **reconstructable research release**, subject to dataset licenses and anonymous-review policy. The release is evidence packaging, not a new scientific experiment.

The release root must contain the following logical payload (directory names may be mapped to repository-native equivalents only if a manifest maps them one-to-one):

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

**`ROADMAP_LOCK.md`**

- exact scientific-roadmap snapshot used for the reported campaign;
- SHA-256 digest of that snapshot;
- code commit/release identifier;
- submission-time literature-search date from Part I §10.D.9A.

**`MANIFEST_SHA256.csv`**

One row per released artifact **except `MANIFEST_SHA256.csv` itself and its `MANIFEST_SHA256.sha256` sidecar**, with at least:

```text
relative_path
sha256
bytes
artifact_type
dataset_id
population_id
training_method
training_seed
threshold_policy
experiment_id
```

Fields that do not apply use an explicit `NA`, never an empty ambiguous value. SHA-256 is computed on the exact released bytes. After `MANIFEST_SHA256.csv` is finalized, compute its SHA-256 and write exactly one lowercase hexadecimal digest followed by two spaces and `MANIFEST_SHA256.csv` plus a terminating newline to `MANIFEST_SHA256.sha256`. The sidecar is not listed inside the CSV; this avoids an impossible self-referential hash.

**`SEEDS.csv`**

- the exact ten confirmatory training seeds;
- every declared nested/randomness purpose label;
- deterministic derivation inputs sufficient to reconstruct calibration subsamples, cluster repeats, KLL runs, fine-tuning batch order, and any other seeded nested operation;
- no seed may be regenerated from an undocumented process during reproduction.

**Data/split provenance**

Raw third-party datasets are **not redistributed when licensing does not permit it**. Instead release:

- official acquisition instructions/identifiers;
- raw-file checksums where redistribution-independent checksums are lawful to publish;
- canonical processed-artifact checksums;
- ordered row-identity-set hashes for train/calibration/evaluation artifacts;
- client membership counts and the deterministic population-construction manifest.

For an ordered row-identity artifact, hash the UTF-8 byte sequence formed by canonical row IDs joined by the single byte `0x0A` in artifact order with no trailing newline. Persist both `ordered_row_sha256` and `row_count`. This makes split identity reproducible without publishing sensitive/raw row contents.

**Preprocessing/models/scores/thresholds**

Release or hash, subject to licensing/security constraints:

- fitted preprocessing-state artifacts and protocol identities;
- terminal round-200 model artifacts for each training condition/seed, including personalized client states where releasable;
- canonical calibration/evaluation score artifacts or, where source-data licensing prevents score redistribution, their exact ordered-row identities, hashes, generation command, and model/preprocessing hashes;
- every threshold output and its contributor/support metadata.

**Metrics/statistics/figures**

Release:

- tidy seed×client×policy metric tables;
- all ten confirmatory paired deltas;
- BCa bootstrap configuration and deterministic bootstrap seed material;
- Wilcoxon/sign-test/effect-size/multiplicity inputs and outputs;
- the source-data table behind every manuscript figure and table;
- typed unavailability states rather than silently dropped cells.

**Environment metadata**

Record at minimum:

```text
Python version
OS and kernel
CPU model
RAM
GPU model
GPU count
CUDA runtime
GPU driver
cuDNN version where applicable
PyTorch version
Flower version
NumPy/SciPy/scikit-learn versions
all locked direct dependency versions
```

Timing artifacts additionally record the exact host identifier/configuration class and prohibit cross-machine speedup claims.

The release has one explicit state:

```text
PUBLIC
BLINDED_ARCHIVE
WITHHELD_LICENSE_RESTRICTED
```

`BLINDED_ARCHIVE` is used when anonymous-review rules forbid a public identity-bearing release; the same artifact bundle must remain reconstructable. `WITHHELD_LICENSE_RESTRICTED` may be used only for specific artifacts whose redistribution is prohibited, and every withheld artifact must have a hash/provenance/reconstruction record.

A release-validation command must first validate `MANIFEST_SHA256.csv` against `MANIFEST_SHA256.sha256`, then recompute every listed artifact SHA-256 and byte count. It must fail on a missing listed file, an unexpected non-metadata file, byte-size mismatch, or digest mismatch. Publication figures/tables are considered reconstructable only if their released source tables pass this manifest validation.

### 21. Final publication-readiness gate

DATP-Core is publication-ready only when all of the following are true:

- [ ] the anchor reproduction gate has the roadmap-defined outcome;
- [ ] the ten-seed confirmatory campaign is complete or explicitly yields `CONFIRMATORY_INFERENCE_UNAVAILABLE` for a roadmap-valid reason;
- [ ] every mandatory supportive/mechanism/stress/boundary experiment is complete or has a pre-specified infeasibility record;
- [ ] all causal-isolation and leakage gates pass for evidence used in claims;
- [ ] all required metric and statistical audits pass, including exact sign-test, calibration-generalization-gap, `H_TAUTOLOGY` disjoint-row evidence, calibration-support-versus-burden, natural-device helped/harmed/support-stratum outputs, per-device direction-count, and leave-one-device-out influence outputs;
- [ ] the submission-time novelty-survival gate passes and the manuscript novelty wording matches the updated collision and source-grounded distinction tables;
- [ ] the honest-calibration threat boundary is explicit and no result is mislabeled as adversarial/Byzantine calibration robustness;
- [ ] all expected unavailable metrics are distinguished from missing implementation;
- [ ] all required tables/figures can be reconstructed from retained evidence;
- [ ] the §20A reproducibility-release bundle exists in the correct release state and every manifest SHA-256/byte-count validation passes;
- [ ] the claim-to-evidence audit passes without tier promotion;
- [ ] the final manuscript explicitly reports material negative evidence and accepted limitations.

A readiness audit is a verification step, not a result-selection step. Failure to pass does not authorize changing the scientific protocol after inspecting outcomes.

## Appendix A — Research foundations and citations

The roadmap uses one definition per citation key. Literature supports design choice and positioning; it does not override the locked DATP-Core causal or claim contracts.

[^nbaiot]: Y. Meidan et al., “N-BaIoT—Network-Based Detection of IoT Botnet Attacks Using Deep Autoencoders,” *IEEE Pervasive Computing*, 2018. DOI: [10.1109/MPRV.2018.03367731](https://doi.org/10.1109/MPRV.2018.03367731). Supports the use of nine physical N-BaIoT devices, device-specific benign-trained autoencoders, and the historical device-specific `mean + standard deviation` anomaly-threshold context. DATP's locked moment sensitivity remains an adaptation rather than a full reproduction because Meidan also personalizes the detector and sequential decision rule.

[^edge-iiotset]: M. A. Ferrag et al., “Edge-IIoTset: A New Comprehensive Realistic Cyber Security Dataset of IoT and IIoT Applications for Centralized and Federated Learning,” *IEEE Access*, 2022. DOI: [10.1109/ACCESS.2022.3165809](https://doi.org/10.1109/ACCESS.2022.3165809). Supports Edge-IIoTset as an independent IoT/IIoT external dataset.

[^ciciot2023]: E. C. P. Neto et al., “CICIoT2023: A Real-Time Dataset and Benchmark for Large-Scale Attacks in IoT Environment,” *Sensors*, 2023. DOI: [10.3390/s23135941](https://doi.org/10.3390/s23135941). Supports the original dataset context of 105 devices and 33 attacks; the available data do not retain a verified physical-device mapping.

[^laridi]: S. Laridi, G. Palmer, and K.-M. M. Tam, “Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding,” *Scientific Reports*, 2024. DOI: [10.1038/s41598-024-76961-2](https://doi.org/10.1038/s41598-024-76961-2). The method aggregates summary statistics from normal and anomalous validation data; this motivates but is not equivalent to the benign-only `FEDERATED_BENIGN_SUMMARY_THRESHOLD` comparator.

[^motley]: S. Wu, T. Li, Z. Charles, Y. Xiao, Z. Liu, Z. Xu, and V. Smith, “Motley: Benchmarking Heterogeneity and Personalization in Federated Learning,” arXiv:2206.09262, 2022. [Primary paper](https://arxiv.org/abs/2206.09262). Supports the explicit distinction between persistent/stateful cross-silo-style personalization semantics and intermittent/stateless cross-device FL; DATP-Core borrows the regime distinction, not Motley's task or benchmark conclusions.

[^matsuda-pfl]: K. Matsuda, Y. Sasaki, C. Xiao, and M. Onizuka, “Benchmark for Personalized Federated Learning,” *IEEE Open Journal of the Computer Society*, vol. 5, pp. 2–13, 2024, DOI: 10.1109/OJCS.2023.3332351. [IEEE Computer Society record](https://www.computer.org/csdl/journal/oj/2024/01/10316561/1S2UbvQk5Tq). Supports treating ordinary FL plus client-local fine-tuning as a serious simple personalization baseline rather than assuming a specialized PFL method is necessarily stronger.

[^cheng-ftfa]: G. Cheng, K. Chadha, and J. Duchi, “Federated Asymptotics: a model to compare federated learning algorithms,” *Proceedings of AISTATS*, PMLR 206:10650–10689, 2023. [Primary paper](https://proceedings.mlr.press/v206/cheng23b.html). Their empirical FTFA/RTFA/MAML-FL evaluation performs 10 local personalization epochs before test evaluation; DATP-Core uses that value only as a prospective stress-depth precedent and retains its own optimizer/data/AE semantics.

[^fairhetero]: Z. Talukder, B. Lu, S. Ren, and M. A. Islam, “Hardware-Sensitive Fairness in Heterogeneous Federated Learning,” *ACM Transactions on Modeling and Performance Evaluation of Computing Systems*, vol. 10, no. 1, 2025, DOI: 10.1145/3703627. Supports distinguishing hardware/model-capacity heterogeneity from DATP-Core's statistical/score/calibration heterogeneity rather than treating every form of client heterogeneity as one construct.

[^fedprox]: T. Li et al., “Federated Optimization in Heterogeneous Networks,” *Proceedings of MLSys*, 2020. [Primary paper](https://arxiv.org/abs/1812.06127). Supports FedProx as a heterogeneity-oriented training stress test and not as a threshold policy.

[^ditto]: T. Li, S. Hu, A. Beirami, and V. Smith, “Ditto: Fair and Robust Federated Learning Through Personalization,” *Proceedings of ICML*, PMLR 139, 2021. [Primary paper](https://proceedings.mlr.press/v139/li21h.html). Supports the model-personalization stress-test design.

[^lu-fcp]: C. Lu et al., “Federated Conformal Predictors for Distributed Uncertainty Quantification,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/lu23i.html).

[^humbert-fcp]: P. Humbert, B. Le Bars, A. Bellet, and S. Arlot, “One-Shot Federated Conformal Prediction,” *Proceedings of ICML*, PMLR 202, 2023. [Primary publication](https://proceedings.mlr.press/v202/humbert23a.html).

[^fedcal2024]: H. Peng, H. Yu, X. Tang, and X. Li, “FedCal: Achieving Local and Global Calibration in Federated Learning via Aggregated Parameterized Scaler,” *Proceedings of the 41st International Conference on Machine Learning (ICML)*, PMLR 235, pp. 40331–40346, 2024. [Primary publication](https://proceedings.mlr.press/v235/peng24g.html). FedCal explicitly targets both local and global predictive calibration under federated heterogeneity; it is adjacent calibration prior art but does not study benign anomaly-score threshold scope or cross-client FPR dispersion.

[^robfcp2024]: M. Kang, Z. Lin, J. Sun, C. Xiao, and B. Li, “Certifiably Byzantine-Robust Federated Conformal Prediction,” *Proceedings of the 41st International Conference on Machine Learning (ICML)*, PMLR 235, pp. 23022–23057, 2024. [Primary publication](https://proceedings.mlr.press/v235/kang24c.html). Rob-FCP explicitly addresses malicious clients that can report arbitrary statistics during federated conformal calibration and provides Byzantine-setting coverage analysis; DATP cites it to define an adversarial-calibration boundary, not as a threshold-scope comparator.

[^cfhfc2026]: S. Izadi and M. Ahmadi, “CF-HFC: Calibrated Federated based Hardware-aware Fuzzy Clustering for Intrusion Detection in Heterogeneous IoTs,” arXiv:2602.12557v1, submitted 13 February 2026. [Primary preprint](https://arxiv.org/abs/2602.12557). The method combines hardware-aware fuzzy clustering, Fuzzy-FedProx, and Adaptive Conformal Calibration that dynamically adjusts decision thresholds; it is current IoT-IDS collision/positioning evidence, not a fixed-score DATP baseline.

[^prismfcp2026]: E. Lari, R. Arablouei, and S. Werner, “Communication-Efficient Byzantine-Robust Federated Conformal Prediction via Partial Model Sharing,” arXiv:2602.18396v2, revised 9 July 2026; the manuscript states that a conference version was accepted to EUSIPCO 2026. [Primary preprint](https://arxiv.org/abs/2602.18396). PRISM-FCP mitigates Byzantine behavior during both federated training and conformal calibration; DATP cites it only to delimit the honest-calibration threat model.

[^fediot2021]: T. Zhang, C. He, T. Ma, L. Gao, M. Ma, and S. Avestimehr, “Federated Learning for Internet of Things: A Federated Learning Framework for On-device Anomaly Data Detection,” *3rd International Workshop on Challenges in Artificial Intelligence and Machine Learning for Internet of Things (AIChallengeIoT 2021), co-located with ACM SenSys 2021*, 2021. DOI: [10.1145/3485730.3493444](https://doi.org/10.1145/3485730.3493444); [arXiv:2106.07976](https://arxiv.org/abs/2106.07976). FedIoT/FedDetect is prior art for federated IoT autoencoder anomaly detection and post-training global/personalized threshold construction.

[^rey2022]: V. Rey, P. M. Sánchez Sánchez, A. Huertas Celdrán, G. Bovet, and M. Jaggi, “Federated Learning for Malware Detection in IoT Devices,” *Computer Networks*, 2022, Article 108693. DOI: [10.1016/j.comnet.2021.108693](https://doi.org/10.1016/j.comnet.2021.108693).

[^ochiai2023]: H. Ochiai et al., “Detection of Global Anomalies on Distributed IoT Edges with Federated Learning,” *Proceedings of ACM MobiHoc 2023*, pp. 388–393, 2023. DOI: [10.1145/3565287.3616528](https://doi.org/10.1145/3565287.3616528).

[^asiri2025]: M. Asiri et al., “Decentralized Federated Learning for IoT Malware Detection,” *Future Internet*, vol. 17, no. 10, 475, 2025. DOI: [10.3390/fi17100475](https://doi.org/10.3390/fi17100475). The published method explicitly defines each local anomaly threshold as the 95th percentile of benign-validation reconstruction errors.

[^feddtcn2026]: M. A. Khan, O. Khalid, and R. N. B. Rais, “Fed-DTCN: A Federated Disentangled Learning Framework for Unsupervised Zero-Day Anomaly Detection in IoT with Semantic-Aware Augmentation,” *Sensors*, vol. 26, no. 6, 1918, 2026. DOI: [10.3390/s26061918](https://doi.org/10.3390/s26061918). The method includes a client-specific threshold \(\rho^{(k)}\); it is prior art for careless claims of first client-specific federated IoT anomaly thresholds.

[^pfcp2025]: Y. Min, C. Zhang, L. Peng, and C. Zou, “Personalized Federated Conformal Prediction with Localization,” *Advances in Neural Information Processing Systems (NeurIPS 2025)*, 2025. [Primary paper](https://proceedings.neurips.cc/paper_files/paper/2025/file/930a720c815416c263b0a090448ee901-Paper-Conference.pdf). The method constructs agent-personalized conformal prediction sets with target-agent marginal coverage; it is adjacent calibration prior art, not an AE-threshold comparator.

[^fedwqcp2026]: Q.-H. Nguyen, J. Wang, and W.-S. Ku, “Conformalized Neural Networks for Federated Uncertainty Quantification under Dual Heterogeneity,” arXiv:2602.23296, 2026. [Primary preprint](https://arxiv.org/abs/2602.23296). The FedWQ-CP method has clients transmit local conformal quantile thresholds and calibration sample sizes and forms a weighted global threshold at the server; it is direct prior art for broad federated weighted-quantile aggregation claims.

[^gcfcp2026]: H. Wen, O. Simeone, and H. Xing, “Efficient Federated Conformal Prediction with Group-Conditional Guarantee,” arXiv:2603.14198v3, 2026. [Primary preprint](https://arxiv.org/abs/2603.14198). GC-FCP targets group-conditional coverage using mergeable group-stratified calibration summaries; it is a formal-calibration boundary for FAMILY_THRESHOLD/CLUSTER_THRESHOLD, not an AE threshold comparator to implement in DATP-Core.

[^pfwcp2026]: M. V. Vejling, C. A. N. Biscio, A. Mazoyer, P. Popovski, and S. R. Pandey, “Multi-Agent Conformal Prediction with Personalized Statistical Validity,” arXiv:2606.00717, 2026. [Primary preprint](https://arxiv.org/abs/2606.00717). The PFWCP method combines density-ratio weighting and weighted quantile aggregation for agent-personalized calibration; it narrows any broad personalized-calibration novelty claim.

[^shahid-fcrc2026]: N. F. Shahid, “When Average Calibration Fails: Site-Conditional Federated Conformal Risk Control,” arXiv:2606.20115v3, 24 July 2026. [Primary preprint](https://arxiv.org/abs/2606.20115). On FeTS-2022 it reports pooled calibration violating the site-level target at 8/20 institutions while the average appears calibrated, and it uses `w_k=n_k/(n_k+n_0)` risk-curve shrinkage with leave-one-site-out sensitivity analysis. This is adjacent, high-priority novelty prior art for average-versus-local calibration and sample-size shrinkage; it is not an IoT anomaly-threshold experiment.

[^komadina2024]: A. Komadina, M. Martinić, S. Groš, and Ž. Mihajlović, “Comparing Threshold Selection Methods for Network Anomaly Detection,” *IEEE Access*, vol. 12, pp. 124943–124973, 2024. DOI: [10.1109/ACCESS.2024.3452168](https://doi.org/10.1109/ACCESS.2024.3452168). The paper identifies and implements five supervised and twenty unsupervised threshold-selection methods and is used here to support the estimator-versus-scope distinction, not to justify an estimator zoo in DATP-Core.

[^gpfli2026]: D. A. Oladele et al., “G-PFL-ID: Graph-Driven Personalized Federated Learning for Unsupervised Intrusion Detection in Non-IID IoT Systems,” *IoT*, vol. 7, no. 1, Article 13, published 29 January 2026. DOI: [10.3390/iot7010013](https://doi.org/10.3390/iot7010013). It evaluates unsupervised personalized federated intrusion detection using graph encoders and DeepSVDD on IoT-23 and natural-device N-BaIoT, including IoT-23 Dirichlet `alpha={0.1,0.5,infinity}` and `K={10,15,20}`; reported headline AUROC reaches 99.46% on IoT-23 and 97.74% on N-BaIoT. It motivates the model-personalization counterfactual but is not a DATP baseline to implement.

[^fbid2026]: A. K. Bui, C. T. Nguyen, H.-A. Pham, D. T. Hoang, and D. N. Nguyen, “FBID: Adaptive Personalized Federated Learning for Robust Out-of-Distribution Attack Detection in IoT Networks,” arXiv:2608.04073v1, 4 August 2026. [Primary preprint](https://arxiv.org/abs/2608.04073). FBID uses server-side contextual-bandit personalization control and trust-based global/local blending on heterogeneous CICIoT2023 OOD experiments, reporting individual-client relative improvements up to 7.66% in detection rate and 5.08% in F1 over its strongest stable baseline. DATP cites it only as current PFL-IDS context.

[^robalino2026]: J. Robalino-Díaz, A. Cabrera-Andrade, S. Luján-Mora, and W. Villegas-Ch, “Structural Impact of Non-IID Heterogeneity on Federated Behavioral Anomaly Detection in IoT and IoMT Systems,” *Frontiers in Artificial Intelligence*, vol. 9, Article 1825067, published 18 June 2026. DOI: [10.3389/frai.2026.1825067](https://doi.org/10.3389/frai.2026.1825067). Under the reported fixed `0.5` decision threshold, the federated model retains `AUC-ROC=0.995` while overall recall falls to `0.530` and IoMT recall to `0.290`; the paper is cited as direct motivation for separating discrimination from operating-point behavior, not as a threshold-scope comparator.

[^fedbn]: X. Li et al., “FedBN: Federated Learning on Non-IID Features via Local Batch Normalization,” *International Conference on Learning Representations (ICLR)*, 2021. [Primary paper](https://openreview.net/forum?id=6YEQUn0QICG). It supports the broader reviewer counterfactual that client-local normalization/model state can mitigate feature-shift heterogeneity; DATP-Core does not implement FedBN because BatchNorm would alter the locked autoencoder architecture.

[^kll]: Z. Karnin, K. Lang, and E. Liberty, “Optimal Quantile Approximation in Streams,” *2016 IEEE 57th Annual Symposium on Foundations of Computer Science (FOCS)*, pp. 71–78, 2016. [arXiv:1603.05346](https://arxiv.org/abs/1603.05346).

[^datasketches-kll]: Apache DataSketches, [“KLL Sketch Accuracy and Size Vs K and N”](https://datasketches.apache.org/docs/KLL/KLLAccuracyAndSize.html) and [“Understanding KLL Bounds”](https://datasketches.apache.org/docs/KLL/UnderstandingKLLBounds.html). The implementation documentation specifies normalized-rank error as a function of `k` and documents the approximately `0.68%` single-sided error for `k=400` under its 99% rank-bound convention; this is an implementation/reference bound, not a DATP result.

[^split-conformal]: J. Lei, M. G’Sell, A. Rinaldo, R. J. Tibshirani, and L. Wasserman, “Distribution-Free Predictive Inference for Regression,” *Journal of the American Statistical Association*, 2018. DOI: [10.1080/01621459.2017.1307116](https://doi.org/10.1080/01621459.2017.1307116). Supports finite-sample split-conformal rank correction under exchangeability.

[^fed-conformal-label-shift]: V. Plassier et al., “Conformal Prediction for Federated Uncertainty Quantification Under Label Shift,” *Proceedings of ICML*, PMLR 202, 2023. [Primary paper](https://proceedings.mlr.press/v202/plassier23a.html). Supports caution that federated distribution shift requires explicit treatment for conformal validity.

[^fed-conformal-heterogeneity]: V. Plassier et al., “Efficient Conformal Prediction under Data Heterogeneity,” *Proceedings of AISTATS*, PMLR 238, 2024. [Primary paper](https://proceedings.mlr.press/v238/plassier24a.html). Supports treating agent heterogeneity and non-exchangeability as substantive conformal-prediction issues.

[^ari]: L. Hubert and P. Arabie, “Comparing Partitions,” *Journal of Classification*, 1985. DOI: [10.1007/BF01908075](https://doi.org/10.1007/BF01908075). Supports adjusted Rand index for chance-adjusted comparison of cluster assignments.
