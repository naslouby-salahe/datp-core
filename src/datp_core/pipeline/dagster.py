"""Dagster resources, assets, jobs, and definitions over pipeline workflows."""

from pathlib import Path

from dagster import AssetSelection, ConfigurableResource, Definitions, asset, define_asset_job

from datp_core.domain.enums import ExperimentId, PopulationId
from datp_core.pipeline.execution.engine import plan_and_build_campaign
from datp_core.pipeline.workflows.centralized import run_centralized_reference_seed
from datp_core.pipeline.workflows.confirmatory import (
    analyze_confirmatory_campaign,
    load_fedavg_cv_fpr_effect,
    run_confirmatory_campaign,
)
from datp_core.pipeline.workflows.external import (
    analyze_ciciot_boundary_campaign,
    analyze_external_validation_campaign,
    run_ciciot_boundary_seed,
    run_external_validation_seed,
)
from datp_core.pipeline.workflows.personalization import (
    analyze_fedprox_absorption,
    build_fedprox_absorption_observation,
    run_ditto_absorption_campaign,
    run_ditto_stress_test_seed,
    run_fedprox_coefficient_campaign,
)
from datp_core.pipeline.workflows.temporal import run_temporal_campaign
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import DITTO_PRIMARY_REGULARIZATION, FEDPROX_COEFFICIENTS
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT

_FEDPROX_PRIMARY_COEFFICIENT = FEDPROX_COEFFICIENTS[0]


class PipelinePaths(ConfigurableResource["PipelinePaths"]):
    data_root: str
    outputs_root: str

    @property
    def data_root_path(self) -> Path:
        return Path(self.data_root)

    @property
    def outputs_root_path(self) -> Path:
        return Path(self.outputs_root)


PIPELINE_PATHS = PipelinePaths(data_root=str(DATA_ROOT), outputs_root=str(OUTPUTS_ROOT))


@asset
def deterministic_plan(paths: PipelinePaths) -> str:
    _ = paths.data_root_path, paths.outputs_root_path
    plan, campaign = plan_and_build_campaign()
    return f"{plan.digest.value}:{campaign.digest.value}"


@asset(deps=["deterministic_plan"])
def confirmatory_campaign(paths: PipelinePaths) -> list[str]:
    _ = paths.outputs_root_path
    result = run_confirmatory_campaign()
    return [
        f"{seed.training_seed.value}:{method.value}"
        for seed in result.seeds
        for method in seed.completed_threshold_methods
    ]


@asset
def confirmatory_evidence(confirmatory_campaign: list[str], paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    if not confirmatory_campaign:
        raise ValueError("confirmatory evidence requires completed threshold evaluations")
    return str(analyze_confirmatory_campaign())


@asset(deps=["deterministic_plan"])
def centralized_reference_seed(paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    seed = CONFIRMATORY_SEED_COHORT.values[0]
    result = run_centralized_reference_seed(training_seed=seed)
    return f"{seed.value}:{result.complete_digest.value}"


@asset(deps=["deterministic_plan"])
def ditto_stress_campaign(paths: PipelinePaths) -> int:
    _ = paths.outputs_root_path
    results = tuple(
        run_ditto_stress_test_seed(
            training_seed=seed,
            regularization=DITTO_PRIMARY_REGULARIZATION,
        )
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    return len(results)


@asset
def ditto_absorption_evidence(ditto_stress_campaign: int, paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    if ditto_stress_campaign < 1:
        raise ValueError("ditto absorption requires completed stress-test seeds")
    cohort = run_ditto_absorption_campaign(regularization=DITTO_PRIMARY_REGULARIZATION)
    return cohort.decision.decision.value


@asset(deps=["deterministic_plan"])
def fedprox_stress_campaign(paths: PipelinePaths) -> int:
    _ = paths.outputs_root_path
    results = run_fedprox_coefficient_campaign(coefficient=_FEDPROX_PRIMARY_COEFFICIENT)
    return len(results)


@asset
def fedprox_absorption_evidence(fedprox_stress_campaign: int, paths: PipelinePaths) -> str:
    if fedprox_stress_campaign < 1:
        raise ValueError("fedprox absorption requires completed stress-test seeds")
    experiment = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
    observations = tuple(
        build_fedprox_absorption_observation(
            training_seed=seed,
            coefficient=_FEDPROX_PRIMARY_COEFFICIENT,
            reference=load_fedavg_cv_fpr_effect(seed, experiment=experiment),
        )
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    output = (
        paths.outputs_root_path
        / "fedprox_stress_test"
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / "analysis"
        / str(_FEDPROX_PRIMARY_COEFFICIENT.value)
    )
    cohort = analyze_fedprox_absorption(observations, output_directory=output)
    return cohort.decision.decision.value


@asset(deps=["deterministic_plan"])
def temporal_evidence_campaign(paths: PipelinePaths) -> int:
    _ = paths.outputs_root_path
    result = run_temporal_campaign()
    return len(result.seeds)


@asset(deps=["deterministic_plan"])
def edge_benign_equity_seed(paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    seed = BOUNDED_EVIDENCE_SEED_COHORT.values[0]
    result = run_external_validation_seed(seed)
    return f"{seed.value}:{','.join(item.value for item in result.completed_threshold_methods)}"


@asset
def edge_benign_equity_analysis(edge_benign_equity_seed: str, paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    if not edge_benign_equity_seed:
        raise ValueError("edge equity analysis requires a completed seed")
    return str(analyze_external_validation_campaign().output_directory)


@asset(deps=["deterministic_plan"])
def ciciot_boundary_seed(paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    seed = BOUNDED_EVIDENCE_SEED_COHORT.values[0]
    result = run_ciciot_boundary_seed(seed)
    return f"{seed.value}:{','.join(item.value for item in result.completed_threshold_methods)}"


@asset
def ciciot_boundary_analysis(ciciot_boundary_seed: str, paths: PipelinePaths) -> str:
    _ = paths.outputs_root_path
    if not ciciot_boundary_seed:
        raise ValueError("ciciot boundary analysis requires a completed seed")
    return str(analyze_ciciot_boundary_campaign().output_directory)


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
STRESS_JOB = define_asset_job(
    "datp_core_training_stress",
    selection=AssetSelection.assets(
        "deterministic_plan",
        "ditto_stress_campaign",
        "ditto_absorption_evidence",
        "fedprox_stress_campaign",
        "fedprox_absorption_evidence",
    ),
)
EXTERNAL_TEMPORAL_JOB = define_asset_job(
    "datp_core_external_temporal",
    selection=AssetSelection.assets(
        "deterministic_plan",
        "temporal_evidence_campaign",
        "edge_benign_equity_seed",
        "edge_benign_equity_analysis",
        "ciciot_boundary_seed",
        "ciciot_boundary_analysis",
        "centralized_reference_seed",
    ),
)

DEFINITIONS = Definitions(
    assets=(
        deterministic_plan,
        confirmatory_campaign,
        confirmatory_evidence,
        centralized_reference_seed,
        ditto_stress_campaign,
        ditto_absorption_evidence,
        fedprox_stress_campaign,
        fedprox_absorption_evidence,
        temporal_evidence_campaign,
        edge_benign_equity_seed,
        edge_benign_equity_analysis,
        ciciot_boundary_seed,
        ciciot_boundary_analysis,
    ),
    jobs=(PLAN_JOB, CONFIRMATORY_JOB, STRESS_JOB, EXTERNAL_TEMPORAL_JOB),
    resources={"paths": PIPELINE_PATHS},
)
