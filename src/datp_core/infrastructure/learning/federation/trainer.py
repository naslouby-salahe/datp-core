from dataclasses import dataclass
from typing import Protocol

import torch
from torch import Tensor

from datp_core.application.ports.learning import TrainFederatedModelRequest, TrainingRunResult
from datp_core.application.ports.persistence import CheckpointStore, SaveScientificCheckpointRequest
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import (
    ClientShapeMismatchError,
    MalformedClientUpdateError,
    NonFiniteClientUpdateError,
    RoundAbortedError,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.checkpoints import CheckpointDescriptor
from datp_core.domain.runtime.seeds import RoundNumber


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientModelUpdate:
    client_id: ClientId
    tensors: tuple[Tensor, ...]
    sample_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class FederatedRoundUpdates:
    expected_clients: tuple[ClientId, ...]
    updates: tuple[ClientModelUpdate, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StagedFederatedCheckpoint:
    checkpoint: CheckpointDescriptor
    artifact: ArtifactRef


class FederatedRoundExecutor(Protocol):
    def execute(self, request: TrainFederatedModelRequest, round_number: RoundNumber) -> FederatedRoundUpdates: ...


class FederatedCheckpointStager(Protocol):
    def stage(
        self,
        request: TrainFederatedModelRequest,
        round_number: RoundNumber,
        parameters: tuple[Tensor, ...],
    ) -> StagedFederatedCheckpoint: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowerFederatedTrainer:
    round_executor: FederatedRoundExecutor
    checkpoint_stager: FederatedCheckpointStager
    checkpoint_store: CheckpointStore

    def train(self, request: TrainFederatedModelRequest) -> TrainingRunResult:
        checkpoints: list[CheckpointDescriptor] = []
        scheduled_rounds = set(request.checkpoint_schedule.rounds)
        for round_value in range(1, request.training.federation.rounds_max + 1):
            round_number = RoundNumber(value=round_value)
            round_updates = self.round_executor.execute(request, round_number)
            validate_full_participation_updates(
                expected_clients=round_updates.expected_clients,
                updates=round_updates.updates,
                round_number=round_number,
            )
            parameters = weighted_fedavg(round_updates.updates)
            if round_number in scheduled_rounds:
                staged = self.checkpoint_stager.stage(request, round_number, parameters)
                saved = self.checkpoint_store.save(
                    SaveScientificCheckpointRequest(checkpoint=staged.checkpoint, staged_artifact=staged.artifact)
                )
                checkpoints.append(saved.checkpoint)
        return TrainingRunResult(checkpoints=tuple(checkpoints))


def validate_full_participation_updates(
    *,
    expected_clients: tuple[ClientId, ...],
    updates: tuple[ClientModelUpdate, ...],
    round_number: RoundNumber,
) -> None:
    completed_clients = tuple(update.client_id for update in updates)
    if _has_invalid_roster(expected_clients, completed_clients):
        raise _round_aborted(expected_clients, completed_clients)
    _validate_update_payloads(updates, round_number)
    _validate_matching_shapes(updates, round_number)


def weighted_fedavg(updates: tuple[ClientModelUpdate, ...]) -> tuple[Tensor, ...]:
    total_samples = sum(update.sample_count for update in updates)
    if total_samples <= 0:
        raise _malformed_update(updates[0].client_id, RoundNumber(value=1), "non-positive aggregate sample count")
    return tuple(
        torch.stack(tuple(update.tensors[index] * (update.sample_count / total_samples) for update in updates)).sum(
            dim=0
        )
        for index in range(len(updates[0].tensors))
    )


def _validate_update_payloads(updates: tuple[ClientModelUpdate, ...], round_number: RoundNumber) -> None:
    for update in updates:
        client = _validated_client(update, round_number)
        _validate_sample_count(update, client, round_number)
        _validate_tensor_collection(update, client, round_number)
        _validate_tensor_values(update, client, round_number)


def _has_invalid_roster(expected: tuple[ClientId, ...], completed: tuple[ClientId, ...]) -> bool:
    if not expected:
        return True
    if _has_duplicates(expected):
        return True
    if _has_duplicates(completed):
        return True
    return set(expected) != set(completed)


def _has_duplicates(clients: tuple[ClientId, ...]) -> bool:
    return len(set(clients)) != len(clients)


def _validated_client(update: ClientModelUpdate, round_number: RoundNumber) -> ClientId:
    if type(update.client_id) is not ClientId:
        raise _malformed_update(ClientId(value="malformed-client"), round_number, "invalid client identity")
    return update.client_id


def _validate_sample_count(update: ClientModelUpdate, client: ClientId, round_number: RoundNumber) -> None:
    if type(update.sample_count) is not int or update.sample_count <= 0:
        raise _malformed_update(client, round_number, "non-positive sample count")


def _validate_tensor_collection(update: ClientModelUpdate, client: ClientId, round_number: RoundNumber) -> None:
    if type(update.tensors) is not tuple or not update.tensors:
        raise _malformed_update(client, round_number, "empty tensor collection")
    for tensor in update.tensors:
        if type(tensor) is not Tensor:
            raise _malformed_update(client, round_number, "non-tensor update value")


def _validate_tensor_values(update: ClientModelUpdate, client: ClientId, round_number: RoundNumber) -> None:
    for tensor in update.tensors:
        if not torch.isfinite(tensor).all().item():
            raise NonFiniteClientUpdateError(
                detail="client update contains a non-finite tensor value",
                round_number=round_number.value,
                client=client.value,
                update_evidence="non-finite tensor",
            )


def _validate_matching_shapes(updates: tuple[ClientModelUpdate, ...], round_number: RoundNumber) -> None:
    reference_shapes = tuple(tensor.shape for tensor in updates[0].tensors)
    for update in updates[1:]:
        if tuple(tensor.shape for tensor in update.tensors) != reference_shapes:
            raise ClientShapeMismatchError(
                detail="client update tensor shapes do not match the round reference",
                round_number=round_number.value,
                client=update.client_id.value,
                update_evidence="shape mismatch",
            )


def _round_aborted(expected: tuple[ClientId, ...], completed: tuple[ClientId, ...]) -> RoundAbortedError:
    return RoundAbortedError(
        detail="full participation requires exactly one valid update from every expected client",
        expected_roster=repr(tuple(client.value for client in expected)),
        completed_roster=repr(tuple(client.value for client in completed)),
        failed_roster=repr(tuple(client.value for client in expected if client not in completed)),
    )


def _malformed_update(client: ClientId, round_number: RoundNumber, evidence: str) -> MalformedClientUpdateError:
    return MalformedClientUpdateError(
        detail="client update is malformed",
        round_number=round_number.value,
        client=client.value,
        update_evidence=evidence,
    )
