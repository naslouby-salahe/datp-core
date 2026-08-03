from pathlib import Path

import numpy as np
import polars as pl
import pytest

from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    TrustedEstimatorClassName,
)
from datp_core.domain.errors import LeakageError
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    Checksum,
    ClientPathToken,
    FeatureName,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    RowCount,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel
from datp_core.preprocessing.federated import (
    fit_estimators_for_federated_clients,
)
from datp_core.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    ClientLocalFittedEstimators,
    ClientPreprocessingPartitions,
    ClientPreprocessingPartitionSet,
    FederatedFittedPreprocessingState,
    PooledFittedEstimator,
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitionSet,
    PreprocessingProtocol,
)
from datp_core.preprocessing.validation import fit_trusted_batch


def _protocol(scope: PreprocessingFitScope = PreprocessingFitScope.CLIENT_LOCAL_TRAINING) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=scope,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
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
    partition_set = ClientPreprocessingPartitionSet(
        clients=(
            ClientPreprocessingPartitions(client_identity=client_a, partitions=_partition_set("a")),
            ClientPreprocessingPartitions(client_identity=client_b, partitions=_partition_set("b")),
        )
    )
    result = fit_estimators_for_federated_clients(protocol, partition_set)
    assert isinstance(result, ClientLocalFittedEstimators)
    estimator_a = result.require(client_a)
    estimator_b = result.require(client_b)
    assert estimator_a is not estimator_b


def test_fit_estimators_pooled_returns_single_pooled_estimator() -> None:
    protocol = _protocol(PreprocessingFitScope.POOLED_TRAINING)
    client_a = ClientPathToken("client_a")
    client_b = ClientPathToken("client_b")
    partition_set = ClientPreprocessingPartitionSet(
        clients=(
            ClientPreprocessingPartitions(client_identity=client_a, partitions=_partition_set("a")),
            ClientPreprocessingPartitions(client_identity=client_b, partitions=_partition_set("b")),
        )
    )
    result = fit_estimators_for_federated_clients(protocol, partition_set)
    assert isinstance(result, PooledFittedEstimator)
    assert result.estimator is not None


def test_fit_trusted_batch_rejects_attack_labels() -> None:
    protocol = _protocol()
    matrix = np.asarray([[0.0, 1.0], [1.0, 2.0]], dtype=float)

    with pytest.raises(LeakageError):
        fit_trusted_batch(
            protocol,
            PreprocessingFitBatch(
                training_matrix=matrix,
                training_row_ids=StableRowIdSequence((StableRowId("r0"), StableRowId("r1"))),
                training_labels=OutcomeLabelSequence((OutcomeLabel("benign"), OutcomeLabel("attack"))),
            ),
            subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        )


def test_fitted_state_types() -> None:
    protocol = _protocol()
    centralized_state = CentralizedFittedPreprocessingState(
        protocol=protocol,
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(2),
    )
    assert not hasattr(centralized_state, "client_identity")

    federated_state = FederatedFittedPreprocessingState(
        protocol=protocol,
        client_identity=ClientPathToken("client_a"),
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(2),
    )
    assert federated_state.client_identity == ClientPathToken("client_a")
