"""Construct and atomically publish one federated threshold cell."""

from dataclasses import dataclass
from enum import StrEnum
from json import dumps
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.artifacts.serialization import to_json_compatible
from datp_core.artifacts.store import publish_atomically
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, checksum_text
from datp_core.scoring.models import ScoreArtifactManifest
from datp_core.thresholding.dispatch import ThresholdConstructionRequest, dispatch_federated_threshold
from datp_core.thresholding.models import ThresholdConstructionResult


class ConstructFederatedThresholdsAssetName(StrEnum):
    RESULT = "threshold_result.json"
    TEMPORAL_PROVENANCE = "temporal_threshold_provenance.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsRequest:
    request: ThresholdConstructionRequest
    output_directory: Path
    overwrite: bool
    temporal_provenance: TemporalDeploymentProvenance | None = None
    temporal_score_manifest: ScoreArtifactManifest | None = None

    def __post_init__(self) -> None:
        if (self.temporal_provenance is None) != (self.temporal_score_manifest is None):
            raise ValueError("temporal threshold construction requires both provenance and score manifest")


@dataclass(frozen=True, slots=True)
class ConstructFederatedThresholdsResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_FEDERATED_THRESHOLDS
    result: ThresholdConstructionResult
    publication_status: PublicationStatus
    complete_digest: Checksum
    temporal_provenance: TemporalDeploymentProvenance | None


def _json_payload(value: object) -> str:
    return dumps(to_json_compatible(value), indent=2, sort_keys=True) + "\n"


def threshold_result_checksum(result: ThresholdConstructionResult) -> Checksum:
    return checksum_text(_json_payload(result))


def _stage_checksum(
    result: ThresholdConstructionResult,
    temporal_provenance: TemporalDeploymentProvenance | None,
) -> Checksum:
    return checksum_text(
        _json_payload(
            {
                "result": result,
                "temporal_provenance": temporal_provenance,
            }
        )
    )


def construct_federated_thresholds_stage(
    stage_request: ConstructFederatedThresholdsRequest,
) -> ConstructFederatedThresholdsResult:
    _validate_temporal_request(stage_request)

    def construct() -> ThresholdConstructionResult:
        return dispatch_federated_threshold(stage_request.request)

    def write(temporary: Path) -> ThresholdConstructionResult:
        result = construct()
        (temporary / ConstructFederatedThresholdsAssetName.RESULT).write_text(
            _json_payload(result), encoding="utf-8"
        )
        if stage_request.temporal_provenance is not None:
            (temporary / ConstructFederatedThresholdsAssetName.TEMPORAL_PROVENANCE).write_text(
                _json_payload(stage_request.temporal_provenance),
                encoding="utf-8",
            )
        digest = _stage_checksum(result, stage_request.temporal_provenance)
        (temporary / ConstructFederatedThresholdsAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return result

    outcome = publish_atomically(
        target=stage_request.output_directory,
        overwrite=stage_request.overwrite,
        is_reusable=lambda directory: _is_reusable(directory, stage_request),
        write=write,
        reusable_value=lambda _directory: construct(),
        remove_target=rmtree,
    )
    return ConstructFederatedThresholdsResult(
        result=outcome.value,
        publication_status=outcome.status,
        complete_digest=outcome.complete_digest,
        temporal_provenance=stage_request.temporal_provenance,
    )


def _is_reusable(directory: Path, stage_request: ConstructFederatedThresholdsRequest) -> bool:
    complete = directory / ConstructFederatedThresholdsAssetName.COMPLETE
    document = directory / ConstructFederatedThresholdsAssetName.RESULT
    if not (complete.is_file() and document.is_file()):
        return False
    provenance = stage_request.temporal_provenance
    provenance_document = directory / ConstructFederatedThresholdsAssetName.TEMPORAL_PROVENANCE
    if (provenance is None and provenance_document.exists()) or (
        provenance is not None and not provenance_document.is_file()
    ):
        return False
    expected = _stage_checksum(dispatch_federated_threshold(stage_request.request), provenance)
    return complete.read_text(encoding="utf-8").strip() == expected.value


def _validate_temporal_request(stage_request: ConstructFederatedThresholdsRequest) -> None:
    if stage_request.temporal_provenance is not None:
        if stage_request.temporal_score_manifest is None:
            raise AssertionError("request invariant was checked in __post_init__")
        stage_request.temporal_provenance.validate_score_manifest(stage_request.temporal_score_manifest)
