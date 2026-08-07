# Pre-State — Execution Foundation and Runtime Correctness

Audit scope: ACT-001, ACT-002, ACT-003, ACT-009 and directly related smoke/report/campaign/status defects (WR-004..WR-010).

Authority: `docs/Journal_Extension_Master_Roadmap.md` (fully read) > validated config > typed contracts > implementation > tests.

Date: 2026-08-07.

---

## Finding classification

| Finding | Audit claim | Classification | Evidence (file:line) |
|---|---|---|---|
| ACT-001 / WR-004 | Smoke poisons production output root | **STILL DEFECTIVE** | campaign.py L229/L238 `del output_root` in external dispatch handlers; L258/L267 `del output_root, overwrite` in Ditto/Temporal dispatch. Seed fns hide `output_root: Path \| None = None` defaults → OUTPUTS_ROOT (external.py L96, confirmatory.py L125/L158, personalization.py L476/L487/L505). |
| WR-005 | Smoke runs full FedProx grid instead of requested seed subset | **STILL DEFECTIVE** | campaign.py L246-254 `del seeds`; `run_fedprox_grid_campaign` iterates all FEDPROX_COEFFICIENTS x full CONFIRMATORY_SEED_COHORT. |
| ACT-002 / WR-006 | Report re-executes training (Ditto/Temporal) | **STILL DEFECTIVE** | campaign.py L553 `run_ditto_absorption_campaign` (trains all seeds); L561 `run_temporal_campaign` (trains all seeds). Both inside report handlers. |
| ACT-003 / WR-007 | Campaign triple-executes experiments | **STILL DEFECTIVE** | campaign.py L351 in-loop `generate_report(experiment_id, ...)` + L357 final `generate_report(None, ...)` → Ditto/Temporal execute 3x per campaign (2 in-loop report + 1 final) plus 1 execute pass. |
| WR-008 | Threshold-method execution outcomes discarded | **STILL DEFECTIVE** | Dispatch handlers return `str`; FedProx handler reports `len(results)` only; `completed_threshold_methods` (execution.py L92-93) never surfaced through dispatch. Ditto/Temporal build their own in-memory method outcomes not persisted. |
| ACT-009 / WR-009 | Analysis-complete status unreachable for FedProx/Ditto/Temporal | **STILL DEFECTIVE** | campaign.py `_ANALYSIS_MARKER_CHECKS` has only 4 entries (confirmatory x2, external x2); `_analysis_marker_present` returns False for missing FedProx/Ditto/Temporal (L721-750). |
| WR-010 | Smoke swallows anchor/scientific/prerequisite failures | **STILL DEFECTIVE** | campaign.py L324-325 `except (...) as error: _ = error` in `run_smoke` full branch. |
| ACT-009 sub | `_analysis_marker_present` must return bool for every registered workflow | constraint from test_registry_consistency.py | Current impl returns False when marker absent — ok for registered-without-marker but must be extended to real marker checks. |

## Already-correct boundaries preserved

- `reproduce_anchor(*, overwrite, smoke)` already uses `SMOKE_OUTPUT_ROOT if smoke else OUTPUTS_ROOT` (campaign.py L377) and smoke seed `HISTORICAL_ANCHOR_SEED_COHORT.values[0]` (L386). Anchor failure surfaced as typed BLOCKED result (L411-416). Keep.
- Confirmatory + external (bounded) + FedProx already follow pure-report pattern: execution persists evaluation docs; report loads + analyzes. Only Ditto/Temporal violate.
- `execute_declared_experiment_seed`/`execute_declared_campaign` raise ScientificContractError on any failed coordinate (BLOCKED) — correct, keep.
- `PipelineStageRunner` catches ScientificContractError → BLOCKED; `CompletionRecordOutputStore.state()` ABSENT/COMPLETE_VALID/COMPLETE_INVALID/INCOMPLETE — correct, keep.

## Scientifically intentional unavailable/suppressed

- CV(FPR) ddof=0, no epsilon → UNDEFINED when mean=0: intentional (roadmap).
- `ThresholdUnavailableResult` for size-aware shrinkage / unsupported method on a dataset: intentional typed unavailability — must be SURFACED (WR-008), not converted to failure nor silently dropped.
- Temporal `_evaluate_state` L396-397 `if isinstance(threshold, ThresholdUnavailableResult): continue` — currently discards; must surface as method outcome (WR-008).
- Edge-IIoTset attack metrics UNAVAILABLE via capabilities: intentional, keep.

## Superseded / out of scope

- ACT-004 (B0 centralized reference wiring), ACT-005 (pooled min-max), ACT-006 (15 workflow modules), ACT-007 (size-aware shrinkage), ACT-008 (eval diagnostics), ACT-010..016 (dead code, metrics, dispatch merge, etc.): OUT OF SCOPE for this prompt (execution foundation only). Do not touch.
