"""FedProx aggregation-side heterogeneity stress test: proximal term toward the global state.

The primary FedProx coefficient selection rule is unresolved. Every declared positive
coefficient is trained independently and reported; no coefficient is promoted to
"primary" without a declared rule.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    ClientCount,
    LearningRate,
    ProximalCoefficient,
    Seed,
)
from datp_core.learning.federated.fedavg import (
    FederatedClientDataset,
    FederatedTrainingOutcome,
    _run_federated_training,
    validate_federated_training_request,
)
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol, FedProxProtocol


class FedProxPrimarySelectionStatus(StrEnum):
    UNRESOLVED_NO_SOURCE_BACKED_RULE = "unresolved_no_source_backed_rule"


@dataclass(frozen=True, slots=True)
class FedProxPrimarySelectionOutcome:
    status: FedProxPrimarySelectionStatus
    declared_coefficients: tuple[ProximalCoefficient, ...]
    detail: str


def fedprox_primary_selection_outcome(
    declared_coefficients: tuple[ProximalCoefficient, ...],
) -> FedProxPrimarySelectionOutcome:
    """Report the FedProx primary-coefficient gap rather than inventing a selection rule."""
    return FedProxPrimarySelectionOutcome(
        status=FedProxPrimarySelectionStatus.UNRESOLVED_NO_SOURCE_BACKED_RULE,
        declared_coefficients=declared_coefficients,
        detail=(
            "the pre-registered non-test rule for selecting one primary FedProx coefficient "
            "on Regime A is not declared in the scientific source of truth; the full grid "
            "remains trained and reportable, but no coefficient is promoted to primary"
        ),
    )


@dataclass(frozen=True, slots=True)
class FedProxTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[FederatedClientDataset, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path


def train_fedprox(request: FedProxTrainingRequest) -> FederatedTrainingOutcome:
    """Train one FedProx coefficient's model independently from the FedAvg core."""
    validate_federated_training_request(request, TrainingModelId.FEDPROX_AUTOENCODER)
    if request.coordinate.model_coefficient != request.training_protocol.coefficient:
        raise ScientificContractError(
            "FedProx coordinate coefficient must match the training protocol coefficient",
            subject=ContractSubject.COORDINATE,
        )
    return _run_federated_training(request, proximal_coefficient=request.training_protocol.coefficient)
