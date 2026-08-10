"""Confirmatory, external, and temporal evidence analysis publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from datp_core.analysis.contrasts import PairedContrasts, SupplementaryPairedAnalysisPlan
from datp_core.analysis.inference.contracts import PairedInferenceProtocol
from datp_core.analysis.inference.multiplicity import MultiplicityPlan
from datp_core.analysis.preparation import (
    AnalysisDocument,
    ConfirmatoryAnalysisRequest,
    ExternalAnalysisDocument,
    ExternalAnalysisRequest,
    TemporalAnalysisDocument,
    TemporalAnalysisRequest,
    prepare_confirmatory_analysis,
    prepare_external_analysis,
    prepare_temporal_analysis,
)
from datp_core.analysis.temporal import TemporalDeploymentProvenance, TemporalRecoveryResult
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    ExperimentId,
    FederatedThresholdMethod,
    FileContentText,
)
from datp_core.core.numeric import Seed
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.runtime.filesystem import write_text_atomically

if TYPE_CHECKING:
    from datp_core.analysis.mechanisms import MechanismEvidence


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


class SeedEvidenceAssetName(StrEnum):
    DOCUMENT = "seed.json"


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeConfirmatoryEvidenceRequest:
    contrasts: PairedContrasts
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    output_directory: Path
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeExternalEvidenceRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: PairedContrasts
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed
    output_directory: Path
    mechanisms: tuple[MechanismEvidence, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeTemporalEvidenceRequest:
    experiment: ExperimentId
    threshold_method: FederatedThresholdMethod
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]
    output_directory: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeConfirmatoryEvidenceResult:
    document: AnalysisDocument


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeExternalEvidenceResult:
    document: ExternalAnalysisDocument


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeTemporalEvidenceResult:
    document: TemporalAnalysisDocument


def analyze_confirmatory_evidence(
    request: AnalyzeConfirmatoryEvidenceRequest,
) -> AnalyzeConfirmatoryEvidenceResult:
    document = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=request.contrasts,
            inference_protocol=request.inference_protocol,
            analysis_seed=request.analysis_seed,
            multiplicity_plan=request.multiplicity_plan,
            mechanisms=request.mechanisms,
        )
    )
    _write_analysis_document(request.output_directory, AnalysisAssetName.DOCUMENT, document)
    return AnalyzeConfirmatoryEvidenceResult(document=document)


def analyze_external_evidence(
    request: AnalyzeExternalEvidenceRequest,
) -> AnalyzeExternalEvidenceResult:
    document = prepare_external_analysis(
        ExternalAnalysisRequest(
            execution_identity=request.execution_identity,
            contrasts=request.contrasts,
            plan=request.plan,
            analysis_seed=request.analysis_seed,
            mechanisms=request.mechanisms,
        )
    )
    _write_analysis_document(request.output_directory, AnalysisAssetName.EXTERNAL_DOCUMENT, document)
    return AnalyzeExternalEvidenceResult(document=document)


def analyze_temporal_evidence(
    request: AnalyzeTemporalEvidenceRequest,
) -> AnalyzeTemporalEvidenceResult:
    document = prepare_temporal_analysis(
        TemporalAnalysisRequest(
            experiment=request.experiment,
            threshold_method=request.threshold_method,
            static_reference_identity=request.static_reference_identity,
            frozen_identity=request.frozen_identity,
            recalibrated_identity=request.recalibrated_identity,
            static_reference_provenance=request.static_reference_provenance,
            frozen_provenance=request.frozen_provenance,
            recalibrated_provenance=request.recalibrated_provenance,
            records=request.records,
        )
    )
    _write_analysis_document(request.output_directory, AnalysisAssetName.TEMPORAL_DOCUMENT, document)
    return AnalyzeTemporalEvidenceResult(document=document)


def _write_analysis_document(
    output_directory: Path,
    asset_name: AnalysisAssetName,
    document: StrictModel,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    return write_text_atomically(
        output_directory / asset_name,
        FileContentText(canonical_json_text(document)),
    )
