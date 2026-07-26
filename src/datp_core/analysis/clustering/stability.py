"""Cluster-stability analysis: how sensitive B4 cluster membership is to fingerprint-feature
ablation and seed variation.

``compute_adjusted_rand_index`` is migrated from ``infrastructure/learning/sklearn_adapter.py``
(that module's other half, AUROC, already lives in ``evaluation/predictive_metrics.py``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal

import numpy as np
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.artifact_access.reader import read_parquet_frame
from datp_core.analysis.clustering.models import (
    ClusterAblationObservation,
    ClusterAblationStabilityResult,
    ClusterDispersionResult,
    ClusterDispersionStatus,
    ClusterMembershipStabilityResult,
    ClusterStabilityAnalysisResult,
    ClusterStabilitySeedSummary,
)
from datp_core.analysis.execution.inputs import AnalysisInputBundle
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.experiments import ClusterStabilityAnalysisRecord, ExperimentRecord, ValueSweepRecord
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    return float(adjusted_rand_score(labels_true, labels_pred))


def analyze_cluster_stability(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    config: ResolvedProjectConfiguration,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ClusterStabilityAnalysisResult:
    if analysis.reference_evaluation is not None:
        return _analyze_cluster_ablation(analysis, store=store, inputs=inputs, experiment=experiment, seeds=seeds)
    return _analyze_cluster_membership(
        analysis, store=store, inputs=inputs, config=config, experiment=experiment, seeds=seeds
    )


def _analyze_cluster_ablation(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
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
        reference = _cluster_membership(experiment, seed.value, ref_eval, None, store=store, inputs=inputs)
        for subset in subsets:
            ablated = _cluster_membership(
                experiment,
                seed.value,
                analysis.source_evaluation,
                subset,
                store=store,
                inputs=inputs,
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


def _cluster_dispersion(
    cluster_sizes: Mapping[int, int],
    value_groups: Mapping[int, list[float]],
    *,
    kind: Literal["within", "across"],
    metric_covered_clients: int | None = None,
    total_clients: int | None = None,
) -> ClusterDispersionResult:
    """Compute a within- or across-cluster dispersion, typed to distinguish every unavailable
    reason from a genuinely computed value. ``value_groups`` may under-represent ``cluster_sizes``
    (e.g. clients with no available FPR); ``metric_covered_clients``/``total_clients`` are only
    supplied for FPR-derived dispersions, where zero metric coverage is a distinct condition from
    a merely incomplete one.
    """
    observed_cluster_count = len(cluster_sizes)
    non_empty_labels = sorted(label for label, size in cluster_sizes.items() if size > 0)
    empty_labels = sorted(label for label, size in cluster_sizes.items() if size == 0)
    if empty_labels:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_EMPTY_CLUSTER,
            value=None,
            reason=f"cluster(s) {empty_labels} have no assigned clients",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=0,
        )
    if metric_covered_clients == 0 and total_clients:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INCOMPLETE_METRIC_POPULATION,
            value=None,
            reason="no metric rows are available for any client in the threshold population",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=0,
            excluded_client_count=total_clients,
        )
    excluded_client_count = sum(cluster_sizes[label] - len(value_groups.get(label, [])) for label in non_empty_labels)
    no_value_labels = [label for label in non_empty_labels if not value_groups.get(label)]
    if no_value_labels:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NO_AVAILABLE_FPR,
            value=None,
            reason=f"cluster(s) {no_value_labels} have no available false-positive-rate values",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels) - len(no_value_labels),
            excluded_client_count=excluded_client_count,
        )
    if kind == "across" and len(non_empty_labels) < 2:
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_INSUFFICIENT_OBSERVATIONS,
            value=None,
            reason="fewer than two clusters contribute values; across-cluster dispersion is undefined",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=excluded_client_count,
        )
    if kind == "within":
        value = float(np.mean([np.std(value_groups[label]) for label in non_empty_labels]))
    else:
        value = float(np.std([np.mean(value_groups[label]) for label in non_empty_labels]))
    if not math.isfinite(value):
        return ClusterDispersionResult(
            status=ClusterDispersionStatus.UNAVAILABLE_NON_FINITE_INPUT,
            value=None,
            reason="dispersion computation produced a non-finite value",
            observed_cluster_count=observed_cluster_count,
            available_cluster_count=len(non_empty_labels),
            excluded_client_count=excluded_client_count,
        )
    return ClusterDispersionResult(
        status=ClusterDispersionStatus.AVAILABLE,
        value=value,
        reason=None,
        observed_cluster_count=observed_cluster_count,
        available_cluster_count=len(non_empty_labels),
        excluded_client_count=excluded_client_count,
    )


def _analyze_cluster_membership(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
    config: ResolvedProjectConfiguration,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ClusterMembershipStabilityResult:
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, ClusterThresholdPolicyRecord):
        raise ValueError(
            f"Cluster stability requires a cluster threshold policy, got '{evaluation.threshold_policy_id.value}'"
        )
    expected_cluster_count = policy.cluster_count
    expected_labels = frozenset(range(expected_cluster_count))

    memberships: dict[int, dict[str, int]] = {}
    seed_summaries: list[ClusterStabilitySeedSummary] = []
    for seed in seeds:
        missing = f"Cluster stability artifacts are unavailable for seed {seed.value}"
        threshold_frame = read_parquet_frame(
            store,
            inputs.thresholds(_evaluation_context(experiment, analysis.source_evaluation, seed.value, None)),
            missing_message=missing,
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

        for label_value in labels.values():
            if label_value not in expected_labels:
                raise ValueError(
                    f"Cluster label {label_value} is outside the configured range "
                    f"[0, {expected_cluster_count}) for seed {seed.value}"
                )

        cluster_membership_counts: dict[int, int] = dict.fromkeys(expected_labels, 0)
        for label_value in threshold_frame["cluster_label"].to_list():
            label_int = int(label_value)
            cluster_membership_counts[label_int] = cluster_membership_counts.get(label_int, 0) + 1

        # Threshold dispersion is built directly from the threshold artifact: every
        # threshold-bearing client contributes, independent of metric/FPR availability.
        threshold_groups: dict[int, list[float]] = {label: [] for label in expected_labels}
        for label, threshold in threshold_frame.select("cluster_label", "threshold").iter_rows():
            threshold_groups[int(label)].append(float(threshold))

        metric_frame = validate_client_metric_frame(
            read_parquet_frame(
                store,
                inputs.evaluation_metrics(
                    _evaluation_context(experiment, analysis.source_evaluation, seed.value, None)
                ),
                missing_message=missing,
            )
        )
        metric_client_ids = metric_frame["client_id"].to_list()
        if len(metric_client_ids) != len(set(metric_client_ids)):
            raise ValueError(f"Duplicate client_id in metric frame for seed {seed.value}")
        unknown_metric_clients = set(metric_client_ids) - set(threshold_client_ids)
        if unknown_metric_clients:
            raise ValueError(
                f"Metric frame references clients outside the threshold population for seed "
                f"{seed.value}: {sorted(unknown_metric_clients)}"
            )

        # FPR dispersion is built from a left join against the complete threshold population, so a
        # client entirely missing from the metric frame is excluded rather than dropping the row.
        joined = threshold_frame.select("client_id", "cluster_label").join(
            metric_frame.select("client_id", "false_positive_rate", "false_positive_rate_status"),
            on="client_id",
            how="left",
        )
        if joined.height != len(threshold_client_ids):
            raise ValueError(f"Threshold/metric join changed the client population for seed {seed.value}")

        fpr_groups: dict[int, list[float]] = {label: [] for label in expected_labels}
        metric_covered_clients = 0
        for label, status, fpr in joined.select(
            "cluster_label", "false_positive_rate_status", "false_positive_rate"
        ).iter_rows():
            if status is not None:
                metric_covered_clients += 1
            if status == "available" and fpr is not None:
                fpr_value = float(fpr)
                if not math.isfinite(fpr_value):
                    raise ValueError(
                        f"Non-finite false-positive-rate value in cluster stability input for seed {seed.value}"
                    )
                fpr_groups[int(label)].append(fpr_value)

        seed_summaries.append(
            ClusterStabilitySeedSummary(
                seed=int(seed.value),
                cluster_membership_per_client=labels,
                cluster_size={str(label): cluster_membership_counts[label] for label in expected_labels},
                singleton_cluster_flag=any(cluster_membership_counts[label] == 1 for label in expected_labels),
                empty_cluster_flag=any(cluster_membership_counts[label] == 0 for label in expected_labels),
                within_cluster_threshold_dispersion=_cluster_dispersion(
                    cluster_membership_counts, threshold_groups, kind="within"
                ),
                within_cluster_fpr_dispersion=_cluster_dispersion(
                    cluster_membership_counts,
                    fpr_groups,
                    kind="within",
                    metric_covered_clients=metric_covered_clients,
                    total_clients=len(threshold_client_ids),
                ),
                across_cluster_threshold_dispersion=_cluster_dispersion(
                    cluster_membership_counts, threshold_groups, kind="across"
                ),
                across_cluster_mean_fpr_dispersion=_cluster_dispersion(
                    cluster_membership_counts,
                    fpr_groups,
                    kind="across",
                    metric_covered_clients=metric_covered_clients,
                    total_clients=len(threshold_client_ids),
                ),
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
    expected_pair_count = len(sorted_seeds) * (len(sorted_seeds) - 1) // 2
    if len(aris) != expected_pair_count:
        raise ValueError(f"ARI pair count mismatch: expected {expected_pair_count}, got {len(aris)}")
    return ClusterMembershipStabilityResult(
        analysis_label=analysis.label,
        comparison_unit=analysis.comparison_unit,
        seed_summaries=tuple(seed_summaries),
        adjusted_rand_index=tuple(aris),
        mean_adjusted_rand_index=sum(aris) / len(aris) if aris else None,
    )


def _cluster_membership(
    experiment: ExperimentRecord,
    seed: int,
    label: str,
    features: tuple[str, ...] | None,
    *,
    store: ArtifactStore,
    inputs: AnalysisInputBundle,
) -> dict[str, int]:
    frame = read_parquet_frame(
        store,
        inputs.thresholds(_evaluation_context(experiment, label, seed, features)),
        missing_message=f"Cluster threshold artifact is unavailable for seed {seed}",
    )
    if "cluster_label" not in frame.columns or frame["cluster_label"].null_count() > 0:
        raise ValueError(f"Cluster labels are unavailable for seed {seed}")
    return {str(client): int(label) for client, label in frame.select("client_id", "cluster_label").iter_rows()}


def _evaluation_context(
    experiment: ExperimentRecord, label: str, seed: int, features: tuple[str, ...] | None
) -> StageJobContext:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    return StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
        fingerprint_features=features,
    )


__all__ = ["analyze_cluster_stability", "compute_adjusted_rand_index"]
