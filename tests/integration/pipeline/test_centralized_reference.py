from pathlib import Path

from tests.unit.learning.centralized.helpers import (
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

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.learning.centralized.training import CentralizedTrainingRequest, train_centralized_autoencoder
from datp_core.pipeline.checkpoints.service import retain_centralized_checkpoint_candidates
from datp_core.pipeline.decision.centralized import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    construct_pooled_benign_quantile,
    evaluate_centralized_reference,
)
from datp_core.pipeline.scoring.centralized import score_centralized_reference
from datp_core.pipeline.scoring.models import CentralizedScoringRequest


def test_end_to_end_centralized_pipeline_without_federated_artifacts(tmp_path: Path) -> None:
    require_cuda()
    coordinate = training_coordinate()
    state = fitted_state(tmp_path / "state.skops")
    execution = train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=coordinate,
            training_features=benign_frame(RowCount(64), seed=Seed(0)),
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
            benign_label=PopulationOutcomeLabel.BENIGN,
        )
    )
    training = execution.result
    checkpoint = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)[0]
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=coordinate,
            checkpoint=checkpoint,
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(48), seed=Seed(30)),
            evaluation_features=mixed_evaluation_frame(RowCount(40), seed=Seed(31)),
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
    assert checkpoint.tensor_path.is_file()
    assert scoring.calibration_scores.path.is_file()
    assert scoring.evaluation_scores.path.is_file()
    assert evaluation.evaluation_row_count == 40
