"""External and temporal split publication without mutating canonical membership."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.datasets.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_file, checksum_text
from datp_core.populations.edge_temporal_groups import split_temporal_membership
from datp_core.populations.integrity import validate_no_future_history_leakage, validate_split_manifest
from datp_core.populations.models import PopulationManifest, SplitConstructionRequest, SplitManifest
from datp_core.populations.splits import split_membership


@dataclass(frozen=True, slots=True)
class SplitRequest:
    population: PopulationId
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    partition_seed: Seed
    output_directory: Path
    overwrite: bool
    matched_static_reference_manifest: PopulationManifest | None = None
    matched_static_reference_membership: pl.DataFrame | None = None


@dataclass(frozen=True, slots=True)
class SplitResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    assignments: pl.DataFrame
    manifest: SplitManifest
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifest | None
    complete_digest: Checksum


def split_stage(request: SplitRequest) -> SplitResult:
    """Split a Phase 11 population and, for temporal inputs, its row-matched static reference."""
    result = _split(request)
    payload = _manifest_payload(result)
    digest = checksum_text(payload)

    def write(temporary: Path) -> None:
        result.assignments.write_parquet(temporary / "split_assignments.parquet")
        (temporary / "split_manifest.json").write_text(payload, encoding="utf-8")
        if (
            result.matched_static_reference_assignments is not None
            and result.matched_static_reference_manifest is not None
        ):
            result.matched_static_reference_assignments.write_parquet(
                temporary / "matched_static_reference_assignments.parquet"
            )
            (temporary / "matched_static_reference_split_manifest.json").write_text(
                result.matched_static_reference_manifest.document.model_dump_json(indent=2) + "\n", encoding="utf-8"
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
    return SplitResult(
        StageOperationId.SPLIT,
        PublicationStatus.REUSED if reused else PublicationStatus.PUBLISHED,
        result.assignments,
        result.manifest,
        result.matched_static_reference_assignments,
        result.matched_static_reference_manifest,
        checksum_file(request.output_directory / "COMPLETE"),
    )


def _split(request: SplitRequest) -> SplitResult:
    document = request.population_manifest.document
    if document.population is not request.population:
        raise ScientificContractError("split request population must match its manifest", subject=request.population)
    if request.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        if request.matched_static_reference_manifest is None or request.matched_static_reference_membership is None:
            raise ScientificContractError(
                "temporal execution requires its matched static reference", subject=request.population
            )
        assignments, manifest = split_temporal_membership(
            request.membership,
            partition_seed=request.partition_seed,
            population_manifest_checksum=document.membership_checksum,
        )
        validate_split_manifest(request.membership, assignments, manifest)
        validate_no_future_history_leakage(assignments, EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
        static_assignments, static_manifest = split_membership(
            SplitConstructionRequest(
                membership=request.matched_static_reference_membership,
                population=PopulationId.EDGE_TEMPORAL_GROUPS,
                dataset=document.dataset,
                partition_seed=request.partition_seed,
                split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
                population_manifest_checksum=request.matched_static_reference_manifest.document.membership_checksum,
            )
        )
        _require_matching_reference_rows(request.membership, request.matched_static_reference_membership)
        validate_split_manifest(request.matched_static_reference_membership, static_assignments, static_manifest)
        return SplitResult(
            StageOperationId.SPLIT,
            PublicationStatus.PUBLISHED,
            assignments,
            manifest,
            static_assignments,
            static_manifest,
            checksum_text("unpublished"),
        )
    assignments, manifest = split_membership(
        SplitConstructionRequest(
            membership=request.membership,
            population=request.population,
            dataset=document.dataset,
            partition_seed=request.partition_seed,
            split_protocol=document.split_protocol,
            population_manifest_checksum=document.membership_checksum,
        )
    )
    validate_split_manifest(request.membership, assignments, manifest)
    return SplitResult(
        StageOperationId.SPLIT,
        PublicationStatus.PUBLISHED,
        assignments,
        manifest,
        None,
        None,
        checksum_text("unpublished"),
    )


def _require_matching_reference_rows(temporal: pl.DataFrame, static: pl.DataFrame) -> None:
    temporal_rows = temporal.select("client_id", "stable_row_id").sort(["client_id", "stable_row_id"])
    static_rows = static.select("client_id", "stable_row_id").sort(["client_id", "stable_row_id"])
    if not temporal_rows.equals(static_rows):
        raise ScientificContractError(
            "matched static reference must use the same client rows", subject=PopulationId.EDGE_TEMPORAL_GROUPS
        )


def _manifest_payload(result: SplitResult) -> str:
    payload = result.manifest.document.model_dump_json(indent=2)
    if result.matched_static_reference_manifest is not None:
        payload += "\n" + result.matched_static_reference_manifest.document.model_dump_json(indent=2)
    return payload + "\n"


def _is_reusable(directory: Path, digest: Checksum) -> bool:
    complete = directory / "COMPLETE"
    manifest = directory / "split_manifest.json"
    return complete.is_file() and manifest.is_file() and complete.read_text(encoding="utf-8").strip() == digest.value
