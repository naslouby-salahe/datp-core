"""Confirmatory, external, and temporal evidence analysis publication."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan
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
from datp_core.analysis.inference.multiplicity import MultiplicityPlan
from datp_core.analysis.mechanisms import MechanismEvidence
from datp_core.analysis.preparation import (
    prepare_confirmatory_analysis,
    prepare_external_analysis,
    prepare_temporal_analysis,
)
from datp_core.analysis.temporal import TemporalRecoveryResult
from datp_core.domain.enums import PublicationStatus
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, Seed
from datp_core.pipeline.publication.service import (
    ArtifactPublication,
    ArtifactPublicationResult,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.statistics import PairedInferenceProtocol
from datp_core.protocols.temporal import TemporalDeploymentProvenance


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeConfirmatoryEvidenceRequest:
    contrasts: tuple[PairedContrast, ...]
    inference_protocol: PairedInferenceProtocol
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool
    multiplicity_plan: MultiplicityPlan | None = None
    mechanisms: tuple[MechanismEvidence, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeExternalEvidenceRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    contrasts: tuple[PairedContrast, ...]
    plan: SupplementaryPairedAnalysisPlan
    analysis_seed: Seed
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeTemporalEvidenceRequest:
    static_reference_identity: ExternalTemporalExecutionIdentity
    frozen_identity: ExternalTemporalExecutionIdentity
    recalibrated_identity: ExternalTemporalExecutionIdentity
    static_reference_provenance: TemporalDeploymentProvenance
    frozen_provenance: TemporalDeploymentProvenance
    recalibrated_provenance: TemporalDeploymentProvenance
    records: tuple[TemporalRecoveryResult, ...]
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeConfirmatoryEvidenceResult:
    publication_status: PublicationStatus
    document: AnalysisDocument
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeExternalEvidenceResult:
    publication_status: PublicationStatus
    document: ExternalAnalysisDocument
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyzeTemporalEvidenceResult:
    publication_status: PublicationStatus
    document: TemporalAnalysisDocument
    complete_digest: Checksum


def analyze_confirmatory_evidence(
    request: AnalyzeConfirmatoryEvidenceRequest,
) -> AnalyzeConfirmatoryEvidenceResult:
    prepared = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=request.contrasts,
            inference_protocol=request.inference_protocol,
            analysis_seed=request.analysis_seed,
            multiplicity_plan=request.multiplicity_plan,
            mechanisms=request.mechanisms,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return AnalyzeConfirmatoryEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def analyze_external_evidence(
    request: AnalyzeExternalEvidenceRequest,
) -> AnalyzeExternalEvidenceResult:
    prepared = prepare_external_analysis(
        ExternalAnalysisRequest(
            execution_identity=request.execution_identity,
            contrasts=request.contrasts,
            plan=request.plan,
            analysis_seed=request.analysis_seed,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return AnalyzeExternalEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def analyze_temporal_evidence(
    request: AnalyzeTemporalEvidenceRequest,
) -> AnalyzeTemporalEvidenceResult:
    prepared = prepare_temporal_analysis(
        TemporalAnalysisRequest(
            static_reference_identity=request.static_reference_identity,
            frozen_identity=request.frozen_identity,
            recalibrated_identity=request.recalibrated_identity,
            static_reference_provenance=request.static_reference_provenance,
            frozen_provenance=request.frozen_provenance,
            recalibrated_provenance=request.recalibrated_provenance,
            records=request.records,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return AnalyzeTemporalEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def _publish[DocumentT](
    output_directory: Path,
    overwrite: bool,
    prepared: AnalysisPublication[DocumentT],
) -> ArtifactPublicationResult[DocumentT]:
    return publish_artifact(
        ArtifactPublication(
            target=output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=_write_analysis_publication,
                validator=_analysis_publication_is_reusable,
                loader=_load_reused_analysis_publication,
                rebaser=_rebase_analysis_publication,
            ),
            overwrite=overwrite,
            complete_marker=AnalysisAssetName.COMPLETE,
        )
    )


def _write_analysis_publication[DocumentT](
    publication: AnalysisPublication[DocumentT],
    directory: Path,
) -> DocumentT:
    (directory / publication.asset_name).write_text(
        canonical_json_text(publication.document),
        encoding="utf-8",
    )
    (directory / AnalysisAssetName.COMPLETE).write_text(publication.digest.value, encoding="utf-8")
    return publication.document


def _analysis_publication_is_reusable[DocumentT](
    publication: AnalysisPublication[DocumentT],
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


def _load_reused_analysis_publication[DocumentT](
    publication: AnalysisPublication[DocumentT],
    directory: Path,
) -> DocumentT:
    del directory
    return publication.document


def _rebase_analysis_publication[DocumentT](document: DocumentT, directory: Path) -> DocumentT:
    del directory
    return document
