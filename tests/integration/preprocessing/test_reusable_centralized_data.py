from pathlib import Path

import polars as pl
from sklearn.preprocessing import StandardScaler

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
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
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, Seed
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.data.preprocessing.centralized import PooledPublishRequest, publish_pooled_preprocessing
from datp_core.data.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
    PreprocessingPublishContext,
)


def test_centralized_publication_is_independent_and_reusable(tmp_path: Path) -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )
    frame_train = pl.DataFrame(
        {
            "stable_row_id": ["t0", "t1"],
            "outcome_label": ["benign", "benign"],
            "f0": [0.0, 2.0],
            "f1": [1.0, 3.0],
        }
    )
    frame_cal = pl.DataFrame({"stable_row_id": ["c0"], "outcome_label": ["benign"], "f0": [1.0], "f1": [2.0]})
    frame_eval = pl.DataFrame({"stable_row_id": ["e0"], "outcome_label": ["benign"], "f0": [3.0], "f1": [4.0]})
    partitions = PreprocessingPartitions(
        (
            PreprocessingPartition(PartitionRole.TRAIN, frame_train),
            PreprocessingPartition(PartitionRole.CALIBRATION, frame_cal),
            PreprocessingPartition(PartitionRole.EVALUATION, frame_eval),
        )
    )
    data_root = tmp_path / "data"
    fitted = StandardScaler().fit(frame_train.select(list(protocol.input_feature_names)).to_numpy())
    context = PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=protocol,
        canonical_schema_checksum=Checksum("d" * 64),
        data_root=data_root,
    )
    request = PooledPublishRequest(context=context, fitted_estimator=fitted, partitions=partitions)

    first = publish_pooled_preprocessing(request)
    second = publish_pooled_preprocessing(request)

    assert isinstance(first.fitted_state, CentralizedFittedPreprocessingState)
    assert first.publication_status is PublicationStatus.PUBLISHED
    assert second.publication_status is PublicationStatus.REUSED
    assert first.paths.train == second.paths.train
    assert "centralized_reference" in first.paths.train.parts
