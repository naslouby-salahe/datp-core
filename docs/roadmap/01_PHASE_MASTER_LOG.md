# Phase Master Log

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

## Status vocabulary

Use exactly one status per phase:

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED_SCIENTIFIC_VALUE`
- `BLOCKED_DEPENDENCY`
- `IMPLEMENTED_NOT_AUDITED`
- `AUDIT_FAILED`
- `COMPLETE`

Do not add percentages. A phase is binary with respect to its exit criteria.

## Current phase ledger

| Phase | Status | Entry criteria | Exit evidence | Scientific blockers |
|---|---|---|---|---|
| 01 — Scientific identity and scope | `NOT_STARTED` | Source tree exists | Identity tests and scope audit | None expected |
| 02 — Typed protocols and domain contracts | `NOT_STARTED` | Phase 01 complete | Protocol graph validation and strict typing | Exact seed values and any absent hyperparameters must come from source truth |
| 03 — Dataset audit and capabilities | `NOT_STARTED` | Phase 02 complete | Schema and capability tests for all datasets | Raw-data discrepancies must be resolved by audit, not guesswork |
| 04 — Canonical data and reusable preprocessing | `NOT_STARTED` | Phase 03 complete | Deterministic reusable data manifests and reload checks | Exact preprocessing protocol must be present in source truth |
| 05 — Populations, splits, and cohorts | `NOT_STARTED` | Phase 04 complete | Deterministic split/cohort manifests | Any unspecified non-temporal split ratios remain blocking |
| 06 — Anchor reproduction and gate | `NOT_STARTED` | Phase 05 complete | Explicit equivalence/discrepancy decision | Metric-specific tolerances absent from source truth remain blocking |
| 07 — Centralized reference | `NOT_STARTED` | Phase 05 complete | Independent pooled execution and tests | Centralized training values absent from source truth remain blocking |
| 08 — Federated training, checkpointing, and scoring | `NOT_STARTED` | Phases 05–06 complete | Frozen scores and checkpoint discipline pass | Exact architecture/optimizer/batch values must be sourced |
| 09 — Calibration and threshold methods | `NOT_STARTED` | Phase 08 complete | All feasible methods verified | `CLUSTER_THRESHOLD` grouping input remains unresolved until scientifically declared |
| 10 — Metrics and inference | `NOT_STARTED` | Phase 09 complete | Metric semantics and paired inference pass | Near-zero mean-FPR warning cutoff and temporal materiality cutoff must be declared |
| 11 — External and temporal evidence | `NOT_STARTED` | Phases 08–10 complete | Edge static/temporal and CIC boundary tests pass | Temporal source validity is data-dependent |
| 12 — Experiment planning and campaigns | `NOT_STARTED` | Phases 01–11 complete | Complete feasible plan expansion | Any unresolved protocol makes dependent experiments infeasible |
| 13 — Artifacts and serialization | `NOT_STARTED` | Phases 02–12 complete | Safe reload and deterministic path suite pass | None expected after protocol resolution |
| 14 — Reporting and claims | `NOT_STARTED` | Phases 10–13 complete | Claim suppression and export validation pass | Traffic-rate evidence may remain absent; output must be suppressed |
| 15 — Extension readiness | `NOT_STARTED` | Phases 01–14 complete | Hook-boundary tests pass | No future method is implemented |
| 16 — Final audit | `NOT_STARTED` | All prior phases complete | Full acceptance report | Any unresolved mandatory scientific value blocks release |

## Required implementation record per phase

When a phase status changes, append one record under that phase containing:

- status;
- exact source files changed;
- exact test files added or changed;
- scientific-source sections consulted;
- unresolved values encountered;
- focused commands executed;
- whole-suite command executed;
- Ruff result;
- Pyright result;
- Pylint result;
- audit verdict;
- reason for any blocker.

Do not record dates, durations, commit hashes, or subjective completion percentages.

## Global unresolved scientific decisions

These are blocking until the source of truth explicitly resolves them:

1. Exact integer seed cohorts if the current source specifies only cohort size.
2. Any training architecture, optimizer, learning-rate, batch-size, initialization, or non-temporal split value not explicitly present.
3. The scientific source and construction rule for `CLUSTER_THRESHOLD` group assignments.
4. The warning cutoff for a positive but near-zero mean FPR.
5. The positive-materiality cutoff required before temporal recovery ratio is defined.
6. Metric-specific anchor equivalence tolerances beyond explicitly documented historical reference values.
7. Population-specific traffic-rate evidence for alert-burden translation.

An unresolved optional experiment does not block unrelated mandatory work. An unresolved confirmatory dependency blocks every downstream claim that depends on it.
