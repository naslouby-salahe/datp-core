from math import isfinite

from datp_core.domain.errors import DomainValidationError


def _validated_sample(values: tuple[float, ...], *, name: str) -> None:
    if not values:
        raise DomainValidationError(
            detail="Cliff's delta requires non-empty samples", value=name, constraint="non-empty sample"
        )
    if any(not isfinite(value) for value in values):
        raise DomainValidationError(
            detail="Cliff's delta requires finite samples", value=name, constraint="finite sample"
        )


def _pairwise_wins(sample_a: tuple[float, ...], sample_b: tuple[float, ...]) -> tuple[int, int]:
    return (
        sum(value_a > value_b for value_a in sample_a for value_b in sample_b),
        sum(value_a < value_b for value_a in sample_a for value_b in sample_b),
    )


def cliffs_delta(*, sample_a: tuple[float, ...], sample_b: tuple[float, ...]) -> float:
    _validated_sample(sample_a, name="sample_a")
    _validated_sample(sample_b, name="sample_b")
    favorable_a, favorable_b = _pairwise_wins(sample_a, sample_b)
    return (favorable_a - favorable_b) / (len(sample_a) * len(sample_b))
