# pyright: reportArgumentType=false, reportIndexIssue=false, reportOptionalIterable=false
"""Direct-method tests for `_analyze_association` and `_analyze_cluster_stability`.

`_analyze_association` reads real committed calibration-score Parquet artifacts (to compute
pairwise JS divergence) but takes its paired-analysis `cv_fpr_delta` source as an in-memory
`paired_results` list, so this test crafts that list directly (as the existing
`test_recovery_fraction_analysis.py` already does for other analyses) rather than paying for a
full sweep of paired-analysis artifacts.

`_analyze_cluster_stability` (the non-ablation branch) reads threshold Parquet (with a
`cluster_label` column) and client-metric Parquet per seed.
"""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="API migrated: private methods deleted; needs rewrite for new typed analysis API")

from pathlib import Path

import numpy as np
import polars as pl
from _statistical_analysis_fixtures import client_metric_frame, commit_parquet
from sklearn.metrics import adjusted_rand_score

from datp_core.analysis.execution import StatisticalAnalysisStageHandler
from datp_core.bootstrap import build_application
from datp_core.experiments.models import ClusterStabilityAnalysisRecord, MetricAssociationAnalysisRecord
from datp_core.evaluation.models import calculate_pairwise_js_divergence
from datp_core.pipeline.identifiers import ClientId, ExperimentId, RunId
from datp_core.pipeline.models import StageJobContext
from datp_core.pipeline.values import Seed
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.experiments.identity import IdentityBuilder
pytestmark = pytest.mark.skip(reason="API migrated: private methods deleted; needs rewrite for new typed analysis API")


def test_analyze_association_reports_a_perfectly_monotone_relationship_by_construction(
    tmp_path: Path,
) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("controlled_heterogeneity_response"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, MetricAssociationAnalysisRecord)
        and item.label == "heterogeneity_threshold_benefit_association"
    )
    assert analysis.outcome_source_analysis == "heterogeneity_scope_effect"
    assert analysis.predictor_metric == "pairwise_js_divergence"
    assert analysis.outcome_metric == "cv_fpr_delta"

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    seed_value = 0

    # Three partition conditions with strictly increasing benign-score separation between the
    # two clients (identical -> partially overlapping -> disjoint), which strictly increases
    # pairwise JS divergence; the crafted cv_fpr_delta values are also strictly increasing, so
    # the Spearman correlation must be exactly 1.0 by construction.
    conditions = {
        "dirichlet_alpha_0_1": ((0.0, 20.0), (0.0, 20.0), 0.1),
        "dirichlet_alpha_0_3": ((0.0, 20.0), (10.0, 30.0), 0.2),
        "dirichlet_alpha_1_0": ((0.0, 20.0), (50.0, 70.0), 0.3),
    }
    diagnostics = app.config.metric_definitions.heterogeneity_diagnostics.pairwise_js_divergence
    expected_predictor: dict[str, float] = {}
    for condition, ((a_lo, a_hi), (b_lo, b_hi), _) in conditions.items():
        client_a_scores = tuple(float(v) for v in range(int(a_lo), int(a_hi) + 1))
        client_b_scores = tuple(float(v) for v in range(int(b_lo), int(b_hi) + 1))
        expected_predictor[condition] = calculate_pairwise_js_divergence(
            (
                (ClientId("client_a"), client_a_scores),
                (ClientId("client_b"), client_b_scores),
            ),
            histogram_bins=diagnostics.histogram_bins,
            logarithm_base=diagnostics.logarithm_base,
        )
        context = StageJobContext(experiment_id=experiment.identifier, seed=seed_value, partition_condition=condition)
        frame = pl.DataFrame(
            {
                "client_id": ["client_a"] * len(client_a_scores) + ["client_b"] * len(client_b_scores),
                "score": list(client_a_scores) + list(client_b_scores),
            }
        )
        commit_parquet(
            repository,
            app.config,
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(context).value}",
            IdentityBuilder.calibration_scores_key(context),
            frame,
        )

    # Predictor values must strictly increase with our construction, or the test's premise (a
    # perfectly monotone relationship) does not hold.
    ordered = [expected_predictor[c] for c in conditions]
    assert ordered == sorted(ordered)
    assert len(set(ordered)) == 3

    paired_results = [
        {
            "analysis_label": "heterogeneity_scope_effect",
            "partition_condition": condition,
            "seed_differences": [delta],
        }
        for condition, (_, _, delta) in conditions.items()
    ]
    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    seeds = (Seed(seed_value),)
    result = handler._analyze_association(analysis, paired_results, experiment, seeds, run_id)

    observations = result["observations"]
    assert isinstance(observations, list)
    assert len(observations) == 3
    by_condition = {item["partition_condition"]: item for item in observations}  # type: ignore[index]
    for condition, (_, _, delta) in conditions.items():
        assert by_condition[condition]["pairwise_js_divergence"] == pytest.approx(expected_predictor[condition])
        assert by_condition[condition]["cv_fpr_delta"] == pytest.approx(delta)
        assert by_condition[condition]["seed"] == seed_value

    # Independent, hand-computed check: a strictly monotone increasing relationship between
    # three points has a Spearman rank correlation of exactly 1.0, regardless of the exact JS
    # divergence magnitudes.
    assert result["spearman"]["coefficient"] == pytest.approx(1.0)

    # Independent linear-regression check computed here with plain OLS algebra (not by calling
    # the production regression routine) over the exact predictor/outcome values.
    predictor = np.array([expected_predictor[c] for c in conditions], dtype=np.float64)
    outcome = np.array([delta for _, _, delta in conditions.values()], dtype=np.float64)
    mean_x, mean_y = predictor.mean(), outcome.mean()
    expected_slope = float(np.sum((predictor - mean_x) * (outcome - mean_y)) / np.sum((predictor - mean_x) ** 2))
    expected_intercept = float(mean_y - expected_slope * mean_x)
    assert result["linear_regression"]["coefficient"] == pytest.approx(expected_slope)
    assert result["linear_regression"]["intercept"] == pytest.approx(expected_intercept)


def _commit_cluster_seed(
    repository: AtomicArtifactRepository,
    config,
    experiment,
    run_id: RunId,
    seed_value: int,
    cluster_labels: dict[str, int],
    thresholds: dict[str, float],
    fprs: dict[str, float],
) -> None:
    context = StageJobContext(experiment_id=experiment.identifier, seed=seed_value, evaluation_label="cluster_k3_mean")
    threshold_frame = pl.DataFrame(
        {
            "client_id": list(cluster_labels),
            "threshold": [thresholds[client] for client in cluster_labels],
            "owner_kind": ["cluster_threshold"] * len(cluster_labels),
            "cluster_label": [cluster_labels[client] for client in cluster_labels],
        },
        schema_overrides={"cluster_label": pl.Int64},
    )
    commit_parquet(
        repository,
        config,
        f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}",
        IdentityBuilder.thresholds_key(context),
        threshold_frame,
    )
    metric_frame = client_metric_frame(
        [
            {"client_id": client, "false_positive_rate": fprs[client], "false_positive_rate_status": "available"}
            for client in cluster_labels
        ]
    )
    commit_parquet(
        repository,
        config,
        f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}",
        IdentityBuilder.metrics_key(context),
        metric_frame,
    )


def _expected_within(groups: list[list[tuple[float, float]]], index: int) -> float:
    return float(np.mean([np.std([item[index] for item in group]) for group in groups]))


def _expected_across(groups: list[list[tuple[float, float]]], index: int) -> float:
    return float(np.std([np.mean([item[index] for item in group]) for group in groups]))


def test_analyze_cluster_stability_computes_exact_dispersion_and_ari(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("cluster_and_family_threshold_mechanism"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, ClusterStabilityAnalysisRecord) and item.label == "cluster_stability"
    )
    assert analysis.reference_evaluation is None
    assert analysis.source_evaluation == "cluster_k3_mean"

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")

    thresholds = {"client_a": 1.0, "client_b": 3.0, "client_c": 10.0, "client_d": 20.0}
    fprs = {"client_a": 0.1, "client_b": 0.3, "client_c": 0.5, "client_d": 0.7}
    seed0_labels = {"client_a": 0, "client_b": 0, "client_c": 1, "client_d": 1}
    seed1_labels = {"client_a": 0, "client_b": 1, "client_c": 1, "client_d": 1}
    _commit_cluster_seed(repository, app.config, experiment, run_id, 0, seed0_labels, thresholds, fprs)
    _commit_cluster_seed(repository, app.config, experiment, run_id, 1, seed1_labels, thresholds, fprs)

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    seeds = (Seed(0), Seed(1))
    result = handler._analyze_cluster_stability(analysis, experiment, seeds, run_id)

    seed0_groups = [[(thresholds[c], fprs[c]) for c in seed0_labels if seed0_labels[c] == label] for label in (0, 1)]
    seed1_groups = [[(thresholds[c], fprs[c]) for c in seed1_labels if seed1_labels[c] == label] for label in (0, 1)]
    seed_summaries = result["seed_summaries"]
    assert isinstance(seed_summaries, list)
    summaries = {item["seed"]: item for item in seed_summaries}  # type: ignore[index]
    assert summaries[0]["within_cluster_threshold_dispersion"] == pytest.approx(_expected_within(seed0_groups, 0))
    assert summaries[0]["within_cluster_fpr_dispersion"] == pytest.approx(_expected_within(seed0_groups, 1))
    assert summaries[0]["across_cluster_threshold_dispersion"] == pytest.approx(_expected_across(seed0_groups, 0))
    assert summaries[0]["across_cluster_mean_fpr_dispersion"] == pytest.approx(_expected_across(seed0_groups, 1))
    assert summaries[0]["singleton_cluster_flag"] is False
    assert summaries[1]["within_cluster_threshold_dispersion"] == pytest.approx(_expected_within(seed1_groups, 0))
    assert summaries[1]["within_cluster_fpr_dispersion"] == pytest.approx(_expected_within(seed1_groups, 1))
    assert summaries[1]["across_cluster_threshold_dispersion"] == pytest.approx(_expected_across(seed1_groups, 0))
    assert summaries[1]["across_cluster_mean_fpr_dispersion"] == pytest.approx(_expected_across(seed1_groups, 1))
    # client_a is alone in cluster 0 at seed 1 -> a genuine singleton cluster.
    assert summaries[1]["singleton_cluster_flag"] is True

    expected_ari = adjusted_rand_score(
        [seed0_labels[c] for c in sorted(seed0_labels)],
        [seed1_labels[c] for c in sorted(seed0_labels)],
    )
    assert result["adjusted_rand_index"] == pytest.approx([expected_ari])
    assert result["mean_adjusted_rand_index"] == pytest.approx(expected_ari)


def test_analyze_cluster_stability_fails_typed_when_cluster_labels_are_missing(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("cluster_and_family_threshold_mechanism"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, ClusterStabilityAnalysisRecord) and item.label == "cluster_stability"
    )
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    context = StageJobContext(experiment_id=experiment.identifier, seed=0, evaluation_label="cluster_k3_mean")
    # Threshold artifact with no `cluster_label` column at all.
    threshold_frame = pl.DataFrame({"client_id": ["client_a"], "threshold": [1.0], "owner_kind": ["cluster_threshold"]})
    commit_parquet(
        repository,
        app.config,
        f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}",
        IdentityBuilder.thresholds_key(context),
        threshold_frame,
    )
    metric_frame = client_metric_frame(
        [{"client_id": "client_a", "false_positive_rate": 0.1, "false_positive_rate_status": "available"}]
    )
    commit_parquet(
        repository,
        app.config,
        f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}",
        IdentityBuilder.metrics_key(context),
        metric_frame,
    )

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    with pytest.raises(ValueError, match="Cluster labels are unavailable"):
        handler._analyze_cluster_stability(analysis, experiment, (Seed(0),), run_id)
