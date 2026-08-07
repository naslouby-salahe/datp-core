# Implementation Notes — Execution Foundation

Locked design decisions. Ordered fix plan. Pending subagent verification items marked `[VERIFY]`.

---

## Design: execution context threading

Every registered workflow seed function gains an explicit `output_root: Path` keyword (required — no `Path | None = None` hidden default). Threaded:

- `run_experiment(experiment_id, *, smoke, overwrite)` → `_output_root(smoke)` → dispatch handlers → seed fn.
- `run_campaign(*, overwrite)` → `output_root = OUTPUTS_ROOT` always (campaign never runs in smoke).
- Seed fns that currently default to OUTPUTS_ROOT (confirmatory L125/L158, external L96, personalization L476/L487/L505) drop the default and require the arg.
- Temporal: `run_temporal_seed(partition_seed, *, output_root)` threads into `_execute_temporal_states` (L300/314/317) and `_evaluate_state` (L377) where OUTPUTS_ROOT is currently hardcoded.
- `ditto_directory(seed, reg, branch, output_root)` gains explicit output_root (L965 hardcode removed).
- `_evaluation_path` hardcodes in external.py L196 / personalization.py L810 / confirmatory.py L696-705: `[VERIFY]` decide whether threaded or resolved from artifact discovery — bounded/external paths resolve from output_root via `bounded_evidence_seed_directory`; FedProx path needs output_root thread.

## Design: smoke seed subset

- FedProx dispatch: honor `seeds` argument — run ONLY requested seed subset (smoke = 1 canonical seed). NOT `run_fedprox_grid_campaign` (which is full cohort x all coefficients). Use `run_fedprox_coefficient_campaign(coefficient, output_root, overwrite, seed_cohort=...)` or a new subset-scoped primitive — `[VERIFY]` existing subset capability; `run_fedprox_stress_test_seed(seed, coefficient, output_root, overwrite)` already exists per-seed.
- Smoke seed cohort for all experiments = `seed_cohort_for(experiment_id).values[0]` (canonical_smoke_seed). For bounded-evidence (external/temporal) that's BOUNDED_EVIDENCE_SEED_COHORT[0].
- Smoke FedProx report cannot run `select_primary_fedprox_coefficient_from_artifacts` (FedProxCoefficientTerminalLoss requires full confirmatory cohort). Smoke report must either (a) skip primary-selection step, or (b) fail cleanly. `[VERIFY]` what smoke summary actually publishes.

## Design: report = pure consumer of evidence

- Ditto: `run_ditto_stress_test_seed` gains `output_root`; after computing metrics, PERSISTS a typed per-seed evidence record + COMPLETE digest marker under `ditto_directory(seed, reg, EVIDENCE, output_root)`. Evidence record needs only: `personalized_coordinate` (training_seed, model_coefficient), `shared_threshold_metrics`, `local_threshold_metrics`, `evaluation_cohort` — analysis (`analyze_ditto_absorption`, `_population_cv_fpr_effect`) reads only these. NOT the threshold result objects.
- Report: load all seed evidence records + FedAvg reference (`load_fedavg_cv_fpr_effect`) → `analyze_ditto_absorption(..., output_directory=<analysis dir>)` pure. Delete `run_ditto_absorption_campaign`.
- Temporal: `run_temporal_seed` gains `output_root`; persists per-seed `TemporalSeedResult` evidence (canonical JSON) + COMPLETE marker under `bounded_evidence_seed_directory(...)`-relative analysis/evidence branch. Report: load all seed records → reconstruct `TemporalCampaignResult` → `analyze_temporal_campaign(campaign)` pure. Delete `run_temporal_campaign` (report path).
- Serializability verified: `domain/provenance.py` `canonical_value` handles frozen dataclasses + pydantic wired classes; value objects unwrap to scalars; `TypeAdapter(T).validate_json` deserializes (base.py `__get_pydantic_core_schema__`).

## Design: single-pass campaign

- `run_campaign` executes each coordinate exactly once (dispatch). Reports: after all execution completes, run `generate_report` ONCE per experiment + one programme-level report. Remove in-loop report per experiment. Final report only if `overwrite` semantics allow `[VERIFY]` — report never re-executes so single call is safe.

## Design: threshold-method outcome surfacing

- Dispatch handler return type: `ExperimentRunResult` carrying `completed_threshold_methods: tuple[FederatedThresholdMethod, ...]` + per-method `ThresholdMethodOutcome` (COMPLETED / UNAVAILABLE / INFEASIBLE / FAILED). Do not discard `ThresholdUnavailableResult`.
- Temporal `_evaluate_state`: unavailable method → `TemporalMethodOutcome.UNAVAILABLE` recorded in evidence, not silently skipped.
- Ditto: shared method unavailable → currently raises ScientificContractError (L291-300) — keep raising? `[VERIFY]` roadmap: shared threshold is confirmatory core; unavailable shared = real failure. Local-only unavailable → surface as method outcome.

## Design: status/analysis markers

- Extend `_ANALYSIS_MARKER_CHECKS` to FedProx, Ditto, Temporal with real marker paths:
  - FedProx: `{output_root}/fedprox_stress_test/{population}/analysis/COMPLETE` (or per-coefficient — `[VERIFY]` actual analysis layout in personalization.py analyze path).
  - Ditto: analysis COMPLETE marker under ditto analysis directory.
  - Temporal: temporal analysis COMPLETE marker.
- `_analysis_marker_present(experiment_id, *, output_root)` gains output_root param so status works for smoke-scoped analysis too `[VERIFY]` status call site.
- Status read-only, derived from manifests.

## Design: anchor failure visibility

- `run_smoke` full branch: stop swallowing. On `AnchorReproductionError`/`ScientificContractError`/`MissingPrerequisiteError`: record typed failure per experiment, surface in `SmokeRunResult`, do NOT mark smoke COMPLETE for failed prerequisite. `[VERIFY]` `SmokeRunResult`/`CampaignRunResult` fields.

## Ordered fix plan

1. Smoke isolation (external.py, personalization.py, temporal.py, confirmatory.py seed fns + campaign.py dispatch).
2. Report purity (Ditto evidence persistence + temporal evidence persistence; delete train-paths in report handlers).
3. Single-pass campaign (run_campaign).
4. Threshold outcome surfacing (dispatch return type, temporal outcome recording).
5. Analysis markers + status truthfulness.
6. Anchor failure surfacing in smoke.
7. 10 required tests.
8. Validation (ruff/pyright/format/tests).
9. Graphify post-edit verification.
10. Four-reviewer audit + reconciliation.

## Pending verification items (`[VERIFY]`)

- [ ] checkpoints.py `select_execution_checkpoint` trains-under-output_root or raises when absent (temporal smoke threading depends).
- [ ] scoring/federated.py `publish_federated_scores` signature/output-root.
- [ ] personalization.py `_population_context`/`_personalized_scores` exact inputs.
- [ ] FedProx existing subset-scoped execution primitive.
- [ ] FedProx/Ditto/Temporal analysis directory layout for markers.
- [ ] run_campaign final-report overwrite semantics; SmokeRunResult/CampaignRunResult fields.
- [ ] test constraints from tests/ (test_cli, test_personalization_shared_scoring, others).
- [ ] `_evaluation_path` threading decisions.
