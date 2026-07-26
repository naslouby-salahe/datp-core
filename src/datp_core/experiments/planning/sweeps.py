from __future__ import annotations

from collections.abc import Mapping

from datp_core.experiments.catalogue.models import ExperimentRecord
from datp_core.experiments.catalogue.sweeps import ValueSweepRecord


def _sweep_values(experiment: ExperimentRecord, name: str | None) -> tuple[float, ...]:
    return tuple(
        float(value)
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == name
        for value in sweep.values
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )


def _sweep_reference(overrides, name: str) -> str | None:
    override = None if overrides is None else overrides.get(name)
    reference = override.get("from_sweep") if isinstance(override, Mapping) else None
    return reference if isinstance(reference, str) else None


def _evaluation_sweep_values(experiment: ExperimentRecord, overrides, name: str) -> tuple[float | None, ...]:
    return _sweep_values(experiment, _sweep_reference(overrides, name)) or (None,)


def _feature_sweep_values(experiment: ExperimentRecord, overrides) -> tuple[tuple[str, ...] | None, ...]:
    sweep_name = _sweep_reference(overrides, "fingerprint_features")
    values = tuple(
        value
        for sweep in experiment.sweeps
        if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
        for value in sweep.values
        if isinstance(value, tuple) and value and all(isinstance(feature, str) for feature in value)
    )
    return values or (None,)


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
