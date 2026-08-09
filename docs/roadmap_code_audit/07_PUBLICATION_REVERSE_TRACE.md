# 07 — Publication Reverse Trace

## Traced value #1: Confirmatory CV(FPR) primary contrast

```
presentation/export.py: export_confirmatory_publication() → _interval_table()
  ← document.interval.point_estimate                      (analysis/evidence.py: AnalysisDocument, frozen)
  ← analysis/evidence.analyze_confirmatory_evidence() → analysis/preparation.paired_bca_interval()
  ← experiments/confirmatory/run.py: _confirmatory_contrast(seed) → load_evaluation_document()
  ← detector/scoring FederatedScoreRecord (checksum + path, immutable)
  ← ExperimentWorkspace.scores / .threshold / .selected_checkpoint (cached, single computation)
  ← preprocessing / split / population / canonical dataset chain (06_DATA_AND_ARTIFACT_LINEAGE.md)
```
No recomputation found in `export.py` — it only reads already-computed `AnalysisDocument` fields.

## Traced value #2: AUROC control value

```
experiments/centralized_reference.py: _centralized_reference_publication()
  ← CentralizedReferenceReportManifest (pre-evaluated metrics)
  ← analysis/metrics/fixed_score_construction.py: _client_auroc_evidence()
  ← FederatedScoreRecord (continuous reconstruction-error scores, not threshold predictions)
  ← FixedScoreInvariant.from_manifest() validates checkpoint/score/label identity match
```
AUROC is explicitly a fixed-score/model-quality control per CLAUDE.md §2, computed from continuous scores independent of threshold-calibration scope — confirmed, not merely asserted.

## Reporting-must-not-recompute-science checks (Matrix §47)

| Prohibited behavior | Found? | Evidence |
|---|---|---|
| Recalculate metrics differently in export layer | No | `export.py`/`presentation/tables.py` only format pre-computed `AnalysisDocument`/manifest fields |
| Re-select clients / filter seeds in reporting | No | seed cohort is fixed at experiment-plan level, not report level |
| Convert unavailable to zero | No | `AvailabilityStatus`/`MetricAvailability` typed unions propagate into table cells (`TableCell` with `AvailabilityStatus`) |
| Recompute thresholds in reporting | No | reporting consumes `ThresholdConstructionResult`, never calls `thresholds/dispatch.py` itself |
| Select a preferred/favorable result | No | no filtering logic found in `presentation/` beyond formatting |

## Negative-result / unavailability preservation

- `SIZE_AWARE_SHRINKAGE` → typed `ThresholdUnavailableResult`, reaches the report as an explicit unavailable cell, not silently dropped.
- `ALERT_BURDEN_TRANSLATION` → `SUPPRESSED`, absent from campaign output entirely (correct, since no traffic-rate evidence exists — verified against raw N-BaIoT data in a prior session, see repo memory `graphify-audit-verification.md`).
- `CONFIRMATORY_INFERENCE_UNAVAILABLE` (degenerate BCa, <10 valid paired seeds) → `ScientificDecision.NOT_ESTABLISHED`, no secondary-result substitution found.

## Confirmed deviation from canonical file-level tree (see `08_FINDINGS.md`)

`experiments/anchor/`, `experiments/confirmatory/`, `experiments/temporal/` do not each contain the full `spec.py/run.py/analyze.py/report.py` quartet the CLAUDE.md diagram lists; publication calls are made directly from `run.py`. No recomputation-of-science defect resulted from this (verified above) — it is a file-organization deviation, not a reporting-integrity defect.
