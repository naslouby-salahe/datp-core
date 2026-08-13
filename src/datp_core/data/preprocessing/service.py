from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    DatasetId,
    FeatureName,
    FeatureNameSequence,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.data.edge_iiotset.schema import EdgeCanonicalColumn
from datp_core.data.materialization import require_canonical_dataset
from datp_core.data.paths import canonical_root_under
from datp_core.data.populations.construction import (
    build_preprocessing_handoff,
    join_handoff_with_canonical_features,
)
from datp_core.data.populations.contracts import (
    ClientIdentity,
    PopulationConstructionRequest,
    PreprocessingHandoff,
    PreprocessingHandoffRequest,
)
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope
from datp_core.data.preprocessing.ciciot_file_clients import preprocess_ciciot_client_local
from datp_core.data.preprocessing.client_partitions import (
    MODEL_INPUT_EXCLUSION_ASSET,
    client_partitions,
    join_published_handoff,
    model_feature_names,
    publish_client_partitions,
    write_model_input_exclusion_evidence,
)
from datp_core.data.preprocessing.federated import fit_estimators_for_federated_clients
from datp_core.data.preprocessing.models import (
    SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD,
    SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    PublishedFederatedPreprocessingRequest,
    build_preprocessing_protocol,
)
from datp_core.data.preprocessing.persisted_artifacts import load_published_population_split
from datp_core.data.registry import construct_population, dataset_binding, resolve_population
from datp_core.experiments.common.coordinates import require_execution_identity

_FEDERATED_METHODS = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    }
)

_PROTOCOL_METHODS = {
    PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD: SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
    PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX: SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD,
}

_AUDITED_TIMESTAMP_COLUMN = CaptureTimestampColumn(EdgeCanonicalColumn.CAPTURE_TIMESTAMP.value)

_EMPTY_CLIENT_IDENTITIES: frozenset[ClientIdentity] = frozenset()


def preprocess_federated(
    request: FederatedPreprocessingRequest,
) -> FederatedPreprocessingOutcome:
    _validate_federated_request(request)
    binding = resolve_population(request.population)
    dataset = binding.declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)

    require_canonical_dataset(canonical_root, dataset)

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
    feature_names = model_feature_names(dataset, FeatureNameSequence(tuple(map(FeatureName, schema.feature_columns))))
    protocol = _federated_protocol(request.preprocessing_identity, feature_names)

    joined = join_handoff_with_canonical_features(
        canonical_root,
        handoff,
        feature_names,
    )

    document = construction.manifest.document
    context = PreprocessingPublishContext(
        dataset=document.dataset,
        population=document.population,
        partition_seed=document.partition_seed,
        split_protocol_identity=document.split_protocol,
        protocol=protocol,
        data_root=request.data_root,
        dirichlet_condition=request.dirichlet_condition,
    )

    partitions = client_partitions(
        joined,
        feature_names,
        document.split_protocol,
    )

    result = publish_client_partitions(
        context,
        partitions,
        fit_estimators_for_federated_clients(protocol, partitions),
    )

    return FederatedPreprocessingOutcome(
        population=document.population,
        dataset=document.dataset,
        partition_seed=document.partition_seed,
        split_protocol=document.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=result.publications,
        published_count=result.published_count,
    )


def preprocess_published_federated(
    request: PublishedFederatedPreprocessingRequest,
) -> FederatedPreprocessingOutcome:
    identity = require_execution_identity(
        request.execution_identity,
        request.execution_identity.population,
    )
    if identity is None:
        raise AssertionError("published artifact preprocessing requires an execution identity")

    _validate_artifact_request(request)
    published = load_published_population_split(request, identity)

    document = published.population_manifest.document
    dataset = document.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)

    require_canonical_dataset(canonical_root, dataset)

    schema = dataset_binding(dataset).schema
    feature_names = model_feature_names(dataset, FeatureNameSequence(tuple(map(FeatureName, schema.feature_columns))))
    protocol = _federated_protocol(request.preprocessing_identity, feature_names)

    context = PreprocessingPublishContext(
        dataset=dataset,
        population=document.population,
        partition_seed=document.partition_seed,
        split_protocol_identity=published.split_manifest.split_protocol,
        protocol=protocol,
        data_root=request.data_root,
        execution_identity=identity,
    )

    if dataset is DatasetId.CICIOT2023 and protocol.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
        return preprocess_ciciot_client_local(
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
        deployment_fallback_client_ids=_EMPTY_CLIENT_IDENTITIES,
        client_partition_counts=(),
    )

    handoff_join = join_published_handoff(
        canonical_root,
        handoff,
        feature_names,
        identity,
    )

    if handoff_join.exclusion_evidence is not None and handoff_join.exclusion_evidence.excluded_row_count.value:
        write_model_input_exclusion_evidence(
            request.split_directory.parent.joinpath(MODEL_INPUT_EXCLUSION_ASSET),
            handoff_join.exclusion_evidence,
        )

    partitions = client_partitions(
        handoff_join.joined_rows,
        feature_names,
        published.split_manifest.split_protocol,
    )

    result = publish_client_partitions(
        context,
        partitions,
        fit_estimators_for_federated_clients(protocol, partitions),
    )

    return FederatedPreprocessingOutcome(
        population=document.population,
        dataset=dataset,
        partition_seed=document.partition_seed,
        split_protocol=published.split_manifest.split_protocol,
        preprocessing_identity=request.preprocessing_identity,
        client_publications=result.publications,
        published_count=result.published_count,
        execution_identity=identity,
    )


def _validate_federated_request(
    request: FederatedPreprocessingRequest,
) -> None:
    if request.preprocessing_identity not in _FEDERATED_METHODS:
        raise ScientificContractError(
            ErrorMessage("federated preprocessing requires a federated preprocessing identity"),
            subject=request.preprocessing_identity,
        )
    if (
        request.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
        and request.population is not PopulationId.EDGE_TEMPORAL_CLIENTS
    ):
        raise ScientificContractError(
            ErrorMessage("chronological preprocessing is defined only for Edge temporal groups"),
            subject=request.population,
        )


def _validate_artifact_request(
    request: PublishedFederatedPreprocessingRequest,
) -> None:
    if request.preprocessing_identity not in _FEDERATED_METHODS:
        raise ScientificContractError(
            ErrorMessage("federated preprocessing requires a federated preprocessing identity"),
            subject=request.preprocessing_identity,
        )
    if request.execution_identity.population is PopulationId.EDGE_TEMPORAL_CLIENTS:
        _capture_timestamp_column_for(
            request.execution_identity.population,
            SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            request.capture_timestamp_column,
        )
    elif request.capture_timestamp_column is not None:
        raise ScientificContractError(
            ErrorMessage("non-temporal preprocessing cannot declare a capture timestamp column"),
            subject=request.execution_identity.population,
        )


def _capture_timestamp_column(
    request: FederatedPreprocessingRequest,
) -> CaptureTimestampColumn | None:
    return _capture_timestamp_column_for(
        request.population,
        request.split_protocol,
        request.capture_timestamp_column,
    )


def _capture_timestamp_column_for(
    population: PopulationId,
    split_protocol: SplitProtocolId,
    capture_timestamp_column: CaptureTimestampColumn | None,
) -> CaptureTimestampColumn | None:
    if split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        if capture_timestamp_column not in {None, _AUDITED_TIMESTAMP_COLUMN}:
            raise ScientificContractError(
                ErrorMessage("temporal preprocessing must use the audited Edge capture timestamp column"),
                subject=population,
            )
        return _AUDITED_TIMESTAMP_COLUMN
    return capture_timestamp_column


def _federated_protocol(
    identity: PreprocessingProtocolId,
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    try:
        method = _PROTOCOL_METHODS[identity]
    except KeyError as err:
        raise ScientificContractError(
            ErrorMessage("unsupported federated preprocessing identity"),
            subject=identity,
        ) from err
    return build_preprocessing_protocol(method, feature_names)
