from pathlib import Path

import pytest
from pydantic import ValidationError

from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    TrustedEstimatorClassName,
)
from datp_core.domain.values import (
    AbsoluteTolerance,
    ClientPathToken,
    FeatureName,
    FeatureNameSequence,
    RowCount,
    StableRowId,
    StableRowIdSequence,
)
from datp_core.preprocessing.models import (
    SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD,
    SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD,
    SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
    ClientFittedEstimator,
    ClientLocalFittedEstimators,
    FederatedFittedStatePublishSpec,
    PartitionTransformationEvidence,
    PreprocessingProtocol,
    PreprocessingValidationReport,
    build_preprocessing_protocol,
)


def test_preprocessing_protocol_uses_descriptive_enum_identity() -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
    )
    assert protocol.identity is PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION
    assert protocol.input_feature_names.names == ("f0", "f1")
    with pytest.raises(ValidationError):
        PreprocessingProtocol.model_validate(
            {
                "identity": "not_an_enum_member",
                "fit_scope": PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
                "input_feature_names": ["f0", "f1"],
                "serialization_format": SerializationFormat.SKOPS,
                "estimator_class_name": TrustedEstimatorClassName.STANDARD_SCALER,
                "numerical_equivalence_absolute_tolerance": 1e-12,
            }
        )


def test_scientific_preprocessing_methods_are_locked() -> None:
    federated = SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD
    assert federated.identity is PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    assert federated.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING
    assert federated.estimator_class_name is TrustedEstimatorClassName.STANDARD_SCALER
    assert federated.fit_partition is PartitionRole.TRAIN
    assert federated.serialization_format is SerializationFormat.SKOPS

    centralized = SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD
    assert centralized.identity is PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX
    assert centralized.fit_scope is PreprocessingFitScope.POOLED_TRAINING
    assert centralized.estimator_class_name is TrustedEstimatorClassName.MIN_MAX_SCALER

    supportive = SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD
    assert supportive.identity is PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX
    assert supportive.fit_scope is PreprocessingFitScope.POOLED_TRAINING
    assert supportive.estimator_class_name is TrustedEstimatorClassName.MIN_MAX_SCALER


def test_build_preprocessing_protocol_binds_feature_order() -> None:
    protocol = build_preprocessing_protocol(
        SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
        FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
    )
    assert tuple(protocol.input_feature_names) == ("f0", "f1")
    assert protocol.input_feature_names.names == ("f0", "f1")
    assert protocol.identity is PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    with pytest.raises(ValueError, match="non-empty"):
        build_preprocessing_protocol(SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD, FeatureNameSequence(()))


def test_stable_row_id_sequence_rejects_empty_and_duplicates() -> None:
    assert len(StableRowIdSequence((StableRowId("r1"), StableRowId("r2")))) == 2
    with pytest.raises(ValueError, match="requires a non-empty tuple"):
        StableRowIdSequence(())
    with pytest.raises(ValueError, match="must be unique"):
        StableRowIdSequence((StableRowId("r1"), StableRowId("r1")))


def test_client_local_fitted_estimators_rejects_duplicate_clients() -> None:
    from sklearn.preprocessing import StandardScaler

    dummy_estimator = StandardScaler()
    client_a = ClientPathToken("client_a")
    estimators = ClientLocalFittedEstimators(estimators=(ClientFittedEstimator(client_a, dummy_estimator),))
    assert estimators.require(client_a) is dummy_estimator
    with pytest.raises(ValueError, match="cannot contain duplicate client identities"):
        ClientLocalFittedEstimators(
            estimators=(
                ClientFittedEstimator(client_a, dummy_estimator),
                ClientFittedEstimator(client_a, dummy_estimator),
            )
        )


def test_federated_fitted_state_publish_spec_requires_client_identity() -> None:
    protocol = build_preprocessing_protocol(
        SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
        FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
    )
    spec = FederatedFittedStatePublishSpec(
        protocol=protocol,
        estimator_path=Path("state.skops"),
        fit_row_count=RowCount(10),
        client_identity=ClientPathToken("c1"),
    )

    assert spec.client_identity == ClientPathToken("c1")


def test_validation_report_rejects_mismatched_counts_and_duplicate_roles() -> None:
    evidence = (
        PartitionTransformationEvidence(
            role=PartitionRole.TRAIN, source_row_count=RowCount(10), output_row_count=RowCount(10)
        ),
    )
    report = PreprocessingValidationReport(partition_evidence=evidence)
    assert len(report.partition_evidence) == 1

    with pytest.raises(ValidationError):
        PreprocessingValidationReport(
            partition_evidence=(
                PartitionTransformationEvidence(
                    role=PartitionRole.TRAIN, source_row_count=RowCount(10), output_row_count=RowCount(5)
                ),
            ),
        )

    with pytest.raises(ValidationError):
        PreprocessingValidationReport(partition_evidence=())
