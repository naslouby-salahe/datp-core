# REVIEWER_1 — Smoke isolation, FedProx seed subset, anchor surfacing

Scope traced: campaign.py dispatch/run paths, cli/app.py smoke_command, external.py/personalization.py/temporal.py/confirmatory.py seed entry points, execution.py + engine.py output_root threading, protocols/seeds.py, workflows/__init__.py seed_cohort_for, ledger WR-004/005/010, roadmap §5.1.

## Findings

- [OK] WR-004 (smoke isolation) — VERIFIED FIXED.
  - `_output_root(smoke)` returns `SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT` (campaign.py:193-194); `run_experiment` binds `output_root = _output_root(smoke=smoke)` (campaign.py:209).
  - All four named handlers now thread `output_root`:
    - `_dispatch_edge_benign_equity_validation` -> `run_external_validation_seed(seed, output_root=output_root)` (campaign.py:303-305; external.py:58).
    - `_dispatch_ciciot_file_client_boundary` -> `run_ciciot_boundary_seed(seed, output_root=output_root)` (campaign.py:321-323; external.py:67).
    - `_dispatch_ditto_absorption_stress_test` -> `run_ditto_stress_test_seed(..., output_root=output_root, overwrite=overwrite)` (campaign.py:368-374).
    - `_dispatch_edge_one_shot_recalibration` -> `run_temporal_seed(seed, output_root=output_root)` (campaign.py:390).
  - `_run_bounded_external_seed` (external.py:90), `run_confirmatory_seed`/`run_family_grouped_mechanism_seed` (confirmatory.py:114-165), `run_fedprox_stress_test_seed` (personalization.py:474-528), `run_ditto_stress_test_seed` (personalization.py:262-411) and `ditto_directory` all take and propagate `output_root`; temporal `_execute_temporal_states`/`_evaluate_state` write via `state_root` and persist evidence under `output_root` (temporal.py:367-433, 448-497, 644-649).
  - `execute_declared_campaign` passes `output_root` into `execute_campaign` (execution.py:78-84); engine completion-state/COMPLETE_INVALID checks are relative to that root (engine.py:107-125). Smoke can no longer poison the production tree.
  - No `OUTPUTS_ROOT` reference remains in external.py or temporal.py. Remaining uses in confirmatory.py (183, 188, 424, 488, 565, 699) and personalization.py (854) are analysis/report-time helpers (analyze_confirmatory_campaign, _fedprox_evaluation_path), never reached from the smoke seed-execution path. Smoke summary also written under `SMOKE_OUTPUT_ROOT/summary` (campaign.py:53, 498-504).
  - Note (non-blocking, pre-existing): `del overwrite` remains in the external/temporal handlers (campaign.py:300, 318, 387), so `run_campaign(overwrite=True)` does not force rerun for those; smoke overwrite is handled at the outer scoped-rmtree level (campaign.py:466-472, 210-213).

- [OK] WR-005 (FedProx seed subset) — VERIFIED FIXED.
  - `_dispatch_fedprox_absorption_stress_test` now iterates the passed `seeds` x `FEDPROX_COEFFICIENTS` (campaign.py:338-347); the old `del seeds` + `run_fedprox_grid_campaign` (full CONFIRMATORY_SEED_COHORT) path is removed from the dispatch.
  - `run_experiment` passes `seeds=(canonical_smoke_seed(experiment_id),)` for smoke (campaign.py:215), and `run_fedprox_stress_test_seed` builds its campaign with `seed_cohort=SeedCohort(values=(training_seed,))` (personalization.py:485) — no CONFIRMATORY_SEED_COHORT in the run path. Smoke FedProx = 1 seed x all coefficients; full-cohort runs remain only in `run_fedprox_coefficient_campaign`/`run_fedprox_grid_campaign` (personalization.py:531-563), which smoke no longer invokes.
  - Note: smoke still runs the full FEDPROX_COEFFICIENTS grid (x 1 seed); the ledger fix constrained seeds only, so this matches the stated disposition.

- [SEV-MED] WR-010 (anchor failure surfacing) — PARTIALLY FIXED; still not surfaced end-to-end.
  - campaign.py:482-495 `run_smoke` now records the caught exception into `anchor_failure` (no longer discarded to `_`), and returns it in `CampaignRunResult.anchor_failure` (campaign.py:116-120).
  - However `anchor_failure` has NO consumer: grep shows the field only in campaign.py (120, 479, 482, 487, 494, 526); no CLI, no test, no other module reads it. `smoke_command` (cli/app.py:85-104) echoes only experiment count/detail and per-experiment seeds/methods; it never prints `result.anchor_failure`, and `run_smoke` does not raise on anchor failure, so a smoke run that fails the anchor gate exits 0 with output identical to a passing run.
  - Additionally, the PRIMARY anchor-failure mode is not captured at all: `decide_anchor_gate` returns `AnchorGateStatus.BLOCKED` as a status, not an exception (gate.py:39-46); `verify_anchor` returns normally (anchor.py:104-126); `reproduce_anchor`'s internal try/except converts AnchorReproductionError into a returned BLOCKED result (campaign.py:562-582); `verify_anchor_programme` returns BLOCKED (campaign.py:592-619). `run_smoke` discards both returned `AnchorCommandResult` values (campaign.py:484-485), so a BLOCKED gate leaves `anchor_failure=None`. Only genuinely propagated exceptions (missing prerequisite, seed-execution failure, unreadable package raised inside verify_anchor_programme) populate it.
  - Net effect: the ledger disposition "should report anchor gate status even in smoke" is not met; smoke still silently continues past an anchor gate failure with no user-visible signal.

- [OK] Smoke single-seed invariant — VERIFIED.
  - campaign.py:215: `seeds = (canonical_smoke_seed(experiment_id),) if smoke else cohort.values`. All seven dispatch handlers iterate the passed `seeds` (campaign.py:268-269, 285-287, 303-305, 321-323, 338-347, 368-374, 390); none re-expands to a full cohort. `reproduce_anchor(smoke=True)` uses a single-seed cohort (campaign.py:551-553).

- [OK] canonical_smoke_seed = first declared cohort member — VERIFIED.
  - campaign.py:154-159 returns `cohort.values[0]`. `seed_cohort_for` (workflows/__init__.py:105-113) maps EDGE_SENSOR_GROUPS / EDGE_TEMPORAL_GROUPS / CICIOT_FILE_CLIENTS -> BOUNDED_EVIDENCE_SEED_COHORT (seeds 0-9), else CONFIRMATORY_SEED_COHORT (seeds 0-9) (protocols/seeds.py:27-34). So the canonical smoke seed is `Seed(0)` for every registered experiment. Roadmap §5.1 defines the confirmatory cohort as "ten paired training seeds"; `values[0]` is the first declared member. Caveat: the roadmap never names seed 0 "canonical" (smoke is an internal mechanism); the code satisfies the stated "first declared seed-cohort member" rule by construction, with deterministic cohorts.

## Verdict

Smoke isolation and seed-subset correctness are sound: WR-004 and WR-005 are fixed, smoke is single-seed everywhere, and `canonical_smoke_seed` resolves to the first declared cohort member (Seed(0)) for all experiments. The remaining gap is anchor surfacing (WR-010): `run_smoke` stores the error object but nothing consumes it — the CLI never echoes it, the exit code stays 0, and the routine BLOCKED-gate verdict (returned as a status, not an exception) never even populates `anchor_failure`. Smoke isolation + seed subset are correct; anchor surfacing is only half-implemented and should not be declared done.
