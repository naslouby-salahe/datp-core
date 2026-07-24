"""Reporting profile enums."""

from __future__ import annotations

from enum import StrEnum


class ReportArtifactType(StrEnum):
    TABLE = "table"
    FIGURE = "figure"


class ReportTableType(StrEnum):
    PAIRED_DIFFERENCE = "paired_difference"


class ReportFigureType(StrEnum):
    SEED_DIFFERENCE_SERIES = "seed_difference_series"


class ReportOutputFormat(StrEnum):
    MARKDOWN = "markdown"
    LATEX = "latex"
    PNG = "png"
    PDF = "pdf"


class MissingValuePolicy(StrEnum):
    UNAVAILABLE = "unavailable"
