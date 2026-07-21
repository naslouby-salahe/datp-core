"""Configuration-time guards for locked scientific contracts."""

import pytest
from pydantic import ValidationError

from datp_core.config.models.protocol_config import (
    ClusterThresholdPolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
    SeedCohortConfig,
)


def test_seed_cohort_rejects_duplicate_or_count_mismatched_seeds() -> None:
    with pytest.raises(ValidationError, match="unique"):
        SeedCohortConfig(
            paired_seed_count=2, training_seeds=[1, 1], bootstrap_analysis_seed=300, analysis_seed_model="fixed"
        )
    with pytest.raises(ValidationError, match="paired_seed_count"):
        SeedCohortConfig(
            paired_seed_count=2, training_seeds=[1], bootstrap_analysis_seed=300, analysis_seed_model="fixed"
        )


def test_canonical_b4_rejects_noncanonical_cluster_count() -> None:
    with pytest.raises(ValidationError, match="cluster_count=3"):
        ClusterThresholdPolicyConfig.model_validate(
            {
                "policy": "cluster_threshold",
                "canonical": True,
                "aggregation": "mean",
                "cluster_count": 2,
                "quantile": 0.95,
                "quantile_estimator": "linear",
                "aggregated_quantity": "local_thresholds",
                "aggregation_formula": "mean",
                "sample_weighting": "none",
                "client_accumulation_order": "ascending",
                "fingerprint_features": ["mean"],
                "fingerprint_estimators": {"mean": "arithmetic_mean"},
                "fingerprint_degenerate_client_rules": {},
                "fingerprint_non_finite_value_behavior": "fail",
                "standardization": {},
                "client_ordering_before_fit": "ascending",
                "clustering": {},
                "label_canonicalization": "ascending",
                "insufficient_eligible_clients_behavior": "unavailable",
                "degenerate_fingerprint_matrix_behavior": "unavailable",
                "required_diagnostics": [],
                "threshold_ownership": "cluster",
            }
        )


def test_shrinkage_rejects_out_of_range_locked_weight() -> None:
    with pytest.raises(ValidationError, match="permitted_weight_range"):
        LocalGlobalShrinkagePolicyConfig.model_validate(
            {
                "policy": "local_global_shrinkage_threshold",
                "quantile": 0.95,
                "quantile_estimator": "linear",
                "local_reference": "local",
                "global_reference": "global",
                "interpolation_formula": "linear",
                "weight_semantics": "local",
                "weight_scope": "global",
                "permitted_weight_range": {"minimum": 0.0, "maximum": 1.0},
                "shrinkage_weight_grid": [0.0, 1.5],
                "shrinkage_weight": None,
                "shrinkage_weight_resolution": "authored",
                "out_of_range_weight_behavior": "reject",
                "effective_lambda_reporting": "required",
                "threshold_ownership": "client",
            }
        )
