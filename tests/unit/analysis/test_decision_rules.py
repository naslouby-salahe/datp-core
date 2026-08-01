from datp_core.analysis.decision_rules import decide_confirmatory, decide_model_absorption
from datp_core.analysis.inference import BcaOutcome, BcaReason, BootstrapInterval
from datp_core.domain.enums import AvailabilityStatus, IntervalMethod, ScientificDecision
from datp_core.domain.values import BootstrapReplicateCount, ConfidenceLevel, MetricValue, Seed


def test_confirmatory_decision_uses_positive_bca_interval_not_secondary_evidence() -> None:
    interval = BootstrapInterval(
        IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
        ConfidenceLevel(0.95),
        BootstrapReplicateCount(10_000),
        Seed(3),
        MetricValue(0.2),
        MetricValue(0.01),
        MetricValue(0.4),
        0.0,
        0.0,
        AvailabilityStatus.AVAILABLE,
        BcaOutcome.AVAILABLE,
        BcaReason.NONE,
    )

    result = decide_confirmatory(interval)

    assert result.decision is ScientificDecision.SUPPORTED
    assert result.availability is AvailabilityStatus.AVAILABLE


def test_model_absorption_blocks_a_nonpositive_fedavg_reference_effect() -> None:
    result = decide_model_absorption(MetricValue(0.0), MetricValue(0.2))

    assert result.decision is ScientificDecision.BLOCKED
    assert result.availability is AvailabilityStatus.UNAVAILABLE
