from collections.abc import Mapping
from dataclasses import dataclass, field

import torch
from torch import Tensor

from datp_core.application.ports.learning import TrainFederatedModelRequest
from datp_core.domain.errors import DomainValidationError, TrainingError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.training import TrainingSpec
from datp_core.domain.runtime.seeds import RoundNumber
from datp_core.infrastructure.learning.federation.trainer import (
    ClientModelUpdate,
    FederatedRoundUpdates,
    weighted_fedavg,
)
from datp_core.infrastructure.learning.models.anchor_training import build_anchor_optimizer
from datp_core.infrastructure.learning.models.autoencoder import FixedAutoencoder, build_fixed_autoencoder


def _local_epoch(
    *, model: FixedAutoencoder, optimizer: torch.optim.Optimizer, batch: Tensor, training: TrainingSpec
) -> None:
    micro_batch_size = training.training_batch.micro_batch_size.value
    accumulation_steps = training.training_batch.gradient_accumulation_steps.value
    optimizer.zero_grad()
    pending_steps = 0
    for start in range(0, batch.shape[0], micro_batch_size):
        micro_batch = batch[start : start + micro_batch_size]
        reconstruction = model(micro_batch)
        loss = ((reconstruction - micro_batch) ** 2).mean(dim=1).mean() / accumulation_steps
        loss.backward()
        pending_steps += 1
        if pending_steps == accumulation_steps:
            optimizer.step()
            optimizer.zero_grad()
            pending_steps = 0
    if pending_steps > 0:
        optimizer.step()
        optimizer.zero_grad()


def _client_update(
    *, client_id: ClientId, global_model: FixedAutoencoder, batch: Tensor, training: TrainingSpec
) -> ClientModelUpdate:
    client_model = FixedAutoencoder(training.autoencoder).to(batch.device)
    client_model.load_state_dict(global_model.state_dict())
    optimizer = build_anchor_optimizer(model=client_model, training=training)
    _local_epoch(model=client_model, optimizer=optimizer, batch=batch, training=training)
    tensors = tuple(parameter.detach().clone() for parameter in client_model.parameters())
    return ClientModelUpdate(client_id=client_id, tensors=tensors, sample_count=batch.shape[0])


def _client_batch_sort_key(entry: tuple[ClientId, Tensor]) -> str:
    client_id, _ = entry
    if type(client_id) is not ClientId:
        raise DomainValidationError(
            detail="anchor federated execution requires typed client identifiers",
            value=repr(client_id),
            constraint="ClientId",
        )
    return client_id.value


def _validate_client_batch(*, client_id: ClientId, batch: Tensor) -> None:
    if type(batch) is not Tensor:
        raise DomainValidationError(
            detail="anchor federated execution requires tensor batches",
            value=repr(type(batch)),
            constraint="Tensor[N, features]",
        )
    if batch.ndim != 2 or batch.shape[0] <= 0:
        raise DomainValidationError(
            detail="anchor federated execution requires non-empty two-dimensional tensor batches",
            value=repr((client_id, batch.shape)),
            constraint="non-empty Tensor[N, features]",
        )


def _validate_client_batch_device(*, expected_device: torch.device, batch: Tensor) -> None:
    if batch.device != expected_device:
        raise DomainValidationError(
            detail="all anchor client batches must use the same device",
            value=repr((expected_device, batch.device)),
            constraint="one execution device per round",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorGlobalParameters:
    tensors: tuple[Tensor, ...]


@dataclass(slots=True)
class AnchorFederatedRoundExecutor:
    client_batches: Mapping[ClientId, Tensor]
    initial_parameters: AnchorGlobalParameters | None = None
    _client_batches: tuple[tuple[ClientId, Tensor], ...] = field(init=False)
    _global_model: FixedAutoencoder | None = field(default=None, init=False)
    _last_executed_round: RoundNumber | None = field(default=None, init=False)
    _training: TrainingSpec | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._client_batches = tuple(sorted(self.client_batches.items(), key=_client_batch_sort_key))

    def execute(self, request: TrainFederatedModelRequest, round_number: RoundNumber) -> FederatedRoundUpdates:
        client_batches = self._ordered_client_batches()
        self._validate_round_sequence(round_number=round_number, training=request.training)
        global_model = self._current_global_model(training=request.training, device=client_batches[0][1].device)
        updates = tuple(
            _client_update(
                client_id=client_id,
                global_model=global_model,
                batch=batch,
                training=request.training,
            )
            for client_id, batch in client_batches
        )
        self._advance_global_model(model=global_model, updates=updates)
        self._last_executed_round = round_number
        return FederatedRoundUpdates(
            expected_clients=tuple(client_id for client_id, _ in client_batches),
            updates=updates,
        )

    def _ordered_client_batches(self) -> tuple[tuple[ClientId, Tensor], ...]:
        entries = self._client_batches
        if not entries:
            raise DomainValidationError(
                detail="anchor federated execution requires at least one client batch",
                value="()",
                constraint="non-empty client batches",
            )
        device = entries[0][1].device
        for client_id, batch in entries:
            _validate_client_batch(client_id=client_id, batch=batch)
            _validate_client_batch_device(expected_device=device, batch=batch)
        return entries

    def _validate_round_sequence(self, *, round_number: RoundNumber, training: TrainingSpec) -> None:
        if self._training is None:
            self._training = training
        elif training != self._training:
            raise TrainingError(
                detail="anchor federated execution cannot change the training specification between rounds",
                seed=training.seed.value,
                round_number=round_number.value,
            )
        if self._last_executed_round is None or round_number.value == self._last_executed_round.value + 1:
            return
        raise TrainingError(
            detail="anchor federated rounds must advance sequentially",
            seed=training.seed.value,
            round_number=round_number.value,
        )

    def _current_global_model(self, *, training: TrainingSpec, device: torch.device) -> FixedAutoencoder:
        if self._global_model is None:
            model = build_fixed_autoencoder(
                specification=training.autoencoder,
                initialization_seed=training.seed,
            ).to(device)
            if self.initial_parameters is not None:
                if len(model.state_dict()) != len(self.initial_parameters.tensors):
                    raise TrainingError(
                        detail="resumed anchor parameters do not match the fixed autoencoder state",
                        seed=training.seed.value,
                        round_number=0,
                    )
                with torch.no_grad():
                    for parameter, value in zip(model.parameters(), self.initial_parameters.tensors, strict=True):
                        parameter.copy_(value)
            self._global_model = model
        elif next(self._global_model.parameters()).device != device:
            raise TrainingError(
                detail="anchor federated execution cannot change device after training starts",
                seed=training.seed.value,
                round_number=self._last_executed_round.value if self._last_executed_round is not None else 0,
            )
        return self._global_model

    def _advance_global_model(self, *, model: FixedAutoencoder, updates: tuple[ClientModelUpdate, ...]) -> None:
        aggregated = weighted_fedavg(updates)
        with torch.no_grad():
            for parameter, value in zip(model.parameters(), aggregated, strict=True):
                parameter.copy_(value)

    def current_global_parameters(self) -> AnchorGlobalParameters:
        if self._global_model is None:
            raise DomainValidationError(
                detail="current_global_parameters requires at least one executed round",
                value="no round has been executed",
                constraint="execute() called at least once",
            )
        return AnchorGlobalParameters(
            tensors=tuple(parameter.detach().clone() for parameter in self._global_model.parameters())
        )
