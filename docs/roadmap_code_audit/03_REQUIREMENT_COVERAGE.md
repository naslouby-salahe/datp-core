# 03 — Requirement Coverage

## Scope disclosure

The Requirement Traceability Matrix in `docs/Journal_Extension_Audit_Matrix.md` contains on the order of
1,700+ individual atomic requirement rows (per repo memory from a prior independent reconciliation pass:
ROADMAP_REQUIRED 1,678 + DERIVED_INVARIANT 14 + ROADMAP_UNSPECIFIED 42 = 1,734). Producing a literal
per-row table with independent fresh evidence for all ~1,734 rows in a single pass was not completed;
instead, coverage was verified **domain-by-domain** (one dedicated read-only subagent per domain, each
required to cite `file:line` evidence, run adversarial checks from Matrix §76, and grep the matrix's own
formula/numerical ledgers directly) which reaches every requirement *category* the matrix defines, backed
by concrete source citations, but does not produce 1,734 individually-numbered rows. This is disclosed here
rather than fabricating row-level completeness.

## Domain-level coverage table

| Domain | Requirement families covered | Verdict | Evidence file |
|---|---|---|---|
| CLI / execution spine / registry | Public CLI contract, experiment registry↔recipe wiring, suppressed-experiment handling | PASS | `01_..`, `02_..` |
| Datasets & populations (N-BaIoT, CICIoT2023, Edge-IIoTset) | Schema, client identity, chronology, family taxonomy, exclusions, forbidden reconstructions | PASS | `06_..` |
| Splits | Proportions/ordering per protocol, disjointness, benign-only train/calibration, temporal no-future-leakage | PASS | `06_..` |
| Preprocessing | Scaler family, fit scope, train-only fitting, serialization/reload tolerance, frozen-state reuse by thresholds | PASS | `06_..` |
| Training (FedAvg/FedProx/Ditto/Centralized) | Algorithm distinctness, CUDA-only, seed determinism, no test-outcome influence | PASS | `05_..` |
| Checkpoints | Candidate rounds, terminal-round selection rule, non-test gating, one checkpoint shared across policies | PASS | `05_..` |
| Scoring / fixed-score identity | `FixedScoreInvariant`, shared-artifact reuse across threshold policies, SCIENTIFIC_ARTIFACT_IDENTITY vs NUMERICAL_RELOAD_EQUIVALENCE separation | PASS | `06_..` |
| Calibration & thresholds (SHARED/LOCAL/FAMILY/CLUSTER + shrinkage/conformal/federated-statistics) | Benign-only eligibility, formulas, no evaluation-data leakage, cluster fingerprint isolation | PASS | `06_..` |
| Metrics & statistics | Formula Ledger (36 formulas spot-checked), BCa/Wilcoxon/Holm, seed-level (not client/row) resampling unit, typed unavailability | PASS | `07_..` |
| Anchor gate | Locked interval [0.647,0.769], width 0.122, multiplier 1.20, 14 atomic conditions, gate blocks downstream on failure | PASS | `05_..` |
| Temporal | Historical<calibration<future-recalibration<evaluation ordering enforced in code, no pseudo-chronology | PASS | `05_..` |
| Artifacts / provenance / reuse | Checksum single-source (`artifacts/provenance.py`), completion markers fail-closed, overwrite scoped, coordinate-based collision-proofing | PASS (with 2 documented tree-diagram deviations, see `08_FINDINGS.md`) | `06_..` |
| Reporting / publication reverse-trace | No metric recomputation in export layer, 2 concrete value chains traced end-to-end | PASS (with 1 documented tree-diagram deviation) | `07_..` |
| Experiment catalogue reconciliation | 24/24 matrix↔registry match, 15+ numerical locks spot-checked, naming discipline (no B0-B5/Regime A-D in code) | PASS | `05_..` |

## Roadmap_unspecified items (confirmed correctly left unresolved, not defects)

- `SIZE_AWARE_SHRINKAGE`: no locked λ(n_k) function exists; correctly returns a typed `ThresholdUnavailableResult` rather than inventing one.
- N-BaIoT/CICIoT2023 chronology: genuinely absent in source data; correctly `UNAVAILABLE`, no pseudo-timestamp fabrication found.
- CICIoT2023 physical-device population: none declared (matches roadmap AMBIG-007 resolution); only `CICIOT_FILE_CLIENTS` exists.
- Family taxonomy: only defined for N-BaIoT; correctly `NOT_APPLICABLE`/`UNAVAILABLE` elsewhere.

## Not independently re-derived this pass

Exact per-row reconciliation of every one of the ~1,734 Requirement Traceability Matrix rows against a
dedicated `03_REQUIREMENT_COVERAGE.md` line was not performed (see scope disclosure above). No evidence
of a defect was found in any category audited; if full row-level traceability is required, that is
additional, separately-scoped work beyond this session's 10-domain deep audit.
