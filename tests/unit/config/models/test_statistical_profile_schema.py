"""Strict authored statistical-profile model tests."""

import pytest
from pydantic import ValidationError

from datp_core.configuration.models import StatisticalProfileConfig


def _bca_payload() -> dict[str, object]:
    return {
        "estimand": "mean_paired_seed_level_delta_between_two_evaluations",
        "unit_of_analysis": "training_seed",
        "method": "bca_bootstrap",
        "statistic": "arithmetic_mean_of_paired_deltas",
        "confidence_level": 0.95,
        "resample_count": 50000,
        "pairing_key": "seed",
        "minimum_paired_units": 10,
    }


def test_statistical_profile_rejects_unknown_field() -> None:
    payload = _bca_payload()
    payload["undeclared_field"] = "not declared"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        StatisticalProfileConfig.model_validate(payload)


def test_bootstrap_profile_requires_confidence_level_and_resample_count() -> None:
    payload = _bca_payload()
    del payload["confidence_level"]
    with pytest.raises(ValidationError, match="confidence_level"):
        StatisticalProfileConfig.model_validate(payload)

    payload = _bca_payload()
    del payload["resample_count"]
    with pytest.raises(ValidationError, match="resample_count"):
        StatisticalProfileConfig.model_validate(payload)


def test_non_bootstrap_profile_without_method_is_accepted() -> None:
    profile = StatisticalProfileConfig.model_validate(
        {
            "estimand": "paired_seed_level_rank_evidence",
            "unit_of_analysis": "training_seed",
            "role": "secondary_never_confirmatory",
            "procedures": ["wilcoxon_signed_rank", "matched_pairs_rank_biserial_correlation"],
            "wilcoxon_exact_when_possible": True,
        }
    )
    assert profile.method is None
    assert profile.role == "secondary_never_confirmatory"
    assert profile.confidence_level is None
