"""Typed paired-contrast identities and supplementary analysis plans."""

from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.values.counts import PairedObservationCount, Seed
from datp_core.domain.values.ratios import DittoRegularization, MetricValue, ProximalCoefficient, Ratio
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.protocols.seeds import SeedCohort
from datp_core.protocols.statistics import PairedInferenceProtocol

type MetricSeries = tuple[MetricValue, ...]


class PairedDifferenceCounts(StrictModel):
    positive: PairedObservationCount
    zero: PairedObservationCount
    negative: PairedObservationCount

    @property
    def total(self) -> PairedObservationCount:
        return PairedObservationCount(self.positive.value + self.zero.value + self.negative.value)

    @property
    def positive_proportion(self) -> Ratio | None:
        return Ratio(self.positive.value / self.total.value) if self.total.value else None


class FederatedDesignIdentity(StrictModel):
    """Seed-independent detector design fixed across paired contrasts."""

    population: PopulationId
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None

    @classmethod
    def from_coordinate(
        cls,
        coordinate: FederatedTrainingCoordinate,
    ) -> "FederatedDesignIdentity":
        return cls(
            population=coordinate.population,
            split_protocol=coordinate.split_protocol,
            preprocessing_identity=coordinate.preprocessing_identity,
            model=coordinate.model,
            model_coefficient=coordinate.model_coefficient,
        )


class PairedContrast(StrictModel):
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue

    @model_validator(mode="after")
    def validate_distinct_methods(self) -> "PairedContrast":
        if self.left_method is self.right_method:
            raise ValueError("paired contrast requires two distinct threshold methods")
        return self

    @property
    def seed(self) -> Seed:
        return self.coordinate.training_seed

    @property
    def design(self) -> FederatedDesignIdentity:
        return FederatedDesignIdentity.from_coordinate(self.coordinate)

    @property
    def delta(self) -> MetricValue:
        return MetricValue(self.left_value.value - self.right_value.value)


type PairedContrasts = tuple[PairedContrast, ...]


class SupplementaryPairedAnalysisPlan(StrictModel):
    population: PopulationId
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    seed_cohort: SeedCohort
    inference_protocol: PairedInferenceProtocol

    @model_validator(mode="after")
    def validate_plan(self) -> "SupplementaryPairedAnalysisPlan":
        if self.evidence_role not in {
            EvidenceRole.EXTERNAL_VALIDATION,
            EvidenceRole.APPLICABILITY_BOUNDARY,
            EvidenceRole.TEMPORAL_BOUNDARY,
        }:
            raise ValueError("supplementary paired analysis requires non-confirmatory evidence")
        if self.left_method is self.right_method:
            raise ValueError("supplementary paired analysis requires two distinct threshold methods")
        if self.seed_cohort != self.inference_protocol.seed_cohort:
            raise ValueError("supplementary plan and inference protocol must share one seed cohort")
        return self
