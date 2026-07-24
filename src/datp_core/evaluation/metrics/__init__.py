"""Evaluation metric models and calculations."""

from datp_core.evaluation.metrics.models import (
    ClientConfusionMatrix,
    FprDispersion,
    MetricStatus,
    MetricValue,
)
from datp_core.evaluation.metrics.operating_point import (
    compute_operating_point_metrics,
    ineligible_client_metrics,
)
from datp_core.evaluation.metrics.auroc import (
    ClientAuroc,
    compute_client_auroc,
    compute_roc_auc,
)
from datp_core.evaluation.metrics.diagnostics import (
    assert_auroc_invariant,
    calculate_fpr_dispersion,
    calculate_pairwise_js_divergence,
)

__all__ = [
    "ClientAuroc",
    "ClientConfusionMatrix",
    "FprDispersion",
    "MetricStatus",
    "MetricValue",
    "assert_auroc_invariant",
    "calculate_fpr_dispersion",
    "calculate_pairwise_js_divergence",
    "compute_client_auroc",
    "compute_operating_point_metrics",
    "compute_roc_auc",
    "ineligible_client_metrics",
]
