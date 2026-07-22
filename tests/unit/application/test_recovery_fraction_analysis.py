"""Recovery fractions are derived from the matched paired seed gaps."""

import polars as pl
import pytest

from datp_core.application.stage_handlers import (
    StatisticalAnalysisStageHandler,
    _conformal_seed_coverage,
    _seed_ratio_result,
)
from datp_core.composition.root import build_application
from datp_core.domain.catalogue import AnchorEquivalenceAnalysisRecord, RecoveryFractionAnalysisRecord
from datp_core.domain.identifiers import ExperimentId


def test_recovery_fraction_uses_the_composed_shared_local_denominator() -> None:
    experiment = build_application().config.experiments.get(ExperimentId("cluster_and_family_threshold_mechanism"))
    analysis = next(item for item in experiment.analyses if isinstance(item, RecoveryFractionAnalysisRecord))

    result = StatisticalAnalysisStageHandler._analyze_recovery_fraction(
        analysis,
        [
            {"analysis_label": "shared_vs_cluster_recovery", "seed_differences": [0.2, 0.1]},
            {"analysis_label": "cluster_vs_local", "seed_differences": [0.2, -0.1]},
        ],
    )

    assert result["per_seed_recovery_fraction"] == [0.5, None]
    assert result["defined_seed_count"] == 1
    assert result["mean_defined_recovery_fraction"] == 0.5


def test_absorption_ratio_reports_per_seed_and_ratio_of_seed_means() -> None:
    result = _seed_ratio_result(
        label="absorption",
        formula="stress / reference",
        numerator={"seed_differences": [0.2, 0.1]},
        denominator={"seed_differences": [0.4, 0.0]},
        materiality_rule="absolute_denominator_at_least_1.0e-6",
        undefined_behavior="typed_undefined_ratio",
    )

    assert result["per_seed_ratio"] == [0.5, None]
    assert result["ratio_of_seed_means"] == pytest.approx(0.75)


def test_anchor_equivalence_requires_every_configured_statistical_fallback_rule() -> None:
    experiment = build_application().config.experiments.get(ExperimentId("anchor_reproduction"))
    analysis = next(item for item in experiment.analyses if isinstance(item, AnchorEquivalenceAnalysisRecord))

    result = StatisticalAnalysisStageHandler._analyze_anchor_equivalence(
        analysis,
        [{"analysis_label": "anchor_scope_effect", "mean_difference": 0.72, "confidence_interval": [0.66, 0.76]}],
    )

    assert result["passed"] is True
    assert result["failure_reasons"] == ()


def test_conformal_coverage_uses_held_out_benign_confusion_counts_and_persisted_rank() -> None:
    result = _conformal_seed_coverage(
        pl.DataFrame(
            {
                "client_id": ["c1", "c2"],
                "threshold": [1.0, 2.0],
                "owner_kind": ["split_conformal", "split_conformal"],
                "finite_sample_rank": [96, 96],
                "attainability_status": ["attainable", "attainable"],
            }
        ),
        pl.DataFrame(
            {
                "client_id": ["c1", "c2"],
                "true_positives": [0, 0],
                "false_positives": [10, 0],
                "true_negatives": [90, 100],
                "false_negatives": [0, 0],
                "false_positive_rate": [0.1, 0.0],
                "false_positive_rate_status": ["available", "available"],
                "true_positive_rate": [None, None],
                "true_positive_rate_status": ["unavailable_no_attack_records", "unavailable_no_attack_records"],
                "balanced_accuracy": [None, None],
                "balanced_accuracy_status": ["unavailable_no_attack_records", "unavailable_no_attack_records"],
                "macro_f1": [None, None],
                "macro_f1_status": ["unavailable_no_attack_records", "unavailable_no_attack_records"],
            }
        ),
        {"c1": 100, "c2": 100},
        0.95,
        0.05,
        100,
    )

    assert result["benign_true_negatives"] == 190
    assert result["benign_total"] == 200
    assert result["client_coverages"] == [0.9, 1.0]
    assert result["finite_sample_rank"] == {"c1": 96, "c2": 96}
