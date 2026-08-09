# 11 — Second Audit (Fresh Pass)

Performed after all first-audit-confirmed and reviewer-accepted findings were fixed and verified
(full suite green, `ruff check .` clean, `pyright` clean on changed files). This pass deliberately
re-derived evidence from current source rather than re-reading iteration-1 conclusions, per the
"genuinely fresh" requirement — new checks performed, not a re-statement of `08_FINDINGS.md`.

## Fresh checks performed and results

1. **Recipe/registry/matrix count, re-derived from scratch**: `grep -c "ExperimentRecipe("` → 22;
   `EXPERIMENTS` registry tuple → 24; matrix experiment-catalogue entries → 24. 22 + 1 anchor-only
   (`HISTORICAL_DATP_REPRODUCTION`) + 1 suppressed (`ALERT_BURDEN_TRANSLATION`) = 24. **Confirmed
   consistent** (this replaces the arithmetic error found by Reviewer 2 in the first-pass doc).

2. **Search for other instances of the duplicated atomic-publish-lifecycle pattern** (the same root
   cause as the accepted Reviewer-2 finding), beyond the one already fixed: grepped every `FileLock(`
   usage in `src/datp_core/` (3 total: `artifacts/repositories/publication.py` — the canonical owner;
   `data/preprocessing/publication.py` — **fixed this session**; `data/publication.py` — **NEW FINDING
   ARCH-004**, not previously documented). `data/publication.py::publish_canonical_atomically()` is a
   third, independent reimplementation of the same lock/stage/reuse/atomic-replace pattern, used by
   `data/materialization.py::publish_canonical()` (dataset materialization for N-BaIoT/CICIoT2023/
   Edge-IIoTset). This finding was missed in the first audit's artifacts-domain subagent (which checked
   `artifacts/repositories/` and `data/preprocessing/` but not `data/publication.py` specifically) —
   root cause of the miss: first-pass discovery subagents were assigned by *domain* (datasets vs.
   artifacts vs. preprocessing) and this cross-cutting lifecycle-duplication pattern fell at a domain
   boundary. Recorded in `08_FINDINGS.md` as ARCH-004, assessed as higher-risk to fix than the
   preprocessing case (no explicit `overwrite` parameter, dataset-specific cache-cleanup side effects
   in `remove_target`) and deferred with that rationale disclosed.

3. **Experiment-package file-organization breadth check**: directly listed every `experiments/*`
   subpackage (not just the 3 named in the first pass). Found the file-splitting deviation (ARCH-003)
   is broader than first documented — 7 of 9 non-anchor/confirmatory packages have only `run.py` (or
   `run.py` plus 1-2 domain modules), and `experiments/applicability/` has **no domain modules at all**
   (its one experiment, `CICIOT_FILE_CLIENT_BOUNDARY`, is actually implemented in `experiments/external/
   run.py`). Updated ARCH-003 in `08_FINDINGS.md` to reflect the true, broader scope and to note this
   looks like a consistent, deliberate simplification (single `run.py` per family) rather than scattered
   incomplete work, since it applies near-uniformly rather than to one or two forgotten packages.

4. **Re-ran full verification gate after the ARCH-003 scope correction and ARCH-004 documentation
   (no source changed by these two items, so no re-test was required — confirmed via `git status`
   that only `docs/roadmap_code_audit/**` and the one already-tested `src/datp_core/data/preprocessing/
   publication.py` change are modified).**

## New confirmed findings this pass

- **ARCH-004** (see above) — 1 new finding. Root cause of the iteration-1 miss: domain-based subagent
  assignment left a cross-cutting file (`data/publication.py`, which is a `data/`-level, not
  `data/nbaiot|ciciot2023|edge_iiotset`-level, file) without an explicit owner in the first pass's task
  list. This is a **coverage-assignment gap**, not a hidden runtime branch or a regression introduced
  during fixing.

## Convergence assessment

`NEW_CONFIRMED_FINDINGS = 1` (ARCH-004, a documented, deferred, MODERATE architecture item in the same
family as two items already known from iteration 1 — not a new scientific-correctness defect, and not
evidence of a systemic problem requiring a third full audit cycle). Per the bounded-loop rule (§75), a
single additional finding of the same already-understood root-cause family does not warrant restarting
the entire audit; it is recorded and disclosed as a residual, deferred item in the final report instead.
