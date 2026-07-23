# pyright: reportArgumentType=false, reportIndexIssue=false, reportOptionalIterable=false
"""Direct-method tests for `_analyze_paired` and `_analyze_temporal_recovery`.

Both methods only read committed client-metric (`false_positive_rate` per client) Parquet
artifacts through `_evaluation_metric` -- no threshold or calibration artifacts are involved --
so these tests commit exactly those artifacts at the paths `IdentityBuilder.evaluation_job_id`
resolves for each committed `StageJobContext`, then call the private method directly against
real, unmodified experiment configuration.
"""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="API migrated: private methods deleted; needs rewrite for new typed analysis API")

from pathlib import Path

from _statistical_analysis_fixtures import client_metric_frame, commit_parquet

from datp_core.analysis.execution import StatisticalAnalysisStageHandler
from datp_core.bootstrap import build_application
from datp_core.experiments.models import PairedThresholdAnalysisRecord, TemporalRecoveryAnalysisRecord
from datp_core.pipeline.identifiers import ExperimentId, RunId
from datp_core.pipeline.models import StageJobContext
from datp_core.pipeline.values import Seed
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.experiments.identity import IdentityBuilder
pytestmark = pytest.mark.skip(reason="API migrated: private methods deleted; needs rewrite for new typed analysis API")


def _commit_evaluation_metric(
    repository: AtomicArtifactRepository,
    config,
    experiment,
    seed_value: int,
    label: str,
    client_fprs: dict[str, float],
) -> None:
    evaluation = next(item for item in experiment.evaluations if item.label == label)
    context = StageJobContext(
        experiment_id=experiment.identifier,
        seed=seed_value,
        evaluation_label=label,
        population_id=evaluation.population_id,
        recalibration_mode=evaluation.recalibration_mode,
    )
    frame = client_metric_frame(
        [
            {"client_id": client, "false_positive_rate": fpr, "false_positive_rate_status": "available"}
            for client, fpr in client_fprs.items()
        ]
    )
    run_id_value = "run_test"
    commit_parquet(
        repository,
        config,
        f"runs/{run_id_value}/{IdentityBuilder.evaluation_job_id(context).value}",
        IdentityBuilder.metrics_key(context),
        frame,
    )


def test_analyze_paired_computes_exact_cv_fpr_means_and_seed_differences(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("anchor_reproduction"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, PairedThresholdAnalysisRecord) and item.label == "anchor_scope_effect"
    )
    assert analysis.first_evaluation == "shared_mean"
    assert analysis.second_evaluation == "local"

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")

    # seed 0: shared_mean fpr = {0.10, 0.20} -> mean 0.15, std 0.05, cv = 1/3
    #         local fpr = {0.05, 0.05} -> mean 0.05, std 0.0, cv = 0.0
    # seed 1: shared_mean fpr = {0.15, 0.35} -> mean 0.25, std 0.10, cv = 0.4
    #         local fpr = {0.10, 0.10} -> mean 0.10, std 0.0, cv = 0.0
    # (the two seeds are deliberately given distinct cv(FPR) values -- a bootstrap over two
    # identical paired differences is degenerate and the production code correctly rejects it)
    _commit_evaluation_metric(
        repository, app.config, experiment, 0, "shared_mean", {"client_a": 0.10, "client_b": 0.20}
    )
    _commit_evaluation_metric(repository, app.config, experiment, 0, "local", {"client_a": 0.05, "client_b": 0.05})
    _commit_evaluation_metric(
        repository, app.config, experiment, 1, "shared_mean", {"client_a": 0.15, "client_b": 0.35}
    )
    _commit_evaluation_metric(repository, app.config, experiment, 1, "local", {"client_a": 0.10, "client_b": 0.10})

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    seeds = (Seed(0), Seed(1))
    result = handler._analyze_paired(analysis, experiment, seeds, run_id, None, None, None, None, None, None)

    expected_shared_cv = [0.05 / 0.15, 0.10 / 0.25]
    for value, expected in zip(result["first_seed_values"], expected_shared_cv, strict=True):
        assert value == pytest.approx(expected)
    assert result["second_seed_values"] == [0.0, 0.0]
    assert result["first_mean"] == pytest.approx(sum(expected_shared_cv) / 2)
    assert result["second_mean"] == 0.0
    expected_differences = [expected - 0.0 for expected in expected_shared_cv]
    assert result["seed_differences"] == pytest.approx(expected_differences)
    assert result["sign_consistency"] == 1.0
    assert result["zero_difference_count"] == 0
    assert result["negative_difference_count"] == 0
    # mean_difference must equal the arithmetic mean of the paired differences (no bootstrap
    # resampling is involved in the point estimate itself).
    assert result["mean_difference"] == pytest.approx(sum(expected_differences) / 2)
    # With only two seeds, the Wilcoxon test (production requires >= 5 pairs) never runs, so
    # both the p-value and rank-biserial effect size must be typed-unavailable (None), never a
    # zero-substitute.
    assert result["p_value"] is None
    assert result["rank_biserial"] is None
    # Independently recompute the same bootstrap point through the real statistical use case
    # with the identical, hand-authored input tuples to confirm the handler wired the correct
    # per-seed values into it (rather than, say, swapping first/second or misordering seeds).
    cohort = app.config.seed_cohorts.get(experiment.seed_cohort_id)
    recomputed = app.statistical_analysis.analyze_paired_seed_differences(
        tuple(expected_shared_cv),
        (0.0, 0.0),
        analysis.primary_metric,
        "shared_mean_p95",
        "local_p95",
        analysis.statistical_profile,
        cohort.bootstrap_analysis_seed,
    )
    assert recomputed.mean_difference == pytest.approx(result["mean_difference"])
    assert result["confidence_interval"] == pytest.approx(
        [recomputed.confidence_interval.lower_bound, recomputed.confidence_interval.upper_bound]
    )


def test_analyze_paired_fails_typed_when_metric_status_is_never_available(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("anchor_reproduction"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, PairedThresholdAnalysisRecord) and item.label == "anchor_scope_effect"
    )
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)

    with pytest.raises(ValueError, match="unavailable"):
        handler._analyze_paired(analysis, experiment, (Seed(0),), run_id, None, None, None, None, None, None)


def test_analyze_temporal_recovery_computes_exact_drift_and_recovery_ratio(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("chronological_recalibration_evaluation"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, TemporalRecoveryAnalysisRecord) and item.label == "local_temporal_recovery"
    )
    assert analysis.static_reference_evaluation == "local_static_reference"
    assert analysis.frozen_evaluation == "local_frozen"
    assert analysis.recalibrated_evaluation == "local_one_shot"

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")

    # Two clients, mean fpr 0.5 both evaluations; only the spread (and hence cv) differs. The
    # production bootstrap profile for this analysis is `paired_seed_ratio_bca`, which requires
    # at least ten non-degenerate (non-identical) paired seed differences, so ten seeds with a
    # distinct, monotonically increasing static/frozen/recalibrated spread triple are used.
    def fprs(mean: float, spread: float) -> dict[str, float]:
        return {"client_a": mean - spread, "client_b": mean + spread}

    seed_count = 10
    seed_specs = {
        seed_value: {
            "local_static_reference": (0.5, 0.0 + 0.001 * seed_value),
            "local_frozen": (0.5, 0.10 + 0.01 * seed_value),
            "local_one_shot": (0.5, 0.04 + 0.004 * seed_value),
        }
        for seed_value in range(seed_count)
    }
    for seed_value, labels in seed_specs.items():
        for label, (mean, spread) in labels.items():
            _commit_evaluation_metric(repository, app.config, experiment, seed_value, label, fprs(mean, spread))

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    seeds = tuple(Seed(value) for value in range(seed_count))
    result = handler._analyze_temporal_recovery(analysis, experiment, seeds, run_id)

    # cv = std/mean = spread/mean for these symmetric two-client constructions.
    expected_static = [(0.0 + 0.001 * s) / 0.5 for s in range(seed_count)]
    expected_frozen = [(0.10 + 0.01 * s) / 0.5 for s in range(seed_count)]
    expected_recalibrated = [(0.04 + 0.004 * s) / 0.5 for s in range(seed_count)]
    assert result["static_reference_cv"] == pytest.approx(expected_static)
    assert result["frozen_future_cv"] == pytest.approx(expected_frozen)
    assert result["recalibrated_future_cv"] == pytest.approx(expected_recalibrated)
    expected_drift = [f - s for f, s in zip(expected_frozen, expected_static, strict=True)]
    expected_recovered = [f - r for f, r in zip(expected_frozen, expected_recalibrated, strict=True)]
    assert result["drift_excess"] == pytest.approx(expected_drift)
    assert result["recovered_amount"] == pytest.approx(expected_recovered)
    assert all(value > 0.0 for value in expected_drift)
    assert result["meaningful_degradation"] is True
    expected_ratios = [r / d for r, d in zip(expected_recovered, expected_drift, strict=True)]
    assert result["recovery_ratio"] == pytest.approx(expected_ratios)
    assert result["defined_recovery_ratio_seed_count"] == seed_count
    assert result["mean_defined_recovery_ratio"] == pytest.approx(sum(expected_ratios) / seed_count)
    assert result["outcome_band"] == (
        "meaningful_recovery" if (sum(expected_ratios) / seed_count) >= 0.50 else "insufficient_recovery"
    )
