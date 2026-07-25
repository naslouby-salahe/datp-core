"""Exhaustive analysis-kind routing coverage for ``execution.dispatch``: every non-paired
``AnalysisKind`` must route to its owning capability implementation, and paired-threshold
analyses must never reach the generic dispatcher."""

from __future__ import annotations

import pytest
from attrs import evolve

from datp_core.analysis.execution import dispatch as dispatch_module
from datp_core.analysis.execution.inputs import AnalysisInputBundle, PrerequisiteExperimentResult
from datp_core.core.identifiers import ExperimentId, StatisticalProfileId
from datp_core.experiments import (
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisKind,
    AnchorEquivalenceAnalysisRecord,
    ClusterStabilityAnalysisRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    QuantileEstimationAnalysisRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
)
from datp_core.reporting.freezing.models import FrozenResultManifest

_PROFILE = StatisticalProfileId("paired_seed_bca")

_RECORDS_AND_ENTRY_POINTS = {
    AnalysisKind.METRIC_ASSOCIATION: (
        MetricAssociationAnalysisRecord(
            label="l",
            kind="metric_association_analysis",
            result_type="r",
            statistical_profile=_PROFILE,
            secondary_statistical_profile=None,
            predictor_metric="pairwise_js_divergence",
            outcome_metric="cv_fpr_delta",
            outcome_source_analysis="source",
            interpretation_constraint="c",
            grouping_dimension=None,
        ),
        "analyze_association",
    ),
    AnalysisKind.THRESHOLD_STABILITY: (
        ThresholdStabilityAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluation="e",
            produced_fields=(),
            per_sweep_cell="calibration_sample_count",
        ),
        "analyze_threshold_stability",
    ),
    AnalysisKind.RECOVERY_FRACTION: (
        RecoveryFractionAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            formula="f",
            numerator_analysis="n",
            denominator_analysis="d",
            denominator_composition="c",
            denominator_materiality_rule=1e-6,
            undefined_denominator_behavior="u",
        ),
        "analyze_recovery_fraction",
    ),
    AnalysisKind.ABSORPTION: (
        AbsorptionAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            absorption_metric="m",
            formula="f",
            band_interpretation="b",
            denominator_materiality_rule=1e-6,
            undefined_denominator_behavior="u",
            matching_contract={},
            outcome_bands=(),
            outcome_bands_are_mutually_exclusive_and_exhaustive=True,
            reference_analysis="ref",
            stress_test_analysis="stress",
            alternative_path_rule=None,
        ),
        "analyze_absorption",
    ),
    AnalysisKind.ANCHOR_EQUIVALENCE: (
        AnchorEquivalenceAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_analysis="s",
            comparison_mode="statistical_fallback",
            comparison_mode_rule="rule",
            interval_width_tolerance_multiplier=1.2,
            floating_point_tolerance={},
            historical_reference={},
            expected_metric="cv_fpr",
            expected_first_threshold_policy="shared_mean_p95",
            expected_second_threshold_policy="local_p95",
            statistical_fallback_requirements=(),
            failure_reasons=(),
            downstream_blocking_behavior="block",
        ),
        "analyze_anchor_equivalence",
    ),
    AnalysisKind.TEMPORAL_RECOVERY: (
        TemporalRecoveryAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            primary_metric="cv_fpr",
            static_reference_evaluation="s",
            frozen_evaluation="f",
            recalibrated_evaluation="r",
            recovery_fields=(),
            drift_excess_formula="d",
            recovered_amount_formula="r",
            recovery_ratio_formula="r",
            meaningful_degradation_rule="rule",
            recovery_ratio_precondition="precondition",
            negative_recovery_policy="p",
            recovery_ratio_direction="direction",
            meaningful_recovery_threshold=0.5,
            chronology_unverifiable_policy="p",
            outcome_bands=(),
            outcome_bands_are_mutually_exclusive_and_exhaustive=True,
        ),
        "analyze_temporal_recovery",
    ),
    AnalysisKind.CLUSTER_STABILITY: (
        ClusterStabilityAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluation="e",
            comparison_unit="u",
            produced_fields=(),
            reference_evaluation=None,
            run_requirement=None,
        ),
        "analyze_cluster_stability",
    ),
    AnalysisKind.CONFORMAL_COVERAGE: (
        ConformalCoverageAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluation="e",
            target_coverage=0.95,
            produced_fields=(),
            coverage_direction=None,
        ),
        "analyze_conformal_coverage",
    ),
    AnalysisKind.DISTRIBUTION_MECHANISM: (
        DistributionMechanismAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluations=(),
            produced_fields=(),
            field_formulas=None,
        ),
        "analyze_distribution_mechanism",
    ),
    AnalysisKind.LOCKED_CLIENT_DISTRIBUTION: (
        LockedClientDistributionAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluations=(),
            produced_fields=(),
            locked_client_identifier="client",
        ),
        "analyze_locked_client_distribution",
    ),
    AnalysisKind.ALERT_BURDEN: (
        AlertBurdenAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            formula="f",
            produced_fields=(),
            source_evaluations=(),
            required_operational_input="input",
            per_client_reporting_required=False,
            unavailable_behavior="skip",
        ),
        "analyze_alert_burden",
    ),
    AnalysisKind.QUANTILE_ESTIMATION: (
        QuantileEstimationAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluations=(),
            produced_fields=(),
            oracle_reference="oracle",
        ),
        "analyze_quantile_estimation",
    ),
    AnalysisKind.RESOURCE_COST: (
        ResourceCostAnalysisRecord(
            label="l",
            kind="k",
            result_type="r",
            statistical_profile=_PROFILE,
            source_evaluations=(),
            produced_fields=(),
            estimate_basis="basis",
        ),
        "analyze_resource_cost",
    ),
}


_KINDS = sorted(_RECORDS_AND_ENTRY_POINTS, key=lambda k: k.value)


@pytest.mark.parametrize("kind", _KINDS)
def test_dispatch_routes_each_analysis_kind_to_its_owning_capability(
    kind: AnalysisKind, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, entry_point_name = _RECORDS_AND_ENTRY_POINTS[kind]
    sentinel = object()
    called_with: dict[str, object] = {}

    def stub(analysis_record: object, *_args: object, **_kwargs: object) -> object:
        called_with["record"] = analysis_record
        return sentinel

    monkeypatch.setattr(dispatch_module, entry_point_name, stub)
    if kind is AnalysisKind.ABSORPTION:
        monkeypatch.setattr(dispatch_module, "_reference_paired_result", lambda *_args: object())

    result = dispatch_module.dispatch(
        kind,
        record,
        config=None,  # type: ignore[arg-type]
        store=None,  # type: ignore[arg-type]
        inputs=AnalysisInputBundle(()),
        statistical_analysis=None,  # type: ignore[arg-type]
        experiment=None,  # type: ignore[arg-type]
        seeds=(),
        paired_results=(),
        prerequisite_results=(),
        calibration_sample_count_values=(None,),
    )

    assert called_with["record"] is record
    assert sentinel in result


def test_dispatch_rejects_paired_threshold_since_it_is_routed_separately() -> None:
    with pytest.raises(AssertionError, match="dispatch_paired"):
        dispatch_module.dispatch(
            AnalysisKind.PAIRED_THRESHOLD,
            None,  # type: ignore[arg-type]
            config=None,  # type: ignore[arg-type]
            store=None,  # type: ignore[arg-type]
            inputs=AnalysisInputBundle(()),
            statistical_analysis=None,  # type: ignore[arg-type]
            experiment=None,  # type: ignore[arg-type]
            seeds=(),
            paired_results=(),
            prerequisite_results=(),
            calibration_sample_count_values=(None,),
        )


def test_every_analysis_kind_except_paired_threshold_has_dispatch_coverage() -> None:
    covered = set(_RECORDS_AND_ENTRY_POINTS) | {AnalysisKind.PAIRED_THRESHOLD}
    assert covered == set(AnalysisKind)


def test_absorption_loads_its_reference_paired_result_only_from_the_configured_prerequisite() -> None:
    record = _RECORDS_AND_ENTRY_POINTS[AnalysisKind.ABSORPTION][0]
    assert isinstance(record, AbsorptionAnalysisRecord)
    prerequisite = PrerequisiteExperimentResult(
        experiment_id=ExperimentId("reference-experiment"),
        frozen_result_path="experiments/reference/frozen-result.json",
        frozen_result_checksum="a" * 64,
        scientific_fingerprint="reference-science",
        result=FrozenResultManifest(
            schema_version=1,
            experiment_id="reference-experiment",
            evidence_role="supportive",
            dataset_id="nbaiot",
            population_ids=("natural",),
            seed_cohort_id="cohort",
            seed_count=2,
            seeds_present=(1, 2),
            scientific_fingerprint="reference-science",
            execution_fingerprint="reference-execution",
            source_revision="revision",
            frozen_at="2026-07-25T00:00:00Z",
            metric_definition_version="metrics-v1",
            statistical_procedure_version="stats-v1",
            report_profiles=(),
            source_files=(),
            statistical_results=(
                {
                    "analysis_label": "ref",
                    "metric": "cv_fpr",
                    "first_threshold_policy": "shared_mean_p95",
                    "second_threshold_policy": "local_p95",
                    "training_seeds": [1, 2],
                    "first_seed_values": [0.2, 0.3],
                    "second_seed_values": [0.1, 0.2],
                    "first_mean": 0.25,
                    "second_mean": 0.15,
                    "mean_difference": 0.1,
                        "confidence_interval": {
                            "lower_bound": 0.01,
                            "upper_bound": 0.2,
                            "confidence_level": 0.95,
                            "method": "bca_bootstrap",
                        },
                    "p_value": 0.05,
                    "rank_biserial": 1.0,
                    "resample_count": 1000,
                    "analysis_seed": 300,
                    "seed_differences": [0.1, 0.1],
                    "sign_consistency": 1.0,
                    "zero_difference_count": 0,
                    "negative_difference_count": 0,
                },
            ),
        ),
    )
    configured = evolve(
        record,
        reference_analysis={"experiment": "reference-experiment", "analysis": "ref"},
    )

    reference = dispatch_module._reference_paired_result(configured, (prerequisite,))

    assert reference.analysis_label == "ref"
    with pytest.raises(ValueError, match="requires its prerequisite frozen paired result"):
        dispatch_module._reference_paired_result(configured, ())
