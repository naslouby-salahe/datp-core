"""Sweep-value extraction and stage-context derivation shared across pipeline stages.

Two of `application/scoring_support.py`'s six unrelated concerns (that module was an explicit
"dumping ground" per CURRENT_ARCHITECTURE.md) live here because they are genuinely experiment/sweep
concerns: deriving a score-lookup context that strips execution-only fields, and resolving a
calibration-subset sample-count sweep. The other four concerns move to `evaluation/distributions.py`
and `analysis/{coverage,resources}.py` in later phases.
"""

from __future__ import annotations

from datp_core.experiments.models import ExperimentRecord, ValueSweepRecord
from datp_core.pipeline.models import StageJobContext


def score_context(context: StageJobContext, *, retain_calibration_subset: bool = False) -> StageJobContext:
    """Strip evaluation-only fields, returning the context that identifies a score artifact."""
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


def calibration_sample_counts(experiment: ExperimentRecord) -> tuple[int | None, ...]:
    if experiment.calibration_subset is None:
        return (None,)
    sweep_name = experiment.calibration_subset.requested_sample_count.get("from_sweep")
    values = tuple(
        int(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    )
    if not values:
        raise ValueError("Calibration subset requires a positive integer sample-count sweep")
    return values
