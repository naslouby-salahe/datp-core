"""Dagster resources, assets, jobs, and definitions over pipeline workflows."""

from dagster import AssetSelection, ConfigurableResource, Definitions, asset, define_asset_job

from datp_core.pipeline.execution.engine import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan
from datp_core.pipeline.workflows.confirmatory import analyze_confirmatory_campaign, run_confirmatory_campaign
from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT


class PipelinePaths(ConfigurableResource["PipelinePaths"]):
    data_root: str
    outputs_root: str


PIPELINE_PATHS = PipelinePaths(data_root=str(DATA_ROOT), outputs_root=str(OUTPUTS_ROOT))


@asset
def deterministic_plan() -> str:
    plan = expand_experiment_plan()
    campaign = build_campaign(plan)
    return f"{plan.digest}:{campaign.digest.value}"


@asset(deps=["deterministic_plan"])
def confirmatory_campaign() -> list[str]:
    result = run_confirmatory_campaign()
    return [
        f"{seed.training_seed.value}:{method.value}"
        for seed in result.seeds
        for method in seed.completed_threshold_methods
    ]


@asset
def confirmatory_evidence(confirmatory_campaign: list[str]) -> str:
    if not confirmatory_campaign:
        raise ValueError("confirmatory evidence requires completed threshold evaluations")
    return str(analyze_confirmatory_campaign())


PLAN_JOB = define_asset_job(
    "datp_core_plan",
    selection=AssetSelection.assets("deterministic_plan"),
)
CONFIRMATORY_JOB = define_asset_job(
    "datp_core_confirmatory",
    selection=AssetSelection.assets(
        "deterministic_plan",
        "confirmatory_campaign",
        "confirmatory_evidence",
    ),
)

DEFINITIONS = Definitions(
    assets=(deterministic_plan, confirmatory_campaign, confirmatory_evidence),
    jobs=(PLAN_JOB, CONFIRMATORY_JOB),
    resources={"paths": PIPELINE_PATHS},
)
