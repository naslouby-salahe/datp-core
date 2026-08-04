"""Stage: compose and publish one federated threshold cell."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_file
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.common import (
    FederatedThresholdAssetName,
    FederatedThresholdPublicationRequest,
    federated_threshold_is_reusable,
    load_reused_federated_threshold,
    rebase_federated_threshold,
    threshold_result_checksum,
    write_federated_threshold,
)
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.models import ThresholdConstructionResult


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        FederatedThresholdPublicationRequest(
            request=self.request,
            temporal_provenance=self.temporal_provenance,
            temporal_score_manifest=self.temporal_score_manifest,
        )


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_FEDERATED_THRESHOLDS
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


def construct_federated_thresholds_stage(
    stage_request: ConstructFederatedThresholdsRequest,
) -> ConstructFederatedThresholdsResult:
    publication_request = FederatedThresholdPublicationRequest(
        request=stage_request.request,
        temporal_provenance=stage_request.temporal_provenance,
        temporal_score_manifest=stage_request.temporal_score_manifest,
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=stage_request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_threshold,
                validator=federated_threshold_is_reusable,
                loader=load_reused_federated_threshold,
                rebaser=rebase_federated_threshold,
            ),
            overwrite=stage_request.overwrite,
            complete_marker=FederatedThresholdAssetName.COMPLETE,
        )
    )
    return ConstructFederatedThresholdsResult(
        result=publication.value,
        publication_status=publication.status,
        complete_digest=checksum_file(
            stage_request.output_directory / FederatedThresholdAssetName.COMPLETE
        ),
        temporal_provenance=stage_request.temporal_provenance,
    )
