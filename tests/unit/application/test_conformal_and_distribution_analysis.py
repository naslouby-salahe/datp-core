# pyright: reportArgumentType=false, reportIndexIssue=false, reportOptionalIterable=false
"""Direct-method tests for `_analyze_conformal_coverage`, `_analyze_distribution_mechanism`, and
`_analyze_locked_client_distribution`.

All three read real committed threshold/client-metric/(calibration or test-score) Parquet
artifacts at the exact `IdentityBuilder` paths for a given `StageJobContext`, then are called
directly against real, unmodified experiment configuration.
"""

from __future__ import annotations

from pathlib import Path

import attrs
import polars as pl
import pytest
from _statistical_analysis_fixtures import client_metric_frame, commit_parquet

from datp_core.application.analysis_stages import StatisticalAnalysisStageHandler
from datp_core.application.scoring_support import score_context
from datp_core.composition.root import build_application
from datp_core.domain.catalogue import (
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    LockedClientDistributionAnalysisRecord,
)
from datp_core.domain.identifiers import ExperimentId, RunId
from datp_core.domain.outcomes import StageJobContext
from datp_core.domain.values import Seed
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository
from datp_core.planning.identity import IdentityBuilder


def test_analyze_conformal_coverage_computes_exact_marginal_and_macro_coverage(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("conformal_local_threshold_coverage"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, ConformalCoverageAnalysisRecord) and item.label == "conformal_coverage"
    )
    assert analysis.source_evaluation == "conformal_local"
    assert analysis.target_coverage == pytest.approx(0.95)

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    evaluation = next(item for item in experiment.evaluations if item.label == "conformal_local")

    # seed 0: client_a TN=90/FP=10 (coverage 0.90), client_b TN=100/FP=0 (coverage 1.0)
    # seed 1: client_a TN=95/FP=5 (coverage 0.95), client_b TN=100/FP=0 (coverage 1.0)
    seed_confusion = {
        0: {"client_a": (90, 10), "client_b": (100, 0)},
        1: {"client_a": (95, 5), "client_b": (100, 0)},
    }
    for seed_value, per_client in seed_confusion.items():
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed_value,
            evaluation_label="conformal_local",
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold_frame = pl.DataFrame(
            {
                "client_id": list(per_client),
                "threshold": [0.5 for _ in per_client],
                "owner_kind": ["conformal_local_threshold" for _ in per_client],
                "finite_sample_rank": [96 for _ in per_client],
                "attainability_status": ["attainable" for _ in per_client],
            },
            schema_overrides={"finite_sample_rank": pl.Int64},
        )
        commit_parquet(
            repository,
            app.config,
            f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}",
            IdentityBuilder.thresholds_key(context),
            threshold_frame,
        )
        metric_rows = []
        for client, (tn, fp) in per_client.items():
            total = tn + fp
            metric_rows.append(
                {
                    "client_id": client,
                    "true_negatives": tn,
                    "false_positives": fp,
                    "false_positive_rate": fp / total,
                    "false_positive_rate_status": "available",
                }
            )
        commit_parquet(
            repository,
            app.config,
            f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}",
            IdentityBuilder.metrics_key(context),
            client_metric_frame(metric_rows),
        )
        calibration_context = score_context(context)
        calibration_frame = pl.DataFrame(
            {
                "client_id": [client for client in per_client for _ in range(100)],
                "score": [float(index) for _ in per_client for index in range(100)],
            }
        )
        commit_parquet(
            repository,
            app.config,
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(calibration_context).value}",
            IdentityBuilder.calibration_scores_key(calibration_context),
            calibration_frame,
        )

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    seeds = (Seed(0), Seed(1))
    result = handler._analyze_conformal_coverage(analysis, experiment, seeds, run_id)

    # weighted (marginal) coverage = sum(tn) / sum(tn + fp) across both seeds and clients.
    total_tn = 90 + 100 + 95 + 100
    total_n = 200 + 200
    assert result["achieved_marginal_coverage"] == pytest.approx(total_tn / total_n)
    macro_coverages = [0.90, 1.0, 0.95, 1.0]
    assert result["achieved_macro_client_coverage"] == pytest.approx(sum(macro_coverages) / len(macro_coverages))
    assert result["absolute_coverage_error"] == pytest.approx(abs(total_tn / total_n - 0.95))
    assert result["finite_sample_rank"] == [{"client_a": 96, "client_b": 96}, {"client_a": 96, "client_b": 96}]
    assert result["attainability_status"] == [
        {"client_a": "attainable", "client_b": "attainable"},
        {"client_a": "attainable", "client_b": "attainable"},
    ]


def test_analyze_conformal_coverage_fails_typed_when_target_disagrees_with_policy(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("conformal_local_threshold_coverage"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, ConformalCoverageAnalysisRecord) and item.label == "conformal_coverage"
    )
    bad_analysis = attrs.evolve(analysis, target_coverage=0.42)
    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    with pytest.raises(ValueError, match="target disagrees"):
        handler._analyze_conformal_coverage(bad_analysis, experiment, (Seed(0),), RunId("run_test"))


_ENNIO = "Ennio_Doorbell"
_OTHER = "client_b"
_TEST_SCORES = {
    _ENNIO: {"benign": [1.0, 3.0], "attack": [10.0, 12.0]},
    _OTHER: {"benign": [2.0, 4.0], "attack": [20.0, 22.0]},
}
_THRESHOLDS = {"shared_mean": {_ENNIO: 5.0, _OTHER: 5.0}, "local": {_ENNIO: 2.0, _OTHER: 3.0}}
_THRESHOLDS["cluster_k3_mean"] = {_ENNIO: 6.0, _OTHER: 6.0}
_METRICS = {
    "shared_mean": {
        _ENNIO: {"false_positive_rate": 0.10, "true_positive_rate": 0.90},
        _OTHER: {"false_positive_rate": 0.20, "true_positive_rate": 0.80},
    },
    "local": {
        _ENNIO: {"false_positive_rate": 0.05, "true_positive_rate": 0.95},
        _OTHER: {"false_positive_rate": 0.15, "true_positive_rate": 0.85},
    },
    "cluster_k3_mean": {
        _ENNIO: {"false_positive_rate": 0.12, "true_positive_rate": 0.88},
        _OTHER: {"false_positive_rate": 0.22, "true_positive_rate": 0.78},
    },
}


def _commit_distribution_fixture(repository: AtomicArtifactRepository, config, experiment, run_id: RunId) -> None:
    seed_value = 0
    for label in ("shared_mean", "local", "cluster_k3_mean"):
        evaluation = next(item for item in experiment.evaluations if item.label == label)
        context = StageJobContext(
            experiment_id=experiment.identifier,
            seed=seed_value,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
        )
        threshold_frame = pl.DataFrame(
            {
                "client_id": [_ENNIO, _OTHER],
                "threshold": [_THRESHOLDS[label][_ENNIO], _THRESHOLDS[label][_OTHER]],
                "owner_kind": ["shared_mean", "shared_mean"],
            }
        )
        commit_parquet(
            repository,
            config,
            f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(context).value}",
            IdentityBuilder.thresholds_key(context),
            threshold_frame,
        )
        metric_rows = [
            {
                "client_id": client,
                "false_positive_rate": _METRICS[label][client]["false_positive_rate"],
                "false_positive_rate_status": "available",
                "true_positive_rate": _METRICS[label][client]["true_positive_rate"],
                "true_positive_rate_status": "available",
                "balanced_accuracy": 0.5
                * (
                    _METRICS[label][client]["true_positive_rate"] + 1.0 - _METRICS[label][client]["false_positive_rate"]
                ),
                "balanced_accuracy_status": "available",
                "macro_f1": 0.8,
                "macro_f1_status": "available",
            }
            for client in (_ENNIO, _OTHER)
        ]
        commit_parquet(
            repository,
            config,
            f"runs/{run_id.value}/{IdentityBuilder.evaluation_job_id(context).value}",
            IdentityBuilder.metrics_key(context),
            client_metric_frame(metric_rows),
        )

    # Test scores are identical across evaluations for a given seed (they do not depend on the
    # threshold policy), so `score_context` collapses every evaluation label's context to the
    # same relative path -- commit it exactly once here rather than once per label.
    final_context = StageJobContext(experiment_id=experiment.identifier, seed=seed_value)
    test_score_context = score_context(final_context)
    rows = [
        {"client_id": client, "score": score, "label": 0}
        for client, scores in _TEST_SCORES.items()
        for score in scores["benign"]
    ] + [
        {"client_id": client, "score": score, "label": 1}
        for client, scores in _TEST_SCORES.items()
        for score in scores["attack"]
    ]
    test_frame = pl.DataFrame(rows, schema_overrides={"label": pl.Int64})
    commit_parquet(
        repository,
        config,
        f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(test_score_context).value}",
        IdentityBuilder.test_scores_key(test_score_context),
        test_frame,
    )


def test_analyze_distribution_mechanism_reports_exact_cdfs_and_threshold_positions(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("confirmatory_threshold_scope_effect"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, DistributionMechanismAnalysisRecord) and item.label == "client_score_distribution_mechanism"
    )
    assert analysis.field_formulas is None

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    _commit_distribution_fixture(repository, app.config, experiment, run_id)

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    result = handler._analyze_distribution_mechanism(analysis, experiment, (Seed(0),), run_id)

    seed_result = result["seed_results"][0]
    shared_mean = seed_result["evaluations"]["shared_mean"][_ENNIO]
    # Ennio's benign scores are [1.0, 3.0]; empirical CDF assigns 1/2 then 2/2.
    assert shared_mean["per_client_benign_score_cdf"] == [
        {"score": 1.0, "cumulative_probability": 0.5},
        {"score": 3.0, "cumulative_probability": 1.0},
    ]
    assert shared_mean["per_client_attack_score_cdf"] == [
        {"score": 10.0, "cumulative_probability": 0.5},
        {"score": 12.0, "cumulative_probability": 1.0},
    ]
    # threshold 5.0 is above both benign scores (1.0, 3.0) and below both attack scores (10, 12).
    assert shared_mean["per_client_threshold_position"] == {
        "threshold": 5.0,
        "benign_cdf": 1.0,
        "attack_cdf": 0.0,
    }
    local = seed_result["evaluations"]["local"][_ENNIO]
    # threshold 2.0 is above only the first benign score (1.0 <= 2.0 < 3.0).
    assert local["per_client_threshold_position"] == {"threshold": 2.0, "benign_cdf": 0.5, "attack_cdf": 0.0}
    assert local["false_positive_rate"] == pytest.approx(0.05)
    assert local["true_positive_rate"] == pytest.approx(0.95)

    other_local = seed_result["evaluations"]["local"][_OTHER]
    # client_b's benign scores are [2.0, 4.0]; threshold 3.0 covers only the first (2.0 <= 3.0).
    assert other_local["per_client_threshold_position"] == {"threshold": 3.0, "benign_cdf": 0.5, "attack_cdf": 0.0}


def test_analyze_distribution_mechanism_computes_exact_threshold_shift_tradeoff(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("confirmatory_threshold_scope_effect"))
    analysis = next(
        item
        for item in experiment.analyses
        if isinstance(item, DistributionMechanismAnalysisRecord) and item.label == "threshold_shift_detection_tradeoff"
    )
    assert analysis.field_formulas is not None
    assert analysis.source_evaluations[:2] == ("shared_mean", "local")

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    _commit_distribution_fixture(repository, app.config, experiment, run_id)

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    result = handler._analyze_distribution_mechanism(analysis, experiment, (Seed(0),), run_id)

    tradeoff = result["seed_results"][0]["per_client_tradeoff"]
    assert tradeoff[_ENNIO] == {
        "threshold_shift": pytest.approx(2.0 - 5.0),
        "fpr_delta": pytest.approx(0.05 - 0.10),
        "tpr_delta": pytest.approx(0.95 - 0.90),
    }
    assert tradeoff[_OTHER] == {
        "threshold_shift": pytest.approx(3.0 - 5.0),
        "fpr_delta": pytest.approx(0.15 - 0.20),
        "tpr_delta": pytest.approx(0.85 - 0.80),
    }


def test_analyze_locked_client_distribution_restricts_to_the_configured_client(tmp_path: Path) -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("confirmatory_threshold_scope_effect"))
    analysis = next(item for item in experiment.analyses if isinstance(item, LockedClientDistributionAnalysisRecord))
    assert analysis.locked_client_identifier == _ENNIO

    repository = AtomicArtifactRepository(tmp_path, lock_timeout=5.0)
    run_id = RunId("run_test")
    _commit_distribution_fixture(repository, app.config, experiment, run_id)

    handler = StatisticalAnalysisStageHandler(app.config, repository, app.statistical_analysis)
    result = handler._analyze_locked_client_distribution(analysis, experiment, (Seed(0),), run_id)

    seed_result = result["seed_results"][0]
    for label, per_client in seed_result["evaluations"].items():
        assert set(per_client) == {_ENNIO}, f"expected only the locked client for '{label}'"
    assert seed_result["evaluations"]["shared_mean"][_ENNIO]["threshold"] == 5.0
