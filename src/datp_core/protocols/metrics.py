"""Metric declarations and explicit undefined-result policy."""

from datp_core.domain.enums import AvailabilityStatus, MetricId
from datp_core.domain.values.ratios import MetricValue, Ratio

OPERATING_POINT_METRICS = (
    MetricId.FALSE_POSITIVE_RATE,
    MetricId.FPR_COEFFICIENT_OF_VARIATION,
    MetricId.FPR_POPULATION_STANDARD_DEVIATION,
    MetricId.FPR_IQR,
    MetricId.FPR_RANGE,
    MetricId.WORST_CLIENT_FPR,
)
OPTIONAL_EQUITY_INDEX_METRICS = (
    MetricId.JAIN_FAIRNESS_INDEX,
    MetricId.GINI_COEFFICIENT,
)
ATTACK_QUALITY_CONTROL_METRICS = (
    MetricId.TRUE_POSITIVE_RATE,
    MetricId.BALANCED_ACCURACY,
    MetricId.BINARY_MACRO_F1,
    MetricId.AUROC,
    MetricId.P10_BINARY_MACRO_F1,
    MetricId.WORST_CLIENT_BALANCED_ACCURACY,
)
ATTACK_SENSITIVE_METRICS = ATTACK_QUALITY_CONTROL_METRICS + (
    MetricId.TPR_COEFFICIENT_OF_VARIATION,
    MetricId.MEAN_CLIENT_MACRO_F1,
    MetricId.POOLED_MACRO_F1,
    MetricId.MEAN_CLIENT_BALANCED_ACCURACY,
)
CONFIRMATORY_METRICS = OPERATING_POINT_METRICS + ATTACK_QUALITY_CONTROL_METRICS
SUPPRESSED_OPERATIONAL_METRICS = (MetricId.ALERTS_PER_DAY,)
CV_ZERO_MEAN_POLICY = AvailabilityStatus.UNDEFINED
NEAR_ZERO_MEAN_FPR_WARNING_CUTOFF = Ratio(0.01)
TEMPORAL_CV_MATERIALITY_CUTOFF = MetricValue(0.10)
# Pre-specified floor for a "meaningful portion" of temporal drift recovery
# (roadmap §12.1 qualitative language; locked temporal interpretation decision:
# material recovery requires recovering at least half of the material drift excess).
# Must not reuse the model-absorption partial-retention band (0.25).
TEMPORAL_MATERIAL_RECOVERY_RATIO_MINIMUM = Ratio(0.50)
# Minimum absolute positive reference Δ_CV for absorption retention ratios.
# Below this bound the paired difference remains defined but ratio interpretation
# is scientifically unstable (near-zero denominator).
ABSORPTION_REFERENCE_EFFECT_MATERIALITY_CUTOFF = MetricValue(0.01)
