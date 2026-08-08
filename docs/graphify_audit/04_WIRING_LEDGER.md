# 04_WIRING_LEDGER.md

## Wiring Ledger

> **STATUS: NOT STARTED**
> **PRIORITY: HIGH**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md, 01_GRAPH_INVENTORY.md, 02_ENTRYPOINTS_AND_WORKFLOWS.md**

This document identifies code that exists and appears scientifically required but is disconnected from the runtime graph.

---

## Wiring Classification Rules

For each candidate, ask:
```
Does the journal require this responsibility?
```

- **NO**: Classify as `DELETE_DEAD`
- **YES AND implementation is correct**: Classify as `WIRE_REQUIRED`
- **YES AND implementation is also defective**: Classify as `FIX_INCOMPLETE`

---

## 1. Missing Wiring Categories

### 1.1 Experiment Definitions Without Execution Path

| ID | Severity | Experiment | Defined In | Required By Journal | Current Callers | Expected Call Chain | Classification | Notes |
|----|----------|------------|------------|--------------------|----------------|-------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.2 Enum Members Without Dispatch Path

| ID | Severity | Enum | Member | File | Line | Journal Requirement | Current Dispatch | Expected Dispatch | Classification | Notes |
|----|----------|------|--------|------|------|--------------------|------------------|------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.3 Protocol Implementations Never Selected

| ID | Severity | Protocol | Implementation | File | Line | Journal Requirement | Selection Mechanism | Why Not Selected | Classification | Notes |
|----|----------|----------|----------------|------|------|--------------------|---------------------|-----------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.4 Factories Missing Implementations

| ID | Severity | Factory | Missing Implementation | File | Line | Journal Requirement | Available Implementations | Classification | Notes |
|----|----------|---------|------------------------|------|------|--------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 1.5 Registries Missing Implementations

| ID | Severity | Registry | Missing Implementation | File | Line | Journal Requirement | Registered Items | Classification | Notes |
|----|----------|----------|------------------------|------|------|--------------------|-----------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 2. Domain-Specific Missing Wiring

### 2.1 Dataset Handlers Without Reachability

| ID | Severity | Dataset Handler | Module | Journal Requirement | Expected Entry Point | Current State | Classification | Notes |
|----|----------|-----------------|--------|--------------------|----------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.2 Population Builders Never Used

| ID | Severity | Population Builder | Module | Journal Requirement | Expected Callers | Current State | Classification | Notes |
|----|----------|-------------------|--------|--------------------|-----------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.3 Split Strategies Never Selected

| ID | Severity | Split Strategy | Module | Journal Requirement | Expected Selection | Current State | Classification | Notes |
|----|----------|----------------|--------|--------------------|--------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.4 Preprocessing Implementations Bypassed

| ID | Severity | Preprocessing | Module | Journal Requirement | Expected Usage | Current State | Bypassed By | Classification | Notes |
|----|----------|----------------|--------|--------------------|---------------|---------------|--------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.5 Training Implementations Never Invoked

| ID | Severity | Training Implementation | Module | Journal Requirement | Expected Callers | Current State | Classification | Notes |
|----|----------|------------------------|--------|--------------------|-----------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.6 Checkpoint Selectors Ignored

| ID | Severity | Checkpoint Selector | Module | Journal Requirement | Expected Usage | Current State | Classification | Notes |
|----|----------|--------------------|--------|--------------------|---------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.7 Scoring Implementations Disconnected

| ID | Severity | Scoring Implementation | Module | Journal Requirement | Expected Callers | Current State | Classification | Notes |
|----|----------|------------------------|--------|--------------------|-----------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.8 Threshold Implementations Never Dispatch

| ID | Severity | Threshold Implementation | Module | Journal Requirement | Expected Dispatch | Current State | Classification | Notes |
|----|----------|--------------------------|--------|--------------------|-------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.9 Evaluation Implementations Never Used

| ID | Severity | Evaluation Implementation | Module | Journal Requirement | Expected Usage | Current State | Classification | Notes |
|----|----------|--------------------------|--------|--------------------|---------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.10 Analysis Implementations Without Artifact Inputs

| ID | Severity | Analysis Implementation | Module | Journal Requirement | Expected Inputs | Current Inputs | Classification | Notes |
|----|----------|------------------------|--------|--------------------|----------------|----------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.11 Report/Publication Code Never Reached

| ID | Severity | Report Implementation | Module | Journal Requirement | Expected Entry Point | Current State | Classification | Notes |
|----|----------|-----------------------|--------|--------------------|----------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 2.12 Anchor Logic Disconnected

| ID | Severity | Anchor Implementation | Module | Journal Requirement | Expected Entry Point | Current State | Classification | Notes |
|----|----------|------------------------|--------|--------------------|----------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 3. Workflow Integration Issues

### 3.1 Artifacts Produced but Never Consumed

| ID | Severity | Artifact | Producer | Expected Consumers | Current Consumers | Classification | Notes |
|----|----------|----------|----------|----------------------|-------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.2 Return Values Ignored

| ID | Severity | Function | File | Line | Return Type | Callers | Why Ignored | Classification | Notes |
|----|----------|----------|------|------|------------|---------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.3 Constructed Objects Discarded

| ID | Severity | Object | Constructor | File | Line | Callers | Why Discarded | Classification | Notes |
|----|----------|--------|-------------|------|------|---------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.4 Results Overwritten

| ID | Severity | Variable/Result | File | Line | Overwritten By | Why Problematic | Classification | Notes |
|----|----------|-----------------|------|------|----------------|-----------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 3.5 Missing Calls Between Stages

| ID | Severity | Missing Call | Expected Caller | Expected Callee | Journal Requirement | Current State | Classification | Notes |
|----|----------|--------------|----------------|----------------|--------------------|---------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 4. Orchestration Issues

### 4.1 Campaign Plans Failing to Invoke Declared Experiments

| ID | Severity | Campaign Plan | Missing Experiment | File | Line | Expected Experiments | Actual Experiments | Classification | Notes |
|----|----------|---------------|---------------------|------|------|----------------------|-------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 4.2 CLI Paths That Stop Too Early

| ID | Severity | CLI Path | Module | Function | Expected Behavior | Actual Behavior | Classification | Notes |
|----|----------|----------|--------|----------|-------------------|----------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 4.3 Alternate Paths Bypassing Authoritative Logic

| ID | Severity | Bypass Path | Module | Function | Bypasses | Journal Requirement | Classification | Notes |
|----|----------|-------------|--------|----------|----------|--------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## 5. Evidence Requirements

For every WIRE_REQUIRED issue, answer:

```
Which exact roadmap responsibility requires it?
Where should it enter the runtime graph?
Which component should own the invocation?
Which downstream component requires its output?
```

If these cannot be established: **do not classify as requiring wiring.**

---

## 6. Summary

### 6.1 Confirmed Missing Wiring

| ID | Component | Responsibility | Entry Point | Call Chain | Status |
|----|-----------|----------------|-------------|-----------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD |

### 6.2 Suspected Missing Wiring

| ID | Component | Responsibility | Entry Point | Call Chain | Confidence | Status |
|----|-----------|----------------|-------------|-----------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## Next Steps

1. Systematically check each journal-required responsibility for runtime reachability
2. Identify components that exist but are not connected
3. For each disconnected component, verify journal requirement
4. Classify according to wiring rules
5. Document all evidence and reasoning