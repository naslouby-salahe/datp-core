"""Safe serialization for fitted preprocessing estimators and manifests."""

from hashlib import sha256
from pathlib import Path
from typing import Final, cast

import numpy as np
import skops.io as skops_io
from pydantic import BaseModel
from sklearn.base import BaseEstimator, clone
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.domain.enums import TrustedEstimatorClassName
from datp_core.domain.errors import SerializationSafetyError
from datp_core.domain.values import Checksum
from datp_core.preprocessing.models import PreprocessingProtocol, TransformedSchema

TrustedScaler = StandardScaler | MinMaxScaler
_TRUSTED_ESTIMATOR_TYPES: Final[dict[TrustedEstimatorClassName, type[TrustedScaler]]] = {
    TrustedEstimatorClassName.STANDARD_SCALER: StandardScaler,
    TrustedEstimatorClassName.MIN_MAX_SCALER: MinMaxScaler,
}
_TRUSTED_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    f"{estimator_type.__module__}.{estimator_type.__name__}" for estimator_type in _TRUSTED_ESTIMATOR_TYPES.values()
)


def trusted_estimator_type_names() -> frozenset[str]:
    return _TRUSTED_TYPE_NAMES


def resolve_trusted_estimator_type(protocol: PreprocessingProtocol) -> type[TrustedScaler]:
    try:
        return _TRUSTED_ESTIMATOR_TYPES[protocol.estimator_class_name]
    except KeyError as error:
        raise SerializationSafetyError(
            f"protocol estimator {protocol.qualified_estimator_name} is not an approved trusted type",
            subject="preprocessing estimator",
        ) from error


def construct_trusted_estimator(class_name: TrustedEstimatorClassName) -> TrustedScaler:
    """Build a scientific estimator with locked constructor arguments."""
    match class_name:
        case TrustedEstimatorClassName.STANDARD_SCALER:
            return StandardScaler(with_mean=True, with_std=True)
        case TrustedEstimatorClassName.MIN_MAX_SCALER:
            return MinMaxScaler(feature_range=(0, 1), clip=False)


def clone_trusted_scaler(estimator: TrustedScaler, protocol: PreprocessingProtocol) -> TrustedScaler:
    if type(estimator) is not resolve_trusted_estimator_type(protocol):
        raise SerializationSafetyError(
            "estimator class does not match the preprocessing protocol",
            subject="estimator",
        )
    return cast(TrustedScaler, clone(estimator))


def serialize_estimator(estimator: BaseEstimator, destination: Path) -> Checksum:
    estimator_type = type(estimator)
    if estimator_type not in _TRUSTED_ESTIMATOR_TYPES.values():
        raise SerializationSafetyError(
            f"untrusted preprocessing estimator type {estimator_type.__module__}.{estimator_type.__name__}",
            subject="preprocessing estimator",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(skops_io.dumps(estimator))
    return file_checksum(destination)


def load_estimator(path: Path, protocol: PreprocessingProtocol) -> TrustedScaler:
    expected_type = resolve_trusted_estimator_type(protocol)
    loaded = skops_io.loads(path.read_bytes(), trusted=list(_TRUSTED_TYPE_NAMES))
    if type(loaded) is not expected_type:
        raise SerializationSafetyError(
            "reloaded estimator class does not match the preprocessing protocol",
            subject="preprocessing estimator",
        )
    if not isinstance(loaded, (StandardScaler, MinMaxScaler)):
        raise SerializationSafetyError(
            "reloaded estimator is not an approved trusted type",
            subject="preprocessing estimator",
        )
    return loaded


def serialize_json_model(model: BaseModel, destination: Path) -> Checksum:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump_json()
    destination.write_text(payload, encoding="utf-8")
    return Checksum(sha256(payload.encode()).hexdigest())


def file_checksum(path: Path) -> Checksum:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return Checksum(digest.hexdigest())


def transforms_are_equivalent(
    left: np.ndarray,
    right: np.ndarray,
    absolute_tolerance: float,
) -> bool:
    if left.shape != right.shape:
        return False
    return bool(np.allclose(left, right, rtol=0.0, atol=absolute_tolerance, equal_nan=False))


def schema_feature_matrix(schema: TransformedSchema, values: np.ndarray) -> np.ndarray:
    if values.ndim != 2:
        raise ValueError("transformed feature matrices must be two-dimensional")
    if values.shape[1] != len(schema.features):
        raise ValueError("transformed matrix width must match the transformed schema")
    return values
