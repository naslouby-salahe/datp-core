"""Typed paired-contrast identities for fixed-detector analyses."""

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    DittoRegularization,
    MetricValue,
    PairedObservationCount,
    ProximalCoefficient,
    Ratio,
    Seed,
)
from datp_core.detector.training.contracts import FederatedTrainingCoordinate

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
    population: PopulationId
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: TrainingModelId
    model_coefficient: ProximalCoefficient | DittoRegularization | None

    @classmethod
    def from_coordinate(cls, coordinate: FederatedTrainingCoordinate) -> "FederatedDesignIdentity":
        return cls(
            population=coordinate.population,
            split_protocol=coordinate.split_protocol,
            preprocessing_identity=coordinate.preprocessing_identity,
            model=coordinate.model,
            model_coefficient=coordinate.model_coefficient,
        )


class FixedScorePairProvenance(StrictModel):
    model_checksum: Checksum
    preprocessing_checksum: Checksum
    selected_checkpoint_checksum: Checksum
    split_manifest_checksum: Checksum
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum
    evaluation_label_checksum: Checksum
    source_row_checksum: Checksum
    score_order_checksum: Checksum
    client_inventory_checksum: Checksum
    eligibility_cohort_checksum: Checksum


class PairedContrast(StrictModel):
    coordinate: FederatedTrainingCoordinate
    evidence_role: EvidenceRole
    metric: MetricId
    left_method: FederatedThresholdMethod
    right_method: FederatedThresholdMethod
    left_value: MetricValue
    right_value: MetricValue
    fixed_score: FixedScorePairProvenance

    def model_post_init(self, _context: object) -> None:
        if self.left_method is self.right_method:
            raise ValueError("paired contrast requires two distinct threshold methods")

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


def paired_difference_counts(contrasts: PairedContrasts) -> PairedDifferenceCounts:
    positive = sum(contrast.delta.value > 0.0 for contrast in contrasts)
    negative = sum(contrast.delta.value < 0.0 for contrast in contrasts)
    zero = len(contrasts) - positive - negative
    return PairedDifferenceCounts(
        positive=PairedObservationCount(positive),
        zero=PairedObservationCount(zero),
        negative=PairedObservationCount(negative),
    )
