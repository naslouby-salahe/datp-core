"""Cluster-stability analysis: typed dispersion status coverage and end-to-end membership
analysis against a real committed repository, guarding the two blocker regressions found in
remediation audit -- silently dropping clients through an inner join, and silently persisting
NaN for an empty cluster -- and the additional degenerate scientific states the typed result
must distinguish."""

from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from datp_core.analysis.clustering.models import ClusterDispersionStatus, ClusterMembershipStabilityResult
from datp_core.analysis.clustering.stability import _cluster_dispersion, analyze_cluster_stability
from datp_core.artifacts.codecs.manifest import CURRENT_ARTIFACT_SCHEMA_VERSION
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.payloads import ArtifactCommitMetadata, ArtifactCommitRequest, BytesPayload
from datp_core.artifacts.repository.filesystem import AtomicArtifactRepository
from datp_core.core.hashing import Fingerprint
from datp_core.core.identifiers import ExperimentId, ThresholdPolicyId
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey, node_path
from datp_core.core.seeding import Seed
from datp_core.experiments import ClusterStabilityAnalysisRecord
from datp_core.experiments.catalogue.evaluations import EvaluationSpecRecord, RunRequirement
from datp_core.experiments.identity import IdentityBuilder
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.clustering import (
    ClusterFingerprintConfiguration,
    ClusterStandardizationConfiguration,
    ClusterThresholdPolicyRecord,
    KMeansConfiguration,
)

_FINGERPRINT = Fingerprint("a" * 64)


# --- direct unit coverage of the typed dispersion primitive --------------------------------


def test_available_computes_a_real_value() -> None:
    sizes = {0: 2, 1: 2}
    groups = {0: [1.0, 2.0], 1: [3.0, 5.0]}
    result = _cluster_dispersion(sizes, groups, kind="within")
    assert result.status is ClusterDispersionStatus.AVAILABLE
    # std([1.0, 2.0]) == 0.5, std([3.0, 5.0]) == 1.0; within-cluster dispersion is their mean.
    assert result.value == pytest.approx(0.75)
    assert result.observed_cluster_count == 2
    assert result.available_cluster_count == 2
    assert result.excluded_client_count == 0


def test_empty_cluster_is_typed_not_fabricated_zero_or_nan() -> None:
    sizes = {0: 2, 1: 0}
    groups = {0: [1.0, 2.0], 1: []}
    result = _cluster_dispersion(sizes, groups, kind="within")
    assert result.status is ClusterDispersionStatus.UNAVAILABLE_EMPTY_CLUSTER
    assert result.value is None


def test_no_available_fpr_in_a_non_empty_cluster_is_typed() -> None:
    sizes = {0: 2, 1: 3}
    groups = {0: [0.1, 0.2], 1: []}
    result = _cluster_dispersion(sizes, groups, kind="within")
    assert result.status is ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR
    assert result.excluded_client_count == 3


def test_across_cluster_with_one_contributing_cluster_is_insufficient_observations() -> None:
    sizes = {0: 2, 1: 2}
    groups = {0: [0.1, 0.2], 1: []}
    # Cluster 1 has members but no available values -- caught by no_available_fpr first.
    result = _cluster_dispersion(sizes, groups, kind="across")
    assert result.status is ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR

    # With only one configured cluster, across-cluster dispersion can never be measured
    # regardless of data availability.
    single = _cluster_dispersion({0: 2}, {0: [0.1, 0.2]}, kind="across")
    assert single.status is ClusterDispersionStatus.UNAVAILABLE_INSUFFICIENT_OBSERVATIONS


def test_zero_metric_coverage_is_incomplete_metric_population_not_no_available_fpr() -> None:
    sizes = {0: 2, 1: 2}
    result = _cluster_dispersion(
        sizes, {0: [], 1: []}, kind="within", metric_covered_clients=0, total_clients=4
    )
    assert result.status is ClusterDispersionStatus.UNAVAILABLE_INCOMPLETE_METRIC_POPULATION
    assert result.excluded_client_count == 4


def test_non_finite_computation_is_rejected_not_persisted() -> None:
    sizes = {0: 2, 1: 2}
    groups = {0: [1e300, -1e300], 1: [1.0, 2.0]}
    result = _cluster_dispersion(sizes, groups, kind="within")
    assert result.status is ClusterDispersionStatus.UNAVAILABLE_NON_FINITE_INPUT
    assert result.value is None


# --- end-to-end membership analysis against a real committed repository --------------------


def _commit_parquet(
    repository: AtomicArtifactRepository, *, node_key: StageNodeKey, frame: pl.DataFrame
) -> None:
    buffer = BytesIO()
    frame.write_parquet(buffer)
    request = ArtifactCommitRequest(
        metadata=ArtifactCommitMetadata(
            artifact_key=ArtifactKey(node_key=node_key, kind=ArtifactKind.CLIENT_METRICS),
            artifact_format=ArtifactFormat.PARQUET,
            scientific_fingerprint=_FINGERPRINT,
            execution_fingerprint=_FINGERPRINT,
            relative_path=node_path(node_key),
            parents=(),
            schema_version=CURRENT_ARTIFACT_SCHEMA_VERSION,
            creation_timestamp=time.time(),
            environment_identity="test",
        ),
        payload=BytesPayload(payload_bytes=buffer.getvalue()),
    )
    result = repository.commit(request)
    assert result.success, result.error_message


def _cluster_policy(cluster_count: int) -> ClusterThresholdPolicyRecord:
    return ClusterThresholdPolicyRecord(
        policy="cluster_threshold",
        quantile=0.95,
        quantile_estimator="empirical",
        canonical=True,
        exploratory=False,
        aggregation="mean",
        cluster_count=cluster_count,
        aggregated_quantity="reconstruction_error",
        aggregation_formula="mean",
        median_estimator=None,
        sample_weighting="uniform",
        client_accumulation_order="sorted_client_id",
        fingerprint=ClusterFingerprintConfiguration(
            features=("f1",), estimators={}, degenerate_client_rules={}, non_finite_value_behavior="reject"
        ),
        standardization=ClusterStandardizationConfiguration(method="standard", with_mean=True),
        client_ordering_before_fit="sorted_client_id",
        kmeans=KMeansConfiguration(
            random_seed=0, initialization_runs=10, maximum_iterations=300, convergence_tolerance=1e-4
        ),
        label_canonicalization="ascending_by_mean_threshold",
        insufficient_eligible_clients_behavior="fail",
        degenerate_fingerprint_matrix_behavior="fail",
        required_diagnostics=(),
        threshold_ownership="one_threshold_per_cluster",
    )


def _metric_row(client_id: str, *, fpr: float | None, status: str) -> dict[str, object]:
    return {
        "client_id": client_id,
        "true_positives": 1,
        "false_positives": 1,
        "true_negatives": 1,
        "false_negatives": 1,
        "false_positive_rate": fpr,
        "false_positive_rate_status": status,
        "true_positive_rate": 0.5,
        "true_positive_rate_status": "available",
        "balanced_accuracy": 0.5,
        "balanced_accuracy_status": "available",
        "macro_f1": 0.5,
        "macro_f1_status": "available",
        "auroc": 0.5,
        "auroc_status": "available",
    }


def test_threshold_dispersion_includes_a_client_with_no_metric_row(tmp_path: Path) -> None:
    """A client present in the threshold artifact but entirely absent from the metric frame
    must still contribute to threshold dispersion (regression guard for the inner-join drop),
    while FPR dispersion correctly excludes that client rather than silently dropping the row
    from both."""
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    experiment = SimpleNamespace(
        identifier=ExperimentId("cluster_experiment"),
        evaluations=(
            EvaluationSpecRecord(
                label="cluster_eval",
                threshold_policy_id=ThresholdPolicyId("cluster_k2"),
                run_requirement=RunRequirement.MANDATORY,
                overrides=None,
                population_id=None,
                recalibration_mode=None,
            ),
        ),
    )
    config = SimpleNamespace(threshold_policies=SimpleNamespace(get=lambda _: _cluster_policy(2)))
    analysis = ClusterStabilityAnalysisRecord(
        label="cluster_stability",
        kind="cluster_stability_analysis",
        result_type="cluster_stability_result",
        statistical_profile=None,  # type: ignore[arg-type]
        source_evaluation="cluster_eval",
        comparison_unit="unordered_pair_of_training_seeds",
        produced_fields=(),
        reference_evaluation=None,
        run_requirement=None,
    )
    seeds = (Seed(0), Seed(1))
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier, seed=seed.value, evaluation_label="cluster_eval"
        )
        threshold_node_key = IdentityBuilder.threshold_node_key(context)
        evaluation_node_key = IdentityBuilder.evaluation_node_key(context)
        threshold_frame = pl.DataFrame(
            {
                "client_id": ["c1", "c2", "c3"],
                "cluster_label": [0, 0, 1],
                "threshold": [0.5, 0.6, 0.7],
            }
        )
        _commit_parquet(repository, node_key=threshold_node_key, frame=threshold_frame)
        # c3 has no row at all in the metric frame -- must not silently vanish from threshold
        # dispersion, and must be cleanly excluded (not fabricated) from FPR dispersion.
        metric_frame = pl.DataFrame(
            [_metric_row("c1", fpr=0.1, status="available"), _metric_row("c2", fpr=0.2, status="available")]
        )
        _commit_parquet(repository, node_key=evaluation_node_key, frame=metric_frame)

    result = analyze_cluster_stability(
        analysis,
        repository=repository,
        config=config,  # type: ignore[arg-type]
        experiment=experiment,  # type: ignore[arg-type]
        seeds=seeds,
        experiment_id=experiment.identifier,
    )
    assert isinstance(result, ClusterMembershipStabilityResult)
    for summary in result.seed_summaries:
        # Threshold dispersion reflects all 3 clients (2 in cluster 0, 1 in cluster 1) --
        # cluster 1 has exactly one member so its within-cluster threshold std is 0, not absent.
        assert summary.within_cluster_threshold_dispersion.status is ClusterDispersionStatus.AVAILABLE
        assert summary.across_cluster_threshold_dispersion.status is ClusterDispersionStatus.AVAILABLE
        # FPR dispersion: cluster 1's only client (c3) has no metric row, so that cluster
        # contributes no FPR value -- typed as unavailable, never a fabricated number.
        assert summary.within_cluster_fpr_dispersion.status is ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR
        assert summary.within_cluster_fpr_dispersion.excluded_client_count == 1


def test_metric_client_outside_threshold_population_is_rejected(tmp_path: Path) -> None:
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    experiment = SimpleNamespace(
        identifier=ExperimentId("cluster_experiment"),
        evaluations=(
            EvaluationSpecRecord(
                label="cluster_eval",
                threshold_policy_id=ThresholdPolicyId("cluster_k2"),
                run_requirement=RunRequirement.MANDATORY,
                overrides=None,
                population_id=None,
                recalibration_mode=None,
            ),
        ),
    )
    config = SimpleNamespace(threshold_policies=SimpleNamespace(get=lambda _: _cluster_policy(2)))
    analysis = ClusterStabilityAnalysisRecord(
        label="cluster_stability",
        kind="cluster_stability_analysis",
        result_type="cluster_stability_result",
        statistical_profile=None,  # type: ignore[arg-type]
        source_evaluation="cluster_eval",
        comparison_unit="unordered_pair_of_training_seeds",
        produced_fields=(),
        reference_evaluation=None,
        run_requirement=None,
    )
    seeds = (Seed(0),)
    context = StageJobContext(experiment_id=experiment.identifier, seed=0, evaluation_label="cluster_eval")
    threshold_node_key = IdentityBuilder.threshold_node_key(context)
    evaluation_node_key = IdentityBuilder.evaluation_node_key(context)
    _commit_parquet(
        repository,
        node_key=threshold_node_key,
        frame=pl.DataFrame({"client_id": ["c1", "c2"], "cluster_label": [0, 1], "threshold": [0.5, 0.6]}),
    )
    _commit_parquet(
        repository,
        node_key=evaluation_node_key,
        frame=pl.DataFrame(
            [_metric_row("c1", fpr=0.1, status="available"), _metric_row("ghost", fpr=0.2, status="available")]
        ),
    )

    with pytest.raises(ValueError, match="outside the threshold population"):
        analyze_cluster_stability(
            analysis,
            repository=repository,
            config=config,  # type: ignore[arg-type]
            experiment=experiment,  # type: ignore[arg-type]
            seeds=seeds,
            experiment_id=experiment.identifier,
        )
