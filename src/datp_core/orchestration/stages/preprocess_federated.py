"""Stage: federated preprocessing publication under processed coordinates."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS, EdgeAssetRole, EdgeCanonicalColumn
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionRole,
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
from datp_core.domain.values import Checksum, ClientCount, ClientPathToken, FeatureNameSequence, RowCount, Seed, checksum_text
from datp_core.experiments.models import (
    ExecutionIdentityDocument,
    ExternalTemporalExecutionIdentity,
    require_execution_identity,
)
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
    STABLE_ROW_ID_COLUMN,
    ChronologicalPartitionDiagnosticsDocument,
    ControlledPartitionCondition,
    PopulationFeasibility,
    PopulationManifest,
    PopulationManifestDocument,
    SplitManifestDocument,
    client_identities,
)
from datp_core.preprocessing.federated import (
    ClientPartitionBundle,
    ClientPublishRequest,
    fit_estimators_for_federated_clients,
    publish_client_preprocessing,
)
from datp_core.preprocessing.models import (
    ClientPreprocessPublication,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
    scientific_federated_pooled_min_max_method,
    scientific_preprocessing_method,
)
from datp_core.preprocessing.validation import extract_partitions, require_canonical_publication_complete

_FEDERATED_METHODS = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
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
    stage: StageOperationId
    population: PopulationId
    dataset: DatasetId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    client_publications: tuple[ClientPreprocessPublication, ...]
    published_count: int
    reused_count: int
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(frozen=True, slots=True)
class PreprocessFederatedArtifactsRequest:
    """Preprocess an external or temporal execution from published population and split artifacts."""

    execution_identity: ExternalTemporalExecutionIdentity
    population_directory: Path
    split_directory: Path
    preprocessing_identity: PreprocessingProtocolId
    data_root: Path
    capture_timestamp_column: str | None = None


@dataclass(frozen=True, slots=True)
class _PublishedPopulationSplit:
    population_manifest: PopulationManifest
    membership: pl.DataFrame
    split_manifest: SplitManifestDocument
    assignments: pl.DataFrame


def preprocess_federated_stage(request: PreprocessFederatedRequest) -> PreprocessFederatedResult:
    """Construct population partitions and publish per-client federated preprocessed assets."""
    _validate_federated_request(request)
    binding = resolve_population(request.population)
    dataset = binding.declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    require_canonical_publication_complete(canonical_root, dataset, "federated preprocessing")

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
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
            dataset=dataset,
            deployment_fallback_client_ids=frozenset(),
            capture_timestamp_column=_capture_timestamp_column(request),
        )
    )
    schema = dataset_binding(dataset).schema
    feature_names = _model_feature_names(dataset, schema.feature_columns)
    protocol = _federated_protocol(request.preprocessing_identity, feature_names)
    joined = join_handoff_with_canonical_features(canonical_root, handoff, feature_names)
    context = PreprocessingPublishContext(
        dataset=dataset,
        population=request.population,
        partition_seed=request.partition_seed,
        split_protocol_identity=request.split_protocol,
        protocol=protocol,
        canonical_schema_checksum=schema.checksum,
        data_root=request.data_root,
    )

    client_ids = tuple(sorted(str(value) for value in joined.get_column(CLIENT_ID_COLUMN).unique().to_list()))
    client_partitions: dict[str, ClientPartitionBundle] = {
        client_id: extract_partitions(
            joined.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            feature_names,
            split_protocol=request.split_protocol,
            branch=ProcessedDataBranch.FEDERATED,
            deterministic_sort=False,
        )
        for client_id in client_ids
    }
    fitted_by_client = fit_estimators_for_federated_clients(protocol, client_ids, client_partitions)

    publications: list[ClientPreprocessPublication] = []
    published_count = 0
    reused_count = 0
    for client_id in client_ids:
        partitions, row_ids, _train_labels = client_partitions[client_id]
        result = publish_client_preprocessing(
            ClientPublishRequest(
                context=context,
                client_identity=ClientPathToken(client_id),
                fitted_estimator=fitted_by_client[client_id],
                partitions=partitions,
                row_ids=row_ids,
            )
        )
        if result.publication_status is PublicationStatus.REUSED:
            reused_count += 1
        else:
            published_count += 1
        publications.append(
            ClientPreprocessPublication(
                client_identity=result.client_identity,
                result=result,
                publication_status=result.publication_status,
                train_row_count=RowCount(partitions[PartitionRole.TRAIN].height),
                calibration_row_count=RowCount(partitions[PartitionRole.CALIBRATION].height),
                evaluation_row_count=RowCount(partitions[PartitionRole.EVALUATION].height),
                future_recalibration_row_count=RowCount(
                    partitions.get(
                        PartitionRole.FUTURE_RECALIBRATION,
                        pl.DataFrame(),
                    ).height
                ),
                static_reference_reserve_row_count=RowCount(
                    partitions.get(
                        PartitionRole.STATIC_REFERENCE_RESERVE,
                        pl.DataFrame(),
                    ).height
                ),
            )
        )

    return PreprocessFederatedResult(
        stage=StageOperationId.PREPROCESS_FEDERATED,
        population=request.population,
        dataset=dataset,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=tuple(publications),
        published_count=published_count,
        reused_count=reused_count,
    )


def preprocess_federated_artifacts_stage(
    request: PreprocessFederatedArtifactsRequest,
) -> PreprocessFederatedResult:
    """Publish federated preprocessing from immutable construct and split publications."""
    identity = require_execution_identity(request.execution_identity, request.execution_identity.population)
    if identity is None:
        raise AssertionError("published artifact preprocessing requires an execution identity")
    _validate_artifact_request(request)
    published = _load_published_population_split(request, identity)
    document = published.population_manifest.document
    dataset = document.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    require_canonical_publication_complete(canonical_root, dataset, "federated preprocessing")

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
        execution_identity=identity.document,
    )
    handoff = PreprocessingHandoff(
        population_manifest=published.population_manifest,
        membership=published.membership,
        assignments=published.assignments,
        client_partition_counts=(),
    )
    if dataset is DatasetId.CICIOT2023 and protocol.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
        return _preprocess_ciciot_client_local(
            context=context,
            assignments=published.assignments,
            canonical_root=canonical_root,
            feature_names=feature_names,
            identity=identity,
        )
    joined = _join_published_handoff(canonical_root, handoff, feature_names, identity)
    client_ids = tuple(sorted(str(value) for value in joined.get_column(CLIENT_ID_COLUMN).unique().to_list()))
    client_partitions: dict[str, ClientPartitionBundle] = {
        client_id: extract_partitions(
            joined.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            feature_names,
            split_protocol=published.split_manifest.split_protocol,
            branch=ProcessedDataBranch.FEDERATED,
            deterministic_sort=False,
        )
        for client_id in client_ids
    }
    fitted_by_client = fit_estimators_for_federated_clients(protocol, client_ids, client_partitions)
    publications, published_count, reused_count = _publish_client_partitions(
        context,
        client_ids,
        client_partitions,
        fitted_by_client,
    )
    return PreprocessFederatedResult(
        stage=StageOperationId.PREPROCESS_FEDERATED,
        population=document.population,
        dataset=dataset,
        partition_seed=document.partition_seed,
        split_protocol=published.split_manifest.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=publications,
        published_count=published_count,
        reused_count=reused_count,
        execution_identity=identity,
    )


def _preprocess_ciciot_client_local(
    *,
    context: PreprocessingPublishContext,
    assignments: pl.DataFrame,
    canonical_root: Path,
    feature_names: FeatureNameSequence,
    identity: ExternalTemporalExecutionIdentity,
) -> PreprocessFederatedResult:
    """Fit and publish one file-defined client at a time without materializing the federation-wide join."""
    client_ids = tuple(sorted(str(value) for value in assignments.get_column(CLIENT_ID_COLUMN).unique().to_list()))
    source_files = _ciciot_source_files(canonical_root)
    publications: list[ClientPreprocessPublication] = []
    published_count = 0
    reused_count = 0
    for client_id in client_ids:
        client_assignments = assignments.filter(pl.col(CLIENT_ID_COLUMN) == client_id)
        source_path = _single_client_source_path(client_assignments, client_id)
        feature_frame = pl.read_parquet(
            source_files[source_path],
            columns=[STABLE_ROW_ID_COLUMN, *feature_names],
        )
        joined = client_assignments.join(feature_frame, on=STABLE_ROW_ID_COLUMN, how="inner").sort(
            [PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN]
        )
        if joined.height != client_assignments.height:
            raise ScientificContractError(
                "canonical feature join lost file-client assignment rows",
                subject=identity.population,
            )
        partitions, row_ids, _train_labels = extract_partitions(
            joined,
            feature_names,
            split_protocol=context.split_protocol_identity,
            branch=ProcessedDataBranch.FEDERATED,
            deterministic_sort=False,
        )
        fitted = fit_estimators_for_federated_clients(
            context.protocol,
            (client_id,),
            {client_id: (partitions, row_ids, _train_labels)},
        )[client_id]
        publication = _publish_client_partition(context, client_id, partitions, row_ids, fitted)
        if publication.publication_status is PublicationStatus.REUSED:
            reused_count += 1
        else:
            published_count += 1
        publications.append(publication)
    return PreprocessFederatedResult(
        stage=StageOperationId.PREPROCESS_FEDERATED,
        population=identity.population,
        dataset=DatasetId.CICIOT2023,
        partition_seed=context.partition_seed,
        split_protocol=context.split_protocol_identity,
        preprocessing_identity=context.protocol.identity,
        client_publications=tuple(publications),
        published_count=published_count,
        reused_count=reused_count,
        execution_identity=identity,
    )


def _ciciot_source_files(canonical_root: Path) -> dict[str, Path]:
    source_files: dict[str, Path] = {}
    for path in sorted((canonical_root / "data").glob("*.parquet")):
        source_path = pl.read_parquet(path, columns=["source_path"], n_rows=1).item(0, 0)
        source_files[str(source_path)] = path
    if not source_files:
        raise ScientificContractError("CIC canonical files are unavailable", subject=DatasetId.CICIOT2023)
    return source_files


def _single_client_source_path(assignments: pl.DataFrame, client_id: str) -> str:
    sources = tuple(sorted(str(value) for value in assignments.get_column("source_path").unique().to_list()))
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
    if (
        identity.population is not PopulationId.EDGE_TEMPORAL_GROUPS
        and identity.population is not PopulationId.EDGE_SENSOR_GROUPS
    ):
        return join_handoff_with_canonical_features(canonical_root, handoff, feature_names)
    asset_role = (
        EdgeAssetRole.TEMPORAL_BENIGN
        if identity.population is PopulationId.EDGE_TEMPORAL_GROUPS
        else EdgeAssetRole.STATIC_BENIGN
    )
    assignments = handoff.assignments
    feature_scan = pl.scan_parquet(str(canonical_root / "data" / asset_role.value / "*.parquet")).select(
        [STABLE_ROW_ID_COLUMN, *(pl.col(name).cast(pl.Float64, strict=True).alias(name) for name in feature_names)]
    )
    joined = (
        assignments.lazy()
        .join(feature_scan, on=STABLE_ROW_ID_COLUMN, how="inner")
        .collect()
        .sort([CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN])
    )
    if joined.height != assignments.height:
        raise ScientificContractError(
            "canonical feature join lost assignment rows",
            subject=handoff.population_manifest.document.dataset,
        )
    return joined


def _model_feature_names(dataset: DatasetId, feature_names: tuple[str, ...]) -> FeatureNameSequence:
    if dataset is not DatasetId.EDGE_IIOTSET:
        return FeatureNameSequence(feature_names)
    if set(EDGE_NUMERIC_FEATURE_COLUMNS) - set(feature_names):
        raise ScientificContractError("Edge numeric feature declaration must be a canonical feature subset")
    return FeatureNameSequence(EDGE_NUMERIC_FEATURE_COLUMNS)


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


def _publish_client_partitions(
    context: PreprocessingPublishContext,
    client_ids: tuple[str, ...],
    client_partitions: dict[str, ClientPartitionBundle],
    fitted_by_client: dict[str, TrustedScaler],
) -> tuple[tuple[ClientPreprocessPublication, ...], int, int]:
    publications: list[ClientPreprocessPublication] = []
    published_count = 0
    reused_count = 0
    for client_id in client_ids:
        partitions, row_ids, _train_labels = client_partitions[client_id]
        publication = _publish_client_partition(
            context,
            client_id,
            partitions,
            row_ids,
            fitted_by_client[client_id],
        )
        if publication.publication_status is PublicationStatus.REUSED:
            reused_count += 1
        else:
            published_count += 1
        publications.append(publication)
    return tuple(publications), published_count, reused_count


def _publish_client_partition(
    context: PreprocessingPublishContext,
    client_id: str,
    partitions: Mapping[PartitionRole, pl.DataFrame],
    row_ids: Mapping[PartitionRole, Sequence[str]],
    fitted_estimator: TrustedScaler,
) -> ClientPreprocessPublication:
    """Persist one already-fitted client partition bundle."""
    result = publish_client_preprocessing(
        ClientPublishRequest(
            context=context,
            client_identity=ClientPathToken(client_id),
            fitted_estimator=fitted_estimator,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    return ClientPreprocessPublication(
        client_identity=result.client_identity,
        result=result,
        publication_status=result.publication_status,
        train_row_count=RowCount(partitions[PartitionRole.TRAIN].height),
        calibration_row_count=RowCount(partitions[PartitionRole.CALIBRATION].height),
        evaluation_row_count=RowCount(partitions[PartitionRole.EVALUATION].height),
        future_recalibration_row_count=RowCount(
            partitions.get(PartitionRole.FUTURE_RECALIBRATION, pl.DataFrame()).height
        ),
        static_reference_reserve_row_count=RowCount(
            partitions.get(PartitionRole.STATIC_REFERENCE_RESERVE, pl.DataFrame()).height
        ),
    )


def _load_published_population_split(
    request: PreprocessFederatedArtifactsRequest,
    identity: ExternalTemporalExecutionIdentity,
) -> _PublishedPopulationSplit:
    use_static_reference = identity.temporal_state is TemporalState.STATIC_REFERENCE
    population_manifest_name = (
        "matched_static_reference_manifest.json" if use_static_reference else "population_manifest.json"
    )
    membership_name = "matched_static_reference_membership.parquet" if use_static_reference else "membership.parquet"
    split_manifest_name = (
        "matched_static_reference_split_manifest.json" if use_static_reference else "split_manifest.json"
    )
    assignments_name = (
        "matched_static_reference_assignments.parquet" if use_static_reference else "split_assignments.parquet"
    )
    population_document = _read_population_document(request.population_directory / population_manifest_name)
    split_document = _read_split_document(request.split_directory / split_manifest_name)
    membership = _read_parquet(request.population_directory / membership_name, identity.population)
    assignments = _read_parquet(request.split_directory / assignments_name, identity.population)
    _validate_population_publication(request.population_directory, identity)
    _validate_split_publication(request.split_directory, identity)
    manifest = _population_manifest_from_document(population_document)
    split_manifest = split_document
    _validate_published_pair(manifest, membership, split_manifest, assignments, identity, use_static_reference)
    return _PublishedPopulationSplit(manifest, membership, split_manifest, assignments)


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
    population = identity.population
    complete = _read_complete_digest(directory, population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_population_document(directory / "population_manifest.json")
    payload = "\n".join((identity.document.model_dump_json(indent=2), primary.model_dump_json(indent=2)))
    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        chronology = _read_chronology_document(directory / "chronology.json")
        static = _read_population_document(directory / "matched_static_reference_manifest.json")
        payload = "\n".join((payload, chronology.model_dump_json(indent=2), static.model_dump_json(indent=2)))
    if complete != checksum_text(payload + "\n"):
        raise ScientificContractError(
            "published population COMPLETE digest does not match its manifests",
            subject=population,
        )


def _validate_split_publication(directory: Path, identity: ExternalTemporalExecutionIdentity) -> None:
    population = identity.population
    complete = _read_complete_digest(directory, population)
    _validate_persisted_execution_identity(directory, identity)
    primary = _read_split_document(directory / "split_manifest.json")
    payload = "\n".join((identity.document.model_dump_json(indent=2), primary.model_dump_json(indent=2)))
    if primary.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        static = _read_split_document(directory / "matched_static_reference_split_manifest.json")
        payload = "\n".join((payload, static.model_dump_json(indent=2)))
    if complete != checksum_text(payload + "\n"):
        raise ScientificContractError(
            "published split COMPLETE digest does not match its manifests",
            subject=population,
        )


def _validate_persisted_execution_identity(
    directory: Path,
    identity: ExternalTemporalExecutionIdentity,
) -> None:
    try:
        persisted = ExecutionIdentityDocument.model_validate_json(
            (directory / "execution_identity.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "published artifact lacks a valid execution identity",
            subject=identity.population,
        ) from error
    if persisted != identity.document:
        raise ScientificContractError(
            "published artifact execution identity does not match the request",
            subject=identity.population,
        )


def _read_complete_digest(directory: Path, population: PopulationId) -> Checksum:
    try:
        return Checksum((directory / "COMPLETE").read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as error:
        raise ScientificContractError(
            "published artifact COMPLETE marker is missing or invalid", subject=population
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
            observed_client_count=len(document.accepted_clients),
            evidence="persisted population manifest",
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
    population = identity.population
    document = population_manifest.document
    split_document = split_manifest
    if document.population is not population or split_document.population is not population:
        raise ScientificContractError(
            "published population and split must match execution identity", subject=population
        )
    if document.dataset is not split_document.dataset or document.partition_seed != split_document.partition_seed:
        raise ScientificContractError("published population and split coordinates disagree", subject=population)
    if membership_frame_checksum(membership) != document.membership_checksum:
        raise ScientificContractError("published membership checksum does not match its manifest", subject=population)
    if split_document.population_manifest_checksum != document.membership_checksum:
        raise ScientificContractError("split manifest is not bound to the published population", subject=population)
    expected_protocol = _expected_split_protocol(identity, use_static_reference)
    if split_document.split_protocol is not expected_protocol:
        raise ScientificContractError(
            "published split protocol is incompatible with execution identity", subject=population
        )
    validate_population_manifest(population_manifest, membership)
    validate_split_manifest(membership, assignments, split_manifest)
    if population is PopulationId.EDGE_TEMPORAL_GROUPS and not use_static_reference:
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
            method = scientific_preprocessing_method()
        case PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX:
            method = scientific_federated_pooled_min_max_method()
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing identity",
                subject=identity,
            )
    return build_preprocessing_protocol(method, feature_names)
