"""Detector campaign asset delegated to canonical pipeline execution."""

from dagster import asset

from datp_core.pipeline.confirmatory import run_confirmatory_campaign


@asset(deps=["deterministic_plan"])
def confirmatory_campaign() -> list[str]:
    result = run_confirmatory_campaign()
    return [
        f"{seed.training_seed.value}:{method.value}"
        for seed in result.seeds
        for method in seed.completed_threshold_methods
    ]
