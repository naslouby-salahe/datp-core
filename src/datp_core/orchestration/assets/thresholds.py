"""Threshold completion projection with no scientific calculation."""

from dagster import asset


@asset
def completed_thresholds(confirmatory_campaign: list[str]) -> list[str]:
    return list(confirmatory_campaign)
