from pathlib import Path

import numpy as np
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import LeakageError
from datp_core.core.identifiers import (
    ClientPathToken,
    FeatureName,
    FeatureNameSequence,
    OutcomeLabel,
    OutcomeLabelSequence,
    PartitionRole,
    PreprocessingProtocolId,
    SerializationFormat,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE, RowCount
from datp_core.data.populations.contracts import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel
from datp_core.data.preprocessing.artifact_validation import fit_trusted_batch
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.data.preprocessing.federated import fit_estimators_for_federated_clients
from datp_core.data.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    FederatedFittedPreprocessingState,
    PreprocessingFitBatch,
    PreprocessingPartition,
    PreprocessingPartitions,
    PreprocessingProtocol,
)


def _protocol(scope: PreprocessingFitScope = PreprocessingFitScope.CLIENT_LOCAL_TRAINING) -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=scope,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )


def _partitions(row_prefix: str = "r") -> PreprocessingPartitions:
    frame = pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: [f"{row_prefix}_0", f"{row_prefix}_1"],
            OUTCOME_LABEL_COLUMN: [PopulationOutcomeLabel.BENIGN.value, PopulationOutcomeLabel.BENIGN.value],
            "f0": [0.0, 1.0],
            "f1": [1.0, 2.0],
        }
    )
    return PreprocessingPartitions(
        (
            PreprocessingPartition(PartitionRole.TRAIN, frame),
            PreprocessingPartition(PartitionRole.CALIBRATION, frame),
            PreprocessingPartition(PartitionRole.EVALUATION, frame),
        )
    )


def _client_partitions() -> ClientCollection[ClientPathToken, PreprocessingPartitions]:
    return ClientCollection(
        (
            ClientOwned(ClientPathToken("client_a"), _partitions("a")),
            ClientOwned(ClientPathToken("client_b"), _partitions("b")),
        )
    )


def test_fit_estimators_client_local_returns_distinct_instances() -> None:
    result = fit_estimators_for_federated_clients(
        _protocol(PreprocessingFitScope.CLIENT_LOCAL_TRAINING),
        _client_partitions(),
    )

    assert isinstance(result, ClientCollection)
    assert result.require(ClientPathToken("client_a")) is not result.require(ClientPathToken("client_b"))


def test_fit_estimators_pooled_returns_scaler_directly() -> None:
    result = fit_estimators_for_federated_clients(
        _protocol(PreprocessingFitScope.POOLED_TRAINING),
        _client_partitions(),
    )

    assert isinstance(result, StandardScaler)


def test_fit_trusted_batch_rejects_attack_labels() -> None:
    matrix = np.asarray([[0.0, 1.0], [1.0, 2.0]], dtype=float)
    protocol = _protocol()
    batch = PreprocessingFitBatch(
        training_matrix=matrix,
        training_row_ids=StableRowIdSequence((StableRowId("r0"), StableRowId("r1"))),
        training_labels=OutcomeLabelSequence((OutcomeLabel("benign"), OutcomeLabel("attack"))),
    )
    with pytest.raises(LeakageError):
        fit_trusted_batch(protocol, batch, subject=PreprocessingFitScope.CLIENT_LOCAL_TRAINING)


def test_fitted_state_types_keep_scientific_boundary() -> None:
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
        estimator_path=Path("state.skops"),
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(2),
        client_identity=ClientPathToken("client_a"),
    )
    assert federated_state.client_identity == ClientPathToken("client_a")
