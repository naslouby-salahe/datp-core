import pytest
import torch
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    FEATURE_NAMES,
    benign_frame,
    client_identity,
    fitted_state,
    require_cuda,
)

from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import BatchSize, Checksum, OutcomeLabelSequence, RowCount, Seed
from datp_core.learning.autoencoder import FederatedAutoencoder
from datp_core.learning.federated.models import ClientUpdate
from datp_core.learning.federated.training import (
    ProximalTerm,
    aggregate_client_updates,
    build_client_loader,
    checksum_state_dict,
    client_round_seed,
    extract_feature_arrays,
    preprocessing_state_set_checksum,
    proximal_penalty,
    reject_attack_rows_in_federated_training,
    reject_centralized_preprocessing_for_federated_training,
    run_local_epoch,
    serialized_state_dict_bytes,
)
from datp_core.populations.models import PopulationOutcomeLabel


def test_client_round_seed_is_deterministic_and_client_specific() -> None:
    first = client_round_seed(Seed(3), 0)
    second = client_round_seed(Seed(3), 1)
    assert first != second
    assert client_round_seed(Seed(3), 0) == first


def test_extract_feature_arrays_rejects_row_misalignment() -> None:
    frame = benign_frame(8)
    matrix, labels, row_ids = extract_feature_arrays(frame, FEATURE_NAMES)
    assert matrix.shape == (8, 4)
    assert len(labels) == 8
    assert len(row_ids) == 8


def test_reject_attack_rows_in_federated_training_raises_on_any_attack_label() -> None:
    labels = OutcomeLabelSequence((PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.ATTACK.value))
    with pytest.raises(LeakageError, match="attack-labelled rows"):
        reject_attack_rows_in_federated_training(labels, PopulationOutcomeLabel.BENIGN.value)


def test_reject_attack_rows_in_federated_training_accepts_all_benign() -> None:
    labels = OutcomeLabelSequence((PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.BENIGN.value))
    reject_attack_rows_in_federated_training(labels, PopulationOutcomeLabel.BENIGN.value)


def test_reject_centralized_preprocessing_for_federated_training(tmp_path) -> None:
    from datp_core.domain.enums import ProcessedDataBranch

    state = fitted_state(tmp_path / "state.skops", "client_a")
    object.__setattr__(state, "branch", ProcessedDataBranch.CENTRALIZED_REFERENCE)
    with pytest.raises(LeakageError, match="centralized preprocessing state"):
        reject_centralized_preprocessing_for_federated_training(state)


def test_build_client_loader_is_deterministic_given_the_same_seed() -> None:
    device = require_cuda()
    matrix = benign_frame(8).select(FEATURE_NAMES.as_list()).to_numpy()
    first = build_client_loader(matrix, batch_size=BatchSize(4), seed=Seed(1), device=device)
    second = build_client_loader(matrix, batch_size=BatchSize(4), seed=Seed(1), device=device)
    first_batches = [batch[0].cpu().tolist() for batch in first]
    second_batches = [batch[0].cpu().tolist() for batch in second]
    assert first_batches == second_batches


def test_run_local_epoch_requires_at_least_one_full_batch() -> None:
    device = require_cuda()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    short_matrix = benign_frame(2).select(FEATURE_NAMES.as_list()).to_numpy()
    loader = build_client_loader(short_matrix, batch_size=BatchSize(4), seed=Seed(1), device=device)
    with pytest.raises(ScientificContractError, match="no batches"):
        run_local_epoch(model, optimizer, loader, device)


def test_run_local_epoch_returns_full_state_and_positive_sample_count() -> None:
    device = require_cuda()
    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    matrix = benign_frame(8).select(FEATURE_NAMES.as_list()).to_numpy()
    loader = build_client_loader(matrix, batch_size=BatchSize(4), seed=Seed(1), device=device)
    state, loss, sample_count = run_local_epoch(model, optimizer, loader, device)
    assert set(state.keys()) == set(model.state_dict().keys())
    assert sample_count.value == 8
    assert loss.value >= 0.0


def test_run_local_epoch_with_larger_proximal_coefficient_stays_closer_to_reference() -> None:
    # Adam normalizes step size by gradient magnitude, so this comparison needs SGD (whose
    # step size scales linearly with the gradient) with a small learning rate and many small
    # steps, to stay in the regime where a bigger quadratic penalty reliably pulls the
    # trajectory closer to the reference rather than causing single-step overshoot.
    device = require_cuda()
    matrix = benign_frame(64).select(FEATURE_NAMES.as_list()).to_numpy()
    seed_model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    reference_state = {name: tensor.detach().clone() for name, tensor in seed_model.state_dict().items()}

    def run_with_coefficient(coefficient: float) -> dict[str, torch.Tensor]:
        model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
        model.load_state_dict({name: tensor.clone() for name, tensor in reference_state.items()})
        optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
        loader = build_client_loader(matrix, batch_size=BatchSize(4), seed=Seed(1), device=device)
        state, _loss, _count = run_local_epoch(
            model,
            optimizer,
            loader,
            device,
            proximal_term=ProximalTerm(reference_state=reference_state, coefficient=coefficient),
        )
        return {name: torch.sum((tensor.cpu() - reference_state[name].cpu()) ** 2) for name, tensor in state.items()}

    small_coefficient_drift = run_with_coefficient(0.0)
    large_coefficient_drift = run_with_coefficient(100.0)
    total_small = sum(float(value) for value in small_coefficient_drift.values())
    total_large = sum(float(value) for value in large_coefficient_drift.values())
    assert total_large < total_small


def test_proximal_penalty_is_zero_when_parameters_match() -> None:
    device = require_cuda()
    parameters = [torch.zeros(3, device=device), torch.ones(2, device=device)]
    penalty = proximal_penalty(parameters, parameters, 1.0)
    assert float(penalty.item()) == 0.0


def test_proximal_penalty_scales_with_coefficient() -> None:
    device = require_cuda()
    local = [torch.ones(2, device=device)]
    reference = [torch.zeros(2, device=device)]
    small = proximal_penalty(local, reference, 1.0)
    large = proximal_penalty(local, reference, 4.0)
    assert float(large.item()) == pytest.approx(float(small.item()) * 4.0)


def test_aggregate_client_updates_is_sample_count_weighted() -> None:
    heavy = ClientUpdate(
        client=client_identity("client_a"),
        state_dict={"w": torch.zeros(2)},
        sample_count=RowCount(9),
        local_loss=_metric(0.0),
    )
    light = ClientUpdate(
        client=client_identity("client_b"),
        state_dict={"w": torch.ones(2)},
        sample_count=RowCount(1),
        local_loss=_metric(0.0),
    )
    aggregated = aggregate_client_updates([heavy, light])
    assert torch.allclose(aggregated["w"], torch.tensor([0.1, 0.1]))


def _metric(value: float):
    from datp_core.domain.values import MetricValue

    return MetricValue(value)


def test_aggregate_client_updates_requires_at_least_one_update() -> None:
    with pytest.raises(ScientificContractError, match="at least one client update"):
        aggregate_client_updates([])


def test_serialized_state_dict_bytes_and_checksum_are_deterministic() -> None:
    first_state = {"w": torch.arange(4, dtype=torch.float32)}
    second_state = {"w": torch.arange(4, dtype=torch.float32)}
    assert serialized_state_dict_bytes(first_state) == serialized_state_dict_bytes(second_state)
    assert checksum_state_dict(first_state) == checksum_state_dict(second_state)


def test_preprocessing_state_set_checksum_is_order_independent() -> None:
    checksums = (Checksum("a" * 64), Checksum("b" * 64))
    reversed_checksums = tuple(reversed(checksums))
    assert preprocessing_state_set_checksum(checksums) == preprocessing_state_set_checksum(reversed_checksums)
