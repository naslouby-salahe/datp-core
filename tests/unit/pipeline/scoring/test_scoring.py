from pathlib import Path

import numpy as np
import polars as pl
import pytest

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    FeatureName,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SerializationFormat,
    SplitProtocolId,
    StableRowId,
    StableRowIdSequence,
    TrainingModelId,
)
from datp_core.core.numeric import FeatureCount, RoundNumber, RowCount, Seed
from datp_core.detector.scoring.contracts import ScoreArtifact
from datp_core.detector.scoring.frames import (
    SCORE_FRAME_COLUMNS,
    SCORE_FRAME_DTYPES,
    score_frame,
    validate_persisted_score_frame,
    validate_score_input_frame,
)
from datp_core.detector.training.contracts import FederatedTrainingCoordinate

FEATURE_NAMES = FeatureNameSequence((FeatureName("f0"), FeatureName("f1")))


def _input_frame(
    labels: tuple[str, ...],
    row_ids: tuple[str, ...] | None = None,
) -> pl.DataFrame:
    resolved_row_ids = row_ids or tuple(f"row-{index}" for index in range(len(labels)))
    return pl.DataFrame(
        (
            pl.Series(
                ScoreFrameColumn.STABLE_ROW_ID.value,
                resolved_row_ids,
                dtype=pl.Utf8,
            ),
            pl.Series(
                ScoreFrameColumn.OUTCOME_LABEL.value,
                labels,
                dtype=pl.Utf8,
            ),
            pl.Series(
                "f0",
                tuple(float(index) for index in range(len(labels))),
                dtype=pl.Float64,
            ),
            pl.Series(
                "f1",
                tuple(float(index + 1) for index in range(len(labels))),
                dtype=pl.Float64,
            ),
        )
    )


def test_shared_input_contract_accepts_benign_calibration() -> None:
    validate_score_input_frame(
        _input_frame(("benign", "benign")),
        PartitionRole.CALIBRATION,
        FEATURE_NAMES,
    )


def test_shared_input_contract_rejects_attack_calibration() -> None:
    frame = _input_frame(("benign", "attack"))
    with pytest.raises(LeakageError, match="attack-labelled"):
        validate_score_input_frame(
            frame,
            PartitionRole.CALIBRATION,
            FEATURE_NAMES,
        )


def test_shared_input_contract_rejects_duplicate_row_identity() -> None:
    frame = _input_frame(
        ("benign", "benign"),
        row_ids=("row", "row"),
    )
    with pytest.raises(ScientificContractError, match="unique"):
        validate_score_input_frame(
            frame,
            PartitionRole.CALIBRATION,
            FEATURE_NAMES,
        )


def test_shared_input_contract_rejects_null_feature_value() -> None:
    frame = _input_frame(("benign", "benign")).with_columns(pl.Series("f0", (0.0, None), dtype=pl.Float64))
    with pytest.raises(ScientificContractError, match="null values"):
        validate_score_input_frame(
            frame,
            PartitionRole.CALIBRATION,
            FEATURE_NAMES,
        )


def test_score_frame_persists_exact_schema(tmp_path: Path) -> None:
    frame = score_frame(
        StableRowIdSequence((StableRowId("row-0"), StableRowId("row-1"))),
        OutcomeLabelSequence((OutcomeLabel("benign"), OutcomeLabel("attack"))),
        np.asarray((0.1, 0.9), dtype=np.float64),
    )
    path = tmp_path / "scores.parquet"
    frame.write_parquet(path)
    reloaded = validate_persisted_score_frame(
        path,
        Checksum.from_file(path),
        RowCount(frame.height),
    )
    assert tuple(reloaded.columns) == SCORE_FRAME_COLUMNS
    assert tuple(reloaded.schema[column] for column in SCORE_FRAME_COLUMNS) == SCORE_FRAME_DTYPES


def test_shared_score_artifact_rejects_training_partition(
    tmp_path: Path,
) -> None:
    coordinate = FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    checkpoint_round = RoundNumber(1)
    checkpoint_checksum = Checksum("a" * 64)
    checksum = Checksum("b" * 64)
    row_count = RowCount(1)
    feature_count = FeatureCount(2)
    with pytest.raises(ScientificContractError, match="post-training"):
        ScoreArtifact(
            coordinate=coordinate,
            partition_role=PartitionRole.TRAIN,
            checkpoint_round=checkpoint_round,
            checkpoint_checksum=checkpoint_checksum,
            path=tmp_path / "scores.parquet",
            checksum=checksum,
            row_count=row_count,
            feature_count=feature_count,
            serialization_format=SerializationFormat.PARQUET,
        )
