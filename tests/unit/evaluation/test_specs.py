"""Specification model validation and enum parsing."""

import pytest
from pydantic import ValidationError

from datp_core.core.identifiers import MetricBundleId
from datp_core.evaluation.enums import (
    AggregationKind,
    MetricDirection,
    MetricId,
    MetricRequirement,
    MetricRole,
    MetricStatus,
    MetricUnit,
    MissingThresholdPolicy,
    PredictionRule,
    QuantileEstimator,
    WeightingMode,
)
from datp_core.evaluation.specs import (
    AggregateMetricDefinition,
    CrossClientAggregationSpec,
    MetricBundleSpec,
    MetricDefinition,
    MetricDefinitions,
)


class TestMetricStatus:
    def test_available_value(self) -> None:
        assert MetricStatus.AVAILABLE.value == "available"

    def test_unavailable_ineligible_value(self) -> None:
        assert MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value == "unavailable_ineligible_client"

    def test_single_class_value(self) -> None:
        assert MetricStatus.UNAVAILABLE_SINGLE_CLASS.value == "unavailable_single_class"

    def test_new_ssot_members(self) -> None:
        assert MetricStatus.UNAVAILABLE_INVALID_ATTACK_ASSIGNMENT.value == "unavailable_invalid_attack_assignment"
        assert MetricStatus.UNAVAILABLE_UNSUPPORTED_REGIME.value == "unavailable_unsupported_regime"
        assert MetricStatus.FAILED_STATISTICAL_PROCEDURE.value == "failed_statistical_procedure"

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            MetricStatus("not_a_valid_status")


class TestMissingThresholdPolicy:
    def test_fail_value(self) -> None:
        assert MissingThresholdPolicy.FAIL.value == "fail"

    def test_mark_ineligible_value(self) -> None:
        assert MissingThresholdPolicy.MARK_INELIGIBLE.value == "mark_ineligible"

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            MissingThresholdPolicy("not_a_policy")


class TestMetricDefinition:
    def test_minimal_construction(self) -> None:
        spec = MetricDefinition(
            identifier=MetricId.FALSE_POSITIVE_RATE,
            formula="fp / (fp + tn)",
            unit=MetricUnit.RATIO,
            direction=MetricDirection.LOWER_IS_BETTER,
            role=MetricRole.PRIMARY,
        )
        assert spec.identifier is MetricId.FALSE_POSITIVE_RATE

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinition.model_validate({
                "identifier": "false_positive_rate",
                "formula": "fp / (fp + tn)",
                "unit": "ratio",
                "direction": "lower_is_better",
                "role": "primary",
                "nonexistent_field": 42,
            })

    def test_frozen(self) -> None:
        spec = MetricDefinition(
            identifier=MetricId.FALSE_POSITIVE_RATE,
            formula="fp / (fp + tn)",
            unit=MetricUnit.RATIO,
            direction=MetricDirection.LOWER_IS_BETTER,
            role=MetricRole.PRIMARY,
        )
        with pytest.raises(ValidationError):
            spec.unit = MetricUnit.SCORE  # type: ignore[misc]


class TestAggregateMetricDefinition:
    def test_quantile_required_for_quantile_aggregation(self) -> None:
        with pytest.raises(ValidationError):
            AggregateMetricDefinition(
                identifier=MetricId.CV_FPR,
                source_metric=MetricId.FALSE_POSITIVE_RATE,
                aggregation=AggregationKind.QUANTILE,
                unit=MetricUnit.RATIO,
                direction=MetricDirection.LOWER_IS_BETTER,
                role=MetricRole.PRIMARY,
            )

    def test_quantile_forbidden_for_non_quantile_aggregation(self) -> None:
        with pytest.raises(ValidationError):
            AggregateMetricDefinition(
                identifier=MetricId.CV_FPR,
                source_metric=MetricId.FALSE_POSITIVE_RATE,
                aggregation=AggregationKind.MEAN,
                unit=MetricUnit.RATIO,
                direction=MetricDirection.LOWER_IS_BETTER,
                role=MetricRole.PRIMARY,
                quantile=0.5,
            )


class TestMetricDefinitions:
    def test_missing_required_fields_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinitions.model_validate({})

    def test_duplicate_identifiers_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinitions(
                prediction_rule=PredictionRule.SCORE_GREATER_THAN_THRESHOLD,
                per_client_before_aggregation=True,
                test_rows_only=True,
                metrics=(
                    MetricDefinition(
                        identifier=MetricId.FALSE_POSITIVE_RATE,
                        formula="fp / (fp + tn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.LOWER_IS_BETTER,
                        role=MetricRole.PRIMARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.FALSE_POSITIVE_RATE,
                        formula="fp / (fp + tn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.LOWER_IS_BETTER,
                        role=MetricRole.PRIMARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.TRUE_POSITIVE_RATE,
                        formula="tp / (tp + fn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.BALANCED_ACCURACY,
                        formula="(tpr + 1 - fpr) / 2",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.MACRO_F1,
                        formula="macro_f1",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.AUROC,
                        formula="roc_auc",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.MODEL_QUALITY_CONTROL,
                        requirements=(MetricRequirement.BOTH_CLASSES,),
                    ),
                ),
                cross_client_aggregation=CrossClientAggregationSpec(
                    standard_deviation_ddof=0,
                    cv_instability_threshold_factor=0.01,
                    minimum_client_count=1,
                    weighting=WeightingMode.UNWEIGHTED,
                    quantile_estimator=QuantileEstimator.LINEAR_INTERPOLATED_ORDER_STATISTIC,
                    metrics=(),
                ),
                js_divergence_spec=None,  # type: ignore[arg-type]
                precision_policy_spec=None,  # type: ignore[arg-type]
                metric_statuses=(),
                forbidden_substitutions=(),
            )

    def test_missing_required_metrics_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinitions(
                prediction_rule=PredictionRule.SCORE_GREATER_THAN_THRESHOLD,
                per_client_before_aggregation=True,
                test_rows_only=True,
                metrics=(
                    MetricDefinition(
                        identifier=MetricId.FALSE_POSITIVE_RATE,
                        formula="fp / (fp + tn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.LOWER_IS_BETTER,
                        role=MetricRole.PRIMARY,
                    ),
                ),
                cross_client_aggregation=CrossClientAggregationSpec(
                    standard_deviation_ddof=0,
                    cv_instability_threshold_factor=0.01,
                    minimum_client_count=1,
                    weighting=WeightingMode.UNWEIGHTED,
                    quantile_estimator=QuantileEstimator.LINEAR_INTERPOLATED_ORDER_STATISTIC,
                    metrics=(),
                ),
                js_divergence_spec=None,  # type: ignore[arg-type]
                precision_policy_spec=None,  # type: ignore[arg-type]
                metric_statuses=(),
                forbidden_substitutions=(),
            )

    def test_auroc_must_be_model_quality_control(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinitions(
                prediction_rule=PredictionRule.SCORE_GREATER_THAN_THRESHOLD,
                per_client_before_aggregation=True,
                test_rows_only=True,
                metrics=(
                    MetricDefinition(
                        identifier=MetricId.FALSE_POSITIVE_RATE,
                        formula="fp / (fp + tn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.LOWER_IS_BETTER,
                        role=MetricRole.PRIMARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.TRUE_POSITIVE_RATE,
                        formula="tp / (tp + fn)",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.BALANCED_ACCURACY,
                        formula="(tpr + 1 - fpr) / 2",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.MACRO_F1,
                        formula="macro_f1",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.SECONDARY,
                    ),
                    MetricDefinition(
                        identifier=MetricId.AUROC,
                        formula="roc_auc",
                        unit=MetricUnit.RATIO,
                        direction=MetricDirection.HIGHER_IS_BETTER,
                        role=MetricRole.PRIMARY,
                    ),
                ),
                cross_client_aggregation=CrossClientAggregationSpec(
                    standard_deviation_ddof=0,
                    cv_instability_threshold_factor=0.01,
                    minimum_client_count=1,
                    weighting=WeightingMode.UNWEIGHTED,
                    quantile_estimator=QuantileEstimator.LINEAR_INTERPOLATED_ORDER_STATISTIC,
                    metrics=(),
                ),
                js_divergence_spec=None,  # type: ignore[arg-type]
                precision_policy_spec=None,  # type: ignore[arg-type]
                metric_statuses=(),
                forbidden_substitutions=(),
            )


class TestMetricBundleSpec:
    def test_primary_dispersion_must_be_cross_client(self) -> None:
        with pytest.raises(ValidationError):
            MetricBundleSpec(
                identifier=MetricBundleId("test_bundle"),
                metrics=(MetricId.FALSE_POSITIVE_RATE,),
                cross_client_metrics=(),
                primary_dispersion_metric=MetricId.CV_FPR,
                model_quality_control=MetricId.AUROC,
                excludes_ineligible_clients=True,
                requires_attack_evaluable_clients=False,
            )
