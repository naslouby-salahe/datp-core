from pathlib import Path

import pytest
import torch
from tests.unit.learning.centralized.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    LEARNING_RATE,
    SEED,
    TRAINING_PROTOCOL,
    benign_frame,
    feature_protocol,
    fitted_state,
    require_cuda,
    run_miniature_training,
    training_coordinate,
)

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.domain.values.identifiers import OutcomeLabel, OutcomeLabelSequence
from datp_core.domain.values.paths import ClientPathToken
from datp_core.learning.centralized.training import (
    CentralizedTrainingRequest,
    build_centralized_autoencoder,
    load_centralized_model_tensors,
    reject_attack_rows_in_centralized_training,
    reject_federated_preprocessing_for_training,
    train_centralized_autoencoder,
)
from datp_core.preprocessing.models import FederatedFittedPreprocessingState


def test_rejects_federated_preprocessing_state(tmp_path: Path) -> None:
    state = FederatedFittedPreprocessingState(
        protocol=feature_protocol(),
        client_identity=ClientPathToken("device_a"),
        estimator_path=tmp_path / "state.skops",
        estimator_checksum=Checksum("c" * 64),
        fit_row_count=RowCount(10),
    )
    with pytest.raises(LeakageError, match="federated preprocessing"):
        reject_federated_preprocessing_for_training(state)


def test_rejects_attack_rows_in_training() -> None:
    with pytest.raises(LeakageError, match="attack-labelled"):
        reject_attack_rows_in_centralized_training(
            OutcomeLabelSequence(
                (OutcomeLabel(PopulationOutcomeLabel.BENIGN.value), OutcomeLabel(PopulationOutcomeLabel.ATTACK.value))
            ),
            PopulationOutcomeLabel.BENIGN,
        )


def test_deterministic_cuda_training_and_safetensors_reload(tmp_path: Path) -> None:
    require_cuda()
    first_execution = run_miniature_training(tmp_path / "run_a")
    second_execution = run_miniature_training(tmp_path / "run_b")
    first = first_execution.result
    second = second_execution.result
    assert first_execution.candidate_snapshots
    assert second_execution.candidate_snapshots
    assert first.device_name
    assert first.batch_size_used == BATCH_SIZE
    assert first.final_epoch == CHECKPOINT.maximum_round
    assert first.model_tensor_path.is_file()
    left = load_centralized_model_tensors(first.model_tensor_path, AUTOENCODER)
    right = load_centralized_model_tensors(second.model_tensor_path, AUTOENCODER)
    for left_tensor, right_tensor in zip(left.state_dict().values(), right.state_dict().values(), strict=True):
        assert torch.equal(left_tensor, right_tensor)
    assert [item.mean_training_loss.value for item in first.epoch_losses] == [
        item.mean_training_loss.value for item in second.epoch_losses
    ]


def test_training_rejects_undersized_batch(tmp_path: Path) -> None:
    require_cuda()
    state = fitted_state(tmp_path / "state.skops")
    with pytest.raises(ScientificContractError, match="full declared batch"):
        train_centralized_autoencoder(
            CentralizedTrainingRequest(
                coordinate=training_coordinate(),
                training_features=benign_frame(RowCount(8), seed=Seed(0)),
                feature_names=FEATURE_NAMES,
                preprocessing_state=state,
                split_manifest_checksum=Checksum("d" * 64),
                output_directory=tmp_path / "out",
                training_seed=SEED,
                autoencoder=AUTOENCODER,
                training_protocol=TRAINING_PROTOCOL,
                checkpoint_protocol=CHECKPOINT,
                learning_rate=LEARNING_RATE,
                batch_size=BATCH_SIZE,
                benign_label=PopulationOutcomeLabel.BENIGN,
            )
        )


def test_autoencoder_round_trip_shape() -> None:
    require_cuda()
    model = build_centralized_autoencoder(AUTOENCODER).to("cuda")
    features = torch.randn(5, 4, device="cuda")
    assert model(features).shape == features.shape
