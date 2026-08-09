# 10 — Reviewer Findings (Independent Review)

Four independent adversarial reviewer subagents (read-only, did not trust `docs/roadmap_code_audit/*.md`,
re-derived evidence from current source) were dispatched in parallel after the first audit was frozen.

## Reviewer 1 — scientific causal integrity
Verdict: **CONFIRMED_CORRECT** on all 6 targeted adversarial attempts (fixed-detector caching, threshold-policy
score isolation, benign-only calibration end-to-end trace, checkpoint-selection independence, anchor gate
14-condition enforcement in `experiments/anchor/gate.py`, genuinely separate FedAvg detector per Dirichlet
severity cell). No findings.

## Reviewer 2 — execution and architecture
Two findings, both independently re-verified by me before acceptance:

1. **ACCEPTED** — Recipe-count documentation error: `01_REPOSITORY_AND_CLI_INVENTORY.md` claimed 23 wired
   recipes; direct `grep -c "ExperimentRecipe("` on `app/recipes.py` gives **22** (22 + 1 anchor-only + 1
   suppressed = 24, correctly reconciling). **Fixed**: corrected `01_..md` and `00_AUDIT_CONTROL.md`.
2. **ACCEPTED** — `data/preprocessing/publication.py::publish_processed()` reimplemented the generic
   atomic-publish lifecycle (locking, staging, reuse-check, atomic replace, completion-digest) instead of
   calling `artifacts/repositories/publication.py::publish_artifact()`/`ArtifactPublication`/
   `FunctionalArtifactCodec`, the pattern already used by `data/populations/publication.py` and
   `detector/scoring/federated.py`. This is a genuine violation of CLAUDE.md §11 ("delete duplicated
   path/checksum/lifecycle logic") and directly refutes the first audit's blanket deferral of ARCH-001/002
   (the deferral was reasonable for the *broader* file-relocation question, but this specific case had only
   one caller and a real, pre-existing generic mechanism to delegate to — not a thin-wrapper risk).
   **Fixed this session**: `publish_processed()` now delegates to `publish_artifact()`, reusing the generic
   `complete_digest()` instead of a locally-duplicated one; public API (`ProcessedPublication`,
   `ProcessedPublicationResult`, `publish_processed`) unchanged, so the sole caller
   (`data/preprocessing/artifact_validation.py`) needed no changes. Verified: 36/36 preprocessing tests pass
   unchanged, full suite (859 tests) passes, `ruff check .` clean, `pyright` scoped to the changed package
   clean.

Other checks in Reviewer 2's scope (exception-handling audit of all `except Exception` blocks, hardcoded
`overwrite=True` search, bare-`pass`/`NotImplementedError`/TODO/FIXME sweep, all 22 recipe dispatch/report
handlers) came back CONFIRMED_CORRECT / FALSE_POSITIVE, no further action.

## Reviewer 3 — datasets, artifacts, provenance
Verdict: **CONFIRMED_CORRECT** on all 6 targeted adversarial attempts (no CICIoT2023 physical-device
inference path found anywhere including dead code; Edge-IIoTset chronology never defaulted/estimated,
Modbus exclusion is a simple robust enum check not a fragile timestamp heuristic; checksum payloads are
complete, not truncated; checkpoint writes are atomic with `os.replace`/`FileLock` and reload verification;
preprocessing fit-benign-only gate is on the sole `.fit()` call site reachable by every training mode;
checksum comparisons are always full-value). No findings.

## Reviewer 4 — metrics, statistics, publication
Verdict: **CONFIRMED_CORRECT** on all 6 targeted adversarial attempts, including hand-worked numeric
recomputation of FPR/TPR/BA/Macro-F1/CV(FPR)/IQR/Gini/Jain against toy examples, BCa z0/acceleration/
jackknife-by-seed verification, degenerate-interval handling, single non-conflicting Holm implementation,
no pre-statistic rounding, and explicit `ddof=0` for CV(FPR)'s population standard deviation. One
informational (non-defect) observation: `MultiplicityPlan` is never instantiated in current production call
sites because no analysis currently publishes uncorrected secondary p-values — noted, not actioned (not a
defect; would become one only if a future analysis started reporting uncorrected secondary tests without
routing through Holm correction first).

## Reviewer disposition summary

| Category | Count |
|---|---|
| Findings proposed | 2 (both by Reviewer 2) |
| Accepted | 2 |
| Rejected (false positive) | 0 |
| Duplicate of existing finding | 0 |
| Out of scope | 0 |
| Accepted findings fixed | 2/2 |
