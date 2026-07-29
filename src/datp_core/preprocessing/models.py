"""Typed preprocessing protocol and fitted-state records."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import model_validator

from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.values import Checksum, ClientIdentity, OutcomeLabelSequence, Seed
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE

SCIENTIFIC_TRANSFORM_ABSOLUTE_TOLERANCE = FIXED_SCORE_ABSOLUTE_TOLERANCE.value


class TransformedFeature(StrictModel):
    name: str
    position: int

    @model_validator(mode="after")
    def validate_feature(self) -> "TransformedFeature":
        if not self.name or self.position < 0:
            raise ValueError("transformed features require a name and non-negative position")
        return self


def _require_unique_names(names: tuple[str, ...], subject: str) -> None:
    if len(names) != len(frozenset(names)):
        raise ValueError(f"{subject} must be unique")


def _require_contiguous_positions(features: tuple[TransformedFeature, ...]) -> None:
    positions = tuple(feature.position for feature in features)
    if positions != tuple(range(len(features))):
        raise ValueError("transformed feature positions must be contiguous and ordered")


class TransformedSchema(StrictModel):
    features: tuple[TransformedFeature, ...]

    @model_validator(mode="after")
    def validate_schema(self) -> "TransformedSchema":
        if not self.features:
            raise ValueError("transformed schemas require at least one feature")
        _require_unique_names(tuple(feature.name for feature in self.features), "transformed feature names")
        _require_contiguous_positions(self.features)
        return self

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(feature.name for feature in self.features)


class PreprocessingProtocol(StrictModel):
    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    input_feature_names: tuple[str, ...]
    transformed_schema: TransformedSchema
    serialization_format: SerializationFormat
    estimator_module: TrustedEstimatorModule
    estimator_class_name: TrustedEstimatorClassName
    numerical_equivalence_absolute_tolerance: float

    @model_validator(mode="after")
    def validate_protocol(self) -> "PreprocessingProtocol":
        _require_ordered_unique_features(self.input_feature_names, "preprocessing")
        _require_skops(self.serialization_format, "fitted preprocessing state")
        _require_positive_tolerance(
            self.numerical_equivalence_absolute_tolerance,
            "numerical equivalence tolerance",
        )
        return self

    @property
    def qualified_estimator_name(self) -> str:
        return f"{_estimator_module_path(self.estimator_module)}.{_estimator_class_name(self.estimator_class_name)}"


def _estimator_module_path(module: TrustedEstimatorModule) -> str:
    match module:
        case TrustedEstimatorModule.SKLEARN_PREPROCESSING:
            return "sklearn.preprocessing"


def _estimator_class_name(class_name: TrustedEstimatorClassName) -> str:
    match class_name:
        case TrustedEstimatorClassName.STANDARD_SCALER:
            return "StandardScaler"
        case TrustedEstimatorClassName.MIN_MAX_SCALER:
            return "MinMaxScaler"


def _require_branch_client_pairing(branch: ProcessedDataBranch, client_identity: ClientIdentity | None) -> None:
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
    client_identity: ClientIdentity | None
    estimator_path: Path
    estimator_checksum: Checksum
    transformed_schema: TransformedSchema
    fit_row_count: int
    fit_partition: PartitionRole

    def __post_init__(self) -> None:
        if self.fit_row_count < 1:
            raise ValueError("fitted preprocessing requires at least one training row")
        _require_train_partition(self.fit_partition, "fitted preprocessing")
        _require_branch_client_pairing(self.branch, self.client_identity)


@dataclass(frozen=True, slots=True)
class ClientPreprocessingResult:
    client_identity: ClientIdentity
    train_path: Path
    calibration_path: Path
    evaluation_path: Path
    fitted_state: FittedPreprocessingState
    transformed_schema: TransformedSchema


@dataclass(frozen=True, slots=True)
class PooledPreprocessingResult:
    train_path: Path
    calibration_path: Path
    evaluation_path: Path
    fitted_state: FittedPreprocessingState
    transformed_schema: TransformedSchema


class PreprocessingManifest(StrictModel):
    dataset: DatasetId
    population: PopulationId
    partition_seed: Seed
    split_protocol_identity: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    branch: ProcessedDataBranch
    protocol_checksum: Checksum
    canonical_schema_checksum: Checksum
    input_feature_names: tuple[str, ...]
    transformed_feature_names: tuple[str, ...]
    estimator_class: str
    serialization_format: SerializationFormat
    asset_paths: tuple[str, ...]
    fit_partition: PartitionRole

    @model_validator(mode="after")
    def validate_manifest(self) -> "PreprocessingManifest":
        if self.fit_partition is not PartitionRole.TRAIN:
            raise ValueError("preprocessing manifests must record train-only fitting")
        if not self.asset_paths:
            raise ValueError("preprocessing manifests require published assets")
        if any("=" in path for path in self.asset_paths):
            raise ValueError("reusable data paths must not contain key=value segments")
        return self


class PreprocessingValidationReport(StrictModel):
    finite_transformed_values: bool
    train_only_fit: bool
    no_partition_overlap: bool
    schema_matches_protocol: bool
    branch_isolation: bool

    @model_validator(mode="after")
    def validate_report(self) -> "PreprocessingValidationReport":
        if not all(
            (
                self.finite_transformed_values,
                self.train_only_fit,
                self.no_partition_overlap,
                self.schema_matches_protocol,
                self.branch_isolation,
            )
        ):
            raise ValueError("preprocessing validation report contains failed checks")
        return self


def _require_train_partition(partition: PartitionRole, subject: str) -> None:
    if partition is not PartitionRole.TRAIN:
        raise ValueError(f"{subject} may fit only on the train partition")


def _require_skops(serialization_format: SerializationFormat, subject: str) -> None:
    if serialization_format is not SerializationFormat.SKOPS:
        raise ValueError(f"{subject} fitted state must use skops")


def _require_positive_tolerance(value: float, subject: str) -> None:
    if isinstance(value, bool) or value <= 0:
        raise ValueError(f"{subject} must be a positive float")


def _require_ordered_unique_features(feature_names: tuple[str, ...], subject: str) -> None:
    if not feature_names:
        raise ValueError(f"{subject} requires ordered input features")
    if len(feature_names) != len(frozenset(feature_names)):
        raise ValueError(f"{subject} input features must be unique")


@dataclass(frozen=True, slots=True)
class PreprocessingPublishContext:
    dataset: DatasetId
    population: PopulationId
    partition_seed: Seed
    split_protocol_identity: SplitProtocolId
    protocol: PreprocessingProtocol
    canonical_schema_checksum: Checksum
    data_root: Path


@dataclass(frozen=True, slots=True)
class PreprocessingFitBatch:
    training_matrix: np.ndarray
    training_row_ids: tuple[str, ...]
    training_labels: OutcomeLabelSequence
    benign_label: str


@dataclass(frozen=True, slots=True)
class FittedStatePublishSpec:
    protocol: PreprocessingProtocol
    branch: ProcessedDataBranch
    estimator_path: Path
    fit_row_count: int
    client_identity: ClientIdentity | None = None


@dataclass(frozen=True, slots=True)
class ScientificPreprocessingMethod:
    """Dataset-agnostic scientific method lock; feature order is bound per dataset schema."""

    identity: PreprocessingProtocolId
    fit_scope: PreprocessingFitScope
    estimator_module: TrustedEstimatorModule
    estimator_class_name: TrustedEstimatorClassName
    serialization_format: SerializationFormat
    fit_partition: PartitionRole
    numerical_equivalence_absolute_tolerance: float

    def __post_init__(self) -> None:
        _require_train_partition(self.fit_partition, "scientific preprocessing")
        _require_skops(self.serialization_format, "scientific preprocessing")
        _require_positive_tolerance(
            self.numerical_equivalence_absolute_tolerance,
            "scientific transform tolerance",
        )


SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
    estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
    estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=SCIENTIFIC_TRANSFORM_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=SCIENTIFIC_TRANSFORM_ABSOLUTE_TOLERANCE,
)

SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD = ScientificPreprocessingMethod(
    identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
    fit_scope=PreprocessingFitScope.POOLED_TRAINING,
    estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
    estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
    serialization_format=SerializationFormat.SKOPS,
    fit_partition=PartitionRole.TRAIN,
    numerical_equivalence_absolute_tolerance=SCIENTIFIC_TRANSFORM_ABSOLUTE_TOLERANCE,
)


def scientific_preprocessing_method() -> ScientificPreprocessingMethod:
    """Confirmatory federated method: paper-locked client-local StandardScaler."""
    return SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD


def scientific_federated_pooled_min_max_method() -> ScientificPreprocessingMethod:
    """Supportive FL-aligned method: pooled MinMax (not confirmatory)."""
    return SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD


def scientific_centralized_preprocessing_method() -> ScientificPreprocessingMethod:
    """Scientific method for the independent centralized-reference branch."""
    return SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD


def build_preprocessing_protocol(
    method: ScientificPreprocessingMethod,
    feature_names: tuple[str, ...],
) -> PreprocessingProtocol:
    """Bind a locked scientific method to an ordered model-input feature schema."""
    if not feature_names:
        raise ValueError("preprocessing requires ordered model-input feature names")
    if len(feature_names) != len(frozenset(feature_names)):
        raise ValueError("preprocessing feature names must be unique")
    transformed_schema = TransformedSchema(
        features=tuple(TransformedFeature(name=name, position=index) for index, name in enumerate(feature_names))
    )
    return PreprocessingProtocol(
        identity=method.identity,
        fit_scope=method.fit_scope,
        input_feature_names=feature_names,
        transformed_schema=transformed_schema,
        serialization_format=method.serialization_format,
        estimator_module=method.estimator_module,
        estimator_class_name=method.estimator_class_name,
        numerical_equivalence_absolute_tolerance=method.numerical_equivalence_absolute_tolerance,
    )
