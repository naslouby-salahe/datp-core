from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CheckpointStatus, PartitionRole, SerializationFormat, SplitProtocolId
from datp_core.core.numeric import FeatureCount, RoundNumber, RowCount, Seed
from datp_core.detector.scoring.contracts import (
    FixedScoreInvariant,
    ScoreArtifactManifest,
    ScoreGenerationResult,
    ScoreRecord,
)

_DEFAULT_SEED = Seed(0)


def _record(role: PartitionRole, client_id: str, path: Path, *, seed: Seed = _DEFAULT_SEED) -> ScoreRecord:
    return ScoreRecord(
        coordinate=fedavg_coordinate(seed),
        scored_client=client_identity(client_id),
        partition_role=role,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=path,
        checksum=Checksum("b" * 64),
        row_count=RowCount(4),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
    )


def _manifest(
    tmp_path: Path,
    *,
    scored_split_protocol: SplitProtocolId | None = None,
    calibration_records: tuple[ScoreRecord, ...] | None = None,
    evaluation_records: tuple[ScoreRecord, ...] | None = None,
    future_recalibration_records: tuple[ScoreRecord, ...] = (),
) -> ScoreArtifactManifest:
    coordinate = fedavg_coordinate(Seed(0))
    return ScoreArtifactManifest(
        coordinate=coordinate,
        scored_split_protocol=(coordinate.split_protocol if scored_split_protocol is None else scored_split_protocol),
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        preprocessing_state_set_checksum=Checksum("c" * 64),
        split_manifest_checksum=Checksum("d" * 64),
        calibration_records=(_record(PartitionRole.CALIBRATION, "client_a", tmp_path / "cal.parquet"),)
        if calibration_records is None
        else calibration_records,
        evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),)
        if evaluation_records is None
        else evaluation_records,
        future_recalibration_records=future_recalibration_records,
    )


def test_score_record_rejects_non_calibration_evaluation_partition_role(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="post-training partitions"):
        _record(PartitionRole.TRAIN, "client_a", tmp_path / "train.parquet")


def test_score_record_rejects_non_parquet_serialization(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="Parquet"):
        ScoreRecord(
            coordinate=fedavg_coordinate(Seed(0)),
            scored_client=client_identity("client_a"),
            partition_role=PartitionRole.CALIBRATION,
            checkpoint_round=RoundNumber(2),
            checkpoint_checksum=Checksum("a" * 64),
            path=tmp_path / "cal.json",
            checksum=Checksum("b" * 64),
            row_count=RowCount(4),
            feature_count=FeatureCount(4),
            serialization_format=SerializationFormat.PYDANTIC_JSON,
        )


def test_manifest_rejects_missing_calibration_records(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="calibration and evaluation records"):
        _manifest(tmp_path, calibration_records=())


def test_manifest_rejects_duplicate_scored_client_records(tmp_path: Path) -> None:
    duplicate = _record(PartitionRole.CALIBRATION, "client_a", tmp_path / "cal.parquet")
    with pytest.raises(ScientificContractError, match="duplicate scored-client"):
        _manifest(tmp_path, calibration_records=(duplicate, duplicate))


def test_manifest_rejects_record_from_a_different_coordinate(tmp_path: Path) -> None:
    mismatched_record = _record(
        PartitionRole.CALIBRATION,
        "client_a",
        tmp_path / "cal.parquet",
        seed=Seed(1),
    )
    with pytest.raises(ScientificContractError, match="manifest coordinate"):
        _manifest(tmp_path, calibration_records=(mismatched_record,))


def test_manifest_rejects_record_stored_under_wrong_role(tmp_path: Path) -> None:
    wrong_role_record = _record(PartitionRole.EVALUATION, "client_a", tmp_path / "cal.parquet")
    with pytest.raises(ScientificContractError, match="does not match expected collection role"):
        _manifest(tmp_path, calibration_records=(wrong_role_record,))


def test_manifest_rejects_inconsistent_feature_count(tmp_path: Path) -> None:
    mismatched = ScoreRecord(
        coordinate=fedavg_coordinate(Seed(0)),
        scored_client=client_identity("client_a"),
        partition_role=PartitionRole.CALIBRATION,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=tmp_path / "cal.parquet",
        checksum=Checksum("b" * 64),
        row_count=RowCount(4),
        feature_count=FeatureCount(7),
        serialization_format=SerializationFormat.PARQUET,
    )
    with pytest.raises(ScientificContractError, match="same feature count"):
        _manifest(tmp_path, calibration_records=(mismatched,))


def test_manifest_rejects_missing_client_in_evaluation(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="same client inventory"):
        _manifest(
            tmp_path,
            evaluation_records=(_record(PartitionRole.EVALUATION, "client_b", tmp_path / "eval.parquet"),),
        )


def test_non_temporal_manifest_rejects_future_recalibration_records(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="future-recalibration inventory"):
        _manifest(
            tmp_path,
            future_recalibration_records=(
                _record(
                    PartitionRole.FUTURE_RECALIBRATION,
                    "client_a",
                    tmp_path / "future.parquet",
                ),
            ),
        )


def test_temporal_manifest_requires_future_recalibration_records(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="future-recalibration inventory"):
        _manifest(
            tmp_path,
            scored_split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        )


def test_fixed_score_invariant_is_derived_deterministically_from_the_manifest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    first = FixedScoreInvariant.from_manifest(manifest)
    second = FixedScoreInvariant.from_manifest(manifest)
    assert first == second
    assert first.model_checksum == manifest.checkpoint_checksum


def test_score_generation_result_derives_its_invariant_from_the_manifest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    result = ScoreGenerationResult(manifest=manifest)

    assert result.invariant == FixedScoreInvariant.from_manifest(manifest)
