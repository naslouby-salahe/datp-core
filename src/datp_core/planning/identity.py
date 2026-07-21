"""Deterministic identity builder for JobId, ArtifactId, and ArtifactKey.

The builder consumes typed StageJobContext and produces identifiers deterministically.
No other module may construct id strings through manual f-string composition.
"""

from __future__ import annotations

from datp_core.domain.artifacts import ArtifactId, ArtifactKey, ArtifactKind
from datp_core.domain.identifiers import JobId
from datp_core.domain.outcomes import StageJobContext

_COLON = ":"


def _check_no_delimiter(value: str, *, field_name: str) -> None:
    if _COLON in value:
        raise ValueError(f"Identity field '{field_name}' must not contain '{_COLON}': {value!r}")


class IdentityBuilder:
    """Single deterministic authority for job and artifact identity strings.

    Every format rule lives here; planning and handlers consume tuples/typed context
    instead of parsing formatted strings.
    """

    @staticmethod
    def _seed_str(seed: int | None) -> str:
        if seed is None:
            raise ValueError("seed is required for per-seed job identity")
        return str(seed)

    @staticmethod
    def _condition_suffix(ctx: StageJobContext) -> str:
        return "" if ctx.partition_condition is None else f":condition_{ctx.partition_condition}"

    @staticmethod
    def preflight_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:preflight")

    @staticmethod
    def materialization_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:mat"
        )

    @staticmethod
    def training_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:train"
        )

    @staticmethod
    def calibration_score_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:calibration_scores"
        )

    @staticmethod
    def test_score_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:test_scores"
        )

    @staticmethod
    def threshold_job_id(ctx: StageJobContext) -> JobId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for threshold job identity")
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}:{ctx.evaluation_label}:thresh"
        )

    @staticmethod
    def evaluation_job_id(ctx: StageJobContext) -> JobId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for evaluation job identity")
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}:{ctx.evaluation_label}:eval"
        )

    @staticmethod
    def statistical_analysis_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:statistical_analysis")

    @staticmethod
    def report_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:report_generation")

    @staticmethod
    def preflight_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:preflight_status")

    @staticmethod
    def materialization_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:mat_data"
        )

    @staticmethod
    def checkpoint_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:checkpoint"
        )

    @staticmethod
    def calibration_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:calib_scores"
        )

    @staticmethod
    def test_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}:test_scores"
        )

    @staticmethod
    def threshold_artifact_id(ctx: StageJobContext) -> ArtifactId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for threshold artifact identity")
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}:{ctx.evaluation_label}:threshold_set"
        )

    @staticmethod
    def metrics_artifact_id(ctx: StageJobContext) -> ArtifactId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for metrics artifact identity")
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}:{ctx.evaluation_label}:metrics"
        )

    @staticmethod
    def statistical_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:statistical_report")

    @staticmethod
    def final_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:final_report")

    @staticmethod
    def preflight_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.preflight_artifact_id(ctx),
            kind=ArtifactKind.RESOLVED_CONFIG,
        )

    @staticmethod
    def materialization_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.materialization_artifact_id(ctx),
            kind=ArtifactKind.MATERIALIZED_DATASET,
        )

    @staticmethod
    def checkpoint_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.checkpoint_artifact_id(ctx),
            kind=ArtifactKind.MODEL_CHECKPOINT,
        )

    @staticmethod
    def calibration_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.calibration_scores_artifact_id(ctx),
            kind=ArtifactKind.CALIBRATION_SCORES,
        )

    @staticmethod
    def test_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.test_scores_artifact_id(ctx),
            kind=ArtifactKind.TEST_SCORES,
        )

    @staticmethod
    def thresholds_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.threshold_artifact_id(ctx),
            kind=ArtifactKind.THRESHOLDS,
        )

    @staticmethod
    def metrics_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.metrics_artifact_id(ctx),
            kind=ArtifactKind.CLIENT_METRICS,
        )

    @staticmethod
    def statistical_summary_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.statistical_report_artifact_id(ctx),
            kind=ArtifactKind.STATISTICAL_SUMMARY,
        )

    @staticmethod
    def result_report_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.final_report_artifact_id(ctx),
            kind=ArtifactKind.RESULT_REPORT,
        )

    @staticmethod
    def preflight_job(ctx: StageJobContext) -> tuple[JobId, ArtifactKey]:
        return (IdentityBuilder.preflight_job_id(ctx), IdentityBuilder.preflight_key(ctx))

    @staticmethod
    def materialization_job(
        ctx: StageJobContext, preflight_output: ArtifactKey, preflight_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.materialization_job_id(ctx),
            IdentityBuilder.materialization_key(ctx),
            (preflight_output,),
            (preflight_job_id,),
        )

    @staticmethod
    def training_job(
        ctx: StageJobContext, mat_output: ArtifactKey, mat_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.training_job_id(ctx),
            IdentityBuilder.checkpoint_key(ctx),
            (mat_output,),
            (mat_job_id,),
        )

    @staticmethod
    def calibration_score_job(
        ctx: StageJobContext, train_output: ArtifactKey, mat_output: ArtifactKey, train_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.calibration_score_job_id(ctx),
            IdentityBuilder.calibration_scores_key(ctx),
            (train_output, mat_output),
            (train_job_id,),
        )

    @staticmethod
    def test_score_job(
        ctx: StageJobContext, train_output: ArtifactKey, mat_output: ArtifactKey, train_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.test_score_job_id(ctx),
            IdentityBuilder.test_scores_key(ctx),
            (train_output, mat_output),
            (train_job_id,),
        )

    @staticmethod
    def threshold_job(
        ctx: StageJobContext, calib_score_output: ArtifactKey, calib_score_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.threshold_job_id(ctx),
            IdentityBuilder.thresholds_key(ctx),
            (calib_score_output,),
            (calib_score_job_id,),
        )

    @staticmethod
    def evaluation_job(
        ctx: StageJobContext,
        thresh_output: ArtifactKey,
        test_score_output: ArtifactKey,
        thresh_job_id: JobId,
        test_score_job_id: JobId,
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.evaluation_job_id(ctx),
            IdentityBuilder.metrics_key(ctx),
            (thresh_output, test_score_output),
            (thresh_job_id, test_score_job_id),
        )

    @staticmethod
    def statistical_analysis_job(
        ctx: StageJobContext, eval_outputs: tuple[ArtifactKey, ...], eval_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.statistical_analysis_job_id(ctx),
            IdentityBuilder.statistical_summary_key(ctx),
            eval_outputs,
            eval_job_ids,
        )

    @staticmethod
    def report_job(
        ctx: StageJobContext, stats_output: ArtifactKey, stats_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.report_job_id(ctx),
            IdentityBuilder.result_report_key(ctx),
            (stats_output,),
            (stats_job_id,),
        )
