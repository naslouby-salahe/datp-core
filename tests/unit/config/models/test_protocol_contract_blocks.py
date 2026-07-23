"""Strict typing of the previously-untyped flat protocol contract blocks."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from datp_core.configuration.models import (
    EvaluationResultContractConfig,
    NestedReplicatePolicyConfig,
    ReportDefaultsConfig,
    ResultTypeConfig,
    ThresholdPolicyDefaultsConfig,
)
from datp_core.configuration.loading import YamlConfigurationReader


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


def test_deeply_nested_protocol_blocks_are_strictly_typed() -> None:
    from datp_core.configuration.models import (
        ArtifactIdentityConfig,
        CommunicationEstimationContractConfig,
        MetricDefinitionsConfig,
        OperationalInputsConfig,
        ReportProfileConfig,
    )

    protocols = _protocols()
    assert isinstance(protocols.metric_definitions, MetricDefinitionsConfig)
    assert protocols.metric_definitions.fpr.direction == "lower_is_better"
    assert protocols.metric_definitions.cross_client_aggregation.standard_deviation_ddof == 0
    assert protocols.metric_definitions.cross_client_aggregation.cv_fpr.minimum_client_count == 2

    assert isinstance(protocols.artifact_identity, ArtifactIdentityConfig)
    assert protocols.artifact_identity.digest_bytes == 32
    assert "split_seed" in protocols.artifact_identity.fingerprints.materialization

    assert isinstance(protocols.communication_estimation_contract, CommunicationEstimationContractConfig)
    assert protocols.communication_estimation_contract.field_encodings["float64"].bytes_per_field == 8
    assert protocols.communication_estimation_contract.threshold_exchange.b2.uplink_fields_per_client == []

    assert all(isinstance(p, ReportProfileConfig) for p in protocols.report_profiles.values())
    assert protocols.report_profiles["interval_table"].columns is not None

    assert isinstance(protocols.operational_inputs, OperationalInputsConfig)
    assert protocols.operational_inputs.benign_decision_rate.configured is False
    assert protocols.operational_inputs.benign_decision_rate.value is None
