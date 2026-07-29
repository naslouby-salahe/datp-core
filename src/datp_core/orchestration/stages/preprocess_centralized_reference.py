"""Stage: independent pooled preprocessing for the centralized reference."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.centralized_reference.preprocessing import (
    PooledPublishRequest,
    fit_pooled_preprocessing,
    publish_pooled_preprocessing,
    reject_federated_state_for_pooled,
)
from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.models import CanonicalPublicationArtifact
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, FeatureNameSequence, OutcomeLabelSequence, Seed
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
    join_handoff_with_canonical_features,
    resolve_population,
)
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ControlledPartitionCondition,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
    scientific_centralized_preprocessing_method,
)
from datp_core.preprocessing.validation import core_partition_roles, validate_no_attack_labels_in_fit


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedReferenceRequest:
    dataset_context: PreprocessingPublishContext
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]
    training_labels: OutcomeLabelSequence
    benign_label: str


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
    stage: StageOperationId
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
    validate_no_attack_labels_in_fit(request.training_labels, request.benign_label)
    if PartitionRole.TRAIN not in request.partitions:
        raise ScientificContractError(
            "centralized preprocessing requires a train partition", subject=PartitionRole.TRAIN
        )
    train = request.partitions[PartitionRole.TRAIN]
    feature_names = context.protocol.input_feature_names
    matrix = train.select(list(feature_names)).to_numpy()
    estimator = construct_trusted_estimator(context.protocol.estimator_class_name)
    fitted = fit_pooled_preprocessing(
        context.protocol,
        estimator,
        PreprocessingFitBatch(
            training_matrix=matrix,
            training_row_ids=tuple(request.row_ids[PartitionRole.TRAIN]),
            training_labels=request.training_labels,
            benign_label=request.benign_label,
        ),
    )
    published = publish_pooled_preprocessing(
        PooledPublishRequest(
            context=context,
            fitted_estimator=fitted,
            partitions=request.partitions,
            row_ids=request.row_ids,
        )
    )
    reject_federated_state_for_pooled(published.fitted_state)
    return PreprocessCentralizedReferenceResult(
        stage=StageOperationId.PREPROCESS_CENTRALIZED_REFERENCE,
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
    binding = resolve_population(request.population)
    dataset = binding.declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    if not (canonical_root / CanonicalPublicationArtifact.COMPLETE).is_file():
        raise ScientificContractError(
            "canonical COMPLETE marker is required before centralized preprocessing",
            subject=dataset,
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
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
            dataset=dataset,
            capture_timestamp_column=request.capture_timestamp_column,
        )
    )
    schema = dataset_binding(dataset).schema
    protocol = build_centralized_preprocessing_protocol(FeatureNameSequence(schema.feature_columns))
    joined = join_handoff_with_canonical_features(canonical_root, handoff, schema.feature_columns)
    partitions, row_ids, training_labels = _pooled_partitions(joined, schema.feature_columns)
    context = PreprocessingPublishContext(
        dataset=dataset,
        population=request.population,
        partition_seed=request.partition_seed,
        split_protocol_identity=request.split_protocol,
        protocol=protocol,
        canonical_schema_checksum=schema.checksum,
        data_root=request.data_root,
    )
    return preprocess_centralized_reference_stage(
        PreprocessCentralizedReferenceRequest(
            dataset_context=context,
            partitions=partitions,
            row_ids=row_ids,
            training_labels=training_labels,
            benign_label=PopulationOutcomeLabel.BENIGN.value,
        )
    )


def build_centralized_preprocessing_protocol(feature_names: FeatureNameSequence) -> PreprocessingProtocol:
    return build_preprocessing_protocol(scientific_centralized_preprocessing_method(), feature_names.names)


def require_completed_centralized_preprocessing(state: FittedPreprocessingState) -> Checksum:
    if state.branch is not ProcessedDataBranch.CENTRALIZED_REFERENCE:
        raise LeakageError("expected centralized preprocessing completion", subject=state.branch)
    if not state.estimator_path.is_file():
        raise ArtifactIntegrityError(
            "centralized preprocessing state file is missing", subject=ContractSubject.ARTIFACT_PATH
        )
    return state.estimator_checksum


def rebuild_incomplete_centralized_preprocessing(directory: Path) -> None:
    if directory.exists():
        for path in sorted(directory.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def _pooled_partitions(
    joined: pl.DataFrame,
    feature_names: tuple[str, ...],
) -> tuple[Mapping[PartitionRole, pl.DataFrame], Mapping[PartitionRole, tuple[str, ...]], OutcomeLabelSequence]:
    partitions: dict[PartitionRole, pl.DataFrame] = {}
    row_ids: dict[PartitionRole, tuple[str, ...]] = {}
    keep = [STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names]
    for role in core_partition_roles():
        role_frame = (
            joined.filter(pl.col(PARTITION_ROLE_COLUMN) == role.value).select(keep).sort([STABLE_ROW_ID_COLUMN])
        )
        if role_frame.height == 0:
            raise ScientificContractError(
                f"pooled partition {role.value} is empty",
                subject=role,
            )
        partitions[role] = role_frame
        row_ids[role] = tuple(str(value) for value in role_frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    training_labels = OutcomeLabelSequence(
        tuple(str(value) for value in partitions[PartitionRole.TRAIN].get_column(OUTCOME_LABEL_COLUMN).to_list())
    )
    return partitions, row_ids, training_labels
