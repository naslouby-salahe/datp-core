"""Seed-paired confirmatory, external, and temporal-boundary analysis publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

from datp_core.analysis.decision_rules import ScientificDecisionResult, decide_confirmatory
from datp_core.analysis.descriptive import DescriptiveSummary, PairedDifferenceCounts, summarize_values
from datp_core.analysis.inference import (
    BcaOutcome,
    BcaReason,
    BootstrapInterval,
    ExternalPairedAnalysisPlan,
    ExternalPairedContrast,
    MultiplicityResult,
    PairedContrast,
    RankBiserialResult,
    WilcoxonResult,
    external_paired_bca_interval,
    holm_adjust,
    matched_pairs_rank_biserial,
    paired_bca_interval,
    paired_wilcoxon,
    sign_consistency,
)
from datp_core.analysis.mechanisms import MechanismResult
from datp_core.analysis.temporal import (
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    validate_frozen_recalibrated_pair,
)
from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EffectSizeId,
    EvidenceRole,
    IntervalMethod,
    MultiplicityCorrectionId,
    PopulationId,
    PublicationStatus,
    ScientificDecision,
    StageOperationId,
    StatisticalTestId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    BootstrapReplicateCount,
    Checksum,
    ConfidenceLevel,
    MetricValue,
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
    interval_method: IntervalMethod
    confidence_level: ConfidenceLevel
    replicate_count: BootstrapReplicateCount
    analysis_seed: Seed
    point_estimate: MetricValue | None
    lower_bound: MetricValue | None
    upper_bound: MetricValue | None
    bias_correction: float | None
    acceleration: float | None
    interval_availability: AvailabilityStatus
    outcome: BcaOutcome
    reason: BcaReason
    decision: ScientificDecision
    decision_availability: AvailabilityStatus
    decision_rationale: str
    descriptive: "DescriptiveDocument"
    sign_consistency: "PairedDifferenceCountsDocument"
    wilcoxon: "WilcoxonDocument"
    rank_biserial: "RankBiserialDocument"
    multiplicity: "MultiplicityDocument"
    mechanisms: tuple["MechanismDocument", ...]


class ExternalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    interval_method: IntervalMethod
    confidence_level: ConfidenceLevel
    replicate_count: BootstrapReplicateCount
    analysis_seed: Seed
    point_estimate: MetricValue | None
    lower_bound: MetricValue | None
    upper_bound: MetricValue | None
    interval_availability: AvailabilityStatus
    outcome: BcaOutcome
    reason: BcaReason
    descriptive: "DescriptiveDocument"
    sign_consistency: "PairedDifferenceCountsDocument"
    wilcoxon: "WilcoxonDocument"
    rank_biserial: "RankBiserialDocument"


class TemporalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]


class DescriptiveDocument(StrictModel):
    evidence_role: EvidenceRole
    values: tuple[float, ...]
    available_count: int
    unavailable_count: int
    excluded_count: int
    mean: float | None
    median: float | None
    lower_quantile: float | None
    upper_quantile: float | None
    minimum: float | None
    maximum: float | None
    spread: float | None
    availability: AvailabilityStatus
    reason: str


class PairedDifferenceCountsDocument(StrictModel):
    positive: int
    zero: int
    negative: int


class WilcoxonDocument(StrictModel):
    test: StatisticalTestId
    alternative: str
    zero_method: str
    computation_method: str
    statistic: float | None
    p_value: float | None
    nonzero_pair_count: int
    availability: AvailabilityStatus
    reason: str


class RankBiserialDocument(StrictModel):
    effect_size: EffectSizeId
    value: float | None
    positive_rank_sum: float | None
    negative_rank_sum: float | None
    nonzero_pair_count: int
    availability: AvailabilityStatus
    reason: str


class MultiplicityDocument(StrictModel):
    correction: MultiplicityCorrectionId | None
    family_name: str | None
    raw_p_values: tuple[float, ...]
    adjusted_p_values: tuple[float, ...]
    rejected: tuple[bool, ...]
    availability: AvailabilityStatus
    reason: str


class MechanismDocument(StrictModel):
    evidence_role: EvidenceRole
    group_sizes: tuple[int, ...]
    within_group_threshold_spreads: tuple[MetricValue, ...]
    within_group_fpr_spreads: tuple[MetricValue, ...]
    across_group_threshold_spread: MetricValue | None
    across_group_mean_fpr_spread: MetricValue | None
    singleton_groups: tuple[int, ...]
    empty_groups: tuple[int, ...]
    recovery_fraction: MetricValue | None
    availability: AvailabilityStatus
    reason: str


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
    contrasts: tuple[ExternalPairedContrast, ...]
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


def analyze_stage(request: AnalyzeRequest) -> AnalyzeResult:
    """Run only declared seed-paired inference and preserve degenerate outcomes."""
    interval = paired_bca_interval(
        request.contrasts,
        protocol=request.inference_protocol,
        replicate_count=request.bootstrap_replicates,
        analysis_seed=request.analysis_seed,
    )
    result = _analyze(request, interval)
    document = _analysis_document(result)
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
    """Publish supplementary external evidence without a confirmatory decision."""
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
    deltas = tuple(contrast.delta.value for contrast in request.contrasts)
    descriptive = summarize_values(deltas, evidence_role=request.plan.evidence_role)
    signs = sign_consistency(request.contrasts)
    wilcoxon = paired_wilcoxon(request.contrasts)
    rank_biserial = matched_pairs_rank_biserial(request.contrasts)
    document = ExternalAnalysisDocument(
        evidence_role=request.plan.evidence_role,
        interval_method=interval.method,
        confidence_level=interval.confidence_level,
        replicate_count=interval.replicate_count,
        analysis_seed=interval.analysis_seed,
        point_estimate=interval.point_estimate,
        lower_bound=interval.lower_bound,
        upper_bound=interval.upper_bound,
        interval_availability=interval.availability,
        outcome=interval.outcome,
        reason=interval.reason,
        descriptive=_descriptive_document(descriptive),
        sign_consistency=PairedDifferenceCountsDocument(
            positive=signs.positive,
            zero=signs.zero,
            negative=signs.negative,
        ),
        wilcoxon=_wilcoxon_document(wilcoxon),
        rank_biserial=_rank_biserial_document(rank_biserial),
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
        signs,
        wilcoxon,
        rank_biserial,
        checksum_file(request.output_directory / AnalysisAssetName.COMPLETE),
    )


def analyze_temporal_stage(request: TemporalAnalyzeRequest) -> TemporalAnalyzeResult:
    """Publish one-shot temporal trajectories after enforcing the shared future evaluation binding."""
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
    deltas = tuple(contrast.delta.value for contrast in request.contrasts)
    multiplicity, multiplicity_availability, multiplicity_reason = _multiplicity(request)
    return AnalyzeResult(
        stage=StageOperationId.ANALYZE,
        publication_status=PublicationStatus.PUBLISHED,
        interval=interval,
        decision=decide_confirmatory(interval),
        descriptive=summarize_values(deltas, evidence_role=EvidenceRole.CONFIRMATORY),
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


def _analysis_document(result: AnalyzeResult) -> AnalysisDocument:
    interval = result.interval
    decision = result.decision
    return AnalysisDocument(
        interval_method=interval.method,
        confidence_level=interval.confidence_level,
        replicate_count=interval.replicate_count,
        analysis_seed=interval.analysis_seed,
        point_estimate=interval.point_estimate,
        lower_bound=interval.lower_bound,
        upper_bound=interval.upper_bound,
        bias_correction=interval.bias_correction,
        acceleration=interval.acceleration,
        interval_availability=interval.availability,
        outcome=interval.outcome,
        reason=interval.reason,
        decision=decision.decision,
        decision_availability=decision.availability,
        decision_rationale=decision.rationale,
        descriptive=_descriptive_document(result.descriptive),
        sign_consistency=PairedDifferenceCountsDocument(
            positive=result.sign_consistency.positive,
            zero=result.sign_consistency.zero,
            negative=result.sign_consistency.negative,
        ),
        wilcoxon=_wilcoxon_document(result.wilcoxon),
        rank_biserial=_rank_biserial_document(result.rank_biserial),
        multiplicity=_multiplicity_document(
            result.multiplicity, result.multiplicity_availability, result.multiplicity_reason
        ),
        mechanisms=tuple(_mechanism_document(item) for item in result.mechanisms),
    )


def _descriptive_document(result: DescriptiveSummary) -> DescriptiveDocument:
    return DescriptiveDocument(
        evidence_role=result.evidence_role,
        values=result.values,
        available_count=result.available_count,
        unavailable_count=result.unavailable_count,
        excluded_count=result.excluded_count,
        mean=result.mean,
        median=result.median,
        lower_quantile=result.lower_quantile,
        upper_quantile=result.upper_quantile,
        minimum=result.minimum,
        maximum=result.maximum,
        spread=result.spread,
        availability=result.availability,
        reason=result.reason,
    )


def _wilcoxon_document(result: WilcoxonResult) -> WilcoxonDocument:
    return WilcoxonDocument(
        test=result.test,
        alternative=result.alternative,
        zero_method=result.zero_method,
        computation_method=result.computation_method,
        statistic=result.statistic,
        p_value=result.p_value,
        nonzero_pair_count=result.nonzero_pair_count,
        availability=result.availability,
        reason=result.reason,
    )


def _rank_biserial_document(result: RankBiserialResult) -> RankBiserialDocument:
    return RankBiserialDocument(
        effect_size=result.effect_size,
        value=result.value,
        positive_rank_sum=result.positive_rank_sum,
        negative_rank_sum=result.negative_rank_sum,
        nonzero_pair_count=result.nonzero_pair_count,
        availability=result.availability,
        reason=result.reason,
    )


def _multiplicity_document(
    result: MultiplicityResult | None, availability: AvailabilityStatus, reason: str
) -> MultiplicityDocument:
    if result is None:
        return MultiplicityDocument(
            correction=None,
            family_name=None,
            raw_p_values=(),
            adjusted_p_values=(),
            rejected=(),
            availability=availability,
            reason=reason,
        )
    return MultiplicityDocument(
        correction=result.correction,
        family_name=result.family_name,
        raw_p_values=result.raw_p_values,
        adjusted_p_values=result.adjusted_p_values,
        rejected=result.rejected,
        availability=availability,
        reason=reason,
    )


def _mechanism_document(result: MechanismResult) -> MechanismDocument:
    return MechanismDocument(
        evidence_role=result.evidence_role,
        group_sizes=result.group_sizes,
        within_group_threshold_spreads=result.within_group_threshold_spreads,
        within_group_fpr_spreads=result.within_group_fpr_spreads,
        across_group_threshold_spread=result.across_group_threshold_spread,
        across_group_mean_fpr_spread=result.across_group_mean_fpr_spread,
        singleton_groups=result.singleton_groups,
        empty_groups=result.empty_groups,
        recovery_fraction=result.recovery_fraction,
        availability=result.availability,
        reason=result.reason,
    )


def _read_document(directory: Path) -> AnalysisDocument:
    return AnalysisDocument.model_validate_json((directory / AnalysisAssetName.DOCUMENT).read_text(encoding="utf-8"))


def _result_from_document(
    document: AnalysisDocument, publication_status: PublicationStatus, directory: Path
) -> AnalyzeResult:
    interval = BootstrapInterval(
        method=document.interval_method,
        confidence_level=document.confidence_level,
        replicate_count=document.replicate_count,
        analysis_seed=document.analysis_seed,
        point_estimate=document.point_estimate,
        lower_bound=document.lower_bound,
        upper_bound=document.upper_bound,
        bias_correction=document.bias_correction,
        acceleration=document.acceleration,
        availability=document.interval_availability,
        outcome=document.outcome,
        reason=document.reason,
    )
    decision = ScientificDecisionResult(
        evidence_role=EvidenceRole.CONFIRMATORY,
        decision=document.decision,
        point_estimate=interval.point_estimate,
        interval=interval,
        availability=document.decision_availability,
        rationale=document.decision_rationale,
    )
    multiplicity = _multiplicity_from_document(document.multiplicity)
    return AnalyzeResult(
        stage=StageOperationId.ANALYZE,
        publication_status=publication_status,
        interval=interval,
        decision=decision,
        descriptive=DescriptiveSummary(**document.descriptive.model_dump()),
        sign_consistency=PairedDifferenceCounts(**document.sign_consistency.model_dump()),
        wilcoxon=WilcoxonResult(**document.wilcoxon.model_dump()),
        rank_biserial=RankBiserialResult(**document.rank_biserial.model_dump()),
        multiplicity=multiplicity,
        multiplicity_availability=document.multiplicity.availability,
        multiplicity_reason=document.multiplicity.reason,
        mechanisms=tuple(MechanismResult(**item.model_dump()) for item in document.mechanisms),
        complete_digest=checksum_file(directory / AnalysisAssetName.COMPLETE),
    )


def _multiplicity_from_document(document: MultiplicityDocument) -> MultiplicityResult | None:
    if document.correction is None:
        return None
    if document.family_name is None:
        raise ValueError("available multiplicity output requires a family identity")
    return MultiplicityResult(
        correction=document.correction,
        family_name=document.family_name,
        raw_p_values=document.raw_p_values,
        adjusted_p_values=document.adjusted_p_values,
        rejected=document.rejected,
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
