"""Population split construction, validation, and deterministic publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import canonical_json_text, serialize_json_model
from datp_core.datasets.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_text
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.populations.edge_temporal_groups import split_temporal_membership
from datp_core.populations.integrity import validate_no_future_history_leakage, validate_split_manifest
from datp_core.populations.models import PopulationManifest, SplitConstructionRequest, SplitManifestDocument
from datp_core.populations.splits import split_membership


class SplitPublicationAsset(StrEnum):
    EXECUTION_IDENTITY = "execution_identity.json"
    ASSIGNMENTS = "split_assignments.parquet"
    MANIFEST = "split_manifest.json"
    MATCHED_STATIC_ASSIGNMENTS = "matched_static_reference_assignments.parquet"
    MATCHED_STATIC_MANIFEST = "matched_static_reference_split_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(slots=True, eq=False)
class PopulationSplitRequest:
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    partition_seed: Seed
    matched_static_reference_manifest: PopulationManifest | None = None
    matched_static_reference_membership: pl.DataFrame | None = None

    def __post_init__(self) -> None:
        require_execution_identity(self.execution_identity, self.population)


@dataclass(slots=True, eq=False)
class PopulationSplitArtifacts:
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None


@dataclass(slots=True, eq=False)
class PopulationSplitPublication:
    request: PopulationSplitRequest
    artifacts: PopulationSplitArtifacts
    digest: Checksum


def prepare_population_split(request: PopulationSplitRequest) -> PopulationSplitPublication:
    artifacts = construct_population_split(request)
    return PopulationSplitPublication(
        request=request,
        artifacts=artifacts,
        digest=checksum_text(_manifest_payload(artifacts, request.execution_identity)),
    )


def construct_population_split(request: PopulationSplitRequest) -> PopulationSplitArtifacts:
    """Construct an external or temporal split and its matched static reference when required."""
    document = request.population_manifest.document
    if document.population is not request.population:
        raise ScientificContractError(
            "split request population must match its manifest",
            subject=request.population,
        )
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
                population_manifest_checksum=(
                    request.matched_static_reference_manifest.document.membership_checksum
                ),
            )
        )
        _require_matching_reference_rows(
            request.membership,
            request.matched_static_reference_membership,
        )
        validate_split_manifest(
            request.matched_static_reference_membership,
            static_assignments,
            static_manifest,
        )
        return PopulationSplitArtifacts(
            assignments,
            manifest,
            static_assignments,
            static_manifest,
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
    return PopulationSplitArtifacts(assignments, manifest, None, None)


def write_population_split(
    publication: PopulationSplitPublication,
    directory: Path,
) -> PopulationSplitArtifacts:
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
    (directory / SplitPublicationAsset.COMPLETE).write_text(
        publication.digest.value,
        encoding="utf-8",
    )
    return artifacts


def population_split_is_reusable(
    publication: PopulationSplitPublication,
    directory: Path,
) -> bool:
    complete = directory / SplitPublicationAsset.COMPLETE
    identity_path = directory / SplitPublicationAsset.EXECUTION_IDENTITY
    manifest_path = directory / SplitPublicationAsset.MANIFEST
    assignments_path = directory / SplitPublicationAsset.ASSIGNMENTS
    if not (
        complete.is_file()
        and identity_path.is_file()
        and manifest_path.is_file()
        and assignments_path.is_file()
    ):
        return False
    try:
        if complete.read_text(encoding="utf-8").strip() != publication.digest.value:
            return False
        persisted_identity = ExternalTemporalExecutionIdentity.model_validate_json(
            identity_path.read_text(encoding="utf-8")
        )
        if persisted_identity != publication.request.execution_identity:
            return False
        persisted = SplitManifestDocument.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        if persisted != publication.artifacts.manifest:
            return False
        validate_split_manifest(
            publication.request.membership,
            pl.read_parquet(assignments_path),
            persisted,
        )
        expected_static = publication.artifacts.matched_static_reference_manifest
        if expected_static is not None:
            if not _matches_static_reference(publication.request, directory, expected_static):
                return False
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False
    return True


def load_reused_population_split(
    publication: PopulationSplitPublication,
    directory: Path,
) -> PopulationSplitArtifacts:
    del directory
    return publication.artifacts


def rebase_population_split(
    artifacts: PopulationSplitArtifacts,
    directory: Path,
) -> PopulationSplitArtifacts:
    del directory
    return artifacts


def _matches_static_reference(
    request: PopulationSplitRequest,
    directory: Path,
    expected: SplitManifestDocument,
) -> bool:
    manifest_path = directory / SplitPublicationAsset.MATCHED_STATIC_MANIFEST
    assignments_path = directory / SplitPublicationAsset.MATCHED_STATIC_ASSIGNMENTS
    if not manifest_path.is_file() or not assignments_path.is_file():
        return False
    if request.matched_static_reference_membership is None:
        return False
    static_manifest = SplitManifestDocument.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if static_manifest != expected:
        return False
    validate_split_manifest(
        request.matched_static_reference_membership,
        pl.read_parquet(assignments_path),
        static_manifest,
    )
    return True


def _require_matching_reference_rows(temporal: pl.DataFrame, static: pl.DataFrame) -> None:
    row_columns = ("client_id", "stable_row_id")
    temporal_rows = temporal.select(row_columns).sort(row_columns)
    static_rows = static.select(row_columns).sort(row_columns)
    if not temporal_rows.equals(static_rows):
        raise ScientificContractError(
            "matched static reference must use the same client rows",
            subject=PopulationId.EDGE_TEMPORAL_GROUPS,
        )


def _manifest_payload(
    artifacts: PopulationSplitArtifacts,
    identity: ExternalTemporalExecutionIdentity,
) -> str:
    sections = [canonical_json_text(identity), canonical_json_text(artifacts.manifest)]
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest))
    return "\n".join(sections)
