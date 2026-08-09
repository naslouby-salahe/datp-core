from dataclasses import dataclass
from pathlib import Path

import pytest

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import CheckpointStatus
from datp_core.core.numeric import MetricValue, RoundNumber
from datp_core.detector.checkpoints.contracts import (
    select_terminal_checkpoint,
    validate_ordered_checkpoint_inventory,
    validate_persisted_checkpoint_file,
)


@dataclass(frozen=True, slots=True)
class _Candidate:
    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus


def _candidate(tmp_path: Path, round_number: int) -> _Candidate:
    path = tmp_path / f"checkpoint_round_{round_number}.safetensors"
    path.write_text(f"round-{round_number}", encoding="utf-8")
    from datp_core.artifacts.provenance import Checksum

    return _Candidate(
        round_number=RoundNumber(round_number),
        tensor_path=path,
        tensor_checksum=Checksum.from_file(path),
        mean_training_loss=MetricValue(float(round_number)),
        status=CheckpointStatus.CANDIDATE,
    )


def test_shared_checkpoint_inventory_and_terminal_selection(tmp_path: Path) -> None:
    candidates = (_candidate(tmp_path, 1), _candidate(tmp_path, 2))
    ordered = validate_ordered_checkpoint_inventory(
        candidates,
        (RoundNumber(1), RoundNumber(2)),
    )
    selection = select_terminal_checkpoint(
        ordered,
        RoundNumber(2),
        rebuild=lambda candidate, status: _Candidate(
            round_number=candidate.round_number,
            tensor_path=candidate.tensor_path,
            tensor_checksum=candidate.tensor_checksum,
            mean_training_loss=candidate.mean_training_loss,
            status=status,
        ),
    )
    assert selection.selected.round_number == RoundNumber(2)
    assert tuple(candidate.status for candidate in selection.candidates) == (
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    )


def test_shared_checkpoint_file_validation_rejects_checksum_drift(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path, 1)
    candidate.tensor_path.write_text("changed", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        validate_persisted_checkpoint_file(candidate.tensor_path, candidate.tensor_checksum)
