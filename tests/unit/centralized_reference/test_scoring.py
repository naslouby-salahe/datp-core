from pathlib import Path

import numpy as np
import pytest
from tests.unit.centralized_reference.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEATURE_NAMES,
    benign_frame,
    mixed_evaluation_frame,
    require_cuda,
    run_miniature_training,
    training_coordinate,
)

from datp_core.centralized_reference.checkpointing import (
    reject_federated_checkpoint,
    retain_centralized_checkpoint_candidates,
)
from datp_core.centralized_reference.scoring import (
    CentralizedScoringRequest,
    load_score_frame,
    score_centralized_reference,
)
from datp_core.domain.enums import ScoreFrameColumn, TrainingModelId
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import RowCount, Seed


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
    left = load_score_frame(first.calibration_scores)
    right = load_score_frame(second.calibration_scores)
    assert left.equals(right)
    assert first.calibration_scores.checksum == second.calibration_scores.checksum
    assert first.calibration_scores.row_count.value == 32
    assert first.evaluation_scores.row_count.value == 32


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
    label_column = ScoreFrameColumn.OUTCOME_LABEL.value
    score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
    benign = frame.filter(frame[label_column] == "benign")[score_column].to_numpy()
    attack = frame.filter(frame[label_column] == "attack")[score_column].to_numpy()
    assert float(np.mean(attack)) > float(np.mean(benign))
