import torch
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    LEARNING_RATE,
    build_client_input,
    client_identity,
)

from datp_core.core.identifiers import DatasetId, TrainingModelId
from datp_core.core.numeric import LocalEpochCount, Seed
from datp_core.detector.autoencoder import AutoencoderModelState, build_reconstruction_autoencoder
from datp_core.detector.training.contracts import FedAvgLocalFineTuningProtocol
from datp_core.detector.training.engine import derive_fedavg_local_fine_tuning_seed
from datp_core.detector.training.fine_tuning import FineTuneFedAvgClientsRequest, fine_tune_fedavg_clients
from datp_core.detector.training.protocols import OPTIMIZER


def test_fine_tuning_seed_is_stable_per_client_and_distinct_between_clients() -> None:
    first = client_identity("client_1")
    second = client_identity("client_2")

    assert derive_fedavg_local_fine_tuning_seed(
        DatasetId.NBAIOT, Seed(7), first
    ) == derive_fedavg_local_fine_tuning_seed(DatasetId.NBAIOT, Seed(7), first)
    assert derive_fedavg_local_fine_tuning_seed(
        DatasetId.NBAIOT, Seed(7), first
    ) != derive_fedavg_local_fine_tuning_seed(DatasetId.NBAIOT, Seed(7), second)


def test_fine_tuning_builds_fresh_client_models_from_weights_only(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("datp_core.detector.training.fine_tuning.resolve_cuda_device", lambda: torch.device("cpu"))
    source = build_reconstruction_autoencoder(AUTOENCODER, initialization_seed=Seed(3))
    source_state = AutoencoderModelState.from_model(source)
    protocol = FedAvgLocalFineTuningProtocol(
            source_model=TrainingModelId.FEDAVG_AUTOENCODER,
            local_epochs=LocalEpochCount(10),
        optimizer=OPTIMIZER,
    )

    result = fine_tune_fedavg_clients(
        FineTuneFedAvgClientsRequest(
            dataset=DatasetId.NBAIOT,
            source_fedavg_state=source_state,
            clients=(build_client_input("client_a", tmp_path, seed=Seed(4)),),
            autoencoder=AUTOENCODER,
            protocol=protocol,
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            training_seed=Seed(5),
        )
    )

    model = result.items[0].value
    assert model.source_fedavg_state == source_state
    assert model.terminal_model_state != source_state
