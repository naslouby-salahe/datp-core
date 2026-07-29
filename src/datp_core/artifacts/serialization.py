"""Generic safe serialization for trusted estimators and Pydantic models."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

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


@dataclass(frozen=True, slots=True)
class TrustedEstimatorDefinition:
    estimator_type: type[TrustedScaler]
    constructor: Callable[[], TrustedScaler]


_TRUSTED_ESTIMATORS: dict[TrustedEstimatorClassName, TrustedEstimatorDefinition] = {
    TrustedEstimatorClassName.STANDARD_SCALER: TrustedEstimatorDefinition(
        StandardScaler,
        lambda: StandardScaler(with_mean=True, with_std=True),
    ),
    TrustedEstimatorClassName.MIN_MAX_SCALER: TrustedEstimatorDefinition(
        MinMaxScaler,
        lambda: MinMaxScaler(feature_range=(0, 1), clip=False),
    ),
}


def trusted_estimator_type_names() -> frozenset[str]:
    return frozenset(
        f"{definition.estimator_type.__module__}.{definition.estimator_type.__name__}"
        for definition in _TRUSTED_ESTIMATORS.values()
    )


def resolve_trusted_estimator_type(class_name: TrustedEstimatorClassName) -> type[TrustedScaler]:
    return _TRUSTED_ESTIMATORS[class_name].estimator_type


def construct_trusted_estimator(class_name: TrustedEstimatorClassName) -> TrustedScaler:
    """Build a scientific estimator with locked constructor arguments."""
    return _TRUSTED_ESTIMATORS[class_name].constructor()


def clone_trusted_scaler(estimator: TrustedScaler, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    if type(estimator) is not resolve_trusted_estimator_type(class_name):
        raise SerializationSafetyError(
            "estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.ESTIMATOR,
        )
    return cast(TrustedScaler, clone(estimator))


def serialize_estimator(estimator: BaseEstimator, destination: Path) -> Checksum:
    estimator_type = type(estimator)
    if estimator_type not in {definition.estimator_type for definition in _TRUSTED_ESTIMATORS.values()}:
        raise SerializationSafetyError(
            f"untrusted preprocessing estimator type {estimator_type.__module__}.{estimator_type.__name__}",
            subject=SerializationSubject.PREPROCESSING_ESTIMATOR,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(skops_io.dumps(estimator))
    return checksum_file(destination)


def load_estimator(path: Path, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    expected_type = resolve_trusted_estimator_type(class_name)
    loaded = skops_io.loads(path.read_bytes(), trusted=list(trusted_estimator_type_names()))
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
