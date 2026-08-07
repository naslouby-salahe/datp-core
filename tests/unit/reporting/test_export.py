from pathlib import Path

import pytest

from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    MetricId,
    PopulationId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue
from datp_core.reporting.export import PublicationBundle, ReportProvenance, export_markdown
from datp_core.reporting.figures import (
    EmpiricalCdfFigureSeries,
    FigureSeries,
    FigureSpec,
    empirical_cdf_series_from_points,
    render_markdown_figure,
)
from datp_core.reporting.validation import ClaimDecision, ClaimStatus


def _provenance() -> ReportProvenance:
    return ReportProvenance(
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        evidence_role=EvidenceRole.CONFIRMATORY,
        analysis_checksum=Checksum("a" * 64),
    )


def test_figure_only_bundle_is_fully_rendered(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    figure = FigureSpec(
        title="FPR disparity",
        series=(
            FigureSeries(
                label="Local threshold",
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                values=(0.25, 0.5),
            ),
            FigureSeries(
                label="Unavailable comparator",
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
        wording="Local thresholding reduces FPR dispersion under the confirmatory ladder.",
        reason="claim matches evidence scope",
    )
    blocked = ClaimDecision(
        status=ClaimStatus.BLOCKED,
        wording="",
        reason="the anchor gate blocks dependent journal claims",
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
    from datp_core.reporting.tables import PublicationTable, TableCell

    destination = tmp_path / "report.md"
    blocked = ClaimDecision(
        status=ClaimStatus.BLOCKED,
        wording="",
        reason="confirmatory BCa interval is unavailable",
    )
    table = PublicationTable(
        title="Paired seed inventory",
        cells=(
            TableCell(
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                rendered_value="0.12",
                evidence="should not appear when every claim is blocked",
            ),
        ),
    )
    figure = FigureSpec(
        title="Should not appear",
        series=(
            FigureSeries(
                label="local",
                metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
                availability=AvailabilityStatus.AVAILABLE,
                values=(0.1, 0.2),
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


def test_empirical_cdf_figure_series_uses_reconstruction_and_cumulative_metrics() -> None:
    series = empirical_cdf_series_from_points(
        label="seed0:device_a:benign_evaluation",
        points=(
            (MetricValue(0.1), MetricValue(0.5)),
            (MetricValue(0.3), MetricValue(1.0)),
        ),
        client_id="device_a",
        seed=Seed(0),
        score_role="benign_evaluation",
        threshold_overlays=(
            ("shared_threshold", 0.2),
            ("local_threshold", 0.25),
            ("cluster_threshold", 0.22),
        ),
        source_checksum=Checksum("f" * 64),
    )
    assert isinstance(series, EmpiricalCdfFigureSeries)
    assert series.x_metric is MetricId.RECONSTRUCTION_ERROR
    assert series.y_metric is MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY
    assert series.x_values == (0.1, 0.3)
    assert series.y_values == (0.5, 1.0)
    assert series.threshold_overlays[0] == ("shared_threshold", 0.2)

    unavailable = empirical_cdf_series_from_points(
        label="seed0:device_b:attack_evaluation",
        points=(),
        client_id="device_b",
        seed=Seed(0),
        score_role="attack_evaluation",
        source_checksum=Checksum("f" * 64),
        unavailable_reason="no scores available for the declared role",
    )
    assert unavailable.availability is AvailabilityStatus.UNAVAILABLE
    assert unavailable.x_values == ()
    assert unavailable.y_values == ()

    rendered = render_markdown_figure(
        FigureSpec(
            title="Per-client empirical score CDF",
            empirical_cdf_series=(series, unavailable),
        )
    )
    assert "reconstruction_error" in rendered
    assert "empirical_cumulative_probability" in rendered
    assert "shared_threshold=0.2" in rendered
    assert "device_b" in rendered
    assert "no scores available for the declared role" in rendered


def test_empirical_cdf_rejects_fpr_as_score_metric() -> None:
    with pytest.raises(ValueError, match="reconstruction-error x metric"):
        EmpiricalCdfFigureSeries(
            label="bad",
            x_metric=MetricId.FALSE_POSITIVE_RATE,
            y_metric=MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY,
            availability=AvailabilityStatus.AVAILABLE,
            x_values=(0.1,),
            y_values=(1.0,),
            client_id="device_a",
            seed=Seed(0),
            score_role="benign_evaluation",
            threshold_overlays=(),
            source_checksum=None,
        )
