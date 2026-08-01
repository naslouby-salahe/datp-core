"""External and temporal population construction with deterministic publication."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_file, checksum_text
from datp_core.populations.ciciot_file_clients import build_ciciot_file_clients
from datp_core.populations.edge_sensor_groups import build_edge_sensor_groups
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.models import ChronologicalPartitionDiagnostics, PopulationManifest


@dataclass(frozen=True, slots=True)
class ConstructPopulationRequest:
    canonical_root: Path
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    output_directory: Path
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ConstructPopulationResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnostics | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    complete_digest: Checksum


def construct_population_stage(request: ConstructPopulationRequest) -> ConstructPopulationResult:
    """Build only declared Phase 11 populations; confirmatory population dispatch is excluded."""
    result = _build(request)
    payload = _manifest_payload(result)
    digest = checksum_text(payload)

    def write(temporary: Path) -> None:
        (temporary / "population_manifest.json").write_text(payload, encoding="utf-8")
        result.membership.write_parquet(temporary / "membership.parquet")
        if result.chronology is not None:
            (temporary / "chronology.json").write_text(
                result.chronology.document.model_dump_json(indent=2) + "\n", encoding="utf-8"
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
        (temporary / "COMPLETE").write_text(digest.value, encoding="utf-8")

    reused = publish_atomically(
        AtomicPublication(
            request.output_directory,
            request.overwrite,
            lambda directory: _is_reusable(directory, digest),
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
                "Phase 11 construction requires an external or temporal population", subject=request.population
            )


def _manifest_payload(result: ConstructPopulationResult) -> str:
    sections = [result.population_manifest.document.model_dump_json(indent=2)]
    if result.chronology is not None:
        sections.append(result.chronology.document.model_dump_json(indent=2))
    if result.matched_static_reference_manifest is not None:
        sections.append(result.matched_static_reference_manifest.document.model_dump_json(indent=2))
    return "\n".join(sections) + "\n"


def _is_reusable(directory: Path, digest: Checksum) -> bool:
    complete = directory / "COMPLETE"
    manifest = directory / "population_manifest.json"
    return complete.is_file() and manifest.is_file() and complete.read_text(encoding="utf-8").strip() == digest.value
