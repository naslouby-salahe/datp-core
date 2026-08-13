# DATP-Core Journal Extension — Audit & Implementation Matrix

> **Purpose:** executable audit/implementation contract derived from the authoritative DATP-Core roadmap. This file is deliberately exhaustive, but it is **not a second scientific authority**. If any wording here appears to conflict with the roadmap snapshot below, the roadmap wins and the matrix must be regenerated.

## 0. Matrix lock, authority, and usage

- **Authoritative roadmap snapshot:** `Journal_Extension_Master_Roadmap.md`
- **Authoritative roadmap SHA-256:** `b3f43353081eae89862d42315da7cc1cb13a7ff9d9a9d17d981c3b91dc84c83c`
- **Roadmap size:** `335741` bytes; `6484` lines
- **Matrix generation principle:** define once in the roadmap; map, verify, and implement here.
- **Repository policy:** no backwards compatibility. Obsolete APIs, aliases, wrappers, experiment identities, artifact layouts, and tests must be replaced at their callers and removed unless needed solely to ingest immutable historical provenance.
- **No rescue rule:** supportive/mechanism/external/stress/optional evidence cannot replace or rescue the sole confirmatory endpoint.

### 0.0 Unambiguous interpretation and closure rules

These rules govern **how an implementation agent must read this matrix**. They remove any freedom to treat coverage anchors, inherited contracts, optional evidence, applicability phrases, or blank audit cells as implementation discretion.

1. **Authority is content-addressed.** The roadmap bytes identified by the locked SHA-256 are authoritative. Source line numbers and section names are navigation aids inside that exact snapshot; they do not supersede the hash.
2. **Coverage anchors are not executable substitutes.** Section 1 contract-title rows and Section 15 source-anchor rows prove structural coverage only. They are never sufficient evidence of implementation. Executable closure comes from atomic requirements, formula/literal obligations, experiment cards, metric/statistical contracts, the prose-sentinel register, the table-row sentinel register, and Gates A–R.
3. **AND is the default.** Multiple bullets, rows, outputs, metrics, grids, seeds, or gates listed under one mandatory contract are cumulative requirements unless the roadmap explicitly uses an alternative such as `OR`, `one of`, `optional`, or an explicit typed-unavailability rule. An agent may not choose the easiest subset.
4. **Inheritance is mandatory.** An experiment card describes its delta. Every applicable Part I and Part III contract still applies unless that experiment has an explicit, prospectively declared protocol deviation. Silence is inheritance, not permission to diverge.
5. **No silent defaults.** A repository default, library default, historical value, test fixture, or convenience constant is not a scientific parameter unless the roadmap authorizes it. If a required value is absent from implementation, the result is `MISSING`/`FAIL`, not an inferred default.
6. **Feasibility/applicability is evidence, not discretion.** Phrases such as `where feasible`, `when defined`, `where applicable`, and `subject to support` may be resolved only by roadmap-defined support/availability conditions. Outcome quality, compute convenience, or implementation difficulty are not feasibility criteria. The planner must emit an applicability record for every candidate coordinate with exactly one of `REQUIRED`, `NOT_APPLICABLE`, or `UNAVAILABLE_AS_SPECIFIED`, together with the roadmap requirement ID and a reason code. Silently dropping a coordinate is `FAIL`.
   - If such a phrase appears on a mandatory coordinate but the roadmap supplies no explicit scientific feasibility predicate, the nominal coordinate remains `REQUIRED`. Inability to execute it is an implementation/input `MISSING`/`FAIL` requiring remediation or an explicit prospective roadmap amendment; auditor judgment must not convert it to `NOT_APPLICABLE` or `UNAVAILABLE_AS_SPECIFIED`.
   - When the roadmap explicitly authorizes a computational fallback (for example an exact-preferred statistical test with a documented fallback), feasibility is determined only by the explicitly requested exact mode and the locked statistics-library version accepting the actual paired input. Persist the library/version, requested mode, executed mode, and fallback reason. Outcome magnitude, sign, or p-value must never determine feasibility.
7. **Optional means non-blocking, not free-form.** An optional experiment does not block the confirmatory/publication path when omitted. If executed or reported, however, its implementation, provenance, metric semantics, and claim tier must satisfy the roadmap exactly and it may never rescue a failed mandatory/confirmatory result.
8. **`—` is not a scientific status.** In existing matrix cells it means only `SCIENTIFIC_OUTCOME_NOT_YET_ADJUDICATED`. Once a row is audited, `—` must be replaced by exactly one Part IV scientific status: `PASS`, `FAIL`, `NOT_APPLICABLE`, or `UNAVAILABLE_AS_SPECIFIED`.
9. **`NOT_AUDITED` is implementation workflow state only.** It must never be exported as scientific evidence, manuscript status, or a substitute for typed unavailability.
10. **Claim blocking is derived, never guessed.** `DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS` means the section-level coverage row inherits the strongest claim-blocking consequence of its executable child requirements. It does not authorize the auditor to decide claim importance ad hoc.
11. **Tests alone cannot close production behavior.** A required production contract needs a reachable runtime caller and retained verification evidence. `TEST_ONLY`, `UNREACHABLE`, `DEAD`, or `CONFLICTING_IMPLEMENTATIONS` cannot be marked `PASS` for required production behavior. Reporting-only or static-contract rows must instead prove the roadmap-authorized non-runtime ownership.
12. **One scientific contract, one active semantic owner.** Shared utilities are allowed, but two active runtime paths may not implement different semantics for the same scientific identity. Any such split is `CONFLICTING_IMPLEMENTATIONS` until callers are consolidated.
13. **No row may be silently skipped.** Before publication readiness, every executable row must have an actual implementation or a roadmap-valid non-implementation status, a runtime/static owner, verification evidence, and a scientific outcome.

### 0.1 Scientific audit status vocabulary — locked from Part IV §1

| Status | Meaning |
|---|---|
| `PASS` | implementation/evidence satisfies the roadmap contract |
| `FAIL` | contract violation or missing required implementation/evidence |
| `NOT_APPLICABLE` | requirement legitimately does not apply to this coordinate |
| `UNAVAILABLE_AS_SPECIFIED` | Parts I–III explicitly declare the evidence unavailable; never use for missing implementation |

### 0.2 Repository implementation disposition — matrix-only diagnostic

| Disposition | Meaning |
|---|---|
| `NOT_AUDITED` | not yet mapped to repository |
| `EXACT` | one reachable implementation matches the roadmap |
| `PARTIAL` | some required semantics/outputs exist but not all |
| `INCORRECT` | implementation exists but violates the roadmap |
| `MISSING` | no implementation |
| `STALE` | obsolete implementation retained |
| `DUPLICATED` | multiple competing implementations of one scientific contract |
| `DEAD` | implementation is not reachable and not intentionally retained |
| `TEST_ONLY` | implemented/covered only in tests, not production execution |
| `UNREACHABLE` | implementation exists but intended pipeline does not call it |
| `WRONG_OWNER` | responsibility implemented in the wrong architectural layer |
| `CONFLICTING_IMPLEMENTATIONS` | different runtime paths produce different semantics |

### 0.3 Remediation priority

| Priority | Blocks | Examples |
|---|---|---|
| `P0` | scientific validity / claims | leakage, fixed-score identity, eligibility, terminal detector, confirmatory pairing, invalid inference |
| `P1` | protocol correctness | wrong formula, wrong grid, wrong estimator semantics, wrong metric population |
| `P2` | evidence completeness | missing mandatory diagnostics, tables, figures, negative-result outputs |
| `P3` | reproducibility/publication | provenance, hashes, manifests, reconstruction, environment metadata |
| `P4` | structural quality | stale names, duplication, dead code, package ownership, unnecessary abstractions |

### 0.4 Minimum execution coordinate

Every materialized scientific result must bind all of the following fields; hashes supplement but never replace semantic identity:

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

### 0.5 Required repository-audit columns

| Field | Required use |
|---|---|
| `Requirement ID` | stable matrix key |
| `Roadmap owner` | authoritative source section/line |
| `Requirement` | atomic scientific/engineering rule |
| `Expected owner` | intended package/module responsibility |
| `Actual implementation` | file::symbol after repository mapping |
| `Runtime caller` | pipeline/experiment path that exercises it |
| `Tests` | unit/property/integration/negative tests |
| `Implementation disposition` | matrix diagnostic status |
| `Scientific audit outcome` | PASS/FAIL/NOT_APPLICABLE/UNAVAILABLE_AS_SPECIFIED |
| `Claim blocking` | yes/no and affected claim |
| `Priority` | P0–P4 |
| `Required remediation` | precise no-backcompat fix |
| `Verification evidence` | test/artifact/command/result proving closure |

### 0.5A Deterministic ownership routing

The `Expected owner` field is a responsibility boundary, not permission to scatter one contract across arbitrary modules. During repository mapping, choose the **single semantic owner** according to this routing table; helpers may be elsewhere, but the owner is responsible for the contract and tests.

| Contract type | Semantic owner responsibility | Required runtime/static proof |
|---|---|---|
| identity, enums, immutable coordinates, provenance value objects | domain/protocol contracts | typed identity construction + validation |
| dataset parsing, canonical rows, populations, split-capability facts | dataset capability | dataset materialization/population caller + integrity tests |
| fitted transforms and transform-state identity | preprocessing capability | fit/transform pipeline caller + serialization/equivalence tests |
| centralized/federated/personalized detector training | learning/training capability | training pipeline caller + terminal-detector artifact |
| immutable reconstruction-score generation | scoring capability/pipeline score stage | one canonical scorer + fixed-score provenance tests |
| benign calibration construction, eligibility, support accounting | calibration capability | calibration-stage caller + row-disjointness/support tests |
| threshold estimators/policies/sketches/shrinkage/conformal rules | thresholding capability | threshold-stage caller + formula/grid/property tests |
| per-client and aggregate metric semantics | evaluation capability | evaluation-stage caller + edge/undefined-case tests |
| bootstrap/tests/associations/mechanism/temporal inference | analysis capability | analysis-stage caller + statistical-unit/degeneracy tests |
| experiment coordinate expansion and execution order | planner/pipeline | declarative coordinate plan + completeness proof |
| figures, tables, claim-tier rendering, release exports | reporting/publication | reconstructable source tables + report validation |
| determinism, compute, environment, artifact integrity | runtime/provenance validation | environment/seed/hash manifests + validation gates |

A single experiment invokes multiple capabilities, but the experiment card's integration row does not replace child semantic ownership. Each child requirement is mapped separately, and cross-package integration is proven by `Runtime caller` plus artifact lineage.

## 0.6 Central scientific invariants — explicit drift sentinels

These rows are intentionally duplicated as **audit sentinels** because a paragraph-level omission here would be scientifically dangerous even if downstream experiment rows were otherwise complete. They do not override the authoritative roadmap owner.

| Sentinel ID | Locked invariant | Roadmap owner | Audit consequence |
|---|---|---|---|
| `DRIFT-SENTINEL-001` | Only one endpoint is confirmatory: `NBAIOT_NATURAL_DEVICES`, `SHARED_THRESHOLD` vs `LOCAL_THRESHOLD`, `CV(FPR)`, exactly ten paired training seeds, locked BCa decision rule. | Part I §8.1; Part II §5.1; Part III §11 | Any competing confirmatory endpoint or tier promotion is `FAIL`. |
| `DRIFT-SENTINEL-002` | The core threshold-scope intervention changes threshold-calibration scope only; detector, preprocessing, population, calibration/test score identity, labels, eligibility, q target, and metric semantics are fixed within the comparison coordinate. | Part I §§2.1–2.4 | Policy-specific retraining/rescoring/refitting or test-population changes are causal-isolation `FAIL`. |
| `DRIFT-SENTINEL-003` | Every DATP-compatible threshold uses benign calibration evidence only; calibration and evaluation are disjoint. | Part I §§3.1–3.2 | Attack-label calibration or row overlap is a claim-blocking `FAIL`. |
| `DRIFT-SENTINEL-004` | The complete threshold programme assumes protocol-compliant calibration participants and an honest protocol-executing server; contributor-availability is non-adversarial and does not establish Byzantine/poisoning/message-integrity robustness. | Part I §3.2A / §10.E.10 | Adversarial robustness wording is `FAIL`. |
| `DRIFT-SENTINEL-005` | `n_k_source >= 100` is the primary eligibility rule and is computed before experimental calibration subsampling. | Part I §3.3 | Recomputing eligibility from experimental `m` is `FAIL`. |
| `DRIFT-SENTINEL-006` | Confirmatory deployment regime is `PERSISTENT_IDENTIFIABLE_CLIENTS` with full training participation and persistent client identity/state where required. | Part I §3.3A | Intermittent/unseen-client generalization is `FAIL`. |
| `DRIFT-SENTINEL-007` | Canonical empirical threshold is `q=0.95`, Hyndman–Fan type-7 / NumPy `method="linear"`, float64; conformal and KLL are explicit exceptions with their own semantics. | Part I §2.2.3 | Alternate interpolation under the same method identity is `FAIL`. |
| `DRIFT-SENTINEL-008` | Every federated training execution has one scientific terminal detector at round `200`; diagnostic/recovery checkpoints never become scientific score sources. | Part III §13 / Gate F | Non-terminal scientific scoring is `FAIL`. |
| `DRIFT-SENTINEL-009` | AUROC/AP are detector-quality controls computed from canonical continuous scores; threshold policy cannot improve AUROC within a fixed-score ladder. | Part I §2.2.2 / Part III §§4.5–4.6 | Policy-specific AUROC differences are provenance `FAIL`. |
| `DRIFT-SENTINEL-010` | `CICIOT_FILE_CLIENTS` is file-defined applicability-boundary evidence only; no physical-device reconstruction or device-aware claim is authorized. | Part I §9.2 / Part II §4.2 | Inferred-device semantics are `FAIL`. |
| `DRIFT-SENTINEL-011` | Edge static/temporal populations support the exact client/metric semantics declared by the roadmap; unsupported per-client attack-sensitive metrics remain unavailable. | Part I §§9.4–9.5 / Part II §§4.4–4.5 | Reconstructed unsupported attack metrics are `FAIL`. |
| `DRIFT-SENTINEL-012` | DATP-Core adds no external IoT dataset beyond Edge-IIoTset; no extra dataset is added without an explicit roadmap amendment. | Part I §9.6 / Gate O | Silent dataset expansion is `FAIL`. |
| `DRIFT-SENTINEL-013` | FedProx, `FEDAVG_LOCAL_FINE_TUNING`, Ditto, preprocessing sensitivity, external validation, temporal evidence, threshold variants, and mechanism analyses remain outside the sole confirmatory causal endpoint. | Part I §§7–8 / Part II evidence roles | Stress/supportive evidence cannot rescue or replace confirmation. |
| `DRIFT-SENTINEL-014` | No formal privacy, Byzantine/poisoning robustness, hardware deployment, fleet-scale, continuous-drift, or universal non-IID solution claim is authorized. | Part I §10.B / §10.D / §10.E | Overclaim is Gate R `FAIL`. |

## 1. Scientific programme and global-contract matrix

Every numbered Part I subsection below is independently auditable. The title is navigational; the exact roadmap text and formula/literal ledgers remain authoritative.

| ID | Category | Roadmap owner | Contract | Expected implementation owner | Disposition | Audit | Claim blocker |
|---|---|---|---|---|---|---|---|
| `GLOBAL-CONTRACT-001` | `GLOBAL` | Part I `1.1 Working title` (lines 63–66) | 1.1 Working title | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-002` | `GLOBAL` | Part I `1.2 DATP-Core in one paragraph` (lines 67–86) | 1.2 DATP-Core in one paragraph | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-003` | `GLOBAL` | Part I `2.1 Unit of causal comparison` (lines 89–107) | 2.1 Unit of causal comparison | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-004` | `GLOBAL` | Part I `2.2 Fixed elements` (lines 108–128) | 2.2 Fixed elements | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-001` | `THRESHOLD` | Part I `2.2.3 Empirical-quantile definition lock` (lines 185–210) | 2.2.3 Empirical-quantile definition lock | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-005` | `GLOBAL` | Part I `2.3 Sole manipulated variable` (lines 211–229) | 2.3 Sole manipulated variable | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `BOUNDARY-CONTRACT-001` | `BOUNDARY` | Part I `2.4 Prohibited causal contamination` (lines 230–244) | 2.4 Prohibited causal contamination | validation/reporting | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-001` | `CALIBRATION` | Part I `3.1 Benign-only calibration` (lines 247–265) | 3.1 Benign-only calibration | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-002` | `CALIBRATION` | Part I `3.2 Separation of calibration and evaluation` (lines 266–276) | 3.2 Separation of calibration and evaluation | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-003` | `CALIBRATION` | Part I `3.2A Honest-calibration participant and message-integrity assumption` (lines 277–300) | 3.2A Honest-calibration participant and message-integrity assumption | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-004` | `CALIBRATION` | Part I `3.3 Client eligibility` (lines 301–318) | 3.3 Client eligibility | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-006` | `GLOBAL` | Part I `3.3A Federation regime, client persistence, and deployment identity` (lines 319–355) | 3.3A Federation regime, client persistence, and deployment identity | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-007` | `GLOBAL` | Part I `3.4 Meaning of “fairness”` (lines 356–379) | 3.4 Meaning of “fairness” | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-008` | `GLOBAL` | Part I `3.5 Primary operating-point concern` (lines 380–391) | 3.5 Primary operating-point concern | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-009` | `GLOBAL` | Part I `3.6 Model-quality controls` (lines 392–414) | 3.6 Model-quality controls | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-010` | `GLOBAL` | Part I `4.1 Centralized reference: CENTRALIZED_REFERENCE` (lines 417–432) | 4.1 Centralized reference: CENTRALIZED_REFERENCE | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-002` | `THRESHOLD` | Part I `4.2 Shared threshold: SHARED_THRESHOLD` (lines 433–448) | 4.2 Shared threshold: SHARED_THRESHOLD | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-003` | `THRESHOLD` | Part I `4.3 Local threshold: LOCAL_THRESHOLD` (lines 449–462) | 4.3 Local threshold: LOCAL_THRESHOLD | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-004` | `THRESHOLD` | Part I `4.4 Family threshold: FAMILY_THRESHOLD` (lines 463–479) | 4.4 Family threshold: FAMILY_THRESHOLD | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-005` | `THRESHOLD` | Part I `4.5 Cluster threshold: CLUSTER_THRESHOLD` (lines 480–512) | 4.5 Cluster threshold: CLUSTER_THRESHOLD | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-011` | `GLOBAL` | Part I `4.6 Ladder interpretation` (lines 513–529) | 4.6 Ladder interpretation | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-006` | `THRESHOLD` | Part I `5.1 Quantile sensitivity` (lines 536–547) | 5.1 Quantile sensitivity | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-012` | `GLOBAL` | Part I `5.1A Historical mean-plus-standard-deviation estimator sensitivity` (lines 548–601) | 5.1A Historical mean-plus-standard-deviation estimator sensitivity | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-007` | `THRESHOLD` | Part I `5.2 Local–global shrinkage` (lines 602–646) | 5.2 Local–global shrinkage | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-005` | `CALIBRATION` | Part I `5.3 Calibration-size-aware shrinkage` (lines 647–668) | 5.3 Calibration-size-aware shrinkage | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-006` | `CALIBRATION` | Part I `5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD` (lines 669–696) | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-008` | `THRESHOLD` | Part I `6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`` (lines 699–717) | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-009` | `THRESHOLD` | Part I `6.1A `FEDERATED_KLL_SHARED_THRESHOLD`` (lines 718–757) | 6.1A `FEDERATED_KLL_SHARED_THRESHOLD` | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-013` | `GLOBAL` | Part I `6.2 Relationship to Laridi et al.` (lines 758–774) | 6.2 Relationship to Laridi et al. | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-001` | `TRAIN` | Part I `7.1 FedProx` (lines 781–808) | 7.1 FedProx | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-002` | `TRAIN` | Part I `7.1A FedProx mechanism-activation diagnostics` (lines 809–864) | 7.1A FedProx mechanism-activation diagnostics | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-003` | `TRAIN` | Part I `7.2 Ditto` (lines 865–897) | 7.2 Ditto | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-004` | `TRAIN` | Part I `7.2A Post-FedAvg client-local fine-tuning stress test` (lines 898–955) | 7.2A Post-FedAvg client-local fine-tuning stress test | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-010` | `THRESHOLD` | Part I `7.2B Common model-side score-alignment and threshold-absorption diagnostics` (lines 956–1106) | 7.2B Common model-side score-alignment and threshold-absorption diagnostics | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-014` | `GLOBAL` | Part I `7.3 Fallback naming` (lines 1107–1119) | 7.3 Fallback naming | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-015` | `GLOBAL` | Part I `7.4 Separation from the core ladder` (lines 1120–1131) | 7.4 Separation from the core ladder | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-016` | `GLOBAL` | Part I `8.1 Sole confirmatory evidence` (lines 1134–1145) | 8.1 Sole confirmatory evidence | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-007` | `CALIBRATION` | Part I `8.2 Supporting evidence families` (lines 1146–1170) | 8.2 Supporting evidence families | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-017` | `GLOBAL` | Part I `8.3 Honest negative evidence` (lines 1171–1176) | 8.3 Honest negative evidence | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-001` | `DATASET` | Part I `9.1 N-BaIoT physical-device anchor` (lines 1181–1194) | 9.1 N-BaIoT physical-device anchor | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-002` | `DATASET` | Part I `9.2 CICIoT2023 available-data boundary` (lines 1195–1215) | 9.2 CICIoT2023 available-data boundary | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-003` | `DATASET` | Part I `9.3 Controlled heterogeneity population` (lines 1216–1223) | 9.3 Controlled heterogeneity population | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-004` | `DATASET` | Part I `9.4 Edge-IIoTset external validation` (lines 1224–1243) | 9.4 Edge-IIoTset external validation | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-005` | `DATASET` | Part I `9.5 Temporal external population` (lines 1244–1258) | 9.5 Temporal external population | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-006` | `DATASET` | Part I `9.6 Dataset expansion limit` (lines 1259–1268) | 9.6 Dataset expansion limit | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-001` | `REPORT` | Part I `9.7 Heterogeneity taxonomy and claim boundary` (lines 1269–1297) | 9.7 Heterogeneity taxonomy and claim boundary | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-018` | `GLOBAL` | Part I `10.A.1 External validation` (lines 1306–1309) | 10.A.1 External validation | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-011` | `THRESHOLD` | Part I `10.A.2 Federated threshold comparison` (lines 1310–1313) | 10.A.2 Federated threshold comparison | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-005` | `TRAIN` | Part I `10.A.3 Training-side robustness` (lines 1314–1323) | 10.A.3 Training-side robustness | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-012` | `THRESHOLD` | Part I `10.A.4 Threshold-estimation depth` (lines 1324–1333) | 10.A.4 Threshold-estimation depth | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TEMPORAL-CONTRACT-001` | `TEMPORAL` | Part I `10.A.5 Temporal boundary` (lines 1334–1337) | 10.A.5 Temporal boundary | temporal analysis/pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-019` | `GLOBAL` | Part I `10.A.6 Mechanism analysis` (lines 1338–1350) | 10.A.6 Mechanism analysis | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-020` | `GLOBAL` | Part I `10.A.7 Hard scope limits` (lines 1351–1369) | 10.A.7 Hard scope limits | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-021` | `GLOBAL` | Part I `10.B.1 Security attacks and defenses` (lines 1372–1377) | 10.B.1 Security attacks and defenses | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-022` | `GLOBAL` | Part I `10.B.2 Formal privacy` (lines 1378–1387) | 10.B.2 Formal privacy | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-023` | `GLOBAL` | Part I `10.B.3 Deployment validation` (lines 1388–1393) | 10.B.3 Deployment validation | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-024` | `GLOBAL` | Part I `10.B.4 Fleet scale` (lines 1394–1399) | 10.B.4 Fleet scale | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TEMPORAL-CONTRACT-002` | `TEMPORAL` | Part I `10.B.5 Full drift handling` (lines 1400–1403) | 10.B.5 Full drift handling | temporal analysis/pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-025` | `GLOBAL` | Part I `10.B.6 Broad FL benchmarking` (lines 1404–1409) | 10.B.6 Broad FL benchmarking | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-008` | `CALIBRATION` | Part I `10.B.7 Federated conformal breadth` (lines 1410–1417) | 10.B.7 Federated conformal breadth | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-026` | `GLOBAL` | Part I `10.B.10 Explicit non-expansion guardrails for this amendment` (lines 1418–1435) | 10.B.10 Explicit non-expansion guardrails for this amendment | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-027` | `GLOBAL` | Part I `10.C.1 Project naming` (lines 1438–1465) | 10.C.1 Project naming | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-013` | `THRESHOLD` | Part I `10.C.2 Threshold-policy identifiers` (lines 1466–1487) | 10.C.2 Threshold-policy identifiers | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-014` | `THRESHOLD` | Part I `10.C.3 Threshold-variant identifiers` (lines 1488–1501) | 10.C.3 Threshold-variant identifiers | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-028` | `GLOBAL` | Part I `10.C.4 Laridi naming` (lines 1502–1521) | 10.C.4 Laridi naming | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-029` | `GLOBAL` | Part I `10.C.5 Personalized-model naming` (lines 1522–1542) | 10.C.5 Personalized-model naming | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TRAIN-CONTRACT-006` | `TRAIN` | Part I `10.C.5A Simple local-fine-tuning naming` (lines 1543–1546) | 10.C.5A Simple local-fine-tuning naming | learning/training + pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-007` | `DATASET` | Part I `10.C.6 Population identifiers` (lines 1547–1566) | 10.C.6 Population identifiers | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `STAT-CONTRACT-001` | `STAT` | Part I `10.C.7 Statistical and equity language` (lines 1567–1592) | 10.C.7 Statistical and equity language | analysis/inference | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-009` | `CALIBRATION` | Part I `10.C.7A Calibration-object taxonomy — mandatory at first manuscript use` (lines 1593–1608) | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-002` | `REPORT` | Part I `10.C.8 Novelty language` (lines 1609–1626) | 10.C.8 Novelty language | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-003` | `REPORT` | Part I `10.D.1 Permitted central framing` (lines 1631–1640) | 10.D.1 Permitted central framing | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-004` | `REPORT` | Part I `10.D.2 Prohibited central framing` (lines 1641–1655) | 10.D.2 Prohibited central framing | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `SCORE-CONTRACT-001` | `SCORE` | Part I `10.D.3 AUROC language` (lines 1656–1667) | 10.D.3 AUROC language | scoring + provenance | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `METRIC-CONTRACT-001` | `METRIC` | Part I `10.D.4 Macro-F1 language` (lines 1668–1679) | 10.D.4 Macro-F1 language | evaluation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-030` | `GLOBAL` | Part I `10.D.5 External validation language` (lines 1680–1691) | 10.D.5 External validation language | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TEMPORAL-CONTRACT-003` | `TEMPORAL` | Part I `10.D.6 Temporal language` (lines 1692–1701) | 10.D.6 Temporal language | temporal analysis/pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-031` | `GLOBAL` | Part I `10.D.7 Privacy language` (lines 1702–1711) | 10.D.7 Privacy language | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-032` | `GLOBAL` | Part I `10.D.8 Deployment language` (lines 1712–1725) | 10.D.8 Deployment language | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-005` | `REPORT` | Part I `10.D.9 Novelty boundary and mandatory prior-art audit` (lines 1726–1799) | 10.D.9 Novelty boundary and mandatory prior-art audit | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-006` | `REPORT` | Part I `10.D.9A Submission-time novelty-survival literature gate` (lines 1800–1834) | 10.D.9A Submission-time novelty-survival literature gate | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-007` | `REPORT` | Part I `10.D.9B Mandatory source-grounded prior-art distinction table` (lines 1835–1887) | 10.D.9B Mandatory source-grounded prior-art distinction table | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `REPORT-CONTRACT-008` | `REPORT` | Part I `10.D.10 Claim-survival rules` (lines 1888–1902) | 10.D.10 Claim-survival rules | reporting/claims | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-033` | `GLOBAL` | Part I `10.D.11 Negative evidence that must remain publishable` (lines 1903–1924) | 10.D.11 Negative evidence that must remain publishable | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-008` | `DATASET` | Part I `10.E.1 Small natural client population` (lines 1929–1934) | 10.E.1 Small natural client population | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `DATASET-CONTRACT-009` | `DATASET` | Part I `10.E.2 One external dataset` (lines 1935–1938) | 10.E.2 One external dataset | datasets/populations | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-034` | `GLOBAL` | Part I `10.E.3 Incomplete external attack assignment` (lines 1939–1942) | 10.E.3 Incomplete external attack assignment | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `TEMPORAL-CONTRACT-004` | `TEMPORAL` | Part I `10.E.4 Single temporal family` (lines 1943–1946) | 10.E.4 Single temporal family | temporal analysis/pipeline | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-035` | `GLOBAL` | Part I `10.E.5 No formal privacy guarantee` (lines 1947–1950) | 10.E.5 No formal privacy guarantee | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-036` | `GLOBAL` | Part I `10.E.6 No hardware evidence` (lines 1951–1954) | 10.E.6 No hardware evidence | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `THRESHOLD-CONTRACT-015` | `THRESHOLD` | Part I `10.E.7 Threshold trade-offs` (lines 1955–1958) | 10.E.7 Threshold trade-offs | thresholding | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `GLOBAL-CONTRACT-037` | `GLOBAL` | Part I `10.E.8 Comparator incompleteness` (lines 1959–1962) | 10.E.8 Comparator incompleteness | domain/protocols/pipeline validation | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-010` | `CALIBRATION` | Part I `10.E.9 Conformal limitation` (lines 1963–1966) | 10.E.9 Conformal limitation | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `CALIBRATION-CONTRACT-011` | `CALIBRATION` | Part I `10.E.10 Honest-calibration / no Byzantine-integrity guarantee` (lines 1967–1970) | 10.E.10 Honest-calibration / no Byzantine-integrity guarantee | calibration + thresholding contracts | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |
| `BOUNDARY-CONTRACT-002` | `BOUNDARY` | Part I `10.E.11 Persistent identifiable-client limitation` (lines 1971–1976) | 10.E.11 Persistent identifiable-client limitation | validation/reporting | `NOT_AUDITED` | — | DERIVE_FROM_ATOMIC_CHILD_REQUIREMENTS |

## 2. Numerical lock ledger

This reproduces the roadmap’s own navigation ledger. The cited detailed section remains authoritative. Any code literal affecting these contracts must map to one row; no magic value may bypass the protocol identity.

| ID | Roadmap line | Contract | Locked value / rule | Authoritative section | Repository mapping | Audit |
|---|---:|---|---|---|---|---|
| `NUMERIC-001` | 1983 | calibration object | DATP-Core studies anomaly operating-point calibration of a fixed continuous anomaly score; probability calibration and general federated conformal calibration are separate objects and do not authorize ECE/NLL/Brier or broad coverage claims | §10.C.7A | — | `NOT_AUDITED` |
| `NUMERIC-002` | 1984 | `H_TAUTOLOGY` held-out falsification | `CalibrationExceedance=(1/n_k_used) sum_j 1[e_cal>tau]`; `CalibrationTargetError=CalibrationExceedance-0.05`; `TestTargetError=FPR_test-0.05`; `CalibrationGeneralizationGap=TestTargetError-CalibrationTargetError` on disjoint calibration/evaluation rows | Part III §4.8A | — | `NOT_AUDITED` |
| `NUMERIC-003` | 1985 | honest calibration participants | protocol-compliant clients/server; no fabrication, semantic alteration, suppression, replay, identity substitution, or adversarial message manipulation of calibration rows, scores, thresholds, support counts, summaries, fingerprints, sketches, or conformal statistics; no Byzantine-robustness claim | §3.2A / §10.E.10 | — | `NOT_AUDITED` |
| `NUMERIC-004` | 1986 | canonical empirical quantile | `q=0.95`, Hyndman–Fan type-7 / NumPy `method="linear"` | §2.2.3 | — | `NOT_AUDITED` |
| `NUMERIC-005` | 1987 | quantile sensitivity | `{0.90,0.95,0.975,0.99}` | Part II §6.2 | — | `NOT_AUDITED` |
| `NUMERIC-006` | 1988 | historical moment estimator | `mean + sample SD`, `ddof=1`, float64; 2-by-2 `{TYPE7_Q95, moment} x {SHARED,LOCAL}` | §5.1A / Part II §6.2A | — | `NOT_AUDITED` |
| `NUMERIC-007` | 1989 | primary eligibility | `n_k_source >= 100` | §3.3 | — | `NOT_AUDITED` |
| `NUMERIC-008` | 1990 | calibration-size grid | `m={50,100,250,500,1000,5000}` | Part II §8.1 | — | `NOT_AUDITED` |
| `NUMERIC-009` | 1991 | calibration nested replicates | `R=10` per `(training_seed, client, m)` with prefix-nested SHA-256→PCG64 sampling | Part II §2.3A and §8.1 | — | `NOT_AUDITED` |
| `NUMERIC-010` | 1992 | calibration-subsample threshold variance | sample variance `s_tau^2=(R-1)^{-1} sum_r (tau_r-bar_tau)^2`, `R=10`, `ddof=1`; `ThresholdSD=sqrt(s_tau^2)` | Part III §8.4 | — | `NOT_AUDITED` |
| `NUMERIC-011` | 1993 | support-versus-burden diagnostic | per-seed Spearman correlations `rho(S,FPR_shared)` and `rho(S,FPR_shared-FPR_local)`; average ranks for ties; require at least `5` valid clients and at least `2` distinct values in both inputs; no client-level inferential p-value | Part II §7.5A | — | `NOT_AUDITED` |
| `NUMERIC-012` | 1994 | per-device effect direction counts | exact sign counts of `DeltaFPR_k=FPR_local,k-FPR_shared,k` and, where valid, `DeltaTPR_k=TPR_local,k-TPR_shared,k`; equality uses the exact common FP/TP counts, not a floating tolerance | Part II §7.5 | — | `NOT_AUDITED` |
| `NUMERIC-013` | 1995 | fixed shrinkage | `lambda={0,0.25,0.50,0.75,1.00}` | §5.2 / Part II §8.2 | — | `NOT_AUDITED` |
| `NUMERIC-014` | 1996 | size-aware shrinkage | `lambda_k=n_k_used/(n_k_used+100)` | §5.3 | — | `NOT_AUDITED` |
| `NUMERIC-015` | 1997 | CLUSTER_THRESHOLD fingerprint | `[mean,std,skew,p95]` of benign reconstruction error | §4.5 | — | `NOT_AUDITED` |
| `NUMERIC-016` | 1998 | CLUSTER_THRESHOLD clustering | separate score-side fingerprint standardization; canonical `K=3`; locked initialization/seed handling | §4.5 and Part II §7.1 | — | `NOT_AUDITED` |
| `NUMERIC-017` | 1999 | KLL comparator | float64; primary `k=400`; sensitivity `{200,800}`; inclusive rank | §6.1A / Part II §9.2 | — | `NOT_AUDITED` |
| `NUMERIC-018` | 2000 | FedProx | `mu={0.001,0.01,0.1,1.0}`; `mu=0` is FedAvg-equivalent, not a FedProx cell | §7.1 | — | `NOT_AUDITED` |
| `NUMERIC-019` | 2001 | FedProx activation diagnostics | `L2Drift`, `RMSDrift=L2/sqrt(P)`, terminal rounds `151..200`, un-clipped `DriftSuppression=1-D_FedProx/D_FedAvg` when denominator `>1e-12` | §7.1A / Part II §11.1 | — | `NOT_AUDITED` |
| `NUMERIC-020` | 2002 | calibration-contributor availability | omit `m={0,1,2,3,4}` shared-threshold contributors; exhaust every subset with `K_s-m>=5`; apply resulting shared threshold to unchanged full eligible evaluation population | Part II §8.6 | — | `NOT_AUDITED` |
| `NUMERIC-021` | 2003 | federation regime | persistent identifiable clients; full training participation `1.0`; retained client-local threshold/personalized state where applicable; no intermittent-cross-device or unseen-client claim | §3.3A | — | `NOT_AUDITED` |
| `NUMERIC-022` | 2004 | post-FedAvg local fine-tuning | initialize from exact FedAvg round-200 terminal detector; benign TRAIN only; exactly `10` local epochs; fresh optimizer state; no validation/calibration/test access; epoch-10 terminal personalized state | §7.2A / Part II §11.2A | — | `NOT_AUDITED` |
| `NUMERIC-023` | 2005 | common upstream absorption diagnostics | condition-native `H` for within-condition mapping; cross-model `ModelAlignmentH` on a seed-specific fixed FedAvg 64-bin grid; location/scale/local-q95 dispersion; normalized shared-local threshold distance; raw `DeltaScope`; un-clipped `ScopeAbsorption`; un-clipped `AlignmentReduction` when FedAvg denominator `>1e-12` | §7.2B | — | `NOT_AUDITED` |
| `NUMERIC-024` | 2006 | natural-device helped/harmed profile | exact sign-based FPR/TPR/Macro-F1/BA help-harm fractions; Pareto direction categories; per-device help frequency over the same ten seeds; fixed support strata of 3+3+3 eligible N-BaIoT devices | Part II §7.5B / Part III §5.6 | — | `NOT_AUDITED` |
| `NUMERIC-025` | 2007 | Ditto | `lambda_D={0.1,1.0,2.0}`, canonical `1.0` | §7.2 | — | `NOT_AUDITED` |
| `NUMERIC-026` | 2008 | terminal detector | one detector at fixed round `200` | Part III §13 | — | `NOT_AUDITED` |
| `NUMERIC-027` | 2009 | confirmatory replication | exactly `10` paired training seeds | §8.1 / Part II §5.1 / Part III §11 | — | `NOT_AUDITED` |
| `NUMERIC-028` | 2010 | confirmatory endpoint | SHARED_THRESHOLD vs LOCAL_THRESHOLD on N-BaIoT natural devices; seed-level Δ in `CV(FPR)` | §8.1 / Part II §5.1 / Part III §11 | — | `NOT_AUDITED` |
| `NUMERIC-029` | 2011 | temporal materiality | `drift_excess_materiality_threshold=0.05`; `material_recovery_ratio_minimum=0.5` | Part III §14 | — | `NOT_AUDITED` |
| `NUMERIC-030` | 2012 | serialization/reload equivalence | absolute tolerance `1e-12`; never used as scientific score identity | §2.2.1–§2.2.2 | — | `NOT_AUDITED` |

## 3. Complete block-formula ledger

**Extraction count:** `198` display-math blocks from the locked roadmap snapshot. Each is listed exactly once by source occurrence; duplicate mathematical definitions remain visible if the roadmap repeats them.

### FORMULA-001 — I / source lines 191–193

**Context:** 2.2.2 Fixed-score identity and serialization tolerance

```latex
h=(n-1)q,\qquad j=\lfloor h\rfloor,\qquad \gamma=h-j,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-002 — I / source lines 197–200

**Context:** 2.2.2 Fixed-score identity and serialization tolerance

```latex
Q_7(q)
=(1-\gamma)x_{(j+1)}+\gamma x_{(j+2)},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-003 — I / source lines 560–562

**Context:** 5. Supportive threshold variants

```latex
\bar e_k=\frac{1}{n_k}\sum_{i=1}^{n_k}e_{k,i},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-004 — I / source lines 564–570

**Context:** 5. Supportive threshold variants

```latex
s_k=
\sqrt{
\frac{1}{n_k-1}
\sum_{i=1}^{n_k}(e_{k,i}-\bar e_k)^2
},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-005 — I / source lines 574–576

**Context:** 5. Supportive threshold variants

```latex
\tau_{k,\mathrm{moment}}=\bar e_k+s_k.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-006 — I / source lines 587–589

**Context:** 5. Supportive threshold variants

```latex
\tau_{\mathrm{local},k}^{\mathrm{moment}}=\tau_{k,\mathrm{moment}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-007 — I / source lines 591–594

**Context:** 5. Supportive threshold variants

```latex
\tau_{\mathrm{shared}}^{\mathrm{moment}}
=\frac{1}{K_e}\sum_{k=1}^{K_e}\tau_{k,\mathrm{moment}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-008 — I / source lines 606–608

**Context:** 5. Supportive threshold variants

```latex
\tau_k^*=\inf\{t:F_k(t)\ge q\},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-009 — I / source lines 616–619

**Context:** 5. Supportive threshold variants

```latex
D^{scope}_{s,k}
=\tau^{full}_{shared,s}-\tau^{full}_{local,s,k};
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-010 — I / source lines 629–635

**Context:** 5. Supportive threshold variants

```latex
\tau_k(\lambda)
=
\lambda \tau_{k,\mathrm{local}}
+
(1-\lambda)\tau_{\mathrm{shared}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-011 — I / source lines 651–653

**Context:** 5. Supportive threshold variants

```latex
\lambda_k = \lambda(n_{k,\mathrm{used}}) = \frac{n_{k,\mathrm{used}}}{n_{k,\mathrm{used}} + n_{\min}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-012 — I / source lines 657–659

**Context:** 5. Supportive threshold variants

```latex
\tau_k^{SA} = \lambda_k\tau_{k,\mathrm{local}} + (1-\lambda_k)\tau_{\mathrm{shared}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-013 — I / source lines 740–744

**Context:** 6. Federated threshold comparator

```latex
\widehat F_{pool}(t)
=
\frac{1}{N}\sum_{i=1}^{N}\mathbf 1[e_i\le t].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-014 — I / source lines 748–752

**Context:** 6. Federated threshold comparator

```latex
EmpiricalRankError
=
\left|\widehat F_{pool}(\tau_{KLL})-q\right|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-015 — I / source lines 787–789

**Context:** 7. Training-side stress tests

```latex
\min_w\; F_k(w)+\frac{\mu}{2}\lVert w-w^{(t)}\rVert_2^2,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-016 — I / source lines 815–818

**Context:** 7. Training-side stress tests

```latex
L2Drift_{k,t}
=\left\|w^{out}_{k,t}-w^{(t)}\right\|_2,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-017 — I / source lines 820–823

**Context:** 7. Training-side stress tests

```latex
RMSDrift_{k,t}
=\frac{L2Drift_{k,t}}{\sqrt{P}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-018 — I / source lines 827–830

**Context:** 7. Training-side stress tests

```latex
TerminalProxPenalty_{k,t}(\mu)
=\frac{\mu}{2}L2Drift_{k,t}^2.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-019 — I / source lines 834–837

**Context:** 7. Training-side stress tests

```latex
D^{all}_{s,a}
=\operatorname{median}_{k,t\in\{1,\ldots,200\}} RMSDrift_{k,t},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-020 — I / source lines 839–842

**Context:** 7. Training-side stress tests

```latex
D^{terminal50}_{s,a}
=\operatorname{median}_{k,t\in\{151,\ldots,200\}} RMSDrift_{k,t}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-021 — I / source lines 848–853

**Context:** 7. Training-side stress tests

```latex
DriftSuppression_{s,\mu}
=1-
\frac{D^{terminal50}_{s,FedProx(\mu)}}
{D^{terminal50}_{s,FedAvg}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-022 — I / source lines 859–861

**Context:** 7. Training-side stress tests

```latex
\Delta H_{s,\mu}=H_{s,FedProx(\mu)}-H_{s,FedAvg}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-023 — I / source lines 871–873

**Context:** 7. Training-side stress tests

```latex
\min_{v_k}\;F_k(v_k)+\frac{\lambda_D}{2}\lVert v_k-w\rVert_2^2.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-024 — I / source lines 920–922

**Context:** 7. Training-side stress tests

```latex
v^{FT}_{k,0}=w^{FedAvg}_{200}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-025 — I / source lines 926–931

**Context:** 7. Training-side stress tests

```latex
v^{FT}_{k,e+1}
=\operatorname{LocalEpoch}
\left(v^{FT}_{k,e};\,D^{train,benign}_k,\,\theta_{FedAvg}\right),
\qquad e=0,\ldots,9,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-026 — I / source lines 962–964

**Context:** 7. Training-side stress tests

```latex
M_{s,a,k}=\operatorname{median}(E^{cal}_{s,a,k}),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-027 — I / source lines 966–968

**Context:** 7. Training-side stress tests

```latex
I_{s,a,k}=Q_7(0.75;E^{cal}_{s,a,k})-Q_7(0.25;E^{cal}_{s,a,k}),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-028 — I / source lines 970–972

**Context:** 7. Training-side stress tests

```latex
T_{s,a,k}=Q_7(0.95;E^{cal}_{s,a,k}).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-029 — I / source lines 976–979

**Context:** 7. Training-side stress tests

```latex
LocationDispersion_{s,a}
=\frac{SD_k(M_{s,a,k})}{Mean_k(M_{s,a,k})},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-030 — I / source lines 981–984

**Context:** 7. Training-side stress tests

```latex
ScaleDispersion_{s,a}
=\frac{SD_k(I_{s,a,k})}{Mean_k(I_{s,a,k})},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-031 — I / source lines 986–989

**Context:** 7. Training-side stress tests

```latex
LocalThresholdDispersion_{s,a}
=\frac{SD_k(T_{s,a,k})}{Mean_k(T_{s,a,k})},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-032 — I / source lines 995–999

**Context:** 7. Training-side stress tests

```latex
MeanSharedLocalThresholdDistance_{s,a}
=\frac{1}{K_e}\sum_k
\left|\tau^{shared}_{s,a}-\tau^{local}_{s,a,k}\right|,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-033 — I / source lines 1001–1005

**Context:** 7. Training-side stress tests

```latex
NormalizedSharedLocalThresholdDistance_{s,a}
=\frac{MeanSharedLocalThresholdDistance_{s,a}}
{Mean_k(\tau^{local}_{s,a,k})}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-034 — I / source lines 1013–1016

**Context:** 7. Training-side stress tests

```latex
b_{s,j}=Q_7\!\left(\frac{j}{64};\;\bigcup_{k\in K_e}E^{cal}_{s,FedAvg,k}\right),
\qquad j=1,\ldots,63.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-035 — I / source lines 1020–1022

**Context:** 7. Training-side stress tests

```latex
(-\infty,b_{s,1}],\;(b_{s,1},b_{s,2}],\;\ldots,\;(b_{s,J_s},+\infty),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-036 — I / source lines 1026–1030

**Context:** 7. Training-side stress tests

```latex
ModelAlignmentH_{s,a}
:=\frac{2}{K_e(K_e-1)}
\sum_{i<j}JSD_{B_s}(P_{s,a,i},P_{s,a,j}),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-037 — I / source lines 1036–1039

**Context:** 7. Training-side stress tests

```latex
\Delta Scope_{s,a}
:=CV(FPR)_{s,a,shared}-CV(FPR)_{s,a,local}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-038 — I / source lines 1055–1058

**Context:** 7. Training-side stress tests

```latex
AlignmentReduction^X_{s,a}
=1-\frac{X_{s,a}}{X_{s,FedAvg}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-039 — I / source lines 1064–1067

**Context:** 7. Training-side stress tests

```latex
ScopeAbsorption_{s,a}
=1-\frac{\Delta Scope_{s,a}}{\Delta Scope_{s,FedAvg}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-040 — II / source lines 2565–2571

**Context:** 5. Confirmatory experiment

```latex
\Delta_s
=
CV(FPR)_{\mathrm{shared},s}
-
CV(FPR)_{\mathrm{local},s}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-041 — II / source lines 2814–2817

**Context:** 6. Supportive robustness experiments

```latex
\Delta^{scope}_{s,E}
=CV(FPR)_{s,E,shared}-CV(FPR)_{s,E,local}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-042 — II / source lines 2821–2824

**Context:** 6. Supportive robustness experiments

```latex
\Delta^{estimator}_s
=\Delta^{scope}_{s,MEAN+SD}-\Delta^{scope}_{s,Q95}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-043 — II / source lines 2973–2975

**Context:** 7. Cluster and family mechanism programme

```latex
s_i=\frac{b_i-a_i}{\max(a_i,b_i)}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-044 — II / source lines 2981–2984

**Context:** 7. Cluster and family mechanism programme

```latex
SwitchFrequency_k
=\frac{1}{S-1}\sum_{s\ne s_0}\mathbf 1[\widetilde c_{k,s}\ne c_{k,s_0}].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-045 — II / source lines 2992–2997

**Context:** 7. Cluster and family mechanism programme

```latex
RecoveryFraction_G
=
\frac{CV(FPR)_{\mathrm{shared}}-CV(FPR)_G}
{CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-046 — II / source lines 3042–3045

**Context:** 7. Cluster and family mechanism programme

```latex
WithinFamilyJS
=\frac{1}{|\mathcal P_W|}\sum_{(i,j)\in\mathcal P_W}JSD(P_i,P_j),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-047 — II / source lines 3047–3050

**Context:** 7. Cluster and family mechanism programme

```latex
BetweenFamilyJS
=\frac{1}{|\mathcal P_B|}\sum_{(i,j)\in\mathcal P_B}JSD(P_i,P_j),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-048 — II / source lines 3052–3054

**Context:** 7. Cluster and family mechanism programme

```latex
FamilySeparationJS=BetweenFamilyJS-WithinFamilyJS.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-049 — II / source lines 3058–3063

**Context:** 7. Cluster and family mechanism programme

```latex
WithinFamilyThresholdSD
=\frac{1}{|\mathcal F_{\ge2}|}
\sum_{f\in\mathcal F_{\ge2}}
SD(\{\tau_k:k\in f\},ddof=1),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-050 — II / source lines 3067–3070

**Context:** 7. Cluster and family mechanism programme

```latex
BetweenFamilyThresholdSD
=SD(\{\overline\tau_f:f\in\mathcal F\},ddof=1).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-051 — II / source lines 3118–3120

**Context:** 7. Cluster and family mechanism programme

```latex
\left\{0,\frac{1}{64},\frac{2}{64},\ldots,1\right\}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-052 — II / source lines 3126–3129

**Context:** 7. Cluster and family mechanism programme

```latex
JSD(P,Q)
=\frac{1}{2}KL_2(P\|M)+\frac{1}{2}KL_2(Q\|M),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-053 — II / source lines 3133–3135

**Context:** 7. Cluster and family mechanism programme

```latex
KL_2(P\|M)=\sum_{b:P_b>0}P_b\log_2\frac{P_b}{M_b}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-054 — II / source lines 3139–3142

**Context:** 7. Cluster and family mechanism programme

```latex
H
=\frac{2}{K_e(K_e-1)}\sum_{i<j}JSD(P_i,P_j).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-055 — II / source lines 3169–3171

**Context:** 7. Cluster and family mechanism programme

```latex
\Delta CV_{s,-j}=CV(FPR)_{shared,s,-j}-CV(FPR)_{local,s,-j}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-056 — II / source lines 3175–3177

**Context:** 7. Cluster and family mechanism programme

```latex
MaxLODORhoShift=\max_j|\rho_{-j}-\rho_{full}|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-057 — II / source lines 3197–3204

**Context:** 7. Cluster and family mechanism programme

```latex
\Delta CV_{s,\alpha,m}
=\beta_{0,s}
+\beta_{1,s}H_{s,\alpha}
+\beta_{2,s}\log_{10}(m/100)
+\beta_{3,s}H_{s,\alpha}\log_{10}(m/100)
+\varepsilon_{s,\alpha,m}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-058 — II / source lines 3219–3223

**Context:** 7. Cluster and family mechanism programme

```latex
CV_p\le CV_r,
\qquad
P10F1_p\ge P10F1_r,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-059 — II / source lines 3258–3260

**Context:** 7. Cluster and family mechanism programme

```latex
\Delta \tau_k = \tau_{\mathrm{local},k} - \tau_{\mathrm{shared}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-060 — II / source lines 3262–3264

**Context:** 7. Cluster and family mechanism programme

```latex
\Delta FPR_k = FPR_{\mathrm{local},k} - FPR_{\mathrm{shared},k}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-061 — II / source lines 3266–3268

**Context:** 7. Cluster and family mechanism programme

```latex
\Delta TPR_k = TPR_{\mathrm{local},k} - TPR_{\mathrm{shared},k}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-062 — II / source lines 3280–3284

**Context:** 7. Cluster and family mechanism programme

```latex
N^{FPR}_{down,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}<0],\quad
N^{FPR}_{same,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}=0],\quad
N^{FPR}_{up,s}=\sum_k\mathbf 1[\Delta FPR_{s,k}>0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-063 — II / source lines 3288–3292

**Context:** 7. Cluster and family mechanism programme

```latex
N^{TPR}_{down,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}<0],\quad
N^{TPR}_{same,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}=0],\quad
N^{TPR}_{up,s}=\sum_k\mathbf 1[\Delta TPR_{s,k}>0].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-064 — II / source lines 3314–3316

**Context:** 7. Cluster and family mechanism programme

```latex
S_{s,k}=n_{s,k,source},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-065 — II / source lines 3318–3320

**Context:** 7. Cluster and family mechanism programme

```latex
SharedTargetBurden_{s,k}=FPR_{shared,s,k}-(1-q),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-066 — II / source lines 3324–3326

**Context:** 7. Cluster and family mechanism programme

```latex
PersonalizationRelief_{s,k}=FPR_{shared,s,k}-FPR_{local,s,k}=-\Delta FPR_{s,k}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-067 — II / source lines 3332–3335

**Context:** 7. Cluster and family mechanism programme

```latex
\rho^{support,FPR}_s
=Spearman(S_{s,k},FPR_{shared,s,k}),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-068 — II / source lines 3337–3340

**Context:** 7. Cluster and family mechanism programme

```latex
\rho^{support,relief}_s
=Spearman(S_{s,k},PersonalizationRelief_{s,k}).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-069 — II / source lines 3346–3350

**Context:** 7. Cluster and family mechanism programme

```latex
Spearman(x,y)=
\frac{\sum_k(R(x_k)-\overline{R_x})(R(y_k)-\overline{R_y})}
{\sqrt{\sum_k(R(x_k)-\overline{R_x})^2}\sqrt{\sum_k(R(y_k)-\overline{R_y})^2}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-070 — II / source lines 3376–3378

**Context:** 7. Cluster and family mechanism programme

```latex
FPRRelief_{s,k}=FPR_{shared,s,k}-FPR_{local,s,k},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-071 — II / source lines 3380–3382

**Context:** 7. Cluster and family mechanism programme

```latex
TPRChange_{s,k}=TPR_{local,s,k}-TPR_{shared,s,k},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-072 — II / source lines 3384–3386

**Context:** 7. Cluster and family mechanism programme

```latex
MacroF1Change_{s,k}=MacroF1_{local,s,k}-MacroF1_{shared,s,k},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-073 — II / source lines 3388–3390

**Context:** 7. Cluster and family mechanism programme

```latex
BAChange_{s,k}=BA_{local,s,k}-BA_{shared,s,k}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-074 — II / source lines 3396–3398

**Context:** 7. Cluster and family mechanism programme

```latex
FPRHelpedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}>0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-075 — II / source lines 3400–3402

**Context:** 7. Cluster and family mechanism programme

```latex
FPRHarmedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}<0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-076 — II / source lines 3404–3406

**Context:** 7. Cluster and family mechanism programme

```latex
FPRUnchangedFraction_s=\frac{1}{K_e}\sum_k\mathbf 1[FPRRelief_{s,k}=0].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-077 — II / source lines 3410–3413

**Context:** 7. Cluster and family mechanism programme

```latex
TPRLossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[TPRChange_{s,k}<0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-078 — II / source lines 3415–3418

**Context:** 7. Cluster and family mechanism programme

```latex
MacroF1LossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[MacroF1Change_{s,k}<0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-079 — II / source lines 3420–3423

**Context:** 7. Cluster and family mechanism programme

```latex
BALossFraction_s
=\frac{1}{|K_{attack,s}|}\sum_k\mathbf 1[BAChange_{s,k}<0].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-080 — II / source lines 3439–3441

**Context:** 7. Cluster and family mechanism programme

```latex
FPRHarmMagnitude_{s,k}=FPR_{local,s,k}-FPR_{shared,s,k}=-FPRRelief_{s,k}>0.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-081 — II / source lines 3445–3447

**Context:** 7. Cluster and family mechanism programme

```latex
TPRLossMagnitude_{s,k}=TPR_{shared,s,k}-TPR_{local,s,k}=-TPRChange_{s,k}>0.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-082 — II / source lines 3453–3455

**Context:** 7. Cluster and family mechanism programme

```latex
FPRHelpFrequency_k=\frac{1}{10}\sum_s\mathbf 1[FPRRelief_{s,k}>0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-083 — II / source lines 3457–3459

**Context:** 7. Cluster and family mechanism programme

```latex
FPRHarmFrequency_k=\frac{1}{10}\sum_s\mathbf 1[FPRRelief_{s,k}<0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-084 — II / source lines 3463–3465

**Context:** 7. Cluster and family mechanism programme

```latex
TPRLossFrequency_k=\frac{1}{|S_k^{TPR}|}\sum_{s\in S_k^{TPR}}\mathbf 1[TPRChange_{s,k}<0].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-085 — II / source lines 3473–3477

**Context:** 7. Cluster and family mechanism programme

```latex
SupportScore_k
=\operatorname{median}_{s\in\mathcal S_{train}} n_{s,k,source},
\qquad |\mathcal S_{train}|=10.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-086 — II / source lines 3491–3493

**Context:** 7. Cluster and family mechanism programme

```latex
StratumMeanFPRRelief_{s,g}=\frac{1}{3}\sum_{k\in g}FPRRelief_{s,k},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-087 — II / source lines 3495–3497

**Context:** 7. Cluster and family mechanism programme

```latex
StratumFPRHelpedFraction_{s,g}=\frac{1}{3}\sum_{k\in g}\mathbf 1[FPRRelief_{s,k}>0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-088 — II / source lines 3499–3501

**Context:** 7. Cluster and family mechanism programme

```latex
StratumFPRHarmedFraction_{s,g}=\frac{1}{3}\sum_{k\in g}\mathbf 1[FPRRelief_{s,k}<0],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-089 — II / source lines 3505–3509

**Context:** 7. Cluster and family mechanism programme

```latex
StratumMATE^{p}_{s,g}
=\frac{1}{3}\sum_{k\in g}\left|FPR_{p,s,k}-(1-q)\right|,
\qquad p\in\{shared,local\}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-090 — II / source lines 3523–3528

**Context:** 7. Cluster and family mechanism programme

```latex
TPR_{k,f}
=\frac{TP_{k,f}}{N_{k,f}},\qquad
FNR_{k,f}=1-TPR_{k,f},\qquad
f\in\{Mirai,BASHLITE\}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-091 — II / source lines 3532–3535

**Context:** 7. Cluster and family mechanism programme

```latex
WorstFamilyClientTPR
=\min_{(k,f):N_{k,f}>0} TPR_{k,f},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-092 — II / source lines 3539–3544

**Context:** 7. Cluster and family mechanism programme

```latex
MacroFamilyTPR_f
=\frac{1}{|K_f|}\sum_{k\in K_f}TPR_{k,f},
\qquad
K_f=\{k:N_{k,f}>0\}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-093 — II / source lines 3581–3583

**Context:** 7. Cluster and family mechanism programme

```latex
CV_A\le CV_B,\qquad P10_A\ge P10_B,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-094 — II / source lines 3676–3679

**Context:** 8. Calibration robustness programme

```latex
Bias_\tau(s,k,m)
=\frac{1}{R}\sum_{r=1}^{R}\left(\tau_{s,k,m,r}-\tau^{full}_{s,k}\right),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-095 — II / source lines 3681–3684

**Context:** 8. Calibration robustness programme

```latex
RMSE_\tau(s,k,m)
=\sqrt{\frac{1}{R}\sum_{r=1}^{R}\left(\tau_{s,k,m,r}-\tau^{full}_{s,k}\right)^2};
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-096 — II / source lines 3688–3690

**Context:** 8. Calibration robustness programme

```latex
(\tau_{i,m,r}-\tau_{j,m,r})(\tau^{full}_{i}-\tau^{full}_{j})<0.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-097 — II / source lines 3695–3698

**Context:** 8. Calibration robustness programme

```latex
MeanLocalSharedDistance
=\frac{1}{K_e}\sum_k|\tau_{\mathrm{local},k}-\tau_{\mathrm{shared}}|;
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-098 — II / source lines 3869–3872

**Context:** 8. Calibration robustness programme

```latex
\Delta_{scope,preproc}
=CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-099 — II / source lines 3878–3881

**Context:** 8. Calibration robustness programme

```latex
\Delta^{localStd}_s
=CV(FPR)_{shared,s,localStd}-CV(FPR)_{local,s,localStd},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-100 — II / source lines 3883–3886

**Context:** 8. Calibration robustness programme

```latex
\Delta^{pooledMinMax}_s
=CV(FPR)_{shared,s,pooledMinMax}-CV(FPR)_{local,s,pooledMinMax}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-101 — II / source lines 3890–3893

**Context:** 8. Calibration robustness programme

```latex
PreprocessingAbsorption_s
=1-\frac{\Delta^{pooledMinMax}_s}{\Delta^{localStd}_s}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-102 — II / source lines 3924–3928

**Context:** 8. Calibration robustness programme

```latex
\sum_{m=0}^{4}\binom{9}{m}
=1+9+36+84+126
=256.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-103 — II / source lines 3934–3939

**Context:** 8. Calibration robustness programme

```latex
\tau^{shared}_{s,U}
=\frac{1}{K_s-|U|}
\sum_{k\in E_s\setminus U}
Q_7(E^{cal}_{s,k},0.95).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-104 — II / source lines 3943–3945

**Context:** 8. Calibration robustness programme

```latex
\tau^{local}_{s,k}=Q_7(E^{cal}_{s,k},0.95).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-105 — II / source lines 3949–3952

**Context:** 8. Calibration robustness programme

```latex
SharedThresholdShift_{s,U}
=\tau^{shared}_{s,U}-\tau^{shared}_{s,\emptyset},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-106 — II / source lines 3954–3957

**Context:** 8. Calibration robustness programme

```latex
\Delta CV_{s,U}
=CV(FPR)^{shared}_{s,U}-CV(FPR)^{local}_{s},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-107 — II / source lines 3963–3965

**Context:** 8. Calibration robustness programme

```latex
MedianDeltaCV_{s,m}=\operatorname{median}_{|U|=m}\Delta CV_{s,U},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-108 — II / source lines 3967–3969

**Context:** 8. Calibration robustness programme

```latex
WorstSharedCV_{s,m}=\max_{|U|=m}CV(FPR)^{shared}_{s,U},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-109 — II / source lines 3971–3974

**Context:** 8. Calibration robustness programme

```latex
MaxAbsoluteThresholdShift_{s,m}
=\max_{|U|=m}|SharedThresholdShift_{s,U}|,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-110 — II / source lines 3978–3982

**Context:** 8. Calibration robustness programme

```latex
PositiveScopeGainRetention_{s,m}
=\frac{1}{\binom{K_s}{m}}
\sum_{|U|=m}\mathbf 1[\Delta CV_{s,U}>0].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-111 — II / source lines 4234–4240

**Context:** 11. Training-side stress tests

```latex
\text{stronger client adaptation}
\Rightarrow
\text{lower benign-score/threshold heterogeneity}
\Rightarrow
\text{smaller }\Delta Scope.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-112 — II / source lines 4279–4282

**Context:** 11. Training-side stress tests

```latex
F_k^{prox}(w;w^{(t)},\mu)
=F_k(w)+\frac{\mu}{2}\lVert w-w^{(t)}\rVert_2^2.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-113 — II / source lines 4365–4368

**Context:** 11. Training-side stress tests

```latex
F_k^{Ditto}(v_k;w,\lambda_D)
=F_k(v_k)+\frac{\lambda_D}{2}\lVert v_k-w\rVert_2^2.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-114 — II / source lines 4387–4393

**Context:** 11. Training-side stress tests

```latex
\Delta_{\mathrm{FedAvg}}
=
CV(FPR)_{\mathrm{FedAvg+shared}}
-
CV(FPR)_{\mathrm{FedAvg+local}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-115 — II / source lines 4395–4401

**Context:** 11. Training-side stress tests

```latex
\Delta_{\mathrm{Ditto}}
=
CV(FPR)_{\mathrm{Ditto+shared}}
-
CV(FPR)_{\mathrm{Ditto+local}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-116 — II / source lines 4405–4408

**Context:** 11. Training-side stress tests

```latex
AbsorptionFraction
=1-\frac{\Delta_{\mathrm{Ditto}}}{\Delta_{\mathrm{FedAvg}}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-117 — II / source lines 4470–4473

**Context:** 11. Training-side stress tests

```latex
\Delta_{FT,s}
=CV(FPR)_{FT+shared,s}-CV(FPR)_{FT+local,s},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-118 — II / source lines 4477–4480

**Context:** 11. Training-side stress tests

```latex
ScopeAbsorption_{FT,s}
=1-\frac{\Delta_{FT,s}}{\Delta_{FedAvg,s}};
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-119 — II / source lines 4552–4558

**Context:** 12. Temporal recalibration experiment

```latex
drift\_excess
=
CV_{\mathrm{frozen\ future}}
-
CV_{\mathrm{static\ reference}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-120 — II / source lines 4560–4566

**Context:** 12. Temporal recalibration experiment

```latex
recovered\_amount
=
CV_{\mathrm{frozen\ future}}
-
CV_{\mathrm{recalibrated\ future}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-121 — II / source lines 4568–4572

**Context:** 12. Temporal recalibration experiment

```latex
recovery\_ratio
=
\frac{recovered\_amount}{drift\_excess}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-122 — II / source lines 4580–4582

**Context:** 12. Temporal recalibration experiment

```latex
\Delta\tau_k=\tau_{k,\mathrm{recalibrated}}-\tau_{k,\mathrm{historical}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-123 — II / source lines 4586–4589

**Context:** 12. Temporal recalibration experiment

```latex
FrozenFPRDeterioration_k
=FPR_{k,\mathrm{frozen\\ future}}-FPR_{k,\mathrm{static\\ reference}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-124 — II / source lines 4591–4594

**Context:** 12. Temporal recalibration experiment

```latex
RecoveryFPR_k
=FPR_{k,\mathrm{frozen\\ future}}-FPR_{k,\mathrm{recalibrated\\ future}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-125 — II / source lines 4600–4603

**Context:** 12. Temporal recalibration experiment

```latex
HelpedFraction=\frac{|\{k:RecoveryFPR_k>0\}|}{K_e},\\quad
HarmedFraction=\frac{|\{k:RecoveryFPR_k<0\}|}{K_e}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-126 — II / source lines 4607–4611

**Context:** 12. Temporal recalibration experiment

```latex
WorstClientFPRRecovery
=\\max_k FPR_{k,\mathrm{frozen\\ future}}
-\\max_k FPR_{k,\mathrm{recalibrated\\ future}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-127 — II / source lines 4671–4677

**Context:** 13. Operational translation

```latex
alerts_{k,\mathrm{day}}
=
FPR_k
\times
benign\_traffic\_rate_{k,\mathrm{day}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-128 — III / source lines 4810–4817

**Context:** 2. Prediction and confusion counts

```latex
\widehat{y}
=
\begin{cases}
\text{attack}, & e > \tau \\
\text{benign}, & e \leq \tau
\end{cases}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-129 — III / source lines 4860–4864

**Context:** 3. Metric populations

```latex
coverage
=
\frac{K_{\mathrm{eligible}}}{K_{\mathrm{candidate}}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-130 — III / source lines 4876–4880

**Context:** 4. Per-client metrics

```latex
FPR_k
=
\frac{FP_k}{FP_k + TN_k}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-131 — III / source lines 4886–4890

**Context:** 4. Per-client metrics

```latex
TPR_k
=
\frac{TP_k}{TP_k + FN_k}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-132 — III / source lines 4896–4900

**Context:** 4. Per-client metrics

```latex
BA_k
=
\frac{TPR_k + (1-FPR_k)}{2}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-133 — III / source lines 4908–4916

**Context:** 4. Per-client metrics

```latex
MacroF1_k
=
\frac{
F1_{k,\mathrm{benign}}
+
F1_{k,\mathrm{attack}}
}{2}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-134 — III / source lines 4936–4938

**Context:** 4. Per-client metrics

```latex
AP=\sum_n (R_n-R_{n-1})P_n.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-135 — III / source lines 4946–4948

**Context:** 4. Per-client metrics

```latex
TargetFPR=1-q.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-136 — III / source lines 4952–4954

**Context:** 4. Per-client metrics

```latex
SignedTestFPRTargetError_k=FPR_k-(1-q),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-137 — III / source lines 4956–4958

**Context:** 4. Per-client metrics

```latex
AbsoluteTestFPRTargetError_k=|FPR_k-(1-q)|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-138 — III / source lines 4962–4965

**Context:** 4. Per-client metrics

```latex
MeanAbsoluteTargetError
=\frac{1}{K_e}\sum_k AbsoluteTestFPRTargetError_k,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-139 — III / source lines 4969–4971

**Context:** 4. Per-client metrics

```latex
WorstAbsoluteTargetError=\max_k AbsoluteTestFPRTargetError_k.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-140 — III / source lines 4979–4984

**Context:** 4. Per-client metrics

```latex
CalibrationExceedance_k
=\frac{1}{n_{k,used}}
\sum_{i=1}^{n_{k,used}}
\mathbf 1[e^{cal}_{k,i}>\tau_k].
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-141 — III / source lines 4990–4993

**Context:** 4. Per-client metrics

```latex
CalibrationGeneralizationGap_k
=FPR^{test}_k-CalibrationExceedance_k,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-142 — III / source lines 4997–5000

**Context:** 4. Per-client metrics

```latex
AbsoluteCalibrationGeneralizationGap_k
=|CalibrationGeneralizationGap_k|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-143 — III / source lines 5004–5007

**Context:** 4. Per-client metrics

```latex
MeanAbsoluteCalibrationGeneralizationGap
=\frac{1}{K_e}\sum_k AbsoluteCalibrationGeneralizationGap_k,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-144 — III / source lines 5029–5033

**Context:** 4. Per-client metrics

```latex
CalibrationExceedance_{k,p}
=\frac{1}{n_{k,used}}\sum_{j=1}^{n_{k,used}}
\mathbf 1[e^{cal}_{k,j}>\tau_{k,p}],
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-145 — III / source lines 5037–5040

**Context:** 4. Per-client metrics

```latex
CalibrationTargetError_{k,p}
=CalibrationExceedance_{k,p}-(1-q).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-146 — III / source lines 5044–5047

**Context:** 4. Per-client metrics

```latex
TestTargetError_{k,p}
=FPR^{test}_{k,p}-(1-q),
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-147 — III / source lines 5051–5055

**Context:** 4. Per-client metrics

```latex
TestTargetError_{k,p}-CalibrationTargetError_{k,p}
=FPR^{test}_{k,p}-CalibrationExceedance_{k,p}
=CalibrationGeneralizationGap_{k,p}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-148 — III / source lines 5077–5082

**Context:** 5. Cross-client operating-point metrics

```latex
\mu_{FPR}
=
\frac{1}{K_e}
\sum_{k=1}^{K_e} FPR_k
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-149 — III / source lines 5088–5096

**Context:** 5. Cross-client operating-point metrics

```latex
\sigma_{FPR}
=
\sqrt{
\frac{1}{K_e-1}
\sum_{k=1}^{K_e}
(FPR_k-\mu_{FPR})^2
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-150 — III / source lines 5113–5117

**Context:** 5. Cross-client operating-point metrics

```latex
CV(FPR)
=
\frac{\sigma_{FPR}}{\mu_{FPR}}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-151 — III / source lines 5133–5137

**Context:** 5. Cross-client operating-point metrics

```latex
IQR(FPR)
=
Q_{0.75}(FPR)-Q_{0.25}(FPR)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-152 — III / source lines 5139–5143

**Context:** 5. Cross-client operating-point metrics

```latex
Range(FPR)
=
\max(FPR_k)-\min(FPR_k)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-153 — III / source lines 5145–5149

**Context:** 5. Cross-client operating-point metrics

```latex
WorstFPR
=
\max(FPR_k)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-154 — III / source lines 5155–5160

**Context:** 5. Cross-client operating-point metrics

```latex
CV(TPR)
=
\frac{\operatorname{std}(TPR_k,ddof=1)}
{\operatorname{mean}(TPR_k)}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-155 — III / source lines 5164–5168

**Context:** 5. Cross-client operating-point metrics

```latex
P10(MacroF1)
=
Q_{0.10}(MacroF1_k)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-156 — III / source lines 5170–5174

**Context:** 5. Cross-client operating-point metrics

```latex
WorstBA
=
\min(BA_k)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-157 — III / source lines 5186–5194

**Context:** 6. Optional equity metrics

```latex
Jain(FPR)
=
\frac{
(\sum_k FPR_k)^2
}{
K_e\sum_k FPR_k^2
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-158 — III / source lines 5200–5208

**Context:** 6. Optional equity metrics

```latex
Gini(FPR)
=
\frac{
\sum_i\sum_j|FPR_i-FPR_j|
}{
2K_e\sum_iFPR_i
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-159 — III / source lines 5258–5263

**Context:** 7. Aggregate model-quality controls

```latex
MeanClientMacroF1
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} MacroF1_k
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-160 — III / source lines 5279–5284

**Context:** 7. Aggregate model-quality controls

```latex
MeanClientBA
=
\frac{1}{K_a}
\sum_{k=1}^{K_a} BA_k
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-161 — III / source lines 5300–5304

**Context:** 8. Threshold-estimation metrics

```latex
AbsoluteThresholdError
=
|\tau-\tau_{\mathrm{oracle}}|
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-162 — III / source lines 5306–5314

**Context:** 8. Threshold-estimation metrics

```latex
RelativeThresholdError
=
\frac{
|\tau-\tau_{\mathrm{oracle}}|
}{
|\tau_{\mathrm{oracle}}|
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-163 — III / source lines 5322–5324

**Context:** 8. Threshold-estimation metrics

```latex
TargetExceedance = 1-q
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-164 — III / source lines 5326–5330

**Context:** 8. Threshold-estimation metrics

```latex
SignedAttainmentError
=
AchievedBenignExceedance-(1-q)
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-165 — III / source lines 5332–5336

**Context:** 8. Threshold-estimation metrics

```latex
AbsoluteAttainmentError
=
|SignedAttainmentError|
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-166 — III / source lines 5344–5346

**Context:** 8. Threshold-estimation metrics

```latex
\bar\tau_{s,k,m}=\frac{1}{R}\sum_{r=1}^{R}\tau_{s,k,m,r},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-167 — III / source lines 5348–5351

**Context:** 8. Threshold-estimation metrics

```latex
ThresholdVariance_{s,k,m}
=\frac{1}{R-1}\sum_{r=1}^{R}(\tau_{s,k,m,r}-\bar\tau_{s,k,m})^2,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-168 — III / source lines 5353–5355

**Context:** 8. Threshold-estimation metrics

```latex
ThresholdSD_{s,k,m}=\sqrt{ThresholdVariance_{s,k,m}}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-169 — III / source lines 5388–5396

**Context:** 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

```latex
\mu_{global}
=
\frac{
\sum_k n_k\mu_k
}{
\sum_k n_k
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-170 — III / source lines 5400–5408

**Context:** 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

```latex
within
=
\frac{
\sum_k n_k\sigma_k^2
}{
\sum_k n_k
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-171 — III / source lines 5410–5418

**Context:** 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

```latex
between
=
\frac{
\sum_k n_k(\mu_k-\mu_{global})^2
}{
\sum_k n_k
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-172 — III / source lines 5420–5422

**Context:** 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

```latex
\sigma^2_{global}=within+between
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-173 — III / source lines 5428–5432

**Context:** 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics

```latex
between\_ratio
=
\frac{between}{within+between}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-174 — III / source lines 5446–5452

**Context:** 10. Operational metrics

```latex
Alerts_{k,day}
=
FPR_k
\times
BenignDecisions_{k,day}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-175 — III / source lines 5494–5500

**Context:** 11. Confirmatory statistical analysis

```latex
\Delta_s
=
CV(FPR)_{\mathrm{shared},s}
-
CV(FPR)_{\mathrm{local},s}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-176 — III / source lines 5504–5509

**Context:** 11. Confirmatory statistical analysis

```latex
\overline{\Delta}
=
\frac{1}{10}
\sum_{s=1}^{10}\Delta_s
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-177 — III / source lines 5517–5520

**Context:** 11. Confirmatory statistical analysis

```latex
RelativeCVReduction_s
=\frac{CV(FPR)_{\mathrm{shared},s}-CV(FPR)_{\mathrm{local},s}}{CV(FPR)_{\mathrm{shared},s}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-178 — III / source lines 5526–5529

**Context:** 11. Confirmatory statistical analysis

```latex
DeltaWorstFPR_s
=\max_k FPR_{shared,s,k}-\max_k FPR_{local,s,k},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-179 — III / source lines 5531–5534

**Context:** 11. Confirmatory statistical analysis

```latex
DeltaIQR_s
=IQR(FPR)_{shared,s}-IQR(FPR)_{local,s}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-180 — III / source lines 5557–5565

**Context:** 11. Confirmatory statistical analysis

```latex
SignConsistency
=
\frac{
|\{s:\Delta_s>0\}|
}{
10
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-181 — III / source lines 5587–5593

**Context:** 12. Secondary statistical evidence

```latex
p_{sign}
=\min\left(1,
2\sum_{x=0}^{\min(n_{positive},n_{negative})}
{n_{nonzero}\choose x}2^{-n_{nonzero}}
\right).
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-182 — III / source lines 5685–5689

**Context:** 14. Temporal recalibration quantities

```latex
drift\_excess
=
frozen\_future\_cv-static\_reference\_cv
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-183 — III / source lines 5691–5695

**Context:** 14. Temporal recalibration quantities

```latex
recovered\_amount
=
frozen\_future\_cv-recalibrated\_future\_cv
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-184 — III / source lines 5697–5705

**Context:** 14. Temporal recalibration quantities

```latex
recovery\_ratio
=
\frac{
recovered\_amount
}{
drift\_excess
}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-185 — III / source lines 5727–5729

**Context:** 14. Temporal recalibration quantities

```latex
DeltaTau_k=\tau_{k,recalibrated}-\tau_{k,historical},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-186 — III / source lines 5731–5733

**Context:** 14. Temporal recalibration quantities

```latex
FrozenFPRDeterioration_k=FPR_{k,frozen}-FPR_{k,static},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-187 — III / source lines 5735–5737

**Context:** 14. Temporal recalibration quantities

```latex
RecoveryFPR_k=FPR_{k,frozen}-FPR_{k,recalibrated}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-188 — III / source lines 5751–5753

**Context:** 15. Precision and selection discipline

```latex
SE_{proxy}=\frac{s_\Delta}{\sqrt{10}},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-189 — III / source lines 5757–5759

**Context:** 15. Precision and selection discipline

```latex
H_{normal}=1.96\,SE_{proxy}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-190 — III / source lines 5765–5767

**Context:** 15. Precision and selection discipline

```latex
BCaWidth=U_{BCa}-L_{BCa}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-191 — III / source lines 5771–5774

**Context:** 15. Precision and selection discipline

```latex
\overline\Delta_{(-j)}
=\frac{1}{9}\sum_{s\ne j}\Delta_s,
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-192 — III / source lines 5776–5779

**Context:** 15. Precision and selection discipline

```latex
MaxLOSOShift
=\max_j|\overline\Delta_{(-j)}-\overline\Delta|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-193 — III / source lines 5795–5798

**Context:** 15. Precision and selection discipline

```latex
Delta_{s,-j}
=CV(FPR)_{shared,s,-j}-CV(FPR)_{local,s,-j}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-194 — III / source lines 5802–5804

**Context:** 15. Precision and selection discipline

```latex
\overline{Delta}_{-j}=\frac{1}{10}\sum_{s=1}^{10}Delta_{s,-j}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-195 — III / source lines 5808–5812

**Context:** 15. Precision and selection discipline

```latex
MinLODOMean=\min_j \overline{Delta}_{-j},
\qquad
MaxLODOMean=\max_j \overline{Delta}_{-j},
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-196 — III / source lines 5814–5816

**Context:** 15. Precision and selection discipline

```latex
MaxLODOShift=\max_j|\overline{Delta}_{-j}-\overline{Delta}|.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-197 — III / source lines 5827–5830

**Context:** 15. Precision and selection discipline

```latex
RelativeMaxLODOShift
=\frac{MaxLODOShift}{|\overline{Delta}|}.
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

### FORMULA-198 — III / source lines 5902–5904

**Context:** 16. Mandatory manuscript-facing figures and synthesis tables

```latex
\Delta_s=CV(FPR)_{shared,s}-CV(FPR)_{local,s}
```

| Expected implementation | Disposition | Audit | Tests/evidence |
|---|---|---|---|
| map to the single owning scientific function/value object; preserve denominator, inequality, ddof, clipping/unavailability semantics and nesting exactly | `NOT_AUDITED` | — | — |

## 4. Complete literal / grid / enum / pseudocode ledger

**Extraction count:** `93` fenced blocks. These capture locked identifiers, factor grids, states, procedures, release layouts, and code-facing constants that formulas alone do not capture.

### LITERAL-001 — Part PREAMBLE, source lines 40–55

**Context:** Descriptive naming amendment

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-002 — Part I, source lines 215–217

**Context:** 2.2.2 Fixed-score identity and serialization tolerance

```text
threshold_calibration_scope
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-003 — Part I, source lines 221–226

**Context:** 2.2.2 Fixed-score identity and serialization tolerance

```text
shared
physical_device_family
data_driven_client_cluster
individual_client
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-004 — Part I, source lines 307–309

**Context:** 3. Calibration and evaluation contract

```text
n_k_source >= 100
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-005 — Part I, source lines 325–335

**Context:** 3. Calibration and evaluation contract

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-006 — Part I, source lines 384–386

**Context:** 3. Calibration and evaluation contract

```text
CV(FPR) across eligible clients
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-007 — Part I, source lines 441–443

**Context:** 4. Threshold-policy system

```text
q = 0.95
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-008 — Part I, source lines 455–457

**Context:** 4. Threshold-policy system

```text
q = 0.95
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-009 — Part I, source lines 486–491

**Context:** 4. Threshold-policy system

```text
mean(error)
standard_deviation(error)
skewness(error)
p95(error)
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-010 — Part I, source lines 495–497

**Context:** 4. Threshold-policy system

```text
K = 3
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-011 — Part I, source lines 517–522

**Context:** 4. Threshold-policy system

```text
SHARED_THRESHOLD: one threshold for the federation
FAMILY_THRESHOLD: one threshold per physical-device family
CLUSTER_THRESHOLD: one threshold per data-driven client cluster
LOCAL_THRESHOLD: one threshold per individual client
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-012 — Part I, source lines 540–542

**Context:** 5. Supportive threshold variants

```text
q = 0.95
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-013 — Part I, source lines 554–556

**Context:** 5. Supportive threshold variants

```text
MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-014 — Part I, source lines 580–583

**Context:** 5. Supportive threshold variants

```text
estimator in {TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR}
scope     in {SHARED, LOCAL}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-015 — Part I, source lines 673–675

**Context:** 5. Supportive threshold variants

```text
alpha = 1 - q
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-016 — Part I, source lines 724–734

**Context:** 6. Federated threshold comparator

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-017 — Part I, source lines 795–797

**Context:** 7. Training-side stress tests

```text
mu in {0.001, 0.01, 0.1, 1.0}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-018 — Part I, source lines 877–880

**Context:** 7. Training-side stress tests

```text
lambda_D in {0.1, 1.0, 2.0}
canonical_lambda_D = 1.0
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-019 — Part I, source lines 904–916

**Context:** 7. Training-side stress tests

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-020 — Part I, source lines 946–948

**Context:** 7. Training-side stress tests

```text
(dataset_id, population_id, training_seed, client_id)
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-021 — Part I, source lines 1043–1051

**Context:** 7. Training-side stress tests

```text
X in {
  ModelAlignmentH,
  LocationDispersion,
  ScaleDispersion,
  LocalThresholdDispersion,
  NormalizedSharedLocalThresholdDistance
}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-022 — Part I, source lines 1073–1078

**Context:** 7. Training-side stress tests

```text
ScopeAbsorption <= 0.25          RETAINED_STRONGLY
0.25 < ScopeAbsorption <= 0.75   PARTIALLY_ABSORBED
0.75 < ScopeAbsorption <= 1.00   LARGELY_ABSORBED
ScopeAbsorption > 1.00           REVERSED_SHARED_LOCAL_ORDERING
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-023 — Part I, source lines 1084–1094

**Context:** 7. Training-side stress tests

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-024 — Part I, source lines 1098–1103

**Context:** 7. Training-side stress tests

```text
upstream client adaptation
    -> lower benign-score heterogeneity / dispersion
    -> smaller shared-to-local threshold mismatch
    -> smaller SHARED_THRESHOLD-to-LOCAL_THRESHOLD FPR-equity gain
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-025 — Part I, source lines 1111–1114

**Context:** 7. Training-side stress tests

```text
FedRep-AE
FedPer-AE
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-026 — Part I, source lines 1275–1281

**Context:** 9. Dataset and population boundaries

```text
OBSERVED
MANIPULATED
STRESS_TESTED
BOUNDARY_ONLY
EXCLUDED
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-027 — Part I, source lines 1442–1444

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
DATP
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-028 — Part I, source lines 1450–1452

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
DATP-Core
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-029 — Part I, source lines 1458–1460

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
anchor
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-030 — Part I, source lines 1470–1476

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
CENTRALIZED_REFERENCE
SHARED_THRESHOLD
LOCAL_THRESHOLD
FAMILY_THRESHOLD
CLUSTER_THRESHOLD
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-031 — Part I, source lines 1492–1498

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
LOCAL_GLOBAL_SHRINKAGE
CALIBRATION_SIZE_AWARE_SHRINKAGE
LOCAL_CONFORMAL_THRESHOLD
FEDERATED_BENIGN_SUMMARY_THRESHOLD
FEDERATED_KLL_SHARED_THRESHOLD
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-032 — Part I, source lines 1506–1508

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
FEDERATED_BENIGN_SUMMARY_THRESHOLD
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-033 — Part I, source lines 1514–1516

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
LARIDI_ANOMALY_INFORMED_REFERENCE
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-034 — Part I, source lines 1528–1531

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
FedRep-AE
FedPer-AE
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-035 — Part I, source lines 1535–1539

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
personalized model v2
local personalized baseline
hybrid personalization
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-036 — Part I, source lines 1551–1557

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
NBAIOT_NATURAL_DEVICES
CICIOT_FILE_CLIENTS
NBAIOT_DIRICHLET_CLIENTS
EDGE_SENSOR_CLIENTS
EDGE_TEMPORAL_CLIENTS
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-037 — Part I, source lines 1563–1565

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-038 — Part I, source lines 1571–1578

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
CV(FPR)
IQR(FPR)
worst-client FPR
false-alarm equity
operating-point equity
cross-client FPR dispersion
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-039 — Part I, source lines 1582–1589

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
fair model
fair detector
equal treatment
privacy-preserving threshold
robust threshold
optimal threshold
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-040 — Part I, source lines 1730–1740

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-041 — Part I, source lines 1748–1760

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-042 — Part I, source lines 1806–1822

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-043 — Part I, source lines 1841–1855

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-044 — Part I, source lines 1859–1874

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-045 — Part I, source lines 1878–1884

**Context:** 10. Scope, terminology, claim boundaries, and accepted limitations

```text
YES
NO
PARTIAL
NOT_APPLICABLE
NOT_REPORTED
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-046 — Part II, source lines 2157–2162

**Context:** 2. Protocol inheritance and experiment-wide execution additions

```text
seed_material = "DATP-Core|" + purpose + "|" + "|".join(identity_parts)
digest = SHA256(UTF8(seed_material))
seed32 = int.from_bytes(digest[0:8], byteorder="big", signed=False) mod 2^32
rng = numpy.random.Generator(numpy.random.PCG64(seed32))
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-047 — Part II, source lines 2166–2169

**Context:** 2. Protocol inheritance and experiment-wide execution additions

```text
purpose = "CALIBRATION_SUBSAMPLE"
identity_parts = [dataset_id, population_id, str(training_seed), client_id, str(replicate_index)]
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-048 — Part II, source lines 2366–2368

**Context:** 4. Dataset populations and evaluation settings

```text
alpha in {0.1, 0.3, 0.5, 1.0, 10.0, IID}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-049 — Part II, source lines 2411–2421

**Context:** 4. Dataset populations and evaluation settings

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-050 — Part II, source lines 2478–2483

**Context:** 4. Dataset populations and evaluation settings

```text
historical training       55%
historical calibration    15%
future recalibration      10%
future evaluation         20%
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-051 — Part II, source lines 2633–2639

**Context:** 5. Confirmatory experiment

```text
reference 95% BCa interval = [0.647, 0.769]
reference interval width   = 0.122
maximum width multiplier   = 1.20
maximum exact reproduced interval width = 1.20 x 0.122 = 0.1464
display-only three-decimal value = 0.147
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-052 — Part II, source lines 2679–2681

**Context:** 5. Confirmatory experiment

```text
anchor reproduction -> anchor verification -> anchor acceptance verdict -> permission or prohibition to continue
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-053 — Part II, source lines 2766–2768

**Context:** 6. Supportive robustness experiments

```text
q in {0.90, 0.95, 0.975, 0.99}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-054 — Part II, source lines 2805–2808

**Context:** 6. Supportive robustness experiments

```text
estimator = {TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR}
scope     = {SHARED, LOCAL}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-055 — Part II, source lines 3185–3191

**Context:** 7. Cluster and family mechanism programme

```text
alpha in {0.1, 1.0, IID}
m in {50, 100, 500, full}
policies = {SHARED_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD, fixed-lambda curve, size-aware shrinkage}
finite-m nested replicates = 10 per training seed
training seeds = the same ten-seed campaign cohort
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-056 — Part II, source lines 3212–3215

**Context:** 7. Cluster and family mechanism programme

```text
minimize CV(FPR)
maximize P10 Macro-F1
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-057 — Part II, source lines 3229–3234

**Context:** 7. Cluster and family mechanism programme

```text
UNIQUE_<POLICY_ID>          # exactly one nondominated policy
MULTIPLE_NONDOMINATED      # two or more nondominated policies
UNAVAILABLE_NO_VALID_CV    # CV(FPR) is unavailable on the common population
UNAVAILABLE_NO_COMMON_ATTACK_UTILITY  # P10 Macro-F1 unavailable on the common population
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-058 — Part II, source lines 3427–3433

**Context:** 7. Cluster and family mechanism programme

```text
PARETO_IMPROVED:              FPRRelief > 0 and TPRChange >= 0
PARETO_HARMED:                FPRRelief < 0 and TPRChange <= 0
TRADEOFF_FPR_BETTER_TPR_WORSE: FPRRelief > 0 and TPRChange < 0
TRADEOFF_FPR_WORSE_TPR_BETTER: FPRRelief < 0 and TPRChange > 0
NO_FPR_CHANGE:                FPRRelief = 0   # TPR direction remains separately reported
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-059 — Part II, source lines 3481–3485

**Context:** 7. Cluster and family mechanism programme

```text
LOW_SUPPORT  = SupportScore ranks 1..3
MID_SUPPORT  = SupportScore ranks 4..6
HIGH_SUPPORT = SupportScore ranks 7..9
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-060 — Part II, source lines 3566–3577

**Context:** 7. Cluster and family mechanism programme

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-061 — Part II, source lines 3591–3594

**Context:** 7. Cluster and family mechanism programme

```text
x = mean seed-level CV(FPR)          # lower is better
y = mean seed-level WorstBA         # higher is better
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-062 — Part II, source lines 3624–3626

**Context:** 8. Calibration robustness programme

```text
m in {50, 100, 250, 500, 1000, 5000}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-063 — Part II, source lines 3632–3634

**Context:** 8. Calibration robustness programme

```text
n_k_source >= m
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-064 — Part II, source lines 3729–3733

**Context:** 8. Calibration robustness programme

```text
target calibration m in {0, 10, 25, 50, 100}
10 deterministic nested replicates for m in {10, 25, 50, 100}
m = 0 has no subsampling replicate
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-065 — Part II, source lines 3767–3769

**Context:** 8. Calibration robustness programme

```text
lambda in {0.00, 0.25, 0.50, 0.75, 1.00}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-066 — Part II, source lines 3854–3857

**Context:** 8. Calibration robustness programme

```text
FEDERATED_CLIENT_LOCAL_STANDARD   # confirmatory protocol
FEDERATED_POOLED_MIN_MAX         # supportive alternative
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-067 — Part II, source lines 3913–3920

**Context:** 8. Calibration robustness programme

```text
omitted_shared_contributors m in {0,1,2,3,4}
minimum_remaining_shared_contributors = 5
subset rule = exhaustive over every subset U subset E_s with |U|=m
q = 0.95, type-7, unchanged
local thresholds = unchanged for all eligible clients
shared-threshold evaluation population = all E_s, including omitted contributors
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-068 — Part II, source lines 4019–4021

**Context:** 9. Federated threshold-estimation programme

```text
1 - q
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-069 — Part II, source lines 4074–4082

**Context:** 9. Federated threshold-estimation programme

```text
q = 0.95 canonical
k = 400 canonical
k sensitivity = {200, 800}
KLL input = float64 benign calibration scores
one sketch per eligible client
server merge = all eligible client sketches for the condition
one shared threshold = merged_sketch.quantile(q)
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-070 — Part II, source lines 4122–4124

**Context:** 9. Federated threshold-estimation programme

```text
k in {2.0, 2.5, 3.0}
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-071 — Part II, source lines 4225–4230

**Context:** 11. Training-side stress tests

```text
FedAvg reference
  -> FedProx: heterogeneity-aware global optimization
  -> FEDAVG_LOCAL_FINE_TUNING: simple client-local post-training adaptation
  -> Ditto: persistent regularized personalized models during FL
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-072 — Part II, source lines 4354–4361

**Context:** 11. Training-side stress tests

```text
lambda_D in {0.1, 1.0, 2.0}
canonical_lambda_D = 1.0
personalized_local_epochs_per_round = 1
persistent personalized state = required
personalized states aggregated = forbidden
global Ditto path = same FedAvg global-training protocol as the reference
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-073 — Part II, source lines 4490–4492

**Context:** 11. Training-side stress tests

```text
OBSERVED_ALIGNMENT_ACTIVATION
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-074 — Part II, source lines 4496–4498

**Context:** 11. Training-side stress tests

```text
NO_OBSERVED_ALIGNMENT_ACTIVATION
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-075 — Part II, source lines 4663–4665

**Context:** 13. Operational translation

```text
benign decisions or flows per device per unit time
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-076 — Part II, source lines 4724–4730

**Context:** 13. Operational translation

```text
warm-up iterations = 5
measured iterations = 20
timer = monotonic high-resolution timer (`perf_counter_ns` equivalent)
reported runtime = median, IQR, and p95 over measured iterations
unit = milliseconds
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-077 — Part III, source lines 5019–5023

**Context:** 4. Per-client metrics

```text
H_TAUTOLOGY:
The apparent LOCAL_THRESHOLD FPR benefit is produced trivially because the
same benign observations used to estimate q95 are also used to measure FPR.
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-078 — Part III, source lines 5100–5102

**Context:** 5. Cross-client operating-point metrics

```text
ddof = 1
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-079 — Part III, source lines 5123–5125

**Context:** 5. Cross-client operating-point metrics

```text
CV(FPR) = undefined
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-080 — Part III, source lines 5233–5248

**Context:** 6. Optional equity metrics

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-081 — Part III, source lines 5579–5583

**Context:** 12. Secondary statistical evidence

```text
n_positive = count(Delta_s > 0)
n_negative = count(Delta_s < 0)
n_nonzero  = n_positive + n_negative
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-082 — Part III, source lines 5713–5715

**Context:** 14. Temporal recalibration quantities

```text
recovery_ratio = undefined
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-083 — Part III, source lines 5820–5823

**Context:** 15. Precision and selection discipline

```text
positive_direction_retention = count_j(mean_Delta_-j > 0) / 9
nonpositive_omissions = all device IDs with mean_Delta_-j <= 0
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-084 — Part III, source lines 5836–5840

**Context:** 15. Precision and selection discipline

```text
LODO_HIGH_INFLUENCE =
    any(mean_Delta_-j <= 0)
    OR (RelativeMaxLODOShift >= 0.25, when defined)
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-085 — Part III, source lines 5870–5884

**Context:** 16. Mandatory manuscript-facing figures and synthesis tables

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-086 — Part III, source lines 5888–5894

**Context:** 16. Mandatory manuscript-facing figures and synthesis tables

```text
preprocessing sensitivity -> fitted preprocessing / detector geometry
FedProx + local fine-tuning + Ditto -> training / detector geometry
Komadina-style estimator axis + q95-vs-moment sensitivity -> threshold estimator
DATP core ladder           -> threshold-calibration scope ONLY
one-shot recalibration     -> calibration evidence at a later genuine-time window
```

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-087 — Part III, source lines 5912–5924

**Context:** 16. Mandatory manuscript-facing figures and synthesis tables

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

**Audit:** `NOT_AUDITED` — every code-facing identity/value/state represented here must either exist exactly, be explicitly unavailable, or be demonstrably non-executable narrative text.

### LITERAL-088 — Part IV, source lines 5961–5966

**Context:** 1. Purpose and audit semantics

```text
PASS
FAIL
NOT_APPLICABLE
UNAVAILABLE_AS_SPECIFIED
```

**Audit:** `PASS` — `tools/reproducibility/audit.py:AuditStatus` declares exactly these four statuses; `tests/unit/artifacts/test_audit.py` round-trips and validates them.

### LITERAL-089 — Part IV, source lines 5976–5988

**Context:** 2. Audit object identity

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

**Audit:** `PASS` — persisted evaluation documents retain the complete execution coordinate, and `tools/reproducibility/release.py:_release_artifact_from_document` derives release metadata from it; `tests/unit/artifacts/test_release.py` rejects missing persisted coordinates.

### LITERAL-090 — Part IV, source lines 6271–6288

**Context:** 20A. Reproducibility-release bundle

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

**Audit:** `PASS` — `tools/reproducibility/release.py` locks the required root files/directories and validates their exact inventory; `tests/unit/artifacts/test_release.py::test_release_validation_accepts_complete_exact_inventory` covers the payload.

### LITERAL-091 — Part IV, source lines 6301–6312

**Context:** 20A. Reproducibility-release bundle

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

**Audit:** `PASS` — `tools/reproducibility/release.py:_MANIFEST_COLUMNS` defines the exact fields and rejects malformed/ambiguous metadata during release validation.

### LITERAL-092 — Part IV, source lines 6359–6373

**Context:** 20A. Reproducibility-release bundle

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

**Audit:** `PASS` — `tools/reproducibility/release.py` captures the required runtime/dependency metadata, including explicit `NA` values where unavailable; `tests/unit/artifacts/test_release.py::test_release_builder_packages_explicit_retained_evidence_and_validates_it` verifies the emitted fields.

### LITERAL-093 — Part IV, source lines 6379–6383

**Context:** 20A. Reproducibility-release bundle

```text
PUBLIC
BLINDED_ARCHIVE
WITHHELD_LICENSE_RESTRICTED
```

**Audit:** `PASS` — `tools/reproducibility/release.py:ReleaseState` permits exactly the locked states and validation enforces the restricted-release provenance record; unit release tests cover public, blinded, and license-restricted releases.

## 5. Dataset and population capability matrix

| Population | Client identity | Locked client count | Natural physical-device claim valid? | FPR-equity metrics | Per-client attack metrics | Genuine chronology | Primary evidence role |
|---|---|---:|---|---|---|---|---|
| `NBAIOT_NATURAL_DEVICES` | original commercial IoT device | `9` | **Yes** | **Yes** | **Yes**, subject to held-out family support | **No genuine-time claim** from source-row ordering | sole confirmatory + principal mechanism |
| `CICIOT_FILE_CLIENTS` | processed CSV file pseudo-client | `63` | **No** | **Yes** | **Not authorized for DATP claims** | **No** | applicability boundary |
| `NBAIOT_DIRICHLET_CLIENTS` | synthetic Dirichlet client | `20` | **No** | **Yes** | **Yes**, where source attack support remains valid | **No** | controlled heterogeneity sensitivity |
| `EDGE_SENSOR_CLIENTS` | benign sensor-group folder | `10` | **No physical-device claim** | **Yes** | **No** — valid per-client attack assignment unavailable | **No** | independent external benign-equity validation |
| `EDGE_TEMPORAL_CLIENTS` | timestamp-valid sensor-group folder | `9` | **No physical-device claim** | **Yes** | **No** — temporal experiment is benign-only | **Yes** | one-shot temporal boundary |

### 5.1 Dataset/population implementation audit

| Requirement | Expected implementation | Disposition | Audit |
|---|---|---|---|
| NBAIOT_NATURAL_DEVICES preserves exactly nine physical-device clients and is the sole confirmatory population. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| CICIOT_FILE_CLIENTS preserves file-defined pseudo-client semantics only; no inferred physical-device provenance. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| NBAIOT_DIRICHLET_CLIENTS uses 20 synthetic clients and remains controlled sensitivity evidence. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| EDGE_SENSOR_CLIENTS uses the audited static sensor-group definition and permits benign FPR-equity outcomes only. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| EDGE_TEMPORAL_CLIENTS uses timestamp-valid groups only and genuine chronology. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| FAMILY_THRESHOLD is unavailable when no defensible physical-family taxonomy exists. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| Attack-sensitive metrics on Edge client populations remain typed unavailable where Part II/III prohibit assignment. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |
| No extra dataset may be added without a roadmap amendment. | datasets/populations + validation + experiment planner | `NOT_AUDITED` | — |

## 6. Complete experiment / analysis catalogue

**Master-index count:** `36` rows. Every row below maps to the exact Part II section and receives an immutable descriptive experiment ID.

| Experiment ID | Part II section | Role | Population | Main variation | Mandatory | Source lines | Disposition | Audit |
|---|---|---|---|---|---|---|---|---|
| `EXPERIMENT-SHARED-VERSUS-LOCAL-THRESHOLD-SCOPE-CONFIRMATION` | §5.1 | Confirmatory | N-BaIoT natural devices | SHARED_THRESHOLD vs LOCAL_THRESHOLD | `YES` | 2512–2626 | `NOT_AUDITED` | — |
| `EXPERIMENT-ANCHOR-REPRODUCTION-GATE` | §5.2 | Reproducibility gate | historical N-BaIoT five-seed anchor | reproduction acceptance | `YES` | 2627–2682 | `NOT_AUDITED` | — |
| `EXPERIMENT-SHARED-THRESHOLD-CONSTRUCTION-SENSITIVITY` | §6.1 | Supportive | N-BaIoT natural devices | SHARED_THRESHOLD vs pooled / weighted shared constructions | `YES` | 2708–2753 | `NOT_AUDITED` | — |
| `EXPERIMENT-QUANTILE-LEVEL-SENSITIVITY` | §6.2 | Supportive | N-BaIoT natural devices | `q={0.90,0.95,0.975,0.99}` | `YES` | 2754–2785 | `NOT_AUDITED` | — |
| `EXPERIMENT-THRESHOLD-ESTIMATOR-SCOPE-SENSITIVITY` | §6.2A | Supportive | N-BaIoT natural devices | `{TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR} x {SHARED,LOCAL}` | `YES` | 2786–2857 | `NOT_AUDITED` | — |
| `EXPERIMENT-CONTROLLED-NON-IID-SEVERITY` | §6.3 | Supportive | controlled N-BaIoT partitions | heterogeneity severity | `YES` | 2858–2920 | `NOT_AUDITED` | — |
| `EXPERIMENT-THRESHOLD-SHARING-GRANULARITY-AND-CLUSTER-STABILITY` | §7.1 | Mechanism | N-BaIoT natural devices | SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD + cluster stability | `YES` | 2923–3031 | `NOT_AUDITED` | — |
| `EXPERIMENT-PHYSICAL-FAMILY-EXPLANATORY-ADEQUACY` | §7.2A | Mechanism | N-BaIoT natural devices | within/between-family geometry | `YES` | 3032–3073 | `NOT_AUDITED` | — |
| `EXPERIMENT-PER-CLIENT-SCORE-DISTRIBUTION-EXPLANATION` | §7.3 | Mechanism | N-BaIoT natural devices | benign/attack score geometry | `YES` | 3074–3103 | `NOT_AUDITED` | — |
| `EXPERIMENT-HETEROGENEITY-BENEFIT-ASSOCIATION-AND-DECISION-SURFACE` | §7.4 | Mechanism | natural + controlled N-BaIoT evidence | JS heterogeneity × calibration support | `YES` | 3104–3243 | `NOT_AUDITED` | — |
| `EXPERIMENT-THRESHOLD-MOVEMENT-VERSUS-OPERATING-POINT-HARM` | §7.5 | Mechanism | N-BaIoT natural devices | threshold movement vs FPR/TPR changes + exact device-direction counts | `YES` | 3244–3301 | `NOT_AUDITED` | — |
| `EXPERIMENT-CALIBRATION-SUPPORT-VERSUS-SHARED-THRESHOLD-BURDEN` | §7.5A | Descriptive mechanism diagnostic | N-BaIoT natural devices | source benign-calibration support vs shared FPR and local-personalization relief | `YES` | 3302–3365 | `NOT_AUDITED` | — |
| `EXPERIMENT-NATURAL-DEVICE-HELPED-HARMED-PROFILE-SUPPORT-STRATA` | §7.5B | Mandatory client-impact mechanism diagnostic | N-BaIoT natural devices | exact per-device help/harm/Pareto directions + campaign-fixed 3/3/3 support strata | `YES` | 3366–3512 | `NOT_AUDITED` | — |
| `EXPERIMENT-MALWARE-FAMILY-SENSITIVITY-BREAKDOWN` | §7.6 | Supportive trade-off | N-BaIoT natural devices | Mirai/BASHLITE attack-family outcomes | `YES` | 3513–3557 | `NOT_AUDITED` | — |
| `EXPERIMENT-EQUITY-UTILITY-PARETO-ANALYSIS` | §7.7 | Supportive synthesis | N-BaIoT natural devices | equity vs utility, no scalar winner | `YES` | 3558–3603 | `NOT_AUDITED` | — |
| `EXPERIMENT-CALIBRATION-SIZE-ABLATION` | §8.1 | Boundary/supportive | N-BaIoT natural devices | `m={50,100,250,500,1000,5000}` | `YES` | 3606–3718 | `NOT_AUDITED` | — |
| `EXPERIMENT-CALIBRATION-COLD-START-ONBOARDING-BOUNDARY` | §8.1A | Boundary | N-BaIoT natural devices | low-support onboarding | `YES` | 3719–3754 | `NOT_AUDITED` | — |
| `EXPERIMENT-FIXED-LOCAL-GLOBAL-SHRINKAGE` | §8.2 | Threshold variant | N-BaIoT natural devices | fixed λ curve | `YES` | 3755–3786 | `NOT_AUDITED` | — |
| `EXPERIMENT-CALIBRATION-SIZE-AWARE-SHRINKAGE` | §8.3 | Threshold variant | N-BaIoT natural devices | deterministic λ by `n_k_used` | `YES` | 3787–3804 | `NOT_AUDITED` | — |
| `EXPERIMENT-SPLIT-CONFORMAL-LOCAL-CONFORMAL-THRESHOLD-DIAGNOSTIC` | §8.4 | Threshold variant | N-BaIoT natural devices | finite-sample local coverage | `YES` | 3805–3845 | `NOT_AUDITED` | — |
| `EXPERIMENT-BOUNDED-PREPROCESSING-GEOMETRY-SENSITIVITY` | §8.5 | Supportive boundary | N-BaIoT natural devices | local StandardScaler vs pooled MinMax protocol identity | `YES` | 3846–3896 | `NOT_AUDITED` | — |
| `EXPERIMENT-SHARED-CALIBRATION-CONTRIBUTOR-AVAILABILITY` | §8.6 | Supportive operational sensitivity | N-BaIoT natural devices | exhaustive omission of `m={0,1,2,3,4}` shared-threshold contributors | `YES` | 3897–3989 | `NOT_AUDITED` | — |
| `EXPERIMENT-BENIGN-SUMMARY-STATISTICS-COMPARATOR` | §9.1 | Comparator | N-BaIoT natural devices | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | `YES` | 3992–4056 | `NOT_AUDITED` | — |
| `EXPERIMENT-KLL-FEDERATED-QUANTILE-SKETCH-THRESHOLD` | §9.2 | Comparator | N-BaIoT natural devices | KLL `k={200,400,800}` | `YES` | 4057–4113 | `NOT_AUDITED` | — |
| `EXPERIMENT-FIXED-COEFFICIENT-LARIDI-SENSITIVITY` | §9.3 | Optional supplement | N-BaIoT natural devices | fixed coefficient sensitivity only | `NO` | 4114–4129 | `NOT_AUDITED` | — |
| `EXPERIMENT-EDGE-IIOTSET-EXTERNAL-BENIGN-EQUITY-VALIDATION` | §10.1 | External validation | Edge-IIoTset | independent-dataset benign equity | `YES` | 4132–4194 | `NOT_AUDITED` | — |
| `EXPERIMENT-CICIOT2023-FILE-LEVEL-BOUNDARY` | §10.2 | Applicability boundary | CICIoT2023 file pseudo-clients | available-data boundary | `YES` | 4195–4218 | `NOT_AUDITED` | — |
| `EXPERIMENT-FEDPROX-AGGREGATION-MECHANISM-ACTIVATION-STRESS-TEST` | §11.1 | Training stress | N-BaIoT natural devices | FedProx μ grid + local-update drift diagnostics | `YES` | 4244–4319 | `NOT_AUDITED` | — |
| `EXPERIMENT-DITTO-MODEL-PERSONALIZATION-STRESS-TEST` | §11.2 | Model-personalization stress | N-BaIoT natural devices | Ditto λD grid / absorption | `YES` | 4320–4429 | `NOT_AUDITED` | — |
| `EXPERIMENT-FEDAVG-POST-TRAINING-CLIENT-LOCAL-FINE-TUNING` | §11.2A | Simple model-personalization stress | N-BaIoT natural devices | exactly 10 benign-training local epochs + common absorption diagnostics | `YES` | 4430–4501 | `NOT_AUDITED` | — |
| `EXPERIMENT-ONE-SHOT-RECALIBRATION-UNDER-GENUINE-CHRONOLOGY` | §12.1 | Temporal boundary | Edge-IIoTset temporal population | static vs frozen-future vs one-shot recalibration | `YES` | 4504–4646 | `NOT_AUDITED` | — |
| `EXPERIMENT-ALERT-BURDEN-EXPERIMENT` | §13.1 | Operational interpretation | valid rate-bearing population | alert-count translation | `YES` | 4649–4693 | `NOT_AUDITED` | — |
| `EXPERIMENT-THRESHOLD-STAGE-COMMUNICATION-STORAGE-RUNTIME-ACCOUNTIN` | §13.2 | Operational accounting | applicable methods | payload, storage, threshold-stage timing | `YES` | 4694–4737 | `NOT_AUDITED` | — |
| `EXPERIMENT-ROBUST-CLUSTER-MEDIAN-THRESHOLD` | §14.1 | Optional analysis | N-BaIoT natural devices | cluster median vs mean threshold | `NO` | 4742–4755 | `NOT_AUDITED` | — |
| `EXPERIMENT-ADDITIONAL-EQUITY-INDICES` | §14.2 | Optional analysis | applicable populations | Jain/Gini/IQR/range diagnostics | `NO` | 4756–4768 | `NOT_AUDITED` | — |
| `EXPERIMENT-EXTENDED-SECONDARY-UNCERTAINTY` | §14.3 | Optional analysis | applicable experiments | secondary paired uncertainty | `NO` | 4769–4779 | `NOT_AUDITED` | — |

## 7. Experiment-by-experiment implementation cards

Each card intentionally includes every Markdown list/procedure item found inside its authoritative Part II section, so required factors, procedures, outputs, interpretation constraints, and prohibitions are not reduced to the master index. **The card-level repository-mapping row is the experiment-integration mapping only.** It does not allow one generic owner to close all child requirements: each child scientific rule must be mapped to its single semantic owner under §0.5A, and prose-only constraints from the same source section must also be cross-checked against §15A.

### EXPERIMENT-SHARED-VERSUS-LOCAL-THRESHOLD-SCOPE-CONFIRMATION — Part II §5.1 Shared-versus-local threshold-scope confirmation

- **Role:** Confirmatory
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** SHARED_THRESHOLD vs LOCAL_THRESHOLD
- **Mandatory:** YES
- **Authoritative source:** lines 2512–2626
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2528` — NBAIOT_NATURAL_DEVICES;
- [ ] `2529` — nine physical-device clients;
- [ ] `2530` — ten paired training seeds;
- [ ] `2531` — one terminal scientific detector per seed;
- [ ] `2532` — benign calibration scores;
- [ ] `2533` — held-out benign and attack test scores;
- [ ] `2534` — unchanged eligibility.
- [ ] `2538` — autoencoder architecture;
- [ ] `2539` — FedAvg training;
- [ ] `2540` — local epochs `E = 1`;
- [ ] `2541` — full participation;
- [ ] `2542` — preprocessing;
- [ ] `2543` — terminal scientific-model rule;
- [ ] `2544` — quantile `q = 0.95`;
- [ ] `2545` — test records;
- [ ] `2546` — metric implementation;
- [ ] `2547` — historical temporal-gap data partition (per-device chronological source-row order, `60 / 1 / 20 / 1 / 18`, guard gaps discarded, scaler fit on training rows only).
- [ ] `2553` — SHARED_THRESHOLD shared threshold;
- [ ] `2554` — LOCAL_THRESHOLD per-client threshold.
- [ ] `2558` — Reproduce the locked five-seed subset using the journal implementation.
- [ ] `2559` — Apply the anchor reproduction gate (§5.2) to the reproduced five-seed result. Do not proceed to step 3 unless the gate emits an anchor-success verdict.
- [ ] `2560` — Extend execution to ten paired seeds.
- [ ] `2561` — For every seed, compute per-client FPR under SHARED_THRESHOLD and LOCAL_THRESHOLD.
- [ ] `2562` — Compute `CV(FPR)` over the same eligible clients.
- [ ] `2563` — Compute the paired seed-level contrast:
- [ ] `2573` — Report all ten seed-level contrasts.
- [ ] `2574` — Compute the locked 95% BCa confidence interval over the ten paired contrasts.
- [ ] `2575` — Report sign consistency and the exact paired sign-test diagnostic defined in Part III §12.1A.
- [ ] `2576` — Report IQR and max–min FPR alongside CV to guard against small-denominator distortion.
- [ ] `2577` — Report absolute paired changes in worst-client FPR and FPR IQR, plus the descriptive relative `CV(FPR)` reduction defined in Part III §11.1A.
- [ ] `2578` — Execute the leave-one-device-out influence diagnostic in Part III §15.1A using the already generated score artifacts; do not retrain or rescore.
- [ ] `2579` — Report detection-quality controls for NBAIOT_NATURAL_DEVICES without treating them as the primary verdict.
- [ ] `2583` — SHARED_THRESHOLD and LOCAL_THRESHOLD per-client FPR for every seed;
- [ ] `2584` — seed-level SHARED_THRESHOLD and LOCAL_THRESHOLD `CV(FPR)`;
- [ ] `2585` — ten paired deltas;
- [ ] `2586` — arithmetic-mean paired delta as the confirmatory point estimate, plus the descriptive median paired delta;
- [ ] `2587` — 95% BCa interval;
- [ ] `2588` — sign-consistency positive/zero/negative counts and exact paired sign-test p-value as secondary evidence;
- [ ] `2589` — IQR and range;
- [ ] `2590` — `DeltaWorstFPR`, `DeltaIQR`, and descriptive `RelativeCVReduction`;
- [ ] `2591` — complete leave-one-device-out `Delta_(s,-j)` values, per-device ten-seed mean, `MinLODOMean`, `MaxLODOMean`, `MaxLODOShift`, and positive-direction retention count;
- [ ] `2592` — Macro-F1, balanced accuracy, TPR, and P10 Macro-F1 controls;
- [ ] `2593` — complete nine-client result display.
- [ ] `2622` — no alteration of the terminal detector from this result;
- [ ] `2623` — no replacement by CLUSTER_THRESHOLD, shrinkage, or LOCAL_CONFORMAL_THRESHOLD if the endpoint fails;
- [ ] `2624` — no removal of unfavorable seeds;
- [ ] `2625` — no claim that LOCAL_THRESHOLD improves overall detection performance.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-ANCHOR-REPRODUCTION-GATE — Part II §5.2 Anchor reproduction gate

- **Role:** Reproducibility gate
- **Population/setting:** historical N-BaIoT five-seed anchor
- **Main variation:** reproduction acceptance
- **Mandatory:** YES
- **Authoritative source:** lines 2627–2682
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2647` — the exact historical five-seed cohort is used;
- [ ] `2648` — the historical anchor dataset identity is preserved;
- [ ] `2649` — the historical client population is preserved;
- [ ] `2650` — the historical preprocessing identity is preserved;
- [ ] `2651` — the historical training protocol is preserved;
- [ ] `2652` — the historical terminal-model semantics are preserved;
- [ ] `2653` — the historical scoring semantics are preserved;
- [ ] `2654` — the historical threshold semantics are preserved;
- [ ] `2655` — the historical eligibility semantics are preserved;
- [ ] `2656` — the historical metric definition is preserved;
- [ ] `2657` — the reproduced 95% BCa interval remains entirely positive;
- [ ] `2658` — the reproduced interval overlaps `[0.647, 0.769]`;
- [ ] `2659` — the reproduced interval width is `<= 0.1464`;
- [ ] `2660` — required artifact lineage, provenance, identity, serialization, and reload-validation gates pass.
- [ ] `2668` — blocks the ten-seed journal extension;
- [ ] `2669` — blocks downstream journal claim-generating execution;
- [ ] `2670` — requires investigation;
- [ ] `2671` — requires a successful anchor reproduction before proceeding;
- [ ] `2672` — is not overridden by supportive evidence;
- [ ] `2673` — is not overridden by external validation;
- [ ] `2674` — is not overridden by favorable alternative threshold methods;
- [ ] `2675` — is never relaxed after observing the result; the fourteen acceptance conditions above cannot be loosened post hoc.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-SHARED-THRESHOLD-CONSTRUCTION-SENSITIVITY — Part II §6.1 Shared-threshold construction sensitivity

- **Role:** Supportive
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** SHARED_THRESHOLD vs pooled / weighted shared constructions
- **Mandatory:** YES
- **Authoritative source:** lines 2708–2753
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2720` — SHARED_THRESHOLD arithmetic mean of local quantiles;
- [ ] `2721` — exact pooled benign type-7 quantile;
- [ ] `2722` — sample-weighted mean of eligible local type-7 quantiles;
- [ ] `2723` — `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`;
- [ ] `2724` — `FEDERATED_BENIGN_SUMMARY_THRESHOLD` with the locked matched-target construction;
- [ ] `2725` — LOCAL_THRESHOLD local quantiles.
- [ ] `2735` — compute the shared threshold;
- [ ] `2736` — evaluate all eligible clients;
- [ ] `2737` — compute `CV(FPR)`, IQR, range, and worst-client FPR;
- [ ] `2738` — calculate the paired difference relative to LOCAL_THRESHOLD;
- [ ] `2739` — report achieved pooled and per-client exceedance.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-QUANTILE-LEVEL-SENSITIVITY — Part II §6.2 Quantile-level sensitivity

- **Role:** Supportive
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** `q={0.90,0.95,0.975,0.99}`
- **Mandatory:** YES
- **Authoritative source:** lines 2754–2785
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2774` — compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and canonical CLUSTER_THRESHOLD;
- [ ] `2775` — evaluate on unchanged held-out test scores;
- [ ] `2776` — report mean FPR, `CV(FPR)`, IQR, range, worst-client FPR, TPR, and P10 Macro-F1;
- [ ] `2777` — report achieved benign exceedance against the target `1 - q`;
- [ ] `2778` — visualize the policy-by-quantile surface.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-THRESHOLD-ESTIMATOR-SCOPE-SENSITIVITY — Part II §6.2A Threshold-estimator × scope sensitivity

- **Role:** Supportive
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** `{TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR} x {SHARED,LOCAL}`
- **Mandatory:** YES
- **Authoritative source:** lines 2786–2857
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2798` — NBAIOT_NATURAL_DEVICES only;
- [ ] `2799` — the exact same ten frozen FedAvg detector/score artifacts as §5.1;
- [ ] `2800` — the same eligible clients, calibration records, evaluation rows, labels, and metric implementation;
- [ ] `2801` — no retraining, rescoring, calibration resampling, or windowed majority-vote stage.
- [ ] `2830` — load the canonical fixed calibration/test score artifact for each seed;
- [ ] `2831` — compute the four locked estimator/scope thresholds;
- [ ] `2832` — evaluate per-client FPR and attack-sensitive controls on the unchanged held-out evaluation scores;
- [ ] `2833` — compute `CV(FPR)`, IQR, range, worst-client FPR, held-out target/attainment diagnostics where a nominal target exists, and the calibration-generalization gap from Part III §4.8;
- [ ] `2834` — compute `Delta_scope[s,E]` for both estimator families and `Delta_estimator[s]`;
- [ ] `2835` — report all ten seeds; no estimator or seed may be omitted because it weakens the desired pattern.
- [ ] `2839` — all four threshold conditions per seed/client;
- [ ] `2840` — per-client FPR, TPR, balanced accuracy, and Macro-F1;
- [ ] `2841` — `CV(FPR)`, IQR, range, and worst-client FPR;
- [ ] `2842` — ten `Delta_scope[Q95]` values;
- [ ] `2843` — ten `Delta_scope[MEAN+SD]` values;
- [ ] `2844` — ten `Delta_estimator` values;
- [ ] `2845` — sign counts for each estimator's scope gain;
- [ ] `2846` — paired descriptive BCa interval for mean `Delta_scope[MEAN+SD]` when defined, explicitly secondary;
- [ ] `2847` — complete negative-result reporting when the moment estimator weakens or reverses the scope effect.
- [ ] `2851` — positive mean scope gain under both estimators: evidence that the calibration-scope phenomenon is not unique to q95;
- [ ] `2852` — positive q95 gain but null/opposite moment-rule gain: estimator-dependent scope effect;
- [ ] `2853` — stronger moment-rule gain: supportive robustness only, not permission to replace q95;
- [ ] `2854` — moment-rule failure or poor utility: report as a historical estimator limitation.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CONTROLLED-NON-IID-SEVERITY — Part II §6.3 Controlled non-IID severity

- **Role:** Supportive
- **Population/setting:** controlled N-BaIoT partitions
- **Main variation:** heterogeneity severity
- **Mandatory:** YES
- **Authoritative source:** lines 2858–2920
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2870` — NBAIOT_DIRICHLET_CLIENTS;
- [ ] `2871` — 20 synthetic clients;
- [ ] `2872` — Dirichlet severity grid:
- [ ] `2873` — `0.1`;
- [ ] `2874` — `0.3`;
- [ ] `2875` — `0.5`;
- [ ] `2876` — `1.0`;
- [ ] `2877` — `10.0`;
- [ ] `2878` — IID;
- [ ] `2879` — SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD;
- [ ] `2880` — ten paired seeds where feasible.
- [ ] `2886` — construct the partition using the locked seed and partition rule;
- [ ] `2887` — retain the pre-specified partition;
- [ ] `2888` — train a separate terminal `FEDAVG` detector for this `(training seed, heterogeneity severity)` cell under the fixed training protocol below — this includes IID as one severity condition in this grid; never share another severity's fitted preprocessing state, detector state, calibration scores, or evaluation scores;
- [ ] `2889` — compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD;
- [ ] `2890` — report heterogeneity diagnostics;
- [ ] `2891` — compute the SHARED_THRESHOLD–LOCAL_THRESHOLD `CV(FPR)` difference;
- [ ] `2892` — report uncertainty per alpha;
- [ ] `2893` — display seed distributions rather than only point estimates.
- [ ] `2907` — client sample-count distribution;
- [ ] `2908` — client benign-distribution divergence;
- [ ] `2909` — class or attack composition when valid;
- [ ] `2910` — eligible-client coverage;
- [ ] `2911` — pairwise or aggregate Jensen–Shannon divergence.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-THRESHOLD-SHARING-GRANULARITY-AND-CLUSTER-STABILITY — Part II §7.1 Threshold-sharing granularity and cluster stability

- **Role:** Mechanism
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD + cluster stability
- **Mandatory:** YES
- **Authoritative source:** lines 2923–3031
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `2931` — Does family or cluster threshold sharing recover part of LOCAL_THRESHOLD’s FPR-equity benefit?
- [ ] `2932` — How much calibration granularity is required?
- [ ] `2933` — Are CLUSTER_THRESHOLD client assignments stable across seeds and calibration samples?
- [ ] `2934` — Does cluster sharing provide a defensible middle ground between one global threshold and one threshold per client?
- [ ] `2938` — NBAIOT_NATURAL_DEVICES is mandatory;
- [ ] `2939` — EDGE_SENSOR_CLIENTS may include CLUSTER_THRESHOLD;
- [ ] `2940` — FAMILY_THRESHOLD remains NBAIOT_NATURAL_DEVICES only.
- [ ] `2944` — SHARED_THRESHOLD shared;
- [ ] `2945` — FAMILY_THRESHOLD family;
- [ ] `2946` — CLUSTER_THRESHOLD canonical `K = 3`;
- [ ] `2947` — LOCAL_THRESHOLD local;
- [ ] `2948` — exploratory CLUSTER_THRESHOLD cluster counts where mathematically feasible.
- [ ] `2952` — Build each client fingerprint from benign calibration errors only.
- [ ] `2953` — Standardize fingerprint dimensions using the locked rule.
- [ ] `2954` — Fit canonical k-means with locked initialization and seed handling.
- [ ] `2955` — Assign the cluster-level threshold.
- [ ] `2956` — Evaluate FPR equity and detection controls.
- [ ] `2957` — Repeat clustering across seeds and declared resamples.
- [ ] `2958` — compare assignments using adjusted Rand index.
- [ ] `2959` — compute within-cluster and across-cluster threshold and FPR dispersion.
- [ ] `2960` — display the client-to-cluster membership for every seed.
- [ ] `2961` — compare CLUSTER_THRESHOLD groupings against the device-family taxonomy descriptively without treating taxonomy agreement as the optimization target;
- [ ] `2962` — calculate Euclidean silhouette values in the standardized four-feature fingerprint space;
- [ ] `2963` — calculate within-cluster versus between-cluster benign-score JS divergence;
- [ ] `2964` — calculate per-client assignment-switch frequency after label alignment to the smallest training-seed value used in the campaign;
- [ ] `2965` — execute the four locked leave-one-fingerprint-feature-out ablations, each with `K=3` and otherwise identical clustering:
- [ ] `2966` — omit `mean(error)`;
- [ ] `2967` — omit `standard_deviation(error)`;
- [ ] `2968` — omit `skewness(error)`;
- [ ] `2969` — omit `p95(error)`.
- [ ] `3003` — SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD `CV(FPR)`;
- [ ] `3004` — worst-client FPR;
- [ ] `3005` — IQR and range;
- [ ] `3006` — FAMILY_THRESHOLD and CLUSTER_THRESHOLD recovery fractions relative to the SHARED_THRESHOLD–LOCAL_THRESHOLD gap;
- [ ] `3007` — within-cluster and across-cluster threshold/FPR dispersion;
- [ ] `3008` — within-cluster and between-cluster benign-score JS divergence;
- [ ] `3009` — mean silhouette and per-client silhouette values;
- [ ] `3010` — ARI across seed pairs or declared resamples;
- [ ] `3011` — complete membership assignments;
- [ ] `3012` — per-client switch frequency;
- [ ] `3013` — cluster sizes;
- [ ] `3014` — empty or singleton cluster diagnostics;
- [ ] `3015` — canonical-versus-leave-one-feature-out ARI, silhouette, `CV(FPR)`, and worst-client FPR for all four ablations;
- [ ] `3016` — detection-quality controls for NBAIOT_NATURAL_DEVICES.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-PHYSICAL-FAMILY-EXPLANATORY-ADEQUACY — Part II §7.2A Physical-family explanatory adequacy

- **Role:** Mechanism
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** within/between-family geometry
- **Mandatory:** YES
- **Authoritative source:** lines 3032–3073
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-PER-CLIENT-SCORE-DISTRIBUTION-EXPLANATION — Part II §7.3 Per-client score-distribution explanation

- **Role:** Mechanism
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** benign/attack score geometry
- **Mandatory:** YES
- **Authoritative source:** lines 3074–3103
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3088` — plot held-out benign reconstruction-error CDFs;
- [ ] `3089` — plot held-out attack reconstruction-error CDFs;
- [ ] `3090` — overlay SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD thresholds;
- [ ] `3091` — show each threshold’s benign exceedance and attack acceptance region;
- [ ] `3092` — identify clients with weak score separation;
- [ ] `3093` — include the pre-specified Ennio Doorbell deep dive;
- [ ] `3094` — retain all clients in supplementary panels.
- [ ] `3098` — one complete multi-client CDF figure;
- [ ] `3099` — one detailed Ennio Doorbell panel;
- [ ] `3100` — per-client threshold positions;
- [ ] `3101` — per-client FPR, TPR, balanced accuracy, and Macro-F1;
- [ ] `3102` — explanation of threshold movement without claiming causality beyond the plotted score geometry.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-HETEROGENEITY-BENEFIT-ASSOCIATION-AND-DECISION-SURFACE — Part II §7.4 Heterogeneity–benefit association and decision surface

- **Role:** Mechanism
- **Population/setting:** natural + controlled N-BaIoT evidence
- **Main variation:** JS heterogeneity × calibration support
- **Mandatory:** YES
- **Authoritative source:** lines 3104–3243
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3148` — calculate `H` from benign calibration scores only;
- [ ] `3149` — calculate the SHARED_THRESHOLD–LOCAL_THRESHOLD FPR-equity gain \(\Delta CV=CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}\);
- [ ] `3150` — plot both;
- [ ] `3151` — report Spearman correlation;
- [ ] `3152` — report all points, not only population means;
- [ ] `3153` — include leverage/influence diagnostics.
- [ ] `3161` — remove device `j` from the eligible calibration/evaluation population only;
- [ ] `3162` — do **not** retrain the detector, refit preprocessing, or regenerate scores;
- [ ] `3163` — rebuild the common 64-bin JSD grid from the pooled benign calibration scores of the remaining clients using the same quantile-edge rule above;
- [ ] `3164` — recompute `H_(s,-j)` on the remaining clients;
- [ ] `3165` — recompute the shared threshold from the remaining eligible clients and recompute `CV(FPR)_shared,(s,-j)` over those clients;
- [ ] `3166` — retain each remaining client's original local threshold and recompute `CV(FPR)_local,(s,-j)` over the same reduced client set;
- [ ] `3167` — compute

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-THRESHOLD-MOVEMENT-VERSUS-OPERATING-POINT-HARM — Part II §7.5 Threshold movement versus operating-point harm

- **Role:** Mechanism
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** threshold movement vs FPR/TPR changes + exact device-direction counts
- **Mandatory:** YES
- **Authoritative source:** lines 3244–3301
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3272` — threshold shift versus FPR change;
- [ ] `3273` — threshold shift versus TPR change;
- [ ] `3274` — device labels;
- [ ] `3275` — seed uncertainty;
- [ ] `3276` — all nine clients without filtering.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CALIBRATION-SUPPORT-VERSUS-SHARED-THRESHOLD-BURDEN — Part II §7.5A Calibration support versus shared-threshold burden

- **Role:** Descriptive mechanism diagnostic
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** source benign-calibration support vs shared FPR and local-personalization relief
- **Mandatory:** YES
- **Authoritative source:** lines 3302–3365
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3356` — all client `n_k_source` values;
- [ ] `3357` — a scatter plot with x=`log10(n_k_source)` and y=`FPR_shared` plus a second y=`PersonalizationRelief`; the log transform is visual only and does not change Spearman ranks;
- [ ] `3358` — the ten seed-level `rho` values for `support -> FPR_shared` and `support -> PersonalizationRelief`;
- [ ] `3359` — median, minimum, maximum, and counts of negative/zero/positive `rho` values across valid seeds;
- [ ] `3360` — a per-device table containing `n_k_source`, mean/median SHARED_THRESHOLD FPR across seeds, mean/median `SharedTargetBurden`, and mean/median `PersonalizationRelief`.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-NATURAL-DEVICE-HELPED-HARMED-PROFILE-SUPPORT-STRATA — Part II §7.5B Natural-device helped/harmed profile + support strata

- **Role:** Mandatory client-impact mechanism diagnostic
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** exact per-device help/harm/Pareto directions + campaign-fixed 3/3/3 support strata
- **Mandatory:** YES
- **Authoritative source:** lines 3366–3512
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-MALWARE-FAMILY-SENSITIVITY-BREAKDOWN — Part II §7.6 Malware-family sensitivity breakdown

- **Role:** Supportive trade-off
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** Mirai/BASHLITE attack-family outcomes
- **Mandatory:** YES
- **Authoritative source:** lines 3513–3557
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3548` — every available `TPR_{k,f}` and `FNR_{k,f}`;
- [ ] `3549` — `MacroFamilyTPR_f` for Mirai and BASHLITE separately;
- [ ] `3550` — `WorstFamilyClientTPR` and the exact `(client,family)` that attains it;
- [ ] `3551` — SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD differences;
- [ ] `3552` — the support count \(N_{k,f}\) for every reported value.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-EQUITY-UTILITY-PARETO-ANALYSIS — Part II §7.7 Equity–utility Pareto analysis

- **Role:** Supportive synthesis
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** equity vs utility, no scalar winner
- **Mandatory:** YES
- **Authoritative source:** lines 3558–3603
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CALIBRATION-SIZE-ABLATION — Part II §8.1 Calibration-size ablation

- **Role:** Boundary/supportive
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** `m={50,100,250,500,1000,5000}`
- **Mandatory:** YES
- **Authoritative source:** lines 3606–3718
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3642` — every compared threshold policy receives the same client cohort;
- [ ] `3643` — every compared threshold policy starts from the same source calibration records for that client;
- [ ] `3644` — deterministic subsampling is policy-independent;
- [ ] `3645` — eligibility/feasibility cannot vary by threshold policy.
- [ ] `3657` — SHARED_THRESHOLD;
- [ ] `3658` — LOCAL_THRESHOLD;
- [ ] `3659` — CLUSTER_THRESHOLD;
- [ ] `3660` — complete fixed-lambda shrinkage curve `{0, 0.25, 0.50, 0.75, 1.00}`;
- [ ] `3661` — prospectively locked size-aware shrinkage;
- [ ] `3662` — LOCAL_CONFORMAL_THRESHOLD where its finite-sample rule is valid.
- [ ] `3668` — verify `(client, m)` feasibility (`n_k_source >= m`);
- [ ] `3669` — draw `m` benign calibration records without replacement from that client's source pool;
- [ ] `3670` — compute the declared thresholds;
- [ ] `3671` — evaluate on the unchanged held-out test set;
- [ ] `3672` — record threshold variance across subsamples;
- [ ] `3673` — record held-out FPR target error and the calibration-to-held-out benign generalization gap from Part III §4.8, using the exact subsampled calibration scores that constructed the threshold and the unchanged held-out benign evaluation rows;
- [ ] `3674` — define each client's full-calibration local threshold \(\tau^{full}_{s,k}\) as the fixed reference and calculate, over the `R=10` nested subsamples,
- [ ] `3686` — calculate threshold-order inversion against the full-calibration local thresholds. For every comparable client pair `(i,j)` whose full-calibration thresholds are unequal, a replicate is inverted when
- [ ] `3693` — record the mean absolute LOCAL_THRESHOLD-to-SHARED_THRESHOLD threshold distance
- [ ] `3700` — record `CV(FPR)`, worst-client FPR, IQR, range, P10 Macro-F1, and balanced accuracy over the fixed-cohort intersection defined above for cross-size comparisons;
- [ ] `3701` — report clients infeasible at each size, with the reason.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CALIBRATION-COLD-START-ONBOARDING-BOUNDARY — Part II §8.1A Calibration cold-start/onboarding boundary

- **Role:** Boundary
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** low-support onboarding
- **Mandatory:** YES
- **Authoritative source:** lines 3719–3754
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3737` — target LOCAL_THRESHOLD is `UNAVAILABLE_NO_LOCAL_CALIBRATION`;
- [ ] `3738` — target CLUSTER_THRESHOLD is `UNAVAILABLE_NO_FINGERPRINT`;
- [ ] `3739` — leave-target-out SHARED_THRESHOLD is formed from all other eligible clients and applied to the target;
- [ ] `3740` — leave-target-out FAMILY_THRESHOLD is formed from other eligible members of the target's locked physical family when at least one exists;
- [ ] `3741` — when no other eligible same-family client exists, FAMILY_THRESHOLD explicitly falls back to leave-target-out SHARED_THRESHOLD and records `family_fallback = true`.
- [ ] `3745` — the target's `m` benign records are the only target calibration records supplied to SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD;
- [ ] `3746` — other clients retain their full calibration support;
- [ ] `3747` — CLUSTER_THRESHOLD recomputes the target fingerprint from exactly the `m` target scores and uses the canonical `K=3` construction; if any of `mean`, sample standard deviation, skewness, or p95 is non-finite for that target sample, the CLUSTER_THRESHOLD target result is `UNAVAILABLE_NONFINITE_FINGERPRINT` and no imputation/zero replacement is permitted;
- [ ] `3748` — all policies use the same target subsample within a replicate;
- [ ] `3749` — the held-out test set remains unchanged.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-FIXED-LOCAL-GLOBAL-SHRINKAGE — Part II §8.2 Fixed local–global shrinkage

- **Role:** Threshold variant
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** fixed λ curve
- **Mandatory:** YES
- **Authoritative source:** lines 3755–3786
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3775` — compute the shrinkage threshold for every eligible client;
- [ ] `3776` — evaluate the full lambda curve;
- [ ] `3777` — report `CV(FPR)`, worst-client FPR, IQR, range, TPR, P10 Macro-F1, and threshold variance;
- [ ] `3778` — repeat within the calibration-size grid where planned;
- [ ] `3779` — do not choose one lambda from the test set and present it as the method.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CALIBRATION-SIZE-AWARE-SHRINKAGE — Part II §8.3 Calibration-size-aware shrinkage

- **Role:** Threshold variant
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** deterministic λ by `n_k_used`
- **Mandatory:** YES
- **Authoritative source:** lines 3787–3804
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-SPLIT-CONFORMAL-LOCAL-CONFORMAL-THRESHOLD-DIAGNOSTIC — Part II §8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic

- **Role:** Threshold variant
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** finite-sample local coverage
- **Mandatory:** YES
- **Authoritative source:** lines 3805–3845
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3819` — use only the declared benign calibration scores;
- [ ] `3820` — compute the finite-sample conformal quantile at `alpha = 0.05`;
- [ ] `3821` — evaluate benign coverage on held-out benign scores;
- [ ] `3822` — report coverage error per client and seed;
- [ ] `3823` — evaluate attack-sensitive metrics only on held-out attack scores;
- [ ] `3824` — compare LOCAL_CONFORMAL_THRESHOLD with LOCAL_THRESHOLD and SHARED_THRESHOLD;
- [ ] `3825` — report results at small calibration sizes where rank granularity is material.
- [ ] `3829` — target coverage;
- [ ] `3830` — achieved marginal benign coverage;
- [ ] `3831` — coverage error;
- [ ] `3832` — per-client coverage distribution;
- [ ] `3833` — `CV(FPR)`;
- [ ] `3834` — threshold difference from LOCAL_THRESHOLD;
- [ ] `3835` — detection-quality controls;
- [ ] `3836` — finite-sample discreteness diagnostics.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-BOUNDED-PREPROCESSING-GEOMETRY-SENSITIVITY — Part II §8.5 Bounded preprocessing-geometry sensitivity

- **Role:** Supportive boundary
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** local StandardScaler vs pooled MinMax protocol identity
- **Mandatory:** YES
- **Authoritative source:** lines 3846–3896
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `3863` — `CV(FPR)`, IQR, range, worst-client FPR;
- [ ] `3864` — held-out target-FPR error;
- [ ] `3865` — AUROC and average precision from that detector's canonical score artifact;
- [ ] `3866` — mean pairwise benign-score JSD `H`;
- [ ] `3867` — SHARED_THRESHOLD–LOCAL_THRESHOLD scope gain

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-SHARED-CALIBRATION-CONTRIBUTOR-AVAILABILITY — Part II §8.6 Shared-calibration contributor availability

- **Role:** Supportive operational sensitivity
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** exhaustive omission of `m={0,1,2,3,4}` shared-threshold contributors
- **Mandatory:** YES
- **Authoritative source:** lines 3897–3989
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-BENIGN-SUMMARY-STATISTICS-COMPARATOR — Part II §9.1 Benign summary-statistics comparator

- **Role:** Comparator
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** `FEDERATED_BENIGN_SUMMARY_THRESHOLD`
- **Mandatory:** YES
- **Authoritative source:** lines 3992–4056
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4004` — NBAIOT_NATURAL_DEVICES is mandatory;
- [ ] `4005` — EDGE_SENSOR_CLIENTS is mandatory for benign-FPR outcomes when artifacts are available.
- [ ] `4009` — SHARED_THRESHOLD;
- [ ] `4010` — exact pooled benign quantile;
- [ ] `4011` — sample-weighted shared construction;
- [ ] `4012` — LOCAL_THRESHOLD;
- [ ] `4013` — `FEDERATED_BENIGN_SUMMARY_THRESHOLD`.
- [ ] `4027` — compute the exact centralized benign reference;
- [ ] `4028` — compute every distributed construction from the same calibration records;
- [ ] `4029` — evaluate threshold-estimation error against the centralized reference;
- [ ] `4030` — evaluate achieved benign exceedance;
- [ ] `4031` — evaluate cross-client FPR dispersion;
- [ ] `4032` — report communication payload estimates separately from measured network cost;
- [ ] `4033` — calculate the locked between-ratio diagnostic where defined;
- [ ] `4034` — describe precisely which statistics leave each client.
- [ ] `4038` — threshold value;
- [ ] `4039` — absolute and relative threshold error;
- [ ] `4040` — target-attainment error;
- [ ] `4041` — `CV(FPR)`, IQR, range, and worst-client FPR;
- [ ] `4042` — communication fields and estimated bytes;
- [ ] `4043` — client coverage;
- [ ] `4044` — comparison with SHARED_THRESHOLD and LOCAL_THRESHOLD.
- [ ] `4050` — improve over SHARED_THRESHOLD but remain weaker than LOCAL_THRESHOLD;
- [ ] `4051` — match LOCAL_THRESHOLD;
- [ ] `4052` — dominate LOCAL_THRESHOLD;
- [ ] `4053` — fail to improve over SHARED_THRESHOLD.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-KLL-FEDERATED-QUANTILE-SKETCH-THRESHOLD — Part II §9.2 KLL federated quantile-sketch threshold

- **Role:** Comparator
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** KLL `k={200,400,800}`
- **Mandatory:** YES
- **Authoritative source:** lines 4057–4113
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4069` — NBAIOT_NATURAL_DEVICES mandatory;
- [ ] `4070` — EDGE_SENSOR_CLIENTS benign-equity population mandatory when ready.
- [ ] `4088` — exact pooled type-7 quantile oracle;
- [ ] `4089` — SHARED_THRESHOLD arithmetic mean of local quantiles;
- [ ] `4090` — sample-weighted shared construction;
- [ ] `4091` — `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
- [ ] `4092` — `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`;
- [ ] `4093` — LOCAL_THRESHOLD local.
- [ ] `4099` — use identical eligible calibration-score evidence;
- [ ] `4100` — serialize each client sketch and record actual byte length;
- [ ] `4101` — merge client sketches at the server;
- [ ] `4102` — obtain \(\tau_{KLL}\) at q=0.95;
- [ ] `4103` — calculate `EmpiricalRankError = |F_pool(tau_KLL)-0.95|`;
- [ ] `4104` — calculate absolute and relative threshold error versus the exact pooled type-7 oracle;
- [ ] `4105` — calculate held-out benign signed/absolute target error;
- [ ] `4106` — calculate `CV(FPR)`, IQR, range, worst-client FPR, and attack-sensitive controls where valid;
- [ ] `4107` — record client build time, server merge/query time, upload bytes/client, total upload bytes, and download threshold bytes;
- [ ] `4108` — repeat for `k={200,800}` as sensitivity without selecting a winner.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-FIXED-COEFFICIENT-LARIDI-SENSITIVITY — Part II §9.3 Fixed-coefficient Laridi sensitivity

- **Role:** Optional supplement
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** fixed coefficient sensitivity only
- **Mandatory:** NO
- **Authoritative source:** lines 4114–4129
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-EDGE-IIOTSET-EXTERNAL-BENIGN-EQUITY-VALIDATION — Part II §10.1 Edge-IIoTset external benign-equity validation

- **Role:** External validation
- **Population/setting:** Edge-IIoTset
- **Main variation:** independent-dataset benign equity
- **Mandatory:** YES
- **Authoritative source:** lines 4132–4194
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4144` — EDGE_SENSOR_CLIENTS;
- [ ] `4145` — ten benign sensor-group clients;
- [ ] `4146` — eligible-benign coverage 1.0;
- [ ] `4147` — ten paired seeds where training is feasible.
- [ ] `4151` — SHARED_THRESHOLD;
- [ ] `4152` — LOCAL_THRESHOLD;
- [ ] `4153` — CLUSTER_THRESHOLD canonical;
- [ ] `4154` — `FEDERATED_BENIGN_SUMMARY_THRESHOLD`;
- [ ] `4155` — quantile sensitivity;
- [ ] `4156` — calibration-size and shrinkage analyses where supported.
- [ ] `4162` — train the FedAvg autoencoder per seed using benign training data;
- [ ] `4163` — construct the allowed thresholds;
- [ ] `4164` — evaluate per-client benign FPR;
- [ ] `4165` — compute cross-client equity metrics;
- [ ] `4166` — represent attack-sensitive per-client metrics as unavailable;
- [ ] `4167` — compare the direction and magnitude of SHARED_THRESHOLD–LOCAL_THRESHOLD with NBAIOT_NATURAL_DEVICES without treating the datasets as exchangeable replications.
- [ ] `4171` — eligible-benign coverage;
- [ ] `4172` — per-client benign sample counts;
- [ ] `4173` — SHARED_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD/`FEDERATED_BENIGN_SUMMARY_THRESHOLD` thresholds;
- [ ] `4174` — per-client FPR;
- [ ] `4175` — `CV(FPR)`, IQR, range, and worst-client FPR;
- [ ] `4176` — seed-level SHARED_THRESHOLD–LOCAL_THRESHOLD differences;
- [ ] `4177` — BCa interval as external evidence;
- [ ] `4178` — typed unavailability for attack-sensitive metrics;
- [ ] `4179` — dataset-specific limitations.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-CICIOT2023-FILE-LEVEL-BOUNDARY — Part II §10.2 CICIoT2023 file-level boundary

- **Role:** Applicability boundary
- **Population/setting:** CICIoT2023 file pseudo-clients
- **Main variation:** available-data boundary
- **Mandatory:** YES
- **Authoritative source:** lines 4195–4218
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4207` — quantify pairwise benign-distribution divergence;
- [ ] `4208` — run SHARED_THRESHOLD and LOCAL_THRESHOLD on the same scores;
- [ ] `4209` — include CLUSTER_THRESHOLD only if cluster sizes are meaningful;
- [ ] `4210` — report `CV(FPR)`, IQR, range, and worst pseudo-client FPR;
- [ ] `4211` — keep all wording specific to the available pseudo-clients.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-FEDPROX-AGGREGATION-MECHANISM-ACTIVATION-STRESS-TEST — Part II §11.1 FedProx aggregation + mechanism-activation stress test

- **Role:** Training stress
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** FedProx μ grid + local-update drift diagnostics
- **Mandatory:** YES
- **Authoritative source:** lines 4244–4319
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4260` — NBAIOT_NATURAL_DEVICES is mandatory;
- [ ] `4261` — EDGE_SENSOR_CLIENTS benign-equity outcomes are included after EDGE_SENSOR_CLIENTS readiness.
- [ ] `4265` — FedAvg reference;
- [ ] `4266` — FedProx with frozen `mu` grid:
- [ ] `4267` — `0.001`;
- [ ] `4268` — `0.01`;
- [ ] `4269` — `0.1`;
- [ ] `4270` — `1.0`;
- [ ] `4271` — SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD where valid, and CLUSTER_THRESHOLD.
- [ ] `4288` — train FedProx models independently from FedAvg for every `mu`;
- [ ] `4289` — train to the same fixed terminal round;
- [ ] `4290` — persist the complete round-level training-loss trajectory and any convergence/failure state;
- [ ] `4291` — persist the broadcast-state identity and compute `L2Drift`, `RMSDrift`, and FedProx `TerminalProxPenalty` for every client-round cell exactly as Part I §7.1A specifies;
- [ ] `4292` — compute `D_all` and `D_terminal50` for FedAvg and every `mu`, plus every client's terminal-50 median drift;
- [ ] `4293` — compute seed-level `DriftSuppression[s,mu]` where defined; retain negative values rather than clipping them;
- [ ] `4294` — produce separate score sets;
- [ ] `4295` — report terminal benign reconstruction-error mean, median, and IQR per client;
- [ ] `4296` — compute AUROC and average precision from each model's canonical score artifact where valid;
- [ ] `4297` — calculate full-score benign heterogeneity `H` using the locked JSD definition and compute `DeltaH[s,mu]` relative to FedAvg;
- [ ] `4298` — compute every common Part I §7.2B score/threshold-alignment diagnostic and every defined `AlignmentReduction`;
- [ ] `4299` — evaluate the complete threshold ladder on each trained model;
- [ ] `4300` — calculate `DeltaScope[s,mu]` and `ScopeAbsorption[s,mu]` relative to FedAvg when the FedAvg denominator is valid;
- [ ] `4301` — report, for each seed and `mu`, the tuple `(DriftSuppression, DeltaH, H, LocationDispersion, ScaleDispersion, LocalThresholdDispersion, NormalizedSharedLocalThresholdDistance, DeltaScope, ScopeAbsorption)` so a null absorption result can be distinguished from a FedProx condition that barely changed update/score geometry;
- [ ] `4302` — report SHARED_THRESHOLD and LOCAL_THRESHOLD threshold distributions across clients;
- [ ] `4303` — report training failure or instability without changing the grid retroactively.
- [ ] `4309` — retained threshold-scope effect with observed drift suppression;
- [ ] `4310` — retained threshold-scope effect with little/no observed drift suppression;
- [ ] `4311` — partial absorption;
- [ ] `4312` — full absorption;
- [ ] `4313` — opposite effect;
- [ ] `4314` — FedProx non-convergence or instability.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-DITTO-MODEL-PERSONALIZATION-STRESS-TEST — Part II §11.2 Ditto model-personalization stress test

- **Role:** Model-personalization stress
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** Ditto λD grid / absorption
- **Mandatory:** YES
- **Authoritative source:** lines 4320–4429
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4338` — NBAIOT_NATURAL_DEVICES is mandatory;
- [ ] `4339` — EDGE_SENSOR_CLIENTS is included for benign-equity outcomes after readiness.
- [ ] `4345` — FedAvg model with SHARED_THRESHOLD;
- [ ] `4346` — FedAvg model with LOCAL_THRESHOLD;
- [ ] `4347` — canonical Ditto personalized model (`lambda_D = 1.0`) with SHARED_THRESHOLD;
- [ ] `4348` — canonical Ditto personalized model (`lambda_D = 1.0`) with LOCAL_THRESHOLD.
- [ ] `4374` — train genuine Ditto global and persistent personalized states for each locked λ;
- [ ] `4375` — keep personalized states separate by client and never aggregate them;
- [ ] `4376` — use the same optimizer, learning-rate, batch, round, and local-epoch semantics as the reference unless Ditto's proximal update explicitly changes the objective term;
- [ ] `4377` — generate personalized scores separately from all FedAvg artifacts;
- [ ] `4378` — compute SHARED_THRESHOLD and LOCAL_THRESHOLD from the corresponding personalized score distributions;
- [ ] `4379` — calculate the threshold-scope gain under FedAvg and canonical Ditto;
- [ ] `4380` — compute every common Part I §7.2B score/threshold-alignment diagnostic and available `AlignmentReduction` for canonical Ditto and each sensitivity λ;
- [ ] `4381` — compute AUROC/AP, `CV(FPR)`, worst-client FPR, P10 Macro-F1, and held-out target error;
- [ ] `4382` — measure persistent personalized-model serialized bytes per client, extra local training wall time relative to FedAvg, and total threshold-stage payload; model-update communication remains separately accounted from local personalized-state storage;
- [ ] `4383` — preserve all four canonical corners and all sensitivity λ outcomes.
- [ ] `4416` — `AbsorptionFraction <= 0.25` (equivalently `Delta_Ditto >= 0.75 * Delta_FedAvg`): threshold personalization remains strongly useful;
- [ ] `4417` — `0.25 < AbsorptionFraction <= 0.75`: partial absorption;
- [ ] `4418` — `0.75 < AbsorptionFraction <= 1.0`: largely absorbed;
- [ ] `4419` — `AbsorptionFraction > 1.0`: reversed shared/local ordering under Ditto;
- [ ] `4420` — if `CV(FPR)[Ditto+SHARED_THRESHOLD]` is within absolute `0.05` of `CV(FPR)[FedAvg+LOCAL_THRESHOLD]`, model personalization is reported as an alternative route to operating-point equity.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-FEDAVG-POST-TRAINING-CLIENT-LOCAL-FINE-TUNING — Part II §11.2A FedAvg post-training client-local fine-tuning

- **Role:** Simple model-personalization stress
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** exactly 10 benign-training local epochs + common absorption diagnostics
- **Mandatory:** YES
- **Authoritative source:** lines 4430–4501
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4446` — `NBAIOT_NATURAL_DEVICES` is mandatory;
- [ ] `4447` — `EDGE_SENSOR_CLIENTS` benign-equity outcomes are included after readiness if the same benign-train/calibration/evaluation separation can be preserved.
- [ ] `4451` — FedAvg + SHARED_THRESHOLD;
- [ ] `4452` — FedAvg + LOCAL_THRESHOLD;
- [ ] `4453` — `FEDAVG_LOCAL_FINE_TUNING` + SHARED_THRESHOLD;
- [ ] `4454` — `FEDAVG_LOCAL_FINE_TUNING` + LOCAL_THRESHOLD.
- [ ] `4460` — load the exact seed-matched FedAvg terminal scientific detector at round `200`;
- [ ] `4461` — for every client, initialize a local copy from those exact weights;
- [ ] `4462` — instantiate a fresh optimizer and fine-tune for exactly `10` complete epochs on that client's benign **training** partition only;
- [ ] `4463` — freeze the end-of-epoch-10 client model; no early stopping, validation selection, calibration selection, or aggregation occurs;
- [ ] `4464` — generate one immutable client-specific calibration score artifact and one immutable client-specific evaluation score artifact;
- [ ] `4465` — compute SHARED_THRESHOLD and LOCAL_THRESHOLD from those frozen fine-tuned score artifacts;
- [ ] `4466` — compute AUROC/AP, FPR, `CV(FPR)`, absolute FPR dispersion, TPR, Macro-F1, balanced accuracy, P10 Macro-F1, worst-client BA, held-out target error, and calibration-generalization-gap metrics wherever valid;
- [ ] `4467` — compute the complete common Part I §7.2B mechanism tuple and every available `AlignmentReduction`;
- [ ] `4468` — define
- [ ] `4482` — retain the value un-clipped and use the same literal interpretation as the generic Part I §7.2B definition: `<0` amplification, `0` no absorption, `(0,1)` partial absorption, `1` zero residual shared/local gain, and `>1` reversal;
- [ ] `4483` — report per-client serialized fine-tuned-model bytes and **fine-tuning wall time** measured on the same execution machine as the FedAvg reference; post-training local fine-tuning adds no model-update communication round, so communication is reported as `0 additional federated rounds` rather than converted into a speculative network latency;
- [ ] `4484` — report all ten training seeds. No “best fine-tuning seed” or alternate epoch count may be substituted.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-ONE-SHOT-RECALIBRATION-UNDER-GENUINE-CHRONOLOGY — Part II §12.1 One-shot recalibration under genuine chronology

- **Role:** Temporal boundary
- **Population/setting:** Edge-IIoTset temporal population
- **Main variation:** static vs frozen-future vs one-shot recalibration
- **Mandatory:** YES
- **Authoritative source:** lines 4504–4646
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4516` — EDGE_TEMPORAL_CLIENTS;
- [ ] `4517` — nine verified temporal groups;
- [ ] `4518` — Modbus excluded;
- [ ] `4519` — ten paired seeds where feasible.
- [ ] `4534` — SHARED_THRESHOLD;
- [ ] `4535` — LOCAL_THRESHOLD;
- [ ] `4536` — CLUSTER_THRESHOLD;
- [ ] `4537` — shrinkage where pre-specified.
- [ ] `4541` — verify timestamps for every included client;
- [ ] `4542` — apply stable chronological ordering;
- [ ] `4543` — construct the 55/15/10/20 split;
- [ ] `4544` — fit preprocessing and the autoencoder without future leakage;
- [ ] `4545` — construct historical thresholds;
- [ ] `4546` — evaluate frozen thresholds on future evaluation;
- [ ] `4547` — recompute thresholds from future recalibration only;
- [ ] `4548` — evaluate recalibrated thresholds on the same future evaluation;
- [ ] `4549` — construct the matched static reference;
- [ ] `4550` — calculate:
- [ ] `4615` — chronology-validation record;
- [ ] `4616` — included and excluded clients;
- [ ] `4617` — static-reference CV;
- [ ] `4618` — frozen-future CV;
- [ ] `4619` — recalibrated-future CV;
- [ ] `4620` — drift excess;
- [ ] `4621` — recovered amount;
- [ ] `4622` — recovery ratio when defined;
- [ ] `4623` — per-client FPR trajectories;
- [ ] `4624` — per-client threshold movements `Delta tau_k`;
- [ ] `4625` — per-client `DriftJS_k`;
- [ ] `4626` — per-client frozen deterioration and recovery;
- [ ] `4627` — helped/harmed/unchanged fractions;
- [ ] `4628` — worst-client FPR recovery;
- [ ] `4629` — drift-JS versus FPR-deterioration Spearman summary where available;
- [ ] `4630` — paired seed uncertainty.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-ALERT-BURDEN-EXPERIMENT — Part II §13.1 Alert-burden experiment

- **Role:** Operational interpretation
- **Population/setting:** valid rate-bearing population
- **Main variation:** alert-count translation
- **Mandatory:** YES
- **Authoritative source:** lines 4649–4693
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4681` — report the rate source;
- [ ] `4682` — report whether the rate is measured, dataset-derived, or externally cited;
- [ ] `4683` — propagate rate assumptions separately from model uncertainty;
- [ ] `4684` — show per-device burden, not only a pooled total;
- [ ] `4685` — use SHARED_THRESHOLD and LOCAL_THRESHOLD at minimum;
- [ ] `4686` — label estimates as estimated when no deployment measurement exists.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-THRESHOLD-STAGE-COMMUNICATION-STORAGE-RUNTIME-ACCOUNTIN — Part II §13.2 Threshold-stage communication/storage/runtime accounting

- **Role:** Operational accounting
- **Population/setting:** applicable methods
- **Main variation:** payload, storage, threshold-stage timing
- **Mandatory:** YES
- **Authoritative source:** lines 4694–4737
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:** no list items detected; audit the section prose/formulas through the formula/literal/source-coverage ledgers.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-ROBUST-CLUSTER-MEDIAN-THRESHOLD — Part II §14.1 Robust cluster-median threshold

- **Role:** Optional analysis
- **Population/setting:** N-BaIoT natural devices
- **Main variation:** cluster median vs mean threshold
- **Mandatory:** NO
- **Authoritative source:** lines 4742–4755
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4748` — cluster assignments unchanged;
- [ ] `4749` — cluster threshold difference;
- [ ] `4750` — `CV(FPR)`;
- [ ] `4751` — worst-client FPR;
- [ ] `4752` — outlier-client influence.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-ADDITIONAL-EQUITY-INDICES — Part II §14.2 Additional equity indices

- **Role:** Optional analysis
- **Population/setting:** applicable populations
- **Main variation:** Jain/Gini/IQR/range diagnostics
- **Mandatory:** NO
- **Authoritative source:** lines 4756–4768
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4760` — Jain index;
- [ ] `4761` — Gini coefficient;
- [ ] `4762` — IQR;
- [ ] `4763` — max–min range;
- [ ] `4764` — within-cluster dispersion;
- [ ] `4765` — across-cluster dispersion.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

### EXPERIMENT-EXTENDED-SECONDARY-UNCERTAINTY — Part II §14.3 Extended secondary uncertainty

- **Role:** Optional analysis
- **Population/setting:** applicable experiments
- **Main variation:** secondary paired uncertainty
- **Mandatory:** NO
- **Authoritative source:** lines 4769–4779
- **Repository disposition:** `NOT_AUDITED`
- **Scientific audit outcome:** —

**Source-derived atomic checklist:**

- [ ] `4773` — bootstrap intervals for secondary paired metrics;
- [ ] `4774` — Wilcoxon signed-rank;
- [ ] `4775` — matched-pairs rank-biserial correlation;
- [ ] `4776` — exact sign summaries where useful.

**Repository mapping fields:**

| Expected owner | Actual file::symbol | Runtime caller | Tests | Artifacts | Priority | Remediation | Verification |
|---|---|---|---|---|---|---|---|
| experiment integration owner = planner/pipeline; child semantic owners = §0.5A routing | — | — | — | — | — | — | — |

## 8. Metric, statistical, terminal-detector, and temporal semantics catalogue

| ID | Type | Part III contract | Source lines | Implementation owner | Disposition | Audit |
|---|---|---|---:|---|---|---|
| `METRIC-001` | `METRIC` | 1.1 Fixed-score comparison — inherited contract | 4786–4789 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-002` | `METRIC` | 1.2 Independent unit | 4790–4797 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-003` | `METRIC` | 1.3 Per-client-first reporting | 4798–4805 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-004` | `METRIC` | 3.1 Calibration eligibility — inherited contract | 4838–4841 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-005` | `METRIC` | 3.2 FPR-evaluable population | 4842–4845 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-006` | `METRIC` | 3.3 Attack-evaluable population | 4846–4857 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-007` | `METRIC` | 3.4 Coverage | 4858–4871 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-008` | `METRIC` | 4.1 False-positive rate | 4874–4883 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-009` | `METRIC` | 4.2 True-positive rate | 4884–4893 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-010` | `METRIC` | 4.3 Balanced accuracy | 4894–4903 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-011` | `METRIC` | 4.4 Per-client Macro-F1 | 4904–4921 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-012` | `METRIC` | 4.5 AUROC | 4922–4929 | evaluation/metrics | `NOT_AUDITED` | — |
| `STAT-001` | `STAT` | 4.6 Average precision / PR-curve summary | 4930–4941 | analysis/inference | `NOT_AUDITED` | — |
| `METRIC-013` | `METRIC` | 4.7 Held-out benign target-attainment error | 4942–4974 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-014` | `METRIC` | 4.8 Calibration-to-held-out benign generalization gap | 4975–5014 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-015` | `METRIC` | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | 5015–5070 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-016` | `METRIC` | 5.1 Mean FPR | 5075–5085 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-017` | `METRIC` | 5.2 Sample standard deviation | 5086–5110 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-018` | `METRIC` | 5.3 Coefficient of variation | 5111–5130 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-019` | `METRIC` | 5.4 Absolute dispersion | 5131–5150 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-020` | `METRIC` | 5.5 TPR and lower-tail metrics | 5151–5179 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-021` | `METRIC` | 6.1 Jain index | 5184–5197 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-022` | `METRIC` | 6.2 Gini coefficient | 5198–5211 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-023` | `METRIC` | 6.3 Cluster dispersion | 5212–5226 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-024` | `METRIC` | 5.6 Natural-device help/harm summary semantics | 5227–5253 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-025` | `METRIC` | 7.1 Mean client Macro-F1 | 5256–5266 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-026` | `METRIC` | 7.2 Pooled Macro-F1 | 5267–5276 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-027` | `METRIC` | 7.3 Mean client balanced accuracy | 5277–5289 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-028` | `METRIC` | 8.1 Centralized oracle | 5292–5297 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-029` | `METRIC` | 8.2 Threshold error | 5298–5317 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-030` | `METRIC` | 8.3 Target attainment | 5318–5339 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-031` | `METRIC` | 8.4 Threshold variance and sample efficiency | 5340–5376 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-032` | `METRIC` | 9.1 Global mean | 5386–5397 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-033` | `METRIC` | 9.2 Full pooled variance | 5398–5425 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-034` | `METRIC` | 9.3 Between ratio | 5426–5439 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-035` | `METRIC` | 10.1 Alert burden | 5442–5457 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-036` | `METRIC` | 10.2 Threshold-stage communication | 5458–5470 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-037` | `METRIC` | 10.3 Threshold-stage latency and memory | 5471–5474 | evaluation/metrics | `NOT_AUDITED` | — |
| `METRIC-038` | `METRIC` | 10.4 Ditto incremental state and compute | 5475–5487 | evaluation/metrics | `NOT_AUDITED` | — |
| `STAT-002` | `STAT` | 11.1 Paired contrast | 5490–5512 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-003` | `STAT` | 11.1A Relative and robustness-oriented descriptive effect sizes | 5513–5539 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-004` | `STAT` | 11.2 BCa confidence interval | 5540–5545 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-005` | `STAT` | 11.3 Degenerate BCa | 5546–5554 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-006` | `STAT` | 11.4 Sign consistency | 5555–5572 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-007` | `STAT` | 12.1A Exact paired sign test | 5575–5598 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-008` | `STAT` | 12.1 Wilcoxon signed-rank | 5599–5609 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-009` | `STAT` | 12.2 Matched-pairs rank-biserial correlation | 5610–5617 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-010` | `STAT` | 12.3 Secondary confidence intervals | 5618–5621 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-011` | `STAT` | 12.4 Multiplicity | 5622–5634 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-012` | `STAT` | 12.5 Nested replicates | 5635–5643 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-013` | `STAT` | 12.6 Association analyses | 5644–5656 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-014` | `STAT` | 12.7 Cluster stability | 5657–5662 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-015` | `STAT` | 13.1 Terminal detector | 5665–5668 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-016` | `STAT` | 13.2 Recovery and diagnostic checkpoints | 5669–5672 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-017` | `STAT` | 13.3 Fixed-detector restrictions | 5673–5676 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-018` | `STAT` | 14.1 Client-level temporal diagnostics | 5723–5742 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-019` | `STAT` | 15.1 Locked ten-seed precision diagnostics | 5745–5782 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-020` | `STAT` | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | 5783–5845 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-021` | `STAT` | 15.2 Numerical and selection discipline | 5846–5861 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-022` | `STAT` | 16.1 Causal intervention map — mandatory main-text figure | 5866–5897 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-023` | `STAT` | 16.2 Confirmatory paired-effect view — mandatory main-text figure | 5898–5907 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-024` | `STAT` | 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table | 5908–5927 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-025` | `STAT` | 16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure | 5928–5931 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-026` | `STAT` | 16.4 FedProx mechanism-activation view — mandatory stress-test figure | 5932–5935 | analysis/inference | `NOT_AUDITED` | — |
| `STAT-027` | `STAT` | 16.5 Mandatory synthesis tables | 5936–5948 | analysis/inference | `NOT_AUDITED` | — |

### 8.1 Metric/statistical section checklists

#### METRIC-001 — 1.1 Fixed-score comparison — inherited contract

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-002 — 1.2 Independent unit

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-003 — 1.3 Per-client-first reporting

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-004 — 3.1 Calibration eligibility — inherited contract

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-005 — 3.2 FPR-evaluable population

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-006 — 3.3 Attack-evaluable population

- [ ] `4850` — valid per-client attack assignment;
- [ ] `4851` — at least one held-out attack row;
- [ ] `4852` — both semantic classes where required.

#### METRIC-007 — 3.4 Coverage

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-008 — 4.1 False-positive rate

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-009 — 4.2 True-positive rate

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-010 — 4.3 Balanced accuracy

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-011 — 4.4 Per-client Macro-F1

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-012 — 4.5 AUROC

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-001 — 4.6 Average precision / PR-curve summary

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-013 — 4.7 Held-out benign target-attainment error

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-014 — 4.8 Calibration-to-held-out benign generalization gap

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-015 — 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR

- [ ] `5061` — `CalibrationExceedance`;
- [ ] `5062` — `CalibrationTargetError`;
- [ ] `5063` — `SignedTestFPRTargetError`;
- [ ] `5064` — `AbsoluteTestFPRTargetError`;
- [ ] `5065` — `CalibrationGeneralizationGap`.

#### METRIC-016 — 5.1 Mean FPR

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-017 — 5.2 Sample standard deviation

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-018 — 5.3 Coefficient of variation

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-019 — 5.4 Absolute dispersion

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-020 — 5.5 TPR and lower-tail metrics

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-021 — 6.1 Jain index

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-022 — 6.2 Gini coefficient

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-023 — 6.3 Cluster dispersion

- [ ] `5216` — cluster size;
- [ ] `5217` — within-cluster threshold spread;
- [ ] `5218` — within-cluster FPR spread;
- [ ] `5219` — across-cluster threshold spread;
- [ ] `5220` — across-cluster mean-FPR spread;
- [ ] `5221` — singleton and empty-cluster status.

#### METRIC-024 — 5.6 Natural-device help/harm summary semantics

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-025 — 7.1 Mean client Macro-F1

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-026 — 7.2 Pooled Macro-F1

- [ ] `5273` — mean client Macro-F1;
- [ ] `5274` — P10 Macro-F1;
- [ ] `5275` — worst-client balanced accuracy.

#### METRIC-027 — 7.3 Mean client balanced accuracy

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-028 — 8.1 Centralized oracle

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-029 — 8.2 Threshold error

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-030 — 8.3 Target attainment

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-031 — 8.4 Threshold variance and sample efficiency

- [ ] `5361` — threshold variance across the 10 nested replicates;
- [ ] `5362` — threshold bias versus the full-calibration threshold;
- [ ] `5363` — threshold RMSE versus the full-calibration threshold;
- [ ] `5364` — threshold-order inversion rate and tie rate;
- [ ] `5365` — mean local-to-shared threshold distance;
- [ ] `5366` — held-out signed/absolute target-FPR error;
- [ ] `5367` — `CV(FPR)`;
- [ ] `5368` — worst-client FPR;
- [ ] `5369` — P10 Macro-F1 where available.

#### METRIC-032 — 9.1 Global mean

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-033 — 9.2 Full pooled variance

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-034 — 9.3 Between ratio

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-035 — 10.1 Alert burden

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-036 — 10.2 Threshold-stage communication

- [ ] `5462` — logical fields sent per client;
- [ ] `5463` — actual serialized upload bytes/client;
- [ ] `5464` — total uploaded bytes across participating clients;
- [ ] `5465` — actual serialized server response bytes/client and total;
- [ ] `5466` — whether a broadcast payload is counted once on the wire or once per logical recipient;
- [ ] `5467` — number of post-training threshold-communication rounds.

#### METRIC-037 — 10.3 Threshold-stage latency and memory

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### METRIC-038 — 10.4 Ditto incremental state and compute

- [ ] `5479` — serialized global-model bytes;
- [ ] `5480` — serialized persistent personalized-model bytes per client;
- [ ] `5481` — extra persistent state per client relative to FedAvg;
- [ ] `5482` — measured local personalized-training wall time per round and total;
- [ ] `5483` — global-update communication bytes;
- [ ] `5484` — threshold-stage communication bytes.

#### STAT-002 — 11.1 Paired contrast

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-003 — 11.1A Relative and robustness-oriented descriptive effect sizes

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-004 — 11.2 BCa confidence interval

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-005 — 11.3 Degenerate BCa

- [ ] `5550` — report the paired values and point estimate;
- [ ] `5551` — allow percentile or basic intervals only as diagnostics;
- [ ] `5552` — do not silently substitute another interval for the confirmatory rule;
- [ ] `5553` — report the confirmatory claim as **not established**; never silently convert this outcome to `CONFIRMATORY_SUPPORT` or `NO_OBSERVED_ADVANTAGE`, and never rescue it with a secondary result, another statistical test, or supportive/mechanism/external/stress-test evidence.

#### STAT-006 — 11.4 Sign consistency

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-007 — 12.1A Exact paired sign test

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-008 — 12.1 Wilcoxon signed-rank

- [ ] `5603` — two-sided alternative;
- [ ] `5604` — explicit zero-difference handling;
- [ ] `5605` — exact computation when data and implementation permit;
- [ ] `5606` — recorded approximation or permutation method otherwise.

#### STAT-009 — 12.2 Matched-pairs rank-biserial correlation

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-010 — 12.3 Secondary confidence intervals

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-011 — 12.4 Multiplicity

- [ ] `5628` — define test families before analysis;
- [ ] `5629` — report family size;
- [ ] `5630` — apply Holm correction within each family;
- [ ] `5631` — retain raw values only as clearly labeled diagnostics.

#### STAT-012 — 12.5 Nested replicates

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-013 — 12.6 Association analyses

- [ ] `5648` — Spearman correlation;
- [ ] `5649` — declared regression;
- [ ] `5650` — coefficient and uncertainty;
- [ ] `5651` — `R²`;
- [ ] `5652` — influence diagnostics;
- [ ] `5653` — all observations.

#### STAT-014 — 12.7 Cluster stability

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-015 — 13.1 Terminal detector

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-016 — 13.2 Recovery and diagnostic checkpoints

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-017 — 13.3 Fixed-detector restrictions

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-018 — 14.1 Client-level temporal diagnostics

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-019 — 15.1 Locked ten-seed precision diagnostics

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-020 — 15.1A Leave-one-device-out influence for the natural-device confirmatory effect

- [ ] `5789` — remove device `j` from both the threshold-construction and equity-evaluation client populations;
- [ ] `5790` — recompute the SHARED_THRESHOLD from the remaining eligible local q95 thresholds;
- [ ] `5791` — retain every remaining client's previously computed LOCAL_THRESHOLD;
- [ ] `5792` — compute both `CV(FPR)` values on exactly the same remaining client set;
- [ ] `5793` — define

#### STAT-021 — 15.2 Numerical and selection discipline

- [ ] `5852` — rates and aggregate metrics: three decimals;
- [ ] `5853` — confidence intervals and effect sizes: three decimals;
- [ ] `5854` — p-values: three significant digits, with `< 0.001` when appropriate;
- [ ] `5855` — counts: integers;
- [ ] `5856` — thresholds: enough digits to reproduce decisions.

#### STAT-022 — 16.1 Causal intervention map — mandatory main-text figure

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-023 — 16.2 Confirmatory paired-effect view — mandatory main-text figure

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-024 — 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-025 — 16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-026 — 16.4 FedProx mechanism-activation view — mandatory stress-test figure

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

#### STAT-027 — 16.5 Mandatory synthesis tables

- [ ] Implement and test the exact prose/formula semantics referenced by the formula ledger and source lines above.

## 9. Mandatory manuscript-facing figure and table matrix

### REPORT-16-1-CAUSAL-INTERVENTION-MAP-MANDATORY-MAIN-TEXT-FIGURE — 16.1 Causal intervention map — mandatory main-text figure

**Source:** Part III lines 5866–5897


**Audit:** `NOT_AUDITED`

### REPORT-16-2-CONFIRMATORY-PAIRED-EFFECT-VIEW-MANDATORY-MAIN-TEXT-FIG — 16.2 Confirmatory paired-effect view — mandatory main-text figure

**Source:** Part III lines 5898–5907


**Audit:** `NOT_AUDITED`

### REPORT-16-2A-CONFIRMATORY-EQUITY-UTILITY-CLIENT-IMPACT-BUNDLE-MANDA — 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table

**Source:** Part III lines 5908–5927


**Audit:** `NOT_AUDITED`

### REPORT-16-3-EQUITY-UTILITY-PARETO-VIEW-MANDATORY-MAIN-TEXT-OR-FIRST — 16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure

**Source:** Part III lines 5928–5931


**Audit:** `NOT_AUDITED`

### REPORT-16-4-FEDPROX-MECHANISM-ACTIVATION-VIEW-MANDATORY-STRESS-TEST — 16.4 FedProx mechanism-activation view — mandatory stress-test figure

**Source:** Part III lines 5932–5935


**Audit:** `NOT_AUDITED`

### REPORT-16-5-MANDATORY-SYNTHESIS-TABLES — 16.5 Mandatory synthesis tables

**Source:** Part III lines 5936–5948

- [ ] `5940` — the Part II §4.0 population-capability/claim-boundary table;
- [ ] `5941` — the Part I §10.D.9 prior-art collision table updated through the submission-time novelty gate;
- [ ] `5942` — the shared-threshold robustness panel covering canonical arithmetic-mean shared, exact pooled, sample-weighted shared, `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`, and `FEDERATED_BENIGN_SUMMARY_THRESHOLD` against LOCAL_THRESHOLD;
- [ ] `5943` — the calibration-generalization/target-attainment diagnostics corresponding to the main threshold-policy results;
- [ ] `5944` — the Part I §10.D.9B source-grounded prior-art distinction table, using the locked categorical vocabulary;
- [ ] `5945` — the Part II §7.5A calibration-support-versus-burden table and seed-level association summary;
- [ ] `5946` — the Part II §7.5B natural-device helped/harmed table with the campaign-fixed support strata;
- [ ] `5947` — the Part II §7.4 typed empirical policy-selection surface and its reconstructable raw metric table.

**Audit:** `NOT_AUDITED`

## 10. Claim-to-evidence and claim-survival matrix

The following is copied directly from the roadmap claim-survival table; it is a reporting gate, not a post-hoc selection menu.

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

### 10.1 Negative evidence that must remain publishable

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

## 11. Scope, boundary, exclusion, and unavailability matrix

| ID | Roadmap owner | Boundary / limitation | Implementation implication | Audit |
|---|---|---|---|---|
| `BOUNDARY-001` | Part I `9.2 CICIoT2023 available-data boundary` line 1195 | 9.2 CICIoT2023 available-data boundary | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-002` | Part I `9.7 Heterogeneity taxonomy and claim boundary` line 1269 | 9.7 Heterogeneity taxonomy and claim boundary | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-003` | Part I `10.A.5 Temporal boundary` line 1334 | 10.A.5 Temporal boundary | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-004` | Part I `10.B.1 Security attacks and defenses` line 1372 | 10.B.1 Security attacks and defenses | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-005` | Part I `10.B.2 Formal privacy` line 1378 | 10.B.2 Formal privacy | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-006` | Part I `10.B.3 Deployment validation` line 1388 | 10.B.3 Deployment validation | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-007` | Part I `10.B.4 Fleet scale` line 1394 | 10.B.4 Fleet scale | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-008` | Part I `10.B.5 Full drift handling` line 1400 | 10.B.5 Full drift handling | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-009` | Part I `10.B.6 Broad FL benchmarking` line 1404 | 10.B.6 Broad FL benchmarking | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-010` | Part I `10.B.7 Federated conformal breadth` line 1410 | 10.B.7 Federated conformal breadth | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-011` | Part I `10.B.10 Explicit non-expansion guardrails for this amendment` line 1418 | 10.B.10 Explicit non-expansion guardrails for this amendment | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-012` | Part I `10.D.9 Novelty boundary and mandatory prior-art audit` line 1726 | 10.D.9 Novelty boundary and mandatory prior-art audit | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-013` | Part I `10.E.1 Small natural client population` line 1929 | 10.E.1 Small natural client population | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-014` | Part I `10.E.2 One external dataset` line 1935 | 10.E.2 One external dataset | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-015` | Part I `10.E.3 Incomplete external attack assignment` line 1939 | 10.E.3 Incomplete external attack assignment | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-016` | Part I `10.E.4 Single temporal family` line 1943 | 10.E.4 Single temporal family | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-017` | Part I `10.E.5 No formal privacy guarantee` line 1947 | 10.E.5 No formal privacy guarantee | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-018` | Part I `10.E.6 No hardware evidence` line 1951 | 10.E.6 No hardware evidence | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-019` | Part I `10.E.7 Threshold trade-offs` line 1955 | 10.E.7 Threshold trade-offs | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-020` | Part I `10.E.8 Comparator incompleteness` line 1959 | 10.E.8 Comparator incompleteness | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-021` | Part I `10.E.9 Conformal limitation` line 1963 | 10.E.9 Conformal limitation | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-022` | Part I `10.E.10 Honest-calibration / no Byzantine-integrity guarantee` line 1967 | 10.E.10 Honest-calibration / no Byzantine-integrity guarantee | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |
| `BOUNDARY-023` | Part I `10.E.11 Persistent identifiable-client limitation` line 1971 | 10.E.11 Persistent identifiable-client limitation | encode explicit validation/unavailability/claim restrictions; do not “fix” accepted scientific limitations by silently expanding scope | `NOT_AUDITED` |

### 11.1 Typed unavailability requirements

The implementation must distinguish at least these roadmap-defined scientific states from ordinary missing values. Exact code-facing names that appear in the roadmap are preserved in the literal ledger.

- [ ] `CONFIRMATORY_INFERENCE_UNAVAILABLE` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `INSUFFICIENT_EVIDENCE` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_ALL_ZERO_DIFFERENCES` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_AS_SPECIFIED` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_DEGENERATE_FEDAVG_JSD_GRID` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_EXPECTED_9_ELIGIBLE_NBAIOT_CLIENTS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_MEASUREMENT_NOT_SUPPORTED` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NEAR_ZERO_FEDAVG_DRIFT` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NEAR_ZERO_FULL_EFFECT` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NONFINITE_FINGERPRINT` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NONPOSITIVE_SCALE` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_COMMON_FPR_TPR_CLIENTS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_FINGERPRINT` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_FPR_HARMED_CLIENTS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_LOCAL_CALIBRATION` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_POSITIVE_FEDAVG_REFERENCE` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_POSITIVE_LOCAL_GAP` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_POSITIVE_LOCAL_STANDARD_GAP` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_TPR_LOSS_CLIENTS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_NO_VALID_TPR_SEEDS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNAVAILABLE_TOO_FEW_REMAINING_CONTRIBUTORS` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.
- [ ] `UNDEFINED_CONSTANT_INPUT` — implemented as a typed scientific state with provenance/reason, never a silent `None`/NaN substitute.

## 12. Gates A–R — repository and campaign audit matrix

**Extracted Part IV checkbox count:** `205`. These are copied one-for-one from the source checklist.

### Gate A

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-A-001` | 5994 | Every executable experiment maps to exactly one Part II experiment or explicitly declared diagnostic extension. | `IMPLEMENTED` | `PASS` | `validate_programme` requires every non-suppressed declaration to have exactly one registered recipe; `test_every_non_suppressed_experiment_has_exactly_one_recipe` covers it. |
| `GATE-A-002` | 5995 | No stale method name, retired alias, or opaque experiment code changes the active descriptive scientific identity defined in Part I §10.C. | `IMPLEMENTED` | `PASS` | The canonical protocol graph validates active scientific identities; release validation rejects retired opaque metadata. |
| `GATE-A-003` | 5996 | No opaque B-number threshold alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports. | `IMPLEMENTED` | `PASS` | Graph and release validators reject B-number identities; `test_graph_rejects_opaque_active_protocol_aliases` and release tests cover both boundaries. |
| `GATE-A-004` | 5997 | No lettered population alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports. | `IMPLEMENTED` | `PASS` | Graph and release validators reject lettered population aliases; `test_graph_rejects_opaque_active_protocol_aliases` covers the active-configuration boundary. |
| `GATE-A-005` | 5998 | Threshold policies use exactly `CENTRALIZED_REFERENCE`, `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FAMILY_THRESHOLD`, or `CLUSTER_THRESHOLD` where applicable. | `NOT_AUDITED` | — | — |
| `GATE-A-006` | 5999 | Dataset populations use exactly `NBAIOT_NATURAL_DEVICES`, `CICIOT_FILE_CLIENTS`, `NBAIOT_DIRICHLET_CLIENTS`, `EDGE_SENSOR_CLIENTS`, or `EDGE_TEMPORAL_CLIENTS` where applicable. | `NOT_AUDITED` | — | — |
| `GATE-A-007` | 6000 | Every locked numerical value used by code is traceable to Part I §11 or its authoritative detailed section. | `NOT_AUDITED` | — | — |
| `GATE-A-008` | 6001 | No mandatory grid has silently lost a cell. | `NOT_AUDITED` | — | — |
| `GATE-A-009` | 6002 | No unregistered value has been inserted into a locked grid. | `NOT_AUDITED` | — | — |
| `GATE-A-010` | 6003 | Canonical and sensitivity conditions are distinguishable in configuration and artifacts. | `NOT_AUDITED` | — | — |
| `GATE-A-011` | 6004 | A sensitivity cell cannot be relabelled as canonical after outcomes are observed. | `NOT_AUDITED` | — | — |
| `GATE-A-012` | 6005 | Optional analyses remain explicitly optional and cannot replace mandatory evidence. | `IMPLEMENTED` | `PASS` | Recipes carry a typed campaign role and campaign reporting records optional missing evidence without substituting it for mandatory requirements. |

### Gate B

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-B-001` | 6011 | The physical source and canonical dataset identity are recorded. | `IMPLEMENTED` | `PASS` | Canonical manifests bind each materialized dataset to its typed identity and are rejected on absence, corruption, or identity mismatch. |
| `GATE-B-002` | 6012 | Declared model-input features match the dataset-specific protocol. | `IMPLEMENTED` | `PASS` | Dataset schemas lock ordered feature fields; readers reject unaudited source schemas and preprocessing consumes each protocol’s declared input-feature sequence. |
| `GATE-B-003` | 6013 | Label normalization is deterministic and auditable. | `IMPLEMENTED` | `PASS` | CICIoT retains the raw label, applies deterministic trim/uppercase normalization, validates it against the locked vocabulary, and exposes unrecognized labels in its audit. |
| `GATE-B-004` | 6014 | Missing, non-finite, and ineligible rows follow Part I §2.2.1 exactly; no silent imputation, zero-fill, clipping, capping, infinity replacement, or label inference occurs. | `IMPLEMENTED` | `PASS` | Model-input admission excludes null/non-finite rows without transformation and records exact exclusion evidence; preprocessing and N-BaIoT reader tests cover both behaviors. |
| `GATE-B-005` | 6015 | Stable row identity and source provenance survive preprocessing and splitting. | `IMPLEMENTED` | `PASS` | Readers emit stable row and relative source identities, while preprocessing exclusion evidence persists affected stable row IDs. |
| `GATE-B-006` | 6016 | Dataset-specific exclusions are counted and reported. | `IMPLEMENTED` | `PASS` | Typed validation/exclusion contracts require positive affected counts and exact aggregate totals; preprocessing tests verify persisted evidence. |
| `GATE-B-007` | 6017 | N-BaIoT preserves the nine natural physical devices for the confirmatory population. | `IMPLEMENTED` | `PASS` | Population declarations lock nine N-BaIoT physical devices and capabilities identify the population as confirmatory; registry tests assert the count. |
| `GATE-B-008` | 6018 | CICIoT2023 does not invent physical-device identities from unavailable provenance. | `IMPLEMENTED` | `PASS` | CICIoT is typed as file-defined pseudo-clients with physical-device provenance unavailable; population declarations reject a physical-device interpretation. |
| `GATE-B-009` | 6019 | Edge-IIoTset uses only the client definition and temporal information justified by Part I §9 and Part II §4. | `IMPLEMENTED` | `PASS` | Edge uses separate source-defined and verified-temporal populations; temporal construction requires the locked chronological protocol. |

### Gate C

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-C-001` | 6023 | Each result references an immutable population identity. | `IMPLEMENTED` | `PASS` | Typed `PopulationId` declarations bind every construction/result and persisted population artifacts validate the identity before loading. |
| `GATE-C-002` | 6024 | Client membership is deterministic for a fixed population coordinate. | `IMPLEMENTED` | `PASS` | Construction sorts membership by client/stable-row identity and split tests verify deterministic assignment for a fixed seed. |
| `GATE-C-003` | 6025 | Natural-device, file-defined, synthetic/Dirichlet, external, and temporal populations cannot be silently mixed. | `IMPLEMENTED` | `PASS` | The population registry resolves each typed identity exactly once, and declarations constrain identity kind to the dataset/claim boundary. |
| `GATE-C-004` | 6026 | Population construction never uses held-out test outcomes. | `NOT_AUDITED` | — | — |
| `GATE-C-005` | 6027 | FAMILY_THRESHOLD is enabled only where the locked physical-family taxonomy is scientifically valid. | `IMPLEMENTED` | `PASS` | Population capabilities make family taxonomy unavailable outside N-BaIoT natural devices and dispatch emits the typed unavailable condition without a taxonomy. |
| `GATE-C-006` | 6028 | CLUSTER_THRESHOLD receives exactly the eligible client population declared for the experiment. | `IMPLEMENTED` | `PASS` | Threshold construction accepts the declared eligible local-quantile cohort, validates client partition/membership equality, and returns a typed unavailable state when the eligible cohort cannot support the locked group count. |
| `GATE-C-007` | 6029 | Empty, singleton, and excluded groups remain visible rather than being silently dropped. | `IMPLEMENTED` | `PASS` | Population/evaluation contracts retain explicit exclusion reasons, and family/group contracts reject silently invalid empty memberships. |
| `GATE-C-008` | 6030 | Client counts in tables equal the audited population manifest. | `IMPLEMENTED` | `PASS` | Population-manifest validation rejects mismatched accepted-client counts and membership client sets before persisted evidence can load. |
| `GATE-C-009` | 6032 | For every persistent-client result, the same immutable `client_id` binds training, calibration, evaluation, local threshold state, and any personalized model state exactly as Part I §3.3A requires. | `NOT_AUDITED` | — | — |
| `GATE-C-010` | 6033 | No unseen-client or intermittent-client interpretation is inferred from the calibration cold-start experiment. | `NOT_AUDITED` | — | — |

### Gate D

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-D-001` | 6037 | Train, calibration, and evaluation partitions are disjoint by immutable row identity. | `IMPLEMENTED` | `PASS` | Split construction and preprocessing validation reject any stable-row overlap across partition roles; split tests verify row conservation and uniqueness. |
| `GATE-D-002` | 6038 | Benign training fit uses training rows only. | `IMPLEMENTED` | `PASS` | The locked non-temporal split assigns no attack rows to training or calibration, and training extraction is role-scoped. |
| `GATE-D-003` | 6039 | Calibration rows never enter reported held-out test metrics. | `IMPLEMENTED` | `PASS` | Calibration loading rejects evaluation partition artifacts and calibration/evaluation stable-row overlap before threshold construction. |
| `GATE-D-004` | 6040 | Test outcomes never influence split construction, eligibility, threshold tuning, model selection, or comparator tuning. | `NOT_AUDITED` | — | — |
| `GATE-D-005` | 6041 | `n_k_source` is computed before experimental subsampling. | `NOT_AUDITED` | — | — |
| `GATE-D-006` | 6042 | Primary eligibility is exactly `n_k_source >= 100`. | `IMPLEMENTED` | `PASS` | The shared calibration eligibility protocol locks `MINIMUM_BENIGN_SUPPORT = 100`; eligibility decisions reject smaller benign calibration support with a typed reason. |
| `GATE-D-007` | 6043 | Eligibility is fixed before test evaluation and identical across compared threshold policies. | `IMPLEMENTED` | `PASS` | Eligibility accepts only declared calibration partitions and paired-policy construction requires one common eligible cohort, rejecting any mismatch. |
| `GATE-D-008` | 6044 | Calibration-size ablations use `m` independently of the source-pool eligibility decision. | `NOT_AUDITED` | — | — |
| `GATE-D-009` | 6045 | Temporal experiments use genuine chronology: historical calibration < future recalibration < future evaluation. | `IMPLEMENTED` | `PASS` | Temporal population construction requires verified Edge chronology and the locked chronological split protocol; invalid chronology produces explicit exclusion evidence. |
| `GATE-D-010` | 6046 | Generated pseudo-time or file ordering is never substituted for real timestamps where chronology is required. | `IMPLEMENTED` | `PASS` | N-BaIoT/CICIoT capabilities explicitly reject source/file order as chronology; Edge temporal eligibility requires paired PCAP timestamp evidence. |

### Gate E

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-E-001` | 6050 | Every threshold comparison references one named preprocessing protocol identity. | `IMPLEMENTED` | `PASS` | Every experiment declaration carries a typed preprocessing protocol, and training/prepared-data coordinates persist that identity. |
| `GATE-E-002` | 6051 | `FEDERATED_CLIENT_LOCAL_STANDARD` is fit client-locally on benign training only in the confirmatory protocol. | `IMPLEMENTED` | `PASS` | The locked federated scientific preprocessing method is client-local StandardScaler fitted on the training role; locked split tests establish benign-only training input. |
| `GATE-E-003` | 6052 | `FEDERATED_POOLED_MIN_MAX` is never silently mixed into the confirmatory ladder. | `IMPLEMENTED` | `PASS` | The confirmatory declaration has one primary local-standard protocol; pooled MinMax is a separately typed supportive method/coordinate. |
| `GATE-E-004` | 6053 | `CENTRALIZED_POOLED_MIN_MAX` is independently fitted and never reuses federated fitted states. | `IMPLEMENTED` | `PASS` | Centralized preprocessing has a distinct pooled owner/state/branch and explicitly rejects federated client fitted states. |
| `GATE-E-005` | 6054 | Threshold methods cannot fit, select, or alter model-input preprocessing. | `NOT_AUDITED` | — | — |
| `GATE-E-006` | 6055 | Cluster-fingerprint standardization is kept distinct from model-input preprocessing. | `IMPLEMENTED` | `PASS` | Cluster protocol separately locks fingerprint StandardScaler/features while model-input preprocessing has its own typed protocol/state identity. |
| `GATE-E-007` | 6056 | Serialization/reload equivalence uses the `1e-12` engineering tolerance only for reload validation. | `IMPLEMENTED` | `PASS` | Preprocessing reload validation uses the typed absolute tolerance in `reload_and_compare_transform`; preprocessing state tests exercise the locked `1e-12` check. |
| `GATE-E-008` | 6057 | A reload tolerance comparison is never used to establish scientific fixed-score identity. | `IMPLEMENTED` | `PASS` | Fixed-score validation compares immutable manifest identity and exact persisted score content, independently of preprocessing reload checks. |

### Gate F

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-F-001` | 6061 | Every **federated training** execution has exactly one scientific terminal detector at round `200`; `FEDAVG_LOCAL_FINE_TUNING` starts from that detector and produces separately identified post-training client-personalized states after exactly ten local epochs. | `IMPLEMENTED` | `PASS` | Fine-tuning rejects any source other than the seed-matched FedAvg terminal round 200 and its protocol rejects non-ten-epoch conditions; execution keeps fixed training/score workspace evidence separate from threshold variants. |
| `GATE-F-002` | 6062 | Recovery checkpoints are used only to resume interrupted execution. | `NOT_AUDITED` | — | — |
| `GATE-F-003` | 6063 | Diagnostic checkpoints are observational and never become score sources. | `IMPLEMENTED` | `PASS` | Fixed-score workspace execution scores the terminal model once and supplies the same score manifest to threshold variants; diagnostic snapshot protocols are not a scoring input. |
| `GATE-F-004` | 6064 | SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD do not trigger policy-specific retraining. | `IMPLEMENTED` | `PASS` | The stage runner keys fixed workspace reuse by training coordinate and injects identical context/training/scores into each threshold-method workspace. |
| `GATE-F-005` | 6065 | FedAvg confirmatory models are distinct from FedProx, Ditto, centralized, preprocessing-sensitivity, and post-FedAvg fine-tuned client states where the protocol requires separate detector identities. | `NOT_AUDITED` | — | — |
| `GATE-F-006` | 6066 | No test AUROC, test label, threshold result, DATP effect, or external result changes the terminal detector. | `NOT_AUDITED` | — | — |
| `GATE-F-007` | 6067 | FedProx executes the complete locked `mu` grid. | `NOT_AUDITED` | — | — |
| `GATE-F-008` | 6068 | FedProx persists broadcast/returned state identity and produces `L2Drift`, `RMSDrift`, terminal-50 drift summaries, and `DriftSuppression` exactly as Part I §7.1A requires. | `NOT_AUDITED` | — | — |
| `GATE-F-009` | 6069 | Client-round FedProx drift cells remain nested diagnostics and are never treated as independent inferential observations. | `NOT_AUDITED` | — | — |
| `GATE-F-010` | 6070 | Ditto executes the complete locked `lambda_D` grid and preserves genuine persistent-personalized-state semantics before using the name Ditto. | `NOT_AUDITED` | — | — |
| `GATE-F-011` | 6072 | `FEDAVG_LOCAL_FINE_TUNING` initializes every client from the exact seed-matched FedAvg round-200 model, uses a fresh optimizer state, exactly 10 benign-training epochs, no early stopping, and no calibration/evaluation/attack-label access. | `IMPLEMENTED` | `PASS` | Fine-tuning source and protocol enforce round-200/ten-epoch requirements and client training input is role-scoped. |
| `GATE-F-012` | 6073 | Fine-tuned client models are frozen before scoring and are never re-fine-tuned per threshold policy. | `NOT_AUDITED` | — | — |
| `GATE-F-013` | 6074 | The deterministic fine-tuning seed identity includes `(dataset_id,population_id,training_seed,client_id)` with purpose `FEDAVG_LOCAL_FINE_TUNING`. | `NOT_AUDITED` | — | — |

### Gate G

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-G-001` | 6078 | Exactly one canonical evaluation-score artifact exists per fixed detector / preprocessing / population / seed coordinate. | `IMPLEMENTED` | `PASS` | Fixed workspace reuse and persisted score-manifest/content identity bind one score artifact to the training coordinate. |
| `GATE-G-002` | 6079 | SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD reference that same score artifact identity within a ladder. | `IMPLEMENTED` | `PASS` | Fixed-score comparison validation requires identical score manifest and persisted content across distinct threshold methods. |
| `GATE-G-003` | 6080 | Threshold methods do not independently regenerate detector scores. | `IMPLEMENTED` | `PASS` | Stage execution injects one fixed score workspace into threshold-method variants rather than rescoring per policy. |
| `GATE-G-004` | 6081 | Ordered row identities are preserved across score, label, and evaluation artifacts. | `IMPLEMENTED` | `PASS` | Federated evaluation score arrays require score, label, and stable-row sequences to align exactly. |
| `GATE-G-005` | 6082 | Calibration-score identity is likewise shared where the experiment requires fixed calibration evidence. | `IMPLEMENTED` | `PASS` | Fixed-score controls require one calibration partition role plus identical score manifest/content identity. |
| `GATE-G-006` | 6083 | A higher reconstruction error always denotes greater anomaly evidence. | `IMPLEMENTED` | `PASS` | Evaluation predicts attack exactly when continuous reconstruction error strictly exceeds the threshold. |
| `GATE-G-007` | 6084 | AUROC is computed from the canonical continuous score/label artifact, not from thresholded predictions. | `IMPLEMENTED` | `PASS` | Client metrics calculate AUROC directly from continuous score values and labels, independently of confusion predictions. |
| `GATE-G-008` | 6085 | Any policy-specific AUROC difference within a fixed-score ladder is treated as an identity/provenance failure. | `IMPLEMENTED` | `PASS` | Fixed-score quality-control invariance rejects policy-specific AUROC or AP differences. |

### Gate H

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-H-001` | 6089 | Every DATP-compatible threshold method uses benign calibration data only. | `IMPLEMENTED` | `PASS` | Calibration loading rejects non-benign labels before all threshold construction inputs are created. |
| `GATE-H-002` | 6090 | Attack-labelled rows never affect threshold values, q selection, eligibility, cluster count, comparator tuning, shrinkage, or conformal significance level. | `IMPLEMENTED` | `PASS` | The benign calibration loader fails on any attack label, so downstream policy inputs cannot contain attack-labelled calibration evidence. |
| `GATE-H-003` | 6091 | Calibration and evaluation rows are disjoint. | `IMPLEMENTED` | `PASS` | Calibration service validates calibration/evaluation stable-row disjointness before eligibility/construction. |
| `GATE-H-004` | 6092 | Type-7 empirical quantiles use float64 and are not rounded before threshold application. | `IMPLEMENTED` | `PASS` | Quantile construction materializes scores as `float64` and calls locked NumPy linear (type-7) interpolation directly into the threshold value. |
| `GATE-H-005` | 6093 | LOCAL_CONFORMAL_THRESHOLD is the explicit conformal-order-statistic exception and is not routed through type-7 interpolation. | `IMPLEMENTED` | `PASS` | Finite-sample conformal construction has a separately tested rank-index/order-statistic implementation. |
| `GATE-H-006` | 6094 | Calibration-size subsampling follows Part II §2.3A exactly: immutable-row ordering, SHA-256 seed derivation, PCG64, without replacement, prefix nesting. | `NOT_AUDITED` | — | — |
| `GATE-H-007` | 6095 | The 10 nested calibration replicates are summarized within training seed and never treated as independent seeds. | `NOT_AUDITED` | — | — |
| `GATE-H-008` | 6096 | Shared-calibration contributor-availability sensitivity enumerates every permitted omission subset exhaustively, changes only shared-summary contribution, and evaluates every resulting shared threshold on the unchanged full eligible client population. | `NOT_AUDITED` | — | — |
| `GATE-H-009` | 6097 | Omission subsets are never interpreted as independent replications or used to inflate the seed count. | `NOT_AUDITED` | — | — |
| `GATE-H-010` | 6098 | Every threshold-stage artifact is generated under the Part I §3.2A protocol-compliant participant assumption; no experiment silently injects fabricated thresholds, support counts, summaries, fingerprints, sketches, scores, or client identities. | `NOT_AUDITED` | — | — |
| `GATE-H-011` | 6099 | Contributor-availability sensitivity is labeled non-adversarial; it is never called Byzantine robustness, poisoning resistance, malicious-dropout robustness, or message-integrity validation. | `NOT_AUDITED` | — | — |
| `GATE-H-012` | 6100 | Any threshold-stage provenance/checksum/identity mismatch invalidates the artifact/coordinate and is not counted as an attack-defense success. | `NOT_AUDITED` | — | — |

### Gate I

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-I-001` | 6105 | Computes each eligible client's local q-quantile and takes the arithmetic mean of eligible local quantiles. | `IMPLEMENTED` | `PASS` | Shared construction requires eligible local quantiles and validates their unweighted arithmetic mean. |
| `GATE-I-002` | 6106 | Is never mislabeled as the exact pooled quantile. | `IMPLEMENTED` | `PASS` | Shared and exact-pooled constructions have separate typed methods/contracts, with tests confirming they differ. |
| `GATE-I-003` | 6107 | Applies one threshold to every eligible client. | `IMPLEMENTED` | `PASS` | Shared assignment validation requires every eligible client to carry the identical shared threshold. |
| `GATE-I-004` | 6110 | Uses each eligible client's own benign q-quantile. | `IMPLEMENTED` | `PASS` | Local construction validates that each assignment equals the client’s local benign quantile. |
| `GATE-I-005` | 6111 | Uses the same q and score evidence as SHARED_THRESHOLD in the confirmatory comparison. | `IMPLEMENTED` | `PASS` | Common eligible-cohort/fixed-score controls bind confirmatory shared and local comparisons to the same calibration/score evidence. |
| `GATE-I-006` | 6114 | Uses only the locked physical-family taxonomy. | `IMPLEMENTED` | `PASS` | Family construction requires declared family memberships and population capabilities expose the taxonomy only for natural N-BaIoT devices. |
| `GATE-I-007` | 6115 | Forms family thresholds exactly from eligible family-member local thresholds. | `IMPLEMENTED` | `PASS` | Family group validation requires exact member/local-quantile equality and the unweighted group mean. |
| `GATE-I-008` | 6116 | Is unavailable where no defensible taxonomy exists. | `IMPLEMENTED` | `PASS` | Dispatch emits typed `FAMILY_TAXONOMY_UNAVAILABLE` when no family mapping is supplied. |
| `GATE-I-009` | 6119 | Fingerprint is exactly `[mean(error), std(error), skewness(error), p95(error)]`. | `IMPLEMENTED` | `PASS` | Cluster protocol validates the exact locked feature tuple/order. |
| `GATE-I-010` | 6120 | Canonical clustering uses the separate score-side fingerprint-standardization contract, canonical `K=3`, and the locked initialization/seed handling required by Part II §7.1. | `IMPLEMENTED` | `PASS` | Cluster protocol validates StandardScaler fingerprint standardization, K=3, k-means++, locked n_init/max_iter/random state. |
| `GATE-I-011` | 6121 | Cluster threshold is the mean of member local thresholds. | `IMPLEMENTED` | `PASS` | Cluster membership validation checks the declared local-threshold aggregation; canonical protocol locks arithmetic mean. |
| `GATE-I-012` | 6122 | CLUSTER_THRESHOLD never changes the detector, performs model clustering, or acquires a privacy claim. | `NOT_AUDITED` | — | — |
| `GATE-I-013` | 6123 | Cluster identities are aligned before across-seed switch-frequency reporting. | `IMPLEMENTED` | `PASS` | Cluster switch-frequency analysis aligns target labels to the smallest-seed reference before computing switches. |

### Gate J

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-J-001` | 6127 | Exact pooled benign quantile uses the type-7 pooled oracle. | `IMPLEMENTED` | `PASS` | `construct_pooled_shared_quantile` uses the locked exact empirical quantile. |
| `GATE-J-002` | 6128 | Sample-weighted shared construction uses the declared eligible calibration weights. | `IMPLEMENTED` | `PASS` | The construction retains calibration counts and normalizes their declared weights. |
| `GATE-J-003` | 6129 | Fixed shrinkage executes the full λ curve and never selects a winner post hoc. | `IMPLEMENTED` | `PASS` | Dispatch returns every fixed protocol weight; no selection path exists. |
| `GATE-J-004` | 6130 | Size-aware shrinkage uses `n_k_used/(n_k_used+100)` and never substitutes `n_k_source` for `m` in a subsampled cell. | `IMPLEMENTED` | `PASS` | Each assignment records the used calibration support and its locked support-based weight. |
| `GATE-J-005` | 6131 | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` communicates only the predeclared benign summaries and includes the full pooled variance decomposition. | `IMPLEMENTED` | `PASS` | Per-client float64 summaries and the validated within/between pooled decomposition are retained. |
| `GATE-J-006` | 6132 | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is never called Laridi-faithful. | `IMPLEMENTED` | `PASS` | The persisted benign-summary comparator report explicitly rejects a Laridi-faithfulness claim. |
| `GATE-J-007` | 6133 | KLL uses float64, canonical `k=400`, sensitivity `{200,800}`, ascending client merge order, and the locked inclusive-rank semantics. | `IMPLEMENTED` | `PASS` | The KLL protocol locks the grid; construction sorts clients and explicitly requests the library's inclusive rank. |
| `GATE-J-008` | 6134 | KLL observed empirical rank/threshold errors are measured against the exact pooled type-7 oracle. | `IMPLEMENTED` | `PASS` | Each reconstruction retains empirical-rank and absolute/relative threshold errors against the exact pooled oracle. |
| `GATE-J-009` | 6135 | KLL implementation randomness follows Part II §9.2 and remains nested within training seed. | `IMPLEMENTED` | `PASS` | Each reconstruction persists a distinct deterministic seed derived from its enclosing training seed. |
| `GATE-J-010` | 6136 | `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` uses float64, arithmetic mean, sample standard deviation with `ddof=1`, and the locked `{shared, local}` 2×2 scope comparison; it is never presented as a faithful reproduction of Meidan's complete detector. | `IMPLEMENTED` | `PASS` | The typed estimator is restricted to shared/local scope and the report retains both estimator families; prior-art output distinguishes it from Meidan's complete detector. |
| `GATE-J-011` | 6137 | LOCAL_CONFORMAL_THRESHOLD reports held-out benign coverage and its limitations; it does not claim arbitrary client-conditional validity. | `IMPLEMENTED` | `PASS` | The report retains held-out benign coverage and serializes an explicit finite-sample, retained-evidence claim boundary. |

### Gate K

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-K-001` | 6143 | Every declared factor level was executed or has a recorded pre-specified infeasibility reason. | `IMPLEMENTED` | `PASS` | Materialized coordinates are rejected when missing or unauthorized; graph-validated infeasibility has a typed disposition. |
| `GATE-K-002` | 6144 | Every required comparison method is present. | `IMPLEMENTED` | `PASS` | Coordinate completeness derives the full declaration grid and rejects absent method coordinates. |
| `GATE-K-003` | 6145 | Every required seed is present; confirmatory inference requires exactly ten valid paired seed deltas. | `IMPLEMENTED` | `PASS` | The pre-registered confirmatory cohort and inference protocol both require exactly ten seeds. |
| `GATE-K-004` | 6146 | All declared nested replicates are present where required. | `IMPLEMENTED` | `PASS` | Nested reconstruction and calibration analyses retain their declared replicate identities and validate complete grids. |
| `GATE-K-005` | 6147 | Required outcomes, diagnostics, tables, and figures were produced or explicitly marked unavailable under a roadmap rule. | `NOT_AUDITED` | — | — |
| `GATE-K-006` | 6148 | Null, reversed, unstable, and unfavorable outcomes remain in the result set. | `NOT_AUDITED` | — | — |
| `GATE-K-007` | 6149 | No experiment was dropped because it weakened the narrative. | `NOT_AUDITED` | — | — |
| `GATE-K-008` | 6150 | Optional experiments are visually and semantically separated from mandatory evidence. | `NOT_AUDITED` | — | — |
| `GATE-K-009` | 6151 | Part II §8.6 produces every feasible `m in {0,1,2,3,4}` omission subset, exact seed-level subset summaries, and the identities of worst-case omission sets. | `IMPLEMENTED` | `PASS` | The contributor report retains each omission cell, m-level seed summaries, unavailable cells, and worst-case omission identities. |

### Gate L

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-L-001` | 6155 | Prediction semantics are exactly `attack iff score > threshold`. | `IMPLEMENTED` | `PASS` | The sole decision helper delegates to strict score exceedance. |
| `GATE-L-002` | 6156 | Confusion counts are computed from held-out evaluation rows only. | `IMPLEMENTED` | `PASS` | Confusion construction rejects calibration and duplicate source rows. |
| `GATE-L-003` | 6157 | Per-client metrics are computed before cross-client aggregation where valid client identity exists. | `IMPLEMENTED` | `PASS` | Evaluation constructs each client result before population aggregation. |
| `GATE-L-004` | 6158 | `CV(FPR)` uses only the eligible FPR-evaluable client population defined in Part III. | `IMPLEMENTED` | `PASS` | Population aggregation collects FPR values only from the typed FPR-evaluable cohort. |
| `GATE-L-005` | 6159 | Absolute dispersion metrics accompany CV where low mean FPR could make CV unstable or misleading. | `NOT_AUDITED` | — | — |
| `GATE-L-006` | 6160 | Attack-sensitive metrics are marked unavailable when valid per-client attack assignment is absent. | `IMPLEMENTED` | `PASS` | Attack-rate and attack-derived metric paths return typed unavailability for invalid assignment. |
| `GATE-L-007` | 6161 | Undefined denominators remain undefined; they are never converted to zero. | `IMPLEMENTED` | `PASS` | Zero-mean and undefined-class cases retain typed undefined status and reason. |
| `GATE-L-008` | 6162 | AUROC/AP are detector-quality controls and do not become threshold-scope verdicts. | `IMPLEMENTED` | `PASS` | Fixed-score comparisons reject a policy-specific AUROC or AP difference. |
| `GATE-L-009` | 6163 | Held-out target-attainment error is computed from held-out benign rows and is never replaced by calibration-set exceedance. | `IMPLEMENTED` | `PASS` | Operating-point diagnostics use the held-out client FPR for target error. |
| `GATE-L-010` | 6164 | Calibration-to-held-out benign generalization gap uses the exact calibration scores that constructed each scalar threshold, the strict `score > threshold` exceedance rule, and the unchanged held-out benign evaluation rows. | `IMPLEMENTED` | `PASS` | The diagnostic pairs retained calibration scores with held-out FPR under strict exceedance semantics. |
| `GATE-L-011` | 6165 | Calibration-generalization-gap diagnostics never feed threshold fitting, policy selection, model selection, or claim-tier promotion. | `NOT_AUDITED` | — | — |
| `GATE-L-012` | 6166 | P10 Macro-F1 and worst-client balanced accuracy remain visible when available, including unfavorable trade-offs. | `NOT_AUDITED` | — | — |

### Gate M

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-M-001` | 6170 | Training seed is the independent inferential unit. | `IMPLEMENTED` | `PASS` | Confirmatory validation requires the exact ten-seed cohort and constructs one paired contrast per seed. |
| `GATE-M-002` | 6171 | Nested replicates are summarized within seed before across-seed inference. | `IMPLEMENTED` | `PASS` | Across-seed inference accepts only one ordered paired contrast for each locked seed; nested experiment owners retain and summarize their replicate grids first. |
| `GATE-M-003` | 6172 | Confirmatory delta direction matches the Part III definition. | `IMPLEMENTED` | `PASS` | The endpoint locks `SHARED_THRESHOLD - LOCAL_THRESHOLD` for `CV(FPR)`. |
| `GATE-M-004` | 6173 | The confirmatory statistic is the arithmetic mean of the ten paired seed-level deltas. | `IMPLEMENTED` | `PASS` | The BCa estimator and precision diagnostics use the arithmetic mean of the paired delta vector. |
| `GATE-M-005` | 6174 | The confirmatory uncertainty is the locked two-sided 95% BCa interval over paired seed deltas. | `IMPLEMENTED` | `PASS` | The locked protocol specifies a 95% paired arithmetic-mean BCa interval with 10,000 bootstrap replicates. |
| `GATE-M-006` | 6175 | Degenerate/invalid BCa states produce `CONFIRMATORY_INFERENCE_UNAVAILABLE` rather than a substituted method. | `IMPLEMENTED` | `PASS` | Degenerate and blocked BCa outcomes emit the dedicated unavailable confirmatory decision; no replacement interval determines the verdict. |
| `GATE-M-007` | 6176 | Wilcoxon is paired, uses exact computation where feasible, and records fallback/approximation behavior. | `IMPLEMENTED` | `PASS` | Paired Wilcoxon locks two-sided Pratt handling, selects exact when feasible, and persists the selected method and fallback reason. |
| `GATE-M-008` | 6177 | Rank-biserial effect size is the matched-pairs version, not unpaired Cliff's delta. | `IMPLEMENTED` | `PASS` | The inference protocol and computation owner require matched-pairs rank-biserial correlation. |
| `GATE-M-009` | 6178 | Secondary emphasized p-values use predeclared families and Holm correction. | `IMPLEMENTED` | `PASS` | Confirmatory Wilcoxon and exact-sign p-values form one predeclared two-hypothesis robustness family and are Holm-adjusted before publication. |
| `GATE-M-010` | 6179 | Exact paired sign-test uses only non-zero paired deltas, an exact `Binomial(n_nonzero, 0.5)` null, and no normal approximation; zero deltas remain visible in sign counts. | `IMPLEMENTED` | `PASS` | The exact sign-test owner retains directional nonzero counts, excludes only zeros from the binomial null, and computes the combinatorial two-sided value. |
| `GATE-M-011` | 6180 | Leave-one-seed-out precision diagnostics are reported without changing the inferential sample. | `IMPLEMENTED` | `PASS` | Precision diagnostics retain all leave-one-seed-out means alongside the unchanged full ten-seed estimate. |
| `GATE-M-012` | 6181 | Leave-one-device-out confirmatory influence uses the same ten training seeds and already generated scores; the nine omitted-device means are dependent diagnostics and are never treated as nine independent replicates. | `IMPLEMENTED` | `PASS` | Influence recomputes only threshold/evaluation quantities from fixed score artifacts and summarizes each omitted device across the locked seed cohort. |
| `GATE-M-013` | 6182 | `LODO_HIGH_INFLUENCE` is evaluated exactly as Part III §15.1A specifies; the 25% influence boundary is descriptive and never modifies the BCa decision rule. | `IMPLEMENTED` | `PASS` | The influence owner derives both prospective triggers, including the unmodified 0.25 relative-shift boundary, independently of the BCa decision. |
| `GATE-M-014` | 6183 | No seed or client is removed because of effect direction. | `IMPLEMENTED` | `PASS` | Confirmatory analysis no longer exposes a seed-exclusion path; validation requires every locked seed and influence output retains every omitted client. |

### Gate N

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-N-001` | 6187 | Mechanism analyses use only pre-specified variables and populations. | `NOT_AUDITED` | — | — |
| `GATE-N-002` | 6188 | Jensen–Shannon constructions use the exact locked binning/log convention from Part II. | `IMPLEMENTED` | `PASS` | The mechanism owner uses pooled benign-calibration type-7 64-bin quantile edges, collapses duplicates, blocks collapsed grids, and uses unsmoothed base-2 mean-pairwise JSD. |
| `GATE-N-003` | 6189 | Association analyses use associative, not causal, language. | `IMPLEMENTED` | `PASS` | The mechanism result is explicitly an association record; publication claim rendering prohibits promotion of supportive evidence to causal claims. |
| `GATE-N-004` | 6190 | `n < 5` association cases use the declared insufficient-evidence state rather than fabricated coefficients. | `IMPLEMENTED` | `PASS` | The association owner now returns the typed insufficient-evidence state with no coefficients, p-values, or regression diagnostics for fewer than five observations. |
| `GATE-N-005` | 6191 | Cluster stability reports memberships, sizes, empty clusters, singleton clusters, ARI, and switch behavior where specified. | `IMPLEMENTED` | `PASS` | Cluster stability retains complete partitions and diagnostics; a campaign owner deterministically aligns labels and reports per-client switch frequencies. |
| `GATE-N-006` | 6192 | Recovery-of-local-gap quantities are not clipped to `[0,1]`. | `IMPLEMENTED` | `PASS` | Grouped recovery preserves raw fractions, including values above one and below zero. |
| `GATE-N-007` | 6193 | Non-positive SHARED_THRESHOLD→LOCAL_THRESHOLD denominators use the declared unavailable state. | `IMPLEMENTED` | `PASS` | The grouped-recovery owner returns a typed undefined assessment with a reason when the shared-to-local gap is non-positive. |
| `GATE-N-008` | 6194 | Natural-device mechanism leave-one-device-out analysis never retrains, refits preprocessing, or rescores; it recomputes only the population-dependent heterogeneity/shared-threshold quantities defined in Part II §7.4. | `IMPLEMENTED` | `PASS` | Influence derives reduced manifests from the original fixed-score artifacts and recomputes only calibration/threshold/evaluation aggregates. |
| `GATE-N-009` | 6195 | The `9 × 10` leave-one-device seed cells are never treated as 90 independent observations; the association influence analysis remains a sensitivity analysis over the original population/seed structure. | `IMPLEMENTED` | `PASS` | Per-device summaries retain the ten seed deltas and remain diagnostics; no inferential procedure receives the flattened cells. |
| `GATE-N-010` | 6196 | Part II §7.5 reports exact per-seed FPR/TPR direction counts without inventing a floating tolerance or post-hoc materiality cutoff. | `IMPLEMENTED` | `PASS` | Direction-count owner compares deltas with exact `<`, `==`, and `>` semantics and marks partial TPR evidence unavailable. |
| `GATE-N-011` | 6197 | Part II §7.5A support-versus-burden Spearman coefficients use only the common valid client set, require at least five clients plus nonconstant inputs, use average ranks for ties, and do not report client-level inferential p-values from the nine-device population. | `IMPLEMENTED` | `PASS` | Owner intersects support, movement, and valid-FPR clients, enforces five-client/nonconstant preconditions, and uses average ranks without p-values. |
| `GATE-N-012` | 6198 | The support-versus-burden diagnostic is interpreted associatively and never used to claim that calibration support causes client harm. | `IMPLEMENTED` | `PASS` | Mechanism claim wording is explicitly associative and non-confirmatory. |
| `GATE-N-013` | 6199 | Equity–utility Pareto analysis never invents a scalarized winner. | `IMPLEMENTED` | `PASS` | The owner computes explicit nondominance on mean coordinates and rejects mismatched seed cohorts; it has no scalar selection output. |
| `GATE-N-014` | 6201 | Every FedProx, `FEDAVG_LOCAL_FINE_TUNING`, and Ditto stress condition reports the common Part I §7.2B score/threshold-alignment tuple whenever inputs are valid. | `IMPLEMENTED` | `PASS` | Every stress report now renders the condition’s per-seed five alignment metrics, raw DeltaScope, and un-clipped ScopeAbsorption with the declared unavailable denominator state; reductions remain in the adjacent report. |
| `GATE-N-015` | 6202 | `ScopeAbsorption` and every `AlignmentReduction` are un-clipped; non-positive FedAvg denominators produce the declared unavailable states rather than an epsilon adjustment. | `IMPLEMENTED` | `PASS` | Alignment reductions retain the raw `1 - condition/reference` value; non-positive FedAvg references emit the typed unavailable state without epsilon stabilization. |
| `GATE-N-016` | 6203 | `FEDAVG_LOCAL_FINE_TUNING` uses exactly ten benign-training local epochs from the exact round-200 FedAvg weights, a fresh optimizer state, no early stopping, and no calibration/evaluation/attack-label access. | `IMPLEMENTED` | `PASS` | Fine-tuning validates the FedAvg round-200 source, locks ten local epochs, and invokes the benign training-data update owner with a fresh per-client optimizer update. |
| `GATE-N-017` | 6204 | The N-BaIoT helped/harmed profile reports all ten seed-level fractions and every physical-device help/harm frequency; the 9×10 cells are never treated as independent observations. | `IMPLEMENTED` | `PASS` | Client-impact summaries retain each seed fraction and report per-device frequencies across seed observations without treating the grid as independent evidence. |
| `GATE-N-018` | 6205 | Calibration-support strata are frozen from ascending `SupportScore_k=median_s(n_{s,k,source})` with canonical-client-ID tie-break into ranks `1..3`, `4..6`, `7..9`; if exactly nine eligible N-BaIoT clients are not available, the stratum analysis emits the declared unavailable state. | `IMPLEMENTED` | `PASS` | The stratum owner takes per-client medians across declared seeds, orders ties by canonical client ID, assigns the fixed 3/3/3 ranks, and returns an explicit unavailable record unless exactly nine N-BaIoT devices occur in every seed. |
| `GATE-N-019` | 6206 | The empirical policy-selection surface emits only the declared typed states and raw nondominated sets; no learned classifier, cutoff, scalar utility weight, or post-hoc production rule is fitted. | `IMPLEMENTED` | `PASS` | The typed owner reports only unavailable, unique-nondominated, or multiple-nondominated states and the raw nondominated policy set; it has no fitted-selector input or scalar utility output. |
| `GATE-N-020` | 6207 | `H_TAUTOLOGY` reporting uses disjoint calibration/evaluation row identities and shows calibration exceedance, held-out target error, and calibration-generalization gap rather than calling local q95 held-out FPR “guaranteed.” | `IMPLEMENTED` | `PASS` | Calibration service validates stable row-identity disjointness before threshold construction; held-out operating diagnostics and the confirmatory table render calibration exceedance, calibration target error, held-out target error, and calibration-generalization gap. |

### Gate O

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-O-001` | 6211 | CICIoT2023 findings are described only for file-defined pseudo-clients and never generalized to the original physical-device topology. | `NOT_AUDITED` | — | — |
| `GATE-O-002` | 6212 | Edge-IIoTset conclusions are limited to the metrics and client semantics actually available. | `NOT_AUDITED` | — | — |
| `GATE-O-003` | 6213 | Unavailable Edge attack metrics remain unavailable and are not reconstructed from unsupported labels. | `NOT_AUDITED` | — | — |
| `GATE-O-004` | 6214 | External validation is never promoted into a second confirmatory endpoint. | `NOT_AUDITED` | — | — |
| `GATE-O-005` | 6215 | Controlled Dirichlet partitions remain sensitivity evidence and are not called natural-device evidence. | `NOT_AUDITED` | — | — |
| `GATE-O-006` | 6216 | No extra dataset is added without an explicit roadmap amendment. | `NOT_AUDITED` | — | — |

### Gate P

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-P-001` | 6220 | Temporal evidence uses valid timestamps and genuine chronology only. | `NOT_AUDITED` | — | — |
| `GATE-P-002` | 6221 | Static, frozen-future, and one-shot-recalibrated states are computed exactly as Part II §12.1 specifies. | `NOT_AUDITED` | — | — |
| `GATE-P-003` | 6222 | Future evaluation never influences historical thresholding or future recalibration. | `NOT_AUDITED` | — | — |
| `GATE-P-004` | 6223 | `drift_excess`, `recovered_amount`, and `recovery_ratio` use Part III §14 definitions. | `NOT_AUDITED` | — | — |
| `GATE-P-005` | 6224 | `recovery_ratio` is undefined below the locked positive-materiality threshold. | `NOT_AUDITED` | — | — |
| `GATE-P-006` | 6225 | Temporal association diagnostics use the declared 64-bin common quantile grid and n≥5 requirement. | `NOT_AUDITED` | — | — |
| `GATE-P-007` | 6226 | Results are framed as one-shot threshold aging/recalibration evidence, not continuous drift handling. | `NOT_AUDITED` | — | — |

### Gate Q

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-Q-001` | 6230 | Every table/figure/result row can be traced back to its exact execution coordinate. | `NOT_AUDITED` | — | — |
| `GATE-Q-002` | 6231 | Artifact provenance records code version, dataset identity, population identity, seed, protocol identities, and dependency/library versions required by the method. | `NOT_AUDITED` | — | — |
| `GATE-Q-003` | 6232 | Ordered record identities are recoverable for score and label artifacts. | `NOT_AUDITED` | — | — |
| `GATE-Q-004` | 6233 | Re-running a deterministic coordinate reproduces the same identities and deterministic nested draws. | `NOT_AUDITED` | — | — |
| `GATE-Q-005` | 6234 | KLL serialized artifacts and library version are retained because implementation randomness can affect reconstruction. | `NOT_AUDITED` | — | — |
| `GATE-Q-006` | 6235 | Runtime tables record hardware, OS, runtime, and library versions. | `NOT_AUDITED` | — | — |
| `GATE-Q-007` | 6236 | Cross-machine timing comparisons are not made. | `NOT_AUDITED` | — | — |
| `GATE-Q-008` | 6237 | Missing artifacts cannot be silently regenerated under a different protocol identity and treated as original evidence. | `NOT_AUDITED` | — | — |

### Gate R

| ID | Source line | Audit requirement | Implementation disposition | Audit outcome | Evidence / remediation |
|---|---:|---|---|---|---|
| `GATE-R-001` | 6241 | The manuscript's confirmatory claim is supported only by Part II §5.1 and Part III §11. | `NOT_AUDITED` | — | — |
| `GATE-R-002` | 6242 | Supportive, mechanism, external, stress-test, boundary, operational, and exploratory evidence keeps its declared tier. | `NOT_AUDITED` | — | — |
| `GATE-R-003` | 6243 | A failed/null confirmatory endpoint is not rescued by CLUSTER_THRESHOLD, shrinkage, conformal, FedProx, Ditto, or an external dataset. | `NOT_AUDITED` | — | — |
| `GATE-R-004` | 6244 | Operational FPR equity is not presented as demographic or protected-attribute fairness. | `NOT_AUDITED` | — | — |
| `GATE-R-005` | 6245 | Structural raw-data locality is not called a formal privacy guarantee. | `NOT_AUDITED` | — | — |
| `GATE-R-006` | 6246 | Threshold-stage byte/runtime accounting is not called deployment validation. | `NOT_AUDITED` | — | — |
| `GATE-R-007` | 6247 | No fleet-scale claim is made from synthetic or file-defined pseudo-clients. | `NOT_AUDITED` | — | — |
| `GATE-R-008` | 6248 | LOCAL_THRESHOLD/local thresholds are not claimed as universally novel; prior-art boundaries in Part I §10.D remain visible. | `NOT_AUDITED` | — | — |
| `GATE-R-009` | 6249 | The manuscript defines probability calibration, anomaly operating-point calibration, and conformal calibration according to Part I §10.C.7A and does not demand ECE/Brier/NLL for DATP's non-probabilistic threshold object. | `NOT_AUDITED` | — | — |
| `GATE-R-010` | 6250 | The manuscript explicitly states the Part I §3.2A honest/protocol-compliant calibration assumption and does not imply Byzantine, poisoning, secure-aggregation, authenticated-message, or adversarial-calibration robustness. | `NOT_AUDITED` | — | — |
| `GATE-R-011` | 6251 | The Part I §10.D.9B source-grounded prior-art distinction table is present, uses only the locked categorical vocabulary, and marks unsupported source facts as `NOT_REPORTED` rather than guessed values. | `NOT_AUDITED` | — | — |
| `GATE-R-012` | 6252 | The submission-time novelty-survival literature gate in Part I §10.D.9A was executed within 14 calendar days of submission and both prior-art tables/citations were updated through that search date. | `NOT_AUDITED` | — | — |
| `GATE-R-013` | 6253 | The historical moment-estimator sensitivity is reported as estimator-family robustness only and is not used to replace the q95 confirmatory endpoint. | `NOT_AUDITED` | — | — |
| `GATE-R-014` | 6254 | Null, reversed, infeasible, and unfavorable seed-level evidence is retained in supplementary evidence where required. | `NOT_AUDITED` | — | — |
| `GATE-R-015` | 6255 | Every headline table or figure has a traceable experiment and metric definition. | `NOT_AUDITED` | — | — |
| `GATE-R-016` | 6256 | The mandatory causal intervention map preserves the fixed-score boundary and contains no outcome-to-calibration/training feedback arrow. | `NOT_AUDITED` | — | — |
| `GATE-R-017` | 6257 | The ten confirmatory paired seed deltas are shown individually with the arithmetic mean and locked BCa interval. | `NOT_AUDITED` | — | — |
| `GATE-R-018` | 6258 | Both required equity–utility Pareto views and their target-attainment table are present when attack-sensitive N-BaIoT metrics are available. | `NOT_AUDITED` | — | — |
| `GATE-R-019` | 6259 | The FedProx mechanism figure reports terminal-50 drift rather than inferring mechanism activation from downstream performance alone. | `NOT_AUDITED` | — | — |
| `GATE-R-020` | 6260 | The manuscript explicitly qualifies the confirmatory regime as persistent identifiable IoT clients with full training participation and does not generalize to intermittent/unseen cross-device clients. | `NOT_AUDITED` | — | — |
| `GATE-R-021` | 6261 | The headline confirmatory result includes the mandatory equity–utility/client-impact bundle rather than reporting `CV(FPR)` in isolation. | `NOT_AUDITED` | — | — |
| `GATE-R-022` | 6262 | `FEDAVG_LOCAL_FINE_TUNING` is identified as a bounded simple personalization stress test, not a new PFL contribution and not a replacement for Ditto. | `NOT_AUDITED` | — | — |
| `GATE-R-023` | 6263 | The complete reproducibility-release bundle in §20A is generated in the appropriate `PUBLIC`, `BLINDED_ARCHIVE`, or `WITHHELD_LICENSE_RESTRICTED` state and its SHA-256 manifest validates. | `NOT_AUDITED` | — | — |

## 13. Reproducibility-release bundle matrix

### 13.1 Required logical payload

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

### 13.2 Release artifact requirements

#### `ROADMAP_LOCK.md`
- [ ] `6292` — exact scientific-roadmap snapshot used for the reported campaign;
- [ ] `6293` — SHA-256 digest of that snapshot;
- [ ] `6294` — code commit/release identifier;
- [ ] `6295` — submission-time literature-search date from Part I §10.D.9A.

#### `MANIFEST_SHA256.csv`

#### `SEEDS.csv`
- [ ] `6318` — the exact ten confirmatory training seeds;
- [ ] `6319` — every declared nested/randomness purpose label;
- [ ] `6320` — deterministic derivation inputs sufficient to reconstruct calibration subsamples, cluster repeats, KLL runs, fine-tuning batch order, and any other seeded nested operation;
- [ ] `6321` — no seed may be regenerated from an undocumented process during reproduction.
- [ ] `6327` — official acquisition instructions/identifiers;
- [ ] `6328` — raw-file checksums where redistribution-independent checksums are lawful to publish;
- [ ] `6329` — canonical processed-artifact checksums;
- [ ] `6330` — ordered row-identity-set hashes for train/calibration/evaluation artifacts;
- [ ] `6331` — client membership counts and the deterministic population-construction manifest.
- [ ] `6339` — fitted preprocessing-state artifacts and protocol identities;
- [ ] `6340` — terminal round-200 model artifacts for each training condition/seed, including personalized client states where releasable;
- [ ] `6341` — canonical calibration/evaluation score artifacts or, where source-data licensing prevents score redistribution, their exact ordered-row identities, hashes, generation command, and model/preprocessing hashes;
- [ ] `6342` — every threshold output and its contributor/support metadata.
- [ ] `6348` — tidy seed×client×policy metric tables;
- [ ] `6349` — all ten confirmatory paired deltas;
- [ ] `6350` — BCa bootstrap configuration and deterministic bootstrap seed material;
- [ ] `6351` — Wilcoxon/sign-test/effect-size/multiplicity inputs and outputs;
- [ ] `6352` — the source-data table behind every manuscript figure and table;
- [ ] `6353` — typed unavailability states rather than silently dropped cells.

### 13.3 Final publication-readiness gate

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

## 14. Lossless atomic requirement register

**Extracted list/procedure item count:** `1195` across Parts I–IV. This register intentionally overlaps the curated matrices above. Its purpose is omission detection: every source list/procedure item has an ID, line pointer, and audit slot.

| Requirement ID | Part | Source line | Source section | Atomic requirement | Disposition | Audit |
|---|---|---:|---|---|---|---|
| `DATASET-001` | PREAMBLE | 9 | Purpose and structure | **Scientific programme** — the causal question, evidence hierarchy, methods, populations, scope, and claim boundaries. | `NOT_AUDITED` | — |
| `PREPROCESS-001` | PREAMBLE | 10 | Purpose and structure | **Exact protocol** — the numerical, mathematical, preprocessing, training, thresholding, and dataset rules that determine scientific behavior. | `NOT_AUDITED` | — |
| `GLOBAL-001` | PREAMBLE | 11 | Purpose and structure | **Experiment programme and evaluation** — what is executed, what changes, what is measured, and how inference is performed. | `NOT_AUDITED` | — |
| `PROVENANCE-001` | PREAMBLE | 12 | Purpose and structure | **Development and audit contract** — the provenance, identity, completeness, and publication gates used to verify that the implementation actually realizes the scientific programme. | `NOT_AUDITED` | — |
| `GLOBAL-002` | I | 95 | 2.1 Unit of causal comparison | the same selected autoencoder state; | `NOT_AUDITED` | — |
| `PREPROCESS-002` | I | 96 | 2.1 Unit of causal comparison | the same preprocessing state; | `NOT_AUDITED` | — |
| `GLOBAL-003` | I | 97 | 2.1 Unit of causal comparison | the same client identities; | `NOT_AUDITED` | — |
| `GLOBAL-004` | I | 98 | 2.1 Unit of causal comparison | the same predefined data partitions; | `NOT_AUDITED` | — |
| `CALIBRATION-001` | I | 99 | 2.1 Unit of causal comparison | the same benign calibration records; | `NOT_AUDITED` | — |
| `GLOBAL-005` | I | 100 | 2.1 Unit of causal comparison | the same held-out test scores; | `NOT_AUDITED` | — |
| `GLOBAL-006` | I | 101 | 2.1 Unit of causal comparison | the same held-out test labels; | `NOT_AUDITED` | — |
| `CALIBRATION-002` | I | 102 | 2.1 Unit of causal comparison | the same eligibility rule; | `NOT_AUDITED` | — |
| `THRESHOLD-001` | I | 103 | 2.1 Unit of causal comparison | the same quantile target unless a declared quantile-sensitivity experiment changes it; | `NOT_AUDITED` | — |
| `METRIC-001` | I | 104 | 2.1 Unit of causal comparison | the same metric implementation. | `NOT_AUDITED` | — |
| `GLOBAL-007` | I | 112 | 2.2 Fixed elements | model family; | `NOT_AUDITED` | — |
| `DATASET-002` | I | 113 | 2.2 Fixed elements | autoencoder architecture, apart from the input dimension required by the dataset feature schema; | `NOT_AUDITED` | — |
| `TRAIN-001` | I | 114 | 2.2 Fixed elements | FedAvg as the training algorithm; | `NOT_AUDITED` | — |
| `GLOBAL-008` | I | 115 | 2.2 Fixed elements | one local epoch per round; | `NOT_AUDITED` | — |
| `GLOBAL-009` | I | 116 | 2.2 Fixed elements | full client participation; | `NOT_AUDITED` | — |
| `TRAIN-002` | I | 117 | 2.2 Fixed elements | optimizer and training hyperparameters; | `NOT_AUDITED` | — |
| `PREPROCESS-003` | I | 118 | 2.2 Fixed elements | preprocessing and normalization semantics; | `NOT_AUDITED` | — |
| `GLOBAL-010` | I | 119 | 2.2 Fixed elements | split semantics; | `NOT_AUDITED` | — |
| `GLOBAL-011` | I | 120 | 2.2 Fixed elements | round budget and terminal scientific-model rule; | `NOT_AUDITED` | — |
| `GLOBAL-012` | I | 121 | 2.2 Fixed elements | seed cohort; | `NOT_AUDITED` | — |
| `SCORE-001` | I | 122 | 2.2 Fixed elements | scoring procedure; | `NOT_AUDITED` | — |
| `CALIBRATION-003` | I | 123 | 2.2 Fixed elements | client eligibility; | `NOT_AUDITED` | — |
| `DATASET-003` | I | 124 | 2.2 Fixed elements | test population; | `NOT_AUDITED` | — |
| `METRIC-002` | I | 125 | 2.2 Fixed elements | metric definitions. | `NOT_AUDITED` | — |
| `PREPROCESS-004` | I | 135 | 2.2.1 Preprocessing and normalization lock | transformer family: zero-mean unit-variance standardization (`StandardScaler`, `with_mean=True`, `with_std=True`); | `NOT_AUDITED` | — |
| `PREPROCESS-005` | I | 136 | 2.2.1 Preprocessing and normalization lock | fit scope: **client-local**, fit only on each client’s benign training partition; | `NOT_AUDITED` | — |
| `PREPROCESS-006` | I | 137 | 2.2.1 Preprocessing and normalization lock | fit partition: train only; calibration, evaluation, and future recalibration rows are transformed only; | `NOT_AUDITED` | — |
| `PREPROCESS-007` | I | 138 | 2.2.1 Preprocessing and normalization lock | constant-feature rule: zero training scale uses unit scale and yields a zero-centered column (sklearn standard-scaler behaviour); | `NOT_AUDITED` | — |
| `PREPROCESS-008` | I | 139 | 2.2.1 Preprocessing and normalization lock | out-of-range transformed values after fit: retained unclipped; | `NOT_AUDITED` | — |
| `PREPROCESS-009` | I | 140 | 2.2.1 Preprocessing and normalization lock | fitted-state persistence: skops with trusted estimator classes only; | `NOT_AUDITED` | — |
| `PREPROCESS-010` | I | 141 | 2.2.1 Preprocessing and normalization lock | transform serialization equivalence absolute tolerance: `1e-12` (engineering research amendment reusing the fixed-score absolute-tolerance magnitude; skops defines no scientific tolerance). | `NOT_AUDITED` | — |
| `PREPROCESS-011` | I | 147 | 2.2.1 Preprocessing and normalization lock | transformer family: feature-wise min–max (`MinMaxScaler`); | `NOT_AUDITED` | — |
| `PREPROCESS-012` | I | 148 | 2.2.1 Preprocessing and normalization lock | fit scope: pooled benign training rows of the federated population; | `NOT_AUDITED` | — |
| `PREPROCESS-013` | I | 149 | 2.2.1 Preprocessing and normalization lock | same train-only, skops, unclipped, and tolerance rules. | `NOT_AUDITED` | — |
| `PREPROCESS-014` | I | 155 | 2.2.1 Preprocessing and normalization lock | independent of federated fitted states (never reuse federated client-local or pooled federated states); | `NOT_AUDITED` | — |
| `PREPROCESS-015` | I | 156 | 2.2.1 Preprocessing and normalization lock | transformer family: min–max (`MinMaxScaler`); | `NOT_AUDITED` | — |
| `PREPROCESS-016` | I | 157 | 2.2.1 Preprocessing and normalization lock | fit scope: pooled benign training rows of the centralized reference population; | `NOT_AUDITED` | — |
| `PREPROCESS-017` | I | 158 | 2.2.1 Preprocessing and normalization lock | fit partition: train only; | `NOT_AUDITED` | — |
| `PREPROCESS-018` | I | 159 | 2.2.1 Preprocessing and normalization lock | constant-feature rule: zero training range maps to zero; | `NOT_AUDITED` | — |
| `PREPROCESS-019` | I | 160 | 2.2.1 Preprocessing and normalization lock | unclipped, skops, and tolerance rules as above. | `NOT_AUDITED` | — |
| `PREPROCESS-020` | I | 164 | 2.2.1 Preprocessing and normalization lock | no imputation, zero-fill, clipping, capping, infinity replacement, or label inference in the fitted pipeline; | `NOT_AUDITED` | — |
| `PREPROCESS-021` | I | 165 | 2.2.1 Preprocessing and normalization lock | N-BaIoT non-finite declared features fail validation rather than being filled; | `NOT_AUDITED` | — |
| `PREPROCESS-022` | I | 166 | 2.2.1 Preprocessing and normalization lock | CICIoT2023 model-input eligibility remains the outcome-blind finite-feature and recognized-label gate (canonical rows stay lossless; ineligible rows never enter client construction, split, fit, calibration, or evaluation); | `NOT_AUDITED` | — |
| `PREPROCESS-023` | I | 167 | 2.2.1 Preprocessing and normalization lock | Edge-IIoTset model-input rows with non-finite retained numeric fields are excluded from model input with explicit provenance, never filled; | `NOT_AUDITED` | — |
| `PREPROCESS-024` | I | 168 | 2.2.1 Preprocessing and normalization lock | attack labels never influence preprocessing fit; | `NOT_AUDITED` | — |
| `PREPROCESS-025` | I | 169 | 2.2.1 Preprocessing and normalization lock | empty-train or missing-support recovery by fabricating zero-filled rows is forbidden. | `NOT_AUDITED` | — |
| `CALIBRATION-004` | I | 206 | 2.2.3 Empirical-quantile definition lock | `LOCAL_CONFORMAL_THRESHOLD` uses its finite-sample conformal order-statistic rule rather than type-7 interpolation; | `NOT_AUDITED` | — |
| `THRESHOLD-002` | I | 207 | 2.2.3 Empirical-quantile definition lock | `FEDERATED_KLL_SHARED_THRESHOLD` is an approximate rank sketch and therefore returns an approximate retained-value quantile under the sketch's inclusive-rank semantics. Its error is measured against the exact type-7 pooled oracle rather than silently treated as exact. | `NOT_AUDITED` | — |
| `THRESHOLD-003` | I | 234 | 2.4 Prohibited causal contamination | retraining the autoencoder separately for SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, or CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `TRAIN-003` | I | 235 | 2.4 Prohibited causal contamination | using a non-terminal detector state for a scientific result; | `NOT_AUDITED` | — |
| `THRESHOLD-004` | I | 236 | 2.4 Prohibited causal contamination | selecting thresholds from attack-labelled data; | `NOT_AUDITED` | — |
| `SCORE-002` | I | 237 | 2.4 Prohibited causal contamination | choosing a policy parameter using held-out test F1, TPR, AUROC, balanced accuracy, or `CV(FPR)`; | `NOT_AUDITED` | — |
| `BOUNDARY-001` | I | 238 | 2.4 Prohibited causal contamination | changing eligible clients between compared policies; | `NOT_AUDITED` | — |
| `BOUNDARY-002` | I | 239 | 2.4 Prohibited causal contamination | removing clients that weaken the expected ordering; | `NOT_AUDITED` | — |
| `THRESHOLD-005` | I | 240 | 2.4 Prohibited causal contamination | treating FedProx or model personalization as another threshold-scope condition; | `NOT_AUDITED` | — |
| `CALIBRATION-005` | I | 241 | 2.4 Prohibited causal contamination | replacing a failed shared-versus-local result with a more favorable CLUSTER_THRESHOLD, shrinkage, or conformal result. | `NOT_AUDITED` | — |
| `CALIBRATION-006` | I | 253 | 3.1 Benign-only calibration | threshold values; | `NOT_AUDITED` | — |
| `CALIBRATION-007` | I | 254 | 3.1 Benign-only calibration | quantile selection; | `NOT_AUDITED` | — |
| `CALIBRATION-008` | I | 255 | 3.1 Benign-only calibration | client eligibility; | `NOT_AUDITED` | — |
| `CALIBRATION-009` | I | 256 | 3.1 Benign-only calibration | terminal-detector identity; | `NOT_AUDITED` | — |
| `CALIBRATION-010` | I | 257 | 3.1 Benign-only calibration | comparator tuning; | `NOT_AUDITED` | — |
| `CALIBRATION-011` | I | 258 | 3.1 Benign-only calibration | shrinkage strength; | `NOT_AUDITED` | — |
| `CALIBRATION-012` | I | 259 | 3.1 Benign-only calibration | conformal significance level; | `NOT_AUDITED` | — |
| `CALIBRATION-013` | I | 260 | 3.1 Benign-only calibration | cluster count; | `NOT_AUDITED` | — |
| `CALIBRATION-014` | I | 261 | 3.1 Benign-only calibration | cluster-feature selection; | `NOT_AUDITED` | — |
| `CALIBRATION-015` | I | 262 | 3.1 Benign-only calibration | external-dataset client construction. | `NOT_AUDITED` | — |
| `CALIBRATION-016` | I | 272 | 3.2 Separation of calibration and evaluation | historical calibration must precede future recalibration; | `NOT_AUDITED` | — |
| `CALIBRATION-017` | I | 273 | 3.2 Separation of calibration and evaluation | future recalibration must precede future evaluation; | `NOT_AUDITED` | — |
| `CALIBRATION-018` | I | 274 | 3.2 Separation of calibration and evaluation | future evaluation cannot influence any earlier stage; | `NOT_AUDITED` | — |
| `CALIBRATION-019` | I | 275 | 3.2 Separation of calibration and evaluation | data ordering or generated pseudo-time cannot replace real chronology. | `NOT_AUDITED` | — |
| `CALIBRATION-020` | I | 283 | 3.2A Honest-calibration participant and message-integrity assumption | benign calibration row identities and labels; | `NOT_AUDITED` | — |
| `PREPROCESS-026` | I | 284 | 3.2A Honest-calibration participant and message-integrity assumption | reconstruction scores computed by the locked detector/preprocessing state; | `NOT_AUDITED` | — |
| `CALIBRATION-021` | I | 285 | 3.2A Honest-calibration participant and message-integrity assumption | local empirical thresholds and calibration support counts; | `NOT_AUDITED` | — |
| `CALIBRATION-022` | I | 286 | 3.2A Honest-calibration participant and message-integrity assumption | family/cluster threshold inputs; | `NOT_AUDITED` | — |
| `CALIBRATION-023` | I | 287 | 3.2A Honest-calibration participant and message-integrity assumption | CLUSTER_THRESHOLD fingerprints `[mean, sample std, skewness, p95]`; | `NOT_AUDITED` | — |
| `CALIBRATION-024` | I | 288 | 3.2A Honest-calibration participant and message-integrity assumption | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` summary statistics; | `NOT_AUDITED` | — |
| `CALIBRATION-025` | I | 289 | 3.2A Honest-calibration participant and message-integrity assumption | `FEDERATED_KLL_SHARED_THRESHOLD` sketches and declared sketch parameters; | `NOT_AUDITED` | — |
| `CALIBRATION-026` | I | 290 | 3.2A Honest-calibration participant and message-integrity assumption | conformal score/order-statistic inputs; | `NOT_AUDITED` | — |
| `CALIBRATION-027` | I | 291 | 3.2A Honest-calibration participant and message-integrity assumption | any serialized threshold-stage message used for communication accounting. | `NOT_AUDITED` | — |
| `TRAIN-004` | I | 339 | 3.3A Federation regime, client persistence, and deployment identity | the benign training partition; | `NOT_AUDITED` | — |
| `CALIBRATION-028` | I | 340 | 3.3A Federation regime, client persistence, and deployment identity | the benign calibration source pool; | `NOT_AUDITED` | — |
| `GLOBAL-013` | I | 341 | 3.3A Federation regime, client persistence, and deployment identity | the held-out evaluation partition; | `NOT_AUDITED` | — |
| `PREPROCESS-027` | I | 342 | 3.3A Federation regime, client persistence, and deployment identity | fitted client-local preprocessing state; | `NOT_AUDITED` | — |
| `THRESHOLD-006` | I | 343 | 3.3A Federation regime, client persistence, and deployment identity | client-local threshold state; | `NOT_AUDITED` | — |
| `TRAIN-005` | I | 344 | 3.3A Federation regime, client persistence, and deployment identity | Ditto personalized state; | `NOT_AUDITED` | — |
| `GLOBAL-014` | I | 345 | 3.3A Federation regime, client persistence, and deployment identity | post-FedAvg locally fine-tuned state; | `NOT_AUDITED` | — |
| `METRIC-003` | I | 346 | 3.3A Federation regime, client persistence, and deployment identity | all client-disaggregated metrics. | `NOT_AUDITED` | — |
| `GLOBAL-015` | I | 364 | 3.4 Meaning of “fairness” | demographic fairness; | `NOT_AUDITED` | — |
| `GLOBAL-016` | I | 365 | 3.4 Meaning of “fairness” | protected-attribute fairness; | `NOT_AUDITED` | — |
| `GLOBAL-017` | I | 366 | 3.4 Meaning of “fairness” | individual human fairness; | `NOT_AUDITED` | — |
| `GLOBAL-018` | I | 367 | 3.4 Meaning of “fairness” | equalized odds over human groups; | `NOT_AUDITED` | — |
| `GLOBAL-019` | I | 368 | 3.4 Meaning of “fairness” | social or legal nondiscrimination. | `NOT_AUDITED` | — |
| `METRIC-004` | I | 372 | 3.4 Meaning of “fairness” | operational FPR equity; | `NOT_AUDITED` | — |
| `GLOBAL-020` | I | 373 | 3.4 Meaning of “fairness” | false-alarm equity; | `NOT_AUDITED` | — |
| `METRIC-005` | I | 374 | 3.4 Meaning of “fairness” | cross-client FPR dispersion; | `NOT_AUDITED` | — |
| `GLOBAL-021` | I | 375 | 3.4 Meaning of “fairness” | service-level operating-point equity; | `NOT_AUDITED` | — |
| `GLOBAL-022` | I | 376 | 3.4 Meaning of “fairness” | distribution of false-alarm burden. | `NOT_AUDITED` | — |
| `SCORE-003` | I | 396 | 3.6 Model-quality controls | AUROC; | `NOT_AUDITED` | — |
| `REPORT-001` | I | 397 | 3.6 Model-quality controls | average precision (`AP`, reported as the PR-curve summary / AUPRC control); | `NOT_AUDITED` | — |
| `METRIC-006` | I | 398 | 3.6 Model-quality controls | Macro-F1; | `NOT_AUDITED` | — |
| `METRIC-007` | I | 399 | 3.6 Model-quality controls | balanced accuracy; | `NOT_AUDITED` | — |
| `METRIC-008` | I | 400 | 3.6 Model-quality controls | TPR or recall; | `NOT_AUDITED` | — |
| `METRIC-009` | I | 401 | 3.6 Model-quality controls | P10 Macro-F1; | `NOT_AUDITED` | — |
| `METRIC-010` | I | 402 | 3.6 Model-quality controls | worst-client balanced accuracy. | `NOT_AUDITED` | — |
| `SCORE-004` | I | 408 | 3.6 Model-quality controls | unchanged AUROC does not invalidate a threshold-scope effect; | `NOT_AUDITED` | — |
| `SCORE-005` | I | 409 | 3.6 Model-quality controls | improved AUROC does not establish a threshold-scope effect; | `NOT_AUDITED` | — |
| `THRESHOLD-007` | I | 410 | 3.6 Model-quality controls | lower P10 Macro-F1 under LOCAL_THRESHOLD is an important negative trade-off and must remain visible; | `NOT_AUDITED` | — |
| `GLOBAL-023` | I | 411 | 3.6 Model-quality controls | global average performance cannot hide severe client-level false-alarm disparity. | `NOT_AUDITED` | — |
| `TRAIN-006` | I | 423 | 4.1 Centralized reference: CENTRALIZED_REFERENCE | a centralized autoencoder trained on pooled benign training data; | `NOT_AUDITED` | — |
| `CALIBRATION-029` | I | 424 | 4.1 Centralized reference: CENTRALIZED_REFERENCE | a pooled benign calibration threshold; | `NOT_AUDITED` | — |
| `TRAIN-007` | I | 425 | 4.1 Centralized reference: CENTRALIZED_REFERENCE | separate centralized training and evaluation. | `NOT_AUDITED` | — |
| `THRESHOLD-008` | I | 471 | 4.4 Family threshold: FAMILY_THRESHOLD | a defensible family taxonomy exists; | `NOT_AUDITED` | — |
| `THRESHOLD-009` | I | 472 | 4.4 Family threshold: FAMILY_THRESHOLD | the taxonomy is defined independently of test outcomes; | `NOT_AUDITED` | — |
| `THRESHOLD-010` | I | 473 | 4.4 Family threshold: FAMILY_THRESHOLD | family membership is stable and auditable; | `NOT_AUDITED` | — |
| `THRESHOLD-011` | I | 474 | 4.4 Family threshold: FAMILY_THRESHOLD | the taxonomy represents device identity rather than attack labels. | `NOT_AUDITED` | — |
| `THRESHOLD-012` | I | 505 | 4.5 Cluster threshold: CLUSTER_THRESHOLD | model clustering; | `NOT_AUDITED` | — |
| `THRESHOLD-013` | I | 506 | 4.5 Cluster threshold: CLUSTER_THRESHOLD | clustered federated training; | `NOT_AUDITED` | — |
| `THRESHOLD-014` | I | 507 | 4.5 Cluster threshold: CLUSTER_THRESHOLD | a privacy mechanism; | `NOT_AUDITED` | — |
| `THRESHOLD-015` | I | 508 | 4.5 Cluster threshold: CLUSTER_THRESHOLD | a new clustering algorithm; | `NOT_AUDITED` | — |
| `THRESHOLD-016` | I | 509 | 4.5 Cluster threshold: CLUSTER_THRESHOLD | a confirmatory endpoint. | `NOT_AUDITED` | — |
| `CALIBRATION-030` | I | 614 | 5.2 Local–global shrinkage | full-calibration scope-mismatch proxy: | `NOT_AUDITED` | — |
| `CALIBRATION-031` | I | 621 | 5.2 Local–global shrinkage | finite-calibration local estimation variance across the `R=10` nested subsamples, defined in Part III §8.4; | `NOT_AUDITED` | — |
| `CALIBRATION-032` | I | 622 | 5.2 Local–global shrinkage | `Bias_tau` and `RMSE_tau` versus each client's full-calibration local threshold, defined in Part II §8.1; | `NOT_AUDITED` | — |
| `CALIBRATION-033` | I | 623 | 5.2 Local–global shrinkage | held-out target-attainment error and calibration-to-held-out generalization gap, defined in Part III §§4.7–4.8. | `NOT_AUDITED` | — |
| `THRESHOLD-017` | I | 639 | 5.2 Local–global shrinkage | `lambda = 0` gives the shared endpoint; | `NOT_AUDITED` | — |
| `THRESHOLD-018` | I | 640 | 5.2 Local–global shrinkage | `lambda = 1` gives the local endpoint; | `NOT_AUDITED` | — |
| `THRESHOLD-019` | I | 641 | 5.2 Local–global shrinkage | intermediate values partially pool client information. | `NOT_AUDITED` | — |
| `CALIBRATION-034` | I | 687 | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | arbitrary client-conditional coverage; | `NOT_AUDITED` | — |
| `CALIBRATION-035` | I | 688 | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | validity under unrestricted non-exchangeability; | `NOT_AUDITED` | — |
| `CALIBRATION-036` | I | 689 | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | robustness to Byzantine calibration (explicitly outside scope in light of Rob-FCP/PRISM-FCP[^robfcp2024][^prismfcp2026]); | `NOT_AUDITED` | — |
| `CALIBRATION-037` | I | 690 | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | a full conformal DATP contribution; | `NOT_AUDITED` | — |
| `CALIBRATION-038` | I | 691 | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | a replacement confirmatory endpoint. | `NOT_AUDITED` | — |
| `CALIBRATION-039` | I | 707 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | use benign calibration information only; | `NOT_AUDITED` | — |
| `THRESHOLD-020` | I | 708 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | use the full pooled variance decomposition, including between-client mean-shift; | `NOT_AUDITED` | — |
| `THRESHOLD-021` | I | 709 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | target the same benign exceedance as the DATP quantile; | `NOT_AUDITED` | — |
| `THRESHOLD-022` | I | 710 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | lock its protocol before result inspection; | `NOT_AUDITED` | — |
| `THRESHOLD-023` | I | 711 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | disclose every statistic communicated by a client; | `NOT_AUDITED` | — |
| `THRESHOLD-024` | I | 712 | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | remain a shared-threshold comparator. | `NOT_AUDITED` | — |
| `THRESHOLD-025` | I | 766 | 6.2 Relationship to Laridi et al. | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is not a faithful Laridi reproduction; | `NOT_AUDITED` | — |
| `GLOBAL-024` | I | 767 | 6.2 Relationship to Laridi et al. | it must not be called `LARIDI_ANOMALY_INFORMED_REFERENCE`; | `NOT_AUDITED` | — |
| `REPORT-002` | I | 768 | 6.2 Relationship to Laridi et al. | its results cannot be used to claim reproduction of Laridi et al.; | `NOT_AUDITED` | — |
| `CALIBRATION-040` | I | 769 | 6.2 Relationship to Laridi et al. | the difference in calibration contracts must be disclosed in related work and limitations. | `NOT_AUDITED` | — |
| `TRAIN-008` | I | 886 | 7.2 Ditto | a distinct global model; | `NOT_AUDITED` | — |
| `TRAIN-009` | I | 887 | 7.2 Ditto | persistent client-personalized states; | `NOT_AUDITED` | — |
| `TRAIN-010` | I | 888 | 7.2 Ditto | the correct proximal personalized objective; | `NOT_AUDITED` | — |
| `TRAIN-011` | I | 889 | 7.2 Ditto | no aggregation of personalized states as if they were global; | `NOT_AUDITED` | — |
| `TRAIN-012` | I | 890 | 7.2 Ditto | separate evaluation. | `NOT_AUDITED` | — |
| `TRAIN-013` | I | 937 | 7.2A Post-FedAvg client-local fine-tuning stress test | instantiate a **fresh optimizer** for each `(training_seed, client_id)` fine-tuning run; | `NOT_AUDITED` | — |
| `TRAIN-014` | I | 938 | 7.2A Post-FedAvg client-local fine-tuning stress test | copy model weights only; never copy Adam/SGD momentum, moments, scheduler counters, gradient scaler state, or any other optimizer state from federated training; | `NOT_AUDITED` | — |
| `TRAIN-015` | I | 939 | 7.2A Post-FedAvg client-local fine-tuning stress test | use the FedAvg reference learning rate, batch size, optimizer betas/momentum, epsilon, weight decay, loss, gradient handling, and benign-train data-loader semantics unchanged; | `NOT_AUDITED` | — |
| `TRAIN-016` | I | 940 | 7.2A Post-FedAvg client-local fine-tuning stress test | if the FedAvg reference uses a constant learning rate, retain that constant rate for all ten local epochs; | `NOT_AUDITED` | — |
| `TRAIN-017` | I | 941 | 7.2A Post-FedAvg client-local fine-tuning stress test | if the FedAvg reference uses a round-indexed learning-rate schedule, use the **round-200 reference learning rate** and hold it constant throughout the ten fine-tuning epochs; do not restart or extrapolate the federated schedule; | `NOT_AUDITED` | — |
| `TRAIN-018` | I | 942 | 7.2A Post-FedAvg client-local fine-tuning stress test | no new fine-tuning learning-rate grid, epoch grid, regularization grid, validation sweep, or outcome-selected checkpoint is permitted. | `NOT_AUDITED` | — |
| `THRESHOLD-026` | I | 1124 | 7.4 Separation from the core ladder | SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, and CLUSTER_THRESHOLD may be recomputed from that model’s scores; | `NOT_AUDITED` | — |
| `THRESHOLD-027` | I | 1125 | 7.4 Separation from the core ladder | the model’s threshold-scope difference may be compared with the FedAvg difference; | `NOT_AUDITED` | — |
| `THRESHOLD-028` | I | 1126 | 7.4 Separation from the core ladder | the common score-alignment/threshold-absorption diagnostics in §7.2B are mandatory whenever their inputs are available; | `NOT_AUDITED` | — |
| `CALIBRATION-041` | I | 1127 | 7.4 Separation from the core ladder | the result may support retention, partial absorption, or full absorption; | `NOT_AUDITED` | — |
| `GLOBAL-025` | I | 1128 | 7.4 Separation from the core ladder | the result cannot alter the identity of the FedAvg core ladder. | `NOT_AUDITED` | — |
| `DATASET-004` | I | 1138 | 8.1 Sole confirmatory evidence | N-BaIoT physical-device population; | `NOT_AUDITED` | — |
| `GLOBAL-026` | I | 1139 | 8.1 Sole confirmatory evidence | shared versus local; | `NOT_AUDITED` | — |
| `METRIC-011` | I | 1140 | 8.1 Sole confirmatory evidence | `CV(FPR)`; | `NOT_AUDITED` | — |
| `GLOBAL-027` | I | 1141 | 8.1 Sole confirmatory evidence | ten paired seeds; | `NOT_AUDITED` | — |
| `STAT-001` | I | 1142 | 8.1 Sole confirmatory evidence | locked BCa decision rule. | `NOT_AUDITED` | — |
| `CALIBRATION-042` | I | 1150 | 8.2 Supporting evidence families | supportive robustness; | `NOT_AUDITED` | — |
| `CALIBRATION-043` | I | 1151 | 8.2 Supporting evidence families | mechanism analysis; | `NOT_AUDITED` | — |
| `CALIBRATION-044` | I | 1152 | 8.2 Supporting evidence families | threshold variant; | `NOT_AUDITED` | — |
| `CALIBRATION-045` | I | 1153 | 8.2 Supporting evidence families | shared-estimator control; | `NOT_AUDITED` | — |
| `CALIBRATION-046` | I | 1154 | 8.2 Supporting evidence families | calibration-support/heterogeneity interaction; | `NOT_AUDITED` | — |
| `CALIBRATION-047` | I | 1155 | 8.2 Supporting evidence families | calibration cold-start boundary; | `NOT_AUDITED` | — |
| `PREPROCESS-028` | I | 1156 | 8.2 Supporting evidence families | preprocessing sensitivity; | `NOT_AUDITED` | — |
| `CALIBRATION-048` | I | 1157 | 8.2 Supporting evidence families | external validation; | `NOT_AUDITED` | — |
| `CALIBRATION-049` | I | 1158 | 8.2 Supporting evidence families | aggregation-side stress test; | `NOT_AUDITED` | — |
| `CALIBRATION-050` | I | 1159 | 8.2 Supporting evidence families | simple post-FedAvg fine-tuning stress test; | `NOT_AUDITED` | — |
| `CALIBRATION-051` | I | 1160 | 8.2 Supporting evidence families | model-personalization stress test; | `NOT_AUDITED` | — |
| `CALIBRATION-052` | I | 1161 | 8.2 Supporting evidence families | applicability boundary; | `NOT_AUDITED` | — |
| `CALIBRATION-053` | I | 1162 | 8.2 Supporting evidence families | temporal boundary; | `NOT_AUDITED` | — |
| `CALIBRATION-054` | I | 1163 | 8.2 Supporting evidence families | exploratory supplement; | `NOT_AUDITED` | — |
| `DATASET-005` | I | 1189 | 9.1 N-BaIoT physical-device anchor | the nine physical devices are the natural clients; | `NOT_AUDITED` | — |
| `DATASET-006` | I | 1190 | 9.1 N-BaIoT physical-device anchor | this is the only confirmatory client population; | `NOT_AUDITED` | — |
| `CALIBRATION-055` | I | 1191 | 9.1 N-BaIoT physical-device anchor | the device-family taxonomy may support FAMILY_THRESHOLD; | `NOT_AUDITED` | — |
| `DATASET-007` | I | 1192 | 9.1 N-BaIoT physical-device anchor | all nine clients remain visible in mechanism reporting; | `NOT_AUDITED` | — |
| `DATASET-008` | I | 1193 | 9.1 N-BaIoT physical-device anchor | the small client count is an explicit limitation. | `NOT_AUDITED` | — |
| `DATASET-009` | I | 1203 | 9.2 CICIoT2023 available-data boundary | available-data pseudo-clients may be used only as a dataset-specific applicability boundary; | `NOT_AUDITED` | — |
| `DATASET-010` | I | 1204 | 9.2 CICIoT2023 available-data boundary | a null result cannot be generalized to the original 105-device topology; | `NOT_AUDITED` | — |
| `DATASET-011` | I | 1205 | 9.2 CICIoT2023 available-data boundary | source-paper device counts cannot be substituted for missing artifact metadata; | `NOT_AUDITED` | — |
| `DATASET-012` | I | 1206 | 9.2 CICIoT2023 available-data boundary | device-aware wording is prohibited for this population. | `NOT_AUDITED` | — |
| `DATASET-013` | I | 1234 | 9.4 Edge-IIoTset external validation | per-client TPR is unavailable; | `NOT_AUDITED` | — |
| `DATASET-014` | I | 1235 | 9.4 Edge-IIoTset external validation | per-client Macro-F1 is unavailable; | `NOT_AUDITED` | — |
| `DATASET-015` | I | 1236 | 9.4 Edge-IIoTset external validation | per-client balanced accuracy is unavailable; | `NOT_AUDITED` | — |
| `SCORE-006` | I | 1237 | 9.4 Edge-IIoTset external validation | per-client AUROC is unavailable; | `NOT_AUDITED` | — |
| `DATASET-016` | I | 1238 | 9.4 Edge-IIoTset external validation | attack-sensitive cross-client equity is unavailable. | `NOT_AUDITED` | — |
| `DATASET-017` | I | 1250 | 9.5 Temporal external population | continuous adaptation; | `NOT_AUDITED` | — |
| `DATASET-018` | I | 1251 | 9.5 Temporal external population | online learning; | `NOT_AUDITED` | — |
| `DATASET-019` | I | 1252 | 9.5 Temporal external population | streaming drift detection; | `NOT_AUDITED` | — |
| `CALIBRATION-056` | I | 1253 | 9.5 Temporal external population | drift-triggered recalibration; | `NOT_AUDITED` | — |
| `DATASET-020` | I | 1254 | 9.5 Temporal external population | concept-drift resolution; | `NOT_AUDITED` | — |
| `DATASET-021` | I | 1255 | 9.5 Temporal external population | production stability over repeated cycles. | `NOT_AUDITED` | — |
| `TRAIN-019` | I | 1318 | 10.A.3 Training-side robustness | heterogeneity-aware federated optimization through FedProx; | `NOT_AUDITED` | — |
| `TRAIN-020` | I | 1319 | 10.A.3 Training-side robustness | simple post-FedAvg client-local fine-tuning through `FEDAVG_LOCAL_FINE_TUNING`; | `NOT_AUDITED` | — |
| `TRAIN-021` | I | 1320 | 10.A.3 Training-side robustness | persistent proximal client model personalization through Ditto. | `NOT_AUDITED` | — |
| `THRESHOLD-029` | I | 1328 | 10.A.4 Threshold-estimation depth | quantile-level sensitivity; | `NOT_AUDITED` | — |
| `SCORE-007` | I | 1329 | 10.A.4 Threshold-estimation depth | one fixed-score historical `mean + sample-standard-deviation` estimator-by-scope sensitivity; | `NOT_AUDITED` | — |
| `THRESHOLD-030` | I | 1330 | 10.A.4 Threshold-estimation depth | local–global shrinkage; | `NOT_AUDITED` | — |
| `CALIBRATION-057` | I | 1331 | 10.A.4 Threshold-estimation depth | calibration-size-aware shrinkage; | `NOT_AUDITED` | — |
| `CALIBRATION-058` | I | 1332 | 10.A.4 Threshold-estimation depth | a bounded split-conformal local-threshold diagnostic. | `NOT_AUDITED` | — |
| `GLOBAL-028` | I | 1342 | 10.A.6 Mechanism analysis | family and cluster granularity; | `NOT_AUDITED` | — |
| `GLOBAL-029` | I | 1343 | 10.A.6 Mechanism analysis | cluster stability; | `NOT_AUDITED` | — |
| `GLOBAL-030` | I | 1345 | 10.A.6 Mechanism analysis | per-client benign and attack score geometry; | `NOT_AUDITED` | — |
| `GLOBAL-031` | I | 1346 | 10.A.6 Mechanism analysis | heterogeneity–benefit association; | `NOT_AUDITED` | — |
| `THRESHOLD-031` | I | 1347 | 10.A.6 Mechanism analysis | threshold movement versus FPR/TPR trade-off. | `NOT_AUDITED` | — |
| `DATASET-022` | I | 1355 | 10.A.7 Hard scope limits | one new IoT dataset; | `NOT_AUDITED` | — |
| `GLOBAL-032` | I | 1356 | 10.A.7 Hard scope limits | four bounded external comparator/stress identities: | `NOT_AUDITED` | — |
| `TRAIN-022` | I | 1357 | 10.A.7 Hard scope limits | FedProx; | `NOT_AUDITED` | — |
| `GLOBAL-033` | I | 1358 | 10.A.7 Hard scope limits | `FEDAVG_LOCAL_FINE_TUNING`; | `NOT_AUDITED` | — |
| `TRAIN-023` | I | 1359 | 10.A.7 Hard scope limits | Ditto; | `NOT_AUDITED` | — |
| `THRESHOLD-032` | I | 1360 | 10.A.7 Hard scope limits | one benign-only federated threshold comparator; | `NOT_AUDITED` | — |
| `THRESHOLD-033` | I | 1361 | 10.A.7 Hard scope limits | five threshold-extension families; | `NOT_AUDITED` | — |
| `CALIBRATION-059` | I | 1362 | 10.A.7 Hard scope limits | one temporal-recalibration family; | `NOT_AUDITED` | — |
| `GLOBAL-034` | I | 1363 | 10.A.7 Hard scope limits | the pre-specified mechanism programme; | `NOT_AUDITED` | — |
| `GLOBAL-035` | I | 1364 | 10.A.7 Hard scope limits | ten paired seeds for the confirmatory endpoint. | `NOT_AUDITED` | — |
| `THRESHOLD-034` | I | 1422 | 10.B.10 Explicit non-expansion guardrails for this amendment | no faithful anomaly-informed Laridi comparator inside the core threshold-scope comparison; | `NOT_AUDITED` | — |
| `CALIBRATION-060` | I | 1423 | 10.B.10 Explicit non-expansion guardrails for this amendment | no ECE or Brier score without a probabilistic-calibration semantics that this roadmap does not define; | `NOT_AUDITED` | — |
| `TRAIN-024` | I | 1424 | 10.B.10 Explicit non-expansion guardrails for this amendment | no APFL/pFedMe/Per-FedAvg/FedRep/FedPer/FedBN personalization zoo beyond the two locked client-model stress routes `FEDAVG_LOCAL_FINE_TUNING` and Ditto; G-PFL-ID and FBID are citation/positioning evidence, not additional implementations; | `NOT_AUDITED` | — |
| `TRAIN-025` | I | 1425 | 10.B.10 Explicit non-expansion guardrails for this amendment | no FedNova/FedAdam/FedYogi/SCAFFOLD/robust-aggregation benchmark zoo beyond the locked FedProx stress test; | `NOT_AUDITED` | — |
| `THRESHOLD-035` | I | 1426 | 10.B.10 Explicit non-expansion guardrails for this amendment | no POT/SPOT/ECDF/PyThresh/KDE/MAD or other broad threshold-estimator benchmark zoo; the locked `TYPE7_Q95` versus historical `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` sensitivity is the bounded estimator-family robustness test; | `NOT_AUDITED` | — |
| `CALIBRATION-061` | I | 1427 | 10.B.10 Explicit non-expansion guardrails for this amendment | no poisoning, backdoor, Byzantine, evasion, or calibration-channel attack experiment in DATP-Core; Rob-FCP and PRISM-FCP remain threat-boundary citations, not baselines; | `NOT_AUDITED` | — |
| `CALIBRATION-062` | I | 1428 | 10.B.10 Explicit non-expansion guardrails for this amendment | no CF-HFC reproduction, Fuzzy-FedProx branch, hardware-aware fuzzy scheduling experiment, or Adaptive Conformal Calibration branch; CF-HFC is citation/positioning evidence only; | `NOT_AUDITED` | — |
| `REPORT-003` | I | 1429 | 10.B.10 Explicit non-expansion guardrails for this amendment | no DP, secure aggregation, or homomorphic-encryption claim unless introduced later as a separately scoped mechanism with its own threat model; | `NOT_AUDITED` | — |
| `DATASET-023` | I | 1430 | 10.B.10 Explicit non-expansion guardrails for this amendment | no extra external dataset added merely to increase dataset count; | `NOT_AUDITED` | — |
| `THRESHOLD-036` | I | 1431 | 10.B.10 Explicit non-expansion guardrails for this amendment | no continuous drift detector, adaptive online controller, or streaming-threshold paper hidden inside the one-shot temporal boundary experiment; | `NOT_AUDITED` | — |
| `GLOBAL-036` | I | 1432 | 10.B.10 Explicit non-expansion guardrails for this amendment | no client-count sweep presented as natural-device scalability evidence. | `NOT_AUDITED` | — |
| `THRESHOLD-037` | I | 1482 | 10.C.2 Threshold-policy identifiers | shrinkage; | `NOT_AUDITED` | — |
| `CALIBRATION-063` | I | 1483 | 10.C.2 Threshold-policy identifiers | conformal variants; | `NOT_AUDITED` | — |
| `THRESHOLD-038` | I | 1484 | 10.C.2 Threshold-policy identifiers | summary-statistics comparators; | `NOT_AUDITED` | — |
| `THRESHOLD-039` | I | 1485 | 10.C.2 Threshold-policy identifiers | stress-test models; | `NOT_AUDITED` | — |
| `THRESHOLD-040` | I | 1486 | 10.C.2 Threshold-policy identifiers | future methods. | `NOT_AUDITED` | — |
| `SCORE-008` | I | 1597 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | **Probability/confidence calibration** — transforms or evaluates predictive probabilities/logits so that confidence corresponds to outcome frequency. Typical quantities include ECE, NLL, and Brier score; FedCal is representative adjacent federated work.[^fedcal2024] DATP-Core does **not** claim this object and reconstruction errors are not probabilities. | `NOT_AUDITED` | — |
| `CALIBRATION-064` | I | 1598 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | **Anomaly operating-point calibration** — maps a fixed anomaly-score distribution plus declared benign calibration evidence to one or more decision thresholds. This is DATP-Core's primary object. Its direct held-out diagnostics are FPR, target-FPR error, calibration-to-held-out generalization gap, threshold-estimation error, and cross-client FPR dispersion. | `NOT_AUDITED` | — |
| `CALIBRATION-065` | I | 1599 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | **Conformal calibration** — uses nonconformity/conformity scores and a finite-sample calibration rule to construct prediction sets or acceptance regions with coverage/risk guarantees under stated assumptions. `LOCAL_CONFORMAL_THRESHOLD` touches this object only as a bounded diagnostic and inherits the explicit validity limitations in §5.4. | `NOT_AUDITED` | — |
| `CALIBRATION-066` | I | 1603 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | ECE, NLL, and Brier score are not added merely because DATP uses the word *calibration*; | `NOT_AUDITED` | — |
| `CALIBRATION-067` | I | 1604 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | held-out benign FPR/coverage and operating-point transfer are the correct primary diagnostics for DATP's threshold object; | `NOT_AUDITED` | — |
| `CALIBRATION-068` | I | 1605 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | FedCal cannot be presented as a direct anomaly-threshold baseline; | `NOT_AUDITED` | — |
| `CALIBRATION-069` | I | 1606 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | conformal coverage terminology may be used only for `LOCAL_CONFORMAL_THRESHOLD` and only with its declared assumptions; | `NOT_AUDITED` | — |
| `CALIBRATION-070` | I | 1607 | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | the manuscript must use **anomaly operating-point calibration** or **threshold calibration** when ambiguity with probability/conformal calibration is possible. | `NOT_AUDITED` | — |
| `REPORT-004` | I | 1613 | 10.C.8 Novelty language | first; | `NOT_AUDITED` | — |
| `CALIBRATION-071` | I | 1614 | 10.C.8 Novelty language | novel federated conformal prediction; | `NOT_AUDITED` | — |
| `THRESHOLD-041` | I | 1615 | 10.C.8 Novelty language | first personalized threshold; | `NOT_AUDITED` | — |
| `REPORT-005` | I | 1616 | 10.C.8 Novelty language | state of the art; | `NOT_AUDITED` | — |
| `REPORT-006` | I | 1617 | 10.C.8 Novelty language | universally superior; | `NOT_AUDITED` | — |
| `REPORT-007` | I | 1618 | 10.C.8 Novelty language | solves non-IID; | `NOT_AUDITED` | — |
| `REPORT-008` | I | 1619 | 10.C.8 Novelty language | guarantees fairness; | `NOT_AUDITED` | — |
| `REPORT-009` | I | 1620 | 10.C.8 Novelty language | privacy preserving; | `NOT_AUDITED` | — |
| `REPORT-010` | I | 1621 | 10.C.8 Novelty language | deployment ready. | `NOT_AUDITED` | — |
| `CALIBRATION-072` | I | 1635 | 10.D.1 Permitted central framing | a controlled threshold-calibration-scope study; | `NOT_AUDITED` | — |
| `REPORT-011` | I | 1636 | 10.D.1 Permitted central framing | a study of operating-point reliability under heterogeneous federated IoT clients; | `NOT_AUDITED` | — |
| `REPORT-012` | I | 1637 | 10.D.1 Permitted central framing | a false-alarm-equity analysis on a fixed anomaly detector; | `NOT_AUDITED` | — |
| `REPORT-013` | I | 1638 | 10.D.1 Permitted central framing | a journal extension with external, stress-test, and mechanism evidence; | `NOT_AUDITED` | — |
| `THRESHOLD-042` | I | 1639 | 10.D.1 Permitted central framing | an evaluation of when threshold personalization remains useful. | `NOT_AUDITED` | — |
| `TRAIN-026` | I | 1645 | 10.D.2 Prohibited central framing | a new federated-learning optimizer; | `NOT_AUDITED` | — |
| `REPORT-014` | I | 1646 | 10.D.2 Prohibited central framing | a complete FL-IDS framework benchmark; | `NOT_AUDITED` | — |
| `REPORT-015` | I | 1647 | 10.D.2 Prohibited central framing | a privacy-preserving security system; | `NOT_AUDITED` | — |
| `REPORT-016` | I | 1648 | 10.D.2 Prohibited central framing | a robust federated-learning defense; | `NOT_AUDITED` | — |
| `REPORT-017` | I | 1649 | 10.D.2 Prohibited central framing | a drift-adaptive production IDS; | `NOT_AUDITED` | — |
| `REPORT-018` | I | 1650 | 10.D.2 Prohibited central framing | a fleet-scale deployment; | `NOT_AUDITED` | — |
| `THRESHOLD-043` | I | 1651 | 10.D.2 Prohibited central framing | a universal thresholding method; | `NOT_AUDITED` | — |
| `REPORT-019` | I | 1652 | 10.D.2 Prohibited central framing | a method that improves every client; | `NOT_AUDITED` | — |
| `METRIC-012` | I | 1653 | 10.D.2 Prohibited central framing | a method that improves global Macro-F1; | `NOT_AUDITED` | — |
| `REPORT-020` | I | 1654 | 10.D.2 Prohibited central framing | a solution to non-IID federated learning. | `NOT_AUDITED` | — |
| `THRESHOLD-044` | I | 1766 | 10.D.9 Novelty boundary and mandatory prior-art audit | local anomaly-threshold estimators; | `NOT_AUDITED` | — |
| `THRESHOLD-045` | I | 1767 | 10.D.9 Novelty boundary and mandatory prior-art audit | federated/shared threshold aggregation; | `NOT_AUDITED` | — |
| `THRESHOLD-046` | I | 1768 | 10.D.9 Novelty boundary and mandatory prior-art audit | anomaly-informed supervised global threshold optimization; | `NOT_AUDITED` | — |
| `THRESHOLD-047` | I | 1769 | 10.D.9 Novelty boundary and mandatory prior-art audit | group/cluster threshold scope; | `NOT_AUDITED` | — |
| `THRESHOLD-048` | I | 1770 | 10.D.9 Novelty boundary and mandatory prior-art audit | personalized-model plus personalized-threshold systems; | `NOT_AUDITED` | — |
| `CALIBRATION-073` | I | 1771 | 10.D.9 Novelty boundary and mandatory prior-art audit | formal federated and personalized calibration/conformal methods. | `NOT_AUDITED` | — |
| `REPORT-021` | I | 1828 | 10.D.9A Submission-time novelty-survival literature gate | every material collision has an explicit overlap/distinction record; | `NOT_AUDITED` | — |
| `REPORT-022` | I | 1829 | 10.D.9A Submission-time novelty-survival literature gate | the collision table above is updated through the search date; | `NOT_AUDITED` | — |
| `REPORT-023` | I | 1830 | 10.D.9A Submission-time novelty-survival literature gate | no central contribution sentence relies on an unverified absolute-priority claim; | `NOT_AUDITED` | — |
| `REPORT-024` | I | 1831 | 10.D.9A Submission-time novelty-survival literature gate | the abstract, introduction, related work, discussion, and conclusion use the same narrowed novelty boundary. | `NOT_AUDITED` | — |
| `THRESHOLD-049` | I | 1907 | 10.D.11 Negative evidence that must remain publishable | every device/seed cell for which LOCAL_THRESHOLD increases FPR or lowers an available TPR/Macro-F1 under the exact paired metric values, together with the §7.5B repeated-seed frequency; no post-hoc magnitude cutoff defines whether the cell is retained; | `NOT_AUDITED` | — |
| `GLOBAL-037` | I | 1908 | 10.D.11 Negative evidence that must remain publishable | any seed with \(\Delta_s\le 0\); | `NOT_AUDITED` | — |
| `THRESHOLD-050` | I | 1909 | 10.D.11 Negative evidence that must remain publishable | any quantile level at which the SHARED_THRESHOLD–LOCAL_THRESHOLD ordering weakens or reverses; | `NOT_AUDITED` | — |
| `THRESHOLD-051` | I | 1910 | 10.D.11 Negative evidence that must remain publishable | shrinkage values that are dominated or non-monotone; | `NOT_AUDITED` | — |
| `THRESHOLD-052` | I | 1911 | 10.D.11 Negative evidence that must remain publishable | FAMILY_THRESHOLD/CLUSTER_THRESHOLD groupings that are unstable or provide no recovery; | `NOT_AUDITED` | — |
| `THRESHOLD-053` | I | 1912 | 10.D.11 Negative evidence that must remain publishable | KLL sketch settings whose approximation materially changes the operating point; | `NOT_AUDITED` | — |
| `DATASET-024` | I | 1913 | 10.D.11 Negative evidence that must remain publishable | external-dataset null or opposite results; | `NOT_AUDITED` | — |
| `PREPROCESS-029` | I | 1914 | 10.D.11 Negative evidence that must remain publishable | preprocessing conditions that attenuate the effect; | `NOT_AUDITED` | — |
| `CALIBRATION-074` | I | 1915 | 10.D.11 Negative evidence that must remain publishable | shared-calibration contributor omissions that materially destabilize the shared threshold or its FPR distribution; | `NOT_AUDITED` | — |
| `THRESHOLD-054` | I | 1916 | 10.D.11 Negative evidence that must remain publishable | FedProx conditions that absorb the threshold-scope effect; | `NOT_AUDITED` | — |
| `TRAIN-027` | I | 1917 | 10.D.11 Negative evidence that must remain publishable | FedProx conditions whose downstream result is null while the measured local-update drift is barely changed or moves in the opposite direction; | `NOT_AUDITED` | — |
| `TRAIN-028` | I | 1918 | 10.D.11 Negative evidence that must remain publishable | every `FEDAVG_LOCAL_FINE_TUNING` or Ditto condition that largely absorbs or reverses the shared-to-local scope effect under the locked §7.2B bands; | `NOT_AUDITED` | — |
| `THRESHOLD-055` | I | 1919 | 10.D.11 Negative evidence that must remain publishable | any model-side stress condition that changes detector parameters but fails to reduce `ModelAlignmentH`, score-location/scale dispersion, local-q95 dispersion, or normalized shared-local threshold distance; | `NOT_AUDITED` | — |
| `TEMPORAL-001` | I | 1920 | 10.D.11 Negative evidence that must remain publishable | temporal windows with no drift or no recovery; | `NOT_AUDITED` | — |
| `CALIBRATION-075` | I | 1921 | 10.D.11 Negative evidence that must remain publishable | LOCAL_CONFORMAL_THRESHOLD undercoverage, overcoverage, or coarse finite-sample behavior. | `NOT_AUDITED` | — |
| `GLOBAL-038` | II | 2119 | 1.2 Experiment specification format | **Scientific role** | `NOT_AUDITED` | — |
| `GLOBAL-039` | II | 2120 | 1.2 Experiment specification format | **Question** | `NOT_AUDITED` | — |
| `GLOBAL-040` | II | 2121 | 1.2 Experiment specification format | **Why the experiment is necessary** | `NOT_AUDITED` | — |
| `DATASET-025` | II | 2122 | 1.2 Experiment specification format | **Population and inputs** | `NOT_AUDITED` | — |
| `GLOBAL-041` | II | 2123 | 1.2 Experiment specification format | **Fixed elements** | `NOT_AUDITED` | — |
| `GLOBAL-042` | II | 2124 | 1.2 Experiment specification format | **Experimental factors** | `NOT_AUDITED` | — |
| `GLOBAL-043` | II | 2125 | 1.2 Experiment specification format | **Comparison set** | `NOT_AUDITED` | — |
| `GLOBAL-044` | II | 2126 | 1.2 Experiment specification format | **Procedure** | `NOT_AUDITED` | — |
| `GLOBAL-045` | II | 2127 | 1.2 Experiment specification format | **Required outcomes** | `NOT_AUDITED` | — |
| `STAT-002` | II | 2128 | 1.2 Experiment specification format | **Statistical unit and analysis** | `NOT_AUDITED` | — |
| `GLOBAL-046` | II | 2129 | 1.2 Experiment specification format | **Interpretation rules** | `NOT_AUDITED` | — |
| `GLOBAL-047` | II | 2130 | 1.2 Experiment specification format | **Dependencies and feasibility** | `NOT_AUDITED` | — |
| `BOUNDARY-003` | II | 2131 | 1.2 Experiment specification format | **Prohibited uses** | `NOT_AUDITED` | — |
| `THRESHOLD-056` | II | 2191 | 2.7 Manuscript evidence narrative | **Does threshold scope matter?** — NBAIOT_NATURAL_DEVICES confirmatory shared versus local. | `NOT_AUDITED` | — |
| `THRESHOLD-057` | II | 2192 | 2.7 Manuscript evidence narrative | **Why does it matter?** — CDF/JS geometry, FAMILY_THRESHOLD/CLUSTER_THRESHOLD mechanism, threshold movement, held-out target attainment. | `NOT_AUDITED` | — |
| `PREPROCESS-030` | II | 2193 | 2.7 Manuscript evidence narrative | **When does it matter?** — heterogeneity severity, calibration support, their interaction, quantile sensitivity, shrinkage, preprocessing sensitivity. | `NOT_AUDITED` | — |
| `TRAIN-029` | II | 2194 | 2.7 Manuscript evidence narrative | **When does it stop mattering?** — near-homogeneous CICIoT2023 boundary, FedProx absorption, simple post-FedAvg local fine-tuning absorption, Ditto absorption, external validation, and temporal boundary evidence. | `NOT_AUDITED` | — |
| `SCORE-009` | II | 2200 | 2.7A Three competing explanations that the programme must eliminate or bound | **Scope effect** — heterogeneous clients genuinely require different operating points even when the detector and score artifacts are fixed. Primary evidence: the confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD paired `CV(FPR)` effect, held-out target attainment, per-device threshold/FPR movement, and grouped-scope mechanism analyses. | `NOT_AUDITED` | — |
| `SCORE-010` | II | 2201 | 2.7A Three competing explanations that the programme must eliminate or bound | **Estimator artifact** — the apparent effect exists only because the canonical shared threshold is poorly constructed or because `q=0.95` is a special estimator. Required attacks on this explanation: exact pooled shared, sample-weighted shared, KLL shared, `FEDERATED_BENIGN_SUMMARY_THRESHOLD`, quantile sensitivity, and the fixed-score `TYPE7_Q95` versus `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` 2×2. | `NOT_AUDITED` | — |
| `PREPROCESS-031` | II | 2202 | 2.7A Three competing explanations that the programme must eliminate or bound | **Upstream absorption** — better representation, preprocessing, heterogeneity-aware optimization, or personalized models remove the score heterogeneity that creates the threshold-scope effect. Required attacks on this explanation: pooled-MinMax preprocessing sensitivity, FedProx mechanism-activation/absorption, the literature-backed 10-epoch `FEDAVG_LOCAL_FINE_TUNING` 2×2, the canonical Ditto 2×2, and the common score-alignment/threshold-absorption diagnostics from Part I §7.2B. The required mechanistic chain is `upstream adaptation -> lower score heterogeneity/dispersion -> lower shared-local threshold mismatch -> lower DeltaScope`; every arrow is measured rather than presumed. | `NOT_AUDITED` | — |
| `THRESHOLD-058` | II | 2293 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | CENTRALIZED_REFERENCE, SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, and CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `DATASET-026` | II | 2294 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | the confirmatory shared-versus-local experiment; | `NOT_AUDITED` | — |
| `THRESHOLD-059` | II | 2295 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | shared-threshold construction controls; | `NOT_AUDITED` | — |
| `THRESHOLD-060` | II | 2296 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | quantile sensitivity; | `NOT_AUDITED` | — |
| `DATASET-027` | II | 2297 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | family/cluster granularity and stability; | `NOT_AUDITED` | — |
| `DATASET-028` | II | 2298 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | score-distribution mechanism analyses; | `NOT_AUDITED` | — |
| `CALIBRATION-076` | II | 2299 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | calibration-size ablation; | `NOT_AUDITED` | — |
| `THRESHOLD-061` | II | 2300 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | local–global shrinkage; | `NOT_AUDITED` | — |
| `CALIBRATION-077` | II | 2301 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | LOCAL_CONFORMAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-062` | II | 2302 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; | `NOT_AUDITED` | — |
| `THRESHOLD-063` | II | 2303 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | `FEDERATED_KLL_SHARED_THRESHOLD`; | `NOT_AUDITED` | — |
| `CALIBRATION-078` | II | 2304 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | attack-family TPR breakdown for Mirai and BASHLITE where client-level family support is valid; | `NOT_AUDITED` | — |
| `DATASET-029` | II | 2305 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | equity–utility Pareto analysis; | `NOT_AUDITED` | — |
| `PREPROCESS-032` | II | 2306 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | bounded preprocessing sensitivity; | `NOT_AUDITED` | — |
| `CALIBRATION-079` | II | 2307 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | calibration cold-start boundary; | `NOT_AUDITED` | — |
| `TRAIN-030` | II | 2308 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | FedProx; | `NOT_AUDITED` | — |
| `DATASET-030` | II | 2309 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | `FEDAVG_LOCAL_FINE_TUNING`; | `NOT_AUDITED` | — |
| `TRAIN-031` | II | 2310 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | Ditto; | `NOT_AUDITED` | — |
| `DATASET-031` | II | 2311 | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | operational alert-burden translation when a real or cited traffic rate exists. | `NOT_AUDITED` | — |
| `DATASET-032` | II | 2335 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | device-level generalization on CICIoT2023; | `NOT_AUDITED` | — |
| `DATASET-033` | II | 2336 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | physical-client equity; | `NOT_AUDITED` | — |
| `DATASET-034` | II | 2337 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | temporal behavior; | `NOT_AUDITED` | — |
| `THRESHOLD-064` | II | 2338 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | device-aware threshold performance on the original 105-device topology. | `NOT_AUDITED` | — |
| `DATASET-035` | II | 2342 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | CENTRALIZED_REFERENCE; | `NOT_AUDITED` | — |
| `THRESHOLD-065` | II | 2343 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-066` | II | 2344 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-067` | II | 2345 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `DATASET-036` | II | 2346 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | pairwise benign-distribution Jensen–Shannon divergence; | `NOT_AUDITED` | — |
| `DATASET-037` | II | 2347 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | `CV(FPR)`, IQR, and range; | `NOT_AUDITED` | — |
| `THRESHOLD-068` | II | 2348 | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | descriptive quantile-estimation comparisons. | `NOT_AUDITED` | — |
| `THRESHOLD-069` | II | 2374 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-070` | II | 2375 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-071` | II | 2376 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | CLUSTER_THRESHOLD. | `NOT_AUDITED` | — |
| `DATASET-038` | II | 2386 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | strict monotonicity is not required; | `NOT_AUDITED` | — |
| `DATASET-039` | II | 2387 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | overlapping low-alpha seed distributions are described as a high-heterogeneity band; | `NOT_AUDITED` | — |
| `DATASET-040` | II | 2388 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | a non-monotone result is reported; | `NOT_AUDITED` | — |
| `DATASET-041` | II | 2389 | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | the sweep does not become confirmatory. | `NOT_AUDITED` | — |
| `DATASET-042` | II | 2431 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | per-client benign FPR; | `NOT_AUDITED` | — |
| `DATASET-043` | II | 2432 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | cross-client `CV(FPR)`; | `NOT_AUDITED` | — |
| `DATASET-044` | II | 2433 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | IQR and range of FPR; | `NOT_AUDITED` | — |
| `DATASET-045` | II | 2434 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-072` | II | 2435 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | threshold dispersion; | `NOT_AUDITED` | — |
| `DATASET-046` | II | 2436 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | benign score-distribution analysis; | `NOT_AUDITED` | — |
| `THRESHOLD-073` | II | 2437 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-074` | II | 2438 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; | `NOT_AUDITED` | — |
| `THRESHOLD-075` | II | 2439 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | quantile sensitivity; | `NOT_AUDITED` | — |
| `CALIBRATION-080` | II | 2440 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | calibration-size and shrinkage analyses where sample support permits; | `NOT_AUDITED` | — |
| `TRAIN-032` | II | 2441 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | FedProx and Ditto stress tests where training is feasible. | `NOT_AUDITED` | — |
| `DATASET-047` | II | 2449 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | TPR; | `NOT_AUDITED` | — |
| `DATASET-048` | II | 2450 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | recall; | `NOT_AUDITED` | — |
| `DATASET-049` | II | 2451 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | Macro-F1; | `NOT_AUDITED` | — |
| `DATASET-050` | II | 2452 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | P10 Macro-F1; | `NOT_AUDITED` | — |
| `DATASET-051` | II | 2453 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | balanced accuracy; | `NOT_AUDITED` | — |
| `DATASET-052` | II | 2454 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | worst-client balanced accuracy; | `NOT_AUDITED` | — |
| `SCORE-011` | II | 2455 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | per-client AUROC; | `NOT_AUDITED` | — |
| `THRESHOLD-076` | II | 2456 | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | attack-sensitive threshold trade-offs. | `NOT_AUDITED` | — |
| `CALIBRATION-081` | II | 2489 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | threshold frozen from historical calibration; | `NOT_AUDITED` | — |
| `CALIBRATION-082` | II | 2490 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | one-shot threshold recomputed from the future recalibration window; | `NOT_AUDITED` | — |
| `CALIBRATION-083` | II | 2491 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | matched random-fractional static reference over the same nine clients. The static reference uses the same 55/15/10/20 row budget after deterministic client-local randomization: train, calibration, an explicitly retained but non-fitted/non-scored/non-evaluated reserve, and evaluation. The reserve preserves row-budget comparability without assigning a false temporal meaning to static rows. | `NOT_AUDITED` | — |
| `CALIBRATION-084` | II | 2497 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | streaming recalibration; | `NOT_AUDITED` | — |
| `CALIBRATION-085` | II | 2498 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | periodic recalibration; | `NOT_AUDITED` | — |
| `CALIBRATION-086` | II | 2499 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | sliding windows; | `NOT_AUDITED` | — |
| `CALIBRATION-087` | II | 2500 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | Page–Hinkley; | `NOT_AUDITED` | — |
| `CALIBRATION-088` | II | 2501 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | FLARE; | `NOT_AUDITED` | — |
| `CALIBRATION-089` | II | 2502 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | FLAME; | `NOT_AUDITED` | — |
| `CALIBRATION-090` | II | 2503 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | automatic drift detection; | `NOT_AUDITED` | — |
| `CALIBRATION-091` | II | 2504 | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | cross-dataset transfer. | `NOT_AUDITED` | — |
| `THRESHOLD-077` | II | 2528 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | NBAIOT_NATURAL_DEVICES; | `NOT_AUDITED` | — |
| `THRESHOLD-078` | II | 2529 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | nine physical-device clients; | `NOT_AUDITED` | — |
| `THRESHOLD-079` | II | 2530 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | ten paired training seeds; | `NOT_AUDITED` | — |
| `THRESHOLD-080` | II | 2531 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | one terminal scientific detector per seed; | `NOT_AUDITED` | — |
| `CALIBRATION-092` | II | 2532 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | benign calibration scores; | `NOT_AUDITED` | — |
| `THRESHOLD-081` | II | 2533 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | held-out benign and attack test scores; | `NOT_AUDITED` | — |
| `CALIBRATION-093` | II | 2534 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | unchanged eligibility. | `NOT_AUDITED` | — |
| `THRESHOLD-082` | II | 2538 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | autoencoder architecture; | `NOT_AUDITED` | — |
| `THRESHOLD-083` | II | 2539 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | FedAvg training; | `NOT_AUDITED` | — |
| `THRESHOLD-084` | II | 2540 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | local epochs `E = 1`; | `NOT_AUDITED` | — |
| `THRESHOLD-085` | II | 2541 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | full participation; | `NOT_AUDITED` | — |
| `PREPROCESS-033` | II | 2542 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | preprocessing; | `NOT_AUDITED` | — |
| `THRESHOLD-086` | II | 2543 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | terminal scientific-model rule; | `NOT_AUDITED` | — |
| `THRESHOLD-087` | II | 2544 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | quantile `q = 0.95`; | `NOT_AUDITED` | — |
| `THRESHOLD-088` | II | 2545 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | test records; | `NOT_AUDITED` | — |
| `THRESHOLD-089` | II | 2546 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | metric implementation; | `NOT_AUDITED` | — |
| `THRESHOLD-090` | II | 2547 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | historical temporal-gap data partition (per-device chronological source-row order, `60 / 1 / 20 / 1 / 18`, guard gaps discarded, scaler fit on training rows only). | `NOT_AUDITED` | — |
| `THRESHOLD-091` | II | 2553 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | SHARED_THRESHOLD shared threshold; | `NOT_AUDITED` | — |
| `THRESHOLD-092` | II | 2554 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | LOCAL_THRESHOLD per-client threshold. | `NOT_AUDITED` | — |
| `THRESHOLD-093` | II | 2558 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Reproduce the locked five-seed subset using the journal implementation. | `NOT_AUDITED` | — |
| `THRESHOLD-094` | II | 2559 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Apply the anchor reproduction gate (§5.2) to the reproduced five-seed result. Do not proceed to step 3 unless the gate emits an anchor-success verdict. | `NOT_AUDITED` | — |
| `THRESHOLD-095` | II | 2560 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Extend execution to ten paired seeds. | `NOT_AUDITED` | — |
| `THRESHOLD-096` | II | 2561 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | For every seed, compute per-client FPR under SHARED_THRESHOLD and LOCAL_THRESHOLD. | `NOT_AUDITED` | — |
| `THRESHOLD-097` | II | 2562 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Compute `CV(FPR)` over the same eligible clients. | `NOT_AUDITED` | — |
| `THRESHOLD-098` | II | 2563 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Compute the paired seed-level contrast: | `NOT_AUDITED` | — |
| `THRESHOLD-099` | II | 2573 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Report all ten seed-level contrasts. | `NOT_AUDITED` | — |
| `THRESHOLD-100` | II | 2574 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Compute the locked 95% BCa confidence interval over the ten paired contrasts. | `NOT_AUDITED` | — |
| `THRESHOLD-101` | II | 2575 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Report sign consistency and the exact paired sign-test diagnostic defined in Part III §12.1A. | `NOT_AUDITED` | — |
| `THRESHOLD-102` | II | 2576 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Report IQR and max–min FPR alongside CV to guard against small-denominator distortion. | `NOT_AUDITED` | — |
| `THRESHOLD-103` | II | 2577 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Report absolute paired changes in worst-client FPR and FPR IQR, plus the descriptive relative `CV(FPR)` reduction defined in Part III §11.1A. | `NOT_AUDITED` | — |
| `SCORE-012` | II | 2578 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Execute the leave-one-device-out influence diagnostic in Part III §15.1A using the already generated score artifacts; do not retrain or rescore. | `NOT_AUDITED` | — |
| `THRESHOLD-104` | II | 2579 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Report detection-quality controls for NBAIOT_NATURAL_DEVICES without treating them as the primary verdict. | `NOT_AUDITED` | — |
| `THRESHOLD-105` | II | 2583 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | SHARED_THRESHOLD and LOCAL_THRESHOLD per-client FPR for every seed; | `NOT_AUDITED` | — |
| `THRESHOLD-106` | II | 2584 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | seed-level SHARED_THRESHOLD and LOCAL_THRESHOLD `CV(FPR)`; | `NOT_AUDITED` | — |
| `THRESHOLD-107` | II | 2585 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | ten paired deltas; | `NOT_AUDITED` | — |
| `THRESHOLD-108` | II | 2586 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | arithmetic-mean paired delta as the confirmatory point estimate, plus the descriptive median paired delta; | `NOT_AUDITED` | — |
| `THRESHOLD-109` | II | 2587 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | 95% BCa interval; | `NOT_AUDITED` | — |
| `THRESHOLD-110` | II | 2588 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | sign-consistency positive/zero/negative counts and exact paired sign-test p-value as secondary evidence; | `NOT_AUDITED` | — |
| `THRESHOLD-111` | II | 2589 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | IQR and range; | `NOT_AUDITED` | — |
| `THRESHOLD-112` | II | 2590 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | `DeltaWorstFPR`, `DeltaIQR`, and descriptive `RelativeCVReduction`; | `NOT_AUDITED` | — |
| `THRESHOLD-113` | II | 2591 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | complete leave-one-device-out `Delta_(s,-j)` values, per-device ten-seed mean, `MinLODOMean`, `MaxLODOMean`, `MaxLODOShift`, and positive-direction retention count; | `NOT_AUDITED` | — |
| `THRESHOLD-114` | II | 2592 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | Macro-F1, balanced accuracy, TPR, and P10 Macro-F1 controls; | `NOT_AUDITED` | — |
| `THRESHOLD-115` | II | 2593 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | complete nine-client result display. | `NOT_AUDITED` | — |
| `THRESHOLD-116` | II | 2622 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | no alteration of the terminal detector from this result; | `NOT_AUDITED` | — |
| `CALIBRATION-094` | II | 2623 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | no replacement by CLUSTER_THRESHOLD, shrinkage, or LOCAL_CONFORMAL_THRESHOLD if the endpoint fails; | `NOT_AUDITED` | — |
| `THRESHOLD-117` | II | 2624 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | no removal of unfavorable seeds; | `NOT_AUDITED` | — |
| `THRESHOLD-118` | II | 2625 | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | no claim that LOCAL_THRESHOLD improves overall detection performance. | `NOT_AUDITED` | — |
| `PROVENANCE-002` | II | 2647 | 5.2 Anchor reproduction gate | the exact historical five-seed cohort is used; | `NOT_AUDITED` | — |
| `DATASET-053` | II | 2648 | 5.2 Anchor reproduction gate | the historical anchor dataset identity is preserved; | `NOT_AUDITED` | — |
| `DATASET-054` | II | 2649 | 5.2 Anchor reproduction gate | the historical client population is preserved; | `NOT_AUDITED` | — |
| `PREPROCESS-034` | II | 2650 | 5.2 Anchor reproduction gate | the historical preprocessing identity is preserved; | `NOT_AUDITED` | — |
| `TRAIN-033` | II | 2651 | 5.2 Anchor reproduction gate | the historical training protocol is preserved; | `NOT_AUDITED` | — |
| `PROVENANCE-003` | II | 2652 | 5.2 Anchor reproduction gate | the historical terminal-model semantics are preserved; | `NOT_AUDITED` | — |
| `SCORE-013` | II | 2653 | 5.2 Anchor reproduction gate | the historical scoring semantics are preserved; | `NOT_AUDITED` | — |
| `THRESHOLD-119` | II | 2654 | 5.2 Anchor reproduction gate | the historical threshold semantics are preserved; | `NOT_AUDITED` | — |
| `CALIBRATION-095` | II | 2655 | 5.2 Anchor reproduction gate | the historical eligibility semantics are preserved; | `NOT_AUDITED` | — |
| `METRIC-013` | II | 2656 | 5.2 Anchor reproduction gate | the historical metric definition is preserved; | `NOT_AUDITED` | — |
| `STAT-003` | II | 2657 | 5.2 Anchor reproduction gate | the reproduced 95% BCa interval remains entirely positive; | `NOT_AUDITED` | — |
| `PROVENANCE-004` | II | 2658 | 5.2 Anchor reproduction gate | the reproduced interval overlaps `[0.647, 0.769]`; | `NOT_AUDITED` | — |
| `PROVENANCE-005` | II | 2659 | 5.2 Anchor reproduction gate | the reproduced interval width is `<= 0.1464`; | `NOT_AUDITED` | — |
| `PROVENANCE-006` | II | 2660 | 5.2 Anchor reproduction gate | required artifact lineage, provenance, identity, serialization, and reload-validation gates pass. | `NOT_AUDITED` | — |
| `PROVENANCE-007` | II | 2668 | `ANCHOR_REPRODUCTION_FAILED` | blocks the ten-seed journal extension; | `NOT_AUDITED` | — |
| `REPORT-025` | II | 2669 | `ANCHOR_REPRODUCTION_FAILED` | blocks downstream journal claim-generating execution; | `NOT_AUDITED` | — |
| `PROVENANCE-008` | II | 2670 | `ANCHOR_REPRODUCTION_FAILED` | requires investigation; | `NOT_AUDITED` | — |
| `PROVENANCE-009` | II | 2671 | `ANCHOR_REPRODUCTION_FAILED` | requires a successful anchor reproduction before proceeding; | `NOT_AUDITED` | — |
| `CALIBRATION-096` | II | 2672 | `ANCHOR_REPRODUCTION_FAILED` | is not overridden by supportive evidence; | `NOT_AUDITED` | — |
| `PROVENANCE-010` | II | 2673 | `ANCHOR_REPRODUCTION_FAILED` | is not overridden by external validation; | `NOT_AUDITED` | — |
| `THRESHOLD-120` | II | 2674 | `ANCHOR_REPRODUCTION_FAILED` | is not overridden by favorable alternative threshold methods; | `NOT_AUDITED` | — |
| `PROVENANCE-011` | II | 2675 | `ANCHOR_REPRODUCTION_FAILED` | is never relaxed after observing the result; the fourteen acceptance conditions above cannot be loosened post hoc. | `NOT_AUDITED` | — |
| `BOUNDARY-004` | II | 2687 | 5.3 Confirmatory inference unavailable | fewer than ten valid paired seed deltas; | `NOT_AUDITED` | — |
| `STAT-004` | II | 2688 | 5.3 Confirmatory inference unavailable | undefined BCa acceleration; | `NOT_AUDITED` | — |
| `STAT-005` | II | 2689 | 5.3 Confirmatory inference unavailable | invalid BCa acceleration; | `NOT_AUDITED` | — |
| `STAT-006` | II | 2690 | 5.3 Confirmatory inference unavailable | degenerate bootstrap distribution; | `NOT_AUDITED` | — |
| `STAT-007` | II | 2691 | 5.3 Confirmatory inference unavailable | another explicitly detected BCa degeneracy that prevents valid computation of the locked interval. | `NOT_AUDITED` | — |
| `BOUNDARY-005` | II | 2695 | 5.3 Confirmatory inference unavailable | every available paired seed-level delta; | `NOT_AUDITED` | — |
| `BOUNDARY-006` | II | 2696 | 5.3 Confirmatory inference unavailable | the arithmetic mean paired delta; | `NOT_AUDITED` | — |
| `BOUNDARY-007` | II | 2697 | 5.3 Confirmatory inference unavailable | sign counts; | `NOT_AUDITED` | — |
| `STAT-008` | II | 2698 | 5.3 Confirmatory inference unavailable | the exact reason BCa inference was unavailable; | `NOT_AUDITED` | — |
| `BOUNDARY-008` | II | 2699 | 5.3 Confirmatory inference unavailable | valid descriptive secondary statistics; | `NOT_AUDITED` | — |
| `STAT-009` | II | 2700 | 5.3 Confirmatory inference unavailable | percentile/basic bootstrap intervals only when explicitly labelled as diagnostics. | `NOT_AUDITED` | — |
| `THRESHOLD-121` | II | 2720 | 6.1 Shared-threshold construction sensitivity | SHARED_THRESHOLD arithmetic mean of local quantiles; | `NOT_AUDITED` | — |
| `THRESHOLD-122` | II | 2721 | 6.1 Shared-threshold construction sensitivity | exact pooled benign type-7 quantile; | `NOT_AUDITED` | — |
| `THRESHOLD-123` | II | 2722 | 6.1 Shared-threshold construction sensitivity | sample-weighted mean of eligible local type-7 quantiles; | `NOT_AUDITED` | — |
| `THRESHOLD-124` | II | 2723 | 6.1 Shared-threshold construction sensitivity | `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`; | `NOT_AUDITED` | — |
| `THRESHOLD-125` | II | 2724 | 6.1 Shared-threshold construction sensitivity | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` with the locked matched-target construction; | `NOT_AUDITED` | — |
| `THRESHOLD-126` | II | 2725 | 6.1 Shared-threshold construction sensitivity | LOCAL_THRESHOLD local quantiles. | `NOT_AUDITED` | — |
| `THRESHOLD-127` | II | 2735 | 6.1 Shared-threshold construction sensitivity | compute the shared threshold; | `NOT_AUDITED` | — |
| `THRESHOLD-128` | II | 2736 | 6.1 Shared-threshold construction sensitivity | evaluate all eligible clients; | `NOT_AUDITED` | — |
| `THRESHOLD-129` | II | 2737 | 6.1 Shared-threshold construction sensitivity | compute `CV(FPR)`, IQR, range, and worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-130` | II | 2738 | 6.1 Shared-threshold construction sensitivity | calculate the paired difference relative to LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-131` | II | 2739 | 6.1 Shared-threshold construction sensitivity | report achieved pooled and per-client exceedance. | `NOT_AUDITED` | — |
| `THRESHOLD-132` | II | 2774 | 6.2 Quantile-level sensitivity | compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and canonical CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-133` | II | 2775 | 6.2 Quantile-level sensitivity | evaluate on unchanged held-out test scores; | `NOT_AUDITED` | — |
| `THRESHOLD-134` | II | 2776 | 6.2 Quantile-level sensitivity | report mean FPR, `CV(FPR)`, IQR, range, worst-client FPR, TPR, and P10 Macro-F1; | `NOT_AUDITED` | — |
| `THRESHOLD-135` | II | 2777 | 6.2 Quantile-level sensitivity | report achieved benign exceedance against the target `1 - q`; | `NOT_AUDITED` | — |
| `THRESHOLD-136` | II | 2778 | 6.2 Quantile-level sensitivity | visualize the policy-by-quantile surface. | `NOT_AUDITED` | — |
| `THRESHOLD-137` | II | 2798 | 6.2A Threshold-estimator × scope sensitivity | NBAIOT_NATURAL_DEVICES only; | `NOT_AUDITED` | — |
| `SCORE-014` | II | 2799 | 6.2A Threshold-estimator × scope sensitivity | the exact same ten frozen FedAvg detector/score artifacts as §5.1; | `NOT_AUDITED` | — |
| `CALIBRATION-097` | II | 2800 | 6.2A Threshold-estimator × scope sensitivity | the same eligible clients, calibration records, evaluation rows, labels, and metric implementation; | `NOT_AUDITED` | — |
| `SCORE-015` | II | 2801 | 6.2A Threshold-estimator × scope sensitivity | no retraining, rescoring, calibration resampling, or windowed majority-vote stage. | `NOT_AUDITED` | — |
| `SCORE-016` | II | 2830 | 6.2A Threshold-estimator × scope sensitivity | load the canonical fixed calibration/test score artifact for each seed; | `NOT_AUDITED` | — |
| `THRESHOLD-138` | II | 2831 | 6.2A Threshold-estimator × scope sensitivity | compute the four locked estimator/scope thresholds; | `NOT_AUDITED` | — |
| `THRESHOLD-139` | II | 2832 | 6.2A Threshold-estimator × scope sensitivity | evaluate per-client FPR and attack-sensitive controls on the unchanged held-out evaluation scores; | `NOT_AUDITED` | — |
| `CALIBRATION-098` | II | 2833 | 6.2A Threshold-estimator × scope sensitivity | compute `CV(FPR)`, IQR, range, worst-client FPR, held-out target/attainment diagnostics where a nominal target exists, and the calibration-generalization gap from Part III §4.8; | `NOT_AUDITED` | — |
| `THRESHOLD-140` | II | 2834 | 6.2A Threshold-estimator × scope sensitivity | compute `Delta_scope[s,E]` for both estimator families and `Delta_estimator[s]`; | `NOT_AUDITED` | — |
| `THRESHOLD-141` | II | 2835 | 6.2A Threshold-estimator × scope sensitivity | report all ten seeds; no estimator or seed may be omitted because it weakens the desired pattern. | `NOT_AUDITED` | — |
| `THRESHOLD-142` | II | 2839 | 6.2A Threshold-estimator × scope sensitivity | all four threshold conditions per seed/client; | `NOT_AUDITED` | — |
| `THRESHOLD-143` | II | 2840 | 6.2A Threshold-estimator × scope sensitivity | per-client FPR, TPR, balanced accuracy, and Macro-F1; | `NOT_AUDITED` | — |
| `THRESHOLD-144` | II | 2841 | 6.2A Threshold-estimator × scope sensitivity | `CV(FPR)`, IQR, range, and worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-145` | II | 2842 | 6.2A Threshold-estimator × scope sensitivity | ten `Delta_scope[Q95]` values; | `NOT_AUDITED` | — |
| `THRESHOLD-146` | II | 2843 | 6.2A Threshold-estimator × scope sensitivity | ten `Delta_scope[MEAN+SD]` values; | `NOT_AUDITED` | — |
| `THRESHOLD-147` | II | 2844 | 6.2A Threshold-estimator × scope sensitivity | ten `Delta_estimator` values; | `NOT_AUDITED` | — |
| `THRESHOLD-148` | II | 2845 | 6.2A Threshold-estimator × scope sensitivity | sign counts for each estimator's scope gain; | `NOT_AUDITED` | — |
| `THRESHOLD-149` | II | 2846 | 6.2A Threshold-estimator × scope sensitivity | paired descriptive BCa interval for mean `Delta_scope[MEAN+SD]` when defined, explicitly secondary; | `NOT_AUDITED` | — |
| `THRESHOLD-150` | II | 2847 | 6.2A Threshold-estimator × scope sensitivity | complete negative-result reporting when the moment estimator weakens or reverses the scope effect. | `NOT_AUDITED` | — |
| `CALIBRATION-099` | II | 2851 | 6.2A Threshold-estimator × scope sensitivity | positive mean scope gain under both estimators: evidence that the calibration-scope phenomenon is not unique to q95; | `NOT_AUDITED` | — |
| `THRESHOLD-151` | II | 2852 | 6.2A Threshold-estimator × scope sensitivity | positive q95 gain but null/opposite moment-rule gain: estimator-dependent scope effect; | `NOT_AUDITED` | — |
| `CALIBRATION-100` | II | 2853 | 6.2A Threshold-estimator × scope sensitivity | stronger moment-rule gain: supportive robustness only, not permission to replace q95; | `NOT_AUDITED` | — |
| `THRESHOLD-152` | II | 2854 | 6.2A Threshold-estimator × scope sensitivity | moment-rule failure or poor utility: report as a historical estimator limitation. | `NOT_AUDITED` | — |
| `DATASET-055` | II | 2870 | 6.3 Controlled non-IID severity | NBAIOT_DIRICHLET_CLIENTS; | `NOT_AUDITED` | — |
| `GLOBAL-048` | II | 2871 | 6.3 Controlled non-IID severity | 20 synthetic clients; | `NOT_AUDITED` | — |
| `DATASET-056` | II | 2872 | 6.3 Controlled non-IID severity | Dirichlet severity grid: | `NOT_AUDITED` | — |
| `GLOBAL-049` | II | 2873 | 6.3 Controlled non-IID severity | `0.1`; | `NOT_AUDITED` | — |
| `GLOBAL-050` | II | 2874 | 6.3 Controlled non-IID severity | `0.3`; | `NOT_AUDITED` | — |
| `GLOBAL-051` | II | 2875 | 6.3 Controlled non-IID severity | `0.5`; | `NOT_AUDITED` | — |
| `GLOBAL-052` | II | 2876 | 6.3 Controlled non-IID severity | `1.0`; | `NOT_AUDITED` | — |
| `GLOBAL-053` | II | 2877 | 6.3 Controlled non-IID severity | `10.0`; | `NOT_AUDITED` | — |
| `GLOBAL-054` | II | 2878 | 6.3 Controlled non-IID severity | IID; | `NOT_AUDITED` | — |
| `THRESHOLD-153` | II | 2879 | 6.3 Controlled non-IID severity | SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `GLOBAL-055` | II | 2880 | 6.3 Controlled non-IID severity | ten paired seeds where feasible. | `NOT_AUDITED` | — |
| `GLOBAL-056` | II | 2886 | 6.3 Controlled non-IID severity | construct the partition using the locked seed and partition rule; | `NOT_AUDITED` | — |
| `GLOBAL-057` | II | 2887 | 6.3 Controlled non-IID severity | retain the pre-specified partition; | `NOT_AUDITED` | — |
| `PREPROCESS-035` | II | 2888 | 6.3 Controlled non-IID severity | train a separate terminal `FEDAVG` detector for this `(training seed, heterogeneity severity)` cell under the fixed training protocol below — this includes IID as one severity condition in this grid; never share another severity's fitted preprocessing state, detector state, calibration scores, or evaluation scores; | `NOT_AUDITED` | — |
| `THRESHOLD-154` | II | 2889 | 6.3 Controlled non-IID severity | compute SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `REPORT-026` | II | 2890 | 6.3 Controlled non-IID severity | report heterogeneity diagnostics; | `NOT_AUDITED` | — |
| `THRESHOLD-155` | II | 2891 | 6.3 Controlled non-IID severity | compute the SHARED_THRESHOLD–LOCAL_THRESHOLD `CV(FPR)` difference; | `NOT_AUDITED` | — |
| `REPORT-027` | II | 2892 | 6.3 Controlled non-IID severity | report uncertainty per alpha; | `NOT_AUDITED` | — |
| `GLOBAL-058` | II | 2893 | 6.3 Controlled non-IID severity | display seed distributions rather than only point estimates. | `NOT_AUDITED` | — |
| `GLOBAL-059` | II | 2907 | 6.3 Controlled non-IID severity | client sample-count distribution; | `NOT_AUDITED` | — |
| `GLOBAL-060` | II | 2908 | 6.3 Controlled non-IID severity | client benign-distribution divergence; | `NOT_AUDITED` | — |
| `GLOBAL-061` | II | 2909 | 6.3 Controlled non-IID severity | class or attack composition when valid; | `NOT_AUDITED` | — |
| `GLOBAL-062` | II | 2910 | 6.3 Controlled non-IID severity | eligible-client coverage; | `NOT_AUDITED` | — |
| `GLOBAL-063` | II | 2911 | 6.3 Controlled non-IID severity | pairwise or aggregate Jensen–Shannon divergence. | `NOT_AUDITED` | — |
| `THRESHOLD-156` | II | 2931 | 7.1 Threshold-sharing granularity and cluster stability | Does family or cluster threshold sharing recover part of LOCAL_THRESHOLD’s FPR-equity benefit? | `NOT_AUDITED` | — |
| `CALIBRATION-101` | II | 2932 | 7.1 Threshold-sharing granularity and cluster stability | How much calibration granularity is required? | `NOT_AUDITED` | — |
| `CALIBRATION-102` | II | 2933 | 7.1 Threshold-sharing granularity and cluster stability | Are CLUSTER_THRESHOLD client assignments stable across seeds and calibration samples? | `NOT_AUDITED` | — |
| `THRESHOLD-157` | II | 2934 | 7.1 Threshold-sharing granularity and cluster stability | Does cluster sharing provide a defensible middle ground between one global threshold and one threshold per client? | `NOT_AUDITED` | — |
| `THRESHOLD-158` | II | 2938 | 7.1 Threshold-sharing granularity and cluster stability | NBAIOT_NATURAL_DEVICES is mandatory; | `NOT_AUDITED` | — |
| `THRESHOLD-159` | II | 2939 | 7.1 Threshold-sharing granularity and cluster stability | EDGE_SENSOR_CLIENTS may include CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-160` | II | 2940 | 7.1 Threshold-sharing granularity and cluster stability | FAMILY_THRESHOLD remains NBAIOT_NATURAL_DEVICES only. | `NOT_AUDITED` | — |
| `THRESHOLD-161` | II | 2944 | 7.1 Threshold-sharing granularity and cluster stability | SHARED_THRESHOLD shared; | `NOT_AUDITED` | — |
| `THRESHOLD-162` | II | 2945 | 7.1 Threshold-sharing granularity and cluster stability | FAMILY_THRESHOLD family; | `NOT_AUDITED` | — |
| `THRESHOLD-163` | II | 2946 | 7.1 Threshold-sharing granularity and cluster stability | CLUSTER_THRESHOLD canonical `K = 3`; | `NOT_AUDITED` | — |
| `THRESHOLD-164` | II | 2947 | 7.1 Threshold-sharing granularity and cluster stability | LOCAL_THRESHOLD local; | `NOT_AUDITED` | — |
| `THRESHOLD-165` | II | 2948 | 7.1 Threshold-sharing granularity and cluster stability | exploratory CLUSTER_THRESHOLD cluster counts where mathematically feasible. | `NOT_AUDITED` | — |
| `CALIBRATION-103` | II | 2952 | 7.1 Threshold-sharing granularity and cluster stability | Build each client fingerprint from benign calibration errors only. | `NOT_AUDITED` | — |
| `THRESHOLD-166` | II | 2953 | 7.1 Threshold-sharing granularity and cluster stability | Standardize fingerprint dimensions using the locked rule. | `NOT_AUDITED` | — |
| `THRESHOLD-167` | II | 2954 | 7.1 Threshold-sharing granularity and cluster stability | Fit canonical k-means with locked initialization and seed handling. | `NOT_AUDITED` | — |
| `THRESHOLD-168` | II | 2955 | 7.1 Threshold-sharing granularity and cluster stability | Assign the cluster-level threshold. | `NOT_AUDITED` | — |
| `THRESHOLD-169` | II | 2956 | 7.1 Threshold-sharing granularity and cluster stability | Evaluate FPR equity and detection controls. | `NOT_AUDITED` | — |
| `THRESHOLD-170` | II | 2957 | 7.1 Threshold-sharing granularity and cluster stability | Repeat clustering across seeds and declared resamples. | `NOT_AUDITED` | — |
| `THRESHOLD-171` | II | 2958 | 7.1 Threshold-sharing granularity and cluster stability | compare assignments using adjusted Rand index. | `NOT_AUDITED` | — |
| `THRESHOLD-172` | II | 2959 | 7.1 Threshold-sharing granularity and cluster stability | compute within-cluster and across-cluster threshold and FPR dispersion. | `NOT_AUDITED` | — |
| `THRESHOLD-173` | II | 2960 | 7.1 Threshold-sharing granularity and cluster stability | display the client-to-cluster membership for every seed. | `NOT_AUDITED` | — |
| `THRESHOLD-174` | II | 2961 | 7.1 Threshold-sharing granularity and cluster stability | compare CLUSTER_THRESHOLD groupings against the device-family taxonomy descriptively without treating taxonomy agreement as the optimization target; | `NOT_AUDITED` | — |
| `THRESHOLD-175` | II | 2962 | 7.1 Threshold-sharing granularity and cluster stability | calculate Euclidean silhouette values in the standardized four-feature fingerprint space; | `NOT_AUDITED` | — |
| `THRESHOLD-176` | II | 2963 | 7.1 Threshold-sharing granularity and cluster stability | calculate within-cluster versus between-cluster benign-score JS divergence; | `NOT_AUDITED` | — |
| `THRESHOLD-177` | II | 2964 | 7.1 Threshold-sharing granularity and cluster stability | calculate per-client assignment-switch frequency after label alignment to the smallest training-seed value used in the campaign; | `NOT_AUDITED` | — |
| `THRESHOLD-178` | II | 2965 | 7.1 Threshold-sharing granularity and cluster stability | execute the four locked leave-one-fingerprint-feature-out ablations, each with `K=3` and otherwise identical clustering: | `NOT_AUDITED` | — |
| `THRESHOLD-179` | II | 2966 | 7.1 Threshold-sharing granularity and cluster stability | omit `mean(error)`; | `NOT_AUDITED` | — |
| `THRESHOLD-180` | II | 2967 | 7.1 Threshold-sharing granularity and cluster stability | omit `standard_deviation(error)`; | `NOT_AUDITED` | — |
| `THRESHOLD-181` | II | 2968 | 7.1 Threshold-sharing granularity and cluster stability | omit `skewness(error)`; | `NOT_AUDITED` | — |
| `THRESHOLD-182` | II | 2969 | 7.1 Threshold-sharing granularity and cluster stability | omit `p95(error)`. | `NOT_AUDITED` | — |
| `THRESHOLD-183` | II | 3003 | 7.1 Threshold-sharing granularity and cluster stability | SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD `CV(FPR)`; | `NOT_AUDITED` | — |
| `THRESHOLD-184` | II | 3004 | 7.1 Threshold-sharing granularity and cluster stability | worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-185` | II | 3005 | 7.1 Threshold-sharing granularity and cluster stability | IQR and range; | `NOT_AUDITED` | — |
| `THRESHOLD-186` | II | 3006 | 7.1 Threshold-sharing granularity and cluster stability | FAMILY_THRESHOLD and CLUSTER_THRESHOLD recovery fractions relative to the SHARED_THRESHOLD–LOCAL_THRESHOLD gap; | `NOT_AUDITED` | — |
| `THRESHOLD-187` | II | 3007 | 7.1 Threshold-sharing granularity and cluster stability | within-cluster and across-cluster threshold/FPR dispersion; | `NOT_AUDITED` | — |
| `THRESHOLD-188` | II | 3008 | 7.1 Threshold-sharing granularity and cluster stability | within-cluster and between-cluster benign-score JS divergence; | `NOT_AUDITED` | — |
| `THRESHOLD-189` | II | 3009 | 7.1 Threshold-sharing granularity and cluster stability | mean silhouette and per-client silhouette values; | `NOT_AUDITED` | — |
| `THRESHOLD-190` | II | 3010 | 7.1 Threshold-sharing granularity and cluster stability | ARI across seed pairs or declared resamples; | `NOT_AUDITED` | — |
| `THRESHOLD-191` | II | 3011 | 7.1 Threshold-sharing granularity and cluster stability | complete membership assignments; | `NOT_AUDITED` | — |
| `THRESHOLD-192` | II | 3012 | 7.1 Threshold-sharing granularity and cluster stability | per-client switch frequency; | `NOT_AUDITED` | — |
| `THRESHOLD-193` | II | 3013 | 7.1 Threshold-sharing granularity and cluster stability | cluster sizes; | `NOT_AUDITED` | — |
| `THRESHOLD-194` | II | 3014 | 7.1 Threshold-sharing granularity and cluster stability | empty or singleton cluster diagnostics; | `NOT_AUDITED` | — |
| `THRESHOLD-195` | II | 3015 | 7.1 Threshold-sharing granularity and cluster stability | canonical-versus-leave-one-feature-out ARI, silhouette, `CV(FPR)`, and worst-client FPR for all four ablations; | `NOT_AUDITED` | — |
| `THRESHOLD-196` | II | 3016 | 7.1 Threshold-sharing granularity and cluster stability | detection-quality controls for NBAIOT_NATURAL_DEVICES. | `NOT_AUDITED` | — |
| `GLOBAL-064` | II | 3088 | 7.3 Per-client score-distribution explanation | plot held-out benign reconstruction-error CDFs; | `NOT_AUDITED` | — |
| `GLOBAL-065` | II | 3089 | 7.3 Per-client score-distribution explanation | plot held-out attack reconstruction-error CDFs; | `NOT_AUDITED` | — |
| `THRESHOLD-197` | II | 3090 | 7.3 Per-client score-distribution explanation | overlay SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD thresholds; | `NOT_AUDITED` | — |
| `THRESHOLD-198` | II | 3091 | 7.3 Per-client score-distribution explanation | show each threshold’s benign exceedance and attack acceptance region; | `NOT_AUDITED` | — |
| `GLOBAL-066` | II | 3092 | 7.3 Per-client score-distribution explanation | identify clients with weak score separation; | `NOT_AUDITED` | — |
| `GLOBAL-067` | II | 3093 | 7.3 Per-client score-distribution explanation | include the pre-specified Ennio Doorbell deep dive; | `NOT_AUDITED` | — |
| `GLOBAL-068` | II | 3094 | 7.3 Per-client score-distribution explanation | retain all clients in supplementary panels. | `NOT_AUDITED` | — |
| `REPORT-028` | II | 3098 | 7.3 Per-client score-distribution explanation | one complete multi-client CDF figure; | `NOT_AUDITED` | — |
| `GLOBAL-069` | II | 3099 | 7.3 Per-client score-distribution explanation | one detailed Ennio Doorbell panel; | `NOT_AUDITED` | — |
| `THRESHOLD-199` | II | 3100 | 7.3 Per-client score-distribution explanation | per-client threshold positions; | `NOT_AUDITED` | — |
| `METRIC-014` | II | 3101 | 7.3 Per-client score-distribution explanation | per-client FPR, TPR, balanced accuracy, and Macro-F1; | `NOT_AUDITED` | — |
| `THRESHOLD-200` | II | 3102 | 7.3 Per-client score-distribution explanation | explanation of threshold movement without claiming causality beyond the plotted score geometry. | `NOT_AUDITED` | — |
| `CALIBRATION-104` | II | 3148 | 7.4 Heterogeneity–benefit association and decision surface | calculate `H` from benign calibration scores only; | `NOT_AUDITED` | — |
| `THRESHOLD-201` | II | 3149 | 7.4 Heterogeneity–benefit association and decision surface | calculate the SHARED_THRESHOLD–LOCAL_THRESHOLD FPR-equity gain \(\Delta CV=CV(FPR)_{\mathrm{shared}}-CV(FPR)_{\mathrm{local}}\); | `NOT_AUDITED` | — |
| `GLOBAL-070` | II | 3150 | 7.4 Heterogeneity–benefit association and decision surface | plot both; | `NOT_AUDITED` | — |
| `REPORT-029` | II | 3151 | 7.4 Heterogeneity–benefit association and decision surface | report Spearman correlation; | `NOT_AUDITED` | — |
| `DATASET-057` | II | 3152 | 7.4 Heterogeneity–benefit association and decision surface | report all points, not only population means; | `NOT_AUDITED` | — |
| `GLOBAL-071` | II | 3153 | 7.4 Heterogeneity–benefit association and decision surface | include leverage/influence diagnostics. | `NOT_AUDITED` | — |
| `CALIBRATION-105` | II | 3161 | 7.4 Heterogeneity–benefit association and decision surface | remove device `j` from the eligible calibration/evaluation population only; | `NOT_AUDITED` | — |
| `PREPROCESS-036` | II | 3162 | 7.4 Heterogeneity–benefit association and decision surface | do **not** retrain the detector, refit preprocessing, or regenerate scores; | `NOT_AUDITED` | — |
| `CALIBRATION-106` | II | 3163 | 7.4 Heterogeneity–benefit association and decision surface | rebuild the common 64-bin JSD grid from the pooled benign calibration scores of the remaining clients using the same quantile-edge rule above; | `NOT_AUDITED` | — |
| `GLOBAL-072` | II | 3164 | 7.4 Heterogeneity–benefit association and decision surface | recompute `H_(s,-j)` on the remaining clients; | `NOT_AUDITED` | — |
| `THRESHOLD-202` | II | 3165 | 7.4 Heterogeneity–benefit association and decision surface | recompute the shared threshold from the remaining eligible clients and recompute `CV(FPR)_shared,(s,-j)` over those clients; | `NOT_AUDITED` | — |
| `THRESHOLD-203` | II | 3166 | 7.4 Heterogeneity–benefit association and decision surface | retain each remaining client's original local threshold and recompute `CV(FPR)_local,(s,-j)` over the same reduced client set; | `NOT_AUDITED` | — |
| `GLOBAL-073` | II | 3167 | 7.4 Heterogeneity–benefit association and decision surface | compute | `NOT_AUDITED` | — |
| `THRESHOLD-204` | II | 3272 | 7.5 Threshold movement versus operating-point harm | threshold shift versus FPR change; | `NOT_AUDITED` | — |
| `THRESHOLD-205` | II | 3273 | 7.5 Threshold movement versus operating-point harm | threshold shift versus TPR change; | `NOT_AUDITED` | — |
| `THRESHOLD-206` | II | 3274 | 7.5 Threshold movement versus operating-point harm | device labels; | `NOT_AUDITED` | — |
| `THRESHOLD-207` | II | 3275 | 7.5 Threshold movement versus operating-point harm | seed uncertainty; | `NOT_AUDITED` | — |
| `THRESHOLD-208` | II | 3276 | 7.5 Threshold movement versus operating-point harm | all nine clients without filtering. | `NOT_AUDITED` | — |
| `CALIBRATION-107` | II | 3356 | 7.5A Calibration support versus shared-threshold burden | all client `n_k_source` values; | `NOT_AUDITED` | — |
| `CALIBRATION-108` | II | 3357 | 7.5A Calibration support versus shared-threshold burden | a scatter plot with x=`log10(n_k_source)` and y=`FPR_shared` plus a second y=`PersonalizationRelief`; the log transform is visual only and does not change Spearman ranks; | `NOT_AUDITED` | — |
| `CALIBRATION-109` | II | 3358 | 7.5A Calibration support versus shared-threshold burden | the ten seed-level `rho` values for `support -> FPR_shared` and `support -> PersonalizationRelief`; | `NOT_AUDITED` | — |
| `CALIBRATION-110` | II | 3359 | 7.5A Calibration support versus shared-threshold burden | median, minimum, maximum, and counts of negative/zero/positive `rho` values across valid seeds; | `NOT_AUDITED` | — |
| `CALIBRATION-111` | II | 3360 | 7.5A Calibration support versus shared-threshold burden | a per-device table containing `n_k_source`, mean/median SHARED_THRESHOLD FPR across seeds, mean/median `SharedTargetBurden`, and mean/median `PersonalizationRelief`. | `NOT_AUDITED` | — |
| `DATASET-058` | II | 3548 | 7.6 N-BaIoT malware-family sensitivity breakdown | every available `TPR_{k,f}` and `FNR_{k,f}`; | `NOT_AUDITED` | — |
| `DATASET-059` | II | 3549 | 7.6 N-BaIoT malware-family sensitivity breakdown | `MacroFamilyTPR_f` for Mirai and BASHLITE separately; | `NOT_AUDITED` | — |
| `DATASET-060` | II | 3550 | 7.6 N-BaIoT malware-family sensitivity breakdown | `WorstFamilyClientTPR` and the exact `(client,family)` that attains it; | `NOT_AUDITED` | — |
| `THRESHOLD-209` | II | 3551 | 7.6 N-BaIoT malware-family sensitivity breakdown | SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD differences; | `NOT_AUDITED` | — |
| `CALIBRATION-112` | II | 3552 | 7.6 N-BaIoT malware-family sensitivity breakdown | the support count \(N_{k,f}\) for every reported value. | `NOT_AUDITED` | — |
| `CALIBRATION-113` | II | 3642 | 8.1 Calibration-size ablation | every compared threshold policy receives the same client cohort; | `NOT_AUDITED` | — |
| `CALIBRATION-114` | II | 3643 | 8.1 Calibration-size ablation | every compared threshold policy starts from the same source calibration records for that client; | `NOT_AUDITED` | — |
| `CALIBRATION-115` | II | 3644 | 8.1 Calibration-size ablation | deterministic subsampling is policy-independent; | `NOT_AUDITED` | — |
| `CALIBRATION-116` | II | 3645 | 8.1 Calibration-size ablation | eligibility/feasibility cannot vary by threshold policy. | `NOT_AUDITED` | — |
| `CALIBRATION-117` | II | 3657 | 8.1 Calibration-size ablation | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-118` | II | 3658 | 8.1 Calibration-size ablation | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-119` | II | 3659 | 8.1 Calibration-size ablation | CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-120` | II | 3660 | 8.1 Calibration-size ablation | complete fixed-lambda shrinkage curve `{0, 0.25, 0.50, 0.75, 1.00}`; | `NOT_AUDITED` | — |
| `CALIBRATION-121` | II | 3661 | 8.1 Calibration-size ablation | prospectively locked size-aware shrinkage; | `NOT_AUDITED` | — |
| `CALIBRATION-122` | II | 3662 | 8.1 Calibration-size ablation | LOCAL_CONFORMAL_THRESHOLD where its finite-sample rule is valid. | `NOT_AUDITED` | — |
| `CALIBRATION-123` | II | 3668 | 8.1 Calibration-size ablation | verify `(client, m)` feasibility (`n_k_source >= m`); | `NOT_AUDITED` | — |
| `CALIBRATION-124` | II | 3669 | 8.1 Calibration-size ablation | draw `m` benign calibration records without replacement from that client's source pool; | `NOT_AUDITED` | — |
| `CALIBRATION-125` | II | 3670 | 8.1 Calibration-size ablation | compute the declared thresholds; | `NOT_AUDITED` | — |
| `CALIBRATION-126` | II | 3671 | 8.1 Calibration-size ablation | evaluate on the unchanged held-out test set; | `NOT_AUDITED` | — |
| `CALIBRATION-127` | II | 3672 | 8.1 Calibration-size ablation | record threshold variance across subsamples; | `NOT_AUDITED` | — |
| `CALIBRATION-128` | II | 3673 | 8.1 Calibration-size ablation | record held-out FPR target error and the calibration-to-held-out benign generalization gap from Part III §4.8, using the exact subsampled calibration scores that constructed the threshold and the unchanged held-out benign evaluation rows; | `NOT_AUDITED` | — |
| `CALIBRATION-129` | II | 3674 | 8.1 Calibration-size ablation | define each client's full-calibration local threshold \(\tau^{full}_{s,k}\) as the fixed reference and calculate, over the `R=10` nested subsamples, | `NOT_AUDITED` | — |
| `CALIBRATION-130` | II | 3686 | 8.1 Calibration-size ablation | calculate threshold-order inversion against the full-calibration local thresholds. For every comparable client pair `(i,j)` whose full-calibration thresholds are unequal, a replicate is inverted when | `NOT_AUDITED` | — |
| `CALIBRATION-131` | II | 3693 | 8.1 Calibration-size ablation | record the mean absolute LOCAL_THRESHOLD-to-SHARED_THRESHOLD threshold distance | `NOT_AUDITED` | — |
| `CALIBRATION-132` | II | 3700 | 8.1 Calibration-size ablation | record `CV(FPR)`, worst-client FPR, IQR, range, P10 Macro-F1, and balanced accuracy over the fixed-cohort intersection defined above for cross-size comparisons; | `NOT_AUDITED` | — |
| `CALIBRATION-133` | II | 3701 | 8.1 Calibration-size ablation | report clients infeasible at each size, with the reason. | `NOT_AUDITED` | — |
| `CALIBRATION-134` | II | 3737 | 8.1A Calibration cold-start / onboarding boundary | target LOCAL_THRESHOLD is `UNAVAILABLE_NO_LOCAL_CALIBRATION`; | `NOT_AUDITED` | — |
| `CALIBRATION-135` | II | 3738 | 8.1A Calibration cold-start / onboarding boundary | target CLUSTER_THRESHOLD is `UNAVAILABLE_NO_FINGERPRINT`; | `NOT_AUDITED` | — |
| `CALIBRATION-136` | II | 3739 | 8.1A Calibration cold-start / onboarding boundary | leave-target-out SHARED_THRESHOLD is formed from all other eligible clients and applied to the target; | `NOT_AUDITED` | — |
| `CALIBRATION-137` | II | 3740 | 8.1A Calibration cold-start / onboarding boundary | leave-target-out FAMILY_THRESHOLD is formed from other eligible members of the target's locked physical family when at least one exists; | `NOT_AUDITED` | — |
| `CALIBRATION-138` | II | 3741 | 8.1A Calibration cold-start / onboarding boundary | when no other eligible same-family client exists, FAMILY_THRESHOLD explicitly falls back to leave-target-out SHARED_THRESHOLD and records `family_fallback = true`. | `NOT_AUDITED` | — |
| `CALIBRATION-139` | II | 3745 | 8.1A Calibration cold-start / onboarding boundary | the target's `m` benign records are the only target calibration records supplied to SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-140` | II | 3746 | 8.1A Calibration cold-start / onboarding boundary | other clients retain their full calibration support; | `NOT_AUDITED` | — |
| `CALIBRATION-141` | II | 3747 | 8.1A Calibration cold-start / onboarding boundary | CLUSTER_THRESHOLD recomputes the target fingerprint from exactly the `m` target scores and uses the canonical `K=3` construction; if any of `mean`, sample standard deviation, skewness, or p95 is non-finite for that target sample, the CLUSTER_THRESHOLD target result is `UNAVAILABLE_NONFINITE_FINGERPRINT` and no imputation/zero replacement is permitted; | `NOT_AUDITED` | — |
| `CALIBRATION-142` | II | 3748 | 8.1A Calibration cold-start / onboarding boundary | all policies use the same target subsample within a replicate; | `NOT_AUDITED` | — |
| `CALIBRATION-143` | II | 3749 | 8.1A Calibration cold-start / onboarding boundary | the held-out test set remains unchanged. | `NOT_AUDITED` | — |
| `THRESHOLD-210` | II | 3775 | 8.2 Fixed local–global shrinkage | compute the shrinkage threshold for every eligible client; | `NOT_AUDITED` | — |
| `THRESHOLD-211` | II | 3776 | 8.2 Fixed local–global shrinkage | evaluate the full lambda curve; | `NOT_AUDITED` | — |
| `THRESHOLD-212` | II | 3777 | 8.2 Fixed local–global shrinkage | report `CV(FPR)`, worst-client FPR, IQR, range, TPR, P10 Macro-F1, and threshold variance; | `NOT_AUDITED` | — |
| `CALIBRATION-144` | II | 3778 | 8.2 Fixed local–global shrinkage | repeat within the calibration-size grid where planned; | `NOT_AUDITED` | — |
| `THRESHOLD-213` | II | 3779 | 8.2 Fixed local–global shrinkage | do not choose one lambda from the test set and present it as the method. | `NOT_AUDITED` | — |
| `CALIBRATION-145` | II | 3819 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | use only the declared benign calibration scores; | `NOT_AUDITED` | — |
| `CALIBRATION-146` | II | 3820 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | compute the finite-sample conformal quantile at `alpha = 0.05`; | `NOT_AUDITED` | — |
| `CALIBRATION-147` | II | 3821 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | evaluate benign coverage on held-out benign scores; | `NOT_AUDITED` | — |
| `CALIBRATION-148` | II | 3822 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | report coverage error per client and seed; | `NOT_AUDITED` | — |
| `CALIBRATION-149` | II | 3823 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | evaluate attack-sensitive metrics only on held-out attack scores; | `NOT_AUDITED` | — |
| `CALIBRATION-150` | II | 3824 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | compare LOCAL_CONFORMAL_THRESHOLD with LOCAL_THRESHOLD and SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-151` | II | 3825 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | report results at small calibration sizes where rank granularity is material. | `NOT_AUDITED` | — |
| `CALIBRATION-152` | II | 3829 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | target coverage; | `NOT_AUDITED` | — |
| `CALIBRATION-153` | II | 3830 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | achieved marginal benign coverage; | `NOT_AUDITED` | — |
| `CALIBRATION-154` | II | 3831 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | coverage error; | `NOT_AUDITED` | — |
| `CALIBRATION-155` | II | 3832 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | per-client coverage distribution; | `NOT_AUDITED` | — |
| `CALIBRATION-156` | II | 3833 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | `CV(FPR)`; | `NOT_AUDITED` | — |
| `CALIBRATION-157` | II | 3834 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | threshold difference from LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-158` | II | 3835 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | detection-quality controls; | `NOT_AUDITED` | — |
| `CALIBRATION-159` | II | 3836 | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | finite-sample discreteness diagnostics. | `NOT_AUDITED` | — |
| `PREPROCESS-037` | II | 3863 | 8.5 Bounded preprocessing-geometry sensitivity | `CV(FPR)`, IQR, range, worst-client FPR; | `NOT_AUDITED` | — |
| `PREPROCESS-038` | II | 3864 | 8.5 Bounded preprocessing-geometry sensitivity | held-out target-FPR error; | `NOT_AUDITED` | — |
| `PREPROCESS-039` | II | 3865 | 8.5 Bounded preprocessing-geometry sensitivity | AUROC and average precision from that detector's canonical score artifact; | `NOT_AUDITED` | — |
| `PREPROCESS-040` | II | 3866 | 8.5 Bounded preprocessing-geometry sensitivity | mean pairwise benign-score JSD `H`; | `NOT_AUDITED` | — |
| `PREPROCESS-041` | II | 3867 | 8.5 Bounded preprocessing-geometry sensitivity | SHARED_THRESHOLD–LOCAL_THRESHOLD scope gain | `NOT_AUDITED` | — |
| `GLOBAL-074` | II | 4004 | 9.1 Benign summary-statistics comparator | NBAIOT_NATURAL_DEVICES is mandatory; | `NOT_AUDITED` | — |
| `METRIC-015` | II | 4005 | 9.1 Benign summary-statistics comparator | EDGE_SENSOR_CLIENTS is mandatory for benign-FPR outcomes when artifacts are available. | `NOT_AUDITED` | — |
| `THRESHOLD-214` | II | 4009 | 9.1 Benign summary-statistics comparator | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-215` | II | 4010 | 9.1 Benign summary-statistics comparator | exact pooled benign quantile; | `NOT_AUDITED` | — |
| `GLOBAL-075` | II | 4011 | 9.1 Benign summary-statistics comparator | sample-weighted shared construction; | `NOT_AUDITED` | — |
| `THRESHOLD-216` | II | 4012 | 9.1 Benign summary-statistics comparator | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-217` | II | 4013 | 9.1 Benign summary-statistics comparator | `FEDERATED_BENIGN_SUMMARY_THRESHOLD`. | `NOT_AUDITED` | — |
| `GLOBAL-076` | II | 4027 | 9.1 Benign summary-statistics comparator | compute the exact centralized benign reference; | `NOT_AUDITED` | — |
| `CALIBRATION-160` | II | 4028 | 9.1 Benign summary-statistics comparator | compute every distributed construction from the same calibration records; | `NOT_AUDITED` | — |
| `THRESHOLD-218` | II | 4029 | 9.1 Benign summary-statistics comparator | evaluate threshold-estimation error against the centralized reference; | `NOT_AUDITED` | — |
| `GLOBAL-077` | II | 4030 | 9.1 Benign summary-statistics comparator | evaluate achieved benign exceedance; | `NOT_AUDITED` | — |
| `METRIC-016` | II | 4031 | 9.1 Benign summary-statistics comparator | evaluate cross-client FPR dispersion; | `NOT_AUDITED` | — |
| `REPORT-030` | II | 4032 | 9.1 Benign summary-statistics comparator | report communication payload estimates separately from measured network cost; | `NOT_AUDITED` | — |
| `GLOBAL-078` | II | 4033 | 9.1 Benign summary-statistics comparator | calculate the locked between-ratio diagnostic where defined; | `NOT_AUDITED` | — |
| `GLOBAL-079` | II | 4034 | 9.1 Benign summary-statistics comparator | describe precisely which statistics leave each client. | `NOT_AUDITED` | — |
| `THRESHOLD-219` | II | 4038 | 9.1 Benign summary-statistics comparator | threshold value; | `NOT_AUDITED` | — |
| `THRESHOLD-220` | II | 4039 | 9.1 Benign summary-statistics comparator | absolute and relative threshold error; | `NOT_AUDITED` | — |
| `GLOBAL-080` | II | 4040 | 9.1 Benign summary-statistics comparator | target-attainment error; | `NOT_AUDITED` | — |
| `METRIC-017` | II | 4041 | 9.1 Benign summary-statistics comparator | `CV(FPR)`, IQR, range, and worst-client FPR; | `NOT_AUDITED` | — |
| `GLOBAL-081` | II | 4042 | 9.1 Benign summary-statistics comparator | communication fields and estimated bytes; | `NOT_AUDITED` | — |
| `GLOBAL-082` | II | 4043 | 9.1 Benign summary-statistics comparator | client coverage; | `NOT_AUDITED` | — |
| `THRESHOLD-221` | II | 4044 | 9.1 Benign summary-statistics comparator | comparison with SHARED_THRESHOLD and LOCAL_THRESHOLD. | `NOT_AUDITED` | — |
| `THRESHOLD-222` | II | 4050 | 9.1 Benign summary-statistics comparator | improve over SHARED_THRESHOLD but remain weaker than LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-223` | II | 4051 | 9.1 Benign summary-statistics comparator | match LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-224` | II | 4052 | 9.1 Benign summary-statistics comparator | dominate LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-225` | II | 4053 | 9.1 Benign summary-statistics comparator | fail to improve over SHARED_THRESHOLD. | `NOT_AUDITED` | — |
| `THRESHOLD-226` | II | 4069 | 9.2 KLL federated quantile-sketch shared threshold | NBAIOT_NATURAL_DEVICES mandatory; | `NOT_AUDITED` | — |
| `THRESHOLD-227` | II | 4070 | 9.2 KLL federated quantile-sketch shared threshold | EDGE_SENSOR_CLIENTS benign-equity population mandatory when ready. | `NOT_AUDITED` | — |
| `THRESHOLD-228` | II | 4088 | 9.2 KLL federated quantile-sketch shared threshold | exact pooled type-7 quantile oracle; | `NOT_AUDITED` | — |
| `THRESHOLD-229` | II | 4089 | 9.2 KLL federated quantile-sketch shared threshold | SHARED_THRESHOLD arithmetic mean of local quantiles; | `NOT_AUDITED` | — |
| `THRESHOLD-230` | II | 4090 | 9.2 KLL federated quantile-sketch shared threshold | sample-weighted shared construction; | `NOT_AUDITED` | — |
| `THRESHOLD-231` | II | 4091 | 9.2 KLL federated quantile-sketch shared threshold | `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; | `NOT_AUDITED` | — |
| `THRESHOLD-232` | II | 4092 | 9.2 KLL federated quantile-sketch shared threshold | `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`; | `NOT_AUDITED` | — |
| `THRESHOLD-233` | II | 4093 | 9.2 KLL federated quantile-sketch shared threshold | LOCAL_THRESHOLD local. | `NOT_AUDITED` | — |
| `CALIBRATION-161` | II | 4099 | 9.2 KLL federated quantile-sketch shared threshold | use identical eligible calibration-score evidence; | `NOT_AUDITED` | — |
| `THRESHOLD-234` | II | 4100 | 9.2 KLL federated quantile-sketch shared threshold | serialize each client sketch and record actual byte length; | `NOT_AUDITED` | — |
| `THRESHOLD-235` | II | 4101 | 9.2 KLL federated quantile-sketch shared threshold | merge client sketches at the server; | `NOT_AUDITED` | — |
| `THRESHOLD-236` | II | 4102 | 9.2 KLL federated quantile-sketch shared threshold | obtain \(\tau_{KLL}\) at q=0.95; | `NOT_AUDITED` | — |
| `THRESHOLD-237` | II | 4103 | 9.2 KLL federated quantile-sketch shared threshold | calculate `EmpiricalRankError = \|F_pool(tau_KLL)-0.95\|`; | `NOT_AUDITED` | — |
| `THRESHOLD-238` | II | 4104 | 9.2 KLL federated quantile-sketch shared threshold | calculate absolute and relative threshold error versus the exact pooled type-7 oracle; | `NOT_AUDITED` | — |
| `THRESHOLD-239` | II | 4105 | 9.2 KLL federated quantile-sketch shared threshold | calculate held-out benign signed/absolute target error; | `NOT_AUDITED` | — |
| `THRESHOLD-240` | II | 4106 | 9.2 KLL federated quantile-sketch shared threshold | calculate `CV(FPR)`, IQR, range, worst-client FPR, and attack-sensitive controls where valid; | `NOT_AUDITED` | — |
| `THRESHOLD-241` | II | 4107 | 9.2 KLL federated quantile-sketch shared threshold | record client build time, server merge/query time, upload bytes/client, total upload bytes, and download threshold bytes; | `NOT_AUDITED` | — |
| `THRESHOLD-242` | II | 4108 | 9.2 KLL federated quantile-sketch shared threshold | repeat for `k={200,800}` as sensitivity without selecting a winner. | `NOT_AUDITED` | — |
| `DATASET-061` | II | 4144 | 10.1 Edge-IIoTset external benign-equity validation | EDGE_SENSOR_CLIENTS; | `NOT_AUDITED` | — |
| `DATASET-062` | II | 4145 | 10.1 Edge-IIoTset external benign-equity validation | ten benign sensor-group clients; | `NOT_AUDITED` | — |
| `DATASET-063` | II | 4146 | 10.1 Edge-IIoTset external benign-equity validation | eligible-benign coverage 1.0; | `NOT_AUDITED` | — |
| `TRAIN-034` | II | 4147 | 10.1 Edge-IIoTset external benign-equity validation | ten paired seeds where training is feasible. | `NOT_AUDITED` | — |
| `THRESHOLD-243` | II | 4151 | 10.1 Edge-IIoTset external benign-equity validation | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-244` | II | 4152 | 10.1 Edge-IIoTset external benign-equity validation | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-245` | II | 4153 | 10.1 Edge-IIoTset external benign-equity validation | CLUSTER_THRESHOLD canonical; | `NOT_AUDITED` | — |
| `THRESHOLD-246` | II | 4154 | 10.1 Edge-IIoTset external benign-equity validation | `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; | `NOT_AUDITED` | — |
| `THRESHOLD-247` | II | 4155 | 10.1 Edge-IIoTset external benign-equity validation | quantile sensitivity; | `NOT_AUDITED` | — |
| `CALIBRATION-162` | II | 4156 | 10.1 Edge-IIoTset external benign-equity validation | calibration-size and shrinkage analyses where supported. | `NOT_AUDITED` | — |
| `TRAIN-035` | II | 4162 | 10.1 Edge-IIoTset external benign-equity validation | train the FedAvg autoencoder per seed using benign training data; | `NOT_AUDITED` | — |
| `THRESHOLD-248` | II | 4163 | 10.1 Edge-IIoTset external benign-equity validation | construct the allowed thresholds; | `NOT_AUDITED` | — |
| `DATASET-064` | II | 4164 | 10.1 Edge-IIoTset external benign-equity validation | evaluate per-client benign FPR; | `NOT_AUDITED` | — |
| `DATASET-065` | II | 4165 | 10.1 Edge-IIoTset external benign-equity validation | compute cross-client equity metrics; | `NOT_AUDITED` | — |
| `DATASET-066` | II | 4166 | 10.1 Edge-IIoTset external benign-equity validation | represent attack-sensitive per-client metrics as unavailable; | `NOT_AUDITED` | — |
| `THRESHOLD-249` | II | 4167 | 10.1 Edge-IIoTset external benign-equity validation | compare the direction and magnitude of SHARED_THRESHOLD–LOCAL_THRESHOLD with NBAIOT_NATURAL_DEVICES without treating the datasets as exchangeable replications. | `NOT_AUDITED` | — |
| `DATASET-067` | II | 4171 | 10.1 Edge-IIoTset external benign-equity validation | eligible-benign coverage; | `NOT_AUDITED` | — |
| `DATASET-068` | II | 4172 | 10.1 Edge-IIoTset external benign-equity validation | per-client benign sample counts; | `NOT_AUDITED` | — |
| `THRESHOLD-250` | II | 4173 | 10.1 Edge-IIoTset external benign-equity validation | SHARED_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD/`FEDERATED_BENIGN_SUMMARY_THRESHOLD` thresholds; | `NOT_AUDITED` | — |
| `DATASET-069` | II | 4174 | 10.1 Edge-IIoTset external benign-equity validation | per-client FPR; | `NOT_AUDITED` | — |
| `DATASET-070` | II | 4175 | 10.1 Edge-IIoTset external benign-equity validation | `CV(FPR)`, IQR, range, and worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-251` | II | 4176 | 10.1 Edge-IIoTset external benign-equity validation | seed-level SHARED_THRESHOLD–LOCAL_THRESHOLD differences; | `NOT_AUDITED` | — |
| `DATASET-071` | II | 4177 | 10.1 Edge-IIoTset external benign-equity validation | BCa interval as external evidence; | `NOT_AUDITED` | — |
| `DATASET-072` | II | 4178 | 10.1 Edge-IIoTset external benign-equity validation | typed unavailability for attack-sensitive metrics; | `NOT_AUDITED` | — |
| `DATASET-073` | II | 4179 | 10.1 Edge-IIoTset external benign-equity validation | dataset-specific limitations. | `NOT_AUDITED` | — |
| `DATASET-074` | II | 4207 | 10.2 CICIoT2023 file-level boundary | quantify pairwise benign-distribution divergence; | `NOT_AUDITED` | — |
| `THRESHOLD-252` | II | 4208 | 10.2 CICIoT2023 file-level boundary | run SHARED_THRESHOLD and LOCAL_THRESHOLD on the same scores; | `NOT_AUDITED` | — |
| `THRESHOLD-253` | II | 4209 | 10.2 CICIoT2023 file-level boundary | include CLUSTER_THRESHOLD only if cluster sizes are meaningful; | `NOT_AUDITED` | — |
| `DATASET-075` | II | 4210 | 10.2 CICIoT2023 file-level boundary | report `CV(FPR)`, IQR, range, and worst pseudo-client FPR; | `NOT_AUDITED` | — |
| `DATASET-076` | II | 4211 | 10.2 CICIoT2023 file-level boundary | keep all wording specific to the available pseudo-clients. | `NOT_AUDITED` | — |
| `TRAIN-036` | II | 4260 | 11.1 FedProx aggregation stress test | NBAIOT_NATURAL_DEVICES is mandatory; | `NOT_AUDITED` | — |
| `TRAIN-037` | II | 4261 | 11.1 FedProx aggregation stress test | EDGE_SENSOR_CLIENTS benign-equity outcomes are included after EDGE_SENSOR_CLIENTS readiness. | `NOT_AUDITED` | — |
| `TRAIN-038` | II | 4265 | 11.1 FedProx aggregation stress test | FedAvg reference; | `NOT_AUDITED` | — |
| `TRAIN-039` | II | 4266 | 11.1 FedProx aggregation stress test | FedProx with frozen `mu` grid: | `NOT_AUDITED` | — |
| `TRAIN-040` | II | 4267 | 11.1 FedProx aggregation stress test | `0.001`; | `NOT_AUDITED` | — |
| `TRAIN-041` | II | 4268 | 11.1 FedProx aggregation stress test | `0.01`; | `NOT_AUDITED` | — |
| `TRAIN-042` | II | 4269 | 11.1 FedProx aggregation stress test | `0.1`; | `NOT_AUDITED` | — |
| `TRAIN-043` | II | 4270 | 11.1 FedProx aggregation stress test | `1.0`; | `NOT_AUDITED` | — |
| `THRESHOLD-254` | II | 4271 | 11.1 FedProx aggregation stress test | SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD where valid, and CLUSTER_THRESHOLD. | `NOT_AUDITED` | — |
| `TRAIN-044` | II | 4288 | 11.1 FedProx aggregation stress test | train FedProx models independently from FedAvg for every `mu`; | `NOT_AUDITED` | — |
| `TRAIN-045` | II | 4289 | 11.1 FedProx aggregation stress test | train to the same fixed terminal round; | `NOT_AUDITED` | — |
| `TRAIN-046` | II | 4290 | 11.1 FedProx aggregation stress test | persist the complete round-level training-loss trajectory and any convergence/failure state; | `NOT_AUDITED` | — |
| `TRAIN-047` | II | 4291 | 11.1 FedProx aggregation stress test | persist the broadcast-state identity and compute `L2Drift`, `RMSDrift`, and FedProx `TerminalProxPenalty` for every client-round cell exactly as Part I §7.1A specifies; | `NOT_AUDITED` | — |
| `TRAIN-048` | II | 4292 | 11.1 FedProx aggregation stress test | compute `D_all` and `D_terminal50` for FedAvg and every `mu`, plus every client's terminal-50 median drift; | `NOT_AUDITED` | — |
| `TRAIN-049` | II | 4293 | 11.1 FedProx aggregation stress test | compute seed-level `DriftSuppression[s,mu]` where defined; retain negative values rather than clipping them; | `NOT_AUDITED` | — |
| `TRAIN-050` | II | 4294 | 11.1 FedProx aggregation stress test | produce separate score sets; | `NOT_AUDITED` | — |
| `TRAIN-051` | II | 4295 | 11.1 FedProx aggregation stress test | report terminal benign reconstruction-error mean, median, and IQR per client; | `NOT_AUDITED` | — |
| `SCORE-017` | II | 4296 | 11.1 FedProx aggregation stress test | compute AUROC and average precision from each model's canonical score artifact where valid; | `NOT_AUDITED` | — |
| `TRAIN-052` | II | 4297 | 11.1 FedProx aggregation stress test | calculate full-score benign heterogeneity `H` using the locked JSD definition and compute `DeltaH[s,mu]` relative to FedAvg; | `NOT_AUDITED` | — |
| `THRESHOLD-255` | II | 4298 | 11.1 FedProx aggregation stress test | compute every common Part I §7.2B score/threshold-alignment diagnostic and every defined `AlignmentReduction`; | `NOT_AUDITED` | — |
| `THRESHOLD-256` | II | 4299 | 11.1 FedProx aggregation stress test | evaluate the complete threshold ladder on each trained model; | `NOT_AUDITED` | — |
| `TRAIN-053` | II | 4300 | 11.1 FedProx aggregation stress test | calculate `DeltaScope[s,mu]` and `ScopeAbsorption[s,mu]` relative to FedAvg when the FedAvg denominator is valid; | `NOT_AUDITED` | — |
| `THRESHOLD-257` | II | 4301 | 11.1 FedProx aggregation stress test | report, for each seed and `mu`, the tuple `(DriftSuppression, DeltaH, H, LocationDispersion, ScaleDispersion, LocalThresholdDispersion, NormalizedSharedLocalThresholdDistance, DeltaScope, ScopeAbsorption)` so a null absorption result can be distinguished from a FedProx condition that barely changed update/score geometry; | `NOT_AUDITED` | — |
| `THRESHOLD-258` | II | 4302 | 11.1 FedProx aggregation stress test | report SHARED_THRESHOLD and LOCAL_THRESHOLD threshold distributions across clients; | `NOT_AUDITED` | — |
| `TRAIN-054` | II | 4303 | 11.1 FedProx aggregation stress test | report training failure or instability without changing the grid retroactively. | `NOT_AUDITED` | — |
| `THRESHOLD-259` | II | 4309 | 11.1 FedProx aggregation stress test | retained threshold-scope effect with observed drift suppression; | `NOT_AUDITED` | — |
| `THRESHOLD-260` | II | 4310 | 11.1 FedProx aggregation stress test | retained threshold-scope effect with little/no observed drift suppression; | `NOT_AUDITED` | — |
| `TRAIN-055` | II | 4311 | 11.1 FedProx aggregation stress test | partial absorption; | `NOT_AUDITED` | — |
| `TRAIN-056` | II | 4312 | 11.1 FedProx aggregation stress test | full absorption; | `NOT_AUDITED` | — |
| `TRAIN-057` | II | 4313 | 11.1 FedProx aggregation stress test | opposite effect; | `NOT_AUDITED` | — |
| `TRAIN-058` | II | 4314 | 11.1 FedProx aggregation stress test | FedProx non-convergence or instability. | `NOT_AUDITED` | — |
| `TRAIN-059` | II | 4338 | 11.2 Ditto model-personalization stress test | NBAIOT_NATURAL_DEVICES is mandatory; | `NOT_AUDITED` | — |
| `TRAIN-060` | II | 4339 | 11.2 Ditto model-personalization stress test | EDGE_SENSOR_CLIENTS is included for benign-equity outcomes after readiness. | `NOT_AUDITED` | — |
| `THRESHOLD-261` | II | 4345 | 11.2 Ditto model-personalization stress test | FedAvg model with SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-262` | II | 4346 | 11.2 Ditto model-personalization stress test | FedAvg model with LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-263` | II | 4347 | 11.2 Ditto model-personalization stress test | canonical Ditto personalized model (`lambda_D = 1.0`) with SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-264` | II | 4348 | 11.2 Ditto model-personalization stress test | canonical Ditto personalized model (`lambda_D = 1.0`) with LOCAL_THRESHOLD. | `NOT_AUDITED` | — |
| `TRAIN-061` | II | 4374 | 11.2 Ditto model-personalization stress test | train genuine Ditto global and persistent personalized states for each locked λ; | `NOT_AUDITED` | — |
| `TRAIN-062` | II | 4375 | 11.2 Ditto model-personalization stress test | keep personalized states separate by client and never aggregate them; | `NOT_AUDITED` | — |
| `TRAIN-063` | II | 4376 | 11.2 Ditto model-personalization stress test | use the same optimizer, learning-rate, batch, round, and local-epoch semantics as the reference unless Ditto's proximal update explicitly changes the objective term; | `NOT_AUDITED` | — |
| `TRAIN-064` | II | 4377 | 11.2 Ditto model-personalization stress test | generate personalized scores separately from all FedAvg artifacts; | `NOT_AUDITED` | — |
| `THRESHOLD-265` | II | 4378 | 11.2 Ditto model-personalization stress test | compute SHARED_THRESHOLD and LOCAL_THRESHOLD from the corresponding personalized score distributions; | `NOT_AUDITED` | — |
| `THRESHOLD-266` | II | 4379 | 11.2 Ditto model-personalization stress test | calculate the threshold-scope gain under FedAvg and canonical Ditto; | `NOT_AUDITED` | — |
| `THRESHOLD-267` | II | 4380 | 11.2 Ditto model-personalization stress test | compute every common Part I §7.2B score/threshold-alignment diagnostic and available `AlignmentReduction` for canonical Ditto and each sensitivity λ; | `NOT_AUDITED` | — |
| `SCORE-018` | II | 4381 | 11.2 Ditto model-personalization stress test | compute AUROC/AP, `CV(FPR)`, worst-client FPR, P10 Macro-F1, and held-out target error; | `NOT_AUDITED` | — |
| `THRESHOLD-268` | II | 4382 | 11.2 Ditto model-personalization stress test | measure persistent personalized-model serialized bytes per client, extra local training wall time relative to FedAvg, and total threshold-stage payload; model-update communication remains separately accounted from local personalized-state storage; | `NOT_AUDITED` | — |
| `TRAIN-065` | II | 4383 | 11.2 Ditto model-personalization stress test | preserve all four canonical corners and all sensitivity λ outcomes. | `NOT_AUDITED` | — |
| `THRESHOLD-269` | II | 4416 | 11.2 Ditto model-personalization stress test | `AbsorptionFraction <= 0.25` (equivalently `Delta_Ditto >= 0.75 * Delta_FedAvg`): threshold personalization remains strongly useful; | `NOT_AUDITED` | — |
| `TRAIN-066` | II | 4417 | 11.2 Ditto model-personalization stress test | `0.25 < AbsorptionFraction <= 0.75`: partial absorption; | `NOT_AUDITED` | — |
| `TRAIN-067` | II | 4418 | 11.2 Ditto model-personalization stress test | `0.75 < AbsorptionFraction <= 1.0`: largely absorbed; | `NOT_AUDITED` | — |
| `TRAIN-068` | II | 4419 | 11.2 Ditto model-personalization stress test | `AbsorptionFraction > 1.0`: reversed shared/local ordering under Ditto; | `NOT_AUDITED` | — |
| `THRESHOLD-270` | II | 4420 | 11.2 Ditto model-personalization stress test | if `CV(FPR)[Ditto+SHARED_THRESHOLD]` is within absolute `0.05` of `CV(FPR)[FedAvg+LOCAL_THRESHOLD]`, model personalization is reported as an alternative route to operating-point equity. | `NOT_AUDITED` | — |
| `TRAIN-069` | II | 4446 | 11.2A FedAvg post-training client-local fine-tuning stress test | `NBAIOT_NATURAL_DEVICES` is mandatory; | `NOT_AUDITED` | — |
| `CALIBRATION-163` | II | 4447 | 11.2A FedAvg post-training client-local fine-tuning stress test | `EDGE_SENSOR_CLIENTS` benign-equity outcomes are included after readiness if the same benign-train/calibration/evaluation separation can be preserved. | `NOT_AUDITED` | — |
| `THRESHOLD-271` | II | 4451 | 11.2A FedAvg post-training client-local fine-tuning stress test | FedAvg + SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-272` | II | 4452 | 11.2A FedAvg post-training client-local fine-tuning stress test | FedAvg + LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-273` | II | 4453 | 11.2A FedAvg post-training client-local fine-tuning stress test | `FEDAVG_LOCAL_FINE_TUNING` + SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `THRESHOLD-274` | II | 4454 | 11.2A FedAvg post-training client-local fine-tuning stress test | `FEDAVG_LOCAL_FINE_TUNING` + LOCAL_THRESHOLD. | `NOT_AUDITED` | — |
| `TRAIN-070` | II | 4460 | 11.2A FedAvg post-training client-local fine-tuning stress test | load the exact seed-matched FedAvg terminal scientific detector at round `200`; | `NOT_AUDITED` | — |
| `TRAIN-071` | II | 4461 | 11.2A FedAvg post-training client-local fine-tuning stress test | for every client, initialize a local copy from those exact weights; | `NOT_AUDITED` | — |
| `TRAIN-072` | II | 4462 | 11.2A FedAvg post-training client-local fine-tuning stress test | instantiate a fresh optimizer and fine-tune for exactly `10` complete epochs on that client's benign **training** partition only; | `NOT_AUDITED` | — |
| `CALIBRATION-164` | II | 4463 | 11.2A FedAvg post-training client-local fine-tuning stress test | freeze the end-of-epoch-10 client model; no early stopping, validation selection, calibration selection, or aggregation occurs; | `NOT_AUDITED` | — |
| `SCORE-019` | II | 4464 | 11.2A FedAvg post-training client-local fine-tuning stress test | generate one immutable client-specific calibration score artifact and one immutable client-specific evaluation score artifact; | `NOT_AUDITED` | — |
| `SCORE-020` | II | 4465 | 11.2A FedAvg post-training client-local fine-tuning stress test | compute SHARED_THRESHOLD and LOCAL_THRESHOLD from those frozen fine-tuned score artifacts; | `NOT_AUDITED` | — |
| `SCORE-021` | II | 4466 | 11.2A FedAvg post-training client-local fine-tuning stress test | compute AUROC/AP, FPR, `CV(FPR)`, absolute FPR dispersion, TPR, Macro-F1, balanced accuracy, P10 Macro-F1, worst-client BA, held-out target error, and calibration-generalization-gap metrics wherever valid; | `NOT_AUDITED` | — |
| `TRAIN-073` | II | 4467 | 11.2A FedAvg post-training client-local fine-tuning stress test | compute the complete common Part I §7.2B mechanism tuple and every available `AlignmentReduction`; | `NOT_AUDITED` | — |
| `TRAIN-074` | II | 4468 | 11.2A FedAvg post-training client-local fine-tuning stress test | define | `NOT_AUDITED` | — |
| `TRAIN-075` | II | 4482 | 11.2A FedAvg post-training client-local fine-tuning stress test | retain the value un-clipped and use the same literal interpretation as the generic Part I §7.2B definition: `<0` amplification, `0` no absorption, `(0,1)` partial absorption, `1` zero residual shared/local gain, and `>1` reversal; | `NOT_AUDITED` | — |
| `TRAIN-076` | II | 4483 | 11.2A FedAvg post-training client-local fine-tuning stress test | report per-client serialized fine-tuned-model bytes and **fine-tuning wall time** measured on the same execution machine as the FedAvg reference; post-training local fine-tuning adds no model-update communication round, so communication is reported as `0 additional federated rounds` rather than converted into a speculative network latency; | `NOT_AUDITED` | — |
| `TRAIN-077` | II | 4484 | 11.2A FedAvg post-training client-local fine-tuning stress test | report all ten training seeds. No “best fine-tuning seed” or alternate epoch count may be substituted. | `NOT_AUDITED` | — |
| `CALIBRATION-165` | II | 4516 | 12.1 One-shot recalibration under genuine chronology | EDGE_TEMPORAL_CLIENTS; | `NOT_AUDITED` | — |
| `CALIBRATION-166` | II | 4517 | 12.1 One-shot recalibration under genuine chronology | nine verified temporal groups; | `NOT_AUDITED` | — |
| `CALIBRATION-167` | II | 4518 | 12.1 One-shot recalibration under genuine chronology | Modbus excluded; | `NOT_AUDITED` | — |
| `CALIBRATION-168` | II | 4519 | 12.1 One-shot recalibration under genuine chronology | ten paired seeds where feasible. | `NOT_AUDITED` | — |
| `CALIBRATION-169` | II | 4534 | 12.1 One-shot recalibration under genuine chronology | SHARED_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-170` | II | 4535 | 12.1 One-shot recalibration under genuine chronology | LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-171` | II | 4536 | 12.1 One-shot recalibration under genuine chronology | CLUSTER_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-172` | II | 4537 | 12.1 One-shot recalibration under genuine chronology | shrinkage where pre-specified. | `NOT_AUDITED` | — |
| `CALIBRATION-173` | II | 4541 | 12.1 One-shot recalibration under genuine chronology | verify timestamps for every included client; | `NOT_AUDITED` | — |
| `CALIBRATION-174` | II | 4542 | 12.1 One-shot recalibration under genuine chronology | apply stable chronological ordering; | `NOT_AUDITED` | — |
| `CALIBRATION-175` | II | 4543 | 12.1 One-shot recalibration under genuine chronology | construct the 55/15/10/20 split; | `NOT_AUDITED` | — |
| `PREPROCESS-042` | II | 4544 | 12.1 One-shot recalibration under genuine chronology | fit preprocessing and the autoencoder without future leakage; | `NOT_AUDITED` | — |
| `CALIBRATION-176` | II | 4545 | 12.1 One-shot recalibration under genuine chronology | construct historical thresholds; | `NOT_AUDITED` | — |
| `CALIBRATION-177` | II | 4546 | 12.1 One-shot recalibration under genuine chronology | evaluate frozen thresholds on future evaluation; | `NOT_AUDITED` | — |
| `CALIBRATION-178` | II | 4547 | 12.1 One-shot recalibration under genuine chronology | recompute thresholds from future recalibration only; | `NOT_AUDITED` | — |
| `CALIBRATION-179` | II | 4548 | 12.1 One-shot recalibration under genuine chronology | evaluate recalibrated thresholds on the same future evaluation; | `NOT_AUDITED` | — |
| `CALIBRATION-180` | II | 4549 | 12.1 One-shot recalibration under genuine chronology | construct the matched static reference; | `NOT_AUDITED` | — |
| `CALIBRATION-181` | II | 4550 | 12.1 One-shot recalibration under genuine chronology | calculate: | `NOT_AUDITED` | — |
| `CALIBRATION-182` | II | 4615 | 12.1 One-shot recalibration under genuine chronology | chronology-validation record; | `NOT_AUDITED` | — |
| `CALIBRATION-183` | II | 4616 | 12.1 One-shot recalibration under genuine chronology | included and excluded clients; | `NOT_AUDITED` | — |
| `CALIBRATION-184` | II | 4617 | 12.1 One-shot recalibration under genuine chronology | static-reference CV; | `NOT_AUDITED` | — |
| `CALIBRATION-185` | II | 4618 | 12.1 One-shot recalibration under genuine chronology | frozen-future CV; | `NOT_AUDITED` | — |
| `CALIBRATION-186` | II | 4619 | 12.1 One-shot recalibration under genuine chronology | recalibrated-future CV; | `NOT_AUDITED` | — |
| `CALIBRATION-187` | II | 4620 | 12.1 One-shot recalibration under genuine chronology | drift excess; | `NOT_AUDITED` | — |
| `CALIBRATION-188` | II | 4621 | 12.1 One-shot recalibration under genuine chronology | recovered amount; | `NOT_AUDITED` | — |
| `CALIBRATION-189` | II | 4622 | 12.1 One-shot recalibration under genuine chronology | recovery ratio when defined; | `NOT_AUDITED` | — |
| `CALIBRATION-190` | II | 4623 | 12.1 One-shot recalibration under genuine chronology | per-client FPR trajectories; | `NOT_AUDITED` | — |
| `CALIBRATION-191` | II | 4624 | 12.1 One-shot recalibration under genuine chronology | per-client threshold movements `Delta tau_k`; | `NOT_AUDITED` | — |
| `CALIBRATION-192` | II | 4625 | 12.1 One-shot recalibration under genuine chronology | per-client `DriftJS_k`; | `NOT_AUDITED` | — |
| `CALIBRATION-193` | II | 4626 | 12.1 One-shot recalibration under genuine chronology | per-client frozen deterioration and recovery; | `NOT_AUDITED` | — |
| `CALIBRATION-194` | II | 4627 | 12.1 One-shot recalibration under genuine chronology | helped/harmed/unchanged fractions; | `NOT_AUDITED` | — |
| `CALIBRATION-195` | II | 4628 | 12.1 One-shot recalibration under genuine chronology | worst-client FPR recovery; | `NOT_AUDITED` | — |
| `CALIBRATION-196` | II | 4629 | 12.1 One-shot recalibration under genuine chronology | drift-JS versus FPR-deterioration Spearman summary where available; | `NOT_AUDITED` | — |
| `CALIBRATION-197` | II | 4630 | 12.1 One-shot recalibration under genuine chronology | paired seed uncertainty. | `NOT_AUDITED` | — |
| `REPORT-031` | II | 4681 | 13.1 Alert-burden experiment | report the rate source; | `NOT_AUDITED` | — |
| `DATASET-077` | II | 4682 | 13.1 Alert-burden experiment | report whether the rate is measured, dataset-derived, or externally cited; | `NOT_AUDITED` | — |
| `GLOBAL-083` | II | 4683 | 13.1 Alert-burden experiment | propagate rate assumptions separately from model uncertainty; | `NOT_AUDITED` | — |
| `GLOBAL-084` | II | 4684 | 13.1 Alert-burden experiment | show per-device burden, not only a pooled total; | `NOT_AUDITED` | — |
| `THRESHOLD-275` | II | 4685 | 13.1 Alert-burden experiment | use SHARED_THRESHOLD and LOCAL_THRESHOLD at minimum; | `NOT_AUDITED` | — |
| `GLOBAL-085` | II | 4686 | 13.1 Alert-burden experiment | label estimates as estimated when no deployment measurement exists. | `NOT_AUDITED` | — |
| `THRESHOLD-276` | II | 4748 | 14.1 Robust cluster-median threshold | cluster assignments unchanged; | `NOT_AUDITED` | — |
| `THRESHOLD-277` | II | 4749 | 14.1 Robust cluster-median threshold | cluster threshold difference; | `NOT_AUDITED` | — |
| `THRESHOLD-278` | II | 4750 | 14.1 Robust cluster-median threshold | `CV(FPR)`; | `NOT_AUDITED` | — |
| `THRESHOLD-279` | II | 4751 | 14.1 Robust cluster-median threshold | worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-280` | II | 4752 | 14.1 Robust cluster-median threshold | outlier-client influence. | `NOT_AUDITED` | — |
| `METRIC-018` | II | 4760 | 14.2 Additional equity indices | Jain index; | `NOT_AUDITED` | — |
| `METRIC-019` | II | 4761 | 14.2 Additional equity indices | Gini coefficient; | `NOT_AUDITED` | — |
| `GLOBAL-086` | II | 4762 | 14.2 Additional equity indices | IQR; | `NOT_AUDITED` | — |
| `GLOBAL-087` | II | 4763 | 14.2 Additional equity indices | max–min range; | `NOT_AUDITED` | — |
| `GLOBAL-088` | II | 4764 | 14.2 Additional equity indices | within-cluster dispersion; | `NOT_AUDITED` | — |
| `GLOBAL-089` | II | 4765 | 14.2 Additional equity indices | across-cluster dispersion. | `NOT_AUDITED` | — |
| `METRIC-020` | II | 4773 | 14.3 Extended secondary uncertainty | bootstrap intervals for secondary paired metrics; | `NOT_AUDITED` | — |
| `STAT-010` | II | 4774 | 14.3 Extended secondary uncertainty | Wilcoxon signed-rank; | `NOT_AUDITED` | — |
| `STAT-011` | II | 4775 | 14.3 Extended secondary uncertainty | matched-pairs rank-biserial correlation; | `NOT_AUDITED` | — |
| `GLOBAL-090` | II | 4776 | 14.3 Extended secondary uncertainty | exact sign summaries where useful. | `NOT_AUDITED` | — |
| `GLOBAL-091` | III | 4823 | 2. Prediction and confusion counts | \(TN_k\): benign predicted benign; | `NOT_AUDITED` | — |
| `GLOBAL-092` | III | 4824 | 2. Prediction and confusion counts | \(FP_k\): benign predicted attack; | `NOT_AUDITED` | — |
| `GLOBAL-093` | III | 4825 | 2. Prediction and confusion counts | \(TP_k\): attack predicted attack; | `NOT_AUDITED` | — |
| `GLOBAL-094` | III | 4826 | 2. Prediction and confusion counts | \(FN_k\): attack predicted benign. | `NOT_AUDITED` | — |
| `DATASET-078` | III | 4850 | 3.3 Attack-evaluable population | valid per-client attack assignment; | `NOT_AUDITED` | — |
| `DATASET-079` | III | 4851 | 3.3 Attack-evaluable population | at least one held-out attack row; | `NOT_AUDITED` | — |
| `DATASET-080` | III | 4852 | 3.3 Attack-evaluable population | both semantic classes where required. | `NOT_AUDITED` | — |
| `CALIBRATION-198` | III | 5061 | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `CalibrationExceedance`; | `NOT_AUDITED` | — |
| `CALIBRATION-199` | III | 5062 | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `CalibrationTargetError`; | `NOT_AUDITED` | — |
| `METRIC-021` | III | 5063 | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `SignedTestFPRTargetError`; | `NOT_AUDITED` | — |
| `METRIC-022` | III | 5064 | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `AbsoluteTestFPRTargetError`; | `NOT_AUDITED` | — |
| `CALIBRATION-200` | III | 5065 | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `CalibrationGeneralizationGap`. | `NOT_AUDITED` | — |
| `GLOBAL-095` | III | 5216 | 6.3 Cluster dispersion | cluster size; | `NOT_AUDITED` | — |
| `THRESHOLD-281` | III | 5217 | 6.3 Cluster dispersion | within-cluster threshold spread; | `NOT_AUDITED` | — |
| `METRIC-023` | III | 5218 | 6.3 Cluster dispersion | within-cluster FPR spread; | `NOT_AUDITED` | — |
| `THRESHOLD-282` | III | 5219 | 6.3 Cluster dispersion | across-cluster threshold spread; | `NOT_AUDITED` | — |
| `METRIC-024` | III | 5220 | 6.3 Cluster dispersion | across-cluster mean-FPR spread; | `NOT_AUDITED` | — |
| `GLOBAL-096` | III | 5221 | 6.3 Cluster dispersion | singleton and empty-cluster status. | `NOT_AUDITED` | — |
| `METRIC-025` | III | 5273 | 7.2 Pooled Macro-F1 | mean client Macro-F1; | `NOT_AUDITED` | — |
| `METRIC-026` | III | 5274 | 7.2 Pooled Macro-F1 | P10 Macro-F1; | `NOT_AUDITED` | — |
| `METRIC-027` | III | 5275 | 7.2 Pooled Macro-F1 | worst-client balanced accuracy. | `NOT_AUDITED` | — |
| `THRESHOLD-283` | III | 5361 | 8.4 Threshold variance and sample efficiency | threshold variance across the 10 nested replicates; | `NOT_AUDITED` | — |
| `CALIBRATION-201` | III | 5362 | 8.4 Threshold variance and sample efficiency | threshold bias versus the full-calibration threshold; | `NOT_AUDITED` | — |
| `CALIBRATION-202` | III | 5363 | 8.4 Threshold variance and sample efficiency | threshold RMSE versus the full-calibration threshold; | `NOT_AUDITED` | — |
| `THRESHOLD-284` | III | 5364 | 8.4 Threshold variance and sample efficiency | threshold-order inversion rate and tie rate; | `NOT_AUDITED` | — |
| `THRESHOLD-285` | III | 5365 | 8.4 Threshold variance and sample efficiency | mean local-to-shared threshold distance; | `NOT_AUDITED` | — |
| `THRESHOLD-286` | III | 5366 | 8.4 Threshold variance and sample efficiency | held-out signed/absolute target-FPR error; | `NOT_AUDITED` | — |
| `THRESHOLD-287` | III | 5367 | 8.4 Threshold variance and sample efficiency | `CV(FPR)`; | `NOT_AUDITED` | — |
| `THRESHOLD-288` | III | 5368 | 8.4 Threshold variance and sample efficiency | worst-client FPR; | `NOT_AUDITED` | — |
| `THRESHOLD-289` | III | 5369 | 8.4 Threshold variance and sample efficiency | P10 Macro-F1 where available. | `NOT_AUDITED` | — |
| `THRESHOLD-290` | III | 5381 | 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics | count \(n_k\); | `NOT_AUDITED` | — |
| `THRESHOLD-291` | III | 5382 | 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics | mean \(\mu_k\); | `NOT_AUDITED` | — |
| `THRESHOLD-292` | III | 5383 | 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics | variance \(\sigma_k^2\); | `NOT_AUDITED` | — |
| `THRESHOLD-293` | III | 5384 | 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics | permitted benign exceedance counts. | `NOT_AUDITED` | — |
| `THRESHOLD-294` | III | 5462 | 10.2 Threshold-stage communication | logical fields sent per client; | `NOT_AUDITED` | — |
| `THRESHOLD-295` | III | 5463 | 10.2 Threshold-stage communication | actual serialized upload bytes/client; | `NOT_AUDITED` | — |
| `THRESHOLD-296` | III | 5464 | 10.2 Threshold-stage communication | total uploaded bytes across participating clients; | `NOT_AUDITED` | — |
| `THRESHOLD-297` | III | 5465 | 10.2 Threshold-stage communication | actual serialized server response bytes/client and total; | `NOT_AUDITED` | — |
| `THRESHOLD-298` | III | 5466 | 10.2 Threshold-stage communication | whether a broadcast payload is counted once on the wire or once per logical recipient; | `NOT_AUDITED` | — |
| `THRESHOLD-299` | III | 5467 | 10.2 Threshold-stage communication | number of post-training threshold-communication rounds. | `NOT_AUDITED` | — |
| `TRAIN-078` | III | 5479 | 10.4 Ditto incremental state and compute | serialized global-model bytes; | `NOT_AUDITED` | — |
| `TRAIN-079` | III | 5480 | 10.4 Ditto incremental state and compute | serialized persistent personalized-model bytes per client; | `NOT_AUDITED` | — |
| `TRAIN-080` | III | 5481 | 10.4 Ditto incremental state and compute | extra persistent state per client relative to FedAvg; | `NOT_AUDITED` | — |
| `TRAIN-081` | III | 5482 | 10.4 Ditto incremental state and compute | measured local personalized-training wall time per round and total; | `NOT_AUDITED` | — |
| `TRAIN-082` | III | 5483 | 10.4 Ditto incremental state and compute | global-update communication bytes; | `NOT_AUDITED` | — |
| `THRESHOLD-300` | III | 5484 | 10.4 Ditto incremental state and compute | threshold-stage communication bytes. | `NOT_AUDITED` | — |
| `STAT-012` | III | 5550 | 11.3 Degenerate BCa | report the paired values and point estimate; | `NOT_AUDITED` | — |
| `STAT-013` | III | 5551 | 11.3 Degenerate BCa | allow percentile or basic intervals only as diagnostics; | `NOT_AUDITED` | — |
| `STAT-014` | III | 5552 | 11.3 Degenerate BCa | do not silently substitute another interval for the confirmatory rule; | `NOT_AUDITED` | — |
| `CALIBRATION-203` | III | 5553 | 11.3 Degenerate BCa | report the confirmatory claim as **not established**; never silently convert this outcome to `CONFIRMATORY_SUPPORT` or `NO_OBSERVED_ADVANTAGE`, and never rescue it with a secondary result, another statistical test, or supportive/mechanism/external/stress-test evidence. | `NOT_AUDITED` | — |
| `STAT-015` | III | 5603 | 12.1 Wilcoxon signed-rank | two-sided alternative; | `NOT_AUDITED` | — |
| `STAT-016` | III | 5604 | 12.1 Wilcoxon signed-rank | explicit zero-difference handling; | `NOT_AUDITED` | — |
| `STAT-017` | III | 5605 | 12.1 Wilcoxon signed-rank | exact computation when data and implementation permit; | `NOT_AUDITED` | — |
| `STAT-018` | III | 5606 | 12.1 Wilcoxon signed-rank | recorded approximation or permutation method otherwise. | `NOT_AUDITED` | — |
| `STAT-019` | III | 5628 | 12.4 Multiplicity | define test families before analysis; | `NOT_AUDITED` | — |
| `STAT-020` | III | 5629 | 12.4 Multiplicity | report family size; | `NOT_AUDITED` | — |
| `STAT-021` | III | 5630 | 12.4 Multiplicity | apply Holm correction within each family; | `NOT_AUDITED` | — |
| `STAT-022` | III | 5631 | 12.4 Multiplicity | retain raw values only as clearly labeled diagnostics. | `NOT_AUDITED` | — |
| `GLOBAL-097` | III | 5639 | 12.5 Nested replicates | calculate replicate-level values; | `NOT_AUDITED` | — |
| `GLOBAL-098` | III | 5640 | 12.5 Nested replicates | summarize them within seed; | `NOT_AUDITED` | — |
| `GLOBAL-099` | III | 5641 | 12.5 Nested replicates | produce one seed-level estimate per condition; | `NOT_AUDITED` | — |
| `GLOBAL-100` | III | 5642 | 12.5 Nested replicates | perform across-seed inference on those seed-level estimates. | `NOT_AUDITED` | — |
| `GLOBAL-101` | III | 5648 | 12.6 Association analyses | Spearman correlation; | `NOT_AUDITED` | — |
| `GLOBAL-102` | III | 5649 | 12.6 Association analyses | declared regression; | `NOT_AUDITED` | — |
| `GLOBAL-103` | III | 5650 | 12.6 Association analyses | coefficient and uncertainty; | `NOT_AUDITED` | — |
| `GLOBAL-104` | III | 5651 | 12.6 Association analyses | `R²`; | `NOT_AUDITED` | — |
| `GLOBAL-105` | III | 5652 | 12.6 Association analyses | influence diagnostics; | `NOT_AUDITED` | — |
| `GLOBAL-106` | III | 5653 | 12.6 Association analyses | all observations. | `NOT_AUDITED` | — |
| `CALIBRATION-204` | III | 5681 | 14. Temporal recalibration quantities | `static_reference_cv`; | `NOT_AUDITED` | — |
| `CALIBRATION-205` | III | 5682 | 14. Temporal recalibration quantities | `frozen_future_cv`; | `NOT_AUDITED` | — |
| `CALIBRATION-206` | III | 5683 | 14. Temporal recalibration quantities | `recalibrated_future_cv`. | `NOT_AUDITED` | — |
| `THRESHOLD-301` | III | 5789 | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | remove device `j` from both the threshold-construction and equity-evaluation client populations; | `NOT_AUDITED` | — |
| `THRESHOLD-302` | III | 5790 | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | recompute the SHARED_THRESHOLD from the remaining eligible local q95 thresholds; | `NOT_AUDITED` | — |
| `THRESHOLD-303` | III | 5791 | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | retain every remaining client's previously computed LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `METRIC-028` | III | 5792 | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | compute both `CV(FPR)` values on exactly the same remaining client set; | `NOT_AUDITED` | — |
| `GLOBAL-107` | III | 5793 | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | define | `NOT_AUDITED` | — |
| `METRIC-029` | III | 5852 | 15.2 Numerical and selection discipline | rates and aggregate metrics: three decimals; | `NOT_AUDITED` | — |
| `GLOBAL-108` | III | 5853 | 15.2 Numerical and selection discipline | confidence intervals and effect sizes: three decimals; | `NOT_AUDITED` | — |
| `GLOBAL-109` | III | 5854 | 15.2 Numerical and selection discipline | p-values: three significant digits, with `< 0.001` when appropriate; | `NOT_AUDITED` | — |
| `GLOBAL-110` | III | 5855 | 15.2 Numerical and selection discipline | counts: integers; | `NOT_AUDITED` | — |
| `THRESHOLD-304` | III | 5856 | 15.2 Numerical and selection discipline | thresholds: enough digits to reproduce decisions. | `NOT_AUDITED` | — |
| `DATASET-081` | III | 5940 | 16.5 Mandatory synthesis tables | the Part II §4.0 population-capability/claim-boundary table; | `NOT_AUDITED` | — |
| `REPORT-032` | III | 5941 | 16.5 Mandatory synthesis tables | the Part I §10.D.9 prior-art collision table updated through the submission-time novelty gate; | `NOT_AUDITED` | — |
| `THRESHOLD-305` | III | 5942 | 16.5 Mandatory synthesis tables | the shared-threshold robustness panel covering canonical arithmetic-mean shared, exact pooled, sample-weighted shared, `FEDERATED_KLL_SHARED_THRESHOLD(k=400)`, and `FEDERATED_BENIGN_SUMMARY_THRESHOLD` against LOCAL_THRESHOLD; | `NOT_AUDITED` | — |
| `CALIBRATION-207` | III | 5943 | 16.5 Mandatory synthesis tables | the calibration-generalization/target-attainment diagnostics corresponding to the main threshold-policy results; | `NOT_AUDITED` | — |
| `REPORT-033` | III | 5944 | 16.5 Mandatory synthesis tables | the Part I §10.D.9B source-grounded prior-art distinction table, using the locked categorical vocabulary; | `NOT_AUDITED` | — |
| `CALIBRATION-208` | III | 5945 | 16.5 Mandatory synthesis tables | the Part II §7.5A calibration-support-versus-burden table and seed-level association summary; | `NOT_AUDITED` | — |
| `CALIBRATION-209` | III | 5946 | 16.5 Mandatory synthesis tables | the Part II §7.5B natural-device helped/harmed table with the campaign-fixed support strata; | `NOT_AUDITED` | — |
| `METRIC-030` | III | 5947 | 16.5 Mandatory synthesis tables | the Part II §7.4 typed empirical policy-selection surface and its reconstructable raw metric table. | `NOT_AUDITED` | — |
| `REPORT-034` | IV | 5994 | 3. Gate A — Roadmap and configuration integrity | Every executable experiment maps to exactly one Part II experiment or explicitly declared diagnostic extension. | `PASS` | `validate_programme` requires exact non-suppressed declaration-to-recipe coverage. |
| `GLOBAL-111` | IV | 5995 | 3. Gate A — Roadmap and configuration integrity | No stale method name, retired alias, or opaque experiment code changes the active descriptive scientific identity defined in Part I §10.C. | `PASS` | Canonical graph and release validation reject stale opaque identities. |
| `THRESHOLD-306` | IV | 5996 | 3. Gate A — Roadmap and configuration integrity | No opaque B-number threshold alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports. | `PASS` | Active graph and release manifest validators reject B-number identities. |
| `DATASET-082` | IV | 5997 | 3. Gate A — Roadmap and configuration integrity | No lettered population alias appears in active configuration, manifests, artifacts, tables, figures, reports, or manuscript-facing exports. | `PASS` | Active graph and release manifest validators reject lettered aliases. |
| `THRESHOLD-307` | IV | 5998 | 3. Gate A — Roadmap and configuration integrity | Threshold policies use exactly `CENTRALIZED_REFERENCE`, `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FAMILY_THRESHOLD`, or `CLUSTER_THRESHOLD` where applicable. | `NOT_AUDITED` | — |
| `DATASET-083` | IV | 5999 | 3. Gate A — Roadmap and configuration integrity | Dataset populations use exactly `NBAIOT_NATURAL_DEVICES`, `CICIOT_FILE_CLIENTS`, `NBAIOT_DIRICHLET_CLIENTS`, `EDGE_SENSOR_CLIENTS`, or `EDGE_TEMPORAL_CLIENTS` where applicable. | `NOT_AUDITED` | — |
| `GLOBAL-112` | IV | 6000 | 3. Gate A — Roadmap and configuration integrity | Every locked numerical value used by code is traceable to Part I §11 or its authoritative detailed section. | `NOT_AUDITED` | — |
| `GLOBAL-113` | IV | 6001 | 3. Gate A — Roadmap and configuration integrity | No mandatory grid has silently lost a cell. | `NOT_AUDITED` | — |
| `GLOBAL-114` | IV | 6002 | 3. Gate A — Roadmap and configuration integrity | No unregistered value has been inserted into a locked grid. | `NOT_AUDITED` | — |
| `PROVENANCE-012` | IV | 6003 | 3. Gate A — Roadmap and configuration integrity | Canonical and sensitivity conditions are distinguishable in configuration and artifacts. | `NOT_AUDITED` | — |
| `GLOBAL-115` | IV | 6004 | 3. Gate A — Roadmap and configuration integrity | A sensitivity cell cannot be relabelled as canonical after outcomes are observed. | `NOT_AUDITED` | — |
| `GLOBAL-116` | IV | 6005 | 3. Gate A — Roadmap and configuration integrity | Optional analyses remain explicitly optional and cannot replace mandatory evidence. | `PASS` | Typed recipe campaign roles preserve optional status through campaign reporting. |
| `DATASET-084` | IV | 6011 | 4. Gate B — Dataset integrity | The physical source and canonical dataset identity are recorded. | `PASS` | Canonical manifest validation binds and checks the typed dataset identity. |
| `DATASET-085` | IV | 6012 | 4. Gate B — Dataset integrity | Declared model-input features match the dataset-specific protocol. | `PASS` | Locked schemas/readers and protocol input-feature sequences enforce declared fields. |
| `PREPROCESS-043` | IV | 6013 | 4. Gate B — Dataset integrity | Label normalization is deterministic and auditable. | `PASS` | Raw/normalized labels and eligibility audit retain deterministic normalization evidence. |
| `DATASET-086` | IV | 6014 | 4. Gate B — Dataset integrity | Missing, non-finite, and ineligible rows follow Part I §2.2.1 exactly; no silent imputation, zero-fill, clipping, capping, infinity replacement, or label inference occurs. | `PASS` | Admission excludes invalid rows without fabrication and retains typed evidence. |
| `PREPROCESS-044` | IV | 6015 | 4. Gate B — Dataset integrity | Stable row identity and source provenance survive preprocessing and splitting. | `PASS` | Readers and persisted exclusion evidence retain stable/source identities. |
| `DATASET-087` | IV | 6016 | 4. Gate B — Dataset integrity | Dataset-specific exclusions are counted and reported. | `PASS` | Typed exclusion contracts validate totals and persisted evidence. |
| `DATASET-088` | IV | 6017 | 4. Gate B — Dataset integrity | N-BaIoT preserves the nine natural physical devices for the confirmatory population. | `PASS` | Typed declaration locks nine physical confirmatory devices. |
| `DATASET-089` | IV | 6018 | 4. Gate B — Dataset integrity | CICIoT2023 does not invent physical-device identities from unavailable provenance. | `PASS` | File-defined pseudo-client capability forbids physical-device interpretation. |
| `DATASET-090` | IV | 6019 | 4. Gate B — Dataset integrity | Edge-IIoTset uses only the client definition and temporal information justified by Part I §9 and Part II §4. | `PASS` | Separate typed static and chronology-verified Edge populations enforce the boundary. |
| `DATASET-091` | IV | 6023 | 5. Gate C — Population and client integrity | Each result references an immutable population identity. | `PASS` | Typed population declarations/persisted-artifact validation bind identity. |
| `DATASET-092` | IV | 6024 | 5. Gate C — Population and client integrity | Client membership is deterministic for a fixed population coordinate. | `PASS` | Deterministic ordered membership and fixed-seed split tests cover the contract. |
| `DATASET-093` | IV | 6025 | 5. Gate C — Population and client integrity | Natural-device, file-defined, synthetic/Dirichlet, external, and temporal populations cannot be silently mixed. | `PASS` | Registry/declarations enforce separate typed population identities. |
| `DATASET-094` | IV | 6026 | 5. Gate C — Population and client integrity | Population construction never uses held-out test outcomes. | `NOT_AUDITED` | — |
| `THRESHOLD-308` | IV | 6027 | 5. Gate C — Population and client integrity | FAMILY_THRESHOLD is enabled only where the locked physical-family taxonomy is scientifically valid. | `PASS` | Capabilities and threshold dispatch require a valid family taxonomy. |
| `THRESHOLD-309` | IV | 6028 | 5. Gate C — Population and client integrity | CLUSTER_THRESHOLD receives exactly the eligible client population declared for the experiment. | `PASS` | Cluster construction validates the declared eligible cohort and typed infeasibility. |
| `DATASET-095` | IV | 6029 | 5. Gate C — Population and client integrity | Empty, singleton, and excluded groups remain visible rather than being silently dropped. | `PASS` | Typed group/exclusion contracts keep non-applicable states explicit. |
| `DATASET-096` | IV | 6030 | 5. Gate C — Population and client integrity | Client counts in tables equal the audited population manifest. | `PASS` | Manifest validation rejects client-count or membership-set disagreement. |
| `CALIBRATION-210` | IV | 6032 | 5. Gate C — Population and client integrity | For every persistent-client result, the same immutable `client_id` binds training, calibration, evaluation, local threshold state, and any personalized model state exactly as Part I §3.3A requires. | `NOT_AUDITED` | — |
| `CALIBRATION-211` | IV | 6033 | 5. Gate C — Population and client integrity | No unseen-client or intermittent-client interpretation is inferred from the calibration cold-start experiment. | `NOT_AUDITED` | — |
| `CALIBRATION-212` | IV | 6037 | 6. Gate D — Split, chronology, and eligibility integrity | Train, calibration, and evaluation partitions are disjoint by immutable row identity. | `PASS` | Stable-row partition overlap is rejected before preprocessing/evaluation. |
| `CALIBRATION-213` | IV | 6038 | 6. Gate D — Split, chronology, and eligibility integrity | Benign training fit uses training rows only. | `PASS` | Locked partitioning/training extraction is role-scoped and benign-only. |
| `CALIBRATION-214` | IV | 6039 | 6. Gate D — Split, chronology, and eligibility integrity | Calibration rows never enter reported held-out test metrics. | `PASS` | Calibration/evaluation artifact role and row-set overlap are rejected. |
| `CALIBRATION-215` | IV | 6040 | 6. Gate D — Split, chronology, and eligibility integrity | Test outcomes never influence split construction, eligibility, threshold tuning, model selection, or comparator tuning. | `NOT_AUDITED` | — |
| `CALIBRATION-216` | IV | 6041 | 6. Gate D — Split, chronology, and eligibility integrity | `n_k_source` is computed before experimental subsampling. | `NOT_AUDITED` | — |
| `CALIBRATION-217` | IV | 6042 | 6. Gate D — Split, chronology, and eligibility integrity | Primary eligibility is exactly `n_k_source >= 100`. | `PASS` | Shared typed protocol locks 100 benign calibration rows as the minimum. |
| `CALIBRATION-218` | IV | 6043 | 6. Gate D — Split, chronology, and eligibility integrity | Eligibility is fixed before test evaluation and identical across compared threshold policies. | `PASS` | Calibration-only eligibility and common-cohort validation enforce the comparator boundary. |
| `CALIBRATION-219` | IV | 6044 | 6. Gate D — Split, chronology, and eligibility integrity | Calibration-size ablations use `m` independently of the source-pool eligibility decision. | `NOT_AUDITED` | — |
| `CALIBRATION-220` | IV | 6045 | 6. Gate D — Split, chronology, and eligibility integrity | Temporal experiments use genuine chronology: historical calibration < future recalibration < future evaluation. | `PASS` | Temporal construction requires verified Edge chronology and the chronological protocol. |
| `CALIBRATION-221` | IV | 6046 | 6. Gate D — Split, chronology, and eligibility integrity | Generated pseudo-time or file ordering is never substituted for real timestamps where chronology is required. | `PASS` | Chronology capability and PCAP validation reject file/source-order substitutes. |
| `PREPROCESS-045` | IV | 6050 | 7. Gate E — Preprocessing integrity | Every threshold comparison references one named preprocessing protocol identity. | `PASS` | Typed declarations/coordinates persist preprocessing identity. |
| `PREPROCESS-046` | IV | 6051 | 7. Gate E — Preprocessing integrity | `FEDERATED_CLIENT_LOCAL_STANDARD` is fit client-locally on benign training only in the confirmatory protocol. | `PASS` | Locked local training protocol plus benign training split enforce the condition. |
| `PREPROCESS-047` | IV | 6052 | 7. Gate E — Preprocessing integrity | `FEDERATED_POOLED_MIN_MAX` is never silently mixed into the confirmatory ladder. | `PASS` | Pooled MinMax has a separate typed supportive coordinate. |
| `PREPROCESS-048` | IV | 6053 | 7. Gate E — Preprocessing integrity | `CENTRALIZED_POOLED_MIN_MAX` is independently fitted and never reuses federated fitted states. | `PASS` | Distinct pooled-owner state and centralized branch reject federated fitted state reuse. |
| `PREPROCESS-049` | IV | 6054 | 7. Gate E — Preprocessing integrity | Threshold methods cannot fit, select, or alter model-input preprocessing. | `NOT_AUDITED` | — |
| `PREPROCESS-050` | IV | 6055 | 7. Gate E — Preprocessing integrity | Cluster-fingerprint standardization is kept distinct from model-input preprocessing. | `PASS` | Cluster fingerprint protocol is separate from model-input preprocessing protocol/state. |
| `PREPROCESS-051` | IV | 6056 | 7. Gate E — Preprocessing integrity | Serialization/reload equivalence uses the `1e-12` engineering tolerance only for reload validation. | `PASS` | Typed reload comparison uses the locked engineering tolerance. |
| `PREPROCESS-052` | IV | 6057 | 7. Gate E — Preprocessing integrity | A reload tolerance comparison is never used to establish scientific fixed-score identity. | `PASS` | Fixed-score identity validates exact manifest/content evidence instead. |
| `TRAIN-083` | IV | 6061 | 8. Gate F — Training and terminal-detector integrity | Every **federated training** execution has exactly one scientific terminal detector at round `200`; `FEDAVG_LOCAL_FINE_TUNING` starts from that detector and produces separately identified post-training client-personalized states after exactly ten local epochs. | `PASS` | Fine-tuning requires the exact terminal FedAvg round and locked depth. |
| `TRAIN-084` | IV | 6062 | 8. Gate F — Training and terminal-detector integrity | Recovery checkpoints are used only to resume interrupted execution. | `NOT_AUDITED` | — |
| `TRAIN-085` | IV | 6063 | 8. Gate F — Training and terminal-detector integrity | Diagnostic checkpoints are observational and never become score sources. | `PASS` | Threshold variants consume the one terminal fixed-score workspace. |
| `THRESHOLD-310` | IV | 6064 | 8. Gate F — Training and terminal-detector integrity | SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD do not trigger policy-specific retraining. | `PASS` | Stage runner reuses training and score evidence by training coordinate. |
| `PREPROCESS-053` | IV | 6065 | 8. Gate F — Training and terminal-detector integrity | FedAvg confirmatory models are distinct from FedProx, Ditto, centralized, preprocessing-sensitivity, and post-FedAvg fine-tuned client states where the protocol requires separate detector identities. | `NOT_AUDITED` | — |
| `SCORE-022` | IV | 6066 | 8. Gate F — Training and terminal-detector integrity | No test AUROC, test label, threshold result, DATP effect, or external result changes the terminal detector. | `NOT_AUDITED` | — |
| `TRAIN-086` | IV | 6067 | 8. Gate F — Training and terminal-detector integrity | FedProx executes the complete locked `mu` grid. | `NOT_AUDITED` | — |
| `TRAIN-087` | IV | 6068 | 8. Gate F — Training and terminal-detector integrity | FedProx persists broadcast/returned state identity and produces `L2Drift`, `RMSDrift`, terminal-50 drift summaries, and `DriftSuppression` exactly as Part I §7.1A requires. | `NOT_AUDITED` | — |
| `TRAIN-088` | IV | 6069 | 8. Gate F — Training and terminal-detector integrity | Client-round FedProx drift cells remain nested diagnostics and are never treated as independent inferential observations. | `NOT_AUDITED` | — |
| `TRAIN-089` | IV | 6070 | 8. Gate F — Training and terminal-detector integrity | Ditto executes the complete locked `lambda_D` grid and preserves genuine persistent-personalized-state semantics before using the name Ditto. | `NOT_AUDITED` | — |
| `CALIBRATION-222` | IV | 6072 | 8. Gate F — Training and terminal-detector integrity | `FEDAVG_LOCAL_FINE_TUNING` initializes every client from the exact seed-matched FedAvg round-200 model, uses a fresh optimizer state, exactly 10 benign-training epochs, no early stopping, and no calibration/evaluation/attack-label access. | `PASS` | Fine-tuning source and protocol enforce round-200/ten-epoch requirements and client training input is role-scoped. |
| `SCORE-023` | IV | 6073 | 8. Gate F — Training and terminal-detector integrity | Fine-tuned client models are frozen before scoring and are never re-fine-tuned per threshold policy. | `NOT_AUDITED` | — |
| `TRAIN-090` | IV | 6074 | 8. Gate F — Training and terminal-detector integrity | The deterministic fine-tuning seed identity includes `(dataset_id,population_id,training_seed,client_id)` with purpose `FEDAVG_LOCAL_FINE_TUNING`. | `NOT_AUDITED` | — |
| `PREPROCESS-054` | IV | 6078 | 9. Gate G — Fixed-score and scoring integrity | Exactly one canonical evaluation-score artifact exists per fixed detector / preprocessing / population / seed coordinate. | `PASS` | Fixed workspace and persisted score-manifest identity bind one artifact. |
| `SCORE-024` | IV | 6079 | 9. Gate G — Fixed-score and scoring integrity | SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD reference that same score artifact identity within a ladder. | `PASS` | Fixed-score control requires identical manifest/content evidence. |
| `SCORE-025` | IV | 6080 | 9. Gate G — Fixed-score and scoring integrity | Threshold methods do not independently regenerate detector scores. | `PASS` | Threshold variants receive the fixed score workspace. |
| `SCORE-026` | IV | 6081 | 9. Gate G — Fixed-score and scoring integrity | Ordered row identities are preserved across score, label, and evaluation artifacts. | `PASS` | Evaluation score arrays require exact aligned sequences. |
| `SCORE-027` | IV | 6082 | 9. Gate G — Fixed-score and scoring integrity | Calibration-score identity is likewise shared where the experiment requires fixed calibration evidence. | `PASS` | Fixed-score controls bind common calibration role/identity. |
| `SCORE-028` | IV | 6083 | 9. Gate G — Fixed-score and scoring integrity | A higher reconstruction error always denotes greater anomaly evidence. | `PASS` | Strict score-greater-than-threshold prediction semantics. |
| `SCORE-029` | IV | 6084 | 9. Gate G — Fixed-score and scoring integrity | AUROC is computed from the canonical continuous score/label artifact, not from thresholded predictions. | `PASS` | AUROC consumes continuous score values/labels directly. |
| `SCORE-030` | IV | 6085 | 9. Gate G — Fixed-score and scoring integrity | Any policy-specific AUROC difference within a fixed-score ladder is treated as an identity/provenance failure. | `PASS` | Quality-control invariance rejects policy differences. |
| `CALIBRATION-223` | IV | 6089 | 10. Gate H — Calibration integrity | Every DATP-compatible threshold method uses benign calibration data only. | `PASS` | Benign-only calibration loader is the threshold construction entrypoint. |
| `CALIBRATION-224` | IV | 6090 | 10. Gate H — Calibration integrity | Attack-labelled rows never affect threshold values, q selection, eligibility, cluster count, comparator tuning, shrinkage, or conformal significance level. | `PASS` | Attack labels fail before downstream policy input construction. |
| `CALIBRATION-225` | IV | 6091 | 10. Gate H — Calibration integrity | Calibration and evaluation rows are disjoint. | `PASS` | Stable-row overlap validation rejects the coordinate. |
| `CALIBRATION-226` | IV | 6092 | 10. Gate H — Calibration integrity | Type-7 empirical quantiles use float64 and are not rounded before threshold application. | `PASS` | Float64 linear/type-7 quantile is applied directly. |
| `CALIBRATION-227` | IV | 6093 | 10. Gate H — Calibration integrity | LOCAL_CONFORMAL_THRESHOLD is the explicit conformal-order-statistic exception and is not routed through type-7 interpolation. | `PASS` | Separate finite-sample conformal rank construction. |
| `CALIBRATION-228` | IV | 6094 | 10. Gate H — Calibration integrity | Calibration-size subsampling follows Part II §2.3A exactly: immutable-row ordering, SHA-256 seed derivation, PCG64, without replacement, prefix nesting. | `NOT_AUDITED` | — |
| `CALIBRATION-229` | IV | 6095 | 10. Gate H — Calibration integrity | The 10 nested calibration replicates are summarized within training seed and never treated as independent seeds. | `NOT_AUDITED` | — |
| `CALIBRATION-230` | IV | 6096 | 10. Gate H — Calibration integrity | Shared-calibration contributor-availability sensitivity enumerates every permitted omission subset exhaustively, changes only shared-summary contribution, and evaluates every resulting shared threshold on the unchanged full eligible client population. | `NOT_AUDITED` | — |
| `CALIBRATION-231` | IV | 6097 | 10. Gate H — Calibration integrity | Omission subsets are never interpreted as independent replications or used to inflate the seed count. | `NOT_AUDITED` | — |
| `CALIBRATION-232` | IV | 6098 | 10. Gate H — Calibration integrity | Every threshold-stage artifact is generated under the Part I §3.2A protocol-compliant participant assumption; no experiment silently injects fabricated thresholds, support counts, summaries, fingerprints, sketches, scores, or client identities. | `NOT_AUDITED` | — |
| `CALIBRATION-233` | IV | 6099 | 10. Gate H — Calibration integrity | Contributor-availability sensitivity is labeled non-adversarial; it is never called Byzantine robustness, poisoning resistance, malicious-dropout robustness, or message-integrity validation. | `NOT_AUDITED` | — |
| `CALIBRATION-234` | IV | 6100 | 10. Gate H — Calibration integrity | Any threshold-stage provenance/checksum/identity mismatch invalidates the artifact/coordinate and is not counted as an attack-defense success. | `NOT_AUDITED` | — |
| `THRESHOLD-311` | IV | 6105 | 11. Gate I — Threshold-policy integrity | Computes each eligible client's local q-quantile and takes the arithmetic mean of eligible local quantiles. | `PASS` | Shared construction validates arithmetic mean of local quantiles. |
| `THRESHOLD-312` | IV | 6106 | 11. Gate I — Threshold-policy integrity | Is never mislabeled as the exact pooled quantile. | `PASS` | Separate typed shared and exact-pooled constructions. |
| `THRESHOLD-313` | IV | 6107 | 11. Gate I — Threshold-policy integrity | Applies one threshold to every eligible client. | `PASS` | Shared assignments require one identical threshold. |
| `THRESHOLD-314` | IV | 6110 | 11. Gate I — Threshold-policy integrity | Uses each eligible client's own benign q-quantile. | `PASS` | Local assignments validate own local quantile. |
| `THRESHOLD-315` | IV | 6111 | 11. Gate I — Threshold-policy integrity | Uses the same q and score evidence as SHARED_THRESHOLD in the confirmatory comparison. | `PASS` | Common cohort and fixed-score controls bind comparison evidence. |
| `THRESHOLD-316` | IV | 6114 | 11. Gate I — Threshold-policy integrity | Uses only the locked physical-family taxonomy. | `PASS` | Family mapping must be declared and capability-authorized. |
| `THRESHOLD-317` | IV | 6115 | 11. Gate I — Threshold-policy integrity | Forms family thresholds exactly from eligible family-member local thresholds. | `PASS` | Family membership/local-quantile equality is validated. |
| `THRESHOLD-318` | IV | 6116 | 11. Gate I — Threshold-policy integrity | Is unavailable where no defensible taxonomy exists. | `PASS` | Typed family-taxonomy unavailable result. |
| `THRESHOLD-319` | IV | 6119 | 11. Gate I — Threshold-policy integrity | Fingerprint is exactly `[mean(error), std(error), skewness(error), p95(error)]`. | `PASS` | Cluster protocol validates exact fingerprint fields/order. |
| `THRESHOLD-320` | IV | 6120 | 11. Gate I — Threshold-policy integrity | Canonical clustering uses the separate score-side fingerprint-standardization contract, canonical `K=3`, and the locked initialization/seed handling required by Part II §7.1. | `PASS` | Cluster protocol locks standardization/grouping/init details. |
| `THRESHOLD-321` | IV | 6121 | 11. Gate I — Threshold-policy integrity | Cluster threshold is the mean of member local thresholds. | `PASS` | Canonical cluster aggregation is arithmetic mean. |
| `THRESHOLD-322` | IV | 6122 | 11. Gate I — Threshold-policy integrity | CLUSTER_THRESHOLD never changes the detector, performs model clustering, or acquires a privacy claim. | `NOT_AUDITED` | — |
| `THRESHOLD-323` | IV | 6123 | 11. Gate I — Threshold-policy integrity | Cluster identities are aligned before across-seed switch-frequency reporting. | `PASS` | Cross-seed switch analysis aligns labels to the reference seed. |
| `THRESHOLD-324` | IV | 6127 | 12. Gate J — Comparator and threshold-variant integrity | Exact pooled benign quantile uses the type-7 pooled oracle. | `PASS` | `construct_pooled_shared_quantile` uses the locked exact empirical quantile. |
| `CALIBRATION-235` | IV | 6128 | 12. Gate J — Comparator and threshold-variant integrity | Sample-weighted shared construction uses the declared eligible calibration weights. | `PASS` | The construction retains calibration counts and normalizes their declared weights. |
| `THRESHOLD-325` | IV | 6129 | 12. Gate J — Comparator and threshold-variant integrity | Fixed shrinkage executes the full λ curve and never selects a winner post hoc. | `PASS` | Dispatch returns every fixed protocol weight; no selection path exists. |
| `THRESHOLD-326` | IV | 6130 | 12. Gate J — Comparator and threshold-variant integrity | Size-aware shrinkage uses `n_k_used/(n_k_used+100)` and never substitutes `n_k_source` for `m` in a subsampled cell. | `PASS` | Each assignment records the used calibration support and its locked support-based weight. |
| `THRESHOLD-327` | IV | 6131 | 12. Gate J — Comparator and threshold-variant integrity | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` communicates only the predeclared benign summaries and includes the full pooled variance decomposition. | `PASS` | Per-client float64 summaries and the validated within/between pooled decomposition are retained. |
| `THRESHOLD-328` | IV | 6132 | 12. Gate J — Comparator and threshold-variant integrity | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is never called Laridi-faithful. | `PASS` | The persisted benign-summary comparator report explicitly rejects a Laridi-faithfulness claim. |
| `THRESHOLD-329` | IV | 6133 | 12. Gate J — Comparator and threshold-variant integrity | KLL uses float64, canonical `k=400`, sensitivity `{200,800}`, ascending client merge order, and the locked inclusive-rank semantics. | `PASS` | The KLL protocol locks the grid; construction sorts clients and explicitly requests the library's inclusive rank. |
| `THRESHOLD-330` | IV | 6134 | 12. Gate J — Comparator and threshold-variant integrity | KLL observed empirical rank/threshold errors are measured against the exact pooled type-7 oracle. | `PASS` | Each reconstruction retains empirical-rank and absolute/relative threshold errors against the exact pooled oracle. |
| `THRESHOLD-331` | IV | 6135 | 12. Gate J — Comparator and threshold-variant integrity | KLL implementation randomness follows Part II §9.2 and remains nested within training seed. | `PASS` | Each reconstruction persists a distinct deterministic seed derived from its enclosing training seed. |
| `THRESHOLD-332` | IV | 6136 | 12. Gate J — Comparator and threshold-variant integrity | `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` uses float64, arithmetic mean, sample standard deviation with `ddof=1`, and the locked `{shared, local}` 2×2 scope comparison; it is never presented as a faithful reproduction of Meidan's complete detector. | `PASS` | The typed estimator is restricted to shared/local scope and the report retains both estimator families; prior-art output distinguishes it from Meidan's complete detector. |
| `CALIBRATION-236` | IV | 6137 | 12. Gate J — Comparator and threshold-variant integrity | LOCAL_CONFORMAL_THRESHOLD reports held-out benign coverage and its limitations; it does not claim arbitrary client-conditional validity. | `PASS` | The report retains held-out benign coverage and serializes an explicit finite-sample, retained-evidence claim boundary. |
| `GLOBAL-117` | IV | 6143 | 13. Gate K — Experiment completeness | Every declared factor level was executed or has a recorded pre-specified infeasibility reason. | `PASS` | Materialized coordinates are rejected when missing or unauthorized; graph-validated infeasibility has a typed disposition. |
| `GLOBAL-118` | IV | 6144 | 13. Gate K — Experiment completeness | Every required comparison method is present. | `PASS` | Coordinate completeness derives the full declaration grid and rejects absent method coordinates. |
| `GLOBAL-119` | IV | 6145 | 13. Gate K — Experiment completeness | Every required seed is present; confirmatory inference requires exactly ten valid paired seed deltas. | `PASS` | The pre-registered confirmatory cohort and inference protocol both require exactly ten seeds. |
| `GLOBAL-120` | IV | 6146 | 13. Gate K — Experiment completeness | All declared nested replicates are present where required. | `PASS` | Nested reconstruction and calibration analyses retain their declared replicate identities and validate complete grids. |
| `REPORT-035` | IV | 6147 | 13. Gate K — Experiment completeness | Required outcomes, diagnostics, tables, and figures were produced or explicitly marked unavailable under a roadmap rule. | `NOT_AUDITED` | — |
| `REPORT-036` | IV | 6148 | 13. Gate K — Experiment completeness | Null, reversed, unstable, and unfavorable outcomes remain in the result set. | `NOT_AUDITED` | — |
| `GLOBAL-121` | IV | 6149 | 13. Gate K — Experiment completeness | No experiment was dropped because it weakened the narrative. | `NOT_AUDITED` | — |
| `GLOBAL-122` | IV | 6150 | 13. Gate K — Experiment completeness | Optional experiments are visually and semantically separated from mandatory evidence. | `NOT_AUDITED` | — |
| `GLOBAL-123` | IV | 6151 | 13. Gate K — Experiment completeness | Part II §8.6 produces every feasible `m in {0,1,2,3,4}` omission subset, exact seed-level subset summaries, and the identities of worst-case omission sets. | `PASS` | The contributor report retains each omission cell, m-level seed summaries, unavailable cells, and worst-case omission identities. |
| `THRESHOLD-333` | IV | 6155 | 14. Gate L — Evaluation and metric integrity | Prediction semantics are exactly `attack iff score > threshold`. | `PASS` | The sole decision helper delegates to strict score exceedance. |
| `METRIC-031` | IV | 6156 | 14. Gate L — Evaluation and metric integrity | Confusion counts are computed from held-out evaluation rows only. | `PASS` | Confusion construction rejects calibration and duplicate source rows. |
| `METRIC-032` | IV | 6157 | 14. Gate L — Evaluation and metric integrity | Per-client metrics are computed before cross-client aggregation where valid client identity exists. | `PASS` | Evaluation constructs each client result before population aggregation. |
| `DATASET-097` | IV | 6158 | 14. Gate L — Evaluation and metric integrity | `CV(FPR)` uses only the eligible FPR-evaluable client population defined in Part III. | `PASS` | Population aggregation collects FPR values only from the typed FPR-evaluable cohort. |
| `METRIC-033` | IV | 6159 | 14. Gate L — Evaluation and metric integrity | Absolute dispersion metrics accompany CV where low mean FPR could make CV unstable or misleading. | `NOT_AUDITED` | — |
| `METRIC-034` | IV | 6160 | 14. Gate L — Evaluation and metric integrity | Attack-sensitive metrics are marked unavailable when valid per-client attack assignment is absent. | `PASS` | Attack-rate and attack-derived metric paths return typed unavailability for invalid assignment. |
| `METRIC-035` | IV | 6161 | 14. Gate L — Evaluation and metric integrity | Undefined denominators remain undefined; they are never converted to zero. | `PASS` | Zero-mean and undefined-class cases retain typed undefined status and reason. |
| `SCORE-031` | IV | 6162 | 14. Gate L — Evaluation and metric integrity | AUROC/AP are detector-quality controls and do not become threshold-scope verdicts. | `PASS` | Fixed-score comparisons reject a policy-specific AUROC or AP difference. |
| `CALIBRATION-237` | IV | 6163 | 14. Gate L — Evaluation and metric integrity | Held-out target-attainment error is computed from held-out benign rows and is never replaced by calibration-set exceedance. | `PASS` | Operating-point diagnostics use the held-out client FPR for target error. |
| `CALIBRATION-238` | IV | 6164 | 14. Gate L — Evaluation and metric integrity | Calibration-to-held-out benign generalization gap uses the exact calibration scores that constructed each scalar threshold, the strict `score > threshold` exceedance rule, and the unchanged held-out benign evaluation rows. | `PASS` | The diagnostic pairs retained calibration scores with held-out FPR under strict exceedance semantics. |
| `CALIBRATION-239` | IV | 6165 | 14. Gate L — Evaluation and metric integrity | Calibration-generalization-gap diagnostics never feed threshold fitting, policy selection, model selection, or claim-tier promotion. | `NOT_AUDITED` | — |
| `METRIC-036` | IV | 6166 | 14. Gate L — Evaluation and metric integrity | P10 Macro-F1 and worst-client balanced accuracy remain visible when available, including unfavorable trade-offs. | `NOT_AUDITED` | — |
| `TRAIN-091` | IV | 6170 | 15. Gate M — Statistical integrity | Training seed is the independent inferential unit. | `PASS` | Confirmatory validation requires the exact ten-seed cohort and constructs one paired contrast per seed. |
| `STAT-023` | IV | 6171 | 15. Gate M — Statistical integrity | Nested replicates are summarized within seed before across-seed inference. | `PASS` | Across-seed inference accepts one ordered paired contrast per locked seed after nested owners summarize their grids. |
| `STAT-024` | IV | 6172 | 15. Gate M — Statistical integrity | Confirmatory delta direction matches the Part III definition. | `PASS` | The endpoint locks `SHARED_THRESHOLD - LOCAL_THRESHOLD` for `CV(FPR)`. |
| `STAT-025` | IV | 6173 | 15. Gate M — Statistical integrity | The confirmatory statistic is the arithmetic mean of the ten paired seed-level deltas. | `PASS` | BCa and precision owners use the arithmetic mean of paired deltas. |
| `STAT-026` | IV | 6174 | 15. Gate M — Statistical integrity | The confirmatory uncertainty is the locked two-sided 95% BCa interval over paired seed deltas. | `PASS` | Locked protocol specifies a 95% paired arithmetic-mean BCa interval with 10,000 replicates. |
| `STAT-027` | IV | 6175 | 15. Gate M — Statistical integrity | Degenerate/invalid BCa states produce `CONFIRMATORY_INFERENCE_UNAVAILABLE` rather than a substituted method. | `PASS` | Degenerate and blocked BCa outcomes emit the dedicated unavailable confirmatory decision. |
| `STAT-028` | IV | 6176 | 15. Gate M — Statistical integrity | Wilcoxon is paired, uses exact computation where feasible, and records fallback/approximation behavior. | `PASS` | Paired Wilcoxon locks Pratt handling and retains method selection and fallback reason. |
| `STAT-029` | IV | 6177 | 15. Gate M — Statistical integrity | Rank-biserial effect size is the matched-pairs version, not unpaired Cliff's delta. | `PASS` | Protocol and owner require matched-pairs rank-biserial correlation. |
| `STAT-030` | IV | 6178 | 15. Gate M — Statistical integrity | Secondary emphasized p-values use predeclared families and Holm correction. | `PASS` | Confirmatory Wilcoxon and exact-sign p-values form one predeclared two-hypothesis robustness family and are Holm-adjusted before publication. |
| `STAT-031` | IV | 6179 | 15. Gate M — Statistical integrity | Exact paired sign-test uses only non-zero paired deltas, an exact `Binomial(n_nonzero, 0.5)` null, and no normal approximation; zero deltas remain visible in sign counts. | `PASS` | Exact sign-test retains directional counts and uses the combinatorial two-sided binomial value. |
| `STAT-032` | IV | 6180 | 15. Gate M — Statistical integrity | Leave-one-seed-out precision diagnostics are reported without changing the inferential sample. | `PASS` | All leave-one-seed-out means are retained alongside the unchanged full ten-seed estimate. |
| `TRAIN-092` | IV | 6181 | 15. Gate M — Statistical integrity | Leave-one-device-out confirmatory influence uses the same ten training seeds and already generated scores; the nine omitted-device means are dependent diagnostics and are never treated as nine independent replicates. | `PASS` | Fixed-score artifacts supply the diagnostic, which summarizes each omitted device across the locked cohort. |
| `STAT-033` | IV | 6182 | 15. Gate M — Statistical integrity | `LODO_HIGH_INFLUENCE` is evaluated exactly as Part III §15.1A specifies; the 25% influence boundary is descriptive and never modifies the BCa decision rule. | `PASS` | Both prospective triggers and the unmodified 0.25 threshold are calculated outside the BCa decision. |
| `STAT-034` | IV | 6183 | 15. Gate M — Statistical integrity | No seed or client is removed because of effect direction. | `PASS` | Confirmatory analysis exposes no seed-exclusion path; validation requires every locked seed. |
| `DATASET-098` | IV | 6187 | 16. Gate N — Mechanism-analysis integrity | Mechanism analyses use only pre-specified variables and populations. | `NOT_AUDITED` | — |
| `GLOBAL-124` | IV | 6188 | 16. Gate N — Mechanism-analysis integrity | Jensen–Shannon constructions use the exact locked binning/log convention from Part II. | `PASS` | JSD uses pooled benign-calibration type-7 64-bin quantile edges, duplicate collapse, no pseudocount, and base-2 mean-pairwise aggregation. |
| `GLOBAL-125` | IV | 6189 | 16. Gate N — Mechanism-analysis integrity | Association analyses use associative, not causal, language. | `PASS` | Association records and claim rendering preserve non-causal mechanism/supportive language. |
| `GLOBAL-126` | IV | 6190 | 16. Gate N — Mechanism-analysis integrity | `n < 5` association cases use the declared insufficient-evidence state rather than fabricated coefficients. | `PASS` | The association owner returns insufficient evidence without coefficients, p-values, or regression diagnostics below five observations. |
| `REPORT-037` | IV | 6191 | 16. Gate N — Mechanism-analysis integrity | Cluster stability reports memberships, sizes, empty clusters, singleton clusters, ARI, and switch behavior where specified. | `PASS` | Complete partition diagnostics and deterministic client switch frequencies are retained and rendered. |
| `GLOBAL-127` | IV | 6192 | 16. Gate N — Mechanism-analysis integrity | Recovery-of-local-gap quantities are not clipped to `[0,1]`. | `PASS` | Grouped recovery preserves raw fractions, including values above one and below zero. |
| `THRESHOLD-334` | IV | 6193 | 16. Gate N — Mechanism-analysis integrity | Non-positive SHARED_THRESHOLD→LOCAL_THRESHOLD denominators use the declared unavailable state. | `PASS` | Typed undefined recovery retains the explicit non-positive-gap reason. |
| `PREPROCESS-055` | IV | 6194 | 16. Gate N — Mechanism-analysis integrity | Natural-device mechanism leave-one-device-out analysis never retrains, refits preprocessing, or rescores; it recomputes only the population-dependent heterogeneity/shared-threshold quantities defined in Part II §7.4. | `PASS` | Reduced diagnostics use original fixed-score artifacts only. |
| `DATASET-099` | IV | 6195 | 16. Gate N — Mechanism-analysis integrity | The `9 × 10` leave-one-device seed cells are never treated as 90 independent observations; the association influence analysis remains a sensitivity analysis over the original population/seed structure. | `PASS` | Device-level summaries retain seed series as dependent diagnostics. |
| `METRIC-037` | IV | 6196 | 16. Gate N — Mechanism-analysis integrity | Part II §7.5 reports exact per-seed FPR/TPR direction counts without inventing a floating tolerance or post-hoc materiality cutoff. | `PASS` | Exact comparisons and typed TPR unavailability are tested. |
| `CALIBRATION-240` | IV | 6197 | 16. Gate N — Mechanism-analysis integrity | Part II §7.5A support-versus-burden Spearman coefficients use only the common valid client set, require at least five clients plus nonconstant inputs, use average ranks for ties, and do not report client-level inferential p-values from the nine-device population. | `PASS` | Common valid clients, five-client minimum, average ranks, and no p-value output are enforced. |
| `CALIBRATION-241` | IV | 6198 | 16. Gate N — Mechanism-analysis integrity | The support-versus-burden diagnostic is interpreted associatively and never used to claim that calibration support causes client harm. | `PASS` | Mechanism claim rendering is explicitly associative and non-confirmatory. |
| `GLOBAL-128` | IV | 6199 | 16. Gate N — Mechanism-analysis integrity | Equity–utility Pareto analysis never invents a scalarized winner. | `PASS` | Explicit nondominance is tested; no scalarized winner is emitted. |
| `THRESHOLD-335` | IV | 6201 | 16. Gate N — Mechanism-analysis integrity | Every FedProx, `FEDAVG_LOCAL_FINE_TUNING`, and Ditto stress condition reports the common Part I §7.2B score/threshold-alignment tuple whenever inputs are valid. | `PASS` | All three stress-report paths render the five alignment metrics, raw DeltaScope, un-clipped ScopeAbsorption, and explicit unavailable denominator state. |
| `BOUNDARY-009` | IV | 6202 | 16. Gate N — Mechanism-analysis integrity | `ScopeAbsorption` and every `AlignmentReduction` are un-clipped; non-positive FedAvg denominators produce the declared unavailable states rather than an epsilon adjustment. | `PASS` | Raw reduction formula and typed unavailable denominator state are tested. |
| `CALIBRATION-242` | IV | 6203 | 16. Gate N — Mechanism-analysis integrity | `FEDAVG_LOCAL_FINE_TUNING` uses exactly ten benign-training local epochs from the exact round-200 FedAvg weights, a fresh optimizer state, no early stopping, and no calibration/evaluation/attack-label access. | `PASS` | Fine-tuning validates the round-200 source and the locked ten-epoch benign training contract. |
| `DATASET-100` | IV | 6204 | 16. Gate N — Mechanism-analysis integrity | The N-BaIoT helped/harmed profile reports all ten seed-level fractions and every physical-device help/harm frequency; the 9×10 cells are never treated as independent observations. | `PASS` | Seed-level fractions and device frequencies are retained as descriptive campaign summaries. |
| `CALIBRATION-243` | IV | 6205 | 16. Gate N — Mechanism-analysis integrity | Calibration-support strata are frozen from ascending `SupportScore_k=median_s(n_{s,k,source})` with canonical-client-ID tie-break into ranks `1..3`, `4..6`, `7..9`; if exactly nine eligible N-BaIoT clients are not available, the stratum analysis emits the declared unavailable state. | `PASS` | Per-seed support medians, canonical-ID ties, fixed 3/3/3 ranks, and explicit non-nine-device unavailability are enforced. |
| `GLOBAL-129` | IV | 6206 | 16. Gate N — Mechanism-analysis integrity | The empirical policy-selection surface emits only the declared typed states and raw nondominated sets; no learned classifier, cutoff, scalar utility weight, or post-hoc production rule is fitted. | `PASS` | The policy surface is a typed raw nondominance record only; no selector is fitted or emitted. |
| `CALIBRATION-244` | IV | 6207 | 16. Gate N — Mechanism-analysis integrity | `H_TAUTOLOGY` reporting uses disjoint calibration/evaluation row identities and shows calibration exceedance, held-out target error, and calibration-generalization gap rather than calling local q95 held-out FPR “guaranteed.” | `PASS` | Stable calibration/evaluation identities are checked before construction and the publication record renders all required falsification quantities. |
| `DATASET-101` | IV | 6211 | 17. Gate O — External and boundary evidence integrity | CICIoT2023 findings are described only for file-defined pseudo-clients and never generalized to the original physical-device topology. | `NOT_AUDITED` | — |
| `DATASET-102` | IV | 6212 | 17. Gate O — External and boundary evidence integrity | Edge-IIoTset conclusions are limited to the metrics and client semantics actually available. | `NOT_AUDITED` | — |
| `CALIBRATION-245` | IV | 6213 | 17. Gate O — External and boundary evidence integrity | Unavailable Edge attack metrics remain unavailable and are not reconstructed from unsupported labels. | `NOT_AUDITED` | — |
| `BOUNDARY-010` | IV | 6214 | 17. Gate O — External and boundary evidence integrity | External validation is never promoted into a second confirmatory endpoint. | `NOT_AUDITED` | — |
| `DATASET-103` | IV | 6215 | 17. Gate O — External and boundary evidence integrity | Controlled Dirichlet partitions remain sensitivity evidence and are not called natural-device evidence. | `NOT_AUDITED` | — |
| `DATASET-104` | IV | 6216 | 17. Gate O — External and boundary evidence integrity | No extra dataset is added without an explicit roadmap amendment. | `NOT_AUDITED` | — |
| `TEMPORAL-002` | IV | 6220 | 18. Gate P — Temporal integrity | Temporal evidence uses valid timestamps and genuine chronology only. | `NOT_AUDITED` | — |
| `TEMPORAL-003` | IV | 6221 | 18. Gate P — Temporal integrity | Static, frozen-future, and one-shot-recalibrated states are computed exactly as Part II §12.1 specifies. | `NOT_AUDITED` | — |
| `CALIBRATION-246` | IV | 6222 | 18. Gate P — Temporal integrity | Future evaluation never influences historical thresholding or future recalibration. | `NOT_AUDITED` | — |
| `TEMPORAL-004` | IV | 6223 | 18. Gate P — Temporal integrity | `drift_excess`, `recovered_amount`, and `recovery_ratio` use Part III §14 definitions. | `NOT_AUDITED` | — |
| `THRESHOLD-336` | IV | 6224 | 18. Gate P — Temporal integrity | `recovery_ratio` is undefined below the locked positive-materiality threshold. | `NOT_AUDITED` | — |
| `THRESHOLD-337` | IV | 6225 | 18. Gate P — Temporal integrity | Temporal association diagnostics use the declared 64-bin common quantile grid and n≥5 requirement. | `NOT_AUDITED` | — |
| `CALIBRATION-247` | IV | 6226 | 18. Gate P — Temporal integrity | Results are framed as one-shot threshold aging/recalibration evidence, not continuous drift handling. | `NOT_AUDITED` | — |
| `REPORT-038` | IV | 6230 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Every table/figure/result row can be traced back to its exact execution coordinate. | `NOT_AUDITED` | — |
| `DATASET-105` | IV | 6231 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Artifact provenance records code version, dataset identity, population identity, seed, protocol identities, and dependency/library versions required by the method. | `NOT_AUDITED` | — |
| `PROVENANCE-013` | IV | 6232 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Ordered record identities are recoverable for score and label artifacts. | `NOT_AUDITED` | — |
| `PROVENANCE-014` | IV | 6233 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Re-running a deterministic coordinate reproduces the same identities and deterministic nested draws. | `NOT_AUDITED` | — |
| `THRESHOLD-338` | IV | 6234 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | KLL serialized artifacts and library version are retained because implementation randomness can affect reconstruction. | `NOT_AUDITED` | — |
| `REPORT-039` | IV | 6235 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Runtime tables record hardware, OS, runtime, and library versions. | `NOT_AUDITED` | — |
| `PROVENANCE-015` | IV | 6236 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Cross-machine timing comparisons are not made. | `NOT_AUDITED` | — |
| `PROVENANCE-016` | IV | 6237 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | Missing artifacts cannot be silently regenerated under a different protocol identity and treated as original evidence. | `NOT_AUDITED` | — |
| `CALIBRATION-248` | IV | 6241 | 20. Gate R — Reporting and claim-to-evidence integrity | The manuscript's confirmatory claim is supported only by Part II §5.1 and Part III §11. | `NOT_AUDITED` | — |
| `CALIBRATION-249` | IV | 6242 | 20. Gate R — Reporting and claim-to-evidence integrity | Supportive, mechanism, external, stress-test, boundary, operational, and exploratory evidence keeps its declared tier. | `NOT_AUDITED` | — |
| `CALIBRATION-250` | IV | 6243 | 20. Gate R — Reporting and claim-to-evidence integrity | A failed/null confirmatory endpoint is not rescued by CLUSTER_THRESHOLD, shrinkage, conformal, FedProx, Ditto, or an external dataset. | `NOT_AUDITED` | — |
| `METRIC-038` | IV | 6244 | 20. Gate R — Reporting and claim-to-evidence integrity | Operational FPR equity is not presented as demographic or protected-attribute fairness. | `NOT_AUDITED` | — |
| `REPORT-040` | IV | 6245 | 20. Gate R — Reporting and claim-to-evidence integrity | Structural raw-data locality is not called a formal privacy guarantee. | `NOT_AUDITED` | — |
| `THRESHOLD-339` | IV | 6246 | 20. Gate R — Reporting and claim-to-evidence integrity | Threshold-stage byte/runtime accounting is not called deployment validation. | `NOT_AUDITED` | — |
| `REPORT-041` | IV | 6247 | 20. Gate R — Reporting and claim-to-evidence integrity | No fleet-scale claim is made from synthetic or file-defined pseudo-clients. | `NOT_AUDITED` | — |
| `THRESHOLD-340` | IV | 6248 | 20. Gate R — Reporting and claim-to-evidence integrity | LOCAL_THRESHOLD/local thresholds are not claimed as universally novel; prior-art boundaries in Part I §10.D remain visible. | `NOT_AUDITED` | — |
| `CALIBRATION-251` | IV | 6249 | 20. Gate R — Reporting and claim-to-evidence integrity | The manuscript defines probability calibration, anomaly operating-point calibration, and conformal calibration according to Part I §10.C.7A and does not demand ECE/Brier/NLL for DATP's non-probabilistic threshold object. | `NOT_AUDITED` | — |
| `CALIBRATION-252` | IV | 6250 | 20. Gate R — Reporting and claim-to-evidence integrity | The manuscript explicitly states the Part I §3.2A honest/protocol-compliant calibration assumption and does not imply Byzantine, poisoning, secure-aggregation, authenticated-message, or adversarial-calibration robustness. | `NOT_AUDITED` | — |
| `CALIBRATION-253` | IV | 6251 | 20. Gate R — Reporting and claim-to-evidence integrity | The Part I §10.D.9B source-grounded prior-art distinction table is present, uses only the locked categorical vocabulary, and marks unsupported source facts as `NOT_REPORTED` rather than guessed values. | `NOT_AUDITED` | — |
| `REPORT-042` | IV | 6252 | 20. Gate R — Reporting and claim-to-evidence integrity | The submission-time novelty-survival literature gate in Part I §10.D.9A was executed within 14 calendar days of submission and both prior-art tables/citations were updated through that search date. | `NOT_AUDITED` | — |
| `REPORT-043` | IV | 6253 | 20. Gate R — Reporting and claim-to-evidence integrity | The historical moment-estimator sensitivity is reported as estimator-family robustness only and is not used to replace the q95 confirmatory endpoint. | `NOT_AUDITED` | — |
| `REPORT-044` | IV | 6254 | 20. Gate R — Reporting and claim-to-evidence integrity | Null, reversed, infeasible, and unfavorable seed-level evidence is retained in supplementary evidence where required. | `NOT_AUDITED` | — |
| `METRIC-039` | IV | 6255 | 20. Gate R — Reporting and claim-to-evidence integrity | Every headline table or figure has a traceable experiment and metric definition. | `NOT_AUDITED` | — |
| `SCORE-032` | IV | 6256 | 20. Gate R — Reporting and claim-to-evidence integrity | The mandatory causal intervention map preserves the fixed-score boundary and contains no outcome-to-calibration/training feedback arrow. | `NOT_AUDITED` | — |
| `STAT-035` | IV | 6257 | 20. Gate R — Reporting and claim-to-evidence integrity | The ten confirmatory paired seed deltas are shown individually with the arithmetic mean and locked BCa interval. | `NOT_AUDITED` | — |
| `DATASET-106` | IV | 6258 | 20. Gate R — Reporting and claim-to-evidence integrity | Both required equity–utility Pareto views and their target-attainment table are present when attack-sensitive N-BaIoT metrics are available. | `NOT_AUDITED` | — |
| `TRAIN-093` | IV | 6259 | 20. Gate R — Reporting and claim-to-evidence integrity | The FedProx mechanism figure reports terminal-50 drift rather than inferring mechanism activation from downstream performance alone. | `NOT_AUDITED` | — |
| `TRAIN-094` | IV | 6260 | 20. Gate R — Reporting and claim-to-evidence integrity | The manuscript explicitly qualifies the confirmatory regime as persistent identifiable IoT clients with full training participation and does not generalize to intermittent/unseen cross-device clients. | `NOT_AUDITED` | — |
| `METRIC-040` | IV | 6261 | 20. Gate R — Reporting and claim-to-evidence integrity | The headline confirmatory result includes the mandatory equity–utility/client-impact bundle rather than reporting `CV(FPR)` in isolation. | `NOT_AUDITED` | — |
| `TRAIN-095` | IV | 6262 | 20. Gate R — Reporting and claim-to-evidence integrity | `FEDAVG_LOCAL_FINE_TUNING` is identified as a bounded simple personalization stress test, not a new PFL contribution and not a replacement for Ditto. | `NOT_AUDITED` | — |
| `REPORT-045` | IV | 6263 | 20. Gate R — Reporting and claim-to-evidence integrity | The complete reproducibility-release bundle in §20A is generated in the appropriate `PUBLIC`, `BLINDED_ARCHIVE`, or `WITHHELD_LICENSE_RESTRICTED` state and its SHA-256 manifest validates. | `NOT_AUDITED` | — |
| `REPORT-046` | IV | 6292 | `ROADMAP_LOCK.md` | exact scientific-roadmap snapshot used for the reported campaign; | `NOT_AUDITED` | — |
| `PROVENANCE-017` | IV | 6293 | `ROADMAP_LOCK.md` | SHA-256 digest of that snapshot; | `NOT_AUDITED` | — |
| `PROVENANCE-018` | IV | 6294 | `ROADMAP_LOCK.md` | code commit/release identifier; | `NOT_AUDITED` | — |
| `GLOBAL-130` | IV | 6295 | `ROADMAP_LOCK.md` | submission-time literature-search date from Part I §10.D.9A. | `NOT_AUDITED` | — |
| `TRAIN-096` | IV | 6318 | `SEEDS.csv` | the exact ten confirmatory training seeds; | `NOT_AUDITED` | — |
| `GLOBAL-131` | IV | 6319 | `SEEDS.csv` | every declared nested/randomness purpose label; | `NOT_AUDITED` | — |
| `CALIBRATION-254` | IV | 6320 | `SEEDS.csv` | deterministic derivation inputs sufficient to reconstruct calibration subsamples, cluster repeats, KLL runs, fine-tuning batch order, and any other seeded nested operation; | `NOT_AUDITED` | — |
| `PROVENANCE-019` | IV | 6321 | `SEEDS.csv` | no seed may be regenerated from an undocumented process during reproduction. | `NOT_AUDITED` | — |
| `GLOBAL-132` | IV | 6327 | `SEEDS.csv` | official acquisition instructions/identifiers; | `NOT_AUDITED` | — |
| `GLOBAL-133` | IV | 6328 | `SEEDS.csv` | raw-file checksums where redistribution-independent checksums are lawful to publish; | `NOT_AUDITED` | — |
| `PROVENANCE-020` | IV | 6329 | `SEEDS.csv` | canonical processed-artifact checksums; | `NOT_AUDITED` | — |
| `CALIBRATION-255` | IV | 6330 | `SEEDS.csv` | ordered row-identity-set hashes for train/calibration/evaluation artifacts; | `NOT_AUDITED` | — |
| `DATASET-107` | IV | 6331 | `SEEDS.csv` | client membership counts and the deterministic population-construction manifest. | `NOT_AUDITED` | — |
| `PREPROCESS-056` | IV | 6339 | `SEEDS.csv` | fitted preprocessing-state artifacts and protocol identities; | `NOT_AUDITED` | — |
| `TRAIN-097` | IV | 6340 | `SEEDS.csv` | terminal round-200 model artifacts for each training condition/seed, including personalized client states where releasable; | `NOT_AUDITED` | — |
| `PREPROCESS-057` | IV | 6341 | `SEEDS.csv` | canonical calibration/evaluation score artifacts or, where source-data licensing prevents score redistribution, their exact ordered-row identities, hashes, generation command, and model/preprocessing hashes; | `NOT_AUDITED` | — |
| `CALIBRATION-256` | IV | 6342 | `SEEDS.csv` | every threshold output and its contributor/support metadata. | `NOT_AUDITED` | — |
| `METRIC-041` | IV | 6348 | `SEEDS.csv` | tidy seed×client×policy metric tables; | `NOT_AUDITED` | — |
| `GLOBAL-134` | IV | 6349 | `SEEDS.csv` | all ten confirmatory paired deltas; | `NOT_AUDITED` | — |
| `STAT-036` | IV | 6350 | `SEEDS.csv` | BCa bootstrap configuration and deterministic bootstrap seed material; | `NOT_AUDITED` | — |
| `STAT-037` | IV | 6351 | `SEEDS.csv` | Wilcoxon/sign-test/effect-size/multiplicity inputs and outputs; | `NOT_AUDITED` | — |
| `REPORT-047` | IV | 6352 | `SEEDS.csv` | the source-data table behind every manuscript figure and table; | `NOT_AUDITED` | — |
| `GLOBAL-135` | IV | 6353 | `SEEDS.csv` | typed unavailability states rather than silently dropped cells. | `NOT_AUDITED` | — |
| `PROVENANCE-021` | IV | 6393 | 21. Final publication-readiness gate | the anchor reproduction gate has the roadmap-defined outcome; | `NOT_AUDITED` | — |
| `BOUNDARY-011` | IV | 6394 | 21. Final publication-readiness gate | the ten-seed confirmatory campaign is complete or explicitly yields `CONFIRMATORY_INFERENCE_UNAVAILABLE` for a roadmap-valid reason; | `NOT_AUDITED` | — |
| `CALIBRATION-257` | IV | 6395 | 21. Final publication-readiness gate | every mandatory supportive/mechanism/stress/boundary experiment is complete or has a pre-specified infeasibility record; | `NOT_AUDITED` | — |
| `REPORT-048` | IV | 6396 | 21. Final publication-readiness gate | all causal-isolation and leakage gates pass for evidence used in claims; | `NOT_AUDITED` | — |
| `CALIBRATION-258` | IV | 6397 | 21. Final publication-readiness gate | all required metric and statistical audits pass, including exact sign-test, calibration-generalization-gap, `H_TAUTOLOGY` disjoint-row evidence, calibration-support-versus-burden, natural-device helped/harmed/support-stratum outputs, per-device direction-count, and leave-one-device-out influence outputs; | `NOT_AUDITED` | — |
| `REPORT-049` | IV | 6398 | 21. Final publication-readiness gate | the submission-time novelty-survival gate passes and the manuscript novelty wording matches the updated collision and source-grounded distinction tables; | `NOT_AUDITED` | — |
| `CALIBRATION-259` | IV | 6399 | 21. Final publication-readiness gate | the honest-calibration threat boundary is explicit and no result is mislabeled as adversarial/Byzantine calibration robustness; | `NOT_AUDITED` | — |
| `METRIC-042` | IV | 6400 | 21. Final publication-readiness gate | all expected unavailable metrics are distinguished from missing implementation; | `NOT_AUDITED` | — |
| `REPORT-050` | IV | 6401 | 21. Final publication-readiness gate | all required tables/figures can be reconstructed from retained evidence; | `NOT_AUDITED` | — |
| `PROVENANCE-022` | IV | 6402 | 21. Final publication-readiness gate | the §20A reproducibility-release bundle exists in the correct release state and every manifest SHA-256/byte-count validation passes; | `NOT_AUDITED` | — |
| `REPORT-051` | IV | 6403 | 21. Final publication-readiness gate | the claim-to-evidence audit passes without tier promotion; | `NOT_AUDITED` | — |
| `REPORT-052` | IV | 6404 | 21. Final publication-readiness gate | the final manuscript explicitly reports material negative evidence and accepted limitations. | `NOT_AUDITED` | — |

## 15. Source-coverage ledger

Every H2–H4 heading and numbered/named bold contract anchor through Part IV is represented below. **Anchor count: `301`.** This is the primary structural losslessness check.

| Source line | Part | Kind | Source anchor | Covered by matrix |
|---:|---|---|---|---|
| 5 | PREAMBLE | H2 | Purpose and structure | `YES` |
| 16 | PREAMBLE | H3 | Roadmap architecture and inheritance rule | `YES` |
| 22 | PREAMBLE | H3 | Restructure amendment | `YES` |
| 26 | PREAMBLE | H3 | Surgical strengthening amendment — 12 August 2026 | `YES` |
| 34 | PREAMBLE | H3 | Descriptive naming amendment | `YES` |
| 59 | I | H2 | Part I — Scientific Programme and Global Protocol Contracts | `YES` |
| 61 | I | H3 | 1. Programme identity | `YES` |
| 63 | I | BOLD | 1.1 Working title | `YES` |
| 67 | I | BOLD | 1.2 DATP-Core in one paragraph | `YES` |
| 87 | I | H3 | 2. Core causal contract | `YES` |
| 89 | I | BOLD | 2.1 Unit of causal comparison | `YES` |
| 108 | I | BOLD | 2.2 Fixed elements | `YES` |
| 129 | I | H3 | 2.2.1 Preprocessing and normalization lock | `YES` |
| 175 | I | H3 | 2.2.2 Fixed-score identity and serialization tolerance | `YES` |
| 185 | I | BOLD | 2.2.3 Empirical-quantile definition lock | `YES` |
| 211 | I | BOLD | 2.3 Sole manipulated variable | `YES` |
| 230 | I | BOLD | 2.4 Prohibited causal contamination | `YES` |
| 245 | I | H3 | 3. Calibration and evaluation contract | `YES` |
| 247 | I | BOLD | 3.1 Benign-only calibration | `YES` |
| 266 | I | BOLD | 3.2 Separation of calibration and evaluation | `YES` |
| 277 | I | BOLD | 3.2A Honest-calibration participant and message-integrity assumption | `YES` |
| 301 | I | BOLD | 3.3 Client eligibility | `YES` |
| 319 | I | BOLD | 3.3A Federation regime, client persistence, and deployment identity | `YES` |
| 356 | I | BOLD | 3.4 Meaning of “fairness” | `YES` |
| 380 | I | BOLD | 3.5 Primary operating-point concern | `YES` |
| 392 | I | BOLD | 3.6 Model-quality controls | `YES` |
| 415 | I | H3 | 4. Threshold-policy system | `YES` |
| 417 | I | BOLD | 4.1 Centralized reference: CENTRALIZED_REFERENCE | `YES` |
| 433 | I | BOLD | 4.2 Shared threshold: SHARED_THRESHOLD | `YES` |
| 449 | I | BOLD | 4.3 Local threshold: LOCAL_THRESHOLD | `YES` |
| 463 | I | BOLD | 4.4 Family threshold: FAMILY_THRESHOLD | `YES` |
| 480 | I | BOLD | 4.5 Cluster threshold: CLUSTER_THRESHOLD | `YES` |
| 513 | I | BOLD | 4.6 Ladder interpretation | `YES` |
| 530 | I | H3 | 5. Supportive threshold variants | `YES` |
| 536 | I | BOLD | 5.1 Quantile sensitivity | `YES` |
| 548 | I | BOLD | 5.1A Historical mean-plus-standard-deviation estimator sensitivity | `YES` |
| 602 | I | BOLD | 5.2 Local–global shrinkage | `YES` |
| 647 | I | BOLD | 5.3 Calibration-size-aware shrinkage | `YES` |
| 669 | I | BOLD | 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD | `YES` |
| 697 | I | H3 | 6. Federated threshold comparator | `YES` |
| 699 | I | BOLD | 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | `YES` |
| 718 | I | BOLD | 6.1A `FEDERATED_KLL_SHARED_THRESHOLD` | `YES` |
| 758 | I | BOLD | 6.2 Relationship to Laridi et al. | `YES` |
| 775 | I | H3 | 7. Training-side stress tests | `YES` |
| 781 | I | BOLD | 7.1 FedProx | `YES` |
| 809 | I | BOLD | 7.1A FedProx mechanism-activation diagnostics | `YES` |
| 865 | I | BOLD | 7.2 Ditto | `YES` |
| 898 | I | BOLD | 7.2A Post-FedAvg client-local fine-tuning stress test | `YES` |
| 956 | I | BOLD | 7.2B Common model-side score-alignment and threshold-absorption diagnostics | `YES` |
| 1107 | I | BOLD | 7.3 Fallback naming | `YES` |
| 1120 | I | BOLD | 7.4 Separation from the core ladder | `YES` |
| 1132 | I | H3 | 8. Evidence architecture | `YES` |
| 1134 | I | BOLD | 8.1 Sole confirmatory evidence | `YES` |
| 1146 | I | BOLD | 8.2 Supporting evidence families | `YES` |
| 1171 | I | BOLD | 8.3 Honest negative evidence | `YES` |
| 1177 | I | H3 | 9. Dataset and population boundaries | `YES` |
| 1181 | I | BOLD | 9.1 N-BaIoT physical-device anchor | `YES` |
| 1195 | I | BOLD | 9.2 CICIoT2023 available-data boundary | `YES` |
| 1216 | I | BOLD | 9.3 Controlled heterogeneity population | `YES` |
| 1224 | I | BOLD | 9.4 Edge-IIoTset external validation | `YES` |
| 1244 | I | BOLD | 9.5 Temporal external population | `YES` |
| 1259 | I | BOLD | 9.6 Dataset expansion limit | `YES` |
| 1269 | I | BOLD | 9.7 Heterogeneity taxonomy and claim boundary | `YES` |
| 1298 | I | H3 | 10. Scope, terminology, claim boundaries, and accepted limitations | `YES` |
| 1302 | I | H4 | 10.A Included scientific scope | `YES` |
| 1306 | I | BOLD | 10.A.1 External validation | `YES` |
| 1310 | I | BOLD | 10.A.2 Federated threshold comparison | `YES` |
| 1314 | I | BOLD | 10.A.3 Training-side robustness | `YES` |
| 1324 | I | BOLD | 10.A.4 Threshold-estimation depth | `YES` |
| 1334 | I | BOLD | 10.A.5 Temporal boundary | `YES` |
| 1338 | I | BOLD | 10.A.6 Mechanism analysis | `YES` |
| 1351 | I | BOLD | 10.A.7 Hard scope limits | `YES` |
| 1370 | I | H4 | 10.B Excluded scientific scope | `YES` |
| 1372 | I | BOLD | 10.B.1 Security attacks and defenses | `YES` |
| 1378 | I | BOLD | 10.B.2 Formal privacy | `YES` |
| 1388 | I | BOLD | 10.B.3 Deployment validation | `YES` |
| 1394 | I | BOLD | 10.B.4 Fleet scale | `YES` |
| 1400 | I | BOLD | 10.B.5 Full drift handling | `YES` |
| 1404 | I | BOLD | 10.B.6 Broad FL benchmarking | `YES` |
| 1410 | I | BOLD | 10.B.7 Federated conformal breadth | `YES` |
| 1418 | I | BOLD | 10.B.10 Explicit non-expansion guardrails for this amendment | `YES` |
| 1436 | I | H4 | 10.C Terminology and naming rules | `YES` |
| 1438 | I | BOLD | 10.C.1 Project naming | `YES` |
| 1466 | I | BOLD | 10.C.2 Threshold-policy identifiers | `YES` |
| 1488 | I | BOLD | 10.C.3 Threshold-variant identifiers | `YES` |
| 1502 | I | BOLD | 10.C.4 Laridi naming | `YES` |
| 1522 | I | BOLD | 10.C.5 Personalized-model naming | `YES` |
| 1543 | I | BOLD | 10.C.5A Simple local-fine-tuning naming | `YES` |
| 1547 | I | BOLD | 10.C.6 Population identifiers | `YES` |
| 1567 | I | BOLD | 10.C.7 Statistical and equity language | `YES` |
| 1593 | I | BOLD | 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use | `YES` |
| 1609 | I | BOLD | 10.C.8 Novelty language | `YES` |
| 1627 | I | H4 | 10.D Claim-level framing boundaries | `YES` |
| 1631 | I | BOLD | 10.D.1 Permitted central framing | `YES` |
| 1641 | I | BOLD | 10.D.2 Prohibited central framing | `YES` |
| 1656 | I | BOLD | 10.D.3 AUROC language | `YES` |
| 1668 | I | BOLD | 10.D.4 Macro-F1 language | `YES` |
| 1680 | I | BOLD | 10.D.5 External validation language | `YES` |
| 1692 | I | BOLD | 10.D.6 Temporal language | `YES` |
| 1702 | I | BOLD | 10.D.7 Privacy language | `YES` |
| 1712 | I | BOLD | 10.D.8 Deployment language | `YES` |
| 1726 | I | BOLD | 10.D.9 Novelty boundary and mandatory prior-art audit | `YES` |
| 1800 | I | BOLD | 10.D.9A Submission-time novelty-survival literature gate | `YES` |
| 1835 | I | BOLD | 10.D.9B Mandatory source-grounded prior-art distinction table | `YES` |
| 1888 | I | BOLD | 10.D.10 Claim-survival rules | `YES` |
| 1903 | I | BOLD | 10.D.11 Negative evidence that must remain publishable | `YES` |
| 1925 | I | H4 | 10.E Accepted scientific limitations | `YES` |
| 1929 | I | BOLD | 10.E.1 Small natural client population | `YES` |
| 1935 | I | BOLD | 10.E.2 One external dataset | `YES` |
| 1939 | I | BOLD | 10.E.3 Incomplete external attack assignment | `YES` |
| 1943 | I | BOLD | 10.E.4 Single temporal family | `YES` |
| 1947 | I | BOLD | 10.E.5 No formal privacy guarantee | `YES` |
| 1951 | I | BOLD | 10.E.6 No hardware evidence | `YES` |
| 1955 | I | BOLD | 10.E.7 Threshold trade-offs | `YES` |
| 1959 | I | BOLD | 10.E.8 Comparator incompleteness | `YES` |
| 1963 | I | BOLD | 10.E.9 Conformal limitation | `YES` |
| 1967 | I | BOLD | 10.E.10 Honest-calibration / no Byzantine-integrity guarantee | `YES` |
| 1971 | I | BOLD | 10.E.11 Persistent identifiable-client limitation | `YES` |
| 1977 | I | H3 | 11. Numerical and formula navigation ledger | `YES` |
| 2014 | I | H3 | 12. Protocol ownership and inheritance map | `YES` |
| 2037 | II | H2 | Part II — Experiment Programme and Decision Rules | `YES` |
| 2041 | II | H3 | 0. Master experiment index | `YES` |
| 2085 | II | H3 | 1. How to read this catalogue | `YES` |
| 2087 | II | BOLD | 1.1 Evidence-role vocabulary | `YES` |
| 2115 | II | BOLD | 1.2 Experiment specification format | `YES` |
| 2137 | II | H3 | 2. Protocol inheritance and experiment-wide execution additions | `YES` |
| 2141 | II | BOLD | 2.1 Fixed-detector causal isolation — inherited | `YES` |
| 2145 | II | BOLD | 2.2 Benign-only threshold calibration — inherited | `YES` |
| 2149 | II | BOLD | 2.3 Paired experimental design — inherited | `YES` |
| 2153 | II | BOLD | 2.3A Deterministic nested-randomness contract | `YES` |
| 2175 | II | BOLD | 2.4 Eligibility — inherited | `YES` |
| 2179 | II | BOLD | 2.5 Terminal scientific-model discipline — inherited | `YES` |
| 2183 | II | BOLD | 2.6 Negative-result discipline | `YES` |
| 2187 | II | BOLD | 2.7 Manuscript evidence narrative | `YES` |
| 2196 | II | BOLD | 2.7A Three competing explanations that the programme must eliminate or bound | `YES` |
| 2208 | II | BOLD | 2.8 Reviewer-objection → experiment coverage | `YES` |
| 2238 | II | H3 | 3. Method crosswalk — definitions are owned by Part I | `YES` |
| 2263 | II | H3 | 4. Dataset populations and evaluation settings | `YES` |
| 2265 | II | BOLD | 4.0 Population capability and claim-boundary table | `YES` |
| 2279 | II | BOLD | 4.1 NBAIOT_NATURAL_DEVICES — N-BaIoT physical-device anchor | `YES` |
| 2317 | II | BOLD | 4.2 CICIOT_FILE_CLIENTS — CICIoT2023 file-defined applicability boundary | `YES` |
| 2354 | II | BOLD | 4.3 NBAIOT_DIRICHLET_CLIENTS — controlled N-BaIoT heterogeneity sweep | `YES` |
| 2391 | II | BOLD | 4.4 EDGE_SENSOR_CLIENTS — Edge-IIoTset external benign-equity validation | `YES` |
| 2464 | II | BOLD | 4.5 EDGE_TEMPORAL_CLIENTS — Edge-IIoTset one-shot recalibration boundary | `YES` |
| 2510 | II | H3 | 5. Confirmatory experiment | `YES` |
| 2512 | II | BOLD | 5.1 NBAIOT_NATURAL_DEVICES shared-versus-local threshold-scope confirmation | `YES` |
| 2627 | II | BOLD | 5.2 Anchor reproduction gate | `YES` |
| 2664 | II | BOLD | `ANCHOR_REPRODUCTION_FAILED` | `YES` |
| 2683 | II | BOLD | 5.3 Confirmatory inference unavailable | `YES` |
| 2706 | II | H3 | 6. Supportive robustness experiments | `YES` |
| 2708 | II | BOLD | 6.1 Shared-threshold construction sensitivity | `YES` |
| 2754 | II | BOLD | 6.2 Quantile-level sensitivity | `YES` |
| 2786 | II | BOLD | 6.2A Threshold-estimator × scope sensitivity | `YES` |
| 2858 | II | BOLD | 6.3 Controlled non-IID severity | `YES` |
| 2921 | II | H3 | 7. Cluster and family mechanism programme | `YES` |
| 2923 | II | BOLD | 7.1 Threshold-sharing granularity and cluster stability | `YES` |
| 3032 | II | BOLD | 7.2A Physical-family explanatory adequacy | `YES` |
| 3074 | II | BOLD | 7.3 Per-client score-distribution explanation | `YES` |
| 3104 | II | BOLD | 7.4 Heterogeneity–benefit association and decision surface | `YES` |
| 3244 | II | BOLD | 7.5 Threshold movement versus operating-point harm | `YES` |
| 3302 | II | BOLD | 7.5A Calibration support versus shared-threshold burden | `YES` |
| 3366 | II | BOLD | 7.5B Natural-device helped/harmed profile and calibration-support stratification | `YES` |
| 3513 | II | BOLD | 7.6 N-BaIoT malware-family sensitivity breakdown | `YES` |
| 3558 | II | BOLD | 7.7 Equity–utility Pareto analysis | `YES` |
| 3604 | II | H3 | 8. Calibration robustness programme | `YES` |
| 3606 | II | BOLD | 8.1 Calibration-size ablation | `YES` |
| 3719 | II | BOLD | 8.1A Calibration cold-start / onboarding boundary | `YES` |
| 3755 | II | BOLD | 8.2 Fixed local–global shrinkage | `YES` |
| 3787 | II | BOLD | 8.3 Calibration-size-aware shrinkage | `YES` |
| 3805 | II | BOLD | 8.4 Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | `YES` |
| 3846 | II | BOLD | 8.5 Bounded preprocessing-geometry sensitivity | `YES` |
| 3897 | II | BOLD | 8.6 Shared-calibration contributor availability sensitivity | `YES` |
| 3990 | II | H3 | 9. Federated threshold-estimation programme | `YES` |
| 3992 | II | BOLD | 9.1 Benign summary-statistics comparator | `YES` |
| 4057 | II | BOLD | 9.2 KLL federated quantile-sketch shared threshold | `YES` |
| 4114 | II | BOLD | 9.3 Fixed-coefficient Laridi sensitivity | `YES` |
| 4130 | II | H3 | 10. External validation and applicability boundaries | `YES` |
| 4132 | II | BOLD | 10.1 Edge-IIoTset external benign-equity validation | `YES` |
| 4195 | II | BOLD | 10.2 CICIoT2023 file-level boundary | `YES` |
| 4219 | II | H3 | 11. Training-side stress tests | `YES` |
| 4221 | II | BOLD | 11.0 Upstream alternative-hypothesis ladder | `YES` |
| 4244 | II | BOLD | 11.1 FedProx aggregation stress test | `YES` |
| 4320 | II | BOLD | 11.2 Ditto model-personalization stress test | `YES` |
| 4430 | II | BOLD | 11.2A FedAvg post-training client-local fine-tuning stress test | `YES` |
| 4502 | II | H3 | 12. Temporal recalibration experiment | `YES` |
| 4504 | II | BOLD | 12.1 One-shot recalibration under genuine chronology | `YES` |
| 4647 | II | H3 | 13. Operational translation | `YES` |
| 4649 | II | BOLD | 13.1 Alert-burden experiment | `YES` |
| 4694 | II | BOLD | 13.2 Threshold-stage communication, storage, and runtime accounting | `YES` |
| 4738 | II | H3 | 14. Optional high-value analyses | `YES` |
| 4742 | II | BOLD | 14.1 Robust cluster-median threshold | `YES` |
| 4756 | II | BOLD | 14.2 Additional equity indices | `YES` |
| 4769 | II | BOLD | 14.3 Extended secondary uncertainty | `YES` |
| 4780 | III | H2 | Part III — Evaluation, Statistical Analysis, and Reporting | `YES` |
| 4784 | III | H3 | 1. Evaluation contract | `YES` |
| 4786 | III | BOLD | 1.1 Fixed-score comparison — inherited contract | `YES` |
| 4790 | III | BOLD | 1.2 Independent unit | `YES` |
| 4798 | III | BOLD | 1.3 Per-client-first reporting | `YES` |
| 4806 | III | H3 | 2. Prediction and confusion counts | `YES` |
| 4836 | III | H3 | 3. Metric populations | `YES` |
| 4838 | III | BOLD | 3.1 Calibration eligibility — inherited contract | `YES` |
| 4842 | III | BOLD | 3.2 FPR-evaluable population | `YES` |
| 4846 | III | BOLD | 3.3 Attack-evaluable population | `YES` |
| 4858 | III | BOLD | 3.4 Coverage | `YES` |
| 4872 | III | H3 | 4. Per-client metrics | `YES` |
| 4874 | III | BOLD | 4.1 False-positive rate | `YES` |
| 4884 | III | BOLD | 4.2 True-positive rate | `YES` |
| 4894 | III | BOLD | 4.3 Balanced accuracy | `YES` |
| 4904 | III | BOLD | 4.4 Per-client Macro-F1 | `YES` |
| 4922 | III | BOLD | 4.5 AUROC | `YES` |
| 4930 | III | BOLD | 4.6 Average precision / PR-curve summary | `YES` |
| 4942 | III | BOLD | 4.7 Held-out benign target-attainment error | `YES` |
| 4975 | III | BOLD | 4.8 Calibration-to-held-out benign generalization gap | `YES` |
| 5015 | III | BOLD | 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR | `YES` |
| 5071 | III | H3 | 5. Cross-client operating-point metrics | `YES` |
| 5075 | III | BOLD | 5.1 Mean FPR | `YES` |
| 5086 | III | BOLD | 5.2 Sample standard deviation | `YES` |
| 5111 | III | BOLD | 5.3 Coefficient of variation | `YES` |
| 5131 | III | BOLD | 5.4 Absolute dispersion | `YES` |
| 5151 | III | BOLD | 5.5 TPR and lower-tail metrics | `YES` |
| 5180 | III | H3 | 6. Optional equity metrics | `YES` |
| 5184 | III | BOLD | 6.1 Jain index | `YES` |
| 5198 | III | BOLD | 6.2 Gini coefficient | `YES` |
| 5212 | III | BOLD | 6.3 Cluster dispersion | `YES` |
| 5227 | III | BOLD | 5.6 Natural-device help/harm summary semantics | `YES` |
| 5254 | III | H3 | 7. Aggregate model-quality controls | `YES` |
| 5256 | III | BOLD | 7.1 Mean client Macro-F1 | `YES` |
| 5267 | III | BOLD | 7.2 Pooled Macro-F1 | `YES` |
| 5277 | III | BOLD | 7.3 Mean client balanced accuracy | `YES` |
| 5290 | III | H3 | 8. Threshold-estimation metrics | `YES` |
| 5292 | III | BOLD | 8.1 Centralized oracle | `YES` |
| 5298 | III | BOLD | 8.2 Threshold error | `YES` |
| 5318 | III | BOLD | 8.3 Target attainment | `YES` |
| 5340 | III | BOLD | 8.4 Threshold variance and sample efficiency | `YES` |
| 5377 | III | H3 | 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics | `YES` |
| 5386 | III | BOLD | 9.1 Global mean | `YES` |
| 5398 | III | BOLD | 9.2 Full pooled variance | `YES` |
| 5426 | III | BOLD | 9.3 Between ratio | `YES` |
| 5440 | III | H3 | 10. Operational metrics | `YES` |
| 5442 | III | BOLD | 10.1 Alert burden | `YES` |
| 5458 | III | BOLD | 10.2 Threshold-stage communication | `YES` |
| 5471 | III | BOLD | 10.3 Threshold-stage latency and memory | `YES` |
| 5475 | III | BOLD | 10.4 Ditto incremental state and compute | `YES` |
| 5488 | III | H3 | 11. Confirmatory statistical analysis | `YES` |
| 5490 | III | BOLD | 11.1 Paired contrast | `YES` |
| 5513 | III | BOLD | 11.1A Relative and robustness-oriented descriptive effect sizes | `YES` |
| 5540 | III | BOLD | 11.2 BCa confidence interval | `YES` |
| 5546 | III | BOLD | 11.3 Degenerate BCa | `YES` |
| 5555 | III | BOLD | 11.4 Sign consistency | `YES` |
| 5573 | III | H3 | 12. Secondary statistical evidence | `YES` |
| 5575 | III | BOLD | 12.1A Exact paired sign test | `YES` |
| 5599 | III | BOLD | 12.1 Wilcoxon signed-rank | `YES` |
| 5610 | III | BOLD | 12.2 Matched-pairs rank-biserial correlation | `YES` |
| 5618 | III | BOLD | 12.3 Secondary confidence intervals | `YES` |
| 5622 | III | BOLD | 12.4 Multiplicity | `YES` |
| 5635 | III | BOLD | 12.5 Nested replicates | `YES` |
| 5644 | III | BOLD | 12.6 Association analyses | `YES` |
| 5657 | III | BOLD | 12.7 Cluster stability | `YES` |
| 5663 | III | H3 | 13. Terminal scientific-model protocol | `YES` |
| 5665 | III | BOLD | 13.1 Terminal detector | `YES` |
| 5669 | III | BOLD | 13.2 Recovery and diagnostic checkpoints | `YES` |
| 5673 | III | BOLD | 13.3 Fixed-detector restrictions | `YES` |
| 5677 | III | H3 | 14. Temporal recalibration quantities | `YES` |
| 5723 | III | BOLD | 14.1 Client-level temporal diagnostics | `YES` |
| 5743 | III | H3 | 15. Precision and selection discipline | `YES` |
| 5745 | III | BOLD | 15.1 Locked ten-seed precision diagnostics | `YES` |
| 5783 | III | BOLD | 15.1A Leave-one-device-out influence for the natural-device confirmatory effect | `YES` |
| 5846 | III | BOLD | 15.2 Numerical and selection discipline | `YES` |
| 5862 | III | H3 | 16. Mandatory manuscript-facing figures and synthesis tables | `YES` |
| 5866 | III | BOLD | 16.1 Causal intervention map — mandatory main-text figure | `YES` |
| 5898 | III | BOLD | 16.2 Confirmatory paired-effect view — mandatory main-text figure | `YES` |
| 5908 | III | BOLD | 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table | `YES` |
| 5928 | III | BOLD | 16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure | `YES` |
| 5932 | III | BOLD | 16.4 FedProx mechanism-activation view — mandatory stress-test figure | `YES` |
| 5936 | III | BOLD | 16.5 Mandatory synthesis tables | `YES` |
| 5949 | IV | H2 | Part IV — Development, Reproducibility, and Audit Contract | `YES` |
| 5951 | IV | H3 | 1. Purpose and audit semantics | `YES` |
| 5972 | IV | H3 | 2. Audit object identity | `YES` |
| 5992 | IV | H3 | 3. Gate A — Roadmap and configuration integrity | `YES` |
| 6007 | IV | H3 | 4. Gate B — Dataset integrity | `YES` |
| 6021 | IV | H3 | 5. Gate C — Population and client integrity | `YES` |
| 6035 | IV | H3 | 6. Gate D — Split, chronology, and eligibility integrity | `YES` |
| 6048 | IV | H3 | 7. Gate E — Preprocessing integrity | `YES` |
| 6059 | IV | H3 | 8. Gate F — Training and terminal-detector integrity | `YES` |
| 6076 | IV | H3 | 9. Gate G — Fixed-score and scoring integrity | `YES` |
| 6087 | IV | H3 | 10. Gate H — Calibration integrity | `YES` |
| 6102 | IV | H3 | 11. Gate I — Threshold-policy integrity | `YES` |
| 6125 | IV | H3 | 12. Gate J — Comparator and threshold-variant integrity | `YES` |
| 6139 | IV | H3 | 13. Gate K — Experiment completeness | `YES` |
| 6153 | IV | H3 | 14. Gate L — Evaluation and metric integrity | `YES` |
| 6168 | IV | H3 | 15. Gate M — Statistical integrity | `YES` |
| 6185 | IV | H3 | 16. Gate N — Mechanism-analysis integrity | `YES` |
| 6209 | IV | H3 | 17. Gate O — External and boundary evidence integrity | `YES` |
| 6218 | IV | H3 | 18. Gate P — Temporal integrity | `YES` |
| 6228 | IV | H3 | 19. Gate Q — Artifact, provenance, and deterministic reconstruction integrity | `YES` |
| 6239 | IV | H3 | 20. Gate R — Reporting and claim-to-evidence integrity | `YES` |
| 6265 | IV | H3 | 20A. Reproducibility-release bundle | `YES` |
| 6290 | IV | BOLD | `ROADMAP_LOCK.md` | `YES` |
| 6297 | IV | BOLD | `MANIFEST_SHA256.csv` | `YES` |
| 6316 | IV | BOLD | `SEEDS.csv` | `YES` |
| 6389 | IV | H3 | 21. Final publication-readiness gate | `YES` |

## 15A. Prose-only semantic contract sentinel register

**Purpose:** close every prose-like semantic statement through Part IV that is not already reproduced verbatim elsewhere in the matrix. **Sentinel count: `911`.** This captures positive definitions, interpretation rules, claim boundaries, protocol prose, and implementation constraints that list/formula/table extraction alone can miss. A sentinel may be closed only by (a) mapping it to one or more existing executable/claim/reporting atomic rows that fully realize the statement, or (b) creating a new atomic repository-audit row. It may not be dismissed merely because its section heading is already covered.

**Closure rule for every sentinel:** identify its executable, claim, interpretation, or reporting owner; map the exact implementing symbol or downstream control; prove runtime/static reachability as required; retain tests/evidence; and assign one scientific audit outcome. If the source statement is genuinely contextual/rationale-only, mark `NOT_APPLICABLE` with a retained justification instead of silently skipping it.

- [ ] `PROSE-SENTINEL-0001` — source line `3` — **PREAMBLE**
  > **Working title:** *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection (Journal Extension).*
- [ ] `PROSE-SENTINEL-0002` — source line `7` — **Purpose and structure**
  > This roadmap is the authoritative DATP-Core research contract. It deliberately serves four linked purposes without mixing their ownership:
- [ ] `PROSE-SENTINEL-0003` — source line `14` — **Purpose and structure**
  > The study asks whether the scope of benign threshold calibration changes the distribution of false-positive burden across heterogeneous federated IoT clients while the detector is held fixed. The confirmatory comparison is shared versus per-client threshold calibration on the N-BaIoT natural-device population; all other studies provide supportive, mechanism, stress-test, external, operational, or boundary evidence.
- [ ] `PROSE-SENTINEL-0004` — source line `18` — **Purpose and structure / Roadmap architecture and inheritance rule**
  > **Define once, inherit everywhere.** Each scientific or engineering rule has one authoritative owner. Experiments inherit all applicable global contracts unless they explicitly declare a deviation. Experiment sections therefore describe their scientific delta rather than restating the whole pipeline.
- [ ] `PROSE-SENTINEL-0005` — source line `20` — **Purpose and structure / Roadmap architecture and inheritance rule**
  > This inheritance rule is a deduplication rule, **not a relaxation rule**. A referenced contract remains fully mandatory. If an implementation or experiment must differ, the deviation must receive an explicit protocol identity and be recorded before outcome inspection.
- [ ] `PROSE-SENTINEL-0006` — source line `24` — **Purpose and structure / Restructure amendment**
  > This version restructures the previous master roadmap without narrowing the scientific programme. Detailed experiment procedures, locked grids, formulas, metric semantics, negative-result rules, and audit-critical implementation constraints are retained. True duplicate method definitions and repeated global invariants are consolidated into authoritative contracts and cross-references. Research citations are defined once in Appendix A.
- [ ] `PROSE-SENTINEL-0007` — source line `28` — **Purpose and structure / Surgical strengthening amendment — 12 August 2026**
  > This amendment preserves every existing scientific contract and adds only bounded reviewer-critical strengthening: a fixed-score historical estimator-by-scope sensitivity, natural-device influence diagnostics, calibration-to-held-out generalization metrics, exact seed-sign robustness reporting, normalized model-personalization absorption, promotion of all mandatory shared-threshold constructions into the main robustness panel, a current-literature novelty-survival gate, FedProx mechanism-activation diagnostics, an exhaustive calibration-contributor-availability sensitivity, an explicit four-axis threshold/personalization taxonomy, a population-capability summary, and mandatory causal/equity-utility reporting views. It additionally locks a protocol-compliant/honest calibration-participant assumption for the whole threshold programme, distinguishes anomaly operating-point calibration from probability and conformal calibration, makes the calibration pooling bias–variance hypothesis explicit, adds a calibration-support-versus-client-burden mechanism diagnostic and exact per-device direction counts, strengthens the prior-art distinction schema, and incorporates current 2026 calibrated-IoT/Byzantine-calibration collision literature.
- [ ] `PROSE-SENTINEL-0008` — source line `30` — **Purpose and structure / Surgical strengthening amendment — 12 August 2026**
  > A second bounded strengthening pass on the same date makes the **deployment/federation regime explicit**, adds one simple post-FedAvg client-local fine-tuning stress condition, standardizes model-side absorption diagnostics across FedProx/fine-tuning/Ditto, adds a complete natural-device helped/harmed profile with prospectively fixed support strata, makes the held-out rebuttal to the “local q95 is equalized by construction” objection explicit, converts the existing heterogeneity/support surface into a typed descriptive policy surface rather than a learned selector, and adds a submission-grade reproducibility-release bundle. These additions do **not** change the sole confirmatory endpoint, do not add another dataset, do not create a PFL benchmark zoo, and do not authorize post-hoc model or threshold selection.
- [ ] `PROSE-SENTINEL-0009` — source line `32` — **Purpose and structure / Surgical strengthening amendment — 12 August 2026**
  > It does **not** add a new dataset, a broad FL-algorithm zoo, a threshold-estimator zoo, formal privacy experiments, attack experiments, hardware deployment, sequential majority-vote alerting, or a broader conformal-prediction programme.
- [ ] `PROSE-SENTINEL-0010` — source line `36` — **Purpose and structure / Descriptive naming amendment**
  > This version also removes opaque letter/number aliases from the active scientific vocabulary. Threshold policies, comparators, and dataset populations are named by what they **do** or **contain**, so the roadmap, implementation, audit outputs, tables, and manuscript can be read without decoding shorthand.
- [ ] `PROSE-SENTINEL-0011` — source line `38` — **Purpose and structure / Descriptive naming amendment**
  > The active identifiers are descriptive and stable:
- [ ] `PROSE-SENTINEL-0012` — source line `57` — **Purpose and structure / Descriptive naming amendment**
  > Opaque B-number aliases and lettered population aliases are retired from active use. They must not appear in new code-facing enums, manifests, experiment identifiers, tables, figures, audit outputs, or manuscript prose. Historical artifacts may retain old labels only as immutable provenance; they must be translated to the descriptive identity at the ingestion boundary rather than propagated.
- [ ] `PROSE-SENTINEL-0013` — source line `65` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.1 Working title**
  > *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.*
- [ ] `PROSE-SENTINEL-0014` — source line `69` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > DATP-Core is a controlled study of **threshold-calibration scope** in federated IoT anomaly detection.
- [ ] `PROSE-SENTINEL-0015` — source line `71` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > For each seed and dataset population, a federated autoencoder is trained to one fixed terminal scientific model under one locked training protocol. The terminal detector is fixed before score generation. Compared policies consume the same execution-scoped per-client calibration and test-score evidence. The ladder changes only the scope at which a benign anomaly threshold is estimated: one shared threshold, one threshold per physical-device family, one threshold per data-driven client cluster, or one threshold per client.
- [ ] `PROSE-SENTINEL-0016` — source line `73` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > The scientific question is therefore not:
- [ ] `PROSE-SENTINEL-0017` — source line `77` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > It is:
- [ ] `PROSE-SENTINEL-0018` — source line `81` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > The primary object of interest is cross-client false-positive-rate dispersion. Model discrimination, including AUROC, remains a control rather than the thresholding verdict.
- [ ] `PROSE-SENTINEL-0019` — source line `83` — **Part I — Scientific Programme and Global Protocol Contracts / 1. Programme identity / 1.2 DATP-Core in one paragraph**
  > **Current empirical motivation.** Recent federated IoT/IoMT anomaly-detection evidence independently reinforces the distinction between discrimination and deployment operating point. Robalino-Díaz et al. report a FedAvg model with `AUC-ROC = 0.995` but overall `Recall = 0.530`, with IoMT recall falling to `0.290` under a fixed `0.5` decision threshold; post-hoc calibration materially changes that operating behavior.[^robalino2026] DATP-Core does not reproduce that probabilistic-calibration experiment. It uses the result only as external motivation for treating AUROC as insufficient to characterize a deployed thresholded detector.
- [ ] `PROSE-SENTINEL-0020` — source line `91` — **Part I — Scientific Programme and Global Protocol Contracts / 2. Core causal contract / 2.1 Unit of causal comparison**
  > The controlled comparison is performed within a seed, population, and frozen detector.
- [ ] `PROSE-SENTINEL-0021` — source line `93` — **Part I — Scientific Programme and Global Protocol Contracts / 2. Core causal contract / 2.1 Unit of causal comparison**
  > The core threshold policies must receive:
- [ ] `PROSE-SENTINEL-0022` — source line `106` — **Part I — Scientific Programme and Global Protocol Contracts / 2. Core causal contract / 2.1 Unit of causal comparison**
  > Only threshold-calibration scope may differ.
- [ ] `PROSE-SENTINEL-0023` — source line `110` — **Part I — Scientific Programme and Global Protocol Contracts / 2. Core causal contract / 2.2 Fixed elements**
  > Within a core dataset ladder, the following remain fixed:
- [ ] `PROSE-SENTINEL-0024` — source line `127` — **Part I — Scientific Programme and Global Protocol Contracts / 2. Core causal contract / 2.2 Fixed elements**
  > The fixed-detector rule applies **within each population and training baseline**. It does not mean that the same numerical model parameters are reused across different datasets with incompatible feature spaces.
- [ ] `PROSE-SENTINEL-0025` — source line `131` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock**
  > Preprocessing is part of the fixed detector state. Within a seed, population, training baseline, and **named preprocessing protocol identity**, every compared threshold policy reuses one fitted preprocessing state. Threshold methods never select, refit, or alter preprocessing. Distinct protocol identities must never be mixed silently within one confirmatory ladder.
- [ ] `PROSE-SENTINEL-0026` — source line `133` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock**
  > **Primary confirmatory federated method** (`FEDERATED_CLIENT_LOCAL_STANDARD`):
- [ ] `PROSE-SENTINEL-0027` — source line `143` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock**
  > **Rationale.** The conference DATP reproducibility specification locks **per-client StandardScaler** for model-input normalization. The recovered anchor implementation stores one scaler per device fitted on benign train only. Meidan et al. leave scaling unspecified; the paper’s reproducibility table and the historical DATP artifact path supply the confirmatory lock for the N-BaIoT natural-device ladder. Cluster-threshold **fingerprint** standardization remains a separate score-side `StandardScaler` contract and is not model-input preprocessing.
- [ ] `PROSE-SENTINEL-0028` — source line `151` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock / Supportive federated method** (`FEDERATED_POOLED_MIN_MAX`) — **not confirmatory:**
  > Successor N-BaIoT federated-AE work often uses global/collaborative min–max for a shared detector. That geometry may be used only under its own protocol identity and claim tier (supportive / mechanism). It must not replace the confirmatory client-local StandardScaler ladder without an explicit claim-tier change.
- [ ] `PROSE-SENTINEL-0029` — source line `153` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock / Supportive federated method** (`FEDERATED_POOLED_MIN_MAX`) — **not confirmatory:**
  > **Centralized-reference scientific method** (`CENTRALIZED_POOLED_MIN_MAX`):
- [ ] `PROSE-SENTINEL-0030` — source line `171` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock / Missing-value and non-finite policy (all datasets):**
  > **Excluded for multi-feature confirmatory AE input:** identity (no scaling) transforms.
- [ ] `PROSE-SENTINEL-0031` — source line `173` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.1 Preprocessing and normalization lock / Missing-value and non-finite policy (all datasets):**
  > These locks are prospective research amendments that complete the fixed-detector contract. Confirmatory client-local StandardScaler is paper-and-anchor backed; pooled MinMax is a declared supportive alternative from successor FL literature, not the confirmatory default.
- [ ] `PROSE-SENTINEL-0032` — source line `177` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance**
  > Two distinct notions of score equality apply within DATP-Core and must never be conflated.
- [ ] `PROSE-SENTINEL-0033` — source line `179` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance**
  > **Scientific fixed-score identity.** Within any fixed-detector threshold comparison, calibration scores and evaluation scores are immutable scientific inputs. Every compared threshold policy must reference the same score-artifact identity, ordered row identities, client identities, split identities, terminal-detector identity, preprocessing identity, and evaluation labels. Policy-level score equality is proven by scientific artifact identity and provenance, never by two independently generated floating-point arrays being numerically close. A threshold policy must never independently regenerate scores when the scientific contract requires one fixed score artifact.
- [ ] `PROSE-SENTINEL-0034` — source line `181` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance**
  > **Serialization/reload equivalence.** The `1e-12` absolute tolerance defined in §2.2.1 applies only to serialization/reload numerical equivalence (for example, confirming a persisted and reloaded preprocessing state reproduces the same transform). It must not be silently redefined as the threshold-policy score-identity criterion.
- [ ] `PROSE-SENTINEL-0035` — source line `183` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance**
  > **AUROC.** AUROC is a detector-quality control computed from the fixed continuous evaluation-score and evaluation-label artifact; the threshold policy itself is not an AUROC input. Within one fixed-detector threshold ladder, AUROC is computed once from the canonical score/label artifact, or is proven to derive from that exact artifact by scientific artifact identity. A threshold-policy-specific AUROC difference indicates a score/provenance identity failure, not a threshold-scope effect.
- [ ] `PROSE-SENTINEL-0036` — source line `187` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > Every non-conformal exact empirical quantile used by SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, CLUSTER_THRESHOLD, the exact pooled benign oracle, the sample-weighted shared construction, shrinkage endpoints, calibration-size studies, and quantile-sensitivity studies uses the same Hyndman–Fan type-7 / NumPy `method="linear"` convention.
- [ ] `PROSE-SENTINEL-0037` — source line `189` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > For sorted scores \(x_{(1)} \le \cdots \le x_{(n)}\), target \(q\in[0,1]\), and
- [ ] `PROSE-SENTINEL-0038` — source line `195` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > the locked quantile is
- [ ] `PROSE-SENTINEL-0039` — source line `202` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > with the boundary cases \(Q_7(0)=x_{(1)}\) and \(Q_7(1)=x_{(n)}\). Internal calculations use `float64` and are not rounded before threshold application.
- [ ] `PROSE-SENTINEL-0040` — source line `204` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > Two exceptions are intentional and must stay explicit:
- [ ] `PROSE-SENTINEL-0041` — source line `209` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.2.3 Empirical-quantile definition lock**
  > A change in quantile interpolation is a protocol change, not an implementation detail.
- [ ] `PROSE-SENTINEL-0042` — source line `213` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.3 Sole manipulated variable**
  > For the core threshold-scope comparison, the manipulated variable is:
- [ ] `PROSE-SENTINEL-0043` — source line `219` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.3 Sole manipulated variable**
  > Its permitted core values are:
- [ ] `PROSE-SENTINEL-0044` — source line `228` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.3 Sole manipulated variable**
  > A policy-specific terminal detector, feature transformation, or test population invalidates the controlled comparison.
- [ ] `PROSE-SENTINEL-0045` — source line `232` — **Part I — Scientific Programme and Global Protocol Contracts / 2.2.2 Fixed-score identity and serialization tolerance / 2.4 Prohibited causal contamination**
  > The following are forbidden inside the core ladder:
- [ ] `PROSE-SENTINEL-0046` — source line `249` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.1 Benign-only calibration**
  > Every core threshold and every DATP-compatible threshold variant is fitted using benign calibration data only.
- [ ] `PROSE-SENTINEL-0047` — source line `251` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.1 Benign-only calibration**
  > Attack-labelled records are reserved for held-out evaluation and may not influence:
- [ ] `PROSE-SENTINEL-0048` — source line `264` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.1 Benign-only calibration**
  > This boundary is central to DATP’s identity. It distinguishes the study from methods that optimize a threshold using both normal and anomalous validation summaries.
- [ ] `PROSE-SENTINEL-0049` — source line `268` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2 Separation of calibration and evaluation**
  > Calibration records and evaluation records must be disjoint.
- [ ] `PROSE-SENTINEL-0050` — source line `270` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2 Separation of calibration and evaluation**
  > For temporal experiments:
- [ ] `PROSE-SENTINEL-0051` — source line `279` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > The complete DATP-Core threshold programme assumes **protocol-compliant calibration participants and an honest protocol-executing server**. This is a scientific threat-model boundary, not a security guarantee.
- [ ] `PROSE-SENTINEL-0052` — source line `281` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > For every client and every threshold method, the following are assumed to be generated exactly from the declared immutable artifacts and procedure:
- [ ] `PROSE-SENTINEL-0053` — source line `293` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > DATP-Core does **not** allow a participant or server to fabricate, edit, suppress, replay, reorder for semantic effect, or substitute these scientific values adversarially. In particular, no client may falsify a local threshold, support count, score summary, fingerprint, KLL sketch, conformal statistic, or client identity. No network adversary is modeled between client and server.
- [ ] `PROSE-SENTINEL-0054` — source line `295` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > The shared-calibration contributor-availability sensitivity in Part II §8.6 is explicitly **non-adversarial availability sensitivity**: omission subsets are prospectively enumerated and the remaining contributors still report truthful values. It is not a Byzantine-client experiment and cannot support malicious-dropout, poisoning, integrity, or robust-aggregation claims.
- [ ] `PROSE-SENTINEL-0055` — source line `297` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > A checksum/provenance mismatch, impossible support count, or message/artifact identity mismatch is treated as an **invalid scientific artifact / failed integrity gate**, not as empirical evidence that the method resisted an attack.
- [ ] `PROSE-SENTINEL-0056` — source line `299` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.2A Honest-calibration participant and message-integrity assumption**
  > This boundary is required because Byzantine federated-calibration work demonstrates that malicious clients can corrupt federated conformal calibration by reporting arbitrary calibration statistics, and newer work jointly protects training and calibration against Byzantine behavior.[^robfcp2024][^prismfcp2026] DATP-Core therefore makes no claim of Byzantine-robust calibration, secure threshold aggregation, authenticated messaging, or adversarial calibration integrity.
- [ ] `PROSE-SENTINEL-0057` — source line `303` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > Two explicit calibration-size quantities apply throughout DATP-Core. `n_k_source` is the number of benign calibration records available to client `k` **before** any experimental calibration-size subsampling. `m` is the calibration sample size actually used by the calibration-size ablation (Part II — Experiment Programme, §8.1); its locked grid is `m in {50, 100, 250, 500, 1000, 5000}`.
- [ ] `PROSE-SENTINEL-0058` — source line `305` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > The canonical minimum benign calibration support for primary-analysis eligibility is:
- [ ] `PROSE-SENTINEL-0059` — source line `311` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > Eligibility is determined from the source calibration pool, before calibration-size experimental subsampling (Part II — Experiment Programme, §8.1). It is never recomputed simply because a declared ablation cell deliberately uses fewer than 100 observations.
- [ ] `PROSE-SENTINEL-0060` — source line `313` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > Only eligible clients enter the primary cross-client false-positive dispersion calculation.
- [ ] `PROSE-SENTINEL-0061` — source line `315` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > Eligibility is determined before test evaluation and is identical across policies compared within the same experiment.
- [ ] `PROSE-SENTINEL-0062` — source line `317` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3 Client eligibility**
  > An ineligible client may receive a separately declared deployment fallback only when the experiment explicitly studies fallback behavior. It cannot be silently included in the confirmatory population.
- [ ] `PROSE-SENTINEL-0063` — source line `321` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > DATP-Core's confirmatory population is a **persistent, identifiable-client federation**. This is an explicit operating assumption, not an implicit generalization to massive intermittent cross-device FL. Motley distinguishes cross-device settings—where clients may be numerous, sampled sparsely, unavailable, and effectively stateless—from cross-silo settings with persistent identities and stateful personalization.[^motley] DATP-Core uses the persistence semantics relevant to the latter while retaining **physical IoT devices**, not organizations, as the N-BaIoT clients.
- [ ] `PROSE-SENTINEL-0064` — source line `323` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > The locked confirmatory regime is:
- [ ] `PROSE-SENTINEL-0065` — source line `337` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > For an execution coordinate `(dataset_id, population_id, training_seed)`, the same immutable `client_id` must bind, where applicable:
- [ ] `PROSE-SENTINEL-0066` — source line `348` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > A mismatch in this identity chain invalidates the affected artifact. Client identities may not be reassigned between training, calibration, and evaluation to make a personalization method feasible.
- [ ] `PROSE-SENTINEL-0067` — source line `350` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > The cold-start calibration experiment in Part II §8.1A studies **insufficient calibration support for an already-defined client**. It is not a new/unseen-client personalization experiment. `m=0` therefore means “the known client has no usable local calibration sample in this experimental cell,” not “a never-before-seen device has arrived.”
- [ ] `PROSE-SENTINEL-0068` — source line `352` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > Training-time partial participation, random client dropout, stragglers, churn, stateless client sampling, and unseen-client adaptation are outside the present scientific programme. The threshold-stage calibration-contributor-availability sensitivity in Part II §8.6 is not a substitute for those experiments because it changes only truthful contributor availability at threshold construction after the detector has already been trained.
- [ ] `PROSE-SENTINEL-0069` — source line `354` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.3A Federation regime, client persistence, and deployment identity**
  > The manuscript must therefore qualify any deployment statement as applying to **persistent identifiable IoT clients capable of retaining client-specific calibration/personalization state**. No conclusion may be generalized to population-scale intermittent cross-device FL without a separately scoped study.
- [ ] `PROSE-SENTINEL-0070` — source line `358` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.4 Meaning of “fairness”**
  > Within DATP-Core, **fairness means operational or service-level false-positive-rate equity**.
- [ ] `PROSE-SENTINEL-0071` — source line `360` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.4 Meaning of “fairness”**
  > It refers to how evenly false alarms are distributed across IoT clients.
- [ ] `PROSE-SENTINEL-0072` — source line `362` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.4 Meaning of “fairness”**
  > It does not refer to:
- [ ] `PROSE-SENTINEL-0073` — source line `370` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.4 Meaning of “fairness”**
  > Preferred manuscript language is:
- [ ] `PROSE-SENTINEL-0074` — source line `378` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.4 Meaning of “fairness”**
  > The unqualified word *fairness* should be used sparingly and defined at first use.
- [ ] `PROSE-SENTINEL-0075` — source line `382` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.5 Primary operating-point concern**
  > The primary concern is:
- [ ] `PROSE-SENTINEL-0076` — source line `388` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.5 Primary operating-point concern**
  > Absolute dispersion measures accompany it when mean FPR is small.
- [ ] `PROSE-SENTINEL-0077` — source line `390` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.5 Primary operating-point concern**
  > The confirmatory endpoint and its decision rule are specified in Part III — Evaluation, Statistical Analysis, and Reporting.
- [ ] `PROSE-SENTINEL-0078` — source line `394` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.6 Model-quality controls**
  > The following may be reported as controls:
- [ ] `PROSE-SENTINEL-0079` — source line `404` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.6 Model-quality controls**
  > They do not replace `CV(FPR)` as the primary operating-point verdict.
- [ ] `PROSE-SENTINEL-0080` — source line `406` — **Part I — Scientific Programme and Global Protocol Contracts / 3. Calibration and evaluation contract / 3.6 Model-quality controls**
  > In particular:
- [ ] `PROSE-SENTINEL-0081` — source line `419` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.1 Centralized reference: CENTRALIZED_REFERENCE**
  > CENTRALIZED_REFERENCE is the privacy-incompatible centralized reference.
- [ ] `PROSE-SENTINEL-0082` — source line `421` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.1 Centralized reference: CENTRALIZED_REFERENCE**
  > It uses:
- [ ] `PROSE-SENTINEL-0083` — source line `427` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.1 Centralized reference: CENTRALIZED_REFERENCE**
  > CENTRALIZED_REFERENCE is not part of the federated threshold-scope comparison.
- [ ] `PROSE-SENTINEL-0084` — source line `429` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.1 Centralized reference: CENTRALIZED_REFERENCE**
  > A FedAvg model evaluated with a pooled threshold is not CENTRALIZED_REFERENCE.
- [ ] `PROSE-SENTINEL-0085` — source line `431` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.1 Centralized reference: CENTRALIZED_REFERENCE**
  > CENTRALIZED_REFERENCE exists to provide context for the cost of federation, not to participate in the confirmatory claim.
- [ ] `PROSE-SENTINEL-0086` — source line `435` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.2 Shared threshold: SHARED_THRESHOLD**
  > SHARED_THRESHOLD is the shared-scope anchor.
- [ ] `PROSE-SENTINEL-0087` — source line `437` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.2 Shared threshold: SHARED_THRESHOLD**
  > Each eligible client computes its local benign quantile. The server calculates one shared threshold as the arithmetic mean of the eligible local quantiles.
- [ ] `PROSE-SENTINEL-0088` — source line `439` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.2 Shared threshold: SHARED_THRESHOLD**
  > At the canonical operating point:
- [ ] `PROSE-SENTINEL-0089` — source line `445` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.2 Shared threshold: SHARED_THRESHOLD**
  > Every eligible client uses the same resulting threshold.
- [ ] `PROSE-SENTINEL-0090` — source line `447` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.2 Shared threshold: SHARED_THRESHOLD**
  > SHARED_THRESHOLD is not the exact pooled quantile and must not be described as such.
- [ ] `PROSE-SENTINEL-0091` — source line `451` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.3 Local threshold: LOCAL_THRESHOLD**
  > LOCAL_THRESHOLD is the client-local scope anchor.
- [ ] `PROSE-SENTINEL-0092` — source line `453` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.3 Local threshold: LOCAL_THRESHOLD**
  > Each eligible client deploys its own benign calibration quantile at the same canonical target:
- [ ] `PROSE-SENTINEL-0093` — source line `459` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.3 Local threshold: LOCAL_THRESHOLD**
  > LOCAL_THRESHOLD is the comparator in the sole confirmatory shared-versus-local endpoint.
- [ ] `PROSE-SENTINEL-0094` — source line `461` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.3 Local threshold: LOCAL_THRESHOLD**
  > LOCAL_THRESHOLD is not assumed to dominate every policy on every metric. It may reduce FPR dispersion while increasing missed detections or weakening lower-tail classification performance for specific clients.
- [ ] `PROSE-SENTINEL-0095` — source line `465` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.4 Family threshold: FAMILY_THRESHOLD**
  > FAMILY_THRESHOLD assigns one threshold to each validated physical-device family.
- [ ] `PROSE-SENTINEL-0096` — source line `467` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.4 Family threshold: FAMILY_THRESHOLD**
  > The threshold is formed from the eligible local thresholds belonging to that family.
- [ ] `PROSE-SENTINEL-0097` — source line `469` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.4 Family threshold: FAMILY_THRESHOLD**
  > FAMILY_THRESHOLD is permitted only when:
- [ ] `PROSE-SENTINEL-0098` — source line `476` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.4 Family threshold: FAMILY_THRESHOLD**
  > FAMILY_THRESHOLD is a mechanism baseline.
- [ ] `PROSE-SENTINEL-0099` — source line `478` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.4 Family threshold: FAMILY_THRESHOLD**
  > It is available for the N-BaIoT physical-device population and unavailable in populations without a defensible family taxonomy.
- [ ] `PROSE-SENTINEL-0100` — source line `482` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > CLUSTER_THRESHOLD is the taxonomy-free grouped-threshold mechanism.
- [ ] `PROSE-SENTINEL-0101` — source line `484` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > Each eligible client is represented by its benign reconstruction-error fingerprint:
- [ ] `PROSE-SENTINEL-0102` — source line `493` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > The canonical cluster count is:
- [ ] `PROSE-SENTINEL-0103` — source line `499` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > The threshold for a cluster is the mean of the eligible local thresholds of its members.
- [ ] `PROSE-SENTINEL-0104` — source line `501` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > CLUSTER_THRESHOLD studies grouped threshold sharing on a fixed detector.
- [ ] `PROSE-SENTINEL-0105` — source line `503` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > It is not:
- [ ] `PROSE-SENTINEL-0106` — source line `511` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.5 Cluster threshold: CLUSTER_THRESHOLD**
  > Alternative cluster counts, including `K = 9`, are exploratory or supplementary. The canonical count cannot be changed after observing the most favorable test outcome.
- [ ] `PROSE-SENTINEL-0107` — source line `515` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.6 Ladder interpretation**
  > The core ladder represents increasing calibration granularity:
- [ ] `PROSE-SENTINEL-0108` — source line `524` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.6 Ladder interpretation**
  > FAMILY_THRESHOLD and CLUSTER_THRESHOLD do not have to form a strict numerical ordering between SHARED_THRESHOLD and LOCAL_THRESHOLD.
- [ ] `PROSE-SENTINEL-0109` — source line `526` — **Part I — Scientific Programme and Global Protocol Contracts / 4. Threshold-policy system / 4.6 Ladder interpretation**
  > Their scientific role is to test whether intermediate sharing scopes recover part of LOCAL_THRESHOLD’s operating-point equity while reducing per-client calibration dependence.
- [ ] `PROSE-SENTINEL-0110` — source line `532` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants**
  > Threshold variants preserve the fixed detector but alter the threshold estimator.
- [ ] `PROSE-SENTINEL-0111` — source line `534` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants**
  > They remain outside the core threshold-scope identity and cannot become confirmatory after results are observed.
- [ ] `PROSE-SENTINEL-0112` — source line `538` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1 Quantile sensitivity**
  > The canonical quantile remains:
- [ ] `PROSE-SENTINEL-0113` — source line `544` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1 Quantile sensitivity**
  > A pre-specified sensitivity grid tests whether conclusions depend on that choice.
- [ ] `PROSE-SENTINEL-0114` — source line `546` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1 Quantile sensitivity**
  > An alternative quantile cannot replace the canonical endpoint post hoc.
- [ ] `PROSE-SENTINEL-0115` — source line `550` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > A fixed-score estimator-by-scope sensitivity tests whether the shared-versus-local operating-point effect is specific to the empirical `q=0.95` estimator. It uses the historical N-BaIoT-style moment rule as a deliberately simple alternative estimator while preserving the DATP causal score identity.[^nbaiot]
- [ ] `PROSE-SENTINEL-0116` — source line `552` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > The code-facing estimator identity is:
- [ ] `PROSE-SENTINEL-0117` — source line `558` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > For eligible client `k` with benign calibration reconstruction errors `S_k={e_{k,1},...,e_{k,n_k}}`, define
- [ ] `PROSE-SENTINEL-0118` — source line `572` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > using `float64` and sample standard deviation with `ddof=1`. The local moment-rule threshold is
- [ ] `PROSE-SENTINEL-0119` — source line `578` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > The sensitivity is a locked `2 x 2` estimator-by-scope design:
- [ ] `PROSE-SENTINEL-0120` — source line `585` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > For `TYPE7_Q95`, the existing SHARED_THRESHOLD and LOCAL_THRESHOLD definitions are reused unchanged. For the moment estimator:
- [ ] `PROSE-SENTINEL-0121` — source line `596` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > Every eligible client uses `tau_shared^moment` in the shared condition. The arithmetic mean is intentionally the same equal-client scope operator used by SHARED_THRESHOLD, so the sensitivity changes the estimator family without changing the meaning of shared versus local calibration scope.
- [ ] `PROSE-SENTINEL-0122` — source line `598` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > This is **not** presented as a faithful reproduction of Meidan et al.'s complete detector, because their system also used separately trained per-device autoencoders, separately optimized hyperparameters, and a sequential majority-vote alarm rule. DATP uses only the moment threshold formula as a historical estimator-family sensitivity on one frozen score artifact. No sequential windowing is imported.
- [ ] `PROSE-SENTINEL-0123` — source line `600` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.1A Historical mean-plus-standard-deviation estimator sensitivity**
  > This sensitivity is supportive only. `q=0.95` remains the confirmatory estimator and cannot be replaced by the moment rule after outcome inspection.
- [ ] `PROSE-SENTINEL-0124` — source line `604` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > **Calibration pooling bias–variance hypothesis.** Let the unknown client-specific population benign q-quantile be
- [ ] `PROSE-SENTINEL-0125` — source line `610` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > where `F_k` is client `k`'s benign reconstruction-error CDF under the fixed detector. A single shared threshold can reduce estimation noise by pooling information but can incur **distribution-mismatch error** when `tau_shared` differs from `tau_k^*`. A client-local empirical threshold better targets the client's own score distribution but has greater finite-sample estimation variance when local calibration support is small. DATP-Core does not estimate `tau_k^*` from held-out test outcomes and does not claim an unbiased estimator of this unknown population quantity.
- [ ] `PROSE-SENTINEL-0126` — source line `612` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > The empirical programme therefore uses only predeclared proxies:
- [ ] `PROSE-SENTINEL-0127` — source line `625` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > The scientific hypothesis is therefore not “local is always better.” It is that **shared calibration trades lower sampling variance for potential cross-client distribution mismatch, while local calibration trades lower scope mismatch for potentially higher finite-sample variance**. FAMILY_THRESHOLD, CLUSTER_THRESHOLD, fixed shrinkage, and size-aware shrinkage are interpreted as partial-pooling points on this trade-off, not as automatically superior methods. This framing is consistent with modern federated calibration work in which local calibration can become statistically poor at small sites and shrinkage borrows information across sites.[^shahid-fcrc2026]
- [ ] `PROSE-SENTINEL-0128` — source line `627` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > The local–global shrinkage threshold is:
- [ ] `PROSE-SENTINEL-0129` — source line `637` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > Interpretation:
- [ ] `PROSE-SENTINEL-0130` — source line `643` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > The complete pre-specified lambda curve is the result.
- [ ] `PROSE-SENTINEL-0131` — source line `645` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.2 Local–global shrinkage**
  > A favorable intermediate lambda cannot be presented as the primary policy unless its selection rule was fixed without test leakage.
- [ ] `PROSE-SENTINEL-0132` — source line `649` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > The size-aware rule is fixed prospectively before experiment execution. `n_k_source` is client `k`'s complete benign calibration support before experimental subsampling and is used only for eligibility and feasibility. `n_k_used` is the benign calibration support actually supplied to estimate client `k`'s local threshold in the current experimental cell.
- [ ] `PROSE-SENTINEL-0133` — source line `655` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > where `n_min = 100`, the existing canonical minimum benign support. The deployed threshold is:
- [ ] `PROSE-SENTINEL-0134` — source line `661` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > This deterministic rule never depends on evaluation or test labels, metrics, F1, FPR, `CV(FPR)`, AUROC, balanced accuracy, or downstream results. It is bounded in `[0, 1]` and strictly increases with positive `n_k_used`. `lambda = 0` is the conceptual shared endpoint and `lambda -> 1` approaches the local endpoint as calibration support grows. `n_min = 100` is neither fitted nor selected from experiment results; it is inherited from the canonical calibration-support contract.
- [ ] `PROSE-SENTINEL-0135` — source line `663` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > In ordinary full-calibration execution, `n_k_used` is the exact benign calibration count supplied to threshold construction. In calibration-size ablations, `n_k_used = m`; a cell exists only when `n_k_source >= m`, and `n_k_source` must never replace `m` in the weight. The locked grid therefore has weights `m=50 -> 50/150`, `m=100 -> 100/200`, `m=250 -> 250/350`, `m=500 -> 500/600`, `m=1000 -> 1000/1100`, and `m=5000 -> 5000/5100`. Values are never rounded internally.
- [ ] `PROSE-SENTINEL-0136` — source line `665` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > Size-aware shrinkage is compared with the shared threshold, the local threshold, and the complete locked fixed-lambda curve `{0, 0.25, 0.50, 0.75, 1.00}` without post-hoc fixed-lambda selection. It is a calibration-robustness mechanism, not a novel statistical-theory claim or confirmatory endpoint.
- [ ] `PROSE-SENTINEL-0137` — source line `667` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.3 Calibration-size-aware shrinkage**
  > **Current-literature positioning.** Shahid's 2026 site-conditional federated conformal-risk-control study independently uses the same shrinkage-weight family `w_k=n_k/(n_k+n_0)` to interpolate between site-local and pooled calibration, with `n_0` selected through leave-one-site-out sensitivity analysis.[^shahid-fcrc2026] DATP therefore makes **no novelty claim for the functional form** `n/(n+n_0)`. DATP's distinct protocol choice is that the denominator constant is prospectively fixed to the pre-existing `n_min=100` calibration-support contract and is never selected from downstream performance.
- [ ] `PROSE-SENTINEL-0138` — source line `671` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > LOCAL_CONFORMAL_THRESHOLD applies a finite-sample-adjusted local conformal quantile to benign reconstruction errors. Its significance level is tied to the threshold target by:
- [ ] `PROSE-SENTINEL-0139` — source line `677` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > At the canonical `q = 0.95`, the main diagnostic setting is `alpha = 0.05`.
- [ ] `PROSE-SENTINEL-0140` — source line `679` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > Its role is to test held-out benign coverage and address the criticism that per-client thresholds merely equalize FPR by construction.
- [ ] `PROSE-SENTINEL-0141` — source line `681` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > The principal federated-conformal positioning anchors are Lu et al.’s Federated Conformal Prediction framework and Humbert et al.’s one-shot federated conformal method.[^lu-fcp][^humbert-fcp] The submission-time related-work boundary must also acknowledge personalized/localized federated conformal prediction, FedWQ-CP weighted aggregation of client quantile thresholds, group-conditional federated conformal prediction, and personalized federated weighted conformal prediction.[^pfcp2025][^fedwqcp2026][^gcfcp2026][^pfwcp2026]
- [ ] `PROSE-SENTINEL-0142` — source line `683` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > These methods strengthen the scope boundary rather than expanding the experiment programme: DATP does not implement group-conditional conformal calibration, density-ratio-weighted conformal calibration, or a broad federated-conformal benchmark.
- [ ] `PROSE-SENTINEL-0143` — source line `685` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > LOCAL_CONFORMAL_THRESHOLD does not establish:
- [ ] `PROSE-SENTINEL-0144` — source line `693` — **Part I — Scientific Programme and Global Protocol Contracts / 5. Supportive threshold variants / 5.4 Split-conformal local threshold: LOCAL_CONFORMAL_THRESHOLD**
  > Coverage failures, finite-sample granularity, and heterogeneous-client limitations remain reportable.
- [ ] `PROSE-SENTINEL-0145` — source line `701` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**
  > `FEDERATED_BENIGN_SUMMARY_THRESHOLD` is the DATP-compatible benign-only federated summary-statistics comparator.
- [ ] `PROSE-SENTINEL-0146` — source line `703` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**
  > It exists to compare threshold-scope personalization against a federated shared-threshold method that communicates summary statistics rather than local score arrays.
- [ ] `PROSE-SENTINEL-0147` — source line `705` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**
  > Its main construction must:
- [ ] `PROSE-SENTINEL-0148` — source line `714` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**
  > The primary comparator is matched by target exceedance.
- [ ] `PROSE-SENTINEL-0149` — source line `716` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1 `FEDERATED_BENIGN_SUMMARY_THRESHOLD`**
  > A fixed multiplier such as `k = 2`, `2.5`, or `3` is supplementary sensitivity only.
- [ ] `PROSE-SENTINEL-0150` — source line `720` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > `FEDERATED_KLL_SHARED_THRESHOLD` is the mandatory quantile-native shared-threshold comparator. It answers whether a communication-efficient, mergeable approximation of the **pooled benign quantile** can remove an apparent SHARED_THRESHOLD weakness without introducing attack labels or a local threshold at deployment.
- [ ] `PROSE-SENTINEL-0151` — source line `722` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > The comparator uses the Karnin–Lang–Liberty (KLL) mergeable quantile sketch.[^kll] The locked implementation contract is:
- [ ] `PROSE-SENTINEL-0152` — source line `736` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > Apache DataSketches reports single-sided normalized-rank errors of approximately `1.33%`, `0.68%`, and `0.35%` for `k = 200`, `400`, and `800`, respectively; its `k=400` bound is approximately `0.006776` in normalized-rank units at the library's documented 99% error-bound convention.[^datasketches-kll] These values justify the locked grid; they are not DATP empirical results.
- [ ] `PROSE-SENTINEL-0153` — source line `738` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > For pooled benign calibration scores \(S=\{e_i\}_{i=1}^{N}\), define the empirical CDF
- [ ] `PROSE-SENTINEL-0154` — source line `746` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > For the sketch threshold \(\tau_{KLL}\), report the directly observed rank error
- [ ] `PROSE-SENTINEL-0155` — source line `754` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > Also report absolute and relative threshold error against the exact type-7 pooled quantile, held-out benign target-attainment error, `CV(FPR)`, IQR, range, worst-client FPR, actual serialized sketch bytes per client, total uploaded sketch bytes, merge/query time, and client coverage.
- [ ] `PROSE-SENTINEL-0156` — source line `756` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.1A `FEDERATED_KLL_SHARED_THRESHOLD`**
  > The primary comparator uses `k=400`. The `k={200,800}` conditions are sensitivity points only and cannot replace `k=400` after outcome inspection. KLL itself is established prior art; DATP makes no sketch-algorithm novelty claim.
- [ ] `PROSE-SENTINEL-0157` — source line `760` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.2 Relationship to Laridi et al.**
  > Laridi et al. proposed a federated autoencoder threshold based on aggregated summary statistics from both normal and anomalous validation data.[^laridi]
- [ ] `PROSE-SENTINEL-0158` — source line `762` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.2 Relationship to Laridi et al.**
  > DATP’s comparator deliberately excludes anomalous calibration information.
- [ ] `PROSE-SENTINEL-0159` — source line `764` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.2 Relationship to Laridi et al.**
  > Therefore:
- [ ] `PROSE-SENTINEL-0160` — source line `771` — **Part I — Scientific Programme and Global Protocol Contracts / 6. Federated threshold comparator / 6.2 Relationship to Laridi et al.**
  > The reserved name `LARIDI_ANOMALY_INFORMED_REFERENCE` refers only to a genuinely anomaly-informed implementation, which is out of scope for DATP-Core.
- [ ] `PROSE-SENTINEL-0161` — source line `777` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests**
  > Training-side stress tests change the detector and therefore cannot share the causal interpretation of the core threshold-scope comparison.
- [ ] `PROSE-SENTINEL-0162` — source line `779` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests**
  > They require separate models, score sets, and evaluation.
- [ ] `PROSE-SENTINEL-0163` — source line `783` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > FedProx is the aggregation-side heterogeneity stress test.
- [ ] `PROSE-SENTINEL-0164` — source line `785` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > At round \(t\), client \(k\) optimizes the genuine FedProx local objective
- [ ] `PROSE-SENTINEL-0165` — source line `791` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > where \(w^{(t)}\) is the server model broadcast at the start of the round. FedProx was introduced to address statistical and systems heterogeneity in federated optimization.[^fedprox]
- [ ] `PROSE-SENTINEL-0166` — source line `793` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > The locked DATP stress-test coefficient grid is:
- [ ] `PROSE-SENTINEL-0167` — source line `799` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > `mu = 0` is FedAvg-equivalent and is not treated as a FedProx condition. The complete grid is reported; no single coefficient may be promoted post hoc as the "best FedProx" condition.
- [ ] `PROSE-SENTINEL-0168` — source line `801` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > Its purpose in DATP-Core is to ask:
- [ ] `PROSE-SENTINEL-0169` — source line `805` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > FedProx results must be described as a training-side sensitivity.
- [ ] `PROSE-SENTINEL-0170` — source line `807` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1 FedProx**
  > They cannot be merged with the FedAvg confirmatory endpoint.
- [ ] `PROSE-SENTINEL-0171` — source line `811` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > Because DATP-Core deliberately fixes `local_epochs = 1`, the FedProx stress test must measure whether the proximal intervention actually changes local-update drift rather than assuming that the mechanism was strongly activated.
- [ ] `PROSE-SENTINEL-0172` — source line `813` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > Let `P` be the total number of trainable scalar parameters. For client `k` in round `t`, let `w^(t)` be the exact server-broadcast state and `w_out(k,t)` the exact client state returned after its one local epoch. Persist the broadcast-state identity and compute in float64:
- [ ] `PROSE-SENTINEL-0173` — source line `825` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > and, for FedProx only,
- [ ] `PROSE-SENTINEL-0174` — source line `832` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > For each training seed `s` and training condition `a in {FedAvg, FedProx(mu)}`, summarize:
- [ ] `PROSE-SENTINEL-0175` — source line `844` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > The terminal-50-round window is fixed prospectively to the final 25% of the locked 200-round training run and is never changed after outcomes are seen. Also report each client's terminal-50 median so that a federation-wide median cannot hide one highly drifting client.
- [ ] `PROSE-SENTINEL-0176` — source line `846` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > When `D_terminal50[s,FedAvg] > 1e-12`, define the un-clipped descriptive drift-suppression fraction
- [ ] `PROSE-SENTINEL-0177` — source line `855` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > Interpretation is literal: `0` means no median drift suppression, `0.5` means a 50% reduction, values `<0` mean larger median drift than FedAvg, and values `>1` are impossible for non-negative drift unless a provenance/numerical error has occurred. If the FedAvg denominator is `<=1e-12`, record `UNAVAILABLE_NEAR_ZERO_FEDAVG_DRIFT`; do not add an epsilon.
- [ ] `PROSE-SENTINEL-0178` — source line `857` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > For each `mu`, report the ten seed-level drift-suppression values together with the corresponding change in full-score benign heterogeneity
- [ ] `PROSE-SENTINEL-0179` — source line `863` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.1A FedProx mechanism-activation diagnostics**
  > and the SHARED_THRESHOLD-to-LOCAL_THRESHOLD scope gain. These quantities are mechanism diagnostics only. Client-round cells are repeated measurements nested inside a training seed and must never be treated as independent inferential observations.
- [ ] `PROSE-SENTINEL-0180` — source line `867` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > Ditto is the planned model-personalization stress test.
- [ ] `PROSE-SENTINEL-0181` — source line `869` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > Ditto maintains the ordinary global federated solution \(w\) and, for each client \(k\), a persistent personalized state \(v_k\) obtained from
- [ ] `PROSE-SENTINEL-0182` — source line `875` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > The locked DATP stress-test grid is
- [ ] `PROSE-SENTINEL-0183` — source line `882` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > The grid is taken from the scale of the original Ditto evaluation, which explicitly tuned among values including `{0.1, 1, 2}`; `1.0` is prospectively designated as the canonical DATP condition before DATP outcomes are inspected.[^ditto] All three values are executed and reported. The `0.1` and `2.0` conditions are sensitivity analyses and cannot rescue or replace the canonical `1.0` result.
- [ ] `PROSE-SENTINEL-0184` — source line `884` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > The name *Ditto* may be used only when the implementation preserves genuine Ditto semantics, including:
- [ ] `PROSE-SENTINEL-0185` — source line `892` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > The purpose is to ask:
- [ ] `PROSE-SENTINEL-0186` — source line `896` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2 Ditto**
  > The in-paper comparison remains one personalized-model family, not a broad personalized-FL benchmark.
- [ ] `PROSE-SENTINEL-0187` — source line `900` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > `FEDAVG_LOCAL_FINE_TUNING` is the simple model-personalization stress condition. It is included because empirical PFL benchmarking shows that standard FL followed by local fine-tuning is a strong baseline and can rival more specialized personalization methods.[^matsuda-pfl] Cheng, Chadha, and Duchi additionally evaluate fine-tuned FedAvg with **10 local epochs before evaluation**; DATP-Core adopts `10` as a prospective, literature-backed stress depth rather than tuning the number of epochs against DATP outcomes.[^cheng-ftfa]
- [ ] `PROSE-SENTINEL-0188` — source line `902` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > The stress condition is intentionally simple:
- [ ] `PROSE-SENTINEL-0189` — source line `918` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > For client `k`, initialize
- [ ] `PROSE-SENTINEL-0190` — source line `924` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > and perform exactly ten complete local epochs minimizing the ordinary client benign-training reconstruction objective
- [ ] `PROSE-SENTINEL-0191` — source line `933` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > where `theta_FedAvg` denotes the **same optimizer class and local-training hyperparameters** used by the FedAvg reference. The objective receives no proximal or personalization penalty; the only change is continued local optimization from the FedAvg terminal weights.
- [ ] `PROSE-SENTINEL-0192` — source line `935` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > The optimizer contract is exact:
- [ ] `PROSE-SENTINEL-0193` — source line `944` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > Fine-tuning randomness is derived deterministically from the existing seed-derivation contract with purpose label `FEDAVG_LOCAL_FINE_TUNING` and identity tuple
- [ ] `PROSE-SENTINEL-0194` — source line `950` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > so that repeated execution of the same coordinate yields the same local batch order and terminal personalized state.
- [ ] `PROSE-SENTINEL-0195` — source line `952` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > After epoch 10, each client model is frozen. That client model generates one immutable calibration-score artifact and one immutable evaluation-score artifact for that client. SHARED_THRESHOLD and LOCAL_THRESHOLD are then computed from those **fine-tuned-model scores**, without further model updates. Policy-specific re-fine-tuning is forbidden.
- [ ] `PROSE-SENTINEL-0196` — source line `954` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2A Post-FedAvg client-local fine-tuning stress test**
  > This condition is a model-side stress test, not part of the FedAvg fixed-detector confirmatory ladder. Ditto remains a distinct persistent regularized-personalization stress test; fine-tuning does not replace it and cannot be renamed Ditto.
- [ ] `PROSE-SENTINEL-0197` — source line `958` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > FedProx, `FEDAVG_LOCAL_FINE_TUNING`, and Ditto must all be analyzed through the same upstream-mechanism vocabulary so that “absorption” is not inferred only from the final `CV(FPR)` contrast.
- [ ] `PROSE-SENTINEL-0198` — source line `960` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > For every training seed `s`, model condition `a`, and eligible client `k`, use that condition's **full benign calibration score artifact** to compute in float64:
- [ ] `PROSE-SENTINEL-0199` — source line `974` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > Across the common eligible clients, define three coefficient-of-variation-style descriptive dispersions:
- [ ] `PROSE-SENTINEL-0200` — source line `991` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > where every `SD` is the sample standard deviation with `ddof=1`. If a denominator is non-finite or `<=1e-12`, the corresponding quantity is `UNAVAILABLE_NONPOSITIVE_SCALE`; no epsilon is added.
- [ ] `PROSE-SENTINEL-0201` — source line `993` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > Let `tau_shared[s,a]` be that condition's canonical SHARED_THRESHOLD and `tau_local[s,a,k]=T[s,a,k]`. Define
- [ ] `PROSE-SENTINEL-0202` — source line `1007` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > The normalized quantity is unavailable when its denominator is non-finite or `<=1e-12`.
- [ ] `PROSE-SENTINEL-0203` — source line `1009` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > The ordinary within-condition benign-distribution heterogeneity term `H[s,a]` remains the exact 64-bin mean pairwise JSD defined in Part II §7.4 and is used for the within-condition empirical policy-selection surface. It is **not** used for a cross-model reduction ratio because condition-specific quantile bin edges would move with the model.
- [ ] `PROSE-SENTINEL-0204` — source line `1011` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > For cross-model alignment only, define a FedAvg-anchored histogram grid separately for each training seed `s`. Pool the **FedAvg full benign calibration scores** of the common eligible clients and compute the 63 type-7 cut points
- [ ] `PROSE-SENTINEL-0205` — source line `1018` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > Remove non-finite cut points and collapse exact duplicate cut points while preserving strict ascending order. The resulting fixed bins are
- [ ] `PROSE-SENTINEL-0206` — source line `1024` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > where `J_s` is the number of retained unique interior cut points. If `J_s=0`, emit `UNAVAILABLE_DEGENERATE_FEDAVG_JSD_GRID` for cross-model JSD alignment. Otherwise apply **these same FedAvg-derived bins without refitting** to every client under FedAvg, every FedProx `mu`, `FEDAVG_LOCAL_FINE_TUNING`, and every Ditto `lambda_D`. Convert counts to relative frequencies; add no pseudocount. Use the same base-2 JSD and `0*log2(0/x)=0` convention as Part II §7.4. Define
- [ ] `PROSE-SENTINEL-0207` — source line `1032` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > where `B_s` denotes the fixed seed-specific FedAvg bin grid. `ModelAlignmentH` is therefore directly comparable across model-side conditions within a seed; the ordinary `H` remains the condition-native heterogeneity descriptor.
- [ ] `PROSE-SENTINEL-0208` — source line `1034` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > The raw threshold-scope gain is
- [ ] `PROSE-SENTINEL-0209` — source line `1041` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > For any scalar mechanism quantity
- [ ] `PROSE-SENTINEL-0210` — source line `1053` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > with valid `X[s,FedAvg] > 1e-12`, define the un-clipped alignment-reduction fraction
- [ ] `PROSE-SENTINEL-0211` — source line `1060` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > If the FedAvg denominator is `<=1e-12`, emit `UNAVAILABLE_NO_POSITIVE_FEDAVG_REFERENCE`. Negative values are retained and mean the upstream model condition increased the measured dispersion/heterogeneity.
- [ ] `PROSE-SENTINEL-0212` — source line `1062` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > When `DeltaScope[s,FedAvg] > 1e-12`, define the general un-clipped scope-absorption fraction
- [ ] `PROSE-SENTINEL-0213` — source line `1069` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > The existing canonical Ditto `AbsorptionFraction` is exactly `ScopeAbsorption[s,Ditto(lambda_D=1.0)]`; it is not a separate formula. The same calculation is reported for every FedProx coefficient and for `FEDAVG_LOCAL_FINE_TUNING` when the denominator is valid.
- [ ] `PROSE-SENTINEL-0214` — source line `1071` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > For every model-side condition, interpretation uses the same locked seed-level bands when `DeltaScope[s,FedAvg] > 1e-12`:
- [ ] `PROSE-SENTINEL-0215` — source line `1080` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > Values `<0` remain inside `RETAINED_STRONGLY` and explicitly mean amplification rather than absorption. When the FedAvg gap is `<=1e-12`, emit `UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP` and interpret raw deltas only. Campaign summaries report the ten seed-level raw deltas and the distribution of valid seed-level absorption values; a ratio of campaign-level means is forbidden.
- [ ] `PROSE-SENTINEL-0216` — source line `1082` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > Every model-side stress condition must report, per seed, the tuple
- [ ] `PROSE-SENTINEL-0217` — source line `1096` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > plus every available `AlignmentReduction`. The mechanistic hypothesis is the ordered chain
- [ ] `PROSE-SENTINEL-0218` — source line `1105` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.2B Common model-side score-alignment and threshold-absorption diagnostics**
  > This chain is **tested descriptively, not assumed**. If a stress method changes the detector but does not reduce `ModelAlignmentH`/score/threshold dispersion, a null absorption result must not be interpreted as evidence that threshold personalization survives a strongly activated alignment mechanism. Conversely, association among these quantities is not sufficient for a causal mediation claim.
- [ ] `PROSE-SENTINEL-0219` — source line `1109` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.3 Fallback naming**
  > When genuine Ditto cannot be implemented without violating the locked model contract, the alternative must be named according to the algorithm actually implemented, such as:
- [ ] `PROSE-SENTINEL-0220` — source line `1116` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.3 Fallback naming**
  > A fallback must never be called Ditto.
- [ ] `PROSE-SENTINEL-0221` — source line `1118` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.3 Fallback naming**
  > A fallback changes the scientific comparator and must be recorded before its results are used.
- [ ] `PROSE-SENTINEL-0222` — source line `1122` — **Part I — Scientific Programme and Global Protocol Contracts / 7. Training-side stress tests / 7.4 Separation from the core ladder**
  > For every stress-test model:
- [ ] `PROSE-SENTINEL-0223` — source line `1144` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.1 Sole confirmatory evidence**
  > The statistical decision rule is specified in Part III — Evaluation, Statistical Analysis, and Reporting.
- [ ] `PROSE-SENTINEL-0224` — source line `1148` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.2 Supporting evidence families**
  > All remaining work belongs to one of the following roles:
- [ ] `PROSE-SENTINEL-0225` — source line `1165` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.2 Supporting evidence families**
  > A supportive analysis cannot be promoted to rescue a failed confirmatory endpoint.
- [ ] `PROSE-SENTINEL-0226` — source line `1167` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.2 Supporting evidence families**
  > An external dataset cannot silently become a second confirmatory population.
- [ ] `PROSE-SENTINEL-0227` — source line `1169` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.2 Supporting evidence families**
  > An exploratory result cannot be rewritten as pre-specified evidence after it is observed.
- [ ] `PROSE-SENTINEL-0228` — source line `1173` — **Part I — Scientific Programme and Global Protocol Contracts / 8. Evidence architecture / 8.3 Honest negative evidence**
  > Null, opposite, and infeasible outcomes remain scientifically meaningful. They must be reported rather than hidden or replaced by a more favorable analysis.
- [ ] `PROSE-SENTINEL-0229` — source line `1179` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries**
  > Detailed population procedures belong to Part II — Experiment Programme. This section fixes only the identity-level boundaries.
- [ ] `PROSE-SENTINEL-0230` — source line `1183` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.1 N-BaIoT physical-device anchor**
  > N-BaIoT is the confirmatory dataset anchor.
- [ ] `PROSE-SENTINEL-0231` — source line `1185` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.1 N-BaIoT physical-device anchor**
  > The original dataset study evaluated nine commercial IoT devices infected with Mirai and BASHLITE using deep autoencoder anomaly detection.[^nbaiot]
- [ ] `PROSE-SENTINEL-0232` — source line `1187` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.1 N-BaIoT physical-device anchor**
  > For DATP-Core:
- [ ] `PROSE-SENTINEL-0233` — source line `1197` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > The original CICIoT2023 publication describes a large IoT environment with 105 devices and 33 attacks.[^ciciot2023]
- [ ] `PROSE-SENTINEL-0234` — source line `1199` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > The available processed DATP artifact does not retain a verified physical-device mapping.
- [ ] `PROSE-SENTINEL-0235` — source line `1201` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > Therefore:
- [ ] `PROSE-SENTINEL-0236` — source line `1208` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > Without verified physical-device identities, CICIoT2023 cannot be repartitioned as physical devices. Artificial groupings and inferred chronology are not valid substitutes.
- [ ] `PROSE-SENTINEL-0237` — source line `1210` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > The lossless canonical artifact remains the raw-fidelity record. Before any file-defined client construction, split, fitting, calibration, or evaluation, a CICIoT2023 row is eligible for model input if and only if its normalized label is recognized and every declared model-input feature is finite. The gate records the missing-or-unrecognized-label and non-finite-feature signals independently, preserves stable row identity and source provenance, and applies identically to every compared method. It never imputes, zero-fills, caps, clips, replaces infinities, or infers labels.
- [ ] `PROSE-SENTINEL-0238` — source line `1212` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > **No additional CICIoT2023 physical-device population is defined.** The currently available CICIoT2023 artifact supports `CICIOT_FILE_CLIENTS` only. The original study's device count must not be substituted for missing device-level provenance in the available DATP artifact. Do not construct inferred devices, MAC-derived clients without verified MAC provenance, artificial physical-device mappings, or synthetic replacements masquerading as natural devices.
- [ ] `PROSE-SENTINEL-0239` — source line `1214` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.2 CICIoT2023 available-data boundary**
  > A future CICIoT2023 physical-device population would constitute a new scientific population and may be added only if independently verified device-level provenance becomes available and the roadmap is explicitly revised before execution.
- [ ] `PROSE-SENTINEL-0240` — source line `1218` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.3 Controlled heterogeneity population**
  > The Dirichlet N-BaIoT population is a controlled sensitivity experiment.
- [ ] `PROSE-SENTINEL-0241` — source line `1220` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.3 Controlled heterogeneity population**
  > It does not replace natural device partitioning.
- [ ] `PROSE-SENTINEL-0242` — source line `1222` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.3 Controlled heterogeneity population**
  > It may support a graded heterogeneity interpretation but cannot establish that one scalar non-IID parameter reproduces real device heterogeneity.
- [ ] `PROSE-SENTINEL-0243` — source line `1226` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > Edge-IIoTset is the sole new external dataset.[^edge-iiotset]
- [ ] `PROSE-SENTINEL-0244` — source line `1228` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > Its client definition is established from first-principles dataset evidence, not by copying a partition from another paper.
- [ ] `PROSE-SENTINEL-0245` — source line `1230` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > The external scope is benign operating-point equity.
- [ ] `PROSE-SENTINEL-0246` — source line `1232` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > Where attack traffic cannot be validly assigned to each client:
- [ ] `PROSE-SENTINEL-0247` — source line `1240` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > These outcomes must be represented as unavailable rather than estimated, inherited from another partition, or fabricated.
- [ ] `PROSE-SENTINEL-0248` — source line `1242` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.4 Edge-IIoTset external validation**
  > FAMILY_THRESHOLD is omitted when no defensible external family taxonomy exists.
- [ ] `PROSE-SENTINEL-0249` — source line `1246` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.5 Temporal external population**
  > The temporal experiment is limited to one-shot threshold recalibration on a verified chronological Edge-IIoTset population.
- [ ] `PROSE-SENTINEL-0250` — source line `1248` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.5 Temporal external population**
  > It does not establish:
- [ ] `PROSE-SENTINEL-0251` — source line `1257` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.5 Temporal external population**
  > CICIoT2023 temporal probing remains suppressed when valid timestamps are absent.
- [ ] `PROSE-SENTINEL-0252` — source line `1261` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.6 Dataset expansion limit**
  > DATP-Core adds no external IoT dataset beyond Edge-IIoTset.
- [ ] `PROSE-SENTINEL-0253` — source line `1263` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.6 Dataset expansion limit**
  > Adding another dataset would change the study’s scientific scope.
- [ ] `PROSE-SENTINEL-0254` — source line `1265` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.6 Dataset expansion limit**
  > This limit prevents the paper from becoming a generic multi-dataset FL-IDS benchmark.
- [ ] `PROSE-SENTINEL-0255` — source line `1271` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > The phrase **heterogeneous federated IoT clients** is not permitted to collapse fundamentally different sources of heterogeneity. Hardware-sensitive FL work explicitly treats model/hardware-capability heterogeneity as a separate problem from statistical data heterogeneity,[^fairhetero] while DATP-Core's intervention is primarily about the distribution of anomaly scores and calibration support after model training.
- [ ] `PROSE-SENTINEL-0256` — source line `1273` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > Every heterogeneity dimension in DATP-Core has one or more of the following status labels:
- [ ] `PROSE-SENTINEL-0257` — source line `1294` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > `MANIPULATED_INDIRECTLY` means the programme changes a declared upstream condition (for example Dirichlet allocation, preprocessing, or model training) and then **measures** resulting score heterogeneity; it does not directly synthesize a target JSD value.
- [ ] `PROSE-SENTINEL-0258` — source line `1296` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > The manuscript's unqualified central heterogeneity language refers to **natural/statistical device heterogeneity, benign-score heterogeneity, and calibration-support heterogeneity**, with the controlled Dirichlet and temporal programmes providing bounded sensitivity/boundary evidence. Hardware/model-capacity heterogeneity and intermittent-client systems heterogeneity remain separate research problems.
- [ ] `PROSE-SENTINEL-0259` — source line `1300` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations**
  > This section consolidates scope control, vocabulary, claim discipline, and accepted limitations. The underlying constraints are preserved; consolidation prevents the same boundary from being rediscovered in several distant sections.
- [ ] `PROSE-SENTINEL-0260` — source line `1304` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations**
  > DATP-Core strengthens the original DATP study along six bounded directions.
- [ ] `PROSE-SENTINEL-0261` — source line `1308` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.1 External validation**
  > One external IoT/IIoT dataset tests whether benign false-alarm equity effects transfer beyond N-BaIoT.
- [ ] `PROSE-SENTINEL-0262` — source line `1312` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.2 Federated threshold comparison**
  > One benign-only summary-statistics comparator tests whether threshold personalization is dominated by a distributed shared-threshold alternative.
- [ ] `PROSE-SENTINEL-0263` — source line `1316` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.3 Training-side robustness**
  > Three bounded training-side stress routes examine:
- [ ] `PROSE-SENTINEL-0264` — source line `1322` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.3 Training-side robustness**
  > They remain outside the causal ladder. Fine-tuning and Ditto are two deliberately different implementations of the same reviewer counterfactual—client-specific model adaptation—not authorization for a broader PFL benchmark.
- [ ] `PROSE-SENTINEL-0265` — source line `1326` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.4 Threshold-estimation depth**
  > The threshold story is extended through:
- [ ] `PROSE-SENTINEL-0266` — source line `1336` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.5 Temporal boundary**
  > One chronological, one-shot recalibration experiment tests whether frozen thresholds age and whether a single future benign calibration window recovers operating-point equity.
- [ ] `PROSE-SENTINEL-0267` — source line `1340` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.6 Mechanism analysis**
  > The journal extension includes bounded mechanism work covering:
- [ ] `PROSE-SENTINEL-0268` — source line `1349` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.6 Mechanism analysis**
  > These analyses explain the result but do not create additional confirmatory claims.
- [ ] `PROSE-SENTINEL-0269` — source line `1353` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.7 Hard scope limits**
  > The complete programme is limited to:
- [ ] `PROSE-SENTINEL-0270` — source line `1366` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.A.7 Hard scope limits**
  > Expansion beyond these limits would change the study’s scientific scope.
- [ ] `PROSE-SENTINEL-0271` — source line `1374` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.1 Security attacks and defenses**
  > DATP-Core does not study adversarial attacks, poisoning, or defensive mechanisms. The exclusion covers training poisoning, model/update poisoning, backdoors, inference-time evasion, malicious calibration-row manipulation, falsified threshold/summary/fingerprint/sketch messages, Byzantine calibration contributors, malicious contributor omission, and network tampering with threshold-stage messages. The protocol-compliant calibration assumption is defined in §3.2A.
- [ ] `PROSE-SENTINEL-0272` — source line `1376` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.1 Security attacks and defenses**
  > Rob-FCP shows that arbitrary malicious calibration statistics can invalidate ordinary federated conformal calibration, while PRISM-FCP extends Byzantine treatment across both training and calibration phases.[^robfcp2024][^prismfcp2026] These works define an explicit future/security boundary; they do not create a DATP-Core experiment.
- [ ] `PROSE-SENTINEL-0273` — source line `1380` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.2 Formal privacy**
  > DATP-Core does not implement or claim formal privacy protections or guarantees.
- [ ] `PROSE-SENTINEL-0274` — source line `1382` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.2 Formal privacy**
  > Keeping raw data local is a structural property of FL, not a formal privacy guarantee.
- [ ] `PROSE-SENTINEL-0275` — source line `1384` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.2 Formal privacy**
  > CLUSTER_THRESHOLD clustering is not a privacy mechanism.
- [ ] `PROSE-SENTINEL-0276` — source line `1386` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.2 Formal privacy**
  > Threshold-message size is not a privacy proof.
- [ ] `PROSE-SENTINEL-0277` — source line `1390` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.3 Deployment validation**
  > DATP-Core does not provide hardware, resource, network-traffic, or production deployment validation.
- [ ] `PROSE-SENTINEL-0278` — source line `1392` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.3 Deployment validation**
  > Communication and storage may be estimated from serialized message sizes. Such estimates must not be called deployment measurements.
- [ ] `PROSE-SENTINEL-0279` — source line `1396` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.4 Fleet scale**
  > The paper does not claim fleet-scale validation above 100 clients.
- [ ] `PROSE-SENTINEL-0280` — source line `1398` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.4 Fleet scale**
  > Synthetic client counts or available-data pseudo-clients do not establish real fleet-scale deployment.
- [ ] `PROSE-SENTINEL-0281` — source line `1402` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.5 Full drift handling**
  > The temporal experiment does not provide continuous adaptation, online recalibration, or autonomous drift detection.
- [ ] `PROSE-SENTINEL-0282` — source line `1406` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.6 Broad FL benchmarking**
  > The study is not an exhaustive benchmark of federated learning, personalization, clustering, anomaly detection, privacy, or intrusion-detection methods.
- [ ] `PROSE-SENTINEL-0283` — source line `1408` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.6 Broad FL benchmarking**
  > FedBN is excluded because introducing BatchNorm would change the locked autoencoder architecture and therefore the scientific object.
- [ ] `PROSE-SENTINEL-0284` — source line `1412` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.7 Federated conformal breadth**
  > The bounded LOCAL_CONFORMAL_THRESHOLD diagnostic does not expand into federated conformal benchmarking, method development, adversarial conformal prediction, or online adaptation.
- [ ] `PROSE-SENTINEL-0285` — source line `1414` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.7 Federated conformal breadth**
  > Lu et al. and Humbert et al. are primary prior-art anchors for federated conformal prediction.[^lu-fcp][^humbert-fcp]
- [ ] `PROSE-SENTINEL-0286` — source line `1420` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.10 Explicit non-expansion guardrails for this amendment**
  > The additions above do not authorize the following scope expansion:
- [ ] `PROSE-SENTINEL-0287` — source line `1434` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.B.10 Explicit non-expansion guardrails for this amendment**
  > These remain future or separate-study directions.
- [ ] `PROSE-SENTINEL-0288` — source line `1440` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > Use:
- [ ] `PROSE-SENTINEL-0289` — source line `1446` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > for the original method and conference identity.
- [ ] `PROSE-SENTINEL-0290` — source line `1448` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > Use:
- [ ] `PROSE-SENTINEL-0291` — source line `1454` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > for the extended study.
- [ ] `PROSE-SENTINEL-0292` — source line `1456` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > Use:
- [ ] `PROSE-SENTINEL-0293` — source line `1462` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > for the conference-faithful reference protocol inside DATP-Core.
- [ ] `PROSE-SENTINEL-0294` — source line `1464` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.1 Project naming**
  > Avoid using *journal* as a model, experiment, or scientific method name.
- [ ] `PROSE-SENTINEL-0295` — source line `1468` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.2 Threshold-policy identifiers**
  > Active descriptive policy identifiers are:
- [ ] `PROSE-SENTINEL-0296` — source line `1478` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.2 Threshold-policy identifiers**
  > Their meanings are fixed by this document. The identifiers describe the scientific behavior directly and are shared across the roadmap, implementation contracts, manifests, audit outputs, tables, and figures.
- [ ] `PROSE-SENTINEL-0297` — source line `1480` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.2 Threshold-policy identifiers**
  > Do not reuse these identifiers for:
- [ ] `PROSE-SENTINEL-0298` — source line `1490` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.3 Threshold-variant identifiers**
  > Use descriptive identities:
- [ ] `PROSE-SENTINEL-0299` — source line `1500` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.3 Threshold-variant identifiers**
  > Opaque numbered aliases, recycled family-policy labels, and vague names such as `Laridi-faithful benign` are prohibited. `FAMILY_THRESHOLD` is reserved exclusively for physical-device-family thresholding.
- [ ] `PROSE-SENTINEL-0300` — source line `1504` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.4 Laridi naming**
  > Use:
- [ ] `PROSE-SENTINEL-0301` — source line `1510` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.4 Laridi naming**
  > for the benign-only DATP-compatible summary-statistics comparator.
- [ ] `PROSE-SENTINEL-0302` — source line `1512` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.4 Laridi naming**
  > Reserve:
- [ ] `PROSE-SENTINEL-0303` — source line `1518` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.4 Laridi naming**
  > for a genuinely anomaly-informed reproduction, which is out of scope.
- [ ] `PROSE-SENTINEL-0304` — source line `1520` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.4 Laridi naming**
  > Never call the benign adaptation *faithful*.
- [ ] `PROSE-SENTINEL-0305` — source line `1524` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.5 Personalized-model naming**
  > Use *Ditto* only for a genuine Ditto implementation.
- [ ] `PROSE-SENTINEL-0306` — source line `1526` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.5 Personalized-model naming**
  > Otherwise use the actual method name, such as:
- [ ] `PROSE-SENTINEL-0307` — source line `1533` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.5 Personalized-model naming**
  > Do not use generic names such as:
- [ ] `PROSE-SENTINEL-0308` — source line `1541` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.5 Personalized-model naming**
  > when a recognized algorithm is implemented.
- [ ] `PROSE-SENTINEL-0309` — source line `1545` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.5A Simple local-fine-tuning naming**
  > Use the exact identity `FEDAVG_LOCAL_FINE_TUNING` for the locked ten-epoch post-FedAvg stress condition. Do not call it Ditto, FedPer, Per-FedAvg, local-only training, or a new DATP threshold method. Its personalization occurs in the detector parameters before scoring; the downstream SHARED_THRESHOLD/LOCAL_THRESHOLD comparison remains a separate threshold-calibration intervention.
- [ ] `PROSE-SENTINEL-0310` — source line `1549` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.6 Population identifiers**
  > Active population identifiers are:
- [ ] `PROSE-SENTINEL-0311` — source line `1559` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.6 Population identifiers**
  > They refer to scientific dataset/population contracts, not arbitrary implementation labels.
- [ ] `PROSE-SENTINEL-0312` — source line `1561` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.6 Population identifiers**
  > Every mention must include a descriptive phrase at first use, such as:
- [ ] `PROSE-SENTINEL-0313` — source line `1569` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.7 Statistical and equity language**
  > Use:
- [ ] `PROSE-SENTINEL-0314` — source line `1580` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.7 Statistical and equity language**
  > Avoid:
- [ ] `PROSE-SENTINEL-0315` — source line `1591` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.7 Statistical and equity language**
  > unless the corresponding property is formally established.
- [ ] `PROSE-SENTINEL-0316` — source line `1595` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use**
  > The word *calibration* is overloaded. DATP-Core must distinguish the following three scientific objects explicitly:
- [ ] `PROSE-SENTINEL-0317` — source line `1601` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.7A Calibration-object taxonomy — mandatory at first manuscript use**
  > Consequences:
- [ ] `PROSE-SENTINEL-0318` — source line `1611` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.8 Novelty language**
  > Do not use:
- [ ] `PROSE-SENTINEL-0319` — source line `1623` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.8 Novelty language**
  > Such language requires independent evidence beyond this roadmap.
- [ ] `PROSE-SENTINEL-0320` — source line `1629` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.C.8 Novelty language**
  > The following scope-level framing remains mandatory.
- [ ] `PROSE-SENTINEL-0321` — source line `1633` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.1 Permitted central framing**
  > DATP-Core may be framed as:
- [ ] `PROSE-SENTINEL-0322` — source line `1643` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.2 Prohibited central framing**
  > DATP-Core must not be framed as:
- [ ] `PROSE-SENTINEL-0323` — source line `1658` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.3 AUROC language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0324` — source line `1662` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.3 AUROC language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0325` — source line `1666` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.3 AUROC language**
  > A threshold change cannot change score ranking when the model and scores are fixed.
- [ ] `PROSE-SENTINEL-0326` — source line `1670` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.4 Macro-F1 language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0327` — source line `1674` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.4 Macro-F1 language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0328` — source line `1678` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.4 Macro-F1 language**
  > That statement is unsupported when global or lower-tail classification metrics weaken.
- [ ] `PROSE-SENTINEL-0329` — source line `1682` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.5 External validation language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0330` — source line `1686` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.5 External validation language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0331` — source line `1690` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.5 External validation language**
  > Per-client attack-sensitive metrics are unavailable under the audited artifact.
- [ ] `PROSE-SENTINEL-0332` — source line `1694` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.6 Temporal language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0333` — source line `1698` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.6 Temporal language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0334` — source line `1704` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.7 Privacy language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0335` — source line `1708` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.7 Privacy language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0336` — source line `1714` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.8 Deployment language**
  > Permitted:
- [ ] `PROSE-SENTINEL-0337` — source line `1718` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.8 Deployment language**
  > Prohibited:
- [ ] `PROSE-SENTINEL-0338` — source line `1722` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.8 Deployment language**
  > No hardware validation supports those claims.
- [ ] `PROSE-SENTINEL-0339` — source line `1728` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > DATP-Core does **not** claim invention of any of the following primitives:
- [ ] `PROSE-SENTINEL-0340` — source line `1742` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > The defensible contribution is the controlled intervention:
- [ ] `PROSE-SENTINEL-0341` — source line `1746` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > The manuscript must distinguish four separate design axes:
- [ ] `PROSE-SENTINEL-0342` — source line `1762` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > Komadina et al. provide direct evidence that the estimator axis is itself broad: their IEEE Access study identifies and implements five supervised and twenty unsupervised threshold-selection methods.[^komadina2024] DATP-Core deliberately does not reproduce that estimator catalogue. Its confirmatory causal comparison manipulates **axis B only**, while the detector/score artifact, type-7 empirical-quantile estimator, and `q=0.95` target are fixed. The q95-versus-moment sensitivity deliberately changes axis A; FedProx/Ditto and preprocessing sensitivity alter upstream detector geometry (axis C or its inputs); the one-shot temporal experiment changes axis D. None can replace the confirmatory axis-B endpoint.
- [ ] `PROSE-SENTINEL-0343` — source line `1764` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > The threshold-related-work subsection must be organized by the object being calibrated or personalized:
- [ ] `PROSE-SENTINEL-0344` — source line `1773` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > At minimum, the following collision table must be represented in the manuscript or supplement and kept current at submission time:
- [ ] `PROSE-SENTINEL-0345` — source line `1798` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > No absolute `first`, `only`, or `state-of-the-art` novelty sentence is permitted unless it is separately re-verified against literature available immediately before submission.
- [ ] `PROSE-SENTINEL-0346` — source line `1802` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9A Submission-time novelty-survival literature gate**
  > Within **14 calendar days before manuscript submission**, repeat a targeted literature search against at least Google Scholar, Semantic Scholar, arXiv, IEEE Xplore, ACM Digital Library, Scopus or Web of Science when institutionally available, and the target journal publisher search. The search date, database/source, exact query string, and top relevant collisions must be retained with the submission evidence.
- [ ] `PROSE-SENTINEL-0347` — source line `1804` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9A Submission-time novelty-survival literature gate**
  > The mandatory query set is:
- [ ] `PROSE-SENTINEL-0348` — source line `1824` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9A Submission-time novelty-survival literature gate**
  > For each query, inspect at minimum the first **50 relevance-ranked results** when the source exposes that many results, plus every 2025–submission-date item whose title/abstract directly concerns distributed/federated calibration, anomaly thresholding, client/site-conditional calibration, or personalized conformal calibration. Duplicate versions of one work are consolidated to the latest authoritative version.
- [ ] `PROSE-SENTINEL-0349` — source line `1826` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9A Submission-time novelty-survival literature gate**
  > A newly discovered collision triggers claim rewording and citation updates, not post-hoc experiment substitution. The gate passes only when:
- [ ] `PROSE-SENTINEL-0350` — source line `1833` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9A Submission-time novelty-survival literature gate**
  > This literature/claim-survival gate is not an authorization to add new experiments after results are known.
- [ ] `PROSE-SENTINEL-0351` — source line `1837` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9B Mandatory source-grounded prior-art distinction table**
  > In addition to the narrative collision table above, the manuscript or supplement must include one compact **method-object distinction table**. This is a related-work evidence table, not an implementation audit.
- [ ] `PROSE-SENTINEL-0352` — source line `1839` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9B Mandatory source-grounded prior-art distinction table**
  > Minimum rows:
- [ ] `PROSE-SENTINEL-0353` — source line `1857` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9B Mandatory source-grounded prior-art distinction table**
  > Required columns, in this order:
- [ ] `PROSE-SENTINEL-0354` — source line `1876` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9B Mandatory source-grounded prior-art distinction table**
  > Every categorical cell must use exactly one of:
- [ ] `PROSE-SENTINEL-0355` — source line `1886` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9B Mandatory source-grounded prior-art distinction table**
  > `NOT_REPORTED` is mandatory when the primary source does not establish the fact; inference must not be silently promoted into a factual table cell. Each row must be traceable to the primary paper/official publication. The table must be updated by the 14-day novelty-survival gate together with the narrative collision table.
- [ ] `PROSE-SENTINEL-0356` — source line `1927` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.11 Negative evidence that must remain publishable**
  > The following limitations are accepted by design and must be disclosed rather than “fixed” through scope expansion.
- [ ] `PROSE-SENTINEL-0357` — source line `1931` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.1 Small natural client population**
  > N-BaIoT provides nine physical-device clients.
- [ ] `PROSE-SENTINEL-0358` — source line `1933` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.1 Small natural client population**
  > The study does not infer fleet-scale behavior from this population.
- [ ] `PROSE-SENTINEL-0359` — source line `1937` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.2 One external dataset**
  > Edge-IIoTset improves external validity but does not establish universal cross-dataset generalization.
- [ ] `PROSE-SENTINEL-0360` — source line `1941` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.3 Incomplete external attack assignment**
  > The available Edge-IIoTset data support benign operating-point equity but not valid per-client attack-sensitive evaluation.
- [ ] `PROSE-SENTINEL-0361` — source line `1945` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.4 Single temporal family**
  > One-shot recalibration on one verified chronological population is a boundary probe, not a general drift solution.
- [ ] `PROSE-SENTINEL-0362` — source line `1949` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.5 No formal privacy guarantee**
  > Federated data locality is retained, but model updates and threshold summaries may disclose information. No formal protection is claimed.
- [ ] `PROSE-SENTINEL-0363` — source line `1953` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.6 No hardware evidence**
  > Estimated message sizes do not establish latency, energy, memory, or deployment feasibility.
- [ ] `PROSE-SENTINEL-0364` — source line `1957` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.7 Threshold trade-offs**
  > Reducing FPR dispersion may worsen attack sensitivity for some clients. The journal contribution includes this trade-off rather than assuming it away.
- [ ] `PROSE-SENTINEL-0365` — source line `1961` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.8 Comparator incompleteness**
  > One aggregation stress family and two bounded client-model adaptation routes (simple post-FedAvg fine-tuning and Ditto) cannot establish superiority over the full FL or personalized-FL literature.
- [ ] `PROSE-SENTINEL-0366` — source line `1965` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.9 Conformal limitation**
  > LOCAL_CONFORMAL_THRESHOLD is an empirical diagnostic under bounded assumptions. It does not establish arbitrary per-client conditional coverage under heterogeneous, non-exchangeable, or adversarial data.
- [ ] `PROSE-SENTINEL-0367` — source line `1969` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.10 Honest-calibration / no Byzantine-integrity guarantee**
  > All threshold-stage results assume the protocol-compliant calibration contract in §3.2A. A compromised client could in principle falsify calibration scores, local thresholds, support counts, summary statistics, cluster fingerprints, or quantile sketches; DATP-Core neither detects nor tolerates such behavior. Rob-FCP and PRISM-FCP show that adversarial calibration is a distinct federated research problem.[^robfcp2024][^prismfcp2026] This limitation is disclosed rather than repaired by adding an attack/defense branch to DATP-Core.
- [ ] `PROSE-SENTINEL-0368` — source line `1973` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.E.11 Persistent identifiable-client limitation**
  > The confirmatory and client-personalized stress results require the Part I §3.3A regime: the same client identity persists across training, calibration, deployment evaluation, and any retained local threshold/personalized-model state, with full training participation. DATP-Core therefore makes **no empirical claim** for massive intermittent cross-device FL, stateless clients, unseen clients that lack a pre-existing local calibration state, or client populations whose identities cannot be linked across stages. The calibration cold-start experiment tests **support scarcity for an identified client**, not unseen-client personalization.
- [ ] `PROSE-SENTINEL-0369` — source line `1979` — **Part I — Scientific Programme and Global Protocol Contracts / 11. Numerical and formula navigation ledger**
  > This ledger is a **lookup index**, not a competing definition. When a conflict exists, the cited authoritative section wins. The purpose is to let implementation and audit work locate every high-risk numerical lock quickly.
- [ ] `PROSE-SENTINEL-0370` — source line `2016` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > Every rule has one owner. Downstream sections inherit the owner and state only deviations or experiment-specific additions.
- [ ] `PROSE-SENTINEL-0371` — source line `2034` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > A duplicated statement in a downstream section is explanatory only; it cannot override the authoritative owner. Any intentional deviation must be named as a separate protocol identity before execution.
- [ ] `PROSE-SENTINEL-0372` — source line `2039` — **Part II — Experiment Programme and Decision Rules**
  > This part defines the complete executable scientific programme. It is deliberately detailed, but it no longer redefines global method or causal contracts already owned by Part I. Each experiment states what changes, what is compared, what evidence must be produced, and how the result may be interpreted.
- [ ] `PROSE-SENTINEL-0373` — source line `2043` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > This index is navigational. Detailed procedures and decision rules remain authoritative in the referenced sections.
- [ ] `PROSE-SENTINEL-0374` — source line `2089` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / 1.1 Evidence-role vocabulary**
  > Every experiment has exactly one primary evidentiary role.
- [ ] `PROSE-SENTINEL-0375` — source line `2092` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Confirmatory**
  > Tests the sole locked journal endpoint. Only the NBAIOT_NATURAL_DEVICES shared-versus-local comparison on `CV(FPR)` is confirmatory.
- [ ] `PROSE-SENTINEL-0376` — source line `2095` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Supportive**
  > Tests robustness of the confirmatory interpretation without becoming a second confirmatory claim.
- [ ] `PROSE-SENTINEL-0377` — source line `2098` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Mechanism analysis**
  > Explains why, when, or for which clients the threshold-scope effect appears. Mechanism analyses may support interpretation but cannot rescue a failed confirmatory endpoint.
- [ ] `PROSE-SENTINEL-0378` — source line `2101` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Threshold variant**
  > Tests a modified threshold-estimation rule while preserving the fixed detector. Variants are evaluated as alternatives or boundary probes, not silently merged into core threshold-scope.
- [ ] `PROSE-SENTINEL-0379` — source line `2104` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / External validation**
  > Tests whether the operating-point effect appears on an independent dataset under a separately audited client definition.
- [ ] `PROSE-SENTINEL-0380` — source line `2107` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Stress test**
  > Changes the training algorithm or model-personalization mechanism and therefore sits outside the controlled core threshold-scope causal comparison.
- [ ] `PROSE-SENTINEL-0381` — source line `2110` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Boundary condition**
  > Identifies settings where DATP is weak, unnecessary, infeasible, or not interpretable.
- [ ] `PROSE-SENTINEL-0382` — source line `2113` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / Exploratory**
  > Generates descriptive or hypothesis-forming evidence that cannot be promoted after results are seen.
- [ ] `PROSE-SENTINEL-0383` — source line `2117` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / 1.2 Experiment specification format**
  > Each mandatory experiment is documented using the same subsections:
- [ ] `PROSE-SENTINEL-0384` — source line `2133` — **Part II — Experiment Programme and Decision Rules / 1. How to read this catalogue / 1.2 Experiment specification format**
  > This structure replaces the previous matrix rows and prevents important requirements from being hidden in dense cells.
- [ ] `PROSE-SENTINEL-0385` — source line `2139` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions**
  > The experiment catalogue is **delta-based**. Unless an experiment explicitly declares a deviation, it inherits the authoritative contracts in Part I and the evaluation/statistical rules in Part III. An experiment-specific section may narrow a contract but may not silently redefine it.
- [ ] `PROSE-SENTINEL-0386` — source line `2143` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.1 Fixed-detector causal isolation — inherited**
  > Authoritative definition: Part I §§2.1–2.4. core threshold-scope share the same detector, preprocessing state, score artifacts, labels, eligibility state, and metric implementation within a fixed comparison coordinate. Threshold scope is the only manipulated variable.
- [ ] `PROSE-SENTINEL-0387` — source line `2147` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.2 Benign-only threshold calibration — inherited**
  > Authoritative definition: Part I §§3.1–3.3. All DATP-compatible threshold methods use benign calibration evidence only. The Laridi distinction is defined once in Part I §6.2.
- [ ] `PROSE-SENTINEL-0388` — source line `2151` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.3 Paired experimental design — inherited**
  > Authoritative scientific pairing: Part I §2.1 and Part III §§1.1–1.3. The independent replication unit is the training seed. Clients, rows, checkpoints, windows, sketch reconstructions, cluster restarts, and calibration subsamples are nested evidence and never inflate the seed count.
- [ ] `PROSE-SENTINEL-0389` — source line `2155` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.3A Deterministic nested-randomness contract**
  > Every newly introduced calibration subsample, cold-start subsample, or other nested experimental draw uses the same deterministic seed derivation. Let `purpose` be an ASCII identifier and let all identity parts be canonical UTF-8 strings. Define
- [ ] `PROSE-SENTINEL-0390` — source line `2164` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.3A Deterministic nested-randomness contract**
  > For calibration-size and cold-start sampling:
- [ ] `PROSE-SENTINEL-0391` — source line `2171` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.3A Deterministic nested-randomness contract**
  > The source calibration pool is first sorted by immutable row identity. One permutation of that ordered pool is generated per `(dataset, population, training_seed, client, replicate_index)`. A sample of size `m` is the first `m` positions of that permutation. Therefore, within one replicate, smaller feasible calibration sets are exact prefixes of larger feasible sets (`m=50` is contained in `m=100`, etc.). Sampling is without replacement. Policies never receive different permutations.
- [ ] `PROSE-SENTINEL-0392` — source line `2173` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.3A Deterministic nested-randomness contract**
  > `replicate_index` is zero-based in `{0,...,9}`. This deterministic subsampling seed is a nested experimental seed only; it is not a new training seed and is summarized within training seed before inference.
- [ ] `PROSE-SENTINEL-0393` — source line `2177` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.4 Eligibility — inherited**
  > Authoritative definition: Part I §3.3. Every result still reports total clients, eligible clients, excluded clients, exclusion reasons, eligibility coverage, and whether compared methods used the identical eligible population.
- [ ] `PROSE-SENTINEL-0394` — source line `2181` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.5 Terminal scientific-model discipline — inherited**
  > Authoritative definition: Part III §13. The locked terminal scientific round is **200**. Recovery and diagnostic checkpoints cannot become scientific detectors or policy-specific score sources.
- [ ] `PROSE-SENTINEL-0395` — source line `2185` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.6 Negative-result discipline**
  > Every mandatory experiment remains reportable when it produces a strong expected effect, weak effect, null effect, reversed effect, unstable estimate, or infeasibility result. No supportive or mechanism result may replace the confirmatory endpoint.
- [ ] `PROSE-SENTINEL-0396` — source line `2189` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.7 Manuscript evidence narrative**
  > The programme is interpreted through four questions; experiments are not presented as an undifferentiated benchmark zoo.
- [ ] `PROSE-SENTINEL-0397` — source line `2198` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.7A Three competing explanations that the programme must eliminate or bound**
  > The manuscript must organize the robustness evidence around three mutually distinguishable reviewer explanations rather than presenting supportive experiments as an algorithm catalogue:
- [ ] `PROSE-SENTINEL-0398` — source line `2204` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.7A Three competing explanations that the programme must eliminate or bound**
  > Calibration-size/shrinkage analyses bound a fourth practical issue—**finite local calibration uncertainty**—without redefining the three causal explanations above. External and temporal experiments bound transport/stationarity rather than replacing the primary explanation test.
- [ ] `PROSE-SENTINEL-0399` — source line `2206` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.7A Three competing explanations that the programme must eliminate or bound**
  > A result may survive one explanation and fail another; the manuscript must report that pattern rather than collapse all evidence into a single robustness adjective.
- [ ] `PROSE-SENTINEL-0400` — source line `2235` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > This table is a manuscript-defence map, not an implementation audit.
- [ ] `PROSE-SENTINEL-0401` — source line `2240` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > Part II does not redefine methods. It references the authoritative scientific definitions below and adds only experiment-specific factors, procedures, and outputs.
- [ ] `PROSE-SENTINEL-0402` — source line `2260` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > Any implementation that changes one of these definitions creates a new protocol identity; it may not inherit the old name silently.
- [ ] `PROSE-SENTINEL-0403` — source line `2267` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / 4.0 Population capability and claim-boundary table**
  > This table is mandatory manuscript/supplement metadata. It prevents an available metric from being mistaken for an authorized scientific claim.
- [ ] `PROSE-SENTINEL-0404` — source line `2277` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / 4.0 Population capability and claim-boundary table**
  > `FPR-equity metrics = Yes` means the roadmap authorizes per-client benign FPR and cross-client dispersion for that population under its own protocol. It does not imply that all threshold methods or all manuscript claims are available there. `Per-client attack metrics = No` is an explicit scientific unavailability state, not missing implementation.
- [ ] `PROSE-SENTINEL-0405` — source line `2283` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scientific role**
  > NBAIOT_NATURAL_DEVICES is the sole confirmatory population and the principal mechanism-analysis substrate.
- [ ] `PROSE-SENTINEL-0406` — source line `2287` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Dataset and population**
  > N-BaIoT contains traffic from nine commercial IoT devices exposed to Mirai and BASHLITE botnet activity in the original dataset study.[^nbaiot] The nine physical devices are the nine federated clients.
- [ ] `PROSE-SENTINEL-0407` — source line `2291` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Permitted analyses**
  > NBAIOT_NATURAL_DEVICES supports:
- [ ] `PROSE-SENTINEL-0408` — source line `2315` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Primary limitation**
  > The population contains only nine physical clients. Client-level results are therefore displayed completely; no client may be filtered because it weakens the desired pattern.
- [ ] `PROSE-SENTINEL-0409` — source line `2321` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scientific role**
  > CICIOT_FILE_CLIENTS tests whether threshold personalization remains useful when the available processed artifacts form near-homogeneous file-defined pseudo-clients rather than natural physical-device clients.
- [ ] `PROSE-SENTINEL-0410` — source line `2325` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Dataset context**
  > The original CICIoT2023 study describes a large IoT topology with 105 devices and 33 attacks grouped into seven categories.[^ciciot2023] Those source-level properties do not automatically survive into every processed CSV distribution.
- [ ] `PROSE-SENTINEL-0411` — source line `2327` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Dataset context**
  > The available data contain 63 file-defined pseudo-clients and lack the metadata required to reconstruct physical-device clients.
- [ ] `PROSE-SENTINEL-0412` — source line `2331` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Permitted interpretation**
  > CICIOT_FILE_CLIENTS may support only an applicability-boundary statement about the file-defined pseudo-clients.
- [ ] `PROSE-SENTINEL-0413` — source line `2333` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Permitted interpretation**
  > It must not be used to claim:
- [ ] `PROSE-SENTINEL-0414` — source line `2352` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Required conclusion discipline**
  > A null shared-versus-local difference is expected to be scientifically useful: it indicates that personalization may be unnecessary when clients are nearly homogeneous.
- [ ] `PROSE-SENTINEL-0415` — source line `2358` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scientific role**
  > NBAIOT_DIRICHLET_CLIENTS tests whether the threshold-scope effect changes systematically with controlled non-IID severity.
- [ ] `PROSE-SENTINEL-0416` — source line `2362` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Population**
  > Twenty synthetic clients are constructed from the N-BaIoT analysis population using the locked Dirichlet partition procedure.
- [ ] `PROSE-SENTINEL-0417` — source line `2370` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Severity grid**
  > Lower `alpha` values represent stronger concentration and more severe distributional skew. Dirichlet partitioning is used only as a controlled sensitivity mechanism; it does not replace the natural physical-device evidence of NBAIOT_NATURAL_DEVICES.
- [ ] `PROSE-SENTINEL-0418` — source line `2378` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Policies**
  > FAMILY_THRESHOLD is not automatically available because the synthetic partition need not preserve the physical family taxonomy.
- [ ] `PROSE-SENTINEL-0419` — source line `2382` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Interpretation**
  > The primary expectation is a graded relationship between heterogeneity and the SHARED_THRESHOLD–LOCAL_THRESHOLD `CV(FPR)` difference.
- [ ] `PROSE-SENTINEL-0420` — source line `2384` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Interpretation**
  > However:
- [ ] `PROSE-SENTINEL-0421` — source line `2395` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scientific role**
  > EDGE_SENSOR_CLIENTS is the independent external validation of benign operating-point equity.
- [ ] `PROSE-SENTINEL-0422` — source line `2399` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Dataset context**
  > The Edge-IIoTset paper presents a purpose-built IoT/IIoT testbed with devices, sensors, protocols, and edge/cloud configurations, designed for centralized and federated-learning security research.[^edge-iiotset]
- [ ] `PROSE-SENTINEL-0423` — source line `2403` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Client definition**
  > Ten benign sensor-group folders form the static external client population. The Modbus folder is valid for static benign-equity evaluation because its rows retain the declared 63-column layout; its `frame.time` values are address literals and therefore exclude it only from the temporal population.
- [ ] `PROSE-SENTINEL-0424` — source line `2405` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Client definition**
  > Eligible-benign coverage is 1.0 under the locked `n_k_source >= 100` rule.
- [ ] `PROSE-SENTINEL-0425` — source line `2409` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Model-input representation and architecture**
  > The canonical Edge rows retain their original lexical values for provenance, but the external detector has a separate, immutable numeric model-input schema. A complete canonical-data audit identified 33 columns for which every non-null value in all 11,209,913 static benign rows parses strictly as a finite numeric value. Those columns, in canonical order, are:
- [ ] `PROSE-SENTINEL-0426` — source line `2423` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Model-input representation and architecture**
  > This is a prospective, versioned numeric-projection amendment. It uses strict numeric parsing only; it does not fill, coerce, hash, ordinal-encode, one-hot encode, or fit a vocabulary for mixed lexical fields. `raw_timestamp`, labels, source folders, and client identity remain provenance or outcome fields and never enter the model. A row whose retained numeric value is null or non-finite is excluded with provenance; no missing value is manufactured. The input feature order is part of the preprocessing protocol checksum and is identical for every client.
- [ ] `PROSE-SENTINEL-0427` — source line `2425` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Model-input representation and architecture**
  > The external autoencoder is therefore a 33-dimensional symmetric model with widths `(33, 25, 17, 11, 8, 11, 17, 25, 33)`. It preserves the locked N-BaIoT model's encoder depth, symmetry, and rounded relative compression ratios while matching the declared schema exactly. Padding the vector to 115 dimensions, truncating an existing model, or silently reusing 115-input weights is prohibited. The Edge-IIoTset source establishes the 61 extracted features and the independent testbed; it does not prescribe a categorical encoder, so no unvalidated categorical transformation is represented as source-locked.[^edge-iiotset]
- [ ] `PROSE-SENTINEL-0428` — source line `2429` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Available outcomes**
  > EDGE_SENSOR_CLIENTS supports:
- [ ] `PROSE-SENTINEL-0429` — source line `2445` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Unavailable outcomes**
  > Attack traffic is confined to the attacker’s subnet. Consequently, valid per-client attack assignment is unavailable.
- [ ] `PROSE-SENTINEL-0430` — source line `2447` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Unavailable outcomes**
  > The following per-client outcomes must be represented as unavailable, not estimated or imputed:
- [ ] `PROSE-SENTINEL-0431` — source line `2458` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Unavailable outcomes**
  > EDGE_SENSOR_CLIENTS therefore validates external false-positive equity, not external cross-client attack-detection equity.
- [ ] `PROSE-SENTINEL-0432` — source line `2462` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / FAMILY_THRESHOLD status**
  > FAMILY_THRESHOLD is omitted because no defensible Edge-IIoTset family taxonomy has been established for the ten sensor-group clients.
- [ ] `PROSE-SENTINEL-0433` — source line `2468` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scientific role**
  > This population tests threshold aging and one-shot recalibration under genuine chronology. It is a temporal boundary experiment, not a drift-detection system.
- [ ] `PROSE-SENTINEL-0434` — source line `2472` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Population**
  > Nine temporal groups are used. Modbus is excluded because its timestamps are unusable.
- [ ] `PROSE-SENTINEL-0435` — source line `2476` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Chronological split**
  > Each client’s benign records are stably sorted by genuine capture time and partitioned as:
- [ ] `PROSE-SENTINEL-0436` — source line `2485` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Chronological split**
  > Duplicate timestamps preserve original stable row order.
- [ ] `PROSE-SENTINEL-0437` — source line `2495` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scope boundary**
  > This experiment does not implement:
- [ ] `PROSE-SENTINEL-0438` — source line `2506` — **Part II — Experiment Programme and Decision Rules / 4. Dataset populations and evaluation settings / Scope boundary**
  > Those belong to Dynamic DATP or later work.
- [ ] `PROSE-SENTINEL-0439` — source line `2516` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Scientific role**
  > **Confirmatory.** This is the only experiment that can establish the locked main journal endpoint.
- [ ] `PROSE-SENTINEL-0440` — source line `2520` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Question**
  > Under one fixed FedAvg autoencoder per seed, does changing the calibration scope from one shared threshold (SHARED_THRESHOLD) to one threshold per physical device (LOCAL_THRESHOLD) reduce cross-client false-positive-rate dispersion on N-BaIoT?
- [ ] `PROSE-SENTINEL-0441` — source line `2524` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Why the experiment is necessary**
  > The conference result used five seeds. The journal extension must reproduce that evidence and expand it to ten paired seeds without suppressing a less favorable estimate.
- [ ] `PROSE-SENTINEL-0442` — source line `2551` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Experimental factor**
  > Threshold-calibration scope:
- [ ] `PROSE-SENTINEL-0443` — source line `2597` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Statistical unit and analysis**
  > The training seed is the independent unit.
- [ ] `PROSE-SENTINEL-0444` — source line `2599` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Statistical unit and analysis**
  > The BCa interval is the confirmatory inferential result. Wilcoxon signed-rank and matched-pairs rank-biserial correlation are descriptive secondary evidence.
- [ ] `PROSE-SENTINEL-0445` — source line `2604` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Confirmatory support**
  > The 95% BCa interval excludes zero in the positive direction.
- [ ] `PROSE-SENTINEL-0446` — source line `2607` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Directional but inconclusive**
  > The point estimate is positive, but the interval touches or crosses zero.
- [ ] `PROSE-SENTINEL-0447` — source line `2610` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / No observed advantage**
  > The estimate is approximately null and the interval includes zero.
- [ ] `PROSE-SENTINEL-0448` — source line `2613` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Opposite direction**
  > LOCAL_THRESHOLD increases `CV(FPR)` relative to SHARED_THRESHOLD.
- [ ] `PROSE-SENTINEL-0449` — source line `2616` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Confirmatory inference unavailable**
  > The locked 95% BCa interval cannot validly be produced (see §5.3). The confirmatory claim is not established; no other interval or test substitutes for it.
- [ ] `PROSE-SENTINEL-0450` — source line `2618` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Confirmatory inference unavailable**
  > Every outcome becomes the main ten-seed result. The five-seed result is labelled preliminary when the ten-seed evidence is weaker or materially different.
- [ ] `PROSE-SENTINEL-0451` — source line `2629` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / 5.2 Anchor reproduction gate**
  > This is an anchor reproduction/compatibility gate. It is not a formal statistical equivalence test. No additional equivalence margin is invented.
- [ ] `PROSE-SENTINEL-0452` — source line `2641` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Locked historical reference**
  > `0.1464` is the operative exact bound used for the pass/fail decision. `0.147` is a display-only rounded representation of the same bound; it never introduces a second, looser threshold.
- [ ] `PROSE-SENTINEL-0453` — source line `2645` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Acceptance conditions**
  > The reproduced five-seed anchor passes only when all of the following hold:
- [ ] `PROSE-SENTINEL-0454` — source line `2662` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / Acceptance conditions**
  > If every condition passes, the existing appropriate anchor-success state is emitted and execution may proceed to the ten-seed extension.
- [ ] `PROSE-SENTINEL-0455` — source line `2666` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / `ANCHOR_REPRODUCTION_FAILED`**
  > If any condition fails, the anchor status is exactly `ANCHOR_REPRODUCTION_FAILED`. This status:
- [ ] `PROSE-SENTINEL-0456` — source line `2685` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / 5.3 Confirmatory inference unavailable**
  > The sole confirmatory endpoint locks a 95% BCa confidence interval (Part III §11.2). `CONFIRMATORY_INFERENCE_UNAVAILABLE` is the explicit outcome when that locked interval cannot validly be produced, including at minimum:
- [ ] `PROSE-SENTINEL-0457` — source line `2693` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / 5.3 Confirmatory inference unavailable**
  > When this occurs, the report must include:
- [ ] `PROSE-SENTINEL-0458` — source line `2702` — **Part II — Experiment Programme and Decision Rules / 5. Confirmatory experiment / 5.3 Confirmatory inference unavailable**
  > **Scientific interpretation.** The confirmatory claim is **not established**. This must not be silently converted to `CONFIRMATORY_SUPPORT` or to `NO_OBSERVED_ADVANTAGE`. No secondary result -- percentile bootstrap, basic bootstrap, normal bootstrap, Wilcoxon, another statistical test, a supportive threshold result, mechanism analysis, an external dataset, a FedProx result, a Ditto result, or an exploratory result -- may rescue an unavailable confirmatory inference. The manuscript must explicitly report that the confirmatory endpoint was inferentially unavailable under the locked protocol while separately reporting descriptive observations.
- [ ] `PROSE-SENTINEL-0459` — source line `2716` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Question**
  > Is the observed shared-versus-local difference caused specifically by SHARED_THRESHOLD’s arithmetic mean of local quantiles, or does it persist across alternative shared-threshold constructions?
- [ ] `PROSE-SENTINEL-0460` — source line `2727` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Comparison set**
  > The KLL and benign-summary methods retain their authoritative method definitions in Part I §6 and their dedicated diagnostics in Part II §9; §6.1 only promotes their **shared-versus-local operating-point contrast** into the mandatory shared-construction robustness panel.
- [ ] `PROSE-SENTINEL-0461` — source line `2731` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Procedure**
  > Use the same NBAIOT_NATURAL_DEVICES model, scores, clients, and seeds as the confirmatory experiment. Recompute thresholds only.
- [ ] `PROSE-SENTINEL-0462` — source line `2733` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Procedure**
  > For each shared construction:
- [ ] `PROSE-SENTINEL-0463` — source line `2744` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Robust construction effect**
  > All reasonable shared constructions retain higher FPR dispersion than LOCAL_THRESHOLD.
- [ ] `PROSE-SENTINEL-0464` — source line `2747` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Construction-specific effect**
  > One shared construction approaches or outperforms LOCAL_THRESHOLD. The claim is narrowed to the locked SHARED_THRESHOLD construction.
- [ ] `PROSE-SENTINEL-0465` — source line `2750` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / No shared-versus-local distinction**
  > Shared constructions and LOCAL_THRESHOLD are practically similar.
- [ ] `PROSE-SENTINEL-0466` — source line `2752` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / No shared-versus-local distinction**
  > This experiment cannot alter the definition of the confirmatory SHARED_THRESHOLD endpoint.
- [ ] `PROSE-SENTINEL-0467` — source line `2762` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Question**
  > Does the SHARED_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD ordering depend on choosing `q = 0.95`?
- [ ] `PROSE-SENTINEL-0468` — source line `2772` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Procedure**
  > For every NBAIOT_NATURAL_DEVICES seed and quantile:
- [ ] `PROSE-SENTINEL-0469` — source line `2780` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Procedure**
  > Where EDGE_SENSOR_CLIENTS supports the same calculation, repeat only the benign-FPR outcomes.
- [ ] `PROSE-SENTINEL-0470` — source line `2784` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Interpretation**
  > An ordering inversion is reported directly. The canonical `q = 0.95` is not changed after inspection.
- [ ] `PROSE-SENTINEL-0471` — source line `2794` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Question**
  > Does the shared-versus-local operating-point effect persist when the threshold estimator changes from the canonical type-7 `q=0.95` quantile to the historical `mean + sample-standard-deviation` rule?
- [ ] `PROSE-SENTINEL-0472` — source line `2810` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Locked 2-by-2 factors**
  > `TYPE7_Q95` reuses canonical SHARED_THRESHOLD and LOCAL_THRESHOLD at `q=0.95`. `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` uses Part I §5.1A exactly (`float64`, sample SD, `ddof=1`).
- [ ] `PROSE-SENTINEL-0473` — source line `2812` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Locked 2-by-2 factors**
  > For each seed `s` and estimator `E`, define the scope gain
- [ ] `PROSE-SENTINEL-0474` — source line `2819` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Locked 2-by-2 factors**
  > Define the estimator-sensitivity contrast
- [ ] `PROSE-SENTINEL-0475` — source line `2826` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Locked 2-by-2 factors**
  > This contrast describes how much the shared-to-local gain changes when the estimator family changes. It is secondary and does not test a new confirmatory hypothesis.
- [ ] `PROSE-SENTINEL-0476` — source line `2856` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Interpretation**
  > The moment estimator never becomes confirmatory and is not described as a new DATP thresholding algorithm.
- [ ] `PROSE-SENTINEL-0477` — source line `2866` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Question**
  > Does stronger client heterogeneity increase the operating-point advantage of local threshold calibration?
- [ ] `PROSE-SENTINEL-0478` — source line `2884` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Procedure**
  > For every seed and severity:
- [ ] `PROSE-SENTINEL-0479` — source line `2897` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Detector training discipline**
  > For every `(training seed, heterogeneity severity)` cell, including IID, a separate terminal `FEDAVG` detector is trained. The training **protocol** remains fixed across severities: model family; architecture apart from feature-schema-driven input dimension; optimizer; loss; training hyperparameters; local epoch count; participation; aggregation semantics; round budget; terminal scientific-model rule; training-seed semantics; and named preprocessing protocol identity.
- [ ] `PROSE-SENTINEL-0480` — source line `2899` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Detector training discipline**
  > The following scientific states must never be shared between different severity/population cells: population-dependent fitted preprocessing state; terminal detector state; calibration scores; evaluation scores.
- [ ] `PROSE-SENTINEL-0481` — source line `2901` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Detector training discipline**
  > Within one fixed `(seed, heterogeneity severity)` cell, SHARED_THRESHOLD, LOCAL_THRESHOLD, and CLUSTER_THRESHOLD use the same terminal detector, fitted preprocessing state, calibration scores, evaluation scores, evaluation labels, and eligibility state.
- [ ] `PROSE-SENTINEL-0482` — source line `2905` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Required heterogeneity diagnostics**
  > At minimum:
- [ ] `PROSE-SENTINEL-0483` — source line `2915` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Interpretation**
  > A smooth monotone curve is not required. Low-alpha conditions may form one broad high-heterogeneity band. The result is associative and does not establish that the selected heterogeneity statistic causally determines DATP benefit.
- [ ] `PROSE-SENTINEL-0484` — source line `2917` — **Part II — Experiment Programme and Decision Rules / 6. Supportive robustness experiments / Interpretation**
  > Comparisons across heterogeneity severities are **supportive / associative**, not threshold-only causal comparisons. Changing heterogeneity changes the federated training problem and may change the resulting detector; cross-severity results must not be interpreted as isolating a causal effect of heterogeneity on threshold scope independently of detector learning.
- [ ] `PROSE-SENTINEL-0485` — source line `2971` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > For silhouette, for client \(i\), let \(a_i\) be its mean Euclidean distance to other members of its assigned cluster and \(b_i\) the minimum mean distance to any other non-empty cluster. Then
- [ ] `PROSE-SENTINEL-0486` — source line `2977` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > A singleton client receives `s_i = 0`, matching the standard silhouette-sample convention. Mean silhouette is unavailable when fewer than two non-empty clusters exist.
- [ ] `PROSE-SENTINEL-0487` — source line `2979` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > For label-stable per-client switch reporting, use the smallest training-seed value as the fixed reference partition. For each other seed, align cluster labels to the reference by the permutation that maximizes client-membership overlap. Client \(k\)'s switch frequency is
- [ ] `PROSE-SENTINEL-0488` — source line `2986` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > Adjusted Rand index remains the primary label-invariant partition-comparison diagnostic; the switch-frequency quantity is an interpretable per-client companion. Because NBAIOT_NATURAL_DEVICES has only nine clients, underlying assignments and contingency tables remain mandatory.[^ari]
- [ ] `PROSE-SENTINEL-0489` — source line `2990` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Recovery-of-local-gap definitions**
  > For grouped method `G in {FAMILY_THRESHOLD,CLUSTER_THRESHOLD}`, define, seed by seed,
- [ ] `PROSE-SENTINEL-0490` — source line `2999` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Recovery-of-local-gap definitions**
  > This quantity is available only when the shared-to-local denominator is strictly greater than `1e-12`. It is **not clipped** to `[0,1]`: values below zero mean the grouped policy is worse than SHARED_THRESHOLD on the primary dispersion metric, and values above one mean it exceeds the LOCAL_THRESHOLD reduction for that seed. If the denominator is `<= 1e-12`, the recovery fraction is `UNAVAILABLE_NO_POSITIVE_LOCAL_GAP`, while the raw CV values remain reportable.
- [ ] `PROSE-SENTINEL-0491` — source line `3021` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Useful middle ground**
  > CLUSTER_THRESHOLD or FAMILY_THRESHOLD recovers a meaningful portion of LOCAL_THRESHOLD’s equity improvement with stable groupings.
- [ ] `PROSE-SENTINEL-0492` — source line `3024` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Performance without stability**
  > CLUSTER_THRESHOLD reduces dispersion, but assignments are unstable. The result is reported as fragile.
- [ ] `PROSE-SENTINEL-0493` — source line `3027` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Stable but unhelpful**
  > Clusters repeat, but do not improve the operating point.
- [ ] `PROSE-SENTINEL-0494` — source line `3030` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / No cluster mechanism**
  > CLUSTER_THRESHOLD is unstable and provides little recovery. CLUSTER_THRESHOLD remains an explored negative mechanism result.
- [ ] `PROSE-SENTINEL-0495` — source line `3038` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mechanism analysis for FAMILY_THRESHOLD.**
  > The locked device-family taxonomy is not assumed to correspond to score-distribution similarity. Its explanatory adequacy is measured.
- [ ] `PROSE-SENTINEL-0496` — source line `3040` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mechanism analysis for FAMILY_THRESHOLD.**
  > For every seed, using eligible NBAIOT_NATURAL_DEVICES clients, calculate pairwise benign-score JS divergence. Let \(\mathcal P_W\) be pairs from the same physical family and \(\mathcal P_B\) pairs from different families:
- [ ] `PROSE-SENTINEL-0497` — source line `3056` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mechanism analysis for FAMILY_THRESHOLD.**
  > For local thresholds \(\tau_k\), report the mean within-family threshold SD over families with at least two eligible members,
- [ ] `PROSE-SENTINEL-0498` — source line `3065` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mechanism analysis for FAMILY_THRESHOLD.**
  > and the SD of family-mean thresholds,
- [ ] `PROSE-SENTINEL-0499` — source line `3072` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mechanism analysis for FAMILY_THRESHOLD.**
  > Singleton families remain listed but do not enter `WithinFamilyThresholdSD`. A non-positive `FamilySeparationJS` is a valid finding and blocks any claim that physical family is a natural score-sharing unit.
- [ ] `PROSE-SENTINEL-0500` — source line `3082` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Why does LOCAL_THRESHOLD reduce FPR dispersion yet sometimes lower P10 Macro-F1?
- [ ] `PROSE-SENTINEL-0501` — source line `3086` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > For all nine NBAIOT_NATURAL_DEVICES clients:
- [ ] `PROSE-SENTINEL-0502` — source line `3112` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Does benign score-distribution heterogeneity predict the magnitude of the local-threshold benefit, and how does that relationship interact with calibration support?
- [ ] `PROSE-SENTINEL-0503` — source line `3116` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked Jensen–Shannon construction**
  > For every fixed score artifact, create one common 64-bin histogram grid from the pooled eligible benign **calibration** scores using type-7 pooled quantiles at probabilities
- [ ] `PROSE-SENTINEL-0504` — source line `3122` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked Jensen–Shannon construction**
  > Collapse duplicate adjacent edges. If fewer than two non-zero-width bins remain, JSD is unavailable for that cell. Every client's histogram uses the exact same edges and is normalized to probability vector \(P_k\).
- [ ] `PROSE-SENTINEL-0505` — source line `3124` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked Jensen–Shannon construction**
  > For probability vectors \(P\) and \(Q\), with \(M=(P+Q)/2\), use base-2 logarithms:
- [ ] `PROSE-SENTINEL-0506` — source line `3137` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked Jensen–Shannon construction**
  > Thus `JSD in [0,1]`. No pseudocount is added. The federation-level heterogeneity summary is the unweighted mean pairwise JSD:
- [ ] `PROSE-SENTINEL-0507` — source line `3146` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Primary association procedure**
  > For each valid population/seed unit:
- [ ] `PROSE-SENTINEL-0508` — source line `3157` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Natural-device leave-one-device-out mechanism influence**
  > Because NBAIOT_NATURAL_DEVICES contains only nine physical clients, the heterogeneity mechanism must show whether one device dominates the measured `H` or the association. This is a nested influence diagnostic, not additional independent evidence.
- [ ] `PROSE-SENTINEL-0509` — source line `3159` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Natural-device leave-one-device-out mechanism influence**
  > For each seed `s` and physical device `j`:
- [ ] `PROSE-SENTINEL-0510` — source line `3173` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Natural-device leave-one-device-out mechanism influence**
  > Let `D` be the full collection of valid `(population,seed)` points used for the primary Spearman association and let `rho_full` be that association. For device `j`, construct `D_(-j)` by replacing only NBAIOT_NATURAL_DEVICES points with their recomputed `(H_(s,-j), DeltaCV_(s,-j))` values; every other population/seed point remains unchanged. Compute `rho_(-j)` on `D_(-j)` and report
- [ ] `PROSE-SENTINEL-0511` — source line `3179` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Natural-device leave-one-device-out mechanism influence**
  > Also report `min_j rho_(-j)`, `max_j rho_(-j)`, and the count of the nine `rho_(-j)` values with the same sign as `rho_full`. The 90 nested `(seed,device)` values are never treated as 90 independent observations and never enter a p-value as independent samples.
- [ ] `PROSE-SENTINEL-0512` — source line `3183` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked heterogeneity × calibration-support interaction**
  > Use only the predeclared population-C subset:
- [ ] `PROSE-SENTINEL-0513` — source line `3193` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked heterogeneity × calibration-support interaction**
  > For each `(seed, alpha)`, compute \(H_{s,\alpha}\) once from the **full source calibration pools** so that the heterogeneity covariate itself is not changed by the experimental `m` subsampling. For `m in {50,100,500}`, use the same fixed-cohort and deterministic nested-subsampling rules as §8.1. `full` is reported as a fourth descriptive column but is excluded from the following numerical interaction regression because it has no common finite `m` value.
- [ ] `PROSE-SENTINEL-0514` — source line `3195` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked heterogeneity × calibration-support interaction**
  > Within each training seed, fit the pre-specified descriptive model across the nine finite `(alpha,m)` cells:
- [ ] `PROSE-SENTINEL-0515` — source line `3206` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Locked heterogeneity × calibration-support interaction**
  > The interaction coefficient \(\beta_{3,s}\) describes whether the heterogeneity–benefit association changes with calibration support. The ten seed-level coefficients are then summarized across seeds; any confidence interval on their mean is secondary BCa evidence. No individual `(alpha,m)` cell is promoted because it is favorable.
- [ ] `PROSE-SENTINEL-0516` — source line `3210` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > For each predeclared `(alpha,m)` cell, show the measured `H`, `CV(FPR)`, P10 Macro-F1, worst-client balanced accuracy, and the set of Pareto-nondominated policies under the two primary directions
- [ ] `PROSE-SENTINEL-0517` — source line `3217` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > using the policies already authorized for the interaction grid. Policy `p` dominates policy `r` in a cell when
- [ ] `PROSE-SENTINEL-0518` — source line `3225` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > with at least one strict inequality. No scalar weighting is introduced.
- [ ] `PROSE-SENTINEL-0519` — source line `3227` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > Every cell receives exactly one typed surface state:
- [ ] `PROSE-SENTINEL-0520` — source line `3236` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > For finite `m`, the manuscript-facing surface uses x=`H` and y=`log10(m/100)`; the `full` cell is shown as a separate aligned column because it has no common finite `m`. Every point is annotated with its `(alpha,m)` identity and typed state. A supplementary table contains the raw policy metrics so the state can be reconstructed exactly.
- [ ] `PROSE-SENTINEL-0521` — source line `3238` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Empirical policy-selection surface — descriptive, not learned**
  > Do **not** fit a classifier, decision tree, regression boundary, policy-learning algorithm, or optimized cutoff from these cells. Do **not** invent universal numerical rules such as “if `H>x`, choose local.” The surface is a descriptive map over the tested populations/support levels, intended to show where shared, local, cluster, or shrinkage policies are empirically nondominated—not a production policy or causal treatment rule.
- [ ] `PROSE-SENTINEL-0522` — source line `3242` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Interpretation**
  > A strong relationship supports a heterogeneity-conditioned interpretation. A weak relationship is a real result and prevents using JS divergence as a sufficient predictor. A material interaction supports calibration-support-conditioned wording. All language remains associative, not causal.
- [ ] `PROSE-SENTINEL-0523` — source line `3252` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > How does the client-specific threshold shift from SHARED_THRESHOLD to LOCAL_THRESHOLD relate to changes in false positives and attack detection?
- [ ] `PROSE-SENTINEL-0524` — source line `3256` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > For every NBAIOT_NATURAL_DEVICES device and seed, compute:
- [ ] `PROSE-SENTINEL-0525` — source line `3270` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > Display:
- [ ] `PROSE-SENTINEL-0526` — source line `3278` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > For each seed, also report exact direction counts over the common evaluable device set:
- [ ] `PROSE-SENTINEL-0527` — source line `3286` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > and, where attack-sensitive TPR is valid,
- [ ] `PROSE-SENTINEL-0528` — source line `3294` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Procedure**
  > Because SHARED_THRESHOLD and LOCAL_THRESHOLD use the identical held-out rows, FPR equality can be checked from identical false-positive counts and TPR equality from identical true-positive counts; no floating-point tolerance or post-hoc “material change” cutoff is introduced. Report all ten seed-level count triples and their median across seeds; do not pool the `9 × 10` device-seed cells as 90 independent observations.
- [ ] `PROSE-SENTINEL-0529` — source line `3298` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Interpretation**
  > This experiment quantifies the equity–sensitivity trade-off surface. It does not claim that threshold movement alone explains every detection change.
- [ ] `PROSE-SENTINEL-0530` — source line `3310` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Are clients with different amounts of source benign calibration support systematically associated with different SHARED_THRESHOLD false-positive burden or different FPR relief from LOCAL_THRESHOLD?
- [ ] `PROSE-SENTINEL-0531` — source line `3312` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > For every NBAIOT_NATURAL_DEVICES training seed `s` and eligible FPR-evaluable client `k`, define
- [ ] `PROSE-SENTINEL-0532` — source line `3328` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Positive `SharedTargetBurden` means the shared threshold produces held-out benign FPR above the nominal target. Positive `PersonalizationRelief` means LOCAL_THRESHOLD lowers that client's FPR relative to SHARED_THRESHOLD.
- [ ] `PROSE-SENTINEL-0533` — source line `3330` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Within each training seed compute exactly two nonredundant Spearman rank correlations across the common valid client set:
- [ ] `PROSE-SENTINEL-0534` — source line `3342` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > `SharedTargetBurden` differs from `FPR_shared` only by the seed-invariant constant `(1-q)`, so its Spearman correlation with support is exactly the same as `\rho^{support,FPR}_s` and is not counted as a third statistic.
- [ ] `PROSE-SENTINEL-0535` — source line `3344` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > For any valid pair of variables `x_k,y_k`, ties use average ranks `R(x_k),R(y_k)` and Spearman correlation is computed as the ordinary Pearson correlation of those ranks:
- [ ] `PROSE-SENTINEL-0536` — source line `3352` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > A coefficient is available only when at least `5` common clients are valid and both ranked variables have at least two distinct values; otherwise emit `INSUFFICIENT_EVIDENCE` or `UNDEFINED_CONSTANT_INPUT` as appropriate. Do **not** compute a client-level inferential p-value from `K=9`.
- [ ] `PROSE-SENTINEL-0537` — source line `3354` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > Reporting is locked to:
- [ ] `PROSE-SENTINEL-0538` — source line `3362` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Question**
  > A negative `\rho^{support,FPR}` (equivalently, negative support–`SharedTargetBurden` association) is consistent with lower-support clients carrying higher shared-threshold FPR burden. A negative `\rho^{support,relief}` is consistent with lower-support clients receiving greater FPR relief from localization. Positive associations indicate the opposite ordering. Either direction is descriptive only: calibration support is not randomized and may correlate with device distribution. The calibration-size experiment in §8.1 remains the controlled test of finite-support threshold stability.
- [ ] `PROSE-SENTINEL-0539` — source line `3372` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > The existing direction counts in §7.5 show whether FPR/TPR moves up or down. This section converts those exact paired client outcomes into a complete **help/harm distribution** so a favorable cross-client average cannot hide a subgroup of devices that becomes worse.
- [ ] `PROSE-SENTINEL-0540` — source line `3374` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Use the same common eligible/evaluable clients and the same held-out rows as the confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD comparison. Define, for seed `s` and device `k`:
- [ ] `PROSE-SENTINEL-0541` — source line `3392` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Positive `FPRRelief` is an FPR improvement. Positive values for the other three differences are utility improvements. Equality is exact from the common integer confusion-count inputs where the metric is rationally determined; no arbitrary floating tolerance or “materiality” threshold is introduced.
- [ ] `PROSE-SENTINEL-0542` — source line `3394` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > For every seed, report:
- [ ] `PROSE-SENTINEL-0543` — source line `3408` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > On the common attack-evaluable client set `K_attack,s`, also report
- [ ] `PROSE-SENTINEL-0544` — source line `3425` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > The FPR-versus-TPR paired categories are:
- [ ] `PROSE-SENTINEL-0545` — source line `3435` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Let `K_attack,s` be the clients for which both FPR and TPR are valid in seed `s`. Compute each category fraction as its client count divided by `|K_attack,s|`. When `|K_attack,s|>0`, the five displayed category fractions must sum to exactly `1` up to floating serialization round-off; persist the integer numerator and denominator for every fraction. When `|K_attack,s|=0`, emit `UNAVAILABLE_NO_COMMON_FPR_TPR_CLIENTS`. Do not discard `NO_FPR_CHANGE` clients or force them into a Pareto category.
- [ ] `PROSE-SENTINEL-0546` — source line `3437` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > For FPR-harmed clients, define the positive harm magnitude
- [ ] `PROSE-SENTINEL-0547` — source line `3443` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > For TPR-lost clients, define
- [ ] `PROSE-SENTINEL-0548` — source line `3449` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Within each seed report the median and maximum positive magnitude among harmed/lost clients. If the relevant set is empty, emit `UNAVAILABLE_NO_FPR_HARMED_CLIENTS` or `UNAVAILABLE_NO_TPR_LOSS_CLIENTS`; do not report a fabricated zero magnitude.
- [ ] `PROSE-SENTINEL-0549` — source line `3451` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Across the ten training seeds, preserve seed as the inferential unit. Report the ten seed-level fractions, their arithmetic mean, median, minimum, and maximum. Additionally, for every physical device `k`, report the descriptive frequencies
- [ ] `PROSE-SENTINEL-0550` — source line `3461` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > For TPR, let `S_k^TPR` be the subset of the ten predeclared seeds in which client `k` has a valid TPR. Define
- [ ] `PROSE-SENTINEL-0551` — source line `3467` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Mandatory client-impact diagnostic for the confirmatory N-BaIoT population; descriptive and seed-aware.**
  > Persist `|S_k^TPR|` beside the frequency. If `|S_k^TPR|=0`, emit `UNAVAILABLE_NO_VALID_TPR_SEEDS`. These frequencies are descriptive repeated-seed stability summaries; the `9×10` cells are not treated as 90 independent observations.
- [ ] `PROSE-SENTINEL-0552` — source line `3471` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > For `NBAIOT_NATURAL_DEVICES`, the support-stratified help/harm analysis is available only when the confirmatory eligible population contains exactly the expected nine devices. Because source-pool size can vary with the locked split seed, define one **campaign-fixed, outcome-blind support score** for device `k` from the ten predeclared training/split seeds:
- [ ] `PROSE-SENTINEL-0553` — source line `3479` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > This score uses source calibration counts only and must be computed before any threshold-policy metric is inspected. Rank the nine devices by ascending `SupportScore_k`; break exact ties by ascending canonical `client_id`. Freeze the resulting strata for the complete campaign:
- [ ] `PROSE-SENTINEL-0554` — source line `3487` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > If `K_e != 9`, emit `UNAVAILABLE_EXPECTED_9_ELIGIBLE_NBAIOT_CLIENTS` for this stratum analysis rather than changing bin sizes post hoc.
- [ ] `PROSE-SENTINEL-0555` — source line `3489` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > For each seed `s` and stratum `g`, compute from its three devices:
- [ ] `PROSE-SENTINEL-0556` — source line `3503` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > and the stratum mean absolute held-out target error for SHARED_THRESHOLD and LOCAL_THRESHOLD:
- [ ] `PROSE-SENTINEL-0557` — source line `3511` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Prospectively fixed calibration-support strata**
  > Summarize each stratum quantity across the same ten seeds by arithmetic mean, median, minimum, and maximum. No client-level p-value and no three-stratum significance test is performed: `n_k_source` is an observed device property, not randomized treatment. The controlled calibration-size experiment in §8.1 remains the causal sensitivity to deliberately reduced local support.
- [ ] `PROSE-SENTINEL-0558` — source line `3519` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > On NBAIOT_NATURAL_DEVICES only, compute held-out attack-family recall separately for the two original N-BaIoT malware families, `Mirai` and `BASHLITE`, whenever the client has at least one held-out sample from that family.
- [ ] `PROSE-SENTINEL-0559` — source line `3521` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > For client \(k\) and family \(f\):
- [ ] `PROSE-SENTINEL-0560` — source line `3530` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > For each seed and policy, additionally define the worst supported family-client recall
- [ ] `PROSE-SENTINEL-0561` — source line `3537` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > and the family macro recall
- [ ] `PROSE-SENTINEL-0562` — source line `3546` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > Report:
- [ ] `PROSE-SENTINEL-0563` — source line `3554` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > A reduction in `CV(FPR)` must never be described as an unqualified operating improvement when it is accompanied by a material deterioration in the displayed family-specific recall outcomes. No post-hoc numeric deterioration cutoff is invented; the exact paired seed/client/family changes are shown and discussed alongside the equity result.
- [ ] `PROSE-SENTINEL-0564` — source line `3556` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive trade-off analysis.**
  > Named sub-attack categories may be shown only as supplementary outcomes when their source labels are preserved and the held-out support is non-zero. Family/sub-attack results never select `q`, `lambda`, cluster count, or policy.
- [ ] `PROSE-SENTINEL-0565` — source line `3564` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > The primary Pareto panel uses NBAIOT_NATURAL_DEVICES, canonical `q=0.95`, and the same ten-seed evidence. For each method, x is lower-is-better `CV(FPR)` and y is higher-is-better `P10(MacroF1)`:
- [ ] `PROSE-SENTINEL-0566` — source line `3579` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > Method \(A\) Pareto-dominates \(B\) iff
- [ ] `PROSE-SENTINEL-0567` — source line `3585` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > with at least one strict inequality. The nondominated set is the complete result; no weighted sum of equity and utility is introduced.
- [ ] `PROSE-SENTINEL-0568` — source line `3587` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > For the main panel, each method's plotted x and y coordinates are the arithmetic means of its ten valid seed-level values. Show a 95% BCa interval for each coordinate as **secondary descriptive uncertainty** when defined; Pareto membership itself is determined from the two arithmetic-mean coordinates, not from overlap/non-overlap of confidence intervals. Seed-level points remain available behind the mean/interval display.
- [ ] `PROSE-SENTINEL-0569` — source line `3589` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > A second mandatory robustness panel uses the same x-coordinate but replaces the utility axis with `WorstBA`:
- [ ] `PROSE-SENTINEL-0570` — source line `3596` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > The same Pareto-dominance definition applies. The P10-Macro-F1 panel remains the primary equity–utility view; the WorstBA panel exists to prevent an acceptable lower-tail macro-F1 value from hiding one client with poor balanced accuracy.
- [ ] `PROSE-SENTINEL-0571` — source line `3598` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > Every method in the primary panel must also have an accompanying target-attainment row containing, at minimum, `MeanAbsoluteTargetError`, `WorstAbsoluteTargetError`, and `MeanAbsoluteCalibrationGeneralizationGap`. These diagnostics do not enter Pareto dominance; they explain whether the displayed equity point corresponds to a well-transferred held-out operating target.
- [ ] `PROSE-SENTINEL-0572` — source line `3600` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > Where attack-sensitive metrics are unavailable, such as the Edge benign-only client assignment, the Pareto panel is unavailable rather than substituting another y-axis post hoc.
- [ ] `PROSE-SENTINEL-0573` — source line `3602` — **Part II — Experiment Programme and Decision Rules / 7. Cluster and family mechanism programme / Supportive synthesis; no scalarized winner.**
  > Quantile-sensitivity Pareto panels may appear only as supplementary facets; they do not replace the canonical q=0.95 panel.
- [ ] `PROSE-SENTINEL-0574` — source line `3614` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > How much benign calibration data is required before local thresholds become stable, and at what support levels does finite-sample local-threshold variance become large relative to the distribution-mismatch cost of a shared threshold?
- [ ] `PROSE-SENTINEL-0575` — source line `3616` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > This experiment operationalizes the pooling bias–variance hypothesis in Part I §5.2. It does not estimate the unknown population quantile `tau_k^*`; instead it jointly reports the locked full-calibration shared/local distance, subsampling variance, `Bias_tau`, `RMSE_tau`, held-out target error, and calibration-to-held-out generalization gap.
- [ ] `PROSE-SENTINEL-0576` — source line `3620` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Two distinct calibration-size quantities**
  > `n_k_source` is client `k`'s benign calibration support before any experimental subsampling (Part I §3.3, locks canonical eligibility at `n_k_source >= 100`). `m` is the calibration sample size drawn for this ablation. Canonical eligibility is fixed from `n_k_source` before this experiment subsamples anything and is never recomputed from `m`.
- [ ] `PROSE-SENTINEL-0577` — source line `3630` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Feasibility rule**
  > A `(client, m)` experimental cell is feasible only when:
- [ ] `PROSE-SENTINEL-0578` — source line `3636` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Feasibility rule**
  > The `m = 50` condition is an explicit **sample-starved supportive/diagnostic condition**, deliberately below the canonical deployment-support requirement of `n_k_source >= 100`. It does not redefine canonical eligibility to 50, and it does not enter the sole confirmatory shared-versus-local endpoint.
- [ ] `PROSE-SENTINEL-0579` — source line `3640` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Fixed-cohort comparator discipline**
  > Within one `m` condition:
- [ ] `PROSE-SENTINEL-0580` — source line `3647` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Fixed-cohort comparator discipline**
  > For cross-size population-level comparisons intended to estimate calibration-size effects, use the intersection of clients feasible across every size directly compared. Size-specific cohorts (all clients feasible at one size, without cross-size intersection) may additionally be reported descriptively only when their coverage and client count are explicit and they are not presented as fixed-cohort calibration-size comparisons.
- [ ] `PROSE-SENTINEL-0581` — source line `3651` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Repetition**
  > Each subsample size must use multiple deterministic subsampling replicates nested within each training seed. Subsampling replicates quantify calibration sampling variability; they are not counted as independent training seeds.
- [ ] `PROSE-SENTINEL-0582` — source line `3653` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Repetition**
  > **Locked replicate count (`CALIBRATION_SUBSAMPLE_REPLICATE_COUNT`, prospective research amendment).** Each subsample size uses exactly `10` deterministic nested replicates per `(training_seed, client)`. The exact SHA-256 → PCG64 seed derivation, immutable-row ordering, one-permutation-per-replicate construction, and prefix nesting across `m` are defined in §2.3A. Replicates are always summarized within seed before any across-seed inference (Part III §12.5); they are never treated as an independent inferential unit and never increase the seed count.
- [ ] `PROSE-SENTINEL-0583` — source line `3666` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Procedure**
  > For every seed, client, size `m`, and subsample replicate:
- [ ] `PROSE-SENTINEL-0584` — source line `3692` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Procedure**
  > Pairs tied in either comparison are reported as ties and excluded from the inversion-rate denominator;
- [ ] `PROSE-SENTINEL-0585` — source line `3706` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Graceful degradation**
  > LOCAL_THRESHOLD remains stable as calibration shrinks.
- [ ] `PROSE-SENTINEL-0586` — source line `3709` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Shrinkage benefit**
  > Naive LOCAL_THRESHOLD destabilizes while shrinkage reduces variance without erasing most personalization.
- [ ] `PROSE-SENTINEL-0587` — source line `3712` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Sample-starved boundary**
  > Local thresholds become unreliable below a clear range. The `m = 50` cell is always this sample-starved supportive/diagnostic condition, never a canonical eligibility redefinition.
- [ ] `PROSE-SENTINEL-0588` — source line `3715` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / No sample-size effect**
  > Threshold stability changes little over the tested grid.
- [ ] `PROSE-SENTINEL-0589` — source line `3717` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / No sample-size effect**
  > The result cannot be summarized using only the best-performing calibration size.
- [ ] `PROSE-SENTINEL-0590` — source line `3725` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > This experiment asks how existing threshold scopes behave while one already-modelled client accumulates benign calibration evidence. It is **not** unseen-device generalization because the detector was trained under the ordinary NBAIOT_NATURAL_DEVICES population.
- [ ] `PROSE-SENTINEL-0591` — source line `3727` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > For each of the nine NBAIOT_NATURAL_DEVICES clients in turn, designate that client as the onboarding target and retain all other clients' full source calibration pools. Use:
- [ ] `PROSE-SENTINEL-0592` — source line `3735` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > Rules at `m = 0`:
- [ ] `PROSE-SENTINEL-0593` — source line `3743` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > Rules at `m > 0`:
- [ ] `PROSE-SENTINEL-0594` — source line `3751` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > Primary target-level outputs are target FPR, signed/absolute target-FPR error, threshold value, threshold RMSE versus the target's full-calibration LOCAL_THRESHOLD threshold, and attack-sensitive controls where available. The mixed-population `CV(FPR)` may be shown secondarily but cannot be interpreted as a pure calibration-size effect because only one target client's support is manipulated at a time.
- [ ] `PROSE-SENTINEL-0595` — source line `3753` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Deployment boundary, never confirmatory.**
  > The experiment may identify an onboarding boundary or fallback behavior; it does not change the canonical `n_k_source >= 100` primary-analysis eligibility rule.
- [ ] `PROSE-SENTINEL-0596` — source line `3763` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > Can partial pooling retain FPR equity while reducing local-threshold variance or detection loss?
- [ ] `PROSE-SENTINEL-0597` — source line `3773` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Procedure**
  > Using the same NBAIOT_NATURAL_DEVICES scores:
- [ ] `PROSE-SENTINEL-0598` — source line `3783` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > The full curve is the result.
- [ ] `PROSE-SENTINEL-0599` — source line `3785` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > A non-monotone response is reported. An intermediate lambda may be described as a useful empirical compromise only if its selection rule is explicitly exploratory or determined without test leakage.
- [ ] `PROSE-SENTINEL-0600` — source line `3795` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > Can personalization weight depend on available benign calibration size without using test outcomes?
- [ ] `PROSE-SENTINEL-0601` — source line `3799` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Requirements**
  > The fixed rule is `lambda(n_k_used) = n_k_used / (n_k_used + 100)`, with 100 inherited from canonical minimum benign support. `n_k_source` remains the complete pre-subsampling support used for eligibility and feasibility, while `n_k_used` is the exact score count used in the local threshold construction. The rule is deterministic, bounded in `[0,1]`, strictly increasing in positive `n_k_used`, independent of all evaluation evidence and downstream metrics, evaluated over the same calibration-size subsamples, and compared with the full fixed-lambda curve and its shared/local endpoints without selection by test outcome.
- [ ] `PROSE-SENTINEL-0602` — source line `3803` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > This is an engineering threshold variant, not a new statistical estimator claim.
- [ ] `PROSE-SENTINEL-0603` — source line `3813` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > Does a finite-sample-adjusted local conformal quantile achieve the intended benign coverage on held-out data, and does cross-client FPR dispersion remain lower than under a shared threshold?
- [ ] `PROSE-SENTINEL-0604` — source line `3817` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Procedure**
  > For every eligible NBAIOT_NATURAL_DEVICES client and seed:
- [ ] `PROSE-SENTINEL-0605` — source line `3840` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > LOCAL_CONFORMAL_THRESHOLD can show that the threshold rule is evaluated through held-out coverage rather than assumed to equalize test FPR by construction.
- [ ] `PROSE-SENTINEL-0606` — source line `3842` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > It does not prove client-conditional validity under arbitrary non-IID shift. Exchangeability limitations must remain explicit.[^split-conformal][^fed-conformal-heterogeneity]
- [ ] `PROSE-SENTINEL-0607` — source line `3852` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > NBAIOT_NATURAL_DEVICES is rerun under exactly two named preprocessing protocols already defined by this roadmap:
- [ ] `PROSE-SENTINEL-0608` — source line `3859` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > Each preprocessing protocol receives its own independently fitted preprocessing state and independently trained FedAvg detector for every training seed. No detector or score artifact is reused across preprocessing protocols.
- [ ] `PROSE-SENTINEL-0609` — source line `3861` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > Within each fixed `(seed, preprocessing_protocol)` detector, evaluate only SHARED_THRESHOLD and LOCAL_THRESHOLD plus the mechanism controls needed to interpret the result:
- [ ] `PROSE-SENTINEL-0610` — source line `3874` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > Differences **within** a preprocessing protocol remain threshold-scope comparisons. Differences **between** preprocessing protocols are supportive sensitivity evidence because preprocessing changes the learned detector geometry. FedBN is relevant prior art for the broader principle that local normalization/state can mitigate feature-shift heterogeneity, but it is **not** implemented here because introducing BatchNorm would alter DATP's locked autoencoder architecture.[^fedbn] A reduction of the DATP effect under pooled MinMax must be reported and cannot trigger replacement of the confirmatory client-local StandardScaler protocol.
- [ ] `PROSE-SENTINEL-0611` — source line `3876` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > For each seed `s`, define
- [ ] `PROSE-SENTINEL-0612` — source line `3888` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > When `Delta_localStd[s] > 1e-12`, report the un-clipped preprocessing-absorption diagnostic
- [ ] `PROSE-SENTINEL-0613` — source line `3895` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Supportive causal-boundary test.**
  > `0` means no attenuation of the threshold-scope gain, `1` means the pooled-MinMax detector has zero shared/local gap, `<0` means the alternative preprocessing increases the gap, and `>1` means the shared/local ordering reverses under pooled MinMax. If the confirmatory-protocol denominator is `<=1e-12`, record `UNAVAILABLE_NO_POSITIVE_LOCAL_STANDARD_GAP`. This diagnostic is descriptive and does not authorize selecting preprocessing from the result.
- [ ] `PROSE-SENTINEL-0614` — source line `3905` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Question**
  > How sensitive is a federation-wide shared threshold to missing client calibration summaries when all clients still retain their own local calibration evidence and remain in the evaluation population?
- [ ] `PROSE-SENTINEL-0615` — source line `3909` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Population and causal lock**
  > Use `NBAIOT_NATURAL_DEVICES` only. For seed `s`, let `E_s` be the fixed eligible client set and `K_s=|E_s|`. This experiment does **not** simulate FL training dropout, client unavailability during optimization, or loss of local calibration data. Every client keeps its original calibration scores, LOCAL_THRESHOLD, test scores, and test labels. The only intervention is that a declared subset does not contribute its local q95 summary to construction of the shared threshold.
- [ ] `PROSE-SENTINEL-0616` — source line `3922` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > A value of `m` is executed only when `K_s-m >= 5`; otherwise the cell is `UNAVAILABLE_TOO_FEW_REMAINING_CONTRIBUTORS`. For the expected nine-client confirmatory population, the exact number of omission subsets per seed is
- [ ] `PROSE-SENTINEL-0617` — source line `3930` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > No stochastic subset sampling is used when exhaustive enumeration is feasible.
- [ ] `PROSE-SENTINEL-0618` — source line `3932` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > For omitted set `U`, construct
- [ ] `PROSE-SENTINEL-0619` — source line `3941` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > Apply `tau_shared[s,U]` to the held-out evaluation scores of **every** client in `E_s`, including clients in `U`. The local comparator is invariant to `U`:
- [ ] `PROSE-SENTINEL-0620` — source line `3947` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > For every subset calculate:
- [ ] `PROSE-SENTINEL-0621` — source line `3959` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > plus `MeanFPR`, `IQR(FPR)`, `Range(FPR)`, `WorstFPR`, `MeanAbsoluteTargetError`, `WorstAbsoluteTargetError`, P10 Macro-F1, and WorstBA where attack metrics are valid.
- [ ] `PROSE-SENTINEL-0622` — source line `3961` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > For each `(seed,m)`, summarize the exhaustive subset distribution with:
- [ ] `PROSE-SENTINEL-0623` — source line `3984` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Locked omission grid**
  > Also record the exact omission set producing `WorstSharedCV` and the exact set producing `MaxAbsoluteThresholdShift`. Across the ten training seeds, report arithmetic mean, median, minimum, and maximum of each **seed-level summary**. Any BCa interval is secondary and may use only the ten seed-level summaries. The 256 within-seed omission subsets are dependent sensitivity cells and are never treated as 256 independent observations.
- [ ] `PROSE-SENTINEL-0624` — source line `3988` — **Part II — Experiment Programme and Decision Rules / 8. Calibration robustness programme / Interpretation**
  > This experiment answers only shared-calibration-summary availability. If shared-threshold behavior degrades as contributors are omitted while LOCAL_THRESHOLD is invariant by construction, the result demonstrates an operational dependency of the shared calibration policy on contributor participation. It does not establish robustness to training-time dropout, stragglers, asynchronous FL, or device failure. A null sensitivity is equally reportable.
- [ ] `PROSE-SENTINEL-0625` — source line `4000` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Question**
  > Does a matched benign-only federated summary-statistics threshold dominate, match, or underperform DATP’s shared and local threshold scopes?
- [ ] `PROSE-SENTINEL-0626` — source line `4017` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Matching rule**
  > The comparator’s target exceedance must be matched to:
- [ ] `PROSE-SENTINEL-0627` — source line `4023` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Matching rule**
  > It may not be tuned on attack labels or F1.
- [ ] `PROSE-SENTINEL-0628` — source line `4048` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Interpretation**
  > `FEDERATED_BENIGN_SUMMARY_THRESHOLD` may:
- [ ] `PROSE-SENTINEL-0629` — source line `4055` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Interpretation**
  > Every outcome is reported. The result does not support a faithful Laridi claim because anomalous validation summaries are excluded.[^laridi]
- [ ] `PROSE-SENTINEL-0630` — source line `4065` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Question**
  > Can a mergeable, quantile-native approximation to the pooled benign `q`-quantile achieve the intended shared operating point without transferring raw calibration-score arrays?
- [ ] `PROSE-SENTINEL-0631` — source line `4084` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Locked factors**
  > KLL is stochastic. Client sketches are always merged in ascending canonical `client_id` order. If the selected implementation exposes a sketch RNG seed, derive it with the §2.3A SHA-256/PCG64 seed contract using `purpose = "KLL"` and identity parts `{dataset_id, population_id, training_seed, client_id, k}`. If the implementation does **not** expose a controllable sketch RNG, lock `KLL_RECONSTRUCTION_REPLICATE_COUNT = 10`: rebuild every client sketch ten times for each `(training_seed,k)`, merge each replicate in the same ascending-client order, and summarize the resulting KLL threshold/rank-error variability within training seed. The exact library version and every serialized sketch artifact are mandatory provenance. KLL reconstruction replicates are nested implementation variability and never count as independent training seeds.
- [ ] `PROSE-SENTINEL-0632` — source line `4097` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Required calculations**
  > For every seed and comparator:
- [ ] `PROSE-SENTINEL-0633` — source line `4110` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Required calculations**
  > The DataSketches reference errors (`1.33%`, `0.68%`, `0.35%` single-sided normalized rank error for `k=200,400,800`) are cited as implementation expectations only; DATP reports its **observed** rank and threshold errors on its score distributions.[^datasketches-kll]
- [ ] `PROSE-SENTINEL-0634` — source line `4112` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Required calculations**
  > No novel sketch or quantile-estimation theorem is claimed.
- [ ] `PROSE-SENTINEL-0635` — source line `4120` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Optional supplementary sensitivity only.**
  > Fixed coefficient values may be evaluated under the benign-only adaptation:
- [ ] `PROSE-SENTINEL-0636` — source line `4126` — **Part II — Experiment Programme and Decision Rules / 9. Federated threshold-estimation programme / Optional supplementary sensitivity only.**
  > This remains a sensitivity of `FEDERATED_BENIGN_SUMMARY_THRESHOLD`; it must not be labelled `LARIDI_ANOMALY_INFORMED_REFERENCE`.
- [ ] `PROSE-SENTINEL-0637` — source line `4140` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Question**
  > Does the shared-versus-local threshold-scope effect appear on an independent sensor-group-partitioned IoT/IIoT dataset?
- [ ] `PROSE-SENTINEL-0638` — source line `4158` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Comparison set**
  > FAMILY_THRESHOLD is omitted.
- [ ] `PROSE-SENTINEL-0639` — source line `4184` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Consistent direction**
  > Supports external benign-equity validation.
- [ ] `PROSE-SENTINEL-0640` — source line `4187` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Weaker or null effect**
  > Defines a cross-dataset boundary.
- [ ] `PROSE-SENTINEL-0641` — source line `4190` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Opposite effect**
  > Narrows the generalization claim.
- [ ] `PROSE-SENTINEL-0642` — source line `4193` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Client assignment or eligibility failure**
  > Produces an infeasibility result; it cannot be repaired by inventing another partition after inspection.
- [ ] `PROSE-SENTINEL-0643` — source line `4203` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Question**
  > When the processed client partitions are near-homogeneous and file-defined, is threshold personalization unnecessary or unidentifiable?
- [ ] `PROSE-SENTINEL-0644` — source line `4215` — **Part II — Experiment Programme and Decision Rules / 10. External validation and applicability boundaries / Interpretation**
  > A null result is not evidence that DATP fails on CICIoT2023’s original physical devices. It is evidence that the available file-defined pseudo-clients do not expose a strong threshold-scope need.
- [ ] `PROSE-SENTINEL-0645` — source line `4223` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / 11.0 Upstream alternative-hypothesis ladder**
  > Training-side stress tests are not ranked as a new algorithm benchmark. They form an ordered falsification ladder for the alternative explanation that DATP merely compensates for an inadequately adapted detector:
- [ ] `PROSE-SENTINEL-0646` — source line `4232` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / 11.0 Upstream alternative-hypothesis ladder**
  > The prospectively tested mechanism is
- [ ] `PROSE-SENTINEL-0647` — source line `4242` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / 11.0 Upstream alternative-hypothesis ladder**
  > This is a **falsifiable mechanism narrative**, not an assumed monotonic ordering. Each method is evaluated independently with the exact common diagnostics from Part I §7.2B. A null/reversed relationship remains a publishable boundary result; it does not authorize adding another PFL method after inspection.
- [ ] `PROSE-SENTINEL-0648` — source line `4252` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Question**
  > Does heterogeneity-aware training absorb the SHARED_THRESHOLD–LOCAL_THRESHOLD threshold-scope effect?
- [ ] `PROSE-SENTINEL-0649` — source line `4256` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Literature rationale**
  > FedProx was designed to address systems and statistical heterogeneity by adding a proximal term to local optimization and generalizing FedAvg.[^fedprox] Its inclusion tests whether better training alignment removes the need for post-training threshold personalization.
- [ ] `PROSE-SENTINEL-0650` — source line `4275` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Coefficient grid**
  > Each declared FedProx coefficient is an independent stress-test condition. Every condition trains its own terminal detector and reports its own outcomes. No coefficient is designated as primary or selected from training, calibration, evaluation, external, or stress-test results.
- [ ] `PROSE-SENTINEL-0651` — source line `4277` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Coefficient grid**
  > The local objective is locked to
- [ ] `PROSE-SENTINEL-0652` — source line `4284` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Coefficient grid**
  > All non-proximal training hyperparameters remain identical to the FedAvg reference unless the original algorithm mathematically requires otherwise.
- [ ] `PROSE-SENTINEL-0653` — source line `4305` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Procedure**
  > No single `mu` is reported as “best FedProx.” The entire grid is the stress-test result.
- [ ] `PROSE-SENTINEL-0654` — source line `4316` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Interpretation**
  > `DriftSuppression <= 0` is reported as `NO_OBSERVED_MEDIAN_DRIFT_SUPPRESSION`; `DriftSuppression > 0` is `OBSERVED_MEDIAN_DRIFT_SUPPRESSION`. These labels are descriptive, not statistical significance or materiality thresholds. No universal claim about FedProx is permitted from the `E=1` DATP stress-test coordinate.
- [ ] `PROSE-SENTINEL-0655` — source line `4318` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Interpretation**
  > FedProx results do not enter the core causal ladder.
- [ ] `PROSE-SENTINEL-0656` — source line `4328` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Question**
  > Does maintaining a personalized model for each client make threshold personalization redundant?
- [ ] `PROSE-SENTINEL-0657` — source line `4332` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Literature rationale**
  > Ditto jointly maintains global and personalized models and was proposed as a general personalized federated-learning framework for statistically heterogeneous clients.[^ditto] It is used here because it can be applied without requiring a hand-defined shared representation/local head split. Current IoT-IDS literature makes this counterfactual reviewer-critical rather than hypothetical: G-PFL-ID evaluates unsupervised personalized federated intrusion detection on IoT-23 and natural-device N-BaIoT,[^gpfli2026] FBID studies adaptive personalized FL under heterogeneous CICIoT2023 and explicit OOD attack conditions,[^fbid2026] and Fed-DTCN couples client-private representation learning with client-specific anomaly thresholds.[^feddtcn2026]
- [ ] `PROSE-SENTINEL-0658` — source line `4334` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Literature rationale**
  > **Comparator-selection rationale.** Ditto is retained for a **causal absorption test**, not because it is claimed to be the newest or strongest IoT IDS. A modern IoT-specific personalized system such as Fed-DTCN changes representation/scoring geometry and threshold deployment jointly, so reproducing it would not isolate whether model personalization alone absorbs the SHARED_THRESHOLD→LOCAL_THRESHOLD effect. Ditto supplies one controlled global-versus-personalized model route while the downstream shared/local threshold comparison remains explicit. G-PFL-ID, FBID, Fed-DTCN, and other PFL-IDS systems are therefore literature counterfactuals, not additional baselines.
- [ ] `PROSE-SENTINEL-0659` — source line `4343` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Primary comparison**
  > The interpretable 2-by-2 core is:
- [ ] `PROSE-SENTINEL-0660` — source line `4350` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Primary comparison**
  > FAMILY_THRESHOLD and CLUSTER_THRESHOLD may be applied as supplementary threshold scopes to the personalized scores.
- [ ] `PROSE-SENTINEL-0661` — source line `4363` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Locked personalization grid**
  > For client \(k\), the personalized objective is
- [ ] `PROSE-SENTINEL-0662` — source line `4370` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Locked personalization grid**
  > All three λ conditions train independent persistent personalized states and are reported. Only λ=1.0 determines the locked canonical absorption wording; sensitivity values cannot replace it after inspection.
- [ ] `PROSE-SENTINEL-0663` — source line `4403` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Absorption measure**
  > When `Delta_FedAvg > 1e-12`, additionally report the normalized absorption fraction
- [ ] `PROSE-SENTINEL-0664` — source line `4410` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Absorption measure**
  > This is exactly the generic `ScopeAbsorption` definition from Part I §7.2B for canonical Ditto (`lambda_D=1.0`); implementations must compute one authoritative quantity and may expose `AbsorptionFraction` only as a manuscript-facing alias.
- [ ] `PROSE-SENTINEL-0665` — source line `4412` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Absorption measure**
  > It is not clipped. `AbsorptionFraction=0` means no absorption; `0.5` means Ditto removes half of the FedAvg shared-to-local gain; `1` means the canonical Ditto shared/local difference is zero; values `<0` mean model personalization amplifies the threshold-scope gain; values `>1` occur when the Ditto shared/local ordering reverses and must be labelled **reversal**, not “more than complete absorption.” If `Delta_FedAvg <= 1e-12`, the normalized fraction is `UNAVAILABLE_NO_POSITIVE_FEDAVG_GAP` and only the raw deltas are interpreted.
- [ ] `PROSE-SENTINEL-0666` — source line `4414` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Absorption measure**
  > Interpretation bands, applied only when `Delta_FedAvg > 1e-12`:
- [ ] `PROSE-SENTINEL-0667` — source line `4422` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Absorption measure**
  > The absorption calculation is performed seed by seed and summarized across the ten paired training seeds; a ratio of campaign-level means is not substituted for the mean/median of valid seed-level absorption fractions.
- [ ] `PROSE-SENTINEL-0668` — source line `4426` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Scope boundary**
  > This is one stress test, not an exhaustive personalized-FL benchmark. APFL, Per-FedAvg, pFedMe, FedRep, FedPer, and broad architecture comparisons are not added to this paper.
- [ ] `PROSE-SENTINEL-0669` — source line `4438` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Question**
  > Does a simple, literature-backed local adaptation of the terminal FedAvg detector absorb the SHARED_THRESHOLD–LOCAL_THRESHOLD effect without introducing a specialized PFL algorithm?
- [ ] `PROSE-SENTINEL-0670` — source line `4442` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Literature rationale**
  > The peer-reviewed personalized-FL benchmark by Matsuda et al. reports that standard FL with client-local fine-tuning can be highly competitive with dedicated PFL methods.[^matsuda-pfl] Cheng et al. provide a separate primary empirical precedent for fine-tuned FedAvg and use 10 local personalization epochs before evaluation; DATP locks that value prospectively and does not tune it on its anomaly-detection outcomes.[^cheng-ftfa]
- [ ] `PROSE-SENTINEL-0671` — source line `4456` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Primary 2-by-2 comparison**
  > The exact fine-tuning optimizer/data/checkpoint contract is inherited from Part I §7.2A. No calibration/test row or attack label may enter fine-tuning.
- [ ] `PROSE-SENTINEL-0672` — source line `4475` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Procedure**
  > and when `Delta_FedAvg,s > 1e-12`,
- [ ] `PROSE-SENTINEL-0673` — source line `4488` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Interpretation**
  > Use the exact generic `ScopeAbsorption` bands from Part I §7.2B; do not invent fine-tuning-specific “small”, “material”, or “near zero” cutoffs. In addition, define one campaign-level mechanism-activation label from the five alignment quantities. Let `MeanAlignmentReduction_X` be the arithmetic mean of the valid ten seed-level `AlignmentReduction^X` values for each `X`. Emit
- [ ] `PROSE-SENTINEL-0674` — source line `4494` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Interpretation**
  > if **at least one** available `MeanAlignmentReduction_X > 0`; otherwise emit
- [ ] `PROSE-SENTINEL-0675` — source line `4500` — **Part II — Experiment Programme and Decision Rules / 11. Training-side stress tests / Interpretation**
  > when every available mean is `<=0`. If all five alignment-reduction quantities are unavailable, emit `ALIGNMENT_ACTIVATION_UNAVAILABLE`. This is a sign-based descriptive label, not a significance or materiality test. The raw quantities remain primary. This stress test cannot replace or rescue the FedAvg confirmatory result.
- [ ] `PROSE-SENTINEL-0676` — source line `4512` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Question**
  > When thresholds are calibrated on historical benign behavior, does future benign behavior increase cross-client FPR dispersion, and can one future benign recalibration window recover it?
- [ ] `PROSE-SENTINEL-0677` — source line `4524` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Static reference**
  > Random-fractional split over the same nine groups, used to estimate ordinary sampling variation without chronology.
- [ ] `PROSE-SENTINEL-0678` — source line `4527` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Frozen future**
  > Thresholds fitted from historical calibration and applied unchanged to future evaluation.
- [ ] `PROSE-SENTINEL-0679` — source line `4530` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / One-shot recalibrated future**
  > Thresholds recomputed once from the future recalibration window and applied to future evaluation.
- [ ] `PROSE-SENTINEL-0680` — source line `4574` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Procedure**
  > `recovery_ratio` is undefined when `drift_excess` is not meaningfully positive.
- [ ] `PROSE-SENTINEL-0681` — source line `4578` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Additional locked client-level temporal diagnostics**
  > For every client \(k\), also calculate threshold drift
- [ ] `PROSE-SENTINEL-0682` — source line `4584` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Additional locked client-level temporal diagnostics**
  > and FPR deterioration/recovery
- [ ] `PROSE-SENTINEL-0683` — source line `4596` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Additional locked client-level temporal diagnostics**
  > Calculate client-level benign drift JSD between the historical calibration and future recalibration windows using one 64-bin common quantile grid built from the union of those two benign windows for that client, with the same base-2 JSD formula as §7.4. Report Spearman association between `DriftJS_k` and `FrozenFPRDeterioration_k` within each seed when at least five valid client pairs exist.
- [ ] `PROSE-SENTINEL-0684` — source line `4598` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Additional locked client-level temporal diagnostics**
  > Report helped/harmed/unchanged client fractions, with exact zero defining unchanged:
- [ ] `PROSE-SENTINEL-0685` — source line `4605` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Additional locked client-level temporal diagnostics**
  > Report worst-client recovery:
- [ ] `PROSE-SENTINEL-0686` — source line `4635` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Temporal degradation with recovery**
  > Frozen future dispersion exceeds the static reference and one-shot recalibration recovers a meaningful portion.
- [ ] `PROSE-SENTINEL-0687` — source line `4638` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / Temporal degradation without recovery**
  > Drift excess is positive, but one-shot recalibration provides little or negative recovery.
- [ ] `PROSE-SENTINEL-0688` — source line `4641` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / No detectable temporal degradation**
  > Frozen future dispersion does not meaningfully exceed the static reference; recovery ratio remains undefined.
- [ ] `PROSE-SENTINEL-0689` — source line `4643` — **Part II — Experiment Programme and Decision Rules / 12. Temporal recalibration experiment / No detectable temporal degradation**
  > No outcome justifies claiming a complete concept-drift solution.
- [ ] `PROSE-SENTINEL-0690` — source line `4657` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Question**
  > What does a difference in FPR mean in approximate alerts per device per day?
- [ ] `PROSE-SENTINEL-0691` — source line `4661` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Required external input**
  > A real measured or appropriately cited benign traffic rate:
- [ ] `PROSE-SENTINEL-0692` — source line `4669` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Calculation**
  > For client \(k\):
- [ ] `PROSE-SENTINEL-0693` — source line `4690` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Suppression rule**
  > When no real or cited rate is available, omit the metric. Do not invent a nominal rate merely to populate a table or figure.
- [ ] `PROSE-SENTINEL-0694` — source line `4698` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Scientific role**
  > **Supportive systems characterization only.** It does not establish edge deployment, energy efficiency, network latency, or hardware suitability.
- [ ] `PROSE-SENTINEL-0695` — source line `4702` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > For each policy/comparator, report both the logical fields disclosed and the actual serialized byte count. The actual serializer output is authoritative; the minimum raw-field counts below are explanatory lower bounds before framing/metadata overhead:
- [ ] `PROSE-SENTINEL-0696` — source line `4714` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > If family/cluster metadata are already part of an authenticated population manifest, do not double-count them as per-execution communication; state that they are pre-existing metadata.
- [ ] `PROSE-SENTINEL-0697` — source line `4718` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Disclosure inventory**
  > For every method, explicitly state whether the server observes an individual client's threshold, moments, fingerprint, sketch, family membership, or cluster assignment. “Raw calibration records are not transmitted” is permitted when true. “Private” or “privacy preserving” is forbidden without a formal mechanism.
- [ ] `PROSE-SENTINEL-0698` — source line `4722` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Runtime benchmark protocol**
  > Threshold construction is timed after score arrays are already materialized in memory, so detector scoring and disk I/O are excluded.
- [ ] `PROSE-SENTINEL-0699` — source line `4732` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Runtime benchmark protocol**
  > For KLL, client build/serialization and server deserialize/merge/query are reported separately. For SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/FedStats/shrinkage, report client-side construction and server aggregation separately where both exist.
- [ ] `PROSE-SENTINEL-0700` — source line `4734` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Runtime benchmark protocol**
  > Peak server memory is `peak RSS - pre-operation RSS`, sampled at no slower than 10 ms during the measured operation. If the runtime environment cannot produce reliable RSS sampling, peak memory is `UNAVAILABLE_MEASUREMENT_NOT_SUPPORTED`; Python-only allocator measurements must not be mislabeled as process memory.
- [ ] `PROSE-SENTINEL-0701` — source line `4736` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Runtime benchmark protocol**
  > Hardware/OS/runtime/library versions are recorded with every timing table. Cross-machine timing comparisons are forbidden.
- [ ] `PROSE-SENTINEL-0702` — source line `4740` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses**
  > These analyses are useful but cannot delay the mandatory programme unless a reviewer-critical gap remains.
- [ ] `PROSE-SENTINEL-0703` — source line `4744` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.1 Robust cluster-median threshold**
  > Replace the mean of cluster-member local thresholds with a median and compare outlier sensitivity.
- [ ] `PROSE-SENTINEL-0704` — source line `4746` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.1 Robust cluster-median threshold**
  > Report:
- [ ] `PROSE-SENTINEL-0705` — source line `4754` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.1 Robust cluster-median threshold**
  > This remains supplementary.
- [ ] `PROSE-SENTINEL-0706` — source line `4758` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.2 Additional equity indices**
  > Report, alongside rather than instead of `CV(FPR)`:
- [ ] `PROSE-SENTINEL-0707` — source line `4767` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.2 Additional equity indices**
  > The primary endpoint remains unchanged.
- [ ] `PROSE-SENTINEL-0708` — source line `4771` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.3 Extended secondary uncertainty**
  > Provide:
- [ ] `PROSE-SENTINEL-0709` — source line `4778` — **Part II — Experiment Programme and Decision Rules / 14. Optional high-value analyses / 14.3 Extended secondary uncertainty**
  > Multiplicity treatment must follow Part III — Evaluation, Statistical Analysis, and Reporting.
- [ ] `PROSE-SENTINEL-0710` — source line `4782` — **Part III — Evaluation, Statistical Analysis, and Reporting**
  > This part owns metric semantics, inferential units, statistical decision rules, temporal quantities, and reporting discipline. It inherits the scientific identities and eligibility rules from Part I and the experiment-specific designs from Part II.
- [ ] `PROSE-SENTINEL-0711` — source line `4788` — **Part III — Evaluation, Statistical Analysis, and Reporting / 1. Evaluation contract / 1.1 Fixed-score comparison — inherited contract**
  > The authoritative fixed-detector and fixed-score rules are Part I §§2.1–2.4, especially §2.2.2. Part III does not redefine them. Evaluation must consume the canonical score/label artifact identities established there; serialization tolerance is never a substitute for scientific score identity.
- [ ] `PROSE-SENTINEL-0712` — source line `4792` — **Part III — Evaluation, Statistical Analysis, and Reporting / 1. Evaluation contract / 1.2 Independent unit**
  > The training seed is the independent replication unit.
- [ ] `PROSE-SENTINEL-0713` — source line `4794` — **Part III — Evaluation, Statistical Analysis, and Reporting / 1. Evaluation contract / 1.2 Independent unit**
  > Clients, rows, checkpoints, attack categories, calibration subsamples, cluster initializations, and temporal windows are not independent replications.
- [ ] `PROSE-SENTINEL-0714` — source line `4800` — **Part III — Evaluation, Statistical Analysis, and Reporting / 1. Evaluation contract / 1.3 Per-client-first reporting**
  > Metrics are calculated per client before cross-client aggregation whenever valid client identity exists.
- [ ] `PROSE-SENTINEL-0715` — source line `4802` — **Part III — Evaluation, Statistical Analysis, and Reporting / 1. Evaluation contract / 1.3 Per-client-first reporting**
  > Pooled-row metrics may be reported as controls but cannot replace client-level operating-point metrics.
- [ ] `PROSE-SENTINEL-0716` — source line `4808` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > For score \(e\) and threshold \(\tau\):
- [ ] `PROSE-SENTINEL-0717` — source line `4819` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > The comparison operator is fixed across policies.
- [ ] `PROSE-SENTINEL-0718` — source line `4821` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > For client \(k\):
- [ ] `PROSE-SENTINEL-0719` — source line `4828` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > All counts come from held-out test rows. Calibration rows never enter reported test metrics.
- [ ] `PROSE-SENTINEL-0720` — source line `4830` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > A higher reconstruction error must always indicate greater anomaly evidence.
- [ ] `PROSE-SENTINEL-0721` — source line `4832` — **Part III — Evaluation, Statistical Analysis, and Reporting / 2. Prediction and confusion counts**
  > This invariant is structurally guaranteed by the mean-squared-error formula used in reconstruction error computation (non-negative by construction; a model collapse to constant output would be caught by the checkpoint validation checksum and CUDA-device requirements). The perturbation-based empirical polarity experiment previously in ``scoring/reconstruction.py`` was removed as redundant with the structural definition and because the additive-perturbation heuristic could admit false-negatives on well-trained detectors. The score semantics remain auditable through the reconstruction-error computation path itself rather than through a manifest field.
- [ ] `PROSE-SENTINEL-0722` — source line `4840` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.1 Calibration eligibility — inherited contract**
  > The authoritative eligibility definition is Part I §3.3: `n_k_source >= 100`, where `n_k_source` is equivalently the `benign_calibration_count`, determined from the source benign calibration pool before experimental subsampling and held fixed across compared policies. Part II §8.1 separately defines the experimental sample size `m`.
- [ ] `PROSE-SENTINEL-0723` — source line `4844` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.2 FPR-evaluable population**
  > A client additionally requires a non-empty benign test denominator.
- [ ] `PROSE-SENTINEL-0724` — source line `4848` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.3 Attack-evaluable population**
  > Attack-sensitive metrics additionally require:
- [ ] `PROSE-SENTINEL-0725` — source line `4854` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.3 Attack-evaluable population**
  > A client may be FPR-evaluable but unavailable for TPR, balanced accuracy, Macro-F1, or AUROC.
- [ ] `PROSE-SENTINEL-0726` — source line `4856` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.3 Attack-evaluable population**
  > This distinction is mandatory for Edge-IIoTset.
- [ ] `PROSE-SENTINEL-0727` — source line `4866` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.4 Coverage**
  > Report candidate, eligible, attack-evaluable, fallback, and excluded client counts, with an exclusion reason per client.
- [ ] `PROSE-SENTINEL-0728` — source line `4868` — **Part III — Evaluation, Statistical Analysis, and Reporting / 3. Metric populations / 3.4 Coverage**
  > Ineligible fallback clients do not enter the primary `CV(FPR)` calculation.
- [ ] `PROSE-SENTINEL-0729` — source line `4882` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.1 False-positive rate**
  > Unavailable when the benign denominator is zero.
- [ ] `PROSE-SENTINEL-0730` — source line `4892` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.2 True-positive rate**
  > Unavailable when the attack denominator is zero or client-level attack assignment is invalid.
- [ ] `PROSE-SENTINEL-0731` — source line `4902` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.3 Balanced accuracy**
  > Unavailable unless both FPR and TPR are available.
- [ ] `PROSE-SENTINEL-0732` — source line `4906` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.4 Per-client Macro-F1**
  > Calculate benign-class and attack-class F1 separately, then:
- [ ] `PROSE-SENTINEL-0733` — source line `4918` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.4 Per-client Macro-F1**
  > Macro-F1 is unavailable when a required class or denominator is absent.
- [ ] `PROSE-SENTINEL-0734` — source line `4920` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.4 Per-client Macro-F1**
  > Do not silently convert undefined class metrics to zero.
- [ ] `PROSE-SENTINEL-0735` — source line `4924` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.5 AUROC**
  > AUROC uses continuous anomaly scores and requires both classes. AUROC is computed from the fixed continuous evaluation-score and evaluation-label artifact; threshold-calibration scope is not an AUROC input (Part I §2.2.2).
- [ ] `PROSE-SENTINEL-0736` — source line `4926` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.5 AUROC**
  > Within a fixed-score core threshold-scope comparison, AUROC is computed once from the canonical score/label artifact, or is proven to derive from that exact artifact by scientific artifact identity (matching score-artifact identity, ordered row identities, client identities, split identities, detector identity, checkpoint identity, and preprocessing identity) rather than by numerical closeness. A policy-dependent AUROC difference indicates a score/provenance identity failure, not a threshold-scope effect.
- [ ] `PROSE-SENTINEL-0737` — source line `4928` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.5 AUROC**
  > AUROC is a model-quality control, not a threshold-policy verdict.
- [ ] `PROSE-SENTINEL-0738` — source line `4932` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.6 Average precision / PR-curve summary**
  > Average precision (`AP`) is the locked precision–recall summary and is reported as the AUPRC-style detector-quality control. It uses the continuous anomaly score and requires at least one attack-positive evaluation row.
- [ ] `PROSE-SENTINEL-0739` — source line `4934` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.6 Average precision / PR-curve summary**
  > With precision \(P_n\) and recall \(R_n\) at the distinct descending score thresholds, compute the standard step-integral average precision:
- [ ] `PROSE-SENTINEL-0740` — source line `4940` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.6 Average precision / PR-curve summary**
  > A trapezoidal PR-AUC must not be silently substituted under the same metric name. Within a fixed-score threshold ladder, AP is computed once from the canonical score/label artifact exactly like AUROC. Any SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD-specific AP difference is a provenance failure.
- [ ] `PROSE-SENTINEL-0741` — source line `4944` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.7 Held-out benign target-attainment error**
  > For any policy targeting quantile \(q\), the nominal held-out benign FPR target is
- [ ] `PROSE-SENTINEL-0742` — source line `4950` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.7 Held-out benign target-attainment error**
  > For FPR-evaluable client \(k\):
- [ ] `PROSE-SENTINEL-0743` — source line `4960` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.7 Held-out benign target-attainment error**
  > Across eligible FPR-evaluable clients report:
- [ ] `PROSE-SENTINEL-0744` — source line `4967` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.7 Held-out benign target-attainment error**
  > plus median absolute target error and
- [ ] `PROSE-SENTINEL-0745` — source line `4973` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.7 Held-out benign target-attainment error**
  > These are held-out operating-point diagnostics. Calibration-set exceedance is not substituted for held-out target attainment.
- [ ] `PROSE-SENTINEL-0746` — source line `4977` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > For every client/policy with a scalar deployed threshold `tau_k` and `n_k_used > 0` benign calibration scores, define the realized calibration exceedance
- [ ] `PROSE-SENTINEL-0747` — source line `4986` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > Use strict `>` because the prediction rule declares an anomaly only when the reconstruction error exceeds the threshold. Ties at the threshold are therefore non-anomalous in both calibration and evaluation calculations.
- [ ] `PROSE-SENTINEL-0748` — source line `4988` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > The held-out benign generalization gap is
- [ ] `PROSE-SENTINEL-0749` — source line `4995` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > with absolute form
- [ ] `PROSE-SENTINEL-0750` — source line `5002` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > Across the common eligible FPR-evaluable client set report:
- [ ] `PROSE-SENTINEL-0751` — source line `5009` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > plus median absolute gap, maximum absolute gap, and the signed client-level gaps.
- [ ] `PROSE-SENTINEL-0752` — source line `5011` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > This diagnostic is mandatory for SHARED_THRESHOLD, LOCAL_THRESHOLD, FAMILY_THRESHOLD, CLUSTER_THRESHOLD, exact pooled/shared construction controls, the q95-versus-moment estimator sensitivity, and shrinkage policies whenever their threshold can be applied to the same calibration scores. It is descriptive for calibration transfer; it never feeds threshold fitting, model selection, client eligibility, or policy selection.
- [ ] `PROSE-SENTINEL-0753` — source line `5013` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8 Calibration-to-held-out benign generalization gap**
  > For `LOCAL_CONFORMAL_THRESHOLD`, the roadmap's conformal coverage diagnostics remain authoritative; this empirical gap may be shown only as an additional descriptive quantity and must not be called a conformal validity guarantee.
- [ ] `PROSE-SENTINEL-0754` — source line `5017` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > A predictable reviewer objection is formalized as
- [ ] `PROSE-SENTINEL-0755` — source line `5025` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > DATP-Core rejects this explanation by design: calibration and evaluation row identities are disjoint under Part I §3.2, and the integrity gate verifies that no evaluation row enters threshold estimation.
- [ ] `PROSE-SENTINEL-0756` — source line `5027` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > For client `k`, policy `p`, and `q=0.95`, define the already-authorized calibration exceedance
- [ ] `PROSE-SENTINEL-0757` — source line `5035` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > and its nominal calibration-target error
- [ ] `PROSE-SENTINEL-0758` — source line `5042` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > The held-out error is
- [ ] `PROSE-SENTINEL-0759` — source line `5049` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > which is the same quantity as `SignedTestFPRTargetError` in §4.7. Their transfer difference is
- [ ] `PROSE-SENTINEL-0760` — source line `5057` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > Therefore even if an empirical local q95 yields calibration exceedance close to `0.05`, it **does not algebraically force** held-out FPR to equal `0.05`. Sampling variation, calibration/evaluation distribution shift, and finite support remain visible in `SignedTestFPRTargetError`, `AbsoluteTestFPRTargetError`, and `CalibrationGeneralizationGap`.
- [ ] `PROSE-SENTINEL-0761` — source line `5059` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > Mandatory confirmatory reporting for SHARED_THRESHOLD and LOCAL_THRESHOLD includes, by client and seed:
- [ ] `PROSE-SENTINEL-0762` — source line `5067` — **Part III — Evaluation, Statistical Analysis, and Reporting / 4. Per-client metrics / 4.8A Explicit `H_TAUTOLOGY` rebuttal — local q95 does not force held-out FPR**
  > No p-value is attached to `H_TAUTOLOGY`; it is a **design-level falsification condition**. Any overlap between the calibration and evaluation row-identity sets makes the affected result invalid rather than “supporting” or “rejecting” the hypothesis empirically.
- [ ] `PROSE-SENTINEL-0763` — source line `5073` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics**
  > Let \(K_e\) be the eligible FPR-evaluable client count.
- [ ] `PROSE-SENTINEL-0764` — source line `5084` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.1 Mean FPR**
  > The primary equity calculation is unweighted by client row count.
- [ ] `PROSE-SENTINEL-0765` — source line `5098` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > Use:
- [ ] `PROSE-SENTINEL-0766` — source line `5104` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > Bessel's correction is locked so that the estimator convention matches the
- [ ] `PROSE-SENTINEL-0767` — source line `5105` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > historical DATP metric definition and the locked anchor reference
- [ ] `PROSE-SENTINEL-0768` — source line `5106` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > `[0.647, 0.769]`, which was derived with `ddof = 1`. Reproduction compares the
- [ ] `PROSE-SENTINEL-0769` — source line `5107` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > re-implemented pipeline to that historical reference, so both sides must share
- [ ] `PROSE-SENTINEL-0770` — source line `5108` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > the same estimator; the `sqrt(K_e / (K_e - 1)) = 1.061` convention mismatch
- [ ] `PROSE-SENTINEL-0771` — source line `5109` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.2 Sample standard deviation**
  > would otherwise bias every reproduction comparison.
- [ ] `PROSE-SENTINEL-0772` — source line `5119` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.3 Coefficient of variation**
  > No epsilon or denominator stabilizer is permitted.
- [ ] `PROSE-SENTINEL-0773` — source line `5121` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.3 Coefficient of variation**
  > When `mean(FPR) = 0`:
- [ ] `PROSE-SENTINEL-0774` — source line `5127` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.3 Coefficient of variation**
  > When the mean is positive but very close to zero, retain the numerical CV only with a near-zero-denominator warning.
- [ ] `PROSE-SENTINEL-0775` — source line `5129` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.3 Coefficient of variation**
  > Such cells are interpreted only alongside absolute dispersion.
- [ ] `PROSE-SENTINEL-0776` — source line `5153` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.5 TPR and lower-tail metrics**
  > Where attack evaluation is valid:
- [ ] `PROSE-SENTINEL-0777` — source line `5162` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.5 TPR and lower-tail metrics**
  > The same zero-denominator rules apply.
- [ ] `PROSE-SENTINEL-0778` — source line `5176` — **Part III — Evaluation, Statistical Analysis, and Reporting / 5. Cross-client operating-point metrics / 5.5 TPR and lower-tail metrics**
  > Report the number of attack-evaluable clients with each aggregate.
- [ ] `PROSE-SENTINEL-0779` — source line `5182` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics**
  > Optional metrics accompany `CV(FPR)` and never replace it.
- [ ] `PROSE-SENTINEL-0780` — source line `5196` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 6.1 Jain index**
  > Undefined when all FPR values are zero.
- [ ] `PROSE-SENTINEL-0781` — source line `5210` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 6.2 Gini coefficient**
  > Undefined when the FPR sum is zero.
- [ ] `PROSE-SENTINEL-0782` — source line `5214` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 6.3 Cluster dispersion**
  > For CLUSTER_THRESHOLD, report:
- [ ] `PROSE-SENTINEL-0783` — source line `5223` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 6.3 Cluster dispersion**
  > Do not conflate these quantities.
- [ ] `PROSE-SENTINEL-0784` — source line `5229` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 5.6 Natural-device help/harm summary semantics**
  > The Part II §7.5B client-impact profile is a mandatory companion to the confirmatory shared-versus-local result. It uses **paired within-client changes**, never pooled device-seed observations.
- [ ] `PROSE-SENTINEL-0785` — source line `5231` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 5.6 Natural-device help/harm summary semantics**
  > A headline statement that LOCAL_THRESHOLD improves operating-point equity is incomplete unless the same result block also reports:
- [ ] `PROSE-SENTINEL-0786` — source line `5250` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 5.6 Natural-device help/harm summary semantics**
  > where attack-sensitive quantities are reported only on their common valid population. A method is not given a single scalar “winner” label from this bundle.
- [ ] `PROSE-SENTINEL-0787` — source line `5252` — **Part III — Evaluation, Statistical Analysis, and Reporting / 6. Optional equity metrics / 5.6 Natural-device help/harm summary semantics**
  > For the complete N-BaIoT physical-device population, the manuscript/supplement must also show every device's ten-seed `FPRHelpFrequency` and `FPRHarmFrequency`, together with its pre-outcome `n_k_source` and support-stratum identity from Part II §7.5B. This is descriptive client stability evidence; it is not a new independent sample.
- [ ] `PROSE-SENTINEL-0788` — source line `5265` — **Part III — Evaluation, Statistical Analysis, and Reporting / 7. Aggregate model-quality controls / 7.1 Mean client Macro-F1**
  > where \(K_a\) is the attack-evaluable client count.
- [ ] `PROSE-SENTINEL-0789` — source line `5269` — **Part III — Evaluation, Statistical Analysis, and Reporting / 7. Aggregate model-quality controls / 7.2 Pooled Macro-F1**
  > Pooled Macro-F1 may be reported from pooled confusion counts but must be labeled separately.
- [ ] `PROSE-SENTINEL-0790` — source line `5271` — **Part III — Evaluation, Statistical Analysis, and Reporting / 7. Aggregate model-quality controls / 7.2 Pooled Macro-F1**
  > It cannot replace:
- [ ] `PROSE-SENTINEL-0791` — source line `5286` — **Part III — Evaluation, Statistical Analysis, and Reporting / 7. Aggregate model-quality controls / 7.3 Mean client balanced accuracy**
  > Always report the worst-client value alongside it.
- [ ] `PROSE-SENTINEL-0792` — source line `5294` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.1 Centralized oracle**
  > When defined by the experiment, the exact pooled benign quantile is the centralized threshold reference.
- [ ] `PROSE-SENTINEL-0793` — source line `5296` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.1 Centralized oracle**
  > The quantile probability and interpolation method must match the distributed estimators.
- [ ] `PROSE-SENTINEL-0794` — source line `5316` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.2 Threshold error**
  > Relative error is undefined when the oracle threshold is zero.
- [ ] `PROSE-SENTINEL-0795` — source line `5320` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.3 Target attainment**
  > For target quantile \(q\):
- [ ] `PROSE-SENTINEL-0796` — source line `5338` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.3 Target attainment**
  > Report both signed and absolute error.
- [ ] `PROSE-SENTINEL-0797` — source line `5342` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.4 Threshold variance and sample efficiency**
  > For calibration-size studies, calculate threshold variation across declared subsampling replicates within client and seed. For `R=10` replicate thresholds `tau_{s,k,m,r}`, define
- [ ] `PROSE-SENTINEL-0798` — source line `5357` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.4 Threshold variance and sample efficiency**
  > Use the sample-variance denominator `R-1`; do not use population variance (`ddof=0`) under the same metric name. Variance/SD are first computed within `(training_seed, client, m)` and only then summarized across clients/seeds according to the experiment contract.
- [ ] `PROSE-SENTINEL-0799` — source line `5359` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.4 Threshold variance and sample efficiency**
  > The complete calibration-size curve is reported using:
- [ ] `PROSE-SENTINEL-0800` — source line `5371` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.4 Threshold variance and sample efficiency**
  > All bias/RMSE/inversion calculations are first summarized within training seed. Nested calibration replicates never enter across-seed inference as independent observations.
- [ ] `PROSE-SENTINEL-0801` — source line `5373` — **Part III — Evaluation, Statistical Analysis, and Reporting / 8. Threshold-estimation metrics / 8.4 Threshold variance and sample efficiency**
  > Subsampling replicates do not increase the seed count.
- [ ] `PROSE-SENTINEL-0802` — source line `5379` — **Part III — Evaluation, Statistical Analysis, and Reporting / 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics**
  > For eligible client \(k\), the comparator uses benign-only:
- [ ] `PROSE-SENTINEL-0803` — source line `5424` — **Part III — Evaluation, Statistical Analysis, and Reporting / 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics / 9.2 Full pooled variance**
  > The between-client mean-shift term must not be omitted.
- [ ] `PROSE-SENTINEL-0804` — source line `5434` — **Part III — Evaluation, Statistical Analysis, and Reporting / 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics / 9.3 Between ratio**
  > Undefined when the denominator is zero.
- [ ] `PROSE-SENTINEL-0805` — source line `5436` — **Part III — Evaluation, Statistical Analysis, and Reporting / 9. `FEDERATED_BENIGN_SUMMARY_THRESHOLD` diagnostics / 9.3 Between ratio**
  > Report `within`, `between`, pooled variance, and `between_ratio`.
- [ ] `PROSE-SENTINEL-0806` — source line `5444` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.1 Alert burden**
  > When a measured or appropriately cited benign decision rate exists:
- [ ] `PROSE-SENTINEL-0807` — source line `5454` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.1 Alert burden**
  > Report the rate source and whether it is measured, dataset-derived, or externally cited.
- [ ] `PROSE-SENTINEL-0808` — source line `5456` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.1 Alert burden**
  > When no defensible rate exists, omit alert burden.
- [ ] `PROSE-SENTINEL-0809` — source line `5460` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.2 Threshold-stage communication**
  > For every threshold method report:
- [ ] `PROSE-SENTINEL-0810` — source line `5469` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.2 Threshold-stage communication**
  > Estimated raw-field bytes and actual serialized bytes must be separate columns.
- [ ] `PROSE-SENTINEL-0811` — source line `5473` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.3 Threshold-stage latency and memory**
  > Use the locked 5-warm-up / 20-measured-iteration protocol from the experiment catalogue. Report median/IQR/p95 construction time and peak RSS delta, with the exact hardware/runtime identity. Do not combine detector scoring time with threshold construction.
- [ ] `PROSE-SENTINEL-0812` — source line `5477` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.4 Ditto incremental state and compute**
  > For the model-personalization stress test report:
- [ ] `PROSE-SENTINEL-0813` — source line `5486` — **Part III — Evaluation, Statistical Analysis, and Reporting / 10. Operational metrics / 10.4 Ditto incremental state and compute**
  > The result is a relative cost characterization on the experiment host, not an IoT-device deployment benchmark.
- [ ] `PROSE-SENTINEL-0814` — source line `5492` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1 Paired contrast**
  > For seed \(s\):
- [ ] `PROSE-SENTINEL-0815` — source line `5502` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1 Paired contrast**
  > The confirmatory point estimate is the arithmetic mean:
- [ ] `PROSE-SENTINEL-0816` — source line `5511` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1 Paired contrast**
  > SHARED_THRESHOLD and LOCAL_THRESHOLD are never resampled independently.
- [ ] `PROSE-SENTINEL-0817` — source line `5515` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1A Relative and robustness-oriented descriptive effect sizes**
  > The confirmatory estimand remains the **absolute** paired difference \(\Delta_s\). In addition, when `CV(FPR)_{\mathrm{shared},s} > 1e-12`, report the descriptive relative reduction
- [ ] `PROSE-SENTINEL-0818` — source line `5522` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1A Relative and robustness-oriented descriptive effect sizes**
  > and `100 * RelativeCVReduction_s` as a percentage. It is unavailable, not zero, when the denominator is `<= 1e-12`.
- [ ] `PROSE-SENTINEL-0819` — source line `5524` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1A Relative and robustness-oriented descriptive effect sizes**
  > Also report the absolute paired worst-client and dispersion-support deltas
- [ ] `PROSE-SENTINEL-0820` — source line `5536` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1A Relative and robustness-oriented descriptive effect sizes**
  > Positive values favor LOCAL_THRESHOLD. Report their ten seed-level values and arithmetic means as descriptive secondary effects.
- [ ] `PROSE-SENTINEL-0821` — source line `5538` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.1A Relative and robustness-oriented descriptive effect sizes**
  > Also report the median paired \(\Delta_s\), minimum, maximum, and the full ordered ten-seed vector. None replaces the arithmetic-mean BCa confirmatory rule.
- [ ] `PROSE-SENTINEL-0822` — source line `5542` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.2 BCa confidence interval**
  > The confirmatory interval is a two-sided 95% BCa bootstrap interval over the ten paired seed-level deltas.
- [ ] `PROSE-SENTINEL-0823` — source line `5544` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.2 BCa confidence interval**
  > The interval resamples paired seed deltas with replacement, uses the arithmetic mean as its statistic, and calculates bias correction and acceleration from the paired seed data.
- [ ] `PROSE-SENTINEL-0824` — source line `5548` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.3 Degenerate BCa**
  > If BCa is undefined or unstable because of identical deltas, invalid acceleration, a degenerate bootstrap distribution, or fewer than ten valid pairs, the result is `CONFIRMATORY_INFERENCE_UNAVAILABLE` (Part II — Experiment Programme, §5.3):
- [ ] `PROSE-SENTINEL-0825` — source line `5567` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.4 Sign consistency**
  > Also report zero and negative counts.
- [ ] `PROSE-SENTINEL-0826` — source line `5569` — **Part III — Evaluation, Statistical Analysis, and Reporting / 11. Confirmatory statistical analysis / 11.4 Sign consistency**
  > This is descriptive only.
- [ ] `PROSE-SENTINEL-0827` — source line `5577` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1A Exact paired sign test**
  > For the confirmatory shared-versus-local seed-level deltas, let
- [ ] `PROSE-SENTINEL-0828` — source line `5585` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1A Exact paired sign test**
  > Zero deltas are discarded for the sign test but remain visible in the sign-consistency counts. Under the null that positive and negative signs are equally likely, `X ~ Binomial(n_nonzero, 0.5)`. The locked two-sided exact p-value is
- [ ] `PROSE-SENTINEL-0829` — source line `5595` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1A Exact paired sign test**
  > If `n_nonzero = 0`, the test is `UNAVAILABLE_ALL_ZERO_DIFFERENCES`. No normal approximation is used. With the full ten non-zero pairs, the smallest possible two-sided p-value is `2/2^10 = 0.001953125`.
- [ ] `PROSE-SENTINEL-0830` — source line `5597` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1A Exact paired sign test**
  > The exact sign test is secondary robustness evidence only. It does not replace or modify the BCa confirmatory decision rule and is not used to add/remove seeds.
- [ ] `PROSE-SENTINEL-0831` — source line `5601` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1 Wilcoxon signed-rank**
  > Use paired seed-level values with:
- [ ] `PROSE-SENTINEL-0832` — source line `5608` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.1 Wilcoxon signed-rank**
  > The p-value does not determine the confirmatory verdict.
- [ ] `PROSE-SENTINEL-0833` — source line `5612` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.2 Matched-pairs rank-biserial correlation**
  > Use matched-pairs rank-biserial correlation as the paired nonparametric effect size.
- [ ] `PROSE-SENTINEL-0834` — source line `5614` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.2 Matched-pairs rank-biserial correlation**
  > Do not use unpaired Cliff’s delta for the seed-paired comparison.
- [ ] `PROSE-SENTINEL-0835` — source line `5616` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.2 Matched-pairs rank-biserial correlation**
  > Report method, sign, magnitude, and non-zero pair count.
- [ ] `PROSE-SENTINEL-0836` — source line `5620` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.3 Secondary confidence intervals**
  > Secondary BCa intervals may be reported for pre-specified seed-level contrasts, but remain secondary.
- [ ] `PROSE-SENTINEL-0837` — source line `5624` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.4 Multiplicity**
  > The single confirmatory endpoint receives no multiplicity correction.
- [ ] `PROSE-SENTINEL-0838` — source line `5626` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.4 Multiplicity**
  > When secondary p-values are emphasized:
- [ ] `PROSE-SENTINEL-0839` — source line `5633` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.4 Multiplicity**
  > Exploratory analyses may remain descriptive.
- [ ] `PROSE-SENTINEL-0840` — source line `5637` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.5 Nested replicates**
  > For calibration subsamples, cluster restarts, or similar nested repetitions:
- [ ] `PROSE-SENTINEL-0841` — source line `5646` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.6 Association analyses**
  > For heterogeneity–benefit analyses, report:
- [ ] `PROSE-SENTINEL-0842` — source line `5655` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.6 Association analyses**
  > Use associative, not causal, language.
- [ ] `PROSE-SENTINEL-0843` — source line `5659` — **Part III — Evaluation, Statistical Analysis, and Reporting / 12. Secondary statistical evidence / 12.7 Cluster stability**
  > Adjusted Rand index is descriptive and must be accompanied by memberships, cluster sizes, empty clusters, and singleton clusters.
- [ ] `PROSE-SENTINEL-0844` — source line `5667` — **Part III — Evaluation, Statistical Analysis, and Reporting / 13. Terminal scientific-model protocol / 13.1 Terminal detector**
  > Every training execution has one terminal scientific detector at the locked terminal round of **200**. Detector weights remain seed-, population-, dataset-, and training-method-specific. The centralized reference remains independent from federated detectors.
- [ ] `PROSE-SENTINEL-0845` — source line `5671` — **Part III — Evaluation, Statistical Analysis, and Reporting / 13. Terminal scientific-model protocol / 13.2 Recovery and diagnostic checkpoints**
  > Recovery checkpoints may resume interrupted training only. Diagnostic checkpoints record training observations only. Neither provides a scientific detector, score source, threshold input, evaluation input, or analysis input.
- [ ] `PROSE-SENTINEL-0846` — source line `5675` — **Part III — Evaluation, Statistical Analysis, and Reporting / 13. Terminal scientific-model protocol / 13.3 Fixed-detector restrictions**
  > No test metric, attack label, threshold outcome, shared-versus-local effect, external result, stress-test result, or policy-specific performance may alter the terminal detector or cause policy-specific retraining.
- [ ] `PROSE-SENTINEL-0847` — source line `5679` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > For each seed and policy, report:
- [ ] `PROSE-SENTINEL-0848` — source line `5707` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > `recovery_ratio` is computed only when `drift_excess` satisfies a positive-materiality threshold specified before analysis.
- [ ] `PROSE-SENTINEL-0849` — source line `5709` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > **Locked temporal decision values (`TEMPORAL_DECISION_PROTOCOL`, prospective research amendment).** `drift_excess_materiality_threshold = 0.05` (`CV(FPR)` units), matching the identical practical-indistinguishability convention already locked for the Ditto absorption comparison (§11: "within `0.05`"), so materiality is judged against the same magnitude this roadmap already treats as scientifically distinguishable rather than an unrelated imported constant. `material_recovery_ratio_minimum = 0.5`: one-shot recalibration must recover at least half of the drift excess to be reported as meaningful recovery, the conventional majority bar in recovery/restoration literature absent a study-specific reason to require more. Both values apply across the locked temporal seed cohort (EDGE_TEMPORAL_CLIENTS, bounded-evidence seeds).
- [ ] `PROSE-SENTINEL-0850` — source line `5711` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > Otherwise:
- [ ] `PROSE-SENTINEL-0851` — source line `5717` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > Temporal BCa analysis resamples paired seed records, not rows or windows.
- [ ] `PROSE-SENTINEL-0852` — source line `5719` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities**
  > Undefined or unavailable metrics must be reported with their reason; do not substitute zero, an empty value, or an unqualified `NaN`.
- [ ] `PROSE-SENTINEL-0853` — source line `5725` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities / 14.1 Client-level temporal diagnostics**
  > In addition to campaign-level `drift_excess` and `recovery_ratio`, persist and report for every valid client:
- [ ] `PROSE-SENTINEL-0854` — source line `5739` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities / 14.1 Client-level temporal diagnostics**
  > `DriftJS_k` uses the locked base-2 JSD formula and 64-bin common quantile grid over that client's historical-calibration plus future-recalibration benign scores. Report within-seed Spearman(`DriftJS_k`, `FrozenFPRDeterioration_k`) only when at least five valid client pairs are present; otherwise record `INSUFFICIENT_EVIDENCE_N_LT_5`.
- [ ] `PROSE-SENTINEL-0855` — source line `5741` — **Part III — Evaluation, Statistical Analysis, and Reporting / 14. Temporal recalibration quantities / 14.1 Client-level temporal diagnostics**
  > Helped/harmed fractions and worst-client FPR recovery use the definitions in the temporal experiment catalogue. Exact zero is retained as unchanged rather than forced into either sign.
- [ ] `PROSE-SENTINEL-0856` — source line `5747` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > The confirmatory sample size remains exactly ten independent training seeds and is never expanded or reduced after viewing the confirmatory effect. Precision is reported rather than retroactively “powered” from the observed result.
- [ ] `PROSE-SENTINEL-0857` — source line `5749` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > Let \(s_\Delta\) be the sample SD of the ten paired deltas. Report the descriptive normal-reference standard error
- [ ] `PROSE-SENTINEL-0858` — source line `5755` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > and reference half-width
- [ ] `PROSE-SENTINEL-0859` — source line `5761` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > These are precision diagnostics only; the confirmatory interval remains BCa.
- [ ] `PROSE-SENTINEL-0860` — source line `5763` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > For the confirmatory BCa interval \([L_{BCa},U_{BCa}]\), report
- [ ] `PROSE-SENTINEL-0861` — source line `5769` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > Perform leave-one-seed-out influence analysis without changing the inferential sample:
- [ ] `PROSE-SENTINEL-0862` — source line `5781` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1 Locked ten-seed precision diagnostics**
  > Report `min_j mean_delta_(-j)`, `max_j mean_delta_(-j)`, and `MaxLOSOShift`. A result dominated by one seed must be described as such even when the confirmatory BCa rule passes.
- [ ] `PROSE-SENTINEL-0863` — source line `5785` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > This diagnostic tests whether one of the nine N-BaIoT physical devices drives the shared-versus-local result. It operates entirely on the already generated fixed score artifacts. It does **not** retrain the detector, refit preprocessing, regenerate scores, alter the seed cohort, or create eight-device “replications.”
- [ ] `PROSE-SENTINEL-0864` — source line `5787` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > For each seed `s` and physical device `j`:
- [ ] `PROSE-SENTINEL-0865` — source line `5800` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > For each omitted device `j`, summarize across the same ten seeds:
- [ ] `PROSE-SENTINEL-0866` — source line `5806` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > Let the full nine-device confirmatory mean be `mean_delta`. Report
- [ ] `PROSE-SENTINEL-0867` — source line `5818` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > Also report:
- [ ] `PROSE-SENTINEL-0868` — source line `5825` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > When `abs(mean_delta) > 1e-12`, define the relative maximum influence shift
- [ ] `PROSE-SENTINEL-0869` — source line `5832` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > When `abs(mean_delta) <= 1e-12`, `RelativeMaxLODOShift` is `UNAVAILABLE_NEAR_ZERO_FULL_EFFECT`; it must not be stabilized by adding an arbitrary denominator constant.
- [ ] `PROSE-SENTINEL-0870` — source line `5834` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > The pre-specified influence flag is:
- [ ] `PROSE-SENTINEL-0871` — source line `5842` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > The `0.25` boundary is a prospective sensitivity flag meaning that omission of one device changes the full-sample mean effect by at least 25%; it is not a significance threshold and does not alter the confirmatory BCa decision rule.
- [ ] `PROSE-SENTINEL-0872` — source line `5844` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.1A Leave-one-device-out influence for the natural-device confirmatory effect**
  > No p-value or BCa interval is computed over the nine omitted-device means because they are highly dependent sensitivity analyses. The original ten-seed, nine-device BCa result remains the only confirmatory inference. If `LODO_HIGH_INFLUENCE` is true, the manuscript must identify every triggering device, report the triggering condition, and describe the headline effect as influence-sensitive.
- [ ] `PROSE-SENTINEL-0873` — source line `5848` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.2 Numerical and selection discipline**
  > Calculations use full available precision. Rounding occurs only for presentation.
- [ ] `PROSE-SENTINEL-0874` — source line `5850` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.2 Numerical and selection discipline**
  > Recommended presentation:
- [ ] `PROSE-SENTINEL-0875` — source line `5858` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.2 Numerical and selection discipline**
  > Never round before computing contrasts or intervals.
- [ ] `PROSE-SENTINEL-0876` — source line `5860` — **Part III — Evaluation, Statistical Analysis, and Reporting / 15. Precision and selection discipline / 15.2 Numerical and selection discipline**
  > Do not choose checkpoints, policies, or parameter values from test outcomes, remove unfavorable seeds or clients, convert undefined metrics to zero, or hide material null or contrary results.
- [ ] `PROSE-SENTINEL-0877` — source line `5864` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables**
  > These are reporting requirements over already declared experiments; they do not create new inferential endpoints.
- [ ] `PROSE-SENTINEL-0878` — source line `5868` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.1 Causal intervention map — mandatory main-text figure**
  > Render the scientific pipeline in this exact left-to-right order:
- [ ] `PROSE-SENTINEL-0879` — source line `5886` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.1 Causal intervention map — mandatory main-text figure**
  > The figure must visually place interventions at their correct stage:
- [ ] `PROSE-SENTINEL-0880` — source line `5896` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.1 Causal intervention map — mandatory main-text figure**
  > There must be **no arrow from held-out evaluation labels or metrics back into threshold estimation, q selection, preprocessing, training, cluster count, shrinkage, or eligibility**. The fixed-score boundary must visually separate the confirmatory threshold-scope intervention from training/model changes.
- [ ] `PROSE-SENTINEL-0881` — source line `5900` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.2 Confirmatory paired-effect view — mandatory main-text figure**
  > Show all ten seed-level
- [ ] `PROSE-SENTINEL-0882` — source line `5906` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.2 Confirmatory paired-effect view — mandatory main-text figure**
  > with a horizontal zero reference, the arithmetic mean, and the locked 95% BCa interval. Every seed remains individually identifiable by seed ID. Do not replace this with a bar chart containing only a mean and error bar.
- [ ] `PROSE-SENTINEL-0883` — source line `5910` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table**
  > The confirmatory SHARED_THRESHOLD versus LOCAL_THRESHOLD result must have one aligned table containing, for both policies and their paired difference where meaningful:
- [ ] `PROSE-SENTINEL-0884` — source line `5926` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.2A Confirmatory equity–utility/client-impact bundle — mandatory companion table**
  > The same table or an immediately adjacent panel must show the ten seed-level `FPRHelpedFraction`, `FPRHarmedFraction`, `TPRLossFraction`, and Pareto client-impact fractions from Part II §7.5B. The purpose is to make an equity improvement visually inseparable from its detection-utility consequences. No table may headline `CV(FPR)` alone while relegating a material TPR/Macro-F1/worst-client degradation to unreferenced supplementary text.
- [ ] `PROSE-SENTINEL-0885` — source line `5930` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.3 Equity–utility Pareto view — mandatory main-text or first-supplement figure**
  > Use Part II §7.7 exactly: primary `CV(FPR)` versus P10 Macro-F1, secondary `CV(FPR)` versus WorstBA, canonical `q=0.95`, same ten-seed method means, and no scalarized winner. The accompanying target-attainment table is mandatory.
- [ ] `PROSE-SENTINEL-0886` — source line `5934` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.4 FedProx mechanism-activation view — mandatory stress-test figure**
  > For every `mu in {0.001,0.01,0.1,1.0}` and FedAvg, show the ten seed-level `D_terminal50` values. A companion panel or aligned table must show `(DriftSuppression, DeltaH, H, ModelAlignmentH, LocalThresholdDispersion, NormalizedSharedLocalThresholdDistance, DeltaScope, ScopeAbsorption)` by `mu`. Do not infer from threshold outcomes alone that the proximal mechanism was active.
- [ ] `PROSE-SENTINEL-0887` — source line `5938` — **Part III — Evaluation, Statistical Analysis, and Reporting / 16. Mandatory manuscript-facing figures and synthesis tables / 16.5 Mandatory synthesis tables**
  > The manuscript or supplement must include:
- [ ] `PROSE-SENTINEL-0888` — source line `5953` — **Part IV — Development, Reproducibility, and Audit Contract / 1. Purpose and audit semantics**
  > This part answers a different question from Parts I–III:
- [ ] `PROSE-SENTINEL-0889` — source line `5957` — **Part IV — Development, Reproducibility, and Audit Contract / 1. Purpose and audit semantics**
  > It does not create new scientific experiments. It operationalizes the existing contracts into development and campaign-level checks.
- [ ] `PROSE-SENTINEL-0890` — source line `5959` — **Part IV — Development, Reproducibility, and Audit Contract / 1. Purpose and audit semantics**
  > An audit item has one of four statuses:
- [ ] `PROSE-SENTINEL-0891` — source line `5968` — **Part IV — Development, Reproducibility, and Audit Contract / 1. Purpose and audit semantics**
  > `UNAVAILABLE_AS_SPECIFIED` is valid only when Parts I–III explicitly declare that evidence unavailable for the relevant population. It must never be used to hide a missing implementation or failed computation.
- [ ] `PROSE-SENTINEL-0892` — source line `5970` — **Part IV — Development, Reproducibility, and Audit Contract / 1. Purpose and audit semantics**
  > A **FAIL** in a causal-isolation, score-identity, split-leakage, calibration-leakage, eligibility, terminal-detector, confirmatory-pairing, or statistical-validity gate blocks the affected scientific claim. A publication bundle must retain the failed audit result and the reason.
- [ ] `PROSE-SENTINEL-0893` — source line `5974` — **Part IV — Development, Reproducibility, and Audit Contract / 2. Audit object identity**
  > Every materialized scientific result must be traceable to a complete execution coordinate containing, at minimum:
- [ ] `PROSE-SENTINEL-0894` — source line `5990` — **Part IV — Development, Reproducibility, and Audit Contract / 2. Audit object identity**
  > Scientific identity is established by semantic provenance and ordered record identity. File hashes or checksums may be used for transport/integrity verification, but they do not replace the scientific identity contract in Part I §2.2.2.
- [ ] `PROSE-SENTINEL-0895` — source line `6009` — **Part IV — Development, Reproducibility, and Audit Contract / 4. Gate B — Dataset integrity**
  > For every dataset used by DATP-Core:
- [ ] `PROSE-SENTINEL-0896` — source line `6141` — **Part IV — Development, Reproducibility, and Audit Contract / 13. Gate K — Experiment completeness**
  > For every mandatory Part II experiment:
- [ ] `PROSE-SENTINEL-0897` — source line `6267` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle**
  > Publication readiness includes a **reconstructable research release**, subject to dataset licenses and anonymous-review policy. The release is evidence packaging, not a new scientific experiment.
- [ ] `PROSE-SENTINEL-0898` — source line `6269` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle**
  > The release root must contain the following logical payload (directory names may be mapped to repository-native equivalents only if a manifest maps them one-to-one):
- [ ] `PROSE-SENTINEL-0899` — source line `6299` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / `MANIFEST_SHA256.csv`**
  > One row per released artifact **except `MANIFEST_SHA256.csv` itself and its `MANIFEST_SHA256.sha256` sidecar**, with at least:
- [ ] `PROSE-SENTINEL-0900` — source line `6314` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / `MANIFEST_SHA256.csv`**
  > Fields that do not apply use an explicit `NA`, never an empty ambiguous value. SHA-256 is computed on the exact released bytes. After `MANIFEST_SHA256.csv` is finalized, compute its SHA-256 and write exactly one lowercase hexadecimal digest followed by two spaces and `MANIFEST_SHA256.csv` plus a terminating newline to `MANIFEST_SHA256.sha256`. The sidecar is not listed inside the CSV; this avoids an impossible self-referential hash.
- [ ] `PROSE-SENTINEL-0901` — source line `6325` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Data/split provenance**
  > Raw third-party datasets are **not redistributed when licensing does not permit it**. Instead release:
- [ ] `PROSE-SENTINEL-0902` — source line `6333` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Data/split provenance**
  > For an ordered row-identity artifact, hash the UTF-8 byte sequence formed by canonical row IDs joined by the single byte `0x0A` in artifact order with no trailing newline. Persist both `ordered_row_sha256` and `row_count`. This makes split identity reproducible without publishing sensitive/raw row contents.
- [ ] `PROSE-SENTINEL-0903` — source line `6337` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Preprocessing/models/scores/thresholds**
  > Release or hash, subject to licensing/security constraints:
- [ ] `PROSE-SENTINEL-0904` — source line `6346` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Metrics/statistics/figures**
  > Release:
- [ ] `PROSE-SENTINEL-0905` — source line `6357` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Environment metadata**
  > Record at minimum:
- [ ] `PROSE-SENTINEL-0906` — source line `6375` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Environment metadata**
  > Timing artifacts additionally record the exact host identifier/configuration class and prohibit cross-machine speedup claims.
- [ ] `PROSE-SENTINEL-0907` — source line `6377` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Environment metadata**
  > The release has one explicit state:
- [ ] `PROSE-SENTINEL-0908` — source line `6385` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Environment metadata**
  > `BLINDED_ARCHIVE` is used when anonymous-review rules forbid a public identity-bearing release; the same artifact bundle must remain reconstructable. `WITHHELD_LICENSE_RESTRICTED` may be used only for specific artifacts whose redistribution is prohibited, and every withheld artifact must have a hash/provenance/reconstruction record.
- [ ] `PROSE-SENTINEL-0909` — source line `6387` — **Part IV — Development, Reproducibility, and Audit Contract / 20A. Reproducibility-release bundle / Environment metadata**
  > A release-validation command must first validate `MANIFEST_SHA256.csv` against `MANIFEST_SHA256.sha256`, then recompute every listed artifact SHA-256 and byte count. It must fail on a missing listed file, an unexpected non-metadata file, byte-size mismatch, or digest mismatch. Publication figures/tables are considered reconstructable only if their released source tables pass this manifest validation.
- [ ] `PROSE-SENTINEL-0910` — source line `6391` — **Part IV — Development, Reproducibility, and Audit Contract / 21. Final publication-readiness gate**
  > DATP-Core is publication-ready only when all of the following are true:
- [ ] `PROSE-SENTINEL-0911` — source line `6406` — **Part IV — Development, Reproducibility, and Audit Contract / 21. Final publication-readiness gate**
  > A readiness audit is a verification step, not a result-selection step. Failure to pass does not authorize changing the scientific protocol after inspecting outcomes.

## 15B. Source-table semantic sentinel register

**Purpose:** close table semantics that were not reproduced verbatim elsewhere in the matrix. **Sentinel count: `128`.** Roadmap tables can encode claim boundaries, comparator roles, reviewer objections, payload contracts, evidence taxonomies, and numerical conditions; table content is therefore not decorative.

**Closure rule for every sentinel:** map the row to the existing dataset/experiment/metric/report/claim/gate requirement that implements it, or create a new atomic row. Header rows define the meaning of their child rows and must be checked for semantic alignment. A table row cannot be omitted because an experiment with a similar title exists.

- [ ] `TABLE-SENTINEL-0001` — source line `1283` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | Heterogeneity dimension | Operational definition in DATP-Core | Locked status | Evidence / experiment | Claim boundary |
- [ ] `TABLE-SENTINEL-0002` — source line `1285` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | natural statistical/device heterogeneity | physical devices have different benign/attack data and resulting score distributions | `OBSERVED` | `NBAIOT_NATURAL_DEVICES` | supports natural-device heterogeneity claims only for the nine N-BaIoT devices |
- [ ] `TABLE-SENTINEL-0003` — source line `1286` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | controlled distribution heterogeneity | source observations are redistributed into synthetic clients with a prospectively fixed Dirichlet severity | `MANIPULATED` | `NBAIOT_DIRICHLET_CLIENTS` | sensitivity evidence; never called natural-device evidence |
- [ ] `TABLE-SENTINEL-0004` — source line `1287` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | benign score-distribution heterogeneity | between-client differences in the frozen detector's benign reconstruction-score distributions, quantified by `H` and score-dispersion diagnostics | `OBSERVED`, `MANIPULATED_INDIRECTLY` | natural devices, Dirichlet sweep, preprocessing/training stress conditions | supports score-geometry mechanism language, not universal “non-IID severity” equivalence |
- [ ] `TABLE-SENTINEL-0005` — source line `1288` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | calibration-support / quantity heterogeneity | clients differ in `n_k_source`; controlled analyses also restrict used calibration size `m` | `OBSERVED`, `MANIPULATED` | Part II §§7.5A, 7.5B, 8.1, 8.1A | supports finite-calibration and support-conditioned conclusions only |
- [ ] `TABLE-SENTINEL-0006` — source line `1289` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | model/predictor heterogeneity | clients deploy distinct learned detector parameters | `STRESS_TESTED`, `EXCLUDED_FROM_CORE` | Ditto and `FEDAVG_LOCAL_FINE_TUNING`; FedProx remains one global-model training condition | cannot be mixed into the fixed-detector confirmatory contrast |
- [ ] `TABLE-SENTINEL-0007` — source line `1290` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | hardware/resource heterogeneity | clients differ in compute, memory, energy, accelerator, or feasible model capacity | `EXCLUDED` | none | no hardware-sensitive or resource-fairness claim |
- [ ] `TABLE-SENTINEL-0008` — source line `1291` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | participation/client-lifecycle heterogeneity | clients are intermittently available, sampled sparsely, churn, or arrive unseen | `EXCLUDED`; truthful threshold-contributor availability is `BOUNDARY_ONLY` | §3.3A and Part II §8.6 | no cross-device intermittency, unseen-client, straggler, or dropout claim |
- [ ] `TABLE-SENTINEL-0009` — source line `1292` — **Part I — Scientific Programme and Global Protocol Contracts / 9. Dataset and population boundaries / 9.7 Heterogeneity taxonomy and claim boundary**
  > | temporal heterogeneity | score distributions change over real chronology | `BOUNDARY_ONLY`, `OBSERVED` where timestamp-valid | `EDGE_TEMPORAL_CLIENTS` one-shot recalibration | no continuous adaptation or drift-detector claim |
- [ ] `TABLE-SENTINEL-0010` — source line `1775` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Prior work | Relevant overlap | What DATP must not claim | DATP distinction |
- [ ] `TABLE-SENTINEL-0011` — source line `1777` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Meidan et al. 2018[^nbaiot] | one benign-trained autoencoder and one anomaly threshold per physical N-BaIoT device; historical `mean + std` threshold rule | first device-specific anomaly threshold / first device-aware thresholding on N-BaIoT | Meidan personalizes detector, hyperparameters, threshold, and sequential alarm rule together; DATP isolates threshold scope on one frozen federated detector and score artifact |
- [ ] `TABLE-SENTINEL-0012` — source line `1778` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Zhang et al. / FedIoT 2021[^fediot2021] | N-BaIoT federated autoencoder with post-training benign-score threshold construction and global/personalized threshold support | first post-training threshold construction for federated IoT anomaly detection | DATP makes threshold scope the controlled intervention and cross-client FPR dispersion the primary outcome |
- [ ] `TABLE-SENTINEL-0013` — source line `1779` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Rey et al. 2022[^rey2022] | federated IoT malware detection with an autoencoder and server averaging of client-local anomaly thresholds | first federated IoT AE thresholding / first aggregation of local thresholds | fixed-score threshold-scope intervention with per-client FPR dispersion as primary outcome |
- [ ] `TABLE-SENTINEL-0014` — source line `1780` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Ochiai et al. 2023[^ochiai2023] | distributed IoT-edge anomaly detection with coordinated thresholding | first distributed IoT threshold coordination | centralized causal comparison of threshold-sharing scope on immutable scores |
- [ ] `TABLE-SENTINEL-0015` — source line `1781` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Laridi et al. 2024[^laridi] | explicit federated global threshold selection | first federated threshold-selection study | benign-only calibration; no anomaly-informed F1 optimization; scope rather than estimator competition |
- [ ] `TABLE-SENTINEL-0016` — source line `1782` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Komadina et al. 2024[^komadina2024] | systematic network-anomaly threshold-estimator study covering five supervised and twenty unsupervised methods | exhaustive/first broad threshold-estimator benchmark; q95 is globally optimal | DATP fixes the estimator in the confirmatory ladder and studies who contributes calibration evidence; the historical estimator 2×2 is only a bounded robustness check |
- [ ] `TABLE-SENTINEL-0017` — source line `1783` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | FedCal 2024[^fedcal2024] | explicit local and global calibration in federated learning using client-specific parameterized scalers aggregated into a global scaler | first local/global federated calibration study / first federated calibration method | DATP calibrates anomaly-score operating thresholds rather than predictive probabilities and studies fixed-score FPR-equity effects in federated IoT anomaly detection |
- [ ] `TABLE-SENTINEL-0018` — source line `1784` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Asiri et al. 2025[^asiri2025] | benign local `p95` reconstruction-error threshold in federated IoT malware detection | first benign p95/client threshold for FL IoT | operating-point-equity study with fixed detector and controlled scope |
- [ ] `TABLE-SENTINEL-0019` — source line `1785` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Personalized federated conformal prediction, 2025[^pfcp2025] | agent-personalized federated calibration with formal coverage goals | first personalized federated calibration / novel federated conformal calibration | LOCAL_CONFORMAL_THRESHOLD is only a bounded supportive diagnostic for AE benign-score thresholding |
- [ ] `TABLE-SENTINEL-0020` — source line `1786` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | G-PFL-ID 2026[^gpfli2026] | unsupervised personalized federated IoT IDS using graph encoders/DeepSVDD, evaluated on IoT-23 and natural-device N-BaIoT | first personalized unsupervised federated IoT IDS / first personalized N-BaIoT anomaly detector | DATP does not compete on model architecture; the locked Ditto experiment asks whether model personalization absorbs the fixed-score threshold-scope effect |
- [ ] `TABLE-SENTINEL-0021` — source line `1787` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Fed-DTCN 2026[^feddtcn2026] | personalized federated IoT anomaly detector with client-specific threshold \(\rho_k\) | first client-specific federated IoT anomaly threshold | shared frozen-detector score evidence is separated from threshold personalization |
- [ ] `TABLE-SENTINEL-0022` — source line `1788` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | FBID 2026[^fbid2026] | adaptive personalized FL for CICIoT2023 OOD intrusion detection using server-side bandit control and global/local blending | first personalized FL-IDS / first OOD-aware personalized IoT IDS | DATP neither reproduces FBID nor claims PFL novelty; FBID strengthens the reviewer counterfactual tested by the single locked Ditto absorption experiment |
- [ ] `TABLE-SENTINEL-0023` — source line `1789` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Robalino-Díaz et al. 2026[^robalino2026] | FedAvg preserves `AUC-ROC=0.995` while recall falls to `0.530` overall and `0.290` on IoMT under a fixed threshold | first observation that discrimination and operating behavior can diverge in federated IoT/IoMT | DATP turns operating-point calibration scope into the controlled intervention and uses AUROC only as a frozen-score detector control |
- [ ] `TABLE-SENTINEL-0024` — source line `1790` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | FedWQ-CP 2026[^fedwqcp2026] | clients transmit local conformal quantile thresholds and calibration sizes; server forms a weighted global threshold | first weighted aggregation of federated local calibration thresholds | DATP's shared-construction controls are comparators; DATP does not claim federated quantile-aggregation novelty |
- [ ] `TABLE-SENTINEL-0025` — source line `1791` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | GC-FCP 2026[^gcfcp2026] | group-conditional federated calibration with mergeable group-stratified summaries and formal coverage objectives | first group-conditional federated calibration | FAMILY_THRESHOLD/CLUSTER_THRESHOLD are empirical AE operating-point scopes, not group-conditional conformal guarantees |
- [ ] `TABLE-SENTINEL-0026` — source line `1792` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | PFWCP 2026[^pfwcp2026] | personalized weighted federated conformal calibration under heterogeneity and limited local calibration | first personalized weighted federated calibration | DATP's local calibration and shrinkage are empirical anomaly-threshold mechanisms without conformal-theory novelty |
- [ ] `TABLE-SENTINEL-0027` — source line `1793` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Rob-FCP 2024[^robfcp2024] | Byzantine-robust federated conformal calibration; malicious clients may submit arbitrary calibration statistics and are filtered before global conformal quantile estimation | Byzantine robustness of DATP thresholds / secure or attack-resistant threshold aggregation | DATP assumes protocol-compliant calibration participants and studies statistical scope, not adversarial trustworthiness |
- [ ] `TABLE-SENTINEL-0028` — source line `1794` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | CF-HFC 2026[^cfhfc2026] | heterogeneous-IoT IDS combining hardware-aware fuzzy client clustering, Fuzzy-FedProx, and Adaptive Conformal Calibration that dynamically adjusts decision thresholds | first calibrated FL-IDS for heterogeneous IoT / first adaptive conformal thresholding in federated IoT | CF-HFC changes clustering, optimization, system scheduling, and calibration jointly; DATP isolates threshold-calibration scope on fixed score artifacts and does not reproduce this multi-component system |
- [ ] `TABLE-SENTINEL-0029` — source line `1795` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | PRISM-FCP 2026[^prismfcp2026] | Byzantine-robust FCP across both model training and calibration using partial model sharing plus histogram-based filtering of calibration submissions | end-to-end Byzantine robustness / communication-efficient secure calibration | DATP's honest-calibration contract intentionally excludes both adversarial training and adversarial calibration; PRISM-FCP is a threat-boundary citation, not a baseline |
- [ ] `TABLE-SENTINEL-0030` — source line `1796` — **Part I — Scientific Programme and Global Protocol Contracts / 10. Scope, terminology, claim boundaries, and accepted limitations / 10.D.9 Novelty boundary and mandatory prior-art audit**
  > | Shahid 2026[^shahid-fcrc2026] | fixed pretrained model; pooled versus local/site-uniform calibration; site-level failures hidden by average calibration; `n_k/(n_k+n_0)` shrinkage | first demonstration that average federated calibration can hide local/site failures / first local-global sample-size shrinkage | DATP's narrow contribution is federated IoT AE operating-point equity under frozen detector/score evidence; its `n_min=100` shrinkage constant is prospectively inherited rather than tuned |
- [ ] `TABLE-SENTINEL-0031` — source line `2018` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | Contract family | Authoritative owner | Typical inheritors |
- [ ] `TABLE-SENTINEL-0032` — source line `2020` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | causal isolation / fixed detector | Part I §2 | all core threshold-scope experiments |
- [ ] `TABLE-SENTINEL-0033` — source line `2021` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | preprocessing identity | Part I §2.2.1 | scoring, thresholding, preprocessing sensitivity |
- [ ] `TABLE-SENTINEL-0034` — source line `2022` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | fixed-score scientific identity | Part I §2.2.2 | all threshold comparisons and evaluation |
- [ ] `TABLE-SENTINEL-0035` — source line `2023` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | quantile convention | Part I §2.2.3 | core threshold-scope, pooled oracle, shrinkage, calibration-size studies |
- [ ] `TABLE-SENTINEL-0036` — source line `2024` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | benign-only calibration / honest-participant contract / eligibility / persistent-client regime | Part I §3 | all DATP-compatible threshold methods, client-bound artifacts, and threshold-stage messages |
- [ ] `TABLE-SENTINEL-0037` — source line `2025` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | threshold-method semantics | Part I §§4–6 | Part II experiments |
- [ ] `TABLE-SENTINEL-0038` — source line `2026` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | training-stress semantics | Part I §7 | FedProx / `FEDAVG_LOCAL_FINE_TUNING` / Ditto experiments |
- [ ] `TABLE-SENTINEL-0039` — source line `2027` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | evidence roles and claim tiers | Part I §8 and §10 | all experiments and manuscript claims |
- [ ] `TABLE-SENTINEL-0040` — source line `2028` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | dataset/population boundaries | Part I §9 | Part II population-specific procedures |
- [ ] `TABLE-SENTINEL-0041` — source line `2029` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | nested randomness | Part II §2.3A | calibration-size, cold-start, KLL when applicable |
- [ ] `TABLE-SENTINEL-0042` — source line `2030` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | experiment-specific procedure | Part II | execution and reporting |
- [ ] `TABLE-SENTINEL-0043` — source line `2031` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | metric and statistical semantics | Part III | all result generation |
- [ ] `TABLE-SENTINEL-0044` — source line `2032` — **Part I — Scientific Programme and Global Protocol Contracts / 12. Protocol ownership and inheritance map**
  > | implementation/provenance/audit checks | Part IV | development, campaign audit, publication gate |
- [ ] `TABLE-SENTINEL-0045` — source line `2045` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | Section | Experiment / analysis | Primary role | Population / setting | Main variation |
- [ ] `TABLE-SENTINEL-0046` — source line `2047` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §5.1 | Shared-versus-local threshold-scope confirmation | Confirmatory | N-BaIoT natural devices | SHARED_THRESHOLD vs LOCAL_THRESHOLD |
- [ ] `TABLE-SENTINEL-0047` — source line `2048` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §5.2 | Anchor reproduction gate | Reproducibility gate | historical N-BaIoT five-seed anchor | reproduction acceptance |
- [ ] `TABLE-SENTINEL-0048` — source line `2049` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §6.1 | Shared-threshold construction sensitivity | Supportive | N-BaIoT natural devices | SHARED_THRESHOLD vs pooled / weighted shared constructions |
- [ ] `TABLE-SENTINEL-0049` — source line `2050` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §6.2 | Quantile-level sensitivity | Supportive | N-BaIoT natural devices | `q={0.90,0.95,0.975,0.99}` |
- [ ] `TABLE-SENTINEL-0050` — source line `2051` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §6.2A | Threshold-estimator × scope sensitivity | Supportive | N-BaIoT natural devices | `{TYPE7_Q95, MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR} x {SHARED,LOCAL}` |
- [ ] `TABLE-SENTINEL-0051` — source line `2052` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §6.3 | Controlled non-IID severity | Supportive | controlled N-BaIoT partitions | heterogeneity severity |
- [ ] `TABLE-SENTINEL-0052` — source line `2053` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.1 | Threshold-sharing granularity and cluster stability | Mechanism | N-BaIoT natural devices | SHARED_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD/LOCAL_THRESHOLD + cluster stability |
- [ ] `TABLE-SENTINEL-0053` — source line `2054` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.2A | Physical-family explanatory adequacy | Mechanism | N-BaIoT natural devices | within/between-family geometry |
- [ ] `TABLE-SENTINEL-0054` — source line `2055` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.3 | Per-client score-distribution explanation | Mechanism | N-BaIoT natural devices | benign/attack score geometry |
- [ ] `TABLE-SENTINEL-0055` — source line `2056` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.4 | Heterogeneity–benefit association and decision surface | Mechanism | natural + controlled N-BaIoT evidence | JS heterogeneity × calibration support |
- [ ] `TABLE-SENTINEL-0056` — source line `2057` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.5 | Threshold movement versus operating-point harm | Mechanism | N-BaIoT natural devices | threshold movement vs FPR/TPR changes + exact device-direction counts |
- [ ] `TABLE-SENTINEL-0057` — source line `2058` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.5A | Calibration support versus shared-threshold burden | Descriptive mechanism diagnostic | N-BaIoT natural devices | source benign-calibration support vs shared FPR and local-personalization relief |
- [ ] `TABLE-SENTINEL-0058` — source line `2059` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.5B | Natural-device helped/harmed profile + support strata | Mandatory client-impact mechanism diagnostic | N-BaIoT natural devices | exact per-device help/harm/Pareto directions + campaign-fixed 3/3/3 support strata |
- [ ] `TABLE-SENTINEL-0059` — source line `2060` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.6 | Malware-family sensitivity breakdown | Supportive trade-off | N-BaIoT natural devices | Mirai/BASHLITE attack-family outcomes |
- [ ] `TABLE-SENTINEL-0060` — source line `2061` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §7.7 | Equity–utility Pareto analysis | Supportive synthesis | N-BaIoT natural devices | equity vs utility, no scalar winner |
- [ ] `TABLE-SENTINEL-0061` — source line `2062` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.1 | Calibration-size ablation | Boundary/supportive | N-BaIoT natural devices | `m={50,100,250,500,1000,5000}` |
- [ ] `TABLE-SENTINEL-0062` — source line `2063` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.1A | Calibration cold-start/onboarding boundary | Boundary | N-BaIoT natural devices | low-support onboarding |
- [ ] `TABLE-SENTINEL-0063` — source line `2064` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.2 | Fixed local–global shrinkage | Threshold variant | N-BaIoT natural devices | fixed λ curve |
- [ ] `TABLE-SENTINEL-0064` — source line `2065` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.3 | Calibration-size-aware shrinkage | Threshold variant | N-BaIoT natural devices | deterministic λ by `n_k_used` |
- [ ] `TABLE-SENTINEL-0065` — source line `2066` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.4 | Split-conformal LOCAL_CONFORMAL_THRESHOLD diagnostic | Threshold variant | N-BaIoT natural devices | finite-sample local coverage |
- [ ] `TABLE-SENTINEL-0066` — source line `2067` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.5 | Bounded preprocessing-geometry sensitivity | Supportive boundary | N-BaIoT natural devices | local StandardScaler vs pooled MinMax protocol identity |
- [ ] `TABLE-SENTINEL-0067` — source line `2068` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §8.6 | Shared-calibration contributor availability | Supportive operational sensitivity | N-BaIoT natural devices | exhaustive omission of `m={0,1,2,3,4}` shared-threshold contributors |
- [ ] `TABLE-SENTINEL-0068` — source line `2069` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §9.1 | Benign summary-statistics comparator | Comparator | N-BaIoT natural devices | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` |
- [ ] `TABLE-SENTINEL-0069` — source line `2070` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §9.2 | KLL federated quantile-sketch threshold | Comparator | N-BaIoT natural devices | KLL `k={200,400,800}` |
- [ ] `TABLE-SENTINEL-0070` — source line `2071` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §9.3 | Fixed-coefficient Laridi sensitivity | Optional supplement | N-BaIoT natural devices | fixed coefficient sensitivity only |
- [ ] `TABLE-SENTINEL-0071` — source line `2072` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §10.1 | Edge-IIoTset external benign-equity validation | External validation | Edge-IIoTset | independent-dataset benign equity |
- [ ] `TABLE-SENTINEL-0072` — source line `2073` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §10.2 | CICIoT2023 file-level boundary | Applicability boundary | CICIoT2023 file pseudo-clients | available-data boundary |
- [ ] `TABLE-SENTINEL-0073` — source line `2074` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §11.1 | FedProx aggregation + mechanism-activation stress test | Training stress | N-BaIoT natural devices | FedProx μ grid + local-update drift diagnostics |
- [ ] `TABLE-SENTINEL-0074` — source line `2075` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §11.2 | Ditto model-personalization stress test | Model-personalization stress | N-BaIoT natural devices | Ditto λD grid / absorption |
- [ ] `TABLE-SENTINEL-0075` — source line `2076` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §11.2A | FedAvg post-training client-local fine-tuning | Simple model-personalization stress | N-BaIoT natural devices | exactly 10 benign-training local epochs + common absorption diagnostics |
- [ ] `TABLE-SENTINEL-0076` — source line `2077` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §12.1 | One-shot recalibration under genuine chronology | Temporal boundary | Edge-IIoTset temporal population | static vs frozen-future vs one-shot recalibration |
- [ ] `TABLE-SENTINEL-0077` — source line `2078` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §13.1 | Alert-burden experiment | Operational interpretation | valid rate-bearing population | alert-count translation |
- [ ] `TABLE-SENTINEL-0078` — source line `2079` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §13.2 | Threshold-stage communication/storage/runtime accounting | Operational accounting | applicable methods | payload, storage, threshold-stage timing |
- [ ] `TABLE-SENTINEL-0079` — source line `2080` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §14.1 | Robust cluster-median threshold | Optional analysis | N-BaIoT natural devices | cluster median vs mean threshold |
- [ ] `TABLE-SENTINEL-0080` — source line `2081` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §14.2 | Additional equity indices | Optional analysis | applicable populations | Jain/Gini/IQR/range diagnostics |
- [ ] `TABLE-SENTINEL-0081` — source line `2082` — **Part II — Experiment Programme and Decision Rules / 0. Master experiment index**
  > | §14.3 | Extended secondary uncertainty | Optional analysis | applicable experiments | secondary paired uncertainty |
- [ ] `TABLE-SENTINEL-0082` — source line `2210` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | Reviewer objection | Mandatory response | Decisive output |
- [ ] `TABLE-SENTINEL-0083` — source line `2212` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “SHARED_THRESHOLD is simply a poor global-threshold estimator.” | exact pooled + sample-weighted + KLL + `FEDERATED_BENIGN_SUMMARY_THRESHOLD` controls | LOCAL_THRESHOLD contrast under every mandatory shared construction |
- [ ] `TABLE-SENTINEL-0084` — source line `2213` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Local p95 is trivial/prior art.” | fixed-detector scope intervention, not estimator novelty | paired `CV(FPR)` effect with immutable score identity |
- [ ] `TABLE-SENTINEL-0085` — source line `2214` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Local q95 equalizes FPR by construction.” | strict calibration/evaluation row disjointness + explicit `H_TAUTOLOGY` rebuttal | calibration exceedance, held-out `SignedTestFPRTargetError`, and `CalibrationGeneralizationGap` on different rows |
- [ ] `TABLE-SENTINEL-0086` — source line `2215` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Local thresholds only work with abundant calibration data.” | calibration-size curve + cold-start boundary | threshold RMSE/bias, target error, SHARED_THRESHOLD/LOCAL_THRESHOLD/shrinkage curves |
- [ ] `TABLE-SENTINEL-0087` — source line `2216` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “The effect is just stronger heterogeneity.” | controlled Dirichlet sweep + JS mechanism | heterogeneity–benefit association with all severities retained |
- [ ] `TABLE-SENTINEL-0088` — source line `2217` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Calibration size and heterogeneity are confounded.” | predeclared 3×4 interaction experiment | interaction coefficient and complete cell grid |
- [ ] `TABLE-SENTINEL-0089` — source line `2218` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “q=0.95 was chosen because it worked.” | locked q sensitivity `{0.90,0.95,0.975,0.99}` | complete q surface; canonical q never replaced |
- [ ] `TABLE-SENTINEL-0090` — source line `2219` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “The scope effect exists only for quantile thresholding.” | fixed-score historical moment-estimator 2-by-2 sensitivity | shared-to-local `CV(FPR)` gain under both `TYPE7_Q95` and `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` |
- [ ] `TABLE-SENTINEL-0091` — source line `2220` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “One pathological N-BaIoT device drives the headline result.” | leave-one-device-out influence diagnostic with no retraining/rescoring | all nine `Delta_(s,-j)` surfaces, mean-effect range, `MaxLODOShift`, and sign retention |
- [ ] `TABLE-SENTINEL-0092` — source line `2221` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “FedAvg is the problem.” | complete FedProx `mu` grid | SHARED_THRESHOLD–LOCAL_THRESHOLD gain under each independently trained detector |
- [ ] `TABLE-SENTINEL-0093` — source line `2222` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Personalized models make DATP redundant.” | literature-backed `FEDAVG_LOCAL_FINE_TUNING` 10-epoch 2×2 + canonical Ditto 2×2 plus Ditto λ sensitivity | raw `DeltaScope`, `ScopeAbsorption`, and common score/threshold-alignment diagnostics |
- [ ] `TABLE-SENTINEL-0094` — source line `2223` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “An upstream method changed the model but did not actually align client score geometry.” | common Part I §7.2B mechanism diagnostics for FedProx/fine-tuning/Ditto | fixed-grid cross-model `ModelAlignmentH`, location/scale/q95 dispersion, normalized shared-local threshold distance, alignment reductions |
- [ ] `TABLE-SENTINEL-0095` — source line `2224` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “DATP silently assumes persistent clients and does not apply to intermittent cross-device FL.” | Part I §3.3A persistent-identifiable-client contract + cold-start distinction | explicit full-participation/persistence regime; unseen/intermittent claims forbidden |
- [ ] `TABLE-SENTINEL-0096` — source line `2225` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Average personalization gains may hide harmed devices.” | exact N-BaIoT helped/harmed profile + fixed support-stratum summary | per-seed help/harm/Pareto fractions, per-device help frequency, support-stratum summaries |
- [ ] `TABLE-SENTINEL-0097` — source line `2226` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “CLUSTER_THRESHOLD is arbitrary clustering.” | stability, silhouette, within/between JS, feature leave-one-out | ARI, membership tables, silhouette, CLUSTER_THRESHOLD recovery and ablations |
- [ ] `TABLE-SENTINEL-0098` — source line `2227` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Per-client normalization created the effect.” | bounded pooled-MinMax preprocessing sensitivity | SHARED_THRESHOLD–LOCAL_THRESHOLD gain and score heterogeneity under each preprocessing protocol |
- [ ] `TABLE-SENTINEL-0099` — source line `2228` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Lower CV merely hides utility loss.” | equity–utility Pareto analysis + family TPR | Pareto set, P10 Macro-F1, worst BA, Mirai/BASHLITE TPR |
- [ ] `TABLE-SENTINEL-0100` — source line `2229` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “The method has no operational-cost story.” | threshold-stage payload/runtime/storage accounting | actual serialized bytes and threshold-stage timing; no hardware claim |
- [ ] `TABLE-SENTINEL-0101` — source line `2230` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Calibration clients can lie or poison the summaries.” | Part I §3.2A honest-calibration threat boundary + Rob-FCP/PRISM-FCP prior art | explicit non-Byzantine scope statement; no attack-resilience claim |
- [ ] `TABLE-SENTINEL-0102` — source line `2231` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Calibration means ECE/Brier; why are those missing?” | Part I §10.C.7A calibration-object taxonomy | anomaly operating-point calibration is separated from probability and conformal calibration |
- [ ] `TABLE-SENTINEL-0103` — source line `2232` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “Small or low-support clients may pay a different shared-threshold burden.” | Part II §7.5A calibration-support-versus-burden diagnostic | per-seed Spearman support associations plus all-client support/burden table |
- [ ] `TABLE-SENTINEL-0104` — source line `2233` — **Part II — Experiment Programme and Decision Rules / 2. Protocol inheritance and experiment-wide execution additions / 2.8 Reviewer-objection → experiment coverage**
  > | “A 2026 heterogeneous-IoT paper already combines FL calibration and adaptive thresholds.” | CF-HFC collision row + fixed-score causal distinction | citation/positioning only; no multi-component CF-HFC reproduction |
- [ ] `TABLE-SENTINEL-0105` — source line `2242` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | Method / family | Authoritative definition | Role in Part II |
- [ ] `TABLE-SENTINEL-0106` — source line `2244` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | CENTRALIZED_REFERENCE centralized reference | Part I §4.1 | contextual centralized reference only |
- [ ] `TABLE-SENTINEL-0107` — source line `2245` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | SHARED_THRESHOLD shared threshold | Part I §4.2 | locked confirmatory shared-scope anchor |
- [ ] `TABLE-SENTINEL-0108` — source line `2246` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | LOCAL_THRESHOLD local threshold | Part I §4.3 | locked confirmatory local-scope comparator |
- [ ] `TABLE-SENTINEL-0109` — source line `2247` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | FAMILY_THRESHOLD physical-family threshold | Part I §4.4 | mechanism baseline where taxonomy is defensible |
- [ ] `TABLE-SENTINEL-0110` — source line `2248` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | CLUSTER_THRESHOLD data-driven cluster threshold | Part I §4.5 | taxonomy-free grouped-threshold mechanism |
- [ ] `TABLE-SENTINEL-0111` — source line `2249` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | exact pooled / sample-weighted shared constructions | Part II §6.1 | supportive shared-estimator controls |
- [ ] `TABLE-SENTINEL-0112` — source line `2250` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | `MEAN_PLUS_STANDARD_DEVIATION_ESTIMATOR` | Part I §5.1A; Part II §6.2A | fixed-score historical estimator-family sensitivity; sample SD `ddof=1` |
- [ ] `TABLE-SENTINEL-0113` — source line `2251` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | fixed local–global shrinkage | Part I §5.2; Part II §8.2 | locked `lambda in {0.00,0.25,0.50,0.75,1.00}` curve |
- [ ] `TABLE-SENTINEL-0114` — source line `2252` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | size-aware shrinkage | Part I §5.3; Part II §8.3 | deterministic `n_k_used/(n_k_used+100)` mechanism |
- [ ] `TABLE-SENTINEL-0115` — source line `2253` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | LOCAL_CONFORMAL_THRESHOLD | Part I §5.4; Part II §8.4 | finite-sample local coverage diagnostic |
- [ ] `TABLE-SENTINEL-0116` — source line `2254` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | Part I §6.1; Part II §9.1 | benign-only shared federated threshold comparator |
- [ ] `TABLE-SENTINEL-0117` — source line `2255` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | `FEDERATED_KLL_SHARED_THRESHOLD` | Part I §6.1A; Part II §9.2 | KLL shared approximate pooled-quantile comparator; sensitivity `k in {200, 800}` around canonical `k=400` |
- [ ] `TABLE-SENTINEL-0118` — source line `2256` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | FedProx | Part I §7.1; Part II §11.1 | separate-detector training stress test; `mu in {0.001,0.01,0.1,1.0}` |
- [ ] `TABLE-SENTINEL-0119` — source line `2257` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | `FEDAVG_LOCAL_FINE_TUNING` | Part I §7.2A; Part II §11.2A | separate client-personalized detector stress test; exactly 10 benign-training epochs from round-200 FedAvg |
- [ ] `TABLE-SENTINEL-0120` — source line `2258` — **Part II — Experiment Programme and Decision Rules / 3. Method crosswalk — definitions are owned by Part I**
  > | Ditto | Part I §7.2; Part II §11.2 | separate personalized-model stress test; `lambda_D in {0.1,1.0,2.0}`, canonical `1.0` |
- [ ] `TABLE-SENTINEL-0121` — source line `4704` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | Method | Client → server threshold-stage content | Minimum raw payload before serialization overhead | Server → client content |
- [ ] `TABLE-SENTINEL-0122` — source line `4706` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | SHARED_THRESHOLD | one `float64` local threshold | `8` bytes/client | one `float64` shared threshold (`8` bytes/client or one broadcast payload) |
- [ ] `TABLE-SENTINEL-0123` — source line `4707` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | LOCAL_THRESHOLD | no threshold summary required centrally for local deployment | `0` bytes/client | `0` |
- [ ] `TABLE-SENTINEL-0124` — source line `4708` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | FAMILY_THRESHOLD | one `float64` local threshold; family identity only if not already server-known | `8` bytes/client plus family-ID encoding when sent | one family threshold (`8` bytes/client) |
- [ ] `TABLE-SENTINEL-0125` — source line `4709` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | CLUSTER_THRESHOLD | four `float64` fingerprint fields + one `float64` local threshold | `40` bytes/client | cluster ID + cluster threshold; minimum `4 + 8 = 12` bytes/client when ID is `int32` |
- [ ] `TABLE-SENTINEL-0126` — source line `4710` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | fixed/size-aware shrinkage | same local-threshold upload needed for the shared component as SHARED_THRESHOLD | `8` bytes/client | shared threshold (`8` bytes/client); local shrinkage computed client-side |
- [ ] `TABLE-SENTINEL-0127` — source line `4711` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | `FEDERATED_BENIGN_SUMMARY_THRESHOLD` | `uint64 n`, `float64 mean`, `float64 variance`, plus each predeclared `uint64` exceedance count | `24 + 8J` bytes/client for `J` exceedance counters | one shared threshold (`8` bytes/client) |
- [ ] `TABLE-SENTINEL-0128` — source line `4712` — **Part II — Experiment Programme and Decision Rules / 13. Operational translation / Payload inventory**
  > | `FEDERATED_KLL_SHARED_THRESHOLD` | serialized KLL sketch | measured serialized size; no fixed raw lower bound substituted | one shared threshold (`8` bytes/client) |

## 15C. Coverage-closure invariant

The matrix is considered **source-complete** only when all of the following are simultaneously true for the locked roadmap hash:

- every H2–H4 heading and numbered/named bold anchor is represented in Section 15;
- every list/procedure item is represented in Section 14 or an experiment/metric/gate card;
- every display-math block is represented in Section 3;
- every fenced literal/code block is represented in Section 4;
- every roadmap table row through Part IV is either already reproduced by a curated matrix or represented by Section 15B;
- every prose-like semantic statement through Part IV is either already reproduced verbatim or represented by Section 15A;
- every Part II experiment-index row has exactly one experiment card;
- every Part III metric/statistical/temporal contract is represented;
- every mandatory figure/table/report output is represented;
- every Gate A–R requirement is represented;
- no source-derived requirement can be closed by a section title alone.

This closure invariant is an **omission detector**, not a new scientific authority. When a sentinel and a curated row overlap, the roadmap wording governs and the auditor records the cross-link rather than implementing duplicate behavior.

## 16. Repository audit / remediation workflow — no backwards compatibility

The agent should execute the following in order. Repository inspection happens **after** this matrix is locked against the roadmap snapshot.

### 16.1 Repository inventory

Inventory packages, modules, classes, dataclasses, enums, functions, constants, experiment definitions, pipeline stages, CLI entry points, tests, fixtures, readers/writers, report/figure generators, stale aliases, duplicate implementations, dead modules.

### 16.2 Structural dependency graph

Build import/dependency graph and verify the intended domain/protocol/capability/pipeline/reporting direction; flag circular or wrong-owner scientific responsibility.

### 16.3 Runtime/call graph

Prove every required implementation is actually reachable from the intended experiment execution spine; `TEST_ONLY` and `UNREACHABLE` are failures for required production behavior.

### 16.4 Roadmap → repository mapping

For every matrix row, identify the single implementation owner, runtime caller, tests, and produced artifacts.

### 16.5 Repository → roadmap reverse mapping

For every material scientific implementation, identify the authorizing requirement/experiment. Remove stale/unauthorized behavior.

### 16.6 P0/P1 remediation

Fix leakage, identity, terminal-detector, pairing, formulas, grids, and metric/statistical semantics first.

### 16.7 P2/P3 remediation

Add missing mandatory evidence, mechanism outputs, provenance, release/reconstruction support.

### 16.8 P4 cleanup

Delete stale aliases, wrappers, dead code, duplicated old/new paths; update callers and tests rather than preserving compatibility.

### 16.9 Static verification

Format/lint/type-check plus focused unit/property/negative tests.

### 16.10 Integration verification

Run pipeline-level identity, leakage, coordinate-completeness, artifact-provenance, and report-reconstruction tests.

### 16.11 One-seed scientific smoke

Run exactly one full seed through the real workflow: data→population→split→preprocess→train→terminal detector→score→calibration→threshold→evaluate→analyze→report/provenance. Smoke does not establish statistical claims.

### 16.12 Full coordinate completeness

Expand declarative experiment grids, compare expected coordinates to actual materialized coordinates, and reject missing/unauthorized cells.

### 16.13 Gates A–R

Evaluate every Gate row above with retained evidence.

### 16.14 Publication readiness

Validate claim tiering, negative evidence, figure/table reconstruction, novelty gate, and the release manifest before declaring readiness.

## 17. Required implementation end state

- [ ] exactly one active implementation per scientific contract unless the roadmap explicitly defines multiple protocol identities
- [ ] one declarative experiment planner capable of enumerating all mandatory coordinates before execution
- [ ] one canonical scoring path per detector/preprocessing/population/seed coordinate; threshold policies never rescore
- [ ] one typed availability/unavailability model; missing implementation cannot masquerade as scientific unavailability
- [ ] one provenance chain from raw/canonical row identity through split, preprocessing, model, scores, thresholds, metrics, analyses, figures/tables
- [ ] no active opaque aliases, no compatibility shims, no old/new duplicate pipelines
- [ ] all mandatory grids complete, all optional grids visibly optional, all negative/unfavorable results retained
- [ ] every report/table/figure reconstructable from manifest-validated source tables and exact experiment coordinates

