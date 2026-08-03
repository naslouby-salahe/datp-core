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
)
from datp_core.domain.values import AbsoluteTolerance, Checksum, ClientPathToken, FeatureName, FeatureNameSequence, Seed
from datp_core.preprocessing.federated import ClientPublishRequest, publish_client_preprocessing
from datp_core.preprocessing.models import (
    PreprocessingPartition,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)


def _protocol(fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=fit_scope,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )


def _partitions() -> PreprocessingPartitionSet:
    frame_train = pl.DataFrame(
        {"stable_row_id": ["t0", "t1"], "outcome_label": ["benign", "benign"], "f0": [0.0, 1.0], "f1": [1.0, 2.0]}
    )
    frame_cal = pl.DataFrame({"stable_row_id": ["c0"], "outcome_label": ["benign"], "f0": [0.5], "f1": [1.5]})
    frame_eval = pl.DataFrame({"stable_row_id": ["e0"], "outcome_label": ["benign"], "f0": [1.5], "f1": [2.5]})
    return PreprocessingPartitionSet(
        partitions=(
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
    fitted = construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(
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
    assert first.is_file() and second.is_file()
    assert str(Seed(0).value) in first.parts
    assert str(Seed(1).value) in second.parts
