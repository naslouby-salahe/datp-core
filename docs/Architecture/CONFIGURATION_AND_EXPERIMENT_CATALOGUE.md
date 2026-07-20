# Configuration and Experiment Catalogue

## Purpose

This is the architecture guide to the configuration surface that exists in
this repository. The YAML documents are authoritative for executable values;
the roadmap is authoritative for scientific claims and interpretation.

## Configuration layout

```text
configs/
├── datasets/
│   ├── nbaiot.yaml
│   ├── ciciot2023.yaml
│   └── edge_iiotset.yaml
├── experiments.yaml
├── protocols.yaml
└── runtime.yaml
```

There are exactly six configuration documents. There is no `models/`
configuration directory, per-experiment YAML directory, `execution.yaml`, or
separate dataset-audit configuration root.

| File | Owns |
|---|---|
| `datasets/*.yaml` | Dataset source contract, field schema, feature order, materializations, row exclusions, splits, client construction, and setup capabilities. |
| `protocols.yaml` | Model, optimizer, batching, seed, checkpoint, training, threshold, eligibility, metric, statistical, result, report, and operational definitions. |
| `experiments.yaml` | Study populations, capability/suppression vocabulary, the external readiness gate, and the experiment catalogue. |
| `runtime.yaml` | Repository roots, raw-source policy, determinism, device/resource policy, and execution profiles. |

Every scientific and operational value is explicit. YAML anchors, aliases,
merge keys, and implicit scientific defaults are not part of the contract.

## Resolution contract

An experiment resolves from its `name`. Each population resolves to a dataset,
setup, and metric bundle. Training, checkpoint, seed, eligibility, threshold,
statistical, and report references resolve into `protocols.yaml`. Resolution
must reject unknown references, missing values, incompatible capabilities, and
unmet typed gates. It must retain the resolved materialization, split, eligible
set, and derived seeds in artifact identity. It cannot silently reduce clients,
rounds, batch size, calibration rows, or seed count.

## Dataset contracts

### N-BaIoT

| Setup | Materialization | Purpose |
|---|---|---|
| `natural_devices` | `datp_core` | Nine physical-device clients for the journal programme. |
| `anchor_natural_devices` | `anchor` | Historical five-seed reproduction. |
| `dirichlet_partitioned` | `datp_core_dirichlet` | Twenty deterministic synthetic clients for controlled heterogeneity. |

The anchor uses standard normalization fit separately on each client's benign
training rows. It is distinct from the journal materialization and never
inherits that materialization's preprocessing or split identity. The
Dirichlet contract fixes row order, source-domain draws, capacity-constrained
integer assignment, seed derivation, tie breaking, split scope, and manifest
invariants. Its IID arm is an explicit uniform allocation.

### CICIoT2023

The merged CSV tree supplies file-defined pseudo-clients, never physical
devices. Duplicate equivalence is the exact hash over model features and
binary label. Feature-identical rows with conflicting labels stay separate and
their count is reported. Whole equivalence classes are placed in one split
before noncanonical members are removed. This dataset supports only the
file-pseudo-client applicability boundary, not device reconstruction or time.

### Edge-IIoTset

The normal-traffic group-folder path is the authoritative benign client
identity. Every source-integrity-valid benign row remains in its folder client.
Direction-normalized endpoint resolution is only for source-integrity audit,
attack-assignment diagnostics, and provenance; it cannot exclude or reassign a
benign row.

| Setup | Population | Materialization | Scope |
|---|---:|---|---|
| `sensor_groups` | 10 folders | `group_benign` | Static benign operating-point equity. |
| `chronological_sensor_groups` | 9 folders | `group_chronological` | Temporal benign operating-point equity. |
| `chronological_static_reference_groups` | Same 9 folders | `group_chronological_static_reference` | Matched temporal control. |

Modbus remains in the 10-client static population because its rows retain the
declared 63-column layout. It is excluded only from both temporal arms because
`frame.time` contains address literals rather than usable temporal values. The
two temporal arms must resolve to the same nine identifiers. Edge supports
benign calibration and FPR evidence, but not per-client attack-sensitive
metrics; Edge experiments never use the family threshold (B3).

## Protocol contracts

`protocols.yaml` owns the fixed dense autoencoder, `adam_default`, standard
batching, and these training profiles: `federated_averaging`,
`federated_averaging_anchor`, `federated_averaging_personalized`,
`federated_proximal`, and `centralized_pooled`. Standard batching is 256 rows,
one accumulation step, per-epoch shuffle, and retained final partial batch.
FedAvg and the anchor use one local epoch and full participation.

### Historical anchor

The anchor cohort is five paired training seeds `0..4`. It uses Adam at 0.001,
batch size 256, one local epoch, full participation, and client-local
train-split standardization. It trains no more than 150 rounds. Starting at
round 40, it tests the trailing ten FedAvg-weighted benign-validation losses:

```text
abs(loss[r-9] - loss[r]) / abs(loss[r-9]) < 0.005
```

A zero start loss has relative change zero. The first qualifying round is
selected; round 150 is selected otherwise; exactly one final checkpoint is
saved. The historical interval is a 95% percentile bootstrap of the mean
paired delta, with 10,000 resamples and seed 42. It is not the journal
ten-seed BCa procedure.

`datp_core_round_grid` has rounds `25, 50, 75, 100, 125, 150, 200`. The
journal cohort has paired training seeds `0..9` and uses its declared BCa
profiles. Cluster insufficiency occurs only when eligible clients are fewer
than K; equality is valid.

Artifact identity includes resolved model/optimizer/batching settings,
training overrides, checkpoint semantics, threshold semantics, eligible set,
metric definition, analysis formula, uncertainty procedure, and upstream
dataset/materialization/split identity. Reuse is forbidden when one differs.

## Experiment catalogue

| Experiment | Population(s) | Role |
|---|---|---|
| `anchor_reproduction` | N-BaIoT anchor natural devices | Historical reproduction. |
| `confirmatory_threshold_scope_effect` | N-BaIoT natural devices | Sole confirmatory B1-versus-B2 comparison. |
| `shared_threshold_construction_sensitivity` | N-BaIoT natural devices | Shared-threshold sensitivity. |
| `threshold_quantile_sensitivity` | N-BaIoT natural devices | Quantile sensitivity. |
| `external_threshold_quantile_sensitivity` | Edge static groups | External quantile sensitivity. |
| `controlled_heterogeneity_response` | N-BaIoT Dirichlet clients | Controlled non-IID response. |
| `cluster_and_family_threshold_mechanism` | N-BaIoT natural devices | Family/cluster mechanism. |
| `external_cluster_threshold_mechanism` | Edge static groups | External cluster mechanism. |
| `calibration_window_size_stability` | N-BaIoT natural devices | Calibration-size robustness. |
| `local_global_threshold_shrinkage` | N-BaIoT natural devices | Shrinkage robustness. |
| `conformal_local_threshold_coverage` | N-BaIoT natural devices | Local conformal diagnostic. |
| `external_conformal_local_threshold_coverage` | Edge static groups | Separate benign-only conformal diagnostic. |
| `centralized_pooled_reference` | N-BaIoT natural devices | B0 supportive reference. |
| `federated_summary_comparator` | N-BaIoT natural devices | Benign federated-summary comparator. |
| `external_federated_summary_comparator` | Edge static groups | External comparator. |
| `file_pseudo_client_applicability_boundary` | CICIoT2023 pseudo-clients | Applicability boundary. |
| `external_sensor_group_validation` | Edge static groups | External validation. |
| `chronological_recalibration_evaluation` | Edge temporal and static-control groups | One-shot temporal boundary. |
| `fedprox_aggregation_stress_test` | N-BaIoT natural devices | FedProx stress test. |
| `external_fedprox_aggregation_stress_test` | Edge static groups | External FedProx test. |
| `model_personalization_absorption_test` | N-BaIoT natural devices | Ditto absorption test. |
| `external_model_personalization_absorption_test` | Edge static groups | External personalization test. |
| `operational_alert_burden` | N-BaIoT natural devices | Conditional operational translation. |

The only confirmatory endpoint is the N-BaIoT ten-seed B1-versus-B2
`CV(FPR)` comparison under its declared paired BCa procedure. Other results
cannot replace it.

## Cross-experiment controls

`edge_external_benign_coverage` runs before listed Edge entries train or
evaluate thresholds. Each candidate folder client needs at least 100 benign
calibration rows and at least 90% of candidate clients must qualify. Failure
is typed as blocked or deferred. Population reduction without explicit roadmap
authorization is forbidden.

The 50-row calibration condition is experimental; the primary local threshold
requires at least 100 rows. Full calibration is evaluated and reported, with
within-seed replicates. The external conformal entry is independent, benign
only, attack-metric unavailable, and never confirmatory.

The temporal study compares B1, B2, and B4 for frozen thresholds, one-shot
recalibration, and a matched static reference. All states use the same frozen
historically trained model. Recovery is defined only after its predeclared
meaningful paired degradation gate; ratios are not clamped and outcome bands
are mutually exclusive.

Every absorption comparison requires equal dataset, setup, materialization,
client population, split manifest, training seed, checkpoint round, eligible
set, threshold-policy semantics, and metric definition. Other differences are
allowed only through the explicit label mapping; undefined denominators remain
typed undefined outcomes.

## Runtime and validation

`runtime.yaml` provides roots and operational rules. It cannot redefine
scientific settings or authorize a smaller batch, fewer clients, fewer rounds,
fewer seeds, or an unapproved device fallback.

Validate syntax and duplicate keys for all six documents, resolve every
cross-file reference, validate population setup/metric bundles and experiment
profile/policy/report/prerequisite/gate references, and persist the resolved
configuration identity. The raw Edge audit must continue to verify the
10-folder static and 9-folder temporal/control contract.
