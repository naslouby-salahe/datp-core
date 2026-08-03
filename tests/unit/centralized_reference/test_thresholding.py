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

from datp_core.centralized_reference.checkpointing import retain_centralized_checkpoint_candidates
from datp_core.centralized_reference.scoring import CentralizedScoringRequest, score_centralized_reference
from datp_core.centralized_reference.thresholding import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    FederatedScoreMarker,
    construct_pooled_benign_quantile,
    exact_pooled_quantile,
    reject_attack_rows_in_benign_calibration,
    reject_centralized_threshold_in_federated_dispatch,
    reject_federated_scores_for_centralized_threshold,
    reject_local_quantile_mean_as_centralized,
)
from datp_core.domain.enums import CentralizedThresholdMethod, FederatedThresholdMethod
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import Quantile, RowCount, Seed, ThresholdValue
from datp_core.populations.models import PopulationOutcomeLabel


def test_pooled_benign_quantile_matches_numpy_linear(tmp_path: Path) -> None:
    require_cuda()
    training = run_miniature_training(tmp_path / "train")
    candidates = retain_centralized_checkpoint_candidates(training, AUTOENCODER)
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
    assert result.quantile == CENTRALIZED_POOLED_QUANTILE_PROTOCOL.quantile
    assert result.calibration_score_count == 48
    from datp_core.centralized_reference.scoring import load_score_frame

    scores = np.asarray(
        load_score_frame(scoring.calibration_scores).get_column("reconstruction_error").to_list(),
        dtype=float,
    )
    expected = float(np.quantile(scores, 0.95, method="linear"))
    assert result.threshold.value == expected


def test_exact_pooled_quantile_unit() -> None:
    scores = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=float)
    threshold = exact_pooled_quantile(scores, Quantile(0.5))
    assert isinstance(threshold, ThresholdValue)
    assert threshold.value == float(np.quantile(scores, 0.5, method="linear"))


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
        reject_federated_scores_for_centralized_threshold(
            FederatedScoreMarker("fedavg_scores", FederatedThresholdMethod.SHARED_THRESHOLD)
        )
    with pytest.raises(LeakageError, match="arithmetic mean of local quantiles"):
        reject_local_quantile_mean_as_centralized((0.1, 0.2, 0.3))
    with pytest.raises(LeakageError, match="federated threshold dispatch"):
        reject_centralized_threshold_in_federated_dispatch(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
