from dataclasses import dataclass
from math import isfinite

from datp_core.domain.errors import DomainValidationError


def _validated_integer(*, value: object, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if value < minimum:
        raise DomainValidationError(
            detail=f"{name} must be an integer greater than or equal to {minimum}",
            value=repr(value),
            constraint=f"integer >= {minimum}",
        )


def _validated_finite_float(*, value: object, name: str, minimum: float, inclusive: bool) -> float:
    numeric_value = _parsed_float(value=_validated_float_input(value=value, name=name), name=name)
    if not isfinite(numeric_value):
        raise DomainValidationError(detail=f"{name} must be finite", value=repr(value), constraint="finite value")
    _validated_numeric_lower_bound(value=numeric_value, name=name, minimum=minimum, inclusive=inclusive)
    return numeric_value


def _validated_float_input(*, value: object, name: str) -> float | int | str:
    if isinstance(value, bool) or not isinstance(value, (float, int, str)):
        raise DomainValidationError(
            detail=f"{name} must be a finite number",
            value=repr(value),
            constraint="finite numeric value",
        )
    return value


def _parsed_float(*, value: float | int | str, name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as error:
        raise DomainValidationError(
            detail=f"{name} must be a finite number",
            value=repr(value),
            constraint="finite numeric value",
        ) from error
    return numeric_value


def _validated_numeric_lower_bound(*, value: float, name: str, minimum: float, inclusive: bool) -> None:
    if inclusive and value >= minimum:
        return
    if not inclusive and value > minimum:
        return
    operator = ">=" if inclusive else ">"
    raise DomainValidationError(
        detail=f"{name} must be finite and {operator} {minimum}",
        value=repr(value),
        constraint=f"finite value {operator} {minimum}",
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class BatchSize:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="batch size", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class GradientAccumulationSteps:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="gradient accumulation steps", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerCount:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="worker count", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class ChunkRowCount:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="chunk row count", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class RamBudgetBytes:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="RAM budget bytes", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class VramBudgetBytes:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="VRAM budget bytes", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class DiskBudgetBytes:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="disk budget bytes", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class PrefetchCapacity:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="prefetch capacity", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class CsvBlockBytes:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="CSV block bytes", minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class VramFraction:
    value: float

    def __post_init__(self) -> None:
        numeric_value = _validated_finite_float(
            value=self.value,
            name="VRAM fraction",
            minimum=0.0,
            inclusive=False,
        )
        if numeric_value > 1.0:
            raise DomainValidationError(
                detail="VRAM fraction must not exceed one",
                value=repr(self.value),
                constraint="0 < VRAM fraction <= 1",
            )
        object.__setattr__(self, "value", numeric_value)


@dataclass(frozen=True, slots=True, kw_only=True)
class GpuIndex:
    value: int

    def __post_init__(self) -> None:
        _validated_integer(value=self.value, name="GPU index", minimum=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class NumericTolerance:
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validated_finite_float(
                value=self.value,
                name="numeric tolerance",
                minimum=0.0,
                inclusive=False,
            ),
        )
