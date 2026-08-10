from dataclasses import dataclass
from pathlib import Path

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.federated import (
    CalibrationSizeAblationCell,
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    FederatedEvaluationRequest,
    ThresholdEstimationStageInput,
)
from datp_core.analysis.metrics.federated_execution import prepare_federated_evaluation
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.models import ClientMetricResult, PopulationMetricResult
from datp_core.analysis.operational.communication import CommunicationMessageDiagnostic
from datp_core.analysis.operational.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.repositories.evaluations import write_federated_evaluation
from datp_core.core.identifiers import EvidenceRole
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.thresholds.dispatch import ThresholdConstructionResult


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorRequest:
    score_manifest: FederatedScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    evidence_role: EvidenceRole
    conformal_coverage_inputs: tuple[ConformalCoverageStageInput, ...]
    threshold_estimation_inputs: tuple[ThresholdEstimationStageInput, ...]
    communication_messages: tuple[CommunicationMessageDiagnostic, ...]
    traffic_rate_evidence: ValidatedTrafficRateEvidence | None
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_threshold_provenance: TemporalDeploymentProvenance | None = None
    execution_identity: ExternalTemporalExecutionIdentity | None = None
    calibration_size_ablation: tuple[CalibrationSizeAblationCell, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorResult:
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics


def evaluate_federated_detector(request: EvaluateFederatedDetectorRequest) -> EvaluateFederatedDetectorResult:
    if request.output_directory.exists() and not request.overwrite:
        raise FileExistsError(f"evaluation output already exists: {request.output_directory}")
    prepared = prepare_federated_evaluation(
        FederatedEvaluationRequest(
            score_manifest=request.score_manifest,
            threshold_result=request.threshold_result,
            cohort=request.cohort,
            fixed_score_evidence=request.fixed_score_evidence,
            evidence_role=request.evidence_role,
            conformal_coverage_inputs=request.conformal_coverage_inputs,
            threshold_estimation_inputs=request.threshold_estimation_inputs,
            communication_messages=request.communication_messages,
            traffic_rate_evidence=request.traffic_rate_evidence,
            temporal_provenance=request.temporal_provenance,
            temporal_threshold_provenance=request.temporal_threshold_provenance,
            execution_identity=request.execution_identity,
            calibration_size_ablation=request.calibration_size_ablation,
        )
    )
    artifacts = write_federated_evaluation(prepared, request.output_directory)
    return EvaluateFederatedDetectorResult(
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
    )
