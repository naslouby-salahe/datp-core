import pytest
from tests.unit.thresholding.helpers import COORDINATE, identity

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    FamilyIdentity,
)
from datp_core.core.numeric import (
    ClusterIndex,
    ConformalRankIndex,
    CoverageTarget,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    Quantile,
    RowCount,
    ScoreMoment,
    ScoreValue,
    ScoreVariance,
    Seed,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    ThresholdDiagnostic,
)
from datp_core.thresholds.policies.cluster import (
    ClusterFingerprint,
    ClusterMembership,
    FingerprintFeatures,
    GroupedThresholdResult,
)
from datp_core.thresholds.policies.family import (
    FamilyMembership,
    FamilyThresholdResult,
)
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import SharedThresholdResult
from datp_core.thresholds.protocols import KMeansInitialization
from datp_core.thresholds.variants.conformal import (
    ConformalAssignment,
    ConformalThresholdResult,
)
from datp_core.thresholds.variants.federated_statistics import (
    PooledVarianceDecomposition,
)
from datp_core.thresholds.variants.shrinkage import (
    ShrinkageAssignment,
    ShrinkageThresholdResult,
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


def _local_quantile(client, value: float) -> LocalQuantile:
    return LocalQuantile(
        client=client,
        coordinate=COORDINATE,
        quantile=QUANTILE,
        value=ThresholdValue(value),
        calibration_count=RowCount(120),
        diagnostic=_diagnostic(),
    )


def test_shared_and_local_results_reject_inconsistent_assignments() -> None:
    local_quantiles = (
        _local_quantile(CLIENT_A, 1.0),
        _local_quantile(CLIENT_B, 2.0),
    )
    shared_threshold = ThresholdValue(1.6)
    shared_assignments = (
        ThresholdAssignment(CLIENT_A, ThresholdValue(1.6)),
        ThresholdAssignment(CLIENT_B, ThresholdValue(1.6)),
    )
    with pytest.raises(ScientificContractError, match="unweighted mean"):
        SharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=shared_threshold,
            assignments=shared_assignments,
        )
    local_assignments = (ThresholdAssignment(CLIENT_A, ThresholdValue(9.0)),)
    with pytest.raises(ScientificContractError, match="own local quantile"):
        LocalThresholdResult(
            coordinate=COORDINATE,
            local_quantiles=(local_quantiles[0],),
            assignments=local_assignments,
        )


def test_family_contracts_enforce_membership_and_assignment_coverage() -> None:
    family_id = FamilyIdentity("doorbell")
    with pytest.raises(
        ScientificContractError,
        match="eligible members and a constructed threshold",
    ):
        FamilyMembership(
            family_id=family_id,
            members=(),
            contributing_local_quantiles=(),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=None,
        )
    family = FamilyMembership(
        family_id=FamilyIdentity("doorbell"),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        status=AvailabilityStatus.AVAILABLE,
        family_threshold=ThresholdValue(1.0),
    )
    family_assignments = (ThresholdAssignment(CLIENT_B, ThresholdValue(1.0)),)
    with pytest.raises(ScientificContractError, match="contributing client set"):
        FamilyThresholdResult(
            coordinate=COORDINATE,
            families=(family,),
            assignments=family_assignments,
        )


def test_family_membership_enforces_the_same_group_membership_contract_as_cluster() -> None:
    family_id = FamilyIdentity("doorbell")
    mismatched_local_quantiles = (_local_quantile(CLIENT_B, 1.0),)
    family_threshold = ThresholdValue(1.0)
    with pytest.raises(ScientificContractError, match="exactly match declared family members"):
        FamilyMembership(
            family_id=family_id,
            members=(CLIENT_A,),
            contributing_local_quantiles=mismatched_local_quantiles,
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=family_threshold,
        )
    matching_local_quantiles = (_local_quantile(CLIENT_A, 1.0),)
    inconsistent_family_threshold = ThresholdValue(999.0)
    with pytest.raises(ScientificContractError, match="unweighted mean of contributing local quantiles"):
        FamilyMembership(
            family_id=family_id,
            members=(CLIENT_A,),
            contributing_local_quantiles=matching_local_quantiles,
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=inconsistent_family_threshold,
        )


def test_cluster_contracts_require_four_features_and_declared_group_count() -> None:
    from datp_core.core.numeric import DistributionSkewness, ScoreMoment

    features = FingerprintFeatures(
        mean=ScoreMoment(1.0),
        standard_deviation=ScoreMoment(1.0),
        skewness=DistributionSkewness(1.0),
        p95=ThresholdValue(1.0),
    )
    standardized = FingerprintFeatures(
        mean=ScoreMoment(0.0),
        standard_deviation=ScoreMoment(0.0),
        skewness=DistributionSkewness(0.0),
        p95=ThresholdValue(0.0),
    )
    fingerprint = ClusterFingerprint(
        client=CLIENT_A,
        raw=features,
        standardized=standardized,
    )
    membership = ClusterMembership(
        cluster_index=ClusterIndex(0),
        members=(CLIENT_A,),
        contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
        cluster_threshold=ThresholdValue(1.0),
    )
    group_assignments = (ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),)
    initialization_count = KMeansInitializationCount(10)
    maximum_iterations = KMeansMaximumIterationCount(300)
    random_state = Seed(42)
    group_count = GroupCount(2)
    with pytest.raises(ScientificContractError, match="number of clusters"):
        GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fingerprint,),
            clusters=(membership,),
            assignments=group_assignments,
            initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
            initialization_count=initialization_count,
            maximum_iterations=maximum_iterations,
            random_state=random_state,
            group_count=group_count,
        )


def test_shrinkage_contracts_enforce_formula_and_complete_curve() -> None:
    local_a = _local_quantile(CLIENT_A, 2.0)
    local_b = _local_quantile(CLIENT_B, 1.0)
    shared_threshold = ThresholdValue(4.0)
    weight = ShrinkageWeight(0.5)
    threshold = ThresholdValue(999.0)
    with pytest.raises(ScientificContractError, match="convex local-shared combination"):
        ShrinkageAssignment(
            client=CLIENT_A,
            local_quantile=local_a,
            shared_threshold=shared_threshold,
            weight=weight,
            threshold=threshold,
        )
    assignments = (
        ShrinkageAssignment(
            client=CLIENT_A,
            local_quantile=local_a,
            shared_threshold=ThresholdValue(2.0),
            weight=ShrinkageWeight(0.0),
            threshold=ThresholdValue(2.0),
        ),
    )
    result_weight = ShrinkageWeight(0.0)
    result_shared_threshold = ThresholdValue(2.0)
    with pytest.raises(ScientificContractError, match="exactly the contributing client set"):
        ShrinkageThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            weight=result_weight,
            shared_threshold=result_shared_threshold,
            local_quantiles=(local_a, local_b),
            assignments=assignments,
        )


def test_conformal_contracts_enforce_rank_and_client_partition() -> None:
    calibration_count = RowCount(10)
    rank_index = ConformalRankIndex(11)
    effective_quantile = Quantile(0.95)
    selected_score = ScoreValue(1.0)
    tie_count = RowCount(0)
    threshold = ThresholdValue(1.0)
    with pytest.raises(ScientificContractError, match="within the calibration sample"):
        ConformalAssignment(
            client=CLIENT_A,
            calibration_count=calibration_count,
            rank_index=rank_index,
            effective_quantile=effective_quantile,
            selected_score=selected_score,
            tie_count=tie_count,
            threshold=threshold,
        )
    assignment = ConformalAssignment(
        client=CLIENT_A,
        calibration_count=RowCount(10),
        rank_index=ConformalRankIndex(9),
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(1.0),
        tie_count=RowCount(0),
        threshold=ThresholdValue(1.0),
    )
    coverage = CoverageTarget(0.95)
    with pytest.raises(
        ScientificContractError,
        match="cannot be both assigned and unavailable",
    ):
        ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=coverage,
            eligible_clients=(CLIENT_A,),
            assignments=(assignment,),
            unavailable_clients=(CLIENT_A,),
        )


def test_federated_statistics_contracts_enforce_variance_identities() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ScoreVariance(-1.0)
    global_mean = ScoreMoment(0.0)
    within_client_variance = ScoreVariance(1.0)
    between_client_variance = ScoreVariance(1.0)
    full_pooled_variance = ScoreVariance(3.0)
    with pytest.raises(
        ScientificContractError,
        match="within-client plus between-client",
    ):
        PooledVarianceDecomposition(
            global_mean=global_mean,
            within_client_variance=within_client_variance,
            between_client_variance=between_client_variance,
            full_pooled_variance=full_pooled_variance,
            between_ratio=None,
        )
    with pytest.raises(ValueError, match="quantile"):
        Quantile(1.5)


def test_unavailable_threshold_requires_human_readable_detail() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        AnalysisReasonText("   ")
