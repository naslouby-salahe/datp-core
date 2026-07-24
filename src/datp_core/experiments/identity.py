"""Deterministic identity builder for JobId, ArtifactId, and ArtifactKey, and run identity.

The builder consumes typed StageJobContext and produces identifiers deterministically.
No other module may construct id strings through manual f-string composition.

Every job/artifact identity kind is declared once in ``_IDENTITY_SPECS`` as a
``StageIdentitySpec`` (which context fields feed the identity string, in the one fixed order,
and the trailing job/artifact tokens); the public per-kind methods below are thin, self-
documenting call-site wrappers over that single shared string-building engine
(``_build_identity_string``), so no suffix-composition rule is ever duplicated across methods.
"""

from __future__ import annotations

from enum import Enum

from attrs import define

from datp_core.artifacts.models import ArtifactId, ArtifactKey, ArtifactKind
from datp_core.core.identifiers import ExperimentId, JobId, RunId
from datp_core.pipeline.models import StageJobContext

_COLON = ":"


def execution_run_id(experiment_id: ExperimentId, execution_fingerprint: str) -> RunId:
    return RunId(f"run_{experiment_id.value}_{execution_fingerprint[:12]}")


def _check_no_delimiter(value: str, *, field_name: str) -> None:
    if _COLON in value:
        raise ValueError(f"Identity field '{field_name}' must not contain '{_COLON}': {value!r}")


class IdentityKind(Enum):
    """Every distinct job/artifact identity shape produced by the pipeline."""

    PREFLIGHT = "preflight"
    MATERIALIZATION = "materialization"
    TRAINING = "training"
    PERSONALIZED_CHECKPOINT = "personalized_checkpoint"
    CALIBRATION_SCORE = "calibration_score"
    FUTURE_RECALIBRATION_SCORE = "future_recalibration_score"
    TEST_SCORE = "test_score"
    THRESHOLD = "threshold"
    EVALUATION = "evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    COHORT_CHECKPOINT_SELECTION = "cohort_checkpoint_selection"
    FEDERATED_PROXIMAL_SELECTION = "federated_proximal_selection"
    DITTO_SELECTION = "ditto_selection"
    REPORT = "report"
    RESULT_FREEZE = "result_freeze"
    CALIBRATION_SUBSET = "calibration_subset"


@define(frozen=True, slots=True, kw_only=True)
class StageIdentitySpec:
    """The context fields (in the one fixed suffix order) and trailing tokens for one identity kind."""

    artifact_kind: ArtifactKind
    job_token: str
    artifact_token: str
    uses_seed: bool = False
    uses_condition: bool = False
    uses_population: bool = False
    uses_execution: bool = False
    uses_calibration_subset: bool = False
    uses_evaluation_label: bool = False


_IDENTITY_SPECS: dict[IdentityKind, StageIdentitySpec] = {
    IdentityKind.PREFLIGHT: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESOLVED_CONFIG, job_token="preflight", artifact_token="preflight_status"
    ),
    IdentityKind.MATERIALIZATION: StageIdentitySpec(
        artifact_kind=ArtifactKind.MATERIALIZED_DATASET,
        job_token="mat",
        artifact_token="mat_data",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
    ),
    IdentityKind.TRAINING: StageIdentitySpec(
        artifact_kind=ArtifactKind.MODEL_CHECKPOINT,
        job_token="train",
        artifact_token="checkpoint",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.PERSONALIZED_CHECKPOINT: StageIdentitySpec(
        artifact_kind=ArtifactKind.PERSONALIZED_MODEL_CHECKPOINT,
        job_token="personalized_checkpoint",
        artifact_token="personalized_checkpoint",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.CALIBRATION_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.CALIBRATION_SCORES,
        job_token="calibration_scores",
        artifact_token="calib_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.FUTURE_RECALIBRATION_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.FUTURE_RECALIBRATION_SCORES,
        job_token="future_recalibration_scores",
        artifact_token="future_recalibration_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.TEST_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.TEST_SCORES,
        job_token="test_scores",
        artifact_token="test_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.THRESHOLD: StageIdentitySpec(
        artifact_kind=ArtifactKind.THRESHOLDS,
        job_token="thresh",
        artifact_token="threshold_set",
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.EVALUATION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CLIENT_METRICS,
        job_token="eval",
        artifact_token="metrics",
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.STATISTICAL_ANALYSIS: StageIdentitySpec(
        artifact_kind=ArtifactKind.STATISTICAL_SUMMARY,
        job_token="statistical_analysis",
        artifact_token="statistical_report",
    ),
    IdentityKind.COHORT_CHECKPOINT_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="cohort_checkpoint_selection",
        artifact_token="cohort_checkpoint_selection",
    ),
    IdentityKind.FEDERATED_PROXIMAL_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="federated_proximal_coefficient_selection",
        artifact_token="federated_proximal_coefficient_selection",
    ),
    IdentityKind.DITTO_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="ditto_proximal_weight_selection",
        artifact_token="ditto_proximal_weight_selection",
    ),
    IdentityKind.REPORT: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESULT_REPORT, job_token="report_generation", artifact_token="final_report"
    ),
    IdentityKind.RESULT_FREEZE: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESULT_FREEZE, job_token="result_freeze", artifact_token="result_freeze"
    ),
    IdentityKind.CALIBRATION_SUBSET: StageIdentitySpec(
        artifact_kind=ArtifactKind.CALIBRATION_SUBSET,
        job_token="calibration_subset",
        artifact_token="calibration_subset",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
        uses_calibration_subset=True,
    ),
}


def _seed_str(seed: int | None) -> str:
    if seed is None:
        raise ValueError("seed is required for per-seed job identity")
    return str(seed)


def _condition_suffix(ctx: StageJobContext) -> str:
    if ctx.partition_condition is None:
        return ""
    _check_no_delimiter(ctx.partition_condition, field_name="partition_condition")
    return f":condition_{ctx.partition_condition}"


def _population_suffix(ctx: StageJobContext) -> str:
    if ctx.population_id is None:
        return ""
    _check_no_delimiter(ctx.population_id.value, field_name="population_id")
    return f":population_{ctx.population_id.value}"


def _execution_suffix(ctx: StageJobContext) -> str:
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
    if ctx.fingerprint_features is not None:
        if not ctx.fingerprint_features or any(not feature or ":" in feature for feature in ctx.fingerprint_features):
            raise ValueError("Fingerprint-feature identity requires non-empty delimiter-free feature names")
        suffixes += (f":features_{'+'.join(ctx.fingerprint_features)}",)
    return "".join(suffixes)


def _calibration_subset_suffix(ctx: StageJobContext) -> str:
    if (ctx.calibration_sample_count is None) != (ctx.calibration_replicate is None):
        raise ValueError("Calibration subset identity requires both sample count and replicate")
    if ctx.calibration_sample_count is None:
        return ""
    if ctx.calibration_sample_count < 1 or ctx.calibration_replicate is None or ctx.calibration_replicate < 0:
        raise ValueError("Calibration subset identity requires a positive sample count and non-negative replicate")
    return f":calibration_n_{ctx.calibration_sample_count}:replicate_{ctx.calibration_replicate}"


def _build_identity_string(ctx: StageJobContext, spec: StageIdentitySpec, token: str) -> str:
    """The one shared authority for suffix composition, in the one fixed order: seed, condition,
    population, execution, calibration-subset, evaluation-label, trailing token."""
    identity = ctx.experiment_id.value
    if spec.uses_seed:
        identity += f":seed_{_seed_str(ctx.seed)}"
    if spec.uses_condition:
        identity += _condition_suffix(ctx)
    if spec.uses_population:
        identity += _population_suffix(ctx)
    if spec.uses_execution:
        identity += _execution_suffix(ctx)
    if spec.uses_calibration_subset:
        identity += _calibration_subset_suffix(ctx)
    if spec.uses_evaluation_label:
        if ctx.evaluation_label is None:
            raise ValueError(f"evaluation_label is required for {token} identity")
        identity += f":{ctx.evaluation_label}"
    return f"{identity}:{token}"


class IdentityBuilder:
    """Single deterministic authority for job and artifact identity strings.

    Every format rule lives here; planning and handlers consume tuples/typed context
    instead of parsing formatted strings.
    """

    @staticmethod
    def job_id(kind: IdentityKind, ctx: StageJobContext) -> JobId:
        spec = _IDENTITY_SPECS[kind]
        return JobId(_build_identity_string(ctx, spec, spec.job_token))

    @staticmethod
    def artifact_id(kind: IdentityKind, ctx: StageJobContext) -> ArtifactId:
        spec = _IDENTITY_SPECS[kind]
        return ArtifactId(_build_identity_string(ctx, spec, spec.artifact_token))

    @staticmethod
    def artifact_key(kind: IdentityKind, ctx: StageJobContext) -> ArtifactKey:
        spec = _IDENTITY_SPECS[kind]
        return ArtifactKey(artifact_id=IdentityBuilder.artifact_id(kind, ctx), kind=spec.artifact_kind)

    @staticmethod
    def preflight_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.PREFLIGHT, ctx)

    @staticmethod
    def materialization_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.MATERIALIZATION, ctx)

    @staticmethod
    def training_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.TRAINING, ctx)

    @staticmethod
    def calibration_score_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.CALIBRATION_SCORE, ctx)

    @staticmethod
    def future_recalibration_score_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx)

    @staticmethod
    def test_score_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.TEST_SCORE, ctx)

    @staticmethod
    def threshold_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.THRESHOLD, ctx)

    @staticmethod
    def evaluation_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.EVALUATION, ctx)

    @staticmethod
    def statistical_analysis_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.STATISTICAL_ANALYSIS, ctx)

    @staticmethod
    def cohort_checkpoint_selection_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx)

    @staticmethod
    def federated_proximal_selection_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx)

    @staticmethod
    def ditto_selection_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.DITTO_SELECTION, ctx)

    @staticmethod
    def report_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.REPORT, ctx)

    @staticmethod
    def result_freeze_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.RESULT_FREEZE, ctx)

    @staticmethod
    def calibration_subset_job_id(ctx: StageJobContext) -> JobId:
        return IdentityBuilder.job_id(IdentityKind.CALIBRATION_SUBSET, ctx)

    @staticmethod
    def preflight_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.PREFLIGHT, ctx)

    @staticmethod
    def materialization_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.MATERIALIZATION, ctx)

    @staticmethod
    def checkpoint_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.TRAINING, ctx)

    @staticmethod
    def personalized_checkpoint_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.PERSONALIZED_CHECKPOINT, ctx)

    @staticmethod
    def calibration_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.CALIBRATION_SCORE, ctx)

    @staticmethod
    def future_recalibration_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx)

    @staticmethod
    def test_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.TEST_SCORE, ctx)

    @staticmethod
    def threshold_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.THRESHOLD, ctx)

    @staticmethod
    def metrics_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.EVALUATION, ctx)

    @staticmethod
    def statistical_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.STATISTICAL_ANALYSIS, ctx)

    @staticmethod
    def cohort_checkpoint_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx)

    @staticmethod
    def federated_proximal_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx)

    @staticmethod
    def ditto_selection_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.DITTO_SELECTION, ctx)

    @staticmethod
    def final_report_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.REPORT, ctx)

    @staticmethod
    def result_freeze_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.RESULT_FREEZE, ctx)

    @staticmethod
    def calibration_subset_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.CALIBRATION_SUBSET, ctx)

    @staticmethod
    def preflight_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.PREFLIGHT, ctx)

    @staticmethod
    def materialization_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.MATERIALIZATION, ctx)

    @staticmethod
    def checkpoint_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.TRAINING, ctx)

    @staticmethod
    def personalized_checkpoint_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.PERSONALIZED_CHECKPOINT, ctx)

    @staticmethod
    def calibration_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.CALIBRATION_SCORE, ctx)

    @staticmethod
    def future_recalibration_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx)

    @staticmethod
    def calibration_subset_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.CALIBRATION_SUBSET, ctx)

    @staticmethod
    def test_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.TEST_SCORE, ctx)

    @staticmethod
    def thresholds_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.THRESHOLD, ctx)

    @staticmethod
    def metrics_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.EVALUATION, ctx)

    @staticmethod
    def statistical_summary_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.STATISTICAL_ANALYSIS, ctx)

    @staticmethod
    def cohort_checkpoint_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx)

    @staticmethod
    def federated_proximal_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx)

    @staticmethod
    def ditto_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.DITTO_SELECTION, ctx)

    @staticmethod
    def result_report_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.REPORT, ctx)

    @staticmethod
    def result_freeze_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.RESULT_FREEZE, ctx)

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
    def future_recalibration_score_job(
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
            IdentityBuilder.future_recalibration_score_job_id(ctx),
            IdentityBuilder.future_recalibration_scores_key(ctx),
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
    def calibration_subset_job(
        ctx: StageJobContext, calibration_output: ArtifactKey, calibration_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.calibration_subset_job_id(ctx),
            IdentityBuilder.calibration_subset_key(ctx),
            (calibration_output,),
            (calibration_job_id,),
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
