"""Heterogeneity-benefit association mechanism evidence."""

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
from datp_core.core.numeric import MetricValue, PairedObservationCount, Ratio, Seed

MINIMUM_ASSOCIATION_OBSERVATIONS = PairedObservationCount(3)
MINIMUM_PUBLICATION_OBSERVATIONS = PairedObservationCount(5)
DEFAULT_ASSOCIATION_CONFIDENCE_LEVEL = Ratio(0.95)


class AssociationIssue(StrEnum):
    INSUFFICIENT_OBSERVATIONS = "association requires at least three observations"
    INSUFFICIENT_EVIDENCE = "association is mathematically computable but scientifically underpowered for publication"
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
        if self is AssociationIssue.INSUFFICIENT_EVIDENCE:
            return AvailabilityStatus.AVAILABLE
        return AvailabilityStatus.UNAVAILABLE


class AssociationObservation(StrictModel):
    seed: Seed
    experiment: ExperimentId
    population: PopulationId
    regime_label: RegimeLabel
    heterogeneity: MetricValue
    benefit: MetricValue


class AssociationStatistics(StrictModel):
    spearman_rho: CorrelationCoefficient
    spearman_p_value: PValue
    regression_intercept: MetricValue
    regression_slope: MetricValue
    regression_slope_standard_error: MetricValue
    regression_slope_confidence_interval: tuple[MetricValue, MetricValue]
    r_squared: Ratio
    leverage: tuple[Ratio, ...]
    leave_one_out_slopes: tuple[MetricValue, ...]
    leave_one_out_r_squared: tuple[Ratio, ...]
    influence: tuple[MetricValue, ...]
    evidentiary_sufficient: bool

    @model_validator(mode="after")
    def validate_statistics(self) -> "AssociationStatistics":
        lower, upper = self.regression_slope_confidence_interval
        if lower.value > upper.value:
            raise ValueError("regression slope confidence interval bounds are inverted")
        return self


class LeaveOneOutAssociationDiagnostics(StrictModel):
    slopes: tuple[MetricValue, ...]
    r_squared: tuple[Ratio, ...]
    influences: tuple[MetricValue, ...]


class AssociationResult(StrictModel):
    observations: tuple[AssociationObservation, ...]
    statistics: AssociationStatistics | None
    issue: AssociationIssue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "AssociationResult":
        if (self.statistics is None) == (self.issue is None):
            if not (self.statistics is not None and self.issue is AssociationIssue.INSUFFICIENT_EVIDENCE):
                raise ValueError("association result requires either statistics or one issue")
        if self.statistics is not None:
            count = len(self.observations)
            if len(self.statistics.leverage) != count:
                raise ValueError("association leverage must cover every observation")
            if len(self.statistics.leave_one_out_slopes) != count:
                raise ValueError("association leave-one-out slopes must cover every observation")
            if len(self.statistics.leave_one_out_r_squared) != count:
                raise ValueError("association leave-one-out R² must cover every observation")
            if len(self.statistics.influence) != count:
                raise ValueError("association influence must cover every observation")
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
    if len(observations) < MINIMUM_ASSOCIATION_OBSERVATIONS.value:
        return _unavailable_association(
            observations,
            AssociationIssue.INSUFFICIENT_OBSERVATIONS,
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
    if np.ptp(x_values) == 0.0:
        return _unavailable_association(
            observations,
            AssociationIssue.ZERO_HETEROGENEITY_VARIATION,
        )
    if np.ptp(y_values) == 0.0:
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
    loo = _leave_one_out(x_values, y_values, slope)
    sufficient = len(observations) >= MINIMUM_PUBLICATION_OBSERVATIONS.value
    statistics = AssociationStatistics(
        spearman_rho=CorrelationCoefficient(spearman.statistic.value),
        spearman_p_value=PValue(spearman.p_value.value),
        regression_intercept=regression.intercept,
        regression_slope=regression.slope,
        regression_slope_standard_error=regression.stderr,
        regression_slope_confidence_interval=(
            MetricValue(slope - t_critical * slope_se),
            MetricValue(slope + t_critical * slope_se),
        ),
        r_squared=Ratio(regression.rvalue.value**2),
        leverage=tuple(Ratio(float(value)) for value in leverage),
        leave_one_out_slopes=loo.slopes,
        leave_one_out_r_squared=loo.r_squared,
        influence=loo.influences,
        evidentiary_sufficient=sufficient,
    )
    return AssociationResult(
        observations=observations,
        statistics=statistics,
        issue=None if sufficient else AssociationIssue.INSUFFICIENT_EVIDENCE,
    )


def _leave_one_out(
    x_values: np.ndarray,
    y_values: np.ndarray,
    full_slope: float,
) -> LeaveOneOutAssociationDiagnostics:
    slopes: list[MetricValue] = []
    r_squared_values: list[Ratio] = []
    influences: list[MetricValue] = []
    for index in range(x_values.size):
        mask = np.ones(x_values.size, dtype=bool)
        mask[index] = False
        x_loo = x_values[mask]
        y_loo = y_values[mask]
        if np.ptp(x_loo) == 0.0 or np.ptp(y_loo) == 0.0:
            slopes.append(MetricValue(full_slope))
            r_squared_values.append(Ratio(0.0))
            influences.append(MetricValue(0.0))
            continue
        fit = cast(
            LinearRegressionResult,
            stats.linregress(x_loo, y_loo, alternative="two-sided"),
        )
        extracted = linear_regression_values(fit)
        if extracted is None:
            slopes.append(MetricValue(full_slope))
            r_squared_values.append(Ratio(0.0))
            influences.append(MetricValue(0.0))
            continue
        loo_slope = extracted.slope.value
        slopes.append(extracted.slope)
        r_squared_values.append(Ratio(extracted.rvalue.value**2))
        influences.append(MetricValue(full_slope - loo_slope))
    return LeaveOneOutAssociationDiagnostics(
        slopes=tuple(slopes),
        r_squared=tuple(r_squared_values),
        influences=tuple(influences),
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
