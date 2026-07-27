"""Stage handler: context model validation."""

from datp_core.core.identifiers import ExperimentId, ThresholdPolicyId
from datp_core.evaluation.enums import MissingThresholdPolicy
from datp_core.pipeline.stages.context import EvaluationContext

_DEFAULT_POLICY_ID = ThresholdPolicyId("shared_mean_p95")


def _make_context(
    *,
    calibration_sample_count: int | None,
    threshold_policy_id: ThresholdPolicyId = _DEFAULT_POLICY_ID,
    missing_threshold_policy: MissingThresholdPolicy = MissingThresholdPolicy.FAIL,
) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=ExperimentId("test_experiment"),
        threshold_policy_id=threshold_policy_id,
        missing_threshold_policy=missing_threshold_policy,
        calibration_sample_count=calibration_sample_count,
        calibration_replicate=0 if calibration_sample_count is not None else None,
    )


class TestMissingThresholdPolicy:
    def test_explicit_fail_policy(self) -> None:
        ctx = _make_context(
            calibration_sample_count=100,
            missing_threshold_policy=MissingThresholdPolicy.FAIL,
        )
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.FAIL

    def test_explicit_mark_ineligible(self) -> None:
        ctx = _make_context(
            calibration_sample_count=100,
            missing_threshold_policy=MissingThresholdPolicy.MARK_INELIGIBLE,
        )
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.MARK_INELIGIBLE

    def test_policy_independent_of_calibration_sample_count(self) -> None:
        ctx = _make_context(
            calibration_sample_count=100,
            missing_threshold_policy=MissingThresholdPolicy.FAIL,
        )
        assert ctx.missing_threshold_policy is MissingThresholdPolicy.FAIL
        assert ctx.threshold_policy_id == ThresholdPolicyId("shared_mean_p95")

    def test_threshold_policy_id_present(self) -> None:
        ctx = _make_context(
            calibration_sample_count=None,
            threshold_policy_id=ThresholdPolicyId("b2_per_client"),
            missing_threshold_policy=MissingThresholdPolicy.MARK_INELIGIBLE,
        )
        assert ctx.threshold_policy_id == ThresholdPolicyId("b2_per_client")
