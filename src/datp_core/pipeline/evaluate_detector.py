"""Federated and centralized held-out detector evaluation."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.centralized_reference.evaluation import CentralizedEvaluationResult
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import PooledThresholdResult
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import EvidenceRole, PublicationStatus
from datp_core.domain.values import Checksum
from datp_core.evaluation.cohorts import EvaluationCohortManifest
from datp_core.evaluation.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.controls import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, PopulationMetricResult
from datp_core.evaluation.operational import (
    CentralizedEvaluationPublicationAsset,
    CentralizedEvaluationPublicationRequest,
    centralized_evaluation_is_reusable,
    load_reused_centralized_evaluation,
    rebase_centralized_evaluation,
    write_centralized_evaluation,
)
from datp_core.evaluation.population import (
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationAssetName,
    FederatedEvaluationRequest,
    ThresholdEstimationStageInput,
    federated_evaluation_is_reusable,
    load_reused_federated_evaluation,
    prepare_federated_evaluation,
    rebase_federated_evaluation,
    write_federated_evaluation,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.common import ThresholdConstructionResult


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    evaluation_scores: PooledScoreArtifact
    threshold: PooledThresholdResult
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateCentralizedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    evaluation: CentralizedEvaluationResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorRequest:
    score_manifest: ScoreArtifactManifest
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


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def evaluate_federated_detector(
    request: EvaluateFederatedDetectorRequest,
) -> EvaluateFederatedDetectorResult:
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
        stage=PipelineStage.EVALUATE_DETECTOR,
        publication_status=publication.status,
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
        complete_digest=publication.complete_digest,
    )


def evaluate_centralized_detector(
    request: EvaluateCentralizedDetectorRequest,
) -> EvaluateCentralizedDetectorResult:
    publication_request = CentralizedEvaluationPublicationRequest(
        coordinate=request.coordinate,
        evaluation_scores=request.evaluation_scores,
        threshold=request.threshold,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_evaluation,
                validator=centralized_evaluation_is_reusable,
                loader=load_reused_centralized_evaluation,
                rebaser=rebase_centralized_evaluation,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedEvaluationPublicationAsset.COMPLETE,
        )
    )
    return EvaluateCentralizedDetectorResult(
        stage=PipelineStage.EVALUATE_DETECTOR,
        publication_status=publication.status,
        evaluation=publication.value,
        complete_digest=publication.complete_digest,
    )
