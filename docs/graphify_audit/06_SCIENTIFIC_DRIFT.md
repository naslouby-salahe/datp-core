# 06_SCIENTIFIC_DRIFT.md

## Scientific Drift Audit

> **STATUS: NOT STARTED**
> **PRIORITY: CRITICAL (HIGHEST PRIORITY)**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md**

This document audits actual runtime behavior against the journal contract to identify scientific drift.

> **RULE: Scientific correctness outranks reducing LOC.**

---

## 1. Fixed-Detector Causal Contract

### 1.1 Threshold-Scope Comparisons

| ID | Severity | Component | Location | Problem | Journal Requirement | Current Behavior | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|---------|------------------------|-------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Verify that threshold-scope comparisons do NOT silently change:**
- [ ] detector
- [ ] model state
- [ ] checkpoint
- [ ] preprocessing state
- [ ] population
- [ ] client identities
- [ ] split
- [ ] calibration records
- [ ] test records
- [ ] test scores
- [ ] eligibility
- [ ] metric implementation

---

## 2. Benign-Only Calibration

### 2.1 Attack-Labelled Information Leakage

| ID | Severity | Component | Location | Leakage Type | Journal Requirement | Current Behavior | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|--------------|------------------------|-------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Verify NO attack-labelled information enters:**
- [ ] threshold fitting
- [ ] client eligibility
- [ ] checkpoint selection
- [ ] comparator tuning
- [ ] shrinkage selection
- [ ] conformal selection
- [ ] cluster selection
- [ ] external population construction

---

## 3. Calibration/Evaluation Isolation

### 3.1 Isolation Violations

| ID | Severity | Component | Location | Violation Type | Journal Requirement | Current Behavior | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|----------------|------------------------|-------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Verify:** `calibration ∩ evaluation = ∅`

- [ ] No direct leakage
- [ ] No indirect leakage

---

## 4. Preprocessing Verification

### 4.1 Preprocessing Identity

| ID | Severity | Preprocessing | Module | Dataset/Regime | Journal Requirement | Current Implementation | Scientific Consequence | Classification | Notes |
|----|----------|---------------|--------|---------------|------------------------|------------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Check for each regime:**
- [ ] fitting scope
- [ ] fitting partition
- [ ] transformer identity
- [ ] state persistence
- [ ] reuse semantics
- [ ] non-finite handling
- [ ] constant feature semantics
- [ ] transform-only partitions

---

## 5. Threshold Policies

### 5.1 Policy Semantics

| ID | Severity | Policy | Module | Location | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|--------|--------|----------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

**Verify exact semantics:**
- [ ] Shared threshold
- [ ] Local threshold
- [ ] Family threshold
- [ ] Cluster threshold

### 5.2 Cluster Threshold Fingerprint

| ID | Severity | Component | Location | Fingerprint Aspect | Journal Requirement | Current Implementation | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|-------------------|------------------------|------------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | mean | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | standard deviation | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | skewness | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | p95 | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | clustering behavior | TBD | TBD | TBD | TBD | TBD |

**Verify the locked clustering behavior is preserved.**

---

## 6. Eligibility Verification

### 6.1 Minimum Benign Calibration Support

| ID | Severity | Component | Location | Eligibility Rule | Journal Requirement | Current Implementation | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|----------------|------------------------|------------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | n >= 100 | TBD | TBD | TBD | TBD |

**Verify:**
- [ ] Eligibility does NOT depend on test outcomes
- [ ] Minimum benign calibration support is enforced

---

## 7. Training Semantics

### 7.1 FedAvg

| ID | Severity | Component | Location | Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Exact core training semantics | TBD | TBD | TBD | TBD |

### 7.2 FedProx

| ID | Severity | Component | Location | Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Training-side stress test only | TBD | TBD | TBD | TBD |

**Verify:** Must NOT accidentally enter the core threshold-scope causal ladder.

### 7.3 Personalized-Model Method

| ID | Severity | Component | Location | Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Actual method correspondence | TBD | TBD | TBD | TBD |

**Verify:**
- [ ] No misleading naming
- [ ] No fake Ditto semantics
- [ ] No aggregation of personalized models if the intended method forbids it

### 7.4 Centralized Reference

| ID | Severity | Component | Location | Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Genuinely independently trained | TBD | TBD | TBD | TBD |

**Verify:** A federated model with a pooled threshold is NOT a centralized reference.

---

## 8. Checkpoint Selection

### 8.1 Independence Verification

| ID | Severity | Component | Location | Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Independent of downstream threshold-policy outcomes | TBD | TBD | TBD | TBD |

---

## 9. Scoring Verification

### 9.1 Frozen Score Sets

| ID | Severity | Component | Location | Policy | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Reuse intended frozen score sets | TBD | TBD | TBD | TBD |

---

## 10. Confirmatory Boundary

### 10.1 Evidence Role Promotion

| ID | Severity | Component | Location | Promotion Type | Journal Requirement | Current Behavior | Scientific Consequence | Classification | Notes |
|----|----------|-----------|----------|----------------|------------------------|-------------------|------------------------|---------------|-------|
| TBD | TBD | TBD | TBD | TBD | Supportive/exploratory must NOT silently become confirmatory | TBD | TBD | TBD | TBD |

**Verify:** A favorable secondary result must NOT rescue a failed primary result.

---

## 11. Dataset Boundaries

### 11.1 N-BaIoT

| ID | Severity | Component | Location | Boundary | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|----------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | Natural physical devices must remain confirmatory population | TBD | TBD | TBD | TBD |

### 11.2 Controlled Heterogeneity

| ID | Severity | Component | Location | Boundary | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|----------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | Artificial/Dirichlet populations must remain controlled sensitivity experiments | TBD | TBD | TBD | TBD |

### 11.3 CICIoT2023

| ID | Severity | Component | Location | Boundary | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|----------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | Do NOT infer unavailable physical-device identity | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | Do NOT fabricate chronology | TBD | TBD | TBD | TBD |

### 11.4 Edge-IIoTset

| ID | Severity | Component | Location | Boundary | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|----------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | Respect declared external-validation limitations | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | Respect declared attack-evaluation limitations | TBD | TBD | TBD | TBD |

---

## 12. Temporal Verification

### 12.1 Chronology

| ID | Severity | Component | Location | Temporal Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|----------------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | history → calibration/recalibration → future evaluation | TBD | TBD | TBD | TBD |

**Verify:** No future-to-history leakage

---

## 13. Statistics Verification

### 13.1 Statistical Semantics

| ID | Severity | Component | Location | Statistical Aspect | Journal Requirement | Current Implementation | Divergence | Classification | Notes |
|----|----------|-----------|----------|--------------------|------------------------|------------------------|------------|---------------|-------|
| TBD | TBD | TBD | TBD | paired-seed semantics | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | correct unit of analysis | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | correct aggregation level | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | primary endpoint | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | supporting endpoints | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | bootstrap/BCa semantics | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | no pseudoreplication | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | no test-informed method selection | TBD | TBD | TBD | TBD | TBD |
| TBD | TBD | TBD | TBD | no accidental mixing of confirmatory and exploratory rows | TBD | TBD | TBD | TBD | TBD |

---

## 14. Classification Summary

### 14.1 FIX_SCIENTIFIC_DRIFT Issues

| ID | Component | Location | Roadmap Section | Drift Type | Current Behavior | Expected Behavior | Scientific Consequence | Confidence | Status |
|----|-----------|----------|----------------|------------|-------------------|-------------------|------------------------|------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

---

## Next Steps

1. **PRIORITY ONE**: Verify fixed-detector causal contract
2. Verify benign-only calibration (no attack data leakage)
3. Verify calibration/evaluation isolation
4. Check preprocessing identity per regime
5. Verify threshold policy semantics
6. Verify eligibility criteria (n >= 100, no test dependence)
7. Verify training semantics (FedAvg, FedProx, Personalized, Centralized)
8. Verify checkpoint selection independence
9. Verify scoring policies
10. Verify confirmatory boundaries
11. Check dataset boundaries (N-BaIoT, CICIoT2023, Edge-IIoTset, Controlled)
12. Verify temporal requirements
13. Verify statistical semantics
14. Classify all violations as FIX_SCIENTIFIC_DRIFT

**REMEMBER: Scientific defects always outrank architectural style issues.**