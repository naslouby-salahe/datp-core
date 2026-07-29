"""Generic safe serialization for trusted estimators and Pydantic models."""

from enum import StrEnum
from pathlib import Path
from typing import Final, cast

import numpy as np
import skops.io as skops_io
from pydantic import BaseModel
from sklearn.base import BaseEstimator, clone
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.domain.enums import TrustedEstimatorClassName
from datp_core.domain.errors import SerializationSafetyError
from datp_core.domain.values import Checksum, checksum_file, checksum_text

TrustedScaler = StandardScaler | MinMaxScaler


class SerializationSubject(StrEnum):
    ESTIMATOR = "estimator"
    PREPROCESSING_ESTIMATOR = "preprocessing estimator"


def _trusted_estimator_type(class_name: TrustedEstimatorClassName) -> type[TrustedScaler]:
    match class_name:
        case TrustedEstimatorClassName.STANDARD_SCALER:
            return StandardScaler
        case TrustedEstimatorClassName.MIN_MAX_SCALER:
            return MinMaxScaler


_TRUSTED_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    (
        f"{StandardScaler.__module__}.{StandardScaler.__name__}",
        f"{MinMaxScaler.__module__}.{MinMaxScaler.__name__}",
    )
)


def trusted_estimator_type_names() -> frozenset[str]:
    return _TRUSTED_TYPE_NAMES


def resolve_trusted_estimator_type(class_name: TrustedEstimatorClassName) -> type[TrustedScaler]:
    return _trusted_estimator_type(class_name)


def construct_trusted_estimator(class_name: TrustedEstimatorClassName) -> TrustedScaler:
    """Build a scientific estimator with locked constructor arguments."""
    match class_name:
        case TrustedEstimatorClassName.STANDARD_SCALER:
            return StandardScaler(with_mean=True, with_std=True)
        case TrustedEstimatorClassName.MIN_MAX_SCALER:
            return MinMaxScaler(feature_range=(0, 1), clip=False)


def clone_trusted_scaler(estimator: TrustedScaler, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    if type(estimator) is not resolve_trusted_estimator_type(class_name):
        raise SerializationSafetyError(
            "estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.ESTIMATOR,
        )
    return cast(TrustedScaler, clone(estimator))


def serialize_estimator(estimator: BaseEstimator, destination: Path) -> Checksum:
    estimator_type = type(estimator)
    if estimator_type not in (StandardScaler, MinMaxScaler):
        raise SerializationSafetyError(
            f"untrusted preprocessing estimator type {estimator_type.__module__}.{estimator_type.__name__}",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(skops_io.dumps(estimator))
    return checksum_file(destination)


def load_estimator(path: Path, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    expected_type = resolve_trusted_estimator_type(class_name)
    loaded = skops_io.loads(path.read_bytes(), trusted=list(_TRUSTED_TYPE_NAMES))
    if type(loaded) is not expected_type:
        raise SerializationSafetyError(
            "reloaded estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    if not isinstance(loaded, (StandardScaler, MinMaxScaler)):
        raise SerializationSafetyError(
            "reloaded estimator is not an approved trusted type",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    return loaded


def serialize_json_model(model: BaseModel, destination: Path) -> Checksum:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump_json()
    destination.write_text(payload, encoding="utf-8")
    return checksum_text(payload)


def transforms_are_equivalent(
    left: np.ndarray,
    right: np.ndarray,
    absolute_tolerance: float,
) -> bool:
    if left.shape != right.shape:
        return False
    return bool(np.allclose(left, right, rtol=0.0, atol=absolute_tolerance, equal_nan=False))


def feature_matrix_width_matches(values: np.ndarray, expected_width: int) -> np.ndarray:
    if values.ndim != 2:
        raise ValueError("transformed feature matrices must be two-dimensional")
    if values.shape[1] != expected_width:
        raise ValueError("transformed matrix width must match the transformed schema")
    return values
