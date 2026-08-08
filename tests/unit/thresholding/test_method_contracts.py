import pytest
from tests.unit.thresholding.helpers import COORDINATE, identity

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    FamilyIdentity,
    FederatedThresholdMethod,
)
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ClusterIndex,
    ConformalRankIndex,
    CoverageTarget,
    GroupCount,
    KMeansInitializationCount,
    KMeansMaximumIterationCount,
    MetricValue,
    Quantile,
    Ratio,
    RowCount,
    ScoreMoment,
    ScoreValue,
    ScoreVariance,
    Seed,
    ShrinkageWeight,
    ThresholdValue,
)
from datp_core.protocols.calibration import KMeansInitialization
from datp_core.thresholds.contracts import (
    LocalQuantile,
    ThresholdAssignment,
    ThresholdDiagnostic,
    ThresholdInfeasibilityReason,
    ThresholdUnavailableResult,
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
from datp_core.thresholds.variants.conformal import (
    ConformalAssignment,
    ConformalThresholdResult,
)
from datp_core.thresholds.variants.federated_statistics import (
    CentralizedAttainmentDiagnostic,
    ClientBenignSummary,
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
    with pytest.raises(ScientificContractError, match="unweighted mean"):
        SharedThresholdResult(
            coordinate=COORDINATE,
            quantile=QUANTILE,
            contributing_local_quantiles=local_quantiles,
            shared_threshold=ThresholdValue(1.6),
            assignments=(
                ThresholdAssignment(CLIENT_A, ThresholdValue(1.6)),
                ThresholdAssignment(CLIENT_B, ThresholdValue(1.6)),
            ),
        )
    with pytest.raises(ScientificContractError, match="own local quantile"):
        LocalThresholdResult(
            coordinate=COORDINATE,
            local_quantiles=(local_quantiles[0],),
            assignments=(ThresholdAssignment(CLIENT_A, ThresholdValue(9.0)),),
        )


def test_family_contracts_enforce_membership_and_assignment_coverage() -> None:
    with pytest.raises(
        ScientificContractError,
        match="eligible members and a constructed threshold",
    ):
        FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
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
    with pytest.raises(ScientificContractError, match="contributing client set"):
        FamilyThresholdResult(
            coordinate=COORDINATE,
            families=(family,),
            assignments=(ThresholdAssignment(CLIENT_B, ThresholdValue(1.0)),),
        )


def test_family_membership_enforces_the_same_group_membership_contract_as_cluster() -> None:
    with pytest.raises(ScientificContractError, match="exactly match declared family members"):
        FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A,),
            contributing_local_quantiles=(_local_quantile(CLIENT_B, 1.0),),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=ThresholdValue(1.0),
        )
    with pytest.raises(ScientificContractError, match="unweighted mean of contributing local quantiles"):
        FamilyMembership(
            family_id=FamilyIdentity("doorbell"),
            members=(CLIENT_A,),
            contributing_local_quantiles=(_local_quantile(CLIENT_A, 1.0),),
            status=AvailabilityStatus.AVAILABLE,
            family_threshold=ThresholdValue(999.0),
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
    with pytest.raises(ScientificContractError, match="number of clusters"):
        GroupedThresholdResult(
            coordinate=COORDINATE,
            fingerprints=(fingerprint,),
            clusters=(membership,),
            assignments=(ThresholdAssignment(CLIENT_A, ThresholdValue(1.0)),),
            initialization=KMeansInitialization.KMEANS_PLUS_PLUS,
            initialization_count=KMeansInitializationCount(10),
            maximum_iterations=KMeansMaximumIterationCount(300),
            random_state=Seed(42),
            group_count=GroupCount(2),
        )


def test_shrinkage_contracts_enforce_formula_and_complete_curve() -> None:
    with pytest.raises(ScientificContractError, match="lambda \\* local"):
        ShrinkageAssignment(
            client=CLIENT_A,
            lambda_weight=ShrinkageWeight(0.5),
            local_threshold=ThresholdValue(2.0),
            shared_threshold=ThresholdValue(4.0),
            blended_threshold=ThresholdValue(999.0),
        )
    assignments = (
        ShrinkageAssignment(
            CLIENT_A,
            ShrinkageWeight(0.0),
            ThresholdValue(1.0),
            ThresholdValue(2.0),
            ThresholdValue(2.0),
        ),
        ShrinkageAssignment(
            CLIENT_B,
            ShrinkageWeight(0.0),
            ThresholdValue(1.0),
            ThresholdValue(2.0),
            ThresholdValue(2.0),
        ),
        ShrinkageAssignment(
            CLIENT_A,
            ShrinkageWeight(1.0),
            ThresholdValue(1.0),
            ThresholdValue(2.0),
            ThresholdValue(1.0),
        ),
    )
    with pytest.raises(ScientificContractError, match="same client set"):
        ShrinkageThresholdResult(
            coordinate=COORDINATE,
            weights=(ShrinkageWeight(0.0), ShrinkageWeight(1.0)),
            assignments=assignments,
        )


def test_conformal_contracts_enforce_rank_and_client_partition() -> None:
    with pytest.raises(ScientificContractError, match="within the calibration sample"):
        ConformalAssignment(
            client=CLIENT_A,
            calibration_count=RowCount(10),
            rank_index=ConformalRankIndex(11),
            effective_quantile=Quantile(0.95),
            selected_score=ScoreValue(1.0),
            tie_count=RowCount(0),
            threshold=ThresholdValue(1.0),
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
    with pytest.raises(
        ScientificContractError,
        match="cannot be both assigned and unavailable",
    ):
        ConformalThresholdResult(
            coordinate=COORDINATE,
            coverage=CoverageTarget(0.95),
            eligible_clients=(CLIENT_A,),
            assignments=(assignment,),
            unavailable_clients=(CLIENT_A,),
        )


def test_federated_statistics_contracts_enforce_variance_identities() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ClientBenignSummary(
            client=CLIENT_A,
            count=RowCount(10),
            mean=ScoreMoment(0.0),
            variance=ScoreVariance(-1.0),
            benign_exceedance_count=None,
        )
    with pytest.raises(
        ScientificContractError,
        match="within-client plus between-client",
    ):
        PooledVarianceDecomposition(
            global_mean=ScoreMoment(0.0),
            within_client_variance=ScoreVariance(1.0),
            between_client_variance=ScoreVariance(1.0),
            full_pooled_variance=ScoreVariance(3.0),
            between_ratio=None,
        )
    with pytest.raises(ValueError, match="quantile"):
        CentralizedAttainmentDiagnostic(
            target_exceedance=Quantile(1.5),
            achieved_exceedance=Ratio(0.1),
            signed_attainment_error=MetricValue(0.0),
            absolute_attainment_error=Ratio(0.0),
            absolute_threshold_error_vs_pooled_quantile=(AbsoluteThresholdError(0.0)),
            relative_threshold_error_vs_pooled_quantile=None,
        )


def test_unavailable_threshold_requires_human_readable_detail() -> None:
    with pytest.raises(
        ScientificContractError,
        match="human-readable detail",
    ):
        ThresholdUnavailableResult(
            method=FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
            coordinate=COORDINATE,
            reason=(ThresholdInfeasibilityReason.SIZE_AWARE_SHRINKAGE_FUNCTION_UNRESOLVED),
            detail="   ",
        )
