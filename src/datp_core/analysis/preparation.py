"""Preparation of confirmatory, external, and temporal analysis publications."""

from datp_core.analysis.descriptive import ObservationCounts, QuantileRange, count_paired_differences, summarize_values
from datp_core.analysis.documents import (
    AnalysisAssetName,
    AnalysisDocument,
    AnalysisPublication,
    ConfirmatoryAnalysisRequest,
    ExternalAnalysisDocument,
    ExternalAnalysisRequest,
    TemporalAnalysisDocument,
    TemporalAnalysisRequest,
)
from datp_core.analysis.inference.bootstrap import paired_bca_interval, supplementary_paired_bca_interval
from datp_core.analysis.inference.multiplicity import holm_adjust
from datp_core.analysis.inference.wilcoxon import matched_pairs_rank_biserial, paired_wilcoxon
from datp_core.analysis.scientific_decision import decide_confirmatory
from datp_core.analysis.temporal import temporal_analysis_record
from datp_core.domain.enums import EvidenceRole, PopulationId, TemporalState
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import PairedObservationCount
from datp_core.protocols.experiments import require_execution_identity
from datp_core.protocols.statistics import PairedInferenceProtocol
from datp_core.protocols.temporal import validate_frozen_recalibrated_pair


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
