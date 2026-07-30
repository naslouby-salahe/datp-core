from typing import cast

import pytest
from tests.unit.thresholding.helpers import COORDINATE, client_scores

from datp_core.domain.enums import (
    CapabilityStatus,
    CentralizedThresholdMethod,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.domain.errors import CapabilityError, LeakageError
from datp_core.domain.values import ClientCount, FamilyIdentity, Quantile
from datp_core.populations.models import ClientIdentity, PopulationCapabilities
from datp_core.thresholding.dispatch import (
    ThresholdConstructionRequest,
    dispatch_federated_threshold,
    reject_centralized_threshold_method,
    validate_population_capability,
)
from datp_core.thresholding.models import (
    ConformalThresholdResult,
    FamilyThresholdResult,
    FederatedStatisticsThresholdResult,
    GroupedThresholdResult,
    LocalThresholdResult,
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
    ShrinkageThresholdResult,
    ThresholdUnavailableResult,
)
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores

QUANTILE = Quantile(0.5)
ELIGIBLE = tuple(
    client_scores(f"client_{index}", tuple(float(index * 100 + value) for value in range(100))) for index in range(6)
)
FAMILY_A = FamilyIdentity("family_a")
FAMILY_BY_CLIENT = tuple((client_scores.client, FAMILY_A) for client_scores in ELIGIBLE)


def _capabilities(valid_threshold_methods: tuple[FederatedThresholdMethod, ...]) -> PopulationCapabilities:
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


def _request(
    method: FederatedThresholdMethod,
    *,
    capabilities: PopulationCapabilities = ALL_METHODS_CAPABILITIES,
    eligible: tuple[ClientBenignCalibrationScores, ...] = ELIGIBLE,
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...] = FAMILY_BY_CLIENT,
) -> ThresholdConstructionRequest:
    return ThresholdConstructionRequest(
        method=method,
        coordinate=COORDINATE,
        quantile=QUANTILE,
        capabilities=capabilities,
        eligible=eligible,
        family_by_client=family_by_client,
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
        (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE, ShrinkageThresholdResult),
        (FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE, ThresholdUnavailableResult),
        (FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD, ConformalThresholdResult),
        (FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS, FederatedStatisticsThresholdResult),
    ],
)
def test_dispatch_returns_the_correct_result_type_for_every_method(method, expected_type) -> None:
    result = dispatch_federated_threshold(_request(method))
    assert isinstance(result, expected_type)


def test_dispatch_family_threshold_without_taxonomy_is_unavailable() -> None:
    result = dispatch_federated_threshold(_request(FederatedThresholdMethod.FAMILY_THRESHOLD, family_by_client=()))
    assert isinstance(result, ThresholdUnavailableResult)


def test_dispatch_cluster_threshold_with_too_few_clients_is_unavailable() -> None:
    small = ELIGIBLE[:2]
    result = dispatch_federated_threshold(_request(FederatedThresholdMethod.CLUSTER_THRESHOLD, eligible=small))
    assert isinstance(result, ThresholdUnavailableResult)


def test_dispatch_rejects_method_unsupported_by_population_capabilities() -> None:
    capabilities = _capabilities((FederatedThresholdMethod.SHARED_THRESHOLD,))
    request = _request(FederatedThresholdMethod.LOCAL_THRESHOLD, capabilities=capabilities)

    def call():
        return dispatch_federated_threshold(request)

    with pytest.raises(CapabilityError):
        call()


def test_validate_population_capability_rejects_unsupported_method() -> None:
    capabilities = _capabilities((FederatedThresholdMethod.SHARED_THRESHOLD,))

    def call() -> None:
        validate_population_capability(capabilities, FederatedThresholdMethod.LOCAL_THRESHOLD)

    with pytest.raises(CapabilityError):
        call()


def test_reject_centralized_threshold_method_raises_leakage_error() -> None:
    def call() -> None:
        reject_centralized_threshold_method(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)

    with pytest.raises(LeakageError, match="cannot enter federated dispatch"):
        call()


def test_reject_centralized_threshold_method_accepts_federated_methods() -> None:
    reject_centralized_threshold_method(FederatedThresholdMethod.SHARED_THRESHOLD)


def test_dispatch_rejects_a_centralized_method_disguised_as_federated() -> None:
    # A caller could only ever get a CentralizedThresholdMethod past ThresholdConstructionRequest's
    # static typing via an explicit bypass; the cast constructs exactly that misuse so the
    # runtime guard (not just the type system) is what is actually being verified here.
    disguised = cast(FederatedThresholdMethod, CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE)
    request = _request(disguised)

    def call():
        return dispatch_federated_threshold(request)

    with pytest.raises(LeakageError):
        call()
