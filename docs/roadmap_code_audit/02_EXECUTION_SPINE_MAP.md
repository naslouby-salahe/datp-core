# 02 — Execution Spine Map

Traced and source-verified (not merely graph-reachable) for the primary confirmatory workflow; identical structural pattern independently re-verified for anchor/temporal/training-stress/external workflows by dedicated subagents (see `05_EXPERIMENT_AUDITS.md`).

```
CLI `run experiment SHARED_VS_LOCAL_CONFIRMATION`
 → app/cli/execution.py:run_experiment()
 → app/validation.require_experiment_execution_ready()   (rejects SUPPRESSED/INFEASIBLE/BLOCKED)
 → app/recipes.recipe_for(id).dispatch()
 → experiments/execution/workspace.ExperimentWorkspace
     .selected_checkpoint   (detector/checkpoints/selection.py — non-test rule, terminal round 200)
     .scores  [@cached_property]  (detector/scoring/{federated,centralized}.py — scored once, reused)
     .eligible_calibration_scores()  (thresholds/calibration/eligibility.py — benign-only, n_k>=100)
     .threshold  (thresholds/dispatch.py → policies/{shared,local,family,cluster}.py — consumes self.scores)
 → experiments/confirmatory/run.py._confirmatory_contrast(seed)
 → analysis/evidence.analyze_confirmatory_evidence() → analysis/preparation.paired_bca_interval()
 → presentation/export.export_confirmatory_publication()
```

Branches audited:
- **Reuse**: `overwrite=False` (default) → `*_is_reusable()` checksum/manifest validation before regenerating (scores: `federated_scoring_is_reusable`/`centralized_scoring_is_reusable`; datasets/thresholds/evaluations: repository-level `artifact_completion_marker_matches`).
- **Overwrite**: `--overwrite` → scoped `rmtree` of the owning artifact directory only, then regenerate (`artifacts/repositories/publication.py`).
- **Missing/corrupt artifact**: completion-marker mismatch or missing file → `is_reusable` returns `False` (fail-closed), forces regeneration; never silently treated as complete.
- **Unsupported/infeasible**: `ExperimentReadiness.{SUPPRESSED,INFEASIBLE,BLOCKED}` raise `ScientificContractError` before any execution (`app/validation.require_experiment_execution_ready`).
- **Anchor-gated execution**: `run_campaign()`/`generate_report()` call `_enforce_anchor_gate()` (`app/research.py`) before producing results; a `ANCHOR_REPRODUCTION_FAILED` status raises and blocks, it does not silently degrade to a supportive-only report.
- **Campaign**: `run_campaign()` executes mandatory recipes in declared dependency order; `CampaignRole.OPTIONAL` recipe failures are caught and reported as such, mandatory failures propagate.
- **Report-only**: `report` command consumes already-validated evidence (`generate_report` → `recipe_for(id).report()`), does not re-run training/scoring.

No dead ends, no bypass path around `ExperimentWorkspace`/`recipe_for` found by any of the 10 discovery subagents; no direct-to-artifact-write shortcut exists outside the artifact-repository publish functions.
