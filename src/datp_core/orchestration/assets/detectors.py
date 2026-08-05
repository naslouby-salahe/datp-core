"""Detector campaign asset delegated to pipeline campaign execution."""

from dagster import asset

from datp_core.pipeline.campaign import run_confirmatory_campaign


@asset(deps=["deterministic_plan"])
def confirmatory_campaign() -> tuple[tuple[int, tuple[str, ...]], ...]:
    return tuple(
        (seed.value, tuple(method.value for method in methods))
        for seed, methods in run_confirmatory_campaign()
    )
