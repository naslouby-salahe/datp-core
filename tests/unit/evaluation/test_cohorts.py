import pytest

from datp_core.domain.enums import EvaluationCohort, FederatedThresholdMethod, PopulationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.evaluation.cohorts import (
    ClientExclusionReason,
    assert_cohort_invariant_to_threshold_methods,
    build_evaluation_cohort_manifest,
)
from datp_core.populations.models import ClientPartitionCounts


def test_fpr_eligibility_requires_support_and_benign_evaluation() -> None:
    counts = (
        ClientPartitionCounts("device_a", 100, 10, 5, True, False),
        ClientPartitionCounts("device_b", 99, 10, 5, True, False),
        ClientPartitionCounts("device_c", 100, 0, 5, True, False),
    )
    manifest = build_evaluation_cohort_manifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        client_counts=counts,
    )
    fpr_evaluable = {item.client_id for item in manifest.memberships if item.cohort is EvaluationCohort.FPR_EVALUABLE}
    assert fpr_evaluable == {"device_a"}
    by_id = {record.client_id: record for record in manifest.records}
    assert ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION in by_id["device_b"].exclusion_reasons
    assert ClientExclusionReason.EMPTY_BENIGN_EVALUATION in by_id["device_c"].exclusion_reasons


def test_fallback_cannot_enter_fpr_cohort() -> None:
    counts = (ClientPartitionCounts("fallback_client", 1000, 100, 0, True, True),)
    manifest = build_evaluation_cohort_manifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        client_counts=counts,
    )
    cohorts = {item.cohort for item in manifest.memberships if item.client_id == "fallback_client"}
    assert EvaluationCohort.DEPLOYMENT_FALLBACK in cohorts
    assert EvaluationCohort.FPR_EVALUABLE not in cohorts


def test_edge_clients_are_not_attack_evaluable() -> None:
    counts = (ClientPartitionCounts("Distance", 200, 50, 0, True, False),)
    manifest = build_evaluation_cohort_manifest(
        population=PopulationId.EDGE_SENSOR_GROUPS,
        partition_seed=Seed(0),
        client_counts=counts,
    )
    assert not any(item.cohort is EvaluationCohort.ATTACK_EVALUABLE for item in manifest.memberships)
    assert any(
        ClientExclusionReason.INVALID_ATTACK_ASSIGNMENT in record.exclusion_reasons for record in manifest.records
    )


def test_cohort_membership_is_invariant_to_threshold_method() -> None:
    counts = (
        ClientPartitionCounts("device_a", 150, 20, 8, True, False),
        ClientPartitionCounts("device_b", 80, 20, 8, True, False),
    )
    methods = (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
    )
    manifest = assert_cohort_invariant_to_threshold_methods(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        client_counts=counts,
        methods=methods,
    )
    assert any(item.cohort is EvaluationCohort.FPR_EVALUABLE for item in manifest.memberships)


def test_cohort_invariance_requires_methods() -> None:
    with pytest.raises(ScientificContractError):
        assert_cohort_invariant_to_threshold_methods(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            client_counts=(),
            methods=(),
        )
