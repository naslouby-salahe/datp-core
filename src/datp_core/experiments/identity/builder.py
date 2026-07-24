"""Deterministic identity builder — single authority for job/artifact identity strings."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey
from datp_core.core.hashing import Checksum
from datp_core.core.identifiers import ArtifactId, ExperimentId, JobId, RunId
from datp_core.experiments.identity.kinds import IdentityKind, StageIdentitySpec
from datp_core.experiments.identity.specs import _IDENTITY_SPECS
from datp_core.pipeline.stages.context import StageJobContext

_COLON = ":"


def execution_run_id(
    experiment_id: ExperimentId,
    execution_fingerprint: str,
    source_provenance_fingerprint: Checksum,
) -> RunId:
    """Construct the run id for an experiment's execution namespace.

    The source-provenance fingerprint is mandatory: a run id built without it names a different,
    incomplete namespace than the one the experiment actually executes under, which breaks every
    cross-experiment reference silently reconstructing a partial id. Callers resolving an *existing*
    experiment's run id (a cross-experiment reference, not the currently executing one) must use
    ``resolve_experiment_run_id`` instead of calling this function directly.
    """
    base = f"run_{experiment_id.value}_{execution_fingerprint[:12]}"
    base += f"_{source_provenance_fingerprint.value[:12]}"
    return RunId(base)


def _check_no_delimiter(value: str, *, field_name: str) -> None:
    if _COLON in value:
        raise ValueError(f"Identity field '{field_name}' must not contain '{_COLON}': {value!r}")


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
        suffixes += (f":mu_{ctx.federated_proximal_mu:.17g}",)
    if ctx.ditto_proximal_weight is not None:
        suffixes += (f":lambda_{ctx.ditto_proximal_weight:.17g}",)
    if ctx.threshold_quantile is not None:
        suffixes += (f":q_{ctx.threshold_quantile:.17g}",)
    if ctx.shrinkage_weight is not None:
        suffixes += (f":shrinkage_{ctx.shrinkage_weight:.17g}",)
    if ctx.federated_summary_fixed_k is not None:
        suffixes += (f":fixed_k_{ctx.federated_summary_fixed_k:.17g}",)
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
    if ctx.calibration_sample_count is not None and ctx.calibration_sample_count < 1:
        raise ValueError("Calibration subset identity requires a positive sample count")
    if ctx.calibration_replicate is not None and ctx.calibration_replicate < 0:
        raise ValueError("Calibration subset identity requires a non-negative replicate")
    return f":calibration_n_{ctx.calibration_sample_count}:replicate_{ctx.calibration_replicate}"


def _build_identity_string(ctx: StageJobContext, spec: StageIdentitySpec, token: str) -> str:
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
    # --- artifact_id shortcuts ---

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
    def calibration_scores_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.CALIBRATION_SCORE, ctx)

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
    def calibration_subset_artifact_id(ctx: StageJobContext) -> ArtifactId:
        return IdentityBuilder.artifact_id(IdentityKind.CALIBRATION_SUBSET, ctx)
    # --- artifact_key shortcuts ---

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
    def federated_proximal_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx)

    @staticmethod
    def ditto_selection_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.DITTO_SELECTION, ctx)

    @staticmethod
    def calibration_scores_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.CALIBRATION_SCORE, ctx)

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
    def calibration_subset_key(ctx: StageJobContext) -> ArtifactKey:
        return IdentityBuilder.artifact_key(IdentityKind.CALIBRATION_SUBSET, ctx)
    # --- job construction helpers ---

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
            IdentityBuilder.artifact_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx),
            train_outputs,
            train_job_ids,
        )

    @staticmethod
    def federated_proximal_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.federated_proximal_selection_job_id(ctx),
            IdentityBuilder.artifact_key(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx),
            train_outputs,
            train_job_ids,
        )

    @staticmethod
    def ditto_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_job_ids: tuple[JobId, ...]
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.ditto_selection_job_id(ctx),
            IdentityBuilder.artifact_key(IdentityKind.DITTO_SELECTION, ctx),
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
            IdentityBuilder.artifact_key(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx),
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
            IdentityBuilder.artifact_key(IdentityKind.STATISTICAL_ANALYSIS, ctx),
            (*eval_outputs, *additional_inputs),
            (*eval_job_ids, *additional_dependencies),
        )

    @staticmethod
    def report_job(
        ctx: StageJobContext, result_freeze_output: ArtifactKey, result_freeze_job_id: JobId
    ) -> tuple[JobId, ArtifactKey, tuple[ArtifactKey, ...], tuple[JobId, ...]]:
        return (
            IdentityBuilder.report_job_id(ctx),
            IdentityBuilder.artifact_key(IdentityKind.REPORT, ctx),
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
            IdentityBuilder.artifact_key(IdentityKind.RESULT_FREEZE, ctx),
            (statistical_output, *evaluation_outputs),
            (statistical_job_id, *evaluation_job_ids),
        )
