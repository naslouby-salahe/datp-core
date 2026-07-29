from pathlib import Path

from tests.unit.centralized_reference.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    LEARNING_RATE,
    SEED,
    TRAINING_PROTOCOL,
    benign_frame,
    fitted_state,
    mixed_evaluation_frame,
    require_cuda,
    training_coordinate,
)

from datp_core.centralized_reference.checkpointing import retain_centralized_checkpoint_candidates
from datp_core.centralized_reference.evaluation import evaluate_centralized_reference
from datp_core.centralized_reference.scoring import CentralizedScoringRequest, score_centralized_reference
from datp_core.centralized_reference.thresholding import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    construct_pooled_benign_quantile,
)
from datp_core.centralized_reference.training import CentralizedTrainingRequest, train_centralized_autoencoder
from datp_core.domain.values import Checksum


def test_end_to_end_centralized_pipeline_without_federated_artifacts(tmp_path: Path) -> None:
    require_cuda()
    coordinate = training_coordinate()
    state = fitted_state(tmp_path / "state.skops")
    training = train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=coordinate,
            training_features=benign_frame(64, seed=0),
            feature_names=FEATURE_NAMES,
            preprocessing_state=state,
            split_manifest_checksum=Checksum("f" * 64),
            output_directory=tmp_path / "model",
            training_seed=SEED,
            autoencoder=AUTOENCODER,
            training_protocol=TRAINING_PROTOCOL,
            checkpoint_protocol=CHECKPOINT,
            learning_rate=LEARNING_RATE,
            batch_size=BATCH_SIZE,
        )
    )
    candidates = retain_centralized_checkpoint_candidates(training, AUTOENCODER)
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=coordinate,
            checkpoint=candidates[0],
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(48, seed=30),
            evaluation_features=mixed_evaluation_frame(40, seed=31),
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_checksum=state.estimator_checksum,
        )
    )
    threshold = construct_pooled_benign_quantile(
        coordinate=coordinate,
        calibration_scores=scoring.calibration_scores,
        protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    )
    evaluation = evaluate_centralized_reference(
        coordinate=coordinate,
        evaluation_scores=scoring.evaluation_scores,
        threshold_result=threshold,
    )
    assert training.model_tensor_path.is_file()
    assert candidates[0].tensor_path.is_file()
    assert scoring.calibration_scores.path.is_file()
    assert scoring.evaluation_scores.path.is_file()
    assert evaluation.evaluation_row_count == 40
    assert evaluation.is_confirmatory_ladder_member is False
