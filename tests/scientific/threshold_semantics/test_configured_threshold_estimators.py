"""Scientific-invariant tests using the new ThresholdEngine and typed policies."""

from __future__ import annotations

import pytest

from datp_core.core.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.thresholding.engine import ThresholdEngine
from datp_core.thresholding.enums import (
    ClusterAggregation,
    FingerprintFeature,
    ThresholdPolicyKind,
)
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    ConformalDiagnostics,
    ThresholdConstructionRequest,
    ThresholdSet,
)
from datp_core.thresholding.policies import (
    CalibrationFallbackPolicy,
    ClusterPolicy,
    ConformalPolicy,
    FederatedFixedPolicy,
    FederatedMatchedPolicy,
    FixedShrinkagePolicy,
    QuantilePolicy,
)


@pytest.fixture
def calibration() -> tuple[BenignCalibrationScores, ...]:
    return tuple(
        BenignCalibrationScores(
            client_id=ClientId(identifier),
            values=tuple(float(multiplier * i) for i in range(1, 101)),
        )
        for identifier, multiplier in (("c1", 1), ("c2", 2), ("c3", 3))
    )


@pytest.fixture
def population_id() -> PopulationId:
    return PopulationId("nbaiot_natural_devices")


def _execute(
    policy: QuantilePolicy
    | ClusterPolicy
    | ConformalPolicy
    | FixedShrinkagePolicy
    | CalibrationFallbackPolicy
    | FederatedFixedPolicy
    | FederatedMatchedPolicy,
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
    policy_id: ThresholdPolicyId | None = None,
) -> ThresholdSet:
    engine = ThresholdEngine()
    return engine.construct(
        ThresholdConstructionRequest(
            policy_id=policy_id or ThresholdPolicyId("test"),
            policy=policy,
            calibration=calibration,
            population_id=population_id,
        )
    )


def _values(result: ThresholdSet) -> list[float]:
    return [float(value.threshold) for value in result.values]


# ── Scope semantics ────────────────────────────────────────────────────────


def test_shared_and_local_policies_preserve_scope_semantics(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    shared = _values(
        _execute(
            QuantilePolicy(kind=ThresholdPolicyKind.SHARED_MEAN, quantile=0.95),
            calibration,
            population_id,
        )
    )
    local = _values(
        _execute(
            QuantilePolicy(kind=ThresholdPolicyKind.LOCAL_QUANTILE, quantile=0.95),
            calibration,
            population_id,
        )
    )
    assert shared[0] == shared[1] == shared[2]
    assert local[0] < local[1] < local[2]


# ── Conformal and federated finite thresholds ──────────────────────────────


def test_conformal_and_federated_policies_produce_finite_thresholds(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    conformal = _values(
        _execute(
            ConformalPolicy(kind=ThresholdPolicyKind.CONFORMAL, coverage_alpha=0.05, minimum_sample_count=1),
            calibration,
            population_id,
        )
    )
    fixed = _values(
        _execute(
            FederatedFixedPolicy(kind=ThresholdPolicyKind.FEDERATED_FIXED, quantile=0.95, fixed_coefficient=3.0),
            calibration,
            population_id,
        )
    )
    matched = _values(
        _execute(
            FederatedMatchedPolicy(
                kind=ThresholdPolicyKind.FEDERATED_MATCHED,
                quantile=0.95,
                candidate_grid_minimum=0.0,
                candidate_grid_maximum=5.0,
                candidate_grid_step=0.01,
            ),
            calibration,
            population_id,
        )
    )
    assert conformal[0] < conformal[1] < conformal[2]
    assert fixed[0] == fixed[1] == fixed[2]
    assert all(value > 0.0 for value in matched)


# ── Conformal diagnostics ──────────────────────────────────────────────────


def test_conformal_thresholds_persist_finite_sample_diagnostics(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    result = _execute(
        ConformalPolicy(kind=ThresholdPolicyKind.CONFORMAL, coverage_alpha=0.05, minimum_sample_count=1),
        calibration,
        population_id,
    )

    assert [record.finite_sample_rank for record in result.values] == [96, 96, 96]
    assert result.diagnostics is not None
    assert isinstance(result.diagnostics, ConformalDiagnostics)
    assert result.diagnostics.coverage_alpha == 0.05
    assert len(result.diagnostics.ranks) == 3


# ── Cluster fingerprint feature subset ─────────────────────────────────────


def test_cluster_policy_uses_explicit_fingerprint_features(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    result = _execute(
        ClusterPolicy(
            kind=ThresholdPolicyKind.CLUSTER,
            quantile=0.95,
            cluster_count=2,
            aggregation=ClusterAggregation.MEAN,
            fingerprint_features=(FingerprintFeature.MEAN_ERROR,),
            kmeans_random_seed=42,
            kmeans_initialization_runs=10,
            kmeans_maximum_iterations=300,
            kmeans_convergence_tolerance=1e-4,
        ),
        calibration,
        population_id,
    )
    assert len(result.values) == 3
    assert all(float(value.threshold) >= 0.0 for value in result.values)
    assert all(value.cluster_label is not None for value in result.values)


# ── Fingerprint quantile locked to 0.95 regardless of policy quantile ──────


def test_cluster_p95_fingerprint_is_locked_to_0_95_regardless_of_swept_quantile() -> None:
    """The fingerprint p95 is always computed at 0.95, independent of the policy quantile.

    Three clients share identical median but distinct true p95 values.
    With quantile=0.5 and fingerprint_features=(P95_ERROR,), the feature values
    should remain distinct (not collapse to the same value).
    """
    cal = tuple(
        BenignCalibrationScores(client_id=ClientId(identifier), values=values)
        for identifier, values in (
            ("c1", tuple([0.0] * 10 + [5.0] * 9 + [100.0])),
            ("c2", tuple([0.0] * 10 + [5.0] * 9 + [200.0])),
            ("c3", tuple([0.0] * 10 + [5.0] * 9 + [300.0])),
        )
    )
    result = _execute(
        ClusterPolicy(
            kind=ThresholdPolicyKind.CLUSTER,
            quantile=0.5,
            cluster_count=2,
            aggregation=ClusterAggregation.MEAN,
            fingerprint_features=(FingerprintFeature.P95_ERROR,),
            kmeans_random_seed=42,
            kmeans_initialization_runs=10,
            kmeans_maximum_iterations=300,
            kmeans_convergence_tolerance=1e-4,
        ),
        cal,
        PopulationId("nbaiot_natural_devices"),
    )
    assert len({value.cluster_label for value in result.values}) > 1


# ── Conformal insufficient calibration ─────────────────────────────────────


def test_conformal_rejects_insufficient_calibration() -> None:
    from datp_core.thresholding.models import InsufficientCalibrationError

    cal = tuple(
        BenignCalibrationScores(
            client_id=ClientId(f"c{i}"),
            values=tuple(float(j) for j in range(1, 6)),
        )
        for i in range(3)
    )
    with pytest.raises(InsufficientCalibrationError):
        _execute(
            ConformalPolicy(kind=ThresholdPolicyKind.CONFORMAL, coverage_alpha=0.05, minimum_sample_count=10),
            cal,
            PopulationId("nbaiot_natural_devices"),
        )


# ── Shrinkage ──────────────────────────────────────────────────────────────


def test_shrinkage_produces_intermediate_thresholds(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    local = _values(
        _execute(
            QuantilePolicy(kind=ThresholdPolicyKind.LOCAL_QUANTILE, quantile=0.95),
            calibration,
            population_id,
        )
    )
    shared = _values(
        _execute(
            QuantilePolicy(kind=ThresholdPolicyKind.SHARED_MEAN, quantile=0.95),
            calibration,
            population_id,
        )
    )
    shrunk = _values(
        _execute(
            FixedShrinkagePolicy(kind=ThresholdPolicyKind.SHRINKAGE, quantile=0.95, shrinkage_weight=0.5),
            calibration,
            population_id,
        )
    )
    # Shrinkage thresholds should lie between local and shared
    for s, l, sh in zip(shrunk, local, shared, strict=True):
        assert min(l, sh) <= s <= max(l, sh)


# ── Calibration fallback ───────────────────────────────────────────────────


def test_calibration_fallback_produces_valid_thresholds(
    calibration: tuple[BenignCalibrationScores, ...],
    population_id: PopulationId,
) -> None:
    result = _execute(
        CalibrationFallbackPolicy(kind=ThresholdPolicyKind.CALIBRATION_FALLBACK, quantile=0.95, n_half=50),
        calibration,
        population_id,
    )
    values = _values(result)
    assert len(values) == 3
    assert all(v > 0.0 for v in values)
    from datp_core.thresholding.models import CalibrationFallbackDiagnostics

    assert isinstance(result.diagnostics, CalibrationFallbackDiagnostics)
