from pathlib import Path

import numpy as np
import polars as pl

from datp_core.artifacts.reload_validation import TransformReloadCheck, reload_and_compare_transform
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
from datp_core.domain.values import Checksum, ClientIdentity, Seed
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


def test_reload_transform_matches_pre_save_transform(tmp_path: Path) -> None:
    protocol = _protocol()
    partitions, row_ids = _partitions()
    matrix = np.asarray(partitions[PartitionRole.TRAIN].select(["f0", "f1"]).to_numpy(), dtype=float)
    estimator = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(matrix)
    expected = np.asarray(estimator.transform(matrix), dtype=float)
    result = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("e" * 64),
                data_root=tmp_path / "data",
            ),
            client_identity=ClientIdentity("device_a"),
            fitted_estimator=estimator,
            partitions=partitions,
            row_ids=row_ids,
        )
    )
    reloaded = reload_and_compare_transform(
        TransformReloadCheck(
            state_path=result.fitted_state.estimator_path,
            class_name=protocol.estimator_class_name,
            absolute_tolerance=protocol.numerical_equivalence_absolute_tolerance,
            source_matrix=matrix,
            expected_transformed=expected,
        )
    )
    assert np.allclose(np.asarray(reloaded.transform(matrix), dtype=float), expected)
