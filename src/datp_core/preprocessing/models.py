"""Typed preprocessing protocol and fitted-state records."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
from pydantic import model_validator

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
    AbsoluteTolerance,
    Checksum,
    ClientPathToken,
    FeatureNameSequence,
    OutcomeLabelSequence,
    RowCount,
    Seed,
    StableRowIdSequence,
)
from datp_core.experiments.models import ExternalTemporalExecutionIdentity
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE


class TransformedSchema(StrictModel):
    feature_names: FeatureNameSequence


class PreprocessingProtocol(StrictModel):
    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    input_feature_names: FeatureNameSequence
    transformed_schema: TransformedSchema
    serialization_format: SerializationFormat
    estimator_class_name: TrustedEstimatorClassName
    numerical_equivalence_absolute_tolerance: AbsoluteTolerance

    @model_validator(mode="after")
    def validate_protocol(self) -> "PreprocessingProtocol":
        _require_skops(self.serialization_format, "fitted preprocessing state")
        return self


@dataclass(frozen=True, slots=True)
class PreprocessingPartition:
    role: PartitionRole
    frame: pl.DataFrame

    @property
    def row_ids(self) -> StableRowIdSequence:
        ids = tuple(str(v) for v in self.frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
        return StableRowIdSequence(ids)

    @property
    def outcome_labels(self) -> OutcomeLabelSequence:
        labels = tuple(str(v) for v in self.frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        return OutcomeLabelSequence(labels)


@dataclass(frozen=True, slots=True)
class PreprocessingPartitionSet:
    partitions: tuple[PreprocessingPartition, ...]

    def __post_init__(self) -> None:
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
class ClientFittedEstimator:
    client_identity: ClientPathToken
    estimator: TrustedScaler


@dataclass(frozen=True, slots=True)
class ClientLocalFittedEstimators:
    estimators: tuple[ClientFittedEstimator, ...]

    def __post_init__(self) -> None:
        clients = tuple(item.client_identity for item in self.estimators)
        if len(frozenset(clients)) != len(clients):
            raise ValueError("ClientLocalFittedEstimators cannot contain duplicate client identities")

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


def _require_branch_client_pairing(branch: ProcessedDataBranch, client_identity: ClientPathToken | None) -> None:
    if branch is ProcessedDataBranch.FEDERATED:
        if not client_identity:
            raise ValueError("federated fitted state requires a client identity")
        return
    if client_identity is not None:
        raise ValueError("centralized fitted state cannot carry a federated client identity")


@dataclass(frozen=True, slots=True)
class FittedPreprocessingState:
    protocol: PreprocessingProtocol
    branch: ProcessedDataBranch
    client_identity: ClientPathToken | None
    estimator_path: Path
    estimator_checksum: Checksum
    fit_row_count: RowCount
    fit_partition: PartitionRole

    def __post_init__(self) -> None:
        if self.fit_row_count < 1:
            raise ValueError("fitted preprocessing requires at least one training row")
        _require_train_partition(self.fit_partition, "fitted preprocessing")
        _require_branch_client_pairing(self.branch, self.client_identity)


@dataclass(frozen=True, slots=True)
class PreprocessedPartitionPaths:
    train: Path
    calibration: Path
    evaluation: Path
    future_recalibration: Path | None = None
    static_reference_reserve: Path | None = None


@dataclass(frozen=True, slots=True)
class ClientPreprocessingResult:
    client_identity: ClientPathToken
    paths: PreprocessedPartitionPaths
    fitted_state: FittedPreprocessingState
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
    fitted_state: FittedPreprocessingState
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
    asset_paths: tuple[str, ...]
    fit_partition: PartitionRole
    execution_identity: ExternalTemporalExecutionIdentity | None = None

    @model_validator(mode="after")
    def validate_manifest(self) -> "PreprocessingManifest":
        if self.fit_partition is not PartitionRole.TRAIN:
            raise ValueError("preprocessing manifests must record train-only fitting")
        if not self.asset_paths:
            raise ValueError("preprocessing manifests require published assets")
        if any("=" in path for path in self.asset_paths):
            raise ValueError("reusable data paths must not contain key=value segments")
        return self


class PartitionTransformationEvidence(StrictModel):
    role: PartitionRole
    source_row_count: RowCount
    output_row_count: RowCount


class PreprocessingValidationReport(StrictModel):
    fit_partition: PartitionRole
    validated_roles: tuple[PartitionRole, ...]
    partition_evidence: tuple[PartitionTransformationEvidence, ...]
    estimator_reload_verified: bool

    @model_validator(mode="after")
    def validate_report(self) -> "PreprocessingValidationReport":
        if self.fit_partition is not PartitionRole.TRAIN:
            raise ValueError("fit_partition must be TRAIN")
        if len(self.validated_roles) != len(frozenset(self.validated_roles)):
            raise ValueError("validated_roles must be unique")
        evidence_roles = tuple(item.role for item in self.partition_evidence)
        if set(evidence_roles) != set(self.validated_roles) or len(evidence_roles) != len(self.partition_evidence):
            raise ValueError("every validated role must have exactly one evidence record")
        for item in self.partition_evidence:
            if item.source_row_count != item.output_row_count:
                raise ValueError("source and output row counts must match")
        if not self.estimator_reload_verified:
            raise ValueError("estimator_reload_verified must be true")
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
class FittedStatePublishSpec:
    protocol: PreprocessingProtocol
    branch: ProcessedDataBranch
    estimator_path: Path
    fit_row_count: RowCount
    client_identity: ClientPathToken | None


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
    numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE,
)


def build_preprocessing_protocol(
    method: ScientificPreprocessingMethod,
    feature_names: FeatureNameSequence,
) -> PreprocessingProtocol:
    """Bind a locked scientific method to an ordered model-input feature schema."""
    transformed_schema = TransformedSchema(feature_names=feature_names)
    return PreprocessingProtocol(
        identity=method.identity,
        fit_scope=method.fit_scope,
        input_feature_names=feature_names,
        transformed_schema=transformed_schema,
        serialization_format=method.serialization_format,
        estimator_class_name=method.estimator_class_name,
        numerical_equivalence_absolute_tolerance=method.numerical_equivalence_absolute_tolerance,
    )
