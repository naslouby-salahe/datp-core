"""Validated scalar scientific values."""

from dataclasses import dataclass
from functools import total_ordering
from hashlib import file_digest, sha256
from math import isclose, isfinite
from operator import lt as _lt
from pathlib import Path
from typing import Any, ClassVar

# Shared math.isclose controls for absolute-only floating comparisons.
NUMERIC_ZERO: float = 0.0
NO_RELATIVE_TOLERANCE: float = 0.0


def floats_absolutely_close(left: float, right: float, absolute_tolerance: float) -> bool:
    """Compare floats with an explicit absolute tolerance and zero relative tolerance."""
    if absolute_tolerance < NUMERIC_ZERO:
        raise ValueError("absolute tolerance must be non-negative")
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance)


def floats_exactly_equal(left: float, right: float) -> bool:
    """Full-precision equality with no absolute or relative tolerance band."""
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=NUMERIC_ZERO)


def is_numeric_zero(value: float) -> bool:
    return floats_exactly_equal(value, NUMERIC_ZERO)


def _integer(value: int, name: str, minimum: int) -> int:
    # bool is a subclass of int; reject it explicitly.
    if isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: int | float, name: str) -> float:
    # bool is a subclass of int; reject it explicitly.
    if isinstance(value, bool) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _ordering_compare(left: Any, right: object, op: Any = None) -> bool:
    """Cross-type total ordering for integer and float value objects.

    Accepts ``left`` (``self``) and ``right`` (another value object or a raw
    ``int`` / ``float``).
    Returns ``NotImplemented`` for unrecognized types so Python can try the
    reflected operator on ``right``.
    """
    if isinstance(right, (int, float)) and not isinstance(right, bool):
        return _lt(left.value, right)
    other_value = getattr(right, "value", None)
    if isinstance(other_value, (int, float)):
        return _lt(left.value, other_value)
    return NotImplemented


def _add_impl(self: Any, other: object) -> Any:
    """Shared __add__ for integer value types. Returns same type as self."""
    if isinstance(other, int) and not isinstance(other, bool):
        return type(self)(self.value + other)
    other_value = getattr(other, "value", None)
    if isinstance(other_value, int):
        return type(self)(self.value + other_value)
    return NotImplemented


def _radd_impl(self: Any, other: object) -> Any:
    """Shared __radd__ for integer value types."""
    if isinstance(other, int) and not isinstance(other, bool):
        return type(self)(other + self.value)
    return NotImplemented


def _pydantic_value_schema(cls, _source_type, _handler):
    """Shared Pydantic v2 schema: validates raw scalar → cls, serializes as .value."""
    from pydantic_core import core_schema as _cs

    def _validate(v):
        if isinstance(v, cls):
            return v
        return cls(v)

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(lambda instance: instance.value),
    )


def _str_enum_schema(cls, _source_type, _handler):
    """Pydantic v2 schema for StrEnum: validates raw str → cls, passes through members."""
    from pydantic_core import core_schema as _cs

    def _validate(v):
        if isinstance(v, cls):
            return v
        if not isinstance(v, str):
            raise TypeError(f"expected {cls.__name__} or str")
        return cls(v)

    return _cs.no_info_plain_validator_function(_validate)


def _str_subclass_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    def _validate(v):
        if isinstance(v, cls):
            return v
        return cls(v)

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(str),
    )


def _typed_eq(self: Any, other: object) -> bool:
    """Equality: true if both are value objects with matching value, or against a raw scalar."""
    if isinstance(other, (int, float)) and not isinstance(other, bool):
        return self.value == other
    other_value = getattr(other, "value", None)
    if isinstance(other_value, (int, float)):
        return self.value == other_value
    return NotImplemented


@total_ordering
@dataclass(frozen=True, slots=True)
class PositiveIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 1)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, int.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class NonNegativeIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 0)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, int.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class PositiveFiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        if _number(self.value, self.validation_name) <= 0:
            raise ValueError(f"{self.validation_name} must be positive")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value


@total_ordering
@dataclass(frozen=True, slots=True)
class NonNegativeFiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        if _number(self.value, self.validation_name) < 0:
            raise ValueError(f"{self.validation_name} must be non-negative")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class OpenUnitIntervalValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        value = _number(self.value, self.validation_name)
        if not 0 < value < 1:
            raise ValueError(f"{self.validation_name} must be in (0, 1)")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class ClosedUnitIntervalValue:
    value: float
    validation_name: ClassVar[str] = "value"

    def __post_init__(self) -> None:
        value = _number(self.value, self.validation_name)
        if not 0 <= value <= 1:
            raise ValueError(f"{self.validation_name} must be in [0, 1]")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value


class Seed(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "seed"


class Ratio(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "ratio"


class Quantile(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "quantile"


class CoverageTarget(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "coverage target"


class CalibrationSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "calibration size"


class ClientCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "client count"


class SeedCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "seed count"


class RoundNumber(PositiveIntegerValue):
    validation_name: ClassVar[str] = "round number"


class LocalEpochCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "local epoch count"


class BatchSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "batch size"


class BootstrapReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "bootstrap replicate count"


class SubsampleReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "subsample replicate count"


class GroupCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "group count"


class ReplicateIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "replicate index"


class ClusterIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "cluster index"


class KMeansInitializationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means initialization count"


class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means maximum iteration count"


class ByteCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "byte count"


class LearningRate(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "learning rate"


class WeightDecay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "weight decay"


class DataLoaderWorkerCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "data loader worker count"


class WorkerCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "worker count"


class FeatureCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "feature count"


class RowCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "row count"


class FeatureName(str):
    def __new__(cls, value: str) -> "FeatureName":
        if not isinstance(value, str) or not value:
            raise ValueError("feature name must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


class OutcomeLabel(str):
    def __new__(cls, value: str) -> "OutcomeLabel":
        if not isinstance(value, str) or not value:
            raise ValueError("outcome label must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


class StableRowId(str):
    def __new__(cls, value: str) -> "StableRowId":
        if not isinstance(value, str) or not value:
            raise ValueError("stable row ID must be a non-empty string")
        if "/" in value or "\\" in value:
            raise ValueError("stable row ID must not contain path separators")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


def _validate_non_empty_tuple(values: tuple, field_name: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field_name} requires a non-empty tuple")


def _validate_unique(values: tuple, field_name: str) -> None:
    if len(frozenset(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")


def _sequence_pydantic_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    def _validate(v):
        if isinstance(v, cls):
            return v
        if isinstance(v, (list, tuple)):
            return cls(tuple(v))
        raise ValueError(f"expected sequence, got {type(v)}")

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(list),
    )


@dataclass(frozen=True, slots=True)
class FeatureNameSequence:
    names: tuple[FeatureName, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, FeatureName) else FeatureName(item) for item in self.names)
        object.__setattr__(self, "names", wrapped)
        _validate_non_empty_tuple(self.names, "feature name sequence")
        _validate_unique(self.names, "feature names")

    def __len__(self) -> int:
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def as_list(self) -> list[str]:
        return list(self.names)

    __get_pydantic_core_schema__ = classmethod(_sequence_pydantic_schema)


@dataclass(frozen=True, slots=True)
class OutcomeLabelSequence:
    labels: tuple[OutcomeLabel, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.labels, tuple):
            raise TypeError("outcome labels must be an immutable tuple")
        wrapped = tuple(item if isinstance(item, OutcomeLabel) else OutcomeLabel(item) for item in self.labels)
        object.__setattr__(self, "labels", wrapped)

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)


@dataclass(frozen=True, slots=True)
class StableRowIdSequence:
    row_ids: tuple[StableRowId, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, StableRowId) else StableRowId(item) for item in self.row_ids)
        object.__setattr__(self, "row_ids", wrapped)
        _validate_non_empty_tuple(self.row_ids, "stable row ID sequence")
        _validate_unique(self.row_ids, "stable row IDs")

    def __len__(self) -> int:
        return len(self.row_ids)

    def __iter__(self):
        return iter(self.row_ids)

    __get_pydantic_core_schema__ = classmethod(_sequence_pydantic_schema)


class AbsoluteTolerance(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "absolute tolerance"


class DirichletConcentration(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "Dirichlet concentration"


class ProximalCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "proximal coefficient"


class DittoRegularization(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "Ditto regularization"


class ModelCoefficientValue(NonNegativeFiniteFloatValue):
    """Serialized form of either ProximalCoefficient or DittoRegularization at manifest boundaries."""

    validation_name: ClassVar[str] = "model coefficient value"


class ShrinkageWeight(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "shrinkage weight"


class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "summary coefficient"


class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "confidence level"


@total_ordering
@dataclass(frozen=True, slots=True)
class ThresholdValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "threshold")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value


@total_ordering
@dataclass(frozen=True, slots=True)
class ScoreValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "score")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value


@total_ordering
@dataclass(frozen=True, slots=True)
class MetricValue:
    value: float

    def __post_init__(self) -> None:
        _number(self.value, "metric")

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other, float.__lt__)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


class TrafficRatePerDay(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "traffic rate"


@dataclass(frozen=True, slots=True)
class Checksum:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("checksum must be non-empty")
        object.__setattr__(self, "value", self.value.strip().lower())

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class ClientPathToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client path token must be non-empty")
        if self.value in {".", ".."} or any(token in self.value for token in ("=", "/", "\\")):
            raise ValueError("client path token must be a single non-relative path segment without key=value syntax")

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("family identity must be non-empty")


class SafeTensorFilename(str):
    def __new__(cls, value: str) -> "SafeTensorFilename":
        if not isinstance(value, str) or not value:
            raise ValueError("SafeTensors filename must be non-empty")
        if not value.endswith(".safetensors"):
            raise ValueError("SafeTensors filename must end with .safetensors")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


class ManifestSchemaVersion(PositiveIntegerValue):
    validation_name: ClassVar[str] = "manifest schema version"


class CudaDeviceName(str):
    def __new__(cls, value: str) -> "CudaDeviceName":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("CUDA device name must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


def checksum_text(payload: str) -> Checksum:
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_bytes(payload: bytes) -> Checksum:
    return Checksum(sha256(payload).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())
