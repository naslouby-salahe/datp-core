from types import SimpleNamespace
from typing import cast

from datp_core.analysis.mechanisms.movement import (
    ThresholdMovement,
    summarize_threshold_movement_direction_counts,
    threshold_movement_direction_counts,
)
from datp_core.core.numeric import MetricValue, Seed


def test_direction_counts_use_exact_zero_and_campaign_medians() -> None:
    first = threshold_movement_direction_counts(_movements(Seed(2), ((-0.1, -0.2), (0.0, 0.0), (0.1, 0.3))))
    second = threshold_movement_direction_counts(_movements(Seed(3), ((-0.1, -0.2), (-0.1, 0.0), (0.1, 0.3))))

    campaign = summarize_threshold_movement_direction_counts((second, first))

    assert (first.fpr_down.value, first.fpr_same.value, first.fpr_up.value) == (1, 1, 1)
    assert first.tpr_down is not None
    assert first.tpr_same is not None
    assert first.tpr_up is not None
    assert (first.tpr_down.value, first.tpr_same.value, first.tpr_up.value) == (1, 1, 1)
    assert tuple(item.seed for item in campaign.seed_counts) == (Seed(2), Seed(3))
    assert campaign.median_fpr_down == MetricValue(1.5)
    assert campaign.median_fpr_same == MetricValue(0.5)
    assert campaign.median_fpr_up == MetricValue(1.0)


def test_direction_counts_mark_tpr_unavailable_if_any_device_lacks_attack_evidence() -> None:
    counts = threshold_movement_direction_counts(_movements(Seed(2), ((-0.1, None), (0.0, 0.0))))

    assert counts.tpr_down is None
    assert counts.tpr_unavailable_reason is not None


def _movements(seed: Seed, values: tuple[tuple[float, float | None], ...]) -> tuple[ThresholdMovement, ...]:
    return tuple(
        cast(
            ThresholdMovement,
            SimpleNamespace(seed=seed, delta_fpr=MetricValue(delta_fpr), delta_tpr=_metric(delta_tpr)),
        )
        for delta_fpr, delta_tpr in values
    )


def _metric(value: float | None) -> MetricValue | None:
    return None if value is None else MetricValue(value)
