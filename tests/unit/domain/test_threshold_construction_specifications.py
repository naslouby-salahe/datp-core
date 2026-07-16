from dataclasses import fields
from decimal import Decimal
from typing import get_args

import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.thresholding.federated_statistics import (
    FedStatsBenignThresholdSpec,
    ThresholdComparatorRole,
)
from datp_core.domain.thresholding.policies import (
    B0PooledThresholdSpec,
    ClusterThresholdSpec,
    FamilyThresholdSpec,
    LocalThresholdSpec,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdConstructionKind,
    ThresholdConstructionSpec,
    ThresholdPercentile,
    compute_b0_pooled_threshold,
)
from datp_core.domain.thresholding.variants import (
    CalibrationSizeFallbackThresholdSpec,
    ConformalThresholdSpec,
    RobustClusterMedianThresholdSpec,
    ShrinkageThresholdSpec,
)


def test_threshold_construction_union_has_exactly_nine_tagged_members() -> None:
    members = get_args(ThresholdConstructionSpec)

    assert members == (
        SharedThresholdSpec,
        LocalThresholdSpec,
        FamilyThresholdSpec,
        ClusterThresholdSpec,
        RobustClusterMedianThresholdSpec,
        ShrinkageThresholdSpec,
        CalibrationSizeFallbackThresholdSpec,
        ConformalThresholdSpec,
        FedStatsBenignThresholdSpec,
    )
    assert all("kind" in {entry.name for entry in fields(member)} for member in members)


def test_explicit_kind_controls_variant_construction() -> None:
    percentile = ThresholdPercentile(value="0.95")
    shared = SharedThresholdSpec(
        kind=ThresholdConstructionKind.SHARED,
        percentile=percentile,
        construction=SharedThresholdConstruction.MEAN,
        estimator=QuantileEstimatorType.LOCAL_EXACT,
    )
    local = LocalThresholdSpec(
        kind=ThresholdConstructionKind.LOCAL,
        percentile=percentile,
        estimator=QuantileEstimatorType.LOCAL_EXACT,
    )

    assert shared.kind is ThresholdConstructionKind.SHARED
    assert local.kind is ThresholdConstructionKind.LOCAL
    with pytest.raises(DomainValidationError):
        LocalThresholdSpec(
            kind=ThresholdConstructionKind.SHARED,
            percentile=percentile,
            estimator=QuantileEstimatorType.LOCAL_EXACT,
        )


def test_union_has_no_test_attack_or_b0_surface() -> None:
    forbidden = ("test", "attack", "centralized", "b0")
    field_names = {entry.name for member in get_args(ThresholdConstructionSpec) for entry in fields(member)}

    assert all(fragment not in name.casefold() for fragment in forbidden for name in field_names)
    assert ThresholdComparatorRole.CENTRALIZED_MODEL_B0 not in ThresholdConstructionKind


def test_b0_pooled_threshold_spec_is_locked_to_p95_and_excluded_from_the_ladder_union() -> None:
    locked = B0PooledThresholdSpec(percentile=ThresholdPercentile(value="0.95"))

    non_locked_percentile = ThresholdPercentile(value="0.90")

    assert locked.percentile.value == Decimal("0.95")
    assert B0PooledThresholdSpec not in get_args(ThresholdConstructionSpec)
    with pytest.raises(DomainValidationError):
        B0PooledThresholdSpec(percentile=non_locked_percentile)


def test_compute_b0_pooled_threshold_matches_the_exact_p95_of_the_pooled_scores() -> None:
    spec = B0PooledThresholdSpec(percentile=ThresholdPercentile(value="0.95"))
    pooled_scores = tuple(float(value) for value in range(1, 101))

    threshold = compute_b0_pooled_threshold(pooled_calibration_scores=pooled_scores, spec=spec)

    assert threshold.value == 95.0
