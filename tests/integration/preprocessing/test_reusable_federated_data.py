from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    PublicationStatus,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.values import Checksum, ClientPathToken, Seed
from datp_core.preprocessing.federated import ClientPublishRequest, publish_client_preprocessing
from datp_core.preprocessing.models import (
    PreprocessingProtocol,
    PreprocessingPublishContext,
    TransformedFeature,
    TransformedSchema,
)


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=("f0", "f1"),
        transformed_schema=TransformedSchema(
            features=(TransformedFeature(name="f0", position=0), TransformedFeature(name="f1", position=1))
        ),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=1e-12,
    )


def _partitions() -> tuple[dict[PartitionRole, pl.DataFrame], dict[PartitionRole, tuple[str, ...]]]:
    partitions = {
        PartitionRole.TRAIN: pl.DataFrame({"row_id": ["t0", "t1"], "f0": [0.0, 1.0], "f1": [1.0, 2.0]}),
        PartitionRole.CALIBRATION: pl.DataFrame({"row_id": ["c0"], "f0": [0.5], "f1": [1.5]}),
        PartitionRole.EVALUATION: pl.DataFrame({"row_id": ["e0"], "f0": [1.5], "f1": [2.5]}),
    }
    row_ids: dict[PartitionRole, tuple[str, ...]] = {
        PartitionRole.TRAIN: ("t0", "t1"),
        PartitionRole.CALIBRATION: ("c0",),
        PartitionRole.EVALUATION: ("e0",),
    }
    return partitions, row_ids


def _fitted_estimator(partitions: dict[PartitionRole, pl.DataFrame], feature_names: tuple[str, ...]):
    matrix = partitions[PartitionRole.TRAIN].select(list(feature_names)).to_numpy()
    return construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(matrix)


def test_identical_coordinates_reuse_completed_federated_asset(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    protocol = _protocol()
    partitions, row_ids = _partitions()
    fitted = _fitted_estimator(partitions, protocol.input_feature_names)
    first = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("c" * 64),
                data_root=data_root,
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    second = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("c" * 64),
                data_root=data_root,
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    assert first.train_path == second.train_path
    assert first.train_path.is_file()
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert (first.train_path.parent / "COMPLETE").is_file()
    assert "=" not in str(first.train_path)
    assert "client" not in first.train_path.parts
    assert "seed_0" not in first.train_path.parts
    assert "0" in first.train_path.parts
