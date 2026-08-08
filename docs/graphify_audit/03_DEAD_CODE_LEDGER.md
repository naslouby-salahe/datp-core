# 03_DEAD_CODE_LEDGER.md

## Dead Code Ledger

> **STATUS: NOT STARTED**
> **PRIORITY: HIGH**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md, 01_GRAPH_INVENTORY.md, 02_ENTRYPOINTS_AND_WORKFLOWS.md**

This document catalogs all production code that may be dead, with justification for each classification.

---

## Classification Rules

**NEVER classify code as dead based solely on Graphify reachability.**

Each candidate must be evaluated against:
1. **Graph/runtime evidence**: Why no meaningful production path requires it
2. **Scientific evidence**: Why the journal does not require the responsibility, OR why the responsibility is already correctly represented elsewhere

**Allowed classifications:**
- `DELETE_DEAD`: Genuinely dead code that is not scientifically required
- `WIRE_REQUIRED`: Scientifically required but not wired
- `FIX_INCOMPLETE`: Scientifically required but unfinished
- `MERGE_DUPLICATE`: Responsibility exists correctly elsewhere

---

## 1. Dead Code Candidates

### 1.1 Never Imported Modules

| ID | Severity | Module | Location | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|--------|----------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.2 Never Imported Symbols

| ID | Severity | Symbol | File | Line | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|--------|------|------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.3 Never Instantiated Classes

| ID | Severity | Class | File | Line | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|-------|------|------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.4 Never Called Functions

| ID | Severity | Function | File | Line | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|----------|------|------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.5 Referenced Only by Tests

| ID | Severity | Symbol | File | Line | Referenced By | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|--------|------|------|----------------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.6 Referenced Only by Dead Code

| ID | Severity | Symbol | File | Line | Referenced By | Graphify Evidence | Source Evidence | Production Reachable | Test-Only Reachable | Scientifically Required | Problem | Classification | Notes |
|----|----------|--------|------|------|----------------|-------------------|------------------|---------------------|---------------------|------------------------|---------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 2. Superseded/Obsolete Components

### 2.1 Old APIs

| ID | Severity | Symbol | File | Line | Superseded By | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|--------|------|------|----------------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.2 Shim/Wrappers

| ID | Severity | Symbol | File | Line | Wraps | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|--------|------|------|-------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.3 Redirects

| ID | Severity | Symbol | File | Line | Redirects To | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|--------|------|------|-------------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.4 Stale Re-exports

| ID | Severity | Symbol | File | Line | Re-exports | Consumers | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|--------|------|------|------------|------------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 3. Unused Constructs

### 3.1 Unused Protocols

| ID | Severity | Protocol | File | Line | Implementations | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------|------|------|-----------------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.2 Unused Implementations

| ID | Severity | Implementation | File | Line | Protocol | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------------|------|------|----------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.3 Unused Dataclasses

| ID | Severity | Dataclass | File | Line | Fields | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|-----------|------|------|--------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.4 Unused Enums

| ID | Severity | Enum | File | Line | Members | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|------|------|------|---------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.5 Unused Enum Members

| ID | Severity | Enum | Member | File | Line | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|------|--------|------|------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.6 Unused Exceptions

| ID | Severity | Exception | File | Line | Raised By | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|-----------|------|------|----------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.7 Unused Helpers

| ID | Severity | Function | File | Line | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------|------|------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.8 Unused Constants

| ID | Severity | Constant | File | Line | Value | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------|------|------|-------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.9 Unused Registry Entries

| ID | Severity | Registry | Entry | File | Line | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------|-------|------|------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.10 Obsolete CLI Paths

| ID | Severity | CLI Path | Module | Function | Graphify Evidence | Source Evidence | Classification | Notes |
|----|----------|----------|--------|----------|-------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 4. Classification Summary

### 4.1 DELETE_DEAD Candidates

| ID | Symbol | Location | Why Unreachable | Why Scientifically Unnecessary | Superseded By | Production Behavior Change | Confidence | Status |
|----|--------|----------|-------------------|--------------------------------|---------------|-----------------------------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 4.2 WIRE_REQUIRED Candidates

| ID | Symbol | Location | Roadmap Responsibility | Required Entry Point | Expected Caller | Expected Callee | Downstream Consumer | Confidence | Status |
|----|--------|----------|------------------------|----------------------|----------------|------------------|---------------------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 4.3 FIX_INCOMPLETE Candidates

| ID | Symbol | Location | Roadmap Responsibility | Missing Implementation | Current State | Required Fix | Confidence | Status |
|----|--------|----------|------------------------|------------------------|---------------|---------------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 4.4 MERGE_DUPLICATE Candidates

| ID | Symbol | Location | Duplicate Of | Roadmap Responsibility | Which to Keep | Which to Remove | Confidence | Status |
|----|--------|----------|--------------|------------------------|---------------|----------------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 5. Evidence Requirements

For every issue, the following must be answered:

### For DELETE_DEAD:
- [ ] Why is it unreachable?
- [ ] Why is it scientifically unnecessary?
- [ ] What implementation supersedes it, if any?
- [ ] What production behavior changes if it is removed?

### For WIRE_REQUIRED:
- [ ] Which exact roadmap responsibility requires it?
- [ ] Where should it enter the runtime graph?
- [ ] Which component should own the invocation?
- [ ] Which downstream component requires its output?

### For FIX_INCOMPLETE:
- [ ] Which exact roadmap responsibility is incomplete?
- [ ] What is missing from the implementation?
- [ ] What is the required final state?

### For MERGE_DUPLICATE:
- [ ] What is the duplicated responsibility?
- [ ] Where are both implementations?
- [ ] Which one should be kept and why?

---

## Next Steps

1. Run Graphify to identify unreachable components
2. For each candidate, verify against source code
3. Check against journal requirements
4. Classify according to the rules above
5. Document all evidence and reasoning