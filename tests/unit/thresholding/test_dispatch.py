import pytest
from tests.unit.thresholding.helpers import COORDINATE, client_scores

from datp_core.core.errors import CapabilityError, LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    CentralizedThresholdMethod,
    DatasetId,
    EvidenceRole,
    FamilyIdentity,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.core.numeric import ClientCount, Quantile
from datp_core.data.populations.contracts import CapabilityStatus, FamilyAssignment, PopulationCapabilities
from datp_core.thresholds.contracts import ThresholdUnavailableResult
from datp_core.thresholds.dispatch import (
    ThresholdConstructionRequest,
    dispatch_federated_threshold,
    reject_centralized_threshold_method,
    validate_population_capability,
)
from datp_core.thresholds.policies.cluster import GroupedThresholdResult
from datp_core.thresholds.policies.family import FamilyThresholdResult
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
)
from datp_core.thresholds.protocols import (
    FIXED_SHRINKAGE_PROTOCOL,
    CalibrationSupportRule,
    ClusterThresholdAggregation,
)
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores
from datp_core.thresholds.variants.conformal import ConformalThresholdResult
from datp_core.thresholds.variants.federated_statistics import FederatedStatisticsThresholdResult
from datp_core.thresholds.variants.shrinkage import (
    FixedShrinkageCurveResult,
    ShrinkageThresholdResult,
    SizeAwareShrinkageThresholdResult,
)

QUANTILE = Quantile(0.5)
ELIGIBLE = tuple(
    client_scores(
        f"client_{index}",
        tuple(float(index * 100 + value) for value in range(100)),
    )
    for index in range(6)
)
FAMILY_A = FamilyIdentity("family_a")
FAMILY_BY_CLIENT = tuple(FamilyAssignment(client=item.client, family=FAMILY_A) for item in ELIGIBLE)


def _capabilities(
    valid_threshold_methods: tuple[FederatedThresholdMethod, ...],
) -> PopulationCapabilities:
    return PopulationCapabilities(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        declared_client_count=ClientCount(len(ELIGIBLE)),
        physical_client_validity=CapabilityStatus.SUPPORTED,
        family_taxonomy=CapabilityStatus.SUPPORTED,
        chronology=CapabilityStatus.UNAVAILABLE,
        client_level_attack_assignment=CapabilityStatus.SUPPORTED,
        fpr_evaluation=CapabilityStatus.SUPPORTED,
        attack_sensitive_evaluation=CapabilityStatus.SUPPORTED,
        temporal_support=CapabilityStatus.UNAVAILABLE,
        valid_threshold_methods=valid_threshold_methods,
        evidentiary_role=EvidenceRole.CONFIRMATORY,
        confirmatory_eligible=True,
    )


ALL_METHODS_CAPABILITIES = _capabilities(tuple(FederatedThresholdMethod))


def _cluster_aggregation(method: FederatedThresholdMethod) -> ClusterThresholdAggregation | None:
    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        return ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS
    return None


def _request(
    method: FederatedThresholdMethod,
    *,
    capabilities: PopulationCapabilities = ALL_METHODS_CAPABILITIES,
    eligible: tuple[ClientBenignCalibrationScores, ...] = ELIGIBLE,
    family_by_client: tuple[FamilyAssignment, ...] = FAMILY_BY_CLIENT,
    support_rule: CalibrationSupportRule = CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
) -> ThresholdConstructionRequest:
    return ThresholdConstructionRequest(
        method=method,
        coordinate=COORDINATE,
        quantile=QUANTILE,
        capabilities=capabilities,
        eligible=eligible,
        family_by_client=family_by_client,
        support_rule=support_rule,
        cluster_threshold_aggregation=_cluster_aggregation(method),
    )


@pytest.mark.parametrize(
    ("method", "expected_type"),
    [
        (FederatedThresholdMethod.SHARED_THRESHOLD, SharedThresholdResult),
        (FederatedThresholdMethod.LOCAL_THRESHOLD, LocalThresholdResult),
        (FederatedThresholdMethod.POOLED_SHARED_QUANTILE, PooledSharedQuantileResult),
        (FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD, SampleWeightedSharedThresholdResult),
        (FederatedThresholdMethod.FAMILY_THRESHOLD, FamilyThresholdResult),
        (FederatedThresholdMethod.CLUSTER_THRESHOLD, GroupedThresholdResult),
        (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE, FixedShrinkageCurveResult),
        (FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE, SizeAwareShrinkageThresholdResult),
        (FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD, ConformalThresholdResult),
        (FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS, FederatedStatisticsThresholdResult),
    ],
)
def test_dispatch_returns_the_correct_result_type_for_every_method(method, expected_type) -> None:
    assert isinstance(dispatch_federated_threshold(_request(method)), expected_type)


def test_dispatch_returns_the_complete_declared_shrinkage_curve() -> None:
    result = dispatch_federated_threshold(_request(FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE))

    assert isinstance(result, FixedShrinkageCurveResult)
    assert result.points
    assert all(isinstance(item, ShrinkageThresholdResult) for item in result.points)
    assert tuple(item.weight for item in result.points) == FIXED_SHRINKAGE_PROTOCOL.weights


def test_dispatch_family_threshold_without_taxonomy_is_unavailable() -> None:
    result = dispatch_federated_threshold(_request(FederatedThresholdMethod.FAMILY_THRESHOLD, family_by_client=()))
    assert isinstance(result, ThresholdUnavailableResult)


def test_dispatch_cluster_threshold_with_too_few_clients_is_unavailable() -> None:
    result = dispatch_federated_threshold(_request(FederatedThresholdMethod.CLUSTER_THRESHOLD, eligible=ELIGIBLE[:2]))
    assert isinstance(result, ThresholdUnavailableResult)


def test_dispatch_rejects_method_unsupported_by_population_capabilities() -> None:
    request = _request(
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        capabilities=_capabilities((FederatedThresholdMethod.SHARED_THRESHOLD,)),
    )
    with pytest.raises(CapabilityError):
        dispatch_federated_threshold(request)


def test_validate_population_capability_rejects_unsupported_method() -> None:
    capabilities = _capabilities((FederatedThresholdMethod.SHARED_THRESHOLD,))
    with pytest.raises(CapabilityError):
        validate_population_capability(capabilities, FederatedThresholdMethod.LOCAL_THRESHOLD)


def test_reject_centralized_threshold_method_raises_leakage_error() -> None:
    with pytest.raises(LeakageError, match="cannot enter federated dispatch"):
        reject_centralized_threshold_method(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)


def test_reject_centralized_threshold_method_accepts_federated_methods() -> None:
    reject_centralized_threshold_method(FederatedThresholdMethod.SHARED_THRESHOLD)


def test_threshold_construction_request_rejects_duplicate_eligible_clients() -> None:
    with pytest.raises(ScientificContractError, match="unique identities"):
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            capabilities=ALL_METHODS_CAPABILITIES,
            eligible=(ELIGIBLE[0], ELIGIBLE[0]),
            family_by_client=(),
            support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
            cluster_threshold_aggregation=None,
        )


def test_threshold_construction_request_rejects_mixed_coordinates() -> None:
    from tests.unit.learning.federated.helpers import fedavg_coordinate

    from datp_core.core.numeric import Seed

    other = client_scores(
        "client_mixed",
        (1.0, 2.0, 3.0),
        coordinate=fedavg_coordinate(Seed(1)),
    )
    with pytest.raises(ScientificContractError, match="request coordinate"):
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            capabilities=ALL_METHODS_CAPABILITIES,
            eligible=(ELIGIBLE[0], other),
            family_by_client=(),
            support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
            cluster_threshold_aggregation=None,
        )


def test_threshold_construction_request_rejects_duplicate_family_taxonomy_client() -> None:
    duplicated = (
        FamilyAssignment(client=ELIGIBLE[0].client, family=FAMILY_A),
        FamilyAssignment(client=ELIGIBLE[0].client, family=FAMILY_A),
    )
    with pytest.raises(ScientificContractError, match="unique client identities"):
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.FAMILY_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            capabilities=ALL_METHODS_CAPABILITIES,
            eligible=ELIGIBLE,
            family_by_client=duplicated,
            support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
            cluster_threshold_aggregation=None,
        )


def test_cluster_threshold_requires_explicit_aggregation() -> None:
    with pytest.raises(ScientificContractError, match="explicit threshold aggregation"):
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.CLUSTER_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            capabilities=ALL_METHODS_CAPABILITIES,
            eligible=ELIGIBLE,
            family_by_client=FAMILY_BY_CLIENT,
            support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
            cluster_threshold_aggregation=None,
        )


def test_non_cluster_threshold_rejects_cluster_aggregation() -> None:
    with pytest.raises(ScientificContractError, match="valid only for CLUSTER_THRESHOLD"):
        ThresholdConstructionRequest(
            method=FederatedThresholdMethod.SHARED_THRESHOLD,
            coordinate=COORDINATE,
            quantile=QUANTILE,
            capabilities=ALL_METHODS_CAPABILITIES,
            eligible=ELIGIBLE,
            family_by_client=FAMILY_BY_CLIENT,
            support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
            cluster_threshold_aggregation=ClusterThresholdAggregation.ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS,
        )


def test_canonical_support_rejects_client_below_one_hundred_benign_rows() -> None:
    undersized = (client_scores("undersized", tuple(float(value) for value in range(50))),)
    request = _request(FederatedThresholdMethod.SHARED_THRESHOLD, eligible=undersized)
    with pytest.raises(ScientificContractError, match="minimum benign calibration support"):
        dispatch_federated_threshold(request)


def test_declared_size_ablation_support_allows_fifty_benign_rows() -> None:
    undersized = (client_scores("ablation", tuple(float(value) for value in range(50))),)
    result = dispatch_federated_threshold(
        _request(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            eligible=undersized,
            support_rule=CalibrationSupportRule.DECLARED_SIZE_ABLATION,
        )
    )
    assert isinstance(result, SharedThresholdResult)
