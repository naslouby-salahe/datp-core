import pytest

from datp_core.datasets.partitioning.contracts import ClientIdentity, ClientPartitionCounts
from datp_core.domain.enums import (
    EvaluationCohort,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.evaluation.cohort.construction import (
    assert_cohort_invariant_to_threshold_methods,
    build_evaluation_cohort_manifest,
)
from datp_core.evaluation.cohort.contracts import ClientExclusionReason


def test_fpr_eligibility_requires_support_and_benign_evaluation() -> None:
    counts = (
        _counts("device_a", 100, 10, 5),
        _counts("device_b", 99, 10, 5),
        _counts("device_c", 100, 0, 5),
    )
    manifest = build_evaluation_cohort_manifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        client_counts=counts,
    )
    fpr_evaluable = {
        item.client.client_id for item in manifest.memberships if item.cohort is EvaluationCohort.FPR_EVALUABLE
    }
    assert fpr_evaluable == {"device_a"}
    by_id = {record.client.client_id: record for record in manifest.records}
    assert ClientExclusionReason.INSUFFICIENT_BENIGN_CALIBRATION in by_id["device_b"].exclusion_reasons
    assert ClientExclusionReason.EMPTY_BENIGN_EVALUATION in by_id["device_c"].exclusion_reasons


def test_fallback_cannot_enter_fpr_cohort() -> None:
    counts = (_counts("fallback_client", 1000, 100, 0, deployment_fallback=True),)
    manifest = build_evaluation_cohort_manifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        client_counts=counts,
    )
    cohorts = {item.cohort for item in manifest.memberships if item.client.client_id == "fallback_client"}
    assert EvaluationCohort.DEPLOYMENT_FALLBACK in cohorts
    assert EvaluationCohort.FPR_EVALUABLE not in cohorts


def test_edge_clients_are_not_attack_evaluable() -> None:
    counts = (
        _counts(
            "Distance",
            200,
            50,
            0,
            population=PopulationId.EDGE_SENSOR_GROUPS,
            identity_kind=PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS,
        ),
    )
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
    counts = (_counts("device_a", 150, 20, 8), _counts("device_b", 80, 20, 8))
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


def test_cohort_rejects_identity_kind_drift() -> None:
    counts = (
        _counts(
            "device_a",
            150,
            20,
            8,
            identity_kind=PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS,
        ),
    )
    with pytest.raises(ScientificContractError, match="identity contract"):
        build_evaluation_cohort_manifest(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            client_counts=counts,
        )


def test_cohort_invariance_requires_methods() -> None:
    with pytest.raises(ScientificContractError):
        assert_cohort_invariant_to_threshold_methods(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            client_counts=(),
            methods=(),
        )


def _counts(
    client_id: str,
    calibration: int,
    benign_evaluation: int,
    attack_evaluation: int,
    *,
    population: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES,
    identity_kind: PopulationIdentityKind = PopulationIdentityKind.PHYSICAL_DEVICES,
    deployment_fallback: bool = False,
) -> ClientPartitionCounts:
    return ClientPartitionCounts(
        client=ClientIdentity(population, client_id, identity_kind),
        benign_calibration_count=RowCount(calibration),
        benign_evaluation_count=RowCount(benign_evaluation),
        attack_evaluation_count=RowCount(attack_evaluation),
        accepted=True,
        deployment_fallback=deployment_fallback,
    )
