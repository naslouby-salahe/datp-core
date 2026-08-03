"""Scientific leakage and schema validation for preprocessing."""

from collections.abc import Iterable
from itertools import combinations
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.artifacts.layout import (
    ProcessedAssetName,
    RelativeAssetPathSequence,
    asset_for_partition,
    partition_roles,
    processed_asset_names,
)
from datp_core.artifacts.reload_validation import TransformReloadCheck, reload_and_compare_transform
from datp_core.artifacts.serialization import TrustedScaler, resolve_trusted_estimator_type, serialize_estimator
from datp_core.artifacts.store import ProcessedPublication, ProcessedPublicationResult, publish_processed
from datp_core.domain.enums import (
    ContractSubject,
    PartitionOrdering,
    PartitionRole,
    PreprocessingFitScope,
    ProcessedDataBranch,
    SplitProtocolId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, ClientPathToken, FeatureNameSequence, RowCount, checksum_file, checksum_text
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    FederatedFittedPreprocessingState,
    FittedStatePublishSpec,
    PartitionTransformationEvidence,
    PooledPreprocessingOwner,
    PreprocessingFitBatch,
    PreprocessingManifest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    PreprocessingValidationReport,
    TransformedSchema,
)


def require_columns(
    frame: pl.DataFrame,
    columns: Iterable[str],
    *,
    subject: ContractSubject | PartitionRole | PreprocessingFitScope | SplitProtocolId,
) -> None:
    missing = tuple(column for column in columns if column not in frame.columns)
    if missing:
        raise ScientificContractError(f"missing required column(s): {', '.join(missing)}", subject=subject)


def require_partitions(
    partitions: PreprocessingPartitions,
    *,
    split_protocol: SplitProtocolId,
    subject: PreprocessingFitScope,
) -> None:
    if partitions.roles() != partition_roles(split_protocol):
        raise ScientificContractError(
            f"{subject.value} partition inventory does not match {split_protocol.value}",
            subject=split_protocol,
        )


def extract_partitions(
    frame: pl.DataFrame,
    feature_names: FeatureNameSequence,
    *,
    split_protocol: SplitProtocolId,
    branch: ProcessedDataBranch,
    ordering: PartitionOrdering,
) -> PreprocessingPartitions:
    require_columns(
        frame,
        [PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names],
        subject=ContractSubject.SCHEMA,
    )
    normalized = frame.with_columns(pl.col(PARTITION_ROLE_COLUMN).cast(pl.String))
    role_series = normalized.get_column(PARTITION_ROLE_COLUMN)
    if role_series.null_count():
        raise ScientificContractError("partition role column contains null values", subject=ContractSubject.SCHEMA)
    expected_roles = partition_roles(split_protocol)
    if set(role_series.unique().to_list()) != {role.value for role in expected_roles}:
        raise ScientificContractError(
            f"extracted roles do not match {split_protocol.value}",
            subject=ContractSubject.SCHEMA,
        )
    keep = [STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names]
    extracted: list[PreprocessingPartition] = []
    for role in expected_roles:
        role_frame = normalized.filter(pl.col(PARTITION_ROLE_COLUMN) == role.value).select(keep)
        if ordering is PartitionOrdering.STABLE_ROW_ID:
            role_frame = role_frame.sort(STABLE_ROW_ID_COLUMN)
        if not role_frame.height:
            raise ScientificContractError(f"{branch.value} partition {role.value} is empty", subject=role)
        extracted.append(PreprocessingPartition(role, role_frame))
    partitions = PreprocessingPartitions(tuple(extracted))
    if sum(partition.frame.height for partition in partitions.partitions) != normalized.height:
        raise ScientificContractError("partition extraction lost rows", subject=ContractSubject.ROWS)
    return partitions


def validate_no_partition_overlap(partitions: PreprocessingPartitions, *, split_protocol: SplitProtocolId) -> None:
    groups = tuple(
        (role, frozenset(partitions.require(role).row_ids.row_ids)) for role in partition_roles(split_protocol)
    )
    for (left_role, left_ids), (right_role, right_ids) in combinations(groups, 2):
        overlap = left_ids & right_ids
        if overlap:
            raise LeakageError(
                f"source-row overlap between {left_role.value} and {right_role.value}: {min(map(str, overlap))}",
                subject=left_role,
            )


def require_finite_matrix(
    matrix: np.ndarray,
    *,
    subject: PartitionRole | PreprocessingFitScope | ContractSubject,
    description: str,
) -> None:
    if not np.isfinite(matrix).all():
        raise ScientificContractError(f"{description} must be finite", subject=subject)


def transform_feature_matrix(
    fitted_estimator: TrustedScaler,
    matrix: np.ndarray,
    feature_names: FeatureNameSequence,
    subject: PartitionRole | PreprocessingFitScope,
    *,
    description: str,
) -> np.ndarray:
    if matrix.ndim != 2:
        raise ScientificContractError("source matrix must be two-dimensional", subject=subject)
    try:
        transformed = np.asarray(fitted_estimator.transform(matrix), dtype=float)
    except Exception as error:
        raise ScientificContractError(f"estimator transform failed: {error}", subject=subject) from error
    if transformed.shape != (matrix.shape[0], len(feature_names)):
        raise ScientificContractError("transformed matrix shape must match rows and schema", subject=subject)
    require_finite_matrix(transformed, subject=subject, description=description)
    return transformed


def protocol_content_checksum(protocol: PreprocessingProtocol) -> Checksum:
    return checksum_text(protocol.model_dump_json())


def build_preprocessing_manifest(
    context: PreprocessingPublishContext,
    *,
    branch: ProcessedDataBranch,
    asset_paths: RelativeAssetPathSequence,
) -> PreprocessingManifest:
    protocol = context.protocol
    return PreprocessingManifest(
        dataset=context.dataset,
        population=context.population,
        partition_seed=context.partition_seed,
        split_protocol_identity=context.split_protocol_identity,
        preprocessing_identity=protocol.identity,
        branch=branch,
        protocol_checksum=protocol_content_checksum(protocol),
        canonical_schema_checksum=context.canonical_schema_checksum,
        input_feature_names=protocol.input_feature_names,
        transformed_feature_names=protocol.input_feature_names,
        estimator_class_name=protocol.estimator_class_name,
        serialization_format=protocol.serialization_format,
        asset_paths=asset_paths,
        fit_partition=PartitionRole.TRAIN,
        execution_identity=context.execution_identity,
    )


def centralized_fitted_state_after_publish(
    spec: FittedStatePublishSpec[PooledPreprocessingOwner],
) -> CentralizedFittedPreprocessingState:
    if spec.owner is not PooledPreprocessingOwner.POOLED:
        raise ValueError("centralized fitted state requires the pooled owner")
    return CentralizedFittedPreprocessingState(
        spec.protocol,
        spec.estimator_path,
        checksum_file(spec.estimator_path),
        spec.fit_row_count,
    )


def federated_fitted_state_after_publish(
    spec: FittedStatePublishSpec[ClientPathToken],
) -> FederatedFittedPreprocessingState:
    return FederatedFittedPreprocessingState(
        spec.protocol,
        spec.estimator_path,
        checksum_file(spec.estimator_path),
        spec.fit_row_count,
        spec.owner,
    )


def fit_trusted_batch(
    protocol: PreprocessingProtocol,
    batch: PreprocessingFitBatch,
    *,
    subject: PreprocessingFitScope,
) -> TrustedScaler:
    if subject is not protocol.fit_scope:
        raise ScientificContractError("fit subject does not match protocol scope", subject=subject)
    try:
        matrix = np.asarray(batch.training_matrix, dtype=float)
    except Exception as error:
        raise ScientificContractError("training matrix must contain numeric values", subject=subject) from error
    if matrix.ndim != 2 or not matrix.shape[0]:
        raise ScientificContractError("training matrix must be non-empty and two-dimensional", subject=subject)
    if matrix.shape[0] not in {len(batch.training_row_ids), len(batch.training_labels)}:
        raise ScientificContractError("training matrix, rows, and labels must align", subject=PartitionRole.TRAIN)
    if matrix.shape[0] != len(batch.training_row_ids) or matrix.shape[0] != len(batch.training_labels):
        raise ScientificContractError("training matrix, rows, and labels must align", subject=PartitionRole.TRAIN)
    if matrix.shape[1] != len(protocol.input_feature_names):
        raise ScientificContractError("training width must match protocol features", subject=ContractSubject.FEATURES)
    require_finite_matrix(matrix, subject=subject, description="training matrix")
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in batch.training_labels.labels):
        raise LeakageError("attack-labelled rows cannot enter benign preprocessing fit", subject=ContractSubject.LABEL)
    try:
        fitted = resolve_trusted_estimator_type(protocol.estimator_class_name)()
        fitted.fit(matrix)
        transform_feature_matrix(
            fitted,
            matrix,
            protocol.input_feature_names,
            subject,
            description=f"{subject.value} training round-trip",
        )
        return fitted
    except (LeakageError, ScientificContractError):
        raise
    except Exception as error:
        raise ScientificContractError("estimator fitting failed", subject=subject) from error


def publish_preprocessed_partitions(
    *,
    context: PreprocessingPublishContext,
    branch: ProcessedDataBranch,
    coordinate_directory: Path,
    fitted_estimator: TrustedScaler,
    partitions: PreprocessingPartitions,
    asset_paths: RelativeAssetPathSequence,
) -> ProcessedPublicationResult[PreprocessingManifest]:
    require_partitions(
        partitions,
        split_protocol=context.split_protocol_identity,
        subject=context.protocol.fit_scope,
    )
    validate_no_partition_overlap(partitions, split_protocol=context.split_protocol_identity)
    return publish_processed(
        ProcessedPublication(
            coordinate_directory=coordinate_directory,
            manifest=build_preprocessing_manifest(context, branch=branch, asset_paths=asset_paths),
            schema=TransformedSchema(feature_names=context.protocol.input_feature_names),
            writer=lambda temporary: write_fitted_transformed_partitions(
                temporary,
                protocol=context.protocol,
                fitted_estimator=fitted_estimator,
                partitions=partitions,
                split_protocol=context.split_protocol_identity,
            ),
            required_assets=processed_asset_names(context.split_protocol_identity),
            overwrite=False,
            manifest_type=PreprocessingManifest,
            schema_type=TransformedSchema,
            report_type=PreprocessingValidationReport,
        )
    )


def write_fitted_transformed_partitions(
    temporary: Path,
    *,
    protocol: PreprocessingProtocol,
    fitted_estimator: TrustedScaler,
    partitions: PreprocessingPartitions,
    split_protocol: SplitProtocolId,
) -> PreprocessingValidationReport:
    if type(fitted_estimator) is not resolve_trusted_estimator_type(protocol.estimator_class_name):
        raise ScientificContractError("estimator type does not match protocol", subject=ContractSubject.FEATURES)
    feature_names = protocol.input_feature_names
    train = partitions.require(PartitionRole.TRAIN)
    require_columns(train.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    train_matrix = train.frame.select(list(feature_names)).to_numpy()
    train_transformed = transform_feature_matrix(
        fitted_estimator,
        train_matrix,
        feature_names,
        PartitionRole.TRAIN,
        description="transformed training matrix",
    )
    state_path = temporary / ProcessedAssetName.STATE
    serialize_estimator(fitted_estimator, state_path)
    reload_and_compare_transform(
        TransformReloadCheck(
            state_path,
            protocol.estimator_class_name,
            protocol.numerical_equivalence_absolute_tolerance,
            train_matrix,
            train_transformed,
        )
    )
    evidence: list[PartitionTransformationEvidence] = []
    for role in partition_roles(split_protocol):
        partition = partitions.require(role)
        require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
        transformed = (
            train_transformed
            if role is PartitionRole.TRAIN
            else transform_feature_matrix(
                fitted_estimator,
                partition.frame.select(list(feature_names)).to_numpy(),
                feature_names,
                role,
                description=f"transformed {role.value} matrix",
            )
        )
        retained = partition.frame.drop(feature_names.as_list())
        transformed_frame = pl.from_numpy(transformed, schema=feature_names.as_list())
        output = transformed_frame if not retained.width else retained.hstack(transformed_frame)
        expected_columns = [*retained.columns, *feature_names.as_list()]
        if output.columns != expected_columns or len(output.columns) != len(frozenset(output.columns)):
            raise ScientificContractError("invalid output column ordering", subject=ContractSubject.SCHEMA)
        output.write_parquet(temporary / asset_for_partition(role))
        evidence.append(
            PartitionTransformationEvidence(
                role,
                RowCount(partition.frame.height),
                RowCount(output.height),
            )
        )
    return PreprocessingValidationReport(partition_evidence=tuple(evidence))
