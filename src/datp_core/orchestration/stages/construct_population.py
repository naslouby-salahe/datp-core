"""External and temporal population construction with deterministic publication."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

import polars as pl

from datp_core.artifacts.serialization import canonical_json_text, serialize_json_model
from datp_core.artifacts.store import publish_atomically
from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_text
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.populations.ciciot_file_clients import (
    build_ciciot_file_clients,
    ciciot_client_eligibility_evidence,
    ciciot_excluded_row_evidence,
)
from datp_core.populations.edge_sensor_groups import build_edge_sensor_groups
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.integrity import membership_frame_checksum
from datp_core.populations.models import (
    ChronologicalPartitionDiagnosticsDocument,
    PopulationManifest,
    PopulationManifestDocument,
)

EXECUTION_IDENTITY_ASSET = "execution_identity.json"
POPULATION_MANIFEST_ASSET = "population_manifest.json"
MEMBERSHIP_ASSET = "membership.parquet"
CHRONOLOGY_ASSET = "chronology.json"
MATCHED_STATIC_MANIFEST_ASSET = "matched_static_reference_manifest.json"
MATCHED_STATIC_MEMBERSHIP_ASSET = "matched_static_reference_membership.parquet"
CICIOT_EXCLUDED_ROWS_ASSET = "ciciot_excluded_rows.parquet"
CICIOT_CLIENT_ELIGIBILITY_ASSET = "ciciot_client_eligibility.parquet"
COMPLETE_ASSET = "COMPLETE"


@dataclass(frozen=True, slots=True)
class ConstructPopulationRequest:
    canonical_root: Path
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    partition_seed: Seed
    split_protocol: SplitProtocolId
    output_directory: Path
    overwrite: bool

    def __post_init__(self) -> None:
        require_execution_identity(self.execution_identity, self.population)


@dataclass(slots=True, eq=False)
class _PopulationArtifacts:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


@dataclass(slots=True, eq=False)
class ConstructPopulationResult:
    stage: ClassVar[StageOperationId] = StageOperationId.CONSTRUCT_POPULATION
    publication_status: PublicationStatus
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    complete_digest: Checksum
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


def construct_population_stage(request: ConstructPopulationRequest) -> ConstructPopulationResult:
    """Build only declared external or temporal populations; confirmatory dispatch is excluded."""
    artifacts = _build(request)
    digest = checksum_text(_manifest_payload(artifacts, request.execution_identity))

    def write(temporary: Path) -> _PopulationArtifacts:
        serialize_json_model(request.execution_identity, temporary / EXECUTION_IDENTITY_ASSET)
        serialize_json_model(artifacts.population_manifest.document, temporary / POPULATION_MANIFEST_ASSET)
        artifacts.membership.write_parquet(temporary / MEMBERSHIP_ASSET)
        if artifacts.chronology is not None:
            serialize_json_model(artifacts.chronology, temporary / CHRONOLOGY_ASSET)
        if (
            artifacts.matched_static_reference_manifest is not None
            and artifacts.matched_static_reference_membership is not None
        ):
            serialize_json_model(
                artifacts.matched_static_reference_manifest.document,
                temporary / MATCHED_STATIC_MANIFEST_ASSET,
            )
            artifacts.matched_static_reference_membership.write_parquet(
                temporary / MATCHED_STATIC_MEMBERSHIP_ASSET
            )
        if artifacts.ciciot_excluded_rows is not None and artifacts.ciciot_client_eligibility is not None:
            artifacts.ciciot_excluded_rows.write_parquet(temporary / CICIOT_EXCLUDED_ROWS_ASSET)
            artifacts.ciciot_client_eligibility.write_parquet(temporary / CICIOT_CLIENT_ELIGIBILITY_ASSET)
        (temporary / COMPLETE_ASSET).write_text(digest.value, encoding="utf-8")
        return artifacts

    outcome = publish_atomically(
        target=request.output_directory,
        overwrite=request.overwrite,
        is_reusable=lambda directory: _is_reusable(directory, artifacts, request.execution_identity, digest),
        write=write,
        reusable_value=lambda _directory: artifacts,
        remove_target=rmtree,
    )
    value = outcome.value
    return ConstructPopulationResult(
        publication_status=outcome.status,
        population_manifest=value.population_manifest,
        membership=value.membership,
        chronology=value.chronology,
        matched_static_reference_manifest=value.matched_static_reference_manifest,
        matched_static_reference_membership=value.matched_static_reference_membership,
        complete_digest=outcome.complete_digest,
        ciciot_excluded_rows=value.ciciot_excluded_rows,
        ciciot_client_eligibility=value.ciciot_client_eligibility,
    )


def _build(request: ConstructPopulationRequest) -> _PopulationArtifacts:
    match request.population:
        case PopulationId.EDGE_SENSOR_GROUPS:
            manifest, membership = build_edge_sensor_groups(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            return _PopulationArtifacts(manifest, membership, None, None, None)
        case PopulationId.CICIOT_FILE_CLIENTS:
            manifest, membership = build_ciciot_file_clients(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            excluded_rows = ciciot_excluded_row_evidence(request.canonical_root)
            return _PopulationArtifacts(
                manifest,
                membership,
                None,
                None,
                None,
                excluded_rows,
                ciciot_client_eligibility_evidence(excluded_rows),
            )
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            manifest, membership, chronology, static_manifest, static_membership = build_edge_temporal_groups(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            return _PopulationArtifacts(manifest, membership, chronology, static_manifest, static_membership)
        case _:
            raise ScientificContractError(
                "construction requires an external or temporal population",
                subject=request.population,
            )


def _manifest_payload(artifacts: _PopulationArtifacts, identity: ExternalTemporalExecutionIdentity) -> str:
    sections = [
        canonical_json_text(identity),
        canonical_json_text(artifacts.population_manifest.document),
    ]
    if artifacts.chronology is not None:
        sections.append(canonical_json_text(artifacts.chronology))
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest.document))
    return "\n".join(sections)


def _is_reusable(
    directory: Path,
    expected: _PopulationArtifacts,
    identity: ExternalTemporalExecutionIdentity,
    digest: Checksum,
) -> bool:
    complete = directory / COMPLETE_ASSET
    identity_path = directory / EXECUTION_IDENTITY_ASSET
    manifest_path = directory / POPULATION_MANIFEST_ASSET
    membership_path = directory / MEMBERSHIP_ASSET
    if not (
        complete.is_file()
        and identity_path.is_file()
        and manifest_path.is_file()
        and membership_path.is_file()
        and complete.read_text(encoding="utf-8").strip() == digest.value
    ):
        return False
    try:
        persisted_identity = ExternalTemporalExecutionIdentity.model_validate_json(
            identity_path.read_text(encoding="utf-8")
        )
        if persisted_identity != identity:
            return False
        persisted = PopulationManifestDocument.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return _matches_population_artifacts(directory, expected, persisted, membership_path)


def _matches_population_artifacts(
    directory: Path,
    expected: _PopulationArtifacts,
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


def _matches_ciciot_evidence(directory: Path, expected: _PopulationArtifacts) -> bool:
    if expected.ciciot_excluded_rows is None or expected.ciciot_client_eligibility is None:
        return True
    try:
        excluded_rows = pl.read_parquet(directory / CICIOT_EXCLUDED_ROWS_ASSET)
        client_evidence = pl.read_parquet(directory / CICIOT_CLIENT_ELIGIBILITY_ASSET)
    except (OSError, pl.exceptions.PolarsError):
        return False
    return excluded_rows.equals(expected.ciciot_excluded_rows) and client_evidence.equals(
        expected.ciciot_client_eligibility
    )


def _matches_chronology(directory: Path, expected: ChronologicalPartitionDiagnosticsDocument) -> bool:
    try:
        persisted = ChronologicalPartitionDiagnosticsDocument.model_validate_json(
            (directory / CHRONOLOGY_ASSET).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return persisted == expected


def _matches_static_reference(directory: Path, expected: PopulationManifest) -> bool:
    try:
        persisted = PopulationManifestDocument.model_validate_json(
            (directory / MATCHED_STATIC_MANIFEST_ASSET).read_text(encoding="utf-8")
        )
        membership = directory / MATCHED_STATIC_MEMBERSHIP_ASSET
        return (
            membership.is_file()
            and persisted == expected.document
            and membership_frame_checksum(pl.read_parquet(membership)) == persisted.membership_checksum
        )
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False
