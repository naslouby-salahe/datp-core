"""Metric identifiers and their claim roles (docs/protocol/identity_lock.md #5-6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Metric(StrEnum):
    FPR = "fpr"
    TPR = "tpr"
    BALANCED_ACCURACY = "balanced_accuracy"
    MACRO_F1 = "macro_f1"
    AUROC = "auroc"
    CV_FPR = "cv_fpr"
    IQR_FPR = "iqr_fpr"
    MAX_MINUS_MIN_FPR = "max_minus_min_fpr"
    WORST_CLIENT_FPR = "worst_client_fpr"
    P10_MACRO_F1 = "p10_macro_f1"
    ALERT_BURDEN = "alert_burden"


class MetricRole(StrEnum):
    """PRIMARY is the sole thresholding-verdict metric; CONTROL is a sanity check only."""

    PRIMARY = "primary"
    CONTROL = "control"
    SECONDARY = "secondary"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class MetricSpec:
    metric: Metric
    role: MetricRole
    is_thresholding_verdict: bool


METRIC_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec(Metric.CV_FPR, MetricRole.PRIMARY, True),
    MetricSpec(Metric.FPR, MetricRole.OPERATIONAL, False),
    MetricSpec(Metric.TPR, MetricRole.SECONDARY, False),
    MetricSpec(Metric.BALANCED_ACCURACY, MetricRole.SECONDARY, False),
    MetricSpec(Metric.MACRO_F1, MetricRole.SECONDARY, False),
    MetricSpec(Metric.AUROC, MetricRole.CONTROL, False),
    MetricSpec(Metric.IQR_FPR, MetricRole.SECONDARY, False),
    MetricSpec(Metric.MAX_MINUS_MIN_FPR, MetricRole.SECONDARY, False),
    MetricSpec(Metric.WORST_CLIENT_FPR, MetricRole.OPERATIONAL, False),
    MetricSpec(Metric.P10_MACRO_F1, MetricRole.SECONDARY, False),
    MetricSpec(Metric.ALERT_BURDEN, MetricRole.OPERATIONAL, False),
)


def metric_spec(metric: Metric) -> MetricSpec:
    for spec in METRIC_SPECS:
        if spec.metric is metric:
            return spec
    raise ValueError(f"missing metric specification for {metric.value}")


def is_primary(metric: Metric) -> bool:
    return metric_spec(metric).role is MetricRole.PRIMARY


def is_control(metric: Metric) -> bool:
    return metric_spec(metric).role is MetricRole.CONTROL


def is_thresholding_verdict(metric: Metric) -> bool:
    return metric_spec(metric).is_thresholding_verdict
