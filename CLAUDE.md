# DATP-Core Engineering and Scientific Contract

## 1. Authority

DATP-Core implements the journal-extension programme defined by `docs/Journal_Extension_Master_Roadmap.md`.

For scientific decisions, authority is:

1. the master roadmap;
2. the canonical experiment specifications and typed core/scientific contracts;
3. implementation;
4. tests and documentation.

Never change the roadmap or weaken a scientific invariant to preserve an implementation, an old package boundary, or a stale test.

## 2. Locked scientific identity

DATP-Core is a controlled study of threshold-calibration scope in federated IoT anomaly detection.

Within each seed, regime, training baseline, and named preprocessing identity, compared threshold methods must reuse the same:

- selected detector state;
- preprocessing state;
- client identities;
- predefined data partitions;
- benign calibration evidence;
- held-out scores and labels;
- client eligibility rule;
- metric definitions.

Only the declared threshold estimator/scope may differ inside a controlled ladder.

Calibration is benign-only. Attack-labelled rows must never influence threshold construction, quantile selection, client eligibility, checkpoint selection, cluster count/features, comparator tuning, shrinkage strength, or conformal settings.

AUROC is a fixed-score/model-quality control. It is not the primary threshold-policy verdict. The sole confirmatory endpoint remains the roadmap-declared N-BaIoT natural-device shared-versus-local comparison on cross-client `CV(FPR)` over the locked paired seed cohort and BCa decision rule.

Training-side FedProx and genuine Ditto studies use separate detectors and remain stress tests. Edge-IIoTset and CICIoT2023 retain their declared capability and interpretation boundaries. Null, opposite, unavailable, and infeasible outcomes must be reported rather than hidden.

Do not add security attacks, defenses, formal privacy claims, deployment claims, additional external datasets, or new scientific methods outside the roadmap.

## 3. Canonical source architecture

Package ownership below is a contract, not a suggestion. Production functionality must live in the
package that owns its responsibility; obsolete roots are deleted after every active caller has been
migrated. Do not preserve old locations with aliases, re-exports, forwarding modules, redirects,
fallback imports, or compatibility packages. Do not use `__init__.py` package markers as re-export
barrels; they should remain empty unless a package genuinely owns a stable public facade.

Canonical ownership is:

- `core`: lowest-level errors, identifiers/enums/value identities, numeric value objects, and immutable cross-cutting contracts.
- `data`: dataset capability/schema/reader/materialization logic, population construction/splitting/integrity, and preprocessing fitting/transformation/validation.
- `detector`: autoencoder, training algorithms, checkpoint contracts/selection, and score generation.
- `thresholds`: benign calibration eligibility/sampling, quantile construction, threshold policies, and declared threshold variants.
- `analysis`: metrics, statistical inference/decisions, mechanisms, and operational translation only. It does not execute experiments or own persistence.
- `experiments`: experiment declarations/specifications plus their run/report recipes. `anchor` is an experiment, not a top-level package. Training-side stress tests remain scientifically separate from the fixed-detector threshold ladder.
- `artifacts`: generic layout, provenance, serialization, publication, reuse, and completion-marker/checksum lifecycle ownership shared by every domain. Domain packages (`data`, `detector`, `thresholds`) may keep their own persistence orchestration colocated with the validation logic that governs it, but the underlying atomic-publish/checksum/reload primitives must delegate to `artifacts` rather than reimplementing them.
- `presentation`: reusable table/figure construction and presentation validation only. Experiment-specific reporting belongs to each experiment's own report logic.
- `app`: public programme planning/campaign/validation and CLI adapters only. It does not own scientific execution kernels.
- `runtime`: compute/device, deterministic execution, process configuration, and filesystem primitives.

The following source roots and architectural concepts are obsolete and must not exist after the cutover:

- `datp_core.anchor`;
- `datp_core.calibration`;
- `datp_core.datasets`;
- `datp_core.domain`;
- `datp_core.evaluation`;
- `datp_core.learning`;
- `datp_core.pipeline`;
- `datp_core.preprocessing`;
- `datp_core.protocols`;
- `datp_core.thresholding`;
- `datp_core.reporting`;
- `datp_core.cli`;
- forwarding or redirect modules preserving deleted imports.

Do not invent a second, independent implementation of a concept another package already owns (duplicate models, duplicate constants, duplicate atomic-publish lifecycles, duplicate checksum logic). A structural change may move, merge, split, rename, or delete source files when required by this ownership contract. Never keep a superseded module merely because it already contains working code.

## 4. No backward compatibility

There is no backward-compatibility requirement.

Never add or retain:

- compatibility shims;
- aliases for deleted types or functions;
- deprecated enum members;
- legacy import paths;
- forwarding modules;
- duplicate entry points;
- dual schemas;
- fallback imports;
- migration adapters;
- old/new switches;
- tests whose only purpose is preserving removed behavior.

When a contract changes, migrate all active callers and delete the obsolete path.

## 5. Strong domain modeling

Use enums for every closed categorical domain. Reuse an existing enum before creating another. Use descriptive names such as `SHARED_THRESHOLD`, `LOCAL_THRESHOLD`, `FAMILY_THRESHOLD`, and `CLUSTER_THRESHOLD` in runtime code. Do not introduce runtime B0/B1/B2/B3/B4/B5 identifiers or other numbered aliases.

Use existing value objects, frozen dataclasses, and strict Pydantic models for meaningful scientific/application quantities and records. Do not model domain concepts with loose primitives when an established type exists.

Forbidden shortcuts include:

- `Any`;
- `object` used to avoid modeling;
- `dict[str, Any]`;
- untyped nested dictionaries as inter-layer contracts;
- broad casts;
- unchecked assertions;
- `# type: ignore`;
- `noqa` or static-analysis suppressions introduced to hide defects.

External-library dictionaries may exist only at a narrow boundary and must immediately convert to/from typed project models.

## 6. Configuration and reproducibility

Scientific and runtime behavior must come from roadmap-backed validated experiment specifications or explicit structural invariants.

Do not hardcode or invent:

- seeds;
- split ratios;
- quantiles or thresholds;
- calibration support;
- client counts;
- cluster counts;
- experiment membership;
- round/epoch budgets;
- optimizer parameters;
- checkpoint rules;
- statistical confidence/bootstrap settings;
- metric sets;
- dataset feature/label semantics;
- resource/device assumptions;
- scientific output layout choices.

Required scientific values do not get hidden defaults or fallback recovery. Missing information fails explicitly.

Every stochastic operation must receive an explicit declared seed. Iteration, traversal, planning, client order, experiment expansion, coordinates, and serialization must be deterministic where the protocol requires it.

## 7. Dataset and metric integrity

Dataset behavior is capability-driven. Never infer physical clients, family taxonomy, timestamps, chronological meaning, attack assignment, or metric support from filenames or general knowledge when the audited artifact does not provide it.

Unsupported metrics are explicit unavailable/infeasible results, not fabricated values and not silently dropped rows.

No imputation, zero-fill, clipping, infinity replacement, inferred labels, fabricated timestamps, pseudo-device identity, or outcome-driven row filtering may be introduced unless the roadmap explicitly defines it.

## 8. Fixed-score and leakage controls

Threshold methods must not retrain detectors, refit model-input preprocessing, select different checkpoints, alter eligible clients, or consume held-out evaluation outcomes.

Core policy comparisons must preserve fixed-score identity. Evaluation must validate the required fixed-score invariants and capability contracts before producing conclusions.

Report generation consumes validated evidence; it does not rerun training or recompute primary scientific evidence from uncontrolled inputs.

## 9. Application and CLI rules

The public CLI is `datp_core.app.cli.app` and exposes only:

```text
validate [EXPERIMENT_ID]
plan [EXPERIMENT_ID]
preprocess [DATASET_ID] [--overwrite]
smoke [EXPERIMENT_ID] [--overwrite]
anchor reproduce [--overwrite]
anchor verify
anchor status
run experiment <EXPERIMENT_ID> [--overwrite]
run campaign [--overwrite]
report [EXPERIMENT_ID] [--overwrite]
status [EXPERIMENT_ID]
```

CLI booleans are adapter input only. Convert lifecycle choices immediately to typed application enums. Do not add scientific hyperparameters to the command line.

Every non-suppressed, non-anchor experiment specification must have exactly one registered application execution path. Suppressed experiments must remain explicitly suppressed. Registry validation fails on missing, duplicate, or stale experiment wiring.

Full programme planning must use each experiment's declared seed cohort rather than applying one global cohort to all datasets/regimes.

## 10. Artifact lifecycle

Use `artifacts` as the single owner of generic coordinates/layout, checksums/provenance, serialization, persistence repositories, completion validation, and reusable publication mechanics.

Do not introduce:

- arbitrary run IDs;
- random output directories;
- `latest` aliases;
- duplicate manifests;
- hidden caches;
- partial outputs marked complete;
- incompatible evidence reuse;
- package-specific ad-hoc persistence when an `artifacts.repositories` owner exists.

Smoke evidence is isolated under the smoke root and is never confirmatory evidence. `--overwrite` deletes/rebuilds only the owning scope.

## 11. Code quality

Bias toward deletion and consolidation. Before adding a class/function/file, search for an existing responsibility that can be reused or extended.

Delete:

- dead code;
- obsolete callers;
- duplicate models/enums;
- duplicated path/checksum/lifecycle logic;
- thin pass-through wrappers;
- meaningless manager/util classes;
- stale comments and documentation;
- tests for deleted APIs.

Classes must own meaningful state, validation, lifecycle, or polymorphism. Functions must have one coherent typed responsibility. Do not catch broad `Exception`; use domain-specific failures and preserve context.

Do not add AI-style narration comments or migration commentary to production source.

## 12. CUDA and performance

CUDA is mandatory for training and GPU-appropriate execution. Do not add CPU fallback paths. Preserve deterministic GPU settings required by the protocol. Use batching/vectorized operations and do not trade scientific equivalence for speed.

## 13. Tests

Tests protect public behavior and scientific invariants, not old architecture or test count.

When architecture changes, rewrite or delete stale tests. Never preserve dead production code for a test.

Prioritize tests for:

- experiment/registry validation;
- fixed-score and leakage controls;
- capability gating;
- deterministic planning and correct seed cohorts;
- artifact completion/reuse;
- threshold and metric semantics;
- application/CLI public contracts;
- exact package/import architecture boundaries;
- previously observed defects.

Do not weaken assertions, skip failures, or shrink scientific protocols merely to make tests pass.

## 14. Quality gates

For repository-wide completion, use the configured tools when the execution environment supports them:

```bash
ruff check .
pyright
python -m importlinter
pytest
```

Fix root causes rather than changing quality configuration to hide findings. If a gate cannot run because the execution environment lacks the repository, CUDA, raw datasets, or required credentials, report that limitation explicitly; do not claim it passed.

## 15. Required workflow

For broad work:

1. read the roadmap and this contract;
2. inspect current experiment specifications, call graph, datasets/capabilities, artifacts, and tests;
3. search for reusable implementations;
4. define clean target ownership using the canonical package boundaries and delete duplicate paths;
5. implement the canonical contracts and migrate every active caller;
6. validate registry, planning, fixed-score science, naming, typing, imports, dead code, and tests;
7. perform a final scientific-drift audit against the roadmap;
8. leave exactly one coherent architecture with no compatibility layer.