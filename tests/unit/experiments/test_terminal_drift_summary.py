import pytest

from datp_core.core.identifiers import ClientIdentityToken
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.training_stress.run import Terminal50ClientDrift, Terminal50DriftSummary


def test_terminal50_drift_summary_requires_client_identity_order() -> None:
    with pytest.raises(ValueError, match="ordered"):
        Terminal50DriftSummary(
            seed=Seed(3),
            coefficient=None,
            federation_rms_drift=MetricValue(0.2),
            client_rms_drifts=(
                Terminal50ClientDrift(ClientIdentityToken("device_b"), MetricValue(0.3)),
                Terminal50ClientDrift(ClientIdentityToken("device_a"), MetricValue(0.1)),
            ),
        )


def test_terminal50_drift_summary_accepts_sorted_client_medians() -> None:
    summary = Terminal50DriftSummary(
        seed=Seed(3),
        coefficient=None,
        federation_rms_drift=MetricValue(0.2),
        client_rms_drifts=(
            Terminal50ClientDrift(ClientIdentityToken("device_a"), MetricValue(0.1)),
            Terminal50ClientDrift(ClientIdentityToken("device_b"), MetricValue(0.3)),
        ),
    )

    assert summary.client_rms_drifts[0].rms_drift == MetricValue(0.1)
