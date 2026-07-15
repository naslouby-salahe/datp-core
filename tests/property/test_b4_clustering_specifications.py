from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.runtime.seeds import Seed
from datp_core.domain.thresholding.clustering import B4ClusteringSpec, ClusterCount, is_canonical_k


@given(st.integers(min_value=1, max_value=20))
def test_only_locked_k_is_constructible_as_canonical_b4(cluster_count: int) -> None:
    candidate = ClusterCount(value=cluster_count)

    assert is_canonical_k(cluster_count=candidate) is (cluster_count == 3)
    assert B4ClusteringSpec(
        experiment_seed=Seed(value=3),
        clustering_identity=StageFingerprint(value="e" * 64),
    ).is_canonical_k
