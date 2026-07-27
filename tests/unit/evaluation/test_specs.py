"""Specification model validation and enum parsing."""

import pytest
from pydantic import ValidationError

from datp_core.evaluation.enums import MetricRole, MetricStatus, MetricUnit, MissingThresholdPolicy
from datp_core.evaluation.specs import (
    InvariantMetricSpec,
    MetricDefinitions,
    ScalarMetricSpec,
)


class TestMetricStatus:
    def test_available_value(self) -> None:
        assert MetricStatus.AVAILABLE.value == "available"

    def test_unavailable_ineligible_value(self) -> None:
        assert MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value == "unavailable_ineligible_client"

    def test_single_class_value(self) -> None:
        assert MetricStatus.UNAVAILABLE_SINGLE_CLASS.value == "unavailable_single_class"


class TestMissingThresholdPolicy:
    def test_fail_value(self) -> None:
        assert MissingThresholdPolicy.FAIL.value == "fail"

    def test_mark_ineligible_value(self) -> None:
        assert MissingThresholdPolicy.MARK_INELIGIBLE.value == "mark_ineligible"


class TestScalarMetricSpec:
    def test_minimal_construction(self) -> None:
        spec = ScalarMetricSpec()
        assert spec.kind == "scalar"
        assert spec.formula is None

    def test_frozen(self) -> None:
        spec = ScalarMetricSpec(unit=MetricUnit.RATIO)
        with pytest.raises(ValidationError):
            spec.unit = MetricUnit.SCORE  # type: ignore[misc]


class TestInvariantMetricSpec:
    def test_construction(self) -> None:
        spec = InvariantMetricSpec(role=MetricRole.MODEL_QUALITY_CONTROL)
        assert spec.kind == "invariant"
        assert spec.role is MetricRole.MODEL_QUALITY_CONTROL


class TestMetricDefinitions:
    def test_missing_required_fields_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            MetricDefinitions.model_validate({})
