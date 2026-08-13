"""Integration coverage for preprocessing publication integrity.

These tests re-establish the behaviors previously covered by the deleted
integration/preprocessing suite (atomic publication and reconstruction after
tampering, deterministic reuse of published artifacts, and pooled-vs-federated
independence) against the current API surface.
"""

from pathlib import Path

import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler

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
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, Seed
from datp_core.data.preprocessing.artifacts import (
    PreprocessingFitScope,
    ProcessedAssetName,
    TrustedEstimatorClassName,
)
from datp_core.data.preprocessing.centralized import PooledPublishRequest, publish_pooled_preprocessing
from datp_core.data.preprocessing.federated import publish_client_preprocessing
from datp_core.data.preprocessing.models import (
    ClientPublishRequest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.data.preprocessing.state import load_estimator, serialize_estimator


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
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


def _context(root: Path) -> PreprocessingPublishContext:
    return PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=_protocol(),
        data_root=root / "data",
    )


def _fitted_scaler(partitions: PreprocessingPartitions) -> StandardScaler:
    train = partitions.require(PartitionRole.TRAIN).frame
    return StandardScaler().fit(train.select(["f0", "f1"]).to_numpy())


def _assert_complete_publication(directory: Path) -> None:
    for asset in (
        ProcessedAssetName.TRAIN,
        ProcessedAssetName.CALIBRATION,
        ProcessedAssetName.EVALUATION,
        ProcessedAssetName.STATE,
        ProcessedAssetName.SCHEMA,
        ProcessedAssetName.PREPROCESSING_MANIFEST,
        ProcessedAssetName.VALIDATION_REPORT,
    ):
        assert (directory / asset.value).is_file(), f"missing published asset: {asset.value}"


def test_publication_is_atomic_and_complete(tmp_path: Path) -> None:
    partitions = _partitions()
    request = ClientPublishRequest(
        context=_context(tmp_path),
        client_identity=ClientPathToken("device_a"),
        fitted_estimator=_fitted_scaler(partitions),
        partitions=partitions,
    )

    published = publish_client_preprocessing(request)
    directory = published.paths.train.parent
    _assert_complete_publication(directory)
    assert pl.read_parquet(published.paths.train).height == 2
    assert pl.read_parquet(published.paths.calibration).height == 1
    assert pl.read_parquet(published.paths.evaluation).height == 1


def test_republish_replaces_tampered_calibration(tmp_path: Path) -> None:
    partitions = _partitions()
    request = ClientPublishRequest(
        context=_context(tmp_path),
        client_identity=ClientPathToken("device_a"),
        fitted_estimator=_fitted_scaler(partitions),
        partitions=partitions,
    )

    published = publish_client_preprocessing(request)
    calibration = pl.read_parquet(published.paths.calibration)
    tampered = calibration.with_columns((pl.col("f0") + 100.0).alias("f0"))
    tampered.write_parquet(published.paths.calibration)
    assert pl.read_parquet(published.paths.calibration).get_column("f0").to_list() == [100.0]

    repaired = publish_client_preprocessing(request)
    assert pl.read_parquet(repaired.paths.calibration).get_column("f0").to_list() == [0.0]


def test_republish_replaces_tampered_estimator(tmp_path: Path) -> None:
    protocol = _protocol()
    partitions = _partitions()
    request = ClientPublishRequest(
        context=_context(tmp_path),
        client_identity=ClientPathToken("device_a"),
        fitted_estimator=_fitted_scaler(partitions),
        partitions=partitions,
    )

    published = publish_client_preprocessing(request)
    state_path = published.fitted_state.estimator_path
    serialize_estimator(StandardScaler().fit(np.asarray([[100.0, 101.0], [102.0, 103.0]])), state_path)
    tampered_estimator = load_estimator(state_path, protocol.estimator_class_name)
    assert isinstance(tampered_estimator, StandardScaler)
    assert tampered_estimator.transform(np.asarray([[0.5, 1.5]])).tolist() != [[0.0, 0.0]]

    repaired = publish_client_preprocessing(request)
    repaired_estimator = load_estimator(
        repaired.fitted_state.estimator_path,
        protocol.estimator_class_name,
    )
    assert isinstance(repaired_estimator, StandardScaler)
    assert repaired_estimator.transform(np.asarray([[0.5, 1.5]])).tolist() == [[0.0, 0.0]]


def test_pooled_publication_is_independent_and_reusable(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )
    partitions = _partitions()
    context = PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=protocol,
        data_root=tmp_path / "data",
    )
    request = PooledPublishRequest(
        context=context,
        fitted_estimator=_fitted_scaler(partitions),
        partitions=partitions,
    )

    published = publish_pooled_preprocessing(request)
    directory = published.paths.train.parent
    _assert_complete_publication(directory)
    reused = publish_pooled_preprocessing(request)
    assert reused.paths.train.parent == published.paths.train.parent
    assert pl.read_parquet(reused.paths.calibration).height == 1
