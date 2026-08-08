"""Persist canonical threshold assignments and the complete policy result evidence."""

from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.artifacts.provenance import Checksum, canonical_checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.detector.scoring.contracts import FixedScoreInvariant
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.contracts import ThresholdAssignment


class ThresholdAsset(StrEnum):
    MANIFEST = "manifest.json"
    RESULT = "result.json"
    COMPLETE = "COMPLETE"


class ThresholdManifest(StrictModel):
    method: FederatedThresholdMethod
    coordinate: FederatedTrainingCoordinate
    assignments: tuple[ThresholdAssignment, ...]
    fixed_score_identity: Checksum
    result_checksum: Checksum


class ThresholdPublication(StrictModel):
    directory: Path
    manifest: ThresholdManifest
    complete_digest: Checksum


def publish_threshold_result(
    *,
    method: FederatedThresholdMethod,
    coordinate: FederatedTrainingCoordinate,
    assignments: tuple[ThresholdAssignment, ...],
    result: object,
    fixed_scores: FixedScoreInvariant,
    directory: Path,
    overwrite: bool,
) -> ThresholdPublication:
    if directory.exists() and not overwrite:
        return load_threshold_publication(directory)
    if directory.exists():
        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)
    result_text = canonical_json_text(result)
    result_path = directory / ThresholdAsset.RESULT.value
    result_path.write_text(result_text, encoding="utf-8")
    result_checksum = canonical_checksum(result)
    manifest = ThresholdManifest(
        method=method,
        coordinate=coordinate,
        assignments=assignments,
        fixed_score_identity=canonical_checksum(fixed_scores),
        result_checksum=result_checksum,
    )
    manifest_path = directory / ThresholdAsset.MANIFEST.value
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")
    digest = canonical_checksum(
        (
            (ThresholdAsset.MANIFEST.value, checksum_file(manifest_path)),
            (ThresholdAsset.RESULT.value, checksum_file(result_path)),
        )
    )
    (directory / ThresholdAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return ThresholdPublication(directory=directory, manifest=manifest, complete_digest=digest)


def load_threshold_publication(directory: Path) -> ThresholdPublication:
    manifest_path = directory / ThresholdAsset.MANIFEST.value
    result_path = directory / ThresholdAsset.RESULT.value
    marker = directory / ThresholdAsset.COMPLETE.value
    if not manifest_path.is_file() or not result_path.is_file() or not marker.is_file():
        raise ArtifactIntegrityError(f"threshold publication is incomplete: {directory}")
    manifest = ThresholdManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    digest = canonical_checksum(
        (
            (ThresholdAsset.MANIFEST.value, checksum_file(manifest_path)),
            (ThresholdAsset.RESULT.value, checksum_file(result_path)),
        )
    )
    if marker.read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError(f"threshold completion digest mismatch: {directory}")
    return ThresholdPublication(directory=directory, manifest=manifest, complete_digest=digest)
