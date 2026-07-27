"""Every resolved threshold policy is a frozen typed domain record."""

from __future__ import annotations

import pydantic
import pytest

from datp_core.config.authored.protocols.thresholds import (
    FederatedFixedCoefficientPolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
)
from datp_core.config.errors import ConfigurationError
from datp_core.config.project import resolve_project_configuration
from datp_core.config.resolution.protocols.thresholds import resolve_threshold_policy
from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.thresholding.enums import ThresholdPolicyKind
from datp_core.thresholding.policies import (
    CalibrationFallbackPolicy,
    ClusterPolicy,
    ConformalPolicy,
    FederatedFixedPolicy,
    FederatedMatchedPolicy,
    FixedShrinkagePolicy,
    QuantilePolicy,
    ThresholdPolicyRecord,
)

_EXPECTED_KIND_BY_POLICY_ID: dict[str, str] = {
    "shared_mean_p95": "shared_mean",
    "shared_pooled_p95": "shared_pooled",
    "shared_weighted_p95": "shared_weighted",
    "local_p95": "local_quantile",
    "family_p95": "family_mean",
    "centralized_pooled_p95": "shared_pooled",
    "cluster_k3_mean_p95": "cluster",
    "cluster_k9_mean_p95": "cluster",
    "cluster_k3_robust_median_p95": "cluster",
    "conformal_local_p95": "conformal",
    "local_global_shrinkage_p95": "shrinkage",
    "calibration_size_aware_fallback_p95": "calibration_fallback",
    "federated_summary_matched_exceedance": "federated_matched",
    "federated_summary_fixed_k": "federated_fixed",
}


@pytest.fixture(scope="module")
def resolved_threshold_policies() -> TypedDomainRegistry[ThresholdPolicyId, ThresholdPolicyRecord]:
    cfg = resolve_project_configuration()
    return cfg.threshold_policies


def test_every_authored_threshold_policy_identifier_is_covered(
    resolved_threshold_policies,
) -> None:
    resolved_ids = {str(pid) for pid in resolved_threshold_policies}
    assert resolved_ids == set(_EXPECTED_KIND_BY_POLICY_ID)


@pytest.mark.parametrize("policy_key,expected_kind", sorted(_EXPECTED_KIND_BY_POLICY_ID.items()))
def test_resolved_threshold_policy_has_expected_kind(
    resolved_threshold_policies, policy_key: str, expected_kind: str
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId(policy_key))
    assert record.kind.value == expected_kind
    assert isinstance(record, pydantic.BaseModel)
    assert record.model_config.get("frozen") is True


@pytest.mark.parametrize("policy_key", sorted(_EXPECTED_KIND_BY_POLICY_ID))
def test_resolved_threshold_policy_record_is_frozen(resolved_threshold_policies, policy_key: str) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId(policy_key))
    first_field = next(iter(type(record).model_fields))
    current_value = getattr(record, first_field)

    with pytest.raises(pydantic.ValidationError):
        setattr(record, first_field, current_value)


def test_cluster_policy_retains_executable_fields_losslessly(
    resolved_threshold_policies,
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("cluster_k3_mean_p95"))
    assert isinstance(record, ClusterPolicy)

    assert record.cluster_count == 3
    assert record.aggregation.value == "mean"
    assert len(record.fingerprint_features) == 4
    assert record.kmeans_random_seed is not None
    assert record.kmeans_initialization_runs >= 1
    assert record.kmeans_maximum_iterations >= 1
    assert record.kmeans_convergence_tolerance > 0.0


def test_federated_matched_policy_retains_grid_fields(
    resolved_threshold_policies,
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("federated_summary_matched_exceedance"))
    assert isinstance(record, FederatedMatchedPolicy)

    assert record.candidate_grid_minimum is not None
    assert record.candidate_grid_maximum is not None
    assert record.candidate_grid_step is not None
    assert record.candidate_grid_step > 0.0


def test_conformal_policy_has_coverage_alpha_not_quantile(
    resolved_threshold_policies,
) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("conformal_local_p95"))
    assert isinstance(record, ConformalPolicy)
    assert not hasattr(record, "quantile")
    assert 0.0 < record.coverage_alpha < 1.0
    assert record.minimum_sample_count >= 1


def test_shrinkage_policy_has_weight(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("local_global_shrinkage_p95"))
    assert isinstance(record, FixedShrinkagePolicy)
    assert record.kind.value == "shrinkage"


def test_fallback_policy_has_n_half(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("calibration_size_aware_fallback_p95"))
    assert isinstance(record, CalibrationFallbackPolicy)
    assert record.kind.value == "calibration_fallback"
    assert record.n_half > 0


def test_quantile_policy_has_quantile_in_range(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("shared_mean_p95"))
    assert isinstance(record, QuantilePolicy)
    assert 0.0 < record.quantile < 1.0


def test_federated_fixed_policy_has_fixed_coefficient(resolved_threshold_policies) -> None:
    record = resolved_threshold_policies.get(ThresholdPolicyId("federated_summary_fixed_k"))
    assert isinstance(record, FederatedFixedPolicy)
    assert record.kind.value == "federated_fixed"


# --- None-rejection: Pydantic field type prevents None at construction ---


def test_fixed_shrinkage_policy_shrinkage_weight_is_not_optional() -> None:
    """shrinkage_weight field is typed float, not float | None."""
    field = FixedShrinkagePolicy.model_fields["shrinkage_weight"]
    assert field.annotation is float


def test_federated_fixed_policy_fixed_coefficient_is_not_optional() -> None:
    """fixed_coefficient field is typed float, not float | None."""
    field = FederatedFixedPolicy.model_fields["fixed_coefficient"]
    assert field.annotation is float


# --- None-rejection: Runtime instantiation with None raises ValidationError ---


def test_fixed_shrinkage_policy_instantiation_rejects_none() -> None:
    """Passing shrinkage_weight=None raises pydantic.ValidationError."""
    with pytest.raises(pydantic.ValidationError):
        FixedShrinkagePolicy(
            kind=ThresholdPolicyKind.SHRINKAGE,
            quantile=0.95,
            shrinkage_weight=None,
        )


def test_federated_fixed_policy_instantiation_rejects_none() -> None:
    """Passing fixed_coefficient=None raises pydantic.ValidationError."""
    with pytest.raises(pydantic.ValidationError):
        FederatedFixedPolicy(
            kind=ThresholdPolicyKind.FEDERATED_FIXED,
            quantile=0.95,
            fixed_coefficient=None,
        )


# --- None-rejection: Config resolver rejects unresolved sweep values ---


def test_resolver_rejects_none_shrinkage_weight() -> None:
    """resolve_threshold_policy raises ConfigurationError when shrinkage_weight is None."""
    cfg = LocalGlobalShrinkagePolicyConfig(
        policy="local_global_shrinkage_threshold",
        quantile=0.95,
        shrinkage_weight_grid=[0.1, 0.5, 0.9],
        shrinkage_weight=None,
        threshold_ownership="shared",
    )
    with pytest.raises(ConfigurationError, match="shrinkage_weight is None"):
        resolve_threshold_policy(cfg)


def test_resolver_rejects_none_fixed_k() -> None:
    """resolve_threshold_policy raises ConfigurationError when fixed_k is None."""
    cfg = FederatedFixedCoefficientPolicyConfig(
        policy="federated_summary_statistic_threshold",
        mode="fixed_k",
        quantile=0.95,
        fixed_k_grid=[1.0, 2.0, 3.0],
        fixed_k=None,
        threshold_ownership="shared",
    )
    with pytest.raises(ConfigurationError, match="fixed_k is None"):
        resolve_threshold_policy(cfg)
