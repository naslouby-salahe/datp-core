"""Scientific leakage and schema validation for preprocessing."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.artifacts.layout import ProcessedAssetName, asset_for_partition, core_processed_asset_names
from datp_core.artifacts.serialization import (
    TrustedScaler,
    clone_trusted_scaler,
    resolve_trusted_estimator_type,
    serialize_estimator,
)
from datp_core.artifacts.store import ProcessedPublication, ProcessedPublicationResult, publish_processed
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PreprocessingFitScope,
    ProcessedDataBranch,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import Checksum, ClientIdentity, OutcomeLabelSequence, checksum_file, checksum_text
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    FittedStatePublishSpec,
    PreprocessingFitBatch,
    PreprocessingManifest,
    PreprocessingProtocol,
    PreprocessingPublishContext,
    PreprocessingValidationReport,
    TransformedSchema,
)

_CORE_PARTITION_ROLES = (
    PartitionRole.TRAIN,
    PartitionRole.CALIBRATION,
    PartitionRole.EVALUATION,
)


def core_partition_roles() -> tuple[PartitionRole, ...]:
    return _CORE_PARTITION_ROLES


def require_core_partitions(
    partitions: Mapping[PartitionRole, pl.DataFrame],
    row_ids: Mapping[PartitionRole, Sequence[str]],
    *,
    subject: PreprocessingFitScope,
) -> None:
    for role in _CORE_PARTITION_ROLES:
        if role not in partitions or role not in row_ids:
            raise ScientificContractError(
                f"{subject.value} missing preprocessing partition {role.value}",
                subject=role,
            )


def validate_train_only_fit(fit_partition: PartitionRole) -> None:
    if fit_partition is not PartitionRole.TRAIN:
        raise LeakageError("preprocessing may fit only on training rows", subject=fit_partition)


def validate_no_partition_overlap(
    train_ids: Sequence[str],
    calibration_ids: Sequence[str],
    evaluation_ids: Sequence[str],
    future_ids: Sequence[str] = (),
) -> None:
    groups = (
        (PartitionRole.TRAIN, frozenset(train_ids)),
        (PartitionRole.CALIBRATION, frozenset(calibration_ids)),
        (PartitionRole.EVALUATION, frozenset(evaluation_ids)),
        (PartitionRole.FUTURE_RECALIBRATION, frozenset(future_ids)),
    )
    for left_role, left_ids in groups:
        for right_role, right_ids in groups:
            if left_role.value >= right_role.value:
                continue
            overlap = left_ids & right_ids
            if overlap:
                raise LeakageError(
                    f"source-row overlap between {left_role.value} and {right_role.value}: "
                    f"{next(iter(sorted(overlap)))}",
                    subject=left_role,
                )


def validate_finite_matrix(matrix: np.ndarray, subject: PartitionRole | ContractSubject) -> None:
    if not np.isfinite(matrix).all():
        raise ScientificContractError("transformed values must be finite", subject=subject)


def transform_feature_matrix(
    fitted_estimator: TrustedScaler,
    matrix: np.ndarray,
    subject: PartitionRole,
) -> np.ndarray:
    transformed = np.asarray(fitted_estimator.transform(matrix), dtype=float)
    validate_finite_matrix(transformed, subject)
    return transformed


def validate_transformed_schema(protocol: PreprocessingProtocol, schema: TransformedSchema) -> None:
    if schema != protocol.transformed_schema:
        raise ScientificContractError(
            "transformed schema does not match the preprocessing protocol", subject=ContractSubject.SCHEMA
        )


def validate_branch_isolation(
    fitted_state: FittedPreprocessingState,
    expected_branch: ProcessedDataBranch,
    client_identity: ClientIdentity | None,
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


def validate_no_attack_labels_in_fit(labels: OutcomeLabelSequence, benign_label: str) -> None:
    if any(label != benign_label for label in labels):
        raise LeakageError("attack-labelled rows cannot enter benign preprocessing fit", subject=ContractSubject.LABEL)


def successful_preprocessing_validation_report() -> PreprocessingValidationReport:
    return PreprocessingValidationReport(
        finite_transformed_values=True,
        train_only_fit=True,
        no_partition_overlap=True,
        schema_matches_protocol=True,
        branch_isolation=True,
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
        transformed_feature_names=protocol.transformed_schema.feature_names,
        estimator_class=protocol.qualified_estimator_name,
        serialization_format=protocol.serialization_format,
        asset_paths=asset_paths,
        fit_partition=PartitionRole.TRAIN,
    )


def fitted_state_after_publish(spec: FittedStatePublishSpec) -> FittedPreprocessingState:
    return FittedPreprocessingState(
        protocol=spec.protocol,
        branch=spec.branch,
        client_identity=spec.client_identity,
        estimator_path=spec.estimator_path,
        estimator_checksum=checksum_file(spec.estimator_path),
        transformed_schema=spec.protocol.transformed_schema,
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
    validate_train_only_fit(PartitionRole.TRAIN)
    validate_no_attack_labels_in_fit(batch.training_labels, batch.benign_label)
    matrix = np.asarray(batch.training_matrix, dtype=float)
    if matrix.shape[0] != len(batch.training_row_ids):
        raise ScientificContractError(
            f"{subject.value} matrix and row identities must align",
            subject=PartitionRole.TRAIN,
        )
    if matrix.shape[1] != len(protocol.input_feature_names):
        raise ScientificContractError(
            f"{subject.value} width must match protocol input features",
            subject=ContractSubject.FEATURES,
        )
    fitted = clone_trusted_scaler(estimator, protocol.estimator_class_name)
    fitted.fit(matrix)
    validate_finite_matrix(np.asarray(fitted.transform(matrix), dtype=float), PartitionRole.TRAIN)
    return fitted


def publication_target(data_root: Path, relative_coordinate: Path) -> Path:
    return data_root.joinpath(*relative_coordinate.parts[1:])


def publish_preprocessed_partitions(
    *,
    context: PreprocessingPublishContext,
    branch: ProcessedDataBranch,
    relative_coordinate: Path,
    fitted_estimator: TrustedScaler,
    partitions: Mapping[PartitionRole, pl.DataFrame],
    row_ids: Mapping[PartitionRole, Sequence[str]],
    fit_scope: PreprocessingFitScope,
    asset_paths: tuple[str, ...],
) -> ProcessedPublicationResult[PreprocessingManifest]:
    validate_train_only_fit(PartitionRole.TRAIN)
    require_core_partitions(partitions, row_ids, subject=fit_scope)
    validate_no_partition_overlap(
        row_ids[PartitionRole.TRAIN],
        row_ids[PartitionRole.CALIBRATION],
        row_ids[PartitionRole.EVALUATION],
    )
    validate_transformed_schema(context.protocol, context.protocol.transformed_schema)
    return publish_processed(
        ProcessedPublication(
            coordinate_directory=publication_target(context.data_root, relative_coordinate),
            manifest=build_preprocessing_manifest(context, branch=branch, asset_paths=asset_paths),
            schema=context.protocol.transformed_schema,
            validation_report=successful_preprocessing_validation_report(),
            writer=lambda temporary: write_fitted_transformed_partitions(
                temporary,
                protocol=context.protocol,
                fitted_estimator=fitted_estimator,
                partitions=partitions,
            ),
            required_assets=core_processed_assets(),
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
    partitions: Mapping[PartitionRole, pl.DataFrame],
) -> None:
    if type(fitted_estimator) is not resolve_trusted_estimator_type(protocol.estimator_class_name):
        raise ScientificContractError(
            "fitted estimator type does not match the preprocessing protocol",
            subject=ContractSubject.FEATURES,
        )
    feature_names = protocol.input_feature_names
    transformed_names = protocol.transformed_schema.feature_names
    train_matrix = partitions[PartitionRole.TRAIN].select(feature_names).to_numpy()
    validate_finite_matrix(
        transform_feature_matrix(fitted_estimator, train_matrix, PartitionRole.TRAIN),
        PartitionRole.TRAIN,
    )
    serialize_estimator(fitted_estimator, temporary / ProcessedAssetName.STATE)
    for role in _CORE_PARTITION_ROLES:
        matrix = partitions[role].select(feature_names).to_numpy()
        transformed = transform_feature_matrix(fitted_estimator, matrix, role)
        retained = partitions[role].select(
            [column for column in partitions[role].columns if column not in feature_names]
        )
        transformed_frame = pl.DataFrame({name: transformed[:, index] for index, name in enumerate(transformed_names)})
        if retained.width == 0:
            output = transformed_frame
        else:
            output = pl.concat([retained, transformed_frame], how="horizontal_extend")
        output.write_parquet(temporary / asset_for_partition(role))


def core_processed_assets() -> tuple[ProcessedAssetName, ...]:
    return core_processed_asset_names()
