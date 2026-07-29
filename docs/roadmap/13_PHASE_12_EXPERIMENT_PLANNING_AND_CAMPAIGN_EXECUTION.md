# Phase 12 — Experiment Planning and Campaign Execution

## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed, validated as one graph at startup, and serialized into every resolved experiment manifest.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Objective

Resolve immutable experiment declarations into exact feasible scientific plans, build the Dagster stage graph, execute single experiments and ordered campaigns deterministically, and recover from interruption without run IDs or hidden state.

## Entry criteria

- Phases 01–11 are complete for every experiment being planned.
- Protocol graph validation is operational.
- Capability and anchor gates are available.

## Source files permitted to change

- `datp_core/experiments/models.py`
- `datp_core/experiments/feasibility.py`
- `datp_core/experiments/planner.py`
- `datp_core/orchestration/definitions.py`
- `datp_core/orchestration/resources.py`
- `datp_core/orchestration/hooks.py`
- `datp_core/orchestration/campaign.py`
- all existing files under `datp_core/orchestration/stages/`
- `datp_core/cli.py`
- `datp_core/runtime/logging.py`

Stage files may call domain services but must not duplicate scientific calculations.

## Required dataclasses and models

In `experiments/models.py`:

- `ScientificCoordinateSet`
- `ExperimentDependency`
- `ExpectedArtifact`
- `StagePlan`
- `ExperimentPlan`
- `FeasibilityDecision`
- `CampaignPlan`
- `CampaignProgress`

In orchestration files:

- `StageExecutionContext`
- `StageResult`
- `HookContext`

## Experiment planning

For each `ExperimentDeclaration`, expand only active coordinates:

- experiment;
- population;
- partition/model/analysis seed as declared;
- model and model coefficient;
- checkpoint round;
- threshold method;
- quantile;
- coverage target;
- calibration size;
- shrinkage weight;
- summary coefficient;
- group assignment/count only when approved;
- calibration replicate;
- temporal state;
- Dirichlet condition.

Do not materialize irrelevant coordinates. The plan contains typed coordinate values, not a dict.

## Feasibility

`experiments/feasibility.py` validates:

- dataset and population capabilities;
- resolved scientific values;
- anchor gate requirements;
- model/method compatibility;
- metric availability;
- temporal support;
- family/group assignment requirements;
- traffic-rate evidence;
- dependencies and reusable data availability.

Return a typed infeasibility decision. Do not create output directories for infeasible cells.

## Stage graph

The existing stage files define the only stage graph:

1. preflight;
2. materialize canonical data;
3. construct population;
4. split;
5. federated or centralized preprocessing;
6. federated or centralized training;
7. checkpoint selection;
8. scoring;
9. calibration;
10. federated or centralized threshold construction;
11. federated or centralized evaluation;
12. anchor verification where applicable;
13. analysis;
14. reporting;
15. finalization.

Dagster definitions express dependencies and reusable assets. Stage modules remain thin orchestration adapters.

## Reuse behavior

- Canonical and processed data are resolved from `data/` coordinates.
- Model/checkpoint/score artifacts may be reused inside a campaign only when complete manifests and scientific coordinates match.
- Threshold and downstream artifacts are experiment-specific.
- A complete experiment is skipped unless explicit overwrite is requested.
- Overwrite deletes the entire experiment output coordinate before execution.

## Campaign recovery

- The deterministic experiment output directory is the authority.
- On interruption, find the first incomplete experiment in declared campaign order.
- Delete that incomplete experiment’s output directory safely.
- Resume from that experiment using the same command.
- Never invent a resume ID, run ID, or job ID.
- Completed earlier experiments remain untouched after manifest validation.

## Hooks

`orchestration/hooks.py` exposes typed no-op stage-boundary hooks for future research. Current hooks may observe typed contexts but cannot change data, scores, thresholds, or results. Phase 15 audits extension readiness.

## CLI

Provide Typer commands:

- `validate-protocols`
- `inspect-experiment`
- `inspect-population`
- `run-experiment`
- `run-campaign`
- `status`
- `clean-experiment`
- `verify-artifacts`

Commands select declared enum identities. They do not accept arbitrary scientific overrides.

## Structured logging

Log experiment, population, seed, model, threshold, stage, client, and coordinate context through structlog. Do not log raw records, secrets, or huge data structures.

## Test files to implement

- `tests/unit/experiments/test_models.py`
- `tests/unit/experiments/test_feasibility.py`
- `tests/unit/experiments/test_planner.py`
- `tests/unit/orchestration/test_definitions.py`
- `tests/unit/orchestration/test_resources.py`
- `tests/unit/orchestration/test_hooks.py`
- `tests/unit/orchestration/test_campaign.py`
- `tests/unit/orchestration/test_stages.py`
- `tests/unit/test_cli.py`
- `tests/unit/runtime/test_logging.py`
- `tests/integration/orchestration/test_single_experiment_execution.py`
- `tests/integration/orchestration/test_campaign_execution.py`
- `tests/integration/orchestration/test_campaign_interruption_recovery.py`
- `tests/integration/orchestration/test_reusable_data_resolution.py`
- `tests/scientific/test_infeasible_cells_do_not_execute.py`
- `tests/scientific/test_scientific_overrides_are_rejected.py`

## Required negative tests

- Arbitrary quantile or seed from CLI.
- Infeasible experiment creates output.
- Incomplete experiment is resumed in place instead of deleted.
- Completed experiment is rerun without overwrite.
- Reused artifact has mismatched manifest.
- Hook mutates stage input or result.
- Threshold comparison trains multiple models.

## Exit criteria

- Every declared experiment expands deterministically or returns typed infeasibility.
- Campaign execution and recovery require no hidden identifiers.
- Reusable data are resolved rather than regenerated.
- Stage graph has no scientific calculations duplicated in orchestration.
- All Phase 12 tests and audits pass.

## External code-health gate

Before phase closure, run the credentials-safe SonarQube CLI and CodeScene procedure in [the roadmap index](00_ROADMAP_INDEX.md#mandatory-external-code-health-gates). Resolve actionable `src/` findings or record the gate as blocked.

## Mandatory closing audit

Before marking this phase complete, the implementing agent must perform and record all applicable checks:

### Scientific audit
- [ ] Every scientific statement and numeric value is traceable to the source of truth or marked unresolved.
- [ ] No attack-labelled record influences training of the benign autoencoder, calibration, threshold construction, checkpoint selection, eligibility, or parameter selection.
- [ ] The fixed-detector contract is preserved wherever threshold methods are compared.
- [ ] Unsupported dataset capabilities produce typed unavailability or infeasibility, never imputation.
- [ ] Confirmatory, supportive, mechanism, external, stress-test, boundary, exploratory, and operational evidence remain separated.

### Architecture audit
- [ ] Only source files explicitly assigned to this phase were modified.
- [ ] No source file was added, renamed, moved, or deleted.
- [ ] No circular dependency was introduced.
- [ ] Domain and protocol modules do not import orchestration, reporting, or concrete storage implementations.
- [ ] No compatibility alias, redirect, deprecated identifier, generic registry, or string-key dispatch was added.

### Typing and validation audit
- [ ] Ruff formatting and linting pass.
- [ ] Pyright strict mode passes for all changed files.
- [ ] Pylint passes at the project threshold without suppressing newly introduced defects.
- [ ] Pydantic models reject extra fields and are frozen.
- [ ] Dataclasses are frozen and slotted unless mutability is scientifically necessary and documented.
- [ ] No `Any`, unchecked cast, mutable module-level collection, or raw configuration dictionary remains.

### Test audit
- [ ] Every test file listed by this phase exists and contains meaningful assertions.
- [ ] Tests verify scientific invariants, invalid inputs, unavailable outcomes, and deterministic behavior—not only happy paths.
- [ ] Tests do not duplicate implementation logic or merely assert that functions return a value.
- [ ] Focused tests pass first; then the complete test suite passes with pytest-xdist.
- [ ] Hypothesis tests use bounded strategies consistent with scientific domains.

### Repository audit
- [ ] `git diff --stat` contains only intended files.
- [ ] No generated output, cache, temporary file, notebook, profiling file, or local path leaked into the repository.
- [ ] No commit or push was performed by the implementing agent.
