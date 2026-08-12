from types import SimpleNamespace
from typing import cast

from datp_core.analysis.mechanisms import ThresholdMovementCohort, summarize_client_impact
from datp_core.core.identifiers import AvailabilityStatus, ExperimentId
from datp_core.core.numeric import MetricValue, Seed


def test_client_impact_preserves_exact_fpr_help_harm_and_pareto_partition() -> None:
    cohort = cast(
        ThresholdMovementCohort,
        SimpleNamespace(
            availability=AvailabilityStatus.AVAILABLE,
            reason=None,
            movements=(
                _movement(delta_fpr=-0.2, delta_tpr=0.0),
                _movement(delta_fpr=0.1, delta_tpr=-0.1),
                _movement(delta_fpr=0.0, delta_tpr=0.2),
            ),
        ),
    )

    summary = summarize_client_impact(cohort)

    assert summary.fpr_helped.numerator is not None
    assert summary.fpr_helped.numerator.value == 1
    assert summary.fpr_harmed.numerator is not None
    assert summary.fpr_harmed.numerator.value == 1
    assert summary.fpr_unchanged.numerator is not None
    assert summary.fpr_unchanged.numerator.value == 1
    assert summary.tpr_loss.numerator is not None
    assert summary.tpr_loss.numerator.value == 1
    assert summary.pareto.pareto_improved.numerator is not None
    assert summary.pareto.pareto_improved.numerator.value == 1
    assert summary.pareto.pareto_harmed.numerator is not None
    assert summary.pareto.pareto_harmed.numerator.value == 1
    assert summary.pareto.no_fpr_change.numerator is not None
    assert summary.pareto.no_fpr_change.numerator.value == 1


def test_client_impact_marks_attack_fractions_unavailable_without_common_tpr() -> None:
    cohort = cast(
        ThresholdMovementCohort,
        SimpleNamespace(
            availability=AvailabilityStatus.AVAILABLE,
            reason=None,
            movements=(_movement(delta_fpr=-0.2, delta_tpr=None),),
        ),
    )

    summary = summarize_client_impact(cohort)

    assert summary.fpr_helped.value is not None
    assert summary.tpr_loss.value is None
    assert summary.tpr_loss.reason is not None
    assert summary.pareto.pareto_improved.value is None


def _movement(*, delta_fpr: float, delta_tpr: float | None) -> SimpleNamespace:
    return SimpleNamespace(
        seed=Seed(1),
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        delta_fpr=MetricValue(delta_fpr),
        delta_tpr=None if delta_tpr is None else MetricValue(delta_tpr),
        delta_macro_f1=None if delta_tpr is None else MetricValue(delta_tpr),
        delta_balanced_accuracy=None if delta_tpr is None else MetricValue(delta_tpr),
    )
