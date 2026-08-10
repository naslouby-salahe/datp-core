from dataclasses import dataclass
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    DatasetId,
    PopulationId,
    SplitProtocolId,
    ValidationReasonText,
)
from datp_core.core.numeric import ClientCount, NonNegativeIntegerValue, Seed
from datp_core.data.populations.contracts import (
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    ModelInputExclusionEvidence,
    PopulationConstructionRequest,
    PopulationConstructionResult,
    PopulationFeasibility,
    PopulationFrameColumn,
    PopulationManifest,
    PopulationManifestDocument,
    SplitConstructionRequest,
    SplitManifestDocument,
    client_identities,
)
from datp_core.data.populations.integrity import validate_split_manifest
from datp_core.data.populations.splits import split_membership
from datp_core.data.registry import construct_population
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.runtime.filesystem import cleanup_staging_on_failure, create_staging_directory, replace_directory

_POPULATION_MANIFEST = "population_manifest.json"
_MEMBERSHIP = "membership.parquet"
_SPLIT_MANIFEST = "split_manifest.json"
_ASSIGNMENTS = "split_assignments.parquet"
_STATIC_POPULATION_MANIFEST = "matched_static_reference_manifest.json"
_STATIC_MEMBERSHIP = "matched_static_reference_membership.parquet"
_STATIC_SPLIT_MANIFEST = "matched_static_reference_split_manifest.json"
_STATIC_ASSIGNMENTS = "matched_static_reference_split_assignments.parquet"
_CHRONOLOGY = "chronology.json"
_EXCLUSIONS = "model_input_exclusions.json"


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
    construction: PopulationConstructionResult
    split_assignments: pl.DataFrame
    split_manifest: SplitManifestDocument


def construct_declared_population(request: ConstructDeclaredPopulationRequest) -> ConstructDeclaredPopulationResult:
    construction = construct_population(
        PopulationConstructionRequest(
            request.population,
            request.canonical_root,
            request.partition_seed,
            request.split_protocol,
            request.controlled_condition,
        )
    )
    split = split_membership(
        SplitConstructionRequest(
            membership=construction.membership,
            population=request.population,
            dataset=request.dataset,
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
            capture_timestamp_column=_capture_timestamp_column_for_split(
                request.split_protocol,
                construction.membership,
            ),
        )
    )
    return ConstructDeclaredPopulationResult(
        construction=construction,
        split_assignments=split.assignments,
        split_manifest=split.manifest,
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
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    chronology: ChronologicalPartitionDiagnosticsDocument | None
    matched_static_reference_manifest: PopulationManifest | None
    matched_static_reference_membership: pl.DataFrame | None
    ciciot_excluded_rows: pl.DataFrame | None = None
    ciciot_client_eligibility: pl.DataFrame | None = None
    model_input_exclusions: ModelInputExclusionEvidence | None = None


def construct_published_population(request: ConstructPublishedPopulationRequest) -> ConstructPublishedPopulationResult:
    require_execution_identity(request.execution_identity, request.population)
    if request.output_directory.exists() and not request.overwrite:
        return _load_population(request.output_directory)
    construction = construct_population(
        PopulationConstructionRequest(
            request.population,
            request.canonical_root,
            request.partition_seed,
            request.split_protocol,
            None,
        )
    )
    temporary = create_staging_directory(request.output_directory)
    with cleanup_staging_on_failure(temporary):
        _write_population(temporary, construction)
        replace_directory(temporary, request.output_directory)
    return _population_result(construction)


@dataclass(slots=True, eq=False, kw_only=True)
class ConstructPublishedSplitRequest:
    population: PopulationId
    execution_identity: ExternalTemporalExecutionIdentity
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    partition_seed: Seed
    output_directory: Path
    overwrite: bool
    matched_static_reference_manifest: PopulationManifest | None = None
    matched_static_reference_membership: pl.DataFrame | None = None


@dataclass(slots=True, eq=False, kw_only=True)
class ConstructPublishedSplitResult:
    assignments: pl.DataFrame
    manifest: SplitManifestDocument
    matched_static_reference_assignments: pl.DataFrame | None
    matched_static_reference_manifest: SplitManifestDocument | None


def construct_published_split(request: ConstructPublishedSplitRequest) -> ConstructPublishedSplitResult:
    if request.output_directory.exists() and not request.overwrite:
        return _load_split(request.output_directory)
    document = request.population_manifest.document
    if document.population is not request.population:
        raise ScientificContractError(ErrorMessage("split request population must match its manifest"))
    split = split_membership(
        SplitConstructionRequest(
            membership=request.membership,
            population=request.population,
            dataset=document.dataset,
            partition_seed=request.partition_seed,
            split_protocol=document.split_protocol,
            capture_timestamp_column=_capture_timestamp_column_for_split(
                document.split_protocol,
                request.membership,
            ),
        )
    )
    validate_split_manifest(request.membership, split.assignments, split.manifest)
    static_assignments: pl.DataFrame | None = None
    static_manifest: SplitManifestDocument | None = None
    if request.matched_static_reference_manifest is not None:
        static_membership = request.matched_static_reference_membership
        if static_membership is None:
            raise ScientificContractError(ErrorMessage("matched reference membership is required"))
        _require_matching_reference_rows(request.membership, static_membership)
        static = split_membership(
            SplitConstructionRequest(
                membership=static_membership,
                population=request.population,
                dataset=document.dataset,
                partition_seed=request.partition_seed,
                split_protocol=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
            )
        )
        static_assignments, static_manifest = static.assignments, static.manifest
    temporary = create_staging_directory(request.output_directory)
    with cleanup_staging_on_failure(temporary):
        split.assignments.write_parquet(temporary / _ASSIGNMENTS)
        _write_json(temporary / _SPLIT_MANIFEST, split.manifest)
        if static_assignments is not None and static_manifest is not None:
            static_assignments.write_parquet(temporary / _STATIC_ASSIGNMENTS)
            _write_json(temporary / _STATIC_SPLIT_MANIFEST, static_manifest)
        replace_directory(temporary, request.output_directory)
    return ConstructPublishedSplitResult(
        assignments=split.assignments,
        manifest=split.manifest,
        matched_static_reference_assignments=static_assignments,
        matched_static_reference_manifest=static_manifest,
    )


def _population_result(construction: PopulationConstructionResult) -> ConstructPublishedPopulationResult:
    matched = construction.matched_reference
    evidence = construction.evidence
    return ConstructPublishedPopulationResult(
        population_manifest=construction.manifest,
        membership=construction.membership,
        chronology=construction.diagnostics
        if isinstance(construction.diagnostics, ChronologicalPartitionDiagnosticsDocument)
        else None,
        matched_static_reference_manifest=matched.manifest if matched is not None else None,
        matched_static_reference_membership=matched.membership if matched is not None else None,
        ciciot_excluded_rows=evidence.excluded_rows if evidence is not None else None,
        ciciot_client_eligibility=evidence.client_eligibility if evidence is not None else None,
        model_input_exclusions=construction.model_input_exclusions,
    )


def _write_population(directory: Path, construction: PopulationConstructionResult) -> None:
    _write_json(directory / _POPULATION_MANIFEST, construction.manifest.document)
    construction.membership.write_parquet(directory / _MEMBERSHIP)
    if isinstance(construction.diagnostics, ChronologicalPartitionDiagnosticsDocument):
        _write_json(directory / _CHRONOLOGY, construction.diagnostics)
    if construction.matched_reference is not None:
        _write_json(directory / _STATIC_POPULATION_MANIFEST, construction.matched_reference.manifest.document)
        construction.matched_reference.membership.write_parquet(directory / _STATIC_MEMBERSHIP)
    if construction.model_input_exclusions is not None:
        _write_json(directory / _EXCLUSIONS, construction.model_input_exclusions)


def _load_population(directory: Path) -> ConstructPublishedPopulationResult:
    document = _read_json(directory / _POPULATION_MANIFEST, PopulationManifestDocument)
    manifest = _manifest(document)
    membership = _read_parquet(directory / _MEMBERSHIP)
    chronology = (
        _read_json(directory / _CHRONOLOGY, ChronologicalPartitionDiagnosticsDocument)
        if (directory / _CHRONOLOGY).is_file()
        else None
    )
    static_manifest = (
        _manifest(_read_json(directory / _STATIC_POPULATION_MANIFEST, PopulationManifestDocument))
        if (directory / _STATIC_POPULATION_MANIFEST).is_file()
        else None
    )
    static_membership = (
        _read_parquet(directory / _STATIC_MEMBERSHIP) if (directory / _STATIC_MEMBERSHIP).is_file() else None
    )
    exclusions = (
        _read_json(directory / _EXCLUSIONS, ModelInputExclusionEvidence)
        if (directory / _EXCLUSIONS).is_file()
        else None
    )
    return ConstructPublishedPopulationResult(
        population_manifest=manifest,
        membership=membership,
        chronology=chronology,
        matched_static_reference_manifest=static_manifest,
        matched_static_reference_membership=static_membership,
        model_input_exclusions=exclusions,
    )


def _load_split(directory: Path) -> ConstructPublishedSplitResult:
    assignments = _read_parquet(directory / _ASSIGNMENTS)
    manifest = _read_json(directory / _SPLIT_MANIFEST, SplitManifestDocument)
    static_assignments = (
        _read_parquet(directory / _STATIC_ASSIGNMENTS) if (directory / _STATIC_ASSIGNMENTS).is_file() else None
    )
    static_manifest = (
        _read_json(directory / _STATIC_SPLIT_MANIFEST, SplitManifestDocument)
        if (directory / _STATIC_SPLIT_MANIFEST).is_file()
        else None
    )
    return ConstructPublishedSplitResult(
        assignments=assignments,
        manifest=manifest,
        matched_static_reference_assignments=static_assignments,
        matched_static_reference_manifest=static_manifest,
    )


def _manifest(document: PopulationManifestDocument) -> PopulationManifest:
    return PopulationManifest(
        document,
        client_identities(document.population, document.candidate_clients, document.identity_kind),
        PopulationFeasibility(
            document.feasibility_status,
            document.feasibility_reason,
            ClientCount(len(document.candidate_clients)),
            NonNegativeIntegerValue(len(document.accepted_clients)),
            ValidationReasonText("prepared population"),
        ),
        (),
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(canonical_json_text(value), encoding="utf-8")


def _read_json[ModelT: BaseModel](path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError(ErrorMessage("prepared data artifact is missing or invalid")) from error


def _read_parquet(path: Path) -> pl.DataFrame:
    try:
        return pl.read_parquet(path)
    except (OSError, pl.exceptions.PolarsError) as error:
        raise ScientificContractError(ErrorMessage("prepared data artifact is missing or invalid")) from error


def _capture_timestamp_column_for_split(
    split_protocol: SplitProtocolId, membership: pl.DataFrame
) -> CaptureTimestampColumn | None:
    if split_protocol is not SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        return None
    column = CaptureTimestampColumn("capture_timestamp")
    if column not in membership.columns:
        raise ScientificContractError(ErrorMessage("temporal split requires capture timestamps"))
    return column


def _require_matching_reference_rows(temporal: pl.DataFrame, static: pl.DataFrame) -> None:
    columns = (PopulationFrameColumn.CLIENT_ID.value, PopulationFrameColumn.STABLE_ROW_ID.value)
    if not temporal.select(columns).sort(columns).equals(static.select(columns).sort(columns)):
        raise ScientificContractError(ErrorMessage("matched static reference must use the same client rows"))
