# Review Resolution — Execution Foundation

Reconciliation of the four independent reviewer reports against the final working tree.
Dispositions: **FIXED** (defect corrected and verified), **ACCEPTED** (correct by design / out of scope, with rationale), **ALREADY FIXED** (corrected earlier in the audit loop before the report was written or by a later change).

Reviewer reports: `reviewers/REVIEWER_{1..4}.md`.

---

## REVIEWER_1 (Smoke isolation, FedProx seed subset, anchor surfacing)

### [SEV-MED] WR-010 anchor failure not surfaced end-to-end — FIXED

Reported: `run_smoke` stored a caught exception in `anchor_failure` but nothing consumed it, the CLI never echoed it, and the routine BLOCKED-gate verdict (returned as a status, not an exception) never populated the field at all.

Resolution, all verified in the final tree:

- `run_smoke` (campaign.py:453-494) now inspects the two returned `AnchorCommandResult` values from `reproduce_anchor` and `verify_anchor_programme`. Any gate status outside `{PASS, PASS_WITH_DECLARED_DISCREPANCY}` produces `anchor_failure = f"anchor gate {','.join(non_pass)}"`. Raised `AnchorReproductionError` / `ScientificContractError` / `MissingPrerequisiteError` still populate `anchor_failure` from the exception message. Both failure shapes are captured.
- `smoke_command` (cli/app.py:97-98) echoes `anchor_failure={result.anchor_failure}` when the field is non-None; a passing gate stays silent.
- Regression tests: `tests/unit/pipeline/workflows/test_smoke_anchor_failure.py` (raise-path, returned-BLOCKED path, PASS path) and `tests/unit/cli/test_cli.py::test_smoke_echoes_an_anchor_failure_instead_of_hiding_it` + `test_smoke_omits_anchor_failure_when_the_gate_passes`. All pass.

### [OK] WR-004 smoke isolation — confirmed fixed

`_output_root(smoke)` / `run_experiment` output_root binding, all dispatch handlers threading output_root into their seed functions, smoke summary under `SMOKE_OUTPUT_ROOT/summary`, and scoped rmtree for smoke overwrite all verified in the final tree. No action.

### [OK] WR-005 FedProx seed subset — confirmed fixed

`_dispatch_fedprox_absorption_stress_test` iterates the passed `seeds` × `FEDPROX_COEFFICIENTS`; smoke = 1 canonical seed × all coefficients; full-cohort runs remain only in report/analysis paths. No action.

### [OK] Smoke single-seed invariant + canonical_smoke_seed — confirmed

`seeds = (canonical_smoke_seed(experiment_id),)` for smoke; `canonical_smoke_seed` returns `cohort.values[0]`; all seven dispatch handlers iterate passed seeds. No action.

---

## REVIEWER_2 (Report purity, single-pass campaign)

### [SEV-LOW] `_generate_campaign_report` best-effort aggregation — ACCEPTED

Reported: `generate_report(None)` (and the final campaign report) returns success even when zero experiments have reportable evidence; the missing state is recorded in `detail` rather than failing.

Acceptance rationale: the missing state is explicit, not silent — each absent experiment is recorded as `item:missing(<typed error>)` in both `CampaignRunResult.detail` and `ReportResult.detail`, and per-loader typed errors (`ReportEvidenceError`, `ScientificContractError`, `MissingPrerequisiteError`) are preserved. This is a deliberate best-effort aggregate report (WR-007 single-pass requires one report invocation after the campaign loop; an all-or-nothing failure would make a partial-but-valid campaign unreportable). The per-handler and per-loader typed-error contract is intact. Not a WR-006/WR-007 regression.

### [OK] WR-006 report handlers load evidence only — confirmed fixed

Verified in the final tree: `_report_ditto_absorption_stress_test` imports `load_ditto_stress_test_evidence` + `analyze_ditto_absorption` only; `_report_edge_one_shot_recalibration` imports `analyze_temporal_campaign` + `load_temporal_campaign_seeds` only; `run_ditto_absorption_campaign` and `run_temporal_campaign` are deleted with zero callers (grep of `src/` and `tests/`). No action.

### [OK] WR-007 single-pass campaign — confirmed fixed

`run_campaign` loop calls only `run_experiment`; the in-loop `generate_report` was removed; one final `generate_report(None, overwrite=overwrite)` runs after the completion marker. No action.

### [OK] Missing report evidence fails with typed errors — confirmed fixed

Ditto/temporal loaders raise `ScientificContractError` on missing/invalid/checksum-mismatched evidence; FedProx selection wraps `ArtifactIntegrityError` as `ReportEvidenceError`. No silent training fallback. No action.

### [OK] Evidence persistence with checksummed COMPLETE markers — confirmed fixed

Ditto slim `DittoStressTestEvidence` + temporal full `TemporalSeedResult` both persist `seed.json` plus a `COMPLETE` marker binding `canonical_checksum(evidence)`; loaders re-verify. No action.

### [OK] Report registry covers registered workflows — confirmed fixed

`_EXPERIMENT_REPORT_HANDLERS` and `_ANALYSIS_MARKER_CHECKS` enforced to exactly equal `REGISTERED_WORKFLOW_EXPERIMENTS`. No action.

---

## REVIEWER_3 (Outcome surfacing, status semantics)

### [SEV-MED] Temporal outcome overclaims all-states/all-seeds — FIXED

Reported: `_temporal_method_outcomes` built `completed` as a union across the three states and all seeds but labeled members COMPLETED "across all temporal states and seeds", even when a method was UNAVAILABLE in the recalibrated state (smaller calibration window). This diverged from `_common_completed_methods`, which enforces cross-state agreement for the persisted `recoveries`.

Resolution: `_temporal_method_outcomes` (campaign.py:389-425) now gates COMPLETED on the method being present in the completed set of **every** seed (`completed_across_seeds = declared ∩ each seed's completed set`, intersection, not union). A method unavailable in any seed surfaces as UNAVAILABLE with reason+detail; methods never completed surface as INFEASIBLE. Regression test `tests/unit/pipeline/workflows/test_temporal_method_outcomes.py` builds real `TemporalSeedResult` objects and asserts the intersection semantics (LOCAL completed in one seed but unavailable in another → UNAVAILABLE, not COMPLETED) and the all-completed case. Pass.

### [SEV-LOW] `_seed_completion_outcomes` at-least-once vs all-seeds — FIXED

Reported: same union-vs-across-all-seeds mismatch for the non-temporal dispatch handlers; the COMPLETED detail claimed execution across `{len(completed_by_seed)}` seeds.

Resolution: `_seed_completion_outcomes` (campaign.py:239-262) now also uses intersection semantics (`completed_across_runs = declared ∩ each run's completed set`), gating COMPLETED on presence in **every** executed run. The detail reads `"executed across all {len(completed_by_seed)} runs"` (run, not seed — the FedProx handler passes one tuple per seed×coefficient execution, so the old "seeds" wording mis-counted 40 runs as "40 seeds"). The INFEASIBLE detail was changed from `"declared but unsupported by the population capability contract"` to `"declared but not completed in this execution"` — the capability-contract phrasing was an unverified claim (R3's separate SEV-LOW on that detail is absorbed by this change; the status itself is correct per ledger). INFEASIBLE now describes only what was observed.

### [SEV-LOW] Ditto dispatch asserts completion instead of deriving — FIXED

Reported: `_dispatch_ditto_absorption_stress_test` asserted `completed = (SHARED_THRESHOLD, LOCAL_THRESHOLD)` and passed `(completed,) * len(seeds)`, discarding the per-seed `DittoStressTestResult` objects.

Resolution: `_dispatch_ditto_absorption_stress_test` (campaign.py:351-373) now derives completion from the actual results: `completed_by_seed=tuple((result.shared_threshold.method, result.local_threshold.method) for result in results)`. Consistent with every other dispatch handler; no fabricated outcomes.

### [SEV-LOW] INFEASIBLE detail unverified — FIXED (absorbed above)

The INFEASIBLE detail no longer asserts the population-capability-contract cause it did not verify; it reports the observed state. Applies to both `_seed_completion_outcomes` and `_temporal_method_outcomes`.

### [SEV-LOW] FedProx COMPLETED detail "executed across N seeds" mis-counts — FIXED (absorbed)

The detail now counts runs and is emitted only for methods present in every run. A full campaign reads "executed across all 40 runs" (10 seeds × 4 coefficients), which is factually correct; a smoke run reads "executed across all 4 runs" (1 seed × 4 coefficients).

### [SEV-LOW] `_evaluate_state` raises on total unavailability — ACCEPTED

Reported: a state where all declared methods are unavailable fails the run (`ScientificContractError("temporal execution produced no evaluable threshold method")`) instead of surfacing all-UNAVAILABLE outcomes.

Acceptance rationale: per-method unavailability is handled without raising (temporal.py:475-483); the total-unavailability raise is a fail-closed safety property. With the current 4-method temporal ladder (SHARED/LOCAL feasible by population capability), total unavailability indicates an upstream contract violation that should fail loudly rather than silently degrade to an empty result. The ledger has no rule requiring all-UNAVAILABLE here. Fail-closed is the correct disposition for an impossible state.

### [SEV-LOW] FedProx marker accepts either role directory — FIXED (decision-derived role)

Reported: `_fedprox_analysis_marker_present` accepted `publication.md` under either `primary` or `sensitivity` per coefficient without checking the role matches the current `primary_coefficient_decision.json`, creating a mild staleness window.

Resolution: `_fedprox_analysis_marker_present` (campaign.py:956-982) now loads the locked decision with `load_fedprox_primary_coefficient_decision` and checks `PUBLICATION_FILENAME` under the **decision-derived role** — `FedProxRoleDirectory.PRIMARY` for the coefficient equal to `decision.primary_coefficient`, `FedProxRoleDirectory.SENSITIVITY` otherwise — for every `FEDPROX_COEFFICIENTS` member. Absent or unreadable decision returns `False` (no false completion). The marker and the report handler (`_report_fedprox_absorption`, campaign.py:788-837) now share the same role-assignment predicate and the same builders (`fedprox_stress_test_root`, `fedprox_analysis_directory`, `FEDPROX_PRIMARY_COEFFICIENT_DECISION_FILENAME`), so a stale-role mismatch cannot yield a false COMPLETED. The write side produces the decision artifact before any role directory, so a valid marker implies the decision existed at analysis time.

### [OK] Verified-fixed list — confirmed

- `ThresholdMethodExecutionStatus` defined; FAILED reserved but never constructed (ledger-sanctioned dead member, not surfaced-and-dropped).
- Every dispatch handler surfaces one outcome per declared method.
- Temporal dispatch derives outcomes from live per-seed runs, not `load_temporal_campaign_seeds`.
- Temporal UNAVAILABLE carries reason+detail; `_ANALYSIS_MARKER_CHECKS` exact-set-enforced for all 7 experiments.
- `programme_status` read-only; `anchor_status` degrades to BLOCKED on missing gate; campaign COMPLETE written after all experiments; CLI echoes all method outcomes.

---

## REVIEWER_4 (Scientific invariants, reuse, typing, config)

### [SEV-MED] `_ditto_analysis_marker_present` hardcodes `"ditto_stress_test"` — FIXED

Reported: the new Ditto analysis-marker function hardcoded the root segment `"ditto_stress_test"` and `"analysis"` despite `ExecutionRootDirectory.DITTO_STRESS_TEST` already being imported in the module.

Resolution: the analysis coordinate is now owned by a single canonical builder. `personalization.ditto_analysis_directory(regularization, *, output_root)` composes `ExecutionRootDirectory.DITTO_STRESS_TEST / PopulationId.NBAIOT_NATURAL_DEVICES.value / DittoArtifactBranch.ANALYSIS / str(regularization.value)` (with `DittoArtifactBranch.ANALYSIS = "analysis"` added to the existing enum), and both the marker (`_ditto_analysis_marker_present`, campaign.py:985-991) and the report handler (`_report_ditto_absorption_stress_test`, campaign.py:714-746) call it. The marker checks both `PUBLICATION_FILENAME` and `MECHANISM_REPORT_FILENAME` under that root. No raw path fragment remains in either function.

### [SEV-LOW] `_fedprox_analysis_marker_present` hardcodes path/role literals — FIXED

Reported: `"fedprox_stress_test"`, `"primary_coefficient_decision.json"`, `"analysis"`, and the role tuple `("primary","sensitivity")` were duplicated against the writer side.

Resolution: the FedProx analysis coordinate is now owned by canonical constants and builders in `personalization.py`. `fedprox_stress_test_root(*, output_root)` composes `ExecutionRootDirectory.FEDPROX_STRESS_TEST` (new member added to `ExecutionRootDirectory` in `layout.py`) with `PopulationId.NBAIOT_NATURAL_DEVICES.value`; `fedprox_analysis_directory(coefficient, role: FedProxRoleDirectory, *, output_root)` appends `FedProxArtifactDirectory.ANALYSIS / role.value / str(coefficient.value)`. The role vocabulary is the new `FedProxRoleDirectory` enum (`PRIMARY="primary"`, `SENSITIVITY="sensitivity"`), the decision filename is the `FEDPROX_PRIMARY_COEFFICIENT_DECISION_FILENAME` constant, and the decision artifact is written/loaded through `write_fedprox_primary_coefficient_decision` / `load_fedprox_primary_coefficient_decision` (typed `FedProxPrimaryCoefficientDecision` round-trip via `canonical_json_text`, replacing the previous ad-hoc role-literal payload). Marker (campaign.py:956-982) and report handler (`_report_fedprox_absorption`, campaign.py:788-837) share all of these, so the marker, the writer, and the loader agree on every path segment and role assignment.

### [SEV-LOW] Ditto dispatch asserts completion instead of deriving — FIXED

Same defect as REVIEWER_3's Ditto finding; fixed by deriving `completed_by_seed` from the returned `DittoStressTestResult` objects. See above.

### [SEV-LOW] `ThresholdMethodExecutionStatus` vocabulary overlaps other enums — ACCEPTED

Reported: members `UNAVAILABLE = "unavailable"` and `INFEASIBLE = "infeasible"` duplicate string values in `AvailabilityStatus` and `ExperimentReadiness`.

Acceptance rationale: the domains are distinct — per-threshold-method execution status (`ThresholdMethodExecutionStatus`) vs per-metric availability (`AvailabilityStatus`) vs experiment-level readiness (`ExperimentReadiness`). A threshold method being unavailable at a partition is not the same categorical domain as a metric being unavailable for a population; forcing a shared enum would couple unrelated state machines. The values coincide because English words for "unavailable" and "infeasible" are fixed; CLAUDE.md §8.1 forbids duplicating the same *vocabulary* (set of members describing one closed domain), not reusing a word across different domains. No behavioral consequence. Accepted as a letter-of-the-rule vs spirit-of-the-rule judgment.

### [SEV-LOW] Ditto/temporal evidence persist/load duplicate pattern — ACCEPTED

Reported: the two new evidence stores implement the same checksum-protected round-trip (write `seed.json` via `canonical_json_text`, write `COMPLETE` via `canonical_checksum`, load via `TypeAdapter.validate_json` + re-verify).

Acceptance rationale: the shared integrity mechanism is the repository's canonical JSON/checksum pattern already used elsewhere (it IS the reuse), and the two call sites differ in their typed record (`DittoStressTestEvidence` vs `TemporalSeedResult`) and their directory builders (`ditto_directory` vs `_temporal_seed_evidence_directory`). Extracting a generic checksummed-evidence helper would require a type-parameterized store abstraction with two instantions and one non-trivial caller each — precisely the "abstraction with only one trivial caller and no domain value" that CLAUDE.md §5 forbids. The duplication is ~10 small lines per side. Accepted; consolidation would reduce clarity without reducing complexity.

### [SEV-LOW] `FAILED` reserved but unused — ACCEPTED

`ThresholdMethodExecutionStatus.FAILED` is never constructed in production code (grep confirms). It is a reserved member of a typed status lattice that the ledger's outcome vocabulary licenses; its absence from construction is the current evidence state, not a dropped failure (a genuine execution failure raises before an outcome is built). Same disposition as Reviewer 3's equivalent note. Accepted.

### [OK] Verified-clean list — confirmed

- Fixed-detector invariant preserved; `run_ditto_absorption_campaign` / `run_temporal_campaign` deleted with zero callers.
- No new hardcoded scientific values, no hidden defaults/fallbacks, no `Any`, no `dict[str, Any]` domain I/O, no suppressions.
- Dispatch iteration order deterministic; output_root threaded so smoke cannot pollute real outputs.
- Typed contracts strengthened (`DispatchOutcome` / `ThresholdMethodOutcome` / `ThresholdMethodExecutionStatus`).
- Roadmap-locked identifiers preserved; evidence integrity checksum-bound.

---

## Additional finding from this reconciliation pass

### [SEV-LOW] Dead parallel FedProx orchestration — FIXED

During verification of R4's reuse findings, `run_fedprox_coefficient_campaign` and `run_fedprox_grid_campaign` (personalization.py) were found to have **zero production callers** — the only references were the (now deleted) smoke dispatch path and a `hasattr` assertion in `tests/e2e/test_fedprox_stress_pipeline.py`. They were the last full-cohort parallel orchestration path left after WR-005 moved the dispatch to the passed-seed subset. Per CLAUDE.md §6 (deletion bias) and §7 (no backward compatibility), both functions were deleted; the e2e `hasattr` assertions for them were removed. The analysis path (`collect_fedprox_coefficient_terminal_losses`) reads artifacts from disk and is unaffected. This also removed a pylint `R0801 duplicate-code` finding introduced by the new dispatch mirroring the dead function's call pattern.

---

## Disposition summary

| Reviewer | Finding | Disposition |
|---|---|---|
| 1 | WR-010 anchor failure not surfaced end-to-end | FIXED |
| 2 | best-effort aggregate report | ACCEPTED |
| 3 | temporal outcome all-states/all-seeds overclaim | FIXED |
| 3 | `_seed_completion_outcomes` union overclaim | FIXED |
| 3 | Ditto dispatch asserts completion | FIXED |
| 3 | INFEASIBLE detail unverified | FIXED |
| 3 | FedProx "seeds" mis-count | FIXED |
| 3 | `_evaluate_state` total-unavailability raise | ACCEPTED |
| 3 | FedProx marker any-role acceptance | FIXED (decision-derived role) |
| 4 | Ditto marker raw path fragment | FIXED |
| 4 | FedProx marker raw path/role literals | FIXED |
| 4 | Ditto dispatch asserts completion | FIXED |
| 4 | enum vocabulary overlap | ACCEPTED |
| 4 | duplicate evidence persist/load pattern | ACCEPTED |
| 4 | `FAILED` reserved-unused | ACCEPTED |
| — | dead FedProx orchestration (reconciliation) | FIXED |
| — | marker/report path + asset-name literal sweep (reconciliation) | FIXED |

All FIXED dispositions are covered by regression tests where a testable contract exists; every FIXED and ACCEPTED item was verified against the final working tree, not against memory of the diff.

## Additional finding from the literal-sweep reconciliation pass

### [SEV-LOW] Remaining path/asset-name literals in marker/report/evidence code — FIXED

A final diff sweep of every changed `src/` file classified every remaining quoted literal in the working tree. Each was either an enum member value, a constant declaration, or a docstring fragment — but before the sweep, several literal usages remained at call sites:

- `"seed.json"` in the Ditto and temporal seed-evidence persist/load functions (personalization.py:173-185, temporal.py:272-283) is now `SeedEvidenceAssetName.DOCUMENT`; the paired `"COMPLETE"` marker is now `AnalysisAssetName.COMPLETE` (the same canonical evidence asset-name enum already used by the confirmatory/external/temporal analysis publishers).
- `"publication.md"` and `"mechanism_report.md"` in `reporting/export.py` are now `PUBLICATION_FILENAME` and `MECHANISM_REPORT_FILENAME` module constants; every write site (4 publication, 1 mechanism-report) references them.
- The FedProx decision artifact filename is now the `FEDPROX_PRIMARY_COEFFICIENT_DECISION_FILENAME` constant, and `write_fedprox_primary_coefficient_decision` / `load_fedprox_primary_coefficient_decision` serialize the typed `FedProxPrimaryCoefficientDecision` directly (via `canonical_json_text` / `TypeAdapter.validate_json`), removing the previous hand-built role-literal payload dict (§9.2).

Post-sweep, no changed function under `src/` composes a path or asset name from a bare literal; all such values come from the canonical enums, constants, or builders listed above.
