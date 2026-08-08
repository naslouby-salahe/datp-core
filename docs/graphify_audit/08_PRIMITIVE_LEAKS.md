# 08_PRIMITIVE_LEAKS.md

## Primitive Leak Audit

> **STATUS: NOT STARTED**
> **PRIORITY: MEDIUM**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md, 01_GRAPH_INVENTORY.md**

This document identifies inappropriate domain/scientific leakage through primitive types.

---

## 1. Primitive Leak Categories

### 1.1 Experiment Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.2 Dataset Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.3 Client Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.4 Population Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.5 Seed Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.6 Round Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.7 Epoch Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.8 Count Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.9 Sample Size Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.10 Fraction Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.11 Quantile Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.12 Threshold Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.13 Policy Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.14 Metric Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.15 Split Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.16 Checkpoint Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.17 Artifact Identities
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.18 Hash/Checksum Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.19 Filesystem Locations
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

### 1.20 Status/State Values
| ID | Severity | Field | Location | Current Type | Expected Type | Journal Context | Classification | Notes |

---

## 2. Inconsistent Representations

### 2.1 Mixed Representations
| ID | Severity | Concept | Location 1 | Type 1 | Location 2 | Type 2 | Journal Context | Classification | Notes |

**Examples to check:**
- Seed / int
- DatasetId / str
- ExperimentId / str
- ThresholdPolicy / str
- Fraction / float
- Status / str
- Path / str vs Path

---

## 3. Existing Value Objects and Enums

### 3.1 Available Type Constructs
| Type Construct | Location | Purpose | Current Usage | Classification | Notes |

### 3.2 Underutilized Type Constructs
| Type Construct | Location | Purpose | Expected Usage | Actual Usage | Classification | Notes |

---

## 4. Classification Summary

### 4.1 FIX_PRIMITIVE_LEAK Issues
| ID | Field | Location | Current Type | Expected Type | Journal Requirement | Existing Type | Reuse Strategy | Classification | Notes |

---

## Next Steps

1. Search for primitive usage in domain contexts
2. Identify inconsistent mixed representations
3. Inventory existing value objects and enums
4. Determine which primitives can be replaced with existing types
5. Identify gaps where new types might be needed
6. Classify all primitive leak findings
7. Propose fixes that reuse existing constructs

**RULE: Do not create meaningless wrapper types merely to eliminate a primitive.**
**RULE: Reuse existing value objects and enums wherever reasonable.**
