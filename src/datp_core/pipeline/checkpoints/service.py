"""Pipeline checkpoint inventory and terminal-selection composition."""

from collections.abc import Callable, Sequence

from datp_core.domain.enums import CheckpointStatus
from datp_core.domain.values import RoundNumber
from datp_core.pipeline.checkpoints.models import PersistedCheckpoint
from datp_core.protocols.checkpoints import (
    select_terminal_checkpoint as apply_terminal_selection,
    validate_ordered_checkpoint_inventory as validate_inventory,
)


def validate_ordered_checkpoint_inventory[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    expected_rounds: tuple[RoundNumber, ...],
) -> tuple[CandidateT, ...]:
    return validate_inventory(candidates, expected_rounds)


def select_terminal_checkpoint[CandidateT: PersistedCheckpoint](
    candidates: Sequence[CandidateT],
    maximum_round: RoundNumber,
    *,
    rebuild: Callable[[CandidateT, CheckpointStatus], CandidateT],
) -> tuple[tuple[CandidateT, ...], CandidateT]:
    return apply_terminal_selection(candidates, maximum_round, rebuild=rebuild)
