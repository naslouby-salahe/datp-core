"""Shared structural checkpoint contracts without branch-specific science."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from datp_core.domain.enums import CheckpointStatus
from datp_core.domain.values import Checksum, MetricValue, RoundNumber

RETAINED_CHECKPOINT_STATUSES = frozenset(
    {
        CheckpointStatus.CANDIDATE,
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    }
)


@runtime_checkable
class PersistedCheckpoint(Protocol):
    """Minimum persisted-checkpoint shape shared by centralized and federated branches."""

    round_number: RoundNumber
    tensor_path: Path
    tensor_checksum: Checksum
    mean_training_loss: MetricValue
    status: CheckpointStatus
