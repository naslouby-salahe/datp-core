"""Federated and centralized benign-only threshold publication."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.centralized_reference.scoring import PooledScoreArtifact
from datp_core.centralized_reference.thresholding import (
    CentralizedThresholdAssetName,
    CentralizedThresholdPublicationRequest,
    PooledThresholdResult,
    centralized_threshold_is_reusable,
    load_reused_centralized_threshold,
    rebase_centralized_threshold,
    write_centralized_threshold,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.protocols.models import CentralizedQuantileProtocol
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.common import (
    FederatedThresholdAssetName,
    FederatedThresholdPublicationRequest,
    ThresholdConstructionResult,
    federated_threshold_is_reusable,
    load_reused_federated_threshold,
    rebase_federated_threshold,
    write_federated_threshold,
)
from datp_core.thresholding.dispatch import ThresholdConstructionRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdRequest:
    coordinate: CentralizedTrainingCoordinate
    calibration_scores: PooledScoreArtifact
    output_directory: Path
    protocol: CentralizedQuantileProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructCentralizedThresholdResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    threshold: PooledThresholdResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructFederatedThresholdsResult:
    stage: PipelineStage
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


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
        stage=PipelineStage.CONSTRUCT_THRESHOLDS,
        result=publication.value,
        publication_status=publication.status,
        complete_digest=publication.complete_digest,
        temporal_provenance=request.temporal_provenance,
    )


def construct_centralized_threshold(
    request: ConstructCentralizedThresholdRequest,
) -> ConstructCentralizedThresholdResult:
    publication_request = CentralizedThresholdPublicationRequest(
        coordinate=request.coordinate,
        calibration_scores=request.calibration_scores,
        protocol=request.protocol,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_threshold,
                validator=centralized_threshold_is_reusable,
                loader=load_reused_centralized_threshold,
                rebaser=rebase_centralized_threshold,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructCentralizedThresholdResult(
        stage=PipelineStage.CONSTRUCT_THRESHOLDS,
        publication_status=publication.status,
        threshold=publication.value,
        complete_digest=publication.complete_digest,
    )
