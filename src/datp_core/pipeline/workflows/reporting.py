"""Final report publication through validated reporting contracts."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.reporting.export import PublicationBundle, export_markdown


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishReportRequest:
    bundle: PublicationBundle
    destination: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishReportResult:
    destination: Path


def publish_report(request: PublishReportRequest) -> PublishReportResult:
    destination = export_markdown(request.bundle, request.destination)
    return PublishReportResult(destination=destination)
