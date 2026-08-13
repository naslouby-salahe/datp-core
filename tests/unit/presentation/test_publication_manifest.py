import json
from csv import DictReader
from pathlib import Path

from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole, ExperimentId, MetricId, PopulationId
from datp_core.presentation.export import (
    PUBLICATION_SOURCE_DATA_FILENAME,
    PUBLICATION_SOURCE_MANIFEST_FILENAME,
    PublicationBundle,
    ReportProvenance,
    export_markdown,
)
from datp_core.presentation.tables import EvidenceText, PublicationTable, TableCell, TableCellRenderedValue, TableTitle


def test_publication_export_writes_traceable_source_manifest(tmp_path: Path) -> None:
    temporal_source = tmp_path / "temporal_source.csv"
    temporal_source.write_text("seed,value\n0,0.05\n", encoding="utf-8")
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
        additional_source_files=(temporal_source,),
    )

    manifest = json.loads((tmp_path / PUBLICATION_SOURCE_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["publication"] == publication.name
    assert manifest["experiment"] == "shared_vs_local_confirmation"
    assert manifest["table_count"] == 1
    assert manifest["sources"] == [
        {"filename": PUBLICATION_SOURCE_DATA_FILENAME, "kind": "table_figure_source_data", "row_count": 1},
        {"filename": "temporal_source.csv", "kind": "additional_figure_table_source", "row_count": 1},
    ]
    with (tmp_path / PUBLICATION_SOURCE_DATA_FILENAME).open(encoding="utf-8", newline="") as stream:
        rows = tuple(DictReader(stream))
    assert rows == (
        {
            "output_kind": "table",
            "output_title": "summary",
            "series_label": "",
            "metric": "false_positive_rate",
            "availability": "available",
            "value_index": "",
            "x_value": "",
            "y_value": "0.05",
            "point_label": "",
            "evidence": "held-out",
            "unavailable_reason": "",
        },
    )
