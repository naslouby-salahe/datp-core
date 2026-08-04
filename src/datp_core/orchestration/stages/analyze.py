"""Paired confirmatory, supplementary, and temporal-boundary analysis publication."""

from dataclasses import dataclass
from enum import StrEnum
from json import dumps
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

from pydantic import model_validator

from datp_core.analysis.descriptive import (
    DescriptiveSummary,
    ObservationCounts,
    QuantileRange,
    count_paired_differences,
    summarize_values,
)
from datp_core.analysis.inference.bootstrap import (
    decide_confirmatory,
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.inference.paired import holm_adjust, matched_pairs_rank_biserial, paired_wilcoxon
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.models import (
    BootstrapInterval,
    MultiplicityPlan,
    MultiplicityResult,
    PairedContrast,
    PairedDifferenceCounts,
    RankBiserialResult,
    ScientificDecisionResult,
    SupplementaryPairedAnalysisPlan,
    WilcoxonResult,
)
from datp_core.analysis.temporal import (
    TemporalAnalysisRecord,
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    temporal_analysis_record,
    validate_frozen_recalibrated_pair,
)
from datp_core.artifacts.store import PublicationOutcome, publish_atomically
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, PopulationId, PublicationStatus, StageOperationId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_value
from datp_core.domain.values import Checksum, PairedObservationCount, Seed, checksum_text
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.protocols.statistics import PairedInferenceProtocol


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    COMPLETE = "COMPLETE"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


@dataclass(frozen=True, slots=True)
class AnalyzeRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()


class AnalysisDocument(StrictModel):
    inference_protocol: PairedInferenceProtocol
    interval: BootstrapInterval
    decision: ScientificDecisionResult
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    multiplicity_plan: MultiplicityPlan | None
    multiplicity_result: MultiplicityResult | None
    mechanisms: tuple[MechanismEvidence, ...]

    @model_validator(mode="after")
    def validate_multiplicity(self) -> "AnalysisDocument":
        if (self.multiplicity_plan is None) != (self.multiplicity_result is None):
            raise ValueError("multiplicity plan and result must occur together")
        return self


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: AnalysisDocument
    complete_digest: Checksum

    @property
    def interval(self) -> BootstrapInterval:
        return self.document.interval

    @property
    def decision(self) -> ScientificDecisionResult:
        return self.document.decision

    @property
    def descriptive(self) -> DescriptiveSummary:
        return self.document.descriptive

    @property
    def sign_consistency(self) -> PairedDifferenceCounts:
        return self.document.sign_consistency

    @property
    def wilcoxon(self) -> WilcoxonResult:
        return self.document.wilcoxon

    @property
    def rank_biserial(self) -> RankBiserialResult:
        return self.document.rank_biserial

    @property
    def multiplicity(self) -> MultiplicityResult | None:
        return self.document.multiplicity_result

    @property
    def mechanisms(self) -> tuple[MechanismEvidence, ...]:
        return self.document.mechanisms


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool


class ExternalAnalysisDocument(StrictModel):
    plan: SupplementaryPairedAnalysisPlan
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult


@dataclass(frozen=True, slots=True)
class ExternalAnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: ExternalAnalysisDocument
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


class TemporalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalAnalysisRecord, ...]

    @model_validator(mode="after")
    def validate_role(self) -> "TemporalAnalysisDocument":
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal analysis must remain temporal-boundary evidence")
        return self


@dataclass(frozen=True, slots=True)
class TemporalAnalyzeResult:
    stage: ClassVar[StageOperationId] = StageOperationId.ANALYZE
    publication_status: PublicationStatus
    document: TemporalAnalysisDocument
    complete_digest: Checksum

    @property
    def records(self) -> tuple[TemporalAnalysisRecord, ...]:
        return self.document.records


def analyze_stage(request: AnalyzeRequest) -> AnalyzeResult:
    document = _analyze(request)
    outcome = _publish(request.output_directory, request.overwrite, AnalysisAssetName.DOCUMENT, document)
    return AnalyzeResult(outcome.status, outcome.value, outcome.complete_digest)


def analyze_external_stage(request: ExternalAnalyzeRequest) -> ExternalAnalyzeResult:
    identity = require_execution_identity(request.execution_identity, request.plan.population)
    if identity is None:
        raise RuntimeError("external analysis requires an execution identity")
    identity.require_evidence_role(request.plan.evidence_role)
    protocol = request.plan.inference_protocol
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    document = ExternalAnalysisDocument(
        plan=request.plan,
        interval=supplementary_paired_bca_interval(
            request.contrasts,
            plan=request.plan,
            analysis_seed=request.analysis_seed,
        ),
        descriptive=summarize_values(
            deltas,
            evidence_role=request.plan.evidence_role,
            counts=_zero_counts(),
            quantiles=_quantile_range(protocol),
        ),
        sign_consistency=count_paired_differences(deltas),
        wilcoxon=paired_wilcoxon(request.contrasts, protocol),
        rank_biserial=matched_pairs_rank_biserial(request.contrasts, protocol),
    )
    outcome = _publish(request.output_directory, request.overwrite, AnalysisAssetName.EXTERNAL_DOCUMENT, document)
    return ExternalAnalyzeResult(outcome.status, outcome.value, outcome.complete_digest)


def analyze_temporal_stage(request: TemporalAnalyzeRequest) -> TemporalAnalyzeResult:
    _validate_temporal_identities(request)
    _validate_temporal_provenance(request)
    document = TemporalAnalysisDocument(
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        static_reference_provenance=request.static_reference_provenance,
        frozen_provenance=request.frozen_provenance,
        recalibrated_provenance=request.recalibrated_provenance,
        records=tuple(temporal_analysis_record(record) for record in request.records),
    )
    outcome = _publish(request.output_directory, request.overwrite, AnalysisAssetName.TEMPORAL_DOCUMENT, document)
    return TemporalAnalyzeResult(outcome.status, outcome.value, outcome.complete_digest)


def _analyze(request: AnalyzeRequest) -> AnalysisDocument:
    protocol = request.inference_protocol
    interval = paired_bca_interval(request.contrasts, protocol=protocol, analysis_seed=request.analysis_seed)
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    multiplicity = None if request.multiplicity_plan is None else holm_adjust(request.multiplicity_plan, protocol)
    return AnalysisDocument(
        inference_protocol=protocol,
        interval=interval,
        decision=decide_confirmatory(interval),
        descriptive=summarize_values(
            deltas,
            evidence_role=EvidenceRole.CONFIRMATORY,
            counts=_zero_counts(),
            quantiles=_quantile_range(protocol),
        ),
        sign_consistency=count_paired_differences(deltas),
        wilcoxon=paired_wilcoxon(request.contrasts, protocol),
        rank_biserial=matched_pairs_rank_biserial(request.contrasts, protocol),
        multiplicity_plan=request.multiplicity_plan,
        multiplicity_result=multiplicity,
        mechanisms=request.mechanisms,
    )


def _quantile_range(protocol: PairedInferenceProtocol) -> QuantileRange:
    return QuantileRange(lower=protocol.descriptive_lower_quantile, upper=protocol.descriptive_upper_quantile)


def _zero_counts() -> ObservationCounts:
    return ObservationCounts(unavailable=PairedObservationCount(0), excluded=PairedObservationCount(0))


def _publish[T](directory: Path, overwrite: bool, asset_name: AnalysisAssetName, document: T) -> PublicationOutcome[T]:
    payload = dumps(canonical_value(document), indent=2, sort_keys=True) + "\n"
    digest = checksum_text(payload)

    def write(temporary: Path) -> T:
        (temporary / asset_name).write_text(payload, encoding="utf-8")
        (temporary / AnalysisAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        return document

    return publish_atomically(
        target=directory,
        overwrite=overwrite,
        is_reusable=lambda target: _is_reusable(target, asset_name, digest),
        write=write,
        reusable_value=lambda _target: document,
        remove_target=rmtree,
    )


def _is_reusable(directory: Path, asset_name: AnalysisAssetName, digest: Checksum) -> bool:
    complete = directory / AnalysisAssetName.COMPLETE
    document = directory / asset_name
    return complete.is_file() and document.is_file() and complete.read_text(encoding="utf-8").strip() == digest.value


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
