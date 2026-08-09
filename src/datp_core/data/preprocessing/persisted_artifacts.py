from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.provenance import Checksum, checksum_text
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import CaptureTimestampColumn, PopulationId, SplitProtocolId, TemporalState
from datp_core.core.numeric import ClientCount, NonNegativeIntegerValue
from datp_core.data.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.data.populations.contracts import (
    ChronologicalPartitionDiagnosticsDocument,
    PopulationFeasibility,
    PopulationManifest,
    PopulationManifestDocument,
    SplitManifestDocument,
    client_identities,
)
from datp_core.data.populations.declarations import split_protocol_for_population
from datp_core.data.populations.integrity import (
    membership_frame_checksum,
    validate_no_future_history_leakage,
    validate_population_manifest,
    validate_split_manifest,
)
from datp_core.data.preprocessing.models import PublishedFederatedPreprocessingRequest
from datp_core.data.registry import population_capabilities, population_declaration
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity

EXECUTION_IDENTITY_ASSET = "execution_identity.json"
POPULATION_MANIFEST_ASSET = "population_manifest.json"
POPULATION_MEMBERSHIP_ASSET = "membership.parquet"
SPLIT_MANIFEST_ASSET = "split_manifest.json"
SPLIT_ASSIGNMENTS_ASSET = "split_assignments.parquet"
MATCHED_STATIC_POPULATION_MANIFEST_ASSET = "matched_static_reference_manifest.json"
MATCHED_STATIC_POPULATION_MEMBERSHIP_ASSET = "matched_static_reference_membership.parquet"
MATCHED_STATIC_SPLIT_MANIFEST_ASSET = "matched_static_reference_split_manifest.json"
MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET = "matched_static_reference_assignments.parquet"
CHRONOLOGY_ASSET = "chronology.json"
COMPLETE_ASSET = "COMPLETE"
PERSISTED_MANIFEST_EVIDENCE = "persisted population manifest"


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
    use_static = identity.temporal_state is TemporalState.STATIC_REFERENCE
    pop_dir = request.population_directory
    split_dir = request.split_directory

    if use_static:
        pop_name, mem_name, split_name, assign_name = (
            MATCHED_STATIC_POPULATION_MANIFEST_ASSET,
            MATCHED_STATIC_POPULATION_MEMBERSHIP_ASSET,
            MATCHED_STATIC_SPLIT_MANIFEST_ASSET,
            MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET,
        )
    else:
        pop_name, mem_name, split_name, assign_name = (
            POPULATION_MANIFEST_ASSET,
            POPULATION_MEMBERSHIP_ASSET,
            SPLIT_MANIFEST_ASSET,
            SPLIT_ASSIGNMENTS_ASSET,
        )

    population_document = _read_population_document(pop_dir.joinpath(pop_name))
    split_document = _read_split_document(split_dir.joinpath(split_name))
    membership = _read_parquet(pop_dir.joinpath(mem_name), identity.population)
    assignments = _read_parquet(split_dir.joinpath(assign_name), identity.population)

    _validate_population_publication(pop_dir, identity)
    _validate_split_publication(split_dir, identity)

    manifest = _population_manifest_from_document(population_document)

    _validate_published_pair(
        manifest,
        membership,
        split_document,
        assignments,
        identity,
        use_static,
    )

    return PublishedPopulationSplit(
        manifest,
        membership,
        split_document,
        assignments,
    )


def _read_population_document(path: Path) -> PopulationManifestDocument:
    try:
        return PopulationManifestDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError("published population manifest is missing or invalid") from error


def _read_split_document(path: Path) -> SplitManifestDocument:
    try:
        return SplitManifestDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError("published split manifest is missing or invalid") from error


def _read_parquet(path: Path, population: PopulationId) -> pl.DataFrame:
    try:
        return pl.read_parquet(path)
    except (OSError, pl.exceptions.PolarsError) as error:
        raise ScientificContractError(
            "published parquet artifact is missing or invalid",
            subject=population,
        ) from error


def _validate_population_publication(
    directory: Path,
    identity: ExternalTemporalExecutionIdentity,
) -> None:
    complete = _read_complete_digest(directory, identity.population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_population_document(directory.joinpath(POPULATION_MANIFEST_ASSET))

    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        sections = (
            canonical_json_text(identity),
            canonical_json_text(primary),
            canonical_json_text(_read_chronology_document(directory.joinpath(CHRONOLOGY_ASSET))),
            canonical_json_text(
                _read_population_document(directory.joinpath(MATCHED_STATIC_POPULATION_MANIFEST_ASSET))
            ),
        )
    else:
        sections = (
            canonical_json_text(identity),
            canonical_json_text(primary),
        )

    if complete != checksum_text("\n".join(sections)):
        raise ScientificContractError(
            "published population COMPLETE digest does not match its manifests",
            subject=identity.population,
        )


def _validate_split_publication(
    directory: Path,
    identity: ExternalTemporalExecutionIdentity,
) -> None:
    complete = _read_complete_digest(directory, identity.population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_split_document(directory.joinpath(SPLIT_MANIFEST_ASSET))

    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        sections = (
            canonical_json_text(identity),
            canonical_json_text(primary),
            canonical_json_text(_read_split_document(directory.joinpath(MATCHED_STATIC_SPLIT_MANIFEST_ASSET))),
        )
    else:
        sections = (
            canonical_json_text(identity),
            canonical_json_text(primary),
        )

    if complete != checksum_text("\n".join(sections)):
        raise ScientificContractError(
            "published split COMPLETE digest does not match its manifests",
            subject=identity.population,
        )


def _validate_persisted_execution_identity(
    directory: Path,
    identity: ExternalTemporalExecutionIdentity,
) -> None:
    try:
        persisted = ExternalTemporalExecutionIdentity.model_validate_json(
            directory.joinpath(EXECUTION_IDENTITY_ASSET).read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "published artifact lacks a valid execution identity",
            subject=identity.population,
        ) from error

    if persisted != identity:
        raise ScientificContractError(
            "published artifact execution identity does not match the request",
            subject=identity.population,
        )


def _read_complete_digest(
    directory: Path,
    population: PopulationId,
) -> Checksum:
    try:
        return Checksum(directory.joinpath(COMPLETE_ASSET).read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "published artifact COMPLETE marker is missing or invalid",
            subject=population,
        ) from error


def _read_chronology_document(
    path: Path,
) -> ChronologicalPartitionDiagnosticsDocument:
    try:
        return ChronologicalPartitionDiagnosticsDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "temporal population lacks valid chronology evidence",
            subject=PopulationId.EDGE_TEMPORAL_GROUPS,
        ) from error


def _population_manifest_from_document(
    document: PopulationManifestDocument,
) -> PopulationManifest:
    return PopulationManifest(
        document=document,
        clients=client_identities(
            document.population,
            document.candidate_clients,
            document.identity_kind,
        ),
        feasibility=PopulationFeasibility(
            status=document.feasibility_status,
            reason=document.feasibility_reason,
            expected_client_count=ClientCount(len(document.candidate_clients)),
            observed_client_count=NonNegativeIntegerValue(len(document.accepted_clients)),
            evidence=PERSISTED_MANIFEST_EVIDENCE,
        ),
        family_by_client=(),
    )


def _validate_published_pair(
    population_manifest: PopulationManifest,
    membership: pl.DataFrame,
    split_manifest: SplitManifestDocument,
    assignments: pl.DataFrame,
    identity: ExternalTemporalExecutionIdentity,
    use_static_reference: bool,
) -> None:
    document = population_manifest.document

    if document.population is not identity.population or split_manifest.population is not identity.population:
        raise ScientificContractError(
            "published coordinates do not match execution identity",
            subject=identity.population,
        )
    if document.dataset is not split_manifest.dataset or document.partition_seed != split_manifest.partition_seed:
        raise ScientificContractError(
            "published population and split coordinates disagree",
            subject=identity.population,
        )
    if membership_frame_checksum(membership) != document.membership_checksum:
        raise ScientificContractError(
            "published membership checksum mismatch",
            subject=identity.population,
        )
    if split_manifest.population_manifest_checksum != document.membership_checksum:
        raise ScientificContractError(
            "split manifest is not bound to its population",
            subject=identity.population,
        )
    if split_manifest.split_protocol is not _expected_split_protocol(identity, use_static_reference):
        raise ScientificContractError(
            "published split protocol is incompatible",
            subject=identity.population,
        )

    validate_population_manifest(
        population_manifest,
        membership,
        population_declaration(identity.population),
        population_capabilities(identity.population),
    )
    validate_split_manifest(membership, assignments, split_manifest)

    if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS and not use_static_reference:
        validate_no_future_history_leakage(
            assignments,
            CaptureTimestampColumn(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value),
        )


def _expected_split_protocol(
    identity: ExternalTemporalExecutionIdentity,
    use_static_reference: bool,
) -> SplitProtocolId:
    if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        return (
            SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
            if use_static_reference
            else SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        )
    return split_protocol_for_population(identity.population)
