import pytest
import torch

from datp_core.application.ports.learning import TrainFederatedModelRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, FittedPreprocessorIdentity, SplitIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.preprocessing import ProcessedSplitResult
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.checkpoints import SCHEDULED_CHECKPOINT_ROUNDS, CheckpointSchedule
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.admissibility import WorkerCount
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan, RoundNumber, Seed
from datp_core.infrastructure.learning.federation.nbaiot_anchor_round_executor import AnchorFederatedRoundExecutor
from datp_core.infrastructure.learning.models.nbaiot_anchor_training import (
    ANCHOR_AUTOENCODER_SPECIFICATION,
    anchor_training_spec,
)
from datp_core.infrastructure.runtime.determinism import configure_determinism
from tests.support.cuda_lane import skip_if_cuda_unavailable
from tests.support.runtime_orchestration import runtime_profile

_INPUT_DIM = ANCHOR_AUTOENCODER_SPECIFICATION.input_dim


def _split_result() -> ProcessedSplitResult:
    fingerprint = StageFingerprint(value="a" * 64)
    return ProcessedSplitResult(
        artifacts=(
            ArtifactRef(
                artifact_id=ArtifactId(value="artifact-" + "b" * 64),
                artifact_type=ArtifactType.PROCESSED_SPLIT,
                content_hash="b" * 64,
                schema_version=ArtifactSchemaVersion(value="v1"),
                serialization_format=SerializationFormat.PARQUET,
            ),
        ),
        split_manifest_identity=SplitIdentity(value=fingerprint),
        preprocessor_identity=FittedPreprocessorIdentity(value=fingerprint),
        source_row_lineage=(DatasetSourceIdentity(value=fingerprint),),
    )


def _request(*, seed: Seed) -> TrainFederatedModelRequest:
    return TrainFederatedModelRequest(
        processed_splits=_split_result(),
        training=anchor_training_spec(seed=seed),
        checkpoint_schedule=CheckpointSchedule(
            rounds=tuple(RoundNumber(value=value) for value in SCHEDULED_CHECKPOINT_ROUNDS)
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


def _client_batches(generator: torch.Generator) -> dict[ClientId, torch.Tensor]:
    return {
        ClientId(value="Danmini_Doorbell"): torch.randn(20, _INPUT_DIM, generator=generator, device="cuda"),
        ClientId(value="Ennio_Doorbell"): torch.randn(12, _INPUT_DIM, generator=generator, device="cuda"),
    }


@pytest.mark.cuda
def test_round_aggregation_is_bit_identical_across_independent_executors_on_cuda() -> None:
    skip_if_cuda_unavailable()
    configure_determinism(DeterminismLevel.STRICT)
    generator = torch.Generator(device="cuda").manual_seed(3)
    batches = _client_batches(generator)
    request = _request(seed=Seed(value=41))

    first_executor = AnchorFederatedRoundExecutor(client_batches=batches)
    second_executor = AnchorFederatedRoundExecutor(client_batches=dict(reversed(tuple(batches.items()))))

    first_executor.execute(request, RoundNumber(value=1))
    second_executor.execute(request, RoundNumber(value=1))

    assert all(
        torch.equal(left, right)
        for left, right in zip(
            first_executor.current_global_parameters().tensors,
            second_executor.current_global_parameters().tensors,
            strict=True,
        )
    )
    assert all(parameter.device.type == "cuda" for parameter in first_executor.current_global_parameters().tensors)


@pytest.mark.cuda
def test_uninterrupted_and_resumed_executors_reach_the_same_global_cuda_state() -> None:
    skip_if_cuda_unavailable()
    configure_determinism(DeterminismLevel.STRICT)
    generator = torch.Generator(device="cuda").manual_seed(5)
    batches = _client_batches(generator)
    request = _request(seed=Seed(value=41))

    uninterrupted = AnchorFederatedRoundExecutor(client_batches=batches)
    for round_value in (1, 2, 3, 4):
        uninterrupted.execute(request, RoundNumber(value=round_value))

    first_half = AnchorFederatedRoundExecutor(client_batches=batches)
    for round_value in (1, 2):
        first_half.execute(request, RoundNumber(value=round_value))
    resumed = AnchorFederatedRoundExecutor(
        client_batches=batches, initial_parameters=first_half.current_global_parameters()
    )
    for round_value in (3, 4):
        resumed.execute(request, RoundNumber(value=round_value))

    assert all(
        torch.equal(left, right)
        for left, right in zip(
            uninterrupted.current_global_parameters().tensors,
            resumed.current_global_parameters().tensors,
            strict=True,
        )
    )
