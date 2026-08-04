"""Population membership construction and deterministic artifact publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import canonical_json_text, serialize_json_model
from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, Seed, checksum_text
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
from datp_core.protocols.experiments import (
    ExternalTemporalExecutionIdentity,
    require_execution_identity,
)


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


@dataclass(frozen=True, slots=True)
class PopulationMembershipRequest:
    canonical_root: Path
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    partition_seed: Seed
    split_protocol: SplitProtocolId

    def __post_init__(self) -> None:
        require_execution_identity(self.execution_identity, self.population)


@dataclass(slots=True, eq=False)
class PopulationMembershipArtifacts:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None


@dataclass(slots=True, eq=False)
class PopulationMembershipPublication:
    request: PopulationMembershipRequest
    artifacts: PopulationMembershipArtifacts
    digest: Checksum


def prepare_population_membership(
    request: PopulationMembershipRequest,
) -> PopulationMembershipPublication:
    artifacts = build_population_membership(request)
    return PopulationMembershipPublication(
        request=request,
        artifacts=artifacts,
        digest=checksum_text(
            _manifest_payload(artifacts, request.execution_identity)
        ),
    )


def build_population_membership(
    request: PopulationMembershipRequest,
) -> PopulationMembershipArtifacts:
    """Build only declared external or temporal populations."""
    match request.population:
        case PopulationId.EDGE_SENSOR_GROUPS:
            manifest, membership = build_edge_sensor_groups(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            return PopulationMembershipArtifacts(
                manifest,
                membership,
                None,
                None,
                None,
            )
        case PopulationId.CICIOT_FILE_CLIENTS:
            manifest, membership = build_ciciot_file_clients(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            excluded_rows = ciciot_excluded_row_evidence(
                request.canonical_root
            )
            return PopulationMembershipArtifacts(
                manifest,
                membership,
                None,
                None,
                None,
                excluded_rows,
                ciciot_client_eligibility_evidence(excluded_rows),
            )
        case PopulationId.EDGE_TEMPORAL_GROUPS:
            (
                manifest,
                membership,
                chronology,
                static_manifest,
                static_membership,
            ) = build_edge_temporal_groups(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            return PopulationMembershipArtifacts(
                manifest,
                membership,
                chronology,
                static_manifest,
                static_membership,
            )
        case _:
            raise ScientificContractError(
                "construction requires an external or temporal population",
                subject=request.population,
            )


def write_population_membership(
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
    artifacts.membership.write_parquet(
        directory / PopulationPublicationAsset.MEMBERSHIP
    )
    if artifacts.chronology is not None:
        serialize_json_model(
            artifacts.chronology,
            directory / PopulationPublicationAsset.CHRONOLOGY,
        )
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
    if (
        artifacts.ciciot_excluded_rows is not None
        and artifacts.ciciot_client_eligibility is not None
    ):
        artifacts.ciciot_excluded_rows.write_parquet(
            directory / PopulationPublicationAsset.CICIOT_EXCLUDED_ROWS
        )
        artifacts.ciciot_client_eligibility.write_parquet(
            directory / PopulationPublicationAsset.CICIOT_CLIENT_ELIGIBILITY
        )
    (directory / PopulationPublicationAsset.COMPLETE).write_text(
        publication.digest.value,
        encoding="utf-8",
    )
    return artifacts


def population_membership_is_reusable(
    publication: PopulationMembershipPublication,
    directory: Path,
) -> bool:
    complete = directory / PopulationPublicationAsset.COMPLETE
    identity_path = directory / PopulationPublicationAsset.EXECUTION_IDENTITY
    manifest_path = directory / PopulationPublicationAsset.POPULATION_MANIFEST
    membership_path = directory / PopulationPublicationAsset.MEMBERSHIP
    if not (
        complete.is_file()
        and identity_path.is_file()
        and manifest_path.is_file()
        and membership_path.is_file()
    ):
        return False
    try:
        if (
            complete.read_text(encoding="utf-8").strip()
            != publication.digest.value
        ):
            return False
        persisted_identity = (
            ExternalTemporalExecutionIdentity.model_validate_json(
                identity_path.read_text(encoding="utf-8")
            )
        )
        if persisted_identity != publication.request.execution_identity:
            return False
        persisted = PopulationManifestDocument.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False
    return _matches_population_artifacts(
        directory,
        publication.artifacts,
        persisted,
        membership_path,
    )


def load_reused_population_membership(
    publication: PopulationMembershipPublication,
    directory: Path,
) -> PopulationMembershipArtifacts:
    del directory
    return publication.artifacts


def rebase_population_membership(
    artifacts: PopulationMembershipArtifacts,
    directory: Path,
) -> PopulationMembershipArtifacts:
    del directory
    return artifacts


def _manifest_payload(
    artifacts: PopulationMembershipArtifacts,
    identity: ExternalTemporalExecutionIdentity,
) -> str:
    sections = [
        canonical_json_text(identity),
        canonical_json_text(artifacts.population_manifest.document),
    ]
    if artifacts.chronology is not None:
        sections.append(canonical_json_text(artifacts.chronology))
    if artifacts.matched_static_reference_manifest is not None:
        sections.append(
            canonical_json_text(
                artifacts.matched_static_reference_manifest.document
            )
        )
    return "\n".join(sections)


def _matches_population_artifacts(
    directory: Path,
    expected: PopulationMembershipArtifacts,
    persisted: PopulationManifestDocument,
    membership: Path,
) -> bool:
    if persisted != expected.population_manifest.document:
        return False
    try:
        if (
            membership_frame_checksum(pl.read_parquet(membership))
            != persisted.membership_checksum
        ):
            return False
    except (OSError, pl.exceptions.PolarsError):
        return False
    if expected.chronology is not None and not _matches_chronology(
        directory,
        expected.chronology,
    ):
        return False
    if expected.matched_static_reference_manifest is None:
        return _matches_ciciot_evidence(directory, expected)
    return _matches_static_reference(
        directory,
        expected.matched_static_reference_manifest,
    )


def _matches_ciciot_evidence(
    directory: Path,
    expected: PopulationMembershipArtifacts,
) -> bool:
    if (
        expected.ciciot_excluded_rows is None
        or expected.ciciot_client_eligibility is None
    ):
        return True
    try:
        excluded_rows = pl.read_parquet(
            directory / PopulationPublicationAsset.CICIOT_EXCLUDED_ROWS
        )
        client_evidence = pl.read_parquet(
            directory / PopulationPublicationAsset.CICIOT_CLIENT_ELIGIBILITY
        )
    except (OSError, pl.exceptions.PolarsError):
        return False
    return excluded_rows.equals(
        expected.ciciot_excluded_rows
    ) and client_evidence.equals(expected.ciciot_client_eligibility)


def _matches_chronology(
    directory: Path,
    expected: ChronologicalPartitionDiagnosticsDocument,
) -> bool:
    try:
        persisted = ChronologicalPartitionDiagnosticsDocument.model_validate_json(
            (directory / PopulationPublicationAsset.CHRONOLOGY).read_text(
                encoding="utf-8"
            )
        )
    except (OSError, ValueError):
        return False
    return persisted == expected


def _matches_static_reference(
    directory: Path,
    expected: PopulationManifest,
) -> bool:
    try:
        persisted = PopulationManifestDocument.model_validate_json(
            (
                directory / PopulationPublicationAsset.MATCHED_STATIC_MANIFEST
            ).read_text(encoding="utf-8")
        )
        membership = (
            directory / PopulationPublicationAsset.MATCHED_STATIC_MEMBERSHIP
        )
        return (
            membership.is_file()
            and persisted == expected.document
            and membership_frame_checksum(pl.read_parquet(membership))
            == persisted.membership_checksum
        )
    except (OSError, ValueError, pl.exceptions.PolarsError):
        return False
