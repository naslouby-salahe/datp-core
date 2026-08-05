"""Population membership construction and deterministic publication preparation."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, Seed, checksum_text
from datp_core.populations.ciciot_file_clients import (
    build_ciciot_file_clients,
    ciciot_client_eligibility_evidence,
    ciciot_excluded_row_evidence,
)
from datp_core.populations.edge_sensor_groups import build_edge_sensor_groups
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.models import (
    ChronologicalPartitionDiagnosticsDocument,
    PopulationManifest,
)
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity, require_execution_identity


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
        digest=checksum_text(_manifest_payload(artifacts, request.execution_identity)),
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
            return PopulationMembershipArtifacts(manifest, membership, None, None, None)
        case PopulationId.CICIOT_FILE_CLIENTS:
            manifest, membership = build_ciciot_file_clients(
                request.canonical_root,
                partition_seed=request.partition_seed,
                split_protocol=request.split_protocol,
            )
            excluded_rows = ciciot_excluded_row_evidence(request.canonical_root)
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
            manifest, membership, chronology, static_manifest, static_membership = build_edge_temporal_groups(
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
        sections.append(canonical_json_text(artifacts.matched_static_reference_manifest.document))
    return "\n".join(sections)
