from collections.abc import Callable
from decimal import Decimal

import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import TrafficRate, TrafficRateUnit
from datp_core.domain.evaluation.metrics import METRIC_SPECS, MetricSpec, OperatingPointMetric
from datp_core.domain.evaluation.operating_points import (
    AlertBurdenEvaluationSuiteSpec,
    ClientEligibilityReason,
    ClientEligibilityStatus,
)
from datp_core.domain.experiments.feasibility import (
    BlockingReason,
    FeasibilityStatus,
    RejectionReason,
    ReuseIncompatibilityReason,
)


def test_feasibility_and_rejection_vocabularies_are_complete() -> None:
    assert tuple(FeasibilityStatus) == (
        FeasibilityStatus.FEASIBLE,
        FeasibilityStatus.GATED,
        FeasibilityStatus.PENDING_VERIFICATION,
        FeasibilityStatus.REJECTED,
    )
    assert tuple(RejectionReason) == (
        RejectionReason.B_B_NO_METADATA,
        RejectionReason.TEMPORAL_NO_TIMESTAMPS,
        RejectionReason.FEDBN_NO_BATCHNORM,
        RejectionReason.LARIDI_ANOMALY_LABELED,
        RejectionReason.MIA_NO_LITERATURE,
        RejectionReason.STREAMING_DRIFT_SCOPE,
        RejectionReason.BYZANTINE_CONFORMAL_SCOPE,
        RejectionReason.BROAD_PFL_LIMIT,
    )


def test_rejection_labels_are_stable_and_rendered_exactly() -> None:
    assert RejectionReason.B_B_NO_METADATA.value == "B_B_REJECTED_NO_METADATA"
    assert RejectionReason.TEMPORAL_NO_TIMESTAMPS.value == "TEMPORAL_REJECTED_NO_TIMESTAMPS"


def test_reuse_and_blocking_vocabularies_are_complete() -> None:
    assert len(ReuseIncompatibilityReason) == 13
    assert tuple(BlockingReason) == (
        BlockingReason.MISSING_SOURCE,
        BlockingReason.FAILED_ANCHOR_GATE,
        BlockingReason.FAILED_FEASIBILITY,
        BlockingReason.UNRESOLVED_SCIENTIFIC_DECISION,
        BlockingReason.INVALID_LINEAGE,
        BlockingReason.REQUIRED_HARDWARE_UNAVAILABLE,
        BlockingReason.INSUFFICIENT_STORAGE,
    )


def test_client_eligibility_vocabulary_excludes_traffic_rate_failures() -> None:
    assert tuple(ClientEligibilityStatus) == (
        ClientEligibilityStatus.ELIGIBLE,
        ClientEligibilityStatus.FALLBACK_ASSIGNED,
        ClientEligibilityStatus.EXCLUDED,
    )
    assert tuple(ClientEligibilityReason) == (
        ClientEligibilityReason.SUFFICIENT_CALIBRATION,
        ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK,
        ClientEligibilityReason.MISSING_TEST_BENIGN,
        ClientEligibilityReason.MISSING_TEST_ATTACK,
    )
    assert all("traffic" not in reason.value for reason in ClientEligibilityReason)


def test_unwrapped_traffic_rate_fails_before_client_eligibility_is_evaluated() -> None:
    metrics = tuple(
        specification
        for specification in METRIC_SPECS
        if specification.metric in (OperatingPointMetric.CV_FPR, OperatingPointMetric.ALERT_BURDEN)
    )

    with pytest.raises(DomainValidationError):
        _construct_suite_with_unwrapped_traffic_rate(AlertBurdenEvaluationSuiteSpec, metrics=metrics)


def _construct_suite_with_unwrapped_traffic_rate(
    constructor: Callable[..., AlertBurdenEvaluationSuiteSpec], *, metrics: tuple[MetricSpec, ...]
) -> AlertBurdenEvaluationSuiteSpec:
    return constructor(
        primary_metric=OperatingPointMetric.CV_FPR,
        metrics=metrics,
        traffic_rate_evidence=TrafficRate(
            value=Decimal("1"),
            unit=TrafficRateUnit.EVENTS_PER_SECOND,
        ),
    )
