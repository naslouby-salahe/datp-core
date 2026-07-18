# CONFIGURATION_AND_EXPERIMENT_CATALOGUE

## 1. Minimal YAML organization

```text
configs/
├── experiments/     # one document per ExperimentTemplate or standalone ExperimentDefinition
├── datasets/          # reusable DataDefinition documents
├── protocols/           # reusable DetectorDefinition and EvaluationDefinition fragments
├── runtime/               # named ExecutionDefinition profiles
└── reporting/               # ReportingDefinition catalogues
```

Five directories, each with exactly one schema owner (`config/schemas/`, one
module per directory). Every document under `experiments/` is a complete,
resolvable root that references, but never duplicates, entries under the
other four directories. There is no per-dataclass directory and no deep
nesting.

## 2. Schema ownership

| Directory | Owns | Schema module |
|---|---|---|
| `experiments/` | identity, dataset/protocol/runtime/reporting references, any sweep dimension, `requires_passed` | `config/schemas/experiment.py` |
| `datasets/` | dataset, client construction, split definition, preprocessing | `config/schemas/data.py` |
| `protocols/` | training protocol, checkpoint policy, threshold construction, evaluation suite, statistical procedure | `config/schemas/protocol.py` |
| `runtime/` | execution mode, device policy, resource budget, batch profile | `config/schemas/runtime.py` |
| `reporting/` | table/figure/report-artifact catalogue and formats | `config/schemas/reporting.py` |

A field absent from its owning document is a validation failure at load
time; it is never satisfied by another document.

## 3. Configuration resolution pipeline

```text
YAML document
  → boundary schema (Pydantic v2, one per directory)
    → typed reference resolution (dataset/protocol/runtime/reporting refs)
      → cross-document scientific-compatibility validation
        → frozen ExperimentDefinition or ExperimentTemplate
          → resolved configuration snapshot (fingerprinted, persisted)
            → stage-specific identity projection (PIPELINE_EXECUTION_AND_ARTIFACTS.md §3)
```

`config/compose.py` is the single typed composer performing every step
exactly once per invocation. No Pydantic model, YAML mapping, or raw
dictionary exists past the frozen-definition step; `application`,
`analysis`, and `infrastructure` never import `config`.

## 4. Scientific authorization

Authorization is enforced by construction validators on the closed
discriminated unions and by cross-field validators at resolution time —
never by a separate "authorized profile" object duplicating the resolved
definition's fields (`SCIENTIFIC_FOUNDATION.md §8`). Resolution rejects, for
every affected document:

- `evidence_role = CONFIRMATORY` paired with a dataset setting other than
  `natural_device_evaluation`, a threshold pair other than
  `{SharedThreshold(MEAN), LocalThreshold}`, a paired-seed count other than
  ten, a primary metric other than `CV_FPR`, or `tier ≠ TIER_1`.
- `evidence_role = ANCHOR` with a paired-seed count other than five, or
  without an `anchor_reference_interval`.
- A `BenignCalibrationSplit` reachable from any field capable of carrying an
  attack label.
- `training_protocol = FederatedAveragingTraining` or
  `FederatedProxTraining` with a non-`NONE` personalization strategy on any
  experiment whose `evidence_role` is not the one authorized
  `model_personalization_absorption_test` slug.
- `TrainingProtocol.FederatedProxTraining.mu` equal to zero, equal to a
  FedAvg-equivalent value, or absent from the pre-registered grid
  `{0.001, 0.01, 0.1}`.
- Any non-`SCIENTIFIC`/`PRINT_GRADE` field explicitly marked `unresolved`
  reaching a `SCIENTIFIC` or `PRINT_GRADE` execution mode.
- Any experiment whose `identity.slug` matches a rejected or out-of-scope
  entry (`SCIENTIFIC_FOUNDATION.md §7.6`).
- A `regime_label` present in an authored YAML document at all — it is
  computed post-resolution by `derive_regime_label`
  (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.1`) and is never a legal
  input field (`§6` above).

## 5. No hidden defaults

No scientific, identity-bearing, or output-affecting field has a Python
default, a dataclass default, a Pydantic default, a `dict.get` fallback, an
environment fallback, a CLI override, a third-party library default,
implicit inheritance, or a YAML merge key or anchor. Every such value is
explicit in a YAML document or reached through a deterministic typed
reference. A discriminated variant rejects a field it does not own:

```yaml
# accepted
threshold:
  policy: local_global_shrinkage_threshold
  shrinkage_weight: 0.5

# rejected: cluster_count is not a field of local_global_shrinkage_threshold
threshold:
  policy: local_global_shrinkage_threshold
  shrinkage_weight: 0.5
  cluster_count: 3
```

`None` represents a meaningful domain state (for example "no personalization
strategy") and never an omitted required value.

## 6. Complete field ownership and identity matrix

| Field family | Scientific identity | Execution identity | Provenance | Reporting presentation | YAML required |
|---|---:|---:|---:|---:|---:|
| Dataset, dataset version | Yes | No | Yes | No | Yes |
| `execution_status` (`MANDATORY`/`OPTIONAL`/`SUPPRESSED`) | No (does not affect a computed value) | No | Yes | Yes (governs whether a result is main-paper or supplement) | Yes |
| `regime_label` | No — derived, never authored | No | Yes (citation only) | Yes | No — computed by `derive_regime_label`, rejected if supplied in YAML |
| Feature schema | Yes | No | Yes | No | Runtime-captured (source-inspected), never authored |
| Client construction, partition seed | Yes | No | Yes | No | Yes |
| Split boundaries (chronological fraction, timestamp field) | Yes | No | Yes | No | Yes |
| Preprocessing (strategy, scope) | Yes | No | Yes | No | Yes |
| Detector architecture (hidden dims, activation) | Yes | No | Yes | No | Yes |
| Optimizer, learning rate | Yes | No | Yes | No | Yes |
| Training rounds, checkpoint schedule | Yes | No | Yes | No | Yes |
| Local epochs, participation | Yes | No | Yes | No | Yes |
| Micro-batch size, gradient accumulation | Yes | No | Yes | No | Yes |
| Worker count | Conditional (identity-bearing only if ordering/output-affecting) | Yes | Yes | No | Yes |
| Precision, determinism level | Yes | No | Yes | No | Yes |
| Checkpoint-selection rule | Yes | No | Yes | No | Yes (locked; one value) |
| Threshold construction and its parameters (quantile, K, λ, α) | Yes | No | Yes | Yes (units, direction) | Yes |
| Cluster-count canonicality, clustering `n_init`/`max_iter` | Yes | No | Yes | No | Yes |
| Shrinkage weight | Yes | No | Yes | Yes | Yes |
| Conformal coverage / alpha | Yes | No | Yes | Yes | Yes |
| Eligibility minimum-calibration threshold | Yes | No | Yes | No | Yes |
| Metric selection | Yes | No | Yes | Yes | Yes |
| Traffic rate (alert burden) | Yes (when requested) | No | Yes | Yes | Yes, when `AlertBurdenEvaluationSuite` is selected |
| Seed cohort size and derivation rule | Yes | No | Yes | No | Yes |
| Confidence level | Yes | No | Yes | Yes | Yes |
| Bootstrap resample count | Yes | No | Yes | Yes | Yes; **unresolved in both source documents — genuine blocker, `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`** |
| Effect-size procedure (Wilcoxon, Cliff's delta) | Yes (descriptive only) | No | Yes | Yes | Yes |
| Runtime device / CUDA requirement | No | Yes | Yes | No | Yes |
| GPU model, driver version | No | No | Yes | No | Runtime-captured only |
| RAM / VRAM budget | No | Yes | Yes | No | Yes; **not numerically specified in either source document — genuine blocker** |
| Output format | No | No | Yes | Yes | Yes |
| Report ordering | No | No | Yes | Yes | Yes |
| Log interval | No | No | Yes | No | Yes (cosmetic; documented single owner) |

## 7. Discriminated variants

Every multi-shaped field carries an explicit discriminator, never an
inferred shape. Example, client construction:

```yaml
client_construction:
  method: dirichlet_partitioned_clients
  client_count: 20
  alpha: 0.3
  # partition_seed: unresolved — no explicit partition seed integer is
  # given by either source document; recorded as a blocker, not defaulted.
```

## 8. Fingerprinting rules

A `StageIdentity` or `ScoreIdentity` fingerprint is a blake3 digest of a
canonical tuple of typed, quantized fields — never a JSON serialization of a
specification. `ThresholdPercentile`, `ShrinkageWeight`, `CoverageRatio`,
and similar identity-bearing decimals are canonicalized once, at
construction, to a fixed twelve-fractional-digit `Decimal` representation
using round-half-even, so `fpr_target == 1 − quantile` holds exactly
regardless of computation path. Enum members contribute their stable
serialized value. The resolved configuration snapshot itself is
fingerprinted the same way and persisted as a `RESOLVED_CONFIGURATION`
artifact before planning begins. An identity-projection rule determines
which fields enter which stage's fingerprint: a reporting-format change
never invalidates training; a threshold-policy change never invalidates
scores; a metric addition never invalidates a threshold; a detector change
invalidates every downstream checkpoint and score
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md §4`).

## 9. Anchor configuration

`configs/experiments/anchor_reproduction.yaml`. Every value below is either
explicitly given by a source document or explicitly marked unresolved; none
is invented.

```yaml
slug: anchor_reproduction
display_name: Anchor Reproduction
evidence_role: anchor
execution_status: mandatory
dataset: datasets/natural_device_nbaiot.yaml
protocol: protocols/core_federated_averaging.yaml
evaluations:
  - threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
    statistics:
      method: bca_bootstrap
      confidence_level: 0.95
      resample_count: unresolved   # BLOCKED — see field-ownership matrix, §6
  - threshold: { policy: local_threshold, quantile: 0.95 }
    statistics:
      method: bca_bootstrap
      confidence_level: 0.95
      resample_count: unresolved   # BLOCKED
seed_plan:
  paired_seed_count: 5
  derivation: deterministic_from_experiment_seed
  experiment_seed: unresolved      # BLOCKED — no base seed integer is given by either source
operations:
  runtime: runtime/scientific.yaml
  artifacts: { namespace: derived_from_evidence_role }
  reporting: reporting/anchor_reporting.yaml
anchor_reference_interval:
  metric: cv_fpr_delta
  confidence_level: 0.95
  lower_bound: 0.647
  upper_bound: 0.769
```

Every anchor-identity value that the source documents actually supply —
evidence role, dataset, both threshold constructions, the quantile `0.95`,
the five-seed count, the confidence level `0.95`, and the reference interval
`[0.647, 0.769]` — is explicit here, none defaulted in Python. The two
fields the source documents do not supply (`resample_count`,
`experiment_seed`) are marked `unresolved`, per `§4` this blocks the
document from `SCIENTIFIC`/`PRINT_GRADE` scheduling until an authority
supplies them; there is no `anchor: true` switch anywhere that bypasses this
document.

## 10. Confirmatory experiment configuration

`configs/experiments/confirmatory_threshold_scope_effect.yaml`:

```yaml
slug: confirmatory_threshold_scope_effect
display_name: Confirmatory Threshold-Scope Effect
evidence_role: confirmatory
execution_status: mandatory
tier: tier_1
roadmap_reference: E-C1
dataset: datasets/natural_device_nbaiot.yaml
protocol: protocols/core_federated_averaging.yaml
evaluations:
  - threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
    statistics: { method: bca_bootstrap, confidence_level: 0.95, resample_count: unresolved }
  - threshold: { policy: local_threshold, quantile: 0.95 }
    statistics: { method: bca_bootstrap, confidence_level: 0.95, resample_count: unresolved }
seed_plan:
  paired_seed_count: 10
  derivation: deterministic_from_experiment_seed
  experiment_seed: unresolved
requires_passed: [anchor_reproduction]
operations:
  runtime: runtime/scientific.yaml
  artifacts: { namespace: derived_from_evidence_role }
  reporting: reporting/main_confirmatory_table.yaml
```

`requires_passed` is a typed reference to another document's
`identity.slug`, resolved by the planner against the `AnchorEquivalenceGate`
result, never a free-text dependency string (`CFG-08`).

## 11. Reusable dataset configuration

`configs/datasets/natural_device_nbaiot.yaml`, using only the source-given
physical-device client count for N-BaIoT:

```yaml
dataset: n_baiot
client_construction:
  method: physical_device_clients
  device_count: 9
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
```

## 12. Reusable protocol configuration

`configs/protocols/core_federated_averaging.yaml`, using only the
source-locked implementation decisions:

```yaml
training_protocol:
  kind: federated_averaging_training
  local_epochs: 1
  participation: full
  personalization: none
autoencoder:
  hidden_dims: [80, 40, 20]
  activation: relu
  batch_normalization: false
optimizer: { type: adam, learning_rate: 0.001, scheduler: none }
precision: fp32
determinism: strict
checkpoint_schedule:
  rounds: [25, 50, 75, 100, 125, 150, 200]
  rounds_max: 200
checkpoint_selection:
  rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
  tie_break: earliest_scheduled_round
training_batch:
  micro_batch_size: 256
  gradient_accumulation_steps: 1
  effective_batch_size: 256
eligibility:
  minimum_calibration_sample_count: 100
```

Every value above — the encoder widths `(80, 40, 20)`, no batch
normalization, MSE-implying reconstruction objective, Adam at `0.001`, one
local epoch, full participation, the fixed `{25,50,75,100,125,150,200}`
schedule, batch size `256`, one gradient-accumulation step, `FP32`, strict
determinism, and the `n_min = 100` eligibility threshold — is given
explicitly in the source architecture's resolved-implementation-decisions
record; none is invented.

## 13. Runtime configuration

`configs/runtime/scientific.yaml`:

```yaml
execution_mode: scientific
device_policy: cuda_required
determinism: strict
resource_budget:
  ram_budget_bytes: unresolved     # BLOCKED — no numeric ceiling given by either source
  vram_fraction: unresolved         # BLOCKED
worker_count: unresolved             # BLOCKED — no worker count given by either source
process_start_method: spawn           # locked rule for any CUDA-touching stage
log_interval_rounds: unresolved        # cosmetic only; still requires an explicit owner value
```

`process_start_method: spawn` is not fabricated: it follows directly from
the source architecture's fixed rule that any stage touching CUDA must use a
spawn context established before any CUDA call in the parent process, never
the global `set_start_method`. Every other field above is a genuine blocker
carried into `ScientificReadinessResult`
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`); a `DEVELOPMENT` or `SMOKE`
profile may carry these unresolved, but a `SCIENTIFIC` or `PRINT_GRADE` run
cannot schedule until a named authority supplies them.

## 14. Stress-test protocol configuration

`configs/protocols/fedprox_stress_test.yaml`, using only the source-locked
pre-registered proximal grid and otherwise matching every non-strategy
field of `core_federated_averaging.yaml` exactly (`SCI-07`):

```yaml
training_protocol:
  kind: federated_prox_training
  mu: 0.001   # or 0.01, or 0.1 — a separate resolved document per grid point,
              # never a caller-supplied value outside {0.001, 0.01, 0.1}
  local_epochs: 1
  participation: full
  personalization: none
autoencoder:
  hidden_dims: [80, 40, 20]
  activation: relu
  batch_normalization: false
optimizer: { type: adam, learning_rate: 0.001, scheduler: none }
precision: fp32
determinism: strict
checkpoint_schedule:
  rounds: [25, 50, 75, 100, 125, 150, 200]
  rounds_max: 200
checkpoint_selection:
  rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
  tie_break: earliest_scheduled_round
training_batch:
  micro_batch_size: 256
  gradient_accumulation_steps: 1
  effective_batch_size: 256
eligibility:
  minimum_calibration_sample_count: 100
```

`configs/experiments/fedprox_aggregation_stress_test.yaml` references this
document, never `core_federated_averaging.yaml`, so the two protocols
remain structurally distinct `TrainingProtocol` variants
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`) even though every field
below `training_protocol` is deliberately identical between them — the
identical fields are what make the two profiles "matched" in the roadmap's
sense, and the discriminated `kind` tag is what keeps the stress test
structurally outside the causal ladder (`SCI-07`).

## 15. Reusable reporting configuration

`configs/reporting/main_confirmatory_table.yaml`:

```yaml
schema_version: "1"
report_artifacts:
  - artifact_type: main_table
    table_type: confirmatory_interval
    columns:
      - { name: threshold_construction, unit: none, direction: none }
      - { name: cv_fpr, unit: ratio, direction: lower_is_better }
      - { name: delta, unit: ratio, direction: higher_is_better }
      - { name: bca_lower_bound, unit: ratio, direction: none }
      - { name: bca_upper_bound, unit: ratio, direction: none }
    ordering: deterministic_by_threshold_construction
    output_formats: [markdown, latex]
wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite]
```

Every column declares a unit and a metric direction explicitly
(`EVALUATION_REPORTING_AND_PROVENANCE.md §9.2`); a column with neither is
rejected at schema validation, because an undirected numeric column cannot
be safely rendered as "higher is better" or "lower is better" without an
explicit author decision.

## 16. Schema versioning and canonical serialization

Every configuration document under all five directories carries a
`schema_version` string. `config/compose.py` rejects an unsupported version
with a typed `ConfigurationError` naming the document and the unsupported
version; there is no automatic migration or backward-compatibility
translation between schema versions (`CFG-07`). The resolved-configuration
snapshot (§22) is serialized through the same canonical, order-stable
rendering used for stage fingerprints (§8): fields in a fixed schema order,
`Decimal`-backed identity fields through their canonical twelve-digit
representation, enum members through their stable serialized value. Two
independently produced snapshots of the same resolved definition are
therefore byte-identical, which is what makes fingerprint comparison and
snapshot diffing (`§22`) meaningful across independent runs.

## 17. Sweep representation

A sweep dimension is declared once, on the `ExperimentTemplate`, using only
the exact grids the roadmap specifies:

```yaml
# configs/experiments/threshold_quantile_sensitivity.yaml
slug: threshold_quantile_sensitivity
evidence_role: supportive
roadmap_reference: E-S2
dataset: datasets/natural_device_nbaiot.yaml
protocol: protocols/core_federated_averaging.yaml
sweep:
  axis: quantile
  values: [0.90, 0.95, 0.975, 0.99]
evaluations:
  - threshold: { policy: shared_threshold, construction: mean, quantile: "{sweep}" }
  - threshold: { policy: local_threshold, quantile: "{sweep}" }
  - threshold: { policy: cluster_threshold, aggregation: mean, cluster_count: 3, quantile: "{sweep}" }
```

The planner expands this template into four `ExperimentCell` values, one
per quantile, each with a `CellIdentity` derived from
`(experiment_slug, sweep_coordinate_hash)`; a collision between two
distinct resolved cells is a planning error, never a silent overwrite. Other
sweep grids follow the identical mechanism using their own source-given
values: alpha `{0.1, 0.3, 0.5, 1.0, 10.0, IID}`
(`controlled_heterogeneity_response`), lambda `{0, .25, .5, .75, 1}`
(`local_global_threshold_shrinkage`), calibration size
`{50, 100, 250, 500, 1000, 5000}` (`calibration_window_size_stability`),
and fixed-k `{2.0, 2.5, 3.0}` (`fixed_parameter_comparator_sensitivity`).

## 18. A second worked sweep: controlled heterogeneity response

`configs/experiments/controlled_heterogeneity_response.yaml`, using only
the roadmap's own Dirichlet grid and client count:

```yaml
slug: controlled_heterogeneity_response
evidence_role: supportive
roadmap_reference: E-S3
dataset: datasets/dirichlet_nbaiot.yaml
protocol: protocols/core_federated_averaging.yaml
sweep:
  axis: alpha
  values: [0.1, 0.3, 0.5, 1.0, 10.0, iid]
evaluations:
  - threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
  - threshold: { policy: local_threshold, quantile: 0.95 }
  - threshold: { policy: cluster_threshold, aggregation: mean, cluster_count: 3, quantile: 0.95 }
```

`configs/datasets/dirichlet_nbaiot.yaml`:

```yaml
dataset: n_baiot
client_construction:
  method: dirichlet_partitioned_clients
  client_count: 20
  alpha: "{sweep}"
  partition_seed: unresolved   # BLOCKED — see §6
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
```

Two templates sharing the identical `protocols/core_federated_averaging.yaml`
reference demonstrate that a new dataset evaluation setting never requires
a new protocol document: only the `dataset` reference and the sweep axis
differ (`SCIENTIFIC_FOUNDATION.md §8` extension test).

## 19. Blocked-value handling, worked

Attempting to schedule `anchor_reproduction.yaml` (§9) as a `scientific`
execution mode is rejected by `ScientificReadinessResult` before any
network, CUDA, or storage resource is touched, because
`evaluations[0].statistics.resample_count` and `seed_plan.experiment_seed`
are both marked `unresolved`. The rejection names both fields, cites the
blocker table entries in `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`, and
proposes no substitute value. The same document under `development` or
`smoke` execution mode is accepted, and every rendered output from that run
is marked non-citable, because `unresolved` fields are permitted only in
those two modes and never silently promoted to a citable result.

## 20. Validation failure examples

Removing `anchor_reference_interval.lower_bound` from §9 fails schema
validation with a missing-field error naming the field and the document; it
never activates a Python default, a Pydantic default, a loader fallback, or
a library default. Supplying `cluster_count` on a
`local_global_shrinkage_threshold` variant (§7) fails for the same reason in
the opposite direction. A `SCIENTIFIC`- or `PRINT_GRADE`-mode document
containing any field marked `unresolved` fails `ScientificReadinessResult`
validation and is blocked from scheduling; only `DEVELOPMENT` and `SMOKE`
profiles may carry an unresolved field, and never a field this table marks
scientific-identity-bearing without an explicit smoke-only exemption.

## 21. CLI configuration policy

The CLI selects a root experiment configuration document, an execution
mode, and a storage root when operationally appropriate. It never accepts a
scientific override such as `--set threshold.quantile=...`; a scientific
change occurs only through an edited, reviewed configuration document,
which produces a new resolved snapshot and new affected identities
(`CFG-09`).

## 22. Resolved configuration snapshot persistence

`config/compose.py` returns both the frozen `ExperimentDefinition` (or
`ExperimentTemplate`, pre-resolution) and a `ResolvedConfigurationSnapshot`
— the exact byte-stable rendering of every field that contributed to it, its
fingerprint, and the source-document identities it was built from. The
snapshot is persisted as a `RESOLVED_CONFIGURATION` artifact before
planning, so a later audit compares a stored result against the exact
configuration that produced it without re-parsing YAML. An unsupported
configuration schema version fails clearly at load time; no automatic
migration or backward-compatibility logic exists (`CFG-10`).
