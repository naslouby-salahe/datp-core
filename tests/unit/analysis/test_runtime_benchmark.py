from datp_core.analysis.operational.runtime_benchmark import (
    MEASURED_ITERATION_COUNT,
    WARM_UP_ITERATION_COUNT,
    benchmark_threshold_construction,
)


def test_threshold_runtime_benchmark_uses_locked_warmup_and_measurement_counts() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1

    benchmark = benchmark_threshold_construction(operation)

    assert calls == WARM_UP_ITERATION_COUNT + MEASURED_ITERATION_COUNT
    assert benchmark.observation_count.value == MEASURED_ITERATION_COUNT
    assert benchmark.peak_server_rss is None
    assert benchmark.peak_server_rss_unavailable_reason is not None
