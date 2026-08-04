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

    @property
    def round_number(self) -> RoundNumber: ...

    @property
    def tensor_path(self) -> Path: ...

    @property
    def tensor_checksum(self) -> Checksum: ...

    @property
    def mean_training_loss(self) -> MetricValue: ...

    @property
    def status(self) -> CheckpointStatus: ...
