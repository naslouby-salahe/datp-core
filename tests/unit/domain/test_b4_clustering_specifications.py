from collections.abc import Callable
from importlib.metadata import version

import pytest

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.seeds import Seed
from datp_core.domain.thresholding.clustering import (
    CANONICAL_CLUSTER_K,
    B4ClusteringAlgorithm,
    B4ClusteringSpec,
    B4Fingerprint,
    B4FingerprintField,
    B4FingerprintFitScope,
    B4FingerprintScalerSpec,
    ClusterAssignmentArtifact,
    ClusterAssignmentEntry,
    ClusterCentroidReference,
    ClusterThresholdAggregationSpec,
    ScaledB4Fingerprint,
    ScaledFingerprintReference,
    adjusted_rand_index,
)
from datp_core.domain.thresholding.policies import ThresholdPercentile, ThresholdValue


def _scaled_fingerprint(*, offset: float) -> ScaledB4Fingerprint:
    return ScaledB4Fingerprint(mean=offset, standard_deviation=offset - 1.0, skew=0.0, p95=offset + 2.0)


def _fingerprint_with_unsupported_field() -> B4Fingerprint:
    return _construct_fingerprint_with_unsupported_field(B4Fingerprint)


def _construct_fingerprint_with_unsupported_field(constructor: Callable[..., B4Fingerprint]) -> B4Fingerprint:
    return constructor(mean=1.0, standard_deviation=1.0, skew=0.0, p95=2.0, q=0.95)


def _assignment_artifact() -> ClusterAssignmentArtifact:
    clients = tuple(ClientId(value=f"client-{index}") for index in range(3))
    fingerprints = tuple(_scaled_fingerprint(offset=float(index)) for index in range(3))
    return ClusterAssignmentArtifact(
        clustering_identity=StageFingerprint(value="a" * 64),
        assignments=tuple(
            ClusterAssignmentEntry(client_id=client, cluster_index=index) for index, client in enumerate(clients)
        ),
        scaled_fingerprints=tuple(
            ScaledFingerprintReference(client_id=client, fingerprint=fingerprint)
            for client, fingerprint in zip(clients, fingerprints, strict=True)
        ),
        centroid_references=tuple(
            ClusterCentroidReference(cluster_index=index, fingerprint=fingerprint)
            for index, fingerprint in enumerate(fingerprints)
        ),
        content_hash="b" * 64,
    )


def test_canonical_b4_locks_fingerprint_scaling_algorithm_and_derived_seed() -> None:
    specification = B4ClusteringSpec(
        experiment_seed=Seed(value=7),
        clustering_identity=StageFingerprint(value="c" * 64),
    )

    assert specification.fingerprint_fields == (
        B4FingerprintField.MEAN,
        B4FingerprintField.STANDARD_DEVIATION,
        B4FingerprintField.SKEW,
        B4FingerprintField.P95,
    )
    assert specification.scaler is B4FingerprintScalerSpec.STANDARD_SCALER
    assert specification.scaler_fit_scope is B4FingerprintFitScope.ELIGIBLE_CLIENT_FINGERPRINTS
    assert specification.algorithm is B4ClusteringAlgorithm.KMEANS_PLUS_PLUS
    assert specification.cluster_count == CANONICAL_CLUSTER_K
    assert specification.n_init.value == 10
    assert specification.max_iter.value == 300
    assert specification.random_state != specification.experiment_seed


def test_scikit_learn_version_lock_matches_installed_dependency() -> None:
    specification = B4ClusteringSpec(
        experiment_seed=Seed(value=7),
        clustering_identity=StageFingerprint(value="c" * 64),
    )

    assert specification.scikit_learn_version.value == version("scikit-learn")


def test_b4_fingerprint_rejects_q_as_a_field() -> None:
    with pytest.raises(TypeError):
        _fingerprint_with_unsupported_field()


def test_cluster_aggregation_is_an_unweighted_member_mean_reused_by_assignment_identity() -> None:
    aggregation = ClusterThresholdAggregationSpec(
        percentile=ThresholdPercentile(value="0.95"),
        member_local_thresholds=(ThresholdValue(value=1.0), ThresholdValue(value=5.0), ThresholdValue(value=9.0)),
        cluster_assignment_identity=StageFingerprint(value="d" * 64),
    )

    assert aggregation.aggregate() == ThresholdValue(value=5.0)


def test_fixed_synthetic_assignment_is_byte_stable_and_has_perfect_adjusted_rand() -> None:
    first = _assignment_artifact()
    second = _assignment_artifact()

    assert first == second
    assert adjusted_rand_index(first=first, second=second) == 1.0


def test_cluster_artifact_rejects_noncanonical_centroid_set() -> None:
    artifact = _assignment_artifact()

    with pytest.raises(DomainValidationError):
        ClusterAssignmentArtifact(
            clustering_identity=artifact.clustering_identity,
            assignments=artifact.assignments,
            scaled_fingerprints=artifact.scaled_fingerprints,
            centroid_references=artifact.centroid_references[:2],
            content_hash=artifact.content_hash,
        )
