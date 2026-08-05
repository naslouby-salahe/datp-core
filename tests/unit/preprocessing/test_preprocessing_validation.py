import numpy as np
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

from datp_core.datasets.partitioning.contracts import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN
from datp_core.domain.enums import (
    ContractSubject,
    PartitionOrdering,
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    FeatureName,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.preprocessing.models import (
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
)
from datp_core.preprocessing.validation import (
    extract_partitions,
    fit_trusted_batch,
    require_finite_matrix,
    transform_feature_matrix,
    validate_no_partition_overlap,
)


def _protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )


def _partition_frame(row_ids: list[str], labels: list[str]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: row_ids,
            OUTCOME_LABEL_COLUMN: labels,
            "f0": [1.0] * len(row_ids),
            "f1": [2.0] * len(row_ids),
        }
    )


def test_partitions_and_overlap_guards() -> None:
    train = PreprocessingPartition(PartitionRole.TRAIN, _partition_frame(["r0", "r1"], ["benign", "benign"]))
    calibration = PreprocessingPartition(PartitionRole.CALIBRATION, _partition_frame(["r2"], ["benign"]))
    evaluation = PreprocessingPartition(PartitionRole.EVALUATION, _partition_frame(["r3"], ["benign"]))
    partitions = PreprocessingPartitions((train, calibration, evaluation))

    validate_no_partition_overlap(partitions, split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS)

    overlap = PreprocessingPartitions(
        (
            train,
            PreprocessingPartition(PartitionRole.CALIBRATION, _partition_frame(["r1"], ["benign"])),
            evaluation,
        )
    )
    with pytest.raises(LeakageError, match="overlap"):
        validate_no_partition_overlap(overlap, split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS)


def test_extract_partitions_returns_role_indexed_collection() -> None:
    frame = pl.DataFrame(
        {
            "partition_role": ["train", "train", "calibration", "evaluation"],
            STABLE_ROW_ID_COLUMN: ["r2", "r1", "r3", "r4"],
            OUTCOME_LABEL_COLUMN: ["benign", "benign", "benign", "benign"],
            "f0": [1.0, 2.0, 3.0, 4.0],
            "f1": [5.0, 6.0, 7.0, 8.0],
        }
    )
    partitions = extract_partitions(
        frame,
        FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        branch=ProcessedDataBranch.FEDERATED,
        ordering=PartitionOrdering.STABLE_ROW_ID,
    )

    assert isinstance(partitions, PreprocessingPartitions)
    assert partitions.require(PartitionRole.TRAIN).row_ids.row_ids == ("r1", "r2")


def test_fit_trusted_batch_validation_rules() -> None:
    protocol = _protocol()
    invalid_batches = (
        PreprocessingFitBatch(
            training_matrix=np.empty((0, 2)),
            training_row_ids=StableRowIdSequence((StableRowId("r0"),)),
            training_labels=OutcomeLabelSequence((OutcomeLabel("benign"),)),
        ),
        PreprocessingFitBatch(
            training_matrix=np.array([1.0, 2.0]),
            training_row_ids=StableRowIdSequence((StableRowId("r0"),)),
            training_labels=OutcomeLabelSequence((OutcomeLabel("benign"),)),
        ),
    )
    for batch in invalid_batches:
        with pytest.raises(ScientificContractError, match="non-empty and two-dimensional"):
            fit_trusted_batch(protocol, batch, subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING)

    with pytest.raises(ScientificContractError, match="width must match"):
        fit_trusted_batch(
            protocol,
            PreprocessingFitBatch(
                training_matrix=np.array([[1.0, 2.0, 3.0]]),
                training_row_ids=StableRowIdSequence((StableRowId("r0"),)),
                training_labels=OutcomeLabelSequence((OutcomeLabel("benign"),)),
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )

    with pytest.raises(ScientificContractError, match="training matrix must be finite"):
        fit_trusted_batch(
            protocol,
            PreprocessingFitBatch(
                training_matrix=np.array([[1.0, np.nan]]),
                training_row_ids=StableRowIdSequence((StableRowId("r0"),)),
                training_labels=OutcomeLabelSequence((OutcomeLabel("benign"),)),
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )


def test_transform_feature_matrix_validations() -> None:
    protocol = _protocol()
    fitted = StandardScaler().fit(np.array([[1.0, 2.0], [3.0, 4.0]]))

    with pytest.raises(ScientificContractError, match="two-dimensional"):
        transform_feature_matrix(
            fitted,
            np.array([1.0, 2.0]),
            protocol.input_feature_names,
            PartitionRole.TRAIN,
            description="transformed evaluation matrix",
        )

    require_finite_matrix(np.asarray([[1.0, 2.0]]), subject=ContractSubject.FEATURES, description="test matrix")
    with pytest.raises(ScientificContractError):
        require_finite_matrix(np.asarray([[1.0, np.nan]]), subject=ContractSubject.FEATURES, description="test matrix")
