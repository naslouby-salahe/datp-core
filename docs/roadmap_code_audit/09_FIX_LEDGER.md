# 09 — Fix Ledger

## First-audit findings and disposition

| Finding | Severity | Fix applied this session? | Rationale |
|---|---|---|---|
| ARCH-001 (`artifacts/repositories/` missing populations/preprocessing/checkpoints/scores modules) | MODERATE | No — deferred | High blast-radius (dozens of call sites across `detector/checkpoints/`, `detector/scoring/`, `data/preprocessing/`, `data/populations/`); no scientific-correctness consequence found; risks introducing the forbidden thin-wrapper anti-pattern if done superficially. Documented in `08_FINDINGS.md` with explicit recommendation for a dedicated follow-up refactor or CLAUDE.md diagram update. |
| ARCH-002 (`artifacts/serializers/` missing safetensors.py/skops.py) | LOW-MODERATE | No — deferred | Same rationale as ARCH-001; each call site is domain-specific, not literal duplicated logic. |
| ARCH-003 (missing spec.py/analyze.py/report.py in anchor/confirmatory/temporal) | LOW | No — deferred | No recomputation-of-science defect found (verified in `07_PUBLICATION_REVERSE_TRACE.md`); pure file-organization convention gap. |
| COLLISION-001 (raw subagent claim) | — | N/A — rejected as false positive | Independently re-verified: `ExperimentCoordinate.stable_key` structurally prevents this. No code change needed. |
| CLI DEFECT-003 (raw subagent claim: missing registry/recipe test) | — | N/A — rejected as false positive | Test already exists (`tests/unit/app/test_programme.py`). No code change needed. |

## Post-review fixes (after 4 parallel independent reviewers)

| Finding | Files changed | Verification |
|---|---|---|
| Recipe-wiring count doc error (23 vs actual 22) | `docs/roadmap_code_audit/01_REPOSITORY_AND_CLI_INVENTORY.md`, `00_AUDIT_CONTROL.md` | direct `grep -c "ExperimentRecipe("` recount |
| `data/preprocessing/publication.py::publish_processed()` duplicated the generic atomic-publish lifecycle instead of delegating to `artifacts/repositories/publication.py::publish_artifact()` | `src/datp_core/data/preprocessing/publication.py` (sole caller `artifact_validation.py` needed no change — public API preserved) | `tests/integration/preprocessing/*` + `tests/unit/preprocessing/*` (36/36 pass unchanged); full suite `tests/unit tests/integration tests/property tests/scientific` (859 passed); `ruff check .` clean; `pyright` scoped to `data/preprocessing/` clean (0 errors) |

See `10_REVIEWER_FINDINGS.md` for full reviewer detail and disposition.


Ten independent read-only discovery subagents, each running the Matrix §76 adversarial checks relevant to
their domain (detector contamination, preprocessing contamination, score-identity failure, dataset/split/
calibration/attack leakage, eligibility/checkpoint drift, cross-severity/FedProx/Ditto/centralized
contamination, cluster contamination, temporal leakage, pseudo-chronology, metric drift, statistical
pseudoreplication, unavailability corruption, negative-result suppression, publication recomputation,
artifact collisions, stale-artifact reuse, partial completion), found zero confirmed scientific defects.
This is consistent with the repository's own memory record of prior, independently-verified audit-and-fix
cycles (`docs/graphify_audit/`, now superseded, and a same-day roadmap-ambiguity resolution pass) having
already closed out the scientific-correctness findings that existed before this session.

No production code was modified during this fixing phase. Proceeding directly to `INDEPENDENT_REVIEW` with
the two documented, deferred ARCH findings carried forward as open items for reviewers to challenge.
