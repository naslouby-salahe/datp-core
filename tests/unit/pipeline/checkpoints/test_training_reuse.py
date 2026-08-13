from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    FEDAVG_PROTOCOL,
    LEARNING_RATE,
    POPULATION_CLIENT_COUNT,
    build_all_client_inputs,
    fedavg_coordinate,
    require_cuda,
)

from datp_core.artifacts.serializers.safetensors import save_state_dict_tensors
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.numeric import RoundNumber, Seed
from datp_core.detector.autoencoder import AutoencoderModelState, build_reconstruction_autoencoder
from datp_core.detector.checkpoints import publication as publication_module
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.identities import FederatedHistoryAssetName
from datp_core.detector.checkpoints.publication import load_federated_training
from datp_core.detector.training import federated as federated_module
from datp_core.detector.training.contracts import (
    AutoencoderArchitecture,
    AutoencoderProtocol,
    FederatedClientDataResidency,
)
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.models import TrainingTerminationReason

FAST_PROTOCOL = DiagnosticSnapshotProtocol(diagnostic_rounds=(), maximum_round=RoundNumber(1))


def _request(tmp_path: Path) -> FederatedTrainingRequest:
    return FederatedTrainingRequest(
        coordinate=fedavg_coordinate(Seed(0)),
        clients=build_all_client_inputs(tmp_path),
        population_client_count=POPULATION_CLIENT_COUNT,
        autoencoder=AUTOENCODER,
        training_protocol=FEDAVG_PROTOCOL,
        diagnostic_snapshot_protocol=FAST_PROTOCOL,
        training_seed=Seed(0),
        batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        output_directory=tmp_path / "training",
        client_data_residency=FederatedClientDataResidency.STREAMING,
    )


def test_train_global_federated_reuses_persisted_evidence_across_separate_invocations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_cuda()
    request = _request(tmp_path)

    first = federated_module.train_global_federated(request)
    assert first.termination_reason is TrainingTerminationReason.FIXED_ROUND_BUDGET_COMPLETED

    def _fail_if_retrained(request: FederatedTrainingRequest) -> None:
        pytest.fail("training coordinate already has valid persisted evidence and must not retrain")

    monkeypatch.setattr(federated_module, "run_federated_training", _fail_if_retrained)

    second = federated_module.train_global_federated(_request(tmp_path))

    assert second.history == first.history
    assert second.terminal_model_state.is_equivalent_to(first.terminal_model_state)
    assert second.termination_reason == first.termination_reason
    assert second.device_name == first.device_name
    assert second.batch_size_used == first.batch_size_used
    client_result = second.history.rounds[0].client_results[0]
    assert client_result.l2_drift is not None
    assert client_result.rms_drift is not None
    assert client_result.terminal_prox_penalty is None


def test_train_global_federated_raises_explicitly_on_corrupt_persisted_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    require_cuda()
    request = _request(tmp_path)
    federated_module.train_global_federated(request)

    round_summary_path = request.output_directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    round_summary_path.write_bytes(b"not a parquet file")

    def _fail_if_retrained(request: FederatedTrainingRequest) -> None:
        pytest.fail("corrupt persisted evidence must fail explicitly rather than trigger a silent retrain")

    monkeypatch.setattr(federated_module, "run_federated_training", _fail_if_retrained)

    with pytest.raises(ArtifactIntegrityError):
        federated_module.train_global_federated(_request(tmp_path))


def test_load_federated_training_returns_none_without_terminal_model_artifact(tmp_path: Path) -> None:
    directory = tmp_path / "training"
    directory.mkdir()

    result = load_federated_training(
        fedavg_coordinate(Seed(0)),
        directory,
        clients=tuple(client_input.client for client_input in build_all_client_inputs(tmp_path)),
        diagnostic_snapshot_protocol=FAST_PROTOCOL,
        autoencoder=AUTOENCODER,
        batch_size=BATCH_SIZE,
    )

    assert result is None


def test_load_federated_training_raises_on_architecture_mismatch(tmp_path: Path) -> None:
    require_cuda()
    request = _request(tmp_path)
    federated_module.train_global_federated(request)

    mismatched_widths = AutoencoderArchitecture((AUTOENCODER.widths[0], AUTOENCODER.widths[0]))
    mismatched_autoencoder = AutoencoderProtocol(widths=mismatched_widths)
    mismatched_model = build_reconstruction_autoencoder(mismatched_autoencoder, initialization_seed=Seed(0))
    save_state_dict_tensors(
        AutoencoderModelState.from_model(mismatched_model).to_torch_state_dict(),
        request.output_directory / FederatedHistoryAssetName.TERMINAL_MODEL.value,
    )

    with pytest.raises(ArtifactIntegrityError):
        load_federated_training(
            request.coordinate,
            request.output_directory,
            clients=tuple(client_input.client for client_input in request.clients),
            diagnostic_snapshot_protocol=FAST_PROTOCOL,
            autoencoder=AUTOENCODER,
            batch_size=BATCH_SIZE,
        )


def test_load_federated_training_module_is_wired_into_train_global_federated() -> None:
    assert federated_module.load_federated_training is publication_module.load_federated_training
