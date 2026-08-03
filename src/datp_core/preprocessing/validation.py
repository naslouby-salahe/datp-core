"""Scientific leakage and schema validation for preprocessing."""

from itertools import combinations
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.artifacts.layout import ProcessedAssetName, asset_for_partition, partition_roles, processed_asset_names
from datp_core.artifacts.reload_validation import TransformReloadCheck, reload_and_compare_transform
from datp_core.artifacts.serialization import (
    TrustedScaler,
    resolve_trusted_estimator_type,
    serialize_estimator,
)
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
from datp_core.domain.values import (
    Checksum,
    ClientPathToken,
    FeatureNameSequence,
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PartitionTransformationEvidence,
    PreprocessingFitBatch,
    PreprocessingManifest,
    PreprocessingPartition,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    PreprocessingValidationReport,
    TransformedSchema,
)


def require_partitions(
    partitions: PreprocessingPartitionSet,
    *,
    split_protocol: SplitProtocolId,
    subject: PreprocessingFitScope,
) -> None:
    required = partition_roles(split_protocol)
    if frozenset(partitions.roles()) != frozenset(required):
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
) -> PreprocessingPartitionSet:
    extracted: list[PreprocessingPartition] = []
    keep = [STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names]
    for role in partition_roles(split_protocol):
        role_frame = frame.filter(pl.col(PARTITION_ROLE_COLUMN) == role.value).select(keep)
        if ordering is PartitionOrdering.STABLE_ROW_ID:
            role_frame = role_frame.sort([STABLE_ROW_ID_COLUMN])
        if role_frame.height == 0:
            raise ScientificContractError(
                f"{branch.value} partition {role.value} is empty",
                subject=role,
            )
        extracted.append(PreprocessingPartition(role=role, frame=role_frame))
    return PreprocessingPartitionSet(partitions=tuple(extracted))


def validate_no_partition_overlap(
    partitions: PreprocessingPartitionSet,
    *,
    split_protocol: SplitProtocolId,
) -> None:
    required = partition_roles(split_protocol)
    groups = tuple((role, frozenset(partitions.require(role).row_ids.row_ids)) for role in required)
    for (left_role, left_ids), (right_role, right_ids) in combinations(groups, 2):
        overlap = left_ids & right_ids
        if overlap:
            raise LeakageError(
                f"source-row overlap between {left_role.value} and {right_role.value}: {next(iter(sorted(overlap)))}",
                subject=left_role,
            )


def validate_finite_matrix(
    matrix: np.ndarray, subject: PartitionRole | PreprocessingFitScope | ContractSubject
) -> None:
    if not np.isfinite(matrix).all():
        raise ScientificContractError("transformed values must be finite", subject=subject)


def transform_feature_matrix(
    fitted_estimator: TrustedScaler,
    matrix: np.ndarray,
    schema: TransformedSchema,
    subject: PartitionRole | PreprocessingFitScope,
) -> np.ndarray:
    if matrix.ndim != 2:
        raise ScientificContractError("source matrix must be two-dimensional", subject=subject)
    try:
        transformed = np.asarray(fitted_estimator.transform(matrix), dtype=float)
    except Exception as error:
        raise ScientificContractError(f"estimator transform failed: {error}", subject=subject) from error
    if transformed.ndim != 2:
        raise ScientificContractError("transformed matrix must be two-dimensional", subject=subject)
    if transformed.shape[0] != matrix.shape[0]:
        raise ScientificContractError("transformed row count must match input matrix", subject=subject)
    if transformed.shape[1] != len(schema.feature_names):
        raise ScientificContractError("transformed matrix width must match schema", subject=subject)
    validate_finite_matrix(transformed, subject)
    return transformed


def validate_branch_isolation(
    fitted_state: FittedPreprocessingState,
    expected_branch: ProcessedDataBranch,
    client_identity: ClientPathToken | None,
) -> None:
    if fitted_state.branch is not expected_branch:
        raise ScientificContractError("fitted-state branch mismatch", subject=fitted_state.branch)
    if expected_branch is ProcessedDataBranch.FEDERATED:
        if fitted_state.client_identity != client_identity:
            raise ScientificContractError(
                "federated fitted state client mismatch",
                subject=ContractSubject.CLIENT_IDENTITY,
            )
    elif fitted_state.client_identity is not None:
        raise ScientificContractError(
            "centralized fitted state must not carry a client identity", subject=ContractSubject.CLIENT
        )


def protocol_content_checksum(protocol: PreprocessingProtocol) -> Checksum:
    return checksum_text(protocol.model_dump_json())


def build_preprocessing_manifest(
    context: PreprocessingPublishContext,
    *,
    branch: ProcessedDataBranch,
    asset_paths: tuple[str, ...],
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
        transformed_feature_names=FeatureNameSequence(protocol.transformed_schema.feature_names.names),
        estimator_class_name=protocol.estimator_class_name,
        serialization_format=protocol.serialization_format,
        asset_paths=asset_paths,
        fit_partition=PartitionRole.TRAIN,
        execution_identity=context.execution_identity,
    )


def fitted_state_after_publish(spec: FittedStatePublishSpec) -> FittedPreprocessingState:
    return FittedPreprocessingState(
        protocol=spec.protocol,
        branch=spec.branch,
        client_identity=spec.client_identity,
        estimator_path=spec.estimator_path,
        estimator_checksum=checksum_file(spec.estimator_path),
        fit_row_count=spec.fit_row_count,
        fit_partition=PartitionRole.TRAIN,
    )


def fit_trusted_batch(
    protocol: PreprocessingProtocol,
    estimator: TrustedScaler,
    batch: PreprocessingFitBatch,
    *,
    subject: PreprocessingFitScope,
) -> TrustedScaler:
    matrix = np.asarray(batch.training_matrix, dtype=float)
    if matrix.ndim != 2:
        raise ScientificContractError(
            f"{subject.value} matrix must be two-dimensional",
            subject=subject,
        )
    if matrix.shape[0] == 0:
        raise ScientificContractError(
            f"{subject.value} matrix must contain at least one row",
            subject=subject,
        )
    if matrix.shape[0] != len(batch.training_row_ids):
        raise ScientificContractError(
            f"{subject.value} matrix and row identities must align",
            subject=PartitionRole.TRAIN,
        )
    if matrix.shape[0] != len(batch.training_labels):
        raise ScientificContractError(
            f"{subject.value} matrix and labels must align",
            subject=PartitionRole.TRAIN,
        )
    if matrix.shape[1] != len(protocol.input_feature_names):
        raise ScientificContractError(
            f"{subject.value} width must match protocol input features",
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            "training matrix contains non-finite values",
            subject=subject,
        )
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in batch.training_labels.labels):
        raise LeakageError(
            "attack-labelled rows cannot enter benign preprocessing fit",
            subject=ContractSubject.LABEL,
        )
    try:
        fitted = resolve_trusted_estimator_type(protocol.estimator_class_name)()
        fitted.fit(matrix)
        validate_finite_matrix(np.asarray(fitted.transform(matrix), dtype=float), subject)
        return fitted
    except (LeakageError, ScientificContractError):
        raise
    except Exception as error:
        raise ScientificContractError(
            f"{subject.value} estimator fitting failed: {error}",
            subject=subject,
        ) from error


def publish_preprocessed_partitions(
    *,
    context: PreprocessingPublishContext,
    branch: ProcessedDataBranch,
    coordinate_directory: Path,
    fitted_estimator: TrustedScaler,
    partitions: PreprocessingPartitionSet,
    fit_scope: PreprocessingFitScope,
    asset_paths: tuple[str, ...],
) -> ProcessedPublicationResult[PreprocessingManifest]:
    require_partitions(partitions, split_protocol=context.split_protocol_identity, subject=fit_scope)
    validate_no_partition_overlap(partitions, split_protocol=context.split_protocol_identity)
    return publish_processed(
        ProcessedPublication(
            coordinate_directory=coordinate_directory,
            manifest=build_preprocessing_manifest(context, branch=branch, asset_paths=asset_paths),
            schema=context.protocol.transformed_schema,
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
    partitions: PreprocessingPartitionSet,
    split_protocol: SplitProtocolId,
) -> PreprocessingValidationReport:
    if type(fitted_estimator) is not resolve_trusted_estimator_type(protocol.estimator_class_name):
        raise ScientificContractError(
            "fitted estimator type does not match the preprocessing protocol",
            subject=ContractSubject.FEATURES,
        )
    feature_names = protocol.input_feature_names
    transformed_names = protocol.transformed_schema.feature_names
    train_partition = partitions.require(PartitionRole.TRAIN)
    train_matrix = train_partition.frame.select(list(feature_names)).to_numpy()
    train_transformed = transform_feature_matrix(
        fitted_estimator, train_matrix, protocol.transformed_schema, PartitionRole.TRAIN
    )
    state_path = temporary / ProcessedAssetName.STATE
    serialize_estimator(fitted_estimator, state_path)
    reload_and_compare_transform(
        TransformReloadCheck(
            state_path=state_path,
            class_name=protocol.estimator_class_name,
            absolute_tolerance=protocol.numerical_equivalence_absolute_tolerance,
            source_matrix=train_matrix,
            expected_transformed=train_transformed,
        )
    )

    evidence_records: list[PartitionTransformationEvidence] = []
    for role in partition_roles(split_protocol):
        partition = partitions.require(role)
        matrix = partition.frame.select(list(feature_names)).to_numpy()
        transformed = transform_feature_matrix(fitted_estimator, matrix, protocol.transformed_schema, role)
        retained = partition.frame.drop(feature_names.as_list())
        transformed_frame = pl.from_numpy(transformed, schema=transformed_names.as_list())
        output = transformed_frame if retained.width == 0 else retained.hstack(transformed_frame)
        expected_columns = list(retained.columns) + transformed_names.as_list()
        if output.columns != expected_columns or len(frozenset(output.columns)) != len(output.columns):
            raise ScientificContractError(
                "output dataframe columns do not match expected ordering or uniqueness",
                subject=ContractSubject.SCHEMA,
            )
        output.write_parquet(temporary / asset_for_partition(role))
        evidence_records.append(
            PartitionTransformationEvidence(
                role=role,
                source_row_count=RowCount(partition.frame.height),
                output_row_count=RowCount(output.height),
            )
        )

    return PreprocessingValidationReport(
        fit_partition=PartitionRole.TRAIN,
        validated_roles=partition_roles(split_protocol),
        partition_evidence=tuple(evidence_records),
        estimator_reload_verified=True,
    )
