# 10_JOURNAL_IMPLEMENTATION_MATRIX.md

## Journal Implementation Coverage Matrix

> **STATUS: NOT STARTED**
> **PRIORITY: CRITICAL**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md**

This is a mandatory deliverable that maps every journal requirement to its implementation state.

---

## Matrix Format

For every meaningful implementation responsibility identified from the journal:

```
Roadmap responsibility: [responsibility name]
Roadmap section: [section reference]
Evidence role: [confirmatory/supportive/exploratory/stress-test/external/anchor]

Expected implementation responsibility: [what should exist]
Actual owner: [module.class or module.function]
Actual file: [file path]
Actual symbol: [symbol name]

Production entrypoint: [CLI command or API]
Actual caller chain: [caller -> callee -> ...]
Actual downstream chain: [callee -> consumer -> ...]

Status: [LIVE_AND_CORRECT/DISCONNECTED/INCOMPLETE/MISSING/DUPLICATED/SCIENTIFICALLY_DRIFTED/INTENTIONALLY_UNAVAILABLE]
Notes: [additional context]
Required action: [what needs to be done]
```

---

## 1. Core Scientific Requirements

### 1.1 Fixed-Detector Causal Contract
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |
|----|----------------|----------------|---------------|-------|------|--------|-------------|-------------|-----------------|--------|-------|----------------|

### 1.2 Confirmatory Comparison
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 2. Experiment Categories

### 2.1 Confirmatory Experiments
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 2.2 Supportive Analyses
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 2.3 Exploratory Analyses
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 2.4 Stress Tests
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 2.5 External Validation
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 2.6 Anchor Reproduction
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 3. Dataset and Regime Requirements

### 3.1 N-BaIoT
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 3.2 CICIoT2023
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 3.3 Edge-IIoTset
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

### 3.4 Controlled Heterogeneity
| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 4. Preprocessing Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 5. Training Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 6. Checkpoint Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 7. Scoring Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 8. Calibration Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 9. Threshold Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 10. Evaluation Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 11. Statistical Analysis Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 12. Reporting/Publication Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 13. Anchor Requirements

| ID | Responsibility | Roadmap Section | Evidence Role | Owner | File | Symbol | Entry Point | Caller Chain | Downstream Chain | Status | Notes | Required Action |

---

## 14. Summary Statistics

### 14.1 Overall Coverage
- Total journal responsibilities: TBD
- LIVE_AND_CORRECT: TBD
- DISCONNECTED: TBD
- INCOMPLETE: TBD
- MISSING: TBD
- DUPLICATED: TBD
- SCIENTIFICALLY_DRIFTED: TBD
- INTENTIONALLY_UNAVAILABLE: TBD

### 14.2 By Evidence Role
| Evidence Role | Total | LIVE_AND_CORRECT | DISCONNECTED | INCOMPLETE | MISSING | DUPLICATED | SCIENTIFICALLY_DRIFTED | INTENTIONALLY_UNAVAILABLE |
|---------------|-------|-----------------|---------------|-------------|--------|------------|------------------------|------------------------|
| Confirmatory | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Supportive | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Exploratory | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Stress-test | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| External | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Anchor | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## Next Steps

1. For every journal responsibility, identify the expected implementation
2. Find the actual implementation (if any)
3. Trace the runtime path from entry points
4. Verify the implementation against journal requirements
5. Classify the status of each responsibility
6. Populate the matrix completely
7. Generate summary statistics
