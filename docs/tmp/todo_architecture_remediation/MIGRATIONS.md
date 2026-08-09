# Migrations Log

## M1 — DatpCoreError.message/reason (batch 1, prior session)
See historical entry: message=ErrorMessage required; reason=Enum|None only.

## M2 — Data foundation value objects (prior session)
ColumnName, PhysicalSchemaText, SourceIdentity, ChronologyGroupIdentity, ValidationSourceContext, CanonicalizationContractName; Checksum/Path on domain dataclasses; JSON boundary fields stay str.

## M3 — Incomplete identity migrations (this session)
- eligibility/centralized: PopulationOutcomeLabel without .value; convert parquet labels to enum
- execution context / training_stress: family_by_client already typed — stop double ClientIdentityToken/FamilyIdentity wrap
- external run: ExternalBenignStatisticsClient.client_id = ClientIdentityToken
- presentation figures: client_id ClientIdentityToken | None

## M4 — Analysis package typing (this session)
- scientific_decision.rationale → DecisionRationale
- absorption.population → PopulationId; ratio reasons → enum; seed counts → SeedObservationCount
- preparation/descriptive/temporal/operational/metrics/inference: reason/unavailable fields → AnalysisReasonText or domain enums; metric property returns → MetricValue not float
- scipy adapter: typed linear regression values

## M5 — Experiments package (this session)
- PlanReason for execute_declared_experiment_seed reason parameters
- EstimationSummaryLoad for summary + missing_count
- AnalysisMarkerText, AnalysisReasonText for report markers/details
- AnchorLayoutDirectory replaces ResearchDirectory imports from app.layout
- Deleted dead absorption/fedprox/applicability modules
- Temporal unavailable reasons → AnalysisReasonText; exclusion enums

## M6 — Presentation package (this session)
- FigureLabel/FigureTitle/ClaimWording
- ThresholdOverlay typed
- TableTitle/EvidenceText
- score_role → ScoreRole where applicable

## M7 — Data residual (this session)
- ModelInputExclusionReason StrEnum
- Removed incorrect polars struct.field("value") on string client_id columns in construction._client_partition_counts

## M8 — App
- app/anchor.py imports PlanReason from app.planning
