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
from datp_core.reporting.export import PublicationBundle, ReportProvenance, export_markdown
from datp_core.reporting.figures import FigureSeries, FigureSpec
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


def test_report_provenance_rejects_primitive_checksum() -> None:
    with pytest.raises(TypeError, match="typed analysis checksum"):
        ReportProvenance(
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            evidence_role=EvidenceRole.CONFIRMATORY,
            analysis_checksum="a" * 64,  # type: ignore[arg-type]
        )
