"""Demand-driven stage job derivation and seed expansion logic."""

from __future__ import annotations

from datp_core.domain.artifacts import ArtifactId, ArtifactKey, ArtifactKind
from datp_core.domain.catalogue import ExperimentRecord, ResolvedCatalogue
from datp_core.domain.identifiers import JobId
from datp_core.domain.outcomes import StageJob, StageKind
from datp_core.planning.graph import PlanningGraph


def expand_experiment_jobs(
    experiment: ExperimentRecord,
    catalogue: ResolvedCatalogue,
) -> PlanningGraph:
    seed_cohort = catalogue.seed_cohorts.get(experiment.seed_cohort_id)
    jobs: list[StageJob] = []

    # 1. Preflight check job
    preflight_job_id = JobId(value=f"{experiment.identifier.value}:preflight")
    preflight_out = ArtifactKey(
        artifact_id=ArtifactId(value=f"{experiment.identifier.value}:preflight_status"),
        kind=ArtifactKind.RESOLVED_CONFIG,
    )
    preflight_job = StageJob(
        job_id=preflight_job_id,
        stage=StageKind.PREFLIGHT,
        inputs=(),
        output=preflight_out,
        dependencies=(),
    )
    jobs.append(preflight_job)

    # 2. Derive jobs per seed
    for seed in seed_cohort.seeds:
        seed_str = str(seed.value)
        # Materialization job
        mat_job_id = JobId(value=f"{experiment.identifier.value}:seed_{seed_str}:mat")
        mat_output = ArtifactKey(
            artifact_id=ArtifactId(value=f"{experiment.identifier.value}:seed_{seed_str}:mat_data"),
            kind=ArtifactKind.MATERIALIZED_DATASET,
        )
        mat_job = StageJob(
            job_id=mat_job_id,
            stage=StageKind.DATASET_MATERIALIZATION,
            inputs=(preflight_job.output,),
            output=mat_output,
            dependencies=(preflight_job_id,),
        )
        jobs.append(mat_job)

        # Model Training job
        train_job_id = JobId(value=f"{experiment.identifier.value}:seed_{seed_str}:train")
        train_output = ArtifactKey(
            artifact_id=ArtifactId(value=f"{experiment.identifier.value}:seed_{seed_str}:checkpoint"),
            kind=ArtifactKind.MODEL_CHECKPOINT,
        )
        train_job = StageJob(
            job_id=train_job_id,
            stage=StageKind.MODEL_TRAINING,
            inputs=(mat_output,),
            output=train_output,
            dependencies=(mat_job_id,),
        )
        jobs.append(train_job)

        # Score Generation job
        score_job_id = JobId(value=f"{experiment.identifier.value}:seed_{seed_str}:scores")
        score_output = ArtifactKey(
            artifact_id=ArtifactId(value=f"{experiment.identifier.value}:seed_{seed_str}:scores_data"),
            kind=ArtifactKind.CALIBRATION_SCORES,
        )
        score_job = StageJob(
            job_id=score_job_id,
            stage=StageKind.SCORE_GENERATION,
            inputs=(train_output, mat_output),
            output=score_output,
            dependencies=(train_job_id,),
        )
        jobs.append(score_job)

        # Threshold Construction & Evaluation jobs per evaluation spec
        for eval_spec in experiment.evaluations:
            thresh_job_id = JobId(value=f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:thresh")
            thresh_output = ArtifactKey(
                artifact_id=ArtifactId(value=f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:threshold_set"),
                kind=ArtifactKind.THRESHOLDS,
            )
            thresh_job = StageJob(
                job_id=thresh_job_id,
                stage=StageKind.THRESHOLD_CONSTRUCTION,
                inputs=(score_output,),
                output=thresh_output,
                dependencies=(score_job_id,),
            )
            jobs.append(thresh_job)

            eval_job_id = JobId(value=f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:eval")
            eval_output = ArtifactKey(
                artifact_id=ArtifactId(value=f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:metrics"),
                kind=ArtifactKind.CLIENT_METRICS,
            )
            eval_job = StageJob(
                job_id=eval_job_id,
                stage=StageKind.OPERATING_POINT_EVALUATION,
                inputs=(thresh_output, score_output),
                output=eval_output,
                dependencies=(thresh_job_id,),
            )
            jobs.append(eval_job)

    planning_graph = PlanningGraph(tuple(jobs))
    planning_graph.validate_acyclic()
    return planning_graph
