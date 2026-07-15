from collections.abc import Callable
from decimal import Decimal

import pytest

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.statistical_results import (
    AnchorMovementAssessment,
    AnchorReferenceInterval,
    AnchorReproductionGateSpec,
    ClaimOutcome,
    ConfidenceLevel,
    ConfirmatoryAnalysisResult,
    DegenerateBootstrapIntervalResult,
    FailedAnchorReproductionResult,
    PairedDeltaDirection,
    PairedDeltaResult,
    StatisticalMethod,
    ValidBootstrapIntervalResult,
    assess_anchor_reproduction,
)
from datp_core.domain.runtime.seeds import Seed, SeedTuple


def _interval(*, lower: float, upper: float) -> ValidBootstrapIntervalResult:
    return ValidBootstrapIntervalResult(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        point_estimate=(lower + upper) / 2,
        lower=lower,
        upper=upper,
        confidence=ConfidenceLevel(value=Decimal("0.95")),
        resamples=BootstrapResampleCount(value=100),
    )


def _paired() -> PairedDeltaResult:
    return PairedDeltaResult(
        direction=PairedDeltaDirection.B1_MINUS_B2,
        per_seed_delta=(0.1, 0.2),
        scope_identity=StageFingerprint(value="a" * 64),
    )


def _paired_delta_with_unsupported_direction() -> PairedDeltaResult:
    return _construct_paired_delta_with_unsupported_direction(PairedDeltaResult)


def _construct_paired_delta_with_unsupported_direction(
    constructor: Callable[..., PairedDeltaResult],
) -> PairedDeltaResult:
    return constructor(
        direction="b2_minus_b1",
        per_seed_delta=(0.1,),
        scope_identity=StageFingerprint(value="a" * 64),
    )


def test_confirmatory_passes_only_for_positive_direction_bca_interval_excluding_zero() -> None:
    assert ConfirmatoryAnalysisResult(paired=_paired(), interval=_interval(lower=0.1, upper=0.2)).passes
    assert not ConfirmatoryAnalysisResult(paired=_paired(), interval=_interval(lower=-0.1, upper=0.2)).passes
    assert not ConfirmatoryAnalysisResult(paired=_paired(), interval=_interval(lower=-0.2, upper=-0.1)).passes
    assert not ConfirmatoryAnalysisResult(
        paired=_paired(),
        interval=DegenerateBootstrapIntervalResult(
            method=StatisticalMethod.BCA_BOOTSTRAP,
            sample_size=2,
            degeneracy_reason="ties",
            attempted_resamples=BootstrapResampleCount(value=100),
            available_point_estimate=0.1,
            wording_outcome=ClaimOutcome.NULL,
        ),
    ).passes


def test_paired_delta_direction_is_locked_to_b1_minus_b2() -> None:
    with pytest.raises(DomainValidationError):
        _paired_delta_with_unsupported_direction()


def test_anchor_gate_blocks_a_wider_than_twenty_percent_reproduction() -> None:
    gate = AnchorReproductionGateSpec(
        seed_cohort=SeedTuple(values=tuple(Seed(value=value) for value in range(5))),
        reference_interval=AnchorReferenceInterval(),
    )
    result = assess_anchor_reproduction(
        gate=gate,
        reproduced_interval=_interval(lower=0.60, upper=0.75),
        movement_assessment=AnchorMovementAssessment.NOT_MATERIAL_TOWARD_ZERO,
    )

    assert gate.reference_interval.width == pytest.approx(0.122)
    assert gate.maximum_width == pytest.approx(0.1464)
    assert isinstance(result, FailedAnchorReproductionResult)
