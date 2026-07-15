from datp_core.domain.thresholding.federated_statistics import ThresholdComparatorRole
from datp_core.domain.thresholding.policies import (
    CoreThresholdPolicy,
    SharedThresholdConstruction,
    ThresholdConstructionKind,
)
from datp_core.domain.thresholding.variants import ConformalMode, ThresholdVariant


def test_core_ladder_has_exactly_the_four_threshold_scope_policies() -> None:
    assert tuple(CoreThresholdPolicy) == (
        CoreThresholdPolicy.B1,
        CoreThresholdPolicy.B2,
        CoreThresholdPolicy.B3,
        CoreThresholdPolicy.B4,
    )
    assert ThresholdComparatorRole.CENTRALIZED_MODEL_B0 not in CoreThresholdPolicy
    assert ThresholdComparatorRole.FED_STATS_BENIGN not in CoreThresholdPolicy


def test_threshold_construction_vocabulary_is_closed_and_stable() -> None:
    assert tuple(ThresholdConstructionKind) == (
        ThresholdConstructionKind.SHARED,
        ThresholdConstructionKind.LOCAL,
        ThresholdConstructionKind.FAMILY,
        ThresholdConstructionKind.CLUSTER,
        ThresholdConstructionKind.ROBUST_CLUSTER_MEDIAN,
        ThresholdConstructionKind.SHRINKAGE,
        ThresholdConstructionKind.CALIB_SIZE_FALLBACK,
        ThresholdConstructionKind.CONFORMAL,
        ThresholdConstructionKind.FED_STATS_BENIGN,
    )
    assert tuple(SharedThresholdConstruction) == (
        SharedThresholdConstruction.MEAN,
        SharedThresholdConstruction.POOLED,
        SharedThresholdConstruction.WEIGHTED,
    )


def test_variants_and_comparators_use_current_non_ladder_names() -> None:
    assert tuple(ThresholdVariant) == (
        ThresholdVariant.SHRINKAGE_LGS,
        ThresholdVariant.CALIB_SIZE_FALLBACK,
        ThresholdVariant.CONFORMAL_B2,
        ThresholdVariant.ROBUST_CLUSTER_MEDIAN_B4,
    )
    assert tuple(ConformalMode) == (ConformalMode.SPLIT, ConformalMode.FEDERATED)
    assert tuple(ThresholdComparatorRole) == (
        ThresholdComparatorRole.CENTRALIZED_MODEL_B0,
        ThresholdComparatorRole.FED_STATS_BENIGN,
    )
    for enum_type in (
        CoreThresholdPolicy,
        SharedThresholdConstruction,
        ThresholdConstructionKind,
        ThresholdVariant,
        ConformalMode,
        ThresholdComparatorRole,
    ):
        assert all("b5" not in member.value and "laridi" not in member.value for member in enum_type)
