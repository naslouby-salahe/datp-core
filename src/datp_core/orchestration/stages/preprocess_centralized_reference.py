"""Stage: independent pooled preprocessing for the centralized reference."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.centralized_reference.preprocessing import (
    PooledPublishRequest,
    fit_pooled_preprocessing,
    publish_pooled_preprocessing,
    reject_federated_state_for_pooled,
)
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, FeatureNameSequence, OutcomeLabelSequence, Seed
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PooledPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
    scientific_centralized_preprocessing_method,
)
from datp_core.preprocessing.validation import validate_no_attack_labels_in_fit


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedReferenceRequest:
    dataset_context: PreprocessingPublishContext
    partitions: Mapping[PartitionRole, pl.DataFrame]
    row_ids: Mapping[PartitionRole, Sequence[str]]
    training_labels: OutcomeLabelSequence
    benign_label: str


@dataclass(frozen=True, slots=True)
class PreprocessCentralizedReferenceResult:
    stage: StageOperationId
    result: PooledPreprocessingResult
    population: PopulationId
    partition_seed: Seed
    preprocessing_identity: PreprocessingProtocolId


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
