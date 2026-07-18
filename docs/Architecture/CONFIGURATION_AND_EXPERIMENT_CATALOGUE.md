# CONFIGURATION_AND_EXPERIMENT_CATALOGUE

## Purpose

Define boundary ownership, composition, sweeps, registry, CLI, and Make.

## Authoritative for

Configuration schemas and resolution contracts.

## Not authoritative for

Scientific meaning, execution mechanics, or report rendering.

## 1. Configuration directories

```text
configs/
├── experiments/      # scientific experiment roots
├── dataset_audits/   # source-inspection and feasibility-audit roots
├── datasets/         # reusable data definitions
├── detectors/        # reusable detector definitions
├── runtime/          # named execution profiles
└── reporting/        # presentation definitions
```

Each directory has one boundary schema owner. Experiment and audit documents
are complete roots that reference, but never duplicate, their reusable
definitions. The `detectors/` directory owns detector definitions only;
evaluation and threshold definitions are experiment-owned.

## 2. Schema ownership

| Directory | Owns | Schema module |
|---|---|---|
| `experiments/` | scientific identity, evidence role/tier, run requirement, dataset/detector/runtime/reporting references, evaluations, analyses, seed cohort, prerequisites, sweeps/bindings, component evidence/placement | `config/schemas/experiment.py` |
| `dataset_audits/` | source inspection, feasibility audit, source reference, audit rules, runtime/reporting references | `config/schemas/dataset_audit.py` |
| `datasets/` | dataset identity/version, source, client/partition/split semantics, scientific preprocessing | `config/schemas/data.py` |
| `detectors/` | architecture, reconstruction objective/loss, training, optimizer/scheduler, participation, checkpoint production, training/scoring batches, precision, deterministic computation | `config/schemas/detector.py` |
| `runtime/` | device/CUDA, RAM/VRAM/disk/worker limits, concurrency, process policies, chunks/prefetch, timeouts, telemetry/logging | `config/schemas/runtime.py` |
| `reporting/` | presentation, formats, ordering, placement, and display labels | `config/schemas/reporting.py` |

A field absent from its owner fails boundary validation. Dataset audits never
carry detector, threshold, seed, evidence-role, or claim-tier fields.
Reporting never owns a scientific setting or a runtime artifact reference.

## 3. Canonical execution lifecycle

Configuration resolution is pre-pipeline composition. Its required order is:

```text
load root boundary document
  → load referenced boundary documents
    → validate each document schema
      → resolve typed references
        → validate typed sweep bindings
          → expand sweep coordinates
            → resolve one complete configuration per coordinate
              → construct frozen resolved domain objects
                → run cross-document scientific validation
                  → create one canonical resolved snapshot per resolved cell
                    → return the resolution result to the application layer
                      → persist snapshots through an application port
                        → run readiness and prerequisite checks
                          → create the execution plan
```

`config/compose.py` performs parsing, reference resolution, sweep expansion,
mapping, and validation only. It neither persists artifacts, imports
infrastructure, creates execution resources, nor runs scientific computation.
The application use case
persists snapshots through `ArtifactStore` after receiving:

```text
ConfigurationResolutionResult
├── authored_root_snapshot
├── resolved_runs
├── resolved_run_snapshots
└── boundary_blockers
```

Resolved runs are complete frozen domain objects. Draft boundary blockers,
operational profile requirements, source-inspection results, feasibility
decisions, and optional telemetry preferences are distinct states; none is a
generic domain sentinel.

## 4. Scientific authorization

Authorization is enforced by construction validators on the closed
discriminated unions and by cross-field validators at resolution time —
never by a separate "authorized profile" object duplicating the resolved
definition's fields (`SCIENTIFIC_FOUNDATION.md §8`). Resolution rejects, for
every affected document:

- `evidence_role = CONFIRMATORY` paired with a dataset setting other than
  `natural_device_evaluation`, a threshold pair other than
  `{SharedThreshold(MEAN), LocalThreshold}`, a `seed_cohort.paired_seed_count`
  other than ten, a primary metric other than `CV_FPR`, or `tier ≠ TIER_1`.
- `evidence_role = ANCHOR` with a `seed_cohort.paired_seed_count` other than
  five, or without an `AnchorEquivalenceAnalysis` owning the reference
  interval.
- A `BenignCalibrationSplit` reachable from any field capable of carrying an
  attack label.
- `training_protocol = FederatedAveragingTraining` or
  `FederatedProxTraining` with a non-`NONE` personalization strategy on any
  experiment whose `evidence_role` is not the one authorized
  `model_personalization_absorption_test` slug.
- `TrainingProtocol.FederatedProxTraining.mu` equal to zero, equal to a
  FedAvg-equivalent value, or absent from the pre-registered grid
  `{0.001, 0.01, 0.1}`.
- Any incomplete boundary document reaching resolve, plan, or run.
- Any experiment whose `identity.slug` matches a rejected or out-of-scope
  entry (`SCIENTIFIC_FOUNDATION.md §7.6`).
- A publication regime label present in authored YAML; it is derived only
  by `derive_publication_regime(data)` for reporting.
- An `effective_batch_size`, `rounds_max`, `batch_normalization`, or
  artifact `namespace` field present in an authored YAML document — each is
  computed post-resolution (`effective_batch_size` and `rounds_max` by the
  pure functions in `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`;
  `namespace` by `derive_artifact_namespace`, `§3.4` of the same file); the
  detector schema has no `batch_normalization` field at all, because the
  encoder architecture structurally forbids it (`SCI-19`) and an
  always-`false` boolean would only invite a future, silently-ignored
  `true` (`§11` below).
- A `requires_passed` free-text field — prerequisites are authored only as
  the typed `prerequisites` list (`§9` below,
  `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`).

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
| `run_requirement` (`MANDATORY`/`OPTIONAL`/`SUPPRESSED`) | No (does not affect a computed value) | No | Yes | Yes (governs whether a result is main-paper or supplement) | Yes |
| publication regime | No — reporting projection only | No | Yes | Yes | No — derived by `derive_publication_regime` |
| Feature schema | Yes | No | Yes | No | Runtime-captured (source-inspected), never authored |
| Client construction, partition seed | Yes | No | Yes | No | Yes |
| Split boundaries (chronological fraction, timestamp field) | Yes | No | Yes | No | Yes |
| Preprocessing (strategy, scope) | Yes | No | Yes | No | Yes |
| Calibration-window selection (`§12` of `DOMAIN_AND_APPLICATION_ARCHITECTURE.md`) | Yes (when populated) | No | Yes | Yes | Yes, only for `calibration_window_size_stability` cells |
| Detector architecture (hidden dims, activation) | Yes | No | Yes | No | Yes |
| Optimizer, learning rate | Yes | No | Yes | No | Yes |
| Training rounds (checkpoint schedule) | Yes | No | Yes | No | Yes |
| `rounds_max` | No — derived from the checkpoint schedule | No | Yes | No | No — computed, rejected if authored |
| Local epochs, participation | Yes | No | Yes | No | Yes |
| Micro-batch size, gradient accumulation | Yes | No | Yes | No | Yes |
| `effective_batch_size` | No — derived (`micro_batch_size × gradient_accumulation_steps`) | No | Yes | No | No — computed, rejected if authored |
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
| `seed_cohort.paired_seed_count`, `seed_cohort.derivation` | Yes | No | Yes | No | Yes |
| `analyses[*].primary_procedure` / `secondary_procedures` | Yes | No | Yes | Yes | Yes |
| `analyses[*].primary_procedure` / `secondary_procedures` | Yes | No | Yes | Yes | Yes; bootstrap resample count remains a blocker until pre-registered |
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
  # A complete document supplies partition_seed. Until its authority is
  # recorded, this draft fails validation and cannot resolve.
```

## 8. Fingerprinting rules

A `StageIdentity` and `ArtifactKey` fingerprint are blake3 digests of a
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

`configs/experiments/anchor_reproduction.yaml`. The fragment below preserves
the source-given fields and illustrates where draft validation reports a
boundary blocker. A draft with either commented requirement cannot resolve,
plan, or run; no resolved object carries a placeholder value.

```yaml
schema_version: 1
slug: anchor_reproduction
display_name: Anchor Reproduction
evidence_role: anchor
run_requirement: mandatory
dataset: datasets/natural_device_nbaiot.yaml
detector: detectors/core_federated_averaging.yaml
evaluations:
  - label: shared_mean
    threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
  - label: local
    threshold: { policy: local_threshold, quantile: 0.95 }
analyses:
  - kind: paired_threshold_analysis
    first_evaluation: shared_mean
    second_evaluation: local
    primary_metric: cv_fpr
    delta_orientation: shared_minus_local
    primary_procedure:
      method: bca_bootstrap
      confidence_level: 0.95
      # BLOCKED: bootstrap resample count must be supplied by statistical authority.
    secondary_procedures: []
  - kind: anchor_equivalence_analysis
    confirmatory_analysis_label: paired_threshold_analysis   # the entry above
    reference_interval:
      metric: cv_fpr_delta
      confidence_level: 0.95
      lower_bound: 0.647
      upper_bound: 0.769
seed_cohort:
  paired_seed_count: 5
  derivation: deterministic_from_experiment_seed
  # BLOCKED: experiment_seed must be supplied before this draft is resolved.
prerequisites: []
operations:
  execution: runtime/scientific.yaml
  reporting: reporting/anchor_reporting.yaml
```

Every anchor-identity value that the source documents actually supply —
evidence role, dataset, both threshold constructions, the quantile `0.95`,
the five-seed count, the confidence level `0.95`, and the reference interval
`[0.647, 0.769]` — is explicit here, none defaulted in Python. The two
fields the source documents do not supply (`resample_count`,
`experiment_seed`) remain boundary blockers until an authority supplies
them; there is no `anchor: true` switch that bypasses this requirement. The
resolved domain object owns the reference interval exactly once, in
`AnchorEquivalenceAnalysis.reference_interval`.

### 9.1 No dynamic client-construction fallback

An `external_device_validation`-family experiment's `client_construction`
is always a fully resolved, explicit `ExternalDeviceOrGroupClients`
document — `granularity: device` or `granularity: group`, never a
placeholder — because it is authored only after the standalone feasibility
audit closes (`SCIENTIFIC_FOUNDATION.md §5.1`). No scientific experiment's
configuration ever contains a runtime selection rule choosing between
device clients, group clients, or a pseudo-client fallback; that would
reintroduce the circular dependency this package removes.

## 10. Confirmatory experiment configuration

`configs/experiments/confirmatory_threshold_scope_effect.yaml`:

```yaml
schema_version: 1
slug: confirmatory_threshold_scope_effect
display_name: Confirmatory Threshold-Scope Effect
evidence_role: confirmatory
run_requirement: mandatory
tier: tier_1
roadmap_reference: E-C1
dataset: datasets/natural_device_nbaiot.yaml
detector: detectors/core_federated_averaging.yaml
evaluations:
  - label: shared_mean
    threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
  - label: local
    threshold: { policy: local_threshold, quantile: 0.95 }
analyses:
  - kind: paired_threshold_analysis
    first_evaluation: shared_mean
    second_evaluation: local
    primary_metric: cv_fpr
    delta_orientation: shared_minus_local
    primary_procedure:
      method: bca_bootstrap
      confidence_level: 0.95
      # BLOCKED: bootstrap resample count must be supplied by statistical authority.
    secondary_procedures:
      - { method: wilcoxon_signed_rank }
      - { method: cliffs_delta }
seed_cohort:
  paired_seed_count: 10
  derivation: deterministic_from_experiment_seed
  # BLOCKED: experiment_seed must be supplied before this draft is resolved.
prerequisites:
  - requires: anchor_reproduction
    required_outcome: anchor_equivalence_passed
operations:
  execution: runtime/scientific.yaml
  reporting: reporting/main_confirmatory_table.yaml
```

`prerequisites` is a list of typed `ExperimentPrerequisite` values, each a
reference to another document's `identity.slug` plus the exact outcome
required of it, resolved by the planner against the `AnchorEquivalenceGate`
result — never a free-text dependency string (`CFG-08`).

## 11. Reusable dataset configuration

`configs/datasets/natural_device_nbaiot.yaml`, using only the source-given
physical-device client count for N-BaIoT:

```yaml
schema_version: 1
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
  chunk_profile: { chunk_row_count: 50000 }
```

## 12. Reusable detector configuration

`configs/detectors/core_federated_averaging.yaml`, using only the
source-locked implementation decisions:

```yaml
schema_version: 1
training_protocol:
  kind: federated_averaging_training
  local_epochs: 1
  participation: full
  personalization: none
autoencoder:
  hidden_dims: [80, 40, 20]
  activation: relu
optimizer:
  optimizer_type: adam
  learning_rate: 0.001
  scheduler: null
precision: fp32
determinism: strict
checkpoint_schedule:
  rounds: [25, 50, 75, 100, 125, 150, 200]
checkpoint_selection:
  rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
  tie_break: earliest_scheduled_round
training_batch:
  micro_batch_size: 256
  gradient_accumulation_steps: 1
eligibility:
  minimum_calibration_sample_count: 100
```

Every value above — the encoder widths `(80, 40, 20)`, no batch
normalization (structurally absent from the schema, `SCI-19`, never an
authored boolean), MSE-implying reconstruction objective, Adam at `0.001`,
one local epoch, full participation, the fixed
`{25,50,75,100,125,150,200}` schedule, batch size `256`, one
gradient-accumulation step, `FP32`, strict determinism, and the
`n_min = 100` eligibility threshold — is given explicitly in the source
architecture's resolved-implementation-decisions record; none is invented.
`rounds_max` (`200`) and `effective_batch_size` (`256`) are never authored
here — both are pure derivations (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md
§3.2`) computed after this document resolves.

## 13. Runtime configuration

`configs/runtime/scientific.yaml` is shown as a non-resolvable draft until
the authority supplies its operational limits:

```yaml
schema_version: 1
execution_mode: scientific
device_policy: cuda_required
determinism: strict
resource_budget:
  # BLOCKED: concrete RAM and VRAM limits are required here.
concurrency:
  # BLOCKED: concrete worker count is required here.
  training_concurrency: 1
  scoring_concurrency: 1
process_start_method: spawn           # locked rule for any CUDA-touching stage
# BLOCKED: log_interval_rounds requires its explicit operational owner value.
```

`process_start_method: spawn` is not fabricated: it follows directly from
the source architecture's fixed rule that any stage touching CUDA must use a
spawn context established before any CUDA call in the parent process, never
the global `set_start_method`. The commented requirements are genuine
boundary blockers reported before a domain value is constructed. Every
execution mode, including development and smoke, requires an explicit,
complete runtime profile; scientific and print-grade modes additionally
require the roadmap's scientific evidence.

## 14. Stress-test detector configuration

`configs/detectors/fedprox_stress_test.yaml`, using only the source-locked
pre-registered proximal grid and otherwise matching every non-strategy
field of `core_federated_averaging.yaml` exactly (`SCI-07`):

```yaml
schema_version: 1
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
optimizer:
  optimizer_type: adam
  learning_rate: 0.001
  scheduler: null
precision: fp32
determinism: strict
checkpoint_schedule:
  rounds: [25, 50, 75, 100, 125, 150, 200]
checkpoint_selection:
  rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
  tie_break: earliest_scheduled_round
training_batch:
  micro_batch_size: 256
  gradient_accumulation_steps: 1
eligibility:
  minimum_calibration_sample_count: 100
```

`configs/experiments/fedprox_aggregation_stress_test.yaml` references this
document, never `core_federated_averaging.yaml`, so the two detectors
remain structurally distinct `TrainingProtocol` variants
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`) even though every field
below `training_protocol` is deliberately identical between them — the
identical fields are what make the two profiles "matched" in the roadmap's
sense, and the discriminated `kind` tag is what keeps the stress test
structurally outside the causal ladder (`SCI-07`).

## 15. Reusable reporting configuration

`configs/reporting/main_confirmatory_table.yaml`:

```yaml
schema_version: 1
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

Every configuration document under all five directories carries an integer
`schema_version` field. `config/compose.py` rejects an unsupported version
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

A sweep dimension is declared once, on the `experiments/` boundary schema
only — never as a domain-level `ExperimentTemplate`
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`) — using only the exact grids
the roadmap specifies:

```yaml
# Non-executable fragment: configs/experiments/threshold_quantile_sensitivity.yaml
schema_version: 1
slug: threshold_quantile_sensitivity
evidence_role: supportive
roadmap_reference: E-S2
dataset: datasets/natural_device_nbaiot.yaml
detector: detectors/core_federated_averaging.yaml
sweep:
  parameters:
    threshold_quantile:
      values: [0.90, 0.95, 0.975, 0.99]
evaluations:
  - label: shared_mean
    threshold:
      policy: shared_threshold
      construction: mean
      quantile: { from_sweep: threshold_quantile }
  - label: local
    threshold: { policy: local_threshold, quantile: { from_sweep: threshold_quantile } }
  - label: cluster_k3
    threshold: { policy: cluster_threshold, aggregation: mean, cluster_count: 3, quantile: { from_sweep: threshold_quantile } }
seed_cohort:
  paired_seed_count: 10
  derivation: deterministic_from_experiment_seed
  # Exact pre-registered seed cohort is required before this fragment becomes executable.
prerequisites:
  - requires: anchor_reproduction
    required_outcome: anchor_equivalence_passed
```

The composer validates a binding's declared parameter and value-object type,
then expands one complete resolved run and canonical snapshot per coordinate.
Bindings are consumed in composition and never enter the domain. Other sweep
grids follow the identical mechanism
using their own source-given values: alpha `{0.1, 0.3, 0.5, 1.0, 10.0, IID}`
(`controlled_heterogeneity_response`), lambda `{0, .25, .5, .75, 1}`
(`local_global_threshold_shrinkage`), calibration size
`{50, 100, 250, 500, 1000, 5000}` (`calibration_window_size_stability`, each
point additionally resolving a `CalibrationSubsetDefinition`), and fixed-k
`{2.0, 2.5, 3.0}` (the `federated_summary_comparator`'s optional
supplementary evaluation).

## 18. A second worked sweep: controlled heterogeneity response

Non-executable fragment — `configs/experiments/controlled_heterogeneity_response.yaml`, using only
the roadmap's own Dirichlet grid and client count:

```yaml
schema_version: 1
slug: controlled_heterogeneity_response
evidence_role: supportive
roadmap_reference: E-S3
dataset: datasets/dirichlet_nbaiot.yaml
detector: detectors/core_federated_averaging.yaml
sweep:
  parameters:
    dirichlet_alpha:
      values: [0.1, 0.3, 0.5, 1.0, 10.0, iid]
evaluations:
  - label: shared_mean
    threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
  - label: local
    threshold: { policy: local_threshold, quantile: 0.95 }
  - label: cluster_k3
    threshold: { policy: cluster_threshold, aggregation: mean, cluster_count: 3, quantile: 0.95 }
analyses:
  - label: heterogeneity_benefit_association
    kind: metric_association_analysis
    predictor_metric: pairwise_js_divergence
    outcome_metric: cv_fpr_delta
    grouping_dimension: dirichlet_alpha
    primary_procedure: { method: spearman_correlation }
    secondary_procedures: [{ method: linear_regression }]
seed_cohort:
  paired_seed_count: 10
  derivation: deterministic_from_experiment_seed
  # Exact pre-registered seed cohort is required before this fragment becomes executable.
prerequisites:
  - requires: anchor_reproduction
    required_outcome: anchor_equivalence_passed
```

Non-executable fragment — `configs/datasets/dirichlet_nbaiot.yaml`:

```yaml
schema_version: 1
dataset: n_baiot
client_construction:
  method: dirichlet_partitioned_clients
  client_count: 20
  alpha: { from_sweep: dirichlet_alpha }
  # The required partition seed is pre-registered before resolution.
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
```

Two templates sharing the identical `detectors/core_federated_averaging.yaml`
reference demonstrate that a new dataset evaluation setting never requires
a new detector document: only the `dataset` reference and the sweep axis
differ (`SCIENTIFIC_FOUNDATION.md §8` extension test).

## 19. Blocked-value handling, worked

Attempting to schedule `anchor_reproduction.yaml` (§9) as a `scientific`
execution mode is rejected by `ScientificReadinessResult` before any
network, CUDA, or storage resource is touched, because
`analyses[0].primary_procedure.resample_count` and
`seed_cohort.experiment_seed` are absent from the draft. The rejection names
both fields, cites the blocker table entries in
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`, and proposes no substitute
value. The same draft is rejected in development and smoke as well: those
modes use complete explicit reduced values and are non-citable because of
execution mode, not incomplete configuration.

## 20. Validation failure examples

Removing `AnchorEquivalenceAnalysis.reference_interval.lower_bound` from §9
fails schema validation with a missing-field error naming the field and the document; it
never activates a Python default, a Pydantic default, a loader fallback, or
a library default. Supplying `cluster_count` on a
`local_global_shrinkage_threshold` variant (§7) fails for the same reason in
the opposite direction. Supplying `effective_batch_size` or `rounds_max` on
a `detectors/` document (§12) fails because the schema owns no such field —
both are computed after resolution, never accepted as input. A
`SCIENTIFIC`- or `PRINT_GRADE`-mode document that is incomplete fails
boundary validation before `ScientificReadinessResult`;
no execution profile may carry a placeholder field.

## 21. CLI contract

One canonical CLI, `datp-core experiment <action>`, with exactly seven
actions:

```bash
datp-core experiment list
datp-core experiment validate --config <slug-or-path>
datp-core experiment resolve --config <slug-or-path>
datp-core experiment plan --config <slug-or-path>
datp-core experiment run --config <slug-or-path>
datp-core experiment status --config <slug-or-path>
datp-core experiment report --config <slug-or-path>
```

`--config` accepts either a YAML path or a registered experiment slug
(`datp-core experiment list` enumerates every registered slug and its
document path). The CLI may additionally accept only a storage-root
override where operationally required, and dry-run, verbosity,
confirmation, and logging controls that do not affect scientific output.

The CLI never accepts a scientific override such as `--set
threshold.quantile=...`, `--seed`, `--rounds`, `--batch-size`, or any flag
that would set, adjust, or replace a dataset, client construction, split,
preprocessing, training protocol, model architecture, optimizer, learning
rate, round or checkpoint schedule, batch size, threshold policy or
quantile, seed cohort, runtime execution mode, statistical procedure,
reporting content, or any other scientific, identity-bearing, or
output-affecting value. Dataset audits expose the identical lifecycle:

```bash
datp-core dataset-audit list
datp-core dataset-audit validate --config <slug-or-path>
datp-core dataset-audit resolve --config <slug-or-path>
datp-core dataset-audit plan --config <slug-or-path>
datp-core dataset-audit run --config <slug-or-path>
datp-core dataset-audit status --config <slug-or-path>
datp-core dataset-audit report --config <slug-or-path>
```

A scientific change occurs only through an edited,
reviewed configuration document, which produces a new resolved snapshot and
new affected identities (`CFG-09`).

## 22. Resolved configuration snapshot persistence

`config/compose.py` returns `ConfigurationResolutionResult`: the authored
root snapshot, complete frozen `RunDefinition` values, canonical resolved
run snapshots, and typed boundary blockers. Scientific sweep coordinates are
represented by `ScientificExperimentCell` within the resolved run result.
The application—not the composer—persists each `RESOLVED_CONFIGURATION`
artifact before planning, so a later audit compares a stored result against
the exact configuration that produced it without re-parsing YAML. An
unsupported configuration schema version fails clearly at load time; no
automatic migration or backward-compatibility logic exists (`CFG-10`).

## 23. Zero-input Make targets

Make targets are convenience aliases around the CLI (`§21`). They contain
no user-supplied parameters and no `EXPERIMENT=...`, `CONFIG=...`,
`MODE=...`, or equivalent input. Each target identifies exactly one action
and one registered experiment configuration; a target whose referenced
configuration document does not exist fails, it never silently no-ops.

### 23.1 Experiment-family targets

Every regularly executed root experiment exposes only the actions
meaningful for it:

| Family | Registered configuration | Actions exposed |
|---|---|---|
| `anchor` | `configs/experiments/anchor_reproduction.yaml` | validate, resolve, plan, run, status, report |
| `confirmatory` | `configs/experiments/confirmatory_threshold_scope_effect.yaml` | validate, resolve, plan, run, status, report |
| `shared-threshold-sensitivity` | `configs/experiments/shared_threshold_construction_sensitivity.yaml` | validate, plan, run, status, report |
| `quantile-sensitivity` | `configs/experiments/threshold_quantile_sensitivity.yaml` | validate, plan, run, status, report |
| `controlled-heterogeneity` | `configs/experiments/controlled_heterogeneity_response.yaml` | validate, plan, run, status, report |
| `cluster-mechanism` | `configs/experiments/cluster_mechanism.yaml` | validate, plan, run, status, report |
| `calibration-window` | `configs/experiments/calibration_window_size_stability.yaml` | validate, plan, run, status, report |
| `threshold-shrinkage` | `configs/experiments/local_global_threshold_shrinkage.yaml` | validate, plan, run, status, report |
| `conformal-threshold` | `configs/experiments/conformal_local_threshold_coverage.yaml` | validate, plan, run, status, report |
| `external-validation` | `configs/experiments/external_device_dataset_validation.yaml` | plan, run, status, report (feasibility-gated; `§9.1`) |
| `fedprox-stress-test` | `configs/experiments/fedprox_aggregation_stress_test.yaml` | plan, run, status, report |
| `personalization-stress-test` | `configs/experiments/model_personalization_absorption_test.yaml` | plan, run, status, report |
| `federated-summary-comparator` | `configs/experiments/federated_summary_comparator.yaml` | validate, plan, run, status, report |
| `temporal-recalibration` | `configs/experiments/chronological_recalibration_evaluation.yaml` | plan, run, status, report (feasibility- and timestamp-gated) |
| `centralized-reference` | `configs/experiments/centralized_pooled_reference.yaml` | validate, plan, run, status, report |
| `pseudo-client-boundary` | `configs/experiments/file_pseudo_client_applicability_boundary.yaml` | validate, plan, run, status, report |

Example:

```make
.PHONY: anchor-validate anchor-resolve anchor-plan anchor-run anchor-status anchor-report

anchor-validate:
	datp-core experiment validate \
		--config configs/experiments/anchor_reproduction.yaml

anchor-resolve:
	datp-core experiment resolve \
		--config configs/experiments/anchor_reproduction.yaml

anchor-plan:
	datp-core experiment plan \
		--config configs/experiments/anchor_reproduction.yaml

anchor-run:
	datp-core experiment run \
		--config configs/experiments/anchor_reproduction.yaml

anchor-status:
	datp-core experiment status \
		--config configs/experiments/anchor_reproduction.yaml

anchor-report:
	datp-core experiment report \
		--config configs/experiments/anchor_reproduction.yaml

.PHONY: confirmatory-validate confirmatory-plan confirmatory-run confirmatory-status confirmatory-report

confirmatory-validate:
	datp-core experiment validate \
		--config configs/experiments/confirmatory_threshold_scope_effect.yaml

confirmatory-plan:
	datp-core experiment plan \
		--config configs/experiments/confirmatory_threshold_scope_effect.yaml

confirmatory-run:
	datp-core experiment run \
		--config configs/experiments/confirmatory_threshold_scope_effect.yaml

confirmatory-status:
	datp-core experiment status \
		--config configs/experiments/confirmatory_threshold_scope_effect.yaml

confirmatory-report:
	datp-core experiment report \
		--config configs/experiments/confirmatory_threshold_scope_effect.yaml

.PHONY: external-validation-plan external-validation-run

external-validation-plan:
	datp-core experiment plan \
		--config configs/experiments/external_device_dataset_validation.yaml

external-validation-run:
	datp-core experiment run \
		--config configs/experiments/external_device_dataset_validation.yaml
```

Every other family in `§23.1` follows the identical two-line-per-action
shape; only the target prefix and the referenced configuration path change.
Target names are explicit, readable without opening the Makefile, and free
of unexplained abbreviations (`cluster-mechanism-plan`,
`personalization-stress-test-run`,
`temporal-recalibration-report` — never `c1`, `run-b`, or `exp-cl`).
Generic parameterized targets (`make run EXPERIMENT=anchor`, `make plan
CONFIG=...`, `make experiment ACTION=run NAME=...`) are never defined.

### 23.2 Global targets

```make
.PHONY: help experiments validate-all plan-all-mandatory status-all report-all-completed mandatory-run

help:
	@echo "Targets:"
	@echo "  anchor-{validate,resolve,plan,run,status,report}"
	@echo "  confirmatory-{validate,resolve,plan,run,status,report}"
	@echo "  <family>-{validate,plan,run,status,report} for every family in §23.1"
	@echo "  experiments            list every registered experiment (datp-core experiment list)"
	@echo "  validate-all           validate every registered experiment configuration"
	@echo "  plan-all-mandatory     plan every run_requirement=MANDATORY experiment"
	@echo "  status-all             report status for every registered experiment"
	@echo "  report-all-completed   render reports for every completed experiment"
	@echo "  mandatory-run          run the fixed, explicitly listed mandatory sequence below"

experiments:
	datp-core experiment list

validate-all:
	datp-core experiment validate --config configs/experiments/anchor_reproduction.yaml
	datp-core experiment validate --config configs/experiments/confirmatory_threshold_scope_effect.yaml
	# one explicit line per registered configuration; never a directory glob

plan-all-mandatory:
	datp-core experiment plan --config configs/experiments/anchor_reproduction.yaml
	datp-core experiment plan --config configs/experiments/confirmatory_threshold_scope_effect.yaml
	# one explicit line per MANDATORY registered configuration

status-all:
	datp-core experiment status --config configs/experiments/anchor_reproduction.yaml
	datp-core experiment status --config configs/experiments/confirmatory_threshold_scope_effect.yaml
	# one explicit line per registered configuration

report-all-completed:
	datp-core experiment report --config configs/experiments/anchor_reproduction.yaml
	datp-core experiment report --config configs/experiments/confirmatory_threshold_scope_effect.yaml
	# one explicit line per completed registered configuration

mandatory-run:
	datp-core experiment run --mandatory
```

Mandatory orchestration and prerequisite enforcement belong to the
application. Make never encodes dependencies, so parallel Make execution
cannot bypass the typed `AnchorEquivalenceGate`.
