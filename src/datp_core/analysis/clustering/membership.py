"""Cluster membership extraction, stability, and population alignment."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from attrs import define

from datp_core.analysis.clustering.dispersion import (
    ClusterAblationObservation,
    ClusterAblationStabilityResult,
    ClusterDispersionResult,
    cluster_dispersion,
    compute_adjusted_rand_index,
)
from datp_core.analysis.enums import ClusterDispersionKind
from datp_core.analysis.errors import (
    ArtifactMissingError,
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.artifacts import AnalysisInputBundle
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.seeding import Seed
from datp_core.evaluation.metrics.models import MetricStatus
from datp_core.experiments import ClusterStabilityAnalysisRecord, ExperimentRecord, ValueSweepRecord
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord


@define(frozen=True, slots=True, kw_only=True)
class ClusterStabilitySeedSummary:
    seed: int
    cluster_membership_per_client: Mapping[str, int]
    cluster_size: Mapping[str, int]
    singleton_cluster_flag: bool
    empty_cluster_flag: bool
    within_cluster_threshold_dispersion: ClusterDispersionResult
    within_cluster_fpr_dispersion: ClusterDispersionResult
    across_cluster_threshold_dispersion: ClusterDispersionResult
    across_cluster_mean_fpr_dispersion: ClusterDispersionResult


@define(frozen=True, slots=True, kw_only=True)
class ClusterMembershipStabilityResult:
    analysis_label: str
    comparison_unit: str
    seed_summaries: tuple[ClusterStabilitySeedSummary, ...]
    adjusted_rand_index: tuple[float, ...]
    mean_adjusted_rand_index: float | None


ClusterStabilityAnalysisResult = ClusterAblationStabilityResult | ClusterMembershipStabilityResult


def analyze_cluster_stability(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    config: ResolvedProjectConfiguration,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ClusterStabilityAnalysisResult:
    if analysis.reference_evaluation is not None:
        return _analyze_cluster_ablation(
            analysis, artifacts=artifacts, inputs=inputs, experiment=experiment, seeds=seeds
        )
    return _analyze_cluster_membership(
        analysis, artifacts=artifacts, inputs=inputs, config=config, experiment=experiment, seeds=seeds
    )


def _analyze_cluster_ablation(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    artifacts: AnalysisArtifactRepository,
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
        raise InvalidAnalysisConfigurationError(
            "Cluster ablation analysis has no configured fingerprint subsets"
        )
    observations: list[ClusterAblationObservation] = []
    ref_eval = analysis.reference_evaluation
    if ref_eval is None:
        raise InvalidAnalysisConfigurationError(
            "Reference evaluation is required for cluster ablation analysis"
        )
    for seed in seeds:
        reference = _cluster_membership(experiment, seed.value, ref_eval, None, artifacts=artifacts, inputs=inputs)
        for subset in subsets:
            ablated = _cluster_membership(
                experiment, seed.value, analysis.source_evaluation, subset, artifacts=artifacts, inputs=inputs
            )
            clients = sorted(set(reference) & set(ablated))
            if set(reference) != set(ablated):
                raise PopulationAlignmentError(
                    "Cluster ablation membership has an incompatible client population"
                )
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
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
    config: ResolvedProjectConfiguration,
    experiment: ExperimentRecord,
    seeds: tuple[Seed, ...],
) -> ClusterMembershipStabilityResult:
    evaluation = next(item for item in experiment.evaluations if item.label == analysis.source_evaluation)
    policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    if not isinstance(policy, ClusterThresholdPolicyRecord):
        raise InvalidAnalysisConfigurationError(
            f"Cluster stability requires a cluster threshold policy, got '{evaluation.threshold_policy_id.value}'"
        )
    expected_cluster_count = policy.cluster_count
    expected_labels = frozenset(range(expected_cluster_count))

    # TODO: replace with tuple[ClientClusterMembership, ...] when the record type is created
    memberships: dict[int, dict[str, int]] = {}
    seed_summaries: list[ClusterStabilitySeedSummary] = []
    for seed in seeds:
        threshold_frame = artifacts.threshold_frame(
            inputs.thresholds(_evaluation_context(experiment, analysis.source_evaluation, seed.value, None)),
        )
        if ThresholdColumn.CLUSTER_LABEL.value not in threshold_frame.columns:
            raise ArtifactMissingError(f"Cluster labels are unavailable for seed {seed.value}")
        if threshold_frame[ThresholdColumn.CLUSTER_LABEL.value].null_count() > 0:
            raise ArtifactSchemaViolationError(f"Cluster labels contain nulls for seed {seed.value}")
        threshold_client_ids = threshold_frame[ThresholdColumn.CLIENT_ID.value].to_list()
        if len(threshold_client_ids) != len(set(threshold_client_ids)):
            raise ArtifactSchemaViolationError(f"Duplicate client_id in threshold frame for seed {seed.value}")

        labels = {
            str(client): int(label)
            for client, label in threshold_frame.select(
                ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value
            ).iter_rows()
        }
        memberships[int(seed.value)] = labels

        for label_value in labels.values():
            if label_value not in expected_labels:
                raise ScientificContractViolationError(
                    f"Cluster label {label_value} is outside the configured range "
                    f"[0, {expected_cluster_count}) for seed {seed.value}"
                )

        cluster_membership_counts: dict[int, int] = dict.fromkeys(expected_labels, 0)
        for label_value in threshold_frame[ThresholdColumn.CLUSTER_LABEL.value].to_list():
            label_int = int(label_value)
            cluster_membership_counts[label_int] = cluster_membership_counts.get(label_int, 0) + 1

        threshold_groups: dict[int, list[float]] = {label: [] for label in expected_labels}
        for label, threshold in threshold_frame.select(
            ThresholdColumn.CLUSTER_LABEL.value, ThresholdColumn.THRESHOLD.value
        ).iter_rows():
            threshold_groups[int(label)].append(float(threshold))

        metric_frame = artifacts.client_metric_frame(
            inputs.evaluation_metrics(_evaluation_context(experiment, analysis.source_evaluation, seed.value, None)),
        )
        metric_client_ids = metric_frame[MetricColumn.CLIENT_ID.value].to_list()
        if len(metric_client_ids) != len(set(metric_client_ids)):
            raise ArtifactSchemaViolationError(f"Duplicate client_id in metric frame for seed {seed.value}")
        unknown_metric_clients = set(metric_client_ids) - set(threshold_client_ids)
        if unknown_metric_clients:
            raise PopulationAlignmentError(
                f"Metric frame references clients outside the threshold population for seed "
                f"{seed.value}: {sorted(unknown_metric_clients)}"
            )

        joined = threshold_frame.select(
            ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value
        ).join(
            metric_frame.select(
                MetricColumn.CLIENT_ID.value,
                MetricColumn.FALSE_POSITIVE_RATE.value,
                MetricColumn.FALSE_POSITIVE_RATE_STATUS.value,
            ),
            on=MetricColumn.CLIENT_ID.value,
            how="left",
        )
        if joined.height != len(threshold_client_ids):
            raise PopulationAlignmentError(f"Threshold/metric join changed the client population for seed {seed.value}")

        fpr_groups: dict[int, list[float]] = {label: [] for label in expected_labels}
        metric_covered_clients = 0
        for label, status, fpr in joined.select(
            ThresholdColumn.CLUSTER_LABEL.value,
            MetricColumn.FALSE_POSITIVE_RATE_STATUS.value,
            MetricColumn.FALSE_POSITIVE_RATE.value,
        ).iter_rows():
            if status is not None:
                metric_covered_clients += 1
            if status == MetricStatus.AVAILABLE.value and fpr is not None:
                fpr_value = float(fpr)
                if not math.isfinite(fpr_value):
                    raise ArtifactSchemaViolationError(
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
                within_cluster_threshold_dispersion=cluster_dispersion(
                    cluster_membership_counts, threshold_groups, kind=ClusterDispersionKind.WITHIN.value
                ),
                within_cluster_fpr_dispersion=cluster_dispersion(
                    cluster_membership_counts,
                    fpr_groups,
                    kind=ClusterDispersionKind.WITHIN.value,
                    metric_covered_clients=metric_covered_clients,
                    total_clients=len(threshold_client_ids),
                ),
                across_cluster_threshold_dispersion=cluster_dispersion(
                    cluster_membership_counts, threshold_groups, kind=ClusterDispersionKind.ACROSS.value
                ),
                across_cluster_mean_fpr_dispersion=cluster_dispersion(
                    cluster_membership_counts,
                    fpr_groups,
                    kind=ClusterDispersionKind.ACROSS.value,
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
            raise PopulationAlignmentError(
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
        raise ScientificContractViolationError(
            f"ARI pair count mismatch: expected {expected_pair_count}, got {len(aris)}"
        )
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
    artifacts: AnalysisArtifactRepository,
    inputs: AnalysisInputBundle,
) -> dict[str, int]:
    # TODO: replace return type with tuple[ClientClusterMembership, ...] when record type exists
    frame = artifacts.threshold_frame(
        inputs.thresholds(_evaluation_context(experiment, label, seed, features)),
    )
    if ThresholdColumn.CLUSTER_LABEL.value not in frame.columns or frame[ThresholdColumn.CLUSTER_LABEL.value].null_count() > 0:
        raise ArtifactMissingError(f"Cluster labels are unavailable for seed {seed}")
    return {
        str(client): int(label)
        for client, label in frame.select(
            ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value
        ).iter_rows()
    }


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
