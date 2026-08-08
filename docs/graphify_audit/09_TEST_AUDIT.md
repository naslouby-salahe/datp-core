# 09_TEST_AUDIT.md

## Test Audit

> **STATUS: NOT STARTED**
> **PRIORITY: MEDIUM**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md, 01_GRAPH_INVENTORY.md**

This document audits tests as verification material, not production authority.

---

## 1. Test-Only Production Dependencies

### 1.1 Production Code Only Called by Tests
| ID | Severity | Symbol | Location | Callers | Journal Requirement | Classification | Notes |

### 1.2 Stale Tests Preserving Removed APIs
| ID | Severity | Test | File | Line | API | Status | Classification | Notes |

### 1.3 Tests Preserving Shims
| ID | Severity | Test | File | Line | Shim | Purpose | Classification | Notes |

### 1.4 Tests Asserting Obsolete Architecture
| ID | Severity | Test | File | Line | Architecture | Current State | Classification | Notes |

### 1.5 Tests Requiring Backwards Compatibility
| ID | Severity | Test | File | Line | Compatibility | Purpose | Classification | Notes |

---

## 2. Test Quality Issues

### 2.1 Duplicate Tests
| ID | Severity | Test | File | Line | Duplicate Of | Classification | Notes |

### 2.2 Stale Fixtures
| ID | Severity | Fixture | File | Line | Purpose | Current Usage | Classification | Notes |

### 2.3 Unused Test Helpers
| ID | Severity | Helper | File | Line | Purpose | Last Used | Classification | Notes |

### 2.4 Tests Inspecting Implementation Detail
| ID | Severity | Test | File | Line | Detail | Expected Behavior | Classification | Notes |

---

## 3. Missing Test Coverage

### 3.1 Missing Tests for Journal Invariants
| ID | Severity | Invariant | Journal Section | Expected Test | Current State | Classification | Notes |

### 3.2 Missing Scientific Verification
| ID | Severity | Requirement | Journal Section | Expected Test | Current State | Classification | Notes |

---

## 4. Classification Summary

### 4.1 FIX_TEST_ONLY_ARTIFACT Issues
| ID | Test | Location | Production Dependency | Classification | Notes |

### 4.2 Test Cleanup Issues
| ID | Test | Location | Problem | Classification | Notes |

---

## Next Steps

1. Identify production code whose only caller is a test
2. Find stale tests preserving removed APIs
3. Find tests preserving shims
4. Find tests asserting obsolete architecture
5. Identify tests requiring backwards compatibility
6. Find duplicate tests
7. Find stale fixtures
8. Find unused test helpers
9. Identify tests inspecting implementation detail
10. Identify missing tests for journal invariants
11. Identify missing scientific verification
12. Classify all findings

**RULE: There is no requirement to preserve stale production interfaces merely because tests reference them.**
