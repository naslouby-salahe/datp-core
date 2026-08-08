"""Scientific preprocessing validation and serialization-equivalence checks."""

import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import ContractSubject, PartitionRole
from datp_core.core.numeric import NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.data.preprocessing.contracts import (
    FittedPreprocessingState,
    PreprocessingPartition,
    PreprocessingProtocol,
    ScalerFamily,
    TrustedScaler,
)


def validate_fit_partition(partition: PreprocessingPartition, protocol: PreprocessingProtocol) -> None:
    if partition.role is not PartitionRole.TRAIN:
        raise LeakageError(
            "preprocessing estimators may be fitted only on the training partition",
            subject=ContractSubject.PREPROCESSING,
        )
    if partition.frame.height < 1:
        raise ScientificContractError(
            "preprocessing fit requires at least one benign training row",
            subject=ContractSubject.PREPROCESSING,
        )
    labels = tuple(str(label) for label in partition.outcome_labels)
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in labels):
        raise LeakageError(
            "attack-labelled rows cannot influence preprocessing fit",
            subject=ContractSubject.ATTACK_LABELS,
        )
    validate_feature_frame(partition.frame, protocol)


def validate_transform_partition(partition: PreprocessingPartition, protocol: PreprocessingProtocol) -> None:
    validate_feature_frame(partition.frame, protocol)


def validate_feature_frame(frame, protocol: PreprocessingProtocol) -> None:
    expected = tuple(protocol.feature_names)
    observed = tuple(frame.columns)
    if observed != expected:
        raise ScientificContractError(
            "preprocessing frame columns must equal the declared feature order exactly",
            subject=ContractSubject.FEATURES,
        )
    values = frame.to_numpy()
    if values.ndim != 2 or values.shape[1] != len(expected):
        raise ScientificContractError(
            "preprocessing frame width must equal the declared feature count",
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(values).all():
        raise ScientificContractError(
            "preprocessing never imputes or replaces non-finite feature values",
            subject=ContractSubject.FEATURES,
        )


def validate_fitted_state(state: FittedPreprocessingState) -> None:
    expected_type: type[TrustedScaler]
    match state.protocol.scaler_family:
        case ScalerFamily.STANDARD:
            expected_type = StandardScaler
        case ScalerFamily.MIN_MAX:
            expected_type = MinMaxScaler
        case ScalerFamily.COLUMN_ORDER_PROJECTION:
            raise ScientificContractError(
                "column-order projection is not a fitted scaler protocol",
                subject=ContractSubject.PREPROCESSING,
            )
    if not isinstance(state.estimator, expected_type):
        raise ScientificContractError(
            "fitted preprocessing estimator does not match its declared scaler family",
            subject=ContractSubject.PREPROCESSING,
        )
    feature_count = len(state.protocol.feature_names)
    observed = getattr(state.estimator, "n_features_in_", None)
    if observed != feature_count:
        raise ScientificContractError(
            "fitted preprocessing estimator feature count does not match the protocol",
            subject=ContractSubject.FEATURES,
        )


def validate_serialization_equivalence(
    reference: TrustedScaler,
    reloaded: TrustedScaler,
    probe: np.ndarray,
) -> None:
    left = np.asarray(reference.transform(probe), dtype=np.float64)
    right = np.asarray(reloaded.transform(probe), dtype=np.float64)
    if left.shape != right.shape or not np.allclose(
        left,
        right,
        rtol=0.0,
        atol=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value,
        equal_nan=False,
    ):
        raise ScientificContractError(
            "reloaded preprocessing state is not numerically equivalent to the fitted state",
            subject=ContractSubject.PREPROCESSING,
        )
