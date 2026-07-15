import csv
import json
from decimal import Decimal
from io import StringIO

import pyarrow as pa
import pyarrow.parquet as pq

from datp_core.analysis.report_models import ReportValue, TableSpecification
from datp_core.analysis.wording import ClaimWording
from datp_core.application.ports.reporting import RenderedReportArtifact, RenderReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import ReportingError
from datp_core.domain.experiments.protocols import ReportArtifactType


class MarkdownReportRenderer:
    def render(self, request: RenderReportArtifactRequest) -> RenderedReportArtifact:
        _validate_markdown_request(request)
        specification = request.traced_specification.specification
        if isinstance(specification, TableSpecification):
            content = _render_table(specification, request.format)
        elif isinstance(specification, ClaimWording):
            content = specification.template
        else:
            raise _rendering_error(request, "Markdown renderer accepts tables and wording blocks only")
        rendered_content = content if isinstance(content, bytes) else content.encode()
        return RenderedReportArtifact(artifact=request.traced_specification.output, content=rendered_content)


def _validate_markdown_request(request: RenderReportArtifactRequest) -> None:
    allowed_formats = (
        SerializationFormat.MARKDOWN,
        SerializationFormat.CSV,
        SerializationFormat.PARQUET,
        SerializationFormat.JSON,
    )
    if request.format not in allowed_formats:
        raise _rendering_error(request, "Markdown renderer received an unsupported serialization format")
    specification = request.traced_specification.specification
    if isinstance(specification, TableSpecification):
        _validate_table_request(request)
        return
    if isinstance(specification, ClaimWording):
        _validate_wording_request(request)
        return
    raise _rendering_error(request, "Markdown renderer accepts tables and wording blocks only")


def _validate_table_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.RENDERED_TABLE:
        raise _rendering_error(request, "traced output artifact type does not match the table specification")
    if request.artifact_type not in {ReportArtifactType.MAIN_TABLE, ReportArtifactType.SUPPLEMENT_TABLE}:
        raise _rendering_error(request, "table specification received a non-table report artifact type")


def _validate_wording_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.WORDING_OUTPUT:
        raise _rendering_error(request, "traced output artifact type does not match the wording specification")
    if request.artifact_type is not ReportArtifactType.WORDING_BLOCK:
        raise _rendering_error(request, "wording specification received a non-wording report artifact type")


def _render_table(specification: TableSpecification, format: SerializationFormat) -> str | bytes:
    if format is SerializationFormat.MARKDOWN:
        return _markdown_table(specification)
    if format is SerializationFormat.CSV:
        return _csv_table(specification)
    if format is SerializationFormat.PARQUET:
        return _parquet_table(specification)
    return _json_table(specification)


def _markdown_table(specification: TableSpecification) -> str:
    header = "| " + " | ".join(column.label for column in specification.columns) + " |"
    separator = "| " + " | ".join("---" for _ in specification.columns) + " |"
    rows = tuple("| " + " | ".join(str(value) for value in row.values) + " |" for row in specification.rows)
    return "\n".join((header, separator, *rows))


def _csv_table(specification: TableSpecification) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(tuple(column.key for column in specification.columns))
    writer.writerows(tuple(tuple(str(value) for value in row.values) for row in specification.rows))
    return output.getvalue().removesuffix("\n")


def _json_table(specification: TableSpecification) -> str:
    return json.dumps(
        {
            "columns": tuple(column.key for column in specification.columns),
            "rows": tuple(tuple(_json_value(value) for value in row.values) for row in specification.rows),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _json_value(value: ReportValue) -> str | int | float:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _parquet_table(specification: TableSpecification) -> bytes:
    values_by_column = {
        column.key: [row.values[index] for row in specification.rows]
        for index, column in enumerate(specification.columns)
    }
    buffer = pa.BufferOutputStream()
    pq.write_table(pa.table(values_by_column), buffer)
    return buffer.getvalue().to_pybytes()


def _rendering_error(request: RenderReportArtifactRequest, cause: str) -> ReportingError:
    return ReportingError(
        detail="report rendering failed", output_id=request.traced_specification.output.artifact_id.value, cause=cause
    )
