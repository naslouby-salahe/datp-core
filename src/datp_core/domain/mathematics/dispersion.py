from dataclasses import dataclass
from math import fsum, isfinite, sqrt

from datp_core.domain.errors import DomainValidationError


def _validated_finite_values(*, values: tuple[float, ...], name: str) -> None:
    if not values or any(not isfinite(value) for value in values):
        raise DomainValidationError(
            detail=f"{name} requires at least one finite value",
            value=repr(values),
            constraint="non-empty finite numeric tuple",
        )


def _validated_positive_integer(value: object, *, name: str) -> None:
    if not isinstance(value, int):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if isinstance(value, bool):
        raise DomainValidationError(detail=f"{name} must be an integer", value=repr(value), constraint="integer")
    if value < 1:
        raise DomainValidationError(
            detail=f"{name} must be a positive integer",
            value=repr(value),
            constraint="integer >= 1",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DefinedCvFpr:
    value: float


@dataclass(frozen=True, slots=True, kw_only=True)
class UndefinedCvFpr:
    mean_value: float


type CvFprOutcome = DefinedCvFpr | UndefinedCvFpr


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMoment:
    sample_count: int
    mean: float
    variance: float

    def __post_init__(self) -> None:
        _validated_positive_integer(self.sample_count, name="client moment sample count")
        if not isfinite(self.mean) or not isfinite(self.variance):
            raise DomainValidationError(
                detail="client moment mean and variance must be finite",
                value=repr((self.mean, self.variance)),
                constraint="finite mean and variance",
            )
        if self.variance < 0:
            raise DomainValidationError(
                detail="client moment mean and variance must be finite and variance non-negative",
                value=repr((self.mean, self.variance)),
                constraint="finite mean and variance >= 0",
            )


def cv_fpr(*, eligible_fprs: tuple[float, ...]) -> CvFprOutcome:
    _validated_finite_values(values=eligible_fprs, name="CV(FPR)")
    mean_value = fsum(eligible_fprs) / len(eligible_fprs)
    if mean_value == 0:
        return UndefinedCvFpr(mean_value=mean_value)
    variance = fsum((value - mean_value) ** 2 for value in eligible_fprs) / len(eligible_fprs)
    return DefinedCvFpr(value=sqrt(variance) / mean_value)


def pooled_variance(*, client_moments: tuple[ClientMoment, ...]) -> float:
    if not client_moments:
        raise DomainValidationError(
            detail="pooled variance requires at least one client moment",
            value=repr(client_moments),
            constraint="non-empty client moment tuple",
        )
    total_count = sum(moment.sample_count for moment in client_moments)
    global_mean = fsum(moment.sample_count * moment.mean for moment in client_moments) / total_count
    return (
        fsum(moment.sample_count * (moment.variance + (moment.mean - global_mean) ** 2) for moment in client_moments)
        / total_count
    )
