from datp_core.application.ports.thresholding import ConstructCentralizedThresholdRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedThresholdIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.splitting import SplitIdentity
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import CentralizedClientCalibrationScoreArtifact, ScoreSampleCount
from datp_core.domain.runtime.admissibility import BatchSize
from datp_core.domain.thresholding.policies import B0PooledThresholdSpec, ThresholdPercentile
from datp_core.infrastructure.thresholding.policies import B0PooledThresholdConstructor


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _artifact(*, client_id: ClientId, character: str) -> CentralizedClientCalibrationScoreArtifact:
    return CentralizedClientCalibrationScoreArtifact(
        client_id=client_id,
        calibration_split_identity=SplitIdentity(value=_fingerprint("a")),
        split_manifest_hash="b" * 64,
        scoring_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("c")),
        centralized_checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("d")),
        centralized_checkpoint_content_hash="e" * 64,
        scoring_batch_size=BatchSize(value=4),
        sample_count=ScoreSampleCount(value=1),
        schema_version=ArtifactSchemaVersion(value="v1"),
        content_hash=character * 64,
        row_order_checksum="order",
        artifact_ref=ArtifactRef(
            artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
            artifact_type=ArtifactType.CALIBRATION_SCORE_SET,
            content_hash=character * 64,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        ),
    )


class _FixedScoreReader:
    def __init__(self, scores_by_content_hash: dict[str, tuple[float, ...]]) -> None:
        self._scores_by_content_hash = scores_by_content_hash

    def read(self, *, artifact: CentralizedClientCalibrationScoreArtifact) -> tuple[float, ...]:
        return self._scores_by_content_hash[artifact.content_hash]


def test_pooled_threshold_constructor_pools_all_client_scores_before_computing_p95() -> None:
    client_a = ClientId(value="client-a")
    client_b = ClientId(value="client-b")
    artifact_a = _artifact(client_id=client_a, character="1")
    artifact_b = _artifact(client_id=client_b, character="2")
    reader = _FixedScoreReader(
        {
            artifact_a.content_hash: tuple(float(value) for value in range(1, 51)),
            artifact_b.content_hash: tuple(float(value) for value in range(51, 101)),
        }
    )
    constructor = B0PooledThresholdConstructor(reader=reader)
    request = ConstructCentralizedThresholdRequest(
        pooled_calibration_scores=(artifact_a, artifact_b),
        spec=B0PooledThresholdSpec(percentile=ThresholdPercentile(value="0.95")),
        centralized_calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("f")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("0")),
    )

    result = constructor.construct(request)

    assert result.assignment.tau.value == 95.0
