"""Typed split protocols and locked split declarations."""

from math import fsum

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import CoverageTarget, Ratio, floats_absolutely_close

UNIT_FRACTION_TOTAL = 1.0
FRACTION_TOTAL_ABSOLUTE_TOLERANCE = 1e-12


def _sums_to_unit_fraction(*values: Ratio | CoverageTarget) -> bool:
    return floats_absolutely_close(
        fsum(values),
        UNIT_FRACTION_TOTAL,
        FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
    )


class FractionalSplitProtocol(StrictModel):
    training: Ratio
    calibration: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "FractionalSplitProtocol":
        if not _sums_to_unit_fraction(
            self.training,
            self.calibration,
            self.evaluation,
        ):
            raise ValueError("fractional split must sum to one")
        return self


class TemporalSplitProtocol(StrictModel):
    historical_training: Ratio
    historical_calibration: Ratio
    future_recalibration: Ratio
    future_evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "TemporalSplitProtocol":
        if not _sums_to_unit_fraction(
            self.historical_training,
            self.historical_calibration,
            self.future_recalibration,
            self.future_evaluation,
        ):
            raise ValueError("temporal split must sum to one")
        return self


class StaticReferenceSplitProtocol(StrictModel):
    """Randomized counterpart to the temporal 55/15/10/20 inventory."""

    training: Ratio
    calibration: Ratio
    reserve: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "StaticReferenceSplitProtocol":
        if not _sums_to_unit_fraction(
            self.training,
            self.calibration,
            self.reserve,
            self.evaluation,
        ):
            raise ValueError("static-reference split must sum to one")
        return self


TEMPORAL_SPLIT = TemporalSplitProtocol(
    historical_training=Ratio(0.55),
    historical_calibration=Ratio(0.15),
    future_recalibration=Ratio(0.10),
    future_evaluation=Ratio(0.20),
)

STATIC_REFERENCE_SPLIT = StaticReferenceSplitProtocol(
    training=Ratio(0.55),
    calibration=Ratio(0.15),
    reserve=Ratio(0.10),
    evaluation=Ratio(0.20),
)

NON_TEMPORAL_SPLIT = FractionalSplitProtocol(
    training=Ratio(1 / 3),
    calibration=Ratio(1 / 3),
    evaluation=Ratio(1 / 3),
)
