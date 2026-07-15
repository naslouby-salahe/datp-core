from dataclasses import dataclass

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CheckpointIdentity,
    DatasetSourceIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    PartitionIdentity,
    SplitIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CalibrationScoreArtifactId,
    StageFingerprint,
)
from datp_core.domain.evaluation.operating_points import EligibleClientSet
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    CalibrationScoringLineage,
    ClientCalibrationScoreArtifact,
    ClientCalibrationScoreMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ScoreLineageContext,
    ScoreSampleCount,
)
from datp_core.domain.learning.training import PrecisionMode
from datp_core.domain.runtime.admissibility import BatchSize


def calibration_scores_and_eligible_clients() -> tuple[CalibrationScoreArtifactSet, EligibleClientSet]:
    client = ClientId(value="client-a")
    roster = ClientRoster(client_ids=(client,))
    calibration_identity = CalibrationScoringIdentity(value=_fingerprint("d"))
    checkpoint_identity = CheckpointIdentity(value=_fingerprint("e"))
    preprocessor_identity = FittedPreprocessorIdentity(value=_fingerprint("f"))
    schema_identity = FeatureSchemaIdentity(value=_fingerprint("0"))
    score_reference = _artifact_ref(character="1", artifact_type=ArtifactType.CALIBRATION_SCORE_SET)
    score_set = CalibrationScoreArtifactSet(
        artifact_id=CalibrationScoreArtifactId(value="artifact-" + "2" * 64),
        lineage=CalibrationScoringLineage(
            scoring_identity=calibration_identity,
            context=score_lineage_context(
                ScoreLineageContextRequest(
                    roster=roster,
                    split_identity=SplitIdentity(value=_fingerprint("4")),
                    checkpoint_identity=checkpoint_identity,
                    checkpoint_content_hash="3" * 64,
                    preprocessor_identity=preprocessor_identity,
                    schema_identity=schema_identity,
                    row_order_checksum="calibration-order",
                )
            ),
        ),
        per_client=ClientCalibrationScoreMap(
            values=ClientMap(
                roster=roster,
                entries=(
                    ClientMapEntry(
                        client_id=client,
                        value=ClientCalibrationScoreArtifact(
                            client_id=client,
                            calibration_split_identity=SplitIdentity(value=_fingerprint("4")),
                            split_manifest_hash="5" * 64,
                            scoring_identity=calibration_identity,
                            scientific_checkpoint_identity=checkpoint_identity,
                            scientific_checkpoint_content_hash="3" * 64,
                            fitted_preprocessor_identity=preprocessor_identity,
                            feature_schema_identity=schema_identity,
                            sample_count=ScoreSampleCount(value=100),
                            schema_version=ArtifactSchemaVersion(value="v1"),
                            content_hash="1" * 64,
                            row_order_checksum="calibration-order",
                            artifact_ref=score_reference,
                        ),
                    ),
                ),
            )
        ),
    )
    return score_set, EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=_fingerprint("6"),
        eligible_clients=(client,),
        ineligible_reasons=(),
        identity=_fingerprint("7"),
    )


def calibration_scores_for_clients(
    score_values: tuple[tuple[float, ...], ...],
) -> tuple[CalibrationScoreArtifactSet, EligibleClientSet]:
    if len(score_values) < 1:
        raise ValueError("synthetic calibration score fixture requires at least one client")
    clients = tuple(ClientId(value=f"client-{index:02d}") for index in range(len(score_values)))
    roster = ClientRoster(client_ids=clients)
    calibration_identity = CalibrationScoringIdentity(value=_fingerprint("d"))
    checkpoint_identity = CheckpointIdentity(value=_fingerprint("e"))
    preprocessor_identity = FittedPreprocessorIdentity(value=_fingerprint("f"))
    schema_identity = FeatureSchemaIdentity(value=_fingerprint("0"))
    entries = tuple(
        ClientMapEntry(
            client_id=client,
            value=ClientCalibrationScoreArtifact(
                client_id=client,
                calibration_split_identity=SplitIdentity(value=_fingerprint("4")),
                split_manifest_hash="5" * 64,
                scoring_identity=calibration_identity,
                scientific_checkpoint_identity=checkpoint_identity,
                scientific_checkpoint_content_hash="3" * 64,
                fitted_preprocessor_identity=preprocessor_identity,
                feature_schema_identity=schema_identity,
                sample_count=ScoreSampleCount(value=len(values)),
                schema_version=ArtifactSchemaVersion(value="v1"),
                content_hash=f"{index:x}" * 64,
                row_order_checksum=f"calibration-order-{index}",
                artifact_ref=_artifact_ref(character=f"{index:x}", artifact_type=ArtifactType.CALIBRATION_SCORE_SET),
            ),
        )
        for index, (client, values) in enumerate(zip(clients, score_values, strict=True))
    )
    score_set = CalibrationScoreArtifactSet(
        artifact_id=CalibrationScoreArtifactId(value="artifact-" + "2" * 64),
        lineage=CalibrationScoringLineage(
            scoring_identity=calibration_identity,
            context=score_lineage_context(
                ScoreLineageContextRequest(
                    roster=roster,
                    split_identity=SplitIdentity(value=_fingerprint("4")),
                    checkpoint_identity=checkpoint_identity,
                    checkpoint_content_hash="3" * 64,
                    preprocessor_identity=preprocessor_identity,
                    schema_identity=schema_identity,
                    row_order_checksum="calibration-order",
                )
            ),
        ),
        per_client=ClientCalibrationScoreMap(values=ClientMap(roster=roster, entries=entries)),
    )
    return score_set, EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=_fingerprint("6"),
        eligible_clients=clients,
        ineligible_reasons=(),
        identity=_fingerprint("7"),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScoreLineageContextRequest:
    roster: ClientRoster
    split_identity: SplitIdentity
    checkpoint_identity: CheckpointIdentity
    checkpoint_content_hash: str
    preprocessor_identity: FittedPreprocessorIdentity
    schema_identity: FeatureSchemaIdentity
    row_order_checksum: str


def score_lineage_context(request: ScoreLineageContextRequest) -> ScoreLineageContext:
    return ScoreLineageContext(
        dataset_source_identity=DatasetSourceIdentity(value=_fingerprint("a")),
        partition_identity=PartitionIdentity(value=_fingerprint("b")),
        split_identity=request.split_identity,
        scientific_checkpoint_identity=request.checkpoint_identity,
        scientific_checkpoint_content_hash=request.checkpoint_content_hash,
        fitted_preprocessor_identity=request.preprocessor_identity,
        feature_schema_identity=request.schema_identity,
        training_identity=TrainingIdentity(value=_fingerprint("c")),
        score_schema_version=ArtifactSchemaVersion(value="v1"),
        roster=request.roster,
        row_order_checksum=request.row_order_checksum,
        precision=PrecisionMode.FP32,
        scoring_batch_size=BatchSize(value=8),
    )


def _artifact_ref(*, character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)
