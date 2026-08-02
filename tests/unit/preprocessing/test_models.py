import pytest
from pydantic import ValidationError

from datp_core.domain.enums import (
    PartitionRole,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.values import FeatureNameSequence
from datp_core.preprocessing.models import (
    SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD,
    SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
    PreprocessingProtocol,
    TransformedFeature,
    TransformedSchema,
    build_preprocessing_protocol,
    scientific_preprocessing_method,
)


def _schema() -> TransformedSchema:
    return TransformedSchema(
        features=(TransformedFeature(name="f0", position=0), TransformedFeature(name="f1", position=1))
    )


def test_preprocessing_protocol_uses_descriptive_enum_identity() -> None:
    protocol = PreprocessingProtocol(
        identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FeatureNameSequence(("f0", "f1")),
        transformed_schema=_schema(),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
        numerical_equivalence_absolute_tolerance=1e-12,
    )
    assert protocol.identity is PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION
    assert protocol.qualified_estimator_name == "sklearn.preprocessing.StandardScaler"
    with pytest.raises(ValidationError):
        PreprocessingProtocol.model_validate(
            {
                "identity": "not_an_enum_member",
                "fit_scope": PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
                "input_feature_names": ["f0", "f1"],
                "transformed_schema": _schema().model_dump(),
                "serialization_format": SerializationFormat.SKOPS,
                "estimator_module": TrustedEstimatorModule.SKLEARN_PREPROCESSING,
                "estimator_class_name": TrustedEstimatorClassName.STANDARD_SCALER,
                "numerical_equivalence_absolute_tolerance": 1e-12,
            }
        )


def test_scientific_preprocessing_methods_are_locked() -> None:
    federated = scientific_preprocessing_method()
    assert federated is SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD
    assert federated.identity is PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    assert federated.fit_scope is PreprocessingFitScope.CLIENT_LOCAL_TRAINING
    assert federated.estimator_class_name is TrustedEstimatorClassName.STANDARD_SCALER
    assert federated.fit_partition is PartitionRole.TRAIN
    assert federated.serialization_format is SerializationFormat.SKOPS

    centralized = SCIENTIFIC_CENTRALIZED_PREPROCESSING_METHOD
    assert centralized.identity is PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX
    assert centralized.fit_scope is PreprocessingFitScope.POOLED_TRAINING
    assert centralized.estimator_class_name is TrustedEstimatorClassName.MIN_MAX_SCALER

    from datp_core.preprocessing.models import (
        SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD,
        scientific_federated_pooled_min_max_method,
    )

    supportive = scientific_federated_pooled_min_max_method()
    assert supportive is SCIENTIFIC_FEDERATED_POOLED_MIN_MAX_METHOD
    assert supportive.identity is PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX
    assert supportive.fit_scope is PreprocessingFitScope.POOLED_TRAINING
    assert supportive.estimator_class_name is TrustedEstimatorClassName.MIN_MAX_SCALER


def test_build_preprocessing_protocol_binds_feature_order() -> None:
    protocol = build_preprocessing_protocol(
        SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD,
        FeatureNameSequence(("f0", "f1")),
    )
    assert tuple(protocol.input_feature_names) == ("f0", "f1")
    assert protocol.transformed_schema.feature_names == ("f0", "f1")
    assert protocol.identity is PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    with pytest.raises(ValueError, match="non-empty"):
        build_preprocessing_protocol(SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD, FeatureNameSequence(()))
