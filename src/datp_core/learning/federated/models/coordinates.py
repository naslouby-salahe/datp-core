"""Typed federated training coordinate contracts."""

from dataclasses import dataclass

from datp_core.datasets.partitioning.contracts import ControlledPartitionKind
from datp_core.domain.enums import (
    ContractSubject,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import DirichletConcentration, DittoRegularization, ProximalCoefficient


def _require_model_coefficient(
    model: TrainingModelId,
    coefficient: ProximalCoefficient | DittoRegularization | None,
) -> None:
    match model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            valid = coefficient is None
            message = "FedAvg coordinates carry no model coefficient"
        case TrainingModelId.FEDPROX_AUTOENCODER:
            valid = isinstance(coefficient, ProximalCoefficient)
            message = "FedProx coordinates require a proximal coefficient"
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            valid = isinstance(coefficient, DittoRegularization)
            message = "Ditto coordinates require a personalization regularization value"
        case _:
            raise ScientificContractError(
                f"unsupported federated training model {model}",
                subject=ContractSubject.TRAINING,
            )
    if not valid:
        raise ScientificContractError(message, subject=ContractSubject.TRAINING)


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
        if self.controlled_partition_kind is ControlledPartitionKind.DIRICHLET and self.dirichlet_concentration is None:
            raise ScientificContractError(
                "Dirichlet controlled partitions require a concentration",
                subject=ContractSubject.COORDINATE,
            )
        if self.controlled_partition_kind is ControlledPartitionKind.IID and self.dirichlet_concentration is not None:
            raise ScientificContractError(
                "IID controlled partitions must not carry a concentration",
                subject=ContractSubject.COORDINATE,
            )
        if self.controlled_partition_kind is None and self.dirichlet_concentration is not None:
            raise ScientificContractError(
                "a Dirichlet concentration requires a controlled partition kind",
                subject=ContractSubject.COORDINATE,
            )
        if self.population is PopulationId.NBAIOT_DIRICHLET_CLIENTS and self.controlled_partition_kind is None:
            raise ScientificContractError(
                "Dirichlet-client populations require an explicit controlled partition condition",
                subject=ContractSubject.COORDINATE,
            )

    def matches_ditto_peer(self, other: "FederatedTrainingCoordinate") -> bool:
        return (
            self.population == other.population
            and self.training_seed == other.training_seed
            and self.split_protocol == other.split_protocol
            and self.preprocessing_identity == other.preprocessing_identity
            and self.model_coefficient == other.model_coefficient
            and self.controlled_partition_kind == other.controlled_partition_kind
            and self.dirichlet_concentration == other.dirichlet_concentration
            and {self.model, other.model}
            == {
                TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
                TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
            }
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoTrainingCoordinates:
    """The one global/personalized coordinate pair for a Ditto experiment identity."""

    global_coordinate: FederatedTrainingCoordinate
    personalized_coordinate: FederatedTrainingCoordinate

    def __post_init__(self) -> None:
        if self.global_coordinate.model is not TrainingModelId.DITTO_GLOBAL_AUTOENCODER:
            raise ScientificContractError(
                "Ditto training coordinates require the DITTO_GLOBAL_AUTOENCODER global coordinate",
                subject=ContractSubject.COORDINATE,
            )
        if self.personalized_coordinate.model is not TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto training coordinates require the DITTO_PERSONALIZED_AUTOENCODER personalized coordinate",
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
