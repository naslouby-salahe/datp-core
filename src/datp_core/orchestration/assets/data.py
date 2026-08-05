"""Data and planning assets delegated to the pipeline."""

from dagster import asset

from datp_core.pipeline.campaign_execution import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan


@asset
def deterministic_plan() -> str:
    plan = expand_experiment_plan()
    campaign = build_campaign(plan)
    return f"{plan.digest}:{campaign.digest.value}"
