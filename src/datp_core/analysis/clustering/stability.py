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
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.core.identifiers import ExperimentId, RunId
from datp_core.core.seeding import Seed
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments import ClusterStabilityAnalysisRecord, ExperimentRecord, ValueSweepRecord
from datp_core.pipeline.stages.context import StageJobContext


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
    observed_labels: set[int] = set()
    for seed in seeds:
        context = StageJobContext(
            experiment_id=experiment.identifier, seed=seed.value, evaluation_label=analysis.source_evaluation
        )
        missing = f"Cluster stability artifacts are unavailable for seed {seed.value}"
        threshold_frame = read_parquet_frame(
            repository, run_id, IdentityBuilder.threshold_job_id(context), missing_message=missing
        )
        if "cluster_label" not in threshold_frame.columns:
            raise ValueError(f"Cluster labels are unavailable for seed {seed.value}")
        if threshold_frame["cluster_label"].null_count() > 0:
            raise ValueError(f"Cluster labels contain nulls for seed {seed.value}")
        threshold_client_ids = threshold_frame["client_id"].to_list()
        if len(threshold_client_ids) != len(set(threshold_client_ids)):
            raise ValueError(f"Duplicate client_id in threshold frame for seed {seed.value}")

        labels = {
            str(client): int(label)
            for client, label in threshold_frame.select("client_id", "cluster_label").iter_rows()
        }
        memberships[int(seed.value)] = labels
        observed_labels.update(labels.values())

        cluster_membership_counts: dict[int, int] = {}
        for label_value in threshold_frame["cluster_label"].to_list():
            label_int = int(label_value)
            cluster_membership_counts[label_int] = cluster_membership_counts.get(label_int, 0) + 1

        metric_frame = validate_client_metric_frame(
            read_parquet_frame(repository, run_id, IdentityBuilder.evaluation_job_id(context), missing_message=missing)
        )
        metric_client_ids = metric_frame["client_id"].to_list()
        if len(metric_client_ids) != len(set(metric_client_ids)):
            raise ValueError(f"Duplicate client_id in metric frame for seed {seed.value}")

        joined = threshold_frame.join(
            metric_frame.select("client_id", "false_positive_rate", "false_positive_rate_status"), on="client_id"
        )
        fpr_clusters: dict[int, list[tuple[float, float]]] = {}
        for label, threshold, fpr, status in joined.select(
            "cluster_label", "threshold", "false_positive_rate", "false_positive_rate_status"
        ).iter_rows():
            if status == "available" and fpr is not None:
                fpr_clusters.setdefault(int(label), []).append((float(threshold), float(fpr)))

        seed_summaries.append(
            ClusterStabilitySeedSummary(
                seed=int(seed.value),
                cluster_membership_per_client=labels,
                cluster_size={str(label): cluster_membership_counts.get(label, 0) for label in cluster_membership_counts},
                singleton_cluster_flag=any(count == 1 for count in cluster_membership_counts.values()),
                empty_cluster_flag=any(count == 0 for count in cluster_membership_counts.values()),
                within_cluster_threshold_dispersion=mean_group_std(list(fpr_clusters.values()), 0),
                within_cluster_fpr_dispersion=mean_group_std(list(fpr_clusters.values()), 1),
                across_cluster_threshold_dispersion=group_mean_std(list(fpr_clusters.values()), 0),
                across_cluster_mean_fpr_dispersion=group_mean_std(list(fpr_clusters.values()), 1),
            )
        )

    sorted_seeds = sorted(memberships)
    reference = memberships[sorted_seeds[0]]
    reference_clients = set(reference)
    for seed_value in sorted_seeds[1:]:
        if set(memberships[seed_value]) != reference_clients:
            raise ValueError(
                f"Incompatible client populations across seeds for ARI computation: "
                f"seed {sorted_seeds[0]} has {len(reference_clients)} clients, "
                f"seed {seed_value} has {len(memberships[seed_value])} clients"
            )

    aris = [
        compute_adjusted_rand_index(
            np.array([memberships[left][client] for client in sorted(memberships[left])]),
            np.array([memberships[right][client] for client in sorted(memberships[left])]),
        )
        for index, left in enumerate(sorted_seeds)
        for right in sorted_seeds[index + 1 :]
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
