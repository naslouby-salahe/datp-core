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
├── datasets/
│   ├── nbaiot.yaml
│   ├── ciciot2023.yaml
│   └── edge_iiotset.yaml
│
├── models/
│   └── autoencoder.yaml
│
├── experiments/
│   ├── anchor.yaml
│   ├── threshold_scope.yaml
│   ├── heterogeneity.yaml
│   ├── calibration_mechanisms.yaml
│   ├── external_validation.yaml
│   ├── training_stress_tests.yaml
│   └── references_and_boundaries.yaml
│
└── execution.yaml
```

Four boundary owners, not six: `datasets/` owns one document per real dataset
(source, feasibility, client-construction setups, splits, preprocessing,
eligibility); `models/` owns one document per model family (architecture,
objective, optimizer, checkpointing, and every named training profile that
shares that family); `experiments/` groups scientifically related
experiments into family documents, each experiment independently
addressable by a semantic slug; `execution.yaml` owns every named execution
profile in one file. `PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md §3`
reproduces this identical tree with per-file schema-module ownership.

There is no `dataset_audits/`, `data_sources/`, `detectors/`, `protocols/`,
`runtime/`, or `reporting/` directory anywhere in this design. Their prior
responsibilities move to a single owner each (`§1.1` below); none is
duplicated, and none survives as an empty or redirect path.

### 1.1 Where prior responsibilities moved

| Prior root | Prior responsibility | New owner |
|---|---|---|
| `dataset_audits/` | source inspection, feasibility audit | the owning dataset's own `audits` list (`§2.1`) — a typed, executable capability of the dataset it inspects, not a parallel hierarchy |
| `detectors/` | architecture, training protocol, checkpointing | `models/autoencoder.yaml`'s architecture fields plus its named `training_profiles` (`§2.2`) |
| `protocols/` | (already retired before this revision) | never existed in this design; confirmed absent |
| `runtime/` | named execution profiles | `execution.yaml`'s named profiles (`§2.4`) |
| `reporting/` | table/figure/wording presentation | each experiment entry's own inline `report` field (`§2.3`); no experiment-specific presentation rule lives outside the experiment that produces it |

## 2. Schema ownership

| File | Owns | Schema module |
|---|---|---|
| `datasets/<dataset>.yaml` | dataset identity/version, source location and integrity, raw/processed source distinction where genuinely required, source-readiness and feasibility audits, feature-schema discovery, client-identity availability, timestamp semantics, named client-construction setups, split definitions, preprocessing, dataset-specific eligibility rules, required readiness evidence and blockers | `config/schemas/data.py` |
| `models/autoencoder.yaml` | architecture, reconstruction objective, optimizer/scheduler, checkpoint production and selection, scientific training/scoring batches, precision, determinism, and every named `training_profile` (federated averaging, federated proximal, centralized pooled, the authorized personalization comparator) | `config/schemas/model.py` |
| `experiments/<family>.yaml` | one family's scientific identity, evidence role/tier, run requirement, dataset+setup and model+training-profile references, evaluations, analyses, seed cohort, prerequisites, sweeps/bindings, inline report, per-experiment scientific blockers — one entry per experiment, every entry independently resolvable | `config/schemas/experiment.py` |
| `execution.yaml` | every named execution profile: CUDA/CPU requirement, RAM/VRAM/disk/worker/concurrency limits, process-start policy, chunking/prefetch, timeouts, logging/telemetry | `config/schemas/execution.py` |

A field absent from its owner fails boundary validation. A dataset document
never carries a model, threshold, seed, evidence-role, or claim-tier field;
`execution.yaml` never carries a scientific value (architecture, threshold,
seed, dataset, metric, or analysis); `models/autoencoder.yaml` never carries
a dataset, threshold, or execution field. Presentation (table/figure
columns, units, direction, ordering, missing-value rendering) lives only
inside the experiment entry that produces it — no reporting schema module
exists as a fifth owner, because no genuinely global rendering default
survived consolidation (`§15`).

### 2.1 Dataset-owned audits

Each dataset document carries an `audits` list: zero or more named,
typed inspection/feasibility checks, each producing a persisted
`FEASIBILITY_RESULT`/`SOURCE_INSPECTION` artifact exactly as the retired
`dataset_audits/` root did (`PIPELINE_EXECUTION_AND_ARTIFACTS.md §2`). An
audit entry carries only audit fields — no detector, threshold, seed,
evidence-role, or claim-tier field reaches it (`ARCH-01`). A scientific
experiment never re-answers a question its dataset's own audit already
closed; it cites the audit's result by `ArtifactRef` as provenance only
(`SCIENTIFIC_FOUNDATION.md §5.1`).

### 2.2 Model-owned training profiles

`models/autoencoder.yaml` is the one model family this design authorizes. It
owns architecture, objective, optimizer, checkpointing, and precision once,
and a `training_profiles` list of named variants that share every one of
those fields and differ only in their aggregation/personalization strategy.
Federated averaging, federated proximal aggregation, centralized pooled
training, and the one authorized model-personalization comparator are four
named profiles of the same model family, never four unrelated detector
files (`§7` below).

### 2.3 Experiment-owned reporting

An experiment entry's `operations.report` field is an inline
`ReportDefinition` (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §16.7`,
`EVALUATION_REPORTING_AND_PROVENANCE.md §9.2`) — table type or figure type,
columns/series with unit and direction, ordering, missing-value policy, and
wording outcomes — authored directly where the experiment that produces it
is authored. No separate presentation file is introduced unless a genuinely
global rendering default is later proven necessary across every experiment;
none has been (`§15`).

### 2.4 Execution-owned profiles

`execution.yaml` carries a `profiles` map keyed by profile name
(`scientific`, `print_grade`, `development`, `smoke`, `dataset_audit`,
`test_smoke`, `§13`). An experiment references exactly one profile by name
(`operations.execution: scientific`); it never inlines execution fields and
never authors a CUDA/RAM/VRAM/worker value itself.

## 3. Canonical execution lifecycle

Configuration resolution is pre-pipeline composition. Its required order is:

```text
load root boundary document
  → load referenced boundary documents (dataset, model, execution)
    → validate each document schema
      → resolve typed references (dataset+setup, model+training_profile, execution profile)
        → validate typed sweep bindings
          → expand sweep coordinates
            → expand each experiment-family document into its independent experiment entries
              → resolve one complete configuration per (experiment, coordinate)
                → construct frozen resolved domain objects
                  → run cross-document scientific validation
                    → create one canonical resolved snapshot per resolved cell
                      → return the resolution result to the application layer
                        → persist snapshots through an application port
                          → run readiness and prerequisite checks
                            → create the execution plan
```

`config/compose.py` performs parsing, reference resolution, family-document
expansion, sweep expansion, mapping, and validation only. It neither
persists artifacts, imports infrastructure, creates execution resources, nor
runs scientific computation. Expanding a family document into its
independent experiment entries is the same kind of pure, boundary-only
expansion sweep expansion already performs (`§17`); no new composition
mechanism is introduced, and no expanded entry ever depends on a sibling
entry's resolution. The application use case persists snapshots through
`ArtifactStore` after receiving:

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
  `nbaiot`'s `natural_devices` setup, a threshold pair other than
  `{SharedThreshold(MEAN), LocalThreshold}`, a `seed_cohort.paired_seed_count`
  other than ten, a primary metric other than `CV_FPR`, or `tier ≠ TIER_1`.
- `evidence_role = ANCHOR` with a `seed_cohort.paired_seed_count` other than
  five, or without an `AnchorEquivalenceAnalysis` owning the reference
  interval.
- A `BenignCalibrationSplit` reachable from any field capable of carrying an
  attack label.
- `training_profile = federated_averaging` or `federated_proximal` with a
  non-`NONE` personalization strategy on any experiment other than the one
  authorized `model_personalization_absorption_test` slug (which selects the
  dedicated `federated_averaging_personalized` profile, `§7`).
- `federated_proximal.mu` equal to zero, equal to a FedAvg-equivalent value,
  or absent from the pre-registered grid `{0.001, 0.01, 0.1}`.
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
  model schema has no `batch_normalization` field at all, because the
  encoder architecture structurally forbids it (`SCI-19`) and an
  always-`false` boolean would only invite a future, silently-ignored
  `true` (`§11` below).
- A `requires_passed` free-text field — prerequisites are authored only as
  the typed `prerequisites` list (`§9` below,
  `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`).
- A dataset-owned eligibility value (`minimum_calibration_sample_count`)
  re-authored inside `models/autoencoder.yaml` or an `experiments/` entry —
  it has exactly one owner, the dataset (`§2`).

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
| Client construction (dataset setup), partition seed | Yes | No | Yes | No | Yes |
| Split boundaries (chronological fraction, timestamp field) | Yes | No | Yes | No | Yes |
| Preprocessing (strategy, scope) | Yes | No | Yes | No | Yes |
| Calibration-window selection (`§12` of `DOMAIN_AND_APPLICATION_ARCHITECTURE.md`) | Yes (when populated) | No | Yes | Yes | Yes, only for `calibration_window_size_stability` cells |
| Model architecture (hidden dims, activation) | Yes | No | Yes | No | Yes |
| Optimizer, learning rate | Yes | No | Yes | No | Yes |
| Training rounds (checkpoint schedule) | Yes | No | Yes | No | Yes |
| `rounds_max` | No — derived from the checkpoint schedule | No | Yes | No | No — computed, rejected if authored |
| Local epochs, participation | Yes | No | Yes | No | Yes |
| Micro-batch size, gradient accumulation | Yes | No | Yes | No | Yes |
| `effective_batch_size` | No — derived (`micro_batch_size × gradient_accumulation_steps`) | No | Yes | No | No — computed, rejected if authored |
| Worker count | Conditional (identity-bearing only if ordering/output-affecting) | Yes | Yes | No | Yes |
| Precision, determinism level | Yes | No | Yes | No | Yes |
| Checkpoint-selection rule | Yes | No | Yes | No | Yes (locked; one value per training profile) |
| Threshold construction and its parameters (quantile, K, λ, α) | Yes | No | Yes | Yes (units, direction) | Yes |
| `recalibration_mode` (`FROZEN`/`ONE_SHOT`) | Yes (when populated) | No | Yes | No | Yes, only for `chronological_recalibration_evaluation` evaluations; `None` (unauthored) elsewhere |
| Cluster-count canonicality, clustering `n_init`/`max_iter` | Yes | No | Yes | No | Yes |
| Shrinkage weight | Yes | No | Yes | Yes | Yes |
| Conformal coverage / alpha | Yes | No | Yes | Yes | Yes |
| Eligibility minimum-calibration threshold | Yes | No | Yes | No | Yes, once, on the owning dataset |
| Metric selection | Yes | No | Yes | Yes | Yes |
| Traffic rate (alert burden) | Yes (when requested) | No | Yes | Yes | Yes, when `AlertBurdenEvaluationSuite` is selected |
| `seed_cohort.paired_seed_count`, `seed_cohort.derivation` | Yes | No | Yes | No | Yes |
| `analyses[*].primary_procedure` / `secondary_procedures` | Yes | No | Yes | Yes | Yes; bootstrap resample count remains a blocker until pre-registered |
| Runtime device / CUDA requirement | No | Yes | Yes | No | Yes, once, on the named execution profile |
| GPU model, driver version | No | No | Yes | No | Runtime-captured only |
| RAM / VRAM budget | No | Yes | Yes | No | Yes; **not numerically specified in either source document — genuine blocker** |
| Output format | No | No | Yes | Yes | Yes |
| Report ordering | No | No | Yes | Yes | Yes |
| Log interval | No | No | Yes | No | Yes (cosmetic; documented single owner, the execution profile) |

## 7. Discriminated variants

Every multi-shaped field carries an explicit discriminator, never an
inferred shape. Example, client construction (a dataset setup):

```yaml
setups:
  dirichlet_partitioned:
    method: dirichlet_partitioned_clients
    client_count: 20
    alpha: 0.3
    # A complete document supplies partition_seed. Until its authority is
    # recorded, this draft fails validation and cannot resolve.
```

Example, training profile — every profile shares the model family's
architecture/optimizer/checkpoint fields and differs only in its own
discriminated `kind` and the fields that `kind` owns:

```yaml
training_profiles:
  federated_averaging:
    kind: federated_averaging_training
    local_epochs: 1
    participation: full
    personalization: none
  federated_averaging_personalized:
    kind: federated_averaging_training
    local_epochs: 1
    participation: full
    personalization: fedrep_ae   # or ditto / fedper_ae — never "Ditto" unless genuine Ditto (NAME-05)
      # BLOCKED: personalization comparator choice and hyperparameters (documented pre-training decision).
  federated_proximal:
    kind: federated_prox_training
    mu: 0.001   # or 0.01, or 0.1 — a separate resolved profile per grid point,
                # never a caller-supplied value outside {0.001, 0.01, 0.1}
    local_epochs: 1
    participation: full
    personalization: none
  centralized_pooled:
    kind: centralized_pooled_training
    # not federated; not in the causal ladder (ANCHOR-04)
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
scores; a metric addition never invalidates a threshold; a model change
invalidates every downstream checkpoint and score
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md §4`).

## 9. Anchor experiment family

`configs/experiments/anchor.yaml` holds exactly one experiment entry. The
fragment below preserves the source-given fields and illustrates where
draft validation reports a boundary blocker. A draft with either commented
requirement cannot resolve, plan, or run; no resolved object carries a
placeholder value.

```yaml
schema_version: 1
family: anchor
experiments:
  - slug: anchor_reproduction
    display_name: Anchor Reproduction
    evidence_role: anchor
    run_requirement: mandatory
    data: { dataset: nbaiot, setup: natural_devices }
    model: autoencoder
    training_profile: federated_averaging
    evaluations:
      - label: shared_mean
        threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
      - label: local
        threshold: { policy: local_threshold, quantile: 0.95 }
    analyses:
      - label: anchor_scope_effect
        kind: paired_threshold_analysis
        first_evaluation: shared_mean
        second_evaluation: local
        primary_metric: cv_fpr
        delta_orientation: shared_minus_local
        primary_procedure:
          method: bca_bootstrap
          confidence_level: 0.95
          # BLOCKED: bootstrap resample count must be supplied by statistical authority.
        secondary_procedures: []
      - label: anchor_equivalence
        kind: anchor_equivalence_analysis
        source_analysis: anchor_scope_effect          # the paired analysis above, by label
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
      execution: scientific
      report:
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
            source_result_types: [confirmatory_analysis_result]
            output_formats: [markdown, latex]
        wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite]
```

Every anchor-identity value that the source documents actually supply —
evidence role, dataset+setup, both threshold constructions, the quantile
`0.95`, the five-seed count, the confidence level `0.95`, and the reference
interval `[0.647, 0.769]` — is explicit here, none defaulted in Python. The
two fields the source documents do not supply (`resample_count`,
`experiment_seed`) remain boundary blockers until an authority supplies
them; there is no `anchor: true` switch that bypasses this requirement. The
resolved domain object owns the reference interval exactly once, in
`AnchorEquivalenceAnalysis.reference_interval`.

### 9.1 No dynamic client-construction fallback

An `external_device_validation`-family experiment's dataset setup is always
a fully resolved, explicit `external_device` or `external_group` setup on
`edge_iiotset.yaml` — `granularity: device` or `granularity: group`, never a
placeholder — because it is authored only after the standalone feasibility
audit closes (`SCIENTIFIC_FOUNDATION.md §5.1`). No scientific experiment's
configuration ever contains a runtime selection rule choosing between
device clients, group clients, or a pseudo-client fallback; that would
reintroduce the circular dependency this package removes.

## 10. Threshold-scope experiment family

`configs/experiments/threshold_scope.yaml` groups the confirmatory endpoint
with its two direct construction/quantile rule-outs — the experiments the
roadmap ties most tightly to the B1-vs-B2 pair (Tier 1 and its immediate
Tier 2 defenses). From here on, a flow-style `report: { table_type: …, … }`
is shorthand for the single-entry `report_artifacts` list worked in full in
`§9` (`report: { report_artifacts: [{ artifact_type: main_table, table_type:
…, … }], wording_outcomes: […] }`); every resolved `ReportDefinition` still
carries the complete `report_artifacts`/`wording_outcomes` shape, only the
prose in this document is compressed:

```yaml
schema_version: 1
family: threshold_scope
experiments:
  - slug: confirmatory_threshold_scope_effect
    display_name: Confirmatory Threshold-Scope Effect
    evidence_role: confirmatory
    run_requirement: mandatory
    tier: tier_1
    roadmap_reference: E-C1
    data: { dataset: nbaiot, setup: natural_devices }
    model: autoencoder
    training_profile: federated_averaging
    evaluations:
      - label: shared_mean
        threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
      - label: local
        threshold: { policy: local_threshold, quantile: 0.95 }
    analyses:
      - label: confirmatory_scope_effect
        kind: paired_threshold_analysis
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
      execution: scientific
      report: { table_type: confirmatory_interval, source_result_types: [confirmatory_analysis_result], output_formats: [markdown, latex], wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite] }
      # columns identical in shape to §9's anchor table; omitted here for brevity, never omitted in the resolved schema

  - slug: shared_threshold_construction_sensitivity
    display_name: Shared-Threshold Construction Sensitivity
    evidence_role: supportive
    run_requirement: mandatory
    tier: tier_2
    roadmap_reference: E-S1
    data: { dataset: nbaiot, setup: natural_devices }
    model: autoencoder
    training_profile: federated_averaging
    evaluations:
      - label: shared_mean
        threshold: { policy: shared_threshold, construction: mean, quantile: 0.95 }
      - label: shared_pooled
        threshold: { policy: shared_threshold, construction: pooled, quantile: 0.95 }
      - label: shared_weighted
        threshold: { policy: shared_threshold, construction: weighted, quantile: 0.95 }
      - label: local
        threshold: { policy: local_threshold, quantile: 0.95 }
    analyses:
      - label: mean_vs_local_dispersion
        kind: paired_threshold_analysis
        first_evaluation: shared_mean
        second_evaluation: local
        primary_metric: cv_fpr
        delta_orientation: shared_minus_local
        primary_procedure: { method: bca_bootstrap, confidence_level: 0.95 }
          # BLOCKED: bootstrap resample count required from statistical authority.
        secondary_procedures: []
    seed_cohort:
      paired_seed_count: 10
      derivation: deterministic_from_experiment_seed
      # BLOCKED: experiment_seed required.
    prerequisites:
      - requires: anchor_reproduction
        required_outcome: anchor_equivalence_passed
    operations:
      execution: scientific
      report: { table_type: dispersion_ladder, source_result_types: [policy_evaluation_result], output_formats: [markdown, latex], wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite] }

  - slug: threshold_quantile_sensitivity
    display_name: Threshold Quantile Sensitivity
    evidence_role: supportive
    run_requirement: mandatory
    tier: tier_2
    roadmap_reference: E-S2
    data: { dataset: nbaiot, setup: natural_devices }
    model: autoencoder
    training_profile: federated_averaging
    sweep:
      parameters:
        threshold_quantile:
          values: [0.90, 0.95, 0.975, 0.99]
    evaluations:
      - label: shared_mean
        threshold: { policy: shared_threshold, construction: mean, quantile: { from_sweep: threshold_quantile } }
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
    operations:
      execution: scientific
      report: { table_type: sensitivity_grid, source_result_types: [policy_evaluation_result], output_formats: [markdown, latex], wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite] }
```

The composer validates a binding's declared parameter and value-object type,
then expands one complete resolved run and canonical snapshot per
coordinate — exactly as it already expands `dirichlet_alpha`,
`shrinkage_weight`, `calibration_sample_count`, and `fixed_k` for the other
families (`§17`). Bindings are consumed in composition and never enter the
domain.

## 11. Reusable dataset configuration

`dataset_version` never carries a meaningless counter such as `v1` or
`processed_v1`; a semantic source name is authored only when a dataset
genuinely has more than one artifact in play (for example a future
raw-versus-reprocessed distinction). None of the three datasets below
currently does, so each authors the one descriptive name that actually
identifies its artifact.

`configs/datasets/nbaiot.yaml` — the sole N-BaIoT document, owning both of
its authorized client-construction setups plus its source-audit trail:

```yaml
schema_version: 1
dataset: n_baiot
dataset_version: processed   # semantic name, not a meaningless "v1"; no second N-BaIoT
                              # artifact exists yet that would require a distinguishing name
audits:
  - check: source_inspection
    inspection:
      expected_facts:
        - feature_schema_present
        - benign_and_attack_members_present
        - per_device_membership_recoverable
      source_row_identity_scheme: required
    feasibility:
      rule: source_schema_complete
      required_evidence: [feature_schema_manifest, per_device_counts]
    operations:
      execution: dataset_audit
      report: { table_type: source_inspection_report, output_formats: [markdown] }
eligibility:
  minimum_calibration_sample_count: 100
setups:
  natural_devices:
    client_construction: { method: physical_device_clients, device_count: 9 }
  dirichlet_partitioned:
    client_construction:
      method: dirichlet_partitioned_clients
      client_count: 20
      alpha: { from_sweep: dirichlet_alpha }   # bound by the owning experiment's sweep
      # The required partition seed is pre-registered before resolution.
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
  chunk_profile: { chunk_row_count: 50000 }
```

`configs/datasets/ciciot2023.yaml` — boundary-role dataset only, carrying
its feature-count re-verification audit as a blocker:

```yaml
schema_version: 1
dataset: ciciot2023
dataset_version: processed   # the only artifact in scope is the processed CSV;
                              # feature count is source-inspected below, never guessed from the name
audits:
  - check: source_inspection
    inspection:
      expected_facts:
        - feature_schema_present
        - file_level_membership_recoverable
        - mac_device_ip_capture_timestamp_columns_present_or_absent   # records absence explicitly
      source_row_identity_scheme: required
    feasibility:
      rule: source_schema_complete
      required_evidence: [feature_schema_manifest, file_member_manifest]
    operations: { execution: dataset_audit, report: { table_type: source_inspection_report, output_formats: [markdown] } }
  - check: processed_feature_verification
    inspection:
      expected_facts: [processed_feature_count_matches_conference_value]
      reference_feature_count: 39
    feasibility:
      rule: processed_feature_count_verified
      required_evidence: [processed_feature_schema_manifest]
      # feature count of the actual processed artifact; mirror distributions differ (roadmap §7).
    operations: { execution: dataset_audit, report: { table_type: source_inspection_report, output_formats: [markdown] } }
eligibility:
  minimum_calibration_sample_count: 100
setups:
  file_pseudo_clients:
    client_construction: { method: dataset_file_pseudo_clients, pseudo_client_count: 63 }
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
  # feature count d is source-inspected, never authored; BLOCKED for any quantitative claim
  # until the processed_feature_verification audit closes (conference value 39).
```

`configs/datasets/edge_iiotset.yaml` — the external-validation dataset,
owning three setups (device, group, chronological) and every audit that
gates them:

```yaml
schema_version: 1
dataset: edge_iiotset
dataset_version: processed   # semantic name; no second Edge-IIoTset artifact exists yet
audits:
  - check: source_inspection
    inspection:
      expected_facts: [feature_schema_present, device_identity_recoverable, capture_timestamp_present_or_absent]
      source_row_identity_scheme: required
    feasibility:
      rule: source_schema_complete
      required_evidence: [feature_schema_manifest, per_device_counts, timestamp_evidence]
    operations: { execution: dataset_audit, report: { table_type: source_inspection_report, output_formats: [markdown] } }
  - check: client_granularity_feasibility
    inspection:
      expected_facts: [per_candidate_client_benign_counts]
      candidate_granularities: [device, group]
      target_client_counts: [6, 15]
    feasibility:
      rule: eligibility_coverage_gate
      minimum_calibration_sample_count: 100
      minimum_client_coverage_ratio: 0.90     # n_k ≥ 100 for ≥ 90% of clients
      required_evidence: [per_client_benign_counts]
      # produces the device-vs-group FEASIBILITY_RESULT; a human then fixes the setup's
      # granularity below (SCIENTIFIC_FOUNDATION.md §5.1).
    operations: { execution: dataset_audit, report: { table_type: feasibility_report, output_formats: [markdown] } }
  - check: timestamp_semantics_verification
    inspection:
      expected_facts: [genuine_capture_time_field_present, per_client_temporal_ordering_recoverable]
    feasibility:
      rule: timestamp_semantics_verified
      required_evidence: [timestamp_evidence, per_client_time_span]
      # gates the chronological setup below; absence blocks the temporal MVE.
    operations: { execution: dataset_audit, report: { table_type: feasibility_report, output_formats: [markdown] } }
eligibility:
  minimum_calibration_sample_count: 100
setups:
  external_device:
    client_construction:
      method: external_device_or_group_clients
      granularity: device                 # fixed by human authorization post-audit
      feasibility_result_ref: client_granularity_feasibility   # provenance only
  external_group:
    client_construction:
      method: external_device_or_group_clients
      granularity: group
      feasibility_result_ref: client_granularity_feasibility
  chronological:
    client_construction:
      method: external_device_or_group_clients
      granularity: device
      feasibility_result_ref: client_granularity_feasibility
    temporal_window:
      role: temporal_evaluation
      historical_fraction: 0.70          # locked chronological boundary
      capture_time_field: capture_timestamp
      # requires the timestamp_semantics_verification audit to have passed.
split_definition:
  train: { role: train }
  calibration: { role: calibration, benign_only: true }
  test: { role: test }
preprocessing:
  normalization: { strategy: min_max, scope: global_train }
  # BLOCKED: external-device feature schema / input dimension from source inspection.
```

## 12. Reusable model configuration

`configs/models/autoencoder.yaml` — the one model family, carrying every
named training profile the roadmap authorizes:

```yaml
schema_version: 1
architecture:
  hidden_dims: [80, 40, 20]
  activation: relu
reconstruction_objective: mse
optimizer:
  optimizer_type: adam
  learning_rate: 0.001
  scheduler: null
precision: fp32
determinism: strict
checkpoint_schedule:
  rounds: [25, 50, 75, 100, 125, 150, 200]
training_batch:
  micro_batch_size: 256
  gradient_accumulation_steps: 1
training_profiles:
  federated_averaging:
    kind: federated_averaging_training
    local_epochs: 1
    participation: full
    personalization: none
    checkpoint_selection:
      rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
      tie_break: earliest_scheduled_round
  federated_averaging_personalized:
    kind: federated_averaging_training
    local_epochs: 1
    participation: full
    personalization: fedrep_ae   # or ditto / fedper_ae — never "Ditto" unless genuine Ditto (NAME-05)
      # BLOCKED: personalization comparator choice and hyperparameters (documented pre-training decision).
    checkpoint_selection:
      rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
      tie_break: earliest_scheduled_round
  federated_proximal:
    kind: federated_prox_training
    mu: 0.001   # or 0.01, or 0.1 — a separate resolved profile per grid point,
                # never a caller-supplied value outside {0.001, 0.01, 0.1}
    local_epochs: 1
    participation: full
    personalization: none
    checkpoint_selection:
      rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
      tie_break: earliest_scheduled_round
  centralized_pooled:
    kind: centralized_pooled_training
    # not federated; not in the causal ladder; own identity chain (ANCHOR-04)
    checkpoint_selection:
      rule: lowest_pooled_benign_validation_reconstruction_error
      tie_break: earliest_scheduled_round
```

Every value above — the encoder widths `(80, 40, 20)`, no batch
normalization (structurally absent from the schema, `SCI-19`, never an
authored boolean), MSE reconstruction objective, Adam at `0.001`, one local
epoch, full participation, the fixed `{25,50,75,100,125,150,200}` schedule,
batch size `256`, one gradient-accumulation step, `FP32`, strict
determinism, and the FedProx µ-grid `{0.001, 0.01, 0.1}` — is given
explicitly in the source architecture's resolved-implementation-decisions
record; none is invented. `rounds_max` (`200`) and `effective_batch_size`
(`256`) are never authored here — both are pure derivations
(`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`) computed after this document
resolves. Eligibility (`minimum_calibration_sample_count = 100`) is **not**
authored here; it is the referencing experiment's dataset that owns it
(`§2`), removing the duplicate-ownership defect a prior draft of this
package carried (a detector document and its owning dataset both declaring
the same eligibility value under different names).

Two templates referencing the identical `training_profiles.federated_averaging`
profile with only their `dataset`/`setup` differing (`natural_devices` vs
`dirichlet_partitioned`) demonstrate that a new dataset evaluation setting
never requires a new model document (`SCIENTIFIC_FOUNDATION.md §8` extension
test).

## 13. Execution configuration

`configs/execution.yaml` — every named profile in one file, shown as a
non-resolvable draft until the authority supplies its operational limits:

```yaml
schema_version: 1
profiles:
  scientific:
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
  print_grade:
    device_policy: cuda_required
    determinism: strict
    resource_budget:
      # BLOCKED: concrete RAM and VRAM limits required.
    concurrency:
      training_concurrency: 1
      scoring_concurrency: 1
      # BLOCKED: concrete worker count required.
    process_start_method: spawn
    # BLOCKED: log_interval_rounds requires its explicit operational owner value.
  development:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 32, max_vram_gib: 12 }   # explicit reduced value; non-citable by mode
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 2 }
    process_start_method: spawn
    log_interval_rounds: 5
  smoke:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 16, max_vram_gib: 8 }
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 1 }
    process_start_method: spawn
    log_interval_rounds: 1
  dataset_audit:
    device_policy: cpu_only          # audits touch no CUDA stage; fork is permitted for CPU-only workers
    determinism: strict
    resource_budget: { max_ram_gib: 16 }
    concurrency: { worker_count: 4 }
    process_start_method: fork
    log_interval_rounds: 10
  test_smoke:
    device_policy: cpu_only          # test-only; resolves storage beneath TEST_SANDBOX; never scientific evidence
    determinism: strict
    resource_budget: { max_ram_gib: 8 }
    concurrency: { worker_count: 1 }
    process_start_method: spawn
    log_interval_rounds: 1
```

`process_start_method: spawn` is not fabricated: it follows directly from
the source architecture's fixed rule that any stage touching CUDA must use a
spawn context established before any CUDA call in the parent process, never
the global `set_start_method`. The commented requirements are genuine
boundary blockers reported before a domain value is constructed. Every
profile, including `development` and `smoke`, requires an explicit,
complete set of fields; `scientific` and `print_grade` additionally require
the roadmap's scientific evidence before a `SCIENTIFIC`/`PRINT_GRADE` cell
may schedule. A reduced profile such as `smoke` is a separately authored
profile, never an automatic backoff from `scientific` (`EXEC-02`).

## 14. Stress-test model reuse

`fedprox_aggregation_stress_test` (`§16`) references
`models/autoencoder.yaml`'s `training_profiles.federated_proximal` profile,
never a separate detector document — every field below `kind` is
deliberately identical to `training_profiles.federated_averaging`'s
non-strategy fields (`SCI-07`), which is what makes the two profiles
"matched" in the roadmap's sense; the discriminated `kind` tag alone keeps
the stress test structurally outside the causal ladder.

## 15. Inline reporting

`operations.report` on every experiment entry is an inline `ReportDefinition`
fragment (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §16.7`); no
`configs/reporting/` directory exists to reference. A representative
non-confirmatory table, inlined on `shared_threshold_construction_sensitivity`
(`§10`):

```yaml
report:
  report_artifacts:
    - artifact_type: main_table
      table_type: dispersion_ladder
      columns:
        - { name: threshold_construction, unit: none, direction: none }
        - { name: cv_fpr, unit: ratio, direction: lower_is_better }
        - { name: iqr_fpr, unit: ratio, direction: lower_is_better }
        - { name: fpr_range, unit: ratio, direction: lower_is_better }
        - { name: worst_client_fpr, unit: ratio, direction: lower_is_better }
      ordering: deterministic_by_threshold_construction
      missing_value_policy: render_typed_unavailable   # never zero/NaN (EVAL §5)
      source_result_types: [policy_evaluation_result]
      output_formats: [markdown, latex]
  wording_outcomes: [strong_positive, weak_positive, mixed, null, opposite]
```

Every column declares a unit and a metric direction explicitly
(`EVALUATION_REPORTING_AND_PROVENANCE.md §9.2`); a column with neither is
rejected at schema validation, because an undirected numeric column cannot
be safely rendered as "higher is better" or "lower is better" without an
explicit author decision. No genuinely global rendering default has been
identified that would justify reintroducing a shared presentation file; if
one is, it is added as a single, small, explicitly justified file — never a
directory mirroring the experiment catalogue.

## 16. Remaining experiment families

Every family below follows the identical shape worked in full in `§§9–10`:
one `configs/experiments/<family>.yaml` document, a `family` name, and an
`experiments` list of independently resolvable entries, each carrying
`data` (dataset + setup), `model` + `training_profile`, `evaluations`,
optional `sweep`, `analyses`, `seed_cohort`, `prerequisites`, and
`operations` (`execution` profile name + inline `report`). Only the
identity-bearing content that differs from `§§9–10` is given here; no field
family, blocker, or scientific value described elsewhere in this package is
altered by moving an experiment into a family file.

### 16.1 `heterogeneity.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `controlled_heterogeneity_response` | E-S3 | supportive; tier_2 | `nbaiot` / `dirichlet_partitioned` | `dirichlet_alpha ∈ {0.1, 0.3, 0.5, 1.0, 10.0, iid}` | carries the heterogeneity–threshold-benefit association (formerly E-M4) as an attached `metric_association_analysis` regressing pairwise JS divergence against `cv_fpr_delta`; report: `severity_trend` figure + `scatter` figure |

### 16.2 `calibration_mechanisms.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `cluster_mechanism` | E-M1/E-M2/E-Q2 | mechanism; tier_5 (+tier_7 exploratory) | `nbaiot` / `natural_devices` (+ `edge_iiotset` where feasible) | `fingerprint_feature_subset` (4 subsets) | one merged experiment, four typed axes: grouping (`family_threshold` vs `cluster_threshold`), fingerprint feature set, aggregation (`mean`/`robust_median`), authorized K (canonical `3`, mandatory; other K exploratory); report: `cluster_stability` table + `contingency` table |
| `calibration_window_size_stability` | E-V1 | boundary; tier_6 (RQ3) | `nbaiot` / `natural_devices` | `calibration_sample_count ∈ {50,100,250,500,1000,5000}` | each point resolves a `CalibrationSubsetDefinition`; includes `calibration_size_aware_fallback_threshold`; report: `sensitivity_grid` |
| `local_global_threshold_shrinkage` | E-V2 | supportive; RQ3 | `nbaiot` / `natural_devices` | `shrinkage_weight ∈ {0, .25, .5, .75, 1}` | report: `lambda_curve` figure |
| `conformal_local_threshold_coverage` | E-V3 | supportive; Tier-1 tautology defense | `nbaiot` / `natural_devices` (+ `edge_iiotset`) | — | `coverage_alpha = 0.05`; report: conformal coverage table |

### 16.3 `external_validation.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `external_device_dataset_validation` | E-X1 | external_validation; tier_3 | `edge_iiotset` / `external_device` (or `external_group`, audit-assigned) | `threshold_quantile ∈ {.90,.95,.975,.99}` (sole owner of the external-dataset q-sensitivity axis) | carries the operational alert-burden evaluation (formerly E-O1) requiring validated `TrafficRateEvidence`; report: external `confirmatory_interval` + `alert_burden` |
| `chronological_recalibration_evaluation` | E-B1 | boundary; tier_6 | `edge_iiotset` / `chronological` | — | frozen vs one-shot recalibration; report: `recovery_curve` figure |

### 16.4 `training_stress_tests.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Training profile | Notes |
|---|---|---|---|---|---|
| `fedprox_aggregation_stress_test` | E-T1 | stress_test; tier_4 | `nbaiot` / `natural_devices` (+ `edge_iiotset`, sibling entry) | `training_profiles.federated_proximal` (µ-grid, `§14`) | report: `stress_test` table |
| `model_personalization_absorption_test` | E-T2 | stress_test; tier_4 | `nbaiot` / `natural_devices` (+ `edge_iiotset`, sibling entry) | `training_profiles.federated_averaging_personalized` | its `AbsorptionAnalysis` reuses the confirmatory experiment's FedAvg core delta by cross-experiment reference, never retraining it; report: `stress_test` table |

### 16.5 `references_and_boundaries.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Training profile | Notes |
|---|---|---|---|---|---|
| `centralized_pooled_reference` | B0 | supportive; mandatory wherever cited | `nbaiot` / `natural_devices` | `training_profiles.centralized_pooled` | own centralized identity chain; never fused with federated artifacts (`ANCHOR-04`, `ART-06`); report: `dispersion_ladder` |
| `federated_summary_comparator` | E-T3/E-Q1/E-Q5 | stress_test (comparator); tier_4 | `nbaiot` / `natural_devices` (+ `edge_iiotset`) | `training_profiles.federated_averaging` | merged: matched benign-summary comparison (mandatory primary), quantile-estimation-error backbone analysis (mandatory), fixed-k `{2.0, 2.5, 3.0}` sensitivity evaluation carrying `execution_requirement: optional`, `publication_placement: supplementary` — optional and supplementary because it can never become the primary comparator result (`SCI-18`); report: `comparator` table |
| `file_pseudo_client_applicability_boundary` | `B_A_APPLICABILITY_BOUNDARY` | boundary; tier_6 | `ciciot2023` / `file_pseudo_clients` | `training_profiles.federated_averaging` | boundary report only, never generalized; report: `boundary_null` table |

## 17. Sweep representation

A sweep dimension is declared once, on the owning `experiments/` entry or
the owning dataset setup, only — never as a domain-level
`ExperimentTemplate` (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §4`) — using
only the exact grids the roadmap specifies. `§10`'s
`threshold_quantile_sensitivity` entry is worked in full above. Other sweep
grids follow the identical mechanism using their own source-given values:
alpha `{0.1, 0.3, 0.5, 1.0, 10.0, IID}` (`controlled_heterogeneity_response`,
bound into `nbaiot.yaml`'s `dirichlet_partitioned` setup), lambda
`{0, .25, .5, .75, 1}` (`local_global_threshold_shrinkage`), calibration
size `{50, 100, 250, 500, 1000, 5000}` (`calibration_window_size_stability`,
each point additionally resolving a `CalibrationSubsetDefinition`), and
fixed-k `{2.0, 2.5, 3.0}` (`federated_summary_comparator`'s optional
supplementary evaluation). Expanding an experiment-family document into its
independent entries (`§3`) and expanding a sweep into its coordinates are
the same class of pure, boundary-only expansion; neither introduces a
second composition mechanism.

## 18. Blocked-value handling, worked

Attempting to schedule `anchor_reproduction` (`§9`) under the `scientific`
execution profile is rejected by `ScientificReadinessResult` before any
network, CUDA, or storage resource is touched, because
`analyses[0].primary_procedure.resample_count` and
`seed_cohort.experiment_seed` are absent from the draft. The rejection names
both fields, cites the blocker table entries in
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`, and proposes no substitute
value. The same draft is rejected under `development` and `smoke` as well:
those profiles use complete explicit reduced values and are non-citable
because of execution mode, not incomplete configuration.

## 19. Validation failure examples

Removing `AnchorEquivalenceAnalysis.reference_interval.lower_bound` from
`§9` fails schema validation with a missing-field error naming the field
and the document; it never activates a Python default, a Pydantic default,
a loader fallback, or a library default. Supplying `cluster_count` on a
`local_global_shrinkage_threshold` variant (`§7`) fails for the same reason
in the opposite direction. Supplying `effective_batch_size` or `rounds_max`
on `models/autoencoder.yaml` (`§12`) fails because the schema owns no such
field — both are computed after resolution, never accepted as input.
Authoring `eligibility.minimum_calibration_sample_count` on the model or on
an experiment entry fails because the dataset is its sole owner (`§2`). A
`SCIENTIFIC`- or `PRINT_GRADE`-mode document that is incomplete fails
boundary validation before `ScientificReadinessResult`; no execution profile
may carry a placeholder field.

## 20. CLI contract

One canonical CLI, `datp-core experiment <action>`, with exactly seven
actions:

```bash
datp-core experiment list
datp-core experiment validate --config <slug>
datp-core experiment resolve --config <slug>
datp-core experiment plan --config <slug>
datp-core experiment run --config <slug>
datp-core experiment status --config <slug>
datp-core experiment report --config <slug>
```

`--config` accepts a registered experiment slug (`datp-core experiment
list` enumerates every registered slug and the family document that
contains it). A slug is unique across every family document; the CLI never
needs a file path, because one family document may hold several experiments
and a path alone would be ambiguous. The CLI may additionally accept only a
storage-root override where operationally required, and dry-run, verbosity,
confirmation, and logging controls that do not affect scientific output.

The CLI never accepts a scientific override such as `--set
threshold.quantile=...`, `--seed`, `--rounds`, `--batch-size`, or any flag
that would set, adjust, or replace a dataset, client construction, split,
preprocessing, training profile, model architecture, optimizer, learning
rate, round or checkpoint schedule, batch size, threshold policy or
quantile, seed cohort, execution profile, statistical procedure, reporting
content, or any other scientific, identity-bearing, or output-affecting
value. Dataset audits expose a parallel, dataset-scoped lifecycle:

```bash
datp-core dataset-audit list
datp-core dataset-audit validate --dataset <dataset> --check <check>
datp-core dataset-audit resolve --dataset <dataset> --check <check>
datp-core dataset-audit plan --dataset <dataset> --check <check>
datp-core dataset-audit run --dataset <dataset> --check <check>
datp-core dataset-audit status --dataset <dataset> --check <check>
datp-core dataset-audit report --dataset <dataset> --check <check>
```

`--dataset` selects the owning `datasets/<name>.yaml` document; `--check`
selects one named entry in its `audits` list (`§2.1`). There is no separate
audit slug or audit file to address, because an audit is no longer a
freestanding root document. A scientific change occurs only through an
edited, reviewed configuration document, which produces a new resolved
snapshot and new affected identities (`CFG-09`).

## 21. Resolved configuration snapshot persistence

`config/compose.py` returns `ConfigurationResolutionResult`: the authored
root snapshot, complete frozen `RunDefinition` values, canonical resolved
run snapshots, and typed boundary blockers. Scientific sweep coordinates are
represented by `ScientificExperimentCell` within the resolved run result.
The application—not the composer—persists each `RESOLVED_CONFIGURATION`
artifact before planning, so a later audit compares a stored result against
the exact configuration that produced it without re-parsing YAML. An
unsupported configuration schema version fails clearly at load time; no
automatic migration or backward-compatibility logic exists (`CFG-10`).

## 22. Zero-input Make targets

Make targets are convenience aliases around the CLI (`§20`). They contain
no user-supplied parameters and no `EXPERIMENT=...`, `CONFIG=...`,
`MODE=...`, or equivalent input. Each target identifies exactly one action
and one registered experiment slug; a target whose referenced slug is not
registered fails, it never silently no-ops.

### 22.1 Experiment-family targets

Every regularly executed root experiment exposes only the actions
meaningful for it, addressed by slug regardless of which family document
backs it:

| Family target prefix | Registered slug | Actions exposed |
|---|---|---|
| `anchor` | `anchor_reproduction` | validate, resolve, plan, run, status, report |
| `confirmatory` | `confirmatory_threshold_scope_effect` | validate, resolve, plan, run, status, report |
| `shared-threshold-sensitivity` | `shared_threshold_construction_sensitivity` | validate, plan, run, status, report |
| `quantile-sensitivity` | `threshold_quantile_sensitivity` | validate, plan, run, status, report |
| `controlled-heterogeneity` | `controlled_heterogeneity_response` | validate, plan, run, status, report |
| `cluster-mechanism` | `cluster_mechanism` | validate, plan, run, status, report |
| `calibration-window` | `calibration_window_size_stability` | validate, plan, run, status, report |
| `threshold-shrinkage` | `local_global_threshold_shrinkage` | validate, plan, run, status, report |
| `conformal-threshold` | `conformal_local_threshold_coverage` | validate, plan, run, status, report |
| `external-validation` | `external_device_dataset_validation` | plan, run, status, report (feasibility-gated; `§9.1`) |
| `fedprox-stress-test` | `fedprox_aggregation_stress_test` | plan, run, status, report |
| `personalization-stress-test` | `model_personalization_absorption_test` | plan, run, status, report |
| `federated-summary-comparator` | `federated_summary_comparator` | validate, plan, run, status, report |
| `temporal-recalibration` | `chronological_recalibration_evaluation` | plan, run, status, report (feasibility- and timestamp-gated) |
| `centralized-reference` | `centralized_pooled_reference` | validate, plan, run, status, report |
| `pseudo-client-boundary` | `file_pseudo_client_applicability_boundary` | validate, plan, run, status, report |

Example:

```make
.PHONY: anchor-validate anchor-resolve anchor-plan anchor-run anchor-status anchor-report

anchor-validate:
	datp-core experiment validate --config anchor_reproduction

anchor-resolve:
	datp-core experiment resolve --config anchor_reproduction

anchor-plan:
	datp-core experiment plan --config anchor_reproduction

anchor-run:
	datp-core experiment run --config anchor_reproduction

anchor-status:
	datp-core experiment status --config anchor_reproduction

anchor-report:
	datp-core experiment report --config anchor_reproduction

.PHONY: confirmatory-validate confirmatory-plan confirmatory-run confirmatory-status confirmatory-report

confirmatory-validate:
	datp-core experiment validate --config confirmatory_threshold_scope_effect

confirmatory-plan:
	datp-core experiment plan --config confirmatory_threshold_scope_effect

confirmatory-run:
	datp-core experiment run --config confirmatory_threshold_scope_effect

confirmatory-status:
	datp-core experiment status --config confirmatory_threshold_scope_effect

confirmatory-report:
	datp-core experiment report --config confirmatory_threshold_scope_effect

.PHONY: external-validation-plan external-validation-run

external-validation-plan:
	datp-core experiment plan --config external_device_dataset_validation

external-validation-run:
	datp-core experiment run --config external_device_dataset_validation
```

Every other family in `§22.1` follows the identical two-line-per-action
shape; only the target prefix and the referenced slug change. Target names
are explicit, readable without opening the Makefile, and free of
unexplained abbreviations (`cluster-mechanism-plan`,
`personalization-stress-test-run`, `temporal-recalibration-report` — never
`c1`, `run-b`, or `exp-cl`). Generic parameterized targets (`make run
EXPERIMENT=anchor`, `make plan CONFIG=...`, `make experiment ACTION=run
NAME=...`) are never defined.

### 22.2 Global targets

```make
.PHONY: help experiments validate-all plan-all-mandatory status-all report-all-completed mandatory-run

help:
	@echo "Targets:"
	@echo "  anchor-{validate,resolve,plan,run,status,report}"
	@echo "  confirmatory-{validate,resolve,plan,run,status,report}"
	@echo "  <family>-{validate,plan,run,status,report} for every family in §22.1"
	@echo "  experiments            list every registered experiment (datp-core experiment list)"
	@echo "  validate-all           validate every registered experiment configuration"
	@echo "  plan-all-mandatory     plan every run_requirement=MANDATORY experiment"
	@echo "  status-all             report status for every registered experiment"
	@echo "  report-all-completed   render reports for every completed experiment"
	@echo "  mandatory-run          run the fixed, explicitly listed mandatory sequence below"

experiments:
	datp-core experiment list

validate-all:
	datp-core experiment validate --config anchor_reproduction
	datp-core experiment validate --config confirmatory_threshold_scope_effect
	# one explicit line per registered slug; never a directory glob

plan-all-mandatory:
	datp-core experiment plan --config anchor_reproduction
	datp-core experiment plan --config confirmatory_threshold_scope_effect
	# one explicit line per MANDATORY registered slug

status-all:
	datp-core experiment status --config anchor_reproduction
	datp-core experiment status --config confirmatory_threshold_scope_effect
	# one explicit line per registered slug

report-all-completed:
	datp-core experiment report --config anchor_reproduction
	datp-core experiment report --config confirmatory_threshold_scope_effect
	# one explicit line per completed registered slug

mandatory-run:
	datp-core experiment run --mandatory
```

Mandatory orchestration and prerequisite enforcement belong to the
application. Make never encodes dependencies, so parallel Make execution
cannot bypass the typed `AnchorEquivalenceGate`.

## 23. Extension worked example

Adding a new threshold construction, a new dataset, or a new attack/defense
direction the roadmap authorizes later never requires editing every
existing family document. Concretely: adding a new dataset means one new
`configs/datasets/<name>.yaml` document, no edit to `models/autoencoder.yaml`
or any `configs/experiments/` family; adding a new threshold construction
means a new discriminated `threshold.policy` arm plus its implementation,
with every existing experiment entry untouched because none references the
new policy; adding a new experiment means one new entry appended to the
family document whose scientific role it matches, referencing existing
dataset/setup and model/training-profile identities, never a new planner or
executor branch (`PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md §7`,
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §9.2`).
