# 04 — Evaluation and Reporting Protocol

## Purpose

This file defines how DATP-Core results are calculated, aggregated, compared, validated, and reported.

It owns:

- metric definitions and undefined-value behavior;
- eligible-client aggregation;
- paired-seed statistics;
- BCa confidence intervals;
- checkpoint evaluation and selection constraints;
- temporal-recalibration quantities;
- result provenance;
- required tables, figures, and diagnostics;
- result freeze and anti-selection rules.

It does not repeat scientific scope, claim wording, experiment procedures, or software architecture.

Related files:

- [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md)
- [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md)
- [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md)
- [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md)
- [06 — Reviewer Risks and Readiness](./06_REVIEWER_RISKS_AND_READINESS.md)

---

# 1. Evaluation contract

## 1.1 Fixed-score comparison

Within B1–B4, every policy uses the same:

- selected model state;
- preprocessing state;
- client identities;
- calibration and test splits;
- score artifacts;
- eligibility decisions;
- metric implementation.

Only thresholds may change.

## 1.2 Independent unit

The training seed is the independent replication unit.

Clients, rows, checkpoints, attack categories, calibration subsamples, cluster initializations, and temporal windows are not independent replications.

Nested replicates are summarized within seed before across-seed inference.

## 1.3 Per-client-first reporting

Metrics are calculated per client before cross-client aggregation whenever valid client identity exists.

Pooled-row metrics may be reported as controls but cannot replace client-level operating-point metrics.

---

# 2. Prediction and confusion counts

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

# 3. Metric populations

## 3.1 Calibration eligibility

A client is primary-analysis eligible when:

```text
benign_calibration_count >= 100
```

Eligibility is determined before test evaluation and remains identical across policies in the same comparison.

## 3.2 FPR-evaluable population

A client additionally requires a non-empty benign test denominator.

## 3.3 Attack-evaluable population

Attack-sensitive metrics additionally require:

- valid per-client attack assignment;
- at least one held-out attack row;
- both semantic classes where required.

A client may be FPR-evaluable but unavailable for TPR, balanced accuracy, Macro-F1, or AUROC.

This distinction is mandatory for Edge-IIoTset.

## 3.4 Coverage

\[
coverage
=
\frac{K_{\mathrm{eligible}}}{K_{\mathrm{candidate}}}
\]

Report candidate, eligible, attack-evaluable, fallback, and excluded client counts, with an exclusion reason per client.

Ineligible fallback clients do not enter the primary `CV(FPR)` calculation.

---

# 4. Per-client metrics

## 4.1 False-positive rate

\[
FPR_k
=
\frac{FP_k}{FP_k + TN_k}
\]

Unavailable when the benign denominator is zero.

## 4.2 True-positive rate

\[
TPR_k
=
\frac{TP_k}{TP_k + FN_k}
\]

Unavailable when the attack denominator is zero or client-level attack assignment is invalid.

## 4.3 Balanced accuracy

\[
BA_k
=
\frac{TPR_k + (1-FPR_k)}{2}
\]

Unavailable unless both FPR and TPR are available.

## 4.4 Per-client Macro-F1

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

Do not silently convert undefined class metrics to zero through library defaults.

## 4.5 AUROC

AUROC uses continuous anomaly scores and requires both classes.

Within a fixed-score B1–B4 comparison, AUROC must be identical up to numerical serialization tolerance. Any policy-dependent difference indicates mismatched artifacts or unintended model variation.

AUROC is a model-quality control, not a threshold-policy verdict.

---

# 5. Cross-client operating-point metrics

Let \(K_e\) be the eligible FPR-evaluable client count.

## 5.1 Mean FPR

\[
\mu_{FPR}
=
\frac{1}{K_e}
\sum_{k=1}^{K_e} FPR_k
\]

The primary equity calculation is unweighted by client row count.

## 5.2 Population standard deviation

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

## 5.3 Coefficient of variation

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

A positive `cv_instability_threshold` must be explicitly configured before analysis. When the mean is positive but below that threshold, retain the numerical CV with a near-zero-denominator warning.

Such cells are interpreted only alongside absolute dispersion.

## 5.4 Absolute dispersion

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

The quantile interpolation method must be explicit and must match the anchor convention. No implicit library default is permitted.

## 5.5 TPR and lower-tail metrics

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

# 6. Optional equity metrics

Optional metrics accompany `CV(FPR)` and never replace it.

## 6.1 Jain index

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

## 6.2 Gini coefficient

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

## 6.3 Cluster dispersion

For B4, report:

- cluster size;
- within-cluster threshold spread;
- within-cluster FPR spread;
- across-cluster threshold spread;
- across-cluster mean-FPR spread;
- singleton and empty-cluster status.

Do not conflate these quantities.

---

# 7. Aggregate model-quality controls

## 7.1 Mean client Macro-F1

\[
MeanClientMacroF1
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} MacroF1_k
\]

where \(K_a\) is the attack-evaluable client count.

## 7.2 Pooled Macro-F1

Pooled Macro-F1 may be reported from pooled confusion counts but must be labeled separately.

It cannot replace:

- mean client Macro-F1;
- P10 Macro-F1;
- worst-client balanced accuracy.

## 7.3 Mean client balanced accuracy

\[
MeanClientBA
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} BA_k
\]

Always report the worst-client value alongside it.

---

# 8. Threshold-estimation metrics

## 8.1 Centralized oracle

When defined by the experiment, the exact pooled benign quantile is the centralized threshold reference.

The quantile probability and interpolation method must match the distributed estimators.

## 8.2 Threshold error

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

## 8.3 Target attainment

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

## 8.4 Threshold variance and sample efficiency

For calibration-size studies, calculate threshold variation across declared subsampling replicates within client and seed.

The complete calibration-size curve is reported using:

- threshold variance;
- attainment error;
- `CV(FPR)`;
- worst-client FPR;
- P10 Macro-F1 where available.

Subsampling replicates do not increase the seed count.

---

# 9. `B-FedStatsBenign` diagnostics

For eligible client \(k\), the comparator uses benign-only:

- count \(n_k\);
- mean \(\mu_k\);
- variance \(\sigma_k^2\);
- permitted benign exceedance counts.

## 9.1 Global mean

\[
\mu_{global}
=
\frac{
\sum_k n_k\mu_k
}{
\sum_k n_k
}
\]

## 9.2 Full pooled variance

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

## 9.3 Between ratio

\[
between\_ratio
=
\frac{between}{within+between}
\]

Undefined when the denominator is zero.

Report `within`, `between`, pooled variance, and `between_ratio`.

---

# 10. Operational metrics

## 10.1 Alert burden

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

## 10.2 Communication and storage

Distinguish:

- analytical payload estimate;
- measured serialized artifact size;
- actual network traffic.

Estimated payload must not be presented as measured communication.

---

# 11. Confirmatory statistical analysis

## 11.1 Paired contrast

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

## 11.2 BCa confidence interval

The confirmatory interval is a two-sided 95% BCa bootstrap interval over the ten paired seed-level deltas.

The implementation must:

- resample paired seed deltas with replacement;
- use the arithmetic mean as the statistic;
- compute bias correction from the bootstrap distribution;
- compute acceleration through leave-one-seed-out jackknife estimates;
- use a fixed recorded analysis seed;
- use at least 10,000 bootstrap resamples;
- use 50,000 resamples for the frozen publication result unless a larger value is explicitly locked;
- store the bootstrap configuration and interval.

No implicit library default is permitted.

## 11.3 Degenerate BCa

If BCa is undefined or unstable because of identical deltas, invalid acceleration, a degenerate bootstrap distribution, or fewer than ten valid pairs:

- record a statistical-procedure failure;
- report the paired values and point estimate;
- allow percentile or basic intervals only as diagnostics;
- do not silently substitute another interval for the confirmatory rule.

Claim consequences belong to [02](./02_CLAIMS_AND_DECISION_RULES.md#3-sole-confirmatory-endpoint).

## 11.4 Sign consistency

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

# 12. Secondary statistical evidence

## 12.1 Wilcoxon signed-rank

Use paired seed-level values with:

- two-sided alternative;
- explicit zero-difference handling;
- exact computation when data and implementation permit;
- recorded approximation or permutation method otherwise.

The p-value does not determine the confirmatory verdict.

## 12.2 Matched-pairs rank-biserial correlation

Use matched-pairs rank-biserial correlation as the paired nonparametric effect size.

Do not use unpaired Cliff’s delta for the seed-paired comparison.

Report method, sign, magnitude, and non-zero pair count.

## 12.3 Secondary confidence intervals

Secondary BCa intervals may be reported for pre-specified seed-level contrasts, but remain secondary.

## 12.4 Multiplicity

The single confirmatory endpoint receives no multiplicity correction.

When secondary p-values are emphasized:

- define test families before analysis;
- report family size;
- apply Holm correction within each family;
- retain raw values only as clearly labeled diagnostics.

Exploratory analyses may remain descriptive.

## 12.5 Nested replicates

For calibration subsamples, cluster restarts, or similar nested repetitions:

1. calculate replicate-level values;
2. summarize them within seed;
3. produce one seed-level estimate per condition;
4. perform across-seed inference on those seed-level estimates.

## 12.6 Association analyses

For heterogeneity–benefit analyses, report:

- Spearman correlation;
- declared regression;
- coefficient and uncertainty;
- `R²`;
- influence diagnostics;
- all observations.

Use associative, not causal, language.

## 12.7 Cluster stability

Adjusted Rand index is descriptive and must be accompanied by memberships, cluster sizes, empty clusters, and singleton clusters.

---

# 13. Checkpoint protocol

## 13.1 Anchor checkpoint

The conference anchor preserves its historical endpoint and checkpoint semantics.

It is not retrofitted with journal checkpoint selection merely to improve reproduction.

Historical anchor training uses one local epoch, Adam (`lr = 0.001`), batch size 256, and client-local standardization fit on benign training rows. Beginning at round 40, compute `abs(loss[r-9] - loss[r]) / abs(loss[r-9])` over the trailing ten FedAvg-weighted benign validation losses; a zero start loss has relative change zero. Select the first round below `0.005`, otherwise the 150-round cap, and save only that final checkpoint. Its five paired seed deltas use the historical 95% percentile bootstrap with 10,000 resamples and seed 42.

## 13.2 Journal checkpoint grid

Train journal runs to 200 rounds and save:

```text
25, 50, 75, 100, 125, 150, 200
```

Convergence is logged but does not stop training.

## 13.3 Primary journal round

Regime A selects one primary **round number** using a non-test rule frozen before journal outcomes are inspected.

The selector must be explicitly configured. No default selector is permitted.

The selected round number is reused across main regimes and policies where the checkpoint exists. Model weights remain regime- and seed-specific.

## 13.4 Forbidden selectors

The round cannot be chosen using:

- test AUROC;
- test FPR or `CV(FPR)`;
- Macro-F1 or balanced accuracy;
- attack labels;
- the B1-versus-B2 effect;
- external or stress-test results;
- policy-specific best performance.

## 13.5 Checkpoint reporting

All saved rounds remain available as supplementary stability evidence.

Report weak trajectories and ordering reversals rather than hiding them.

---

# 14. Temporal recalibration quantities

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

`recovery_ratio` is computed only when `drift_excess` satisfies a positive-materiality threshold explicitly frozen before analysis.

Otherwise:

```text
recovery_ratio = undefined
```

Temporal BCa analysis resamples paired seed records, not rows or windows.

Outcome interpretation belongs to [02](./02_CLAIMS_AND_DECISION_RULES.md#13-temporal-outcomes).

---

# 15. Undefined and unavailable metrics

Every metric record carries a status.

Permitted statuses include:

```text
available
undefined_zero_denominator
undefined_near_zero_denominator
unavailable_missing_benign_class
unavailable_missing_attack_class
unavailable_invalid_attack_assignment
unavailable_ineligible_client
unavailable_unsupported_regime
failed_invalid_artifact
failed_statistical_procedure
```

Do not use zero, an empty string, an omitted row, or unqualified `NaN` as a substitute for a reason.

A near-zero CV may retain its numerical diagnostic value together with its warning status.

---

# 16. Precision and deterministic ordering

Calculations use full available precision. Rounding occurs only for presentation.

Recommended presentation:

- rates and aggregate metrics: three decimals;
- confidence intervals and effect sizes: three decimals;
- p-values: three significant digits, with `< 0.001` when appropriate;
- counts: integers;
- thresholds: enough digits to reproduce decisions.

Never round before computing contrasts or intervals.

Use stable ordering for:

- regime;
- seed;
- checkpoint;
- client;
- policy;
- quantile;
- calibration size;
- shrinkage value;
- cluster count.

---

# 17. Provenance

Every published value must trace through:

```text
configuration
→ dataset artifact
→ split manifest
→ preprocessing state
→ training run
→ checkpoint
→ score artifact
→ threshold artifact
→ per-client metrics
→ seed-level aggregate
→ statistical result
→ table or figure
```

Minimum provenance fields:

- experiment name and evidence role;
- dataset and regime;
- client-definition identifier;
- seed and checkpoint;
- model and score artifact identifiers;
- policy or comparator;
- resolved parameters;
- eligibility manifest;
- metric-definition version;
- statistical-procedure version;
- configuration fingerprint;
- source revision;
- generation timestamp.

Every table and figure identifies its source result manifest.

Manually copied values without provenance are prohibited.

---

# 18. Main-paper reporting

The main paper must include:

## 18.1 Confirmatory evidence

- all ten seed-level B1 and B2 values;
- paired differences;
- BCa interval;
- sign consistency;
- IQR, range, and worst-client FPR;
- per-client FPR;
- P10 Macro-F1 trade-off;
- AUROC invariance control.

## 18.2 Mechanism evidence

- B1/B3/B4/B2 comparison;
- B4 recovery;
- cluster stability and memberships;
- per-client score distributions;
- threshold movement versus FPR/TPR;
- heterogeneity association.

## 18.3 Boundary and stress-test evidence

- calibration-size and shrinkage results;
- B2-conf coverage;
- CICIoT2023 boundary;
- Edge-IIoTset benign-equity validation;
- `B-FedStatsBenign`;
- FedProx;
- Ditto;
- temporal recalibration.

Material negative results remain in the main paper.

---

# 19. Required figures

At minimum provide:

- paired-seed confirmatory plot;
- all-client FPR comparison;
- quantile-sensitivity plot;
- heterogeneity-severity plot;
- cluster membership/stability heatmap or contingency display;
- benign and attack score CDFs;
- threshold-shift versus FPR/TPR plots;
- calibration-size curves;
- shrinkage curve;
- B2-conf coverage plot;
- Edge-IIoTset client plot;
- FedProx and Ditto comparison;
- static/frozen/recalibrated temporal plot.

Figure rules:

- show all pre-specified conditions;
- show all valid clients where population is small;
- show uncertainty where claimed;
- do not apply unsupported smoothing;
- do not truncate axes to exaggerate effects;
- do not use a Sankey diagram for B4;
- use vector output where supported;
- attach provenance.

---

# 20. Required result tables

The result package must support:

- confirmatory metric summary;
- paired statistical summary;
- B1/B2/B3/B4 threshold-policy comparison;
- per-client Regime A metrics;
- calibration-size and shrinkage results;
- comparator and threshold-estimation results;
- Edge-IIoTset external validation;
- FedProx and Ditto stress tests;
- temporal recalibration;
- unavailable and infeasible outcomes.

Tables distinguish:

- mean-client from pooled metrics;
- estimated from measured communication;
- unavailable from undefined;
- core ladder from stress-test models.

---

# 21. Supplementary reporting

The supplement contains:

- all checkpoint trajectories;
- all client-level and seed-level values;
- alternative B4 cluster counts;
- full cluster-feature ablation;
- optional Jain and Gini metrics;
- secondary confidence intervals and p-values;
- fixed-coefficient summary-statistics sensitivity;
- communication and storage detail;
- full provenance references;
- all undefined and unavailable records.

Supplementary placement does not allow stronger claim wording.

---

# 22. Result freeze

A result family is frozen only when:

- all required seeds are present or formally failed;
- eligibility is final;
- all pre-specified conditions are represented;
- metric statuses are resolved;
- statistical configuration is recorded;
- provenance is complete;
- validation checks pass;
- tables and figures reproduce from the same records.

After freeze:

- no seed, client, checkpoint, quantile, calibration size, cluster count, or comparator setting is removed or retuned;
- corrections create a new result version;
- the previous result and reason for correction remain auditable.

---

# 23. Favorable-result selection is prohibited

Do not:

- choose checkpoints from test outcomes;
- select different checkpoints for B1 and B2;
- choose B4 `K` after seeing results;
- report only favorable quantiles or calibration sizes;
- select shrinkage from the test set;
- retune `B-FedStatsBenign` after comparison;
- add a FedProx coefficient after failure;
- change the personalization method after outcome inspection;
- remove unfavorable seeds or clients;
- convert undefined metrics to zero;
- hide external nulls, comparator dominance, or temporal failure;
- move a material negative exclusively to the supplement.

Claim-level consequences are defined in [02](./02_CLAIMS_AND_DECISION_RULES.md#15-anti-harking-and-non-suppression).

---

# 24. Evaluation audit checklist

## Metrics

- [ ] Prediction comparison is fixed.
- [ ] Confusion counts use held-out test rows only.
- [ ] `CV(FPR)` uses `ddof=0`.
- [ ] No denominator stabilizer is used.
- [ ] Zero-mean CV is undefined.
- [ ] Near-zero CV uses a configured warning threshold.
- [ ] IQR and range accompany CV.
- [ ] Per-client and pooled metrics are distinct.
- [ ] Edge-IIoTset attack-sensitive metrics are unavailable where required.

## Statistics

- [ ] Ten paired seeds enter the confirmatory analysis.
- [ ] BCa resamples paired seed-level deltas.
- [ ] Bootstrap count and analysis seed are recorded.
- [ ] Degenerate BCa does not silently fall back.
- [ ] Wilcoxon is secondary.
- [ ] Matched-pairs rank-biserial correlation is used.
- [ ] Nested replicates are summarized within seed.
- [ ] Multiplicity treatment is pre-specified.

## Checkpoints

- [ ] Anchor and journal checkpoint semantics are separate.
- [ ] All journal checkpoint rounds exist.
- [ ] One Regime A-selected round is reused.
- [ ] The selector was frozen before outcome inspection.
- [ ] No test or policy-effect metric selected the round.
- [ ] Full trajectories remain available.

## Reporting

- [ ] All valid seeds and clients are retained.
- [ ] All pre-specified conditions are shown.
- [ ] Undefined and unavailable metrics have reasons.
- [ ] Material negatives remain in the main paper.
- [ ] Figures and tables trace to manifests.
- [ ] Unrounded values drive calculations.
- [ ] No unsupported causal, privacy, drift, or deployment claim appears.

Failure of a locked item blocks result freeze until corrected or formally recorded as infeasible.
