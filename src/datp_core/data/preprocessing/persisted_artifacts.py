from dataclasses import dataclass
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    PopulationId,
    TemporalState,
    ValidationReasonText,
)
from datp_core.core.numeric import ClientCount, NonNegativeIntegerValue
from datp_core.data.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.data.populations.contracts import (
    PopulationFeasibility,
    PopulationManifest,
    PopulationManifestDocument,
    SplitManifestDocument,
    client_identities,
)
from datp_core.data.populations.integrity import (
    validate_no_future_history_leakage,
    validate_population_manifest,
    validate_split_manifest,
)
from datp_core.data.preprocessing.models import PublishedFederatedPreprocessingRequest
from datp_core.data.registry import population_capabilities, population_declaration
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity

POPULATION_MANIFEST_ASSET = "population_manifest.json"
POPULATION_MEMBERSHIP_ASSET = "membership.parquet"
SPLIT_MANIFEST_ASSET = "split_manifest.json"
SPLIT_ASSIGNMENTS_ASSET = "split_assignments.parquet"
MATCHED_STATIC_POPULATION_MANIFEST_ASSET = "matched_static_reference_manifest.json"
MATCHED_STATIC_POPULATION_MEMBERSHIP_ASSET = "matched_static_reference_membership.parquet"
MATCHED_STATIC_SPLIT_MANIFEST_ASSET = "matched_static_reference_split_manifest.json"
MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET = "matched_static_reference_split_assignments.parquet"
PERSISTED_MANIFEST_EVIDENCE = ValidationReasonText("persisted population manifest")


@dataclass(slots=True, eq=False)
class PublishedPopulationSplit:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    split_manifest: SplitManifestDocument
    assignments: pl.DataFrame


def load_published_population_split(
    request: PublishedFederatedPreprocessingRequest,
    identity: ExternalTemporalExecutionIdentity,
) -> PublishedPopulationSplit:
    if identity.temporal_state is TemporalState.STATIC_REFERENCE:
        pop_name, member_name, split_name, assignment_name = (
            MATCHED_STATIC_POPULATION_MANIFEST_ASSET,
            MATCHED_STATIC_POPULATION_MEMBERSHIP_ASSET,
            MATCHED_STATIC_SPLIT_MANIFEST_ASSET,
            MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET,
        )
    else:
        pop_name, member_name, split_name, assignment_name = (
            POPULATION_MANIFEST_ASSET,
            POPULATION_MEMBERSHIP_ASSET,
            SPLIT_MANIFEST_ASSET,
            SPLIT_ASSIGNMENTS_ASSET,
        )
    document = _read_model(request.population_directory / pop_name, PopulationManifestDocument)
    split = _read_model(request.split_directory / split_name, SplitManifestDocument)
    membership = _read_parquet(request.population_directory / member_name, identity.population)
    assignments = _read_parquet(request.split_directory / assignment_name, identity.population)
    manifest = PopulationManifest(
        document,
        client_identities(document.population, document.candidate_clients, document.identity_kind),
        PopulationFeasibility(
            document.feasibility_status,
            document.feasibility_reason,
            ClientCount(len(document.candidate_clients)),
            NonNegativeIntegerValue(len(document.accepted_clients)),
            PERSISTED_MANIFEST_EVIDENCE,
        ),
        (),
    )
    if document.population is not identity.population or split.population is not identity.population:
        raise ScientificContractError(ErrorMessage("prepared population does not match execution identity"))
    if document.dataset is not split.dataset or document.partition_seed != split.partition_seed:
        raise ScientificContractError(ErrorMessage("prepared population and split coordinates disagree"))
    validate_population_manifest(
        manifest, membership, population_declaration(identity.population), population_capabilities(identity.population)
    )
    validate_split_manifest(membership, assignments, split)
    if (
        identity.population is PopulationId.EDGE_TEMPORAL_CLIENTS
        and identity.temporal_state is not TemporalState.STATIC_REFERENCE
    ):
        validate_no_future_history_leakage(
            assignments, CaptureTimestampColumn(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)
        )
    return PublishedPopulationSplit(manifest, membership, split, assignments)


def _read_model[ModelT: BaseModel](path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError(ErrorMessage("prepared data artifact is missing or invalid")) from error


def _read_parquet(path: Path, population: PopulationId) -> pl.DataFrame:
    try:
        return pl.read_parquet(path)
    except (OSError, pl.exceptions.PolarsError) as error:
        raise ScientificContractError(
            ErrorMessage("prepared data artifact is missing or invalid"), subject=population
        ) from error
