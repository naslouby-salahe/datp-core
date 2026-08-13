import math

import numpy as np
from pydantic import model_validator

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import MetricValue, Seed

NORMAL_REFERENCE_MULTIPLIER = 1.96


class LeaveOneSeedOutMean(StrictModel):
    omitted_seed: Seed
    mean_delta: MetricValue


class ConfirmatoryPrecisionDiagnostics(StrictModel):
    full_mean_delta: MetricValue
    sample_standard_deviation: MetricValue
    standard_error_proxy: MetricValue
    normal_reference_half_width: MetricValue
    bca_width: MetricValue | None
    leave_one_seed_out_means: tuple[LeaveOneSeedOutMean, ...]
    minimum_leave_one_seed_out_mean: MetricValue
    maximum_leave_one_seed_out_mean: MetricValue
    maximum_leave_one_seed_out_shift: MetricValue

    @model_validator(mode="after")
    def validate_leave_one_seed_out_means(self) -> "ConfirmatoryPrecisionDiagnostics":
        omitted_seeds = tuple(item.omitted_seed for item in self.leave_one_seed_out_means)
        if len(omitted_seeds) < 2 or len(omitted_seeds) != len(set(omitted_seeds)):
            raise ValueError("precision diagnostics require one leave-one-seed-out mean per distinct seed")
        values = tuple(item.mean_delta.value for item in self.leave_one_seed_out_means)
        if self.minimum_leave_one_seed_out_mean.value != min(values):
            raise ValueError("minimum leave-one-seed-out mean must match the retained values")
        if self.maximum_leave_one_seed_out_mean.value != max(values):
            raise ValueError("maximum leave-one-seed-out mean must match the retained values")
        expected_shift = max(abs(value - self.full_mean_delta.value) for value in values)
        if self.maximum_leave_one_seed_out_shift.value != expected_shift:
            raise ValueError("maximum leave-one-seed-out shift must match the retained means and full mean")
        return self


def confirmatory_precision_diagnostics(
    contrasts: PairedContrasts,
    interval: BootstrapInterval,
) -> ConfirmatoryPrecisionDiagnostics:
    deltas = np.fromiter(
        (contrast.delta.value for contrast in contrasts.values),
        dtype=np.float64,
        count=len(contrasts),
    )
    if len(deltas) < 2:
        raise ValueError("precision diagnostics require at least two paired deltas")
    full_mean = float(np.mean(deltas))
    leave_one_out = tuple(
        LeaveOneSeedOutMean(
            omitted_seed=contrast.seed,
            mean_delta=MetricValue(float(np.mean(np.delete(deltas, index)))),
        )
        for index, contrast in enumerate(contrasts.values)
    )
    sample_standard_deviation = MetricValue(float(np.std(deltas, ddof=1)))
    standard_error_proxy = MetricValue(sample_standard_deviation.value / math.sqrt(len(deltas)))
    leave_one_out_values = tuple(item.mean_delta.value for item in leave_one_out)
    return ConfirmatoryPrecisionDiagnostics(
        full_mean_delta=MetricValue(full_mean),
        sample_standard_deviation=sample_standard_deviation,
        standard_error_proxy=standard_error_proxy,
        normal_reference_half_width=MetricValue(NORMAL_REFERENCE_MULTIPLIER * standard_error_proxy.value),
        bca_width=(
            MetricValue(interval.upper_bound.value - interval.lower_bound.value)
            if interval.lower_bound is not None and interval.upper_bound is not None
            else None
        ),
        leave_one_seed_out_means=leave_one_out,
        minimum_leave_one_seed_out_mean=MetricValue(min(leave_one_out_values)),
        maximum_leave_one_seed_out_mean=MetricValue(max(leave_one_out_values)),
        maximum_leave_one_seed_out_shift=MetricValue(max(abs(value - full_mean) for value in leave_one_out_values)),
    )
