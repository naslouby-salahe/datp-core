from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.runtime.seeds import Seed
from datp_core.domain.thresholding.clustering import (
    B4ClusteringAlgorithm,
    B4ClusteringSpec,
    B4FingerprintField,
    B4FingerprintFitScope,
    B4FingerprintScalerSpec,
    CanonicalB4ClusteringProfile,
    ClusterCount,
    KMeansInitializationCount,
    KMeansMaximumIterations,
    PinnedScikitLearnVersion,
    is_canonical_k,
)


def _canonical_b4_profile() -> CanonicalB4ClusteringProfile:
    return CanonicalB4ClusteringProfile(
        fingerprint_fields=(
            B4FingerprintField.MEAN,
            B4FingerprintField.STANDARD_DEVIATION,
            B4FingerprintField.SKEW,
            B4FingerprintField.P95,
        ),
        scaler=B4FingerprintScalerSpec.STANDARD_SCALER,
        scaler_fit_scope=B4FingerprintFitScope.ELIGIBLE_CLIENT_FINGERPRINTS,
        algorithm=B4ClusteringAlgorithm.KMEANS_PLUS_PLUS,
        n_init=KMeansInitializationCount(value=10),
        max_iter=KMeansMaximumIterations(value=300),
        scikit_learn_version=PinnedScikitLearnVersion(value="1.9.0"),
    )


@given(st.integers(min_value=1, max_value=20))
def test_only_locked_k_is_constructible_as_canonical_b4(cluster_count: int) -> None:
    candidate = ClusterCount(value=cluster_count)

    assert is_canonical_k(cluster_count=candidate) is (cluster_count == 3)
    assert B4ClusteringSpec(
        experiment_seed=Seed(value=3),
        clustering_identity=StageFingerprint(value="e" * 64),
        profile=_canonical_b4_profile(),
    ).is_canonical_k
