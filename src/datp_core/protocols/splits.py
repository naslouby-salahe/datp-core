"""Split declarations."""

from datp_core.domain.values import Ratio

from .models import FractionalSplitProtocol, TemporalSplitProtocol

TEMPORAL_SPLIT = TemporalSplitProtocol(
    historical_training=Ratio(0.55),
    historical_calibration=Ratio(0.15),
    future_recalibration=Ratio(0.10),
    future_evaluation=Ratio(0.20),
)


NON_TEMPORAL_SPLIT = FractionalSplitProtocol(
    training=Ratio(1 / 3),
    calibration=Ratio(1 / 3),
    evaluation=Ratio(1 / 3),
)
