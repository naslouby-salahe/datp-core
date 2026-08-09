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
