from dataclasses import dataclass

from datp_core.analysis.report_models import (
    FigureSpecification,
    HeatmapFigureSpecification,
    SeriesFigureSpecification,
    TableSpecification,
)
from datp_core.analysis.wording import ClaimWording
from datp_core.domain.artifacts.references import ArtifactRef, ArtifactReferenceCollection
from datp_core.domain.errors import DomainValidationError

type ReportSpecification = TableSpecification | FigureSpecification | ClaimWording


@dataclass(frozen=True, slots=True, kw_only=True)
class TracedReportSpecification:
    output: ArtifactRef
    result_freeze: ArtifactRef
    provenance_chain: ArtifactReferenceCollection
    specification: ReportSpecification

    def __post_init__(self) -> None:
        if not _has_traced_specification_components(self):
            raise DomainValidationError(
                detail="traced report specifications require typed artifacts, provenance, and a report specification",
                value=repr(self),
                constraint="ArtifactRef, ArtifactReferenceCollection, and ReportSpecification",
            )


def _has_traced_specification_components(traced: TracedReportSpecification) -> bool:
    return all(
        (
            type(traced.output) is ArtifactRef,
            type(traced.result_freeze) is ArtifactRef,
            type(traced.provenance_chain) is ArtifactReferenceCollection,
            is_report_specification(traced.specification),
        )
    )


def is_report_specification(specification: object) -> bool:
    return isinstance(
        specification,
        (TableSpecification, SeriesFigureSpecification, HeatmapFigureSpecification, ClaimWording),
    )
