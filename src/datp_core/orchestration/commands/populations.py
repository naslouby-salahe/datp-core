"""Typed population construction and split commands."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.domain.enums import PopulationId, PublicationStatus, SplitProtocolId, StageOperationId
from datp_core.domain.values import Checksum, Seed
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.populations.models import (
    ChronologicalPartitionDiagnosticsDocument,
    PopulationManifest,
    SplitManifestDocument,
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


@dataclass(slots=True, eq=False)
class SplitResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SPLIT
    publication_status: PublicationStatus
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None
    complete_digest: Checksum
