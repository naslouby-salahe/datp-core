from pathlib import Path

import pytest

from datp_core.analysis.descriptive import ScoreRole
from datp_core.analysis.inference.bootstrap.contracts import BcaReason, BootstrapInterval
from datp_core.analysis.mechanisms import AbsorptionCohortResult
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    ClaimWording,
    ClientIdentityToken,
    DecisionRationale,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    FigureLabel,
    FigureTitle,
    MetricId,
    PopulationId,
)
from datp_core.core.numeric import MetricValue, Seed, ThresholdValue
from datp_core.presentation.export import (
    PublicationBundle,
    ReportProvenance,
    _interval_table,
    export_markdown,
    export_mechanism_publication,
)
from datp_core.presentation.figures import (
    EmpiricalCdfFigureSeries,
    FigureSeries,
    FigureSpec,
    ThresholdOverlay,
    empirical_cdf_series_from_points,
    render_markdown_figure,
)
from datp_core.presentation.tables import (
    EvidenceText,
    PublicationTable,
    TableCell,
    TableCellRenderedValue,
    TableTitle,
)
from datp_core.presentation.validation import ClaimDecision, ClaimReason, ClaimStatus


def _provenance() -> ReportProvenance:
    return ReportProvenance(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        evidence_role=EvidenceRole.CONFIRMATORY,
        analysis_checksum=Checksum("a" * 64),
    )


def test_interval_table_surfaces_the_bca_degeneracy_reason() -> None:
    from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL

    interval = BootstrapInterval.blocked(
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(3),
        point_estimate=None,
        reason=BcaReason.SEED_COHORT_MISMATCH,
    )
    table = _interval_table(interval)
    assert table.cells[0].evidence == "BCa outcome=blocked reason=seed_cohort_mismatch"


def test_figure_only_bundle_is_fully_rendered(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    figure = FigureSpec(
        title=FigureTitle("FPR disparity"),
        series=(
            FigureSeries(
                label=FigureLabel("Local threshold"),
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                values=(MetricValue(0.25), MetricValue(0.5)),
            ),
            FigureSeries(
                label=FigureLabel("Unavailable comparator"),
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.UNAVAILABLE,
                values=(),
            ),
        ),
    )
    export_markdown(
        PublicationBundle(provenance=_provenance(), claims=(), tables=(), figures=(figure,)),
        destination,
    )
    content = destination.read_text(encoding="utf-8")
    assert "## Figures" in content
    assert "### FPR disparity" in content
    assert "Local threshold" in content
    assert "0.25, 0.5" in content
    assert "Unavailable comparator" in content
    assert "`unavailable`" in content


def test_blocked_claims_are_separated_from_permitted_wording_by_status(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    permitted = ClaimDecision(
        status=ClaimStatus.PERMITTED,
        wording=ClaimWording("Local thresholding reduces FPR dispersion under the confirmatory ladder."),
        reason=ClaimReason("claim matches evidence scope"),
    )
    blocked = ClaimDecision(
        status=ClaimStatus.BLOCKED,
        wording=None,
        reason=ClaimReason("the anchor gate blocks dependent journal claims"),
    )
    export_markdown(
        PublicationBundle(provenance=_provenance(), claims=(permitted, blocked), tables=(), figures=()),
        destination,
    )
    content = destination.read_text(encoding="utf-8")
    assert "Local thresholding reduces FPR dispersion" in content
    assert "## Suppressed or blocked claims" in content
    assert "the anchor gate blocks dependent journal claims" in content


def test_all_blocked_claims_suppress_tables_and_figures(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    blocked = ClaimDecision(
        status=ClaimStatus.BLOCKED,
        wording=None,
        reason=ClaimReason("confirmatory BCa interval is unavailable"),
    )
    table = PublicationTable(
        title=TableTitle("Paired seed inventory"),
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value=TableCellRenderedValue("0.12"),
                evidence=EvidenceText("should not appear when every claim is blocked"),
            ),
        ),
    )
    figure = FigureSpec(
        title=FigureTitle("Should not appear"),
        series=(
            FigureSeries(
                label=FigureLabel("local"),
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                values=(MetricValue(0.1), MetricValue(0.2)),
            ),
        ),
    )
    export_markdown(
        PublicationBundle(
            provenance=_provenance(),
            claims=(blocked,),
            tables=(table,),
            figures=(figure,),
        ),
        destination,
    )
    content = destination.read_text(encoding="utf-8")
    assert "## Suppressed or blocked claims" in content
    assert "confirmatory BCa interval is unavailable" in content
    assert "Paired seed inventory" not in content
    assert "Should not appear" not in content
    assert "0.12" not in content


def test_report_provenance_rejects_primitive_checksum() -> None:
    with pytest.raises(TypeError, match="typed analysis checksum"):
        ReportProvenance(
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            evidence_role=EvidenceRole.CONFIRMATORY,
            analysis_checksum="a" * 64,  # type: ignore[arg-type]
        )


@pytest.fixture
def sample_absorption_mechanisms() -> tuple[AbsorptionCohortResult, ...]:
    return (
        AbsorptionCohortResult(
            observations=(),
            decision=ScientificDecisionResult(
                evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
                decision=ScientificDecision.BLOCKED,
                point_estimate=None,
                interval=None,
                rationale=DecisionRationale("fixture cohort blocked for evidence-role publication test"),
            ),
            mean_retention=None,
        ),
    )


def test_export_mechanism_publication_requires_explicit_evidence_role(
    tmp_path: Path,
    sample_absorption_mechanisms: tuple[AbsorptionCohortResult, ...],
) -> None:
    with pytest.raises(TypeError):
        export_mechanism_publication(  # type: ignore[call-arg]
            sample_absorption_mechanisms,
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=tmp_path,
        )


def test_export_mechanism_publication_does_not_override_supplied_role(
    tmp_path: Path,
    sample_absorption_mechanisms: tuple[AbsorptionCohortResult, ...],
) -> None:
    export_mechanism_publication(
        sample_absorption_mechanisms,
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=tmp_path,
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
    )
    provenance_text = (tmp_path / "publication.md").read_text()
    assert EvidenceRole.TRAINING_STRESS_TEST.value in provenance_text


def test_empirical_cdf_figure_series_uses_reconstruction_and_cumulative_metrics() -> None:
    series = empirical_cdf_series_from_points(
        label=FigureLabel("seed0:device_a:benign_evaluation"),
        points=(
            (MetricValue(0.1), MetricValue(0.5)),
            (MetricValue(0.3), MetricValue(1.0)),
        ),
        client_id=ClientIdentityToken("device_a"),
        seed=Seed(0),
        score_role=ScoreRole.BENIGN_EVALUATION,
        threshold_overlays=(
            ThresholdOverlay(method=FederatedThresholdMethod.SHARED_THRESHOLD, value=ThresholdValue(0.2)),
            ThresholdOverlay(method=FederatedThresholdMethod.LOCAL_THRESHOLD, value=ThresholdValue(0.25)),
            ThresholdOverlay(method=FederatedThresholdMethod.CLUSTER_THRESHOLD, value=ThresholdValue(0.22)),
        ),
        source_checksum=Checksum("f" * 64),
    )
    assert isinstance(series, EmpiricalCdfFigureSeries)
    assert series.x_metric is MetricId.RECONSTRUCTION_ERROR
    assert series.y_metric is MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY
    assert tuple(item.value for item in series.x_values) == (0.1, 0.3)
    assert tuple(item.value for item in series.y_values) == (0.5, 1.0)
    assert series.threshold_overlays[0] == ThresholdOverlay(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        value=ThresholdValue(0.2),
    )

    unavailable = empirical_cdf_series_from_points(
        label=FigureLabel("seed0:device_b:attack_evaluation"),
        points=(),
        client_id=ClientIdentityToken("device_b"),
        seed=Seed(0),
        score_role=ScoreRole.ATTACK_EVALUATION,
        source_checksum=Checksum("f" * 64),
        unavailable_reason=AnalysisReasonText("no scores available for the declared role"),
    )
    assert unavailable.availability is AvailabilityStatus.UNAVAILABLE
    assert unavailable.x_values == ()
    assert unavailable.y_values == ()

    rendered = render_markdown_figure(
        FigureSpec(
            title=FigureTitle("Per-client empirical score CDF"),
            empirical_cdf_series=(series, unavailable),
        )
    )
    assert "reconstruction_error" in rendered
    assert "empirical_cumulative_probability" in rendered
    assert "shared_threshold=0.2" in rendered
    assert "device_b" in rendered
    assert "no scores available for the declared role" in rendered


def test_empirical_cdf_rejects_fpr_as_score_metric() -> None:
    label = FigureLabel("bad")
    client_id = ClientIdentityToken("device_a")
    seed = Seed(0)
    with pytest.raises(ValueError, match="reconstruction-error x metric"):
        EmpiricalCdfFigureSeries(
            label=label,
            x_metric=MetricId.FALSE_POSITIVE_RATE,
            y_metric=MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY,
            availability=AvailabilityStatus.AVAILABLE,
            x_values=(MetricValue(0.1),),
            y_values=(MetricValue(1.0),),
            client_id=client_id,
            seed=seed,
            score_role=ScoreRole.BENIGN_EVALUATION,
            threshold_overlays=(),
            source_checksum=None,
        )
