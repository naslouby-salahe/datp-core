"""Stage: compose held-out federated evaluation publication."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.domain.enums import EvidenceRole, PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum
from datp_core.evaluation.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.controls import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, PopulationMetricResult
from datp_core.evaluation.population import (
    ConformalCoverageStageInput,
    EvaluationDiagnostics,
    FederatedEvaluationArtifacts,
    FederatedEvaluationAssetName,
    FederatedEvaluationInputs,
    FederatedEvaluationPublication,
    FederatedEvaluationRequest,
    ThresholdEstimationStageInput,
    build_federated_evaluation_inputs,
    federated_evaluation_is_reusable,
    load_reused_federated_evaluation,
    prepare_federated_evaluation,
    rebase_federated_evaluation,
    write_federated_evaluation,
)
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.models import ThresholdConstructionResult


@dataclass(frozen=True, slots=True)
class EvaluateFederatedRequest:
    score_manifest: ScoreArtifactManifest
    threshold_result: ThresholdConstructionResult
    cohort: object
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


@dataclass(frozen=True, slots=True)
class FederatedEvaluationResult:
    stage: ClassVar[StageOperationId] = StageOperationId.EVALUATE_FEDERATED
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def evaluate_federated_stage(request: EvaluateFederatedRequest) -> FederatedEvaluationResult:
    evaluation_request = FederatedEvaluationRequest(
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
    prepared = prepare_federated_evaluation(evaluation_request)
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
    return FederatedEvaluationResult(
        publication_status=publication.status,
        clients=artifacts.clients,
        population=artifacts.population,
        diagnostics=artifacts.diagnostics,
        complete_digest=prepared.digest,
    )


__all__ = (
    "ConformalCoverageStageInput",
    "EvaluateFederatedRequest",
    "FederatedEvaluationAssetName",
    "FederatedEvaluationInputs",
    "FederatedEvaluationResult",
    "ThresholdEstimationStageInput",
    "build_federated_evaluation_inputs",
    "evaluate_federated_stage",
)
