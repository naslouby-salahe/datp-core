from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.enums import PartitionRole, SerializationFormat
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, FeatureCount, RoundNumber, RowCount, Seed
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest, ScoreGenerationResult, ScoreRecord


def _record(role: PartitionRole, client_id: str, path: Path) -> ScoreRecord:
    return ScoreRecord(
        coordinate=fedavg_coordinate(Seed(0)),
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


def _manifest(tmp_path: Path) -> ScoreArtifactManifest:
    return ScoreArtifactManifest(
        coordinate=fedavg_coordinate(Seed(0)),
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        preprocessing_state_set_checksum=Checksum("c" * 64),
        split_manifest_checksum=Checksum("d" * 64),
        calibration_records=(_record(PartitionRole.CALIBRATION, "client_a", tmp_path / "cal.parquet"),),
        evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),),
        higher_score_means_greater_anomaly=True,
    )


def test_score_record_rejects_non_calibration_evaluation_partition_role(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="calibration and evaluation"):
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
        ScoreArtifactManifest(
            coordinate=fedavg_coordinate(Seed(0)),
            checkpoint_round=RoundNumber(2),
            checkpoint_checksum=Checksum("a" * 64),
            preprocessing_state_set_checksum=Checksum("c" * 64),
            split_manifest_checksum=Checksum("d" * 64),
            calibration_records=(),
            evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),),
            higher_score_means_greater_anomaly=True,
        )


def test_manifest_rejects_false_anomaly_polarity(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="anomaly-polarity"):
        ScoreArtifactManifest(
            coordinate=fedavg_coordinate(Seed(0)),
            checkpoint_round=RoundNumber(2),
            checkpoint_checksum=Checksum("a" * 64),
            preprocessing_state_set_checksum=Checksum("c" * 64),
            split_manifest_checksum=Checksum("d" * 64),
            calibration_records=(_record(PartitionRole.CALIBRATION, "client_a", tmp_path / "cal.parquet"),),
            evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),),
            higher_score_means_greater_anomaly=False,
        )


def test_manifest_rejects_duplicate_scored_client_records(tmp_path: Path) -> None:
    duplicate = _record(PartitionRole.CALIBRATION, "client_a", tmp_path / "cal.parquet")
    with pytest.raises(ScientificContractError, match="duplicate scored-client"):
        ScoreArtifactManifest(
            coordinate=fedavg_coordinate(Seed(0)),
            checkpoint_round=RoundNumber(2),
            checkpoint_checksum=Checksum("a" * 64),
            preprocessing_state_set_checksum=Checksum("c" * 64),
            split_manifest_checksum=Checksum("d" * 64),
            calibration_records=(duplicate, duplicate),
            evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),),
            higher_score_means_greater_anomaly=True,
        )


def test_manifest_rejects_record_from_a_different_coordinate(tmp_path: Path) -> None:
    mismatched_record = ScoreRecord(
        coordinate=fedavg_coordinate(Seed(1)),
        scored_client=client_identity("client_a"),
        partition_role=PartitionRole.CALIBRATION,
        checkpoint_round=RoundNumber(2),
        checkpoint_checksum=Checksum("a" * 64),
        path=tmp_path / "cal.parquet",
        checksum=Checksum("b" * 64),
        row_count=RowCount(4),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
    )
    with pytest.raises(ScientificContractError, match="manifest coordinate"):
        ScoreArtifactManifest(
            coordinate=fedavg_coordinate(Seed(0)),
            checkpoint_round=RoundNumber(2),
            checkpoint_checksum=Checksum("a" * 64),
            preprocessing_state_set_checksum=Checksum("c" * 64),
            split_manifest_checksum=Checksum("d" * 64),
            calibration_records=(mismatched_record,),
            evaluation_records=(_record(PartitionRole.EVALUATION, "client_a", tmp_path / "eval.parquet"),),
            higher_score_means_greater_anomaly=True,
        )


def test_fixed_score_invariant_is_derived_deterministically_from_the_manifest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    first = FixedScoreInvariant.from_manifest(manifest)
    second = FixedScoreInvariant.from_manifest(manifest)
    assert first == second
    assert first.model_checksum == manifest.checkpoint_checksum


def test_score_generation_result_rejects_a_foreign_invariant(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    foreign_invariant = FixedScoreInvariant(
        model_checksum=Checksum("f" * 64),
        calibration_score_set_checksum=Checksum("f" * 64),
        evaluation_score_set_checksum=Checksum("f" * 64),
        preprocessing_state_set_checksum=Checksum("f" * 64),
        split_manifest_checksum=Checksum("f" * 64),
    )
    with pytest.raises(ScientificContractError, match="derived from its own manifest"):
        ScoreGenerationResult(manifest=manifest, invariant=foreign_invariant)
