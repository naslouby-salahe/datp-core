"""Deterministic configuration-driven experiment planning without data access."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from ..catalogue.domain import ExperimentDefinition, ResolvedConfiguration
from ..kernel.fingerprints import fingerprint
from ..kernel.ids import ExperimentId, JobId, RegistryId, RunId
from ..kernel.values import StructuredValue
from .domain import ExecutionJob, ExecutionPlan, ExperimentPlan, ScientificRun, SeedPlan, SweepCoordinate


def _mapping(value: StructuredValue | None) -> Mapping[str, StructuredValue]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: StructuredValue | None) -> tuple[StructuredValue, ...]:
    return value if isinstance(value, tuple) else ()


def _integer(value: StructuredValue | None, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{location} must be an integer")
    return value


def expand_sweeps(experiment: ExperimentDefinition) -> tuple[SweepCoordinate, ...]:
    sweeps = _mapping(experiment.values.get("sweeps", {}))
    if not sweeps:
        return (SweepCoordinate(components=()),)
    axes: list[tuple[str, tuple[StructuredValue, ...]]] = []
    for name, raw_axis in sweeps.items():
        axis = _mapping(raw_axis)
        values = axis.get("values")
        if isinstance(values, tuple):
            axes.append((name, values))
            continue
        conditions = axis.get("conditions")
        if isinstance(conditions, tuple):
            axes.append((name, conditions))
            continue
        raise ValueError(f"sweep {name!r} has neither values nor conditions")
    return tuple(
        SweepCoordinate(components=tuple(zip((axis[0] for axis in axes), coordinate, strict=True)))
        for coordinate in product(*(axis[1] for axis in axes))
    )


def _cohort_values(
    configuration: ResolvedConfiguration, identifier: RegistryId[object]
) -> Mapping[str, StructuredValue]:
    return configuration.study.protocols.group("seed_cohorts").get(identifier).values


def plan_experiment(configuration: ResolvedConfiguration, experiment_id: ExperimentId) -> ExperimentPlan:
    experiment = configuration.study.experiments.get(experiment_id)
    coordinates = expand_sweeps(experiment)
    cohort = _cohort_values(configuration, experiment.seed_cohort_id)
    training_seeds = _sequence(cohort.get("training_seeds"))
    if not training_seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in training_seeds):
        raise ValueError(f"seed cohort {experiment.seed_cohort_id} is invalid")
    bootstrap_seed = _integer(cohort.get("bootstrap_analysis_seed"), "bootstrap_analysis_seed")
    historical_profiles = tuple(
        analysis.values.get("statistical_profile")
        for analysis in experiment.analyses
        if analysis.kind == "paired_threshold_analysis"
    )
    if "historical_five_seed_percentile_bootstrap" in historical_profiles:
        profile = configuration.study.protocols.group("statistical_profiles").get(
            RegistryId("historical_five_seed_percentile_bootstrap")
        )
        bootstrap_seed = _integer(profile.values.get("analysis_seed"), "analysis_seed")
    runs: list[ScientificRun] = []
    for coordinate in coordinates:
        for raw_training_seed in training_seeds:
            training_seed = _integer(raw_training_seed, "training_seed")
            seed_plan = SeedPlan(training_seed=training_seed, bootstrap_analysis_seed=bootstrap_seed)
            scientific_fingerprint = fingerprint(
                {
                    "catalogue": configuration.study.catalogue_fingerprint.hexadecimal,
                    "experiment": experiment_id.value,
                    "coordinate": coordinate.components,
                    "seed": training_seed,
                }
            )
            runs.append(
                ScientificRun(
                    run_id=RunId(f"{experiment_id.value}-{len(runs):04d}"),
                    experiment_id=experiment_id,
                    coordinate=coordinate,
                    seed_plan=seed_plan,
                    scientific_fingerprint=scientific_fingerprint,
                )
            )
    return ExperimentPlan(
        experiment=experiment, coordinates=coordinates, runs=tuple(runs), dependency_ids=experiment.prerequisite_ids
    )


def build_execution_plan(plan: ExperimentPlan) -> ExecutionPlan:
    jobs: list[ExecutionJob] = []
    for run in plan.runs:
        parent: tuple[JobId, ...] = ()
        for stage in (
            "materialization",
            "training",
            "checkpoint",
            "scores",
            "thresholds",
            "metrics",
            "analyses",
            "reports",
            "freeze",
        ):
            job_id = JobId(f"{run.run_id.value}-{stage}")
            artifact_key = fingerprint({"run": run.scientific_fingerprint.hexadecimal, "stage": stage})
            jobs.append(
                ExecutionJob(job_id=job_id, stage=stage, parent_job_ids=parent, expected_artifact_key=artifact_key)
            )
            parent = (job_id,)
    plan_fingerprint = fingerprint(tuple((job.job_id.value, job.expected_artifact_key.hexadecimal) for job in jobs))
    return ExecutionPlan(experiment_plan=plan, jobs=tuple(jobs), plan_fingerprint=plan_fingerprint)


def plan_all(configuration: ResolvedConfiguration) -> tuple[ExperimentPlan, ...]:
    return tuple(
        plan_experiment(configuration, identifier) for identifier, _ in configuration.study.experiments.items()
    )
