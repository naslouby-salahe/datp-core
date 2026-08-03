from pathlib import Path

import numpy as np
import polars as pl
import pytest

from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    AbsoluteTolerance,
    Checksum,
    ClientPathToken,
    FeatureNameSequence,
    OutcomeLabelSequence,
    RowCount,
    StableRowIdSequence,
)
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel
from datp_core.preprocessing.federated import (
    ClientPreprocessingPartitions,
    fit_estimators_for_federated_clients,
)
from datp_core.preprocessing.models import (
    ClientLocalFittedEstimators,
    FittedPreprocessingState,
    PooledFittedEstimator,
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
    TransformedSchema,
)
from datp_core.preprocessing.validation import fit_trusted_batch, validate_branch_isolation


def _protocol(scope: PreprocessingFitScope = PreprocessingFitScope.CLIENT_LOCAL_TRAINING) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=scope,
        input_feature_names=FeatureNameSequence(("f0", "f1")),
        transformed_schema=TransformedSchema(feature_names=FeatureNameSequence(("f0", "f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )


def _partition_set(row_prefix: str = "r") -> PreprocessingPartitionSet:
    frame = pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: [f"{row_prefix}_0", f"{row_prefix}_1"],
            OUTCOME_LABEL_COLUMN: [PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.BENIGN.value],
            "f0": [0.0, 1.0],
            "f1": [1.0, 2.0],
        }
    )
    return PreprocessingPartitionSet(
        partitions=(
            PreprocessingPartition(role=PartitionRole.TRAIN, frame=frame),
            PreprocessingPartition(role=PartitionRole.CALIBRATION, frame=frame),
            PreprocessingPartition(role=PartitionRole.EVALUATION, frame=frame),
        )
    )


def test_fit_estimators_client_local_returns_distinct_instances() -> None:
    protocol = _protocol(PreprocessingFitScope.CLIENT_LOCAL_TRAINING)
    client_a = ClientPathToken("client_a")
    client_b = ClientPathToken("client_b")
    client_ids = (client_a, client_b)
    partitions = (
        ClientPreprocessingPartitions(client_identity=client_a, partitions=_partition_set("a")),
        ClientPreprocessingPartitions(client_identity=client_b, partitions=_partition_set("b")),
    )
    result = fit_estimators_for_federated_clients(protocol, client_ids, partitions)
    assert isinstance(result, ClientLocalFittedEstimators)
    estimator_a = result.require(client_a)
    estimator_b = result.require(client_b)
    assert estimator_a is not estimator_b


def test_fit_estimators_pooled_returns_single_pooled_estimator() -> None:
    protocol = _protocol(PreprocessingFitScope.POOLED_TRAINING)
    client_a = ClientPathToken("client_a")
    client_b = ClientPathToken("client_b")
    client_ids = (client_a, client_b)
    partitions = (
        ClientPreprocessingPartitions(client_identity=client_a, partitions=_partition_set("a")),
        ClientPreprocessingPartitions(client_identity=client_b, partitions=_partition_set("b")),
    )
    result = fit_estimators_for_federated_clients(protocol, client_ids, partitions)
    assert isinstance(result, PooledFittedEstimator)
    assert result.estimator is not None


def test_fit_trusted_batch_rejects_attack_labels() -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [1.0, 2.0]], dtype=float)
    from datp_core.artifacts.serialization import construct_trusted_estimator

    with pytest.raises(LeakageError):
        fit_trusted_batch(
            protocol,
            construct_trusted_estimator(TrustedEstimatorClassName.STANDARD_SCALER),
            PreprocessingFitBatch(
                training_matrix=matrix,
                training_row_ids=StableRowIdSequence(("r0", "r1")),
                training_labels=OutcomeLabelSequence(("benign", "attack")),
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )


def test_branch_isolation_checks() -> None:
    protocol = _protocol()
    centralized_state = FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        client_identity=None,
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(2),
        fit_partition=PartitionRole.TRAIN,
    )
    with pytest.raises(ScientificContractError):
        validate_branch_isolation(centralized_state, ProcessedDataBranch.FEDERATED, ClientPathToken("client_a"))

    federated_state = FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.FEDERATED,
        client_identity=ClientPathToken("client_a"),
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(2),
        fit_partition=PartitionRole.TRAIN,
    )
    with pytest.raises(ScientificContractError):
        validate_branch_isolation(federated_state, ProcessedDataBranch.CENTRALIZED_REFERENCE, None)
