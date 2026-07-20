# 06 — Reviewer Risks and Readiness

## Purpose

This document identifies the reviewer attacks most likely to threaten DATP-Core and defines the evidence required to answer them.

It owns:

- reviewer-risk prioritization;
- defence requirements;
- residual-risk classification;
- scientific and manuscript readiness;
- submission blockers;
- final reviewer-readiness audits.

It does not redefine claims, experiments, metrics, or implementation.

Related files:

- [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md)
- [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md)
- [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md)
- [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md)
- [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md)
- [07 — Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md)

All readiness items remain unchecked until supported by executed evidence. Rewriting this document does not mark any item complete.

---

# 1. Readiness states

Use the following states consistently.

**Not ready**  
Required evidence or wording is missing.

**Partially ready**  
Some evidence exists, but a material objection remains unanswered.

**Evidence ready**  
The required experiment, audit, and artifacts exist.

**Manuscript ready**  
Evidence is interpreted correctly and limitations are explicit.

**Accepted residual risk**  
The limitation cannot be removed within scope but is disclosed.

**Blocking risk**  
The issue prevents a claim, result family, submission, or the complete paper.

---

# 2. Priority risks

## Highest risks

1. **Model-personalization absorption**  
   Ditto may remove most of the B1-versus-B2 gain.

2. **Laridi novelty overlap**  
   Federated summary-statistics thresholding may substantially overlap the claimed contribution.

3. **Calibration tautology**  
   A reviewer may argue that B2 reduces FPR dispersion by construction.

4. **External client validity**  
   Edge-IIoTset and CICIoT2023 client definitions may be challenged.

5. **Conference-extension originality**  
   The manuscript may appear too close to the conference paper.

## Important accepted limitations

- nine natural N-BaIoT clients;
- one external dataset;
- incomplete Edge-IIoTset client-level attack evaluation;
- one bounded temporal experiment;
- no formal privacy;
- no hardware validation;
- possible ten-seed confidence-interval widening;
- one aggregation and one model-personalization stress test.

These limitations narrow claims but do not invalidate a valid Regime A confirmatory result.

---

# 3. Contribution and novelty risks

## 3.1 Thresholding is “only post-processing”

**Attack**  
The paper does not introduce a new detector and therefore lacks contribution.

**Defence**

- freeze the detector and score artifacts;
- change only threshold-calibration scope;
- show AUROC invariance;
- show material per-client FPR changes;
- frame the contribution as deployment operating-point reliability.

**Evidence required**

- ten-seed B1-versus-B2 result;
- identical B1–B4 score lineage;
- AUROC invariance check;
- per-client FPR;
- threshold-shift and score-distribution analyses.

**Readiness**

- [ ] Same model and scores verified across B1–B4.
- [ ] AUROC invariance verified.
- [ ] Client operating-point effects reported.
- [ ] Manuscript does not claim a new detector.

**Residual risk:** moderate.

---

## 3.2 Laridi et al. already perform federated thresholding

**Attack**  
Federated autoencoder thresholding from distributed summary statistics already exists.

**Defence**

Distinguish:

- anomaly-informed versus benign-only calibration;
- one shared summary threshold versus threshold-scope personalization;
- pooled performance versus cross-client FPR equity;
- Laridi-faithful reproduction versus `B-FedStatsBenign`.

**Evidence required**

- primary-paper comparison;
- matched-exceedance `B-FedStatsBenign`;
- full pooled variance;
- within and between terms;
- B1/B2/comparator result;
- explicit non-faithful naming.

**Readiness**

- [ ] Laridi method verified from the primary paper.
- [ ] Benign-only distinction is precise.
- [ ] Comparator protocol was frozen before computation.
- [ ] Between-client mean shift is included.
- [ ] Matched-exceedance result exists.
- [ ] No “Laridi-faithful” wording is used for the benign adaptation.

**Residual risk:** high until comparator and positioning are complete.

---

## 3.3 B4 is ordinary clustering

**Attack**  
Applying k-means to four score summaries is not novel.

**Defence**

Do not claim clustering novelty.

The contribution is testing whether data-driven threshold-sharing scope on a fixed detector provides a stable intermediate operating point.

**Evidence required**

- canonical `K = 3`;
- B1/B3/B4/B2 comparison;
- recovery fraction;
- memberships and cluster sizes;
- adjusted Rand stability;
- within/across dispersion;
- fingerprint ablation;
- distinction from clustered model training.

**Readiness**

- [ ] Canonical B4 setting is frozen.
- [ ] Alternative `K` values are exploratory.
- [ ] Memberships and stability are reported.
- [ ] Fingerprint ablation is complete.
- [ ] Related work distinguishes threshold clustering from model clustering.
- [ ] No new-clustering-algorithm claim appears.

**Residual risk:** moderate.

---

## 3.4 Shrinkage and quantiles are standard methods

**Attack**  
The journal extension is a collection of textbook tools.

**Defence**

Position them as bounded analyses of:

- calibration scarcity;
- estimator stability;
- target attainment;
- partial pooling;
- shared-versus-local threshold scope.

**Readiness**

- [ ] No new statistical-theory claim appears.
- [ ] Full calibration and shrinkage curves are reported.
- [ ] No favorable value is selected post hoc.
- [ ] Quantile framing is described as a methods backbone.
- [ ] Negative behavior remains visible.

**Residual risk:** low when claims remain narrow.

---

## 3.5 Conference overlap is too high

**Attack**  
The journal paper is not a sufficiently extended work.

**Defence**

The paper must visibly add:

- ten-seed evidence;
- stronger statistics;
- Edge-IIoTset;
- invalid-partition rejection;
- matched threshold comparator;
- FedProx and Ditto;
- calibration robustness;
- B2-conf;
- mechanism analyses;
- temporal recalibration;
- stronger provenance and negative-result handling.

**Readiness**

- [ ] Conference paper is cited.
- [ ] Extension is disclosed.
- [ ] New contributions are enumerated.
- [ ] Figures are redrawn or materially extended.
- [ ] Tables are extended or replaced.
- [ ] Overlap audit is complete.
- [ ] The self-imposed 40% target is not presented as publisher policy.
- [ ] Cover letter explains the extension.

**Blocking level:** submission-blocking.

---

# 4. Confirmatory-methodology risks

## 4.1 B2 reduces FPR dispersion by construction

**Attack**  
The primary finding is predetermined by per-client quantile calibration.

**Defence**

Distinguish calibration exceedance from held-out test FPR.

Explain that test FPR depends on:

- finite calibration;
- calibration/test shift;
- client score distribution;
- sample size;
- threshold-estimation error.

**Evidence required**

- disjoint calibration and test splits;
- held-out FPR;
- calibration-size analysis;
- target-attainment error;
- B2-conf;
- shared-construction controls;
- absolute dispersion.

**Readiness**

- [ ] Calibration and test are disjoint.
- [ ] Held-out FPR is the endpoint.
- [ ] Tautology explanation is included.
- [ ] B2-conf is evaluated.
- [ ] Calibration-size analysis is complete.
- [ ] No claim of guaranteed test-FPR equality appears.

**Residual risk:** high until fully addressed.

---

## 4.2 Local thresholds overfit

**Attack**  
B2 benefits only from highly tailored or noisy calibration.

**Defence**

Use:

- held-out test results;
- repeated calibration subsampling;
- threshold variance;
- calibration-size curves;
- shrinkage;
- B2-conf;
- complete detection trade-offs.

**Readiness**

- [ ] Full calibration-size grid exists.
- [ ] Nested subsamples do not inflate seed count.
- [ ] Threshold variance is reported.
- [ ] Shrinkage curve is complete.
- [ ] Small-sample collapse is not hidden.
- [ ] Detection trade-offs remain visible.

**Residual risk:** moderate after the complete analysis.

---

## 4.3 `CV(FPR)` is fragile

**Attack**  
CV can be unstable when mean FPR is near zero.

**Defence**

Always report:

- mean FPR;
- IQR;
- range;
- worst-client FPR;
- client-level values;
- near-zero status.

Optional Jain and Gini values may supplement but not replace CV.

**Readiness**

- [ ] `ddof=0` is fixed.
- [ ] Zero-mean CV is undefined.
- [ ] Near-zero handling is configured.
- [ ] Absolute dispersion accompanies CV.
- [ ] No metric switch occurs after results.

**Residual risk:** low when protocol is followed.

---

## 4.4 Checkpoint cherry-picking

**Attack**  
The selected round maximizes the DATP effect.

**Defence**

Use one non-test Regime A selector, frozen before outcome inspection, and show all checkpoint trajectories.

**Readiness**

- [ ] Selector is explicitly configured.
- [ ] No test or attack metric enters selection.
- [ ] All candidate checkpoints exist.
- [ ] One round is reused where required.
- [ ] Full trajectories remain available.
- [ ] B1 and B2 do not use different rounds.

**Blocking level:** confirmatory-result blocking.

---

## 4.5 Post-hoc selection of `K`, quantile, or calibration size

**Attack**  
Flexible grids permit favorable selection.

**Defence**

Freeze:

- B4 `K = 3`;
- exploratory alternative `K`;
- quantile grid;
- calibration-size grid;
- shrinkage grid;
- conformal level;
- FedProx grid;
- personalization rule;
- temporal recovery threshold.

**Readiness**

- [ ] Every grid exists in resolved configuration.
- [ ] Every grid value is reported.
- [ ] Canonical settings are unchanged.
- [ ] Deviations appear in the audit log.
- [ ] Exploratory results are labeled.

---

## 4.6 Ten seeds weaken the conference result

**Attack**  
The original result may not reproduce or may be less certain.

**Defence**

- reproduce the historical five-seed subset;
- audit discrepancies;
- use the ten-seed result as authoritative;
- never substitute the stronger conference interval.

**Readiness**

- [ ] Five-seed reproduction completed.
- [ ] Discrepancy report exists.
- [ ] Material differences are resolved or blocking.
- [ ] Ten-seed evidence is primary.
- [ ] Conference values are labeled historical.

**Blocking level:** final confirmatory interpretation while unresolved.

---

# 5. Comparator risks

## 5.1 FedProx is unfairly implemented

**Defence requirements**

- frozen coefficient grid;
- comparable training settings;
- independent models and scores;
- every coefficient retained;
- convergence failures reported;
- no post-hoc coefficient.

**Readiness**

- [ ] Grid frozen.
- [ ] Comparison settings documented.
- [ ] Every coefficient has a terminal status.
- [ ] FedAvg scores are not reused.
- [ ] Convergence diagnostics are reported.
- [ ] FedProx remains a stress test.

---

## 5.2 The model-personalization comparator is not genuine Ditto

**Defence requirements**

A Ditto-labelled implementation must have:

- global state;
- persistent personalized states;
- genuine proximal personalized objective;
- no aggregation of personalized states;
- separate provenance.

Otherwise use the actual method name.

**Readiness**

- [ ] Algorithm checked against the primary paper.
- [ ] Personalized state persistence verified.
- [ ] Global and personalized artifacts are separate.
- [ ] Hyperparameter selection is non-test.
- [ ] Fallback naming is honest.

**Blocking level:** blocks any claim using the name Ditto.

---

## 5.3 Model personalization makes DATP obsolete

**Attack**  
Personalized models may remove the need for threshold personalization.

**Defence**

Evaluate all four corners:

- FedAvg + B1;
- FedAvg + B2;
- personalized model + B1;
- personalized model + B2.

Apply the locked absorption bands without adjustment.

**Readiness**

- [ ] All four corners exist.
- [ ] Every score comes from the correct model.
- [ ] Thresholds are recomputed on personalized scores.
- [ ] Absorption is calculated exactly.
- [ ] Cost differences are reported.
- [ ] Claim wording matches the observed band.

**Residual risk:** high until executed; accepted after honest reporting.

---

# 6. Dataset and client risks

## 6.1 CICIoT2023 pseudo-clients are not physical clients

**Defence**

Treat the available partition as a file-defined applicability boundary only.

**Readiness**

- [ ] Actual artifact schema is reverified.
- [ ] File-defined client construction is documented.
- [ ] Device-aware wording is removed.
- [ ] Physical-device repartition remains suppressed.
- [ ] Row order and merge order are not used.
- [ ] Actual feature count is verified before print.

**Blocking level:** quantitative CICIoT2023 claims until verified.

---

## 6.2 Edge-IIoTset client mapping is ambiguous

**Defence**

Use the first-principles full-corpus audit.

**Readiness**

- [ ] Ten benign sensor groups reproduce.
- [ ] Endpoint normalization is documented.
- [ ] Eligible-benign coverage is reported.
- [ ] Endpoint-unresolved benign rows are retained in their folder-defined client and reported for provenance.
- [ ] Attack-sensitive metric unavailability is enforced.
- [ ] B3 is not executed.

**Blocking level:** external-validation claim.

---

## 6.3 External validation is null or opposite

**Defence**

External evidence is non-confirmatory and has pre-specified null and reversal wording.

**Readiness**

- [ ] It is not described as second confirmation.
- [ ] Null/reversal wording is prepared.
- [ ] Dataset differences are discussed.
- [ ] No replacement partition is introduced.
- [ ] Material negative evidence remains in the main paper.

**Residual risk:** accepted.

---

## 6.4 Natural client count is small

**Defence**

Acknowledge:

- nine natural N-BaIoT clients;
- complete display of all clients;
- seeds do not increase client count;
- synthetic clients are sensitivity evidence;
- no fleet-scale claim.

**Readiness**

- [ ] All natural clients are shown.
- [ ] Client and seed counts are not conflated.
- [ ] No fleet-scale language appears.
- [ ] Limitation is explicit.

**Residual risk:** accepted.

---

# 7. Interpretation risks

## 7.1 AUROC does not improve

**Response**

AUROC is a model-quality control. It should remain invariant across fixed-score threshold policies.

**Readiness**

- [ ] AUROC invariance is verified.
- [ ] AUROC is not the threshold verdict.
- [ ] Any policy-dependent difference is treated as a defect.

---

## 7.2 Macro-F1 trade-off is hidden

**Defence**

Report:

- P10 Macro-F1;
- worst-client balanced accuracy;
- per-client TPR;
- complete client score geometry;
- low-separability client evidence.

**Readiness**

- [ ] P10 degradation is in the main paper.
- [ ] No general Macro-F1 improvement claim appears.
- [ ] All clients remain in the analysis.
- [ ] Detection cost is discussed.

**Blocking level:** submission-blocking if hidden.

---

## 7.3 Family labels are arbitrary

**Defence**

B3 is a physical-taxonomy mechanism baseline, not an assumed optimum.

Weak B3 performance may show that physical taxonomy does not align with calibration structure.

**Readiness**

- [ ] Family taxonomy is artifact-grounded.
- [ ] B3 remains a mechanism baseline.
- [ ] Weak performance is retained.
- [ ] B4 is not retroactively justified by rewriting B3.

---

## 7.4 Heterogeneity analysis claims causation

**Defence**

Use associative language and report full diagnostics.

**Readiness**

- [ ] “Associated with” replaces causal wording.
- [ ] Spearman and regression diagnostics are reported.
- [ ] All observations are shown.
- [ ] Weak association remains visible.

---

# 8. Scope and framing risks

## 8.1 False-positive fairness is not human fairness

**Defence**

Define fairness as operational false-alarm equity.

Prefer:

- operating-point equity;
- false-alarm equity;
- cross-client FPR dispersion.

**Readiness**

- [ ] Definition appears at first use.
- [ ] No protected-attribute meaning is implied.
- [ ] Title, abstract, and conclusion use precise wording.
- [ ] “Fair detector” wording is removed.

---

## 8.2 No privacy guarantee

**Defence**

State:

- raw data stay local;
- no differential privacy;
- no secure aggregation;
- no formal leakage bound;
- threshold summaries may disclose information;
- B4 is not a privacy mechanism.

**Readiness**

- [ ] No privacy-preserving claim appears.
- [ ] Message contents are disclosed.
- [ ] Privacy limitation is explicit.
- [ ] Formal privacy remains future work.

**Residual risk:** accepted.

---

## 8.3 No deployment measurement

**Defence**

Distinguish:

- estimated payload;
- serialized size;
- measured network traffic;
- hardware measurements.

**Readiness**

- [ ] No edge-ready or lightweight claim appears.
- [ ] Alert burden uses a real or cited rate.
- [ ] Hypothetical rates are omitted.
- [ ] Communication estimates are labeled.
- [ ] No hardware conclusion is made.

**Residual risk:** accepted.

---

## 8.4 No poisoning, evasion, backdoor, or Byzantine analysis

**Defence**

These are separate security questions. Calibration poisoning belongs to DATP-CP.

**Readiness**

- [ ] No adversarial-robustness claim appears.
- [ ] Security attacks are explicitly out of scope.
- [ ] Rejected security experiments are not described as missing work.

---

## 8.5 Temporal experiment does not solve drift

**Defence**

Describe the temporal work as one-shot recalibration under one verified chronological population.

**Readiness**

- [ ] Timestamps are verified.
- [ ] Matched static reference exists.
- [ ] Recovery ratio is computed only when defined.
- [ ] No streaming method is added after failure.
- [ ] No general drift-handling claim appears.

---

# 9. Research-integrity risks

## 9.1 Too many experiments create HARKing

**Defence**

Use:

- frozen configurations;
- explicit evidence roles;
- immutable manifests;
- full grid reporting;
- locked fallback interpretations;
- explicit rejected analyses.

**Readiness**

- [ ] Every result has an evidence role.
- [ ] Canonical and exploratory settings are separated.
- [ ] All pre-specified conditions are reported.
- [ ] Null and opposite results remain visible.
- [ ] No hidden main claim exists in the supplement.
- [ ] Deviations are recorded in [07](./07_AUDIT_AND_DECISION_LOG.md).

---

## 9.2 Code inheritance undermines reproducibility

**Defence**

DATP-Core is written from scratch; the prior project is behavioral only.

**Readiness**

- [ ] Reference-code use is documented.
- [ ] No old layout is required.
- [ ] No compatibility shims exist.
- [ ] Anchor behavior is independently reproduced.
- [ ] Every result has new artifact lineage.

---

## 9.3 Scratch code does not reproduce the original result

**Defence**

Require:

- five-seed anchor reproduction;
- split and checkpoint audit;
- metric comparison;
- invariance tests;
- discrepancy handling.

**Readiness**

- [ ] Anchor reproduction report exists.
- [ ] Material differences are explained.
- [ ] B1–B4 semantics are tested.
- [ ] Historical and journal checkpoints are separated.
- [ ] Reproduction does not use manually copied outputs.

---

## 9.4 Methods, results, and claims do not match

**Defence**

Every manuscript value must trace through:

```text
configuration
→ artifacts
→ metrics
→ statistics
→ figure/table
→ claim decision
```

**Readiness**

- [ ] Methods match executed configurations.
- [ ] Figures and tables use frozen manifests.
- [ ] Claim wording follows [02](./02_CLAIMS_AND_DECISION_RULES.md).
- [ ] Limitations match unavailable outcomes.
- [ ] Planned work is not described as completed.

**Blocking level:** submission-blocking.

---

# 10. Scope-balance risks

## 10.1 The extension is too broad

**Defence**

Maintain hard limits:

- one external dataset;
- one benign summary-statistics comparator;
- FedProx;
- one model-personalization method;
- bounded threshold variants;
- one temporal family;
- the locked mechanism analyses.

**Readiness**

- [ ] No second external dataset is added.
- [ ] No broad personalized-FL benchmark is added.
- [ ] No broad aggregation benchmark is added.
- [ ] No privacy, hardware, poisoning, or streaming expansion is added.
- [ ] Main narrative remains threshold-scope focused.

---

## 10.2 The extension is too narrow

**Defence**

Demonstrate depth through:

- ten-seed evidence;
- exact statistical protocol;
- external validation;
- comparator and stress tests;
- mechanism analyses;
- calibration robustness;
- temporal boundary;
- negative-result transparency.

**Readiness**

- [ ] Every module connects to the central question.
- [ ] Main paper exceeds a conference re-run.
- [ ] External, comparator, mechanism, and boundary evidence exist.
- [ ] The paper remains one coherent study.

**Residual risk:** editorial judgment.

---

# 11. Scientific readiness checklist

## Core identity

- [ ] B1–B4 use one fixed model and shared scores.
- [ ] Threshold scope is the sole core variable.
- [ ] Calibration is benign-only.
- [ ] `CV(FPR)` is the sole confirmatory metric.
- [ ] AUROC is a control.
- [ ] Stress tests remain outside the causal ladder.
- [ ] FPR equity is defined precisely.
- [ ] No privacy, deployment, security, or drift overclaim appears.

## Datasets and regimes

- [ ] N-BaIoT nine-device population is verified.
- [ ] N-BaIoT family taxonomy is verified.
- [ ] CICIoT2023 file-defined scope is verified.
- [ ] CICIoT2023 physical-device regime remains suppressed.
- [ ] Actual CICIoT2023 feature count is reverified.
- [ ] Edge-IIoTset ten-group mapping is verified.
- [ ] Edge-IIoTset attack limitations are enforced.
- [ ] Temporal nine-group chronology is verified.
- [ ] Every regime has an immutable readiness and split manifest.

## Confirmatory evidence

- [ ] Five-seed anchor reproduced.
- [ ] Material discrepancies resolved.
- [ ] Ten seed models and scores exist.
- [ ] Primary round is selected without test leakage.
- [ ] Ten paired B1/B2 records exist.
- [ ] BCa interval is reproducible.
- [ ] Absolute dispersion is reported.
- [ ] P10 Macro-F1 trade-off is reported.

## Comparators

- [ ] Shared-threshold controls are complete.
- [ ] `B-FedStatsBenign` is frozen and validated.
- [ ] Full pooled variance is used.
- [ ] FedProx has a terminal result.
- [ ] Ditto or honestly named alternative has a terminal result.
- [ ] Absorption follows the locked rule.

## Mechanisms and boundaries

- [ ] B3/B4 comparison is complete.
- [ ] B4 canonical `K` remains fixed.
- [ ] Cluster memberships and stability are reported.
- [ ] Fingerprint ablation is complete.
- [ ] All-client score distributions exist.
- [ ] Calibration-size and shrinkage grids are complete.
- [ ] B2-conf coverage is complete.
- [ ] Temporal static, frozen, and recalibrated results exist.

---

# 12. Manuscript readiness checklist

## Results

- [ ] Ten-seed evidence appears first.
- [ ] Confirmatory and non-confirmatory evidence are separated.
- [ ] Material negatives remain in the main paper.
- [ ] External evidence is not promoted.
- [ ] Comparator dominance or absorption is reported honestly.
- [ ] Exploratory work is labeled.

## Methods

- [ ] Methods match frozen configurations.
- [ ] Client identity is explained per regime.
- [ ] Eligibility and unavailable metrics are explicit.
- [ ] Checkpoint selection is reproducible.
- [ ] BCa implementation is reproducible.
- [ ] Undefined metrics are explained.
- [ ] Policies and stress-test models are separated.

## Discussion and limitations

- [ ] Success, boundary, and failure are separated.
- [ ] Laridi overlap is addressed.
- [ ] Model-personalization absorption is addressed.
- [ ] FPR equity and detection cost are balanced.
- [ ] No association is described as causal.
- [ ] Nine-client and one-dataset limitations are explicit.
- [ ] Privacy, deployment, temporal, and attack-metric limits are explicit.

## Related work

- [ ] Laridi is compared precisely.
- [ ] Threshold clustering is distinguished from model clustering.
- [ ] FedProx and Ditto are positioned as stress tests.
- [ ] Federated conformal prior art is acknowledged.
- [ ] No unsupported “first” claim appears.
- [ ] Primary sources are verified.

## Abstract and conclusion

- [ ] Written after the frozen results.
- [ ] Use only surviving claims.
- [ ] Include the principal negative trade-off.
- [ ] Do not imply universal generalization.
- [ ] Do not claim privacy, deployment, or drift handling.
- [ ] External evidence is stated at the correct level.

## Supplement and cover letter

- [ ] Supplement contains all seeds and clients.
- [ ] Full checkpoint trajectories are included.
- [ ] Exploratory B4 settings are included.
- [ ] No material negative is hidden there.
- [ ] Conference paper is cited and extension disclosed.
- [ ] New material is enumerated.
- [ ] No simultaneous duplicate submission exists.

---

# 13. Submission blockers

## Scientific blockers

- unresolved anchor reproduction discrepancy;
- missing ten-seed paired result;
- invalid checkpoint selection;
- inconsistent B1–B4 scores;
- attack information entering threshold calibration;
- missing absolute-dispersion safeguards;
- invalid Edge-IIoTset mapping;
- unsupported external attack claims;
- post-hoc policy tuning;
- hidden material negative.

## Novelty blockers

- Laridi overlap not addressed;
- matched comparator missing;
- journal additions not distinguished from conference work;
- overlap audit incomplete;
- standard methods claimed as algorithmically novel.

## Reproducibility blockers

- hidden scientific defaults;
- incomplete artifact lineage;
- manually copied manuscript values;
- unresolved metric inconsistency;
- missing seed or checkpoint provenance;
- overwritten frozen results;
- planned methods described as executed.

## Editorial blockers

- abstract based on planned rather than executed results;
- central claim obscured by too many experiments;
- negative evidence hidden in the supplement;
- limitations incomplete;
- conference-extension disclosure missing;
- current venue policies not rechecked.

---

# 14. Claim-specific blockers

## External validation

Blocked by:

- invalid client mapping;
- failed eligibility;
- stale dataset audit;
- missing paired external analysis;
- unsupported attack-metric interpretation.

## Model personalization

Blocked by:

- non-genuine Ditto naming;
- missing comparison corner;
- model/score provenance mismatch;
- post-hoc selection;
- incorrect absorption calculation.

## Temporal result

Blocked by:

- invalid timestamps;
- future leakage;
- missing static reference;
- missing frozen or recalibrated result;
- recovery ratio computed when undefined.

## Alert burden

Blocked by:

- missing measured or cited traffic rate;
- unclear unit;
- hypothetical rate described as measurement.

## CICIoT2023 quantitative result

Blocked until:

- actual feature count is reverified;
- file-defined clients are confirmed;
- physical-device wording is removed.

---

# 15. Accepted non-blocking outcomes

The following may narrow claims but do not block a scientifically honest paper:

- wider ten-seed interval;
- failed confirmatory endpoint;
- B4 instability;
- weak heterogeneity association;
- small-calibration collapse;
- B2-conf coverage miss;
- `B-FedStatsBenign` parity or dominance;
- FedProx absorption;
- model-personalization absorption;
- Edge-IIoTset null or reversal;
- failed temporal recovery;
- unavailable external attack metrics.

These outcomes must not be hidden.

---

# 16. Final reviewer-readiness audits

Before submission, perform independent audits covering:

## Scientific identity

Verify:

- fixed-detector B1–B4 semantics;
- benign-only calibration;
- FPR-equity framing;
- sole confirmatory endpoint;
- stress-test separation.

## Claims

Check every claim in:

- title;
- abstract;
- introduction;
- results;
- discussion;
- conclusion;
- cover letter;

against its result, evidence role, decision rule, and limitation.

## Reviewer attacks

Run independent critical reviews focused on:

- novelty and Laridi overlap;
- calibration tautology;
- statistical validity;
- model-personalization absorption;
- dataset/client validity;
- reproducibility;
- privacy and security overclaim;
- conference originality;
- negative-result transparency.

## Artifacts

Verify:

- every manuscript number reproduces;
- figures use the intended records;
- all seeds and clients are present;
- no stale artifact is referenced;
- configurations and checksums match.

## Cold read

A new reader must understand:

- the central question;
- what is fixed and what changes;
- the sole confirmatory endpoint;
- why the contribution is not a new detector;
- the strongest prior-work overlap;
- the strongest negative result;
- what generalizes;
- what remains out of scope.

---

# 17. Final readiness verdict

Use exactly one verdict.

## NOT READY

One or more scientific, novelty, reproducibility, or editorial blockers remain.

## READY FOR INTERNAL REVIEW

Mandatory evidence exists, but manuscript integration or independent audits remain incomplete.

## READY FOR SUPERVISOR REVIEW

Scientific blockers are closed, claim wording is frozen, principal figures and tables exist, and internal reviewer attacks have been addressed.

## READY FOR SUBMISSION

Use only when:

- all submission blockers are closed;
- target-journal policies were rechecked;
- conference-extension disclosure is complete;
- every manuscript value reproduces from frozen artifacts;
- independent reviewer audits pass;
- no material negative is hidden;
- the final audit is recorded in [07](./07_AUDIT_AND_DECISION_LOG.md).

A partial state must never be described as submission-ready.
