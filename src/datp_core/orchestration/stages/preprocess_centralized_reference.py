"""Stage: independent pooled preprocessing for the centralized reference."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.centralized_reference.preprocessing import (
    PooledPublishRequest,
    fit_pooled_preprocessing,
    publish_pooled_preprocessing,
    reject_federated_state_for_pooled,
)
from datp_core.datasets.canonical_cache import require_canonical_publication_complete
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionOrdering,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import FeatureName, FeatureNameSequence, Seed
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
    join_handoff_with_canonical_features,
    resolve_population,
)
from datp_core.populations.models import ControlledPartitionCondition
from datp_core.preprocessing.models import (
    SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
)
from datp_core.preprocessing.validation import extract_partitions


@dataclass(slots=True, eq=False)
class PreprocessCentralizedReferenceRequest:
    dataset_context: PreprocessingPublishContext
    partitions: PreprocessingPartitions


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedPopulationRequest:
    population: PopulationId
    partition_seed: Seed
    split_protocol: SplitProtocolId
    data_root: Path
    dirichlet_condition: ControlledPartitionCondition | None
    capture_timestamp_column: str | None


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.PREPROCESS_CENTRALIZED_REFERENCE
    result: PooledPreprocessingResult
    population: PopulationId
    partition_seed: Seed
    preprocessing_identity: PreprocessingProtocolId
    publication_status: PublicationStatus
    dataset: DatasetId


def preprocess_centralized_reference_stage(
    request: PreprocessCentralizedReferenceRequest,
) -> PreprocessCentralizedReferenceResult:
    context = request.dataset_context
    if context.protocol.identity is not PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX:
        raise ScientificContractError(
            "centralized preprocessing stage requires CENTRALIZED_POOLED_MIN_MAX",
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
    return PreprocessCentralizedReferenceResult(
        result=published,
        population=context.population,
        partition_seed=context.partition_seed,
        preprocessing_identity=context.protocol.identity,
        publication_status=published.publication_status,
        dataset=context.dataset,
    )


def preprocess_centralized_reference_population_stage(
    request: PreprocessCentralizedPopulationRequest,
) -> PreprocessCentralizedReferenceResult:
    """Construct population partitions, pool roles, and publish centralized-reference assets."""
    if request.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise ScientificContractError(
            "temporal split preprocessing requires future_recalibration assets not yet in the core publish set",
            subject=request.split_protocol,
        )
    dataset = resolve_population(request.population).declaration.dataset
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
            capture_timestamp_column=request.capture_timestamp_column,
        )
    )
    schema = dataset_binding(dataset).schema
    feature_names = FeatureNameSequence(tuple(FeatureName(name) for name in schema.feature_columns))
    protocol = build_centralized_preprocessing_protocol(feature_names)
    partitions = extract_partitions(
        join_handoff_with_canonical_features(canonical_root, handoff, feature_names),
        feature_names,
        split_protocol=construction.manifest.document.split_protocol,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        ordering=PartitionOrdering.STABLE_ROW_ID,
    )
    document = construction.manifest.document
    return preprocess_centralized_reference_stage(
        PreprocessCentralizedReferenceRequest(
            dataset_context=PreprocessingPublishContext(
                dataset=document.dataset,
                population=document.population,
                partition_seed=document.partition_seed,
                split_protocol_identity=document.split_protocol,
                protocol=protocol,
                canonical_schema_checksum=schema.checksum,
                data_root=request.data_root,
            ),
            partitions=partitions,
        )
    )


def build_centralized_preprocessing_protocol(feature_names: FeatureNameSequence) -> PreprocessingProtocol:
    return build_preprocessing_protocol(SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD, feature_names)
