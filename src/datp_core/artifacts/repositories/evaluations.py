"""Persist and reload typed threshold-evaluation results."""

from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from pydantic import TypeAdapter

from datp_core.analysis.metrics.contracts import ThresholdEvaluationResult
from datp_core.artifacts.provenance import Checksum, canonical_checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.detector.scoring.contracts import FixedScoreInvariant


class EvaluationAsset(StrEnum):
    RESULT = "evaluation.json"
    MANIFEST = "manifest.json"
    COMPLETE = "COMPLETE"


class EvaluationManifest(StrictModel):
    fixed_score_identity: Checksum
    evaluation_checksum: Checksum


class EvaluationPublication(StrictModel):
    directory: Path
    manifest: EvaluationManifest
    complete_digest: Checksum


def publish_evaluation(
    result: ThresholdEvaluationResult,
    *,
    fixed_scores: FixedScoreInvariant,
    directory: Path,
    overwrite: bool,
) -> EvaluationPublication:
    if directory.exists() and not overwrite:
        return load_evaluation_publication(directory)
    if directory.exists():
        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)
    result_path = directory / EvaluationAsset.RESULT.value
    result_path.write_text(canonical_json_text(result), encoding="utf-8")
    manifest = EvaluationManifest(
        fixed_score_identity=canonical_checksum(fixed_scores),
        evaluation_checksum=canonical_checksum(result),
    )
    manifest_path = directory / EvaluationAsset.MANIFEST.value
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")
    digest = canonical_checksum(
        (
            (EvaluationAsset.RESULT.value, checksum_file(result_path)),
            (EvaluationAsset.MANIFEST.value, checksum_file(manifest_path)),
        )
    )
    (directory / EvaluationAsset.COMPLETE.value).write_text(digest.value, encoding="utf-8")
    return EvaluationPublication(directory=directory, manifest=manifest, complete_digest=digest)


def load_evaluation_publication(directory: Path) -> EvaluationPublication:
    result_path = directory / EvaluationAsset.RESULT.value
    manifest_path = directory / EvaluationAsset.MANIFEST.value
    marker = directory / EvaluationAsset.COMPLETE.value
    if not result_path.is_file() or not manifest_path.is_file() or not marker.is_file():
        raise ArtifactIntegrityError(f"evaluation publication is incomplete: {directory}")
    manifest = EvaluationManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    digest = canonical_checksum(
        (
            (EvaluationAsset.RESULT.value, checksum_file(result_path)),
            (EvaluationAsset.MANIFEST.value, checksum_file(manifest_path)),
        )
    )
    if marker.read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError(f"evaluation completion digest mismatch: {directory}")
    return EvaluationPublication(directory=directory, manifest=manifest, complete_digest=digest)


def reload_evaluation(publication: EvaluationPublication) -> ThresholdEvaluationResult:
    result = TypeAdapter(ThresholdEvaluationResult).validate_json(
        (publication.directory / EvaluationAsset.RESULT.value).read_text(encoding="utf-8")
    )
    if canonical_checksum(result) != publication.manifest.evaluation_checksum:
        raise ArtifactIntegrityError("reloaded evaluation semantic checksum mismatch")
    return result
