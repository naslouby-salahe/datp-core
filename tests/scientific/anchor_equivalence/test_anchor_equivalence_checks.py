"""Scientific-invariant tests for anchor equivalence (SCIENTIFIC_SOURCE_OF_TRUTH.md's locked
`confirmatory-b1-vs-b2` anchor claim): `analyze_anchor_equivalence` must correctly decide whether a
reproduced paired-threshold result reproduces the locked historical anchor (B1 CV(FPR)=1.017,
B2 CV(FPR)=0.299, delta=0.718, 95% CI=[0.647, 0.769], interval_width=0.122), using the real,
configured `anchor_reproduction` experiment's `anchor_equivalence` analysis record -- never an
invented one.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from datp_core.analysis.paired import analyze_anchor_equivalence
from datp_core.analysis.results import PairedThresholdAnalysisResult
from datp_core.analysis.statistics import ConfidenceInterval
from datp_core.config.loading import RuntimeBootstrapSettings
from datp_core.config.project import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.core.identifiers import ExperimentId
from datp_core.core.values import Probability
from datp_core.experiments.models import AnchorEquivalenceAnalysisRecord


@pytest.fixture(scope="module")
def _resolved() -> ResolvedProjectConfiguration:
    os.environ.setdefault("DATP_EXECUTION_PROFILE", "scientific")
    return resolve_project_configuration(
        config_dir=Path("configs"),
        bootstrap_settings=RuntimeBootstrapSettings(),  # pyright: ignore[reportCallIssue]
    )


@pytest.fixture(scope="module")
def _record(_resolved: ResolvedProjectConfiguration) -> AnchorEquivalenceAnalysisRecord:
    experiment = _resolved.experiments.get(ExperimentId("anchor_reproduction"))
    record = next(
        item
        for item in experiment.analyses
        if isinstance(item, AnchorEquivalenceAnalysisRecord) and item.label == "anchor_equivalence"
    )
    return record


def _paired_result(
    *, analysis_label: str, mean_difference: float, lower_bound: float, upper_bound: float
) -> PairedThresholdAnalysisResult:
    return PairedThresholdAnalysisResult(
        analysis_label=analysis_label,
        metric="cv_fpr",
        first_threshold_policy="shared_mean_p95",
        second_threshold_policy="local_p95",
        training_seeds=(0, 1, 2, 3, 4),
        first_seed_values=(1.0, 1.0, 1.0, 1.0, 1.0),
        second_seed_values=(0.3, 0.3, 0.3, 0.3, 0.3),
        first_mean=1.0,
        second_mean=0.3,
        mean_difference=mean_difference,
        confidence_interval=ConfidenceInterval(
            lower_bound=lower_bound, upper_bound=upper_bound, confidence_level=Probability(0.95), method="bca"
        ),
        p_value=0.01,
        rank_biserial=1.0,
        resample_count=10_000,
        analysis_seed=300,
        seed_differences=(0.7, 0.7, 0.7, 0.7, 0.7),
        sign_consistency=1.0,
        zero_difference_count=0,
        negative_difference_count=0,
    )


def test_historical_reference_matches_scientific_source_of_truth(_record: AnchorEquivalenceAnalysisRecord) -> None:
    historical = _record.historical_reference
    assert historical["delta"] == 0.718
    assert historical["lower_bound"] == 0.647
    assert historical["upper_bound"] == 0.769
    assert historical["interval_width"] == 0.122


def test_reproduction_of_historical_anchor_passes_every_check(
    _record: AnchorEquivalenceAnalysisRecord,
) -> None:
    source = _paired_result(
        analysis_label=_record.source_analysis, mean_difference=0.73, lower_bound=0.65, upper_bound=0.77
    )
    result = analyze_anchor_equivalence(_record, (source,))
    assert result.passed
    assert result.failure_reasons == ()
    assert result.checks.positive_reproduced_delta
    assert result.checks.reproduced_estimate_within_historical_interval
    assert result.checks.overlapping_confidence_intervals
    assert result.checks.no_material_movement_toward_zero
    assert result.checks.reproduced_interval_width_at_most_1_20x_historical_width


def test_delta_moving_toward_zero_fails_only_that_check(_record: AnchorEquivalenceAnalysisRecord) -> None:
    # Still positive, still inside the historical interval and CI-overlapping, still narrow enough --
    # but below the locked historical delta, which alone must fail reproduction.
    source = _paired_result(
        analysis_label=_record.source_analysis, mean_difference=0.70, lower_bound=0.63, upper_bound=0.77
    )
    result = analyze_anchor_equivalence(_record, (source,))
    assert not result.passed
    assert result.failure_reasons == ("no_material_movement_toward_zero",)
    assert result.checks.positive_reproduced_delta
    assert result.checks.reproduced_estimate_within_historical_interval
    assert result.checks.overlapping_confidence_intervals
    assert not result.checks.no_material_movement_toward_zero
    assert result.checks.reproduced_interval_width_at_most_1_20x_historical_width


def test_interval_too_wide_fails_only_that_check(_record: AnchorEquivalenceAnalysisRecord) -> None:
    # Exactly the historical delta (>= boundary passes) but a CI more than 1.20x the historical width.
    source = _paired_result(
        analysis_label=_record.source_analysis, mean_difference=0.718, lower_bound=0.50, upper_bound=0.95
    )
    result = analyze_anchor_equivalence(_record, (source,))
    assert not result.passed
    assert result.failure_reasons == ("reproduced_interval_width_at_most_1.20x_historical_width",)
    assert result.checks.no_material_movement_toward_zero
    assert not result.checks.reproduced_interval_width_at_most_1_20x_historical_width


def test_sign_reversal_fails_every_directional_check(_record: AnchorEquivalenceAnalysisRecord) -> None:
    source = _paired_result(
        analysis_label=_record.source_analysis, mean_difference=-0.1, lower_bound=-0.2, upper_bound=0.0
    )
    result = analyze_anchor_equivalence(_record, (source,))
    assert not result.passed
    assert not result.checks.positive_reproduced_delta
    assert not result.checks.reproduced_estimate_within_historical_interval
    assert not result.checks.overlapping_confidence_intervals
    assert not result.checks.no_material_movement_toward_zero


def test_missing_paired_source_is_rejected(_record: AnchorEquivalenceAnalysisRecord) -> None:
    with pytest.raises(ValueError, match="no supported paired source"):
        analyze_anchor_equivalence(_record, ())
