"""Generic population construction, splitting, and deterministic publication.

This module publishes population and split artifacts without interpreting
dataset columns or branching on dataset-specific implementation details: it
only reacts to the generic, typed presence of optional construction results
(diagnostics, a matched reference population, typed evidence).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.artifacts.repositories.publication import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
    serialize_json_model,
)
from datp_core.data.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.data.populations.contracts import (
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    PopulationConstructionRequest,
    PopulationConstructionResult,
    PopulationManifest,
    PopulationManifestDocument,
    SplitConstructionRequest,
    SplitManifestDocument,
)
from datp_core.data.populations.integrity import membership_frame_checksum, validate_split_manifest
from datp_core.data.populations.splits import split_membership
from datp_core.data.registry import construct_population
from datp_core.domain.enums import ContractSubject, DatasetId, PopulationId, PublicationStatus, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.identifiers import CaptureTimestampColumn
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity, require_execution_identity


class PopulationPublicationAsset(StrEnum):
    EXECUTION_IDENTITY = "execution_identity.json"
    POPULATION_MANIFEST = "population_manifest.json"
    MEMBERSHIP = "membership.parquet"
    CHRONOLOGY = "chronology.json"
    MATCHED_STATIC_MANIFEST = "matched_static_reference_manifest.json"
    MATCHED_STATIC_MEMBERSHIP = "matched_static_reference_membership.parquet"
    CICIOT_EXCLUDED_ROWS = "ciciot_excluded_rows.parquet"
    CICIOT_CLIENT_ELIGIBILITY = "ciciot_client_eligibility.parquet"
    COMPLETE = "COMPLETE"


class SplitPublicationAsset(StrEnum):
    EXECUTION_IDENTITY = "execution_identity.json"
    ASSIGNMENTS = "split_assignments.parquet"
    MANIFEST = "split_manifest.json"
    MATCHED_STATIC_ASSIGNMENTS = "matched_static_reference_assignments.parquet"
    MATCHED_STATIC_MANIFEST = "matched_static_reference_split_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructDeclaredPopulationRequest:
    population: PopulationId
    dataset: DatasetId
    canonical_root: Path
    partition_seed: Seed
    split_protocol: SplitProtocolId
    controlled_condition: ControlledPartitionCondition | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructDeclaredPopulationResult:
    construction: PopulationConstructionResult
    split_assignments: pl.DataFrame
    split_manifest: SplitManifestDocument


def construct_declared_population(
    request: ConstructDeclaredPopulationRequest,
) -> ConstructDeclaredPopulationResult:
    construction = construct_population(
        PopulationConstructionRequest(
            request.population,
            request.canonical_root,
            request.partition_seed,
            request.split_protocol,
            request.controlled_condition,
        )
    )
    assignments, manifest = split_membership(
        SplitConstructionRequest(
            construction.membership,
            request.population,
            request.dataset,
            request.partition_seed,
            request.split_protocol,
            construction.manifest.document.membership_checksum,
            capture_timestamp_column=_capture_timestamp_column_for_split(
                request.split_protocol,
                construction.membership,
            ),
        )
    )
    return ConstructDeclaredPopulationResult(
        construction=construction,
        split_assignments=assignments,
        split_manifest=manifest,
    )


@dataclass(slots=True, eq=False)
class PopulationMembershipArtifacts:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


def _population_membership_artifacts(construction: PopulationConstructionResult) -> PopulationMembershipArtifacts:
    chronology = (
        construction.diagnostics
        if isinstance(construction.diagnostics, ChronologicalPartitionDiagnosticsDocument)
        else None
    )
    matched_reference = construction.matched_reference
    evidence = construction.evidence
    return PopulationMembershipArtifacts(
        population_manifest=construction.manifest,
        membership=construction.membership,
        chronology=chronology,
        matched_static_reference_manifest=matched_reference.manifest if matched_reference is not None else None,
        matched_static_reference_membership=matched_reference.membership if matched_reference is not None else None,
        ciciot_excluded_rows=evidence.excluded_rows if evidence is not None else None,
        ciciot_client_eligibility=evidence.client_eligibility if evidence is not None else None,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstructPublishedPopulationRequest:
    canonical_root: Path
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    partition_seed: Seed
    split_protocol: SplitProtocolId
    output_directory: Path
    overwrite: bool


@dataclass(slots=True, eq=False, kw_only=True)
class ConstructPublishedPopulationResult:
    publication_status: PublicationStatus
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    complete_digest: Checksum
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


@dataclass(slots=True, eq=False)
class _PopulationMembershipPublication:
    execution_identity: ExternalTemporalExecutionIdentity
    artifacts: PopulationMembershipArtifacts
    digest: Checksum


def construct_published_population(
    request: ConstructPublishedPopulationRequest,
) -> ConstructPublishedPopulationResult:
    require_execution_identity(request.execution_identity, request.population)
    construction = construct_population(
        PopulationConstructionRequest(
            request.population,
            request.canonical_root,
            request.partition_seed,
            request.split_protocol,
            None,
        )
    )
    artifacts = _population_membership_artifacts(construction)
    prepared = _PopulationMembershipPublication(
        execution_identity=request.execution_identity,
        artifacts=artifacts,
        digest=_population_membership_digest(artifacts, request.execution_identity),
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=_write_population_membership,
                validator=_population_membership_is_reusable,
                loader=_load_reused_population_membership,
                rebaser=_rebase_population_membership,
            ),
            overwrite=request.overwrite,
            complete_marker=PopulationPublicationAsset.COMPLETE,
        )
    )
    published = publication.value
    return ConstructPublishedPopulationResult(
        publication_status=publication.status,
        population_manifest=published.population_manifest,
        membership=published.membership,
        chronology=published.chronology,
        matched_static_reference_manifest=published.matched_static_reference_manifest,
        matched_static_reference_membership=published.matched_static_reference_membership,
        complete_digest=publication.complete_digest,
        ciciot_excluded_rows=published.ciciot_excluded_rows,
        ciciot_client_eligibility=published.ciciot_client_eligibility,
    )


def _population_membership_digest(
    artifacts: PopulationMembershipArtifacts,
    identity: ExternalTemporalExecutionIdentity,
) -> Checksum:
    sections = [
        canonical_json_text(identity),
        canonical_json_text(artifacts.population_manifest.document),
    ]
    if artifacts.chronology is not None:
        sections.append(canonical_json_text(artifacts.chronology))
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest.document))
    return checksum_text("\n".join(sections))


@dataclass(slots=True, eq=False, kw_only=True)
class ConstructPublishedSplitRequest:
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    partition_seed: Seed
    output_directory: Path
    overwrite: bool
    matched_static_reference_manifest: PopulationManifest | None = None
    matched_static_reference_membership: pl.DataFrame | None = None


@dataclass(slots=True, eq=False, kw_only=True)
class ConstructPublishedSplitResult:
    publication_status: PublicationStatus
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None
    complete_digest: Checksum


@dataclass(slots=True, eq=False)
class _PopulationSplitArtifacts:
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None


@dataclass(slots=True, eq=False)
class _PopulationSplitPublication:
    request: ConstructPublishedSplitRequest
    artifacts: _PopulationSplitArtifacts
    digest: Checksum


def construct_published_split(request: ConstructPublishedSplitRequest) -> ConstructPublishedSplitResult:
    document = request.population_manifest.document
    if document.population is not request.population:
        raise ScientificContractError(
            "split request population must match its manifest",
            subject=request.population,
        )
    has_matched_reference = request.matched_static_reference_manifest is not None
    if has_matched_reference and request.matched_static_reference_membership is None:
        raise ScientificContractError(
            "a matched reference manifest requires its matched reference membership",
            subject=request.population,
        )
    assignments, manifest = split_membership(
        SplitConstructionRequest(
            membership=request.membership,
            population=request.population,
            dataset=document.dataset,
            partition_seed=request.partition_seed,
            split_protocol=document.split_protocol,
            population_manifest_checksum=document.membership_checksum,
            capture_timestamp_column=_capture_timestamp_column_for_split(
                document.split_protocol,
                request.membership,
            ),
        )
    )
    validate_split_manifest(request.membership, assignments, manifest)
    static_assignments: pl.DataFrame | None = None
    static_manifest: SplitManifestDocument | None = None
    if has_matched_reference:
        assert request.matched_static_reference_manifest is not None
        assert request.matched_static_reference_membership is not None
        _require_matching_reference_rows(request.membership, request.matched_static_reference_membership)
        static_assignments, static_manifest = split_membership(
            SplitConstructionRequest(
                membership=request.matched_static_reference_membership,
                population=request.population,
                dataset=document.dataset,
                partition_seed=request.partition_seed,
                split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
                population_manifest_checksum=request.matched_static_reference_manifest.document.membership_checksum,
            )
        )
        validate_split_manifest(
            request.matched_static_reference_membership,
            static_assignments,
            static_manifest,
        )
    artifacts = _PopulationSplitArtifacts(assignments, manifest, static_assignments, static_manifest)
    sections = [canonical_json_text(request.execution_identity), canonical_json_text(artifacts.manifest)]
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest))
    prepared = _PopulationSplitPublication(
        request=request,
        artifacts=artifacts,
        digest=checksum_text("\n".join(sections)),
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=_write_population_split,
                validator=_population_split_is_reusable,
                loader=_load_reused_population_split,
                rebaser=_rebase_population_split,
            ),
            overwrite=request.overwrite,
            complete_marker=SplitPublicationAsset.COMPLETE,
        )
    )
    published = publication.value
    return ConstructPublishedSplitResult(
        publication_status=publication.status,
        assignments=published.assignments,
        manifest=published.manifest,
        matched_static_reference_assignments=published.matched_static_reference_assignments,
        matched_static_reference_manifest=published.matched_static_reference_manifest,
        complete_digest=publication.complete_digest,
    )


def _require_matching_reference_rows(temporal: pl.DataFrame, static: pl.DataFrame) -> None:
    row_columns = ("client_id", "stable_row_id")
    temporal_rows = temporal.select(row_columns).sort(row_columns)
    static_rows = static.select(row_columns).sort(row_columns)
    if not temporal_rows.equals(static_rows):
        raise ScientificContractError(
            "matched static reference must use the same client rows",
            subject=PopulationId.EDGE_TEMPORAL_GROUPS,
        )


def _write_population_membership(
    publication: _PopulationMembershipPublication,
    directory: Path,
) -> PopulationMembershipArtifacts:
    artifacts = publication.artifacts
    serialize_json_model(
        publication.execution_identity,
        directory / PopulationPublicationAsset.EXECUTION_IDENTITY,
    )
    serialize_json_model(
        artifacts.population_manifest.document,
        directory / PopulationPublicationAsset.POPULATION_MANIFEST,
    )
    artifacts.membership.write_parquet(directory / PopulationPublicationAsset.MEMBERSHIP)
    if artifacts.chronology is not None:
        serialize_json_model(artifacts.chronology, directory / PopulationPublicationAsset.CHRONOLOGY)
    if (
        artifacts.matched_static_reference_manifest is not None
        and artifacts.matched_static_reference_membership is not None
    ):
        serialize_json_model(
            artifacts.matched_static_reference_manifest.document,
            directory / PopulationPublicationAsset.MATCHED_STATIC_MANIFEST,
        )
        artifacts.matched_static_reference_membership.write_parquet(
            directory / PopulationPublicationAsset.MATCHED_STATIC_MEMBERSHIP
        )
    if artifacts.ciciot_excluded_rows is not None and artifacts.ciciot_client_eligibility is not None:
        artifacts.ciciot_excluded_rows.write_parquet(directory / PopulationPublicationAsset.CICIOT_EXCLUDED_ROWS)
        artifacts.ciciot_client_eligibility.write_parquet(
            directory / PopulationPublicationAsset.CICIOT_CLIENT_ELIGIBILITY
        )
    (directory / PopulationPublicationAsset.COMPLETE).write_text(publication.digest.value, encoding="utf-8")
    return artifacts


def _population_membership_is_reusable(
    publication: _PopulationMembershipPublication,
    directory: Path,
) -> bool:
    complete = directory / PopulationPublicationAsset.COMPLETE
    identity_path = directory / PopulationPublicationAsset.EXECUTION_IDENTITY
    manifest_path = directory / PopulationPublicationAsset.POPULATION_MANIFEST
    membership_path = directory / PopulationPublicationAsset.MEMBERSHIP
    if not (complete.is_file() and identity_path.is_file() and manifest_path.is_file() and membership_path.is_file()):
        return False
    try:
        if complete.read_text(encoding="utf-8").strip() != publication.digest.value:
            return False
        persisted_identity = ExternalTemporalExecutionIdentity.model_validate_json(
            identity_path.read_text(encoding="utf-8")
        )
        if persisted_identity != publication.execution_identity:
            return False
        persisted = PopulationManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return _matches_population_artifacts(directory, publication.artifacts, persisted, membership_path)


def _load_reused_population_membership(
    publication: _PopulationMembershipPublication,
    directory: Path,
) -> PopulationMembershipArtifacts:
    del directory
    return publication.artifacts


def _rebase_population_membership(
    artifacts: PopulationMembershipArtifacts,
    directory: Path,
) -> PopulationMembershipArtifacts:
    del directory
    return artifacts


def _matches_population_artifacts(
    directory: Path,
    expected: PopulationMembershipArtifacts,
    persisted: PopulationManifestDocument,
    membership: Path,
) -> bool:
    if persisted != expected.population_manifest.document:
        return False
    try:
        if membership_frame_checksum(pl.read_parquet(membership)) != persisted.membership_checksum:
            return False
    except (OSError, pl.exceptions.PolarsError):
        return False
    if expected.chronology is not None and not _matches_chronology(directory, expected.chronology):
        return False
    if expected.matched_static_reference_manifest is None:
        return _matches_ciciot_evidence(directory, expected)
    return _matches_static_reference(directory, expected.matched_static_reference_manifest)


def _matches_ciciot_evidence(directory: Path, expected: PopulationMembershipArtifacts) -> bool:
    if expected.ciciot_excluded_rows is None or expected.ciciot_client_eligibility is None:
        return True
    try:
        excluded_rows = pl.read_parquet(directory / PopulationPublicationAsset.CICIOT_EXCLUDED_ROWS)
        client_evidence = pl.read_parquet(directory / PopulationPublicationAsset.CICIOT_CLIENT_ELIGIBILITY)
    except (OSError, pl.exceptions.PolarsError):
        return False
    return excluded_rows.equals(expected.ciciot_excluded_rows) and client_evidence.equals(
        expected.ciciot_client_eligibility
    )


def _matches_chronology(
    directory: Path,
    expected: ChronologicalPartitionDiagnosticsDocument,
) -> bool:
    try:
        persisted = ChronologicalPartitionDiagnosticsDocument.model_validate_json(
            (directory / PopulationPublicationAsset.CHRONOLOGY).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return persisted == expected


def _matches_static_reference(directory: Path, expected: PopulationManifest) -> bool:
    try:
        persisted = PopulationManifestDocument.model_validate_json(
            (directory / PopulationPublicationAsset.MATCHED_STATIC_MANIFEST).read_text(encoding="utf-8")
        )
        membership = directory / PopulationPublicationAsset.MATCHED_STATIC_MEMBERSHIP
        return (
            membership.is_file()
            and persisted == expected.document
            and membership_frame_checksum(pl.read_parquet(membership)) == persisted.membership_checksum
        )
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False


def _write_population_split(
    publication: _PopulationSplitPublication,
    directory: Path,
) -> _PopulationSplitArtifacts:
    artifacts = publication.artifacts
    serialize_json_model(
        publication.request.execution_identity,
        directory / SplitPublicationAsset.EXECUTION_IDENTITY,
    )
    artifacts.assignments.write_parquet(directory / SplitPublicationAsset.ASSIGNMENTS)
    serialize_json_model(artifacts.manifest, directory / SplitPublicationAsset.MANIFEST)
    if (
        artifacts.matched_static_reference_assignments is not None
        and artifacts.matched_static_reference_manifest is not None
    ):
        artifacts.matched_static_reference_assignments.write_parquet(
            directory / SplitPublicationAsset.MATCHED_STATIC_ASSIGNMENTS
        )
        serialize_json_model(
            artifacts.matched_static_reference_manifest,
            directory / SplitPublicationAsset.MATCHED_STATIC_MANIFEST,
        )
    (directory / SplitPublicationAsset.COMPLETE).write_text(publication.digest.value, encoding="utf-8")
    return artifacts


def _population_split_is_reusable(
    publication: _PopulationSplitPublication,
    directory: Path,
) -> bool:
    complete = directory / SplitPublicationAsset.COMPLETE
    identity_path = directory / SplitPublicationAsset.EXECUTION_IDENTITY
    manifest_path = directory / SplitPublicationAsset.MANIFEST
    assignments_path = directory / SplitPublicationAsset.ASSIGNMENTS
    if not (complete.is_file() and identity_path.is_file() and manifest_path.is_file() and assignments_path.is_file()):
        return False
    try:
        if complete.read_text(encoding="utf-8").strip() != publication.digest.value:
            return False
        persisted_identity = ExternalTemporalExecutionIdentity.model_validate_json(
            identity_path.read_text(encoding="utf-8")
        )
        if persisted_identity != publication.request.execution_identity:
            return False
        persisted = SplitManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if persisted != publication.artifacts.manifest:
            return False
        validate_split_manifest(publication.request.membership, pl.read_parquet(assignments_path), persisted)
        expected_static = publication.artifacts.matched_static_reference_manifest
        if expected_static is not None and not _matches_split_static_reference(
            publication.request,
            directory,
            expected_static,
        ):
            return False
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False
    return True


def _load_reused_population_split(
    publication: _PopulationSplitPublication,
    directory: Path,
) -> _PopulationSplitArtifacts:
    del directory
    return publication.artifacts


def _rebase_population_split(
    artifacts: _PopulationSplitArtifacts,
    directory: Path,
) -> _PopulationSplitArtifacts:
    del directory
    return artifacts


def _capture_timestamp_column_for_split(
    split_protocol: SplitProtocolId,
    membership: pl.DataFrame,
) -> CaptureTimestampColumn | None:
    """Resolve the audited capture-time column required for chronological splits.

    Temporal partitioning is roadmap-locked to verified Edge capture timestamps.
    Non-temporal protocols never invent a time column.
    """
    if split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        return None
    column = CaptureTimestampColumn(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
    if column not in membership.columns:
        raise ScientificContractError(
            "temporal splits require a capture-timestamp column in membership",
            subject=ContractSubject.SPLIT,
            reason="chronological partitioning cannot invent time",
        )
    return column


def _matches_split_static_reference(
    request: ConstructPublishedSplitRequest,
    directory: Path,
    expected: SplitManifestDocument,
) -> bool:
    manifest_path = directory / SplitPublicationAsset.MATCHED_STATIC_MANIFEST
    assignments_path = directory / SplitPublicationAsset.MATCHED_STATIC_ASSIGNMENTS
    if not manifest_path.is_file() or not assignments_path.is_file():
        return False
    if request.matched_static_reference_membership is None:
        return False
    static_manifest = SplitManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if static_manifest != expected:
        return False
    validate_split_manifest(
        request.matched_static_reference_membership,
        pl.read_parquet(assignments_path),
        static_manifest,
    )
    return True
