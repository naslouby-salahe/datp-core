"""Scientific analysis decisions and typed publication preparation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import model_validator

from datp_core.analysis.contrasts import (
    PairedContrast,
    PairedDifferenceCounts,
    SupplementaryPairedAnalysisPlan,
)
from datp_core.analysis.descriptive import (
    DescriptiveSummary,
    ObservationCounts,
    QuantileRange,
    count_paired_differences,
    summarize_values,
)
from datp_core.analysis.inference.bootstrap import (
    BootstrapInterval,
    paired_bca_interval,
    supplementary_paired_bca_interval,
)
from datp_core.analysis.inference.multiplicity import (
    MultiplicityPlan,
    MultiplicityResult,
    holm_adjust,
)
from datp_core.analysis.inference.wilcoxon import (
    RankBiserialResult,
    WilcoxonResult,
    matched_pairs_rank_biserial,
    paired_wilcoxon,
)
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    PopulationId,
    ScientificDecision,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import Checksum, MetricValue, PairedObservationCount, Seed
from datp_core.protocols.experiments import (
    ExternalTemporalExecutionIdentity,
    require_execution_identity,
)
from datp_core.protocols.statistics import PairedInferenceProtocol


class ScientificDecisionResult(StrictModel):
    evidence_role: EvidenceRole
    decision: ScientificDecision
    point_estimate: MetricValue | None
    interval: BootstrapInterval | None
    rationale: str

    @model_validator(mode="after")
    def validate_decision(self) -> ScientificDecisionResult:
        if not self.rationale.strip():
            raise ValueError("scientific decisions require a rationale")
        if self.interval is not None and self.point_estimate != self.interval.point_estimate:
            raise ValueError("decision estimate must match its interval estimate")
        return self

    @property
    def availability(self) -> AvailabilityStatus:
        return (
            AvailabilityStatus.UNAVAILABLE
            if self.decision is ScientificDecision.BLOCKED
            else AvailabilityStatus.AVAILABLE
        )


def decide_confirmatory(interval: BootstrapInterval) -> ScientificDecisionResult:
    if (
        interval.availability is not AvailabilityStatus.AVAILABLE
        or interval.point_estimate is None
        or interval.lower_bound is None
        or interval.upper_bound is None
    ):
        return ScientificDecisionResult(
            evidence_role=EvidenceRole.CONFIRMATORY,
            decision=ScientificDecision.BLOCKED,
            point_estimate=interval.point_estimate,
            interval=interval,
            rationale="confirmatory BCa interval is unavailable or degenerate",
        )
    if interval.lower_bound.value > 0.0:
        decision = ScientificDecision.SUPPORTED
        rationale = "the paired BCa interval supports lower CV(FPR) under local thresholds"
    elif interval.upper_bound.value < 0.0:
        decision = ScientificDecision.OPPOSITE_DIRECTION
        rationale = "the paired BCa interval supports the opposite direction"
    elif interval.point_estimate.value > 0.0:
        decision = ScientificDecision.DIRECTIONAL_INCONCLUSIVE
        rationale = "the point estimate is directional but the paired BCa interval crosses zero"
    else:
        decision = ScientificDecision.NO_OBSERVED_ADVANTAGE
        rationale = "the paired BCa interval crosses zero without a positive point estimate"
    return ScientificDecisionResult(
        evidence_role=EvidenceRole.CONFIRMATORY,
        decision=decision,
        point_estimate=interval.point_estimate,
        interval=interval,
        rationale=rationale,
    )


if TYPE_CHECKING:
    from datp_core.analysis.mechanisms import MechanismEvidence
    from datp_core.analysis.temporal import (
        TemporalAnalysisRecord,
        TemporalDeploymentProvenance,
        TemporalRecoveryResult,
    )


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    COMPLETE = "COMPLETE"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


@dataclass(frozen=True, slots=True)
class ConfirmatoryAnalysisRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
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
    def validate_multiplicity(self) -> AnalysisDocument:
        if (self.multiplicity_plan is None) != (self.multiplicity_result is None):
            raise ValueError("multiplicity plan and result must occur together")
        return self


@dataclass(frozen=True, slots=True)
class ExternalAnalysisRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed


class ExternalAnalysisDocument(StrictModel):
    plan: SupplementaryPairedAnalysisPlan
    interval: BootstrapInterval
    descriptive: DescriptiveSummary
    sign_consistency: PairedDifferenceCounts
    wilcoxon: WilcoxonResult
    rank_biserial: RankBiserialResult


@dataclass(frozen=True, slots=True)
class TemporalAnalysisRequest:
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]


class TemporalAnalysisDocument(StrictModel):
    evidence_role: EvidenceRole
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalAnalysisRecord, ...]

    @model_validator(mode="after")
    def validate_role_and_records(self) -> TemporalAnalysisDocument:
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal analysis must remain temporal-boundary evidence")
        if not self.records:
            raise ValueError("temporal analysis requires at least one recovery record")
        seeds = tuple(record.recovery.seed for record in self.records)
        if len(seeds) != len(frozenset(seeds)):
            raise ValueError("temporal recovery records must be unique by seed")
        return self


@dataclass(frozen=True, slots=True)
class AnalysisPublication[DocumentT]:
    asset_name: AnalysisAssetName
    document: DocumentT
    digest: Checksum


def prepare_confirmatory_analysis(
    request: ConfirmatoryAnalysisRequest,
) -> AnalysisPublication[AnalysisDocument]:
    from datp_core.analysis.mechanisms import MechanismEvidence

    AnalysisDocument.model_rebuild(_types_namespace={"MechanismEvidence": MechanismEvidence})
    protocol = request.inference_protocol
    interval = paired_bca_interval(
        request.contrasts,
        protocol=protocol,
        analysis_seed=request.analysis_seed,
    )
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    multiplicity = None if request.multiplicity_plan is None else holm_adjust(request.multiplicity_plan, protocol)
    return _publication(
        AnalysisAssetName.DOCUMENT,
        AnalysisDocument(
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
        ),
    )


def prepare_external_analysis(
    request: ExternalAnalysisRequest,
) -> AnalysisPublication[ExternalAnalysisDocument]:
    identity = require_execution_identity(request.execution_identity, request.plan.population)
    if identity is None:
        raise RuntimeError("external analysis requires an execution identity")
    identity.require_evidence_role(request.plan.evidence_role)
    protocol = request.plan.inference_protocol
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    return _publication(
        AnalysisAssetName.EXTERNAL_DOCUMENT,
        ExternalAnalysisDocument(
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
        ),
    )


def prepare_temporal_analysis(
    request: TemporalAnalysisRequest,
) -> AnalysisPublication[TemporalAnalysisDocument]:
    from datp_core.analysis.temporal import (
        TemporalAnalysisRecord,
        TemporalDeploymentProvenance,
        temporal_analysis_record,
    )

    TemporalAnalysisDocument.model_rebuild(
        _types_namespace={
            "TemporalAnalysisRecord": TemporalAnalysisRecord,
            "TemporalDeploymentProvenance": TemporalDeploymentProvenance,
        }
    )
    _validate_temporal_identities(request)
    _validate_temporal_provenance(request)
    return _publication(
        AnalysisAssetName.TEMPORAL_DOCUMENT,
        TemporalAnalysisDocument(
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            static_reference_provenance=request.static_reference_provenance,
            frozen_provenance=request.frozen_provenance,
            recalibrated_provenance=request.recalibrated_provenance,
            records=tuple(temporal_analysis_record(record) for record in request.records),
        ),
    )


def _publication[DocumentT](
    asset_name: AnalysisAssetName,
    document: DocumentT,
) -> AnalysisPublication[DocumentT]:
    return AnalysisPublication(
        asset_name=asset_name,
        document=document,
        digest=canonical_checksum(document),
    )


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
    from datp_core.analysis.temporal import validate_frozen_recalibrated_pair

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
