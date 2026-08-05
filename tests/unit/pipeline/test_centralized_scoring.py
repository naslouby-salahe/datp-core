from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from tests.unit.learning.centralized.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEATURE_NAMES,
    benign_frame,
    mixed_evaluation_frame,
    require_cuda,
    run_miniature_training,
    training_coordinate,
)

from datp_core.domain.enums import (
    CheckpointStatus,
    PartitionRole,
    ScoreFrameColumn,
    SerializationFormat,
    TrainingModelId,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Checksum, FeatureCount, MetricValue, RoundNumber, RowCount, Seed, checksum_file
from datp_core.pipeline.checkpoints.records import CentralizedCheckpointCandidate
from datp_core.pipeline.checkpoints.service import reject_federated_checkpoint, retain_centralized_checkpoint_candidates
from datp_core.pipeline.generate_scores import (
    CentralizedScoreAssetName,
    CentralizedScoringRequest,
    CentralizedScoringResult,
    PooledScoreArtifact,
    centralized_scoring_is_reusable,
    load_score_frame,
    score_artifact_set_checksum,
    score_centralized_reference,
)
from datp_core.pipeline.scoring.frame_contract import score_frame


def test_deterministic_scoring_and_reload(tmp_path: Path) -> None:
    require_cuda()
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)
    request = CentralizedScoringRequest(
        coordinate=training_coordinate(),
        checkpoint=candidates[0],
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        calibration_features=benign_frame(RowCount(32), seed=Seed(3)),
        evaluation_features=mixed_evaluation_frame(RowCount(32), seed=Seed(4)),
        batch_size=BATCH_SIZE,
        output_directory=tmp_path / "scores",
        preprocessing_state_checksum=training.preprocessing_state_checksum,
    )
    first = score_centralized_reference(request)
    second = score_centralized_reference(request)
    assert load_score_frame(first.calibration_scores).equals(load_score_frame(second.calibration_scores))
    assert first.calibration_scores.checksum == second.calibration_scores.checksum


def test_rejects_federated_checkpoint_for_scoring() -> None:
    with pytest.raises(LeakageError, match="federated checkpoint"):
        reject_federated_checkpoint(TrainingModelId.FEDAVG_AUTOENCODER)


def test_score_polarity_higher_is_more_anomalous(tmp_path: Path) -> None:
    require_cuda()
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)
    result = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=training_coordinate(),
            checkpoint=candidates[0],
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(32), seed=Seed(5)),
            evaluation_features=mixed_evaluation_frame(RowCount(32), seed=Seed(6)),
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_checksum=training.preprocessing_state_checksum,
        )
    )
    frame = load_score_frame(result.evaluation_scores)
    benign = frame.filter(frame[ScoreFrameColumn.OUTCOME_LABEL.value] == "benign")[
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value
    ].to_numpy()
    attack = frame.filter(frame[ScoreFrameColumn.OUTCOME_LABEL.value] == "attack")[
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value
    ].to_numpy()
    assert float(np.mean(attack)) > float(np.mean(benign))


def test_reuse_rejects_changed_calibration_row_identity(tmp_path: Path) -> None:
    coordinate = training_coordinate()
    preprocessing_checksum = Checksum("a" * 64)
    split_checksum = Checksum("b" * 64)
    checkpoint_path = tmp_path / "checkpoint.safetensors"
    checkpoint_path.write_text("checkpoint", encoding="utf-8")
    checkpoint = CentralizedCheckpointCandidate(
        coordinate=coordinate,
        round_number=RoundNumber(1),
        tensor_path=checkpoint_path,
        tensor_checksum=checksum_file(checkpoint_path),
        mean_training_loss=MetricValue(0.1),
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_checksum=preprocessing_checksum,
        split_manifest_checksum=split_checksum,
        training_seed=Seed(1),
        autoencoder_widths=tuple(AUTOENCODER.widths),
    )
    calibration = benign_frame(RowCount(4), seed=Seed(7))
    evaluation = mixed_evaluation_frame(RowCount(4), seed=Seed(8))
    directory = tmp_path / "scores"
    directory.mkdir()
    calibration_artifact = _persist_score_artifact(
        coordinate,
        checkpoint,
        calibration,
        PartitionRole.CALIBRATION,
        directory / CentralizedScoreAssetName.CALIBRATION_SCORES,
    )
    evaluation_artifact = _persist_score_artifact(
        coordinate,
        checkpoint,
        evaluation,
        PartitionRole.EVALUATION,
        directory / CentralizedScoreAssetName.EVALUATION_SCORES,
    )
    request = CentralizedScoringRequest(
        coordinate=coordinate,
        checkpoint=checkpoint,
        autoencoder=AUTOENCODER,
        feature_names=FEATURE_NAMES,
        calibration_features=calibration,
        evaluation_features=evaluation,
        batch_size=BATCH_SIZE,
        output_directory=directory,
        preprocessing_state_checksum=preprocessing_checksum,
    )
    result = CentralizedScoringResult(
        calibration_scores=calibration_artifact,
        evaluation_scores=evaluation_artifact,
        model_tensor_checksum=checkpoint.tensor_checksum,
        preprocessing_state_checksum=preprocessing_checksum,
    )
    (directory / CentralizedScoreAssetName.COMPLETE).write_text(
        score_artifact_set_checksum(request, result).value,
        encoding="utf-8",
    )
    assert centralized_scoring_is_reusable(request, directory)
    changed_calibration = calibration.with_columns(
        pl.Series(
            ScoreFrameColumn.STABLE_ROW_ID.value,
            tuple(
                "changed-row" if index == 0 else str(value)
                for index, value in enumerate(calibration[ScoreFrameColumn.STABLE_ROW_ID.value].to_list())
            ),
            dtype=pl.Utf8,
        )
    )
    assert not centralized_scoring_is_reusable(replace(request, calibration_features=changed_calibration), directory)


def _persist_score_artifact(
    coordinate,
    checkpoint: CentralizedCheckpointCandidate,
    source: pl.DataFrame,
    partition_role: PartitionRole,
    path: Path,
) -> PooledScoreArtifact:
    score_frame(
        tuple(str(value) for value in source[ScoreFrameColumn.STABLE_ROW_ID.value].to_list()),
        tuple(str(value) for value in source[ScoreFrameColumn.OUTCOME_LABEL.value].to_list()),
        np.zeros(source.height, dtype=np.float64),
    ).write_parquet(path)
    return PooledScoreArtifact(
        coordinate=coordinate,
        partition_role=partition_role,
        checkpoint_round=checkpoint.round_number,
        checkpoint_checksum=checkpoint.tensor_checksum,
        path=path,
        checksum=checksum_file(path),
        row_count=RowCount(source.height),
        feature_count=FeatureCount(len(FEATURE_NAMES)),
        serialization_format=SerializationFormat.PARQUET,
    )
