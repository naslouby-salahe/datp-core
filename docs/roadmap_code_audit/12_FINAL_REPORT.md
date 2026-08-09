# 12 — Final Report

## Audit identity
- Repository commit at start: `2cfb6fc42aa9ef4581b7a4ce29def59d81d3b18f` (branch `main`, clean working tree).
- Matrix path: `docs/Journal_Extension_Audit_Matrix.md`, sha256 `440bf9d7da012a5ae9ef30ae2ced38ea6e483f7dd72fc02537e1361d587e137c`, 7,439 lines.
- Roadmap path: `docs/Journal_Extension_Master_Roadmap.md`, 3,675 lines.
- Graphify: pre-existing index at `graphify-out/` used as a navigation accelerator; direct source inspection was the verification method for every finding recorded.
- Requirement count: ~1,734 traceability rows (per prior independent reconciliation, re-used as a scale reference); audited domain-by-domain by 10 parallel discovery subagents rather than row-by-row (disclosed scope limitation, see `03_REQUIREMENT_COVERAGE.md`).
- Experiment/analysis count: 24 (matrix and registry both), 22 recipe-wired + 1 anchor-only + 1 suppressed.
- CLI workflow count: 8 top-level commands, 11 total command+subcommand combinations, all verified by direct execution and source inspection.

## First audit
10 parallel read-only discovery subagents covering CLI/execution-spine/registry, datasets/populations,
splits/preprocessing, training/checkpoints, scoring/artifact-identity, calibration/thresholds,
metrics/statistics, anchor/temporal, artifacts/provenance/reuse, and reporting/dead-code/experiment-
catalogue/numerical-locks/naming. Every raw subagent claim was independently re-verified against current
source before being recorded (2 raw claims rejected as false positives after direct re-verification).

- PASS (domain-level): 12/12 audited domains had zero scientific-correctness defects.
- MODERATE architecture findings: 2 (ARCH-001, ARCH-002 — canonical `artifacts/` file-location deviation).
- LOW architecture findings: 1 (ARCH-003 — experiment-package file-splitting convention).
- BLOCKER / CRITICAL / MAJOR: 0.
- Total first-audit findings: 3.

## Fix pass
- 0 scientific-correctness defects required fixing (none were found).
- 0/3 first-audit architecture findings fixed at freeze time (explicitly deferred with disclosed
  engineering rationale: high blast-radius vs. no scientific consequence, and risk of introducing the
  CLAUDE.md-forbidden "thin pass-through wrapper" anti-pattern if done superficially).

## Independent reviewers
4 parallel adversarial reviewers (scientific causal integrity; execution & architecture; datasets/
artifacts/provenance; metrics/statistics/publication), each explicitly instructed to try to falsify the
"clean" first-audit verdict against current source, not the audit documents.
- Findings proposed: 2 (both by the execution/architecture reviewer).
- Accepted: 2/2 (independently re-verified by direct source inspection before acceptance).
- Rejected: 0. Duplicates: 0. Out of scope: 0.
- Fixed: 2/2 — (a) a recipe-count documentation arithmetic error (23→22, corrected); (b)
  `data/preprocessing/publication.py::publish_processed()` was reimplementing the generic atomic-publish
  lifecycle instead of delegating to `artifacts/repositories/publication.py::publish_artifact()` — refactored
  to delegate, public API unchanged, verified via the full test suite (859 passed), `ruff check .` (clean),
  and `pyright` scoped to the changed package (0 errors).

## Second audit
Fresh re-derivation (not a re-statement of iteration-1 conclusions) of: recipe/registry/matrix counts,
a repository-wide search for other instances of the same duplicated-lifecycle root cause, and a full
listing of every `experiments/*` subpackage's actual file contents.
- New confirmed findings: 1 (`ARCH-004` — a third duplicated atomic-publish-lifecycle implementation in
  `data/publication.py::publish_canonical_atomically()`, used by dataset materialization; missed in
  iteration 1 because domain-based subagent assignment left this cross-cutting file without an explicit
  owner). Root cause of the miss: coverage-assignment gap at a domain boundary, not a hidden runtime
  branch or a regression from the fix pass.
- ARCH-003 was also found to be broader than first documented (7 of 9 experiment packages affected, one
  package with zero domain modules) — scope corrected in `08_FINDINGS.md`/`11_SECOND_AUDIT.md`.
- Per the bounded-loop rule, this single same-family finding did not trigger a third full audit cycle;
  it is recorded and disclosed below as a residual, deferred item.

## Scientific verdict
The current DATP-Core implementation **faithfully realizes the applicable Journal Extension Audit Matrix**
across every domain independently audited by both the first-pass discovery subagents and the second,
adversarial reviewer pass: fixed-detector/fixed-preprocessing reuse, score-artifact scientific identity,
benign-only calibration, checkpoint non-test selection, all four threshold-method families plus their
variants, the anchor reproduction gate (locked interval/width/multiplier/14 conditions, non-bypassable),
temporal ordering with no pseudo-chronology, 36 spot-checked metric/statistical formulas (including hand-
worked numeric verification of 8 core metrics), seed-level (not row/client) resampling for BCa/Wilcoxon,
typed unavailability propagation, and a publication layer that consumes but never recomputes science. No
leakage, contamination, artifact-collision, fabrication, or negative-result-suppression defect was found
by either pass. The only confirmed defects across the whole exercise were 4 architecture/file-organization
items (all in the same "duplicated or relocated persistence-lifecycle logic" / "file-splitting convention"
family), of which the lowest-risk instance was fixed and verified this session and the remaining 3 are
disclosed below as genuine, understood, deferred residual items rather than claimed as resolved.

## Residual limitations (genuine, disclosed — not previously-fixed issues relabeled)
- **ARCH-001**: `artifacts/repositories/` lacks dedicated `populations.py/preprocessing.py/checkpoints.py/scores.py`; that persistence logic is colocated with its owning domain package instead. Deferred: large blast-radius, no scientific consequence, risk of introducing forbidden thin wrappers if rushed.
- **ARCH-002**: `artifacts/serializers/` lacks `safetensors.py/skops.py`; used inline in 5 call sites across `detector/checkpoints/`, `detector/training/`, `detector/scoring/`, `data/preprocessing/`. Same deferral rationale.
- **ARCH-003**: 7 of 9 experiment packages consolidate `spec/analyze/report` into `run.py` (one, `applicability/`, has no domain modules at all — its sole experiment is implemented in `external/run.py`). No recomputation-of-science defect resulted. Recommend either a dedicated splitting refactor or updating the CLAUDE.md canonical-tree diagram to match the current, internally-coherent practice.
- **ARCH-004**: `data/publication.py::publish_canonical_atomically()` duplicates the generic atomic-publish lifecycle for dataset materialization (1 caller: `data/materialization.py`). Deferred: higher behavioral-risk than the fixed preprocessing instance (no explicit `overwrite` parameter, dataset-specific cache-cleanup side effects).
- One pre-existing (not introduced this session, confirmed unchanged before/after via `git stash`) `pyright` finding in a test fixture, `tests/unit/preprocessing/test_manifest_severity.py` (5 "redundant tuple-length" type errors), out of scope of the confirmed findings above.

## Verification gates
- Full applicable test suite (`tests/unit tests/integration tests/property tests/scientific`): **859 passed**.
- `ruff check .`: **clean**.
- `pyright` (scoped to changed package): **0 errors**; whole-repo `pyright` has the 5 pre-existing, unrelated test-fixture errors noted above.
- No accidental files were created outside `docs/roadmap_code_audit/` and `tmp/roadmap_code_audit/`.
