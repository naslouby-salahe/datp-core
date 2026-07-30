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
    ClientBenignSummary,
    ClusterFingerprint,
    ClusterMembership,
    CommunicationPayload,
    ConformalAssignment,
    ConformalThresholdResult,
    FamilyMembership,
    FamilyThresholdResult,
    FixedCoefficientResult,
    GroupedThresholdResult,
    LocalQuantile,
    LocalThresholdResult,
    MatchedAttainmentDiagnostic,
    PooledVarianceDecomposition,
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
        tie_count=0,
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
            tie_count=-1,
            availability=AvailabilityStatus.AVAILABLE,
        )

    with pytest.raises(ScientificContractError, match="non-negative"):
        build()


def test_shared_threshold_result_requires_uniform_assignments() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0), _local_quantile(CLIENT_B, 2.0))
    mismatched = (
        ThresholdAssignment(CLIENT_A, ThresholdValue(1.5)),
        ThresholdAssignment(CLIENT_B, ThresholdValue(1.5)),
    )

    def build() -> SharedThresholdResult:
        return SharedThresholdResult(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
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
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        coordinate=COORDINATE,
        quantile=QUANTILE,
        contributing_local_quantiles=local_quantiles,
        shared_threshold=shared_value,
        assignments=assignments,
    )
    assert result.shared_threshold == shared_value


def test_shared_threshold_result_rejects_wrong_method() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0),)
    shared_value = ThresholdValue(1.0)
    assignments = (ThresholdAssignment(CLIENT_A, shared_value),)

    def build() -> SharedThresholdResult:
        return SharedThresholdResult(
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=shared_value,
            assignments=assignments,
        )

    with pytest.raises(ScientificContractError, match="method must be"):
        build()


def test_local_threshold_result_requires_assignment_to_match_own_quantile() -> None:
    local_quantiles = (_local_quantile(CLIENT_A, 1.0),)
    wrong_assignments = (ThresholdAssignment(CLIENT_A, ThresholdValue(9.0)),)

    def build() -> LocalThresholdResult:
        return LocalThresholdResult(
            method=FederatedThresholdMethod.LOCAL_THRESHOLD,
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
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
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
    # A malformed length can only reach this boundary through a bypass of the type
    # system (e.g. deserialized data); the cast constructs exactly that scenario.
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
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
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
            method=FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
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
            effective_quantile=0.95,
            selected_score=ScoreValue(1.0),
            tie_count=0,
            threshold=ThresholdValue(1.0),
        )

    with pytest.raises(ScientificContractError, match="within the calibration sample"):
        build()


def test_conformal_threshold_result_rejects_client_both_assigned_and_unavailable() -> None:
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=10,
        effective_quantile=1.0,
        selected_score=ScoreValue(1.0),
        tie_count=0,
        threshold=ThresholdValue(1.0),
    )

    def build() -> ConformalThresholdResult:
        return ConformalThresholdResult(
            method=FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            significance=Ratio(0.05),
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


def test_matched_attainment_diagnostic_rejects_out_of_range_target() -> None:
    def build() -> MatchedAttainmentDiagnostic:
        return MatchedAttainmentDiagnostic(
            target_exceedance=1.5,
            achieved_exceedance=0.1,
            signed_attainment_error=0.0,
            absolute_attainment_error=0.0,
            absolute_threshold_error_vs_pooled_quantile=0.0,
            relative_threshold_error_vs_pooled_quantile=None,
        )

    with pytest.raises(ScientificContractError, match="target exceedance"):
        build()


def test_communication_payload_requires_at_least_one_field() -> None:
    def build() -> CommunicationPayload:
        return CommunicationPayload(fields=(), estimated_bytes=ByteCount(0))

    with pytest.raises(ScientificContractError, match="at least one communicated field"):
        build()


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
