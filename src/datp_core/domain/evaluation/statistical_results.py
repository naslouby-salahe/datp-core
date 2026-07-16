from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import isfinite

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import AnchorReproductionFailure, DomainValidationError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.runtime.seeds import CONFIRMATORY_PAIRED_SEED_COUNT, SeedTuple
from datp_core.domain.thresholding.policies import DecimalValue, FiniteFloatValue


class StatisticalMethod(StrEnum):
    BCA_BOOTSTRAP = "bca_bootstrap"
    PERCENTILE_BOOTSTRAP = "percentile_bootstrap"
    WILCOXON_SIGNED_RANK = "wilcoxon_signed_rank"
    CLIFFS_DELTA = "cliffs_delta"
    SPEARMAN = "spearman"
    LINEAR_REGRESSION_R2 = "linear_regression_r2"


class ClaimOutcome(StrEnum):
    STRONG_POSITIVE = "strong_positive"
    WEAK_POSITIVE = "weak_positive"
    MIXED = "mixed"
    NULL = "null"
    OPPOSITE = "opposite"
    FEASIBILITY_REJECTION = "feasibility_rejection"
    SUPPRESSED = "suppressed"


class AbsorptionBand(StrEnum):
    STRONGLY_USEFUL = "strongly_useful"
    PARTIAL = "partial"
    LARGELY_ABSORBED = "largely_absorbed"
    ALTERNATIVE_PATH = "alternative_path"


class PairedDeltaDirection(StrEnum):
    B1_MINUS_B2 = "b1_minus_b2"


class AnchorMovementAssessment(StrEnum):
    NOT_MATERIAL_TOWARD_ZERO = "not_material_toward_zero"
    MATERIAL_TOWARD_ZERO = "material_toward_zero"


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class ConfidenceLevel(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) < value < Decimal(1):
            raise DomainValidationError(
                detail="confidence level must be strictly between zero and one",
                value=str(value),
                constraint="0 < confidence level < 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class StatisticalAnalysisSpec:
    method: StatisticalMethod
    confidence: ConfidenceLevel
    resamples: BootstrapResampleCount
    paired_seed_count: int

    def __post_init__(self) -> None:
        if (
            type(self.method) is not StatisticalMethod
            or type(self.confidence) is not ConfidenceLevel
            or type(self.resamples) is not BootstrapResampleCount
            or type(self.paired_seed_count) is not int
            or self.paired_seed_count < 1
        ):
            raise DomainValidationError(
                detail="statistical analysis requires typed method, confidence, resamples, and paired seed count",
                value=repr(self),
                constraint="typed procedure fields and paired_seed_count >= 1",
            )

    @property
    def is_confirmatory_locked(self) -> bool:
        return (
            self.method is StatisticalMethod.BCA_BOOTSTRAP
            and self.confidence == ConfidenceLevel(value=0.95)
            and self.paired_seed_count == CONFIRMATORY_PAIRED_SEED_COUNT
        )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class CoverageRatio(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) <= value <= Decimal(1):
            raise DomainValidationError(
                detail="coverage ratio must be between zero and one",
                value=str(value),
                constraint="0 <= coverage ratio <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class EligibilityCoverage(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) <= value <= Decimal(1):
            raise DomainValidationError(
                detail="eligibility coverage must be between zero and one",
                value=str(value),
                constraint="0 <= eligibility coverage <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class Probability(DecimalValue):
    def _validate(self, value: Decimal) -> None:
        if not Decimal(0) <= value <= Decimal(1):
            raise DomainValidationError(
                detail="probability must be between zero and one",
                value=str(value),
                constraint="0 <= probability <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class FalsePositiveRate(FiniteFloatValue):
    def _validate(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise DomainValidationError(
                detail="false positive rate must be between zero and one",
                value=str(value),
                constraint="0 <= false positive rate <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class TruePositiveRate(FiniteFloatValue):
    def _validate(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise DomainValidationError(
                detail="true positive rate must be between zero and one",
                value=str(value),
                constraint="0 <= true positive rate <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class AuRocScore(FiniteFloatValue):
    def _validate(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise DomainValidationError(
                detail="AUROC score must be between zero and one",
                value=str(value),
                constraint="0 <= AUROC score <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PairedDeltaResult:
    direction: PairedDeltaDirection
    per_seed_delta: tuple[float, ...]
    scope_identity: StageFingerprint

    def __post_init__(self) -> None:
        if (
            self.direction is not PairedDeltaDirection.B1_MINUS_B2
            or not self.per_seed_delta
            or any(not isfinite(value) for value in self.per_seed_delta)
            or type(self.scope_identity) is not StageFingerprint
        ):
            raise DomainValidationError(
                detail="paired delta requires finite B1 minus B2 values and typed scope",
                value=repr(self),
                constraint="locked B1_MINUS_B2 direction with non-empty finite values",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidBootstrapIntervalResult:
    method: StatisticalMethod
    point_estimate: float
    lower: float
    upper: float
    confidence: ConfidenceLevel
    resamples: BootstrapResampleCount

    def __post_init__(self) -> None:
        if (
            self.method is not StatisticalMethod.BCA_BOOTSTRAP
            or any(not isfinite(value) for value in (self.point_estimate, self.lower, self.upper))
            or self.lower > self.upper
            or type(self.confidence) is not ConfidenceLevel
            or type(self.resamples) is not BootstrapResampleCount
        ):
            raise DomainValidationError(
                detail="valid bootstrap interval must be a finite ordered BCa interval",
                value=repr(self),
                constraint="BCA bootstrap with finite lower <= upper",
            )

    @property
    def excludes_zero(self) -> bool:
        return self.upper < 0 or self.lower > 0

    @property
    def direction_positive(self) -> bool:
        return self.lower > 0


@dataclass(frozen=True, slots=True, kw_only=True)
class DegenerateBootstrapIntervalResult:
    method: StatisticalMethod
    sample_size: int
    degeneracy_reason: str
    attempted_resamples: BootstrapResampleCount
    available_point_estimate: float | None
    wording_outcome: ClaimOutcome

    def __post_init__(self) -> None:
        if not _is_valid_degenerate_bootstrap_interval(self):
            raise DomainValidationError(
                detail="degenerate bootstrap must persist typed BCa degeneracy evidence",
                value=repr(self),
                constraint="BCa degeneracy with sample evidence and wording outcome",
            )


def _is_valid_degenerate_bootstrap_interval(result: DegenerateBootstrapIntervalResult) -> bool:
    return all(
        (
            result.method is StatisticalMethod.BCA_BOOTSTRAP,
            _is_positive_integer(result.sample_size),
            _is_non_empty_string(result.degeneracy_reason),
            type(result.attempted_resamples) is BootstrapResampleCount,
            _is_optional_finite_float(result.available_point_estimate),
            type(result.wording_outcome) is ClaimOutcome,
        )
    )


def _is_positive_integer(value: int) -> bool:
    return type(value) is int and value >= 1


def _is_non_empty_string(value: str) -> bool:
    return type(value) is str and bool(value)


def _is_optional_finite_float(value: float | None) -> bool:
    return value is None or isfinite(value)


type BootstrapIntervalOutcome = ValidBootstrapIntervalResult | DegenerateBootstrapIntervalResult


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatoryAnalysisResult:
    paired: PairedDeltaResult
    interval: BootstrapIntervalOutcome

    @property
    def passes(self) -> bool:
        if isinstance(self.interval, ValidBootstrapIntervalResult):
            return self.interval.excludes_zero and self.interval.direction_positive
        return False


@dataclass(frozen=True, slots=True, kw_only=True)
class WilcoxonSignedRankResult:
    statistic: float
    p_value: float


@dataclass(frozen=True, slots=True, kw_only=True)
class CliffsDeltaResult:
    value: float


@dataclass(frozen=True, slots=True, kw_only=True)
class AbsorptionResult:
    delta_fedavg: float
    delta_personalized: float
    ratio: float
    band: AbsorptionBand


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryResult:
    frozen_cv: float
    recalibrated_cv: float
    recovery_ratio: float
    outcome: ClaimOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class SecondaryIntervalResult:
    interval: BootstrapIntervalOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class AbsorptionStatisticalResult:
    result: AbsorptionResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalStatisticalResult:
    result: TemporalRecoveryResult


type StatisticalAnalysisResult = (
    ConfirmatoryAnalysisResult | SecondaryIntervalResult | AbsorptionStatisticalResult | TemporalStatisticalResult
)


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class AnchorReferenceInterval:
    lower: float
    upper: float

    def __init__(self) -> None:
        object.__setattr__(self, "lower", 0.647)
        object.__setattr__(self, "upper", 0.769)

    @property
    def width(self) -> float:
        return self.upper - self.lower


@dataclass(frozen=True, slots=True, kw_only=True)
class AnchorReproductionGateSpec:
    seed_cohort: SeedTuple
    reference_interval: AnchorReferenceInterval

    def __post_init__(self) -> None:
        if not _is_valid_anchor_reproduction_gate(self):
            raise DomainValidationError(
                detail="anchor gate requires exactly five seeds and the immutable reference interval",
                value=repr(self),
                constraint="five-seed cohort and AnchorReferenceInterval",
            )

    @property
    def maximum_width(self) -> float:
        return self.reference_interval.width * 1.2


def _is_valid_anchor_reproduction_gate(specification: AnchorReproductionGateSpec) -> bool:
    return all(
        (
            type(specification.seed_cohort) is SeedTuple,
            len(specification.seed_cohort.values) == 5,
            type(specification.reference_interval) is AnchorReferenceInterval,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class PassedAnchorReproductionResult:
    reproduced_interval: ValidBootstrapIntervalResult
    movement_assessment: AnchorMovementAssessment


@dataclass(frozen=True, slots=True, kw_only=True)
class FailedAnchorReproductionResult:
    reproduced_interval: ValidBootstrapIntervalResult
    movement_assessment: AnchorMovementAssessment
    failure: AnchorReproductionFailure


type AnchorReproductionResult = PassedAnchorReproductionResult | FailedAnchorReproductionResult


def assess_anchor_reproduction(
    *,
    gate: AnchorReproductionGateSpec,
    reproduced_interval: ValidBootstrapIntervalResult,
    movement_assessment: AnchorMovementAssessment,
) -> AnchorReproductionResult:
    fails = (
        reproduced_interval.upper < gate.reference_interval.upper
        and movement_assessment is AnchorMovementAssessment.MATERIAL_TOWARD_ZERO
    ) or reproduced_interval.upper - reproduced_interval.lower > gate.maximum_width
    if not fails:
        return PassedAnchorReproductionResult(
            reproduced_interval=reproduced_interval, movement_assessment=movement_assessment
        )
    return FailedAnchorReproductionResult(
        reproduced_interval=reproduced_interval,
        movement_assessment=movement_assessment,
        failure=AnchorReproductionFailure(
            detail="anchor reproduction violates the movement or width gate",
            reference_interval=f"[{gate.reference_interval.lower}, {gate.reference_interval.upper}]",
            reproduced_interval=f"[{reproduced_interval.lower}, {reproduced_interval.upper}]",
        ),
    )
