# 02_ENTRYPOINTS_AND_WORKFLOWS.md

## Production Entry Points and Workflow Analysis

> **STATUS: NOT STARTED**
> **PRIORITY: HIGH**
> **DEPENDS ON: 00_JOURNAL_CONTRACT.md, 01_GRAPH_INVENTORY.md**

This document identifies all genuine production entry points and traces their end-to-end workflows.

---

## 1. CLI Entry Points

### 1.1 Expected CLI Structure (from requirements)

```
datp-core
├── validate [EXPERIMENT_ID]
├── plan [EXPERIMENT_ID]
├── preprocess [DATASET_ID] [--overwrite]
├── smoke [EXPERIMENT_ID] [--overwrite]
├── anchor
│   ├── reproduce [--overwrite]
│   ├── verify
│   └── status
├── run
│   ├── experiment <EXPERIMENT_ID> [--overwrite]
│   └── campaign [--overwrite]
├── report [EXPERIMENT_ID] [--overwrite]
└── status [EXPERIMENT_ID]
```

### 1.2 Actual CLI Implementation

| Command | Module | Function | Status | Notes |
|---------|--------|----------|--------|-------|
| TBD | TBD | TBD | Pending | TBD |

### 1.3 CLI Root Analysis

| CLI Root | Entry Point | Orchestrator | Status |
|----------|-------------|--------------|--------|
| TBD | TBD | TBD | Pending |

---

## 2. Orchestration Roots

### 2.1 Non-CLI Execution Paths

| Root | Module | Function | Purpose | Status |
|------|--------|----------|---------|--------|
| TBD | TBD | TBD | TBD | Pending |

### 2.2 Dagster Assets/Jobs (if applicable)

| Asset/Job | Module | Purpose | Status |
|-----------|--------|---------|--------|
| TBD | TBD | TBD | Pending |

### 2.3 Public Python APIs

| API | Module | Function | Purpose | Status |
|-----|--------|----------|---------|--------|
| TBD | TBD | TBD | TBD | Pending |

---

## 3. Workflow Tracing

### 3.1 Standard Experiment Workflow

**Expected Conceptual Flow:**
```
experiment identity
→ validation
→ planning
→ dataset resolution
→ raw-data validation
→ preprocessing
→ population/client construction
→ split creation
→ preprocessing fitting
→ transformation
→ federated/centralized training
→ checkpoint selection
→ scoring
→ benign calibration
→ threshold construction
→ evaluation
→ statistical analysis
→ reporting/publication artifacts
```

**Actual Implementation Flow:**
```
TBD
```

### 3.2 Per-Experiment Workflow Analysis

#### 3.2.1 Confirmatory Experiments

| Experiment | Entry Point | Workflow Path | Status | Divergence |
|------------|-------------|---------------|--------|------------|
| TBD | TBD | TBD | Pending | TBD |

#### 3.2.2 Supportive Experiments

| Experiment | Entry Point | Workflow Path | Status | Divergence |
|------------|-------------|---------------|--------|------------|
| TBD | TBD | TBD | Pending | TBD |

#### 3.2.3 Exploratory Experiments

| Experiment | Entry Point | Workflow Path | Status | Divergence |
|------------|-------------|---------------|--------|------------|
| TBD | TBD | TBD | Pending | TBD |

#### 3.2.4 Stress Test Experiments

| Experiment | Entry Point | Workflow Path | Status | Divergence |
|------------|-------------|---------------|--------|------------|
| FedProx stress test | TBD | TBD | Pending | TBD |
| Personalized-model stress test | TBD | TBD | Pending | TBD |

#### 3.2.5 Anchor Experiments

| Experiment | Entry Point | Workflow Path | Status | Divergence |
|------------|-------------|---------------|--------|------------|
| Anchor reproduction | TBD | TBD | Pending | TBD |

---

## 4. Stage-by-Stage Analysis

### 4.1 Validation Stage

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| experiment validation | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.2 Planning Stage

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| experiment planning | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.3 Dataset Resolution

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| dataset resolution | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.4 Raw Data Validation

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| raw-data validation | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.5 Preprocessing

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| preprocessing | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.6 Population/Client Construction

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| population/client construction | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.7 Split Creation

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| split creation | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.8 Preprocessing Fitting

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| preprocessing fitting | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.9 Transformation

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| transformation | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.10 Training

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| federated training | TBD | TBD | TBD | TBD | TBD | Pending |
| centralized training | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.11 Checkpoint Selection

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| checkpoint selection | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.12 Scoring

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| scoring | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.13 Benign Calibration

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| benign calibration | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.14 Threshold Construction

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| threshold construction | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.15 Evaluation

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| evaluation | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.16 Statistical Analysis

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| statistical analysis | TBD | TBD | TBD | TBD | TBD | Pending |

### 4.17 Reporting/Publication

| Stage | Invoked By | Implementation | Input | Output | Consumer | Status |
|-------|------------|----------------|-------|--------|----------|--------|
| reporting/publication | TBD | TBD | TBD | TBD | TBD | Pending |

---

## 5. Reachability Analysis

### 5.1 Production-Reachable Components

| Component | Entry Point | Call Chain | Status |
|-----------|-------------|------------|--------|
| TBD | TBD | TBD | Pending |

### 5.2 Unreachable Components

| Component | Location | Why Unreachable | Status |
|-----------|----------|------------------|--------|
| TBD | TBD | TBD | Pending |

---

## 6. Missing Wiring Analysis

### 6.1 Components with No Entry Point

| Component | Responsibility | Required By Journal | Status |
|-----------|----------------|--------------------|--------|
| TBD | TBD | TBD | Pending |

### 6.2 Disconnected Stages

| Stage | Expected Input | Expected Output | Current State | Status |
|-------|----------------|-----------------|---------------|--------|
| TBD | TBD | TBD | TBD | Pending |

---

## Next Steps

1. Identify all genuine production entry points
2. Trace each workflow end-to-end
3. Verify actual implementation against expected flow
4. Identify missing wiring and disconnected components
5. Document all findings systematically