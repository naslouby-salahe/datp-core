from pathlib import Path

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
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.data.preprocessing.federated import publish_client_preprocessing
from datp_core.data.preprocessing.models import (
    ClientPublishRequest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
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


def _publish(tmp_path: Path, seed: Seed, identity: PreprocessingProtocolId) -> Path:
    protocol = PreprocessingProtocol(
        identity=identity,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )
    partitions = _partitions()
    fitted = StandardScaler().fit(
        partitions.require(PartitionRole.TRAIN).frame.select(list(protocol.input_feature_names)).to_numpy()
    )
    result = publish_client_preprocessing(
        ClientPublishRequest(
            context=PreprocessingPublishContext(
                dataset=DatasetId.NBAIOT,
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=seed,
                split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                protocol=protocol,
                canonical_schema_checksum=Checksum("f" * 64),
                data_root=tmp_path / "data",
            ),
            client_identity=ClientPathToken("device_a"),
            fitted_estimator=fitted,
            partitions=partitions,
        )
    )
    return result.paths.train


def test_changed_seed_or_protocol_creates_distinct_asset(tmp_path: Path) -> None:
    first = _publish(tmp_path, seed=Seed(0), identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION)
    second = _publish(tmp_path, seed=Seed(1), identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION)

    assert first != second
    assert first.is_file()
    assert second.is_file()
    assert str(Seed(0).value) in first.parts
    assert str(Seed(1).value) in second.parts
