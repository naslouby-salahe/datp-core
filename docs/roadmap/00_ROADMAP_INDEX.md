# DATP-Core Implementation Roadmap

## Scientific authority and interpretation rules

- Before planning, editing, testing, or auditing this phase, read **`/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md`** in full. It is the authoritative source for the scientific question, permitted evidence, dataset boundaries, numerical grids, metrics, inference, and claim restrictions.
- Use descriptive implementation identities only. Never introduce opaque lettered populations, numbered threshold policies, numbered baselines, compatibility aliases, redirects, deprecated names, or duplicated identifiers.
- The centralized reference is an independent pooled-data pipeline. It is never a federated threshold method and never consumes scores produced by a federated model.
- The confirmatory comparison reuses one selected FedAvg detector, one preprocessing state, one client population, one calibration set, and one held-out score set per seed. Only threshold-calibration scope changes.
- Calibration is benign-only. Attack labels and held-out outcomes cannot select models, checkpoints, quantiles, shrinkage values, statistical coefficients, clients, or group assignments.
- The implementation source tree is locked to the files already created under `datp_core/`. Do not create, rename, move, delete, or replace source files. Test files may be created only when explicitly named in this roadmap.
- Scientific values absent from the source of truth must remain unresolved. Do not infer them from memory, historical repositories, convenient defaults, or common practice. Record the blocker in `01_PHASE_MASTER_LOG.md`.
- Python protocol declarations replace YAML. Protocol objects are immutable, fully typed, explicitly constructed as `CANONICAL_PROTOCOL_GRAPH`, validated at startup without hidden defaults, and serialized into every resolved experiment manifest. `CANONICAL_RUNTIME` locks `require_cuda=True` and `worker_count=6`.
- Do not add backward compatibility, migration adapters, aliases, generic registries, service locators, untyped dictionaries, `Any`, silent fallbacks, or catch-all modules.
- Do not add comments that restate code. Express intent through names, enums, types, validated records, and small functions.
- Reusable canonical and preprocessed data belong under `data/`. Experiment-specific trained states, scores, thresholds, evaluations, analyses, and reports belong under `outputs/`.

## Purpose

This roadmap is the implementation authority for the already-created `datp_core/` source tree. It converts the scientific programme in `/home/naslouby/Projects/datp-core/docs/Journal_Extension_Master_Roadmap.md` into a phased, testable, source-file-constrained implementation plan. It does not replace the scientific source of truth and must never be used to invent scientific values.

## Locked implementation principles

1. **One source tree.** The source files listed in the user-approved tree are exhaustive. New behavior must be placed in the existing file whose responsibility matches it.
2. **Python-native protocols.** Closed identities are enums. Numeric scientific quantities are validated values. Compound declarations are frozen Pydantic models or frozen slotted dataclasses. Experiment declarations are typed objects, never dictionaries.
3. **Reusable data.** Canonical and transformed datasets are reusable assets under `data/`, keyed by scientific and preprocessing coordinates. They are not duplicated per experiment.
4. **Independent centralized reference.** Pooled preprocessing, training, checkpointing, scoring, thresholding, and evaluation remain separate from federated execution.
5. **Deterministic results.** Every output path is derived from descriptive scientific coordinates. No run IDs, job IDs, timestamps, random directory names, or hidden defaults are permitted.
6. **Capability-driven feasibility.** Dataset and population capability contracts decide which metrics, threshold methods, temporal analyses, and claims are valid.
7. **Explicit populations.** Confirmatory-eligible, attack-evaluable, unavailable, and deployment-fallback populations are separate typed cohorts. Fallback clients never enter confirmatory cross-client dispersion.
8. **Safe persistence.** SafeTensors stores model tensors; skops stores fitted scikit-learn state; Parquet/PyArrow stores tables and schemas; Pydantic JSON stores manifests and summaries. Unsafe pickle is prohibited.
9. **Honest negative evidence.** Null, reversed, unstable, unavailable, and infeasible results are first-class outputs.
10. **No hidden extension.** Attacks, defenses, dynamic adaptation, and future datasets are supported only through typed boundaries. They are not implemented in DATP-Core.

## Required libraries

Use only libraries that remove substantial custom code or provide a required scientific/system contract:

- `pydantic>=2` for frozen validated protocol and manifest models.
- `polars` and `pyarrow` for lazy tabular processing, Parquet, and schema persistence.
- `pandera` with its Polars backend for executable dataset and transformed-schema validation.
- `numpy`, `scipy`, `statsmodels`, and `pingouin` for numerical and statistical analysis.
- `torch` and `safetensors` for autoencoders and safe tensor persistence.
- `flwr` for FedAvg/FedProx orchestration primitives where it removes custom federated boilerplate.
- `scikit-learn` and `skops` for preprocessing, clustering utilities only after a grouping rule is scientifically approved, and safe estimator persistence.
- `dagster` for the explicit stage graph and asset dependencies.
- `typer`, `rich`, and `structlog` for the CLI and structured execution feedback.
- `filelock` only around reusable data materialization and atomic cache publication.
- `pytest`, `hypothesis`, `pytest-xdist`, `pytest-cov`, and `pytest-benchmark` for verification.

Do not add a library merely to wrap a few lines of straightforward typed code.

## Mandatory external code-health gates

Every phase must run the following WSL commands before completion, after its local tests and static checks pass:

```bash
set -a
. ./.env
set +a
test -n "${SONARQUBE_CLI_TOKEN:-}"
SONARQUBE_CLI_SERVER="https://sonarcloud.io" \
SONARQUBE_CLI_ORG="naslouby-salahe" \
  "$HOME/.local/share/sonarqube-cli/bin/sonar" analyze \
  --project "naslouby-salahe_datp-core" --base origin/main --depth DEEP --format json

test -n "${CS_ACCESS_TOKEN:-}"
/usr/local/bin/cs delta --output-format json --pretty
```

`.env` is the local credential loader and must remain untracked. Sonar and CodeScene receive tokens only through their child-process environment. Never print tokens, put them in command-line arguments, persist them in the repository, or include them in audit output. Resolve actionable `src/` findings. Record service-side analysis unavailability separately from authentication failure. Do not push solely to produce an analysis.

## Phase order

| File | Phase | Depends on | Primary completion gate |
|---|---|---|---|
| `02_PHASE_01_SCIENTIFIC_IDENTITY_AND_SCOPE.md` | Scientific identity and scope | None | Descriptive identities and scope guards locked |
| `03_PHASE_02_TYPED_PROTOCOLS_AND_DOMAIN_CONTRACTS.md` | Typed protocols and domain contracts | Phase 01 | Complete immutable protocol graph validates |
| `04_PHASE_03_DATASET_AUDIT_AND_CAPABILITIES.md` | Dataset audit and capabilities | Phase 02 | Three datasets validate against audited schemas |
| `05_PHASE_04_CANONICAL_DATA_AND_REUSABLE_PREPROCESSING.md` | Canonical data and reusable preprocessing | Phase 03 | Reusable data can be rebuilt and safely reloaded |
| `06_PHASE_05_POPULATIONS_SPLITS_AND_EVALUATION_COHORTS.md` | Populations, splits, and cohorts | Phase 04 | Population manifests are deterministic and leak-free |
| `07_PHASE_06_ANCHOR_REPRODUCTION_AND_JOURNAL_GATE.md` | Anchor reproduction and gate | Phase 05 | Anchor gate returns an explicit scientific decision |
| `08_PHASE_07_CENTRALIZED_REFERENCE_PIPELINE.md` | Independent centralized reference | Phase 05 | Pooled pipeline executes without federated artifacts |
| `09_PHASE_08_FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING.md` | Federated models and scores | Phases 05–06 | Frozen detector scores are reusable across thresholds |
| `10_PHASE_09_CALIBRATION_AND_THRESHOLD_METHODS.md` | Calibration and thresholds | Phase 08 | Threshold methods satisfy benign-only contracts |
| `11_PHASE_10_EVALUATION_METRICS_AND_STATISTICAL_INFERENCE.md` | Metrics and inference | Phase 09 | Metric semantics and paired inference are verified |
| `12_PHASE_11_EXTERNAL_VALIDATION_AND_TEMPORAL_RECALIBRATION.md` | External and temporal evidence | Phases 08–10 | Capability-limited external/temporal results execute |
| `13_PHASE_12_EXPERIMENT_PLANNING_AND_CAMPAIGN_EXECUTION.md` | Planning and campaigns | Phases 01–11 | Catalogue expands to deterministic feasible plans |
| `14_PHASE_13_ARTIFACTS_SERIALIZATION_AND_OUTPUT_LAYOUT.md` | Artifacts and persistence | Phases 02–12 | All persisted types reload and validate safely |
| `15_PHASE_14_REPORTING_CLAIMS_AND_PUBLICATION_EXPORTS.md` | Reporting and claims | Phases 10–13 | Blocked or unavailable claims cannot leak into reports |
| `16_PHASE_15_EXTENSION_READINESS.md` | Future extension boundaries | Phases 01–14 | Extension hooks add no current scientific behavior |
| `17_PHASE_16_FINAL_SCIENTIFIC_AND_ENGINEERING_AUDIT.md` | Final audit | All phases | Full scientific and engineering acceptance passes |

## Source-addition rule

Phase documents restrict additions under `src/`; they do not prohibit necessary edits to existing source files. A new source file requires explicit user approval, a focused responsibility, and an update to the locked-source architecture test. Existing source files may be corrected when a later phase discovers an upstream contract omission.

## Test-tree rule

The roadmap may add focused tests beneath `tests/`. Test package markers and small local fixtures are permitted when required for deterministic collection or a clear miniature-data assertion. Shared fixture utility packages remain disallowed unless explicitly approved.

## Completion discipline

A phase is complete only when its implementation, focused tests, whole-suite tests, static checks, scientific audit, and source-tree audit all pass. “Code exists” is not completion.
