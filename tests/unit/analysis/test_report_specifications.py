from dataclasses import fields
from decimal import Decimal

from datp_core.analysis.figures.specifications import (
    cdf_overlay_figure,
    heatmap_figure,
    lambda_curve_figure,
    recovery_curve_figure,
    scatter_figure,
    severity_trend_figure,
)
from datp_core.analysis.report_models import (
    CartesianPoint,
    FigureSeries,
    HeatmapCell,
    ReportColumn,
    ReportRow,
    TableSpecification,
)
from datp_core.analysis.tables.specifications import (
    ConformalCoverageTableSpecification,
    EligibilityCoverageTableSpecification,
    alert_burden_table,
    boundary_null_table,
    cluster_stability_table,
    communication_storage_cost_table,
    comparator_table,
    confirmatory_interval_table,
    contingency_table,
    dispersion_ladder_table,
    policy_evaluation_summary_table,
    sensitivity_grid_table,
    stress_test_table,
)
from datp_core.analysis.wording import select_claim_wording
from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.evaluation.alert_burden import (
    CalibrationSampleCount,
    CalibrationSampleCountRef,
    ConfusionCount,
    SampleCount,
)
from datp_core.domain.evaluation.operating_points import (
    BalancedAccuracyScore,
    ClientEligibilityReason,
    ClientEligibilityStatus,
    ClientEvaluationResult,
    ConformalCoverageResult,
    EligibilityCoverageResult,
    EligibleClientSet,
    F1Score,
    FleetDetectionResult,
    FleetDispersionResult,
    PolicyEvaluationResult,
    PrecisionScore,
    RecallScore,
    ValidCvResult,
    ZeroDenominatorPolicy,
)
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ClaimOutcome,
    EligibilityCoverage,
    FalsePositiveRate,
    TruePositiveRate,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.experiments.protocols import FigureType, TableType
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.thresholding.policies import CoreThresholdPolicy, ThresholdValue


def _columns() -> tuple[ReportColumn, ...]:
    return (ReportColumn(key="metric", label="Metric"),)


def _rows() -> tuple[ReportRow, ...]:
    return (ReportRow(values=(0.125,)),)


def _series() -> tuple[FigureSeries, ...]:
    return (FigureSeries(label="observed", points=(CartesianPoint(horizontal=1, vertical=0.125),)),)


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _policy_evaluation() -> PolicyEvaluationResult:
    client = ClientId(value="client-a")
    eligible_client_set = EligibleClientSet(
        roster=ClientRoster(client_ids=(client,)),
        protocol_eligibility_rule_identity=_fingerprint("a"),
        eligible_clients=(client,),
        ineligible_reasons=(),
        identity=_fingerprint("b"),
    )
    client_result = ClientEvaluationResult(
        client_id=client,
        true_positive=ConfusionCount(value=8),
        false_positive=ConfusionCount(value=2),
        true_negative=ConfusionCount(value=18),
        false_negative=ConfusionCount(value=2),
        benign_test_count=SampleCount(value=20),
        attack_test_count=SampleCount(value=10),
        assigned_threshold=ThresholdValue(value=1.0),
        false_positive_rate=FalsePositiveRate(value=0.1),
        true_positive_rate=TruePositiveRate(value=0.8),
        precision=PrecisionScore(value=0.8),
        recall=RecallScore(value=0.8),
        f1=F1Score(value=0.8),
        balanced_accuracy=BalancedAccuracyScore(value=0.85),
        eligibility_status=ClientEligibilityStatus.ELIGIBLE,
        eligibility_reason=ClientEligibilityReason.SUFFICIENT_CALIBRATION,
        calibration_sample_count_reference=CalibrationSampleCountRef(
            calibration_artifact_id=CalibrationScoreArtifactId(value="artifact-" + "c" * 64),
            client_id=client,
            recorded_count=CalibrationSampleCount(value=100),
        ),
        eligible_client_set_identity=eligible_client_set.identity,
        fallback_fingerprint=_fingerprint("d"),
        test_split_identity=_fingerprint("e"),
        zero_denominator_policy=ZeroDenominatorPolicy.ZERO,
    )
    coverage = EligibilityCoverageResult(
        eligible_count=1,
        roster_count=1,
        coverage=EligibilityCoverage(value=Decimal("1")),
        eligible_client_set_identity=eligible_client_set.identity,
    )
    return PolicyEvaluationResult(
        policy=CoreThresholdPolicy.B2,
        evaluation_identity=_fingerprint("f"),
        eligible_client_set=eligible_client_set,
        client_results=(client_result,),
        fleet_dispersion=FleetDispersionResult(
            cv_fpr=ValidCvResult(point_estimate=0.1, affected_scope_identity=_fingerprint("f")),
            cv_tpr=ValidCvResult(point_estimate=0.2, affected_scope_identity=_fingerprint("f")),
            iqr_fpr=0.01,
            fpr_range=0.02,
            worst_client_fpr=FalsePositiveRate(value=0.1),
            eligibility_coverage=coverage,
        ),
        fleet_detection=FleetDetectionResult(
            macro_f1=F1Score(value=0.8),
            p10_macro_f1=F1Score(value=0.8),
            worst_client_balanced_accuracy=BalancedAccuracyScore(value=0.85),
            auroc_control=AuRocScore(value=0.9),
        ),
        fleet_equity=None,
        cluster_dispersion=None,
    )


def test_every_table_family_constructs_a_framework_free_table_specification() -> None:
    constructors = (
        confirmatory_interval_table,
        dispersion_ladder_table,
        sensitivity_grid_table,
        comparator_table,
        stress_test_table,
        cluster_stability_table,
        contingency_table,
        boundary_null_table,
        alert_burden_table,
        communication_storage_cost_table,
    )

    specifications = tuple(constructor(_columns(), _rows()) for constructor in constructors)

    assert tuple(specification.table_type for specification in specifications) == tuple(TableType)
    assert all(type(specification) is TableSpecification for specification in specifications)


def test_every_approved_figure_family_constructs_without_a_sankey_path() -> None:
    figures = (
        cdf_overlay_figure("score", "cdf", _series()),
        scatter_figure("heterogeneity", "gain", _series()),
        heatmap_figure("quantile", "policy", "cv_fpr", (HeatmapCell(horizontal=0.95, vertical="b2", intensity=0.1),)),
        lambda_curve_figure("lambda", "gain", _series()),
        recovery_curve_figure("window", "recovery", _series()),
        severity_trend_figure("alpha", "gain", _series()),
    )

    assert tuple(figure.figure_type for figure in figures) == tuple(FigureType)
    assert all("sankey" not in figure.figure_type.value for figure in figures)


def test_eligibility_and_conformal_coverage_are_separate_typed_specification_fields() -> None:
    table = sensitivity_grid_table(_columns(), _rows())
    eligibility = EligibilityCoverageResult(
        eligible_count=1,
        roster_count=2,
        coverage=EligibilityCoverage(value=Decimal("0.5")),
        eligible_client_set_identity=StageFingerprint(value="a" * 64),
    )
    conformal = ConformalCoverageResult(
        empirical_coverage=0.95,
        target_coverage=0.95,
        conformal_split_identity=StageFingerprint(value="b" * 64),
    )

    eligibility_specification = EligibilityCoverageTableSpecification(table=table, eligibility_coverage=eligibility)
    conformal_specification = ConformalCoverageTableSpecification(table=table, conformal_coverage=conformal)

    assert tuple(field.name for field in fields(EligibilityCoverageTableSpecification)) == (
        "table",
        "eligibility_coverage",
    )
    assert tuple(field.name for field in fields(ConformalCoverageTableSpecification)) == (
        "table",
        "conformal_coverage",
    )
    assert eligibility_specification.eligibility_coverage is eligibility
    assert conformal_specification.conformal_coverage is conformal


def test_policy_evaluation_table_uses_typed_result_values_and_eligibility_coverage() -> None:
    specification = policy_evaluation_summary_table(_policy_evaluation())

    assert specification.table.table_type is TableType.DISPERSION_LADDER
    assert specification.table.rows[0].values == ("b2", 0.1, 0.01, 0.02, 0.1, 1, 1)
    assert specification.eligibility_coverage.coverage.value == Decimal("1.000000000000")


def test_claim_wording_is_closed_and_deterministic_for_every_outcome() -> None:
    selections = tuple(select_claim_wording(outcome) for outcome in ClaimOutcome)

    assert tuple(selection.outcome for selection in selections) == tuple(ClaimOutcome)
    assert all(selection.template for selection in selections)
    assert select_claim_wording(ClaimOutcome.NULL) == select_claim_wording(ClaimOutcome.NULL)
