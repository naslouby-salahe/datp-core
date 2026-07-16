from dataclasses import dataclass, field

import torch
from torch import Tensor

from datp_core.domain.errors import DomainValidationError, TrainingError
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.models.autoencoder import FixedAutoencoder, build_fixed_autoencoder
from datp_core.infrastructure.learning.models.nbaiot_anchor_training import (
    ANCHOR_AUTOENCODER_SPECIFICATION,
    build_anchor_optimizer,
)
from datp_core.infrastructure.learning.models.nbaiot_anchor_training import (
    anchor_training_spec as _b0_training_spec,
)


@dataclass(slots=True)
class CentralizedPooledBenignTrainingExecutor:
    comparator: CentralizedModelComparatorSpec
    seed: Seed
    _model: FixedAutoencoder | None = field(default=None, init=False)
    _optimizer: torch.optim.Optimizer | None = field(default=None, init=False)
    _last_completed_epoch: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if type(self.comparator) is not CentralizedModelComparatorSpec:
            raise DomainValidationError(
                detail="B0 centralized training requires a centralized comparator identity, never a FedAvg identity",
                value=repr(self.comparator),
                constraint="CentralizedModelComparatorSpec",
            )

    def execute(self, *, pooled_benign_batch: Tensor, epoch_number: int) -> None:
        if epoch_number != self._last_completed_epoch + 1:
            raise TrainingError(
                detail="B0 centralized training epochs must advance sequentially",
                seed=self.seed.value,
                round_number=epoch_number,
            )
        if pooled_benign_batch.ndim != 2 or pooled_benign_batch.shape[0] <= 0:
            raise DomainValidationError(
                detail="B0 centralized training requires a non-empty two-dimensional pooled benign batch",
                value=repr(pooled_benign_batch.shape),
                constraint="non-empty Tensor[N, features]",
            )
        model, optimizer = self._current_model_and_optimizer(device=pooled_benign_batch.device)
        model.train()
        optimizer.zero_grad()
        reconstruction = model(pooled_benign_batch)
        loss = ((reconstruction - pooled_benign_batch) ** 2).mean(dim=1).mean()
        loss.backward()
        optimizer.step()
        self._last_completed_epoch = epoch_number

    def _current_model_and_optimizer(self, *, device: torch.device) -> tuple[FixedAutoencoder, torch.optim.Optimizer]:
        if self._model is not None and self._optimizer is not None:
            if next(self._model.parameters()).device != device:
                raise TrainingError(
                    detail="B0 centralized training cannot change device after training starts",
                    seed=self.seed.value,
                    round_number=self._last_completed_epoch,
                )
            return self._model, self._optimizer
        training = _b0_training_spec(seed=self.seed)
        model = build_fixed_autoencoder(
            specification=ANCHOR_AUTOENCODER_SPECIFICATION, initialization_seed=self.seed
        ).to(device)
        optimizer = build_anchor_optimizer(model=model, training=training)
        self._model = model
        self._optimizer = optimizer
        return model, optimizer

    def current_parameters(self) -> tuple[Tensor, ...]:
        if self._model is None:
            raise DomainValidationError(
                detail="current_parameters requires at least one executed epoch",
                value="no epoch has been executed",
                constraint="execute() called at least once",
            )
        return tuple(parameter.detach().clone() for parameter in self._model.parameters())
