"""Dagster jobs selecting thin pipeline-backed assets."""

from dagster import AssetSelection, define_asset_job

PLAN_JOB = define_asset_job(
    "datp_core_plan",
    selection=AssetSelection.assets("deterministic_plan"),
)
CONFIRMATORY_JOB = define_asset_job(
    "datp_core_confirmatory",
    selection=AssetSelection.assets(
        "deterministic_plan",
        "confirmatory_campaign",
        "completed_thresholds",
        "confirmatory_evidence",
    ),
)
