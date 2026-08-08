"""Typed persistence and reload of fitted preprocessing states and transformed partitions."""

from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl
from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.artifacts.serializers.parquet import read_frame, write_frame
from datp_core.artifacts.serializers.skops import dump_scaler, load_scaler
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import (
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    PartitionRole,
    PreprocessingProtocolId,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.core.numeric import RowCount
from datp_core.data.populations.contracts import ClientIdentity, PopulationFrameColumn
from datp_core.data.preprocessing.contracts import (
    ClientPreprocessingResult,
    FittedPreprocessingState,
    PreprocessingFitScope,
    PreprocessingProtocol,
    ScalerFamily,
    TransformedPartition,
)
from datp_core.data.preprocessing.validation import validate_fitted_state, validate_serialization_equivalence


class PreprocessingAsset(StrEnum):
    STATE = "state.skops"
    MANIFEST = "manifest.json"
    COMPLETE = "COMPLETE"


class PartitionAsset(StrEnum):
    TRAIN = "train.parquet"
    CALIBRATION = "calibration.parquet"
    EVALUATION = "evaluation.parquet"
    FUTURE_RECALIBRATION = "future_recalibration.parquet"
    STATIC_REFERENCE_RESERVE = "static_reference_reserve.parquet"

    @classmethod
    def for_role(cls, role: PartitionRole) -> "PartitionAsset":
        return cls(role.value + ".parquet")


class PersistedPartition(StrictModel):
    role: PartitionRole
    asset: PartitionAsset
    checksum: Checksum
    row_count: RowCount

    @model_validator(mode="after")
    def validate_asset(self) -> "PersistedPartition":
        if self.asset is not PartitionAsset.for_role(self.role):
            raise ValueError("persisted preprocessing partition asset must match its role")
        return self


class PreprocessingManifest(StrictModel):
    client: ClientIdentity
    protocol_identity: PreprocessingProtocolId
    feature_names: FeatureNameSequence
    fit_scope: PreprocessingFitScope
    scaler_family: ScalerFamily
    fit_row_count: RowCount
    fit_row_checksum: Checksum
    estimator_checksum: Checksum
    partitions: tuple[PersistedPartition, ...]

    @model_validator(mode="after")
    def validate_partitions(self) -> "PreprocessingManifest":
        if not self.partitions:
            raise ValueError("preprocessing manifest requires persisted partitions")
        roles = tuple(item.role for item in self.partitions)
        if len(frozenset(roles)) != len(roles):
            raise ValueError("preprocessing manifest partitions must be unique by role")
        return self


class PreprocessingPublication(StrictModel):
    directory: Path
    manifest: PreprocessingManifest
    complete_digest: Checksum


def publish_client_preprocessing(
    result: ClientPreprocessingResult,
    directory: Path,
    *,
    overwrite: bool,
) -> PreprocessingPublication:
    if directory.exists() and not overwrite:
        return load_client_preprocessing_publication(directory)
    if directory.exists():
        from shutil import rmtree

        rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)

    validate_fitted_state(result.state)
    state_path = directory / PreprocessingAsset.STATE.value
    estimator_checksum = dump_scaler(result.state.estimator, state_path)
    probe = np.zeros((1, len(result.state.protocol.feature_names)), dtype=np.float64)
    reloaded = load_scaler(state_path, expected_checksum=estimator_checksum)
    validate_serialization_equivalence(result.state.estimator, reloaded, probe)

    persisted = tuple(_persist_partition(partition, directory) for partition in result.partitions)
    manifest = PreprocessingManifest(
        client=result.client,
        protocol_identity=result.state.protocol.identity,
        feature_names=result.state.protocol.feature_names,
        fit_scope=result.state.protocol.fit_scope,
        scaler_family=result.state.protocol.scaler_family,
        fit_row_count=result.state.fit_row_count,
        fit_row_checksum=result.state.fit_row_checksum,
        estimator_checksum=estimator_checksum,
        partitions=persisted,
    )
    manifest_path = directory / PreprocessingAsset.MANIFEST.value
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")
    complete_digest = checksum_file(manifest_path)
    (directory / PreprocessingAsset.COMPLETE.value).write_text(complete_digest.value, encoding="utf-8")
    return PreprocessingPublication(directory=directory, manifest=manifest, complete_digest=complete_digest)


def load_client_preprocessing_publication(directory: Path) -> PreprocessingPublication:
    manifest_path = directory / PreprocessingAsset.MANIFEST.value
    complete_path = directory / PreprocessingAsset.COMPLETE.value
    if not manifest_path.is_file() or not complete_path.is_file():
        raise ArtifactIntegrityError(f"preprocessing publication is incomplete: {directory}")
    manifest = PreprocessingManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    digest = checksum_file(manifest_path)
    if complete_path.read_text(encoding="utf-8").strip() != digest.value:
        raise ArtifactIntegrityError(f"preprocessing completion digest mismatch: {directory}")
    load_scaler(directory / PreprocessingAsset.STATE.value, expected_checksum=manifest.estimator_checksum)
    for partition in manifest.partitions:
        read_frame(
            directory / partition.asset.value,
            expected_checksum=partition.checksum,
            expected_row_count=partition.row_count,
        )
    return PreprocessingPublication(directory=directory, manifest=manifest, complete_digest=digest)


def reload_client_preprocessing(publication: PreprocessingPublication) -> ClientPreprocessingResult:
    manifest = publication.manifest
    protocol = PreprocessingProtocol(
        identity=manifest.protocol_identity,
        feature_names=manifest.feature_names,
        fit_scope=manifest.fit_scope,
        scaler_family=manifest.scaler_family,
    )
    estimator = load_scaler(
        publication.directory / PreprocessingAsset.STATE.value,
        expected_checksum=manifest.estimator_checksum,
    )
    state = FittedPreprocessingState(
        protocol=protocol,
        estimator=estimator,
        fit_row_count=manifest.fit_row_count,
        fit_row_checksum=manifest.fit_row_checksum,
        owner=manifest.client if manifest.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING else None,
    )
    partitions = tuple(
        _reload_partition(item, publication.directory, manifest.feature_names) for item in manifest.partitions
    )
    return ClientPreprocessingResult(client=manifest.client, state=state, partitions=partitions)


def _persist_partition(partition: TransformedPartition, directory: Path) -> PersistedPartition:
    identity = pl.DataFrame(
        {
            PopulationFrameColumn.STABLE_ROW_ID.value: tuple(str(item) for item in partition.row_ids),
            PopulationFrameColumn.OUTCOME_LABEL.value: tuple(str(item) for item in partition.outcome_labels),
        }
    )
    payload = pl.concat((identity, partition.frame), how="horizontal")
    asset = PartitionAsset.for_role(partition.role)
    checksum, row_count = write_frame(payload, directory / asset.value)
    return PersistedPartition(role=partition.role, asset=asset, checksum=checksum, row_count=row_count)


def _reload_partition(
    persisted: PersistedPartition,
    directory: Path,
    feature_names: FeatureNameSequence,
) -> TransformedPartition:
    payload = read_frame(
        directory / persisted.asset.value,
        expected_checksum=persisted.checksum,
        expected_row_count=persisted.row_count,
    )
    row_ids = StableRowIdSequence(
        tuple(
            StableRowId(value)
            for value in payload.get_column(PopulationFrameColumn.STABLE_ROW_ID.value).cast(pl.String)
        )
    )
    labels = OutcomeLabelSequence(
        tuple(
            OutcomeLabel(value)
            for value in payload.get_column(PopulationFrameColumn.OUTCOME_LABEL.value).cast(pl.String)
        )
    )
    frame = payload.select(tuple(feature_names))
    return TransformedPartition(
        role=persisted.role,
        frame=frame,
        row_ids=row_ids,
        outcome_labels=labels,
    )
