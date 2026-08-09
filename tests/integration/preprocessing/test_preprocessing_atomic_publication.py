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
    PublicationStatus,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.core.numeric import AbsoluteTolerance, Seed
from datp_core.data.preprocessing.artifacts import (
    PreprocessingFitScope,
    ProcessedAssetName,
    TrustedEstimatorClassName,
)
from datp_core.data.preprocessing.federated import publish_client_preprocessing
from datp_core.data.preprocessing.models import (
    ClientPublishRequest,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)
from datp_core.data.preprocessing.state import load_estimator, serialize_estimator


def test_partial_asset_is_rebuilt_after_cleanup(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )
    frame_train = pl.DataFrame(
        {
            "stable_row_id": ["t0", "t1"],
            "outcome_label": ["benign", "benign"],
            "f0": [0.0, 1.0],
            "f1": [1.0, 2.0],
        }
    )
    frame_cal = pl.DataFrame(
        {
            "stable_row_id": ["c0"],
            "outcome_label": ["benign"],
            "f0": [0.5],
            "f1": [1.5],
        }
    )
    frame_eval = pl.DataFrame(
        {
            "stable_row_id": ["e0"],
            "outcome_label": ["benign"],
            "f0": [1.5],
            "f1": [2.5],
        }
    )
    partitions = PreprocessingPartitions(
        (
            PreprocessingPartition(PartitionRole.TRAIN, frame_train),
            PreprocessingPartition(PartitionRole.CALIBRATION, frame_cal),
            PreprocessingPartition(PartitionRole.EVALUATION, frame_eval),
        )
    )
    fitted = StandardScaler().fit(frame_train.select(list(protocol.input_feature_names)).to_numpy())
    context = PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=protocol,
        canonical_schema_checksum=Checksum("a" * 64),
        data_root=tmp_path / "data",
    )
    request = ClientPublishRequest(
        context=context,
        client_identity=ClientPathToken("device_a"),
        fitted_estimator=fitted,
        partitions=partitions,
    )

    first = publish_client_preprocessing(request)
    (first.paths.train.parent / ProcessedAssetName.COMPLETE).unlink()
    rebuilt = publish_client_preprocessing(request)

    assert rebuilt.paths.train.parent == first.paths.train.parent
    assert (rebuilt.paths.train.parent / ProcessedAssetName.COMPLETE).is_file()

    # Exercise persisted scientific content, not just its schema/manifest: this
    # is an actual transformed calibration row with stable-row provenance.
    calibration = pl.read_parquet(rebuilt.paths.calibration)
    tampered_calibration = calibration.with_columns((pl.col("f0") + 100.0).alias("f0"))
    tampered_calibration.write_parquet(rebuilt.paths.calibration)
    assert pl.read_parquet(rebuilt.paths.calibration).get_column("f0").to_list() == [100.0]

    repaired_partitions = publish_client_preprocessing(request)
    assert repaired_partitions.publication_status is PublicationStatus.PUBLISHED
    assert pl.read_parquet(repaired_partitions.paths.calibration).get_column("f0").to_list() == [0.0]

    # A valid-but-different skops payload must also be rejected; merely being
    # parseable is insufficient for scientific preprocessing reuse.
    state_path = repaired_partitions.fitted_state.estimator_path
    serialize_estimator(StandardScaler().fit(np.asarray([[100.0, 101.0], [102.0, 103.0]])), state_path)
    tampered_estimator = load_estimator(state_path, protocol.estimator_class_name)
    assert isinstance(tampered_estimator, StandardScaler)
    assert tampered_estimator.transform(np.asarray([[0.5, 1.5]])).tolist() != [[0.0, 0.0]]

    repaired_state = publish_client_preprocessing(request)
    assert repaired_state.publication_status is PublicationStatus.PUBLISHED
    repaired_estimator = load_estimator(
        repaired_state.fitted_state.estimator_path,
        protocol.estimator_class_name,
    )
    assert isinstance(repaired_estimator, StandardScaler)
    assert repaired_estimator.transform(np.asarray([[0.5, 1.5]])).tolist() == [[0.0, 0.0]]
