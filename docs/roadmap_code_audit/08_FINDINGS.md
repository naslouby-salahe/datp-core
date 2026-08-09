# 08 — Findings Ledger (First Audit)

Ten parallel read-only discovery subagents audited: CLI/execution-spine/registry, datasets/populations,
splits/preprocessing, training/checkpoints, scoring/artifact-identity, calibration/thresholds,
metrics/statistics, anchor/temporal, artifacts/provenance/reuse, reporting/dead-code/canonical-tree, and
experiment-catalogue/numerical-locks/naming. Every raw subagent claim below was independently re-verified
against current source (not merely trusted) before being recorded as a finding, per repo memory lessons on
subagent-audit false positives.

## Rejected / downgraded raw subagent claims (independently verified false or overstated)

- **CLI subagent DEFECT-003** ("no test asserts registry/recipe consistency"): **FALSE** — `tests/unit/app/test_programme.py::test_every_non_suppressed_experiment_has_exactly_one_recipe` already asserts this exactly. No action needed.
- **Artifacts subagent COLLISION-001** ("HIGH — no runtime collision detection for `ExperimentCoordinate`"): **REJECTED_FALSE_POSITIVE (downgraded)** — `stable_key` structurally encodes every scientifically relevant dimension and coordinates are only ever produced by deterministic plan-expansion from declared registry grids (never open user input), so cross-condition collision is prevented by construction, not merely by convention. See `05_EXPERIMENT_AUDITS.md`.
- **Threshold-audit subagent's own report table** used shorthand labels `B1/B2/B3/B4` next to `SHARED_THRESHOLD/LOCAL_THRESHOLD/FAMILY_THRESHOLD/CLUSTER_THRESHOLD` — **verified these are the subagent's own annotation, not code**: `grep -rn "B0\|B1\b\|B2\b\|B3\b\|B4\b\|Regime [A-D]"` against `src/datp_core/thresholds/policies/` returns zero matches. No naming-discipline violation exists in source.

## Confirmed findings

### ARCH-001 — `artifacts/repositories/` file-location vs. CLAUDE.md diagram (RESOLVED — contract corrected)
- **Original observation**: `artifacts/repositories/` lacked dedicated `populations.py/preprocessing.py/checkpoints.py/scores.py` files that an earlier, more literal reading of CLAUDE.md's diagram implied were required; persistence/reuse logic for those domains is colocated with its owning package (`data/populations/`, `data/preprocessing/`, `detector/checkpoints/`, `detector/scoring/`) instead.
- **Resolution**: at the user's direction, CLAUDE.md §3 was rewritten to remove the literal file-tree diagram (which was producing false architecture-deviation findings) and now states the actual ownership rule directly: domain packages may keep persistence orchestration colocated with their validation logic, but the underlying atomic-publish/checksum/reload primitives must delegate to `artifacts` rather than reimplementing them. The current domain-colocated design already satisfies this rule (verified: `data/populations/publication.py`, `data/preprocessing/publication.py`, and `data/materialization.py` all call `artifacts/repositories/publication.py`'s `publish_artifact`/`publish_atomically` directly — no reimplementation remains, see ARCH-004 below). **Also found and deleted**: `artifacts/repositories/datasets.py` was itself fully dead code (a simpler, superseded prototype with zero callers, missing the asset-role/exclusion/provenance richness `data/materialization.py` actually needs) — removed rather than resurrected.
- **Status**: RESOLVED.

### ARCH-002 — `artifacts/serializers/` safetensors/skops consolidation (RESOLVED)
- **Original observation**: `safetensors.torch.{save_file,load_file,save}` used directly (and with duplicated cpu-contiguous-conversion/reload-verification logic) in `detector/checkpoints/candidates.py`, `detector/scoring/frames.py`, `detector/training/{centralized,engine}.py`.
- **Fix**: created `artifacts/serializers/safetensors.py` owning the genuinely duplicated logic — `to_cpu_contiguous_state()`, `save_state_dict_tensors()`, `load_state_dict_tensors()` (the exact "detach/cpu/contiguous + save_file/load_file + checksum" sequence was byte-for-byte duplicated in 3 places). All 4 call sites now delegate to it; the two *different* reload-verification functions (`_assert_checkpoint_reload_equality` in candidates.py vs. `assert_safetensors_reload` in centralized.py, which have genuinely different semantics — one validates a raw tensor dict, the other round-trips through a reconstructed model) were kept separate rather than force-merged, since collapsing them would risk weakening one of the two checks.
- **`skops` left as-is**: `data/preprocessing/state.py`'s trusted-estimator-class list is preprocessing-domain-specific (not a generic serialization concern); a generic `artifacts/serializers/skops.py` wrapper here would be a thin pass-through, which CLAUDE.md §11 separately forbids. No change made.
- **Also found and eliminated** (per user follow-up: "do not create such thin wrappers/redirects"): the ARCH-002 fix initially left `centralized.py::persist_state_dict_tensors()` as a one-line pass-through to the new shared function. Deleted; its 2 real callers (`centralized.py`, `checkpoints/service.py`) now call `save_state_dict_tensors()` directly.
- **Status**: RESOLVED.

### ARCH-003 — Experiment-package `spec.py`/`analyze.py`/`report.py` split (RESOLVED — contract corrected)
- **Original observation**: 7 of 9 non-anchor/confirmatory experiment packages consolidate into a single `run.py` rather than the `spec/run/analyze/report` quartet a literal reading of the old CLAUDE.md diagram implied; `experiments/applicability/` has no domain modules at all (its one experiment is implemented in `experiments/external/run.py`).
- **Resolution**: same CLAUDE.md §3 rewrite as ARCH-001 — the contract no longer prescribes an exact file-per-experiment layout, only that experiment packages own their declarations/run/report recipes, which they already do. No recomputation-of-science defect was ever found in this area (`07_PUBLICATION_REVERSE_TRACE.md`).
- **Status**: RESOLVED.

### ARCH-004 — Third duplicated atomic-publish-lifecycle implementation (RESOLVED)
- **Observed**: `data/publication.py::publish_canonical_atomically()` reimplemented the same lock/stage/reuse-check/atomic-replace lifecycle as `artifacts/repositories/publication.py::publish_atomically()`, for canonical dataset materialization. Sole caller: `data/materialization.py::publish_canonical()`.
- **Fix**: `data/materialization.py` now calls `publish_atomically()` directly (with `overwrite=False`, matching the prior behavior — overwrite is handled upstream in `data/service.py` before this function is ever reached). The now-fully-redundant `data/publication.py` module (`DatasetPublicationOutcome` was a byte-for-byte structural duplicate of `ArtifactPublicationResult`) was deleted entirely rather than kept as a thin redirect.
- **Status**: RESOLVED. Verified: 859/859 tests pass, `ruff check .` clean, `pyright` 0 errors on all touched files.


## Summary

- **BLOCKER/CRITICAL/MAJOR findings: 0.**
- **ARCH-001/002/003/004: all RESOLVED** (CLAUDE.md's file-tree diagram removed at user direction and replaced with an ownership-only contract; the one genuinely duplicated atomic-publish-lifecycle instance with a safe, low-risk fix path (`data/publication.py`) was eliminated entirely; safetensors serialization consolidated into `artifacts/serializers/safetensors.py`; a thin one-line redirect function introduced during that consolidation was caught by user review and removed, with callers pointed at the shared function directly).
- **Real bugs found and fixed along the way** (not originally part of the architecture findings, discovered while investigating duplication): a wrong duplicate `split_protocol_for_population()` in `data/populations/contracts.py` that silently returned the wrong split protocol for `EDGE_SENSOR_GROUPS`; a ~150-line dead duplicate of the entire FedAvg/FedProx/Ditto protocol-declaration block in `detector/training/contracts.py` (protocols.py's copy is the one every real caller uses); several smaller confirmed-dead functions/classes (`artifacts/repositories/datasets.py` in full, `validate_checkpoint_inventory_files`, `centralized_candidate_set_checksum` + duplicate `CentralizedCheckpointSetEntry`, unused federated `CheckpointSetEntry`, `echo_lines`) \u2014 each independently verified via AST-precise repo-wide import analysis (not just text grep) before deletion, after an initial text-grep-only check missed one real test-file caller (caught and fixed).
- No scientific-correctness defect, leakage, contamination, artifact-collision, or fabrication was found across any of the 10 originally-audited domains, confirmed independently by 4 adversarial reviewers.
- Final verification: 859/859 tests pass, `ruff check .` clean (only the user's own intentional TODO comments in `data/nbaiot/schema.py` remain, explicitly preserved per instruction), `pyright` 0 errors on every touched file.
