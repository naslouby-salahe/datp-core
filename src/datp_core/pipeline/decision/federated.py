"""Federated threshold publication and fixed-score evaluation."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.artifacts.repositories.publication import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.domain.enums import EvidenceRole, PublicationStatus
from datp_core.domain.values.checksums import Checksum
from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.operational.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.federated.contracts import (
    CalibrationSizeAblationCell,
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationRequest,
    ThresholdEstimationStageInput,
)
from datp_core.evaluation.federated.execution import prepare_federated_evaluation
from datp_core.evaluation.federated.publication import (
    FederatedEvaluationAssetName,
    federated_evaluation_is_reusable,
    load_reused_federated_evaluation,
    rebase_federated_evaluation,
    write_federated_evaluation,
)
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.models import ClientMetricResult, PopulationMetricResult
from datp_core.analysis.operational.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.temporal import TemporalDeploymentProvenance
from datp_core.thresholds.dispatch import ThresholdConstructionResult


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorRequest:
    score_manifest: FederatedScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: EvaluationCohortManifest
    fixed_score_evidence: FixedScoreEvidence
    comparison_fixed_score_evidence: FixedScoreEvidence | None
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
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def evaluate_federated_detector(request: EvaluateFederatedDetectorRequest) -> EvaluateFederatedDetectorResult:
    prepared = prepare_federated_evaluation(
        FederatedEvaluationRequest(
            score_manifest=request.score_manifest,
            threshold_result=request.threshold_result,
            cohort=request.cohort,
            fixed_score_evidence=request.fixed_score_evidence,
            comparison_fixed_score_evidence=request.comparison_fixed_score_evidence,
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
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_federated_evaluation,
                validator=federated_evaluation_is_reusable,
                loader=load_reused_federated_evaluation,
                rebaser=rebase_federated_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedEvaluationAssetName.COMPLETE,
        )
    )
    artifacts: FederatedEvaluationArtifacts = publication.value
    return EvaluateFederatedDetectorResult(
        publication_status=publication.status,
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
        complete_digest=publication.complete_digest,
    )
