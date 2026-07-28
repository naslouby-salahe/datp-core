# DATP-Core Aggressive Configuration Elimination and Full Adaptation

## Mission

Work directly in:

`/home/naslouby/Projects/datp-core`

Aggressively reduce the authored and resolved configuration system to the smallest configuration surface that genuinely controls executable behavior.

This is not a cosmetic YAML cleanup. Delete the complete vertical slice of every unnecessary field:

`YAML key → authored schema field → resolver logic → resolved record field → validator → fingerprint projection → drift support → reporting/freezing support → fixture → test`

Do not preserve compatibility with the current configuration format. Do not introduce aliases, deprecated fields, migrations, adapters, translation layers, ignored keys, fallback parsing, or legacy fixtures.

Do not commit or push anything.

Continue through audit, implementation, testing, scientific verification, and cleanup until every acceptance criterion is satisfied. Do not stop after producing an inventory or partial refactor.

## Scientific authority

Before changing anything, read the complete `roadmap/` folder, including:

* `roadmap/00_ROADMAP_INDEX.md`
* `roadmap/01_SCIENTIFIC_IDENTITY_AND_SCOPE.md`
* `roadmap/02_CLAIMS_AND_DECISION_RULES.md`
* `roadmap/03_EXPERIMENT_CATALOGUE.md`
* `roadmap/04_EVALUATION_AND_REPORTING_PROTOCOL.md`
* `roadmap/05_IMPLEMENTATION_ROADMAP.md`
* `roadmap/06_REVIEWER_RISKS_AND_READINESS.md`
* `roadmap/07_AUDIT_AND_DECISION_LOG.md`
* `roadmap/SCIENTIFIC_SOURCE_OF_TRUTH.md`

Also read:

`/home/naslouby/Projects/datp-core/docs/DATP-Core Simplification.md`

Treat these files as the scientific authority and scope boundary. They are not a source of configuration prose to copy back into YAML or Python.

Keep the roadmap files read-only unless an actual factual contradiction caused by this refactor requires a minimal correction. Do not rewrite or expand them.

Preserve all locked scientific behavior, including:

* the fixed-model threshold-calibration identity;
* benign-only calibration;
* attack rows reserved for evaluation;
* FedAvg as the core training baseline;
* `E=1` where locked;
* full participation where locked;
* the B1/B2/B3/B4 policy meanings;
* per-client FPR dispersion as the primary operating-point concern;
* AUROC as a model-quality control rather than the threshold verdict;
* seed meanings and paired-seed semantics;
* experiment dependencies and confirmatory boundaries;
* dataset capability limitations;
* checkpoint-selection discipline;
* no test-set-driven selection;
* Dagster as the canonical orchestrator.

Do not invent scientific values, seeds, thresholds, formulas, partition rules, dataset properties, or fallback behavior.

## Core configuration rule

A configuration value is permitted only when changing that value is intended to alter executable behavior without changing source code.

A field must be deleted when any of the following is true:

1. It is descriptive prose.
2. It documents a claim, limitation, scope boundary, manuscript role, interpretation, or reporting sentence.
3. It repeats behavior already encoded in code.
4. It repeats an enum member, class identity, discriminator, result type, or implementation name.
5. It merely asserts a fixed invariant that the owning implementation must enforce.
6. It is derivable from another configured value.
7. It is derivable from a list length, identifier, selected implementation, schema, model type, or dataset adapter.
8. It is only copied into another model.
9. It is only serialized into a result or manifest.
10. It is only included in a fingerprint or drift projection.
11. It is only read by a catalogue-description command.
12. It exists only because a test expects it.
13. It is only used to generate an explanatory error message.
14. It represents a fixed dataset fact already known by the corresponding adapter or schema.
15. It represents an algorithmic formula already implemented by the owning function.
16. It is a validation declaration whose rule is already enforced or should be enforced directly by code.
17. It is a count that can be computed from the actual collection.
18. It is an authored-to-resolved pass-through with no semantic transformation.
19. It is an optional field that no production execution path consumes.
20. It is an unused aspirational control that the code does not enforce.

A field does not become legitimate merely because it is included in a fingerprint, validation report, frozen result, drift report, debug description, or test fixture.

Do not create a fake runtime consumer merely to justify keeping a field.

Do not move deleted prose into:

* another YAML file;
* Python constants;
* enum documentation;
* class or function docstrings;
* source comments;
* manifests;
* report profiles;
* frozen metadata;
* test data;
* README tables.

Delete it.

## Values that may remain

Retain only values proven to affect execution, such as:

* external paths and source file patterns that genuinely vary;
* selected dataset, materialization, setup, experiment, policy, or profile identifiers;
* model dimensions and real numerical hyperparameters;
* optimizer numerical parameters;
* batching sizes and accumulation values;
* actual split ratios and seeds;
* quantiles, thresholds, cluster counts, sweep values, and materiality thresholds;
* experiment dependencies that alter scheduling;
* evaluation bindings;
* actual analysis inputs;
* statistical method, confidence level, and resample count when consumed;
* resource constraints that are genuinely enforced;
* runtime concurrency values that are genuinely consumed;
* output roots and execution profile selection.

Even these must be deleted when they are fixed by the selected typed implementation and are not intended to vary independently.

Do not replace removed configuration with hidden defaults. A truly variable value remains explicitly required. A fixed invariant belongs exactly once in its owning implementation or type.

## Mandatory starting deletion set

This list is a starting point, not the full scope. Audit every remaining leaf key.

### Dataset configuration

Aggressively remove descriptive and duplicated dataset fields, including candidates such as:

* `display_name` when it is only presentation metadata;
* `source_contract`;
* `fingerprint_inputs`;
* `client_identity_contract`;
* source `owns`;
* source `permitted_uses`;
* `contributes_rows_to_executable_materializations`;
* `defines_pseudo_clients`;
* descriptive cross-source relationship declarations;
* identity prose and provenance descriptions already encoded by adapters;
* `role` and `type` values that merely restate the containing structure;
* `semantics`;
* `reason`;
* `consequence`;
* `use`;
* `validation_scope`;
* `client_semantics`;
* `split_row_semantics`;
* `infeasibility_policy` when no branch consumes it;
* `post_encoding_feature_order: same_as_model_features`;
* derived source-column, feature, client, and folder counts;
* header assertions already enforced by schemas;
* partition assertions already enforced by materializers;
* duplicate and row-integrity descriptions already enforced by code;
* preprocessing sequences that merely narrate a hardcoded materializer pipeline;
* row-exclusion descriptions that do not dispatch behavior;
* capability declarations that can be derived from the selected typed adapter/setup;
* manifest-field lists that merely document what the code already writes.

Dataset-specific executable facts already owned by `NBaIoTAdapter`, `CICIoT2023Adapter`, `EdgeIIoTsetAdapter`, Pandera schemas, materializers, source contracts, or typed dataset definitions must not also remain in YAML.

Do not remove an actual source path, feature selection, label binding, split value, or partition parameter until its real consumer has been identified.

### Experiment configuration

Delete metadata copied into `ExperimentRecord` without an execution reader, including:

* `validation_scope`;
* `never_promoted_to_confirmatory`;
* `outside_core_causal_ladder`;
* `faithful_reproduction_claim_forbidden`;
* `attack_sensitive_metrics_requested`;
* `unavailable_capability_reporting`;
* `method_naming_rule`;
* `run_condition` when it is not executed;
* `blocks_other_experiments_when_unavailable` when it is not executed;
* `client_semantics_constraint`;
* `generalization_constraint`;
* `quantitative_claim_gate`;
* `population_equivalence_requirement`;
* `population_roles`;
* `scope_constraint`;
* `temporal_procedure`;
* `primary_coefficient_selection` when only preserved as metadata;
* `independent_of_experiment` when it does not alter planning;
* descriptive `unavailable_behavior`;
* presentation-only `display_name`;
* any `evidence_role` value that does not alter execution, validation, freezing, or campaign behavior.

Do not retain fields solely because they are included in the scientific fingerprint.

Keep only experiment fields required to construct the real DAG, bind populations and profiles, expand sweeps, select evaluations and analyses, enforce prerequisites, or execute reporting.

### Analysis configuration

Audit every analysis subtype independently. Do not preserve a common bloated base merely because some fields are used by one analysis family.

Delete fields that are only descriptive, copied, or redundantly validated, including:

* `result_type` where `kind` and typed result discriminators already determine the result;
* the top-level `result_types` registry when it exists only to validate evidence-role prose;
* `secondary_statistical_profile` when no procedure consumes it;
* `delta_orientation` when the calculation already defines the orientation;
* `delta_interpretation`;
* `required_direction` when not enforced;
* `monotonicity_required` when not enforced;
* `ordering_inversion_reporting`;
* `full_curve_reporting`;
* `post_hoc_weight_selection`;
* `absorption_metric` when the handler determines it;
* `band_interpretation`;
* `matching_contract` when it is not enforced;
* configured outcome-band prose;
* `outcome_bands_are_mutually_exclusive_and_exhaustive`;
* `alternative_path_rule`;
* `per_client_reporting_required` when not consumed;
* `comparison_mode_rule`;
* unused floating-point tolerance mappings;
* configured failure-reason lists;
* `downstream_blocking_behavior` when campaign behavior is already typed;
* unused analysis-level `run_requirement`;
* `grouping_dimension` when not consumed;
* temporal recovery formula strings;
* temporal precondition descriptions;
* recovery-direction descriptions;
* configured temporal outcome-band prose;
* `interpretation_constraint` when it is only copied into output;
* `produced_fields` when the handler/result type already determines the fields;
* formula strings that are merely copied into result objects.

Where formulas are executable, the implementation is authoritative. Do not configure the same formula as a sentence and then compare it to a code constant.

Each analysis record should contain only the inputs required by its handler.

Remove analysis fields from:

* authored models;
* resolved models;
* resolvers;
* handler signatures;
* result models;
* validators;
* projections;
* fixtures;
* tests;
* report rendering.

### Protocol configuration

Aggressively remove protocol prose and unused records.

Audit and trim:

* global `capabilities` when an enum or adapter registry is authoritative;
* `suppression_behaviors` when runtime behavior is already typed;
* `population_readiness_rule` prose;
* `analysis_conventions`;
* `result_types`;
* `evaluation_result_contract`;
* `report_defaults`;
* unused eligibility declarations;
* normalization formula descriptions;
* metric formulas already implemented in evaluation code;
* metric units and directions already owned by metric enums;
* configured metric status lists already owned by `MetricStatus`;
* configured forbidden-substitution prose;
* threshold `construction` descriptions;
* `threshold_ownership`;
* duplicated nominal coverage or target-exceedance fields;
* policy `mode` fields duplicated by the discriminated policy class;
* candidate-grid payload descriptions;
* byte-order descriptions when byte width is all that is used;
* model-exchange formula strings;
* checkpoint-content descriptions;
* checkpoint byte-formula strings;
* report format descriptions not consumed by renderers;
* selection-scope prose;
* forbidden-selector lists that code already enforces;
* model architecture construction descriptions;
* activation-placement descriptions fixed by the model class;
* decoder descriptions fixed by the model class;
* anomaly-score descriptions fixed by scoring code;
* optimizer lifecycle prose;
* aggregation formula prose;
* client-ordering prose already enforced by implementation;
* participation descriptions duplicated by concrete federation settings;
* derived effective batch size;
* seed-count fields derived from seed lists;
* analysis-seed-model prose;
* deterministic-algorithm prose already implemented in seed utilities;
* nested-replicate declarations that no analysis reads;
* statistical-profile prose not consumed by the selected procedure.

For statistical profiles, retain only actual consumed controls. For example, a bootstrap profile may need:

* method;
* confidence level;
* resample count;
* correction method if actually used;
* minimum sample count if actually enforced.

Do not retain twenty narrative properties around those four controls.

### Runtime configuration

Trace every runtime field to an actual execution read.

Delete complete unused sections rather than preserving aspirational controls, particularly candidates such as:

* raw-source policy declarations with no runtime reader;
* device-policy rules that do not affect device selection;
* resource-pressure rules that are not enforced;
* inactive concurrency dimensions;
* unused RAM and VRAM budgets;
* unused streaming flags;
* unused process-start declarations;
* unused logging intervals;
* unused atomic-write declarations when storage is always atomic;
* temporary-storage descriptions;
* determinism fields that are fingerprinted but never applied;
* recorded-environment field lists that are never recorded.

Do not wire an unused field into production merely to keep it. Delete the field and its model.

Preserve CUDA requirements, determinism controls, resource limits, or concurrency only when the runtime actually applies them.

### Fingerprints and drift

Rebuild scientific and execution projections around executable state only.

Do not call `model_dump()` over large resolved records when that includes unused metadata.

Create narrow typed projections that contain only actual scientific or execution controls.

A change to wording, labels, descriptions, claim prose, report prose, error text, or presentation metadata must not change the scientific fingerprint.

A change to a real seed, split, quantile, threshold policy, model hyperparameter, training profile, evaluation binding, or statistical procedure must change the correct fingerprint.

Update drift tooling to compare only the new minimal projections.

Authored YAML drift may still report differences between currently valid authored documents, but no compatibility with the deleted schema is required.

### Reporting, freezing, manifests, and CLI

Remove deleted metadata from:

* frozen results;
* experiment summaries;
* result packages;
* reports;
* manifest models;
* audit records;
* CLI catalogue descriptions;
* config descriptions.

Do not retain a field because it makes an output “more descriptive.” Scientific and reporting prose belongs in the roadmap and manuscript layer.

Reports should derive stable labels from typed identifiers where needed.

## Architecture and implementation rules

### No backward compatibility

Do not add:

* aliases;
* deprecated names;
* compatibility properties;
* legacy parsing;
* old-to-new converters;
* redirects;
* re-export modules;
* migration commands;
* ignored extra fields;
* permissive schemas;
* fallback lookup paths;
* dual-format fixtures.

Old keys must fail strict validation as unknown fields.

Delete obsolete code completely.

### Typed design

Use:

* `StrEnum` or `Enum` for closed vocabularies;
* discriminated Pydantic models for true variants;
* typed value objects for identifiers and constrained numbers;
* immutable tuples for ordered fixed collections;
* typed registries where dynamic lookup is necessary;
* Polars, Pandera, Pydantic, and existing standard libraries rather than custom boilerplate.

Do not use raw strings for closed protocol state.

Do not use `Any`.

Do not use untyped `dict` or `Mapping[str, object]` in domain/configuration code.

At unavoidable serialization or third-party boundaries, isolate conversion to one small boundary and immediately return to typed models. Do not leak dictionaries through the application.

Do not use reflection, `getattr`, string-based dispatch, or nested `.get()` chains to replace typed fields.

### Defaults and constants

Do not introduce hidden defaults.

Remove optional fields and default factories that exist only to tolerate incomplete configuration.

A value is either:

* required because it genuinely varies; or
* absent from configuration because it is a fixed implementation invariant.

Do not duplicate a fixed invariant as a configurable string.

Do not introduce unexplained raw literals. Use the owning enum, value object, typed policy, or algorithm implementation.

### Code cleanup

No comments or explanatory docstrings in touched production code.

Do not add comments, banner comments, audit comments, migration notes, TODOs, “temporary” explanations, or AI-style narration.

Remove stale, obvious, or descriptive comments and docstrings from every touched production file.

Delete:

* dead imports;
* unused enums;
* empty wrappers;
* one-method indirection with no architectural value;
* duplicate models;
* pass-through resolver functions;
* redundant authored/resolved layers;
* obsolete validators;
* obsolete errors;
* unused CLI commands;
* empty files and unnecessary packages;
* tests that only assert deleted structure.

Merge files or models when doing so reduces indirection without mixing unrelated responsibilities.

Do not create new packages unless a clear capability boundary requires them.

Dagster remains the canonical orchestrator.

### No mass editing

Do not use broad search-and-replace scripts, generated rewrites, or regex-based mass mutation.

Changes must be semantically reviewed by configuration family and owning capability.

Read-only audit scripts are permitted only under `.tmp/`. Delete them at completion.

### Preexisting issues

Preexisting issues discovered during this work are in scope.

Do not dismiss a failure because it existed before the refactor.

Fix related and repository-wide issues surfaced by:

* tests;
* Ruff;
* Pyright;
* Pylance;
* Pylint;
* import-linter;
* SonarCloud;
* CodeScene;
* runtime diagnostics;
* scientific audits.

Pay particular attention to:

* raw dictionaries and mappings;
* `type: ignore` suppressions;
* stringly typed state;
* duplicated models;
* optional-field supersets;
* hidden defaults;
* dead configuration records;
* fingerprint pollution;
* unused runtime controls;
* copied formula strings;
* result metadata with no consumer;
* repeated Python iteration over Polars frames where vectorization is possible;
* boilerplate that an existing dependency can replace;
* comments and docstrings in touched files;
* values duplicated between code and configuration.

Do not alter scientific behavior merely to satisfy static analysis.

## Parallel execution

Use at least six parallel subagents whenever the environment supports them.

Maintain at least these independent workstreams:

1. Dataset YAML, dataset authored models, dataset resolution, adapters, materializers, and dataset tests.
2. Experiment catalogue, sweeps, evaluations, planning, campaign execution, and experiment tests.
3. Threshold, training, optimizer, batching, checkpoint, and seed protocols.
4. Metrics, statistics, eligibility, operational analysis, reporting, and result contracts.
5. Runtime configuration, fingerprints, drift, CLI, freezing, and manifests.
6. Cross-cutting typing, dead-code removal, test adaptation, and scientific equivalence audits.

Use additional subagents for:

* static-analysis cleanup;
* full test review;
* Dagster diagnostics;
* SonarCloud and CodeScene;
* final scientific drift audit.

Avoid overlapping edits without coordination. The main agent owns integration and final verification.

## Required execution loop

Repeat this loop until all acceptance criteria pass:

1. Read.
2. Inventory.
3. Classify.
4. Plan.
5. Implement one coherent deletion slice.
6. Adapt consumers.
7. Adapt or delete tests.
8. Run impacted checks.
9. Audit scientific behavior.
10. Reinspect remaining configuration.
11. Replan.
12. Continue.

Do not stop after one pass. Perform at least six independent final audits.

## Phase 1 — Baseline capture

Before editing:

1. Record the current configuration file list, line counts, byte counts, non-empty key counts, and model-field counts.
2. Run strict configuration loading and validation.
3. Resolve the complete project configuration.
4. Capture the scientific and execution fingerprints.
5. Compile every experiment.
6. Capture every experiment DAG and ordered stage/job coordinates.
7. Capture all populations, datasets, materializations, training profiles, seed cohorts, checkpoint profiles, threshold policies, evaluations, analyses, sweeps, and prerequisites.
8. Run the existing impacted configuration/planning tests.
9. Run one-seed isolated diagnostics where currently possible.
10. Store baseline audit material only under `.tmp/config-trim-baseline/`.

Do not treat the old fingerprint as an equivalence target because it is polluted by descriptive fields. Instead, construct a temporary executable-behavior projection for comparison.

The temporary projection must include only values that actually affect:

* data ingestion;
* materialization;
* splitting;
* normalization;
* training;
* checkpoint selection;
* scoring;
* calibration subsampling;
* threshold construction;
* evaluation;
* statistical analysis;
* reporting paths;
* stage planning.

Delete the temporary baseline material after final verification.

## Phase 2 — Exhaustive leaf-key consumer graph

Enumerate every YAML leaf key across all configuration files.

For each leaf, record temporarily:

* YAML path;
* authored model field;
* resolver;
* resolved field;
* production readers;
* validators;
* fingerprint inclusion;
* tests;
* classification;
* final action.

Allowed classifications:

* `EXECUTABLE_VARIABLE`
* `FIXED_CODE_INVARIANT`
* `DERIVABLE`
* `VALIDATION_ONLY`
* `PRESENTATION_ONLY`
* `MANUSCRIPT_OR_ROADMAP_ONLY`
* `FINGERPRINT_ONLY`
* `DEAD`

Only `EXECUTABLE_VARIABLE` may remain in YAML.

For each retained field, identify the exact production branch, algorithm parameter, path calculation, or artifact difference caused by changing it.

“Used by resolver” is not sufficient.

“Used by fingerprint” is not sufficient.

“Used by test” is not sufficient.

“Copied to result” is not sufficient.

Store this audit temporarily under `.tmp/` and delete it after the final report.

## Phase 3 — Deletion and adaptation

Process one configuration family at a time:

1. Remove keys from YAML.
2. Remove authored Pydantic fields.
3. Remove resolved fields.
4. Remove resolver plumbing.
5. Remove validators made obsolete.
6. Remove fingerprint projection fields.
7. Remove drift paths.
8. Remove frozen/report fields.
9. Remove CLI output.
10. Adapt or delete fixtures.
11. Adapt tests to behavior rather than deleted structure.
12. Delete newly empty classes, functions, modules, and exports.
13. Run impacted tests before continuing.

Do not retain empty abstractions.

Where authored and resolved models become identical pass-throughs, collapse the unnecessary layer unless a real semantic transformation justifies both.

## Phase 4 — Tests and validation

Run focused tests after each deletion family.

At minimum, cover:

* strict YAML parsing;
* unknown-key rejection;
* authored Pydantic schemas;
* dataset resolution;
* protocol resolution;
* experiment resolution;
* runtime resolution;
* cross-document validation;
* scientific fingerprinting;
* execution fingerprinting;
* drift explanation;
* experiment compilation;
* planning DAGs;
* campaign dependencies;
* dataset materialization contracts;
* training profile resolution;
* checkpoint selection;
* score generation;
* calibration subsampling;
* threshold construction;
* evaluation;
* statistical analysis;
* freezing;
* reporting;
* CLI config commands;
* Dagster definitions.

Tests must verify behavior, not the continued existence of old keys.

Add tests proving:

1. Removed legacy keys are rejected.
2. Descriptive metadata cannot influence the scientific fingerprint.
3. Every retained scientific field does influence the scientific fingerprint.
4. Every retained execution-only field influences only the execution fingerprint.
5. Compiled experiment behavior remains scientifically equivalent.
6. The selected threshold policy implementations and numerical parameters are unchanged.
7. Seed cohorts and seed derivation remain unchanged.
8. Split and materialization behavior remains unchanged.
9. Removing configuration prose does not alter artifact coordinates.
10. No result depends on a deleted interpretation string.

After package-level work is complete, run the complete test suite.

Run tests in parallel where safe.

## Required quality checks

Run and fix all findings from:

* Ruff formatting and linting;
* Pyright;
* Pylance analysis when available;
* Pylint;
* import-linter;
* pytest;
* configured architecture checks;
* SonarCloud;
* CodeScene.

If an external service quota or availability issue occurs:

1. Continue with all local work.
2. Retry later in the same execution.
3. Report the exact unavailable check only after all possible retries.
4. Do not weaken acceptance criteria or add suppressions.

Do not reduce batch size, rounds, seeds, clients, calibration sizes, or scientific workloads to make checks pass.

## Runtime diagnostics

After the full suite is green:

1. Run configuration validation through the real CLI.
2. Compile and plan every experiment.
3. Run the one-seed diagnostic path for every configured experiment.
4. Run the complete one-seed diagnostic campaign.
5. Run at least one representative experiment through Dagster.
6. Keep diagnostics isolated under `.tmp/diagnostics/`.
7. Never write to official experiment outputs.
8. Delete all diagnostic outputs after verification.

Do not run an expensive full scientific campaign unless required to validate a behavior that cannot be checked through isolated diagnostics.

## Scientific equivalence audit

Because the configuration format will intentionally change, compare executable behavior rather than raw config or old fingerprints.

Verify before versus after equality for all preserved scientific dimensions:

* dataset identifiers;
* executable source paths and patterns;
* feature order and label handling where still configurable;
* materialization IDs;
* client construction;
* split methods, ratios, chronology, and seeds;
* normalization strategy;
* training profiles;
* model architecture;
* optimizer numerical parameters;
* batching;
* seed cohorts;
* checkpoint schedules and selection behavior;
* threshold policy kinds and numerical parameters;
* experiment populations;
* evaluation bindings;
* sweeps;
* statistical method and numerical controls;
* experiment prerequisites;
* compiled DAG stage ordering;
* artifact coordinates;
* reporting outputs that remain scientifically required.

Any difference must be either:

* an intentional deletion of non-executable metadata; or
* a preexisting defect that was corrected and explicitly documented.

No unexplained drift is acceptable.

## Quantitative trimming requirements

This must be a massive reduction, not a token cleanup.

Required minimum outcome:

* remove every confirmed non-executable leaf;
* reduce total authored YAML non-empty, non-comment lines by at least 50%;
* aim for at least 60%;
* reduce configuration authored-schema and resolution LOC by at least 35%;
* reduce the number of configuration model fields substantially;
* remove all resolved fields with no production reader;
* remove all fingerprint-only descriptive fields;
* eliminate all one-to-one metadata pass-throughs.

Do not stop after reaching the numerical target. Continue until every retained leaf has a proven executable consumer.

If the 50% YAML reduction cannot be reached without changing behavior, the final report must contain an exhaustive consumer trace for every remaining field. Unsupported claims that a field is “scientifically useful” do not count.

## Final acceptance criteria

The task is complete only when all of the following are true:

* The roadmap and scientific source of truth were read.
* Every configuration leaf was classified.
* Only executable variables remain.
* No simple descriptions, claims, limitations, interpretations, or manuscript language remain in runtime configuration.
* No deleted field remains in any authored or resolved model.
* No deleted field remains in a resolver, validator, fingerprint, drift tool, result, manifest, report, fixture, or test.
* Old keys fail strict validation.
* No backward compatibility exists.
* No aliases, shims, redirects, migrations, or deprecated names exist.
* No configuration field is retained solely for fingerprints, drift, descriptions, tests, or reporting.
* Scientific fingerprints contain only scientific behavior.
* Execution fingerprints contain only execution behavior.
* Every remaining field has a documented production consumer.
* No hidden defaults were introduced.
* No duplicated code/config authority remains.
* No raw `Any` remains in the touched architecture.
* No raw dictionary-based domain/config contracts remain in touched and adjacent code.
* Closed vocabularies use enums.
* Touched production code has no comments or explanatory docstrings.
* No stale imports, models, validators, errors, files, or tests remain.
* Dagster remains canonical.
* All impacted tests pass.
* The full test suite passes.
* Ruff passes.
* Pyright passes.
* Pylance passes when available.
* Pylint passes.
* Import-linter passes.
* SonarCloud and CodeScene findings caused or exposed by the refactor are fixed.
* One-seed experiment and campaign diagnostics pass.
* Scientific executable behavior is verified.
* `.tmp` audit and diagnostic artifacts are deleted.
* Official outputs remain untouched.
* Nothing was committed or pushed.

## Required final audits

Perform at least these six audits after implementation:

1. Configuration-leaf consumer audit.
2. Dead schema/resolver/model audit.
3. Fingerprint and drift-pollution audit.
4. Scientific behavior equivalence audit.
5. Architecture, typing, dictionary, enum, and default audit.
6. Test, diagnostic, cleanup, and repository-hygiene audit.

Repeat implementation and audits whenever any audit fails.

## Final report format

Return a concise but complete report containing:

1. Before/after YAML lines, bytes, and leaf-key counts by file.
2. Before/after configuration model and field counts.
3. Before/after configuration subsystem LOC.
4. Deleted configuration sections and fields grouped by family.
5. Deleted schemas, records, resolver functions, validators, projections, and files.
6. Remaining configuration fields and their exact executable consumers.
7. Preexisting issues fixed.
8. Scientific equivalence evidence.
9. Tests and diagnostics run with results.
10. Ruff, Pyright, Pylance, Pylint, import-linter, SonarCloud, and CodeScene results.
11. Confirmation that no compatibility layer was added.
12. Confirmation that no commit or push occurred.
13. Confirmation that `.tmp` and diagnostic outputs were removed.

Do not output a Git patch or plus/minus diff.

Do not claim completion while any acceptance criterion is unresolved.
