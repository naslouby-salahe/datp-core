from tests.unit.learning.federated.helpers import client_identity

from datp_core.analysis.mechanisms.model_alignment import (
    ModelAlignmentClientScores,
    ModelAlignmentCondition,
    ModelAlignmentMetric,
    alignment_reductions,
    fedavg_alignment_grid,
    model_alignment,
)
from datp_core.core.numeric import ScoreValue, ThresholdValue


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
