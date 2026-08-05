"""Detector campaign asset delegated to pipeline campaign execution."""

from dagster import asset

from datp_core.pipeline.campaign import run_confirmatory_campaign


@asset(deps=["deterministic_plan"])
def confirmatory_campaign() -> list[str]:
    return [f"{seed.value}:{method.value}" for seed, methods in run_confirmatory_campaign() for method in methods]
