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


METRIC_SPECS: dict[Metric, MetricSpec] = {
    Metric.CV_FPR: MetricSpec(Metric.CV_FPR, MetricRole.PRIMARY, True),
    Metric.FPR: MetricSpec(Metric.FPR, MetricRole.OPERATIONAL, False),
    Metric.TPR: MetricSpec(Metric.TPR, MetricRole.SECONDARY, False),
    Metric.BALANCED_ACCURACY: MetricSpec(Metric.BALANCED_ACCURACY, MetricRole.SECONDARY, False),
    Metric.MACRO_F1: MetricSpec(Metric.MACRO_F1, MetricRole.SECONDARY, False),
    Metric.AUROC: MetricSpec(Metric.AUROC, MetricRole.CONTROL, False),
    Metric.IQR_FPR: MetricSpec(Metric.IQR_FPR, MetricRole.SECONDARY, False),
    Metric.MAX_MINUS_MIN_FPR: MetricSpec(Metric.MAX_MINUS_MIN_FPR, MetricRole.SECONDARY, False),
    Metric.WORST_CLIENT_FPR: MetricSpec(Metric.WORST_CLIENT_FPR, MetricRole.OPERATIONAL, False),
    Metric.P10_MACRO_F1: MetricSpec(Metric.P10_MACRO_F1, MetricRole.SECONDARY, False),
    Metric.ALERT_BURDEN: MetricSpec(Metric.ALERT_BURDEN, MetricRole.OPERATIONAL, False),
}


def is_primary(metric: Metric) -> bool:
    return METRIC_SPECS[metric].role is MetricRole.PRIMARY


def is_control(metric: Metric) -> bool:
    return METRIC_SPECS[metric].role is MetricRole.CONTROL


def is_thresholding_verdict(metric: Metric) -> bool:
    return METRIC_SPECS[metric].is_thresholding_verdict
