import pytest
import torch
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    build_client_input,
    client_identity,
    fitted_state,
    require_cuda,
)

from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    MetricValue,
    OutcomeLabelSequence,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder
from datp_core.learning.federated.models import ClientUpdate
from datp_core.learning.federated.training import (
    ProximalTerm,
    aggregate_client_updates,
    build_client_loader,
    client_round_seed,
    prepare_federated_client_data,
    preprocessing_state_set_checksum,
    proximal_penalty,
    reject_attack_rows_in_federated_training,
    reject_centralized_preprocessing_for_federated_training,
    run_local_epoch,
    serialize_and_checksum_state_dict,
)
from datp_core.populations.models import PopulationOutcomeLabel


def test_client_round_seed_is_deterministic_and_client_specific() -> None:
    first = client_round_seed(Seed(3), RoundNumber(1), 0)
    second = client_round_seed(Seed(3), RoundNumber(1), 1)
    third = client_round_seed(Seed(3), RoundNumber(2), 0)
    assert first != second
    assert first != third
    assert client_round_seed(Seed(3), RoundNumber(1), 0) == first


def test_reject_attack_rows_in_federated_training_raises_on_any_attack_label() -> None:
    labels = OutcomeLabelSequence((PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.ATTACK.value))
    with pytest.raises(LeakageError, match="attack-labelled rows"):
        reject_attack_rows_in_federated_training(labels)


def test_reject_attack_rows_in_federated_training_accepts_all_benign() -> None:
    labels = OutcomeLabelSequence((PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.BENIGN.value))
    reject_attack_rows_in_federated_training(labels)


def test_reject_centralized_preprocessing_for_federated_training(tmp_path) -> None:
    from datp_core.domain.enums import ProcessedDataBranch

    state = fitted_state(tmp_path / "state.skops", "client_a")
    object.__setattr__(state, "branch", ProcessedDataBranch.CENTRALIZED_REFERENCE)
    with pytest.raises(LeakageError, match="centralized preprocessing state"):
        reject_centralized_preprocessing_for_federated_training(state)


def test_prepare_federated_client_data_validates_client_identity_and_preprocessing(tmp_path) -> None:
    client_input = build_client_input("client_a", tmp_path)
    prepared = prepare_federated_client_data(client_input, AUTOENCODER)
    assert prepared.client == client_identity("client_a")
    assert prepared.features_cpu.shape == (16, 4)


def test_build_client_loader_is_deterministic_given_the_same_seed(tmp_path) -> None:
    client_input = build_client_input("client_a", tmp_path)
    prepared = prepare_federated_client_data(client_input, AUTOENCODER)
    first = build_client_loader(prepared, batch_size=BatchSize(4), seed=Seed(1))
    second = build_client_loader(prepared, batch_size=BatchSize(4), seed=Seed(1))
    first_batches = [batch[0].cpu().tolist() for batch in first]
    second_batches = [batch[0].cpu().tolist() for batch in second]
    assert first_batches == second_batches


def test_run_local_epoch_returns_full_state_and_positive_sample_count(tmp_path) -> None:
    device = require_cuda()
    model = ReconstructionAutoencoder(AUTOENCODER.widths).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    client_input = build_client_input("client_a", tmp_path)
    prepared = prepare_federated_client_data(client_input, AUTOENCODER)
    loader = build_client_loader(prepared, batch_size=BatchSize(4), seed=Seed(1))
    state, loss, sample_count = run_local_epoch(model, optimizer, loader, device)
    assert set(state.keys()) == set(model.state_dict().keys())
    assert sample_count.value == 16
    assert loss.value >= 0.0


def test_run_local_epoch_with_larger_proximal_coefficient_stays_closer_to_reference(tmp_path) -> None:
    device = require_cuda()
    client_input = build_client_input("client_a", tmp_path, row_count=RowCount(64))
    prepared = prepare_federated_client_data(client_input, AUTOENCODER)
    seed_model = ReconstructionAutoencoder(AUTOENCODER.widths).to(device)
    reference_state = {name: tensor.detach().clone() for name, tensor in seed_model.state_dict().items()}

    def run_with_coefficient(coefficient: float) -> dict[str, torch.Tensor]:
        model = ReconstructionAutoencoder(AUTOENCODER.widths).to(device)
        model.load_state_dict({name: tensor.clone() for name, tensor in reference_state.items()})
        optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
        loader = build_client_loader(prepared, batch_size=BatchSize(4), seed=Seed(1))
        state, _loss, _count = run_local_epoch(
            model,
            optimizer,
            loader,
            device,
            proximal_term=ProximalTerm(reference_state=reference_state, coefficient=ProximalCoefficient(coefficient)),
        )
        return {name: torch.sum((tensor.cpu() - reference_state[name].cpu()) ** 2) for name, tensor in state.items()}

    small_coefficient_drift = run_with_coefficient(1e-6)
    large_coefficient_drift = run_with_coefficient(100.0)
    total_small = sum(float(value) for value in small_coefficient_drift.values())
    total_large = sum(float(value) for value in large_coefficient_drift.values())
    assert total_large < total_small


def test_proximal_penalty_is_zero_when_parameters_match() -> None:
    device = require_cuda()
    parameters = [torch.zeros(3, device=device), torch.ones(2, device=device)]
    penalty = proximal_penalty(parameters, parameters, ProximalCoefficient(1.0))
    assert float(penalty.item()) == 0.0


def test_proximal_penalty_scales_with_coefficient() -> None:
    device = require_cuda()
    local = [torch.ones(2, device=device)]
    reference = [torch.zeros(2, device=device)]
    small = proximal_penalty(local, reference, ProximalCoefficient(1.0))
    large = proximal_penalty(local, reference, ProximalCoefficient(4.0))
    assert float(large.item()) == pytest.approx(float(small.item()) * 4.0)


def test_aggregate_client_updates_is_sample_count_weighted() -> None:
    heavy = ClientUpdate(
        client=client_identity("client_a"),
        state_dict={"w": torch.zeros(2)},
        sample_count=RowCount(9),
        local_loss=MetricValue(0.0),
    )
    light = ClientUpdate(
        client=client_identity("client_b"),
        state_dict={"w": torch.ones(2)},
        sample_count=RowCount(1),
        local_loss=MetricValue(0.0),
    )
    aggregated = aggregate_client_updates([heavy, light])
    assert torch.allclose(aggregated["w"], torch.tensor([0.1, 0.1]))


def test_aggregate_client_updates_requires_at_least_one_update() -> None:
    with pytest.raises(ScientificContractError, match="at least one client update"):
        aggregate_client_updates([])


def test_serialize_and_checksum_state_dict_is_deterministic() -> None:
    first_state = {"w": torch.arange(4, dtype=torch.float32)}
    second_state = {"w": torch.arange(4, dtype=torch.float32)}
    first_checksum, _first_bytes = serialize_and_checksum_state_dict(first_state)
    second_checksum, _second_bytes = serialize_and_checksum_state_dict(second_state)
    assert first_checksum == second_checksum


def test_preprocessing_state_set_checksum_binds_client_identity() -> None:
    c1, c2 = client_identity("client_a"), client_identity("client_b")
    chk1, chk2 = Checksum("a" * 64), Checksum("b" * 64)

    pairs1 = ((c1, chk1), (c2, chk2))
    pairs1_reversed = ((c2, chk2), (c1, chk1))
    assert preprocessing_state_set_checksum(pairs1) == preprocessing_state_set_checksum(pairs1_reversed)

    # Swapping checksums between client_a and client_b must change set checksum!
    pairs_swapped = ((c1, chk2), (c2, chk1))
    assert preprocessing_state_set_checksum(pairs1) != preprocessing_state_set_checksum(pairs_swapped)
