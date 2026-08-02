"""External and temporal population construction with deterministic publication."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_file, checksum_text
from datp_core.experiments.models import (
    ExecutionIdentityDocument,
    ExternalTemporalExecutionIdentity,
    require_execution_identity,
)
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


@dataclass(frozen=True, slots=True)
class ConstructPopulationResult:
    stage: StageOperationId
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
    result = _build(request)
    payload = _manifest_payload(result, request.execution_identity)
    digest = checksum_text(payload)

    def write(temporary: Path) -> None:
        (temporary / "execution_identity.json").write_text(
            request.execution_identity.document.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (temporary / "population_manifest.json").write_text(
            result.population_manifest.document.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        result.membership.write_parquet(temporary / "membership.parquet")
        if result.chronology is not None:
            (temporary / "chronology.json").write_text(
                result.chronology.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
        if (
            result.matched_static_reference_manifest is not None
            and result.matched_static_reference_membership is not None
        ):
            (temporary / "matched_static_reference_manifest.json").write_text(
                result.matched_static_reference_manifest.document.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            result.matched_static_reference_membership.write_parquet(
                temporary / "matched_static_reference_membership.parquet"
            )
        if result.ciciot_excluded_rows is not None and result.ciciot_client_eligibility is not None:
            result.ciciot_excluded_rows.write_parquet(temporary / "ciciot_excluded_rows.parquet")
            result.ciciot_client_eligibility.write_parquet(temporary / "ciciot_client_eligibility.parquet")
        (temporary / "COMPLETE").write_text(digest.value, encoding="utf-8")

    reused = publish_atomically(
        AtomicPublication(
            request.output_directory,
            request.overwrite,
            lambda directory: _is_reusable(directory, result, request.execution_identity, digest),
            write,
            rmtree,
        )
    )
    return ConstructPopulationResult(
        StageOperationId.CONSTRUCT_POPULATION,
        PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED,
        result.population_manifest,
        result.membership,
        result.chronology,
        result.matched_static_reference_manifest,
        result.matched_static_reference_membership,
        checksum_file(request.output_directory / "COMPLETE"),
    )


def _build(request: ConstructPopulationRequest) -> ConstructPopulationResult:
    match request.population:
        case PopulationId.EDGE_SENSOR_GROUPS:
            manifest, membership = build_edge_sensor_groups(
                request.canonical_root, partition_seed=request.partition_seed, split_protocol=request.split_protocol
            )
            return ConstructPopulationResult(
                StageOperationId.CONSTRUCT_POPULATION,
                PublicationStatus.PUBLISHED,
                manifest,
                membership,
                None,
                None,
                None,
                checksum_text("unpublished"),
            )
        case PopulationId.CICIOT_FILE_CLIENTS:
            manifest, membership = build_ciciot_file_clients(
                request.canonical_root, partition_seed=request.partition_seed, split_protocol=request.split_protocol
            )
            excluded_rows = ciciot_excluded_row_evidence(request.canonical_root)
            return ConstructPopulationResult(
                StageOperationId.CONSTRUCT_POPULATION,
                PublicationStatus.PUBLISHED,
                manifest,
                membership,
                None,
                None,
                None,
                checksum_text("unpublished"),
                excluded_rows,
                ciciot_client_eligibility_evidence(excluded_rows),
            )
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            manifest, membership, chronology, static_manifest, static_membership = build_edge_temporal_groups(
                request.canonical_root, partition_seed=request.partition_seed, split_protocol=request.split_protocol
            )
            return ConstructPopulationResult(
                StageOperationId.CONSTRUCT_POPULATION,
                PublicationStatus.PUBLISHED,
                manifest,
                membership,
                chronology,
                static_manifest,
                static_membership,
                checksum_text("unpublished"),
            )
        case _:
            raise ScientificContractError(
                "construction requires an external or temporal population", subject=request.population
            )


def _manifest_payload(result: ConstructPopulationResult, identity: ExternalTemporalExecutionIdentity) -> str:
    sections = [
        identity.document.model_dump_json(indent=2),
        result.population_manifest.document.model_dump_json(indent=2),
    ]
    if result.chronology is not None:
        sections.append(result.chronology.model_dump_json(indent=2))
    if result.matched_static_reference_manifest is not None:
        sections.append(result.matched_static_reference_manifest.document.model_dump_json(indent=2))
    return "\n".join(sections) + "\n"


def _is_reusable(
    directory: Path,
    expected: ConstructPopulationResult,
    identity: ExternalTemporalExecutionIdentity,
    digest: Checksum,
) -> bool:
    complete = directory / "COMPLETE"
    identity_path = directory / "execution_identity.json"
    manifest = directory / "population_manifest.json"
    membership = directory / "membership.parquet"
    if not (
        complete.is_file()
        and identity_path.is_file()
        and manifest.is_file()
        and membership.is_file()
        and complete.read_text(encoding="utf-8").strip() == digest.value
    ):
        return False
    try:
        if identity.document != _read_execution_identity(identity_path):
            return False
        persisted = PopulationManifestDocument.model_validate_json(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return _matches_population_artifacts(directory, expected, persisted, membership)


def _read_execution_identity(path: Path) -> ExecutionIdentityDocument:
    return ExecutionIdentityDocument.model_validate_json(path.read_text(encoding="utf-8"))


def _matches_population_artifacts(
    directory: Path,
    expected: ConstructPopulationResult,
    persisted: PopulationManifestDocument,
    membership: Path,
) -> bool:
    if persisted != expected.population_manifest.document:
        return False
    if membership_frame_checksum(pl.read_parquet(membership)) != persisted.membership_checksum:
        return False
    if expected.chronology is not None and not _matches_chronology(directory, expected.chronology):
        return False
    if expected.matched_static_reference_manifest is None:
        return _matches_ciciot_evidence(directory, expected)
    return _matches_static_reference(directory, expected.matched_static_reference_manifest)


def _matches_ciciot_evidence(directory: Path, expected: ConstructPopulationResult) -> bool:
    if expected.ciciot_excluded_rows is None or expected.ciciot_client_eligibility is None:
        return True
    try:
        excluded_rows = pl.read_parquet(directory / "ciciot_excluded_rows.parquet")
        client_evidence = pl.read_parquet(directory / "ciciot_client_eligibility.parquet")
    except OSError:
        return False
    return excluded_rows.equals(expected.ciciot_excluded_rows) and client_evidence.equals(
        expected.ciciot_client_eligibility
    )


def _matches_chronology(directory: Path, expected: ChronologicalPartitionDiagnosticsDocument) -> bool:
    try:
        persisted = ChronologicalPartitionDiagnosticsDocument.model_validate_json(
            (directory / "chronology.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return persisted == expected


def _matches_static_reference(directory: Path, expected: PopulationManifest) -> bool:
    try:
        persisted = PopulationManifestDocument.model_validate_json(
            (directory / "matched_static_reference_manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    membership = directory / "matched_static_reference_membership.parquet"
    return (
        membership.is_file()
        and persisted == expected.document
        and membership_frame_checksum(pl.read_parquet(membership)) == persisted.membership_checksum
    )
