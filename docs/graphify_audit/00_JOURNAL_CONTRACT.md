# 00_JOURNAL_CONTRACT.md

## Scientific Implementation Contract for DATP-Core

> **STATUS: NOT STARTED**
> **PRIORITY: ABSOLUTE PREREQUISITE**

This document summarizes the scientific implementation contract that the code is expected to satisfy based on the authoritative DATP-Core journal roadmap.

---

## Journal Source

**Authoritative Document:** `docs/Journal_Extension_Master_Roadmap.md`
**Read Status:** Pending
**Summary Status:** Pending

---

## Scientific Responsibility Inventory

### 1. Core Scientific Identity

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| DATP-Core identity | TBD | TBD | Pending |
| Fixed-detector causal contract | TBD | TBD | Pending |

### 2. Experiment Categories

#### 2.1 Confirmatory Experiments

| Experiment | Roadmap Section | Evidence Role | Population | Method | Status |
|------------|----------------|---------------|------------|--------|--------|
| Primary confirmatory | TBD | Confirmatory | TBD | TBD | Pending |

#### 2.2 Supportive Experiments

| Experiment | Roadmap Section | Evidence Role | Purpose | Status |
|------------|----------------|---------------|---------|--------|
| Supportive analysis | TBD | Supportive | TBD | Pending |

#### 2.3 Exploratory Experiments

| Experiment | Roadmap Section | Evidence Role | Purpose | Status |
|------------|----------------|---------------|---------|--------|
| Exploratory | TBD | Exploratory | TBD | Pending |

#### 2.4 Stress Test Experiments

| Experiment | Roadmap Section | Evidence Role | Purpose | Status |
|------------|----------------|---------------|---------|--------|
| FedProx stress test | TBD | Stress-test | Training-side | Pending |
| Personalized-model stress test | TBD | Stress-test | Training-side | Pending |

#### 2.5 External Validation

| Experiment | Roadmap Section | Evidence Role | Purpose | Status |
|------------|----------------|---------------|---------|--------|
| Edge-IIoTset | TBD | External | Validation | Pending |

#### 2.6 Anchor Experiments

| Experiment | Roadmap Section | Evidence Role | Purpose | Status |
|------------|----------------|---------------|---------|--------|
| Anchor reproduction | TBD | Anchor | Reproduction | Pending |

### 3. Dataset/Regime Requirements

#### 3.1 Primary Datasets

| Dataset | Roadmap Section | Role | Characteristics | Status |
|---------|----------------|------|----------------|--------|
| N-BaIoT | TBD | Confirmatory population | Natural physical devices | Pending |
| CICIoT2023 | TBD | Limited | TBD | Pending |
| Edge-IIoTset | TBD | External validation | TBD | Pending |

#### 3.2 Synthetic/Controlled Regimes

| Regime | Roadmap Section | Role | Characteristics | Status |
|--------|----------------|------|----------------|--------|
| Controlled heterogeneity | TBD | Sensitivity | Artificial/Dirichlet populations | Pending |

### 4. Preprocessing Semantics

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Preprocessing identity | TBD | Per-regime definitions | Pending |
| Fitting scope | TBD | Journal-defined | Pending |
| Fitting partition | TBD | Journal-defined | Pending |
| Transformer identity | TBD | Journal-defined | Pending |
| State persistence | TBD | Journal-defined | Pending |
| Reuse semantics | TBD | Journal-defined | Pending |
| Non-finite handling | TBD | Journal-defined | Pending |
| Constant feature semantics | TBD | Journal-defined | Pending |
| Transform-only partitions | TBD | Journal-defined | Pending |

### 5. Training Semantics

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| FedAvg semantics | TBD | Core training | Pending |
| FedProx semantics | TBD | Stress test only | Pending |
| Personalized-model method | TBD | Stress test, no aggregation | Pending |
| Centralized reference | TBD | Independently trained | Pending |
| Checkpoint selection | TBD | Independent of threshold outcomes | Pending |

### 6. Scoring Semantics

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Score generation | TBD | Frozen score sets | Pending |
| Benign-only calibration | TBD | No attack-labelled information | Pending |

### 7. Calibration Requirements

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Benign score isolation | TBD | No attack data in calibration | Pending |
| Minimum support | TBD | n >= 100 for benign calibration | Pending |
| Eligibility criteria | TBD | Based on benign calibration only | Pending |

### 8. Threshold Semantics

#### 8.1 Threshold Policies

| Policy | Roadmap Section | Semantics | Status |
|--------|----------------|-----------|--------|
| Shared threshold | TBD | TBD | Pending |
| Local threshold | TBD | TBD | Pending |
| Family threshold | TBD | TBD | Pending |
| Cluster threshold | TBD | Benign score fingerprint | Pending |

#### 8.2 Cluster Fingerprint

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Mean | TBD | Required | Pending |
| Standard deviation | TBD | Required | Pending |
| Skewness | TBD | Required | Pending |
| P95 | TBD | Required | Pending |
| Clustering behavior | TBD | Locked | Pending |

### 9. Evaluation Semantics

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Primary metrics | TBD | TBD | Pending |
| Supporting metrics | TBD | TBD | Pending |
| Unit of analysis | TBD | Correct aggregation | Pending |
| Bootstrap/BCa semantics | TBD | Where locked | Pending |
| No pseudoreplication | TBD | Required | Pending |
| No test-informed selection | TBD | Required | Pending |

### 10. Statistical Analysis

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Paired-seed semantics | TBD | Required | Pending |
| Statistical analysis | TBD | TBD | Pending |
| Confirmatory decision rule | TBD | TBD | Pending |

### 11. Temporal Requirements

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Chronology | TBD | history → calibration → future evaluation | Pending |
| No future-to-history leakage | TBD | Required | Pending |

### 12. Reporting/Publication

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Report/publication paths | TBD | TBD | Pending |
| Reporting/claim boundaries | TBD | TBD | Pending |

### 13. Confirmatory Boundaries

| Aspect | Roadmap Section | Requirement | Status |
|--------|----------------|-------------|--------|
| Confirmatory vs supportive | TBD | No silent promotion | Pending |
| Confirmatory vs exploratory | TBD | No silent promotion | Pending |
| Failed primary results | TBD | Not rescued by secondary results | Pending |

---

## Critical Invariants

To be extracted from the journal roadmap.

## Explicit Prohibitions

To be extracted from the journal roadmap.

---

## Next Steps

1. Read the complete `docs/Journal_Extension_Master_Roadmap.md`
2. Extract all scientific requirements systematically
3. Populate this contract document
4. Use this contract as the authoritative reference for all audit decisions