from dataclasses import dataclass, field

import torch

from datp_core.application.ports.learning import TrainFederatedModelRequest
from datp_core.application.ports.persistence import (
    CheckpointLookupResult,
    CheckpointWriteResult,
    FindCheckpointRequest,
    LoadRecoveryStateRequest,
    RecoveryLookupResult,
    RecoveryWriteResult,
    SaveRecoveryStateRequest,
    SaveScientificCheckpointRequest,
)
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    DatasetSourceIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactSchemaVersion,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.checkpoints import CheckpointDescriptor, CheckpointSchedule
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import (
    AggregationStrategy,
    ClientBatchPartitioning,
    DeterminismLevel,
    FederationSpec,
    LrSchedulerType,
    ModelPersonalizationStrategy,
    OptimizerStepSemantics,
    OptimizerType,
    ParticipationStrategy,
    PrecisionMode,
    TrainingBatchSpec,
    TrainingSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps, WorkerCount
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan, RoundNumber, Seed
from datp_core.infrastructure.learning.federation.trainer import (
    ClientModelUpdate,
    FederatedRoundUpdates,
    FlowerFederatedTrainer,
    StagedFederatedCheckpoint,
)
from tests.support.runtime_orchestration import runtime_profile


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _artifact_ref(character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _request() -> TrainFederatedModelRequest:
    batch_size = BatchSize(value=8)
    return TrainFederatedModelRequest(
        processed_splits=ProcessedSplitResult(
            artifacts=(_artifact_ref("a", ArtifactType.PROCESSED_SPLIT),),
            split_manifest_identity=SplitIdentity(value=_fingerprint("b")),
            preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("c")),
            source_row_lineage=(DatasetSourceIdentity(value=_fingerprint("d")),),
        ),
        training=TrainingSpec(
            seed=Seed(value=1),
            autoencoder=AutoencoderSpec(
                input_dim=4,
                hidden_dims=(2,),
                bottleneck_dim=1,
                activation=ActivationFunction.RELU,
            ),
            federation=FederationSpec(
                aggregation=AggregationStrategy.FEDAVG,
                local_epochs=1,
                participation=ParticipationStrategy.FULL,
                rounds_max=200,
                fedprox_mu=None,
            ),
            optimizer=OptimizerType.ADAM,
            lr=0.001,
            scheduler=LrSchedulerType.NONE,
            training_batch=TrainingBatchSpec(
                micro_batch_size=batch_size,
                gradient_accumulation_steps=GradientAccumulationSteps(value=1),
                effective_batch_size=batch_size,
                dataloader_batch_size=batch_size,
                client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
                optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
            ),
            precision=PrecisionMode.FP32,
            determinism=DeterminismLevel.STRICT,
            personalization=ModelPersonalizationStrategy.NONE,
        ),
        checkpoint_schedule=CheckpointSchedule(
            rounds=tuple(RoundNumber(value=value) for value in (25, 50, 75, 100, 125, 150, 200))
        ),
        resolved_batch_profile=runtime_profile(),
        dataloader_seed_plan=DataLoaderSeedPlan(
            shuffle_seed=Seed(value=11),
            sampler_seed=Seed(value=12),
            worker_seed=Seed(value=13),
            client_seed=Seed(value=14),
            epoch_seed=Seed(value=15),
            round_seed=Seed(value=16),
            worker_count=WorkerCount(value=0),
        ),
        compatible_recovery=None,
    )


@dataclass
class _RoundExecutor:
    executed_rounds: list[RoundNumber] = field(default_factory=lambda: list[RoundNumber]())

    def execute(self, request: TrainFederatedModelRequest, round_number: RoundNumber) -> FederatedRoundUpdates:
        del request
        self.executed_rounds.append(round_number)
        return FederatedRoundUpdates(
            expected_clients=(ClientId(value="client-a"), ClientId(value="client-b")),
            updates=(
                ClientModelUpdate(
                    client_id=ClientId(value="client-a"), tensors=(torch.tensor((1.0,)),), sample_count=1
                ),
                ClientModelUpdate(
                    client_id=ClientId(value="client-b"), tensors=(torch.tensor((3.0,)),), sample_count=1
                ),
            ),
        )


@dataclass
class _CheckpointStager:
    staged_rounds: list[RoundNumber] = field(default_factory=lambda: list[RoundNumber]())

    def stage(
        self,
        request: TrainFederatedModelRequest,
        round_number: RoundNumber,
        parameters: tuple[torch.Tensor, ...],
    ) -> StagedFederatedCheckpoint:
        assert torch.equal(parameters[0], torch.tensor((2.0,)))
        self.staged_rounds.append(round_number)
        artifact = _artifact_ref("e", ArtifactType.SCIENTIFIC_CHECKPOINT)
        return StagedFederatedCheckpoint(
            checkpoint=CheckpointDescriptor(
                checkpoint_id=CheckpointId(value=f"checkpoint-{round_number.value:064x}"),
                round=round_number,
                seed=request.training.seed,
                training_identity=TrainingIdentity(value=_fingerprint("f")),
                artifact_ref=artifact,
                content_hash=artifact.content_hash,
                schema_version=artifact.schema_version,
            ),
            artifact=artifact,
        )


@dataclass
class _CheckpointStore:
    saved_requests: list[SaveScientificCheckpointRequest] = field(
        default_factory=lambda: list[SaveScientificCheckpointRequest]()
    )

    def find_compatible(self, request: FindCheckpointRequest) -> CheckpointLookupResult:
        del request
        return CheckpointLookupResult(checkpoint=None)

    def save(self, request: SaveScientificCheckpointRequest) -> CheckpointWriteResult:
        self.saved_requests.append(request)
        return CheckpointWriteResult(checkpoint=request.checkpoint)

    def save_recovery(self, request: SaveRecoveryStateRequest) -> RecoveryWriteResult:
        raise AssertionError(f"scientific training must not save recovery state: {request!r}")

    def load_recovery(self, request: LoadRecoveryStateRequest) -> RecoveryLookupResult:
        raise AssertionError(f"scientific training must not load recovery state: {request!r}")


def test_trainer_completes_all_rounds_and_persists_only_the_fixed_schedule() -> None:
    executor = _RoundExecutor()
    stager = _CheckpointStager()
    store = _CheckpointStore()

    result = FlowerFederatedTrainer(
        round_executor=executor,
        checkpoint_stager=stager,
        checkpoint_store=store,
    ).train(_request())

    scheduled_rounds = (25, 50, 75, 100, 125, 150, 200)
    assert tuple(round_number.value for round_number in executor.executed_rounds) == tuple(range(1, 201))
    assert tuple(round_number.value for round_number in stager.staged_rounds) == scheduled_rounds
    assert tuple(request.checkpoint.round.value for request in store.saved_requests) == scheduled_rounds
    assert tuple(checkpoint.round.value for checkpoint in result.checkpoints) == scheduled_rounds
