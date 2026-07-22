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
        if ctx.partition_condition is None:
            return ""
        _check_no_delimiter(ctx.partition_condition, field_name="partition_condition")
        return f":condition_{ctx.partition_condition}"

    @staticmethod
    def _training_suffix(ctx: StageJobContext) -> str:
        suffixes = ()
        if ctx.federated_proximal_mu is not None:
            suffixes += (f":mu_{ctx.federated_proximal_mu:g}",)
        if ctx.ditto_proximal_weight is not None:
            suffixes += (f":lambda_{ctx.ditto_proximal_weight:g}",)
        if ctx.threshold_quantile is not None:
            suffixes += (f":q_{ctx.threshold_quantile:g}",)
        if ctx.shrinkage_weight is not None:
            suffixes += (f":shrinkage_{ctx.shrinkage_weight:g}",)
        if ctx.federated_summary_fixed_k is not None:
            suffixes += (f":fixed_k_{ctx.federated_summary_fixed_k:g}",)
        return "".join(suffixes)

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
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:train"
        )

    @staticmethod
    def calibration_score_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:calibration_scores"
        )

    @staticmethod
    def test_score_job_id(ctx: StageJobContext) -> JobId:
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:test_scores"
        )

    @staticmethod
    def threshold_job_id(ctx: StageJobContext) -> JobId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for threshold job identity")
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:{ctx.evaluation_label}:thresh"
        )

    @staticmethod
    def evaluation_job_id(ctx: StageJobContext) -> JobId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for evaluation job identity")
        return JobId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:{ctx.evaluation_label}:eval"
        )

    @staticmethod
    def statistical_analysis_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:statistical_analysis")

    @staticmethod
    def cohort_checkpoint_selection_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:cohort_checkpoint_selection")

    @staticmethod
    def federated_proximal_selection_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:federated_proximal_coefficient_selection")

    @staticmethod
    def ditto_selection_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:ditto_proximal_weight_selection")

    @staticmethod
    def report_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:report_generation")

    @staticmethod
    def result_freeze_job_id(ctx: StageJobContext) -> JobId:
        return JobId(f"{ctx.experiment_id.value}:result_freeze")

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
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:checkpoint"
        )

    @staticmethod
    def personalized_checkpoint_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}"
            f"{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:personalized_checkpoint"
        )

    @staticmethod
    def calibration_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:calib_scores"
        )

    @staticmethod
    def test_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:test_scores"
        )

    @staticmethod
    def threshold_artifact_id(ctx: StageJobContext) -> ArtifactId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for threshold artifact identity")
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:{ctx.evaluation_label}:threshold_set"
        )

    @staticmethod
    def metrics_artifact_id(ctx: StageJobContext) -> ArtifactId:
        if ctx.evaluation_label is None:
            raise ValueError("evaluation_label is required for metrics artifact identity")
        return ArtifactId(
            f"{ctx.experiment_id.value}:seed_{IdentityBuilder._seed_str(ctx.seed)}{IdentityBuilder._condition_suffix(ctx)}{IdentityBuilder._training_suffix(ctx)}:{ctx.evaluation_label}:metrics"
        )

    @staticmethod
    def statistical_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:statistical_report")

    @staticmethod
    def cohort_checkpoint_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:cohort_checkpoint_selection")

    @staticmethod
    def federated_proximal_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:federated_proximal_coefficient_selection")

    @staticmethod
    def ditto_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:ditto_proximal_weight_selection")

    @staticmethod
    def final_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:final_report")

    @staticmethod
    def result_freeze_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return ArtifactId(f"{ctx.experiment_id.value}:result_freeze")

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
    def personalized_checkpoint_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.personalized_checkpoint_artifact_id(ctx),
            kind=ArtifactKind.PERSONALIZED_MODEL_CHECKPOINT,
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
    def cohort_checkpoint_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.cohort_checkpoint_selection_artifact_id(ctx),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )

    @staticmethod
    def federated_proximal_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.federated_proximal_selection_artifact_id(ctx),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )

    @staticmethod
    def ditto_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.ditto_selection_artifact_id(ctx),
            kind=ArtifactKind.CHECKPOINT_SELECTION,
        )

    @staticmethod
    def result_report_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.final_report_artifact_id(ctx),
            kind=ArtifactKind.RESULT_REPORT,
        )

    @staticmethod
    def result_freeze_key(ctx: StageJobContext) -> ArtifactKey:
        return ArtifactKey(
            artifact_id=IdentityBuilder.result_freeze_artifact_id(ctx),
            kind=ArtifactKind.RESULT_FREEZE,
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
    def cohort_checkpoint_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.cohort_checkpoint_selection_job_id(ctx),
            IdentityBuilder.cohort_checkpoint_selection_key(ctx),
            train_outputs,
            train_job_ids,
        )

    @staticmethod
    def federated_proximal_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.federated_proximal_selection_job_id(ctx),
            IdentityBuilder.federated_proximal_selection_key(ctx),
            train_outputs,
            train_job_ids,
        )

    @staticmethod
    def ditto_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.ditto_selection_job_id(ctx),
            IdentityBuilder.ditto_selection_key(ctx),
            train_outputs,
            train_job_ids,
        )

    @staticmethod
    def calibration_score_job(
        ctx: StageJobContext,
        train_output: ArtifactKey,
        mat_output: ArtifactKey,
        train_job_id: JobId,
        selection_output: ArtifactKey | None = None,
        selection_job_id: JobId | None = None,
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        selection_inputs = () if selection_output is None else (selection_output,)
        selection_dependencies = () if selection_job_id is None else (selection_job_id,)
        return (
            IdentityBuilder.calibration_score_job_id(ctx),
            IdentityBuilder.calibration_scores_key(ctx),
            (train_output, mat_output, *selection_inputs),
            (train_job_id, *selection_dependencies),
        )

    @staticmethod
    def test_score_job(
        ctx: StageJobContext,
        train_output: ArtifactKey,
        mat_output: ArtifactKey,
        train_job_id: JobId,
        selection_output: ArtifactKey | None = None,
        selection_job_id: JobId | None = None,
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        selection_inputs = () if selection_output is None else (selection_output,)
        selection_dependencies = () if selection_job_id is None else (selection_job_id,)
        return (
            IdentityBuilder.test_score_job_id(ctx),
            IdentityBuilder.test_scores_key(ctx),
            (train_output, mat_output, *selection_inputs),
            (train_job_id, *selection_dependencies),
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
        ctx: StageJobContext,
        eval_outputs: tuple[ArtifactKey, ...],
        eval_job_ids: tuple[JobId, ...],
        additional_inputs: tuple[ArtifactKey, ...] = (),
        additional_dependencies: tuple[JobId, ...] = (),
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.statistical_analysis_job_id(ctx),
            IdentityBuilder.statistical_summary_key(ctx),
            (*eval_outputs, *additional_inputs),
            (*eval_job_ids, *additional_dependencies),
        )

    @staticmethod
    def report_job(
        ctx: StageJobContext, result_freeze_output: ArtifactKey, result_freeze_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.report_job_id(ctx),
            IdentityBuilder.result_report_key(ctx),
            (result_freeze_output,),
            (result_freeze_job_id,),
        )

    @staticmethod
    def result_freeze_job(
        ctx: StageJobContext,
        statistical_output: ArtifactKey,
        statistical_job_id: JobId,
        evaluation_outputs: tuple[ArtifactKey, ...],
        evaluation_job_ids: tuple[JobId, ...],
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.result_freeze_job_id(ctx),
            IdentityBuilder.result_freeze_key(ctx),
            (statistical_output, *evaluation_outputs),
            (statistical_job_id, *evaluation_job_ids),
        )
