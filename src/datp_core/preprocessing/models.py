"""Typed preprocessing protocol and fitted-state records."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl
from pydantic import model_validator

from datp_core.artifacts.layout import RelativeAssetPathSequence
from datp_core.artifacts.serialization import TrustedScaler
from datp_core.domain.contracts import ClientCollection, StrictModel
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
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
)
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


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
        _require_skops(
            self.serialization_format,
            "fitted preprocessing state",
        )
        forbidden = {
            STABLE_ROW_ID_COLUMN,
            OUTCOME_LABEL_COLUMN,
            PARTITION_ROLE_COLUMN,
        }
        if any(name in forbidden for name in self.input_feature_names.names):
            raise ValueError("input_feature_names cannot contain structural columns")
        return self


@dataclass(slots=True, eq=False)
class PreprocessingPartition:
    role: PartitionRole
    frame: pl.DataFrame

    def __post_init__(self) -> None:
        if self.frame.height == 0:
            raise ValueError(f"preprocessing partition {self.role.value} cannot be empty")
        for column in (STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN):
            if column not in self.frame.columns:
                raise ScientificContractError(
                    f"missing structural column {column}",
                    subject=ContractSubject.SCHEMA,
                )
            if self.frame.get_column(column).null_count() > 0:
                raise ValueError(f"{column} cannot contain null values")
        _ = self.row_ids
        _ = self.outcome_labels

    @property
    def row_ids(self) -> StableRowIdSequence:
        return StableRowIdSequence(
            tuple(StableRowId(str(value)) for value in self.frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
        )

    @property
    def outcome_labels(self) -> OutcomeLabelSequence:
        return OutcomeLabelSequence(
            tuple(OutcomeLabel(str(value)) for value in self.frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        )


@dataclass(slots=True, eq=False)
class PreprocessingPartitions:
    partitions: tuple[PreprocessingPartition, ...]

    def __post_init__(self) -> None:
        if not self.partitions:
            raise ValueError("preprocessing partitions cannot be empty")
        roles = tuple(partition.role for partition in self.partitions)
        if len(roles) != len(frozenset(roles)):
            raise ValueError("preprocessing partitions cannot contain duplicate roles")

    def require(self, role: PartitionRole) -> PreprocessingPartition:
        matches = tuple(partition for partition in self.partitions if partition.role is role)
        if len(matches) != 1:
            raise ScientificContractError(
                f"missing preprocessing partition {role.value}",
                subject=role,
            )
        return matches[0]

    def roles(self) -> tuple[PartitionRole, ...]:
        return tuple(partition.role for partition in self.partitions)


type FederatedFittedEstimators = ClientCollection[ClientPathToken, TrustedScaler] | TrustedScaler


@dataclass(frozen=True, slots=True)
class _FittedPreprocessingStateBase:
    protocol: PreprocessingProtocol
    estimator_path: Path
    estimator_checksum: Checksum
    fit_row_count: RowCount

    def __post_init__(self) -> None:
        if self.fit_row_count.value < 1:
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
        if any(item.source_row_count != item.output_row_count for item in self.partition_evidence):
            raise ValueError("source and output row counts must match")
        return self


def _require_train_partition(
    partition: PartitionRole,
    subject: str,
) -> None:
    if partition is not PartitionRole.TRAIN:
        raise ValueError(f"{subject} may fit only on the train partition")


def _require_skops(
    serialization_format: SerializationFormat,
    subject: str,
) -> None:
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


@dataclass(slots=True, eq=False)
class ClientPublishRequest:
    context: PreprocessingPublishContext
    client_identity: ClientPathToken
    fitted_estimator: TrustedScaler
    partitions: PreprocessingPartitions


@dataclass(slots=True, eq=False)
class PreprocessingFitBatch:
    training_matrix: np.ndarray
    training_row_ids: StableRowIdSequence
    training_labels: OutcomeLabelSequence


class PooledPreprocessingOwner(StrEnum):
    POOLED = "pooled"


@dataclass(frozen=True, slots=True)
class FittedStatePublishSpec[OwnerT]:
    protocol: PreprocessingProtocol
    estimator_path: Path
    fit_row_count: RowCount
    owner: OwnerT


@dataclass(frozen=True, slots=True)
class ScientificPreprocessingMethod:
    """Dataset-agnostic method lock bound later to a feature schema."""

    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    estimator_class_name: TrustedEstimatorClassName
    serialization_format: SerializationFormat
    fit_partition: PartitionRole
    numerical_equivalence_absolute_tolerance: AbsoluteTolerance

    def __post_init__(self) -> None:
        _require_train_partition(
            self.fit_partition,
            "scientific preprocessing",
        )
        _require_skops(
            self.serialization_format,
            "scientific preprocessing",
        )


SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=(NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE),
)

SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=(NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE),
)

SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=(NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE),
)


def build_preprocessing_protocol(
    method: ScientificPreprocessingMethod,
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    """Bind a locked scientific method to ordered model-input features."""
    return PreprocessingProtocol(
        identity=method.identity,
        fit_scope=method.fit_scope,
        input_feature_names=feature_names,
        serialization_format=method.serialization_format,
        estimator_class_name=method.estimator_class_name,
        numerical_equivalence_absolute_tolerance=(method.numerical_equivalence_absolute_tolerance),
    )
