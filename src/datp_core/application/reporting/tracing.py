from dataclasses import dataclass
from enum import StrEnum

from datp_core.application.reporting.contracts import (
    ReportSpecification,
    TracedReportSpecification,
    is_report_specification,
)
from datp_core.application.reporting.freeze import ResultFreezeEligibility, ResultFreezeEligibilityValidator
from datp_core.domain.artifacts.references import ArtifactRef, ArtifactReferenceCollection
from datp_core.domain.errors import DomainValidationError, ProvenanceError


class RenderingStatus(StrEnum):
    PENDING = "pending"
    RENDERED = "rendered"
    TRACE_REFUSED = "trace_refused"


@dataclass(frozen=True, slots=True, kw_only=True)
class TraceReportArtifactRequest:
    output: ArtifactRef
    specification: ReportSpecification
    required_inputs: ArtifactReferenceCollection
    provenance_chain: ArtifactReferenceCollection
    result_freeze: ResultFreezeEligibility

    def __post_init__(self) -> None:
        if not _is_trace_request_typed(self):
            raise DomainValidationError(
                detail="report tracing requires typed output, input closure, and result-freeze eligibility",
                value=repr(self),
                constraint="ArtifactRef, ArtifactReferenceCollection, ResultFreezeEligibility",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TableFigureTracer:
    def trace(self, request: TraceReportArtifactRequest) -> TracedReportSpecification:
        ResultFreezeEligibilityValidator().validate(eligibility=request.result_freeze)
        missing_inputs = tuple(
            reference
            for reference in request.required_inputs.references
            if reference not in request.provenance_chain.references
        )
        if missing_inputs:
            raise ProvenanceError(
                detail="report output cannot render before every required provenance input closes",
                output_id=request.output.artifact_id.value,
                missing_inputs=repr(missing_inputs),
            )
        return TracedReportSpecification(
            output=request.output,
            result_freeze=request.result_freeze.result_freeze,
            provenance_chain=request.provenance_chain,
            specification=request.specification,
        )


def _is_trace_request_typed(request: TraceReportArtifactRequest) -> bool:
    return all(
        (
            type(request.output) is ArtifactRef,
            is_report_specification(request.specification),
            type(request.required_inputs) is ArtifactReferenceCollection,
            type(request.provenance_chain) is ArtifactReferenceCollection,
            type(request.result_freeze) is ResultFreezeEligibility,
        )
    )
