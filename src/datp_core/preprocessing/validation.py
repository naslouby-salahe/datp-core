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
    CentralizedFittedPreprocessingState,
    CentralizedFittedStatePublishSpec,
    FederatedFittedPreprocessingState,
    FederatedFittedStatePublishSpec,
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


def require_columns(
    frame: pl.DataFrame,
    columns: Iterable[str],
    *,
    subject: ContractSubject | PartitionRole | PreprocessingFitScope | SplitProtocolId,
) -> None:
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise ScientificContractError(
            f"missing required column(s): {', '.join(missing)}",
            subject=subject,
        )


def require_partitions(
    partitions: PreprocessingPartitionSet,
    *,
    split_protocol: SplitProtocolId,
    subject: PreprocessingFitScope,
) -> None:
    required = partition_roles(split_protocol)
    if partitions.roles() != required:
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
    require_columns(
        frame,
        [PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names],
        subject=ContractSubject.SCHEMA,
    )
    normalized = frame.with_columns(pl.col(PARTITION_ROLE_COLUMN).cast(pl.String))
    role_series = normalized.get_column(PARTITION_ROLE_COLUMN)
    if role_series.null_count() > 0:
        raise ScientificContractError(
            "partition role column contains null values",
            subject=ContractSubject.SCHEMA,
        )
    expected_roles = partition_roles(split_protocol)
    expected_role_strs = {r.value for r in expected_roles}
    actual_role_strs = set(role_series.unique().to_list())
    if actual_role_strs != expected_role_strs:
        raise ScientificContractError(
            f"extracted roles {actual_role_strs} do not match expected roles {expected_role_strs} "
            f"for {split_protocol.value}",
            subject=ContractSubject.SCHEMA,
        )

    extracted: list[PreprocessingPartition] = []
    keep = [STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN, *feature_names.names]
    for role in expected_roles:
        role_frame = normalized.filter(pl.col(PARTITION_ROLE_COLUMN) == role.value).select(keep)
        if ordering is PartitionOrdering.STABLE_ROW_ID:
            role_frame = role_frame.sort([STABLE_ROW_ID_COLUMN])
        if role_frame.height == 0:
            raise ScientificContractError(
                f"{branch.value} partition {role.value} is empty",
                subject=role,
            )
        extracted.append(PreprocessingPartition(role=role, frame=role_frame))
    partition_set = PreprocessingPartitionSet(partitions=tuple(extracted))
    total_extracted = sum(p.frame.height for p in partition_set.partitions)
    if total_extracted != normalized.height:
        raise ScientificContractError(
            f"extracted row count ({total_extracted}) does not match source frame row count ({normalized.height})",
            subject=ContractSubject.ROWS,
        )
    return partition_set


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
            first_overlap = min(str(row_id) for row_id in overlap)
            raise LeakageError(
                f"source-row overlap between {left_role.value} and {right_role.value}: {first_overlap}",
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
    if transformed.ndim != 2:
        raise ScientificContractError("transformed matrix must be two-dimensional", subject=subject)
    if transformed.shape[0] != matrix.shape[0]:
        raise ScientificContractError("transformed row count must match input matrix", subject=subject)
    if transformed.shape[1] != len(feature_names):
        raise ScientificContractError("transformed matrix width must match schema", subject=subject)
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
    spec: CentralizedFittedStatePublishSpec,
) -> CentralizedFittedPreprocessingState:
    checksum = checksum_file(spec.estimator_path)
    return CentralizedFittedPreprocessingState(
        protocol=spec.protocol,
        estimator_path=spec.estimator_path,
        estimator_checksum=checksum,
        fit_row_count=spec.fit_row_count,
    )


def federated_fitted_state_after_publish(
    spec: FederatedFittedStatePublishSpec,
) -> FederatedFittedPreprocessingState:
    checksum = checksum_file(spec.estimator_path)
    return FederatedFittedPreprocessingState(
        protocol=spec.protocol,
        client_identity=spec.client_identity,
        estimator_path=spec.estimator_path,
        estimator_checksum=checksum,
        fit_row_count=spec.fit_row_count,
    )


def fit_trusted_batch(
    protocol: PreprocessingProtocol,
    batch: PreprocessingFitBatch,
    *,
    subject: PreprocessingFitScope,
) -> TrustedScaler:
    if subject is not protocol.fit_scope:
        raise ScientificContractError(
            f"subject {subject.value} does not match protocol fit scope {protocol.fit_scope.value}",
            subject=subject,
        )
    try:
        matrix = np.asarray(batch.training_matrix, dtype=float)
    except Exception as error:
        raise ScientificContractError(
            "training matrix must contain numeric values",
            subject=subject,
        ) from error
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
    require_finite_matrix(matrix, subject=subject, description="training matrix")
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in batch.training_labels.labels):
        raise LeakageError(
            "attack-labelled rows cannot enter benign preprocessing fit",
            subject=ContractSubject.LABEL,
        )
    try:
        fitted = resolve_trusted_estimator_type(protocol.estimator_class_name)()
        fitted.fit(matrix)
        transform_feature_matrix(
            fitted,
            matrix,
            protocol.input_feature_names,
            subject,
            description=f"{subject.value} training matrix round-trip transform",
        )
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
    asset_paths: RelativeAssetPathSequence,
) -> ProcessedPublicationResult[PreprocessingManifest]:
    fit_scope = context.protocol.fit_scope
    require_partitions(partitions, split_protocol=context.split_protocol_identity, subject=fit_scope)
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
    partitions: PreprocessingPartitionSet,
    split_protocol: SplitProtocolId,
) -> PreprocessingValidationReport:
    if type(fitted_estimator) is not resolve_trusted_estimator_type(protocol.estimator_class_name):
        raise ScientificContractError(
            "fitted estimator type does not match the preprocessing protocol",
            subject=ContractSubject.FEATURES,
        )
    feature_names = protocol.input_feature_names
    train_partition = partitions.require(PartitionRole.TRAIN)
    require_columns(train_partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
    train_matrix = train_partition.frame.select(list(feature_names)).to_numpy()
    train_transformed = transform_feature_matrix(
        fitted_estimator,
        train_matrix,
        feature_names,
        PartitionRole.TRAIN,
        description="client-local transformed training matrix",
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
        require_columns(partition.frame, feature_names.names, subject=ContractSubject.SCHEMA)
        if role is PartitionRole.TRAIN:
            transformed = train_transformed
        else:
            matrix = partition.frame.select(list(feature_names)).to_numpy()
            description = _transform_description_for_role(role)
            transformed = transform_feature_matrix(
                fitted_estimator,
                matrix,
                feature_names,
                role,
                description=description,
            )
        retained = partition.frame.drop(feature_names.as_list())
        transformed_frame = pl.from_numpy(transformed, schema=feature_names.as_list())
        output = transformed_frame if retained.width == 0 else retained.hstack(transformed_frame)
        expected_columns = list(retained.columns) + feature_names.as_list()
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
        partition_evidence=tuple(evidence_records),
    )


def _transform_description_for_role(role: PartitionRole) -> str:
    match role:
        case PartitionRole.TRAIN:
            return "transformed train matrix"
        case PartitionRole.CALIBRATION:
            return "transformed calibration matrix"
        case PartitionRole.EVALUATION:
            return "transformed evaluation matrix"
        case PartitionRole.FUTURE_RECALIBRATION:
            return "transformed future recalibration matrix"
        case PartitionRole.STATIC_REFERENCE_RESERVE:
            return "transformed static reference reserve matrix"
