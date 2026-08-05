# Phase 14 — Reporting, Claims, and Publication Exports

## Authority

`docs/Journal_Extension_Master_Roadmap.md` is the scientific authority. Reporting may present only validated typed analysis and evaluation artifacts. It must preserve evidence role, availability, provenance, scientific decision, anchor status, and suppression status without recalculating or rescuing results.

## Final ownership

- `src/datp_core/reporting/tables.py`: typed table specifications and explicit unavailable cells.
- `src/datp_core/reporting/figures.py`: source-authorized typed figure specifications.
- `src/datp_core/reporting/validation.py`: machine-enforced claim boundaries.
- `src/datp_core/reporting/export.py`: validated report-bundle export.
- `src/datp_core/pipeline/publish_report.py`: pipeline composition and publication entry point.
- `src/datp_core/pipeline/publication/`: atomic persistence, inventory, completion, checksum, and reload validation.

CLI and Dagster are thin adapters. They do not construct scientific claims, tables, figures, or publication files independently.

## Reporting contract

Reports consume validated typed artifacts bound to deterministic experiment coordinates. Tables and figures preserve provenance and evidence roles. Unavailable, undefined, infeasible, suppressed, null, reversed, unstable, and boundary outcomes remain explicit and reportable; they are never converted to zero, omitted as though executed evidence, or relabelled as positive support.

Confirmatory, supportive, mechanism, threshold-variant, external-validation, training-stress-test, applicability-boundary, temporal-boundary, exploratory, and operational evidence remain distinct. No secondary analysis, alternative quantile, shrinkage setting, stress test, or sensitivity analysis may rescue a failed confirmatory endpoint.

## Claim control

Claim validation blocks or suppresses:

- journal claims when the anchor gate is blocked;
- confirmatory language without a supported confirmatory BCa decision;
- external, supportive, stress-test, exploratory, or boundary evidence presented as confirmatory;
- suppressed or infeasible experiments presented as executed evidence;
- attack-sensitive Edge claims where attack assignment is unavailable;
- CIC physical-device or device-aware wording;
- one-shot recalibration described as continuous adaptation, online learning, or a general concept-drift solution;
- data locality described as formal privacy;
- payload estimates described as measured deployment communication;
- alert burden without valid traffic-rate evidence;
- undefined or unavailable metrics rendered as numeric zero;
- AUROC presented as a threshold-policy benefit rather than detector-quality control.

Null, opposite, unstable, infeasible, and applicability-boundary outcomes remain publishable with their exact status and provenance.

## Authorized outputs

Typed table and figure identities cover only source-authorized analyses, including protocol and population summaries, anchor comparison, confirmatory paired-seed evidence, per-client natural-device metrics, threshold and quantile sensitivities, controlled heterogeneity, calibration-size and shrinkage behavior, conformal coverage, federated benign-statistics diagnostics, external Edge benign-equity evidence, CIC file-client boundaries, FedProx and genuine Ditto stress tests, temporal one-shot recalibration, and unavailable-outcome summaries.

Grouped-threshold output remains unavailable unless an outcome-independent audited assignment exists. Alert-burden output remains unavailable without valid rate evidence.

Tables export to CSV and Parquet. Consolidated machine-readable results use Parquet. Claim status, warnings, suppression, and validation use typed JSON. Figures use PDF and an already-supported vector format. Calculations remain full precision; presentation rounding occurs only at export.

## Scientific invariants

- The fixed detector, preprocessing state, population, split, checkpoint, score set, labels, eligibility, and metric implementation remain identical inside threshold-scope comparisons.
- Calibration remains benign-only.
- Centralized reference remains independently trained and is never relabelled as a shared-threshold federated result.
- AUROC remains a detector-quality control.
- Edge remains benign operating-point external evidence where attack assignment is unavailable.
- CIC remains a file-client applicability boundary without verified physical-device identity or chronology.
- Message sizes are estimates, not deployment measurements.
- Data locality is not a formal privacy guarantee.

## Verification

Meaningful tests cover supported confirmatory claims, inconclusive and opposite decisions, blocked anchor, suppressed experiments, external null boundaries, unavailable grouped thresholds, undefined CV, missing traffic-rate evidence, Edge attack-claim rejection, CIC device-language rejection, one-shot temporal wording, privacy and deployment suppression, unavailable values not rendered as zero, negative results retained, provenance preservation, and export reload equivalence.

## Completion record

Phase 14 is complete only when every displayed value is traceable to a validated typed artifact and coordinate, claim status is machine-enforced, all unavailable and negative states remain explicit, publication export cannot alter scientific meaning, and relevant unit, integration, architecture, and scientific tests pass.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, hosted CI, and external quality gates are outside this pull request's completion procedure.
