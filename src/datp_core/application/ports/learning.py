from dataclasses import dataclass
from typing import Protocol

from datp_core.application.runtime.preflight import ResolvedBatchExecutionProfile
from datp_core.domain.artifacts.lineage import CentralizedCheckpointIdentity
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, CheckpointSchedule, RecoveryState
from datp_core.domain.learning.training import TrainingSpec
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedModelRequest:
    processed_splits: ProcessedSplitResult
    training: TrainingSpec
    checkpoint_schedule: CheckpointSchedule
    resolved_batch_profile: ResolvedBatchExecutionProfile
    dataloader_seed_plan: DataLoaderSeedPlan
    compatible_recovery: RecoveryState | None


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainCentralizedModelRequest:
    processed_splits: ProcessedSplitResult
    comparator: CentralizedModelComparatorSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainingRunResult:
    checkpoints: tuple[CheckpointDescriptor, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedTrainingRunResult:
    checkpoint_identity: CentralizedCheckpointIdentity
    checkpoint_artifact: ArtifactRef

    def __post_init__(self) -> None:
        if not (
            type(self.checkpoint_identity) is CentralizedCheckpointIdentity
            and type(self.checkpoint_artifact) is ArtifactRef
        ):
            raise DomainValidationError(
                detail="centralized training result requires only centralized checkpoint lineage",
                value=repr(self),
                constraint="CentralizedCheckpointIdentity and ArtifactRef",
            )


class FederatedTrainer(Protocol):
    def train(self, request: TrainFederatedModelRequest) -> TrainingRunResult: ...


class CentralizedModelTrainer(Protocol):
    def train(self, request: TrainCentralizedModelRequest) -> CentralizedTrainingRunResult: ...
