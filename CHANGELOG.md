# CHANGELOG — DATP Journal Extension (`datp-core`)

> Agent-progress tracker for the scratch build. Read the dashboard first, then the
> phase/ticket tables, then the latest update. Plan of record:
> [MASTER_TICKET_LOG.md](MASTER_TICKET_LOG.md).
>
> **This is not a scientific result file.** It tracks implementation progress,
> tests, blockers, and decisions only. It must never contain experimental result
> claims, CI values, or metric outcomes. Status values: `Not Started` ·
> `In Progress` · `Blocked` · `Done` · `Skipped` · `Split` · `Merged` · `Reopened`.

---

## 1. Current Status Dashboard

```text
Current phase:        Phase 2 — Anchor Reproduction Pipeline (implementation-ready)
Current ticket:       None — Phase 2 quality gate is Green; real mini/full execution remains operator-gated
Overall progress:     49 / 99 tickets Done (49%)
Completed tickets:    49
In-progress tickets:  0
Blocked tickets:      0
Last completed ticket: P2-T20
Next ticket:          Operator-authorized two-seed real N-BaIoT mini run
Last tests run:       pytest -q — 188 passed, 1 valid environment-dependent skip (ruff / pyright clean)
Current blocker:      None
Last update:          2026-07-09 — typed-state/configuration-boundary remediation verified;
                       full execution remains unattempted.
```

---

## 2. Phase Progress Table

| Phase | Total Tickets | Done | In Progress | Blocked | Status | Exit Gate |
|---|---|---|---|---|---|---|
| 0 — Protocol/scope/architecture freeze | 11 | 11 | 0 | 0 | Done | P0-T11 go/no-go signed (Go) |
| 1 — Scratch foundation | 18 | 18 | 0 | 0 | Done | P1-T18 quality gate green |
| 2 — Anchor reproduction pipeline | 20 | 20 | 0 | 0 | Done | Fixture smoke, CUDA readiness, and real inventory verified |
| 3 — Core threshold policies & metrics | 11 | 0 | 0 | 0 | Not Started | P3-T11 B0–B4 + metrics validated |
| 4 — Threshold variants & comparators | 9 | 0 | 0 | 0 | Not Started | P4-T09 variants reuse scores |
| 5 — Mechanism analyses | 8 | 0 | 0 | 0 | Not Started | P5-T08 mechanisms from fixtures |
| 6 — External dataset & stress tests | 12 | 0 | 0 | 0 | Not Started | P6-T12 D/C frozen, stress separated |
| 7 — Temporal, final audit & freeze | 10 | 0 | 0 | 0 | Not Started | P7-T10 readiness report signed |
| **Total** | **99** | **49** | **0** | **0** | **In Progress** | — |

Phase 1 total was revised from 10 to 18 tickets (+8), then the user-authorized
Phase 2 breakdown revised it from 11 to 20 tickets (+9); the plan-of-record
total is 99. See §12.

---

## 3. Ticket Progress Table

| Ticket | Phase | Status | Last Update | Tests Run | Files Changed | Notes |
|---|---|---|---|---|---|---|
| P0-T01 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_scope_boundaries.py` (2 passed) | `docs/protocol/identity_lock.md`, `docs/protocol/scope_boundaries.md`, `tests/unit/test_scope_boundaries.py` | Scientific scope & identity freeze |
| P0-T02 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_claim_hierarchy.py` (3 passed) | `docs/protocol/claim_hierarchy.md`, `tests/unit/test_claim_hierarchy.py` | Claim hierarchy & confirmatory isolation |
| P0-T03 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_regimes_doc.py` (3 passed) | `docs/protocol/regimes.md`, `tests/unit/test_regimes_doc.py` | Regime definitions freeze |
| P0-T04 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_policies_doc.py` (4 passed) | `docs/protocol/policies.md`, `tests/unit/test_policies_doc.py` | Threshold-policy & comparator nomenclature |
| P0-T05 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_artifact_contracts_doc.py` (3 passed) | `docs/protocol/artifact_contracts.md`, `data/README.md`, `checkpoints/README.md`, `outputs/README.md`, `results/README.md`, `tests/unit/test_artifact_contracts_doc.py` | Dataset & artifact/directory contracts |
| P0-T06 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_naming_conventions.py` (3 passed) | `docs/protocol/naming_conventions.md`, `tests/unit/test_naming_conventions.py` | Config/suite/experiment-ID naming |
| P0-T07 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_seed_plan_doc.py` (3 passed) | `docs/protocol/seed_plan.md`, `tests/unit/test_seed_plan_doc.py` | Seed plan freeze |
| P0-T08 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_testing_contract.py` (2 passed) | `docs/protocol/testing_contract.md`, `tests/unit/test_testing_contract.py` | Testing contract & test-pyramid |
| P0-T09 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_reuse_policy_doc.py` (3 passed) | `docs/protocol/reuse_policy.md`, `tests/unit/test_reuse_policy_doc.py` | Reuse/caching + raw-data placement |
| P0-T10 | 0 | Done | 2026-07-09 | `pytest tests/unit/test_behavioral_reference.py` (2 passed) | `docs/protocol/behavioral_reference.md`, `tests/unit/test_behavioral_reference.py` | Old DATP behavioral-reference extraction |
| P0-T11 | 0 | Done | 2026-07-09 | `pytest tests/unit -q` (full suite) | `docs/protocol/structure_decision.md`, `docs/protocol/go_no_go.md`, `CHANGELOG.md`, `tests/unit/test_changelog_format.py` | Structure decision + changelog + go/no-go |
| P1-T01 | 1 | Done | 2026-07-09 | `pytest -q` (32 passed, baseline) | `pyproject.toml`, `uv.lock`, `Makefile`, `.env.example`, `.gitignore`, `src/datp_core/__init__.py` | Skeleton, pyproject, tooling, Makefile |
| P1-T02 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_paths.py -q` (10 passed) | `src/datp_core/utils/paths.py`, `tests/unit/test_paths.py` | Canonical path resolver |
| P1-T03 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_domain_enums.py -q` (17 passed) | `src/datp_core/domain/{regimes,clients,partitions,policies,datasets,seeds,metrics}.py`, `tests/unit/test_domain_enums.py` | Domain enums & typed identifiers |
| P1-T04 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_config_loader.py tests/unit/test_config_validation.py -q` (31 passed) | `src/datp_core/config/{loader,schemas,validation}.py`, `tests/unit/test_config_{loader,validation}.py` | Typed config loader & schema validation |
| P1-T05 | 1 | Done | 2026-07-09 | `pytest tests/integration/test_config_skeletons.py -q` (8 passed) | `configs/{datasets,training,thresholding,analysis,suites}/*.yaml` (22 files) | Config skeletons, all `status: contract_only` |
| P1-T06 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_dataset_contracts.py -q` (7 passed) | `src/datp_core/data/manifests.py`, `tests/unit/test_dataset_contracts.py` | Dataset registry & contract types |
| P1-T07 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_manifests.py -q` (14 passed) | `src/datp_core/experiments/{provenance,artifacts}.py`, `tests/unit/test_manifests.py` | Artifact manifest schema + JSON round-trip |
| P1-T08 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_artifact_guards.py tests/integration/test_no_overwrite_policy.py -q` (10 passed) | `src/datp_core/experiments/overwrite_guard.py`, `tests/unit/test_artifact_guards.py`, `tests/integration/test_no_overwrite_policy.py` | No-overwrite & lineage guard |
| P1-T09 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_determinism.py -q` (8 passed) | `src/datp_core/utils/{determinism,random}.py`, `tests/unit/test_determinism.py` | Determinism & seed-locking utilities |
| P1-T10 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_hardware.py -q` (8 passed) | `src/datp_core/utils/hardware.py`, `tests/unit/test_hardware.py` | Hardware/device selection utility |
| P1-T11 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_logging.py -q` (5 passed) | `src/datp_core/utils/logging.py`, `tests/unit/test_logging.py` | Logging convention (no duplicate handlers) |
| P1-T12 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_cli.py -q` (7 passed) | `src/datp_core/cli.py`, `src/datp_core/utils/layout.py`, `tests/unit/test_cli.py` | CLI skeleton (`doctor`/`validate-config`/`show-paths`/`list-suites`/`validate-layout`); no train command |
| P1-T13 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_fixtures.py -q` (5 passed) | `tests/fixtures/{tiny_clients,tiny_scores,tiny_dataset_contract,tiny_config,tiny_manifest,b_fedstats_benign_scores,absorption_bands}.py`, `tests/unit/test_fixtures.py` | Reusable tiny deterministic fixtures |
| P1-T14 | 1 | Done | 2026-07-09 | `pytest tests/unit/test_layout.py tests/integration/test_layout_contract.py -q` (8 passed) | `src/datp_core/utils/layout.py`, `tests/unit/test_layout.py`, `tests/integration/test_layout_contract.py` | Output/results/checkpoints contract checks |
| P1-T15 | 1 | Done | 2026-07-09 | `pytest tests/unit -q` (158 passed) | — (sweep/audit ticket; no new modules) | Phase 1 unit-test sweep confirmed complete |
| P1-T16 | 1 | Done | 2026-07-09 | `pytest tests/integration -q` (19 passed) | `tests/integration/{test_layout_contract,test_manifest_lineage,test_cli_doctor}.py` | Phase 1 integration tests |
| P1-T17 | 1 | Done | 2026-07-09 | `make show-paths list-suites lint typecheck unit integration validate-config validate-layout doctor` (all green) | `README.md`, `Makefile` | READMEs / Makefile / `.env.example` reviewed and updated |
| P1-T18 | 1 | Done | 2026-07-09 | `pytest -q` (177 passed); `ruff check .`; `pyright` (0 errors) | `CHANGELOG.md`, `MASTER_TICKET_LOG.md` | Phase 1 quality gate + changelog/master-log update |
| P2-T01 | 2 | Done | 2026-07-09 | `pytest -q`; entry commands | `CHANGELOG.md`, `MASTER_TICKET_LOG.md` | Entry gate verified; user-authorized 20-ticket split recorded |
| P2-T02 | 2 | Done | 2026-07-09 | `test_nbaiot_discovery.py` | `data/nbaiot.py` | Raw discovery, inventory, missing-data reporting |
| P2-T03 | 2 | Done | 2026-07-09 | `test_nbaiot_discovery.py` | `data/nbaiot.py` | Typed CSV loader preserves device/source identity |
| P2-T04 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `partitioning/physical_device.py` | Deterministic physical-device client mapping |
| P2-T05 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `data/splits.py`, `data/preprocessing.py` | Benign train/cal/test splits and scaling |
| P2-T06 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `data/splits.py` | Split manifest and leakage validation |
| P2-T07 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `models/autoencoder.py` | Fixed deterministic autoencoder |
| P2-T08 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `federation/fedavg.py` | Full-participation benign-only FedAvg |
| P2-T09 | 2 | Done | 2026-07-09 | `test_anchor_fixture_pipeline.py` | `models/checkpoints.py`, `models/frozen.py` | Final-round selection and frozen loading |
| P2-T10 | 2 | Done | 2026-07-09 | `test_anchor_fixture_pipeline.py` | `models/scoring.py` | Calibration/test reconstruction scores |
| P2-T11 | 2 | Done | 2026-07-09 | `test_anchor_fixture_pipeline.py` | `models/scoring.py` | Score lineage and reuse guard |
| P2-T12 | 2 | Done | 2026-07-09 | `test_anchor_fixture_pipeline.py` | `thresholding/{quantiles,shared,local}.py` | B1/B2 p95 thresholds from stored scores |
| P2-T13 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `evaluation/{predictions,classification,disparity}.py` | Anchor predictions and control metrics |
| P2-T14 | 2 | Done | 2026-07-09 | `test_anchor_fixture_pipeline.py` | `evaluation/aggregation.py` | Per-seed paired delta preserves B1−B2 sign |
| P2-T15 | 2 | Done | 2026-07-09 | `test_anchor_pipeline.py` | `experiments/plan.py` | Locked 10-seed B1/B2 plan |
| P2-T16 | 2 | Done | 2026-07-09 | `test_anchor_cli.py` | `cli.py`, `experiments/anchor.py` | Fixture smoke, safe mini/full gates, threshold-only command |
| P2-T17 | 2 | Done | 2026-07-09 | `tests/unit/test_{nbaiot_discovery,anchor_pipeline}.py` | unit tests | Phase 2 unit coverage |
| P2-T18 | 2 | Done | 2026-07-09 | `tests/integration/test_anchor_{fixture_pipeline,cli}.py` | integration tests | Shared checkpoint, lineage, CLI, no-retrain path |
| P2-T19 | 2 | Done | 2026-07-09 | `datp-core run-smoke anchor-fixture` | `outputs/anchor-fixture/` (ignored runtime artifact) | Fixture end-to-end smoke passes |
| P2-T20 | 2 | Done | 2026-07-09 | `pytest -q`; `ruff`; `pyright`; config/layout/readiness gates | runtime/config/docs | Real N-BaIoT, CUDA readiness, typed-state remediation, and static analysis verified |
| P3-T01 | 3 | Not Started | — | — | — | Federated quantile backbone |
| P3-T02 | 3 | Not Started | — | — | — | Threshold-policy interface & validation |
| P3-T03 | 3 | Not Started | — | — | — | B0 centralized reference |
| P3-T04 | 3 | Not Started | — | — | — | B1 shared threshold |
| P3-T05 | 3 | Not Started | — | — | — | B2 per-client threshold |
| P3-T06 | 3 | Not Started | — | — | — | B3 family-mean threshold |
| P3-T07 | 3 | Not Started | — | — | — | B4 cluster threshold (fingerprint+kmeans) |
| P3-T08 | 3 | Not Started | — | — | — | Prediction generation & operating points |
| P3-T09 | 3 | Not Started | — | — | — | Classification metrics (AUROC control) |
| P3-T10 | 3 | Not Started | — | — | — | Disparity metrics & aggregation |
| P3-T11 | 3 | Not Started | — | — | — | Threshold-policy equivalence tests |
| P4-T01 | 4 | Not Started | — | — | — | q-sensitivity sweep |
| P4-T02 | 4 | Not Started | — | — | — | Local-global shrinkage (τ-shrink) |
| P4-T03 | 4 | Not Started | — | — | — | Calibration-size fallback & ablation |
| P4-T04 | 4 | Not Started | — | — | — | Split/federated conformal B2-conf |
| P4-T05 | 4 | Not Started | — | — | — | B-FedStatsBenign statistics contract |
| P4-T06 | 4 | Not Started | — | — | — | B-FedStatsBenign matched-exceedance |
| P4-T07 | 4 | Not Started | — | — | — | B-LaridiFaithful disclosure guard |
| P4-T08 | 4 | Not Started | — | — | — | Threshold-only reuse (no-retrain) guard |
| P4-T09 | 4 | Not Started | — | — | — | Variant output contracts, tables & figures |
| P5-T01 | 5 | Not Started | — | — | — | Benign/attack CDF overlays & Ennio |
| P5-T02 | 5 | Not Started | — | — | — | Threshold-shift vs ΔFPR/ΔTPR surface |
| P5-T03 | 5 | Not Started | — | — | — | Cluster granularity, stability, ARI, ablation |
| P5-T04 | 5 | Not Started | — | — | — | JS-divergence vs benefit regression |
| P5-T05 | 5 | Not Started | — | — | — | P10 Macro-F1 & FPR-concentration |
| P5-T06 | 5 | Not Started | — | — | — | Alert-burden (gated on real/cited rate) |
| P5-T07 | 5 | Not Started | — | — | — | Mechanism figure/table export |
| P5-T08 | 5 | Not Started | — | — | — | Mechanism tests from fixtures |
| P6-T01 | 6 | Not Started | — | — | — | Edge-IIoTset loader & schema |
| P6-T02 | 6 | Not Started | — | — | — | Edge-IIoTset client-mapping feasibility |
| P6-T03 | 6 | Not Started | — | — | — | Edge-IIoTset preprocessing & cache (**heavy**) |
| P6-T04 | 6 | Not Started | — | — | — | Regime D splits & coverage gate |
| P6-T05 | 6 | Not Started | — | — | — | Regime D FedAvg train & score (**heavy**) |
| P6-T06 | 6 | Not Started | — | — | — | Regime D threshold ladder & comparator |
| P6-T07 | 6 | Not Started | — | — | — | CICIoT2023 file-level loader & B-a boundary |
| P6-T08 | 6 | Not Started | — | — | — | CICIoT2023 B-b rejection guard |
| P6-T09 | 6 | Not Started | — | — | — | Regime C Dirichlet builder & sweep (**heavy**) |
| P6-T10 | 6 | Not Started | — | — | — | FedProx impl & stress eval (**heavy**) |
| P6-T11 | 6 | Not Started | — | — | — | Model-personalization & absorption (**heavy**) |
| P6-T12 | 6 | Not Started | — | — | — | Stress-test reporting |
| P7-T01 | 7 | Not Started | — | — | — | Chronological split & temporal contract |
| P7-T02 | 7 | Not Started | — | — | — | Frozen vs one-shot recal & 3 outcomes (**heavy**) |
| P7-T03 | 7 | Not Started | — | — | — | BCa CI audit, Wilcoxon, Cliff's δ |
| P7-T04 | 7 | Not Started | — | — | — | Claim-gate logic |
| P7-T05 | 7 | Not Started | — | — | — | Claim-to-evidence map |
| P7-T06 | 7 | Not Started | — | — | — | Result curation (outputs→results) |
| P7-T07 | 7 | Not Started | — | — | — | Table/figure reproducibility checks |
| P7-T08 | 7 | Not Started | — | — | — | Full-suite dry run |
| P7-T09 | 7 | Not Started | — | — | — | Final audit: leakage/overwrite/provenance |
| P7-T10 | 7 | Not Started | — | — | — | Final implementation readiness report |

---

## 4. Latest Update Block

> Use the template in §14 for every future update. The most recent update goes
> at the top of §5 (Completed Work Log).

---

## 5. Completed Work Log

Newest first.

```text
## 2026-07-09 — P2 stabilization remediation — Wrapper removal

Status:            Done
Summary:           Removed forwarding-only APIs, including the random utility
                    module, frozen-model forwarding class, convenience
                    manifest serializers/writers, seed/metric facades, and
                    raw-path helper. Direct callers now own the required
                    standard-library or concrete-domain call.
Files changed:      Domain, data, artifact, model, CLI, determinism, and
                    focused test modules; `utils/random.py` deleted.
Tests added:        None; existing behavioral tests were updated to direct APIs.
Tests run:          Focused wrapper-affected tests (47 passed, 1
                    environment-dependent skip); ruff; pyright. Full suite
                    pending final cleanup audit.
Result:             No wrapper classes, forwarding functions, redirect modules,
                    or compatibility APIs remain in the implemented scope.
Artifacts created:  None.
Decisions made:     None.
Blockers:           None.
Risks:              None.
Next ticket:        Operator-authorized two-seed real N-BaIoT mini run.
```

```text
## 2026-07-09 — P2 stabilization remediation — Artifact-boundary hardening

Status:            Done
Summary:           Centralized Phase 2 JSON artifact writes in the manifest
                    writer; replaced the anonymous split-manifest dictionary
                    with typed manifest records; and added validation for
                    checkpoint, score, threshold, prediction, metric, and
                    paired-summary state.
Files changed:      Phase 2 artifact, data, model, thresholding, evaluation,
                    CLI, and focused fixture/integration test modules.
Tests added:        Malformed score/checkpoint metadata rejection and invalid
                    metric-value coverage.
Tests run:          Focused artifact/anchor/CLI tests (24 passed); ruff;
                    pyright. Full suite pending final stabilization audit.
Result:             Metadata is now written through one owned boundary and
                    malformed provenance is rejected before downstream use.
                    No real training, mini run, full run, or Phase 3 work ran.
Artifacts created:  None.
Decisions made:     None.
Blockers:           None.
Risks:              Generic JSON and NumPy adapters retain dynamic I/O values
                    at their serialization boundaries only.
Next ticket:        Operator-authorized two-seed real N-BaIoT mini run.
```

```text
## 2026-07-09 — P2-T20 remediation — Typed configuration and protocol state

Status:            Done
Summary:           Replaced internal mutable dictionary registries, dispatch,
                    grouping, parameter-transfer, eligibility, and seed-role
                    state with typed tuples and dataclasses. YAML/JSON/NPZ and
                    PyTorch mappings are now limited to their I/O adapters.
                    Anchor runtime grouping now owns config-derived dataset,
                    regime, seed plan, FedAvg, splits, fixture distribution,
                    client count, artifact layout, and CUDA device values.
Files changed:      config loader/schemas/validation, data contracts/loading,
                    domain registries, model/federation/scoring, CLI, utilities,
                    artifact readers, and focused tests; confirmatory YAML
                    now explicitly defines the artifact layout and all fixture
                    and FedAvg runtime values are in YAML.
Tests added:        Existing focused tests updated to use typed lookup APIs.
Tests run:          pytest -q (188 passed, 1 environment-dependent skip); ruff;
                    pyright; config validation; layout validation; readiness gate.
Result:             No hidden anchor-runtime defaults or duplicated runtime
                    policy values remain. No mini/full training was run.
Artifacts created:  None.
Decisions made:     D-011.
Blockers:           None.
Risks:              External serialization and PyTorch APIs necessarily accept
                    mappings; those mappings are isolated at adapter boundaries.
Next ticket:        Operator-authorized two-seed real N-BaIoT mini run.
```

```text
## 2026-07-09 — P2-T20 — Configuration, CUDA, raw-layout, and Sonar remediation

Status:            Done
Summary:           Replaced the lowercase raw-directory assumption with the
                    actual configured `N-BaIoT` directory; made runtime split,
                    q, fixture, optimizer, and CUDA settings typed config
                    fields; replaced the CPU-only NumPy AE path with CUDA
                    PyTorch; and configured/scanned SonarQube Community Build.
Files changed:      pyproject.toml, uv.lock, sonar-project.properties,
                    configs/{datasets,training,thresholding}, source/runtime
                    modules, tests, README.md, CHANGELOG.md.
Tests added:        Updated hardware/config/anchor coverage for configured CUDA.
Tests run:          pytest -q (188 passed, 1 environment-dependent skip); ruff;
                    pyright; CUDA fixture smoke; SonarQube scan (0 open issues).
Result:             Real raw inventory reports 9 device candidates, 9 benign
                    files, and 80 attack files. No real training, mini run,
                    full run, result claim, or Phase 3 work was performed.
Artifacts created:  Runtime-only CUDA fixture checkpoint and score artifacts.
Decisions made:     D-009.
Blockers:           None.
Risks:              Real full-data loading remains operator-gated.
Next ticket:        Operator-authorized two-seed real N-BaIoT mini run.
```

```text
## 2026-07-09 — P2-T01..P2-T19 — Phase 2 anchor implementation

Status:            Done
Summary:           Implemented the fixture-validated Regime A N-BaIoT anchor
                    pipeline: raw discovery/loading, natural device clients,
                    benign-only splits and scaling, fixed AE/FedAvg, frozen
                    checkpoints, stored reconstruction scores, B1/B2, metrics,
                    paired planning, and safe commands. No Phase 3 component,
                    raw-data mutation, result curation, or full run occurred.
Files changed:      `src/datp_core/{data,partitioning,models,federation,thresholding,evaluation,experiments}/`,
                    `src/datp_core/cli.py`, `configs/training/*.yaml`, focused
                    unit/integration tests, `README.md`.
Tests added:        N-BaIoT discovery, anchor unit, fixture pipeline, and CLI
                    integration tests.
Tests run:          `pytest -q` (189 passed); `ruff check .`; `pyright`; fixture
                    smoke; plan; readiness, config, layout, and doctor commands.
Result:             Fixture anchor and threshold-only rerun pass with frozen
                    checkpoint/score lineage. This is implementation-readiness
                    evidence only, not a scientific result.
Artifacts created:  `outputs/anchor-fixture/` runtime-only fixture artifact.
Decisions made:     D-008 superseded by D-009 (CUDA PyTorch backend and typed real-data root).
Blockers:           None; the two-seed real mini run remains operator-gated.
Risks:              Full raw loading/training has not been authorized or run.
Next ticket:        Operator-authorized two-seed real N-BaIoT mini run.
```

```text
## 2026-07-09 — P1-T18 — Phase 1 quality gate & CHANGELOG/master-log update

Status:            Done
Summary:           Ran the full Phase 1 quality gate (lint, typecheck, unit,
                    integration, CLI doctor, config validation, layout
                    validation, manifest round-trip, no-overwrite, git-status
                    and stale-label audit) and reconciled CHANGELOG.md and
                    MASTER_TICKET_LOG.md with the 18-ticket Phase 1 actually
                    executed this session.
Files changed:      CHANGELOG.md, MASTER_TICKET_LOG.md
Tests added:        None (gate ticket; runs the existing suite)
Tests run:          `pytest -q` (177 passed); `ruff check .` (clean); `pyright` (0 errors, 0 warnings)
Result:             All Phase 1 quality-gate checks green; no temp files, no
                    ops/audit side folders, no stale B5/B3-LGS/local_head/Ditto
                    labels found outside documentation prose explaining the ban.
Artifacts created:  None
Decisions made:     D-007 (see §8)
Blockers:           None
Risks:              See §11 — original P1-T08 (preprocessing cache) and part of
                    original P1-T09 (CLI run-dispatcher/readiness gate) were not
                    built this session; deferred to Phase 2 (§12).
Next ticket:        P2-T01 — N-BaIoT loader & schema (not started; requires
                    explicit authorization to begin Phase 2)
```

```text
## 2026-07-09 — P1-T17 — README / data-checkpoint-output-result READMEs / developer commands

Status:            Done
Summary:           Rewrote the root README.md with Phase 1 scope, setup, raw
                    data placement, outputs/results/checkpoints summary, and a
                    verified developer command reference; added `show-paths`
                    and `list-suites` Makefile targets. Reviewed
                    data/checkpoints/outputs/results READMEs (written in
                    Phase 0) and .env.example; no changes needed, still accurate.
Files changed:      README.md, Makefile
Tests added:        None (docs ticket)
Tests run:          `make show-paths list-suites lint typecheck unit integration validate-config validate-layout doctor` — all exit 0
Result:             Every documented command verified to actually work against the real repo.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T18 — Phase 1 quality gate & changelog update
```

```text
## 2026-07-09 — P1-T16 — Phase 1 integration tests

Status:            Done
Summary:           Added the remaining integration tests: end-to-end layout
                    contract against the real repo, a full manifest lineage
                    chain (dataset->preprocessing->split->checkpoint->score->
                    threshold->metric) with reuse-mismatch rejection, and a
                    real-subprocess CLI doctor test exercising the installed
                    entrypoint. test_config_skeletons.py and
                    test_no_overwrite_policy.py were already added under
                    P1-T05/P1-T08.
Files changed:      tests/integration/test_layout_contract.py,
                    tests/integration/test_manifest_lineage.py,
                    tests/integration/test_cli_doctor.py
Tests added:        test_real_repo_resolves_and_satisfies_the_layout_contract,
                    test_lineage_chain_links_every_stage_by_manifest_id,
                    test_lineage_reuse_rejects_a_different_seed_anywhere_in_the_chain,
                    test_doctor_subprocess_exits_cleanly_without_raw_datasets, +4 more
Tests run:          `pytest tests/integration -q` — 19 passed
Result:             Full integration suite green; no raw datasets required by any test.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T17 — READMEs & developer commands
```

```text
## 2026-07-09 — P1-T15 — Phase 1 unit-test sweep

Status:            Done
Summary:           Audit-only ticket: confirmed every Phase 1 foundation
                    module named in the ticket brief has a corresponding
                    tests/unit/test_*.py file, and ran the full unit suite,
                    lint, and typecheck together.
Files changed:      None (no new modules; verification only)
Tests added:        None (existing tests from P1-T02..P1-T14)
Tests run:          `pytest tests/unit -q` — 158 passed; `ruff check .` clean; `pyright` 0 errors
Result:             All expected unit test files present and green.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T16 — Phase 1 integration tests
```

```text
## 2026-07-09 — P1-T14 — Output/results/checkpoints contract checks

Status:            Done
Summary:           Implemented a repository-layout validator: required
                    top-level directories exist; data/raw stays a symlink
                    (never committed raw content); checkpoints/ and outputs/
                    contents are actually git-ignored (verified via
                    `git check-ignore`, not just pattern inspection);
                    results/ stays tracked (curated, never git-ignored). Added
                    two artifact-placement guards: a checkpoint manifest path
                    must never live under outputs/, and every curated result
                    file must have a companion manifest.
Files changed:      src/datp_core/utils/layout.py, tests/unit/test_layout.py
Tests added:        test_layout_check_passes_on_expected_skeleton,
                    test_missing_required_directory_fails,
                    test_outputs_results_confusion_fails,
                    test_checkpoint_path_under_outputs_fails_if_disallowed,
                    test_result_file_without_manifest_fails, +1 more
Tests run:          `pytest tests/unit/test_layout.py -q` — 6 passed
Result:             Real-repo layout check passes; synthetic misconfigured
                    repos (missing dir, results/outputs gitignore confusion)
                    are correctly rejected.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T15 — Phase 1 unit-test sweep
```

```text
## 2026-07-09 — P1-T13 — Reusable test fixtures

Status:            Done
Summary:           Added tiny, deterministic, dataset-free fixtures under
                    tests/fixtures/: clients, benign scores, a synthetic
                    dataset contract, in-memory config dicts, a score
                    manifest, a B-FedStatsBenign-shaped calibration-score
                    placeholder, and an absorption-bands placeholder. Added
                    `pythonpath = ["."]` to pytest config so
                    `tests.fixtures.*` imports resolve without package
                    `__init__.py` files.
Files changed:      tests/fixtures/{tiny_clients,tiny_scores,tiny_dataset_contract,
                    tiny_config,tiny_manifest,b_fedstats_benign_scores,
                    absorption_bands}.py, tests/unit/test_fixtures.py, pyproject.toml
Tests added:        test_fixtures_load_without_error, test_fixtures_are_deterministic,
                    test_fixtures_do_not_require_raw_dataset, test_fixtures_are_small,
                    test_fixtures_contain_no_scientific_result_claims
Tests run:          `pytest tests/unit/test_fixtures.py -q` — 5 passed
Result:             Fixtures load, are deterministic, and contain no result claims.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T14 — Output/results/checkpoints contract checks
```

```text
## 2026-07-09 — P1-T12 — CLI skeleton & command discovery

Status:            Done
Summary:           Implemented `datp-core` (argparse-based, stdlib only) with
                    five safe, read-only commands: doctor, validate-config,
                    show-paths, list-suites, validate-layout. `doctor` reports
                    missing raw datasets clearly without creating anything and
                    exits 0 when only data is missing (non-zero only on a real
                    layout failure). No train/run command exists — Phase 1
                    never dispatches heavy work.
Files changed:      src/datp_core/cli.py, src/datp_core/utils/layout.py,
                    tests/unit/test_cli.py
Tests added:        test_cli_help_works, test_doctor_works_without_raw_datasets_and_reports_missing_data,
                    test_validate_config_works_on_skeleton_configs, test_show_paths_prints_canonical_roots,
                    test_list_suites_lists_suite_configs, test_training_command_is_absent_during_phase1
Tests run:          `pytest tests/unit/test_cli.py -q` — 7 passed
Result:             `uv run datp-core --help/doctor/validate-config/show-paths/list-suites/validate-layout` all verified manually.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              utils/layout.py (originally scoped to P1-T14) was built
                    here because validate-layout depends on it; P1-T14 adds
                    its own dedicated tests on top of this implementation.
Next ticket:        P1-T13 — Reusable test fixtures
```

```text
## 2026-07-09 — P1-T11 — Logging & command-output conventions

Status:            Done
Summary:           Implemented get_logger(): exactly one managed StreamHandler
                    per logger name (repeat calls never duplicate handlers), a
                    consistent format including an optional run_id (updatable
                    in place on repeat calls), and a log level sourced from an
                    explicit argument or the DATP_LOG_LEVEL env var (default INFO).
Files changed:      src/datp_core/utils/logging.py, tests/unit/test_logging.py
Tests added:        test_logger_can_be_created, test_duplicate_handlers_are_not_added,
                    test_run_id_appears_in_formatted_output, test_log_level_comes_from_explicit_argument,
                    test_log_level_defaults_to_info
Tests run:          `pytest tests/unit/test_logging.py -q` — 5 passed
Result:             No duplicate handlers across repeated get_logger() calls; run_id renders correctly.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T12 — CLI skeleton & command discovery
```

```text
## 2026-07-09 — P1-T10 — Hardware/device selection utility

Status:            Done
Summary:           Implemented select_device(): CPU fallback by default,
                    CUDA only when torch is installed AND reports available;
                    strict mode raises HardwareError instead of silently
                    downgrading; select_device_from_env() reads the
                    documented DATP_DEVICE variable. DeviceDescriptor
                    serializes to a plain dict for manifest use.
Files changed:      src/datp_core/utils/hardware.py, tests/unit/test_hardware.py
Tests added:        test_cpu_selected_by_default, test_cuda_request_fails_clearly_when_unavailable,
                    test_auto_mode_returns_a_valid_device_descriptor, test_strict_mode_rejects_unavailable_accelerator,
                    test_device_descriptor_serializes_to_manifest_compatible_form, +2 more
Tests run:          `pytest tests/unit/test_hardware.py -q` — 8 passed
Result:             No GPU/torch present in this environment; every CUDA-path
                    assertion in the tests exercises the real absence, not a mock.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T11 — Logging & command-output conventions
```

```text
## 2026-07-09 — P1-T09 — Determinism & seed-locking utilities

Status:            Done
Summary:           Implemented Python/NumPy RNG seeding primitives
                    (utils/random.py) and apply_seed() (utils/determinism.py):
                    seeds Python+NumPy always, seeds PyTorch only if installed,
                    and strict mode raises DeterminismError instead of
                    claiming a guarantee it cannot verify (PyTorch is not a
                    Phase 1 dependency, so strict=True currently always fails
                    honestly rather than lying). seed_for_role() derives
                    train/analysis/stress-test sub-seeds so paired roles never
                    collide. seed_plan_to_dict/from_dict make domain.seeds.SeedPlan
                    manifest-compatible.
Files changed:      src/datp_core/utils/random.py, src/datp_core/utils/determinism.py,
                    tests/unit/test_determinism.py
Tests added:        test_same_seed_gives_same_numpy_sequence, test_different_seeds_differ,
                    test_paired_seed_plan_stable, test_seed_for_role_is_deterministic_and_role_distinct,
                    test_strict_mode_fails_clearly_when_torch_unavailable, test_seed_plan_serializes_to_manifest_compatible_form
Tests run:          `pytest tests/unit/test_determinism.py -q` — 8 passed
Result:             No false determinism claims; strict mode fails clearly given the current environment.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T10 — Hardware/device selection utility
```

```text
## 2026-07-09 — P1-T08 — No-overwrite & artifact lineage guard

Status:            Done
Summary:           Implemented guard_artifact_write() with three modes
                    (create_new, resume_same_run_if_manifest_matches,
                    overwrite_only_if_explicit_and_marked_dev) and
                    guard_results_overwrite() for curated results/, which
                    only allows overwrite when the source manifest matches or
                    an explicit refresh flag is set.
Files changed:      src/datp_core/experiments/overwrite_guard.py,
                    tests/unit/test_artifact_guards.py,
                    tests/integration/test_no_overwrite_policy.py
Tests added:        test_new_artifact_path_is_allowed, test_existing_path_rejected_under_create_new,
                    test_resume_with_matching_manifest_allowed, test_resume_with_mismatched_manifest_rejected,
                    test_explicit_dev_overwrite_requires_flag, test_results_overwrite_without_matching_source_manifest_rejected
Tests run:          `pytest tests/unit/test_artifact_guards.py tests/integration/test_no_overwrite_policy.py -q` — 10 passed
Result:             No production output can be silently overwritten by any of the three modes.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T09 — Determinism & seed-locking utilities
```

```text
## 2026-07-09 — P1-T07 — Artifact manifest schema & read/write helpers

Status:            Done
Summary:           Implemented 12 manifest dataclasses (dataset, preprocessing,
                    split, checkpoint, score, threshold, metric, statistics,
                    table, figure, run, curated-result), each referencing its
                    upstream artifact by manifest_id and rejecting missing
                    required identity fields in __post_init__. Added JSON
                    round-trip (to_dict/to_json/write_manifest, and a
                    from_dict function per type) plus two reuse-identity
                    guards (verify_score_manifest_reuse,
                    verify_checkpoint_manifest_reuse) that reject any
                    identity mismatch.
Files changed:      src/datp_core/experiments/provenance.py,
                    src/datp_core/experiments/artifacts.py,
                    tests/unit/test_manifests.py
Tests added:        test_checkpoint_manifest_round_trips_through_json, test_read_manifest_round_trips,
                    test_score_manifest_cannot_omit_checkpoint_id, test_threshold_manifest_cannot_omit_score_manifest_id,
                    test_metric_manifest_cannot_omit_threshold_id, test_verify_score_manifest_reuse_rejects_identity_mismatch, +8 more
Tests run:          `pytest tests/unit/test_manifests.py -q` — 14 passed
Result:             Every manifest type round-trips through JSON unchanged; reuse mismatches are hard rejections.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T08 — No-overwrite & artifact lineage guard
```

```text
## 2026-07-09 — P1-T06 — Dataset registry skeleton & dataset contract types

Status:            Done
Summary:           Implemented DatasetContract and a DATASET_CONTRACTS
                    registry with one entry per (dataset, regime-scope) named
                    contract: nbaiot (A, C), ciciot2023_file_level (B-a only),
                    ciciot2023_rejected_b_b (rejected, requires
                    rejection_rule, no invented client identity),
                    edge_iiotset (D, D-temporal). require_raw_dataset_present()
                    raises DatasetContractError instead of creating anything
                    when raw data is missing. No dataset loading/preprocessing
                    is implemented.
Files changed:      src/datp_core/data/manifests.py, tests/unit/test_dataset_contracts.py
Tests added:        test_nbaiot_supports_regime_a_and_c, test_ciciot2023_file_level_supports_b_a_only,
                    test_ciciot2023_b_b_requires_metadata_feasibility_and_is_rejected,
                    test_edge_iiotset_supports_regime_d, test_missing_raw_path_is_reported_not_created,
                    test_dataset_contract_serializes_and_deserializes
Tests run:          `pytest tests/unit/test_dataset_contracts.py -q` — 7 passed
Result:             All four dataset contracts match artifact_contracts.md exactly; raw-data absence never auto-creates anything.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T07 — Artifact manifest schema & read/write helpers
```

```text
## 2026-07-09 — P1-T05 — Config skeletons under configs/

Status:            Done
Summary:           Created all 22 config skeleton YAML files across
                    configs/{datasets,training,thresholding,analysis,suites}/
                    named exactly per naming_conventions.md §1, every one
                    `status: contract_only` and loadable/validatable through
                    the P1-T04 loader. Reworked ThresholdingConfig from
                    singular policy/q to plural policies/q_values to
                    represent multi-policy files (core_ladder.yaml lists
                    B0-B4) and sweep files (quantiles.yaml lists 4 q values)
                    without a second schema. Added ModelArchitectureConfig
                    for the dataset-agnostic base_autoencoder.yaml. Made
                    DatasetConfig.client_identity_type optional, required
                    only once a config reaches ready_for_smoke (so
                    edge_iiotset.yaml can stay contract_only pending the
                    P6-T02 feasibility audit without inventing an identity type).
Files changed:      configs/datasets/{nbaiot,ciciot2023_file_level,
                    ciciot2023_rejected_b_b,edge_iiotset}.yaml,
                    configs/training/{base_autoencoder,fedavg_nbaiot,
                    fedavg_edge_iiotset,fedprox_nbaiot,fedprox_edge_iiotset,
                    personalized_ae}.yaml,
                    configs/thresholding/{core_ladder,b_fedstats_benign,
                    quantiles,shrinkage,calibration_size,
                    calibration_size_shrinkage,conformal_b2}.yaml,
                    configs/analysis/{statistics,mechanisms,absorption,
                    reporting}.yaml,
                    configs/suites/{confirmatory_regime_a,regime_c_dirichlet,
                    external_validation_regime_d,threshold_variants,
                    stress_tests,temporal_recalibration,full_journal}.yaml,
                    src/datp_core/config/{schemas,loader,validation}.py (revised),
                    tests/integration/test_config_skeletons.py
Tests added:        test_all_dataset_configs_parse_and_are_phase1_readiness,
                    test_full_journal_suite_refuses_full_execution_during_phase1,
                    test_confirmatory_suite_recognized_but_not_runnable,
                    test_threshold_only_suites_declare_score_reuse_requirement, +4 more
Tests run:          `pytest tests/integration/test_config_skeletons.py -q` — 8 passed
Result:             All 22 skeletons parse and validate; none exceeds
                    implementation_pending readiness; full_journal.is_runnable
                    is False.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T06 — Dataset registry skeleton & dataset contract types
```

```text
## 2026-07-09 — P1-T04 — Typed config loader & schema validation skeleton

Status:            Done
Summary:           Implemented YAML->dataclass loaders for all five config
                    groups (dataset, training/model-architecture,
                    thresholding, analysis, suite) with strict unknown-field
                    rejection, plus protocol-level validation: dataset-regime
                    compatibility, q in (0,1), seed-plan validity, B3 requires
                    a family taxonomy, B4 requires a positive cluster K,
                    B-FedStatsBenign requires benign-only calibration scope,
                    and a threshold-only suite may not enable training unless
                    explicitly overridden.
Files changed:      src/datp_core/config/{loader,schemas,validation}.py,
                    tests/unit/test_config_loader.py, tests/unit/test_config_validation.py
Tests added:        test_valid_minimal_dataset_config_loads, test_unknown_field_fails,
                    test_invalid_dataset_regime_pair_fails, test_invalid_q_fails,
                    test_b3_without_taxonomy_fails, test_b4_invalid_k_fails,
                    test_b_fedstats_benign_under_anomaly_labeled_calibration_fails,
                    test_threshold_only_suite_with_training_enabled_fails, +18 more
Tests run:          `pytest tests/unit/test_config_loader.py tests/unit/test_config_validation.py -q` — 31 passed
Result:             Every required negative case (unknown field, invalid
                    regime/policy/q/seed-plan, B3/B4/B-FedStatsBenign/suite
                    scope rules) is rejected with a typed error.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T05 — Config skeletons under configs/
```

```text
## 2026-07-09 — P1-T03 — Domain enums & typed identifiers

Status:            Done
Summary:           Implemented Regime/RegimeRole/RegimeSpec, ClientIdentityType/
                    ClientId, SplitType/SplitRole/SplitRatios, ThresholdPolicy/
                    Comparator/TrainingAlgorithm, DatasetId, SeedRole/SeedPlan,
                    and Metric/MetricRole/MetricSpec — every value matching
                    docs/protocol/{regimes,policies,naming_conventions,
                    seed_plan,identity_lock}.md literally. All StrEnum
                    (ruff UP042). Verified: no B5/B3-LGS/local_head/LocalHead
                    token anywhere in any enum name or value; AUROC is
                    CONTROL-only; CV(FPR) is the sole PRIMARY/thresholding-verdict
                    metric; Regime A is the sole CONFIRMATORY regime; Regime D
                    is EXTERNAL_VALIDATION only; FedProx/Ditto/FedRep-AE/FedPer-AE
                    are all in STRESS_TEST_COMPARATORS, outside CORE_CAUSAL_LADDER.
Files changed:      src/datp_core/domain/{regimes,clients,partitions,policies,
                    datasets,seeds,metrics}.py, tests/unit/test_domain_enums.py
Tests added:        test_all_enum_values_are_stable, test_no_stale_labels_in_enum_identifiers,
                    test_ditto_fallback_naming_rule_is_representable, test_metric_claim_roles_are_correct,
                    test_auroc_is_marked_control_only, test_regime_a_is_marked_confirmatory,
                    test_regime_d_is_marked_external_validation_only,
                    test_fedprox_and_personalization_are_outside_causal_ladder, +9 more
Tests run:          `pytest tests/unit/test_domain_enums.py -q` — 17 passed
Result:             Domain identifiers match the locked protocol nomenclature exactly.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T04 — Typed config loader & schema validation skeleton
```

```text
## 2026-07-09 — P1-T02 — Canonical path resolver & repository layout contract

Status:            Done
Summary:           Implemented find_repo_root() (walks up for AGENTS.md +
                    pyproject.toml markers), resolve_paths() (repo/config/
                    data/raw/preprocessed/manifest/checkpoint/outputs/results/
                    logs/score/metric/manifest/tables/figures roots, with
                    DATP_DATA_ROOT as the only environment override), and
                    safe_join() (rejects path-escape attempts via ..).
Files changed:      src/datp_core/utils/paths.py, tests/unit/test_paths.py
Tests added:        test_valid_repo_root_detection, test_raw_data_root_resolves_under_data_raw,
                    test_outputs_root_resolves_to_outputs, test_results_root_resolves_to_results,
                    test_checkpoint_root_resolves_to_checkpoints, test_env_override_applies_only_to_data_raw,
                    test_unsupported_env_var_has_no_effect, test_path_escape_is_rejected,
                    test_missing_repo_marker_fails_clearly
Tests run:          `pytest tests/unit/test_paths.py -q` — 10 passed
Result:             All canonical roots resolve correctly; only DATP_DATA_ROOT overrides anything; path escape rejected.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T03 — Domain enums & typed identifiers
```

```text
## 2026-07-09 — P1-T01 — Bootstrap project skeleton & package metadata

Status:            Done
Summary:           Created pyproject.toml (uv/hatchling, Python >=3.11,
                    pyyaml+numpy runtime deps, pytest/ruff/pyright dev deps,
                    datp-core CLI entrypoint), uv.lock, Makefile, .env.example
                    (DATP_DATA_ROOT + DATP_DEVICE only), .gitignore additions
                    for data/raw, data/preprocessed, data/manifests,
                    checkpoints/*, outputs/* (with checkpoints/README.md and
                    outputs/README.md negated), and the Phase 1 package
                    directories (domain, config, utils, data, experiments)
                    under src/datp_core/. No CITATION.cff/VERSIONING.md
                    (release/versioning work is forbidden by AGENTS.md).
                    scripts/ was not created: nothing populates it yet in
                    Phase 1 (structure_decision.md "do not pre-create empty
                    folders").
Files changed:      pyproject.toml, uv.lock, Makefile, .env.example,
                    .gitignore, src/datp_core/__init__.py,
                    src/datp_core/{domain,config,utils,data,experiments}/__init__.py
Tests added:        None (bootstrap ticket; acceptance verified via commands below)
Tests run:          `uv sync`; `uv run pytest --collect-only -q` (32 collected,
                    Phase 0 baseline); `uv run python -c "import datp_core"`;
                    `uv run ruff check .` (clean); `uv run pyright` (0 errors)
Result:             Package imports cleanly; pytest discovers tests; ruff and pyright both clean.
Artifacts created:  None
Decisions made:     None
Blockers:           None
Risks:              None
Next ticket:        P1-T02 — Canonical path resolver & repository layout contract
```

```text
## 2026-07-09 — P0-T11 — Repository structure decision, changelog format & go/no-go coding gate

Status:            Done
Summary:           Ratified the §5 structure decision as docs/protocol/structure_decision.md,
                    wrote docs/protocol/go_no_go.md recording the Go verdict, added the
                    changelog-format parser test, and closed out this changelog for all of
                    Phase 0.
Files changed:      docs/protocol/structure_decision.md (new), docs/protocol/go_no_go.md (new),
                    tests/unit/test_changelog_format.py (new), CHANGELOG.md (this file).
Tests added:        test_changelog_format.py::test_dashboard_fields_present,
                    ::test_status_enum_values, ::test_update_template_present,
                    ::test_no_experimental_claims_in_changelog.
Tests run:          pytest tests/unit -q — see full-suite count in §9.
Result:             Phase 0 exit gate signed Go. Phase 1 authorized but not started.
Artifacts created:  docs/protocol/structure_decision.md, docs/protocol/go_no_go.md.
Decisions made:     None new; ratifies D-002, D-003 (Decision Log §8).
Blockers:           None.
Risks:              None new.
Next ticket:        P1-T01 (not started; requires explicit Phase 1 authorization).
```

```text
## 2026-07-09 — P0-T10 — Old DATP behavioral-reference extraction

Status:            Done
Summary:           Extracted threshold-policy math, eligibility/fallback rule, CV(FPR)
                    formula, split semantics, checkpoint protocol, and AUROC role from
                    /home/naslouby/Projects/datp as behavior-only notes (no source paste, no
                    layout, no module-name inheritance).
Files changed:      docs/protocol/behavioral_reference.md (new),
                    tests/unit/test_behavioral_reference.py (new).
Tests added:        test_behavioral_reference.py::test_no_source_paths_copied,
                    ::test_no_backward_compat_language.
Tests run:          pytest tests/unit/test_behavioral_reference.py -q — 2 passed.
Result:             Behavioral reference locked; no structural/code inheritance introduced.
Artifacts created:  docs/protocol/behavioral_reference.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T11.
```

```text
## 2026-07-09 — P0-T09 — Reuse/caching principle & raw-data placement freeze

Status:            Done
Summary:           Locked the heavy-vs-cheap stage table, the six invalidation triggers, and
                    the data/raw symlink placement contract.
Files changed:      docs/protocol/reuse_policy.md (new), tests/unit/test_reuse_policy_doc.py
                    (new).
Tests added:        test_reuse_policy_doc.py::test_stage_classification_complete,
                    ::test_invalidation_triggers_listed, ::test_threshold_stage_not_marked_heavy.
Tests run:          pytest tests/unit/test_reuse_policy_doc.py -q — 3 passed.
Result:             Reuse/caching contract locked; enforced later by P4-T08 and P7-T09.
Artifacts created:  docs/protocol/reuse_policy.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T10.
```

```text
## 2026-07-09 — P0-T08 — Testing contract & test-pyramid freeze

Status:            Done
Summary:           Canonicalized the unit/integration/smoke/negative test taxonomy
                    (MASTER_TICKET_LOG.md §10) as a standalone doc with a coverage-of-contract
                    rule and named Phase-0 test files.
Files changed:      docs/protocol/testing_contract.md (new),
                    tests/unit/test_testing_contract.py (new).
Tests added:        test_testing_contract.py::test_every_subsystem_has_named_tests,
                    ::test_no_generic_add_tests_placeholder.
Tests run:          pytest tests/unit/test_testing_contract.py -q — 2 passed.
Result:             Testing contract locked as the authority for MASTER_TICKET_LOG.md §10.
Artifacts created:  docs/protocol/testing_contract.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T09.
```

```text
## 2026-07-09 — P0-T07 — Seed plan freeze

Status:            Done
Summary:           Locked the 10-seed set, the B1/B2/B0/B3/B4 pairing rule, the 5-seed
                    preliminary vs 10-seed main distinction, and the seed-extension honesty
                    rule (SB-21).
Files changed:      docs/protocol/seed_plan.md (new), tests/unit/test_seed_plan_doc.py (new).
Tests added:        test_seed_plan_doc.py::test_ten_paired_seeds,
                    ::test_seed_extension_rule_present, ::test_no_seed_dropping_allowed.
Tests run:          pytest tests/unit/test_seed_plan_doc.py -q — 3 passed.
Result:             Seed plan locked; feeds P1-T03 seed types and P2-T09 paired plan.
Artifacts created:  docs/protocol/seed_plan.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T08.
```

```text
## 2026-07-09 — P0-T06 — Config, experiment-suite & experiment-ID naming conventions

Status:            Done
Summary:           Locked the five config groups, the seven suite names, and the full
                    E-C1…E-Q6 experiment-ID-to-suite registry; stated config-key naming rules
                    (enum-backed, no raw policy strings, no "Ditto" hardcode).
Files changed:      docs/protocol/naming_conventions.md (new),
                    tests/unit/test_naming_conventions.py (new).
Tests added:        test_naming_conventions.py::test_experiment_ids_unique,
                    ::test_suite_names_map_to_known_experiments,
                    ::test_no_stale_policy_names_in_registry.
Tests run:          pytest tests/unit/test_naming_conventions.py -q — 3 passed.
Result:             Naming conventions locked; feeds P1-T04 config schemas.
Artifacts created:  docs/protocol/naming_conventions.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T07.
```

```text
## 2026-07-09 — P0-T05 — Dataset & artifact/directory contract definitions

Status:            Done
Summary:           Wrote per-dataset contracts (N-BaIoT, CICIoT2023, Edge-IIoTset; 12 fields
                    each) and the 20-class pipeline artifact contract table (producer,
                    consumers, manifest fields, reuse-validity key, read-only rule); added
                    stub READMEs for data/, checkpoints/, outputs/, results/.
Files changed:      docs/protocol/artifact_contracts.md (new), data/README.md (new),
                    checkpoints/README.md (new), outputs/README.md (new), results/README.md
                    (new), tests/unit/test_artifact_contracts_doc.py (new).
Tests added:        test_artifact_contracts_doc.py::test_every_artifact_has_manifest_fields,
                    ::test_readmes_exist, ::test_results_excludes_heavy_artifacts.
Tests run:          pytest tests/unit/test_artifact_contracts_doc.py -q — 3 passed.
Result:             Dataset/artifact contracts locked; concretely implemented by P1-T07.
Artifacts created:  docs/protocol/artifact_contracts.md, four README.md stubs.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T06.
```

```text
## 2026-07-09 — P0-T04 — Threshold-policy & comparator nomenclature freeze

Status:            Done
Summary:           Locked B0–B4, threshold variants (τ-shrink, calibration-size-aware
                    fallback, B2-conf), comparators (B-FedStatsBenign, B-LaridiFaithful), and
                    stress-test comparators (FedProx, Ditto/FedRep-AE/FedPer-AE), plus every
                    naming lock (no B5, no B3-LGS, B4 canonical K=3, no bare "Ditto").
Files changed:      docs/protocol/policies.md (new), tests/unit/test_policies_doc.py (new).
Tests added:        test_policies_doc.py::test_no_stale_labels, ::test_b0_not_in_causal_ladder,
                    ::test_b4_canonical_k_is_3, ::test_fallback_not_named_ditto.
Tests run:          pytest tests/unit/test_policies_doc.py -q — 4 passed.
Result:             Policy/comparator nomenclature locked; feeds P3/P4 implementations.
Artifacts created:  docs/protocol/policies.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T05.
```

```text
## 2026-07-09 — P0-T03 — Regime definitions freeze (A / B-a / B-b / C / D / D-temporal)

Status:            Done
Summary:           Locked all six regimes with role, client definition, purpose, threshold
                    policies, primary metric, and pass/fail/suppression rule; recorded the two
                    rejected-status labels (B_B_REJECTED_NO_METADATA,
                    TEMPORAL_REJECTED_NO_TIMESTAMPS).
Files changed:      docs/protocol/regimes.md (new), tests/unit/test_regimes_doc.py (new).
Tests added:        test_regimes_doc.py::test_all_regimes_have_role_and_passrule,
                    ::test_bb_marked_rejected, ::test_no_quantitative_bb_claim.
Tests run:          pytest tests/unit/test_regimes_doc.py -q — 3 passed.
Result:             Regime definitions locked; drives the Regime enum and P6 loaders/guards.
Artifacts created:  docs/protocol/regimes.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T04.
```

```text
## 2026-07-09 — P0-T02 — Claim hierarchy & confirmatory-endpoint isolation freeze

Status:            Done
Summary:           Locked the nine claim tiers with the singular Tier-1 confirmatory claim,
                    evidence/regime/metric/min-pass/fallback/reviewer-risk/placement fields
                    per tier, and the Tier-9 forbidden-claims list.
Files changed:      docs/protocol/claim_hierarchy.md (new),
                    tests/unit/test_claim_hierarchy.py (new).
Tests added:        test_claim_hierarchy.py::test_single_confirmatory_tier1,
                    ::test_tier9_forbidden_enumerated, ::test_no_supportive_marked_confirmatory.
Tests run:          pytest tests/unit/test_claim_hierarchy.py -q — 3 passed.
Result:             Claim hierarchy locked; feeds ClaimRole enum and P7-T04 claim gates.
Artifacts created:  docs/protocol/claim_hierarchy.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T03.
```

```text
## 2026-07-09 — P0-T01 — Scientific scope & identity freeze

Status:            Done
Summary:           Locked the fixed-encoder / sole-causal-variable / benign-only /
                    CV(FPR)-primary / AUROC-control / stress-outside-ladder identity
                    statements and the operational-FPR-equity fairness definition; enumerated
                    SB-01…SB-32 as a parseable, testable list.
Files changed:      docs/protocol/identity_lock.md (new), docs/protocol/scope_boundaries.md
                    (new), tests/unit/test_scope_boundaries.py (new).
Tests added:        test_scope_boundaries.py::test_all_SB_ids_present_and_unique,
                    ::test_forbidden_terms_absent.
Tests run:          pytest tests/unit/test_scope_boundaries.py -q — 2 passed.
Result:             Scientific identity locked; imported by all later P0 docs and by P1-T02.
Artifacts created:  docs/protocol/identity_lock.md, docs/protocol/scope_boundaries.md.
Decisions made:     None new.
Blockers:           None.
Risks:              None new.
Next ticket:        P0-T02.
```

```text
## 2026-07-09 — Planning — MASTER_TICKET_LOG.md + CHANGELOG.md created

Status: Done
Summary: Authored the full 82-ticket master plan across 8 phases and this
         progress tracker. No implementation started.
Files changed: MASTER_TICKET_LOG.md (new), CHANGELOG.md (new).
Tests added: None (planning only).
Tests run: None.
Result: Plan of record established; ready to begin P0-T01.
Artifacts created: MASTER_TICKET_LOG.md, CHANGELOG.md.
Decisions made: See Decision Log §8 (D-001…D-006).
Blockers: None.
Risks: See MASTER_TICKET_LOG §19 (R1–R14).
Next ticket: P0-T01 — Scientific scope & identity freeze.
```

---

## 6. In-Progress Work Log

*None.* When a ticket moves to `In Progress`, record: ticket ID, start date,
current sub-tasks, partial artifacts, and any early findings.

---

## 7. Blocked Ticket Log

*None.*

---

## 8. Decision Log

| ID | Date | Decision | Rationale | Affected tickets |
|---|---|---|---|---|
| D-001 | 2026-07-09 | 82 tickets across 8 phases (vs ~60 target) | Reviewer-proof single-concern separation (L01–L28, SB-01–SB-32); heavy/cheap reuse split | All |
| D-002 | 2026-07-09 | Reject `VERSIONING.md` and `CITATION.cff` | Governance forbids release/tag/versioning work | P1-T01 |
| D-003 | 2026-07-09 | Keep `data/raw` as existing symlink; no committed `.gitkeep` trees inside it | Symlink already points to shared data; folders created lazily | P0-T05, P1-T07, P2-T01 |
| D-004 | 2026-07-09 | Model-personalization fallback never labeled "Ditto" | SB-24; use `FedRep-AE`/`FedPer-AE` unless true Ditto implemented | P6-T11 |
| D-005 | 2026-07-09 | `B-FedStatsBenign` uses full pooled variance + matched-exceedance, locked before computation | SB-26/27; matched-exceedance is the main comparison | P4-T05, P4-T06 |
| D-006 | 2026-07-09 | Statistics (BCa CI) computed in P7-T03; claim gating separated into P7-T04 | Keep number computation distinct from claim pass/fail logic | P7-T03, P7-T04 |
| D-007 | 2026-07-09 | Execute Phase 1 under a user-authorized 18-ticket breakdown (P1-T01..P1-T18) instead of the original 10-ticket plan; total ticket count moves 82→90 | User request explicitly permitted splitting tickets and required recording the deviation; finer granularity matches one-concern-per-ticket governance | P1-T01..P1-T18 (see §12) |
| D-008 | 2026-07-09 | `ThresholdingConfig` uses plural `policies`/`q_values` instead of singular `policy`/`q` | `core_ladder.yaml` must list all of B0-B4 and `quantiles.yaml` must list a q-sweep in one file without a second schema | P1-T04, P1-T05 |
| D-009 | 2026-07-09 | Anchor execution requires configured CUDA PyTorch and the exact external `N-BaIoT` raw directory | The available RTX 5060 Ti is mandatory for anchor commands; no CPU fallback or lowercase path alias remains | P2-T20 |
| D-011 | 2026-07-09 | Internal protocol state and registries use dataclasses/tuples; mappings are I/O adapters only | Typed state prevents unvalidated keys and hidden runtime behavior while retaining required YAML/JSON/NPZ/PyTorch interoperability | P2-T20 remediation |
| D-009 | 2026-07-09 | `DatasetConfig.client_identity_type` is optional below `ready_for_smoke` readiness | `edge_iiotset.yaml`'s identity type is genuinely undecided pending the P6-T02 feasibility audit (SB-28 forbids inventing it); `ciciot2023_rejected_b_b.yaml` never gets one | P1-T04, P1-T05 |
| D-010 | 2026-07-09 | `src/datp_core/data/cache.py` (preprocessing cache) and the CLI run-dispatcher/readiness-gate (`experiments/plan.py`, `experiments/runner.py`, `experiments/readiness.py`, `scripts/run_experiment.py`) are deferred to Phase 2 | Nothing in Phase 1 needs an actual cache or execution engine yet; building them now would be scientific-algorithm-adjacent scope beyond a contract/skeleton | P1-T08 (original), P1-T09 (original) — see §12 |

---

## 9. Test Log

| Date | Ticket | Command | Result | Notes |
|---|---|---|---|---|
| 2026-07-09 | P0-T01 | `pytest tests/unit/test_scope_boundaries.py -q` | 2 passed | SB-ID parser + forbidden-term negation checks |
| 2026-07-09 | P0-T02 | `pytest tests/unit/test_claim_hierarchy.py -q` | 3 passed | Tier parser |
| 2026-07-09 | P0-T03 | `pytest tests/unit/test_regimes_doc.py -q` | 3 passed | Regime role/pass-rule parser |
| 2026-07-09 | P0-T04 | `pytest tests/unit/test_policies_doc.py -q` | 4 passed | Naming-lock parser |
| 2026-07-09 | P0-T05 | `pytest tests/unit/test_artifact_contracts_doc.py -q` | 3 passed | Artifact-table + README existence |
| 2026-07-09 | P0-T06 | `pytest tests/unit/test_naming_conventions.py -q` | 3 passed | Experiment-ID registry parser |
| 2026-07-09 | P0-T07 | `pytest tests/unit/test_seed_plan_doc.py -q` | 3 passed | Seed-set + honesty-rule parser |
| 2026-07-09 | P0-T08 | `pytest tests/unit/test_testing_contract.py -q` | 2 passed | Subsystem-coverage parser |
| 2026-07-09 | P0-T09 | `pytest tests/unit/test_reuse_policy_doc.py -q` | 3 passed | Stage-classification parser |
| 2026-07-09 | P0-T10 | `pytest tests/unit/test_behavioral_reference.py -q` | 2 passed | No-source-paste / no-compat-language checks |
| 2026-07-09 | P0-T11 | `pytest tests/unit -q` | 32 passed | Full Phase-0 doc-parser suite (includes test_changelog_format.py) |
| 2026-07-09 | P1-T01 | `uv sync && uv run pytest --collect-only -q` | 32 collected | Package imports cleanly on top of Phase 0 baseline |
| 2026-07-09 | P1-T02 | `pytest tests/unit/test_paths.py -q` | 10 passed | Path resolver + escape rejection |
| 2026-07-09 | P1-T03 | `pytest tests/unit/test_domain_enums.py -q` | 17 passed | Domain enum/identifier locks |
| 2026-07-09 | P1-T04 | `pytest tests/unit/test_config_loader.py tests/unit/test_config_validation.py -q` | 31 passed | Config loader + validation rules |
| 2026-07-09 | P1-T05 | `pytest tests/integration/test_config_skeletons.py -q` | 8 passed | All 22 config skeletons parse/validate |
| 2026-07-09 | P1-T06 | `pytest tests/unit/test_dataset_contracts.py -q` | 7 passed | Dataset contract registry |
| 2026-07-09 | P1-T07 | `pytest tests/unit/test_manifests.py -q` | 14 passed | Manifest JSON round-trip + required-field guards |
| 2026-07-09 | P1-T08 | `pytest tests/unit/test_artifact_guards.py tests/integration/test_no_overwrite_policy.py -q` | 10 passed | No-overwrite policy (3 modes) |
| 2026-07-09 | P1-T09 | `pytest tests/unit/test_determinism.py -q` | 8 passed | Seed application + role-derived sub-seeds |
| 2026-07-09 | P1-T10 | `pytest tests/unit/test_hardware.py -q` | 8 passed | CPU-fallback device selection |
| 2026-07-09 | P1-T11 | `pytest tests/unit/test_logging.py -q` | 5 passed | No duplicate handlers; run_id formatting |
| 2026-07-09 | P1-T12 | `pytest tests/unit/test_cli.py -q` | 7 passed | CLI skeleton, 5 read-only commands |
| 2026-07-09 | P1-T13 | `pytest tests/unit/test_fixtures.py -q` | 5 passed | Tiny deterministic fixtures |
| 2026-07-09 | P1-T14 | `pytest tests/unit/test_layout.py -q` | 6 passed | Repo layout + artifact-placement guards |
| 2026-07-09 | P1-T15 | `pytest tests/unit -q` | 158 passed | Full Phase 1 unit sweep |
| 2026-07-09 | P1-T16 | `pytest tests/integration -q` | 19 passed | Full Phase 1 integration sweep |
| 2026-07-09 | P1-T17 | `make show-paths list-suites lint typecheck unit integration validate-config validate-layout doctor` | all exit 0 | Every documented dev command verified |
| 2026-07-09 | P1-T18 | `pytest -q`; `ruff check .`; `pyright` | 177 passed; clean; 0 errors | Final Phase 1 quality gate |

Record `make test` / `make lint` / `make typecheck` and targeted `pytest` runs
here, one row per meaningful run, tied to the ticket that triggered it.

---

## 10. Files Changed Log

| Date | Ticket | File | Change |
|---|---|---|---|
| 2026-07-09 | Planning | `MASTER_TICKET_LOG.md` | Created (82-ticket plan) |
| 2026-07-09 | Planning | `CHANGELOG.md` | Created (this tracker) |
| 2026-07-09 | P0-T01 | `docs/protocol/identity_lock.md` | Created |
| 2026-07-09 | P0-T01 | `docs/protocol/scope_boundaries.md` | Created |
| 2026-07-09 | P0-T01 | `tests/unit/test_scope_boundaries.py` | Created |
| 2026-07-09 | P0-T02 | `docs/protocol/claim_hierarchy.md` | Created |
| 2026-07-09 | P0-T02 | `tests/unit/test_claim_hierarchy.py` | Created |
| 2026-07-09 | P0-T03 | `docs/protocol/regimes.md` | Created |
| 2026-07-09 | P0-T03 | `tests/unit/test_regimes_doc.py` | Created |
| 2026-07-09 | P0-T04 | `docs/protocol/policies.md` | Created |
| 2026-07-09 | P0-T04 | `tests/unit/test_policies_doc.py` | Created |
| 2026-07-09 | P0-T05 | `docs/protocol/artifact_contracts.md` | Created |
| 2026-07-09 | P0-T05 | `data/README.md` | Created |
| 2026-07-09 | P0-T05 | `checkpoints/README.md` | Created |
| 2026-07-09 | P0-T05 | `outputs/README.md` | Created |
| 2026-07-09 | P0-T05 | `results/README.md` | Created |
| 2026-07-09 | P0-T05 | `tests/unit/test_artifact_contracts_doc.py` | Created |
| 2026-07-09 | P0-T06 | `docs/protocol/naming_conventions.md` | Created |
| 2026-07-09 | P0-T06 | `tests/unit/test_naming_conventions.py` | Created |
| 2026-07-09 | P0-T07 | `docs/protocol/seed_plan.md` | Created |
| 2026-07-09 | P0-T07 | `tests/unit/test_seed_plan_doc.py` | Created |
| 2026-07-09 | P0-T08 | `docs/protocol/testing_contract.md` | Created |
| 2026-07-09 | P0-T08 | `tests/unit/test_testing_contract.py` | Created |
| 2026-07-09 | P0-T09 | `docs/protocol/reuse_policy.md` | Created |
| 2026-07-09 | P0-T09 | `tests/unit/test_reuse_policy_doc.py` | Created |
| 2026-07-09 | P0-T10 | `docs/protocol/behavioral_reference.md` | Created |
| 2026-07-09 | P0-T10 | `tests/unit/test_behavioral_reference.py` | Created |
| 2026-07-09 | P0-T11 | `docs/protocol/structure_decision.md` | Created |
| 2026-07-09 | P0-T11 | `docs/protocol/go_no_go.md` | Created |
| 2026-07-09 | P0-T11 | `tests/unit/test_changelog_format.py` | Created |
| 2026-07-09 | P0-T11 | `CHANGELOG.md` | Updated (dashboard, tables, 11 update blocks, this log) |
| 2026-07-09 | P1-T01 | `pyproject.toml`, `uv.lock`, `Makefile`, `.env.example`, `.gitignore`, `src/datp_core/__init__.py` + 5 subpackage `__init__.py` | Created |
| 2026-07-09 | P1-T02 | `src/datp_core/utils/paths.py`, `tests/unit/test_paths.py` | Created |
| 2026-07-09 | P1-T03 | `src/datp_core/domain/{regimes,clients,partitions,policies,datasets,seeds,metrics}.py`, `tests/unit/test_domain_enums.py` | Created |
| 2026-07-09 | P1-T04 | `src/datp_core/config/{loader,schemas,validation}.py`, `tests/unit/test_config_{loader,validation}.py` | Created |
| 2026-07-09 | P1-T05 | `configs/{datasets,training,thresholding,analysis,suites}/*.yaml` (22 files), `tests/integration/test_config_skeletons.py` | Created |
| 2026-07-09 | P1-T06 | `src/datp_core/data/manifests.py`, `tests/unit/test_dataset_contracts.py` | Created |
| 2026-07-09 | P1-T07 | `src/datp_core/experiments/{provenance,artifacts}.py`, `tests/unit/test_manifests.py` | Created |
| 2026-07-09 | P1-T08 | `src/datp_core/experiments/overwrite_guard.py`, `tests/unit/test_artifact_guards.py`, `tests/integration/test_no_overwrite_policy.py` | Created |
| 2026-07-09 | P1-T09 | `src/datp_core/utils/{determinism,random}.py`, `tests/unit/test_determinism.py` | Created |
| 2026-07-09 | P1-T10 | `src/datp_core/utils/hardware.py`, `tests/unit/test_hardware.py` | Created |
| 2026-07-09 | P1-T11 | `src/datp_core/utils/logging.py`, `tests/unit/test_logging.py` | Created |
| 2026-07-09 | P1-T12 | `src/datp_core/cli.py`, `src/datp_core/utils/layout.py`, `tests/unit/test_cli.py` | Created |
| 2026-07-09 | P1-T13 | `tests/fixtures/*.py` (7 files), `tests/unit/test_fixtures.py`, `pyproject.toml` | Created / Updated (`pythonpath`) |
| 2026-07-09 | P1-T14 | `tests/unit/test_layout.py`, `tests/integration/test_layout_contract.py` | Created |
| 2026-07-09 | P1-T16 | `tests/integration/{test_manifest_lineage,test_cli_doctor}.py` | Created |
| 2026-07-09 | P1-T17 | `README.md`, `Makefile` | Updated |
| 2026-07-09 | P1-T18 | `CHANGELOG.md`, `MASTER_TICKET_LOG.md` | Updated |

---

## 11. Risks and Follow-ups

- Live risk register is maintained in [MASTER_TICKET_LOG.md §19](MASTER_TICKET_LOG.md)
  (R1–R14). Add follow-ups here as they surface during implementation.
- Conditional gates (non-blocking for Regime A/C): OQ1 CICIoT2023 feature-count
  verification (P6-T07); OQ2 Edge-IIoTset coverage/partition (P6-T02/T04); OQ3
  Ditto-vs-fallback choice (P6-T11). See MASTER_TICKET_LOG §20.
- **Preprocessing cache contract not built.** The original P1-T08
  (`src/datp_core/data/cache.py`, raw-hash + preprocessing-config-hash cache
  keying) was not implemented this session (§12). Phase 2 preprocessing
  tickets (P2-T02, P6-T03) will need it before they can claim heavy-stage
  reuse; pick it up as an early Phase 2 ticket or reopen it explicitly.
- **CLI run-dispatcher/readiness gate not built.** The original P1-T09's
  `datp run <suite>` dispatch, `experiments/plan.py`, `experiments/runner.py`,
  and `experiments/readiness.py` were not implemented (§12); Phase 1's CLI is
  read-only by design, but Phase 2 will need a controlled single execution
  surface before any heavy stage runs, per the "no hidden one-off scripts" rule.
- **CHANGELOG-consistency enforcement test not built.** The original P1-T10
  wanted `tests/integration/test_changelog_update_after_ticket.py` (asserts
  Done tickets carry a tests-run entry, Blocked tickets carry a blocker entry,
  and changelog status matches MASTER_TICKET_LOG.md programmatically). This
  session's `test_changelog_format.py` (from P0-T11) checks structural format
  only, not per-ticket consistency. Recommend building this test before Phase 2
  produces enough tickets for manual consistency checking to become unreliable.

---

## 12. Deviations from MASTER_TICKET_LOG.md

Phase 1 was executed under an alternate ticket breakdown supplied directly by
the requesting user for this session (18 tickets, P1-T01..P1-T18), explicitly
authorized to split/renumber the original 10-ticket Phase 1 plan
(MASTER_TICKET_LOG.md §"Phase 1 — Scratch Foundation", original P1-T01..P1-T10).
Recorded per-item below:

| Ticket(s) | Deviation type | Reason | Master-log update |
|---|---|---|---|
| Original P1-T01..P1-T10 → new P1-T01..P1-T18 | Split | User-supplied, more granular breakdown (one concern per ticket: path resolver, domain enums, config loader, config skeletons, dataset registry, manifests, no-overwrite guard, determinism, hardware, logging, CLI, fixtures, layout checks, unit-test sweep, integration-test sweep, docs, quality gate — each isolated) | Phase 1 total revised 10→18; plan-of-record total 82→90 (§2). Original P1-T01..P1-T10 prose bodies in `MASTER_TICKET_LOG.md` are left as the historical plan record; see the implementation note added directly above `#### P1-T01` there. |
| Original P1-T08 "Preprocessing cache contract" (`data/cache.py`) | Skipped (deferred) | Not requested by the user's 18-ticket brief; nothing in Phase 1 performs preprocessing yet, so a cache has nothing to key against. Building it now would be premature/speculative. | Deferred to Phase 2 (§11 follow-up). Original ticket body left untouched in `MASTER_TICKET_LOG.md`. |
| Original P1-T09 "CLI entrypoint & dataset registry" — the run-dispatch half (`experiments/{plan,runner,readiness}.py`, `scripts/run_experiment.py`, `datp run <suite>`) | Skipped (deferred) | The user's Phase 1 brief explicitly required the CLI to expose read-only commands only and forbade any training/run command in Phase 1 ("training command is absent or blocked"); the dataset-registry half of the original ticket is covered by new P1-T06, and the CLI-skeleton half by new P1-T12. | Deferred to Phase 2 (§11 follow-up). Original ticket body left untouched in `MASTER_TICKET_LOG.md`. |
| Original P1-T02 `ClientKind` naming | Naming difference (non-breaking) | The canonical protocol doc (`docs/protocol/naming_conventions.md`) and this session's own domain-enum ticket used `ClientIdentityType` throughout; no `ClaimRole` enum was built in `domain/` since Tier/claim-role logic already lives in `docs/protocol/claim_hierarchy.md` (Phase 0) and is consumed there, not re-encoded as a Phase 1 domain type. | No master-log content changed; noted here for traceability only. |
| Original P1-T10 CHANGELOG-consistency enforcement test | Not built this session | Out of the user's explicit 18-ticket list for this session. | See §11 follow-up; recommend an early Phase 2 (or reopened Phase 1) ticket. |
| Original Phase 2 P2-T01..P2-T11 → authorized P2-T01..P2-T20 | Split | The user supplied a finer, explicitly scoped Phase 2 contract that separates discovery, loader, mapping, split/leakage, model/training, artifacts, B1/B2, evaluation, planning, commands, tests, and quality gate. | Phase 2 total revised 11→20; plan total 90→99. The historical Phase 2 prose remains in the master log with an explicit supersession note. |

Changelog statuses in §3 match `MASTER_TICKET_LOG.md`'s Phase 1 implementation
note (see the note directly above `#### P1-T01` there) as of this update.

---

## 13. Next Action

- **Phase 0 is complete.** All eleven P0 tickets are `Done`; the go/no-go gate
  ([docs/protocol/go_no_go.md](docs/protocol/go_no_go.md)) is signed **Go**.
- **Phase 1 is complete.** All eighteen P1 tickets (this session's revised
  breakdown, §12) are `Done`; the Phase 1 quality gate (P1-T18) is green:
  `pytest -q` 177 passed, `ruff check .` clean, `pyright` 0 errors.
- **Phase 2 implementation is ready.** The real `data/raw/N-BaIoT` inventory
  has nine physical-device candidates and CUDA execution is enforced; no real
  mini/full run or scientific result has been produced.
- **Next action:** authorize and run the two-seed mini gate, then decide
  separately whether to authorize the operator-gated full 10-seed run.
- **Phase 3 has not started.** B3/B4, variants, FedProx, personalization,
  Regime C, external datasets, temporal work, statistics, and curation remain out of scope.

---

## 14. Update Template (use after every ticket)

```text
## YYYY-MM-DD — P?-T?? — Ticket Title

Status:            (Done / In Progress / Blocked / Skipped / Split / Merged / Reopened)
Summary:           (what changed, one paragraph)
Files changed:     (paths)
Tests added:       (named tests)
Tests run:         (command + pass/fail counts)
Result:            (outcome — implementation status only, never a scientific claim)
Artifacts created: (manifests/outputs, or None)
Decisions made:    (link Decision Log IDs, or None)
Blockers:          (blocker + dependency, or None)
Risks:             (new/updated risks, or None)
Next ticket:       (ID + title)
```

After filling the template: update the §1 dashboard, the §2 phase table, and the
§3 ticket row for that ticket. Marking a ticket `Done` requires a Tests-run entry;
marking it `Blocked` requires a §7 blocker entry.

---

## 15. Phase 0 Consistency Audit (P0-T14/P0-T11 exit check)

Run 2026-07-09 after all eleven P0 tickets reached `Done` and
`pytest tests/unit -q` passed (32/32). Manual review against the checklist
below; each row cites the doc that carries the guarantee.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Scientific identity is preserved | Pass | `docs/protocol/identity_lock.md` |
| 2 | Core ladder has a fixed encoder | Pass | `identity_lock.md` §1, `policies.md` |
| 3 | B1–B4 share the same AE checkpoint per seed | Pass | `behavioral_reference.md` §7, `artifact_contracts.md` (frozen-checkpoint reuse key) |
| 4 | Calibration is benign-only | Pass | `identity_lock.md` §4, `behavioral_reference.md` §6 |
| 5 | Attack data is excluded from threshold fitting | Pass | `behavioral_reference.md` §6, `artifact_contracts.md` §1 (per-dataset benign-only requirement) |
| 6 | AUROC is not used as the threshold verdict | Pass | `identity_lock.md` §6, `behavioral_reference.md` §8 |
| 7 | Regime A confirmatory endpoint is isolated | Pass | `claim_hierarchy.md` Tier 1 (singular `role=confirmatory`), `regimes.md` |
| 8 | Supportive/stress/exploratory modules are not promoted | Pass | `claim_hierarchy.md` (`test_no_supportive_marked_confirmatory`) |
| 9 | FedProx and personalization are outside the causal ladder | Pass | `policies.md` (stress-test comparators table), `identity_lock.md` §8 |
| 10 | Regime D is external validation only | Pass | `regimes.md` (`role: external_validation`) |
| 11 | CICIoT2023 B-b has a metadata-based guard | Pass | `regimes.md`, `artifact_contracts.md` §1.2 rejection rule |
| 12 | Threshold variants are threshold-only unless explicitly requiring new scores | Pass | `reuse_policy.md` stage table |
| 13 | Score reuse contract is explicit | Pass | `artifact_contracts.md` §2 (reuse-validity key column) |
| 14 | Checkpoint reuse contract is explicit | Pass | `artifact_contracts.md` §2, `checkpoints/README.md` |
| 15 | No hidden retraining is allowed | Pass | `reuse_policy.md` "Enforcement" |
| 16 | No stale labels are allowed | Pass | `policies.md` "Naming Locks" (`test_no_stale_labels`) |
| 17 | No old DATP compatibility is allowed | Pass | `behavioral_reference.md` (`test_no_backward_compat_language`) |
| 18 | No shims are allowed | Pass | `structure_decision.md` "Rejected" |
| 19 | No duplicated pipelines are allowed | Pass | `reuse_policy.md` "Enforcement" (P7-T08 dry-run cross-reference) |
| 20 | Repository structure decision is documented | Pass | `docs/protocol/structure_decision.md` |
| 21 | Changelog is initialized | Pass | This file (dashboard, phase/ticket tables, 12 update blocks) |
| 22 | Phase 1 entry criteria are clear | Pass | `docs/protocol/go_no_go.md` |
| 23 | No temp files or ops/audit side folders were created | Pass | `git status --short` shows only `docs/protocol/`, `tests/`, four README stubs, and this file |
| 24 | No runtime/experiment code exists | Pass | No `src/`, `pyproject.toml`, or `scripts/` created |
| 25 | No raw dataset was moved or modified | Pass | `data/raw` symlink untouched; only `data/README.md` added |

**Audit result: 25/25 pass, 0 failures.** Phase 0 go/no-go
([docs/protocol/go_no_go.md](docs/protocol/go_no_go.md)) is signed **Go**.

---

## Initial State (bootstrap record)

- **Initial status:** Not Started (0 / 82 Done).
- **Initial phase:** Phase 0 — Protocol, Scope & Architecture Freeze.
- **Initial ticket:** P0-T01 — Scientific scope & identity freeze.
- **Initial blocker state:** None.
- **Next action:** Begin P0-T01 (see §13).
- **Reminder:** This changelog MUST be updated after every ticket using the §14
  template, and its statuses MUST stay consistent with
  [MASTER_TICKET_LOG.md](MASTER_TICKET_LOG.md). It records implementation progress
  only — never unverified experimental claims.
