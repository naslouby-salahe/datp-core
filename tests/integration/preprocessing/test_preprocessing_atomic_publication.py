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
)
from datp_core.domain.values import AbsoluteTolerance, Checksum, ClientPathToken, FeatureNameSequence, Seed
from datp_core.preprocessing.federated import ClientPublishRequest, publish_client_preprocessing
from datp_core.preprocessing.models import (
    PreprocessingPartition,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)


def test_partial_asset_is_rebuilt_after_cleanup(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence(("f0", "f1")),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )
    frame_train = pl.DataFrame(
        {"stable_row_id": ["t0", "t1"], "outcome_label": ["benign", "benign"], "f0": [0.0, 1.0], "f1": [1.0, 2.0]}
    )
    frame_cal = pl.DataFrame({"stable_row_id": ["c0"], "outcome_label": ["benign"], "f0": [0.5], "f1": [1.5]})
    frame_eval = pl.DataFrame({"stable_row_id": ["e0"], "outcome_label": ["benign"], "f0": [1.5], "f1": [2.5]})
    partitions = PreprocessingPartitionSet(
        partitions=(
            PreprocessingPartition(PartitionRole.TRAIN, frame_train),
            PreprocessingPartition(PartitionRole.CALIBRATION, frame_cal),
            PreprocessingPartition(PartitionRole.EVALUATION, frame_eval),
        )
    )
    fitted = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(
        frame_train.select(list(protocol.input_feature_names)).to_numpy()
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
        )
    )
    (first.paths.train.parent / ProcessedAssetName.COMPLETE).unlink()
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
        )
    )
    assert rebuilt.paths.train.parent == first.paths.train.parent
    assert (rebuilt.paths.train.parent / ProcessedAssetName.COMPLETE).is_file()
