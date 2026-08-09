"""Confirmatory, external, and temporal evidence analysis publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from pydantic import ValidationError

from datp_core.analysis.contrasts import PairedContrast, SupplementaryPairedAnalysisPlan
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
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.publication import (
    ArtifactPublication,
    ArtifactPublicationResult,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.artifacts.serializers.json import canonical_checksum, canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod, PublicationStatus
from datp_core.core.numeric import Seed
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity

if TYPE_CHECKING:
    from datp_core.analysis.mechanisms import MechanismEvidence

AnalysisDocumentT = TypeVar("AnalysisDocumentT", bound=StrictModel)


class AnalysisAssetName(StrEnum):
    DOCUMENT = "analysis.json"
    COMPLETE = "COMPLETE"
    EXTERNAL_DOCUMENT = "external_analysis.json"
    TEMPORAL_DOCUMENT = "temporal_analysis.json"


class SeedEvidenceAssetName(StrEnum):
    DOCUMENT = "seed.json"


@dataclass(frozen=True, slots=True)
class AnalysisPublication[AnalysisDocumentT: StrictModel]:
    asset_name: AnalysisAssetName
    document: AnalysisDocumentT
    digest: Checksum
    document_type: type[AnalysisDocumentT]


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
    document = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=request.contrasts,
            inference_protocol=request.inference_protocol,
            analysis_seed=request.analysis_seed,
            multiplicity_plan=request.multiplicity_plan,
            mechanisms=request.mechanisms,
        )
    )
    publication = _publish(
        request.output_directory,
        request.overwrite,
        _publication(AnalysisAssetName.DOCUMENT, document, AnalysisDocument),
    )
    return AnalyzeConfirmatoryEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


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
    publication = _publish(
        request.output_directory,
        request.overwrite,
        _publication(AnalysisAssetName.EXTERNAL_DOCUMENT, document, ExternalAnalysisDocument),
    )
    return AnalyzeExternalEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


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
    publication = _publish(
        request.output_directory,
        request.overwrite,
        _publication(AnalysisAssetName.TEMPORAL_DOCUMENT, document, TemporalAnalysisDocument),
    )
    return AnalyzeTemporalEvidenceResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def _publication[AnalysisDocumentT: StrictModel](
    asset_name: AnalysisAssetName,
    document: AnalysisDocumentT,
    document_type: type[AnalysisDocumentT],
) -> AnalysisPublication[AnalysisDocumentT]:
    return AnalysisPublication(
        asset_name=asset_name,
        document=document,
        digest=canonical_checksum(document),
        document_type=document_type,
    )


def _publish[AnalysisDocumentT: StrictModel](
    output_directory: Path,
    overwrite: bool,
    prepared: AnalysisPublication[AnalysisDocumentT],
) -> ArtifactPublicationResult[AnalysisDocumentT]:
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


def _write_analysis_publication[AnalysisDocumentT: StrictModel](
    publication: AnalysisPublication[AnalysisDocumentT],
    directory: Path,
) -> AnalysisDocumentT:
    (directory / publication.asset_name).write_text(
        canonical_json_text(publication.document),
        encoding="utf-8",
    )
    (directory / AnalysisAssetName.COMPLETE).write_text(publication.digest.value, encoding="utf-8")
    return publication.document


def _analysis_publication_is_reusable[AnalysisDocumentT: StrictModel](
    publication: AnalysisPublication[AnalysisDocumentT],
    directory: Path,
) -> bool:
    complete = directory / AnalysisAssetName.COMPLETE
    document_path = directory / publication.asset_name
    try:
        if not complete.is_file() or not document_path.is_file():
            return False
        marker = complete.read_text(encoding="utf-8").strip()
        loaded = publication.document_type.model_validate_json(document_path.read_text(encoding="utf-8"))
        recalculated = canonical_checksum(loaded)
        if marker != recalculated.value:
            return False
        if recalculated != publication.digest:
            return False
        if not _analysis_identity_matches(publication.document, loaded):
            return False
        return True
    except (OSError, UnicodeError, ValidationError, ValueError, TypeError):
        return False


def _load_reused_analysis_publication[AnalysisDocumentT: StrictModel](
    publication: AnalysisPublication[AnalysisDocumentT],
    directory: Path,
) -> AnalysisDocumentT:
    document_path = directory / publication.asset_name
    try:
        loaded = publication.document_type.model_validate_json(document_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ScientificContractError(
            ErrorMessage(f"completed analysis document is unreadable or invalid: {document_path}")
        ) from error
    recalculated = canonical_checksum(loaded)
    marker = (directory / AnalysisAssetName.COMPLETE).read_text(encoding="utf-8").strip()
    if recalculated.value != marker:
        raise ScientificContractError(
            ErrorMessage(f"analysis document checksum does not match completion marker: {document_path}")
        )
    if recalculated != publication.digest:
        raise ScientificContractError(
            ErrorMessage(f"analysis document identity does not match the requested analysis: {document_path}")
        )
    if not _analysis_identity_matches(publication.document, loaded):
        raise ScientificContractError(
            ErrorMessage(f"persisted analysis identity does not match the requested run: {document_path}")
        )
    return loaded


def _rebase_analysis_publication[AnalysisDocumentT: StrictModel](
    document: AnalysisDocumentT,
    directory: Path,
) -> AnalysisDocumentT:
    del directory
    return document


def _analysis_identity_matches(requested: object, loaded: object) -> bool:
    if type(requested) is not type(loaded):
        return False
    if isinstance(requested, AnalysisDocument) and isinstance(loaded, AnalysisDocument):
        return requested.inference_protocol == loaded.inference_protocol and tuple(
            item.seed for item in requested.contrasts
        ) == tuple(item.seed for item in loaded.contrasts)
    if isinstance(requested, ExternalAnalysisDocument) and isinstance(loaded, ExternalAnalysisDocument):
        return requested.plan == loaded.plan and tuple(item.seed for item in requested.contrasts) == tuple(
            item.seed for item in loaded.contrasts
        )
    if isinstance(requested, TemporalAnalysisDocument) and isinstance(loaded, TemporalAnalysisDocument):
        return (
            requested.experiment is loaded.experiment
            and requested.threshold_method is loaded.threshold_method
            and requested.paired_seed_identities == loaded.paired_seed_identities
        )
    return requested == loaded
