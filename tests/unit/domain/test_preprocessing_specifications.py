from dataclasses import fields

import pytest

from datp_core.domain.artifacts.lineage import PartitionIdentity, SplitIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.preprocessing import (
    FittedPreprocessorResult,
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
    validate_train_fit_split,
)
from datp_core.domain.data.splitting import BenignCalibrationSplitSpec, TestSplitSpec, TrainingSplitSpec
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.runtime.admissibility import ChunkRowCount


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _training_split() -> TrainingSplitSpec:
    return TrainingSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint("a")),
        partition_identity=PartitionIdentity(value=_fingerprint("b")),
    )


def test_preprocessing_specification_owns_exactly_the_three_typed_chunk_sizes() -> None:
    chunking = PreprocessingChunkSpec(
        source_scan_batch_rows=ChunkRowCount(value=1),
        preprocessing_chunk_rows=ChunkRowCount(value=2),
        parquet_write_batch_rows=ChunkRowCount(value=3),
    )
    specification = PreprocessingSpec(
        strategy=NormalizationStrategy.STANDARD,
        scope=NormalizationScope.GLOBAL_TRAIN,
        fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
        chunking=chunking,
    )

    assert specification.chunking is chunking
    assert {entry.name for entry in fields(PreprocessingChunkSpec)} == {
        "source_scan_batch_rows",
        "preprocessing_chunk_rows",
        "parquet_write_batch_rows",
    }


def test_fitted_preprocessor_result_has_no_test_or_processed_split_surface() -> None:
    field_names = {entry.name for entry in fields(FittedPreprocessorResult)}

    assert field_names == {"artifact", "identity", "training_row_order_checksum"}
    assert all("test" not in name and "processed" not in name for name in field_names)


def test_preprocessing_fit_authorization_rejects_calibration_and_test_splits() -> None:
    training = _training_split()
    partition = training.partition_identity
    calibration = BenignCalibrationSplitSpec(
        split_identity=SplitIdentity(value=_fingerprint("c")), partition_identity=partition
    )
    test = TestSplitSpec(split_identity=SplitIdentity(value=_fingerprint("d")), partition_identity=partition)

    assert validate_train_fit_split(split=training) is training
    for split in (calibration, test):
        with pytest.raises(DomainValidationError):
            validate_train_fit_split(split=split)
