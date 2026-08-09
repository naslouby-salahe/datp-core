# Inventory (final snapshot)

## TODO/FIXME/XXX

**0** markers in `src/datp_core` and `tests`.

## Shared types introduced / extended during remediation

### core/identifiers.py (selected)
- DecisionRationale, AnalysisReasonText
- FigureLabel, FigureTitle, ClaimWording
- MessageEndpoint, CommunicationGroupIdentity
- TrafficRateReference, TrafficRateProvenanceText, TrafficRateLocatorText
- RegimeLabel, StageExecutionEvidence, UtcInstantText
- ArtifactDirectoryPathText, AnalysisMarkerText, SourceRuleDescription
- ColumnName, ValidationLabel, PhysicalSchemaText, SourceIdentity, …
- Existing: DatasetId, PopulationId, ExperimentId, FederatedThresholdMethod, MetricId, ClientIdentityToken, FamilyIdentity, NonEmptyString, …

### core/numeric.py (selected)
- SeedObservationCount (non-negative seed counts)
- Existing: Seed, ClientCount, SeedCount, MetricValue, Quantile, RowCount, PairedObservationCount, …

### analysis
- AbsorptionRatioUnavailableReason
- TemporalClientUnavailableReason (experiments/temporal)
- ClientEvaluationScoreSeries
- Many reason fields migrated to AnalysisReasonText / DecisionRationale / StrEnums

### presentation
- ThresholdOverlay (method + ThresholdValue)
- TableTitle, EvidenceText (presentation/tables)
- client_id: ClientIdentityToken | None

### data
- ModelInputExclusionReason StrEnum
- PopulationOutcomeLabel used at calibration boundaries without .value leak

## Dead code removed
- src/datp_core/experiments/training_stress/absorption.py (duplicate of analysis)
- src/datp_core/experiments/training_stress/fedprox.py (1-line unused stub)
- src/datp_core/experiments/applicability/ (empty package with TODO-only __init__)

## Test directory names
`tests/unit/{pipeline,learning,thresholding,calibration,preprocessing,evaluation}` remain as **folder names only**; imports target canonical packages. Not renames in this pass (no production impact; architecture tests already guard deleted package roots).

## Judgment calls retained
- CapabilityStatement.evidence/reason stay free-form `str` with non-empty validation (scientific prose documentation)
- Markdown render helpers return `str` at true presentation boundary
- `.value` retained only for filesystem paths, JSON/polars column names, checksum materialization, and similar external boundaries
