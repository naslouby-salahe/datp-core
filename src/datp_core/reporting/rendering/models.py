"""Typed rendered output models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RenderedTable(BaseModel):
    """A rendered table artifact with Markdown and LaTeX representations."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    artifact_type: str
    table_type: str
    markdown: str
    latex: str


class RenderedFigure(BaseModel):
    """A rendered figure artifact with PNG and PDF base64-encoded representations."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    artifact_type: str
    figure_type: str
    png_base64: str
    pdf_base64: str


class RenderedReportPackage(BaseModel):
    """A complete rendered report package with all table and figure artifacts."""

    model_config = ConfigDict(frozen=True)

    schema_version: int
    experiment_id: str
    scientific_fingerprint: str
    source_files: tuple[dict[str, str], ...]
    rendered_artifacts: tuple[dict[str, object], ...]
