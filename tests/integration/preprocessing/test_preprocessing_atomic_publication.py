from pathlib import Path

import polars as pl

from datp_core.artifacts.layout import ProcessedAssetName
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


def test_partial_asset_is_rebuilt_after_cleanup(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
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
    fitted = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(
        partitions[PartitionRole.TRAIN].select(list(protocol.input_feature_names)).to_numpy()
    )
    first = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("a" * 64),
                data_root=tmp_path / "data",
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    (first.train_path.parent / ProcessedAssetName.COMPLETE).unlink()
    rebuilt = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("a" * 64),
                data_root=tmp_path / "data",
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    assert rebuilt.train_path.parent == first.train_path.parent
    assert (rebuilt.train_path.parent / ProcessedAssetName.COMPLETE).is_file()
