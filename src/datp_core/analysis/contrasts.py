from math import isclose
from typing import overload

from pydantic import model_validator

from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.fixed_score import FixedScoreEvidence
from datp_core.analysis.metrics.fixed_score_validation import validate_fixed_score_controls
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
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
from datp_core.experiments.common.seeds import SeedCohort

type MetricSeries = tuple[MetricValue, ...]

CONFIRMATORY_RELATIVE_CV_REDUCTION_CUTOFF = MetricValue(1e-12)


class ConfirmatoryDescriptiveEffect(StrictModel):
    seed: Seed
    shared_cv_fpr: MetricValue
    local_cv_fpr: MetricValue
    relative_cv_reduction: MetricValue | None
    delta_worst_fpr: MetricValue
    delta_iqr_fpr: MetricValue

    @model_validator(mode="after")
    def validate_relative_reduction(self) -> "ConfirmatoryDescriptiveEffect":
        if self.shared_cv_fpr.value <= CONFIRMATORY_RELATIVE_CV_REDUCTION_CUTOFF.value:
            if self.relative_cv_reduction is not None:
                raise ValueError("relative CV reduction is unavailable when shared CV(FPR) is near zero")
            return self
        if self.relative_cv_reduction is None:
            raise ValueError("relative CV reduction is required when shared CV(FPR) exceeds the cutoff")
        expected = (self.shared_cv_fpr.value - self.local_cv_fpr.value) / self.shared_cv_fpr.value
        if not isclose(self.relative_cv_reduction.value, expected, rel_tol=0.0, abs_tol=1e-15):
            raise ValueError("relative CV reduction must match the paired shared/local CV(FPR) values")
        return self


class ConfirmatoryDescriptiveEffects(StrictModel):
    values: tuple[ConfirmatoryDescriptiveEffect, ...]

    @model_validator(mode="after")
    def validate_unique_ordered_seeds(self) -> "ConfirmatoryDescriptiveEffects":
        seeds = tuple(effect.seed for effect in self.values)
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("confirmatory descriptive effects require one record per seed")
        if seeds != tuple(sorted(seeds, key=lambda seed: seed.value)):
            raise ValueError("confirmatory descriptive effects must be ordered by seed")
        return self


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
    fixed_score: FixedScoreEvidence

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


class PairedContrasts(StrictModel):
    values: tuple[PairedContrast, ...]

    @model_validator(mode="after")
    def validate_unique_seeds(self) -> "PairedContrasts":
        if len({contrast.seed for contrast in self.values}) != len(self.values):
            raise ValueError("paired contrasts require one observation per seed")
        return self

    def __bool__(self) -> bool:
        return bool(self.values)

    def __len__(self) -> int:
        return len(self.values)

    @overload
    def __getitem__(self, index: int) -> PairedContrast: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[PairedContrast, ...]: ...

    def __getitem__(self, index: int | slice) -> PairedContrast | tuple[PairedContrast, ...]:
        return self.values[index]

    @property
    def deltas(self) -> tuple[MetricValue, ...]:
        return tuple(contrast.delta for contrast in self.values)

    def ordered_by_seed(self) -> "PairedContrasts":
        return PairedContrasts(values=tuple(sorted(self.values, key=lambda contrast: contrast.seed.value)))


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
        if self.seed_cohort.member_count != self.inference_protocol.paired_seed_count:
            raise ValueError("supplementary plan and inference protocol must require the same seed count")
        return self


def build_paired_contrast(
    *,
    left: FederatedEvaluationDocument,
    right: FederatedEvaluationDocument,
    metric: MetricId,
    left_value: MetricValue,
    right_value: MetricValue,
    evidence_role: EvidenceRole,
) -> PairedContrast:
    if left.score_coordinate != right.score_coordinate:
        raise ScientificContractError(ErrorMessage("paired evaluation documents use different training coordinates"))
    if left.threshold_method is right.threshold_method:
        raise ScientificContractError(ErrorMessage("paired evaluation documents require distinct threshold methods"))
    if left.evidence_role is not evidence_role or right.evidence_role is not evidence_role:
        raise ScientificContractError(
            ErrorMessage("paired evaluation documents must share the requested evidence role")
        )
    validate_fixed_score_controls(left.fixed_score_evidence, right.fixed_score_evidence)
    left_evidence = left.fixed_score_evidence
    return PairedContrast(
        coordinate=left.score_coordinate,
        evidence_role=evidence_role,
        metric=metric,
        left_method=left.threshold_method,
        right_method=right.threshold_method,
        left_value=left_value,
        right_value=right_value,
        fixed_score=left_evidence,
    )
