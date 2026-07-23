import pytest

from datp_core.analysis.resources import threshold_exchange_cost
from datp_core.bootstrap import _build_estimator_registry, build_application
from datp_core.pipeline.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.thresholding.construction import ConstructThresholdsUseCase
from datp_core.thresholding.models import BenignCalibrationScores, ConformalAttainabilityStatus, ThresholdSet


@pytest.fixture
def calibration() -> tuple[BenignCalibrationScores, ...]:
    return tuple(
        BenignCalibrationScores(
            client_id=ClientId(identifier), values=tuple(float(multiplier * i) for i in range(1, 101))
        )
        for identifier, multiplier in (("c1", 1), ("c2", 2), ("c3", 3))
    )


def _execute(
    policy_id: ThresholdPolicyId,
    calibration: tuple[BenignCalibrationScores, ...],
    coefficient: float | None = None,
    fingerprint_features: tuple[str, ...] | None = None,
) -> ThresholdSet:
    config = build_application().config
    use_case = ConstructThresholdsUseCase(config, _build_estimator_registry(config))
    return use_case.execute(
        policy_id,
        calibration,
        PopulationId("nbaiot_natural_devices"),
        None,
        None,
        coefficient,
        fingerprint_features_override=fingerprint_features,
    )


def _values(result: ThresholdSet) -> list[float]:
    return [float(value.threshold) for value in result.values]


def test_shared_and_local_configured_policies_preserve_scope_semantics(
    calibration: tuple[BenignCalibrationScores, ...],
) -> None:
    shared = _values(_execute(ThresholdPolicyId("shared_mean_p95"), calibration))
    local = _values(_execute(ThresholdPolicyId("local_p95"), calibration))
    assert shared[0] == shared[1] == shared[2]
    assert local[0] < local[1] < local[2]


def test_conformal_and_federated_configured_policies_produce_finite_thresholds(
    calibration: tuple[BenignCalibrationScores, ...],
) -> None:
    conformal = _values(_execute(ThresholdPolicyId("conformal_local_p95"), calibration))
    fixed = _values(_execute(ThresholdPolicyId("federated_summary_fixed_k"), calibration, 3.0))
    matched = _values(_execute(ThresholdPolicyId("federated_summary_matched_exceedance"), calibration))
    assert conformal[0] < conformal[1] < conformal[2]
    assert fixed[0] == fixed[1] == fixed[2]
    assert all(value > 0.0 for value in matched)


def test_conformal_thresholds_persist_finite_sample_diagnostics(
    calibration: tuple[BenignCalibrationScores, ...],
) -> None:
    result = _execute(ThresholdPolicyId("conformal_local_p95"), calibration)

    assert [record.finite_sample_rank for record in result.values] == [96, 96, 96]
    assert all(record.attainability_status is ConformalAttainabilityStatus.ATTAINABLE for record in result.values)


def test_cluster_policy_uses_the_explicit_fingerprint_feature_subset(
    calibration: tuple[BenignCalibrationScores, ...],
) -> None:
    result = _execute(ThresholdPolicyId("cluster_k3_mean_p95"), calibration, fingerprint_features=("mean_error",))

    assert len(result.values) == 3
    assert all(float(value.threshold) >= 0.0 for value in result.values)
    assert all(value.cluster_label is not None for value in result.values)


def test_registry_matches_complete_authored_policy_catalogue() -> None:
    config = build_application().config
    assert set(_build_estimator_registry(config).keys()) == set(config.threshold_policies)


def test_cluster_p95_fingerprint_is_locked_to_0_95_regardless_of_swept_quantile() -> None:
    """protocols.yaml locks fingerprint_estimators.p95_error to a fixed 0.95 quantile; the
    quantile-sensitivity sweep (mandatory experiment threshold_quantile_sensitivity) overrides
    the policy's own threshold-construction quantile, which must not leak into this fingerprint
    dimension. Three clients below share an identical median (quantile 0.5) but have distinct
    true p95 values, so overriding the swept quantile to 0.5 while restricting the fingerprint
    to p95_error alone is degenerate under the bug (all three collapse to the same feature value)
    and non-degenerate under the fix (the fixed-0.95 feature values remain distinct).
    """
    calibration = tuple(
        BenignCalibrationScores(client_id=ClientId(identifier), values=values)
        for identifier, values in (
            ("c1", tuple([0.0] * 10 + [5.0] * 9 + [100.0])),
            ("c2", tuple([0.0] * 10 + [5.0] * 9 + [200.0])),
            ("c3", tuple([0.0] * 10 + [5.0] * 9 + [300.0])),
        )
    )
    config = build_application().config
    use_case = ConstructThresholdsUseCase(config, _build_estimator_registry(config))

    result = use_case.execute(
        ThresholdPolicyId("cluster_k3_mean_p95"),
        calibration,
        PopulationId("nbaiot_natural_devices"),
        None,
        None,
        None,
        quantile_override=0.5,
        fingerprint_features_override=("p95_error",),
    )

    assert len({value.cluster_label for value in result.values}) > 1


def test_federated_summary_resource_estimate_counts_every_candidate_exchange() -> None:
    config = build_application().config
    fields, payload = threshold_exchange_cost(
        config.communication_estimation_contract,
        config.threshold_policies.get(ThresholdPolicyId("federated_summary_matched_exceedance")),
        3,
    )

    assert fields == (
        "benign_calibration_count_uint64",
        "benign_local_mean_float64",
        "benign_local_variance_float64",
        "candidate_coefficient_float64",
        "benign_exceedance_count_uint64",
    )
    assert payload == 3 * (24 + 501 * 16)
