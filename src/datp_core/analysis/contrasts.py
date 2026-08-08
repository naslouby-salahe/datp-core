"""Typed paired-contrast identities and supplementary analysis plans."""

from pydantic import model_validator

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
from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import PairedObservationCount, Seed
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    AbsoluteTolerance,
    DittoRegularization,
    MetricValue,
    ProximalCoefficient,
    Ratio,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.fixed_score_validation import validate_fixed_score_controls
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.analysis.inference.wilcoxon import PairedInferenceProtocol
from datp_core.experiments.common.seeds import SeedCohort

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


class FixedScorePairProvenance(StrictModel):
    """Fixed-score invariants proven identical across paired threshold policies."""

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


def build_paired_contrast(
    *,
    left: FederatedEvaluationDocument,
    right: FederatedEvaluationDocument,
    metric: MetricId,
    left_value: MetricValue,
    right_value: MetricValue,
    evidence_role: EvidenceRole,
    auroc_absolute_tolerance: AbsoluteTolerance = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
) -> PairedContrast:
    """Build a typed paired contrast only after full fixed-score control validation."""
    if left.score_coordinate != right.score_coordinate:
        raise ScientificContractError("paired evaluation documents use different training coordinates")
    if left.threshold_method is right.threshold_method:
        raise ScientificContractError("paired evaluation documents require distinct threshold methods")
    if left.evidence_role is not evidence_role or right.evidence_role is not evidence_role:
        raise ScientificContractError("paired evaluation documents must share the requested evidence role")
    if left.split_manifest_checksum != right.split_manifest_checksum:
        raise ScientificContractError("paired evaluation documents use different split-manifest checksums")
    if (
        left.score_checkpoint_checksum != right.score_checkpoint_checksum
        or left.preprocessing_state_set_checksum != right.preprocessing_state_set_checksum
    ):
        raise ScientificContractError("paired evaluation documents use different detector or preprocessing state")
    validate_fixed_score_controls(
        left.fixed_score_evidence,
        right.fixed_score_evidence,
        auroc_absolute_tolerance=auroc_absolute_tolerance,
    )
    left_evidence = left.fixed_score_evidence
    return PairedContrast(
        coordinate=left.score_coordinate,
        evidence_role=evidence_role,
        metric=metric,
        left_method=left.threshold_method,
        right_method=right.threshold_method,
        left_value=left_value,
        right_value=right_value,
        fixed_score=FixedScorePairProvenance(
            model_checksum=left_evidence.detector.model_checksum,
            preprocessing_checksum=left_evidence.detector.preprocessing_checksum,
            selected_checkpoint_checksum=left_evidence.detector.selected_checkpoint_checksum,
            split_manifest_checksum=left.split_manifest_checksum,
            calibration_score_checksum=left_evidence.calibration.score_checksum,
            evaluation_score_checksum=left_evidence.evaluation.score_checksum,
            evaluation_label_checksum=left_evidence.evaluation.label_checksum,
            source_row_checksum=left_evidence.evaluation.source_row_checksum,
            score_order_checksum=left_evidence.evaluation.score_order_checksum,
            client_inventory_checksum=left_evidence.population.client_inventory_checksum,
            eligibility_cohort_checksum=left_evidence.population.eligibility_cohort_checksum,
        ),
    )
