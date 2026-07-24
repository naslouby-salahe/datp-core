"""Deterministic identity builder — single authority for StageNodeKey / ArtifactKey construction."""

from __future__ import annotations

from collections import Counter

from datp_core.artifacts.identity import ArtifactKey
from datp_core.experiments.identity.kinds import IdentityKind, StageIdentitySpec
from datp_core.experiments.identity.specs import _IDENTITY_SPECS
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey

# StageKinds that map to more than one IdentityKind — the kind_suffix
# discriminator is only set for these to keep labels short.
_ambiguous_stage_kinds: frozenset[StageKind] = frozenset(
    sk
    for sk, count in Counter(spec.stage_kind for spec in _IDENTITY_SPECS.values()).items()
    if count > 1
)


def _construct_node_key(ctx: StageJobContext, spec: StageIdentitySpec, kind: IdentityKind) -> StageNodeKey:
    """Build a StageNodeKey from context and identity-kind spec."""
    return StageNodeKey(
        experiment=ctx.experiment_id,
        stage=spec.stage_kind,
        kind_suffix=kind.value if spec.stage_kind in _ambiguous_stage_kinds else None,
        seed=ctx.seed if spec.uses_seed else None,
        population=ctx.population_id if spec.uses_population else None,
        partition_condition=ctx.partition_condition if spec.uses_condition else None,
        evaluation_label=ctx.evaluation_label if spec.uses_evaluation_label else None,
        # threshold_policy is intentionally absent from the identity — scores are
        # shared across threshold policies so the node key must not vary with policy.
        federated_proximal_mu=ctx.federated_proximal_mu if spec.uses_execution else None,
        ditto_proximal_weight=ctx.ditto_proximal_weight if spec.uses_execution else None,
        threshold_quantile=ctx.threshold_quantile if spec.uses_execution else None,
        shrinkage_weight=ctx.shrinkage_weight if spec.uses_execution else None,
        federated_summary_fixed_k=ctx.federated_summary_fixed_k if spec.uses_execution else None,
        fingerprint_features=ctx.fingerprint_features if spec.uses_execution else None,
        calibration_sample_count=ctx.calibration_sample_count if spec.uses_calibration_subset else None,
        calibration_replicate=ctx.calibration_replicate if spec.uses_calibration_subset else None,
    )


class IdentityBuilder:
    @staticmethod
    def node_key(kind: IdentityKind, ctx: StageJobContext) -> StageNodeKey:
        spec = _IDENTITY_SPECS[kind]
        return _construct_node_key(ctx, spec, kind)

    @staticmethod
    def artifact_key(kind: IdentityKind, ctx: StageJobContext) -> ArtifactKey:
        spec = _IDENTITY_SPECS[kind]
        return ArtifactKey(node_key=IdentityBuilder.node_key(kind, ctx), kind=spec.artifact_kind)

    # --- node_key shortcuts ---

    @staticmethod
    def preflight_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.PREFLIGHT, ctx)

    @staticmethod
    def materialization_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.MATERIALIZATION, ctx)

    @staticmethod
    def training_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.TRAINING, ctx)

    @staticmethod
    def calibration_score_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.CALIBRATION_SCORE, ctx)

    @staticmethod
    def future_recalibration_score_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx)

    @staticmethod
    def test_score_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.TEST_SCORE, ctx)

    @staticmethod
    def threshold_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.THRESHOLD, ctx)

    @staticmethod
    def evaluation_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.EVALUATION, ctx)

    @staticmethod
    def statistical_analysis_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.STATISTICAL_ANALYSIS, ctx)

    @staticmethod
    def cohort_checkpoint_selection_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx)

    @staticmethod
    def federated_proximal_selection_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx)

    @staticmethod
    def ditto_selection_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.DITTO_SELECTION, ctx)

    @staticmethod
    def report_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.REPORT, ctx)

    @staticmethod
    def result_freeze_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.RESULT_FREEZE, ctx)

    @staticmethod
    def calibration_subset_node_key(ctx: StageJobContext) -> StageNodeKey:
        return IdentityBuilder.node_key(IdentityKind.CALIBRATION_SUBSET, ctx)

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
    def preflight_job(ctx: StageJobContext) -> tuple[StageNodeKey, ArtifactKey]:
        return (IdentityBuilder.preflight_node_key(ctx), IdentityBuilder.preflight_key(ctx))

    @staticmethod
    def materialization_job(
        ctx: StageJobContext, preflight_output: ArtifactKey, preflight_node_key: StageNodeKey
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.materialization_node_key(ctx),
            IdentityBuilder.materialization_key(ctx),
            (preflight_output,),
            (preflight_node_key,),
        )

    @staticmethod
    def training_job(
        ctx: StageJobContext, mat_output: ArtifactKey, mat_node_key: StageNodeKey
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.training_node_key(ctx),
            IdentityBuilder.checkpoint_key(ctx),
            (mat_output,),
            (mat_node_key,),
        )

    @staticmethod
    def cohort_checkpoint_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_node_keys: tuple[StageNodeKey, ...]
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.cohort_checkpoint_selection_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.COHORT_CHECKPOINT_SELECTION, ctx),
            train_outputs,
            train_node_keys,
        )

    @staticmethod
    def federated_proximal_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_node_keys: tuple[StageNodeKey, ...]
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.federated_proximal_selection_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.FEDERATED_PROXIMAL_SELECTION, ctx),
            train_outputs,
            train_node_keys,
        )

    @staticmethod
    def ditto_selection_job(
        ctx: StageJobContext, train_outputs: tuple[ArtifactKey, ...], train_node_keys: tuple[StageNodeKey, ...]
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.ditto_selection_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.DITTO_SELECTION, ctx),
            train_outputs,
            train_node_keys,
        )

    @staticmethod
    def calibration_score_job(
        ctx: StageJobContext,
        train_output: ArtifactKey,
        mat_output: ArtifactKey,
        train_node_key: StageNodeKey,
        selection_output: ArtifactKey | None = None,
        selection_node_key: StageNodeKey | None = None,
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        selection_inputs = () if selection_output is None else (selection_output,)
        selection_dependencies = () if selection_node_key is None else (selection_node_key,)
        return (
            IdentityBuilder.calibration_score_node_key(ctx),
            IdentityBuilder.calibration_scores_key(ctx),
            (train_output, mat_output, *selection_inputs),
            (train_node_key, *selection_dependencies),
        )

    @staticmethod
    def future_recalibration_score_job(
        ctx: StageJobContext,
        train_output: ArtifactKey,
        mat_output: ArtifactKey,
        train_node_key: StageNodeKey,
        selection_output: ArtifactKey | None = None,
        selection_node_key: StageNodeKey | None = None,
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        selection_inputs = () if selection_output is None else (selection_output,)
        selection_dependencies = () if selection_node_key is None else (selection_node_key,)
        return (
            IdentityBuilder.future_recalibration_score_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.FUTURE_RECALIBRATION_SCORE, ctx),
            (train_output, mat_output, *selection_inputs),
            (train_node_key, *selection_dependencies),
        )

    @staticmethod
    def test_score_job(
        ctx: StageJobContext,
        train_output: ArtifactKey,
        mat_output: ArtifactKey,
        train_node_key: StageNodeKey,
        selection_output: ArtifactKey | None = None,
        selection_node_key: StageNodeKey | None = None,
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        selection_inputs = () if selection_output is None else (selection_output,)
        selection_dependencies = () if selection_node_key is None else (selection_node_key,)
        return (
            IdentityBuilder.test_score_node_key(ctx),
            IdentityBuilder.test_scores_key(ctx),
            (train_output, mat_output, *selection_inputs),
            (train_node_key, *selection_dependencies),
        )

    @staticmethod
    def calibration_subset_job(
        ctx: StageJobContext, calibration_output: ArtifactKey, calibration_node_key: StageNodeKey
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.calibration_subset_node_key(ctx),
            IdentityBuilder.calibration_subset_key(ctx),
            (calibration_output,),
            (calibration_node_key,),
        )

    @staticmethod
    def threshold_job(
        ctx: StageJobContext, calib_score_output: ArtifactKey, calib_score_node_key: StageNodeKey
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.threshold_node_key(ctx),
            IdentityBuilder.thresholds_key(ctx),
            (calib_score_output,),
            (calib_score_node_key,),
        )

    @staticmethod
    def evaluation_job(
        ctx: StageJobContext,
        thresh_output: ArtifactKey,
        test_score_output: ArtifactKey,
        thresh_node_key: StageNodeKey,
        test_score_node_key: StageNodeKey,
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.evaluation_node_key(ctx),
            IdentityBuilder.metrics_key(ctx),
            (thresh_output, test_score_output),
            (thresh_node_key, test_score_node_key),
        )

    @staticmethod
    def statistical_analysis_job(
        ctx: StageJobContext,
        eval_outputs: tuple[ArtifactKey, ...],
        eval_node_keys: tuple[StageNodeKey, ...],
        additional_inputs: tuple[ArtifactKey, ...] = (),
        additional_dependencies: tuple[StageNodeKey, ...] = (),
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.statistical_analysis_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.STATISTICAL_ANALYSIS, ctx),
            (*eval_outputs, *additional_inputs),
            (*eval_node_keys, *additional_dependencies),
        )

    @staticmethod
    def report_job(
        ctx: StageJobContext, result_freeze_output: ArtifactKey, result_freeze_node_key: StageNodeKey
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.report_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.REPORT, ctx),
            (result_freeze_output,),
            (result_freeze_node_key,),
        )

    @staticmethod
    def result_freeze_job(
        ctx: StageJobContext,
        statistical_output: ArtifactKey,
        statistical_node_key: StageNodeKey,
        evaluation_outputs: tuple[ArtifactKey, ...],
        evaluation_node_keys: tuple[StageNodeKey, ...],
    ) -> tuple[StageNodeKey, ArtifactKey, tuple[ArtifactKey, ...], tuple[StageNodeKey, ...]]:
        return (
            IdentityBuilder.result_freeze_node_key(ctx),
            IdentityBuilder.artifact_key(IdentityKind.RESULT_FREEZE, ctx),
            (statistical_output, *evaluation_outputs),
            (statistical_node_key, *evaluation_node_keys),
        )
