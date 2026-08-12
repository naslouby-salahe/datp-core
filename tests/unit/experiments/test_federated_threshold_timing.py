from datp_core.core.numeric import ElapsedSeconds
from datp_core.experiments.federated_threshold.run import _runtime_timing_summary


def test_kll_timing_environment_records_hardware_identity() -> None:
    summary = _runtime_timing_summary((ElapsedSeconds(0.001), ElapsedSeconds(0.002)))

    assert summary is not None
    assert summary.environment.hardware
