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
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import AvailabilityStatus, EvidenceRole
from datp_core.domain.values import MetricValue, PairedObservationCount, Ratio

MINIMUM_ASSOCIATION_OBSERVATIONS = PairedObservationCount(3)


class AssociationIssue(StrEnum):
    INSUFFICIENT_OBSERVATIONS = "association requires at least three observations"
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
    heterogeneity: MetricValue
    benefit: MetricValue


class AssociationStatistics(StrictModel):
    spearman_rho: CorrelationCoefficient
    spearman_p_value: PValue
    regression_intercept: MetricValue
    regression_slope: MetricValue
    regression_slope_standard_error: MetricValue
    r_squared: Ratio
    leverage: tuple[Ratio, ...]


class AssociationResult(StrictModel):
    observations: tuple[AssociationObservation, ...]
    statistics: AssociationStatistics | None
    issue: AssociationIssue | None

    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.MECHANISM

    @model_validator(mode="after")
    def validate_result(self) -> "AssociationResult":
        if (self.statistics is None) == (self.issue is None):
            raise ValueError("association result requires either statistics or one issue")
        if self.statistics is not None and len(self.statistics.leverage) != len(self.observations):
            raise ValueError("association leverage must cover every observation")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return AvailabilityStatus.AVAILABLE if self.issue is None else self.issue.availability

    @property
    def reason(self) -> str | None:
        return None if self.issue is None else self.issue.value

    @property
    def observation_count(self) -> PairedObservationCount:
        return PairedObservationCount(len(self.observations))


def heterogeneity_benefit_association(
    observations: tuple[AssociationObservation, ...],
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
    values = spearman + regression
    design = np.column_stack((np.ones(x_values.size), x_values))
    leverage = np.einsum("ij,ji->i", design, np.linalg.pinv(design))
    return AssociationResult(
        observations=observations,
        statistics=AssociationStatistics(
            spearman_rho=CorrelationCoefficient(values[0]),
            spearman_p_value=PValue(values[1]),
            regression_intercept=MetricValue(values[2]),
            regression_slope=MetricValue(values[3]),
            regression_slope_standard_error=MetricValue(values[4]),
            r_squared=Ratio(values[5] ** 2),
            leverage=tuple(Ratio(float(value)) for value in leverage),
        ),
        issue=None,
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
