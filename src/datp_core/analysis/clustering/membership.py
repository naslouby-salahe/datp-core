"""Cluster membership extraction, stability, and population alignment."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

from datp_core.analysis.clustering.dispersion import (
    cluster_dispersion,
    compute_adjusted_rand_index,
)
from datp_core.analysis.contracts import (
    ClientClusterMembership,
    ClusterAblationObservation,
    ClusterAblationStabilityResult,
    ClusterMembershipStabilityResult,
    ClusterSize,
    ClusterStabilityAnalysisResult,
    ClusterStabilitySeedSummary,
    PairedAnalysisCell,
)
from datp_core.analysis.enums import ClusterDispersionKind
from datp_core.analysis.errors import (
    ArtifactMissingError,
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.analysis.runtime.runner import run_analysis
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, ClusterLabel, EvaluationLabel
from datp_core.core.seeding import Seed
from datp_core.evaluation.metrics.models import MetricStatus
from datp_core.experiments import ClusterStabilityAnalysisRecord, ValueSweepRecord
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord


@run_analysis.register
def analyze_cluster_stability(
    specification: ClusterStabilityAnalysisRecord,
    context: AnalysisExecutionContext,
    cell: PairedAnalysisCell | None = None,
) -> tuple[ClusterStabilityAnalysisResult, ...]:
    """Execute cluster stability or ablation analysis across seeds."""
    if specification.reference_evaluation is not None:
        res = _analyze_cluster_ablation(specification, context=context)
        return (res,)
    res_mem = _analyze_cluster_membership(specification, context=context)
    return (res_mem,)


def _analyze_cluster_ablation(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    context: AnalysisExecutionContext,
) -> ClusterAblationStabilityResult:
    source_label = EvaluationLabel(analysis.source_evaluation)
    ref_label = EvaluationLabel(analysis.reference_evaluation) if analysis.reference_evaluation is not None else None
    if ref_label is None:
        raise InvalidAnalysisConfigurationError(
            "Reference evaluation is required for cluster ablation analysis"
        )

    source = context.evaluation(source_label)
    override = (source.overrides or {}).get("fingerprint_features")
    sweep_name = override.get("from_sweep") if isinstance(override, Mapping) else None

    subsets = tuple(
        value
        for sweep in context.experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value)
    )
    if not subsets:
        raise InvalidAnalysisConfigurationError(
            "Cluster ablation analysis has no configured fingerprint subsets"
        )

    observations: list[ClusterAblationObservation] = []
    for seed in context.seeds:
        reference_memberships = _cluster_membership(context, seed, ref_label, None)
        ref_map = {m.client_id: m.cluster_label for m in reference_memberships}

        for subset in subsets:
            ablated_memberships = _cluster_membership(context, seed, source_label, subset)
            ablated_map = {m.client_id: m.cluster_label for m in ablated_memberships}

            clients = sorted(set(ref_map) & set(ablated_map), key=lambda c: c.value)
            if set(ref_map) != set(ablated_map):
                raise PopulationAlignmentError(
                    "Cluster ablation membership has an incompatible client population"
                )
            observations.append(
                ClusterAblationObservation(
                    seed=seed,
                    fingerprint_features=subset,
                    adjusted_rand_index=compute_adjusted_rand_index(
                        np.array([int(ref_map[c].value) for c in clients]),
                        np.array([int(ablated_map[c].value) for c in clients]),
                    ),
                )
            )
    return ClusterAblationStabilityResult(
        analysis_label=AnalysisLabel(analysis.label),
        comparison_unit=analysis.comparison_unit,
        reference_evaluation=ref_label,
        observations=tuple(observations),
    )


def _analyze_cluster_membership(
    analysis: ClusterStabilityAnalysisRecord,
    *,
    context: AnalysisExecutionContext,
) -> ClusterMembershipStabilityResult:
    source_label = EvaluationLabel(analysis.source_evaluation)
    policy_id = context.threshold_policy_id(source_label)
    policy = context.config.threshold_policies.get(policy_id)

    if not isinstance(policy, ClusterThresholdPolicyRecord):
        raise InvalidAnalysisConfigurationError(
            f"Cluster stability requires a cluster threshold policy, got '{policy_id.value}'"
        )
    expected_cluster_count = policy.cluster_count
    expected_labels = tuple(ClusterLabel(str(i)) for i in range(expected_cluster_count))
    expected_set = set(expected_labels)

    memberships_by_seed: dict[Seed, tuple[ClientClusterMembership, ...]] = {}
    seed_summaries: list[ClusterStabilitySeedSummary] = []

    for seed in context.seeds:
        eval_ctx = context.evaluation_context(source_label, seed)
        threshold_frame = context.artifacts.thresholds(eval_ctx)

        if ThresholdColumn.CLUSTER_LABEL.value not in threshold_frame.columns:
            raise ArtifactMissingError(f"Cluster labels are unavailable for seed {seed.value}")
        if threshold_frame[ThresholdColumn.CLUSTER_LABEL.value].null_count() > 0:
            raise ArtifactSchemaViolationError(f"Cluster labels contain nulls for seed {seed.value}")
        threshold_client_ids = threshold_frame[ThresholdColumn.CLIENT_ID.value].to_list()
        if len(threshold_client_ids) != len(set(threshold_client_ids)):
            raise ArtifactSchemaViolationError(f"Duplicate client_id in threshold frame for seed {seed.value}")

        memberships_list: list[ClientClusterMembership] = []
        for client, label_val in threshold_frame.select(
            ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value
        ).iter_rows():
            cid = ClientId(str(client))
            clabel = ClusterLabel(str(int(label_val)))
            if clabel not in expected_set:
                raise ScientificContractViolationError(
                    f"Cluster label {clabel.value} is outside configured range for seed {seed.value}"
                )
            memberships_list.append(ClientClusterMembership(client_id=cid, cluster_label=clabel))

        memberships_tuple = tuple(memberships_list)
        memberships_by_seed[seed] = memberships_tuple

        cluster_counts_map: dict[ClusterLabel, int] = {lbl: 0 for lbl in expected_labels}
        for m in memberships_tuple:
            cluster_counts_map[m.cluster_label] += 1

        cluster_sizes_tuple = tuple(
            ClusterSize(cluster_label=lbl, client_count=cluster_counts_map[lbl]) for lbl in expected_labels
        )

        threshold_groups: dict[ClusterLabel, list[float]] = {lbl: [] for lbl in expected_labels}
        for label_val, threshold in threshold_frame.select(
            ThresholdColumn.CLUSTER_LABEL.value, ThresholdColumn.THRESHOLD.value
        ).iter_rows():
            threshold_groups[ClusterLabel(str(int(label_val)))].append(float(threshold))

        metric_frame = context.artifacts.client_metrics(eval_ctx)
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
            raise PopulationAlignmentError(f"Threshold/metric join changed client population for seed {seed.value}")

        fpr_groups: dict[ClusterLabel, list[float]] = {lbl: [] for lbl in expected_labels}
        metric_covered_clients = 0
        for label_val, status, fpr in joined.select(
            ThresholdColumn.CLUSTER_LABEL.value,
            MetricColumn.FALSE_POSITIVE_RATE_STATUS.value,
            MetricColumn.FALSE_POSITIVE_RATE.value,
        ).iter_rows():
            clabel = ClusterLabel(str(int(label_val)))
            if status is not None:
                metric_covered_clients += 1
            if status == MetricStatus.AVAILABLE.value and fpr is not None:
                fpr_val = float(fpr)
                if not math.isfinite(fpr_val):
                    raise ArtifactSchemaViolationError(
                        f"Non-finite false-positive-rate in cluster stability for seed {seed.value}"
                    )
                fpr_groups[clabel].append(fpr_val)

        seed_summaries.append(
            ClusterStabilitySeedSummary(
                seed=seed,
                cluster_memberships=memberships_tuple,
                cluster_sizes=cluster_sizes_tuple,
                singleton_cluster_flag=any(cluster_counts_map[lbl] == 1 for lbl in expected_labels),
                empty_cluster_flag=any(cluster_counts_map[lbl] == 0 for lbl in expected_labels),
                within_cluster_threshold_dispersion=cluster_dispersion(
                    cluster_counts_map, threshold_groups, kind=ClusterDispersionKind.WITHIN
                ),
                within_cluster_fpr_dispersion=cluster_dispersion(
                    cluster_counts_map,
                    fpr_groups,
                    kind=ClusterDispersionKind.WITHIN,
                    metric_covered_clients=metric_covered_clients,
                    total_clients=len(threshold_client_ids),
                ),
                across_cluster_threshold_dispersion=cluster_dispersion(
                    cluster_counts_map, threshold_groups, kind=ClusterDispersionKind.ACROSS
                ),
                across_cluster_mean_fpr_dispersion=cluster_dispersion(
                    cluster_counts_map,
                    fpr_groups,
                    kind=ClusterDispersionKind.ACROSS,
                    metric_covered_clients=metric_covered_clients,
                    total_clients=len(threshold_client_ids),
                ),
            )
        )

    maps_by_seed: dict[Seed, dict[ClientId, ClusterLabel]] = {}
    for seed_item, mems in memberships_by_seed.items():
        seed_map: dict[ClientId, ClusterLabel] = {}
        for m in mems:
            if m.client_id in seed_map:
                raise ArtifactSchemaViolationError(
                    f"Duplicate client_id '{m.client_id.value}' in seed {seed_item.value}"
                )
            seed_map[m.client_id] = m.cluster_label
        maps_by_seed[seed_item] = seed_map

    sorted_seeds = sorted(memberships_by_seed.keys(), key=lambda s: s.value)
    ref_seed_map = maps_by_seed[sorted_seeds[0]]
    ref_client_set = set(ref_seed_map.keys())

    for seed in sorted_seeds[1:]:
        cur_map = maps_by_seed[seed]
        if set(cur_map.keys()) != ref_client_set:
            raise PopulationAlignmentError(
                f"Incompatible client populations across seeds for ARI computation: "
                f"seed {sorted_seeds[0].value} has {len(ref_client_set)} clients, "
                f"seed {seed.value} has {len(cur_map)} clients"
            )

    ordered_client_ids = sorted(ref_client_set, key=lambda c: c.value)

    aris: list[float] = []
    for index, s1_seed in enumerate(sorted_seeds):
        map1 = maps_by_seed[s1_seed]
        vec1 = np.array([int(map1[c].value) for c in ordered_client_ids])
        for s2_seed in sorted_seeds[index + 1 :]:
            map2 = maps_by_seed[s2_seed]
            vec2 = np.array([int(map2[c].value) for c in ordered_client_ids])
            aris.append(compute_adjusted_rand_index(vec1, vec2))

    expected_pair_count = len(sorted_seeds) * (len(sorted_seeds) - 1) // 2
    if len(aris) != expected_pair_count:
        raise ScientificContractViolationError(
            f"ARI pair count mismatch: expected {expected_pair_count}, got {len(aris)}"
        )

    return ClusterMembershipStabilityResult(
        analysis_label=AnalysisLabel(analysis.label),
        comparison_unit=analysis.comparison_unit,
        seed_summaries=tuple(seed_summaries),
        adjusted_rand_index=tuple(aris),
        mean_adjusted_rand_index=sum(aris) / len(aris) if aris else None,
    )


def _cluster_membership(
    context: AnalysisExecutionContext,
    seed: Seed,
    label: EvaluationLabel,
    features: tuple[str, ...] | None,
) -> tuple[ClientClusterMembership, ...]:
    eval_ctx = context.evaluation_context(label, seed, fingerprint_features=features)
    frame = context.artifacts.thresholds(eval_ctx)

    if (
        ThresholdColumn.CLUSTER_LABEL.value not in frame.columns
        or frame[ThresholdColumn.CLUSTER_LABEL.value].null_count() > 0
    ):
        raise ArtifactMissingError(f"Cluster labels are unavailable for seed {seed.value}")

    return tuple(
        ClientClusterMembership(
            client_id=ClientId(str(client)),
            cluster_label=ClusterLabel(str(int(c_label))),
        )
        for client, c_label in frame.select(
            ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value
        ).iter_rows()
    )
