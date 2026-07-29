from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import (
    AUTOENCODER,
    CHECKPOINT,
    client_identity,
    fedavg_coordinate,
    require_cuda,
)

from datp_core.domain.enums import CheckpointSelectionRule, CheckpointStatus
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RoundNumber, Seed
from datp_core.learning.federated.checkpointing import (
    RoundSnapshot,
    candidate_set_checksum,
    candidate_tensor_name,
    retain_checkpoint_candidates,
    select_checkpoint,
    validate_candidate_coordinates,
)
from datp_core.runtime.compute import resolve_cuda_device


def _snapshots() -> tuple[RoundSnapshot, ...]:
    device = require_cuda()
    from datp_core.learning.autoencoder import FederatedAutoencoder

    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    return tuple(RoundSnapshot(candidate, state, MetricValue(0.1)) for candidate in CHECKPOINT.candidates)


def test_retain_checkpoint_candidates_persists_and_reloads(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    assert len(candidates) == len(CHECKPOINT.candidates)
    for candidate in candidates:
        assert candidate.tensor_path.is_file()
        assert candidate.status is CheckpointStatus.CANDIDATE


def test_select_checkpoint_chooses_maximum_round(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    decision = select_checkpoint(
        candidates,
        CHECKPOINT,
        coordinate=coordinate,
        client=None,
        selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
    )
    assert decision.selected.round_number == CHECKPOINT.maximum_round
    assert decision.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE
    non_terminal = [item for item in decision.candidates if item.round_number != CHECKPOINT.maximum_round]
    assert all(item.status is CheckpointStatus.STABILITY_EVIDENCE for item in non_terminal)


def test_select_checkpoint_rejects_held_out_metrics(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    with pytest.raises(LeakageError, match="held-out evaluation outcomes"):
        select_checkpoint(
            candidates,
            CHECKPOINT,
            coordinate=coordinate,
            client=None,
            selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
            held_out_metrics=(MetricValue(0.9),),
        )


def test_select_checkpoint_rejects_attack_labels(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    with pytest.raises(LeakageError, match="attack labels"):
        select_checkpoint(
            candidates,
            CHECKPOINT,
            coordinate=coordinate,
            client=None,
            selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
            attack_labels_present=True,
        )


def test_retain_checkpoint_candidates_rejects_missing_declared_round(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = require_cuda()
    from datp_core.learning.autoencoder import FederatedAutoencoder

    model = FederatedAutoencoder(AUTOENCODER.widths).to(device)
    state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    only_one_snapshot = (RoundSnapshot(CHECKPOINT.candidates[0], state, MetricValue(0.1)),)
    with pytest.raises(ScientificContractError, match="declared candidate rounds"):
        retain_checkpoint_candidates(
            coordinate,
            only_one_snapshot,
            checkpoint_protocol=CHECKPOINT,
            autoencoder=AUTOENCODER,
            output_directory=tmp_path,
            preprocessing_state_set_checksum=Checksum("a" * 64),
            split_manifest_checksum=Checksum("b" * 64),
            client=None,
            device=device,
        )


def test_select_checkpoint_rejects_missing_tensor_file(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    candidates[0].tensor_path.unlink()
    with pytest.raises(ArtifactIntegrityError, match="tensor file is missing"):
        select_checkpoint(
            candidates,
            CHECKPOINT,
            coordinate=coordinate,
            client=None,
            selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
        )


def test_validate_candidate_coordinates_rejects_mismatched_client(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    with pytest.raises(ScientificContractError, match="client identity mismatch"):
        validate_candidate_coordinates(
            candidates,
            coordinate,
            client=client_identity("client_a"),
            preprocessing_state_set_checksum=Checksum("a" * 64),
            split_manifest_checksum=Checksum("b" * 64),
        )


def test_candidate_tensor_name_distinguishes_personalized_clients() -> None:
    global_name = candidate_tensor_name(RoundNumber(200))
    personalized_name = candidate_tensor_name(RoundNumber(200), client_identity("client_a"))
    assert global_name != personalized_name
    assert global_name.endswith(".safetensors")
    assert "client_a" in personalized_name


def test_candidate_set_checksum_is_order_independent_of_input_but_content_sensitive(tmp_path: Path) -> None:
    coordinate = fedavg_coordinate(Seed(0))
    device = resolve_cuda_device()
    candidates = retain_checkpoint_candidates(
        coordinate,
        _snapshots(),
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
        device=device,
    )
    first = candidate_set_checksum(candidates)
    second = candidate_set_checksum(candidates)
    assert first == second
