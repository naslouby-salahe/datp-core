from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
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


def _protocol(fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=fit_scope,
        input_feature_names=("f0", "f1"),
        transformed_schema=TransformedSchema(
            features=(TransformedFeature(name="f0", position=0), TransformedFeature(name="f1", position=1))
        ),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=1e-12,
    )


def _partitions():
    partitions = {
        PartitionRole.TRAIN: pl.DataFrame({"row_id": ["t0", "t1"], "f0": [0.0, 1.0], "f1": [1.0, 2.0]}),
        PartitionRole.CALIBRATION: pl.DataFrame({"row_id": ["c0"], "f0": [0.5], "f1": [1.5]}),
        PartitionRole.EVALUATION: pl.DataFrame({"row_id": ["e0"], "f0": [1.5], "f1": [2.5]}),
    }
    row_ids = {
        PartitionRole.TRAIN: ("t0", "t1"),
        PartitionRole.CALIBRATION: ("c0",),
        PartitionRole.EVALUATION: ("e0",),
    }
    return partitions, row_ids


def _publish(tmp_path: Path, seed: int, identity: PreprocessingProtocolId) -> Path:
    protocol = PreprocessingProtocol(
        identity=identity,
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
    partitions, row_ids = _partitions()
    fitted = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(
        partitions[PartitionRole.TRAIN].select(list(protocol.input_feature_names)).to_numpy()
    )
    result = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(seed),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("f" * 64),
                data_root=tmp_path / "data",
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    return result.train_path


def test_changed_seed_or_protocol_creates_distinct_asset(tmp_path: Path) -> None:
    first = _publish(tmp_path, seed=0, identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION)
    second = _publish(tmp_path, seed=1, identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION)
    # only one scientific-test protocol id exists; distinct seed is enough
    assert first != second
    assert first.is_file() and second.is_file()
    assert str(Seed(0).value) in first.parts
    assert str(Seed(1).value) in second.parts
