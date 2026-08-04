from pathlib import Path

import numpy as np
import polars as pl
import pytest

from datp_core.domain.enums import (
    PartitionRole,
    ScoreFrameColumn,
    SerializationFormat,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    Checksum,
    FeatureCount,
    FeatureName,
    FeatureNameSequence,
    RoundNumber,
    RowCount,
    checksum_file,
)
from datp_core.pipeline.scoring.frame_contract import (
    SCORE_FRAME_COLUMNS,
    SCORE_FRAME_DTYPES,
    score_frame,
    validate_persisted_score_frame,
    validate_score_input_frame,
)
from datp_core.pipeline.scoring.models import ScoreArtifact

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
    with pytest.raises(LeakageError, match="attack-labelled"):
        validate_score_input_frame(
            _input_frame(("benign", "attack")),
            PartitionRole.CALIBRATION,
            FEATURE_NAMES,
        )


def test_shared_input_contract_rejects_duplicate_row_identity() -> None:
    with pytest.raises(ScientificContractError, match="unique"):
        validate_score_input_frame(
            _input_frame(
                ("benign", "benign"),
                row_ids=("row", "row"),
            ),
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
        ("row-0", "row-1"),
        ("benign", "attack"),
        np.asarray((0.1, 0.9), dtype=np.float64),
    )
    path = tmp_path / "scores.parquet"
    frame.write_parquet(path)
    reloaded = validate_persisted_score_frame(
        path,
        checksum_file(path),
        RowCount(frame.height),
    )
    assert tuple(reloaded.columns) == SCORE_FRAME_COLUMNS
    assert tuple(reloaded.schema[column] for column in SCORE_FRAME_COLUMNS) == SCORE_FRAME_DTYPES


def test_shared_score_artifact_rejects_training_partition(
    tmp_path: Path,
) -> None:
    with pytest.raises(ScientificContractError, match="post-training"):
        ScoreArtifact(
            coordinate="detector",
            partition_role=PartitionRole.TRAIN,
            checkpoint_round=RoundNumber(1),
            checkpoint_checksum=Checksum("a" * 64),
            path=tmp_path / "scores.parquet",
            checksum=Checksum("b" * 64),
            row_count=RowCount(1),
            feature_count=FeatureCount(2),
            serialization_format=SerializationFormat.PARQUET,
        )
