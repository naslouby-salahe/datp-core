from tests.unit.learning.federated.helpers import client_identity

from datp_core.analysis.mechanisms.model_alignment import (
    AlignmentActivationLabel,
    AlignmentReductionOutcome,
    AlignmentReductionUnavailableReason,
    ModelAlignmentClientScores,
    ModelAlignmentCondition,
    ModelAlignmentMetric,
    alignment_reductions,
    fedavg_alignment_grid,
    model_alignment,
    summarize_alignment_activation,
)
from datp_core.core.numeric import MetricValue, ScoreValue, ThresholdValue


def _condition() -> ModelAlignmentCondition:
    return ModelAlignmentCondition(
        client_scores=(
            ModelAlignmentClientScores(
                client=client_identity("client_a"),
                calibration_scores=tuple(ScoreValue(value) for value in (1.0, 2.0, 3.0, 4.0)),
            ),
            ModelAlignmentClientScores(
                client=client_identity("client_b"),
                calibration_scores=tuple(ScoreValue(value) for value in (2.0, 3.0, 4.0, 5.0)),
            ),
        ),
        shared_threshold=ThresholdValue(4.5),
    )


def test_alignment_uses_a_fedavg_type7_grid_without_smoothing() -> None:
    condition = _condition()

    result = model_alignment(condition, grid=fedavg_alignment_grid(condition))

    outcomes = {item.metric: item for item in result.metrics}
    assert result.grid.available
    assert outcomes[ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY].value is not None
    assert outcomes[ModelAlignmentMetric.LOCATION_DISPERSION].value is not None
    assert outcomes[ModelAlignmentMetric.SCALE_DISPERSION].value is not None
    assert outcomes[ModelAlignmentMetric.LOCAL_THRESHOLD_DISPERSION].value is not None
    assert outcomes[ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE].value is not None


def test_alignment_retains_one_unique_fedavg_cut_point_for_constant_scores() -> None:
    condition = ModelAlignmentCondition(
        client_scores=(
            ModelAlignmentClientScores(client=client_identity("client_a"), calibration_scores=(ScoreValue(1.0),)),
            ModelAlignmentClientScores(client=client_identity("client_b"), calibration_scores=(ScoreValue(1.0),)),
        ),
        shared_threshold=ThresholdValue(1.0),
    )

    result = model_alignment(condition, grid=fedavg_alignment_grid(condition))

    assert result.grid.available
    assert result.metrics[0].value is not None
    assert result.metrics[0].value.value == 0.0


def test_alignment_reductions_are_unclipped_and_require_positive_reference() -> None:
    reference = model_alignment(_condition(), grid=fedavg_alignment_grid(_condition()))
    condition = ModelAlignmentCondition(
        client_scores=(
            ModelAlignmentClientScores(
                client=client_identity("client_a"),
                calibration_scores=tuple(ScoreValue(value) for value in (1.0, 3.0, 5.0, 7.0)),
            ),
            ModelAlignmentClientScores(
                client=client_identity("client_b"),
                calibration_scores=tuple(ScoreValue(value) for value in (2.0, 4.0, 6.0, 8.0)),
            ),
        ),
        shared_threshold=ThresholdValue(7.5),
    )

    reductions = alignment_reductions(reference, model_alignment(condition, grid=reference.grid))

    assert len(reductions) == len(ModelAlignmentMetric)
    assert any(item.value is not None for item in reductions)


def test_alignment_activation_uses_valid_seed_means_and_positive_sign() -> None:
    first_seed = tuple(
        AlignmentReductionOutcome(
            metric=metric,
            value=MetricValue(0.5 if metric is ModelAlignmentMetric.LOCATION_DISPERSION else -0.2),
            unavailable_reason=None,
        )
        for metric in ModelAlignmentMetric
    )
    second_seed = tuple(
        AlignmentReductionOutcome(
            metric=metric,
            value=None,
            unavailable_reason=AlignmentReductionUnavailableReason.NO_POSITIVE_FEDAVG_REFERENCE,
        )
        for metric in ModelAlignmentMetric
    )

    summary = summarize_alignment_activation((first_seed, second_seed))

    assert summary.label is AlignmentActivationLabel.OBSERVED_ALIGNMENT_ACTIVATION
    assert all(item.valid_seed_count.value == 1 for item in summary.reductions)
    assert summary.reductions[1].value is not None
    assert summary.reductions[1].value.value == 0.5


def test_alignment_activation_is_unavailable_when_every_reduction_is_unavailable() -> None:
    reductions = tuple(
        AlignmentReductionOutcome(
            metric=metric,
            value=None,
            unavailable_reason=AlignmentReductionUnavailableReason.CONDITION_METRIC_UNAVAILABLE,
        )
        for metric in ModelAlignmentMetric
    )

    summary = summarize_alignment_activation((reductions,))

    assert summary.label is AlignmentActivationLabel.ALIGNMENT_ACTIVATION_UNAVAILABLE
    assert all(item.value is None and item.valid_seed_count.value == 0 for item in summary.reductions)


def test_alignment_activation_is_not_observed_when_every_valid_mean_is_nonpositive() -> None:
    reductions = tuple(
        AlignmentReductionOutcome(
            metric=metric,
            value=MetricValue(0.0 if metric is ModelAlignmentMetric.LOCATION_DISPERSION else -0.1),
            unavailable_reason=None,
        )
        for metric in ModelAlignmentMetric
    )

    summary = summarize_alignment_activation((reductions,))

    assert summary.label is AlignmentActivationLabel.NO_OBSERVED_ALIGNMENT_ACTIVATION
