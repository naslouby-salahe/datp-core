from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Literal, cast, overload

from pydantic import ConfigDict, Field, GetCoreSchemaHandler, model_validator

from datp_core.core.contracts import StrictModel, sequence_pydantic_schema, validate_non_empty_tuple
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CentralizedModelId,
    ContractSubject,
    OptimizerId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    DirichletConcentration,
    DittoRegularization,
    FeatureCount,
    LocalEpochCount,
    ProximalCoefficient,
    Ratio,
    Seed,
    WeightDecay,
)
from datp_core.data.populations.contracts import ControlledPartitionKind


@dataclass(frozen=True, slots=True)
class AutoencoderArchitecture(Sequence[FeatureCount]):
    widths: tuple[FeatureCount, ...]

    def __post_init__(self) -> None:
        raw_widths = cast(tuple[FeatureCount | int, ...], self.widths)
        normalized = tuple(width if isinstance(width, FeatureCount) else FeatureCount(width) for width in raw_widths)
        object.__setattr__(self, "widths", normalized)
        validate_non_empty_tuple(normalized, "autoencoder architecture")
        if len(normalized) < 2:
            raise ScientificContractError(
                ErrorMessage("autoencoder architecture requires at least input and output layers")
            )
        if normalized[0] != normalized[-1]:
            raise ScientificContractError(ErrorMessage("autoencoder input and output widths must match"))

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
    def __get_pydantic_core_schema__(
        cls,
        source_type: object,
        handler: GetCoreSchemaHandler,
    ) -> object:
        return sequence_pydantic_schema(cls, source_type, handler)


class AutoencoderProtocol(StrictModel):
    model_config = ConfigDict(revalidate_instances="never")
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


def _require_model_coefficient(
    model: TrainingModelId,
    coefficient: ProximalCoefficient | DittoRegularization | None,
) -> None:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            if coefficient is not None:
                raise ScientificContractError(
                    ErrorMessage("FedAvg coordinates carry no model coefficient"), subject=ContractSubject.TRAINING
                )
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if not isinstance(coefficient, ProximalCoefficient):
                raise ScientificContractError(
                    ErrorMessage("FedProx coordinates require a proximal coefficient"), subject=ContractSubject.TRAINING
                )
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            if not isinstance(coefficient, DittoRegularization):
                raise ScientificContractError(
                    ErrorMessage("Ditto coordinates require a personalization regularization value"),
                    subject=ContractSubject.TRAINING,
                )
        case _:
            raise ScientificContractError(
                ErrorMessage(f"unsupported federated training model {model}"), subject=ContractSubject.TRAINING
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
                    ErrorMessage("a Dirichlet concentration requires a controlled partition kind"),
                    subject=ContractSubject.COORDINATE,
                )
            if self.controlled_partition_kind is ControlledPartitionKind.IID:
                raise ScientificContractError(
                    ErrorMessage("IID controlled partitions must not carry a concentration"),
                    subject=ContractSubject.COORDINATE,
                )
        elif self.controlled_partition_kind is ControlledPartitionKind.DIRICHLET:
            raise ScientificContractError(
                ErrorMessage("Dirichlet controlled partitions require a concentration"),
                subject=ContractSubject.COORDINATE,
            )
        if self.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS and self.controlled_partition_kind is None:
            raise ScientificContractError(
                ErrorMessage("Dirichlet-client populations require an explicit controlled partition condition"),
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
                ErrorMessage("Ditto training coordinates require the global Ditto coordinate"),
                subject=ContractSubject.COORDINATE,
            )
        if self.personalized_coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("Ditto training coordinates require the personalized Ditto coordinate"),
                subject=ContractSubject.COORDINATE,
            )
        if not self.global_coordinate.matches_ditto_peer(self.personalized_coordinate):
            raise ScientificContractError(
                ErrorMessage("Ditto global and personalized coordinates must share one experiment identity"),
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
