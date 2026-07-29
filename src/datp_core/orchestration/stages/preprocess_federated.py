"""Stage: federated preprocessing publication under processed coordinates."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.artifacts.serialization import TrustedScaler, construct_trusted_estimator
from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.models import CanonicalPublicationArtifact
from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import ClientIdentity, OutcomeLabelSequence, Seed
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
    join_handoff_with_canonical_features,
    resolve_population,
)
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ControlledPartitionCondition,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.federated import (
    ClientPublishRequest,
    fit_federated_preprocessing,
    publish_client_preprocessing,
)
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    PreprocessingFitBatch,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    build_preprocessing_protocol,
    scientific_federated_pooled_min_max_method,
    scientific_preprocessing_method,
)
from datp_core.preprocessing.validation import core_partition_roles

_FEDERATED_METHODS = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    }
)
type ClientPartitionBundle = tuple[
    Mapping[PartitionRole, pl.DataFrame],
    Mapping[PartitionRole, tuple[str, ...]],
    OutcomeLabelSequence,
]


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
class ClientPreprocessPublication:
    client_identity: ClientIdentity
    result: ClientPreprocessingResult
    publication_status: PublicationStatus
    train_row_count: int
    calibration_row_count: int
    evaluation_row_count: int


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


def preprocess_federated_stage(request: PreprocessFederatedRequest) -> PreprocessFederatedResult:
    """Construct population partitions and publish per-client federated preprocessed assets."""
    _validate_federated_request(request)
    binding = resolve_population(request.population)
    dataset = binding.declaration.dataset
    canonical_root = canonical_root_under(request.data_root, dataset)
    if not (canonical_root / CanonicalPublicationArtifact.COMPLETE).is_file():
        raise ScientificContractError(
            "canonical COMPLETE marker is required before federated preprocessing",
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
    protocol = _federated_protocol(request.preprocessing_identity, schema.feature_columns)
    joined = join_handoff_with_canonical_features(canonical_root, handoff, schema.feature_columns)
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
        client_id: _partitions_for_client(
            joined.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            schema.feature_columns,
        )
        for client_id in client_ids
    }
    fitted_by_client = _fit_estimators(protocol, client_ids, client_partitions)

    publications: list[ClientPreprocessPublication] = []
    published_count = 0
    reused_count = 0
    for client_id in client_ids:
        partitions, row_ids, _train_labels = client_partitions[client_id]
        result = publish_client_preprocessing(
            ClientPublishRequest(
                context=context,
                client_identity=ClientIdentity(client_id),
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
                train_row_count=partitions[PartitionRole.TRAIN].height,
                calibration_row_count=partitions[PartitionRole.CALIBRATION].height,
                evaluation_row_count=partitions[PartitionRole.EVALUATION].height,
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


def _fit_estimators(
    protocol: PreprocessingProtocol,
    client_ids: tuple[str, ...],
    client_partitions: Mapping[str, ClientPartitionBundle],
) -> dict[str, TrustedScaler]:
    estimator_template = construct_trusted_estimator(protocol.estimator_class_name)
    feature_names = list(protocol.input_feature_names)
    match protocol.fit_scope:
        case PreprocessingFitScope.CLIENT_LOCAL_TRAINING:
            fitted: dict[str, TrustedScaler] = {}
            for client_id in client_ids:
                partitions, row_ids, train_labels = client_partitions[client_id]
                fitted[client_id] = fit_federated_preprocessing(
                    protocol,
                    estimator_template,
                    PreprocessingFitBatch(
                        training_matrix=partitions[PartitionRole.TRAIN].select(feature_names).to_numpy(),
                        training_row_ids=row_ids[PartitionRole.TRAIN],
                        training_labels=train_labels,
                        benign_label=PopulationOutcomeLabel.BENIGN.value,
                    ),
                )
            return fitted
        case PreprocessingFitScope.POOLED_TRAINING:
            matrices = [
                client_partitions[client_id][0][PartitionRole.TRAIN].select(feature_names).to_numpy()
                for client_id in client_ids
            ]
            row_ids = tuple(
                row_id for client_id in client_ids for row_id in client_partitions[client_id][1][PartitionRole.TRAIN]
            )
            labels = OutcomeLabelSequence(
                tuple(label for client_id in client_ids for label in client_partitions[client_id][2])
            )
            pooled = fit_federated_preprocessing(
                protocol,
                estimator_template,
                PreprocessingFitBatch(
                    training_matrix=np.vstack(matrices),
                    training_row_ids=row_ids,
                    training_labels=labels,
                    benign_label=PopulationOutcomeLabel.BENIGN.value,
                ),
            )
            return {client_id: pooled for client_id in client_ids}
        case _:
            raise ScientificContractError(
                "unsupported federated preprocessing fit scope",
                subject=protocol.fit_scope,
            )


def _validate_federated_request(request: PreprocessFederatedRequest) -> None:
    if request.preprocessing_identity not in _FEDERATED_METHODS:
        raise ScientificContractError(
            "federated preprocess stage requires a federated preprocessing identity",
            subject=request.preprocessing_identity,
        )
    if request.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
        raise ScientificContractError(
            "temporal split preprocessing requires future_recalibration assets not yet in the core publish set",
            subject=request.split_protocol,
        )


def _federated_protocol(
    identity: PreprocessingProtocolId,
    feature_names: tuple[str, ...],
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


def _partitions_for_client(
    client_frame: pl.DataFrame,
    feature_names: tuple[str, ...],
) -> ClientPartitionBundle:
    partitions: dict[PartitionRole, pl.DataFrame] = {}
    row_ids: dict[PartitionRole, tuple[str, ...]] = {}
    for role in core_partition_roles():
        role_frame = client_frame.filter(pl.col(PARTITION_ROLE_COLUMN) == role.value)
        if role_frame.height == 0:
            raise ScientificContractError(
                f"client partition {role.value} is empty",
                subject=role,
            )
        keep = [STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names]
        partitions[role] = role_frame.select(keep)
        row_ids[role] = tuple(str(value) for value in role_frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    train_labels = OutcomeLabelSequence(
        tuple(str(value) for value in partitions[PartitionRole.TRAIN].get_column(OUTCOME_LABEL_COLUMN).to_list())
    )
    return partitions, row_ids, train_labels
