"""Strict authored evaluation-model tests."""

import pytest
from pydantic import ValidationError

from datp_core.config.models.experiment_config import EvaluationSpecConfig


def test_evaluation_schema_rejects_undeclared_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        EvaluationSpecConfig.model_validate(
            {"label": "policy", "threshold_policy": "local_p95", "unexpected": "not declared"}
        )
