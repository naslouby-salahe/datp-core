"""Independent pooled preprocessing workflow for the centralized reference."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.data.canonical_cache import require_canonical_publication_complete
from datp_core.data.paths import canonical_root_under
from datp_core.data.populations.construction import (
    build_preprocessing_handoff,
    join_handoff_with_canonical_features,
)
from datp_core.data.populations.contracts import (
    ControlledPartitionCondition,
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
)
from datp_core.data.preprocessing.artifact_validation import (
    centralized_fitted_state_after_publish,
    extract_partitions,
    fit_trusted_batch,
    publish_preprocessed_partitions,
)
from datp_core.data.preprocessing.artifacts import (
    PartitionOrdering,
    PreprocessingFitScope,
    ProcessedAssetName,
    RelativeAssetPathSequence,
    ReusableDataCoordinate,
    branch_asset_path,
    canonical_relative_asset_path,
    centralized_branch_directory,
    processed_asset_names,
)
from datp_core.data.preprocessing.models import (
    SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD,
    FederatedFittedPreprocessingState,
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PooledPreprocessingOwner,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
)
from datp_core.data.preprocessing.paths import build_preprocessed_partition_paths
from datp_core.data.preprocessing.state import TrustedScaler
from datp_core.data.registry import construct_population, dataset_binding, resolve_population
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    SplitProtocolId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.domain.values.identifiers import CaptureTimestampColumn, FeatureName, FeatureNameSequence


@dataclass(slots=True, eq=False)
class PooledPublishRequest:
    context: PreprocessingPublishContext
    fitted_estimator: TrustedScaler
    partitions: PreprocessingPartitions


@dataclass(slots=True, eq=False)
class CentralizedPreprocessingRequest:
    dataset_context: PreprocessingPublishContext
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True)
class CentralizedPopulationPreprocessingRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: CaptureTimestampColumn | None


@dataclass(frozen=True, slots=True)
class CentralizedPreprocessingOutcome:
    result: PooledPreprocessingResult
    population: PopulationId
    partition_seed: Seed
    preprocessing_identity: PreprocessingProtocolId
    publication_status: PublicationStatus
    dataset: DatasetId


def fit_pooled_preprocessing(
    protocol: PreprocessingProtocol,
    batch: PreprocessingFitBatch,
) -> TrustedScaler:
    return fit_trusted_batch(protocol, batch, subject=PreprocessingFitScope.POOLED_TRAINING)


def publish_pooled_preprocessing(request: PooledPublishRequest) -> PooledPreprocessingResult:
    context = request.context
    cond = context.dirichlet_condition

    branch_coordinate_directory = centralized_branch_directory(
        context.data_root,
        ReusableDataCoordinate(
            dataset=context.dataset,
            population=context.population,
            partition_seed=context.partition_seed,
            split_protocol_identity=context.split_protocol_identity,
            preprocessing_identity=context.protocol.identity,
            branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
            client_identity=None,
            controlled_partition_kind=cond.kind if cond else None,
            dirichlet_concentration=cond.concentration if cond else None,
        ),
    )

    asset_names = processed_asset_names(context.split_protocol_identity)
    asset_paths = RelativeAssetPathSequence(
        tuple(
            canonical_relative_asset_path(asset, ProcessedDataBranch.CENTRALIZED_REFERENCE, None)
            for asset in asset_names
        )
    )

    result = publish_preprocessed_partitions(
        context=context,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        coordinate_directory=branch_coordinate_directory,
        fitted_estimator=request.fitted_estimator,
        partitions=request.partitions,
        asset_paths=asset_paths,
    )

    state = centralized_fitted_state_after_publish(
        FittedStatePublishSpec(
            protocol=context.protocol,
            estimator_path=branch_asset_path(result.coordinate_directory, ProcessedAssetName.STATE),
            fit_row_count=RowCount(request.partitions.require(PartitionRole.TRAIN).frame.height),
            owner=PooledPreprocessingOwner.POOLED,
        )
    )

    return PooledPreprocessingResult(
        paths=build_preprocessed_partition_paths(result.coordinate_directory, context.split_protocol_identity),
        fitted_state=state,
        publication_status=result.publication_status,
    )


def reject_federated_state_for_pooled(state: FittedPreprocessingState) -> None:
    if isinstance(state, FederatedFittedPreprocessingState):
        raise LeakageError(
            "federated client fitted state cannot be reused by the centralized reference",
            subject=ProcessedDataBranch.FEDERATED,
        )


def preprocess_centralized(
    request: CentralizedPreprocessingRequest,
) -> CentralizedPreprocessingOutcome:
    context = request.dataset_context
    if context.protocol.identity is not PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX:
        raise ScientificContractError(
            "centralized preprocessing requires CENTRALIZED_POOLED_MIN_MAX",
            subject=context.protocol.identity,
        )

    train_partition = request.partitions.require(PartitionRole.TRAIN)
    fitted = fit_pooled_preprocessing(
        context.protocol,
        PreprocessingFitBatch(
            training_matrix=train_partition.frame.select(list(context.protocol.input_feature_names)).to_numpy(),
            training_row_ids=train_partition.row_ids,
            training_labels=train_partition.outcome_labels,
        ),
    )

    published = publish_pooled_preprocessing(
        PooledPublishRequest(
            context=context,
            fitted_estimator=fitted,
            partitions=request.partitions,
        )
    )

    reject_federated_state_for_pooled(published.fitted_state)

    return CentralizedPreprocessingOutcome(
        result=published,
        population=context.population,
        partition_seed=context.partition_seed,
        preprocessing_identity=context.protocol.identity,
        publication_status=published.publication_status,
        dataset=context.dataset,
    )


def preprocess_centralized_population(
    request: CentralizedPopulationPreprocessingRequest,
) -> CentralizedPreprocessingOutcome:
    if request.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise ScientificContractError(
            "temporal split preprocessing requires future_recalibration assets not yet in the core publish set",
            subject=request.split_protocol,
        )

    dataset = resolve_population(request.population).declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)

    require_canonical_publication_complete(
        canonical_root,
        dataset,
        ContractSubject.PREPROCESSING,
    )

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
            capture_timestamp_column=request.capture_timestamp_column,
        )
    )

    schema = dataset_binding(dataset).schema
    feature_names = FeatureNameSequence(tuple(map(FeatureName, schema.feature_columns)))
    protocol = build_centralized_preprocessing_protocol(feature_names)

    partitions = extract_partitions(
        join_handoff_with_canonical_features(
            canonical_root,
            handoff,
            feature_names,
        ),
        feature_names,
        split_protocol=construction.manifest.document.split_protocol,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        ordering=PartitionOrdering.STABLE_ROW_ID,
    )

    document = construction.manifest.document

    return preprocess_centralized(
        CentralizedPreprocessingRequest(
            dataset_context=PreprocessingPublishContext(
                dataset=document.dataset,
                population=document.population,
                partition_seed=document.partition_seed,
                split_protocol_identity=document.split_protocol,
                protocol=protocol,
                canonical_schema_checksum=schema.checksum,
                data_root=request.data_root,
                dirichlet_condition=request.dirichlet_condition,
            ),
            partitions=partitions,
        )
    )


def build_centralized_preprocessing_protocol(
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    return build_preprocessing_protocol(
        SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD,
        feature_names,
    )
