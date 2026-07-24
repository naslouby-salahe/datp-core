"""The closed ``AnalysisResult`` union across every analysis capability, and the stable
JSON-serialization entry point for the persisted statistical-analysis artifact."""

from __future__ import annotations

from attrs import asdict

from datp_core.analysis.calibration.models import (
    ConformalCoverageAnalysisResult,
    QuantileEstimationAnalysisResult,
    ThresholdStabilityAnalysisResult,
)
from datp_core.analysis.clustering.models import ClusterStabilityAnalysisResult
from datp_core.analysis.comparisons.models import (
    AbsorptionAnalysisResult,
    MetricAssociationAnalysisResult,
    PairedThresholdAnalysisResult,
    RecoveryFractionAnalysisResult,
)
from datp_core.analysis.distributions.models import (
    DistributionMechanismAnalysisResult,
    LockedClientDistributionAnalysisResult,
)
from datp_core.analysis.operations.models import AlertBurdenAnalysisResult, ResourceCostAnalysisResult
from datp_core.analysis.selection.models import DittoSelectionResult, FederatedProximalSelectionResult
from datp_core.analysis.temporal.models import TemporalRecoveryAnalysisResult
from datp_core.analysis.validation.models import AnchorEquivalenceAnalysisResult

AnalysisResult = (
    PairedThresholdAnalysisResult
    | FederatedProximalSelectionResult
    | DittoSelectionResult
    | MetricAssociationAnalysisResult
    | ThresholdStabilityAnalysisResult
    | RecoveryFractionAnalysisResult
    | AbsorptionAnalysisResult
    | ConformalCoverageAnalysisResult
    | DistributionMechanismAnalysisResult
    | LockedClientDistributionAnalysisResult
    | AlertBurdenAnalysisResult
    | QuantileEstimationAnalysisResult
    | ResourceCostAnalysisResult
    | ClusterStabilityAnalysisResult
    | TemporalRecoveryAnalysisResult
    | AnchorEquivalenceAnalysisResult
)


def analysis_result_to_payload(result: AnalysisResult) -> dict[str, object]:
    """Convert one typed analysis result into the exact JSON-serializable shape persisted on disk.

    Uses ``attrs.asdict`` for structural recursion (nested attrs records and Mapping/tuple values
    all unstructure to plain JSON-safe types); the one authored dotted metric-formula key on
    ``AnchorEquivalenceChecks`` is restored explicitly since it cannot be a Python identifier.
    """
    payload = asdict(result, recurse=True)
    checks = payload.get("checks")
    if isinstance(checks, dict) and "reproduced_interval_width_at_most_1_20x_historical_width" in checks:
        checks["reproduced_interval_width_at_most_1.20x_historical_width"] = checks.pop(
            "reproduced_interval_width_at_most_1_20x_historical_width"
        )
    return payload


__all__ = ["AnalysisResult", "analysis_result_to_payload"]
