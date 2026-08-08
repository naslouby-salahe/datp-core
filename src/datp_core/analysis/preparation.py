"""Preparation of confirmatory, external, and temporal analysis documents."""

from dataclasses import dataclass

from pydantic import model_validator

from datp_core.analysis.contrasts import PairedContrast, PairedDifferenceCounts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.descriptive import (
    DescriptiveSummary,
    ObservationCounts,
    QuantileRange,
    count_paired_differences,
    summarize_values,
)
from datp_core.analysis.inference.bootstrap.contracts import BcaReason, BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import (
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.inference.bootstrap.validation import (
    PairedAnalysisContractError,
    validate_confirmatory_contrasts,
    validate_supplementary_contrasts,
)
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.inference.multiplicity import MultiplicityPlan, MultiplicityResult, holm_adjust
from datp_core.analysis.inference.wilcoxon import (
    RankBiserialResult,
    WilcoxonResult,
    blocked_rank_biserial,
    blocked_wilcoxon,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
)
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.scientific_decision import ScientificDecision, ScientificDecisionResult, decide_confirmatory
from datp_core.analysis.temporal import (
    TemporalAnalysisRecord,
    TemporalDeploymentProvenance,
    TemporalRecoveryResult,
    decide_temporal_campaign,
    temporal_analysis_record,
    temporal_seed_series_intervals,
    validate_frozen_recalibrated_pair,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TemporalState,
)
from datp_core.core.numeric import PairedObservationCount, Seed
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT


@dataclass(frozen=True, slots=True)
class ConfirmatoryAnalysisRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()
    unavailable_reason: str | None = None
    excluded_seeds: tuple[Seed, ...] = ()


class AnalysisDocument(StrictModel):
    contrasts: tuple[PairedContrast, ...]
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
    excluded_seeds: tuple[Seed, ...]
    unavailable_reason: str | None

    @model_validator(mode="after")
    def validate_multiplicity(self) -> "AnalysisDocument":
        if (self.multiplicity_plan is None) != (self.multiplicity_result is None):
            raise ValueError("multiplicity plan and result must occur together")
        return self


@dataclass(frozen=True, slots=True)
class ExternalAnalysisRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed
    mechanisms: tuple[MechanismEvidence, ...] = ()
    unavailable_reason: str | None = None
    excluded_seeds: tuple[Seed, ...] = ()


class ExternalAnalysisDocument(StrictModel):
    plan: SupplementaryPairedAnalysisPlan
    contrasts: tuple[PairedContrast, ...]
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult
    mechanisms: tuple[MechanismEvidence, ...]
    excluded_seeds: tuple[Seed, ...]
    unavailable_reason: str | None


@dataclass(frozen=True, slots=True)
class TemporalAnalysisRequest:
    experiment: ExperimentId
    threshold_method: FederatedThresholdMethod
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]


class TemporalAnalysisDocument(StrictModel):
    experiment: ExperimentId
    threshold_method: FederatedThresholdMethod
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalAnalysisRecord, ...]
    campaign_decision: ScientificDecisionResult
    paired_seed_identities: tuple[Seed, ...]
    excluded_seeds: tuple[Seed, ...] = ()
    unavailable_reason: str | None = None
    drift_excess_interval: BootstrapInterval | None = None
    recovered_amount_interval: BootstrapInterval | None = None
    recovery_ratio_interval: BootstrapInterval | None = None

    @model_validator(mode="after")
    def validate_role_and_records(self) -> "TemporalAnalysisDocument":
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal analysis must remain temporal-boundary evidence")
        if not self.records:
            raise ValueError("temporal analysis requires at least one recovery record")
        seeds = tuple(record.recovery.seed for record in self.records)
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("temporal recovery records must be unique by seed")
        if seeds != self.paired_seed_identities:
            raise ValueError("temporal paired seed identities must match recovery records in order")
        if any(record.recovery.experiment is not self.experiment for record in self.records):
            raise ValueError("temporal records must share the document experiment identity")
        if any(record.recovery.threshold_method is not self.threshold_method for record in self.records):
            raise ValueError("temporal records must share the document threshold method")
        if self.campaign_decision.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal campaign decision must remain temporal-boundary evidence")
        if (
            self.campaign_decision.decision is ScientificDecision.SUPPORTED
            and len(self.records) < BOUNDED_EVIDENCE_SEED_COHORT.member_count.value
        ):
            raise ValueError(
                "publication-level temporal SUPPORTED is forbidden without the complete declared multi-seed cohort"
            )
        return self


def prepare_confirmatory_analysis(request: ConfirmatoryAnalysisRequest) -> AnalysisDocument:
    protocol = request.inference_protocol
    try:
        contrasts = validate_confirmatory_contrasts(request.contrasts, protocol)
    except PairedAnalysisContractError as error:
        return _blocked_confirmatory_document(request, error.reason.value)
    if request.unavailable_reason is not None:
        return _blocked_confirmatory_document(request, request.unavailable_reason)
    interval = paired_bca_interval(
        contrasts,
        protocol=protocol,
        analysis_seed=request.analysis_seed,
    )
    if interval.outcome.value != "available":
        reason = interval.reason.value if interval.reason is not None else "confirmatory BCa interval is blocked"
        deltas = tuple(contrast.delta for contrast in contrasts)
        return AnalysisDocument(
            contrasts=contrasts,
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
            wilcoxon=blocked_wilcoxon(f"dependent Wilcoxon blocked: {reason}"),
            rank_biserial=blocked_rank_biserial(f"dependent rank-biserial blocked: {reason}"),
            multiplicity_plan=None,
            multiplicity_result=None,
            mechanisms=request.mechanisms,
            excluded_seeds=request.excluded_seeds,
            unavailable_reason=reason,
        )
    deltas = tuple(contrast.delta for contrast in contrasts)
    multiplicity = None if request.multiplicity_plan is None else holm_adjust(request.multiplicity_plan, protocol)
    return AnalysisDocument(
        contrasts=contrasts,
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
        wilcoxon=paired_wilcoxon(contrasts, protocol),
        rank_biserial=matched_pairs_rank_biserial(contrasts, protocol),
        multiplicity_plan=request.multiplicity_plan,
        multiplicity_result=multiplicity,
        mechanisms=request.mechanisms,
        excluded_seeds=request.excluded_seeds,
        unavailable_reason=None,
    )


def prepare_external_analysis(request: ExternalAnalysisRequest) -> ExternalAnalysisDocument:
    identity = require_execution_identity(request.execution_identity, request.plan.population)
    if identity is None:
        raise RuntimeError("external analysis requires an execution identity")
    identity.require_evidence_role(request.plan.evidence_role)
    protocol = request.plan.inference_protocol
    try:
        contrasts = validate_supplementary_contrasts(request.contrasts, request.plan)
    except PairedAnalysisContractError as error:
        return _blocked_external_document(request, error.reason.value)
    if request.unavailable_reason is not None:
        return _blocked_external_document(request, request.unavailable_reason)
    interval = supplementary_paired_bca_interval(
        contrasts,
        plan=request.plan,
        analysis_seed=request.analysis_seed,
    )
    deltas = tuple(contrast.delta for contrast in contrasts)
    if interval.outcome.value != "available":
        reason = interval.reason.value if interval.reason is not None else "external BCa interval is blocked"
        return ExternalAnalysisDocument(
            plan=request.plan,
            contrasts=contrasts,
            interval=interval,
            descriptive=summarize_values(
                deltas,
                evidence_role=request.plan.evidence_role,
                counts=_zero_counts(),
                quantiles=_quantile_range(protocol),
            ),
            sign_consistency=count_paired_differences(deltas),
            wilcoxon=blocked_wilcoxon(f"dependent Wilcoxon blocked: {reason}"),
            rank_biserial=blocked_rank_biserial(f"dependent rank-biserial blocked: {reason}"),
            mechanisms=request.mechanisms,
            excluded_seeds=request.excluded_seeds,
            unavailable_reason=reason,
        )
    return ExternalAnalysisDocument(
        plan=request.plan,
        contrasts=contrasts,
        interval=interval,
        descriptive=summarize_values(
            deltas,
            evidence_role=request.plan.evidence_role,
            counts=_zero_counts(),
            quantiles=_quantile_range(protocol),
        ),
        sign_consistency=count_paired_differences(deltas),
        wilcoxon=paired_wilcoxon(contrasts, protocol),
        rank_biserial=matched_pairs_rank_biserial(contrasts, protocol),
        mechanisms=request.mechanisms,
        excluded_seeds=request.excluded_seeds,
        unavailable_reason=None,
    )


def prepare_temporal_analysis(request: TemporalAnalysisRequest) -> TemporalAnalysisDocument:
    _validate_temporal_identities(request)
    _validate_temporal_provenance(request)
    ordered = tuple(sorted(request.records, key=lambda item: item.seed.value))
    for record in ordered:
        if record.experiment is not request.experiment:
            raise ScientificContractError("temporal recovery experiment must match the analysis request")
        if record.threshold_method is not request.threshold_method:
            raise ScientificContractError("temporal recovery threshold method must match the analysis request")
        provenance = record.provenance
        if provenance.seed != record.seed:
            raise ScientificContractError("temporal recovery provenance seed must match the recovery seed")
        if provenance.experiment is not record.experiment:
            raise ScientificContractError("temporal recovery provenance experiment must match the recovery")
        if provenance.threshold_method is not record.threshold_method:
            raise ScientificContractError("temporal recovery provenance threshold method must match the recovery")
        if not provenance.population.strip():
            raise ScientificContractError("temporal recovery provenance requires a population identity")
    observed = frozenset(item.seed for item in ordered)
    declared = frozenset(BOUNDED_EVIDENCE_SEED_COHORT.values)
    if observed != declared:
        missing = tuple(sorted((seed for seed in declared - observed), key=lambda item: item.value))
        extra = tuple(sorted((seed for seed in observed - declared), key=lambda item: item.value))
        raise ScientificContractError(
            "temporal analysis requires exact declared seed-cohort equality "
            f"(missing={tuple(seed.value for seed in missing)}, extra={tuple(seed.value for seed in extra)})"
        )
    records = tuple(temporal_analysis_record(item) for item in ordered)
    drift_interval, recovered_interval, ratio_interval = temporal_seed_series_intervals(ordered)
    return TemporalAnalysisDocument(
        experiment=request.experiment,
        threshold_method=request.threshold_method,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        static_reference_provenance=request.static_reference_provenance,
        frozen_provenance=request.frozen_provenance,
        recalibrated_provenance=request.recalibrated_provenance,
        records=records,
        campaign_decision=decide_temporal_campaign(ordered),
        paired_seed_identities=tuple(item.seed for item in ordered),
        excluded_seeds=(),
        unavailable_reason=None,
        drift_excess_interval=drift_interval,
        recovered_amount_interval=recovered_interval,
        recovery_ratio_interval=ratio_interval,
    )


def _blocked_confirmatory_document(
    request: ConfirmatoryAnalysisRequest,
    reason: str,
) -> AnalysisDocument:
    protocol = request.inference_protocol
    interval = BootstrapInterval.blocked(
        protocol=protocol,
        analysis_seed=request.analysis_seed,
        point_estimate=None,
        reason=_bca_reason_or_fixed(reason),
    )
    return AnalysisDocument(
        contrasts=request.contrasts,
        inference_protocol=protocol,
        interval=interval,
        decision=ScientificDecisionResult(
            evidence_role=EvidenceRole.CONFIRMATORY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=None,
            interval=interval,
            rationale=f"confirmatory analysis blocked: {reason}",
        ),
        descriptive=summarize_values(
            (),
            evidence_role=EvidenceRole.CONFIRMATORY,
            counts=_zero_counts(),
            quantiles=_quantile_range(protocol),
        ),
        sign_consistency=count_paired_differences(()),
        wilcoxon=blocked_wilcoxon(f"dependent Wilcoxon blocked: {reason}"),
        rank_biserial=blocked_rank_biserial(f"dependent rank-biserial blocked: {reason}"),
        multiplicity_plan=None,
        multiplicity_result=None,
        mechanisms=request.mechanisms,
        excluded_seeds=request.excluded_seeds,
        unavailable_reason=reason,
    )


def _blocked_external_document(
    request: ExternalAnalysisRequest,
    reason: str,
) -> ExternalAnalysisDocument:
    protocol = request.plan.inference_protocol
    interval = BootstrapInterval.blocked(
        protocol=protocol,
        analysis_seed=request.analysis_seed,
        point_estimate=None,
        reason=_bca_reason_or_fixed(reason),
    )
    return ExternalAnalysisDocument(
        plan=request.plan,
        contrasts=request.contrasts,
        interval=interval,
        descriptive=summarize_values(
            (),
            evidence_role=request.plan.evidence_role,
            counts=_zero_counts(),
            quantiles=_quantile_range(protocol),
        ),
        sign_consistency=count_paired_differences(()),
        wilcoxon=blocked_wilcoxon(f"dependent Wilcoxon blocked: {reason}"),
        rank_biserial=blocked_rank_biserial(f"dependent rank-biserial blocked: {reason}"),
        mechanisms=request.mechanisms,
        excluded_seeds=request.excluded_seeds,
        unavailable_reason=reason,
    )


def _bca_reason_or_fixed(reason: str) -> BcaReason:
    for item in BcaReason:
        if item.value == reason:
            return item
    return BcaReason.FIXED_COORDINATE_MISMATCH


def _quantile_range(protocol: PairedInferenceProtocol) -> QuantileRange:
    return QuantileRange(
        lower=protocol.descriptive_lower_quantile,
        upper=protocol.descriptive_upper_quantile,
    )


def _zero_counts() -> ObservationCounts:
    return ObservationCounts(
        unavailable=PairedObservationCount(0),
        excluded=PairedObservationCount(0),
    )


def _validate_temporal_provenance(request: TemporalAnalysisRequest) -> None:
    static = request.static_reference_provenance
    frozen = request.frozen_provenance
    if static.state is not TemporalState.STATIC_REFERENCE:
        raise ValueError("temporal analysis requires static-reference provenance")
    validate_frozen_recalibrated_pair(frozen, request.recalibrated_provenance)
    bindings = (
        (
            static.checkpoint_checksum,
            frozen.checkpoint_checksum,
            "all temporal states must share one fitted detector",
        ),
        (
            static.preprocessing_state_set_checksum,
            frozen.preprocessing_state_set_checksum,
            "all temporal states must share one fitted preprocessing state",
        ),
        (
            static.coordinate_checksum,
            frozen.coordinate_checksum,
            "all temporal states must share one training coordinate",
        ),
    )
    for observed, expected, message in bindings:
        if observed != expected:
            raise ValueError(message)


def _validate_temporal_identities(request: TemporalAnalysisRequest) -> None:
    bindings = (
        (request.static_reference_identity, TemporalState.STATIC_REFERENCE),
        (request.frozen_identity, TemporalState.FROZEN_FUTURE),
        (request.recalibrated_identity, TemporalState.RECALIBRATED_FUTURE),
    )
    for identity, expected_state in bindings:
        bound = require_execution_identity(identity, PopulationId.EDGE_TEMPORAL_GROUPS)
        if bound is None or bound.temporal_state is not expected_state:
            raise ScientificContractError("temporal analysis identity must match its deployment state")
        if bound.experiment is not request.experiment:
            raise ScientificContractError("temporal analysis identity must match the declared experiment")
