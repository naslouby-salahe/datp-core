"""Population construction, splitting, and deterministic publication."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.domain.enums import DatasetId, PopulationId, PublicationStatus, SplitProtocolId
from datp_core.domain.values import Checksum, Seed
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.populations.catalogue import (
    PopulationConstructionRequest as CapabilityPopulationConstructionRequest,
)
from datp_core.populations.catalogue import (
    PopulationConstructionResult as CapabilityPopulationConstructionResult,
)
from datp_core.populations.catalogue import construct_population as construct_population_capability
from datp_core.populations.membership import (
    PopulationMembershipRequest,
    PopulationPublicationAsset,
    load_reused_population_membership,
    population_membership_is_reusable,
    prepare_population_membership,
    rebase_population_membership,
    write_population_membership,
)
from datp_core.populations.models import (
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    PopulationManifest,
    SplitConstructionRequest,
    SplitManifestDocument,
)
from datp_core.populations.splits import split_membership
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


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
                writer=write_population_membership,
                validator=population_membership_is_reusable,
                loader=load_reused_population_membership,
                rebaser=rebase_population_membership,
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
