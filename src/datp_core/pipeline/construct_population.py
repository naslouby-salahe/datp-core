"""Population construction, splitting, and deterministic publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.domain.enums import DatasetId, PopulationId, PublicationStatus, SplitProtocolId
from datp_core.domain.values import Checksum, Seed
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.pipeline.publication.serialization import serialize_json_model
from datp_core.populations.catalogue import (
    PopulationConstructionRequest as CapabilityPopulationConstructionRequest,
)
from datp_core.populations.catalogue import (
    PopulationConstructionResult as CapabilityPopulationConstructionResult,
)
from datp_core.populations.catalogue import construct_population as construct_population_capability
from datp_core.populations.integrity import membership_frame_checksum
from datp_core.populations.membership import (
    PopulationMembershipArtifacts,
    PopulationMembershipPublication,
    PopulationMembershipRequest,
    prepare_population_membership,
)
from datp_core.populations.models import (
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    PopulationManifest,
    PopulationManifestDocument,
    SplitConstructionRequest,
    SplitManifestDocument,
)
from datp_core.populations.splits import split_membership
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


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
    stage: PipelineStage
    construction: CapabilityPopulationConstructionResult
    split_assignments: pl.DataFrame
    split_manifest: SplitManifestDocument


def construct_declared_population(
    request: ConstructDeclaredPopulationRequest,
) -> ConstructDeclaredPopulationResult:
    construction = construct_population_capability(
        CapabilityPopulationConstructionRequest(
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
        )
    )
    return ConstructDeclaredPopulationResult(
        stage=PipelineStage.CONSTRUCT_POPULATION,
        construction=construction,
        split_assignments=assignments,
        split_manifest=manifest,
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
    stage: PipelineStage
    publication_status: PublicationStatus
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    complete_digest: Checksum
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


def construct_published_population(
    request: ConstructPublishedPopulationRequest,
) -> ConstructPublishedPopulationResult:
    prepared = prepare_population_membership(
        PopulationMembershipRequest(
            canonical_root=request.canonical_root,
            population=request.population,
            execution_identity=request.execution_identity,
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
        )
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
    artifacts = publication.value
    return ConstructPublishedPopulationResult(
        stage=PipelineStage.CONSTRUCT_POPULATION,
        publication_status=publication.status,
        population_manifest=artifacts.population_manifest,
        membership=artifacts.membership,
        chronology=artifacts.chronology,
        matched_static_reference_manifest=artifacts.matched_static_reference_manifest,
        matched_static_reference_membership=artifacts.matched_static_reference_membership,
        complete_digest=publication.complete_digest,
        ciciot_excluded_rows=artifacts.ciciot_excluded_rows,
        ciciot_client_eligibility=artifacts.ciciot_client_eligibility,
    )


def _write_population_membership(
    publication: PopulationMembershipPublication,
    directory: Path,
) -> PopulationMembershipArtifacts:
    artifacts = publication.artifacts
    serialize_json_model(
        publication.request.execution_identity,
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
    publication: PopulationMembershipPublication,
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
        if persisted_identity != publication.request.execution_identity:
            return False
        persisted = PopulationManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return _matches_population_artifacts(directory, publication.artifacts, persisted, membership_path)


def _load_reused_population_membership(
    publication: PopulationMembershipPublication,
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
