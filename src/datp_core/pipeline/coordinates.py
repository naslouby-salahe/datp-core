"""Complete scientific coordinate identity shared by pipeline lifecycle services."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import ModelCoefficientValue

_MODEL_COEFFICIENT_TRAINING_MODELS = frozenset(
    (TrainingModelId.FEDPROX_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)

_DITTO_TRAINING_MODELS = frozenset(
    (TrainingModelId.DITTO_GLOBAL_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)


class CoordinateIdentitySegment(StrEnum):
    NO_MODEL_COEFFICIENT = "no_model_coefficient"
    NON_TEMPORAL = "non_temporal"


class ExecutionRoute(StrEnum):
    """Execution mechanism required by one coordinate's scientific shape.

    `SINGLE_COORDINATE` is executed by `execution.execute_experiment` and
    `runner.StageRunner`. `TEMPORAL_PAIRED_EXECUTION` is executed by
    `temporal_evidence.run_temporal_future_pair`, while
    `DITTO_JOINT_PUBLICATION` is executed by
    `ditto_stress.run_ditto_stress_test_seed`. The joint routes preserve shared
    detector or related-model identities that cannot be represented safely by
    independent single-coordinate recipes.
    """

    SINGLE_COORDINATE = "single_coordinate"
    DITTO_JOINT_PUBLICATION = "ditto_joint_publication"
    TEMPORAL_PAIRED_EXECUTION = "temporal_paired_execution"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentCoordinate:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    dataset: DatasetId
    population: PopulationId
    training_model: TrainingModelId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_protocol: PreprocessingProtocolId
    model_coefficient: ModelCoefficientValue | None
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None

    def __post_init__(self) -> None:
        requires_coefficient = self.training_model in _MODEL_COEFFICIENT_TRAINING_MODELS
        if requires_coefficient and self.model_coefficient is None:
            raise ValueError("training models with a declared coefficient grid require a model coefficient")
        if not requires_coefficient and self.model_coefficient is not None:
            raise ValueError("a model coefficient is only active for training models with a declared coefficient grid")

    @property
    def stable_key(self) -> str:
        temporal = (
            self.temporal_state.value
            if self.temporal_state is not None
            else CoordinateIdentitySegment.NON_TEMPORAL.value
        )
        coefficient = (
            f"{self.model_coefficient.value}"
            if self.model_coefficient is not None
            else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
        )
        return "/".join(
            (
                self.experiment.value,
                self.evidence_role.value,
                self.dataset.value,
                self.population.value,
                self.training_model.value,
                str(self.training_seed.value),
                self.split_protocol.value,
                self.preprocessing_protocol.value,
                coefficient,
                self.threshold_method.value,
                self.metric.value,
                temporal,
            )
        )


def execution_route_for(coordinate: ExperimentCoordinate) -> ExecutionRoute:
    if coordinate.temporal_state is not None:
        return ExecutionRoute.TEMPORAL_PAIRED_EXECUTION
    if coordinate.training_model in _DITTO_TRAINING_MODELS:
        return ExecutionRoute.DITTO_JOINT_PUBLICATION
    return ExecutionRoute.SINGLE_COORDINATE
