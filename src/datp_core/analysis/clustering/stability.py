"""Cluster-stability analysis: how sensitive B4 cluster membership is to fingerprint-feature
ablation and seed variation.

``compute_adjusted_rand_index`` is migrated from ``infrastructure/learning/sklearn_adapter.py``
(that module's other half, AUROC, already lives in ``evaluation/predictive_metrics.py``).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.clustering.models import (
    ClusterAblationObservation,
    ClusterAblationStabilityResult,
    ClusterMembershipStabilityResult,
    ClusterStabilityAnalysisResult,
    ClusterStabilitySeedSummary,
)
from datp_core.analysis.statistics.descriptive import group_mean_std, mean_group_std
from datp_core.artifacts.models import ArtifactRepository
from datp_core.contracts.frames import validate_client_metric_frame
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.core.values import Seed
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.models import ClusterStabilityAnalysisRecord, ExperimentRecord, ValueSweepRecord
from datp_core.pipeline.models import StageJobContext


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    return float(adjusted_rand_score(labels_true, labels_pred))


def analyze_cluster_stability(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> ClusterStabilityAnalysisResult:
    if analysis.reference_evaluation is not None:
        return _analyze_cluster_ablation(
            analysis, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
        )
    return _analyze_cluster_membership(
        analysis, repository=repository, experiment=experiment, seeds=seeds, run_id=run_id
    )


def _analyze_cluster_ablation(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> ClusterAblationStabilityResult:
    source = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    override = (source.overrides or {}).get("fingerprint_features")
    sweep_name = override.get("from_sweep") if isinstance(override, Mapping) else None
    subsets = tuple(
        value
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value)
    )
    if not subsets:
        raise ValueError("Cluster ablation analysis has no configured fingerprint subsets")
    observations: list[ClusterAblationObservation] = []
    ref_eval = analysis.reference_evaluation
    assert ref_eval is not None  # guarded by _analyze_cluster_ablation caller
    for seed in seeds:
        reference = _cluster_membership(
            experiment.identifier, seed.value, ref_eval, None, run_id, repository=repository
        )
        for subset in subsets:
            ablated = _cluster_membership(
                experiment.identifier, seed.value, analysis.source_evaluation, subset, run_id, repository=repository
            )
            clients = sorted(set(reference) & set(ablated))
            if set(reference) != set(ablated):
                raise ValueError("Cluster ablation membership has an incompatible client population")
            observations.append(
                ClusterAblationObservation(
                    seed=seed.value,
                    fingerprint_features=subset,
                    adjusted_rand_index=compute_adjusted_rand_index(
                        np.array([reference[client] for client in clients]),
                        np.array([ablated[client] for client in clients]),
                    ),
                )
            )
    return ClusterAblationStabilityResult(
        analysis_label=analysis.label,
        comparison_unit=analysis.comparison_unit,
        reference_evaluation=ref_eval,
        observations=tuple(observations),
    )


def _analyze_cluster_membership(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    repository: ArtifactRepository,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
    run_id: RunId,
) -> ClusterMembershipStabilityResult:
    memberships: dict[int, dict[str, int]] = {}
    seed_summaries: list[ClusterStabilitySeedSummary] = []
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier, seed=seed.value, evaluation_label=analysis.source_evaluation
        )
        missing = f"Cluster stability artifacts are unavailable for seed {seed.value}"
        threshold_frame = read_parquet_frame(
            repository, run_id, IdentityBuilder.threshold_job_id(context), missing_message=missing
        )
        if "cluster_label" not in threshold_frame.columns or threshold_frame["cluster_label"].null_count() > 0:
            raise ValueError(f"Cluster labels are unavailable for seed {seed.value}")
        metric_frame = validate_client_metric_frame(
            read_parquet_frame(repository, run_id, IdentityBuilder.evaluation_job_id(context), missing_message=missing)
        )
        joined = threshold_frame.join(
            metric_frame.select("client_id", "false_positive_rate", "false_positive_rate_status"), on="client_id"
        )
        labels = {str(client): int(label) for client, label in joined.select("client_id", "cluster_label").iter_rows()}
        memberships[int(seed.value)] = labels
        clusters: dict[int, list[tuple[float, float]]] = {}
        for label, threshold, fpr, status in joined.select(
            "cluster_label", "threshold", "false_positive_rate", "false_positive_rate_status"
        ).iter_rows():
            if status == "available" and fpr is not None:
                clusters.setdefault(int(label), []).append((float(threshold), float(fpr)))
        seed_summaries.append(
            ClusterStabilitySeedSummary(
                seed=int(seed.value),
                cluster_membership_per_client=labels,
                cluster_size={str(label): len(values) for label, values in clusters.items()},
                singleton_cluster_flag=any(len(values) == 1 for values in clusters.values()),
                empty_cluster_flag=False,
                within_cluster_threshold_dispersion=mean_group_std(list(clusters.values()), 0),
                within_cluster_fpr_dispersion=mean_group_std(list(clusters.values()), 1),
                across_cluster_threshold_dispersion=group_mean_std(list(clusters.values()), 0),
                across_cluster_mean_fpr_dispersion=group_mean_std(list(clusters.values()), 1),
            )
        )
    aris = [
        compute_adjusted_rand_index(
            np.array([memberships[left][client] for client in sorted(memberships[left])]),
            np.array([memberships[right][client] for client in sorted(memberships[left])]),
        )
        for index, left in enumerate(sorted(memberships))
        for right in sorted(memberships)[index + 1 :]
        if set(memberships[left]) == set(memberships[right])
    ]
    return ClusterMembershipStabilityResult(
        analysis_label=analysis.label,
        comparison_unit=analysis.comparison_unit,
        seed_summaries=tuple(seed_summaries),
        adjusted_rand_index=tuple(aris),
        mean_adjusted_rand_index=sum(aris) / len(aris) if aris else None,
    )


def _cluster_membership(
    experiment_id: ExperimentId,
    seed: int,
    label: str,
    features: tuple[str, ...] | None,
    run_id: RunId,
    *,
    repository: ArtifactRepository,
) -> dict[str, int]:
    context = StageJobContext(
        experiment_id=experiment_id, seed=seed, evaluation_label=label, fingerprint_features=features
    )
    frame = read_parquet_frame(
        repository,
        run_id,
        IdentityBuilder.threshold_job_id(context),
        missing_message=f"Cluster threshold artifact is unavailable for seed {seed}",
    )
    if "cluster_label" not in frame.columns or frame["cluster_label"].null_count() > 0:
        raise ValueError(f"Cluster labels are unavailable for seed {seed}")
    return {str(client): int(label) for client, label in frame.select("client_id", "cluster_label").iter_rows()}


__all__ = ["analyze_cluster_stability", "compute_adjusted_rand_index"]
