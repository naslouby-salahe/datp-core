"""Every resolved threshold policy is a pure, frozen domain record -- never a Pydantic model."""

from __future__ import annotations

import attrs
import pydantic
import pytest

from datp_core.config.resolver import resolve_project_configuration
from datp_core.domain.identifiers import ThresholdPolicyId
from datp_core.domain.thresholding import (
    CalibrationFallbackThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyRecord,
    FamilyMeanThresholdPolicyRecord,
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    SplitConformalThresholdPolicyRecord,
)

# Maps every authored identifier in configs/protocols.yaml's threshold_policies block to the
# domain record type it must resolve into.
_EXPECTED_RECORD_TYPE_BY_POLICY_ID = {
    "shared_mean_p95": SharedMeanThresholdPolicyRecord,
    "shared_pooled_p95": SharedPooledThresholdPolicyRecord,
    "shared_weighted_p95": SharedWeightedThresholdPolicyRecord,
    "local_p95": LocalQuantileThresholdPolicyRecord,
    "family_p95": FamilyMeanThresholdPolicyRecord,
    "centralized_pooled_p95": CentralizedPooledThresholdPolicyRecord,
    "cluster_k3_mean_p95": ClusterThresholdPolicyRecord,
    "cluster_k9_mean_p95": ClusterThresholdPolicyRecord,
    "cluster_k3_robust_median_p95": ClusterThresholdPolicyRecord,
    "conformal_local_p95": SplitConformalThresholdPolicyRecord,
    "local_global_shrinkage_p95": LocalGlobalShrinkageThresholdPolicyRecord,
    "calibration_size_aware_fallback_p95": CalibrationFallbackThresholdPolicyRecord,
    "federated_summary_matched_exceedance": FederatedMatchedExceedanceThresholdPolicyRecord,
    "federated_summary_fixed_k": FederatedFixedCoefficientThresholdPolicyRecord,
}


@pytest.fixture(scope="module")
def resolved_threshold_policies():
    cfg = resolve_project_configuration()
    return cfg.threshold_policies


def test_every_authored_threshold_policy_identifier_is_covered(resolved_threshold_policies) -> None:
    resolved_ids = {str(policy_id) for policy_id in resolved_threshold_policies}
    assert resolved_ids == set(_EXPECTED_RECORD_TYPE_BY_POLICY_ID)


@pytest.mark.parametrize("policy_key,expected_type", sorted(_EXPECTED_RECORD_TYPE_BY_POLICY_ID.items()))
def test_resolved_threshold_policy_is_the_expected_pure_domain_record(
    resolved_threshold_policies, policy_key: str, expected_type: type
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId(policy_key))

    assert isinstance(record, expected_type)
    assert not isinstance(record, pydantic.BaseModel)
    assert attrs.has(type(record))


@pytest.mark.parametrize("policy_key", sorted(_EXPECTED_RECORD_TYPE_BY_POLICY_ID))
def test_resolved_threshold_policy_record_is_frozen(resolved_threshold_policies, policy_key: str) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId(policy_key))
    first_field = attrs.fields(type(record))[0].name
    current_value = getattr(record, first_field)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        setattr(record, first_field, current_value)


def test_cluster_threshold_policy_retains_every_authored_field_losslessly(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("cluster_k3_mean_p95"))
    assert isinstance(record, ClusterThresholdPolicyRecord)

    assert record.cluster_count == 3
    assert record.aggregation in ("mean", "robust_median")
    assert len(record.fingerprint_features) > 0
    assert isinstance(record.fingerprint_estimators, dict) is False  # must be an immutable Mapping, not a plain dict
    assert record.clustering.get("random_seed") is not None
    assert isinstance(record.required_diagnostics, tuple)


def test_federated_matched_exceedance_policy_retains_client_message_and_candidate_grid(
    resolved_threshold_policies,
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("federated_summary_matched_exceedance"))
    assert isinstance(record, FederatedMatchedExceedanceThresholdPolicyRecord)

    assert record.mode == "matched_exceedance"
    assert record.candidate_grid.get("minimum") is not None
    assert record.candidate_grid.get("maximum") is not None
    assert len(record.required_diagnostics) > 0


def test_split_conformal_policy_has_no_quantile_field(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("conformal_local_p95"))
    assert isinstance(record, SplitConformalThresholdPolicyRecord)
    assert not hasattr(record, "quantile")
    assert 0.0 <= record.nominal_coverage <= 1.0
