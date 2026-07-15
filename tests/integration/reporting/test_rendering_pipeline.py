from dataclasses import replace
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp_core.analysis.report_models import ReportColumn, ReportRow, TableSpecification
from datp_core.application.ports.reporting import RenderReportArtifactRequest
from datp_core.application.reporting.freeze import ResultFreezeEligibility
from datp_core.application.reporting.tracing import TableFigureTracer, TraceReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
)
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.protocols import ReportArtifactType, TableType
from datp_core.infrastructure.reporting.markdown import MarkdownReportRenderer


def _artifact(character: str, artifact_type: ArtifactType, format: SerializationFormat) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=format,
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "format",
    (SerializationFormat.MARKDOWN, SerializationFormat.CSV, SerializationFormat.PARQUET, SerializationFormat.JSON),
)
def test_synthetic_traced_table_renders_deterministically_without_value_loss(format: SerializationFormat) -> None:
    specification = TableSpecification(
        table_type=TableType.DISPERSION_LADDER,
        columns=(ReportColumn(key="cv_fpr", label="CV(FPR)"),),
        rows=(ReportRow(values=(Decimal("0.123456789012"),)),),
    )
    input_artifact = _artifact("a", ArtifactType.TABLE_INPUT, SerializationFormat.JSON)
    trace = TableFigureTracer().trace(
        TraceReportArtifactRequest(
            output=_artifact("b", ArtifactType.RENDERED_TABLE, format),
            specification=specification,
            required_inputs=ArtifactReferenceCollection(references=(input_artifact,)),
            provenance_chain=ArtifactReferenceCollection(references=(input_artifact,)),
            result_freeze=ResultFreezeEligibility(
                result_freeze=_artifact("c", ArtifactType.RESULT_FREEZE, SerializationFormat.JSON),
                readiness=ScientificReadinessResult(blockers=()),
            ),
        )
    )
    request = RenderReportArtifactRequest(
        traced_specification=trace,
        artifact_type=ReportArtifactType.MAIN_TABLE,
        format=format,
    )

    first = MarkdownReportRenderer().render(request)
    second = MarkdownReportRenderer().render(replace(request))

    assert first.content == second.content
    if format is SerializationFormat.PARQUET:
        assert first.content.startswith(b"PAR1")
        assert pq.read_table(pa.BufferReader(first.content)).column(0).to_pylist() == [Decimal("0.123456789012")]
    else:
        assert b"0.123456789012" in first.content
    assert first.artifact is trace.output
