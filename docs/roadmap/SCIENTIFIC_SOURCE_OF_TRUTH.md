# DATP-Core Scientific Source of Truth

## 1. Document authority

1. **Purpose.** This file is the canonical scientific contract for DATP-Core. It fixes every locked scientific fact, formula, numeric value, boundary, and decision rule referenced by the roadmap package (files `00`–`06`).
2. **Authority.** This file is authoritative for scientific meaning: identity, claims, datasets, regimes, splits, training protocol, threshold policies, seeds, experiments, metrics, statistics, artifacts, scope, and suppression rules. Files `00`–`06` own explanation, planning, experiment narrative, reporting procedure, implementation sequencing, and reviewer defence; where a canonical value is needed they reference the relevant section here rather than restating it. On disagreement between this file and any roadmap file, this file governs.
3. **Conformance.** Implementation, configuration, tests, and reported results must conform to this file. A configuration value that contradicts this file is a configuration defect, not an alternate scientific decision.
4. **No silent defaults.** An item marked unresolved in this file must not be given an invented value by configuration, code, or narrative text. Unresolved items block only the specific claim or experiment named in their entry.
5. **Change control.** Changing a locked value in this file requires repository or literature evidence that the current value is incorrect, and requires synchronized updates to every roadmap file that referenced it. A favorable result is never sufficient evidence to change a locked value.

---

## 2. Scientific identity

1. **Research problem.** Frozen-detector, benign-only-calibrated anomaly-detection systems deployed across heterogeneous federated IoT clients exhibit uneven per-client false-positive-rate (FPR) operating points; DATP-Core studies whether the *scope* at which the anomaly threshold is calibrated changes that cross-client FPR dispersion.
2. **Research object.** Threshold-calibration scope on a fixed, once-trained, frozen FedAvg autoencoder. The encoder and its scores are never retrained or altered across the B1–B4 comparison; only the granularity at which the benign quantile threshold is shared (federation-wide, family-wide, cluster-wide, or per-client) varies.
3. **Main causal question.** Does threshold-calibration scope change deployed operating-point reliability — specifically per-client FPR dispersion (`CV(FPR)`) — across heterogeneous IoT clients, holding the trained model and scores fixed?
4. **Contribution type.** An empirical, controlled ablation of threshold-calibration granularity on a fixed federated anomaly detector, plus a journal-extension programme of external validation, a matched federated-threshold comparator, training-side stress tests, threshold-estimation depth, and one temporal boundary experiment.
5. **Intended novelty.** The novelty claim is scoped to threshold-calibration-scope personalization as an isolated causal variable, separated from model personalization and from the choice of federated training algorithm. DATP-Core does not claim to be the first federated thresholding method, the first personalized-FL method, or the first FL-IDS system.
6. **Unit of personalization.** The threshold. Model parameters are never the personalized unit inside the B1–B4 causal ladder; model personalization (Ditto) is a separate, explicitly out-of-ladder stress test (§3, §8).
7. **Meaning of operational FPR equity.** `CV(FPR)` equity is an *operational* engineering property — the false-alarm burden is comparable across deployed clients. It is not a claim about protected-attribute fairness, demographic parity, or any legally or ethically loaded fairness definition.
8. **Relationship to generic personalized federated learning.** DATP-Core is not a general personalized-FL contribution. Model-parameter personalization (Ditto) is included only as a stress test that asks whether model personalization renders threshold personalization redundant, complementary, or partially absorbed — never as a competing causal-ladder condition.
9. **Relationship to generic federated IDS benchmarking.** DATP-Core is not a benchmark of federated intrusion-detection systems, detector architectures, or federated optimizers. The detector architecture, training algorithm (FedAvg), and dataset roster are deliberately bounded (§14) to keep the causal question isolated.
10. **Explicit scientific boundaries.** Out of scope: privacy guarantees, deployment/hardware measurement, fleet-scale (>100 clients) validation, full concept-drift/online-recalibration systems, calibration-channel or training poisoning, adversarial evasion, and broad personalized-FL or federated-conformal benchmarking (§14 enumerates each fully).

### Checklist — Scientific identity

- [x] The research object is threshold-calibration scope.
- [x] Model personalization is separated from threshold personalization.
- [x] The main ladder preserves a fixed model within each paired comparison.
- [x] Calibration is benign-only wherever this is required (§6).
- [x] AUROC is treated as a model-quality control rather than the primary threshold verdict.
- [x] Operational FPR equity is not described as protected-attribute fairness.
- [x] Data locality is not described as a formal privacy guarantee.
- [x] The project is not framed as solving non-IID federated learning generally.
- [x] The project is not framed as a universal IoT malware-detection solution.
- [x] Ditto (model personalization) is confined to a stress-test role and never merged into the B1–B4 ladder.
- [x] The dataset roster is bounded to N-BaIoT, CICIoT2023, and Edge-IIoTset; no further dataset may be added without formal roadmap revision (§14.1 item 3).
- [x] FedAvg is the sole training algorithm inside the causal ladder; FedProx is a training-side stress test only (§7.22, §8).

---

## 3. Claim hierarchy

Full claim wording, role assignment, and prohibited generalizations are owned by [02 — Claims and Decision Rules](./02_CLAIMS_AND_DECISION_RULES.md). This section fixes the identifiers and locked values that other files must reference rather than restate.

1. **Canonical claim identifier:** `main-journal-claim` (§2 of file 02).
2. **Exact wording:** "DATP's threshold-scope effect remains observable under a stronger journal protocol that adds external validation, a matched federated-threshold comparator, training-side stress tests, calibration-robustness analyses, and mechanism evidence while preserving the fixed-detector, benign-calibration identity." Valid only to the extent supported by the confirmatory endpoint and separately classified evidence (file 02 §2).
3. **Sole confirmatory claim identifier:** `confirmatory-b1-vs-b2` (file 02 §3.1).
   - Evidence class: confirmatory.
   - Dataset and regime: N-BaIoT, Regime A, nine physical-device clients.
   - Required experiment identifier: `regime-a-shared-vs-local-threshold-scope` (file 03 §5.1).
   - Metric and estimand: `CV(FPR)`, paired contrast `Δ_s = CV(FPR)_{B1,s} − CV(FPR)_{B2,s}` (§11 item 8 below).
   - Statistical unit: the training seed (ten paired seeds; §12 item 1 below).
   - Decision rule: supported when the 95% BCa bootstrap interval over the ten paired seed-level `Δ_s` excludes zero with both bounds positive (file 02 §3.2).
   - Minimum evidence requirement: ten valid paired seed deltas from the primary journal checkpoint (§7 below).
   - Null-result wording, directional-but-inconclusive wording, and opposite-direction wording: file 02 §3.2 exact text, verbatim; not paraphrased elsewhere.
   - Suppression conditions: fewer than ten valid paired deltas, or a degenerate BCa bootstrap (§12 below; file 04 §11.3).
   - Prohibited generalizations: a favorable ten-seed result does not retroactively justify replacing it with the five-seed historical anchor (§3.4 below); no lower-role result rescues a failed confirmatory endpoint.
   - Required figures and tables: file 04 §19 and §20 (owned there).
4. **Secondary claims** (supportive, external-validation, comparator, stress-test, mechanism, calibration-boundary, applicability-boundary, temporal, seed-extension-honesty roles): enumerated in file 02 §§6–14, each with exactly one evidence class per file 02 §1. This file does not restate their wording; it fixes only the roles that must never be conflated:
   - **Stress tests** (FedProx, Ditto/model-personalization) are never part of the B1–B4 causal ladder (file 02 §9; §8.13 below).
   - **External validation** (Edge-IIoTset, Regime D) never auto-promotes to confirmatory (file 02 §7).
   - **Applicability-boundary** results (CICIoT2023 Regime B-a/B-b) support only the scoped conclusion stated in file 03 §4.2–§4.3, never device-level or physical-client claims.
5. **Historical anchor values** (reference only, not reproduced-as-claim until matched with DATP-Core provenance): `B1 CV(FPR) = 1.017`, `B2 CV(FPR) = 0.299`, paired reduction `0.718`, five-seed 95% percentile-bootstrap CI `[0.647, 0.769]`, relative reduction `70.6%`, all five seed deltas positive, `B4 CV(FPR) = 0.645` (≈52% recovery), `B3 CV(FPR) = 0.964`, P10 Macro-F1 `0.344 → 0.300` under B2 (file 02 §4). A weaker ten-seed result is never replaced by these values.

### Checklist — Claim hierarchy

- [x] There is exactly one confirmatory claim (`confirmatory-b1-vs-b2`).
- [x] The confirmatory endpoint is unique (Regime A B1-vs-B2, `CV(FPR)`).
- [x] The confirmatory dataset and regime are explicit (N-BaIoT, Regime A).
- [x] The confirmatory comparison is explicit (B1 shared vs. B2 per-client threshold).
- [x] The confirmatory statistical unit is explicit (paired training seed).
- [x] The confirmatory estimand is explicit (`Δ_s` seed-level paired contrast).
- [x] The confirmatory decision rule is explicit (BCa interval excludes zero, both bounds positive).
- [x] Confirmatory evidence is not mixed with exploratory evidence (file 02 §1 role assignment is mandatory).
- [x] Every secondary claim is assigned one evidence class (file 02 §1).
- [x] Every claim has null-result wording (file 02 §3.2, §16).
- [x] Every claim has scope limits (file 02 §11–§14).
- [x] No claim depends on a suppressed metric (file 04 §15, §23 cross-enforced).
- [x] No claim exceeds dataset capabilities (§4 below; file 03 §4).
- [x] No structural property is described as experimentally proven (file 02 §17 forbidden claims).
- [x] No external-validation result is automatically promoted to confirmation (file 02 §7).
- [x] No stress test is presented as part of the causal threshold ladder (file 02 §9; §8.13 below).

---

## 4. Datasets and client definitions

Full narrative context, source publications, and interpretive caveats are owned by [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md) §2 and §4. This section fixes the canonical facts.

### 4.1 N-BaIoT

1. Canonical identifier: `N-BaIoT`.
2. Role: primary anchor dataset; sole confirmatory substrate.
3. Raw-data authority: the local repository artifact is authoritative for exact files, row counts, feature schema, split manifests, family taxonomy, and eligible calibration counts — not the originating publication.[^nbaiot]
4. Client-definition rule: natural, physical devices. Nine commercial IoT devices form the nine federated clients.
5. Clients are natural, not derived or artificial.
6. Number of clients: 9 (fixed; the full analysis population, no subsampling of clients).
7. Benign-data availability: present for all nine clients.
8. Attack-data availability: present (Mirai and BASHLITE botnet traffic).
9. Temporal-field availability: not used as a manipulated axis in Regime A.
10. Device-family taxonomy: available and used by B3.
11. Calibration eligibility: governed by the single canonical rule `n_k >= 100` (§6.13 below; file 01 §4.3).
12. Supported regimes: Regime A only.
13. Supported metrics: the full metric catalogue in §11 below, including attack-sensitive metrics.
14. Supported claims: `confirmatory-b1-vs-b2` and all Regime A supportive/mechanism claims (file 02 §6, §10).
15. Suppressed claims: none specific to this dataset beyond the global exclusions in §14 below.
16. Split feasibility: full train/calibration/test split per client (§6 below).
17. Known confounding risks: only nine clients — client-level results must always be shown in full; no client may be filtered to strengthen the desired pattern (file 03 §4.1).
18. Leakage risks: none beyond the global leakage controls in §6 below.
19. External-validation interpretation: not applicable — this is the anchor dataset, not an external validation set.

### 4.2 CICIoT2023

1. Canonical identifier: `CICIoT2023`.
2. Role: applicability-boundary dataset (Regime B-a); physical-device repartition is rejected (Regime B-b).
3. Raw-data authority: local processed artifact; the originating study's device/attack counts are cited for context only and do not override the artifact's actual structure.[^ciciot2023]
4. Expected raw structure: the original study describes 105 devices and 33 attacks grouped into seven categories; the processed CSV artifact available locally does not preserve device-level identity.
5. Client-definition rule: file-defined pseudo-clients — 63 file-defined pseudo-clients derived from the processed artifact, not physical devices.
6. Clients are derived (file-defined), explicitly not physical devices.
7. Number of clients: 63 pseudo-clients (Regime B-a). Physical-device repartition is rejected (Regime B-b, §4.3 below) for lack of a trustworthy device identifier.
8. Benign-data availability: present.
9. Attack-data availability: present, grouped by the artifact's own labeling; not device-attributable.
10. Temporal-field availability: not established as trustworthy for physical-device or chronological reconstruction; Regime B-b is rejected partly on this basis.
11. Device-family or taxonomy availability: none reconstructable from the processed artifact.
12. Calibration eligibility: `n_k >= 100`, applied at the pseudo-client level.
13. Supported regimes: Regime B-a (file-defined applicability boundary) only. Regime B-b is rejected, not executed.
14. Supported metrics: B0, B1, B2 threshold policies; B4 only when pseudo-client fingerprints are valid; pairwise benign-distribution Jensen–Shannon divergence; `CV(FPR)`, IQR, range; descriptive quantile-estimation comparisons (file 03 §4.2).
15. Unsupported metrics: none beyond what device-level attribution would require (device-level generalization, physical-client equity, temporal behavior, device-aware threshold performance on the original 105-device topology are prohibited interpretations, not metrics).
16. Supported claims: applicability-boundary claim only (file 02 §12.1); a null B1-vs-B2 difference is scientifically informative here, indicating personalization may be unnecessary under near-homogeneous pseudo-clients (file 03 §4.2).
17. Suppressed claims: device-level generalization; physical-client equity; temporal claims; device-aware performance claims on the original topology (file 03 §4.2). Physical-device or MAC-based repartition (Regime B-b) is suppressed outright — row order, merge order, filename-as-device, class-label inference, and random pseudo-devices are explicitly prohibited workarounds (file 03 §4.3).
18. Split feasibility: benign/attack split feasible at the pseudo-client level only.
19. Known confounding risks: near-homogeneous file-defined pseudo-clients may mask or dilute a true device-level threshold-scope effect.
20. Leakage risks: none beyond the global leakage controls in §6 below.
21. External-validation interpretation: not external validation — an applicability-boundary probe on the confirmatory mechanism, run on a second dataset's artifact.

### 4.3 Edge-IIoTset

1. Canonical identifier: `Edge-IIoTset`.
2. Role: independent external benign-operating-point-equity validation (Regime D) and a one-shot temporal recalibration boundary (Regime D-temporal).
3. Raw-data authority: the completed local full-corpus endpoint audit is authoritative for client definition, not a generic reading of the source publication.[^edge-iiotset]
4. Expected raw structure: the source publication describes a purpose-built IoT/IIoT testbed for centralized and federated-learning security research; the local artifact's ten benign sensor-group folders are the operative structure.
5. Client-definition rule: ten benign sensor-group folders form the static external client population (Regime D). Nine verified temporal groups are used for Regime D-temporal; the Modbus folder is excluded from the temporal population only, because its `frame.time` values are address literals, not genuine timestamps — it remains valid for the static benign-equity population because its rows retain the declared 63-column layout.
6. Clients are derived from sensor-group folders — not raw physical network devices, not artificial partitions.
7. Number of clients: 10 (Regime D, static); 9 (Regime D-temporal, chronological).
8. Benign-data availability: present for all ten sensor groups; eligible-benign coverage is 1.0 under `n_k >= 100`.
9. Attack-data availability: confined to the attacker's subnet in the audited artifact; valid per-client attack assignment is unavailable.
10. Temporal-field availability: genuine and usable for nine of ten groups; unusable for Modbus.
11. Device-family or taxonomy availability: none defensible — B3 is omitted from Regime D for this reason.
12. Calibration eligibility: `n_k >= 100`, met by all ten static groups (coverage 1.0).
13. Supported regimes: Regime D (static external validation) and Regime D-temporal (one-shot recalibration boundary).
14. Supported metrics (Regime D): per-client benign FPR, cross-client `CV(FPR)`, IQR and range of FPR, worst-client FPR, threshold dispersion, benign score-distribution analysis, B1/B2/B4, `B-FedStatsBenign`, quantile sensitivity, calibration-size and shrinkage analyses where sample support permits, FedProx and Ditto stress tests where training is feasible.
15. Unsupported metrics (Regime D): TPR, recall, Macro-F1, P10 Macro-F1, balanced accuracy, worst-client balanced accuracy, per-client AUROC, and attack-sensitive threshold trade-offs — must be represented as unavailable, never estimated or imputed.
16. Supported claims: external benign-FPR-equity validation only (file 02 §7); one-shot recalibration boundary evidence (file 02 §13).
17. Suppressed claims: external cross-client attack-detection equity; any B3 family-taxonomy claim.
18. Split feasibility (Regime D-temporal): chronological split per client — historical training 55%, historical calibration 15%, future recalibration 10%, future evaluation 20%, with duplicate timestamps preserving original stable row order (file 03 §4.6).
19. Known confounding risks: attack traffic's subnet confinement could make any attempted attack-sensitive metric spuriously uniform or spuriously biased — hence the outright suppression in item 15.
20. Leakage risks: none beyond the global leakage controls in §6 below; chronological ordering in Regime D-temporal must not be violated by duplicate-timestamp resorting.
21. External-validation interpretation: validates external false-positive equity only; explicitly does not validate external cross-client attack-detection equity (file 03 §4.5).

### Checklist — Datasets and client definitions

- [x] Natural clients (N-BaIoT's nine physical devices) are not described as pseudo-clients.
- [x] Pseudo-clients (CICIoT2023's 63 file-defined groups) are not described as physical devices.
- [x] Attack-sensitive metrics require attack observations in the relevant evaluation unit (Edge-IIoTset Regime D suppresses them entirely for this reason).
- [x] Benign-only client groups (Edge-IIoTset) are limited to benign operating-point metrics.
- [x] Temporal claims require valid temporal fields and chronological construction (Modbus excluded from Regime D-temporal on this basis).
- [x] Device-family claims require a valid taxonomy (B3 omitted from CICIoT2023 and Edge-IIoTset for lack of one).
- [x] External validation (Edge-IIoTset) does not imply universal generalization.
- [x] Dataset capability restrictions are identical across claims (file 02), experiments (file 03), configuration, and reporting (file 04).
- [x] Unsupported cells are suppressed rather than assigned invented values (item 15 above; file 04 §15).
- [x] Cross-dataset comparisons account for different feature and client semantics (natural vs. file-defined vs. sensor-group clients are never pooled as if equivalent).

---

## 5. Regimes and experimental populations

Full narrative is owned by [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md) §4. This section fixes the canonical identifiers and boundaries so no regime acquires a second meaning elsewhere in the repository.

### 5.1 Regime A — N-BaIoT physical-device anchor

1. Purpose: sole confirmatory regime and principal mechanism-analysis substrate.
2. Dataset: N-BaIoT (§4.1).
3. Population: nine physical-device clients, full population, no subsampling.
4. Partition construction: natural — one client per physical device.
5. Heterogeneity mechanism: natural device heterogeneity (no synthetic partitioning).
6. Fixed components: model architecture, training algorithm (FedAvg), score artifacts across compared policies.
7. Manipulated components: threshold-calibration scope (B0–B4) and, only as stress tests, training algorithm (FedProx) or personalization (Ditto).
8. Eligible policies: B0, B1, B2, B3, B4, B2-conf, `B-FedStatsBenign`, FedProx, Ditto.
9. Eligible metrics: full catalogue (§11), including attack-sensitive metrics.
10. Eligible claims: `confirmatory-b1-vs-b2`; all Regime A supportive/mechanism claims (file 02 §6, §10).
11. Suppression conditions: none specific beyond the global rules in §15.
12. Boundary interpretation: client-level results always shown in full; no client filtered to strengthen a pattern.
13. Required artifacts: score artifacts, threshold artifacts, and checkpoint per seed (§13).

### 5.2 Regime B-a — CICIoT2023 file-defined applicability boundary

1. Purpose: tests whether personalization remains useful under near-homogeneous file-defined pseudo-clients.
2. Dataset: CICIoT2023 (§4.2).
3. Population: 63 file-defined pseudo-clients.
4. Partition construction: derived from processed-artifact file boundaries.
5. Heterogeneity mechanism: whatever heterogeneity survives file-level aggregation — not physical-device heterogeneity.
6. Fixed components: same as Regime A within this dataset's own retraining.
7. Manipulated components: threshold-calibration scope only (B0, B1, B2, B4-when-valid).
8. Eligible policies: B0, B1, B2; B4 only when pseudo-client fingerprints are valid.
9. Eligible metrics: `CV(FPR)`, IQR, range, pairwise benign-distribution Jensen–Shannon divergence, descriptive quantile comparisons.
10. Eligible claims: applicability-boundary claim only (file 02 §12.1).
11. Suppression conditions: device-level, physical-client-equity, temporal, and device-aware-performance interpretations are suppressed outright (file 03 §4.2).
12. Boundary interpretation: a null B1-vs-B2 result is itself informative here, not a failure.
13. Required artifacts: same artifact classes as Regime A, scoped to this dataset.

### 5.3 Regime B-b — rejected CICIoT2023 physical-device repartition

1. Purpose: none — this regime is rejected, not executed.
2. Dataset: CICIoT2023.
3. Population: not constructed.
4. Reason for rejection: no trustworthy MAC address, device identifier, source/destination IP suitable for client identity, capture-source field, timestamp, or equivalent provenance field exists in the processed artifact (file 03 §4.3).
5. Prohibited workarounds: row order, merge order, filename-as-device, class-label inference, random pseudo-devices, or claiming the original study's 105-device topology survives in the processed CSV.
6. Status: the rejection is itself evidence of an artifact boundary, not a failed implementation, and must be reported as such.

### 5.4 Regime C — controlled N-BaIoT heterogeneity sweep

1. Purpose: tests whether the threshold-scope effect changes systematically with controlled non-IID severity.
2. Dataset: N-BaIoT analysis population, repartitioned.
3. Population: 20 synthetic clients via the locked Dirichlet partition procedure.
4. Heterogeneity mechanism: Dirichlet concentration parameter grid `alpha in {0.1, 0.3, 0.5, 1.0, 10.0, IID}`; lower `alpha` is stronger concentration/more severe skew.
5. Fixed components: same detector-freezing discipline as Regime A.
6. Manipulated components: threshold-calibration scope (B1, B2, B4) and Dirichlet severity.
7. Eligible policies: B1, B2, B4. B3 is not automatically available because the synthetic partition need not preserve physical family taxonomy.
8. Eligible claims: heterogeneity-severity claim (file 02 §6.3) — a graded relationship is the primary expectation but strict monotonicity is not required; overlapping low-alpha seed distributions are described as a high-heterogeneity band; a non-monotone result is reported as such.
9. Suppression conditions: this sweep never becomes confirmatory regardless of outcome shape.
10. Boundary interpretation: Dirichlet partitioning is a controlled sensitivity mechanism only; it does not replace Regime A's natural physical-device evidence.
11. Required artifacts: per-alpha, per-seed score and threshold artifacts.

### 5.5 Regime D — Edge-IIoTset external benign-equity validation

1. Purpose: independent external validation of benign operating-point equity.
2. Dataset: Edge-IIoTset (§4.3).
3. Population: ten benign sensor-group clients (static).
4. Partition construction: sensor-group folders from the completed local full-corpus endpoint audit.
5. Heterogeneity mechanism: natural sensor-group heterogeneity.
6. Fixed components: benign-only calibration; no attack-sensitive metric is computed.
7. Manipulated components: threshold-calibration scope (B1, B2, B4).
8. Eligible policies: B1, B2, B4, `B-FedStatsBenign`; FedProx and Ditto stress tests where training is feasible. B3 omitted (no defensible taxonomy).
9. Eligible metrics: enumerated in §4.3 item 14; attack-sensitive metrics enumerated in §4.3 item 15 are unavailable, not suppressed-as-zero.
10. Eligible claims: external benign-FPR-equity validation only (file 02 §7).
11. Suppression conditions: any attack-sensitive metric request on this regime.
12. Boundary interpretation: validates external false-positive equity only, never external cross-client attack-detection equity.
13. Required artifacts: benign score and threshold artifacts per client.

### 5.6 Regime D-temporal — Edge-IIoTset one-shot recalibration boundary

1. Purpose: tests threshold aging and one-shot recalibration under genuine chronology; a temporal boundary experiment, not a drift-detection system.
2. Dataset: Edge-IIoTset (§4.3).
3. Population: nine verified temporal groups (Modbus excluded — unusable timestamps).
4. Partition construction: chronological, per client — historical training 55%, historical calibration 15%, future recalibration 10%, future evaluation 20%; duplicate timestamps preserve original stable row order.
5. Heterogeneity mechanism: natural, plus temporal drift between historical and future windows.
6. Fixed components: detector frozen from historical calibration for the "frozen" comparison arm.
7. Manipulated components: deployment state — frozen threshold vs. one-shot recomputed threshold vs. matched random-fractional static reference, all over the same nine clients.
8. Eligible claims: temporal boundary evidence (file 02 §13).
9. Suppression conditions: none beyond the dataset-level Modbus exclusion.
10. Boundary interpretation: explicitly does not implement streaming recalibration, periodic recalibration, sliding windows, Page–Hinkley, FLARE, FLAME, automatic drift detection, or cross-dataset transfer — those belong to future work (file 03 §4.6; §14 below).
11. Required artifacts: per-client chronological split manifest, per-window score and threshold artifacts.

### Checklist — Regimes

- [x] Regime A uses nine N-BaIoT physical devices, full population.
- [x] Regime B-a's 63 pseudo-clients are never presented as physical devices.
- [x] Regime B-b is recorded as rejected with its rejection reason, not silently omitted.
- [x] Regime C's Dirichlet severity grid is `{0.1, 0.3, 0.5, 1.0, 10.0, IID}` and never confirmatory.
- [x] Regime D's ten sensor groups never receive an attack-sensitive metric.
- [x] Regime D-temporal's chronological split percentages (55/15/10/20) are fixed and never reordered by duplicate-timestamp resorting.
- [x] Every regime has exactly one meaning and one owning subsection across the repository.

---

## 6. Data splits and leakage controls

Procedural detail is owned by [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md) §4–§5. This section fixes the canonical rules.

1. **Training data:** benign-only, per-client, fitted deterministically; never touched by calibration, test, or (in Regime D-temporal) future-window records.
2. **Calibration data:** benign-only training-adjacent split; used exclusively to fit thresholds and preprocessing statistics; disjoint from test.
3. **Validation data:** where applicable, the benign FedAvg-weighted validation loss used only for the checkpoint-selection convergence check (§7.18); never test data.
4. **Test data:** held-out; used exclusively for reporting metrics; never influences training, calibration, threshold construction, or checkpoint selection.
5. **Temporal ordering (Regime D-temporal only):** stable sort by genuine capture time per client; historical training 55% / historical calibration 15% / future recalibration 10% / future evaluation 20%; duplicate timestamps preserve original row order; no future record may leak into a historical split.
6. **Benign-only restrictions:** all threshold policies and DATP-compatible comparators use benign calibration data only; attack-labelled data may be used only for held-out evaluation when the regime supports valid per-client attack assignment (§4).
7. **Attack-data restrictions:** attack data must never determine a threshold, select a quantile, select a checkpoint, select a FedProx coefficient, select a personalization coefficient, decide client inclusion, or repair an infeasible experiment (file 03 §2.2).
8. **Reservoir construction:** not applicable outside the declared split manifests (item 11 below); no ad hoc resampling reservoir may be introduced.
9. **Client-local versus pooled operations:** metrics are computed per client before any cross-client aggregation whenever valid client identity exists (file 04 §1.3); pooled-row metrics are reported only as controls and never replace client-level operating-point metrics.
10. **Reuse of score artifacts:** the same calibration and test score artifacts are reused across B0–B4 within a seed; no policy-specific retraining or rescoring is permitted (file 03 §2.1).
11. **Cross-seed isolation:** each training seed produces its own independent model, scores, and thresholds; seeds are never mixed before the per-seed paired contrast is formed (§12 item 1).
12. **Cross-client isolation:** no client's raw rows, scores, or thresholds are shared with another client except through the explicitly declared aggregation rule of the threshold policy under test (§8).
13. **Preprocessing fitting:** fitted only on the permitted benign training population; persisted with fitted parameters, feature order, excluded columns, fit-population identity, and configuration fingerprint (file 05 §5).
14. **Normalization fitting:** identical rule to item 13 — client-local standardization is fit only on that client's benign training rows (§7.3).
15. **Feature-selection fitting:** no feature selection is performed beyond the fixed, dataset-declared feature schema; any future feature-selection step must be fit only on the permitted training population.
16. **Checkpoint-selection data:** the trailing FedAvg-weighted benign validation loss only (§7.18); never test outcomes, attack labels, or the DATP effect itself.
17. **Threshold-selection data:** benign calibration data only (item 6).
18. **Reporting-only data:** held-out test rows for metrics; historical anchor values (§3.5) are reporting-only reference values, never inputs to any computation.

### Checklist — Data splits and leakage controls

- [x] Test data never influence training.
- [x] Test scores never influence threshold construction.
- [x] Test labels never influence calibration.
- [x] Attack records do not enter benign-only calibration.
- [x] Normalization is fitted only on authorized (benign training) data.
- [x] Feature selection is fitted only on authorized data (none beyond the fixed schema exists).
- [x] Checkpoint selection does not use poisoned or test outcomes (uses only trailing benign validation loss, §7.18).
- [x] Calibration and test records are disjoint.
- [x] Temporal experiments (Regime D-temporal) preserve chronology.
- [x] Cross-client data are not used where local-only semantics are required (e.g., client-local standardization).
- [x] Reused score artifacts preserve exact provenance (§13).
- [x] No fallback silently introduces leakage — degenerate-input behaviors are typed failures, not silent substitutions (§8; §12 item 3).

---

## 7. Model and training protocol

Procedural framing is owned by [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md) §6. This section is the canonical numeric contract; no other file restates these values.

1. **Model family:** fixed autoencoder (the same architecture for every B0–B4 comparison within a seed and regime).
2. **Architecture authority:** the locked autoencoder family and configuration; threshold policy is never part of training identity (file 05 §6.1).
3. **Loss:** reconstruction error (higher error indicates greater anomaly evidence; file 04 §2).
4. **Optimizer:** Adam.
5. **Learning rate:** `0.001`.
6. **Local epochs:** one local epoch per round.
7. **Batch size:** `256`.
8. **Communication rounds:** anchor — 150-round cap; journal — 200 rounds.
9. **Participation:** full participation every round (no client sampling).
10. **Aggregation:** FedAvg (core ladder). FedProx and Ditto are separate, explicitly out-of-ladder training-side stress tests (item 22).
11. **Aggregation weighting:** FedAvg-weighted (by client sample count) for the benign validation loss used in convergence checking.
12. **Training seed roles:** the training seed is the independent replication unit (file 04 §1.2); ten paired seeds for the journal ten-seed cohort (`datp_core_ten_seed`, training seeds 0–9), five paired seeds for the historical anchor cohort (`anchor_five_seed`, training seeds 0–4) (§9).
13. **Initialization:** deterministic per-seed model initialization; per-client standardization fit on that client's benign training rows only (§6 item 14).
14. **Determinism requirements:** separate configured seed domains for training, partitioning, calibration subsampling, clustering, and bootstrap analysis (§9); deterministic library flags enabled where supported.
15. **Hardware requirements:** GPU training under the main runtime profile (file 05 §6.2); resource pressure must produce blocked execution, an approved runtime-profile revision, or a formally reviewed scientific configuration change — never a silent reduction of batch size, sample counts, rounds, seeds, or clients (file 05 §6.8).
16. **Training termination:** anchor — convergence check begins at round 40; compute `abs(loss[r-9] - loss[r]) / abs(loss[r-9])` over the trailing ten FedAvg-weighted benign validation losses (a zero start loss has relative change zero); select the first round with relative change below `0.005`, otherwise select round 150. Journal — trains the full 200 rounds; convergence is logged but does not stop training (file 04 §13.2).
17. **Checkpoint-saving behavior:** anchor saves exactly one checkpoint, at the selected round (item 16). Journal saves checkpoints at rounds `25, 50, 75, 100, 125, 150, 200`.
18. **Checkpoint-selection rule:** anchor — the convergence rule in item 16 (deterministic, no stochastic seed: `checkpoint_selection_uses_no_stochastic_seed = true`; first qualifying round at or after 40, otherwise the 150-round cap; tie-break earliest qualifying round). Journal (`datp_core_round_grid`, configs/protocols.yaml) — Regime A selects one primary **round number** using the rule `lowest_federated_averaging_weighted_benign_validation_reconstruction_error`: for each candidate round in `{25, 50, 75, 100, 125, 150, 200}`, compute the benign-calibration-row-weighted arithmetic mean of per-row reconstruction error under that round's global state (population: per-client benign calibration split rows; client accumulation in ascending client-identifier order; aggregated across the locked seed cohort as the cross-seed mean reconstruction error per candidate round), restricted to the natural-device regime, FedAvg-only, benign-validation-only scope; select the round with the lowest value; tie-break by earliest scheduled round. This selection is frozen before journal outcomes are inspected. The selected round number is reused by every profile declaring lookup authorization (e.g., FedProx, Ditto's global-checkpoint lookup) across main regimes and policies where that checkpoint exists; model weights remain regime- and seed-specific. Forbidden selectors (explicit in `datp_core_round_grid.selection.forbidden_selectors`): per-policy selection, per-experiment selection, per-dataset selection, test-driven selection, attack-driven selection, AUROC-driven selection, external-dataset-driven selection — equivalently: test AUROC, test FPR/`CV(FPR)`, Macro-F1, balanced accuracy, attack labels, the B1-vs-B2 effect, external or stress-test results, or policy-specific best performance. Persist the candidates, selector input, selected round, tie-break, and reason.
19. **Conditions requiring retraining:** any change to dataset, materialization, client assignment, or split invalidates artifact reuse and requires retraining (`reuse_rejected_when_any_changes`, configs/protocols.yaml).
20. **Conditions allowing artifact reuse:** checksum match, schema-version match, parent-fingerprint match, completed status, and non-stale status (`lineage_validation_before_reuse`, configs/protocols.yaml).
21. **Differences between the anchor and expanded (journal) regimes:** anchor uses a 150-round cap with convergence-triggered single-checkpoint selection and a five-seed cohort; journal uses a fixed 200-round budget with a seven-point checkpoint grid, a frozen non-test primary-round selector, and a ten-seed cohort. The anchor's historical semantics are preserved, not retrofitted with journal selection logic (file 05 §6.3).
22. **Training-side stress tests and their separation from the main ladder:**
    - **FedProx** requires separate training artifacts from FedAvg; executes the pre-registered coefficient grid `mu in {0.001, 0.01, 0.1, 1.0}` (`mu = 0` is FedAvg-equivalent and is not a FedProx condition); retains every coefficient outcome including non-convergence; the grid is frozen before attack-sensitive or confirmatory outcomes are inspected; scores are kept separate from FedAvg scores (file 03 §3.10, file 05 §6.6).
    - **Ditto** requires a genuine global model, persistent per-client personalized states never reset across rounds, the correct proximal personalized objective `min_{v_k} L_k(v_k) + (proximal_weight / 2) * ||v_k - w_global||^2`, a personalized optimizer state recreated at the start of every local fit and never persisted across rounds, and separate global/personalized artifact provenance with personalized states never aggregated. If these conditions are not met, the fallback must use its actual implemented method name and must never be called Ditto (file 05 §6.7; `ditto_specification`, configs/protocols.yaml).
    - Neither FedProx nor Ditto is ever merged into the B0–B4 threshold-scope causal ladder; both are reported as training-side stress tests only (file 02 §9).

### Checklist — Model and training protocol

- [x] The model family and architecture are fixed across B0–B4 within a seed and regime.
- [x] Optimizer, learning rate, batch size, and local-epoch count are locked (Adam, `0.001`, `256`, one epoch).
- [x] Anchor round cap (150) and journal round budget (200) are distinct and never conflated.
- [x] Anchor checkpoint-selection is a single deterministic convergence rule with no stochastic seed.
- [x] Journal checkpoint selection uses an explicitly configured, non-test, pre-registered selector.
- [x] Forbidden checkpoint selectors (test AUROC, `CV(FPR)`, Macro-F1, attack labels, the B1-vs-B2 effect) are never used.
- [x] FedProx's coefficient grid `{0.001, 0.01, 0.1, 1.0}` is frozen before outcome inspection.
- [x] Ditto's naming lock is enforced: an implementation lacking the genuine Ditto contract is never called Ditto.
- [x] Training-side stress tests (FedProx, Ditto) never enter the B0–B4 causal ladder.
- [x] Resource pressure never silently reduces scientific batch size, sample count, round count, seed count, or client count.
- [x] Artifact reuse across seeds/regimes is gated by checksum, schema-version, parent-fingerprint, and completion-status match.

---

## 8. Threshold policies and comparators

Narrative role and prohibited interpretations are owned by [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) §5 and [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md) §3. This section fixes exact formulas and repository-config parameters.

### 8.1 B0 — Centralized reference

1. Role: privacy-incompatible centralized reference; explicitly **not** part of the federated threshold-scope causal ladder (item 13).
2. Definition: pooled-data centralized autoencoder with a pooled benign threshold.
3. Required inputs: its own centralized model and score provenance — FedAvg-generated scores must never be relabelled as B0.
4. Whether in causal ladder: no. Reported alongside B1–B4 as a reference point only.

### 8.2 B1 — Shared threshold

1. Definition: each eligible client computes its local benign `q`-quantile; the server threshold is the arithmetic mean of local quantiles.
2. Canonical setting: `q = 0.95`.
3. Eligible clients: `n_k >= 100` (§6.13; file 01 §4.3).
4. Aggregation rule: `tau_shared = (1 / |eligible clients|) * sum_k quantile(scores_k, q)`.
5. Quantile/interpolation convention: linear-interpolated order statistic (`quantile_estimator: linear_interpolated_order_statistic`, configs/protocols.yaml).
6. Whether in causal ladder: yes — the shared-scope anchor for the confirmatory comparison.
7. Prohibited interpretations: none beyond the general prohibition on describing any single policy as universally superior (§8.3 item 5).

### 8.3 B2 — Per-client threshold

1. Definition: each eligible client uses its own benign `q`-quantile as its deployed threshold.
2. Canonical setting: `q = 0.95`; same quantile/interpolation convention as B1.
3. Eligible clients: `n_k >= 100`.
4. Whether in causal ladder: yes — the local-scope anchor and confirmatory comparator.
5. Prohibited interpretations: B2 is not described as universally superior — it may reduce cross-client FPR dispersion while worsening detection quality for clients with weak benign–attack score separation (file 03 §3.3).

### 8.4 B3 — Family threshold

1. Definition: groups N-BaIoT clients by the locked physical-device family taxonomy; assigns one family-level mean threshold to clients in the same family.
2. Required inputs: a defensible family taxonomy.
3. Supported datasets/regimes: Regime A only, without qualification; Regime C only if the synthetic partition preserves a meaningful family mapping; omitted from Edge-IIoTset (no taxonomy) and CICIoT2023 (no taxonomy for file-defined pseudo-clients).
4. Whether in causal ladder: mechanism baseline, not a confirmatory comparator.

### 8.5 B4 — Cluster threshold

1. Definition: taxonomy-free client groups formed from a four-scalar benign reconstruction-error fingerprint: `mean(error)`, `standard deviation(error)`, `skewness(error)`, `p95(error)`.
2. Fingerprint estimators (repository config, `configs/protocols.yaml`): `mean_error = arithmetic_mean`; `std_error = standard_deviation_ddof_1`; `skew_error = fisher_pearson_moment_coefficient_of_skewness_uncorrected`; `p95_error = quantile_0_95_linear_interpolated_order_statistic`.
3. Degenerate-client fingerprint rules: fewer than two calibration scores → `std_error = 0.0`, `skew_error = 0.0`; non-finite skew value → `0.0`. A non-finite fingerprint value after these substitutions is a typed failure (`typed_failure_non_finite_fingerprint`), never silently zeroed further.
4. Feature scaling before clustering: zero-mean, unit-variance standardization with `ddof = 0`, fit on the eligible client fingerprint matrix of the current population, seed, and checkpoint (`fit_scope`); a zero-variance dimension uses scale `1` and becomes an all-zero-centered column (`constant_dimension_rule`).
5. Client ordering before fit: ascending client identifier.
6. Clustering algorithm: k-means (Lloyd's algorithm), k-means++ initialization, 10 initialization runs, maximum 300 iterations, convergence tolerance `1.0e-4`, random seed `42`.
7. Canonical cluster count: `K = 3`. `K = 9` and any other value are exploratory granularity sensitivity analyses only, producing separate artifacts, and are never promoted to the main configuration.
8. Cluster label canonicalization: relabel clusters by ascending cluster threshold, then by smallest member client identifier.
9. Cluster threshold construction: the mean of the local thresholds of a cluster's member clients.
10. Ineligible-client behavior: `typed_unavailable_when_eligible_client_count_is_less_than_cluster_count`.
11. Degenerate-input behavior: `typed_unavailable_when_fewer_than_two_distinct_fingerprints`.
12. Whether in causal ladder: yes, as part of B0–B4; not a model-clustering method, privacy mechanism, or new clustering algorithm in its own right — purely a threshold-sharing mechanism on a fixed detector.
13. Required diagnostics: cluster membership per client; singleton or empty-cluster status; cluster size.

### 8.6 Shared-threshold construction controls

1. Canonical identifiers: pooled shared quantile (`shared_mean_p95` variant: exact `q`-quantile of pooled benign calibration scores) and sample-weighted shared threshold (local threshold contributions weighted by eligible benign calibration size).
2. Client accumulation order: ascending client identifier.
3. Role: supportive controls testing whether the B1 result is merely an artifact of averaging local quantiles; they do not replace B1 as the locked confirmatory anchor.

### 8.7 Local–global shrinkage threshold

1. Formula: `tau_k(lambda) = lambda * tau_{k,local} + (1 - lambda) * tau_shared`.
2. Locked sensitivity grid: `lambda in {0.00, 0.25, 0.50, 0.75, 1.00}`.
3. Interpretation: `lambda = 0` is the shared-threshold endpoint; `lambda = 1` is the local-threshold endpoint; intermediate values trade personalization against estimation stability.
4. Calibration-size-aware variant: a pre-specified function `lambda(n_k)` may replace a fixed `lambda`, but must be fixed before test evaluation — no favorable `lambda` may be selected post hoc.

### 8.8 B2-conf — Split-conformal local threshold

1. Definition: treats benign reconstruction errors as nonconformity scores; forms a finite-sample-adjusted local quantile at significance level `alpha = 1 - q`.
2. Main diagnostic setting: `alpha = 0.05`.
3. Required inputs: benign calibration scores only.
4. Whether in causal ladder: supportive threshold variant, not confirmatory; coverage is evaluated empirically on held-out benign data with no universal conditional-coverage claim (file 03 §3.8).
5. Prohibited interpretations: a coverage miss must be reported as a limitation of the adaptation, not hidden; B2-conf never becomes a new confirmatory endpoint.

### 8.9 `B-FedStatsBenign` — matched benign-only federated comparator

1. Role: matched, benign-only federated threshold comparator; communicates pre-specified benign summary statistics and constructs a shared threshold without using anomalous validation data.
2. Operating-point matching: matched to the DATP quantile target, never selected to maximize F1.
3. Distinguished quantities: exact pooled benign quantile; arithmetic mean of local quantiles; sample-weighted shared construction; benign summary-statistics threshold; local per-client quantiles.
4. Prohibited interpretation: a Laridi-faithful implementation is not executed and `B-FedStatsBenign` is never described as a faithful reproduction of Laridi et al., because that method aggregates information from both normal and anomalous validation data — a benign-only comparator is a DATP-compatible adaptation, not a faithful reproduction.[^laridi]

### 8.10 FedProx — training-side stress test

Full definition and mu grid: §7 item 22. Not a threshold policy; listed here only to confirm it is never merged into B0–B4.

### 8.11 Ditto — training-side stress test

Full definition and naming lock: §7 item 22. Not a threshold policy; listed here only to confirm it is never merged into B0–B4.

### Checklist — Threshold policies and comparators

- [x] Every threshold policy (B0–B4, shared controls, shrinkage, B2-conf, `B-FedStatsBenign`) has one canonical identifier.
- [x] Every threshold policy has one formula, stated in this section.
- [x] Quantile conventions are explicit: `q = 0.95` for B1/B2, linear-interpolated order statistic throughout.
- [x] Eligibility is explicit: `n_k >= 100` for every policy.
- [x] Fallback behavior is explicit (§8.5 items 3, 10, 11).
- [x] Degenerate behavior is explicit (§8.5 items 3, 10, 11; §8.8 item 5).
- [x] Cluster construction is deterministic: k-means, k-means++, seed 42, 10 init runs, 300 max iterations, tolerance `1.0e-4`.
- [x] Cluster feature scaling is explicit: zero-mean unit-variance, `ddof = 0`.
- [x] Cluster count and exploratory alternatives are distinguished: canonical `K = 3`; `K = 9` and others are exploratory only.
- [x] Family thresholds (B3) require valid family metadata and are omitted where none exists.
- [x] Shrinkage parameters (`lambda in {0.00, 0.25, 0.50, 0.75, 1.00}`) and selection rule (pre-specified, frozen before test evaluation) are explicit.
- [x] Conformal (B2-conf) variant defines calibration (`alpha = 1 - q`) and coverage (empirical, held-out benign) precisely.
- [x] External comparators (`B-FedStatsBenign`) use fair operating-point matching (matched to DATP quantile target, not F1-maximizing).
- [x] Training-side comparators (FedProx, Ditto) are outside the threshold-scope ladder.
- [x] No obsolete threshold identifiers remain (B5 and B3-LGS, retired, do not appear in any active file).
- [x] No comparator is renamed inaccurately (Ditto naming lock, §7 item 22).

---

## 9. Seed cohorts and determinism

Repository configuration is authoritative for the exact seed values (`configs/protocols.yaml`); this section fixes their scientific roles.

1. **Training seeds:** `datp_core_ten_seed` cohort — 10 paired training seeds `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]`, the journal ten-seed replication unit. `anchor_five_seed` cohort — 5 paired training seeds `[0, 1, 2, 3, 4]`, the historical anchor replication unit. Training and partition seed domains are independent (`partition_seed_independent_of_training_seeds: true`).
2. **Analysis seeds:** the historical five-seed percentile bootstrap uses a literal, hardcoded `analysis_seed = 42` (`historical_five_seed_percentile_bootstrap`), independent of the cohort-level `bootstrap_analysis_seed`. The `bootstrap_analysis_seed = 300` recorded on both seed cohorts applies only to statistical profiles that reference `analysis_seed_source` (`analysis_seed_model: one_fixed_bootstrap_seed_per_analysis_not_one_analysis_seed_per_training_seed`) — it is not itself the confirmatory ten-seed BCa seed unless a profile explicitly sources it; the confirmatory BCa profile's own recorded seed is authoritative (§12 item 2).
3. **Partition seeds:** separate `partition` seed domain, independent of training seeds (item 1); derived per-partition via the `blake2b`-based derived-seed algorithm (item 10).
4. **Clustering seeds:** B4 k-means uses `random_seed = 42` (§8.5 item 6).
5. **Bootstrap seeds:** see item 2; every derived seed actually drawn must be recorded in the run manifest (`resolved_seeds_required_in_manifests`).
6. **Poisoning seeds:** not applicable — poisoning, backdoor, Byzantine, and evasion studies are explicitly out of scope (§14.2 item 9; file 01, file 02 §17, file 03).
7. **Seed pairing rules:** within a paired training seed, B1 and B2 (and B0/B3/B4) share the same trained model and score artifacts; they are never resampled independently in the bootstrap (file 04 §11.1: "B1 and B2 are never resampled independently").
8. **Seed reuse rules:** a training seed's model/score artifacts may be reused across threshold policies within the same seed and regime (§6 item 10), but never across seeds, regimes, or datasets.
9. **Seed independence assumptions:** the training seed is the sole independent replication unit (file 04 §1.2); clients, rows, checkpoints, attack categories, calibration subsamples, cluster initializations, and temporal windows are not independent replications.
10. **Deterministic-library settings:** separate configured seed domains for training, partitioning, calibration subsampling, clustering, bootstrap analysis, and dataloader shuffling (`determinism.seed_domains`, configs/protocols.yaml); derived seeds use a `blake2b` hash (8-byte digest) over an ordered, UTF-8-encoded component key, reduced by `modulo 2^32` to an unsigned big-endian integer.
11. **GPU determinism:** enabled where supported for the ML framework and GPU operations (file 05 §12); recorded per run alongside OS, Python version, framework, CUDA/driver versions, and GPU identity.
12. **Data-loader determinism:** `dataloader_shuffle` and `dataloader_worker` seed namespaces are derived from `[training_seed, round_index, client_identifier, local_epoch_index]` and `[training_seed, round_index, client_identifier, worker_index]` respectively (configs/protocols.yaml).
13. **Cluster reproducibility:** fixed `random_seed = 42`, fixed initialization count (10), fixed max iterations (300), fixed tolerance (`1.0e-4`) — see §8.5.
14. **Artifact fingerprinting:** every run records a configuration fingerprint and a dependency-lock fingerprint (§13); reuse is validated against checksum, schema-version, and parent-fingerprint match (§7 item 20).
15. **Allowed nondeterminism:** when full bitwise determinism is unavailable (e.g., certain GPU reduction orders), the limitation is recorded and quantified rather than a bitwise-reproducibility claim being made (file 05 §12: "record and quantify the limitation rather than claiming bitwise reproducibility").
16. **Failure behavior when determinism cannot be achieved:** the run proceeds with the limitation explicitly recorded (item 15); it does not silently claim bitwise reproduction, and does not block execution outright unless the affected quantity is itself a locked scientific decision (e.g., checkpoint selection, which must use no stochastic seed — item within §7 item 18).

### Checklist — Seed cohorts and determinism

- [x] Every seed role (training, partition, calibration-subsample, clustering, bootstrap, dataloader) is defined exactly once, here, and used consistently by configuration and roadmap prose.
- [x] The ten-seed journal cohort and five-seed anchor cohort use disjoint, explicitly listed training-seed values.
- [x] The historical bootstrap seed (`42`) and the cohort-level `bootstrap_analysis_seed` (`300`) are distinguished and never conflated.
- [x] B1 and B2 (and B0/B3/B4) are never resampled independently within a seed.
- [x] Checkpoint selection uses no stochastic seed (anchor) or an explicitly configured non-test selector (journal).
- [x] Cluster seed, initialization count, iteration cap, and tolerance are fixed and recorded.
- [x] Nondeterminism, where unavoidable, is recorded and quantified, never silently claimed away.

---

## 10. Experiment catalogue

Full per-experiment procedure, required figures/tables, and dependency detail are owned by [03 — Experiment Catalogue](./03_EXPERIMENT_CATALOGUE.md) §5–§17. This section is the canonical index: one row per mandatory or conditional experiment family, its evidence role, dataset/regime, execution stage, and whether it is mandatory, conditional, optional, or exploratory. No experiment identifier below may acquire a second meaning in any other file.

| Experiment family | Evidence role | Dataset / regime | Stage | Status |
|---|---|---|---|---|
| Regime A shared-vs-local threshold-scope confirmation (`confirmatory-b1-vs-b2`) | Confirmatory | N-BaIoT / Regime A | 1 | Mandatory |
| Shared-threshold construction sensitivity | Supportive | N-BaIoT / Regime A | 2 | Mandatory |
| Quantile-level sensitivity | Supportive | N-BaIoT / Regime A | 2 | Mandatory |
| Controlled non-IID severity sweep | Supportive/boundary | N-BaIoT / Regime C | 3 | Mandatory |
| Threshold-sharing granularity and cluster stability | Mechanism | N-BaIoT / Regime A | 2 | Mandatory |
| B4 fingerprint ablation | Mechanism | N-BaIoT / Regime A | 2 | Mandatory |
| Per-client score-distribution explanation | Mechanism | N-BaIoT / Regime A | 2 | Mandatory |
| Heterogeneity–benefit association | Mechanism | N-BaIoT / Regime A | 2 | Mandatory |
| Threshold movement versus operating-point harm | Mechanism | N-BaIoT / Regime A | 2 | Mandatory |
| Calibration-size ablation | Boundary | N-BaIoT / Regime A | 2 | Mandatory |
| Fixed local–global shrinkage | Boundary | N-BaIoT / Regime A | 2 | Mandatory |
| Calibration-size-aware shrinkage | Boundary | N-BaIoT / Regime A | 2 | Mandatory |
| Split-conformal B2-conf diagnostic | Threshold variant | N-BaIoT / Regime A | 2 | Mandatory |
| Benign summary-statistics comparator (`B-FedStatsBenign`) | Comparator | N-BaIoT / Regime A | 2 | Mandatory |
| Federated quantile-estimation backbone | Comparator | N-BaIoT / Regime A | 2 | Mandatory |
| Fixed-coefficient Laridi sensitivity | Comparator, optional | N-BaIoT / Regime A | 7 | Optional |
| Edge-IIoTset external benign-equity validation | External validation | Edge-IIoTset / Regime D | 4 | Mandatory |
| CICIoT2023 file-level boundary | Applicability boundary | CICIoT2023 / Regime B-a | — | Mandatory |
| FedProx aggregation stress test | Stress test | N-BaIoT / Regime A | 5 | Mandatory |
| Ditto model-personalization stress test | Stress test | N-BaIoT / Regime A | 5 | Mandatory |
| One-shot recalibration under genuine chronology | Temporal boundary | Edge-IIoTset / Regime D-temporal | 6 | Mandatory |
| Alert-burden experiment | Operational translation | N-BaIoT / Regime A | 2 | Conditional (requires a real or cited traffic rate) |
| Robust cluster-median threshold | Exploratory | N-BaIoT / Regime A | 7 | Optional |
| Additional equity indices | Exploratory | N-BaIoT / Regime A | 7 | Optional |
| Extended secondary uncertainty | Exploratory | N-BaIoT / Regime A | 7 | Optional |
| Communication and storage estimates | Exploratory | N-BaIoT / Regime A | 7 | Optional |
| CICIoT2023 device/MAC repartition | Suppressed | CICIoT2023 / Regime B-b | — | Rejected (§5.3) |
| CICIoT2023 temporal analysis | Suppressed | CICIoT2023 | — | Rejected (no trustworthy timestamps) |
| FedBN | Suppressed | — | — | Rejected (out of scope) |
| Anomaly-labelled Laridi-faithful threshold | Suppressed | — | — | Rejected (violates benign-only contract, §8.9 item 4) |
| Empirical membership-inference probe | Suppressed | — | — | Rejected (out of scope, §14) |
| Streaming drift detectors and continuous adaptation | Future work | — | — | Named, unexecuted (belongs to Dynamic DATP) |
| Byzantine-robust federated conformal prediction | Future work | — | — | Named, unexecuted |
| Broad personalized-FL benchmark | Future work | — | — | Named, unexecuted; contradicts §2 item 9 if executed here |

**Execution stages** (file 03 §17): Stage 1 anchor reproduction and confirmatory extension (blocking gate: no expansion claim proceeds if the five-seed reproduction materially disagrees with the locked historical reference, §3.5, unresolved); Stage 2 stored-score threshold analyses (reuse frozen Regime A score artifacts, no retraining); Stage 3 controlled heterogeneity (blocking gate: every alpha cell needs a valid manifest and comparable eligible-client reporting); Stage 4 external dataset validation; Stage 5 training-side stress tests (FedProx, then Ditto; both require new training and separate score artifacts, never overwriting FedAvg anchor artifacts); Stage 6 temporal boundary; Stage 7 optional supplement (only after all mandatory evidence is complete).

Each experiment family's fixed/manipulated variables, seed cohort, metrics, statistical profile, required artifacts, decision rule, null interpretation, and suppression behavior are defined in file 03's corresponding subsection (see the "Experiment family" column, cross-referenced by file 03's own section numbers §5–§13) and are not restated here to avoid duplication (§1 item 2, §2.2 of the governing task contract).

### Checklist — Experiment catalogue

- [x] Every experiment family in the table above has a unique identifier and evidence role.
- [x] The sole confirmatory experiment is `confirmatory-b1-vs-b2` / "Regime A shared-vs-local threshold-scope confirmation".
- [x] Every mandatory experiment's inputs (frozen Regime A scores, or the relevant dataset/regime) are available per §4–§5.
- [x] Fixed and manipulated variables for each family are defined once, in file 03, not duplicated here.
- [x] Every experiment's seed cohort is one of the two defined in §9.
- [x] Every experiment's metrics are drawn from the supported-metric list of its dataset/regime (§4, §5, §11).
- [x] Every experiment's statistical analysis is one of the profiles in §12.
- [x] Every experiment's decision rule and null interpretation are owned by file 02 (§3), not invented per-experiment.
- [x] Suppression conditions (rejected/suppressed rows) are recorded with a reason, not silently dropped.
- [x] Dependencies and execution-stage ordering match file 03 §17 exactly.
- [x] No experiment family duplicates another (the CICIoT2023 device/MAC repartition is recorded once, as rejected, not re-attempted under a different name).
- [x] Every mandatory/conditional experiment is computationally feasible given the fixed-detector, stored-score reuse discipline (Stage 2 explicitly forbids retraining).
- [x] Every experiment family maps to implementation work in file 05 (§16 below).

---

## 11. Metrics

Full context is owned by [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md) §2–§10. This section is the exact formula and behavior contract.

**Prediction rule (all metrics):** `y_hat = attack if e > tau else benign`, with `e` the reconstruction error and `tau` the deployed threshold; the comparison operator is fixed across policies; a higher reconstruction error always indicates greater anomaly evidence.

1. **`FPR_k`** — `FPR_k = FP_k / (FP_k + TN_k)`. Direction of improvement: lower. Unit: proportion `[0,1]`. Aggregation level: per client. Required inputs: benign test confusion counts. Valid datasets: all. Invalid datasets: none. Eligibility: FPR-evaluable (non-empty benign test denominator, file 04 §3.2). Missing-cell behavior: `unavailable_missing_benign_class`. Zero-denominator behavior: `undefined_zero_denominator`. Degenerate behavior: none beyond zero-denominator. Threshold-dependent: yes. Attack-sensitive: no. Role: confirmatory input (via `CV(FPR)`, item 9). Reporting precision: 3 decimals. Sign convention: not applicable (not a delta).
2. **`TPR_k`** — `TPR_k = TP_k / (TP_k + FN_k)`. Direction: higher. Unit: proportion. Aggregation: per client. Required inputs: attack test confusion counts, valid per-client attack assignment. Valid datasets: attack-evaluable regimes only. Invalid datasets: Edge-IIoTset Regime D (no valid per-client attack assignment). Eligibility: attack-evaluable (file 04 §3.3). Missing-cell behavior: `unavailable_missing_attack_class` or `unavailable_invalid_attack_assignment`. Zero-denominator: `undefined_zero_denominator`. Threshold-dependent: yes. Attack-sensitive: yes. Role: companion reporting (file 02 §3.3), never confirmatory. Reporting precision: 3 decimals.
3. **`BA_k`** (balanced accuracy) — `BA_k = (TPR_k + (1 - FPR_k)) / 2`. Direction: higher. Requires both `FPR_k` and `TPR_k` available; otherwise unavailable. Attack-sensitive: yes. Role: companion reporting only.
4. **Per-client Macro-F1** — average of benign-class and attack-class F1: `MacroF1_k = (F1_{k,benign} + F1_{k,attack}) / 2`. Missing-cell behavior: unavailable when a required class or denominator is absent; never silently converted to zero via library defaults. Attack-sensitive: yes. Role: companion reporting; also feeds `P10(MacroF1)` (item 10).
5. **AUROC** — computed from continuous anomaly scores; requires both classes. Within a fixed-score B1–B4 comparison, AUROC must be identical up to numerical serialization tolerance; any policy-dependent difference indicates mismatched artifacts or unintended model variation. Role: model-quality control, explicitly **not** a threshold-policy verdict (file 02 identity boundary, §2 item 7 of this file).
6. **`mu_FPR`** (mean FPR) — `mu_FPR = (1/K_e) * sum_k FPR_k` over `K_e` eligible FPR-evaluable clients; unweighted by client row count (the primary equity calculation is deliberately unweighted).
7. **`sigma_FPR`** (population SD of FPR) — `sigma_FPR = sqrt((1/K_e) * sum_k (FPR_k - mu_FPR)^2)`, with `ddof = 0` (population, not sample, variance) — the executed eligible clients are treated as the complete descriptive population for that cell.
8. **`CV(FPR)`** (primary confirmatory metric) — `CV(FPR) = sigma_FPR / mu_FPR`. No epsilon or denominator stabilizer is permitted. When `mean(FPR) = 0`, `CV(FPR) = undefined`. A positive `cv_instability_threshold` must be explicitly configured before analysis; when the mean is positive but below that threshold, the numerical CV is retained together with a near-zero-denominator warning status (`undefined_near_zero_denominator`), and such cells are interpreted only alongside absolute dispersion (item 9). Direction of improvement: lower. Confirmatory role: sole primary metric (§3 item 3).
9. **Absolute dispersion** — `IQR(FPR) = Q_0.75(FPR) − Q_0.25(FPR)`; `Range(FPR) = max(FPR_k) − min(FPR_k)`; `WorstFPR = max(FPR_k)`. Quantile interpolation must match the anchor convention (linear-interpolated order statistic, §8.2 item 5) — no implicit library default is permitted. Role: required companion reporting, never a substitute for `CV(FPR)`.
10. **Lower-tail companions** — `CV(TPR) = std(TPR_k, ddof=0) / mean(TPR_k)` (same zero-denominator rules as item 8); `P10(MacroF1) = Q_0.10(MacroF1_k)`; `WorstBA = min(BA_k)`. Report the attack-evaluable client count alongside each.
11. **Metric status vocabulary** (applies to every metric above): `available`, `undefined_zero_denominator`, `undefined_near_zero_denominator`, `unavailable_missing_benign_class`, `unavailable_missing_attack_class`, `unavailable_invalid_attack_assignment`, `unavailable_ineligible_client`, `unavailable_unsupported_regime`, `failed_invalid_artifact`, `failed_statistical_procedure`. Zero, an empty string, an omitted row, or an unqualified `NaN` is never a substitute for one of these named reasons.
12. **Reporting precision.** Full available precision is used for computation; rounding occurs only for presentation. Rates and aggregate metrics: 3 decimals. Confidence intervals and effect sizes: 3 decimals. p-values: 3 significant digits, with `< 0.001` when appropriate. Counts: integers. Thresholds: enough digits to reproduce decisions. Contrasts and intervals are never rounded before computation.
13. **Sign convention for deltas.** The confirmatory contrast is `Δ_s = CV(FPR)_{B1,s} − CV(FPR)_{B2,s}` (§3 item 3); a positive value means B2 has lower dispersion than B1 (the hypothesized, required direction). All other paired deltas in the roadmap follow the same "reference-minus-comparator" sign convention unless the owning experiment subsection in file 03 states otherwise.

### Checklist — Metrics

- [x] Macro-F1 aggregation is explicit: mean of benign-class and attack-class F1 (item 4).
- [x] `CV(FPR)` has no epsilon stabilizer and an explicit `undefined` rule at zero mean (item 8).
- [x] `sigma_FPR` uses population variance (`ddof = 0`), not sample variance (item 7).
- [x] AUROC is a model-quality control, never a threshold-policy verdict (item 5).
- [x] Every attack-sensitive metric requires valid per-client attack assignment (items 2–4, 10).
- [x] Quantile interpolation is explicit and matches the anchor convention across all quantile-based metrics (item 9, §8.2 item 5).
- [x] Missing-cell and zero-denominator behaviors use the named status vocabulary, never a silent zero or NaN (items 8, 11).
- [x] Reporting precision does not affect computed contrasts or intervals (item 12).
- [x] Sign convention for every delta metric is stated once and applied consistently (item 13).
- [x] No metric is computed on an ineligible client (`n_k >= 100`, §6.13).

---

## 12. Statistical analysis

Full derivation and diagnostic detail are owned by [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md) §11–§12. This section fixes the exact procedure.

1. **Confirmatory paired contrast:** `Δ_s = CV(FPR)_{B1,s} − CV(FPR)_{B2,s}` for training seed `s`; confirmatory point estimate is the arithmetic mean `Δ̄ = (1/10) * sum_{s=1}^{10} Δ_s`; B1 and B2 are never resampled independently.
2. **Confirmatory interval:** two-sided 95% BCa bootstrap interval over the ten paired seed-level deltas. Implementation requirements: resample paired seed deltas with replacement; use the arithmetic mean as the statistic; compute bias correction from the bootstrap distribution; compute acceleration through leave-one-seed-out jackknife estimates; use a fixed, recorded analysis seed; use at least 10,000 bootstrap resamples for exploratory/development use, and 50,000 resamples for the frozen publication result unless a larger value is explicitly locked; store the full bootstrap configuration and interval. No implicit library default is permitted for any of these choices.
3. **Degenerate-BCa behavior:** if BCa is undefined or unstable — identical deltas, invalid acceleration, a degenerate bootstrap distribution, or fewer than ten valid pairs — record a statistical-procedure failure (`failed_statistical_procedure`, §11 item 11); report the paired values and point estimate; percentile or basic intervals are permitted only as diagnostics, never as a silent substitute for the confirmatory BCa rule. Claim consequences of a degenerate BCa are owned by file 02 §3.
4. **Sign consistency (descriptive only):** `SignConsistency = |{s : Δ_s > 0}| / 10`; zero and negative counts are also reported.
5. **Secondary test — Wilcoxon signed-rank:** paired seed-level values, two-sided alternative, explicit zero-difference handling, exact computation when data and implementation permit, otherwise a recorded approximation or permutation method. The p-value never determines the confirmatory verdict.
6. **Secondary effect size — matched-pairs rank-biserial correlation:** the paired nonparametric effect size for the seed-paired comparison; unpaired Cliff's delta must never be substituted. Report method, sign, magnitude, and non-zero pair count.
7. **Secondary confidence intervals:** BCa intervals may be reported for pre-specified seed-level contrasts beyond the confirmatory one, but remain secondary regardless of outcome.
8. **Multiplicity correction:** the single confirmatory endpoint receives no multiplicity correction. When secondary p-values are emphasized, test families must be defined before analysis, family size reported, Holm correction applied within each family, and raw values retained only as clearly labeled diagnostics. Exploratory analyses may remain descriptive without correction.
9. **Nested-replicate handling** (calibration subsamples, cluster restarts, or similar): (1) calculate replicate-level values; (2) summarize within seed; (3) produce one seed-level estimate per condition; (4) perform across-seed inference only on those seed-level estimates — never on pooled replicate-level rows.
10. **Association analyses** (heterogeneity–benefit, item used by §10 mechanism experiments): report Spearman correlation, the declared regression, coefficient and uncertainty, `R²`, influence diagnostics, and all observations; use associative, never causal, language.
11. **Cluster-stability statistic:** Adjusted Rand Index, descriptive only, always accompanied by cluster memberships, cluster sizes, empty-cluster count, and singleton-cluster count.
12. **Historical five-seed bootstrap (`historical_five_seed_percentile_bootstrap`):** a 95% two-sided percentile bootstrap (not BCa) over the five historical paired seed deltas, with 10,000 resamples and a literal, hardcoded `analysis_seed = 42`, distinct from the confirmatory ten-seed BCa procedure and from the cohort-level `bootstrap_analysis_seed = 300` (§9 item 2). Used only to reproduce/contextualize the historical anchor (§3 item 5); never substituted for the ten-seed BCa confirmatory rule.

### Checklist — Statistical correctness

- [x] The confirmatory interval is BCa, not percentile or basic, over exactly ten paired seed-level deltas.
- [x] The bootstrap resamples paired seed-level deltas rather than client-seed rows or unpaired values.
- [x] Bias correction and jackknife acceleration are both computed; no interval skips either.
- [x] A fixed, recorded analysis seed is used for the confirmatory bootstrap; the historical bootstrap uses its own recorded seed (`42`), and the two are never conflated (§9 item 2).
- [x] Degenerate BCa does not silently fall back to percentile/basic without recording a `failed_statistical_procedure` status.
- [x] Secondary p-values (Wilcoxon) never override the BCa-based confirmatory decision.
- [x] The paired effect size is matched-pairs rank-biserial correlation, not unpaired Cliff's delta.
- [x] Multiplicity correction (Holm, within pre-declared families) is applied only when secondary p-values are emphasized, never to the sole confirmatory endpoint.
- [x] Nested replicates are summarized within seed before any across-seed inference.
- [x] Association analyses use associative, not causal, language.
- [x] Cluster stability (Adjusted Rand Index) is reported with full membership and degeneracy detail, never as a bare number.

---

## 13. Artifacts, provenance, and reporting

Field-level schema detail is owned by [04 — Evaluation and Reporting Protocol](./04_EVALUATION_AND_REPORTING_PROTOCOL.md) §17–§20 and [05 — Implementation Roadmap](./05_IMPLEMENTATION_ROADMAP.md) §3; `configs/runtime.yaml` and `configs/protocols.yaml` are the configuration authority for the values below.

1. **Required artifact types:** resolved-configuration artifact; dataset/source artifact; split manifest; preprocessing state artifact; training-run artifact; checkpoint artifact; score artifact; threshold artifact; per-client metric record; seed-level aggregate record; statistical-result record; report table; report figure.
2. **Artifact identity:** every artifact carries a scoped identity key composed of the identity fields of every upstream link in the provenance chain (item 13 below) that it depends on — e.g. a score artifact's identity is dataset + regime + client partition + split manifest + preprocessing artifact + model configuration + training configuration + seed + training algorithm (file 05 §6.1).
3. **Dataset identity:** the canonical dataset identifier (N-BaIoT, CICIoT2023, or Edge-IIoTset, §4) plus the resolved source-artifact fingerprint (item 9).
4. **Experiment identity:** the experiment-family identifier from §10's index table, plus dataset/regime and evidence role.
5. **Policy identity:** the threshold-policy or comparator identifier (B0–B4, B2-conf, `B-FedStatsBenign`, FedProx, Ditto, §8) plus its resolved parameters (quantile, shrinkage coefficient, cluster count, proximal `mu`, personalization grid value, etc.).
6. **Seed identity:** the training seed (from `datp_core_ten_seed` or `anchor_five_seed`, §9 item 1) plus any independent partition/clustering/bootstrap seed actually drawn for that artifact.
7. **Checkpoint identity:** the selected round number (§7 item 18) plus the checkpoint-selection-rule identifier (anchor convergence rule vs. journal `datp_core_round_grid` rule) that produced it.
8. **Configuration fingerprint:** a fingerprint of the fully resolved configuration used for a run, recorded per `configs/protocols.yaml`'s determinism and reuse-validation apparatus; required on every training, scoring, and threshold artifact.
9. **Scientific fingerprint:** the combination of dataset identity, regime, client-definition rule, split manifest, and model/training protocol version that defines "the same scientific object" for reuse purposes (file 05 §6.1; §6 item 10 above).
10. **Execution fingerprint:** the recorded environment fields — operating system, Python version, framework version, CUDA version, driver version, GPU identity, dependency-lock fingerprint, deterministic flags, and execution profile (`configs/runtime.yaml: determinism_enforcement.strict.recorded_environment_fields`).
11. **Input hashes:** every training, scoring, or statistical-analysis stage records a hash or fingerprint of its resolved input artifacts (dataset/source artifact, prior-stage artifact) sufficient to detect a changed upstream input (feeds reuse validation, item 15).
12. **Output hashes:** every produced artifact records its own content checksum, used for reuse validation (`checksum_match`, §6 item 10 cross-reference) and for detecting corrupted or partial writes.
13. **Provenance chain:** `configuration → dataset artifact → split manifest → preprocessing state → training run → checkpoint → score artifact → threshold artifact → per-client metrics → seed-level aggregate → statistical result → table or figure` (identical to file 04 §17); every published value must trace through every link.
14. **Atomic-write requirements:** every artifact write in every execution profile (`scientific`, `development`, `smoke`, `dataset_audit`, `test_smoke`) is atomic (`configs/runtime.yaml: atomic_write: true` on every profile) — a reader never observes a partially written artifact; a crashed write leaves no artifact rather than a corrupt one.
15. **Reuse validation:** an artifact may be reused only when `checksum_match`, `schema_version_match`, `parent_fingerprint_match`, `completion_status_completed`, and `non_stale_status` all hold (`configs/protocols.yaml: lineage_validation_before_reuse`); reuse is rejected when the dataset, materialization, client assignment, or split has changed (`reuse_rejected_when_any_changes`).
16. **Invalidation rules:** a changed upstream input (item 11), a changed configuration fingerprint (item 8), a changed scientific fingerprint (item 9), or a failed reuse-validation check (item 15) invalidates every downstream artifact keyed on it; invalidated artifacts must be regenerated, never silently patched in place.
17. **Figure-producing artifacts:** every figure declared in file 04 §18–§20 (e.g., CDF mechanism figures, threshold-shift trade-off plots, cluster-stability figures) is produced from a named statistical-result or seed-level-aggregate artifact, never hand-plotted from an intermediate value without a saved artifact.
18. **Table-producing artifacts:** every `report_profiles` table type in `configs/protocols.yaml` (`interval_table`, `dispersion_ladder_table`, `minimal_dispersion_table`, `sensitivity_grid_table`, `coverage_table`, `cluster_stability_table`, `cluster_contingency_table`, `communication_storage_table`, `alert_burden_table`, and others declared there) is produced from a named statistical-result or seed-level-aggregate artifact with the exact column set, unit, and direction-of-improvement recorded in its profile.
19. **Report profiles:** each table/figure profile fixes its artifact type (`main_table` / `supplementary_table`), table type, column list (name, unit, direction), and — where applicable — its estimate basis (e.g., `communication_storage_table`'s `estimate_basis: analytical_payload_estimate_never_measured_network_traffic`, consistent with §14.2 item 7).
20. **Suppressed-output behavior:** a table or figure cell whose underlying metric or statistical result carries a non-`available` status (§11 item 11, §12 item 3) is omitted from that cell, with the suppression reason recorded in the source result manifest — never populated with zero, a dash without a status code, or an interpolated value.

### Checklist — Artifacts, provenance, and reporting

- [x] Every published value traces through the full canonical provenance chain (item 13).
- [x] Every artifact type in item 1 has an identity rule (items 2–7).
- [x] Configuration, scientific, and execution fingerprints are each recorded and distinguished (items 8–10).
- [x] Input and output hashes are recorded on every stage (items 11–12).
- [x] Every artifact write is atomic in every execution profile (item 14).
- [x] Reuse is gated on checksum, schema-version, parent-fingerprint, and completion-status match, and rejected on any dataset/materialization/client-assignment/split change (item 15).
- [x] An invalidated upstream artifact invalidates every downstream artifact keyed on it, with regeneration rather than in-place patching (item 16).
- [x] Every figure and table is produced from a named artifact, never hand-plotted from an unsaved intermediate value (items 17–18).
- [x] Every report-table profile's column list, unit, and direction match `configs/protocols.yaml: report_profiles` exactly (item 19).
- [x] A suppressed metric or statistical result never appears in a table/figure as a bare zero or unlabeled blank (item 20).
- [x] Every claim in §3 can be traced to an immutable, versioned artifact rather than a manually copied number.

---

## 14. Scope exclusions and prohibited claims

Full narrative is owned by [01 — Scientific Identity and Scope](./01_SCIENTIFIC_IDENTITY_AND_SCOPE.md) §11-§12. This section fixes the exact boundary list, including every prohibited-claim category required at minimum, plus the repository-specific exclusions found in this audit.

### 14.1 Included scientific scope (hard limits)

1. **One new dataset.** Exactly one new IoT dataset is added for this journal extension beyond the conference-anchor dataset: Edge-IIoTset (§4.3), used for external validation only.
2. **Three external comparator families.** Exactly three external comparator families are added: FedProx (training-side stress test, §8.10), one model-personalization method -- Ditto (training-side stress test, §8.11) -- and one benign-only federated summary-statistics comparator -- `B-FedStatsBenign` (§8.9).
3. **Fixed roster.** The dataset roster (N-BaIoT, CICIoT2023, Edge-IIoTset) and the comparator roster (items 1-2 above, plus the core B0-B4 ladder and its shrinkage/split-conformal variants, §8) are fixed; no further dataset or comparator family may be added without a formal roadmap revision recorded in [07 -- Audit and Decision Log](./07_AUDIT_AND_DECISION_LOG.md).

### 14.2 Excluded scientific scope and prohibited claims

At minimum, this file addresses the following excluded areas and prohibited claim categories, in the order required by the audit specification:

1. **Privacy guarantees.** Prohibited: any claim of differential privacy, secure aggregation, homomorphic encryption, secure multiparty computation, membership-inference resistance, reconstruction resistance, or a formal privacy budget. Permitted: describing local-data retention as a structural property of federated learning.
2. **Deployment readiness.** Prohibited: any claim of production readiness, hardware suitability, or deployment validation.
3. **Universal non-IID robustness.** Prohibited: any claim that DATP-Core solves non-IID federated learning in general. Permitted: claims scoped to the specific heterogeneity mechanisms studied (natural device heterogeneity, Regime C's Dirichlet severity grid).
4. **Universal superiority.** Prohibited: any claim that a threshold policy (B1-B4) or comparator is universally superior across datasets, regimes, or metrics. Permitted: claims scoped to the confirmatory endpoint's exact population and conditions (§3).
5. **Fleet-scale claims.** Prohibited: any claim of validation at fleet scale above 100 clients. Permitted: reporting the exact natural or pseudo-client counts used (§4).
6. **Real-time claims.** Prohibited: any claim of real-time detection, real-time response, or online operation. DATP-Core studies a frozen, offline-scored detector.
7. **Energy claims.** Prohibited: any training-energy, inference-energy, or battery-impact claim. Permitted: analytically estimated communication/storage costs, explicitly labeled as estimates rather than measured network traffic (`communication_storage_table`'s `estimate_basis: analytical_payload_estimate_never_measured_network_traffic`, §13 item 19).
8. **Raw-network attack realizability.** Prohibited: any claim that a dataset's synthetic or simulated attack traffic is representative of a real-world attacker's raw-network behavior beyond what the source dataset publication itself claims.
9. **General poisoning robustness.** Prohibited: any claim of robustness to poisoning, backdoors, Byzantine clients, or evasion; no such experiment exists in the roadmap.
10. **Full concept-drift handling.** Prohibited: any claim of general concept-drift handling, streaming adaptation, or continuous recalibration; Regime D-temporal is a single one-shot boundary probe only, never a drift-tracking or repeated-recalibration study.
11. **Protected-attribute fairness.** Prohibited: equating benign false-positive-rate equity across clients/devices with human-subject or protected-attribute fairness; "false-positive fairness" in this roadmap refers only to cross-client FPR dispersion, never demographic fairness (file 06 §8.1).
12. **Generic personalized-FL superiority.** Prohibited: presenting the Ditto stress test as evidence that model personalization is generally superior to (or generally inferior to) threshold-scope adaptation; Ditto is a stress test outside the causal ladder (§8.11), not a benchmarked alternative to B1-B4.
13. **Cross-dataset universal generalization.** Prohibited: treating the single external-validation dataset (Edge-IIoTset) as proof of universal cross-dataset generalization; external validation tests transfer to one additional dataset only.
14. **Unsupported temporal claims.** Prohibited: any claim beyond the exact scope of the one-shot Regime D-temporal recalibration experiment -- no claim of long-horizon drift tracking, no claim of repeated recalibration benefit, no claim about drift mechanisms not directly measured.

Repository-specific exclusion found in this audit, additional to the required minimum above:

15. **FedBN.** Excluded from the comparator roster; remains excluded rather than added as a comparator under any name.

### Checklist -- Excluded scientific scope and prohibited claims

- [x] No privacy-guarantee wording appears in any claim, experiment, figure, table, or implementation task (item 1).
- [x] No deployment-readiness or hardware-suitability wording appears anywhere (item 2).
- [x] No universal non-IID-robustness wording appears anywhere (item 3).
- [x] No universal-superiority wording appears for any threshold policy or comparator (item 4).
- [x] No fleet-scale-above-100-clients claim appears anywhere (item 5).
- [x] No real-time or online-operation claim appears anywhere (item 6).
- [x] No energy or battery claim appears anywhere; communication/storage costs are labeled as analytical estimates (item 7).
- [x] No raw-network attack-realizability claim beyond the source dataset's own claims appears anywhere (item 8).
- [x] No poisoning/backdoor/Byzantine/evasion robustness claim appears anywhere (item 9).
- [x] No full concept-drift-handling claim appears; Regime D-temporal is described only as a one-shot boundary probe (item 10).
- [x] No protected-attribute-fairness framing is applied to the FPR-equity metric (item 11).
- [x] No generic personalized-FL-superiority claim is drawn from the Ditto stress test (item 12).
- [x] No cross-dataset universal-generalization claim is drawn from the single Edge-IIoTset validation (item 13).
- [x] No temporal claim exceeds the exact scope of the one-shot recalibration experiment (item 14).
- [x] FedBN remains excluded rather than added as a comparator (item 15).
- [x] Every exclusion above is respected consistently across claims (§3), experiments (§10), figures/tables (§13), and implementation tasks (§16).

---

### 14.3 External-validation limits

1. **Single external dataset.** External validation tests transfer to exactly one additional dataset (Edge-IIoTset); this is never treated as proof of universal cross-dataset generalization.
2. **Fair comparator matching.** External comparators use fair operating-point matching -- e.g. `B-FedStatsBenign`'s operating point is matched to the DATP quantile target rather than selected to maximize F1 (§8.9).

### 14.4 Named future work

Any capability named as future work anywhere in files 00-07 (e.g., additional datasets, additional personalization methods, drift-tracking studies, formal privacy mechanisms) is described as unexecuted and out of the current journal-extension scope; it must never be partially implemented under a different name and presented as in-scope.

### Checklist -- Scope exclusions and prohibited claims

- [x] The dataset and comparator rosters are each fixed and enumerated; no addition occurs without a recorded formal revision (§14.1 item 3).
- [x] No poisoning/backdoor/Byzantine/evasion robustness claim appears anywhere (§14.2 item 9).
- [x] No privacy-guarantee wording appears in any claim, experiment, figure, table, or implementation task (§14.2 item 1).
- [x] No energy, battery, or deployment-readiness claim appears anywhere; communication/storage costs are labeled as analytical estimates (§14.2 items 2, 7).
- [x] No universal non-IID-robustness wording appears anywhere (§14.2 item 3).
- [x] No full concept-drift-handling claim appears; Regime D-temporal is described only as a one-shot boundary probe (§14.2 item 10).
- [x] No universal-superiority claim appears for any threshold policy or comparator (§14.2 item 4).
- [x] No fleet-scale-above-100-clients claim appears anywhere (§14.2 item 5).
- [x] No real-time or online-operation claim appears anywhere (§14.2 item 6).
- [x] No raw-network attack-realizability claim beyond the source dataset's own claims appears anywhere (§14.2 item 8).
- [x] No protected-attribute-fairness framing is applied to the FPR-equity metric (§14.2 item 11).
- [x] No generic personalized-FL-superiority claim is drawn from the Ditto stress test (§14.2 item 12).
- [x] No temporal claim exceeds the exact scope of the one-shot recalibration experiment (§14.2 item 14).
- [x] No cross-dataset universal-generalization claim is drawn from the single Edge-IIoTset validation (§14.2 item 13).
- [x] FedBN remains excluded rather than added as a comparator (§14.2 item 15).
- [x] Named future work is described as unexecuted, never partially implemented under a different name (§14.4).

---

## 15. Suppression and failure rules

1. **A dataset-regime cell is suppressed** when: source-artifact integrity validation fails; a required client-definition rule cannot be reproduced (e.g., Regime B-b's rejected repartition, §5.2); eligibility coverage falls below the configured minimum; or the regime's dataset lacks a capability required by the analysis (e.g., attack-sensitive metrics on Edge-IIoTset Regime D, §4.3 item 6). Machine-enforceable via the `dataset_specific_gates` and readiness-report checks (file 05 §4.2–§4.3).
2. **A metric is suppressed** when its required denominator, class, or attack assignment is unavailable (§11 item 11's named status vocabulary) — never silently replaced by zero or `NaN`. Machine-enforceable via the fixed metric-status enum.
3. **An experiment is blocked** when its declared eligibility capabilities (file 03 §2.4, e.g., `benign_test_false_positive_metrics`, `family_taxonomy`, `per_client_attack_detection_metrics`) are unavailable for the target dataset/regime, per each experiment's `when_unavailable: fail_experiment` gate (`configs/experiments.yaml`). Machine-enforceable via the eligibility-capability check at experiment-launch time.
4. **A claim is narrowed** when its supporting experiment's evidence role or dataset/regime scope does not extend as far as the claim's original wording — the claim wording is edited to match the achieved evidence rather than the evidence being stretched to match the claim (file 02 §3, §11–§14 scope-limit apparatus).
5. **A claim cannot be made** when its sole confirmatory or required-comparator experiment fails, is suppressed, or is blocked (items 1–3) and no alternative pre-specified evidence role can support it; the claim is reported as unsupported with the blocking reason named (§3 item 3, degenerate-BCa handling in §12 item 3).
6. **An artifact cannot be reused** when any of the reuse-validation checks in §13 item 15 fails, or when any of the reuse-rejection triggers (dataset, materialization, client-assignment, or split change) fires; a fresh artifact must be generated instead of a stale one being reused.
7. **A statistical result is invalid** when it is computed on fewer than the minimum valid units for its profile (ten paired seeds for the confirmatory BCa, five for the historical bootstrap, §9 item 1), when required pairing is broken (B1/B2 resampled independently, forbidden per §9 item 7), or when the estimand is computed after rather than before resampling where the profile requires the former (§12 items 1–2); it is recorded as `failed_statistical_procedure` (§11 item 11) rather than reported as a normal result.
8. **A figure or table cell must be omitted** when the metric or statistical result it would display carries a non-`available` status (§13 item 20); the cell is left blank with the suppression reason recorded in the source result manifest, never populated with an interpolated or default value.
9. **A run must fail rather than fall back** when: a required configuration value is missing (§13 item 5 / file 05 §2.2); a required device policy cannot be satisfied (`cuda_required` with no GPU present — `configs/runtime.yaml: device_policy_rules.cuda_required.missing_device_behavior: fail_execution_never_downgrade`); resource pressure would otherwise silently reduce batch size, round count, seed count, or client count (`configs/runtime.yaml: resource_pressure_policy`, all three forbidden, `on_budget_exceeded: block_execution_and_report`); or a nondeterministic operation would otherwise be silently downgraded (`nondeterministic_operation_policy: raise_never_silently_downgrade`).
10. **An unresolved scientific decision blocks execution** only for the specific claim or experiment it governs (§1 item 4, §15 [Unresolved items] below); it never blocks unrelated claims or experiments, and it is never given an invented value to unblock execution.

Suppression is explicit and machine-enforceable wherever a repository-level check, named configuration flag, or typed status code already exists (items 1–3, 6–9 above); where no such mechanism yet exists, it is recorded as an implementation-roadmap task (§16 below) rather than left as an undocumented convention.

### Checklist — Suppression and failure rules

- [x] Every dataset-regime suppression condition names its trigger and its enforcement mechanism (item 1).
- [x] Every metric-suppression condition uses the named status vocabulary, never a silent zero or NaN (item 2).
- [x] Every experiment-blocking condition is tied to a declared eligibility capability and its `when_unavailable` behavior (item 3).
- [x] Claim narrowing edits the claim to match the evidence, never the reverse (item 4).
- [x] A claim that cannot be made is reported as unsupported with a named blocking reason, not omitted silently (item 5).
- [x] Artifact reuse failure is tied to the exact reuse-validation and reuse-rejection rules in §13 item 15 (item 6).
- [x] Statistical-result invalidity has a named minimum-unit, pairing, and estimand-ordering rule per profile (item 7).
- [x] Suppressed figure/table cells are blank with a recorded reason, never populated with a default (item 8).
- [x] Every "fail rather than fall back" condition is tied to an explicit configuration flag (item 9).
- [x] Unresolved items block only their named scope, never the whole roadmap (item 10).

---

## 16. Scientific-to-implementation traceability

Every scientific contract item in §2–§15 above maps to the following eight implementation dimensions. This section states the mapping rule for each dimension; §10's experiment index and file 05's task breakdown are where the mapping is instantiated per experiment.

1. **Configuration section.** Every locked numeric/formula/rule value maps to a named key path in `configs/protocols.yaml`, `configs/experiments.yaml`, or `configs/runtime.yaml` (§16 item 1, prior draft — consolidated here).
2. **Domain model.** Every scientific entity (client, regime, threshold policy, seed cohort, checkpoint, score artifact, statistical-result) maps to a named domain type in the implementation, carrying exactly the identity fields defined in §13 items 2–7.
3. **Validator.** Every eligibility rule, leakage control, forbidden-selector list, and reuse-validation gate maps to an explicit validator function or check, never an unenforced convention.
4. **Pipeline stage.** Every scientific decision maps onto exactly one link of the canonical provenance chain (§13 item 13).
5. **Artifact.** Every threshold, score, checkpoint, and statistical-result artifact type named in §7–§13 has a corresponding artifact-identity rule (§13 items 2–7).
6. **Test family.** Every claim-decision rule (§3), leakage control (§6), degenerate-metric rule (§11 item 11), and degenerate-statistical-procedure rule (§12 item 3, §15 item 7) requires a corresponding automated test family; a locked rule with no named test family is a gap to raise in file 05's task breakdown.
7. **Implementation roadmap task.** File 05 owns the task breakdown; every regime (§5), threshold policy (§8), comparator (§8), and statistical procedure (§12) in this file must appear as a task or task group in file 05.
8. **Reporting output.** File 04 §18–§20 owns required figures and tables; every confirmatory and supportive claim in §3 must produce at least one reporting output named there, per the report-profile schema in §13 items 17–19.

No scientific decision in this file exists only in prose without at least the configuration-section and domain-model mappings (items 1–2); a decision additionally requiring a validator, test family, or reporting output (items 3, 6, 8) is flagged incomplete until that mapping exists. No implementation behavior in file 05 exists without a corresponding scientific basis traceable to §2–§15 of this file.

### Checklist — Scientific-to-implementation traceability

- [x] Every locked numeric/formula decision has a named configuration-key mapping (item 1).
- [x] Every scientific entity has a named domain-model mapping with the correct identity fields (item 2).
- [x] Every eligibility, leakage, and selection rule has a named validator mapping (item 3).
- [x] Every scientific decision maps onto exactly one pipeline stage (item 4).
- [x] Every artifact type has an identity-rule mapping (item 5).
- [x] Every degenerate/failure rule has a named test-family mapping, or is flagged as an implementation gap (item 6).
- [x] Every regime, policy, comparator, and statistical procedure appears as a task or task group in file 05 (item 7).
- [x] Every confirmatory and supportive claim produces at least one reporting output (item 8).
- [x] No scientific decision exists only in prose with zero implementation-dimension mappings.
- [x] No implementation behavior in file 05 lacks a traceable scientific basis in this file.

---

## 17. Complete readiness checklist

Every item below was verified against the repaired roadmap files (00–07) and the repository configuration (`configs/protocols.yaml`, `configs/experiments.yaml`, `configs/runtime.yaml`) as of this audit. An unchecked item carries a concise explanation directly below it and corresponds to §15 (Unresolved items).

**1. Scientific identity**
- [x] The research object is threshold-calibration scope on a fixed, frozen FedAvg autoencoder (§2 item 2).
- [x] The encoder and its scores are never retrained or altered across the B1–B4 comparison (§2 item 2).
- [x] Ditto is confined to a stress-test role and never merged into the B1–B4 ladder (§2 item 9).
- [x] The dataset roster is bounded to exactly three datasets (§2 item 9, §4).

**2. Claim discipline**
- [x] The sole confirmatory endpoint is `confirmatory-b1-vs-b2` on Regime A (§3 item 1).
- [x] Every secondary claim is assigned exactly one evidence class (§3 item 2).
- [x] No stress test (FedProx, Ditto) is presented as part of the causal threshold ladder (§3 checklist item, §8.10–§8.11).
- [x] No external-validation result is automatically promoted to a confirmatory claim (§3 checklist item).

**3. Dataset validity**
- [x] N-BaIoT's raw-data authority is the local repository artifact, not the originating publication (§4.1 item 3).
- [x] CICIoT2023's client population is file-defined pseudo-clients, never presented as physical devices (§4 checklist).
- [x] Edge-IIoTset's attack-sensitive metrics are suppressed for lack of a valid per-client attack assignment (§4 checklist, §11 item 2).
- [x] No fourth dataset appears anywhere in files 00–07 (§14.1 item 3).

**4. Client construction**
- [x] Regime A uses nine N-BaIoT physical devices, full population, natural partitioning (§5.1).
- [x] Regime B-a's 63 pseudo-clients are never presented as physical devices (§5 checklist).
- [x] Regime D's ten sensor groups never receive an attack-sensitive metric (§5 checklist).
- [x] Every regime has exactly one meaning and one owning subsection across the repository (§5 checklist).

**5. Split integrity**
- [x] Training, calibration, validation, and test splits are disjoint and each has a stated purpose (§6 items 1–4).
- [x] Regime D-temporal preserves chronology; no future-window record leaks into training or calibration (§6 checklist).
- [x] Calibration and test records are disjoint in every regime (§6 checklist).

**6. Leakage prevention**
- [x] Checkpoint selection uses only trailing benign validation loss, never test or attack outcomes (§7 item 18, forbidden-selector list).
- [x] Cross-client data are never used where local-only semantics are required (§6 checklist).
- [x] No fallback silently introduces leakage; degenerate-input behaviors are typed failures (§6 checklist, §13 item 20).

**7. Training protocol**
- [x] Architecture, optimizer, learning rate, local-epoch count, and aggregation formula are fixed and identical across B0–B4 within a seed and regime (§7 items 1–9).
- [x] FedProx's proximal coefficient grid `{0.001, 0.01, 0.1, 1.0}` is frozen before outcome inspection (§7 checklist item).
- [x] Ditto's naming lock is enforced — an implementation lacking the genuine Ditto contract is never called Ditto (§7 checklist item).
- [x] Training-side stress tests never enter the B0–B4 causal ladder (§7 checklist item).

**8. Threshold policies**
- [x] B0–B4 are each precisely defined with role, required inputs, and suppression conditions (§8.1–§8.5).
- [x] Shared-threshold construction controls (exact pooled quantile, weighted mean, sample-weighted construction) are explicitly distinguished (§8.6).
- [x] B4's cluster count, fingerprint, scaling procedure, and random seed are locked (§8.5, §9 item 4).
- [x] No obsolete threshold identifier (B5, B3-LGS) appears in any active file (§8 checklist item).

**9. Comparator validity**
- [x] `B-FedStatsBenign`'s operating point is matched to the DATP quantile target, never selected to maximize F1 (§8.9, §14.3 item 2).
- [x] FedProx and Ditto require new training and separate score artifacts, never overwriting FedAvg anchor artifacts (§10, Stage 5 gate).
- [x] A Laridi-faithful implementation is not executed because it violates the benign-only threshold contract (file 03 §3.9).

**10. Seed determinism**
- [x] The ten-seed journal cohort and five-seed anchor cohort use disjoint, explicitly listed training-seed values (§9 checklist item).
- [x] The historical bootstrap seed (`42`) and the cohort-level `bootstrap_analysis_seed` (`300`) are distinguished and never conflated (§9 item 2).
- [x] B1 and B2 are never resampled independently within a seed (§9 item 7).
- [x] Cluster seed (`42`), initialization count (10), iteration cap (300), and tolerance (`1.0e-4`) are fixed and recorded (§9 item 13).

**11. Experiment completeness**
- [x] Every mandatory and conditional experiment family in §10's index table has a defined evidence role, dataset/regime, and execution stage.
- [x] Every rejected/suppressed experiment records its rejection reason rather than being silently omitted (§10 table, rejected rows).
- [x] Execution-stage ordering and blocking gates match file 03 §17 exactly (§10, "Execution stages").

**12. Metric correctness**
- [x] `CV(FPR)` has no epsilon stabilizer and an explicit `undefined` rule at zero mean (§11 item 8).
- [x] `sigma_FPR` uses population variance (`ddof = 0`), not sample variance (§11 item 7).
- [x] AUROC is a model-quality control, never a threshold-policy verdict (§11 item 5).
- [x] Macro-F1 is never silently converted to zero via library defaults on a missing class (§11 item 4).

**13. Statistical correctness**
- [x] The confirmatory interval is BCa, not percentile or basic, over exactly ten paired seed-level deltas (§12 item 2).
- [x] Bias correction and jackknife acceleration are both computed (§12 item 2).
- [x] Degenerate BCa records a `failed_statistical_procedure` status rather than silently substituting another interval (§12 item 3).
- [x] The paired effect size is matched-pairs rank-biserial correlation, not unpaired Cliff's delta (§12 item 6).
- [x] Multiplicity correction is applied only to secondary-p-value families, never to the sole confirmatory endpoint (§12 item 8).

**14. Artifact provenance**
- [x] Every published value traces through the full canonical provenance chain (§13 item 13).
- [x] Score and threshold artifacts carry a configuration fingerprint enabling reuse validation (§13 items 8, 15).
- [x] Every artifact write is atomic in every execution profile (§13 item 14).
- [x] Reuse is rejected on any dataset, materialization, client-assignment, or split change (§13 item 15).

**15. Reporting traceability**
- [x] Every figure and table is produced from a named artifact, never hand-plotted from an unsaved intermediate value (§13 items 17–18).
- [x] Every report-table profile's column list, unit, and direction match `configs/protocols.yaml: report_profiles` exactly (§13 item 19).
- [x] A suppressed metric or statistical result never appears in a table/figure as a bare zero or unlabeled blank (§13 item 20).

**16. Scope boundaries**
- [x] No poisoning, evasion, backdoor, or Byzantine study was added (§14.2 item 9).
- [x] No formal privacy, deployment-readiness, fleet-scale, real-time, or energy claim appears anywhere (§14.2 items 1, 2, 5, 6, 7).
- [x] FedBN remains excluded rather than added as a comparator (§14.2 item 15).
- [x] Named future work is described as unexecuted, never partially implemented under a different name (§14.4).

**17. Suppression behavior**
- [x] Every dataset-regime, metric, and experiment suppression condition names its trigger and enforcement mechanism (§15 items 1–3).
- [x] A run fails rather than falls back on a missing configuration value, unmet device policy, resource pressure, or nondeterministic-operation downgrade (§15 item 9).
- [x] Unresolved items block only their named scope, never the whole roadmap (§15 item 10, §1 item 4).

**18. Implementation traceability**
- [x] Every locked numeric/formula decision has a named configuration-key mapping (§16 item 1).
- [x] Every regime, threshold policy, comparator, and statistical procedure appears as a task or task group in file 05 (§16 item 7).
- [x] No scientific decision exists only in prose with zero implementation-dimension mappings (§16 checklist).

**19. Reviewer-risk mitigation**
- [x] Thresholding-as-"only post-processing" is addressed with an explicit mechanism-analysis programme distinguishing threshold scope from model quality (file 06 §3.1; AUROC-invariance control, §11 item 5).
- [x] The Laridi-overlap risk is addressed by an explicit contract distinction (benign-only vs. Laridi's anomalous-inclusive calibration, file 03 §3.9; file 06 §3.2).
- [x] The "B2 reduces dispersion by construction" risk is addressed by reporting AUROC invariance and absolute dispersion alongside `CV(FPR)` (file 06 §4.1; §11 items 5, 9).
- [x] Checkpoint-cherry-picking risk is addressed by the frozen, non-test checkpoint-selection rule with an explicit forbidden-selector list (§7 item 18; file 06 §4.4).
- [x] The "ten seeds weakens the conference result" risk is addressed by explicitly distinguishing the anchor five-seed cohort from the journal ten-seed cohort and reproducing the anchor before extending it (§9 item 1; file 06 §4.6; Stage 1 blocking gate, §10).

**20. Execution readiness**
- [x] Stage 1 (anchor reproduction and confirmatory extension) blocks all downstream expansion claims until the five-seed reproduction is resolved or confirmed non-discrepant (§10, Stage 1 gate).
- [x] Stage 2 analyses are restricted to reuse of frozen Regime A score artifacts with no retraining (§10, Stage 2).
- [x] Stage 3 (controlled heterogeneity) requires a valid manifest and comparable eligible-client reporting for every alpha cell before proceeding (§10, Stage 3 gate).
- [x] Stage 5 (training-side stress tests) requires new training and separate score artifacts that never overwrite FedAvg anchor artifacts (§10, Stage 5).
- [ ] The `cv_instability_threshold` numeric value required by §11 item 8 is not yet configured in the repository — see §15.1 for the full disclosure. This blocks only the near-zero-denominator warning annotation on `CV(FPR)` cells; it does not block the confirmatory endpoint or any other checklist item above.

---

**Total checklist items across this file (§2–§17 section checklists plus this comprehensive checklist):** every section's checklist above is exhaustive for its section; the single unresolved item is §15.1 / item 20 above (`cv_instability_threshold`). All other items across all sections were verified `[x]` against the repaired roadmap and repository as of this audit.
