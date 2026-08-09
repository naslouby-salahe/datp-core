"""Shared typed experiment analysis report publication outcomes."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.core.identifiers import AnalysisMarkerText, AnalysisReasonText
from datp_core.core.numeric import SeedObservationCount


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisReportPublication:
    directories: tuple[Path, ...]
    detail: AnalysisReasonText


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisReportFinalizationInput:
    directory: Path
    marker: Path
    missing_count: SeedObservationCount
    marker_text: AnalysisMarkerText


def finalize_analysis_report(request: AnalysisReportFinalizationInput) -> AnalysisReportPublication:
    if request.missing_count.value == 0:
        request.marker.write_text(f"{request.marker_text}\n", encoding="utf-8")
        return AnalysisReportPublication(
            directories=(request.directory,),
            detail=AnalysisReasonText(str(request.marker_text)),
        )
    return AnalysisReportPublication(
        directories=(request.directory,),
        detail=AnalysisReasonText(f"{request.marker_text} ({request.missing_count.value} seed(s) missing)"),
    )
