"""Strict typing of the previously-untyped flat protocol contract blocks."""

import pytest
from pydantic import ValidationError

from datp_core.config.models.protocol_config import (
    EvaluationResultContractConfig,
    NestedReplicatePolicyConfig,
    ReportDefaultsConfig,
    ResultTypeConfig,
    ThresholdPolicyDefaultsConfig,
)
from datp_core.config.yaml_loader import YamlConfigurationReader
from pathlib import Path


def _protocols():
    return YamlConfigurationReader.read_protocols_document(Path("configs/protocols.yaml"))


def test_flat_protocol_blocks_resolve_to_strict_models() -> None:
    protocols = _protocols()
    assert isinstance(protocols.threshold_policy_defaults, ThresholdPolicyDefaultsConfig)
    assert protocols.threshold_policy_defaults.attack_rows_forbidden_in_calibration is True
    assert isinstance(protocols.nested_replicate_policy, NestedReplicatePolicyConfig)
    assert protocols.nested_replicate_policy.replicates_counted_as_independent_units is False
    assert isinstance(protocols.evaluation_result_contract, EvaluationResultContractConfig)
    assert "threshold_record" in protocols.evaluation_result_contract.per_evaluation_required_records
    assert isinstance(protocols.report_defaults, ReportDefaultsConfig)
    assert "markdown" in protocols.report_defaults.table_output_formats
    assert all(isinstance(v, ResultTypeConfig) for v in protocols.result_types.values())


def test_result_type_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ResultTypeConfig.model_validate({"permitted_evidence_roles": ["confirmatory"], "unexpected": 1})
