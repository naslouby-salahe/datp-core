"""Federated threshold publication and fixed-score evaluation."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import EvidenceRole, PublicationStatus
from datp_core.domain.values.checksums import Checksum
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.communication import CommunicationMessageDiagnostic
from datp_core.evaluation.federated.contracts import (
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
from datp_core.evaluation.fixed_score.contracts import FixedScoreEvidence
from datp_core.evaluation.models import ClientMetricResult, PopulationMetricResult
from datp_core.evaluation.traffic_rates import ValidatedTrafficRateEvidence
from datp_core.pipeline.publication.service import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.temporal import TemporalDeploymentProvenance
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.models import ThresholdConstructionResult
from datp_core.thresholding.publication import (
    FederatedThresholdAssetName,
    FederatedThresholdPublicationRequest,
    federated_threshold_is_reusable,
    load_reused_federated_threshold,
    rebase_federated_threshold,
    write_federated_threshold,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: FederatedScoreArtifactManifest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsResult:
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


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


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluateFederatedDetectorResult:
    publication_status: PublicationStatus
    clients: tuple[ClientMetricResult, ...]
    population: PopulationMetricResult
    diagnostics: EvaluationDiagnostics
    complete_digest: Checksum


def construct_federated_thresholds(
    request: ConstructFederatedThresholdsRequest,
) -> ConstructFederatedThresholdsResult:
    publication_request = FederatedThresholdPublicationRequest(
        request=request.request,
        temporal_provenance=request.temporal_provenance,
        temporal_score_manifest=request.temporal_score_manifest,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_threshold,
                validator=federated_threshold_is_reusable,
                loader=load_reused_federated_threshold,
                rebaser=rebase_federated_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructFederatedThresholdsResult(
        result=publication.value,
        publication_status=publication.status,
        complete_digest=publication.complete_digest,
        temporal_provenance=request.temporal_provenance,
    )


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
