"""Stage handler: context model validation."""

from datp_core.core.identifiers import ExperimentId
from datp_core.evaluation.enums import MissingThresholdPolicy
from datp_core.pipeline.stages.context import EvaluationContext


def _make_context(
    *,
    calibration_sample_count: int | None,
    missing_threshold_policy: MissingThresholdPolicy = MissingThresholdPolicy.FAIL,
) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=ExperimentId("test_experiment"),
        calibration_sample_count=calibration_sample_count,
        calibration_replicate=0 if calibration_sample_count is not None else None,
        missing_threshold_policy=missing_threshold_policy,
    )


class TestMissingThresholdPolicy:
    def test_default_missing_threshold_policy_is_fail(self) -> None:
        ctx = _make_context(calibration_sample_count=None)
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.FAIL

    def test_explicit_mark_ineligible(self) -> None:
        ctx = _make_context(calibration_sample_count=100, missing_threshold_policy=MissingThresholdPolicy.MARK_INELIGIBLE)
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.MARK_INELIGIBLE

    def test_policy_independent_of_calibration_sample_count(self) -> None:
        ctx = _make_context(calibration_sample_count=100)
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.FAIL
