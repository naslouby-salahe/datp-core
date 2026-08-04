"""External and temporal split publication without mutating canonical membership."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

import polars as pl

from datp_core.artifacts.serialization import canonical_json_text, serialize_json_model
from datp_core.datasets.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_text
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.pipeline.publication.atomic import publish_atomically
from datp_core.populations.edge_temporal_groups import split_temporal_membership
from datp_core.populations.integrity import validate_no_future_history_leakage, validate_split_manifest
from datp_core.populations.models import PopulationManifest, SplitConstructionRequest, SplitManifestDocument
from datp_core.populations.splits import split_membership

EXECUTION_IDENTITY_ASSET = "execution_identity.json"
SPLIT_ASSIGNMENTS_ASSET = "split_assignments.parquet"
SPLIT_MANIFEST_ASSET = "split_manifest.json"
MATCHED_STATIC_ASSIGNMENTS_ASSET = "matched_static_reference_assignments.parquet"
MATCHED_STATIC_MANIFEST_ASSET = "matched_static_reference_split_manifest.json"
COMPLETE_ASSET = "COMPLETE"


@dataclass(slots=True, eq=False)
class SplitRequest:
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    partition_seed: Seed
    output_directory: Path
    overwrite: bool
    matched_static_reference_manifest: PopulationManifest | None = None
    matched_static_reference_membership: pl.DataFrame | None = None

    def __post_init__(self) -> None:
        require_execution_identity(self.execution_identity, self.population)


@dataclass(slots=True, eq=False)
class _SplitArtifacts:
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None


@dataclass(slots=True, eq=False)
class SplitResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SPLIT
    publication_status: PublicationStatus
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None
    complete_digest: Checksum


def split_stage(request: SplitRequest) -> SplitResult:
    """Split an external or temporal population and its row-matched static reference when required."""
    artifacts = _split(request)
    digest = checksum_text(_manifest_payload(artifacts, request.execution_identity))

    def write(temporary: Path) -> _SplitArtifacts:
        serialize_json_model(request.execution_identity, temporary / EXECUTION_IDENTITY_ASSET)
        artifacts.assignments.write_parquet(temporary / SPLIT_ASSIGNMENTS_ASSET)
        serialize_json_model(artifacts.manifest, temporary / SPLIT_MANIFEST_ASSET)
        if (
            artifacts.matched_static_reference_assignments is not None
            and artifacts.matched_static_reference_manifest is not None
        ):
            artifacts.matched_static_reference_assignments.write_parquet(
                temporary / MATCHED_STATIC_ASSIGNMENTS_ASSET
            )
            serialize_json_model(
                artifacts.matched_static_reference_manifest,
                temporary / MATCHED_STATIC_MANIFEST_ASSET,
            )
        (temporary / COMPLETE_ASSET).write_text(digest.value, encoding="utf-8")
        return artifacts

    outcome = publish_atomically(
        target=request.output_directory,
        overwrite=request.overwrite,
        is_reusable=lambda directory: _is_reusable(directory, request, artifacts, digest),
        write=write,
        reusable_value=lambda _directory: artifacts,
        remove_target=rmtree,
    )
    return SplitResult(
        publication_status=outcome.status,
        assignments=outcome.value.assignments,
        manifest=outcome.value.manifest,
        matched_static_reference_assignments=outcome.value.matched_static_reference_assignments,
        matched_static_reference_manifest=outcome.value.matched_static_reference_manifest,
        complete_digest=outcome.complete_digest,
    )


def _split(request: SplitRequest) -> _SplitArtifacts:
    document = request.population_manifest.document
    if document.population is not request.population:
        raise ScientificContractError("split request population must match its manifest", subject=request.population)
    if request.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        if request.matched_static_reference_manifest is None or request.matched_static_reference_membership is None:
            raise ScientificContractError(
                "temporal execution requires its matched static reference",
                subject=request.population,
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
        return _SplitArtifacts(assignments, manifest, static_assignments, static_manifest)
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
    return _SplitArtifacts(assignments, manifest, None, None)


def _require_matching_reference_rows(temporal: pl.DataFrame, static: pl.DataFrame) -> None:
    row_columns = ("client_id", "stable_row_id")
    temporal_rows = temporal.select(row_columns).sort(row_columns)
    static_rows = static.select(row_columns).sort(row_columns)
    if not temporal_rows.equals(static_rows):
        raise ScientificContractError(
            "matched static reference must use the same client rows",
            subject=PopulationId.EDGE_TEMPORAL_GROUPS,
        )


def _manifest_payload(artifacts: _SplitArtifacts, identity: ExternalTemporalExecutionIdentity) -> str:
    sections = [canonical_json_text(identity), canonical_json_text(artifacts.manifest)]
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest))
    return "\n".join(sections)


def _is_reusable(
    directory: Path,
    request: SplitRequest,
    expected: _SplitArtifacts,
    digest: Checksum,
) -> bool:
    complete = directory / COMPLETE_ASSET
    identity_path = directory / EXECUTION_IDENTITY_ASSET
    manifest_path = directory / SPLIT_MANIFEST_ASSET
    assignments_path = directory / SPLIT_ASSIGNMENTS_ASSET
    if not (
        complete.is_file()
        and identity_path.is_file()
        and manifest_path.is_file()
        and assignments_path.is_file()
        and complete.read_text(encoding="utf-8").strip() == digest.value
    ):
        return False
    try:
        persisted_identity = ExternalTemporalExecutionIdentity.model_validate_json(
            identity_path.read_text(encoding="utf-8")
        )
        if persisted_identity != request.execution_identity:
            return False
        persisted = SplitManifestDocument.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if persisted != expected.manifest:
            return False
        validate_split_manifest(request.membership, pl.read_parquet(assignments_path), persisted)
        if expected.matched_static_reference_manifest is not None:
            static_manifest_path = directory / MATCHED_STATIC_MANIFEST_ASSET
            static_assignments_path = directory / MATCHED_STATIC_ASSIGNMENTS_ASSET
            if not static_manifest_path.is_file() or not static_assignments_path.is_file():
                return False
            static_manifest = SplitManifestDocument.model_validate_json(
                static_manifest_path.read_text(encoding="utf-8")
            )
            if static_manifest != expected.matched_static_reference_manifest:
                return False
            if request.matched_static_reference_membership is None:
                return False
            validate_split_manifest(
                request.matched_static_reference_membership,
                pl.read_parquet(static_assignments_path),
                static_manifest,
            )
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False
    return True
