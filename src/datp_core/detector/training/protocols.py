from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CentralizedModelId,
    OptimizerId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    BatchSize,
    DataLoaderWorkerCount,
    DittoRegularization,
    FeatureCount,
    LearningRate,
    LocalEpochCount,
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    Ratio,
    WeightDecay,
)
from datp_core.detector.training import contracts as training_contracts

FEDAVG_LOCAL_EPOCHS = LocalEpochCount(1)
FEDAVG_LOCAL_FINE_TUNING_EPOCHS = LocalEpochCount(10)
ANCHOR_LOCAL_EPOCHS = LocalEpochCount(5)
DECLARED_FEDAVG_LOCAL_EPOCHS = frozenset({FEDAVG_LOCAL_EPOCHS, ANCHOR_LOCAL_EPOCHS})
FEDPROX_COEFFICIENTS = tuple(ProximalCoefficient(value) for value in (0.001, 0.01, 0.1, 1.0))
DITTO_RETAINED_EFFECT_MINIMUM = Ratio(0.75)
DITTO_PARTIAL_EFFECT_MINIMUM = Ratio(0.25)
DITTO_ALTERNATIVE_ROUTE_DIFFERENCE = MetricValue(0.05)
MODEL_ABSORPTION_DECISION_PROTOCOL = training_contracts.ModelAbsorptionDecisionProtocol(
    full_retention_minimum=DITTO_RETAINED_EFFECT_MINIMUM,
    partial_retention_minimum=DITTO_PARTIAL_EFFECT_MINIMUM,
)
NBAIOT_AUTOENCODER = training_contracts.AutoencoderProtocol(
    widths=training_contracts.AutoencoderArchitecture(
        tuple(FeatureCount(value) for value in (115, 86, 58, 38, 29, 38, 58, 86, 115))
    )
)
ANCHOR_NBAIOT_AUTOENCODER = training_contracts.AutoencoderProtocol(
    widths=training_contracts.AutoencoderArchitecture(
        tuple(FeatureCount(value) for value in (115, 80, 40, 20, 40, 80, 115))
    )
)
EDGE_IIOTSET_NUMERIC_AUTOENCODER = training_contracts.AutoencoderProtocol(
    widths=training_contracts.AutoencoderArchitecture(
        tuple(FeatureCount(value) for value in (33, 25, 17, 11, 8, 11, 17, 25, 33))
    )
)
CICIOT2023_AUTOENCODER = training_contracts.AutoencoderProtocol(
    widths=training_contracts.AutoencoderArchitecture(
        tuple(FeatureCount(value) for value in (39, 29, 20, 13, 10, 13, 20, 29, 39))
    )
)
WEIGHT_DECAY = WeightDecay(0.0)
OPTIMIZER = training_contracts.OptimizerProtocol(
    identity=OptimizerId.ADAM,
    weight_decay=WEIGHT_DECAY,
)
LEARNING_RATE = LearningRate(0.001)
ANCHOR_BATCH_SIZE = BatchSize(256)
BATCH_SIZE = BatchSize(8192)
CENTRALIZED_DATALOADER_WORKER_COUNT = DataLoaderWorkerCount(0)
DITTO_REGULARIZATION_GRID = tuple(DittoRegularization(value) for value in (0.1, 1.0, 2.0))
DITTO_PRIMARY_REGULARIZATION = DittoRegularization(1.0)
CENTRALIZED_TRAINING_PROTOCOL = training_contracts.CentralizedTrainingProtocol(
    kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    optimizer=OPTIMIZER,
)
FEDAVG_TRAINING_PROTOCOL = training_contracts.FedAvgProtocol(
    kind=TrainingModelId.FEDAVG_AUTOENCODER,
    local_epochs=FEDAVG_LOCAL_EPOCHS,
    optimizer=OPTIMIZER,
)
FEDAVG_LOCAL_FINE_TUNING_PROTOCOL = training_contracts.FedAvgLocalFineTuningProtocol(
    source_model=TrainingModelId.FEDAVG_AUTOENCODER,
    local_epochs=FEDAVG_LOCAL_FINE_TUNING_EPOCHS,
    optimizer=OPTIMIZER,
)
ANCHOR_FEDAVG_TRAINING_PROTOCOL = training_contracts.FedAvgProtocol(
    kind=TrainingModelId.FEDAVG_AUTOENCODER,
    local_epochs=ANCHOR_LOCAL_EPOCHS,
    optimizer=OPTIMIZER,
)
FEDPROX_TRAINING_PROTOCOLS = tuple(
    training_contracts.FedProxProtocol(
        kind=TrainingModelId.FEDPROX_AUTOENCODER,
        local_epochs=FEDAVG_LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        coefficient=coefficient,
    )
    for coefficient in FEDPROX_COEFFICIENTS
)
DITTO_TRAINING_PROTOCOLS = tuple(
    training_contracts.DittoProtocol(
        kind=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        local_epochs=FEDAVG_LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        regularization=regularization,
    )
    for regularization in DITTO_REGULARIZATION_GRID
)


def resolve_fedprox_protocol(
    coefficient: ModelCoefficientValue | ProximalCoefficient,
) -> training_contracts.FedProxProtocol:
    matches = tuple(
        protocol for protocol in FEDPROX_TRAINING_PROTOCOLS if protocol.coefficient.value == coefficient.value
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage("a FedProx coefficient must resolve to exactly one declared training protocol"),
            subject=TrainingModelId.FEDPROX_AUTOENCODER,
        )
    return matches[0]


def resolve_ditto_protocol(regularization: DittoRegularization) -> training_contracts.DittoProtocol:
    matches = tuple(
        protocol for protocol in DITTO_TRAINING_PROTOCOLS if protocol.regularization.value == regularization.value
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage("a Ditto regularization value must resolve to exactly one declared training protocol"),
            subject=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        )
    return matches[0]


def resolve_single_model_federated_training_protocol(
    *,
    model: TrainingModelId,
    coefficient: ModelCoefficientValue | ProximalCoefficient | DittoRegularization | None,
) -> training_contracts.FedAvgProtocol | training_contracts.FedProxProtocol:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError(
                    ErrorMessage("FedAvg must not declare a model coefficient"),
                    subject=model,
                )
            return FEDAVG_TRAINING_PROTOCOL
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if coefficient is None or isinstance(coefficient, DittoRegularization):
                raise ScientificContractError(
                    ErrorMessage("FedProx requires a declared proximal coefficient"),
                    subject=model,
                )
            return resolve_fedprox_protocol(coefficient)
        case TrainingModelId.FEDAVG_LOCAL_FINE_TUNING:
            raise ScientificContractError(
                ErrorMessage("local fine-tuning requires its dedicated post-training execution route"),
                subject=model,
            )
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("Ditto requires its related global and personalized execution route"),
                subject=model,
            )
