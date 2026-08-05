from pathlib import Path

import polars as pl

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
)
from datp_core.domain.values import (
    AbsoluteTolerance,
    Checksum,
    ClientPathToken,
    FeatureName,
    FeatureNameSequence,
    Seed,
)
from datp_core.preprocessing.federated import publish_client_preprocessing
from datp_core.preprocessing.models import (
    ClientPublishRequest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.preprocessing.state import construct_trusted_estimator


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
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


def _fitted_estimator(partitions: PreprocessingPartitions, feature_names: tuple[str, ...]):
    matrix = partitions.require(PartitionRole.TRAIN).frame.select(list(feature_names)).to_numpy()
    return construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER).fit(matrix)


def test_identical_coordinates_reuse_completed_federated_asset(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    protocol = _protocol()
    partitions = _partitions()
    fitted = _fitted_estimator(partitions, protocol.input_feature_names.names)
    context = PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=protocol,
        canonical_schema_checksum=Checksum("c" * 64),
        data_root=data_root,
    )
    request = ClientPublishRequest(
        context=context,
        client_identity=ClientPathToken("device_a"),
        fitted_estimator=fitted,
        partitions=partitions,
    )

    first = publish_client_preprocessing(request)
    second = publish_client_preprocessing(request)

    assert first.paths.train == second.paths.train
    assert first.paths.train.is_file()
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert (first.paths.train.parent / "COMPLETE").is_file()
    assert "=" not in str(first.paths.train)
    assert "client" not in first.paths.train.parts
    assert "seed_0" not in first.paths.train.parts
    assert "0" in first.paths.train.parts
