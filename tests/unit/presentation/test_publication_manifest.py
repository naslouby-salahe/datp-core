import json
from pathlib import Path

from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole, ExperimentId, MetricId, PopulationId
from datp_core.presentation.export import (
    PUBLICATION_SOURCE_MANIFEST_FILENAME,
    PublicationBundle,
    ReportProvenance,
    export_markdown,
)
from datp_core.presentation.tables import EvidenceText, PublicationTable, TableCell, TableCellRenderedValue, TableTitle


def test_publication_export_writes_traceable_source_manifest(tmp_path: Path) -> None:
    publication = export_markdown(
        PublicationBundle(
            provenance=ReportProvenance(
                experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                evidence_role=EvidenceRole.CONFIRMATORY,
            ),
            claims=(),
            tables=(
                PublicationTable(
                    title=TableTitle("summary"),
                    cells=(
                        TableCell(
                            metric=MetricId.FALSE_POSITIVE_RATE,
                            availability=AvailabilityStatus.AVAILABLE,
                            rendered_value=TableCellRenderedValue("0.05"),
                            evidence=EvidenceText("held-out"),
                        ),
                    ),
                ),
            ),
            figures=(),
        ),
        tmp_path / "publication.md",
    )

    manifest = json.loads((tmp_path / PUBLICATION_SOURCE_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["publication"] == publication.name
    assert manifest["experiment"] == "shared_vs_local_confirmation"
    assert manifest["table_count"] == 1
