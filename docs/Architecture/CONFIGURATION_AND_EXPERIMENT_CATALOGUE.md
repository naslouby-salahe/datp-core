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
- An `effective_batch_size`, `rounds_max`, `batch_normalization`,
  `input_dim`, or artifact `namespace` field present in an authored YAML
  document — each is computed post-resolution (`effective_batch_size` and
  `rounds_max` by the pure functions in
  `DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`; `input_dim` as
  `len(model_feature_order)` from the resolved dataset's
  `DatasetFieldSchema`, `§3.1` of the same file; `namespace` by
  `derive_artifact_namespace`, `§3.4` of the same file); the
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

### 11.0 Field-level schema evidence base

Every field claim in `§§11.1–11.3` below is sourced directly from the
mounted raw corpus (`data/raw/`, a symlink to the shared external data
root) — header inspection, targeted row sampling, and the dataset
authors' own documentation shipped alongside the files. Nothing is
inferred from the roadmap or from memory of the published papers alone. A
`DatasetFieldSchema` (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.1`) is the
resolved, fingerprinted form of each table below; `SOURCE_INSPECTION`
(`PIPELINE_EXECUTION_AND_ARTIFACTS.md §2`) is the stage that re-derives it
from the actual mounted files at run time rather than trusting this
document as a substitute for inspection. Where the raw corpus does not
settle a question, the table says so explicitly and
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7` carries the corresponding
blocker; nothing below is invented.

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

### 11.1 N-BaIoT field-level schema

**Source layout (verified against the mounted corpus).** Nine per-device
directories (`Danmini_Doorbell`, `Ecobee_Thermostat`, `Ennio_Doorbell`,
`Philips_B120N10_Baby_Monitor`, `Provision_PT_737E_Security_Camera`,
`Provision_PT_838_Security_Camera`, `Samsung_SNH_1011_N_Webcam`,
`SimpleHome_XCS7_1002_WHT_Security_Camera`,
`SimpleHome_XCS7_1003_WHT_Security_Camera` — exactly `device_count: 9`,
confirming `PhysicalDeviceClients`). Each device directory holds
`benign_traffic.csv` plus zero or more attack-family subdirectories: every
device has `gafgyt_attacks/` (BASHLITE; five files —
`combo.csv`, `junk.csv`, `scan.csv`, `tcp.csv`, `udp.csv`); seven of the
nine devices additionally have `mirai_attacks/` (five files — `ack.csv`,
`scan.csv`, `syn.csv`, `udp.csv`, `udpplain.csv`). **`Ennio_Doorbell` and
`Samsung_SNH_1011_N_Webcam` have no `mirai_attacks/` directory at all** —
confirmed by directory listing, not merely undocumented; any experiment
computing a per-family (Mirai-specific) statistic must treat these two
clients as structurally ineligible for that family, never as
zero-count/absent-but-expected. A top-level `demonstrate_structure.csv`
and `N_BaIoT_dataset_description_v1.txt` exist alongside the nine device
directories; the former is a header-only file (zero data rows) and is not
a data source.

**Row identity, client identity, label.** No CSV carries an identity, MAC,
IP, device, or timestamp column of any kind — confirmed: every
`benign_traffic.csv` and every attack file has exactly the same 115
comma-separated numeric fields and nothing else. Client identity is
therefore **path-derived only** (the device directory name); the binary
label is **path-derived only** (`benign_traffic.csv` → benign,
any file under `gafgyt_attacks/` or `mirai_attacks/` → attack); the
attack-family label is the subdirectory name (`gafgyt` | `mirai`) and the
attack-type label is the file's base name (`combo`, `junk`, `scan`, `tcp`,
`udp` under `gafgyt`; `ack`, `scan`, `syn`, `udp`, `udpplain` under
`mirai` — note `scan` and `udp` are reused file names under both families
and are only unambiguous together with the family directory). There is no
row-level provenance field distinguishing individual capture sessions
within one file.

**Feature schema (all 115 columns, header-verified byte-identical across
all nine devices and both attack families).** The columns are Kitsune
stream-aggregation statistics (`N_BaIoT_dataset_description_v1.txt`,
shipped with the corpus), a regular product of five aggregation scopes,
five damped-window decay factors, and each scope's own statistic set —
every one of the 115 names was enumerated from the actual header, not
computed from the rule alone:

| Aggregation scope | Meaning | Statistics | Per-window count | × 5 windows (`L5,L3,L1,L0.1,L0.01`) |
|---|---|---|---|---|
| `MI_dir` | stats of recent traffic from this packet's host (IP+MAC) | `weight, mean, variance` | 3 | 15 |
| `H` | stats of recent traffic from this packet's host (IP) | `weight, mean, variance` | 3 | 15 |
| `HH` | stats of traffic from this host to the destination host | `weight, mean, std, magnitude, radius, covariance, pcc` | 7 | 35 |
| `HH_jit` | jitter of traffic from this host to the destination host | `weight, mean, variance` | 3 | 15 |
| `HpHp` | stats of traffic from this host+port to the destination host+port | `weight, mean, std, magnitude, radius, covariance, pcc` | 7 | 35 |

`15+15+35+15+35 = 115`, matching the header column count exactly (no
undocumented 116th column, no short row observed). Column naming is
`{scope}_L{window}_{statistic}` (`HH_jit` is the one scope whose own name
contains an underscore, e.g. `HH_jit_L0.01_variance`). Every one of the 115
columns is `role: MODEL_FEATURE`, `inferred_type: NUMERIC_FLOAT`; there is
no excluded, identity, or label column to carry — canonical field IDs are
the lowercased, dot-normalized source names (`HH_L0.1_pcc` →
`hh_l0_1_pcc`) and `model_feature_order` is the literal 115-column header
order, verified identical across every one of the eighteen inspected files
(nine devices × {benign, one gafgyt file, one mirai file where present}).

**Verified data-quality findings.**
- **Row-1 cold-start artifact (every raw file).** The very first data row
  of every N-BaIoT CSV is the stream's first-ever observed packet under
  Kitsune's incremental damped-window statistics. For that row only, every
  `*_weight` column reads `1`, every `*_variance`/`*_std` column reads `0`,
  and — verified on `Danmini_Doorbell/benign_traffic.csv` — every
  `HH_jit_L*_mean` column reads the literal value `1505661693`, a Unix
  epoch timestamp (2017-09-17), not a jitter statistic; row 2 of the same
  file already shows an ordinary small jitter mean (`≈4.98`). This is a
  genuine artifact of the extractor's cold start, not a transcription
  error: it reproduces on every file checked. **Preprocessing rule:** row 1
  of every raw N-BaIoT file is either dropped before model-feature
  materialization or explicitly flagged as a cold-start row; it is never
  averaged, scaled, or calibrated against without this handling, because
  its `HH_jit_*_mean` values are off-scale by roughly nine orders of
  magnitude relative to every other row.
- **Low-rate exact-duplicate rows.** `Ecobee_Thermostat/benign_traffic.csv`
  (13,113 rows) contains 2 exact-duplicate rows (0.015%); no non-numeric or
  empty cell and no constant column were found in the same file. Duplicate
  handling is a stated, explicit policy (kept or deduplicated), never
  silently assumed.
- **No missing/non-numeric cells** were found in any sampled file beyond
  the row-1 artifact above; every cell parses as a finite float.

**Blockers.** None for feature-schema identity (fully verified, closed by
inspection). The row-1 cold-start handling policy and the duplicate-row
policy are genuine open decisions — `ScientificReadinessResult` blockers,
not invented defaults — until an authority fixes one
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`).

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
      # Manually re-verified against the mounted corpus (`§11.2` below): both the per-class
      # CSV/ tree and the MERGED_CSV/ tree carry exactly 39 feature columns, matching the
      # conference value exactly. This audit's automated SOURCE_INSPECTION run is still the
      # authoritative gate that must execute and persist its own FEASIBILITY_RESULT before any
      # experiment cites it — a manual documentation inspection is corroborating evidence, never
      # a substitute for the pipeline's own check.
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
  # feature count d is source-inspected, never authored; the conference value of 39 is
  # corroborated by manual inspection (`§11.2`) but the processed_feature_verification audit's
  # own run remains the citable gate for any quantitative claim.
```

### 11.2 CICIoT2023 field-level schema

**Source layout (verified against the mounted corpus).** Two parallel
trees under `CIC_IOT_Dataset2023/CSV/`: `CSV/` holds 34 class-labeled
folders (33 attack classes plus `Benign_Final`), each containing one or
more `<Capture>.pcap.csv` per-capture-chunk files — **309 files in total**,
counted directly (matching the shipped `README_CSV.pdf`'s "All 309 .csv
files" statement; an unrelated "169 .csv files" sentence earlier in the
same PDF is leftover boilerplate from a different CIC release and does not
describe this corpus — verified false by direct count, not used).
`MERGED_CSV/` holds exactly **63 files** (`Merged01.csv` … `Merged63.csv`),
matching `DatasetFilePseudoClients.pseudo_client_count: 63` exactly. Per
the dataset authors' own `README.pdf`: "The `MERGED_CSV` folder contains
the same exact data as within each of the attack folders under `CSV`
subfolder, except they have been **merged, shuffled and split** into
multiple files for easy loading into machine learning scripts." **Each of
the 63 files is therefore an arbitrary shuffled slice of the full
34-class distribution, not a naturally distinct capture, source, or
device** — confirmed directly: `Merged01.csv` alone contains rows from all
34 distinct `Label` values. This is the concrete mechanism behind the
roadmap's "near-homogeneous" framing of Regime B-a
(`SCIENTIFIC_FOUNDATION.md §5`): the 63 pseudo-clients are close to i.i.d.
samples of the same mixture, so a threshold-scope effect is not expected to
appear across them, and any effect that did appear would need separate
scrutiny as a possible sampling artifact rather than genuine heterogeneity.

**Row identity, client identity, label.** No row-identity, MAC, device, IP,
or capture-source column exists in either tree — confirmed by header
inspection of both `CSV/` and `MERGED_CSV/` files: neither carries any of
`mac`, `device`, `ip`, `capture`, or a genuine wall-clock timestamp field
(`IAT` is inter-arrival *time delta*, a computed flow feature, not an
absolute timestamp). This directly confirms the roadmap's rejection basis
for `device_mac_repartition` (E-R1) and `chronological_probe_ciciot2023`
(E-R2) from the actual files, not merely from the roadmap's own assertion.
Client identity for `file_pseudo_client_evaluation` is **file-derived
only** (one `MERGED_CSV/MergedNN.csv` file = one pseudo-client). The binary
label is derived from the `Label` column present only in `MERGED_CSV/`
files (`BENIGN` → benign, any of the other 33 values → attack); the
per-class `CSV/` tree instead derives its label from the folder name and
carries no `Label` column at all (39 columns, not 40) — the two trees are
schema-siblings differing by exactly one column, never silently assumed
interchangeable.

**Feature schema (39 columns, per-class `CSV/` tree; verified
byte-identical header across every sampled class folder).** In exact source
order:

```text
Header_Length, Protocol Type, Time_To_Live, Rate, fin_flag_number, syn_flag_number,
rst_flag_number, psh_flag_number, ack_flag_number, ece_flag_number, cwr_flag_number,
ack_count, syn_count, fin_count, rst_count, HTTP, HTTPS, DNS, Telnet, SMTP, SSH, IRC,
TCP, UDP, DHCP, ARP, ICMP, IGMP, IPv, LLC, Tot sum, Min, Max, AVG, Std, Tot size, IAT,
Number, Variance
```

All 39 are `role: MODEL_FEATURE`; canonical field IDs are the
lowercased, space/dot-normalized source names (`Tot sum` → `tot_sum`,
`Protocol Type` → `protocol_type`). `MERGED_CSV/` carries the identical 39
in the identical order, plus a 40th trailing column, `Label`
(`role: MULTICLASS_LABEL`, `inferred_type: CATEGORICAL_STRING`, 34 distinct
values verified in `Merged01.csv`: `BACKDOOR_MALWARE`, `BENIGN`,
`BROWSERHIJACKING`, `COMMANDINJECTION`, ten `DDOS-*` variants,
`DICTIONARYBRUTEFORCE`, `DNS_SPOOFING`, four `DOS-*` variants, three
`MIRAI-*` variants, `MITM-ARPSPOOFING`, four `RECON-*` variants,
`SQLINJECTION`, `UPLOADING_ATTACK`, `VULNERABILITYSCAN`, `XSS`); the binary
`role: BINARY_LABEL` is a pure derivation, `Label == "BENIGN"`, never a
second authored column.

**Verified data-quality findings.**
- **`Std` and `Variance` can be empty (missing), and `Rate` can be the
  literal string `inf`.** Sampled directly in
  `CSV/Benign_Final/BenignTraffic1.pcap.csv`: rows 8940 and 16401 (of a
  20,000-row sample) have `Rate = inf` and `Std = ""`, `Variance = ""` in
  the same row — a degenerate single-packet flow window where the rate
  computation divides by a zero time delta and the variance/std of a
  single sample is undefined. **Preprocessing rule:** `Rate == inf` and
  blank `Std`/`Variance` are a genuine, recurring degenerate-window
  condition, never a transcription error; they require an explicit,
  typed handling policy (e.g. a typed sentinel or row exclusion) before
  numeric materialization — never a silent `0`/`NaN`-fill.
- **Three quasi-constant protocol-indicator columns observed in a
  single-class sample.** `Telnet`, `SMTP`, `IRC` were constant (`0`) across
  the entire 20,001-row `BenignTraffic1.pcap.csv` sample — expected,
  since these are per-protocol presence flags and this capture contains no
  Telnet/SMTP/IRC traffic; not evidence that these columns are globally
  constant across the full 309-file corpus, and never dropped on the
  strength of a single-file sample.
- No non-numeric cell was found outside the `inf`/empty pattern above; no
  duplicate-row check has been run over the full corpus (scale: 8.4–8.7 GB
  per tree) — an open item, not a finding either way.

**Blockers.** Feature-schema identity is verified (closed). Open:
the full-corpus duplicate-row rate; the exact row count and class balance
of every one of the 309 `CSV/` files and 63 `MERGED_CSV/` files (only a
subset was directly inspected); the `Rate`/`Std`/`Variance` degenerate-window
handling policy (`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`).

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
  # The 63-column raw source schema and its 15-column drop list / 7-column dummy-encoding
  # list are verified (`§11.3`); the exact post-encoding input dimension remains BLOCKED
  # because one-hot expansion width is data-dependent (varies with the distinct category
  # values surviving dropna/dedup), never guessed ahead of running the actual preprocessing.
```

### 11.3 Edge-IIoTset field-level schema

**Source layout (verified against the mounted corpus).** Three top-level
roots: `Normal traffic/` (ten sensor-type subfolders, each with one
`<Name>.csv` + one `<Name>.pcap`: `Distance`, `Flame_Sensor`, `Heart_Rate`,
`IR_Receiver`, `Modbus`, `Soil_Moisture`, `Sound_Sensor`,
`Temperature_and_Humidity`, `Water_Level`, `phValue`); `Attack traffic/`
(14 `<Name>_attack.csv`/`.pcap` pairs — `Backdoor`, `DDoS_HTTP_Flood`,
`DDoS_ICMP_Flood`, `DDoS_TCP_SYN_Flood`, `DDoS_UDP_Flood`, `MITM`,
`OS_Fingerprinting`, `Password`, `Port_Scanning`, `Ransomware`,
`SQL_injection`, `Uploading`, `Vulnerability_scanner`, `XSS`); and
`Selected dataset for ML and DL/` (`ML-EdgeIIoT-dataset.csv`,
157,801 rows; `DNN-EdgeIIoT-dataset.csv`, 2,219,202 rows). **All three
roots share the identical 63-column raw header** — confirmed by diffing
`Normal traffic/Distance/Distance.csv`, `Attack traffic/Backdoor_attack.csv`,
and both "Selected" files. Unlike N-BaIoT and CICIoT2023, Edge-IIoTset
ships **raw Wireshark dissector fields, not pre-engineered numeric flow
statistics** — the "Selected dataset for ML and DL" files are a curated
*row selection*, not a feature-engineered artifact; no further-reduced
numeric-only file exists anywhere in the corpus. This is a genuine,
verified raw-versus-processed distinction this dataset alone has among the
three (`SCIENTIFIC_FOUNDATION.md §5` cross-reference).

**Row identity, client/group identity, timestamp, label — all confirmed
present, unlike the other two datasets.** `frame.time` is a genuine capture
timestamp (raw per-sensor files show Wireshark-format strings, e.g.
`" 2021 23:58:21.314757000 "`); `ip.src_host`/`ip.dst_host` are genuine
per-row IP-address identity fields; `Attack_label` is binary (`0`/`1`,
confirmed both values present in the full `ML-EdgeIIoT-dataset.csv`:
133,499 rows labeled `1`, 24,301 labeled `0`); `Attack_type` is the
multi-class label (verified 15 distinct values in the ML file: `Normal`
plus 14 attack types matching the 14 `Attack traffic/` files exactly, with
`DDoS_ICMP`/`DDoS_UDP`/`DDoS_TCP`/`DDoS_HTTP` merged from the
flood-specific file names into shorter type labels). **Group identity is
folder-derived, not `ip.src_host`-derived:** each `Normal traffic/`
sensor-type folder occupies its own distinct `/24` subnet
(`Distance→192.168.1.x`, `Flame_Sensor→192.168.7.x`, `Heart_Rate→192.168.3.x`,
`IR_Receiver→192.168.5.x`, `Modbus→192.168.0.x`, `Soil_Moisture→192.168.8.x`,
`Sound_Sensor→192.168.6.x`, `Water_Level→192.168.4.x`, `phValue→192.168.2.x`;
`Temperature_and_Humidity` is the one exception, dominated by public IPs in
sampling — worth a dedicated feasibility-audit check, not assumed
consistent with the other nine), so the ten sensor-type folder names are a
clean, verified candidate `GROUP_IDENTITY`/device-type taxonomy, while
`ip.src_host` read directly is **not** clean (see below).

**`ip.src_host` is not usable as client identity without cleaning.**
Full-file scan of `ML-EdgeIIoT-dataset.csv` (157,801 rows): 19,090 distinct
`ip.src_host` values, but three IPs (`192.168.0.128`, `192.168.0.170`,
`192.168.0.101`) account for ≈83% of rows, the literal string `"0"`
(a placeholder, not a real address) accounts for 7,991 rows, `"0.0.0.0"`
for 208, and the remaining several thousand distinct values are
long-tail public/incidental IPs each appearing 1–17 times (background
DNS/NTP/CDN traffic, not IoT clients). A naive per-`ip.src_host` client
partition would therefore produce one extreme majority handful of clients
plus thousands of near-singleton pseudo-clients — concretely
demonstrating, from the actual data, why `external_device_validation`'s
device-vs-group granularity is feasibility-gated
(`SCIENTIFIC_FOUNDATION.md §5.1`) rather than assumed.

**Raw schema, 63 columns, in exact source order, classified by role
against the dataset authors' own documented preprocessing recipe**
(`Edge-IIoTset/Readme.txt`, "Step 4: Dropping data" / "Step 5: Categorical
data encoding" — this is the creators' own canonical script, not a DATP-Core
invention):

| # | Source field | Inferred type | Role | Basis |
|---|---|---|---|---|
| 1 | `frame.time` | timestamp_string | `TIMESTAMP` | author-dropped before modeling |
| 2 | `ip.src_host` | ip_address_string | `CLIENT_IDENTITY` | author-dropped before modeling |
| 3 | `ip.dst_host` | ip_address_string | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling |
| 4 | `arp.dst.proto_ipv4` | ip_address_string | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling |
| 5 | `arp.opcode` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 6 | `arp.hw.size` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 7 | `arp.src.proto_ipv4` | ip_address_string | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling |
| 8 | `icmp.checksum` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 9 | `icmp.seq_le` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 10 | `icmp.transmit_timestamp` | numeric_int | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling |
| 11 | `icmp.unused` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 12 | `http.file_data` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 13 | `http.content_length` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 14 | `http.request.uri.query` | free_text | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling; sampled values contain literal SQL-injection payload text |
| 15 | `http.request.method` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot) |
| 16 | `http.referer` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot) |
| 17 | `http.request.full_uri` | free_text | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling; sampled values contain literal SQL-injection/XSS payload text |
| 18 | `http.request.version` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot) |
| 19 | `http.response` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 20 | `http.tls_port` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 21 | `tcp.ack` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 22 | `tcp.ack_raw` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 23 | `tcp.checksum` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 24 | `tcp.connection.fin` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 25 | `tcp.connection.rst` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 26 | `tcp.connection.syn` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 27 | `tcp.connection.synack` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 28 | `tcp.dstport` | numeric_int | `EXCLUDED_HIGH_CARDINALITY` | author-dropped before modeling |
| 29 | `tcp.flags` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 30 | `tcp.flags.ack` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 31 | `tcp.len` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 32 | `tcp.options` | free_text | `EXCLUDED_HIGH_CARDINALITY` | author-dropped before modeling; opaque hex payload |
| 33 | `tcp.payload` | free_text | `EXCLUDED_HIGH_CARDINALITY` | author-dropped before modeling; opaque hex payload |
| 34 | `tcp.seq` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 35 | `tcp.srcport` | numeric_int | `EXCLUDED_HIGH_CARDINALITY` | author-dropped before modeling |
| 36 | `udp.port` | numeric_int | `EXCLUDED_HIGH_CARDINALITY` | author-dropped before modeling |
| 37 | `udp.stream` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 38 | `udp.time_delta` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 39 | `dns.qry.name` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 40 | `dns.qry.name.len` | numeric_int | `MODEL_FEATURE` | author dummy-encodes (one-hot) despite the numeric-looking values |
| 41 | `dns.qry.qu` | numeric_int | `MODEL_FEATURE` | retained by author recipe |
| 42 | `dns.qry.type` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 43 | `dns.retransmission` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 44 | `dns.retransmit_request` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 45 | `dns.retransmit_request_in` | numeric_int | `MODEL_FEATURE` | retained by author recipe (constant `0.0` in sample) |
| 46 | `mqtt.conack.flags` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot); protocol-conditional placeholder `0.0` outside MQTT rows |
| 47 | `mqtt.conflag.cleansess` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 48 | `mqtt.conflags` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 49 | `mqtt.hdrflags` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 50 | `mqtt.len` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 51 | `mqtt.msg_decoded_as` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 52 | `mqtt.msg` | numeric_int | `EXCLUDED_LEAKAGE_RISK` | author-dropped before modeling |
| 53 | `mqtt.msgtype` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 54 | `mqtt.proto_len` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 55 | `mqtt.protoname` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot); protocol-conditional placeholder |
| 56 | `mqtt.topic` | categorical_string | `MODEL_FEATURE` | author dummy-encodes (one-hot); protocol-conditional placeholder |
| 57 | `mqtt.topic_len` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 58 | `mqtt.ver` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 59 | `mbtcp.len` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 60 | `mbtcp.trans_id` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 61 | `mbtcp.unit_id` | numeric_int | `MODEL_FEATURE` | retained by author recipe; protocol-conditional placeholder |
| 62 | `Attack_label` | numeric_int | `BINARY_LABEL` | — |
| 63 | `Attack_type` | categorical_string | `MULTICLASS_LABEL` | — |

**Preprocessing and feature-group rules (author-verified, `Readme.txt`
"Step 4"/"Step 5").** Drop exactly the 15 columns marked
`EXCLUDED_LEAKAGE_RISK`/`EXCLUDED_HIGH_CARDINALITY`/`TIMESTAMP`/
`CLIENT_IDENTITY` above (`frame.time`, `ip.src_host`, `ip.dst_host`,
`arp.src.proto_ipv4`, `arp.dst.proto_ipv4`, `http.file_data`,
`http.request.full_uri`, `icmp.transmit_timestamp`,
`http.request.uri.query`, `tcp.options`, `tcp.payload`, `tcp.srcport`,
`tcp.dstport`, `udp.port`, `mqtt.msg`) — note `http.file_data` is
author-*retained* despite being constant in-sample, and `icmp.transmit_timestamp`
is author-*dropped* despite being numeric, so type alone never determines
exclusion, only the documented role does. One-hot ("dummy") encode exactly
the 7 columns marked "author dummy-encodes" above
(`http.request.method`, `http.referer`, `http.request.version`,
`dns.qry.name.len`, `mqtt.conack.flags`, `mqtt.protoname`, `mqtt.topic`).
Row filter: drop any row with a null in a retained column, then drop exact
duplicate rows, before encoding. The remaining 46 retained non-label
columns (63 − 15 dropped − 2 label) are deterministic and fully verified;
the *final* ordered `model_feature_order` width is not, because one-hot
expansion produces one column per distinct category value that survives
row-filtering — data-dependent, never estimated or guessed ahead of
actually running this pipeline.

**Verified data-quality findings.**
- **`ip.src_host` literal `"0"` and `"0.0.0.0"` placeholders** occur in
  every one of the ten `Normal traffic/` sensor folders (both appear among
  the first five distinct values in every folder checked) — a systematic,
  not incidental, missing-value pattern; never treated as a real address.
- **`frame.time` format is inconsistent between the raw per-sensor files
  and the combined "Selected" files.** Raw `Normal traffic/Distance/Distance.csv`
  carries proper Wireshark timestamp strings (`" 2021 23:58:21.314757000 "`);
  a sampled row of `ML-EdgeIIoT-dataset.csv` carries `frame.time = "6.0"`,
  which is not a valid Wireshark timestamp. Since `frame.time` is dropped
  before modeling regardless (author recipe), this does not affect the
  feature schema, but it **blocks** any temporal-ordering claim
  (`chronological_recalibration_evaluation`'s `capture_time_field`) until
  the actual distribution of malformed values across the corpus is
  characterized by `edge_iiotset_timestamp_semantics_verification`.
- **Many `mqtt.*`/`mbtcp.*` columns are constant (`0.0`) except in rows from
  their own protocol's captures** (`role` notes above) — a genuine,
  systematic protocol-conditional placeholder pattern (confirmed on a
  30,000-row sample of `ML-EdgeIIoT-dataset.csv`), not a defect, but a
  required normalization consideration: these columns' informativeness is
  concentrated in a small row subset and their global variance is
  therefore not representative of their conditional variance.

**Blockers.** Final post-encoding `model_feature_order` width (data-dependent
one-hot expansion, `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`);
`frame.time` malformed-value distribution and true timestamp semantics
(gates `chronological_recalibration_evaluation`); `Temperature_and_Humidity`
folder's subnet-consistency exception (candidate group-identity anomaly,
unresolved); full-corpus duplicate-row rate (only a 30,000-row sample was
checked). Device-vs-group granularity itself remains gated by
`edge_iiotset_client_granularity_feasibility` exactly as already documented
(`SCIENTIFIC_FOUNDATION.md §5.1`) — the `ip.src_host` noise findings above
are additional evidence for why that gate exists, not a resolution of it.

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
