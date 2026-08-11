import torch
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

from datp_core.core.numeric import Seed
from datp_core.detector.checkpoints.protocols import DIAGNOSTIC_SNAPSHOT_PROTOCOL
from datp_core.detector.training.contracts import FederatedClientDataResidency
from datp_core.detector.training.engine import (
    DeviceResidentFederatedClientData,
    FederatedTrainingRequest,
    prepare_device_resident_client_data,
    prepare_federated_client_data,
    run_federated_training,
)


def test_device_resident_client_data_moves_the_full_cohort_to_cuda(tmp_path) -> None:
    device = require_cuda()
    prepared = tuple(
        prepare_federated_client_data(client_input, AUTOENCODER) for client_input in build_all_client_inputs(tmp_path)
    )

    resident = prepare_device_resident_client_data(prepared, device)

    assert all(isinstance(client_data, DeviceResidentFederatedClientData) for client_data in resident)
    for cpu_client, cuda_client in zip(prepared, resident, strict=True):
        assert isinstance(cuda_client, DeviceResidentFederatedClientData)
        assert cuda_client.features_cuda.device.type == device.type
        assert cuda_client.validation_features_cuda.device.type == device.type
        assert cuda_client.features_cuda.device.index == torch.cuda.current_device()
        assert cuda_client.validation_features_cuda.device.index == torch.cuda.current_device()
        assert torch.equal(cuda_client.features_cuda.cpu(), cpu_client.features_cpu)
        assert torch.equal(cuda_client.validation_features_cuda.cpu(), cpu_client.validation_features_cpu)


def test_device_resident_client_data_falls_back_when_memory_budget_is_exhausted(monkeypatch, tmp_path) -> None:
    device = require_cuda()
    prepared = tuple(
        prepare_federated_client_data(client_input, AUTOENCODER) for client_input in build_all_client_inputs(tmp_path)
    )
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda _: (0, 0))

    resident = prepare_device_resident_client_data(prepared, device)

    assert resident == prepared


def test_gpu_resident_training_is_bitwise_equivalent_to_streaming(tmp_path) -> None:
    require_cuda()
    clients = build_all_client_inputs(tmp_path)
    coordinate = fedavg_coordinate(Seed(0))

    streaming = run_federated_training(
        FederatedTrainingRequest(
            coordinate=coordinate,
            clients=clients,
            population_client_count=POPULATION_CLIENT_COUNT,
            autoencoder=AUTOENCODER,
            training_protocol=FEDAVG_PROTOCOL,
            diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
            training_seed=Seed(0),
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            output_directory=tmp_path,
            client_data_residency=FederatedClientDataResidency.STREAMING,
        )
    )
    resident = run_federated_training(
        FederatedTrainingRequest(
            coordinate=coordinate,
            clients=clients,
            population_client_count=POPULATION_CLIENT_COUNT,
            autoencoder=AUTOENCODER,
            training_protocol=FEDAVG_PROTOCOL,
            diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
            training_seed=Seed(0),
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            output_directory=tmp_path,
            client_data_residency=FederatedClientDataResidency.GPU_RESIDENT_COHORT,
        )
    )

    assert streaming.training_result.history == resident.training_result.history
    assert streaming.training_result.terminal_model_state.is_equivalent_to(
        resident.training_result.terminal_model_state
    )
