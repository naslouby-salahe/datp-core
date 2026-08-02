"""Seed-paired confirmatory, external, and temporal-boundary analysis publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.descriptive import DescriptiveSummary, QuantileRange, summarize_values
from datp_core.analysis.inference.bootstrap import (
    decide_confirmatory,
    external_paired_bca_interval,
    paired_bca_interval,
)
from datp_core.analysis.inference.paired import (
    holm_adjust,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
    sign_consistency,
)
from datp_core.analysis.mechanisms import MechanismResult
from datp_core.analysis.models import (
    BootstrapInterval,
    ExternalPairedAnalysisPlan,
    MultiplicityResult,
    PairedContrast,
    PairedDifferenceCounts,
    RankBiserialResult,
    ScientificDecisionResult,
    WilcoxonResult,
)
from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    validate_frozen_recalibrated_pair,
)
from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PopulationId,
    PublicationStatus,
    StageOperationId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BootstrapReplicateCount,
    Checksum,
    Ratio,
    Seed,
    checksum_file,
    checksum_text,
)
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.protocols.models import StatisticalInferenceProtocol


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    COMPLETE = "COMPLETE"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


class AnalysisDocument(StrictModel):
    interval: BootstrapInterval
    decision: ScientificDecisionResult
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    multiplicity: MultiplicityResult | None
    multiplicity_availability: AvailabilityStatus
    multiplicity_reason: str
    mechanisms: tuple[MechanismResult, ...]


class ExternalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult


class TemporalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]


@dataclass(frozen=True, slots=True)
class AnalyzeRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: StatisticalInferenceProtocol
    bootstrap_replicates: BootstrapReplicateCount
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool
    secondary_family_name: str | None = None
    secondary_p_values: tuple[float, ...] = ()
    secondary_alpha: Ratio | None = None
    mechanisms: tuple[MechanismResult, ...] = ()

    def __post_init__(self) -> None:
        complete_secondary_family = (
            self.secondary_family_name is not None
            and bool(self.secondary_p_values)
            and self.secondary_alpha is not None
        )
        if complete_secondary_family:
            return
        if self.secondary_family_name is not None or self.secondary_p_values or self.secondary_alpha is not None:
            raise ValueError("secondary multiplicity requires a complete predeclared family")


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    interval: BootstrapInterval
    decision: ScientificDecisionResult
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    multiplicity: MultiplicityResult | None
    multiplicity_availability: AvailabilityStatus
    multiplicity_reason: str
    mechanisms: tuple[MechanismResult, ...]
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: ExternalPairedAnalysisPlan
    bootstrap_replicates: BootstrapReplicateCount
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    complete_digest: Checksum


@dataclass(frozen=True, slots=True)
class TemporalAnalyzeRequest:
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TemporalAnalyzeResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    records: tuple[TemporalRecoveryResult, ...]
    complete_digest: Checksum


_DEFAULT_QUANTILES = QuantileRange(lower=Ratio(0.25), upper=Ratio(0.75))


def analyze_stage(request: AnalyzeRequest) -> AnalyzeResult:
    interval = paired_bca_interval(
        request.contrasts,
        protocol=request.inference_protocol,
        replicate_count=request.bootstrap_replicates,
        analysis_seed=request.analysis_seed,
    )
    result = _analyze(request, interval)
    document = AnalysisDocument(
        interval=result.interval,
        decision=result.decision,
        descriptive=result.descriptive,
        sign_consistency=result.sign_consistency,
        wilcoxon=result.wilcoxon,
        rank_biserial=result.rank_biserial,
        multiplicity=result.multiplicity,
        multiplicity_availability=result.multiplicity_availability,
        multiplicity_reason=result.multiplicity_reason,
        mechanisms=result.mechanisms,
    )
    payload = document.model_dump_json(indent=2) + "\n"
    digest = checksum_text(payload)

    def write(temporary: Path) -> None:
        (temporary / AnalysisAssetName.DOCUMENT).write_text(payload, encoding="utf-8")
        (temporary / AnalysisAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, document, digest),
            write=write,
            remove_target=rmtree,
        )
    )
    persisted = _read_document(request.output_directory) if reused else document
    return _result_from_document(
        persisted, PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED, request.output_directory
    )


def analyze_external_stage(request: ExternalAnalyzeRequest) -> ExternalAnalyzeResult:
    identity = require_execution_identity(request.execution_identity, request.plan.population)
    if identity is None:
        raise RuntimeError("external analysis requires an execution identity")
    identity.require_evidence_role(request.plan.evidence_role)
    interval = external_paired_bca_interval(
        request.contrasts,
        plan=request.plan,
        replicate_count=request.bootstrap_replicates,
        analysis_seed=request.analysis_seed,
    )
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    descriptive = summarize_values(
        deltas,
        evidence_role=request.plan.evidence_role,
        unavailable_count=0,
        excluded_count=0,
        quantiles=_DEFAULT_QUANTILES,
    )
    document = ExternalAnalysisDocument(
        evidence_role=request.plan.evidence_role,
        interval=interval,
        descriptive=descriptive,
        sign_consistency=sign_consistency(request.contrasts),
        wilcoxon=paired_wilcoxon(request.contrasts),
        rank_biserial=matched_pairs_rank_biserial(request.contrasts),
    )
    payload = document.model_dump_json(indent=2) + "\n"
    digest = checksum_text(payload)
    reused = publish_atomically(
        AtomicPublication(
            request.output_directory,
            request.overwrite,
            lambda directory: _is_external_reusable(directory, digest),
            lambda temporary: _write_external_analysis(temporary, payload, digest),
            rmtree,
        )
    )
    return ExternalAnalyzeResult(
        StageOperationId.ANALYZE,
        PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED,
        interval,
        descriptive,
        document.sign_consistency,
        document.wilcoxon,
        document.rank_biserial,
        checksum_file(request.output_directory / AnalysisAssetName.COMPLETE),
    )


def analyze_temporal_stage(request: TemporalAnalyzeRequest) -> TemporalAnalyzeResult:
    _validate_temporal_identities(request)
    _validate_temporal_provenance(request)
    document = TemporalAnalysisDocument(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        static_reference_provenance=request.static_reference_provenance,
        frozen_provenance=request.frozen_provenance,
        recalibrated_provenance=request.recalibrated_provenance,
        records=request.records,
    )
    payload = document.model_dump_json(indent=2) + "\n"
    digest = checksum_text(payload)
    reused = publish_atomically(
        AtomicPublication(
            request.output_directory,
            request.overwrite,
            lambda directory: _is_temporal_reusable(directory, digest),
            lambda temporary: _write_temporal_analysis(temporary, payload, digest),
            rmtree,
        )
    )
    return TemporalAnalyzeResult(
        stage=StageOperationId.ANALYZE,
        publication_status=PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED,
        records=request.records,
        complete_digest=checksum_file(request.output_directory / AnalysisAssetName.COMPLETE),
    )


def _analyze(request: AnalyzeRequest, interval: BootstrapInterval) -> AnalyzeResult:
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    multiplicity, multiplicity_availability, multiplicity_reason = _multiplicity(request)
    return AnalyzeResult(
        stage=StageOperationId.ANALYZE,
        publication_status=PublicationStatus.PUBLISHED,
        interval=interval,
        decision=decide_confirmatory(interval),
        descriptive=summarize_values(
            deltas,
            evidence_role=EvidenceRole.CONFIRMATORY,
            unavailable_count=0,
            excluded_count=0,
            quantiles=_DEFAULT_QUANTILES,
        ),
        sign_consistency=sign_consistency(request.contrasts),
        wilcoxon=paired_wilcoxon(request.contrasts),
        rank_biserial=matched_pairs_rank_biserial(request.contrasts),
        multiplicity=multiplicity,
        multiplicity_availability=multiplicity_availability,
        multiplicity_reason=multiplicity_reason,
        mechanisms=request.mechanisms,
        complete_digest=checksum_text("unpublished"),
    )


def _multiplicity(request: AnalyzeRequest) -> tuple[MultiplicityResult | None, AvailabilityStatus, str]:
    if not request.secondary_p_values:
        return None, AvailabilityStatus.UNAVAILABLE, "no predeclared secondary multiplicity family"
    if request.secondary_family_name is None or request.secondary_alpha is None:
        raise ValueError("secondary multiplicity requires a complete predeclared family")
    return (
        holm_adjust(
            request.secondary_p_values, family_name=request.secondary_family_name, alpha=request.secondary_alpha
        ),
        AvailabilityStatus.AVAILABLE,
        "",
    )


def _read_document(directory: Path) -> AnalysisDocument:
    return AnalysisDocument.model_validate_json((directory / AnalysisAssetName.DOCUMENT).read_text(encoding="utf-8"))


def _result_from_document(
    document: AnalysisDocument, publication_status: PublicationStatus, directory: Path
) -> AnalyzeResult:
    return AnalyzeResult(
        stage=StageOperationId.ANALYZE,
        publication_status=publication_status,
        interval=document.interval,
        decision=document.decision,
        descriptive=document.descriptive,
        sign_consistency=document.sign_consistency,
        wilcoxon=document.wilcoxon,
        rank_biserial=document.rank_biserial,
        multiplicity=document.multiplicity,
        multiplicity_availability=document.multiplicity_availability,
        multiplicity_reason=document.multiplicity_reason,
        mechanisms=document.mechanisms,
        complete_digest=checksum_file(directory / AnalysisAssetName.COMPLETE),
    )


def _is_reusable(directory: Path, expected_document: AnalysisDocument, digest: Checksum) -> bool:
    complete = directory / AnalysisAssetName.COMPLETE
    document = directory / AnalysisAssetName.DOCUMENT
    if not complete.is_file() or not document.is_file() or complete.read_text(encoding="utf-8").strip() != digest.value:
        return False
    try:
        persisted = _read_document(directory)
    except ValueError:
        return False
    return persisted == expected_document


def _is_external_reusable(directory: Path, digest: Checksum) -> bool:
    return _is_matching_document(directory, AnalysisAssetName.EXTERNAL_DOCUMENT, ExternalAnalysisDocument, digest)


def _is_temporal_reusable(directory: Path, digest: Checksum) -> bool:
    return _is_matching_document(directory, AnalysisAssetName.TEMPORAL_DOCUMENT, TemporalAnalysisDocument, digest)


def _is_matching_document(
    directory: Path,
    asset_name: AnalysisAssetName,
    document_type: type[ExternalAnalysisDocument] | type[TemporalAnalysisDocument],
    digest: Checksum,
) -> bool:
    complete = directory / AnalysisAssetName.COMPLETE
    document = directory / asset_name
    if not complete.is_file() or not document.is_file() or complete.read_text(encoding="utf-8").strip() != digest.value:
        return False
    try:
        document_type.model_validate_json(document.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return checksum_text(document.read_text(encoding="utf-8")) == digest


def _write_external_analysis(temporary: Path, payload: str, digest: Checksum) -> None:
    (temporary / AnalysisAssetName.EXTERNAL_DOCUMENT).write_text(payload, encoding="utf-8")
    (temporary / AnalysisAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")


def _write_temporal_analysis(temporary: Path, payload: str, digest: Checksum) -> None:
    (temporary / AnalysisAssetName.TEMPORAL_DOCUMENT).write_text(payload, encoding="utf-8")
    (temporary / AnalysisAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")


def _validate_temporal_provenance(request: TemporalAnalyzeRequest) -> None:
    static = request.static_reference_provenance
    if static.state is not TemporalState.STATIC_REFERENCE:
        raise ValueError("temporal analysis requires static-reference provenance")
    validate_frozen_recalibrated_pair(request.frozen_provenance, request.recalibrated_provenance)
    if static.checkpoint_checksum != request.frozen_provenance.checkpoint_checksum:
        raise ValueError("all temporal states must share one fitted detector")


def _validate_temporal_identities(request: TemporalAnalyzeRequest) -> None:
    bindings = (
        (request.static_reference_identity, TemporalState.STATIC_REFERENCE),
        (request.frozen_identity, TemporalState.FROZEN_FUTURE),
        (request.recalibrated_identity, TemporalState.RECALIBRATED_FUTURE),
    )
    for identity, expected_state in bindings:
        bound = require_execution_identity(identity, PopulationId.EDGE_TEMPORAL_GROUPS)
        if bound is None or bound.temporal_state is not expected_state:
            raise ScientificContractError("temporal analysis identity must match its deployment state")
