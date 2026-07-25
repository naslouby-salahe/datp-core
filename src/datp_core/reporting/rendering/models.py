"""Typed rendered output models."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class RenderedTable:
    """A rendered table artifact with Markdown and LaTeX representations."""

    identifier: str
    artifact_type: str
    table_type: str
    markdown: str
    latex: str


@define(frozen=True, slots=True, kw_only=True)
class RenderedFigure:
    """A rendered figure artifact with PNG and PDF base64-encoded representations."""

    identifier: str
    artifact_type: str
    figure_type: str
    png_base64: str
    pdf_base64: str


@define(frozen=True, slots=True, kw_only=True)
class RenderedReportPackage:
    """A complete rendered report package with all table and figure artifacts."""

    schema_version: int
    experiment_id: str
    scientific_fingerprint: str
    source_files: tuple[dict[str, str], ...]
    rendered_artifacts: tuple[dict[str, object], ...]
