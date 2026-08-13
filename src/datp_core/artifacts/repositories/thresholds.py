from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.identifiers import FileContentText
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.dispatch import (
    ThresholdConstructionRequest,
    ThresholdConstructionResult,
    dispatch_federated_threshold,
)

type FederatedScoreArtifactManifest = ScoreArtifactManifest[FederatedTrainingCoordinate, ClientIdentity]


class FederatedThresholdAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedThresholdConstructionRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: FederatedScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        if self.output_directory.is_symlink():
            raise ValueError("threshold output directory cannot be a symbolic link")
        if self.output_directory.exists() and not self.output_directory.is_dir():
            raise ValueError("threshold output destination must be a directory")
        if (self.temporal_provenance is None) != (self.temporal_score_manifest is None):
            raise ValueError("temporal threshold construction requires both provenance and score manifest")
        if self.temporal_provenance is not None and self.temporal_score_manifest is not None:
            self.temporal_provenance.validate_score_manifest(self.temporal_score_manifest)
            if self.request.coordinate != self.temporal_score_manifest.coordinate:
                raise ValueError("temporal threshold request and score manifest must share one coordinate")


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedThresholdConstructionResult:
    result: ThresholdConstructionResult
    temporal_provenance: TemporalDeploymentProvenance | None


def construct_and_publish_federated_thresholds(
    request: FederatedThresholdConstructionRequest,
) -> FederatedThresholdConstructionResult:
    if request.output_directory.exists() and not request.overwrite:
        raise FileExistsError(f"threshold output already exists: {request.output_directory}")
    result = dispatch_federated_threshold(request.request)
    write_text_atomically(
        request.output_directory / FederatedThresholdAssetName.RESULT,
        FileContentText(canonical_json_text(result)),
    )
    if request.temporal_provenance is not None:
        write_text_atomically(
            request.output_directory / FederatedThresholdAssetName.TEMPORAL_PROVENANCE,
            FileContentText(canonical_json_text(request.temporal_provenance)),
        )
    return FederatedThresholdConstructionResult(
        result=result,
        temporal_provenance=request.temporal_provenance,
    )
