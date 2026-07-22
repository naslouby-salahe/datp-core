# 02 — Claims and Decision Rules

## Purpose

This file defines what DATP-Core may claim and how results change those claims. It owns the confirmatory endpoint, claim hierarchy, research questions, decision thresholds, fallback interpretations, and anti-HARKing rules.

It does not repeat:

- scientific identity or policy definitions → [01](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md);
- experiment procedures → [03](./03_EXPERIMENT_CATALOGUE.md);
- metric formulas and statistical implementation → [04](./04_EVALUATION_AND_REPORTING_PROTOCOL.md);
- reviewer defences → [06](./06_REVIEWER_RISKS_AND_READINESS.md);
- audit history → [07](./07_AUDIT_AND_DECISION_LOG.md).

---

# 1. Claim roles

Every result is assigned one role before interpretation:

- **Confirmatory:** the sole Regime A B1-versus-B2 endpoint.
- **Supportive:** robustness checks that strengthen or narrow the confirmatory interpretation.
- **External validation:** independent dataset evidence that never becomes confirmatory.
- **Stress test:** evidence after changing the training algorithm or personalizing the model.
- **Mechanism:** evidence explaining when, why, or for which clients the effect occurs.
- **Threshold variant:** alternative estimators evaluated on the fixed detector.
- **Boundary:** settings where the effect weakens, reverses, or is not identifiable.
- **Exploratory:** hypothesis-forming evidence that cannot be promoted post hoc.
- **Suppression evidence:** a valid reason why an intended analysis cannot be executed.
- **Future work:** named but unexecuted research.

A failed confirmatory endpoint cannot be rescued by any lower-level result.

---

# 2. Main journal claim

> **DATP’s threshold-scope effect remains observable under a stronger journal protocol that adds external validation, a matched federated-threshold comparator, training-side stress tests, calibration-robustness analyses, and mechanism evidence while preserving the fixed-detector, benign-calibration identity.**

This statement is valid only to the extent supported by the confirmatory endpoint and the separately classified evidence below.

---

# 3. Sole confirmatory endpoint

## 3.1 Locked endpoint

- **Regime:** Regime A.
- **Dataset:** N-BaIoT.
- **Population:** nine physical-device clients.
- **Comparison:** B1 shared threshold versus B2 per-client threshold.
- **Primary metric:** `CV(FPR)` over the same eligible clients.
- **Replication:** ten paired training seeds.
- **Paired contrast:**

\[
\Delta_s = CV(FPR)_{B1,s} - CV(FPR)_{B2,s}
\]

- **Inference:** 95% BCa bootstrap confidence interval over the ten seed-level contrasts.
- **Required direction:** positive.

## 3.2 Decision

**Supported:** the BCa interval excludes zero and both bounds are positive.

> B2 reduces cross-client FPR dispersion relative to B1 under the natural N-BaIoT physical-device regime.

**Directional but inconclusive:** the point estimate is positive but the interval includes zero.

> The direction favors B2, but the confirmatory endpoint is not met.

**Null:** the estimate is approximately zero and the interval includes zero.

> No B1-versus-B2 reduction is established under the locked protocol.

**Opposite:** the interval excludes zero in the negative direction.

> B2 increases cross-client FPR dispersion relative to B1 under Regime A.

The valid ten-seed result is always the main result.

## 3.3 Required companion reporting

Always report:

- all ten paired contrasts and sign consistency;
- per-client FPR;
- IQR, range, and worst-client FPR;
- TPR, Macro-F1, balanced accuracy, and P10 Macro-F1;
- AUROC as a detector-quality control.

None replaces `CV(FPR)` as the confirmatory endpoint.

---

# 4. Historical anchor

Conference reference values:

```text
B1 CV(FPR) = 1.017
B2 CV(FPR) = 0.299
paired reduction = 0.718
five-seed bootstrap CI = [0.647, 0.769]
relative reduction = 70.6%
all five seed deltas positive
B4 CV(FPR) = 0.645
B4 recovery ≈ 52%
B3 CV(FPR) = 0.964
P10 Macro-F1: 0.344 → 0.300 under B2
```

These are historical until reproduced with DATP-Core provenance. A weaker ten-seed result is never replaced by the conference estimate.

The historical execution contract (training hyperparameters, convergence rule, checkpoint selection) is canonical in [`SCIENTIFIC_SOURCE_OF_TRUTH.md` §7](./SCIENTIFIC_SOURCE_OF_TRUTH.md#7-model-and-training-protocol). The five seed-level B1-minus-B2 deltas use a 95% percentile bootstrap with 10,000 resamples and seed 42 (`historical_five_seed_percentile_bootstrap`, [SCIENTIFIC_SOURCE_OF_TRUTH.md §12](./SCIENTIFIC_SOURCE_OF_TRUTH.md#12-statistical-analysis)).

---

# 5. Research questions

**RQ1 — Confirmatory effect.** Does B2 reduce cross-client FPR dispersion relative to B1 on a fixed FedAvg detector, and what detection trade-off accompanies the change?

**RQ2 — Intermediate sharing.** Do B3 and B4 recover part of B2’s benefit, and are their groupings stable and interpretable?

**RQ3 — Calibration scarcity.** How do local thresholds behave as benign calibration windows shrink, and can shrinkage improve stability?

**RQ4 — Distributed estimation.** Do pooled, weighted, or benign summary-statistics thresholds explain, challenge, or dominate the DATP effect?

**RQ5 — Training-side absorption.** Does the effect remain under FedProx or genuine model personalization?

**RQ6 — Generalization and limits.** Does the effect appear on Edge-IIoTset, vary with controlled heterogeneity, and disappear under near-homogeneous or temporally unstable conditions?

---

# 6. Supportive claims

## 6.1 Shared-threshold construction

Claim allowed when B2 remains less dispersed than all pre-specified shared constructions:

> The effect is not specific to B1’s arithmetic-mean construction.

If a shared construction matches or exceeds B2:

> The effect is construction-specific rather than a general shared-versus-local distinction.

## 6.2 Absolute dispersion

Claim allowed when B2 improves `CV(FPR)`, IQR, and range:

> The result is present in both relative and absolute FPR dispersion.

If only CV improves:

> The result is metric-sensitive and may depend on the mean-FPR denominator.

## 6.3 Heterogeneity severity

When the B1-versus-B2 gap is larger under strong Regime C heterogeneity and attenuates toward IID:

> Threshold-personalization benefit is concentrated in the high-heterogeneity region.

Strict monotonicity is not required. If irregular:

> The effect varies with partition severity, but no monotonic relationship is established.

## 6.4 Quantile sensitivity

When the B2 direction remains consistent over the locked grid:

> The result is not unique to `q = 0.95`.

Any inversion is reported as a quantile-dependent boundary.

---

# 7. External validation

Edge-IIoTset supports only benign false-positive-equity validation under the audited sensor-group population.

**Consistent direction**

> Edge-IIoTset shows a directionally consistent B1-versus-B2 reduction in benign FPR dispersion.

**Attenuated or null**

> The N-BaIoT effect does not transfer at the same magnitude, defining an external boundary.

**Opposite**

> Edge-IIoTset shows an opposite threshold-scope pattern, narrowing DATP’s generalization.

**Infeasible**

> External validation was infeasible under the available artifact; no substitute client partition was invented.

External validation is never a second confirmatory endpoint. Per-client attack-detection equity is not claimed when attack assignment is unavailable.

---

# 8. Comparator claims

## 8.1 `B-FedStatsBenign`

**Improves over B1 but not B2**

> Distributed benign summary statistics improve the shared operating point but do not fully recover local-threshold equity.

**Matches B2**

> A benign summary-statistics shared threshold provides an alternative route to comparable FPR equity.

**Outperforms B2**

> The comparator outperforms local calibration on the primary equity measure, narrowing the DATP claim.

**No benefit**

> The evaluated summary-statistics construction does not improve over B1.

No result is called a faithful Laridi reproduction because anomalous calibration information is excluded.

## 8.2 Federated quantile framing

Permitted claim:

> Treating the policies as distributed quantile estimators makes estimation error, target attainment, and communication directly comparable.

No novel-estimator claim is permitted without separate methodological development.

---

# 9. Training-side stress tests

## 9.1 FedProx

- **Retained:** the threshold-scope difference persists under FedProx.
- **Attenuated:** FedProx reduces but does not remove it.
- **Absorbed:** FedProx removes most of it, narrowing DATP to FedAvg-style settings.
- **Invalid comparison:** the frozen FedProx grid fails; no post-hoc coefficient is added.

FedProx remains outside the core causal ladder.

## 9.2 Model-personalization absorption

Define:

\[
\Delta_{\mathrm{FedAvg}}
=
CV(FPR)_{\mathrm{FedAvg+B1}}
-
CV(FPR)_{\mathrm{FedAvg+B2}}
\]

\[
\Delta_{\mathrm{personalized}}
=
CV(FPR)_{\mathrm{personalized+B1}}
-
CV(FPR)_{\mathrm{personalized+B2}}
\]

**Strong retention**

```text
Delta_personalized >= 0.75 × Delta_FedAvg
```

> Threshold personalization remains strongly useful after model personalization.

**Partial absorption**

```text
0.25 × Delta_FedAvg <= Delta_personalized < 0.75 × Delta_FedAvg
```

> Model personalization partially absorbs the effect, but threshold personalization retains value.

**Large absorption**

```text
Delta_personalized < 0.25 × Delta_FedAvg
```

> Model personalization largely absorbs the effect, narrowing DATP to shared-model settings.

**Alternative path**

When:

```text
abs(CV(FPR)[personalized+B1] - CV(FPR)[FedAvg+B2]) <= 0.05
```

> Model personalization provides an alternative path to a similar operating point.

The method is called Ditto only when the genuine Ditto contract is met.

---

# 10. Mechanism claims

## 10.1 Intermediate sharing

When B3 or canonical B4 recovers part of the B1-to-B2 improvement:

> Intermediate threshold sharing recovers part of the local-threshold benefit.

The recovery amount is stated numerically.

When negligible:

> The evaluated grouping does not provide a useful intermediate operating point.

## 10.2 Cluster stability

**Stable**

> B4 identifies a repeatable taxonomy-free grouping under the evaluated fingerprint.

**Unstable**

> B4 is sensitive to client assignment and remains exploratory.

Memberships and cluster sizes must accompany adjusted Rand results.

## 10.3 Score geometry

Permitted claim:

> Client-specific benign and attack score geometry explains why lower FPR dispersion can coincide with worse detection for low-separability clients.

## 10.4 Heterogeneity association

Permitted wording:

> Greater benign score-distribution heterogeneity is associated with a larger threshold-personalization benefit.

Use *associated with*, not *causes*. Weak association is reported as insufficient explanatory evidence.

## 10.5 Threshold trade-off

Permitted claim:

> The B1-to-B2 threshold shift traces a client-specific false-positive versus true-positive trade-off.

All clients remain included.

---

# 11. Calibration boundaries

## 11.1 Small calibration windows

Valid conclusions are:

- local thresholds remain stable to the tested size;
- shrinkage reduces variance while retaining part of the equity benefit;
- local thresholds become unreliable below an observed range;
- the evaluated shrinkage rules provide no benefit.

The complete calibration-size curve is reported.

## 11.2 Shrinkage

Positive wording:

> Intermediate shrinkage provides an empirical compromise between shared-threshold stability and local-threshold equity.

Negative wording:

> Shrinkage is non-monotone or does not mitigate the trade-off; no favorable value is selected post hoc.

## 11.3 B2-conf

**Supported diagnostic**

> The finite-sample local conformal threshold approximately attains held-out benign coverage while retaining lower FPR dispersion than B1.

**Coverage miss**

> The conformal adaptation misses its intended coverage under the evaluated clients or calibration sizes.

B2-conf cannot support universal conditional coverage, adversarial robustness, or replacement of the confirmatory endpoint.

---

# 12. Applicability boundaries

## 12.1 CICIoT2023 file-defined clients

When B1 and B2 are similar:

> Under the available near-homogeneous file-defined pseudo-client partition, threshold personalization provides little measurable equity benefit.

This is artifact-specific and cannot be generalized to the original physical-device topology.

## 12.2 Rejected physical-device repartition

Required wording:

> A physical-device CICIoT2023 regime was not executed because the processed artifact does not preserve defensible device-identifying metadata.

## 12.3 Detection trade-off

When B2 improves FPR equity but worsens lower-tail detection:

> Local calibration improves false-alarm equity while increasing detection cost for clients with weak score separation.

This negative remains part of the main paper.

---

# 13. Temporal outcomes

Define:

\[
drift\_excess
=
CV(FPR)_{\mathrm{frozen\ future}}
-
CV(FPR)_{\mathrm{static\ reference}}
\]

\[
recovered\_amount
=
CV(FPR)_{\mathrm{frozen\ future}}
-
CV(FPR)_{\mathrm{recalibrated\ future}}
\]

\[
recovery\_ratio
=
\frac{recovered\_amount}{drift\_excess}
\]

`recovery_ratio` is undefined when `drift_excess` is not meaningfully positive.

**Meaningful recovery**

```text
recovery_ratio >= 0.50
```

> One-shot recalibration recovers a meaningful portion of the observed threshold-aging effect.

**Insufficient recovery**

```text
recovery_ratio < 0.50
```

> Thresholds exhibit temporal fragility, and one-shot recalibration is insufficient.

**No meaningful degradation**

> No clear threshold-aging effect is observed within the available chronological window.

No outcome supports a general concept-drift claim.

---

# 14. Seed-extension honesty

The historical five-seed subset must be reproduced before finalizing the ten-seed interpretation.

Historical interval width:

```text
0.769 - 0.647 = 0.122
```

A discrepancy audit is required when the reproduced interval:

- materially shifts toward zero; or
- is more than approximately 20% wider, i.e. wider than about `0.146`.

When unexplained:

- expansion claims are blocked;
- provenance, splits, checkpoints, metrics, and implementation are audited;
- no confirmatory interpretation is finalized.

After the reproduction audit, the ten-seed estimate is authoritative and is never suppressed when less favorable.

---

# 15. Anti-HARKing and non-suppression

Freeze before outcome inspection:

- confirmatory endpoint and seed cohort;
- checkpoint rule;
- quantile grid;
- canonical B4 cluster count;
- comparator construction;
- shrinkage grid;
- FedProx grid;
- personalization rule;
- temporal thresholds;
- client eligibility;
- external client definitions.

Forbidden promotions:

- supportive or external → confirmatory;
- exploratory B4 setting → canonical;
- secondary metric → primary;
- favorable checkpoint, quantile, calibration size, or partition → new main protocol.

The following remain reportable:

- failed confirmatory endpoint;
- wider ten-seed interval;
- unfavorable seeds;
- ordering inversions;
- null B4 recovery;
- unstable clusters;
- weak heterogeneity association;
- calibration collapse;
- conformal coverage miss;
- comparator dominance;
- FedProx or model-personalization absorption;
- external null or reversal;
- failed temporal recovery;
- metadata-based infeasibility.

---

# 16. Standard confirmatory wording

## Endpoint met

> Across ten paired seeds, B2 changed `CV(FPR)` from **[B1]** to **[B2]**, with a paired difference of **[delta]** and a 95% BCa confidence interval of **[lower, upper]**. The interval excludes zero in the positive direction, meeting the confirmatory endpoint.

## Endpoint not met

> The paired difference was **[delta]**, with a 95% BCa confidence interval of **[lower, upper]**. Because the interval includes zero, the confirmatory endpoint is not met; the ten-seed result is reported without substituting the earlier estimate.

## Reversal

> B2 increased `CV(FPR)` relative to B1 by **[magnitude]**, with a 95% BCa confidence interval of **[lower, upper]** in the opposite direction.

## Infeasibility

> The analysis was not executed because **[required metadata, eligibility, or chronology condition]** was not satisfied. No substitute partition or proxy was introduced.

---

# 17. Forbidden claims

DATP-Core must not claim that it:

- solves non-IID federated learning;
- improves global Macro-F1 in general;
- improves every client;
- guarantees human or demographic fairness;
- provides formal privacy;
- is robust to poisoning, backdoors, Byzantine clients, or evasion;
- handles concept drift beyond one-shot recalibration;
- is deployment ready or hardware validated;
- is validated at fleet scale above 100 real clients;
- universally dominates shared thresholding or model personalization;
- establishes Edge-IIoTset cross-client attack-detection equity;
- faithfully reproduces Laridi et al. through `B-FedStatsBenign`;
- introduces the first federated conformal method;
- provides a universally optimal threshold;
- proves that Jensen–Shannon divergence causes DATP benefit;
- makes B4 privacy preserving.

Words such as *first*, *novel*, *state of the art*, *guarantees*, *solves*, *optimal*, and *universally superior* require independent verification.

---

# 18. Future-work boundary

The following are named only as unexecuted future work:

- Dynamic DATP and repeated recalibration;
- Conformal DATP beyond B2-conf;
- differential privacy and secure aggregation;
- threshold-leakage analysis;
- poisoning and robust defenses;
- fleet-scale validation;
- real-device profiling;
- broad personalized-FL or aggregation benchmarking;
- standalone model-versus-threshold personalization with full cost accounting.

They cannot appear as completed contributions or current capabilities.

---

# 19. Claim-freeze checklist

- [ ] Regime A B1 versus B2 remains the sole confirmatory endpoint.
- [ ] `CV(FPR)` remains the sole primary confirmatory metric.
- [ ] Ten paired seeds and the 95% BCa rule remain fixed.
- [ ] Positive direction remains required.
- [ ] Every other result has a declared evidence role.
- [ ] External validation remains non-confirmatory.
- [ ] Absorption and temporal thresholds are frozen.
- [ ] Five-seed discrepancy handling is frozen.
- [ ] Null, opposite, and infeasible outcomes remain reportable.
- [ ] No forbidden claim appears.

Any post-result claim revision must be recorded in `07_AUDIT_AND_DECISION_LOG.md`.
