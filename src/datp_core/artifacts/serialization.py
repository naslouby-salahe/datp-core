"""Safe serialization for trusted estimators and canonical artifact documents."""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, StrEnum
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
import skops.io as skops_io
from pydantic import BaseModel, TypeAdapter
from sklearn.base import BaseEstimator, clone
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from datp_core.domain.enums import TrustedEstimatorClassName
from datp_core.domain.errors import SerializationSafetyError
from datp_core.domain.values import AbsoluteTolerance, Checksum, checksum_file, checksum_text

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

TrustedScaler = StandardScaler | MinMaxScaler

type CanonicalValue = (
    None
    | bool
    | int
    | float
    | str
    | tuple["CanonicalValue", ...]
    | list["CanonicalValue"]
    | dict[str, "CanonicalValue"]
)

STANDARD_SCALER_WITH_MEAN = True
STANDARD_SCALER_WITH_STANDARD_DEVIATION = True
MIN_MAX_LOWER_BOUND = 0.0
MIN_MAX_UPPER_BOUND = 1.0
MIN_MAX_CLIP = False
JSON_SEPARATORS = (",", ":")


class SerializationSubject(StrEnum):
    ESTIMATOR = "estimator"
    PREPROCESSING_ESTIMATOR = "preprocessing estimator"


@dataclass(frozen=True, slots=True)
class TrustedEstimatorDefinition:
    identity: TrustedEstimatorClassName
    estimator_type: type[TrustedScaler]
    constructor: Callable[[], TrustedScaler]


_TRUSTED_ESTIMATORS: tuple[TrustedEstimatorDefinition, ...] = (
    TrustedEstimatorDefinition(
        identity=TrustedEstimatorClassName.STANDARD_SCALER,
        estimator_type=StandardScaler,
        constructor=lambda: StandardScaler(
            with_mean=STANDARD_SCALER_WITH_MEAN,
            with_std=STANDARD_SCALER_WITH_STANDARD_DEVIATION,
        ),
    ),
    TrustedEstimatorDefinition(
        identity=TrustedEstimatorClassName.MIN_MAX_SCALER,
        estimator_type=MinMaxScaler,
        constructor=lambda: MinMaxScaler(
            feature_range=(MIN_MAX_LOWER_BOUND, MIN_MAX_UPPER_BOUND),
            clip=MIN_MAX_CLIP,
        ),
    ),
)


def _canonical_dataclass_value(value: "DataclassInstance") -> CanonicalValue:
    if getattr(type(value), "__get_pydantic_core_schema__", None) is not None:
        return canonical_value(TypeAdapter(type(value)).dump_python(value))
    own_fields = fields(value)
    if len(own_fields) == 1 and own_fields[0].name == "value":
        return canonical_value(getattr(value, own_fields[0].name))
    return {field.name: canonical_value(getattr(value, field.name)) for field in own_fields}


def canonical_value(value: object) -> CanonicalValue:
    """Convert a supported value into a deterministic, finite JSON document value."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical scientific artifacts cannot contain non-finite floats")
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return canonical_value(value.value)
    if isinstance(value, BaseModel):
        return {name: canonical_value(getattr(value, name)) for name in type(value).model_fields}
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_dataclass_value(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return {key: canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return tuple(canonical_value(item) for item in value)
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    raise TypeError(f"unsupported canonical artifact value: {type(value).__qualname__}")


def canonical_mapping(value: object) -> dict[str, CanonicalValue]:
    """Return a canonical JSON object and reject non-mapping roots."""
    document = canonical_value(value)
    if not isinstance(document, dict):
        raise TypeError("canonical document root must be a mapping")
    return document


def canonical_json_text(value: object) -> str:
    """Serialize one supported value using the repository canonical JSON contract."""
    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=JSON_SEPARATORS,
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_checksum(value: object) -> Checksum:
    """Checksum one supported value under the canonical JSON contract."""
    return checksum_text(canonical_json_text(value))


def _definition_for(identity: TrustedEstimatorClassName) -> TrustedEstimatorDefinition:
    matches = tuple(definition for definition in _TRUSTED_ESTIMATORS if definition.identity is identity)
    if len(matches) != 1:
        raise SerializationSafetyError(
            "trusted estimator identity must resolve exactly once",
            subject=SerializationSubject.ESTIMATOR,
        )
    return matches[0]


def trusted_estimator_type_names() -> frozenset[str]:
    return frozenset(
        f"{definition.estimator_type.__module__}.{definition.estimator_type.__name__}"
        for definition in _TRUSTED_ESTIMATORS
    )


def resolve_trusted_estimator_type(class_name: TrustedEstimatorClassName) -> type[TrustedScaler]:
    return _definition_for(class_name).estimator_type


def construct_trusted_estimator(class_name: TrustedEstimatorClassName) -> TrustedScaler:
    """Build a scientific estimator with explicit locked constructor arguments."""
    return _definition_for(class_name).constructor()


def clone_trusted_scaler(estimator: TrustedScaler, class_name: TrustedEstimatorClassName) -> TrustedScaler:
    if type(estimator) is not resolve_trusted_estimator_type(class_name):
        raise SerializationSafetyError(
            "estimator class does not match the trusted estimator identity",
            subject=SerializationSubject.ESTIMATOR,
        )
    return cast(TrustedScaler, clone(estimator))


def serialize_estimator(estimator: BaseEstimator, destination: Path) -> Checksum:
    estimator_type = type(estimator)
    trusted_types = tuple(definition.estimator_type for definition in _TRUSTED_ESTIMATORS)
    if estimator_type not in trusted_types:
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
    """Persist one strict model through the repository canonical JSON contract."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_text(model)
    destination.write_text(payload, encoding="utf-8")
    return checksum_text(payload)


def transforms_are_equivalent(
    left: np.ndarray,
    right: np.ndarray,
    absolute_tolerance: AbsoluteTolerance,
) -> bool:
    if left.shape != right.shape:
        return False
    return bool(
        np.allclose(
            left,
            right,
            rtol=0.0,
            atol=absolute_tolerance.value,
            equal_nan=False,
        )
    )
