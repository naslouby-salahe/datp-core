from typing import cast

import pytest
from tests.unit.thresholding.helpers import COORDINATE, identity

from datp_core.domain.enums import AvailabilityStatus, FederatedThresholdMethod, KMeansInitialization
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    ByteCount,
    Checksum,
    ClusterIndex,
    CoverageTarget,
    FamilyIdentity,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Quantile,
    Ratio,
    RowCount,
    ScoreValue,
    Seed,
    ShrinkageWeight,
    SummaryCoefficient,
    ThresholdValue,
)
from datp_core.thresholding.models import (
    CentralizedAttainmentDiagnostic,
    ClientBenignSummary,
    ClusterFingerprint,
    ClusterMembership,
    CommunicationPayload,
    ConformalAssignment,
    ConformalThresholdResult,
    FamilyMembership,
    FamilyThresholdResult,
    FederatedStatisticsThresholdResult,
    FixedCoefficientResult,
    GroupedThresholdResult,
    LocalQuantile,
    LocalThresholdResult,
    PooledSharedQuantileResult,
    PooledVarianceDecomposition,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
    ShrinkageAssignment,
    ShrinkageThresholdResult,
    ThresholdAssignment,
    ThresholdDiagnostic,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
)

CLIENT_A = identity("client_a")
CLIENT_B = identity("client_b")
QUANTILE = Quantile(0.95)


def _diagnostic() -> ThresholdDiagnostic:
    return ThresholdDiagnostic(
        quantile_interpolation=None,
        score_set_checksum=Checksum("a" * 64),
        calibration_manifest_checksum=Checksum("b" * 64),
        tie_count=RowCount(0),
        availability=AvailabilityStatus.AVAILABLE,
    )


def _local_quantile(client, value: float, count: int = 120) -> LocalQuantile:
    return LocalQuantile(
        client=client,
        coordinate=COORDINATE,
        quantile=QUANTILE,
        value=ThresholdValue(value),
        calibration_count=RowCount(count),
        diagnostic=_diagnostic(),
    )


def test_threshold_diagnostic_rejects_negative_tie_count() -> None:
    def build() -> ThresholdDiagnostic:
        return ThresholdDiagnostic(
            quantile_interpolation=None,
            score_set_checksum=Checksum("a" * 64),
            calibration_manifest_checksum=Checksum("b" * 64),
            tie_count=RowCount(-1),
            availability=AvailabilityStatus.AVAILABLE,
        )

    with pytest.raises(ValueError, match="row count"):
        build()


def test_shared_threshold_result_requires_uniform_assignments() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 2.0))
    mismatched = (
        ThresholdAssignment(CLIENT_A, ThresholdValue(1.5)),
        ThresholdAssignment(CLIENT_B, ThresholdValue(1.5)),
    )

    def build() -> SharedThresholdResult:
        return SharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=ThresholdValue(1.6),
            assignments=mismatched,
        )

    with pytest.raises(ScientificContractError, match="identical shared value"):
        build()


def test_shared_threshold_result_accepts_consistent_assignments() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 2.0))
    shared_value = ThresholdValue(1.5)
    assignments = (ThresholdAssignment(CLIENT_A, shared_value), ThresholdAssignment(CLIENT_B, shared_value))
    result = SharedThresholdResult(
        coordinate=COORDINATE,
        quantile=QUANTILE,
        contributing_local_quantiles=local_quantiles,
        shared_threshold=shared_value,
        assignments=assignments,
    )
    assert result.shared_threshold == shared_value


def test_local_threshold_result_requires_assignment_to_match_own_quantile() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0),)
    wrong_assignments = (ThresholdAssignment(CLIENT_A, ThresholdValue(9.0)),)

    def build() -> LocalThresholdResult:
        return LocalThresholdResult(
            coordinate=COORDINATE,
            local_quantiles=local_quantiles,
            assignments=wrong_assignments,
        )

    with pytest.raises(ScientificContractError, match="own local quantile"):
        build()


def test_family_membership_available_requires_members_and_threshold() -> None:
    def build() -> FamilyMembership:
        return FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(),
            contributing_local_quantiles=(),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=None,
        )

    with pytest.raises(ScientificContractError, match="eligible members and a constructed threshold"):
        build()


def test_family_membership_unavailable_must_carry_no_threshold() -> None:
    def build() -> FamilyMembership:
        return FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A,),
            contributing_local_quantiles=(),
            status=AvailabilityStatus.UNAVAILABLE,
            family_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="no members and no threshold"):
        build()


def test_family_threshold_result_assignments_must_match_available_members() -> None:
    family = FamilyMembership(
        family_id=FamilyIdentity("doorbell"),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        status=AvailabilityStatus.AVAILABLE,
        family_threshold=ThresholdValue(1.0),
    )
    wrong_assignments = (ThresholdAssignment(CLIENT_B, ThresholdValue(1.0)),)

    def build() -> FamilyThresholdResult:
        return FamilyThresholdResult(
            coordinate=COORDINATE,
            families=(family,),
            assignments=wrong_assignments,
        )

    with pytest.raises(ScientificContractError, match="contributing client set"):
        build()


def test_cluster_membership_requires_at_least_one_member() -> None:
    def build() -> ClusterMembership:
        return ClusterMembership(
            cluster_index=ClusterIndex(0),
            members=(),
            contributing_local_quantiles=(),
            cluster_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="at least one member"):
        build()


def test_cluster_fingerprint_requires_exactly_four_features() -> None:
    short_raw = cast(tuple[float, float, float, float], (1.0, 2.0, 3.0))

    def build() -> ClusterFingerprint:
        return ClusterFingerprint(client=CLIENT_A, raw=short_raw, standardized=(1.0, 2.0, 3.0, 4.0))

    with pytest.raises(ScientificContractError, match="mean, standard deviation, skewness, and p95"):
        build()


def _cluster_protocol_fields() -> dict:
    return {
        "initialization": KMeansInitialization.KMEANS_PLUS_PLUS,
        "initialization_count": KMeansInitializationCount(10),
        "maximum_iterations": KMeansMaximumIterationCount(300),
        "random_state": Seed(42),
        "group_count": GroupCount(2),
    }


def test_grouped_threshold_result_requires_cluster_count_to_match_group_count() -> None:
    fingerprint = ClusterFingerprint(client=CLIENT_A, raw=(1.0, 1.0, 1.0, 1.0), standardized=(0.0, 0.0, 0.0, 0.0))
    membership = ClusterMembership(
        cluster_index=ClusterIndex(0),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        cluster_threshold=ThresholdValue(1.0),
    )

    def build() -> GroupedThresholdResult:
        return GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fingerprint,),
            clusters=(membership,),
            assignments=(ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),),
            **_cluster_protocol_fields(),
        )

    with pytest.raises(ScientificContractError, match="number of clusters must equal"):
        build()


def test_shrinkage_assignment_validates_the_blend_formula() -> None:
    def build() -> ShrinkageAssignment:
        return ShrinkageAssignment(
            client=CLIENT_A,
            lambda_weight=ShrinkageWeight(0.5),
            local_threshold=ThresholdValue(2.0),
            shared_threshold=ThresholdValue(4.0),
            blended_threshold=ThresholdValue(999.0),
        )

    with pytest.raises(ScientificContractError, match="lambda \\* local"):
        build()


def test_shrinkage_assignment_endpoint_zero_reproduces_shared_exactly() -> None:
    assignment = ShrinkageAssignment(
        client=CLIENT_A,
        lambda_weight=ShrinkageWeight(0.0),
        local_threshold=ThresholdValue(2.0),
        shared_threshold=ThresholdValue(4.0),
        blended_threshold=ThresholdValue(4.0),
    )
    assert assignment.blended_threshold.value == 4.0


def test_shrinkage_threshold_result_requires_every_weight_over_same_clients() -> None:
    complete_weight_assignments = (
        ShrinkageAssignment(
            CLIENT_A, ShrinkageWeight(0.0), ThresholdValue(1.0), ThresholdValue(2.0), ThresholdValue(2.0)
        ),
        ShrinkageAssignment(
            CLIENT_B, ShrinkageWeight(0.0), ThresholdValue(1.0), ThresholdValue(2.0), ThresholdValue(2.0)
        ),
        ShrinkageAssignment(
            CLIENT_A, ShrinkageWeight(1.0), ThresholdValue(1.0), ThresholdValue(2.0), ThresholdValue(1.0)
        ),
    )

    def build() -> ShrinkageThresholdResult:
        return ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.0), ShrinkageWeight(1.0)),
            assignments=complete_weight_assignments,
        )

    with pytest.raises(ScientificContractError, match="same client set"):
        build()


def test_conformal_assignment_rejects_rank_index_out_of_bounds() -> None:
    def build() -> ConformalAssignment:
        return ConformalAssignment(
            client=CLIENT_A,
            calibration_count=RowCount(10),
            rank_index=11,
            effective_quantile=Quantile(0.95),
            selected_score=ScoreValue(1.0),
            tie_count=RowCount(0),
            threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="within the calibration sample"):
        build()


def test_conformal_threshold_result_rejects_client_both_assigned_and_unavailable() -> None:
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=9,
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(1.0),
        tie_count=RowCount(0),
        threshold=ThresholdValue(1.0),
    )

    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
            eligible_clients=(CLIENT_A,),
            assignments=(assignment,),
            unavailable_clients=(CLIENT_A,),
        )

    with pytest.raises(ScientificContractError, match="cannot be both assigned and unavailable"):
        build()


def test_client_benign_summary_rejects_negative_variance() -> None:
    def build() -> ClientBenignSummary:
        return ClientBenignSummary(
            client=CLIENT_A, count=RowCount(10), mean=0.0, variance=-1.0, benign_exceedance_count=None
        )

    with pytest.raises(ScientificContractError, match="non-negative"):
        build()


def test_pooled_variance_decomposition_requires_the_additive_identity() -> None:
    def build() -> PooledVarianceDecomposition:
        return PooledVarianceDecomposition(
            global_mean=0.0,
            within_client_variance=1.0,
            between_client_variance=1.0,
            full_pooled_variance=3.0,
            between_ratio=None,
        )

    with pytest.raises(ScientificContractError, match="within-client plus between-client"):
        build()


def test_centralized_attainment_diagnostic_rejects_out_of_range_target() -> None:
    def build() -> CentralizedAttainmentDiagnostic:
        return CentralizedAttainmentDiagnostic(
            target_exceedance=Quantile(1.5),
            achieved_exceedance=Ratio(0.1),
            signed_attainment_error=0.0,
            absolute_attainment_error=Ratio(0.0),
            absolute_threshold_error_vs_pooled_quantile=0.0,
            relative_threshold_error_vs_pooled_quantile=None,
        )

    with pytest.raises(ValueError, match="quantile"):
        build()


def test_communication_payload_declares_fixed_fields() -> None:
    payload = CommunicationPayload(estimated_bytes=ByteCount(10))
    assert payload.fields == ("count", "mean", "variance")
    assert payload.estimated_bytes == ByteCount(10)


def test_fixed_coefficient_result_holds_its_value() -> None:
    result = FixedCoefficientResult(coefficient=SummaryCoefficient(2.0), threshold=ThresholdValue(3.0))
    assert result.threshold.value == 3.0


def test_threshold_unavailable_result_requires_a_detail() -> None:
    def build() -> ThresholdUnavailableResult:
        return ThresholdUnavailableResult(
            method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
            coordinate=COORDINATE,
            reason=ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED,
            detail="   ",
        )

    with pytest.raises(ScientificContractError, match="human-readable detail"):
        build()


def test_family_membership_rejects_quantile_clients_mismatched_with_members() -> None:
    def build() -> FamilyMembership:
        return FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A,),
            contributing_local_quantiles=(_local_quantile(CLIENT_B, 1.0),),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="exactly match declared family members"):
        build()


def test_family_membership_rejects_duplicate_quantile_clients() -> None:
    def build() -> FamilyMembership:
        return FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A, CLIENT_B),
            contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_A, 2.0)),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_family_threshold_result_rejects_assignment_not_matching_family_threshold() -> None:
    family = FamilyMembership(
        family_id=FamilyIdentity("doorbell"),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        status=AvailabilityStatus.AVAILABLE,
        family_threshold=ThresholdValue(1.0),
    )
    wrong_assignments = (ThresholdAssignment(CLIENT_A, ThresholdValue(9.0)),)

    def build() -> FamilyThresholdResult:
        return FamilyThresholdResult(
            coordinate=COORDINATE,
            families=(family,),
            assignments=wrong_assignments,
        )

    with pytest.raises(ScientificContractError, match="family's constructed threshold"):
        build()


def test_shrinkage_threshold_result_rejects_empty_assignments() -> None:
    def build() -> ShrinkageThresholdResult:
        return ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.0),),
            assignments=(),
        )

    with pytest.raises(ScientificContractError, match="at least one client assignment"):
        build()


def test_shrinkage_threshold_result_rejects_duplicate_client_weight_pair() -> None:
    duped = (
        ShrinkageAssignment(
            CLIENT_A, ShrinkageWeight(0.0), ThresholdValue(1.0), ThresholdValue(2.0), ThresholdValue(2.0)
        ),
        ShrinkageAssignment(
            CLIENT_B, ShrinkageWeight(0.0), ThresholdValue(5.0), ThresholdValue(2.0), ThresholdValue(2.0)
        ),
        ShrinkageAssignment(
            CLIENT_A, ShrinkageWeight(0.0), ThresholdValue(1.0), ThresholdValue(2.0), ThresholdValue(2.0)
        ),
    )

    def build() -> ShrinkageThresholdResult:
        return ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.0),),
            assignments=duped,
        )

    with pytest.raises(ScientificContractError, match="exactly one shrinkage assignment"):
        build()


def test_conformal_threshold_result_requires_at_least_one_assignment() -> None:
    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
            eligible_clients=(),
            assignments=(),
            unavailable_clients=(),
        )

    with pytest.raises(ScientificContractError, match="at least one assigned client"):
        build()


def test_conformal_threshold_result_rejects_duplicate_assignments() -> None:
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=9,
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(1.0),
        tie_count=RowCount(0),
        threshold=ThresholdValue(1.0),
    )
    duped = (assignment, assignment)

    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
            eligible_clients=(CLIENT_A,),
            assignments=duped,
            unavailable_clients=(),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_conformal_threshold_result_rejects_duplicate_unavailable_clients() -> None:
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=9,
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(1.0),
        tie_count=RowCount(0),
        threshold=ThresholdValue(1.0),
    )

    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
            eligible_clients=(CLIENT_A, CLIENT_B),
            assignments=(assignment,),
            unavailable_clients=(CLIENT_B, CLIENT_B),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_federated_statistics_result_uses_centralized_pooled_quantile_diagnostic_field() -> None:
    fields = {field.name for field in FederatedStatisticsThresholdResult.__dataclass_fields__.values()}
    assert "centralized_pooled_quantile_diagnostic" in fields
    assert "centralized_attainment_diagnostic" in fields
    assert "matched_diagnostic" not in fields
    assert "exact_pooled_quantile_reference" not in fields


# ── ConformalAssignment invariants ──


def test_conformal_assignment_rejects_threshold_not_equal_to_selected_score() -> None:
    def build() -> ConformalAssignment:
        return ConformalAssignment(
            client=CLIENT_A,
            calibration_count=RowCount(10),
            rank_index=5,
            effective_quantile=Quantile(0.5),
            selected_score=ScoreValue(3.0),
            tie_count=RowCount(0),
            threshold=ThresholdValue(9.0),
        )

    with pytest.raises(ScientificContractError, match="selected score"):
        build()


def test_conformal_assignment_rejects_effective_quantile_not_equal_to_rank_over_count() -> None:
    def build() -> ConformalAssignment:
        return ConformalAssignment(
            client=CLIENT_A,
            calibration_count=RowCount(10),
            rank_index=5,
            effective_quantile=Quantile(0.9),
            selected_score=ScoreValue(3.0),
            tie_count=RowCount(0),
            threshold=ThresholdValue(3.0),
        )

    with pytest.raises(ScientificContractError, match="effective quantile"):
        build()


# ── ConformalThresholdResult coverage ──


def test_conformal_threshold_result_rejects_incomplete_client_coverage() -> None:
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=9,
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(1.0),
        tie_count=RowCount(0),
        threshold=ThresholdValue(1.0),
    )

    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
            eligible_clients=(CLIENT_A, CLIENT_B),
            assignments=(assignment,),
            unavailable_clients=(),
        )

    with pytest.raises(ScientificContractError, match="exactly cover"):
        build()


# ── ClusterFingerprint finiteness ──


def test_cluster_fingerprint_rejects_non_finite_raw_feature() -> None:
    def build() -> ClusterFingerprint:
        return ClusterFingerprint(
            client=CLIENT_A,
            raw=(1.0, 2.0, float("nan"), 4.0),
            standardized=(0.0, 0.0, 0.0, 0.0),
        )

    with pytest.raises(ScientificContractError, match="finite"):
        build()


def test_cluster_fingerprint_rejects_non_finite_standardized_feature() -> None:
    def build() -> ClusterFingerprint:
        return ClusterFingerprint(
            client=CLIENT_A,
            raw=(1.0, 2.0, 3.0, 4.0),
            standardized=(0.0, float("inf"), 0.0, 0.0),
        )

    with pytest.raises(ScientificContractError, match="finite"):
        build()


# ── ClusterMembership ──


def test_cluster_membership_rejects_duplicate_members() -> None:
    def build() -> ClusterMembership:
        return ClusterMembership(
            cluster_index=ClusterIndex(0),
            members=(CLIENT_A, CLIENT_A),
            contributing_local_quantiles=(
                _local_quantile(CLIENT_A, 1.0),
                _local_quantile(CLIENT_A, 2.0),
            ),
            cluster_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_cluster_membership_rejects_quantile_clients_not_equal_to_members() -> None:
    def build() -> ClusterMembership:
        return ClusterMembership(
            cluster_index=ClusterIndex(0),
            members=(CLIENT_A,),
            contributing_local_quantiles=(_local_quantile(CLIENT_B, 1.0),),
            cluster_threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="exactly equal cluster members"):
        build()


# ── GroupedThresholdResult ──


def test_grouped_threshold_result_rejects_assignment_not_matching_cluster_threshold() -> None:
    fp_a = ClusterFingerprint(client=CLIENT_A, raw=(1.0, 1.0, 1.0, 1.0), standardized=(0.0, 0.0, 0.0, 0.0))
    fp_b = ClusterFingerprint(client=CLIENT_B, raw=(2.0, 2.0, 2.0, 2.0), standardized=(0.0, 0.0, 0.0, 0.0))

    def build() -> GroupedThresholdResult:
        return GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fp_a, fp_b),
            clusters=(
                ClusterMembership(
                    cluster_index=ClusterIndex(0),
                    members=(CLIENT_A,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
                    cluster_threshold=ThresholdValue(1.0),
                ),
                ClusterMembership(
                    cluster_index=ClusterIndex(1),
                    members=(CLIENT_B,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_B, 2.0),),
                    cluster_threshold=ThresholdValue(2.0),
                ),
            ),
            assignments=(
                ThresholdAssignment(CLIENT_A, ThresholdValue(99.0)),
                ThresholdAssignment(CLIENT_B, ThresholdValue(2.0)),
            ),
            **_cluster_protocol_fields(),
        )

    with pytest.raises(ScientificContractError, match="cluster's threshold"):
        build()


def test_grouped_threshold_result_rejects_duplicate_fingerprint_clients() -> None:
    fp_a = ClusterFingerprint(client=CLIENT_A, raw=(1.0, 1.0, 1.0, 1.0), standardized=(0.0, 0.0, 0.0, 0.0))
    fp_a2 = ClusterFingerprint(client=CLIENT_A, raw=(2.0, 2.0, 2.0, 2.0), standardized=(1.0, 1.0, 1.0, 1.0))
    fp_b = ClusterFingerprint(client=CLIENT_B, raw=(3.0, 3.0, 3.0, 3.0), standardized=(0.0, 0.0, 0.0, 0.0))

    def build() -> GroupedThresholdResult:
        return GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fp_a, fp_a2, fp_b),
            clusters=(
                ClusterMembership(
                    cluster_index=ClusterIndex(0),
                    members=(CLIENT_A,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
                    cluster_threshold=ThresholdValue(1.0),
                ),
                ClusterMembership(
                    cluster_index=ClusterIndex(1),
                    members=(CLIENT_B,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_B, 2.0),),
                    cluster_threshold=ThresholdValue(2.0),
                ),
            ),
            assignments=(
                ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),
                ThresholdAssignment(CLIENT_B, ThresholdValue(2.0)),
            ),
            **_cluster_protocol_fields(),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_grouped_threshold_result_rejects_duplicate_cluster_indices() -> None:
    fp_a = ClusterFingerprint(client=CLIENT_A, raw=(1.0, 1.0, 1.0, 1.0), standardized=(0.0, 0.0, 0.0, 0.0))
    fp_b = ClusterFingerprint(client=CLIENT_B, raw=(2.0, 2.0, 2.0, 2.0), standardized=(0.0, 0.0, 0.0, 0.0))

    def build() -> GroupedThresholdResult:
        return GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fp_a, fp_b),
            clusters=(
                ClusterMembership(
                    cluster_index=ClusterIndex(0),
                    members=(CLIENT_A,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
                    cluster_threshold=ThresholdValue(1.0),
                ),
                ClusterMembership(
                    cluster_index=ClusterIndex(0),
                    members=(CLIENT_B,),
                    contributing_local_quantiles=(_local_quantile(CLIENT_B, 2.0),),
                    cluster_threshold=ThresholdValue(2.0),
                ),
            ),
            assignments=(
                ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),
                ThresholdAssignment(CLIENT_B, ThresholdValue(2.0)),
            ),
            **_cluster_protocol_fields(),
        )

    with pytest.raises(ScientificContractError, match="cluster indices must equal exactly"):
        build()


# ── Shrinkage ──


def test_shrinkage_threshold_result_rejects_duplicate_declared_weights() -> None:
    def build() -> ShrinkageThresholdResult:
        return ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.5), ShrinkageWeight(0.5)),
            assignments=(),
        )

    with pytest.raises(ScientificContractError, match="unique"):
        build()


def test_shrinkage_threshold_result_rejects_undeclared_weight_in_assignment() -> None:
    def build() -> ShrinkageThresholdResult:
        return ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.0),),
            assignments=(
                ShrinkageAssignment(
                    CLIENT_A, ShrinkageWeight(0.5), ThresholdValue(3.0), ThresholdValue(3.0), ThresholdValue(3.0)
                ),
            ),
        )

    with pytest.raises(ScientificContractError, match="declared lambda weight"):
        build()


# ── Federated statistics ──


def test_federated_statistics_result_rejects_duplicate_client_summaries() -> None:
    summary = ClientBenignSummary(
        client=CLIENT_A, count=RowCount(10), mean=0.0, variance=1.0, benign_exceedance_count=None
    )

    def build() -> FederatedStatisticsThresholdResult:
        return FederatedStatisticsThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            client_summaries=(summary, summary),
            decomposition=PooledVarianceDecomposition(
                global_mean=0.0,
                within_client_variance=0.5,
                between_client_variance=0.5,
                full_pooled_variance=1.0,
                between_ratio=Ratio(0.5),
            ),
            matched_threshold=ThresholdValue(1.0),
            centralized_attainment_diagnostic=CentralizedAttainmentDiagnostic(
                target_exceedance=Quantile(0.05),
                achieved_exceedance=Ratio(0.05),
                signed_attainment_error=0.0,
                absolute_attainment_error=Ratio(0.0),
                absolute_threshold_error_vs_pooled_quantile=0.0,
                relative_threshold_error_vs_pooled_quantile=None,
            ),
            centralized_pooled_quantile_diagnostic=ThresholdValue(1.0),
            fixed_coefficient_curve=(),
            assignments=(ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),),
            communication_payload=CommunicationPayload(estimated_bytes=ByteCount(10)),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_client_benign_summary_rejects_non_finite_mean() -> None:
    def build() -> ClientBenignSummary:
        return ClientBenignSummary(
            client=CLIENT_A,
            count=RowCount(10),
            mean=float("inf"),
            variance=1.0,
            benign_exceedance_count=None,
        )

    with pytest.raises(ScientificContractError, match="finite"):
        build()


def test_client_benign_summary_rejects_exceedance_count_exceeding_count() -> None:
    def build() -> ClientBenignSummary:
        return ClientBenignSummary(
            client=CLIENT_A,
            count=RowCount(10),
            mean=0.0,
            variance=1.0,
            benign_exceedance_count=RowCount(11),
        )

    with pytest.raises(ScientificContractError, match="cannot exceed"):
        build()


# ── Shared / Local duplicate clients ──


def test_shared_threshold_result_rejects_duplicate_contributing_clients() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_A, 2.0))
    shared_value = ThresholdValue(1.5)
    assignments = (ThresholdAssignment(CLIENT_A, shared_value),)

    def build() -> SharedThresholdResult:
        return SharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=shared_value,
            assignments=assignments,
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_pooled_shared_quantile_rejects_duplicate_assignments() -> None:
    def build() -> PooledSharedQuantileResult:
        return PooledSharedQuantileResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            pooled_benign_score_count=RowCount(100),
            diagnostic=_diagnostic(),
            shared_threshold=ThresholdValue(1.0),
            assignments=(
                ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),
                ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),
            ),
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_local_threshold_result_rejects_duplicate_local_quantiles() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_A, 2.0))
    assignments = (
        ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),
        ThresholdAssignment(CLIENT_A, ThresholdValue(2.0)),
    )

    def build() -> LocalThresholdResult:
        return LocalThresholdResult(
            coordinate=COORDINATE,
            local_quantiles=local_quantiles,
            assignments=assignments,
        )

    with pytest.raises(ScientificContractError, match="unique client identities"):
        build()


def test_shared_threshold_result_rejects_inconsistent_threshold_formula() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 3.0))
    wrong_shared_value = ThresholdValue(5.0)
    assignments = (ThresholdAssignment(CLIENT_A, wrong_shared_value), ThresholdAssignment(CLIENT_B, wrong_shared_value))

    with pytest.raises(ScientificContractError, match="unweighted mean"):
        SharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=wrong_shared_value,
            assignments=assignments,
        )


def test_sample_weighted_shared_threshold_result_rejects_inconsistent_threshold_formula() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 3.0))
    weights = (0.5, 0.5)
    wrong_shared_value = ThresholdValue(9.0)
    assignments = (ThresholdAssignment(CLIENT_A, wrong_shared_value), ThresholdAssignment(CLIENT_B, wrong_shared_value))

    with pytest.raises(ScientificContractError, match="normalized weighted mean"):
        SampleWeightedSharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            normalized_weights=weights,
            shared_threshold=wrong_shared_value,
            assignments=assignments,
        )


def test_family_membership_rejects_inconsistent_family_threshold_formula() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 3.0))
    wrong_family_threshold = ThresholdValue(10.0)

    with pytest.raises(ScientificContractError, match="unweighted mean"):
        FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A, CLIENT_B),
            contributing_local_quantiles=local_quantiles,
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=wrong_family_threshold,
        )


def test_cluster_membership_rejects_inconsistent_cluster_threshold_formula() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 3.0))
    wrong_cluster_threshold = ThresholdValue(10.0)

    with pytest.raises(ScientificContractError, match="unweighted mean"):
        ClusterMembership(
            cluster_index=ClusterIndex(0),
            members=(CLIENT_A, CLIENT_B),
            contributing_local_quantiles=local_quantiles,
            cluster_threshold=wrong_cluster_threshold,
        )


def test_grouped_threshold_result_rejects_out_of_range_or_non_canonical_cluster_indices() -> None:
    cluster_a = ClusterMembership(
        cluster_index=ClusterIndex(1),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        cluster_threshold=ThresholdValue(1.0),
    )
    fp_a = ClusterFingerprint(CLIENT_A, raw=(1.0, 1.0, 1.0, 1.0), standardized=(1.0, 1.0, 1.0, 1.0))
    assignment = ThresholdAssignment(CLIENT_A, ThresholdValue(1.0))

    with pytest.raises(ScientificContractError, match=r"cluster indices must equal exactly 0\.\.group_count"):
        GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fp_a,),
            clusters=(cluster_a,),
            assignments=(assignment,),
            initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
            initialization_count=KMeansInitializationCount(10),
            maximum_iterations=KMeansMaximumIterationCount(300),
            random_state=Seed(42),
            group_count=GroupCount(1),
        )


def test_centralized_attainment_diagnostic_rejects_inconsistent_signed_error() -> None:
    with pytest.raises(ScientificContractError, match="signed attainment error"):
        CentralizedAttainmentDiagnostic(
            target_exceedance=Quantile(0.05),
            achieved_exceedance=Ratio(0.10),
            signed_attainment_error=0.0,
            absolute_attainment_error=Ratio(0.05),
            absolute_threshold_error_vs_pooled_quantile=0.0,
            relative_threshold_error_vs_pooled_quantile=None,
        )


def test_centralized_attainment_diagnostic_rejects_inconsistent_absolute_error() -> None:
    with pytest.raises(ScientificContractError, match="absolute attainment error"):
        CentralizedAttainmentDiagnostic(
            target_exceedance=Quantile(0.05),
            achieved_exceedance=Ratio(0.10),
            signed_attainment_error=0.05,
            absolute_attainment_error=Ratio(0.99),
            absolute_threshold_error_vs_pooled_quantile=0.0,
            relative_threshold_error_vs_pooled_quantile=None,
        )


def test_centralized_attainment_diagnostic_rejects_non_finite_fields() -> None:
    with pytest.raises(ValueError, match="quantile"):
        CentralizedAttainmentDiagnostic(
            target_exceedance=Quantile(float("nan")),
            achieved_exceedance=Ratio(0.10),
            signed_attainment_error=0.05,
            absolute_attainment_error=Ratio(0.05),
            absolute_threshold_error_vs_pooled_quantile=0.0,
            relative_threshold_error_vs_pooled_quantile=None,
        )
