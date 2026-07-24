"""Context transformations for planning."""

from __future__ import annotations

from datp_core.pipeline.models import StageJobContext


def score_context(context: StageJobContext, *, retain_calibration_subset: bool = False) -> StageJobContext:
    return StageJobContext(
        experiment_id=context.experiment_id,
        seed=context.seed,
        partition_condition=context.partition_condition,
        population_id=context.population_id,
        federated_proximal_mu=context.federated_proximal_mu,
        ditto_proximal_weight=context.ditto_proximal_weight,
        calibration_sample_count=context.calibration_sample_count if retain_calibration_subset else None,
        calibration_replicate=context.calibration_replicate if retain_calibration_subset else None,
    )
