from pathlib import Path

import numpy as np
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

from datp_core.domain.enums import CentralizedThresholdMethod, FederatedThresholdMethod, ScoreFrameColumn
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Quantile, RowCount, Seed, ThresholdValue
from datp_core.pipeline.checkpoints.service import retain_centralized_checkpoint_candidates
from datp_core.pipeline.decision.centralized import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    construct_pooled_benign_quantile,
    exact_pooled_quantile,
    reject_attack_rows_in_benign_calibration,
    reject_centralized_threshold_in_federated_dispatch,
    reject_federated_scores_for_centralized_threshold,
    reject_local_quantile_mean_as_centralized,
)
from datp_core.pipeline.scoring.centralized import load_score_frame, score_centralized_reference
from datp_core.pipeline.scoring.models import CentralizedScoringRequest
from datp_core.populations.models import PopulationOutcomeLabel


def test_pooled_benign_quantile_matches_declared_linear_quantile(tmp_path: Path) -> None:
    require_cuda()
    execution = run_miniature_training(tmp_path / "train")
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, AUTOENCODER)
    scoring = score_centralized_reference(
        CentralizedScoringRequest(
            coordinate=training_coordinate(),
            checkpoint=candidates[0],
            autoencoder=AUTOENCODER,
            feature_names=FEATURE_NAMES,
            calibration_features=benign_frame(RowCount(48), seed=Seed(7)),
            evaluation_features=mixed_evaluation_frame(RowCount(32), seed=Seed(8)),
            batch_size=BATCH_SIZE,
            output_directory=tmp_path / "scores",
            preprocessing_state_checksum=training.preprocessing_state_checksum,
        )
    )
    result = construct_pooled_benign_quantile(
        coordinate=training_coordinate(),
        calibration_scores=scoring.calibration_scores,
        protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    )
    assert result.method is CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE
    scores = np.asarray(
        load_score_frame(scoring.calibration_scores)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list(),
        dtype=float,
    )
    assert result.threshold.value == float(
        np.quantile(scores, CENTRALIZED_POOLED_QUANTILE_PROTOCOL.quantile.value, method="linear")
    )


def test_exact_pooled_quantile_unit() -> None:
    quantile = Quantile(0.5)
    scores = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=float)
    threshold = exact_pooled_quantile(scores, quantile)
    assert isinstance(threshold, ThresholdValue)
    assert threshold.value == float(np.quantile(scores, quantile.value, method="linear"))


def test_rejects_attack_rows_in_calibration() -> None:
    from datp_core.domain.values import OutcomeLabel, OutcomeLabelSequence

    with pytest.raises(LeakageError, match="attack-labelled"):
        reject_attack_rows_in_benign_calibration(
            OutcomeLabelSequence(
                (OutcomeLabel(PopulationOutcomeLabel.BENIGN.value), OutcomeLabel(PopulationOutcomeLabel.ATTACK.value))
            ),
            PopulationOutcomeLabel.BENIGN,
        )


def test_rejects_federated_scores_and_local_mean() -> None:
    with pytest.raises(LeakageError, match="federated score"):
        reject_federated_scores_for_centralized_threshold("fedavg_scores", FederatedThresholdMethod.SHARED_THRESHOLD)
    with pytest.raises(LeakageError, match="arithmetic mean of local quantiles"):
        reject_local_quantile_mean_as_centralized((0.1, 0.2, 0.3))
    with pytest.raises(LeakageError, match="federated threshold dispatch"):
        reject_centralized_threshold_in_federated_dispatch(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
