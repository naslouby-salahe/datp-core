"""Demand-driven stage job derivation and seed expansion logic."""

from __future__ import annotations

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import ArtifactId, ArtifactKey, ArtifactKind
from datp_core.domain.catalogue import ExperimentRecord
from datp_core.domain.identifiers import JobId
from datp_core.domain.outcomes import StageJob, StageKind
from datp_core.planning.graph import PlanningGraph


def expand_experiment_jobs(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> PlanningGraph:
    """Expand resolved experiment into a complete, validated execution plan graph."""
    seed_cohort = config.seed_cohorts.get(experiment.seed_cohort_id)

    jobs: list[StageJob] = []

    # 1. Preflight check job
    preflight_job_id = JobId(f"{experiment.identifier.value}:preflight")
    preflight_out = ArtifactKey(
        artifact_id=ArtifactId(f"{experiment.identifier.value}:preflight_status"),
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

    eval_job_outputs: list[ArtifactKey] = []
    eval_job_ids: list[JobId] = []

    # 2. Derive jobs per seed
    for seed in seed_cohort.training_seeds:
        seed_str = str(seed.value)

        # Dataset materialization
        mat_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:mat")
        mat_output = ArtifactKey(
            artifact_id=ArtifactId(f"{experiment.identifier.value}:seed_{seed_str}:mat_data"),
            kind=ArtifactKind.MATERIALIZED_DATASET,
        )
        mat_job = StageJob(
            job_id=mat_job_id,
            stage=StageKind.DATASET_MATERIALIZATION,
            inputs=(preflight_out,),
            output=mat_output,
            dependencies=(preflight_job_id,),
        )
        jobs.append(mat_job)

        # Model Training
        train_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:train")
        train_output = ArtifactKey(
            artifact_id=ArtifactId(f"{experiment.identifier.value}:seed_{seed_str}:checkpoint"),
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

        # Calibration Score Generation
        calibration_score_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:calibration_scores")
        calib_score_output = ArtifactKey(
            artifact_id=ArtifactId(f"{experiment.identifier.value}:seed_{seed_str}:calib_scores"),
            kind=ArtifactKind.CALIBRATION_SCORES,
        )
        calibration_score_job = StageJob(
            job_id=calibration_score_job_id,
            stage=StageKind.SCORE_GENERATION,
            inputs=(train_output, mat_output),
            output=calib_score_output,
            dependencies=(train_job_id,),
        )
        jobs.append(calibration_score_job)

        test_score_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:test_scores")
        test_score_output = ArtifactKey(
            artifact_id=ArtifactId(f"{experiment.identifier.value}:seed_{seed_str}:test_scores"),
            kind=ArtifactKind.TEST_SCORES,
        )
        test_score_job = StageJob(
            job_id=test_score_job_id,
            stage=StageKind.SCORE_GENERATION,
            inputs=(train_output, mat_output),
            output=test_score_output,
            dependencies=(train_job_id,),
        )
        jobs.append(test_score_job)

        # Threshold Construction & Evaluation jobs per evaluation spec
        for eval_spec in experiment.evaluations:
            thresh_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:thresh")
            thresh_output = ArtifactKey(
                artifact_id=ArtifactId(
                    f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:threshold_set"
                ),
                kind=ArtifactKind.THRESHOLDS,
            )
            thresh_job = StageJob(
                job_id=thresh_job_id,
                stage=StageKind.THRESHOLD_CONSTRUCTION,
                inputs=(calib_score_output,),
                output=thresh_output,
                dependencies=(calibration_score_job_id,),
            )
            jobs.append(thresh_job)

            eval_job_id = JobId(f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:eval")
            eval_output = ArtifactKey(
                artifact_id=ArtifactId(f"{experiment.identifier.value}:seed_{seed_str}:{eval_spec.label}:metrics"),
                kind=ArtifactKind.CLIENT_METRICS,
            )
            eval_job = StageJob(
                job_id=eval_job_id,
                stage=StageKind.OPERATING_POINT_EVALUATION,
                inputs=(thresh_output, test_score_output),
                output=eval_output,
                dependencies=(thresh_job_id, test_score_job_id),
            )
            jobs.append(eval_job)
            eval_job_outputs.append(eval_output)
            eval_job_ids.append(eval_job_id)

    # 3. Statistical Analysis job across all seed evaluation outputs
    stats_job_id = JobId(f"{experiment.identifier.value}:statistical_analysis")
    stats_output = ArtifactKey(
        artifact_id=ArtifactId(f"{experiment.identifier.value}:statistical_report"),
        kind=ArtifactKind.STATISTICAL_SUMMARY,
    )
    stats_job = StageJob(
        job_id=stats_job_id,
        stage=StageKind.STATISTICAL_ANALYSIS,
        inputs=tuple(eval_job_outputs),
        output=stats_output,
        dependencies=tuple(eval_job_ids),
    )
    jobs.append(stats_job)

    # 4. Report Generation job
    report_job_id = JobId(f"{experiment.identifier.value}:report_generation")
    report_output = ArtifactKey(
        artifact_id=ArtifactId(f"{experiment.identifier.value}:final_report"),
        kind=ArtifactKind.RESULT_REPORT,
    )
    report_job = StageJob(
        job_id=report_job_id,
        stage=StageKind.REPORT_GENERATION,
        inputs=(stats_output,),
        output=report_output,
        dependencies=(stats_job_id,),
    )
    jobs.append(report_job)

    planning_graph = PlanningGraph(tuple(jobs))
    planning_graph.validate_acyclic()
    return planning_graph
