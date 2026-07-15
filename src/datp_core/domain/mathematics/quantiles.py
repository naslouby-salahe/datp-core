from math import ceil, isfinite

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.thresholding.policies import FprTarget, ThresholdPercentile


def _validated_positive_weight(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainValidationError(
            detail="exact weighted quantile weights must be integers", value=repr(value), constraint="integer weights"
        )
    if value < 1:
        raise DomainValidationError(
            detail="exact weighted quantile weights must be positive integers",
            value=repr(value),
            constraint="positive integer weights",
        )


def fpr_target(*, percentile: ThresholdPercentile) -> FprTarget:
    return FprTarget.from_percentile(percentile=percentile)


def exact_quantile(*, values: tuple[float, ...], percentile: ThresholdPercentile) -> float:
    if not values or any(not isfinite(value) for value in values):
        raise DomainValidationError(
            detail="exact quantile requires at least one finite value",
            value=repr(values),
            constraint="non-empty finite numeric tuple",
        )
    ordered_values = tuple(sorted(values))
    index = ceil(percentile.value * len(ordered_values)) - 1
    return ordered_values[index]


def exact_weighted_quantile(
    *,
    values: tuple[float, ...],
    weights: tuple[int, ...],
    percentile: ThresholdPercentile,
) -> float:
    _validated_weighted_inputs(values=values, weights=weights)
    ordered_pairs = tuple(sorted(zip(values, weights, strict=True)))
    required_rank = ceil(percentile.value * sum(weights))
    return _value_at_weighted_rank(ordered_pairs=ordered_pairs, required_rank=required_rank)


def _validated_weighted_inputs(*, values: tuple[float, ...], weights: tuple[int, ...]) -> None:
    _validated_paired_finite_values(values=values, weights=weights)
    _validated_weights(weights)


def _validated_paired_finite_values(*, values: tuple[float, ...], weights: tuple[int, ...]) -> None:
    if len(values) != len(weights):
        raise DomainValidationError(
            detail="exact weighted quantile requires paired values and weights",
            value=repr((values, weights)),
            constraint="equal-length values and weights",
        )
    if not values:
        raise DomainValidationError(
            detail="exact weighted quantile requires values", value=repr(values), constraint="non-empty values"
        )
    if any(not isfinite(value) for value in values):
        raise DomainValidationError(
            detail="exact weighted quantile requires paired finite values and weights",
            value=repr((values, weights)),
            constraint="finite values",
        )


def _validated_weights(weights: tuple[int, ...]) -> None:
    for weight in weights:
        _validated_positive_weight(weight)


def _value_at_weighted_rank(*, ordered_pairs: tuple[tuple[float, int], ...], required_rank: int) -> float:
    cumulative_weight = 0
    for value, weight in ordered_pairs:
        cumulative_weight += weight
        if cumulative_weight >= required_rank:
            return value
    raise AssertionError("positive weighted quantile rank must select a value")
