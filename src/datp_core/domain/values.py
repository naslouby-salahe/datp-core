"""Validated scalar scientific values."""

from dataclasses import dataclass
from functools import total_ordering
from hashlib import file_digest, sha256
from math import isclose, isfinite
from pathlib import Path
from types import NotImplementedType
from typing import Callable, ClassVar, cast

NUMERIC_ZERO: float = 0.0
NO_RELATIVE_TOLERANCE: float = 0.0


def floats_absolutely_close(left: float, right: float, absolute_tolerance: float) -> bool:
    """Compare floats with an explicit absolute tolerance and zero relative tolerance."""
    if absolute_tolerance < NUMERIC_ZERO:
        raise ValueError("absolute tolerance must be non-negative")
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance)


def floats_exactly_equal(left: float, right: float) -> bool:
    """Compare floats at full precision with no tolerance band."""
    return isclose(left, right, rel_tol=NO_RELATIVE_TOLERANCE, abs_tol=NUMERIC_ZERO)


def is_numeric_zero(value: float) -> bool:
    return floats_exactly_equal(value, NUMERIC_ZERO)


def _integer(value: int, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number(value: int | float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


NumericValue = int | float


def _numeric_value(instance: object) -> NumericValue:
    value = getattr(instance, "value", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{type(instance).__name__} does not expose a numeric value")
    return value


def _compatible_value(self: object, other: object) -> NumericValue | NotImplementedType:
    if isinstance(other, (int, float)) and not isinstance(other, bool):
        return other
    if type(other) is type(self):
        return _numeric_value(other)
    family = getattr(self, "comparison_family", None)
    if family is not None and getattr(other, "comparison_family", None) == family:
        return _numeric_value(other)
    return NotImplemented


def _ordering_compare(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) < other_value


def _typed_eq(self: object, other: object) -> bool | NotImplementedType:
    other_value = _compatible_value(self, other)
    if other_value is NotImplemented:
        return NotImplemented
    return _numeric_value(self) == other_value


def _integer_constructor(instance: object) -> Callable[[int], object]:
    return cast(Callable[[int], object], type(instance))


def _add_impl(self: object, other: object) -> object | NotImplementedType:
    self_value = _numeric_value(self)
    if not isinstance(self_value, int):
        return NotImplemented
    constructor = _integer_constructor(self)
    if isinstance(other, int) and not isinstance(other, bool):
        return constructor(self_value + other)
    if type(other) is type(self):
        other_value = _numeric_value(other)
        return constructor(self_value + int(other_value))
    return NotImplemented


def _radd_impl(self: object, other: object) -> object | NotImplementedType:
    self_value = _numeric_value(self)
    if isinstance(self_value, int) and isinstance(other, int) and not isinstance(other, bool):
        return _integer_constructor(self)(other + self_value)
    return NotImplemented


def _pydantic_value_schema(cls, _source_type, _handler):
    """Validate a raw scalar into a value object and serialize its scalar value."""
    from pydantic_core import core_schema as _cs

    def _validate(value):
        return value if isinstance(value, cls) else cls(value)

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(lambda instance: instance.value),
    )


def _str_enum_schema(cls, _source_type, _handler):
    """Validate a raw string into a StrEnum member."""
    from pydantic_core import core_schema as _cs

    def _validate(value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"expected {cls.__name__} or str")
        return cls(value)

    return _cs.no_info_plain_validator_function(_validate)


def _str_subclass_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    def _validate(value):
        return value if isinstance(value, cls) else cls(value)

    return _cs.no_info_plain_validator_function(
        _validate,
        serialization=_cs.plain_serializer_function_ser_schema(str),
    )


@total_ordering
@dataclass(frozen=True, slots=True)
class PositiveIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 1)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class NonNegativeIntegerValue:
    value: int
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        _integer(self.value, self.validation_name, 0)

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    __add__ = _add_impl
    __radd__ = _radd_impl
    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


@total_ordering
@dataclass(frozen=True, slots=True)
class FiniteFloatValue:
    value: float
    validation_name: ClassVar[str] = "value"
    comparison_family: ClassVar[str | None] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _number(self.value, self.validation_name))

    def __lt__(self, other: object) -> bool:
        return _ordering_compare(self, other)

    def __eq__(self, other: object) -> bool:
        return _typed_eq(self, other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __float__(self) -> float:
        return self.value

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


class PositiveFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value <= 0:
            raise ValueError(f"{self.validation_name} must be positive")


class NonNegativeFiniteFloatValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value < 0:
            raise ValueError(f"{self.validation_name} must be non-negative")


class OpenUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 < self.value < 1:
            raise ValueError(f"{self.validation_name} must be in (0, 1)")


class ClosedUnitIntervalValue(FiniteFloatValue):
    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 <= self.value <= 1:
            raise ValueError(f"{self.validation_name} must be in [0, 1]")


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
    comparison_family: ClassVar[str | None] = "row_count"


class ClientCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "client count"
    comparison_family: ClassVar[str | None] = "population_cardinality"


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
    comparison_family: ClassVar[str | None] = "population_cardinality"


class ReplicateIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "replicate index"


class ConformalRankIndex(PositiveIntegerValue):
    validation_name: ClassVar[str] = "conformal rank index"


class ClusterIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "cluster index"


class KMeansInitializationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means initialization count"


class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means maximum iteration count"


class ByteCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "byte count"


class LogicalElementCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "logical element count"


class CudaDeviceCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "CUDA device count"


class ClientPublicationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "client publication count"


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
    comparison_family: ClassVar[str | None] = "row_count"


class _NonEmptyString(str):
    validation_name: ClassVar[str] = "value"

    def __new__(cls, value: str):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{cls.validation_name} must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


class FeatureName(_NonEmptyString):
    validation_name: ClassVar[str] = "feature name"


class OutcomeLabel(_NonEmptyString):
    validation_name: ClassVar[str] = "outcome label"


class StableRowId(_NonEmptyString):
    validation_name: ClassVar[str] = "stable row ID"

    def __new__(cls, value: str) -> "StableRowId":
        instance = super().__new__(cls, value)
        if "/" in instance or "\\" in instance:
            raise ValueError("stable row ID must not contain path separators")
        return instance


def _validate_non_empty_tuple(values: tuple, field_name: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field_name} requires a non-empty tuple")


def _validate_unique(values: tuple, field_name: str) -> None:
    if len(frozenset(values)) != len(values):
        raise ValueError(f"{field_name} must be unique")


def _sequence_pydantic_schema(cls, _source_type, _handler):
    from pydantic_core import core_schema as _cs

    def _validate(value):
        if isinstance(value, cls):
            return value
        if isinstance(value, (list, tuple)):
            return cls(tuple(value))
        raise ValueError(f"expected sequence, got {type(value)}")

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
        object.__setattr__(
            self,
            "labels",
            tuple(item if isinstance(item, OutcomeLabel) else OutcomeLabel(item) for item in self.labels),
        )

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)

    __get_pydantic_core_schema__ = classmethod(_sequence_pydantic_schema)


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


NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE = AbsoluteTolerance(1e-12)


class DirichletConcentration(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "Dirichlet concentration"


class ProximalCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "proximal coefficient"


class DittoRegularization(NonNegativeFiniteFloatValue):
    validation_name: ClassVar[str] = "Ditto regularization"


class ModelCoefficientValue(NonNegativeFiniteFloatValue):
    """Serialized form of a proximal or Ditto coefficient at manifest boundaries."""

    validation_name: ClassVar[str] = "model coefficient value"


class ShrinkageWeight(ClosedUnitIntervalValue):
    validation_name: ClassVar[str] = "shrinkage weight"


class SummaryCoefficient(PositiveFiniteFloatValue):
    validation_name: ClassVar[str] = "summary coefficient"


class ConfidenceLevel(OpenUnitIntervalValue):
    validation_name: ClassVar[str] = "confidence level"


class ThresholdValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "threshold"
    comparison_family: ClassVar[str | None] = "anomaly_score"


class ScoreValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "score"
    comparison_family: ClassVar[str | None] = "anomaly_score"


class MetricValue(FiniteFloatValue):
    validation_name: ClassVar[str] = "metric"


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

    __get_pydantic_core_schema__ = classmethod(_pydantic_value_schema)


class SafeTensorFilename(_NonEmptyString):
    validation_name: ClassVar[str] = "SafeTensors filename"

    def __new__(cls, value: str) -> "SafeTensorFilename":
        instance = super().__new__(cls, value)
        if not instance.endswith(".safetensors"):
            raise ValueError("SafeTensors filename must end with .safetensors")
        return instance


class ManifestSchemaVersion(PositiveIntegerValue):
    validation_name: ClassVar[str] = "manifest schema version"


class CudaDeviceName(_NonEmptyString):
    validation_name: ClassVar[str] = "CUDA device name"

    def __new__(cls, value: str) -> "CudaDeviceName":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("CUDA device name must be a non-empty string")
        return str.__new__(cls, value)


def checksum_text(payload: str) -> Checksum:
    return Checksum(sha256(payload.encode()).hexdigest())


def checksum_bytes(payload: bytes) -> Checksum:
    return Checksum(sha256(payload).hexdigest())


def checksum_file(path: Path) -> Checksum:
    with path.open("rb") as source:
        return Checksum(file_digest(source, "sha256").hexdigest())
