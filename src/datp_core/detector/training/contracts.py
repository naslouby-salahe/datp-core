"""Training declarations, protocol resolution, and typed federated coordinates."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol, overload

from pydantic import Field, model_validator

from datp_core.core.contracts import StrictModel, sequence_pydantic_schema, validate_non_empty_tuple
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    CentralizedModelId,
    ContractSubject,
    FedProxCoefficientSelectionRule,
    OptimizerId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
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
    Seed,
    WeightDecay,
    DirichletConcentration,
)
from datp_core.data.populations.contracts import ControlledPartitionKind


@dataclass(frozen=True, slots=True)
class AutoencoderArchitecture(Sequence[FeatureCount]):
    widths: tuple[FeatureCount, ...]

    def __post_init__(self) -> None:
        normalized = tuple(width if isinstance(width, FeatureCount) else FeatureCount(width) for width in self.widths)
        object.__setattr__(self, "widths", normalized)
        validate_non_empty_tuple(normalized, "autoencoder architecture")
        if len(normalized) < 2:
            raise ValueError("autoencoder architecture requires at least input and output layers")
        if normalized[0] != normalized[-1]:
            raise ValueError("autoencoder input and output widths must match")

    def __len__(self) -> int:
        return len(self.widths)

    @overload
    def __getitem__(self, index: int) -> FeatureCount: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[FeatureCount, ...]: ...

    def __getitem__(self, index: int | slice) -> FeatureCount | tuple[FeatureCount, ...]:
        return self.widths[index]

    @property
    def input_width(self) -> FeatureCount:
        return self.widths[0]

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: object) -> object:
        return sequence_pydantic_schema(cls, source_type, handler)


class AutoencoderProtocol(StrictModel):
    widths: AutoencoderArchitecture

    @model_validator(mode="after")
    def validate_widths(self) -> "AutoencoderProtocol":
        if self.widths.input_width.value < 1:
            raise ValueError("autoencoder input width must be positive")
        return self


class OptimizerProtocol(StrictModel):
    identity: OptimizerId
    weight_decay: WeightDecay


class FedAvgProtocol(StrictModel):
    kind: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol


class FedProxProtocol(StrictModel):
    kind: Literal[TrainingModelId.FEDPROX_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol
    coefficient: ProximalCoefficient


class DittoProtocol(StrictModel):
    kind: Literal[TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol
    regularization: DittoRegularization


TrainingProtocol = Annotated[FedAvgProtocol | FedProxProtocol | DittoProtocol, Field(discriminator="kind")]


class CentralizedTrainingProtocol(StrictModel):
    kind: Literal[CentralizedModelId.CENTRALIZED_AUTOENCODER]
    optimizer: OptimizerProtocol


class ModelAbsorptionDecisionProtocol(StrictModel):
    full_retention_minimum: Ratio
    partial_retention_minimum: Ratio

    @model_validator(mode="after")
    def validate_ordering(self) -> "ModelAbsorptionDecisionProtocol":
        if self.partial_retention_minimum.value >= self.full_retention_minimum.value:
            raise ValueError("partial retention minimum must be below the full retention minimum")
        return self


FEDAVG_LOCAL_EPOCHS = LocalEpochCount(1)
FEDPROX_COEFFICIENTS = tuple(ProximalCoefficient(value) for value in (0.001, 0.01, 0.1, 1.0))
FEDPROX_COEFFICIENT_SELECTION_RULE = FedProxCoefficientSelectionRule.FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS


def require_non_test_fedprox_coefficient_selection_inputs(
    *,
    selection_rule: FedProxCoefficientSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None,
    attack_labels_present: bool,
) -> None:
    if held_out_metrics is not None:
        raise LeakageError(
            "held-out evaluation outcomes cannot influence FedProx coefficient selection",
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            "attack labels cannot influence FedProx coefficient selection",
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule is not FEDPROX_COEFFICIENT_SELECTION_RULE:
        raise ScientificContractError(
            "unsupported FedProx coefficient selection rule",
            subject=ContractSubject.FEDPROX_COEFFICIENT_SELECTION_RULE,
        )


class FedProxCoefficientTrainingLossContract(Protocol):
    @property
    def coefficient(self) -> ProximalCoefficient: ...

    @property
    def mean_terminal_training_loss(self) -> MetricValue: ...


def select_primary_fedprox_coefficient[CandidateT: FedProxCoefficientTrainingLossContract](
    candidates: Sequence[CandidateT],
) -> CandidateT:
    observed = tuple(candidate.coefficient for candidate in candidates)
    if observed != FEDPROX_COEFFICIENTS:
        raise ScientificContractError(
            "FedProx coefficient candidates must equal the declared frozen grid",
            subject=ContractSubject.FEDPROX_COEFFICIENT_SELECTION_RULE,
        )
    return min(
        candidates,
        key=lambda candidate: (candidate.mean_terminal_training_loss.value, candidate.coefficient.value),
    )


DITTO_RETAINED_EFFECT_MINIMUM = Ratio(0.75)
DITTO_PARTIAL_EFFECT_MINIMUM = Ratio(0.25)
DITTO_ALTERNATIVE_ROUTE_DIFFERENCE = MetricValue(0.05)
MODEL_ABSORPTION_DECISION_PROTOCOL = ModelAbsorptionDecisionProtocol(
    full_retention_minimum=DITTO_RETAINED_EFFECT_MINIMUM,
    partial_retention_minimum=DITTO_PARTIAL_EFFECT_MINIMUM,
)
NBAIOT_AUTOENCODER = AutoencoderProtocol(
    widths=AutoencoderArchitecture(tuple(FeatureCount(value) for value in (115, 86, 58, 38, 29, 38, 58, 86, 115)))
)
EDGE_IIOTSET_NUMERIC_AUTOENCODER = AutoencoderProtocol(
    widths=AutoencoderArchitecture(tuple(FeatureCount(value) for value in (33, 25, 17, 11, 8, 11, 17, 25, 33)))
)
CICIOT2023_AUTOENCODER = AutoencoderProtocol(
    widths=AutoencoderArchitecture(tuple(FeatureCount(value) for value in (39, 29, 20, 13, 10, 13, 20, 29, 39)))
)
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
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError("FedAvg must not declare a model coefficient", subject=model)
            return FEDAVG_TRAINING_PROTOCOL
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if coefficient is None or isinstance(coefficient, DittoRegularization):
                raise ScientificContractError("FedProx requires a declared proximal coefficient", subject=model)
            return resolve_fedprox_protocol(coefficient)
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto requires its related global and personalized execution route",
                subject=model,
            )


def _require_model_coefficient(
    model: TrainingModelId,
    coefficient: ProximalCoefficient | DittoRegularization | None,
) -> None:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError(
                    "FedAvg coordinates carry no model coefficient", subject=ContractSubject.TRAINING
                )
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if not isinstance(coefficient, ProximalCoefficient):
                raise ScientificContractError(
                    "FedProx coordinates require a proximal coefficient", subject=ContractSubject.TRAINING
                )
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            if not isinstance(coefficient, DittoRegularization):
                raise ScientificContractError(
                    "Ditto coordinates require a personalization regularization value", subject=ContractSubject.TRAINING
                )
        case _:
            raise ScientificContractError(
                f"unsupported federated training model {model}", subject=ContractSubject.TRAINING
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingCoordinate:
    population: PopulationId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None
    controlled_partition_kind: ControlledPartitionKind | None = None
    dirichlet_concentration: DirichletConcentration | None = None

    def __post_init__(self) -> None:
        _require_model_coefficient(self.model, self.model_coefficient)
        if self.dirichlet_concentration is not None:
            if self.controlled_partition_kind is None:
                raise ScientificContractError(
                    "a Dirichlet concentration requires a controlled partition kind",
                    subject=ContractSubject.COORDINATE,
                )
            if self.controlled_partition_kind is ControlledPartitionKind.IID:
                raise ScientificContractError(
                    "IID controlled partitions must not carry a concentration",
                    subject=ContractSubject.COORDINATE,
                )
        elif self.controlled_partition_kind is ControlledPartitionKind.DIRICHLET:
            raise ScientificContractError(
                "Dirichlet controlled partitions require a concentration",
                subject=ContractSubject.COORDINATE,
            )
        if self.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS and self.controlled_partition_kind is None:
            raise ScientificContractError(
                "Dirichlet-client populations require an explicit controlled partition condition",
                subject=ContractSubject.COORDINATE,
            )

    def matches_ditto_peer(self, other: "FederatedTrainingCoordinate") -> bool:
        model_pair = (self.model, other.model)
        if model_pair not in {
            (TrainingModelId.DITTO_GLOBAL_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER),
            (TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER, TrainingModelId.DITTO_GLOBAL_AUTOENCODER),
        }:
            return False
        return (
            self.population == other.population
            and self.training_seed == other.training_seed
            and self.split_protocol == other.split_protocol
            and self.preprocessing_identity == other.preprocessing_identity
            and self.model_coefficient == other.model_coefficient
            and self.controlled_partition_kind == other.controlled_partition_kind
            and self.dirichlet_concentration == other.dirichlet_concentration
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoTrainingCoordinates:
    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate

    def __post_init__(self) -> None:
        if self.global_coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            raise ScientificContractError(
                "Ditto training coordinates require the global Ditto coordinate",
                subject=ContractSubject.COORDINATE,
            )
        if self.personalized_coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto training coordinates require the personalized Ditto coordinate",
                subject=ContractSubject.COORDINATE,
            )
        if not self.global_coordinate.matches_ditto_peer(self.personalized_coordinate):
            raise ScientificContractError(
                "Ditto global and personalized coordinates must share one experiment identity",
                subject=ContractSubject.COORDINATE,
            )

    @classmethod
    def create(
        cls,
        population: PopulationId,
        training_seed: Seed,
        split_protocol: SplitProtocolId,
        preprocessing_identity: PreprocessingProtocolId,
        regularization: DittoRegularization,
    ) -> "DittoTrainingCoordinates":
        return cls(
            global_coordinate=FederatedTrainingCoordinate(
                population=population,
                training_seed=training_seed,
                split_protocol=split_protocol,
                preprocessing_identity=preprocessing_identity,
                model=TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
                model_coefficient=regularization,
            ),
            personalized_coordinate=FederatedTrainingCoordinate(
                population=population,
                training_seed=training_seed,
                split_protocol=split_protocol,
                preprocessing_identity=preprocessing_identity,
                model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
                model_coefficient=regularization,
            ),
        )
