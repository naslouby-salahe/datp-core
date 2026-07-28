"""Metric declarations and explicit undefined-result policy."""

from datp_core.domain.enums import AvailabilityStatus, MetricId
from datp_core.domain.values import MetricValue, Ratio

CONFIRMATORY_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.FPR_COEFFICIENT_OF_VARIATION,
    MetricId.FPR_POPULATION_STANDARD_DEVIATION,
)
ATTACK_METRICS = (MetricId.TRUE_POSITIVE_RATE, MetricId.BALANCED_ACCURACY, MetricId.BINARY_MACRO_F1, MetricId.AUROC)
SUPPRESSED_OPERATIONAL_METRICS = (MetricId.ALERTS_PER_DAY,)
CV_ZERO_MEAN_POLICY = AvailabilityStatus.UNDEFINED
NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF = Ratio(0.01)
TEMPORAL_CV_MATERIALITY_CUTOFF = MetricValue(0.10)
