"""Evaluation: metrics, distributions, definitions, and execution handlers."""

from datp_core.evaluation.definitions.bundles import MetricBundleRecord
from datp_core.evaluation.definitions.metrics import (
    ClusterDiagnosticsRecord,
    CrossClientAggregationRecord,
    HeterogeneityDiagnosticsRecord,
    JsDivergenceRecord,
    MetricDefinitionsRecord,
    MetricFormulaRecord,
    PrecisionPolicyRecord,
    ThresholdEstimationMetricsRecord,
)
from datp_core.evaluation.definitions.results import EvaluationResultContractRecord
from datp_core.evaluation.distributions.cdf import client_score_distributions
from datp_core.evaluation.distributions.models import (
    CdfPoint,
    ClientScoreDistributionRecord,
    QuantileVarianceTerms,
    ThresholdPositionRecord,
    ThresholdTradeoffEntry,
)
from datp_core.evaluation.distributions.tradeoff import threshold_tradeoff
from datp_core.evaluation.distributions.variance import calibration_variance_terms
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
