from pathlib import Path

import polars as pl

from datp_core.artifacts.serialization import construct_trusted_estimator
from datp_core.centralized_reference.preprocessing import PooledPublishRequest, publish_pooled_preprocessing
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
from datp_core.domain.values import Checksum, FeatureNameSequence, Seed
from datp_core.preprocessing.models import (
    PreprocessingProtocol,
    PreprocessingPublishContext,
    TransformedFeature,
    TransformedSchema,
)


def test_centralized_publication_is_independent_and_reusable(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FeatureNameSequence(("f0", "f1")),
        transformed_schema=TransformedSchema(
            features=(TransformedFeature(name="f0", position=0), TransformedFeature(name="f1", position=1))
        ),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=1e-12,
    )
    partitions = {
        PartitionRole.TRAIN: pl.DataFrame({"row_id": ["t0", "t1"], "f0": [0.0, 2.0], "f1": [1.0, 3.0]}),
        PartitionRole.CALIBRATION: pl.DataFrame({"row_id": ["c0"], "f0": [1.0], "f1": [2.0]}),
        PartitionRole.EVALUATION: pl.DataFrame({"row_id": ["e0"], "f0": [3.0], "f1": [4.0]}),
    }
    row_ids: dict[PartitionRole, tuple[str, ...]] = {
        PartitionRole.TRAIN: ("t0", "t1"),
        PartitionRole.CALIBRATION: ("c0",),
        PartitionRole.EVALUATION: ("e0",),
    }
    data_root = tmp_path / "data"
    fitted = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(
        partitions[PartitionRole.TRAIN].select(list(protocol.input_feature_names)).to_numpy()
    )
    first = publish_pooled_preprocessing(
        PooledPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("d" * 64),
                data_root=data_root,
            ),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    second = publish_pooled_preprocessing(
        PooledPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("d" * 64),
                data_root=data_root,
            ),
            fitted_estimator=fitted,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    assert first.fitted_state.client_identity is None
    assert first.train_path == second.train_path
    assert "centralized_reference" in first.train_path.parts
