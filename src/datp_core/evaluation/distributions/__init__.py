"""Per-client score-distribution and threshold-tradeoff views."""

from datp_core.evaluation.distributions.models import (
    CdfPoint,
    ClientScoreDistributionRecord,
    QuantileVarianceTerms,
    ThresholdPositionRecord,
    ThresholdTradeoffEntry,
)
from datp_core.evaluation.distributions.cdf import client_score_distributions
from datp_core.evaluation.distributions.tradeoff import threshold_tradeoff
from datp_core.evaluation.distributions.variance import calibration_variance_terms

__all__ = [
    "CdfPoint",
    "ClientScoreDistributionRecord",
    "QuantileVarianceTerms",
    "ThresholdPositionRecord",
    "ThresholdTradeoffEntry",
    "calibration_variance_terms",
    "client_score_distributions",
    "threshold_tradeoff",
]
