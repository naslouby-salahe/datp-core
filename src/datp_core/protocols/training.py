"""Training declarations and authoritative protocol resolution."""

from collections.abc import Sequence

from datp_core.domain.enums import (
    CentralizedModelId,
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    OptimizerId,
    TrainingModelId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    DataLoaderWorkerCount,
    DittoRegularization,
    LearningRate,
    LocalEpochCount,
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    Ratio,
    RoundNumber,
    WeightDecay,
)

from .models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)

CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)),
    maximum_round=RoundNumber(200),
)
CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND


def require_non_test_checkpoint_selection_inputs(
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None,
    attack_labels_present: bool,
    branch_label: str,
) -> None:
    """Reject test leakage and unsupported selection rules before branch-specific selection."""
    if held_out_metrics is not None:
        raise LeakageError(
            f"held-out evaluation outcomes cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            f"attack labels cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
        raise ScientificContractError(
            f"unsupported {branch_label} checkpoint selection rule",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )


def fixed_terminal_checkpoint_status(
    round_number: RoundNumber,
    maximum_round: RoundNumber,
) -> CheckpointStatus:
    """Map a candidate round onto FIXED_TERMINAL_MAXIMUM_ROUND statuses."""
    if round_number == maximum_round:
        return CheckpointStatus.SELECTED_BY_NON_TEST_RULE
    return CheckpointStatus.STABILITY_EVIDENCE


FEDAVG_LOCAL_EPOCHS = LocalEpochCount(1)
FEDPROX_COEFFICIENTS = tuple(ProximalCoefficient(value) for value in (0.001, 0.01, 0.1, 1.0))
DITTO_RETAINED_EFFECT_MINIMUM = Ratio(0.75)
DITTO_PARTIAL_EFFECT_MINIMUM = Ratio(0.25)
DITTO_ALTERNATIVE_ROUTE_DIFFERENCE = MetricValue(0.05)
NBAIOT_AUTOENCODER = AutoencoderProtocol(widths=(115, 86, 58, 38, 29, 38, 58, 86, 115))
EDGE_IIOTSET_NUMERIC_AUTOENCODER = AutoencoderProtocol(widths=(33, 25, 17, 11, 8, 11, 17, 25, 33))
WEIGHT_DECAY = WeightDecay(0.0)
OPTIMIZER = OptimizerProtocol(identity=OptimizerId.ADAM, weight_decay=WEIGHT_DECAY)
LEARNING_RATE = LearningRate(0.001)
BATCH_SIZE = BatchSize(256)
CENTRALIZED_DATALOADER_WORKER_COUNT = DataLoaderWorkerCount(0)
FEDERATED_DATALOADER_WORKER_COUNT = DataLoaderWorkerCount(0)
DITTO_REGULARIZATION_GRID = tuple(DittoRegularization(value) for value in (0.05, 0.1, 0.2))
DITTO_PRIMARY_REGULARIZATION = DittoRegularization(0.1)
CENTRALIZED_TRAINING_PROTOCOL = CentralizedTrainingProtocol(
    kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    optimizer=OPTIMIZER,
)
FEDAVG_TRAINING_PROTOCOL = FedAvgProtocol(
    kind=TrainingModelId.FEDAVG_AUTOENCODER,
    local_epochs=FEDAVG_LOCAL_EPOCHS,
    optimizer=OPTIMIZER,
)
FEDPROX_TRAINING_PROTOCOLS = tuple(
    FedProxProtocol(
        kind=TrainingModelId.FEDPROX_AUTOENCODER,
        local_epochs=FEDAVG_LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        coefficient=coefficient,
    )
    for coefficient in FEDPROX_COEFFICIENTS
)
DITTO_TRAINING_PROTOCOLS = tuple(
    DittoProtocol(
        kind=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        local_epochs=FEDAVG_LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        regularization=regularization,
    )
    for regularization in DITTO_REGULARIZATION_GRID
)


def resolve_fedprox_protocol(coefficient: ModelCoefficientValue | ProximalCoefficient) -> FedProxProtocol:
    matches = tuple(
        protocol for protocol in FEDPROX_TRAINING_PROTOCOLS if protocol.coefficient.value == coefficient.value
    )
    if len(matches) != 1:
        raise ScientificContractError(
            "a FedProx coefficient must resolve to exactly one declared training protocol",
            subject=TrainingModelId.FEDPROX_AUTOENCODER,
        )
    return matches[0]


def resolve_ditto_protocol(regularization: DittoRegularization) -> DittoProtocol:
    matches = tuple(
        protocol for protocol in DITTO_TRAINING_PROTOCOLS if protocol.regularization.value == regularization.value
    )
    if len(matches) != 1:
        raise ScientificContractError(
            "a Ditto regularization value must resolve to exactly one declared training protocol",
            subject=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        )
    return matches[0]


def resolve_single_model_federated_training_protocol(
    *,
    model: TrainingModelId,
    coefficient: ModelCoefficientValue | ProximalCoefficient | DittoRegularization | None,
) -> FedAvgProtocol | FedProxProtocol:
    """Resolve the only supported single-model federated training protocol for a typed identity."""
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError(
                    "FedAvg must not declare a model coefficient",
                    subject=model,
                )
            return FEDAVG_TRAINING_PROTOCOL
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if coefficient is None or isinstance(coefficient, DittoRegularization):
                raise ScientificContractError(
                    "FedProx requires a declared proximal coefficient",
                    subject=model,
                )
            return resolve_fedprox_protocol(coefficient)
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto requires its related global and personalized execution route",
                subject=model,
            )
