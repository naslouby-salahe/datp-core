"""Typed preprocessing protocol and fitted-state records."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from pydantic import model_validator

from datp_core.artifacts.layout import RelativeAssetPathSequence
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    AbsoluteTolerance,
    Checksum,
    ClientPathToken,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    RowCount,
    Seed,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN


class TransformedSchema(StrictModel):
    feature_names: FeatureNameSequence


class PreprocessingProtocol(StrictModel):
    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    input_feature_names: FeatureNameSequence
    serialization_format: SerializationFormat
    estimator_class_name: TrustedEstimatorClassName
    numerical_equivalence_absolute_tolerance: AbsoluteTolerance

    @model_validator(mode="after")
    def validate_protocol(self) -> "PreprocessingProtocol":
        _require_skops(self.serialization_format, "fitted preprocessing state")
        forbidden = {STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, PARTITION_ROLE_COLUMN}
        if any(name in forbidden for name in self.input_feature_names.names):
            raise ValueError("input_feature_names cannot contain structural columns")
        return self


@dataclass(frozen=True, slots=True)
class PreprocessingPartition:
    role: PartitionRole
    frame: pl.DataFrame

    def __post_init__(self) -> None:
        if self.frame.height == 0:
            raise ValueError(f"PreprocessingPartition frame for role {self.role.value} cannot be empty")
        for col in (STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN):
            if col not in self.frame.columns:
                raise ScientificContractError(f"missing structural column {col}", subject=ContractSubject.SCHEMA)
        if self.frame.get_column(STABLE_ROW_ID_COLUMN).null_count() > 0:
            raise ValueError("STABLE_ROW_ID_COLUMN cannot contain null values")
        if self.frame.get_column(OUTCOME_LABEL_COLUMN).null_count() > 0:
            raise ValueError("OUTCOME_LABEL_COLUMN cannot contain null values")
        _ = self.row_ids
        _ = self.outcome_labels

    @property
    def row_ids(self) -> StableRowIdSequence:
        ids = tuple(StableRowId(str(v)) for v in self.frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
        return StableRowIdSequence(ids)

    @property
    def outcome_labels(self) -> OutcomeLabelSequence:
        labels = tuple(OutcomeLabel(str(v)) for v in self.frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        return OutcomeLabelSequence(labels)


@dataclass(frozen=True, slots=True)
class PreprocessingPartitionSet:
    partitions: tuple[PreprocessingPartition, ...]

    def __post_init__(self) -> None:
        if not self.partitions:
            raise ValueError("PreprocessingPartitionSet cannot be empty")
        roles = tuple(p.role for p in self.partitions)
        if len(frozenset(roles)) != len(roles):
            raise ValueError("PreprocessingPartitionSet cannot contain duplicate partition roles")

    def require(self, role: PartitionRole) -> PreprocessingPartition:
        for partition in self.partitions:
            if partition.role is role:
                return partition
        raise ScientificContractError(f"missing preprocessing partition {role.value}", subject=role)

    def roles(self) -> tuple[PartitionRole, ...]:
        return tuple(p.role for p in self.partitions)


@dataclass(frozen=True, slots=True)
class ClientPreprocessingPartitions:
    client_identity: ClientPathToken
    partitions: PreprocessingPartitionSet


@dataclass(frozen=True, slots=True)
class ClientPreprocessingPartitionSet:
    clients: tuple[ClientPreprocessingPartitions, ...]

    def __post_init__(self) -> None:
        if not self.clients:
            raise ValueError("ClientPreprocessingPartitionSet cannot be empty")
        identities = tuple(item.client_identity for item in self.clients)
        if len(frozenset(identities)) != len(identities):
            raise ValueError("ClientPreprocessingPartitionSet cannot contain duplicate client identities")


@dataclass(frozen=True, slots=True)
class ClientFittedEstimator:
    client_identity: ClientPathToken
    estimator: TrustedScaler


@dataclass(frozen=True, slots=True)
class ClientLocalFittedEstimators:
    estimators: tuple[ClientFittedEstimator, ...]

    def __post_init__(self) -> None:
        if not self.estimators:
            raise ValueError("ClientLocalFittedEstimators cannot be empty")
        clients = tuple(item.client_identity for item in self.estimators)
        if len(frozenset(clients)) != len(clients):
            raise ValueError("ClientLocalFittedEstimators cannot contain duplicate client identities")
        if len({id(item.estimator) for item in self.estimators}) != len(self.estimators):
            raise ValueError("client-local estimators must be distinct objects")

    def require(self, client_identity: ClientPathToken) -> TrustedScaler:
        for item in self.estimators:
            if item.client_identity == client_identity:
                return item.estimator
        raise ScientificContractError(
            f"missing estimator for client {client_identity.value}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


@dataclass(frozen=True, slots=True)
class PooledFittedEstimator:
    estimator: TrustedScaler


type FederatedFittedEstimators = ClientLocalFittedEstimators | PooledFittedEstimator


@dataclass(frozen=True, slots=True)
class _FittedPreprocessingStateBase:
    protocol: PreprocessingProtocol
    estimator_path: Path
    estimator_checksum: Checksum
    fit_row_count: RowCount

    def __post_init__(self) -> None:
        if self.fit_row_count < 1:
            raise ValueError("fitted preprocessing requires at least one training row")

    @property
    def fit_partition(self) -> PartitionRole:
        return PartitionRole.TRAIN


@dataclass(frozen=True, slots=True)
class CentralizedFittedPreprocessingState(_FittedPreprocessingStateBase):
    pass


@dataclass(frozen=True, slots=True)
class FederatedFittedPreprocessingState(_FittedPreprocessingStateBase):
    client_identity: ClientPathToken


type FittedPreprocessingState = CentralizedFittedPreprocessingState | FederatedFittedPreprocessingState


@dataclass(frozen=True, slots=True)
class PreprocessedPartitionPaths:
    train: Path
    calibration: Path
    evaluation: Path
    future_recalibration: Path | None
    static_reference_reserve: Path | None


@dataclass(frozen=True, slots=True)
class ClientPreprocessingResult:
    client_identity: ClientPathToken
    paths: PreprocessedPartitionPaths
    fitted_state: FederatedFittedPreprocessingState
    publication_status: PublicationStatus


@dataclass(frozen=True, slots=True)
class ClientPreprocessPublication:
    result: ClientPreprocessingResult
    train_row_count: RowCount
    calibration_row_count: RowCount
    evaluation_row_count: RowCount
    future_recalibration_row_count: RowCount
    static_reference_reserve_row_count: RowCount


@dataclass(frozen=True, slots=True)
class PooledPreprocessingResult:
    paths: PreprocessedPartitionPaths
    fitted_state: CentralizedFittedPreprocessingState
    publication_status: PublicationStatus


class PreprocessingManifest(StrictModel):
    dataset: DatasetId
    population: PopulationId
    partition_seed: Seed
    split_protocol_identity: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    branch: ProcessedDataBranch
    protocol_checksum: Checksum
    canonical_schema_checksum: Checksum
    input_feature_names: FeatureNameSequence
    transformed_feature_names: FeatureNameSequence
    estimator_class_name: TrustedEstimatorClassName
    serialization_format: SerializationFormat
    asset_paths: RelativeAssetPathSequence
    fit_partition: PartitionRole
    execution_identity: ExternalTemporalExecutionIdentity | None = None

    @model_validator(mode="after")
    def validate_manifest(self) -> "PreprocessingManifest":
        if self.fit_partition is not PartitionRole.TRAIN:
            raise ValueError("preprocessing manifests must record train-only fitting")
        if not self.asset_paths:
            raise ValueError("preprocessing manifests require published assets")
        return self


class PartitionTransformationEvidence(StrictModel):
    role: PartitionRole
    source_row_count: RowCount
    output_row_count: RowCount


class PreprocessingValidationReport(StrictModel):
    partition_evidence: tuple[PartitionTransformationEvidence, ...]

    @model_validator(mode="after")
    def validate_report(self) -> "PreprocessingValidationReport":
        if not self.partition_evidence:
            raise ValueError("partition_evidence cannot be empty")
        roles = tuple(item.role for item in self.partition_evidence)
        if len(roles) != len(frozenset(roles)):
            raise ValueError("partition evidence roles must be unique")
        if PartitionRole.TRAIN not in roles:
            raise ValueError("partition evidence must contain TRAIN")
        for item in self.partition_evidence:
            if item.source_row_count != item.output_row_count:
                raise ValueError("source and output row counts must match")
        return self


def _require_train_partition(partition: PartitionRole, subject: str) -> None:
    if partition is not PartitionRole.TRAIN:
        raise ValueError(f"{subject} may fit only on the train partition")


def _require_skops(serialization_format: SerializationFormat, subject: str) -> None:
    if serialization_format is not SerializationFormat.SKOPS:
        raise ValueError(f"{subject} fitted state must use skops")


@dataclass(frozen=True, slots=True)
class PreprocessingPublishContext:
    dataset: DatasetId
    population: PopulationId
    partition_seed: Seed
    split_protocol_identity: SplitProtocolId
    protocol: PreprocessingProtocol
    canonical_schema_checksum: Checksum
    data_root: Path
    execution_identity: ExternalTemporalExecutionIdentity | None = None


@dataclass(frozen=True, slots=True)
class ClientPublishRequest:
    context: PreprocessingPublishContext
    client_identity: ClientPathToken
    fitted_estimator: TrustedScaler
    partitions: PreprocessingPartitionSet


@dataclass(frozen=True, slots=True)
class PreprocessingFitBatch:
    training_matrix: np.ndarray
    training_row_ids: StableRowIdSequence
    training_labels: OutcomeLabelSequence


@dataclass(frozen=True, slots=True)
class CentralizedFittedStatePublishSpec:
    protocol: PreprocessingProtocol
    estimator_path: Path
    fit_row_count: RowCount


@dataclass(frozen=True, slots=True)
class FederatedFittedStatePublishSpec:
    protocol: PreprocessingProtocol
    estimator_path: Path
    fit_row_count: RowCount
    client_identity: ClientPathToken


@dataclass(frozen=True, slots=True)
class ScientificPreprocessingMethod:
    """Dataset-agnostic scientific method lock; feature order is bound per dataset schema."""

    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    estimator_class_name: TrustedEstimatorClassName
    serialization_format: SerializationFormat
    fit_partition: PartitionRole
    numerical_equivalence_absolute_tolerance: AbsoluteTolerance

    def __post_init__(self) -> None:
        _require_train_partition(self.fit_partition, "scientific preprocessing")
        _require_skops(self.serialization_format, "scientific preprocessing")


SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
)


def build_preprocessing_protocol(
    method: ScientificPreprocessingMethod,
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    """Bind a locked scientific method to an ordered model-input feature schema."""
    return PreprocessingProtocol(
        identity=method.identity,
        fit_scope=method.fit_scope,
        input_feature_names=feature_names,
        serialization_format=method.serialization_format,
        estimator_class_name=method.estimator_class_name,
        numerical_equivalence_absolute_tolerance=method.numerical_equivalence_absolute_tolerance,
    )
