"""Population split construction and deterministic publication preparation."""

from dataclasses import dataclass

import polars as pl

from datp_core.datasets.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_json_text
from datp_core.domain.values import Checksum, Seed, checksum_text
from datp_core.populations.edge_temporal_groups import split_temporal_membership
from datp_core.populations.integrity import validate_no_future_history_leakage, validate_split_manifest
from datp_core.populations.models import (
    PopulationManifest,
    SplitConstructionRequest,
    SplitManifestDocument,
)
from datp_core.populations.splits import split_membership
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity, require_execution_identity


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
    """Construct an external or temporal split and matched static reference."""
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
                population_manifest_checksum=request.matched_static_reference_manifest.document.membership_checksum,
            )
        )
        _require_matching_reference_rows(request.membership, request.matched_static_reference_membership)
        validate_split_manifest(
            request.matched_static_reference_membership,
            static_assignments,
            static_manifest,
        )
        return PopulationSplitArtifacts(assignments, manifest, static_assignments, static_manifest)
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
