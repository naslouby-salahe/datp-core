"""Cluster membership extraction, stability, and population alignment."""

from __future__ import annotations

from collections.abc import Mapping as _Mapping

import polars as pl

from datp_core.analysis.clustering.contracts import (
    ClientClusterMembership,
    ClusterAblationObservation,
    ClusterAblationStabilityResult,
    ClusterMembershipStabilityResult,
    ClusterSize,
    ClusterStabilityAnalysisResult,
    ClusterStabilitySeedSummary,
)
from datp_core.analysis.clustering.dispersion import (
    cluster_dispersion,
    compute_adjusted_rand_index,
)
from datp_core.analysis.contracts import PairedAnalysisCell
from datp_core.analysis.enums import ClusterDispersionKind
from datp_core.analysis.errors import (
    ArtifactMissingError,
    ArtifactSchemaViolationError,
    InvalidAnalysisConfigurationError,
    PopulationAlignmentError,
    ScientificContractViolationError,
)
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.artifacts.schemas.columns import MetricColumn, ThresholdColumn
from datp_core.core.identifiers import AnalysisLabel, ClientId, ClusterLabel, EvaluationLabel
from datp_core.core.seeding import Seed
from datp_core.evaluation.enums import MetricStatus
from datp_core.experiments import ClusterStabilityAnalysisRecord, ValueSweepRecord
from datp_core.thresholding.policies import ClusterPolicy


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
        raise InvalidAnalysisConfigurationError("Reference evaluation is required for cluster ablation analysis")

    source = context.evaluation(source_label)
    sweep_name: str | None = None
    if source.overrides is not None:
        raw = source.overrides.get("fingerprint_features")
        if isinstance(raw, _Mapping):
            val = raw.get("from_sweep")
            if isinstance(val, str):
                sweep_name = val

    subsets = tuple(
        value
        for sweep in context.experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value)
    )
    if not subsets:
        raise InvalidAnalysisConfigurationError("Cluster ablation analysis has no configured fingerprint subsets")

    cid_col = ThresholdColumn.CLIENT_ID.value
    cl_col = ThresholdColumn.CLUSTER_LABEL.value

    observations: list[ClusterAblationObservation] = []
    for seed in context.seeds:
        ref_ctx = context.evaluation_context(ref_label, seed, fingerprint_features=None)
        ref_frame = context.artifacts.thresholds(ref_ctx)

        if cl_col not in ref_frame.columns or ref_frame[cl_col].null_count() > 0:
            raise ArtifactMissingError(f"Cluster labels are unavailable for reference seed {seed.value}")

        ref_aligned = ref_frame.select(cid_col, cl_col).sort(cid_col)
        ref_labels_np = ref_aligned[cl_col].cast(pl.Int32).to_numpy()

        for subset in subsets:
            abl_ctx = context.evaluation_context(source_label, seed, fingerprint_features=subset)
            abl_frame = context.artifacts.thresholds(abl_ctx)

            if cl_col not in abl_frame.columns or abl_frame[cl_col].null_count() > 0:
                raise ArtifactMissingError(f"Cluster labels are unavailable for ablated seed {seed.value}")

            abl_aligned = abl_frame.select(cid_col, cl_col).sort(cid_col)

            # Verify client populations match
            if ref_aligned.height != abl_aligned.height:
                raise PopulationAlignmentError("Cluster ablation membership has an incompatible client population")
            if not ref_aligned[cid_col].series_equal(abl_aligned[cid_col]):  # type: ignore[reportAttributeAccessIssue]
                raise PopulationAlignmentError("Cluster ablation membership has an incompatible client population")

            observations.append(
                ClusterAblationObservation(
                    seed=seed,
                    fingerprint_features=subset,
                    adjusted_rand_index=compute_adjusted_rand_index(
                        ref_labels_np,
                        abl_aligned[cl_col].cast(pl.Int32).to_numpy(),
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
    policy = context.threshold_policies.get(policy_id)

    if not isinstance(policy, ClusterPolicy):
        raise InvalidAnalysisConfigurationError(
            f"Cluster stability requires a cluster threshold policy, got '{policy_id.value}'"
        )
    expected_cluster_count = policy.cluster_count
    expected_labels = tuple(ClusterLabel(str(i)) for i in range(expected_cluster_count))
    expected_set = set(expected_labels)

    seed_summaries: list[ClusterStabilitySeedSummary] = []
    membership_frames: dict[Seed, pl.DataFrame] = {}

    cid_col = ThresholdColumn.CLIENT_ID.value
    cl_col = ThresholdColumn.CLUSTER_LABEL.value
    thr_col = ThresholdColumn.THRESHOLD.value
    fpr_col = MetricColumn.FALSE_POSITIVE_RATE.value
    fpr_status_col = MetricColumn.FALSE_POSITIVE_RATE_STATUS.value

    for seed in context.seeds:
        eval_ctx = context.evaluation_context(source_label, seed)
        threshold_frame = context.artifacts.thresholds(eval_ctx)

        if cl_col not in threshold_frame.columns:
            raise ArtifactMissingError(f"Cluster labels are unavailable for seed {seed.value}")
        if threshold_frame[cl_col].null_count() > 0:
            raise ArtifactSchemaViolationError(f"Cluster labels contain nulls for seed {seed.value}")

        # Validate unique client_ids
        if threshold_frame[cid_col].is_duplicated().any():
            raise ArtifactSchemaViolationError(f"Duplicate client_id in threshold frame for seed {seed.value}")

        # Validate cluster labels are within the configured range
        unique_labels = threshold_frame[cl_col].unique()
        for lbl_val in unique_labels:
            label_str = str(int(lbl_val))
            if ClusterLabel(label_str) not in expected_set:
                raise ScientificContractViolationError(
                    f"Cluster label '{label_str}' is outside configured range for seed {seed.value}"
                )

        # Store sorted membership frame for ARI across seeds
        membership_frame = threshold_frame.select(cid_col, cl_col).sort(cid_col)
        membership_frames[seed] = membership_frame

        # Build memberships tuple for the seed summary
        # Domain object construction requires Python iteration from Polars
        memberships = tuple(
            ClientClusterMembership(
                client_id=ClientId(str(row.client_id)),  # type: ignore[reportAttributeAccessIssue]
                cluster_label=ClusterLabel(str(int(row.cluster_label))),  # type: ignore[reportAttributeAccessIssue]
            )
            for row in membership_frame.iter_rows(named=True)
        )

        # Cluster sizes via group_by
        sizes_df = threshold_frame.group_by(cl_col).agg(pl.len().alias("client_count"))
        counts_map: dict[ClusterLabel, int] = {lbl: 0 for lbl in expected_labels}
        for row in sizes_df.iter_rows(named=True):
            counts_map[ClusterLabel(str(int(row.cluster_label)))] = row.client_count  # type: ignore[reportAttributeAccessIssue]

        cluster_sizes_tuple = tuple(
            ClusterSize(cluster_label=lbl, client_count=counts_map[lbl]) for lbl in expected_labels
        )

        # Singleton / empty flags from the group-by result
        singleton_cluster_flag = sizes_df.filter(pl.col("client_count") == 1).height > 0
        populated_count = sizes_df.height
        empty_cluster_flag = populated_count < expected_cluster_count

        # Build threshold dispersion frame (all clients have a value)
        threshold_value_frame = threshold_frame.select(
            pl.col(cl_col).cast(pl.Utf8).alias("cluster_label"),
            pl.col(thr_col).alias("value"),
        )

        # Load and merge metric frame
        metric_frame = context.artifacts.client_metrics(eval_ctx)

        if metric_frame[cid_col].is_duplicated().any():
            raise ArtifactSchemaViolationError(f"Duplicate client_id in metric frame for seed {seed.value}")

        unknown_metric_clients = metric_frame.select(cid_col).filter(~pl.col(cid_col).is_in(threshold_frame[cid_col]))
        if unknown_metric_clients.height > 0:
            raise PopulationAlignmentError(
                f"Metric frame references clients outside the threshold population "
                f"for seed {seed.value}: "
                # Polars-to-Python bridge: error message requires Python list
                f"{unknown_metric_clients[cid_col].sort().to_list()}"
            )

        joined = threshold_frame.select(cid_col, cl_col).join(
            metric_frame.select(cid_col, fpr_col, fpr_status_col),
            on=cid_col,
            how="left",
        )
        if joined.height != threshold_frame.height:
            raise PopulationAlignmentError(f"Threshold/metric join changed client population for seed {seed.value}")

        # Count clients with any FPR status
        metric_covered = joined.filter(pl.col(fpr_status_col).is_not_null()).height

        # Build FPR dispersion frame (nullable — clients without AVAILABLE status
        # get a null value)
        fpr_value_frame = joined.select(
            pl.col(cl_col).cast(pl.Utf8).alias("cluster_label"),
            pl.when(pl.col(fpr_status_col) == MetricStatus.AVAILABLE.value)
            .then(pl.col(fpr_col))
            .otherwise(None)
            .alias("value"),
        )

        # Validate non-finite FPR values
        has_non_finite = (
            fpr_value_frame.filter(pl.col("value").is_not_null() & (~pl.col("value").is_finite())).height > 0
        )
        if has_non_finite:
            raise ArtifactSchemaViolationError(
                f"Non-finite false-positive-rate in cluster stability for seed {seed.value}"
            )

        seed_summaries.append(
            ClusterStabilitySeedSummary(
                seed=seed,
                cluster_memberships=memberships,
                cluster_sizes=cluster_sizes_tuple,
                singleton_cluster_flag=singleton_cluster_flag,
                empty_cluster_flag=empty_cluster_flag,
                within_cluster_threshold_dispersion=cluster_dispersion(
                    threshold_value_frame,
                    kind=ClusterDispersionKind.WITHIN,
                    expected_cluster_count=expected_cluster_count,
                ),
                within_cluster_fpr_dispersion=cluster_dispersion(
                    fpr_value_frame,
                    kind=ClusterDispersionKind.WITHIN,
                    expected_cluster_count=expected_cluster_count,
                    total_client_count=threshold_frame.height,
                    metric_covered_client_count=metric_covered,
                ),
                across_cluster_threshold_dispersion=cluster_dispersion(
                    threshold_value_frame,
                    kind=ClusterDispersionKind.ACROSS,
                    expected_cluster_count=expected_cluster_count,
                ),
                across_cluster_mean_fpr_dispersion=cluster_dispersion(
                    fpr_value_frame,
                    kind=ClusterDispersionKind.ACROSS,
                    expected_cluster_count=expected_cluster_count,
                    total_client_count=threshold_frame.height,
                    metric_covered_client_count=metric_covered,
                ),
            )
        )

    # -- ARI across all seed pairs -------------------------------------------
    sorted_seeds = sorted(membership_frames.keys(), key=lambda s: s.value)
    ref_frame = membership_frames[sorted_seeds[0]]
    ref_client_ids = ref_frame[cid_col]

    for seed in sorted_seeds[1:]:
        cur_frame = membership_frames[seed]
        if cur_frame.height != ref_frame.height:
            raise PopulationAlignmentError(
                f"Incompatible client populations across seeds for ARI "
                f"computation: seed {sorted_seeds[0].value} has "
                f"{ref_frame.height} clients, seed {seed.value} has "
                f"{cur_frame.height} clients"
            )
        if not cur_frame[cid_col].series_equal(ref_client_ids):  # type: ignore[reportAttributeAccessIssue]
            raise PopulationAlignmentError("Incompatible client populations across seeds for ARI computation")

    aris: list[float] = []
    for index, s1_seed in enumerate(sorted_seeds):
        vec1 = membership_frames[s1_seed][cl_col].cast(pl.Int32).to_numpy()
        for s2_seed in sorted_seeds[index + 1 :]:
            vec2 = membership_frames[s2_seed][cl_col].cast(pl.Int32).to_numpy()
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

    # Domain object construction requires Python iteration from Polars
    return tuple(
        ClientClusterMembership(
            client_id=ClientId(str(row.client_id)),  # type: ignore[reportAttributeAccessIssue]
            cluster_label=ClusterLabel(str(int(row.cluster_label))),  # type: ignore[reportAttributeAccessIssue]
        )
        for row in frame.select(ThresholdColumn.CLIENT_ID.value, ThresholdColumn.CLUSTER_LABEL.value).iter_rows(
            named=True
        )
    )
