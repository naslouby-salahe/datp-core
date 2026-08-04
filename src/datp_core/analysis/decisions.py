"""Confirmatory, supplementary, and temporal analysis decisions and publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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
from datp_core.artifacts.serialization import canonical_json_text
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import EvidenceRole, PopulationId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, PairedObservationCount, Seed, checksum_text
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.protocols.statistics import PairedInferenceProtocol


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
    def validate_role(self) -> "TemporalAnalysisDocument":
        if self.evidence_role is not EvidenceRole.TEMPORAL_BOUNDARY:
            raise ValueError("temporal analysis must remain temporal-boundary evidence")
        return self


@dataclass(frozen=True, slots=True)
class AnalysisPublication[DocumentT]:
    asset_name: AnalysisAssetName
    document: DocumentT
    digest: Checksum


def prepare_confirmatory_analysis(
    request: ConfirmatoryAnalysisRequest,
) -> AnalysisPublication[AnalysisDocument]:
    protocol = request.inference_protocol
    interval = paired_bca_interval(
        request.contrasts,
        protocol=protocol,
        analysis_seed=request.analysis_seed,
    )
    deltas = tuple(contrast.delta for contrast in request.contrasts)
    multiplicity = (
        None
        if request.multiplicity_plan is None
        else holm_adjust(request.multiplicity_plan, protocol)
    )
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


def write_analysis_publication(
    publication: AnalysisPublication[DocumentT],
    directory: Path,
) -> DocumentT:
    (directory / publication.asset_name).write_text(
        canonical_json_text(publication.document),
        encoding="utf-8",
    )
    (directory / AnalysisAssetName.COMPLETE).write_text(
        publication.digest.value,
        encoding="utf-8",
    )
    return publication.document


def analysis_publication_is_reusable(
    publication: AnalysisPublication[object],
    directory: Path,
) -> bool:
    complete = directory / AnalysisAssetName.COMPLETE
    document = directory / publication.asset_name
    try:
        return (
            complete.is_file()
            and document.is_file()
            and complete.read_text(encoding="utf-8").strip() == publication.digest.value
        )
    except OSError:
        return False


def load_reused_analysis_publication(
    publication: AnalysisPublication[DocumentT],
    directory: Path,
) -> DocumentT:
    del directory
    return publication.document


def rebase_analysis_publication(document: DocumentT, directory: Path) -> DocumentT:
    del directory
    return document


def _publication[DocumentT](
    asset_name: AnalysisAssetName,
    document: DocumentT,
) -> AnalysisPublication[DocumentT]:
    return AnalysisPublication(
        asset_name=asset_name,
        document=document,
        digest=checksum_text(canonical_json_text(document)),
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
    static = request.static_reference_provenance
    if static.state is not TemporalState.STATIC_REFERENCE:
        raise ValueError("temporal analysis requires static-reference provenance")
    validate_frozen_recalibrated_pair(
        request.frozen_provenance,
        request.recalibrated_provenance,
    )
    if static.checkpoint_checksum != request.frozen_provenance.checkpoint_checksum:
        raise ValueError("all temporal states must share one fitted detector")


def _validate_temporal_identities(request: TemporalAnalysisRequest) -> None:
    bindings = (
        (request.static_reference_identity, TemporalState.STATIC_REFERENCE),
        (request.frozen_identity, TemporalState.FROZEN_FUTURE),
        (request.recalibrated_identity, TemporalState.RECALIBRATED_FUTURE),
    )
    for identity, expected_state in bindings:
        bound = require_execution_identity(identity, PopulationId.EDGE_TEMPORAL_GROUPS)
        if bound is None or bound.temporal_state is not expected_state:
            raise ScientificContractError(
                "temporal analysis identity must match its deployment state"
            )
