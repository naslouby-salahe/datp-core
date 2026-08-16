import csv
from dataclasses import dataclass
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import cast

from datp_core.artifacts.serializers.json import canonical_value, serialize_json_model
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import AnalysisMarkerText, AnalysisReasonText, FileContentText
from datp_core.core.numeric import SeedObservationCount
from datp_core.runtime.filesystem import write_text_atomically


class ResultTableAssetName(StrEnum):
    RESULTS_TABLE = "results.csv"


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisReportPublication:
    directories: tuple[Path, ...]
    detail: AnalysisReasonText


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisReportFinalizationInput:
    directory: Path
    missing_count: SeedObservationCount
    marker_text: AnalysisMarkerText


def persist_result_document(model: StrictModel, json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    serialize_json_model(model, json_path)
    raw_rows: object = getattr(model, "rows", None)
    if not isinstance(raw_rows, tuple) or not raw_rows:
        raw_rows = getattr(model, "observations", None)
    if not isinstance(raw_rows, tuple) or not raw_rows:
        return
    entries = cast(tuple[object, ...], raw_rows)
    models: list[StrictModel] = []
    for raw_item in entries:
        if not isinstance(raw_item, StrictModel):
            return
        models.append(raw_item)
    if not models:
        return
    field_names = tuple(type(models[0]).model_fields)
    serialized_rows = tuple(_csv_row(item, field_names) for item in models)
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(field_names)
    writer.writerows(serialized_rows)
    write_text_atomically(
        json_path.with_name(ResultTableAssetName.RESULTS_TABLE),
        FileContentText(buffer.getvalue()),
    )


def finalize_analysis_report(request: AnalysisReportFinalizationInput) -> AnalysisReportPublication:
    if request.missing_count.value == 0:
        return AnalysisReportPublication(
            directories=(request.directory,),
            detail=AnalysisReasonText(str(request.marker_text)),
        )
    return AnalysisReportPublication(
        directories=(request.directory,),
        detail=AnalysisReasonText(f"{request.marker_text} ({request.missing_count.value} seed(s) missing)"),
    )


def _csv_row(model: StrictModel, field_names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_csv_cell(getattr(model, name)) for name in field_names)


def _csv_cell(value: object) -> str:
    rendered = canonical_value(value)
    if rendered is None or isinstance(rendered, (dict, list, tuple)):
        return ""
    return str(rendered)
