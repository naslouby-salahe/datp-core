"""Stage: federated preprocessing publication under processed coordinates."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.artifacts.serialization import TrustedScaler, canonical_json_text
from datp_core.datasets.canonical_cache import require_canonical_publication_complete
from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS, EdgeAssetRole, EdgeCanonicalColumn
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionOrdering,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    ClientPathToken,
    ClientPublicationCount,
    FeatureName,
    FeatureNameSequence,
    NonNegativeIntegerValue,
    Seed,
    checksum_text,
)
from datp_core.experiments.models import ExternalTemporalExecutionIdentity, require_execution_identity
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoff,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
    join_handoff_with_canonical_features,
    resolve_population,
)
from datp_core.populations.integrity import (
    membership_frame_checksum,
    validate_no_future_history_leakage,
    validate_population_manifest,
    validate_split_manifest,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    PARTITION_ROLE_COLUMN,
    SOURCE_PATH_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    PopulationFeasibility,
    PopulationManifest,
    PopulationManifestDocument,
    SplitManifestDocument,
    client_identities,
)
from datp_core.preprocessing.federated import fit_estimators_for_federated_clients, publish_client_preprocessing
from datp_core.preprocessing.models import (
    SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD,
    SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
    ClientPreprocessingResult,
    ClientPublishRequest,
    FederatedFittedEstimators,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
)
from datp_core.preprocessing.validation import extract_partitions

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
CANONICAL_DATA_DIRECTORY = "data"
PARQUET_PATTERN = "*.parquet"
PERSISTED_MANIFEST_EVIDENCE = "persisted population manifest"

_FEDERATED_METHODS = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    }
)
_EDGE_PUBLISHED_POPULATIONS = frozenset(
    {
        PopulationId.EDGE_TEMPORAL_GROUPS,
        PopulationId.EDGE_SENSOR_GROUPS,
    }
)


@dataclass(frozen=True, slots=True)
class PreprocessFederatedRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True)
class PreprocessFederatedResult:
    stage: ClassVar[StageOperationId] = StageOperationId.PREPROCESS_FEDERATED
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    client_publications: tuple[ClientPreprocessingResult, ...]
    published_count: ClientPublicationCount
    reused_count: ClientPublicationCount
    execution_identity: ExternalTemporalExecutionIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.published_count, ClientPublicationCount) or not isinstance(
            self.reused_count,
            ClientPublicationCount,
        ):
            raise TypeError("preprocessing results require typed publication counts")
        if self.published_count.value + self.reused_count.value != len(self.client_publications):
            raise ValueError("published and reused counts must cover every client publication")


@dataclass(frozen=True, slots=True)
class PreprocessFederatedArtifactsRequest:
    execution_identity: ExternalTemporalExecutionIdentity
    population_directory: Path
    split_directory: Path
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    capture_timestamp_column: str | None = None


@dataclass(slots=True, eq=False)
class _PublishedPopulationSplit:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    split_manifest: SplitManifestDocument
    assignments: pl.DataFrame


@dataclass(frozen=True, slots=True)
class _CanonicalSourceFile:
    source_path: str
    parquet_path: Path


def preprocess_federated_stage(request: PreprocessFederatedRequest) -> PreprocessFederatedResult:
    _validate_federated_request(request)
    binding = resolve_population(request.population)
    dataset = binding.declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    require_canonical_publication_complete(canonical_root, dataset, ContractSubject.PREPROCESSING)
    construction = construct_population(
        PopulationConstructionRequest(
            population_id=request.population,
            canonical_root=canonical_root,
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
            dirichlet_condition=request.dirichlet_condition,
        )
    )
    handoff = build_preprocessing_handoff(
        PreprocessingHandoffRequest(
            construction=construction,
            deployment_fallback_client_ids=frozenset(),
            capture_timestamp_column=_capture_timestamp_column(request),
        )
    )
    schema = dataset_binding(dataset).schema
    feature_names = _model_feature_names(dataset, schema.feature_columns)
    protocol = _federated_protocol(request.preprocessing_identity, feature_names)
    joined = join_handoff_with_canonical_features(canonical_root, handoff, feature_names)
    document = construction.manifest.document
    context = PreprocessingPublishContext(
        dataset=document.dataset,
        population=document.population,
        partition_seed=document.partition_seed,
        split_protocol_identity=document.split_protocol,
        protocol=protocol,
        canonical_schema_checksum=schema.checksum,
        data_root=request.data_root,
    )
    partitions = _client_partitions(joined, feature_names, document.split_protocol)
    publications, published_count, reused_count = _publish_client_partitions(
        context,
        partitions,
        fit_estimators_for_federated_clients(protocol, partitions),
    )
    return PreprocessFederatedResult(
        population=document.population,
        dataset=document.dataset,
        partition_seed=document.partition_seed,
        split_protocol=document.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=publications,
        published_count=ClientPublicationCount(published_count),
        reused_count=ClientPublicationCount(reused_count),
    )


def preprocess_federated_artifacts_stage(
    request: PreprocessFederatedArtifactsRequest,
) -> PreprocessFederatedResult:
    identity = require_execution_identity(request.execution_identity, request.execution_identity.population)
    if identity is None:
        raise AssertionError("published artifact preprocessing requires an execution identity")
    _validate_artifact_request(request)
    published = _load_published_population_split(request, identity)
    document = published.population_manifest.document
    dataset = document.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    require_canonical_publication_complete(canonical_root, dataset, ContractSubject.PREPROCESSING)
    schema = dataset_binding(dataset).schema
    feature_names = _model_feature_names(dataset, schema.feature_columns)
    protocol = _federated_protocol(request.preprocessing_identity, feature_names)
    context = PreprocessingPublishContext(
        dataset=dataset,
        population=document.population,
        partition_seed=document.partition_seed,
        split_protocol_identity=published.split_manifest.split_protocol,
        protocol=protocol,
        canonical_schema_checksum=schema.checksum,
        data_root=request.data_root,
        execution_identity=identity,
    )
    if dataset is DatasetId.CICIOT2023 and protocol.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
        return _preprocess_ciciot_client_local(
            context=context,
            assignments=published.assignments,
            canonical_root=canonical_root,
            feature_names=feature_names,
            identity=identity,
        )
    handoff = PreprocessingHandoff(
        population_manifest=published.population_manifest,
        membership=published.membership,
        assignments=published.assignments,
        client_partition_counts=(),
    )
    joined = _join_published_handoff(canonical_root, handoff, feature_names, identity)
    partitions = _client_partitions(joined, feature_names, published.split_manifest.split_protocol)
    publications, published_count, reused_count = _publish_client_partitions(
        context,
        partitions,
        fit_estimators_for_federated_clients(protocol, partitions),
    )
    return PreprocessFederatedResult(
        population=document.population,
        dataset=dataset,
        partition_seed=document.partition_seed,
        split_protocol=published.split_manifest.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=publications,
        published_count=ClientPublicationCount(published_count),
        reused_count=ClientPublicationCount(reused_count),
        execution_identity=identity,
    )


def _client_partitions(
    joined: pl.DataFrame,
    feature_names: FeatureNameSequence,
    split_protocol: SplitProtocolId,
) -> ClientCollection[ClientPathToken, PreprocessingPartitions]:
    client_ids = tuple(
        ClientPathToken(str(value))
        for value in sorted(joined.get_column(CLIENT_ID_COLUMN).unique().to_list())
    )
    return ClientCollection(
        tuple(
            ClientOwned(
                client_id,
                extract_partitions(
                    joined.filter(pl.col(CLIENT_ID_COLUMN) == client_id.value),
                    feature_names,
                    split_protocol=split_protocol,
                    branch=ProcessedDataBranch.FEDERATED,
                    ordering=PartitionOrdering.PRESERVE_SOURCE_ORDER,
                ),
            )
            for client_id in client_ids
        )
    )


def _preprocess_ciciot_client_local(
    *,
    context: PreprocessingPublishContext,
    assignments: pl.DataFrame,
    canonical_root: Path,
    feature_names: FeatureNameSequence,
    identity: ExternalTemporalExecutionIdentity,
) -> PreprocessFederatedResult:
    client_ids = tuple(
        ClientPathToken(str(value))
        for value in sorted(assignments.get_column(CLIENT_ID_COLUMN).unique().to_list())
    )
    source_files = _ciciot_source_files(canonical_root)
    publications: list[ClientPreprocessingResult] = []
    published_count = 0
    reused_count = 0
    for client_id in client_ids:
        client_assignments = assignments.filter(pl.col(CLIENT_ID_COLUMN) == client_id.value)
        source_path = _single_client_source_path(client_assignments)
        features = pl.read_parquet(
            _canonical_source_file(source_files, source_path).parquet_path,
            columns=(STABLE_ROW_ID_COLUMN, *feature_names),
        )
        joined = client_assignments.join(features, on=STABLE_ROW_ID_COLUMN, how="inner").sort(
            (PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN)
        )
        if joined.height != client_assignments.height:
            raise ScientificContractError(
                "canonical feature join lost file-client assignment rows",
                subject=identity.population,
            )
        partitions = extract_partitions(
            joined,
            feature_names,
            split_protocol=context.split_protocol_identity,
            branch=ProcessedDataBranch.FEDERATED,
            ordering=PartitionOrdering.PRESERVE_SOURCE_ORDER,
        )
        collection = ClientCollection((ClientOwned(client_id, partitions),))
        estimators = fit_estimators_for_federated_clients(context.protocol, collection)
        estimator = _estimator_for_client(estimators, client_id)
        publication = publish_client_preprocessing(ClientPublishRequest(context, client_id, estimator, partitions))
        if publication.publication_status is PublicationStatus.REUSED:
            reused_count += 1
        else:
            published_count += 1
        publications.append(publication)
    return PreprocessFederatedResult(
        population=identity.population,
        dataset=DatasetId.CICIOT2023,
        partition_seed=context.partition_seed,
        split_protocol=context.split_protocol_identity,
        preprocessing_identity=context.protocol.identity,
        client_publications=tuple(publications),
        published_count=ClientPublicationCount(published_count),
        reused_count=ClientPublicationCount(reused_count),
        execution_identity=identity,
    )


def _publish_client_partitions(
    context: PreprocessingPublishContext,
    client_partitions: ClientCollection[ClientPathToken, PreprocessingPartitions],
    fitted_estimators: FederatedFittedEstimators,
) -> tuple[tuple[ClientPreprocessingResult, ...], int, int]:
    publications = tuple(
        publish_client_preprocessing(
            ClientPublishRequest(
                context=context,
                client_identity=item.client,
                fitted_estimator=_estimator_for_client(fitted_estimators, item.client),
                partitions=item.value,
            )
        )
        for item in client_partitions.items
    )
    reused = sum(item.publication_status is PublicationStatus.REUSED for item in publications)
    return publications, len(publications) - reused, reused


def _estimator_for_client(
    fitted_estimators: FederatedFittedEstimators,
    client: ClientPathToken,
) -> TrustedScaler:
    if isinstance(fitted_estimators, ClientCollection):
        return fitted_estimators.require(client)
    return fitted_estimators


def _ciciot_source_files(canonical_root: Path) -> tuple[_CanonicalSourceFile, ...]:
    sources = tuple(
        _CanonicalSourceFile(
            source_path=str(pl.read_parquet(path, columns=(SOURCE_PATH_COLUMN,), n_rows=1).item(0, 0)),
            parquet_path=path,
        )
        for path in sorted((canonical_root / CANONICAL_DATA_DIRECTORY).glob(PARQUET_PATTERN))
    )
    if not sources:
        raise ScientificContractError("CIC canonical files are unavailable", subject=DatasetId.CICIOT2023)
    source_paths = tuple(source.source_path for source in sources)
    if len(frozenset(source_paths)) != len(source_paths):
        raise ScientificContractError(
            "CIC canonical source paths must be unique",
            subject=DatasetId.CICIOT2023,
        )
    return sources


def _canonical_source_file(
    source_files: tuple[_CanonicalSourceFile, ...],
    source_path: str,
) -> _CanonicalSourceFile:
    matches = tuple(source for source in source_files if source.source_path == source_path)
    if len(matches) != 1:
        raise ScientificContractError(
            "file-defined client source must resolve exactly once",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]


def _single_client_source_path(assignments: pl.DataFrame) -> str:
    sources = tuple(
        sorted(str(value) for value in assignments.get_column(SOURCE_PATH_COLUMN).unique().to_list())
    )
    if len(sources) != 1:
        raise ScientificContractError(
            "file-defined client assignments must originate from exactly one source file",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return sources[0]


def _join_published_handoff(
    canonical_root: Path,
    handoff: PreprocessingHandoff,
    feature_names: FeatureNameSequence,
    identity: ExternalTemporalExecutionIdentity,
) -> pl.DataFrame:
    if identity.population not in _EDGE_PUBLISHED_POPULATIONS:
        return join_handoff_with_canonical_features(canonical_root, handoff, feature_names)
    asset_role = (
        EdgeAssetRole.TEMPORAL_BENIGN
        if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS
        else EdgeAssetRole.STATIC_BENIGN
    )
    assignments = handoff.assignments
    feature_scan = pl.scan_parquet(
        str(canonical_root / CANONICAL_DATA_DIRECTORY / asset_role.value / PARQUET_PATTERN)
    ).select(
        (STABLE_ROW_ID_COLUMN, *(pl.col(name).cast(pl.Float64, strict=True).alias(name) for name in feature_names))
    )
    joined = (
        assignments.lazy()
        .join(feature_scan, on=STABLE_ROW_ID_COLUMN, how="inner")
        .collect()
        .sort((CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN))
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "canonical feature join lost assignment rows",
            subject=handoff.population_manifest.document.dataset,
        )
    return joined


def _model_feature_names(dataset: DatasetId, feature_names: tuple[str, ...]) -> FeatureNameSequence:
    if dataset is not DatasetId.EDGE_IIOTSET:
        return FeatureNameSequence(tuple(FeatureName(name) for name in feature_names))
    if frozenset(EDGE_NUMERIC_FEATURE_COLUMNS) - frozenset(feature_names):
        raise ScientificContractError("Edge numeric feature declaration must be a canonical feature subset")
    return FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


def _validate_federated_request(request: PreprocessFederatedRequest) -> None:
    if request.preprocessing_identity not in _FEDERATED_METHODS:
        raise ScientificContractError(
            "federated preprocess stage requires a federated preprocessing identity",
            subject=request.preprocessing_identity,
        )
    if (
        request.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        and request.population is not PopulationId.EDGE_TEMPORAL_GROUPS
    ):
        raise ScientificContractError(
            "chronological preprocessing is defined only for Edge temporal groups",
            subject=request.population,
        )


def _validate_artifact_request(request: PreprocessFederatedArtifactsRequest) -> None:
    if request.preprocessing_identity not in _FEDERATED_METHODS:
        raise ScientificContractError(
            "federated preprocess stage requires a federated preprocessing identity",
            subject=request.preprocessing_identity,
        )
    if request.execution_identity.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        _capture_timestamp_column_for(
            request.execution_identity.population,
            SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            request.capture_timestamp_column,
        )
    elif request.capture_timestamp_column is not None:
        raise ScientificContractError(
            "non-temporal preprocessing cannot declare a capture timestamp column",
            subject=request.execution_identity.population,
        )


def _load_published_population_split(
    request: PreprocessFederatedArtifactsRequest,
    identity: ExternalTemporalExecutionIdentity,
) -> _PublishedPopulationSplit:
    use_static = identity.temporal_state is TemporalState.STATIC_REFERENCE
    population_manifest_name = (
        MATCHED_STATIC_POPULATION_MANIFEST_ASSET if use_static else POPULATION_MANIFEST_ASSET
    )
    membership_name = (
        MATCHED_STATIC_POPULATION_MEMBERSHIP_ASSET if use_static else POPULATION_MEMBERSHIP_ASSET
    )
    split_manifest_name = MATCHED_STATIC_SPLIT_MANIFEST_ASSET if use_static else SPLIT_MANIFEST_ASSET
    assignments_name = MATCHED_STATIC_SPLIT_ASSIGNMENTS_ASSET if use_static else SPLIT_ASSIGNMENTS_ASSET
    population_document = _read_population_document(request.population_directory / population_manifest_name)
    split_document = _read_split_document(request.split_directory / split_manifest_name)
    membership = _read_parquet(request.population_directory / membership_name, identity.population)
    assignments = _read_parquet(request.split_directory / assignments_name, identity.population)
    _validate_population_publication(request.population_directory, identity)
    _validate_split_publication(request.split_directory, identity)
    manifest = _population_manifest_from_document(population_document)
    _validate_published_pair(manifest, membership, split_document, assignments, identity, use_static)
    return _PublishedPopulationSplit(manifest, membership, split_document, assignments)


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
        raise ScientificContractError("published parquet artifact is missing or invalid", subject=population) from error


def _validate_population_publication(directory: Path, identity: ExternalTemporalExecutionIdentity) -> None:
    complete = _read_complete_digest(directory, identity.population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_population_document(directory / POPULATION_MANIFEST_ASSET)
    sections = [canonical_json_text(identity), canonical_json_text(primary)]
    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        sections.extend(
            (
                canonical_json_text(_read_chronology_document(directory / CHRONOLOGY_ASSET)),
                canonical_json_text(
                    _read_population_document(directory / MATCHED_STATIC_POPULATION_MANIFEST_ASSET)
                ),
            )
        )
    if complete != checksum_text("\n".join(sections)):
        raise ScientificContractError(
            "published population COMPLETE digest does not match its manifests",
            subject=identity.population,
        )


def _validate_split_publication(directory: Path, identity: ExternalTemporalExecutionIdentity) -> None:
    complete = _read_complete_digest(directory, identity.population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_split_document(directory / SPLIT_MANIFEST_ASSET)
    sections = [canonical_json_text(identity), canonical_json_text(primary)]
    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        sections.append(
            canonical_json_text(_read_split_document(directory / MATCHED_STATIC_SPLIT_MANIFEST_ASSET))
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
            (directory / EXECUTION_IDENTITY_ASSET).read_text(encoding="utf-8")
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


def _read_complete_digest(directory: Path, population: PopulationId) -> Checksum:
    try:
        return Checksum((directory / COMPLETE_ASSET).read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "published artifact COMPLETE marker is missing or invalid",
            subject=population,
        ) from error


def _read_chronology_document(path: Path) -> ChronologicalPartitionDiagnosticsDocument:
    try:
        return ChronologicalPartitionDiagnosticsDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "temporal population lacks valid chronology evidence",
            subject=PopulationId.EDGE_TEMPORAL_GROUPS,
        ) from error


def _population_manifest_from_document(document: PopulationManifestDocument) -> PopulationManifest:
    return PopulationManifest(
        document=document,
        clients=client_identities(document.population, document.candidate_clients, document.identity_kind),
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
        raise ScientificContractError("published membership checksum mismatch", subject=identity.population)
    if split_manifest.population_manifest_checksum != document.membership_checksum:
        raise ScientificContractError("split manifest is not bound to its population", subject=identity.population)
    if split_manifest.split_protocol is not _expected_split_protocol(identity, use_static_reference):
        raise ScientificContractError("published split protocol is incompatible", subject=identity.population)
    validate_population_manifest(population_manifest, membership)
    validate_split_manifest(membership, assignments, split_manifest)
    if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS and not use_static_reference:
        validate_no_future_history_leakage(assignments, EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)


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
    return SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS


def _capture_timestamp_column(request: PreprocessFederatedRequest) -> str | None:
    return _capture_timestamp_column_for(
        request.population,
        request.split_protocol,
        request.capture_timestamp_column,
    )


def _capture_timestamp_column_for(
    population: PopulationId,
    split_protocol: SplitProtocolId,
    capture_timestamp_column: str | None,
) -> str | None:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        if capture_timestamp_column not in {None, EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value}:
            raise ScientificContractError(
                "temporal preprocessing must use the audited Edge capture timestamp column",
                subject=population,
            )
        return EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value
    return capture_timestamp_column


def _federated_protocol(
    identity: PreprocessingProtocolId,
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    match identity:
        case PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD:
            method = SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD
        case PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX:
            method = SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD
        case _:
            raise ScientificContractError("unsupported federated preprocessing identity", subject=identity)
    return build_preprocessing_protocol(method, feature_names)
