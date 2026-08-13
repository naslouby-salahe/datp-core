from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter_ns

import numpy as np

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ValidationReasonText
from datp_core.core.numeric import MetricValue, SeedObservationCount

WARM_UP_ITERATION_COUNT = 5
MEASURED_ITERATION_COUNT = 20
PEAK_RSS_UNAVAILABLE = ValidationReasonText("UNAVAILABLE_MEASUREMENT_NOT_SUPPORTED")


@dataclass(frozen=True, slots=True)
class ThresholdConstructionRuntimeBenchmark:
    median_milliseconds: MetricValue
    interquartile_range_milliseconds: MetricValue
    p95_milliseconds: MetricValue
    observation_count: SeedObservationCount
    peak_server_rss: MetricValue | None
    peak_server_rss_unavailable_reason: ValidationReasonText | None

    def __post_init__(self) -> None:
        if self.observation_count.value != MEASURED_ITERATION_COUNT:
            raise ScientificContractError(
                ErrorMessage("threshold runtime benchmark requires exactly 20 measured iterations")
            )
        if (self.peak_server_rss is None) == (self.peak_server_rss_unavailable_reason is None):
            raise ScientificContractError(
                ErrorMessage("runtime benchmark requires peak RSS or an explicit unavailable reason")
            )


def benchmark_threshold_construction(operation: Callable[[], object]) -> ThresholdConstructionRuntimeBenchmark:
    """Time construction only; callers supply already materialized score/calibration arrays."""
    for _ in range(WARM_UP_ITERATION_COUNT):
        operation()
    elapsed_nanoseconds: list[int] = []
    for _ in range(MEASURED_ITERATION_COUNT):
        started = perf_counter_ns()
        operation()
        elapsed_nanoseconds.append(perf_counter_ns() - started)
    milliseconds = np.asarray(elapsed_nanoseconds, dtype=np.float64) / 1_000_000.0
    lower, upper = np.quantile(milliseconds, (0.25, 0.75), method="linear")
    return ThresholdConstructionRuntimeBenchmark(
        median_milliseconds=MetricValue(float(np.quantile(milliseconds, 0.5, method="linear"))),
        interquartile_range_milliseconds=MetricValue(float(upper - lower)),
        p95_milliseconds=MetricValue(float(np.quantile(milliseconds, 0.95, method="linear"))),
        observation_count=SeedObservationCount(MEASURED_ITERATION_COUNT),
        peak_server_rss=None,
        peak_server_rss_unavailable_reason=PEAK_RSS_UNAVAILABLE,
    )
