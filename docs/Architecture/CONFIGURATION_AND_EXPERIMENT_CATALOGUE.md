# CONFIGURATION_AND_EXPERIMENT_CATALOGUE

## Purpose

Define boundary ownership, composition, sweeps, registry, CLI, and Make.

## Authoritative for

Configuration schemas and resolution contracts.

## Not authoritative for

Scientific meaning, execution mechanics, or report rendering.

## 1. Configuration documents

```text
configs/
├── datasets/
│   ├── nbaiot.yaml
│   ├── ciciot2023.yaml
│   └── edge_iiotset.yaml
│
├── experiments.yaml
├── protocols.yaml
└── runtime.yaml
```

Six documents and exactly one directory. `datasets/` owns one document per
real dataset, and dataset source schemas are independent enough that they
remain one file per dataset rather than one merged document: each declares
source layout, machine-readable field schema, the source contract, named
materializations — each pairing a normalization, preprocessing sequence,
row-exclusion policy, and split — client-construction setups that reference a
materialization, and the capabilities that setup provides. A dataset document
carries no measured count, category inventory, readiness verdict, or
audit-time field; those are generated evidence and live only in the
consolidated dataset-source audit output.

`protocols.yaml` owns every reusable, execution-independent scientific
definition — model architectures, optimizers, batching, seed cohorts,
checkpoint profiles, training profiles, eligibility policies, threshold
policies, metric bundles, statistical profiles, result types, report profiles,
and operational inputs — each stated exactly once and referenced by a stable
descriptive identifier. `experiments.yaml` owns the study populations, the
capability and suppression vocabularies, and the single experiment catalogue,
each entry independently addressable by a descriptive name. `runtime.yaml`
owns machine and operational execution profiles only — repository-relative
roots, the read-only raw-source policy, and each profile's device policy,
resource budget, concurrency, data-loading chunk size and streaming policy —
and holds no scientific parameter.
`PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md §3` reproduces this identical tree
with per-file schema-module ownership.

There is no `models/`, `experiments/`, `dataset_audits/`, `data_sources/`,
`detectors/`, `catalogues/`, `contracts/`, `profiles/`, `policies/`,
`reporting/`, or `execution.yaml` path anywhere in this design. Their prior
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
| `datasets/<dataset>.yaml` | dataset identity and `schema_id`, source location and integrity, machine-readable field schema (ordered source columns, identity/label fields, ordered model features, leakage exclusions, fingerprint inputs), source-readiness and feasibility audits, client-identity availability, timestamp semantics, named materializations (normalization, preprocessing sequence, row exclusion, split), named client-construction setups that reference a materialization, dataset-specific eligibility rules, required readiness evidence and blockers | `config/schemas/data.py` |
| `models/autoencoder.yaml` | architecture, reconstruction objective, optimizer/scheduler, checkpoint production and selection, scientific training/scoring batches, precision, determinism, and every named `training_profile` (federated averaging, federated proximal, centralized pooled, the authorized personalization comparator) | `config/schemas/model.py` |
| `experiments/<family>.yaml` | one family's scientific identity, evidence role/tier, run requirement, dataset+setup and model+training-profile references, evaluations, analyses, seed cohort, prerequisites, sweeps/bindings, inline report, per-experiment scientific blockers — one entry per experiment, every entry independently resolvable | `config/schemas/experiment.py` |
| `execution.yaml` | every named execution profile: CUDA/CPU requirement, RAM/VRAM/disk/worker/concurrency limits, process-start policy, data-loading chunk size and streaming, prefetch, timeouts, logging/telemetry | `config/schemas/execution.py` |

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
            → expand each experiment catalogue into its independent experiment entries
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
runs scientific computation. Expanding the experiment catalogue into its
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
- `training.profile = federated_averaging` or `federated_proximal` with a
  non-`NONE` personalization strategy on any experiment other than the one
  authorized `model_personalization_absorption_test` slug (which selects the
  dedicated `federated_averaging_personalized` profile, `§7`).
- A FedProx `training.parameters.mu` binding equal to zero, equal to a
  FedAvg-equivalent value, or drawn from anything other than the experiment's
  own pre-registered `federated_proximal_mu` sweep grid `{0.001, 0.01, 0.1}`
  (`§7`); `mu` is no longer a field of the reusable `federated_proximal`
  profile — it is bound per experiment through the discriminated
  `training.parameters`.
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
| Dataset identity, `schema_id`, materialization | Yes | No | Yes | No | Yes |
| `run_requirement` (`MANDATORY`/`OPTIONAL`/`SUPPRESSED`) | No (does not affect a computed value) | No | Yes | Yes (governs whether a result is main-paper or supplement) | Yes |
| publication regime | No — reporting projection only | No | Yes | Yes | No — derived by `derive_publication_regime` |
| Feature schema | Yes | No | Yes | No | Runtime-captured (source-inspected), never authored |
| Client construction (dataset setup), partition seed | Yes | No | Yes | No | Yes |
| Split boundaries (per-materialization: method, fractions, split seed) | Yes | No | Yes | No | Yes |
| Preprocessing & normalization (per-materialization sequence, scope) | Yes | No | Yes | No | Yes |
| Calibration-window selection (`§12` of `DOMAIN_AND_APPLICATION_ARCHITECTURE.md`) | Yes (when populated) | No | Yes | Yes | Yes, only for `calibration_window_size_stability` cells |
| Model architecture (hidden dims, activation) | Yes | No | Yes | No | Yes |
| Optimizer, learning rate | Yes | No | Yes | No | Yes |
| Training rounds (named checkpoint profile) | Yes | No | Yes | No | Yes |
| `rounds_max` | No — derived from the referenced checkpoint profile's rounds | No | Yes | No | No — computed, rejected if authored |
| Local epochs, participation | Yes | No | Yes | No | Yes |
| Micro-batch size, gradient accumulation | Yes | No | Yes | No | Yes |
| `effective_batch_size` | No — derived (`micro_batch_size × gradient_accumulation_steps`) | No | Yes | No | No — computed, rejected if authored |
| Worker count | Conditional (identity-bearing only if ordering/output-affecting) | Yes | Yes | No | Yes |
| Precision, determinism level | Yes | No | Yes | No | Yes |
| Checkpoint-selection rule | Yes | No | Yes | No | Yes (locked; `federated_averaging` on `natural_devices` performs the single `authorization: primary_selection_computed_once_on_regime_a`; `federated_averaging_personalized`, `federated_proximal`, and every other profile that shares the `datp_core` checkpoint profile carry an identical rule string only as an `authorization: lookup_of_federated_averaging_regime_a_primary_selection` — a documented reuse, never an independent per-profile recomputation; `centralized_pooled` alone selects independently, on its own non-federated curve, per `ANCHOR-04`) |
| Threshold construction and its parameters (quantile, K, λ, α) | Yes | No | Yes | Yes (units, direction) | Yes |
| `recalibration_mode` (`FROZEN`/`ONE_SHOT`) | Yes (when populated) | No | Yes | No | Yes, only for `chronological_recalibration_evaluation` evaluations; `None` (unauthored) elsewhere |
| Cluster-count canonicality, clustering `n_init`/`max_iter` | Yes | No | Yes | No | Yes |
| Shrinkage weight | Yes | No | Yes | Yes | Yes |
| Conformal coverage / alpha | Yes | No | Yes | Yes | Yes |
| Eligibility minimum-calibration threshold | Yes | No | Yes | No | Yes, once, on the owning dataset |
| Metric selection | Yes | No | Yes | Yes | Yes |
| Traffic rate (alert burden) | Yes (when requested) | No | Yes | Yes | Yes, when `AlertBurdenEvaluationSuite` is selected |
| `seed_cohort.paired_seed_count`, `seed_cohort.derivation` | Yes | No | Yes | No | Yes |
| `analyses[*].primary_procedure` / `secondary_procedures` | Yes | No | Yes | Yes | Yes; bootstrap `resample_count` is pre-registered at `10000` |
| `analyses[*].statistical_profile` (pairing key, resampling unit, analysis-seed derivation, missing-pair behavior, zero-difference behavior, finite-value validation) | Yes | No | Yes | No | Yes, on every `analyses[*]` entry alongside `primary_procedure` |
| `evaluations[*].requested_metrics` | Yes | No | Yes | Yes | Yes, when narrower than the evaluation's default metric set (e.g. `local_global_threshold_shrinkage`'s `[cv_fpr, p10_macro_f1]`) |
| `regimes[*].limitations` (typed unavailability: `capability`, `status`, `unavailable_reason`) | Yes | No | Yes | Yes | Yes, on every `regime_d`/`regime_d_temporal` cell; owns the enforcement of `per_client_attack_detection_metrics: unavailable` |
| `regimes[*].decision_ref` | No — provenance pointer only | No | Yes | No | Yes, when a regime cites a dataset-level `audits[*].check` as the basis for a limitation (must resolve to a real `check` name, e.g. `client_granularity_feasibility`) |
| Runtime device / CUDA requirement | No | Yes | Yes | No | Yes, once, on the named execution profile |
| GPU model, driver version | No | No | Yes | No | Runtime-captured only |
| RAM / VRAM budget | No | Yes | Yes | No | Yes, once, on the named execution profile |
| Output format | No | No | Yes | Yes | Yes |
| Report ordering | No | No | Yes | Yes | Yes |
| Log interval | No | No | Yes | No | Yes (cosmetic; documented single owner, the execution profile) |

## 7. Discriminated variants

Every multi-shaped field carries an explicit discriminator, never an
inferred shape. Example, client construction (a dataset setup):

```yaml
setups:
  dirichlet_partitioned:
    materialization: datp_core_dirichlet
    client_construction:
      method: dirichlet_partitioned_clients
      client_count: 20
      alpha: { from_sweep: dirichlet_alpha }   # bound by the owning experiment's sweep
      partition_seed: 0
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
    personalization: ditto                 # genuine Ditto, not a renamed FedRep/FedPer (NAME-05)
    personalization_proximal_weight: 1.0
  federated_proximal:
    kind: federated_prox_training
    local_epochs: 1
    participation: full
    personalization: none
    # no literal `mu` here: the FedProx strength is bound per experiment through the
    # discriminated `training.parameters` (below), sweeping the experiment's own
    # pre-registered `federated_proximal_mu` grid {0.001, 0.01, 0.1}
  centralized_pooled:
    kind: centralized_pooled_training
    # not federated; not in the causal ladder (ANCHOR-04)
```

An experiment never re-declares a profile's body; it references a profile by
name and supplies only that profile's own discriminated `training.parameters`
(empty when the profile binds no per-experiment value, populated only for
FedProx's swept `mu`):

```yaml
# FedAvg / personalized / centralized-pooled experiment — no bound parameters
training: { profile: federated_averaging, parameters: {} }

# FedProx experiment — binds mu from its own pre-registered sweep grid
training:
  profile: federated_proximal
  parameters:
    mu: { from_sweep: federated_proximal_mu }
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

`configs/experiments.yaml` holds exactly one experiment entry. The
fragment below is an **abbreviated field-coverage illustration**, not a
verbatim byte-for-byte reproduction — the real file wraps `data`/
`evaluation_scope`/`evaluation_refs`/`analysis_refs`/`prerequisites` in a
`regimes:` list (one `regime_a` entry) and additionally carries an explicit
`roadmap_reference` (`null`, since the anchor is not a numbered roadmap
`E-*` item) and a fully specified two-mode `anchor_equivalence` contract
(`comparison_mode` with `strict_artifact_comparison`/`statistical_fallback`,
`expected_seed_cohort`, `historical_reference` with the individual B1/B2
point values, `checks`, `failure_reasons`, `downstream_blocking_behavior`).
`configs/experiments.yaml` is authoritative for the exact shape;
every scientific value the source documents supply is explicit there, none
defaulted in Python. It references the `anchor` materialization (`§11.1`)
through the `anchor_natural_devices` setup and the `anchor_terminal`
checkpoint profile (one terminal checkpoint at round 150), never the
DATP-Core materialization or round schedule.

```yaml
schema_version: 1
family: anchor
experiments:
  - slug: anchor_reproduction
    display_name: Anchor Reproduction
    evidence_role: anchor
    run_requirement: mandatory
    data: { dataset: nbaiot, setup: anchor_natural_devices }
    model: autoencoder
    checkpoint_profile: anchor_terminal
    training:
      profile: federated_averaging
      parameters: {}
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
          resample_count: 10000
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
      experiment_seed: 0
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

Every anchor-identity value that the source documents supply — evidence
role, dataset+setup, both threshold constructions, the quantile `0.95`, the
five-seed count, the confidence level `0.95`, the bootstrap `resample_count`
`10000`, the `experiment_seed` `0`, and the reference interval
`[0.647, 0.769]` — is explicit here, none defaulted in Python. Nothing in
this draft is a boundary blocker; there is no `anchor: true` switch, because
none is needed. The resolved domain object owns the reference interval
exactly once, in `AnchorEquivalenceAnalysis.reference_interval`.

### 9.1 No dynamic client-construction fallback

Edge-IIoTset external validation is **capability-scoped**, not runtime-selected.
The `client_granularity_feasibility` audit rejects device granularity outright,
so `edge_iiotset.yaml` carries no `external_device` setup; it keeps the benign
`external_group` setup (`granularity: group`, K = 10) and the `chronological`
setup, both now `executable: true` with a declared
`validation_scope` (`benign_operating_point_equity` and
`benign_temporal_operating_point_equity`). Because false-positive metrics need
only held-out benign rows, these setups produce benign calibration, threshold
construction, benign-test FPR, and cross-client FPR dispersion; only per-client
attack-sensitive metrics carry a typed `per_client_attack_detection_metrics:
unavailable` limitation (`attack_traffic_confined_to_subnet_zero`, `§11.3`). The
`external_sensor_group_validation` experiment is therefore
`run_requirement: mandatory` with `evaluation_scope:
benign_operating_point_equity` (`§16.3`). The no-runtime-fallback principle is
unchanged: no scientific experiment's configuration ever contains a runtime rule
choosing between device clients, group clients, or a pseudo-client fallback; the
group granularity is fixed and human-authored, so the circular dependency this
package removes never returns.

## 10. Threshold-scope experiment family

`configs/experiments.yaml` groups the confirmatory endpoint
with its two direct construction/quantile rule-outs — the experiments the
roadmap ties most tightly to the B1-vs-B2 pair (Tier 1 and its immediate
Tier 2 defenses). As in `§9`, the fragments below are **abbreviated
field-coverage illustrations**: the real file wraps each experiment's
`data`/`evaluation_scope`/`evaluation_refs`/`analysis_refs`/`prerequisites`
in a `regimes:` list and additionally carries a `statistical_profile` block
(pairing key, resampling unit, analysis-seed derivation, missing-pair and
zero-difference behavior, finite-value validation) alongside every
`primary_procedure`; `configs/experiments.yaml` is
authoritative for the exact shape. From here on, a flow-style
`report: { table_type: …, … }` is shorthand for the single-entry
`report_artifacts` list worked in full in `§9` (`report: { report_artifacts:
[{ artifact_type: main_table, table_type: …, … }], wording_outcomes: […] }`);
every resolved `ReportDefinition` still carries the complete
`report_artifacts`/`wording_outcomes` shape, only the prose in this document
is compressed:

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
    checkpoint_profile: datp_core
    training:
      profile: federated_averaging
      parameters: {}
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
          resample_count: 10000
        statistical_profile: { pairing_key: seed, resampling_unit: per_seed_paired_delta, analysis_seed_derivation: deterministic_from_experiment_seed_and_analysis_label, missing_pair_behavior: exclude_and_report_reduced_seed_count, zero_difference_behavior: retain_as_zero_delta_included_in_resample, finite_value_validation: reject_non_finite_delta_as_typed_error }
        secondary_procedures:
          - { method: wilcoxon_signed_rank }
          - { method: matched_pairs_rank_biserial_correlation }
    seed_cohort:
      paired_seed_count: 10
      derivation: deterministic_from_experiment_seed
      experiment_seed: 0
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
    checkpoint_profile: datp_core
    training:
      profile: federated_averaging
      parameters: {}
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
        primary_procedure: { method: bca_bootstrap, confidence_level: 0.95, resample_count: 10000 }
        secondary_procedures: []
    seed_cohort:
      paired_seed_count: 10
      derivation: deterministic_from_experiment_seed
      experiment_seed: 0
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
    checkpoint_profile: datp_core
    training:
      profile: federated_averaging
      parameters: {}
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
      experiment_seed: 0
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

Datasets no longer carry a `dataset_version` field. Each dataset authors a
semantic `schema_id` (identifying its verified field schema) plus a
`materializations:` map — one entry per distinct normalization + preprocessing
sequence + row-exclusion + split combination — and named `setups` that each
reference a materialization by name. Where a dataset genuinely needs more than
one processed form (N-BaIoT's DATP-Core versus historical `anchor`
materialization, `§11.1`), each is a named materialization, never a version
counter. Chunk sizes and streaming are no longer dataset fields; they live per
execution profile in `execution.yaml` (`data_loading: { chunk_row_count: N,
streaming: true }`, `§13`).

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

`configs/datasets/nbaiot.yaml` — the sole N-BaIoT document, owning its
machine-readable schema, three materializations, and three client-construction
setups (the full 115-column `model_features.order` and 9-entry `family_map`
are authored verbatim in the file; both are elided here for brevity):

```yaml
schema_version: 1
dataset: nbaiot
display_name: N-BaIoT
schema_id: nbaiot_kitsune_115
source_layout:
  root: N-BaIoT
  device_dirs: [Danmini_Doorbell, Ecobee_Thermostat, Ennio_Doorbell, ...]   # 9 device directories
  benign_file: benign_traffic.csv
  attack_family_dirs: [gafgyt_attacks, mirai_attacks]
field_schema:
  source_column_count: 115
  identity_scheme:
    row_identity: { components: [source_file_path, source_row_index], index_scope: within_source_file }
    client_identity: { source: path, derived_from: device_directory_name }
    label_identity: { source: path, benign_rule: file_is_benign_traffic_csv, attack_rule: file_under_attack_family_dir }
    timestamp_field: none
  label_fields:
    family_taxonomy: device_type
    family_map: { Danmini_Doorbell: doorbell, Ennio_Doorbell: doorbell, Provision_PT_838_Security_Camera: camera, Ecobee_Thermostat: other, ... }   # doorbell | camera | other
  model_features: { role: model_feature, type: numeric_float, order: [MI_dir_L5_weight, ..., HpHp_L0.01_pcc] }   # 115 ordered Kitsune columns
  post_encoding_feature_order: same_as_model_features
  categorical_encoding: none
  leakage_exclusions: []
observed_facts: { device_count: 9, devices_without_mirai_family: [Ennio_Doorbell, Samsung_SNH_1011_N_Webcam], benign_exact_duplicate_rate: 0.07633 }
readiness: { source_schema_complete: true, feature_schema_verified: true, per_device_membership_recoverable: true }
eligibility:
  minimum_calibration_sample_count: 100
materializations:
  datp_core:
    materialization_id: nbaiot_datp_core
    normalization: { strategy: min_max, scope: global_train }
    preprocessing_sequence: [drop_cold_start_row, drop_exact_duplicate_rows, chronological_gapped_split, min_max_normalization_fit_on_train]
    row_exclusion: { cold_start_row: drop_first_row_per_source_file, duplicate_rows: drop_exact_duplicates_keep_first }
    split: { method: chronological_gapped, calibration_benign_only: true, ratios: { train: 0.60, gap_1: 0.01, calibration: 0.20, gap_2: 0.01, test: 0.18 } }
  datp_core_dirichlet:
    materialization_id: nbaiot_datp_core_dirichlet
    normalization: { strategy: min_max, scope: global_train }
    preprocessing_sequence: [drop_cold_start_row, drop_exact_duplicate_rows, random_fractional_split, min_max_normalization_fit_on_train]
    row_exclusion: { cold_start_row: drop_first_row_per_source_file, duplicate_rows: drop_exact_duplicates_keep_first }
    split: { method: random_fractional, calibration_benign_only: true, split_seed: 0, ratios: { train: 0.70, calibration: 0.15, test: 0.15 } }
  anchor:
    materialization_id: nbaiot_anchor_historical
    normalization: { strategy: standard, scope: global_train }   # StandardScaler, recovered from the DATP reference project
    preprocessing_sequence: [chronological_gapped_split, standard_normalization_fit_on_train]
    row_exclusion: { cold_start_row: retain, duplicate_rows: retain }   # raw rows retained: no cold-start drop, no dedup
    split: { method: chronological_gapped, calibration_benign_only: true, ratios: { train: 0.60, gap_1: 0.01, calibration: 0.20, gap_2: 0.01, test: 0.18 } }
setups:
  natural_devices:        { materialization: datp_core,           client_construction: { method: physical_device_clients, device_count: 9 } }
  anchor_natural_devices: { materialization: anchor,              client_construction: { method: physical_device_clients, device_count: 9 } }
  dirichlet_partitioned:
    materialization: datp_core_dirichlet
    client_construction:
      method: dirichlet_partitioned_clients
      client_count: 20
      alpha: { from_sweep: dirichlet_alpha }
      iid_endpoint: { alpha_label: iid, allocation: equal_across_source_domains }
      source_mixture_components: nine_physical_device_domains
      label_field: physical_device_domain
      partition_seed: 0
      partition_seed_independent_of_training_seeds: true
      allocation_procedure: dirichlet_draw_per_synthetic_client_over_nine_source_domain_proportions
      same_proportions_govern: [benign_train_rows, benign_calibration_rows, benign_test_rows, attack_evaluation_rows]
      split_role_preservation: each_source_domain_row_keeps_its_pre_partition_split_role
      attack_row_assignment: allocated_by_same_per_client_source_domain_proportions_as_benign_rows
      attack_labels_used_in_partition_generation: false
      minimum_row_counts: { train: 100, calibration: 100, test: 50 }
      retry_policy: { behavior: deterministic_reseed_retry, max_retries: 10, retry_seed_derivation: partition_seed_plus_attempt_index }
      feasibility_failure: typed_infeasibility_outcome_if_minimum_row_counts_unmet_after_max_retries
      manifest: { fields: [client_count, alpha, partition_seed, per_client_source_domain_proportions, per_client_row_counts, retry_attempts_used, feasibility_status], fingerprint: blake3_over_manifest_fields }
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
  error: it reproduces on every file checked. **Preprocessing rule (now
  resolved per materialization):** the DATP-Core `datp_core` and
  `datp_core_dirichlet` materializations drop row 1 of every raw N-BaIoT file
  before model-feature materialization; the historical `anchor` materialization
  retains it (raw pass-through). It is never averaged, scaled, or calibrated
  against under the DATP-Core materializations, because its `HH_jit_*_mean`
  values are off-scale by roughly nine orders of magnitude relative to every
  other row.
- **Low-rate exact-duplicate rows.** `Ecobee_Thermostat/benign_traffic.csv`
  (13,113 rows) contains 2 exact-duplicate rows (0.015%); no non-numeric or
  empty cell and no constant column were found in the same file. Duplicate
  handling is now explicit per materialization: the DATP-Core materializations
  drop exact duplicates (keep first), while the `anchor` materialization
  retains them.
- **No missing/non-numeric cells** were found in any sampled file beyond
  the row-1 artifact above; every cell parses as a finite float.

**Materializations and blockers.** Feature-schema identity is verified
(closed by inspection). The row-1 cold-start and duplicate-row policies are no
longer open decisions: the DATP-Core `datp_core`/`datp_core_dirichlet`
materializations min-max normalize (fit on train), drop the cold-start row,
and deduplicate; the `anchor` materialization is a **distinct historical
materialization** recovered from the DATP reference project — StandardScaler
normalization with raw rows retained (no cold-start drop, no dedup) —
reproducing the original anchor pipeline exactly. The two never share a
materialization, a normalizer, or a terminal state, which is why the anchor
experiment binds `anchor_natural_devices` + `anchor_terminal` while DATP-Core
binds `natural_devices` + `datp_core` (`§9`, `§12`).

`configs/datasets/ciciot2023.yaml` — boundary-role dataset, carrying its
feature-count re-verification audit and one `datp_core` materialization (the
full 39-column `model_features.order` is authored verbatim in the file;
elided here for brevity):

```yaml
schema_version: 1
dataset: ciciot2023
display_name: CICIoT2023
schema_id: ciciot2023_flow_39
source_layout:
  root: CIC_IOT_Dataset2023/CSV
  per_class_root: CIC_IOT_Dataset2023/CSV/CSV
  merged_root: CIC_IOT_Dataset2023/CSV/MERGED_CSV
field_schema:
  source_column_count: { per_class: 39, merged: 40 }
  identity_scheme:
    row_identity: { components: [source_file_path, source_row_index], index_scope: within_source_file }
    client_identity: { source: file, derived_from: merged_file_name }
    label_identity: { source: column, column: Label, present_in: merged_only }
    timestamp_field: none
    device_mac_ip_field: none
  label_fields:
    multiclass_label: { column: Label, type: categorical_string }
    binary_label: { derivation: label_equals_benign, benign_value: BENIGN }
  model_features: { role: model_feature, type: numeric_float, order: [Header_Length, "Protocol Type", ..., Variance] }   # 39 ordered flow features
  post_encoding_feature_order: same_as_model_features
  categorical_encoding: none
  leakage_exclusions: [Label]
observed_facts: { pseudo_client_count: 63, per_class_file_count: 309, model_feature_count: 39, merged_excess_duplicate_rate: 0.53340, device_mac_ip_capture_timestamp_columns_present: false }
readiness: { source_schema_complete: true, processed_feature_count_verified: true }
eligibility:
  minimum_calibration_sample_count: 100
materializations:
  datp_core:
    materialization_id: ciciot2023_datp_core
    role: primary
    normalization: { strategy: min_max, scope: global_train }
    preprocessing_sequence: [exclude_degenerate_window_rows, compute_global_exact_duplicate_equivalence_classes, assign_each_equivalence_class_to_one_split, drop_non_canonical_equivalence_class_members, random_fractional_split, min_max_normalization_fit_on_train]
    row_exclusion:
      degenerate_window: exclude_rate_inf_or_blank_std_variance
      duplicate_equivalence_class_scope: global_across_all_63_files
      duplicate_equivalence_class_split_assignment: whole_class_to_one_split_never_crosses_train_calibration_test
      canonical_row_provenance_preserved: true
    split: { method: random_fractional, calibration_benign_only: true, split_seed: 0, ratios: { train: 0.70, calibration: 0.15, test: 0.15 } }
    reporting: [removed_rows, retained_rows_per_pseudo_client, client_eligibility_changes, pseudo_client_coverage]
    infeasibility_policy: typed_boundary_result_if_dedup_removes_experiment_feasibility
  datp_core_duplicate_preserving_sensitivity:
    materialization_id: ciciot2023_datp_core_duplicate_preserving_sensitivity
    role: sensitivity_only_never_primary
    normalization: { strategy: min_max, scope: global_train }
    preprocessing_sequence: [exclude_degenerate_window_rows, drop_exact_duplicate_rows_per_file, assign_cross_file_duplicate_equivalence_classes_to_one_split, random_fractional_split, min_max_normalization_fit_on_train]
    row_exclusion: { degenerate_window: exclude_rate_inf_or_blank_std_variance, within_file_duplicate_policy: drop_exact_duplicates_keep_first_per_file, cross_file_duplicate_policy: retain_across_pseudo_clients, cross_file_duplicate_split_assignment: whole_equivalence_class_to_one_split_consistent_across_pseudo_clients }
    split: { method: random_fractional, calibration_benign_only: true, split_seed: 0, ratios: { train: 0.70, calibration: 0.15, test: 0.15 } }
setups:
  file_pseudo_clients:
    materialization: datp_core
    client_construction: { method: dataset_file_pseudo_clients, pseudo_client_count: 63 }
  file_pseudo_clients_duplicate_sensitivity:
    materialization: datp_core_duplicate_preserving_sensitivity
    client_construction: { method: dataset_file_pseudo_clients, pseudo_client_count: 63 }
    execution_requirement: optional
    publication_placement: supplementary
```

The primary materialization computes exact-duplicate equivalence classes
**globally** across all 63 files and assigns each whole class to exactly
one split, so no equivalence class crosses train/calibration/test; it
reports removed rows, retained rows per pseudo-client, client eligibility
changes, and pseudo-client coverage, and yields a typed boundary result if
deduplication removes experiment feasibility rather than being silently
dropped. `datp_core_duplicate_preserving_sensitivity` — the prior per-file/
cross-client-retaining behavior — survives only as an explicitly optional,
supplementary sensitivity materialization, per its own split-assignment
constraint (`§5` requirement: a duplicate-preserving variant is permitted
only when each equivalence class is still wholly assigned to one split).

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
  duplicate-row check has been run over the raw per-class `CSV/` tree (309
  files, scale 8.4–8.7 GB) — an open item, not a finding either way, and not
  the tree the executable materialization reads.

**Blockers.** Feature-schema identity is verified (closed). Open: the raw
per-class `CSV/` tree's duplicate-row rate and the exact row count/class
balance of every one of the 309 `CSV/` files (only a subset was directly
inspected; not read by the executable materialization). The executable
`MERGED_CSV/` tree's global candidate-duplicate rate **is** measured
(`observed_facts.merged_excess_duplicate_rate: 0.53340`) and feeds the
`datp_core` primary materialization's global equivalence-class
deduplication (`§11.1`) directly; it is not an open item. Also open: the
`Rate`/`Std`/`Variance` degenerate-window handling policy
(`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`).

`configs/datasets/edge_iiotset.yaml` — the external-validation dataset. Its
`client_granularity_feasibility` audit rejects device granularity, so it owns
**no `external_device` setup**; it keeps a benign `external_group` setup and a
`chronological` setup, both `executable: true` with a declared `validation_scope`
(`benign_operating_point_equity` / `benign_temporal_operating_point_equity`),
because false-positive metrics need only held-out benign rows while attack
traffic is confined to subnet 0 (the full 63-column source schema and 39-entry
`retained_numeric_features.order` are authored verbatim in the file; elided
here for brevity):

```yaml
schema_version: 1
dataset: edge_iiotset
display_name: Edge-IIoTset
schema_id: edge_iiotset_wireshark_63
source_layout:
  root: "Edge-IIoTset dataset"
  normal_group_folders: [Distance, Flame_Sensor, Heart_Rate, IR_Receiver, Modbus, Soil_Moisture, Sound_Sensor, Temperature_and_Humidity, Water_Level, phValue]   # 10 sensor-type groups
  attack_files: [Backdoor_attack.csv, ..., XSS_attack.csv]   # 14 attack-type files, no group column
field_schema:
  source_column_count: 63
  identity_scheme:
    row_identity: { components: [source_file_path, source_row_index], index_scope: within_source_file }
    benign_group_identity: { source: path, derived_from: normal_traffic_group_folder }
    attack_row_group_identity: unavailable
    device_identity: { source: column, column: ip.src_host, usable: false }
    timestamp_field: { column: frame.time, semantics: time_of_day_no_month_day }
  label_fields:
    binary_label: { column: Attack_label, values: [0, 1] }
    multiclass_label: { column: Attack_type }
    family_taxonomy: unavailable                 # no family/B3 taxonomy on Edge-IIoTset
  attack_row_group_assignment:
    available: false
    reason: attack_traffic_confined_to_subnet_zero
    decision_ref: client_granularity_feasibility
    evidence: >-
      Direction-normalized internal-endpoint resolution over all four endpoint fields (keyed on
      the paper TABLE VI subnet topology) resolves 99.95% of the 9,729,709 attack rows to a
      single subnet: subnet 0 (Temperature/Modbus), the /24 hosting the Kali attacker and its
      victim. No attack row carries any subnet 1-8 endpoint. The ten benign sensor-group client
      folders resolve to only nine distinct /24 subnets, because Modbus is dual-homed (subnets 0
      and 7) and is therefore excluded from this clean per-subnet accounting; of the remaining
      nine cleanly-resolved groups, eight (all but Temperature_and_Humidity, subnet 0) receive
      zero attack rows. This subnet-level accounting does not change the authorized K = 10
      static benign client-group count. See endpoint_identity.
  endpoint_identity:                             # direction-normalized resolution; benign confirmed, attack subnet-0 confined
    resolution: direction_normalized_internal_endpoint
    subnet_to_group: { 0: [Temperature_and_Humidity, Modbus], 1: Distance, 2: phValue, 3: Heart_Rate, 4: Water_Level, 5: IR_Receiver, 6: Sound_Sensor, 7: [Flame_Sensor, Modbus], 8: Soil_Moisture }
    excluded_endpoints: { attacker: [192.168.0.170, 192.168.0.152], ambiguous_dual_role: [192.168.0.101], placeholder: ["0", "0.0.0.0"], public_external: spoofed_flood_or_incidental_background }
    resolved_coverage: { attack: { resolved_subnets: [0] }, clients_with_benign_and_attack: 1, joint_client_coverage_ratio: 0.11 }   # 1 of the 9 cleanly-resolved (Modbus-excluded) subnet groups
    verdict: benign_group_identity_confirmed_attack_partition_infeasible
  retained_numeric_features: { role: model_feature, type: numeric_float, count: 39, order: [arp.opcode, ..., mbtcp.unit_id] }
  categorical_encoding:
    strategy: one_hot
    columns: [http.request.method, http.referer, http.request.version, dns.qry.name.len, mqtt.conack.flags, mqtt.protoname, mqtt.topic]   # 7 columns
    retained_numeric_feature_count: 39
    vocabulary_scope: benign_training_rows_only        # historical_benign_train for the chronological materialization
    vocabulary_fit_split: benign_train                 # historical_benign_train (chronological)
    vocabulary_artifact: frozen_at_materialization_fit_time
    vocabulary_fingerprint: derived_from_fitted_benign_train_categories
    category_order: ascending_string
    encoded_feature_naming: "{column}={category_value}"
    missing_category_policy: absent_value_maps_to_missing_indicator
    unknown_category_policy: unseen_value_maps_to_unknown_indicator   # distinct indicator from missing
    unknown_reporting: { unknown_counts_by_split: reported_at_fit_time, unknown_fractions_by_client: reported_at_fit_time }
    full_corpus_audit_reference:                        # audit observation only, never the executable vocabulary
      encoded_feature_count: 76
      total_model_feature_count: 115           # 76 dummies + 39 numeric; superseded by the benign-train-only fit at execution
      category_values: { <per-column, enumerated over the full corpus (benign+attack), audit reference only> }
    categorical_vocabulary_benign_fit_audit:            # re-derives per-column widths and total_model_feature_count from a benign-only fit
      status: pending_execution
  leakage_exclusions: { columns: [frame.time, ip.src_host, ip.dst_host, ...], role_basis: leakage_or_high_cardinality_or_client_identity_or_timestamp }   # 15 dropped
readiness:
  source_schema_complete: true
  benign_group_partition_recoverable: true
  benign_endpoint_identity_recoverable: true
  eligible_benign_client_coverage_ratio: 1.0
  fpr_scope_evaluation_executable: true
  benign_temporal_fpr_evaluation_executable: true
  attack_sensitive_per_client_evaluation_executable: false
  attack_row_group_assignment_recoverable: false
  external_validation_mode: benign_operating_point_equity
evaluation_capabilities:
  benign_test_false_positive_metrics: { status: available, supported_metrics: [fpr, cv_fpr, iqr_fpr, fpr_range, worst_client_fpr, jain_index, gini_coefficient] }
  threshold_scope_dispersion: { status: available }
  benign_score_distribution_analysis: { status: available }
  conformal_benign_coverage: { status: available }
  per_client_attack_detection_metrics: { status: unavailable, reason: attack_traffic_confined_to_subnet_zero, unsupported_metrics: [tpr, cv_tpr, recall, macro_f1, p10_macro_f1, balanced_accuracy, worst_client_ba, auroc] }
  attack_sensitive_threshold_tradeoff: { status: unavailable, reason: attack_traffic_confined_to_subnet_zero }
audits:
  - { check: source_inspection, ... }
  - check: client_granularity_feasibility
    outcome: { device_granularity: rejected, resolved_endpoint_granularity: benign_only, group_granularity: authorized_benign_only, group_count: 10, joint_benign_attack_partition: infeasible, benign_operating_point_equity_executable: true, attack_sensitive_per_client_evaluation_executable: false }
    # ...inspection + feasibility as before
  - check: timestamp_semantics_verification
    outcome: { within_client_ordering: time_of_day_with_midnight_rollover_correction, cross_client_wall_clock_ordering: unavailable, temporal_group_count: 9, excluded_groups: [Modbus] }
    # ...
eligibility:
  minimum_calibration_sample_count: 100
materializations:
  group_benign:
    materialization_id: edge_iiotset_group_benign
    normalization: { strategy: min_max, scope: global_train }
    vocabulary_fit_split: benign_train
    preprocessing_sequence: [drop_row_with_null_in_retained_column, drop_exact_duplicate_rows, one_hot_encode_categoricals, min_max_normalization_fit_on_train]
    split: { method: random_fractional, calibration_benign_only: true, split_seed: 0, ratios: { train: 0.70, calibration: 0.15, test: 0.15 } }
  group_chronological:
    materialization_id: edge_iiotset_group_chronological
    normalization: { strategy: min_max, scope: historical_train }
    vocabulary_fit_split: historical_benign_train
    preprocessing_sequence: [drop_row_with_null_in_retained_column, drop_exact_duplicate_rows, resolve_within_client_time_order, chronological_split, one_hot_encode_categoricals, min_max_normalization_fit_on_historical_train]
    row_exclusion: { unresolved_row_policy: excluded_from_client_assignment, duplicate_timestamp_policy: preserve_original_row_order_stable_sort }
    split:
      method: within_client_chronological
      calibration_benign_only: true
      role_order: [historical_train, historical_calibration, future_recalibration, future_evaluation]
      historical_train_fraction: 0.55
      historical_calibration_fraction: 0.15
      future_recalibration_fraction: 0.10
      future_evaluation_fraction: 0.20
      ordering_field: frame.time
      ordering_scope: per_client
      rollover_policy: add_twenty_four_hours_on_time_decrease
      minimum_row_counts: { historical_train: 100, historical_calibration: 100, future_recalibration: 50, future_evaluation: 100 }
      missing_client_policy: exclude_client_report_reduced_k
      chronology_unverifiable_policy: typed_infeasibility_outcome
    static_reference: { note: matched static reference over the same nine temporal groups (Modbus excluded) via group_benign, materialization_ref: group_benign }
    recovery_analysis:
      fields: [static_reference_cv, frozen_future_cv, recalibrated_future_cv, drift_excess, recovered_amount, recovery_ratio]
      drift_excess_formula: frozen_future_cv - static_reference_cv
      recovered_amount_formula: frozen_future_cv - recalibrated_future_cv
      recovery_ratio_formula: recovered_amount / drift_excess
      recovery_ratio_precondition: drift_excess_meaningfully_positive
      negative_recovery_policy: report_as_is_no_floor_clamp
      outcome_thresholds: { outcome_a_recovery_ratio_min: 0.50, outcome_b_recovery_ratio_max: 0.50, outcome_c_condition: no_meaningful_positive_drift_excess }
      seed_analysis: paired_seed_ci_over_locked_seed_cohort
      confidence_interval_procedure: bca_bootstrap_95
setups:
  external_group:
    materialization: group_benign
    client_construction: { method: external_group_clients, group_count: 10 }
    executable: true
    validation_scope: benign_operating_point_equity
    supported_capabilities: [benign_calibration, benign_test_false_positive_metrics, threshold_scope_dispersion, benign_score_distribution_analysis, conformal_benign_coverage]
    unsupported_capabilities: [per_client_attack_detection_metrics, attack_sensitive_threshold_tradeoff]
    limitation: { capability: per_client_attack_detection_metrics, status: unavailable, reason: attack_traffic_confined_to_subnet_zero }
  chronological:
    materialization: group_chronological
    client_construction: { method: external_group_clients, group_count: 9, excluded_groups: [Modbus] }
    temporal_window: { role: temporal_evaluation, historical_train_fraction: 0.55, historical_calibration_fraction: 0.15, future_recalibration_fraction: 0.10, future_evaluation_fraction: 0.20, capture_time_field: frame.time, ordering_derivation: time_of_day_with_midnight_rollover_correction }
    executable: true
    validation_scope: benign_temporal_operating_point_equity
    supported_scope: [historical_benign_training, historical_benign_calibration, future_benign_fpr_evaluation, frozen_vs_one_shot_recalibrated_thresholds, cv_fpr_drift_and_recovery]
    unsupported_scope: [per_client_temporal_tpr, temporal_macro_f1, temporal_balanced_accuracy, attack_sensitive_temporal_recovery]
    limitation: { capability: per_client_attack_detection_metrics, status: unavailable, reason: attack_traffic_confined_to_subnet_zero }
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
folder-derived, and now independently confirmed from the endpoint IPs:**
a direction-normalized full-corpus audit (below) resolves each `Normal traffic/`
sensor-type folder to its own distinct `/24` subnet
(`Distance→192.168.1.x`, `phValue→192.168.2.x`, `Heart_Rate→192.168.3.x`,
`Water_Level→192.168.4.x`, `IR_Receiver→192.168.5.x`, `Sound_Sensor→192.168.6.x`,
`Flame_Sensor→192.168.7.x`, `Soil_Moisture→192.168.8.x`,
`Temperature_and_Humidity→192.168.0.x`; `Modbus` spans `192.168.0.x` (client)
and a dominant `192.168.7.x` (server), overlapping both `Temperature_and_Humidity`
and `Flame_Sensor`). The earlier note that `Temperature_and_Humidity` was
"dominated by public IPs" was a small-sample artifact: over the full corpus it
is a clean subnet-0 folder whose 17% non-resolving rows are MAC-address source
values, not public IPs. So the ten sensor-type folder names are a clean,
verified candidate `GROUP_IDENTITY`/device-type taxonomy, while
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
demonstrating, from the actual data, why `external_sensor_group_validation`'s
sensor-group granularity is feasibility-gated
(`SCIENTIFIC_FOUNDATION.md §5.1`) rather than assumed.

**Reopened full-corpus endpoint audit (direction-normalized).** Because the
single-field `ip.src_host` view above is confounded by spoofed flood sources,
MAC-address rows, and the attacker's own address, the feasibility question was
reopened over the **complete** corpus (11,209,913 benign rows across the ten
folders; 9,729,709 attack rows across the fourteen files) using **all four**
endpoint fields (`ip.src_host`, `ip.dst_host`, `arp.src.proto_ipv4`,
`arp.dst.proto_ipv4`) with **direction normalization** — each row is reduced to
one internal endpoint, preferring the non-attacker `192.168.X.Y` address, keyed
on the dataset paper's TABLE VI testbed topology (the third octet identifies the
sensor `/24`). This resolves benign client identity **directly from the data**:
97.5% of benign rows resolve to their own sensor subnet (≈99.99% per folder
except `Temperature_and_Humidity`, whose 17% MAC-address source rows are
unresolvable), independently confirming the folder taxonomy.

**Attack traffic is confined to the attacker's subnet — the decisive
suppression evidence.** Every attack row resolves to **one** subnet: subnet 0
(`192.168.0.x`, Temperature/Modbus), the `/24` hosting both the Kali attacker
`192.168.0.170` (present in 1,586,635 attack rows) and its primary victim
`192.168.0.128` (9,724,050 attack rows). Only 0.048% of attack rows are
unresolved (chiefly MITM/ARP MAC rows), and **no attack row carries any subnet
1–8 endpoint in any of the four fields** — verified exhaustively across all
fourteen files. The DDoS floods spoof public source IPs (ICMP 77% public,
TCP-SYN 52%), but direction normalization recovers the internal victim
`192.168.0.128` and still resolves them to subnet 0. Per-client joint coverage:

| Sensor client (subnet) | Benign rows | Attack rows |
|---|---|---|
| 0 Temperature_and_Humidity / Modbus | 1,341,883 | 9,725,008 |
| 1 Distance | 1,143,398 | 0 |
| 2 phValue | 746,618 | 0 |
| 3 Heart_Rate | 165,206 | 0 |
| 4 Water_Level | 2,295,078 | 0 |
| 5 IR_Receiver | 1,307,660 | 0 |
| 6 Sound_Sensor | 1,512,754 | 0 |
| 7 Flame_Sensor / Modbus-server | 1,225,711 | 0 |
| 8 Soil_Moisture | 1,192,245 | 0 |

Exactly **one** of the nine sensor clients (subnet 0) ever receives attack
traffic — joint benign+attack coverage 1/9 ≈ 11%, far below the ≥ 90%
eligibility gate. Three partition strategies were audited and all fail:
(1) **resolved internal-endpoint clients** — eight of nine clients have zero
attack test rows; (2) **source-grounded endpoint/service groups containing both
benign and attack rows** — only subnet 0 qualifies, a single group that cannot
form a multi-client dispersion ladder; (3) **controlled non-IID synthetic
clients** — would require fabricating attack traffic for subnets 1–8 that have
none, and would misrepresent Regime D's sensor-group-partitioned external-validation
claim (RQ6) while duplicating Regime C's heterogeneity role. No source-grounded
multi-client benign+attack partition exists, so per-client attack-sensitive
metrics are unavailable. But false-positive metrics require only held-out benign
rows — recoverable for all ten sensor groups (eligible-benign coverage 1.0) — so
Regime D and D-temporal are **executable for benign operating-point equity**
(`CV(FPR)` and its benign-derivable companions); only their attack-sensitive
per-client metrics carry a typed `per_client_attack_detection_metrics:
unavailable` limitation (`attack_traffic_confined_to_subnet_zero`), never a
deleted cell and never a fabricated mapping. The benign endpoint mapping,
evaluation capabilities, and the excluded attacker/placeholder/public/malformed
values are recorded machine-readably in `edge_iiotset.yaml`
(`field_schema.endpoint_identity`). `Modbus` benign traffic is itself split
across subnet 0 (client, 3,455 rows) and subnet 7 (server, 155,614 rows),
overlapping both `Temperature_and_Humidity` and `Flame_Sensor`, so an
IP-subnet client identity would also silently merge those folders — a further
reason the folder-derived benign grouping, not a subnet client id, is the
authorized benign taxonomy.

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
duplicate rows, before encoding. The 39 retained numeric non-label columns
and the 7 one-hot-encoded columns are deterministic and fully verified; the
one-hot expansion has now been measured on the mounted corpus at 76 dummy
columns, for `39 + 76 = 115` total model features. The exact post-encoding
column *names* are now authored deterministically as `{column}={category_value}`
from the enumerated per-column category vocabulary (full corpus, benign+attack,
ascending-string order; unknown/missing values map to an all-zero indicator), and
the total width is no longer a blocker.

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

**Capability scope and blockers.** The post-encoding model-feature width is
resolved (`39 + 76 = 115`; names authored deterministically as `{column}={category_value}` from the enumerated per-column category vocabulary). The decisive finding is
that **external validation is capability-scoped, not suppressed**: a reopened
direction-normalized full-corpus endpoint audit confirms benign client identity
directly from the endpoints (each sensor folder maps to its own `/24`,
eligible-benign coverage 1.0), while **all attack traffic resolves to the single
attacker subnet 0** (Temperature/Modbus) — no attack row carries any subnet 1–8
endpoint, so eight of the nine sensor clients receive zero attack rows. Because
false-positive metrics need only held-out benign rows, the `external_group` and
`chronological` setups are `executable: true` for benign operating-point equity
(`CV(FPR)` and its benign-derivable companions); only per-client attack-sensitive
metrics carry a typed `per_client_attack_detection_metrics: unavailable`
limitation (`attack_traffic_confined_to_subnet_zero`). The audit records
`device_granularity: rejected`, `group_granularity: authorized_benign_only`
(K = 10), `joint_benign_attack_partition: infeasible`, and
`benign_operating_point_equity_executable: true`; no `family_taxonomy` exists, so
the B3 family threshold is not authored on Edge-IIoTset. Remaining open items are
corroborating, not gating: the `frame.time` malformed-value distribution (in the
combined "Selected" files only; the per-sensor captures the campaign uses are
well-formed) and the full-corpus duplicate-row rate
(only a 30,000-row sample was checked). The `Temperature_and_Humidity`
subnet-consistency question is resolved — it is a clean subnet-0 folder (see
above).

## 12. Reusable model configuration

`configs/protocols.yaml` — the one model family, carrying every
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
checkpoint_profiles:
  datp_core:
    rounds: [25, 50, 75, 100, 125, 150, 200]
  anchor_terminal:
    rounds: [150]
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
    personalization: ditto                 # genuine Ditto, not a renamed FedRep/FedPer (NAME-05)
    personalization_proximal_weight: 1.0
    checkpoint_selection:
      rule: lowest_federated_averaging_weighted_benign_validation_reconstruction_error
      tie_break: earliest_scheduled_round
  federated_proximal:
    kind: federated_prox_training
    local_epochs: 1
    participation: full
    personalization: none
    # no literal `mu`: bound per experiment via training.parameters (§7),
    # sweeping the federated_proximal_mu grid {0.001, 0.01, 0.1}
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
epoch, full participation, the two named checkpoint profiles
(`datp_core` = `{25,50,75,100,125,150,200}`, `anchor_terminal` = `{150}`),
batch size `256`, one gradient-accumulation step, `FP32`, strict
determinism, and genuine Ditto personalization
(`personalization_proximal_weight: 1.0`) — is given explicitly in the source
architecture's resolved-implementation-decisions record; none is invented.
FedProx `mu` is no longer a model field: it is bound per experiment from the
`federated_proximal_mu` sweep grid `{0.001, 0.01, 0.1}` (`§7`). `rounds_max`
and `effective_batch_size` (`256`) are never authored here — both are pure
derivations (`DOMAIN_AND_APPLICATION_ARCHITECTURE.md §3.2`) computed after
this document resolves; `rounds_max` is the maximum of the *referenced*
checkpoint profile's rounds, so it is `200` for a `datp_core` experiment but
`150` for the anchor's `anchor_terminal` profile — the anchor and DATP-Core
do not share a terminal round, checkpoint set, or terminal state. Eligibility (`minimum_calibration_sample_count = 100`) is **not**
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

`configs/runtime.yaml` — every named profile in one file, shown as a
non-resolvable draft until the authority supplies its operational limits:

```yaml
schema_version: 1
profiles:
  scientific:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 10, max_vram_gib: 12 }
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 4 }
    data_loading: { chunk_row_count: 50000, streaming: true }
    process_start_method: spawn           # locked rule for any CUDA-touching stage
    log_interval_rounds: 25
  print_grade:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 10, max_vram_gib: 12 }
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 4 }
    data_loading: { chunk_row_count: 50000, streaming: true }
    process_start_method: spawn
    log_interval_rounds: 25
  development:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 8, max_vram_gib: 8 }
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 2 }
    data_loading: { chunk_row_count: 10000, streaming: true }
    process_start_method: spawn
    log_interval_rounds: 5
  smoke:
    device_policy: cuda_required
    determinism: strict
    resource_budget: { max_ram_gib: 6, max_vram_gib: 6 }
    concurrency: { training_concurrency: 1, scoring_concurrency: 1, worker_count: 1 }
    data_loading: { chunk_row_count: 1000, streaming: true }
    process_start_method: spawn
    log_interval_rounds: 1
  dataset_audit:
    device_policy: cpu_only          # audits touch no CUDA stage; fork is permitted for CPU-only workers
    determinism: strict
    resource_budget: { max_ram_gib: 8 }
    concurrency: { worker_count: 4 }
    data_loading: { chunk_row_count: 50000, streaming: true }
    process_start_method: fork
    log_interval_rounds: 10
  test_smoke:
    device_policy: cpu_only          # test-only; resolves storage beneath TEST_SANDBOX; never scientific evidence
    determinism: strict
    resource_budget: { max_ram_gib: 4 }
    concurrency: { worker_count: 1 }
    data_loading: { chunk_row_count: 1000, streaming: true }
    process_start_method: spawn
    log_interval_rounds: 1
```

`process_start_method: spawn` is not fabricated: it follows directly from
the source architecture's fixed rule that any stage touching CUDA must use a
spawn context established before any CUDA call in the parent process, never
the global `set_start_method`. Each profile now supplies complete operational
limits, including its own data-loading chunk size and streaming flag; no field
is a boundary blocker. Every
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
one `configs/experiments.yaml` document, a `family` name, and an
`experiments` list of independently resolvable entries, each carrying either
`data` (dataset + setup) or a `regimes:` list of regime cells, `model` +
`checkpoint_profile` + a `training` block (`profile` + `parameters`),
`evaluations`, optional `sweep`, `analyses`, `seed_cohort`, `prerequisites`,
and `operations` (`execution` profile name + inline `report`). Only the
identity-bearing content that differs from `§§9–10` is given here; no field
family, blocker, or scientific value described elsewhere in this package is
altered by moving an experiment into a family file.

### 16.1 `heterogeneity.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `controlled_heterogeneity_response` | E-S3 | supportive; tier_2 | `nbaiot` / `dirichlet_partitioned` | `dirichlet_alpha ∈ {0.1, 0.3, 0.5, 1.0, 10.0, iid}` | carries the heterogeneity–threshold-benefit association (formerly E-M4) as an attached `metric_association_analysis` regressing pairwise JS divergence against `cv_fpr_delta`; carries a benign-FPR-scope `regime_d` regime (`edge_iiotset`/`external_group`, `evaluation_scope: benign_operating_point_equity`) realizing the roadmap "+ Regime D points" seam; report: `severity_trend` figure + `scatter` figure |

### 16.2 `calibration_mechanisms.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `cluster_mechanism` | E-M1/E-M2/E-Q2 | mechanism; tier_5 (+tier_7 exploratory) | `nbaiot` / `natural_devices`; benign-FPR-scope `regime_d` regime (`edge_iiotset`/`external_group`, B1/B2/B4, `family` excluded) | `fingerprint_feature_subset` (4 subsets) | one merged experiment, four typed axes: grouping (`family_threshold` vs `cluster_threshold`), fingerprint feature set, aggregation (`mean`/`robust_median`), authorized K (canonical `3`, mandatory; other K exploratory); report: `cluster_stability` table + `contingency` table |
| `calibration_window_size_stability` | E-V1 | boundary; tier_6 (RQ3) | `nbaiot` / `natural_devices` | `calibration_sample_count ∈ {50,100,250,500,1000,5000}` | each point resolves a `CalibrationSubsetDefinition`; includes `calibration_size_aware_fallback_threshold`; report: `sensitivity_grid` |
| `local_global_threshold_shrinkage` | E-V2 | supportive; RQ3 | `nbaiot` / `natural_devices` | `shrinkage_weight ∈ {0, .25, .5, .75, 1}` | report: `lambda_curve` figure |
| `conformal_local_threshold_coverage` | E-V3 | supportive; `tier_2` (`supports_confirmatory_tautology_defense: tier_1`, never `tier: tier_1` itself — Tier 1 is reserved exclusively for the confirmatory claim, `SCI-14`) | `nbaiot` / `natural_devices`; benign-FPR-scope `regime_d` regime (`edge_iiotset`/`external_group`, benign coverage only) | — | `coverage_alpha = 0.05`; rank `= min(ceil((n+1)*(1-alpha)), n)`, tie-break nearest higher order statistic, `minimum_sample_count: 100`; reports marginal sample-weighted / macro-client / per-client coverage and coverage-target error; exchangeability assumed within-client, not verified across clients; typed unavailable below the minimum sample count; report: conformal coverage table |

### 16.3 `external_validation.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Sweep | Notes |
|---|---|---|---|---|---|
| `external_sensor_group_validation` | E-X1 | external_validation; tier_3; **benign-FPR scope** | `edge_iiotset` / `external_group` (device granularity rejected) | `threshold_quantile = .95` (pinned; q-sweep owned by E-S2) | `run_requirement: mandatory`, `evaluation_scope: benign_operating_point_equity` (`§9.1`, `§11.3`); B1–B4 + matched-summary request FPR-family metrics only (no B3, no attack-sensitive metrics — typed `per_client_attack_detection_metrics: unavailable`); report: `external_validation_interval` table_type (distinct from the confirmatory-only `confirmatory_interval` reserved for `anchor_reproduction`/`confirmatory_threshold_scope_effect`, `EVALUATION_REPORTING_AND_PROVENANCE.md §9.4`) |
| `chronological_recalibration_evaluation` | E-B1 | boundary; tier_6; **benign-temporal-FPR scope** | `edge_iiotset` / `chronological` | — | `run_requirement: mandatory`, `evaluation_scope: benign_temporal_operating_point_equity` (defensible within-client benign ordering); frozen vs one-shot recalibration on benign FPR; per-client temporal attack metrics unavailable; report: `recovery_curve` figure |

### 16.4 `training_stress_tests.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Training profile | Notes |
|---|---|---|---|---|---|
| `fedprox_aggregation_stress_test` | E-T1 | stress_test; tier_4 | `regimes:` — `regime_a` (`nbaiot`/`natural_devices`, run) + `regime_d` (`edge_iiotset`/`external_group`, benign operating-point equity) | `federated_proximal` with `training.parameters.mu` bound from the `federated_proximal_mu` grid (`§7`, `§14`) | one experiment, no top-level `data:`; report: `stress_test` table |
| `model_personalization_absorption_test` | E-T2 | stress_test; tier_4 | `regimes:` — `regime_a` (`nbaiot`/`natural_devices`, run) + `regime_d` (`edge_iiotset`/`external_group`, benign operating-point equity) | `federated_averaging_personalized` (genuine Ditto) | one experiment, no top-level `data:`; its `AbsorptionAnalysis` reuses the confirmatory experiment's FedAvg core delta by cross-experiment reference, never retraining it; report: `stress_test` table |

### 16.5 `references_and_boundaries.yaml`

| Slug | Roadmap ref | Role; tier | Dataset + setup | Training profile | Notes |
|---|---|---|---|---|---|
| `centralized_pooled_reference` | B0 | supportive; mandatory wherever cited | `nbaiot` / `natural_devices` | `training_profiles.centralized_pooled` | own centralized identity chain; never fused with federated artifacts (`ANCHOR-04`, `ART-06`); report: `dispersion_ladder` |
| `federated_summary_comparator` | E-T3/E-Q1/E-Q5 | stress_test (comparator); tier_4 | `regimes:` — `regime_a` (`nbaiot`/`natural_devices`, run) + `regime_d` (`edge_iiotset`/`external_group`, benign operating-point equity) | `federated_averaging` | merged: matched benign-summary comparison (`mode: matched_exceedance`, `matched_exceedance_k_grid_step: 0.01`, mandatory primary — E-T3), quantile-estimation-error backbone analysis (`execution_requirement: optional`, `publication_placement: supplementary`, matching the roadmap's Tier-7/Supplement status for E-Q1, `§5.7`, `§9.3`), and a `mode: fixed_k` evaluation with a scalar `fixed_k: { from_sweep: federated_summary_fixed_k }` over `{2.0, 2.5, 3.0}` carrying `execution_requirement: optional`, `publication_placement: supplementary` (`SCI-18`, E-Q5); report: `comparator` table |
| `operational_alert_burden` | E-O1 | supportive; tier_5; **conditional on a valid cited traffic rate** | `regimes:` — `regime_a` (`nbaiot`/`natural_devices`) + `regime_d` (`edge_iiotset`/`external_group`, benign operating-point equity) | `federated_averaging` | `cited_traffic_rate.status: not_configured` — no rate is invented; the `alert_burden_per_device` analysis produces a typed `omitted` outcome per SB-20 until a real/cited rate (value, unit, citation identifier, source title, source metadata, applicability statement; finite and non-negative) is configured; report: `alert_burden` table |
| `file_pseudo_client_applicability_boundary` | `B_A_APPLICABILITY_BOUNDARY` | boundary; tier_6 | `ciciot2023` / `file_pseudo_clients` (global-dedup primary materialization; `file_pseudo_clients_duplicate_sensitivity` is an optional duplicate-preserving sensitivity variant) | `training_profiles.federated_averaging` | boundary report only, never generalized; report: `boundary_null` table |

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
supplementary evaluation). Expanding the experiment catalogue into its
independent entries (`§3`) and expanding a sweep into its coordinates are
the same class of pure, boundary-only expansion; neither introduces a
second composition mechanism.

## 18. Blocked-value handling, worked

`anchor_reproduction` (`§9`) now supplies every scientific value it needs —
`analyses[0].primary_procedure.resample_count: 10000` and
`seed_cohort.experiment_seed: 0` are both present — so it resolves, plans, and
runs under the `scientific` execution profile without a boundary blocker. The
mechanism that would reject an incomplete draft is unchanged: were either
field removed, `ScientificReadinessResult` would reject the draft before any
network, CUDA, or storage resource is touched, name the missing field, cite
the blocker table in `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §7`, and
propose no substitute value. A reduced profile such as `development` or
`smoke` is non-citable because of execution mode, never because of an
incomplete configuration.

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
list` enumerates every registered experiment name). A name is unique across
the whole catalogue; the CLI never
needs a file path, because the one catalogue document holds every experiment
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
meaningful for it, addressed by name regardless of where in the catalogue
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
| `external-validation` | `external_sensor_group_validation` | validate, plan, run, status, report (benign operating-point equity; per-client attack-sensitive metrics unavailable — `§9.1`) |
| `fedprox-stress-test` | `fedprox_aggregation_stress_test` | plan, run, status, report |
| `personalization-stress-test` | `model_personalization_absorption_test` | plan, run, status, report |
| `federated-summary-comparator` | `federated_summary_comparator` | validate, plan, run, status, report |
| `temporal-recalibration` | `chronological_recalibration_evaluation` | validate, plan, run, status, report (benign temporal operating-point equity; per-client temporal attack metrics unavailable — `§9.1`) |
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
	datp-core experiment plan --config external_sensor_group_validation
external-validation-run:
	datp-core experiment run --config external_sensor_group_validation
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
existing catalogue entry. Concretely: adding a new dataset means one new
`configs/datasets/<name>.yaml` document, no edit to `models/autoencoder.yaml`
or any `configs/experiments.yaml` family; adding a new threshold construction
means a new discriminated `threshold.policy` arm plus its implementation,
with every existing experiment entry untouched because none references the
new policy; adding a new experiment means one new entry appended to the
catalogue entry whose scientific role it matches, referencing existing
dataset/setup and model/training-profile identities, never a new planner or
executor branch (`PROJECT_STRUCTURE_AND_MODULE_CATALOGUE.md §7`,
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §9.2`).
