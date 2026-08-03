"""Scientific contract: FIXED_TERMINAL_MAXIMUM_ROUND selection ignores every test-derived signal."""

from pathlib import Path

import pytest
from tests.unit.learning.federated.helpers import AUTOENCODER, CHECKPOINT, fedavg_coordinate

from datp_core.domain.enums import CheckpointSelectionRule, CheckpointStatus
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RoundNumber, Seed
from datp_core.learning.federated.checkpointing import RoundSnapshot, retain_checkpoint_candidates, select_checkpoint


def _candidates_with_favorable_non_terminal_loss(tmp_path: Path):
    from datp_core.learning.autoencoder import ReconstructionAutoencoder

    coordinate = fedavg_coordinate(Seed(0))
    model = ReconstructionAutoencoder(AUTOENCODER.widths)
    state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
    # The non-terminal candidate is given a dramatically better ("lower") loss than the
    # terminal candidate. If any test-adjacent signal ever entered selection, this would
    # tempt a selector into picking the non-terminal round instead.
    losses = {CHECKPOINT.candidates[0]: MetricValue(0.0001), CHECKPOINT.candidates[-1]: MetricValue(99.0)}
    snapshots = tuple(RoundSnapshot(candidate, state, losses[candidate]) for candidate in CHECKPOINT.candidates)
    candidates = retain_checkpoint_candidates(
        coordinate,
        snapshots,
        checkpoint_protocol=CHECKPOINT,
        autoencoder=AUTOENCODER,
        output_directory=tmp_path,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
        client=None,
    )
    return coordinate, candidates


def test_selection_ignores_training_loss_even_when_a_non_terminal_round_looks_better(tmp_path: Path) -> None:
    coordinate, candidates = _candidates_with_favorable_non_terminal_loss(tmp_path)
    decision = select_checkpoint(
        candidates,
        CHECKPOINT,
        coordinate=coordinate,
        client=None,
        selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
    )
    assert decision.selected.round_number == CHECKPOINT.maximum_round
    assert decision.selected.mean_training_loss.value == 99.0


@pytest.mark.parametrize(
    "held_out_metrics",
    [
        (MetricValue(0.5),),
        (MetricValue(0.99), MetricValue(0.01)),
        (MetricValue(1.0),) * 5,
    ],
)
def test_selection_rejects_every_shape_of_held_out_metrics(tmp_path: Path, held_out_metrics) -> None:
    coordinate, candidates = _candidates_with_favorable_non_terminal_loss(tmp_path)
    with pytest.raises(LeakageError, match="held-out evaluation outcomes"):
        select_checkpoint(
            candidates,
            CHECKPOINT,
            coordinate=coordinate,
            client=None,
            selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
            held_out_metrics=held_out_metrics,
            preprocessing_state_set_checksum=Checksum("a" * 64),
            split_manifest_checksum=Checksum("b" * 64),
        )


def test_selection_rejects_attack_label_presence_regardless_of_other_arguments(tmp_path: Path) -> None:
    coordinate, candidates = _candidates_with_favorable_non_terminal_loss(tmp_path)
    with pytest.raises(LeakageError, match="attack labels"):
        select_checkpoint(
            candidates,
            CHECKPOINT,
            coordinate=coordinate,
            client=None,
            selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
            attack_labels_present=True,
            preprocessing_state_set_checksum=Checksum("a" * 64),
            split_manifest_checksum=Checksum("b" * 64),
        )


def test_historical_anchor_endpoint_status_can_never_be_constructed(tmp_path: Path) -> None:
    """Conference anchor historical endpoints are isolated: a federated checkpoint candidate
    cannot even be constructed with HISTORICAL_ENDPOINT status, let alone selected."""
    _coordinate, candidates = _candidates_with_favorable_non_terminal_loss(tmp_path)
    original = candidates[0]
    with pytest.raises(ScientificContractError, match="invalid status"):
        original.__class__(
            coordinate=original.coordinate,
            round_number=original.round_number,
            client=original.client,
            tensor_path=original.tensor_path,
            tensor_checksum=original.tensor_checksum,
            mean_training_loss=original.mean_training_loss,
            status=CheckpointStatus.HISTORICAL_ENDPOINT,
            preprocessing_state_set_checksum=original.preprocessing_state_set_checksum,
            split_manifest_checksum=original.split_manifest_checksum,
        )


def test_only_the_declared_maximum_round_is_ever_marked_selected(tmp_path: Path) -> None:
    coordinate, candidates = _candidates_with_favorable_non_terminal_loss(tmp_path)
    decision = select_checkpoint(
        candidates,
        CHECKPOINT,
        coordinate=coordinate,
        client=None,
        selection_rule=CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
        preprocessing_state_set_checksum=Checksum("a" * 64),
        split_manifest_checksum=Checksum("b" * 64),
    )
    selected_candidates = [
        item for item in decision.candidates if item.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE
    ]
    assert len(selected_candidates) == 1
    assert selected_candidates[0].round_number == CHECKPOINT.maximum_round
    stability_candidates = [item for item in decision.candidates if item.status is CheckpointStatus.STABILITY_EVIDENCE]
    assert all(item.round_number != CHECKPOINT.maximum_round for item in stability_candidates)


def test_round_number_type_alone_cannot_smuggle_a_metric_value() -> None:
    with pytest.raises(ValueError, match="round number"):
        RoundNumber(-1)
