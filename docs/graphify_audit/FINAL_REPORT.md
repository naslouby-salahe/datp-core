# DATP-Core Graphify-Assisted Structural, Runtime, Wiring, Dead-Code, Architecture, and Scientific Audit — Final Report

**Date:** 2026-08-07
**Scope:** Complete repository audit of `/home/naslouby/Projects/datp-core`
**Authority:** `docs/Journal_Extension_Master_Roadmap.md`

---

## Executive Verdict

**NOT READY — RUNTIME ISSUES**

The repository has strong scientific fidelity — all core algorithms, threshold policies, evaluation metrics, statistical procedures, and preprocessing protocols correctly implement the journal contract. However, critical runtime defects prevent clean execution:

1. Smoke runs poison production outputs for 4 of 7 registered experiments
2. Report generation re-executes training for Ditto/Temporal experiments
3. Campaign mode triple-executes Ditto/Temporal experiments
4. B0 centralized reference is implemented but completely unreachable
5. 15 of 24 declared experiments have no execution path

These are infrastructure/wiring defects, not scientific defects. The scientific logic, when it runs, is correct.

---

## Counts

### Confirmed Issues

| Category | Count |
|----------|-------|
| Runtime bugs (FIX_RUNTIME_BUG) | 8 |
| Required but disconnected (WIRE_REQUIRED) | 5 |
| Incomplete implementations (FIX_INCOMPLETE) | 6 |
| Confirmed dead code (DELETE_DEAD) | 8 |
| Duplications (MERGE_DUPLICATE) | 7 |
| Test-only production code | 6 |
| Simplifications | 5 |
| Primitive leaks | 0 |
| Scientific drift | 0 |

### Journal Implementation Coverage

| State | Count | Pct |
|-------|-------|-----|
| LIVE_AND_CORRECT | 52 | 85% |
| DISCONNECTED | 6 | 10% |
| INCOMPLETE | 1 | 2% |
| MISSING | 1 | 2% |
| PARTIAL | 1 | 2% |
| **Total** | **61** | 100% |

---

## Most Serious Issues

### CRITICAL — Execution Defects

1. **Smoke poisons production** (`campaign.py:228-272`): External, CICIoT, Ditto, and Temporal dispatch handlers ignore `output_root` and write to real `OUTPUTS_ROOT`. Smoke single-seed completion records poison future full-cohort runs with `COMPLETE_INVALID`.

2. **FedProx smoke runs full grid** (`campaign.py:246-254`): Deletes `seeds` parameter; smoke runs all 10 seeds × 4 coefficients instead of 1 canonical seed.

3. **Report re-executes training** (`campaign.py:542-563`): Ditto and Temporal report handlers call full training/scoring/evaluation instead of loading existing evidence. Violates documented "no training" report contract.

4. **Triple execution per campaign** (`campaign.py:341-361`): In-loop `generate_report` + final `generate_report(None)` causes Ditto/Temporal to execute 3× per campaign.

### HIGH — Missing Wiring

5. **B0 centralized reference unreachable**: 145-line complete implementation, zero callers. Journal requires B0 as privacy-incompatible centralized context.

6. **15 experiments declared but not executable**: All mandatory supportive, mechanism, threshold-variant experiments have no workflow modules.

7. **FEDERATED_POOLED_MIN_MAX undispatched**: Implemented in preprocessing dispatch but planning hardcodes FEDERATED_CLIENT_LOCAL_STANDARD.

### HIGH — Dead Code

8. **`runtime/logging.py`** (45 lines): Test-only, never wired into pipeline. Structlog used directly elsewhere.

9. **`analysis/mechanisms/__init__.py`**: `cluster_mechanism_bundle` and `heterogeneity_association_from_observations` — zero consumers.

10. **10 dead MetricId members**: Have enum definitions but no metric producers.

---

## Scientific Verification

### VERIFIED CORRECT — All Core Algorithms

- **Fixed-detector causal contract**: Same scores reused across B1-B4, enforced by checksum validation
- **Benign-only calibration**: Attack labels rejected at calibration construction
- **Calibration/evaluation isolation**: Split construction prevents leakage
- **Threshold policies B1-B4**: All correctly implement journal-specified construction
- **B4 fingerprint**: mean, std(ddof=0), skew(bias=True), p95; K=3 canonical
- **Eligibility n_k >= 100**: Enforced at calibration and threshold construction
- **CV(FPR) computation**: ddof=0, no epsilon stabilizer, zero mean → UNDEFINED
- **FedAvg**: Sample-count-weighted mean, 1 local epoch, full participation
- **FedProx**: Separate protocol, proximal term, non-test coefficient selection
- **Ditto**: Genuine Ditto semantics (global + persistent personalized, correct proximal objective)
- **Checkpoint selection**: FIXED_TERMINAL_MAXIMUM_ROUND=200, all 7 candidates saved
- **Preprocessing**: FEDERATED_CLIENT_LOCAL_STANDARD, StandardScaler, client-local, train-only
- **BCa bootstrap**: Paired seed deltas, 10k reps, jackknife acceleration
- **Confirmatory decision**: 95% BCa lower bound > 0
- **B-FedStatsBenign**: Full pooled variance = within + between
- **Dataset boundaries**: Correct capability enforcement for all regimes

### NOTED — Non-Scientific Concerns

- **Anchor tolerance 1e-12**: Over-strict (bit-exact rather than material consistency). No roadmap-specified tolerance.
- **Anchor reference provenance**: Conference literals in code only, no checksum/DOI citation.
- **Anchor gate currently BLOCKED**: No independent package exists; confirmatory chain cannot run.

---

## Architecture Assessment

**Quality: HIGH.** Clean layered architecture, no circular dependencies, strong typing, comprehensive enum coverage, consistent StrictModel/dataclass patterns. Primary issues are dead code and missing wiring, not structural problems.

### Simplification Opportunities

- Merge two dispatch tables into single registry (reduces ~15 LOC)
- Deduplicate `complete_digest` (4 copies), `serialize_json_model` (2 copies), `_required_metric` (2 copies), `_evaluation_path` (2 copies)
- Remove dead `runtime/logging.py` and `pipeline/workflows/centralized.py`
- Remove 10 dead MetricId members
- Consider splitting `personalization.py` (977 LOC), `export.py` (900 LOC), `temporal.py` (885 LOC)

---

## Primitive Leak Assessment

**CLEAN.** Zero `Any` types in production. Zero `dict[str, Any]` as domain contracts. Zero `# type: ignore` in production. Strong value object coverage (15+ wrappers). All closed categorical domains use enums.

---

## Test Assessment

**Quality: HIGH.** 174 test files, 765 tests. Strong scientific invariant coverage. Well-structured test hierarchy (unit/integration/e2e/scientific/property). No stale tests. Good CUDA-gating.

**Gaps:** No test for smoke isolation (the bug exists). No campaign orchestration integration test. No test for report-from-evidence contract.

---

## Workflow Findings

| Experiment | Execute Path | Report Path | Issues |
|-----------|-------------|-------------|--------|
| SHARED_VS_LOCAL_CONFIRMATION | `confirmatory.py` | `confirmatory.py` | OK |
| FAMILY_AND_GROUPED_GRANULARITY | `confirmatory.py` | `confirmatory.py` (shared) | No dedicated report |
| EDGE_BENIGN_EQUITY_VALIDATION | `external.py` | `external.py` | Smoke isolation broken |
| CICIOT_FILE_CLIENT_BOUNDARY | `external.py` | `external.py` | Smoke isolation broken |
| FEDPROX_ABSORPTION_STRESS_TEST | `personalization.py` | `personalization.py` | Smoke runs full grid |
| DITTO_ABSORPTION_STRESS_TEST | `personalization.py` | `personalization.py` | Report re-executes training |
| EDGE_ONE_SHOT_RECALIBRATION | `temporal.py` | `temporal.py` | Report re-executes training |
| 15 other experiments | NONE | NONE | No workflow modules |

---

## Recommended Execution Order

See `docs/graphify_audit/11_ACTION_PLAN.md` for detailed action plan.

Priority:
1. Fix smoke isolation (ACT-001)
2. Fix report re-execution (ACT-002)
3. Fix triple execution (ACT-003)
4. Delete confirmed dead code (ACT-010 through ACT-013, ACT-015)
5. Wire B0 centralized reference (ACT-004)
6. Add analysis markers (ACT-009)
7. Fix incomplete implementations (ACT-007, ACT-008)
8. Wire FEDERATED_POOLED_MIN_MAX (ACT-005)
9. Implement missing workflow modules (ACT-006)
10. Simplify architecture (ACT-014)
11. Document anchor provenance (ACT-016)

---

## Final Verdict

**NOT READY — RUNTIME ISSUES**

The scientific implementation is faithful to the journal contract. All core algorithms are correct. The codebase has excellent type discipline, clean architecture, and comprehensive testing.

However, the repository cannot be used for production research execution because:
- Smoke runs corrupt production outputs
- Report generation re-executes training
- Campaign mode executes experiments 2-3 times
- B0 centralized reference is unreachable
- 15/24 experiments cannot be executed

These are fixable infrastructure defects concentrated in `campaign.py`. The estimated fix effort is ~300 lines of changes across ~5 files for the critical defects, plus larger workflow module implementations for the 15 unregistered experiments.

**Repository is scientifically correct but not operationally ready.**
