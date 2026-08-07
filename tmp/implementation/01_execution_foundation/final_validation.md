# Final Validation — Execution Foundation

Validation evidence for the completed execution-foundation work (WR-004, WR-005, WR-006, WR-007, WR-008, WR-009, WR-010) on the final working tree.

Companion documents: `implementation_notes.md` (design decisions), `pre_state.md` (pre-change classification), `reviewers/REVIEWER_{1..4}.md` (independent audit), `review_resolution.md` (reconciliation).

---

## Changed files

| File | Change |
|---|---|
| `src/datp_core/pipeline/workflows/campaign.py` | Smoke isolation (`_output_root`, scoped rmtree, smoke summary root); FedProx dispatch honors passed seeds; report handlers become pure evidence consumers; single-pass `run_campaign` (in-loop report removed); `ThresholdMethodOutcome`/`DispatchOutcome`/`CampaignRunResult.anchor_failure`; intersection-based `_seed_completion_outcomes` and `_temporal_method_outcomes`; Ditto/FedProx/Temporal analysis markers using layout enums; exact-set dispatch/report/marker registry enforcement; CLI-facing outcomes |
| `src/datp_core/cli/app.py` | `smoke_command` echoes `anchor_failure`; per-experiment `methods={method}={status}` echo |
| `src/datp_core/cli/execution.py` | Experiment command echoes method outcomes |
| `src/datp_core/domain/enums.py` | `ThresholdMethodExecutionStatus` (COMPLETED/UNAVAILABLE/INFEASIBLE/FAILED); `FedProxRoleDirectory` (PRIMARY/SENSITIVITY) |
| `src/datp_core/pipeline/decision/evidence.py` | `SeedEvidenceAssetName.DOCUMENT = "seed.json"` (alongside the existing `AnalysisAssetName`) |
| `src/datp_core/pipeline/execution/layout.py` | `ExecutionRootDirectory.FEDPROX_STRESS_TEST` member |
| `src/datp_core/pipeline/workflows/confirmatory.py` | `output_root` threaded (no hidden default); analysis-path helpers |
| `src/datp_core/pipeline/workflows/external.py` | `output_root` threaded into bounded-external seed paths; analysis helpers |
| `src/datp_core/pipeline/workflows/personalization.py` | Ditto evidence persistence (`SeedEvidenceAssetName.DOCUMENT` + checksummed `AnalysisAssetName.COMPLETE`) + loader; `DittoArtifactBranch.ANALYSIS` + new `FedProxArtifactDirectory` enum; canonical builders `ditto_analysis_directory` / `fedprox_stress_test_root` / `fedprox_analysis_directory`; `FEDPROX_PRIMARY_COEFFICIENT_DECISION_FILENAME` constant; typed `write_fedprox_primary_coefficient_decision` / `load_fedprox_primary_coefficient_decision` round-trip (replaces ad-hoc role-literal payload); `output_root` threaded; Ditto dispatch derives completion; dead FedProx grid/coefficient orchestration deleted |
| `src/datp_core/pipeline/workflows/temporal.py` | Temporal seed evidence persistence + loader using the canonical asset-name enums; `output_root` threaded; unavailable-method surfacing |
| `src/datp_core/reporting/export.py` | `PUBLICATION_FILENAME` / `MECHANISM_REPORT_FILENAME` constants; every publication/mechanism-report write site references them |
| `tests/unit/cli/test_cli.py` | Anchor-failure CLI echo tests (+2) |
| `tests/unit/pipeline/workflows/test_smoke_anchor_failure.py` | NEW — smoke anchor surfacing (raise / BLOCKED / PASS) |
| `tests/unit/pipeline/workflows/test_temporal_method_outcomes.py` | NEW — temporal intersection outcome semantics |
| `tests/scientific/test_fedprox_primary_coefficient_from_training_history.py` | Decision artifact now asserted via `load_fedprox_primary_coefficient_decision` round-trip (typed equality) instead of raw-string role literal |
| `tests/e2e/test_fedprox_stress_pipeline.py` | Removed `hasattr` assertions for deleted dead orchestration |

## Reused or removed

- **Deleted**: `run_ditto_absorption_campaign`, `run_temporal_campaign` (report-path re-training wrappers); `run_fedprox_coefficient_campaign`, `run_fedprox_grid_campaign` (dead parallel orchestration, zero production callers after WR-005); optional `output_root: Path | None = None` fallbacks on seed functions; ad-hoc FedProx decision payload dict (role literal) replaced by typed serialization.
- **Reused**: `execute_declared_experiment_seed` / `execute_declared_campaign` for all seed runs; `seed_cohort_for` / `canonical_smoke_seed` for cohorts; `canonical_checksum` + `canonical_json_text` + `TypeAdapter.validate_json` for checksummed evidence; `ditto_directory`/`bounded_evidence_seed_directory` path builders; `ExecutionRootDirectory`/`DittoArtifactBranch`/`AnalysisAssetName` enums for marker and evidence paths; existing `load_*`/`analyze_*` functions in report handlers.
- **Added canonical vocabulary**: `FedProxRoleDirectory`, `SeedEvidenceAssetName`, `FedProxArtifactDirectory`, `DittoArtifactBranch.ANALYSIS`, `PUBLICATION_FILENAME`, `MECHANISM_REPORT_FILENAME`, `FEDPROX_PRIMARY_COEFFICIENT_DECISION_FILENAME`, and the `ditto_analysis_directory` / `fedprox_stress_test_root` / `fedprox_analysis_directory` builders — so no marker, report handler, or evidence function under `src/` composes a path or asset name from a bare literal.

## Scientific invariants verified

Against `docs/Journal_Extension_Master_Roadmap.md` (authoritative) and `CLAUDE.md` §2/§3:

- Fixed detector preserved: reports consume persisted evidence, never re-train. Roadmap's fixed-detector/threshold-scope ladder intact.
- Threshold-scope ladder remains the controlled dimension; training-side comparators (FedProx/Ditto stress tests) remain outside the controlled ladder and are not promoted into confirmatory claims.
- Same eligible score artifacts reused across threshold-policy comparisons (report handlers load canonical evidence).
- Calibration remains benign-only; attack data remain evaluation-only; threshold construction does not access test labels/outcomes (unchanged pipeline boundaries).
- AUROC remains model-quality control, not the threshold-policy verdict (unchanged).
- Per-client FPR disparity remains the central operating point (unchanged metric set).
- Claim tiers separated: confirmatory / supportive / stress-test / boundary-condition evidence kept distinct; no result promoted.
- Determinism: seed cohorts from configuration, stable iteration order (seed-major, fixed coefficient order, fixed temporal state order), deterministic smoke seed, deterministic dispatch expansion.
- No new hardcoded scientific values, no hidden defaults, no hidden fallbacks introduced; missing/unsupported state fails clearly (checksum mismatch → `ScientificContractError`; missing report evidence → typed error; unregistered experiment → exact-set enforcement error).

## Validation executed

| Check | Result |
|---|---|
| `pytest tests/unit/ tests/property/ tests/scientific/ tests/integration/` | 844 passed |
| `pytest tests/e2e/` | 11 passed |
| `ruff check src/datp_core tests/unit tests/e2e` | All checks passed |
| `ruff format --check` on all 11 changed `src/` files | 11 files already formatted |
| `pyright` on all 11 changed `src/` files | 0 errors, 0 warnings, 0 informations |
| `pylint` on all 11 changed `src/` files | 9.73/10; remaining findings pre-existing (W0621 `AnalysisDocumentT` redefined-outer-name in evidence.py, 2× R0914 too-many-locals in confirmatory.py/temporal.py, R0911/R0912 in export.py, 3× R0801 duplicate-code paired-contrast/evaluation-load helpers in confirmatory.py/external.py, lazy `import-outside-toplevel` dispatch-local pattern in campaign.py) — none from the literal sweep |
| `import-linter lint` | 13 contracts kept, 0 broken |
| Architecture/import-contract tests (`test_package_imports.py`, `test_architecture_boundaries.py`, `test_analysis_architecture.py`, `test_federated_architecture.py`, `test_scoring_architecture.py`, `test_fixed_detector_contract.py`) | 33 passed |
| Deterministic rerun of outcome tests | `test_temporal_method_outcomes.py`, `test_smoke_anchor_failure.py`, CLI anchor tests pass repeatedly |
| Literal sweep of the full `src/` diff | Every remaining quoted literal is an enum member value, constant declaration, or docstring fragment; zero usage-site path/asset-name literals remain in changed functions |

Full-suite total across all four local suites plus e2e: 855 passed (844 unit/property/scientific/integration + 11 e2e).

## Not run (external analysis gates)

CLAUDE.md §18.1 requires the SonarQube CLI (`sonar analyze`) and CodeScene (`cs delta`) from the repository root with credentials sourced from `.env`. These were **not run** in this session: they require the `.env` credential loader and network access to `sonarcloud.io`, and this environment did not surface the tokens or a verified uncommitted-revision policy for remote analysis. This is recorded here as an unavailability of the service-side analysis environment, distinct from a code-quality pass. The local gates above (ruff, pyright, pylint, import-linter, full test suite) are complete.

## Remaining issues

- None blocking. All reviewer findings resolved (FIXED or ACCEPTED with rationale in `review_resolution.md`); the FedProx any-role marker finding is now FIXED (decision-derived role) rather than ACCEPTED.
- Pre-existing (unrelated to this work, not introduced by this diff): W0621 `AnalysisDocumentT` redefined-outer-name in evidence.py; 2× `R0914 too-many-locals` (confirmatory.py, temporal.py) and R0911/R0912 (export.py) complexity findings in unchanged regions; 3× `R0801 duplicate-code` (paired-contrast and evaluation-document helpers shared between confirmatory.py and external.py); lazy `import-outside-toplevel` imports in campaign.py (intentional dispatch-local imports, pre-existing pattern).
