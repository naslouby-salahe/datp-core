from dataclasses import dataclass
from typing import assert_never

from datp_core.application.ports.learning import (
    CentralizedModelTrainer,
    CentralizedTrainingRunResult,
    FederatedTrainer,
    ResolvedBatchExecutionProfile,
    TrainCentralizedModelRequest,
    TrainFederatedModelRequest,
    TrainingRunResult,
)
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.domain.learning.checkpoints import CheckpointSchedule, RecoveryState
from datp_core.domain.learning.training import TrainingSpec
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedTrainingStageRequest:
    processed_splits: ProcessedSplitResult
    training: TrainingSpec
    checkpoint_schedule: CheckpointSchedule
    resolved_batch_profile: ResolvedBatchExecutionProfile
    dataloader_seed_plan: DataLoaderSeedPlan
    compatible_recovery: RecoveryState | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedTrainingStageRequest:
    processed_splits: ProcessedSplitResult
    comparator: CentralizedModelComparatorSpec


type TrainingStageRequest = FederatedTrainingStageRequest | CentralizedTrainingStageRequest
type TrainingStageResult = TrainingRunResult | CentralizedTrainingRunResult


def train_model(
    *,
    request: TrainingStageRequest,
    federated_trainer: FederatedTrainer,
    centralized_trainer: CentralizedModelTrainer,
) -> TrainingStageResult:
    match request:
        case FederatedTrainingStageRequest():
            return federated_trainer.train(
                TrainFederatedModelRequest(
                    processed_splits=request.processed_splits,
                    training=request.training,
                    checkpoint_schedule=request.checkpoint_schedule,
                    resolved_batch_profile=request.resolved_batch_profile,
                    dataloader_seed_plan=request.dataloader_seed_plan,
                    compatible_recovery=request.compatible_recovery,
                )
            )
        case CentralizedTrainingStageRequest():
            return centralized_trainer.train(
                TrainCentralizedModelRequest(
                    processed_splits=request.processed_splits,
                    comparator=request.comparator,
                )
            )
        case _ as unreachable:
            assert_never(unreachable)
