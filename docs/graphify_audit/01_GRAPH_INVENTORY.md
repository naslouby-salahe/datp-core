# 01_GRAPH_INVENTORY.md

## Module Dependency Graph Inventory

> **STATUS: NOT STARTED**
> **PRIORITY: HIGH**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md**

This document captures the complete dependency graph, import graph, and runtime relationships discovered through Graphify analysis.

---

## Analysis Methodology

- **Tool:** Graphify (complete repository scan)
- **Scope:** All production code in `/src/datp_core/`
- **Verification:** All major findings verified against source code

---

## 1. Module Hierarchy

### 1.1 Package Structure

```
src/datp_core/
├── [TBD - to be populated from actual source]
```

### 1.2 Import Graph Summary

| Module | Imports | Imported By | Re-exports | Status |
|--------|---------|-------------|------------|--------|
| TBD | TBD | TBD | TBD | Pending |

### 1.3 Circular Dependencies

| Cycle | Modules Involved | Severity | Status |
|-------|------------------|----------|--------|
| TBD | TBD | TBD | Pending |

---

## 2. Class Relationships

### 2.1 Inheritance Hierarchy

```
TBD
```

### 2.2 Protocol Implementations

| Protocol | Implementations | Status |
|----------|-----------------|--------|
| TBD | TBD | Pending |

---

## 3. Factory and Registry Analysis

### 3.1 Factories

| Factory | Products | Callers | Status |
|---------|----------|---------|--------|
| TBD | TBD | TBD | Pending |

### 3.2 Registries

| Registry | Registered Items | Usage | Status |
|----------|------------------|-------|--------|
| TBD | TBD | TBD | Pending |

---

## 4. Dispatch Analysis

### 4.1 Dispatch Paths

| Dispatcher | Dispatch Key | Implementations | Selection Logic | Status |
|-----------|--------------|-----------------|-----------------|--------|
| TBD | TBD | TBD | TBD | Pending |

---

## 5. CLI and Orchestration Roots

### 5.1 CLI Entry Points

| Command | Module | Function | Status |
|---------|--------|----------|--------|
| TBD | TBD | TBD | Pending |

### 5.2 Orchestration Roots

| Root | Module | Purpose | Status |
|------|--------|---------|--------|
| TBD | TBD | TBD | Pending |

---

## 6. Domain-Specific Paths

### 6.1 Dataset Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.2 Population/Client Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.3 Preprocessing Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.4 Training Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.5 Checkpoint Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.6 Scoring Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.7 Threshold Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.8 Evaluation Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.9 Statistical Analysis Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.10 Reporting/Publication Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

### 6.11 Anchor Paths

| Path | Module | Responsibility | Status |
|------|--------|----------------|--------|
| TBD | TBD | TBD | Pending |

---

## 7. Re-export Analysis

### 7.1 Stale Re-exports

| Re-export | Source | Consumers | Status |
|-----------|--------|------------|--------|
| TBD | TBD | TBD | Pending |

### 7.2 Redirect Modules

| Redirect | Target | Purpose | Status |
|----------|--------|---------|--------|
| TBD | TBD | TBD | Pending |

---

## 8. File-Level Inventory

### 8.1 All Production Modules

```
TBD - Complete list of all .py files in src/datp_core/
```

### 8.2 Symbol-Level Inventory

| File | Classes | Functions | Constants | Status |
|------|---------|-----------|-----------|--------|
| TBD | TBD | TBD | TBD | Pending |

---

## 9. Unreachable Components

### 9.1 Never Imported

| Module/Symbol | Location | Evidence | Status |
|---------------|----------|----------|--------|
| TBD | TBD | TBD | Pending |

### 9.2 Never Instantiated/Called

| Symbol | Defined In | Callers | Status |
|--------|------------|---------|--------|
| TBD | TBD | TBD | Pending |

---

## 10. Verification Notes

All Graphify findings must be verified against actual source code before being classified as confirmed.

---

## Next Steps

1. Run Graphify over complete repository
2. Extract dependency graphs and relationships
3. Verify major findings against source code
4. Populate this inventory systematically