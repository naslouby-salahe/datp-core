from pathlib import Path

import pytest
from tests.unit.learning.centralized.helpers import AUTOENCODER, CHECKPOINT, require_cuda, run_miniature_training

from datp_core.core.errors import LeakageError
from datp_core.core.identifiers import CheckpointSelectionRule, CheckpointStatus, TrainingModelId
from datp_core.core.numeric import MetricValue
from datp_core.detector.checkpoints.service import (
    reject_federated_checkpoint,
    retain_centralized_checkpoint_candidates,
    select_centralized_checkpoint,
)
from datp_core.protocols.training import CHECKPOINT_SELECTION_RULE


def test_retains_declared_checkpoint_candidates(tmp_path: Path) -> None:
    require_cuda()
    candidates = retain_centralized_checkpoint_candidates(run_miniature_training(tmp_path / "train"), AUTOENCODER)
    assert len(candidates) == len(CHECKPOINT.candidates)
    assert candidates[0].round_number == CHECKPOINT.candidates[0]
    assert candidates[0].tensor_path.is_file()


def test_selection_uses_fixed_terminal_maximum_round(tmp_path: Path) -> None:
    require_cuda()
    candidates = retain_centralized_checkpoint_candidates(run_miniature_training(tmp_path / "train"), AUTOENCODER)
    decision = select_centralized_checkpoint(
        candidates,
        CHECKPOINT,
        selection_rule=CHECKPOINT_SELECTION_RULE,
    )
    assert decision.selection_rule is CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND
    assert decision.selected.round_number == CHECKPOINT.maximum_round
    assert decision.selected.status is CheckpointStatus.SELECTED_BY_NON_TEST_RULE


def test_selection_rejects_held_out_metrics(tmp_path: Path) -> None:
    require_cuda()
    candidates = retain_centralized_checkpoint_candidates(run_miniature_training(tmp_path / "train"), AUTOENCODER)
    with pytest.raises(LeakageError, match="held-out"):
        select_centralized_checkpoint(
            candidates,
            CHECKPOINT,
            selection_rule=CHECKPOINT_SELECTION_RULE,
            held_out_metrics=(MetricValue(0.1),),
        )


def test_rejects_federated_checkpoint_identity() -> None:
    with pytest.raises(LeakageError, match="federated checkpoint"):
        reject_federated_checkpoint(TrainingModelId.FEDAVG_AUTOENCODER)
