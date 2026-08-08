# 11_ACTION_PLAN.md

## Action Plan

> **STATUS: NOT STARTED**
> **PRIORITY: CRITICAL**
> **DEPENDS ON: All previous audit documents**

This document describes the exact recommended remediation order.

---

## Priority Order

1. **SCIENTIFIC DRIFT** (FIX_SCIENTIFIC_DRIFT) - Highest priority
2. **MISSING/BROKEN WIRING** (WIRE_REQUIRED, FIX_INCOMPLETE) - Critical
3. **INCOMPLETE SCIENTIFIC IMPLEMENTATIONS** (FIX_INCOMPLETE) - Critical
4. **RUNTIME BUGS** (FIX_RUNTIME_BUG) - High
5. **CONFIRMED DEAD-CODE DELETION** (DELETE_DEAD) - Medium
6. **DUPLICATED RESPONSIBILITY CONSOLIDATION** (MERGE_DUPLICATE) - Medium
7. **PRIMITIVE LEAK CORRECTION** (FIX_PRIMITIVE_LEAK) - Medium
8. **ARCHITECTURAL SIMPLIFICATION** (SIMPLIFY) - Low
9. **TEST CLEANUP** (FIX_TEST_ONLY_ARTIFACT) - Low

---

## Action Items

### Priority 1: Scientific Drift Fixes

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |
|-----------|--------------------|-------|---------------|--------------|-----|-----------------------|----------------|-----------------|----------------|---------------------|--------|

### Priority 2: Missing/Broken Wiring

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 3: Incomplete Scientific Implementations

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 4: Runtime Bugs

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 5: Dead Code Deletion

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 6: Duplicate Consolidation

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 7: Primitive Leak Correction

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 8: Architectural Simplification

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

### Priority 9: Test Cleanup

| Action ID | Related Issue IDs | Title | Files/Symbols | Exact Change | Why | Scientific Constraints | Expected Impact | Affected Callers | Affected Tests | Validation Required | Status |

---

## Execution Phases

### Phase 1: Critical Scientific Fixes
- [ ] Fix all FIX_SCIENTIFIC_DRIFT issues
- [ ] Validate scientific correctness

### Phase 2: Wiring and Completion
- [ ] Wire all WIRE_REQUIRED components
- [ ] Complete all FIX_INCOMPLETE implementations

### Phase 3: Runtime Stability
- [ ] Fix all FIX_RUNTIME_BUG issues
- [ ] Validate runtime behavior

### Phase 4: Cleanup and Simplification
- [ ] Delete all DELETE_DEAD code
- [ ] Merge all MERGE_DUPLICATE components
- [ ] Fix all FIX_PRIMITIVE_LEAK issues
- [ ] Apply SIMPLIFY changes
- [ ] Clean up tests (FIX_TEST_ONLY_ARTIFACT)

---

## Dependencies and Ordering

### Hard Dependencies
- Scientific drift fixes must be completed before any cleanup
- Wiring fixes must be completed before dead code deletion
- Runtime bug fixes should be validated before architectural changes

### Validation Strategy
- Each action must be validated individually
- Scientific validation must occur before architectural changes
- Runtime validation must occur before cleanup

---

## Metrics

### Expected Code Changes
- Lines of code removed: TBD
- Lines of code added: TBD
- Net code reduction: TBD
- Files deleted: TBD
- Files modified: TBD

### Expected Complexity Changes
- Number of concepts reduced: TBD
- Number of abstractions reduced: TBD
- Number of dependencies reduced: TBD

---

## Next Steps

1. Aggregate all findings from previous audit documents
2. Organize by priority and dependency
3. Create specific action items for each finding
4. Validate dependencies and ordering
5. Populate this action plan completely
6. Execute according to priority order
