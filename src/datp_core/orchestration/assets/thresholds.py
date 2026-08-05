"""Threshold completion projection with no scientific calculation."""

from dagster import asset


@asset
def completed_thresholds(
    confirmatory_campaign: tuple[tuple[int, tuple[str, ...]], ...],
) -> tuple[str, ...]:
    return tuple(
        f"{seed}:{method}"
        for seed, methods in confirmatory_campaign
        for method in methods
    )
