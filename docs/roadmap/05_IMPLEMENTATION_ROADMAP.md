# 05 — Implementation Roadmap

## Purpose

This document converts the DATP-Core scientific plan into an executable sequence.

It defines:

- which implementation capabilities must exist;
- which analyses reuse frozen artifacts;
- which analyses require new preprocessing or training;
- the order of work;
- the gate that must pass before each stage;
- configuration, determinism, provenance, and resumability requirements;
- the evidence required before implementation may be called scientifically complete.

It does **not** define source folders, classes, dataclasses, enums, APIs, method signatures, or module boundaries. Those belong to the architecture documentation.

Related files:

- [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md)
- [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md)
- [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md)
- [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md)
- [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md)
- [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md)

---

# 1. Implementation boundary

## 1.1 From-scratch codebase

DATP-Core is implemented from scratch.

The original DATP project:

```text
/home/naslouby/Projects/datp
```

is consulted only to recover scientific behavior:

- B0–B4 semantics;
- calibration and test split meaning;
- historical seed behavior;
- score reuse across threshold policies;
- historical checkpoint behavior;
- conference result interpretation.

Its source layout, APIs, technical debt, names, defaults, and compatibility behavior are not inherited.

## 1.2 No compatibility work

Do not create:

- backward-compatibility shims;
- import redirects;
- path aliases;
- legacy wrappers;
- duplicate old and new policy names;
- migration layers;
- temporary adapters intended only to preserve the old repository.

Scientific equivalence is required. Software equivalence is not.

## 1.3 Scientific behavior that must remain unchanged

The new implementation must preserve:

- fixed-detector comparison across B1–B4;
- benign-only calibration;
- the natural N-BaIoT physical-device population;
- conference-anchor semantics;
- deterministic seed interpretation;
- the locked client eligibility rule;
- exact metric semantics;
- the confirmatory B1-versus-B2 contrast;
- score-artifact reuse across threshold policies.

---

# 2. Execution principles

## 2.1 Configuration is authoritative

Every result-affecting value must come from validated configuration, including:

- dataset and regime;
- client definition;
- split policy;
- model and training settings;
- seeds;
- round budget and checkpoint candidates;
- checkpoint selector;
- batch sizes;
- quantile target;
- eligibility minimum;
- cluster count and fingerprint;
- shrinkage and calibration-size grids;
- conformal significance level;
- comparator grids;
- bootstrap settings;
- temporal materiality thresholds;
- reporting profile.

No scientific value may be hidden in an implementation default.

## 2.2 Missing values fail explicitly

A missing scientific value must produce:

- configuration validation failure;
- blocked readiness;
- or typed infeasibility.

It must not silently choose a seed, checkpoint, quantile, batch size, cluster count, shrinkage value, bootstrap count, or comparator parameter.

## 2.3 Stage separation

Implementation must preserve this sequence:

```text
source validation
→ client assignment
→ split construction
→ preprocessing
→ training
→ checkpoint selection
→ score generation
→ threshold estimation
→ metric evaluation
→ statistical analysis
→ reporting
→ result freeze
```

A downstream stage may reuse a validated upstream artifact.

It must not silently recompute or mutate it.

## 2.4 Typed outcomes

Each stage ends with one of:

```text
completed
completed_with_warnings
infeasible
failed_validation
failed_execution
blocked_by_dependency
```

An empty file or missing row is never used as a failure signal.

## 2.5 Idempotency and resumption

Rerunning the same resolved configuration must:

- resolve to the same experiment identity;
- reuse compatible immutable artifacts;
- avoid duplicate result families;
- resume from the latest valid stage;
- reject stale or incompatible artifacts;
- never overwrite a frozen result.

Examples:

- threshold changes reuse scores;
- reporting changes reuse statistics;
- scoring resumes from checkpoints;
- failed exports do not retrain models.

---

# 3. Configuration contract

## 3.1 Conceptual configuration domains

The resolved configuration must distinguish:

- dataset;
- client partition;
- split;
- preprocessing;
- model;
- training;
- checkpoint;
- scoring;
- threshold policy;
- metrics;
- statistics;
- reporting;
- runtime resources.

The physical number of files is an architecture decision.

## 3.2 Resolved configuration artifact

Persist the fully resolved configuration after:

- inheritance;
- references;
- environment substitution;
- runtime-profile selection;
- allowed overrides;
- validation.

The persisted resolved form is the scientific execution input.

## 3.3 Configuration fingerprint

A deterministic fingerprint must change when any result-affecting value changes.

It should remain stable across comments, key ordering, irrelevant whitespace, and machine-specific path presentation.

## 3.4 Required validation

Reject configurations that request:

- B3 without a valid family taxonomy;
- B3 on Edge-IIoTset;
- temporal execution without verified timestamps;
- attack-sensitive client metrics without attack assignment;
- B4 with more clusters than eligible clients;
- invalid shrinkage values;
- duplicate or missing seeds;
- missing checkpoint selection;
- retired names such as `B5` or `B3-LGS`;
- an unknown comparator;
- an implicit batch-size change;
- an unavailable metric without explicit unavailability handling.

## 3.5 Descriptive experiment identity

Opaque experiment codes must not be the sole identity.

An execution must be understandable from its:

- regime;
- scientific purpose;
- policy or comparator;
- seed;
- declared variation.

---

# 4. Data readiness and splits

## 4.1 Source validation

Before preprocessing, validate:

- expected files;
- schema;
- feature order;
- labels;
- numeric validity;
- client metadata;
- timestamps where required;
- benign and attack support;
- duplicate behavior;
- deterministic source ordering;
- source fingerprint.

No data defect is silently repaired.

## 4.2 Dataset-specific gates

### N-BaIoT

Verify:

- nine physical-device clients;
- expected benign and attack artifacts;
- anchor feature semantics;
- family taxonomy where B3 is used;
- calibration and test support;
- no cross-client leakage.

### CICIoT2023 file-defined regime

Verify:

- exact processed artifact;
- file-defined pseudo-client population;
- actual feature schema;
- missing or available device metadata;
- missing or available timestamps;
- artifact-specific scope.

Do not infer physical devices from source-paper descriptions.

### Controlled Dirichlet regime

Verify:

- twenty synthetic clients;
- full alpha grid;
- deterministic partition seed;
- complete row accounting;
- immutable partition manifest.

### Edge-IIoTset external regime

Verify:

- audited benign sensor-group population;
- expected ten groups;
- eligible-benign coverage;
- attack-assignment limitation;
- B3 unavailability.

### Edge-IIoTset temporal regime

Verify:

- expected nine temporal groups;
- explicit Modbus exclusion;
- genuine timestamps;
- stable duplicate-time handling;
- sufficient rows for every temporal window;
- no future leakage.

## 4.3 Readiness report

Each dataset/regime produces a readiness report containing:

- source fingerprint;
- schema summary;
- client and row counts;
- class counts;
- metadata availability;
- projected eligibility;
- attack-evaluability;
- timestamp validity;
- blocking defects;
- final readiness status.

Training is blocked when readiness fails.

## 4.4 Client assignment

Every row maps to exactly one:

- valid client;
- or explicit excluded/unresolved category.

Assignment must be deterministic and must not depend on row order, test outcome, or model score.

## 4.5 Split manifest

Persist row-level membership in:

```text
training
calibration
test
```

or:

```text
historical_training
historical_calibration
future_recalibration
future_evaluation
```

Validate:

- disjointness;
- row coverage;
- client consistency;
- class availability;
- expected proportions;
- eligibility;
- chronology;
- absence of future leakage.

A manifest used by frozen downstream artifacts is immutable.

---

# 5. Preprocessing

Preprocessing is fitted only on the permitted benign training population.

Calibration, test, and temporal future records may be transformed but cannot influence fit.

Persist:

- fitted parameters;
- input and output feature order;
- excluded columns;
- fit-population identity;
- source and split references;
- configuration fingerprint;
- validation summary.

Validate:

- finite output;
- expected dimensions;
- deterministic transformation;
- traceable row ordering;
- no label leakage;
- no test or future leakage;
- no accidental inclusion of client identifiers as model features.

Different datasets or incompatible schemas require separate preprocessing artifacts.

---

# 6. Training and checkpoints

## 6.1 Training identity

A training run is identified by:

- dataset and regime;
- client partition;
- split manifest;
- preprocessing artifact;
- model configuration;
- training configuration;
- seed;
- training algorithm.

Threshold policy is not part of the core FedAvg training identity.

## 6.2 Core FedAvg

The core ladder uses:

- the locked autoencoder family;
- one local epoch;
- full participation;
- deterministic seeds;
- the locked round budget;
- GPU training under the main runtime profile;
- mandatory batching.

B1–B4 reuse the same trained model within a seed and regime.

## 6.3 Anchor execution

The anchor preserves historical conference semantics, including its historical training endpoint and checkpoint behavior.

It is not retrofitted with journal checkpoint selection merely to improve agreement.

## 6.4 Journal execution

Journal training:

- runs to 200 rounds;
- saves checkpoints at `25, 50, 75, 100, 125, 150, 200`;
- records convergence without stopping early;
- uses the frozen non-test primary-round selector.

## 6.5 Primary round

Regime A selects one primary **round number**.

The selected round number is reused where the protocol requires common journal checkpoint semantics.

Weights remain seed- and regime-specific.

Checkpoint selection must not use:

- held-out attack labels;
- test AUROC;
- FPR or `CV(FPR)`;
- Macro-F1;
- the B1-versus-B2 effect;
- external or stress-test results.

Persist the candidates, selector input, selected round, tie-break, and reason.

## 6.6 FedProx

FedProx requires separate training artifacts.

It must:

- execute the locked coefficient grid;
- retain every coefficient outcome;
- record non-convergence;
- avoid adding a coefficient after outcome inspection;
- keep scores separate from FedAvg.

## 6.7 Ditto

Genuine Ditto requires:

- a global model;
- persistent personalized client states;
- the correct proximal personalized objective;
- separate global and personalized provenance;
- no aggregation of personalized states.

If these conditions are not met, use the actual implemented method name.

## 6.8 Resource discipline

Scientific batch sizes are configuration-controlled.

Do not silently reduce batch sizes, sample counts, rounds, seeds, or clients to fit available resources.

Resource pressure produces:

- blocked execution;
- an approved runtime-profile revision;
- or a formally reviewed scientific configuration change.

## 6.9 Training output

Persist:

- model state;
- round and seed;
- client participation;
- optimizer state when resumption requires it;
- per-round diagnostics;
- convergence status;
- runtime summary;
- configuration fingerprint;
- split and preprocessing references;
- completion status.

---

# 7. Score artifacts

## 7.1 Role

Scores form the boundary between training and threshold analysis.

A valid score artifact allows threshold policies to run without retraining or reloading the model.

## 7.2 Required content

Where supported, persist per client:

- benign calibration scores;
- benign test scores;
- attack test scores;
- future recalibration scores;
- future evaluation scores.

Each record preserves:

- row identity;
- client;
- split;
- label where permitted;
- anomaly score;
- model identity;
- checkpoint;
- seed;
- preprocessing identity;
- score orientation.

## 7.3 Validation

Validate:

- finite scores;
- exact row-count agreement with manifests;
- stable client assignment;
- no duplicate row identity;
- fixed score orientation;
- identical B1–B4 score inputs;
- no threshold application during scoring;
- AUROC invariance inputs.

Validated scores are immutable.

Any correction invalidates dependent thresholds, metrics, statistics, tables, and figures.

---

# 8. Threshold estimation

## 8.1 Common output

Every threshold estimator records:

- policy or comparator;
- scope;
- threshold value or values;
- client or group assignment;
- calibration count;
- quantile or operating point;
- resolved parameters;
- source score identity;
- eligibility;
- status.

## 8.2 Core policies

Implement B1, B2, B3, and B4 according to [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md#5-threshold-policy-system).

Reject unsupported combinations.

## 8.3 Shared controls

Keep distinct identities for:

- arithmetic mean of local quantiles;
- exact pooled benign quantile;
- sample-weighted shared threshold.

## 8.4 Shrinkage

Execute the complete locked lambda grid.

A size-aware rule must be explicitly configured before test evaluation.

Do not select one favorable lambda post hoc.

## 8.5 B2-conf

Use benign calibration scores only.

Persist:

- significance level;
- finite-sample rank;
- threshold;
- calibration count;
- attainability status;
- held-out coverage result.

Do not convert a conformal diagnostic into a universal validity claim.

## 8.6 B4

Preserve:

- the locked four-scalar fingerprint;
- deterministic feature scaling;
- canonical `K = 3`;
- configured clustering seed;
- client membership;
- cluster size;
- singleton or empty-cluster status;
- cluster threshold construction.

Alternative `K` values produce separate exploratory artifacts.

---

# 9. `B-FedStatsBenign`

## 9.1 Client message

Each eligible client contributes benign-only:

- count \(n_k\);
- mean \(\mu_k\);
- variance \(\sigma_k^2\);
- exceedance counts for the fixed candidate grid.

Raw scores and attack labels are not part of this comparator message.

## 9.2 Aggregation

\[
\mu_{global}
=
\frac{\sum_k n_k\mu_k}{\sum_k n_k}
\]

\[
within
=
\frac{\sum_k n_k\sigma_k^2}{\sum_k n_k}
\]

\[
between
=
\frac{\sum_k n_k(\mu_k-\mu_{global})^2}{\sum_k n_k}
\]

\[
\sigma^2_{global}
=
within+between
\]

The between-client mean-shift term is mandatory.

## 9.3 Candidate grid

\[
\tau(k)
=
\mu_{global}
+
k\sigma_{global}
\]

with:

```text
k = 0.00, 0.01, ..., 5.00
```

## 9.4 Matched exceedance

Select:

\[
k^*
=
\arg\min_k
|
AchievedExceedance(k)-(1-q)
|
\]

Tie-break toward the larger \(k\).

Persist:

- every candidate;
- achieved exceedance;
- attainment error;
- selected coefficient;
- tie set;
- tie-break result.

## 9.5 Required diagnostics

Report:

- `within`;
- `between`;
- pooled variance;
- `between_ratio`;
- selected coefficient;
- threshold;
- target and achieved exceedance;
- transmitted fields;
- estimated payload.

Fixed coefficients `2.0`, `2.5`, and `3.0` remain supplementary.

## 9.6 Rejection conditions

Reject any implementation that:

- uses attack summaries;
- omits the between term;
- changes the candidate grid after results;
- uses a fixed coefficient as the primary comparator;
- has an unrecorded tie-break;
- uses an inconsistent variance convention;
- calls the benign comparator `B-LaridiFaithful`.

---

# 10. Metrics, statistics, and reporting

## 10.1 Metrics

Metric semantics are owned by [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md).

Implementation must:

- calculate client metrics before aggregation;
- distinguish FPR-evaluable and attack-evaluable clients;
- preserve undefined and unavailable statuses;
- use the locked `ddof`;
- keep pooled and mean-client metrics distinct;
- use full precision;
- attach the eligibility manifest.

## 10.2 Statistics

Statistical analysis consumes validated seed-level records paired by seed identity.

The confirmatory analysis must:

- require all ten paired seeds;
- calculate the locked delta;
- execute the locked BCa procedure;
- record bootstrap seed and count;
- fail explicitly when BCa is degenerate;
- keep Wilcoxon and rank-biserial results secondary.

Nested subsampling and clustering repetitions are summarized within seed.

## 10.3 Reporting

Tables and figures are generated from frozen artifacts.

Reporting profiles may change presentation only.

Exports must:

- preserve deterministic order;
- show unavailable values explicitly;
- retain negative results;
- retain all pre-specified parameter values;
- distinguish core policies from stress tests;
- attach result-manifest provenance.

Do not manually copy values into manuscript figures or tables.

---

# 11. Artifact and provenance contract

Every published result must trace through:

```text
resolved configuration
→ readiness report
→ client and split manifest
→ preprocessing
→ training
→ checkpoint
→ scores
→ thresholds
→ metrics
→ statistics
→ table or figure
```

Each artifact records:

- type and schema version;
- logical experiment identity;
- configuration fingerprint;
- parent identities;
- source revision;
- timestamp;
- completion status;
- checksum.

Before consuming an artifact, validate:

- checksum;
- schema;
- configuration compatibility;
- scientific compatibility;
- parent completeness;
- non-stale status.

Frozen artifacts are immutable.

Corrections create a new version.

Scientific execution must not depend on an ambiguous `latest` artifact.

---

# 12. Determinism

Use separate configured seed domains for:

- training;
- partitioning;
- calibration subsampling;
- clustering;
- bootstrap analysis;
- other stochastic procedures.

Where supported, enable deterministic behavior for:

- Python;
- numerical libraries;
- ML framework;
- GPU operations;
- data loading;
- client iteration;
- file discovery;
- clustering;
- bootstrap resampling.

Record:

- operating system;
- Python version;
- framework;
- CUDA and driver versions;
- GPU identity;
- dependency-lock fingerprint;
- deterministic flags;
- runtime profile.

When full determinism is unavailable, record and quantify the limitation rather than claiming bitwise reproducibility.

---

# 13. Validation requirements

## 13.1 Formula and policy validation

Validate:

- B1–B4 behavior;
- quantile interpolation;
- eligibility;
- pooled variance;
- matched-exceedance selection;
- metric formulas;
- undefined denominators;
- BCa behavior;
- temporal quantities;
- artifact fingerprints.

## 13.2 Stage contracts

Validate every boundary:

```text
split → preprocessing
preprocessing → training
training → checkpoint
checkpoint → scores
scores → thresholds
thresholds → metrics
metrics → statistics
statistics → exports
```

## 13.3 Scientific invariants

Required checks include:

- B1–B4 use identical scores;
- AUROC is invariant across B1–B4;
- eligible populations match;
- no attack data enters thresholding;
- no test metric selects checkpoints;
- no future data enters historical temporal stages;
- B3 is blocked where unsupported;
- B4 canonical `K` remains locked;
- `B-FedStatsBenign` includes the between term.

## 13.4 Anchor reproduction

Before expansion claims:

- reproduce the five-seed anchor;
- compare every reference value;
- explain material discrepancies;
- block expansion claims while discrepancies remain unresolved.

## 13.5 End-to-end validation

At least one bounded run validates the complete path from configuration to export.

Synthetic fixtures may validate formulas and contracts, but cannot substitute for real-data scientific evidence.

---

# 14. Failure and infeasibility

Expected scientific infeasibility includes:

- missing client metadata;
- invalid timestamps;
- insufficient eligible clients;
- unsupported attack assignment;
- impossible cluster count;
- unavailable traffic rate;
- missing metric denominators;
- degenerate BCa;
- non-convergent stress-test training.

Do not recover by:

- inventing clients;
- using row order as time;
- lowering eligibility after results;
- imputing unsupported attack metrics;
- adding favorable hyperparameters;
- silently reducing scientific workload;
- replacing the external dataset;
- renaming an unsupported method.

Operational retries are allowed only when scientific inputs and configuration are unchanged and the retry is recorded.

A scientific configuration change creates a new experiment identity.

---

# 15. Execution sequence

## Stage 0 — Readiness foundation

Implement and validate:

- configuration resolution;
- fingerprints;
- readiness reporting;
- client assignment;
- split manifests;
- preprocessing;
- stage status;
- deterministic seed handling.

**Gate:** N-BaIoT anchor readiness and split validation pass.

## Stage 1 — Anchor reproduction

Execute:

- historical five-seed cohort;
- historical checkpoint semantics;
- B0–B4 anchor behavior;
- historical metrics;
- discrepancy audit.

**Gate:** no unresolved material reproduction discrepancy.

## Stage 2 — Journal Regime A

Execute:

- ten-seed FedAvg training;
- journal checkpoint grid;
- primary-round selection;
- score generation;
- B1 and B2 confirmatory metrics;
- BCa analysis.

**Gate:** ten valid paired seed records and frozen primary scores.

## Stage 3 — Stored-score extensions

Using frozen Regime A scores, execute:

- shared-threshold controls;
- quantile sensitivity;
- B3 and B4;
- cluster stability and ablation;
- CDF and threshold-shift mechanisms;
- calibration-size analyses;
- shrinkage;
- B2-conf;
- `B-FedStatsBenign`;
- optional equity and communication outputs.

**Gate:** no retraining or score mutation.

## Stage 4 — Controlled heterogeneity

Execute all Regime C alpha conditions with:

- deterministic partitions;
- complete manifests;
- required training;
- B1/B2/B4 evaluation;
- heterogeneity diagnostics.

**Gate:** every condition has valid and comparable client coverage.

## Stage 5 — Edge-IIoTset external validation

Execute:

- readiness audit reproduction;
- ten benign sensor groups;
- preprocessing and training;
- B1, B2, B4, and `B-FedStatsBenign`;
- external statistics;
- typed attack-metric unavailability.

**Gate:** client assignment and benign eligibility pass.

## Stage 6 — Training-side stress tests

Execute:

1. FedProx;
2. genuine Ditto or the formally approved actual alternative.

Each requires independent training and scores.

**Gate:** no reuse of FedAvg scores as a substitute for retraining.

## Stage 7 — Temporal experiment

Execute:

- nine temporal groups;
- verified chronology;
- 55/15/10/20 split;
- static reference;
- frozen historical thresholds;
- one-shot recalibration;
- future evaluation;
- recovery statistics.

**Gate:** timestamp and leakage validation pass.

## Stage 8 — Reporting and freeze

Generate:

- main tables;
- supplementary tables;
- figures;
- audit exports;
- final manifests;
- claim-decision inputs.

**Gate:** result-freeze requirements in [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md#22-result-freeze) pass.

---

# 16. Artifact reuse rules

## 16.1 Reuse frozen scores for

- B1–B4 threshold recomputation;
- shared controls;
- quantile sensitivity;
- shrinkage;
- B2-conf;
- calibration subsampling;
- `B-FedStatsBenign`;
- score-distribution analysis;
- threshold-shift analysis;
- optional equity reporting.

## 16.2 Retrain for

- missing anchor or journal seeds;
- regime-specific Dirichlet training;
- Edge-IIoTset;
- FedProx;
- Ditto or another personalized model;
- chronological training with a different split;
- B0 centralized reference.

## 16.3 Never reuse scores when changing

- dataset;
- regime;
- client partition;
- split;
- preprocessing;
- model;
- training algorithm;
- seed;
- checkpoint;
- feature schema.

---

# 17. Completion criteria

Implementation is scientifically ready only when:

- anchor reproduction is audited;
- no hidden scientific defaults remain;
- readiness reports and split manifests validate;
- B1–B4 reuse identical models and scores;
- checkpoint selection is test-independent;
- all required checkpoints and scores exist;
- threshold policies pass contract validation;
- `B-FedStatsBenign` uses full pooled variance;
- metrics preserve undefined and unavailable values;
- ten paired seeds support the confirmatory analysis;
- BCa execution is reproducible;
- Edge-IIoTset limitations are enforced;
- temporal leakage checks pass;
- figures and tables trace to frozen artifacts;
- every mandatory experiment has a terminal status.

“Code exists” is not completion.

“Tests pass” is not completion when scientific gates or artifacts remain incomplete.

---

# 18. Implementation audit checklist

## Configuration

- [ ] Every scientific value is explicit.
- [ ] Resolved configuration is persisted.
- [ ] Fingerprints are deterministic.
- [ ] Invalid combinations are rejected.
- [ ] Retired names are rejected.
- [ ] No hidden result-affecting default remains.

## Data and training

- [ ] Sources are fingerprinted.
- [ ] Client assignment is deterministic.
- [ ] Splits are disjoint and reconstructable.
- [ ] Temporal splits use real chronology.
- [ ] Core training is policy-independent.
- [ ] Anchor and journal checkpoint semantics are distinct.
- [ ] All journal checkpoints exist.
- [ ] Resource pressure did not silently alter the protocol.

## Scores and thresholds

- [ ] B1–B4 use identical scores.
- [ ] Scores are immutable.
- [ ] B3 is blocked without taxonomy.
- [ ] B4 uses the locked fingerprint and canonical `K`.
- [ ] Shrinkage and quantile grids are complete.
- [ ] B2-conf is benign-only.
- [ ] `B-FedStatsBenign` includes the between term.
- [ ] Tie-breaking is deterministic.

## Metrics and statistics

- [ ] Client metrics precede aggregation.
- [ ] FPR-evaluable and attack-evaluable populations are distinct.
- [ ] Undefined values are not converted to zero.
- [ ] Ten paired seed records exist.
- [ ] BCa uses paired seed deltas.
- [ ] Nested repetitions do not inflate sample size.
- [ ] Secondary analyses remain secondary.

## Provenance and reporting

- [ ] Every artifact references its parents.
- [ ] Checksums and schema versions validate.
- [ ] Frozen artifacts are immutable.
- [ ] No ambiguous `latest` dependency exists.
- [ ] Tables and figures use frozen manifests.
- [ ] Negative results remain visible.
- [ ] Every mandatory experiment has a terminal status.

Any failed locked item blocks scientific completion until corrected or recorded as infeasible in [07](./07_AUDIT_AND_DECISION_LOG.md).