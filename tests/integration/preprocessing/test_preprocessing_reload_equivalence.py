from pathlib import Path

import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    ClientPathToken,
    DatasetId,
    FeatureName,
    FeatureNameSequence,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.core.numeric import AbsoluteTolerance, Seed
from datp_core.data.preprocessing.contracts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.data.preprocessing.federated import publish_client_preprocessing
from datp_core.data.preprocessing.models import (
    ClientPublishRequest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.data.preprocessing.state import (
    TransformReloadCheck,
    reload_and_compare_transform,
)


def _protocol(
    fit_scope: PreprocessingFitScope = PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=fit_scope,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )


def _partitions() -> PreprocessingPartitions:
    frame_train = pl.DataFrame(
        {
            "stable_row_id": ["t0", "t1"],
            "outcome_label": ["benign", "benign"],
            "f0": [0.0, 1.0],
            "f1": [1.0, 2.0],
        }
    )
    frame_cal = pl.DataFrame({"stable_row_id": ["c0"], "outcome_label": ["benign"], "f0": [0.5], "f1": [1.5]})
    frame_eval = pl.DataFrame({"stable_row_id": ["e0"], "outcome_label": ["benign"], "f0": [1.5], "f1": [2.5]})
    return PreprocessingPartitions(
        (
            PreprocessingPartition(PartitionRole.TRAIN, frame_train),
            PreprocessingPartition(PartitionRole.CALIBRATION, frame_cal),
            PreprocessingPartition(PartitionRole.EVALUATION, frame_eval),
        )
    )


def test_reload_transform_matches_pre_save_transform(tmp_path: Path) -> None:
    protocol = _protocol()
    partitions = _partitions()
    train_frame = partitions.require(PartitionRole.TRAIN).frame
    matrix = np.asarray(train_frame.select(["f0", "f1"]).to_numpy(), dtype=float)
    estimator = StandardScaler().fit(matrix)
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
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=estimator,
            partitions=partitions,
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
