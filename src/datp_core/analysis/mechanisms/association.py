from enum import StrEnum
from typing import ClassVar, cast

import numpy as np
from pydantic import model_validator
from scipy import stats

from datp_core.analysis.adapters.scipy import (
    LinearRegressionResult,
    StatisticPValueResult,
    linear_regression_values,
    statistic_p_value,
)
from datp_core.analysis.inference.wilcoxon import CorrelationCoefficient, PValue
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    PopulationId,
    RegimeLabel,
)
from datp_core.core.numeric import MetricValue, PairedObservationCount, Ratio, Seed, is_numeric_zero

MINIMUM_PUBLICATION_OBSERVATIONS = PairedObservationCount(5)
DEFAULT_ASSOCIATION_CONFIDENCE_LEVEL = Ratio(0.95)


class AssociationIssue(StrEnum):
    INSUFFICIENT_EVIDENCE = "association requires at least five observations for publication"
    NON_FINITE_OBSERVATION = "association observations must be finite"
    ZERO_HETEROGENEITY_VARIATION = "heterogeneity has zero variation"
    ZERO_BENEFIT_VARIATION = "benefit has zero variation"
    INVALID_STATISTICS = "statistics library returned invalid association values"

    @property
    def availability(self) -> AvailabilityStatus:
        if self in {
            AssociationIssue.ZERO_HETEROGENEITY_VARIATION,
            AssociationIssue.ZERO_BENEFIT_VARIATION,
        }:
            return AvailabilityStatus.UNDEFINED
        return AvailabilityStatus.UNAVAILABLE


class AssociationObservation(StrictModel):
    seed: Seed
    experiment: ExperimentId
    population: PopulationId
    regime_label: RegimeLabel
    heterogeneity: MetricValue
    benefit: MetricValue


class RegressionSlopeConfidenceInterval(StrictModel):
    lower_bound: MetricValue
    upper_bound: MetricValue

    @model_validator(mode="after")
    def validate_interval(self) -> "RegressionSlopeConfidenceInterval":
        if self.lower_bound.value > self.upper_bound.value:
            raise ValueError("regression slope confidence interval bounds are inverted")
        return self


class LeaveOneOutAssociationDiagnostics(StrictModel):
    slopes: tuple[MetricValue | None, ...]
    r_squared: tuple[Ratio | None, ...]
    influences: tuple[MetricValue | None, ...]
    unavailable_reasons: tuple[AnalysisReasonText | None, ...]


class AssociationStatistics(StrictModel):
    spearman_rho: CorrelationCoefficient
    spearman_p_value: PValue
    regression_intercept: MetricValue
    regression_slope: MetricValue
    regression_slope_standard_error: MetricValue
    regression_slope_confidence_interval: RegressionSlopeConfidenceInterval
    r_squared: Ratio
    leverage: tuple[Ratio, ...]
    leave_one_out_diagnostics: LeaveOneOutAssociationDiagnostics
    evidentiary_sufficient: bool


class AssociationResult(StrictModel):
    observations: tuple[AssociationObservation, ...]
    statistics: AssociationStatistics | None
    issue: AssociationIssue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "AssociationResult":
        if all(
            hasattr(item, field)
            for item in self.observations
            for field in ("seed", "experiment", "population", "regime_label")
        ):
            identities = tuple(
                (item.seed, item.experiment, item.population, item.regime_label)
                for item in self.observations
            )
            if len(identities) != len(frozenset(identities)):
                raise ValueError(
                    "association observations must be unique by seed, experiment, population, and regime"
                )
        if (self.statistics is None) == (self.issue is None):
            raise ValueError("association result requires either statistics or one issue")
        if self.statistics is not None:
            count = len(self.observations)
            if len(self.statistics.leverage) != count:
                raise ValueError("association leverage must cover every observation")
            if len(self.statistics.leave_one_out_diagnostics.slopes) != count:
                raise ValueError("association leave-one-out slopes must cover every observation")
            if len(self.statistics.leave_one_out_diagnostics.r_squared) != count:
                raise ValueError("association leave-one-out R² must cover every observation")
            if len(self.statistics.leave_one_out_diagnostics.influences) != count:
                raise ValueError("association influence must cover every observation")
            if len(self.statistics.leave_one_out_diagnostics.unavailable_reasons) != count:
                raise ValueError("association leave-one-out reasons must cover every observation")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        if self.issue is None:
            return AvailabilityStatus.AVAILABLE
        if self.statistics is not None and self.issue is AssociationIssue.INSUFFICIENT_EVIDENCE:
            return AvailabilityStatus.AVAILABLE
        return self.issue.availability

    @property
    def reason(self) -> AnalysisReasonText | None:
        return None if self.issue is None else AnalysisReasonText(self.issue.value)

    @property
    def observation_count(self) -> PairedObservationCount:
        return PairedObservationCount(len(self.observations))


def heterogeneity_benefit_association(
    observations: tuple[AssociationObservation, ...],
    *,
    confidence_level: Ratio = DEFAULT_ASSOCIATION_CONFIDENCE_LEVEL,
) -> AssociationResult:
    if len(observations) < MINIMUM_PUBLICATION_OBSERVATIONS.value:
        return _unavailable_association(
            observations,
            AssociationIssue.INSUFFICIENT_EVIDENCE,
        )
    x_values = np.fromiter(
        (item.heterogeneity.value for item in observations),
        dtype=np.float64,
    )
    y_values = np.fromiter(
        (item.benefit.value for item in observations),
        dtype=np.float64,
    )
    if not np.isfinite(x_values).all() or not np.isfinite(y_values).all():
        return _unavailable_association(
            observations,
            AssociationIssue.NON_FINITE_OBSERVATION,
        )
    if is_numeric_zero(float(np.ptp(x_values))):
        return _unavailable_association(
            observations,
            AssociationIssue.ZERO_HETEROGENEITY_VARIATION,
        )
    if is_numeric_zero(float(np.ptp(y_values))):
        return _unavailable_association(
            observations,
            AssociationIssue.ZERO_BENEFIT_VARIATION,
        )
    spearman = statistic_p_value(
        cast(
            StatisticPValueResult,
            stats.spearmanr(x_values, y_values, alternative="two-sided"),
        )
    )
    regression = linear_regression_values(
        cast(
            LinearRegressionResult,
            stats.linregress(x_values, y_values, alternative="two-sided"),
        )
    )
    if spearman is None or regression is None:
        return _unavailable_association(
            observations,
            AssociationIssue.INVALID_STATISTICS,
        )
    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = np.einsum("ij,ji->i", design, np.linalg.pinv(design))
    slope = regression.slope.value
    slope_se = regression.stderr.value
    alpha = 1.0 - confidence_level.value
    t_critical = float(stats.t.ppf(1.0 - alpha / 2.0, df=max(x_values.size - 2, 1)))
    loo = _leave_one_out(x_values, y_values, regression.slope)
    statistics = AssociationStatistics(
        spearman_rho=CorrelationCoefficient(spearman.statistic.value),
        spearman_p_value=PValue(spearman.p_value.value),
        regression_intercept=regression.intercept,
        regression_slope=regression.slope,
        regression_slope_standard_error=regression.stderr,
        regression_slope_confidence_interval=RegressionSlopeConfidenceInterval(
            lower_bound=MetricValue(slope - t_critical * slope_se),
            upper_bound=MetricValue(slope + t_critical * slope_se),
        ),
        r_squared=Ratio(regression.rvalue.value**2),
        leverage=tuple(Ratio(float(value)) for value in leverage),
        leave_one_out_diagnostics=loo,
        evidentiary_sufficient=True,
    )
    return AssociationResult(
        observations=observations,
        statistics=statistics,
        issue=None,
    )


def _leave_one_out(
    x_values: np.ndarray,
    y_values: np.ndarray,
    full_slope: MetricValue,
) -> LeaveOneOutAssociationDiagnostics:
    slopes: list[MetricValue | None] = []
    r_squared_values: list[Ratio | None] = []
    influences: list[MetricValue | None] = []
    unavailable_reasons: list[AnalysisReasonText | None] = []
    for index in range(x_values.size):
        mask = np.ones(x_values.size, dtype=bool)
        mask[index] = False
        x_loo = x_values[mask]
        y_loo = y_values[mask]
        if is_numeric_zero(float(np.ptp(x_loo))) or is_numeric_zero(float(np.ptp(y_loo))):
            slopes.append(None)
            r_squared_values.append(None)
            influences.append(None)
            unavailable_reasons.append(
                AnalysisReasonText("leave-one-out regression is undefined because an omitted sample removes variation")
            )
            continue
        fit = cast(
            LinearRegressionResult,
            stats.linregress(x_loo, y_loo, alternative="two-sided"),
        )
        extracted = linear_regression_values(fit)
        if extracted is None:
            slopes.append(None)
            r_squared_values.append(None)
            influences.append(None)
            unavailable_reasons.append(AnalysisReasonText("leave-one-out regression returned invalid statistics"))
            continue
        loo_slope = extracted.slope.value
        slopes.append(extracted.slope)
        r_squared_values.append(Ratio(extracted.rvalue.value**2))
        influences.append(MetricValue(full_slope.value - loo_slope))
        unavailable_reasons.append(None)
    return LeaveOneOutAssociationDiagnostics(
        slopes=tuple(slopes),
        r_squared=tuple(r_squared_values),
        influences=tuple(influences),
        unavailable_reasons=tuple(unavailable_reasons),
    )


def _unavailable_association(
    observations: tuple[AssociationObservation, ...],
    issue: AssociationIssue,
) -> AssociationResult:
    return AssociationResult(
        observations=observations,
        statistics=None,
        issue=issue,
    )
